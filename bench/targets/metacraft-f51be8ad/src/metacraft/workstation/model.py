from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType


GIBIBYTE = 1024**3
PHYSICAL_CORES_PER_LANE = 4
RESERVED_PHYSICAL_CORES = 4
LANE_MEMORY_BYTES = 16 * GIBIBYTE
WORKSTATION_MEMORY_GUARD_BYTES = 16 * GIBIBYTE
LAYOUT_FRESHNESS = timedelta(minutes=5)


class StaleLane(RuntimeError):
    """
    Signals that a local placement must be observed again before use.
    """


@dataclass(frozen=True, slots=True)
class LogicalProcessor:
    """
    Describes one logical processor in the host topology.
    """

    identifier: int
    processor_group: int
    logical_processor: int
    core: int
    last_level_cache: int
    numa_node: int
    is_available: bool = True


@dataclass(frozen=True, slots=True)
class Memory:
    """
    Records currently available memory for one NUMA node.
    """

    numa_node: int
    available_bytes: int


@dataclass(frozen=True, slots=True)
class Host:
    """
    Holds one immutable local topology and memory observation.
    """

    identity: str
    logical_processors: tuple[LogicalProcessor, ...]
    memory: tuple[Memory, ...]
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class Demand:
    """
    Requests bounded workers for tasks that fit one fixed lane.
    """

    workers: int
    worker_memory_bytes: int


@dataclass(frozen=True, slots=True)
class Command:
    """
    Describes one product-owned worker process without product meaning.
    """

    executable: Path
    arguments: tuple[str, ...] = ()
    directory: Path | None = None
    environment: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Freeze the environment overlay before the worker can start.
        """

        object.__setattr__(
            self,
            "environment",
            MappingProxyType(dict(self.environment)),
        )


@dataclass(frozen=True, slots=True)
class Lane:
    """
    Keeps one local placement opaque outside the workstation Module.
    """

    identity: str
    processor_group: int
    numa_node: int
    last_level_cache: int
    _logical_processors: tuple[LogicalProcessor, ...]
    observed_at: datetime
    fresh_until: datetime

    def __post_init__(self) -> None:
        """
        Refuse placements that did not come from one complete locality cell.
        """

        cores = {
            (processor.processor_group, processor.core)
            for processor in self._logical_processors
        }
        identifiers = {
            processor.identifier
            for processor in self._logical_processors
        }
        is_one_cell = all(
            processor.is_available
            and processor.processor_group == self.processor_group
            and processor.numa_node == self.numa_node
            and processor.last_level_cache == self.last_level_cache
            for processor in self._logical_processors
        )
        has_timezone_aware_times = (
            self.observed_at.tzinfo is not None
            and self.fresh_until.tzinfo is not None
        )
        if (
            not self.identity.strip()
            or (
                len(self._logical_processors)
                != PHYSICAL_CORES_PER_LANE
            )
            or len(identifiers) != PHYSICAL_CORES_PER_LANE
            or len(cores) != PHYSICAL_CORES_PER_LANE
            or not is_one_cell
            or not has_timezone_aware_times
            or self.fresh_until < self.observed_at
        ):
            raise ValueError("lane_shape_invalid")

    def as_mapping(self) -> dict[str, object]:
        """
        Return placement evidence without exposing raw CPU identifiers.
        """

        return {
            "identity": self.identity,
            "last_level_cache": self.last_level_cache,
            "logical_processors": len(self._logical_processors),
            "memory_bytes": LANE_MEMORY_BYTES,
            "numa_node": self.numa_node,
            "physical_cores": len(
                {
                    processor.core
                    for processor in self._logical_processors
                }
            ),
            "processor_group": self.processor_group,
            "uses_smt": len(
                {
                    processor.core
                    for processor in self._logical_processors
                }
            )
            != len(self._logical_processors),
        }

    def is_fresh_at(self, value: datetime) -> bool:
        """
        Report whether this exact placement may still start a worker.
        """

        return self.observed_at <= value <= self.fresh_until


@dataclass(frozen=True, slots=True)
class Layout:
    """
    Retains one fresh set of independent local lanes.
    """

    host_identity: str
    observed_at: datetime
    fresh_until: datetime
    lanes: tuple[Lane, ...]

    @property
    def limit(self) -> int:
        """
        Return the number of complete lanes in this layout.
        """

        return len(self.lanes)

    def is_fresh_at(self, value: datetime) -> bool:
        """
        Report whether this layout may still start workers.
        """

        return self.observed_at <= value <= self.fresh_until

    def as_mapping(self) -> dict[str, object]:
        """
        Return the complete local capacity evidence.
        """

        return {
            "fresh_until": self.fresh_until,
            "host_identity": self.host_identity,
            "lanes": tuple(lane.as_mapping() for lane in self.lanes),
            "limit": self.limit,
            "observed_at": self.observed_at,
        }


def plan(
    demand: Demand,
    *,
    host: Host,
    now: datetime | None = None,
) -> Layout:
    """
    Form fixed local lanes from one explicit host observation.
    """

    if demand.workers <= 0:
        raise ValueError("worker_demand_invalid")
    if demand.worker_memory_bytes <= 0:
        raise ValueError("memory_demand_invalid")
    if demand.worker_memory_bytes > LANE_MEMORY_BYTES:
        raise ValueError("lane_memory_exceeded")
    current = now or datetime.now(UTC)
    fresh_until = host.observed_at + LAYOUT_FRESHNESS
    cells = _physical_cores(host)
    core_bound = max(
        0,
        (sum(len(cores) for cores in cells.values()) - RESERVED_PHYSICAL_CORES)
        // PHYSICAL_CORES_PER_LANE,
    )
    memory_slots = _memory_slots(host.memory)
    chunks = {
        cell: tuple(
            tuple(cores[start : start + PHYSICAL_CORES_PER_LANE])
            for start in range(
                0,
                len(cores) - PHYSICAL_CORES_PER_LANE + 1,
                PHYSICAL_CORES_PER_LANE,
            )
        )
        for cell, cores in cells.items()
    }
    selected: list[
        tuple[
            tuple[int, int, int],
            tuple[LogicalProcessor, ...],
        ]
    ] = []
    used_by_node: dict[int, int] = defaultdict(int)
    depth = 0
    ceiling = min(demand.workers, core_bound)
    ordered_cells = tuple(sorted(chunks))
    while len(selected) < ceiling:
        is_added = False
        for cell in ordered_cells:
            group, node, _cache = cell
            del group
            candidates = chunks[cell]
            if depth >= len(candidates):
                continue
            if used_by_node[node] >= memory_slots.get(node, 0):
                continue
            selected.append((cell, candidates[depth]))
            used_by_node[node] += 1
            is_added = True
            if len(selected) == ceiling:
                break
        if not is_added:
            break
        depth += 1
    lanes = tuple(
        Lane(
            identity=f"lane-{number:02d}",
            processor_group=cell[0],
            numa_node=cell[1],
            last_level_cache=cell[2],
            _logical_processors=logical_processors,
            observed_at=host.observed_at,
            fresh_until=fresh_until,
        )
        for number, (cell, logical_processors) in enumerate(selected, 1)
    )
    layout = Layout(
        host_identity=host.identity,
        observed_at=host.observed_at,
        fresh_until=fresh_until,
        lanes=lanes,
    )
    if not layout.is_fresh_at(current):
        return Layout(
            host_identity=host.identity,
            observed_at=host.observed_at,
            fresh_until=fresh_until,
            lanes=(),
        )
    return layout


def _physical_cores(
    host: Host,
) -> Mapping[tuple[int, int, int], list[LogicalProcessor]]:
    cores: dict[
        tuple[int, int, int],
        dict[tuple[int, int], LogicalProcessor],
    ] = defaultdict(dict)
    for processor in sorted(
        host.logical_processors,
        key=lambda item: item.identifier,
    ):
        if not processor.is_available:
            continue
        cell = (
            processor.processor_group,
            processor.numa_node,
            processor.last_level_cache,
        )
        cores[cell].setdefault(
            (processor.processor_group, processor.core),
            processor,
        )
    return {
        cell: list(selected.values())
        for cell, selected in sorted(cores.items())
    }


def _memory_slots(memory: tuple[Memory, ...]) -> dict[int, int]:
    ordered = tuple(sorted(memory, key=lambda item: item.numa_node))
    if not ordered:
        return {}
    guard, remainder = divmod(WORKSTATION_MEMORY_GUARD_BYTES, len(ordered))
    return {
        item.numa_node: max(
            0,
            (
                item.available_bytes
                - guard
                - (1 if index < remainder else 0)
            )
            // LANE_MEMORY_BYTES,
        )
        for index, item in enumerate(ordered)
    }

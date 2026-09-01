from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from .session import Session

@dataclass(frozen=True, slots=True)
class ProjectExecution:
    """
    Identifies how one native project was executed.
    """

    source: str
    is_native: bool
    project: str
    return_code: int
    placement: Mapping[str, object]

    def __post_init__(self) -> None:
        """
        Freeze placement evidence after validating the execution identity.
        """

        if not self.source.strip() or not self.project.strip():
            raise ValueError("execution_identity_required")
        object.__setattr__(
            self,
            "placement",
            MappingProxyType(dict(self.placement)),
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Keep native and deterministic test evidence distinguishable.
        """

        return {
            "native": self.is_native,
            "placement": dict(self.placement),
            "project": self.project,
            "return_code": self.return_code,
            "source": self.source,
        }

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> ProjectExecution:
        """
        Restore one execution record without accepting extra facts.
        """

        if set(value) != {
            "native",
            "placement",
            "project",
            "return_code",
            "source",
        }:
            raise RuntimeError("execution_record_fields_invalid")
        is_native = value["native"]
        return_code = value["return_code"]
        placement = value["placement"]
        if (
            not isinstance(is_native, bool)
            or not isinstance(return_code, int)
            or isinstance(return_code, bool)
            or not isinstance(placement, Mapping)
        ):
            raise RuntimeError("execution_record_invalid")
        record = cls(
            source=str(value["source"]),
            is_native=is_native,
            project=str(value["project"]),
            return_code=return_code,
            placement=placement,
        )
        if record.as_mapping() != dict(value):
            raise RuntimeError("execution_record_invalid")
        return record


@dataclass(frozen=True, slots=True)
class ExecutedProject:
    """
    Pairs one completed project session with its execution record.
    """

    session: Session
    execution: ProjectExecution

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import inspect
import json
import os
from pathlib import Path
import sys
import time

import pytest

import metacraft.workstation as workstation
from metacraft.workstation import (
    Command,
    Demand,
    Host,
    Lane,
    LogicalProcessor,
    Memory,
    StaleLane,
    plan,
    start,
)
from metacraft.workstation.model import plan as plan_model


GIBIBYTE = 1024**3


def _host(
    *,
    cells: tuple[tuple[int, int, int], ...],
    memory_by_node: tuple[tuple[int, int], ...],
    observed_at: datetime,
) -> Host:
    logical_processors = []
    identifier = 0
    core = 0
    for node, cache, physical_cores in cells:
        for _ in range(physical_cores):
            for logical_processor in range(2):
                logical_processors.append(
                    LogicalProcessor(
                        identifier=identifier,
                        processor_group=0,
                        logical_processor=logical_processor,
                        core=core,
                        last_level_cache=cache,
                        numa_node=node,
                    )
                )
                identifier += 1
            core += 1
    return Host(
        identity="fixture-workstation",
        logical_processors=tuple(logical_processors),
        memory=tuple(
            Memory(numa_node=node, available_bytes=available)
            for node, available in memory_by_node
        ),
        observed_at=observed_at,
    )


def test_plan_forms_one_fixed_lane_in_each_locality_cell() -> None:
    observed_at = datetime(2026, 7, 23, tzinfo=UTC)
    host = _host(
        cells=((0, 0, 6), (0, 1, 6)),
        memory_by_node=((0, 64 * GIBIBYTE),),
        observed_at=observed_at,
    )

    layout = plan(
        Demand(workers=8, worker_memory_bytes=8 * GIBIBYTE),
        host=host,
        now=observed_at,
    )

    assert layout.limit == 2
    assert layout.as_mapping()["lanes"] == (
        {
            "identity": "lane-01",
            "last_level_cache": 0,
            "logical_processors": 4,
            "memory_bytes": 16 * GIBIBYTE,
            "numa_node": 0,
            "physical_cores": 4,
            "processor_group": 0,
            "uses_smt": False,
        },
        {
            "identity": "lane-02",
            "last_level_cache": 1,
            "logical_processors": 4,
            "memory_bytes": 16 * GIBIBYTE,
            "numa_node": 0,
            "physical_cores": 4,
            "processor_group": 0,
            "uses_smt": False,
        },
    )


def test_model_planner_requires_one_explicit_host_fact() -> None:
    parameter = inspect.signature(plan_model).parameters["host"]

    assert parameter.default is inspect.Parameter.empty


def test_package_plan_observes_only_when_host_is_absent(monkeypatch) -> None:
    observed_at = datetime(2026, 7, 23, tzinfo=UTC)
    host = _host(
        cells=((0, 0, 8),),
        memory_by_node=((0, 64 * GIBIBYTE),),
        observed_at=observed_at,
    )
    observations = []

    def observe() -> Host:
        observations.append(host.identity)
        return host

    monkeypatch.setattr(workstation, "observe", observe)
    demand = Demand(workers=1, worker_memory_bytes=GIBIBYTE)

    observed = workstation.plan(demand, now=observed_at)
    supplied = workstation.plan(demand, host=host, now=observed_at)

    assert observed == supplied
    assert observations == [host.identity]


@pytest.mark.skipif(os.name != "nt", reason="Windows workstation boundary")
def test_start_defers_a_lane_after_its_observation_expires(
    tmp_path: Path,
) -> None:
    observed_at = datetime.now(UTC) - timedelta(minutes=10)
    layout = plan(
        Demand(workers=1, worker_memory_bytes=GIBIBYTE),
        host=_host(
            cells=((0, 0, 8),),
            memory_by_node=((0, 64 * GIBIBYTE),),
            observed_at=observed_at,
        ),
        now=observed_at,
    )

    with pytest.raises(StaleLane, match="lane_stale"):
        start(
            Command(
                executable=Path(sys.executable),
                arguments=("-c", "pass"),
                directory=tmp_path,
            ),
            layout.lanes[0],
        )


def test_plan_rejects_work_that_cannot_fit_one_lane() -> None:
    observed_at = datetime(2026, 7, 23, tzinfo=UTC)
    host = _host(
        cells=((0, 0, 8),),
        memory_by_node=((0, 64 * GIBIBYTE),),
        observed_at=observed_at,
    )

    with pytest.raises(ValueError, match="lane_memory_exceeded"):
        plan(
            Demand(
                workers=1,
                worker_memory_bytes=16 * GIBIBYTE + 1,
            ),
            host=host,
            now=observed_at,
        )


@pytest.mark.parametrize(
    ("demand", "finding"),
    (
        (
            Demand(workers=0, worker_memory_bytes=GIBIBYTE),
            "worker_demand_invalid",
        ),
        (
            Demand(workers=1, worker_memory_bytes=0),
            "memory_demand_invalid",
        ),
    ),
)
def test_plan_rejects_empty_demand(demand: Demand, finding: str) -> None:
    observed_at = datetime(2026, 7, 23, tzinfo=UTC)
    host = _host(
        cells=((0, 0, 8),),
        memory_by_node=((0, 64 * GIBIBYTE),),
        observed_at=observed_at,
    )

    with pytest.raises(ValueError, match=finding):
        plan(demand, host=host, now=observed_at)


def test_plan_keeps_large_workstations_cell_local() -> None:
    observed_at = datetime(2026, 7, 23, tzinfo=UTC)
    host = _host(
        cells=(
            (0, 0, 14),
            (1, 1, 14),
            (2, 2, 14),
            (3, 3, 14),
        ),
        memory_by_node=(
            (0, 64 * GIBIBYTE),
            (1, 64 * GIBIBYTE),
            (2, 64 * GIBIBYTE),
            (3, 64 * GIBIBYTE),
        ),
        observed_at=observed_at,
    )

    layout = plan(
        Demand(workers=60, worker_memory_bytes=16 * GIBIBYTE),
        host=host,
        now=observed_at,
    )

    assert layout.limit == 12
    assert {
        (lane["numa_node"], lane["last_level_cache"])
        for lane in layout.as_mapping()["lanes"]
    } == {(0, 0), (1, 1), (2, 2), (3, 3)}
    assert all(
        lane["physical_cores"] == lane["logical_processors"] == 4
        for lane in layout.as_mapping()["lanes"]
    )


def test_lane_cannot_be_forged_outside_one_locality_cell() -> None:
    observed_at = datetime(2026, 7, 23, tzinfo=UTC)
    logical_processors = (
        LogicalProcessor(0, 0, 0, 0, 0, 0),
        LogicalProcessor(1, 0, 1, 0, 0, 0),
        LogicalProcessor(2, 0, 0, 1, 0, 0),
        LogicalProcessor(3, 0, 0, 2, 1, 0),
    )

    with pytest.raises(ValueError, match="lane_shape_invalid"):
        Lane(
            identity="forged",
            processor_group=0,
            numa_node=0,
            last_level_cache=0,
            _logical_processors=logical_processors,
            observed_at=observed_at,
            fresh_until=observed_at + timedelta(minutes=5),
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows workstation boundary")
def test_start_contains_one_real_worker_in_one_lane(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "worker.json"
    monkeypatch.setenv("METACRAFT_PROHIBITED_SECRET", "must-not-cross")
    layout = plan(Demand(workers=1, worker_memory_bytes=GIBIBYTE))
    if not layout.lanes:
        pytest.skip("host has no complete workstation lane")
    command = Command(
        executable=Path(sys.executable),
        arguments=(
            "-c",
            (
                "import json, os, pathlib; "
                "pathlib.Path(os.environ['WORKER_OUTPUT']).write_text("
                "json.dumps({'prohibited_secret': os.environ.get("
                "'METACRAFT_PROHIBITED_SECRET'), 'pid': os.getpid()}), "
                "encoding='utf-8')"
            ),
        ),
        directory=tmp_path,
        environment={"WORKER_OUTPUT": str(output)},
    )

    with start(command, layout.lanes[0]) as worker:
        assert worker.wait(timeout=10) == 0
        placement = worker.as_mapping()

    observed = json.loads(output.read_text(encoding="utf-8"))
    assert observed == {
        "prohibited_secret": None,
        "pid": placement["pid"],
    }
    assert placement["effective_cpu_sets"] == 4
    assert placement["job_memory_bytes"] == 16 * GIBIBYTE
    assert placement["lane"] == layout.lanes[0].as_mapping()


@pytest.mark.skipif(os.name != "nt", reason="Windows workstation boundary")
def test_one_lane_cannot_hold_two_process_trees(tmp_path: Path) -> None:
    layout = plan(Demand(workers=1, worker_memory_bytes=GIBIBYTE))
    if not layout.lanes:
        pytest.skip("host has no complete workstation lane")
    lane = layout.lanes[0]
    sleeping = Command(
        executable=Path(sys.executable),
        arguments=("-c", "import time; time.sleep(30)"),
        directory=tmp_path,
    )
    worker = start(sleeping, lane)
    try:
        with pytest.raises(RuntimeError, match="lane_busy"):
            start(sleeping, lane)
        from metacraft.workstation.windows import observe

        host = observe()
        alternatives = tuple(
            tuple(
                logical_processor
                for logical_processor in host.logical_processors
                if (
                    logical_processor.processor_group
                    == selected.processor_group
                )
                and logical_processor.core == selected.core
                and logical_processor.identifier != selected.identifier
            )
            for selected in lane._logical_processors
        )
        if all(alternatives):
            sibling_lane = Lane(
                identity="same-cores-other-threads",
                processor_group=lane.processor_group,
                numa_node=lane.numa_node,
                last_level_cache=lane.last_level_cache,
                _logical_processors=tuple(
                    processors[0] for processors in alternatives
                ),
                observed_at=lane.observed_at,
                fresh_until=lane.fresh_until,
            )
            with pytest.raises(RuntimeError, match="lane_busy"):
                start(sleeping, sibling_lane)
    finally:
        worker.close()

    with start(
        Command(
            executable=Path(sys.executable),
            arguments=("-c", "pass"),
            directory=tmp_path,
        ),
        lane,
    ) as reused:
        assert reused.wait(timeout=10) == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows workstation boundary")
def test_job_affinity_reaches_a_child_process(tmp_path: Path) -> None:
    output = tmp_path / "child-affinity.txt"
    layout = plan(Demand(workers=1, worker_memory_bytes=GIBIBYTE))
    if not layout.lanes:
        pytest.skip("host has no complete workstation lane")
    child = (
        "import ctypes, os, pathlib; "
        "k=ctypes.WinDLL('kernel32', use_last_error=True); "
        "k.GetCurrentProcess.restype=ctypes.c_void_p; "
        "k.GetProcessAffinityMask.argtypes=(ctypes.c_void_p, "
        "ctypes.POINTER(ctypes.c_size_t), "
        "ctypes.POINTER(ctypes.c_size_t)); "
        "p=ctypes.c_size_t(); s=ctypes.c_size_t(); "
        "ok=k.GetProcessAffinityMask(k.GetCurrentProcess(), "
        "ctypes.byref(p), ctypes.byref(s)); "
        "assert ok; "
        "pathlib.Path(os.environ['AFFINITY_OUTPUT']).write_text("
        "str(p.value.bit_count()), encoding='utf-8')"
    )
    parent = (
        "import subprocess, sys; "
        f"raise SystemExit(subprocess.run([sys.executable, '-c', {child!r}])."
        "returncode)"
    )

    with start(
        Command(
            executable=Path(sys.executable),
            arguments=("-c", parent),
            directory=tmp_path,
            environment={"AFFINITY_OUTPUT": str(output)},
        ),
        layout.lanes[0],
    ) as worker:
        assert worker.wait(timeout=10) == 0

    assert output.read_text(encoding="utf-8") == "4"


@pytest.mark.skipif(os.name != "nt", reason="Windows workstation boundary")
def test_closing_worker_ends_its_complete_process_tree(tmp_path: Path) -> None:
    ready = tmp_path / "ready"
    escaped = tmp_path / "escaped"
    layout = plan(Demand(workers=1, worker_memory_bytes=GIBIBYTE))
    if not layout.lanes:
        pytest.skip("host has no complete workstation lane")
    child = (
        "import os, pathlib, time; time.sleep(1); "
        "pathlib.Path(os.environ['ESCAPED']).write_text("
        "'escaped', encoding='utf-8')"
    )
    parent = (
        "import os, pathlib, subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
        "pathlib.Path(os.environ['READY']).write_text("
        "'ready', encoding='utf-8'); "
        "time.sleep(30)"
    )
    worker = start(
        Command(
            executable=Path(sys.executable),
            arguments=("-c", parent),
            directory=tmp_path,
            environment={
                "ESCAPED": str(escaped),
                "READY": str(ready),
            },
        ),
        layout.lanes[0],
    )
    try:
        deadline = time.monotonic() + 5
        while not ready.is_file() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.is_file()
    finally:
        worker.close()

    time.sleep(1.5)
    assert not escaped.exists()

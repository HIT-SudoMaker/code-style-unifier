from __future__ import annotations

import hashlib

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import inspect
from pathlib import Path
from threading import Event
from time import monotonic, sleep

import pytest

import metacraft.solvers.lumerical_fdtd._lane_worker as lane_worker_module
import metacraft.solvers.lumerical_fdtd.lane as lane_module
from metacraft.authority import Reference
from metacraft.canonical import encode_bytes
from metacraft.solvers.lumerical_fdtd.project_execution import ProjectExecution
from metacraft.solvers.lumerical_fdtd.probe import ProductProbe
from metacraft.solvers.lumerical_fdtd.lane import (
    SessionPool,
    WorkstationExecution,
)
from metacraft.solvers.lumerical_fdtd.artifacts import (
    RunDirectory,
    WorkRecord,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    CapacityObservation,
    LumericalBinding,
    LumericalUnavailable,
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseQualification,
)
from metacraft.solvers.lumerical_fdtd.periodic_response import (
    LumericalPeriodicResponse,
)
from metacraft.solvers.lumerical_fdtd.session import (
    _GratingResponsePlanes,
    _OptionalResult,
)
from metacraft.work_execution import CapacityRenewalRequired
from metacraft.workstation import StaleLane
from tests.lumerical_fixtures import workstation_layout
from tests.solver_fakes import ActiveEngines, FakeSession


def _binding(tmp_path: Path) -> LumericalBinding:
    return LumericalBinding(
        executable=str(tmp_path / "fdtd-solutions.exe"),
        engine=str(tmp_path / "fdtd-engine.exe"),
        python_api=str(tmp_path / "lumapi.py"),
        product_version="2026 r1",
        api_identity="fixture-api",
        license_server="fixture-license",
        resource_identity="fixture-cpu",
        response_qualifications=(
            PeriodicResponseQualification.qualified(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )


def _capacity(
    observed_at: datetime,
    *,
    limit: int,
) -> CapacityObservation:
    return CapacityObservation(
        scope="lumerical-fdtd/fixture",
        limit=limit,
        observed_at=observed_at,
        fresh_until=observed_at.replace(year=observed_at.year + 1),
        lumerical_gui_limit=limit,
        lumerical_solve_limit=limit,
        workstation_limit=limit,
    )


def _reference_hash(name: str) -> str:
    return f"sha256:{hashlib.sha256(name.encode()).hexdigest()}"


def _capacity_reference(name: str) -> Reference:
    return Reference(
        content_hash=_reference_hash(name),
        media_type="application/json",
        metadata_content_hash=_reference_hash("metadata-" + name),
        size_bytes=len(name),
    )


def test_one_lane_reuses_one_session_and_reopens_with_a_new_identity(
    tmp_path: Path,
) -> None:
    """
    Keep work, lane, and native-session identities independent.
    """

    lane = workstation_layout(
        datetime.now(UTC),
        physical_cores=8,
    ).lanes[0]
    opened: list[FakeSession] = []

    def open_session(admitted_lane):
        session = FakeSession(
            active=ActiveEngines(),
            result={},
        )
        session.placement = {
            "effective_cpu_sets": 4,
            "job_memory_bytes": 16 * 1024**3,
            "lane": admitted_lane.as_mapping(),
        }
        opened.append(session)
        return session

    sessions = SessionPool(
        WorkstationExecution(
            Path(_binding(tmp_path).python_api),
            _binding(tmp_path).license_server,
        ),
        (lane,),
        _open_session=open_session,
    )
    with sessions.lease() as first:
        first_identity = first.session_identity
        assert first.lane_identity == lane.identity
        assert first.session_identity != first.lane_identity
        assert not first.is_reused
    with sessions.lease() as reused:
        assert reused.session_identity == first_identity
        assert reused.is_reused
    with pytest.raises(RuntimeError, match="discard session"):
        with sessions.lease():
            raise RuntimeError("discard session")
    with sessions.lease() as reopened:
        assert reopened.lane_identity == lane.identity
        assert reopened.session_identity != first_identity
        assert not reopened.is_reused
    sessions.close()

    assert len(opened) == 2
    assert all(session.closed for session in opened)


def test_stale_lane_defers_work_until_capacity_can_be_renewed(
    tmp_path: Path,
) -> None:
    """
    Translate stale local placement into the runner's renewal signal.
    """

    lane = workstation_layout(
        datetime.now(UTC),
        physical_cores=8,
    ).lanes[0]
    opened = 0

    def open_session(admitted_lane):
        nonlocal opened
        opened += 1
        if opened == 1:
            raise StaleLane("lane_stale")
        session = FakeSession(active=ActiveEngines(), result={})
        session.placement = {
            "effective_cpu_sets": 4,
            "job_memory_bytes": 16 * 1024**3,
            "lane": admitted_lane.as_mapping(),
        }
        return session

    sessions = SessionPool(
        WorkstationExecution(
            Path(_binding(tmp_path).python_api),
            _binding(tmp_path).license_server,
        ),
        (lane,),
        _open_session=open_session,
    )

    with pytest.raises(
        CapacityRenewalRequired,
        match="local_placement_stale",
    ):
        with sessions.lease():
            pass
    with sessions.lease() as lease:
        assert lease.lane_identity == lane.identity
    sessions.close()


def test_capacity_renewal_waits_for_the_lease_then_changes_its_lane(
    tmp_path: Path,
) -> None:
    """
    Replace capacity and lanes as one change between leases.
    """

    now = datetime.now(UTC)
    layout = workstation_layout(now, physical_cores=16)
    first_lane = layout.lanes[0]
    second_lane = layout.lanes[-1]
    first_capacity = _capacity(now, limit=1)
    second_capacity = _capacity(now, limit=1)
    first_reference = _capacity_reference("first")
    second_reference = _capacity_reference("second")
    active = ActiveEngines()
    opened: list[FakeSession] = []

    def open_session(lane):
        session = FakeSession(active=active, result={})
        session.placement = {
            "effective_cpu_sets": 4,
            "job_memory_bytes": 16 * 1024**3,
            "lane": lane.as_mapping(),
        }
        opened.append(session)
        return session

    sessions = SessionPool(
        WorkstationExecution(
            Path(_binding(tmp_path).python_api),
            _binding(tmp_path).license_server,
        ),
        (first_lane,),
        capacity_reference=first_reference,
        capacity=first_capacity,
        _open_session=open_session,
    )
    entered = Event()
    release = Event()

    def hold_lease() -> None:
        with sessions.lease() as lease:
            assert lease.lane_identity == first_lane.identity
            assert lease.capacity_reference == first_reference
            entered.set()
            release.wait(1)

    with ThreadPoolExecutor(max_workers=2) as workers:
        held = workers.submit(hold_lease)
        assert entered.wait(1)
        renewal = workers.submit(
            sessions.replace,
            lanes=(second_lane,),
            capacity_reference=second_reference,
            capacity=second_capacity,
        )
        sleep(0.05)
        assert not renewal.done()
        release.set()
        held.result(timeout=1)
        renewal.result(timeout=1)

    with sessions.lease() as lease:
        assert lease.lane_identity == second_lane.identity
        assert lease.capacity_reference == second_reference
        assert lease.capacity == second_capacity
    sessions.close()

    assert len(opened) == 2
    assert all(session.closed for session in opened)


def test_native_session_timeout_releases_every_started_resource(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Interrupt acceptance before waiting for its thread or worker.
    """

    events: list[str] = []

    class Connection:
        closed = False

        def close(self) -> None:
            self.closed = True
            events.append("connection closed")

    connection = Connection()

    class Listener:
        address = ("127.0.0.1", 42000)

        def __init__(self, *_args, **_kwargs) -> None:
            self.closed = Event()

        def accept(self):
            self.closed.wait(0.25)
            events.append("accept returned")
            return connection

        def close(self) -> None:
            events.append("listener closed")
            self.closed.set()

    class Worker:
        closed = False

        def close(self) -> None:
            self.closed = True
            events.append("worker closed")

    worker = Worker()
    monkeypatch.setattr(lane_module, "Listener", Listener)
    monkeypatch.setattr(
        lane_module,
        "_SESSION_OPEN_TIMEOUT_SECONDS",
        0.01,
        raising=False,
    )
    lane = workstation_layout(
        datetime.now(UTC),
        physical_cores=8,
    ).lanes[0]
    execution = WorkstationExecution(
        Path(_binding(tmp_path).python_api),
        _binding(tmp_path).license_server,
        starter=lambda _command, _lane: worker,
    )
    sessions = SessionPool(execution, (lane,))

    started = monotonic()
    with pytest.raises(
        RuntimeError,
        match="native_session_start_timeout",
    ):
        with sessions.lease():
            pass

    assert monotonic() - started < 0.15
    assert connection.closed
    assert worker.closed
    assert events.index("listener closed") < events.index("accept returned")


def test_native_worker_responses_have_three_exact_envelopes() -> None:
    """
    Accept success, typed absence, and failure without permissive overlap.
    """

    assert lane_module._native_value({"ok": True, "value": "ready"}) == "ready"
    with pytest.raises(LumericalUnavailable) as absent:
        lane_module._native_value({"ok": False, "unavailable": "license_unavailable"})
    assert absent.value.reason == "license_unavailable"
    with pytest.raises(
        RuntimeError,
        match="native_session_failed:RuntimeError:broken",
    ):
        lane_module._native_value(
            {
                "error": "RuntimeError",
                "message": "broken",
                "ok": False,
            }
        )


@pytest.mark.parametrize(
    "response",
    (
        {"ok": 1, "value": None},
        {"error": "x", "ok": True, "value": None},
        {
            "error": "x",
            "ok": False,
            "unavailable": "license_unavailable",
        },
        {"error": "x", "message": "", "ok": False, "surplus": None},
        {"error": "x", "ok": False},
    ),
)
def test_native_worker_response_drift_reaches_the_caller(
    response: dict[str, object],
) -> None:
    """
    Reject truthy flags, surplus keys, conflicts, and incomplete failures.
    """

    with pytest.raises(
        RuntimeError,
        match="native_session_protocol_drift",
    ):
        lane_module._native_value(response)


def test_optional_result_crosses_the_native_session_ipc_envelope() -> None:
    requests: list[object] = []

    class Connection:
        def send(self, request: object) -> None:
            requests.append(request)

        def recv(self) -> object:
            return {
                "ok": True,
                "value": {"status": "response_not_returned"},
            }

    class Worker:
        def as_mapping(self) -> dict[str, object]:
            return {}

    session = lane_module._NativeSession(Connection(), Worker())

    outcome = session.optional_result(
        "grating_response",
        "reference_surface",
    )

    assert type(outcome) is _OptionalResult
    assert outcome.response is None
    assert requests == [
        {
            "arguments": (
                "grating_response",
                "reference_surface",
            ),
            "operation": "optional_result",
        }
    ]


def test_grating_response_planes_cross_the_native_session_ipc_envelope() -> None:
    requests: list[object] = []

    class Connection:
        def send(self, request: object) -> None:
            requests.append(request)

        def recv(self) -> object:
            return {
                "ok": True,
                "value": {
                    "reflection_plane_z_nm": -650,
                    "source_plane_z_nm": -750,
                    "transmission_plane_z_nm": 850,
                },
            }

    class Worker:
        def as_mapping(self) -> dict[str, object]:
            return {}

    session = lane_module._NativeSession(Connection(), Worker())

    planes = session.prepare_grating_response("grating_response")

    assert type(planes) is _GratingResponsePlanes
    assert planes.reflection_plane_z_nm == -650
    assert planes.source_plane_z_nm == -750
    assert planes.transmission_plane_z_nm == 850
    assert requests == [
        {
            "arguments": ("grating_response",),
            "operation": "prepare_grating_response",
        }
    ]


@pytest.mark.parametrize(
    "value",
    (
        {
            "reflection_plane_z_nm": -650,
            "source_plane_z_nm": -750,
        },
        {
            "reflection_plane_z_nm": -650,
            "source_plane_z_nm": -750,
            "transmission_plane_z_nm": 850.0,
        },
    ),
)
def test_native_session_rejects_malformed_grating_response_planes(
    value: object,
) -> None:
    class Connection:
        def send(self, request: object) -> None:
            pass

        def recv(self) -> object:
            return {"ok": True, "value": value}

    class Worker:
        def as_mapping(self) -> dict[str, object]:
            return {}

    session = lane_module._NativeSession(Connection(), Worker())

    with pytest.raises(
        RuntimeError,
        match="grating_response_planes_ipc_invalid",
    ):
        session.prepare_grating_response("grating_response")


def test_worker_encodes_grating_response_planes_explicitly() -> None:
    replies: list[object] = []

    class Connection:
        def __init__(self) -> None:
            self._requests = iter(
                (
                    {
                        "arguments": ("grating_response",),
                        "operation": "prepare_grating_response",
                    },
                    {"operation": "close"},
                )
            )

        def recv(self) -> object:
            return next(self._requests)

        def send(self, response: object) -> None:
            replies.append(response)

    class Session:
        def prepare_grating_response(
            self,
            name: str,
        ) -> _GratingResponsePlanes:
            assert name == "grating_response"
            return _GratingResponsePlanes(
                reflection_plane_z_nm=-650,
                source_plane_z_nm=-750,
                transmission_plane_z_nm=850,
            )

        def close(self) -> None:
            pass

    lane_worker_module._serve(Connection(), Session())  # type: ignore[arg-type]

    assert replies == [
        {
            "ok": True,
            "value": {
                "reflection_plane_z_nm": -650,
                "source_plane_z_nm": -750,
                "transmission_plane_z_nm": 850,
            },
        },
        {"ok": True, "value": None},
    ]


def test_worker_and_fake_share_the_optional_result_envelope() -> None:
    replies: list[object] = []

    class Connection:
        def __init__(self) -> None:
            self._requests = iter(
                (
                    {
                        "arguments": (
                            "grating_response",
                            "propagation",
                        ),
                        "operation": "optional_result",
                    },
                    {"operation": "close"},
                )
            )

        def recv(self) -> object:
            return next(self._requests)

        def send(self, response: object) -> None:
            replies.append(response)

    class Session:
        def optional_result(
            self,
            name: str,
            result_name: str,
        ) -> _OptionalResult:
            assert (name, result_name) == (
                "grating_response",
                "propagation",
            )
            return _OptionalResult.returned({"power_transmission": 0.8})

        def close(self) -> None:
            pass

    lane_worker_module._serve(Connection(), Session())  # type: ignore[arg-type]

    assert replies == [
        {
            "ok": True,
            "value": {
                "response": {"power_transmission": 0.8},
                "status": "returned",
            },
        },
        {"ok": True, "value": None},
    ]
    fake_session = FakeSession(
        active=ActiveEngines(),
        result={
            "_responses": {
                "propagation": {"power_transmission": 0.8},
            }
        },
    )
    fake_session.create("grating_response", "grating_response", {})
    assert fake_session.optional_result(
        "grating_response",
        "propagation",
    ).as_ipc_mapping() == replies[0]["value"]
    assert fake_session.optional_result(
        "grating_response",
        "reference_surface",
    ).as_ipc_mapping() == {"status": "response_not_returned"}


def test_native_session_close_attempts_every_owned_resource() -> None:
    """
    One close failure never suppresses the remaining cleanup attempts.
    """

    events: list[str] = []

    class Connection:
        def send(self, _request: object) -> None:
            events.append("request")

        def recv(self) -> object:
            events.append("response")
            raise EOFError("channel lost")

        def close(self) -> None:
            events.append("connection")
            raise RuntimeError("connection close failed")

    class Worker:
        def wait(self, *, timeout: float) -> int:
            assert timeout == 30
            events.append("wait")
            raise RuntimeError("worker wait failed")

        def close(self) -> None:
            events.append("worker")
            raise RuntimeError("worker close failed")

        def as_mapping(self) -> dict[str, object]:
            return {}

    session = lane_module._NativeSession(Connection(), Worker())

    with pytest.raises(BaseExceptionGroup) as raised:
        session.close()

    assert events == [
        "request",
        "response",
        "wait",
        "connection",
        "worker",
    ]
    assert len(raised.value.exceptions) == 4
    assert session._is_closed is True


@pytest.mark.parametrize(
    ("operation", "first_failure"),
    (
        ("close", KeyboardInterrupt("close interrupted")),
        (
            "replace",
            BaseExceptionGroup(
                "close interrupted",
                (KeyboardInterrupt("replace interrupted"),),
            ),
        ),
    ),
)
def test_session_pool_attempts_every_retained_close(
    tmp_path: Path,
    operation: str,
    first_failure: BaseException,
) -> None:
    """
    A base failure from one slot never strands its retained sibling.
    """

    events: list[str] = []

    class ClosingSession:
        def __init__(
            self,
            name: str,
            failure: BaseException | None = None,
        ) -> None:
            self.name = name
            self.failure = failure

        def close(self) -> None:
            events.append(self.name)
            if self.failure is not None:
                raise self.failure

    now = datetime.now(UTC)
    lanes = workstation_layout(now, physical_cores=16).lanes[:2]
    sessions = SessionPool(
        WorkstationExecution(
            Path(_binding(tmp_path).python_api),
            _binding(tmp_path).license_server,
        ),
        lanes,
    )
    sessions._slots[0].session = ClosingSession(  # type: ignore[assignment]
        "first",
        first_failure,
    )
    sessions._slots[1].session = ClosingSession(  # type: ignore[assignment]
        "second",
    )

    with pytest.raises(BaseExceptionGroup):
        if operation == "close":
            sessions.close()
        else:
            sessions.replace(
                lanes=lanes,
                capacity_reference=_capacity_reference("replacement"),
                capacity=_capacity(now, limit=2),
            )

    assert events == ["first", "second"]


@pytest.mark.parametrize("channel_error", (EOFError("eof"), OSError("lost")))
def test_native_startup_channel_absence_preserves_cleanup_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    channel_error: BaseException,
) -> None:
    """
    Keep startup absence typed while reporting every later cleanup failure.
    """

    events: list[str] = []

    class Connection:
        def poll(self, _timeout: float) -> bool:
            events.append("poll")
            return True

        def recv(self) -> object:
            events.append("receive")
            raise channel_error

        def close(self) -> None:
            events.append("connection")
            raise RuntimeError("connection close failed")

    connection = Connection()

    class Listener:
        address = ("127.0.0.1", 42000)

        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def accept(self) -> Connection:
            events.append("accept")
            return connection

        def close(self) -> None:
            events.append("listener")

    class Worker:
        def close(self) -> None:
            events.append("worker")
            raise RuntimeError("worker close failed")

    worker = Worker()
    monkeypatch.setattr(lane_module, "Listener", Listener)
    lane = workstation_layout(
        datetime.now(UTC),
        physical_cores=8,
    ).lanes[0]
    execution = WorkstationExecution(
        Path(_binding(tmp_path).python_api),
        _binding(tmp_path).license_server,
        starter=lambda _command, _lane: worker,
    )

    with pytest.raises(
        BaseExceptionGroup,
        match="native_session_start_terminalization_failed",
    ) as raised:
        execution._open_session(lane)

    assert isinstance(raised.value.exceptions[0], LumericalUnavailable)
    assert raised.value.exceptions[0].reason == "native_session_unavailable"
    assert tuple(str(error) for error in raised.value.exceptions[1:]) == (
        "connection close failed",
        "worker close failed",
    )
    assert "connection" in events
    assert "worker" in events


def test_run_directory_restores_one_complete_work_record(
    tmp_path: Path,
) -> None:
    """
    Let one value own the standard native-work artifact manifest.
    """

    run = RunDirectory(tmp_path / "run")
    directory = run.prepare_candidate(
        "circle-120",
        {"diameter_nm": 120},
        work_identity="sha256:work",
    )
    constructed, completed = run.native_projects(directory)
    constructed.write_bytes(b"constructed")
    completed.write_bytes(b"completed")
    capacity = _capacity(datetime.now(UTC), limit=1)
    capacity_reference = _capacity_reference("work")
    placement = {
        "effective_cpu_sets": 4,
        "job_memory_bytes": 16 * 1024**3,
        "lane": {
            "identity": "lane-01",
            "memory_bytes": 16 * 1024**3,
            "physical_cores": 4,
            "uses_smt": False,
        },
    }
    execution = ProjectExecution(
        source="deterministic_test",
        is_native=False,
        project="after.fsp",
        return_code=0,
        placement=placement,
    )
    record = WorkRecord(
        work_identity="sha256:work",
        session_identity="session:one",
        lane_identity="lane-01",
        is_session_reused=False,
        construction={"matches": True},
        execution=execution,
        observation={
            "execution": execution.as_mapping(),
            "phase": "1.25",
        },
        log="solver complete",
        lease_placement=placement,
        capacity=capacity,
        capacity_reference=capacity_reference,
    )

    run.record_execution(directory, execution)
    execution_bytes = (directory / "execution.json").read_bytes()
    run.record_work(directory, record)

    assert run.restore_work(directory) == record
    mapping = record.as_mapping()
    assert mapping["session_reused"] is False
    assert "is_session_reused" not in mapping
    assert "placement" not in mapping
    assert "execution" not in record.observation
    assert record.complete_observation()["execution"] == (execution.as_mapping())
    assert (directory / "work.json").read_bytes() == encode_bytes(record.as_mapping())
    assert (directory / "execution.json").read_bytes() == execution_bytes
    with pytest.raises(
        RuntimeError,
        match="work_record_fields_invalid",
    ):
        WorkRecord.from_mapping({**record.as_mapping(), "unknown": True})
    assert sorted(path.name for path in directory.iterdir()) == [
        "after.fsp",
        "before.fsp",
        "construction.json",
        "execution.json",
        "identity.json",
        "input.json",
        "observation.json",
        "solver.log",
        "work.json",
    ]


def test_run_directory_records_and_restores_one_project_execution(
    tmp_path: Path,
) -> None:
    """
    Preserve one completed project execution before work is complete.
    """

    run = RunDirectory(tmp_path / "run")
    directory = run.prepare_candidate(
        "circle-120",
        {"diameter_nm": 120},
        work_identity="sha256:work",
    )
    placement = {
        "lane": {
            "identity": "lane-01",
            "memory_bytes": 16 * 1024**3,
            "physical_cores": 4,
            "uses_smt": False,
        },
    }
    execution = ProjectExecution(
        source="deterministic_test",
        is_native=False,
        project="after.fsp",
        return_code=0,
        placement=placement,
    )

    with pytest.raises(
        RuntimeError,
        match="execution_completed_project_missing",
    ):
        run.record_execution(directory, execution)
    (directory / "after.fsp").write_bytes(b"completed")
    run.record_execution(directory, execution)
    run.record_execution(directory, execution)

    assert run.restore_execution(directory) == execution
    assert (directory / "execution.json").read_bytes() == encode_bytes(
        execution.as_mapping()
    )

    conflicting = ProjectExecution(
        source="conflicting_test",
        is_native=True,
        project="after.fsp",
        return_code=0,
        placement=placement,
    )
    with pytest.raises(RuntimeError, match="artifact_mismatch:execution.json"):
        run.record_execution(directory, conflicting)

    (directory / "execution.json").write_bytes(b"not-json")
    with pytest.raises(RuntimeError, match="artifact_json_invalid"):
        run.restore_execution(directory)


def test_run_directory_names_basis_work_and_distinct_summaries(
    tmp_path: Path,
) -> None:
    """
    Keep solver file vocabulary behind RunDirectory domain operations.
    """

    run = RunDirectory(tmp_path / "run")
    candidate = run.prepare_candidate(
        "rectangle-120-80",
        {"length_nm": 120, "width_nm": 80},
    )
    basis = run.prepare_basis(
        candidate,
        "x",
        {"incident_axis": "x"},
        work_identity="sha256:basis",
    )
    run.record_summary(
        candidate,
        observation={"converted_power": "0.91"},
        log="basis pair complete",
    )

    assert basis.name == "from-x"
    assert run.basis_work(candidate, "x") == basis
    assert (candidate / "summary.json").is_file()
    assert (candidate / "summary.log").is_file()
    assert not (candidate / "observation.json").exists()
    assert not (candidate / "solver.log").exists()
    assert not hasattr(RunDirectory, "read_json")
    assert not hasattr(RunDirectory, "write_json")
    assert not hasattr(RunDirectory, "write_text")


def test_public_periodic_response_accepts_no_parallel_policy() -> None:
    """
    Let callers supply authority, product configuration, and a run only.

    The response accepts one sealed request. Worker count, lane, session,
    permit, and parallelism policy remain product-private.
    """

    assert tuple(inspect.signature(ProductProbe).parameters) == ()
    assert tuple(inspect.signature(LumericalPeriodicResponse).parameters) == (
        "authority",
        "config",
        "run",
    )
    assert tuple(inspect.signature(LumericalPeriodicResponse.open).parameters) == (
        "authority",
        "config",
        "run",
    )
    assert not hasattr(LumericalPeriodicResponse, "open_sweep")
    assert tuple(inspect.signature(LumericalPeriodicResponse.observe).parameters) == (
        "self",
        "request",
    )

from __future__ import annotations

import base64
from collections.abc import Callable, Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextlib import contextmanager
from dataclasses import dataclass
from multiprocessing.connection import Listener
import os
from pathlib import Path
import secrets
import sys
from threading import Condition, Lock
from typing import Any, Protocol

from ...authority import Reference
from ...external_activity import ExternalActivityClosure, _native_activity
from ...work_execution import CapacityRenewalRequired
from ...workstation import (
    LANE_MEMORY_BYTES,
    Command,
    Lane,
    StaleLane,
    Worker,
    start,
)
from .project_execution import ExecutedProject, ProjectExecution
from .qualification import CapacityObservation, LumericalUnavailable
from .session import (
    Session as _TemplateSession,
    _GratingResponsePlanes,
    _OptionalResult,
)


_SESSION_OPEN_TIMEOUT_SECONDS = 30.0


def _native_value(response: object) -> Any:
    """
    Decode one exact worker response envelope.
    """

    if not isinstance(response, Mapping):
        raise RuntimeError("native_session_protocol_drift")
    keys = frozenset(response)
    status = response.get("ok")
    if type(status) is not bool:
        raise RuntimeError("native_session_protocol_drift")
    if status:
        if keys != {"ok", "value"}:
            raise RuntimeError("native_session_protocol_drift")
        return response["value"]
    if keys == {"ok", "unavailable"}:
        reason = response["unavailable"]
        if not isinstance(reason, str) or not reason:
            raise RuntimeError("native_session_protocol_drift")
        raise LumericalUnavailable(reason)
    if keys == {"error", "message", "ok"}:
        error = response["error"]
        message = response["message"]
        if (
            not isinstance(error, str)
            or not error
            or not isinstance(message, str)
        ):
            raise RuntimeError("native_session_protocol_drift")
        raise RuntimeError(f"native_session_failed:{error}:{message}")
    raise RuntimeError("native_session_protocol_drift")


def _capture_cleanup_failure(
    name: str,
    cleanup: Callable[[], object],
    failures: list[BaseException],
) -> None:
    """
    Attempt one cleanup and retain its original failure for direct grouping.
    """

    try:
        cleanup()
    except BaseException as error:
        error.add_note(f"cleanup_operation:{name}")
        failures.append(error)


class _WorkingSession(_TemplateSession, Protocol):
    """
    Defines one placed session that can execute a native project.
    """

    @property
    def placement(self) -> Mapping[str, object]:
        """
        Return verified placement for the session process tree.
        """

        ...

    def solve(self, before: Path, after: Path) -> ProjectExecution:
        """
        Solve and identify one completed native project.
        """

        ...


class _NativeSession:
    """
    Presents one hidden native session owned by a workstation process tree.
    """

    def __init__(
        self,
        connection: Any,
        worker: Worker,
    ) -> None:
        """
        Bind one native connection to its lane-owned workstation worker.
        """

        self._connection = connection
        self._worker = worker
        self._lock = Lock()
        self._is_closed = False

    @property
    def placement(self) -> Mapping[str, object]:
        """
        Return the verified lane placement for this whole process tree.
        """

        return self._worker.as_mapping()

    def create(
        self,
        kind: str,
        name: str,
        properties: Mapping[str, Any],
    ) -> None:
        """
        Create one named native object.
        """

        self._call("create", kind, name, dict(properties))

    def read(
        self,
        name: str,
        properties: tuple[str, ...],
    ) -> Mapping[str, Any]:
        """
        Read named properties from one native object.
        """

        value = self._call("read", name, properties)
        if not isinstance(value, Mapping):
            raise RuntimeError("native_session_read_invalid")
        return value

    def save(self, path: Path) -> None:
        """
        Save the current native project.
        """

        self._call("save", str(path.expanduser().resolve()))

    def result(self, name: str, result_name: str) -> Mapping[str, Any]:
        """
        Read one named native result.
        """

        value = self._call("result", name, result_name)
        if not isinstance(value, Mapping):
            raise RuntimeError("native_session_result_invalid")
        return value

    def optional_result(
        self,
        name: str,
        result_name: str,
    ) -> _OptionalResult:
        """
        Read one optional native result through its strict IPC envelope.
        """

        value = self._call("optional_result", name, result_name)
        return _OptionalResult.from_ipc_mapping(value)

    def prepare_grating_response(self, name: str) -> _GratingResponsePlanes:
        """
        Pin and read the physical planes of one native grating response.
        """

        value = self._call("prepare_grating_response", name)
        return _GratingResponsePlanes.from_ipc_mapping(value)

    def change_maximum_time(
        self,
        name: str,
        maximum_time_fs: int,
    ) -> None:
        """
        Apply the one declared time extension through the worker seam.
        """

        self._call("change_maximum_time", name, maximum_time_fs)

    def reset(self) -> None:
        """
        Clear the native session before its next work item.
        """

        self._call("reset")

    def solve(self, before: Path, after: Path) -> ProjectExecution:
        """
        Solve inside the retained lane and keep the session alive.
        """

        self._call(
            "solve",
            str(before.expanduser().resolve()),
            str(after.expanduser().resolve()),
        )
        return ProjectExecution(
            source="lumerical_fdtd_native_session",
            is_native=True,
            project=after.name,
            return_code=0,
            placement=self.placement,
        )

    def close(self) -> None:
        """
        End the hidden session and every descendant before releasing its lane.
        """

        if self._is_closed:
            return
        failures: list[BaseException] = []
        try:
            self._call("close")
        except BaseException as error:
            failures.append(error)
        try:
            if self._worker.wait(timeout=30) != 0:
                failures.append(
                    RuntimeError("native_session_worker_failed")
                )
        except BaseException as error:
            failures.append(error)
        try:
            self._connection.close()
        except BaseException as error:
            failures.append(error)
        try:
            self._worker.close()
        except BaseException as error:
            failures.append(error)
        self._is_closed = True
        if failures:
            raise BaseExceptionGroup(
                "native_session_close_failed",
                failures,
            )

    def _call(self, operation: str, *arguments: Any) -> Any:
        try:
            with self._lock:
                if self._is_closed:
                    raise RuntimeError("native_session_closed")
                self._connection.send(
                    {
                        "arguments": arguments,
                        "operation": operation,
                    }
                )
                response = self._connection.recv()
        except (EOFError, OSError) as error:
            raise LumericalUnavailable(
                "native_session_unavailable"
            ) from error
        return _native_value(response)


class WorkstationExecution:
    """
    Opens and solves one native session inside its workstation lane.
    """

    def __init__(
        self,
        python_api: Path,
        license_server: str,
        *,
        starter: Callable[[Command, Lane], Worker] = start,
    ) -> None:
        """
        Bind native startup to one configured Python API and license server.
        """

        if not license_server.strip():
            raise ValueError("lumerical_license_server_required")
        self._python_api = python_api.expanduser().resolve()
        self._license_server = license_server
        self._starter = starter

    def _open_session(self, lane: Lane) -> _WorkingSession:
        """
        Place the complete process tree before accepting native readiness.
        """

        key = secrets.token_bytes(32)
        listener = Listener(
            ("127.0.0.1", 0),
            family="AF_INET",
            authkey=key,
        )
        host, port = listener.address
        source_root = Path(__file__).resolve().parents[3]
        inherited = os.environ.get("PYTHONPATH")
        python_path = (
            str(source_root)
            if not inherited
            else os.pathsep.join((str(source_root), inherited))
        )
        command = Command(
            executable=Path(sys.executable),
            arguments=(
                "-m",
                "metacraft.solvers.lumerical_fdtd._lane_worker",
                str(host),
                str(port),
                base64.urlsafe_b64encode(key).decode("ascii"),
                str(self._python_api),
                self._license_server,
            ),
            directory=source_root.parent,
            environment={
                "ANSYSLMD_LICENSE_FILE": self._license_server,
                "PYTHONPATH": python_path,
            },
        )
        worker: Worker | None = None
        connection: Any | None = None
        acceptor = ThreadPoolExecutor(max_workers=1)
        acceptance = acceptor.submit(listener.accept)
        try:
            worker = self._starter(command, lane)
            try:
                connection = acceptance.result(
                    timeout=_SESSION_OPEN_TIMEOUT_SECONDS
                )
            except FutureTimeout as error:
                raise LumericalUnavailable(
                    "native_session_start_timeout"
                ) from error
            assert connection is not None
            assert worker is not None
            try:
                if not connection.poll(_SESSION_OPEN_TIMEOUT_SECONDS):
                    raise LumericalUnavailable(
                        "native_session_ready_timeout"
                    )
                response = connection.recv()
            except (EOFError, OSError) as error:
                raise LumericalUnavailable(
                    "native_session_unavailable"
                ) from error
            if _native_value(response) != "ready":
                raise RuntimeError("native_session_start_failed")
            listener.close()
            acceptor.shutdown(wait=True, cancel_futures=True)
            return _NativeSession(connection, worker)
        except BaseException as primary:
            cleanup_failures: list[BaseException] = []
            _capture_cleanup_failure(
                "listener close",
                listener.close,
                cleanup_failures,
            )
            _capture_cleanup_failure(
                "acceptance cancel",
                acceptance.cancel,
                cleanup_failures,
            )
            _capture_cleanup_failure(
                "acceptor shutdown",
                lambda: acceptor.shutdown(
                    wait=True,
                    cancel_futures=True,
                ),
                cleanup_failures,
            )
            if (
                connection is None
                and acceptance.done()
                and not acceptance.cancelled()
            ):
                try:
                    connection = acceptance.result()
                except BaseException as error:
                    error.add_note(
                        "cleanup_operation:accepted connection recovery"
                    )
                    cleanup_failures.append(error)
            if connection is not None:
                _capture_cleanup_failure(
                    "connection close",
                    connection.close,
                    cleanup_failures,
                )
            if worker is not None:
                _capture_cleanup_failure(
                    "worker close",
                    worker.close,
                    cleanup_failures,
                )
            if cleanup_failures:
                raise BaseExceptionGroup(
                    "native_session_start_terminalization_failed",
                    [primary, *cleanup_failures],
                ) from primary
            raise

    def solve(
        self,
        session: _WorkingSession,
        before: Path,
        after: Path,
    ) -> ExecutedProject:
        execution = session.solve(before, after)
        if not isinstance(execution, ProjectExecution):
            raise TypeError("lumerical_execution_record_required")
        return ExecutedProject(
            session,
            execution,
        )


@dataclass(slots=True)
class _SessionSlot:
    lane: Lane
    session: _WorkingSession | None = None
    session_identity: str | None = None
    uses: int = 0
    is_busy: bool = False


@dataclass(frozen=True, slots=True)
class SessionLease:
    """
    Identifies one temporary use of a retained native session.
    """

    session: _WorkingSession
    session_identity: str
    lane_identity: str
    placement: Mapping[str, object]
    is_reused: bool
    capacity_reference: Reference | None
    capacity: CapacityObservation | None


class SessionPool:
    """
    Retains one hidden native session for every admitted workstation lane.
    """

    def __init__(
        self,
        execution: WorkstationExecution,
        lanes: tuple[Lane, ...],
        *,
        capacity_reference: Reference | None = None,
        capacity: CapacityObservation | None = None,
        _open_session: Callable[[Lane], _WorkingSession] | None = None,
    ) -> None:
        """
        Retain at most one native session for each admitted lane.
        """

        if not lanes:
            raise ValueError("lumerical_session_lanes_required")
        identities = tuple(lane.identity for lane in lanes)
        if len(set(identities)) != len(identities):
            raise ValueError("lumerical_session_lane_duplicate")
        if (capacity_reference is None) != (capacity is None):
            raise ValueError("lumerical_session_capacity_incomplete")
        if capacity is not None and capacity.limit != len(lanes):
            raise ValueError("lumerical_session_capacity_mismatch")
        self._execution = execution
        self._open_session = (
            execution._open_session
            if _open_session is None
            else _open_session
        )
        self._condition = Condition()
        self._slots = [_SessionSlot(lane) for lane in lanes]
        self._capacity_reference = capacity_reference
        self._capacity = capacity
        self._is_closed = False
        self._is_replacing = False
        self._opened_session_count = 0
        self._closed_session_count = 0
        self._started_execution_count = 0
        self._settled_execution_count = 0
        self._opened_placement_count = 0
        self._closed_placement_count = 0

    @contextmanager
    def lease(self) -> Iterator[SessionLease]:
        """
        Lend one session and retire only the session whose work failed.
        """

        with self._condition:
            while True:
                if self._is_closed:
                    raise RuntimeError("lumerical_session_pool_closed")
                if self._is_replacing:
                    self._condition.wait()
                    continue
                slot = next(
                    (
                        candidate
                        for candidate in self._slots
                        if not candidate.is_busy
                    ),
                    None,
                )
                if slot is not None:
                    slot.is_busy = True
                    break
                self._condition.wait()
        failure: BaseException | None = None
        try:
            if slot.session is None:
                try:
                    slot.session = self._open_session(slot.lane)
                except StaleLane as error:
                    raise CapacityRenewalRequired(
                        "local_placement_stale"
                    ) from error
                slot.session_identity = (
                    "session:" + secrets.token_hex(16)
                )
                slot.uses = 0
                with self._condition:
                    self._opened_session_count += 1
                    self._opened_placement_count += 1
            assert slot.session_identity is not None
            session = slot.session
            if session is None:
                raise RuntimeError("lumerical_session_missing")
            placement = session.placement
            if (
                placement.get("effective_cpu_sets") != 4
                or placement.get("job_memory_bytes") != LANE_MEMORY_BYTES
                or placement.get("lane") != slot.lane.as_mapping()
            ):
                raise RuntimeError("lumerical_session_placement_changed")
            lease = SessionLease(
                session=session,
                session_identity=slot.session_identity,
                lane_identity=slot.lane.identity,
                placement=dict(placement),
                is_reused=slot.uses > 0,
                capacity_reference=self._capacity_reference,
                capacity=self._capacity,
            )
            session.reset()
            slot.uses += 1
            yield lease
        except BaseException as error:
            failure = error
            raise
        finally:
            close_error: BaseException | None = None
            if failure is not None and slot.session is not None:
                try:
                    self._close_session(slot.session)
                except BaseException as error:
                    close_error = error
                finally:
                    slot.session = None
                    slot.session_identity = None
                    slot.uses = 0
            with self._condition:
                slot.is_busy = False
                self._condition.notify()
            if close_error is not None:
                assert failure is not None
                raise BaseExceptionGroup(
                    "lumerical_discarded_session_close_failed",
                    [failure, close_error],
                ) from failure

    def solve(
        self,
        lease: SessionLease,
        before: Path,
        after: Path,
    ) -> ExecutedProject:
        """
        Solve through the execution owner of this leased native session.
        """

        with self._condition:
            self._started_execution_count += 1
        try:
            return self._execution.solve(lease.session, before, after)
        finally:
            with self._condition:
                self._settled_execution_count += 1

    def uses(
        self,
        capacity_reference: Reference,
        capacity: CapacityObservation,
    ) -> bool:
        """
        Report whether new leases carry this exact admitted capacity.
        """

        with self._condition:
            return (
                self._capacity_reference == capacity_reference
                and self._capacity == capacity
            )

    def replace(
        self,
        *,
        lanes: tuple[Lane, ...],
        capacity_reference: Reference,
        capacity: CapacityObservation,
    ) -> None:
        """
        Replace lanes and capacity together after every active lease ends.
        """

        if not lanes:
            raise ValueError("lumerical_session_lanes_required")
        identities = tuple(lane.identity for lane in lanes)
        if len(set(identities)) != len(identities):
            raise ValueError("lumerical_session_lane_duplicate")
        if capacity.limit != len(lanes):
            raise ValueError("lumerical_session_capacity_mismatch")
        with self._condition:
            if self._is_closed:
                raise RuntimeError("lumerical_session_pool_closed")
            while self._is_replacing:
                self._condition.wait()
            self._is_replacing = True
            while any(slot.is_busy for slot in self._slots):
                self._condition.wait()
            sessions = tuple(
                slot.session
                for slot in self._slots
                if slot.session is not None
            )
        failures: list[BaseException] = []
        for session in sessions:
            try:
                self._close_session(session)
            except BaseException as error:
                failures.append(error)
        with self._condition:
            self._slots = [_SessionSlot(lane) for lane in lanes]
            self._capacity_reference = capacity_reference
            self._capacity = capacity
            self._is_replacing = False
            self._condition.notify_all()
        if failures:
            raise BaseExceptionGroup(
                "lumerical_session_replacement_failed",
                failures,
            )

    def close(self) -> ExternalActivityClosure:
        """
        Close every retained session once no lease remains active.
        """

        with self._condition:
            while self._is_replacing:
                self._condition.wait()
            self._is_closed = True
            while any(slot.is_busy for slot in self._slots):
                self._condition.wait()
            sessions = tuple(
                slot.session
                for slot in self._slots
                if slot.session is not None
            )
            for slot in self._slots:
                slot.session = None
                slot.session_identity = None
                slot.uses = 0
        failures: list[BaseException] = []
        for session in sessions:
            try:
                self._close_session(session)
            except BaseException as error:
                failures.append(error)
        if failures:
            raise BaseExceptionGroup(
                "lumerical_session_pool_close_failed",
                failures,
            )
        return self._activity_closure()

    def _close_session(self, session: _WorkingSession) -> None:
        """
        Close one retained product session and its local placement.
        """

        try:
            session.close()
        finally:
            with self._condition:
                self._closed_session_count += 1
                self._closed_placement_count += 1

    def _activity_closure(self) -> ExternalActivityClosure:
        """
        Return owner-produced counts after the pool has fully closed.
        """

        if (
            self._opened_session_count != self._closed_session_count
            or self._started_execution_count
            != self._settled_execution_count
            or self._opened_placement_count
            != self._closed_placement_count
        ):
            raise RuntimeError("lumerical_session_pool_activity_unsettled")
        return _native_activity(
            external_execution_count=self._started_execution_count,
            product_session_count=self._opened_session_count,
            local_placement_count=self._opened_placement_count,
        )

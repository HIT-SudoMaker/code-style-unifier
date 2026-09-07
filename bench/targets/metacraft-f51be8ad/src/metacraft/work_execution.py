from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import json
from time import sleep
from typing import Generic, NoReturn, Protocol, TypeVar

from .authority import Document, Reference
from .authority.session import (
    AuthoritySession,
    PermitReservationWaiting,
)
from .canonical import encode_bytes
from .external_activity import (
    ExternalActivityClosure,
    _native_activity,
)


PERMITTED_WORK_SCHEMA = "metacraft.science.permitted_work"
CLOSED_WORK_SCHEMA = "metacraft.science.closed_work"


class Capacity(Protocol):
    """
    Describe one fresh bounded work domain.
    """

    @property
    def scope(self) -> str:
        """
        Return the immutable work-capacity scope.
        """

        ...

    @property
    def limit(self) -> int:
        """
        Return the maximum concurrent work count.
        """

        ...

    @property
    def fresh_until(self) -> datetime:
        """
        Return the instant after which new work cannot be admitted.
        """

        ...

    def is_fresh_at(self, value: datetime) -> bool:
        """
        Report whether this capacity admits work at the given instant.
        """

        ...

    def as_mapping(self) -> Mapping[str, object]:
        """
        Return the exact capacity evidence admitted by Authority.
        """

        ...


ObservationValue = TypeVar("ObservationValue")


@dataclass(frozen=True, slots=True)
class WorkAttempt:
    """
    Tell product observation whether incomplete prior work is being resumed.
    """

    is_resuming: bool


@dataclass(frozen=True, slots=True)
class WorkRequest(Generic[ObservationValue]):
    """
    Bind one immutable work identity to its typed settlement operation.
    """

    work_identity: str
    observe: Callable[[WorkAttempt], ObservationValue]
    encode: Callable[[ObservationValue], Document]
    restore: Callable[[Document], ObservationValue]

    def __post_init__(self) -> None:
        """
        Require one named work identity.
        """

        if not self.work_identity.strip():
            raise ValueError("work_identity_required")


@dataclass(frozen=True, slots=True)
class CompletedWork(Generic[ObservationValue]):
    """
    Return one fresh or restored observation with its exact Rust receipt.
    """

    work_identity: str
    observation: ObservationValue
    body_reference: Reference
    receipt_reference: Reference


@dataclass(frozen=True, slots=True)
class CompletedWorkExecution(Generic[ObservationValue]):
    """
    Return completed work with exact activity owned by this execute call.
    """

    items: tuple[CompletedWork[ObservationValue], ...]
    activity_closure: ExternalActivityClosure


class WorkExecutionFault(BaseExceptionGroup):
    """
    Retain one direct work fault beside its owner-produced activity evidence.
    """

    activity_closure: ExternalActivityClosure | None

    def __new__(
        cls,
        fault: BaseException,
        activity_closure: ExternalActivityClosure | None,
    ) -> WorkExecutionFault:
        """
        Build one explicit carrier whose member is the unchanged fault.
        """

        instance = super().__new__(
            cls,
            f"work_execution_failed:{type(fault).__name__}:{fault}",
            (fault,),
        )
        instance.activity_closure = activity_closure
        return instance

    def __init__(
        self,
        fault: BaseException,
        activity_closure: ExternalActivityClosure | None,
    ) -> None:
        """
        Leave BaseExceptionGroup initialization to ``__new__``.
        """

        pass

    @property
    def fault(self) -> BaseException:
        """
        Return the original direct or grouped fault unchanged.
        """

        return self.exceptions[0]


@dataclass(frozen=True, slots=True)
class WorkWaiting(Generic[ObservationValue]):
    """
    Report work that cannot start under fresh positive capacity.
    """

    reason: str
    work_identities: tuple[str, ...]
    completed: tuple[CompletedWork[ObservationValue], ...] = ()
    activity_closure: ExternalActivityClosure = ExternalActivityClosure.none()


@dataclass(frozen=True, slots=True)
class CapacityRenewalWaiting:
    """
    Report that a capacity source cannot establish a fresh positive bound.
    """

    reason: str


class CapacityRenewalRequired(RuntimeError):
    """
    Ask WorkExecution to replace stale local placement before retrying work.
    """


class _PermitReservationDeferred(RuntimeError):
    """
    Classify permits closed after bounded sibling reservation contention.
    """


@dataclass(frozen=True, slots=True)
class _AcquiredChunk(Generic[ObservationValue]):
    permitted: tuple[
        tuple[WorkRequest[ObservationValue], bool, Reference],
        ...,
    ]
    completed: tuple[CompletedWork[ObservationValue], ...]
    is_waiting: bool = False
    is_capacity_renewal_required: bool = False


@dataclass(slots=True)
class _WorkActivity:
    """
    Count permits acquired by one current execute call.
    """

    acquired_work_count: int = 0
    settled_work_count: int = 0

    def closure(self) -> ExternalActivityClosure | None:
        """
        Return settled evidence, or no evidence when cleanup did not close.
        """

        if self.acquired_work_count != self.settled_work_count:
            return None
        return _native_activity(
            authority_work_count=self.acquired_work_count,
        )


class WorkExecution:
    """
    Own complete permit-to-receipt lives behind one bounded execute method.
    """

    __slots__ = (
        "_capacity",
        "_capacity_reference",
        "_now",
        "_permit_attempts",
        "_renew_capacity",
        "_session",
        "_wait",
    )

    def __init__(
        self,
        session: AuthoritySession,
        *,
        capacity_reference: Reference,
        capacity: Capacity,
        renew_capacity: (
            Callable[
                [],
                tuple[Reference, Capacity] | CapacityRenewalWaiting,
            ]
            | None
        ) = None,
        _now: Callable[[], datetime] = lambda: datetime.now(UTC),
        _wait: Callable[[float], object] = sleep,
        _permit_attempts: int = 32,
    ) -> None:
        """
        Bind one Authority session to its exact admitted capacity.
        """

        if _permit_attempts <= 0:
            raise ValueError("permit_attempts_invalid")
        self._session = session
        self._capacity_reference = capacity_reference
        self._capacity = capacity
        self._renew_capacity = renew_capacity
        self._now = _now
        self._wait = _wait
        self._permit_attempts = _permit_attempts

    @property
    def capacity_scope(self) -> str:
        """
        Return the immutable work domain this execution coordinates.
        """

        return self._capacity.scope

    @property
    def capacity_reference(self) -> Reference:
        """
        Return the exact current capacity reference used for new permits.
        """

        return self._capacity_reference

    def execute(
        self,
        requests: tuple[WorkRequest[ObservationValue], ...],
    ) -> CompletedWorkExecution[ObservationValue] | WorkWaiting[ObservationValue]:
        """
        Restore or observe each work identity and close every acquired permit.
        """

        activity = _WorkActivity()
        try:
            outcome = self._execute_requests(requests, activity)
        except BaseException as error:
            if activity.acquired_work_count == 0:
                raise
            raise WorkExecutionFault(
                error,
                activity.closure(),
            ) from error
        if isinstance(outcome, WorkWaiting):
            closure = activity.closure()
            if closure is None:
                raise RuntimeError("work_activity_unsettled")
            return replace(
                outcome,
                activity_closure=closure,
            )
        closure = activity.closure()
        if closure is None:
            raise RuntimeError("work_activity_unsettled")
        return CompletedWorkExecution(outcome, closure)

    def _execute_requests(
        self,
        requests: tuple[WorkRequest[ObservationValue], ...],
        activity: _WorkActivity,
    ) -> tuple[CompletedWork[ObservationValue], ...] | WorkWaiting[ObservationValue]:
        """
        Run the one public lifecycle while retaining internal counts.
        """

        if not requests:
            return ()
        self._validate_capacity_generation(
            self._capacity_reference,
            self._capacity,
        )
        identities = tuple(request.work_identity for request in requests)
        if len(set(identities)) != len(identities):
            raise ValueError("work_request_identity_duplicate")
        self._close_expired_permits()
        restored = {
            item.work_identity: item
            for request in requests
            if (item := self._restore(request)) is not None
        }
        pending = tuple(
            request for request in requests if request.work_identity not in restored
        )
        if not pending:
            return tuple(restored[identity] for identity in identities)

        completed = dict(restored)
        failures: list[Exception] = []
        remaining = list(pending)
        while remaining:
            self._close_expired_permits()
            if self._capacity.limit <= 0 or not self._capacity.is_fresh_at(self._now()):
                if failures:
                    _raise_work_failures(failures)
                waiting = self._renew(
                    tuple(item.work_identity for item in remaining),
                    tuple(completed.values()),
                )
                if waiting is not None:
                    return waiting
            chunk = tuple(remaining[: self._capacity.limit])
            remaining = remaining[len(chunk) :]
            acquisition = self._acquire_chunk(chunk, activity)
            completed.update(
                (item.work_identity, item) for item in acquisition.completed
            )
            if acquisition.is_waiting:
                if failures:
                    _raise_work_failures(failures)
                return WorkWaiting(
                    "permit_unavailable",
                    tuple(
                        item.work_identity
                        for item in (
                            *(
                                request
                                for request in chunk
                                if request.work_identity not in completed
                            ),
                            *remaining,
                        )
                    ),
                    tuple(completed.values()),
                )
            if acquisition.is_capacity_renewal_required:
                if failures:
                    _raise_work_failures(failures)
                waiting = self._renew(
                    tuple(
                        item.work_identity
                        for item in (*chunk, *remaining)
                        if item.work_identity not in completed
                    ),
                    tuple(completed.values()),
                )
                if waiting is not None:
                    return waiting
                remaining = [
                    *(item for item in chunk if item.work_identity not in completed),
                    *remaining,
                ]
                continue
            permitted = acquisition.permitted
            if not permitted:
                continue
            try:
                with ThreadPoolExecutor(max_workers=len(permitted)) as workers:
                    observed = []
                    for request, is_resuming, permit in permitted:
                        future = workers.submit(
                            request.observe,
                            WorkAttempt(is_resuming=is_resuming),
                        )
                        observed.append((request, permit, future))
            except BaseException as error:
                close_failures = self._close_acquired(
                    list(permitted),
                    error,
                    activity,
                )
                if close_failures:
                    if isinstance(error, Exception):
                        raise ExceptionGroup(
                            "work_terminalization_failed",
                            [error, *close_failures],
                        ) from error
                    raise BaseExceptionGroup(
                        "work_terminalization_failed",
                        [error, *close_failures],
                    ) from error
                raise
            deferred: list[WorkRequest[ObservationValue]] = []
            for index, (request, permit, future) in enumerate(observed):
                is_permit_settled = False
                try:
                    observation = future.result()
                    document = request.encode(observation)
                    decision = self._session.admit_receipt(
                        document,
                        permit_reference=permit,
                    )
                    activity.settled_work_count += 1
                    is_permit_settled = True
                    if (
                        decision.body_reference is None
                        or decision.proposal_reference is None
                    ):
                        raise RuntimeError("work_receipt_reference_missing")
                except CapacityRenewalRequired as error:
                    if not is_permit_settled:
                        try:
                            self._close_failed(
                                permit,
                                request.work_identity,
                                error,
                                activity,
                            )
                        except Exception as close_error:
                            failures.append(close_error)
                    deferred.append(request)
                    continue
                except Exception as error:
                    failures.append(error)
                    if not is_permit_settled:
                        try:
                            self._close_failed(
                                permit,
                                request.work_identity,
                                error,
                                activity,
                            )
                        except Exception as close_error:
                            failures.append(close_error)
                    continue
                except BaseException as error:
                    close_failures = self._close_acquired(
                        list(permitted[index:]),
                        error,
                        activity,
                    )
                    if close_failures:
                        raise BaseExceptionGroup(
                            "work_terminalization_failed",
                            [error, *close_failures],
                        ) from error
                    raise
                completed[request.work_identity] = CompletedWork(
                    request.work_identity,
                    observation,
                    decision.body_reference,
                    decision.proposal_reference,
                )
            if deferred:
                waiting = self._renew(
                    tuple(item.work_identity for item in deferred),
                    tuple(completed.values()),
                )
                if waiting is not None:
                    if failures:
                        _raise_work_failures(failures)
                    return WorkWaiting(
                        waiting.reason,
                        (
                            *waiting.work_identities,
                            *(item.work_identity for item in remaining),
                        ),
                        waiting.completed,
                    )
                remaining = [*deferred, *remaining]
                self._wait(0.05)
        if failures:
            _raise_work_failures(failures)
        return tuple(completed[identity] for identity in identities)

    def _renew(
        self,
        pending: tuple[str, ...],
        completed: tuple[CompletedWork[ObservationValue], ...],
    ) -> WorkWaiting[ObservationValue] | None:
        reason = (
            "capacity_not_positive" if self._capacity.limit <= 0 else "capacity_stale"
        )
        if self._renew_capacity is None:
            return WorkWaiting(reason, pending, completed)
        renewed = self._renew_capacity()
        if isinstance(renewed, CapacityRenewalWaiting):
            return WorkWaiting(renewed.reason, pending, completed)
        reference, capacity = renewed
        if capacity.scope != self._capacity.scope:
            raise RuntimeError("capacity_scope_changed")
        if capacity.limit <= 0:
            return WorkWaiting(
                "capacity_not_positive",
                pending,
                completed,
            )
        if not capacity.is_fresh_at(self._now()):
            return WorkWaiting("capacity_stale", pending, completed)
        current = {
            item.key: item.body_reference for item in self._session.observe().current
        }.get(f"capacity:{capacity.scope}")
        if current != reference:
            raise RuntimeError("capacity_reference_not_current")
        self._validate_capacity_generation(reference, capacity)
        self._capacity_reference = reference
        self._capacity = capacity
        return None

    def _validate_capacity_generation(
        self,
        reference: Reference,
        capacity: Capacity,
    ) -> None:
        """
        Bind the in-memory freshness boundary to exact admitted qualification.
        """

        fresh_until = capacity.fresh_until
        if fresh_until.tzinfo is None:
            raise RuntimeError("capacity_fresh_until_timezone_missing")
        mapping = capacity.as_mapping()
        expected_fresh_until = (
            fresh_until.astimezone(UTC)
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )
        if (
            not isinstance(mapping, Mapping)
            or mapping.get("scope") != capacity.scope
            or type(mapping.get("limit")) is not int
            or mapping.get("limit") != capacity.limit
            or mapping.get("fresh_until") != expected_fresh_until
        ):
            raise RuntimeError("capacity_observation_invalid")
        expected_observation = encode_bytes(mapping)
        try:
            body = self._session.fetch(reference)
            decoded = json.loads(body)
            if encode_bytes(decoded) != body or not isinstance(decoded, dict):
                raise ValueError("capacity_not_canonical")
            if set(decoded) != {
                "limit",
                "qualification_references",
                "schema_identifier",
                "scope",
            }:
                raise ValueError("capacity_fields_invalid")
            if (
                decoded["schema_identifier"] != "metacraft.authority.capacity"
                or decoded["scope"] != capacity.scope
                or type(decoded["limit"]) is not int
                or decoded["limit"] != capacity.limit
                or not isinstance(
                    decoded["qualification_references"],
                    list,
                )
            ):
                raise ValueError("capacity_values_invalid")
            qualifications = tuple(
                Reference.from_mapping(item)
                for item in decoded["qualification_references"]
            )
        except (TypeError, ValueError) as error:
            raise RuntimeError("capacity_document_invalid") from error
        if not any(
            self._session.fetch(qualification) == expected_observation
            for qualification in qualifications
        ):
            raise RuntimeError("capacity_observation_mismatch")

    def _restore(
        self,
        request: WorkRequest[ObservationValue],
    ) -> CompletedWork[ObservationValue] | None:
        restored: list[CompletedWork[ObservationValue]] = []
        for permit in self._session.observe().permits:
            if permit.scope != self._capacity.scope:
                continue
            if self._permit_work_identity(permit.body_reference) != (
                request.work_identity
            ):
                continue
            if permit.state != "closed" or permit.close_reason != "consumed":
                continue
            if (
                permit.receipt_body_reference is None
                or permit.receipt_reference is None
            ):
                raise RuntimeError("work_receipt_reference_missing")
            document = Document.from_bytes(
                self._session.fetch(permit.receipt_body_reference)
            )
            observation = request.restore(document)
            restored_document = request.encode(observation)
            if restored_document.to_bytes() != document.to_bytes():
                raise RuntimeError("work_receipt_observation_mismatch")
            restored.append(
                CompletedWork(
                    request.work_identity,
                    observation,
                    permit.receipt_body_reference,
                    permit.receipt_reference,
                )
            )
        if len(restored) > 1:
            raise RuntimeError("work_receipt_duplicate")
        return restored[0] if restored else None

    def _is_resuming(
        self,
        request: WorkRequest[ObservationValue],
    ) -> bool:
        for permit in self._session.observe().permits:
            if permit.scope != self._capacity.scope:
                continue
            if self._permit_work_identity(permit.body_reference) != (
                request.work_identity
            ):
                continue
            if permit.state == "closed" and permit.close_reason in {
                "expired",
                "revoked",
            }:
                return True
        return False

    def _reserve(
        self,
        request: WorkRequest[ObservationValue],
    ) -> Reference | CompletedWork[ObservationValue] | CapacityRenewalRequired | None:
        for _attempt in range(self._permit_attempts):
            reservation = self._session.reserve_work(
                Document(
                    PERMITTED_WORK_SCHEMA,
                    {"work": request.work_identity},
                ),
                capacity_reference=self._capacity_reference,
                scope=self._capacity.scope,
                expires_at=self._permit_expiry(request),
            )
            if isinstance(reservation, Reference):
                return reservation
            if reservation.reason == "permit_capacity_not_current":
                return CapacityRenewalRequired("permit_capacity_not_current")
            if reservation.reason == "permit_already_closed":
                restored = self._restore(request)
                if restored is not None:
                    return restored
            self._wait(0.05)
        return None

    def _acquire_chunk(
        self,
        chunk: tuple[WorkRequest[ObservationValue], ...],
        activity: _WorkActivity,
    ) -> _AcquiredChunk[ObservationValue]:
        """
        Reserve one bounded chunk or close every sibling already reserved.
        """

        acquired: list[tuple[WorkRequest[ObservationValue], bool, Reference]] = []
        completed: list[CompletedWork[ObservationValue]] = []
        try:
            for request in chunk:
                is_resuming = self._is_resuming(request)
                reservation = self._reserve(request)
                if isinstance(reservation, CompletedWork):
                    completed.append(reservation)
                    continue
                if isinstance(reservation, CapacityRenewalRequired):
                    close_failures = self._close_acquired(
                        acquired,
                        reservation,
                        activity,
                    )
                    acquired.clear()
                    if close_failures:
                        raise ExceptionGroup(
                            "capacity_renewal_close_failed",
                            close_failures,
                        )
                    return _AcquiredChunk(
                        (),
                        tuple(completed),
                        is_capacity_renewal_required=True,
                    )
                if reservation is None:
                    failure = _PermitReservationDeferred("permit_reservation_deferred")
                    close_failures = self._close_acquired(
                        acquired,
                        failure,
                        activity,
                    )
                    acquired.clear()
                    if close_failures:
                        raise ExceptionGroup(
                            "permit_reservation_close_failed",
                            close_failures,
                        )
                    return _AcquiredChunk(
                        (),
                        tuple(completed),
                        is_waiting=True,
                    )
                acquired.append((request, is_resuming, reservation))
                activity.acquired_work_count += 1
        except BaseException as error:
            close_failures = self._close_acquired(
                acquired,
                error,
                activity,
            )
            if close_failures:
                if isinstance(error, Exception):
                    raise ExceptionGroup(
                        "permit_acquisition_failed",
                        [error, *close_failures],
                    ) from error
                raise BaseExceptionGroup(
                    "permit_acquisition_failed",
                    [error, *close_failures],
                ) from error
            raise
        return _AcquiredChunk(tuple(acquired), tuple(completed))

    def _permit_expiry(
        self,
        request: WorkRequest[ObservationValue],
    ) -> datetime:
        """
        Derive one stable lease identity per capacity and retry attempt.
        """

        fresh_until = self._capacity.fresh_until
        if fresh_until.tzinfo is None:
            raise RuntimeError("capacity_fresh_until_timezone_missing")
        retry_index = 0
        for permit in self._session.observe().permits:
            if (
                permit.scope != self._capacity.scope
                or permit.capacity_reference != self._capacity_reference
            ):
                continue
            if self._permit_work_identity(permit.body_reference) != (
                request.work_identity
            ):
                continue
            if permit.state == "closed" and permit.close_reason in {
                "expired",
                "revoked",
            }:
                retry_index += 1
        return fresh_until.astimezone(UTC) + timedelta(
            hours=1,
            microseconds=retry_index,
        )

    def _close_acquired(
        self,
        acquired: list[tuple[WorkRequest[ObservationValue], bool, Reference]],
        failure: BaseException,
        activity: _WorkActivity,
    ) -> list[Exception]:
        close_failures: list[Exception] = []
        for request, _is_resuming, permit in acquired:
            try:
                self._close_failed(
                    permit,
                    request.work_identity,
                    failure,
                    activity,
                )
            except Exception as close_error:
                close_failures.append(close_error)
        return close_failures

    def _close_expired_permits(self) -> None:
        """
        Close replayed expired permits before they can block a fresh work life.
        """

        now = self._now()
        for permit in self._session.observe().permits:
            if (
                permit.state != "open"
                or permit.scope != self._capacity.scope
                or _permit_expiry(permit.expires_at) > now
            ):
                continue
            work_identity = self._permit_work_identity(permit.body_reference)
            self._session.close_permit(
                Document(
                    CLOSED_WORK_SCHEMA,
                    {
                        "failure": "PermitExpired",
                        "work": work_identity,
                    },
                ),
                permit_reference=permit.permit_reference,
                reason="expired",
                is_already_closed_allowed=True,
            )

    def _permit_work_identity(self, reference: Reference) -> str:
        try:
            document = Document.from_bytes(self._session.fetch(reference))
        except (TypeError, ValueError) as error:
            raise RuntimeError("work_permit_document_invalid") from error
        work_identity = document.values.get("work")
        if (
            document.schema_identifier != PERMITTED_WORK_SCHEMA
            or set(document.values) != {"work"}
            or not isinstance(work_identity, str)
            or not work_identity.strip()
        ):
            raise RuntimeError("work_permit_document_invalid")
        return work_identity

    def _close_failed(
        self,
        permit: Reference,
        work_identity: str,
        failure: BaseException,
        activity: _WorkActivity,
    ) -> None:
        self._session.close_permit(
            Document(
                CLOSED_WORK_SCHEMA,
                {
                    "failure": type(failure).__name__,
                    "work": work_identity,
                },
            ),
            permit_reference=permit,
            reason="revoked",
        )
        activity.settled_work_count += 1


def _permit_expiry(value: str) -> datetime:
    expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if expiry.tzinfo is None:
        raise RuntimeError("permit_expiry_timezone_missing")
    return expiry.astimezone(UTC)


def _raise_work_failures(failures: list[Exception]) -> NoReturn:
    """
    Preserve one direct fault and group only genuinely multiple failures.
    """

    if len(failures) == 1:
        raise failures[0]
    raise ExceptionGroup("work_failed", failures)

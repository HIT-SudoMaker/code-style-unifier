from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Lock
from typing import Protocol, TypeVar

import pytest

from metacraft.authority import Authority, Document, Reference
from metacraft.authority.session import (
    AuthoritySession,
    PermitReservationWaiting,
)
from metacraft.canonical import encode_bytes
from metacraft.work_execution import (
    PERMITTED_WORK_SCHEMA,
    CapacityRenewalWaiting,
    CapacityRenewalRequired,
    CompletedWork,
    CompletedWorkExecution,
    WorkAttempt,
    WorkExecution,
    WorkExecutionFault,
    WorkRequest,
    WorkWaiting,
)


@dataclass(frozen=True, slots=True)
class _Capacity:
    scope: str
    limit: int
    fresh_until: datetime

    def is_fresh_at(self, value: datetime) -> bool:
        return value <= self.fresh_until

    def as_mapping(self) -> dict[str, object]:
        return {
            "fresh_until": self.fresh_until.astimezone(UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "limit": self.limit,
            "scope": self.scope,
        }


@dataclass(frozen=True, slots=True)
class _Observation:
    status: str

    def as_mapping(self) -> dict[str, object]:
        return {"status": self.status}


class _MappableObservation(Protocol):
    def as_mapping(self) -> Mapping[str, object]: ...


_FixtureObservation = TypeVar(
    "_FixtureObservation",
    bound=_MappableObservation,
)


def _observation_request(
    work_identity: str,
    observation_schema: str,
    observe: Callable[[WorkAttempt], _FixtureObservation],
    restore: Callable[[Document], _FixtureObservation],
) -> WorkRequest[_FixtureObservation]:
    return WorkRequest(
        work_identity=work_identity,
        observe=observe,
        encode=lambda observation: Document(
            observation_schema,
            observation.as_mapping(),
        ),
        restore=restore,
    )


def _encode_observation(observation: _Observation) -> Document:
    return Document("fixture.observation", observation.as_mapping())


def _restore_observation(document: Document) -> _Observation:
    if document.schema_identifier != "fixture.observation":
        raise ValueError("fixture_observation_schema_invalid")
    return _Observation(str(document.values["status"]))


def _admit_capacity(
    session: AuthoritySession,
    capacity: _Capacity,
    *,
    qualification: Reference,
    supersedes: Reference | None = None,
) -> Reference:
    observation = session.admit_object(
        encode_bytes(capacity.as_mapping()),
        media_type="application/vnd.metacraft.fixture-capacity+json",
        descriptive_metadata={"object_kind": "FixtureCapacity"},
    )
    return session.admit_capacity(
        scope=capacity.scope,
        limit=capacity.limit,
        qualification_references=(qualification, observation),
        supersedes=supersedes,
    )


def _execution(
    tmp_path: Path,
    *,
    limit: int = 1,
) -> tuple[Authority, WorkExecution]:
    authority, session, capacity, capacity_reference = _capacity_setup(
        tmp_path,
        limit=limit,
    )
    return authority, WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
    )


def _capacity_setup(
    tmp_path: Path,
    *,
    limit: int = 1,
    fresh_until: datetime | None = None,
) -> tuple[Authority, AuthoritySession, _Capacity, Reference]:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    qualification = session.admit_document(
        Document("fixture.qualification", {"qualified": True})
    )
    capacity = _Capacity(
        "solver:fixture",
        limit,
        fresh_until or datetime.now(UTC) + timedelta(minutes=5),
    )
    capacity_reference = _admit_capacity(
        session,
        capacity,
        qualification=qualification,
    )
    return authority, session, capacity, capacity_reference


def test_fresh_work_returns_one_consumed_completed_work(
    tmp_path: Path,
) -> None:
    authority, execution = _execution(tmp_path)

    outcome = execution.execute(
        (
            _observation_request(
                work_identity="cell-1",
                observation_schema="fixture.observation",
                observe=lambda _attempt: _Observation("complete"),
                restore=_restore_observation,
            ),
        )
    )

    assert isinstance(outcome, CompletedWorkExecution)
    assert len(outcome.items) == 1
    completed = outcome.items[0]
    assert isinstance(completed, CompletedWork)
    assert completed.work_identity == "cell-1"
    assert completed.observation == _Observation("complete")
    permit = authority.view().permits[0]
    assert permit.close_reason == "consumed"
    assert completed.body_reference == permit.receipt_body_reference
    assert completed.receipt_reference == permit.receipt_reference


def test_consumed_work_restores_without_observing_again(
    tmp_path: Path,
) -> None:
    _authority, execution = _execution(tmp_path)
    observations = 0

    def observe(_attempt: WorkAttempt) -> _Observation:
        nonlocal observations
        observations += 1
        return _Observation("complete")

    request = _observation_request(
        work_identity="cell-1",
        observation_schema="fixture.observation",
        observe=observe,
        restore=_restore_observation,
    )
    first = execution.execute((request,))
    restored = execution.execute((request,))

    assert isinstance(first, CompletedWorkExecution)
    assert isinstance(restored, CompletedWorkExecution)
    assert restored.items == first.items
    assert observations == 1


def test_consumed_work_restores_an_alternate_typed_outcome_without_reexecution(
    tmp_path: Path,
) -> None:
    @dataclass(frozen=True, slots=True)
    class Incomplete:
        reason: str

    observations = 0
    _authority, execution = _execution(tmp_path)

    def observe(_attempt: WorkAttempt) -> Incomplete:
        nonlocal observations
        observations += 1
        return Incomplete("time_budget_exhausted")

    def encode(outcome: Incomplete) -> Document:
        return Document("fixture.incomplete", {"reason": outcome.reason})

    def restore(document: Document) -> Incomplete:
        if document.schema_identifier != "fixture.incomplete":
            raise ValueError("fixture_incomplete_schema_invalid")
        return Incomplete(str(document.values["reason"]))

    request = WorkRequest(
        work_identity="cell-incomplete",
        observe=observe,
        encode=encode,
        restore=restore,
    )

    first = execution.execute((request,))
    restored = execution.execute((request,))

    assert isinstance(first, CompletedWorkExecution)
    assert isinstance(restored, CompletedWorkExecution)
    assert restored.items == first.items
    assert restored.items[0].observation == Incomplete("time_budget_exhausted")
    assert observations == 1


def test_failed_work_closes_its_permit_while_sibling_keeps_receipt(
    tmp_path: Path,
) -> None:
    authority, execution = _execution(tmp_path, limit=2)

    def fail(_attempt: WorkAttempt) -> _Observation:
        raise RuntimeError("native failure")

    with pytest.raises(WorkExecutionFault) as raised:
        execution.execute(
            (
                _observation_request(
                    "cell-failed",
                    "fixture.observation",
                    fail,
                    _restore_observation,
                ),
                _observation_request(
                    "cell-complete",
                    "fixture.observation",
                    lambda _attempt: _Observation("complete"),
                    _restore_observation,
                ),
            )
        )
    assert isinstance(raised.value.fault, RuntimeError)
    assert str(raised.value.fault) == "native failure"

    permits = authority.view().permits
    assert tuple(sorted(str(item.close_reason) for item in permits)) == (
        "consumed",
        "revoked",
    )


def test_revoked_work_retries_as_one_resuming_attempt(
    tmp_path: Path,
) -> None:
    _authority, execution = _execution(tmp_path)

    def fail(_attempt: WorkAttempt) -> _Observation:
        raise RuntimeError("interrupted")

    failed = _observation_request(
        "cell-1",
        "fixture.observation",
        fail,
        _restore_observation,
    )
    with pytest.raises(WorkExecutionFault) as raised:
        execution.execute((failed,))
    assert isinstance(raised.value.fault, RuntimeError)

    attempts: list[WorkAttempt] = []

    def resume(attempt: WorkAttempt) -> _Observation:
        attempts.append(attempt)
        return _Observation("complete")

    completed = execution.execute(
        (
            _observation_request(
                "cell-1",
                "fixture.observation",
                resume,
                _restore_observation,
            ),
        )
    )

    assert isinstance(completed, CompletedWorkExecution)
    assert attempts == [WorkAttempt(is_resuming=True)]


def test_stale_capacity_is_renewed_before_pending_work(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    qualification = session.admit_document(
        Document("fixture.qualification", {"qualified": True})
    )
    stale = _Capacity(
        "solver:fixture",
        1,
        datetime.now(UTC) - timedelta(seconds=1),
    )
    stale_reference = _admit_capacity(
        session,
        stale,
        qualification=qualification,
    )
    renewed = _Capacity(
        stale.scope,
        1,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    renewals = 0

    def renew() -> tuple[Reference, _Capacity]:
        nonlocal renewals
        renewals += 1
        reference = _admit_capacity(
            session,
            renewed,
            qualification=qualification,
            supersedes=stale_reference,
        )
        return reference, renewed

    execution = WorkExecution(
        session,
        capacity_reference=stale_reference,
        capacity=stale,
        renew_capacity=renew,
    )
    outcome = execution.execute(
        (
            _observation_request(
                "cell-1",
                "fixture.observation",
                lambda _attempt: _Observation("complete"),
                _restore_observation,
            ),
        )
    )

    assert not isinstance(outcome, WorkWaiting)
    assert renewals == 1


def test_stale_placement_closes_renews_and_resumes_same_work(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    qualification = session.admit_document(
        Document("fixture.qualification", {"qualified": True})
    )
    capacity = _Capacity(
        "solver:fixture",
        1,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    capacity_reference = _admit_capacity(
        session,
        capacity,
        qualification=qualification,
    )
    renewals = 0

    def renew() -> tuple[Reference, _Capacity]:
        nonlocal capacity_reference, renewals
        renewals += 1
        capacity_reference = _admit_capacity(
            session,
            capacity,
            qualification=qualification,
            supersedes=capacity_reference,
        )
        return capacity_reference, capacity

    attempts: list[WorkAttempt] = []

    def observe(attempt: WorkAttempt) -> _Observation:
        attempts.append(attempt)
        if not attempt.is_resuming:
            raise CapacityRenewalRequired("local_placement_stale")
        return _Observation("complete")

    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
        renew_capacity=renew,
        _wait=lambda _seconds: None,
    )
    outcome = execution.execute(
        (
            _observation_request(
                "cell-1",
                "fixture.observation",
                observe,
                _restore_observation,
            ),
        )
    )

    assert isinstance(outcome, CompletedWorkExecution)
    assert renewals == 1
    assert attempts == [
        WorkAttempt(is_resuming=False),
        WorkAttempt(is_resuming=True),
    ]
    assert tuple(
        sorted(str(item.close_reason) for item in authority.view().permits)
    ) == ("consumed", "revoked")


def test_bounded_chunk_contention_closes_every_partially_reserved_permit(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    qualification = session.admit_document(
        Document("fixture.qualification", {"qualified": True})
    )
    capacity = _Capacity(
        "solver:fixture",
        2,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    capacity_reference = _admit_capacity(
        session,
        capacity,
        qualification=qualification,
    )
    blocked = session.reserve_work(
        Document(PERMITTED_WORK_SCHEMA, {"work": "cell-blocked"}),
        capacity_reference=capacity_reference,
        scope=capacity.scope,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    assert blocked is not None
    observations = 0

    def observe(_attempt: WorkAttempt) -> _Observation:
        nonlocal observations
        observations += 1
        return _Observation("complete")

    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
        _wait=lambda _seconds: None,
        _permit_attempts=1,
    )
    outcome = execution.execute(
        (
            _observation_request(
                "cell-acquired",
                "fixture.observation",
                observe,
                _restore_observation,
            ),
            _observation_request(
                "cell-blocked",
                "fixture.observation",
                observe,
                _restore_observation,
            ),
        )
    )

    assert isinstance(outcome, WorkWaiting)
    assert outcome.reason == "permit_unavailable"
    assert outcome.work_identities == ("cell-acquired", "cell-blocked")
    assert observations == 0
    permits = authority.view().permits
    close_reason_by_work = {
        str(
            Document.from_bytes(authority.fetch(item.body_reference)).values["work"]
        ): item.close_reason
        for item in permits
    }
    assert close_reason_by_work == {
        "cell-acquired": "revoked",
        "cell-blocked": None,
    }


def test_partial_acquisition_closes_reserved_sibling_on_base_exception(
    tmp_path: Path,
) -> None:
    class InterruptingSession(AuthoritySession):
        __slots__ = ("_reservations",)

        def __init__(self, authority: Authority) -> None:
            super().__init__(authority)
            self._reservations = 0

        def reserve_work(
            self,
            document: Document,
            *,
            capacity_reference: Reference,
            scope: str,
            expires_at: datetime,
        ) -> Reference | PermitReservationWaiting:
            self._reservations += 1
            if self._reservations == 2:
                raise KeyboardInterrupt("fixture acquisition cancelled")
            return super().reserve_work(
                document,
                capacity_reference=capacity_reference,
                scope=scope,
                expires_at=expires_at,
            )

    authority, _session, capacity, capacity_reference = _capacity_setup(
        tmp_path,
        limit=2,
    )
    execution = WorkExecution(
        InterruptingSession(authority),
        capacity_reference=capacity_reference,
        capacity=capacity,
    )

    with pytest.raises(WorkExecutionFault) as raised:
        execution.execute(
            (
                _observation_request(
                    "cell-acquired",
                    "fixture.observation",
                    lambda _attempt: _Observation("unexpected"),
                    _restore_observation,
                ),
                _observation_request(
                    "cell-cancelled",
                    "fixture.observation",
                    lambda _attempt: _Observation("unexpected"),
                    _restore_observation,
                ),
            )
        )
    assert isinstance(raised.value.fault, KeyboardInterrupt)
    assert "acquisition cancelled" in str(raised.value.fault)

    permits = authority.view().permits
    assert len(permits) == 1
    assert permits[0].state == "closed"
    assert permits[0].close_reason == "revoked"


def test_two_sessions_share_one_stable_permit_and_observe_exactly_once(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    setup = AuthoritySession(authority)
    qualification = setup.admit_document(
        Document("fixture.qualification", {"qualified": True})
    )
    capacity = _Capacity(
        "solver:fixture",
        2,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    capacity_reference = _admit_capacity(
        setup,
        capacity,
        qualification=qualification,
    )
    first_execution = WorkExecution(
        AuthoritySession(authority),
        capacity_reference=capacity_reference,
        capacity=capacity,
    )
    second_execution = WorkExecution(
        AuthoritySession(authority),
        capacity_reference=capacity_reference,
        capacity=capacity,
    )
    observation_started = Event()
    release_observation = Event()
    counter_lock = Lock()
    observations = 0

    def observe(_attempt: WorkAttempt) -> _Observation:
        nonlocal observations
        with counter_lock:
            observations += 1
        observation_started.set()
        assert release_observation.wait(timeout=2)
        return _Observation("complete")

    request = _observation_request(
        "same-cell",
        "fixture.observation",
        observe,
        _restore_observation,
    )
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(first_execution.execute, (request,))
        assert observation_started.wait(timeout=2)
        second = workers.submit(second_execution.execute, (request,))
        release_observation.set()
        first_outcome = first.result(timeout=3)
        second_outcome = second.result(timeout=3)

    assert isinstance(first_outcome, CompletedWorkExecution)
    assert isinstance(second_outcome, CompletedWorkExecution)
    assert second_outcome.items == first_outcome.items
    assert observations == 1
    assert len(authority.view().permits) == 1


def test_restore_rejects_boolean_for_persisted_integer(
    tmp_path: Path,
) -> None:
    @dataclass(frozen=True, slots=True)
    class NumericObservation:
        value: int | bool

        def as_mapping(self) -> dict[str, object]:
            return {"value": self.value}

    _authority, execution = _execution(tmp_path)
    recorded = _observation_request(
        "numeric-cell",
        "fixture.numeric",
        lambda _attempt: NumericObservation(1),
        lambda document: NumericObservation(bool(document.values["value"])),
    )
    first = execution.execute((recorded,))
    assert isinstance(first, CompletedWorkExecution)

    with pytest.raises(
        RuntimeError,
        match="work_receipt_observation_mismatch",
    ):
        execution.execute((recorded,))


def test_direct_failure_wins_over_later_capacity_waiting(
    tmp_path: Path,
) -> None:
    @dataclass(slots=True)
    class OneWaveCapacity:
        scope: str
        limit: int
        fresh_until: datetime
        checks: int = 0

        def is_fresh_at(self, _value: datetime) -> bool:
            self.checks += 1
            return self.checks <= 3

        def as_mapping(self) -> dict[str, object]:
            return {
                "fresh_until": self.fresh_until.astimezone(UTC)
                .isoformat()
                .replace("+00:00", "Z"),
                "limit": self.limit,
                "scope": self.scope,
            }

    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    qualification = session.admit_document(
        Document("fixture.qualification", {"qualified": True})
    )
    capacity = OneWaveCapacity(
        "solver:fixture",
        1,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    capacity_reference = _admit_capacity(
        session,
        _Capacity(
            capacity.scope,
            capacity.limit,
            capacity.fresh_until,
        ),
        qualification=qualification,
    )

    def fail(_attempt: WorkAttempt) -> _Observation:
        raise RuntimeError("first-wave-failed")

    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
    )
    with pytest.raises(WorkExecutionFault) as raised:
        execution.execute(
            (
                _observation_request(
                    "first",
                    "fixture.observation",
                    fail,
                    _restore_observation,
                ),
                _observation_request(
                    "second",
                    "fixture.observation",
                    lambda _attempt: _Observation("complete"),
                    _restore_observation,
                ),
            )
        )

    assert str(raised.value.fault) == "first-wave-failed"


def test_capacity_reference_rejects_a_different_freshness_generation(
    tmp_path: Path,
) -> None:
    authority, session, capacity, capacity_reference = _capacity_setup(tmp_path)
    mismatched = _Capacity(
        capacity.scope,
        capacity.limit,
        capacity.fresh_until + timedelta(seconds=1),
    )
    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=mismatched,
    )

    with pytest.raises(RuntimeError, match="capacity_observation_mismatch"):
        execution.execute(
            (
                _observation_request(
                    "cell-1",
                    "fixture.observation",
                    lambda _attempt: _Observation("complete"),
                    _restore_observation,
                ),
            )
        )

    assert authority.view().permits == ()


def test_stale_capacity_without_a_renewal_is_typed_waiting(
    tmp_path: Path,
) -> None:
    _authority, session, capacity, capacity_reference = _capacity_setup(
        tmp_path,
        fresh_until=datetime.now(UTC) - timedelta(seconds=1),
    )
    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
    )

    outcome = execution.execute(
        (
            _observation_request(
                "cell-1",
                "fixture.observation",
                lambda _attempt: pytest.fail("stale work was observed"),
                _restore_observation,
            ),
        )
    )

    assert isinstance(outcome, WorkWaiting)
    assert outcome.reason == "capacity_stale"
    assert outcome.work_identities == ("cell-1",)


def test_unavailable_capacity_renewal_is_typed_waiting(
    tmp_path: Path,
) -> None:
    _authority, session, capacity, capacity_reference = _capacity_setup(
        tmp_path,
        fresh_until=datetime.now(UTC) - timedelta(seconds=1),
    )
    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
        renew_capacity=lambda: CapacityRenewalWaiting("capacity_not_positive"),
    )

    outcome = execution.execute(
        (
            _observation_request(
                "cell-1",
                "fixture.observation",
                lambda _attempt: pytest.fail("unavailable work was observed"),
                _restore_observation,
            ),
        )
    )

    assert isinstance(outcome, WorkWaiting)
    assert outcome.reason == "capacity_not_positive"


def test_expired_permit_is_closed_before_same_work_is_observed(
    tmp_path: Path,
) -> None:
    observed_at = datetime.now(UTC)
    authority, session, capacity, capacity_reference = _capacity_setup(
        tmp_path,
        fresh_until=observed_at + timedelta(minutes=10),
    )
    expired = session.reserve_work(
        Document(PERMITTED_WORK_SCHEMA, {"work": "cell-1"}),
        capacity_reference=capacity_reference,
        scope=capacity.scope,
        expires_at=observed_at + timedelta(milliseconds=100),
    )
    assert isinstance(expired, Reference)
    assert Event().wait(timeout=0.15) is False
    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
    )

    outcome = execution.execute(
        (
            _observation_request(
                "cell-1",
                "fixture.observation",
                lambda attempt: _Observation(
                    "resumed" if attempt.is_resuming else "fresh"
                ),
                _restore_observation,
            ),
        )
    )

    assert isinstance(outcome, CompletedWorkExecution)
    assert outcome.items[0].observation == _Observation("resumed")
    assert tuple(
        sorted(str(permit.close_reason) for permit in authority.view().permits)
    ) == ("consumed", "expired")


def test_malformed_non_string_permit_work_remains_a_direct_fault(
    tmp_path: Path,
) -> None:
    _authority, session, capacity, capacity_reference = _capacity_setup(tmp_path)
    malformed = session.reserve_work(
        Document(PERMITTED_WORK_SCHEMA, {"work": 7}),
        capacity_reference=capacity_reference,
        scope=capacity.scope,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )
    assert isinstance(malformed, Reference)
    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
    )

    with pytest.raises(RuntimeError, match="work_permit_document_invalid"):
        execution.execute(
            (
                _observation_request(
                    "cell-1",
                    "fixture.observation",
                    lambda _attempt: _Observation("complete"),
                    _restore_observation,
                ),
            )
        )


def test_restored_receipt_schema_drift_remains_a_direct_fault(
    tmp_path: Path,
) -> None:
    _authority, session, capacity, capacity_reference = _capacity_setup(tmp_path)
    permit = session.reserve_work(
        Document(PERMITTED_WORK_SCHEMA, {"work": "cell-1"}),
        capacity_reference=capacity_reference,
        scope=capacity.scope,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )
    assert isinstance(permit, Reference)
    session.admit_receipt(
        Document("fixture.wrong_observation", {"status": "complete"}),
        permit_reference=permit,
    )
    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
    )

    with pytest.raises(ValueError, match="fixture_observation_schema_invalid"):
        execution.execute(
            (
                _observation_request(
                    "cell-1",
                    "fixture.observation",
                    lambda _attempt: pytest.fail("schema-drifted receipt was repeated"),
                    _restore_observation,
                ),
            )
        )


def test_duplicate_consumed_receipts_remain_a_direct_fault(
    tmp_path: Path,
) -> None:
    _authority, session, capacity, capacity_reference = _capacity_setup(tmp_path)
    for offset in (1, 2):
        permit = session.reserve_work(
            Document(PERMITTED_WORK_SCHEMA, {"work": "cell-1"}),
            capacity_reference=capacity_reference,
            scope=capacity.scope,
            expires_at=datetime.now(UTC) + timedelta(minutes=offset),
        )
        assert isinstance(permit, Reference)
        session.admit_receipt(
            Document(
                "fixture.observation",
                {"status": "complete"},
            ),
            permit_reference=permit,
        )
    execution = WorkExecution(
        session,
        capacity_reference=capacity_reference,
        capacity=capacity,
    )

    with pytest.raises(RuntimeError, match="work_receipt_duplicate"):
        execution.execute(
            (
                _observation_request(
                    "cell-1",
                    "fixture.observation",
                    lambda _attempt: pytest.fail("duplicate receipt was repeated"),
                    _restore_observation,
                ),
            )
        )

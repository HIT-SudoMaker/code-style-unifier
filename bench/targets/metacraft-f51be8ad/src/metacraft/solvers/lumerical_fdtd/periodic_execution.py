from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
from pathlib import Path

from ...authority import Document, Reference
from ...canonical import encode_bytes
from ...external_activity import (
    ExternalActivityClosure,
    _combine_external_activity,
)
from ...field.reference_surface import RequestedInputBasis
from ...field.sample import Medium
from ...science.periodic_response import (
    PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA,
    AdmittedPeriodicObservationIncomplete,
    AdmittedPeriodicPolarization,
    AdmittedPeriodicTransmission,
    ObservedPeriodicPolarization,
    ObservedPeriodicTransmission,
    PeriodicPolarizationObservation,
    PeriodicPolarizationRequest,
    PeriodicCellObservation,
    PeriodicTransmissionObservation,
    PeriodicTransmissionRequest,
    PeriodicWork,
    PeriodicResponseClosure,
    PeriodicObservationDocument,
    PeriodicObservationIncomplete,
    PeriodicObservationIncompleteReason,
    PeriodicPolarizationIncomplete,
    PeriodicTransmissionIncomplete,
    form_admitted_periodic_polarization,
    form_admitted_periodic_transmission,
    decode_periodic_observation_incomplete,
    decode_periodic_polarization,
    decode_periodic_transmission,
)
from ...science.phase import phase_from_float
from ...work_execution import (
    WorkAttempt,
    WorkExecution,
    WorkExecutionFault,
    WorkRequest,
    WorkWaiting,
)

from .artifacts import RunDirectory, WorkRecord
from .lane import SessionLease, SessionPool
from .project_execution import ProjectExecution
from .qualification import CapacityObservation
from .reference_surface import (
    ReferenceSurfaceRequest,
    decode_reference_surface,
    periodic_reference_surface_request,
)
from .session import Session
from .template import (
    ConstructionManifest,
    PeriodicConstruction,
    prepare_periodic_construction,
)
from .time_budget import (
    PeriodicNumericalClosure,
    SolverTermination,
    TimeBudgetAttempt,
    polarization_response_change,
    reference_surface_response_change,
    transmission_response_change,
)


class PeriodicExecutionFault(BaseExceptionGroup):
    """
    Retain one direct product fault beside fully settled batch activity.
    """

    activity_closure: ExternalActivityClosure

    def __new__(
        cls,
        fault: BaseException,
        activity_closure: ExternalActivityClosure,
    ) -> PeriodicExecutionFault:
        """
        Build one batch-fault carrier around the unchanged product fault.
        """

        instance = super().__new__(
            cls,
            "periodic_execution_failed",
            (fault,),
        )
        instance.activity_closure = activity_closure
        return instance

    def __init__(
        self,
        fault: BaseException,
        activity_closure: ExternalActivityClosure,
    ) -> None:
        """
        Leave BaseExceptionGroup initialization to ``__new__``.
        """

        pass

    @property
    def fault(self) -> BaseException:
        """
        Return the original direct or grouped product fault unchanged.
        """

        return self.exceptions[0]


@dataclass(frozen=True, slots=True)
class _PeriodicAttempt:
    """
    Retain one native attempt until the time budget selects its result.
    """

    name: str
    maximum_time_fs: int
    execution: ProjectExecution
    session: Session
    termination: SolverTermination
    response: Mapping[str, object]
    reference_surface: Mapping[str, object] | None


@dataclass(slots=True)
class PeriodicBatchExecution:
    """
    Execute one sealed physical batch through one WorkExecution.

    This is the product's only response runner. It owns lanes, sessions,
    native projects, artifacts, receipts, and exact recovery; it knows no
    scientific route and forms no scientific library.
    """

    work_execution: WorkExecution
    sessions: SessionPool
    run: RunDirectory
    should_sample_reference_surface: bool
    qualification_closure: ExternalActivityClosure = ExternalActivityClosure.none()

    def observe_transmission(
        self,
        request: PeriodicTransmissionRequest,
    ) -> (
        ObservedPeriodicTransmission
        | PeriodicTransmissionIncomplete
        | WorkWaiting[
            PeriodicObservationDocument[PeriodicTransmissionObservation]
            | PeriodicObservationIncomplete
        ]
    ):
        """
        Observe one transmission batch and close every owned resource.
        """

        self._prepare_batch(tuple(request.items))
        try:
            completed = self.work_execution.execute(
                tuple(self._transmission_request(work) for work in request.items)
            )
        except WorkExecutionFault as failure:
            primary = failure.fault
            try:
                session_activity = self.sessions.close()
            except BaseException as cleanup:
                raise BaseExceptionGroup(
                    "periodic_transmission_terminalization_failed",
                    [primary, cleanup],
                ) from primary
            if failure.activity_closure is None:
                raise primary
            raise PeriodicExecutionFault(
                primary,
                _combine_external_activity(
                    failure.activity_closure,
                    session_activity,
                ),
            ) from primary
        session_activity = self.sessions.close()
        work_activity = completed.activity_closure
        observation_activity = _combine_external_activity(
            work_activity,
            session_activity,
        )
        if isinstance(completed, WorkWaiting):
            return WorkWaiting(
                completed.reason,
                completed.work_identities,
                completed.completed,
                observation_activity,
            )
        observations = tuple(
            form_admitted_periodic_transmission(
                item.work_identity,
                item.observation,
                item.body_reference,
                item.receipt_reference,
            )
            for item in completed.items
            if isinstance(item.observation, PeriodicObservationDocument)
        )
        incompletions = tuple(
            AdmittedPeriodicObservationIncomplete(
                item.work_identity,
                item.observation,
                item.body_reference,
                item.receipt_reference,
            )
            for item in completed.items
            if isinstance(item.observation, PeriodicObservationIncomplete)
        )
        closure = PeriodicResponseClosure(
            request.request_identity,
            self.qualification_closure,
            observation_activity,
        )
        if incompletions:
            return PeriodicTransmissionIncomplete(
                request.request_identity,
                observations,
                incompletions,
                closure,
            )
        return ObservedPeriodicTransmission(
            request.request_identity,
            observations,
            closure,
        )

    def observe_polarization(
        self,
        request: PeriodicPolarizationRequest,
    ) -> (
        ObservedPeriodicPolarization
        | PeriodicPolarizationIncomplete
        | WorkWaiting[
            PeriodicObservationDocument[PeriodicPolarizationObservation]
            | PeriodicObservationIncomplete
        ]
    ):
        """
        Observe one polarization batch and close every owned resource.
        """

        self._prepare_batch(tuple(request.items))
        try:
            completed = self.work_execution.execute(
                tuple(self._polarization_request(work) for work in request.items)
            )
        except WorkExecutionFault as failure:
            primary = failure.fault
            try:
                session_activity = self.sessions.close()
            except BaseException as cleanup:
                raise BaseExceptionGroup(
                    "periodic_polarization_terminalization_failed",
                    [primary, cleanup],
                ) from primary
            if failure.activity_closure is None:
                raise primary
            raise PeriodicExecutionFault(
                primary,
                _combine_external_activity(
                    failure.activity_closure,
                    session_activity,
                ),
            ) from primary
        session_activity = self.sessions.close()
        work_activity = completed.activity_closure
        observation_activity = _combine_external_activity(
            work_activity,
            session_activity,
        )
        if isinstance(completed, WorkWaiting):
            return WorkWaiting(
                completed.reason,
                completed.work_identities,
                completed.completed,
                observation_activity,
            )
        observations = tuple(
            form_admitted_periodic_polarization(
                item.work_identity,
                item.observation,
                item.body_reference,
                item.receipt_reference,
            )
            for item in completed.items
            if isinstance(item.observation, PeriodicObservationDocument)
        )
        incompletions = tuple(
            AdmittedPeriodicObservationIncomplete(
                item.work_identity,
                item.observation,
                item.body_reference,
                item.receipt_reference,
            )
            for item in completed.items
            if isinstance(item.observation, PeriodicObservationIncomplete)
        )
        closure = PeriodicResponseClosure(
            request.request_identity,
            self.qualification_closure,
            observation_activity,
        )
        if incompletions:
            return PeriodicPolarizationIncomplete(
                request.request_identity,
                observations,
                incompletions,
                closure,
            )
        return ObservedPeriodicPolarization(
            request.request_identity,
            observations,
            closure,
        )

    def _transmission_request(
        self,
        work: PeriodicWork,
    ) -> WorkRequest[
        PeriodicObservationDocument[PeriodicTransmissionObservation]
        | PeriodicObservationIncomplete
    ]:
        return WorkRequest(
            work_identity=work.work_identity,
            observe=lambda attempt: self._observe_transmission(
                work,
                attempt=attempt,
            ),
            encode=lambda observation: self._encode_outcome(observation, work),
            restore=lambda document: self._restore_transmission(
                document,
                work,
            ),
        )

    def _polarization_request(
        self,
        work: PeriodicWork,
    ) -> WorkRequest[
        PeriodicObservationDocument[PeriodicPolarizationObservation]
        | PeriodicObservationIncomplete
    ]:
        return WorkRequest(
            work_identity=work.work_identity,
            observe=lambda attempt: self._observe_polarization(
                work,
                attempt=attempt,
            ),
            encode=lambda observation: self._encode_outcome(observation, work),
            restore=lambda document: self._restore_polarization(
                document,
                work,
            ),
        )

    def _encode_outcome(
        self,
        outcome: (
            PeriodicObservationDocument[PeriodicTransmissionObservation]
            | PeriodicObservationDocument[PeriodicPolarizationObservation]
            | PeriodicObservationIncomplete
        ),
        work: PeriodicWork,
    ) -> Document:
        schema = (
            PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA
            if isinstance(outcome, PeriodicObservationIncomplete)
            else work.observation_schema
        )
        return Document(schema, outcome.as_mapping())

    def _prepare_batch(self, items: tuple[PeriodicWork, ...]) -> None:
        first = items[0]
        if any(
            item.capacity_scope != self.work_execution.capacity_scope for item in items
        ):
            raise ValueError("periodic_work_capacity_scope_mismatch")
        self.run.record_manifest(
            period_nm=first.period_nm,
            order_regime=first.order_regime,
            cautions=(),
        )

    def _observe_transmission(
        self,
        work: PeriodicWork,
        *,
        attempt: WorkAttempt,
    ) -> (
        PeriodicObservationDocument[PeriodicTransmissionObservation]
        | PeriodicObservationIncomplete
    ):
        construction = prepare_periodic_construction(work)
        directory = self.run.prepare_candidate(
            work.cell_identity,
            construction.as_mapping(),
            work_identity=work.work_identity,
            should_adopt_identity=attempt.is_resuming,
        )
        restored = self.run.find_work(directory)
        if restored is not None:
            return self._restore_transmission_values(
                restored.complete_observation(),
                work,
                construction=construction,
            )
        with self.sessions.lease() as lease:
            session = lease.session
            observed_session = session
            try:
                manifest = construction.build_in(session)
                if manifest.mismatches:
                    raise RuntimeError("construction_read_back_mismatch")
                ordinary = self._run_attempt(
                    lease,
                    directory,
                    attempt="ordinary",
                    maximum_time_fs=(construction.time_budget.ordinary_maximum_fs),
                    result_name="propagation",
                    construction=construction,
                    work=work,
                )
                observed_session = ordinary.session
                closed = self._close_transmission_time(
                    lease,
                    directory,
                    construction,
                    work,
                    ordinary,
                )
                if isinstance(closed, PeriodicObservationIncomplete):
                    return closed
                selected, numerical_closure = closed
                observed_session = selected.session
                raw = _with_numerical_warnings(
                    selected.response,
                    numerical_closure,
                )
                observation = _transmission_observation(
                    work,
                    manifest,
                    raw,
                    selected.execution,
                    reference_surface=selected.reference_surface,
                )
                self._record_work(
                    directory,
                    work=work,
                    lease=lease,
                    manifest=manifest,
                    numerical_closure=numerical_closure,
                    execution=selected.execution,
                    observation=observation.as_mapping(),
                    warnings=_warnings(raw.get("warnings", ())),
                )
                return observation
            finally:
                if observed_session is not session:
                    observed_session.close()

    def _observe_polarization(
        self,
        work: PeriodicWork,
        *,
        attempt: WorkAttempt,
    ) -> (
        PeriodicObservationDocument[PeriodicPolarizationObservation]
        | PeriodicObservationIncomplete
    ):
        construction = prepare_periodic_construction(work)
        candidate_directory = self.run.candidate(work.cell_identity)
        basis = _linear_axis(work.input_basis)
        directory = self.run.prepare_basis(
            candidate_directory,
            basis,
            construction.as_mapping(),
            work_identity=work.work_identity,
            should_adopt_identity=attempt.is_resuming,
        )
        restored = self.run.find_work(directory)
        if restored is not None:
            return self._restore_polarization_values(
                restored.complete_observation(),
                work,
                construction=construction,
            )
        with self.sessions.lease() as lease:
            session = lease.session
            observed_session = session
            try:
                manifest = construction.build_in(session)
                if manifest.mismatches:
                    raise RuntimeError("construction_read_back_mismatch")
                ordinary = self._run_attempt(
                    lease,
                    directory,
                    attempt="ordinary",
                    maximum_time_fs=(construction.time_budget.ordinary_maximum_fs),
                    result_name="linear_transmission",
                    construction=construction,
                    work=work,
                )
                observed_session = ordinary.session
                closed = self._close_polarization_time(
                    lease,
                    directory,
                    construction,
                    work,
                    ordinary,
                )
                if isinstance(closed, PeriodicObservationIncomplete):
                    return closed
                selected, numerical_closure = closed
                observed_session = selected.session
                raw = _with_numerical_warnings(
                    selected.response,
                    numerical_closure,
                )
                observation = _polarization_observation(
                    work,
                    raw,
                    selected.execution,
                    reference_surface=selected.reference_surface,
                )
                self._record_work(
                    directory,
                    work=work,
                    lease=lease,
                    manifest=manifest,
                    numerical_closure=numerical_closure,
                    execution=selected.execution,
                    observation=observation.as_mapping(),
                    warnings=_warnings(raw.get("warnings", ())),
                )
                return observation
            finally:
                if observed_session is not session:
                    observed_session.close()

    def _run_attempt(
        self,
        lease: SessionLease,
        directory: Path,
        *,
        attempt: str,
        maximum_time_fs: int,
        result_name: str,
        construction: PeriodicConstruction,
        work: PeriodicWork,
    ) -> _PeriodicAttempt:
        constructed, completed = self.run.native_projects(directory)
        executed = self.sessions.solve(lease, constructed, completed)
        self.run.record_execution(directory, executed.execution)
        termination = SolverTermination.from_mapping(
            _mapping(executed.session.result("solver", "termination"))
        )
        if termination.outcome == "diverged":
            return _PeriodicAttempt(
                name=attempt,
                maximum_time_fs=maximum_time_fs,
                execution=executed.execution,
                session=executed.session,
                termination=termination,
                response={},
                reference_surface=None,
            )
        try:
            response = _mapping(
                executed.session.result("grating_response", result_name)
            )
            _require_response_inventory(response, result_name=result_name)
            reference_surface = self._sample_reference_surface(
                executed.session,
                construction,
                work,
            )
        except BaseException:
            self.run.record_current_termination(
                directory,
                termination.as_mapping(),
            )
            raise
        return _PeriodicAttempt(
            name=attempt,
            maximum_time_fs=maximum_time_fs,
            execution=executed.execution,
            session=executed.session,
            termination=termination,
            response=response,
            reference_surface=reference_surface,
        )

    def _close_transmission_time(
        self,
        lease: SessionLease,
        directory: Path,
        construction: PeriodicConstruction,
        work: PeriodicWork,
        ordinary: _PeriodicAttempt,
    ) -> (
        tuple[_PeriodicAttempt, PeriodicNumericalClosure]
        | PeriodicObservationIncomplete
    ):
        if ordinary.termination.outcome == "diverged":
            return self._refuse_numerical_time(
                directory,
                construction,
                work,
                attempts=(ordinary,),
                reason=PeriodicObservationIncompleteReason.SOLVER_DIVERGED,
            )
        should_extend = ordinary.termination.outcome == "maximum_time"
        power = Decimal(str(ordinary.response["power_transmission"]))
        if power.is_finite() and not Decimal(0) <= power <= Decimal(1):
            should_extend = True
        if not should_extend:
            return ordinary, PeriodicNumericalClosure(
                budget=construction.time_budget,
                attempts=(_time_attempt(ordinary),),
                disposition="autoshutoff",
            )
        extended = self._extend_attempt(
            lease,
            directory,
            construction,
            work,
            ordinary,
            result_name="propagation",
        )
        attempts = (ordinary, extended)
        if extended.termination.outcome == "diverged":
            return self._refuse_numerical_time(
                directory,
                construction,
                work,
                attempts=attempts,
                reason=PeriodicObservationIncompleteReason.SOLVER_DIVERGED,
            )
        extended_power = Decimal(str(extended.response["power_transmission"]))
        if not extended_power.is_finite() or not Decimal(
            0
        ) <= extended_power <= Decimal(1):
            return self._refuse_numerical_time(
                directory,
                construction,
                work,
                attempts=attempts,
                reason=PeriodicObservationIncompleteReason.TIME_BUDGET_EXHAUSTED,
            )
        time_attempts = tuple(_time_attempt(attempt) for attempt in attempts)
        if extended.termination.outcome == "autoshutoff":
            return extended, PeriodicNumericalClosure(
                budget=construction.time_budget,
                attempts=time_attempts,
                disposition="autoshutoff_after_extension",
            )
        has_converged, change = transmission_response_change(
            ordinary.response,
            extended.response,
        )
        surface_converged, surface_change = _surface_response_change(
            ordinary,
            extended,
        )
        change.update(surface_change)
        has_converged = has_converged and surface_converged
        if not has_converged:
            return self._refuse_numerical_time(
                directory,
                construction,
                work,
                attempts=attempts,
                reason=PeriodicObservationIncompleteReason.TIME_BUDGET_EXHAUSTED,
                response_change=change,
            )
        return extended, PeriodicNumericalClosure(
            budget=construction.time_budget,
            attempts=time_attempts,
            disposition="converged_by_extension",
            response_change=change,
        )

    def _close_polarization_time(
        self,
        lease: SessionLease,
        directory: Path,
        construction: PeriodicConstruction,
        work: PeriodicWork,
        ordinary: _PeriodicAttempt,
    ) -> (
        tuple[_PeriodicAttempt, PeriodicNumericalClosure]
        | PeriodicObservationIncomplete
    ):
        if ordinary.termination.outcome == "diverged":
            return self._refuse_numerical_time(
                directory,
                construction,
                work,
                attempts=(ordinary,),
                reason=PeriodicObservationIncompleteReason.SOLVER_DIVERGED,
            )
        if ordinary.termination.outcome == "autoshutoff":
            return ordinary, PeriodicNumericalClosure(
                budget=construction.time_budget,
                attempts=(_time_attempt(ordinary),),
                disposition="autoshutoff",
            )
        extended = self._extend_attempt(
            lease,
            directory,
            construction,
            work,
            ordinary,
            result_name="linear_transmission",
        )
        attempts = (ordinary, extended)
        if extended.termination.outcome == "diverged":
            return self._refuse_numerical_time(
                directory,
                construction,
                work,
                attempts=attempts,
                reason=PeriodicObservationIncompleteReason.SOLVER_DIVERGED,
            )
        time_attempts = tuple(_time_attempt(attempt) for attempt in attempts)
        if extended.termination.outcome == "autoshutoff":
            return extended, PeriodicNumericalClosure(
                budget=construction.time_budget,
                attempts=time_attempts,
                disposition="autoshutoff_after_extension",
            )
        has_converged, change = polarization_response_change(
            ordinary.response,
            extended.response,
        )
        surface_converged, surface_change = _surface_response_change(
            ordinary,
            extended,
        )
        change.update(surface_change)
        has_converged = has_converged and surface_converged
        if not has_converged:
            return self._refuse_numerical_time(
                directory,
                construction,
                work,
                attempts=attempts,
                reason=PeriodicObservationIncompleteReason.TIME_BUDGET_EXHAUSTED,
                response_change=change,
            )
        return extended, PeriodicNumericalClosure(
            budget=construction.time_budget,
            attempts=time_attempts,
            disposition="converged_by_extension",
            response_change=change,
        )

    def _extend_attempt(
        self,
        lease: SessionLease,
        directory: Path,
        construction: PeriodicConstruction,
        work: PeriodicWork,
        ordinary: _PeriodicAttempt,
        *,
        result_name: str,
    ) -> _PeriodicAttempt:
        self.run.record_current_termination(
            directory,
            ordinary.termination.as_mapping(),
        )
        self.run.archive_ordinary_attempt(directory)
        lease.session.change_maximum_time(
            "solver",
            construction.time_budget.extended_maximum_fs,
        )
        return self._run_attempt(
            lease,
            directory,
            attempt="extended",
            maximum_time_fs=construction.time_budget.extended_maximum_fs,
            result_name=result_name,
            construction=construction,
            work=work,
        )

    def _refuse_numerical_time(
        self,
        directory: Path,
        construction: PeriodicConstruction,
        work: PeriodicWork,
        *,
        attempts: tuple[_PeriodicAttempt, ...],
        reason: PeriodicObservationIncompleteReason,
        response_change: Mapping[str, str] | None = None,
    ) -> PeriodicObservationIncomplete:
        """
        Record and return one settled bounded numerical incompletion.
        """

        outcome = PeriodicObservationIncomplete(
            work_identity=work.work_identity,
            reason=reason,
            time_budget=construction.time_budget.as_mapping(),
            attempts=tuple(_time_attempt(attempt).as_mapping() for attempt in attempts),
            response_change=response_change,
        )
        self.run.record_numerical_refusal(directory, outcome.as_mapping())
        return outcome

    def _restore_transmission(
        self,
        document: Document,
        work: PeriodicWork,
    ) -> (
        PeriodicObservationDocument[PeriodicTransmissionObservation]
        | PeriodicObservationIncomplete
    ):
        if document.schema_identifier == PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA:
            return self._restore_incomplete(document, work)
        if document.schema_identifier != work.observation_schema:
            raise ValueError("periodic_response_receipt_schema_mismatch")
        return self._restore_transmission_values(
            document.values,
            work,
            construction=prepare_periodic_construction(work),
        )

    def _restore_transmission_values(
        self,
        values: Mapping[str, object],
        work: PeriodicWork,
        *,
        construction: PeriodicConstruction,
    ) -> PeriodicObservationDocument[PeriodicTransmissionObservation]:
        observation = decode_periodic_transmission(values)
        _validate_candidate(observation.observation.cell, work)
        self._validate_embedded_surface(
            observation.as_mapping(),
            work,
            construction=construction,
        )
        return observation

    def _restore_polarization(
        self,
        document: Document,
        work: PeriodicWork,
    ) -> (
        PeriodicObservationDocument[PeriodicPolarizationObservation]
        | PeriodicObservationIncomplete
    ):
        if document.schema_identifier == PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA:
            return self._restore_incomplete(document, work)
        if document.schema_identifier != work.observation_schema:
            raise ValueError("periodic_response_receipt_schema_mismatch")
        return self._restore_polarization_values(
            document.values,
            work,
            construction=prepare_periodic_construction(work),
        )

    def _restore_incomplete(
        self,
        document: Document,
        work: PeriodicWork,
    ) -> PeriodicObservationIncomplete:
        outcome = decode_periodic_observation_incomplete(document.values)
        if outcome.work_identity != work.work_identity:
            raise ValueError("periodic_incompletion_work_identity_mismatch")
        return outcome

    def _restore_polarization_values(
        self,
        values: Mapping[str, object],
        work: PeriodicWork,
        *,
        construction: PeriodicConstruction,
    ) -> PeriodicObservationDocument[PeriodicPolarizationObservation]:
        observation = decode_periodic_polarization(values)
        _validate_candidate(observation.observation.cell, work)
        if observation.observation.input_basis != _linear_axis(work.input_basis):
            raise RuntimeError("periodic_polarization_basis_mismatch")
        self._validate_embedded_surface(
            observation.as_mapping(),
            work,
            construction=construction,
        )
        record = self.run.restore_work(
            self.run.basis_work(
                self.run.candidate(work.cell_identity),
                _linear_axis(work.input_basis),
            )
        )
        if encode_bytes(record.complete_observation()) != encode_bytes(
            observation.as_mapping()
        ):
            raise RuntimeError("periodic_polarization_artifact_mismatch")
        return observation

    def _sample_reference_surface(
        self,
        session: Session,
        construction: PeriodicConstruction,
        work: PeriodicWork,
    ) -> Mapping[str, object] | None:
        if not self.should_sample_reference_surface:
            return None
        raw = _normalize_reference_surface(
            _mapping(
                session.result(
                    "grating_response",
                    "reference_surface",
                )
            ),
            order_regime=work.order_regime,
        )
        expected = _surface_request(
            raw,
            construction,
            work,
            source_references=work.source_references,
        )
        decode_reference_surface(raw, expected=expected)
        return raw

    def _validate_embedded_surface(
        self,
        values: Mapping[str, object],
        work: PeriodicWork,
        *,
        construction: PeriodicConstruction,
    ) -> None:
        raw = values.get("reference_surface")
        if raw is None:
            if self.should_sample_reference_surface:
                raise ValueError("reference_surface_observation_missing")
            return
        if not self.should_sample_reference_surface:
            raise ValueError("reference_surface_capability_unproved")
        surface = _mapping(raw)
        decode_reference_surface(
            surface,
            expected=_surface_request(
                surface,
                construction,
                work,
                source_references=work.source_references,
            ),
        )

    def _record_work(
        self,
        directory: Path,
        *,
        work: PeriodicWork,
        lease: SessionLease,
        manifest: ConstructionManifest,
        numerical_closure: PeriodicNumericalClosure,
        execution: ProjectExecution,
        observation: Mapping[str, object],
        warnings: tuple[str, ...],
    ) -> None:
        self.run.record_work(
            directory,
            WorkRecord(
                work_identity=work.work_identity,
                session_identity=lease.session_identity,
                lane_identity=lease.lane_identity,
                is_session_reused=lease.is_reused,
                construction={
                    **manifest.as_mapping(),
                    "numerical_closure": numerical_closure.as_mapping(),
                },
                execution=execution,
                observation=observation,
                log="\n".join(warnings),
                capacity=_lease_capacity(lease),
                capacity_reference=_lease_capacity_reference(lease),
                lease_placement=lease.placement,
            ),
        )


def _transmission_observation(
    work: PeriodicWork,
    construction: ConstructionManifest,
    raw: Mapping[str, object],
    execution: ProjectExecution,
    *,
    reference_surface: Mapping[str, object] | None,
) -> PeriodicObservationDocument[PeriodicTransmissionObservation]:
    coefficient = _complex_response(raw["complex_transmission"])
    power = Decimal(str(raw["power_transmission"]))
    if not (
        math.isfinite(coefficient.real)
        and math.isfinite(coefficient.imag)
        and power.is_finite()
        and Decimal(0) <= power <= Decimal(1)
    ):
        raise ValueError("periodic_transmission_response_invalid")
    status = str(raw["solver_status"])
    if status != "complete":
        raise ValueError("periodic_solver_status_invalid")
    phase = phase_from_float(math.atan2(coefficient.imag, coefficient.real))
    values: dict[str, object] = {
        "candidate": work.candidate_mapping(),
        "construction_valid": not construction.mismatches,
        "execution": execution.as_mapping(),
        "phase": {"value": format(phase, "f")},
        "phase_planes": str(raw["phase_planes"]),
        "power": {
            "leakage": format(max(Decimal(0), Decimal(1) - power), "f"),
            "useful": format(power, "f"),
        },
        "solver_status": status,
        "transmission": _encode_complex_response(coefficient),
        "warnings": _warnings(raw.get("warnings", ())),
    }
    if reference_surface is not None:
        values["reference_surface"] = reference_surface
    return decode_periodic_transmission(values)


def _polarization_observation(
    work: PeriodicWork,
    raw: Mapping[str, object],
    execution: ProjectExecution,
    *,
    reference_surface: Mapping[str, object] | None,
) -> PeriodicObservationDocument[PeriodicPolarizationObservation]:
    if str(raw["solver_status"]) != "complete":
        raise ValueError("periodic_solver_status_invalid")
    output_x = _complex_response(raw["output_x"])
    output_y = _complex_response(raw["output_y"])
    if not all(
        math.isfinite(value)
        for value in (
            output_x.real,
            output_x.imag,
            output_y.real,
            output_y.imag,
        )
    ):
        raise ValueError("periodic_polarization_response_invalid")
    values: dict[str, object] = {
        "basis": _linear_axis(work.input_basis),
        "candidate": work.candidate_mapping(),
        "execution": execution.as_mapping(),
        "output_x": _encode_complex_response(output_x),
        "output_y": _encode_complex_response(output_y),
        "phase_planes": str(raw["phase_planes"]),
        "solver_status": "complete",
        "warnings": _warnings(raw.get("warnings", ())),
    }
    if reference_surface is not None:
        values["reference_surface"] = reference_surface
    return decode_periodic_polarization(values)


def _validate_candidate(
    cell: object,
    work: PeriodicWork,
) -> None:
    expected = PeriodicCellObservation(
        work.cell_identity,
        work.height_nm,
        work.geometry,
    )
    if cell != expected:
        raise RuntimeError("periodic_response_candidate_mismatch")


def _surface_request(
    value: Mapping[str, object],
    construction: PeriodicConstruction,
    work: PeriodicWork,
    *,
    source_references: tuple[Reference, ...],
) -> ReferenceSurfaceRequest:
    return periodic_reference_surface_request(
        value,
        wavelength_m=work.wavelength_nm * 1e-9,
        period_m=work.period_nm * 1e-9,
        transmission_plane_m=(construction.transmission_plane_z_nm * 1e-9),
        medium=Medium("air"),
        requested_input_basis=(
            RequestedInputBasis.X_LINEAR
            if work.input_basis == "x linear"
            else RequestedInputBasis.Y_LINEAR
        ),
        order_regime=work.order_regime,
        source_references=source_references,
    )


def _normalize_reference_surface(
    value: Mapping[str, object],
    *,
    order_regime: str,
) -> Mapping[str, object]:
    if value.get("medium") not in {"air", "transmission medium"}:
        raise ValueError("reference_surface_medium_unrecognized")
    components = _mapping(value.get("electric_components"))
    surface = _mapping(value.get("surface"))
    return {
        **value,
        "electric_components": {
            str(name): {
                str(part): _canonical_sample_grid(samples)
                for part, samples in _mapping(encoded).items()
            }
            for name, encoded in components.items()
        },
        "incident_reference_power": _canonical_number(
            value.get("incident_reference_power")
        ),
        "medium": "air",
        "order_regime": order_regime,
        "surface": {
            **surface,
            "position_m": _canonical_number(surface.get("position_m")),
            "x_coordinates_m": _canonical_sample_grid(surface.get("x_coordinates_m")),
            "y_coordinates_m": _canonical_sample_grid(surface.get("y_coordinates_m")),
        },
        "transmitted_power": _canonical_number(value.get("transmitted_power")),
        "wavelength_m": _canonical_number(value.get("wavelength_m")),
    }


def _canonical_sample_grid(value: object) -> list[object]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("reference_surface_component_invalid")
    return [
        (
            _canonical_sample_grid(item)
            if isinstance(item, (list, tuple))
            else _canonical_number(item)
        )
        for item in value
    ]


def _canonical_number(value: object) -> str:
    if isinstance(value, bool):
        raise ValueError("reference_surface_number_invalid")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("reference_surface_number_invalid") from error
    if not number.is_finite():
        raise ValueError("reference_surface_number_invalid")
    return format(number, "f")


def _complex_response(value: object) -> complex:
    if isinstance(value, bool) or not isinstance(
        value,
        (complex, float, int),
    ):
        raise TypeError("periodic_complex_response_required")
    return complex(value)


def _encode_complex_response(value: complex) -> dict[str, str]:
    return {
        "imaginary_part": format(Decimal(str(value.imag)), "f"),
        "real_part": format(Decimal(str(value.real)), "f"),
    }


def _linear_axis(value: str) -> str:
    if value == "x linear":
        return "x"
    if value == "y linear":
        return "y"
    raise ValueError("periodic_linear_input_required")


def _warnings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError("periodic_warnings_collection_required")
    return tuple(str(item) for item in value)


def _time_attempt(attempt: _PeriodicAttempt) -> TimeBudgetAttempt:
    return TimeBudgetAttempt(
        maximum_time_fs=attempt.maximum_time_fs,
        termination=attempt.termination,
    )


def _surface_response_change(
    initial: _PeriodicAttempt,
    extended: _PeriodicAttempt,
) -> tuple[bool, dict[str, str]]:
    """
    Compare a sampled surface exactly when the admitted capability needs it.
    """

    if initial.reference_surface is None:
        if extended.reference_surface is not None:
            raise RuntimeError("reference_surface_attempts_mismatch")
        return True, {}
    if extended.reference_surface is None:
        raise RuntimeError("reference_surface_attempts_mismatch")
    return reference_surface_response_change(
        initial.reference_surface,
        extended.reference_surface,
    )


def _require_response_inventory(
    response: Mapping[str, object],
    *,
    result_name: str,
) -> None:
    required = (
        ("complex_transmission", "power_transmission")
        if result_name == "propagation"
        else ("output_x", "output_y")
    )
    for name in required:
        response[name]


def _with_numerical_warnings(
    response: Mapping[str, object],
    closure: PeriodicNumericalClosure,
) -> Mapping[str, object]:
    return {
        **response,
        "warnings": [
            *_warnings(response.get("warnings", ())),
            *closure.warnings,
        ],
    }


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("periodic_mapping_required")
    return value


def _lease_capacity(lease: SessionLease) -> CapacityObservation:
    if lease.capacity is None:
        raise RuntimeError("solver_lease_capacity_missing")
    return lease.capacity


def _lease_capacity_reference(lease: SessionLease) -> Reference:
    if lease.capacity_reference is None:
        raise RuntimeError("solver_lease_capacity_reference_missing")
    return lease.capacity_reference

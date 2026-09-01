from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from ...authority import Authority, Document, Reference
from ...authority.session import AuthoritySession
from ...canonical import encode_bytes
from ...external_activity import (
    ExternalActivityClosure,
)
from ...science.periodic_response import (
    PeriodicPolarizationRequest,
    PeriodicResponseClosure,
    PeriodicResponseContext,
    PeriodicResponseKind,
    PeriodicResponseOutcome,
    PeriodicResponseRequest,
    PeriodicResponseUnavailable,
    PeriodicResponseUnavailableReason,
    PeriodicTransmissionRequest,
)
from ...work_execution import (
    CapacityRenewalWaiting,
    WorkExecution,
    WorkWaiting,
)
from ...workstation import LANE_MEMORY_BYTES, Demand, Layout, plan
from metacraft.solvers.recorded_periodic_response import (
    RecordedPeriodicResponse,
)
from .artifacts import RunDirectory
from .lane import SessionPool, WorkstationExecution
from .material import LumericalMaterialSample, material_sample_key
from .periodic_execution import PeriodicBatchExecution
from .periodic_execution import PeriodicExecutionFault
from .probe import ProductProbe
from .qualification import (
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    CapacityObservation,
    LicenseCapacity,
    LumericalBinding,
    LumericalConfig,
    LumericalUnavailable,
    bounded_capacity,
    qualify,
)


class LumericalPeriodicResponse:
    """
    Allocate qualified capacity for bounded periodic observations.
    """

    __slots__ = (
        "_authority",
        "_binding",
        "_binding_reference",
        "_capacity",
        "_capacity_observation_reference",
        "_capacity_reference",
        "_config",
        "_layout",
        "_planner",
        "_probe",
        "_qualification_closure",
        "_renewal",
        "_run",
        "_session",
    )

    def __init__(
        self,
        *,
        authority: Authority,
        config: LumericalConfig,
        run: RunDirectory,
    ) -> None:
        """
        Qualify the product and admit its binding and tightest capacity.

        Qualification happens before a response port exists, so configuration
        or installation absence raises ``LumericalUnavailable`` at this
        composition seam. Once constructed, ``observe`` returns only the
        closed ``PeriodicResponseUnavailable`` reason family.
        """

        self._authority = authority
        self._session = AuthoritySession(authority)
        self._run = run
        self._config = config
        self._probe = ProductProbe()
        self._planner = plan
        self._renewal = Lock()
        binding, capacity, layout, qualification_closure = self._observe(
            now=None
        )
        self._binding = binding
        self._layout = layout
        self._binding_reference = self._admit_binding(binding)
        observation_reference = self._admit_capacity_observation(capacity)
        self._capacity_reference = self._open_capacity(
            capacity,
            observation_reference=observation_reference,
        )
        self._capacity_observation_reference = observation_reference
        self._capacity = capacity
        self._qualification_closure = qualification_closure

    @classmethod
    def open(
        cls,
        *,
        authority: Authority,
        config: LumericalConfig,
        run: RunDirectory,
    ) -> LumericalPeriodicResponse:
        """
        Inspect product and host at the explicit composition seam.
        """

        return cls(
            authority=authority,
            config=config,
            run=run,
        )

    @property
    def binding_reference(self) -> Reference:
        """
        Identify the admitted solver binding.
        """

        return self._binding_reference

    @property
    def product_binding(self) -> dict[str, object]:
        """
        Return the role-neutral product binding content.
        """

        return self._binding.as_mapping()

    @property
    def capacity(self) -> CapacityObservation:
        """
        Return the freshest admitted capacity observation.
        """

        return self._capacity

    @property
    def context(self) -> PeriodicResponseContext:
        """
        Return the admitted route-neutral response facts for compilation.
        """

        return PeriodicResponseContext(
            binding_reference=self._binding_reference,
            capacity_scope=self._capacity.scope,
            response_kinds=tuple(
                PeriodicResponseKind(name)
                for name in self._binding.response_capabilities
            ),
            qualification_closure=self._qualification_closure,
        )

    def observe(
        self,
        request: PeriodicResponseRequest,
    ) -> PeriodicResponseOutcome:
        """
        Observe one exhaustive physical request without interpreting its use.
        """

        if type(request) is PeriodicTransmissionRequest:
            capability = "periodic_transmission_response"
            unavailable = (
                PeriodicResponseUnavailableReason.TRANSMISSION_RESPONSE_UNQUALIFIED
            )
        elif type(request) is PeriodicPolarizationRequest:
            capability = "periodic_polarization_response"
            unavailable = (
                PeriodicResponseUnavailableReason.POLARIZATION_RESPONSE_UNQUALIFIED
            )
        else:
            raise TypeError("periodic_response_request_unsupported")
        if not self._supports(capability):
            return PeriodicResponseUnavailable(
                request.request_identity,
                unavailable,
                self._closure(
                    request.request_identity,
                    ExternalActivityClosure.none(),
                ),
            )
        self._validate_request(request)
        try:
            execution = self._open_batch(request.request_identity)
            observed = (
                execution.observe_transmission(request)
                if type(request) is PeriodicTransmissionRequest
                else execution.observe_polarization(request)
            )
        except LumericalUnavailable as error:
            return PeriodicResponseUnavailable(
                request.request_identity,
                _unavailability_reason(error.reason),
                self._closure(
                    request.request_identity,
                    ExternalActivityClosure.none(),
                ),
            )
        except PeriodicExecutionFault as failure:
            if not isinstance(failure.fault, LumericalUnavailable):
                raise failure.fault
            return PeriodicResponseUnavailable(
                request.request_identity,
                _unavailability_reason(failure.fault.reason),
                self._closure(
                    request.request_identity,
                    failure.activity_closure,
                ),
            )
        if isinstance(observed, WorkWaiting):
            return PeriodicResponseUnavailable(
                request.request_identity,
                _unavailability_reason(observed.reason),
                self._closure(
                    request.request_identity,
                    observed.activity_closure,
                ),
            )
        return observed

    def _supports(self, capability: str) -> bool:
        return capability in self._binding.response_capabilities

    def _validate_request(
        self,
        request: PeriodicTransmissionRequest | PeriodicPolarizationRequest,
    ) -> None:
        if any(
            item.binding_reference != self._binding_reference for item in request.items
        ):
            raise ValueError("periodic_response_binding_mismatch")
        if any(item.capacity_scope != self._capacity.scope for item in request.items):
            raise ValueError("periodic_response_capacity_scope_mismatch")

    def _open_batch(
        self,
        request_identity: str,
    ) -> PeriodicBatchExecution:
        """
        Open one batch whose capacity renewals stay behind the Adapter seam.
        """

        with self._renewal:
            run = self._run.for_response(request_identity)
            run.record_response_capacity(
                capacity_reference=self._capacity_reference,
                admitted_lanes=self._capacity.limit,
                lumerical_gui_limit=self._capacity.lumerical_gui_limit,
                lumerical_solve_limit=self._capacity.lumerical_solve_limit,
                workstation_lanes=self._capacity.workstation_limit,
            )
            execution = WorkstationExecution(
                Path(self._binding.python_api),
                self._binding.license_server,
            )
            sessions = SessionPool(
                execution,
                self._layout.lanes[: self._capacity.limit],
                capacity_reference=self._capacity_reference,
                capacity=self._capacity,
            )
            return PeriodicBatchExecution(
                work_execution=WorkExecution(
                    AuthoritySession(self._authority),
                    capacity_reference=self._capacity_reference,
                    capacity=self._capacity,
                    renew_capacity=lambda: self._renew_capacity(
                        sessions,
                        should_force=True,
                    ),
                ),
                sessions=sessions,
                run=run,
                should_sample_reference_surface=self._supports(
                    PERIODIC_REFERENCE_SURFACE_RESPONSE
                ),
                qualification_closure=self._qualification_closure,
            )

    def _observe(
        self,
        *,
        now: datetime | None,
    ) -> tuple[
        LumericalBinding,
        CapacityObservation,
        Layout,
        ExternalActivityClosure,
    ]:
        planned: list[Layout] = []

        def planner(demand: Demand) -> Layout:
            """
            Wrap the planner, recording each layout for capacity derivation.
            """

            layout = self._planner(demand)
            planned.append(layout)
            return layout

        observed = qualify(
            self._config,
            self._probe,
            planner=planner,
            now=now,
        )
        if observed.binding is None or observed.capacity is None:
            finding = ",".join(observed.findings) or "unavailable"
            raise LumericalUnavailable(finding)
        return (
            observed.binding,
            observed.capacity,
            planned[-1],
            observed.activity_closure,
        )

    def _closure(
        self,
        request_identity: str,
        observation: ExternalActivityClosure,
    ) -> PeriodicResponseClosure:
        """
        Bind current-call activity to one exact response request.
        """

        return PeriodicResponseClosure(
            request_identity,
            self._qualification_closure,
            observation,
        )

    def _renew_capacity(
        self,
        sessions: SessionPool | None = None,
        *,
        should_force: bool = False,
    ) -> tuple[Reference, CapacityObservation] | CapacityRenewalWaiting:
        with self._renewal:
            if sessions is not None and not sessions.uses(
                self._capacity_reference,
                self._capacity,
            ):
                sessions.replace(
                    lanes=self._layout.lanes[: self._capacity.limit],
                    capacity_reference=self._capacity_reference,
                    capacity=self._capacity,
                )
                return self._capacity_reference, self._capacity
            if not should_force and self._capacity.is_fresh_at(datetime.now(UTC)):
                return self._capacity_reference, self._capacity
            try:
                license_capacity: LicenseCapacity = self._probe.refresh_capacity(
                    self._config
                )
                layout = self._planner(
                    Demand(
                        workers=min(
                            license_capacity.lumerical_gui_limit,
                            license_capacity.lumerical_solve_limit,
                        ),
                        worker_memory_bytes=LANE_MEMORY_BYTES,
                    )
                )
                capacity = bounded_capacity(
                    self._config,
                    self._binding,
                    license_capacity,
                    layout,
                )
            except LumericalUnavailable as error:
                return CapacityRenewalWaiting(error.reason)
            if capacity is None:
                return CapacityRenewalWaiting("capacity_not_positive")
            previous = self._capacity_reference
            observation_reference = self._admit_capacity_observation(capacity)
            current = self._session.current_reference(f"capacity:{capacity.scope}")
            if (
                current == previous
                and capacity.scope == self._capacity.scope
                and capacity.limit == self._capacity.limit
                and observation_reference == self._capacity_observation_reference
            ):
                reference = previous
            else:
                reference = self._admit_capacity(
                    capacity,
                    observation_reference=observation_reference,
                    supersedes=current,
                )
            if sessions is not None:
                try:
                    sessions.replace(
                        lanes=layout.lanes[: capacity.limit],
                        capacity_reference=reference,
                        capacity=capacity,
                    )
                except BaseException:
                    if sessions.uses(reference, capacity):
                        self._capacity = capacity
                        self._capacity_observation_reference = observation_reference
                        self._capacity_reference = reference
                        self._layout = layout
                    raise
            self._capacity = capacity
            self._capacity_observation_reference = observation_reference
            self._capacity_reference = reference
            self._layout = layout
            return reference, capacity

    def _admit_binding(self, binding: LumericalBinding) -> Reference:
        return self._session.admit_document(
            Document(
                "metacraft.solver.lumerical_binding",
                binding.as_mapping(),
            )
        )

    def _admit_capacity(
        self,
        capacity: CapacityObservation,
        *,
        observation_reference: Reference,
        supersedes: Reference | None,
    ) -> Reference:
        return self._session.admit_capacity(
            scope=capacity.scope,
            limit=capacity.limit,
            qualification_references=(
                self._binding_reference,
                observation_reference,
            ),
            supersedes=supersedes,
        )

    def _admit_capacity_observation(
        self,
        capacity: CapacityObservation,
    ) -> Reference:
        """
        Admit the exact time-bounded observation that names this generation.
        """

        return self._session.admit_object(
            encode_bytes(capacity.as_mapping()),
            media_type=(
                "application/vnd.metacraft." "lumerical-capacity-observation+json"
            ),
            descriptive_metadata={"object_kind": "LumericalCapacityObservation"},
        )

    def _open_capacity(
        self,
        capacity: CapacityObservation,
        *,
        observation_reference: Reference,
    ) -> Reference:
        """
        Reuse or supersede the exact current capacity when reopening.
        """

        key = f"capacity:{capacity.scope}"
        reference = self._session.current_reference(key)
        if reference is None:
            return self._admit_capacity(
                capacity,
                observation_reference=observation_reference,
                supersedes=None,
            )
        expected = Document(
            "metacraft.authority.capacity",
            {
                "limit": capacity.limit,
                "qualification_references": [
                    self._binding_reference.as_mapping(),
                    observation_reference.as_mapping(),
                ],
                "scope": capacity.scope,
            },
        )
        if self._session.fetch(reference) == expected.to_bytes():
            return reference
        return self._admit_capacity(
            capacity,
            observation_reference=observation_reference,
            supersedes=reference,
        )


def _unavailability_reason(
    reason: str,
) -> PeriodicResponseUnavailableReason:
    """
    Translate one product-owned absence without caller text parsing.
    """

    if reason == "configuration_incomplete":
        return PeriodicResponseUnavailableReason.CONFIGURATION_INCOMPLETE
    if reason in {"license_unavailable", "license_utility_not_found"}:
        return PeriodicResponseUnavailableReason.LICENSE_UNAVAILABLE
    if reason == "capacity_not_positive":
        return PeriodicResponseUnavailableReason.CAPACITY_NOT_POSITIVE
    if reason == "capacity_stale":
        return PeriodicResponseUnavailableReason.CAPACITY_STALE
    return PeriodicResponseUnavailableReason.NATIVE_UNAVAILABLE


def restore_material_sample(
    authority: Authority,
    *,
    sample_reference: Reference,
) -> tuple[LumericalMaterialSample, Reference]:
    """
    Restore one binding's sample from the Authority view alone.
    """

    sample = LumericalMaterialSample.from_document_bytes(
        authority.fetch(sample_reference)
    )
    material_sample_key(sample)
    return sample, sample_reference

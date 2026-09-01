from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
from typing import cast

import numpy
import pytest

from metacraft.authority import Authority, Document, Reference
from metacraft.authority.session import AuthoritySession
from metacraft.canonical import encode_bytes
from metacraft.field.sample import (
    ComponentBasis,
    CoordinateFrame,
    FieldComponent,
    Medium,
)
from metacraft.field.rectilinear import RectilinearPlane
from metacraft.external_activity import (
    ExternalActivityClosure,
    ExternalActivityOrigin,
)
from metacraft.science.metalens.reference_surface_evidence import (
    admit_reference_surfaces,
)
from metacraft.science.metalens import reference_surface_evidence
from metacraft.science.periodic_response import (
    AdmittedPeriodicTransmission,
    CircularCrossSection,
    EllipticalCrossSection,
    ObservedPeriodicPolarization,
    ObservedPeriodicTransmission,
    PeriodicMaterials,
    PeriodicObservationIncomplete,
    PeriodicPolarizationObservation,
    PeriodicCellObservation,
    PeriodicComplexValue,
    PeriodicPolarizationRequest,
    PeriodicReferenceSurfaceObservation,
    PeriodicResponseUnavailableReason,
    PeriodicResponseUnavailable,
    PeriodicResponseContext,
    PeriodicResponseKind,
    PeriodicTransmissionIncomplete,
    PeriodicObservationIncompleteReason,
    PeriodicTransmissionObservation,
    PeriodicTransmissionRequest,
    PeriodicWork,
    periodic_request_identity,
    RectangularCrossSection,
    PeriodicResponseClosure,
    decode_periodic_polarization,
    decode_periodic_observation_incomplete,
    decode_periodic_reference_surface,
    decode_periodic_transmission,
)
from metacraft.solvers.recorded_periodic_response import (
    RecordedPeriodicResponse,
)
from metacraft.solvers.lumerical_fdtd.artifacts import RunDirectory
from metacraft.solvers.lumerical_fdtd.periodic_response import (
    LumericalPeriodicResponse,
)
from metacraft.solvers.lumerical_fdtd.lane import (
    SessionPool,
    WorkstationExecution,
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
from metacraft.solvers.lumerical_fdtd.periodic_execution import (
    PeriodicBatchExecution,
)
from metacraft.solvers.lumerical_fdtd.template import (
    prepare_periodic_construction,
)
from metacraft.work_execution import (
    PERMITTED_WORK_SCHEMA,
    CompletedWorkExecution,
    WorkExecution,
    WorkRequest,
    WorkWaiting,
)
from metacraft.workstation import Lane, StaleLane
from tests.lumerical_fixtures import workstation_layout
from tests.solver_fakes import (
    ActiveEngines,
    FakeSession,
    FakeSessionFactory,
)


def test_reference_surface_formation_failure_precedes_all_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callbacks = 0

    def count_admission(*_args: object, **_kwargs: object) -> Reference:
        nonlocal callbacks
        callbacks += 1
        raise AssertionError("admission_must_not_run")

    monkeypatch.setattr(
        reference_surface_evidence,
        "_select_reference_surfaces",
        lambda *_args, **_kwargs: (),
    )

    def fail_formation(*_args: object, **_kwargs: object) -> object:
        raise ValueError("formation_failed")

    monkeypatch.setattr(
        reference_surface_evidence,
        "form_uniform_reference_surfaces",
        fail_formation,
    )

    with pytest.raises(ValueError, match="formation_failed"):
        admit_reference_surfaces(
            cast(PeriodicTransmissionRequest, object()),
            cast(ObservedPeriodicTransmission, object()),
            admit_object=count_admission,
            admit_document=count_admission,
        )

    assert callbacks == 0


@dataclass(frozen=True, slots=True)
class _Capacity:
    scope: str
    limit: int
    fresh_until: datetime

    def is_fresh_at(self, value: datetime) -> bool:
        return value <= self.fresh_until

    def as_mapping(self) -> dict[str, object]:
        return {
            "fresh_until": self.fresh_until.isoformat().replace("+00:00", "Z"),
            "limit": self.limit,
            "scope": self.scope,
        }


def _admit_periodic_fixture(
    session: AuthoritySession,
    execution: WorkExecution,
    work: PeriodicWork,
    values: dict[str, object],
) -> tuple[Reference, Reference]:
    permit = session.reserve_work(
        Document(PERMITTED_WORK_SCHEMA, {"work": work.work_identity}),
        capacity_reference=execution.capacity_reference,
        scope=work.capacity_scope,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )
    assert isinstance(permit, Reference)
    decision = session.admit_receipt(
        Document(work.observation_schema, values),
        permit_reference=permit,
    )
    assert decision.body_reference is not None
    assert decision.proposal_reference is not None
    return decision.body_reference, decision.proposal_reference


def _transmission_values() -> dict[str, object]:
    return {
        "candidate": {
            "diameter_nm": 180,
            "height_nm": 600,
            "name": "circular-pillar-height-0600nm-diameter-0180nm",
            "shape": "circular pillar",
        },
        "construction_valid": True,
        "execution": {
            "native": False,
            "placement": {"lane": "fixture"},
            "project": "fixture.fsp",
            "return_code": 0,
            "source": "fixture",
        },
        "phase": {"value": "0.250000000000000"},
        "phase_planes": "source to transmission",
        "power": {"leakage": "0.2", "useful": "0.8"},
        "solver_status": "complete",
        "transmission": {
            "imaginary_part": "0.2",
            "real_part": "0.7",
        },
        "warnings": (),
    }


def test_transmission_observation_exposes_only_typed_scientific_fields() -> None:
    observation = PeriodicTransmissionObservation(
        cell=PeriodicCellObservation(
            cell_identity="circular-pillar-height-0600nm-diameter-0180nm",
            height_nm=600,
            geometry=CircularCrossSection(180),
        ),
        transmission=PeriodicComplexValue(
            real_part=Decimal("0.7"),
            imaginary_part=Decimal("0.1"),
        ),
        useful_power=Decimal("0.8"),
        leakage_power=Decimal("0.2"),
        realized_phase=Decimal("0.25"),
        phase_planes="grating_s_params",
        warnings=(),
        reference_surface=None,
    )

    assert observation.cell.height_nm == 600
    assert observation.transmission.real_part == Decimal("0.7")
    assert not hasattr(observation, "values")
    assert not hasattr(observation, "as_mapping")


def test_polarization_observation_exposes_exact_basis_response_fields() -> None:
    observation = PeriodicPolarizationObservation(
        input_basis="x",
        cell=PeriodicCellObservation(
            cell_identity="rectangular-fin-height-0600nm-length-0140nm-width-0080nm",
            height_nm=600,
            geometry=RectangularCrossSection(80, 140),
        ),
        output_x=PeriodicComplexValue(Decimal("1"), Decimal("0")),
        output_y=PeriodicComplexValue(Decimal("0"), Decimal("0")),
        phase_planes="grating_s_params",
        warnings=(),
        reference_surface=None,
    )

    assert observation.input_basis == "x"
    assert observation.output_x.real_part == Decimal("1")
    assert not hasattr(observation, "values")


def test_reference_surface_observation_exposes_field_language() -> None:
    samples = numpy.ones((3, 4), dtype="<c16")
    samples.setflags(write=False)
    observation = PeriodicReferenceSurfaceObservation(
        requested_input_basis="x linear",
        output_basis=ComponentBasis.CARTESIAN,
        order_regime="multi order",
        surface=RectilinearPlane(
            position_m=1e-6,
            horizontal_coordinates_m=numpy.asarray((-1e-7, -0.4e-7, 0.2e-7, 1e-7)),
            vertical_coordinates_m=numpy.asarray((-1e-7, 0.0, 1e-7)),
        ),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        electric_components=tuple(
            FieldComponent(name, samples)
            for name in ComponentBasis.CARTESIAN.components
        ),
        incident_reference_power=Decimal("1"),
        transmitted_power=Decimal("0.5"),
        wavelength_m=Decimal("0.0000004"),
    )

    assert observation.surface.shape == (3, 4)
    assert tuple(component.name for component in observation.electric_components) == (
        "x",
        "y",
        "z",
    )
    assert not hasattr(observation, "values")


def _surface_values() -> dict[str, object]:
    zeros = tuple(tuple("0" for _ in range(4)) for _ in range(3))
    return {
        "electric_components": {
            "x": {
                "imaginary": zeros,
                "real": zeros,
            },
            "y": {
                "imaginary": zeros,
                "real": zeros,
            },
            "z": {
                "imaginary": zeros,
                "real": zeros,
            },
        },
        "frame": {
            "normal_axis": "z",
            "propagation_direction": "positive",
            "sample_order": ("y", "x"),
        },
        "incident_reference_power": "1",
        "medium": "air",
        "order_regime": "multi order",
        "output_basis": "cartesian",
        "requested_input_basis": "x linear",
        "surface": {
            "position_m": "0.000001",
            "x_coordinates_m": (
                "-0.0000001",
                "-0.00000004",
                "0.00000002",
                "0.0000001",
            ),
            "y_coordinates_m": (
                "-0.0000001",
                "0",
                "0.0000001",
            ),
        },
        "transmitted_power": "0.75",
        "wavelength_m": "0.00000155",
    }


def _polarization_values(
    work: PeriodicWork,
    *,
    basis: str,
    has_extra_candidate_field: bool = False,
) -> dict[str, object]:
    candidate = work.candidate_mapping()
    if has_extra_candidate_field:
        candidate["unexpected"] = "drift"
    return {
        "basis": basis,
        "candidate": candidate,
        "execution": {
            "native": False,
            "placement": {"lane": "fixture"},
            "project": "fixture.fsp",
            "return_code": 0,
            "source": "fixture",
        },
        "output_x": {
            "imaginary_part": "0.125",
            "real_part": "0.875",
        },
        "output_y": {
            "imaginary_part": "0.5",
            "real_part": "-0.25",
        },
        "phase_planes": "grating_s_params",
        "solver_status": "complete",
        "warnings": (),
    }


def _recorded_setup(
    tmp_path: Path,
) -> tuple[
    Authority,
    AuthoritySession,
    Reference,
    Reference,
    Reference,
    WorkExecution,
]:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    binding = session.admit_document(Document("fixture.binding", {"solver": "fixture"}))
    atom = session.admit_document(Document("fixture.material", {"family": "silicon"}))
    substrate = session.admit_document(
        Document("fixture.material", {"family": "silica"})
    )
    capacity = _Capacity(
        "solver:fixture",
        4,
        datetime.now(UTC) + timedelta(minutes=5),
    )
    observation = session.admit_object(
        encode_bytes(capacity.as_mapping()),
        media_type="application/vnd.metacraft.fixture-capacity+json",
        descriptive_metadata={"object_kind": "FixtureCapacity"},
    )
    capacity_reference = session.admit_capacity(
        scope=capacity.scope,
        limit=capacity.limit,
        qualification_references=(binding, observation),
    )
    return (
        authority,
        session,
        binding,
        atom,
        substrate,
        WorkExecution(
            session,
            capacity_reference=capacity_reference,
            capacity=capacity,
        ),
    )


def _recorded_response(
    session: AuthoritySession,
    binding_reference: Reference,
) -> RecordedPeriodicResponse:
    return RecordedPeriodicResponse(
        session,
        context=PeriodicResponseContext(
            binding_reference=binding_reference,
            capacity_scope="solver:fixture",
            response_kinds=tuple(PeriodicResponseKind),
            qualification_closure=ExternalActivityClosure.recorded(),
        ),
    )


def _work(
    binding: Reference,
    atom: Reference,
    substrate: Reference,
    *,
    work_identity: str = "sha256:stable-work",
    observation_schema: str = "fixture.periodic.transmission",
    input_basis: str = "x linear",
) -> PeriodicWork:
    return PeriodicWork(
        cell_identity="circular-pillar-height-0600nm-diameter-0180nm",
        work_identity=work_identity,
        observation_schema=observation_schema,
        wavelength_nm=1550,
        period_nm=650,
        height_nm=600,
        geometry=CircularCrossSection(180),
        materials=PeriodicMaterials(
            atom_native_identity="Si (Silicon) - Palik",
            atom_refractive_index=Decimal("3.48"),
            atom_source_reference=atom,
            substrate_native_identity="SiO2 (Glass) - Palik",
            substrate_refractive_index=Decimal("1.45"),
            substrate_source_reference=substrate,
        ),
        source_references=(atom, substrate),
        binding_reference=binding,
        capacity_scope="solver:fixture",
        input_basis=input_basis,
        output_basis="transverse linear",
        order_regime="zeroth order",
    )


def _physical_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    result: dict[str, object],
    response_qualifications: tuple[PeriodicResponseQualification, ...],
    should_stale_once: bool = False,
) -> tuple[
    LumericalPeriodicResponse,
    PeriodicWork,
    FakeSessionFactory,
    Authority,
]:
    authority = Authority(tmp_path / "live-authority")
    session = AuthoritySession(authority)
    binding = LumericalBinding(
        executable=str(tmp_path / "fdtd-solutions.exe"),
        engine=str(tmp_path / "fdtd-engine.exe"),
        python_api=str(tmp_path / "lumapi.py"),
        product_version="fixture",
        api_identity="fixture-api",
        license_server="fixture-license",
        resource_identity="fixture-cpu",
        response_qualifications=response_qualifications,
    )
    binding_reference = session.admit_document(
        Document(
            "metacraft.solver.lumerical_binding",
            binding.as_mapping(),
        )
    )
    atom = session.admit_document(Document("fixture.material", {"family": "silicon"}))
    substrate = session.admit_document(
        Document("fixture.material", {"family": "silica"})
    )
    observed_at = datetime.now(UTC)
    capacity = CapacityObservation(
        scope="lumerical-fdtd/fixture",
        limit=1,
        observed_at=observed_at,
        fresh_until=observed_at + timedelta(minutes=5),
        lumerical_gui_limit=1,
        lumerical_solve_limit=1,
        workstation_limit=1,
    )
    capacity_observation = session.admit_object(
        encode_bytes(capacity.as_mapping()),
        media_type=("application/vnd.metacraft." "lumerical-capacity-observation+json"),
        descriptive_metadata={"object_kind": "LumericalCapacityObservation"},
    )
    capacity_reference = session.admit_capacity(
        scope=capacity.scope,
        limit=capacity.limit,
        qualification_references=(
            binding_reference,
            capacity_observation,
        ),
    )
    work = replace(
        _work(binding_reference, atom, substrate),
        capacity_scope=capacity.scope,
        output_basis="transverse linear",
    )
    factory = FakeSessionFactory(
        active=ActiveEngines(),
        result=result,
    )
    lane = workstation_layout(observed_at).lanes[0]
    run = RunDirectory(tmp_path / "live-run")
    stale_open_count = 0

    def open_batch(
        _response: LumericalPeriodicResponse,
        _request_identity: str,
    ) -> PeriodicBatchExecution:
        nonlocal stale_open_count

        def open_session(selected_lane: Lane) -> FakeSession:
            nonlocal stale_open_count
            if should_stale_once and stale_open_count == 0:
                stale_open_count += 1
                raise StaleLane("fixture_stale_lane")
            return factory(selected_lane)

        sessions = SessionPool(
            WorkstationExecution(
                Path(binding.python_api),
                binding.license_server,
            ),
            (lane,),
            capacity_reference=capacity_reference,
            capacity=capacity,
            _open_session=open_session,
        )
        work_execution = WorkExecution(
            AuthoritySession(authority),
            capacity_reference=capacity_reference,
            capacity=capacity,
            renew_capacity=lambda: _renew_fixture_capacity(
                sessions,
                lane=lane,
                capacity_reference=capacity_reference,
                capacity=capacity,
            ),
        )
        return PeriodicBatchExecution(
            work_execution=work_execution,
            sessions=sessions,
            run=run,
            should_sample_reference_surface=(
                PERIODIC_REFERENCE_SURFACE_RESPONSE in binding.response_capabilities
            ),
            qualification_closure=_response._qualification_closure,
        )

    monkeypatch.setattr(
        LumericalPeriodicResponse,
        "_open_batch",
        open_batch,
    )
    response = object.__new__(LumericalPeriodicResponse)
    response._binding = binding
    response._binding_reference = binding_reference
    response._capacity = capacity
    response._authority = authority
    response._session = session
    response._qualification_closure = ExternalActivityClosure.recorded()
    return response, work, factory, authority


def _renew_fixture_capacity(
    sessions: SessionPool,
    *,
    lane: Lane,
    capacity_reference: Reference,
    capacity: CapacityObservation,
) -> tuple[Reference, CapacityObservation]:
    sessions.replace(
        lanes=(lane,),
        capacity_reference=capacity_reference,
        capacity=capacity,
    )
    return capacity_reference, capacity


def _transmission_result() -> dict[str, object]:
    return {
        "complex_transmission": complex(0.75, -0.125),
        "phase_planes": "metamaterial_surfaces",
        "power_transmission": 0.578125,
        "solver_status": "complete",
        "warnings": ["fixture warning"],
    }


def _termination(
    status: int,
    *,
    simulated_time_fs: str,
    terminal_autoshutoff: str,
) -> dict[str, object]:
    return {
        "autoshutoff_threshold": "0.00001",
        "native_status": status,
        "outcome": {1: "maximum_time", 2: "autoshutoff"}[status],
        "simulated_time_fs": simulated_time_fs,
        "terminal_autoshutoff": terminal_autoshutoff,
    }


def test_lumerical_transmission_extends_once_after_invalid_ordinary_power(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary = {**_transmission_result(), "power_transmission": 1.027}
    extended = {**_transmission_result(), "power_transmission": 0.9335}
    response, work, sessions, authority = _physical_response(
        tmp_path,
        monkeypatch,
        result={
            "_responses": {
                "propagation": [ordinary, extended],
                "termination": [
                    _termination(
                        1,
                        simulated_time_fs="2000",
                        terminal_autoshutoff="0.001",
                    ),
                    _termination(
                        2,
                        simulated_time_fs="3400",
                        terminal_autoshutoff="0.000009",
                    ),
                ],
            }
        },
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity("transmission", (work.work_identity,)),
        (work,),
    )

    observed = response.observe(request)

    assert isinstance(observed, ObservedPeriodicTransmission)
    assert observed.items[0].observation.useful_power == Decimal("0.9335")
    assert "periodic_time_budget_extended" in (observed.items[0].observation.warnings)
    assert len(sessions.sessions) == 1
    run = RunDirectory(tmp_path / "live-run")
    directory = run.candidate(work.cell_identity)
    record = run.restore_work(directory)
    numerical = cast(
        dict[str, object],
        record.construction["numerical_closure"],
    )
    assert numerical["disposition"] == "autoshutoff_after_extension"
    assert len(cast(list[object], numerical["attempts"])) == 2
    assert all(path.is_file() for path in run.archived_ordinary_projects(directory))
    assert (directory / "ordinary" / "termination.json").is_file()


def test_lumerical_transmission_accepts_stable_residual_energy_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary = _transmission_result()
    extended = {
        **ordinary,
        "complex_transmission": complex(0.7501, -0.1249),
        "power_transmission": 0.5783,
    }
    response, work, _sessions, _authority = _physical_response(
        tmp_path,
        monkeypatch,
        result={
            "_responses": {
                "propagation": [ordinary, extended],
                "termination": [
                    _termination(
                        1,
                        simulated_time_fs="2000",
                        terminal_autoshutoff="0.002",
                    ),
                    _termination(
                        1,
                        simulated_time_fs="4000",
                        terminal_autoshutoff="0.0012",
                    ),
                ],
            }
        },
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity("transmission", (work.work_identity,)),
        (work,),
    )

    observed = response.observe(request)

    assert isinstance(observed, ObservedPeriodicTransmission)
    warnings = observed.items[0].observation.warnings
    assert "periodic_time_budget_extended" in warnings
    assert "periodic_residual_energy_after_extension" in warnings
    record = RunDirectory(tmp_path / "live-run").restore_work(
        tmp_path / "live-run" / work.cell_identity
    )
    numerical = cast(
        dict[str, object],
        record.construction["numerical_closure"],
    )
    assert numerical["disposition"] == "converged_by_extension"
    assert numerical["response_change"] is not None


def test_lumerical_transmission_refuses_an_unstable_second_maximum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordinary = _transmission_result()
    extended = {
        **ordinary,
        "complex_transmission": complex(-0.2, 0.8),
        "power_transmission": 0.8,
    }
    response, work, sessions, authority = _physical_response(
        tmp_path,
        monkeypatch,
        result={
            "_responses": {
                "propagation": [ordinary, extended],
                "termination": [
                    _termination(
                        1,
                        simulated_time_fs="2000",
                        terminal_autoshutoff="0.02",
                    ),
                    _termination(
                        1,
                        simulated_time_fs="4000",
                        terminal_autoshutoff="0.01",
                    ),
                ],
            }
        },
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity("transmission", (work.work_identity,)),
        (work,),
    )

    outcome = response.observe(request)

    assert isinstance(outcome, PeriodicTransmissionIncomplete)
    assert outcome.items == ()
    assert len(outcome.incomplete_items) == 1
    incomplete = outcome.incomplete_items[0]
    assert incomplete.work_identity == work.work_identity
    assert incomplete.outcome.reason is (
        PeriodicObservationIncompleteReason.TIME_BUDGET_EXHAUSTED
    )
    assert len(incomplete.outcome.attempts) == 2

    replayed = RecordedPeriodicResponse(
        AuthoritySession(authority),
        context=response.context,
    ).observe(request)
    assert isinstance(replayed, PeriodicTransmissionIncomplete)
    assert replayed.items == outcome.items
    assert replayed.incomplete_items == outcome.incomplete_items

    assert len(sessions.sessions) == 1
    assert sessions.sessions[0]._solve_count == 2
    refusal_path = (
        RunDirectory(tmp_path / "live-run").candidate(work.cell_identity)
        / "numerical-refusal.json"
    )
    refusal = json.loads(refusal_path.read_text(encoding="utf-8"))
    assert refusal["reason"] == "periodic_time_budget_exhausted"
    assert len(refusal["attempts"]) == 2


def test_periodic_incompletion_rejects_inconsistent_numerical_evidence() -> None:
    outcome = PeriodicObservationIncomplete(
        work_identity="sha256:bounded-numerical-incompletion",
        reason=PeriodicObservationIncompleteReason.TIME_BUDGET_EXHAUSTED,
        time_budget={
            "autoshutoff_threshold": "0.00001",
            "causal_floor_fs": 1000,
            "extended_maximum_fs": 4000,
            "ordinary_maximum_fs": 2000,
            "resonance_guard_fs": 1000,
        },
        attempts=(
            {
                "maximum_time_fs": 2000,
                "termination": _termination(
                    1,
                    simulated_time_fs="2000",
                    terminal_autoshutoff="0.02",
                ),
            },
            {
                "maximum_time_fs": 4000,
                "termination": _termination(
                    1,
                    simulated_time_fs="4000",
                    terminal_autoshutoff="0.01",
                ),
            },
        ),
        response_change={"power": "0.2"},
    )
    mutations = []
    status_drift = deepcopy(outcome.as_mapping())
    status_drift["attempts"][0]["termination"]["native_status"] = 2
    mutations.append(status_drift)
    maximum_drift = deepcopy(outcome.as_mapping())
    maximum_drift["attempts"][1]["maximum_time_fs"] = 5000
    mutations.append(maximum_drift)
    threshold_drift = deepcopy(outcome.as_mapping())
    threshold_drift["attempts"][0]["termination"]["autoshutoff_threshold"] = "0.001"
    mutations.append(threshold_drift)

    for values in mutations:
        with pytest.raises(ValueError, match="periodic_incompletion_invalid"):
            decode_periodic_observation_incomplete(values)


def _surface_result(work: PeriodicWork) -> dict[str, object]:
    construction = prepare_periodic_construction(work)
    zeros = [[0.0] * 3 for _ in range(3)]
    ones = [[1.0] * 3 for _ in range(3)]
    half_period_m = work.period_nm * 1e-9 / 2
    closed_axis = [
        format(-half_period_m, ".17g"),
        "0",
        format(half_period_m, ".17g"),
    ]
    return {
        "electric_components": {
            "x": {"imaginary": zeros, "real": ones},
            "y": {"imaginary": zeros, "real": zeros},
            "z": {"imaginary": zeros, "real": zeros},
        },
        "frame": {
            "normal_axis": "z",
            "propagation_direction": "positive",
            "sample_order": ["y", "x"],
        },
        "incident_reference_power": "1",
        "medium": "transmission medium",
        "order_regime": work.order_regime,
        "output_basis": "cartesian",
        "requested_input_basis": work.input_basis,
        "surface": {
            "position_m": format(
                construction.transmission_plane_z_nm * 1e-9,
                ".17g",
            ),
            "x_coordinates_m": closed_axis,
            "y_coordinates_m": closed_axis,
        },
        "transmitted_power": "0.5",
        "wavelength_m": format(work.wavelength_nm * 1e-9, ".17g"),
    }


def test_lumerical_residual_acceptance_includes_the_sampled_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured: dict[str, object] = {
        "_responses": {
            "propagation": [_transmission_result(), _transmission_result()],
            "termination": [
                _termination(
                    1,
                    simulated_time_fs="2000",
                    terminal_autoshutoff="0.002",
                ),
                _termination(
                    1,
                    simulated_time_fs="4000",
                    terminal_autoshutoff="0.0012",
                ),
            ],
        }
    }
    response, work, sessions, _authority = _physical_response(
        tmp_path,
        monkeypatch,
        result=configured,
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    ordinary_surface = _surface_result(work)
    changed_surface = deepcopy(ordinary_surface)
    changed_components = cast(
        dict[str, object],
        changed_surface["electric_components"],
    )
    changed_x = cast(dict[str, object], changed_components["x"])
    changed_x["real"] = [[2.0] * 3 for _ in range(3)]
    responses = cast(dict[str, object], configured["_responses"])
    responses["reference_surface"] = [ordinary_surface, changed_surface]
    request = PeriodicTransmissionRequest(
        periodic_request_identity("transmission", (work.work_identity,)),
        (work,),
    )

    outcome = response.observe(request)

    assert isinstance(outcome, PeriodicTransmissionIncomplete)
    assert outcome.incomplete_items[0].outcome.reason is (
        PeriodicObservationIncompleteReason.TIME_BUDGET_EXHAUSTED
    )

    assert sessions.sessions[0]._solve_count == 2


def test_sealed_requests_reject_incomplete_polarization_and_unknown_values(
    tmp_path: Path,
) -> None:
    _authority, session, binding, atom, substrate, _execution = _recorded_setup(
        tmp_path
    )
    x_work = replace(
        _work(binding, atom, substrate),
        geometry=RectangularCrossSection(80, 140),
        output_basis="cartesian",
    )

    with pytest.raises(
        ValueError,
        match="periodic_polarization_bases_incomplete",
    ):
        PeriodicPolarizationRequest(
            periodic_request_identity(
                "polarization",
                (x_work.work_identity,),
            ),
            (x_work,),
        )

    class _UnknownRequest:
        pass

    with pytest.raises(
        TypeError,
        match="periodic_response_request_unsupported",
    ):
        _recorded_response(session, binding).observe(
            _UnknownRequest()  # type: ignore[arg-type]
        )


def test_sealed_transmission_requires_isotropic_transverse_work(
    tmp_path: Path,
) -> None:
    _authority, _session, binding, atom, substrate, _execution = _recorded_setup(
        tmp_path
    )
    valid = _work(binding, atom, substrate)
    PeriodicTransmissionRequest(
        periodic_request_identity(
            "transmission",
            (valid.work_identity,),
        ),
        (valid,),
    )
    for invalid in (
        replace(valid, output_basis="cartesian"),
        replace(valid, geometry=RectangularCrossSection(80, 140)),
        replace(valid, input_basis="left circular"),
    ):
        with pytest.raises(
            ValueError,
            match="periodic_transmission_variant_invalid",
        ):
            PeriodicTransmissionRequest(
                periodic_request_identity(
                    "transmission",
                    (invalid.work_identity,),
                ),
                (invalid,),
            )
    mixed_basis = replace(
        valid,
        work_identity="sha256:mixed-transmission-basis",
        input_basis="y linear",
    )
    with pytest.raises(
        ValueError,
        match="periodic_transmission_variant_invalid",
    ):
        PeriodicTransmissionRequest(
            periodic_request_identity(
                "transmission",
                (valid.work_identity, mixed_basis.work_identity),
            ),
            (valid, mixed_basis),
        )


@pytest.mark.parametrize(
    ("field", "value", "finding"),
    [
        (
            "wavelength_nm",
            1310,
            "periodic_response_batch_context_mismatch",
        ),
        (
            "height_nm",
            700,
            "periodic_response_batch_context_mismatch",
        ),
        (
            "geometry",
            EllipticalCrossSection(80, 140),
            "periodic_polarization_context_mismatch",
        ),
        (
            "capacity_scope",
            "solver:other",
            "periodic_response_batch_context_mismatch",
        ),
        (
            "observation_schema",
            "fixture.periodic.other",
            "periodic_response_batch_context_mismatch",
        ),
    ],
)
def test_sealed_polarization_rejects_mixed_pair_context(
    tmp_path: Path,
    field: str,
    value: object,
    finding: str,
) -> None:
    _authority, _session, binding, atom, substrate, _execution = _recorded_setup(
        tmp_path
    )
    base = replace(
        _work(binding, atom, substrate),
        geometry=RectangularCrossSection(80, 140),
        output_basis="cartesian",
    )
    x_work = replace(
        base,
        work_identity="sha256:context-x",
        input_basis="x linear",
    )
    y_work = replace(
        base,
        work_identity="sha256:context-y",
        input_basis="y linear",
        **{field: value},
    )

    with pytest.raises(
        ValueError,
        match=finding,
    ):
        PeriodicPolarizationRequest(
            periodic_request_identity(
                "polarization",
                (x_work.work_identity, y_work.work_identity),
            ),
            (x_work, y_work),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "leakage_nan",
        "construction_not_bool",
        "execution_empty",
        "execution_project_not_string",
        "warnings_not_collection",
        "phase_extra",
        "phase_planes_not_string",
        "power_not_conserved",
        "phase_not_canonical",
        "complex_not_canonical",
    ],
)
def test_transmission_decoder_rejects_nested_protocol_drift(
    mutation: str,
) -> None:
    values = deepcopy(_transmission_values())
    if mutation == "leakage_nan":
        cast(dict[str, object], values["power"])["leakage"] = "NaN"
    elif mutation == "construction_not_bool":
        values["construction_valid"] = "yes"
    elif mutation == "execution_empty":
        values["execution"] = {}
    elif mutation == "execution_project_not_string":
        cast(dict[str, object], values["execution"])["project"] = 1
    elif mutation == "warnings_not_collection":
        values["warnings"] = "warning"
    elif mutation == "phase_extra":
        cast(dict[str, object], values["phase"])["unit"] = "rad"
    elif mutation == "power_not_conserved":
        cast(dict[str, object], values["power"])["leakage"] = "0.1"
    elif mutation == "phase_not_canonical":
        cast(dict[str, object], values["phase"])["value"] = "07"
    elif mutation == "complex_not_canonical":
        cast(
            dict[str, object],
            values["transmission"],
        )["real_part"] = "00.7"
    else:
        values["phase_planes"] = 1

    with pytest.raises(
        ValueError,
        match="periodic_transmission_observation_invalid",
    ):
        decode_periodic_transmission(values)


@pytest.mark.parametrize("mutation", ["shape", "non_finite"])
def test_reference_surface_decoder_rejects_invalid_component_grid(
    mutation: str,
) -> None:
    values = deepcopy(_surface_values())
    components = cast(
        dict[str, object],
        values["electric_components"],
    )
    x_component = cast(dict[str, object], components["x"])
    if mutation == "shape":
        x_component["real"] = ((0, 0, 0, 0),)
    else:
        x_component["real"] = (
            (0, 0, 0, 0),
            (0, 0, 0, "NaN"),
            (0, 0, 0, 0),
        )

    with pytest.raises(
        ValueError,
        match="periodic_reference_surface_observation_invalid",
    ):
        decode_periodic_reference_surface(values)


def test_request_identity_binds_variant_order_and_exact_work(
    tmp_path: Path,
) -> None:
    _authority, _session, binding, atom, substrate, _execution = _recorded_setup(
        tmp_path
    )
    first = _work(binding, atom, substrate)
    second = replace(first, work_identity="sha256:second-work")
    identity = periodic_request_identity(
        "transmission",
        (first.work_identity, second.work_identity),
    )

    PeriodicTransmissionRequest(identity, (first, second))
    with pytest.raises(
        ValueError,
        match="periodic_response_request_identity_mismatch",
    ):
        PeriodicTransmissionRequest(identity, (second, first))
    with pytest.raises(
        ValueError,
        match="periodic_response_request_identity_mismatch",
    ):
        PeriodicTransmissionRequest(
            identity,
            (first, replace(second, work_identity="sha256:drifted-work")),
        )
    assert identity != periodic_request_identity(
        "polarization",
        (first.work_identity, second.work_identity),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("period_nm", 700),
        ("height_nm", 700),
        ("order_regime", "multi order"),
    ],
)
def test_sealed_batch_rejects_mixed_shared_execution_context(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    _authority, _session, binding, atom, substrate, _execution = _recorded_setup(
        tmp_path
    )
    first = _work(binding, atom, substrate)
    second = replace(
        first,
        work_identity="sha256:mixed-context",
        **{field: value},
    )

    with pytest.raises(
        ValueError,
        match="periodic_response_batch_context_mismatch",
    ):
        PeriodicTransmissionRequest(
            periodic_request_identity(
                "transmission",
                (first.work_identity, second.work_identity),
            ),
            (first, second),
        )


def test_recorded_transmission_restores_exact_body_and_receipt_references(
    tmp_path: Path,
) -> None:
    authority, session, binding, atom, substrate, execution = _recorded_setup(tmp_path)
    work = _work(binding, atom, substrate)
    values = _transmission_values()
    body_reference, receipt_reference = _admit_periodic_fixture(
        session,
        execution,
        work,
        values,
    )
    before = authority.view()

    outcome = _recorded_response(session, binding).observe(
        PeriodicTransmissionRequest(
            periodic_request_identity(
                "transmission",
                (work.work_identity,),
            ),
            (work,),
        )
    )

    assert isinstance(outcome, ObservedPeriodicTransmission)
    assert len(outcome.items) == 1
    restored = outcome.items[0]
    assert isinstance(restored, AdmittedPeriodicTransmission)
    assert restored.observation.transmission.real_part == Decimal("0.7")
    assert restored.observation.useful_power == Decimal("0.8")
    assert restored.body_reference == body_reference
    assert restored.receipt_reference == receipt_reference
    assert (
        authority.fetch(restored.body_reference)
        == Document(
            work.observation_schema,
            values,
        ).to_bytes()
    )
    assert authority.view() == before


@pytest.mark.parametrize("has_extra_candidate_field", [False, True])
def test_recorded_ellipse_uses_the_exact_shared_candidate_codec(
    tmp_path: Path,
    has_extra_candidate_field: bool,
) -> None:
    _authority, session, binding, atom, substrate, execution = _recorded_setup(tmp_path)
    base = replace(
        _work(binding, atom, substrate),
        cell_identity=("elliptical-pillar-height-0600nm-major-0140nm-minor-0080nm"),
        geometry=EllipticalCrossSection(80, 140),
        observation_schema="fixture.periodic.polarization",
        output_basis="cartesian",
    )
    x_work = replace(
        base,
        work_identity="sha256:ellipse-x",
        input_basis="x linear",
    )
    y_work = replace(
        base,
        work_identity="sha256:ellipse-y",
        input_basis="y linear",
    )
    for work, basis in ((x_work, "x"), (y_work, "y")):
        values = _polarization_values(
            work,
            basis=basis,
            has_extra_candidate_field=(has_extra_candidate_field and basis == "x"),
        )
        if has_extra_candidate_field and basis == "x":
            with pytest.raises(
                ValueError,
                match="periodic_polarization_observation_invalid",
            ):
                decode_periodic_polarization(values)
            return
        observation = decode_periodic_polarization(values)
        outcome = execution.execute(
            (
                WorkRequest(
                    work.work_identity,
                    lambda _attempt, value=observation: value,
                    lambda value: Document(
                        work.observation_schema,
                        value.as_mapping(),
                    ),
                    lambda document: decode_periodic_polarization(document.values),
                ),
            )
        )
        assert isinstance(outcome, CompletedWorkExecution)
    request = PeriodicPolarizationRequest(
        periodic_request_identity(
            "polarization",
            (x_work.work_identity, y_work.work_identity),
        ),
        (x_work, y_work),
    )

    restored = _recorded_response(session, binding).observe(request)
    assert isinstance(restored, ObservedPeriodicPolarization)
    assert tuple(item.observation.cell for item in restored.items) == (
        PeriodicCellObservation(
            x_work.cell_identity,
            x_work.height_nm,
            x_work.geometry,
        ),
        PeriodicCellObservation(
            y_work.cell_identity,
            y_work.height_nm,
            y_work.geometry,
        ),
    )


def test_recorded_response_returns_typed_unavailability_for_no_exact_receipt(
    tmp_path: Path,
) -> None:
    _authority, session, binding, atom, substrate, _execution = _recorded_setup(
        tmp_path
    )
    work = _work(binding, atom, substrate)

    outcome = _recorded_response(session, binding).observe(
        PeriodicTransmissionRequest(
            periodic_request_identity(
                "transmission",
                (work.work_identity,),
            ),
            (work,),
        )
    )

    assert outcome == PeriodicResponseUnavailable(
        periodic_request_identity(
            "transmission",
            (work.work_identity,),
        ),
        PeriodicResponseUnavailableReason.RECORDED_RESPONSE_MISSING,
        PeriodicResponseClosure(
            periodic_request_identity(
                "transmission",
                (work.work_identity,),
            ),
            ExternalActivityClosure.recorded(),
            ExternalActivityClosure.recorded(),
        ),
    )


def test_recorded_response_rejects_schema_and_variant_drift(
    tmp_path: Path,
) -> None:
    _authority, session, binding, atom, substrate, execution = _recorded_setup(tmp_path)
    admitted_work = _work(binding, atom, substrate)
    observation = decode_periodic_transmission(_transmission_values())
    completed = execution.execute(
        (
            WorkRequest(
                admitted_work.work_identity,
                lambda _attempt: observation,
                lambda value: Document(
                    admitted_work.observation_schema,
                    value.as_mapping(),
                ),
                lambda document: decode_periodic_transmission(document.values),
            ),
        )
    )
    assert isinstance(completed, CompletedWorkExecution)
    schema_drift = replace(
        admitted_work,
        observation_schema="fixture.periodic.other",
    )
    with pytest.raises(
        RuntimeError,
        match="periodic_response_receipt_schema_mismatch",
    ):
        _recorded_response(session, binding).observe(
            PeriodicTransmissionRequest(
                periodic_request_identity(
                    "transmission",
                    (schema_drift.work_identity,),
                ),
                (schema_drift,),
            )
        )


def test_recorded_response_rejects_duplicate_exact_receipts(
    tmp_path: Path,
) -> None:
    _authority, session, binding, atom, substrate, execution = _recorded_setup(tmp_path)
    work = _work(binding, atom, substrate)
    observation = decode_periodic_transmission(_transmission_values())
    outcome = execution.execute(
        (
            WorkRequest(
                work.work_identity,
                lambda _attempt: observation,
                lambda value: Document(
                    work.observation_schema,
                    value.as_mapping(),
                ),
                lambda document: decode_periodic_transmission(document.values),
            ),
        )
    )
    assert isinstance(outcome, CompletedWorkExecution)
    original_view = session.observe()
    permit = original_view.permits[0]

    class _DuplicateReceiptSession:
        def observe(self):
            return replace(
                original_view,
                permits=(permit, replace(permit)),
            )

        def fetch(self, reference: Reference) -> bytes:
            return session.fetch(reference)

    recorded = RecordedPeriodicResponse(
        cast(AuthoritySession, _DuplicateReceiptSession()),
        context=PeriodicResponseContext(
            binding_reference=binding,
            capacity_scope="solver:fixture",
            response_kinds=tuple(PeriodicResponseKind),
            qualification_closure=ExternalActivityClosure.recorded(),
        ),
    )
    with pytest.raises(
        RuntimeError,
        match="periodic_response_record_duplicate",
    ):
        recorded.observe(
            PeriodicTransmissionRequest(
                periodic_request_identity(
                    "transmission",
                    (work.work_identity,),
                ),
                (work,),
            )
        )


def test_lumerical_observe_recovers_exact_work_and_reuses_same_solve_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native: dict[str, object] = {}
    response, work, sessions, authority = _physical_response(
        tmp_path,
        monkeypatch,
        result=native,
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    native["_responses"] = {
        "propagation": _transmission_result(),
        "reference_surface": _surface_result(work),
    }
    qualification = ExternalActivityClosure(
        ExternalActivityOrigin.NATIVE,
        0,
        0,
        3,
        3,
        2,
        2,
        1,
        1,
    )
    response._qualification_closure = qualification
    request = PeriodicTransmissionRequest(
        periodic_request_identity(
            "transmission",
            (work.work_identity,),
        ),
        (work,),
    )

    first = response.observe(request)
    assert isinstance(first, ObservedPeriodicTransmission)
    assert len(sessions.sessions) == 1
    assert sessions.sessions[0].closed
    permits_after_solve = authority.view().permits

    restored = response.observe(request)
    assert isinstance(restored, ObservedPeriodicTransmission)
    assert restored.items == first.items
    assert len(sessions.sessions) == 1

    formation_session = AuthoritySession(authority)
    surfaces = admit_reference_surfaces(
        request,
        first,
        admit_object=formation_session.admit_object,
        admit_document=formation_session.admit_document,
    )
    assert len(surfaces) == 1
    assert surfaces[0].response.field.surface.shape == (24, 24)
    assert surfaces[0].response.field.basis is ComponentBasis.CARTESIAN
    assert surfaces[0].response.field.source_references[0] == (
        first.items[0].body_reference
    )
    assert surfaces[0].response.field.source_references[1] not in {
        first.items[0].body_reference,
        response.binding_reference,
    }
    assert authority.view().permits == permits_after_solve
    assert len(sessions.sessions) == 1


def test_lumerical_polarization_succeeds_and_replays_two_exact_basis_lives(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PolarizationNativeResponses:
        def __init__(self) -> None:
            self._calls_by_basis: dict[tuple[int, int], int] = {}
            self.work_by_angle: dict[int, PeriodicWork] = {}

        def __call__(
            self,
            objects: dict[str, dict[str, object]],
        ) -> dict[str, object]:
            angle = int(objects["grating_response"]["polarization_angle_degrees"])
            response_identity = (id(objects), angle)
            call = self._calls_by_basis.get(response_identity, 0)
            self._calls_by_basis[response_identity] = call + 1
            if call == 0:
                return {
                    "output_x": (complex(1, 0) if angle == 0 else complex(0, 0)),
                    "output_y": (complex(0, 0) if angle == 0 else complex(-1, 0)),
                    "phase_planes": "grating_s_params",
                    "solver_status": "complete",
                    "warnings": [],
                }
            return _surface_result(self.work_by_angle[angle])

    native = PolarizationNativeResponses()
    response, base, sessions, authority = _physical_response(
        tmp_path,
        monkeypatch,
        result=native,
        response_qualifications=(
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(PERIODIC_POLARIZATION_RESPONSE),
            PeriodicResponseQualification.qualified(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    cell_identity = "rectangular-fin-height-0600nm-length-0140nm-width-0080nm"
    x_work = replace(
        base,
        cell_identity=cell_identity,
        work_identity="sha256:polarization-success-x",
        geometry=RectangularCrossSection(80, 140),
        input_basis="x linear",
        output_basis="cartesian",
    )
    y_work = replace(
        x_work,
        work_identity="sha256:polarization-success-y",
        input_basis="y linear",
    )
    native.work_by_angle = {0: x_work, 90: y_work}
    request = PeriodicPolarizationRequest(
        periodic_request_identity(
            "polarization",
            (x_work.work_identity, y_work.work_identity),
        ),
        (x_work, y_work),
    )

    first = response.observe(request)

    assert isinstance(first, ObservedPeriodicPolarization)
    assert tuple(item.observation.input_basis for item in first.items) == ("x", "y")
    assert len({item.receipt_reference for item in first.items}) == 2
    assert all(item.observation.reference_surface is not None for item in first.items)
    permits_after_solve = authority.view().permits
    assert len(permits_after_solve) == 2
    assert sessions.sessions
    assert all(session.closed for session in sessions.sessions)
    native_session_count = len(sessions.sessions)

    replayed = response.observe(request)

    assert isinstance(replayed, ObservedPeriodicPolarization)
    assert replayed.items == first.items
    assert first.closure.observation.acquired_authority_work_count == 2
    assert first.closure.observation.started_external_execution_count == 2
    assert first.closure.observation.opened_product_session_count == 1
    assert replayed.closure.observation.acquired_authority_work_count == 0
    assert replayed.closure.observation.started_external_execution_count == 0
    assert replayed.closure.observation.opened_product_session_count == 0
    assert authority.view().permits == permits_after_solve
    assert len(sessions.sessions) == native_session_count

    formation_session = AuthoritySession(authority)
    surfaces = admit_reference_surfaces(
        request,
        first,
        cell_identity=cell_identity,
        admit_object=formation_session.admit_object,
        admit_document=formation_session.admit_document,
    )
    assert tuple(surface.response.requested_input_basis for surface in surfaces) == (
        "x linear",
        "y linear",
    )
    assert tuple(
        surface.response.field.source_references[0] for surface in surfaces
    ) == tuple(item.body_reference for item in first.items)
    assert len({surface.response.field.surface for surface in surfaces}) == 1
    assert tuple(surface.response.field.surface.shape for surface in surfaces) == (
        (24, 24),
        (24, 24),
    )
    assert tuple(item.body_reference for item in first.items) == tuple(
        surface.response.field.source_references[0] for surface in surfaces
    )
    assert authority.view().permits == permits_after_solve
    assert len(sessions.sessions) == native_session_count


@pytest.mark.parametrize("response_kind", ("transmission", "polarization"))
def test_lumerical_result_failure_retains_only_completed_project_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    response_kind: str,
) -> None:
    """
    A completed solve remains durable when subsequent observation fails.
    """

    qualifications = (
        PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
        PeriodicResponseQualification.qualified(PERIODIC_POLARIZATION_RESPONSE),
        PeriodicResponseQualification.response_not_returned(
            PERIODIC_REFERENCE_SURFACE_RESPONSE
        ),
    )
    response, base, _sessions, authority = _physical_response(
        tmp_path,
        monkeypatch,
        result={"_responses": {}},
        response_qualifications=qualifications,
    )
    if response_kind == "transmission":
        works = (base,)
        request = PeriodicTransmissionRequest(
            periodic_request_identity("transmission", (base.work_identity,)),
            works,
        )
        directories = (tmp_path / "live-run" / base.cell_identity,)
    else:
        cell_identity = "rectangular-fin-height-0600nm-length-0140nm-width-0080nm"
        x_work = replace(
            base,
            cell_identity=cell_identity,
            work_identity="sha256:result-failure-x",
            geometry=RectangularCrossSection(80, 140),
            input_basis="x linear",
            output_basis="cartesian",
        )
        y_work = replace(
            x_work,
            work_identity="sha256:result-failure-y",
            input_basis="y linear",
        )
        works = (x_work, y_work)
        request = PeriodicPolarizationRequest(
            periodic_request_identity(
                "polarization",
                tuple(work.work_identity for work in works),
            ),
            works,
        )
        candidate = tmp_path / "live-run" / cell_identity
        directories = (candidate / "from-x", candidate / "from-y")

    if response_kind == "transmission":
        with pytest.raises(KeyError, match="result_missing"):
            response.observe(request)
    else:
        with pytest.raises(ExceptionGroup, match="work_failed") as raised:
            response.observe(request)
        assert all(
            isinstance(error, KeyError) and "result_missing" in str(error)
            for error in raised.value.exceptions
        )

    for directory in directories:
        assert (directory / "after.fsp").is_file()
        assert (directory / "execution.json").is_file()
        assert not (directory / "observation.json").exists()
        assert not (directory / "work.json").exists()
    permits = authority.view().permits
    assert len(permits) == len(works)
    assert all(permit.receipt_reference is None for permit in permits)


def test_lumerical_solve_failure_does_not_record_project_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Do not invent execution evidence when the solve returns no execution.
    """

    response, work, _sessions, authority = _physical_response(
        tmp_path,
        monkeypatch,
        result={"_responses": {"propagation": _transmission_result()}},
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )

    def fail_solve(self, before: Path, after: Path):
        del self, before, after
        raise RuntimeError("solve did not return")

    monkeypatch.setattr(FakeSession, "solve", fail_solve)
    request = PeriodicTransmissionRequest(
        periodic_request_identity("transmission", (work.work_identity,)),
        (work,),
    )

    with pytest.raises(RuntimeError, match="solve did not return"):
        response.observe(request)

    directory = tmp_path / "live-run" / work.cell_identity
    assert not (directory / "execution.json").exists()
    assert not (directory / "observation.json").exists()
    assert not (directory / "work.json").exists()
    assert authority.view().permits[0].receipt_reference is None


def test_lumerical_observe_returns_typed_independent_capability_absence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response, base, sessions, _authority = _physical_response(
        tmp_path,
        monkeypatch,
        result={},
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    cell_identity = "rectangular-fin-height-0600nm-length-0140nm-width-0080nm"
    x_work = replace(
        base,
        cell_identity=cell_identity,
        work_identity="sha256:polarization-x",
        geometry=RectangularCrossSection(80, 140),
        input_basis="x linear",
        output_basis="cartesian",
    )
    y_work = replace(
        x_work,
        work_identity="sha256:polarization-y",
        input_basis="y linear",
    )
    request = PeriodicPolarizationRequest(
        periodic_request_identity(
            "polarization",
            (x_work.work_identity, y_work.work_identity),
        ),
        (x_work, y_work),
    )

    outcome = response.observe(request)

    assert outcome == PeriodicResponseUnavailable(
        request.request_identity,
        PeriodicResponseUnavailableReason.POLARIZATION_RESPONSE_UNQUALIFIED,
        PeriodicResponseClosure(
            request.request_identity,
            ExternalActivityClosure.recorded(),
            ExternalActivityClosure.none(),
        ),
    )
    assert sessions.sessions == []


@pytest.mark.parametrize(
    ("product_reason", "expected"),
    [
        (
            "configuration_incomplete",
            PeriodicResponseUnavailableReason.CONFIGURATION_INCOMPLETE,
        ),
        (
            "license_unavailable",
            PeriodicResponseUnavailableReason.LICENSE_UNAVAILABLE,
        ),
        (
            "license_utility_not_found",
            PeriodicResponseUnavailableReason.LICENSE_UNAVAILABLE,
        ),
        (
            "capacity_not_positive",
            PeriodicResponseUnavailableReason.CAPACITY_NOT_POSITIVE,
        ),
        (
            "capacity_stale",
            PeriodicResponseUnavailableReason.CAPACITY_STALE,
        ),
        (
            "native_session_unavailable",
            PeriodicResponseUnavailableReason.NATIVE_UNAVAILABLE,
        ),
    ],
)
def test_lumerical_observe_maps_product_absence_to_closed_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    product_reason: str,
    expected: PeriodicResponseUnavailableReason,
) -> None:
    response, work, _sessions, _authority = _physical_response(
        tmp_path,
        monkeypatch,
        result={},
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )

    def unavailable(
        _response: LumericalPeriodicResponse,
        _request_identity: str,
    ) -> None:
        raise LumericalUnavailable(product_reason)

    monkeypatch.setattr(
        LumericalPeriodicResponse,
        "_open_batch",
        unavailable,
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity(
            "transmission",
            (work.work_identity,),
        ),
        (work,),
    )

    outcome = response.observe(request)

    assert outcome == PeriodicResponseUnavailable(
        request.request_identity,
        expected,
        PeriodicResponseClosure(
            request.request_identity,
            ExternalActivityClosure.recorded(),
            ExternalActivityClosure.none(),
        ),
    )


def test_lumerical_native_absence_reports_every_settled_resource(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(
        _objects: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        raise LumericalUnavailable("native_session_unavailable")

    response, work, sessions, _authority = _physical_response(
        tmp_path,
        monkeypatch,
        result=unavailable,
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity(
            "transmission",
            (work.work_identity,),
        ),
        (work,),
    )

    outcome = response.observe(request)

    assert isinstance(outcome, PeriodicResponseUnavailable)
    assert outcome.reason is PeriodicResponseUnavailableReason.NATIVE_UNAVAILABLE
    assert outcome.closure.observation == ExternalActivityClosure(
        origin=ExternalActivityOrigin.NATIVE,
        acquired_authority_work_count=1,
        settled_authority_work_count=1,
        started_external_execution_count=1,
        settled_external_execution_count=1,
        opened_product_session_count=1,
        closed_product_session_count=1,
        opened_local_placement_count=1,
        closed_local_placement_count=1,
    )
    assert sessions.sessions[0].closed


def test_lumerical_stale_retry_reports_every_authority_work_life(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response, work, sessions, _authority = _physical_response(
        tmp_path,
        monkeypatch,
        result=_transmission_result(),
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
        should_stale_once=True,
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity(
            "transmission",
            (work.work_identity,),
        ),
        (work,),
    )

    outcome = response.observe(request)

    assert isinstance(outcome, ObservedPeriodicTransmission)
    assert outcome.closure.observation == ExternalActivityClosure(
        origin=ExternalActivityOrigin.NATIVE,
        acquired_authority_work_count=2,
        settled_authority_work_count=2,
        started_external_execution_count=1,
        settled_external_execution_count=1,
        opened_product_session_count=1,
        closed_product_session_count=1,
        opened_local_placement_count=1,
        closed_local_placement_count=1,
    )
    assert sessions.sessions[0].closed


@pytest.mark.parametrize(
    ("waiting_reason", "expected"),
    [
        (
            "capacity_not_positive",
            PeriodicResponseUnavailableReason.CAPACITY_NOT_POSITIVE,
        ),
        (
            "capacity_stale",
            PeriodicResponseUnavailableReason.CAPACITY_STALE,
        ),
    ],
)
def test_lumerical_observe_maps_renewal_waiting_without_text_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    waiting_reason: str,
    expected: PeriodicResponseUnavailableReason,
) -> None:
    response, work, _sessions, _authority = _physical_response(
        tmp_path,
        monkeypatch,
        result={},
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )

    class WaitingBatch:
        def observe_transmission(
            self,
            _request: PeriodicTransmissionRequest,
        ) -> WorkWaiting[PeriodicTransmissionObservation]:
            return WorkWaiting(
                waiting_reason,
                (work.work_identity,),
            )

    monkeypatch.setattr(
        LumericalPeriodicResponse,
        "_open_batch",
        lambda _response, _request_identity: WaitingBatch(),
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity(
            "transmission",
            (work.work_identity,),
        ),
        (work,),
    )

    outcome = response.observe(request)

    assert outcome == PeriodicResponseUnavailable(
        request.request_identity,
        expected,
        PeriodicResponseClosure(
            request.request_identity,
            ExternalActivityClosure.recorded(),
            ExternalActivityClosure.none(),
        ),
    )


def test_lumerical_malformed_native_payload_is_a_direct_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response, work, sessions, _authority = _physical_response(
        tmp_path,
        monkeypatch,
        result={
            "solver_status": "complete",
            "warnings": [],
        },
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    request = PeriodicTransmissionRequest(
        periodic_request_identity(
            "transmission",
            (work.work_identity,),
        ),
        (work,),
    )

    with pytest.raises(KeyError, match="complex_transmission"):
        response.observe(request)

    assert len(sessions.sessions) == 1
    assert sessions.sessions[0].closed


def test_lumerical_cleanup_group_of_absences_remains_a_direct_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = LumericalUnavailable("native_session_unavailable")
    cleanup = LumericalUnavailable("native_session_close_unavailable")

    def unavailable(
        _objects: dict[str, dict[str, object]],
    ) -> dict[str, object]:
        raise primary

    response, work, sessions, _authority = _physical_response(
        tmp_path,
        monkeypatch,
        result=unavailable,
        response_qualifications=(
            PeriodicResponseQualification.qualified(PERIODIC_TRANSMISSION_RESPONSE),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )
    original_close = FakeSession.close

    def close_with_absence(session: FakeSession) -> None:
        original_close(session)
        raise cleanup

    monkeypatch.setattr(FakeSession, "close", close_with_absence)
    request = PeriodicTransmissionRequest(
        periodic_request_identity(
            "transmission",
            (work.work_identity,),
        ),
        (work,),
    )

    with pytest.raises(ExceptionGroup) as raised:
        response.observe(request)

    assert raised.value.exceptions == (primary, cleanup)
    assert sessions.sessions[0].closed

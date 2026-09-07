from __future__ import annotations

import cmath
from dataclasses import replace
from decimal import Decimal
import json
import math
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import numpy

from metacraft.authority import Document, Reference
from metacraft.authority.reference import reference_for
from metacraft.external_activity import ExternalActivityClosure
from metacraft.science.metalens.achromatic import (
    AchromaticAperture,
    AchromaticFocus,
    AchromaticFocusEntry,
    AchromaticTarget,
    ResponseQualificationProfile,
    SpectralCellStudyPlan,
    SpectralCellScreen,
    SpectralEvidenceRequirement,
    SpectralFieldEntry,
    SpectralFieldFamily,
    SpectralJonesLibrary,
    SpectralJonesObservation,
    SpectralLibraryQualification,
    SpectralMaterialBinding,
    SpectralMaterialPoint,
    SpectralQualificationStatus,
    SpectralRectangle,
    SpectralStudySpecification,
    assign_continuous_achromatic_aperture,
    form_achromatic_aperture_field,
    form_achromatic_focus,
    form_spectral_cell_study_plan,
    form_spectral_cell_screen,
    form_spectral_jones_library,
    form_spectral_observations,
    form_spectral_study_specification,
    project_spectral_periodic_requests,
    project_spectral_reference_request,
    qualify_spectral_jones_library,
    require_spectral_material_binding,
)
from metacraft.science.metalens.aperture import Lattice, resolve_lattice
from metacraft.science.metalens.design import resolve_metalens_design
from metacraft.science.metalens.geometric_phase import (
    ComplexCoefficient,
    JonesResponse,
    PolarizationConvention,
    project_circular_channels,
)
from metacraft.science.metalens.focus import (
    Focus,
    FocusConvergence,
    HalfMaximum,
    Leakage,
)
from metacraft.science.study import Task
from metacraft.science.periodic_response import (
    AdmittedPeriodicObservationIncomplete,
    ObservedPeriodicPolarization,
    PeriodicPolarizationRequest,
    PeriodicPolarizationIncomplete,
    PeriodicObservationIncomplete,
    PeriodicObservationIncompleteReason,
    PeriodicResponseClosure,
    RectangularCrossSection,
    decode_periodic_polarization,
    form_admitted_periodic_polarization,
)
from tests.brief_fixtures import (
    continuous_achromatic_brief,
    continuous_achromatic_publication_brief,
)


def _target(*, numerical_aperture: Decimal = Decimal("0.2")) -> AchromaticTarget:
    brief = replace(
        continuous_achromatic_brief(),
        numerical_aperture=numerical_aperture,
    )
    return AchromaticTarget.from_design(resolve_metalens_design(brief))


def _point(wavelength_nm: int) -> SpectralMaterialPoint:
    return SpectralMaterialPoint(
        wavelength_nm=wavelength_nm,
        atom_refractive_index=Decimal("2.45"),
        atom_extinction_coefficient=Decimal("0.0000002"),
        substrate_refractive_index=Decimal("1.46"),
        substrate_extinction_coefficient=Decimal(0),
    )


def _binding(wavelengths_nm: tuple[int, ...]) -> SpectralMaterialBinding:
    return SpectralMaterialBinding(
        atom_family="amorphous titanium dioxide",
        atom_native_name="TiO2 (Titanium Dioxide) - Siefke",
        substrate_family="glass",
        substrate_native_name="SiO2 (Glass) - Palik",
        points=tuple(_point(wavelength) for wavelength in wavelengths_nm),
        solver_binding_reference=reference_for(b"spectral material solver"),
        source_references=tuple(
            reference_for(f"spectral material sample {wavelength}".encode("ascii"))
            for wavelength in wavelengths_nm
        ),
    )


def _profile() -> ResponseQualificationProfile:
    return ResponseQualificationProfile(
        version="reviewed-test-profile-v1",
        provenance=("reviewed test Method contract",),
        source_references=(reference_for(b"reviewed qualification source"),),
        minimum_reference_converted_power=Decimal("0.05"),
        minimum_full_band_converted_power=Decimal("0.05"),
        maximum_full_band_leakage_power=Decimal("0.20"),
        minimum_design_r_squared=Decimal("0.99"),
        maximum_interleaved_phase_residual_rad=Decimal("0.15"),
        maximum_reference_phase_gap_rad=Decimal("1.5707963267948966"),
        maximum_dense_phase_residual_rad=Decimal("0.20"),
        maximum_phase_curvature_rad=Decimal("0.10"),
    )


def _specification() -> SpectralStudySpecification:
    profile = _profile()
    return form_spectral_study_specification(
        _target(),
        qualification_profile_reference=reference_for(profile.document().to_bytes()),
    )


def _plan() -> SpectralCellStudyPlan:
    target = _target()
    specification = _specification()
    binding = _binding(specification.full_band_wavelengths_nm)
    result = form_spectral_cell_study_plan(
        target,
        binding,
        material_binding_reference=reference_for(binding.document().to_bytes()),
        dimension_step_nm=10,
        aspect_limit=8,
        specification=specification,
        specification_reference=reference_for(specification.document().to_bytes()),
    )
    assert isinstance(result, SpectralCellStudyPlan)
    return result


def _coefficient(value: complex) -> ComplexCoefficient:
    return ComplexCoefficient(
        real_part=Decimal(str(value.real)),
        imaginary_part=Decimal(str(value.imag)),
    )


def _reference_surface_values(
    wavelength_nm: int,
    basis: str,
    *,
    transmitted_power: Decimal,
) -> dict[str, object]:
    coordinates = ["-0.00000016", "0", "0.00000016"]
    zero_patch = [["0", "0", "0"] for _ in range(3)]
    return {
        "electric_components": {
            component: {"imaginary": zero_patch, "real": zero_patch}
            for component in ("x", "y", "z")
        },
        "frame": {
            "normal_axis": "z",
            "propagation_direction": "positive",
            "sample_order": ["y", "x"],
        },
        "incident_reference_power": "1",
        "medium": "air",
        "order_regime": "zeroth order",
        "output_basis": "cartesian",
        "requested_input_basis": f"{basis} linear",
        "surface": {
            "position_m": "0.0000008",
            "x_coordinates_m": coordinates,
            "y_coordinates_m": coordinates,
        },
        "transmitted_power": format(transmitted_power, "f"),
        "wavelength_m": format(Decimal(wavelength_nm) / Decimal(1_000_000_000), "f"),
    }


def _observed_batch_with_power_normalization(
    request: PeriodicPolarizationRequest,
    *,
    transmitted_power_per_squared_amplitude: Decimal,
    weakened_geometry: SpectralRectangle | None = None,
) -> ObservedPeriodicPolarization:
    admitted = []
    for work in request.items:
        basis = work.input_basis.removesuffix(" linear")
        amplitude = (
            Decimal("0.08")
            if weakened_geometry is not None
            and isinstance(work.geometry, RectangularCrossSection)
            and work.geometry.short_side_nm == weakened_geometry.short_side_nm
            and work.geometry.long_side_nm == weakened_geometry.long_side_nm
            else Decimal("0.8")
        )
        transmitted_power = transmitted_power_per_squared_amplitude * amplitude**2
        values = {
            "basis": basis,
            "candidate": work.candidate_mapping(),
            "execution": {
                "native": False,
                "placement": {},
                "project": "recorded spectral power fixture",
                "return_code": 0,
                "source": "test",
            },
            "output_x": {
                "imaginary_part": "0",
                "real_part": format(amplitude, "f") if basis == "x" else "0",
            },
            "output_y": {
                "imaginary_part": "0",
                "real_part": "0" if basis == "x" else format(-amplitude, "f"),
            },
            "phase_planes": "same input and output reference planes",
            "reference_surface": _reference_surface_values(
                work.wavelength_nm,
                basis,
                transmitted_power=transmitted_power,
            ),
            "solver_status": "complete",
            "warnings": [],
        }
        decoded = decode_periodic_polarization(values)
        body_reference = reference_for(
            Document(work.observation_schema, values).to_bytes()
        )
        admitted.append(
            form_admitted_periodic_polarization(
                work.work_identity,
                decoded,
                body_reference,
                reference_for(f"receipt {work.work_identity}".encode("ascii")),
            )
        )
    return ObservedPeriodicPolarization(
        request_identity=request.request_identity,
        items=tuple(admitted),
        closure=PeriodicResponseClosure(
            request.request_identity,
            ExternalActivityClosure.none(),
            ExternalActivityClosure.none(),
        ),
    )


def _screen(
    plan: SpectralCellStudyPlan,
    binding: SpectralMaterialBinding,
    periodic_binding_reference: Reference,
    *,
    weakened_geometry: SpectralRectangle | None = None,
) -> tuple[PeriodicPolarizationRequest, SpectralCellScreen]:
    plan_reference = reference_for(plan.document().to_bytes())
    task = Task(
        proof_identity="sha256:" + "4" * 64,
        claim="spectral_cell_screen",
        method="screen_spectral_cells",
        schema="metacraft.science.metalens.spectral_cell_screen",
        brief_identity="sha256:" + "5" * 64,
        design_identity="sha256:" + "6" * 64,
        prerequisite_evidence=(plan_reference,),
        consultations=(),
        binding_reference=periodic_binding_reference,
        capacity_scope="fixture:spectral-periodic",
    )
    request = project_spectral_reference_request(plan, binding, task=task)
    return request, form_spectral_cell_screen(
        plan,
        request,
        _observed_batch_with_power_normalization(
            request,
            transmitted_power_per_squared_amplitude=Decimal(1),
            weakened_geometry=weakened_geometry,
        ),
        convention=PolarizationConvention(circular_input="left"),
        profile=_profile(),
        profile_reference=plan.qualification_profile_reference,
        solver_binding_reference=periodic_binding_reference,
    )


def _reference_screen_observation_fixture() -> tuple[
    SpectralCellStudyPlan,
    Reference,
    PeriodicPolarizationRequest,
    ObservedPeriodicPolarization,
]:
    plan = _plan()
    binding = _binding(plan.full_band_wavelengths_nm)
    solver_binding_reference = reference_for(b"spectral periodic solver")
    request, _screen_result = _screen(
        plan,
        binding,
        solver_binding_reference,
    )
    outcome = _observed_batch_with_power_normalization(
        request,
        transmitted_power_per_squared_amplitude=Decimal(1),
    )
    return plan, solver_binding_reference, request, outcome


def test_spectral_observation_rejects_a_body_for_another_cell() -> None:
    plan, solver_binding_reference, request, outcome = (
        _reference_screen_observation_fixture()
    )
    wrong_cell = replace(
        outcome.items[0].observation.cell,
        cell_identity="rectangular-fin-from-another-work",
    )
    wrong_items = tuple(
        replace(item, observation=replace(item.observation, cell=wrong_cell))
        if index < 2
        else item
        for index, item in enumerate(outcome.items)
    )

    with TestCase().assertRaisesRegex(
        ValueError,
        "^periodic_response_candidate_mismatch$",
    ):
        form_spectral_observations(
            plan.geometries,
            wavelength_nm=plan.reference_wavelength_nm,
            request=request,
            outcome=replace(outcome, items=wrong_items),
            solver_binding_reference=solver_binding_reference,
        )


def test_spectral_observation_rejects_a_body_for_another_wavelength() -> None:
    plan, solver_binding_reference, request, outcome = (
        _reference_screen_observation_fixture()
    )
    surface = outcome.items[0].observation.reference_surface
    assert surface is not None
    wrong_items = tuple(
        replace(
            item,
            observation=replace(
                item.observation,
                reference_surface=replace(
                    item.observation.reference_surface,
                    wavelength_m=Decimal("0.000000531"),
                ),
            ),
        )
        if index < 2
        else item
        for index, item in enumerate(outcome.items)
    )

    with TestCase().assertRaisesRegex(
        ValueError,
        "^periodic_response_wavelength_mismatch$",
    ):
        form_spectral_observations(
            plan.geometries,
            wavelength_nm=plan.reference_wavelength_nm,
            request=request,
            outcome=replace(outcome, items=wrong_items),
            solver_binding_reference=solver_binding_reference,
        )


def _incomplete_outcome(
    request: PeriodicPolarizationRequest,
) -> PeriodicPolarizationIncomplete:
    completed = _observed_batch_with_power_normalization(
        request,
        transmitted_power_per_squared_amplitude=Decimal(1),
    )
    incomplete_work = request.items[-1]
    incomplete = PeriodicObservationIncomplete(
        work_identity=incomplete_work.work_identity,
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
                "termination": {
                    "autoshutoff_threshold": "0.00001",
                    "native_status": 1,
                    "outcome": "maximum_time",
                    "simulated_time_fs": "2000",
                    "terminal_autoshutoff": "0.02",
                },
            },
            {
                "maximum_time_fs": 4000,
                "termination": {
                    "autoshutoff_threshold": "0.00001",
                    "native_status": 1,
                    "outcome": "maximum_time",
                    "simulated_time_fs": "4000",
                    "terminal_autoshutoff": "0.01",
                },
            },
        ),
        response_change={
            "cartesian_change": "0.02",
            "cartesian_tolerance": "0.005",
            "response": "cartesian_polarization",
        },
    )
    body_reference = reference_for(
        Document(
            "metacraft.science.periodic_observation_incomplete",
            incomplete.as_mapping(),
        ).to_bytes()
    )
    return PeriodicPolarizationIncomplete(
        request_identity=request.request_identity,
        items=completed.items[:-1],
        incomplete_items=(
            AdmittedPeriodicObservationIncomplete(
                incomplete_work.work_identity,
                incomplete,
                body_reference,
                reference_for(b"incomplete receipt"),
            ),
        ),
        closure=completed.closure,
    )


def _library(plan: SpectralCellStudyPlan) -> SpectralJonesLibrary:
    delays_fs = tuple(
        3.8 * index / (len(plan.geometries) - 1)
        for index in range(len(plan.geometries))
    )
    observations = []
    for index, (geometry, delay_fs) in enumerate(
        zip(plan.geometries, delays_fs, strict=True)
    ):
        reference_omega = 2 * math.pi * 299.792458 / 530
        intercept = (
            index * 2 * math.pi / len(plan.geometries) - delay_fs * reference_omega
        )
        for wavelength_nm in plan.wavelengths_nm:
            omega = 2 * math.pi * 299.792458 / wavelength_nm
            converted = math.sqrt(0.8) * cmath.exp(1j * (intercept + delay_fs * omega))
            observations.append(
                SpectralJonesObservation(
                    geometry=geometry,
                    wavelength_nm=wavelength_nm,
                    response=JonesResponse(
                        output_x_from_input_x=_coefficient(converted),
                        output_y_from_input_x=_coefficient(0j),
                        output_x_from_input_y=_coefficient(0j),
                        output_y_from_input_y=_coefficient(-converted),
                    ),
                    transmitted_power_per_squared_amplitude=Decimal(1),
                    source_references=(
                        reference_for(f"x {geometry} {wavelength_nm}".encode("ascii")),
                        reference_for(f"y {geometry} {wavelength_nm}".encode("ascii")),
                    ),
                )
            )
    return SpectralJonesLibrary(
        plan_reference=reference_for(plan.document().to_bytes()),
        screen_reference=reference_for(b"spectral cell screen"),
        solver_binding_reference=reference_for(b"spectral periodic solver"),
        selected_geometries=plan.geometries,
        observations=tuple(observations),
        convention=PolarizationConvention(circular_input="left"),
    )


def _qualification(
    target: AchromaticTarget,
    plan: SpectralCellStudyPlan,
    library: SpectralJonesLibrary,
) -> SpectralLibraryQualification:
    return qualify_spectral_jones_library(
        target,
        plan,
        library,
        profile=_profile(),
        profile_reference=plan.qualification_profile_reference,
    )


def test_retained_local_single_point_is_incomplete_not_a_band_binding() -> None:
    binding = _binding((532,))
    requirement = require_spectral_material_binding(
        _target(),
        binding,
        specification=_specification(),
    )

    assert isinstance(requirement, SpectralEvidenceRequirement)
    assert requirement.claim == "spectral_material_binding"
    assert requirement.reason == "spectral_material_samples_incomplete"
    assert requirement.missing_wavelengths_nm == tuple(range(470, 591, 5))
    assert SpectralMaterialBinding.from_document(binding.document()) == binding


def test_plan_adapts_the_paper_seed_to_the_local_square_cell_contract() -> None:
    plan = _plan()

    assert plan.design_wavelengths_nm == (470, 500, 530, 560, 590)
    assert plan.holdout_wavelengths_nm == (485, 515, 545, 575)
    assert plan.period_nm == 320
    assert plan.height_nm == 600
    assert len(plan.geometries) == 136
    assert plan.reference_screen_work_count == 272
    assert plan.maximum_followup_work_count == 2176
    assert plan.maximum_post_freeze_work_count == 4352
    assert plan.maximum_work_count == 6800
    assert all(
        geometry.short_side_nm < geometry.long_side_nm
        and plan.period_nm - geometry.long_side_nm >= 80
        for geometry in plan.geometries
    )
    assert plan.document().values["template"] == (
        "single rectangular fin in square periodic cell"
    )
    assert SpectralCellStudyPlan.from_document(plan.document()) == plan


def test_native_material_grid_keeps_the_adapted_period_below_every_order_limit() -> (
    None
):
    witness_path = (
        Path(__file__).parents[1]
        / "fixtures"
        / "achromatic"
        / "native-material-grid-20260814.json"
    )
    witness = json.loads(witness_path.read_text(encoding="utf-8"))
    values = witness["values"]
    assert values["adapter"] == "ProductProbe.sample_materials"
    assert values["admitted_to_authority"] is False
    points = tuple(
        SpectralMaterialPoint(
            wavelength_nm=item["wavelength_nm"],
            atom_refractive_index=Decimal(item["atom_refractive_index"]),
            atom_extinction_coefficient=Decimal(item["atom_extinction_coefficient"]),
            substrate_refractive_index=Decimal(item["substrate_refractive_index"]),
            substrate_extinction_coefficient=Decimal(
                item["substrate_extinction_coefficient"]
            ),
        )
        for item in values["points"]
    )
    binding = SpectralMaterialBinding(
        atom_family=values["atom"]["family"],
        atom_native_name=values["atom"]["native_name"],
        substrate_family=values["substrate"]["family"],
        substrate_native_name=values["substrate"]["native_name"],
        points=points,
        solver_binding_reference=reference_for(b"native witness binding"),
        source_references=tuple(
            reference_for(
                f"native material point {point.wavelength_nm}".encode("ascii")
            )
            for point in points
        ),
    )
    result = form_spectral_cell_study_plan(
        _target(),
        binding,
        material_binding_reference=reference_for(binding.document().to_bytes()),
        dimension_step_nm=10,
        aspect_limit=8,
        specification=_specification(),
        specification_reference=reference_for(_specification().document().to_bytes()),
    )

    assert isinstance(result, SpectralEvidenceRequirement)
    assert result.claim == "spectral_material_binding"
    assert result.missing_wavelengths_nm == (
        _specification().blind_verification_wavelengths_nm
    )


def test_native_periodic_spot_uses_reference_power_not_raw_amplitude_squared() -> None:
    witness_path = (
        Path(__file__).parents[1]
        / "fixtures"
        / "achromatic"
        / "native-periodic-spot-20260814.json"
    )
    witness = json.loads(witness_path.read_text(encoding="utf-8"))["values"]
    x_input = witness["responses"]["x_input"]
    y_input = witness["responses"]["y_input"]
    response = JonesResponse(
        output_x_from_input_x=_coefficient_from_mapping(x_input["output_x"]),
        output_y_from_input_x=_coefficient_from_mapping(x_input["output_y"]),
        output_x_from_input_y=_coefficient_from_mapping(y_input["output_x"]),
        output_y_from_input_y=_coefficient_from_mapping(y_input["output_y"]),
    )
    x_squared_amplitude = sum(
        abs(value.complex_value()) ** 2
        for value in (
            response.output_x_from_input_x,
            response.output_y_from_input_x,
        )
    )
    y_squared_amplitude = sum(
        abs(value.complex_value()) ** 2
        for value in (
            response.output_x_from_input_y,
            response.output_y_from_input_y,
        )
    )
    factors = (
        float(x_input["transmitted_power"]) / x_squared_amplitude,
        float(y_input["transmitted_power"]) / y_squared_amplitude,
    )
    converted, retained = project_circular_channels(
        response,
        PolarizationConvention(circular_input="left"),
    )
    normalization = sum(factors) / len(factors)

    assert math.isclose(factors[0], factors[1], rel_tol=1e-12)
    assert math.isclose(
        normalization,
        float(witness["derived"]["power_normalization"]),
        rel_tol=1e-14,
    )
    assert math.isclose(
        abs(converted.complex_value()) ** 2 * normalization,
        float(witness["derived"]["converted_power"]),
        rel_tol=1e-14,
    )
    assert math.isclose(
        abs(retained.complex_value()) ** 2 * normalization,
        float(witness["derived"]["retained_power"]),
        rel_tol=1e-14,
    )
    assert float(witness["derived"]["converted_power"]) < float(
        witness["interpretation"]["chen_cell_conversion_gate"]
    )


def test_native_reference_screen_retains_partial_success_and_exact_fault() -> None:
    witness_path = (
        Path(__file__).parents[1]
        / "fixtures"
        / "achromatic"
        / "native-reference-screen-20260814.json"
    )
    witness = json.loads(witness_path.read_text(encoding="utf-8"))["values"]
    complete = tuple(
        item for item in witness["observations"] if item["status"] == "complete"
    )
    eligible = tuple(
        item["geometry"]
        for item in complete
        if Decimal(item["converted_power"])
        >= Decimal(witness["interpretation"]["minimum_converted_power"])
    )

    assert witness["fault"] == "periodic_time_budget_exhausted"
    assert witness["no_native_retry"] is True
    assert len(complete) == witness["interpretation"]["complete_geometry_count"]
    assert eligible == tuple(witness["interpretation"]["eligible_complete_geometries"])
    assert witness["interpretation"]["scope"] == (
        "reference wavelength only; no full-band qualification"
    )


def _coefficient_from_mapping(value: object) -> ComplexCoefficient:
    assert isinstance(value, dict)
    return ComplexCoefficient(
        real_part=Decimal(str(value["real_part"])),
        imaginary_part=Decimal(str(value["imaginary_part"])),
    )


def test_reference_screen_filters_before_the_full_spectral_followup() -> None:
    plan = _plan()
    binding = _binding(plan.full_band_wavelengths_nm)
    periodic_binding_reference = reference_for(b"spectral periodic solver")
    request, screen = _screen(plan, binding, periodic_binding_reference)

    assert request.items[0].wavelength_nm == 530
    assert len(request.items) == len(plan.geometries) * 2
    assert screen.eligible_geometries == plan.geometries
    assert SpectralCellScreen.from_document(screen.document()) == screen


def test_reference_screen_retains_numerical_incompletion_as_unresolved() -> None:
    plan = _plan()
    binding = _binding(plan.full_band_wavelengths_nm)
    periodic_binding_reference = reference_for(b"spectral periodic solver")
    request, _complete = _screen(plan, binding, periodic_binding_reference)
    outcome = _incomplete_outcome(request)

    screen = form_spectral_cell_screen(
        plan,
        request,
        outcome,
        convention=PolarizationConvention(circular_input="left"),
        solver_binding_reference=periodic_binding_reference,
        profile=_profile(),
        profile_reference=plan.qualification_profile_reference,
    )

    unresolved = plan.geometries[-1]
    assert screen.unresolved_geometries == (unresolved,)
    assert unresolved not in screen.eligible_geometries
    assert unresolved not in screen.filtered_geometries
    assert screen.incompletions[0].source_references == (
        outcome.incomplete_items[0].body_reference,
    )
    assert SpectralCellScreen.from_document(screen.document()) == screen


def test_full_band_projection_contains_only_reference_screen_survivors() -> None:
    plan = _plan()
    binding = _binding(plan.full_band_wavelengths_nm)
    periodic_binding_reference = reference_for(b"spectral periodic solver")
    excluded = plan.geometries[0]
    _, screen = _screen(
        plan,
        binding,
        periodic_binding_reference,
        weakened_geometry=excluded,
    )
    plan_reference = reference_for(plan.document().to_bytes())
    screen_reference = reference_for(screen.document().to_bytes())
    task = Task(
        proof_identity="sha256:" + "7" * 64,
        claim="spectral_jones_library",
        method="observe_spectral_jones",
        schema="metacraft.science.metalens.spectral_jones_library",
        brief_identity="sha256:" + "8" * 64,
        design_identity="sha256:" + "9" * 64,
        prerequisite_evidence=(plan_reference, screen_reference),
        consultations=(),
        binding_reference=periodic_binding_reference,
        capacity_scope="fixture:spectral-periodic",
    )

    requests = project_spectral_periodic_requests(plan, binding, screen, task=task)

    assert excluded not in screen.eligible_geometries
    assert len(screen.eligible_geometries) == len(plan.geometries) - 1
    assert all(
        work.geometry
        != RectangularCrossSection(excluded.short_side_nm, excluded.long_side_nm)
        for request in requests
        for work in request.items
    )
    assert sum(len(request.items) for request in requests) == (
        (len(plan.wavelengths_nm) - 1) * len(screen.eligible_geometries) * 2
    )


def test_plan_projects_one_atomic_periodic_request_per_wavelength() -> None:
    plan = _plan()
    binding = _binding(plan.full_band_wavelengths_nm)
    plan_reference = reference_for(plan.document().to_bytes())
    periodic_binding_reference = reference_for(b"spectral periodic solver")
    _, screen = _screen(plan, binding, periodic_binding_reference)
    screen_reference = reference_for(screen.document().to_bytes())
    task = Task(
        proof_identity="sha256:" + "1" * 64,
        claim="spectral_jones_library",
        method="observe_spectral_jones",
        schema="metacraft.science.metalens.spectral_jones_library",
        brief_identity="sha256:" + "2" * 64,
        design_identity="sha256:" + "3" * 64,
        prerequisite_evidence=(plan_reference, screen_reference),
        consultations=(),
        binding_reference=periodic_binding_reference,
        capacity_scope="fixture:spectral-periodic",
    )

    requests = project_spectral_periodic_requests(plan, binding, screen, task=task)

    assert tuple(request.items[0].wavelength_nm for request in requests) == (
        tuple(
            wavelength
            for wavelength in plan.wavelengths_nm
            if wavelength != plan.reference_wavelength_nm
        )
    )
    assert all(len(request.items) == len(plan.geometries) * 2 for request in requests)
    assert (
        len({item.work_identity for request in requests for item in request.items})
        == plan.maximum_followup_work_count
    )
    assert all(
        item.binding_reference == periodic_binding_reference
        and item.period_nm == plan.period_nm
        and item.height_nm == plan.height_nm
        and item.output_basis == "cartesian"
        and item.order_regime == "zeroth order"
        for request in requests
        for item in request.items
    )
    for request in requests:
        expected_source = dict(
            zip(
                (point.wavelength_nm for point in binding.points),
                binding.source_references,
                strict=True,
            )
        )[request.items[0].wavelength_nm]
        assert {item.materials.atom_source_reference for item in request.items} == {
            expected_source
        }
        assert {
            item.materials.substrate_source_reference for item in request.items
        } == {expected_source}
        assert {item.cell_identity for item in request.items[::2]} == {
            item.cell_identity for item in request.items[1::2]
        }


def test_observed_periodic_batches_form_one_source_complete_spectral_library() -> None:
    plan = _plan()
    binding = _binding(plan.full_band_wavelengths_nm)
    plan_reference = reference_for(plan.document().to_bytes())
    periodic_binding_reference = reference_for(b"spectral periodic solver")
    _, screen = _screen(plan, binding, periodic_binding_reference)
    screen_reference = reference_for(screen.document().to_bytes())
    task = Task(
        proof_identity="sha256:" + "1" * 64,
        claim="spectral_jones_library",
        method="observe_spectral_jones",
        schema="metacraft.science.metalens.spectral_jones_library",
        brief_identity="sha256:" + "2" * 64,
        design_identity="sha256:" + "3" * 64,
        prerequisite_evidence=(plan_reference, screen_reference),
        consultations=(),
        binding_reference=periodic_binding_reference,
        capacity_scope="fixture:spectral-periodic",
    )
    requests = project_spectral_periodic_requests(plan, binding, screen, task=task)
    outcomes = []
    for request in requests:
        admitted = []
        for work in request.items:
            basis = work.input_basis.removesuffix(" linear")
            values = {
                "basis": basis,
                "candidate": work.candidate_mapping(),
                "execution": {
                    "native": False,
                    "placement": {},
                    "project": "recorded spectral fixture",
                    "return_code": 0,
                    "source": "test",
                },
                "output_x": {
                    "imaginary_part": "0",
                    "real_part": "0.8" if basis == "x" else "0",
                },
                "output_y": {
                    "imaginary_part": "0",
                    "real_part": "0" if basis == "x" else "-0.8",
                },
                "phase_planes": "same input and output reference planes",
                "reference_surface": _reference_surface_values(
                    work.wavelength_nm,
                    basis,
                    transmitted_power=Decimal("0.64"),
                ),
                "solver_status": "complete",
                "warnings": [],
            }
            decoded = decode_periodic_polarization(values)
            body_reference = reference_for(
                Document(work.observation_schema, values).to_bytes()
            )
            admitted.append(
                form_admitted_periodic_polarization(
                    work.work_identity,
                    decoded,
                    body_reference,
                    reference_for(f"receipt {work.work_identity}".encode("ascii")),
                )
            )
        outcomes.append(
            ObservedPeriodicPolarization(
                request_identity=request.request_identity,
                items=tuple(admitted),
                closure=PeriodicResponseClosure(
                    request.request_identity,
                    ExternalActivityClosure.none(),
                    ExternalActivityClosure.none(),
                ),
            )
        )

    library = form_spectral_jones_library(
        plan,
        screen,
        requests,
        tuple(outcomes),
        convention=PolarizationConvention(circular_input="left"),
        solver_binding_reference=periodic_binding_reference,
    )

    assert len(library.observations) == len(plan.geometries) * len(plan.wavelengths_nm)
    assert all(
        len(observation.source_references) == 2
        and observation.transmitted_power_per_squared_amplitude == 1
        for observation in library.observations
    )
    assert SpectralJonesLibrary.from_document(library.document()) == library


def test_periodic_jones_power_is_normalized_by_its_reference_surfaces() -> None:
    plan = _plan()
    binding = _binding(plan.full_band_wavelengths_nm)
    plan_reference = reference_for(plan.document().to_bytes())
    periodic_binding_reference = reference_for(b"spectral periodic solver")
    _, screen = _screen(plan, binding, periodic_binding_reference)
    screen_reference = reference_for(screen.document().to_bytes())
    task = Task(
        proof_identity="sha256:" + "1" * 64,
        claim="spectral_jones_library",
        method="observe_spectral_jones",
        schema="metacraft.science.metalens.spectral_jones_library",
        brief_identity="sha256:" + "2" * 64,
        design_identity="sha256:" + "3" * 64,
        prerequisite_evidence=(plan_reference, screen_reference),
        consultations=(),
        binding_reference=periodic_binding_reference,
        capacity_scope="fixture:spectral-periodic",
    )
    requests = project_spectral_periodic_requests(plan, binding, screen, task=task)
    outcomes = tuple(
        _observed_batch_with_power_normalization(
            request,
            transmitted_power_per_squared_amplitude=Decimal("0.684548590037827"),
        )
        for request in requests
    )

    library = form_spectral_jones_library(
        plan,
        screen,
        requests,
        outcomes,
        convention=PolarizationConvention(circular_input="left"),
        solver_binding_reference=periodic_binding_reference,
    )
    qualification = _qualification(_target(), plan, library)

    assert all(
        observation.transmitted_power_per_squared_amplitude
        == (
            Decimal(1)
            if observation.wavelength_nm == plan.reference_wavelength_nm
            else Decimal("0.684548590037827")
        )
        for observation in library.observations
    )
    assert all(
        Decimal("0.438111097624208")
        < assessment.minimum_converted_power
        < Decimal("0.438111097624211")
        for assessment in qualification.assessments
    )


def test_one_library_is_a_candidate_for_the_positive_target_and_refuses_neighbour() -> (
    None
):
    plan = _plan()
    library = _library(plan)

    positive = _qualification(_target(), plan, library)
    nearby = _qualification(
        _target(numerical_aperture=Decimal("0.24719")),
        plan,
        library,
    )

    assert isinstance(positive, SpectralLibraryQualification)
    assert positive.status is SpectralQualificationStatus.CANDIDATE
    assert Decimal("3.79") < positive.available_relative_delay_span_fs < Decimal("3.81")
    assert all(
        assessment.design_r_squared >= Decimal("0.99")
        and assessment.holdout_maximum_residual_rad <= Decimal("0.15")
        and assessment.minimum_converted_power >= Decimal("0.79")
        for assessment in positive.assessments
    )
    assert positive.target_reference == reference_for(_target().document().to_bytes())
    assert positive.plan_reference == library.plan_reference
    assert positive.library_reference == reference_for(library.document().to_bytes())
    assert SpectralJonesLibrary.from_document(library.document()) == library
    assert SpectralLibraryQualification.from_document(positive.document()) == positive
    assert positive.document().values["status"] == (
        "positive_single_rectangle_candidate"
    )
    assert nearby.status is SpectralQualificationStatus.DELAY_SPAN_INSUFFICIENT
    assert nearby.required_relative_delay_fs > nearby.available_relative_delay_span_fs


def test_holdout_phase_never_changes_the_design_fit_or_available_delay() -> None:
    plan = _plan()
    library = _library(plan)
    baseline = _qualification(_target(), plan, library)
    shifted = []
    for observation in library.observations:
        if observation.wavelength_nm not in plan.holdout_wavelengths_nm:
            shifted.append(observation)
            continue
        response = observation.response
        factor = cmath.exp(1j * 3.14)
        shifted.append(
            replace(
                observation,
                response=JonesResponse(
                    *(
                        _coefficient(coefficient.complex_value() * factor)
                        for coefficient in (
                            response.output_x_from_input_x,
                            response.output_y_from_input_x,
                            response.output_x_from_input_y,
                            response.output_y_from_input_y,
                        )
                    )
                ),
            )
        )

    challenged = _qualification(
        _target(),
        plan,
        replace(library, observations=tuple(shifted)),
    )

    assert tuple(item.relative_delay_fs for item in challenged.assessments) == (
        tuple(item.relative_delay_fs for item in baseline.assessments)
    )
    assert tuple(item.design_r_squared for item in challenged.assessments) == (
        tuple(item.design_r_squared for item in baseline.assessments)
    )
    assert (
        challenged.status
        is SpectralQualificationStatus.INTERLEAVED_VALIDATION_INSUFFICIENT
    )
    assert all(
        item.holdout_maximum_residual_rad > Decimal("3.13")
        for item in challenged.assessments
    )


def test_ineligible_cell_is_filtered_before_library_coverage_is_assessed() -> None:
    plan = _plan()
    library = _library(plan)
    excluded_geometry = plan.geometries[0]
    weakened = tuple(
        (
            replace(
                observation,
                response=JonesResponse(
                    *(
                        _coefficient(coefficient.complex_value() * 0.1)
                        for coefficient in (
                            observation.response.output_x_from_input_x,
                            observation.response.output_y_from_input_x,
                            observation.response.output_x_from_input_y,
                            observation.response.output_y_from_input_y,
                        )
                    )
                ),
            )
            if observation.geometry == excluded_geometry
            else observation
        )
        for observation in library.observations
    )

    qualification = _qualification(
        _target(),
        plan,
        replace(library, observations=weakened),
    )

    assert qualification.status is SpectralQualificationStatus.CANDIDATE
    assert (
        Decimal("3.77")
        < qualification.available_relative_delay_span_fs
        < Decimal("3.78")
    )
    assert len(qualification.assessments) == len(plan.geometries)


def test_incomplete_atomic_jones_sweep_never_becomes_a_physics_refusal() -> None:
    plan = _plan()
    complete = _library(plan)
    incomplete = replace(complete, observations=complete.observations[:-1])

    result = _qualification(_target(), plan, incomplete)

    assert result.status is SpectralQualificationStatus.EVIDENCE_INCOMPLETE
    assert not result.assessments
    assert result.reasons == (
        f"{plan.geometries[-1].short_side_nm}x"
        f"{plan.geometries[-1].long_side_nm}@590nm",
    )


def _assigned_aperture() -> tuple[
    AchromaticAperture,
    SpectralCellStudyPlan,
    SpectralJonesLibrary,
]:
    target = _target()
    plan = _plan()
    library = _library(plan)
    qualification = _qualification(target, plan, library)
    target_reference = reference_for(target.document().to_bytes())
    plan_reference = reference_for(plan.document().to_bytes())
    library_reference = reference_for(library.document().to_bytes())
    qualification_reference = reference_for(qualification.document().to_bytes())
    lattice = resolve_lattice(
        resolve_metalens_design(continuous_achromatic_publication_brief()),
        spacing_nm=plan.period_nm,
        spacing_source_reference=plan_reference,
    )
    assert isinstance(lattice, Lattice)
    lattice_reference = reference_for(lattice.document().to_bytes())
    return (
        assign_continuous_achromatic_aperture(
            target,
            plan,
            library,
            qualification,
            lattice,
            target_reference=target_reference,
            plan_reference=plan_reference,
            library_reference=library_reference,
            qualification_reference=qualification_reference,
            lattice_reference=lattice_reference,
            selection_binding_reference=reference_for(b"deterministic selection"),
        ),
        plan,
        library,
    )


def test_continuous_aperture_uses_geometry_for_delay_and_pb_for_phase() -> None:
    target = _target()
    aperture, plan, _library_value = _assigned_aperture()

    assert target.phase_convention.endswith("-2 theta")
    assert aperture.phase_sign == -1
    assert aperture.site_count > 1
    assert aperture.lattice_reference == reference_for(
        resolve_lattice(
            resolve_metalens_design(continuous_achromatic_publication_brief()),
            spacing_nm=320,
            spacing_source_reference=reference_for(plan.document().to_bytes()),
        ).document().to_bytes()  # type: ignore[union-attr]
    )
    assert len(set(aperture.geometry_indices[aperture.is_occupied].tolist())) > 1
    phase_error = numpy.angle(
        numpy.exp(
            1j
            * (
                aperture.realized_reference_phase_rad[aperture.is_occupied]
                - aperture.target_reference_phase_rad[aperture.is_occupied]
            )
        )
    )
    assert numpy.max(numpy.abs(phase_error)) < 1e-12
    assert numpy.max(aperture.delay_error_fs[aperture.is_occupied]) < 0.25

    restored = AchromaticAperture.from_document(aperture.document())
    assert restored.document().to_bytes() == aperture.document().to_bytes()
    assert numpy.array_equal(restored.geometry_indices, aperture.geometry_indices)
    assert not restored.orientations_rad.flags.writeable


def test_fixed_aperture_records_selection_and_adjacency_diagnostics() -> None:
    aperture, _plan_value, _library_value = _assigned_aperture()
    occupied = aperture.is_occupied
    assigned = {
        aperture.geometries[int(index)]
        for index in aperture.geometry_indices[occupied]
    }

    assert aperture.used_geometries == tuple(
        geometry
        for geometry in aperture.geometries
        if geometry in assigned or geometry == aperture.baseline_geometry
    )
    assert set(aperture.used_geometries) == assigned | {aperture.baseline_geometry}
    assert aperture.selection_policy == (
        "minimum absolute relative-delay error",
        "greater minimum converted power",
        "lower holdout phase residual",
        "smaller rectangular dimensions",
    )

    diagnostics = aperture.adjacency_diagnostics
    expected_right = numpy.zeros(occupied.shape, dtype=numpy.bool_)
    expected_right[:, :-1] = occupied[:, :-1] & occupied[:, 1:]
    expected_down = numpy.zeros(occupied.shape, dtype=numpy.bool_)
    expected_down[:-1, :] = occupied[:-1, :] & occupied[1:, :]
    assert numpy.array_equal(diagnostics.is_right_adjacent, expected_right)
    assert numpy.array_equal(diagnostics.is_down_adjacent, expected_down)
    assert diagnostics.right_dimension_jumps_nm.shape == (*occupied.shape, 2)
    assert diagnostics.down_dimension_jumps_nm.shape == (*occupied.shape, 2)
    assert set(diagnostics.right_transition_classes[expected_right]) <= {
        "same geometry",
        "short-side jump",
        "long-side jump",
        "two-dimension jump",
    }
    assert set(diagnostics.down_transition_classes[expected_down]) <= {
        "same geometry",
        "short-side jump",
        "long-side jump",
        "two-dimension jump",
    }
    assert not diagnostics.right_dimension_jumps_nm.flags.writeable
    assert not diagnostics.down_transition_classes.flags.writeable

    restored = AchromaticAperture.from_document(aperture.document())
    assert restored.used_geometries == aperture.used_geometries
    assert restored.adjacency_diagnostics.as_mapping() == diagnostics.as_mapping()
    assert restored.document().to_bytes() == aperture.document().to_bytes()


def test_polarization_handedness_controls_the_pb_sign() -> None:
    left_target = _target()
    plan = _plan()
    left_library = _library(plan)
    right_target = replace(
        left_target,
        phase_convention="exp(-i omega t); converted PB phase +2 theta",
    )
    right_library = replace(
        left_library,
        convention=PolarizationConvention(circular_input="right"),
    )
    right_qualification = _qualification(right_target, plan, right_library)
    target_reference = reference_for(right_target.document().to_bytes())
    plan_reference = reference_for(plan.document().to_bytes())
    library_reference = reference_for(right_library.document().to_bytes())
    qualification_reference = reference_for(
        right_qualification.document().to_bytes()
    )
    lattice = resolve_lattice(
        resolve_metalens_design(continuous_achromatic_publication_brief()),
        spacing_nm=plan.period_nm,
        spacing_source_reference=plan_reference,
    )
    assert isinstance(lattice, Lattice)

    aperture = assign_continuous_achromatic_aperture(
        right_target,
        plan,
        right_library,
        right_qualification,
        lattice,
        target_reference=target_reference,
        plan_reference=plan_reference,
        library_reference=library_reference,
        qualification_reference=qualification_reference,
        lattice_reference=reference_for(lattice.document().to_bytes()),
        selection_binding_reference=reference_for(b"deterministic selection"),
    )

    assert aperture.phase_sign == 1
    phase_error = numpy.angle(
        numpy.exp(
            1j
            * (
                aperture.propagation_reference_phase_rad[aperture.is_occupied]
                + 2 * aperture.orientations_rad[aperture.is_occupied]
                - aperture.realized_reference_phase_rad[aperture.is_occupied]
            )
        )
    )
    assert numpy.max(numpy.abs(phase_error)) < 1e-12

    left_qualification = _qualification(right_target, plan, left_library)
    with TestCase().assertRaisesRegex(
        ValueError,
        "achromatic_aperture_phase_convention_mismatch",
    ):
        assign_continuous_achromatic_aperture(
            right_target,
            plan,
            left_library,
            left_qualification,
            lattice,
            target_reference=target_reference,
            plan_reference=plan_reference,
            library_reference=reference_for(left_library.document().to_bytes()),
            qualification_reference=reference_for(
                left_qualification.document().to_bytes()
            ),
            lattice_reference=reference_for(lattice.document().to_bytes()),
            selection_binding_reference=reference_for(b"deterministic selection"),
        )


def test_aperture_rejects_non_candidate_and_cross_linked_evidence() -> None:
    target = _target()
    nearby_target = _target(numerical_aperture=Decimal("0.24719"))
    plan = _plan()
    library = _library(plan)
    qualification = _qualification(target, plan, library)
    nearby_qualification = _qualification(nearby_target, plan, library)
    target_reference = reference_for(target.document().to_bytes())
    nearby_target_reference = reference_for(nearby_target.document().to_bytes())
    plan_reference = reference_for(plan.document().to_bytes())
    library_reference = reference_for(library.document().to_bytes())
    qualification_reference = reference_for(qualification.document().to_bytes())
    lattice = resolve_lattice(
        resolve_metalens_design(continuous_achromatic_publication_brief()),
        spacing_nm=plan.period_nm,
        spacing_source_reference=plan_reference,
    )
    assert isinstance(lattice, Lattice)

    with TestCase().assertRaisesRegex(
        ValueError,
        "achromatic_aperture_requires_candidate_library",
    ):
        assign_continuous_achromatic_aperture(
            nearby_target,
            plan,
            library,
            nearby_qualification,
            lattice,
            target_reference=nearby_target_reference,
            plan_reference=plan_reference,
            library_reference=library_reference,
            qualification_reference=reference_for(
                nearby_qualification.document().to_bytes()
            ),
            lattice_reference=reference_for(lattice.document().to_bytes()),
            selection_binding_reference=reference_for(b"deterministic selection"),
        )

    foreign_lattice = replace(
        lattice,
        spacing_source_reference=reference_for(b"foreign spectral plan"),
    )
    with TestCase().assertRaisesRegex(
        ValueError,
        "achromatic_aperture_evidence_mismatch",
    ):
        assign_continuous_achromatic_aperture(
            target,
            plan,
            library,
            qualification,
            foreign_lattice,
            target_reference=target_reference,
            plan_reference=plan_reference,
            library_reference=library_reference,
            qualification_reference=qualification_reference,
            lattice_reference=reference_for(foreign_lattice.document().to_bytes()),
            selection_binding_reference=reference_for(b"deterministic selection"),
        )

    cross_linked_library = replace(
        library,
        plan_reference=reference_for(b"foreign spectral plan"),
    )
    with TestCase().assertRaisesRegex(
        ValueError,
        "achromatic_aperture_evidence_mismatch",
    ):
        assign_continuous_achromatic_aperture(
            target,
            plan,
            cross_linked_library,
            qualification,
            lattice,
            target_reference=target_reference,
            plan_reference=plan_reference,
            library_reference=reference_for(
                cross_linked_library.document().to_bytes()
            ),
            qualification_reference=qualification_reference,
            lattice_reference=reference_for(lattice.document().to_bytes()),
            selection_binding_reference=reference_for(b"deterministic selection"),
        )


def test_aperture_assignment_creates_no_rotation_solver_work() -> None:
    target = _target()
    plan = _plan()
    library = _library(plan)
    target_reference = reference_for(target.document().to_bytes())
    plan_reference = reference_for(plan.document().to_bytes())
    lattice = resolve_lattice(
        resolve_metalens_design(continuous_achromatic_publication_brief()),
        spacing_nm=plan.period_nm,
        spacing_source_reference=plan_reference,
    )
    assert isinstance(lattice, Lattice)

    def forbid_rotation_solver_projection(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("aperture assignment projected periodic solver work")

    with patch(
        "metacraft.science.metalens.achromatic.project_spectral_periodic_requests",
        side_effect=forbid_rotation_solver_projection,
    ):
        qualification = _qualification(target, plan, library)
        aperture = assign_continuous_achromatic_aperture(
            target,
            plan,
            library,
            qualification,
            lattice,
            target_reference=target_reference,
            plan_reference=plan_reference,
            library_reference=reference_for(library.document().to_bytes()),
            qualification_reference=reference_for(
                qualification.document().to_bytes()
            ),
            lattice_reference=reference_for(lattice.document().to_bytes()),
            selection_binding_reference=reference_for(b"deterministic selection"),
        )

    assert aperture.site_count == lattice.site_count


def test_all_wavelength_fields_reuse_one_layout_and_pb_baseline() -> None:
    aperture, plan, library = _assigned_aperture()
    aperture_reference = reference_for(aperture.document().to_bytes())

    fields = {
        (strategy, wavelength): form_achromatic_aperture_field(
            aperture,
            library,
            wavelength_nm=wavelength,
            strategy=strategy,
            aperture_reference=aperture_reference,
        )
        for strategy in ("continuous compensation", "pb-only baseline")
        for wavelength in (plan.wavelengths_nm[0], plan.wavelengths_nm[-1])
    }

    assert {field.surface.shape for field in fields.values()} == {
        aperture.is_occupied.shape
    }
    assert {field.surface.spacing_m for field in fields.values()} == {
        aperture.period_nm * 1e-9
    }
    assert all(field.component_names == ("right", "left") for field in fields.values())
    assert all(not field.electric("right").flags.writeable for field in fields.values())
    assert not numpy.array_equal(
        fields[("continuous compensation", plan.wavelengths_nm[-1])].electric("right"),
        fields[("pb-only baseline", plan.wavelengths_nm[-1])].electric("right"),
    )


def _complete_focus(*, focal_shift_m: float, leakage_fraction: float) -> Focus:
    span = HalfMaximum(-1e-6, 1e-6, 2e-6, True)
    distances = (4.8e-5, 4.9e-5, 5.0e-5)
    return Focus(
        expected_focus_m=4.9e-5,
        found_focus_m=4.9e-5 + focal_shift_m,
        focal_shift_m=focal_shift_m,
        x_half_maximum=span,
        y_half_maximum=span,
        depth_of_focus=span,
        transmitted_fraction=0.8,
        focused_fraction=0.6,
        focus_efficiency=0.48,
        peak_intensity=1.0,
        airy_radius_m=1.5e-6,
        is_focus_bracketed=True,
        observed_components=("right",),
        convergence=FocusConvergence(3, 1e-6, False),
        axial_distances_m=distances,
        axial_peak_intensities=(0.5, 1.0, 0.5),
        leakage=Leakage(
            channel="retained",
            role="leakage",
            observed_distance_m=4.9e-5,
            transmitted_fraction=leakage_fraction,
            peak_intensity=0.1,
            integrated_intensity=1.0,
            axial_distances_m=distances,
            axial_peak_intensities=(0.1, 0.2, 0.1),
        ),
    )


def test_achromatic_focus_retains_design_holdout_and_pb_baseline() -> None:
    aperture, plan, _library_value = _assigned_aperture()
    aperture_reference = reference_for(aperture.document().to_bytes())
    field_entries = tuple(
        SpectralFieldEntry(
            strategy=strategy,
            wavelength_nm=wavelength,
            field_reference=reference_for(f"field:{strategy}:{wavelength}".encode()),
            focal_region_reference=reference_for(
                f"region:{strategy}:{wavelength}".encode()
            ),
        )
        for strategy in ("continuous compensation", "pb-only baseline")
        for wavelength in plan.full_band_wavelengths_nm
    )
    family = SpectralFieldFamily(
        aperture_reference=aperture_reference,
        qualification_reference=aperture.qualification_reference,
        library_reference=aperture.library_reference,
        propagation_binding_reference=reference_for(b"angular spectrum"),
        post_freeze_library_reference=reference_for(b"post-freeze library"),
        design_wavelengths_nm=plan.design_wavelengths_nm,
        holdout_wavelengths_nm=plan.holdout_wavelengths_nm,
        blind_verification_wavelengths_nm=plan.blind_verification_wavelengths_nm,
        entries=field_entries,
    )
    family_reference = reference_for(family.document().to_bytes())
    entries = tuple(
        AchromaticFocusEntry(
            strategy=item.strategy,
            wavelength_nm=item.wavelength_nm,
            focus_reference=reference_for(
                f"focus:{item.strategy}:{item.wavelength_nm}".encode()
            ),
            focus=_complete_focus(
                focal_shift_m=(1e-7 if item.strategy == "continuous compensation" else 8e-7),
                leakage_fraction=0.03,
            ),
        )
        for item in field_entries
    )

    result = form_achromatic_focus(
        family,
        entries,
        family_reference=family_reference,
        evaluation_binding_reference=reference_for(b"focus evaluation"),
    )

    assert result.compensated_focal_shift_improvement_m == 7e-7
    assert len(result.entries) == 2 * len(plan.full_band_wavelengths_nm)
    assert len(result.role_summaries) == 6
    assert AchromaticFocus.from_document(result.document()).document().to_bytes() == (
        result.document().to_bytes()
    )

from __future__ import annotations

import cmath
from dataclasses import replace
from decimal import Decimal
import math

from metacraft.authority import Document
from metacraft.authority.reference import reference_for
from metacraft.external_activity import ExternalActivityClosure
from metacraft.science.metalens.achromatic import (
    AchromaticAperture,
    AchromaticTarget,
    ResponseQualificationProfile,
    SpectralCellStudyPlan,
    SpectralJonesLibrary,
    SpectralJonesObservation,
    SpectralLibraryQualification,
    SpectralMaterialBinding,
    SpectralMaterialPoint,
    SpectralStudySpecification,
    assign_continuous_achromatic_aperture,
    form_spectral_cell_study_plan,
    form_spectral_study_specification,
    qualify_spectral_jones_library,
)
from metacraft.science.metalens.aperture import Lattice, resolve_lattice
from metacraft.science.metalens.design import resolve_metalens_design
from metacraft.science.metalens.focus import (
    Focus,
    FocusConvergence,
    HalfMaximum,
    Leakage,
)
from metacraft.science.metalens.geometric_phase import (
    ComplexCoefficient,
    JonesResponse,
    PolarizationConvention,
)
from metacraft.science.periodic_response import (
    AdmittedPeriodicObservationIncomplete,
    PeriodicObservationIncomplete,
    PeriodicObservationIncompleteReason,
    PeriodicPolarizationIncomplete,
    PeriodicPolarizationRequest,
    PeriodicResponseClosure,
)
from tests.brief_fixtures import (
    continuous_achromatic_brief,
    continuous_achromatic_publication_brief,
)


def achromatic_target(
    *, numerical_aperture: Decimal = Decimal("0.2")
) -> AchromaticTarget:
    brief = replace(
        continuous_achromatic_brief(),
        numerical_aperture=numerical_aperture,
    )
    return AchromaticTarget.from_design(resolve_metalens_design(brief))


def spectral_binding(wavelengths_nm: tuple[int, ...]) -> SpectralMaterialBinding:
    return SpectralMaterialBinding(
        atom_family="amorphous titanium dioxide",
        atom_native_name="TiO2 (Titanium Dioxide) - Siefke",
        substrate_family="glass",
        substrate_native_name="SiO2 (Glass) - Palik",
        points=tuple(
            SpectralMaterialPoint(
                wavelength_nm=wavelength_nm,
                atom_refractive_index=Decimal("2.45"),
                atom_extinction_coefficient=Decimal("0.0000002"),
                substrate_refractive_index=Decimal("1.46"),
                substrate_extinction_coefficient=Decimal(0),
            )
            for wavelength_nm in wavelengths_nm
        ),
        solver_binding_reference=reference_for(b"spectral material solver"),
        source_references=tuple(
            reference_for(f"spectral material sample {wavelength_nm}".encode("ascii"))
            for wavelength_nm in wavelengths_nm
        ),
    )


def qualification_profile() -> ResponseQualificationProfile:
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


def spectral_specification() -> SpectralStudySpecification:
    profile = qualification_profile()
    return form_spectral_study_specification(
        achromatic_target(),
        qualification_profile_reference=reference_for(profile.document().to_bytes()),
    )


def spectral_plan() -> SpectralCellStudyPlan:
    target = achromatic_target()
    specification = spectral_specification()
    binding = spectral_binding(specification.full_band_wavelengths_nm)
    outcome = form_spectral_cell_study_plan(
        target,
        binding,
        material_binding_reference=reference_for(binding.document().to_bytes()),
        dimension_step_nm=10,
        aspect_limit=8,
        specification=specification,
        specification_reference=reference_for(specification.document().to_bytes()),
    )
    assert isinstance(outcome, SpectralCellStudyPlan)
    return outcome


def complex_coefficient(value: complex) -> ComplexCoefficient:
    return ComplexCoefficient(
        real_part=Decimal(str(value.real)),
        imaginary_part=Decimal(str(value.imag)),
    )


def candidate_library(plan: SpectralCellStudyPlan) -> SpectralJonesLibrary:
    observations = []
    for index, geometry in enumerate(plan.geometries):
        delay_fs = 3.8 * index / (len(plan.geometries) - 1)
        reference_omega = 2 * math.pi * 299.792458 / 530
        intercept = index * 2 * math.pi / len(plan.geometries) - delay_fs * reference_omega
        for wavelength_nm in plan.wavelengths_nm:
            omega = 2 * math.pi * 299.792458 / wavelength_nm
            converted = math.sqrt(0.8) * cmath.exp(1j * (intercept + delay_fs * omega))
            observations.append(
                SpectralJonesObservation(
                    geometry=geometry,
                    wavelength_nm=wavelength_nm,
                    response=JonesResponse(
                        output_x_from_input_x=complex_coefficient(converted),
                        output_y_from_input_x=complex_coefficient(0j),
                        output_x_from_input_y=complex_coefficient(0j),
                        output_y_from_input_y=complex_coefficient(-converted),
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


def qualify_candidate_library(
    target: AchromaticTarget,
    plan: SpectralCellStudyPlan,
    library: SpectralJonesLibrary,
) -> SpectralLibraryQualification:
    return qualify_spectral_jones_library(
        target,
        plan,
        library,
        profile=qualification_profile(),
        profile_reference=plan.qualification_profile_reference,
    )


def assigned_aperture() -> tuple[
    AchromaticAperture,
    SpectralCellStudyPlan,
    SpectralJonesLibrary,
]:
    target = achromatic_target()
    plan = spectral_plan()
    library = candidate_library(plan)
    qualification = qualify_candidate_library(target, plan, library)
    plan_reference = reference_for(plan.document().to_bytes())
    lattice = resolve_lattice(
        resolve_metalens_design(continuous_achromatic_publication_brief()),
        spacing_nm=plan.period_nm,
        spacing_source_reference=plan_reference,
    )
    assert isinstance(lattice, Lattice)
    return (
        assign_continuous_achromatic_aperture(
            target,
            plan,
            library,
            qualification,
            lattice,
            target_reference=reference_for(target.document().to_bytes()),
            plan_reference=plan_reference,
            library_reference=reference_for(library.document().to_bytes()),
            qualification_reference=reference_for(qualification.document().to_bytes()),
            lattice_reference=reference_for(lattice.document().to_bytes()),
            selection_binding_reference=reference_for(b"deterministic selection"),
        ),
        plan,
        library,
    )


def complete_focus(*, focal_shift_m: float, leakage_fraction: float) -> Focus:
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


def blind_observations(
    *, phase_bump_rad: float = 0.0
) -> tuple[SpectralJonesObservation, ...]:
    aperture, plan, _library = assigned_aperture()
    observations = []
    for geometry in aperture.used_geometries:
        index = plan.geometries.index(geometry)
        delay_fs = 3.8 * index / (len(plan.geometries) - 1)
        intercept = index * 2 * math.pi / len(plan.geometries) - delay_fs * (
            2 * math.pi * 299.792458 / 530
        )
        for wavelength_nm in plan.blind_verification_wavelengths_nm:
            bump = phase_bump_rad if wavelength_nm == 535 else 0.0
            converted = math.sqrt(0.8) * cmath.exp(
                1j
                * (
                    intercept
                    + delay_fs * 2 * math.pi * 299.792458 / wavelength_nm
                    + bump
                )
            )
            observations.append(
                SpectralJonesObservation(
                    geometry=geometry,
                    wavelength_nm=wavelength_nm,
                    response=JonesResponse(
                        output_x_from_input_x=complex_coefficient(converted),
                        output_y_from_input_x=complex_coefficient(0j),
                        output_x_from_input_y=complex_coefficient(0j),
                        output_y_from_input_y=complex_coefficient(-converted),
                    ),
                    transmitted_power_per_squared_amplitude=Decimal(1),
                    source_references=(
                        reference_for(f"blind x {geometry} {wavelength_nm}".encode()),
                        reference_for(f"blind y {geometry} {wavelength_nm}".encode()),
                    ),
                )
            )
    return tuple(observations)


def incomplete_periodic_outcome(
    request: PeriodicPolarizationRequest,
) -> PeriodicPolarizationIncomplete:
    work = request.items[-1]
    outcome = PeriodicObservationIncomplete(
        work_identity=work.work_identity,
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
            outcome.as_mapping(),
        ).to_bytes()
    )
    return PeriodicPolarizationIncomplete(
        request_identity=request.request_identity,
        items=(),
        incomplete_items=(
            AdmittedPeriodicObservationIncomplete(
                work.work_identity,
                outcome,
                body_reference,
                reference_for(b"incomplete receipt"),
            ),
        ),
        closure=PeriodicResponseClosure(
            request.request_identity,
            ExternalActivityClosure.none(),
            ExternalActivityClosure.none(),
        ),
    )

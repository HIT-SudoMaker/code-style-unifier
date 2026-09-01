from __future__ import annotations

import cmath
from dataclasses import replace
from decimal import Decimal
import math

from metacraft.authority.reference import reference_for
from metacraft.science.metalens.achromatic import (
    AchromaticTarget,
    ResponseQualificationProfile,
    SpectralCellStudyPlan,
    SpectralJonesLibrary,
    SpectralJonesObservation,
    SpectralQualificationStatus,
    form_spectral_cell_study_plan,
    form_spectral_study_specification,
    qualify_spectral_jones_library,
)
from metacraft.science.metalens.geometric_phase import (
    ComplexCoefficient,
    JonesResponse,
    PolarizationConvention,
)
from tests.achromatic_fixtures import (
    achromatic_target as _target,
    qualification_profile as _profile,
    spectral_binding as _binding,
)


def _coefficient(value: complex) -> ComplexCoefficient:
    return ComplexCoefficient(
        real_part=Decimal(str(value.real)),
        imaginary_part=Decimal(str(value.imag)),
    )


def _candidate(
    profile: ResponseQualificationProfile | None = None,
) -> tuple[AchromaticTarget, SpectralCellStudyPlan, SpectralJonesLibrary]:
    target = _target()
    profile = _profile() if profile is None else profile
    specification = form_spectral_study_specification(
        target,
        qualification_profile_reference=reference_for(profile.document().to_bytes()),
    )
    binding = _binding(specification.full_band_wavelengths_nm)
    plan = form_spectral_cell_study_plan(
        target,
        binding,
        material_binding_reference=reference_for(binding.document().to_bytes()),
        dimension_step_nm=10,
        aspect_limit=8,
        specification=specification,
        specification_reference=reference_for(specification.document().to_bytes()),
    )
    assert isinstance(plan, SpectralCellStudyPlan)
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
                        output_x_from_input_x=_coefficient(converted),
                        output_y_from_input_x=_coefficient(0j),
                        output_x_from_input_y=_coefficient(0j),
                        output_y_from_input_y=_coefficient(-converted),
                    ),
                    transmitted_power_per_squared_amplitude=Decimal(1),
                    source_references=(
                        reference_for(f"x:{index}:{wavelength_nm}".encode()),
                        reference_for(f"y:{index}:{wavelength_nm}".encode()),
                    ),
                )
            )
    library = SpectralJonesLibrary(
        plan_reference=reference_for(plan.document().to_bytes()),
        screen_reference=reference_for(b"screen"),
        solver_binding_reference=reference_for(b"solver"),
        selected_geometries=plan.geometries,
        observations=tuple(observations),
        convention=PolarizationConvention(circular_input="left"),
    )
    return target, plan, library


def test_qualification_owns_exact_profile_and_eligible_geometry_set() -> None:
    target, plan, library = _candidate()
    profile = _profile()
    profile_reference = reference_for(profile.document().to_bytes())

    qualification = qualify_spectral_jones_library(
        target,
        plan,
        library,
        profile=profile,
        profile_reference=profile_reference,
    )

    assert qualification.status is SpectralQualificationStatus.CANDIDATE
    assert qualification.profile_reference == profile_reference
    assert qualification.campaign_reference == plan.specification_reference
    assert qualification.material_binding_reference == plan.material_binding_reference
    assert qualification.eligible_geometries
    assert qualification.eligible_geometries == tuple(
        item.geometry for item in qualification.assessments if item.is_eligible
    )
    assert all(item.maximum_leakage_power == 0 for item in qualification.assessments)


def test_profile_changes_the_verdict_without_material_name_rules() -> None:
    profile = replace(
        _profile(),
        minimum_full_band_converted_power=Decimal("0.9"),
    )
    target, plan, library = _candidate(profile)

    qualification = qualify_spectral_jones_library(
        target,
        plan,
        library,
        profile=profile,
        profile_reference=reference_for(profile.document().to_bytes()),
    )

    assert qualification.status is SpectralQualificationStatus.CONVERSION_INSUFFICIENT
    assert qualification.eligible_geometries == ()

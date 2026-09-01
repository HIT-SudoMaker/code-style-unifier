from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from metacraft.authority.reference import reference_for
from metacraft.science.metalens.achromatic import (
    AchromaticTarget,
    ResponseQualificationProfile,
    SpectralCellStudyPlan,
    SpectralMaterialBinding,
    SpectralMaterialPoint,
    SpectralStudySpecification,
    SpectralEvidenceRequirement,
    SpectralCampaignStop,
    form_spectral_cell_study_plan,
    form_spectral_study_specification,
)


def _target() -> AchromaticTarget:
    return AchromaticTarget(
        lower_wavelength_nm=470,
        upper_wavelength_nm=590,
        reference_wavelength_nm=530,
        numerical_aperture=Decimal("0.2"),
        focal_length_um=Decimal("49"),
        required_relative_delay_fs=Decimal("3.37"),
        phase_convention="exp(-i omega t); converted PB phase -2 theta",
    )


def _binding(wavelengths_nm: tuple[int, ...]) -> SpectralMaterialBinding:
    return SpectralMaterialBinding(
        atom_family="amorphous titanium dioxide",
        atom_native_name="TiO2 (Visible)",
        substrate_family="glass",
        substrate_native_name="SiO2 (Glass)",
        points=tuple(
            SpectralMaterialPoint(
                wavelength_nm=wavelength_nm,
                atom_refractive_index=Decimal("2.4"),
                atom_extinction_coefficient=Decimal("0"),
                substrate_refractive_index=Decimal("1.46"),
                substrate_extinction_coefficient=Decimal("0"),
            )
            for wavelength_nm in wavelengths_nm
        ),
        solver_binding_reference=reference_for(b"material binding"),
        source_references=tuple(
            reference_for(f"material:{wavelength_nm}".encode())
            for wavelength_nm in wavelengths_nm
        ),
    )


def _profile() -> ResponseQualificationProfile:
    return ResponseQualificationProfile(
        version="reviewed-visible-profile-v1",
        provenance=("reviewed Method contract",),
        source_references=(reference_for(b"reviewed profile source"),),
        minimum_reference_converted_power=Decimal("0.05"),
        minimum_full_band_converted_power=Decimal("0.05"),
        maximum_full_band_leakage_power=Decimal("0.20"),
        minimum_design_r_squared=Decimal("0.99"),
        maximum_interleaved_phase_residual_rad=Decimal("0.15"),
        maximum_reference_phase_gap_rad=Decimal("1.5707963267948966"),
        maximum_dense_phase_residual_rad=Decimal("0.20"),
        maximum_phase_curvature_rad=Decimal("0.10"),
    )


def test_campaign_freezes_three_wavelength_roles_and_closed_work_ceiling() -> None:
    profile = _profile()
    profile_reference = reference_for(profile.document().to_bytes())
    specification = form_spectral_study_specification(
        _target(),
        qualification_profile_reference=profile_reference,
    )

    assert specification.design_wavelengths_nm == (470, 500, 530, 560, 590)
    assert specification.holdout_wavelengths_nm == (485, 515, 545, 575)
    assert specification.blind_verification_wavelengths_nm == (
        475,
        480,
        490,
        495,
        505,
        510,
        520,
        525,
        535,
        540,
        550,
        555,
        565,
        570,
        580,
        585,
    )
    assert specification.full_band_wavelengths_nm == tuple(range(470, 591, 5))
    assert specification.maximum_reference_work_count == 272
    assert specification.maximum_candidate_followup_work_count == 2176
    assert specification.maximum_post_freeze_work_count == 4352
    assert specification.maximum_work_count == 6800
    assert specification.authorized_work_ceiling == 6800
    assert SpectralStudySpecification.from_document(specification.document()) == specification


def test_campaign_plan_enumerates_every_legal_unequal_rectangle() -> None:
    profile = _profile()
    specification = form_spectral_study_specification(
        _target(),
        qualification_profile_reference=reference_for(profile.document().to_bytes()),
    )
    binding = _binding(specification.full_band_wavelengths_nm)
    plan = form_spectral_cell_study_plan(
        _target(),
        binding,
        material_binding_reference=reference_for(binding.document().to_bytes()),
        dimension_step_nm=10,
        aspect_limit=8,
        specification=specification,
        specification_reference=reference_for(specification.document().to_bytes()),
    )

    assert isinstance(plan, SpectralCellStudyPlan)
    assert len(plan.geometries) == 136
    assert plan.geometries[0].as_mapping() == {
        "short_side_nm": 80,
        "long_side_nm": 90,
    }
    assert plan.geometries[-1].as_mapping() == {
        "short_side_nm": 230,
        "long_side_nm": 240,
    }
    assert plan.wavelengths_nm == (470, 485, 500, 515, 530, 545, 560, 575, 590)
    assert plan.full_band_wavelengths_nm == specification.full_band_wavelengths_nm
    assert plan.reference_screen_work_count == 272
    assert plan.maximum_followup_work_count == 2176
    assert plan.maximum_post_freeze_work_count == 4352
    assert plan.maximum_work_count == 6800


def test_missing_reviewed_profile_is_an_evidence_boundary() -> None:
    binding = _binding(tuple(range(470, 591, 5)))

    outcome = form_spectral_cell_study_plan(
        _target(),
        binding,
        material_binding_reference=reference_for(binding.document().to_bytes()),
        dimension_step_nm=10,
        aspect_limit=8,
    )

    assert isinstance(outcome, SpectralEvidenceRequirement)
    assert outcome.claim == "spectral_study_specification"
    assert outcome.reason == "response_qualification_profile_missing"


def test_empty_fabrication_domain_is_a_typed_pre_execution_stop() -> None:
    profile = _profile()
    specification = form_spectral_study_specification(
        _target(),
        qualification_profile_reference=reference_for(profile.document().to_bytes()),
    )
    binding = _binding(specification.full_band_wavelengths_nm)

    outcome = form_spectral_cell_study_plan(
        _target(),
        binding,
        material_binding_reference=reference_for(binding.document().to_bytes()),
        dimension_step_nm=10,
        aspect_limit=1,
        specification=specification,
        specification_reference=reference_for(specification.document().to_bytes()),
    )

    assert isinstance(outcome, SpectralEvidenceRequirement)
    assert outcome.reason == "single_rectangle_fabrication_domain_empty"


def test_exceeded_campaign_work_budget_is_a_typed_pre_execution_stop() -> None:
    profile = _profile()
    specification = form_spectral_study_specification(
        _target(),
        qualification_profile_reference=reference_for(profile.document().to_bytes()),
    )
    specification = replace(specification, authorized_work_ceiling=6799)
    binding = _binding(specification.full_band_wavelengths_nm)

    outcome = form_spectral_cell_study_plan(
        _target(),
        binding,
        material_binding_reference=reference_for(binding.document().to_bytes()),
        dimension_step_nm=10,
        aspect_limit=8,
        specification=specification,
        specification_reference=reference_for(specification.document().to_bytes()),
    )

    assert outcome == SpectralCampaignStop(
        claim="spectral_cell_study_plan",
        reason="spectral_campaign_work_budget_exceeded",
        projected_work_count=6800,
        authorized_work_ceiling=6799,
    )

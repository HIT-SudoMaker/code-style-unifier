from __future__ import annotations

import cmath
from dataclasses import replace
from decimal import Decimal
import math

from metacraft.authority.reference import reference_for
from metacraft.science.metalens.achromatic import (
    AchromaticFocusEntry,
    POST_FREEZE_JONES_LIBRARY_SCHEMA,
    BandVerificationEvidence,
    BandVerificationStatus,
    SpectralFieldEntry,
    SpectralFieldFamily,
    SpectralJonesObservation,
    form_achromatic_focus,
    form_band_verification_evidence,
    form_post_freeze_jones_library,
    project_post_freeze_blind_requests,
)
from metacraft.science.metalens.geometric_phase import JonesResponse
from metacraft.science.result import EvidenceOrigin
from metacraft.science.periodic_response import RectangularCrossSection
from metacraft.science.study import Task
from tests.achromatic_fixtures import (
    assigned_aperture as _assigned_aperture,
    complete_focus as _complete_focus,
    complex_coefficient as _coefficient,
    qualification_profile as _profile,
    spectral_binding as _binding,
)


def test_post_freeze_projection_uses_only_frozen_aperture_geometries_and_blind_role() -> None:
    aperture, plan, _library = _assigned_aperture()
    aperture_reference = reference_for(aperture.document().to_bytes())
    profile = _profile()
    profile_reference = reference_for(profile.document().to_bytes())
    task = Task(
        proof_identity="sha256:" + "a" * 64,
        claim="post_freeze_jones_library",
        method="observe_post_freeze_jones",
        schema=POST_FREEZE_JONES_LIBRARY_SCHEMA,
        brief_identity="sha256:" + "b" * 64,
        design_identity="sha256:" + "c" * 64,
        prerequisite_evidence=(aperture_reference, profile_reference),
        consultations=(),
        binding_reference=reference_for(b"periodic polarization solver"),
        capacity_scope="fixture:post-freeze-band-verification",
    )

    requests = project_post_freeze_blind_requests(
        plan,
        _binding(plan.full_band_wavelengths_nm),
        aperture,
        profile=profile,
        task=task,
    )

    assert tuple(request.items[0].wavelength_nm for request in requests) == (
        plan.blind_verification_wavelengths_nm
    )
    assert sum(len(request.items) for request in requests) == (
        len(aperture.used_geometries)
        * len(plan.blind_verification_wavelengths_nm)
        * 2
    )
    assert {
        (item.geometry.short_side_nm, item.geometry.long_side_nm)
        for request in requests
        for item in request.items
        if isinstance(item.geometry, RectangularCrossSection)
    } == {
        (geometry.short_side_nm, geometry.long_side_nm)
        for geometry in aperture.used_geometries
    }


def _blind_observations(*, phase_bump_rad: float = 0.0) -> tuple[SpectralJonesObservation, ...]:
    aperture, plan, _library = _assigned_aperture()
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
                        output_x_from_input_x=_coefficient(converted),
                        output_y_from_input_x=_coefficient(0j),
                        output_x_from_input_y=_coefficient(0j),
                        output_y_from_input_y=_coefficient(-converted),
                    ),
                    transmitted_power_per_squared_amplitude=Decimal(1),
                    source_references=(
                        reference_for(f"blind x {geometry} {wavelength_nm}".encode()),
                        reference_for(f"blind y {geometry} {wavelength_nm}".encode()),
                    ),
                )
            )
    return tuple(observations)


def _verification(phase_bump_rad: float = 0.0) -> BandVerificationEvidence:
    aperture, plan, candidate = _assigned_aperture()
    profile = _profile()
    post_freeze = form_post_freeze_jones_library(
        plan,
        aperture,
        candidate,
        _blind_observations(phase_bump_rad=phase_bump_rad),
        profile=profile,
        qualification_reference=aperture.qualification_reference,
        solver_binding_reference=candidate.solver_binding_reference,
    )
    post_freeze_reference = reference_for(post_freeze.document().to_bytes())
    entries = tuple(
        SpectralFieldEntry(
            strategy=strategy,
            wavelength_nm=wavelength,
            field_reference=reference_for(f"field:{strategy}:{wavelength}".encode()),
            focal_region_reference=reference_for(f"region:{strategy}:{wavelength}".encode()),
        )
        for strategy in ("continuous compensation", "pb-only baseline")
        for wavelength in plan.full_band_wavelengths_nm
    )
    family = SpectralFieldFamily(
        aperture_reference=reference_for(aperture.document().to_bytes()),
        qualification_reference=aperture.qualification_reference,
        library_reference=aperture.library_reference,
        propagation_binding_reference=reference_for(b"propagation"),
        post_freeze_library_reference=post_freeze_reference,
        design_wavelengths_nm=plan.design_wavelengths_nm,
        holdout_wavelengths_nm=plan.holdout_wavelengths_nm,
        blind_verification_wavelengths_nm=plan.blind_verification_wavelengths_nm,
        entries=entries,
    )
    family_reference = reference_for(family.document().to_bytes())
    focus = form_achromatic_focus(
        family,
        tuple(
            AchromaticFocusEntry(
                strategy=item.strategy,
                wavelength_nm=item.wavelength_nm,
                focus_reference=reference_for(f"focus:{item.strategy}:{item.wavelength_nm}".encode()),
                focus=_complete_focus(focal_shift_m=1e-7, leakage_fraction=0.01),
            )
            for item in entries
        ),
        family_reference=family_reference,
        evaluation_binding_reference=reference_for(b"focus evaluation"),
    )
    return form_band_verification_evidence(
        plan,
        aperture,
        candidate,
        post_freeze,
        family,
        focus,
        profile=profile,
        qualification_reference=aperture.qualification_reference,
        family_reference=family_reference,
        focus_reference=reference_for(focus.document().to_bytes()),
    )


def test_complete_dense_matrix_closes_one_replayable_pass_evidence() -> None:
    verification = _verification()

    assert verification.status is BandVerificationStatus.PASS
    assert verification.maximum_dense_phase_residual_rad is not None
    assert verification.maximum_phase_curvature_rad is not None
    assert BandVerificationEvidence.from_document(verification.document()) == verification


def test_dense_residual_and_curvature_are_distinct_post_freeze_stops() -> None:
    assert _verification(0.3).status is BandVerificationStatus.DENSE_RESIDUAL
    assert _verification(0.08).status is BandVerificationStatus.CURVATURE


def test_missing_and_numerical_blind_evidence_stop_without_fake_focus() -> None:
    aperture, plan, candidate = _assigned_aperture()
    profile = _profile()
    outcomes = []
    for numerical in (False, True):
        post_freeze = form_post_freeze_jones_library(
            plan,
            aperture,
            candidate,
            (),
            profile=profile,
            qualification_reference=aperture.qualification_reference,
            solver_binding_reference=candidate.solver_binding_reference,
            numerical_incompletion_references=(
                (reference_for(b"numerical incompletion"),) if numerical else ()
            ),
            missing_wavelengths_nm=(
                () if numerical else plan.blind_verification_wavelengths_nm
            ),
            unavailable_reasons=(
                ()
                if numerical
                else tuple(
                    f"{wavelength}:registration_absent"
                    for wavelength in plan.blind_verification_wavelengths_nm
                )
            ),
        )
        outcomes.append(
            form_band_verification_evidence(
                plan,
                aperture,
                candidate,
                post_freeze,
                None,
                None,
                profile=profile,
                qualification_reference=aperture.qualification_reference,
                family_reference=None,
                focus_reference=None,
            )
        )

    assert tuple(item.status for item in outcomes) == (
        BandVerificationStatus.MISSING_BLIND,
        BandVerificationStatus.NUMERICAL_INCOMPLETE,
    )
    assert all(
        item.spectral_field_family_reference is None and item.focus_reference is None
        for item in outcomes
    )


def test_mixed_execution_origins_stop_before_field_or_focus_formation() -> None:
    aperture, plan, candidate = _assigned_aperture()
    profile = _profile()
    observations = _blind_observations()
    mixed = (
        replace(observations[0], execution_origin=EvidenceOrigin.NATIVE),
        *observations[1:],
    )
    post_freeze = form_post_freeze_jones_library(
        plan,
        aperture,
        candidate,
        mixed,
        profile=profile,
        qualification_reference=aperture.qualification_reference,
        solver_binding_reference=candidate.solver_binding_reference,
    )

    verification = form_band_verification_evidence(
        plan,
        aperture,
        candidate,
        post_freeze,
        None,
        None,
        profile=profile,
        qualification_reference=aperture.qualification_reference,
        family_reference=None,
        focus_reference=None,
    )

    assert not post_freeze.is_complete
    assert verification.status is BandVerificationStatus.EVIDENCE_ORIGIN_MISMATCH
    assert verification.spectral_field_family_reference is None
    assert verification.focus_reference is None

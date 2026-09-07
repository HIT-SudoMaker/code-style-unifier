from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from metacraft import conduct
from metacraft.authority import Authority, Document, Reference
from metacraft.science import CompletedResults, ConductOutcome
from metacraft.science.metalens import AchromaticResult, MetalensBrief
from metacraft.science.metalens.evidence_adapter import MetalensEvidenceAdapter
from metacraft.science.metalens.result import restore_conclusion


_SCHEMA = "metacraft.examples.continuous_achromatic_showcase"
_ROLES = (
    "design",
    "interleaved_validation",
    "blind_verification",
)
Fetch = Callable[[Reference], bytes]


def run_continuous_achromatic_showcase(
    brief: MetalensBrief,
    *,
    application_root: Path,
    evidence_adapter: MetalensEvidenceAdapter | None = None,
) -> ConductOutcome | Document:
    """
    Conduct one continuous-compensation life and expose its admitted Result.

    Focus evaluation and Native evidence remain external responsibilities.
    Every typed conduct stop crosses this example unchanged; the showcase is
    formed only after the public life returns ``CompletedResults``.
    """

    outcome = conduct(
        brief,
        application_root=application_root,
        evidence_adapter=evidence_adapter,
    )
    if not isinstance(outcome, CompletedResults):
        return outcome
    authority = Authority(Path(application_root) / "authority")
    return continuous_achromatic_showcase(outcome, fetch=authority.fetch)


def continuous_achromatic_showcase(
    completed: CompletedResults,
    *,
    fetch: Fetch,
) -> Document:
    """Project the sole admitted continuous-compensation Result."""

    candidates = []
    for result in completed.results:
        conclusion = restore_conclusion(result.document, fetch=fetch)
        if isinstance(conclusion, AchromaticResult):
            candidates.append((result, conclusion))
    if len(candidates) != 1:
        raise ValueError("continuous_achromatic_showcase_result_not_unique")
    result, conclusion = candidates[0]

    aperture_values = conclusion.aperture.document().values
    focus_entries = {
        (entry.strategy, entry.wavelength_nm): entry
        for entry in conclusion.focus.entries
    }
    field_entries = {
        (entry.strategy, entry.wavelength_nm): entry
        for entry in conclusion.spectral_field_family.entries
    }
    role_wavelengths = {
        "design": conclusion.focus.design_wavelengths_nm,
        "interleaved_validation": conclusion.focus.holdout_wavelengths_nm,
        "blind_verification": (
            conclusion.focus.blind_verification_wavelengths_nm
        ),
    }
    focus_by_role = {}
    for role in _ROLES:
        wavelengths = role_wavelengths[role]
        field_and_focus = []
        for field_entry in conclusion.spectral_field_family.entries:
            if field_entry.wavelength_nm not in wavelengths:
                continue
            focus_entry = focus_entries[
                (field_entry.strategy, field_entry.wavelength_nm)
            ]
            field_and_focus.append(
                {
                    "field_reference": field_entry.field_reference.as_mapping(),
                    "focal_region_reference": (
                        field_entry.focal_region_reference.as_mapping()
                    ),
                    "focus": focus_entry.focus.as_mapping(),
                    "focus_reference": focus_entry.focus_reference.as_mapping(),
                    "strategy": field_entry.strategy,
                    "wavelength_nm": field_entry.wavelength_nm,
                }
            )
        expected_entries = {
            key: entry
            for key, entry in field_entries.items()
            if key[1] in wavelengths
        }
        if len(field_and_focus) != len(expected_entries):
            raise ValueError("continuous_achromatic_showcase_focus_mismatch")
        focus_by_role[role] = {
            "field_and_focus": field_and_focus,
            "focus_summaries": [
                summary.summary.as_mapping()
                for summary in conclusion.focus.role_summaries
                if summary.role == role
            ],
            "wavelengths_nm": list(wavelengths),
        }

    return Document(
        _SCHEMA,
        {
            "band_verification": (
                conclusion.band_verification.document().values
            ),
            "brief_identity": completed.brief_identity,
            "execution_origin": conclusion.execution_origin.value,
            "fixed_aperture": {
                "coordinates_nm": aperture_values["coordinates_nm"],
                "geometries": aperture_values["geometries"],
                "geometry_indices": aperture_values["geometry_indices"],
                "height_nm": aperture_values["height_nm"],
                "occupied": aperture_values["occupied"],
                "orientations_rad": aperture_values["orientations_rad"],
                "period_nm": aperture_values["period_nm"],
                "site_count": conclusion.aperture.site_count,
            },
            "phase_maps": {
                "geometry_controlled_phase_rad": aperture_values[
                    "propagation_reference_phase_rad"
                ],
                "pb_phase_rad": aperture_values["geometric_phase_rad"],
                "realized_composition_phase_rad": aperture_values[
                    "realized_reference_phase_rad"
                ],
                "target_phase_rad": aperture_values[
                    "target_reference_phase_rad"
                ],
            },
            "physical_semantics": {
                "pb_orientation_group_delay": "none",
                "realized_phase_composition": (
                    "geometry-controlled phase + PB phase modulo 2 pi"
                ),
                "response_coupling": (
                    "geometry-controlled and PB responses belong to the same "
                    "anisotropic structure"
                ),
            },
            "references": {
                "achromatic_aperture": (
                    conclusion.aperture_reference.as_mapping()
                ),
                "achromatic_focus": conclusion.focus_reference.as_mapping(),
                "band_verification": (
                    conclusion.band_verification_reference.as_mapping()
                ),
                "qualified_spectral_library": (
                    conclusion.qualification_reference.as_mapping()
                ),
                "result": result.reference.as_mapping(),
                "spectral_field_family": (
                    conclusion.spectral_field_family_reference.as_mapping()
                ),
            },
            "showcase": "continuous achromatic compensation",
            "spectral_focus_by_role": focus_by_role,
        },
    )


__all__ = [
    "continuous_achromatic_showcase",
    "run_continuous_achromatic_showcase",
]

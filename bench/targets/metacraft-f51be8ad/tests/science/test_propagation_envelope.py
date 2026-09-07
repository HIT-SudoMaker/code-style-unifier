from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, localcontext
import hashlib
import inspect

from metacraft.authority.reference import reference_for
import pytest

from metacraft.authority import Document, Reference
from tests.brief_fixtures import propagation_brief
from metacraft.science import compile_study
from metacraft.science.metalens import propagation_envelope
from metacraft.science.metalens.brief import MonochromaticSpectrum
from metacraft.science.metalens.material import MaterialBinding
from metacraft.science.metalens.propagation_envelope import (
    OpticalContrast,
    PhaseEnvelope,
    estimate_phase_envelope,
)
from metacraft.science.study import Study
from tests.derivations.phase_envelope import derive_documents
from tests.domain_fixtures import height_domain, material_binding


def _study(wavelength_nm: int = 940) -> Study:
    brief = propagation_brief()
    return compile_study(
        replace(
            brief,
            wording=(f"Review the propagation envelope at {wavelength_nm} nm."),
            operating_spectrum=MonochromaticSpectrum(wavelength_nm),
        )
    )


def _binding(study: Study) -> MaterialBinding:
    return material_binding(study)


def _golden_envelope(wavelength_nm: int) -> PhaseEnvelope:
    study = _study(wavelength_nm)
    binding_reference = _golden_reference("material-binding", wavelength_nm)
    sample_reference = _golden_reference("material-sample", wavelength_nm)
    domain_reference = _golden_reference("height-domain", wavelength_nm)
    domain = replace(
        height_domain(study),
        brief_identity=f"reviewed-propagation-{wavelength_nm}-nm",
        material_binding_reference=binding_reference,
        material_sample_reference=sample_reference,
        evidence_reference=domain_reference,
    )
    return estimate_phase_envelope(
        domain,
        OpticalContrast(
            atom_refractive_index=Decimal("2.05"),
            substrate_refractive_index=Decimal("1.48"),
            ambient_refractive_index=Decimal("1"),
            material_binding_reference=binding_reference,
            material_sample_reference=sample_reference,
        ),
    )


def _golden_reference(name: str, wavelength_nm: int) -> Reference:
    identity = f"{name}-{wavelength_nm}"
    return Reference(
        content_hash=_reference_hash(identity),
        media_type="application/json",
        metadata_content_hash=_reference_hash("metadata-" + identity),
        size_bytes=len(identity),
    )


def _reference_hash(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def test_phase_envelope_rules_only_from_arithmetic_or_bounds() -> None:
    """
    Permit hard exclusions only from arithmetic or certified bounds.
    """

    study = _study()
    binding = _binding(study)
    domain = height_domain(study)

    envelope = estimate_phase_envelope(
        domain,
        OpticalContrast.from_binding(binding),
    )

    height_500 = envelope.reach_for(500)
    assert height_500.grid.candidate_count == 39
    assert tuple(
        (standing.levels, standing.standing, standing.deciding_tier)
        for standing in height_500.standings
    ) == (
        (8, "ruled out", "bounded"),
        (12, "ruled out", "bounded"),
        (16, "ruled out", "bounded"),
    )
    checks = envelope.bound_checks
    assert checks.ceiling_reaches_pillar.expected_endpoint == Decimal("2.05")
    assert checks.ceiling_reaches_pillar.certified_interval == (
        Decimal("2.05"),
        Decimal("2.05"),
    )
    assert checks.floor_reaches_ambient.expected_endpoint == Decimal("1")
    assert checks.floor_reaches_ambient.certified_interval == (
        Decimal("1"),
        Decimal("1"),
    )
    assert checks.floor_stays_below_ceiling.minimum_certified_separation == Decimal(
        "1.05"
    )
    assert checks.authorizes_bounded_exclusion
    assert tuple(checks.as_mapping()) == (
        "ceiling_reaches_pillar",
        "floor_reaches_ambient",
        "floor_stays_below_ceiling",
    )
    assert envelope.source_references == (
        domain.evidence_reference,
        domain.material_binding_reference,
        domain.material_sample_reference,
    )
    assert all(
        standing.deciding_tier != "forecast"
        for reach in envelope.reaches
        for standing in reach.standings
    )
    assert "subprocess" not in inspect.getsource(propagation_envelope)
    assert "lumapi" not in inspect.getsource(propagation_envelope)


def test_phase_envelope_document_round_trips_exactly() -> None:
    """
    Preserve the phase-envelope evidence bytes across admission.
    """

    study = _study()
    binding = _binding(study)
    domain = height_domain(study)
    envelope = estimate_phase_envelope(
        domain,
        OpticalContrast.from_binding(binding),
    )
    reference = reference_for(envelope.document().to_bytes())

    restored = envelope.admitted(reference)

    assert restored.evidence_reference == reference
    assert restored.document().to_bytes() == envelope.document().to_bytes()


def test_height_reach_keeps_forecast_and_applicability_distinct() -> None:
    """
    Report model absence and applicability without inventing a verdict.
    """

    study = _study()
    binding = _binding(study)
    domain = height_domain(study)

    reach = estimate_phase_envelope(
        domain,
        OpticalContrast.from_binding(binding),
    ).reach_for(500)

    assert reach.forecast.model_spans == ()
    assert reach.forecast.steepest_adjacent_step_turns is None
    assert tuple(
        (budget.levels, budget.maximum_adjacent_step_turns)
        for budget in reach.forecast.level_budgets
    ) == (
        (8, Decimal("0.125")),
        (12, Decimal("0.08333333333333333333333333333")),
        (16, Decimal("0.0625")),
    )
    assert reach.forecast.as_mapping() == {
        "annotation": "forecast insufficient",
        "level_budgets": [
            {
                "levels": 8,
                "maximum_adjacent_step_turns": "0.125",
            },
            {
                "levels": 12,
                "maximum_adjacent_step_turns": ("0.08333333333333333333333333333"),
            },
            {
                "levels": 16,
                "maximum_adjacent_step_turns": "0.0625",
            },
        ],
        "model_spans": [],
    }
    assert reach.applicability.single_mode_cutoff_diameter_nm == Decimal("402.084184")
    assert reach.applicability.affected_candidate_count == 5
    assert reach.applicability.affected_candidate_fraction == Decimal(
        "0.1282051282051282051282051282"
    )
    assert reach.bounded_reasoning.ceiling_polarization == ("polarization independent")


@pytest.mark.parametrize("wavelength_nm", (940, 1550))
def test_phase_envelope_matches_reviewed_bytes(
    wavelength_nm: int,
) -> None:
    """
    Keep the public document equal to independently reviewed bytes.
    """

    assert _golden_envelope(wavelength_nm).document().to_bytes() == (
        derive_documents()[wavelength_nm]
    )


def test_uncertified_check_cannot_authorize_a_bounded_standing() -> None:
    """
    Reject admitted bytes that claim a bound after its support is removed.
    """

    study = _study()
    binding = _binding(study)
    domain = height_domain(study)
    contrast = OpticalContrast(
        atom_refractive_index=Decimal("1.10"),
        substrate_refractive_index=Decimal("1.48"),
        ambient_refractive_index=Decimal("1"),
        material_binding_reference=binding.evidence_reference,
        material_sample_reference=binding.sample_reference,
    )
    envelope = estimate_phase_envelope(domain, contrast)
    assert any(
        standing.deciding_tier == "bounded"
        for reach in envelope.reaches
        for standing in reach.standings
    )
    values = deepcopy(dict(envelope.document().values))
    checks = values["bound_checks"]
    assert isinstance(checks, dict)
    ceiling = checks["ceiling_reaches_pillar"]
    assert isinstance(ceiling, dict)
    ceiling["certified"] = False
    document = Document(
        envelope.document().schema_identifier,
        values,
    )

    with pytest.raises(
        ValueError,
        match="phase_envelope_uncertified_bounded_exclusion",
    ):
        type(envelope).from_document(
            document,
            evidence_reference=reference_for(document.to_bytes()),
        )


def test_phase_envelope_owns_its_decimal_precision() -> None:
    """
    Keep canonical evidence independent of a caller's Decimal context.
    """

    with localcontext() as context:
        context.prec = 12
        observed = _golden_envelope(940).document().to_bytes()

    assert observed == derive_documents()[940]

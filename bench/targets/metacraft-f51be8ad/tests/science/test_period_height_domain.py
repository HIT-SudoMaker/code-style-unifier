from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from tests.brief_fixtures import geometric_brief, propagation_brief
from metacraft.authority import Authority, Document
from metacraft.authority.reference import reference_for
from metacraft.authority.session import AuthoritySession
from metacraft.science import (
    Binding,
    Capability,
    Finding,
    FindingKind,
    InvalidBrief,
    Study,
    compile_study,
)
from metacraft.science.consultation import (
    ConsultationAnswer,
    EvidenceRequired,
    Recommendation,
    ResearchMode,
)
from metacraft.science.metalens.consultation import (
    accept_period_consultation_answer,
    form_period_consultation_request,
)
from metacraft.science.metalens.brief import MonochromaticSpectrum
from metacraft.science.metalens.design import require_metalens_design
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.checkpoint import StudyFrontier
from metacraft.science.metalens.evidence import MetalensEvidence
from metacraft.science.metalens.height import (
    derive_height_domain,
)
from metacraft.science.metalens.height_advice import HeightAdvice
from metacraft.science.metalens.period import (
    PeriodAdviceBasis,
    PeriodConstraintBasis,
    PeriodChoice,
    PeriodDomain,
    derive_period_domain,
    resolve_period_choice,
    validate_period_value,
)
from metacraft.science.metalens.period_advice import (
    PeriodAdvice,
    PeriodRecommendation,
)
from examples import select_metalens_benchmark_case

from tests.domain_fixtures import (
    compile_with_facts,
    height_domain as admitted_height_domain,
    height_evidence_required as fixture_height_evidence_required,
    material_binding,
    period_domain as admitted_period_domain,
    period_choice as admitted_period_choice,
    period_advice as fixture_period_advice,
    phase_envelope as admitted_phase_envelope,
)


def _material_capabilities() -> tuple[Capability, ...]:
    return (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("deterministic_selection"),
    )


def _material_bindings() -> tuple[Binding, ...]:
    return (
        Binding("optical_material", reference_for(b"material solver")),
        Binding(
            "fabrication_constraint",
            reference_for(b"fabrication"),
        ),
        Binding(
            "deterministic_selection",
            reference_for(b"selection"),
        ),
    )


def test_grid_aligned_sampling_ceiling_leaves_one_strict_period_step() -> None:
    """
    Keep the physical ceiling exact and the selected period strictly below it.
    """

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
        cell_period_nm=840,
        dimension_step_nm=10,
    )
    study = compile_study(brief)
    domain = admitted_period_domain(study, substrate_index="1.7")
    choice = admitted_period_choice(study, substrate_index="1.7")

    assert not hasattr(
        require_metalens_design(study),
        "cell_period_nm",
    )
    assert domain.order_ceiling_nm == Decimal("850")
    assert domain.period_limit_nm == 2830
    assert choice.period_nm == 840
    assert choice.basis == PeriodConstraintBasis()


def test_exact_grid_sampling_ceiling_yields_one_strict_period_step_below() -> None:
    """
    An exact 1700 nm sampling ceiling yields a maximum period of 1690 nm.

    The same case retains its exact 850 nm order ceiling as proof context.
    """

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.5"),
    )
    study = compile_study(brief)
    binding = material_binding(study, substrate_index="1.5")

    domain = derive_period_domain(study, binding)

    assert domain.sampling_ceiling_nm == Decimal("1700")
    assert domain.order_ceiling_nm == Decimal("850")
    assert domain.period_limit_nm == 1690


def test_non_grid_sampling_ceiling_keeps_the_largest_10nm_step_below() -> None:
    """
    A non-grid 2125 nm sampling ceiling keeps the 2120 nm grid step.
    """

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.4"),
    )
    study = compile_study(brief)
    binding = material_binding(study, substrate_index="1.46")

    domain = derive_period_domain(study, binding)

    assert domain.sampling_ceiling_nm == Decimal("2125")
    assert domain.order_ceiling_nm < domain.sampling_ceiling_nm
    assert domain.period_limit_nm % 10 == 0
    assert domain.period_limit_nm == 2120
    assert Decimal(domain.period_limit_nm) < domain.sampling_ceiling_nm


def test_period_domain_grid_is_independent_of_dimension_step() -> None:
    """
    The fixed 10 nm period grid does not move when the brief changes its
    lateral dimension step; that step enters only the height domain's
    candidate arithmetic.
    """

    base = propagation_brief()
    for dimension_step_nm in (10, 20, 50, 100):
        brief = replace(base, dimension_step_nm=dimension_step_nm)
        study = compile_study(brief)
        binding = material_binding(study)
        domain = derive_period_domain(study, binding)
        assert domain.period_limit_nm == 660
        assert domain.period_limit_nm % 10 == 0


def test_sampling_ceiling_equality_is_rejected_by_sampling() -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.5"),
    )
    study = compile_study(brief)
    domain = admitted_period_domain(study, substrate_index="1.5")

    with pytest.raises(
        ValueError,
        match="^cell_period_at_or_above_sampling_ceiling$",
    ):
        validate_period_value(1_700, domain)


def test_sampling_legal_advice_retains_multi_order_classification_and_caution() -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    advice = fixture_period_advice(initial, domain, period_nm=1_600)
    study, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    choice = resolve_period_choice(study, domain, period_advice=advice)

    assert isinstance(choice, PeriodChoice)
    assert choice.period_nm == 1_600
    assert choice.order_regime == "multi order"
    assert tuple(caution.concern for caution in choice.cautions) == (
        "higher orders possible",
    )


def test_material_evidence_requests_period_before_height_domain() -> None:
    """
    Ask for one period only after the exact material evidence is present.
    """

    brief = propagation_brief()
    study, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": reference_for(b"material"),
            "period_domain": reference_for(b"period-domain"),
        },
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    assert not any(task.claim == "period_choice" for task in study.ready_tasks)
    assert any(
        finding.claim == "period_choice"
        and finding.kind is FindingKind.ADVICE
        and finding.needs == ("period",)
        for finding in study.findings
    )


def test_period_advice_cites_one_exact_domain_without_copying_its_facts() -> None:
    """
    Keep consultation provenance while the period domain remains sole owner.
    """

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    study = compile_study(brief)
    binding = material_binding(study, substrate_index="1.7")
    domain = admitted_period_domain(study, substrate_index="1.7")

    request = form_period_consultation_request(
        brief,
        domain,
        research_mode=ResearchMode.CLOSED_BOOK,
    )
    candidate = next(
        item for item in request.candidates if item.quantity == Decimal(840)
    )
    advice = accept_period_consultation_answer(
        brief,
        domain,
        request,
        ConsultationAnswer(
            request_identity=request.identity,
            conclusion=Recommendation(
                candidate_identity=candidate.identity,
                reason="Leave a strict G0 margin.",
                decisive_ground_identities=(request.grounds[-1].identity,),
                external_claim_identities=(),
            ),
            external_claims=(),
        ),
    )

    assert isinstance(advice, PeriodAdvice)
    assert advice.domain_reference == domain.evidence_reference
    assert isinstance(advice.conclusion, PeriodRecommendation)
    assert advice.conclusion.period_nm == 840
    assert {
        "material_binding_reference",
        "sampling_ceiling_nm",
        "order_ceiling_nm",
        "period_limit_nm",
    }.isdisjoint(advice.document().values)
    assert PeriodAdvice.from_document(advice.document()) == advice


def test_period_choice_accepts_period_advice_without_repair() -> None:
    """
    Form the choice from the exact advised period and its exclusive basis.
    """

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    advice = _period_advice(initial, material, period_nm=840)
    advice_reference = reference_for(advice.document().to_bytes())
    domain = admitted_period_domain(initial, substrate_index="1.7")
    study, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    choice = resolve_period_choice(
        study,
        domain,
        period_advice=advice,
    )

    assert choice.period_nm == 840
    assert choice.basis == PeriodAdviceBasis(advice_reference)


def test_period_choice_returns_typed_advice_finding_outside_domain() -> None:
    """Keep an untrusted out-of-domain proposal as an expected outcome."""

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    advice = _period_advice(initial, material, period_nm=2_840)
    study, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    outcome = resolve_period_choice(
        study,
        domain,
        period_advice=advice,
    )

    assert outcome.claim == "period_choice"
    assert outcome.kind is FindingKind.ADVICE
    assert outcome.needs == ("period_advice_outside_domain",)
    assert outcome.record_references == (reference_for(advice.document().to_bytes()),)


def test_period_replay_rejects_advice_outside_the_current_candidates(
    tmp_path: Path,
) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    advice = _period_advice(initial, material, period_nm=2_840)
    grounded, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    finding = resolve_period_choice(
        grounded,
        domain,
        period_advice=advice,
    )
    assert isinstance(finding, Finding)
    session = AuthoritySession(Authority(tmp_path / "authority"))
    assert session.admit_document(domain.document()) == domain.evidence_reference
    assert session.admit_document(advice.document()) == reference_for(
        advice.document().to_bytes()
    )
    with pytest.raises(ValueError, match="^period_advice_replay_mismatch$"):
        MetalensEvidence(session).with_finding(grounded, finding)


def test_valid_period_advice_binds_the_period_choice_task() -> None:
    """
    Make exactly the advised period available to the period-choice operation.
    """

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    advice = _period_advice(initial, material, period_nm=840)
    advice_reference = reference_for(advice.document().to_bytes())

    domain = admitted_period_domain(initial, substrate_index="1.7")
    study, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    task = next(task for task in study.ready_tasks if task.claim == "period_choice")
    assert task.consultations == (advice_reference,)


def test_period_advice_is_unique_and_cannot_be_replaced_by_height_advice() -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    period_advice = _period_advice(initial, material, period_nm=840)

    with pytest.raises(ValueError, match="period_advice_duplicate"):
        compile_metalens(brief, advice=(period_advice, period_advice))

    height_ground = admitted_height_domain(initial, substrate_index="1.7")
    envelope = admitted_phase_envelope(
        initial,
        height_ground,
        substrate_index="1.7",
    )
    height_advice = fixture_height_evidence_required(
        brief,
        height_ground,
        envelope=envelope,
    )
    with pytest.raises(ValueError, match="period_advice_type_invalid"):
        grounded, _facts = compile_with_facts(
            brief,
            references={
                "target_phase": reference_for(b"phase"),
                "material_binding": material.evidence_reference,
                "period_domain": domain.evidence_reference,
            },
            capabilities=_material_capabilities(),
            bindings=_material_bindings(),
        )
        resolve_period_choice(
            grounded,
            domain,
            period_advice=height_advice,  # type: ignore[arg-type]
        )


def test_period_domain_rejects_an_on_grid_recommendation_above_its_limit() -> None:
    """
    Consultation syntax may be valid, but only the cited domain admits value.
    """

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    advice = _period_advice(initial, material, period_nm=2_840)
    study, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    assert any(task.claim == "period_choice" for task in study.ready_tasks)
    outcome = resolve_period_choice(
        study,
        domain,
        period_advice=advice,
    )

    assert outcome.kind is FindingKind.ADVICE
    assert outcome.needs == ("period_advice_outside_domain",)


def test_off_grid_period_advice_waits_without_repair() -> None:
    """
    Keep an invalid proposal visible instead of rounding it into a choice.
    """

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    advice = _period_advice(initial, material, period_nm=839)
    advice_reference = reference_for(advice.document().to_bytes())
    domain = admitted_period_domain(initial, substrate_index="1.7")

    study, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    outcome = resolve_period_choice(
        study,
        domain,
        period_advice=advice,
    )

    assert outcome.kind is FindingKind.ADVICE
    assert outcome.needs == ("period_advice_off_grid",)
    assert outcome.record_references == (advice_reference,)


@pytest.mark.parametrize("period_nm", [0, -10])
def test_nonpositive_period_advice_cannot_become_a_choice(
    period_nm: int,
) -> None:
    """
    Reject untrusted document advice before it can form a period choice.
    """

    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    received = _period_advice(initial, material, period_nm=840)
    values = dict(received.document().values)
    conclusion = dict(values["conclusion"])
    conclusion["period_nm"] = period_nm
    values["conclusion"] = conclusion

    with pytest.raises(ValueError, match="period_advice_invalid"):
        PeriodAdvice.from_document(
            Document(received.document().schema_identifier, values)
        )


@pytest.mark.parametrize(
    ("invalid_field", "expected_error"),
    (
        ("brief_identity", "period_advice_brief_mismatch"),
        ("domain_reference", "period_advice_domain_mismatch"),
    ),
)
@pytest.mark.parametrize("is_evidence_required", (False, True))
def test_compiler_rejects_period_advice_with_stale_grounds(
    invalid_field: str,
    expected_error: str,
    is_evidence_required: bool,
) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    advice = _period_advice(initial, material, period_nm=840)
    if is_evidence_required:
        advice = replace(
            advice,
            conclusion=EvidenceRequired(
                missing_fact="fabrication tolerance",
                reason="A conservative period cannot yet be justified.",
            ),
        )
    invalid = (
        replace(advice, brief_identity="sha256:stale-brief")
        if invalid_field == "brief_identity"
        else replace(
            advice,
            domain_reference=reference_for(b"stale period domain"),
        )
    )

    with pytest.raises(ValueError, match=f"^{expected_error}$"):
        compile_with_facts(
            brief,
            references={
                "target_phase": reference_for(b"phase"),
                "material_binding": material.evidence_reference,
                "period_domain": domain.evidence_reference,
            },
            advice=(invalid,),
            capabilities=_material_capabilities(),
            bindings=_material_bindings(),
        )


def test_frontier_rejects_unavailable_period_advice_with_a_stale_domain(
    tmp_path: Path,
) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    unavailable = replace(
        _period_advice(initial, material, period_nm=840),
        conclusion=EvidenceRequired(
            missing_fact="fabrication tolerance",
            reason="A conservative period cannot yet be justified.",
        ),
    )
    compiled, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(unavailable,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    stale = replace(
        unavailable,
        domain_reference=reference_for(b"stale period domain"),
    )
    forged = replace(
        compiled,
        advice=tuple(
            stale if isinstance(item, PeriodAdvice) else item
            for item in compiled.advice
        ),
        findings=tuple(
            (
                replace(
                    finding,
                    record_references=(reference_for(stale.document().to_bytes()),),
                )
                if finding.claim == "period_choice"
                else finding
            )
            for finding in compiled.findings
        ),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    assert session.admit_document(domain.document()) == domain.evidence_reference
    assert session.admit_document(stale.document()) == reference_for(
        stale.document().to_bytes()
    )

    with pytest.raises(ValueError, match="^study_frontier_invalid$"):
        StudyFrontier.from_document(
            StudyFrontier.start(forged).document(),
            brief=brief,
            session=session,
        )


@pytest.mark.parametrize(
    ("period_nm", "expected_need"),
    (
        (None, "period_evidence_required"),
        (839, "period_advice_off_grid"),
    ),
)
def test_received_period_findings_require_their_bound_consultation(
    period_nm: int | None,
    expected_need: str,
) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    received = _period_advice(initial, material, period_nm=840)
    conclusion = (
        EvidenceRequired(
            missing_fact="fabrication tolerance",
            reason="A conservative period cannot yet be justified.",
        )
        if period_nm is None
        else replace(received.conclusion, period_nm=period_nm)
    )
    candidate = replace(received, conclusion=conclusion)
    study_bound_to_received, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(received,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    if period_nm is None:
        unbound = resolve_period_choice(
            study_bound_to_received,
            domain,
            period_advice=candidate,
        )
        assert isinstance(unbound, Finding)
        assert unbound.needs == ("period_evidence_required",)
    else:
        with pytest.raises(ValueError, match="^period_advice_not_bound$"):
            resolve_period_choice(
                study_bound_to_received,
                domain,
                period_advice=candidate,
            )

    study_bound_to_candidate, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(candidate,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    outcome = resolve_period_choice(
        study_bound_to_candidate,
        domain,
        period_advice=candidate,
    )

    assert isinstance(outcome, Finding)
    assert outcome.kind is FindingKind.ADVICE
    assert outcome.needs == (expected_need,)
    assert outcome.record_references == (
        reference_for(candidate.document().to_bytes()),
    )


def test_height_domain_derives_from_the_admitted_period_choice() -> None:
    """
    Height domain carries the period value only from the admitted choice and
    keeps no independent period authority.
    """

    brief = replace(propagation_brief(), cell_period_nm=200)
    initial = compile_study(brief)
    binding = material_binding(initial)
    period_domain = admitted_period_domain(initial)
    before_choice, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": binding.evidence_reference,
            "period_domain": period_domain.evidence_reference,
        },
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    provisional = resolve_period_choice(before_choice, period_domain)
    choice = provisional.bind_evidence(reference_for(provisional.document().to_bytes()))
    study, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": binding.evidence_reference,
            "period_domain": period_domain.evidence_reference,
            "period_choice": choice.evidence_reference,
        },
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    domain = derive_height_domain(study, choice, binding)
    assert domain.period_nm == choice.period_nm
    assert domain.period_choice_reference == choice.evidence_reference
    assert "period_basis" not in domain.document().values

    foreign = replace(
        choice,
        reason="foreign choice",
        evidence_reference=None,
    )
    foreign = foreign.bind_evidence(reference_for(foreign.document().to_bytes()))
    with pytest.raises(ValueError, match="period_choice_not_admitted"):
        derive_height_domain(study, foreign, binding)


def test_square_aperture_keeps_its_explicit_span_through_height_compile() -> None:
    """
    Square site count defines a footprint; it is not a circular NA radius.
    """

    brief = replace(
        select_metalens_benchmark_case("yang-2018-low-na-geometric").brief,
        cell_period_nm=800,
    )

    domain = admitted_height_domain(compile_study(brief))

    assert brief.aperture is not None
    assert brief.aperture.site_count == 15
    assert domain.period_nm == 800


def test_standard_wavelengths_keep_their_finite_height_priors() -> None:
    """
    Keep the visible and infrared priors explicit and route independent.
    """

    cases = (
        (
            replace(
                geometric_brief(),
                operating_spectrum=MonochromaticSpectrum(532),
                dimension_step_nm=20,
            ),
            (500, 550, 600, 650, 700, 750, 800),
        ),
        (
            replace(
                propagation_brief(),
                operating_spectrum=MonochromaticSpectrum(940),
            ),
            (500, 550),
        ),
        (
            replace(
                propagation_brief(),
                operating_spectrum=MonochromaticSpectrum(1_550),
            ),
            (800, 850, 900),
        ),
        (
            replace(
                geometric_brief(),
                operating_spectrum=MonochromaticSpectrum(1_550),
                dimension_step_nm=100,
            ),
            (800, 850, 900),
        ),
    )

    for brief, expected in cases:
        domain = admitted_height_domain(compile_study(brief))
        assert domain.heights_nm == expected


def test_candidate_minimum_depends_on_the_compiled_route() -> None:
    """
    Require sixteen propagation dimensions but only two geometric axes.
    """

    propagation = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
        dimension_step_nm=100,
    )
    geometric = replace(
        geometric_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
        dimension_step_nm=100,
    )

    assert admitted_height_domain(compile_study(propagation)).heights_nm == ()
    assert admitted_height_domain(compile_study(geometric)).heights_nm == (500, 550)


def test_generated_geometry_requires_a_dimension_step() -> None:
    """
    Request fabrication resolution from the brief instead of inventing it.
    """

    outcome = compile_study(replace(propagation_brief(), dimension_step_nm=None))

    assert isinstance(outcome, InvalidBrief)
    assert "dimension_step_nm" in outcome.reason


def test_reported_period_advice_rejects_an_open_ended_need() -> None:
    brief = propagation_brief()
    study = compile_study(brief)
    binding = material_binding(study)
    advice = _period_advice(study, binding, period_nm=840)

    with pytest.raises(ValueError, match="^reported_finding_invalid$"):
        compile_metalens(
            brief,
            advice=(advice,),
            reported_findings=(
                Finding(
                    claim="period_choice",
                    kind=FindingKind.ADVICE,
                    needs=("period_advice_external_failure",),
                    record_references=(reference_for(advice.document().to_bytes()),),
                ),
            ),
        )


def test_reported_period_advice_rejects_a_stale_record_reference() -> None:
    brief = propagation_brief()
    study = compile_study(brief)
    binding = material_binding(study)
    advice = _period_advice(study, binding, period_nm=840)

    with pytest.raises(ValueError, match="^reported_finding_invalid$"):
        compile_metalens(
            brief,
            advice=(advice,),
            reported_findings=(
                Finding(
                    claim="period_choice",
                    kind=FindingKind.ADVICE,
                    needs=("period_advice_outside_domain",),
                    record_references=(reference_for(b"stale advice"),),
                ),
            ),
        )


def test_domain_rejects_a_forged_outside_finding_for_an_inside_period() -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    advice = _period_advice(initial, material, period_nm=840)
    grounded, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )

    with pytest.raises(ValueError, match="^reported_finding_invalid$"):
        compile_metalens(
            brief,
            advice=(advice,),
            evidence=grounded.evidence,
            capabilities=grounded.capabilities,
            bindings=grounded.bindings,
            reported_findings=(
                Finding(
                    claim="period_choice",
                    kind=FindingKind.ADVICE,
                    needs=("period_advice_outside_domain",),
                    record_references=(reference_for(advice.document().to_bytes()),),
                ),
            ),
        )


@pytest.mark.parametrize(
    "claim",
    ("period_choice", "height_domain", "height_choice"),
)
def test_compiler_rejects_domain_owned_refusals(claim: str) -> None:
    with pytest.raises(ValueError, match="^reported_finding_invalid$"):
        compile_metalens(
            propagation_brief(),
            reported_findings=(
                Finding(
                    claim=claim,
                    kind=FindingKind.REFUSAL,
                    needs=("forged_domain_refusal",),
                ),
            ),
        )


@pytest.mark.parametrize(
    "claim",
    ("period_choice", "height_domain", "height_choice"),
)
def test_compiler_rejects_domain_owned_capability_findings(
    claim: str,
) -> None:
    with pytest.raises(ValueError, match="^reported_finding_invalid$"):
        compile_metalens(
            propagation_brief(),
            reported_findings=(
                Finding(
                    claim=claim,
                    kind=FindingKind.CAPABILITY,
                    needs=("forged_capability",),
                    record_references=(reference_for(b"forged capability"),),
                ),
            ),
        )


def test_compiler_rejects_domain_owned_incomplete_finding() -> None:
    with pytest.raises(ValueError, match="^reported_finding_invalid$"):
        compile_metalens(
            propagation_brief(),
            reported_findings=(
                Finding(
                    claim="height_choice",
                    kind=FindingKind.INCOMPLETE,
                    needs=("focus_incomplete",),
                    record_references=(reference_for(b"forged survey"),),
                ),
            ),
        )


def test_evidence_recompile_drops_a_domain_owned_capability_finding(
    tmp_path: Path,
) -> None:
    compiled = compile_metalens(propagation_brief())
    forged_finding = Finding(
        claim="height_domain",
        kind=FindingKind.CAPABILITY,
        needs=("forged_capability",),
        record_references=(reference_for(b"forged capability"),),
    )
    forged = replace(
        compiled,
        findings=tuple(
            forged_finding if finding.claim == "height_domain" else finding
            for finding in compiled.findings
        ),
    )

    restored = MetalensEvidence(
        AuthoritySession(Authority(tmp_path / "authority"))
    ).recompile(forged)

    assert forged_finding not in restored.findings
    assert restored == compiled


def test_frontier_restore_rejects_a_domain_owned_capability_finding(
    tmp_path: Path,
) -> None:
    brief = propagation_brief()
    compiled = compile_metalens(brief)
    forged_finding = Finding(
        claim="period_choice",
        kind=FindingKind.CAPABILITY,
        needs=("forged_capability",),
        record_references=(reference_for(b"forged capability"),),
    )
    forged = replace(
        compiled,
        findings=tuple(
            forged_finding if finding.claim == "period_choice" else finding
            for finding in compiled.findings
        ),
    )

    with pytest.raises(ValueError, match="^study_frontier_invalid$"):
        StudyFrontier.from_document(
            StudyFrontier.start(forged).document(),
            brief=brief,
            session=AuthoritySession(Authority(tmp_path / "authority")),
        )


def test_period_owner_rejects_a_forged_refusal(tmp_path: Path) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    initial = compile_study(brief)
    material = material_binding(initial, substrate_index="1.7")
    domain = admitted_period_domain(initial, substrate_index="1.7")
    advice = _period_advice(initial, material, period_nm=840)
    grounded, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    assert session.admit_document(domain.document()) == domain.evidence_reference
    assert session.admit_document(advice.document()) == reference_for(
        advice.document().to_bytes()
    )

    with pytest.raises(ValueError, match="^reported_finding_invalid$"):
        MetalensEvidence(session).with_finding(
            grounded,
            Finding(
                claim="period_choice",
                kind=FindingKind.REFUSAL,
                needs=("forged_domain_refusal",),
            ),
        )


def test_height_domain_owner_rejects_a_forged_refusal(
    tmp_path: Path,
) -> None:
    brief = replace(propagation_brief(), cell_period_nm=200)
    initial = compile_study(brief)
    solver_body = b'"fixture solver"'
    sample_body = b'"fixture material sample"'
    binding = replace(
        material_binding(initial),
        solver_binding_reference=reference_for(solver_body),
        sample_reference=reference_for(sample_body),
    )
    binding = replace(
        binding,
        evidence_reference=reference_for(binding.document().to_bytes()),
    )
    domain = derive_period_domain(initial, binding)
    domain = domain.bind_evidence(reference_for(domain.document().to_bytes()))
    before_choice, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": binding.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    choice = resolve_period_choice(before_choice, domain)
    assert isinstance(choice, PeriodChoice)
    choice = choice.bind_evidence(reference_for(choice.document().to_bytes()))
    grounded, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": binding.evidence_reference,
            "period_domain": domain.evidence_reference,
            "period_choice": choice.evidence_reference,
        },
        capabilities=_material_capabilities(),
        bindings=_material_bindings(),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    assert (
        session.admit_object(
            solver_body,
            media_type="application/json",
            descriptive_metadata={},
        )
        == binding.solver_binding_reference
    )
    assert (
        session.admit_object(
            sample_body,
            media_type="application/json",
            descriptive_metadata={},
        )
        == binding.sample_reference
    )
    assert session.admit_document(binding.document()) == binding.evidence_reference
    assert session.admit_document(choice.document()) == choice.evidence_reference

    with pytest.raises(ValueError, match="^reported_finding_invalid$"):
        MetalensEvidence(session).with_finding(
            grounded,
            Finding(
                claim="height_domain",
                kind=FindingKind.REFUSAL,
                needs=("forged_domain_refusal",),
            ),
        )


def _period_advice(study, binding, *, period_nm: int) -> PeriodAdvice:
    provisional = derive_period_domain(study, binding)
    domain = provisional.bind_evidence(reference_for(provisional.document().to_bytes()))
    valid = fixture_period_advice(
        study,
        domain,
        period_nm=domain.period_limit_nm,
    )
    if period_nm == domain.period_limit_nm:
        return valid
    conclusion = valid.conclusion
    assert isinstance(conclusion, PeriodRecommendation)
    return replace(
        valid,
        conclusion=replace(conclusion, period_nm=period_nm),
    )

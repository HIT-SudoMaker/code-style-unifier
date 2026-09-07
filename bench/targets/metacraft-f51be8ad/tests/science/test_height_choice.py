from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from metacraft.authority import (
    Authority,
    Document,
    Proposal,
    Reference,
    Structure,
    reference_for,
)
from metacraft.authority.session import AuthoritySession
from tests.brief_fixtures import geometric_brief, propagation_brief
from metacraft.science.metalens.checkpoint import StudyFrontier
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.evidence import MetalensEvidence
from metacraft.science.metalens.height import (
    HeightAdviceBasis,
    HEIGHT_CHOICE_SCHEMA,
    HeightChoice,
    HeightDomain,
    resolve_height_choice,
    validate_height_choice,
)
from metacraft.science.metalens.height_advice import HeightAdvice
from metacraft.science.metalens.height_advice import HeightRecommendation
from metacraft.science.consultation import EvidenceRequired
from metacraft.science.metalens.period import PeriodChoice
from metacraft.science.metalens.period_advice import PeriodAdvice
from metacraft.science.metalens.brief import MetalensBrief, MonochromaticSpectrum
from metacraft.science.study import (
    Binding,
    Capability,
    Evidence,
    Finding,
    FindingKind,
    Study,
)
from metacraft.science.metalens.propagation_envelope import PhaseEnvelope
from tests.domain_fixtures import (
    compile_with_facts,
    height_advice as fixture_height_advice,
    height_domain,
    height_evidence_required as fixture_height_evidence_required,
    material_binding,
    period_domain,
    period_choice,
    period_advice as fixture_period_advice,
    phase_envelope,
)


def _reference_hash(name: str) -> str:
    return f"sha256:{hashlib.sha256(name.encode()).hexdigest()}"


def _reference(name: str) -> Reference:
    return Reference(
        content_hash=_reference_hash(name),
        media_type="application/json",
        metadata_content_hash=_reference_hash("metadata-" + name),
        size_bytes=len(name),
    )


def _identity(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _viable_brief() -> MetalensBrief:
    """
    Use an infrared tracer with enough legal dimensions for phase matching.
    """

    return replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(wavelength_nm=940),
    )


def _domain(brief: MetalensBrief) -> HeightDomain:
    return height_domain(compile_metalens(brief), atom_index="3.5")


def _envelope(
    brief: MetalensBrief,
    domain: HeightDomain,
) -> PhaseEnvelope:
    return phase_envelope(
        compile_metalens(brief),
        domain,
        atom_index="3.5",
    )


def _advice(
    brief: MetalensBrief,
    domain: HeightDomain,
    height: int,
    envelope: PhaseEnvelope,
) -> HeightAdvice:
    return fixture_height_advice(
        brief,
        domain,
        height_nm=height,
        envelope=envelope,
    )


def _period_advice_for(
    brief: MetalensBrief,
) -> PeriodAdvice:
    """
    Rebuild the period-advice consultation the shared height-domain fixture
    used internally. Keeping this inline lets the study cite the same
    consultation while assembling content-addressed evidence for the new
    task-identity system, without touching the shared fixture helper.
    """

    base = compile_metalens(brief)
    domain = period_domain(base, atom_index="3.5")
    limit = domain.period_limit_nm
    return fixture_period_advice(base, domain, period_nm=limit)


def _study(
    brief: MetalensBrief,
    domain: HeightDomain,
    envelope: PhaseEnvelope,
    advice: HeightAdvice,
    *,
    findings: tuple[Finding, ...] = (),
) -> Study:
    period_advice = _period_advice_for(brief)
    capabilities = (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("deterministic_selection"),
    )
    bindings = (
        Binding("optical_material", _reference("optical-binding")),
        Binding(
            "fabrication_constraint",
            _reference("fabrication-binding"),
        ),
        Binding(
            "deterministic_selection",
            _reference("selection-binding"),
        ),
    )
    base = compile_metalens(brief)
    material = material_binding(base, atom_index="3.5")
    pdomain = period_domain(base, atom_index="3.5")
    pchoice = period_choice(base, atom_index="3.5")
    references = {
        "target_phase": _reference("target"),
        "material_binding": material.evidence_reference,
        "period_domain": pdomain.evidence_reference,
        "period_choice": pchoice.evidence_reference,
        "height_domain": domain.evidence_reference,
        "phase_envelope": envelope.evidence_reference,
    }
    _interim, facts = compile_with_facts(
        brief,
        references,
        advice=(period_advice, advice),
        capabilities=capabilities,
        bindings=bindings,
    )
    return compile_metalens(
        brief,
        advice=(period_advice, advice),
        evidence=tuple(facts.values()),
        capabilities=capabilities,
        bindings=bindings,
        reported_findings=findings,
    )


def _admit_height_choice_context(
    session: AuthoritySession,
    study: Study,
    domain: HeightDomain,
    envelope: PhaseEnvelope,
    advice: HeightAdvice,
) -> None:
    pdomain = period_domain(compile_metalens(study.brief), atom_index="3.5")
    for value in (pdomain, domain, envelope, *study.advice, advice):
        expected = reference_for(value.document().to_bytes())
        assert session.admit_document(value.document()) == expected


def _geometric_study(
    brief: MetalensBrief,
    domain: HeightDomain,
    advice: HeightAdvice,
) -> Study:
    base = compile_metalens(brief)
    material = material_binding(base)
    pdomain = period_domain(base)
    pchoice = period_choice(base)
    study, _facts = compile_with_facts(
        brief,
        {
            "target_phase": _reference("target"),
            "material_binding": material.evidence_reference,
            "period_domain": pdomain.evidence_reference,
            "period_choice": pchoice.evidence_reference,
            "height_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=(
            Capability("optical_material"),
            Capability("fabrication_constraint"),
            Capability("deterministic_selection"),
        ),
        bindings=(
            Binding("optical_material", _reference("optical-binding")),
            Binding(
                "fabrication_constraint",
                _reference("fabrication-binding"),
            ),
            Binding(
                "deterministic_selection",
                _reference("selection-binding"),
            ),
        ),
    )
    return study


def _rule_out_height(
    envelope: PhaseEnvelope,
    height_nm: int,
) -> PhaseEnvelope:
    provisional = replace(
        envelope,
        reaches=tuple(
            (
                replace(
                    reach,
                    standings=tuple(
                        replace(
                            standing,
                            standing="ruled out",
                            reason="fixture exclusion",
                        )
                        for standing in reach.standings
                    ),
                )
                if reach.height_nm == height_nm
                else reach
            )
            for reach in envelope.reaches
        ),
        evidence_reference=None,
    )
    return provisional.admitted(reference_for(provisional.document().to_bytes()))


def test_advice_selects_one_height_without_solver_observations() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    advice = _advice(brief, domain, 500, envelope)
    advice_reference = reference_for(advice.document().to_bytes())
    study = _study(brief, domain, envelope, advice)

    choice = resolve_height_choice(
        study,
        domain,
        advice,
        envelope=envelope,
    )

    assert choice.height_nm == 500
    assert choice.period_nm == 520
    assert choice.order_regime == "zeroth order"
    assert choice.minimum_feature_nm == 70
    assert choice.maximum_feature_nm == 450
    assert choice.dimension_step_nm == 10
    assert choice.cautions == ()
    assert choice.domain_reference == domain.evidence_reference
    assert choice.basis == HeightAdviceBasis(advice_reference)
    assert choice.references() == (
        domain.evidence_reference,
        advice_reference,
    )
    document = choice.document().to_bytes().decode("utf-8")
    assert "survey" not in document


def test_height_advice_is_unique_and_cannot_be_replaced_by_period_advice() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    height_advice = _advice(brief, domain, 500, envelope)

    with pytest.raises(ValueError, match="height_advice_duplicate"):
        compile_metalens(brief, advice=(height_advice, height_advice))

    period_advice = _period_advice_for(brief)
    with pytest.raises(ValueError, match="height_advice_type_invalid"):
        resolve_height_choice(
            _study(brief, domain, envelope, height_advice),
            domain,
            period_advice,  # type: ignore[arg-type]
            envelope=envelope,
        )


def test_height_choice_document_round_trips_exactly() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    advice = _advice(brief, domain, 500, envelope)
    choice = resolve_height_choice(
        _study(brief, domain, envelope, advice),
        domain,
        advice,
        envelope=envelope,
    )

    assert HeightChoice.from_document(choice.document()) == choice


def test_height_choice_document_rejects_the_wrong_schema() -> None:
    wrong = Document("fixture.height_choice", {})

    with pytest.raises(ValueError, match="height_choice_schema_mismatch"):
        HeightChoice.from_document(wrong)


def test_evidence_required_height_advice_remains_an_honest_wait() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    advice = fixture_height_evidence_required(
        brief,
        domain,
        envelope=envelope,
    )
    study = _study(brief, domain, envelope, advice)
    finding = resolve_height_choice(
        study,
        domain,
        advice,
        envelope=envelope,
    )
    assert isinstance(finding, Finding)
    assert finding.needs == ("height_evidence_required",)
    assert finding in study.findings
    assert all(task.claim != "height_choice" for task in study.ready_tasks)


def test_propagation_height_advice_rejects_a_stale_envelope_before_outcome() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    legal = fixture_height_evidence_required(
        brief,
        domain,
        envelope=envelope,
    )
    study = _study(brief, domain, envelope, legal)
    stale = replace(
        legal,
        envelope_reference=_reference("stale-envelope"),
    )

    with pytest.raises(ValueError, match="^height_advice_envelope_stale$"):
        resolve_height_choice(
            study,
            domain,
            stale,
            envelope=envelope,
        )


def test_geometric_height_advice_forbids_an_envelope_before_outcome() -> None:
    brief = replace(geometric_brief(), cell_period_nm=200)
    domain = height_domain(compile_metalens(brief))
    legal = fixture_height_evidence_required(
        brief,
        domain,
    )
    study = _geometric_study(brief, domain, legal)
    forbidden = replace(
        legal,
        envelope_reference=_reference("forbidden-envelope"),
    )

    with pytest.raises(
        ValueError,
        match="^geometric_phase_envelope_forbidden$",
    ):
        resolve_height_choice(study, domain, forbidden)


def test_height_owner_rejects_empty_advice_with_a_stale_envelope(
    tmp_path: Path,
) -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    legal = fixture_height_evidence_required(
        brief,
        domain,
        envelope=envelope,
    )
    stale = replace(
        legal,
        envelope_reference=_reference("stale-envelope"),
    )
    finding = Finding(
        claim="height_choice",
        kind=FindingKind.ADVICE,
        needs=("height_evidence_required",),
        record_references=(reference_for(stale.document().to_bytes()),),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    for value in (domain, envelope, stale):
        assert session.admit_document(value.document()) == reference_for(
            value.document().to_bytes()
        )

    with pytest.raises(ValueError, match="^height_advice_envelope_stale$"):
        MetalensEvidence(session).with_finding(
            _study(brief, domain, envelope, stale),
            finding,
        )


def test_recommended_height_advice_requires_its_bound_consultation() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    legal = _advice(brief, domain, 500, envelope)
    study = _study(brief, domain, envelope, legal)
    tampered = replace(legal, request_identity="sha256:tampered")

    with pytest.raises(ValueError, match="^height_advice_not_bound$"):
        resolve_height_choice(
            study,
            domain,
            tampered,
            envelope=envelope,
        )


def test_frontier_rejects_evidence_required_with_a_stale_envelope(
    tmp_path: Path,
) -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    legal = fixture_height_evidence_required(
        brief,
        domain,
        envelope=envelope,
    )
    unavailable = legal
    compiled = _study(brief, domain, envelope, unavailable)
    stale = replace(
        unavailable,
        envelope_reference=_reference("stale-envelope"),
    )
    forged = replace(
        compiled,
        advice=tuple(
            stale if isinstance(item, HeightAdvice) else item
            for item in compiled.advice
        ),
        findings=tuple(
            (
                replace(
                    finding,
                    record_references=(reference_for(stale.document().to_bytes()),),
                )
                if finding.claim == "height_choice"
                else finding
            )
            for finding in compiled.findings
        ),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    _admit_height_choice_context(session, forged, domain, envelope, stale)

    with pytest.raises(ValueError, match="^study_frontier_invalid$") as raised:
        StudyFrontier.from_document(
            StudyFrontier.start(forged).document(),
            brief=brief,
            session=session,
        )
    assert raised.value.__cause__ is not None
    assert raised.value.__cause__.args == ("height_advice_replay_mismatch",)


def test_frontier_preserves_legal_evidence_required_height_advice(
    tmp_path: Path,
) -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    unavailable = fixture_height_evidence_required(
        brief,
        domain,
        envelope=envelope,
    )
    waiting = _study(brief, domain, envelope, unavailable)
    session = AuthoritySession(Authority(tmp_path / "authority"))
    _admit_height_choice_context(session, waiting, domain, envelope, unavailable)

    restored = StudyFrontier.from_document(
        StudyFrontier.start(waiting).document(),
        brief=brief,
        session=session,
    )

    assert restored.studies == (waiting,)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    (
        (
            "brief_identity",
            "sha256:stale-brief",
            "height_advice_brief_mismatch",
        ),
        (
            "domain_reference",
            _reference("stale-domain"),
            "height_advice_stale",
        ),
    ),
)
def test_compiler_rejects_evidence_required_with_stale_grounds(
    field: str,
    value: object,
    error: str,
) -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    unavailable = fixture_height_evidence_required(
        brief,
        domain,
        envelope=envelope,
    )
    if field == "brief_identity":
        assert isinstance(value, str)
        invalid = replace(unavailable, brief_identity=value)
    else:
        assert isinstance(value, Reference)
        invalid = replace(unavailable, domain_reference=value)

    with pytest.raises(ValueError, match=f"^{error}$"):
        _study(brief, domain, envelope, invalid)


def test_height_choice_owner_rejects_a_forged_refusal(
    tmp_path: Path,
) -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    advice = _advice(brief, domain, 500, envelope)
    study = _study(brief, domain, envelope, advice)
    forged = Finding(
        claim="height_choice",
        kind=FindingKind.REFUSAL,
        needs=("height_constraint_ruled_out",),
        record_references=(envelope.evidence_reference,),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    _admit_height_choice_context(session, study, domain, envelope, advice)

    with pytest.raises(ValueError, match="^reported_finding_invalid$"):
        MetalensEvidence(session).with_finding(study, forged)


def test_outside_height_advice_remains_its_exact_typed_finding(
    tmp_path: Path,
) -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    legal = _advice(brief, domain, 500, envelope)
    assert isinstance(legal.conclusion, HeightRecommendation)
    advice = replace(
        legal,
        conclusion=replace(legal.conclusion, height_nm=650),
    )
    study = _study(brief, domain, envelope, advice)
    finding = resolve_height_choice(
        study,
        domain,
        advice,
        envelope=envelope,
    )
    assert isinstance(finding, Finding)
    assert finding.needs == ("height_advice_outside_domain",)
    session = AuthoritySession(Authority(tmp_path / "authority"))
    _admit_height_choice_context(session, study, domain, envelope, advice)

    with pytest.raises(ValueError, match="^height_advice_replay_mismatch$"):
        MetalensEvidence(session).with_finding(study, finding)


def test_ruled_out_height_advice_remains_its_exact_typed_finding(
    tmp_path: Path,
) -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    admitted_envelope = _envelope(brief, domain)
    envelope = _rule_out_height(admitted_envelope, 500)
    advice = replace(
        _advice(brief, domain, 500, admitted_envelope),
        envelope_reference=envelope.evidence_reference,
    )
    study = _study(brief, domain, envelope, advice)
    finding = resolve_height_choice(
        study,
        domain,
        advice,
        envelope=envelope,
    )
    assert isinstance(finding, Finding)
    assert finding.needs == ("height_advice_ruled_out",)
    session = AuthoritySession(Authority(tmp_path / "authority"))
    _admit_height_choice_context(session, study, domain, envelope, advice)

    with pytest.raises(ValueError, match="^height_advice_request_stale$"):
        MetalensEvidence(session).with_finding(study, finding)


def test_height_domain_is_exact_and_route_specific() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    advice = _advice(brief, domain, 500, envelope)
    study = _study(brief, domain, envelope, advice)
    tampered = replace(domain, heights_nm=(500, 550, 650))

    with pytest.raises(ValueError, match="height_domain_reference_mismatch"):
        resolve_height_choice(
            study,
            tampered,
            advice,
            envelope=envelope,
        )


def test_advice_cannot_cross_a_changed_height_domain() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    advice = replace(
        _advice(brief, domain, 500, envelope),
        domain_reference=_reference("stale-domain"),
    )

    with pytest.raises(ValueError, match="height_advice_stale"):
        _study(brief, domain, envelope, advice)


def test_evidence_required_height_returns_a_typed_finding() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    unavailable = fixture_height_evidence_required(
        brief,
        domain,
        envelope=envelope,
    )
    outcome = resolve_height_choice(
        _study(brief, domain, envelope, unavailable),
        domain,
        unavailable,
        envelope=envelope,
    )

    assert outcome.claim == "height_choice"
    assert outcome.kind is FindingKind.ADVICE
    assert outcome.needs == ("height_evidence_required",)
    assert outcome.record_references == (
        reference_for(unavailable.document().to_bytes()),
    )


def test_tampered_height_advice_is_a_direct_fault() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)

    advice = _advice(brief, domain, 500, envelope)
    tampered = replace(
        advice,
        conclusion=_advice(
            brief,
            domain,
            550,
            envelope,
        ).conclusion,
    )
    with pytest.raises(ValueError, match="height_advice_not_bound"):
        resolve_height_choice(
            _study(brief, domain, envelope, advice),
            domain,
            tampered,
            envelope=envelope,
        )


def test_height_choice_crosses_authority_with_domain_and_advice_only(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "workspace")
    brief = _viable_brief()
    base = compile_metalens(brief)
    provisional_domain = height_domain(base, atom_index="3.5")
    domain_reference = _admit(authority, provisional_domain.document())
    domain = provisional_domain.bind_evidence(domain_reference)
    provisional_envelope = phase_envelope(
        base,
        domain,
        atom_index="3.5",
    )
    envelope_reference = _admit_structured(
        authority,
        provisional_envelope.document(),
        (domain_reference,),
    )
    envelope = provisional_envelope.admitted(envelope_reference)
    advice = _advice(brief, domain, 500, envelope)
    _admit_structured(
        authority,
        advice.document(),
        (domain_reference, envelope_reference),
    )
    study = _study(brief, domain, envelope, advice)

    choice = resolve_height_choice(
        study,
        domain,
        advice,
        envelope=envelope,
    )
    choice_reference = _admit_structured(
        authority,
        choice.document(),
        choice.references(),
    )

    assert authority.fetch(choice_reference) == choice.document().to_bytes()


def test_admitted_height_choice_must_still_belong_to_the_exact_study() -> None:
    brief = _viable_brief()
    domain = _domain(brief)
    envelope = _envelope(brief, domain)
    advice = _advice(brief, domain, 500, envelope)
    study = _study(brief, domain, envelope, advice)
    choice = resolve_height_choice(
        study,
        domain,
        advice,
        envelope=envelope,
    )
    height_choice_task = next(
        task for task in study.ready_tasks if task.claim == "height_choice"
    )

    for stale, error in (
        (replace(choice, brief_identity="sha256:stale-brief"), "brief_mismatch"),
        (
            replace(choice, domain_reference=_reference("stale-domain")),
            "domain_mismatch",
        ),
        (replace(choice, minimum_feature_nm=80), "fabrication_mismatch"),
    ):
        stale_reference = reference_for(stale.document().to_bytes())
        stale_study = compile_metalens(
            brief,
            advice=study.advice,
            evidence=(
                *study.evidence,
                Evidence(
                    task_identity=height_choice_task.identity,
                    claim="height_choice",
                    schema=HEIGHT_CHOICE_SCHEMA,
                    reference=stale_reference,
                    binding_reference=height_choice_task.binding_reference,
                    consultations=height_choice_task.consultations,
                ),
            ),
            capabilities=study.capabilities,
            bindings=study.bindings,
        )

        with pytest.raises(ValueError, match=f"height_choice_{error}"):
            validate_height_choice(
                stale_study,
                stale,
                choice_reference=stale_reference,
            )


def _admit(authority: Authority, document: Document) -> Reference:
    decision = authority.decide(
        Proposal.record(document),
        at=authority.view().revision,
    )
    assert decision.body_reference is not None
    return decision.body_reference


def _admit_structured(
    authority: Authority,
    document: Document,
    references: tuple[Reference, ...],
) -> Reference:
    structure = authority.decide(
        Proposal.structure(Structure.for_document(document, references=references)),
        at=authority.view().revision,
    )
    assert structure.body_reference is not None
    decision = authority.decide(
        Proposal.structured(
            document,
            structure_reference=structure.body_reference,
            references=references,
        ),
        at=structure.resulting_revision,
    )
    assert decision.body_reference is not None
    return decision.body_reference

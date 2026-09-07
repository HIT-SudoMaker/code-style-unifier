from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from metacraft.authority import Authority, Document, reference_for
from metacraft.authority.session import AuthoritySession
from metacraft.science.consultation import (
    ConsultationAnswer,
    EvidenceRequired,
    ExternalClaim,
    Recommendation,
    ResearchMode,
)
from metacraft.science.metalens.checkpoint import StudyFrontier
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.brief import MonochromaticSpectrum
from metacraft.science.metalens.consultation import (
    accept_height_consultation_answer,
    accept_period_consultation_answer,
    form_height_consultation_request,
    form_period_consultation_request,
)
from metacraft.science.metalens.evidence import MetalensEvidence
from metacraft.science.metalens.height_advice import HeightAdvice
from metacraft.science.metalens.period_advice import PeriodAdvice
from metacraft.science.metalens.period import (
    PeriodChoice,
    resolve_period_choice,
)
from metacraft.science.study import Binding, Capability, Study
from tests.brief_fixtures import propagation_brief
from tests.domain_fixtures import (
    compile_with_facts,
    height_domain,
    material_binding,
    period_advice,
    period_choice,
    period_domain,
    phase_envelope,
)


_CAPABILITIES = (
    Capability("optical_material"),
    Capability("fabrication_constraint"),
    Capability("deterministic_selection"),
)
_BINDINGS = tuple(
    Binding(name, reference_for(f"replay-{name}".encode()))
    for name in (
        "optical_material",
        "fabrication_constraint",
        "deterministic_selection",
    )
)


def _brief():
    return replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
    )


def _answer(request, conclusion_kind: str) -> ConsultationAnswer:
    if conclusion_kind == "evidence_required":
        conclusion = EvidenceRequired(
            missing_fact="replay evidence",
            reason="current grounds require more evidence",
        )
        claims = ()
    else:
        claims = (
            ()
            if request.research_mode is ResearchMode.CLOSED_BOOK
            else (
                ExternalClaim(
                    statement="A source-grounded replay claim.",
                    locator="doi:10.0000/metacraft.replay",
                ),
            )
        )
        conclusion = Recommendation(
            candidate_identity=request.candidates[0].identity,
            reason="candidate closes the current question",
            decisive_ground_identities=(request.grounds[0].identity,),
            external_claim_identities=tuple(item.identity for item in claims),
        )
    return ConsultationAnswer(
        request_identity=request.identity,
        conclusion=conclusion,
        external_claims=claims,
    )


def _period_case(mode: ResearchMode, conclusion_kind: str):
    brief = _brief()
    base = compile_metalens(brief)
    domain = period_domain(base, atom_index="3.5")
    request = form_period_consultation_request(
        brief,
        domain,
        research_mode=mode,
    )
    advice = accept_period_consultation_answer(
        brief,
        domain,
        request,
        _answer(request, conclusion_kind),
    )
    material = material_binding(base, atom_index="3.5")
    study, _facts = compile_with_facts(
        brief,
        {
            "target_phase": reference_for(b"replay-target"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_CAPABILITIES,
        bindings=_BINDINGS,
    )
    return study, (domain.document(), advice.document())


def _height_case(mode: ResearchMode, conclusion_kind: str):
    brief = _brief()
    base = compile_metalens(brief)
    material = material_binding(base, atom_index="3.5")
    pdomain = period_domain(base, atom_index="3.5")
    padvice = period_advice(
        base,
        pdomain,
        period_nm=pdomain.period_limit_nm,
    )
    pchoice = period_choice(base, atom_index="3.5")
    hdomain = height_domain(base, atom_index="3.5")
    envelope = phase_envelope(base, hdomain, atom_index="3.5")
    request = form_height_consultation_request(
        brief,
        hdomain,
        envelope=envelope,
        research_mode=mode,
    )
    hadvice = accept_height_consultation_answer(
        brief,
        hdomain,
        request,
        _answer(request, conclusion_kind),
        envelope=envelope,
    )
    study, _facts = compile_with_facts(
        brief,
        {
            "target_phase": reference_for(b"replay-target"),
            "material_binding": material.evidence_reference,
            "period_domain": pdomain.evidence_reference,
            "period_choice": pchoice.evidence_reference,
            "height_domain": hdomain.evidence_reference,
            "phase_envelope": envelope.evidence_reference,
        },
        advice=(padvice, hadvice),
        capabilities=_CAPABILITIES,
        bindings=_BINDINGS,
    )
    return study, (
        pdomain.document(),
        padvice.document(),
        hdomain.document(),
        envelope.document(),
        hadvice.document(),
    )


@pytest.mark.parametrize("question", ("period", "height"))
@pytest.mark.parametrize("conclusion_kind", ("recommendation", "evidence_required"))
@pytest.mark.parametrize("mode", tuple(ResearchMode))
def test_recompile_replays_every_closed_advice_path_without_mutation(
    tmp_path: Path,
    question: str,
    conclusion_kind: str,
    mode: ResearchMode,
) -> None:
    study, documents = (
        _period_case(mode, conclusion_kind)
        if question == "period"
        else _height_case(mode, conclusion_kind)
    )
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    for document in documents:
        session.admit_document(document)
    before = authority.view()

    replayed = MetalensEvidence(session).recompile(study)

    assert replayed.canonical_bytes() == study.canonical_bytes()
    assert authority.view() == before


def test_replayed_multi_order_period_keeps_current_classification(
    tmp_path: Path,
) -> None:
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(1_700),
        numerical_aperture=Decimal("0.3"),
    )
    base = compile_metalens(brief)
    material = material_binding(base, substrate_index="1.7")
    domain = period_domain(base, substrate_index="1.7")
    advice = period_advice(base, domain, period_nm=1_600)
    study, _facts = compile_with_facts(
        brief,
        {
            "target_phase": reference_for(b"replay-target"),
            "material_binding": material.evidence_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_CAPABILITIES,
        bindings=_BINDINGS,
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    session.admit_document(domain.document())
    session.admit_document(advice.document())

    replayed = MetalensEvidence(session).recompile(study)
    choice = resolve_period_choice(replayed, domain, period_advice=advice)

    assert isinstance(choice, PeriodChoice)
    assert choice.order_regime == "multi order"
    assert tuple(caution.concern for caution in choice.cautions) == (
        "higher orders possible",
    )


def test_recompile_rejects_missing_advice_body_directly(tmp_path: Path) -> None:
    study, documents = _period_case(
        ResearchMode.CLOSED_BOOK,
        "recommendation",
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    session.admit_document(documents[0])

    with pytest.raises(RuntimeError, match="^reference_unresolvable"):
        MetalensEvidence(session).recompile(study)


def test_recompile_rejects_duplicate_period_advice(tmp_path: Path) -> None:
    study, documents = _period_case(
        ResearchMode.CLOSED_BOOK,
        "recommendation",
    )
    advice = next(item for item in study.advice if isinstance(item, PeriodAdvice))
    other = replace(advice, request_identity="sha256:other-request")
    session = AuthoritySession(Authority(tmp_path / "authority"))
    for document in (*documents, other.document()):
        session.admit_document(document)

    with pytest.raises(ValueError, match="^period_advice_duplicate$"):
        MetalensEvidence(session).recompile(
            study,
            advice=(advice, other),
        )


def test_recompile_rejects_a_stale_research_mode_identity(tmp_path: Path) -> None:
    study, documents = _period_case(
        ResearchMode.CLOSED_BOOK,
        "recommendation",
    )
    advice = next(item for item in study.advice if isinstance(item, PeriodAdvice))
    stale = replace(advice, request_identity="sha256:removed-research-mode")
    session = AuthoritySession(Authority(tmp_path / "authority"))
    for document in (documents[0], stale.document()):
        session.admit_document(document)

    with pytest.raises(ValueError, match="^period_advice_request_stale$"):
        MetalensEvidence(session).recompile(study, advice=(stale,))


def test_checkpoint_preserves_the_direct_replay_fault_as_cause(
    tmp_path: Path,
) -> None:
    study, documents = _period_case(
        ResearchMode.CLOSED_BOOK,
        "recommendation",
    )
    advice = next(item for item in study.advice if isinstance(item, PeriodAdvice))
    stale = replace(advice, request_identity="sha256:removed-research-mode")
    forged = replace(study, advice=(stale,))
    session = AuthoritySession(Authority(tmp_path / "authority"))
    for document in (documents[0], stale.document()):
        session.admit_document(document)

    with pytest.raises(ValueError, match="^study_frontier_invalid$") as raised:
        StudyFrontier.from_document(
            StudyFrontier.start(forged).document(),
            brief=study.brief,
            session=session,
        )

    assert raised.value.__cause__ is not None
    assert raised.value.__cause__.args == ("period_advice_request_stale",)


def test_recompile_rejects_regenerated_byte_mismatch(tmp_path: Path) -> None:
    study, documents = _period_case(
        ResearchMode.CLOSED_BOOK,
        "recommendation",
    )
    advice = next(item for item in study.advice if isinstance(item, PeriodAdvice))
    surplus = replace(
        advice.grounds[1],
        statement=f"{advice.grounds[1].statement} (surplus)",
    )
    forged = replace(advice, grounds=(*advice.grounds, surplus))
    session = AuthoritySession(Authority(tmp_path / "authority"))
    for document in (documents[0], forged.document()):
        session.admit_document(document)

    with pytest.raises(ValueError, match="^period_advice_replay_mismatch$"):
        MetalensEvidence(session).recompile(study, advice=(forged,))


def test_recompile_translates_a_forged_answer_rule_fault_to_replay_mismatch(
    tmp_path: Path,
) -> None:
    study, documents = _period_case(
        ResearchMode.CLOSED_BOOK,
        "recommendation",
    )
    advice = next(item for item in study.advice if isinstance(item, PeriodAdvice))
    forged_ground = replace(
        advice.grounds[0],
        statement=f"{advice.grounds[0].statement} (forged)",
    )
    forged = replace(
        advice,
        grounds=(forged_ground,),
        conclusion=replace(
            advice.conclusion,
            decisive_ground_identities=(forged_ground.identity,),
        ),
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    for document in (documents[0], forged.document()):
        session.admit_document(document)

    with pytest.raises(ValueError, match="^period_advice_replay_mismatch$"):
        MetalensEvidence(session).recompile(study, advice=(forged,))


class _WrongAdviceBytesSession:
    def __init__(self, advice_reference) -> None:
        self._advice_reference = advice_reference

    def observe_admitted(self, reference) -> None:
        assert reference == self._advice_reference

    def fetch(self, reference) -> bytes:
        assert reference == self._advice_reference
        return b"wrong admitted advice bytes"


def test_recompile_compares_retained_and_authority_advice_bytes() -> None:
    study, _documents = _period_case(
        ResearchMode.CLOSED_BOOK,
        "recommendation",
    )
    advice = next(item for item in study.advice if isinstance(item, PeriodAdvice))
    reference = reference_for(advice.document().to_bytes())

    with pytest.raises(ValueError, match="^period_advice_replay_mismatch$"):
        MetalensEvidence(_WrongAdviceBytesSession(reference)).recompile(study)  # type: ignore[arg-type]


def test_frontier_rejects_forged_advice_subtree(tmp_path: Path) -> None:
    study, documents = _period_case(
        ResearchMode.CLOSED_BOOK,
        "recommendation",
    )
    encoded = StudyFrontier.start(study).document().values
    studies = dict(encoded["studies"])
    first = dict(studies["study_001"])
    values = dict(first["values"])
    advice = dict(values["advice"])
    advice["advice_001"] = {"forged": True}
    values["advice"] = advice
    first["values"] = values
    studies["study_001"] = first
    forged = Document(
        StudyFrontier.start(study).document().schema_identifier,
        {**encoded, "studies": studies},
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))
    for document in documents:
        session.admit_document(document)

    with pytest.raises(ValueError, match="^study_frontier_invalid$"):
        StudyFrontier.from_document(
            forged,
            brief=study.brief,
            session=session,
        )

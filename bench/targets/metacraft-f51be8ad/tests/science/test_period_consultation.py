from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from typing import cast

import metacraft.science.metalens.consultation as metalens_consultation
import pytest

from metacraft.authority import Authority, Document, reference_for
from metacraft.canonical import encode_bytes
from metacraft.science import Binding, Capability, FindingKind, compile_study
from metacraft.science.consultation import (
    ConsultationAnswer,
    EvidenceRequired,
    ExternalClaim,
    Recommendation,
    ResearchMode,
    QuestionKind,
    validate_consultation_answer,
)
from metacraft.science.metalens.consultation import (
    InvalidMetalensConsultationAnswer,
    accept_period_consultation_answer,
    form_period_consultation_request,
)
from metacraft.science.metalens.brief import MonochromaticSpectrum
from metacraft.science.metalens.period_advice import (
    PERIOD_ADVICE_SCHEMA,
    PeriodAdvice,
)
from tests.brief_fixtures import propagation_brief
from tests.domain_fixtures import compile_with_facts, period_domain


def _period_request(*, research_mode: ResearchMode = ResearchMode.CLOSED_BOOK):
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(wavelength_nm=1_700),
        numerical_aperture=Decimal("0.3"),
    )
    study = compile_study(brief)
    domain = period_domain(study, substrate_index="1.7")
    request = form_period_consultation_request(
        brief,
        domain,
        research_mode=research_mode,
    )
    return brief, study, domain, request


def _recommendation_for(request, *, period_nm: int = 840) -> Recommendation:
    candidate = next(
        candidate
        for candidate in request.candidates
        if candidate.quantity == Decimal(period_nm)
    )
    return Recommendation(
        candidate_identity=candidate.identity,
        reason="Preserve a conservative margin below the physical ceiling.",
        decisive_ground_identities=(request.grounds[-1].identity,),
        external_claim_identities=(),
    )


class _SentinelFailure(ValueError):
    pass


def _raise_sentinel(*_args, **_kwargs):
    raise _SentinelFailure("sentinel")


def _grounding_capabilities() -> tuple[Capability, ...]:
    return (
        Capability("optical_material"),
        Capability("fabrication_constraint"),
        Capability("deterministic_selection"),
    )


def _grounding_bindings() -> tuple[Binding, ...]:
    return tuple(
        Binding(name, reference_for(name.encode()))
        for name in (
            "optical_material",
            "fabrication_constraint",
            "deterministic_selection",
        )
    )


def test_period_request_round_trips_canonical_grounded_bytes() -> None:
    brief, _study, domain, request = _period_request()

    restored = type(request).from_document(request.document())

    assert restored == request
    assert restored.document().to_bytes() == request.document().to_bytes()
    assert request.brief_identity == _study.brief_identity
    assert request.grounds
    assert request.candidates[0].quantity == Decimal(10)
    assert request.candidates[-1].quantity == Decimal(domain.period_limit_nm)
    assert {candidate.unit for candidate in request.candidates} == {"nm"}
    assert request.grounds[-1].source_identity == (
        "sha256:"
        + hashlib.sha256(
            encode_bytes(domain.evidence_reference.as_mapping())
        ).hexdigest()
    )
    encoded = request.document().to_bytes()
    for forbidden in (
        b"height",
        b"provider",
        b"model",
        b"endpoint",
        b"harness",
        b"benchmark",
    ):
        assert forbidden not in encoded


def test_period_request_offers_sampling_legal_multi_order_candidates() -> None:
    brief, _study, domain, request = _period_request()

    candidate = next(
        item for item in request.candidates if item.quantity == Decimal(900)
    )
    advice = accept_period_consultation_answer(
        brief,
        domain,
        request,
        ConsultationAnswer(
            request_identity=request.identity,
            conclusion=Recommendation(
                candidate_identity=candidate.identity,
                reason="Use a sampling-legal period with visible order risk.",
                decisive_ground_identities=(request.grounds[1].identity,),
                external_claim_identities=(),
            ),
            external_claims=(),
        ),
    )

    assert domain.order_ceiling_nm == Decimal("850")
    assert domain.period_limit_nm == 2830
    assert advice.conclusion.period_nm == 900
    assert request.grounds[2].kind.value == "caution"
    assert "order ceiling: 850 nm" in request.grounds[2].statement


def test_answer_contract_is_sufficient_to_write_one_exact_answer() -> None:
    _brief, _study, _domain, request = _period_request(
        research_mode=ResearchMode.SOURCE_GROUNDED
    )
    contract = request.document().values["answer_contract"]

    assert contract == {
        "candidate_unit": "nm",
        "conclusions": {
            "evidence_required": {
                "fields": ["kind", "missing_fact", "reason"],
                "kind": "evidence_required",
            },
            "recommendation": {
                "fields": [
                    "candidate_identity",
                    "decisive_ground_identities",
                    "external_claim_identities",
                    "kind",
                    "reason",
                ],
                "kind": "recommendation",
            },
        },
        "document_fields": [
            "conclusion",
            "external_claims",
            "request_identity",
        ],
        "external_claims": {
            "identity_rule": (
                "sha256:<lowercase hex> of UTF-8 JSON over locator and "
                "statement with sorted keys, no whitespace, and unescaped "
                "Unicode"
            ),
            "index_format": "claim_001, claim_002, ...",
            "locator_rule": "absolute https URL or doi:<non-empty>",
            "member_fields": ["identity", "locator", "statement"],
        },
        "requires_concise_reason": True,
        "schema_identifier": "metacraft.science.consultation_answer",
    }
    claim_value = {
        "locator": "doi:10.1000/contract-example",
        "statement": "A primary source supports the conservative margin.",
    }
    claim_identity = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                claim_value,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
    )
    candidate_identity = request.candidates[-1].identity
    ground_identity = request.grounds[-1].identity
    answer_document = Document(
        contract["schema_identifier"],
        {
            "conclusion": {
                "candidate_identity": candidate_identity,
                "decisive_ground_identities": [ground_identity],
                "external_claim_identities": [claim_identity],
                "kind": "recommendation",
                "reason": "Retain the largest supported conservative cell.",
            },
            "external_claims": {
                "claim_001": {"identity": claim_identity, **claim_value}
            },
            "request_identity": request.identity,
        },
    )

    answer = ConsultationAnswer.from_document(answer_document)
    validate_consultation_answer(request, answer)

    changed = dict(request.document().values)
    changed_contract = dict(contract)
    changed_contract["schema_identifier"] = "metacraft.foreign.answer"
    changed["answer_contract"] = changed_contract
    with pytest.raises(ValueError, match="consultation_request_invalid"):
        type(request).from_document(Document(request.schema_identifier, changed))


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (("quantity", "NaN"), ("unit", "um")),
)
def test_period_request_rejects_nonfinite_or_wrong_unit_candidates(
    field: str,
    invalid_value: str,
) -> None:
    _brief, _study, _domain, request = _period_request()
    values = dict(request.document().values)
    candidates = dict(values["candidates"])
    first = dict(candidates["candidate_001"])
    first[field] = invalid_value
    candidates["candidate_001"] = first
    values["candidates"] = candidates

    with pytest.raises(ValueError, match="consultation_request_invalid"):
        type(request).from_document(
            Document(request.document().schema_identifier, values)
        )


def test_closed_answer_becomes_provider_free_period_advice() -> None:
    brief, _study, domain, request = _period_request()
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=_recommendation_for(request),
        external_claims=(),
    )

    advice = accept_period_consultation_answer(
        brief,
        domain,
        request,
        answer,
    )

    assert advice.document().schema_identifier == PERIOD_ADVICE_SCHEMA
    assert PeriodAdvice.from_document(advice.document()) == advice
    assert advice.conclusion.period_nm == 840
    assert advice.conclusion.reason == answer.conclusion.reason
    assert advice.grounds == request.grounds
    assert advice.external_claims == ()
    for retired in (
        "status",
        "provider",
        "endpoint_identity",
        "model",
        "prompt",
        "raw_response",
        "failure",
        "synthetic",
    ):
        assert retired not in advice.document().values


@pytest.mark.parametrize("fault", ("stale", "ground", "candidate"))
def test_period_answer_rejects_stale_or_invented_identity(fault: str) -> None:
    brief, _study, domain, request = _period_request()
    recommendation = _recommendation_for(request)
    if fault == "ground":
        recommendation = replace(
            recommendation,
            decisive_ground_identities=("sha256:invented-ground",),
        )
    elif fault == "candidate":
        recommendation = replace(
            recommendation,
            candidate_identity="sha256:invented-candidate",
        )
    answer = ConsultationAnswer(
        request_identity=(
            "sha256:stale-request" if fault == "stale" else request.identity
        ),
        conclusion=recommendation,
        external_claims=(),
    )

    with pytest.raises(InvalidMetalensConsultationAnswer) as rejected:
        accept_period_consultation_answer(
            brief,
            domain,
            request,
            answer,
        )
    assert rejected.value.question_kind is QuestionKind.PERIOD


def test_invalid_period_answer_leaves_authority_unchanged(tmp_path) -> None:
    brief, _study, domain, request = _period_request()
    authority = Authority(tmp_path / "authority")
    before = authority.view()
    answer = ConsultationAnswer(
        request_identity="sha256:stale-request",
        conclusion=_recommendation_for(request),
        external_claims=(),
    )

    with pytest.raises(InvalidMetalensConsultationAnswer) as rejected:
        accept_period_consultation_answer(
            brief,
            domain,
            request,
            answer,
        )
    assert rejected.value.question_kind is QuestionKind.PERIOD

    after = authority.view()
    assert after == before


def test_period_internal_request_staleness_remains_direct() -> None:
    brief, _study, domain, request = _period_request()
    stale = replace(request, cautions=(*request.cautions, "internal drift"))
    answer = ConsultationAnswer(
        request_identity=stale.identity,
        conclusion=_recommendation_for(stale),
        external_claims=(),
    )

    with pytest.raises(ValueError, match="^period_consultation_request_stale$"):
        accept_period_consultation_answer(brief, domain, stale, answer)


def test_period_formation_fault_remains_direct(monkeypatch) -> None:
    brief, _study, domain, request = _period_request()
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=_recommendation_for(request),
        external_claims=(),
    )
    monkeypatch.setattr(
        metalens_consultation,
        "form_period_consultation_request",
        _raise_sentinel,
    )

    with pytest.raises(_SentinelFailure):
        accept_period_consultation_answer(brief, domain, request, answer)


@pytest.mark.parametrize(
    "construction",
    ("candidate_conversion", "PeriodRecommendation", "PeriodAdvice"),
)
def test_period_candidate_and_advice_construction_faults_remain_direct(
    monkeypatch,
    construction: str,
) -> None:
    brief, _study, domain, request = _period_request()
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=_recommendation_for(request),
        external_claims=(),
    )
    if construction == "candidate_conversion":
        monkeypatch.setattr(
            metalens_consultation,
            "int",
            _raise_sentinel,
            raising=False,
        )
    else:
        monkeypatch.setattr(
            metalens_consultation,
            construction,
            _raise_sentinel,
        )

    with pytest.raises(_SentinelFailure):
        accept_period_consultation_answer(brief, domain, request, answer)


def test_wrong_period_answer_runtime_type_remains_direct() -> None:
    brief, _study, domain, request = _period_request()

    with pytest.raises(AttributeError):
        accept_period_consultation_answer(
            brief,
            domain,
            request,
            cast(ConsultationAnswer, object()),
        )


def test_invalid_period_domain_keeps_its_direct_error() -> None:
    brief, _study, domain, request = _period_request()
    forged = replace(
        domain,
        evidence_reference=reference_for(b"forged period domain"),
    )
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=_recommendation_for(request),
        external_claims=(),
    )

    with pytest.raises(ValueError, match="^period_domain_reference_mismatch$"):
        accept_period_consultation_answer(
            brief,
            forged,
            request,
            answer,
        )


def test_closed_book_answer_rejects_external_claims() -> None:
    brief, _study, domain, request = _period_request()
    claim = ExternalClaim(
        statement="A paper reports a similar lattice period.",
        locator="https://example.test/paper",
    )
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=replace(
            _recommendation_for(request),
            external_claim_identities=(claim.identity,),
        ),
        external_claims=(claim,),
    )

    with pytest.raises(InvalidMetalensConsultationAnswer) as rejected:
        accept_period_consultation_answer(
            brief,
            domain,
            request,
            answer,
        )
    assert rejected.value.question_kind is QuestionKind.PERIOD


def test_source_grounded_answer_closes_every_external_claim_identity() -> None:
    brief, _study, domain, request = _period_request(
        research_mode=ResearchMode.SOURCE_GROUNDED
    )
    claim = ExternalClaim(
        statement="A primary source supports the stated fabrication margin.",
        locator="doi:10.1000/example",
    )
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=replace(
            _recommendation_for(request),
            external_claim_identities=(claim.identity,),
        ),
        external_claims=(claim,),
    )

    advice = accept_period_consultation_answer(
        brief,
        domain,
        request,
        answer,
    )

    assert advice.external_claims == (claim,)
    assert ConsultationAnswer.from_document(answer.document()) == answer


def test_evidence_required_cannot_create_period_or_height_work() -> None:
    brief, _study, domain, request = _period_request()
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=EvidenceRequired(
            missing_fact="fabrication tolerance at the requested wavelength",
            reason="The supplied domain cannot establish a conservative choice.",
        ),
        external_claims=(),
    )
    advice = accept_period_consultation_answer(
        brief,
        domain,
        request,
        answer,
    )
    compiled, _facts = compile_with_facts(
        brief,
        references={
            "target_phase": reference_for(b"phase"),
            "material_binding": domain.material_binding_reference,
            "period_domain": domain.evidence_reference,
        },
        advice=(advice,),
        capabilities=_grounding_capabilities(),
        bindings=_grounding_bindings(),
    )

    assert any(
        finding.kind is FindingKind.ADVICE
        and finding.claim == "period_choice"
        and finding.needs == ("period_evidence_required",)
        for finding in compiled.findings
    )
    assert not any(
        task.claim in {"period_choice", "height_domain", "height_choice"}
        for task in compiled.ready_tasks
    )


def test_retired_period_advice_schema_has_no_compatibility_reader() -> None:
    with pytest.raises(ValueError, match="period_advice_schema_mismatch"):
        PeriodAdvice.from_document(Document("metacraft.advice.period", {}))

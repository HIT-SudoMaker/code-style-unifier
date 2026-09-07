from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import hashlib

import metacraft.science.metalens.consultation as metalens_consultation
import pytest

from metacraft.authority import reference_for
from metacraft.authority import Document
from metacraft.canonical import encode_bytes
from metacraft.science import Binding, Capability, FindingKind
from metacraft.science.consultation import (
    ConsultationAnswer,
    EvidenceRequired,
    GroundKind,
    Recommendation,
    ResearchMode,
    QuestionKind,
)
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.brief import MonochromaticSpectrum
from metacraft.science.metalens.consultation import (
    InvalidMetalensConsultationAnswer,
    accept_height_consultation_answer,
    form_height_consultation_request,
)
from metacraft.science.metalens.height_advice import (
    HEIGHT_ADVICE_SCHEMA,
    HeightAdvice,
    HeightRecommendation,
)
from tests.brief_fixtures import geometric_brief, propagation_brief
from tests.domain_fixtures import (
    compile_with_facts,
    height_domain,
    material_binding,
    period_domain,
    period_choice,
    period_advice,
    phase_envelope,
)


def _propagation_request():
    brief = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
    )
    study = compile_metalens(brief)
    domain = height_domain(study, atom_index="3.5")
    envelope = phase_envelope(study, domain, atom_index="3.5")
    request = form_height_consultation_request(
        brief,
        domain,
        envelope=envelope,
        research_mode=ResearchMode.CLOSED_BOOK,
    )
    return brief, study, domain, envelope, request


def _recommendation_for(request, *, height_nm: int = 500) -> Recommendation:
    candidate = next(
        item for item in request.candidates if item.quantity == Decimal(height_nm)
    )
    decisive = tuple(
        ground.identity
        for ground in request.grounds
        if ground.kind in {GroundKind.FACT, GroundKind.CONSTRAINT}
    )
    return Recommendation(
        candidate_identity=candidate.identity,
        reason="Use a legal height with conservative fabrication margin.",
        decisive_ground_identities=decisive,
        external_claim_identities=(),
    )


class _SentinelFailure(ValueError):
    pass


def _raise_sentinel(*_args, **_kwargs):
    raise _SentinelFailure("sentinel")


def _readmit_envelope(envelope, **changes):
    provisional = replace(
        envelope,
        **changes,
        evidence_reference=None,
    )
    return provisional.admitted(reference_for(provisional.document().to_bytes()))


def _reference_identity(reference) -> str:
    return "sha256:" + hashlib.sha256(encode_bytes(reference.as_mapping())).hexdigest()


def test_propagation_height_request_round_trips_exact_grounded_bytes() -> None:
    brief, study, domain, envelope, request = _propagation_request()

    restored = type(request).from_document(request.document())

    assert restored == request
    assert request.brief_identity == study.brief_identity
    assert request.document().schema_identifier == (
        "metacraft.science.metalens.height_consultation_request"
    )
    assert tuple(int(item.quantity) for item in request.candidates) == (
        domain.heights_nm
    )
    assert {item.unit for item in request.candidates} == {"nm"}
    assert any(
        ground.source_identity == _reference_identity(domain.period_choice_reference)
        and f"selected period: {domain.period_nm} nm" in ground.statement
        for ground in request.grounds
    )
    assert any(
        ground.source_identity == _reference_identity(envelope.evidence_reference)
        and ground.kind is GroundKind.FORECAST
        and "forecast" in ground.statement
        for ground in request.grounds
    )
    assert any(
        ground.kind is GroundKind.CONSTRAINT
        and f"aspect limit: {domain.aspect_limit}" in ground.statement
        and f"dimension step: {domain.dimension_step_nm} nm" in ground.statement
        for ground in request.grounds
    )
    assert all(
        str(fabrication.candidate_count)
        in " ".join(ground.statement for ground in request.grounds)
        for fabrication in domain.fabrication_ranges
        if fabrication.height_nm in domain.heights_nm
    )
    encoded = request.document().to_bytes()
    for forbidden in (b"provider", b"endpoint", b"harness", b"benchmark"):
        assert forbidden not in encoded


def test_geometric_height_request_is_envelope_free_and_jones_honest() -> None:
    brief = replace(geometric_brief(), cell_period_nm=220)
    study = compile_metalens(brief)
    domain = height_domain(study)

    request = form_height_consultation_request(
        brief,
        domain,
        research_mode=ResearchMode.CLOSED_BOOK,
    )

    assert tuple(int(item.quantity) for item in request.candidates) == (
        domain.heights_nm
    )
    assert all(ground.kind is not GroundKind.FORECAST for ground in request.grounds)
    assert any("Jones" in caution for caution in request.cautions)
    assert b"phase_envelope" not in request.document().to_bytes()

    propagation = replace(
        propagation_brief(),
        operating_spectrum=MonochromaticSpectrum(940),
    )
    propagation_study = compile_metalens(propagation)
    propagation_domain = height_domain(propagation_study, atom_index="3.5")
    with pytest.raises(ValueError, match="phase_envelope_required"):
        form_height_consultation_request(propagation, propagation_domain)
    with pytest.raises(ValueError, match="geometric_phase_envelope_forbidden"):
        form_height_consultation_request(
            brief,
            domain,
            envelope=phase_envelope(
                propagation_study,
                propagation_domain,
                atom_index="3.5",
            ),
        )


def test_closed_answer_becomes_provider_free_height_advice() -> None:
    brief, _study, domain, envelope, request = _propagation_request()
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=_recommendation_for(request),
        external_claims=(),
    )

    advice = accept_height_consultation_answer(
        brief,
        domain,
        request,
        answer,
        envelope=envelope,
    )

    assert advice.document().schema_identifier == HEIGHT_ADVICE_SCHEMA
    assert HeightAdvice.from_document(advice.document()) == advice
    assert isinstance(advice.conclusion, HeightRecommendation)
    assert advice.conclusion.height_nm == 500
    assert advice.domain_reference == domain.evidence_reference
    assert advice.envelope_reference == envelope.evidence_reference
    assert advice.grounds == request.grounds
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


def test_height_answer_cannot_make_a_forecast_decisive() -> None:
    brief, _study, domain, envelope, request = _propagation_request()
    candidate = next(
        item for item in request.candidates if item.quantity == Decimal(500)
    )
    forecast = next(
        ground for ground in request.grounds if ground.kind is GroundKind.FORECAST
    )
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=Recommendation(
            candidate_identity=candidate.identity,
            reason="The forecast alone suggests this height.",
            decisive_ground_identities=(forecast.identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )

    with pytest.raises(InvalidMetalensConsultationAnswer) as rejected:
        accept_height_consultation_answer(
            brief,
            domain,
            request,
            answer,
            envelope=envelope,
        )
    assert rejected.value.question_kind is QuestionKind.HEIGHT


def test_height_answer_cannot_select_a_certifiably_ruled_out_height() -> None:
    brief, _study, domain, envelope, _request = _propagation_request()
    ruled_out = _readmit_envelope(
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
                if reach.height_nm == 500
                else reach
            )
            for reach in envelope.reaches
        ),
    )
    request = form_height_consultation_request(
        brief,
        domain,
        envelope=ruled_out,
        research_mode=ResearchMode.CLOSED_BOOK,
    )
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=_recommendation_for(request),
        external_claims=(),
    )

    with pytest.raises(InvalidMetalensConsultationAnswer) as rejected:
        accept_height_consultation_answer(
            brief,
            domain,
            request,
            answer,
            envelope=ruled_out,
        )
    assert rejected.value.question_kind is QuestionKind.HEIGHT


def test_height_envelope_integrity_faults_remain_direct_with_an_answer() -> None:
    brief, _study, domain, envelope, request = _propagation_request()
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=_recommendation_for(request),
        external_claims=(),
    )
    malformed = (
        (None, "phase_envelope_required"),
        (
            replace(
                envelope,
                evidence_reference=reference_for(b"forged phase envelope"),
            ),
            "phase_envelope_reference_mismatch",
        ),
        (
            _readmit_envelope(envelope, brief_identity="sha256:other-brief"),
            "phase_envelope_brief_mismatch",
        ),
        (
            _readmit_envelope(
                envelope,
                height_domain_reference=reference_for(b"other height domain"),
            ),
            "phase_envelope_domain_mismatch",
        ),
        (
            _readmit_envelope(envelope, reaches=envelope.reaches[1:]),
            "phase_envelope_height_coverage_mismatch",
        ),
    )

    for candidate, reason in malformed:
        with pytest.raises(ValueError, match=f"^{reason}$"):
            accept_height_consultation_answer(
                brief,
                domain,
                request,
                answer,
                envelope=candidate,
            )


def test_geometric_envelope_prohibition_remains_direct_with_an_answer() -> None:
    brief = replace(geometric_brief(), cell_period_nm=220)
    study = compile_metalens(brief)
    domain = height_domain(study)
    request = form_height_consultation_request(
        brief,
        domain,
        research_mode=ResearchMode.CLOSED_BOOK,
    )
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=_recommendation_for(
            request,
            height_nm=domain.heights_nm[0],
        ),
        external_claims=(),
    )
    propagation_brief_value, propagation_study, propagation_domain, _, _ = (
        _propagation_request()
    )
    del propagation_brief_value
    envelope = phase_envelope(
        propagation_study,
        propagation_domain,
        atom_index="3.5",
    )

    with pytest.raises(ValueError, match="^geometric_phase_envelope_forbidden$"):
        accept_height_consultation_answer(
            brief,
            domain,
            request,
            answer,
            envelope=envelope,
        )


@pytest.mark.parametrize("fault", ("missing", "extra", "duplicate"))
def test_propagation_request_requires_exact_envelope_height_coverage(
    fault: str,
) -> None:
    brief, _study, domain, envelope, _request = _propagation_request()
    if fault == "missing":
        reaches = envelope.reaches[1:]
    elif fault == "extra":
        reaches = (
            *envelope.reaches,
            replace(envelope.reaches[-1], height_nm=600),
        )
    else:
        reaches = (*envelope.reaches, envelope.reaches[-1])
    unbound = replace(envelope, reaches=reaches, evidence_reference=None)
    malformed = unbound.admitted(reference_for(unbound.document().to_bytes()))

    with pytest.raises(
        ValueError,
        match="phase_envelope_height_coverage_mismatch",
    ):
        form_height_consultation_request(
            brief,
            domain,
            envelope=malformed,
        )


@pytest.mark.parametrize("fault", ("stale", "ground", "candidate"))
def test_height_answer_rejects_stale_or_invented_identity(fault: str) -> None:
    brief, _study, domain, envelope, request = _propagation_request()
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
        accept_height_consultation_answer(
            brief,
            domain,
            request,
            answer,
            envelope=envelope,
        )
    assert rejected.value.question_kind is QuestionKind.HEIGHT


def test_height_internal_request_staleness_remains_direct() -> None:
    brief, _study, domain, envelope, request = _propagation_request()
    stale = replace(request, cautions=(*request.cautions, "internal drift"))
    answer = ConsultationAnswer(
        request_identity=stale.identity,
        conclusion=_recommendation_for(stale),
        external_claims=(),
    )

    with pytest.raises(ValueError, match="^height_consultation_request_stale$"):
        accept_height_consultation_answer(
            brief,
            domain,
            stale,
            answer,
            envelope=envelope,
        )


def test_height_formation_fault_remains_direct(monkeypatch) -> None:
    brief, _study, domain, envelope, request = _propagation_request()
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=_recommendation_for(request),
        external_claims=(),
    )
    monkeypatch.setattr(
        metalens_consultation,
        "form_height_consultation_request",
        _raise_sentinel,
    )

    with pytest.raises(_SentinelFailure):
        accept_height_consultation_answer(
            brief,
            domain,
            request,
            answer,
            envelope=envelope,
        )


@pytest.mark.parametrize(
    "construction",
    ("candidate_conversion", "HeightRecommendation", "HeightAdvice"),
)
def test_height_candidate_and_advice_construction_faults_remain_direct(
    monkeypatch,
    construction: str,
) -> None:
    brief, _study, domain, envelope, request = _propagation_request()
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
        accept_height_consultation_answer(
            brief,
            domain,
            request,
            answer,
            envelope=envelope,
        )


def test_evidence_required_forms_provider_free_height_advice() -> None:
    brief, _study, domain, envelope, request = _propagation_request()
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=EvidenceRequired(
            missing_fact="fabrication tolerance for the candidate heights",
            reason="The supplied grounds cannot support a safe height.",
        ),
        external_claims=(),
    )

    advice = accept_height_consultation_answer(
        brief,
        domain,
        request,
        answer,
        envelope=envelope,
    )

    assert advice.conclusion == answer.conclusion
    assert HeightAdvice.from_document(advice.document()) == advice

    compiled, _facts = compile_with_facts(
        brief,
        {
            "target_phase": reference_for(b"height target phase"),
            "material_binding": material_binding(
                _study, atom_index="3.5"
            ).evidence_reference,
            "period_domain": period_domain(_study, atom_index="3.5").evidence_reference,
            "period_choice": period_choice(_study, atom_index="3.5").evidence_reference,
            "height_domain": domain.evidence_reference,
            "phase_envelope": envelope.evidence_reference,
        },
        advice=(
            period_advice(
                _study,
                period_domain(_study, atom_index="3.5"),
                period_nm=period_choice(_study, atom_index="3.5").period_nm,
            ),
            advice,
        ),
        capabilities=tuple(
            Capability(name)
            for name in (
                "optical_material",
                "fabrication_constraint",
                "deterministic_selection",
            )
        ),
        bindings=tuple(
            Binding(name, reference_for(name.encode()))
            for name in (
                "optical_material",
                "fabrication_constraint",
                "deterministic_selection",
            )
        ),
    )

    assert any(
        finding.claim == "height_choice"
        and finding.kind is FindingKind.ADVICE
        and finding.needs == ("height_evidence_required",)
        for finding in compiled.findings
    )
    assert not any(
        task.claim
        in {
            "height_choice",
            "propagation_cell_library",
            "jones_library",
            "cell_choice",
            "orientation_relation",
        }
        for task in compiled.ready_tasks
    )


def test_retired_height_advice_schema_has_no_compatibility_reader() -> None:
    with pytest.raises(ValueError, match="height_advice_schema_mismatch"):
        HeightAdvice.from_document(Document("metacraft.advice.height", {}))

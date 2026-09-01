from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
from typing import Literal

from ...authority.protocol import Reference
from ...authority.reference import reference_matches
from ...canonical import encode_bytes, encode_text
from ..consultation import (
    AnswerContract,
    ConsultationAnswer,
    ConsultationCandidate,
    ConsultationGround,
    ConsultationRequest,
    GroundKind,
    Recommendation,
    ResearchMode,
    QuestionKind,
    validate_consultation_answer,
)

from .brief import ControlStrategy, MetalensBrief
from .height import HeightDomain
from .height_advice import HeightAdvice
from .height_advice import HeightRecommendation
from .period import PeriodDomain, validate_period_domain
from .period_advice import PeriodAdvice, PeriodRecommendation
from .propagation_envelope import PhaseEnvelope


@dataclass(frozen=True, slots=True)
class ConsultationUnavailable:
    """
    Report that recorded science has no answer for exact valid grounds.
    """

    question: Literal["period", "height"]


PERIOD_CONSULTATION_REQUEST_SCHEMA = (
    "metacraft.science.metalens.period_consultation_request"
)
HEIGHT_CONSULTATION_REQUEST_SCHEMA = (
    "metacraft.science.metalens.height_consultation_request"
)


class InvalidMetalensConsultationAnswer(ValueError):
    """
    Mark caller-controlled answer contents rejected by one question.
    """

    def __init__(self, question_kind: QuestionKind) -> None:
        """
        Retain the exact question whose answer rule rejected the input.
        """

        if not isinstance(question_kind, QuestionKind):
            raise TypeError("metalens_consultation_question_kind_invalid")
        self.question_kind = question_kind
        super().__init__(
            f"metalens_consultation_answer_invalid:{question_kind.value}"
        )


def form_period_consultation_request(
    brief: MetalensBrief,
    domain: PeriodDomain,
    *,
    research_mode: ResearchMode = ResearchMode.SOURCE_GROUNDED,
) -> ConsultationRequest:
    """
    Form the exact period question from admitted scientific grounds.
    """

    validate_period_consultation(brief, domain)
    if not isinstance(research_mode, ResearchMode):
        raise ValueError("period_consultation_research_mode_invalid")
    assert domain.evidence_reference is not None
    brief_identity = _brief_identity(brief)
    domain_identity = _reference_identity(domain.evidence_reference)
    grounds = (
        ConsultationGround(
            statement=f"working wavelength: {domain.wavelength_nm} nm",
            source_identity=brief_identity,
            kind=GroundKind.FACT,
        ),
        ConsultationGround(
            statement=(
                "sampling ceiling: "
                f"{format(domain.sampling_ceiling_nm, 'f')} nm"
            ),
            source_identity=domain_identity,
            kind=GroundKind.CONSTRAINT,
        ),
        ConsultationGround(
            statement=(
                "order ceiling: "
                f"{format(domain.order_ceiling_nm, 'f')} nm"
            ),
            source_identity=domain_identity,
            kind=GroundKind.CAUTION,
        ),
        ConsultationGround(
            statement=(
                f"legal period limit: {domain.period_limit_nm} nm on a "
                "10 nm grid"
            ),
            source_identity=domain_identity,
            kind=GroundKind.CONSTRAINT,
        ),
    )
    candidates = tuple(
        ConsultationCandidate(quantity=Decimal(period_nm), unit="nm")
        for period_nm in range(10, domain.period_limit_nm + 1, 10)
    )
    cautions = (
        (
            "Candidates at or above the order ceiling require a response method "
            "that retains the opened diffraction channels."
        ),
        (
            "A legal candidate is not evidence of transmission, phase "
            "coverage, or focusing performance."
        ),
    )
    return ConsultationRequest(
        schema_identifier=PERIOD_CONSULTATION_REQUEST_SCHEMA,
        question_kind=QuestionKind.PERIOD,
        research_mode=research_mode,
        brief_identity=brief_identity,
        grounds=grounds,
        candidates=candidates,
        exclusions=(
            "Choose only the cell period; later cell dimensions and shape "
            "remain outside this question.",
        ),
        cautions=cautions,
        answer_contract=AnswerContract(candidate_unit="nm"),
    )


def accept_period_consultation_answer(
    brief: MetalensBrief,
    domain: PeriodDomain,
    request: ConsultationRequest,
    answer: ConsultationAnswer,
) -> PeriodAdvice:
    """
    Validate one closed answer before a period advice record exists.
    """

    expected = form_period_consultation_request(
        brief,
        domain,
        research_mode=request.research_mode,
    )
    if (
        request.schema_identifier != PERIOD_CONSULTATION_REQUEST_SCHEMA
        or request.document().to_bytes() != expected.document().to_bytes()
    ):
        raise ValueError("period_consultation_request_stale")
    try:
        validate_consultation_answer(request, answer)
    except ValueError as error:
        raise InvalidMetalensConsultationAnswer(QuestionKind.PERIOD) from error
    conclusion = answer.conclusion
    if isinstance(conclusion, Recommendation):
        candidate = next(
            item
            for item in request.candidates
            if item.identity == conclusion.candidate_identity
        )
        if (
            candidate.unit != "nm"
            or candidate.quantity != candidate.quantity.to_integral_value()
        ):
            raise ValueError("period_consultation_candidate_invalid")
        period_conclusion = PeriodRecommendation(
            period_nm=int(candidate.quantity),
            reason=conclusion.reason,
            decisive_ground_identities=(
                conclusion.decisive_ground_identities
            ),
            external_claim_identities=(
                conclusion.external_claim_identities
            ),
        )
    else:
        period_conclusion = conclusion
    assert domain.evidence_reference is not None
    return PeriodAdvice(
        brief_identity=request.brief_identity,
        domain_reference=domain.evidence_reference,
        request_identity=request.identity,
        conclusion=period_conclusion,
        grounds=request.grounds,
        external_claims=answer.external_claims,
    )


def form_height_consultation_request(
    brief: MetalensBrief,
    domain: HeightDomain,
    *,
    envelope: PhaseEnvelope | None = None,
    research_mode: ResearchMode = ResearchMode.SOURCE_GROUNDED,
) -> ConsultationRequest:
    """
    Form one height question after the exact period choice is present.
    """

    validate_height_consultation(brief, domain, envelope)
    if not isinstance(research_mode, ResearchMode):
        raise ValueError("height_consultation_research_mode_invalid")
    if not isinstance(brief.control_strategy, ControlStrategy):
        raise ValueError("height_consultation_control_strategy_invalid")
    assert domain.evidence_reference is not None
    domain_identity = _reference_identity(domain.evidence_reference)
    grounds: list[ConsultationGround] = [
        ConsultationGround(
            statement=f"working wavelength: {domain.wavelength_nm} nm",
            source_identity=domain.brief_identity,
            kind=GroundKind.FACT,
        ),
        ConsultationGround(
            statement=f"control strategy: {brief.control_strategy.value}",
            source_identity=domain.brief_identity,
            kind=GroundKind.FACT,
        ),
        ConsultationGround(
            statement=(
                f"selected period: {domain.period_nm} nm; order regime: "
                f"{domain.order_regime}"
            ),
            source_identity=_reference_identity(
                domain.period_choice_reference
            ),
            kind=GroundKind.FACT,
        ),
        ConsultationGround(
            statement=(
                f"aspect limit: {domain.aspect_limit}; dimension step: "
                f"{domain.dimension_step_nm} nm"
            ),
            source_identity=domain_identity,
            kind=GroundKind.CONSTRAINT,
        ),
    ]
    for fabrication in domain.fabrication_ranges:
        if fabrication.height_nm not in domain.heights_nm:
            continue
        grounds.append(
            ConsultationGround(
                statement=(
                    f"height {fabrication.height_nm} nm fabrication range: "
                    f"{fabrication.minimum_feature_nm} to "
                    f"{fabrication.maximum_feature_nm} nm with "
                    f"{fabrication.candidate_count} lateral candidates"
                ),
                source_identity=domain_identity,
                kind=GroundKind.CONSTRAINT,
            )
        )
    if envelope is not None:
        assert envelope.evidence_reference is not None
        envelope_identity = _reference_identity(
            envelope.evidence_reference
        )
        for reach in envelope.reaches:
            if reach.height_nm not in domain.heights_nm:
                continue
            grounds.append(
                ConsultationGround(
                    statement=(
                        f"height {reach.height_nm} nm phase forecast: "
                        f"{encode_text(reach.forecast.as_mapping())}; "
                        "applicability: "
                        f"{encode_text(reach.applicability.as_mapping())}"
                    ),
                    source_identity=envelope_identity,
                    kind=GroundKind.FORECAST,
                )
            )
            grounds.append(
                ConsultationGround(
                    statement=(
                        f"height {reach.height_nm} nm certified standings: "
                        f"{encode_text([item.as_mapping() for item in reach.standings])}"
                    ),
                    source_identity=envelope_identity,
                    kind=GroundKind.CONSTRAINT,
                )
            )
    cautions = [
        f"{caution.concern}: {caution.explanation}"
        for caution in domain.cautions
    ]
    cautions.append(
        "A legal height is not evidence of transmission, phase coverage, "
        "or focusing performance."
    )
    if envelope is not None:
        cautions.append(
            "Phase-envelope model estimates are forecasts; only certified "
            "standings can rule a candidate out."
        )
    else:
        cautions.append(
            "A geometric-phase height does not establish Jones retardance, "
            "polarization conversion, or periodic response."
        )
    candidates = tuple(
        ConsultationCandidate(quantity=Decimal(height_nm), unit="nm")
        for height_nm in domain.heights_nm
    )
    return ConsultationRequest(
        schema_identifier=HEIGHT_CONSULTATION_REQUEST_SCHEMA,
        question_kind=QuestionKind.HEIGHT,
        research_mode=research_mode,
        brief_identity=domain.brief_identity,
        grounds=tuple(grounds),
        candidates=candidates,
        exclusions=(
            "Choose only the atom height; lateral geometry and response "
            "remain outside this question.",
        ),
        cautions=tuple(cautions),
        answer_contract=AnswerContract(candidate_unit="nm"),
    )


def accept_height_consultation_answer(
    brief: MetalensBrief,
    domain: HeightDomain,
    request: ConsultationRequest,
    answer: ConsultationAnswer,
    *,
    envelope: PhaseEnvelope | None = None,
) -> HeightAdvice:
    """
    Validate one closed answer before a height advice record exists.
    """

    expected = form_height_consultation_request(
        brief,
        domain,
        envelope=envelope,
        research_mode=request.research_mode,
    )
    if (
        request.schema_identifier != HEIGHT_CONSULTATION_REQUEST_SCHEMA
        or request.document().to_bytes() != expected.document().to_bytes()
    ):
        raise ValueError("height_consultation_request_stale")
    try:
        validate_consultation_answer(request, answer)
        conclusion = answer.conclusion
        if isinstance(conclusion, Recommendation):
            decisive_ground_identities = set(
                conclusion.decisive_ground_identities
            )
            if any(
                ground.identity in decisive_ground_identities
                and ground.kind
                not in {GroundKind.FACT, GroundKind.CONSTRAINT}
                for ground in request.grounds
            ):
                raise ValueError(
                    "height_consultation_decisive_ground_invalid"
                )
    except ValueError as error:
        raise InvalidMetalensConsultationAnswer(QuestionKind.HEIGHT) from error
    conclusion = answer.conclusion
    if isinstance(conclusion, Recommendation):
        candidate = next(
            item
            for item in request.candidates
            if item.identity == conclusion.candidate_identity
        )
        if (
            candidate.unit != "nm"
            or candidate.quantity != candidate.quantity.to_integral_value()
        ):
            raise ValueError("height_consultation_candidate_invalid")
        height_nm = int(candidate.quantity)
        if envelope is not None:
            standings = envelope.reach_for(height_nm).standings
            if all(
                standing.standing == "ruled out" for standing in standings
            ):
                raise InvalidMetalensConsultationAnswer(QuestionKind.HEIGHT)
        height_conclusion = HeightRecommendation(
            height_nm=height_nm,
            reason=conclusion.reason,
            decisive_ground_identities=(
                conclusion.decisive_ground_identities
            ),
            external_claim_identities=(
                conclusion.external_claim_identities
            ),
        )
    else:
        height_conclusion = conclusion
    assert domain.evidence_reference is not None
    return HeightAdvice(
        brief_identity=request.brief_identity,
        domain_reference=domain.evidence_reference,
        envelope_reference=(
            None if envelope is None else envelope.evidence_reference
        ),
        request_identity=request.identity,
        conclusion=height_conclusion,
        grounds=request.grounds,
        external_claims=answer.external_claims,
    )


def validate_height_consultation(
    brief: MetalensBrief,
    domain: HeightDomain,
    envelope: PhaseEnvelope | None,
) -> None:
    """
    Require admitted height grounds in period-before-height order.
    """

    if domain.evidence_reference is None:
        raise ValueError("height_domain_not_admitted")
    if not reference_matches(
        domain.evidence_reference,
        domain.document().to_bytes(),
    ):
        raise ValueError("height_domain_reference_mismatch")
    if domain.brief_identity != _brief_identity(brief):
        raise ValueError("height_domain_brief_mismatch")
    if brief.control_strategy is ControlStrategy.PROPAGATION_PHASE:
        if envelope is None or envelope.evidence_reference is None:
            raise ValueError("phase_envelope_required")
        if not reference_matches(
            envelope.evidence_reference,
            envelope.document().to_bytes(),
        ):
            raise ValueError("phase_envelope_reference_mismatch")
        if envelope.brief_identity != domain.brief_identity:
            raise ValueError("phase_envelope_brief_mismatch")
        if envelope.height_domain_reference != domain.evidence_reference:
            raise ValueError("phase_envelope_domain_mismatch")
        if tuple(
            sorted(reach.height_nm for reach in envelope.reaches)
        ) != domain.heights_nm:
            raise ValueError("phase_envelope_height_coverage_mismatch")
        return
    if envelope is not None:
        raise ValueError("geometric_phase_envelope_forbidden")


def validate_period_consultation(
    brief: MetalensBrief,
    domain: PeriodDomain,
) -> None:
    """
    Require one admitted, self-matching period domain.
    """

    validate_period_domain(brief, domain)
    if domain.evidence_reference is None:
        raise ValueError("period_domain_not_admitted")
    if not reference_matches(
        domain.evidence_reference,
        domain.document().to_bytes(),
    ):
        raise ValueError("period_domain_reference_mismatch")


def _brief_identity(brief: MetalensBrief) -> str:
    return f"sha256:{hashlib.sha256(brief.canonical_bytes()).hexdigest()}"


def _reference_identity(reference: Reference) -> str:
    encoded = encode_bytes(reference.as_mapping())
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

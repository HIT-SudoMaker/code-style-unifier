from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ...authority import Document, Reference
from ..consultation import (
    ConsultationGround,
    EvidenceRequired,
    ExternalClaim,
)
from ._closed_advice import (
    RecommendationFields,
    _ClosedAdviceDocumentMismatch,
    _ClosedAdviceInvalid,
    require_exact_document_bytes,
    restore_advice_fields,
    validate_advice_fields,
    validate_recommendation_fields,
)


PERIOD_ADVICE_SCHEMA = "metacraft.science.metalens.period_advice"


@dataclass(frozen=True, slots=True, kw_only=True)
class PeriodRecommendation:
    """
    Retain one validated period and the grounds that justified it.
    """

    period_nm: int
    reason: str
    decisive_ground_identities: tuple[str, ...]
    external_claim_identities: tuple[str, ...]

    def __post_init__(self) -> None:
        """
        Reject an incomplete or nonphysical recommendation value.
        """

        try:
            validate_recommendation_fields(
                self.period_nm,
                self.reason,
                self.decisive_ground_identities,
                self.external_claim_identities,
            )
        except _ClosedAdviceInvalid as error:
            raise ValueError("period_recommendation_invalid") from error

    def as_mapping(self) -> dict[str, object]:
        """
        Return the strict durable recommendation value.
        """

        return {
            "decisive_ground_identities": list(
                self.decisive_ground_identities
            ),
            "external_claim_identities": list(
                self.external_claim_identities
            ),
            "kind": "recommendation",
            "period_nm": self.period_nm,
            "reason": self.reason,
        }


PeriodConclusion = PeriodRecommendation | EvidenceRequired


@dataclass(frozen=True, slots=True, kw_only=True)
class PeriodAdvice:
    """
    Retain one validated scientific conclusion and its exact grounds.
    """

    brief_identity: str
    domain_reference: Reference
    request_identity: str
    conclusion: PeriodConclusion
    grounds: tuple[ConsultationGround, ...]
    external_claims: tuple[ExternalClaim, ...]

    def __post_init__(self) -> None:
        """
        Reject advice whose identities or conclusion are internally inconsistent.
        """

        try:
            validate_advice_fields(
                self.brief_identity,
                self.request_identity,
                self.grounds,
                _closed_conclusion(self.conclusion),
                self.external_claims,
            )
        except _ClosedAdviceInvalid as error:
            raise ValueError("period_advice_invalid") from error

    def canonical_value(self) -> dict[str, object]:
        """
        Return the aim-owned value retained inside a generic Study.
        """

        return self.as_mapping()

    def as_mapping(self) -> dict[str, object]:
        """
        Return the exact provider-free period advice value.
        """

        return {
            "brief_identity": self.brief_identity,
            "conclusion": self.conclusion.as_mapping(),
            "domain_reference": self.domain_reference.as_mapping(),
            "external_claims": {
                f"claim_{index:03d}": claim.as_mapping()
                for index, claim in enumerate(self.external_claims, start=1)
            },
            "grounds": {
                f"ground_{index:03d}": ground.as_mapping()
                for index, ground in enumerate(self.grounds, start=1)
            },
            "request_identity": self.request_identity,
        }

    def document(self) -> Document:
        """
        Wrap this advice in its strict Authority document schema.
        """

        return Document(PERIOD_ADVICE_SCHEMA, self.as_mapping())

    @classmethod
    def from_canonical_value(cls, value: object) -> PeriodAdvice:
        """
        Strictly restore the period-owned subtree of one Study.
        """

        if not isinstance(value, Mapping):
            raise ValueError("period_advice_invalid")
        return cls.from_document(Document(PERIOD_ADVICE_SCHEMA, value))

    @classmethod
    def from_document(cls, document: Document) -> PeriodAdvice:
        """
        Restore one exact provider-free period advice document.
        """

        if document.schema_identifier != PERIOD_ADVICE_SCHEMA:
            raise ValueError("period_advice_schema_mismatch")
        try:
            fields = restore_advice_fields(
                document,
                exact_keys=frozenset(
                    {
                        "brief_identity",
                        "conclusion",
                        "domain_reference",
                        "external_claims",
                        "grounds",
                        "request_identity",
                    }
                ),
                recommendation_key="period_nm",
            )
            advice = cls(
                brief_identity=fields.brief_identity,
                domain_reference=fields.domain_reference,
                request_identity=fields.request_identity,
                conclusion=_period_conclusion(fields.conclusion),
                grounds=fields.grounds,
                external_claims=fields.external_claims,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("period_advice_invalid") from error
        try:
            require_exact_document_bytes(advice.document(), document)
        except _ClosedAdviceDocumentMismatch as error:
            raise ValueError("period_advice_document_mismatch") from error
        return advice


def _period_conclusion(
    value: RecommendationFields | EvidenceRequired,
) -> PeriodConclusion:
    if isinstance(value, RecommendationFields):
        return PeriodRecommendation(
            period_nm=value.quantity,
            reason=value.reason,
            decisive_ground_identities=value.decisive_ground_identities,
            external_claim_identities=value.external_claim_identities,
        )
    return value


def _closed_conclusion(
    value: PeriodConclusion,
) -> RecommendationFields | EvidenceRequired:
    if isinstance(value, PeriodRecommendation):
        return RecommendationFields(
            quantity=value.period_nm,
            reason=value.reason,
            decisive_ground_identities=value.decisive_ground_identities,
            external_claim_identities=value.external_claim_identities,
        )
    if isinstance(value, EvidenceRequired):
        return value
    raise _ClosedAdviceInvalid("closed_advice_invalid")

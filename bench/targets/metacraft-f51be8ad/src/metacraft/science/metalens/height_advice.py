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


HEIGHT_ADVICE_SCHEMA = "metacraft.science.metalens.height_advice"


@dataclass(frozen=True, slots=True, kw_only=True)
class HeightRecommendation:
    """
    Retain one validated height and the grounds that justified it.
    """

    height_nm: int
    reason: str
    decisive_ground_identities: tuple[str, ...]
    external_claim_identities: tuple[str, ...]

    def __post_init__(self) -> None:
        """
        Require one positive height and closed evidence identities.
        """

        try:
            validate_recommendation_fields(
                self.height_nm,
                self.reason,
                self.decisive_ground_identities,
                self.external_claim_identities,
            )
        except _ClosedAdviceInvalid as error:
            raise ValueError("height_recommendation_invalid") from error

    def as_mapping(self) -> dict[str, object]:
        """
        Return one closed recommendation value.
        """

        return {
            "decisive_ground_identities": list(
                self.decisive_ground_identities
            ),
            "external_claim_identities": list(
                self.external_claim_identities
            ),
            "height_nm": self.height_nm,
            "kind": "recommendation",
            "reason": self.reason,
        }


HeightConclusion = HeightRecommendation | EvidenceRequired


@dataclass(frozen=True, slots=True, kw_only=True)
class HeightAdvice:
    """
    Retain one validated height conclusion and its exact grounds.
    """

    brief_identity: str
    domain_reference: Reference
    envelope_reference: Reference | None
    request_identity: str
    conclusion: HeightConclusion
    grounds: tuple[ConsultationGround, ...]
    external_claims: tuple[ExternalClaim, ...]

    def __post_init__(self) -> None:
        """
        Require one closed conclusion over unique grounds and claims.
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
            raise ValueError("height_advice_invalid") from error

    def canonical_value(self) -> dict[str, object]:
        """
        Retain the aim-owned advice subtree inside canonical Study bytes.
        """

        return self.as_mapping()

    def as_mapping(self) -> dict[str, object]:
        """
        Return the provider-free scientific record.
        """

        return {
            "brief_identity": self.brief_identity,
            "conclusion": self.conclusion.as_mapping(),
            "domain_reference": self.domain_reference.as_mapping(),
            "envelope_reference": (
                None
                if self.envelope_reference is None
                else self.envelope_reference.as_mapping()
            ),
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
        Wrap the exact advice for Authority admission.
        """

        return Document(HEIGHT_ADVICE_SCHEMA, self.as_mapping())

    @classmethod
    def from_canonical_value(cls, value: object) -> HeightAdvice:
        """
        Strictly restore the Study subtree owned by height consultation.
        """

        if not isinstance(value, Mapping):
            raise ValueError("height_advice_invalid")
        return cls.from_document(Document(HEIGHT_ADVICE_SCHEMA, value))

    @classmethod
    def from_document(cls, document: Document) -> HeightAdvice:
        """
        Restore only the current provider-free height schema.
        """

        if document.schema_identifier != HEIGHT_ADVICE_SCHEMA:
            raise ValueError("height_advice_schema_mismatch")
        try:
            fields = restore_advice_fields(
                document,
                exact_keys=frozenset(
                    {
                        "brief_identity",
                        "conclusion",
                        "domain_reference",
                        "envelope_reference",
                        "external_claims",
                        "grounds",
                        "request_identity",
                    }
                ),
                recommendation_key="height_nm",
            )
            envelope_value = document.values["envelope_reference"]
            advice = cls(
                brief_identity=fields.brief_identity,
                domain_reference=fields.domain_reference,
                envelope_reference=(
                    None
                    if envelope_value is None
                    else Reference.from_mapping(
                        _reference_mapping(envelope_value)
                    )
                ),
                request_identity=fields.request_identity,
                conclusion=_height_conclusion(fields.conclusion),
                grounds=fields.grounds,
                external_claims=fields.external_claims,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("height_advice_invalid") from error
        try:
            require_exact_document_bytes(advice.document(), document)
        except _ClosedAdviceDocumentMismatch as error:
            raise ValueError("height_advice_document_mismatch") from error
        return advice


def _height_conclusion(
    value: RecommendationFields | EvidenceRequired,
) -> HeightConclusion:
    if isinstance(value, RecommendationFields):
        return HeightRecommendation(
            height_nm=value.quantity,
            reason=value.reason,
            decisive_ground_identities=value.decisive_ground_identities,
            external_claim_identities=value.external_claim_identities,
        )
    return value


def _closed_conclusion(
    value: HeightConclusion,
) -> RecommendationFields | EvidenceRequired:
    if isinstance(value, HeightRecommendation):
        return RecommendationFields(
            quantity=value.height_nm,
            reason=value.reason,
            decisive_ground_identities=value.decisive_ground_identities,
            external_claim_identities=value.external_claim_identities,
        )
    if isinstance(value, EvidenceRequired):
        return value
    raise _ClosedAdviceInvalid("closed_advice_invalid")


def _reference_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    return value

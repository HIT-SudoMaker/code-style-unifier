from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ...authority import Document, Reference
from ..consultation import (
    ConsultationGround,
    EvidenceRequired,
    ExternalClaim,
)


class _ClosedAdviceInvalid(ValueError):
    """
    Report one invalid private closed-record structure.
    """


class _ClosedAdviceDocumentMismatch(ValueError):
    """
    Report that a rebuilt public value changed the supplied bytes.
    """


@dataclass(frozen=True, slots=True, kw_only=True)
class RecommendationFields:
    """
    Carry only the structure shared by question-owned recommendations.
    """

    quantity: int
    reason: str
    decisive_ground_identities: tuple[str, ...]
    external_claim_identities: tuple[str, ...]

    def __post_init__(self) -> None:
        """
        Validate the shared recommendation-field contract.

        Raises:
            _ClosedAdviceInvalid: The quantity, reason, or identity closure is
                invalid.
        """

        validate_recommendation_fields(
            self.quantity,
            self.reason,
            self.decisive_ground_identities,
            self.external_claim_identities,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class RestoredAdviceFields:
    """
    Return common strict fields to one question-owned public shell.
    """

    brief_identity: str
    domain_reference: Reference
    request_identity: str
    conclusion: RecommendationFields | EvidenceRequired
    grounds: tuple[ConsultationGround, ...]
    external_claims: tuple[ExternalClaim, ...]


def validate_recommendation_fields(
    quantity: int,
    reason: str,
    decisive_ground_identities: tuple[str, ...],
    external_claim_identities: tuple[str, ...],
) -> None:
    """
    Require one positive quantity and closed supporting identities.

    The contract accepts a positive integer quantity, a non-empty reason, and
    unique non-empty decisive-ground and external-claim identity sequences.
    Invalid fields raise ``_ClosedAdviceInvalid``.
    """

    if (
        not isinstance(quantity, int)
        or isinstance(quantity, bool)
        or quantity <= 0
        or not isinstance(reason, str)
        or not reason.strip()
        or not decisive_ground_identities
        or any(
            not isinstance(identity, str) or not identity.strip()
            for identity in (
                *decisive_ground_identities,
                *external_claim_identities,
            )
        )
        or len(set(decisive_ground_identities))
        != len(decisive_ground_identities)
        or len(set(external_claim_identities))
        != len(external_claim_identities)
    ):
        raise _ClosedAdviceInvalid("closed_recommendation_invalid")


def validate_advice_fields(
    brief_identity: str,
    request_identity: str,
    grounds: tuple[ConsultationGround, ...],
    conclusion: RecommendationFields | EvidenceRequired,
    external_claims: tuple[ExternalClaim, ...],
) -> None:
    """
    Require one closed conclusion over unique grounds and claims.
    """

    if (
        not isinstance(brief_identity, str)
        or not brief_identity.strip()
        or not isinstance(request_identity, str)
        or not request_identity.strip()
        or not grounds
        or any(not isinstance(ground, ConsultationGround) for ground in grounds)
        or any(not isinstance(claim, ExternalClaim) for claim in external_claims)
    ):
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    ground_identities = {ground.identity for ground in grounds}
    claim_identities = {claim.identity for claim in external_claims}
    if (
        len(ground_identities) != len(grounds)
        or len(claim_identities) != len(external_claims)
    ):
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    if isinstance(conclusion, RecommendationFields):
        if not set(conclusion.decisive_ground_identities) <= ground_identities:
            raise _ClosedAdviceInvalid("closed_advice_invalid")
        if set(conclusion.external_claim_identities) != claim_identities:
            raise _ClosedAdviceInvalid("closed_advice_invalid")
    elif isinstance(conclusion, EvidenceRequired):
        if external_claims:
            raise _ClosedAdviceInvalid("closed_advice_invalid")
    else:
        raise _ClosedAdviceInvalid("closed_advice_invalid")


def restore_advice_fields(
    document: Document,
    *,
    exact_keys: frozenset[str],
    recommendation_key: str,
) -> RestoredAdviceFields:
    """
    Strictly decode the common fields of one question-owned document.
    """

    values = document.values
    if set(values) != exact_keys:
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    try:
        external_claims = tuple(
            ExternalClaim.from_mapping(item)
            for item in _indexed_values(values["external_claims"], "claim")
        )
        conclusion = _restore_conclusion(
            values["conclusion"],
            recommendation_key=recommendation_key,
        )
        fields = RestoredAdviceFields(
            brief_identity=_text(values["brief_identity"]),
            domain_reference=Reference.from_mapping(
                _mapping(values["domain_reference"])
            ),
            request_identity=_text(values["request_identity"]),
            conclusion=conclusion,
            grounds=tuple(
                ConsultationGround.from_mapping(item)
                for item in _indexed_values(values["grounds"], "ground")
            ),
            external_claims=external_claims,
        )
        validate_advice_fields(
            fields.brief_identity,
            fields.request_identity,
            fields.grounds,
            fields.conclusion,
            fields.external_claims,
        )
        return fields
    except _ClosedAdviceInvalid:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise _ClosedAdviceInvalid("closed_advice_invalid") from error


def require_exact_document_bytes(actual: Document, expected: Document) -> None:
    """
    Require a rebuilt question-owned document to preserve exact bytes.
    """

    if actual.to_bytes() != expected.to_bytes():
        raise _ClosedAdviceDocumentMismatch("closed_advice_document_mismatch")


def _restore_conclusion(
    value: object,
    *,
    recommendation_key: str,
) -> RecommendationFields | EvidenceRequired:
    if not isinstance(value, Mapping):
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    kind = value.get("kind")
    if kind == "recommendation":
        if set(value) != {
            "decisive_ground_identities",
            "external_claim_identities",
            "kind",
            recommendation_key,
            "reason",
        }:
            raise _ClosedAdviceInvalid("closed_advice_invalid")
        quantity = value[recommendation_key]
        if not isinstance(quantity, int) or isinstance(quantity, bool):
            raise _ClosedAdviceInvalid("closed_advice_invalid")
        return RecommendationFields(
            quantity=quantity,
            reason=_text(value["reason"]),
            decisive_ground_identities=_text_list(
                value["decisive_ground_identities"]
            ),
            external_claim_identities=_text_list(
                value["external_claim_identities"]
            ),
        )
    if kind == "evidence_required":
        if set(value) != {"kind", "missing_fact", "reason"}:
            raise _ClosedAdviceInvalid("closed_advice_invalid")
        return EvidenceRequired(
            missing_fact=_text(value["missing_fact"]),
            reason=_text(value["reason"]),
        )
    raise _ClosedAdviceInvalid("closed_advice_invalid")


def _indexed_values(value: object, prefix: str) -> tuple[object, ...]:
    if not isinstance(value, Mapping):
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    expected = [
        f"{prefix}_{index:03d}" for index in range(1, len(value) + 1)
    ]
    if list(value) != expected:
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    return tuple(value[key] for key in expected)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    return value


def _text_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    result = tuple(_text(item) for item in value)
    if len(set(result)) != len(result):
        raise _ClosedAdviceInvalid("closed_advice_invalid")
    return result

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
from typing import TypeVar
from urllib.parse import urlsplit

from ..authority import Document
from ..canonical import encode_bytes


CONSULTATION_ANSWER_SCHEMA = "metacraft.science.consultation_answer"
_IndexedValue = TypeVar("_IndexedValue")


class QuestionKind(str, Enum):
    """
    Name the scientific quantity requested by one consultation.
    """

    PERIOD = "period"
    HEIGHT = "height"


class ResearchMode(str, Enum):
    """
    Declare whether an answer may introduce sourced external claims.
    """

    CLOSED_BOOK = "closed_book"
    SOURCE_GROUNDED = "source_grounded"


class GroundKind(str, Enum):
    """
    Classify one request-owned proposition by its evidential role.
    """

    FACT = "fact"
    CONSTRAINT = "constraint"
    FORECAST = "forecast"
    CAUTION = "caution"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsultationGround:
    """
    Carry one identified proposition supplied by a consultation request.
    """

    statement: str
    source_identity: str
    kind: GroundKind

    def __post_init__(self) -> None:
        """
        Reject incomplete text or an unknown ground classification.
        """

        _require_text(self.statement)
        _require_text(self.source_identity)
        if not isinstance(self.kind, GroundKind):
            raise ValueError("consultation_ground_invalid")

    @property
    def identity(self) -> str:
        """
        Return the canonical identity of this ground's defining value.
        """

        return _identity(self._identity_value())

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the ground with its canonical identity.
        """

        return {"identity": self.identity, **self._identity_value()}

    def _identity_value(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "source_identity": self.source_identity,
            "statement": self.statement,
        }

    @classmethod
    def from_mapping(cls, value: object) -> ConsultationGround:
        """
        Restore one exact ground from its closed mapping contract.
        """

        values = _closed_mapping(
            value,
            {"identity", "kind", "source_identity", "statement"},
            "consultation_ground_invalid",
        )
        try:
            ground = cls(
                statement=_require_text(values["statement"]),
                source_identity=_require_text(values["source_identity"]),
                kind=GroundKind(_require_text(values["kind"])),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("consultation_ground_invalid") from error
        if values["identity"] != ground.identity:
            raise ValueError("consultation_ground_invalid")
        return ground


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsultationCandidate:
    """
    Name one positive finite quantity admitted as an answer candidate.
    """

    quantity: Decimal
    unit: str

    def __post_init__(self) -> None:
        """
        Reject non-positive, non-finite, or unitless candidates.
        """

        if (
            not isinstance(self.quantity, Decimal)
            or not self.quantity.is_finite()
            or self.quantity <= 0
        ):
            raise ValueError("consultation_candidate_invalid")
        _require_text(self.unit)

    @property
    def identity(self) -> str:
        """
        Return the canonical identity of this candidate quantity.
        """

        return _identity(self._identity_value())

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the candidate with its canonical identity.
        """

        return {"identity": self.identity, **self._identity_value()}

    def _identity_value(self) -> dict[str, object]:
        return {"quantity": format(self.quantity, "f"), "unit": self.unit}

    @classmethod
    def from_mapping(cls, value: object) -> ConsultationCandidate:
        """
        Restore one exact candidate from its closed mapping contract.
        """

        values = _closed_mapping(
            value,
            {"identity", "quantity", "unit"},
            "consultation_candidate_invalid",
        )
        try:
            candidate = cls(
                quantity=Decimal(_require_text(values["quantity"])),
                unit=_require_text(values["unit"]),
            )
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("consultation_candidate_invalid") from error
        if values["identity"] != candidate.identity:
            raise ValueError("consultation_candidate_invalid")
        return candidate


@dataclass(frozen=True, slots=True, kw_only=True)
class AnswerContract:
    """
    Describe the closed document shape accepted for one answer.
    """

    candidate_unit: str

    def __post_init__(self) -> None:
        """
        Require the unit used by every recommendation candidate.
        """

        _require_text(self.candidate_unit)

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the complete answer-document contract.
        """

        return {
            "candidate_unit": self.candidate_unit,
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
                    "statement with sorted keys, no whitespace, and "
                    "unescaped Unicode"
                ),
                "index_format": "claim_001, claim_002, ...",
                "locator_rule": "absolute https URL or doi:<non-empty>",
                "member_fields": ["identity", "locator", "statement"],
            },
            "requires_concise_reason": True,
            "schema_identifier": CONSULTATION_ANSWER_SCHEMA,
        }

    @classmethod
    def from_mapping(cls, value: object) -> AnswerContract:
        """
        Restore an answer contract only from its exact canonical mapping.
        """

        values = _closed_mapping(
            value,
            {
                "candidate_unit",
                "conclusions",
                "document_fields",
                "external_claims",
                "requires_concise_reason",
                "schema_identifier",
            },
            "answer_contract_invalid",
        )
        contract = cls(
            candidate_unit=_require_text(values["candidate_unit"])
        )
        if dict(values) != contract.as_mapping():
            raise ValueError("answer_contract_invalid")
        return contract


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsultationRequest:
    """
    Pose one identified scientific choice over closed grounds and candidates.
    """

    schema_identifier: str
    question_kind: QuestionKind
    research_mode: ResearchMode
    brief_identity: str
    grounds: tuple[ConsultationGround, ...]
    candidates: tuple[ConsultationCandidate, ...]
    exclusions: tuple[str, ...]
    cautions: tuple[str, ...]
    answer_contract: AnswerContract

    def __post_init__(self) -> None:
        """
        Enforce a complete, unique, and unit-consistent request.
        """

        _require_text(self.schema_identifier)
        _require_text(self.brief_identity)
        if not isinstance(self.question_kind, QuestionKind):
            raise ValueError("consultation_request_invalid")
        if not isinstance(self.research_mode, ResearchMode):
            raise ValueError("consultation_request_invalid")
        if not self.grounds or not self.candidates:
            raise ValueError("consultation_request_invalid")
        _require_unique(tuple(item.identity for item in self.grounds))
        _require_unique(tuple(item.identity for item in self.candidates))
        if any(
            candidate.unit != self.answer_contract.candidate_unit
            for candidate in self.candidates
        ):
            raise ValueError("consultation_request_invalid")
        _require_text_tuple(self.exclusions)
        _require_text_tuple(self.cautions)

    @property
    def identity(self) -> str:
        """
        Return the canonical identity of the request-owned question.
        """

        return _identity(self._identity_value())

    def document(self) -> Document:
        """
        Encode the request as its canonical Authority document.
        """

        return Document(
            self.schema_identifier,
            {"identity": self.identity, **self._identity_value()},
        )

    def _identity_value(self) -> dict[str, object]:
        return {
            "answer_contract": self.answer_contract.as_mapping(),
            "brief_identity": self.brief_identity,
            "candidates": _indexed(
                self.candidates,
                "candidate",
                lambda item: item.as_mapping(),
            ),
            "cautions": list(self.cautions),
            "exclusions": list(self.exclusions),
            "grounds": _indexed(
                self.grounds,
                "ground",
                lambda item: item.as_mapping(),
            ),
            "question_kind": self.question_kind.value,
            "research_mode": self.research_mode.value,
        }

    @classmethod
    def from_document(cls, document: Document) -> ConsultationRequest:
        """
        Restore a request only from its exact canonical document.
        """

        values = _closed_mapping(
            document.values,
            {
                "answer_contract",
                "brief_identity",
                "candidates",
                "cautions",
                "exclusions",
                "grounds",
                "identity",
                "question_kind",
                "research_mode",
            },
            "consultation_request_invalid",
        )
        try:
            request = cls(
                schema_identifier=document.schema_identifier,
                question_kind=QuestionKind(
                    _require_text(values["question_kind"])
                ),
                research_mode=ResearchMode(
                    _require_text(values["research_mode"])
                ),
                brief_identity=_require_text(values["brief_identity"]),
                grounds=tuple(
                    ConsultationGround.from_mapping(item)
                    for item in _indexed_values(values["grounds"], "ground")
                ),
                candidates=tuple(
                    ConsultationCandidate.from_mapping(item)
                    for item in _indexed_values(values["candidates"], "candidate")
                ),
                exclusions=_text_sequence(values["exclusions"]),
                cautions=_text_sequence(values["cautions"]),
                answer_contract=AnswerContract.from_mapping(
                    values["answer_contract"]
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("consultation_request_invalid") from error
        if values["identity"] != request.identity:
            raise ValueError("consultation_request_invalid")
        if request.document().to_bytes() != document.to_bytes():
            raise ValueError("consultation_request_invalid")
        return request


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalClaim:
    """
    Carry one identified externally sourced proposition and locator.
    """

    statement: str
    locator: str

    def __post_init__(self) -> None:
        """
        Require complete claim text and an accepted absolute locator.
        """

        _require_text(self.statement)
        _require_locator(self.locator)

    @property
    def identity(self) -> str:
        """
        Return the canonical identity of this external claim.
        """

        return _identity(self._identity_value())

    def as_mapping(self) -> dict[str, object]:
        """
        Encode the external claim with its canonical identity.
        """

        return {"identity": self.identity, **self._identity_value()}

    def _identity_value(self) -> dict[str, object]:
        return {"locator": self.locator, "statement": self.statement}

    @classmethod
    def from_mapping(cls, value: object) -> ExternalClaim:
        """
        Restore one exact external claim from its closed mapping.
        """

        values = _closed_mapping(
            value,
            {"identity", "locator", "statement"},
            "external_claim_invalid",
        )
        try:
            claim = cls(
                statement=_require_text(values["statement"]),
                locator=_require_text(values["locator"]),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("external_claim_invalid") from error
        if values["identity"] != claim.identity:
            raise ValueError("external_claim_invalid")
        return claim


@dataclass(frozen=True, slots=True, kw_only=True)
class Recommendation:
    """
    Select one candidate and close its decisive evidence references.
    """

    candidate_identity: str
    reason: str
    decisive_ground_identities: tuple[str, ...]
    external_claim_identities: tuple[str, ...]

    def __post_init__(self) -> None:
        """
        Require one candidate, reason, and at least one decisive ground.
        """

        _require_text(self.candidate_identity)
        _require_text(self.reason)
        if not self.decisive_ground_identities:
            raise ValueError("recommendation_invalid")
        _require_text_tuple(self.decisive_ground_identities)
        _require_text_tuple(self.external_claim_identities)

    def as_mapping(self) -> dict[str, object]:
        """
        Encode this recommendation as a closed conclusion mapping.
        """

        return {
            "candidate_identity": self.candidate_identity,
            "decisive_ground_identities": list(
                self.decisive_ground_identities
            ),
            "external_claim_identities": list(
                self.external_claim_identities
            ),
            "kind": "recommendation",
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceRequired:
    """
    Stop a consultation when a named fact is still missing.
    """

    missing_fact: str
    reason: str

    def __post_init__(self) -> None:
        """
        Require the missing fact and the reason work cannot continue.
        """

        _require_text(self.missing_fact)
        _require_text(self.reason)

    def as_mapping(self) -> dict[str, object]:
        """
        Encode this evidence request as a closed conclusion mapping.
        """

        return {
            "kind": "evidence_required",
            "missing_fact": self.missing_fact,
            "reason": self.reason,
        }


ConsultationConclusion = Recommendation | EvidenceRequired


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsultationAnswer:
    """
    Close one request with a recommendation or an evidence requirement.
    """

    request_identity: str
    conclusion: ConsultationConclusion
    external_claims: tuple[ExternalClaim, ...]

    def __post_init__(self) -> None:
        """
        Require one recognized conclusion and unique external claims.
        """

        _require_text(self.request_identity)
        if not isinstance(self.conclusion, (Recommendation, EvidenceRequired)):
            raise ValueError("consultation_answer_invalid")
        _require_unique(tuple(claim.identity for claim in self.external_claims))

    def document(self) -> Document:
        """
        Encode the answer as its canonical Authority document.
        """

        return Document(
            CONSULTATION_ANSWER_SCHEMA,
            {
                "conclusion": self.conclusion.as_mapping(),
                "external_claims": _indexed(
                    self.external_claims,
                    "claim",
                    lambda item: item.as_mapping(),
                ),
                "request_identity": self.request_identity,
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> ConsultationAnswer:
        """
        Restore an answer only from its exact canonical document.
        """

        if document.schema_identifier != CONSULTATION_ANSWER_SCHEMA:
            raise ValueError("consultation_answer_schema_mismatch")
        values = _closed_mapping(
            document.values,
            {"conclusion", "external_claims", "request_identity"},
            "consultation_answer_invalid",
        )
        try:
            answer = cls(
                request_identity=_require_text(values["request_identity"]),
                conclusion=_conclusion(values["conclusion"]),
                external_claims=tuple(
                    ExternalClaim.from_mapping(item)
                    for item in _indexed_values(values["external_claims"], "claim")
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("consultation_answer_invalid") from error
        if answer.document().to_bytes() != document.to_bytes():
            raise ValueError("consultation_answer_invalid")
        return answer


def validate_consultation_answer(
    request: ConsultationRequest,
    answer: ConsultationAnswer,
) -> None:
    """
    Validate answer closure against the exact request it cites.
    """

    if answer.request_identity != request.identity:
        raise ValueError("consultation_answer_request_mismatch")
    claims = {claim.identity: claim for claim in answer.external_claims}
    if request.research_mode is ResearchMode.CLOSED_BOOK and claims:
        raise ValueError("consultation_answer_external_claim_forbidden")
    if isinstance(answer.conclusion, EvidenceRequired):
        if claims:
            raise ValueError("consultation_answer_external_claim_surplus")
        return
    conclusion = answer.conclusion
    if conclusion.candidate_identity not in {
        candidate.identity for candidate in request.candidates
    }:
        raise ValueError("consultation_answer_candidate_unknown")
    if not set(conclusion.decisive_ground_identities) <= {
        ground.identity for ground in request.grounds
    }:
        raise ValueError("consultation_answer_ground_unknown")
    if set(conclusion.external_claim_identities) != set(claims):
        raise ValueError("consultation_answer_external_claim_closure_invalid")


def _conclusion(value: object) -> ConsultationConclusion:
    if not isinstance(value, Mapping):
        raise ValueError("consultation_answer_invalid")
    kind = value.get("kind")
    if kind == "recommendation":
        values = _closed_mapping(
            value,
            {
                "candidate_identity",
                "decisive_ground_identities",
                "external_claim_identities",
                "kind",
                "reason",
            },
            "consultation_answer_invalid",
        )
        return Recommendation(
            candidate_identity=_require_text(values["candidate_identity"]),
            reason=_require_text(values["reason"]),
            decisive_ground_identities=_text_sequence(
                values["decisive_ground_identities"]
            ),
            external_claim_identities=_text_sequence(
                values["external_claim_identities"]
            ),
        )
    if kind == "evidence_required":
        values = _closed_mapping(
            value,
            {"kind", "missing_fact", "reason"},
            "consultation_answer_invalid",
        )
        return EvidenceRequired(
            missing_fact=_require_text(values["missing_fact"]),
            reason=_require_text(values["reason"]),
        )
    raise ValueError("consultation_answer_invalid")


def _identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(encode_bytes(value)).hexdigest()}"


def _closed_mapping(
    value: object,
    keys: set[str],
    finding: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(finding)
    return value


def _require_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("consultation_text_invalid")
    return value


def _require_text_tuple(values: tuple[str, ...]) -> None:
    if not isinstance(values, tuple):
        raise ValueError("consultation_sequence_invalid")
    for value in values:
        _require_text(value)
    _require_unique(values)


def _text_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError("consultation_sequence_invalid")
    result = tuple(_require_text(item) for item in value)
    _require_unique(result)
    return result


def _require_unique(values: tuple[str, ...]) -> None:
    if len(set(values)) != len(values):
        raise ValueError("consultation_identity_duplicate")


def _indexed(
    values: Iterable[_IndexedValue],
    prefix: str,
    encode: Callable[[_IndexedValue], object],
) -> dict[str, object]:
    return {
        f"{prefix}_{index:03d}": encode(value)
        for index, value in enumerate(values, start=1)
    }


def _indexed_values(value: object, prefix: str) -> tuple[object, ...]:
    if not isinstance(value, Mapping):
        raise ValueError("consultation_index_invalid")
    expected = [
        f"{prefix}_{index:03d}" for index in range(1, len(value) + 1)
    ]
    if list(value) != expected:
        raise ValueError("consultation_index_invalid")
    return tuple(value[key] for key in expected)


def _require_locator(locator: str) -> None:
    if locator.startswith("doi:") and locator[4:].strip():
        return
    parsed = urlsplit(locator)
    if parsed.scheme == "https" and parsed.netloc and parsed.hostname:
        return
    raise ValueError("external_claim_locator_invalid")

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any, cast

import pytest

from metacraft.authority import Document, reference_for
from metacraft.science.consultation import (
    ConsultationGround,
    EvidenceRequired,
    ExternalClaim,
    GroundKind,
)
from metacraft.science.metalens.height_advice import (
    HEIGHT_ADVICE_SCHEMA,
    HeightAdvice,
    HeightRecommendation,
)
from metacraft.science.metalens.period_advice import (
    PERIOD_ADVICE_SCHEMA,
    PeriodAdvice,
    PeriodRecommendation,
)


@dataclass(frozen=True, slots=True)
class AdviceCase:
    name: str
    advice_type: type[PeriodAdvice] | type[HeightAdvice]
    recommendation_type: type[PeriodRecommendation] | type[HeightRecommendation]
    quantity_name: str
    quantity: int
    schema: str
    recommendation_reason: str
    advice_reason: str
    document_mismatch_reason: str


CASES = (
    AdviceCase(
        name="period",
        advice_type=PeriodAdvice,
        recommendation_type=PeriodRecommendation,
        quantity_name="period_nm",
        quantity=400,
        schema=PERIOD_ADVICE_SCHEMA,
        recommendation_reason="period_recommendation_invalid",
        advice_reason="period_advice_invalid",
        document_mismatch_reason="period_advice_document_mismatch",
    ),
    AdviceCase(
        name="height",
        advice_type=HeightAdvice,
        recommendation_type=HeightRecommendation,
        quantity_name="height_nm",
        quantity=500,
        schema=HEIGHT_ADVICE_SCHEMA,
        recommendation_reason="height_recommendation_invalid",
        advice_reason="height_advice_invalid",
        document_mismatch_reason="height_advice_document_mismatch",
    ),
)


def _ground() -> ConsultationGround:
    return ConsultationGround(
        statement="One admitted constraint.",
        source_identity="sha256:source",
        kind=GroundKind.CONSTRAINT,
    )


def _recommendation(case: AdviceCase):
    ground = _ground()
    return case.recommendation_type(
        **{
            case.quantity_name: case.quantity,
            "reason": "Use the admitted constraint.",
            "decisive_ground_identities": (ground.identity,),
            "external_claim_identities": (),
        }
    )


def _advice(
    case: AdviceCase,
    *,
    conclusion: object | None = None,
    envelope: bool = False,
    external_claims: tuple[ExternalClaim, ...] = (),
):
    values: dict[str, object] = {
        "brief_identity": "sha256:brief",
        "domain_reference": reference_for(b"closed-advice-domain"),
        "request_identity": "sha256:request",
        "conclusion": _recommendation(case) if conclusion is None else conclusion,
        "grounds": (_ground(),),
        "external_claims": external_claims,
    }
    if case.name == "height":
        values["envelope_reference"] = (
            reference_for(b"closed-advice-envelope") if envelope else None
        )
    return cast(Any, case.advice_type)(**values)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
@pytest.mark.parametrize(
    ("reason", "ground_identities", "claim_identities"),
    (
        pytest.param(None, ("ground",), (), id="reason_not_text"),
        pytest.param("", ("ground",), (), id="reason_blank"),
        pytest.param("reason", (), (), id="ground_empty"),
        pytest.param("reason", ("",), (), id="ground_blank"),
        pytest.param("reason", ("ground", "ground"), (), id="ground_duplicate"),
        pytest.param("reason", ("ground",), ("",), id="claim_blank"),
        pytest.param("reason", ("ground",), ("claim", "claim"), id="claim_duplicate"),
    ),
)
def test_recommendation_direct_construction_rejects_open_values(
    case: AdviceCase,
    reason: object,
    ground_identities: tuple[str, ...],
    claim_identities: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match=f"^{case.recommendation_reason}$"):
        case.recommendation_type(
            **{
                case.quantity_name: case.quantity,
                "reason": cast(str, reason),
                "decisive_ground_identities": ground_identities,
                "external_claim_identities": claim_identities,
            }
        )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
@pytest.mark.parametrize(
    ("field", "value"),
    (
        pytest.param("brief_identity", None, id="brief_not_text"),
        pytest.param("request_identity", None, id="request_not_text"),
        pytest.param("grounds", (object(),), id="ground_wrong_type"),
        pytest.param("external_claims", (object(),), id="claim_wrong_type"),
    ),
)
def test_advice_direct_construction_rejects_open_values(
    case: AdviceCase,
    field: str,
    value: object,
) -> None:
    advice = _advice(case)

    with pytest.raises(ValueError, match=f"^{case.advice_reason}$"):
        replace(advice, **{field: cast(Any, value)})


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_evidence_required_rejects_external_claims(case: AdviceCase) -> None:
    claim = ExternalClaim(
        statement="An external claim.",
        locator="https://example.com/closed-advice",
    )
    advice = _advice(
        case,
        conclusion=EvidenceRequired(
            missing_fact="missing evidence",
            reason="Selection is unsafe.",
        ),
    )

    with pytest.raises(ValueError, match=f"^{case.advice_reason}$"):
        replace(advice, external_claims=(claim,))

    values = cast(dict[str, object], deepcopy(dict(advice.document().values)))
    values["external_claims"] = {"claim_001": claim.as_mapping()}
    with pytest.raises(ValueError, match=f"^{case.advice_reason}$"):
        case.advice_type.from_document(Document(case.schema, values))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_recommendation_closes_external_claims(case: AdviceCase) -> None:
    claim = ExternalClaim(
        statement="An external claim.",
        locator="https://example.com/closed-advice",
    )
    ground = _ground()
    recommendation = case.recommendation_type(
        **{
            case.quantity_name: case.quantity,
            "reason": "Use the admitted constraint and cited claim.",
            "decisive_ground_identities": (ground.identity,),
            "external_claim_identities": (claim.identity,),
        }
    )
    advice = _advice(
        case,
        conclusion=recommendation,
        external_claims=(claim,),
    )

    assert case.advice_type.from_document(advice.document()) == advice


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_recommendation_and_evidence_required_round_trip_exactly(
    case: AdviceCase,
) -> None:
    recommendation = _advice(case)
    evidence_required = _advice(
        case,
        conclusion=EvidenceRequired(
            missing_fact=f"{case.name} evidence",
            reason="Selection is unsafe.",
        ),
        envelope=case.name == "height",
    )

    assert case.advice_type.from_document(recommendation.document()) == recommendation
    assert case.advice_type.from_canonical_value(
        evidence_required.canonical_value()
    ) == evidence_required


@pytest.mark.parametrize(
    ("case", "conclusion", "envelope", "expected_reference"),
    (
        pytest.param(
            CASES[0],
            "recommendation",
            False,
            {
                "content_hash": "sha256:3d465a651650011e4487d9134d9c871eafaf086db3634a7e202b459b4c35c39b",
                "media_type": "application/json",
                "metadata_content_hash": "sha256:003df38408083f6a10fe3aa7d56046edf5f4a58ffcc4f48810c2fa9d7163d45f",
                "size_bytes": 856,
            },
            id="period-recommendation",
        ),
        pytest.param(
            CASES[0],
            "evidence_required",
            False,
            {
                "content_hash": "sha256:6eaa04a882b8721a98c0594a34c886e1976becad94042da43568f17a13af4b37",
                "media_type": "application/json",
                "metadata_content_hash": "sha256:c7ec92df188db5466aa5f777feeccb154c9300689e0a9dd5b95c79884a4ed07d",
                "size_bytes": 732,
            },
            id="period-evidence-required",
        ),
        pytest.param(
            CASES[1],
            "recommendation",
            False,
            {
                "content_hash": "sha256:d3cf2b5f40e94b0d44813e5e8c2ab0d5648c5424b10c00396c74da0416f3ec79",
                "media_type": "application/json",
                "metadata_content_hash": "sha256:6fcc28bce5241c7d5200ffa166924a11d50a893ecca21a1739e54b0e62371f0b",
                "size_bytes": 882,
            },
            id="height-recommendation-without-envelope",
        ),
        pytest.param(
            CASES[1],
            "evidence_required",
            True,
            {
                "content_hash": "sha256:eb40aa230669696e9b6a20c979545212359e13e36d160a452a0502ea5c930fe8",
                "media_type": "application/json",
                "metadata_content_hash": "sha256:569db611e6b6bf04b4edffee0d399dd82eb4412dbfd1f749b71a5ded771ca333",
                "size_bytes": 990,
            },
            id="height-evidence-required-with-envelope",
        ),
    ),
)
def test_advice_document_references_are_frozen(
    case: AdviceCase,
    conclusion: str,
    envelope: bool,
    expected_reference: dict[str, object],
) -> None:
    advice = _advice(
        case,
        conclusion=(
            None
            if conclusion == "recommendation"
            else EvidenceRequired(
                missing_fact=f"{case.name} evidence",
                reason="Selection is unsafe.",
            )
        ),
        envelope=envelope,
    )

    assert reference_for(advice.document().to_bytes()).as_mapping() == (
        expected_reference
    )


def _mutated_document(case: AdviceCase, mutation: str) -> Document:
    values = cast(
        dict[str, object],
        deepcopy(dict(_advice(case).document().values)),
    )
    conclusion = cast(dict[str, object], values["conclusion"])
    if mutation == "quantity_not_integer":
        conclusion[case.quantity_name] = "400"
    elif mutation == "quantity_boolean":
        conclusion[case.quantity_name] = True
    elif mutation == "quantity_nonpositive":
        conclusion[case.quantity_name] = 0
    elif mutation == "reason_blank":
        conclusion["reason"] = ""
    elif mutation == "ground_duplicate":
        ground = cast(list[str], conclusion["decisive_ground_identities"])[0]
        conclusion["decisive_ground_identities"] = [ground, ground]
    elif mutation == "unknown_kind":
        conclusion["kind"] = "other"
    elif mutation == "missing_key":
        del values["request_identity"]
    elif mutation == "extra_key":
        values["extra"] = "not allowed"
    elif mutation == "malformed_index":
        grounds = cast(dict[str, object], values["grounds"])
        grounds["ground_002"] = grounds.pop("ground_001")
    elif mutation == "wrong_reference":
        values["domain_reference"] = {"content_hash": "sha256:missing"}
    elif mutation == "open_ground":
        grounds = cast(dict[str, object], values["grounds"])
        ground = cast(dict[str, object], grounds["ground_001"])
        del ground["statement"]
    elif mutation == "open_claim":
        conclusion["external_claim_identities"] = ["sha256:invented-claim"]
    else:
        raise AssertionError(mutation)
    return Document(case.schema, values)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
@pytest.mark.parametrize(
    "mutation",
    (
        "quantity_not_integer",
        "quantity_boolean",
        "quantity_nonpositive",
        "reason_blank",
        "ground_duplicate",
        "unknown_kind",
        "missing_key",
        "extra_key",
        "malformed_index",
        "wrong_reference",
        "open_ground",
        "open_claim",
    ),
)
def test_advice_document_rejects_open_values(
    case: AdviceCase,
    mutation: str,
) -> None:
    with pytest.raises(ValueError, match=f"^{case.advice_reason}$"):
        case.advice_type.from_document(_mutated_document(case, mutation))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_advice_schema_mismatch_keeps_question_owner(case: AdviceCase) -> None:
    with pytest.raises(ValueError, match=f"^{case.name}_advice_schema_mismatch$"):
        case.advice_type.from_document(Document("metacraft.foreign.advice", {}))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_advice_document_mismatch_keeps_question_owner(case: AdviceCase) -> None:
    advice = _advice(case)

    class ChangedBytesDocument(Document):
        def to_bytes(self) -> bytes:
            return super().to_bytes() + b" "

    changed = ChangedBytesDocument(case.schema, advice.document().values)

    with pytest.raises(ValueError, match=f"^{case.document_mismatch_reason}$"):
        case.advice_type.from_document(changed)

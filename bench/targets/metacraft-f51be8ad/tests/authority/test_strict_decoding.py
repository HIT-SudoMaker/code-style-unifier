"""
Strict decoder tests for the Python authority Adapter seam.

These tests prove the Adapter accepts only the exact schema, primitive types,
references, timestamps, and permit relationships Rust can emit, and rejects
every malformed imitation at the seam with no coercion.

The golden valid mapping is the real Rust protocol fixture view, so a round
trip through the public Python ``AuthorityView`` decoder is proven against
bytes the native extension actually emits.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from metacraft.authority import (
    AdmittedDecision,
    Authority,
    AuthorityView,
    CheckReport,
    Current,
    Decision,
    Document,
    Permit,
    Proposal,
    Reference,
    Revision,
)
from metacraft.canonical import encode_bytes

FIXTURE = (
    Path(__file__).parents[2]
    / "rust"
    / "tests"
    / "fixtures"
    / "authority_protocol.json"
)

#: A reference mapping in the exact form Rust emits on the wire.
VALID_REFERENCE: dict[str, Any] = {
    "content_hash": "sha256:" + "0d" * 32,
    "media_type": "application/json",
    "metadata_content_hash": "sha256:" + "1e" * 32,
    "size_bytes": 4,
}

PROPOSAL_MEDIA_TYPE = "application/vnd.metacraft.authority.proposal+json"


@pytest.mark.parametrize("source", (b"null", b"[]", b'"document"'))
def test_document_decoder_rejects_non_mapping_json_with_stable_shape_error(
    source: bytes,
) -> None:
    with pytest.raises(ValueError, match="^document_shape_invalid$"):
        Document.from_bytes(source)


def _proposal_metadata_hash(
    content_hash: str,
    *,
    size_bytes: int,
) -> str:
    metadata = {
        "content_hash": content_hash,
        "descriptive_metadata": {"object_kind": "Proposal"},
        "media_type": PROPOSAL_MEDIA_TYPE,
        "size_bytes": size_bytes,
    }
    return f"sha256:{hashlib.sha256(encode_bytes(metadata)).hexdigest()}"


VALID_PROPOSAL_REFERENCE: dict[str, Any] = {
    "content_hash": "sha256:" + "5" * 64,
    "media_type": PROPOSAL_MEDIA_TYPE,
    "metadata_content_hash": _proposal_metadata_hash(
        "sha256:" + "5" * 64,
        size_bytes=32,
    ),
    "size_bytes": 32,
}

VALID_PERMIT_RECEIPT_REFERENCE: dict[str, Any] = {
    "content_hash": "sha256:" + "ab" * 32,
    "media_type": PROPOSAL_MEDIA_TYPE,
    "metadata_content_hash": _proposal_metadata_hash(
        "sha256:" + "ab" * 32,
        size_bytes=32,
    ),
    "size_bytes": 32,
}

VALID_PERMIT_RECEIPT_BODY_REFERENCE: dict[str, Any] = {
    "content_hash": "sha256:" + "ef" * 32,
    "media_type": "application/json",
    "metadata_content_hash": "sha256:" + "12" * 32,
    "size_bytes": 8,
}


def _golden_view() -> dict[str, Any]:
    with FIXTURE.open(encoding="utf-8") as handle:
        return copy.deepcopy(json.load(handle)["view"])


def _minimal_view() -> dict[str, Any]:
    return {
        "current": [],
        "decisions": [],
        "permits": [],
        "revision": "root",
        "schema_identifier": "metacraft.authority.view",
    }


def _reference(seed: str, *, media_type: str = "application/json") -> dict[str, Any]:
    return {
        "content_hash": "sha256:" + seed * 32,
        "media_type": media_type,
        "metadata_content_hash": "sha256:" + seed[::-1] * 32,
        "size_bytes": 4,
    }


def _proposal_reference(seed: str) -> dict[str, Any]:
    reference = _reference(
        seed,
        media_type=PROPOSAL_MEDIA_TYPE,
    )
    reference["metadata_content_hash"] = _proposal_metadata_hash(
        reference["content_hash"],
        size_bytes=reference["size_bytes"],
    )
    return reference


def _permit_entry(
    *,
    state: str = "open",
    close_reason: Any = None,
    receipt_reference: Any = None,
    receipt_body_reference: Any = "__omitted__",
    scope: str = "fixture",
    expires_at: str = "2099-01-01T00:00:00+00:00",
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "body_reference": copy.deepcopy(VALID_REFERENCE),
        "capacity_reference": copy.deepcopy(VALID_REFERENCE),
        "close_reason": close_reason,
        "expires_at": expires_at,
        "permit_reference": copy.deepcopy(VALID_PROPOSAL_REFERENCE),
        "receipt_reference": receipt_reference,
        "scope": scope,
        "state": state,
    }
    if receipt_body_reference != "__omitted__":
        entry["receipt_body_reference"] = receipt_body_reference
    return entry


# ---------------------------------------------------------------------------
# Golden round trip
# ---------------------------------------------------------------------------


def test_golden_rust_view_round_trips_into_typed_collections() -> None:
    view = AuthorityView.from_mapping(_golden_view())

    assert isinstance(view, AuthorityView)
    assert view.schema_identifier == "metacraft.authority.view"
    assert isinstance(view.revision, Revision)
    assert view.revision.value.startswith("sha256:")
    assert len(view.current) == 1
    assert len(view.decisions) == 3
    assert len(view.permits) == 1

    permit = view.permits[0]
    assert isinstance(permit, Permit)
    assert permit.state == "closed"
    assert permit.close_reason == "consumed"
    assert permit.receipt_reference is not None
    assert permit.receipt_body_reference is not None

    decision = view.decisions[0]
    assert isinstance(decision, AdmittedDecision)
    assert decision.relation in {
        "record",
        "current",
        "permit",
        "receipt",
        "close",
    }

    current = view.current[0]
    assert isinstance(current, Current)
    assert current.key.startswith("capacity:")
    proposal_hashes = tuple(
        item.proposal_reference.content_hash for item in view.decisions
    )
    # Rust preserves admission chronology; it does not repair history by hash.
    assert proposal_hashes != tuple(sorted(proposal_hashes))


def test_empty_workspace_view_decodes() -> None:
    view = AuthorityView.from_mapping(_minimal_view())
    assert view.current == ()
    assert view.decisions == ()
    assert view.permits == ()
    assert view.revision == Revision("root")


def test_view_revision_and_history_move_together() -> None:
    advanced_without_history = {
        **_minimal_view(),
        "revision": "sha256:" + "9" * 64,
    }
    with pytest.raises(
        ValueError,
        match="authority_view_revision_relation_invalid",
    ):
        AuthorityView.from_mapping(advanced_without_history)

    history_at_root = {
        **_minimal_view(),
        "decisions": [_decision_entry()],
    }
    with pytest.raises(
        ValueError,
        match="authority_view_revision_relation_invalid",
    ):
        AuthorityView.from_mapping(history_at_root)


@pytest.mark.parametrize(
    "revision",
    [
        pytest.param("committed", id="private_projection_sentinel"),
        pytest.param("future", id="arbitrary_word"),
        pytest.param("sha256", id="short_hash"),
        pytest.param("sha256:" + "A" * 64, id="uppercase_hash"),
    ],
)
def test_view_rejects_a_revision_rust_cannot_publish(revision: str) -> None:
    malformed = {**_minimal_view(), "revision": revision}
    with pytest.raises(ValueError, match="revision_invalid"):
        AuthorityView.from_mapping(malformed)


# ---------------------------------------------------------------------------
# Reference decoding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param({"content_hash": "sha256"}, id="content_hash_short"),
        pytest.param({"content_hash": "sha256:" + "g" * 64}, id="content_hash_non_hex"),
        pytest.param(
            {"content_hash": "sha256:" + "A" * 64}, id="content_hash_uppercase"
        ),
        pytest.param(
            {"content_hash": "sha256:" + "0" * 63}, id="content_hash_wrong_length"
        ),
        pytest.param(
            {"content_hash": "SHA256:" + "0" * 64}, id="content_hash_wrong_prefix"
        ),
        pytest.param({"content_hash": ""}, id="content_hash_empty"),
        pytest.param({"content_hash": 1}, id="content_hash_integer"),
        pytest.param({"content_hash": True}, id="content_hash_boolean"),
        pytest.param({"metadata_content_hash": "sha256"}, id="metadata_hash_short"),
        pytest.param(
            {"metadata_content_hash": "sha256:" + "z" * 64},
            id="metadata_hash_non_hex",
        ),
        pytest.param({"metadata_content_hash": 1}, id="metadata_hash_integer"),
        pytest.param({"metadata_content_hash": True}, id="metadata_hash_boolean"),
        pytest.param({"media_type": ""}, id="media_type_empty"),
        pytest.param({"media_type": "   "}, id="media_type_whitespace"),
        pytest.param({"media_type": 1}, id="media_type_integer"),
        pytest.param({"media_type": True}, id="media_type_boolean"),
        pytest.param({"size_bytes": True}, id="size_bytes_boolean_true"),
        pytest.param({"size_bytes": False}, id="size_bytes_boolean_false"),
        pytest.param({"size_bytes": -1}, id="size_bytes_negative"),
        pytest.param({"size_bytes": 1.0}, id="size_bytes_float"),
        pytest.param({"size_bytes": "4"}, id="size_bytes_string"),
        pytest.param({"extra_field": True}, id="unknown_field"),
    ],
)
def test_reference_from_mapping_rejects_each_malformed_field(
    mutation: dict[str, Any],
) -> None:
    malformed = {**VALID_REFERENCE, **mutation}
    with pytest.raises(ValueError):
        Reference.from_mapping(malformed)


@pytest.mark.parametrize(
    "missing", ["content_hash", "media_type", "metadata_content_hash", "size_bytes"]
)
def test_reference_from_mapping_rejects_missing_field(missing: str) -> None:
    malformed = {**VALID_REFERENCE}
    del malformed[missing]
    with pytest.raises(ValueError):
        Reference.from_mapping(malformed)


def test_reference_from_mapping_rejects_non_mapping() -> None:
    with pytest.raises(ValueError):
        Reference.from_mapping("not-a-mapping")  # type: ignore[arg-type]


def test_reference_from_mapping_keeps_exact_types_without_coercion() -> None:
    decoded = Reference.from_mapping(VALID_REFERENCE)
    assert decoded.content_hash == VALID_REFERENCE["content_hash"]
    assert decoded.media_type == VALID_REFERENCE["media_type"]
    assert decoded.metadata_content_hash == VALID_REFERENCE["metadata_content_hash"]
    assert decoded.size_bytes == VALID_REFERENCE["size_bytes"]
    assert isinstance(decoded.size_bytes, int)
    assert not isinstance(decoded.size_bytes, bool)


# ---------------------------------------------------------------------------
# Authority view top-level shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param({"extra": True}, id="unknown_top_level_field"),
        pytest.param({"revision": 1}, id="revision_integer"),
        pytest.param({"revision": True}, id="revision_boolean"),
        pytest.param({"revision": ""}, id="revision_empty"),
        pytest.param({"revision": None}, id="revision_null"),
        pytest.param({"schema_identifier": "metacraft.other"}, id="schema_wrong"),
        pytest.param({"schema_identifier": 1}, id="schema_integer"),
        pytest.param({"schema_identifier": ""}, id="schema_empty"),
        pytest.param({"current": {}}, id="current_not_list"),
        pytest.param({"decisions": "record"}, id="decisions_not_list"),
        pytest.param({"permits": {}}, id="permits_not_list"),
    ],
)
def test_view_from_mapping_rejects_top_level_malformations(
    mutation: dict[str, Any],
) -> None:
    malformed = {**_minimal_view(), **mutation}
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed)


@pytest.mark.parametrize(
    "missing", ["current", "decisions", "permits", "revision", "schema_identifier"]
)
def test_view_from_mapping_rejects_missing_top_level_field(missing: str) -> None:
    malformed = {**_minimal_view()}
    del malformed[missing]
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed)


def test_view_from_mapping_rejects_non_mapping() -> None:
    with pytest.raises(ValueError):
        AuthorityView.from_mapping([])  # type: ignore[arg-type]


def test_view_from_mapping_rejects_non_mapping_entry() -> None:
    malformed = {**_minimal_view(), "current": ["not-a-mapping"]}
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed)


# ---------------------------------------------------------------------------
# Current entry decoding
# ---------------------------------------------------------------------------


def _current_entry() -> dict[str, Any]:
    return {
        "body_reference": copy.deepcopy(VALID_REFERENCE),
        "key": "anchor",
        "superseded": [],
    }


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param({"extra": True}, id="unknown_field"),
        pytest.param({"key": ""}, id="key_empty"),
        pytest.param({"key": "   "}, id="key_whitespace"),
        pytest.param({"key": 1}, id="key_integer"),
        pytest.param({"key": True}, id="key_boolean"),
        pytest.param(
            {"body_reference": {"content_hash": "sha256"}}, id="body_reference_bad"
        ),
        pytest.param({"superseded": {}}, id="superseded_not_list"),
        pytest.param(
            {"superseded": [{"content_hash": "sha256"}]},
            id="superseded_entry_bad",
        ),
    ],
)
def test_current_entry_rejects_malformations(mutation: dict[str, Any]) -> None:
    entry = {**_current_entry(), **mutation}
    malformed = {**_minimal_view(), "current": [entry]}
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed)


def test_view_rejects_duplicate_or_unsorted_current_keys() -> None:
    alpha = {**_current_entry(), "key": "alpha"}
    beta = {
        **_current_entry(),
        "body_reference": _reference("12"),
        "key": "beta",
    }
    duplicate = {**_minimal_view(), "current": [alpha, alpha]}
    unsorted = {**_minimal_view(), "current": [beta, alpha]}

    with pytest.raises(ValueError, match="authority_view_current_order_invalid"):
        AuthorityView.from_mapping(duplicate)
    with pytest.raises(ValueError, match="authority_view_current_order_invalid"):
        AuthorityView.from_mapping(unsorted)


# ---------------------------------------------------------------------------
# Admitted decision entry decoding
# ---------------------------------------------------------------------------


def _decision_entry() -> dict[str, Any]:
    return {
        "body_reference": copy.deepcopy(VALID_REFERENCE),
        "outcome": "admitted",
        "proposal_reference": copy.deepcopy(VALID_PROPOSAL_REFERENCE),
        "relation": "record",
    }


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param({"extra": True}, id="unknown_field"),
        pytest.param({"outcome": "rejected"}, id="outcome_not_admitted"),
        pytest.param({"outcome": 1}, id="outcome_integer"),
        pytest.param({"outcome": True}, id="outcome_boolean"),
        pytest.param({"relation": "deferred"}, id="relation_unknown"),
        pytest.param({"relation": 1}, id="relation_integer"),
        pytest.param({"relation": True}, id="relation_boolean"),
        pytest.param(
            {"body_reference": {"content_hash": "sha256"}}, id="body_reference_bad"
        ),
        pytest.param(
            {"proposal_reference": {"content_hash": "sha256"}},
            id="proposal_reference_bad",
        ),
        pytest.param(
            {
                "proposal_reference": {
                    **VALID_PROPOSAL_REFERENCE,
                    "metadata_content_hash": "sha256:" + "0" * 64,
                }
            },
            id="proposal_reference_metadata_mismatch",
        ),
    ],
)
def test_decision_entry_rejects_malformations(mutation: dict[str, Any]) -> None:
    entry = {**_decision_entry(), **mutation}
    malformed = {**_minimal_view(), "decisions": [entry]}
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed)


def test_admitted_decision_requires_a_proposal_reference() -> None:
    malformed = {
        **_decision_entry(),
        "proposal_reference": copy.deepcopy(VALID_REFERENCE),
    }
    with pytest.raises(ValueError, match="decision_proposal_reference_invalid"):
        AdmittedDecision.from_mapping(malformed)


def test_repeated_record_decisions_preserve_valid_rust_history(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "workspace")
    proposal = Proposal.record(Document("metacraft.test.record", {"value": "same"}))

    first = authority.decide(proposal, at=Revision.root())
    second = authority.decide(proposal, at=first.resulting_revision)
    view = authority.view()

    assert first.admitted and second.admitted
    assert len(view.decisions) == 2
    assert view.decisions[0] == view.decisions[1]


def test_repeated_current_decisions_preserve_valid_rust_history(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "workspace")
    document = Document("metacraft.test.current", {"value": "same"})
    first = authority.decide(
        Proposal.current(document, key="study"),
        at=Revision.root(),
    )
    assert first.body_reference is not None
    repeated = Proposal.current(
        document,
        key="study",
        supersedes=first.body_reference,
    )

    second = authority.decide(repeated, at=first.resulting_revision)
    third = authority.decide(repeated, at=second.resulting_revision)
    view = authority.view()

    assert second.admitted and third.admitted
    assert len(view.current[0].superseded) == 2
    assert view.decisions[1] == view.decisions[2]


def test_view_accepts_only_the_current_history_rust_can_replay() -> None:
    earlier = _reference("12")
    latest = _reference("34")
    earlier_decision = {
        **_decision_entry(),
        "body_reference": copy.deepcopy(earlier),
        "proposal_reference": _proposal_reference("56"),
        "relation": "current",
    }
    latest_decision = {
        **_decision_entry(),
        "body_reference": copy.deepcopy(latest),
        "proposal_reference": _proposal_reference("78"),
        "relation": "current",
    }
    current = {
        "body_reference": copy.deepcopy(latest),
        "key": "study",
        "superseded": [copy.deepcopy(earlier)],
    }
    coherent = {
        **_minimal_view(),
        "current": [current],
        "decisions": [earlier_decision, latest_decision],
        "revision": "sha256:" + "9" * 64,
    }
    decoded = AuthorityView.from_mapping(coherent)
    assert decoded.current[0].body_reference.content_hash == latest["content_hash"]

    reversed_history = {
        **coherent,
        "decisions": [latest_decision, earlier_decision],
    }
    with pytest.raises(ValueError, match="authority_view_current_history_invalid"):
        AuthorityView.from_mapping(reversed_history)

    missing_history = {**coherent, "decisions": [latest_decision]}
    with pytest.raises(ValueError, match="authority_view_current_history_invalid"):
        AuthorityView.from_mapping(missing_history)


# ---------------------------------------------------------------------------
# Permit entry decoding and lifecycle relationships
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expires_at",
    [
        "2099-01-01T00:00:00+00:00",
        "2099-01-01T00:00:00.100+00:00",
        "2099-01-01T00:00:00.000001+00:00",
        "2099-01-01T00:00:00.000000001+00:00",
    ],
)
def test_permit_accepts_rust_normalized_utc_expiry(expires_at: str) -> None:
    permit = Permit.from_mapping(_permit_entry(expires_at=expires_at))
    assert permit.expires_at == expires_at


def test_open_permit_round_trips_without_receipt_fields() -> None:
    permit = Permit.from_mapping(_permit_entry(state="open"))
    assert permit.state == "open"
    assert permit.close_reason is None
    assert permit.receipt_reference is None
    assert permit.receipt_body_reference is None


def test_consumed_permit_round_trips_with_exact_receipts() -> None:
    entry = _permit_entry(
        state="closed",
        close_reason="consumed",
        receipt_reference=copy.deepcopy(VALID_PERMIT_RECEIPT_REFERENCE),
        receipt_body_reference=copy.deepcopy(VALID_PERMIT_RECEIPT_BODY_REFERENCE),
    )
    permit = Permit.from_mapping(entry)
    assert permit.state == "closed"
    assert permit.close_reason == "consumed"
    assert permit.receipt_reference is not None
    assert permit.receipt_body_reference is not None


def test_revoked_permit_round_trips_without_receipts() -> None:
    entry = _permit_entry(state="closed", close_reason="revoked")
    permit = Permit.from_mapping(entry)
    assert permit.state == "closed"
    assert permit.close_reason == "revoked"
    assert permit.receipt_reference is None
    assert permit.receipt_body_reference is None


def test_expired_permit_round_trips_without_receipts() -> None:
    entry = _permit_entry(state="closed", close_reason="expired")
    permit = Permit.from_mapping(entry)
    assert permit.close_reason == "expired"


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param({"extra": True}, id="unknown_field"),
        pytest.param({"state": "pending"}, id="state_unknown"),
        pytest.param({"state": 1}, id="state_integer"),
        pytest.param({"state": True}, id="state_boolean"),
        pytest.param({"close_reason": "deferred"}, id="close_reason_unknown"),
        pytest.param({"close_reason": 1}, id="close_reason_integer"),
        pytest.param({"close_reason": True}, id="close_reason_boolean"),
        pytest.param({"scope": ""}, id="scope_empty"),
        pytest.param({"scope": "   "}, id="scope_whitespace"),
        pytest.param({"scope": 1}, id="scope_integer"),
        pytest.param({"scope": True}, id="scope_boolean"),
        pytest.param({"expires_at": "not-a-timestamp"}, id="expiry_invalid"),
        pytest.param({"expires_at": "2099-01-01T00:00:00"}, id="expiry_no_timezone"),
        pytest.param({"expires_at": "2099-01-01T00:00:00Z"}, id="expiry_zulu"),
        pytest.param(
            {"expires_at": "2099-01-01T01:00:00+01:00"},
            id="expiry_nonzero_offset",
        ),
        pytest.param(
            {"expires_at": "2099-01-01T00:00:00.1+00:00"},
            id="expiry_one_digit_fraction",
        ),
        pytest.param({"expires_at": "2099-01-01"}, id="expiry_date_only"),
        pytest.param({"expires_at": 1}, id="expiry_integer"),
        pytest.param({"expires_at": True}, id="expiry_boolean"),
        pytest.param(
            {"body_reference": {"content_hash": "sha256"}}, id="body_reference_bad"
        ),
        pytest.param(
            {"capacity_reference": {"content_hash": "sha256"}},
            id="capacity_reference_bad",
        ),
        pytest.param(
            {"permit_reference": {"content_hash": "sha256"}},
            id="permit_reference_bad",
        ),
    ],
)
def test_permit_entry_rejects_field_malformations(mutation: dict[str, Any]) -> None:
    entry = {**_permit_entry(), **mutation}
    malformed = {**_minimal_view(), "permits": [entry]}
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed)


@pytest.mark.parametrize(
    "missing", ["body_reference", "capacity_reference", "permit_reference"]
)
def test_permit_entry_rejects_missing_required_reference(missing: str) -> None:
    entry = _permit_entry()
    del entry[missing]
    malformed = {**_minimal_view(), "permits": [entry]}
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed)


def test_permit_requires_proposal_references() -> None:
    wrong_permit = {
        **_permit_entry(),
        "permit_reference": copy.deepcopy(VALID_REFERENCE),
    }
    with pytest.raises(ValueError, match="permit_proposal_reference_invalid"):
        Permit.from_mapping(wrong_permit)

    wrong_receipt = _permit_entry(
        state="closed",
        close_reason="consumed",
        receipt_reference=copy.deepcopy(VALID_REFERENCE),
        receipt_body_reference=copy.deepcopy(VALID_PERMIT_RECEIPT_BODY_REFERENCE),
    )
    with pytest.raises(ValueError, match="permit_receipt_reference_invalid"):
        Permit.from_mapping(wrong_receipt)


def test_permit_entry_rejects_null_receipt_body_reference_when_present() -> None:
    # Rust omits this field via skip_serializing_if; a present null never ships.
    entry = _permit_entry(state="open")
    entry["receipt_body_reference"] = None
    malformed = {**_minimal_view(), "permits": [entry]}
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed)


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(
            _permit_entry(
                state="open",
                close_reason="consumed",
            ),
            id="open_with_close_reason",
        ),
        pytest.param(
            _permit_entry(
                state="open",
                receipt_reference=copy.deepcopy(VALID_PERMIT_RECEIPT_REFERENCE),
            ),
            id="open_with_receipt_reference",
        ),
        pytest.param(
            _permit_entry(
                state="open",
                receipt_body_reference=copy.deepcopy(
                    VALID_PERMIT_RECEIPT_BODY_REFERENCE
                ),
            ),
            id="open_with_receipt_body",
        ),
        pytest.param(
            _permit_entry(state="closed"),
            id="closed_without_reason",
        ),
        pytest.param(
            _permit_entry(
                state="closed",
                close_reason="consumed",
            ),
            id="consumed_without_receipt_reference",
        ),
        pytest.param(
            _permit_entry(
                state="closed",
                close_reason="consumed",
                receipt_reference=copy.deepcopy(VALID_PERMIT_RECEIPT_REFERENCE),
            ),
            id="consumed_without_receipt_body",
        ),
        pytest.param(
            _permit_entry(
                state="closed",
                close_reason="revoked",
                receipt_reference=copy.deepcopy(VALID_PERMIT_RECEIPT_REFERENCE),
            ),
            id="revoked_with_receipt_reference",
        ),
        pytest.param(
            _permit_entry(
                state="closed",
                close_reason="expired",
                receipt_body_reference=copy.deepcopy(
                    VALID_PERMIT_RECEIPT_BODY_REFERENCE
                ),
            ),
            id="expired_with_receipt_body",
        ),
    ],
)
def test_permit_entry_rejects_impossible_relationships(entry: dict[str, Any]) -> None:
    malformed = {**_minimal_view(), "permits": [entry]}
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed)


def _permit_view() -> dict[str, Any]:
    capacity_body = _reference("10")
    capacity_proposal = _proposal_reference("20")
    first_body = _reference("30")
    first_proposal = _proposal_reference("40")
    second_body = _reference("50")
    second_proposal = _proposal_reference("60")
    current = {
        "body_reference": copy.deepcopy(capacity_body),
        "key": "capacity:solver",
        "superseded": [],
    }
    decisions = [
        {
            "body_reference": copy.deepcopy(capacity_body),
            "outcome": "admitted",
            "proposal_reference": capacity_proposal,
            "relation": "current",
        },
        {
            "body_reference": copy.deepcopy(first_body),
            "outcome": "admitted",
            "proposal_reference": copy.deepcopy(first_proposal),
            "relation": "permit",
        },
        {
            "body_reference": copy.deepcopy(second_body),
            "outcome": "admitted",
            "proposal_reference": copy.deepcopy(second_proposal),
            "relation": "permit",
        },
    ]
    permits = [
        {
            **_permit_entry(scope="solver"),
            "body_reference": first_body,
            "capacity_reference": copy.deepcopy(capacity_body),
            "permit_reference": first_proposal,
        },
        {
            **_permit_entry(scope="solver"),
            "body_reference": second_body,
            "capacity_reference": copy.deepcopy(capacity_body),
            "permit_reference": second_proposal,
        },
    ]
    return {
        **_minimal_view(),
        "current": [current],
        "decisions": decisions,
        "permits": permits,
        "revision": "sha256:" + "9" * 64,
    }


def test_view_rejects_duplicate_or_unsorted_permits() -> None:
    coherent = _permit_view()
    assert len(AuthorityView.from_mapping(coherent).permits) == 2

    first, second = coherent["permits"]
    duplicate = {**coherent, "permits": [first, first]}
    unsorted = {**coherent, "permits": [second, first]}
    with pytest.raises(ValueError, match="authority_view_permit_order_invalid"):
        AuthorityView.from_mapping(duplicate)
    with pytest.raises(ValueError, match="authority_view_permit_order_invalid"):
        AuthorityView.from_mapping(unsorted)


def test_view_rejects_a_duplicate_single_use_decision() -> None:
    malformed = _permit_view()
    malformed["decisions"].append(copy.deepcopy(malformed["decisions"][1]))
    with pytest.raises(ValueError, match="authority_view_decision_duplicate"):
        AuthorityView.from_mapping(malformed)


def test_view_rejects_a_permit_without_its_capacity_or_admission() -> None:
    coherent = _permit_view()
    unrelated_capacity = copy.deepcopy(coherent)
    unrelated_capacity["permits"][0]["capacity_reference"] = _reference("70")
    with pytest.raises(ValueError, match="authority_view_permit_capacity_invalid"):
        AuthorityView.from_mapping(unrelated_capacity)

    missing_admission = {
        **coherent,
        "decisions": coherent["decisions"][:-1],
    }
    with pytest.raises(ValueError, match="authority_view_permit_history_invalid"):
        AuthorityView.from_mapping(missing_admission)


def test_view_rejects_a_permit_admitted_before_its_capacity() -> None:
    malformed = _permit_view()
    malformed["decisions"][0], malformed["decisions"][1] = (
        malformed["decisions"][1],
        malformed["decisions"][0],
    )
    with pytest.raises(ValueError, match="authority_view_decision_order_invalid"):
        AuthorityView.from_mapping(malformed)


def test_view_rejects_a_receipt_admitted_before_its_permit() -> None:
    malformed = _golden_view()
    malformed["decisions"][1], malformed["decisions"][2] = (
        malformed["decisions"][2],
        malformed["decisions"][1],
    )
    with pytest.raises(ValueError, match="authority_view_decision_order_invalid"):
        AuthorityView.from_mapping(malformed)


# ---------------------------------------------------------------------------
# Decision (decide verb result) decoding
# ---------------------------------------------------------------------------


def _decision_result() -> dict[str, Any]:
    return {
        "body_reference": copy.deepcopy(VALID_REFERENCE),
        "findings": [],
        "observed_revision": "root",
        "outcome": "admitted",
        "proposal_content_hash": "sha256:" + "5" * 64,
        "proposal_reference": copy.deepcopy(VALID_PROPOSAL_REFERENCE),
        "resulting_revision": "sha256:" + "6" * 64,
        "schema_identifier": "metacraft.authority.decision",
    }


def test_decision_result_round_trips() -> None:
    decision = Decision.from_mapping(_decision_result())
    assert decision.admitted
    assert isinstance(decision.body_reference, Reference)
    assert decision.findings == ()
    assert decision.observed_revision == Revision("root")
    assert decision.proposal_content_hash == "sha256:" + "5" * 64


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param({"extra": True}, id="unknown_field"),
        pytest.param({"outcome": "unknown"}, id="outcome_unknown"),
        pytest.param({"outcome": 1}, id="outcome_integer"),
        pytest.param({"outcome": True}, id="outcome_boolean"),
        pytest.param({"observed_revision": ""}, id="observed_revision_empty"),
        pytest.param({"observed_revision": 1}, id="observed_revision_integer"),
        pytest.param({"observed_revision": True}, id="observed_revision_boolean"),
        pytest.param({"resulting_revision": ""}, id="resulting_revision_empty"),
        pytest.param({"resulting_revision": True}, id="resulting_revision_boolean"),
        pytest.param({"schema_identifier": "metacraft.other"}, id="schema_wrong"),
        pytest.param({"findings": {}}, id="findings_not_list"),
        pytest.param({"findings": [1]}, id="findings_non_string"),
        pytest.param({"findings": [True]}, id="findings_boolean"),
        pytest.param(
            {"body_reference": {"content_hash": "sha256"}}, id="body_reference_bad"
        ),
        pytest.param(
            {"proposal_reference": {"content_hash": "sha256"}},
            id="proposal_reference_bad",
        ),
        pytest.param(
            {
                "proposal_reference": {
                    **VALID_PROPOSAL_REFERENCE,
                    "metadata_content_hash": "sha256:" + "0" * 64,
                }
            },
            id="proposal_reference_metadata_mismatch",
        ),
        pytest.param(
            {"proposal_content_hash": "sha256"},
            id="proposal_content_hash_bad_form",
        ),
        pytest.param(
            {"proposal_content_hash": 1},
            id="proposal_content_hash_integer",
        ),
        pytest.param(
            {"proposal_content_hash": True},
            id="proposal_content_hash_boolean",
        ),
    ],
)
def test_decision_result_rejects_malformations(mutation: dict[str, Any]) -> None:
    malformed = {**_decision_result(), **mutation}
    with pytest.raises(ValueError):
        Decision.from_mapping(malformed)


def test_decision_result_admits_the_exact_rejection_rust_emits() -> None:
    rejected = {
        "body_reference": None,
        "findings": ["revision_mismatch"],
        "observed_revision": "root",
        "outcome": "rejected",
        "proposal_content_hash": "sha256:" + "5" * 64,
        "proposal_reference": None,
        "resulting_revision": "root",
        "schema_identifier": "metacraft.authority.decision",
    }
    decision = Decision.from_mapping(rejected)
    assert not decision.admitted
    assert decision.body_reference is None
    assert decision.proposal_reference is None
    assert decision.proposal_content_hash == "sha256:" + "5" * 64
    assert decision.findings == ("revision_mismatch",)


@pytest.mark.parametrize(
    "finding",
    [
        "permit_expired",
        "structure_mismatch",
        "structure_mismatch:$",
        "structure_mismatch:$.enabled",
    ],
)
def test_rejected_decision_accepts_rust_findings(finding: str) -> None:
    rejected = {
        **_decision_result(),
        "body_reference": None,
        "findings": [finding],
        "outcome": "rejected",
        "proposal_reference": None,
        "resulting_revision": "root",
    }
    assert Decision.from_mapping(rejected).findings == (finding,)


@pytest.mark.parametrize(
    "finding",
    [
        "unexpected",
        "structure_mismatch:",
        "structure_mismatch:path",
        "structure_mismatch:$$",
    ],
)
def test_rejected_decision_rejects_findings_rust_cannot_emit(
    finding: str,
) -> None:
    rejected = {
        **_decision_result(),
        "body_reference": None,
        "findings": [finding],
        "outcome": "rejected",
        "proposal_reference": None,
        "resulting_revision": "root",
    }
    with pytest.raises(ValueError, match="decision_result_finding_invalid"):
        Decision.from_mapping(rejected)


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param({"body_reference": None}, id="missing_body_reference"),
        pytest.param({"proposal_reference": None}, id="missing_proposal_reference"),
        pytest.param({"proposal_content_hash": None}, id="missing_proposal_hash"),
        pytest.param(
            {"findings": ["revision_mismatch"]},
            id="finding_on_admission",
        ),
        pytest.param({"resulting_revision": "root"}, id="revision_did_not_advance"),
        pytest.param(
            {
                "observed_revision": "sha256:" + "8" * 64,
                "resulting_revision": "root",
            },
            id="revision_returned_to_root",
        ),
        pytest.param(
            {"proposal_reference": _proposal_reference("77")},
            id="proposal_hash_disagrees_with_reference",
        ),
    ],
)
def test_admitted_decision_rejects_impossible_relationships(
    mutation: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="decision_result_relation_invalid"):
        Decision.from_mapping({**_decision_result(), **mutation})


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(
            {"body_reference": copy.deepcopy(VALID_REFERENCE)}, id="body_reference"
        ),
        pytest.param(
            {"proposal_reference": copy.deepcopy(VALID_PROPOSAL_REFERENCE)},
            id="proposal_reference",
        ),
        pytest.param({"findings": []}, id="finding_missing"),
        pytest.param(
            {"findings": ["revision_mismatch", "permit_already_closed"]},
            id="multiple_findings",
        ),
        pytest.param(
            {"resulting_revision": "sha256:" + "7" * 64},
            id="revision_advanced",
        ),
        pytest.param({"proposal_content_hash": None}, id="proposal_hash_missing"),
    ],
)
def test_rejected_decision_rejects_impossible_relationships(
    mutation: dict[str, Any],
) -> None:
    rejected = {
        **_decision_result(),
        "body_reference": None,
        "findings": ["revision_mismatch"],
        "outcome": "rejected",
        "proposal_reference": None,
        "resulting_revision": "root",
    }
    with pytest.raises(ValueError, match="decision_result_relation_invalid"):
        Decision.from_mapping({**rejected, **mutation})


@pytest.mark.parametrize(
    "field",
    ["observed_revision", "resulting_revision"],
)
@pytest.mark.parametrize("revision", ["future", "committed", "sha256:" + "A" * 64])
def test_decision_rejects_a_revision_rust_cannot_publish(
    field: str,
    revision: str,
) -> None:
    with pytest.raises(ValueError, match="revision_invalid"):
        Decision.from_mapping({**_decision_result(), field: revision})


# ---------------------------------------------------------------------------
# Check report decoding
# ---------------------------------------------------------------------------


def _check_report() -> dict[str, Any]:
    return {
        "findings": [],
        "ledger_event_count": 3,
        "protocol_identifier": "metacraft.authority",
        "schema_identifier": "metacraft.authority.check",
        "schema_content_hashes": {
            "capacity": "sha256:b3f8f4089f897c9cb9b9bfe4db2f2cc1e043841834109f3ebeb4f28ab8e919e7",
            "decision": "sha256:2d6a0e816fa1c9cf973f68fe90e3b119f960690afb198a959bc4376128e199a7",
            "proposal": "sha256:3ac33ccc4183fcbd63534824a3d8ae24bdf4094fe4ac4b5865efa114ca6fda5a",
            "reference": "sha256:bab101133f0f759d8201581c5e68c47391f8c84fe079f3b73a1e276f297330ea",
            "structure": "sha256:69517363134539f624477f451f9973b4ba872a2dcdaa171d0eea52dbc421f56e",
            "view": "sha256:ffef8a6d313c417cd89384bdda1b7c99aaef4d11d8181a4245e53d8894bc0ba3",
        },
        "workspace_valid": True,
    }


def test_check_report_round_trips_without_boolean_coercion() -> None:
    report = CheckReport.from_mapping(_check_report())
    assert report.is_workspace_valid is True
    assert report.findings == ()
    assert report.ledger_event_count == 3
    assert report.schema_content_hashes["view"].startswith("sha256:")


def test_public_authority_decodes_the_real_native_check(tmp_path: Path) -> None:
    report = Authority(tmp_path / "workspace").check()
    assert report.is_workspace_valid is True
    assert report.findings == ()
    assert report.ledger_event_count == 0


@pytest.mark.parametrize(
    "missing",
    [
        "findings",
        "ledger_event_count",
        "protocol_identifier",
        "schema_identifier",
        "schema_content_hashes",
        "workspace_valid",
    ],
)
def test_check_report_rejects_each_missing_field(missing: str) -> None:
    malformed = _check_report()
    del malformed[missing]
    with pytest.raises(ValueError, match="check_report_shape_invalid"):
        CheckReport.from_mapping(malformed)


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param({"workspace_valid": "false"}, id="string_boolean"),
        pytest.param({"workspace_valid": 1}, id="integer_boolean"),
        pytest.param({"ledger_event_count": True}, id="boolean_count"),
        pytest.param({"ledger_event_count": -1}, id="negative_count"),
        pytest.param({"findings": "none"}, id="findings_not_list"),
        pytest.param({"findings": [1]}, id="finding_not_string"),
        pytest.param(
            {"findings": ["z_finding", "a_finding"], "workspace_valid": False},
            id="findings_unsorted",
        ),
        pytest.param(
            {"findings": ["same", "same"], "workspace_valid": False},
            id="findings_duplicate",
        ),
        pytest.param({"protocol_identifier": "metacraft.other"}, id="protocol"),
        pytest.param({"schema_identifier": "metacraft.other"}, id="schema"),
        pytest.param({"schema_content_hashes": []}, id="hashes_not_mapping"),
        pytest.param(
            {"schema_content_hashes": {"view": "sha256:" + "0" * 64}},
            id="hashes_incomplete",
        ),
        pytest.param({"extra": True}, id="surplus_field"),
    ],
)
def test_check_report_rejects_malformed_native_values(
    mutation: dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        CheckReport.from_mapping({**_check_report(), **mutation})


def test_check_report_rejects_validity_that_disagrees_with_findings() -> None:
    with pytest.raises(ValueError, match="check_report_relation_invalid"):
        CheckReport.from_mapping(
            {
                **_check_report(),
                "findings": ["projection_replay_mismatch"],
            }
        )


# ---------------------------------------------------------------------------
# Architecture: no raw native-view key parsing outside the adapter
# ---------------------------------------------------------------------------


def test_view_decoders_are_invoked_only_inside_the_authority_adapter() -> None:
    """
    Application, replay, scheduling, and science callers consume typed
    attributes; they never call the native-view decoders themselves.
    """

    source_root = Path(__file__).parents[2] / "src" / "metacraft"
    decode_names = {
        "AuthorityView",
        "Decision",
        "Current",
        "Permit",
        "AdmittedDecision",
    }
    offenders: list[str] = []
    for path in source_root.rglob("*.py"):
        if "authority" in path.relative_to(source_root).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if (
                    node.func.attr == "from_mapping"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in decode_names
                ):
                    offenders.append(f"{path.relative_to(source_root)}:{node.lineno}")
    assert offenders == [], offenders

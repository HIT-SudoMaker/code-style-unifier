from __future__ import annotations

from dataclasses import replace

from metacraft.authority import (
    Reference,
    reference_for,
    reference_matches,
)


CAPACITY_BODY = (
    b'{"limit":1,"qualification_references":[],"schema_identifier":'
    b'"metacraft.authority.capacity","scope":"solver"}'
)
CAPACITY_REFERENCE = Reference(
    content_hash=(
        "sha256:0d0f4f94a552fd9925970f8d3e4f3c6c9f480fda1a9bdcae243ab95a14be3abb"
    ),
    media_type="application/json",
    metadata_content_hash=(
        "sha256:df5becfd1637744593e60ad73f941a09eeb92e5a42c425571a19e450fafbb55d"
    ),
    size_bytes=109,
)


def test_reference_matches_the_native_empty_metadata_contract() -> None:
    assert reference_for(CAPACITY_BODY) == CAPACITY_REFERENCE
    assert reference_matches(CAPACITY_REFERENCE, CAPACITY_BODY)


def test_reference_rejects_tampered_descriptive_metadata() -> None:
    described = reference_for(
        CAPACITY_BODY,
        descriptive_metadata={"source": "fixture"},
    )
    tampered = replace(
        described,
        metadata_content_hash=CAPACITY_REFERENCE.metadata_content_hash,
    )

    assert reference_matches(
        described,
        CAPACITY_BODY,
        descriptive_metadata={"source": "fixture"},
    )
    assert not reference_matches(described, CAPACITY_BODY)
    assert not reference_matches(
        tampered,
        CAPACITY_BODY,
        descriptive_metadata={"source": "fixture"},
    )

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from metacraft.authority import (
    AdmittedDecision,
    Authority,
    AuthorityView,
    Current,
    Document,
    Permit,
    Proposal,
    Reference,
    Revision,
)


def _reference_mapping(reference: Reference) -> dict[str, object]:
    return reference.as_mapping()


def test_decoded_view_exposes_typed_current_decisions_and_permits(
    tmp_path: Path,
) -> None:
    """
    One complete replayed view decodes into the three typed collections.
    """

    authority = Authority(tmp_path / "workspace")
    qualification = authority.decide(
        Proposal.record(Document("fixture.qualification", {"ready": True})),
        at=Revision.root(),
    )
    assert qualification.body_reference is not None

    capacity = authority.decide(
        Proposal.capacity(
            scope="fixture",
            limit=2,
            qualification_references=(qualification.body_reference,),
        ),
        at=authority.view().revision,
    )
    assert capacity.body_reference is not None

    first_permit = authority.decide(
        Proposal.permit(
            Document("metacraft.science.permitted_work", {"work": "alpha"}),
            capacity_reference=capacity.body_reference,
            scope="fixture",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ),
        at=authority.view().revision,
    )
    assert first_permit.body_reference is not None
    assert first_permit.proposal_reference is not None

    consumed = authority.decide(
        Proposal.receipt(
            Document("fixture.observation", {"value": 1}),
            permit_reference=first_permit.proposal_reference,
        ),
        at=authority.view().revision,
    )
    assert consumed.body_reference is not None

    view = authority.view()

    assert isinstance(view, AuthorityView)
    assert view.schema_identifier == "metacraft.authority.view"
    assert isinstance(view.current, tuple)
    assert isinstance(view.decisions, tuple)
    assert isinstance(view.permits, tuple)
    assert all(isinstance(item, Current) for item in view.current)
    assert all(isinstance(item, AdmittedDecision) for item in view.decisions)
    assert all(isinstance(item, Permit) for item in view.permits)

    capacity_current = next(
        current for current in view.current if current.key == "capacity:fixture"
    )
    assert capacity_current.body_reference == capacity.body_reference
    assert capacity_current.superseded == ()

    permit = view.permits[0]
    assert permit.scope == "fixture"
    assert permit.state == "closed"
    assert permit.close_reason == "consumed"
    assert permit.body_reference == first_permit.body_reference
    assert permit.permit_reference == first_permit.proposal_reference
    assert permit.capacity_reference == capacity.body_reference
    assert permit.receipt_body_reference == consumed.body_reference
    assert permit.receipt_reference is not None

    receipt_decision = next(
        decision
        for decision in view.decisions
        if decision.relation == "receipt"
    )
    assert receipt_decision.body_reference == consumed.body_reference
    assert receipt_decision.proposal_reference == consumed.proposal_reference


def test_current_superseded_chain_round_trips_into_typed_references(
    tmp_path: Path,
) -> None:
    """
    Superseding one current entry preserves the predecessor reference.
    """

    authority = Authority(tmp_path / "workspace")
    first = authority.decide(
        Proposal.current(
            Document("fixture.anchor", {"version": 1}),
            key="anchor",
        ),
        at=Revision.root(),
    )
    assert first.body_reference is not None
    second = authority.decide(
        Proposal.current(
            Document("fixture.anchor", {"version": 2}),
            key="anchor",
            supersedes=first.body_reference,
        ),
        at=authority.view().revision,
    )
    assert second.body_reference is not None

    view = authority.view()
    assert len(view.current) == 1
    current = view.current[0]
    assert current.key == "anchor"
    assert current.body_reference == second.body_reference
    assert current.superseded == (first.body_reference,)


def test_from_mapping_rejects_malformed_nested_entries() -> None:
    """
    Bad references, invalid permit states, and unknown keys fail at decode.
    """

    reference = Reference(
        content_hash="sha256:0" * 7,
        media_type="application/json",
        metadata_content_hash="sha256:1" * 7,
        size_bytes=1,
    ).as_mapping()

    base_view: dict[str, object] = {
        "current": [],
        "decisions": [],
        "permits": [],
        "revision": "root",
        "schema_identifier": "metacraft.authority.view",
    }

    malformed_current = {
        **base_view,
        "current": [
            {
                "key": "anchor",
                "body_reference": {"content_hash": "sha256"},
                "superseded": [],
            }
        ],
    }
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed_current)

    unknown_permit = {
        **base_view,
        "permits": [
            {
                "body_reference": reference,
                "capacity_reference": reference,
                "close_reason": None,
                "expires_at": "2099-01-01T00:00:00Z",
                "permit_reference": reference,
                "receipt_reference": None,
                "scope": "fixture",
                "state": "open",
                "unexpected_field": True,
            }
        ],
    }
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(unknown_permit)

    invalid_state = {
        **base_view,
        "permits": [
            {
                "body_reference": reference,
                "capacity_reference": reference,
                "close_reason": None,
                "expires_at": "2099-01-01T00:00:00Z",
                "permit_reference": reference,
                "receipt_reference": None,
                "scope": "fixture",
                "state": "pending",
            }
        ],
    }
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(invalid_state)

    invalid_close_reason = {
        **base_view,
        "permits": [
            {
                "body_reference": reference,
                "capacity_reference": reference,
                "close_reason": "deferred",
                "expires_at": "2099-01-01T00:00:00Z",
                "permit_reference": reference,
                "receipt_reference": None,
                "scope": "fixture",
                "state": "closed",
            }
        ],
    }
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(invalid_close_reason)

    malformed_decision = {
        **base_view,
        "decisions": [
            {
                "body_reference": reference,
                "outcome": "admitted",
                "proposal_reference": reference,
                "relation": "deferred",
            }
        ],
    }
    with pytest.raises(ValueError):
        AuthorityView.from_mapping(malformed_decision)


def test_permit_lifecycle_round_trips_through_typed_values(
    tmp_path: Path,
) -> None:
    """
    Reserve, consume, close, and inspect permits through typed Permit values.
    """

    authority = Authority(tmp_path / "workspace")
    qualification = authority.decide(
        Proposal.record(Document("fixture.qualification", {"ready": True})),
        at=Revision.root(),
    )
    assert qualification.body_reference is not None
    capacity = authority.decide(
        Proposal.capacity(
            scope="fixture",
            limit=2,
            qualification_references=(qualification.body_reference,),
        ),
        at=authority.view().revision,
    )
    assert capacity.body_reference is not None

    open_permit = authority.decide(
        Proposal.permit(
            Document("metacraft.science.permitted_work", {"work": "alpha"}),
            capacity_reference=capacity.body_reference,
            scope="fixture",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ),
        at=authority.view().revision,
    )
    assert open_permit.proposal_reference is not None

    consumed_permit = authority.decide(
        Proposal.permit(
            Document("metacraft.science.permitted_work", {"work": "beta"}),
            capacity_reference=capacity.body_reference,
            scope="fixture",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ),
        at=authority.view().revision,
    )
    assert consumed_permit.proposal_reference is not None
    authority.decide(
        Proposal.receipt(
            Document("fixture.observation", {"value": 1}),
            permit_reference=consumed_permit.proposal_reference,
        ),
        at=authority.view().revision,
    )

    revoked_permit = authority.decide(
        Proposal.permit(
            Document("metacraft.science.permitted_work", {"work": "gamma"}),
            capacity_reference=capacity.body_reference,
            scope="fixture",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        ),
        at=authority.view().revision,
    )
    assert revoked_permit.proposal_reference is not None
    authority.decide(
        Proposal.close(
            Document("metacraft.science.closed_work", {"work": "gamma"}),
            permit_reference=revoked_permit.proposal_reference,
            reason="revoked",
        ),
        at=authority.view().revision,
    )

    permits = authority.view().permits
    by_work = {
        Document.from_bytes(
            authority.fetch(permit.body_reference)
        ).values["work"]: permit
        for permit in permits
    }
    assert by_work["alpha"].state == "open"
    assert by_work["alpha"].close_reason is None
    assert by_work["alpha"].receipt_body_reference is None

    assert by_work["beta"].state == "closed"
    assert by_work["beta"].close_reason == "consumed"
    assert by_work["beta"].receipt_body_reference is not None

    assert by_work["gamma"].state == "closed"
    assert by_work["gamma"].close_reason == "revoked"
    assert by_work["gamma"].receipt_body_reference is None

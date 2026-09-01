from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from metacraft.authority import Authority, Document, Reference
from metacraft.authority.session import AuthoritySession


def test_plain_admission_advances_one_observed_authority_head(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    document = Document("fixture.note", {"message": "first"})

    reference = session.admit_document(document)

    assert authority.fetch(reference) == document.to_bytes()
    assert session.observe() == authority.view()


def test_structured_admission_keeps_shape_and_document_in_one_session(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    source = session.admit_document(
        Document("fixture.source", {"ready": True})
    )
    document = Document(
        "fixture.derived",
        {"source": source.as_mapping()},
    )

    reference = session.admit_document(document, references=(source,))

    view = authority.view()
    assert authority.fetch(reference) == document.to_bytes()
    assert session.observe() == view
    assert tuple(item.relation for item in view.decisions) == (
        "record",
        "record",
        "record",
    )


def test_opaque_admission_retains_exact_body_and_metadata(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)

    reference = session.admit_object(
        b"exact opaque bytes",
        media_type="application/vnd.metacraft.fixture",
        descriptive_metadata={"object_kind": "FixtureOpaque"},
    )

    assert session.fetch(reference) == b"exact opaque bytes"
    assert reference.media_type == "application/vnd.metacraft.fixture"


def test_rejected_decision_leaves_the_session_usable(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    absent_permit = Reference(
        content_hash="sha256:" + "1" * 64,
        media_type="application/json",
        metadata_content_hash="sha256:" + "2" * 64,
        size_bytes=1,
    )

    with pytest.raises(RuntimeError, match="receipt_admission_rejected"):
        session.admit_receipt(
            Document("fixture.observation", {"complete": True}),
            permit_reference=absent_permit,
        )

    admitted = session.admit_document(
        Document("fixture.note", {"message": "still usable"})
    )
    assert session.fetch(admitted) == Document(
        "fixture.note",
        {"message": "still usable"},
    ).to_bytes()


def test_revision_contention_reobserves_without_duplicate_admission(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    first = AuthoritySession(authority)
    competing = AuthoritySession(authority)
    competing.admit_document(
        Document("fixture.note", {"message": "competing"})
    )

    admitted = first.admit_document(
        Document("fixture.note", {"message": "after contention"})
    )

    view = authority.view()
    assert first.observe() == view
    assert tuple(item.body_reference for item in view.decisions) == (
        view.decisions[0].body_reference,
        admitted,
    )


def test_capacity_admission_returns_the_current_capacity_reference(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    qualification = session.admit_document(
        Document("fixture.qualification", {"qualified": True})
    )

    capacity = session.admit_capacity(
        scope="solver:fixture",
        limit=2,
        qualification_references=(qualification,),
    )

    current = {
        item.key: item.body_reference for item in session.observe().current
    }
    assert current == {"capacity:solver:fixture": capacity}


def test_two_sessions_converge_on_the_same_capacity_generation(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    setup = AuthoritySession(authority)
    qualification = setup.admit_document(
        Document("fixture.qualification", {"qualified": True})
    )
    first = AuthoritySession(authority)
    second = AuthoritySession(authority)

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = tuple(
            future.result()
            for future in (
                workers.submit(
                    first.admit_capacity,
                    scope="solver:fixture",
                    limit=2,
                    qualification_references=(qualification,),
                ),
                workers.submit(
                    second.admit_capacity,
                    scope="solver:fixture",
                    limit=2,
                    qualification_references=(qualification,),
                ),
            )
        )

    assert outcomes[0] == outcomes[1]
    assert first.current_reference("capacity:solver:fixture") == outcomes[0]


def test_current_admission_compare_and_replaces_exact_predecessor(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    first = session.admit_current(
        Document("fixture.checkpoint", {"step": 1}),
        key="checkpoint:fixture",
        supersedes=None,
    )

    second = session.admit_current(
        Document("fixture.checkpoint", {"step": 2}),
        key="checkpoint:fixture",
        supersedes=first,
    )

    assert session.current_reference("checkpoint:fixture") == second
    assert authority.fetch(first) != authority.fetch(second)


def test_current_admission_preserves_structured_reference_closure(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    source = session.admit_document(
        Document("fixture.source", {"ready": True})
    )
    document = Document(
        "fixture.checkpoint",
        {"source": source.as_mapping()},
    )

    checkpoint = session.admit_current(
        document,
        key="checkpoint:fixture",
        supersedes=None,
        references=(source,),
    )

    assert authority.fetch(checkpoint) == document.to_bytes()
    assert session.current_reference("checkpoint:fixture") == checkpoint


def test_two_sessions_converge_on_the_same_current_body(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    first = AuthoritySession(authority)
    second = AuthoritySession(authority)
    document = Document("fixture.checkpoint", {"step": 1})

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = tuple(
            future.result()
            for future in (
                workers.submit(
                    first.admit_current,
                    document,
                    key="checkpoint:fixture",
                    supersedes=None,
                ),
                workers.submit(
                    second.admit_current,
                    document,
                    key="checkpoint:fixture",
                    supersedes=None,
                ),
            )
        )

    assert outcomes[0] == outcomes[1]
    assert first.current_reference("checkpoint:fixture") == outcomes[0]


def test_current_compare_and_swap_conflict_remains_a_direct_fault(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    first = AuthoritySession(authority)
    stale = AuthoritySession(authority)
    first.admit_current(
        Document("fixture.checkpoint", {"step": 1}),
        key="checkpoint:fixture",
        supersedes=None,
    )

    with pytest.raises(RuntimeError, match="current_admission_conflict"):
        stale.admit_current(
            Document("fixture.checkpoint", {"step": 2}),
            key="checkpoint:fixture",
            supersedes=None,
        )


def test_same_current_body_with_different_metadata_remains_a_conflict(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    first = AuthoritySession(authority)
    stale = AuthoritySession(authority)
    document = Document("fixture.checkpoint", {"step": 1})
    first.admit_current(
        document,
        key="checkpoint:fixture",
        supersedes=None,
        descriptive_metadata={"generation": "first"},
    )

    with pytest.raises(RuntimeError, match="current_admission_conflict"):
        stale.admit_current(
            document,
            key="checkpoint:fixture",
            supersedes=None,
            descriptive_metadata={"generation": "different"},
        )


def test_delegated_reference_is_verified_before_session_reobserves(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "authority")
    session = AuthoritySession(authority)
    delegated = AuthoritySession(authority)
    reference = delegated.admit_document(
        Document("fixture.delegated", {"complete": True})
    )

    session.observe_admitted(reference)

    assert session.observe() == authority.view()

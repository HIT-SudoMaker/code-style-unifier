from __future__ import annotations

from pathlib import Path

import pytest

from metacraft.authority import (
    Authority,
    Document,
    Proposal,
    Reference,
    ReferenceUnresolvable,
    Revision,
)
from metacraft.authority import interface as authority_interface


_CONTRACT_BYTES = (
    b'{"schema_identifier":"metacraft.test.authority_contract",'
    b'"values":{"count":1,"name":"violet focus"}}'
)
_CONTRACT_REFERENCE = {
    "content_hash": (
        "sha256:06f1bb3746fe050fd3d73909b40a9abe"
        "964368c0f16aff6d88c89d0a50cfd7ee"
    ),
    "media_type": "application/json",
    "metadata_content_hash": (
        "sha256:e87ab3dcc8c845522dcab0e003f2ef8b"
        "031b54f2d11bdd01071964b1e24c42d3"
    ),
    "size_bytes": 100,
}


def test_public_authority_verbs_preserve_canonical_bytes_and_replay(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    authority = Authority(workspace)
    document = Document(
        "metacraft.test.authority_contract",
        {"count": 1, "name": "violet focus"},
    )

    decision = authority.decide(
        Proposal.record(document),
        at=Revision.root(),
    )

    assert document.to_bytes() == _CONTRACT_BYTES
    assert decision.admitted
    assert decision.body_reference is not None
    assert decision.body_reference.as_mapping() == _CONTRACT_REFERENCE
    assert authority.fetch(decision.body_reference) == _CONTRACT_BYTES
    assert authority.check().is_workspace_valid
    assert authority.view().revision == decision.resulting_revision

    replayed = Authority(workspace)
    assert replayed.view() == authority.view()
    assert replayed.fetch(decision.body_reference) == _CONTRACT_BYTES


def test_public_authority_distinguishes_domain_rejection_from_stale_revision(
    tmp_path: Path,
) -> None:
    authority = Authority(tmp_path / "workspace")
    first = authority.decide(
        Proposal.current(
            Document("metacraft.test.authority_contract", {"name": "current"}),
            key="contract",
        ),
        at=Revision.root(),
    )
    assert first.admitted

    domain_rejection = authority.decide(
        Proposal.current(
            Document(
                "metacraft.test.authority_contract",
                {"name": "replacement"},
            ),
            key="contract",
        ),
        at=first.resulting_revision,
    )
    stale_revision = authority.decide(
        Proposal.record(
            Document("metacraft.test.authority_contract", {"name": "stale"})
        ),
        at=Revision.root(),
    )

    assert not domain_rejection.admitted
    assert domain_rejection.findings == ("current_reference_mismatch",)
    assert domain_rejection.resulting_revision == first.resulting_revision
    assert not stale_revision.admitted
    assert stale_revision.findings == ("revision_mismatch",)
    assert stale_revision.resulting_revision == first.resulting_revision


def test_public_authority_reports_integrity_and_keeps_exception_text(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    authority = Authority(workspace)
    (workspace / "workspace.marker").write_bytes(b"not a workspace\n")

    report = authority.check()

    assert report.is_workspace_valid is False
    assert report.findings == ("workspace_marker_invalid",)
    with pytest.raises(
        RuntimeError,
        match="^workspace_open_failed: invalid workspace marker$",
    ):
        Authority(workspace)


def test_public_authority_types_a_missing_immutable_reference(tmp_path: Path) -> None:
    authority = Authority(tmp_path / "workspace")
    missing = Reference.from_mapping(_CONTRACT_REFERENCE)

    with pytest.raises(
        ReferenceUnresolvable,
        match="^reference_unresolvable: object missing$",
    ):
        authority.fetch(missing)


def test_public_authority_does_not_classify_runtime_error_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NativeFault:
        def __init__(self, _workspace: str) -> None:
            pass

        def fetch(self, _reference: str) -> bytes:
            raise RuntimeError("reference_unresolvable: forged implementation fault")

    monkeypatch.setattr(authority_interface, "NativeAuthority", NativeFault)
    authority = Authority("unused-workspace")
    reference = Reference.from_mapping(_CONTRACT_REFERENCE)

    with pytest.raises(
        RuntimeError,
        match="^reference_unresolvable: forged implementation fault$",
    ) as raised:
        authority.fetch(reference)
    assert type(raised.value) is RuntimeError

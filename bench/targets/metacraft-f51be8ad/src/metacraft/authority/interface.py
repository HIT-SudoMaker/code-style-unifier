from __future__ import annotations

import json
from pathlib import Path

from .._authority import (
    Authority as NativeAuthority,
    ReferenceUnresolvableError as NativeReferenceUnresolvableError,
)
from .errors import ReferenceUnresolvable
from .protocol import (
    AuthorityView,
    CheckReport,
    Decision,
    Proposal,
    Reference,
    Revision,
    workspace_path,
)


class Authority:
    """
    Typed Python access to the frozen workspace authority.
    """

    __slots__ = ("_native",)

    def __init__(self, workspace: str | Path) -> None:
        """
        Open or create one explicit authority workspace.
        """

        self._native = NativeAuthority(workspace_path(workspace))

    def check(self) -> CheckReport:
        """
        Verify the workspace and return its typed integrity report.
        """

        return CheckReport.from_mapping(json.loads(self._native.check()))

    def view(self) -> AuthorityView:
        """
        Return the replayed authority view at its exact revision.
        """

        return AuthorityView.from_mapping(json.loads(self._native.view()))

    def fetch(self, reference: Reference) -> bytes:
        """
        Fetch immutable bytes by their exact typed reference.
        """

        try:
            return bytes(self._native.fetch(reference.canonical_text()))
        except NativeReferenceUnresolvableError as error:
            raise ReferenceUnresolvable(str(error)) from error

    def decide(self, proposal: Proposal, *, at: Revision) -> Decision:
        """
        Submit one canonical proposal at one exact revision.
        """

        raw = self._native.decide(proposal.canonical_text(), at=at.value)
        return Decision.from_mapping(json.loads(raw))

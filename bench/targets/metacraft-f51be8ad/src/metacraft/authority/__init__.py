from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .interface import Authority

from .errors import ReferenceUnresolvable
from .protocol import (
    AdmittedDecision,
    AuthorityView,
    CheckReport,
    Current,
    Decision,
    Document,
    Permit,
    Proposal,
    Reference,
    Revision,
    Structure,
)
from .reference import reference_for, reference_matches

__all__ = [
    "AdmittedDecision",
    "Authority",
    "AuthorityView",
    "CheckReport",
    "Current",
    "Decision",
    "Document",
    "Permit",
    "Proposal",
    "Reference",
    "ReferenceUnresolvable",
    "reference_for",
    "reference_matches",
    "Revision",
    "Structure",
]


def __getattr__(name: str) -> Any:
    """
    Keep protocol values usable without loading the native extension.
    """

    if name == "Authority":
        from .interface import Authority

        return Authority
    raise AttributeError(name)

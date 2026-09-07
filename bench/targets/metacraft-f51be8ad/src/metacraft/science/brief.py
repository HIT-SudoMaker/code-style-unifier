from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..canonical import encode_bytes


@dataclass(frozen=True, slots=True, kw_only=True)
class Brief:
    """
    Preserves one user's aim, objectives, and honest omissions.
    """

    wording: str
    aim: str
    objectives: tuple[str, ...]
    budget: str
    omissions: tuple[str, ...] = ()

    def canonical_value(self) -> Any:
        """
        Return the durable brief value used at identity boundaries.
        """

        return self

    def canonical_bytes(self) -> bytes:
        """
        Encode this brief for stable identity.
        """

        return encode_bytes(self.canonical_value())

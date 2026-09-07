from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Method:
    """
    Establish one claim from explicit claims and qualified evidence.

    ``schema`` names the stable schema identifier of the scientific value
    this method establishes. The identifier is owned beside the value's
    decoder; the compiler copies and validates it without manufacturing a
    schema from a route name.
    """

    name: str
    claim: str
    requires: tuple[str, ...]
    capability: str | None
    schema: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Relationship:
    """
    Declares one aim-specific proof language without owning execution.
    """

    aim: str
    objectives: tuple[str, ...]
    applicability: str
    methods: tuple[Method, ...]

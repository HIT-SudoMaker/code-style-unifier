from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from .brief import Brief
from .compiler import MissingBriefFacts
from .metalens.brief import MetalensBrief
from .metalens.compiler import compile_metalens, metalens_brief_finding
from .study import Study


@dataclass(frozen=True, slots=True)
class InvalidBrief:
    """
    Report wording or facts that cannot name one scientific study.
    """

    reason: str


@dataclass(frozen=True, slots=True)
class UnsupportedAim:
    """
    Report one canonical aim whose scientific module is not implemented.
    """

    aim: str


CompileOutcome: TypeAlias = Study | InvalidBrief | UnsupportedAim


def compile_study(brief: Brief) -> CompileOutcome:
    """
    Purely compile one immutable brief through its explicitly owned aim.

    Known but unimplemented aims and invalid user vocabulary are ordinary
    values. Scientific recompilation with admitted facts remains owned by
    the selected aim module rather than widening this application seam.
    """

    if not isinstance(brief, Brief):
        return InvalidBrief("brief_type_invalid")
    common_finding = _common_brief_finding(brief)
    if common_finding is not None:
        return InvalidBrief(common_finding)
    if isinstance(brief, MetalensBrief) and brief.aim != "metalens":
        return InvalidBrief("brief_aim_mismatch")
    if brief.aim in {
        "frequency selective surface",
        "holographic metasurface",
        "quasi-bic metasurface",
    }:
        return UnsupportedAim(brief.aim)
    if brief.aim != "metalens":
        return InvalidBrief("aim_unknown")
    if not isinstance(brief, MetalensBrief):
        return InvalidBrief("metalens_facts_missing")
    try:
        metalens_finding = metalens_brief_finding(brief)
    except MissingBriefFacts as error:
        return InvalidBrief(str(error))
    if metalens_finding is not None:
        return InvalidBrief(metalens_finding)
    return compile_metalens(brief)


def _common_brief_finding(brief: Brief) -> str | None:
    for name, value in (
        ("wording", brief.wording),
        ("aim", brief.aim),
        ("budget", brief.budget),
    ):
        if not isinstance(value, str) or not value.strip():
            return f"brief_{name}_invalid"
    for name, values in (
        ("objectives", brief.objectives),
        ("omissions", brief.omissions),
    ):
        if not isinstance(values, tuple) or any(
            not isinstance(value, str) or not value.strip()
            for value in values
        ):
            return f"brief_{name}_invalid"
        if len(set(values)) != len(values):
            return f"brief_{name}_duplicate"
    if not brief.objectives:
        return "brief_objectives_missing"
    return None

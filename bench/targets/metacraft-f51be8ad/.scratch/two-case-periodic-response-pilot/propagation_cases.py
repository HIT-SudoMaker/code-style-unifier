"""Closed case configuration for the two propagation-response pilots."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PropagationPilotCase:
    benchmark_name: str
    stem: str
    period_nm: int
    height_nm: int
    period_reason: str
    height_reason: str


CASES = {
    "mcclung": PropagationPilotCase(
        benchmark_name="mcclung-2024-low-na-propagation",
        stem="mcclung",
        period_nm=430,
        height_nm=650,
        period_reason=(
            "Choose 430 nm to preserve practical lateral feature room under "
            "the sampling ceiling; retain the multi-order caution and require "
            "response evidence."
        ),
        height_reason=(
            "Choose 650 nm as the tallest relevant conservative candidate; "
            "the exact periodic response must still establish phase coverage "
            "and useful transmission."
        ),
    ),
    "arbabi": PropagationPilotCase(
        benchmark_name="arbabi-2015-high-na-propagation",
        stem="arbabi",
        period_nm=800,
        height_nm=900,
        period_reason=(
            "Choose 800 nm as a rounded high-NA lattice with sampling margin "
            "and practical lateral room; retain the multi-order caution and "
            "require sampled response evidence."
        ),
        height_reason=(
            "Choose 900 nm as the tallest legal propagation-phase candidate; "
            "the exact periodic response must still establish phase coverage "
            "and useful transmission."
        ),
    ),
}


def propagation_case(name: str) -> PropagationPilotCase:
    try:
        return CASES[name]
    except KeyError as error:
        raise ValueError(f"propagation_pilot_case_unknown:{name}") from error

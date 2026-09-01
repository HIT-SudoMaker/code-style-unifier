from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import math

import numpy
from numpy.typing import NDArray


FULL_TURN = Decimal("6.283185307179586")
PHASE_KEY_SCALE = Decimal("1000000000000")


def canonical_phase(value: Decimal) -> Decimal:
    """
    Place one finite phase on the shared half-open phase circle.
    """

    if not value.is_finite():
        raise ValueError("phase_not_finite")
    with localcontext() as context:
        context.prec = _working_precision(value)
        context.rounding = ROUND_HALF_EVEN
        phase = value % FULL_TURN
        if phase < 0:
            phase += FULL_TURN
    return Decimal(0) if phase == 0 else phase


def phase_from_float(value: float) -> Decimal:
    """
    Preserve a floating phase while removing turn-sized rounding noise.
    """

    if not math.isfinite(value):
        raise ValueError("phase_not_finite")
    remainder = math.remainder(value, math.tau)
    if abs(remainder) <= 2 * math.ulp(value):
        return Decimal(0)
    return canonical_phase(Decimal(str(value)))


def cyclic_distance(left: Decimal, right: Decimal) -> Decimal:
    """
    Return the shorter unsigned distance between two phases.
    """

    left_phase = canonical_phase(left)
    right_phase = canonical_phase(right)
    with localcontext() as context:
        context.prec = _working_precision(left_phase, right_phase)
        context.rounding = ROUND_HALF_EVEN
        difference = abs(left_phase - right_phase)
        return min(difference, FULL_TURN - difference)


def uniform_targets(levels: int) -> tuple[Decimal, ...]:
    """
    Place one target at every uniform level on the phase circle.
    """

    if levels <= 0:
        raise ValueError("phase_levels_invalid")
    step = FULL_TURN / Decimal(levels)
    return tuple(step * level for level in range(levels))


def level_tolerance(levels: int) -> Decimal:
    """
    Return the half-step tolerance of one uniform quantization.
    """

    if levels <= 0:
        raise ValueError("phase_levels_invalid")
    return (FULL_TURN / Decimal(levels)) / Decimal(2)


def covers_uniform_levels(
    phases: tuple[Decimal, ...],
    levels: int,
) -> bool:
    """
    Require a distinct measured phase within every target's half-step.
    """

    if len(phases) < levels:
        return False
    tolerance = level_tolerance(levels)
    candidates = tuple(canonical_phase(phase) for phase in phases)
    adjacency = tuple(
        tuple(
            index
            for index, phase in enumerate(candidates)
            if cyclic_distance(target, phase) <= tolerance
        )
        for target in uniform_targets(levels)
    )
    if any(not choices for choices in adjacency):
        return False
    return _has_distinct_assignment(adjacency, len(candidates))


def phase_key(value: Decimal) -> int:
    """
    Give equivalent phases the same stable scalar lookup key.
    """

    phase = canonical_phase(value)
    with localcontext() as context:
        context.prec = _working_precision(phase, PHASE_KEY_SCALE)
        context.rounding = ROUND_HALF_EVEN
        return int((phase * PHASE_KEY_SCALE).to_integral_value())


def nearest_phase_levels(
    values: NDArray[numpy.floating],
    levels: int,
) -> NDArray[numpy.int64]:
    """
    Match uniform levels; a half-step tie advances to the next level.
    """

    if levels <= 0:
        raise ValueError("phase_levels_invalid")
    phases = numpy.asarray(values, dtype=numpy.float64)
    if not numpy.isfinite(phases).all():
        raise ValueError("phase_not_finite")
    full_turn = float(FULL_TURN)
    positions = numpy.remainder(phases, full_turn) * levels / full_turn
    nearest = numpy.floor(positions + 0.5).astype(numpy.int64)
    return nearest % levels


def _has_distinct_assignment(
    adjacency: tuple[tuple[int, ...], ...],
    candidate_count: int,
) -> bool:
    matched_target = [-1] * candidate_count

    def _place(target: int, seen: set[int]) -> bool:
        for candidate in adjacency[target]:
            if candidate in seen:
                continue
            seen.add(candidate)
            previous = matched_target[candidate]
            if previous < 0 or _place(previous, seen):
                matched_target[candidate] = target
                return True
        return False

    return all(
        _place(target, set()) for target in range(len(adjacency))
    )


def _working_precision(*values: Decimal) -> int:
    operands = (*values, FULL_TURN)
    highest_digit = max(value.adjusted() for value in operands)
    places = []
    for value in operands:
        exponent = value.as_tuple().exponent
        if not isinstance(exponent, int):
            raise ValueError("phase_not_finite")
        places.append(exponent)
    lowest_place = min(places)
    return max(50, highest_digit - lowest_place + 4)


__all__ = [
    "FULL_TURN",
    "PHASE_KEY_SCALE",
    "canonical_phase",
    "covers_uniform_levels",
    "cyclic_distance",
    "level_tolerance",
    "nearest_phase_levels",
    "phase_from_float",
    "phase_key",
    "uniform_targets",
]

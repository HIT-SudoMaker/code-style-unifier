from decimal import Decimal
import math

from metacraft.science.phase import (
    FULL_TURN,
    canonical_phase,
    covers_uniform_levels,
    cyclic_distance,
    level_tolerance,
    phase_from_float,
    uniform_targets,
)


def test_phase_circle_has_one_canonical_cut() -> None:
    edge = Decimal("0.000000000000001")
    floating_edge = Decimal("1e-100")

    assert canonical_phase(-edge) == FULL_TURN - edge
    assert canonical_phase(FULL_TURN) == Decimal(0)
    assert canonical_phase(-FULL_TURN) == Decimal(0)
    assert canonical_phase(2 * FULL_TURN + edge) == edge
    assert canonical_phase(FULL_TURN * Decimal(2)) == Decimal(0)
    assert all(
        phase_from_float(turns * math.tau) == Decimal(0)
        for turns in (1, 2, 1000, 10_000_000)
    )
    assert cyclic_distance(-edge, edge) == 2 * edge
    assert Decimal(0) <= canonical_phase(-floating_edge) < FULL_TURN
    assert cyclic_distance(-floating_edge, Decimal(0)) == floating_edge
    assert canonical_phase(Decimal("62831853.07179587")) != Decimal(0)
    assert phase_from_float(-1e-100) == canonical_phase(floating_edge * -1)


def test_uniform_coverage_requires_one_distinct_phase_per_level() -> None:
    step = FULL_TURN / Decimal(4)
    phases = (
        step / Decimal(2),
        step * Decimal(2),
        step * Decimal(3),
        step * Decimal(2),
    )

    assert uniform_targets(4) == (
        Decimal(0),
        step,
        step * Decimal(2),
        step * Decimal(3),
    )
    assert level_tolerance(4) == step / Decimal(2)
    assert all(
        any(
            cyclic_distance(target, phase) <= level_tolerance(4)
            for phase in phases
        )
        for target in uniform_targets(4)
    )
    assert not covers_uniform_levels(phases, 4)

from __future__ import annotations

from decimal import Decimal

import pytest

from metacraft.solvers.lumerical_fdtd.time_budget import (
    PeriodicNumericalClosure,
    SolverTermination,
    TimeBudgetAttempt,
    plan_periodic_time_budget,
    reference_surface_response_change,
)


def test_visible_and_infrared_structures_receive_distinct_bounded_ladders(
) -> None:
    visible = plan_periodic_time_budget(
        wavelength_nm=405,
        solver_span_nm=2_000,
        maximum_refractive_index=Decimal("2.6"),
    )
    infrared = plan_periodic_time_budget(
        wavelength_nm=1_550,
        solver_span_nm=2_800,
        maximum_refractive_index=Decimal("3.48"),
    )

    assert visible.ordinary_maximum_fs == 1_000
    assert visible.extended_maximum_fs == 2_000
    assert infrared.causal_floor_fs == 300
    assert infrared.ordinary_maximum_fs == 2_000
    assert infrared.extended_maximum_fs == 4_000


def test_numerical_closure_requires_matching_native_stop_evidence() -> None:
    budget = plan_periodic_time_budget(
        wavelength_nm=405,
        solver_span_nm=2_000,
        maximum_refractive_index=Decimal("2.6"),
    )
    mismatched = SolverTermination(
        outcome="autoshutoff",
        native_status=2,
        simulated_time_fs=Decimal("800"),
        terminal_autoshutoff=Decimal("0.000009"),
        autoshutoff_threshold=Decimal("0.000001"),
    )

    with pytest.raises(
        ValueError,
        match="periodic_numerical_closure_evidence_invalid",
    ):
        PeriodicNumericalClosure(
            budget=budget,
            attempts=(
                TimeBudgetAttempt(
                    maximum_time_fs=budget.ordinary_maximum_fs,
                    termination=mismatched,
                ),
            ),
            disposition="autoshutoff",
        )


def test_surface_convergence_covers_the_field_consumed_by_assembly() -> None:
    initial = _reference_surface(1.0)
    extended = _reference_surface(1.001)

    has_converged, change = reference_surface_response_change(
        initial,
        extended,
    )

    assert has_converged
    assert Decimal(change["field_relative_change"]) < Decimal("0.005")


def test_surface_convergence_refuses_a_changed_physical_context() -> None:
    initial = _reference_surface(1.0)
    extended = {
        **_reference_surface(1.0),
        "wavelength_m": "6.33e-7",
    }

    with pytest.raises(ValueError, match="reference_surface_context_changed"):
        reference_surface_response_change(initial, extended)


def _reference_surface(scale: float) -> dict[str, object]:
    real = [[scale, scale], [scale, scale]]
    zero = [[0.0, 0.0], [0.0, 0.0]]
    return {
        "electric_components": {
            "x": {"imaginary": zero, "real": real},
            "y": {"imaginary": zero, "real": zero},
            "z": {"imaginary": zero, "real": zero},
        },
        "frame": "cartesian",
        "surface": "same grid",
        "transmitted_power": "0.5",
        "wavelength_m": "4.05e-7",
    }

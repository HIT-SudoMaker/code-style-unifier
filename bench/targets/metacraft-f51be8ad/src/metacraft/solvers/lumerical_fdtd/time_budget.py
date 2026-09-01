from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
import math
from types import MappingProxyType

import numpy

_AUTOSHUTOFF_THRESHOLD = Decimal("0.00001")
_CROSSING_COUNT = 4
_LIGHT_SPEED_METRES_PER_SECOND = Decimal(299_792_458)
_MAXIMUM_TIME_READBACK_TOLERANCE_FS = Decimal("1")
_MAXIMUM_TIME_STEP_FS = 100
_ORDINARY_PROFILE_FLOOR_FS = 1_000
_QUALITY_FACTOR_GUARD = 200
_SOURCE_INJECTION_GUARD_FS = 100
_CARTESIAN_RESPONSE_TOLERANCE = Decimal("0.005")
_FIELD_RESPONSE_TOLERANCE = Decimal("0.005")
_PHASE_TOLERANCE_RAD = Decimal("0.01")
_POWER_TOLERANCE = Decimal("0.005")


@dataclass(frozen=True, slots=True)
class PeriodicTimeBudget:
    """
    Bound one ordinary periodic response and its sole time extension.

    The budget is product policy, not caller input. Geometry supplies the
    causal floor, a guarded resonant lifetime supplies the wavelength scale,
    and the native solver may finish either maximum early by autoshutoff.
    """

    causal_floor_fs: int
    resonance_guard_fs: int
    ordinary_maximum_fs: int
    extended_maximum_fs: int
    autoshutoff_threshold: Decimal = _AUTOSHUTOFF_THRESHOLD

    def __post_init__(self) -> None:
        """
        Require an outward-rounded, causally sufficient time budget.
        """
        values = (
            self.causal_floor_fs,
            self.resonance_guard_fs,
            self.ordinary_maximum_fs,
            self.extended_maximum_fs,
        )
        if any(type(value) is not int or value <= 0 for value in values):
            raise ValueError("periodic_time_budget_duration_invalid")
        if any(value % _MAXIMUM_TIME_STEP_FS for value in values):
            raise ValueError("periodic_time_budget_not_outward_rounded")
        if self.ordinary_maximum_fs < max(
            self.causal_floor_fs,
            self.resonance_guard_fs,
            _ORDINARY_PROFILE_FLOOR_FS,
        ):
            raise ValueError("periodic_time_budget_ordinary_maximum_invalid")
        if self.extended_maximum_fs != 2 * self.ordinary_maximum_fs:
            raise ValueError("periodic_time_budget_extension_invalid")
        if (
            type(self.autoshutoff_threshold) is not Decimal
            or not self.autoshutoff_threshold.is_finite()
            or not Decimal(0) < self.autoshutoff_threshold < Decimal(1)
        ):
            raise ValueError("periodic_time_budget_autoshutoff_invalid")

    def as_mapping(self) -> dict[str, object]:
        """
        Record the complete reviewed numerical-time policy.
        """

        return {
            "autoshutoff_threshold": format(
                self.autoshutoff_threshold,
                "f",
            ),
            "causal_floor_fs": self.causal_floor_fs,
            "extended_maximum_fs": self.extended_maximum_fs,
            "ordinary_maximum_fs": self.ordinary_maximum_fs,
            "resonance_guard_fs": self.resonance_guard_fs,
        }


@dataclass(frozen=True, slots=True)
class SolverTermination:
    """
    Retain why one native FDTD attempt stopped and at what energy level.
    """

    outcome: str
    native_status: int
    simulated_time_fs: Decimal
    terminal_autoshutoff: Decimal
    autoshutoff_threshold: Decimal

    def __post_init__(self) -> None:
        """
        Require one finite native termination observation.
        """
        expected = {
            1: "maximum_time",
            2: "autoshutoff",
            3: "diverged",
        }
        if expected.get(self.native_status) != self.outcome:
            raise ValueError("solver_termination_status_invalid")
        for value in (
            self.simulated_time_fs,
            self.terminal_autoshutoff,
            self.autoshutoff_threshold,
        ):
            if type(value) is not Decimal or not value.is_finite():
                raise ValueError("solver_termination_value_invalid")
        if (
            self.simulated_time_fs <= 0
            or self.terminal_autoshutoff < 0
            or not Decimal(0) < self.autoshutoff_threshold < Decimal(1)
        ):
            raise ValueError("solver_termination_value_invalid")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> SolverTermination:
        """
        Restore one exact native termination observation.
        """
        required = {
            "autoshutoff_threshold",
            "native_status",
            "outcome",
            "simulated_time_fs",
            "terminal_autoshutoff",
        }
        if set(value) != required:
            raise ValueError("solver_termination_fields_invalid")
        status = value["native_status"]
        if type(status) is not int:
            raise ValueError("solver_termination_status_invalid")
        return cls(
            outcome=str(value["outcome"]),
            native_status=status,
            simulated_time_fs=Decimal(str(value["simulated_time_fs"])),
            terminal_autoshutoff=Decimal(str(value["terminal_autoshutoff"])),
            autoshutoff_threshold=Decimal(str(value["autoshutoff_threshold"])),
        )

    def as_mapping(self) -> dict[str, object]:
        return {
            "autoshutoff_threshold": format(
                self.autoshutoff_threshold,
                "f",
            ),
            "native_status": self.native_status,
            "outcome": self.outcome,
            "simulated_time_fs": format(self.simulated_time_fs, "f"),
            "terminal_autoshutoff": format(
                self.terminal_autoshutoff,
                "f",
            ),
        }


@dataclass(frozen=True, slots=True)
class TimeBudgetAttempt:
    """
    Pair one declared maximum with the native termination it produced.
    """

    maximum_time_fs: int
    termination: SolverTermination

    def __post_init__(self) -> None:
        """
        Require one budget-consistent native attempt.
        """
        if type(self.maximum_time_fs) is not int or self.maximum_time_fs <= 0:
            raise ValueError("time_budget_attempt_maximum_invalid")
        if type(self.termination) is not SolverTermination:
            raise TypeError("time_budget_attempt_termination_invalid")

    def as_mapping(self) -> dict[str, object]:
        return {
            "maximum_time_fs": self.maximum_time_fs,
            "termination": self.termination.as_mapping(),
        }


@dataclass(frozen=True, slots=True)
class PeriodicNumericalClosure:
    """
    Close one periodic response with at most one deterministic extension.
    """

    budget: PeriodicTimeBudget
    attempts: tuple[TimeBudgetAttempt, ...]
    disposition: str
    response_change: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        """
        Require two comparable attempts and finite response deltas.
        """
        if type(self.budget) is not PeriodicTimeBudget:
            raise TypeError("periodic_numerical_closure_budget_invalid")
        if len(self.attempts) not in {1, 2} or any(
            type(attempt) is not TimeBudgetAttempt for attempt in self.attempts
        ):
            raise ValueError("periodic_numerical_closure_attempts_invalid")
        if self.attempts[0].maximum_time_fs != (self.budget.ordinary_maximum_fs):
            raise ValueError("periodic_numerical_closure_ordinary_invalid")
        if len(self.attempts) == 2 and self.attempts[1].maximum_time_fs != (
            self.budget.extended_maximum_fs
        ):
            raise ValueError("periodic_numerical_closure_extension_invalid")
        if any(
            attempt.termination.autoshutoff_threshold
            != self.budget.autoshutoff_threshold
            or attempt.termination.simulated_time_fs
            > (Decimal(attempt.maximum_time_fs) + _MAXIMUM_TIME_READBACK_TOLERANCE_FS)
            for attempt in self.attempts
        ):
            raise ValueError("periodic_numerical_closure_evidence_invalid")
        allowed = {
            "autoshutoff",
            "autoshutoff_after_extension",
            "converged_by_extension",
        }
        if self.disposition not in allowed:
            raise ValueError("periodic_numerical_closure_disposition_invalid")
        if self.disposition == "autoshutoff" and (
            len(self.attempts) != 1
            or self.attempts[0].termination.outcome != "autoshutoff"
        ):
            raise ValueError("periodic_numerical_closure_disposition_invalid")
        if self.disposition != "autoshutoff" and len(self.attempts) != 2:
            raise ValueError("periodic_numerical_closure_disposition_invalid")
        if self.disposition == "autoshutoff_after_extension" and (
            self.attempts[-1].termination.outcome != "autoshutoff"
        ):
            raise ValueError("periodic_numerical_closure_disposition_invalid")
        if self.disposition == "converged_by_extension" and (
            self.attempts[-1].termination.outcome != "maximum_time"
            or self.response_change is None
        ):
            raise ValueError("periodic_numerical_closure_disposition_invalid")
        if self.response_change is not None:
            if not self.response_change or any(
                type(name) is not str or not name or type(value) is not str or not value
                for name, value in self.response_change.items()
            ):
                raise ValueError("periodic_numerical_closure_change_invalid")
            object.__setattr__(
                self,
                "response_change",
                MappingProxyType(dict(self.response_change)),
            )

    @property
    def warnings(self) -> tuple[str, ...]:
        """
        Return cautions established by the two-attempt closure.
        """
        if self.disposition == "autoshutoff":
            return ()
        if self.disposition == "autoshutoff_after_extension":
            return ("periodic_time_budget_extended",)
        return (
            "periodic_time_budget_extended",
            "periodic_residual_energy_after_extension",
        )

    def as_mapping(self) -> dict[str, object]:
        return {
            "attempts": [attempt.as_mapping() for attempt in self.attempts],
            "disposition": self.disposition,
            "response_change": (
                None if self.response_change is None else dict(self.response_change)
            ),
            "time_budget": self.budget.as_mapping(),
        }


def transmission_response_change(
    initial: Mapping[str, object],
    extended: Mapping[str, object],
) -> tuple[bool, dict[str, str]]:
    """
    Compare the power and wrapped phase that propagation science consumes.
    """

    initial_coefficient = _complex_response(initial["complex_transmission"])
    extended_coefficient = _complex_response(extended["complex_transmission"])
    values = (
        initial_coefficient.real,
        initial_coefficient.imag,
        extended_coefficient.real,
        extended_coefficient.imag,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("periodic_transmission_response_invalid")
    initial_power = Decimal(str(initial["power_transmission"]))
    extended_power = Decimal(str(extended["power_transmission"]))
    if not initial_power.is_finite() or not extended_power.is_finite():
        raise ValueError("periodic_transmission_response_invalid")
    raw_phase_delta = math.atan2(
        extended_coefficient.imag,
        extended_coefficient.real,
    ) - math.atan2(initial_coefficient.imag, initial_coefficient.real)
    phase_delta = math.atan2(
        math.sin(raw_phase_delta),
        math.cos(raw_phase_delta),
    )
    phase_change = Decimal(str(abs(phase_delta)))
    power_change = abs(extended_power - initial_power)
    comparison = {
        "phase_change_rad": format(phase_change, "f"),
        "phase_tolerance_rad": format(_PHASE_TOLERANCE_RAD, "f"),
        "power_change": format(power_change, "f"),
        "power_tolerance": format(_POWER_TOLERANCE, "f"),
        "response": "complex_transmission",
    }
    return (
        power_change <= _POWER_TOLERANCE and phase_change <= _PHASE_TOLERANCE_RAD,
        comparison,
    )


def polarization_response_change(
    initial: Mapping[str, object],
    extended: Mapping[str, object],
) -> tuple[bool, dict[str, str]]:
    """
    Compare the two Cartesian output components of one Jones column.
    """

    changes = tuple(
        abs(_complex_response(extended[name]) - _complex_response(initial[name]))
        for name in ("output_x", "output_y")
    )
    if not all(math.isfinite(value) for value in changes):
        raise ValueError("periodic_polarization_response_invalid")
    maximum_change = Decimal(str(max(changes)))
    comparison = {
        "cartesian_change": format(maximum_change, "f"),
        "cartesian_tolerance": format(
            _CARTESIAN_RESPONSE_TOLERANCE,
            "f",
        ),
        "response": "cartesian_polarization",
    }
    return maximum_change <= _CARTESIAN_RESPONSE_TOLERANCE, comparison


def reference_surface_response_change(
    initial: Mapping[str, object],
    extended: Mapping[str, object],
) -> tuple[bool, dict[str, str]]:
    """
    Compare the exact sampled field that downstream assembly consumes.

    Stable G0 power alone cannot prove a multi-order near-field patch. The
    second maximum therefore has to preserve both its physical context and
    its complete Cartesian complex field before residual energy is accepted.
    """

    varying_fields = {"electric_components", "transmitted_power"}
    if {
        name: value for name, value in initial.items() if name not in varying_fields
    } != {
        name: value for name, value in extended.items() if name not in varying_fields
    }:
        raise ValueError("reference_surface_context_changed")
    initial_field = _reference_surface_field(initial)
    extended_field = _reference_surface_field(extended)
    if initial_field.shape != extended_field.shape:
        raise ValueError("reference_surface_shape_changed")
    difference_norm = float(numpy.linalg.norm(extended_field - initial_field))
    field_scale = max(
        float(numpy.linalg.norm(initial_field)),
        float(numpy.linalg.norm(extended_field)),
        numpy.finfo(numpy.float64).tiny,
    )
    relative_field_change = Decimal(str(difference_norm / field_scale))
    initial_power = Decimal(str(initial["transmitted_power"]))
    extended_power = Decimal(str(extended["transmitted_power"]))
    if not initial_power.is_finite() or not extended_power.is_finite():
        raise ValueError("reference_surface_power_invalid")
    power_change = abs(extended_power - initial_power)
    comparison = {
        "field_relative_change": format(relative_field_change, "f"),
        "field_relative_tolerance": format(
            _FIELD_RESPONSE_TOLERANCE,
            "f",
        ),
        "surface_power_change": format(power_change, "f"),
        "surface_power_tolerance": format(_POWER_TOLERANCE, "f"),
    }
    return (
        relative_field_change <= _FIELD_RESPONSE_TOLERANCE
        and power_change <= _POWER_TOLERANCE,
        comparison,
    )


def _reference_surface_field(value: Mapping[str, object]) -> numpy.ndarray:
    components = value.get("electric_components")
    if not isinstance(components, Mapping) or set(components) != {
        "x",
        "y",
        "z",
    }:
        raise ValueError("reference_surface_components_invalid")
    encoded_components: list[numpy.ndarray] = []
    for name in ("x", "y", "z"):
        encoded = components[name]
        if not isinstance(encoded, Mapping) or set(encoded) != {
            "imaginary",
            "real",
        }:
            raise ValueError("reference_surface_components_invalid")
        try:
            real = numpy.asarray(encoded["real"], dtype=numpy.float64)
            imaginary = numpy.asarray(
                encoded["imaginary"],
                dtype=numpy.float64,
            )
        except (TypeError, ValueError) as error:
            raise ValueError("reference_surface_components_invalid") from error
        if (
            real.ndim != 2
            or real.shape != imaginary.shape
            or not numpy.isfinite(real).all()
            or not numpy.isfinite(imaginary).all()
        ):
            raise ValueError("reference_surface_components_invalid")
        encoded_components.append(real + 1j * imaginary)
    return numpy.stack(encoded_components, axis=-1)


def _complex_response(value: object) -> complex:
    if isinstance(value, bool) or not isinstance(
        value,
        (complex, float, int),
    ):
        raise TypeError("periodic_complex_response_required")
    return complex(value)


def plan_periodic_time_budget(
    *,
    wavelength_nm: int,
    solver_span_nm: int,
    maximum_refractive_index: Decimal,
) -> PeriodicTimeBudget:
    """
    Plan one structure- and wavelength-aware bounded time ladder.

    The material term deliberately uses the greatest admitted phase index as
    a conservative path guard. It does not pretend to predict resonant group
    delay; the independent quality-factor guard and native termination gate
    own that uncertainty.
    """

    if type(wavelength_nm) is not int or wavelength_nm <= 0:
        raise ValueError("periodic_time_budget_wavelength_invalid")
    if type(solver_span_nm) is not int or solver_span_nm <= 0:
        raise ValueError("periodic_time_budget_span_invalid")
    if (
        type(maximum_refractive_index) is not Decimal
        or not maximum_refractive_index.is_finite()
        or maximum_refractive_index <= 0
    ):
        raise ValueError("periodic_time_budget_refractive_index_invalid")

    femtoseconds_per_nanometre = Decimal(1_000_000) / _LIGHT_SPEED_METRES_PER_SECOND
    crossing_time_fs = (
        maximum_refractive_index * Decimal(solver_span_nm) * femtoseconds_per_nanometre
    )
    causal_floor_fs = _ceil_time(
        Decimal(_SOURCE_INJECTION_GUARD_FS)
        + Decimal(_CROSSING_COUNT) * crossing_time_fs
    )
    resonance_lifetime_fs = (
        Decimal(_QUALITY_FACTOR_GUARD)
        * Decimal(wavelength_nm)
        * femtoseconds_per_nanometre
        * Decimal(str(math.log(1 / float(_AUTOSHUTOFF_THRESHOLD))))
        / Decimal(str(2 * math.pi))
    )
    resonance_guard_fs = _ceil_time(
        Decimal(_SOURCE_INJECTION_GUARD_FS) + resonance_lifetime_fs
    )
    ordinary_maximum_fs = _ceil_time(
        max(
            Decimal(_ORDINARY_PROFILE_FLOOR_FS),
            Decimal(causal_floor_fs),
            Decimal(resonance_guard_fs),
        )
    )
    return PeriodicTimeBudget(
        causal_floor_fs=causal_floor_fs,
        resonance_guard_fs=resonance_guard_fs,
        ordinary_maximum_fs=ordinary_maximum_fs,
        extended_maximum_fs=2 * ordinary_maximum_fs,
    )


def _ceil_time(value_fs: Decimal) -> int:
    step = Decimal(_MAXIMUM_TIME_STEP_FS)
    return int((value_fs / step).to_integral_value(rounding=ROUND_CEILING) * step)

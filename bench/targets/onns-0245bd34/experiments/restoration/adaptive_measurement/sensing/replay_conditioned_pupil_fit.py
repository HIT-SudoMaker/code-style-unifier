from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from numbers import Integral, Real
from types import MappingProxyType

import torch

from experiments.restoration.adaptive_measurement.sensing.quadrature import (
    QuadratureFieldEstimate,
)
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.optical_bench import (
    OpticalBenchConfig,
    propagate_interferometric_bench,
)
from experiments.restoration.pupil_aberrations import (
    SUPPORTED_PUPIL_MODES,
    PupilAberrationState,
    build_pupil_aberration_phase,
)


@dataclass(frozen=True, slots=True, eq=False)
class ReplayConditionedPupilEstimate:
    """A modal pupil estimate fitted without clean-image or aberration truth."""

    estimated_phase_radians: torch.Tensor
    coefficients_radians: Mapping[str, float]
    initial_cross_term_nrmse: float
    fitted_cross_term_nrmse: float
    iteration_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "estimated_phase_radians",
            self.estimated_phase_radians.detach().clone(),
        )
        object.__setattr__(
            self,
            "coefficients_radians",
            MappingProxyType(dict(self.coefficients_radians)),
        )


def fit_replay_conditioned_pupil_phase(
    estimate: QuadratureFieldEstimate,
    replay_input_field: torch.Tensor,
    bench_config: OpticalBenchConfig,
    pupil: torch.Tensor,
    *,
    mode_names: Sequence[str] = SUPPORTED_PUPIL_MODES,
    iteration_count: int = 150,
    learning_rate: float = 0.05,
    coefficient_regularization: float = 1e-5,
    coefficient_limit_radians: float = 3.0,
) -> ReplayConditionedPupilEstimate:
    """Fit a calibrated pupil model to a four-step image-plane cross term.

    The controlled replay command is an allowed input condition. The function
    never accepts the clean image, injected aberration, or an oracle action.
    """
    if not isinstance(estimate, QuadratureFieldEstimate):
        raise TypeError("estimate must be a QuadratureFieldEstimate")
    if not isinstance(bench_config, OpticalBenchConfig):
        raise TypeError("bench_config must be an OpticalBenchConfig")
    bench_config.validate()
    iterations = _positive_integer("iteration_count", iteration_count)
    step_size = _positive_real("learning_rate", learning_rate)
    regularization = _nonnegative_real(
        "coefficient_regularization",
        coefficient_regularization,
    )
    coefficient_limit = _positive_real(
        "coefficient_limit_radians",
        coefficient_limit_radians,
    )
    modes = _mode_names(mode_names)
    target_cross_term = estimate.cross_term
    if tuple(target_cross_term.shape[-2:]) != bench_config.input_array_resolution:
        raise invalid_restoration_contract(
            "quadrature estimate must match the optical bench resolution"
        )
    field = _replay_field(
        replay_input_field,
        array_resolution=bench_config.input_array_resolution,
        device=target_cross_term.device,
    )
    pupil_plane = _pupil_plane(
        pupil,
        array_resolution=bench_config.input_array_resolution,
        device=target_cross_term.device,
    )
    basis = torch.stack(
        tuple(
            build_pupil_aberration_phase(
                bench_config.input_array_resolution,
                PupilAberrationState({mode_name: 1.0}),
                device=target_cross_term.device,
            )[0]
            for mode_name in modes
        )
    )
    coefficients = torch.zeros(
        len(modes),
        device=target_cross_term.device,
        dtype=torch.float32,
        requires_grad=True,
    )
    optimizer = torch.optim.Adam((coefficients,), lr=step_size)
    target_power = torch.mean(target_cross_term.abs().square()).detach()
    target_power = torch.clamp(target_power, min=1e-12)
    best_coefficients = coefficients.detach().clone()
    best_nrmse = float("inf")
    initial_nrmse = float("inf")

    with torch.enable_grad():
        for iteration_index in range(iterations):
            optimizer.zero_grad(set_to_none=True)
            phase = torch.einsum("m,mhw->hw", coefficients, basis)
            predicted_cross_term = _predict_cross_term(
                field,
                phase,
                pupil_plane,
                bench_config,
            )
            normalized_error = (
                torch.mean((predicted_cross_term - target_cross_term).abs().square())
                / target_power
            )
            fit_nrmse = float(torch.sqrt(normalized_error.detach()).item())
            if iteration_index == 0:
                initial_nrmse = fit_nrmse
            if fit_nrmse < best_nrmse:
                best_nrmse = fit_nrmse
                best_coefficients = coefficients.detach().clone()
            loss = normalized_error + regularization * torch.mean(coefficients.square())
            loss.backward()
            optimizer.step()
            with torch.no_grad():
                coefficients.clamp_(
                    min=-coefficient_limit,
                    max=coefficient_limit,
                )

        final_phase = torch.einsum("m,mhw->hw", coefficients, basis)
        final_prediction = _predict_cross_term(
            field,
            final_phase,
            pupil_plane,
            bench_config,
        )
        final_nrmse = float(
            torch.sqrt(
                torch.mean((final_prediction - target_cross_term).abs().square())
                / target_power
            ).item()
        )
        if final_nrmse < best_nrmse:
            best_nrmse = final_nrmse
            best_coefficients = coefficients.detach().clone()

    estimated_phase = torch.einsum("m,mhw->hw", best_coefficients, basis)
    return ReplayConditionedPupilEstimate(
        estimated_phase_radians=estimated_phase,
        coefficients_radians={
            mode_name: float(coefficient.item())
            for mode_name, coefficient in zip(
                modes,
                best_coefficients,
                strict=True,
            )
        },
        initial_cross_term_nrmse=initial_nrmse,
        fitted_cross_term_nrmse=best_nrmse,
        iteration_count=iterations,
    )


def _predict_cross_term(
    replay_input_field: torch.Tensor,
    aberration_phase_radians: torch.Tensor,
    pupil: torch.Tensor,
    bench_config: OpticalBenchConfig,
) -> torch.Tensor:
    fields = propagate_interferometric_bench(
        replay_input_field,
        torch.zeros_like(aberration_phase_radians),
        bench_config,
        processing_aberration_radians=aberration_phase_radians,
        processing_pupil=pupil,
    )
    return torch.conj(fields.reference) * fields.processing


def _mode_names(value: Sequence[str]) -> tuple[str, ...]:
    modes = tuple(value)
    if not modes:
        raise invalid_restoration_contract("mode_names must not be empty")
    if len(set(modes)) != len(modes):
        raise invalid_restoration_contract("mode_names must be unique")
    unsupported = tuple(mode for mode in modes if mode not in SUPPORTED_PUPIL_MODES)
    if unsupported:
        raise invalid_restoration_contract(
            f"unsupported pupil modes: {', '.join(unsupported)}"
        )
    return modes


def _replay_field(
    value: torch.Tensor,
    *,
    array_resolution: tuple[int, int],
    device: torch.device,
) -> torch.Tensor:
    if not isinstance(value, torch.Tensor) or not torch.is_complex(value):
        raise invalid_restoration_contract("replay_input_field must be complex")
    field = value.to(device=device, dtype=torch.complex64)
    if tuple(field.shape[-2:]) != array_resolution:
        raise invalid_restoration_contract(
            "replay_input_field must match the optical bench resolution"
        )
    if field.ndim == 3:
        field = field.unsqueeze(0)
    if field.ndim != 4 or field.shape[-3] != 1:
        raise invalid_restoration_contract(
            "replay_input_field must resolve to [batch, 1, height, width]"
        )
    if not bool(torch.isfinite(field).all()):
        raise invalid_restoration_contract("replay_input_field must be finite")
    return field


def _pupil_plane(
    value: torch.Tensor,
    *,
    array_resolution: tuple[int, int],
    device: torch.device,
) -> torch.Tensor:
    if (
        not isinstance(value, torch.Tensor)
        or torch.is_complex(value)
        or tuple(value.shape) != array_resolution
    ):
        raise invalid_restoration_contract(
            "pupil must be a real plane matching the optical bench resolution"
        )
    pupil = value.to(device=device, dtype=torch.float32)
    if not bool(torch.isfinite(pupil).all()) or bool(torch.any(pupil < 0.0)):
        raise invalid_restoration_contract("pupil must be finite and nonnegative")
    if float(pupil.sum().item()) <= 0.0:
        raise invalid_restoration_contract("pupil must contain positive support")
    return pupil


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    return int(value)


def _positive_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a positive real number")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized <= 0.0:
        raise invalid_restoration_contract(f"{name} must be a positive real number")
    return normalized


def _nonnegative_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a nonnegative real number")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0.0:
        raise invalid_restoration_contract(f"{name} must be a nonnegative real number")
    return normalized

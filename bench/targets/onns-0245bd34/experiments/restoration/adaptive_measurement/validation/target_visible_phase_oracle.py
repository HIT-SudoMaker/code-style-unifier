from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real

import torch

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.metrics import extract_center_image_region
from experiments.restoration.optical_bench import (
    OpticalBenchConfig,
    propagate_interferometric_bench,
)
from experiments.restoration.phase_control import PhaseCommand


@dataclass(frozen=True, slots=True)
class TargetVisiblePhaseOracleResult:
    """Hold one target-visible command used only to measure optical headroom."""

    command: PhaseCommand
    iteration_count: int
    continuous_mean_square_error: float
    continuous_piston_radians: float


def optimize_target_visible_phase(
    *,
    degraded_input_field: torch.Tensor,
    evaluator_target_intensity: torch.Tensor,
    bench_config: OpticalBenchConfig,
    evaluation_resolution: tuple[int, int],
    iteration_count: int,
    learning_rate: float,
    response_gain: float,
    drift_radians: float,
    processing_aberration_radians: torch.Tensor | None = None,
    processing_pupil: torch.Tensor | None = None,
) -> TargetVisiblePhaseOracleResult:
    """Optimize a full-grid phase with a hidden target, then precompensate delivery."""
    if (
        isinstance(iteration_count, bool)
        or not isinstance(iteration_count, Integral)
        or int(iteration_count) <= 0
    ):
        raise invalid_restoration_contract("iteration_count must be a positive integer")
    learning_rate_value = _positive_real("learning_rate", learning_rate)
    response_gain_value = _positive_real("response_gain", response_gain)
    drift_value = _finite_real("drift_radians", drift_radians)
    if not isinstance(degraded_input_field, torch.Tensor) or not torch.is_complex(
        degraded_input_field
    ):
        raise invalid_restoration_contract(
            "degraded_input_field must be a complex tensor"
        )
    if tuple(degraded_input_field.shape[-2:]) != bench_config.input_array_resolution:
        raise invalid_restoration_contract(
            "degraded_input_field must match the optical bench resolution"
        )
    target_region = extract_center_image_region(
        evaluator_target_intensity,
        region_resolution=evaluation_resolution,
    ).to(device=degraded_input_field.device, dtype=torch.float32)

    spatial_phase = torch.zeros(
        bench_config.input_array_resolution,
        device=degraded_input_field.device,
        dtype=torch.float32,
        requires_grad=True,
    )
    piston = torch.zeros(
        (),
        device=degraded_input_field.device,
        dtype=torch.float32,
        requires_grad=True,
    )
    optimizer = torch.optim.Adam(
        (spatial_phase, piston),
        lr=learning_rate_value,
    )
    best_error = math.inf
    best_spatial_phase = torch.zeros_like(spatial_phase)
    best_piston = 0.0

    with torch.enable_grad():
        for _ in range(int(iteration_count)):
            optimizer.zero_grad(set_to_none=True)
            zero_mean_spatial_phase = spatial_phase - torch.mean(spatial_phase)
            delivered_target_phase = zero_mean_spatial_phase + piston
            output_intensity = (
                propagate_interferometric_bench(
                    degraded_input_field,
                    delivered_target_phase,
                    bench_config,
                    processing_aberration_radians=processing_aberration_radians,
                    processing_pupil=processing_pupil,
                )
                .combined.abs()
                .square()
                .real
            )
            output_region = extract_center_image_region(
                output_intensity,
                region_resolution=evaluation_resolution,
            )
            mean_square_error = torch.mean((output_region - target_region).square())
            mean_square_error.backward()
            error_value = float(mean_square_error.detach().item())
            if error_value < best_error:
                best_error = error_value
                best_spatial_phase = zero_mean_spatial_phase.detach().clone()
                best_piston = float(piston.detach().item())
            optimizer.step()

    command = PhaseCommand(
        "evaluator-only-target-visible-oracle",
        best_spatial_phase / response_gain_value,
        piston_radians=(best_piston - drift_value) / response_gain_value,
    )
    return TargetVisiblePhaseOracleResult(
        command=command,
        iteration_count=int(iteration_count),
        continuous_mean_square_error=best_error,
        continuous_piston_radians=best_piston,
    )


def _positive_real(name: str, value: object) -> float:
    numeric_value = _finite_real(name, value)
    if numeric_value <= 0.0:
        raise invalid_restoration_contract(f"{name} must be positive")
    return numeric_value


def _finite_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    return numeric_value

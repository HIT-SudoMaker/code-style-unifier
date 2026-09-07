from __future__ import annotations

import torch
import torch.nn.functional as functional

from experiments.restoration.adaptive_measurement.validation.target_visible_phase_oracle import (
    optimize_target_visible_phase,
)
from experiments.restoration.optical_bench import (
    OpticalBenchConfig,
    propagate_interferometric_bench,
)


def test_target_visible_phase_oracle_improves_degraded_input_headroom() -> None:
    resolution = (32, 32)
    coordinate = torch.linspace(-1.0, 1.0, resolution[0])
    grid_y, grid_x = torch.meshgrid(coordinate, coordinate, indexing="ij")
    target = torch.exp(-18.0 * (grid_x.square() + grid_y.square()))[None, None]
    degraded = functional.avg_pool2d(target, kernel_size=7, stride=1, padding=3)
    input_field = torch.sqrt(degraded).to(torch.complex64)
    bench_config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=min(resolution),
    )
    zero_phase_output = (
        propagate_interferometric_bench(
            input_field,
            torch.zeros(resolution),
            bench_config,
        )
        .combined.abs()
        .square()
        .real
    )

    result = optimize_target_visible_phase(
        degraded_input_field=input_field,
        evaluator_target_intensity=target,
        bench_config=bench_config,
        evaluation_resolution=resolution,
        iteration_count=80,
        learning_rate=0.08,
        response_gain=1.0,
        drift_radians=0.0,
    )
    corrected_output = (
        propagate_interferometric_bench(
            input_field,
            result.command.phase_radians + result.command.piston_radians,
            bench_config,
        )
        .combined.abs()
        .square()
        .real
    )

    zero_phase_error = torch.mean((zero_phase_output - target).square())
    corrected_error = torch.mean((corrected_output - target).square())

    assert corrected_error < zero_phase_error * 0.2
    assert result.command.phase_radians.shape == resolution
    assert result.iteration_count == 80

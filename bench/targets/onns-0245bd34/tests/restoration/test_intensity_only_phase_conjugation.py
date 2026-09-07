from __future__ import annotations

import inspect
import math

import torch

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    CoherentPupilBench,
    CoherentPupilScene,
)
from experiments.restoration.adaptive_measurement.sensing.intensity_only_phase_conjugation import (
    infer_phase_conjugate_action,
)
from experiments.restoration.adaptive_measurement.sensing.quadrature import (
    demodulate_phase_shifted_observations,
)
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.phase_control import IdealPhaseDelivery, PhaseCommand


def _intensity_observations(
    scene: CoherentPupilScene,
    config: OpticalBenchConfig,
) -> tuple:
    bench = CoherentPupilBench(config, IdealPhaseDelivery())
    zero_phase = torch.zeros(config.input_array_resolution)
    return tuple(
        bench.acquire(
            scene,
            PhaseCommand(
                f"pre-{index}",
                zero_phase,
                piston_radians=piston,
            ),
            observation_id=f"pre-{index}",
            kind="calibration",
            sequence_index=index,
        )
        for index, piston in enumerate(
            (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)
        )
    )


def test_intensity_only_estimator_cannot_accept_hidden_scene_state() -> None:
    parameter_names = tuple(inspect.signature(infer_phase_conjugate_action).parameters)

    assert parameter_names == (
        "estimate",
        "bench_config",
        "spectral_support_threshold",
    )


def test_intensity_only_estimator_returns_zero_for_zero_phase_degradation() -> None:
    resolution = (32, 32)
    degraded_intensity = torch.linspace(0.1, 1.0, 32).repeat(32, 1)
    input_field = torch.sqrt(degraded_intensity).to(torch.complex64)[None, None]
    config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    scene = CoherentPupilScene(
        input_field,
        torch.zeros(resolution),
        torch.ones(resolution),
    )
    estimate = demodulate_phase_shifted_observations(
        _intensity_observations(scene, config)
    )

    result = infer_phase_conjugate_action(estimate, config)

    assert result.estimated_input_intensity.shape == (1, 1, 32, 32)
    assert torch.allclose(
        result.estimated_input_intensity,
        input_field.abs().square().real,
        atol=1e-5,
        rtol=1e-5,
    )
    assert result.command.phase_radians.abs().amax().item() < 1e-4
    assert result.spectral_support_fraction > 0.0

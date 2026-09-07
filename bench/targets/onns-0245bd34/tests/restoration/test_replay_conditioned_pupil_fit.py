from __future__ import annotations

import inspect
import math

import torch

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    CoherentPupilBench,
    CoherentPupilScene,
)
from experiments.restoration.adaptive_measurement.sensing.quadrature import (
    demodulate_phase_shifted_observations,
)
from experiments.restoration.adaptive_measurement.sensing.replay_conditioned_pupil_fit import (
    fit_replay_conditioned_pupil_phase,
)
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.phase_control import IdealPhaseDelivery, PhaseCommand
from experiments.restoration.pupil_aberrations import (
    PupilAberrationState,
    build_pupil_aberration_phase,
)


def test_replay_conditioned_fit_cannot_accept_evaluator_truth() -> None:
    parameter_names = tuple(
        inspect.signature(fit_replay_conditioned_pupil_phase).parameters
    )

    assert "evaluator_target_intensity" not in parameter_names
    assert "aberration_phase_radians" not in parameter_names
    assert "oracle_action" not in parameter_names


def test_replay_conditioned_fit_recovers_hidden_coma_from_four_intensities() -> None:
    resolution = (32, 32)
    config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    generator = torch.Generator().manual_seed(2026)
    degraded_intensity = 0.2 + 0.8 * torch.rand(
        resolution,
        generator=generator,
    )
    replay_input_field = torch.sqrt(degraded_intensity).to(torch.complex64)[None]
    aberration, pupil = build_pupil_aberration_phase(
        resolution,
        PupilAberrationState({"coma_horizontal": 0.8}),
    )
    scene = CoherentPupilScene(replay_input_field, aberration, pupil)
    bench = CoherentPupilBench(config, IdealPhaseDelivery())
    zero_phase = torch.zeros(resolution)
    observations = tuple(
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

    result = fit_replay_conditioned_pupil_phase(
        demodulate_phase_shifted_observations(observations),
        replay_input_field,
        config,
        pupil,
        iteration_count=120,
    )

    assert abs(result.coefficients_radians["coma_horizontal"] - 0.8) < 0.02
    assert result.fitted_cross_term_nrmse < 1e-3
    assert result.fitted_cross_term_nrmse < result.initial_cross_term_nrmse

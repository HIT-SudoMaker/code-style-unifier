from __future__ import annotations

import torch

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    CoherentPupilBench,
    CoherentPupilScene,
    SimulatedBench,
)
from experiments.restoration.phase_control import (
    IdealPhaseDelivery,
    PhaseCommand,
    SimulatedSlmPhaseDelivery,
)
from experiments.restoration.optical_bench import (
    OpticalBenchConfig,
    propagate_interferometric_bench,
)
from experiments.restoration.pupil_aberrations import (
    PupilAberrationState,
    build_pupil_aberration_phase,
)
from experiments.restoration.targets import siemens_star


def test_ideal_phase_correction_improves_a_later_science_observation() -> None:
    resolution = (64, 64)
    target = torch.from_numpy(siemens_star(resolution).image)
    object_field = torch.sqrt(target).to(torch.complex64)[None, None]
    aberration, pupil = build_pupil_aberration_phase(
        resolution,
        PupilAberrationState({"defocus": 1.4, "astigmatism_oblique": 0.5}),
    )
    bench = CoherentPupilBench(
        OpticalBenchConfig(
            input_array_resolution=resolution,
            phase_mask_resolution=min(resolution),
        ),
        IdealPhaseDelivery(),
    )
    reference_scene = CoherentPupilScene(
        object_field,
        torch.zeros_like(aberration),
        pupil,
    )
    aberrated_scene = CoherentPupilScene(object_field, aberration, pupil)
    reference = bench.acquire(
        reference_scene,
        PhaseCommand("reference", torch.zeros_like(aberration)),
        observation_id="science-reference",
        kind="science",
        sequence_index=0,
    )
    safe = bench.acquire(
        aberrated_scene,
        PhaseCommand("safe", torch.zeros_like(aberration)),
        observation_id="science-safe",
        kind="science",
        sequence_index=1,
    )
    corrected = bench.acquire(
        aberrated_scene,
        PhaseCommand("oracle", -aberration),
        observation_id="science-corrected",
        kind="science",
        sequence_index=2,
    )

    safe_error = torch.mean((safe.intensity - reference.intensity).square())
    corrected_error = torch.mean((corrected.intensity - reference.intensity).square())

    assert corrected_error < safe_error * 1e-4
    assert corrected.is_reference_enabled is True
    assert corrected.observation_id != safe.observation_id


def test_same_device_bench_delivers_the_complete_composite_once() -> None:
    resolution = (32, 32)
    bench_config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    displayed_intensity = 0.2 + 0.8 * torch.rand(
        (1, *resolution),
        generator=torch.Generator().manual_seed(41),
    )
    hidden_phase, pupil = build_pupil_aberration_phase(
        resolution,
        PupilAberrationState({"defocus": 0.8}),
    )
    action_phase = torch.rand(
        resolution,
        generator=torch.Generator().manual_seed(43),
    )
    delivery = SimulatedSlmPhaseDelivery(
        phase_levels=16,
        response_gain=0.91,
        drift_radians=0.13,
        crosstalk_mix=0.2,
    )
    bench = SimulatedBench(
        bench_config,
        delivery,
        displayed_intensity,
        hidden_phase,
        pupil,
        calibration_id="same-device-composite-v1",
    )
    command = PhaseCommand(
        "policy-action",
        action_phase,
        piston_radians=torch.pi / 2.0,
    )
    safe_command = PhaseCommand("safe-action", torch.zeros_like(hidden_phase))

    bench.acquire(
        safe_command,
        observation_id="b1-safe-baseline",
        kind="science",
        sequence_index=0,
    )
    bench.acquire(
        safe_command,
        observation_id="b2-safe-baseline",
        kind="science",
        sequence_index=1,
    )

    observation = bench.acquire(
        command,
        observation_id="composite-observation",
        kind="science",
        sequence_index=2,
    )
    b1_state, b2_state, composite_state = bench.read_evaluator_composite_states()
    expected_composite_command = PhaseCommand(
        "expected-composite",
        hidden_phase + action_phase,
        piston_radians=torch.pi / 2.0,
    )
    expected_composite_delivery = delivery.deliver(
        expected_composite_command,
        pupil=pupil,
    )
    expected_intensity = propagate_interferometric_bench(
        torch.sqrt(displayed_intensity).to(torch.complex64)[None],
        expected_composite_delivery.phase_radians,
        bench_config,
        processing_pupil=pupil,
    ).combined_intensity

    assert torch.allclose(
        composite_state.command.phase_radians,
        hidden_phase + action_phase,
    )
    assert torch.allclose(b1_state.command.phase_radians, hidden_phase)
    assert torch.allclose(b2_state.command.phase_radians, hidden_phase)
    assert torch.allclose(
        torch.exp(1j * b1_state.delivery.phase_radians),
        torch.exp(1j * b2_state.delivery.phase_radians),
        atol=1e-6,
        rtol=1e-6,
    )
    assert torch.allclose(
        torch.exp(1j * composite_state.delivery.phase_radians),
        torch.exp(1j * expected_composite_delivery.phase_radians),
        atol=1e-6,
        rtol=1e-6,
    )
    assert torch.allclose(observation.command_phase_radians, action_phase)
    assert torch.allclose(observation.intensity, expected_intensity)

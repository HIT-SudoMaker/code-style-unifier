from __future__ import annotations

from dataclasses import replace

import torch

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    CoherentPupilBench,
    CoherentPupilScene,
)
from experiments.restoration.fixed_measurement.optics.frontend import (
    RestorationFrontend,
)
from experiments.restoration.optical_bench import (
    DetectorNoiseModel,
    OpticalBenchConfig,
    propagate_interferometric_bench,
)
from experiments.restoration.phase_control import IdealPhaseDelivery, PhaseCommand


def _unit_field(resolution: tuple[int, int]) -> torch.Tensor:
    generator = torch.Generator().manual_seed(17)
    amplitude = torch.rand(resolution, generator=generator)
    return torch.sqrt(amplitude).to(torch.complex64)[None, None]


def test_fixed_frontend_matches_the_shared_bench_operation() -> None:
    resolution = (32, 32)
    bench_config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    input_field = _unit_field(resolution)
    phase = torch.rand(resolution, generator=torch.Generator().manual_seed(23))
    frontend = RestorationFrontend(bench_config)
    with torch.no_grad():
        frontend.phase_mask_fourier.copy_(phase)

    expected = propagate_interferometric_bench(
        input_field,
        torch.remainder(phase * (2.0 * torch.pi), 2.0 * torch.pi),
        bench_config,
    ).combined_intensity

    assert torch.allclose(frontend(input_field), expected, atol=1e-6, rtol=1e-6)


def test_adaptive_acquisition_matches_the_shared_bench_operation() -> None:
    resolution = (32, 32)
    bench_config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    input_field = _unit_field(resolution)
    pupil = torch.ones(resolution)
    aberration = (
        torch.linspace(-0.4, 0.4, resolution[0]).unsqueeze(1).expand(resolution)
    )
    command = PhaseCommand(
        "shared-phase",
        torch.rand(resolution, generator=torch.Generator().manual_seed(29)),
    )
    delivery = IdealPhaseDelivery()
    delivered = delivery.deliver(command, pupil=pupil)
    bench = CoherentPupilBench(bench_config, delivery)

    observation = bench.acquire(
        CoherentPupilScene(input_field, aberration, pupil),
        command,
        observation_id="shared-bench",
        kind="science",
        sequence_index=0,
    )
    expected = propagate_interferometric_bench(
        input_field,
        delivered.phase_radians,
        bench_config,
        processing_aberration_radians=aberration,
        processing_pupil=pupil,
    ).combined_intensity

    assert torch.allclose(observation.intensity, expected, atol=1e-6, rtol=1e-6)


def test_adaptive_bench_uses_the_shared_seeded_detector_noise() -> None:
    resolution = (32, 32)
    bench_config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    input_field = _unit_field(resolution)
    pupil = torch.ones(resolution)
    scene = CoherentPupilScene(input_field, torch.zeros(resolution), pupil)
    command = PhaseCommand("noise-equivalence", torch.zeros(resolution))
    clean_bench = CoherentPupilBench(bench_config, IdealPhaseDelivery())
    noisy_bench = CoherentPupilBench(
        bench_config,
        IdealPhaseDelivery(),
        photon_count=1_000.0,
        read_noise_standard_deviation=0.01,
        seed=71,
    )
    clean = clean_bench.acquire(
        scene,
        command,
        observation_id="clean",
        kind="science",
        sequence_index=3,
    )
    noisy = noisy_bench.acquire(
        scene,
        command,
        observation_id="noisy",
        kind="science",
        sequence_index=3,
    )

    expected = DetectorNoiseModel(
        photon_count=1_000.0,
        read_noise_standard_deviation=0.01,
        seed=71,
    ).sample(clean.intensity, sequence_index=3)

    assert torch.equal(noisy.intensity, expected)


def test_focal_length_changes_the_common_fourier_aperture() -> None:
    resolution = (128, 128)
    short_relay = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=128,
        focal_length=0.1,
    )
    long_relay = replace(short_relay, focal_length=0.2)
    input_field = torch.zeros((1, 1, *resolution), dtype=torch.complex64)
    input_field[..., resolution[0] // 2, resolution[1] // 2] = 1.0
    phase = torch.zeros(resolution)

    short_field = propagate_interferometric_bench(
        input_field,
        phase,
        short_relay,
    ).processing
    long_field = propagate_interferometric_bench(
        input_field,
        phase,
        long_relay,
    ).processing

    assert not torch.allclose(short_field, long_field)

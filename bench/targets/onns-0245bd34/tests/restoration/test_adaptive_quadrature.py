from __future__ import annotations

import math

import torch

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    CoherentPupilBench,
    CoherentPupilScene,
)
from experiments.restoration.adaptive_measurement.sensing.quadrature import (
    demodulate_phase_shifted_observations,
)
from experiments.restoration.optical_bench import (
    OpticalBenchConfig,
    propagate_interferometric_bench,
)
from experiments.restoration.phase_control import IdealPhaseDelivery, PhaseCommand
from experiments.restoration.pupil_aberrations import (
    PupilAberrationState,
    build_pupil_aberration_phase,
)
from experiments.restoration.targets import siemens_star


def test_quadrature_recovers_the_image_plane_cross_term() -> None:
    resolution = (64, 64)
    target = torch.from_numpy(siemens_star(resolution).image)
    object_field = torch.sqrt(target).to(torch.complex64)[None, None]
    aberration, pupil = build_pupil_aberration_phase(
        resolution,
        PupilAberrationState({"defocus": 1.2, "coma_horizontal": 0.4}),
    )
    config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=min(resolution),
    )
    scene = CoherentPupilScene(object_field, aberration, pupil)
    bench = CoherentPupilBench(config, IdealPhaseDelivery())
    spatial_action = torch.zeros_like(aberration)
    pistons = (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)
    observations = tuple(
        bench.acquire(
            scene,
            PhaseCommand(
                f"pre-{index}",
                spatial_action,
                piston_radians=piston,
            ),
            observation_id=f"pre-{index}",
            kind="calibration",
            sequence_index=index,
        )
        for index, piston in enumerate(pistons)
    )

    estimate = demodulate_phase_shifted_observations(observations)
    fields = propagate_interferometric_bench(
        object_field,
        spatial_action,
        config,
        processing_aberration_radians=aberration,
        processing_pupil=pupil,
    )
    expected = torch.conj(fields.reference) * fields.processing
    relative_error = torch.linalg.vector_norm(estimate.cross_term - expected)
    relative_error /= torch.linalg.vector_norm(expected)

    assert relative_error.item() < 1e-5
    assert estimate.design_condition_number < 2.0

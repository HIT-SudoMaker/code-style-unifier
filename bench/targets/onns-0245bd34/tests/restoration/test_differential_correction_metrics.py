from __future__ import annotations

import math

import torch

from experiments.restoration.observations import OpticalObservation
from experiments.restoration.studies.differential_correction import (
    _evaluate_metrics,
)


def test_fixed_aligned_metrics_score_the_full_display_canvas() -> None:
    resolution = (512, 512)
    clean_target = torch.full((1, *resolution), 0.5)
    degraded_intensity = clean_target.clone()
    b0_intensity = clean_target[None].clone()
    b1_intensity = b0_intensity.clone()
    b1_intensity[..., :64, :] = 0.0
    observations = tuple(
        _observation(name, intensity, sequence_index=index)
        for index, (name, intensity) in enumerate(
            (
                ("b0", b0_intensity),
                ("b1", b1_intensity),
                ("b2", b0_intensity),
                ("b3", b0_intensity),
            )
        )
    )

    metrics = _evaluate_metrics(
        degraded_intensity,
        clean_target,
        *observations,
    )

    assert math.isinf(metrics["b1_active_clean_psnr_db"])
    assert math.isfinite(metrics["b1_fixed_aligned_clean_psnr_db"])
    assert metrics["b1_fixed_aligned_clean_psnr_db"] < 20.0


def _observation(
    observation_id: str,
    intensity: torch.Tensor,
    *,
    sequence_index: int,
) -> OpticalObservation:
    phase = torch.zeros(intensity.shape[-2:])
    return OpticalObservation(
        observation_id=observation_id,
        kind="science",
        sequence_index=sequence_index,
        intensity=intensity,
        command_id=f"{observation_id}-command",
        command_phase_radians=phase,
        delivered_phase_radians=phase,
        delivery_model="test",
        is_reference_enabled=True,
    )

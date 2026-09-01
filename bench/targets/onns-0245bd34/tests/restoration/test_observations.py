from __future__ import annotations

import pytest
import torch

from experiments.restoration.observations import OpticalObservation


def test_optical_observation_freezes_detector_evidence() -> None:
    intensity = torch.ones((1, 1, 8, 8))
    observation = OpticalObservation(
        observation_id="science-001",
        kind="science",
        sequence_index=3,
        intensity=intensity,
        command_id="held-correction",
        command_phase_radians=torch.zeros((8, 8)),
        delivered_phase_radians=torch.ones((8, 8)),
        delivery_model="simulated_slm_phase",
        is_reference_enabled=False,
        elapsed_time_s=0.15,
        metadata={"frame_id": "frame-001"},
    )
    intensity.zero_()

    assert torch.all(observation.intensity == 1.0)
    assert torch.all(observation.delivered_phase_radians == 1.0)
    assert observation.metadata["frame_id"] == "frame-001"


def test_optical_observation_rejects_negative_intensity() -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        OpticalObservation(
            observation_id="bad",
            kind="science",
            sequence_index=0,
            intensity=torch.full((2, 2), -1.0),
            command_id="safe",
            command_phase_radians=torch.zeros((2, 2)),
            delivered_phase_radians=torch.zeros((2, 2)),
            delivery_model="ideal",
            is_reference_enabled=False,
        )

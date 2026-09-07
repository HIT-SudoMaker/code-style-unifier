from __future__ import annotations

import torch
from torch.utils.data import Dataset

from data.configs import SourceConfig
from experiments.restoration.adaptive_measurement.inputs.replay_scene import (
    AdaptiveReplayDataConfig,
    AdaptiveReplayDataset,
)
from experiments.restoration.degradation import (
    STANDARD_RESTORATION_PROFILE_NAMES,
    restoration_profile,
)
from experiments.restoration.fixed_measurement.learning.standard_configs import (
    build_standard_dataset_config,
)
from experiments.restoration.input_protocol import build_restoration_source


class _EncodedSceneDataset(Dataset):
    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> dict[str, object]:
        if index != 0:
            raise IndexError(index)
        intensity = torch.linspace(0.0, 1.0, 512).repeat(512, 1).unsqueeze(0)
        return {
            "input_image": intensity,
            "input_field": torch.sqrt(intensity).to(torch.complex64),
            "reference_image": torch.ones_like(intensity),
            "label": 0,
            "category": "gradient",
            "provenance": {"image_id": "synthetic/gradient"},
        }


def test_adaptive_replay_scene_loads_the_degraded_image_on_slm1() -> None:
    dataset = AdaptiveReplayDataset(_EncodedSceneDataset())
    scene = dataset[0]

    assert scene.scene_id == "synthetic/gradient"
    assert scene.input_field.shape == (1, 512, 512)
    assert torch.allclose(scene.input_field.abs().square(), scene.degraded_intensity)
    assert torch.equal(scene.evaluator_target_intensity, torch.ones((1, 512, 512)))

    selected = dataset.scene_by_id("synthetic/gradient")
    assert selected.scene_id == scene.scene_id


def test_adaptive_replay_uses_the_fixed_preparation_geometry() -> None:
    config = AdaptiveReplayDataConfig(
        source=SourceConfig(dataset_name="fmd", dataset_root="data/raw")
    )

    assert config.preparation.image_resolution == (256, 256)
    assert config.preparation.array_resolution == (512, 512)
    assert config.preparation.normalization_method == "auto"
    assert config.preparation.resize_interpolation_method == "bilinear"
    assert config.preparation.edge_taper_width == 0
    assert config.perturbation == restoration_profile("medium")


def test_fixed_and_adaptive_share_every_input_contract() -> None:
    """Prevent a nominally matched comparison from drifting at any data stage."""
    source = build_restoration_source("data/raw")

    for profile_name in STANDARD_RESTORATION_PROFILE_NAMES:
        adaptive_config = AdaptiveReplayDataConfig(
            source=source,
            perturbation=restoration_profile(profile_name),
        )
        fixed_wrapper = build_standard_dataset_config(
            profile_name=profile_name,
            split="val",
            split_manifest={"records": []},
            dataset_root="data/raw",
        )
        fixed_config = fixed_wrapper["dataset_config"]

        assert adaptive_config.source == fixed_config.source
        assert adaptive_config.preparation == fixed_config.preparation
        assert adaptive_config.perturbation == fixed_config.perturbation
        assert adaptive_config.encoding == fixed_config.encoding

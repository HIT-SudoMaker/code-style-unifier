from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import torch
from torch.utils.data import Dataset

from experiments.restoration.adaptive_measurement.inputs.comparison_protocol import (
    select_aligned_replay_scene,
)
from experiments.restoration.adaptive_measurement.inputs.replay_scene import (
    AdaptiveReplayDataset,
)


class _TwoSceneDataset(Dataset):
    scene_ids = ("fmd/scene-a", "fmd/scene-b")

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: int) -> dict[str, object]:
        scene_id = self.scene_ids[index]
        intensity = torch.full((1, 512, 512), float(index), dtype=torch.float32)
        return {
            "input_image": intensity,
            "input_field": torch.sqrt(intensity).to(torch.complex64),
            "reference_image": torch.ones_like(intensity),
            "label": index,
            "category": "synthetic",
            "provenance": {"image_id": scene_id},
        }


def test_comparison_protocol_selects_the_manifest_scene(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    payload = {
        "dataset_name": "fmd",
        "content_inventory_sha256": "a" * 64,
        "records": [
            {"image_id": "fmd/scene-a", "split": "train"},
            {"image_id": "fmd/scene-b", "split": "val"},
        ],
    }
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    selection = select_aligned_replay_scene(
        AdaptiveReplayDataset(_TwoSceneDataset()),
        manifest_path=manifest_path,
        split="val",
        scene_index=0,
    )

    assert selection.scene.scene_id == "fmd/scene-b"
    assert selection.split == "val"
    assert (
        selection.manifest_sha256
        == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    )


def test_comparison_protocol_rejects_an_out_of_range_scene(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_name": "fmd",
                "content_inventory_sha256": "a" * 64,
                "records": [{"image_id": "fmd/scene-a", "split": "val"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="split size"):
        select_aligned_replay_scene(
            AdaptiveReplayDataset(_TwoSceneDataset()),
            manifest_path=manifest_path,
            split="val",
            scene_index=1,
        )

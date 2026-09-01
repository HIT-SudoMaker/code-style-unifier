from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from numbers import Integral
from pathlib import Path

from experiments.restoration.adaptive_measurement.inputs.replay_scene import (
    AdaptiveReplayDataset,
    AdaptiveReplayScene,
)
from experiments.restoration.errors import invalid_restoration_contract


DEFAULT_FIXED_SPLIT_MANIFEST = Path(
    "experiments/restoration/fixed_measurement/protocol_assets/"
    "fmd_split_manifest.json"
)
ALIGNED_EVALUATION_SPLITS = ("train", "val", "test")


@dataclass(frozen=True, slots=True)
class AlignedReplaySelection:
    """Bind one Adaptive scene to the immutable Fixed split identity."""

    scene: AdaptiveReplayScene
    split: str
    scene_index: int
    manifest_path: Path
    manifest_sha256: str
    content_inventory_sha256: str


def select_aligned_replay_scene(
    dataset: AdaptiveReplayDataset,
    *,
    manifest_path: Path | str,
    split: str,
    scene_index: int,
) -> AlignedReplaySelection:
    """Select the same manifest scene used by the Fixed evaluation protocol."""
    if not isinstance(dataset, AdaptiveReplayDataset):
        raise TypeError("dataset must be an AdaptiveReplayDataset")
    if split not in ALIGNED_EVALUATION_SPLITS:
        raise invalid_restoration_contract("split must be one of: train, val, test")
    if (
        isinstance(scene_index, bool)
        or not isinstance(scene_index, Integral)
        or int(scene_index) < 0
    ):
        raise invalid_restoration_contract("scene_index must be a nonnegative integer")
    resolved_manifest = Path(manifest_path).resolve()
    payload = json.loads(resolved_manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or payload.get("dataset_name") != "fmd":
        raise invalid_restoration_contract(
            "aligned comparison requires the canonical FMD split manifest"
        )
    records = payload.get("records")
    if not isinstance(records, list):
        raise invalid_restoration_contract("split manifest records must be a list")
    split_scene_ids = tuple(
        record.get("image_id")
        for record in records
        if isinstance(record, Mapping) and record.get("split") == split
    )
    if not split_scene_ids or not all(
        isinstance(scene_id, str) and scene_id for scene_id in split_scene_ids
    ):
        raise invalid_restoration_contract(
            f"split manifest contains no valid {split} scenes"
        )
    selected_index = int(scene_index)
    if selected_index >= len(split_scene_ids):
        raise invalid_restoration_contract(
            f"scene_index exceeds the {split} split size of {len(split_scene_ids)}"
        )
    inventory_hash = payload.get("content_inventory_sha256")
    if not isinstance(inventory_hash, str) or len(inventory_hash) != 64:
        raise invalid_restoration_contract(
            "split manifest must preserve its content inventory hash"
        )
    selected_scene_id = split_scene_ids[selected_index]
    assert isinstance(selected_scene_id, str)
    return AlignedReplaySelection(
        scene=dataset.scene_by_id(selected_scene_id),
        split=split,
        scene_index=selected_index,
        manifest_path=resolved_manifest,
        manifest_sha256=compute_file_sha256(resolved_manifest),
        content_inventory_sha256=inventory_hash,
    )


def compute_file_sha256(path: Path | str) -> str:
    """Hash one protocol asset without depending on an experiment package."""
    resolved_path = Path(path)
    digest = hashlib.sha256()
    with resolved_path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

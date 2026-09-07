from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset, default_collate

from data import encode, load, perturb, prepare
from data.configs import (
    EncodingConfig,
    PerturbationConfig,
    PreparationConfig,
    SourceConfig,
)
from experiments.restoration.fixed_measurement.learning.data_contract import (
    RestorationBatch,
    RestorationDataContractError,
)
from experiments.restoration.fixed_measurement.learning.splits import SplitFilteredDataset


_MISSING_COLLATE_VALUE = object()
_DATASET_CONFIG_REQUIRED = "dataset_config must not be None"
_RESTORATION_DATASET_REQUIRED = (
    "build_restoration_dataset must return a torch Dataset"
)
_SPLIT_OPTIONS_REQUIRED = "split must be one of: train, val, test"
_SPLIT_STRING_REQUIRED = "split must be a string"
_SPLIT_MANIFEST_MAPPING_REQUIRED = "split_manifest must be a Mapping"
_COLLATION_MAPPING_REQUIRED = "restoration collation must produce a mapping"
_CLEAN_IMAGE_REQUIRED = "batch must include clean_image tensor"
_DEGRADED_IMAGE_REQUIRED = "batch must include degraded_image tensor"
_INPUT_FIELD_TENSOR_REQUIRED = "input_field must be a tensor"
_INPUT_FIELD_SHAPE_REQUIRED = "input_field must have shape (B, 1, H, W)"


@dataclass(frozen=True, slots=True)
class RestorationDataConfig:
    """Stages assembled by a restoration experiment."""

    source: SourceConfig
    preparation: PreparationConfig = field(default_factory=PreparationConfig)
    perturbation: PerturbationConfig = field(default_factory=PerturbationConfig)
    encoding: EncodingConfig = field(
        default_factory=lambda: EncodingConfig(encoding_method="intensity")
    )

    def _config_hash_payload(self) -> dict[str, object]:
        """Preserve the archived identity of the implicit encoded output."""
        return {
            "source": self.source,
            "preparation": self.preparation,
            "perturbation": self.perturbation,
            "encoding": self.encoding,
            "output_stage": "encoded",
        }


class RestorationDataset(Dataset):
    """Name generic encoded-stage fields in restoration terminology."""

    def __init__(self, source: Dataset) -> None:
        self.source = source

    def __len__(self) -> int:
        return len(self.source)

    def __getitem__(self, index: int) -> dict[str, Any]:
        sample = self.source[index]
        if not isinstance(sample, Mapping):
            raise RestorationDataContractError("encoded sample must be a mapping")
        reference_image = sample.get("reference_image")
        if not isinstance(reference_image, torch.Tensor):
            raise RestorationDataContractError(
                "encoded sample must include reference_image"
            )
        degraded_image = sample.get("input_image")
        if not isinstance(degraded_image, torch.Tensor):
            raise RestorationDataContractError(
                "encoded sample must include input_image"
            )
        return {
            "clean_image": reference_image,
            "degraded_image": degraded_image,
            "input_field": sample["input_field"],
            "label": sample["label"],
            "category": sample["category"],
            "provenance": sample["provenance"],
        }


def build_restoration_dataset(config: RestorationDataConfig) -> RestorationDataset:
    """Assemble generic data stages for a restoration experiment."""
    if not isinstance(config, RestorationDataConfig):
        raise TypeError("config must be a RestorationDataConfig")
    source = load(config.source)
    prepared = prepare(source, config.preparation)
    perturbed = perturb(prepared, config.perturbation)
    encoded = encode(perturbed, config.encoding)
    return RestorationDataset(encoded)


def build_restoration_loader(
    dataset_config: object,
    batch_size: int,
    is_shuffle_enabled: bool,
) -> DataLoader:
    """
    鏋勫缓 restoration 瀹為獙浣跨敤鐨勬暟鎹姞杞藉櫒
    """
    if dataset_config is None:
        raise ValueError(_DATASET_CONFIG_REQUIRED)
    inner_config, split_manifest, split = _split_aware_dataset_config(dataset_config)
    dataset = build_restoration_dataset(inner_config)  # type: ignore[arg-type]
    if not isinstance(dataset, Dataset):
        raise ValueError(_RESTORATION_DATASET_REQUIRED)
    if split_manifest is not None and split is not None:
        if split not in ("train", "val", "test"):
            raise ValueError(_SPLIT_OPTIONS_REQUIRED)
        dataset = SplitFilteredDataset(dataset, manifest=split_manifest, split=split)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=is_shuffle_enabled,
        collate_fn=collate_restoration_batch,
    )


def _split_aware_dataset_config(
    dataset_config: object,
) -> tuple[object, Mapping[str, object] | None, str | None]:
    if not isinstance(dataset_config, Mapping):
        return dataset_config, None, None
    if not {"dataset_config", "split_manifest", "split"}.issubset(dataset_config):
        return dataset_config, None, None

    split = dataset_config["split"]
    split_manifest = dataset_config["split_manifest"]
    if not isinstance(split, str):
        raise ValueError(_SPLIT_STRING_REQUIRED)
    if not isinstance(split_manifest, Mapping):
        raise ValueError(_SPLIT_MANIFEST_MAPPING_REQUIRED)
    return dataset_config["dataset_config"], split_manifest, split


def collate_restoration_batch(batch: list[object]) -> RestorationBatch:
    """
    鍚堝苟 restoration batch 骞剁Щ闄や笉鍙?collate 瀛楁
    """
    collated = default_collate([clean_collate_item(item) for item in batch])
    if not isinstance(collated, Mapping):
        raise RestorationDataContractError(_COLLATION_MAPPING_REQUIRED)
    return RestorationBatch.from_collated(collated)


def clean_collate_item(value: object) -> object:
    """
    娓呯悊鍗曚釜 batch 鍏冪礌涓殑绌哄€煎拰璺緞
    """
    if value is None:
        return _MISSING_COLLATE_VALUE
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        cleaned = {
            key: cleaned_value
            for key, raw_value in value.items()
            if (cleaned_value := clean_collate_item(raw_value))
            is not _MISSING_COLLATE_VALUE
        }
        return cleaned if cleaned else _MISSING_COLLATE_VALUE
    if isinstance(value, tuple):
        cleaned_values = tuple(
            cleaned_value
            for raw_value in value
            if (cleaned_value := clean_collate_item(raw_value))
            is not _MISSING_COLLATE_VALUE
        )
        return cleaned_values if cleaned_values else _MISSING_COLLATE_VALUE
    if isinstance(value, list):
        cleaned_values = [
            cleaned_value
            for raw_value in value
            if (cleaned_value := clean_collate_item(raw_value))
            is not _MISSING_COLLATE_VALUE
        ]
        return cleaned_values if cleaned_values else _MISSING_COLLATE_VALUE
    return value


def target_from_batch(batch: Mapping[str, object]) -> torch.Tensor:
    """
    浠?batch 涓彇鍑哄共鍑€鐩爣鍥惧儚
    """
    value = batch.get("clean_image")
    if isinstance(value, torch.Tensor):
        return value
    raise ValueError(_CLEAN_IMAGE_REQUIRED)


def degraded_from_batch(batch: Mapping[str, object]) -> torch.Tensor:
    """
    浠?batch 涓彇鍑洪€€鍖栬緭鍏ュ浘鍍?    """
    value = batch.get("degraded_image")
    if isinstance(value, torch.Tensor):
        return value
    raise RestorationDataContractError(_DEGRADED_IMAGE_REQUIRED)


def ensure_batched_field(input_field: torch.Tensor) -> torch.Tensor:
    """
    纭繚杈撳叆澶嶅満鍏锋湁鎵归噺缁村害
    """
    if not isinstance(input_field, torch.Tensor):
        raise ValueError(_INPUT_FIELD_TENSOR_REQUIRED)
    if input_field.ndim == 3:
        input_field = input_field.unsqueeze(0)
    if input_field.ndim != 4:
        raise ValueError(_INPUT_FIELD_SHAPE_REQUIRED)
    return input_field

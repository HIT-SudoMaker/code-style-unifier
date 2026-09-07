from __future__ import annotations

from copy import deepcopy
from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset, random_split

from experiments.classification.geometry import (
    ClassificationGeometry,
    get_classification_geometry,
)

CLASSIFICATION_DATASET_NAME = "mnist"
DEFAULT_CLASSIFICATION_GEOMETRY = get_classification_geometry("without_lens")
CLASSIFICATION_IMAGE_RESOLUTION = DEFAULT_CLASSIFICATION_GEOMETRY.image_resolution
CLASSIFICATION_ARRAY_RESOLUTION = DEFAULT_CLASSIFICATION_GEOMETRY.array_resolution
CLASSIFICATION_ENCODING_METHOD = "intensity"
CLASSIFICATION_BATCH_SIZE = 200
CLASSIFICATION_VALIDATION_SIZE = 10_000
CLASSIFICATION_SPLIT_SEED = 42

CLASSIFICATION_DETECTOR_SIZE = DEFAULT_CLASSIFICATION_GEOMETRY.detector_size
CLASSIFICATION_DETECTOR_PADDING = DEFAULT_CLASSIFICATION_GEOMETRY.detector_padding
CLASSIFICATION_DETECTOR_SETS = DEFAULT_CLASSIFICATION_GEOMETRY.detector_sets
CLASSIFICATION_DETECTOR_STEPS_X = DEFAULT_CLASSIFICATION_GEOMETRY.detector_steps_x
CLASSIFICATION_DETECTOR_STEP_Y = DEFAULT_CLASSIFICATION_GEOMETRY.detector_step_y
CLASSIFICATION_DETECTOR_COUNT = len(DEFAULT_CLASSIFICATION_GEOMETRY.detector_regions)
CLASSIFICATION_DETECTOR_REGIONS = DEFAULT_CLASSIFICATION_GEOMETRY.detector_regions
SUPPORTED_RESIZE_MODES = ("nearest", "bilinear")


def build_detector_targets(
    *,
    geometry: ClassificationGeometry | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Build detector masks and one-hot targets for a classification geometry."""
    geometry = geometry or DEFAULT_CLASSIFICATION_GEOMETRY
    detector_regions = geometry.detector_regions
    masks = torch.zeros(
        (len(detector_regions), 1, *geometry.array_resolution),
        dtype=torch.float32,
    )
    for index, (x0, x1, y0, y1) in enumerate(detector_regions):
        masks[index, 0, y0:y1, x0:x1] = 1.0
    return masks, torch.eye(len(detector_regions), dtype=torch.float32)


class ClassificationDataset(Dataset):
    """Add classification targets to an encoded data-stage dataset."""

    def __init__(
        self,
        *,
        source_dataset: Dataset,
        topology: str = "without_lens",
    ) -> None:
        self.source_dataset = source_dataset
        self.geometry = get_classification_geometry(topology)
        self.target_detector_masks, self.target_detector_distributions = (
            build_detector_targets(geometry=self.geometry)
        )

    def __len__(self) -> int:
        return len(self.source_dataset)

    def __getitem__(self, index: int) -> dict[str, Any]:
        sample = self.source_dataset[index]
        if not isinstance(sample, dict):
            raise ValueError("encoded sample must be a mapping")

        provenance = sample.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError("encoded sample is missing provenance")
        encoding_method = provenance.get("encoding_method")
        if encoding_method != CLASSIFICATION_ENCODING_METHOD:
            raise ValueError(
                "encoding_method mismatch: "
                f"expected {CLASSIFICATION_ENCODING_METHOD}, got {encoding_method}"
            )

        preparation = provenance.get("preparation")
        if (
            not isinstance(preparation, dict)
            or tuple(preparation.get("image_resolution", ()))
            != self.geometry.image_resolution
            or tuple(preparation.get("array_resolution", ()))
            != self.geometry.array_resolution
        ):
            raise ValueError("encoded sample geometry does not match topology")

        label = int(sample["label"])
        if label < 0 or label >= len(self.target_detector_masks):
            raise ValueError(f"label out of range: {label}")

        return {
            "input_image": sample["input_image"],
            "input_field": sample["input_field"],
            "label": label,
            "target_detector_mask": self.target_detector_masks[label].clone(),
            "target_detector_distribution": self.target_detector_distributions[
                label
            ].clone(),
            "provenance": deepcopy(provenance),
        }


def _build_dataset(
    *,
    is_train: bool,
    topology: str,
    resize_mode: str,
    samples_per_class: int | None,
    random_seed: int,
) -> ClassificationDataset:
    from data import encode, load, prepare
    from data.configs import EncodingConfig, PreparationConfig, SourceConfig

    if resize_mode not in SUPPORTED_RESIZE_MODES:
        raise ValueError(f"Unsupported resize_mode: {resize_mode}")

    geometry = get_classification_geometry(topology)
    source = load(
        SourceConfig(
            dataset_name=CLASSIFICATION_DATASET_NAME,
            is_train=is_train,
            samples_per_class=samples_per_class,
            random_seed=random_seed,
        )
    )
    prepared = prepare(
        source,
        PreparationConfig(
            image_resolution=geometry.image_resolution,
            array_resolution=geometry.array_resolution,
            normalization_method="auto",
            resize_interpolation_method=resize_mode,
        ),
    )
    encoded = encode(
        prepared,
        EncodingConfig(encoding_method=CLASSIFICATION_ENCODING_METHOD),
    )
    return ClassificationDataset(source_dataset=encoded, topology=topology)


def _split_train_validation_dataset(dataset: Dataset) -> tuple[Dataset, Dataset]:
    sample_count = len(dataset)
    if sample_count < 2:
        return dataset, dataset
    validation_size = min(CLASSIFICATION_VALIDATION_SIZE, max(1, sample_count // 6))
    train_size = sample_count - validation_size
    if train_size <= 0:
        return dataset, dataset
    generator = torch.Generator().manual_seed(CLASSIFICATION_SPLIT_SEED)
    return random_split(dataset, [train_size, validation_size], generator=generator)


def build_classification_dataloaders(
    *,
    batch_size: int = CLASSIFICATION_BATCH_SIZE,
    topology: str = "without_lens",
    resize_mode: str = "bilinear",
    samples_per_class: int | None = None,
    random_seed: int = 42,
) -> dict[str, DataLoader]:
    """Assemble classification datasets and return train, validation, and test loaders."""
    train_dataset = _build_dataset(
        is_train=True,
        topology=topology,
        resize_mode=resize_mode,
        samples_per_class=samples_per_class,
        random_seed=random_seed,
    )
    test_dataset = _build_dataset(
        is_train=False,
        topology=topology,
        resize_mode=resize_mode,
        samples_per_class=samples_per_class,
        random_seed=random_seed,
    )
    train_dataset, val_dataset = _split_train_validation_dataset(train_dataset)
    generator = torch.Generator().manual_seed(random_seed)
    return {
        "train": DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            generator=generator,
        ),
        "val": DataLoader(val_dataset, batch_size=batch_size, shuffle=False),
        "test": DataLoader(test_dataset, batch_size=batch_size, shuffle=False),
    }

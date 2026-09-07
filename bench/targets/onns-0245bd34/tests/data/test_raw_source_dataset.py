from __future__ import annotations

import numpy as np
import pytest
import torch
from data.data_source.datasets.source_dataset import SourceImageDataset


class _FakeRawDataset:
    def __init__(self, image: np.ndarray) -> None:
        self.targets = np.array([1], dtype=np.int64)
        self._image = image

    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> tuple[np.ndarray, int]:
        return self._image, 1


def test_source_image_dataset_returns_raw_single_channel_sample() -> None:
    dataset = SourceImageDataset(
        raw_dataset=_FakeRawDataset(np.arange(16, dtype=np.uint8).reshape(4, 4)),
        class_names=["zero", "one"],
        dataset_name="mnist",
        split_name="train",
        samples_per_class=1,
        random_seed=7,
    )

    sample = dataset[0]

    assert isinstance(sample["image"], torch.Tensor)
    assert sample["image"].shape == (1, 4, 4)
    assert sample["image"].dtype == torch.float32
    assert float(sample["image"].max()) == 15.0
    assert sample["label"] == 1
    assert sample["category"] == "one"
    assert sample["provenance"]["dataset_name"] == "mnist"
    assert sample["provenance"]["split_name"] == "train"
    assert sample["provenance"]["source_index"] == 0
    assert sample["provenance"]["sampling_seed"] == 7
    assert sample["provenance"]["raw_resolution"] == (4, 4)
    assert "preprocessing_chain" not in sample["provenance"]
    assert "image_resolution" not in sample["provenance"]
    assert "array_resolution" not in sample["provenance"]


def test_source_image_dataset_accepts_explicit_single_channel_axis() -> None:
    dataset = SourceImageDataset(
        raw_dataset=_FakeRawDataset(np.arange(16, dtype=np.uint8).reshape(1, 4, 4)),
        class_names=["zero", "one"],
        dataset_name="mnist",
        split_name="train",
        samples_per_class=1,
        random_seed=7,
    )

    sample = dataset[0]

    assert sample["image"].shape == (1, 4, 4)
    assert sample["image"].dtype == torch.float32
    assert float(sample["image"][0, 0, 0]) == 0.0


def test_source_image_dataset_rejects_multi_channel_raw_input() -> None:
    dataset = SourceImageDataset(
        raw_dataset=_FakeRawDataset(np.ones((4, 4, 3), dtype=np.uint8)),
        class_names=["zero", "one"],
        dataset_name="mnist",
        split_name="train",
        samples_per_class=1,
        random_seed=7,
    )

    with pytest.raises(ValueError, match="单通道"):
        dataset[0]

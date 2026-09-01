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


def test_source_image_dataset_emits_provenance_for_single_channel_inputs() -> None:
    dataset = SourceImageDataset(
        raw_dataset=_FakeRawDataset(np.ones((4, 4), dtype=np.uint8)),
        class_names=["zero", "one"],
        dataset_name="mnist",
        split_name="train",
        samples_per_class=1,
        random_seed=7,
    )

    sample = dataset[0]

    assert sample["label"] == 1
    assert sample["provenance"]["dataset_name"] == "mnist"
    assert sample["provenance"]["split_name"] == "train"
    assert sample["provenance"]["source_index"] == 0
    assert sample["provenance"]["sampling_seed"] == 7
    assert sample["image"].shape == (1, 4, 4)
    assert sample["image"].dtype == torch.float32
    assert sample["provenance"] == {
        "dataset_name": "mnist",
        "split_name": "train",
        "image_id": "mnist/train/0",
        "source_index": 0,
        "sampled_index": 0,
        "source_path": "train/0",
        "provenance_url": "unknown",
        "license": "unknown",
        "source_metadata": {},
        "sampling_seed": 7,
        "is_stratified_sampled": True,
        "raw_resolution": (4, 4),
    }


def test_source_image_dataset_rejects_rgb_inputs_without_projection_rule() -> None:
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

from __future__ import annotations

import numpy as np
import pytest
from data._validation import normalize_resolution_pair
from data.data_source.datasets.source_dataset import SourceImageDataset


class _InvalidLabelRawDataset:
    targets = np.asarray([99])

    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> tuple[np.ndarray, int]:
        return np.zeros((2, 2), dtype=np.float32), int(self.targets[index])


def test_normalize_resolution_pair_rejects_bool_dimensions() -> None:
    with pytest.raises(ValueError, match="image_resolution"):
        normalize_resolution_pair("image_resolution", (True, 4))


def test_normalize_resolution_pair_returns_plain_int_tuple() -> None:
    assert normalize_resolution_pair("array_resolution", (np.int64(3), np.int64(4))) == (
        3,
        4,
    )


def test_source_image_dataset_rejects_out_of_range_label_with_context() -> None:
    dataset = SourceImageDataset(
        raw_dataset=_InvalidLabelRawDataset(),
        class_names=["zero"],
        dataset_name="custom",
        split_name="train",
        samples_per_class=None,
        random_seed=7,
    )

    with pytest.raises(ValueError, match="label out of range"):
        dataset[0]

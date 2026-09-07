from pathlib import Path

import numpy as np
import torch

import data.data_source.adapters.fashion_mnist as fashion_source
from data.data_source.adapters.fashion_mnist import BaseFashionMNISTDataset


class StubRawDataset:
    def __init__(self, labels: list[int]) -> None:
        self.images = np.stack(
            [np.full((28, 28), fill_value=label, dtype=np.uint8) for label in labels]
        )
        self.targets = np.array(labels, dtype=np.uint8)

    def __len__(self) -> int:
        return len(self.targets)

    def __getitem__(self, index: int) -> tuple[np.ndarray, int]:
        return self.images[index], int(self.targets[index])


def _install_local_raw_dataset(
    monkeypatch,
    dataset_root: Path,
    labels: list[int],
) -> None:
    (dataset_root / "fashion_mnist" / "raw").mkdir(parents=True)
    monkeypatch.setattr(
        fashion_source,
        "RawIDXVisionDataset",
        lambda **kwargs: StubRawDataset(labels),
    )


def test_base_fashion_mnist_dataset_returns_shared_sample_contract(monkeypatch, tmp_path):
    _install_local_raw_dataset(monkeypatch, tmp_path, list(range(10)))

    dataset = BaseFashionMNISTDataset(
        dataset_root=str(tmp_path),
        is_train=False,
        samples_per_class=1,
    )

    sample = dataset[0]

    assert set(sample.keys()) == {"image", "label", "category", "provenance"}
    assert sample["image"].shape == (1, 28, 28)
    assert sample["image"].dtype == torch.float32
    assert isinstance(sample["label"], int)
    assert isinstance(sample["category"], str)
    assert sample["provenance"]["dataset_name"] == "fashion_mnist"
    assert sample["provenance"]["split_name"] == "test"
    assert sample["provenance"]["raw_resolution"] == (28, 28)


def test_base_fashion_mnist_dataset_uses_prepared_local_idx_files(
    monkeypatch,
    tmp_path,
):
    _install_local_raw_dataset(monkeypatch, tmp_path, [0, 0, 1])

    dataset = BaseFashionMNISTDataset(
        dataset_root=str(tmp_path),
        is_train=False,
        samples_per_class=3,
    )

    sample = dataset[0]

    assert len(dataset) == 3
    assert [dataset[index]["label"] for index in range(len(dataset))] == [0, 0, 1]
    assert sample["label"] == 0
    assert sample["category"] == "T-shirt/top"


def test_base_fashion_mnist_dataset_rejects_missing_local_raw_files(tmp_path):
    try:
        BaseFashionMNISTDataset(
            dataset_root=str(tmp_path),
            is_train=False,
            samples_per_class=1,
        )
    except FileNotFoundError as exc:
        assert "fashion_mnist" in str(exc).lower()
        assert "raw" in str(exc).lower()
    else:
        raise AssertionError("Expected missing local FashionMNIST files to fail")


def test_base_fashion_mnist_dataset_does_not_download_when_local_raw_files_are_missing(
    tmp_path,
):
    try:
        BaseFashionMNISTDataset(
            dataset_root=str(tmp_path),
            is_train=False,
            samples_per_class=1,
        )
    except FileNotFoundError as exc:
        assert "fashion_mnist" in str(exc).lower()
        assert "raw" in str(exc).lower()
    else:
        raise AssertionError("Expected missing local FashionMNIST files to fail")


def test_base_fashion_mnist_dataset_returns_source_sample_contract(
    monkeypatch,
    tmp_path,
):
    _install_local_raw_dataset(monkeypatch, tmp_path, [5])
    dataset = BaseFashionMNISTDataset(
        dataset_root=str(tmp_path),
        is_train=False,
        samples_per_class=1,
    )
    sample = dataset[0]
    assert set(sample.keys()) == {"image", "label", "category", "provenance"}
    assert sample["image"].shape == (1, 28, 28)
    assert sample["image"].dtype == torch.float32
    assert sample["label"] == 5
    assert sample["provenance"]["dataset_name"] == "fashion_mnist"


def test_base_fashion_mnist_dataset_applies_max_samples(monkeypatch, tmp_path):
    _install_local_raw_dataset(monkeypatch, tmp_path, list(range(10)))

    dataset = BaseFashionMNISTDataset(
        dataset_root=str(tmp_path),
        is_train=False,
        max_samples=3,
    )

    assert len(dataset) == 3
    assert [dataset[index]["label"] for index in range(len(dataset))] == [0, 1, 2]


def test_base_fashion_mnist_dataset_rejects_non_default_source_sizing(
    monkeypatch,
    tmp_path,
):
    _install_local_raw_dataset(monkeypatch, tmp_path, [5])

    try:
        BaseFashionMNISTDataset(
            dataset_root=str(tmp_path),
            is_train=False,
            array_resolution=(64, 64),
            samples_per_class=1,
        )
    except ValueError as exc:
        message = str(exc)
        assert "data_source" in message
        assert "后续管线阶段" in message
    else:
        raise AssertionError("Expected non-default source sizing to be rejected")

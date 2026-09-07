from __future__ import annotations

import pytest
import torch
from torch.utils.data import Dataset

import data
from experiments.classification import dataset_adapter as adapter


class _FakeEncodedDataset(Dataset):
    def __init__(
        self,
        *,
        image_resolution: tuple[int, int] = (32, 32),
        array_resolution: tuple[int, int] = (64, 64),
    ) -> None:
        self.image_resolution = image_resolution
        self.array_resolution = array_resolution

    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> dict[str, object]:
        del index
        array_height, array_width = self.array_resolution
        return {
            "input_image": torch.ones(
                (1, array_height, array_width),
                dtype=torch.float32,
            ),
            "input_field": torch.ones(
                (1, array_height, array_width),
                dtype=torch.complex64,
            ),
            "label": 3,
            "provenance": {
                "dataset_name": "mnist",
                "stage": "encoded",
                "encoding_method": "intensity",
                "preparation": {
                    "image_resolution": self.image_resolution,
                    "array_resolution": self.array_resolution,
                },
            },
        }


def test_classification_constants_match_training_contract() -> None:
    assert adapter.CLASSIFICATION_ARRAY_RESOLUTION == (64, 64)
    assert adapter.get_classification_geometry("without_lens").array_resolution == (
        64,
        64,
    )
    assert adapter.get_classification_geometry("with_lens").array_resolution == (
        128,
        128,
    )
    assert adapter.CLASSIFICATION_BATCH_SIZE == 200
    assert adapter.CLASSIFICATION_ENCODING_METHOD == "intensity"
    assert adapter.CLASSIFICATION_VALIDATION_SIZE == 10_000
    assert adapter.CLASSIFICATION_SPLIT_SEED == 42


def test_classification_detector_regions_match_geometry() -> None:
    assert len(adapter.CLASSIFICATION_DETECTOR_REGIONS) == 10
    assert adapter.CLASSIFICATION_DETECTOR_REGIONS[0] == (6, 10, 6, 10)
    assert adapter.CLASSIFICATION_DETECTOR_REGIONS[3] == (6, 10, 30, 34)
    assert adapter.CLASSIFICATION_DETECTOR_REGIONS[-1] == (54, 58, 54, 58)


def test_build_detector_targets_returns_masks_and_one_hot_vectors() -> None:
    masks, vectors = adapter.build_detector_targets()

    assert masks.shape == (10, 1, 64, 64)
    assert vectors.shape == (10, 10)
    assert torch.equal(vectors, torch.eye(10, dtype=torch.float32))

    expected_mask = torch.zeros((1, 64, 64), dtype=torch.float32)
    expected_mask[0, 6:10, 6:10] = 1.0
    assert torch.equal(masks[0], expected_mask)

    interior_mask = torch.zeros((1, 64, 64), dtype=torch.float32)
    interior_mask[0, 30:34, 6:10] = 1.0
    assert torch.equal(masks[3], interior_mask)
    assert torch.count_nonzero(masks[3][0, 6:10, 30:34]) == 0


def test_build_detector_targets_accepts_with_lens_geometry() -> None:
    geometry = adapter.get_classification_geometry("with_lens")

    masks, vectors = adapter.build_detector_targets(geometry=geometry)

    assert masks.shape == (10, 1, 128, 128)
    assert vectors.shape == (10, 10)
    assert masks[0, 0, 32:41, 32:41].sum().item() == 81
    assert masks[9, 0, 86:95, 86:95].sum().item() == 81


def test_dataset_adapter_exposes_classification_dataset_api() -> None:
    removed_name = "Classification" + "ONNDataset"

    assert hasattr(adapter, "ClassificationDataset")
    assert not hasattr(adapter, removed_name)


def test_classification_dataset_wraps_encoded_samples() -> None:
    dataset = adapter.ClassificationDataset(source_dataset=_FakeEncodedDataset())

    sample = dataset[0]

    assert set(sample) == {
        "input_image",
        "input_field",
        "label",
        "target_detector_mask",
        "target_detector_distribution",
        "provenance",
    }
    assert sample["input_image"].shape == (1, 64, 64)
    assert sample["input_field"].dtype == torch.complex64
    assert sample["label"] == 3
    assert sample["target_detector_mask"].shape == (1, 64, 64)
    assert sample["target_detector_distribution"].shape == (10,)
    assert sample["provenance"]["encoding_method"] == "intensity"


def test_classification_dataset_uses_with_lens_geometry() -> None:
    dataset = adapter.ClassificationDataset(
        source_dataset=_FakeEncodedDataset(
            image_resolution=(64, 64),
            array_resolution=(128, 128),
        ),
        topology="with_lens",
    )

    sample = dataset[0]

    assert sample["input_image"].shape == (1, 128, 128)
    assert sample["input_field"].shape == (1, 128, 128)
    assert sample["target_detector_mask"].shape == (1, 128, 128)
    assert sample["provenance"]["preparation"]["image_resolution"] == (64, 64)
    assert sample["provenance"]["preparation"]["array_resolution"] == (128, 128)


def test_classification_dataset_rejects_encoded_geometry_mismatch() -> None:
    dataset = adapter.ClassificationDataset(
        source_dataset=_FakeEncodedDataset(array_resolution=(128, 128)),
        topology="without_lens",
    )

    with pytest.raises(ValueError, match="geometry"):
        dataset[0]


def test_classification_dataset_rejects_wrong_encoding_method() -> None:
    class _WrongEncodingDataset(_FakeEncodedDataset):
        def __getitem__(self, index: int) -> dict[str, object]:
            sample = super().__getitem__(index)
            sample["provenance"] = {
                **sample["provenance"],
                "encoding_method": "phase",
            }
            return sample

    dataset = adapter.ClassificationDataset(source_dataset=_WrongEncodingDataset())

    with pytest.raises(ValueError, match="encoding"):
        dataset[0]


def test_build_classification_dataloaders_assembles_data_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []

    def _fake_load(config: object) -> _FakeEncodedDataset:
        calls.append(("load", config))
        return _FakeEncodedDataset()

    def _fake_prepare(source: Dataset, config: object) -> Dataset:
        calls.append(("prepare", config))
        return source

    def _fake_encode(source: Dataset, config: object) -> Dataset:
        calls.append(("encode", config))
        return source

    monkeypatch.setattr(data, "load", _fake_load)
    monkeypatch.setattr(data, "prepare", _fake_prepare)
    monkeypatch.setattr(data, "encode", _fake_encode)

    dataloaders = adapter.build_classification_dataloaders()

    assert [name for name, _ in calls] == [
        "load",
        "prepare",
        "encode",
        "load",
        "prepare",
        "encode",
    ]
    load_configs = [config for name, config in calls if name == "load"]
    prepare_configs = [config for name, config in calls if name == "prepare"]
    encode_configs = [config for name, config in calls if name == "encode"]
    assert [config.dataset_name for config in load_configs] == ["mnist", "mnist"]
    assert [config.is_train for config in load_configs] == [True, False]
    assert all(config.array_resolution == (64, 64) for config in prepare_configs)
    assert all(config.encoding_method == "intensity" for config in encode_configs)
    assert set(dataloaders) == {"train", "val", "test"}
    train_loader = dataloaders["train"]
    val_loader = dataloaders["val"]
    test_loader = dataloaders["test"]
    assert isinstance(test_loader.dataset, adapter.ClassificationDataset)
    assert train_loader.batch_size == adapter.CLASSIFICATION_BATCH_SIZE
    assert val_loader.batch_size == adapter.CLASSIFICATION_BATCH_SIZE
    assert test_loader.batch_size == adapter.CLASSIFICATION_BATCH_SIZE


def test_split_train_validation_dataset_is_deterministic() -> None:
    source_dataset = adapter.ClassificationDataset(
        source_dataset=_FakeEncodedDataset(),
    )

    train_dataset, validation_dataset = adapter._split_train_validation_dataset(
        source_dataset,
    )

    assert train_dataset is source_dataset
    assert validation_dataset is source_dataset

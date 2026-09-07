from __future__ import annotations

from pathlib import Path

import pytest
import torch
from torch.utils.data import Dataset

from data.configs import (
    EncodingConfig,
    PerturbationConfig,
    PreparationConfig,
    SourceConfig,
)
from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.fixed_measurement.learning import data_loading
from experiments.restoration.fixed_measurement.learning.data_contract import RestorationBatch
from experiments.restoration.fixed_measurement.learning.splits import build_split_manifest, select_split_records


class _TinyRestorationDataset(Dataset):
    """
    鎻愪緵鏁版嵁鍔犺浇娴嬭瘯澶瑰叿
    """
    def __len__(self) -> int:
        """
        杩斿洖娴嬭瘯鏁版嵁闀垮害
        """
        return 2

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        杩斿洖鍗曚釜娴嬭瘯鏍锋湰
        """
        image = torch.full((1, 8, 8), float(index + 1) / 4.0)
        return {
            "input_field": torch.sqrt(image).to(torch.complex64),
            "input_image": image,
            "degraded_image": image,
            "clean_image": image + 0.1,
            "provenance": {"image_id": f"unit/example/{index}"},
            "path": Path(f"sample_{index}.png"),
            "empty": None,
        }


class _TinyProvenanceRestorationDataset(Dataset):
    """
    鎻愪緵娴嬭瘯杈呭姪鏇胯韩
    """
    def __len__(self) -> int:
        """
        鎻愪緵娴嬭瘯杈呭姪閫昏緫
        """
        return 3

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        鎻愪緵娴嬭瘯杈呭姪閫昏緫
        """
        image = torch.full((1, 8, 8), float(index + 1) / 4.0)
        return {
            "input_field": torch.sqrt(image).to(torch.complex64),
            "input_image": image,
            "degraded_image": image,
            "clean_image": image + 0.1,
            "provenance": {
                "image_id": f"fmd/Confocal_BPAE_G/{index + 1}/avg50",
            },
        }


def test_build_restoration_loader_uses_project_dataset_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鏁版嵁鍔犺浇濂戠害
    """
    monkeypatch.setattr(
        data_loading,
        "build_restoration_dataset",
        lambda config: _TinyRestorationDataset(),
    )

    loader = data_loading.build_restoration_loader(
        {"kind": "unit"},
        batch_size=2,
        is_shuffle_enabled=False,
    )
    batch = next(iter(loader))

    assert isinstance(batch, RestorationBatch)
    assert batch["input_field"].shape == (2, 1, 8, 8)
    assert "input_image" not in batch
    assert batch["degraded_image"].shape == (2, 1, 8, 8)
    assert batch["clean_image"].shape == (2, 1, 8, 8)
    assert batch["path"] == ["sample_0.png", "sample_1.png"]
    assert "empty" not in batch


def test_build_restoration_loader_applies_split_manifest_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    image_ids = [f"fmd/Confocal_BPAE_G/{index + 1}/avg50" for index in range(3)]
    manifest = build_split_manifest(
        image_ids=image_ids,
        source_paths=[f"sample_{index}.png" for index in range(3)],
        train_fraction=1 / 3,
        val_fraction=1 / 3,
        test_fraction=1 / 3,
    )
    selected_ids = {
        record["image_id"] for record in select_split_records(manifest, split="test")
    }
    monkeypatch.setattr(
        data_loading,
        "build_restoration_dataset",
        lambda config: _TinyProvenanceRestorationDataset(),
    )

    loader = data_loading.build_restoration_loader(
        {
            "dataset_config": {"kind": "unit"},
            "split_manifest": manifest,
            "split": "test",
            "profile_name": "medium",
        },
        batch_size=2,
        is_shuffle_enabled=False,
    )
    batch = next(iter(loader))

    assert batch["clean_image"].shape[0] == len(selected_ids)
    assert set(batch["provenance"]["image_id"]) == selected_ids


def test_build_restoration_loader_rejects_invalid_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鏁版嵁鍔犺浇濂戠害
    """
    with pytest.raises(ValueError, match="dataset_config must not be None"):
        data_loading.build_restoration_loader(
            None,
            batch_size=1,
            is_shuffle_enabled=False,
        )

    monkeypatch.setattr(data_loading, "build_restoration_dataset", lambda config: object())

    with pytest.raises(ValueError, match="build_restoration_dataset must return"):
        data_loading.build_restoration_loader(
            {"kind": "bad"},
            batch_size=1,
            is_shuffle_enabled=False,
        )


def test_build_restoration_dataset_assembles_stages_and_names_task_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class _EncodedDataset(Dataset):
        def __len__(self) -> int:
            return 1

        def __getitem__(self, index: int) -> dict[str, object]:
            del index
            degraded = torch.full((1, 8, 8), 0.25)
            return {
                "input_image": degraded,
                "input_field": torch.sqrt(degraded).to(torch.complex64),
                "reference_image": degraded + 0.1,
                "label": 0,
                "category": "unit",
                "provenance": {"image_id": "unit/0"},
            }

    def _stage(name: str):
        def apply(source: Dataset, config: object) -> Dataset:
            del config
            calls.append(name)
            return source

        return apply

    source = _EncodedDataset()

    def _load(config: object) -> Dataset:
        del config
        calls.append("load")
        return source

    monkeypatch.setattr(data_loading, "load", _load)
    monkeypatch.setattr(data_loading, "prepare", _stage("prepare"))
    monkeypatch.setattr(data_loading, "perturb", _stage("perturb"))
    monkeypatch.setattr(data_loading, "encode", _stage("encode"))

    config = data_loading.RestorationDataConfig(
        source=SourceConfig(dataset_name="unit"),
        preparation=PreparationConfig(),
        perturbation=PerturbationConfig(),
        encoding=EncodingConfig(encoding_method="intensity"),
    )
    dataset = data_loading.build_restoration_dataset(config)
    sample = dataset[0]

    assert calls == ["load", "prepare", "perturb", "encode"]
    assert set(sample) == {
        "clean_image",
        "degraded_image",
        "input_field",
        "label",
        "category",
        "provenance",
    }
    assert torch.equal(sample["clean_image"], source[0]["reference_image"])
    assert torch.equal(sample["degraded_image"], source[0]["input_image"])


def test_restoration_data_config_hash_preserves_archived_encoded_identity() -> None:
    config = data_loading.RestorationDataConfig(
        source=SourceConfig(dataset_name="unit"),
        preparation=PreparationConfig(),
        perturbation=PerturbationConfig(),
        encoding=EncodingConfig(encoding_method="intensity"),
    )

    expected_identity = {
        "source": config.source,
        "preparation": config.preparation,
        "perturbation": config.perturbation,
        "encoding": config.encoding,
        "output_stage": "encoded",
    }

    assert compute_config_hash(config) == compute_config_hash(expected_identity)


def test_target_from_batch_prefers_clean_image() -> None:
    """
    鏍￠獙鏁版嵁鍔犺浇濂戠害
    """
    batch = {
        "clean_image": torch.ones(1, 1, 4, 4),
        "input_image": torch.zeros(1, 1, 4, 4),
    }

    assert torch.equal(data_loading.target_from_batch(batch), batch["clean_image"])


def test_target_from_batch_requires_clean_image() -> None:
    """
    鏍￠獙鏁版嵁鍔犺浇濂戠害
    """
    with pytest.raises(ValueError, match="clean_image"):
        data_loading.target_from_batch({"input_image": torch.ones(1, 1, 4, 4)})
    with pytest.raises(ValueError, match="clean_image"):
        data_loading.target_from_batch({"clean_image": None, "input_image": None})


def test_degraded_from_batch_requires_degraded_image_by_name() -> None:
    """
    鏍￠獙鏁版嵁鍔犺浇濂戠害
    """
    degraded_image = torch.ones((2, 1, 8, 8), dtype=torch.float32)
    input_image = torch.zeros((2, 1, 8, 8), dtype=torch.float32)

    assert (
        data_loading.degraded_from_batch(
            {"degraded_image": degraded_image, "input_image": input_image}
        )
        is degraded_image
    )
    with pytest.raises(ValueError, match="degraded_image"):
        data_loading.degraded_from_batch({"input_image": input_image})
    with pytest.raises(ValueError, match="degraded_image"):
        data_loading.degraded_from_batch(
            {"degraded_image": None, "input_image": None}
        )


def test_ensure_batched_field_adds_missing_batch_dimension() -> None:
    """
    鏍￠獙鏁版嵁鍔犺浇濂戠害
    """
    field = torch.ones((1, 8, 8), dtype=torch.complex64)

    assert data_loading.ensure_batched_field(field).shape == (1, 1, 8, 8)


def test_ensure_batched_field_rejects_wrong_shape() -> None:
    """
    鏍￠獙鏁版嵁鍔犺浇濂戠害
    """
    with pytest.raises(ValueError, match="input_field must be a tensor"):
        data_loading.ensure_batched_field("bad")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="input_field must have shape"):
        data_loading.ensure_batched_field(torch.ones(8, 8))


def test_clean_collate_item_removes_none_and_paths() -> None:
    """
    鏍￠獙鏁版嵁鍔犺浇濂戠害
    """
    cleaned = data_loading.clean_collate_item(
        {
            "path": Path("sample.png"),
            "none": None,
            "value": 1,
            "nested": {"keep": Path("inner.png"), "drop": None},
            "items": [Path("a.png"), None, Path("b.png")],
            "pair": (Path("left.png"), None, 2),
        }
    )

    assert cleaned == {
        "path": "sample.png",
        "value": 1,
        "nested": {"keep": "inner.png"},
        "items": ["a.png", "b.png"],
        "pair": ("left.png", 2),
    }

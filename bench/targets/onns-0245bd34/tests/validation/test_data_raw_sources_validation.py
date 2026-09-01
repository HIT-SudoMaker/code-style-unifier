from __future__ import annotations

from pathlib import Path

import torch


class _FakeRawDataset:
    def __init__(self, dataset_name: str, classes: int = 6) -> None:
        """
        绑定fake raw dataset的名称和类别数
        """
        self.dataset_name = dataset_name
        self.classes = classes

    def __len__(self) -> int:
        """
        返回至少可展示6张图的样本数
        """
        return max(self.classes, 6)

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        返回带raw sample契约的fake样本
        """
        label = index % self.classes
        image = torch.full((1, 8, 8), float(label) / 10.0, dtype=torch.float32)
        return {
            "image": image,
            "label": label,
            "category": f"class_{label}",
            "provenance": {
                "dataset_name": self.dataset_name,
                "split_name": "validation",
                "source_index": index,
                "sampled_index": index,
                "raw_resolution": (8, 8),
                "image_id": f"{self.dataset_name}/{index}",
                "source_path": f"{self.dataset_name}/{index}.png",
            },
        }


def test_raw_sources_validation_writes_required_artifacts(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证raw source validator写出必需artifact
    """
    from experiments.validation.data import validate_raw_sources

    def _fake_build_raw_dataset(
        dataset_name: str,
        **kwargs: object,
    ) -> _FakeRawDataset:
        del kwargs
        classes = 10 if dataset_name in {"mnist", "fashion_mnist"} else 6
        return _FakeRawDataset(dataset_name, classes=classes)

    monkeypatch.setattr(
        validate_raw_sources,
        "build_raw_dataset",
        _fake_build_raw_dataset,
    )
    monkeypatch.setattr(
        validate_raw_sources,
        "_asset_readiness_records",
        lambda dataset_root: [
            {"source": name, "expected_path": str(tmp_path / name), "is_ready": True}
            for name in validate_raw_sources.CORE_SOURCE_NAMES
        ],
    )

    result = validate_raw_sources.run(output_root=tmp_path, seed=7, size="tiny")

    output_dir = tmp_path / "raw_sources"
    assert result["data"] == "raw_sources"
    assert result["status"] == "PASS"
    assert {check["name"] for check in result["checks"]} == {
        "raw_asset_readiness",
        "dataset_construction",
        "sample_contract",
        "image_contract",
        "provenance_contract",
        "class_coverage",
    }
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "metrics.csv").exists()
    for figure_name in (
        "01_raw_source_gallery_mnist",
        "02_raw_source_gallery_fashion_mnist",
        "03_raw_source_gallery_microscopy",
        "04_raw_source_gallery_targets",
    ):
        assert (output_dir / f"{figure_name}.png").exists()
        assert (output_dir / f"{figure_name}.svg").exists()


def test_raw_sources_validation_keeps_classification_scan_window() -> None:
    """
    Classification galleries need enough raw samples to find all ten classes.
    """
    from experiments.validation.data import validate_raw_sources

    assert validate_raw_sources._max_samples_for_source("mnist", size="tiny") == 512
    assert validate_raw_sources._max_samples_for_source("fashion_mnist", size="tiny") == 512
    assert validate_raw_sources._max_samples_for_source("fmd", size="tiny") == 6


def test_raw_sources_validation_fails_when_core_asset_is_missing(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证核心raw资产缺失时validator失败
    """
    from experiments.validation.data import validate_raw_sources

    monkeypatch.setattr(
        validate_raw_sources,
        "_asset_readiness_records",
        lambda dataset_root: [
            {
                "source": "fmd",
                "expected_path": str(tmp_path / "fmd" / "averaged"),
                "is_ready": False,
            }
        ],
    )

    result = validate_raw_sources.run(output_root=tmp_path, seed=7, size="tiny")

    assert result["status"] == "FAIL"
    readiness = next(
        check for check in result["checks"] if check["name"] == "raw_asset_readiness"
    )
    assert readiness["status"] == "FAIL"
    assert "fmd" in str(readiness["detail"])

from __future__ import annotations

import csv
from pathlib import Path

import torch

_CHECK_NAMES = {
    "pipeline_recipe_construction",
    "multi_sample_pipeline_execution",
    "clean_degraded_reference_preservation",
    "encoded_field_contract",
    "pipeline_provenance_contract",
    "restoration_operator_scope",
}

_OPERATOR_FAMILY_RECIPE_NAMES = {
    "additive_gaussian_noise",
    "poisson_gaussian_noise",
    "gaussian_blur",
    "defocus_blur",
    "psf_convolution",
}

_RESTORATION_RECIPE_NAMES = {
    "noise",
    "blur",
    "defocus",
    "combined_degradation",
}


class _FakeRawDataset:
    def __len__(self) -> int:
        """
        返回端到端网格所需的3个fake样本
        """
        return 3

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        返回带FMD-like provenance的fake raw样本
        """
        base_image = torch.linspace(0.0, 1.0, 16 * 16, dtype=torch.float32)
        image = base_image.reshape(1, 16, 16).roll(shifts=index, dims=2)
        return {
            "image": image,
            "label": index,
            "category": f"fake-{index}",
            "provenance": {
                "dataset_name": "fake_fmd",
                "split_name": "validation",
                "source_index": index,
                "sampled_index": index,
                "sampling_seed": 100 + index,
                "raw_resolution": (16, 16),
            },
        }


def test_end_to_end_pipeline_validation_writes_artifacts_with_fake_fmd(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证端到端validator使用fake FMD写出必需artifact
    """
    from experiments.validation.data import validate_end_to_end_pipeline

    calls: list[tuple[str, int | None, int]] = []

    def _fake_build_raw_dataset(
        dataset_name: str,
        *,
        max_samples: int | None = None,
        random_seed: int = 42,
    ) -> _FakeRawDataset:
        calls.append((dataset_name, max_samples, random_seed))
        return _FakeRawDataset()

    monkeypatch.setattr(
        validate_end_to_end_pipeline,
        "build_raw_dataset",
        _fake_build_raw_dataset,
    )

    result = validate_end_to_end_pipeline.run(
        output_root=tmp_path,
        device="cpu",
        seed=7,
        size="tiny",
    )

    output_dir = tmp_path / "end_to_end_pipeline"
    assert calls == [("fmd", 3, 7)]
    assert result["data"] == "end_to_end_pipeline"
    assert result["status"] == "PASS"
    assert {check["name"] for check in result["checks"]} == _CHECK_NAMES
    encoded_check = next(
        check for check in result["checks"] if check["name"] == "encoded_field_contract"
    )
    assert encoded_check["input_image_dtype"] == "torch.float32"
    assert encoded_check["input_field_dtype"] == "torch.complex64"
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "01_end_to_end_operator_family_grid.png").exists()
    assert (output_dir / "01_end_to_end_operator_family_grid.svg").exists()
    assert (output_dir / "02_restoration_recipe_grid.png").exists()
    assert (output_dir / "02_restoration_recipe_grid.svg").exists()

    summary_text = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert "End-To-End Pipeline Validation" in summary_text
    assert "end_to_end_pipeline" in summary_text

    with (output_dir / "metrics.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 27
    assert {
        row["recipe"]
        for row in rows
        if row["figure_group"] == "operator_family"
    } == _OPERATOR_FAMILY_RECIPE_NAMES
    assert {
        row["recipe"]
        for row in rows
        if row["figure_group"] == "restoration_recipe"
    } == _RESTORATION_RECIPE_NAMES
    assert {
        "sample_index",
        "figure_group",
        "recipe",
        "image_shape",
        "field_shape",
        "image_dtype",
        "field_dtype",
        "operations",
        "clean_degraded_max_abs_error",
        "provenance_keys",
    }.issubset(rows[0])
    assert all(row["image_shape"] == "1x128x128" for row in rows)
    assert all(row["field_shape"] == "1x128x128" for row in rows)
    assert all(row["image_dtype"] == "torch.float32" for row in rows)
    assert all(row["field_dtype"] == "torch.complex64" for row in rows)
    assert all("perturbation" in row["provenance_keys"] for row in rows)

    metrics_text = (output_dir / "metrics.csv").read_text(encoding="utf-8")
    for recipe_name in _OPERATOR_FAMILY_RECIPE_NAMES | _RESTORATION_RECIPE_NAMES:
        assert recipe_name in metrics_text
    assert "apply_gaussian_blur" in metrics_text
    assert "apply_psf_kernel" in metrics_text
    assert "build_canny_edge_map" not in metrics_text
    assert "build_sobel_edge_map" not in metrics_text
    assert "build_laplacian_of_gaussian_edge_map" not in metrics_text


def test_end_to_end_pipeline_validation_main_accepts_cli_arguments(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证端到端validator命令行入口接受参数
    """
    from experiments.validation.data import validate_end_to_end_pipeline

    calls: list[tuple[str, int | None, int]] = []

    def _fake_build_raw_dataset(
        dataset_name: str,
        *,
        max_samples: int | None = None,
        random_seed: int = 42,
    ) -> _FakeRawDataset:
        calls.append((dataset_name, max_samples, random_seed))
        return _FakeRawDataset()

    monkeypatch.setattr(
        validate_end_to_end_pipeline,
        "build_raw_dataset",
        _fake_build_raw_dataset,
    )

    result = validate_end_to_end_pipeline.main(
        [
            "--output-root",
            str(tmp_path),
            "--seed",
            "11",
            "--size",
            "tiny",
        ]
    )

    assert calls == [("fmd", 3, 11)]
    assert result["data"] == "end_to_end_pipeline"
    assert (tmp_path / "end_to_end_pipeline" / "summary.md").exists()

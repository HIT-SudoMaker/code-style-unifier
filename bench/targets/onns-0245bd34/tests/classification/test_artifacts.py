from __future__ import annotations

import csv
import json
from pathlib import Path

import torch

from experiments.classification import artifacts
from experiments.classification import train
from experiments.classification.config import TrainingConfig


def test_build_run_paths_uses_canonical_classification_layout(tmp_path: Path) -> None:
    """
    分类产物目录契约
    """
    paths = artifacts.build_run_paths(tmp_path, topology="with_lens", run_name="smoke")

    root = tmp_path / "results" / "classification" / "with_lens" / "smoke"
    assert paths == {
        "root": root,
        "epoch_metrics": root / "epoch_metrics.csv",
        "final_metrics": root / "final_metrics.json",
        "config": root / "config.json",
        "runtime": root / "runtime.json",
        "summary": root / "summary.md",
        "model_checkpoints": root / "model_checkpoints",
        "best_checkpoint": root / "model_checkpoints" / "best.pt",
        "last_checkpoint": root / "model_checkpoints" / "last.pt",
        "figures": root / "diagnostic_figures",
    }


def test_write_json_creates_parent_dirs_and_writes_readable_json(
    tmp_path: Path,
) -> None:
    """
    排序 JSON 写入契约
    """
    path = artifacts._write_json(tmp_path / "nested" / "payload.json", {"b": 2, "a": 1})

    assert path == tmp_path / "nested" / "payload.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1, "b": 2}


def test_append_epoch_metrics_writes_fields_and_row_data(tmp_path: Path) -> None:
    """
    轮次指标 CSV 契约
    """
    row = {
        "epoch": 1,
        "train_loss": 0.5,
        "val_loss": 0.75,
        "train_accuracy": 0.8,
        "val_accuracy": 0.7,
        "seconds": 1.25,
    }

    path = artifacts._append_epoch_metrics(tmp_path / "metrics" / "epoch.csv", row)

    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert rows[0].keys() == set(artifacts.EPOCH_METRIC_FIELDS)
    assert rows == [
        {
            "epoch": "1",
            "train_loss": "0.5",
            "val_loss": "0.75",
            "train_accuracy": "0.8",
            "val_accuracy": "0.7",
            "seconds": "1.25",
        }
    ]


def test_reset_run_artifacts_removes_stale_run_outputs(tmp_path: Path) -> None:
    """
    运行产物清理边界
    """
    paths = artifacts.build_run_paths(tmp_path, topology="with_lens", run_name="smoke")
    stale_paths = [
        paths["epoch_metrics"],
        paths["final_metrics"],
        paths["summary"],
        paths["best_checkpoint"],
        paths["last_checkpoint"],
        paths["figures"] / "01_training_dynamics.png",
        paths["figures"] / "01_training_dynamics.svg",
        paths["figures"] / "training_curves.png",
        paths["figures"] / "training_curves.svg",
        paths["figures"] / "02_confusion_matrix.png",
        paths["figures"] / "02_confusion_matrix.svg",
        paths["figures"] / "03_per_class_accuracy.png",
        paths["figures"] / "03_per_class_accuracy.svg",
        paths["figures"] / "04_optical_readout_examples_upper.png",
        paths["figures"] / "04_optical_readout_examples_upper.svg",
        paths["figures"] / "04_optical_readout_examples_lower.png",
        paths["figures"] / "04_optical_readout_examples_lower.svg",
        paths["figures"] / "04_optical_readout_examples.png",
        paths["figures"] / "04_optical_readout_examples.svg",
        paths["figures"] / "02_evaluation_summary.png",
        paths["figures"] / "02_evaluation_summary.svg",
        paths["figures"] / "03_optical_readout_examples.png",
        paths["figures"] / "03_optical_readout_examples.svg",
        paths["figures"] / "confusion_matrix.png",
        paths["figures"] / "confusion_matrix.svg",
        paths["figures"] / "per_class_accuracy.png",
        paths["figures"] / "per_class_accuracy.svg",
        paths["figures"] / "readout_examples.json",
        paths["figures"] / "readout_examples.pt",
    ]
    retained_path = paths["figures"] / "retained.txt"
    for stale_path in [*stale_paths, retained_path]:
        stale_path.parent.mkdir(parents=True, exist_ok=True)
        stale_path.write_text("stale\n", encoding="utf-8")

    artifacts._reset_run_artifacts(paths)

    for stale_path in stale_paths:
        assert not stale_path.exists()
    assert retained_path.read_text(encoding="utf-8") == "stale\n"


def test_write_runtime_records_selected_device_and_seed(tmp_path: Path) -> None:
    """
    运行元数据契约
    """
    path = artifacts._write_runtime(
        tmp_path / "runtime.json",
        device=torch.device("cpu"),
        seed=123,
    )

    runtime = json.loads(path.read_text(encoding="utf-8"))
    assert runtime["selected_device"] == "cpu"
    assert runtime["seed"] == 123


def test_write_summary_lists_publication_and_diagnostic_artifacts(
    tmp_path: Path,
) -> None:
    """
    运行摘要产物清单
    """
    paths = artifacts.build_run_paths(tmp_path, topology="with_lens", run_name="smoke")
    paths["root"].mkdir(parents=True)

    summary_path = artifacts._write_summary(
        paths["summary"],
        config=TrainingConfig(topology="with_lens", epochs=1),
        final_metrics={
            "best_val_accuracy": 0.9,
            "evaluation_accuracy": 0.8,
            "evaluation_split": "val",
        },
        paths=paths,
    )

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "01_training_dynamics" in summary_text
    assert "02_confusion_matrix" in summary_text
    assert "03_per_class_accuracy" in summary_text
    assert "04_optical_readout_examples_upper" in summary_text
    assert "04_optical_readout_examples_lower" in summary_text
    retired_summary_artifacts = (
        "02_evaluation_summary",
        "03_optical_readout_examples",
        "diagnostic_figures/04_optical_readout_examples.png",
        "diagnostic_figures/04_optical_readout_examples.svg",
        "diagnostic_training_curves",
        "diagnostic_figures/training_curves.png",
        "diagnostic_figures/training_curves.svg",
        "diagnostic_figures/confusion_matrix.png",
        "diagnostic_figures/confusion_matrix.svg",
        "diagnostic_figures/per_class_accuracy.png",
        "diagnostic_figures/per_class_accuracy.svg",
    )
    for retired_artifact in retired_summary_artifacts:
        assert retired_artifact not in summary_text
    assert "legacy_" not in summary_text


def test_train_re_exports_artifact_surface(tmp_path: Path) -> None:
    """
    训练模块产物接口
    """
    assert train.EPOCH_METRIC_FIELDS is artifacts.EPOCH_METRIC_FIELDS
    assert train.build_run_paths(tmp_path, "with_lens")["root"].name == "default"

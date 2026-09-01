from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import torch
from torch import nn

from experiments.classification import replot


def _write_epoch_metrics(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "epoch",
                "train_loss",
                "val_loss",
                "train_accuracy",
                "val_accuracy",
                "seconds",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "epoch": 1,
                "train_loss": 2.0,
                "val_loss": 1.5,
                "train_accuracy": 0.2,
                "val_accuracy": 0.3,
                "seconds": 0.1,
            }
        )
        writer.writerow(
            {
                "epoch": 2,
                "train_loss": 1.0,
                "val_loss": 0.5,
                "train_accuracy": 0.8,
                "val_accuracy": 0.7,
                "seconds": 0.2,
            }
        )


def _write_final_metrics(path: Path, *, best_epoch: object = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "confusion_matrix": [
                    [1 if row_index == column_index else 0 for column_index in range(10)]
                    for row_index in range(10)
                ],
                "per_class_accuracy": [1.0 for _ in range(10)],
                "best_epoch": best_epoch,
                "best_val_accuracy": 0.7,
                "evaluation_accuracy": 0.7,
                "evaluation_split": "val",
                "test_accuracy": None,
                "test_loader_available": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_config(path: Path) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "batch_size": 128,
        "device": "cpu",
        "epochs": 50,
        "focal_length": 0.005,
        "is_scheduler_enabled": False,
        "learning_rate": 0.0037,
        "phase_initialization": "uniform",
        "phase_parameterization": "direct",
        "project_root": str(path.parents[4]),
        "propagation_distance": 0.005,
        "resize_mode": "bilinear",
        "run_name": "default",
        "samples_per_class": None,
        "seed": 42,
        "topology": "without_lens",
        "weight_decay": 0.0,
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return payload


def test_replot_cached_run_redraws_scalar_figures(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    _write_epoch_metrics(run_root / "epoch_metrics.csv")
    _write_final_metrics(run_root / "final_metrics.json")
    _write_config(run_root / "config.json")
    summary_path = run_root / "summary.md"
    summary_path.write_text(
        "- diagnostic_training_curves: diagnostic_figures/training_curves.png\n",
        encoding="utf-8",
    )
    figure_root = run_root / "diagnostic_figures"
    figure_root.mkdir(parents=True)
    (figure_root / "training_curves.png").write_text("stale", encoding="utf-8")
    (figure_root / "training_curves.svg").write_text("stale", encoding="utf-8")

    result = replot.replot_run(
        project_root=tmp_path,
        topology="without_lens",
        run_name="default",
        mode="cached",
    )

    assert result["status"] == "PASS"
    assert (figure_root / "01_training_dynamics.png").exists()
    assert (figure_root / "01_training_dynamics.svg").exists()
    assert not (figure_root / "training_curves.png").exists()
    assert not (figure_root / "training_curves.svg").exists()
    assert (figure_root / "02_confusion_matrix.png").exists()
    assert (figure_root / "02_confusion_matrix.svg").exists()
    assert (figure_root / "03_per_class_accuracy.png").exists()
    assert (figure_root / "03_per_class_accuracy.svg").exists()
    assert not (figure_root / "02_evaluation_summary.png").exists()
    assert not (figure_root / "02_evaluation_summary.svg").exists()
    assert not (figure_root / "confusion_matrix.png").exists()
    assert not (figure_root / "confusion_matrix.svg").exists()
    assert not (figure_root / "per_class_accuracy.png").exists()
    assert not (figure_root / "per_class_accuracy.svg").exists()
    assert "04_optical_readout_examples" not in result["figures"]
    assert "training_curves" not in result["figures"]
    assert not (figure_root / "04_optical_readout_examples_upper.png").exists()
    assert not (figure_root / "04_optical_readout_examples_upper.svg").exists()
    assert not (figure_root / "04_optical_readout_examples_lower.png").exists()
    assert not (figure_root / "04_optical_readout_examples_lower.svg").exists()
    assert not (figure_root / "04_optical_readout_examples.png").exists()
    assert not (figure_root / "04_optical_readout_examples.svg").exists()
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "- 01_training_dynamics: diagnostic_figures/01_training_dynamics.png" in summary_text
    assert "diagnostic_training_curves" not in summary_text
    assert "training_curves.png" not in summary_text


def test_replot_cached_run_normalizes_best_epoch_before_plotting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    _write_epoch_metrics(run_root / "epoch_metrics.csv")
    _write_final_metrics(run_root / "final_metrics.json", best_epoch="2")
    captured: dict[str, object] = {}

    def _capture_training_dynamics(
        history_rows: list[dict[str, object]],
        output_base: Path,
        *,
        best_epoch: object = None,
    ) -> dict[str, str]:
        captured["best_epoch"] = best_epoch
        return {
            "png": str(output_base.with_suffix(".png")),
            "svg": str(output_base.with_suffix(".svg")),
        }

    monkeypatch.setattr(
        replot,
        "visualize_training_dynamics",
        _capture_training_dynamics,
    )

    result = replot.replot_run(
        project_root=tmp_path,
        topology="without_lens",
        run_name="default",
        mode="cached",
    )

    assert result["status"] == "PASS"
    assert captured["best_epoch"] == 2
    assert isinstance(captured["best_epoch"], int)


def test_replot_cached_run_fails_when_epoch_metrics_are_missing(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    _write_final_metrics(run_root / "final_metrics.json")

    with pytest.raises(FileNotFoundError, match="epoch_metrics.csv"):
        replot.replot_run(
            project_root=tmp_path,
            topology="without_lens",
            run_name="default",
            mode="cached",
        )


def test_replot_cached_run_fails_when_final_metrics_are_missing(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    _write_epoch_metrics(run_root / "epoch_metrics.csv")

    with pytest.raises(FileNotFoundError, match="final_metrics.json"):
        replot.replot_run(
            project_root=tmp_path,
            topology="without_lens",
            run_name="default",
            mode="cached",
        )


def test_replot_cli_accepts_mode_and_checkpoint_choices(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    args = replot.parse_args(
        [
            "--project-root",
            str(tmp_path),
            "--topology",
            "with_lens",
            "--run-name",
            "trial",
            "--mode",
            "checkpoint",
            "--checkpoint",
            "last",
        ]
    )

    assert args.project_root == tmp_path
    assert args.topology == ["with_lens"]
    assert args.run_name == "trial"
    assert args.mode == "checkpoint"
    assert args.checkpoint == "last"


class _TinyReadoutModel(nn.Module):
    detector_regions = [(0, 2, 0, 2)] * 10

    def __init__(self, **kwargs: object) -> None:
        """
        初始化重绘模型替身模块
        """
        super().__init__()
        self.weight = nn.Parameter(torch.ones(()))
        self.kwargs = kwargs

    def forward(self, input_field: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        执行测试替身前向传播
        """
        batch_size = input_field.shape[0]
        detector = torch.zeros((batch_size, 10), device=input_field.device)
        detector[:, 0] = self.weight
        intensity = torch.ones((batch_size, 8, 8), device=input_field.device) * self.weight
        return detector, intensity


def _write_config(path: Path) -> dict[str, object]:
    payload: dict[str, object] = {
        "topology": "without_lens",
        "resize_mode": "bilinear",
        "phase_parameterization": "direct",
        "phase_initialization": "uniform",
        "propagation_distance": 0.005,
        "focal_length": 0.2,
        "seed": 42,
        "samples_per_class": None,
        "batch_size": 2,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return payload


def _tiny_dataloaders() -> dict[str, list[dict[str, torch.Tensor]]]:
    return {
        "val": [
            {
                "input_field": torch.ones((2, 8, 8), dtype=torch.complex64),
                "input_image": torch.ones((2, 1, 8, 8)),
                "label": torch.tensor([0, 1]),
                "target_detector_distribution": torch.eye(10)[:2],
            }
        ]
    }


def test_replot_checkpoint_run_exports_readout_cache_and_figure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    config_payload = _write_config(run_root / "config.json")
    model = _TinyReadoutModel(topology="without_lens")
    checkpoint_path = run_root / "model_checkpoints" / "best.pt"
    checkpoint_path.parent.mkdir(parents=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "training_config": {**config_payload, "project_root": tmp_path},
        },
        checkpoint_path,
    )
    monkeypatch.setattr(replot, "ClassificationONN", _TinyReadoutModel)
    monkeypatch.setattr(
        replot,
        "build_classification_dataloaders",
        lambda **kwargs: _tiny_dataloaders(),
    )

    result = replot.replot_run(
        project_root=tmp_path,
        topology="without_lens",
        run_name="default",
        mode="checkpoint",
    )

    figure_root = run_root / "diagnostic_figures"
    assert result["status"] == "PASS"
    assert (figure_root / "04_optical_readout_examples_upper.png").exists()
    assert (figure_root / "04_optical_readout_examples_upper.svg").exists()
    assert (figure_root / "04_optical_readout_examples_lower.png").exists()
    assert (figure_root / "04_optical_readout_examples_lower.svg").exists()
    assert not (figure_root / "04_optical_readout_examples.png").exists()
    assert not (figure_root / "04_optical_readout_examples.svg").exists()
    assert set(result["figures"]["04_optical_readout_examples"]) == {
        "upper_png",
        "upper_svg",
        "lower_png",
        "lower_svg",
    }
    assert (figure_root / "readout_examples.json").exists()
    assert (figure_root / "readout_examples.pt").exists()
    payload = torch.load(figure_root / "readout_examples.pt", map_location="cpu")
    assert payload["source_checkpoint"] == "best"
    assert payload["examples"][0]["intensity_map"].shape == (8, 8)


def test_replot_checkpoint_run_rejects_missing_required_config_field(
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    payload = _write_config(run_root / "config.json")
    payload.pop("focal_length")
    (run_root / "config.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    checkpoint_path = run_root / "model_checkpoints" / "best.pt"
    checkpoint_path.parent.mkdir(parents=True)
    torch.save({"model_state_dict": {}}, checkpoint_path)

    with pytest.raises(ValueError, match="focal_length"):
        replot.replot_run(
            project_root=tmp_path,
            topology="without_lens",
            mode="checkpoint",
        )


def test_replot_checkpoint_run_reports_config_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    config_payload = _write_config(run_root / "config.json")
    checkpoint_path = run_root / "model_checkpoints" / "best.pt"
    checkpoint_path.parent.mkdir(parents=True)
    torch.save(
        {
            "model_state_dict": _TinyReadoutModel().state_dict(),
            "training_config": {**config_payload, "topology": "with_lens"},
        },
        checkpoint_path,
    )
    monkeypatch.setattr(replot, "ClassificationONN", _TinyReadoutModel)
    monkeypatch.setattr(
        replot,
        "build_classification_dataloaders",
        lambda **kwargs: _tiny_dataloaders(),
    )

    result = replot.replot_run(
        project_root=tmp_path,
        topology="without_lens",
        mode="checkpoint",
    )

    assert result["status"] == "PASS_WITH_WARNINGS"
    assert "topology" in result["config_mismatches"]


def test_replot_checkpoint_run_rejects_malformed_checkpoint(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    _write_config(run_root / "config.json")
    checkpoint_path = run_root / "model_checkpoints" / "best.pt"
    checkpoint_path.parent.mkdir(parents=True)
    torch.save({"training_config": {}}, checkpoint_path)

    with pytest.raises(ValueError, match="model_state_dict"):
        replot.replot_run(
            project_root=tmp_path,
            topology="without_lens",
            mode="checkpoint",
        )


def test_replot_auto_skips_missing_checkpoint_but_keeps_scalar_figures(
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    _write_epoch_metrics(run_root / "epoch_metrics.csv")
    _write_final_metrics(run_root / "final_metrics.json")

    result = replot.replot_run(
        project_root=tmp_path,
        topology="without_lens",
        mode="auto",
    )

    assert result["status"] == "PASS"
    assert "01_training_dynamics" in result["figures"]
    assert "04_optical_readout_examples" not in result["figures"]
    assert any("best.pt" in item for item in result["skipped"])


def test_replot_auto_skips_malformed_checkpoint_but_keeps_scalar_figures(
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    _write_epoch_metrics(run_root / "epoch_metrics.csv")
    _write_final_metrics(run_root / "final_metrics.json")
    _write_config(run_root / "config.json")
    checkpoint_path = run_root / "model_checkpoints" / "best.pt"
    checkpoint_path.parent.mkdir(parents=True)
    torch.save({"training_config": {}}, checkpoint_path)

    result = replot.replot_run(
        project_root=tmp_path,
        topology="without_lens",
        mode="auto",
    )

    assert result["status"] == "PASS"
    assert "01_training_dynamics" in result["figures"]
    assert "04_optical_readout_examples" not in result["figures"]
    assert any("model_state_dict" in item for item in result["skipped"])


def test_replot_auto_skips_malformed_cached_artifacts_but_keeps_readout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    run_root = tmp_path / "results" / "classification" / "without_lens" / "default"
    _write_epoch_metrics(run_root / "epoch_metrics.csv")
    malformed_final_metrics = {"per_class_accuracy": [1.0 for _ in range(10)]}
    (run_root / "final_metrics.json").write_text(
        json.dumps(malformed_final_metrics) + "\n",
        encoding="utf-8",
    )
    config_payload = _write_config(run_root / "config.json")
    model = _TinyReadoutModel(topology="without_lens")
    checkpoint_path = run_root / "model_checkpoints" / "best.pt"
    checkpoint_path.parent.mkdir(parents=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "training_config": config_payload,
        },
        checkpoint_path,
    )
    monkeypatch.setattr(replot, "ClassificationONN", _TinyReadoutModel)
    monkeypatch.setattr(
        replot,
        "build_classification_dataloaders",
        lambda **kwargs: _tiny_dataloaders(),
    )

    result = replot.replot_run(
        project_root=tmp_path,
        topology="without_lens",
        mode="auto",
    )

    assert result["status"] == "PASS"
    assert "01_training_dynamics" not in result["figures"]
    assert "04_optical_readout_examples" in result["figures"]
    assert any("confusion_matrix" in item for item in result["skipped"])


def test_replot_auto_raises_when_no_requested_figures_can_be_redrawn(
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    with pytest.raises(FileNotFoundError, match="no classification artifacts"):
        replot.replot_run(
            project_root=tmp_path,
            topology="without_lens",
            mode="auto",
        )


def test_replot_main_runs_requested_topology_and_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    calls: list[dict[str, object]] = []

    def _fake_replot_run(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {"status": "PASS", "figures": {}, "skipped": []}

    monkeypatch.setattr(replot, "replot_run", _fake_replot_run)
    monkeypatch.setattr(
        replot.report,
        "run",
        lambda project_root: tmp_path / "summary_figures" / "05_topology_comparison.png",
    )

    result = replot.main(
        [
            "--project-root",
            str(tmp_path),
            "--topology",
            "with_lens",
            "--mode",
            "cached",
        ]
    )

    assert list(result["runs"]) == ["with_lens"]
    assert calls == [
        {
            "project_root": tmp_path,
            "topology": "with_lens",
            "run_name": "default",
            "mode": "cached",
            "checkpoint": "best",
            "device": "cpu",
        }
    ]
    assert (
        result["summary_path"]
        == tmp_path / "summary_figures" / "05_topology_comparison.png"
    )

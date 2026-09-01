from __future__ import annotations

import json
from pathlib import Path
import pytest


def _write_topology_run(
    root: Path,
    topology: str,
    *,
    accuracy: float,
    is_epoch_metrics_written: bool = True,
) -> Path:
    run_dir = root / "results" / "classification" / topology / "default"
    run_dir.mkdir(parents=True)
    (run_dir / "final_metrics.json").write_text(
        json.dumps(
            {
                "evaluation_accuracy": accuracy,
                "best_val_accuracy": accuracy - 0.01,
                "evaluation_split": "test",
                "test_accuracy": accuracy,
                "test_loader_available": True,
            }
        ),
        encoding="utf-8",
    )
    if is_epoch_metrics_written:
        (run_dir / "epoch_metrics.csv").write_text(
            "epoch,train_loss,val_loss,train_accuracy,val_accuracy,seconds\n"
            "1,1.0,1.1,0.4,0.5,0.25\n"
            "2,0.8,0.9,0.6,0.7,0.35\n",
            encoding="utf-8",
        )
    figure_dir = run_dir / "diagnostic_figures"
    figure_dir.mkdir(parents=True)
    (figure_dir / "01_training_dynamics.png").write_text("new", encoding="utf-8")
    (figure_dir / "training_curves.png").write_text("legacy", encoding="utf-8")
    return run_dir


def test_report_aggregates_training_optuna_and_reference(tmp_path: Path) -> None:
    """
    分类报告应汇总两种拓扑、Optuna 和参考对比摘要
    """
    for topology, accuracy in [("without_lens", 0.81), ("with_lens", 0.84)]:
        _write_topology_run(tmp_path, topology, accuracy=accuracy)

    optuna_dir = tmp_path / "results" / "classification" / "optuna"
    optuna_dir.mkdir(parents=True)
    (optuna_dir / "summary.md").write_text("# Optuna\n\nStatus: SKIPPED\n", encoding="utf-8")
    reference_dir = tmp_path / "results" / "classification" / "reference_comparison"
    reference_dir.mkdir(parents=True)
    (reference_dir / "summary.md").write_text(
        "# Reference\n\nStatus: PASS\n\nFairness notes\n",
        encoding="utf-8",
    )

    from experiments.classification import report

    output = report.run(project_root=tmp_path)

    content = output.read_text(encoding="utf-8")
    assert output == tmp_path / "results" / "classification" / "summary.md"
    assert "without_lens" in content
    assert "with_lens" in content
    assert "Optuna" in content
    assert "Reference" in content
    assert "summary_figures/05_topology_comparison.png" in content
    assert "summary_figures/04_topology_comparison.png" not in content
    assert "without_lens/default/diagnostic_figures/01_training_dynamics.png" in content
    assert "with_lens/default/diagnostic_figures/01_training_dynamics.png" in content
    assert "training_curves.png" not in content
    assert "optuna/optimization_history.png" not in content
    figure_dir = tmp_path / "results" / "classification" / "summary_figures"
    assert (figure_dir / "05_topology_comparison.png").exists()
    assert (figure_dir / "05_topology_comparison.svg").exists()


def test_report_topology_comparison_marks_missing_data_as_unavailable(
    tmp_path: Path,
) -> None:
    """
    缺失拓扑或历史指标时报告使用 n/a
    """
    _write_topology_run(
        tmp_path,
        "without_lens",
        accuracy=0.75,
        is_epoch_metrics_written=False,
    )

    from experiments.classification import report

    output = report.run(project_root=tmp_path)

    content = output.read_text(encoding="utf-8")
    assert "without_lens" in content
    assert "with_lens" in content
    assert (
        "- without_lens: evaluation_accuracy=0.7500; "
        "best_val_accuracy=0.7400; mean_epoch_seconds=n/a"
    ) in content
    assert (
        "- with_lens: evaluation_accuracy=n/a; "
        "best_val_accuracy=n/a; mean_epoch_seconds=n/a"
    ) in content
    assert "summary_figures/04_topology_comparison.png" not in content
    figure_dir = tmp_path / "results" / "classification" / "summary_figures"
    assert (figure_dir / "05_topology_comparison.png").exists()
    assert (figure_dir / "05_topology_comparison.svg").exists()


def test_report_raises_for_malformed_final_metrics_json(tmp_path: Path) -> None:
    """
    损坏指标清晰失败
    """
    from experiments.classification import report

    output = report.run(project_root=tmp_path)
    content = output.read_text(encoding="utf-8")
    assert "| without_lens | n/a | n/a | n/a | missing |" in content

    run_dir = tmp_path / "results" / "classification" / "without_lens" / "default"
    run_dir.mkdir(parents=True)
    (run_dir / "final_metrics.json").write_text("{bad json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        report.run(project_root=tmp_path)

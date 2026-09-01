from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import csv
import json
from pathlib import Path

from experiments.classification.visualize import visualize_topology_comparison


def _classification_root(project_root: str | Path) -> Path:
    return Path(project_root) / "results" / "classification"


def _read_json(path: Path) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(payload, Mapping):
        message = f"Expected JSON object in {path}"
        raise ValueError(message)
    return payload


def _mean_epoch_seconds(epoch_metrics_path: Path) -> float | None:
    if not epoch_metrics_path.exists():
        return None
    try:
        with epoch_metrics_path.open(encoding="utf-8", newline="") as handle:
            rows = csv.DictReader(handle)
            seconds = []
            for row in rows:
                value = row.get("seconds")
                if value in (None, ""):
                    continue
                try:
                    seconds.append(float(value))
                except ValueError:
                    continue
    except (OSError, csv.Error):
        return None
    if not seconds:
        return None
    return sum(seconds) / len(seconds)


def _format_metric(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int | float):
        return f"{float(value):.4f}"
    return str(value)


def _training_row(root: Path, topology: str) -> tuple[str, Mapping[str, object]]:
    metrics_path = root / topology / "default" / "final_metrics.json"
    if not metrics_path.exists():
        return f"| {topology} | n/a | n/a | n/a | missing |", {}
    metrics = _read_json(metrics_path)
    return (
        "| {topology} | {evaluation} | {split} | {test} | {best} |".format(
            topology=topology,
            evaluation=_format_metric(metrics.get("evaluation_accuracy")),
            split=metrics.get("evaluation_split", "n/a"),
            test=_format_metric(metrics.get("test_accuracy")),
            best=_format_metric(metrics.get("best_val_accuracy")),
        ),
        metrics,
    )


def _topology_summary(topology: str, run_root: Path) -> dict[str, object]:
    metrics = _read_json(run_root / "final_metrics.json")
    if not metrics:
        return {
            "topology": topology,
            "evaluation_accuracy": None,
            "best_val_accuracy": None,
            "evaluation_split": "n/a",
            "test_accuracy": None,
            "test_loader_available": False,
            "mean_epoch_seconds": None,
            "is_available": False,
        }
    return {
        "topology": topology,
        "evaluation_accuracy": metrics.get("evaluation_accuracy"),
        "best_val_accuracy": metrics.get("best_val_accuracy"),
        "evaluation_split": metrics.get("evaluation_split", "n/a"),
        "test_accuracy": metrics.get("test_accuracy"),
        "test_loader_available": bool(metrics.get("test_loader_available", False)),
        "mean_epoch_seconds": _mean_epoch_seconds(run_root / "epoch_metrics.csv"),
        "is_available": True,
    }


def _topology_input_line(row: Mapping[str, object]) -> str:
    test_loader = row["test_loader_available"] if row.get("is_available") else "n/a"
    return (
        "- {topology}: evaluation_accuracy={evaluation}; "
        "best_val_accuracy={best}; mean_epoch_seconds={seconds}; "
        "evaluation_split={split}; test_accuracy={test}; "
        "test_loader_available={test_loader}"
    ).format(
        topology=row["topology"],
        evaluation=_format_metric(row["evaluation_accuracy"]),
        best=_format_metric(row["best_val_accuracy"]),
        seconds=_format_metric(row["mean_epoch_seconds"]),
        split=row.get("evaluation_split", "n/a"),
        test=_format_metric(row["test_accuracy"]),
        test_loader=test_loader,
    )


def _optuna_lines(root: Path) -> list[str]:
    trials_path = root / "optuna" / "optuna_trials.csv"
    if not trials_path.exists():
        return ["- Optuna: skipped or not run."]
    with trials_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return ["- Optuna: no completed trials."]
    best_row = max(rows, key=lambda row: float(row.get("value") or 0.0))
    return [
        f"- trials: {len(rows)}",
        f"- best_value: {best_row.get('value', 'n/a')}",
        f"- best_params: `{best_row.get('params', '{}')}`",
    ]


def _figure_lines(root: Path) -> list[str]:
    figure_paths = [
        root / "summary_figures" / "05_topology_comparison.png",
        root
        / "without_lens"
        / "default"
        / "diagnostic_figures"
        / "01_training_dynamics.png",
        root
        / "with_lens"
        / "default"
        / "diagnostic_figures"
        / "01_training_dynamics.png",
        root / "optuna" / "optimization_history.png",
    ]
    return [
        f"- {figure_path.relative_to(root).as_posix()}"
        for figure_path in figure_paths
        if figure_path.exists()
    ]


def run(project_root: str | Path = Path.cwd()) -> Path:
    """
    汇总分类对标训练结果
    """
    root = _classification_root(project_root)
    root.mkdir(parents=True, exist_ok=True)
    output_path = root / "summary.md"
    without_row, _ = _training_row(root, "without_lens")
    with_row, _ = _training_row(root, "with_lens")
    topology_rows = [
        _topology_summary("without_lens", root / "without_lens" / "default"),
        _topology_summary("with_lens", root / "with_lens" / "default"),
    ]
    figure_dir = root / "summary_figures"
    visualize_topology_comparison(topology_rows, figure_dir / "05_topology_comparison")
    lines = [
        "# Classification Summary",
        "",
        "## Baselines",
        "",
        "| topology | evaluation_accuracy | split | test_accuracy | best_val_accuracy |",
        "| --- | --- | --- | --- | --- |",
        without_row,
        with_row,
        "",
        "## Optuna",
        "",
        *_optuna_lines(root),
        "",
        "## Reference Note",
        (
            "The reference with_lens notebook uses a ReLU-like nonlinear absorber. "
            "Current baselines keep the repository's linear optical layers, so "
            "remaining differences should be interpreted through this modeling gap."
        ),
        "",
        "## Topology Figure Inputs",
        *[_topology_input_line(row) for row in topology_rows],
        "",
        "## Figures",
        *_figure_lines(root),
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    解析报告命令行参数
    """
    parser = argparse.ArgumentParser(description="Build classification summary report.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> Path:
    """
    命令行入口
    """
    args = parse_args(argv)
    return run(project_root=args.project_root)


if __name__ == "__main__":
    main()

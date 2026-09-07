from __future__ import annotations

from collections.abc import Mapping
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import TYPE_CHECKING

import numpy as np
import torch

from experiments.classification.config import _validate_run_name
from experiments.classification.model import normalize_topology

if TYPE_CHECKING:
    from experiments.classification.config import TrainingConfig


EPOCH_METRIC_FIELDS = (
    "epoch",
    "train_loss",
    "val_loss",
    "train_accuracy",
    "val_accuracy",
    "seconds",
)


def build_run_paths(
    project_root: str | Path,
    topology: str,
    run_name: str = "default",
    mode: str | None = None,
) -> dict[str, Path]:
    """
    分类训练产物路径
    """
    del mode
    safe_run_name = _validate_run_name(run_name)
    root = (
        Path(project_root)
        / "results"
        / "classification"
        / normalize_topology(topology)
        / safe_run_name
    )
    return {
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


def _write_json(path: str | Path, payload: object) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    return output_path


def _write_runtime(path: str | Path, *, device: torch.device, seed: int) -> Path:
    metadata: dict[str, object] = {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "selected_device": str(device),
        "seed": seed,
        "time": datetime.now(timezone.utc).isoformat(),
    }
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    else:
        commit = completed.stdout.strip()
        if commit:
            metadata["git_commit"] = commit
    return _write_json(path, metadata)


def _append_epoch_metrics(path: str | Path, row: Mapping[str, object]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    should_write_header = not output_path.exists() or output_path.stat().st_size == 0
    with output_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(EPOCH_METRIC_FIELDS))
        if should_write_header:
            writer.writeheader()
        writer.writerow({field: row[field] for field in EPOCH_METRIC_FIELDS})
    return output_path


def _reset_run_artifacts(paths: Mapping[str, Path]) -> None:
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
    for stale_path in stale_paths:
        if stale_path.exists():
            stale_path.unlink()


def _write_summary(
    path: str | Path,
    *,
    config: "TrainingConfig",
    final_metrics: Mapping[str, object],
    paths: Mapping[str, Path],
) -> Path:
    lines = [
        f"# Classification: {config.topology}",
        "",
        "Status: PASS",
        "",
        "## Settings",
        f"- epochs: {config.epochs}",
        f"- batch_size: {config.batch_size}",
        f"- learning_rate: {config.learning_rate}",
        f"- resize_mode: {config.resize_mode}",
        f"- phase: {config.phase_parameterization}/{config.phase_initialization}",
        "",
        "## Results",
        f"- best_val_accuracy: {float(final_metrics['best_val_accuracy']):.6f}",
        f"- evaluation_accuracy: {float(final_metrics['evaluation_accuracy']):.6f}",
        f"- evaluation_split: {final_metrics['evaluation_split']}",
        "",
        "## Notes",
        "- with_lens omits the comparison notebook's non-physical ReLU absorber.",
        "",
        "## Artifacts",
        f"- epoch_metrics: {paths['epoch_metrics']}",
        f"- final_metrics: {paths['final_metrics']}",
        "- 01_training_dynamics: diagnostic_figures/01_training_dynamics.png",
        "- 02_confusion_matrix: diagnostic_figures/02_confusion_matrix.png",
        "- 03_per_class_accuracy: diagnostic_figures/03_per_class_accuracy.png",
        "- 04_optical_readout_examples_upper: "
        "diagnostic_figures/04_optical_readout_examples_upper.png",
        "- 04_optical_readout_examples_lower: "
        "diagnostic_figures/04_optical_readout_examples_lower.png",
        "- readout_examples: diagnostic_figures/readout_examples.json",
        "- best_checkpoint: model_checkpoints/best.pt",
    ]
    output_path = Path(path)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return output_path

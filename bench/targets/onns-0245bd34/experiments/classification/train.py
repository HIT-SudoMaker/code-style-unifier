from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from experiments.classification.artifacts import (
    _append_epoch_metrics,
    _reset_run_artifacts,
    _write_json,
    _write_runtime,
    _write_summary,
    build_run_paths,
    EPOCH_METRIC_FIELDS,
)
from experiments.classification.config import (
    BasicConfig,
    build_default_training_config,
    ModelConfig,
    resolve_default_epochs,
    SearchConfig,
    TrainingConfig,
)
from experiments.classification.dataset_adapter import build_classification_dataloaders
from experiments.classification.engine import (
    _evaluate_loss_accuracy,
    _extract_batch,
    _run_epoch,
    build_target_distribution,
)
from experiments.classification.experiment import (
    _resolve_device,
    _set_random_seed,
    _validate_dataloaders,
    run_experiment,
)
from experiments.classification.model import (
    ClassificationONN,
    normalize_topology,
)
from experiments.classification.readout import (
    _collect_readout_examples,
    _write_readout_examples,
)
from experiments.classification.visualize import (
    visualize_confusion_matrix,
    visualize_optical_readout_examples,
    visualize_per_class_accuracy,
    visualize_training_curves,
    visualize_training_dynamics,
)


_ERROR_EPOCHS_POSITIVE = "epochs must be positive"


def run_training(
    config: TrainingConfig,
    project_root: str | Path | None = None,
) -> dict[str, object]:
    """
    分类训练入口
    """
    return run_experiment(config, project_root=project_root)


def _parse_positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError(_ERROR_EPOCHS_POSITIVE)
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> TrainingConfig:
    """
    训练命令参数契约
    """
    parser = argparse.ArgumentParser(description="Train classification ONN baseline.")
    parser.add_argument("--topology", choices=("without_lens", "with_lens"))
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.0037)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--epochs", type=_parse_positive_int, default=50)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-name", default="default")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--resize-mode", choices=("nearest", "bilinear"), default="bilinear")
    parser.add_argument("--samples-per-class", type=int, default=None)
    args = parser.parse_args(argv)
    config = TrainingConfig(
        topology=normalize_topology(args.topology or "without_lens"),
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        epochs=args.epochs,
        device=args.device,
        seed=args.seed,
        run_name=args.run_name,
        project_root=args.project_root,
        resize_mode=args.resize_mode,
        samples_per_class=args.samples_per_class,
    )
    config.validate()
    return config


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    训练命令入口
    """
    return run_training(parse_args(argv))


if __name__ == "__main__":
    main()

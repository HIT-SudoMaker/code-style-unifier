from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import random
import time

import numpy as np
from torch import nn
import torch
from torch.optim import Adam

from experiments.classification.artifacts import (
    _append_epoch_metrics,
    _reset_run_artifacts,
    _write_json,
    _write_runtime,
    _write_summary,
    build_run_paths,
)
from experiments.classification.config import TrainingConfig
from experiments.classification.dataset_adapter import build_classification_dataloaders
from experiments.classification.engine import _evaluate_loss_accuracy, _run_epoch
from experiments.classification.eval import evaluate_model
from experiments.classification.model import ClassificationONN
from experiments.classification.readout import (
    _collect_readout_examples,
    _write_readout_examples,
)
from experiments.classification.visualize import (
    visualize_confusion_matrix,
    visualize_optical_readout_examples,
    visualize_per_class_accuracy,
    visualize_training_dynamics,
)


def _checkpoint_training_config(config: Mapping[str, object]) -> dict[str, object]:
    payload = dict(config)
    if "project_root" in payload:
        payload["project_root"] = str(payload["project_root"])
    return payload


def _set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(requested)


def _validate_dataloaders(dataloaders: object) -> Mapping[str, object]:
    if not isinstance(dataloaders, Mapping):
        message = "build_classification_dataloaders() must return a mapping"
        raise TypeError(message)
    missing = [split for split in ("train", "val") if split not in dataloaders]
    if missing:
        message = f"missing dataloader splits: {', '.join(missing)}"
        raise ValueError(message)
    return dataloaders


def run_experiment(
    config: TrainingConfig,
    project_root: str | Path | None = None,
) -> dict[str, object]:
    """
    分类实验编排入口
    """
    config.validate()
    normalized = config.normalized()
    if project_root is not None:
        normalized = TrainingConfig(
            **{
                **normalized.to_flat_dict(),
                "project_root": Path(project_root),
            }
        )
        normalized = normalized.normalized()
    _set_random_seed(normalized.seed)
    paths = build_run_paths(
        normalized.project_root,
        topology=normalized.topology,
        run_name=normalized.run_name,
    )
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["model_checkpoints"].mkdir(parents=True, exist_ok=True)
    paths["figures"].mkdir(parents=True, exist_ok=True)
    _reset_run_artifacts(paths)
    flat_config = normalized.to_flat_dict()
    checkpoint_config = _checkpoint_training_config(flat_config)
    _write_json(paths["config"], checkpoint_config)

    device = _resolve_device(normalized.device)
    _write_runtime(paths["runtime"], device=device, seed=normalized.seed)
    try:
        dataloaders = build_classification_dataloaders(
            batch_size=normalized.batch_size,
            topology=normalized.topology,
            resize_mode=normalized.resize_mode,
            samples_per_class=normalized.samples_per_class,
            random_seed=normalized.seed,
        )
    except TypeError:
        dataloaders = build_classification_dataloaders(batch_size=normalized.batch_size)
    dataloaders = _validate_dataloaders(dataloaders)
    try:
        model = ClassificationONN(
            topology=normalized.topology,
            phase_parameterization=normalized.phase_parameterization,
            phase_initialization=normalized.phase_initialization,
            propagation_distance=normalized.propagation_distance,
            focal_length=normalized.focal_length,
        ).to(device)
    except TypeError:
        model = ClassificationONN(topology=normalized.topology).to(device)
    criterion = nn.MSELoss(reduction="sum")
    optimizer = Adam(
        model.parameters(),
        lr=normalized.learning_rate,
        weight_decay=normalized.weight_decay,
    )
    history_rows: list[dict[str, object]] = []
    best_val_accuracy = float("-inf")
    best_epoch = 0

    for epoch in range(1, normalized.epochs + 1):
        started = time.perf_counter()
        train_loss, train_accuracy = _run_epoch(
            model=model,
            dataloader=dataloaders["train"],
            criterion=criterion,
            optimizer=optimizer,
            device=device,
        )
        val_loss, val_accuracy = _evaluate_loss_accuracy(
            model=model,
            dataloader=dataloaders["val"],
            criterion=criterion,
            device=device,
            split="val",
        )
        row = {
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "train_accuracy": train_accuracy,
            "val_accuracy": val_accuracy,
            "seconds": time.perf_counter() - started,
        }
        history_rows.append(row)
        _append_epoch_metrics(paths["epoch_metrics"], row)
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "val_accuracy": val_accuracy,
            "training_config": checkpoint_config,
        }
        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            best_epoch = epoch
            torch.save(checkpoint, paths["best_checkpoint"])

    torch.save(
        {
            "epoch": normalized.epochs,
            "model_state_dict": model.state_dict(),
            "val_accuracy": history_rows[-1]["val_accuracy"],
            "training_config": checkpoint_config,
        },
        paths["last_checkpoint"],
    )
    evaluation_split = "test" if "test" in dataloaders else "val"
    evaluation_loss, evaluation_accuracy = _evaluate_loss_accuracy(
        model=model,
        dataloader=dataloaders[evaluation_split],
        criterion=criterion,
        device=device,
        split=evaluation_split,
    )
    diagnostic_metrics = evaluate_model(
        model=model,
        dataloader=dataloaders[evaluation_split],
        device=device,
    )
    final_metrics = {
        **diagnostic_metrics,
        "best_val_accuracy": best_val_accuracy,
        "best_epoch": best_epoch,
        "evaluation_loss": evaluation_loss,
        "evaluation_accuracy": evaluation_accuracy,
        "evaluation_split": evaluation_split,
        "test_accuracy": evaluation_accuracy if evaluation_split == "test" else None,
        "test_loader_available": evaluation_split == "test",
    }
    if evaluation_split == "val":
        final_metrics["validation_accuracy_substitute"] = evaluation_accuracy
    _write_json(paths["final_metrics"], final_metrics)
    visualize_training_dynamics(
        history_rows,
        paths["figures"] / "01_training_dynamics",
        best_epoch=best_epoch,
    )
    visualize_confusion_matrix(
        final_metrics["confusion_matrix"],
        paths["figures"] / "02_confusion_matrix",
    )
    visualize_per_class_accuracy(
        final_metrics["per_class_accuracy"],
        paths["figures"] / "03_per_class_accuracy",
    )
    readout_examples = _collect_readout_examples(
        model=model,
        dataloader=dataloaders[evaluation_split],
        device=device,
    )
    _write_readout_examples(paths["figures"] / "readout_examples.json", readout_examples)
    visualize_optical_readout_examples(
        readout_examples,
        paths["figures"] / "04_optical_readout_examples",
    )
    _write_summary(
        paths["summary"],
        config=normalized,
        final_metrics=final_metrics,
        paths=paths,
    )
    return {
        "history": history_rows,
        "final_metrics": final_metrics,
        "paths": paths,
        "best_checkpoint": paths["best_checkpoint"],
        "last_checkpoint": paths["last_checkpoint"],
        "summary_path": paths["summary"],
    }

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
import csv
import hashlib
import json
import pathlib
from pathlib import Path

import torch

from experiments.classification import report
from experiments.classification.artifacts import _write_summary, build_run_paths
from experiments.classification.config import TrainingConfig
from experiments.classification.dataset_adapter import build_classification_dataloaders
from experiments.classification.model import ClassificationONN, normalize_topology
from experiments.classification.readout import (
    _collect_readout_examples,
    _write_readout_examples,
    _write_readout_render_cache,
)
from experiments.classification.visualize import (
    visualize_confusion_matrix,
    visualize_optical_readout_examples,
    visualize_per_class_accuracy,
    visualize_training_dynamics,
)

REDRAW_MODES = ("auto", "cached", "checkpoint")
CHECKPOINT_CHOICES = ("best", "last")
CHECKPOINT_SAFE_GLOBALS = tuple(
    value
    for value in (
        getattr(pathlib, "PosixPath", None),
        getattr(pathlib, "WindowsPath", None),
    )
    if value is not None
)
REQUIRED_REDRAW_CONFIG_FIELDS = (
    "topology",
    "resize_mode",
    "phase_parameterization",
    "phase_initialization",
    "propagation_distance",
    "focal_length",
    "seed",
    "samples_per_class",
)


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        message = f"expected JSON object in {path}"
        raise ValueError(message)
    return payload


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _training_config_from_payload(payload: Mapping[str, object]) -> TrainingConfig:
    scheduler_flag = payload.get("is_scheduler_enabled", False)
    if not isinstance(scheduler_flag, bool):
        message = "is_scheduler_enabled must be a boolean"
        raise ValueError(message)
    return TrainingConfig(
        project_root=payload.get("project_root", Path.cwd()),
        run_name=str(payload.get("run_name", "default")),
        device=str(payload.get("device", "cpu")),
        seed=int(payload.get("seed", 42)),
        topology=str(payload.get("topology", "without_lens")),
        batch_size=int(payload.get("batch_size", 128)),
        learning_rate=float(payload.get("learning_rate", 0.0037)),
        weight_decay=float(payload.get("weight_decay", 0.0)),
        epochs=int(payload.get("epochs", 50)),
        samples_per_class=_optional_int(payload.get("samples_per_class")),
        is_scheduler_enabled=scheduler_flag,
        resize_mode=str(payload.get("resize_mode", "bilinear")),
        phase_parameterization=str(payload.get("phase_parameterization", "direct")),
        phase_initialization=str(payload.get("phase_initialization", "uniform")),
        propagation_distance=float(payload.get("propagation_distance", 0.005)),
        focal_length=float(payload.get("focal_length", 0.005)),
    ).normalized()


def _read_epoch_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _config_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_redraw_config(config: Mapping[str, object], path: Path) -> None:
    missing = [field for field in REQUIRED_REDRAW_CONFIG_FIELDS if field not in config]
    if missing:
        missing_fields = ", ".join(missing)
        message = f"{path} missing required redraw fields: {missing_fields}"
        raise ValueError(message)


def _checkpoint_path(paths: Mapping[str, Path], checkpoint: str) -> Path:
    if checkpoint == "best":
        return paths["best_checkpoint"]
    if checkpoint == "last":
        return paths["last_checkpoint"]
    message = f"checkpoint must be one of: {', '.join(CHECKPOINT_CHOICES)}"
    raise ValueError(message)


def _config_mismatches(
    config: Mapping[str, object],
    checkpoint_payload: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    training_config = checkpoint_payload.get("training_config", {})
    if not isinstance(training_config, Mapping):
        return {}
    mismatches: dict[str, dict[str, object]] = {}
    for key, config_value in config.items():
        if key not in training_config:
            continue
        checkpoint_value = training_config[key]
        if checkpoint_value != config_value:
            mismatches[str(key)] = {
                "config_json": config_value,
                "checkpoint_training_config": checkpoint_value,
            }
    return mismatches


def _resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(requested)


def _sequence_metric(
    final_metrics: Mapping[str, object],
    key: str,
) -> Sequence[object]:
    value = final_metrics.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str):
        message = f"final_metrics.json must contain sequence field {key!r}"
        raise ValueError(message)
    return value


def _replot_cached_figures(paths: Mapping[str, Path]) -> dict[str, dict[str, str]]:
    history_rows = _read_epoch_rows(paths["epoch_metrics"])
    final_metrics = _read_json_object(paths["final_metrics"])
    best_epoch = final_metrics.get("best_epoch")
    best_epoch_value = None if best_epoch is None else int(best_epoch)
    confusion_matrix = _sequence_metric(final_metrics, "confusion_matrix")
    per_class_accuracy = _sequence_metric(final_metrics, "per_class_accuracy")

    figure_root = paths["figures"]
    for suffix in ("png", "svg"):
        stale_training_curves = figure_root / f"training_curves.{suffix}"
        if stale_training_curves.exists():
            stale_training_curves.unlink()
    figures = {
        "01_training_dynamics": visualize_training_dynamics(
            history_rows,
            figure_root / "01_training_dynamics",
            best_epoch=best_epoch_value,
        ),
        "02_confusion_matrix": visualize_confusion_matrix(
            confusion_matrix,  # type: ignore[arg-type]
            figure_root / "02_confusion_matrix",
        ),
        "03_per_class_accuracy": visualize_per_class_accuracy(
            per_class_accuracy,  # type: ignore[arg-type]
            figure_root / "03_per_class_accuracy",
        ),
    }
    if paths["config"].exists():
        config = _training_config_from_payload(_read_json_object(paths["config"]))
        _write_summary(paths["summary"], config=config, final_metrics=final_metrics, paths=paths)
    return figures


def _load_checkpoint_payload(path: Path) -> Mapping[str, object]:
    if not path.exists():
        raise FileNotFoundError(path)
    with torch.serialization.safe_globals(CHECKPOINT_SAFE_GLOBALS):
        payload = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(payload, Mapping):
        message = "checkpoint payload must be a mapping"
        raise ValueError(message)
    if "model_state_dict" not in payload:
        message = "checkpoint is missing required model_state_dict"
        raise ValueError(message)
    return payload


def _build_model_from_config(config: Mapping[str, object]) -> torch.nn.Module:
    return ClassificationONN(
        topology=str(config["topology"]),
        phase_parameterization=str(config["phase_parameterization"]),
        phase_initialization=str(config["phase_initialization"]),
        propagation_distance=float(config["propagation_distance"]),
        focal_length=float(config["focal_length"]),
    )


def _build_dataloaders_from_config(
    config: Mapping[str, object],
) -> Mapping[str, Iterable[Mapping[str, object]]]:
    return build_classification_dataloaders(
        batch_size=int(config.get("batch_size", 128)),
        topology=str(config["topology"]),
        resize_mode=str(config["resize_mode"]),
        samples_per_class=config["samples_per_class"],  # type: ignore[arg-type]
        random_seed=int(config["seed"]),
    )


def _replot_checkpoint_figures(
    paths: Mapping[str, Path],
    *,
    checkpoint: str,
    device: str,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, object]]]:
    selected_checkpoint_path = _checkpoint_path(paths, checkpoint)
    checkpoint_payload = _load_checkpoint_payload(selected_checkpoint_path)

    config = _read_json_object(paths["config"])
    _validate_redraw_config(config, paths["config"])
    mismatches = _config_mismatches(config, checkpoint_payload)

    torch_device = _resolve_device(device)
    model = _build_model_from_config(config)
    model.load_state_dict(checkpoint_payload["model_state_dict"], strict=True)
    model.to(torch_device)

    dataloaders = _build_dataloaders_from_config(config)
    evaluation_split = "test" if "test" in dataloaders else "val"
    if evaluation_split not in dataloaders:
        message = "classification dataloaders must include val or test split"
        raise ValueError(message)

    readout_examples = _collect_readout_examples(
        model=model,
        dataloader=dataloaders[evaluation_split],
        device=torch_device,
    )
    figure_root = paths["figures"]
    _write_readout_examples(figure_root / "readout_examples.json", readout_examples)
    _write_readout_render_cache(
        figure_root / "readout_examples.pt",
        readout_examples,
        source_checkpoint=checkpoint,
        source_checkpoint_path=selected_checkpoint_path,
        config_hash=_config_hash(paths["config"]),
    )
    figures = {
        "04_optical_readout_examples": visualize_optical_readout_examples(
            readout_examples,
            figure_root / "04_optical_readout_examples",
        )
    }
    return figures, mismatches


def replot_run(
    *,
    project_root: str | Path = Path.cwd(),
    topology: str = "without_lens",
    run_name: str = "default",
    mode: str = "auto",
    checkpoint: str = "best",
    device: str = "cpu",
) -> dict[str, object]:
    """
    重绘指定分类运行的缓存图或 checkpoint 图
    """
    if mode not in REDRAW_MODES:
        message = f"mode must be one of: {', '.join(REDRAW_MODES)}"
        raise ValueError(message)
    if checkpoint not in CHECKPOINT_CHOICES:
        message = f"checkpoint must be one of: {', '.join(CHECKPOINT_CHOICES)}"
        raise ValueError(message)

    normalized_topology = normalize_topology(topology)
    paths = build_run_paths(project_root, normalized_topology, run_name)
    figures: dict[str, dict[str, str]] = {}
    skipped: list[str] = []
    config_mismatches: dict[str, dict[str, object]] = {}

    if mode in {"cached", "auto"}:
        if mode == "cached":
            figures.update(_replot_cached_figures(paths))
        else:
            try:
                figures.update(_replot_cached_figures(paths))
            except Exception as error:
                skipped.append(f"cached scalar redraw failed: {error}")

    if mode in {"checkpoint", "auto"}:
        try:
            checkpoint_figures, config_mismatches = _replot_checkpoint_figures(
                paths,
                checkpoint=checkpoint,
                device=device,
            )
            figures.update(checkpoint_figures)
        except FileNotFoundError as error:
            if mode == "checkpoint":
                raise
            skipped.append(str(error))
        except Exception as error:
            if mode == "checkpoint":
                raise
            skipped.append(f"checkpoint redraw failed: {error}")

    if not figures and mode == "auto":
        raise FileNotFoundError(
            "no classification artifacts could be redrawn; skipped: "
            + "; ".join(skipped)
        )

    status = "PASS" if figures else "SKIPPED"
    if status == "PASS" and config_mismatches:
        status = "PASS_WITH_WARNINGS"

    return {
        "status": status,
        "topology": normalized_topology,
        "run_name": run_name,
        "mode": mode,
        "checkpoint": checkpoint,
        "figures": figures,
        "skipped": skipped,
        "config_mismatches": config_mismatches,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    解析分类重绘命令行参数
    """
    parser = argparse.ArgumentParser(description="Redraw classification figures.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--topology",
        action="append",
        choices=("without_lens", "with_lens"),
        help="Topology to redraw. Repeat to redraw multiple topologies.",
    )
    parser.add_argument("--run-name", default="default")
    parser.add_argument("--mode", choices=REDRAW_MODES, default="auto")
    parser.add_argument("--checkpoint", choices=CHECKPOINT_CHOICES, default="best")
    parser.add_argument("--device", default="cpu")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    执行分类重绘 CLI 并刷新汇总报告
    """
    args = parse_args(argv)
    topologies = args.topology or ["without_lens", "with_lens"]
    results = {
        topology: replot_run(
            project_root=args.project_root,
            topology=topology,
            run_name=args.run_name,
            mode=args.mode,
            checkpoint=args.checkpoint,
            device=args.device,
        )
        for topology in topologies
    }
    summary_path = report.run(project_root=args.project_root)
    return {"runs": results, "summary_path": summary_path}


if __name__ == "__main__":
    main()

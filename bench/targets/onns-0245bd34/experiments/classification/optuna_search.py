from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import csv
from dataclasses import replace
import importlib
import importlib.util
import json
from pathlib import Path
import shutil

from experiments.classification.config import SearchConfig, TrainingConfig
from experiments.classification.train import run_training

_UNSET = object()


def _output_dir(project_root: str | Path) -> Path:
    path = Path(project_root) / "results" / "classification" / "optuna"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _reset_output_dir(output_dir: Path) -> None:
    for stale_path in output_dir.iterdir():
        if stale_path.is_dir():
            shutil.rmtree(stale_path)
        else:
            stale_path.unlink()


def write_skipped(
    project_root: str | Path = Path.cwd(),
    *,
    reason: str,
) -> dict[str, object]:
    """
    写入 Optuna 跳过摘要
    """
    output_dir = _output_dir(project_root)
    _reset_output_dir(output_dir)
    summary_path = _write_summary(
        output_dir,
        status="SKIPPED",
        trials=0,
        warnings=[reason],
        best_value=None,
    )
    return {"status": "SKIPPED", "summary_path": summary_path, "warnings": [reason]}


def _write_json(path: str | Path, payload: object) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    return output_path


def _write_summary(
    output_dir: Path,
    *,
    status: str,
    trials: int,
    best_value: float | None,
    warnings: Sequence[str] = (),
) -> Path:
    lines = [
        "# Classification Optuna Search",
        "",
        f"Status: {status}",
        "",
        "## Settings",
        f"- trials: {trials}",
        "",
        "## Results",
        f"- best_value: {best_value:.6f}" if best_value is not None else "- best_value: n/a",
    ]
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(
        [
            "",
            "## Artifacts",
            "- optuna_trials.csv",
            "- best_params.json",
            "- best_trial_summary.txt",
            "- optimization_history.png / optimization_history.svg",
        ]
    )
    output_path = output_dir / "summary.md"
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _metric_from_training_result(result: Mapping[str, object]) -> float:
    final_metrics = result.get("final_metrics", {})
    if not isinstance(final_metrics, Mapping):
        return 0.0
    return float(final_metrics.get("best_val_accuracy", 0.0))


def _resolve_search_config(
    search: SearchConfig | None,
    *,
    trials: int | None = None,
    is_best_retraining_enabled: bool | None = None,
    trial_epochs: int | None = None,
    seed: int | None = None,
    samples_per_class: int | None | object = _UNSET,
) -> SearchConfig:
    resolved = search or SearchConfig()
    replacements: dict[str, object] = {}
    if trials is not None:
        replacements["trials"] = trials
    if is_best_retraining_enabled is not None:
        replacements["is_best_retraining_enabled"] = is_best_retraining_enabled
    if trial_epochs is not None:
        replacements["trial_epochs"] = trial_epochs
    if seed is not None:
        replacements["seed"] = seed
    if samples_per_class is not _UNSET:
        replacements["samples_per_class"] = samples_per_class
    if replacements:
        resolved = replace(resolved, **replacements)
    return resolved.normalized()


def _trial_params(trial: object, *, search: SearchConfig) -> dict[str, object]:
    topology = trial.suggest_categorical("topology", list(search.topology_candidates))
    learning_rate_low, learning_rate_high = search.learning_rate_range
    propagation_low, propagation_high = search.propagation_distance_range
    return {
        "topology": str(topology),
        "batch_size": int(
            trial.suggest_categorical("batch_size", list(search.batch_size_candidates))
        ),
        "learning_rate": float(
            trial.suggest_float(
                "learning_rate",
                learning_rate_low,
                learning_rate_high,
                log=True,
            )
        ),
        "resize_mode": str(
            trial.suggest_categorical(
                "resize_mode",
                list(search.resize_mode_candidates),
            )
        ),
        "propagation_distance": float(
            trial.suggest_float(
                "propagation_distance",
                propagation_low,
                propagation_high,
            )
        ),
        "epochs": int(trial.suggest_int("epochs", 1, search.trial_epochs)),
    }


def _write_trials_csv(study: object, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["number", "value", "state", "params"],
        )
        writer.writeheader()
        for trial in getattr(study, "trials", []):
            writer.writerow(
                {
                    "number": getattr(trial, "number", ""),
                    "value": getattr(trial, "value", ""),
                    "state": str(getattr(trial, "state", "")),
                    "params": json.dumps(
                        getattr(trial, "params", {}),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                }
            )
    return output_path


def _save_optimization_history(study: object, output_dir: Path) -> list[str]:
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt

        from experiments.classification.visualize import (
            _apply_classification_figure_style,
            figure_style,
            line_style,
            palette_color,
            save_classification_figure_pair,
            style_report_axis,
        )
    except (ImportError, RuntimeError, ValueError) as error:
        return [f"Matplotlib unavailable: {error}"]

    trials = [
        trial
        for trial in getattr(study, "trials", [])
        if getattr(trial, "value", None) is not None
    ]
    if not trials:
        return ["No completed Optuna trials; optimization history skipped."]
    numbers = [int(getattr(trial, "number", 0)) for trial in trials]
    values = [float(getattr(trial, "value", 0.0)) for trial in trials]
    figure = figure_style("optimization_history")
    line = line_style("training_curve")
    fig, axis = plt.subplots(figsize=figure.figsize)
    axis.plot(
        numbers,
        values,
        marker="o",
        color=palette_color("train_line"),
        linewidth=line.width,
    )
    axis.set_title(figure.title)
    axis.set_xlabel("Trial")
    axis.set_ylabel("Validation accuracy")
    style_report_axis(axis)
    fig.tight_layout()
    save_classification_figure_pair(
        fig,
        output_dir / "optimization_history",
        style_applier=_apply_classification_figure_style,
    )
    return []


def run_optuna_search(
    project_root: str | Path = Path.cwd(),
    device: str = "cpu",
    *,
    search: SearchConfig | None = None,
    trials: int | None = None,
    is_best_retraining_enabled: bool | None = None,
    trial_epochs: int | None = None,
    seed: int | None = None,
    samples_per_class: int | None | object = _UNSET,
) -> dict[str, object]:
    """
    运行简洁 Optuna 搜索
    """
    resolved_search = _resolve_search_config(
        search,
        trials=trials,
        is_best_retraining_enabled=is_best_retraining_enabled,
        trial_epochs=trial_epochs,
        seed=seed,
        samples_per_class=samples_per_class,
    )
    output_dir = _output_dir(project_root)
    _reset_output_dir(output_dir)
    if importlib.util.find_spec("optuna") is None:
        return write_skipped(
            project_root=project_root,
            reason="Optuna is not installed; search was not executed.",
        )

    optuna = importlib.import_module("optuna")
    study = optuna.create_study(direction="maximize")

    def objective(trial: object) -> float:
        """
        训练单个 trial 并返回验证准确率
        """
        params = _trial_params(trial, search=resolved_search)
        config = TrainingConfig(
            topology=str(params["topology"]),
            batch_size=int(params["batch_size"]),
            learning_rate=float(params["learning_rate"]),
            epochs=int(params["epochs"]),
            device=device,
            seed=resolved_search.seed + int(getattr(trial, "number", 0)),
            run_name=f"optuna_trial_{getattr(trial, 'number', 0)}",
            project_root=Path(project_root),
            resize_mode=str(params["resize_mode"]),
            propagation_distance=float(params["propagation_distance"]),
            samples_per_class=resolved_search.samples_per_class,
        )
        return _metric_from_training_result(run_training(config))

    study.optimize(objective, n_trials=resolved_search.trials)
    _write_trials_csv(study, output_dir / "optuna_trials.csv")
    best_params = dict(getattr(study, "best_params", {}))
    _write_json(output_dir / "best_params.json", best_params)
    best_value = float(getattr(study, "best_value", 0.0))
    best_trial = getattr(study, "best_trial", None)
    (output_dir / "best_trial_summary.txt").write_text(
        "\n".join(
            [
                f"number: {getattr(best_trial, 'number', '')}",
                f"value: {best_value:.6f}",
                f"params: {json.dumps(best_params, ensure_ascii=False, sort_keys=True)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    warnings = _save_optimization_history(study, output_dir)
    retrain_result = None
    if resolved_search.is_best_retraining_enabled and best_params:
        retrain_config = TrainingConfig(
            topology=str(best_params.get("topology", "without_lens")),
            batch_size=int(best_params.get("batch_size", 128)),
            learning_rate=float(best_params.get("learning_rate", 0.0037)),
            epochs=50,
            device=device,
            seed=resolved_search.seed,
            run_name="optuna_best_retrain",
            project_root=Path(project_root),
            resize_mode=str(best_params.get("resize_mode", "bilinear")),
            propagation_distance=float(best_params.get("propagation_distance", 5e-3)),
            samples_per_class=resolved_search.samples_per_class,
        )
        retrain_result = run_training(retrain_config)
    summary_path = _write_summary(
        output_dir,
        status="PASS",
        trials=resolved_search.trials,
        best_value=best_value,
        warnings=warnings,
    )
    return {
        "status": "PASS",
        "summary_path": summary_path,
        "best_params": best_params,
        "best_value": best_value,
        "warnings": warnings,
        "retrain_result": retrain_result,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    解析 Optuna 命令行参数
    """
    parser = argparse.ArgumentParser(description="Run classification Optuna search.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--retrain-best", action="store_true")
    parser.add_argument("--trial-epochs", type=int, default=3)
    parser.add_argument("--samples-per-class", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    命令行搜索入口
    """
    args = parse_args(argv)
    search = SearchConfig(
        trials=args.trials,
        trial_epochs=args.trial_epochs,
        is_best_retraining_enabled=args.retrain_best,
        samples_per_class=args.samples_per_class,
    )
    return run_optuna_search(
        project_root=args.project_root,
        device=args.device,
        search=search,
    )


if __name__ == "__main__":
    main()

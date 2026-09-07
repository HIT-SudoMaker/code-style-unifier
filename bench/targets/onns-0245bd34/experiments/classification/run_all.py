from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from experiments.classification import (
    optuna_search,
    reference_comparison,
    report,
    train,
)
from experiments.classification.config import TrainingConfig


def run(
    project_root: str | Path = Path.cwd(),
    *,
    epochs: int = 50,
    device: str = "cpu",
    is_optuna_enabled: bool = False,
    is_optuna_skipped: bool | None = None,
    optuna_trials: int = 10,
    samples_per_class: int | None = None,
) -> dict[str, object]:
    """
    运行两个 D2NN 分类基线和可选 Optuna 搜索
    """
    root = Path(project_root)
    results: dict[str, object] = {}
    for topology in ("without_lens", "with_lens"):
        config = TrainingConfig(
            topology=topology,
            epochs=epochs,
            device=device,
            run_name="default",
            project_root=root,
            samples_per_class=samples_per_class,
        )
        results[topology] = train.run_training(config)

    if is_optuna_skipped is not None:
        is_optuna_enabled = not is_optuna_skipped

    if not is_optuna_enabled:
        results["optuna"] = optuna_search.write_skipped(
            project_root=root,
            reason="Optuna search skipped for canonical baseline run.",
        )
    else:
        results["optuna"] = optuna_search.run_optuna_search(
            project_root=root,
            trials=optuna_trials,
            device=device,
            samples_per_class=samples_per_class,
        )
    results["reference_comparison"] = reference_comparison.run(project_root=root)
    results["summary_path"] = report.run(project_root=root)
    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """
    解析 run_all 命令行参数
    """
    parser = argparse.ArgumentParser(description="Run D2NN classification baselines.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--enable-optuna", action="store_true")
    parser.add_argument("--skip-optuna", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--optuna-trials", type=int, default=10)
    parser.add_argument("--samples-per-class", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    命令行入口
    """
    args = parse_args(argv)
    return run(
        project_root=args.project_root,
        epochs=args.epochs,
        device=args.device,
        is_optuna_enabled=args.enable_optuna and not args.skip_optuna,
        optuna_trials=args.optuna_trials,
        samples_per_class=args.samples_per_class,
    )


if __name__ == "__main__":
    main()

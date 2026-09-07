from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from experiments.validation.config import (
    coerce_run_config,
    ValidationBasicConfig,
    ValidationRunConfig,
)
from experiments.validation.data import run_data
from experiments.validation.layers import run_layers
from experiments.validation.layers.validation_utils import aggregate_status, clear_output_dir


def run(
    output_root: str | Path = "results/validation",
    *,
    config: ValidationBasicConfig | ValidationRunConfig | None = None,
    device: str = "auto",
    seed: int = 42,
    size: str = "middle",
) -> dict[str, object]:
    """
    运行全部validation验证器
    """
    run_config = coerce_run_config(
        config,
        output_root=output_root,
        device=device,
        seed=seed,
        size=size,
    )
    basic = run_config.basic
    root = clear_output_dir(Path(basic.output_root))
    results: dict[str, object] = {}
    status_inputs: list[dict[str, object]] = []
    if "data" in run_config.suites:
        data_result = run_data.run(
            output_root=root / "data",
            device=basic.device,
            seed=basic.seed,
            size=basic.size,
        )
        results["data"] = data_result
        status_inputs.append(data_result)
    if "layers" in run_config.suites:
        layer_result = run_layers.run(
            output_root=root / "layers",
            device=basic.device,
            seed=basic.seed,
            size=basic.size,
        )
        results["layers"] = layer_result
        status_inputs.append(layer_result)
    return {"status": aggregate_status(status_inputs), **results}


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    解析命令行参数并运行全部validation
    """
    parser = argparse.ArgumentParser(description="Run validation utilities.")
    parser.add_argument("--output-root", type=Path, default=Path("results/validation"))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--size", choices=("tiny", "middle", "full"), default="middle")
    args = parser.parse_args(argv)
    return run(
        output_root=args.output_root,
        device=args.device,
        seed=args.seed,
        size=args.size,
    )


if __name__ == "__main__":
    main()

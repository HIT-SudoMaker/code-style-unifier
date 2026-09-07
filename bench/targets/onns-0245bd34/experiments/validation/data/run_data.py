from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from experiments.validation.config import (
    coerce_basic_config,
    ValidationBasicConfig,
    ValidationRunConfig,
)
from experiments.validation.data import (
    validate_degradation_scenarios,
    validate_end_to_end_pipeline,
    validate_raw_sources,
)
from experiments.validation.layers.validation_utils import aggregate_status, ensure_output_dir

VALIDATORS = (
    validate_raw_sources,
    validate_degradation_scenarios,
    validate_end_to_end_pipeline,
)


def _validator_name(validator: ModuleType | object) -> str:
    name = getattr(validator, "__name__", validator.__class__.__name__)
    return str(name).rsplit(".", maxsplit=1)[-1].removeprefix("validate_")


def _failure_record(validator: ModuleType | object, error: Exception) -> dict[str, object]:
    return {
        "data": _validator_name(validator),
        "status": "FAIL",
        "error": f"{error.__class__.__name__}: {error}",
        "checks": [],
    }


def run(
    output_root: str | Path = "results/validation/data",
    *,
    config: ValidationBasicConfig | ValidationRunConfig | None = None,
    device: str = "auto",
    seed: int = 42,
    size: str = "middle",
) -> dict[str, object]:
    """
    运行全部data validation验证器
    """
    basic = coerce_basic_config(
        config,
        output_root=output_root,
        device=device,
        seed=seed,
        size=size,
    )
    root = ensure_output_dir(Path(basic.output_root))
    results: list[dict[str, object]] = []
    for validator in VALIDATORS:
        try:
            results.append(
                validator.run(
                    output_root=root,
                    device=basic.device,
                    seed=basic.seed,
                    size=basic.size,
                ),
            )
        except Exception as error:
            results.append(_failure_record(validator, error))
    return {"status": aggregate_status(results), "data": results}


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    解析命令行参数并运行data validation
    """
    parser = argparse.ArgumentParser(description="Run data validation utilities.")
    parser.add_argument("--output-root", type=Path, default=Path("results/validation/data"))
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

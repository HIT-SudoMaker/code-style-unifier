from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Literal

from experiments.restoration.fixed_measurement.evidence.training_artifacts import write_json
from experiments.restoration.fixed_measurement.protocol.inputs import (
    DEFAULT_OPERATING_POINT,
    DEFAULT_SPLIT_MANIFEST,
    load_protocol_inputs,
)
from experiments.restoration.fixed_measurement import (
    FixedMeasurementRequest,
    run_fixed_measurement,
)
from experiments.restoration.fixed_measurement.protocol.plan import (
    FIXED_BACKEND_MODEL,
    compile_fixed_experiment_plan,
)
from experiments.restoration.fixed_measurement.protocol.settings import (
    FIXED_TRAINING_POLICY,
    PRIMARY_MAX_OPTIMIZER_UPDATES,
    ProtocolInputs,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    瑙ｆ瀽鍒嗛樁娈靛浐瀹氭祴閲忓崗璁懡浠?    """
    parser = argparse.ArgumentParser(
        description="Run the preregistered fixed-measurement restoration protocol",
    )
    parser.add_argument(
        "command",
        choices=(
            "describe",
            "load",
            "train",
        ),
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--operating-point",
        type=Path,
        default=DEFAULT_OPERATING_POINT,
    )
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=DEFAULT_SPLIT_MANIFEST,
    )
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """
    鎵ц涓€涓甫璇佹嵁闂ㄧ鐨勫浐瀹氭祴閲忓崗璁樁娈?    """
    arguments = parse_args(argv)
    inputs = _protocol_inputs(arguments)
    if arguments.command == "describe":
        result = _write_protocol_descriptions(inputs)
    else:
        execution_mode = "load" if arguments.command == "load" else "train"
        record = run_fixed_measurement(
            _fixed_request(inputs, execution_mode=execution_mode)
        )
        result = {
            "status": record.status,
            "study_count": record.study_count,
            "report_json": record.report_json,
            "summary_md": record.summary_md,
            "skipped_run_ids": record.skipped_run_ids,
            "execution_mode": record.execution_mode,
        }
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("status") == "PASS" else 1


def _protocol_inputs(arguments: argparse.Namespace) -> ProtocolInputs:
    return load_protocol_inputs(
        project_root=arguments.project_root,
        operating_point_path=arguments.operating_point,
        split_manifest_path=arguments.split_manifest,
        device=arguments.device,
    )


def _write_protocol_descriptions(inputs: ProtocolInputs) -> dict[str, object]:
    output_dir = (
        Path(inputs.project_root)
        / "results"
        / "restoration"
        / "fixed_measurement"
        / "protocol"
    )
    plan = compile_fixed_experiment_plan(inputs)
    matrix_path = write_json(
        output_dir / "fixed_measurement_matrix.json",
        {
            "schema_version": "fixed_measurement_matrix_v3",
            "plan_id": plan.plan_id,
            "run_count": len(plan.studies),
            "backend_model": FIXED_BACKEND_MODEL,
            "primary_optimizer_update_budget": PRIMARY_MAX_OPTIMIZER_UPDATES,
            "runs": [
                {
                    "role": study.study_id,
                    "method": study.method_id,
                    "profile_name": study.profile_name,
                    "seed": study.seed,
                    "run_id": study.run_id,
                    "upstream_run_ids": study.upstream_run_ids,
                }
                for study in plan.studies
            ],
        },
    )
    training_policy_path = write_json(
        output_dir / "fixed_training_policy.json",
        {
            "schema_version": "fixed_measurement_training_policy_v1",
            "policy_count": len(FIXED_TRAINING_POLICY),
            "policies": [
                {
                    "family": family,
                    "profile_name": profile_name,
                    "parameters": dict(parameters),
                }
                for (family, profile_name), parameters in sorted(
                    FIXED_TRAINING_POLICY.items()
                )
            ],
        },
    )
    return {
        "status": "PASS",
        "fixed_measurement_matrix": matrix_path,
        "fixed_training_policy": training_policy_path,
    }


def _fixed_request(
    inputs: ProtocolInputs,
    *,
    execution_mode: Literal["load", "train"],
) -> FixedMeasurementRequest:
    return FixedMeasurementRequest(
        project_root=inputs.project_root,
        operating_point_path=inputs.operating_point_path,
        split_manifest=inputs.split_manifest,
        dataset_root=inputs.dataset_root,
        device=inputs.device,
        execution_mode=execution_mode,
    )


if __name__ == "__main__":
    raise SystemExit(main())

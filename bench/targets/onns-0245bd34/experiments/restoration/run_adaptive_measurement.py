from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.restoration.adaptive_measurement.protocol.oracle import (
    OracleLadderConfig,
)
from experiments.restoration.adaptive_measurement.protocol.episode import (
    AdaptiveEpisodePolicy,
)
from experiments.restoration.adaptive_measurement.validation.hardware_readiness import (
    HardwareEvidence,
    assess_hardware_readiness,
)
from experiments.restoration.adaptive_measurement.validation.oracle_ladder import (
    run_oracle_ladder,
)
from experiments.restoration.degradation import STANDARD_RESTORATION_PROFILE_NAMES
from experiments.restoration.pupil_aberrations import (
    SUPPORTED_PUPIL_MODES,
    PupilAberrationState,
)
from experiments.restoration.studies import (
    DifferentialCorrectionStudyConfig,
    run_differential_correction_study,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run evidence-gated Adaptive restoration studies",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    oracle = commands.add_parser(
        "oracle-ladder",
        help="Run the physically distinct O1/O2/O3 simulation gate",
    )
    oracle.add_argument("--project-root", type=Path, default=Path.cwd())
    oracle.add_argument("--resolution", type=int, default=512)
    oracle.add_argument(
        "--target",
        choices=("siemens_star", "slanted_edge", "usaf_bars"),
        default="siemens_star",
    )
    oracle.add_argument("--phase-levels", type=int, default=256)
    oracle.add_argument("--response-gain", type=float, default=0.97)
    oracle.add_argument("--drift-radians", type=float, default=0.015)
    oracle.add_argument("--crosstalk-mix", type=float, default=0.04)
    oracle.add_argument("--minimum-o3-gain-db", type=float, default=1.0)
    oracle.add_argument("--seed", type=int, default=2026)
    oracle.add_argument("--device", choices=("cpu", "cuda"), default="cpu")

    readiness = commands.add_parser(
        "check-hardware",
        help="Check measured readiness evidence before a physical episode",
    )
    readiness.add_argument("--evidence", type=Path, required=True)

    correction = commands.add_parser(
        "differential-correction",
        help="Run one controlled replay and differential-aberration study",
    )
    correction.add_argument("--project-root", type=Path, default=Path.cwd())
    correction.add_argument("--seed", type=int, default=2026)
    correction.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    correction.add_argument(
        "--degradation-profile",
        choices=("all", *STANDARD_RESTORATION_PROFILE_NAMES),
        default="all",
    )
    correction.add_argument(
        "--evaluation-split",
        choices=("train", "val", "test"),
        default="val",
    )
    correction.add_argument("--scene-index", type=int, default=0)
    correction.add_argument(
        "--aberration-mode",
        choices=SUPPORTED_PUPIL_MODES,
        default="defocus",
    )
    correction.add_argument("--aberration-rms-radians", type=float, default=1.0)
    correction.add_argument("--fit-iterations", type=int, default=150)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_args(argv)
    if arguments.command == "oracle-ladder":
        payload, exit_code = _run_oracle(arguments)
    elif arguments.command == "check-hardware":
        payload, exit_code = _check_hardware(arguments.evidence)
    else:
        payload, exit_code = _run_differential_correction(arguments)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


def _run_oracle(arguments: argparse.Namespace) -> tuple[dict[str, object], int]:
    result = run_oracle_ladder(
        OracleLadderConfig(
            project_root=arguments.project_root,
            array_resolution=(arguments.resolution, arguments.resolution),
            target_name=arguments.target,
            phase_levels=arguments.phase_levels,
            response_gain=arguments.response_gain,
            drift_radians=arguments.drift_radians,
            crosstalk_mix=arguments.crosstalk_mix,
            minimum_o3_gain_db=arguments.minimum_o3_gain_db,
            seed=arguments.seed,
            device=arguments.device,
        )
    )
    return (
        {
            "status": result.status,
            "run_id": result.run_id,
            "run_dir": result.run_dir.as_posix(),
            "metrics": dict(result.metrics),
            "result_json": result.result_json.as_posix(),
            "summary_md": result.summary_md.as_posix(),
        },
        0 if result.status == "PASS" else 1,
    )


def _check_hardware(evidence_path: Path) -> tuple[dict[str, object], int]:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        raise ValueError("hardware evidence must be a JSON object")
    report = assess_hardware_readiness(HardwareEvidence.from_mapping(evidence))
    return (
        {
            "status": report.status,
            "missing_fields": list(report.missing_fields),
            "invalid_fields": dict(report.invalid_fields),
        },
        0 if report.status == "READY" else 1,
    )


def _run_differential_correction(
    arguments: argparse.Namespace,
) -> tuple[dict[str, object], int]:
    profile_names = (
        STANDARD_RESTORATION_PROFILE_NAMES
        if arguments.degradation_profile == "all"
        else (arguments.degradation_profile,)
    )
    run_dirs = tuple(
        run_differential_correction_study(
            DifferentialCorrectionStudyConfig(
                project_root=arguments.project_root,
                degradation_profile_name=profile_name,
                evaluation_split=arguments.evaluation_split,
                scene_index=arguments.scene_index,
                aberration=PupilAberrationState(
                    {arguments.aberration_mode: (arguments.aberration_rms_radians)}
                ),
                policy=AdaptiveEpisodePolicy(
                    fit_iteration_count=arguments.fit_iterations,
                ),
                seed=arguments.seed,
                device=arguments.device,
            )
        )
        for profile_name in profile_names
    )
    return (
        {
            "status": "MEASURED",
            "runs": [
                {
                    "degradation_profile": profile_name,
                    "run_dir": run_dir.as_posix(),
                    "result_json": (run_dir / "result.json").as_posix(),
                    "comparison_png": (run_dir / "comparison.png").as_posix(),
                }
                for profile_name, run_dir in zip(
                    profile_names,
                    run_dirs,
                    strict=True,
                )
            ],
        },
        0,
    )


if __name__ == "__main__":
    raise SystemExit(main())

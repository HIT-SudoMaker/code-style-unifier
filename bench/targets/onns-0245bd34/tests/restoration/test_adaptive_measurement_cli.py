from __future__ import annotations

from experiments.restoration.run_adaptive_measurement import parse_args


def test_differential_aberration_cli_names_the_controlled_replay_contract() -> None:
    arguments = parse_args(
        [
            "differential-correction",
            "--degradation-profile",
            "medium",
            "--aberration-mode",
            "coma_horizontal",
            "--aberration-rms-radians",
            "0.8",
            "--fit-iterations",
            "120",
        ]
    )

    assert arguments.command == "differential-correction"
    assert arguments.degradation_profile == "medium"
    assert arguments.aberration_mode == "coma_horizontal"
    assert arguments.aberration_rms_radians == 0.8
    assert arguments.fit_iterations == 120

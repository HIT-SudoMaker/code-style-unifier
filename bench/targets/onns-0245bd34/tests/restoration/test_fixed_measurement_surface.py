from __future__ import annotations

import importlib


def test_fixed_measurement_surface_exposes_one_deep_interface() -> None:
    """
    验证固定测量公开对偶执行接口
    """
    fixed_measurement = importlib.import_module(
        "experiments.restoration.fixed_measurement"
    )

    assert tuple(fixed_measurement.__all__) == (
        "FixedMeasurementRequest",
        "FixedMeasurementRecord",
        "FixedOpticalRecord",
        "run_fixed_measurement",
        "record_fixed_optical_states",
    )
    for name in fixed_measurement.__all__:
        assert hasattr(fixed_measurement, name)
    for legacy_name in (
        "StudyConfig",
        "ExperimentPlan",
        "run_experiment",
        "verify_formal_archive",
        "acquire_fixed_replay_observation",
    ):
        assert not hasattr(fixed_measurement, legacy_name)

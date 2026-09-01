from __future__ import annotations

import pytest

from experiments.restoration.fixed_measurement.learning.schemas import (
    BACKEND_FAMILIES,
    BACKEND_MODELS,
    BENCHMARK_SCHEMA_VERSION,
    BENCHMARK_BASELINE_FIELDS,
    BENCHMARK_EFFICIENCY_FIELDS,
    BENCHMARK_SAMPLE_FIELDS,
    BENCHMARK_SIGNIFICANCE_FIELDS,
    BOUNDARY_FAILURE_FIELDS,
    BOUNDARY_GRID_FIELDS,
    CHARACTERIZATION_BASELINE_NAMES,
    FRONTEND_CONDITIONS,
    METHOD_MODEL_ROLE_MAP,
    RESTORATION_METHOD_NAMES,
    RESTORATION_MODEL_ROLES,
    TRAINABLE_PARAMETERS_BY_MODEL_ROLE,
    backend_identity_strings,
    model_role_for_method,
    validate_method_model_role,
)
from experiments.restoration.fixed_measurement.learning.backend import BackendConfig


def test_characterization_and_benchmark_namespaces_are_separate() -> None:
    """
    鏍￠獙 characterization 涓?benchmark 鍛藉悕绌洪棿浜掍笉娣风敤
    """
    assert CHARACTERIZATION_BASELINE_NAMES == (
        "input_identity",
        "reference_arm_only",
        "process_arm_phase_zero",
        "full_frontend_phase_zero",
        "interference_term",
    )
    assert RESTORATION_METHOD_NAMES == (
        "degraded",
        "reference_arm",
        "process_arm_zero_phase",
        "full_frontend_zero_phase",
        "full_frontend_trained_phase",
        "digital_backend",
        "frozen_optical_frontend_digital_backend",
        "joint_optical_frontend_digital_backend",
    )
    assert "interference_term" not in RESTORATION_METHOD_NAMES
    assert "digital_backend" not in CHARACTERIZATION_BASELINE_NAMES


@pytest.mark.parametrize(
    "method_name",
    (
        "frozen_frontend_backend",
        "joint_frontend_backend",
    ),
)
def test_legacy_hybrid_method_names_are_rejected(method_name: str) -> None:
    """
    Verify legacy hybrid names are not accepted as read-side aliases.
    """
    with pytest.raises(
        ValueError,
        match="frozen_optical_frontend_digital_backend",
    ):
        model_role_for_method(method_name)


def test_method_role_mapping_is_complete_and_unambiguous() -> None:
    """
    鏍￠獙鎭㈠鏂规硶鍒版ā鍨嬭鑹茬殑鏄犲皠瀹屾暣涓斿崟涔?    """
    assert RESTORATION_MODEL_ROLES == (
        "deterministic",
        "frontend_only",
        "backend_only",
        "frozen_optical_frontend_digital_backend",
        "joint_optical_frontend_digital_backend",
    )
    assert set(METHOD_MODEL_ROLE_MAP) == set(RESTORATION_METHOD_NAMES)
    assert set(METHOD_MODEL_ROLE_MAP.values()).issubset(set(RESTORATION_MODEL_ROLES))
    assert model_role_for_method("degraded") == "deterministic"
    assert model_role_for_method("full_frontend_trained_phase") == "frontend_only"
    assert model_role_for_method("digital_backend") == "backend_only"
    assert (
        model_role_for_method("joint_optical_frontend_digital_backend")
        == "joint_optical_frontend_digital_backend"
    )


def test_method_role_validation_rejects_invalid_combinations() -> None:
    """
    鏍￠獙鎭㈠鏂规硶涓庢ā鍨嬭鑹茬殑闈炴硶缁勫悎浼氳鎷掔粷
    """
    validate_method_model_role("degraded", "deterministic")
    validate_method_model_role("digital_backend", "backend_only")
    with pytest.raises(ValueError, match="method_name must be one of"):
        validate_method_model_role("unknown_method", "deterministic")
    with pytest.raises(ValueError, match="method_name must be one of"):
        validate_method_model_role("joint_frontend_backend", "backend_only")
    with pytest.raises(
        ValueError,
        match="model_role for digital_backend must be backend_only",
    ):
        validate_method_model_role("digital_backend", "frontend_only")


def test_trainable_parameter_contracts_are_role_specific() -> None:
    """
    鏍￠獙涓嶅悓妯″瀷瑙掕壊鎷ユ湁鐙珛璁粌鍙傛暟濂戠害
    """
    assert ("phase_mask_fourier",) in TRAINABLE_PARAMETERS_BY_MODEL_ROLE["frontend_only"]
    assert (
        "phase_mask_fourier",
        "phase_offset_reference",
    ) in TRAINABLE_PARAMETERS_BY_MODEL_ROLE["frontend_only"]
    assert ("backend",) in TRAINABLE_PARAMETERS_BY_MODEL_ROLE["backend_only"]
    assert ("backend",) in TRAINABLE_PARAMETERS_BY_MODEL_ROLE[
        "frozen_optical_frontend_digital_backend"
    ]
    assert (
        "phase_mask_fourier",
        "backend",
    ) in TRAINABLE_PARAMETERS_BY_MODEL_ROLE[
        "joint_optical_frontend_digital_backend"
    ]


def test_method_condition_names_are_stable() -> None:
    """
    鏍￠獙 benchmark 鏂规硶鏉′欢瀛楁鍙栧€肩ǔ瀹?    """
    assert FRONTEND_CONDITIONS == (
        "none",
        "reference_arm",
        "process_arm_zero_phase",
        "full_frontend_zero_phase",
        "full_frontend_trained_phase",
    )


def test_backend_families_are_restoration_native() -> None:
    """
    Verify backend family names expose only restoration-native choices.
    """
    assert BACKEND_FAMILIES == ("none", "restoration_native")


def test_backend_models_include_only_archived_fixed_scales() -> None:
    """
    Verify backend model names expose the project NAFNet variants.
    """
    assert BACKEND_MODELS == (
        "none",
        "nafnet_s",
        "nafnet_m",
    )


def test_csv_field_contracts_use_stable_long_form_fields() -> None:
    """
    鏍￠獙 benchmark 涓?boundary CSV 瀛楁椤哄簭绋冲畾
    """
    assert BENCHMARK_SCHEMA_VERSION == "restoration_benchmark_v4"
    assert BENCHMARK_SAMPLE_FIELDS == (
        "schema_version",
        "study_name",
        "condition_id",
        "sample_id",
        "dataset_name",
        "method_name",
        "model_role",
        "source_run_id",
        "source_checkpoint_path",
        "source_config_hash",
        "source_degradation_hash",
        "frontend_condition",
        "backend_family",
        "backend_model",
        "connection_mode",
        "initial_optical_residual_gate",
        "optical_residual_gate_state",
        "optical_residual_gate",
        "degradation_family",
        "degradation_level",
        "metric_name",
        "metric_value",
        "metric_unit",
        "status",
    )
    assert BENCHMARK_BASELINE_FIELDS == (
        "schema_version",
        "study_name",
        "condition_id",
        "method_name",
        "model_role",
        "source_run_id",
        "source_checkpoint_path",
        "source_config_hash",
        "source_degradation_hash",
        "frontend_condition",
        "backend_family",
        "backend_model",
        "connection_mode",
        "initial_optical_residual_gate",
        "optical_residual_gate_state",
        "optical_residual_gate",
        "metric_name",
        "mean_value",
        "std_value",
        "median_value",
        "num_samples",
        "metric_unit",
        "status",
    )
    assert BENCHMARK_SIGNIFICANCE_FIELDS == (
        "study_name",
        "condition_id",
        "metric_name",
        "method_name",
        "baseline_method_name",
        "mean_delta",
        "median_delta",
        "wilcoxon_statistic",
        "p_value",
        "alpha",
        "sample_count",
        "nonzero_difference_count",
        "status",
    )
    assert BENCHMARK_EFFICIENCY_FIELDS == (
        "study_name",
        "method_name",
        "model_role",
        "frontend_condition",
        "backend_family",
        "backend_model",
        "connection_mode",
        "initial_optical_residual_gate",
        "optical_residual_gate_state",
        "optical_residual_gate",
        "model_parameter_count",
        "model_conv2d_macs",
        "forward_seconds_mean",
        "forward_seconds_std",
        "status",
    )
    assert "method_name" in BOUNDARY_FAILURE_FIELDS
    assert "blur_level" in BOUNDARY_GRID_FIELDS


def test_backend_identity_strings_derive_display_columns_from_nested_backend() -> None:
    """
    Backend display columns are derived from canonical nested BackendConfig.
    """
    assert backend_identity_strings(None) == ("none", "none")
    assert backend_identity_strings(
        BackendConfig(model_name="nafnet_m", residual_learning=False)
    ) == ("restoration_native", "nafnet_m")

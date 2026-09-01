from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, Literal

from experiments.restoration.errors import invalid_restoration_contract

if TYPE_CHECKING:
    from experiments.restoration.fixed_measurement.learning.backend import BackendConfig


RestorationMethodName = Literal[
    "degraded",
    "reference_arm",
    "process_arm_zero_phase",
    "full_frontend_zero_phase",
    "full_frontend_trained_phase",
    "digital_backend",
    "frozen_optical_frontend_digital_backend",
    "joint_optical_frontend_digital_backend",
]

OpticalResidualGateState = Literal["", "zero", "learned", "one"]

ModelRole = Literal[
    "deterministic",
    "frontend_only",
    "backend_only",
    "frozen_optical_frontend_digital_backend",
    "joint_optical_frontend_digital_backend",
]

FrontendCondition = Literal[
    "none",
    "reference_arm",
    "process_arm_zero_phase",
    "full_frontend_zero_phase",
    "full_frontend_trained_phase",
]

BackendFamily = Literal["none", "restoration_native"]

BackendModel = Literal[
    "none",
    "nafnet_s",
    "nafnet_m",
]

CHARACTERIZATION_BASELINE_NAMES: Final[tuple[str, ...]] = (
    "input_identity",
    "reference_arm_only",
    "process_arm_phase_zero",
    "full_frontend_phase_zero",
    "interference_term",
)

RESTORATION_METHOD_NAMES: Final[tuple[str, ...]] = (
    "degraded",
    "reference_arm",
    "process_arm_zero_phase",
    "full_frontend_zero_phase",
    "full_frontend_trained_phase",
    "digital_backend",
    "frozen_optical_frontend_digital_backend",
    "joint_optical_frontend_digital_backend",
)

RESTORATION_MODEL_ROLES: Final[tuple[str, ...]] = (
    "deterministic",
    "frontend_only",
    "backend_only",
    "frozen_optical_frontend_digital_backend",
    "joint_optical_frontend_digital_backend",
)

FRONTEND_CONDITIONS: Final[tuple[str, ...]] = (
    "none",
    *RESTORATION_METHOD_NAMES[1:5],
)

BACKEND_FAMILIES: Final[tuple[str, ...]] = ("none", "restoration_native")

BACKEND_MODELS: Final[tuple[str, ...]] = (
    "none",
    "nafnet_s",
    "nafnet_m",
)

BENCHMARK_SCHEMA_VERSION: Final[str] = "restoration_benchmark_v4"

BENCHMARK_CONNECTION_FIELDS: Final[tuple[str, ...]] = (
    "connection_mode",
    "initial_optical_residual_gate",
    "optical_residual_gate_state",
    "optical_residual_gate",
)

METHOD_MODEL_ROLE_MAP: Final[Mapping[str, str]] = MappingProxyType(
    {
        "degraded": "deterministic",
        "reference_arm": "deterministic",
        "process_arm_zero_phase": "deterministic",
        "full_frontend_zero_phase": "deterministic",
        "full_frontend_trained_phase": "frontend_only",
        "digital_backend": "backend_only",
        "frozen_optical_frontend_digital_backend": (
            "frozen_optical_frontend_digital_backend"
        ),
        "joint_optical_frontend_digital_backend": (
            "joint_optical_frontend_digital_backend"
        ),
    }
)

DEFAULT_TRAINABLE_PARAMETERS_BY_MODEL_ROLE: Final[Mapping[str, tuple[str, ...]]] = (
    MappingProxyType(
        {
            "frontend_only": ("phase_mask_fourier",),
            "backend_only": ("backend",),
            "frozen_optical_frontend_digital_backend": ("backend",),
            "joint_optical_frontend_digital_backend": (
                "phase_mask_fourier",
                "backend",
            ),
        }
    )
)

TRAINABLE_PARAMETERS_BY_MODEL_ROLE: Final[Mapping[str, tuple[tuple[str, ...], ...]]] = (
    MappingProxyType(
        {
            "frontend_only": (
                ("phase_mask_fourier",),
                ("phase_mask_fourier", "phase_offset_reference"),
            ),
            "backend_only": (("backend",),),
            "frozen_optical_frontend_digital_backend": (
                ("backend",),
                ("connection", "backend"),
            ),
            "joint_optical_frontend_digital_backend": (
                ("phase_mask_fourier", "backend"),
                ("phase_mask_fourier", "connection", "backend"),
                ("phase_mask_fourier", "phase_offset_reference", "backend"),
                (
                    "phase_mask_fourier",
                    "phase_offset_reference",
                    "connection",
                    "backend",
                ),
            ),
        }
    )
)

BENCHMARK_SAMPLE_FIELDS: Final[tuple[str, ...]] = (
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
    *BENCHMARK_CONNECTION_FIELDS,
    "degradation_family",
    "degradation_level",
    "metric_name",
    "metric_value",
    "metric_unit",
    "status",
)

BENCHMARK_BASELINE_FIELDS: Final[tuple[str, ...]] = (
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
    *BENCHMARK_CONNECTION_FIELDS,
    "metric_name",
    "mean_value",
    "std_value",
    "median_value",
    "num_samples",
    "metric_unit",
    "status",
)

BENCHMARK_SIGNIFICANCE_FIELDS: Final[tuple[str, ...]] = (
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

BENCHMARK_EFFICIENCY_FIELDS: Final[tuple[str, ...]] = (
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
    # Historical field name; value is total model MACs for the active NAFNet.
    "model_conv2d_macs",
    "forward_seconds_mean",
    "forward_seconds_std",
    "status",
)

BOUNDARY_GRID_FIELDS: Final[tuple[str, ...]] = (
    "study_name",
    "condition_id",
    "degradation_family",
    "blur_level",
    "noise_level",
    "defocus_level",
    "speckle_level",
    "astigmatism_level",
    "photon_level",
    "seed",
    "status",
)

BOUNDARY_FAILURE_FIELDS: Final[tuple[str, ...]] = (
    "study_name",
    "condition_id",
    "method_name",
    "model_role",
    "frontend_condition",
    "backend_family",
    "backend_model",
    "reference_method_name",
    "primary_metric_name",
    "primary_metric_delta",
    "secondary_metric_name",
    "secondary_metric_delta",
    "failure_label",
    "failure_reason",
    "status",
)


def model_role_for_method(method_name: str) -> str:
    """
    杩斿洖 benchmark 鏂规硶瀵瑰簲鐨勬ā鍨嬭鑹?    """
    try:
        return METHOD_MODEL_ROLE_MAP[method_name]
    except KeyError as exc:
        allowed = ", ".join(RESTORATION_METHOD_NAMES)
        raise invalid_restoration_contract(
            f"method_name must be one of: {allowed}"
        ) from exc


def backend_identity_strings(backend: "BackendConfig | None") -> tuple[str, str]:
    """
    浠庢爣鍑嗗祵濂楄韩浠芥帹瀵兼暟瀛楀悗绔睍绀哄瓧娈?    """
    if backend is None:
        return ("none", "none")
    return (backend.family, backend.model_name)


def validate_method_model_role(method_name: str, model_role: str) -> None:
    """
    鏍￠獙 benchmark 鏂规硶涓庢ā鍨嬭鑹叉槸鍚﹀尮閰?    """
    expected_role = model_role_for_method(method_name)
    if model_role != expected_role:
        raise invalid_restoration_contract(
            f"model_role for {method_name} must be "
            f"{expected_role}; got {model_role}"
        )

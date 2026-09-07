from __future__ import annotations

import math
from numbers import Integral, Real
from typing import Any

from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
from experiments.restoration.errors import invalid_restoration_contract

_INTENSITY_NORMALIZATION_POLICIES = {
    "fixed_dataset_level",
    "characterization_calibrated_gain",
    "per_image_min_max",
}
_BACKEND_MODEL_ROLES = {
    "backend_only",
    "frozen_optical_frontend_digital_backend",
    "joint_optical_frontend_digital_backend",
}
_SUPPORTED_PHASE_PARAMETERIZATIONS = {"direct", "sigmoid"}
_SUPPORTED_PHASE_INITIALIZATIONS = {"zeros", "uniform", "normal"}
_SINGLE_CHANNEL_BACKEND_MODELS = (
    "nafnet_s",
    "nafnet_m",
)
_DUAL_CHANNEL_CONNECTION_MODES = ("dual_channel", "dual_channel_optical_zeroed")


def finite_real(name: str, value: object) -> float:
    """
    鏍￠獙骞惰繑鍥炴湁闄愬疄鏁?    """
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    return numeric_value


def positive(name: str, value: object) -> None:
    """
    鏍￠獙姝ｅ疄鏁?    """
    if finite_real(name, value) <= 0:
        raise invalid_restoration_contract(f"{name} must be positive")


def nonnegative(name: str, value: object) -> None:
    """
    鏍￠獙闈炶礋瀹炴暟
    """
    if finite_real(name, value) < 0:
        raise invalid_restoration_contract(f"{name} must be nonnegative")


def positive_integer(name: str, value: object) -> None:
    """
    鏍￠獙姝ｆ暣鏁?    """
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    if int(value) <= 0:
        raise invalid_restoration_contract(f"{name} must be a positive integer")


def nonnegative_integer(name: str, value: object) -> None:
    """
    鏍￠獙闈炶礋鏁存暟
    """
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise invalid_restoration_contract(f"{name} must be a nonnegative integer")
    if int(value) < 0:
        raise invalid_restoration_contract(f"{name} must be a nonnegative integer")


def boolean(name: str, value: object) -> None:
    """
    鏍￠獙甯冨皵鍊?    """
    if not isinstance(value, bool):
        raise invalid_restoration_contract(f"{name} must be a boolean")


def tuple_from_sequence(name: str, value: object) -> tuple[Any, ...]:
    """
    闈炴枃鏈簭鍒楀厓缁勫寲
    """
    if isinstance(value, (str, bytes)):
        raise invalid_restoration_contract(f"{name} must be a sequence")
    try:
        return tuple(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise invalid_restoration_contract(f"{name} must be a sequence") from exc


def validate_resolution_pair(name: str, value: object) -> None:
    """
    鏍￠獙浜岀淮鍒嗚鲸鐜?    """
    if not isinstance(value, tuple) or len(value) != 2:
        raise invalid_restoration_contract(f"{name} must have height and width")
    positive_integer(f"{name}[0]", value[0])
    positive_integer(f"{name}[1]", value[1])


def validate_intensity_normalization_policy(policy: str) -> None:
    """
    鏍￠獙寮哄害褰掍竴鍖栫瓥鐣?    """
    if policy not in _INTENSITY_NORMALIZATION_POLICIES:
        raise invalid_restoration_contract(
            "intensity_normalization_policy must be one of: "
            "fixed_dataset_level, characterization_calibrated_gain, per_image_min_max"
        )


def validate_backend_role(model_role: str, backend: BackendConfig | None) -> None:
    """
    鏍￠獙妯″瀷瑙掕壊涓庢暟瀛楀悗绔殑涓€鑷存€?    """
    if model_role == "frontend_only" and backend is not None:
        raise invalid_restoration_contract(
            "backend must be None for frontend_only training"
        )
    if model_role in _BACKEND_MODEL_ROLES and not isinstance(backend, BackendConfig):
        raise invalid_restoration_contract(
            "backend must be a BackendConfig for backend and hybrid roles"
        )


def validate_connection_role(model_role: str, connection_mode: str) -> None:
    """
    鏍￠獙妯″瀷瑙掕壊涓庤繛鎺ユ柟寮忕殑涓€鑷存€?    """
    if model_role in {"frontend_only", "backend_only"} and connection_mode != "serial":
        raise invalid_restoration_contract(
            "non-serial connection requires a hybrid model_role"
        )


def validate_backend_connection_compatibility(
    connection_mode: str,
    backend: BackendConfig | None,
) -> None:
    """
    鏍￠獙杩炴帴妯″紡涓庡悗绔緭鍏ヨ兘鍔涙槸鍚﹀吋瀹?    """
    if (
        connection_mode in _DUAL_CHANNEL_CONNECTION_MODES
        and backend is not None
        and backend.model_name in _SINGLE_CHANNEL_BACKEND_MODELS
    ):
        raise invalid_restoration_contract(
            "dual_channel connections require a multi-channel backend; "
            "the selected backend accepts single-channel input only"
        )
def validate_phase_options(
    phase_parameterization: str,
    phase_initialization: str,
) -> None:
    """
    鐩镐綅绛栫暐绾︽潫
    """
    if phase_parameterization not in _SUPPORTED_PHASE_PARAMETERIZATIONS:
        raise invalid_restoration_contract(
            "phase_parameterization must be one of: direct, sigmoid"
        )
    if phase_initialization not in _SUPPORTED_PHASE_INITIALIZATIONS:
        raise invalid_restoration_contract(
            "phase_initialization must be one of: zeros, uniform, normal"
        )

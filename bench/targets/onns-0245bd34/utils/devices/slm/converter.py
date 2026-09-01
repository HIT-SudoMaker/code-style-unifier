from __future__ import annotations

import math

import numpy as np

from .frame import SLMFrame
from .frame import SLM_10BIT_GRAY_LEVEL_COUNT
from .frame import SLM_10BIT_MAX_VALUE


_QUANTIZATION_EPSILON = 1e-4


def intensity_to_slm_frame(image: object) -> SLMFrame:
    """
    强度数据转十位帧

    参数:
        image: 二维图像，或单通道 [1, H, W] 图像

    返回:
        十位硬件帧。

    抛出:
        ValueError: 形状或数值范围无效时抛出
    """
    image_array = _as_float32_2d_array(image, context_name="intensity")
    if np.any(image_array < 0.0) or np.any(image_array > 1.0):
        message = "intensity values must be in range 0..1"
        raise ValueError(message)

    data = _quantize_unit_array_to_ten_bit(image_array)
    return _make_slm_frame(data)


def phase_to_slm_frame(
    phase: object,
    *,
    phase_period: float = math.tau,
) -> SLMFrame:
    """
    相位数据转十位帧

    参数:
        phase:        二维相位图，或单通道 [1, H, W] 相位图
        phase_period: 相位周期，默认 2pi

    返回:
        十位硬件帧。

    抛出:
        ValueError: 形状、相位周期或数值无效时抛出
    """
    if not np.isfinite(phase_period) or phase_period <= 0.0:
        message = "phase_period must be a positive finite value"
        raise ValueError(message)

    phase_array = _as_float32_2d_array(phase, context_name="phase")
    wrapped_phase = np.remainder(phase_array, float(phase_period))
    normalized_phase = wrapped_phase / float(phase_period)
    data = _quantize_unit_array_to_ten_bit(normalized_phase)
    return _make_slm_frame(data)


def _make_slm_frame(data: np.ndarray) -> SLMFrame:
    return SLMFrame(
        data=data,
        width=int(data.shape[1]),
        height=int(data.shape[0]),
        gray_level_count=SLM_10BIT_GRAY_LEVEL_COUNT,
)


def _as_float32_2d_array(values: object, *, context_name: str) -> np.ndarray:
    if hasattr(values, "detach") and callable(values.detach):
        values = values.detach().cpu().numpy()

    array = np.asarray(values)
    if np.iscomplexobj(array):
        message = "%s data must be real-valued" % context_name
        raise ValueError(message)
    if array.ndim == 3 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 2:
        message = "%s data must be a two-dimensional array" % context_name
        raise ValueError(message)
    if array.size == 0:
        message = "%s data must not be empty" % context_name
        raise ValueError(message)

    float_array = array.astype(np.float32, copy=False)
    if not np.all(np.isfinite(float_array)):
        message = "%s data must contain only finite values" % context_name
        raise ValueError(message)
    return float_array


def _quantize_unit_array_to_ten_bit(values: np.ndarray) -> np.ndarray:
    quantized = np.floor(
        values * SLM_10BIT_MAX_VALUE + 0.5 + _QUANTIZATION_EPSILON
    )
    quantized = np.clip(quantized, 0.0, float(SLM_10BIT_MAX_VALUE))
    return np.ascontiguousarray(quantized.astype(np.uint16))


__all__ = [
    "intensity_to_slm_frame",
    "phase_to_slm_frame",
]

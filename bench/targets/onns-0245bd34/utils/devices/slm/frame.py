from __future__ import annotations

import ctypes
from dataclasses import dataclass

import numpy as np


SLM_10BIT_GRAY_LEVEL_COUNT = 1024
SLM_10BIT_MAX_VALUE = SLM_10BIT_GRAY_LEVEL_COUNT - 1


@dataclass(frozen=True)
class SLMFrame:
    """
    空间光调制器帧

    参数:
        data:             范围为 0..1023 的二维 uint16 数据
        width:            帧宽度，单位为像素
        height:           帧高度，单位为像素
        gray_level_count: 硬件灰度级数
    """

    data: np.ndarray
    width: int
    height: int
    gray_level_count: int = SLM_10BIT_GRAY_LEVEL_COUNT


def slm_frame_to_ctypes_buffer(frame: SLMFrame) -> ctypes.Array:
    """
    帧数据转行优先缓冲区

    参数:
        frame: 准备好的 10bit SLM 帧

    返回:
        可传入 display_integer_data 的 c_ushort 数组

    抛出:
        ValueError: 帧不是有效 10bit 硬件帧时抛出
    """
    data_array = np.asarray(frame.data)
    _validate_slm_frame(frame, data_array)

    contiguous_data = np.ascontiguousarray(data_array, dtype=np.uint16)
    buffer_type = ctypes.c_ushort * int(contiguous_data.size)
    return buffer_type.from_buffer_copy(contiguous_data)


def _validate_slm_frame(frame: SLMFrame, data_array: np.ndarray) -> None:
    if data_array.ndim != 2:
        message = "SLMFrame data must be a two-dimensional array"
        raise ValueError(message)
    if data_array.dtype != np.uint16:
        message = "SLMFrame data must use uint16 dtype"
        raise ValueError(message)
    if data_array.size == 0:
        message = "SLMFrame data must not be empty"
        raise ValueError(message)
    if frame.width != int(data_array.shape[1]):
        message = "SLMFrame width must match data shape"
        raise ValueError(message)
    if frame.height != int(data_array.shape[0]):
        message = "SLMFrame height must match data shape"
        raise ValueError(message)
    if frame.gray_level_count != SLM_10BIT_GRAY_LEVEL_COUNT:
        message = "SLMFrame only supports 1024 gray levels"
        raise ValueError(message)
    if data_array.max() > SLM_10BIT_MAX_VALUE:
        message = "SLMFrame data must be in range 0..1023"
        raise ValueError(message)


__all__ = [
    "SLMFrame",
    "slm_frame_to_ctypes_buffer",
]

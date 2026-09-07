from __future__ import annotations

import ctypes
from dataclasses import dataclass

import numpy as np

from ._bindings import ASI_IMG_RAW8


@dataclass(frozen=True)
class CameraFrame:
    """
    相机帧数据

    参数:
        data:       二维图像数据
        width:      帧宽度，单位为像素
        height:     帧高度，单位为像素
        image_type: ZWO ASI 图像类型
    """

    data: np.ndarray
    width: int
    height: int
    image_type: int = ASI_IMG_RAW8


def raw8_buffer_to_camera_frame(
    buffer: ctypes.Array,
    *,
    width: int,
    height: int,
) -> CameraFrame:
    """
    缓冲区转相机帧

    参数:
        buffer: ASIGetVideoData 返回的 RAW8 字节缓冲区
        width:  帧宽度，单位为像素
        height: 帧高度，单位为像素

    返回:
        包含 uint8 行优先数据的 CameraFrame

    抛出:
        ValueError: 尺寸或缓冲区大小无效时抛出
    """
    _validate_dimensions(width=width, height=height)
    expected_size = int(width) * int(height)
    if len(buffer) != expected_size:
        message = "RAW8 buffer size must match width * height"
        raise ValueError(message)

    flat_data = np.ctypeslib.as_array(buffer, shape=(expected_size,))
    data = np.array(flat_data, dtype=np.uint8, copy=True).reshape((height, width))
    return CameraFrame(
        data=data,
        width=int(width),
        height=int(height),
        image_type=ASI_IMG_RAW8,
    )


def camera_frame_to_ctypes_buffer(frame: CameraFrame) -> ctypes.Array:
    """
    相机帧转缓冲区

    参数:
        frame: RAW8 相机帧

    返回:
        包含行优先帧数据的 c_ubyte 数组

    抛出:
        ValueError: 帧不是有效 RAW8 帧时抛出
    """
    data_array = np.asarray(frame.data)
    _validate_raw8_frame(frame, data_array)

    contiguous_data = np.ascontiguousarray(data_array, dtype=np.uint8)
    buffer_type = ctypes.c_ubyte * int(contiguous_data.size)
    return buffer_type.from_buffer_copy(contiguous_data)


def _validate_dimensions(
    *,
    width: int,
    height: int,
) -> None:
    if int(width) <= 0:
        message = "width must be positive"
        raise ValueError(message)
    if int(height) <= 0:
        message = "height must be positive"
        raise ValueError(message)


def _validate_raw8_frame(
    frame: CameraFrame,
    data_array: np.ndarray,
) -> None:
    if frame.image_type != ASI_IMG_RAW8:
        message = "CameraFrame helper only supports RAW8 data"
        raise ValueError(message)
    if data_array.ndim != 2:
        message = "CameraFrame data must be a two-dimensional array"
        raise ValueError(message)
    if data_array.dtype != np.uint8:
        message = "RAW8 CameraFrame data must use uint8 dtype"
        raise ValueError(message)
    if data_array.size == 0:
        message = "CameraFrame data must not be empty"
        raise ValueError(message)
    if frame.width != int(data_array.shape[1]):
        message = "CameraFrame width must match data shape"
        raise ValueError(message)
    if frame.height != int(data_array.shape[0]):
        message = "CameraFrame height must match data shape"
        raise ValueError(message)


__all__ = [
    "CameraFrame",
    "camera_frame_to_ctypes_buffer",
    "raw8_buffer_to_camera_frame",
]

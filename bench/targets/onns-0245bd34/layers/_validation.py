from __future__ import annotations

import math
from numbers import Integral, Real

import torch


def _format_invalid_value(name: str, expected: str, actual: object) -> str:
    return f"{name}应为{expected}，实际为{actual}"


def _format_supported_values(name: str, supported: object, actual: object) -> str:
    return f"{name}应为{supported}之一，实际为: {actual}"


def _validate_finite_real_scalar(name: str, value: object, expected: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(_format_invalid_value(name, expected, value))
    normalized_value = float(value)
    if not math.isfinite(normalized_value):
        raise ValueError(_format_invalid_value(name, expected, value))
    return normalized_value


def validate_positive_scalar(name: str, value: object) -> None:
    """
    校验正有限实数

    Args:
        name:  待校验标量名称
        value: 待校验标量值

    Raises:
        ValueError: 标量不是正有限实数
    """
    expected = "正数且有限实数"
    normalized_value = _validate_finite_real_scalar(name, value, expected)
    if normalized_value <= 0:
        raise ValueError(_format_invalid_value(name, expected, value))


def validate_nonzero_scalar(name: str, value: object) -> None:
    """
    校验非零有限实数

    Args:
        name:  待校验标量名称
        value: 待校验标量值

    Raises:
        ValueError: 标量不是非零有限实数
    """
    expected = "非零且有限实数"
    normalized_value = _validate_finite_real_scalar(name, value, expected)
    if normalized_value == 0:
        raise ValueError(_format_invalid_value(name, expected, value))


def validate_bool(name: str, value: object) -> None:
    """
    校验布尔参数

    Args:
        name:  待校验参数名称
        value: 待校验参数值

    Raises:
        ValueError: 参数值不是布尔类型
    """
    if not isinstance(value, bool):
        raise ValueError(
            _format_invalid_value(name, "布尔值", value)
        )


def normalize_array_resolution(array_resolution: tuple[int, int]) -> tuple[int, int]:
    """
    规范化阵列分辨率

    Args:
        array_resolution: 待校验阵列分辨率

    Returns:
        规范化后的高度与宽度整数元组

    Raises:
        ValueError: 阵列分辨率格式或取值无效
    """
    try:
        height, width = array_resolution
    except (TypeError, ValueError):
        raise ValueError(
            _format_invalid_value("阵列分辨率", "长度为2的元组", array_resolution)
        ) from None
    if isinstance(height, bool) or isinstance(width, bool):
        raise ValueError(
            _format_invalid_value("阵列分辨率各维度", "非布尔值", array_resolution)
        )
    if not isinstance(height, Integral) or not isinstance(width, Integral):
        raise ValueError(
            _format_invalid_value("阵列分辨率各维度", "整数", array_resolution)
        )
    if height <= 0 or width <= 0:
        raise ValueError(
            _format_invalid_value("阵列分辨率各维度", "正整数", array_resolution)
        )
    return int(height), int(width)


def validate_complex_input_field(
    input_field: torch.Tensor,
    *,
    height: int,
    width: int,
) -> None:
    """
    校验复数光场张量

    Args:
        input_field: 待校验输入光场
        height:      期望输入高度
        width:       期望输入宽度

    Raises:
        ValueError: 输入光场形状、类型或分辨率不符合要求
    """
    if input_field.dim() != 4 or input_field.shape[1] != 1:
        raise ValueError(
            "输入光场应为[batch_size, 1, height, width]，"
            f"实际为: {list(input_field.shape)}"
        )
    if not torch.is_complex(input_field):
        raise ValueError(
            _format_invalid_value("输入光场", "复数张量", input_field.dtype)
        )
    if input_field.dtype != torch.complex64:
        raise ValueError(
            "input_field dtype must be torch.complex64, "
            f"收到: {input_field.dtype}"
        )
    if input_field.shape[-2:] != (height, width):
        raise ValueError(
            f"输入光场分辨率应为({height}, {width})，"
            f"实际为: ({input_field.shape[-2]}, {input_field.shape[-1]})"
        )


def validate_same_device(
    input_field: torch.Tensor,
    reference_tensor: torch.Tensor,
    layer_name: str,
) -> None:
    """
    校验输入光场与 layer 状态位于同一设备

    Args:
        input_field:      待校验输入光场
        reference_tensor: 代表 layer 设备的参数或缓冲张量
        layer_name:       错误消息中的 layer 名称

    Raises:
        ValueError: 输入光场与 layer 状态不在同一设备
    """
    if input_field.device != reference_tensor.device:
        raise ValueError(
            f"输入光场与{layer_name}不在同一设备上，"
            f"输入设备为: {input_field.device}，"
            f"layer 设备为: {reference_tensor.device}"
        )


def force_real_single_precision(tensor: torch.Tensor) -> torch.Tensor:
    """
    将 layer 的实数状态锁定为 torch.float32

    Args:
        tensor: 待恢复精度的参数或缓冲张量

    Returns:
        单精度实数状态，或未改变的非浮点张量
    """
    if torch.is_complex(tensor):
        return tensor.real.to(dtype=torch.float32)
    if tensor.is_floating_point():
        return tensor.to(dtype=torch.float32)
    return tensor

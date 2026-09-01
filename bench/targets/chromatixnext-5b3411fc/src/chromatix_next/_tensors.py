from __future__ import annotations

import math

import torch

import chromatix_next.errors as _errors

_REAL_DTYPE: torch.dtype = torch.float64

_COMPLEX_DTYPE: torch.dtype = torch.complex128



def is_value_readable(value: torch.Tensor) -> bool:
    """
    判断张量的取值是否可读，meta 设备上的张量只有形状而无取值

    """
    return not value.is_meta


def is_finite_fixed_double_scalar(value: object) -> bool:
    """
    判断实数或零维 float64 实张量是否合格并有限，取值不可读时只查结构/dtype

    """
    if isinstance(value, torch.Tensor):
        if value.dim() != 0 or value.dtype is not torch.float64:
            return False
        if value.is_meta:
            return True
        return bool(torch.isfinite(value))
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def is_finite_fixed_double_scalar_in_closed_interval(
    value: object,
    *,
    lower_bound: float,
    upper_bound: float,
) -> bool:
    """
    判断合格有限 fixed-double 标量是否位于含双端点的闭区间

    meta 张量只有结构与 dtype；其不可读取的区间取值留到真实执行边界复核。

    """

    if not is_finite_fixed_double_scalar(value):
        return False
    if isinstance(value, torch.Tensor):
        if not is_value_readable(value):
            return True
        return bool((value >= lower_bound) & (value <= upper_bound))
    assert isinstance(value, (int, float))
    return lower_bound <= float(value) <= upper_bound


def _materialize_finite_fixed_double_three_vector(
    value: object,
) -> torch.Tensor | None:
    if isinstance(value, torch.Tensor):
        if value.shape != (3,) or value.dtype is not torch.float64:
            return None
        if value.is_meta:
            return value
        if not bool(torch.isfinite(value).all()):
            return None
        return value
    if (
        not isinstance(value, tuple)
        or len(value) != 3
        or any(
            isinstance(component, bool)
            or not isinstance(component, (int, float))
            or not math.isfinite(float(component))
            for component in value
        )
    ):
        return None
    return torch.tensor(
        tuple(float(component) for component in value),
        dtype=_REAL_DTYPE,
    )


def is_nonzero_finite_fixed_double_scalar(value: object) -> bool:
    """
    判断对象是否为非零合格的 float64 实标量；张量仅在取值可读时查零

    """

    if not is_finite_fixed_double_scalar(value):
        return False
    if isinstance(value, torch.Tensor):
        is_zero = value == 0.0
        return not is_value_readable(is_zero) or not bool(is_zero)
    return value != 0.0


def register_fixed_double_real_scalar(
    module: torch.nn.Module,
    *,
    name: str,
    value: float | torch.Tensor,
) -> None:
    """
    以原身份注册合格 float64 标量：Parameter 入 register_parameter，
    非 Parameter float64 张量入 register_buffer，Python 实数物化为 CPU float64 Buffer

    """
    assert is_finite_fixed_double_scalar(value)
    if isinstance(value, torch.nn.Parameter):
        module.register_parameter(name, value)
        return
    if isinstance(value, torch.Tensor):
        module.register_buffer(name, value)
        return
    module.register_buffer(name, torch.tensor(value, dtype=_REAL_DTYPE))


def _validate_fixed_double_real_scalar(
    *,
    value: object,
    is_positive: bool,
    error_identity: str,
    tensor_message: str,
    scalar_message: str,
) -> None:
    if isinstance(value, torch.Tensor):
        is_structure_invalid = (
            value.dim() != 0 or value.dtype is not torch.float64
        )
        is_value_invalid = False
        if not is_structure_invalid:
            is_finite = torch.isfinite(value)
            if is_value_readable(is_finite):
                is_value_invalid = not bool(is_finite)
                if is_positive and not is_value_invalid:
                    is_value_invalid = not bool(value > 0.0)
        if is_structure_invalid or is_value_invalid:
            explanation = tensor_message.format(value=value)
            raise _errors.OpticalValueError(error_identity, explanation)
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or (is_positive and float(value) <= 0.0)
    ):
        explanation = scalar_message.format(value=value)
        raise _errors.OpticalValueError(error_identity, explanation)


def _register_fixed_double_scalar_parameter_or_buffer(
    module: torch.nn.Module,
    *,
    name: str,
    value: float | torch.nn.Parameter,
    is_positive: bool,
    error_identity: str,
    tensor_message: str,
    scalar_message: str,
    non_parameter_tensor_message: str = "",
) -> None:
    _validate_fixed_double_real_scalar(
        value=value,
        is_positive=is_positive,
        error_identity=error_identity,
        tensor_message=tensor_message,
        scalar_message=scalar_message,
    )
    if isinstance(value, torch.nn.Parameter):
        module.register_parameter(name, value)
        return
    if isinstance(value, torch.Tensor):
        if non_parameter_tensor_message:
            message = non_parameter_tensor_message.format(value=value)
        else:
            message = (
                f"{name} 作为张量提供时必须是 torch.nn.Parameter；"
                f"若不需要训练请传 Python 标量，收到的是 {value!r}"
            )
        raise _errors.OpticalTypeError(error_identity, message)
    module.register_buffer(name, torch.tensor(float(value), dtype=_REAL_DTYPE))


def cache_identity(value: float | torch.Tensor) -> object:
    """
    返回不读取张量物理取值的可哈希缓存标识

    """
    if isinstance(value, torch.Tensor):
        # 可训练或不可读的值不形成可复用缓存键；一次性身份强制派生缓存重算
        if value.requires_grad or not is_value_readable(value):
            return object()
        return (
            id(value),
            value._version,
            tuple(value.shape),
            value.dtype,
            value.device,
        )
    return value

from __future__ import annotations

from dataclasses import dataclass
import math

import torch

from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

from .._orthonormal_basis import (
    _require_authored_orthonormal_basis,
    _require_authored_unit_three_vector,
)


@dataclass(frozen=True)
class _TerminalFrame:
    """
    一次性派生的 Terminal 空间原点、半方向与横向基

    Attributes:
        origin: Terminal 的全局空间原点
        incident_direction: 指向 owner 内部的入射单位半方向
        incident_horizontal: 入射横向基的水平单位轴
        incident_vertical: 入射横向基的竖直单位轴
        outgoing_direction: 指向 owner 外部的出射单位半方向
        outgoing_horizontal: 出射横向基的水平单位轴
        outgoing_vertical: 出射横向基的竖直单位轴

    """

    origin: torch.Tensor
    incident_direction: torch.Tensor
    incident_horizontal: torch.Tensor
    incident_vertical: torch.Tensor
    outgoing_direction: torch.Tensor
    outgoing_horizontal: torch.Tensor
    outgoing_vertical: torch.Tensor


def _prepare_fixed_geometry_vector(
    value: object,
    *,
    owner_label: str,
    field_name: str,
    identity_prefix: str,
) -> torch.Tensor:
    if isinstance(value, torch.nn.Parameter) or (
        isinstance(value, torch.Tensor) and value.requires_grad
    ):
        raise _errors.OpticalTypeError(
            f"{identity_prefix}_type_invalid",
            f"{owner_label} 的 {field_name} 是固定几何，不接受 Parameter 或 "
            "requires_grad=True 的 Tensor；请传有限 float64 Tensor 或三个有限"
            "实数的元组，"
            f"收到的是 {type(value).__name__}",
        )
    if isinstance(value, torch.Tensor):
        if value.dtype is not torch.float64:
            raise _errors.OpticalTypeError(
                f"{identity_prefix}_dtype_invalid",
                f"{owner_label} 的 {field_name} 必须是 float64，"
                f"收到的 dtype 是 {value.dtype}；请以 fixed-double 重建该几何向量",
            )
        if value.shape != (3,):
            raise _errors.OpticalValueError(
                f"{identity_prefix}_shape_invalid",
                f"{owner_label} 的 {field_name} 必须是形状 (3,) 的三向量，"
                f"收到的形状是 {tuple(value.shape)}；请提供恰好三个笛卡尔分量",
            )
        if is_value_readable(value) and not bool(torch.isfinite(value).all()):
            raise _errors.OpticalValueError(
                f"{identity_prefix}_nonfinite",
                f"{owner_label} 的 {field_name} 每个分量都必须有限，"
                f"收到的是 {value!r}；请移除 NaN 或 Inf",
            )
        return value
    if not isinstance(value, tuple) or len(value) != 3 or any(
        isinstance(component, bool) or not isinstance(component, (int, float))
        for component in value
    ):
        raise _errors.OpticalTypeError(
            f"{identity_prefix}_type_invalid",
            f"{owner_label} 的 {field_name} 必须是 float64 Tensor 或三个实数的元组，"
            f"收到的是 {type(value).__name__}；请按固定三向量形式提供",
        )
    try:
        materialized = tuple(float(component) for component in value)
    except OverflowError as error:
        raise _errors.OpticalValueError(
            f"{identity_prefix}_nonfinite",
            f"{owner_label} 的 {field_name} 每个分量都必须能表示为有限 float64；"
            f"收到的是 {value!r}；请缩小非有限分量",
        ) from error
    if not all(math.isfinite(component) for component in materialized):
        raise _errors.OpticalValueError(
            f"{identity_prefix}_nonfinite",
            f"{owner_label} 的 {field_name} 每个分量都必须有限，"
            f"收到的是 {value!r}；请移除 NaN 或 Inf",
        )
    return torch.tensor(materialized, dtype=torch.float64)


def _require_fixed_unit_vector(
    value: torch.Tensor,
    *,
    owner_label: str,
    field_name: str,
    error_identity: str,
) -> None:
    _require_authored_unit_three_vector(
        value,
        error_identity=error_identity,
        message=(
            f"{owner_label} 的 {field_name} 必须是 fixed-double 准入预算内的"
            f"单位向量，收到的是 {value!r}；请在 authoring 前归一化该固定轴"
        ),
    )


def _require_fixed_orthogonal_axes(
    first: torch.Tensor,
    second: torch.Tensor,
    *,
    owner_label: str,
    first_name: str,
    second_name: str,
    error_identity: str,
) -> None:
    if not is_value_readable(first) or not is_value_readable(second):
        return
    if first.device != second.device:
        raise _errors.OpticalValueError(
            error_identity,
            f"{owner_label} 的 {first_name} 与 {second_name} 必须先位于同一设备才能"
            "形成固定正交几何；请在构造 owner 前对齐设备",
        )
    _require_authored_orthonormal_basis(
        first,
        second,
        not_orthogonal_identity=error_identity,
        not_orthogonal_message=(
            f"{owner_label} 的 {first_name} 与 {second_name} 必须正交，"
            f"收到的是 {first!r} 与 {second!r}；请提供固定正交轴"
        ),
    )


def _derive_terminal_frame(
    *,
    origin: torch.Tensor,
    outward_direction: torch.Tensor,
    vertical_direction: torch.Tensor,
) -> _TerminalFrame:
    incident_direction = -outward_direction
    incident_horizontal = torch.linalg.cross(
        vertical_direction,
        incident_direction,
    )
    outgoing_direction = outward_direction.clone()
    outgoing_horizontal = torch.linalg.cross(
        vertical_direction,
        outgoing_direction,
    )
    return _TerminalFrame(
        origin=origin.clone(),
        incident_direction=incident_direction,
        incident_horizontal=incident_horizontal,
        incident_vertical=vertical_direction.clone(),
        outgoing_direction=outgoing_direction,
        outgoing_horizontal=outgoing_horizontal,
        outgoing_vertical=vertical_direction.clone(),
    )

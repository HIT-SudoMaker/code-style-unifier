from __future__ import annotations

import math
from typing import Literal

import torch

from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

from .._orthonormal_basis import (
    _materialize_authored_three_vector,
    _require_authored_orthonormal_basis,
    _require_authored_unit_three_vector,
)

_SURFACE_THREE_VECTOR_TENSOR_REQUIREMENT = (
    "必须是长度为 3 的有限 float64 实张量"
)
_SURFACE_THREE_VECTOR_TUPLE_REQUIREMENT = "必须是三个有限实数构成的元组"

def _require_unit_vector(
    value: torch.Tensor,
    *,
    field_name: str,
    error_identity: str,
) -> None:
    _require_authored_unit_three_vector(
        value,
        error_identity=error_identity,
        message=(
            f"{field_name} 必须是单位向量，面不会静默归一化 authored 物理，"
            f"收到的是 {value!r}"
        ),
    )


def _require_surface_orthonormal_basis(
    tangent_x: torch.Tensor,
    tangent_y: torch.Tensor,
    *,
    not_orthogonal_identity: str,
) -> None:
    _require_authored_orthonormal_basis(
        tangent_x,
        tangent_y,
        not_orthogonal_identity=not_orthogonal_identity,
        not_orthogonal_message=(
            "面的两个基向量必须正交，面不会静默旋转 authored 姿态，"
            f"收到的纵向基是 {tangent_x!r}，横向基是 {tangent_y!r}"
        ),
    )


def _register_surface_pose(
    module: torch.nn.Module,
    *,
    surface_name: Literal["plane", "sphere", "conic"],
    origin: object,
    tangent_x: object,
    tangent_y: object,
) -> None:
    # 三种 Surface 只在域名与中文说明上不同；机械生命周期在这里保持同一顺序
    if surface_name == "plane":
        surface_label = "平面"
        pose_name = "origin"
        pose_label = "平面原点"
    elif surface_name == "sphere":
        surface_label = "球面"
        pose_name = "vertex"
        pose_label = "球面顶点"
    else:
        surface_label = "圆锥面"
        pose_name = "vertex"
        pose_label = "圆锥面顶点"

    materialized_tangent_x = _materialize_authored_three_vector(
        tangent_x,
        field_name=f"{surface_label}tangent_x",
        error_identity=f"{surface_name}_tangent_x_invalid",
        tensor_requirement=_SURFACE_THREE_VECTOR_TENSOR_REQUIREMENT,
        tuple_requirement=_SURFACE_THREE_VECTOR_TUPLE_REQUIREMENT,
    )
    materialized_tangent_y = _materialize_authored_three_vector(
        tangent_y,
        field_name=f"{surface_label}tangent_y",
        error_identity=f"{surface_name}_tangent_y_invalid",
        tensor_requirement=_SURFACE_THREE_VECTOR_TENSOR_REQUIREMENT,
        tuple_requirement=_SURFACE_THREE_VECTOR_TUPLE_REQUIREMENT,
    )
    _require_unit_vector(
        materialized_tangent_x,
        field_name=f"{surface_label}tangent_x",
        error_identity=f"{surface_name}_tangent_x_not_unit",
    )
    _require_unit_vector(
        materialized_tangent_y,
        field_name=f"{surface_label}tangent_y",
        error_identity=f"{surface_name}_tangent_y_not_unit",
    )
    _require_surface_orthonormal_basis(
        materialized_tangent_x,
        materialized_tangent_y,
        not_orthogonal_identity=f"{surface_name}_basis_not_orthogonal",
    )
    materialized_origin = _materialize_authored_three_vector(
        origin,
        field_name=pose_label,
        error_identity=f"{surface_name}_{pose_name}_invalid",
        tensor_requirement=_SURFACE_THREE_VECTOR_TENSOR_REQUIREMENT,
        tuple_requirement=_SURFACE_THREE_VECTOR_TUPLE_REQUIREMENT,
    )
    if isinstance(materialized_origin, torch.nn.Parameter):
        module.register_parameter(pose_name, materialized_origin)
    else:
        module.register_buffer(pose_name, materialized_origin)
    module.register_buffer("tangent_x", materialized_tangent_x)
    module.register_buffer("tangent_y", materialized_tangent_y)


def _require_valid_surface_pose(
    *,
    surface_name: Literal["plane", "sphere", "conic"],
    origin: object,
    tangent_x: torch.Tensor,
    tangent_y: torch.Tensor,
) -> None:
    if surface_name == "plane":
        surface_label = "平面"
    elif surface_name == "sphere":
        surface_label = "球面"
    else:
        surface_label = "圆锥面"

    _require_unit_vector(
        tangent_x,
        field_name=f"{surface_label}tangent_x",
        error_identity=f"{surface_name}_tangent_x_not_unit",
    )
    _require_unit_vector(
        tangent_y,
        field_name=f"{surface_label}tangent_y",
        error_identity=f"{surface_name}_tangent_y_not_unit",
    )
    _require_surface_orthonormal_basis(
        tangent_x,
        tangent_y,
        not_orthogonal_identity=f"{surface_name}_basis_not_orthogonal",
    )
    _materialize_authored_three_vector(
        origin,
        field_name=(
            "平面原点" if surface_name == "plane" else f"{surface_name}顶点"
        ),
        error_identity=(
            f"{surface_name}_origin_invalid"
            if surface_name == "plane"
            else f"{surface_name}_vertex_invalid"
        ),
        tensor_requirement=_SURFACE_THREE_VECTOR_TENSOR_REQUIREMENT,
        tuple_requirement=_SURFACE_THREE_VECTOR_TUPLE_REQUIREMENT,
    )


def _require_positive_finite_scalar(
    value: object,
    *,
    field_name: str,
    error_identity: str,
) -> None:
    if isinstance(value, torch.Tensor):
        is_structure_invalid = (
            value.dim() != 0
            or torch.is_complex(value)
            or not value.is_floating_point()
        )
        is_value_invalid = False
        if not is_structure_invalid:
            is_finite = torch.isfinite(value)
            is_positive = value > 0
            if is_value_readable(is_finite):
                is_value_invalid = (
                    not bool(is_finite) or not bool(is_positive)
                )
        if is_structure_invalid or is_value_invalid:
            message = (
                f"{field_name} 必须是正的有限实数标量，"
                "不能是复数或多分量张量，"
                f"收到的是 {value!r}"
            )
            raise _errors.OpticalValueError(error_identity, message)
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0.0
    ):
        message = (
            f"{field_name} 必须是正的有限实数，零和负数没有物理意义，"
            f"收到的是 {value!r}"
        )
        raise _errors.OpticalValueError(error_identity, message)


def _register_hard_aperture(
    module: torch.nn.Module,
    *,
    name: str,
    value: object,
    owner_identity: str,
) -> None:
    if value is None:
        return
    if isinstance(value, torch.nn.Parameter):
        message = (
            f"{name} 是硬拓扑输入，不接受可训练 Parameter；"
            "若不需训练请传 Python float 或 fixed float64 Tensor"
        )
        raise _errors.OpticalTypeError(owner_identity, message)
    if isinstance(value, torch.Tensor):
        _require_positive_finite_scalar(
            value,
            field_name=name,
            error_identity=owner_identity,
        )
        if value.dtype is not torch.float64:
            message = (
                f"{name} 作为张量必须是 float64（fixed-double 硬拓扑输入），"
                f"收到的是 {value.dtype}"
            )
            raise _errors.OpticalTypeError(owner_identity, message)
        if value.requires_grad:
            message = (
                f"{name} 是硬拓扑输入，不接受 requires_grad=True 的张量"
            )
            raise _errors.OpticalTypeError(owner_identity, message)
        module.register_buffer(name, value.detach())
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        message = (
            f"{name} 必须是正的有限实数或 fixed float64 张量，收到的是 {value!r}"
        )
        raise _errors.OpticalTypeError(owner_identity, message)
    _require_positive_finite_scalar(
        value,
        field_name=name,
        error_identity=owner_identity,
    )
    module.register_buffer(
        name,
        torch.tensor(float(value), dtype=torch.float64),
    )

from __future__ import annotations

from collections.abc import Sequence
import math

import torch

import chromatix_next.errors as _errors


def _as_finite_real_scalar(
    value: object,
    *,
    field_name: str,
    error_identity: str,
) -> float:
    if isinstance(value, torch.Tensor):
        if (
            value.dim() != 0
            or torch.is_complex(value)
            or value.dtype is not torch.float64
            or value.requires_grad
        ):
            message = (
                f"近轴光线传递的 {field_name} 必须是零维 float64 实张量且 "
                f"requires_grad=False（独立解析参考），收到的是形状 "
                f"{tuple(value.shape)}、dtype {value.dtype}、"
                f"requires_grad={value.requires_grad}"
            )
            raise _errors.OpticalValueError(error_identity, message)
        if not value.is_meta and not bool(torch.isfinite(value)):
            message = (
                f"近轴光线传递的 {field_name} 必须处处有限，"
                f"收到的 dtype 是 {value.dtype}"
            )
            raise _errors.OpticalValueError(error_identity, message)
        return float(value)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        message = (
            f"近轴光线传递的 {field_name} 必须是有限实数标量，收到的是 {value!r}"
        )
        raise _errors.OpticalValueError(error_identity, message)
    return float(value)


def _matrix(
    rows: tuple[float, float, float, float],
    *,
    device: torch.device,
) -> torch.Tensor:
    # 按行优先的四元组构造 (2,2) float64 实张量（ADR-0005 固定双精度核）
    return torch.tensor(rows, dtype=torch.float64, device=device).reshape(2, 2)


def free_space_ray_transfer_matrix(
    distance: float | torch.Tensor,
    *,
    device: torch.device,
) -> torch.Tensor:
    """
    返回自由空间距离 ``distance`` 的近轴光线传递矩阵

    Args:
        distance: 沿光轴传播的有符号距离
        device: 承载固定双精度结果的 PyTorch 设备

    Returns:
        自由空间传播的 2×2 float64 近轴传递矩阵

    Raises:
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    axial = _as_finite_real_scalar(
        distance,
        field_name="distance",
        error_identity="paraxial_ray_transfer_free_space_distance_invalid",
    )
    return _matrix(
        (1.0, axial, 0.0, 1.0),
        device=device,
    )


def thin_lens_ray_transfer_matrix(
    focal_length: float | torch.Tensor,
    *,
    device: torch.device,
) -> torch.Tensor:
    """
    返回焦距 ``focal_length`` 的薄透镜近轴光线传递矩阵

    Args:
        focal_length: 薄透镜或聚焦模型的焦距
        device: 承载固定双精度结果的 PyTorch 设备

    Returns:
        薄透镜作用的 2×2 float64 近轴传递矩阵

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    focal = _as_finite_real_scalar(
        focal_length,
        field_name="focal_length",
        error_identity="paraxial_ray_transfer_thin_lens_focal_length_invalid",
    )
    if focal == 0.0:
        message_zero = (
            "薄透镜焦距不能为零，零焦距对应无穷光焦度的非物理薄透镜"
        )
        raise _errors.OpticalValueError(
            "paraxial_ray_transfer_thin_lens_focal_length_zero",
            message_zero,
        )
    return _matrix(
        (1.0, 0.0, -1.0 / focal, 1.0),
        device=device,
    )


def spherical_refraction_ray_transfer_matrix(
    curvature: float | torch.Tensor,
    incident_index: float | torch.Tensor,
    destination_index: float | torch.Tensor,
    *,
    device: torch.device,
) -> torch.Tensor:
    """
    返回球面折射（入射介质→目标介质，曲率 ``curvature``）的近轴光线传递矩阵

    Args:
        curvature: 以长度倒数表示的顶点曲率
        incident_index: 相互作用前介质的折射率
        destination_index: 相互作用后介质的折射率
        device: 承载固定双精度结果的 PyTorch 设备

    Returns:
        返回描述该近轴作用的固定双精度传递矩阵

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    c_value = _as_finite_real_scalar(
        curvature,
        field_name="curvature",
        error_identity="paraxial_ray_transfer_spherical_refraction_curvature_invalid",
    )
    n_i = _as_finite_real_scalar(
        incident_index,
        field_name="incident_index",
        error_identity=(
            "paraxial_ray_transfer_spherical_refraction_incident_index_invalid"
        ),
    )
    n_t = _as_finite_real_scalar(
        destination_index,
        field_name="destination_index",
        error_identity=(
            "paraxial_ray_transfer_spherical_refraction_destination_index_invalid"
        ),
    )
    if n_t <= 0.0:
        message_nonpositive = (
            "目标介质折射率必须为正，非物理介质不能作为折射目标"
        )
        raise _errors.OpticalValueError(
            "paraxial_ray_transfer_spherical_refraction_destination_index_nonpositive",
            message_nonpositive,
        )
    return _matrix(
        (
            1.0,
            0.0,
            -(n_t - n_i) * c_value / n_t,
            n_i / n_t,
        ),
        device=device,
    )


def compose_ray_transfer_matrices(
    matrices: Sequence[torch.Tensor],
) -> torch.Tensor:
    """
    按光线传播顺序链乘一组近轴光线传递矩阵并返回复合矩阵

    Args:
        matrices: 按光线行进顺序给出的传输矩阵

    Returns:
        返回描述组合近轴作用的固定双精度传递矩阵

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    if len(matrices) == 0:
        message_empty = (
            "compose_ray_transfer_matrices 至少需要一张近轴光线传递矩阵，"
            "空序列没有物理含义"
        )
        raise _errors.OpticalValueError(
            "paraxial_ray_transfer_compose_empty",
            message_empty,
        )
    composed: torch.Tensor | None = None
    for matrix in matrices:
        if (
            not isinstance(matrix, torch.Tensor)
            or matrix.shape != (2, 2)
            or torch.is_complex(matrix)
            or matrix.dtype is not torch.float64
            or matrix.requires_grad
        ):
            message_shape = (
                "compose_ray_transfer_matrices 的每一项必须是 (2,2) float64 实张量且 "
                "requires_grad=False（独立解析参考），近轴光线传递链只能复合非可训练"
                "的固定双精度实矩阵"
            )
            raise _errors.OpticalValueError(
                "paraxial_ray_transfer_compose_matrix_invalid",
                message_shape,
            )
        composed = matrix if composed is None else matrix @ composed
    assert composed is not None
    return composed


__all__ = [
    "compose_ray_transfer_matrices",
    "free_space_ray_transfer_matrix",
    "spherical_refraction_ray_transfer_matrix",
    "thin_lens_ray_transfer_matrix",
]

from __future__ import annotations

import math

import torch

from .complex_phase import _unit_phasor_from_cycles


def quadratic_phase_factor(
    *,
    position_y: torch.Tensor,
    position_x: torch.Tensor,
    phase_curvature: torch.Tensor,
    center_y: float | torch.Tensor = 0.0,
    center_x: float | torch.Tensor = 0.0,
) -> torch.Tensor:
    """
    返回可带前导批次维的可分离径向二次相位因子

    ``phase_curvature`` 保持 rad/m²（与公共 TransverseWavevector 的 rad/m 单位
    一致），由本所有者负责在送入唯一 phasor 前除以 ``2π`` 换算成周期。

    """

    radius_squared = (
        position_y[:, None] - center_y
    ).square() + (
        position_x[None, :] - center_x
    ).square()
    cycles = phase_curvature[..., None, None] * radius_squared / (2.0 * math.pi)
    return _unit_phasor_from_cycles(cycles)

def spatial_sample_positions(
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    reference: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    返回与参考张量同设备、同精度的纵向与横向样本位置

    """

    counts_y, counts_x = sample_counts
    spacing_y = signed_spacing[0].to(
        device=reference.device,
        dtype=reference.dtype,
    )
    spacing_x = signed_spacing[1].to(
        device=reference.device,
        dtype=reference.dtype,
    )
    origin_y = first_sample_position[0].to(
        device=reference.device,
        dtype=reference.dtype,
    )
    origin_x = first_sample_position[1].to(
        device=reference.device,
        dtype=reference.dtype,
    )
    position_y = (
        torch.arange(
            counts_y,
            device=reference.device,
            dtype=reference.dtype,
        )
        * spacing_y
        + origin_y
    )
    position_x = (
        torch.arange(
            counts_x,
            device=reference.device,
            dtype=reference.dtype,
        )
        * spacing_x
        + origin_x
    )
    return position_y, position_x


def isolated_destination_within_tripled_window(
    *,
    input_sample_counts: tuple[int, int],
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    input_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    output_sample_counts: tuple[int, int],
    output_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    reference: torch.Tensor,
) -> torch.Tensor:
    """
    判断目标采样足迹是否落在孤立外部的三倍零延拓计算窗口内

    """

    spacing_in_y = input_signed_spacing[0].to(
        dtype=reference.dtype,
        device=reference.device,
    )
    spacing_in_x = input_signed_spacing[1].to(
        dtype=reference.dtype,
        device=reference.device,
    )
    origin_in_y = input_first_sample_position[0].to(
        dtype=reference.dtype,
        device=reference.device,
    )
    origin_in_x = input_first_sample_position[1].to(
        dtype=reference.dtype,
        device=reference.device,
    )
    spacing_out_y = output_signed_spacing[0].to(
        dtype=reference.dtype,
        device=reference.device,
    )
    spacing_out_x = output_signed_spacing[1].to(
        dtype=reference.dtype,
        device=reference.device,
    )
    origin_out_y = output_first_sample_position[0].to(
        dtype=reference.dtype,
        device=reference.device,
    )
    origin_out_x = output_first_sample_position[1].to(
        dtype=reference.dtype,
        device=reference.device,
    )
    source_centre_y = origin_in_y + (
        input_sample_counts[0] - 1
    ) * spacing_in_y / 2.0
    source_centre_x = origin_in_x + (
        input_sample_counts[1] - 1
    ) * spacing_in_x / 2.0
    half_extent_y = (
        3 * input_sample_counts[0] * spacing_in_y.abs() / 2.0
    )
    half_extent_x = (
        3 * input_sample_counts[1] * spacing_in_x.abs() / 2.0
    )
    out_first_y = origin_out_y
    out_last_y = (
        origin_out_y
        + (output_sample_counts[0] - 1) * spacing_out_y
    )
    out_first_x = origin_out_x
    out_last_x = (
        origin_out_x
        + (output_sample_counts[1] - 1) * spacing_out_x
    )
    out_min_y = torch.minimum(out_first_y, out_last_y)
    out_max_y = torch.maximum(out_first_y, out_last_y)
    out_min_x = torch.minimum(out_first_x, out_last_x)
    out_max_x = torch.maximum(out_first_x, out_last_x)
    tolerance_y = (
        8.0
        * torch.finfo(reference.dtype).eps
        * (2.0 * half_extent_y)
    )
    tolerance_x = (
        8.0
        * torch.finfo(reference.dtype).eps
        * (2.0 * half_extent_x)
    )
    is_inside = (
        (out_min_y >= source_centre_y - half_extent_y - tolerance_y)
        & (out_max_y <= source_centre_y + half_extent_y + tolerance_y)
        & (out_min_x >= source_centre_x - half_extent_x - tolerance_x)
        & (out_max_x <= source_centre_x + half_extent_x + tolerance_x)
    ).detach()
    return is_inside

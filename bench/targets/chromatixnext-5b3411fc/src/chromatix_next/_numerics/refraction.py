from __future__ import annotations

from dataclasses import dataclass

import torch

from chromatix_next._numerics._certified_predicates import (
    scaled_squared_norm_difference_sign,
)


@dataclass(frozen=True, slots=True)
class RefractedRays:
    """
    折射 interact 的结构化结果（方向、逐 ray 折射率、覆写后的状态、成功折射掩码）

    """

    direction: torch.Tensor
    refractive_index: torch.Tensor
    status: torch.Tensor
    is_refracted: torch.Tensor


def refract_at_advance(
    *,
    ray_direction: torch.Tensor,
    incident_refractive_indices: torch.Tensor,
    destination_refractive_indices: torch.Tensor,
    unit_normal: torch.Tensor,
    is_interacted: torch.Tensor,
    base_status: torch.Tensor,
    total_internal_reflection_status_value: int,
) -> RefractedRays:
    """
    在共享推进给出的法线、interacted 掩码与基线状态上施加 Snell、TIR 与折射率切换

    """

    refractive_index_ratio = (
        incident_refractive_indices / destination_refractive_indices
    )
    cos_incident = -(ray_direction * unit_normal).sum(dim=-1)
    sin_squared_incident = 1.0 - cos_incident * cos_incident
    sin_squared_transmitted = (
        refractive_index_ratio
        * refractive_index_ratio
        * sin_squared_incident
    )
    sin_incident = torch.sqrt(
        torch.clamp(sin_squared_incident, min=0.0)
    )
    transmitted_challenger = (
        incident_refractive_indices * sin_incident
    ).unsqueeze(-1)
    total_internal_reflection_sign = scaled_squared_norm_difference_sign(
        destination_refractive_indices,
        transmitted_challenger,
    )
    is_total_internal_reflection = total_internal_reflection_sign < 0
    safe_sin_squared = torch.where(
        is_total_internal_reflection,
        torch.ones_like(sin_squared_transmitted),
        torch.clamp(
            sin_squared_transmitted,
            min=0.0,
            max=1.0,
        ),
    )
    cos_transmitted = torch.sqrt(1.0 - safe_sin_squared)
    refracted_direction = (
        refractive_index_ratio.unsqueeze(-1) * ray_direction
        + (
            refractive_index_ratio * cos_incident - cos_transmitted
        ).unsqueeze(-1)
        * unit_normal
    )
    is_refracted = is_interacted & ~is_total_internal_reflection
    next_direction = torch.where(
        is_refracted.unsqueeze(-1),
        refracted_direction,
        ray_direction,
    )
    next_refractive_index = torch.where(
        is_refracted,
        destination_refractive_indices,
        incident_refractive_indices,
    )
    tir_status = torch.full_like(
        base_status,
        total_internal_reflection_status_value,
    )
    is_tir_interacted = is_interacted & is_total_internal_reflection
    next_status = torch.where(is_tir_interacted, tir_status, base_status)
    return RefractedRays(
        direction=next_direction,
        refractive_index=next_refractive_index,
        status=next_status,
        is_refracted=is_refracted,
    )

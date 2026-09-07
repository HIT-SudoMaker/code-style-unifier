from __future__ import annotations

import torch

from chromatix_next._numerics._certified_predicates import (
    dot_sign,
    scaled_squared_norm_difference_sign,
)
from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter


def plane_encounter(
    *,
    ray_origin: torch.Tensor,
    ray_direction: torch.Tensor,
    plane_origin: torch.Tensor,
    plane_tangent_x: torch.Tensor,
    plane_tangent_y: torch.Tensor,
    clear_aperture_radius: torch.Tensor | None,
) -> SurfaceEncounter:
    """
    计算 RayBundle 与平面的交点

    """

    normal = torch.linalg.cross(plane_tangent_x, plane_tangent_y)
    offset = plane_origin - ray_origin
    numerator = (offset * normal).sum(dim=-1)
    denominator = (ray_direction * normal).sum(dim=-1)
    denominator_sign = dot_sign(ray_direction, normal)
    numerator_sign = dot_sign(offset, normal)
    is_parallel = denominator_sign == 0
    forward_sign = numerator_sign * denominator_sign
    is_forward = forward_sign >= 0
    is_encountered = (~is_parallel) & is_forward
    is_continuous_distance_resolvable = is_parallel | (denominator != 0)
    safe_denominator = torch.where(
        is_parallel | (~is_continuous_distance_resolvable),
        torch.ones_like(denominator),
        denominator,
    )
    ordinary_distance = numerator / safe_denominator
    distance = torch.where(
        is_continuous_distance_resolvable,
        ordinary_distance,
        torch.zeros_like(ordinary_distance),
    )
    intersection = ray_origin + distance.unsqueeze(-1) * ray_direction
    if clear_aperture_radius is None:
        is_inside_aperture = torch.ones_like(is_encountered)
    else:
        local_offset = intersection - plane_origin
        local_x = (local_offset * plane_tangent_x).sum(dim=-1)
        local_y = (local_offset * plane_tangent_y).sum(dim=-1)
        aperture_components = torch.stack((local_y, local_x), dim=-1)
        aperture_sign = scaled_squared_norm_difference_sign(
            clear_aperture_radius,
            aperture_components,
        )
        is_inside_aperture = aperture_sign >= 0
    is_inside_aperture = torch.where(
        is_continuous_distance_resolvable,
        is_inside_aperture,
        torch.ones_like(is_inside_aperture),
    )
    needs_flip = denominator_sign > 0
    # 派生法线按自身范数可微归一化而不触碰 authored 切向量状态
    normal_norm = torch.linalg.vector_norm(normal)
    unit_normal = torch.where(
        needs_flip.unsqueeze(-1),
        -normal / normal_norm,
        normal / normal_norm,
    )
    return SurfaceEncounter(
        distance=distance,
        intersection=intersection,
        unit_normal=unit_normal,
        is_encountered=is_encountered,
        is_inside_aperture=is_inside_aperture,
        is_continuous_distance_resolvable=(
            is_continuous_distance_resolvable
        ),
    )

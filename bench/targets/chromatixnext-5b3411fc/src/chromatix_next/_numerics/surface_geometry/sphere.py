from __future__ import annotations

import torch

from chromatix_next._numerics._certified_predicates import (
    dot_sign,
    quadratic_discriminant_sign,
    scaled_squared_norm_difference_sign,
)
from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter


def sphere_encounter(
    *,
    ray_origin: torch.Tensor,
    ray_direction: torch.Tensor,
    sphere_center: torch.Tensor,
    sphere_vertex: torch.Tensor,
    sphere_tangent_x: torch.Tensor,
    sphere_tangent_y: torch.Tensor,
    physical_radius: torch.Tensor,
    clear_aperture_radius: torch.Tensor | None,
) -> SurfaceEncounter:
    """
    计算 RayBundle 与球面的交点

    """

    offset = ray_origin - sphere_center
    midpoint_dot = (offset * ray_direction).sum(dim=-1)
    offset_squared = (offset * offset).sum(dim=-1)
    radius_squared = physical_radius * physical_radius
    discriminant_sign = quadratic_discriminant_sign(
        torch.ones_like(midpoint_dot),
        2.0 * midpoint_dot,
        offset_squared - radius_squared,
    )
    has_real_root = discriminant_sign >= 0
    inside_sign = scaled_squared_norm_difference_sign(physical_radius, offset)
    midpoint_sign = dot_sign(offset, ray_direction)
    # 光滑根（可微）：稳定 q-公式。约化判别式 D = md² − (‖offset‖² − R²)
    discriminant = midpoint_dot * midpoint_dot - (
        offset_squared - radius_squared
    )
    safe_discriminant = torch.where(
        has_real_root,
        torch.clamp(discriminant, min=0.0),
        torch.zeros_like(discriminant),
    )
    sqrt_discriminant = torch.sqrt(safe_discriminant)
    large_root = -(midpoint_dot + torch.copysign(sqrt_discriminant, midpoint_dot))
    safe_large_root = torch.where(
        large_root != 0.0,
        large_root,
        torch.ones_like(large_root),
    )
    small_root = (offset_squared - radius_squared) / safe_large_root
    near_root = torch.minimum(large_root, small_root)
    far_root = torch.maximum(large_root, small_root)
    is_inside = inside_sign > 0
    is_on_surface = inside_sign == 0
    is_outside_toward = (inside_sign < 0) & (midpoint_sign < 0)
    is_encountered = has_real_root & (
        is_inside | is_on_surface | is_outside_toward
    )
    chosen_distance = torch.where(
        is_on_surface,
        torch.zeros_like(near_root),
        torch.where(
            is_inside,
            far_root,
            torch.where(
                is_outside_toward,
                near_root,
                torch.zeros_like(near_root),
            ),
        ),
    )
    safe_distance = torch.where(
        is_encountered,
        chosen_distance,
        torch.zeros_like(chosen_distance),
    )
    intersection = ray_origin + safe_distance.unsqueeze(-1) * ray_direction
    surface_normal = intersection - sphere_center
    unit_normal = surface_normal / physical_radius
    cos_against_normal = (ray_direction * unit_normal).sum(dim=-1)
    needs_flip = cos_against_normal > 0
    oriented_normal = torch.where(
        needs_flip.unsqueeze(-1),
        -unit_normal,
        unit_normal,
    )
    if clear_aperture_radius is None:
        is_inside_aperture = torch.ones_like(is_encountered)
    else:
        local_offset = intersection - sphere_vertex
        local_x = (local_offset * sphere_tangent_x).sum(dim=-1)
        local_y = (local_offset * sphere_tangent_y).sum(dim=-1)
        aperture_components = torch.stack((local_y, local_x), dim=-1)
        aperture_sign = scaled_squared_norm_difference_sign(
            clear_aperture_radius,
            aperture_components,
        )
        is_inside_aperture = aperture_sign >= 0
    return SurfaceEncounter(
        distance=safe_distance,
        intersection=intersection,
        unit_normal=oriented_normal,
        is_encountered=is_encountered,
        is_inside_aperture=is_inside_aperture,
        is_continuous_distance_resolvable=torch.ones_like(is_encountered),
    )

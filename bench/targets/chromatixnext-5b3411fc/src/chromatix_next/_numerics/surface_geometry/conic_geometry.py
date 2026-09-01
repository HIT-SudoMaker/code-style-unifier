from __future__ import annotations

from dataclasses import dataclass

import torch

from chromatix_next._numerics._certified_predicates import (
    scaled_squared_norm_difference_sign,
)


@dataclass(frozen=True, slots=True)
class _ConicRayLocalGeometry:
    """
    承载光线在圆锥局部坐标中的几何分量

    """

    local_origin_x: torch.Tensor
    local_origin_y: torch.Tensor
    local_origin_z: torch.Tensor
    local_direction_x: torch.Tensor
    local_direction_y: torch.Tensor
    local_direction_z: torch.Tensor
    radial_origin_squared: torch.Tensor
    radial_origin_direction_dot: torch.Tensor
    transverse_direction_squared: torch.Tensor


@dataclass(frozen=True, slots=True)
class _ConicLocalPoint:
    """
    承载圆锥局部点及其径向平方

    """

    x: torch.Tensor
    y: torch.Tensor
    z: torch.Tensor
    radius_squared: torch.Tensor


def _conic_even_polynomial(
    *,
    radius_squared: torch.Tensor,
    even_coefficients: torch.Tensor,
) -> torch.Tensor:
    # 按 authored 偶次系数顺序计算 Σ a_i q^i；空系数返回同形零张量
    if even_coefficients.numel() == 0:
        return torch.zeros_like(radius_squared)
    powers = torch.arange(
        1,
        even_coefficients.numel() + 1,
        dtype=radius_squared.dtype,
        device=radius_squared.device,
    )
    bases = radius_squared.unsqueeze(-1) ** powers
    return (bases * even_coefficients).sum(dim=-1)


def _conic_even_polynomial_derivative(
    *,
    radius_squared: torch.Tensor,
    even_coefficients: torch.Tensor,
) -> torch.Tensor:
    # 按原有运算顺序计算 d/dq Σ a_i q^i
    if even_coefficients.numel() == 0:
        return torch.zeros_like(radius_squared)
    coefficients = even_coefficients * torch.arange(
        1,
        even_coefficients.numel() + 1,
        dtype=even_coefficients.dtype,
        device=even_coefficients.device,
    )
    powers = torch.arange(
        0,
        even_coefficients.numel(),
        dtype=radius_squared.dtype,
        device=radius_squared.device,
    )
    bases = radius_squared.unsqueeze(-1) ** powers
    return (bases * coefficients).sum(dim=-1)


def _derive_conic_ray_local_geometry(
    *,
    ray_origin: torch.Tensor,
    ray_direction: torch.Tensor,
    conic_vertex: torch.Tensor,
    conic_tangent_x: torch.Tensor,
    conic_tangent_y: torch.Tensor,
    normal: torch.Tensor,
) -> _ConicRayLocalGeometry:
    # 只改变事实的表达形式；全部投影与乘加顺序保持既有合同
    offset = ray_origin - conic_vertex
    local_origin_x = (offset * conic_tangent_x).sum(dim=-1)
    local_origin_y = (offset * conic_tangent_y).sum(dim=-1)
    local_origin_z = (offset * normal).sum(dim=-1)
    local_direction_x = (ray_direction * conic_tangent_x).sum(dim=-1)
    local_direction_y = (ray_direction * conic_tangent_y).sum(dim=-1)
    local_direction_z = (ray_direction * normal).sum(dim=-1)
    radial_origin_squared = (
        local_origin_x * local_origin_x + local_origin_y * local_origin_y
    )
    radial_origin_direction_dot = (
        local_origin_x * local_direction_x
        + local_origin_y * local_direction_y
    )
    transverse_direction_squared = (
        local_direction_x * local_direction_x
        + local_direction_y * local_direction_y
    )
    return _ConicRayLocalGeometry(
        local_origin_x=local_origin_x,
        local_origin_y=local_origin_y,
        local_origin_z=local_origin_z,
        local_direction_x=local_direction_x,
        local_direction_y=local_direction_y,
        local_direction_z=local_direction_z,
        radial_origin_squared=radial_origin_squared,
        radial_origin_direction_dot=radial_origin_direction_dot,
        transverse_direction_squared=transverse_direction_squared,
    )


def _conic_local_point_at_distance(
    *,
    geometry: _ConicRayLocalGeometry,
    distance: torch.Tensor,
) -> _ConicLocalPoint:
    x = geometry.local_origin_x + distance * geometry.local_direction_x
    y = geometry.local_origin_y + distance * geometry.local_direction_y
    z = geometry.local_origin_z + distance * geometry.local_direction_z
    radius_squared = x * x + y * y
    return _ConicLocalPoint(
        x=x,
        y=y,
        z=z,
        radius_squared=radius_squared,
    )


def _implicit_polynomial_value(
    *,
    geometry: _ConicRayLocalGeometry,
    distance: torch.Tensor,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
) -> torch.Tensor:
    point = _conic_local_point_at_distance(
        geometry=geometry,
        distance=distance,
    )
    even_value = _conic_even_polynomial(
        radius_squared=point.radius_squared,
        even_coefficients=even_coefficients,
    )
    sag_offset = point.z - even_value
    return (
        curvature * point.radius_squared
        - 2.0 * sag_offset
        + (1.0 + conic_constant) * curvature * sag_offset * sag_offset
    )


def _implicit_polynomial_derivative(
    *,
    geometry: _ConicRayLocalGeometry,
    distance: torch.Tensor,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
) -> torch.Tensor:
    point = _conic_local_point_at_distance(
        geometry=geometry,
        distance=distance,
    )
    even_value = _conic_even_polynomial(
        radius_squared=point.radius_squared,
        even_coefficients=even_coefficients,
    )
    even_derivative = _conic_even_polynomial_derivative(
        radius_squared=point.radius_squared,
        even_coefficients=even_coefficients,
    )
    sag_offset = point.z - even_value
    radial_derivative = 2.0 * (
        point.x * geometry.local_direction_x
        + point.y * geometry.local_direction_y
    )
    sag_offset_derivative = (
        geometry.local_direction_z - even_derivative * radial_derivative
    )
    implicit_sag_derivative = (
        -2.0
        + 2.0
        * (1.0 + conic_constant)
        * curvature
        * sag_offset
    )
    return (
        curvature * radial_derivative
        + sag_offset_derivative * implicit_sag_derivative
    )


def _implicit_gradient_local(
    *,
    point: _ConicLocalPoint,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    even_value = _conic_even_polynomial(
        radius_squared=point.radius_squared,
        even_coefficients=even_coefficients,
    )
    even_derivative = _conic_even_polynomial_derivative(
        radius_squared=point.radius_squared,
        even_coefficients=even_coefficients,
    )
    sag_offset = point.z - even_value
    implicit_sag_derivative = (
        -2.0
        + 2.0
        * (1.0 + conic_constant)
        * curvature
        * sag_offset
    )
    negative_implicit_sag_derivative = (
        2.0
        - 2.0
        * (1.0 + conic_constant)
        * curvature
        * sag_offset
    )
    transverse_scale = (
        curvature + even_derivative * negative_implicit_sag_derivative
    )
    gradient_x = 2.0 * point.x * transverse_scale
    gradient_y = 2.0 * point.y * transverse_scale
    gradient_z = implicit_sag_derivative
    return gradient_x, gradient_y, gradient_z


def _sheet_guard(
    *,
    geometry: _ConicRayLocalGeometry,
    distance: torch.Tensor,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
) -> torch.Tensor:
    point = _conic_local_point_at_distance(
        geometry=geometry,
        distance=distance,
    )
    even_value = _conic_even_polynomial(
        radius_squared=point.radius_squared,
        even_coefficients=even_coefficients,
    )
    sag_offset = point.z - even_value
    return 1.0 - (1.0 + conic_constant) * curvature * sag_offset


def _real_domain_radicand(
    *,
    geometry: _ConicRayLocalGeometry,
    distance: torch.Tensor,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
) -> torch.Tensor:
    point = _conic_local_point_at_distance(
        geometry=geometry,
        distance=distance,
    )
    return (
        1.0
        - (1.0 + conic_constant)
        * curvature
        * curvature
        * point.radius_squared
    )


def _oriented_unit_normal_from_gradient(
    *,
    gradient_x: torch.Tensor,
    gradient_y: torch.Tensor,
    gradient_z: torch.Tensor,
    conic_tangent_x: torch.Tensor,
    conic_tangent_y: torch.Tensor,
    normal: torch.Tensor,
    ray_direction: torch.Tensor,
) -> torch.Tensor:
    magnitude_squared = (
        gradient_x * gradient_x
        + gradient_y * gradient_y
        + gradient_z * gradient_z
    )
    magnitude = torch.sqrt(magnitude_squared)
    safe_magnitude = torch.where(
        magnitude > 0.0,
        magnitude,
        torch.ones_like(magnitude),
    )
    unit_x = gradient_x / safe_magnitude
    unit_y = gradient_y / safe_magnitude
    unit_z = gradient_z / safe_magnitude
    global_unit_normal = (
        unit_x.unsqueeze(-1) * conic_tangent_x
        + unit_y.unsqueeze(-1) * conic_tangent_y
        + unit_z.unsqueeze(-1) * normal
    )
    cosine_against_normal = (ray_direction * global_unit_normal).sum(dim=-1)
    should_flip = cosine_against_normal > 0
    return torch.where(
        should_flip.unsqueeze(-1),
        -global_unit_normal,
        global_unit_normal,
    )


def _is_inside_conic_aperture(
    *,
    clear_aperture_radius: torch.Tensor,
    local_x: torch.Tensor,
    local_y: torch.Tensor,
) -> torch.Tensor:
    components = torch.stack((local_x, local_y), dim=-1)
    sign = scaled_squared_norm_difference_sign(
        clear_aperture_radius,
        components,
    )
    return sign >= 0

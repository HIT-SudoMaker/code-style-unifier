from __future__ import annotations

import torch

from chromatix_next._numerics.surface_geometry.base_conic_roots import (
    select_base_conic_root,
)
from chromatix_next._numerics.surface_geometry.conic_geometry import (
    _conic_local_point_at_distance,
    _derive_conic_ray_local_geometry,
    _implicit_gradient_local,
    _is_inside_conic_aperture,
    _oriented_unit_normal_from_gradient,
)
from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter
from chromatix_next._numerics.surface_geometry.polynomial_conic_roots import (
    solve_polynomial_conic_root,
)
import chromatix_next.errors as _errors

_REFINEMENT_TOLERANCE = 1.0e-12


def conic_encounter(
    *,
    ray_origin: torch.Tensor,
    ray_direction: torch.Tensor,
    conic_vertex: torch.Tensor,
    conic_tangent_x: torch.Tensor,
    conic_tangent_y: torch.Tensor,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
    clear_aperture_radius: torch.Tensor | None,
) -> SurfaceEncounter:
    """
    计算 RayBundle 与圆锥曲面的交点

    """

    normal = torch.linalg.cross(conic_tangent_x, conic_tangent_y)
    geometry = _derive_conic_ray_local_geometry(
        ray_origin=ray_origin,
        ray_direction=ray_direction,
        conic_vertex=conic_vertex,
        conic_tangent_x=conic_tangent_x,
        conic_tangent_y=conic_tangent_y,
        normal=normal,
    )
    residual_tolerance = torch.tensor(
        _REFINEMENT_TOLERANCE,
        dtype=ray_origin.dtype,
        device=ray_origin.device,
    )
    has_even_asphere = even_coefficients.numel() > 0
    if has_even_asphere:
        assert clear_aperture_radius is not None
        polynomial_root = solve_polynomial_conic_root(
            geometry=geometry,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even_coefficients,
            clear_aperture_radius=clear_aperture_radius,
            residual_tolerance=residual_tolerance,
        )
        if not polynomial_root.distance.is_meta:
            if bool(polynomial_root.is_unprovable.any()):
                message = (
                    "圆锥偶次非球面多项式求交的存在性、唯一性或收敛性"
                    "不可在冻结资源预算内证明，这通常意味着病态参数、"
                    "切向入射或近重根；请检查 ConicEvenAsphere 参数"
                )
                raise _errors.OpticalValueError(
                    "conic_intersection_not_converged",
                    message,
                )
        selected_distance = polynomial_root.distance
        is_encountered = polynomial_root.is_encountered
    else:
        base_root = select_base_conic_root(
            geometry=geometry,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even_coefficients,
        )
        selected_distance = base_root.distance
        is_encountered = base_root.is_encountered
    safe_distance = torch.where(
        is_encountered,
        selected_distance,
        torch.zeros_like(selected_distance),
    )
    local_point = _conic_local_point_at_distance(
        geometry=geometry,
        distance=safe_distance,
    )
    gradient_x, gradient_y, gradient_z = _implicit_gradient_local(
        point=local_point,
        curvature=curvature,
        conic_constant=conic_constant,
        even_coefficients=even_coefficients,
    )
    unit_normal = _oriented_unit_normal_from_gradient(
        gradient_x=gradient_x,
        gradient_y=gradient_y,
        gradient_z=gradient_z,
        conic_tangent_x=conic_tangent_x,
        conic_tangent_y=conic_tangent_y,
        normal=normal,
        ray_direction=ray_direction,
    )
    intersection = (
        conic_vertex
        + local_point.x.unsqueeze(-1) * conic_tangent_x
        + local_point.y.unsqueeze(-1) * conic_tangent_y
        + local_point.z.unsqueeze(-1) * normal
    )
    if clear_aperture_radius is None:
        is_inside_aperture = torch.ones_like(is_encountered)
    else:
        is_inside_aperture = _is_inside_conic_aperture(
            clear_aperture_radius=clear_aperture_radius,
            local_x=local_point.x,
            local_y=local_point.y,
        )
    return SurfaceEncounter(
        distance=safe_distance,
        intersection=intersection,
        unit_normal=unit_normal,
        is_encountered=is_encountered,
        is_inside_aperture=is_inside_aperture,
        is_continuous_distance_resolvable=torch.ones_like(is_encountered),
    )

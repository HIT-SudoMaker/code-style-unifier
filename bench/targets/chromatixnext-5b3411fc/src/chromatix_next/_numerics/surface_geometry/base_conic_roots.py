from __future__ import annotations

from dataclasses import dataclass

import torch

from chromatix_next._numerics._certified_predicates import base_conic_discriminant_sign

from .conic_geometry import _ConicRayLocalGeometry, _real_domain_radicand, _sheet_guard


@dataclass(frozen=True, slots=True)
class _BaseConicEquation:
    """
    承载基础圆锥求交方程及其判别式事实

    """

    quadratic_coefficient: torch.Tensor
    linear_coefficient: torch.Tensor
    constant_coefficient: torch.Tensor
    discriminant_sign: torch.Tensor


@dataclass(frozen=True, slots=True)
class _BaseConicRootSelection:
    """
    承载基础圆锥最近合法根的选择结果

    """

    distance: torch.Tensor
    is_encountered: torch.Tensor


@dataclass(frozen=True, slots=True)
class _OutwardInterval:
    """
    承载基础圆锥根认证算术的外扩二进制区间

    """

    lower: torch.Tensor
    upper: torch.Tensor


def _point_interval(value: torch.Tensor) -> _OutwardInterval:
    return _OutwardInterval(lower=value, upper=value)


def _interval_add(
    first: _OutwardInterval,
    second: _OutwardInterval,
) -> _OutwardInterval:
    negative_infinity = torch.full_like(first.lower + second.lower, -torch.inf)
    positive_infinity = torch.full_like(first.upper + second.upper, torch.inf)
    return _OutwardInterval(
        lower=torch.nextafter(
            first.lower + second.lower,
            negative_infinity,
        ),
        upper=torch.nextafter(
            first.upper + second.upper,
            positive_infinity,
        ),
    )


def _interval_negate(interval: _OutwardInterval) -> _OutwardInterval:
    return _OutwardInterval(
        lower=-interval.upper,
        upper=-interval.lower,
    )


def _interval_multiply(
    first: _OutwardInterval,
    second: _OutwardInterval,
) -> _OutwardInterval:
    products = torch.stack(
        (
            first.lower * second.lower,
            first.lower * second.upper,
            first.upper * second.lower,
            first.upper * second.upper,
        ),
        dim=0,
    )
    has_undefined_product = torch.isnan(products).any(dim=0)
    rounded_lower = products.amin(dim=0)
    rounded_upper = products.amax(dim=0)
    negative_infinity = torch.full_like(rounded_lower, -torch.inf)
    positive_infinity = torch.full_like(rounded_upper, torch.inf)
    return _OutwardInterval(
        lower=torch.where(
            has_undefined_product,
            negative_infinity,
            torch.nextafter(rounded_lower, negative_infinity),
        ),
        upper=torch.where(
            has_undefined_product,
            positive_infinity,
            torch.nextafter(rounded_upper, positive_infinity),
        ),
    )


def _base_conic_discriminant_interval(
    *,
    geometry: _ConicRayLocalGeometry,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
) -> _OutwardInterval:
    origin_x = _point_interval(geometry.local_origin_x)
    origin_y = _point_interval(geometry.local_origin_y)
    origin_z = _point_interval(geometry.local_origin_z)
    direction_x = _point_interval(geometry.local_direction_x)
    direction_y = _point_interval(geometry.local_direction_y)
    direction_z = _point_interval(geometry.local_direction_z)
    curvature_interval = _point_interval(curvature)
    conic_constant_interval = _point_interval(conic_constant)
    one = _point_interval(torch.ones_like(conic_constant))
    two = _point_interval(torch.full_like(conic_constant, 2.0))
    four = _point_interval(torch.full_like(conic_constant, 4.0))
    one_plus_conic_constant = _interval_add(one, conic_constant_interval)

    transverse_direction_squared = _interval_add(
        _interval_multiply(direction_x, direction_x),
        _interval_multiply(direction_y, direction_y),
    )
    direction_z_squared = _interval_multiply(direction_z, direction_z)
    quadratic_coefficient = _interval_multiply(
        curvature_interval,
        _interval_add(
            transverse_direction_squared,
            _interval_multiply(
                one_plus_conic_constant,
                direction_z_squared,
            ),
        ),
    )

    radial_origin_direction_dot = _interval_add(
        _interval_multiply(origin_x, direction_x),
        _interval_multiply(origin_y, direction_y),
    )
    linear_coefficient = _interval_add(
        _interval_add(
            _interval_multiply(
                two,
                _interval_multiply(
                    curvature_interval,
                    radial_origin_direction_dot,
                ),
            ),
            _interval_negate(_interval_multiply(two, direction_z)),
        ),
        _interval_multiply(
            two,
            _interval_multiply(
                _interval_multiply(
                    one_plus_conic_constant,
                    curvature_interval,
                ),
                _interval_multiply(origin_z, direction_z),
            ),
        ),
    )

    radial_origin_squared = _interval_add(
        _interval_multiply(origin_x, origin_x),
        _interval_multiply(origin_y, origin_y),
    )
    constant_coefficient = _interval_add(
        _interval_add(
            _interval_multiply(curvature_interval, radial_origin_squared),
            _interval_negate(_interval_multiply(two, origin_z)),
        ),
        _interval_multiply(
            _interval_multiply(
                one_plus_conic_constant,
                curvature_interval,
            ),
            _interval_multiply(origin_z, origin_z),
        ),
    )
    return _interval_add(
        _interval_multiply(linear_coefficient, linear_coefficient),
        _interval_negate(
            _interval_multiply(
                four,
                _interval_multiply(
                    quadratic_coefficient,
                    constant_coefficient,
                ),
            ),
        ),
    )


def _base_conic_discriminant_sign(
    *,
    geometry: _ConicRayLocalGeometry,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
) -> torch.Tensor:
    if geometry.local_origin_x.is_meta:
        return base_conic_discriminant_sign(
            geometry.local_origin_x,
            geometry.local_origin_y,
            geometry.local_origin_z,
            geometry.local_direction_x,
            geometry.local_direction_y,
            geometry.local_direction_z,
            curvature,
            conic_constant,
        )
    interval = _base_conic_discriminant_interval(
        geometry=geometry,
        curvature=curvature,
        conic_constant=conic_constant,
    )
    is_positive = interval.lower > 0.0
    is_negative = interval.upper < 0.0
    needs_exact_sign = ~(is_positive | is_negative)
    interval_sign = torch.where(
        is_positive,
        torch.ones_like(interval.lower, dtype=torch.int8),
        -torch.ones_like(interval.lower, dtype=torch.int8),
    )
    if not bool(needs_exact_sign.any()):
        return interval_sign
    exact_sign = base_conic_discriminant_sign(
        geometry.local_origin_x,
        geometry.local_origin_y,
        geometry.local_origin_z,
        geometry.local_direction_x,
        geometry.local_direction_y,
        geometry.local_direction_z,
        curvature,
        conic_constant,
    )
    return torch.where(needs_exact_sign, exact_sign, interval_sign)


def _derive_base_conic_equation(
    *,
    geometry: _ConicRayLocalGeometry,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
) -> _BaseConicEquation:
    one_plus_conic_constant = 1.0 + conic_constant
    local_direction_z = geometry.local_direction_z
    quadratic_coefficient = curvature * (
        geometry.transverse_direction_squared
        + one_plus_conic_constant
        * local_direction_z
        * local_direction_z
    )
    linear_coefficient = (
        2.0 * curvature * geometry.radial_origin_direction_dot
        - 2.0 * geometry.local_direction_z
        + 2.0
        * one_plus_conic_constant
        * curvature
        * geometry.local_origin_z
        * geometry.local_direction_z
    )
    constant_coefficient = (
        curvature * geometry.radial_origin_squared
        - 2.0 * geometry.local_origin_z
        + one_plus_conic_constant
        * curvature
        * geometry.local_origin_z
        * geometry.local_origin_z
    )
    discriminant_sign = _base_conic_discriminant_sign(
        geometry=geometry,
        curvature=curvature,
        conic_constant=conic_constant,
    )
    return _BaseConicEquation(
        quadratic_coefficient=quadratic_coefficient,
        linear_coefficient=linear_coefficient,
        constant_coefficient=constant_coefficient,
        discriminant_sign=discriminant_sign,
    )


def _stable_quadratic_roots(
    *,
    equation: _BaseConicEquation,
    has_real_root: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    quadratic = equation.quadratic_coefficient
    linear = equation.linear_coefficient
    constant = equation.constant_coefficient
    discriminant = linear * linear - 4.0 * quadratic * constant
    tiny = torch.finfo(discriminant.dtype).tiny
    safe_discriminant = torch.where(
        has_real_root,
        torch.clamp(discriminant, min=tiny),
        torch.ones_like(discriminant),
    )
    square_root_discriminant = torch.sqrt(safe_discriminant)
    stable_factor = -0.5 * (
        linear + torch.copysign(square_root_discriminant, linear)
    )
    safe_stable_factor = torch.where(
        stable_factor != 0.0,
        stable_factor,
        torch.ones_like(stable_factor),
    )
    safe_quadratic = torch.where(
        quadratic != 0.0,
        quadratic,
        torch.ones_like(quadratic),
    )
    root_by_quadratic = stable_factor / safe_quadratic
    root_by_factor = constant / safe_stable_factor
    near = torch.minimum(root_by_quadratic, root_by_factor)
    far = torch.maximum(root_by_quadratic, root_by_factor)
    safe_linear = torch.where(
        linear != 0.0,
        linear,
        torch.ones_like(linear),
    )
    linear_root = -constant / safe_linear
    is_linear = (quadratic == 0.0) & (linear != 0.0)
    near = torch.where(is_linear, linear_root, near)
    far = torch.where(is_linear, linear_root, far)
    zero = torch.zeros_like(near)
    near = torch.where(has_real_root, near, zero)
    far = torch.where(has_real_root, far, zero)
    return near, far


def _select_nearest_nonnegative(
    *,
    candidates: tuple[torch.Tensor, ...],
    valid_masks: tuple[torch.Tensor, ...],
    reference: torch.Tensor,
) -> _BaseConicRootSelection:
    infinity = torch.full_like(reference, float("inf"))
    selected = infinity
    is_encountered = torch.zeros_like(reference, dtype=torch.bool)
    for candidate, is_valid in zip(candidates, valid_masks):
        is_finite_candidate = torch.isfinite(candidate)
        is_selectable = is_valid & is_finite_candidate
        is_encountered = is_encountered | is_selectable
        is_nearer = is_selectable & (candidate < selected)
        selected = torch.where(is_nearer, candidate, selected)
    return _BaseConicRootSelection(
        distance=selected,
        is_encountered=is_encountered,
    )


def select_base_conic_root(
    *,
    geometry: _ConicRayLocalGeometry,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
) -> _BaseConicRootSelection:
    """
    选择 base-Conic 的最近前向物理根

    """

    equation = _derive_base_conic_equation(
        geometry=geometry,
        curvature=curvature,
        conic_constant=conic_constant,
    )
    has_real_root = equation.discriminant_sign >= 0
    near, far = _stable_quadratic_roots(
        equation=equation,
        has_real_root=has_real_root,
    )
    plane_branch = curvature == 0.0
    local_direction_z = geometry.local_direction_z
    safe_local_direction_z = torch.where(
        local_direction_z != 0.0,
        local_direction_z,
        torch.ones_like(local_direction_z),
    )
    plane_distance = -geometry.local_origin_z / safe_local_direction_z
    plane_valid = plane_branch & (local_direction_z != 0.0)
    candidates = (near, far, plane_distance)
    valid_masks: list[torch.Tensor] = []
    for candidate in candidates:
        sheet = _sheet_guard(
            geometry=geometry,
            distance=candidate,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even_coefficients,
        )
        radicand = _real_domain_radicand(
            geometry=geometry,
            distance=candidate,
            curvature=curvature,
            conic_constant=conic_constant,
        )
        is_forward = candidate >= 0.0
        is_on_authored_sheet = sheet >= 0.0
        is_in_real_domain = radicand >= 0.0
        if candidate is plane_distance:
            is_valid_root = plane_valid & is_forward
        else:
            is_valid_root = (
                has_real_root
                & (~plane_branch)
                & is_forward
                & is_on_authored_sheet
                & is_in_real_domain
            )
        valid_masks.append(is_valid_root)
    return _select_nearest_nonnegative(
        candidates=candidates,
        valid_masks=tuple(valid_masks),
        reference=near,
    )

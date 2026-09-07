from __future__ import annotations

from dataclasses import dataclass
import math

import torch

from chromatix_next._numerics._certified_predicates import quotient_sign
from chromatix_next._numerics.surface_geometry.conic_geometry import (
    _ConicRayLocalGeometry,
    _implicit_polynomial_derivative,
    _implicit_polynomial_value,
)
from chromatix_next._numerics.surface_geometry.conic_root_proof import (
    MAX_POLYNOMIAL_DEGREE,
    isolate_real_roots,
    polynomial_degree,
)
from chromatix_next._tensors import is_value_readable

FAST_INTERVAL_SUBDIVISIONS: int = 32
REFINEMENT_NEWTON_STEPS: int = 64
_INTERVAL_OPERATION_BUDGET: int = 256


@dataclass(frozen=True, slots=True)
class _PolynomialConicRootSelection:
    """
    承载多项式圆锥根选择与不可证明状态

    """

    distance: torch.Tensor
    is_encountered: torch.Tensor
    is_unprovable: torch.Tensor


@dataclass(frozen=True, slots=True)
class _StagedCertifiedIntervals:
    """
    承载送往宿主证明侧车的认证区间

    """

    lower_bounds: tuple[float, ...]
    upper_bounds: tuple[float, ...]
    has_certified_interval: tuple[bool, ...]
    is_unprovable: tuple[bool, ...]


def _unit_roundoff(dtype: torch.dtype) -> float:
    return torch.finfo(dtype).eps / 2.0


def _rounding_error_factor(operation_count: int, dtype: torch.dtype) -> float:
    unit_roundoff = _unit_roundoff(dtype)
    accumulated_roundoff = operation_count * unit_roundoff
    return accumulated_roundoff / (1.0 - accumulated_roundoff)


def _safeguarded_refine(
    *,
    geometry: _ConicRayLocalGeometry,
    initial_distance: torch.Tensor,
    interval_lower: torch.Tensor,
    interval_upper: torch.Tensor,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
    residual_tolerance: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    current_distance = initial_distance.clone()
    current_lower_bound = interval_lower
    current_upper_bound = interval_upper
    converged = torch.zeros_like(current_distance, dtype=torch.bool)
    for _ in range(REFINEMENT_NEWTON_STEPS):
        value = _implicit_polynomial_value(
            geometry=geometry,
            distance=current_distance,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even_coefficients,
        )
        derivative = _implicit_polynomial_derivative(
            geometry=geometry,
            distance=current_distance,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even_coefficients,
        )
        residual_small = torch.abs(value) <= residual_tolerance
        deriv_magnitude = torch.abs(derivative)
        usable_derivative = torch.where(
            deriv_magnitude > residual_tolerance,
            derivative,
            torch.ones_like(derivative),
        )
        newton_step = value / usable_derivative
        newton_distance = current_distance - newton_step
        is_inside_interval = (
            newton_distance >= current_lower_bound
        ) & (
            newton_distance <= current_upper_bound
        )
        interval_midpoint = 0.5 * (
            current_lower_bound + current_upper_bound
        )
        candidate_distance = torch.where(
            is_inside_interval,
            newton_distance,
            interval_midpoint,
        )
        value_candidate = _implicit_polynomial_value(
            geometry=geometry,
            distance=candidate_distance,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even_coefficients,
        )
        value_lo = _implicit_polynomial_value(
            geometry=geometry,
            distance=current_lower_bound,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even_coefficients,
        )
        product_sign = quotient_sign(value_candidate, value_lo)
        root_in_lower = product_sign < 0
        updated_upper_bound = torch.where(
            root_in_lower,
            candidate_distance,
            current_upper_bound,
        )
        updated_lower_bound = torch.where(
            root_in_lower,
            current_lower_bound,
            candidate_distance,
        )
        # 步长判据：|Δt| 小于容差
        delta_small = (
            torch.abs(candidate_distance - current_distance)
            <= residual_tolerance
        )
        step_converged = residual_small & delta_small
        converged = step_converged
        current_lower_bound = updated_lower_bound
        current_upper_bound = updated_upper_bound
        current_distance = candidate_distance
        if not current_distance.is_meta:
            if bool(step_converged.all()):
                break
    return current_distance, converged


def _search_interval(
    *,
    geometry: _ConicRayLocalGeometry,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
    clear_aperture_radius: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    aperture_radius_squared = clear_aperture_radius * clear_aperture_radius
    cylinder_constant = geometry.radial_origin_squared - aperture_radius_squared
    transverse_direction_squared = geometry.transverse_direction_squared
    radial_origin_direction_dot = geometry.radial_origin_direction_dot
    cylinder_discriminant = (
        radial_origin_direction_dot * radial_origin_direction_dot
        - transverse_direction_squared * cylinder_constant
    )
    cylinder_has = cylinder_discriminant >= 0.0
    safe_cylinder_disc = torch.where(
        cylinder_has,
        torch.clamp(cylinder_discriminant, min=0.0),
        torch.zeros_like(cylinder_discriminant),
    )
    cylinder_discriminant_root = torch.sqrt(safe_cylinder_disc)
    safe_transverse_direction_squared = torch.where(
        transverse_direction_squared != 0.0,
        transverse_direction_squared,
        torch.ones_like(transverse_direction_squared),
    )
    cylinder_lower = torch.where(
        cylinder_has & (transverse_direction_squared > 0.0),
        (-radial_origin_direction_dot - cylinder_discriminant_root)
        / safe_transverse_direction_squared,
        torch.full_like(radial_origin_direction_dot, float("-inf")),
    )
    cylinder_upper = torch.where(
        cylinder_has & (transverse_direction_squared > 0.0),
        (-radial_origin_direction_dot + cylinder_discriminant_root)
        / safe_transverse_direction_squared,
        torch.full_like(radial_origin_direction_dot, float("inf")),
    )
    axial_branch = transverse_direction_squared == 0.0
    safe_radial_origin_direction_dot = torch.where(
        radial_origin_direction_dot != 0.0,
        radial_origin_direction_dot,
        torch.ones_like(radial_origin_direction_dot),
    )
    axial_t_at_radius = torch.where(
        radial_origin_direction_dot != 0.0,
        (aperture_radius_squared - geometry.radial_origin_squared)
        / (2.0 * safe_radial_origin_direction_dot),
        torch.zeros_like(radial_origin_direction_dot),
    )
    cylinder_lower = torch.where(
        axial_branch & (radial_origin_direction_dot > 0.0),
        torch.zeros_like(radial_origin_direction_dot),
        cylinder_lower,
    )
    cylinder_upper = torch.where(
        axial_branch & (radial_origin_direction_dot > 0.0),
        axial_t_at_radius,
        cylinder_upper,
    )
    cylinder_lower = torch.where(
        axial_branch & (radial_origin_direction_dot < 0.0),
        axial_t_at_radius,
        cylinder_lower,
    )
    cylinder_upper = torch.where(
        axial_branch & (radial_origin_direction_dot < 0.0),
        torch.zeros_like(radial_origin_direction_dot),
        cylinder_upper,
    )
    if even_coefficients.numel() > 0:
        powers = torch.arange(
            1,
            even_coefficients.numel() + 1,
            dtype=even_coefficients.dtype,
            device=even_coefficients.device,
        )
        poly_bound = (
            (
                even_coefficients.abs()
                * aperture_radius_squared.unsqueeze(-1) ** powers
            ).sum(dim=-1)
        )
    else:
        poly_bound = torch.zeros_like(aperture_radius_squared)
    sag_bound = curvature.abs() * aperture_radius_squared + poly_bound
    local_origin_z = geometry.local_origin_z
    local_direction_z = geometry.local_direction_z
    safe_local_direction_z = torch.where(
        local_direction_z != 0.0,
        local_direction_z,
        torch.ones_like(local_direction_z),
    )
    unsorted_sag_lower = (
        -sag_bound - local_origin_z
    ) / safe_local_direction_z
    unsorted_sag_upper = (
        sag_bound - local_origin_z
    ) / safe_local_direction_z
    sag_lower = torch.minimum(unsorted_sag_lower, unsorted_sag_upper)
    sag_upper = torch.maximum(unsorted_sag_lower, unsorted_sag_upper)
    sag_lower = torch.where(
        local_direction_z != 0.0,
        sag_lower,
        torch.full_like(sag_lower, float("-inf")),
    )
    sag_upper = torch.where(
        local_direction_z != 0.0,
        sag_upper,
        torch.full_like(sag_upper, float("inf")),
    )
    lower = torch.maximum(cylinder_lower, sag_lower)
    upper = torch.minimum(cylinder_upper, sag_upper)
    empty = lower > upper
    lower = torch.where(empty, torch.zeros_like(lower), lower)
    upper = torch.where(empty, torch.zeros_like(upper), upper)
    return lower, upper


def _interval_widen_outward(
    lower_bound: torch.Tensor,
    upper_bound: torch.Tensor,
    rounding_error_factor: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    magnitude = torch.maximum(lower_bound.abs(), upper_bound.abs())
    return (
        lower_bound - rounding_error_factor * magnitude,
        upper_bound + rounding_error_factor * magnitude,
    )


def _budgeted_interval_add(
    first_lower_bound: torch.Tensor,
    first_upper_bound: torch.Tensor,
    second_lower_bound: torch.Tensor,
    second_upper_bound: torch.Tensor,
    rounding_error_factor: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    return _interval_widen_outward(
        first_lower_bound + second_lower_bound,
        first_upper_bound + second_upper_bound,
        rounding_error_factor,
    )


def _interval_subtract(
    minuend_lower_bound: torch.Tensor,
    minuend_upper_bound: torch.Tensor,
    subtrahend_lower_bound: torch.Tensor,
    subtrahend_upper_bound: torch.Tensor,
    rounding_error_factor: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    return _interval_widen_outward(
        minuend_lower_bound - subtrahend_upper_bound,
        minuend_upper_bound - subtrahend_lower_bound,
        rounding_error_factor,
    )


def _budgeted_interval_multiply(
    first_lower_bound: torch.Tensor,
    first_upper_bound: torch.Tensor,
    second_lower_bound: torch.Tensor,
    second_upper_bound: torch.Tensor,
    rounding_error_factor: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    lower_lower_product = first_lower_bound * second_lower_bound
    lower_upper_product = first_lower_bound * second_upper_bound
    upper_lower_product = first_upper_bound * second_lower_bound
    upper_upper_product = first_upper_bound * second_upper_bound
    product_lower_bound = torch.minimum(
        torch.minimum(lower_lower_product, lower_upper_product),
        torch.minimum(upper_lower_product, upper_upper_product),
    )
    product_upper_bound = torch.maximum(
        torch.maximum(lower_lower_product, lower_upper_product),
        torch.maximum(upper_lower_product, upper_upper_product),
    )
    return _interval_widen_outward(
        product_lower_bound,
        product_upper_bound,
        rounding_error_factor,
    )


def _interval_scale(
    scalar: torch.Tensor | float,
    lower_bound: torch.Tensor,
    upper_bound: torch.Tensor,
    rounding_error_factor: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    scaled_lower_bound = scalar * lower_bound
    scaled_upper_bound = scalar * upper_bound
    return _interval_widen_outward(
        torch.minimum(scaled_lower_bound, scaled_upper_bound),
        torch.maximum(scaled_lower_bound, scaled_upper_bound),
        rounding_error_factor,
    )


def _interval_square(
    lower_bound: torch.Tensor,
    upper_bound: torch.Tensor,
    rounding_error_factor: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    lower_squared = lower_bound * lower_bound
    upper_squared = upper_bound * upper_bound
    squared_upper_bound = torch.maximum(lower_squared, upper_squared)
    crosses_zero = (lower_bound < 0) & (upper_bound > 0)
    lower_endpoint = torch.minimum(lower_squared, upper_squared)
    squared_lower_bound = torch.where(
        crosses_zero,
        torch.zeros_like(squared_upper_bound),
        lower_endpoint,
    )
    return _interval_widen_outward(
        squared_lower_bound,
        squared_upper_bound,
        rounding_error_factor,
    )


def _implicit_residual_bounds_for_subinterval(
    *,
    geometry: _ConicRayLocalGeometry,
    subinterval_lower_bound: torch.Tensor,
    subinterval_upper_bound: torch.Tensor,
    curvature: torch.Tensor,
    conic_quadratic_scale: torch.Tensor,
    even_coefficients: torch.Tensor,
    rounding_error_factor: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    # 按局部坐标、径向平方、偶次垂度、隐式残差的物理顺序构造一个子区间包络
    local_x_lower, local_x_upper = _interval_widen_outward(
        torch.minimum(
            geometry.local_origin_x
            + subinterval_lower_bound * geometry.local_direction_x,
            geometry.local_origin_x
            + subinterval_upper_bound * geometry.local_direction_x,
        ),
        torch.maximum(
            geometry.local_origin_x
            + subinterval_lower_bound * geometry.local_direction_x,
            geometry.local_origin_x
            + subinterval_upper_bound * geometry.local_direction_x,
        ),
        rounding_error_factor,
    )
    local_y_lower, local_y_upper = _interval_widen_outward(
        torch.minimum(
            geometry.local_origin_y
            + subinterval_lower_bound * geometry.local_direction_y,
            geometry.local_origin_y
            + subinterval_upper_bound * geometry.local_direction_y,
        ),
        torch.maximum(
            geometry.local_origin_y
            + subinterval_lower_bound * geometry.local_direction_y,
            geometry.local_origin_y
            + subinterval_upper_bound * geometry.local_direction_y,
        ),
        rounding_error_factor,
    )
    local_z_lower, local_z_upper = _interval_widen_outward(
        torch.minimum(
            geometry.local_origin_z
            + subinterval_lower_bound * geometry.local_direction_z,
            geometry.local_origin_z
            + subinterval_upper_bound * geometry.local_direction_z,
        ),
        torch.maximum(
            geometry.local_origin_z
            + subinterval_lower_bound * geometry.local_direction_z,
            geometry.local_origin_z
            + subinterval_upper_bound * geometry.local_direction_z,
        ),
        rounding_error_factor,
    )
    local_x_squared_lower, local_x_squared_upper = _interval_square(
        local_x_lower,
        local_x_upper,
        rounding_error_factor,
    )
    local_y_squared_lower, local_y_squared_upper = _interval_square(
        local_y_lower,
        local_y_upper,
        rounding_error_factor,
    )
    radius_squared_lower, radius_squared_upper = _budgeted_interval_add(
        local_x_squared_lower,
        local_x_squared_upper,
        local_y_squared_lower,
        local_y_squared_upper,
        rounding_error_factor,
    )
    even_sag_lower = torch.zeros_like(radius_squared_lower)
    even_sag_upper = torch.zeros_like(radius_squared_upper)
    radius_power_lower = torch.ones_like(radius_squared_lower)
    radius_power_upper = torch.ones_like(radius_squared_upper)
    for coefficient in even_coefficients:
        radius_power_lower, radius_power_upper = _budgeted_interval_multiply(
            radius_power_lower,
            radius_power_upper,
            radius_squared_lower,
            radius_squared_upper,
            rounding_error_factor,
        )
        even_sag_term_lower, even_sag_term_upper = _interval_scale(
            coefficient,
            radius_power_lower,
            radius_power_upper,
            rounding_error_factor,
        )
        even_sag_lower, even_sag_upper = _budgeted_interval_add(
            even_sag_lower,
            even_sag_upper,
            even_sag_term_lower,
            even_sag_term_upper,
            rounding_error_factor,
        )
    sag_residual_lower, sag_residual_upper = _interval_subtract(
        local_z_lower,
        local_z_upper,
        even_sag_lower,
        even_sag_upper,
        rounding_error_factor,
    )
    sag_residual_squared_lower, sag_residual_squared_upper = _interval_square(
        sag_residual_lower,
        sag_residual_upper,
        rounding_error_factor,
    )
    radial_curvature_lower, radial_curvature_upper = _interval_scale(
        curvature,
        radius_squared_lower,
        radius_squared_upper,
        rounding_error_factor,
    )
    linear_sag_lower, linear_sag_upper = _interval_scale(
        -2.0,
        sag_residual_lower,
        sag_residual_upper,
        rounding_error_factor,
    )
    quadratic_sag_lower, quadratic_sag_upper = _interval_scale(
        conic_quadratic_scale,
        sag_residual_squared_lower,
        sag_residual_squared_upper,
        rounding_error_factor,
    )
    residual_lower, residual_upper = _budgeted_interval_add(
        radial_curvature_lower,
        radial_curvature_upper,
        linear_sag_lower,
        linear_sag_upper,
        rounding_error_factor,
    )
    return _budgeted_interval_add(
        residual_lower,
        residual_upper,
        quadratic_sag_lower,
        quadratic_sag_upper,
        rounding_error_factor,
    )


def _fast_interval_exclusion(
    *,
    geometry: _ConicRayLocalGeometry,
    search_lower: torch.Tensor,
    search_upper: torch.Tensor,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
) -> torch.Tensor:
    with torch.no_grad():
        if search_lower.is_meta:
            return torch.zeros_like(search_lower, dtype=torch.bool)
        dtype = search_lower.dtype
        interval_rounding_error_factor = _rounding_error_factor(
            _INTERVAL_OPERATION_BUDGET,
            dtype,
        )
        proved_root_free = torch.ones_like(search_lower, dtype=torch.bool)
        search_width = search_upper - search_lower
        has_positive_search_width = search_width > 0.0
        one_plus_conic_constant = 1.0 + conic_constant
        conic_quadratic_scale = one_plus_conic_constant * curvature
        for index in range(FAST_INTERVAL_SUBDIVISIONS):
            subinterval_lower_bound = (
                search_lower
                + index * search_width / FAST_INTERVAL_SUBDIVISIONS
            )
            subinterval_upper_bound = (
                search_lower
                + (index + 1) * search_width / FAST_INTERVAL_SUBDIVISIONS
            )
            residual_lower_bound, residual_upper_bound = (
                _implicit_residual_bounds_for_subinterval(
                    geometry=geometry,
                    subinterval_lower_bound=subinterval_lower_bound,
                    subinterval_upper_bound=subinterval_upper_bound,
                    curvature=curvature,
                    conic_quadratic_scale=conic_quadratic_scale,
                    even_coefficients=even_coefficients,
                    rounding_error_factor=interval_rounding_error_factor,
                )
            )
            excludes_zero = (residual_lower_bound > 0) | (
                residual_upper_bound < 0
            )
            proved_root_free = proved_root_free & (
                excludes_zero | (~has_positive_search_width)
            )
        return proved_root_free & has_positive_search_width


def solve_polynomial_conic_root(
    *,
    geometry: _ConicRayLocalGeometry,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
    clear_aperture_radius: torch.Tensor,
    residual_tolerance: torch.Tensor,
) -> _PolynomialConicRootSelection:
    """
    按设备排除、宿主认证、设备精化的顺序选择 polynomial-Conic 根

    """
    reference = geometry.local_origin_x
    if reference.is_meta:
        selected_distance = torch.zeros_like(reference)
        is_encountered = torch.zeros_like(reference, dtype=torch.bool)
        is_unprovable = torch.zeros_like(reference, dtype=torch.bool)
        return _PolynomialConicRootSelection(
            distance=selected_distance,
            is_encountered=is_encountered,
            is_unprovable=is_unprovable,
        )
    search_lower, search_upper = _search_interval(
        geometry=geometry,
        curvature=curvature,
        conic_constant=conic_constant,
        even_coefficients=even_coefficients,
        clear_aperture_radius=clear_aperture_radius,
    )
    proved_root_free = _fast_interval_exclusion(
        geometry=geometry,
        search_lower=search_lower,
        search_upper=search_upper,
        curvature=curvature,
        conic_constant=conic_constant,
        even_coefficients=even_coefficients,
    )
    requires_host_certification = (
        (~proved_root_free) & is_value_readable(search_lower)
    )
    selected_distance = torch.zeros_like(search_lower)
    is_encountered = torch.zeros_like(search_lower, dtype=torch.bool)
    is_unprovable = torch.zeros_like(search_lower, dtype=torch.bool)
    if search_lower.is_meta or not bool(requires_host_certification.any()):
        return _PolynomialConicRootSelection(
            distance=selected_distance,
            is_encountered=is_encountered,
            is_unprovable=is_unprovable,
        )
    certified_intervals = _stage_unresolved_lanes_to_host(
        geometry=geometry,
        curvature=curvature,
        conic_constant=conic_constant,
        even_coefficients=even_coefficients,
        clear_aperture_radius=clear_aperture_radius,
        search_lower=search_lower,
        search_upper=search_upper,
        needs_host=requires_host_certification,
    )
    device = search_lower.device
    dtype = search_lower.dtype
    certified_lower_bound = torch.tensor(
        certified_intervals.lower_bounds,
        dtype=dtype,
        device=device,
    )
    certified_upper_bound = torch.tensor(
        certified_intervals.upper_bounds,
        dtype=dtype,
        device=device,
    )
    has_certified_interval = torch.tensor(
        certified_intervals.has_certified_interval,
        dtype=torch.bool,
        device=device,
    )
    is_unprovable = torch.tensor(
        certified_intervals.is_unprovable,
        dtype=torch.bool,
        device=device,
    )
    certified_lower_bound = certified_lower_bound.reshape_as(search_lower)
    certified_upper_bound = certified_upper_bound.reshape_as(search_upper)
    has_certified_interval = has_certified_interval.reshape_as(search_lower)
    is_unprovable = is_unprovable.reshape_as(search_lower)
    if bool(has_certified_interval.any()):
        initial_distance = 0.5 * (
            certified_lower_bound + certified_upper_bound
        )
        refined_distance, converged = _safeguarded_refine(
            geometry=geometry,
            initial_distance=initial_distance,
            interval_lower=certified_lower_bound,
            interval_upper=certified_upper_bound,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even_coefficients,
            residual_tolerance=residual_tolerance,
        )
        is_refined_root_valid = has_certified_interval & converged
        is_unprovable = is_unprovable | (
            has_certified_interval & (~converged)
        )
        selected_distance = torch.where(
            is_refined_root_valid,
            refined_distance,
            selected_distance,
        )
        is_encountered = is_refined_root_valid
    return _PolynomialConicRootSelection(
        distance=selected_distance,
        is_encountered=is_encountered,
        is_unprovable=is_unprovable,
    )


def _stage_unresolved_lanes_to_host(
    *,
    geometry: _ConicRayLocalGeometry,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    even_coefficients: torch.Tensor,
    clear_aperture_radius: torch.Tensor,
    search_lower: torch.Tensor,
    search_upper: torch.Tensor,
    needs_host: torch.Tensor,
) -> _StagedCertifiedIntervals:
    lane_count = int(search_lower.numel())
    flat_lower = search_lower.reshape(-1).detach().cpu()
    flat_upper = search_upper.reshape(-1).detach().cpu()
    flat_geometry = _ConicRayLocalGeometry(
        local_origin_x=geometry.local_origin_x.reshape(-1).detach().cpu(),
        local_origin_y=geometry.local_origin_y.reshape(-1).detach().cpu(),
        local_origin_z=geometry.local_origin_z.reshape(-1).detach().cpu(),
        local_direction_x=(
            geometry.local_direction_x.reshape(-1).detach().cpu()
        ),
        local_direction_y=(
            geometry.local_direction_y.reshape(-1).detach().cpu()
        ),
        local_direction_z=(
            geometry.local_direction_z.reshape(-1).detach().cpu()
        ),
        radial_origin_squared=(
            geometry.radial_origin_squared.reshape(-1).detach().cpu()
        ),
        radial_origin_direction_dot=(
            geometry.radial_origin_direction_dot.reshape(-1).detach().cpu()
        ),
        transverse_direction_squared=(
            geometry.transverse_direction_squared.reshape(-1).detach().cpu()
        ),
    )
    flat_curvature = (
        curvature.detach().cpu()
        if curvature.numel() == lane_count
        else curvature.detach().cpu().reshape(-1)
    )
    flat_conic = (
        conic_constant.detach().cpu()
        if conic_constant.numel() == lane_count
        else conic_constant.detach().cpu().reshape(-1)
    )
    host_even_coefficients = tuple(
        float(value) for value in even_coefficients.detach().cpu().reshape(-1)
    )
    aperture_value = float(
        clear_aperture_radius.detach().cpu().reshape(-1)[0].item()
    )
    host_required_by_lane = needs_host.reshape(-1)
    certified_lower_bounds: list[float] = [0.0] * lane_count
    certified_upper_bounds: list[float] = [0.0] * lane_count
    has_certified_interval: list[bool] = [False] * lane_count
    is_unprovable: list[bool] = [False] * lane_count
    for lane_index in range(lane_count):
        if not bool(host_required_by_lane[lane_index]):
            continue
        local_origin = (
            float(flat_geometry.local_origin_x[lane_index].item()),
            float(flat_geometry.local_origin_y[lane_index].item()),
            float(flat_geometry.local_origin_z[lane_index].item()),
        )
        local_direction = (
            float(flat_geometry.local_direction_x[lane_index].item()),
            float(flat_geometry.local_direction_y[lane_index].item()),
            float(flat_geometry.local_direction_z[lane_index].item()),
        )
        curvature_value = float(
            flat_curvature[lane_index].item()
            if flat_curvature.numel() > 1
            else flat_curvature.item()
        )
        conic_value = float(
            flat_conic[lane_index].item()
            if flat_conic.numel() > 1
            else flat_conic.item()
        )
        lane_search_lower = float(flat_lower[lane_index].item())
        lane_search_upper = float(flat_upper[lane_index].item())
        interval_result = _host_isolate_nearest_valid_root(
            origin=local_origin,
            direction=local_direction,
            curvature=curvature_value,
            conic_constant=conic_value,
            even_coefficients=host_even_coefficients,
            search_lower=lane_search_lower,
            search_upper=lane_search_upper,
            aperture_value=aperture_value,
        )
        if interval_result.is_unproved:
            is_unprovable[lane_index] = True
            continue
        if interval_result.has_valid:
            certified_lower_bounds[lane_index] = interval_result.lower
            certified_upper_bounds[lane_index] = interval_result.upper
            has_certified_interval[lane_index] = True
    return _StagedCertifiedIntervals(
        lower_bounds=tuple(certified_lower_bounds),
        upper_bounds=tuple(certified_upper_bounds),
        has_certified_interval=tuple(has_certified_interval),
        is_unprovable=tuple(is_unprovable),
    )


@dataclass(frozen=True, slots=True)
class _HostIntervalResult:
    """
    承载宿主精确隔离返回的区间状态

    """

    lower: float
    upper: float
    has_valid: bool
    is_unproved: bool

    @classmethod
    def empty(cls) -> _HostIntervalResult:
        """
        返回未命中且可证的空结果

        """
        return cls(lower=0.0, upper=0.0, has_valid=False, is_unproved=False)

    @classmethod
    def unproved(cls) -> _HostIntervalResult:
        """
        返回存在性或唯一性不可证的结果

        """
        return cls(lower=0.0, upper=0.0, has_valid=False, is_unproved=True)


def _host_isolate_nearest_valid_root(
    *,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    curvature: float,
    conic_constant: float,
    even_coefficients: tuple[float, ...],
    search_lower: float,
    search_upper: float,
    aperture_value: float,
) -> _HostIntervalResult:
    if not (search_upper > search_lower):
        return _HostIntervalResult.empty()
    degree = polynomial_degree(
        origin=origin,
        direction=direction,
        curvature=curvature,
        conic_constant=conic_constant,
        even_coefficients=even_coefficients,
    )
    if degree < 1:
        return _HostIntervalResult.empty()
    if degree > MAX_POLYNOMIAL_DEGREE:
        return _HostIntervalResult.unproved()
    isolated_roots = isolate_real_roots(
        origin=origin,
        direction=direction,
        curvature=curvature,
        conic_constant=conic_constant,
        even_coefficients=even_coefficients,
        interval_lower=search_lower,
        interval_upper=search_upper,
    )
    if not isolated_roots:
        return _HostIntervalResult.empty()
    aperture_radius_squared = aperture_value * aperture_value
    one_plus_conic_constant = 1.0 + conic_constant
    nearest_root_lower_bound: float | None = None
    nearest_root_upper_bound: float | None = None
    for (
        root_lower_fraction,
        root_upper_fraction,
        distinct_root_count,
    ) in isolated_roots:
        if distinct_root_count > 1:
            return _HostIntervalResult.unproved()
        root_upper_bound = math.nextafter(
            float(root_upper_fraction),
            math.inf,
        )
        if root_upper_bound < 0.0:
            continue
        root_midpoint = float(
            (root_lower_fraction + root_upper_fraction) / 2
        )
        local_x = origin[0] + root_midpoint * direction[0]
        local_y = origin[1] + root_midpoint * direction[1]
        local_z = origin[2] + root_midpoint * direction[2]
        radius_squared = local_x * local_x + local_y * local_y
        even_sag = 0.0
        radius_power = radius_squared
        for coefficient in even_coefficients:
            even_sag += coefficient * radius_power
            radius_power *= radius_squared
        base_sag_residual = local_z - even_sag
        sheet_guard = (
            1.0
            - one_plus_conic_constant * curvature * base_sag_residual
        )
        real_domain_radicand = (
            1.0
            - one_plus_conic_constant
            * curvature
            * curvature
            * radius_squared
        )
        if (
            sheet_guard < 0.0
            or real_domain_radicand < 0.0
            or radius_squared > aperture_radius_squared
        ):
            continue
        root_lower_bound = math.nextafter(
            float(root_lower_fraction),
            -math.inf,
        )
        if (
            nearest_root_lower_bound is None
            or root_lower_bound < nearest_root_lower_bound
        ):
            nearest_root_lower_bound = root_lower_bound
            nearest_root_upper_bound = root_upper_bound
    if nearest_root_lower_bound is None:
        return _HostIntervalResult.empty()
    assert nearest_root_upper_bound is not None
    certified_lower_bound = max(
        search_lower,
        nearest_root_lower_bound,
    )
    certified_upper_bound = min(
        search_upper,
        nearest_root_upper_bound,
    )
    if not (certified_upper_bound > certified_lower_bound):
        # 区间在数值零宽：用上界占位，设备精化会立即收敛到该点
        certified_lower_bound = max(
            search_lower,
            math.nextafter(certified_lower_bound, -math.inf),
        )
        certified_upper_bound = min(
            search_upper,
            math.nextafter(certified_upper_bound, math.inf),
        )
    return _HostIntervalResult(
        lower=certified_lower_bound,
        upper=certified_upper_bound,
        has_valid=True,
        is_unproved=False,
    )

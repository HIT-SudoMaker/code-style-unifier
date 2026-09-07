from __future__ import annotations

import torch

from chromatix_next._numerics._exact_binary64_sign import (
    _exact_binary64_monomial_sum_sign,
)
from chromatix_next._tensors import is_value_readable

_TRIPLE_PRODUCT_OPERATION_COUNT = 18
_DISCRIMINANT_OPERATION_COUNT = 8
_SQUARED_REFERENCE_MINUS_FACTOR_OPERATION_COUNT = 8


def _unit_roundoff(dtype: torch.dtype) -> float:
    if dtype is torch.complex128:
        dtype = torch.float64
    elif dtype is torch.complex64:
        dtype = torch.float32
    return torch.finfo(dtype).eps / 2.0


def _binary_rounding_could_change_sign(
    *,
    rounded_value: torch.Tensor,
    magnitude_envelope: torch.Tensor,
    operation_count: int,
    underflow_amplification: torch.Tensor,
) -> torch.Tensor:
    if (
        rounded_value.is_meta
        or magnitude_envelope.is_meta
        or underflow_amplification.is_meta
    ):
        return torch.ones_like(rounded_value, dtype=torch.bool)
    if operation_count <= 0:
        return torch.ones_like(rounded_value, dtype=torch.bool)

    positive_infinity = torch.full_like(rounded_value, torch.inf)
    negative_infinity = torch.full_like(rounded_value, -torch.inf)
    unit_roundoff = torch.full_like(
        rounded_value,
        _unit_roundoff(rounded_value.dtype),
    )
    smallest_subnormal = torch.nextafter(
        torch.zeros_like(rounded_value),
        positive_infinity,
    )
    operation_count_value = torch.full_like(
        rounded_value,
        float(operation_count),
    )
    accumulated_roundoff = torch.nextafter(
        operation_count_value * unit_roundoff,
        positive_infinity,
    )
    recovery_denominator = torch.nextafter(
        1.0 - accumulated_roundoff,
        negative_infinity,
    )
    relative_error_factor = torch.nextafter(
        accumulated_roundoff / recovery_denominator,
        positive_infinity,
    )
    absolute_error = torch.nextafter(
        operation_count_value * smallest_subnormal,
        positive_infinity,
    )
    absolute_error = torch.nextafter(
        absolute_error * underflow_amplification,
        positive_infinity,
    )
    recovered_envelope = torch.nextafter(
        magnitude_envelope + absolute_error,
        positive_infinity,
    )
    envelope_recovery_denominator = torch.nextafter(
        1.0 - relative_error_factor,
        negative_infinity,
    )
    recovered_envelope = torch.nextafter(
        recovered_envelope / envelope_recovery_denominator,
        positive_infinity,
    )
    relative_error = torch.nextafter(
        relative_error_factor * recovered_envelope,
        positive_infinity,
    )
    rounding_bound = torch.nextafter(
        relative_error + absolute_error,
        positive_infinity,
    )
    has_invalid_certificate_input = (
        ~torch.isfinite(rounded_value)
        | ~torch.isfinite(magnitude_envelope)
        | ~torch.isfinite(underflow_amplification)
        | (magnitude_envelope < 0.0)
        | (underflow_amplification < 0.0)
        | ~torch.isfinite(relative_error_factor)
        | (recovery_denominator <= 0.0)
        | (envelope_recovery_denominator <= 0.0)
        | ~torch.isfinite(rounding_bound)
    )
    return has_invalid_certificate_input | (rounded_value.abs() <= rounding_bound)


def _vector_reduction_batch_shape(
    *tensors: torch.Tensor,
) -> tuple[int, ...]:
    return torch.broadcast_shapes(
        *(tuple(tensor.shape[:-1]) for tensor in tensors)
    )


def _resolve_ambiguous_sign(
    *,
    float_value: torch.Tensor,
    ambiguous: torch.Tensor,
    exact_monomials: tuple[tuple[int, tuple[torch.Tensor, ...]], ...],
) -> torch.Tensor:
    is_ambiguity_readable = is_value_readable(ambiguous)
    if is_ambiguity_readable and not bool(ambiguous.any()):
        return torch.sign(float_value).to(torch.int8)
    exact_sign = _exact_binary64_monomial_sum_sign(
        exact_monomials,
        tuple(float_value.shape),
    )
    if not is_ambiguity_readable:
        # Meta 不读取数据，但进入一次结构整数肢路径，使 Workstation 存储预检保持保守
        return exact_sign
    return torch.where(
        ambiguous,
        exact_sign,
        torch.sign(float_value),
    ).to(torch.int8)


def _common_scale_exponent(*operand_abs: torch.Tensor) -> torch.Tensor:
    per_axis_max = torch.stack(list(operand_abs), dim=0)
    max_abs = per_axis_max.max(dim=0).values
    safe_max = torch.where(max_abs > 0.0, max_abs, torch.ones_like(max_abs))
    _fraction, exponent = torch.frexp(safe_max)
    return -exponent


def dot_sign(first: torch.Tensor, second: torch.Tensor) -> torch.Tensor:
    """
    返回 ``first · second``（沿末维 3 向量）的精确符号 ``-1/0/+1``

    """
    batch_shape = _vector_reduction_batch_shape(first, second)
    first_expanded = first.broadcast_to(batch_shape + (first.shape[-1],))
    second_expanded = second.broadcast_to(batch_shape + (second.shape[-1],))
    scale_exponent = _common_scale_exponent(
        first_expanded.abs().amax(dim=-1),
        second_expanded.abs().amax(dim=-1),
    )
    scaled_first = torch.ldexp(first_expanded, scale_exponent.unsqueeze(-1))
    scaled_second = torch.ldexp(second_expanded, scale_exponent.unsqueeze(-1))
    float_dot = (scaled_first * scaled_second).sum(dim=-1)
    magnitude_scale = (scaled_first.abs() * scaled_second.abs()).sum(dim=-1)
    exact_monomials = tuple(
        (
            1,
            (
                first_expanded[..., component_index],
                second_expanded[..., component_index],
            ),
        )
        for component_index in range(first.shape[-1])
    )
    operation_count = 2 * first.shape[-1] - 1
    ambiguous = _binary_rounding_could_change_sign(
        rounded_value=float_dot,
        magnitude_envelope=magnitude_scale,
        operation_count=operation_count,
        underflow_amplification=torch.ones_like(float_dot),
    )
    return _resolve_ambiguous_sign(
        float_value=float_dot,
        ambiguous=ambiguous,
        exact_monomials=exact_monomials,
    )


def triple_product_sign(
    first: torch.Tensor,
    second: torch.Tensor,
    third: torch.Tensor,
) -> torch.Tensor:
    """
    返回 ``first · (second × third)`` 的精确符号 ``-1/0/+1``（各为末维 3 向量）

    """
    batch_shape = _vector_reduction_batch_shape(first, second, third)
    first_expanded = first.broadcast_to(batch_shape + (3,))
    second_expanded = second.broadcast_to(batch_shape + (3,))
    third_expanded = third.broadcast_to(batch_shape + (3,))
    scale_exponent = _common_scale_exponent(
        first_expanded.abs().amax(dim=-1),
        second_expanded.abs().amax(dim=-1),
        third_expanded.abs().amax(dim=-1),
    )
    scaled_first = torch.ldexp(first_expanded, scale_exponent.unsqueeze(-1))
    scaled_second = torch.ldexp(second_expanded, scale_exponent.unsqueeze(-1))
    scaled_third = torch.ldexp(third_expanded, scale_exponent.unsqueeze(-1))
    cross = torch.linalg.cross(scaled_second, scaled_third, dim=-1)
    float_value = (scaled_first * cross).sum(dim=-1)
    magnitude_scale = (
        scaled_first.abs().sum(dim=-1)
        * scaled_second.abs().sum(dim=-1)
        * scaled_third.abs().sum(dim=-1)
    )
    exact_monomials = (
        (1, (first_expanded[..., 0], second_expanded[..., 1], third_expanded[..., 2])),
        (-1, (first_expanded[..., 0], second_expanded[..., 2], third_expanded[..., 1])),
        (-1, (first_expanded[..., 1], second_expanded[..., 0], third_expanded[..., 2])),
        (1, (first_expanded[..., 1], second_expanded[..., 2], third_expanded[..., 0])),
        (1, (first_expanded[..., 2], second_expanded[..., 0], third_expanded[..., 1])),
        (-1, (first_expanded[..., 2], second_expanded[..., 1], third_expanded[..., 0])),
    )
    ambiguous = _binary_rounding_could_change_sign(
        rounded_value=float_value,
        magnitude_envelope=magnitude_scale,
        operation_count=_TRIPLE_PRODUCT_OPERATION_COUNT,
        underflow_amplification=torch.full_like(float_value, 9.0),
    )
    return _resolve_ambiguous_sign(
        float_value=float_value,
        ambiguous=ambiguous,
        exact_monomials=exact_monomials,
    )


def scaled_squared_norm_difference_sign(
    reference: torch.Tensor,
    vector: torch.Tensor,
) -> torch.Tensor:
    """
    返回 ``reference² − ‖vector‖²`` 的精确符号

    ``reference`` 为标量、``vector`` 为 (...,K)。按最大幅值的 2 的幂统一缩放 reference
    与 vector，避免 float 平方溢出/下溢；sign 不变。

    """
    batch_shape = torch.broadcast_shapes(
        tuple(reference.shape),
        tuple(vector.shape[:-1]),
    )
    reference_broadcast = reference.expand(batch_shape)
    vector_broadcast = vector.broadcast_to(batch_shape + (vector.shape[-1],))
    scale_exponent = _common_scale_exponent(
        reference_broadcast.abs(),
        vector_broadcast.abs().amax(dim=-1),
    )
    scaled_reference = torch.ldexp(reference_broadcast, scale_exponent)
    scaled_vector = torch.ldexp(vector_broadcast, scale_exponent.unsqueeze(-1))
    float_difference = (
        scaled_reference * scaled_reference
        - (scaled_vector * scaled_vector).sum(dim=-1)
    )
    magnitude_scale = (
        scaled_reference * scaled_reference
        + (scaled_vector * scaled_vector).sum(dim=-1)
    )
    exact_monomials = (
        (1, (reference_broadcast, reference_broadcast)),
        *(
            (
                -1,
                (
                    vector_broadcast[..., component_index],
                    vector_broadcast[..., component_index],
                ),
            )
            for component_index in range(vector_broadcast.shape[-1])
        ),
    )
    operation_count = 2 * vector.shape[-1] + 4
    ambiguous = _binary_rounding_could_change_sign(
        rounded_value=float_difference,
        magnitude_envelope=magnitude_scale,
        operation_count=operation_count,
        underflow_amplification=torch.ones_like(float_difference),
    )
    return _resolve_ambiguous_sign(
        float_value=float_difference,
        ambiguous=ambiguous,
        exact_monomials=exact_monomials,
    )


def squared_reference_minus_squared_factor_extra_factor_sign(
    reference: torch.Tensor,
    squared_factor: torch.Tensor,
    extra_factor: torch.Tensor,
) -> torch.Tensor:
    """
    返回 ``参考量² - 平方因子² · 额外因子`` 的精确符号

    用于把 ``A·sqrt(Q) < X`` 这样的比较改写为多项式符号判定：在平方-符号等价区间
    内（两同号非负或两同号非正），``A·sqrt(Q) < X`` 与 ``X² − A²·Q`` 同号，故把
    ``sqrt(Q)`` 的舍入从判据中完全移除而仍得到严格符号。调用方负责保证仅在
    额外因子（即 ``Q``）非负且平方-符号等价成立时使用本函数的输出；
    本函数只返回多项式的精确符号 ``-1/0/+1``。

    """
    batch_shape = torch.broadcast_shapes(
        tuple(reference.shape),
        tuple(squared_factor.shape),
        tuple(extra_factor.shape),
    )
    reference_broadcast = reference.expand(batch_shape)
    squared_factor_broadcast = squared_factor.expand(batch_shape)
    extra_factor_broadcast = extra_factor.expand(batch_shape)
    scale_exponent = _common_scale_exponent(
        reference_broadcast.abs(),
        squared_factor_broadcast.abs(),
    )
    scaled_reference = torch.ldexp(reference_broadcast, scale_exponent)
    scaled_squared_factor = torch.ldexp(squared_factor_broadcast, scale_exponent)
    scaled_extra_factor = extra_factor_broadcast
    squared_reference = scaled_reference * scaled_reference
    squared_factor_times_extra = (
        scaled_squared_factor
        * scaled_squared_factor
        * scaled_extra_factor
    )
    float_difference = squared_reference - squared_factor_times_extra
    magnitude_scale = squared_reference.abs() + squared_factor_times_extra.abs()
    exact_monomials = (
        (1, (reference_broadcast, reference_broadcast)),
        (
            -1,
            (
                squared_factor_broadcast,
                squared_factor_broadcast,
                extra_factor_broadcast,
            ),
        ),
    )
    underflow_amplification = torch.maximum(
        torch.ones_like(extra_factor_broadcast),
        extra_factor_broadcast.abs(),
    )
    ambiguous = _binary_rounding_could_change_sign(
        rounded_value=float_difference,
        magnitude_envelope=magnitude_scale,
        operation_count=_SQUARED_REFERENCE_MINUS_FACTOR_OPERATION_COUNT,
        underflow_amplification=underflow_amplification,
    )
    return _resolve_ambiguous_sign(
        float_value=float_difference,
        ambiguous=ambiguous,
        exact_monomials=exact_monomials,
    )


def base_conic_discriminant_sign(
    origin_x: torch.Tensor,
    origin_y: torch.Tensor,
    origin_z: torch.Tensor,
    direction_x: torch.Tensor,
    direction_y: torch.Tensor,
    direction_z: torch.Tensor,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
) -> torch.Tensor:
    """
    返回原始 binary64 圆锥操作数所定义判别式的精确符号
    """

    batch_shape = torch.broadcast_shapes(
        tuple(origin_x.shape),
        tuple(origin_y.shape),
        tuple(origin_z.shape),
        tuple(direction_x.shape),
        tuple(direction_y.shape),
        tuple(direction_z.shape),
        tuple(curvature.shape),
        tuple(conic_constant.shape),
    )
    ox = origin_x.expand(batch_shape)
    oy = origin_y.expand(batch_shape)
    oz = origin_z.expand(batch_shape)
    dx = direction_x.expand(batch_shape)
    dy = direction_y.expand(batch_shape)
    dz = direction_z.expand(batch_shape)
    c = curvature.expand(batch_shape)
    k = conic_constant.expand(batch_shape)
    exact_monomials = (
        (1, (dz, dz)),
        (-1, (c, c, dx, dx, oy, oy)),
        (-1, (c, c, dx, dx, oz, oz)),
        (-1, (c, c, dy, dy, ox, ox)),
        (-1, (c, c, dy, dy, oz, oz)),
        (-1, (c, c, dz, dz, ox, ox)),
        (-1, (c, c, dz, dz, oy, oy)),
        (-1, (c, c, dx, dx, k, oz, oz)),
        (-1, (c, c, dy, dy, k, oz, oz)),
        (-1, (c, c, dz, dz, k, ox, ox)),
        (-1, (c, c, dz, dz, k, oy, oy)),
        (1, (c, dx, dx, oz)),
        (1, (c, dx, dx, oz)),
        (1, (c, dy, dy, oz)),
        (1, (c, dy, dy, oz)),
        (-1, (c, dx, dz, ox)),
        (-1, (c, dx, dz, ox)),
        (-1, (c, dy, dz, oy)),
        (-1, (c, dy, dz, oy)),
        (1, (c, c, dx, dy, ox, oy)),
        (1, (c, c, dx, dy, ox, oy)),
        (1, (c, c, dx, dz, ox, oz)),
        (1, (c, c, dx, dz, ox, oz)),
        (1, (c, c, dy, dz, oy, oz)),
        (1, (c, c, dy, dz, oy, oz)),
        (1, (c, c, dx, dz, k, ox, oz)),
        (1, (c, c, dx, dz, k, ox, oz)),
        (1, (c, c, dy, dz, k, oy, oz)),
        (1, (c, c, dy, dz, k, oy, oz)),
    )
    return _resolve_ambiguous_sign(
        float_value=torch.zeros(
            batch_shape,
            dtype=origin_x.dtype,
            device=origin_x.device,
        ),
        ambiguous=torch.ones(
            batch_shape,
            dtype=torch.bool,
            device=origin_x.device,
        ),
        exact_monomials=exact_monomials,
    )


def quadratic_discriminant_sign(
    quadratic_coefficient: torch.Tensor,
    linear_coefficient: torch.Tensor,
    constant_coefficient: torch.Tensor,
) -> torch.Tensor:
    """
    返回二次判别式的精确符号 ``-1/0/+1``

    """
    batch_shape = torch.broadcast_shapes(
        tuple(quadratic_coefficient.shape),
        tuple(linear_coefficient.shape),
        tuple(constant_coefficient.shape),
    )
    quadratic_coefficient_broadcast = quadratic_coefficient.expand(batch_shape)
    linear_coefficient_broadcast = linear_coefficient.expand(batch_shape)
    constant_coefficient_broadcast = constant_coefficient.expand(batch_shape)
    scale_exponent = _common_scale_exponent(
        quadratic_coefficient_broadcast.abs(),
        linear_coefficient_broadcast.abs(),
        constant_coefficient_broadcast.abs(),
    )
    scaled_quadratic_coefficient = torch.ldexp(
        quadratic_coefficient_broadcast,
        scale_exponent,
    )
    scaled_linear_coefficient = torch.ldexp(
        linear_coefficient_broadcast,
        scale_exponent,
    )
    scaled_constant_coefficient = torch.ldexp(
        constant_coefficient_broadcast,
        scale_exponent,
    )
    float_value = (
        scaled_linear_coefficient * scaled_linear_coefficient
        - 4.0
        * scaled_quadratic_coefficient
        * scaled_constant_coefficient
    )
    magnitude_scale = (
        scaled_linear_coefficient.abs() * scaled_linear_coefficient.abs()
        + 4.0
        * scaled_quadratic_coefficient.abs()
        * scaled_constant_coefficient.abs()
    )
    exact_monomials = (
        (
            1,
            (
                linear_coefficient_broadcast,
                linear_coefficient_broadcast,
            ),
        ),
        (
            -4,
            (
                quadratic_coefficient_broadcast,
                constant_coefficient_broadcast,
            ),
        ),
    )
    ambiguous = _binary_rounding_could_change_sign(
        rounded_value=float_value,
        magnitude_envelope=magnitude_scale,
        operation_count=_DISCRIMINANT_OPERATION_COUNT,
        underflow_amplification=torch.full_like(float_value, 4.0),
    )
    return _resolve_ambiguous_sign(
        float_value=float_value,
        ambiguous=ambiguous,
        exact_monomials=exact_monomials,
    )


def quotient_sign(numerator: torch.Tensor, denominator: torch.Tensor) -> torch.Tensor:
    """
    返回 ``numerator / denominator`` 的精确符号 ``-1/0/+1``，不经除法

    一个标量积的精确符号恰为两因子符号之积（积为零当且仅当某因子为零），与幅值无关——
    即便积下溢到浮点零，两因子各自的符号仍可读。故此处不做幅值缩放/展开，直接
    ``sign(num)·sign(den)``，对任意幅值比（含 ``5e-324`` 与 ``1e200`` vs ``1e-200`` 等
    极端指数情形）都精确。``denominator == 0`` 返回 0（平行/未定义，由调用方掩码处理）。

    """
    batch_shape = torch.broadcast_shapes(
        tuple(numerator.shape),
        tuple(denominator.shape),
    )
    if numerator.is_meta or denominator.is_meta:
        return torch.zeros(batch_shape, dtype=torch.int8, device=numerator.device)
    numerator_sign = torch.sign(numerator.expand(batch_shape))
    denominator_sign = torch.sign(denominator.expand(batch_shape))
    return (numerator_sign * denominator_sign).to(torch.int8)

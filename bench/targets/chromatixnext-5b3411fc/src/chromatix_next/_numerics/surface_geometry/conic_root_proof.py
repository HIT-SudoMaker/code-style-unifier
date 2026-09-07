from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

MAX_POLYNOMIAL_DEGREE: int = 256
ISOLATION_BISECTION_DEPTH: int = 96
_Polynomial = tuple[Fraction, ...]
def _normalize(coefficients: Sequence[Fraction]) -> _Polynomial:
    values = list(coefficients)
    while values and values[-1] == 0:
        values.pop()
    return tuple(values)


def _degree(polynomial: _Polynomial) -> int:
    return len(polynomial) - 1


def _add(first: _Polynomial, second: _Polynomial) -> _Polynomial:
    length = max(len(first), len(second))
    sums = [Fraction(0)] * length
    for index, coefficient in enumerate(first):
        sums[index] += coefficient
    for index, coefficient in enumerate(second):
        sums[index] += coefficient
    return _normalize(sums)


def _scale(scalar: Fraction, polynomial: _Polynomial) -> _Polynomial:
    if scalar == 0 or not polynomial:
        return ()
    return tuple(scalar * coefficient for coefficient in polynomial)


def _multiply(first: _Polynomial, second: _Polynomial) -> _Polynomial:
    if not first or not second:
        return ()
    product = [Fraction(0)] * (len(first) + len(second) - 1)
    for index_a, coefficient_a in enumerate(first):
        if coefficient_a == 0:
            continue
        for index_b, coefficient_b in enumerate(second):
            product[index_a + index_b] += coefficient_a * coefficient_b
    return _normalize(product)


def _derivative(polynomial: _Polynomial) -> _Polynomial:
    if len(polynomial) <= 1:
        return ()
    derived = [index * coefficient for index, coefficient in enumerate(polynomial)]
    derived[0] = Fraction(0)
    return _normalize(derived[1:])


def _divide_remainder(
    dividend: _Polynomial,
    divisor: _Polynomial,
) -> _Polynomial:
    assert divisor, "多项式除法要求非零除数（调用方保证）"
    remainder = list(dividend)
    lead = divisor[-1]
    divisor_len = len(divisor)
    for index in range(len(dividend) - 1, divisor_len - 2, -1):
        coefficient = remainder[index]
        if coefficient == 0:
            continue
        quotient_factor = coefficient / lead
        offset = index - divisor_len + 1
        for inner, divisor_coefficient in enumerate(divisor):
            remainder[offset + inner] -= quotient_factor * divisor_coefficient
    return _normalize(remainder[: max(divisor_len - 1, 0)])


def _gcd(first: _Polynomial, second: _Polynomial) -> _Polynomial:
    current = _normalize(first)
    partner = _normalize(second)
    while partner:
        remainder = _divide_remainder(current, partner)
        current = partner
        partner = remainder
    if current:
        lead = current[-1]
        current = tuple(coefficient / lead for coefficient in current)
    return current


def _square_free_part(polynomial: _Polynomial) -> _Polynomial:
    if _degree(polynomial) <= 0:
        return polynomial
    derivative = _derivative(polynomial)
    if not derivative:
        return polynomial
    common_polynomial_factor = _gcd(polynomial, derivative)
    if (
        not common_polynomial_factor
        or common_polynomial_factor == (Fraction(1),)
    ):
        return polynomial
    return _divide_polynomial_quotient(polynomial, common_polynomial_factor)


def _divide_polynomial_quotient(
    dividend: _Polynomial,
    divisor: _Polynomial,
) -> _Polynomial:
    assert divisor, "多项式除法要求非零除数（调用方保证）"
    remainder = list(dividend)
    lead = divisor[-1]
    divisor_len = len(divisor)
    quotient_degree = len(dividend) - divisor_len
    if quotient_degree < 0:
        return ()
    quotient = [Fraction(0)] * (quotient_degree + 1)
    for index in range(len(dividend) - 1, divisor_len - 2, -1):
        coefficient = remainder[index]
        if coefficient == 0:
            continue
        quotient_factor = coefficient / lead
        quotient[index - divisor_len + 1] = quotient_factor
        offset = index - divisor_len + 1
        for inner, divisor_coefficient in enumerate(divisor):
            remainder[offset + inner] -= quotient_factor * divisor_coefficient
    return _normalize(quotient)


def _sturm_sequence(square_free: _Polynomial) -> tuple[_Polynomial, ...]:
    sequence: list[_Polynomial] = [square_free, _derivative(square_free)]
    while _degree(sequence[-1]) > 0:
        remainder = _divide_remainder(sequence[-2], sequence[-1])
        if not remainder:
            break
        negated = _scale(Fraction(-1), remainder)
        lead_abs = negated[-1] if negated[-1] >= 0 else -negated[-1]
        if lead_abs > 0:
            normalized = tuple(coefficient / lead_abs for coefficient in negated)
        else:
            normalized = negated
        sequence.append(normalized)
    return tuple(sequence)


def _sign_at(
    polynomial: _Polynomial,
    point: Fraction,
) -> int:
    value = Fraction(0)
    power = Fraction(1)
    for coefficient in polynomial:
        value += coefficient * power
        power *= point
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _variation_count_right(
    sequence: Sequence[_Polynomial],
    point: Fraction,
) -> int:
    signs: list[int] = []
    for polynomial in sequence:
        if not polynomial:
            continue
        signs.append(_sign_at(polynomial, point))
    if signs and signs[0] == 0:
        for sign_index in range(1, len(signs)):
            if signs[sign_index] != 0:
                signs[0] = signs[sign_index]
                break
        else:
            signs[0] = 1
    compact = [sign_value for sign_value in signs if sign_value != 0]
    variations = 0
    for index in range(1, len(compact)):
        if compact[index] != compact[index - 1]:
            variations += 1
    return variations


def _root_count_open_left_closed_right(
    sequence: Sequence[_Polynomial],
    lower: Fraction,
    upper: Fraction,
) -> int:
    if lower >= upper:
        return 0
    v_lower = _variation_count_right(sequence, lower)
    v_upper = _variation_count_right(sequence, upper)
    count = v_lower - v_upper
    return count if count > 0 else 0


def _narrow_single_root(
    sequence: Sequence[_Polynomial],
    lower: Fraction,
    upper: Fraction,
    *,
    depth_budget: int,
) -> tuple[Fraction, Fraction]:
    if depth_budget <= 0:
        return lower, upper
    width = upper - lower
    magnitude = abs(lower) if abs(lower) > abs(upper) else abs(upper)
    if magnitude == 0:
        magnitude = width
    if width == 0 or width <= magnitude * (Fraction(1) / (1 << 60)):
        return lower, upper
    midpoint = (lower + upper) / 2
    left_count = _root_count_open_left_closed_right(sequence, lower, midpoint)
    next_depth = depth_budget - 1
    if left_count == 1:
        return _narrow_single_root(sequence, lower, midpoint, depth_budget=next_depth)
    return _narrow_single_root(sequence, midpoint, upper, depth_budget=next_depth)


def _isolate_in_interval(
    square_free: _Polynomial,
    sequence: Sequence[_Polynomial],
    lower: Fraction,
    upper: Fraction,
    *,
    depth_budget: int,
) -> list[tuple[Fraction, Fraction]]:
    count = _root_count_open_left_closed_right(sequence, lower, upper)
    if count == 0:
        return []
    if count == 1:
        return [_narrow_single_root(sequence, lower, upper, depth_budget=depth_budget)]
    if depth_budget <= 0:
        # 超出冻结预算：把整段作为含多根的不分段返回，调用方据此判非唯一 ⇒ 抛稳定错误
        return [(lower, upper)]
    midpoint = (lower + upper) / 2
    left = _isolate_in_interval(
        square_free,
        sequence,
        lower,
        midpoint,
        depth_budget=depth_budget - 1,
    )
    right = _isolate_in_interval(
        square_free,
        sequence,
        midpoint,
        upper,
        depth_budget=depth_budget - 1,
    )
    return left + right


def build_polynomial_coefficients(
    *,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    curvature: float,
    conic_constant: float,
    even_coefficients: Sequence[float],
) -> _Polynomial:
    """
    诱导 P(t) 的精确有理系数多项式

    """
    local_origin_x_fraction, local_origin_y_fraction, local_origin_z_fraction = (
        Fraction(origin[0]),
        Fraction(origin[1]),
        Fraction(origin[2]),
    )
    (
        local_direction_x_fraction,
        local_direction_y_fraction,
        local_direction_z_fraction,
    ) = (
        Fraction(direction[0]),
        Fraction(direction[1]),
        Fraction(direction[2]),
    )
    curvature_fraction = Fraction(curvature)
    conic_constant_fraction = Fraction(conic_constant)
    even_coefficient_fractions = tuple(
        Fraction(value) for value in even_coefficients
    )
    local_x_polynomial = (
        local_origin_x_fraction,
        local_direction_x_fraction,
    )
    local_y_polynomial = (
        local_origin_y_fraction,
        local_direction_y_fraction,
    )
    local_z_polynomial = (
        local_origin_z_fraction,
        local_direction_z_fraction,
    )
    radial_squared_polynomial = _add(
        _multiply(local_x_polynomial, local_x_polynomial),
        _multiply(local_y_polynomial, local_y_polynomial),
    )
    even_sag_polynomial: _Polynomial = ()
    radial_squared_power_polynomial: _Polynomial = (Fraction(1),)
    for coefficient in even_coefficient_fractions:
        radial_squared_power_polynomial = _multiply(
            radial_squared_power_polynomial,
            radial_squared_polynomial,
        )
        even_sag_polynomial = _add(
            even_sag_polynomial,
            _scale(coefficient, radial_squared_power_polynomial),
        )
    sag_residual_polynomial = _add(
        local_z_polynomial,
        _scale(Fraction(-1), even_sag_polynomial),
    )
    radial_curvature_term = _scale(
        curvature_fraction,
        radial_squared_polynomial,
    )
    linear_sag_term = _scale(Fraction(-2), sag_residual_polynomial)
    quadratic_sag_term = _scale(
        (Fraction(1) + conic_constant_fraction) * curvature_fraction,
        _multiply(sag_residual_polynomial, sag_residual_polynomial),
    )
    return _add(_add(radial_curvature_term, linear_sag_term), quadratic_sag_term)


def isolate_real_roots(
    *,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    curvature: float,
    conic_constant: float,
    even_coefficients: Sequence[float],
    interval_lower: float,
    interval_upper: float,
) -> list[tuple[Fraction, Fraction, int]]:
    """
    隔离区间内 P(t) 的互异实根

    """
    polynomial = build_polynomial_coefficients(
        origin=origin,
        direction=direction,
        curvature=curvature,
        conic_constant=conic_constant,
        even_coefficients=even_coefficients,
    )
    if _degree(polynomial) < 1:
        return []
    if _degree(polynomial) > MAX_POLYNOMIAL_DEGREE:
        return []
    square_free = _square_free_part(polynomial)
    if _degree(square_free) < 1:
        return []
    sequence = _sturm_sequence(square_free)
    lower = Fraction(interval_lower)
    upper = Fraction(interval_upper)
    raw_intervals = _isolate_in_interval(
        square_free,
        sequence,
        lower,
        upper,
        depth_budget=ISOLATION_BISECTION_DEPTH,
    )
    roots: list[tuple[Fraction, Fraction, int]] = []
    for low_bound, high_bound in raw_intervals:
        count = _root_count_open_left_closed_right(sequence, low_bound, high_bound)
        roots.append((low_bound, high_bound, count))
    return roots


def polynomial_degree(
    *,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    curvature: float,
    conic_constant: float,
    even_coefficients: Sequence[float],
) -> int:
    """
    返回 P(t) 的次数（供资源预算检查与诊断）

    """
    polynomial = build_polynomial_coefficients(
        origin=origin,
        direction=direction,
        curvature=curvature,
        conic_constant=conic_constant,
        even_coefficients=even_coefficients,
    )
    return _degree(polynomial)

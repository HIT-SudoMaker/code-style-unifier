from __future__ import annotations

from fractions import Fraction
import math

import pytest
import torch

from chromatix_next import _execution_memory
from chromatix_next._numerics._certified_predicates import (
    dot_sign,
    quadratic_discriminant_sign,
    quotient_sign,
    scaled_squared_norm_difference_sign,
    squared_reference_minus_squared_factor_extra_factor_sign,
    triple_product_sign,
)

FIXED_DOUBLE = torch.float64


def _binary64_bit_patterns(values: tuple[float, ...]) -> tuple[str, ...]:
    # 给失败消息保留可复现的 binary64 十六进制位型
    tensor = torch.tensor(values, dtype=torch.float64)
    return tuple(
        f"{int(bits) & ((1 << 64) - 1):016x}"
        for bits in tensor.view(torch.int64)
    )


def _as_fraction(value: float) -> Fraction:
    # 把 binary64 还原为精确有理数（独立 oracle，不复用生产展开）
    if value == 0.0:
        return Fraction(0)
    negative = value < 0.0
    fraction, exponent = math.frexp(-value if negative else value)
    mantissa = int(fraction * (1 << 53))
    rational = Fraction(mantissa) * Fraction(2) ** (exponent - 53)
    return -rational if negative else rational


def _sign_of(rational: Fraction) -> int:
    if rational > 0:
        return 1
    if rational < 0:
        return -1
    return 0


def _zero_predicate_operands(
    *,
    lane_count: int,
    device: torch.device,
    dtype: torch.dtype = FIXED_DOUBLE,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    # 为五类具名谓词建立相同的精确零输入，不代理任何谓词 Interface
    if lane_count == 513:
        first_batch_shape = (3, 1)
        second_batch_shape = (1, 171)
    else:
        first_batch_shape = (lane_count,)
        second_batch_shape = (lane_count,)
    first_vector = torch.zeros(
        first_batch_shape + (3,),
        dtype=dtype,
        device=device,
    )
    second_vector = torch.zeros(
        second_batch_shape + (3,),
        dtype=dtype,
        device=device,
    )
    first_scalar = torch.zeros(first_batch_shape, dtype=dtype, device=device)
    second_scalar = torch.zeros(second_batch_shape, dtype=dtype, device=device)
    return first_vector, second_vector, first_scalar, second_scalar


def _oracle_dot(first: tuple[float, ...], second: tuple[float, ...]) -> int:
    total = sum(
        (
            _as_fraction(first[index]) * _as_fraction(second[index])
            for index in range(len(first))
        ),
        Fraction(0),
    )
    return _sign_of(total)


def _oracle_triple_product(
    first: tuple[float, ...],
    second: tuple[float, ...],
    third: tuple[float, ...],
) -> int:
    exact_first = [_as_fraction(value) for value in first]
    exact_second = [_as_fraction(value) for value in second]
    exact_third = [_as_fraction(value) for value in third]
    exact_cross = [
        exact_second[(index + 1) % 3] * exact_third[(index + 2) % 3]
        - exact_second[(index + 2) % 3] * exact_third[(index + 1) % 3]
        for index in range(3)
    ]
    return _sign_of(
        sum(
            (
                exact_first[index] * exact_cross[index]
                for index in range(3)
            ),
            Fraction(0),
        )
    )


def _oracle_discriminant(
    quadratic_coefficient: float,
    linear_coefficient: float,
    constant_coefficient: float,
) -> int:
    value = (
        _as_fraction(linear_coefficient) ** 2
        - _as_fraction(4)
        * _as_fraction(quadratic_coefficient)
        * _as_fraction(constant_coefficient)
    )
    return _sign_of(value)


def _oracle_squared_norm_difference_sign(
    reference: float,
    components: tuple[float, ...],
) -> int:
    value = _as_fraction(reference) ** 2 - sum(
        _as_fraction(component) ** 2 for component in components
    )
    return _sign_of(value)


def _oracle_squared_reference_minus_squared_factor_times_extra_factor_sign(
    reference: float,
    squared_factor: float,
    extra: float,
) -> int:
    value = (
        _as_fraction(reference) ** 2
        - _as_fraction(squared_factor) ** 2 * _as_fraction(extra)
    )
    return _sign_of(value)


def _assert_predicate_result(
    *,
    predicate_name: str,
    case_name: str,
    input_groups: tuple[tuple[float, ...], ...],
    oracle_sign: int,
    actual_sign: torch.Tensor,
    device_label: str,
) -> None:
    # 给五个公开判定接口统一失败诊断，不抽象其各自的物理输入或执行方式
    input_bit_patterns = tuple(
        _binary64_bit_patterns(values)
        for values in input_groups
    )
    actual_value = int(actual_sign.item())
    assert actual_value == oracle_sign, (
        f"predicate={predicate_name}, case={case_name}, "
        f"inputs={input_bit_patterns}, oracle={oracle_sign}, "
        f"actual={actual_value}, device={device_label}"
    )


_LARGEST_BINARY64_POWER = math.ldexp(1.0, 1023)
_DECISIVE_COMPONENT = math.ldexp(1.0, -100)
_DIAGONAL_COMPONENT = math.sqrt(0.5)
_TINY_DIAGONAL_COMPONENT = math.ldexp(1.0, -600)

_DOT_CASES = (
    ("zero", (1.0, 1.0, 0.0), (1.0, -1.0, 0.0)),
    ("cancellation", (1.0, 2.0, 3.0), (-3.0, -2.0, -1.0)),
    ("subnormal", (2.0**-1070, 0.0, 0.0), (2.0**-1070, 0.0, 0.0)),
    (
        "adjacent_positive",
        (1.0, 1.0, 0.0),
        (math.nextafter(1.0, math.inf), -1.0, 0.0),
    ),
    (
        "full_exponent",
        (_DIAGONAL_COMPONENT, _DIAGONAL_COMPONENT, _TINY_DIAGONAL_COMPONENT),
        (
            _DIAGONAL_COMPONENT,
            -_DIAGONAL_COMPONENT,
            math.nextafter(_TINY_DIAGONAL_COMPONENT, math.inf),
        ),
    ),
    (
        "gradual_underflow_counterexample",
        (
            1.913831216316605e150,
            2.2633346905583664e150,
            3.0105468651638876e150,
        ),
        (
            3.820314390567769e-173,
            5.576637738044548e-173,
            -5.999771497809962e-173,
        ),
    ),
)
_TRIPLE_PRODUCT_CASES = (
    ("positive", (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ("negative", (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    ("zero", (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0)),
    (
        "full_exponent",
        (_LARGEST_BINARY64_POWER, _LARGEST_BINARY64_POWER, _DECISIVE_COMPONENT),
        (_LARGEST_BINARY64_POWER, _LARGEST_BINARY64_POWER, 0.0),
        (0.0, _LARGEST_BINARY64_POWER, _LARGEST_BINARY64_POWER),
    ),
)
_SQUARED_NORM_CASES = (
    ("zero", 5.0, (3.0, 4.0)),
    ("large", 1e200, (6e199, 8e199)),
    ("subnormal", 2.0**-1069, (2.0**-1070,)),
    (
        "full_exponent",
        _LARGEST_BINARY64_POWER,
        (_LARGEST_BINARY64_POWER, _DECISIVE_COMPONENT),
    ),
)
_DISCRIMINANT_CASES = (
    ("zero", 1.0, 2.0, 1.0),
    ("positive", 1.0, 0.0, -1.0),
    ("negative", 1.0, 0.0, 1.0),
    ("adjacent", 1.0, 2.0, math.nextafter(1.0, math.inf)),
    (
        "full_exponent",
        math.ldexp(1.0, -600),
        math.nextafter(2.0, math.inf),
        math.ldexp(1.0, 600),
    ),
)
_ROOT_FACTOR_CASES = (
    ("zero", 6.0, 3.0, 4.0),
    ("negative", 5.0, 3.0, 4.0),
    ("positive", 7.0, 3.0, 4.0),
    ("adjacent", math.nextafter(6.0, math.inf), 3.0, 4.0),
    (
        "full_exponent",
        math.nextafter(math.ldexp(1.0, -1000), math.inf),
        math.ldexp(1.0, -489),
        math.ldexp(1.0, -1022),
    ),
    (
        "gradual_underflow_wrong_nonzero_sign",
        float.fromhex("0x1.79e354b0ffaddp-515"),
        float.fromhex("0x1.ea1e7529b6a0cp-1"),
        float.fromhex("0x0.0260ba5267dc5p-1022"),
    ),
)


@pytest.mark.parametrize(
    ("case_name", "first", "second"),
    _DOT_CASES,
    ids=tuple(case[0] for case in _DOT_CASES),
)
def test_dot_sign_matches_independent_oracle(
    case_name: str,
    first: tuple[float, ...],
    second: tuple[float, ...],
) -> None:
    """
    点积符号与独立有理 oracle 一致（含相消/极值/次正规）
    """

    actual_sign = dot_sign(
        torch.tensor(first, dtype=FIXED_DOUBLE),
        torch.tensor(second, dtype=FIXED_DOUBLE),
    )
    _assert_predicate_result(
        predicate_name="dot_sign",
        case_name=case_name,
        input_groups=(first, second),
        oracle_sign=_oracle_dot(first, second),
        actual_sign=actual_sign,
        device_label="cpu",
    )


def test_dot_fast_path_does_not_enter_exact_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    普通可认证点积留在快速路径，不分配整数肢累加器
    """

    import chromatix_next._numerics._certified_predicates as predicates

    was_exact_core_called = False

    def _record_exact_core_call(
        *_args: object,
        **_kwargs: object,
    ) -> torch.Tensor:
        nonlocal was_exact_core_called
        was_exact_core_called = True
        return torch.empty((), dtype=torch.int8)

    monkeypatch.setattr(
        predicates,
        "_exact_binary64_monomial_sum_sign",
        _record_exact_core_call,
    )
    sign = predicates.dot_sign(
        torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
        torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
    )
    assert not was_exact_core_called
    assert int(sign.item()) == 1


def test_gradual_underflow_dot_enters_exact_core_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    渐进下溢点积不被快速过滤误认证，并且整批只进入精确核一次
    """

    import chromatix_next._numerics._certified_predicates as predicates

    original_exact_core = predicates._exact_binary64_monomial_sum_sign
    exact_core_call_count = 0

    def _record_exact_core_call(
        monomials: tuple[tuple[int, tuple[torch.Tensor, ...]], ...],
        batch_shape: tuple[int, ...],
    ) -> torch.Tensor:
        nonlocal exact_core_call_count
        exact_core_call_count += 1
        return original_exact_core(monomials, batch_shape)

    monkeypatch.setattr(
        predicates,
        "_exact_binary64_monomial_sum_sign",
        _record_exact_core_call,
    )
    _, first, second = next(
        case
        for case in _DOT_CASES
        if case[0] == "gradual_underflow_counterexample"
    )
    sign = predicates.dot_sign(
        torch.tensor(first, dtype=FIXED_DOUBLE),
        torch.tensor(second, dtype=FIXED_DOUBLE),
    )

    assert int(sign.item()) == 1
    assert exact_core_call_count == 1


def test_dot_sign_retains_meta_structure() -> None:
    """
    Meta 推导只保留广播形状与 int8 dtype，不执行值依赖整数核
    """

    first = torch.empty((2, 1, 3), dtype=FIXED_DOUBLE, device="meta")
    second = torch.empty((1, 4, 3), dtype=FIXED_DOUBLE, device="meta")
    sign = dot_sign(first, second)
    assert sign.device.type == "meta"
    assert sign.dtype is torch.int8
    assert sign.shape == (2, 4)


@pytest.mark.parametrize(
    (
        "case_name",
        "quadratic_coefficient",
        "linear_coefficient",
        "constant_coefficient",
    ),
    _DISCRIMINANT_CASES,
    ids=tuple(case[0] for case in _DISCRIMINANT_CASES),
)
def test_discriminant_sign_matches_oracle(
    case_name: str,
    quadratic_coefficient: float,
    linear_coefficient: float,
    constant_coefficient: float,
) -> None:
    """
    判别式符号与独立有理 oracle 一致
    """

    sign = quadratic_discriminant_sign(
        torch.tensor(quadratic_coefficient, dtype=FIXED_DOUBLE),
        torch.tensor(linear_coefficient, dtype=FIXED_DOUBLE),
        torch.tensor(constant_coefficient, dtype=FIXED_DOUBLE),
    )
    _assert_predicate_result(
        predicate_name="quadratic_discriminant_sign",
        case_name=case_name,
        input_groups=(
            (quadratic_coefficient,),
            (linear_coefficient,),
            (constant_coefficient,),
        ),
        oracle_sign=_oracle_discriminant(
            quadratic_coefficient,
            linear_coefficient,
            constant_coefficient,
        ),
        actual_sign=sign,
        device_label="cpu",
    )


@pytest.mark.parametrize(
    ("case_name", "reference", "squared_factor", "extra_factor"),
    _ROOT_FACTOR_CASES,
    ids=tuple(case[0] for case in _ROOT_FACTOR_CASES),
)
def test_squared_reference_minus_squared_factor_extra_factor_sign_matches_oracle(
    case_name: str,
    reference: float,
    squared_factor: float,
    extra_factor: float,
) -> None:
    """
    ``reference² - squared_factor²·extra`` 精确符号与独立有理 oracle 一致
    """
    sign = squared_reference_minus_squared_factor_extra_factor_sign(
        torch.tensor(reference, dtype=FIXED_DOUBLE),
        torch.tensor(squared_factor, dtype=FIXED_DOUBLE),
        torch.tensor(extra_factor, dtype=FIXED_DOUBLE),
    )
    _assert_predicate_result(
        predicate_name=(
            "squared_reference_minus_squared_factor_extra_factor_sign"
        ),
        case_name=case_name,
        input_groups=((reference,), (squared_factor,), (extra_factor,)),
        oracle_sign=(
            _oracle_squared_reference_minus_squared_factor_times_extra_factor_sign(
                reference,
                squared_factor,
                extra_factor,
            )
        ),
        actual_sign=sign,
        device_label="cpu",
    )


def test_squared_reference_minus_squared_factor_extra_factor_sign_runs_on_meta(
) -> None:
    """
    meta 设备上原语返回同形状 int8 张量
    """
    reference = torch.tensor(0.0, dtype=FIXED_DOUBLE, device="meta")
    squared_factor = torch.tensor(0.0, dtype=FIXED_DOUBLE, device="meta")
    extra = torch.empty((), dtype=FIXED_DOUBLE, device="meta")
    sign = squared_reference_minus_squared_factor_extra_factor_sign(
        reference,
        squared_factor,
        extra,
    )
    assert sign.shape == ()
    assert sign.dtype == torch.int8
    assert sign.device.type == "meta"


@pytest.mark.parametrize(
    ("case_name", "reference", "components"),
    _SQUARED_NORM_CASES,
    ids=tuple(case[0] for case in _SQUARED_NORM_CASES),
)
def test_scaled_squared_norm_difference_sign_matches_oracle(
    case_name: str,
    reference: float,
    components: tuple[float, ...],
) -> None:
    """
    缩放平方范数差符号与独立 oracle 一致（含大坐标不溢出）
    """

    sign = scaled_squared_norm_difference_sign(
        torch.tensor(reference, dtype=FIXED_DOUBLE),
        torch.tensor(components, dtype=FIXED_DOUBLE),
    )
    _assert_predicate_result(
        predicate_name="scaled_squared_norm_difference_sign",
        case_name=case_name,
        input_groups=((reference,), components),
        oracle_sign=_oracle_squared_norm_difference_sign(reference, components),
        actual_sign=sign,
        device_label="cpu",
    )


@pytest.mark.parametrize(
    ("case_name", "first", "second", "third"),
    _TRIPLE_PRODUCT_CASES,
    ids=tuple(case[0] for case in _TRIPLE_PRODUCT_CASES),
)
def test_triple_product_sign_matches_orientation(
    case_name: str,
    first: tuple[float, ...],
    second: tuple[float, ...],
    third: tuple[float, ...],
) -> None:
    """
    右手系为 +1、左手系为 -1、共面退化为 0
    """

    sign = triple_product_sign(
        torch.tensor(first, dtype=FIXED_DOUBLE),
        torch.tensor(second, dtype=FIXED_DOUBLE),
        torch.tensor(third, dtype=FIXED_DOUBLE),
    )
    _assert_predicate_result(
        predicate_name="triple_product_sign",
        case_name=case_name,
        input_groups=(first, second, third),
        oracle_sign=_oracle_triple_product(first, second, third),
        actual_sign=sign,
        device_label="cpu",
    )


def test_quotient_sign_without_division() -> None:
    """
    num/den 符号不经除法；num=0 与 den=0 均返回 0
    """

    positive = quotient_sign(
        torch.tensor(3.0, dtype=FIXED_DOUBLE),
        torch.tensor(2.0, dtype=FIXED_DOUBLE),
    )
    assert int(positive.item()) == 1
    negative = quotient_sign(
        torch.tensor(3.0, dtype=FIXED_DOUBLE),
        torch.tensor(-2.0, dtype=FIXED_DOUBLE),
    )
    assert int(negative.item()) == -1
    zero_num = quotient_sign(
        torch.tensor(0.0, dtype=FIXED_DOUBLE),
        torch.tensor(2.0, dtype=FIXED_DOUBLE),
    )
    assert int(zero_num.item()) == 0
    zero_den = quotient_sign(
        torch.tensor(3.0, dtype=FIXED_DOUBLE),
        torch.tensor(0.0, dtype=FIXED_DOUBLE),
    )
    assert int(zero_den.item()) == 0


def test_quotient_sign_keeps_factor_sign_across_full_exponent_spread() -> None:
    """
    商符号只读两个原始因子；即使浮点乘积下溢也不依赖求和型精确核
    """

    smallest_positive = math.ldexp(1.0, -1074)
    largest_negative = -math.nextafter(math.inf, 0.0)
    sign = quotient_sign(
        torch.tensor(smallest_positive, dtype=FIXED_DOUBLE),
        torch.tensor(largest_negative, dtype=FIXED_DOUBLE),
    )
    assert int(sign.item()) == -1


def test_remaining_predicates_preserve_broadcast_batch_shapes() -> None:
    """
    四类收缩后的判定保留各自广播批形状与 int8 结果
    """

    triple_signs = triple_product_sign(
        torch.tensor([[[1.0, 0.0, 0.0]], [[0.0, 1.0, 0.0]]], dtype=FIXED_DOUBLE),
        torch.tensor([[[0.0, 1.0, 0.0]], [[0.0, 0.0, 1.0]]], dtype=FIXED_DOUBLE),
        torch.tensor(
            [[[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]],
            dtype=FIXED_DOUBLE,
        ),
    )
    norm_signs = scaled_squared_norm_difference_sign(
        torch.tensor([[5.0], [13.0]], dtype=FIXED_DOUBLE),
        torch.tensor([[[3.0, 4.0], [5.0, 12.0], [0.0, 0.0]]], dtype=FIXED_DOUBLE),
    )
    discriminant_signs = quadratic_discriminant_sign(
        torch.tensor([[1.0], [2.0]], dtype=FIXED_DOUBLE),
        torch.tensor([[2.0, 3.0, 4.0]], dtype=FIXED_DOUBLE),
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
    )
    factor_signs = squared_reference_minus_squared_factor_extra_factor_sign(
        torch.tensor([[6.0], [7.0]], dtype=FIXED_DOUBLE),
        torch.tensor([[3.0, 2.0, 1.0]], dtype=FIXED_DOUBLE),
        torch.tensor(4.0, dtype=FIXED_DOUBLE),
    )

    for signs in (
        triple_signs,
        norm_signs,
        discriminant_signs,
        factor_signs,
    ):
        assert signs.shape == (2, 3)
        assert signs.dtype == torch.int8


def test_dot_family_reports_batched_broadcast_results_through_diagnostic() -> None:
    """
    点积族的批量广播逐通道经过统一可复现诊断
    """

    first_vectors = (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    )
    second_vectors = (
        (1.0, 0.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, 1.0, 0.0),
    )
    signs = dot_sign(
        torch.tensor(first_vectors, dtype=FIXED_DOUBLE).unsqueeze(1),
        torch.tensor(second_vectors, dtype=FIXED_DOUBLE).unsqueeze(0),
    )

    assert signs.shape == (2, 3)
    for first_index, first in enumerate(first_vectors):
        for second_index, second in enumerate(second_vectors):
            _assert_predicate_result(
                predicate_name="dot_sign",
                case_name=f"broadcast_{first_index}_{second_index}",
                input_groups=(first, second),
                oracle_sign=_oracle_dot(first, second),
                actual_sign=signs[first_index, second_index],
                device_label="cpu",
            )


def test_remaining_predicates_preserve_meta_structure() -> None:
    """
    四类收缩后的判定在 Meta 上只保留广播形状与 int8 结构
    """

    vector = torch.empty((2, 1, 3), dtype=FIXED_DOUBLE, device="meta")
    broadcast_vector = torch.empty((1, 4, 3), dtype=FIXED_DOUBLE, device="meta")
    scalar = torch.empty((2, 1), dtype=FIXED_DOUBLE, device="meta")
    broadcast_scalar = torch.empty((1, 4), dtype=FIXED_DOUBLE, device="meta")
    signs = (
        triple_product_sign(vector, broadcast_vector, broadcast_vector),
        scaled_squared_norm_difference_sign(scalar, broadcast_vector),
        quadratic_discriminant_sign(
            scalar,
            broadcast_scalar,
            broadcast_scalar,
        ),
        squared_reference_minus_squared_factor_extra_factor_sign(
            scalar,
            broadcast_scalar,
            broadcast_scalar,
        ),
    )

    for sign in signs:
        assert sign.device.type == "meta"
        assert sign.dtype == torch.int8
        assert sign.shape == (2, 4)


def test_remaining_predicates_enter_exact_core_once_per_ambiguous_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    模糊批一次进入精确符号核
    """

    import chromatix_next._numerics._certified_predicates as predicates

    exact_core_call_count = 0

    def _record_exact_core_call(
        _monomials: object,
        batch_shape: tuple[int, ...],
    ) -> torch.Tensor:
        nonlocal exact_core_call_count
        exact_core_call_count += 1
        return torch.zeros(batch_shape, dtype=torch.int8)

    monkeypatch.setattr(
        predicates,
        "_exact_binary64_monomial_sum_sign",
        _record_exact_core_call,
    )
    first_axis = torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE)
    second_axis = torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE)
    predicates.triple_product_sign(
        first_axis,
        second_axis,
        first_axis + second_axis,
    )
    predicates.scaled_squared_norm_difference_sign(
        torch.tensor(5.0, dtype=FIXED_DOUBLE),
        torch.tensor([3.0, 4.0], dtype=FIXED_DOUBLE),
    )
    predicates.quadratic_discriminant_sign(
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
        torch.tensor(2.0, dtype=FIXED_DOUBLE),
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
    )
    predicates.squared_reference_minus_squared_factor_extra_factor_sign(
        torch.tensor(6.0, dtype=FIXED_DOUBLE),
        torch.tensor(3.0, dtype=FIXED_DOUBLE),
        torch.tensor(4.0, dtype=FIXED_DOUBLE),
    )

    assert exact_core_call_count == 4


def test_remaining_predicates_keep_ordinary_batches_on_fast_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    四类普通批不进入整数肢核
    """

    import chromatix_next._numerics._certified_predicates as predicates

    was_exact_core_called = False

    def _record_exact_core_call(
        *_args: object,
        **_kwargs: object,
    ) -> torch.Tensor:
        nonlocal was_exact_core_called
        was_exact_core_called = True
        return torch.empty((), dtype=torch.int8)

    monkeypatch.setattr(
        predicates,
        "_exact_binary64_monomial_sum_sign",
        _record_exact_core_call,
    )
    predicates.triple_product_sign(
        torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
        torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE),
        torch.tensor([0.0, 0.0, 1.0], dtype=FIXED_DOUBLE),
    )
    predicates.scaled_squared_norm_difference_sign(
        torch.tensor(5.0, dtype=FIXED_DOUBLE),
        torch.tensor([1.0, 1.0], dtype=FIXED_DOUBLE),
    )
    predicates.quadratic_discriminant_sign(
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
        torch.tensor(3.0, dtype=FIXED_DOUBLE),
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
    )
    predicates.squared_reference_minus_squared_factor_extra_factor_sign(
        torch.tensor(3.0, dtype=FIXED_DOUBLE),
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
    )

    assert not was_exact_core_called


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is unavailable")
def test_remaining_exact_predicate_families_match_oracles_on_cuda() -> None:
    """
    五类整数肢精确回退在原生 CUDA 上与独立有理 oracle 一致
    """

    device = torch.device("cuda")
    for case_name, first, second in _DOT_CASES:
        sign = dot_sign(
            torch.tensor(first, dtype=FIXED_DOUBLE, device=device),
            torch.tensor(second, dtype=FIXED_DOUBLE, device=device),
        )
        _assert_predicate_result(
            predicate_name="dot_sign",
            case_name=case_name,
            input_groups=(first, second),
            oracle_sign=_oracle_dot(first, second),
            actual_sign=sign,
            device_label="native_cuda",
        )
    for case_name, first, second, third in _TRIPLE_PRODUCT_CASES:
        sign = triple_product_sign(
            torch.tensor(first, dtype=FIXED_DOUBLE, device=device),
            torch.tensor(second, dtype=FIXED_DOUBLE, device=device),
            torch.tensor(third, dtype=FIXED_DOUBLE, device=device),
        )
        _assert_predicate_result(
            predicate_name="triple_product_sign",
            case_name=case_name,
            input_groups=(first, second, third),
            oracle_sign=_oracle_triple_product(first, second, third),
            actual_sign=sign,
            device_label="native_cuda",
        )
    for case_name, reference, components in _SQUARED_NORM_CASES:
        sign = scaled_squared_norm_difference_sign(
            torch.tensor(reference, dtype=FIXED_DOUBLE, device=device),
            torch.tensor(components, dtype=FIXED_DOUBLE, device=device),
        )
        _assert_predicate_result(
            predicate_name="scaled_squared_norm_difference_sign",
            case_name=case_name,
            input_groups=((reference,), components),
            oracle_sign=_oracle_squared_norm_difference_sign(reference, components),
            actual_sign=sign,
            device_label="native_cuda",
        )
    for (
        case_name,
        quadratic_coefficient,
        linear_coefficient,
        constant_coefficient,
    ) in _DISCRIMINANT_CASES:
        sign = quadratic_discriminant_sign(
            torch.tensor(quadratic_coefficient, dtype=FIXED_DOUBLE, device=device),
            torch.tensor(linear_coefficient, dtype=FIXED_DOUBLE, device=device),
            torch.tensor(constant_coefficient, dtype=FIXED_DOUBLE, device=device),
        )
        _assert_predicate_result(
            predicate_name="quadratic_discriminant_sign",
            case_name=case_name,
            input_groups=(
                (quadratic_coefficient,),
                (linear_coefficient,),
                (constant_coefficient,),
            ),
            oracle_sign=_oracle_discriminant(
                quadratic_coefficient,
                linear_coefficient,
                constant_coefficient,
            ),
            actual_sign=sign,
            device_label="native_cuda",
        )
    for case_name, reference, squared_factor, extra_factor in _ROOT_FACTOR_CASES:
        sign = squared_reference_minus_squared_factor_extra_factor_sign(
            torch.tensor(reference, dtype=FIXED_DOUBLE, device=device),
            torch.tensor(squared_factor, dtype=FIXED_DOUBLE, device=device),
            torch.tensor(extra_factor, dtype=FIXED_DOUBLE, device=device),
        )
        _assert_predicate_result(
            predicate_name=(
                "squared_reference_minus_squared_factor_extra_factor_sign"
            ),
            case_name=case_name,
            input_groups=((reference,), (squared_factor,), (extra_factor,)),
            oracle_sign=(
                _oracle_squared_reference_minus_squared_factor_times_extra_factor_sign(
                    reference,
                    squared_factor,
                    extra_factor,
                )
            ),
            actual_sign=sign,
            device_label="native_cuda",
        )


def test_exact_fallback_is_exercised_on_exact_cancellation() -> None:
    """
    精确回退被实际触发（完全平方判别式浮点恰为 0）后仍返回精确 0
    """

    sign = quadratic_discriminant_sign(
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
        torch.tensor(2.0, dtype=FIXED_DOUBLE),
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
    )
    assert int(sign.item()) == 0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is unavailable")
def test_classification_is_identical_on_cuda() -> None:
    """
    CPU 与 CUDA 分类逐元素一致（binary64 IEEE 算术确定）
    """

    cases = torch.tensor(
        [[1.0, 1.0, 0.0, 1.0, -1.0, 0.0], [1.0, 2.0, 1.0, 0.0, 0.0, -1.0]],
        dtype=FIXED_DOUBLE,
    )
    cpu = dot_sign(cases, cases)
    cuda = dot_sign(cases.cuda(), cases.cuda())
    assert torch.equal(cpu, cuda.cpu())


def test_stranded_residual_cases_locked() -> None:
    """
    跨单项相消后残差留在中间分量；只读末位会错误返回 0
    """

    # a·b = 1 - 1 + 2^-60 = 2^-60 > 0；末位读出会因前两项相消误返回 0
    assert int(
        dot_sign(
            torch.tensor([1.0, 1.0, 2.0 ** -60], dtype=FIXED_DOUBLE),
            torch.tensor([1.0, -1.0, 1.0], dtype=FIXED_DOUBLE),
        ).item()
    ) == 1
    # R² − ‖v‖² = 1 − (1 + 2^-120) = -2^-120 < 0
    assert int(
        scaled_squared_norm_difference_sign(
            torch.tensor(1.0, dtype=FIXED_DOUBLE),
            torch.tensor([1.0, 2.0 ** -60], dtype=FIXED_DOUBLE),
        ).item()
    ) == -1


def test_near_tangent_non_axis_aligned_discriminant_is_positive() -> None:
    """
    非轴对齐近切线判别式的精确符号为 +1，不是 0
    """

    quadratic_coefficient = 2.329369856604598
    linear_coefficient = 8.217574209508822
    constant_coefficient = 7.2475100612851335
    sign = quadratic_discriminant_sign(
        torch.tensor(quadratic_coefficient, dtype=FIXED_DOUBLE),
        torch.tensor(linear_coefficient, dtype=FIXED_DOUBLE),
        torch.tensor(constant_coefficient, dtype=FIXED_DOUBLE),
    )
    assert int(sign.item()) == 1
    assert _oracle_discriminant(
        quadratic_coefficient,
        linear_coefficient,
        constant_coefficient,
    ) == 1


@pytest.mark.parametrize("lane_count", (0, 1, 511, 512, 513))
def test_dot_meta_workspace_conservatively_covers_cpu_peak(lane_count: int) -> None:
    """
    点积谓词的 Meta 结构工作集覆盖 CPU 模糊通道存储峰值
    """

    with _execution_memory._trace_storage_lifetimes() as cpu_trace:
        first_vector, second_vector, _first_scalar, _second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("cpu"),
            )
        )
        cpu_result = dot_sign(first_vector, second_vector)
        cpu_trace.observe_value(cpu_result)
    with _execution_memory._trace_storage_lifetimes() as meta_trace:
        first_vector, second_vector, _first_scalar, _second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("meta"),
            )
        )
        meta_result = dot_sign(first_vector, second_vector)
        meta_trace.observe_value(meta_result)

    assert meta_result.dtype is torch.int8
    assert meta_result.shape == cpu_result.shape
    assert meta_trace.peak_bytes >= cpu_trace.peak_bytes


@pytest.mark.parametrize("lane_count", (0, 1, 511, 512, 513))
def test_triple_product_meta_workspace_conservatively_covers_cpu_peak(
    lane_count: int,
) -> None:
    """
    三重积谓词的 Meta 结构工作集覆盖 CPU 模糊通道存储峰值
    """

    with _execution_memory._trace_storage_lifetimes() as cpu_trace:
        first_vector, second_vector, _first_scalar, _second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("cpu"),
            )
        )
        cpu_result = triple_product_sign(
            first_vector,
            second_vector,
            first_vector,
        )
        cpu_trace.observe_value(cpu_result)
    with _execution_memory._trace_storage_lifetimes() as meta_trace:
        first_vector, second_vector, _first_scalar, _second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("meta"),
            )
        )
        meta_result = triple_product_sign(
            first_vector,
            second_vector,
            first_vector,
        )
        meta_trace.observe_value(meta_result)

    assert meta_result.dtype is torch.int8
    assert meta_result.shape == cpu_result.shape
    assert meta_trace.peak_bytes >= cpu_trace.peak_bytes


@pytest.mark.parametrize("lane_count", (0, 1, 511, 512, 513))
def test_squared_norm_difference_meta_workspace_covers_cpu_peak(
    lane_count: int,
) -> None:
    """
    平方范数差谓词的 Meta 结构工作集覆盖 CPU 模糊通道存储峰值
    """

    with _execution_memory._trace_storage_lifetimes() as cpu_trace:
        _first_vector, second_vector, first_scalar, _second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("cpu"),
            )
        )
        cpu_result = scaled_squared_norm_difference_sign(
            first_scalar,
            second_vector,
        )
        cpu_trace.observe_value(cpu_result)
    with _execution_memory._trace_storage_lifetimes() as meta_trace:
        _first_vector, second_vector, first_scalar, _second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("meta"),
            )
        )
        meta_result = scaled_squared_norm_difference_sign(
            first_scalar,
            second_vector,
        )
        meta_trace.observe_value(meta_result)

    assert meta_result.dtype is torch.int8
    assert meta_result.shape == cpu_result.shape
    assert meta_trace.peak_bytes >= cpu_trace.peak_bytes


@pytest.mark.parametrize("lane_count", (0, 1, 511, 512, 513))
def test_root_factor_meta_workspace_conservatively_covers_cpu_peak(
    lane_count: int,
) -> None:
    """
    根因子谓词的 Meta 结构工作集覆盖 CPU 模糊通道存储峰值
    """

    with _execution_memory._trace_storage_lifetimes() as cpu_trace:
        _first_vector, _second_vector, first_scalar, second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("cpu"),
            )
        )
        cpu_result = squared_reference_minus_squared_factor_extra_factor_sign(
            first_scalar,
            second_scalar,
            first_scalar,
        )
        cpu_trace.observe_value(cpu_result)
    with _execution_memory._trace_storage_lifetimes() as meta_trace:
        _first_vector, _second_vector, first_scalar, second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("meta"),
            )
        )
        meta_result = squared_reference_minus_squared_factor_extra_factor_sign(
            first_scalar,
            second_scalar,
            first_scalar,
        )
        meta_trace.observe_value(meta_result)

    assert meta_result.dtype is torch.int8
    assert meta_result.shape == cpu_result.shape
    assert meta_trace.peak_bytes >= cpu_trace.peak_bytes


@pytest.mark.parametrize("lane_count", (0, 1, 511, 512, 513))
def test_discriminant_meta_workspace_conservatively_covers_cpu_peak(
    lane_count: int,
) -> None:
    """
    判别式谓词的 Meta 结构工作集覆盖 CPU 模糊通道存储峰值
    """

    with _execution_memory._trace_storage_lifetimes() as cpu_trace:
        _first_vector, _second_vector, first_scalar, second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("cpu"),
            )
        )
        cpu_result = quadratic_discriminant_sign(
            first_scalar,
            second_scalar,
            first_scalar,
        )
        cpu_trace.observe_value(cpu_result)
    with _execution_memory._trace_storage_lifetimes() as meta_trace:
        _first_vector, _second_vector, first_scalar, second_scalar = (
            _zero_predicate_operands(
                lane_count=lane_count,
                device=torch.device("meta"),
            )
        )
        meta_result = quadratic_discriminant_sign(
            first_scalar,
            second_scalar,
            first_scalar,
        )
        meta_trace.observe_value(meta_result)

    assert meta_result.dtype is torch.int8
    assert meta_result.shape == cpu_result.shape
    assert meta_trace.peak_bytes >= cpu_trace.peak_bytes


def test_meta_float32_predicates_retain_structural_shape() -> None:
    """
    float32 Meta 直接推导五类谓词的形状与工作集，不构成科学精度准入
    """

    first_vector, second_vector, first_scalar, second_scalar = (
        _zero_predicate_operands(
            lane_count=513,
            device=torch.device("meta"),
            dtype=torch.float32,
        )
    )
    results = (
        dot_sign(first_vector, second_vector),
        triple_product_sign(first_vector, second_vector, first_vector),
        scaled_squared_norm_difference_sign(first_scalar, second_vector),
        squared_reference_minus_squared_factor_extra_factor_sign(
            first_scalar,
            second_scalar,
            first_scalar,
        ),
        quadratic_discriminant_sign(
            first_scalar,
            second_scalar,
            first_scalar,
        ),
    )

    for result in results:
        assert result.device.type == "meta"
        assert result.dtype is torch.int8
        assert result.shape == (3, 171)

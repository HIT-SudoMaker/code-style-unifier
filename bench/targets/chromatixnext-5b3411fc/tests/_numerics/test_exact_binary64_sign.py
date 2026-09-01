from __future__ import annotations

from fractions import Fraction
import math

import pytest
import torch

from chromatix_next._numerics._certified_predicates import dot_sign
from chromatix_next._numerics._exact_binary64_sign import (
    _exact_binary64_monomial_sum_sign,
)

FIXED_DOUBLE = torch.float64


def _oracle_monomial_sum(
    monomials: tuple[tuple[int, tuple[float, ...]], ...],
) -> int:
    # 直接以 binary64 的有理数值求单项式和，不复用生产整数肢实现
    exact_total = Fraction(0)
    for coefficient, factors in monomials:
        exact_product = Fraction(coefficient)
        for factor in factors:
            exact_product *= _as_fraction(factor)
        exact_total += exact_product
    return _sign_of(exact_total)


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


@pytest.mark.parametrize(
    ("case_name", "monomials"),
    (
        (
            "exact_zero",
            ((1, (1.0, 1.0)), (-1, (1.0, 1.0))),
        ),
        (
            "adjacent_binary64",
            (
                (1, (math.nextafter(1.0, math.inf), 1.0)),
                (-1, (1.0, 1.0)),
            ),
        ),
        (
            "subnormal_product",
            ((1, (math.ulp(0.0), math.ulp(0.0))),),
        ),
        (
            "degree_three_cancellation",
            (
                (1, (1.0, 1.0, math.nextafter(1.0, math.inf))),
                (-1, (1.0, 1.0, 1.0)),
            ),
        ),
        (
            "degree_seven_cancellation",
            (
                (
                    1,
                    (
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        math.nextafter(1.0, math.inf),
                    ),
                ),
                (-1, (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)),
            ),
        ),
        (
            "magnitude_four_coefficient",
            ((1, (2.0, 2.0)), (-4, (1.0, 1.0))),
        ),
        (
            "wide_exponent_spread",
            ((1, (2.0**900, 2.0**-900)), (-1, (1.0, 1.0))),
        ),
    ),
)
def test_exact_binary64_core_matches_rational_oracle(
    case_name: str,
    monomials: tuple[tuple[int, tuple[float, ...]], ...],
) -> None:
    """
    闭合二次/三次整数肢核覆盖等式、邻值、次正规、宽指数与负四系数
    """

    tensor_monomials = tuple(
        (
            coefficient,
            tuple(torch.tensor(factor, dtype=FIXED_DOUBLE) for factor in factors),
        )
        for coefficient, factors in monomials
    )
    actual_sign = int(
        _exact_binary64_monomial_sum_sign(tensor_monomials, ()).item()
    )
    expected_sign = _oracle_monomial_sum(monomials)
    flattened_values = tuple(
        factor
        for _coefficient, factors in monomials
        for factor in factors
    )
    assert actual_sign == expected_sign, (
        "predicate=exact_binary64_monomial_sum_sign, "
        f"case={case_name}, bits={_binary64_bit_patterns(flattened_values)}, "
        f"oracle={expected_sign}, actual={actual_sign}, device=cpu"
    )


def test_exact_binary64_core_preserves_broadcast_batch_shape() -> None:
    """
    精确核沿批形状广播，返回同形状 int8 符号
    """

    first_factors = torch.tensor([[1.0], [-1.0]], dtype=FIXED_DOUBLE)
    second_factors = torch.tensor([[2.0, -3.0]], dtype=FIXED_DOUBLE)
    signs = _exact_binary64_monomial_sum_sign(
        ((1, (first_factors, second_factors)),),
        (2, 2),
    )
    assert signs.dtype is torch.int8
    assert signs.shape == (2, 2)
    assert torch.equal(
        signs,
        torch.tensor([[1, -1], [-1, 1]], dtype=torch.int8),
    )


def test_exact_binary64_core_preserves_empty_batch_shape() -> None:
    """
    零通道批返回同形状 int8 空张量，不进入分块拼接
    """

    empty_factors = torch.empty((0, 3), dtype=FIXED_DOUBLE)
    signs = _exact_binary64_monomial_sum_sign(
        ((1, (empty_factors, empty_factors)),),
        (0, 3),
    )
    assert signs.dtype is torch.int8
    assert signs.shape == (0, 3)
    assert signs.numel() == 0


def test_exact_binary64_core_crosses_chunk_boundary() -> None:
    """
    五百一十三通道跨过固定分块边界且逐通道符号不漂移
    """

    first_factors = torch.ones(513, dtype=FIXED_DOUBLE)
    second_factors = torch.where(
        torch.arange(513) % 2 == 0,
        torch.ones(513, dtype=FIXED_DOUBLE),
        -torch.ones(513, dtype=FIXED_DOUBLE),
    )
    signs = _exact_binary64_monomial_sum_sign(
        ((1, (first_factors, second_factors)),),
        (513,),
    )
    assert torch.equal(signs, second_factors.to(torch.int8))


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is unavailable")
def test_exact_core_and_dot_counterexample_match_on_cuda() -> None:
    """
    CUDA 使用同一设备本地整数核，反例结果与 CPU 一致且不跳过
    """

    diagonal_component = math.sqrt(0.5)
    tiny_component = 2.0**-600
    first = torch.tensor(
        [diagonal_component, diagonal_component, tiny_component],
        dtype=FIXED_DOUBLE,
    )
    second = torch.tensor(
        [
            diagonal_component,
            -diagonal_component,
            math.nextafter(tiny_component, math.inf),
        ],
        dtype=FIXED_DOUBLE,
    )
    cpu_sign = dot_sign(first, second)
    cuda_sign = dot_sign(first.cuda(), second.cuda())
    assert int(cpu_sign.item()) == 1
    assert torch.equal(cuda_sign.cpu(), cpu_sign)


@pytest.mark.parametrize(
    ("batch_shape", "factor_shapes"),
    (
        ((), ((), ())),
        ((2, 3), ((2, 1), (1, 3))),
        ((0, 3), ((0, 1), (1, 3))),
    ),
)
def test_private_exact_core_reserves_float32_meta_structure(
    batch_shape: tuple[int, ...],
    factor_shapes: tuple[tuple[int, ...], tuple[int, ...]],
) -> None:
    """
    私有精确核对标量、广播与空批 float32 Meta 返回结构 int8
    """

    factors = tuple(
        torch.empty(shape, dtype=torch.float32, device="meta")
        for shape in factor_shapes
    )
    result = _exact_binary64_monomial_sum_sign(
        ((1, factors),),
        batch_shape,
    )

    assert result.device.type == "meta"
    assert result.dtype is torch.int8
    assert result.shape == batch_shape


def test_private_exact_core_rejects_real_float32() -> None:
    """
    Meta 的结构宽容不放行真实 float32 精确科学执行
    """

    factor = torch.ones(2, dtype=torch.float32)
    with pytest.raises(AssertionError):
        _exact_binary64_monomial_sum_sign(
            ((1, (factor, factor)),),
            (2,),
        )


def test_private_meta_validates_contract_before_workspace_reservation() -> None:
    """
    Meta 预留工作集前仍拒绝非法系数、次数、设备与批形状
    """

    meta_factor = torch.ones(2, dtype=torch.float32, device="meta")
    cpu_factor = torch.ones(2, dtype=torch.float32)
    invalid_calls = (
        (((2, (meta_factor, meta_factor)),), (2,)),
        (((1, (meta_factor,)),), (2,)),
        (((1, (meta_factor, cpu_factor)),), (2,)),
        (((1, (meta_factor, meta_factor)),), (3,)),
    )
    for monomials, batch_shape in invalid_calls:
        with pytest.raises(AssertionError):
            _exact_binary64_monomial_sum_sign(
                monomials,
                batch_shape,
            )

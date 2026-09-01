
from __future__ import annotations

import cmath
import math

import pytest
import torch

from chromatix_next._numerics.complex_phase import _unit_phasor_from_cycles

_TAU = 2.0 * math.pi


def _independent_phasor_from_cycles(cycle: float) -> complex:
    fraction = cycle - math.floor(cycle)
    return cmath.exp(1j * _TAU * fraction)


def test_exact_rational_cycles_match_independent_reference() -> None:
    """
    0、±1/4、±1/2、整数周期与独立 cmath 参照一致到 fp64 尾数
    """

    cycles_values = (
        0.0,
        0.25,
        -0.25,
        0.5,
        -0.5,
        1.0,
        -1.0,
        3.0,
        -7.0,
        0.75,
        -0.75,
    )
    cycles = torch.tensor(cycles_values, dtype=torch.float64)
    actual = _unit_phasor_from_cycles(cycles)
    expected = torch.tensor(
        [_independent_phasor_from_cycles(value) for value in cycles_values],
        dtype=torch.complex128,
    )
    assert actual.dtype is torch.complex128
    assert torch.allclose(actual, expected, rtol=1.0e-12, atol=1.0e-12)


@pytest.mark.parametrize("cycle", (0.25, -0.25, 0.5, -0.5, 0.75))
def test_half_and_quarter_cycle_tie_is_representation_invariant(
    cycle: float,
) -> None:
    """
    半周期 tie：c 与 c ± 0.5·(整数差) 在两种归约表示下给出同一 phasor
    """

    base = torch.tensor([cycle], dtype=torch.float64)
    shifted = torch.tensor([cycle + 5.0], dtype=torch.float64)
    neg_shifted = torch.tensor([cycle - 3.0], dtype=torch.float64)
    first = _unit_phasor_from_cycles(base)
    second = _unit_phasor_from_cycles(shifted)
    third = _unit_phasor_from_cycles(neg_shifted)
    assert torch.equal(first, second)
    assert torch.equal(first, third)


def test_huge_cycles_retain_fractional_phasor() -> None:
    """
    1e15 + 0.25 周期仍保留四分之一周期 phasor，不被巨弧度尾数吞掉
    """

    huge = torch.tensor(
        [1.0e15 + 0.25, 1.0e15 - 0.25, 1.0e15 + 0.5],
        dtype=torch.float64,
    )
    actual = _unit_phasor_from_cycles(huge)
    expected = torch.tensor(
        [
            _independent_phasor_from_cycles(0.25),
            _independent_phasor_from_cycles(-0.25),
            _independent_phasor_from_cycles(0.5),
        ],
        dtype=torch.complex128,
    )
    assert torch.allclose(actual, expected, rtol=0.0, atol=1.0e-10)


def test_reduction_boundary_values_handle_integer_and_half_cycles() -> None:
    """
    整数与半周期边界、负周期靠近边界的若干样本保留正确 phasor
    """

    cycles_values = (
        1.0 - 1.0e-12,
        1.0 + 1.0e-12,
        0.5 - 1.0e-12,
        0.5 + 1.0e-12,
        -1.0 + 1.0e-12,
        -1.0 - 1.0e-12,
        -0.5 - 1.0e-12,
        -0.5 + 1.0e-12,
        2.5,
        -2.5,
    )
    cycles = torch.tensor(cycles_values, dtype=torch.float64)
    actual = _unit_phasor_from_cycles(cycles)
    expected = torch.tensor(
        [_independent_phasor_from_cycles(value) for value in cycles_values],
        dtype=torch.complex128,
    )
    assert torch.allclose(actual, expected, rtol=0.0, atol=2.0e-12)


@pytest.mark.parametrize(
    ("real_dtype", "complex_dtype"),
    (
        (torch.float32, torch.complex64),
        (torch.float64, torch.complex128),
    ),
)
def test_dtype_pairing_preserved(
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
) -> None:
    """
    phasor 输出始终与输入实数精度的配对复数类型一致
    """

    cycles = torch.tensor([0.0, 0.25, 0.5], dtype=real_dtype)
    actual = _unit_phasor_from_cycles(cycles)
    assert actual.dtype is complex_dtype
    assert actual.device == cycles.device


def test_analytic_derivative_away_from_discontinuities() -> None:
    """
    远离整数与半周期间断点处自洽可微，梯度匹配 ``i·tau·exp(i·tau·c)``
    """

    interior_cycles = torch.tensor(
        [0.125, 0.375, -0.125, -0.375, 0.2, -0.7, 2.3],
        dtype=torch.float64,
        requires_grad=True,
    )
    phasor = _unit_phasor_from_cycles(interior_cycles)
    # 标量损失：对每个分量与 1+0j 的内积取实部之和，等价于 Σ Re(phasor)
    loss = phasor.real.sum()
    loss.backward()
    analytic = 1j * _TAU * phasor.detach()
    actual_grad = interior_cycles.grad
    expected_grad = analytic.real
    assert actual_grad is not None
    assert torch.allclose(actual_grad, expected_grad, rtol=0.0, atol=1.0e-12)


def test_complex_derivative_via_gradcheck() -> None:
    """
    gradcheck 双向有限差分下整段内部点梯度自洽
    """

    interior_cycles = torch.tensor(
        (0.125, 0.375, -0.125, 0.2, -0.7),
        dtype=torch.float64,
        requires_grad=True,
    )

    assert torch.autograd.gradcheck(
        lambda candidate: _unit_phasor_from_cycles(candidate),
        (interior_cycles,),
        eps=1.0e-6,
        atol=1.0e-5,
        rtol=1.0e-3,
    )


@pytest.mark.parametrize("cycle_offset", (0.25, -0.25, 0.5, 0.125))
def test_phasor_value_is_periodic_under_integer_shift(cycle_offset: float) -> None:
    """
    整数平移不变：phasor(c + n) 与 phasor(c) 逐位相等
    """

    n = 5.0
    base = torch.tensor([cycle_offset], dtype=torch.float64)
    shifted = torch.tensor([cycle_offset + n], dtype=torch.float64)
    neg_shifted = torch.tensor([cycle_offset - n], dtype=torch.float64)
    assert torch.equal(
        _unit_phasor_from_cycles(base),
        _unit_phasor_from_cycles(shifted),
    )
    assert torch.equal(
        _unit_phasor_from_cycles(base),
        _unit_phasor_from_cycles(neg_shifted),
    )


def test_phasor_value_is_continuous_across_integer_boundary() -> None:
    """
    整数归约边界两侧 phasor 值连续（无离散跳变），证明归约保持 phasor 连续
    """

    # n ± ε 处 phasor 都应接近 1+0j（n 任意整数），跳变只由 ε 决定，量级 ≈ 2π·1e-9
    n = 5.0
    below = torch.tensor([n - 1.0e-9], dtype=torch.float64)
    above = torch.tensor([n + 1.0e-9], dtype=torch.float64)
    boundary_jump = (
        _unit_phasor_from_cycles(below)
        - _unit_phasor_from_cycles(above)
    ).abs()
    assert boundary_jump < 1.0e-7
    # 半周期 tie 同值：c = 0.5 与 c = -0.5（两种归约表示）phasor 逐位相等
    positive_half = torch.tensor([0.5], dtype=torch.float64)
    negative_half = torch.tensor([-0.5], dtype=torch.float64)
    assert torch.equal(
        _unit_phasor_from_cycles(positive_half),
        _unit_phasor_from_cycles(negative_half),
    )


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA evidence requires an available CUDA device",
)
def test_cuda_matches_cpu_under_fp64_budgets() -> None:
    """
    可用 Windows CUDA 与 CPU 在 fp64 预算下值与梯度都一致
    """

    cpu_cycles = torch.linspace(-3.5, 3.5, 141, dtype=torch.float64)
    cuda_cycles = cpu_cycles.cuda()
    cpu_phasor = _unit_phasor_from_cycles(cpu_cycles)
    cuda_phasor = _unit_phasor_from_cycles(cuda_cycles)
    assert torch.allclose(
        cuda_phasor.cpu(),
        cpu_phasor,
        rtol=1.0e-12,
        atol=1.0e-12,
    )

    cpu_grad_cycles = cpu_cycles.detach().clone().requires_grad_(True)
    cuda_grad_cycles = (
        cpu_cycles.detach().clone().cuda().requires_grad_(True)
    )
    _unit_phasor_from_cycles(cpu_grad_cycles).real.sum().backward()
    _unit_phasor_from_cycles(cuda_grad_cycles).real.sum().backward()
    assert cuda_grad_cycles.grad is not None
    assert cpu_grad_cycles.grad is not None
    assert torch.allclose(
        cuda_grad_cycles.grad.cpu(),
        cpu_grad_cycles.grad,
        rtol=1.0e-10,
        atol=1.0e-10,
    )

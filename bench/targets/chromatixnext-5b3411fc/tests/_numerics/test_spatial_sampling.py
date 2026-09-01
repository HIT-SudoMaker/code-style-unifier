from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.spatial_sampling import (
    isolated_destination_within_tripled_window,
    quadratic_phase_factor,
    spatial_sample_positions,
)


def test_spatial_sample_positions_match_independent_reference() -> None:
    """
    两个坐标轴按样本索引、带符号间距与首样本位置展开（固定双精度证据）

    ``_numerics.spatial_sampling`` 是物理值所有者共用的内部精度无关工具；
    保留固定双精度分支作为方程专属证据。早先的 float32 兼容性 parametrize 已删除
    （complex64/float32 兼容性证据不保留为兼容性证据）。
    """

    real_dtype = torch.float64
    position_y, position_x = spatial_sample_positions(
        sample_counts=(3, 4),
        signed_spacing=(
            torch.tensor(-0.5, dtype=torch.float64),
            torch.tensor(0.25, dtype=torch.float64),
        ),
        first_sample_position=(
            torch.tensor(1.0, dtype=torch.float64),
            torch.tensor(-0.5, dtype=torch.float64),
        ),
        reference=torch.empty((), dtype=real_dtype),
    )
    expected_y = torch.tensor(
        (1.0, 0.5, 0.0),
        dtype=real_dtype,
    )
    expected_x = torch.tensor(
        (-0.5, -0.25, 0.0, 0.25),
        dtype=real_dtype,
    )

    assert position_y.dtype is real_dtype
    assert position_x.dtype is real_dtype
    assert torch.equal(position_y, expected_y)
    assert torch.equal(position_x, expected_x)


def test_spatial_sample_positions_pass_gradient_check() -> None:
    """
    间距与首样本位置通过同一坐标展开保留完整双精度梯度
    """

    spacing_y = torch.tensor(
        -0.4,
        dtype=torch.float64,
        requires_grad=True,
    )
    origin_y = torch.tensor(
        0.6,
        dtype=torch.float64,
        requires_grad=True,
    )
    reference = torch.empty((), dtype=torch.float64)

    def _positions(
        spacing: torch.Tensor,
        origin: torch.Tensor,
    ) -> torch.Tensor:
        position_y, position_x = spatial_sample_positions(
            sample_counts=(3, 2),
            signed_spacing=(
                spacing,
                torch.tensor(0.25, dtype=torch.float64),
            ),
            first_sample_position=(
                origin,
                torch.tensor(-0.25, dtype=torch.float64),
            ),
            reference=reference,
        )
        return torch.cat((position_y, position_x))

    assert torch.autograd.gradcheck(
        _positions,
        (spacing_y, origin_y),
    )


def test_spatial_sample_positions_run_on_meta() -> None:
    """
    meta 参考张量经同一实现推导坐标形状、设备与精度
    """

    real_dtype = torch.float64
    position_y, position_x = spatial_sample_positions(
        sample_counts=(3, 5),
        signed_spacing=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        first_sample_position=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        reference=torch.empty((), dtype=real_dtype, device="meta"),
    )

    assert position_y.shape == (3,)
    assert position_x.shape == (5,)
    assert position_y.dtype is real_dtype
    assert position_x.dtype is real_dtype
    assert position_y.device.type == "meta"
    assert position_x.device.type == "meta"


def test_quadratic_phase_factor_matches_radial_phase_reference() -> None:
    """
    二次相位因子等于以弧度曲率乘径向距离平方构成的单位复相位
    """

    position_y = torch.tensor((-1.0, 2.0), dtype=torch.float64)
    position_x = torch.tensor((-2.0, 1.0), dtype=torch.float64)
    phase_curvature = torch.tensor(0.37, dtype=torch.float64)
    factor = quadratic_phase_factor(
        position_y=position_y,
        position_x=position_x,
        phase_curvature=phase_curvature,
        center_y=0.5,
        center_x=-0.25,
    )
    radius_squared = (
        position_y[:, None] - 0.5
    ).square() + (
        position_x[None, :] + 0.25
    ).square()
    expected = torch.polar(
        torch.ones_like(radius_squared),
        phase_curvature * radius_squared,
    )

    assert factor.dtype is torch.complex128
    assert torch.allclose(factor, expected, atol=1.0e-15, rtol=0.0)


def test_tripled_window_accepts_exact_boundary_and_rejects_outer_neighbour() -> None:
    """
    孤立三倍窗口包含精确等号边界与其内侧相邻值，并拒绝外侧相邻值
    """

    reference = torch.empty((), dtype=torch.float64)
    spacing = torch.tensor(1.0, dtype=torch.float64)
    source_origin = torch.tensor(-1.5, dtype=torch.float64)
    geometric_lower_boundary = torch.tensor(-6.0, dtype=torch.float64)
    admitted_tolerance = (
        8.0
        * torch.finfo(torch.float64).eps
        * torch.tensor(12.0, dtype=torch.float64)
    )
    exact_lower_boundary = geometric_lower_boundary - admitted_tolerance
    inside_neighbour = torch.nextafter(
        exact_lower_boundary,
        torch.tensor(math.inf, dtype=torch.float64),
    )
    outside_neighbour = torch.nextafter(
        exact_lower_boundary,
        torch.tensor(-math.inf, dtype=torch.float64),
    )

    def _is_inside(output_origin_y: torch.Tensor) -> bool:
        result = isolated_destination_within_tripled_window(
            input_sample_counts=(4, 4),
            input_signed_spacing=(spacing, spacing),
            input_first_sample_position=(source_origin, source_origin),
            output_sample_counts=(1, 1),
            output_signed_spacing=(spacing, spacing),
            output_first_sample_position=(output_origin_y, torch.tensor(0.0)),
            reference=reference,
        )
        return bool(result)

    assert _is_inside(exact_lower_boundary)
    assert _is_inside(inside_neighbour)
    assert not _is_inside(outside_neighbour)


from __future__ import annotations

from fractions import Fraction
import math

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics import Polarization, RayBundle, SpatialGrid, Spectrum
from chromatix_next.optics.source import CollimatedRaySource


def _unit_round_off() -> Fraction:
    return Fraction(1, 2**53)


def _gamma(operation_count: int) -> Fraction:
    unit = _unit_round_off()
    product = operation_count * unit
    return product / (1 - product)


def _authored_basis_budget() -> float:
    # authored 基底预算 ``8·gamma_3``（≈ 2.66e-15）
    return float(8 * _gamma(3))


def _direction_budget() -> float:
    # RayBundle 方向预算 ``16·gamma_5``（≈ 8.88e-15）
    return float(16 * _gamma(5))


def _next_after(value: float) -> float:
    # ``value`` 朝 +∞ 的下一个 float64 可表示值
    return torch.nextafter(
        torch.tensor(value, dtype=torch.float64),
        torch.tensor(math.inf, dtype=torch.float64),
    ).item()


def _monochromatic() -> Spectrum:
    return Spectrum.monochromatic(wavelength=2.0e-6)


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(3, 4),
        sample_spacing=(1.0, 1.0),
    )


def _near_unit_axis_over_budget() -> float:
    # 找到首个使平方范数残差 > ``8·gamma_3`` 的可表示标量 ``z``：axis = (z, 0, 0)
    budget = _authored_basis_budget()
    z = 1.0
    for _ in range(1_000):
        candidate = _next_after(z)
        if abs(candidate * candidate - 1.0) > budget:
            return candidate
        z = candidate
    boundary_error = "未找到越界 axis 标量"
    raise AssertionError(boundary_error)


class TestCollimatedSourceStrictPoseAdmission:
    """
    源姿态基按 ``8·gamma_3`` 钉边界；源专属错误身份保持
    """

    def test_axis_angle_pose_admitted_and_produces_valid_bundle(self) -> None:
        """
        sin/cos 轴角帧通过，且 forward 产出的 RayBundle 合法（源与 RayBundle 同走共享
        基底权威，无中间态）
        """

        angle = 0.23
        source = CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            ray_power=1.0,
            launch_tangent_x=(math.cos(angle), math.sin(angle), 0.0),
            launch_tangent_y=(-math.sin(angle), math.cos(angle), 0.0),
        )
        bundle = source(_grid())
        assert isinstance(bundle, RayBundle)
        # 源姿态派生方向落在 RayBundle 容差内
        direction_squared_norm = (bundle.direction * bundle.direction).sum(
            dim=-1
        )
        assert torch.all(
            (direction_squared_norm - 1.0).abs()
            <= _direction_budget() * 2.0  # 余量，仅表明远在 RayBundle 预算内
        )

    def test_outside_budget_tangent_x_fails_at_construction(self) -> None:
        """
        紧邻越界的 tangent_x 在构造期以
        ``..._tangent_x_not_unit`` 拒绝——forward 永不执行
        """

        z_over = _near_unit_axis_over_budget()
        assert z_over > 1.0  # 越界在 +∞ 方向
        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),
                polarization=Polarization.linear_x(),
                ray_power=1.0,
                launch_tangent_x=(z_over, 0.0, 0.0),
                launch_tangent_y=(0.0, 1.0, 0.0),
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_launch_tangent_x_not_unit"
        )

    def test_outside_budget_tangent_y_fails_at_construction(self) -> None:
        """
        紧邻越界的 tangent_y 在构造期以 ``..._tangent_y_not_unit`` 拒绝
        """

        z_over = _near_unit_axis_over_budget()
        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),
                polarization=Polarization.linear_x(),
                ray_power=1.0,
                launch_tangent_x=(1.0, 0.0, 0.0),
                launch_tangent_y=(0.0, z_over, 0.0),
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_launch_tangent_y_not_unit"
        )

    def test_clearly_non_unit_axis_rejected(self) -> None:
        """
        明显非单位 tangent_x（远超预算）被拒；旧 1e-6 也拒，钉住身份不变
        """

        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),
                polarization=Polarization.linear_x(),
                ray_power=1.0,
                launch_tangent_x=(2.0, 0.0, 0.0),
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_launch_tangent_x_not_unit"
        )

    def test_parallel_axes_rejected_as_not_orthogonal(self) -> None:
        """
        平行两轴以 ``..._not_orthogonal`` 拒绝
        """

        with pytest.raises(OpticalValueError) as rejected:
            CollimatedRaySource(
                spectrum=_monochromatic(),
                polarization=Polarization.linear_x(),
                ray_power=1.0,
                launch_tangent_x=(1.0, 0.0, 0.0),
                launch_tangent_y=(1.0, 0.0, 0.0),
            )
        assert (
            rejected.value.identity
            == "collimated_ray_source_launch_basis_not_orthogonal"
        )

    def test_swapped_axes_admit_and_launch_opposite_direction(self) -> None:
        """
        交换 tangent_x/tangent_y 是合法的有序正交基（发射方向取反）：
        作者通过轴序控制朝向，而非被「左手系」拒绝。认证三重积分类的是非退化（任意
        非共线正交对的叉积平方范数为正；方向由切向量顺序决定。
        """

        source = CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            ray_power=1.0,
            launch_tangent_x=(0.0, 1.0, 0.0),
            launch_tangent_y=(1.0, 0.0, 0.0),
        )
        direction = source._launch_direction()  # noqa: SLF001
        assert torch.allclose(
            direction,
            torch.tensor([0.0, 0.0, -1.0], dtype=direction.dtype),
        )


class TestSourceRayBundleAtomicAdmissibility:
    """
    源与下游 RayBundle 同走共享基底权威——无「源接纳但 RayBundle 拒绝」的中间态
    """

    def test_source_pose_budget_is_tighter_than_raybundle_direction_budget(
        self,
    ) -> None:
        """
        独立 Oracle 钉住：authored 基底预算 ``8·gamma_3`` 严格小于 RayBundle 方向预
        算 ``16·gamma_5``，故源接纳的姿态所派生的方向必落在 RayBundle 预算内。
        """

        basis_budget = 8 * _gamma(3)
        direction_budget = 16 * _gamma(5)
        assert basis_budget < direction_budget

    def test_inside_budget_source_always_yields_valid_ray_bundle(
        self,
    ) -> None:
        """
        多组合法 authored 帧（默认、轴角、归一化任意向量）经 forward 都产出合法
        RayBundle——源接纳即等于 RayBundle 接纳，不存在中间拒绝态。
        """

        angle = 0.37
        # 归一化任意向量帧：用任意单位向量作 tangent_x，再取正交切向量 tangent_y
        yv = torch.tensor((1.0, 2.0, 0.5), dtype=torch.float64)
        yv = yv / yv.norm()
        cross_with_z = torch.linalg.cross(
            yv,
            torch.tensor((0.0, 0.0, 1.0), dtype=torch.float64),
        )
        tangent_y_vec = cross_with_z / cross_with_z.norm()
        poses = (
            ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            (
                (math.cos(angle), math.sin(angle), 0.0),
                (-math.sin(angle), math.cos(angle), 0.0),
            ),
            (
                (float(yv[0]), float(yv[1]), float(yv[2])),
                (
                    float(tangent_y_vec[0]),
                    float(tangent_y_vec[1]),
                    float(tangent_y_vec[2]),
                ),
            ),
        )
        for tangent_x, tangent_y in poses:
            source = CollimatedRaySource(
                spectrum=_monochromatic(),
                polarization=Polarization.linear_x(),
                ray_power=1.0,
                launch_tangent_x=tangent_x,
                launch_tangent_y=tangent_y,
            )
            bundle = source(_grid())
            assert isinstance(bundle, RayBundle)
            # 直接证据：产出的 RayBundle 通过其全部容纳性检查（构造未抛即已通过）

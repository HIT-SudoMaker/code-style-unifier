
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.surface_geometry.sphere import sphere_encounter

FIXED_DOUBLE = torch.float64


class TestSphereEncounterRootSelection:
    """
    精确符号驱动的根选择
    """

    def test_outside_ray_picks_near_root(self) -> None:
        """
        球外指向球心时命中近根
        """

        ro = torch.tensor([[[0.0, 0.0, -5.0]]], dtype=FIXED_DOUBLE)
        rd = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=FIXED_DOUBLE)
        encounter = sphere_encounter(
            ray_origin=ro,
            ray_direction=rd,
            sphere_center=torch.tensor([0.0, 0.0, 5.0], dtype=FIXED_DOUBLE),
            sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_tangent_x=torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
            sphere_tangent_y=torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE),
            physical_radius=torch.tensor(5.0, dtype=FIXED_DOUBLE),
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        assert torch.allclose(
            encounter.distance[0, 0],
            torch.tensor(5.0, dtype=FIXED_DOUBLE),
            atol=1e-12,
        )

    def test_inside_ray_picks_far_root(self) -> None:
        """
        球内起点命中远根（凹面顺序追迹典型）
        """

        ro = torch.tensor([[[0.0, 0.0, 5.0]]], dtype=FIXED_DOUBLE)
        rd = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=FIXED_DOUBLE)
        encounter = sphere_encounter(
            ray_origin=ro,
            ray_direction=rd,
            sphere_center=torch.tensor([0.0, 0.0, 5.0], dtype=FIXED_DOUBLE),
            sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_tangent_x=torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
            sphere_tangent_y=torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE),
            physical_radius=torch.tensor(5.0, dtype=FIXED_DOUBLE),
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        assert torch.allclose(
            encounter.distance[0, 0],
            torch.tensor(5.0, dtype=FIXED_DOUBLE),
            atol=1e-12,
        )

    def test_on_surface_origin_is_t_zero_hit(self) -> None:
        """
        起点恰在球面上时认证 t=0 命中
        """

        ro = torch.tensor([[[0.0, 0.0, 0.0]]], dtype=FIXED_DOUBLE)
        rd = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=FIXED_DOUBLE)
        encounter = sphere_encounter(
            ray_origin=ro,
            ray_direction=rd,
            sphere_center=torch.tensor([0.0, 0.0, 5.0], dtype=FIXED_DOUBLE),
            sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_tangent_x=torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
            sphere_tangent_y=torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE),
            physical_radius=torch.tensor(5.0, dtype=FIXED_DOUBLE),
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        assert float(encounter.distance[0, 0]) == 0.0

    def test_outside_pointing_away_is_missed(self) -> None:
        """
        球外指向远离球心时两根均负，判未命中
        """

        ro = torch.tensor([[[0.0, 0.0, 20.0]]], dtype=FIXED_DOUBLE)
        rd = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=FIXED_DOUBLE)
        encounter = sphere_encounter(
            ray_origin=ro,
            ray_direction=rd,
            sphere_center=torch.tensor([0.0, 0.0, 5.0], dtype=FIXED_DOUBLE),
            sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_tangent_x=torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
            sphere_tangent_y=torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE),
            physical_radius=torch.tensor(5.0, dtype=FIXED_DOUBLE),
            clear_aperture_radius=None,
        )
        assert not bool(encounter.is_encountered[0, 0])

    def test_concave_signed_radius_geometry_preserved(self) -> None:
        """
        负曲率半径（凹面）的中心在顶点反向，仍命中正确的物理面
        """

        ro = torch.tensor([[[0.0, 0.0, 10.0]]], dtype=FIXED_DOUBLE)
        rd = torch.tensor([[[0.0, 0.0, -1.0]]], dtype=FIXED_DOUBLE)
        encounter = sphere_encounter(
            ray_origin=ro,
            ray_direction=rd,
            sphere_center=torch.tensor([0.0, 0.0, -5.0], dtype=FIXED_DOUBLE),
            sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_tangent_x=torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
            sphere_tangent_y=torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE),
            physical_radius=torch.tensor(5.0, dtype=FIXED_DOUBLE),
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        assert torch.allclose(
            encounter.distance[0, 0],
            torch.tensor(10.0, dtype=FIXED_DOUBLE),
            atol=1e-12,
        )


class TestSphereEncounterTangent:
    """
    判别式 = 0 的切线命中（含大坐标）
    """

    def test_tangent_ray_hits_at_single_root(self) -> None:
        """
        切线 ray（判别式恰为 0）单根命中
        """

        # origin (5,0,0) 距中心 (0,0,0) 恰为 R=5，沿 +z 切于 origin 自身（t=0）
        ro = torch.tensor([[[5.0, 0.0, 0.0]]], dtype=FIXED_DOUBLE)
        rd = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=FIXED_DOUBLE)
        encounter = sphere_encounter(
            ray_origin=ro,
            ray_direction=rd,
            sphere_center=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_tangent_x=torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
            sphere_tangent_y=torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE),
            physical_radius=torch.tensor(5.0, dtype=FIXED_DOUBLE),
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        assert float(encounter.distance[0, 0]) == 0.0

    def test_large_coordinate_tangent_classified_correctly(self) -> None:
        """
        大坐标（~1e8）切线的判别式符号不被浮点噪声误判
        """

        scale = 1.0e8
        radius = 5.0 * scale
        ro = torch.tensor([[[radius, 0.0, 0.0]]], dtype=FIXED_DOUBLE)
        rd = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=FIXED_DOUBLE)
        encounter = sphere_encounter(
            ray_origin=ro,
            ray_direction=rd,
            sphere_center=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_tangent_x=torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
            sphere_tangent_y=torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE),
            physical_radius=torch.tensor(radius, dtype=FIXED_DOUBLE),
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        assert float(encounter.distance[0, 0]) == 0.0


class TestSphereEncounterApertureBoundary:
    """
    孔径边界 R²−r² = 0 判为孔径内（闭边界）
    """

    def test_aperture_equality_is_inside(self) -> None:
        """
        交点径向恰等于孔径半径时判孔径内
        """

        # origin (3,0,-5) 沿 +z 命中中心 (0,0,0)、R=5 球面；交点径向 r=3，aperture=3
        ro = torch.tensor([[[3.0, 0.0, -5.0]]], dtype=FIXED_DOUBLE)
        rd = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=FIXED_DOUBLE)
        encounter = sphere_encounter(
            ray_origin=ro,
            ray_direction=rd,
            sphere_center=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_tangent_x=torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE),
            sphere_tangent_y=torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE),
            physical_radius=torch.tensor(5.0, dtype=FIXED_DOUBLE),
            clear_aperture_radius=torch.tensor(3.0, dtype=FIXED_DOUBLE),
        )
        assert bool(encounter.is_encountered[0, 0])
        assert bool(encounter.is_inside_aperture[0, 0])


class TestSphereEncounterNonAxisAlignedNearTangent:
    """
    非整数、非轴对齐的近切线判别式用例（数 ULP 量级，验证精确符号读出）
    """

    def test_near_tangent_discriminant_classified_as_real_hit(self) -> None:
        """
        非轴对齐近切线判别式的精确符号为 +1，判实根命中
        """

        a = 2.329369856604598
        b = 8.217574209508822
        c = 7.2475100612851335
        from chromatix_next._numerics._certified_predicates import (
            quadratic_discriminant_sign,
        )

        sign = quadratic_discriminant_sign(
            torch.tensor(a, dtype=FIXED_DOUBLE),
            torch.tensor(b, dtype=FIXED_DOUBLE),
            torch.tensor(c, dtype=FIXED_DOUBLE),
        )
        assert int(sign.item()) == 1


class TestSphereEncounterTrainableRadiusGradient:
    """
    可训练半径的距离梯度：精确符号只选分支，光滑根的梯度完整保留，与中心差分一致
    """

    def test_distance_gradient_matches_central_finite_difference(self) -> None:
        """
        远离切线/孔径硬边界处，distance 对 physical_radius 的解析梯度与中心差分一致
        """

        torch.manual_seed(0)
        radius_value = 5.0e-6
        center = torch.tensor([0.0, 0.0, 0.0], dtype=FIXED_DOUBLE)
        tangent_x = torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE)
        tangent_y = torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE)
        # 斜入射、起点在球外远离切线（denominator 远离 0）
        ray_origin = torch.tensor([[[0.3e-6, -0.2e-6, -8.0e-6]]], dtype=FIXED_DOUBLE)
        direction = torch.tensor([0.1, -0.05, 1.0], dtype=FIXED_DOUBLE)
        direction = direction / direction.norm()
        ray_direction = direction.view(1, 1, 3)

        def distance_at(radius: float) -> float:
            """
            在给定物理半径上求交集距离（中心差分参考，无梯度）
            """

            r = torch.tensor(radius, dtype=FIXED_DOUBLE)
            encounter = sphere_encounter(
                ray_origin=ray_origin,
                ray_direction=ray_direction,
                sphere_center=center,
                sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
                sphere_tangent_x=tangent_x,
                sphere_tangent_y=tangent_y,
                physical_radius=r,
                clear_aperture_radius=None,
            )
            return float(encounter.distance[0, 0].item())

        radius_param = torch.tensor(
            radius_value,
            dtype=FIXED_DOUBLE,
            requires_grad=True,
        )
        encounter = sphere_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            sphere_center=center,
            sphere_vertex=torch.zeros(3, dtype=FIXED_DOUBLE),
            sphere_tangent_x=tangent_x,
            sphere_tangent_y=tangent_y,
            physical_radius=radius_param,
            clear_aperture_radius=None,
        )
        encounter.distance[0, 0].backward()
        assert radius_param.grad is not None
        analytic = float(radius_param.grad.item())
        step = 1.0e-9
        forward_d = distance_at(radius_value + step)
        backward_d = distance_at(radius_value - step)
        central = (forward_d - backward_d) / (2.0 * step)
        # 解析梯度与中心差分一致（精确符号选 near 根；光滑路径保留梯度）
        assert math.isclose(analytic, central, rel_tol=1.0e-5, abs_tol=1.0e-9)

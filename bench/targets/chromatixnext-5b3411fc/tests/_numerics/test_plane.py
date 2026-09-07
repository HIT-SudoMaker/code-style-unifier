
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.reflection import reflect_direction
from chromatix_next._numerics.refraction import refract_at_advance
from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter
from chromatix_next._numerics.surface_geometry.plane import plane_encounter
from chromatix_next.optics._orthonormal_basis import AUTHORED_BASIS_ADMISSIBILITY_BUDGET
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
)


def _analytic_plane_distance(
    ray_origin: torch.Tensor,
    ray_direction: torch.Tensor,
    origin: torch.Tensor,
    normal: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    # 独立闭式 ray-plane 交集（不复用生产 encounter）
    denominator = (ray_direction * normal).sum(dim=-1)
    numerator = ((origin - ray_origin) * normal).sum(dim=-1)
    is_nonparallel = torch.abs(denominator) > 0.0
    safe_denominator = torch.where(
        is_nonparallel,
        denominator,
        torch.ones_like(denominator),
    )
    distance = numerator / safe_denominator
    is_hit = is_nonparallel & (distance >= 0)
    return distance, is_hit


def _analytic_refracted_direction(
    direction: torch.Tensor,
    normal: torch.Tensor,
    eta: float,
) -> torch.Tensor:
    # 独立闭式向量 ``Snell``（已定向法线，cos_i = −d·n̂ ≥ 0）
    cos_incident = -(direction * normal).sum(dim=-1)
    sin_squared_incident = 1.0 - cos_incident * cos_incident
    sin_squared_transmitted = (eta * eta) * sin_squared_incident
    safe = torch.where(
        sin_squared_transmitted > 1.0,
        torch.ones_like(sin_squared_transmitted),
        sin_squared_transmitted,
    )
    cos_transmitted = torch.sqrt(1.0 - safe)
    return (
        eta * direction
        + (eta * cos_incident - cos_transmitted).unsqueeze(-1) * normal
    )


def _plane(
    *,
    origin: torch.Tensor | tuple[float, float, float] = (0.0, 0.0, 0.0),
    tangent_x: tuple[float, float, float] = (1.0, 0.0, 0.0),
    tangent_y: tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    # 返回 (原点, 纵基, 横基, 法线)，均为 float64
    real_dtype = torch.float64
    po = (
        origin
        if isinstance(origin, torch.Tensor)
        else torch.tensor(origin, dtype=real_dtype)
    )
    tangent_x_tensor = torch.tensor(tangent_x, dtype=real_dtype)
    tangent_y_tensor = torch.tensor(tangent_y, dtype=real_dtype)
    normal = torch.linalg.cross(tangent_x_tensor, tangent_y_tensor)
    return po, tangent_x_tensor, tangent_y_tensor, normal


class TestPlaneEncounterIncidentOrientationInvariant:
    """
    逐 ray 法线定向不变量（``unit_normal`` 指向入射介质侧，``dot(d, n) ≤ 0``）
    """

    @pytest.mark.parametrize(
        ("authored_tangent_x", "authored_tangent_y"),
        (
            ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
            ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
        ),
    )
    def test_unit_normal_points_against_incident_for_every_encountered_ray(
        self,
        authored_tangent_x: tuple[float, float, float],
        authored_tangent_y: tuple[float, float, float],
    ) -> None:
        """
        跨入射方向与 authored 法线：每条命中 ray 的法线定向到入射侧、保持单位长度
        """

        origin, tangent_x_tensor, tangent_y_tensor, authored_normal = _plane(
            tangent_x=authored_tangent_x,
            tangent_y=authored_tangent_y,
        )
        directions = torch.tensor(
            [
                [0.0, 0.0, 1.0],
                [0.0, 0.0, -1.0],
                [0.3, 0.0, 0.9],
                [-0.2, 0.4, 0.9],
                [1.0, 0.0, 0.0],
            ],
            dtype=torch.float64,
        )
        directions = directions / directions.norm(dim=-1, keepdim=True)
        ray_count = directions.shape[0]
        origins = (
            torch.zeros((ray_count, 3), dtype=torch.float64)
            - 1.5 * authored_normal.unsqueeze(0)
        )
        ray_origin = origins.unsqueeze(0)
        ray_direction = directions.unsqueeze(0)
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x_tensor,
            plane_tangent_y=tangent_y_tensor,
            clear_aperture_radius=None,
        )
        assert bool(torch.isfinite(encounter.unit_normal).all())
        norms = encounter.unit_normal.norm(dim=-1)
        assert torch.allclose(norms, torch.ones_like(norms), atol=2.0e-7)
        incident_dot_normal = (ray_direction * encounter.unit_normal).sum(dim=-1)
        encountered = encounter.is_encountered
        violated = encountered & (incident_dot_normal > 1.0e-6)
        assert not bool(violated.any())


class TestAuthoredBudgetTangentNormalConditioning:
    """
    authored 8γ₃ 预算内的非严格单位切向量：派生法线必须按自身范数归一化后出场
    （ADR-0010：私有数值核算对派生计算方向做条件化，不触碰 authored 状态）
    """

    def test_unit_normal_conditioned_from_authored_budget_tangents(self) -> None:
        """
        复核反例：a = 1.0000000000000013 的两个切向量落在 authored 预算内，
        cross 产物范数 ≈ 1.0000000000000027；未归一化出场会把残差翻倍并击穿
        下游 Householder/Snell 的单位性验收
        """

        a = 1.0000000000000013
        tangent_x = torch.tensor([a, 0.0, 0.0], dtype=torch.float64)
        tangent_y = torch.tensor([0.0, a, 0.0], dtype=torch.float64)
        ray_origin = torch.tensor([[[0.0, 0.0, -1.0]]], dtype=torch.float64)
        ray_direction = torch.tensor(
            [[[math.sqrt(0.5), 0.0, math.sqrt(0.5)]]],
            dtype=torch.float64,
        )
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=torch.zeros(3, dtype=torch.float64),
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        squared_norm = (encounter.unit_normal * encounter.unit_normal).sum(dim=-1)
        residual = (squared_norm - 1.0).abs()
        # 派生法线的 squared-norm 残差不得劣于 authored 切向量自身的验收预算
        assert bool(residual[0, 0] <= AUTHORED_BASIS_ADMISSIBILITY_BUDGET)
        # 归一化只条件化长度：方向仍沿 ±z 且定向到入射侧（d·n̂ ≤ 0）
        assert torch.allclose(
            encounter.unit_normal,
            torch.tensor([[[0.0, 0.0, -1.0]]], dtype=torch.float64),
            atol=1.0e-12,
        )


class TestPlaneEncounterFeedsRefractingAction:
    """
    plane_encounter 的法线喂入折射动作的 Snell helper：handoff §2 反例闭环为直通透射
    """

    def test_paraxial_passthrough_refracts_forward_not_backward(self) -> None:
        """
        入射 [0,0,+1]、authored 法线 [0,0,+1]、n_i=1.0→n_t=1.5：透射方向为直通
        """

        origin, tangent_x, tangent_y, _normal = _plane()
        ray_origin = torch.tensor([[[0.0, 0.0, -1.0]]], dtype=torch.float64)
        ray_direction = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=torch.float64)
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        incident_dot_normal = (ray_direction * encounter.unit_normal).sum(dim=-1)
        assert float(incident_dot_normal[0, 0]) <= 0.0
        n_i, n_t = 1.0, 1.5
        incident_indices = torch.full((1, 1), n_i, dtype=torch.float64)
        destination_indices = torch.full((1, 1), n_t, dtype=torch.float64)
        is_interacted = torch.ones((1, 1), dtype=torch.bool)
        base_status = torch.full(
            (1, 1),
            RAY_STATUS_ACTIVE,
            dtype=torch.uint8,
        )
        refracted = refract_at_advance(
            ray_direction=ray_direction,
            incident_refractive_indices=incident_indices,
            destination_refractive_indices=destination_indices,
            unit_normal=encounter.unit_normal,
            is_interacted=is_interacted,
            base_status=base_status,
            total_internal_reflection_status_value=(
                RAY_STATUS_TOTAL_INTERNAL_REFLECTION
            ),
        )
        direction = refracted.direction
        index = refracted.refractive_index
        status = refracted.status
        assert status[0, 0] == RAY_STATUS_ACTIVE
        expected_passthrough = torch.tensor([[0.0, 0.0, 1.0]], dtype=torch.float64)
        assert torch.allclose(direction[0], expected_passthrough, atol=1e-12)
        expected_snell = _analytic_refracted_direction(
            ray_direction,
            encounter.unit_normal,
            n_i / n_t,
        )
        assert torch.allclose(direction, expected_snell, atol=1e-12)
        # 成功透射光线逐 ray 折射率切到目标介质
        assert torch.allclose(index, torch.full_like(index, n_t))


class TestPlaneEncounterCertifiedParallelAndForward:
    """
    精确符号平行/正向判定：``d·n == 0`` 平行（含共面）；非平行可解掠入射不再被容差误判；
    认证 ``t=0`` 非平行根为命中
    """

    def test_exact_parallel_ray_is_missed(self) -> None:
        """
        ray 在面内沿面方向（d·n 恰为 0）判未命中
        """

        origin, tangent_x, tangent_y, _n = _plane()
        ray_origin = torch.tensor([[[0.0, 0.0, 0.0]]], dtype=torch.float64)
        ray_direction = torch.tensor([[[1.0, 0.0, 0.0]]], dtype=torch.float64)
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        assert not bool(encounter.is_encountered[0, 0])

    def test_exact_hit_reports_unrepresentable_continuous_distance(self) -> None:
        """
        精确拓扑恢复命中；普通点积同时归零时只携带有限占位与不可表示事实
        """

        diagonal_component = math.sqrt(0.5)
        tiny_component = 2.0**-600
        ray_direction = torch.tensor(
            [
                [
                    [
                        diagonal_component,
                        diagonal_component,
                        tiny_component,
                    ]
                ]
            ],
            dtype=torch.float64,
        )
        ray_origin = torch.zeros_like(ray_direction)
        origin = ray_direction[0, 0].clone()
        tangent_x = torch.tensor(
            [diagonal_component, diagonal_component, 0.0],
            dtype=torch.float64,
        )
        tangent_y = torch.tensor(
            [
                -tiny_component * diagonal_component,
                tiny_component * diagonal_component,
                1.0,
            ],
            dtype=torch.float64,
        )
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        assert not bool(encounter.is_continuous_distance_resolvable[0, 0])
        assert float(encounter.distance[0, 0]) == 0.0
        assert torch.equal(encounter.intersection, ray_origin)
        assert bool(torch.isfinite(encounter.intersection).all())
        assert bool(encounter.is_inside_aperture[0, 0])

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is unavailable")
    def test_exact_hit_unrepresentable_fact_matches_on_cuda(self) -> None:
        """
        反例的精确拓扑、有限占位与连续可表示事实在 CPU/CUDA 一致
        """

        diagonal_component = math.sqrt(0.5)
        tiny_component = 2.0**-600
        direction_cpu = torch.tensor(
            [[[diagonal_component, diagonal_component, tiny_component]]],
            dtype=torch.float64,
        )
        origin_cpu = torch.zeros_like(direction_cpu)
        origin_cpu = direction_cpu[0, 0].clone()
        tangent_x_cpu = torch.tensor(
            [diagonal_component, diagonal_component, 0.0],
            dtype=torch.float64,
        )
        tangent_y_cpu = torch.tensor(
            [
                -tiny_component * diagonal_component,
                tiny_component * diagonal_component,
                1.0,
            ],
            dtype=torch.float64,
        )

        def _encounter_on(device: torch.device) -> SurfaceEncounter:
            return plane_encounter(
                ray_origin=origin_cpu.to(device),
                ray_direction=direction_cpu.to(device),
                plane_origin=origin_cpu.to(device),
                plane_tangent_x=tangent_x_cpu.to(device),
                plane_tangent_y=tangent_y_cpu.to(device),
                clear_aperture_radius=None,
            )

        cpu_encounter = _encounter_on(torch.device("cpu"))
        cuda_encounter = _encounter_on(torch.device("cuda"))
        assert torch.equal(
            cuda_encounter.is_encountered.cpu(),
            cpu_encounter.is_encountered,
        )
        assert torch.equal(
            cuda_encounter.is_continuous_distance_resolvable.cpu(),
            cpu_encounter.is_continuous_distance_resolvable,
        )
        assert torch.equal(
            cuda_encounter.distance.cpu(),
            cpu_encounter.distance,
        )
        assert bool(torch.isfinite(cuda_encounter.intersection).all())

    def test_meta_encounter_carries_continuous_resolvability_shape(self) -> None:
        """
        Meta Plane 相遇保留新增私有事实的批形状，不读取数值
        """

        encounter = plane_encounter(
            ray_origin=torch.empty((2, 1, 3), dtype=torch.float64, device="meta"),
            ray_direction=torch.empty(
                (2, 1, 3),
                dtype=torch.float64,
                device="meta",
            ),
            plane_origin=torch.empty((3,), dtype=torch.float64, device="meta"),
            plane_tangent_x=torch.empty((3,), dtype=torch.float64, device="meta"),
            plane_tangent_y=torch.empty((3,), dtype=torch.float64, device="meta"),
            clear_aperture_radius=None,
        )
        assert encounter.is_continuous_distance_resolvable.device.type == "meta"
        assert encounter.is_continuous_distance_resolvable.shape == (2, 1)

    def test_coplanar_parallel_with_separate_hit_in_batch(self) -> None:
        """
        共面平行（ray 在面内、d·n=0）missed；同 batch 的普通命中正常——平行不污染邻批
        """

        origin, tangent_x, tangent_y, _n = _plane()
        ray_origin = torch.tensor(
            [[[0.0, 0.0, 0.0]], [[0.0, 0.0, -2.0]]],
            dtype=torch.float64,
        )
        ray_direction = torch.tensor(
            [[[1.0, 0.0, 0.0]], [[0.0, 0.0, 1.0]]],
            dtype=torch.float64,
        )
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        assert not bool(encounter.is_encountered[0, 0])
        assert bool(encounter.is_encountered[1, 0])
        assert torch.allclose(
            encounter.distance[1],
            torch.tensor(2.0, dtype=torch.float64),
            atol=1e-12,
        )

    def test_small_nonparallel_forward_root_is_a_certified_hit(self) -> None:
        """
        反例闭环：旧 5e-12 容差把 ``|d·n| ≈ 1e-13`` 的可解掠入射误判为平行（missed）；
        精确符号下 ``d·n != 0`` 判为非平行，正向命中。原 Plane 5e-12 false-miss 被消除
        """

        origin, tangent_x, tangent_y, _n = _plane()
        cosine = 1.0e-13
        ray_direction = torch.tensor(
            [[[math.sqrt(1.0 - cosine * cosine), 0.0, cosine]]],
            dtype=torch.float64,
        )
        ray_origin = torch.tensor([[[0.0, 0.0, -1.0]]], dtype=torch.float64)
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        # 交点距离应与独立闭式一致（distance = -origin_z / d_z = 1 / 1e-13 = 1e13）
        assert torch.allclose(
            encounter.distance[0, 0],
            torch.tensor(1.0 / cosine, dtype=torch.float64),
            rtol=1e-12,
        )

    def test_certified_t_zero_nonparallel_root_is_a_hit(self) -> None:
        """
        非平行且分子恰为零（ray 起点在面上）：认证 t=0 命中，distance=0
        """

        origin, tangent_x, tangent_y, _n = _plane()
        ray_origin = torch.tensor([[[0.0, 0.0, 0.0]]], dtype=torch.float64)
        ray_direction = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=torch.float64)
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        assert bool(encounter.is_encountered[0, 0])
        assert float(encounter.distance[0, 0]) == 0.0

    def test_backward_nonparallel_root_is_missed(self) -> None:
        """
        非平行但交点在 ray 反向（num/den < 0）：未命中
        """

        origin, tangent_x, tangent_y, _n = _plane()
        ray_origin = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=torch.float64)
        ray_direction = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=torch.float64)
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        # ray 在 z=1 沿 +z，面在 z=0 ⇒ 交点在反向 ⇒ missed
        assert not bool(encounter.is_encountered[0, 0])


class TestPlaneEncounterValidHitPhysicsUnchanged:
    """
    有效命中的交点/距离/法线模长与独立闭式参考一致：定向只选法线符号，不扰动命中
    """

    def test_forward_hit_matches_closed_form_intersection_and_distance(
        self,
    ) -> None:
        """
        斜入射正向命中：距离、交点与闭式参考一致；法线单位、定向到入射侧
        """

        origin, tangent_x, tangent_y, authored_normal = _plane()
        direction = torch.tensor([[0.2, 0.1, 1.0]], dtype=torch.float64)
        direction = direction / direction.norm(dim=-1, keepdim=True)
        ray_origin = torch.tensor([[0.0, 0.0, -2.0]], dtype=torch.float64).unsqueeze(0)
        ray_direction = direction.unsqueeze(0)
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        closed_distance, closed_is_hit = _analytic_plane_distance(
            ray_origin[0],
            ray_direction[0],
            origin,
            authored_normal,
        )
        assert bool(closed_is_hit[0])
        assert bool(encounter.is_encountered[0, 0])
        assert torch.allclose(
            encounter.distance[0],
            closed_distance[0],
            atol=1e-12,
        )
        closed_intersection = (
            ray_origin[0] + closed_distance[0].unsqueeze(-1) * ray_direction[0]
        )
        assert torch.allclose(
            encounter.intersection[0],
            closed_intersection,
            atol=1e-12,
        )
        norm = encounter.unit_normal[0].norm()
        assert torch.allclose(norm, torch.ones_like(norm), atol=1e-12)

    def test_ordinary_distance_retains_original_gradient_path(self) -> None:
        """
        精确拓扑掩码不替代普通点积给出的距离梯度
        """

        origin, tangent_x, tangent_y, _normal = _plane()
        ray_origin = torch.tensor(
            [[[0.0, 0.0, -2.0]]],
            dtype=torch.float64,
            requires_grad=True,
        )
        ray_direction = torch.tensor(
            [[[0.0, 0.0, 1.0]]],
            dtype=torch.float64,
        )
        encounter = plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=None,
        )
        encounter.distance.sum().backward()
        assert ray_origin.grad is not None
        assert torch.equal(
            ray_origin.grad,
            torch.tensor([[[0.0, 0.0, -1.0]]], dtype=torch.float64),
        )


class TestReflectionLawNormalSignInvariant:
    """
    反射律对法线符号不变：定向不影响反射方向（反射动作的 reflect_direction helper）
    """

    def test_reflection_identical_for_flipped_normal(self) -> None:
        """
        同一相遇仅法线符号相反：反射方向完全一致（Householder 律对 n̂ 符号不变）
        """

        real_dtype = torch.float64
        ray_direction = torch.tensor([[[0.3, 0.0, 1.0]]], dtype=real_dtype)
        ray_direction = ray_direction / ray_direction.norm(dim=-1, keepdim=True)
        normal = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=real_dtype)
        is_interacted = torch.ones((1, 1), dtype=torch.bool)
        direction_plus = reflect_direction(
            ray_direction=ray_direction,
            unit_normal=normal,
            is_interacted=is_interacted,
        )
        direction_minus = reflect_direction(
            ray_direction=ray_direction,
            unit_normal=-normal,
            is_interacted=is_interacted,
        )
        assert torch.equal(direction_plus, direction_minus)
        # 反射后方向保单位长度（Householder 构造性不变量）
        norms = direction_plus.norm(dim=-1)
        assert torch.allclose(norms, torch.ones_like(norms), atol=1.0e-9)

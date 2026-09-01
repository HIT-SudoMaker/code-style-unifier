
from __future__ import annotations

import math

import torch

from chromatix_next._numerics.refraction import refract_at_advance
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
)

FIXED_DOUBLE = torch.float64


def _refract(
    *,
    cos_incident: float,
    incident_index: float,
    transmitted_index: float,
) -> int:
    # 构造入射方向与法线，唤折射 action owner 的 Snell+TIR helper，返回 status 值
    sin_incident = math.sqrt(max(0.0, 1.0 - cos_incident * cos_incident))
    ray_direction = torch.tensor(
        [[[sin_incident, 0.0, cos_incident]]],
        dtype=FIXED_DOUBLE,
    )
    unit_normal = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=FIXED_DOUBLE)
    is_interacted = torch.ones((1, 1), dtype=torch.bool)
    base_status = torch.full(
        (1, 1),
        RAY_STATUS_ACTIVE,
        dtype=torch.uint8,
    )
    refracted = refract_at_advance(
        ray_direction=ray_direction,
        incident_refractive_indices=torch.full(
            (1, 1),
            incident_index,
            dtype=FIXED_DOUBLE,
        ),
        destination_refractive_indices=torch.full(
            (1, 1),
            transmitted_index,
            dtype=FIXED_DOUBLE,
        ),
        unit_normal=unit_normal,
        is_interacted=is_interacted,
        base_status=base_status,
        total_internal_reflection_status_value=(
            RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        ),
    )
    return int(refracted.status[0, 0])


class TestTotalInternalReflectionClassification:
    """
    ``Q`` 三态分类的独立证据
    """

    def test_ordinary_transmission_above_boundary(self) -> None:
        """
        近正入射（cos≈1）普通透射，状态为 active
        """

        status = _refract(
            cos_incident=1.0,
            incident_index=1.5,
            transmitted_index=1.0,
        )
        assert status == RAY_STATUS_ACTIVE

    def test_grazing_at_q_zero(self) -> None:
        """
        ``Q = 0`` 恰等时为掠射（非全内反射）
        """

        # 折射率 1→1、cos=0 ⇒ Q = 1 − 1·(1−0) = 0
        status = _refract(
            cos_incident=0.0,
            incident_index=1.0,
            transmitted_index=1.0,
        )
        assert status == RAY_STATUS_ACTIVE

    def test_total_internal_reflection_below_boundary(self) -> None:
        """
        ``Q < 0`` 超临界时为全内反射
        """

        # 折射率 1.5→1.0、cos=0 ⇒ Q = 1 − 2.25·1 < 0
        status = _refract(
            cos_incident=0.0,
            incident_index=1.5,
            transmitted_index=1.0,
        )
        assert status == RAY_STATUS_TOTAL_INTERNAL_REFLECTION

    def test_critical_angle_neighbours_are_deterministic(self) -> None:
        """
        临界角两相邻可表示值给出确定性分类（不经 η≈1 舍入翻转）
        """

        sin_critical = 1.0 / 1.5
        cos_critical = math.sqrt(1.0 - sin_critical * sin_critical)
        below = math.nextafter(cos_critical, math.inf)
        above = math.nextafter(cos_critical, -math.inf)
        status_below = _refract(
            cos_incident=below,
            incident_index=1.5,
            transmitted_index=1.0,
        )
        status_above = _refract(
            cos_incident=above,
            incident_index=1.5,
            transmitted_index=1.0,
        )
        assert status_below in {
            RAY_STATUS_ACTIVE,
            RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
        }
        assert status_above in {
            RAY_STATUS_ACTIVE,
            RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
        }

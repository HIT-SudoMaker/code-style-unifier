
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics.surface import Plane


def _unit(axis: tuple[float, float, float]) -> tuple[float, float, float]:
    # 归一化三维轴向量到单位长度
    tensor = torch.tensor(axis, dtype=torch.float64)
    normalized = tensor / tensor.norm()
    return (float(normalized[0]), float(normalized[1]), float(normalized[2]))


class TestPoseAdmissibilityBudget:
    """
    ``8·γ₃`` 预算容许合理 authored 帧，拒绝真非单位/近退化帧
    """

    def test_axis_angle_frame_admitted(self) -> None:
        """
        sin/cos 构造的轴角帧通过（构造误差远小于 24u）
        """

        angle = 0.3
        axis_y = (math.cos(angle), math.sin(angle), 0.0)
        axis_x = (-math.sin(angle), math.cos(angle), 0.0)
        plane = Plane(tangent_x=axis_y, tangent_y=axis_x)
        assert isinstance(plane.tangent_x, torch.Tensor)

    def test_normalized_arbitrary_vector_frame_admitted(self) -> None:
        """
        归一化任意向量构造的正交右手帧通过
        """

        axis_y = _unit((1.0, 2.0, 0.5))
        yv = torch.tensor(axis_y, dtype=torch.float64)
        candidate = torch.linalg.cross(
            yv,
            torch.tensor([0.0, 0.0, 1.0], dtype=torch.float64),
        )
        candidate = candidate / candidate.norm()
        axis_x = (float(candidate[0]), float(candidate[1]), float(candidate[2]))
        plane = Plane(tangent_x=axis_y, tangent_y=axis_x)
        assert isinstance(plane.tangent_x, torch.Tensor)

    def test_trainable_valid_pose_admitted(self) -> None:
        """
        可训练原点加合法单位基通过（梯度仍流过原点）
        """

        origin = torch.nn.Parameter(
            torch.tensor([0.0, 0.0, 1.0e-6], dtype=torch.float64),
        )
        plane = Plane(
            origin=origin,
            tangent_x=(1.0, 0.0, 0.0),
            tangent_y=(0.0, 1.0, 0.0),
        )
        assert isinstance(plane.origin, torch.nn.Parameter)

    def test_genuinely_non_unit_frame_rejected(self) -> None:
        """
        真非单位基（偏差远超预算）被拒
        """

        with pytest.raises(OpticalValueError):
            Plane(
                tangent_x=(1.0, 0.0, 0.001),
                tangent_y=(0.0, 1.0, 0.0),
            )

    def test_near_degenerate_parallel_frame_rejected(self) -> None:
        """
        近退化（两基近共线）被拒（认证三重积符号为 0）
        """

        with pytest.raises(OpticalValueError):
            Plane(
                tangent_x=(1.0, 0.0, 0.0),
                tangent_y=(1.0, 1.0e-9, 0.0),
            )

    def test_non_orthogonal_frame_rejected(self) -> None:
        """
        明显非正交基被拒
        """

        with pytest.raises(OpticalValueError):
            Plane(
                tangent_x=(1.0, 0.0, 0.0),
                tangent_y=(1.0, 1.0, 0.0),
            )

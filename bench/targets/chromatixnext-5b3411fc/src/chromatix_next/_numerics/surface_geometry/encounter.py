from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True, slots=True)
class SurfaceEncounter:
    """
    汇集一次表面相交判定产生的逐光线几何事实

    Attributes:
        distance: 从光线当前位置到交点的有符号距离
        intersection: 以实验坐标表示的交点位置
        unit_normal: 交点处采用表面取向的单位法向量
        is_encountered: 光线是否在允许方向上遇到表面
        is_inside_aperture: 交点是否位于表面的通光孔径内
        is_continuous_distance_resolvable: 连续距离能否由 float64 位置增量表示

    """

    distance: torch.Tensor
    intersection: torch.Tensor
    unit_normal: torch.Tensor
    is_encountered: torch.Tensor
    is_inside_aperture: torch.Tensor
    is_continuous_distance_resolvable: torch.Tensor

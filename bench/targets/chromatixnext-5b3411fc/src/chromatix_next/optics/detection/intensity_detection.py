from __future__ import annotations

import torch

from chromatix_next._numerics.intensity import spectral_intensity_reduction
import chromatix_next.errors as _errors

from .._role_contract import _DetectionRole
from ..field import OpticalField
from ..intensity import Intensity


def intensity_detection(field: OpticalField) -> Intensity:
    """
    把一个光场约减为保留网格与归一化语义的光强

    Args:
        field: 待处理的入射光场

    Returns:
        返回遵循该 Interface 归一化约定的强度张量

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

    """
    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "intensity_detection_field_invalid",
            "强度探测只接受光场，"
            f"收到的是 {type(field).__name__}；"
            "光强已经是可观测量，不能再次探测",
        )
    values = spectral_intensity_reduction(
        field.envelope,
        torch.tensor(
            field.spectrum.weights,
            device=field.envelope.device,
            dtype=field.envelope.real.dtype,
        ),
    )
    return Intensity(
        values=values,
        grid=field.grid,
        normalization=field.normalization,
    )


class IntensityDetection(torch.nn.Module):
    """
    将光场约减为光强的探测组件

    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def role(self) -> _DetectionRole:
        """
        探测角色字面量

        Returns:
            返回该检测组件的稳定 Detection 角色标识 "detection"

        """

        return "detection"

    def forward(self, field: OpticalField) -> Intensity:  # type: ignore[override]
        """
        计算光场的光强可观测量

        Args:
            field: 待处理的入射光场

        Returns:
            返回遵循该 Interface 归一化约定的强度张量

        """
        return intensity_detection(field)

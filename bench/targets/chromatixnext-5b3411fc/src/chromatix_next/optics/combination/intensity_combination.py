from __future__ import annotations

import torch

import chromatix_next.errors as _errors

from .._role_contract import _CombinationRole
from ..intensity import Intensity


def intensity_combination(
    intensity_1: Intensity,
    intensity_2: Intensity,
) -> Intensity:
    """
    把两路兼容光强逐元素相加并继承第一路物理轮廓

    Args:
        intensity_1: 参与非相干相加的第一份强度
        intensity_2: 参与非相干相加的第二份强度

    Returns:
        返回遵循该 Interface 归一化约定的强度张量

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

        AssemblyError: 拓扑/端口/冻结状态不满足前置条件
    """
    if not isinstance(intensity_1, Intensity):
        raise _errors.OpticalTypeError(
            "intensity_combination_intensity_1_invalid",
            "强度组合的第一路输入必须是光强，"
            f"收到的是 {type(intensity_1).__name__}；"
            "光场请先经探测约减为光强",
        )
    if not isinstance(intensity_2, Intensity):
        raise _errors.OpticalTypeError(
            "intensity_combination_intensity_2_invalid",
            "强度组合的第二路输入必须是光强，"
            f"收到的是 {type(intensity_2).__name__}；"
            "光场请先经探测约减为光强",
        )
    _raise_on_intensity_incompatibility(intensity_1, intensity_2)
    return Intensity(
        values=intensity_1.values + intensity_2.values,
        grid=intensity_1.grid,
        normalization=intensity_1.normalization,
    )

def _raise_on_intensity_incompatibility(
    intensity_1: Intensity,
    intensity_2: Intensity,
) -> None:
    findings: list[str] = []
    if not intensity_1.grid.is_inference_compatible_with(intensity_2.grid):
        findings.append("intensity_combination_grid_mismatch")
    if intensity_1.normalization is not intensity_2.normalization:
        findings.append("intensity_combination_normalization_mismatch")
    if tuple(intensity_1.values.shape) != tuple(intensity_2.values.shape):
        findings.append("intensity_combination_axis_mismatch")
    if intensity_1.values.device != intensity_2.values.device:
        findings.append("intensity_combination_device_mismatch")
    if findings:
        raise _errors.AssemblyError(
            "; ".join(findings),
            "两路光强要相加，必须在网格、归一化、形状与设备位置上一致，"
            "以上是未通过的检查",
        )


class IntensityCombination(torch.nn.Module):
    """
    拥有无状态强度叠加动作的组合组件

    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def role(self) -> _CombinationRole:
        """
        组合角色字面量

        Returns:
            返回该组合组件声明的 Combination 角色

        """

        return "combination"

    @property
    def input_ports(self) -> tuple[str, str]:
        """
        两路固定光强输入端口名（intensity_1, intensity_2）

        Returns:
            固定为 (intensity_1, intensity_2) 的输入端口名称元组

        """

        return ("intensity_1", "intensity_2")

    def forward(  # type: ignore[override]
        self,
        intensity_1: Intensity,
        intensity_2: Intensity,
    ) -> Intensity:
        """
        把两个兼容光强的实数值逐元素相加并继承第一输入轮廓

        Args:
            intensity_1: 参与非相干相加的第一份强度
            intensity_2: 参与非相干相加的第二份强度

        Returns:
            返回遵循该 Interface 归一化约定的强度张量

        """
        return intensity_combination(intensity_1, intensity_2)

from __future__ import annotations

import torch

from chromatix_next._numerics.optical_path_reference import (
    sum_envelopes_in_optical_path_reference,
)
import chromatix_next.errors as _errors

from .._coherence import _collect_coherent_field_findings
from .._role_contract import _CombinationRole
from ..field import OpticalField, _transform_field


def coherent_combination(
    field_1: OpticalField,
    field_2: OpticalField,
) -> OpticalField:
    """
    把两路相干兼容的光场包络相加并继承第一路物理轮廓

    Args:
        field_1: 参与相干叠加的第一束光场
        field_2: 参与相干叠加的第二束光场

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

        AssemblyError: 拓扑/端口/冻结状态不满足前置条件
    """
    if not isinstance(field_1, OpticalField):
        raise _errors.OpticalTypeError(
            "coherent_combination_field_1_invalid",
            "相干组合的第一路输入必须是光场，"
            f"收到的是 {type(field_1).__name__}；"
            "光强已丢失相位，只能进入强度组合",
        )
    if not isinstance(field_2, OpticalField):
        raise _errors.OpticalTypeError(
            "coherent_combination_field_2_invalid",
            "相干组合的第二路输入必须是光场，"
            f"收到的是 {type(field_2).__name__}；"
            "光强已丢失相位，只能进入强度组合",
        )
    _raise_on_field_incompatibility(field_1, field_2)
    output_envelope = sum_envelopes_in_optical_path_reference(
        destination_envelope=field_1.envelope,
        added_envelope=field_2.envelope,
        wavelengths=field_1.spectrum.wavelengths,
        destination_reference_lengths=field_1.path_reference.lengths,
        added_reference_lengths=field_2.path_reference.lengths,
    )
    return _transform_field(
        field_1,
        envelope=output_envelope,
    )

def _raise_on_field_incompatibility(
    field_1: OpticalField,
    field_2: OpticalField,
) -> None:
    findings = _collect_coherent_field_findings(
        field_1,
        field_2,
        prefix="coherent_combination_",
    )
    if findings:
        raise _errors.AssemblyError(
            "; ".join(findings),
            "两路光场必须在波长、权重、偏振、介质、网格、归一化、轴、"
            "精度与源谱系上相干兼容；光程参考可以不同，会在混合前载波对齐",
        )


class CoherentCombination(torch.nn.Module):
    """
    拥有无状态相干场叠加动作的组合组件

    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def role(self) -> _CombinationRole:
        """
        组合角色字面量

        Returns:
            返回该组合组件的稳定 Combination 角色标识 "combination"

        """

        return "combination"

    @property
    def input_ports(self) -> tuple[str, str]:
        """
        两路固定光场输入端口名（field_1, field_2）

        Returns:
            固定为 (field_1, field_2) 的输入端口名称元组

        """

        return ("field_1", "field_2")

    def forward(  # type: ignore[override]
        self,
        field_1: OpticalField,
        field_2: OpticalField,
    ) -> OpticalField:
        """
        把两个相干兼容光场的包络逐元素相加，返回继承第一输入轮廓的相干输出

        Args:
            field_1: 参与相干叠加的第一束光场
            field_2: 参与相干叠加的第二束光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """
        return coherent_combination(field_1, field_2)

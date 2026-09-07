from __future__ import annotations

from typing import NotRequired, TypeAlias, TypedDict

import torch

SampleProvenance: TypeAlias = dict[str, object]


class RawSample(TypedDict):
    """
    原始图像样本

    Attributes:
        image:      单通道原始图像张量，dtype 保留原始数据源语义
        label:      类别标签整数
        category:   类别名称
        provenance: 来源元数据字典
    """
    image: torch.Tensor
    label: int
    category: str
    provenance: SampleProvenance


class PreparedSample(TypedDict):
    """
    预处理后的图像样本

    Attributes:
        image:      预处理后的单通道 float32 图像张量，形状为 [1, H, W]
        label:      类别标签整数
        category:   类别名称
        provenance: 来源与预处理元数据字典
    """
    image: torch.Tensor
    label: int
    category: str
    provenance: SampleProvenance


class PerturbedSample(TypedDict):
    """
    扰动后的图像样本。

    Attributes:
        image:           当前扰动结果。
        reference_image: 进入扰动阶段前的准备图像。
        label:           类别标签整数。
        category:        类别名称。
        provenance:      来源与扰动元数据。
    """

    image: torch.Tensor
    reference_image: torch.Tensor
    label: int
    category: str
    provenance: SampleProvenance


class EncodedSample(TypedDict):
    """
    光场编码后的样本

    Attributes:
        input_image: 编码前的单通道 float32 输入图像张量，形状为 [1, H, W]
        input_field: 编码后的 complex64 复数光场张量，形状为 [1, H, W]
        label:       类别标签整数
        category:    类别名称
        provenance:  来源与编码元数据字典
    """
    input_image: torch.Tensor
    input_field: torch.Tensor
    reference_image: NotRequired[torch.Tensor]
    label: int
    category: str
    provenance: SampleProvenance

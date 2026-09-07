from __future__ import annotations

from copy import deepcopy

import numpy as np
import torch

from data.types import SampleProvenance


def to_numpy_image(image: torch.Tensor, *, context_name: str) -> np.ndarray:
    """
    单通道二维numpy数组

    Args:
        image:        输入图像张量
        context_name: 调用方上下文名称，用于错误定位

    Returns:
        单通道二维float32数组

    Raises:
        ValueError: 当输入不是单通道二维数组时抛出
    """
    image_array = image.detach().cpu().numpy()
    if image_array.ndim == 3 and image_array.shape[0] == 1:
        image_array = image_array[0]
    if image_array.ndim != 2:
        raise ValueError(
            f"{context_name}期望单通道输入，"
            f"实际形状为{image_array.shape}"
        )
    return np.array(image_array, copy=True)


def copy_provenance(provenance: SampleProvenance) -> SampleProvenance:
    """
    深拷贝来源元数据

    Args:
        provenance: 待拷贝的来源元数据

    Returns:
        深拷贝后的来源元数据
    """
    return deepcopy(provenance)

from __future__ import annotations

import numpy as np
import torch


def encode_image_to_field(*, image: np.ndarray, encoding_method: str = "intensity") -> torch.Tensor:
    """
    将二维图像编码为复振幅光场张量

    Args:
        image:           输入归一化二维图像数组，数值范围为 [0, 1]
        encoding_method: 编码方式，可选"intensity"或"phase"

    Returns:
        编码后的 complex64 复振幅光场张量，形状为 [1, H, W]

    Raises:
        ValueError: 编码方式不支持时抛出
    """
    image_float = image.astype(np.float32, copy=False)
    if image_float.ndim != 2:
        raise ValueError(
            f"image必须是二维数组，收到shape={image_float.shape}"
        )
    if not np.all(np.isfinite(image_float)):
        raise ValueError(
            "image只能包含有限数值"
        )
    if np.any(image_float < 0.0) or np.any(image_float > 1.0):
        raise ValueError(
            "image必须归一化到[0, 1]范围"
        )
    if encoding_method == "intensity":
        amplitude = np.sqrt(image_float)
        phase = np.zeros_like(amplitude, dtype=np.float32)
    elif encoding_method == "phase":
        amplitude = np.ones_like(image_float, dtype=np.float32)
        phase = image_float * (2.0 * np.pi)
    else:
        raise ValueError(
            f"未知的编码方式: {encoding_method}"
        )
    field = amplitude * np.exp(1j * phase)
    return torch.from_numpy(field.astype(np.complex64)).unsqueeze(0)

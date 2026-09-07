from __future__ import annotations

import numpy as np


def apply_gaussian_blur(image: np.ndarray, *, kernel_size: int) -> np.ndarray:
    """
    对归一化浮点图像施加高斯模糊退化

    Args:
        image:       输入归一化图像
        kernel_size: 高斯核尺寸，必须为正奇数

    Returns:
        高斯模糊后的图像

    Raises:
        ValueError: kernel_size不为正奇数时抛出
    """
    if kernel_size <= 0 or kernel_size % 2 == 0:
        raise ValueError(
            f"kernel_size必须为正奇数，收到: {kernel_size}"
        )

    import cv2

    return cv2.GaussianBlur(
        image.astype(np.float32, copy=False),
        (kernel_size, kernel_size),
        0.0,
    )

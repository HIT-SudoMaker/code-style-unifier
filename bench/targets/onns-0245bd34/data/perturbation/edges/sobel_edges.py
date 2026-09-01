from __future__ import annotations

import numpy as np

from data.perturbation.edges._shared import _normalize_edge_response


def build_sobel_edge_map(image: np.ndarray, *, kernel_size: int) -> np.ndarray:
    """
    构建归一化的Sobel梯度幅值边缘图

    Args:
        image:       输入归一化图像数组
        kernel_size: Sobel核尺寸

    Returns:
        归一化到 [0, 1] 的边缘幅值图
    """
    import cv2

    image_float = image.astype(np.float32, copy=False)
    gradient_x = cv2.Sobel(
        image_float,
        cv2.CV_32F,
        1,
        0,
        ksize=kernel_size,
    )
    gradient_y = cv2.Sobel(
        image_float,
        cv2.CV_32F,
        0,
        1,
        ksize=kernel_size,
    )
    magnitude = cv2.magnitude(gradient_x, gradient_y)
    return _normalize_edge_response(magnitude)

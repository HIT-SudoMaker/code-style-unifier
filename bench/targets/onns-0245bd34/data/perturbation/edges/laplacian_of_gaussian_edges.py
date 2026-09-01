from __future__ import annotations

import numpy as np

from data.perturbation.edges._shared import _normalize_edge_response


def build_laplacian_of_gaussian_edge_map(
    image: np.ndarray,
    *,
    kernel_size: int,
    sigma: float = 0.0,
) -> np.ndarray:
    """
    构建归一化的高斯拉普拉斯边缘响应图

    Args:
        image:       输入归一化图像数组
        kernel_size: 高斯与拉普拉斯核尺寸
        sigma:       高斯平滑标准差

    Returns:
        归一化到 [0, 1] 的绝对拉普拉斯响应图
    """
    import cv2

    image_float = image.astype(np.float32, copy=False)
    smoothed_image = cv2.GaussianBlur(
        image_float,
        (kernel_size, kernel_size),
        sigma,
    )
    laplacian_response = cv2.Laplacian(
        smoothed_image,
        cv2.CV_32F,
        ksize=kernel_size,
    )
    return _normalize_edge_response(laplacian_response)

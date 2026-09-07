from __future__ import annotations

import numpy as np


def build_canny_edge_map(image: np.ndarray, *, threshold1: float, threshold2: float) -> np.ndarray:
    """
    构建归一化Canny边缘图

    Args:
        image:      输入归一化图像
        threshold1: Canny低阈值
        threshold2: Canny高阈值
    """
    import cv2

    image_uint8 = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    edges = cv2.Canny(
        image_uint8,
        threshold1=threshold1,
        threshold2=threshold2,
    )
    return edges.astype(np.float32) / 255.0

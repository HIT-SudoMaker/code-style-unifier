from __future__ import annotations

import numpy as np


def apply_defocus_blur(image: np.ndarray, *, radius: int) -> np.ndarray:
    """
    使用归一化圆盘点扩散函数施加离焦模糊

    Args:
        image:  输入归一化图像数组
        radius: 圆盘点扩散半径，单位为像素

    Returns:
        与归一化圆盘点扩散函数卷积后的图像

    Raises:
        ValueError: radius不为正整数时抛出
    """
    import cv2

    if radius <= 0:
        raise ValueError(
            "radius必须为正整数"
        )

    kernel = _build_disk_point_spread_function(radius=radius)
    blurred_image = cv2.filter2D(
        image.astype(np.float32, copy=False),
        ddepth=-1,
        kernel=kernel,
        borderType=cv2.BORDER_CONSTANT,
    )
    return blurred_image.astype(np.float32, copy=False)


def _build_disk_point_spread_function(*, radius: int) -> np.ndarray:
    kernel_size = 2 * radius + 1
    coordinate = np.arange(kernel_size, dtype=np.float32) - float(radius)
    coordinate_y, coordinate_x = np.meshgrid(coordinate, coordinate, indexing="ij")
    disk = (coordinate_x**2 + coordinate_y**2) <= float(radius**2)
    kernel = disk.astype(np.float32)
    return kernel / float(kernel.sum())

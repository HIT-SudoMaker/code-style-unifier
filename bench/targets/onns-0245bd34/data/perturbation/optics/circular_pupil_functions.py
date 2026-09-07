from __future__ import annotations

import numpy as np


def build_circular_pupil_function(*, shape: tuple[int, int], radius_fraction: float) -> np.ndarray:
    """
    构建居中的圆形复数pupil掩膜

    Args:
        shape:           输出pupil高度和宽度
        radius_fraction: 用作直径的较短图像边长比例

    Returns:
        孔径内振幅为1的complex64pupil掩膜

    Raises:
        ValueError: 当形状或半径比例超出支持范围时抛出
    """
    if not 0.0 < radius_fraction <= 1.0:
        raise ValueError(
            "radius_fraction必须位于(0, 1]范围内"
        )

    height, width = shape
    if height <= 0 or width <= 0:
        raise ValueError(
            "shape各维度必须为正数"
        )

    row_coordinates, column_coordinates = np.indices((height, width))
    row_center = (height - 1) / 2.0
    column_center = (width - 1) / 2.0
    radius = min(height, width) * radius_fraction / 2.0
    pupil_mask = (
        (row_coordinates - row_center) ** 2
        + (column_coordinates - column_center) ** 2
        <= radius**2
    )
    return pupil_mask.astype(np.complex64)

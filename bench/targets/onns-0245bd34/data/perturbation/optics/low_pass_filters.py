from __future__ import annotations

import numpy as np


def build_ideal_low_pass_filter(*, shape: tuple[int, int], cutoff_fraction: float) -> np.ndarray:
    """
    构建居中的圆形频域低通掩膜

    Args:
        shape:           输出掩膜高度和宽度
        cutoff_fraction: 截止半径相对于较短图像边长的比例

    Returns:
        通带内为1且其余位置为0的float32掩膜

    Raises:
        ValueError: 当形状或截止比例超出支持范围时抛出
    """
    if not 0.0 < cutoff_fraction <= 0.5:
        raise ValueError(
            "cutoff_fraction必须位于(0, 0.5]范围内"
        )

    height, width = shape
    if height <= 0 or width <= 0:
        raise ValueError(
            "shape各维度必须为正数"
        )

    row_coordinates, column_coordinates = np.indices((height, width))
    row_center = height // 2
    column_center = width // 2
    radius = min(height, width) * cutoff_fraction
    mask = (
        (row_coordinates - row_center) ** 2
        + (column_coordinates - column_center) ** 2
        <= radius**2
    )
    return mask.astype(np.float32)

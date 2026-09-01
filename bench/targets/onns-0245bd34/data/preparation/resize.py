from __future__ import annotations

import numpy as np

from data._validation import normalize_resolution_pair
from data.configs.stages import ResizeMethod

_INTERPOLATION_TO_CV2 = {
    "nearest": "INTER_NEAREST",
    "bilinear": "INTER_LINEAR",
    "bicubic": "INTER_CUBIC",
}


def resize_image(
    *,
    image: np.ndarray,
    image_resolution: tuple[int, int],
    array_resolution: tuple[int, int],
    interpolation_method: ResizeMethod = "nearest",
    edge_taper_width: int = 0,
) -> np.ndarray:
    """
    缩放图像支撑区域并居中填充至光学阵列尺寸

    Args:
        image:                   输入图像数组
        image_resolution:        目标图像支撑分辨率，格式为(height, width)
        array_resolution:        输出光学阵列分辨率，格式为(height, width)
        interpolation_method:    缩放插值策略
        edge_taper_width:        图像支撑区域内余弦边缘切趾的宽度

    Returns:
        缩放并居中后的float32图像

    Raises:
        ValueError: 几何参数或策略值无效时抛出
    """
    # 延迟导入cv2以避免可选重型依赖增加模块加载成本
    import cv2

    image_height, image_width = normalize_resolution_pair(
        "image_resolution",
        image_resolution,
    )
    array_height, array_width = normalize_resolution_pair(
        "array_resolution",
        array_resolution,
    )
    if image_height > array_height or image_width > array_width:
        raise ValueError(
            "resize_image要求image_resolution <= array_resolution; "
            f"收到image_resolution={(image_height, image_width)}, "
            f"array_resolution={(array_height, array_width)}"
        )
    if interpolation_method not in _INTERPOLATION_TO_CV2:
        raise ValueError(
            "interpolation_method须为nearest、bilinear或bicubic之一"
        )
    if not isinstance(edge_taper_width, int) or isinstance(edge_taper_width, bool):
        raise ValueError(
            "edge_taper_width必须为非负整数"
        )
    if edge_taper_width < 0:
        raise ValueError(
            "edge_taper_width必须为非负整数"
        )

    cv2_interpolation = getattr(cv2, _INTERPOLATION_TO_CV2[interpolation_method])
    resized = cv2.resize(
        np.asarray(image, dtype=np.float32),
        dsize=(image_width, image_height),
        interpolation=cv2_interpolation,
    ).astype(np.float32)
    if edge_taper_width > 0:
        resized = _apply_edge_taper(
            image=resized,
            edge_taper_width=edge_taper_width,
        )

    output = np.zeros((array_height, array_width), dtype=np.float32)
    top = (array_height - image_height) // 2
    left = (array_width - image_width) // 2
    output[
        top : top + image_height,
        left : left + image_width,
    ] = resized
    return output


def _apply_edge_taper(
    *,
    image: np.ndarray,
    edge_taper_width: int,
) -> np.ndarray:
    image_height, image_width = image.shape
    max_taper_width = min(image_height, image_width) // 2
    if edge_taper_width > max_taper_width:
        raise ValueError(
            "edge_taper_width不得超过图像较小维度的一半"
        )
    row_coordinates = np.arange(image_height, dtype=np.float32)
    column_coordinates = np.arange(image_width, dtype=np.float32)
    row_distance = np.minimum(row_coordinates, image_height - 1 - row_coordinates)
    column_distance = np.minimum(
        column_coordinates,
        image_width - 1 - column_coordinates,
    )
    row_window = _cosine_taper(row_distance, edge_taper_width)
    column_window = _cosine_taper(column_distance, edge_taper_width)
    window = np.outer(row_window, column_window).astype(np.float32)
    return (image * window).astype(np.float32)


def _cosine_taper(
    distance_to_edge: np.ndarray,
    edge_taper_width: int,
) -> np.ndarray:
    normalized_distance = np.clip(distance_to_edge / edge_taper_width, 0.0, 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * normalized_distance)

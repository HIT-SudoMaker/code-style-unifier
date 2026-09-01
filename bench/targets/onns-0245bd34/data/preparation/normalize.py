from __future__ import annotations

import numpy as np

from data.configs.stages import NormalizationMethod


def normalize_image(
    *,
    image: np.ndarray,
    normalization_method: NormalizationMethod = "auto",
    percentile_range: tuple[float, float] = (1.0, 99.0),
) -> np.ndarray:
    """
    将图像归一化到float32预处理范围

    Args:
        image:                 输入图像数组
        normalization_method:  归一化策略
        percentile_range:      百分位裁剪的下界与上界百分位

    Returns:
        归一化后的float32图像
    """
    if normalization_method == "none":
        return image.astype(np.float32)
    if normalization_method == "auto":
        return _normalize_auto(image)
    if normalization_method == "uint8":
        return _clip_unit(image.astype(np.float32) / 255.0)
    if normalization_method == "uint16":
        return _clip_unit(image.astype(np.float32) / 65535.0)
    if normalization_method == "min_max":
        return _normalize_min_max(image.astype(np.float32))
    if normalization_method == "percentile":
        return _normalize_percentile(
            image.astype(np.float32),
            percentile_range=percentile_range,
        )
    raise ValueError(
        f"不支持的normalization_method: {normalization_method}"
    )


def _normalize_auto(image: np.ndarray) -> np.ndarray:
    image_float = image.astype(np.float32)
    _validate_finite(image_float)
    if image_float.size == 0:
        return image_float
    image_min = float(image_float.min())
    image_max = float(image_float.max())
    if image_min >= 0.0 and image_max <= 1.0:
        return image_float
    if np.issubdtype(image.dtype, np.integer):
        if image.dtype == np.uint16:
            return _clip_unit(image_float / 65535.0)
        return _clip_unit(image_float / 255.0)
    if image_min >= 0.0 and image_max <= 255.0:
        return _clip_unit(image_float / 255.0)
    if image_min >= 0.0 and image_max <= 65535.0:
        return _clip_unit(image_float / 65535.0)
    raise ValueError(
        "normalization_method='auto'仅支持非负单位范围、uint8或uint16类范围; "
        "请显式使用min_max或percentile"
    )


def _normalize_min_max(image: np.ndarray) -> np.ndarray:
    _validate_finite(image)
    if image.size == 0:
        return image
    image_min = float(image.min())
    image_max = float(image.max())
    if image_max == image_min:
        return np.zeros_like(image, dtype=np.float32)
    return _clip_unit((image - image_min) / (image_max - image_min))


def _normalize_percentile(
    image: np.ndarray,
    *,
    percentile_range: tuple[float, float],
) -> np.ndarray:
    _validate_finite(image)
    if image.size == 0:
        return image
    lower_percentile, upper_percentile = percentile_range
    if not 0.0 <= lower_percentile < upper_percentile <= 100.0:
        raise ValueError(
            "percentile_range须满足0 <= lower < upper <= 100"
        )
    lower_value, upper_value = np.percentile(
        image,
        [lower_percentile, upper_percentile],
    )
    if upper_value == lower_value:
        return np.zeros_like(image, dtype=np.float32)
    clipped = np.clip(image, lower_value, upper_value)
    return _clip_unit((clipped - lower_value) / (upper_value - lower_value))


def _clip_unit(image: np.ndarray) -> np.ndarray:
    return np.clip(image, 0.0, 1.0).astype(np.float32)


def _validate_finite(image: np.ndarray) -> None:
    if not np.all(np.isfinite(image)):
        raise ValueError(
            "图像包含非有限值"
        )

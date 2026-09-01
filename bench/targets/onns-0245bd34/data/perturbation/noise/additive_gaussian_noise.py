from __future__ import annotations

import numpy as np


def add_additive_gaussian_noise(
    image: np.ndarray,
    *,
    sigma: float,
    random_generator: np.random.Generator | None = None,
) -> np.ndarray:
    """
    向归一化浮点图像添加截断高斯噪声

    Args:
        image:            输入归一化图像数组
        sigma:            高斯噪声标准差
        random_generator: 随机数生成器，None则使用默认生成器

    Returns:
        添加噪声并截断至[0, 1]的图像数组
    """
    if random_generator is not None:
        generator = random_generator
    else:
        generator = np.random.default_rng()
    noise = generator.normal(0.0, sigma, size=image.shape).astype(np.float32)
    return np.clip(image.astype(np.float32, copy=False) + noise, 0.0, 1.0)

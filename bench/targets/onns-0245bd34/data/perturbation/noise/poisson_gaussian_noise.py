from __future__ import annotations

import numpy as np


def add_poisson_gaussian_noise(
    image: np.ndarray,
    *,
    peak_photons: float,
    read_noise_sigma: float,
    random_seed: int | None = None,
) -> np.ndarray:
    """
    向归一化图像添加Poisson光子噪声和Gaussian读出噪声

    Args:
        image:            归一化输入图像
        peak_photons:     图像强度1对应的光子数
        read_noise_sigma: 加性读出噪声标准差
        random_seed:      可选确定性随机种子

    Returns:
        裁剪到归一化范围内的float32噪声图像

    Raises:
        ValueError: 当光子数非正或读出噪声为负时抛出
    """
    if peak_photons <= 0.0:
        raise ValueError(
            "peak_photons必须为正数"
        )
    if read_noise_sigma < 0.0:
        raise ValueError(
            "read_noise_sigma必须为非负数"
        )

    random_generator = np.random.default_rng(random_seed)
    clipped_image = np.clip(image.astype(np.float32, copy=False), 0.0, 1.0)
    noisy_photon_image = (
        random_generator.poisson(clipped_image * peak_photons)
        .astype(np.float32)
        / peak_photons
    )
    read_noise = random_generator.normal(
        0.0,
        read_noise_sigma,
        size=clipped_image.shape,
    ).astype(np.float32)
    return np.clip(noisy_photon_image + read_noise, 0.0, 1.0).astype(np.float32, copy=False)

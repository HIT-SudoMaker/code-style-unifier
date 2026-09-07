from __future__ import annotations

import numpy as np


def point_spread_function_from_pupil_function(pupil_function: np.ndarray) -> np.ndarray:
    """
    根据复数pupil构建归一化点扩散函数

    Args:
        pupil_function: 复数pupil数组

    Returns:
        能量总和为1的float32点扩散函数

    Raises:
        ValueError: 当pupil产生零能量时抛出
    """
    field = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(pupil_function)))
    intensity = np.abs(field) ** 2
    total_energy = float(intensity.sum())
    if total_energy <= 0.0:
        raise ValueError(
            "pupil产生零能量PSF"
        )
    return (intensity / total_energy).astype(np.float32)


def optical_transfer_function_from_point_spread_function(
    point_spread_function: np.ndarray,
) -> np.ndarray:
    """
    根据点扩散函数构建DC归一化光学传递函数

    Args:
        point_spread_function: 点扩散函数数组

    Returns:
        DC增益归一化为1的complex64光学传递函数

    Raises:
        ValueError: 当点扩散函数具有零DC响应时抛出
    """
    optical_transfer_function = np.fft.fftshift(
        np.fft.fft2(np.fft.ifftshift(point_spread_function))
    )
    center = tuple(size // 2 for size in point_spread_function.shape)
    normalizer = optical_transfer_function[center]
    if np.isclose(abs(normalizer), 0.0):
        raise ValueError(
            "PSF产生零DC响应OTF"
        )
    return (optical_transfer_function / normalizer).astype(np.complex64)

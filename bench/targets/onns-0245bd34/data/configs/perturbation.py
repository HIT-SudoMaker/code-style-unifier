from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

import numpy as np


@dataclass(slots=True, frozen=True)
class AdditiveGaussianNoiseConfig:
    """
    描述加性高斯噪声算子配置
    """

    sigma: float


@dataclass(slots=True, frozen=True)
class GaussianBlurConfig:
    """
    描述高斯模糊算子配置
    """

    kernel_size: int


@dataclass(slots=True, frozen=True)
class DefocusBlurConfig:
    """
    描述离焦模糊算子配置
    """

    radius: int


@dataclass(slots=True, frozen=True)
class PoissonGaussianNoiseConfig:
    """
    描述泊松-高斯噪声算子配置
    """

    peak_photons: float
    read_noise_sigma: float


@dataclass(slots=True, frozen=True)
class CannyEdgesConfig:
    """
    描述Canny边缘提取算子配置
    """

    threshold1: float = 10.0
    threshold2: float = 20.0


@dataclass(slots=True, frozen=True)
class SobelEdgesConfig:
    """
    鎻忚堪Sobel杈圭紭鎻愬彇绠楀瓙閰嶇疆
    """

    kernel_size: int = 3


@dataclass(slots=True, frozen=True)
class LaplacianOfGaussianEdgesConfig:
    """
    鎻忚堪LoG杈圭紭鎻愬彇绠楀瓙閰嶇疆
    """

    kernel_size: int = 3
    sigma: float = 0.0


@dataclass(slots=True, frozen=True)
class PsfConvolutionConfig:
    """
    描述点扩散函数卷积算子配置
    """

    kernel: np.ndarray

    def __post_init__(self) -> None:
        """
        冻结点扩散函数卷积核副本
        """
        kernel = np.array(self.kernel, copy=True)
        kernel.setflags(write=False)
        object.__setattr__(self, "kernel", kernel)


PerturbationOperationConfig: TypeAlias = (
    AdditiveGaussianNoiseConfig
    | GaussianBlurConfig
    | DefocusBlurConfig
    | PoissonGaussianNoiseConfig
    | CannyEdgesConfig
    | SobelEdgesConfig
    | LaplacianOfGaussianEdgesConfig
    | PsfConvolutionConfig
)


@dataclass(slots=True, frozen=True)
class PerturbationConfig:
    """
    描述由有序算子组成的扰动阶段配置
    """

    operations: tuple[PerturbationOperationConfig, ...] = field(default_factory=tuple)
    degradation_seed: int | None = None

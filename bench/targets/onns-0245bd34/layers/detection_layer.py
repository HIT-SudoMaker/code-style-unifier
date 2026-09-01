from __future__ import annotations

import torch
import torch.nn as nn

from ._validation import (
    normalize_array_resolution,
    validate_bool,
    validate_complex_input_field,
    validate_same_device,
)


class DetectionLayer(nn.Module):
    """
    检测层
    """

    def __init__(
        self,
        array_resolution: tuple[int, int],
        is_normalization_enabled: bool = False,
    ) -> None:
        """
        检测层

        Args:
            array_resolution:          光场阵列分辨率
            is_normalization_enabled:  是否启用逐样本峰值归一化

        Raises:
            ValueError: 阵列分辨率或归一化开关无效
        """
        super().__init__()

        self._height, self._width = normalize_array_resolution(array_resolution)
        self.register_buffer("array_resolution", torch.tensor([self._height, self._width]))
        validate_bool("is_normalization_enabled", is_normalization_enabled)
        self.is_normalization_enabled = is_normalization_enabled

    def _validate_input_field(self, input_field: torch.Tensor) -> None:
        validate_complex_input_field(input_field, height=self._height, width=self._width)
        validate_same_device(input_field, self.array_resolution, "探测层")

    def forward(self, input_field: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        Args:
            input_field: 输入复数光场张量，dtype 必须为 torch.complex64

        Returns:
            torch.float32 光强张量，启用归一化时按样本最大值归一化

        Raises:
            ValueError: 输入光场契约无效
        """
        self._validate_input_field(input_field)
        intensity = input_field.abs().square()
        if not self.is_normalization_enabled:
            return intensity
        peak = intensity.amax(dim=(-2, -1), keepdim=True)
        safe_peak = torch.where(peak > 0, peak, torch.ones_like(peak))
        return intensity / safe_peak

    def extra_repr(self) -> str:
        """
        返回层参数表示
        """
        return (
            f"array_resolution=({self._height}, {self._width}), "
            f"is_normalization_enabled={self.is_normalization_enabled}"
        )

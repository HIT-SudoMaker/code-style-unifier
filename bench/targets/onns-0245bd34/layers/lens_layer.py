from __future__ import annotations

from collections.abc import Callable
import math

import torch
import torch.nn as nn

from ._validation import (
    force_real_single_precision,
    normalize_array_resolution,
    validate_complex_input_field,
    validate_nonzero_scalar,
    validate_positive_scalar,
    validate_same_device,
)


class LensLayer(nn.Module):
    """
    透镜层
    """

    def __init__(
        self,
        wavelength: float,
        focal_length: float,
        pixel_size: float,
        array_resolution: tuple[int, int],
    ) -> None:
        """
        透镜层

        Args:
            wavelength:       工作波长
            focal_length:     透镜焦距
            pixel_size:       像素物理尺寸
            array_resolution: 光场阵列分辨率

        Raises:
            ValueError: 物理参数或阵列分辨率无效
        """
        super().__init__()

        validate_positive_scalar("工作波长", wavelength)
        validate_nonzero_scalar("透镜焦距", focal_length)
        validate_positive_scalar("像素尺寸", pixel_size)

        self._height, self._width = normalize_array_resolution(array_resolution)
        self.register_buffer("wavelength", torch.tensor(float(wavelength), dtype=torch.float32))
        self.register_buffer("focal_length", torch.tensor(float(focal_length), dtype=torch.float32))
        self.register_buffer("pixel_size", torch.tensor(float(pixel_size), dtype=torch.float32))
        self.register_buffer(
            "wavenumber",
            torch.tensor(math.tau / float(wavelength), dtype=torch.float32),
        )
        self.register_buffer("array_resolution", torch.tensor([self._height, self._width]))

        self._initialize_lens_phase()

    def _initialize_lens_phase(self) -> None:
        pixel_size = self.pixel_size.item()
        wavenumber = self.wavenumber.item()
        focal_length = self.focal_length.item()

        y_coordinates = (
            torch.arange(
                self._height,
                dtype=self.pixel_size.dtype,
                device=self.pixel_size.device,
            )
            - (self._height - 1) / 2.0
        ) * pixel_size
        x_coordinates = (
            torch.arange(
                self._width,
                dtype=self.pixel_size.dtype,
                device=self.pixel_size.device,
            )
            - (self._width - 1) / 2.0
        ) * pixel_size
        y_coordinate_grid, x_coordinate_grid = torch.meshgrid(
            y_coordinates,
            x_coordinates,
            indexing="ij",
        )

        radius_squared = x_coordinate_grid.square() + y_coordinate_grid.square()
        raw_lens_phase = -wavenumber * radius_squared / (2.0 * focal_length)
        lens_phase = torch.remainder(raw_lens_phase, 2 * torch.pi)
        self.register_buffer("lens_phase", lens_phase, persistent=True)

    def _validate_input_field(self, input_field: torch.Tensor) -> None:
        validate_complex_input_field(input_field, height=self._height, width=self._width)
        validate_same_device(input_field, self.wavelength, "透镜层")

    def _apply(self, function: Callable[[torch.Tensor], torch.Tensor]) -> "LensLayer":
        result = super()._apply(function)
        super()._apply(force_real_single_precision)
        return result

    def forward(self, input_field: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        Args:
            input_field: 输入复数光场张量，dtype 必须为 torch.complex64

        Returns:
            经透镜相位调制后的 torch.complex64 复数光场张量

        Raises:
            ValueError: 输入光场形状、类型、分辨率或设备不符合要求
        """
        self._validate_input_field(input_field)
        lens_complex_mask = torch.exp(1j * self.lens_phase)
        return input_field * lens_complex_mask

    def get_lens_phase_information(self) -> torch.Tensor:
        """
        返回透镜相位分布
        """
        return self.lens_phase.clone()

    def extra_repr(self) -> str:
        """
        返回层参数表示
        """
        return (
            f"wavelength={self.wavelength.item():.3g}, "
            f"focal_length={self.focal_length.item():.3g}, "
            f"pixel_size={self.pixel_size.item():.3g}, "
            f"array_resolution=({self._height}, {self._width})"
        )

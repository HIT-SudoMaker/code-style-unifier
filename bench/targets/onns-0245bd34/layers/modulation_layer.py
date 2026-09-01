from __future__ import annotations

from collections.abc import Callable

import torch
import torch.nn as nn

from ._validation import (
    _format_supported_values,
    force_real_single_precision,
    normalize_array_resolution,
    validate_complex_input_field,
    validate_same_device,
)

SUPPORTED_PHASE_PARAMETERIZATIONS = ("sigmoid", "direct")
SUPPORTED_PHASE_INITIALIZATIONS = ("normal", "zeros", "uniform")


class ModulationLayer(nn.Module):
    """
    调制层
    """

    def __init__(
        self,
        array_resolution: tuple[int, int],
        phase_parameterization: str = "sigmoid",
        phase_initialization: str = "normal",
    ) -> None:
        """
        调制层

        Args:
            array_resolution:       光场阵列分辨率
            phase_parameterization: 相位参数化方式
            phase_initialization:   相位初始化方式

        Raises:
            ValueError: 阵列分辨率、相位参数化方式或相位初始化方式无效
        """
        super().__init__()

        self._height, self._width = normalize_array_resolution(array_resolution)
        if phase_parameterization not in SUPPORTED_PHASE_PARAMETERIZATIONS:
            raise ValueError(
                _format_supported_values(
                    "phase_parameterization",
                    "sigmoid或direct",
                    phase_parameterization,
                )
            )
        if phase_initialization not in SUPPORTED_PHASE_INITIALIZATIONS:
            raise ValueError(
                _format_supported_values(
                    "phase_initialization",
                    "normal、zeros或uniform",
                    phase_initialization,
                )
            )

        self.register_buffer("array_resolution", torch.tensor([self._height, self._width]))
        self.phase_parameterization = str(phase_parameterization)
        self.phase_initialization = str(phase_initialization)
        self.modulation_phase = nn.Parameter(self._initialize_modulation_phase())

    def _initialize_modulation_phase(self) -> torch.Tensor:
        if self.phase_initialization == "normal":
            return torch.randn(self._height, self._width, dtype=torch.float32) * 0.5
        if self.phase_initialization == "uniform":
            return torch.rand(self._height, self._width, dtype=torch.float32)
        return torch.zeros(self._height, self._width, dtype=torch.float32)

    def _validate_input_field(self, input_field: torch.Tensor) -> None:
        validate_complex_input_field(input_field, height=self._height, width=self._width)
        validate_same_device(input_field, self.modulation_phase, "调制层")

    def _compute_effective_phase(self) -> torch.Tensor:
        if self.phase_parameterization == "direct":
            return torch.remainder(self.modulation_phase * 2 * torch.pi, 2 * torch.pi)
        return torch.sigmoid(self.modulation_phase) * 2 * torch.pi

    def _apply(self, function: Callable[[torch.Tensor], torch.Tensor]) -> "ModulationLayer":
        result = super()._apply(function)
        super()._apply(force_real_single_precision)
        return result

    def forward(self, input_field: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        Args:
            input_field: 输入复数光场张量，dtype 必须为 torch.complex64

        Returns:
            经相位调制后的 torch.complex64 复数光场张量

        Raises:
            ValueError: 输入光场形状、类型、分辨率或设备不符合要求
        """
        self._validate_input_field(input_field)
        effective_phase = self._compute_effective_phase()
        modulation_complex = torch.exp(1j * effective_phase)
        return input_field * modulation_complex

    def get_modulation_phase_information(self) -> torch.Tensor:
        """
        返回有效调制相位
        """
        return self._compute_effective_phase()

    def extra_repr(self) -> str:
        """
        返回层参数表示
        """
        return (
            f"array_resolution=({self._height}, {self._width}), "
            f"phase_parameterization={self.phase_parameterization}, "
            f"phase_initialization={self.phase_initialization}"
        )

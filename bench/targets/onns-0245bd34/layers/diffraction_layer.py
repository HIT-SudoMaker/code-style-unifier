from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
import math

import torch
import torch.fft as fft
import torch.nn as nn

from ._validation import (
    _format_supported_values,
    normalize_array_resolution,
    validate_bool,
    validate_complex_input_field,
    validate_positive_scalar,
    validate_same_device,
)

_EPSILON = 1e-10
_MAX_CACHE_ENTRIES = 10


def _refresh_loaded_diffraction_state(
    module: "DiffractionLayer",
    incompatible_keys: object,
) -> None:
    del incompatible_keys
    module._wavelength_value = float(module.wavelength.detach().cpu().item())
    module._pixel_size_value = float(module.pixel_size.detach().cpu().item())
    module._register_physical_buffers(
        dtype=module.wavelength.dtype,
        device=module.wavelength.device,
    )
    module._height = int(module.array_resolution[0].item())
    module._width = int(module.array_resolution[1].item())
    module._initialize_frequency_grid()
    module._clear_cache()


class DiffractionLayer(nn.Module):
    """
    衍射层
    """

    def __init__(
        self,
        wavelength: float,
        pixel_size: float,
        array_resolution: tuple[int, int],
        is_cache_enabled: bool = True,
    ) -> None:
        """
        衍射层

        Args:
            wavelength:       工作波长
            pixel_size:       像素物理尺寸
            array_resolution: 光场阵列分辨率
            is_cache_enabled: 是否启用传递函数缓存

        Raises:
            ValueError: 物理参数、阵列分辨率或缓存开关无效
        """
        super().__init__()

        validate_positive_scalar("工作波长", wavelength)
        validate_positive_scalar("像素尺寸", pixel_size)

        self._wavelength_value = float(wavelength)
        self._pixel_size_value = float(pixel_size)
        self._height, self._width = normalize_array_resolution(array_resolution)
        self._register_physical_buffers(dtype=torch.float32)
        self.register_buffer("array_resolution", torch.tensor([self._height, self._width]))

        validate_bool("is_cache_enabled", is_cache_enabled)
        self.is_cache_enabled = is_cache_enabled
        self._initialize_frequency_grid()
        self._cache_hits = 0
        self._cache_misses = 0
        self.register_load_state_dict_post_hook(_refresh_loaded_diffraction_state)

        if self.is_cache_enabled:
            self._transfer_function_cache: OrderedDict[
                tuple[str, int | None, torch.dtype, float], torch.Tensor
            ] = OrderedDict()

    def _register_physical_buffers(
        self,
        *,
        dtype: torch.dtype,
        device: torch.device | None = None,
    ) -> None:
        self.register_buffer(
            "wavelength",
            torch.tensor(self._wavelength_value, dtype=dtype, device=device),
        )
        self.register_buffer(
            "wavenumber",
            torch.tensor(math.tau / self._wavelength_value, dtype=dtype, device=device),
        )
        self.register_buffer(
            "pixel_size",
            torch.tensor(self._pixel_size_value, dtype=dtype, device=device),
        )

    def _initialize_frequency_grid(self) -> None:
        pixel_size = self.pixel_size.item()
        vertical_frequency = fft.fftshift(
            fft.fftfreq(
                self._height,
                d=pixel_size,
                dtype=self.pixel_size.dtype,
                device=self.pixel_size.device,
            )
        )
        horizontal_frequency = fft.fftshift(
            fft.fftfreq(
                self._width,
                d=pixel_size,
                dtype=self.pixel_size.dtype,
                device=self.pixel_size.device,
            )
        )
        vertical_frequency_grid, horizontal_frequency_grid = torch.meshgrid(
            vertical_frequency,
            horizontal_frequency,
            indexing="ij",
        )
        frequency_grid_squared = (
            vertical_frequency_grid.square()
            + horizontal_frequency_grid.square()
            + _EPSILON
        )
        self.register_buffer("frequency_grid_squared", frequency_grid_squared, persistent=False)

        frequency_cutoff_squared = (1.0 / self.wavelength.item()) ** 2
        frequency_mask = frequency_grid_squared <= frequency_cutoff_squared
        self.register_buffer("frequency_mask", frequency_mask, persistent=False)

    def _validate_input_field(self, input_field: torch.Tensor) -> None:
        validate_complex_input_field(input_field, height=self._height, width=self._width)
        validate_same_device(input_field, self.wavelength, "衍射层")

    def _compute_transfer_function(
        self,
        propagation_distance: float,
        complex_dtype: torch.dtype,
        device: torch.device,
    ) -> torch.Tensor:
        cache_key = (device.type, device.index, complex_dtype, float(propagation_distance))
        if self.is_cache_enabled and cache_key in self._transfer_function_cache:
            self._transfer_function_cache.move_to_end(cache_key)
            self._cache_hits += 1
            return self._transfer_function_cache[cache_key]

        wavelength_squared = self.wavelength**2
        propagation_factor = torch.clamp(
            1.0 - wavelength_squared * self.frequency_grid_squared,
            min=0.0,
        ).to(complex_dtype)
        normalized_wavevector_z = torch.sqrt(propagation_factor)

        propagation_phase = self.wavenumber * normalized_wavevector_z
        propagation_phase = propagation_phase * propagation_distance

        transfer_phase = torch.exp(1j * propagation_phase)
        transfer_function = transfer_phase * self.frequency_mask

        if self.is_cache_enabled:
            self._cache_misses += 1
            if len(self._transfer_function_cache) >= _MAX_CACHE_ENTRIES:
                self._transfer_function_cache.popitem(last=False)
            self._transfer_function_cache[cache_key] = transfer_function

        return transfer_function

    def _clear_cache(self) -> None:
        if self.is_cache_enabled:
            self._transfer_function_cache.clear()

    def _apply(self, function: Callable[[torch.Tensor], torch.Tensor]) -> "DiffractionLayer":
        self._clear_cache()
        result = super()._apply(function)
        self._register_physical_buffers(dtype=torch.float32, device=self.wavelength.device)
        self._initialize_frequency_grid()
        self._clear_cache()
        return result

    def forward(self, input_field: torch.Tensor, propagation_distance: float) -> torch.Tensor:
        """
        前向传播

        Args:
            input_field:          输入复数光场张量，dtype 必须为 torch.complex64
            propagation_distance: 传播距离

        Returns:
            经角谱法传播后的 torch.complex64 复数光场张量

        Raises:
            ValueError: 传播距离或输入光场契约无效
        """
        validate_positive_scalar("传播距离", propagation_distance)

        self._validate_input_field(input_field)
        transfer_function = self._compute_transfer_function(
            propagation_distance,
            complex_dtype=input_field.dtype,
            device=input_field.device,
        )
        input_spectrum = fft.fftshift(fft.fft2(input_field), dim=(-2, -1))
        output_spectrum = input_spectrum * transfer_function
        output_field = fft.ifft2(fft.ifftshift(output_spectrum, dim=(-2, -1)))
        return output_field

    def get_transfer_function_information(
        self,
        propagation_distance: float,
        return_type: str,
    ) -> torch.Tensor:
        """
        返回传递函数信息

        Args:
            propagation_distance: 传播距离
            return_type:          返回类型，可选phase、amplitude或complex

        Returns:
            传递函数的相位、振幅或 complex64 复数形式张量

        Raises:
            ValueError: 传播距离或返回类型无效
        """
        validate_positive_scalar("传播距离", propagation_distance)
        if return_type not in ["phase", "amplitude", "complex"]:
            raise ValueError(
                _format_supported_values(
                    "return_type",
                    "phase、amplitude或complex",
                    return_type,
                )
            )

        with torch.no_grad():
            transfer_function = self._compute_transfer_function(
                propagation_distance,
                complex_dtype=torch.complex64,
                device=self.wavelength.device,
            )
            if return_type == "phase":
                return torch.angle(transfer_function)
            if return_type == "amplitude":
                return torch.abs(transfer_function)
            return transfer_function.clone()

    def get_cache_statistics(self) -> dict[str, int | bool]:
        """
        返回缓存统计信息

        Returns:
            包含缓存启用状态、条目数、命中次数和未命中次数的字典
        """
        return {
            "is_enabled": self.is_cache_enabled,
            "entries": len(self._transfer_function_cache) if self.is_cache_enabled else 0,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
        }

    def extra_repr(self) -> str:
        """
        返回层参数表示
        """
        return (
            f"wavelength={self.wavelength.item():.3g}, "
            f"pixel_size={self.pixel_size.item():.3g}, "
            f"array_resolution=({self._height}, {self._width}), "
            f"is_cache_enabled={self.is_cache_enabled}"
        )

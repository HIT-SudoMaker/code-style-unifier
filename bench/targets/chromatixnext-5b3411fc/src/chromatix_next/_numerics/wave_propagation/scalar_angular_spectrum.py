from __future__ import annotations

from typing import NamedTuple

import torch

from .radiative_spectrum import (
    _embed_computational_window,
    _extract_computational_window,
    _radiative_plane_transfer,
)
from .spatial_frequency import apply_frequency_transfer, to_frequency


class ScalarAngularSpectrumSupportStatistics(NamedTuple):
    """
    逐光谱的角谱存活频点、支持比例与保留功率比例

    """

    surviving_frequency_count: torch.Tensor
    support_ratio: torch.Tensor
    retained_power_ratio: torch.Tensor


class ScalarAngularSpectrumCalculation(NamedTuple):
    """
    标量角谱传递张量及其尚未解释的方法适用性事实

    """

    transfer: torch.Tensor
    has_narrow_alias_band: torch.Tensor


def scalar_angular_spectrum_support_statistics(
    *,
    envelope: torch.Tensor,
    transfer: torch.Tensor,
    computational_counts: tuple[int, int],
    padding: tuple[int, int],
) -> ScalarAngularSpectrumSupportStatistics:
    """
    汇总角谱传递张量的频率支撑与输入频域保留功率

    """
    embedded = _embed_computational_window(
        envelope=envelope,
        computational_counts=computational_counts,
        padding=padding,
    )
    frequency_values = to_frequency(embedded)
    frequency_support = transfer.abs() > 0.0
    supported_frequency_values = (
        frequency_values * frequency_support.unsqueeze(-3)
    )
    reduction_axes = (-3, -2, -1)
    total_power = frequency_values.abs().square().sum(dim=reduction_axes)
    retained_power = (
        supported_frequency_values.abs().square().sum(dim=reduction_axes)
    )
    has_input_power = total_power > 0.0
    safe_total_power = torch.where(
        has_input_power,
        total_power,
        torch.ones_like(total_power),
    )
    return ScalarAngularSpectrumSupportStatistics(
        surviving_frequency_count=torch.count_nonzero(
            frequency_support,
            dim=(-2, -1),
        ),
        support_ratio=frequency_support.to(
            dtype=transfer.real.dtype,
        ).mean(dim=(-2, -1)),
        retained_power_ratio=torch.where(
            has_input_power,
            retained_power / safe_total_power,
            torch.zeros_like(total_power),
        ),
    )


def scalar_angular_spectrum_calculation(
    *,
    computational_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    displacement: tuple[torch.Tensor, torch.Tensor],
    axial_distance: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    device: torch.device,
) -> ScalarAngularSpectrumCalculation:
    """
    计算每个光谱分量的标量角谱复传递张量

    """
    plane_transfer = _radiative_plane_transfer(
        computational_counts=computational_counts,
        signed_spacing=signed_spacing,
        displacement=displacement,
        axial_distance=axial_distance,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        real_dtype=real_dtype,
        complex_dtype=complex_dtype,
        device=device,
    )
    return ScalarAngularSpectrumCalculation(
        transfer=plane_transfer.transfer,
        has_narrow_alias_band=plane_transfer.has_narrow_alias_band,
    )


def propagate_scalar_angular_spectrum(
    *,
    envelope: torch.Tensor,
    transfer: torch.Tensor,
    computational_counts: tuple[int, int],
    window_counts: tuple[int, int],
    padding: tuple[int, int],
) -> torch.Tensor:
    """
    以传递张量作用于包络：零延拓、FFT、乘传递、IFFT、抽取中心窗口

    """
    embedded = _embed_computational_window(
        envelope=envelope,
        computational_counts=computational_counts,
        padding=padding,
    )

    propagated = apply_frequency_transfer(
        embedded,
        transfer,
    )

    return _extract_computational_window(
        envelope=propagated,
        window_counts=window_counts,
        padding=padding,
    )

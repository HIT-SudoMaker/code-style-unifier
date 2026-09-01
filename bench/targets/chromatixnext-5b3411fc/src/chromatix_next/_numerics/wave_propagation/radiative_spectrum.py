from __future__ import annotations

import math
from typing import NamedTuple

import torch

from .._certified_predicates import (
    scaled_squared_norm_difference_sign,
    squared_reference_minus_squared_factor_extra_factor_sign,
)
from ..complex_phase import _unit_phasor_from_cycles
from ..wave_number import medium_wave_numbers


class _RadiativeSpectrumFacts(NamedTuple):
    """
    承载辐射谱、支撑与传播相位的共享事实

    """

    wave_number: torch.Tensor
    transverse_wavevector_y: torch.Tensor
    transverse_wavevector_x: torch.Tensor
    longitudinal_wave_number: torch.Tensor
    radiative_support: torch.Tensor
    alias_support: torch.Tensor
    has_narrow_alias_band: torch.Tensor
    axial_cycles: torch.Tensor
    shift_cycles: torch.Tensor
class _ComputationalWindowFacts(NamedTuple):
    """
    承载传播计算窗口的尺寸、填充与支撑状态

    """

    computational_counts: tuple[int, int]
    padding: tuple[int, int]
    is_outside_support: torch.Tensor


def _computational_window_facts(
    *,
    input_counts: tuple[int, int],
    sample_spacing: tuple[torch.Tensor, torch.Tensor],
    displacement: tuple[torch.Tensor, torch.Tensor],
    exterior: str,
) -> _ComputationalWindowFacts:
    if exterior == "periodic":
        return _ComputationalWindowFacts(
            computational_counts=input_counts,
            padding=(0, 0),
            is_outside_support=torch.zeros(
                (),
                dtype=torch.bool,
                device=displacement[0].device,
            ),
        )
    computational_counts = (
        3 * input_counts[0],
        3 * input_counts[1],
    )
    supported_y = (
        input_counts[0]
        * sample_spacing[0].to(
            device=displacement[0].device,
            dtype=displacement[0].dtype,
        ).abs()
    )
    supported_x = (
        input_counts[1]
        * sample_spacing[1].to(
            device=displacement[1].device,
            dtype=displacement[1].dtype,
        ).abs()
    )
    tolerance_y = (
        8.0 * torch.finfo(displacement[0].dtype).eps * supported_y
    )
    tolerance_x = (
        8.0 * torch.finfo(displacement[1].dtype).eps * supported_x
    )
    is_outside_support = (
        (displacement[0].abs() > supported_y + tolerance_y)
        | (displacement[1].abs() > supported_x + tolerance_x)
    ).detach()
    return _ComputationalWindowFacts(
        computational_counts=computational_counts,
        padding=input_counts,
        is_outside_support=is_outside_support,
    )


def _embed_computational_window(
    *,
    envelope: torch.Tensor,
    computational_counts: tuple[int, int],
    padding: tuple[int, int],
) -> torch.Tensor:
    if padding == (0, 0):
        return envelope
    shape = (*envelope.shape[:-2], *computational_counts)
    embedded = torch.zeros(
        shape,
        dtype=envelope.dtype,
        device=envelope.device,
    )
    padding_y, padding_x = padding
    embedded[
        ...,
        padding_y : padding_y + envelope.shape[-2],
        padding_x : padding_x + envelope.shape[-1],
    ] = envelope
    return embedded


def _extract_computational_window(
    *,
    envelope: torch.Tensor,
    window_counts: tuple[int, int],
    padding: tuple[int, int],
) -> torch.Tensor:
    if padding == (0, 0):
        return envelope
    padding_y, padding_x = padding
    return envelope[
        ...,
        padding_y : padding_y + window_counts[0],
        padding_x : padding_x + window_counts[1],
    ].contiguous()


def _radiative_spectrum_facts(
    *,
    computational_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    displacement: tuple[torch.Tensor, torch.Tensor],
    axial_distance: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    real_dtype: torch.dtype,
    device: torch.device,
) -> _RadiativeSpectrumFacts:
    height, width = computational_counts
    spacing_y = signed_spacing[0].to(dtype=real_dtype, device=device)
    spacing_x = signed_spacing[1].to(dtype=real_dtype, device=device)
    frequency_y = (
        torch.fft.fftfreq(height, d=1.0, dtype=real_dtype, device=device)
        / spacing_y
    )
    frequency_x = (
        torch.fft.fftfreq(width, d=1.0, dtype=real_dtype, device=device)
        / spacing_x
    )
    frequency_grid_y, frequency_grid_x = torch.meshgrid(
        frequency_y,
        frequency_x,
        indexing="ij",
    )
    wavelengths_real = wavelengths.to(dtype=real_dtype, device=device)
    refractive_indices_real = refractive_indices.to(dtype=real_dtype, device=device)
    wave_number = medium_wave_numbers(
        wavelengths=wavelengths_real,
        refractive_indices=refractive_indices_real,
    ).reshape(-1, 1, 1)
    transverse_wavevector_y = (2.0 * math.pi * frequency_grid_y).unsqueeze(0)
    transverse_wavevector_x = (2.0 * math.pi * frequency_grid_x).unsqueeze(0)
    negative_transverse_squared = -(
        transverse_wavevector_y.square() + transverse_wavevector_x.square()
    )
    longitudinal_squared = wave_number.square() + negative_transverse_squared
    # support 判定委托 certified 精确符号而避免 grazing 舍入误判
    longitudinal_squared_sign = scaled_squared_norm_difference_sign(
        reference=wave_number,
        vector=torch.stack(
            (transverse_wavevector_y, transverse_wavevector_x),
            dim=-1,
        ),
    )
    radiative_support = (longitudinal_squared_sign > 0).detach()
    # 连续纵向波数保持普通可微单一路径并在不可表示通道携带保守 0 占位
    longitudinal_wave_number = torch.sqrt(
        torch.clamp(longitudinal_squared, min=0.0),
    )
    displacement_y = displacement[0].to(dtype=real_dtype, device=device)
    displacement_x = displacement[1].to(dtype=real_dtype, device=device)
    alias_support, has_narrow_alias_band = _alias_support_and_narrow_band(
        transverse_wavevector_y=transverse_wavevector_y,
        transverse_wavevector_x=transverse_wavevector_x,
        longitudinal_squared=longitudinal_squared,
        radiative_support=radiative_support,
        axial_distance=axial_distance,
        displacement_y=displacement_y,
        displacement_x=displacement_x,
        computational_counts=computational_counts,
        spacing_magnitudes=(spacing_y.abs(), spacing_x.abs()),
        refractive_indices=refractive_indices_real,
        wavelengths=wavelengths_real,
    )
    stable_residual = negative_transverse_squared / (
        longitudinal_wave_number + wave_number
    )
    axial_cycles = stable_residual * axial_distance.to(
        dtype=real_dtype,
        device=device,
    ).reshape(1, 1, 1) / (2.0 * math.pi)
    shift_cycles = (
        frequency_grid_y.unsqueeze(0) * displacement_y
        + frequency_grid_x.unsqueeze(0) * displacement_x
    )
    return _RadiativeSpectrumFacts(
        wave_number=wave_number,
        transverse_wavevector_y=transverse_wavevector_y,
        transverse_wavevector_x=transverse_wavevector_x,
        longitudinal_wave_number=longitudinal_wave_number,
        radiative_support=radiative_support,
        alias_support=alias_support,
        has_narrow_alias_band=has_narrow_alias_band,
        axial_cycles=axial_cycles,
        shift_cycles=shift_cycles,
    )


class _RadiativePlaneTransfer(NamedTuple):

    """
    承载平行平面辐射传递及其支撑事实

    """

    transfer: torch.Tensor
    support: torch.Tensor
    has_narrow_alias_band: torch.Tensor
    facts: _RadiativeSpectrumFacts


def _radiative_plane_transfer(
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
) -> _RadiativePlaneTransfer:
    facts = _radiative_spectrum_facts(
        computational_counts=computational_counts,
        signed_spacing=signed_spacing,
        displacement=displacement,
        axial_distance=axial_distance,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        real_dtype=real_dtype,
        device=device,
    )
    support = (facts.radiative_support & facts.alias_support).detach()
    transfer = _unit_phasor_from_cycles(facts.axial_cycles + facts.shift_cycles)
    transfer = torch.where(
        support,
        transfer,
        torch.zeros_like(transfer),
    ).to(dtype=complex_dtype)
    return _RadiativePlaneTransfer(
        transfer=transfer,
        support=support,
        has_narrow_alias_band=facts.has_narrow_alias_band,
        facts=facts,
    )


def _alias_support_and_narrow_band(
    *,
    transverse_wavevector_y: torch.Tensor,
    transverse_wavevector_x: torch.Tensor,
    longitudinal_squared: torch.Tensor,
    radiative_support: torch.Tensor,
    axial_distance: torch.Tensor,
    displacement_y: torch.Tensor,
    displacement_x: torch.Tensor,
    computational_counts: tuple[int, int],
    spacing_magnitudes: tuple[torch.Tensor, torch.Tensor],
    refractive_indices: torch.Tensor,
    wavelengths: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    height, width = computational_counts
    spacing_y, spacing_x = spacing_magnitudes
    # 带符号轴向距离：反向传播仅取共轭相位，不改支撑（位移判据对 d 偶）
    distance_signed = axial_distance.detach()
    distance_magnitude = distance_signed.abs()
    denominator_y = torch.sqrt(
        1.0 + (2.0 * distance_magnitude / (height * spacing_y)) ** 2,
    )
    denominator_x = torch.sqrt(
        1.0 + (2.0 * distance_magnitude / (width * spacing_x)) ** 2,
    )
    physical_limit = (refractive_indices / wavelengths).reshape(-1, 1, 1)
    limit_y = physical_limit / denominator_y
    limit_x = physical_limit / denominator_x
    fundamental_frequency_y = (
        0.0 if height <= 1 else 1.0 / (height * spacing_y)
    )
    fundamental_frequency_x = (
        0.0 if width <= 1 else 1.0 / (width * spacing_x)
    )
    is_narrow = torch.any(
        (
            (limit_y < fundamental_frequency_y)
            | (limit_x < fundamental_frequency_x)
        ).detach(),
    )
    longitudinal_wavevector_squared = longitudinal_squared
    # 辐射拓扑复用 _radiative_spectrum_facts 的 certified 结论
    is_radiative = radiative_support
    distance_per_spectrum = distance_signed.to(
        dtype=longitudinal_wavevector_squared.dtype,
        device=longitudinal_wavevector_squared.device,
    ).reshape(-1, 1, 1)
    half_extent_y = 0.5 * (height * spacing_y)
    half_extent_x = 0.5 * (width * spacing_x)
    distance_weighted_transverse_wavevector_y = (
        distance_per_spectrum * transverse_wavevector_y
    )
    distance_weighted_transverse_wavevector_x = (
        distance_per_spectrum * transverse_wavevector_x
    )
    admit_y = _admit_shifted_support_axis(
        distance_weighted_transverse_wavevector=(
            distance_weighted_transverse_wavevector_y
        ),
        boundary_low=displacement_y - half_extent_y,
        boundary_high=displacement_y + half_extent_y,
        longitudinal_wavevector_squared=longitudinal_wavevector_squared,
    )
    admit_x = _admit_shifted_support_axis(
        distance_weighted_transverse_wavevector=(
            distance_weighted_transverse_wavevector_x
        ),
        boundary_low=displacement_x - half_extent_x,
        boundary_high=displacement_x + half_extent_x,
        longitudinal_wavevector_squared=longitudinal_wavevector_squared,
    )
    support = (is_radiative & admit_y & admit_x).detach()
    return support, is_narrow


def _admit_shifted_support_axis(
    *,
    distance_weighted_transverse_wavevector: torch.Tensor,
    boundary_low: torch.Tensor,
    boundary_high: torch.Tensor,
    longitudinal_wavevector_squared: torch.Tensor,
) -> torch.Tensor:
    sign_xa = squared_reference_minus_squared_factor_extra_factor_sign(
        reference=distance_weighted_transverse_wavevector,
        squared_factor=boundary_low,
        extra_factor=longitudinal_wavevector_squared,
    )
    sign_xb = squared_reference_minus_squared_factor_extra_factor_sign(
        reference=distance_weighted_transverse_wavevector,
        squared_factor=boundary_high,
        extra_factor=longitudinal_wavevector_squared,
    )
    x_positive = distance_weighted_transverse_wavevector > 0.0
    x_non_negative = distance_weighted_transverse_wavevector >= 0.0
    low_negative = boundary_low < 0.0
    high_positive = boundary_high > 0.0
    lower_admit = torch.where(
        x_positive,
        low_negative | (sign_xa > 0),
        low_negative & (sign_xa < 0),
    )
    upper_admit = torch.where(
        x_non_negative,
        high_positive & (sign_xb < 0),
        high_positive | (sign_xb > 0),
    )
    return lower_admit & upper_admit

from __future__ import annotations

from typing import NamedTuple

import torch

from .radiative_spectrum import (
    _embed_computational_window,
    _extract_computational_window,
    _radiative_plane_transfer,
    _RadiativeSpectrumFacts,
)
from .spatial_frequency import to_frequency, to_space


class VectorAngularSpectrumCalculation(NamedTuple):
    """
    矢量角谱传递张量、辐射支撑与逐光谱波数事实

    """

    transfer: torch.Tensor
    support: torch.Tensor
    has_narrow_alias_band: torch.Tensor
    facts: _RadiativeSpectrumFacts


def vector_angular_spectrum_calculation(
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
) -> VectorAngularSpectrumCalculation:
    """
    计算每个光谱分量的矢量角谱复传递张量与辐射支撑

    传递构造与标量角谱共用 ``_radiative_plane_transfer``：严格 ``Q>0`` 辐射分类与
    联合二维位移判据一致，标量与矢量同支撑；偏振重建与横场校验留给施函数，由包络
    决定。

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
    return VectorAngularSpectrumCalculation(
        transfer=plane_transfer.transfer,
        support=plane_transfer.support,
        has_narrow_alias_band=plane_transfer.has_narrow_alias_band,
        facts=plane_transfer.facts,
    )


def propagate_vector_angular_spectrum(
    *,
    envelope: torch.Tensor,
    calculation: VectorAngularSpectrumCalculation,
    computational_counts: tuple[int, int],
    padding: tuple[int, int],
    is_full: bool,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    以已建传递张量作用于包络：零延拓、FFT、偏振重建或横场校验、乘传递、IFFT、抽取

    横向表示（两分量）在频域由横向波矢与纵向波数重建纵向分量；完整表示（三分量）
    则校验其在辐射支撑内满足波矢与电场正交。返回 ``(传播包络, 完整场是否横向)``。

    """
    facts = calculation.facts
    embedded = _embed_computational_window(
        envelope=envelope,
        computational_counts=computational_counts,
        padding=padding,
    )
    frequency_field = to_frequency(embedded)
    if is_full:
        is_full_field_transverse = _full_field_is_transverse(
            frequency_field=frequency_field,
            wave_number=facts.wave_number,
            transverse_wavevector_y=facts.transverse_wavevector_y,
            transverse_wavevector_x=facts.transverse_wavevector_x,
            longitudinal_wave_number=facts.longitudinal_wave_number,
            support=calculation.support,
        )
        vector_frequency_field = frequency_field
    else:
        is_full_field_transverse = torch.ones(
            (),
            dtype=torch.bool,
            device=envelope.device,
        )
        safe_longitudinal = torch.where(
            calculation.support,
            facts.longitudinal_wave_number,
            torch.ones_like(facts.longitudinal_wave_number),
        )
        field_x = frequency_field[..., 0, :, :]
        field_y = frequency_field[..., 1, :, :]
        field_z = -(
            facts.transverse_wavevector_x * field_x
            + facts.transverse_wavevector_y * field_y
        ) / safe_longitudinal
        field_z = torch.where(
            calculation.support,
            field_z,
            torch.zeros_like(field_z),
        )
        vector_frequency_field = torch.cat(
            (frequency_field, field_z.unsqueeze(-3)),
            dim=-3,
        )
    propagated_frequency = (
        vector_frequency_field
        * calculation.support.unsqueeze(-3)
        * calculation.transfer.unsqueeze(-3)
    )
    propagated = to_space(propagated_frequency)
    return (
        _extract_computational_window(
            envelope=propagated,
            window_counts=(envelope.shape[-2], envelope.shape[-1]),
            padding=padding,
        ),
        is_full_field_transverse,
    )


def _full_field_is_transverse(
    *,
    frequency_field: torch.Tensor,
    wave_number: torch.Tensor,
    transverse_wavevector_y: torch.Tensor,
    transverse_wavevector_x: torch.Tensor,
    longitudinal_wave_number: torch.Tensor,
    support: torch.Tensor,
) -> torch.Tensor:
    field_x = frequency_field[..., 0, :, :]
    field_y = frequency_field[..., 1, :, :]
    field_z = frequency_field[..., 2, :, :]
    residual = (
        transverse_wavevector_x * field_x
        + transverse_wavevector_y * field_y
        + longitudinal_wave_number * field_z
    ).abs()
    magnitude = torch.sqrt(
        field_x.abs().square()
        + field_y.abs().square()
        + field_z.abs().square(),
    )
    admitted_residual = torch.where(
        support,
        residual,
        torch.zeros_like(residual),
    )
    admitted_scale = torch.where(
        support,
        wave_number * magnitude,
        torch.zeros_like(magnitude),
    )
    maximum_residual = admitted_residual.amax(dim=(-2, -1))
    maximum_scale = admitted_scale.amax(dim=(-2, -1))
    tiny = torch.finfo(frequency_field.real.dtype).tiny
    tolerance = (
        128.0
        * torch.finfo(frequency_field.real.dtype).eps
        * torch.clamp(maximum_scale, min=tiny)
    )
    return torch.all(maximum_residual <= tolerance)

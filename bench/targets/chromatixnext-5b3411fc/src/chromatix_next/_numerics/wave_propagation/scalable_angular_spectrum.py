from __future__ import annotations

import math
from typing import NamedTuple

import torch

from .._certified_predicates import (
    squared_reference_minus_squared_factor_extra_factor_sign,
)
from ..complex_phase import _unit_phasor_from_cycles
from .radiative_spectrum import (
    _embed_computational_window,
    _radiative_spectrum_facts,
    _RadiativeSpectrumFacts,
)
from .scaled_fresnel import ScaledFresnelCalculation, propagate_scaled_fresnel


class ScalableAngularSpectrumPrecompensation(NamedTuple):
    """
    承载 SAS bounded scope（有界作用域）目标网格模型的预补偿与混叠判定

    该模型依据 Heintzmann、Loetgering 与 Wechsler（Optica 2023，
    DOI 10.1364/OPTICA.497809），不声明严格逆变换

    Attributes:
        transfer: 计算网格上的复预补偿传递张量
        has_narrow_alias_band: 目标网格是否留下过窄的无混叠频带

    """

    transfer: torch.Tensor
    has_narrow_alias_band: torch.Tensor


def scalable_angular_spectrum_precompensation(
    *,
    computational_counts: tuple[int, int],
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    axial_distance: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    device: torch.device,
) -> ScalableAngularSpectrumPrecompensation:
    """
    在计算网格上构造 SAS 预补偿传递张量

    残差相位以单一稳定形式 ``-(n·d/λ)·u²/(2·(1+s_z)²)`` 给出（``u=s_x²+s_y²``、
    ``s_z=sqrt(1-u)``），等价于精确角谱残差相位 ``d·(kz−k)`` 与共轭近轴 Fresnel
    残差相位 ``+d·k_perp²/(2k)`` 之和但不分别计算两单项后相加——避免近轴区两单项
    大小近似相反造成的灾难性抵消。辐射波数与辐射事实复用同一辐射谱所有者；SAS
    残差支撑按残差相位的横向导数带限于本模块自有（区别于标准 AS 的位移支撑），
    以逐轴严格 ``|d·s_a·u/(s_z·(1+s_z))| < L_a/2`` 经所有者本地多项式精确符号判定，
    不经 ``s_z`` 的舍入除法判定。轴向距离取带符号，使 ``p(d<0) = conj(p(|d|))``；
    支撑判据对距离取绝对值，故支撑对距离符号偶（反向传递为正向的共轭）。

    """

    zero_displacement = (
        torch.zeros((), dtype=real_dtype, device=device),
        torch.zeros((), dtype=real_dtype, device=device),
    )
    distance_signed = axial_distance.to(
        dtype=real_dtype,
        device=device,
    )
    facts = _radiative_spectrum_facts(
        computational_counts=computational_counts,
        signed_spacing=input_signed_spacing,
        displacement=zero_displacement,
        axial_distance=distance_signed,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        real_dtype=real_dtype,
        device=device,
    )
    support = _scalable_angular_spectrum_residual_support(
        facts=facts,
        computational_counts=computational_counts,
        signed_spacing=input_signed_spacing,
        axial_distance_signed=distance_signed,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        real_dtype=real_dtype,
        device=device,
    )
    cycles = _scalable_angular_spectrum_residual_cycles(
        facts=facts,
        axial_distance_signed=distance_signed,
    )
    transfer = torch.where(
        support,
        _unit_phasor_from_cycles(cycles),
        torch.zeros_like(cycles),
    ).to(dtype=complex_dtype)
    return ScalableAngularSpectrumPrecompensation(
        transfer=transfer,
        has_narrow_alias_band=facts.has_narrow_alias_band,
    )


def propagate_scalable_angular_spectrum(
    *,
    envelope: torch.Tensor,
    precompensation_transfer: torch.Tensor,
    fresnel_calculation: ScaledFresnelCalculation,
    computational_counts: tuple[int, int],
    padding: tuple[int, int],
    output_sample_counts: tuple[int, int],
    axial_distance: torch.Tensor,
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    device: torch.device,
) -> torch.Tensor:
    """
    以 SAS 预补偿继以带尺度 Fresnel 阶段评估目标网格包络

    """

    embedded = _embed_computational_window(
        envelope=envelope,
        computational_counts=computational_counts,
        padding=padding,
    )
    precompensated = _apply_precompensation(embedded, precompensation_transfer)
    return propagate_scaled_fresnel(
        envelope=precompensated,
        calculation=fresnel_calculation,
        computational_counts=computational_counts,
        padding=(0, 0),
        output_sample_counts=output_sample_counts,
        axial_distance=axial_distance,
        real_dtype=real_dtype,
        complex_dtype=complex_dtype,
        device=device,
    )


def _apply_precompensation(
    envelope: torch.Tensor,
    transfer: torch.Tensor,
) -> torch.Tensor:
    spectrum = torch.fft.fftn(envelope, dim=(-2, -1))
    precompensated_spectrum = spectrum * transfer.unsqueeze(-3)
    return torch.fft.ifftn(precompensated_spectrum, dim=(-2, -1))


def _scalable_angular_spectrum_residual_cycles(
    *,
    facts: _RadiativeSpectrumFacts,
    axial_distance_signed: torch.Tensor,
) -> torch.Tensor:
    transverse_squared = (
        facts.transverse_wavevector_y.square()
        + facts.transverse_wavevector_x.square()
    )
    normalized_transverse_wavevector_squared = (
        transverse_squared / facts.wave_number.square()
    )
    direction_z_squared = 1.0 - normalized_transverse_wavevector_squared
    direction_z = torch.sqrt(torch.clamp(direction_z_squared, min=0.0))
    one_plus_direction_z = 1.0 + direction_z
    axial_carrier_cycles = (
        facts.wave_number
        * axial_distance_signed.to(
            dtype=facts.wave_number.dtype,
            device=facts.wave_number.device,
        ).reshape(1, 1, 1)
        / (2.0 * math.pi)
    )
    return -axial_carrier_cycles * normalized_transverse_wavevector_squared.square() / (
        2.0 * one_plus_direction_z.square()
    )


def _scalable_angular_spectrum_residual_support(
    *,
    facts: _RadiativeSpectrumFacts,
    computational_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    axial_distance_signed: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    real_dtype: torch.dtype,
    device: torch.device,
) -> torch.Tensor:
    two_pi = 2.0 * math.pi
    wavelengths_real = wavelengths.to(dtype=real_dtype, device=device).reshape(-1, 1, 1)
    refractive_indices_real = (
        refractive_indices.to(dtype=real_dtype, device=device).reshape(-1, 1, 1)
    )
    frequency_y = facts.transverse_wavevector_y / two_pi
    frequency_x = facts.transverse_wavevector_x / two_pi
    transverse_spatial_frequency_squared = (
        frequency_y.square() + frequency_x.square()
    )
    radiative_support_margin = (
        refractive_indices_real.square()
        - wavelengths_real.square() * transverse_spatial_frequency_squared
    )
    spacing_y = signed_spacing[0].to(dtype=real_dtype, device=device).abs()
    spacing_x = signed_spacing[1].to(dtype=real_dtype, device=device).abs()
    half_extent_y = 0.5 * computational_counts[0] * spacing_y
    half_extent_x = 0.5 * computational_counts[1] * spacing_x
    distance_magnitude = (
        axial_distance_signed.to(dtype=real_dtype, device=device)
        .abs()
        .reshape(-1, 1, 1)
    )
    admit_y = _admit_residual_axis(
        frequency_axis=frequency_y,
        transverse_spatial_frequency_squared=transverse_spatial_frequency_squared,
        radiative_support_margin=radiative_support_margin,
        refractive_indices=refractive_indices_real,
        wavelengths=wavelengths_real,
        distance_magnitude=distance_magnitude,
        half_extent=half_extent_y,
    )
    admit_x = _admit_residual_axis(
        frequency_axis=frequency_x,
        transverse_spatial_frequency_squared=transverse_spatial_frequency_squared,
        radiative_support_margin=radiative_support_margin,
        refractive_indices=refractive_indices_real,
        wavelengths=wavelengths_real,
        distance_magnitude=distance_magnitude,
        half_extent=half_extent_x,
    )
    return (facts.radiative_support & admit_y & admit_x).detach()


def _admit_residual_axis(
    *,
    frequency_axis: torch.Tensor,
    transverse_spatial_frequency_squared: torch.Tensor,
    radiative_support_margin: torch.Tensor,
    refractive_indices: torch.Tensor,
    wavelengths: torch.Tensor,
    distance_magnitude: torch.Tensor,
    half_extent: torch.Tensor,
) -> torch.Tensor:
    lambda_cubed = wavelengths * wavelengths * wavelengths
    residual_slope_magnitude = (
        (distance_magnitude * frequency_axis).abs()
        * lambda_cubed
        * transverse_spatial_frequency_squared
    )
    support_threshold = half_extent * refractive_indices * radiative_support_margin
    ones = torch.ones_like(radiative_support_margin)
    fast_sign = squared_reference_minus_squared_factor_extra_factor_sign(
        reference=residual_slope_magnitude,
        squared_factor=support_threshold,
        extra_factor=ones,
    )
    fast_admit = fast_sign < 0
    residual_slope_excess = residual_slope_magnitude - support_threshold
    squared_support_scale = (
        half_extent * refractive_indices * refractive_indices
    )
    squared_sign = squared_reference_minus_squared_factor_extra_factor_sign(
        reference=residual_slope_excess,
        squared_factor=squared_support_scale,
        extra_factor=radiative_support_margin,
    )
    squared_admit = squared_sign < 0
    return fast_admit | squared_admit

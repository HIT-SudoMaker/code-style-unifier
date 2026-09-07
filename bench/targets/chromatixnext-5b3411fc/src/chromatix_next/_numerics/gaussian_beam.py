from __future__ import annotations

import math

import torch

from chromatix_next._numerics.complex_phase import _unit_phasor_from_cycles
from chromatix_next._numerics.spatial_sampling import spatial_sample_positions
from chromatix_next._numerics.wave_number import medium_wave_numbers


def gaussian_beam_power_amplitude(
    *,
    total_power: torch.Tensor,
    spectral_weights: torch.Tensor,
    unit_envelope: torch.Tensor,
    cell_area: torch.Tensor,
) -> torch.Tensor:
    """
    由总功率与单位包络模方导出标量振幅

    """

    modulus_squared = (
        unit_envelope.real.square() + unit_envelope.imag.square()
    )
    per_spectrum = modulus_squared.sum(dim=-3)
    spatial_integral = per_spectrum.sum(dim=(-2, -1))
    weighted_power = (spectral_weights * spatial_integral).sum()
    represented_power = weighted_power * cell_area.to(
        device=total_power.device,
        dtype=total_power.dtype,
    )
    return torch.sqrt(total_power / represented_power)
def gaussian_beam_unit_envelope(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    waist_radius: torch.Tensor,
    waist_location: torch.Tensor,
    polarization_state: torch.Tensor,
) -> torch.Tensor:
    """
    合成形状为 (光谱, 偏振, 高, 宽) 的 paraxial 高斯光束单位包络

    """

    position_y, position_x = spatial_sample_positions(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        reference=wavelengths,
    )
    wave_number = medium_wave_numbers(
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
    )
    waist_squared = waist_radius * waist_radius
    rayleigh_range = 0.5 * wave_number * waist_squared
    rayleigh_squared = rayleigh_range * rayleigh_range
    axial_squared = waist_location * waist_location
    beam_radius = waist_radius * torch.sqrt(
        1.0 + axial_squared / rayleigh_squared
    )
    curvature_factor = waist_location / (
        2.0 * (axial_squared + rayleigh_squared)
    )
    # Gouy 角由 arctan 给出，按周期表达送入 phasor：负 Gouy 与角谱正向传播复域一致
    gouy_cycles = torch.atan(waist_location / rayleigh_range) / (2.0 * math.pi)
    radius_squared = (
        position_y.reshape(1, -1, 1).square()
        + position_x.reshape(1, 1, -1).square()
    )
    amplitude_factor = (waist_radius / beam_radius).reshape(-1, 1, 1)
    beam_radius_squared = (beam_radius * beam_radius).reshape(-1, 1, 1)
    transverse_envelope = torch.exp(-radius_squared / beam_radius_squared)
    curvature_cycles = (
        (wave_number * curvature_factor).reshape(-1, 1, 1)
        * radius_squared
        / (2.0 * math.pi)
    )
    curvature_phasor = _unit_phasor_from_cycles(curvature_cycles)
    # 负 Gouy 相位 exp(-i arctan(z/zR))：与角谱正向传播复域一致
    gouy_phasor = _unit_phasor_from_cycles((-gouy_cycles).reshape(-1, 1, 1))
    scalar_envelope = (
        amplitude_factor * transverse_envelope * curvature_phasor * gouy_phasor
    )
    return scalar_envelope.unsqueeze(1) * polarization_state.reshape(
        1,
        -1,
        1,
        1,
    )

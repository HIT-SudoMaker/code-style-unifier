from __future__ import annotations

import math

import torch

from chromatix_next._numerics.complex_phase import _unit_phasor_from_cycles
from chromatix_next._numerics.spatial_sampling import (
    quadratic_phase_factor,
    spatial_sample_positions,
)
from chromatix_next._numerics.wave_propagation.spatial_frequency import to_frequency


def fresnel_output_spacing(
    *,
    sample_counts: tuple[int, int],
    input_spacing: tuple[torch.Tensor, torch.Tensor],
    wavelength_distance: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    解析单次 Fresnel 变换的纵横输出采样间距

    """

    return (
        wavelength_distance.abs()
        / (sample_counts[0] * input_spacing[0].to(wavelength_distance)),
        wavelength_distance.abs()
        / (sample_counts[1] * input_spacing[1].to(wavelength_distance)),
    )

def fresnel_transform_envelope(
    *,
    envelope: torch.Tensor,
    sample_counts: tuple[int, int],
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    input_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    output_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelength_distance: torch.Tensor,
) -> torch.Tensor:
    """
    以单次正交傅里叶变换计算单色 Fresnel 包络

    """
    input_y, input_x = spatial_sample_positions(
        sample_counts=sample_counts,
        signed_spacing=input_signed_spacing,
        first_sample_position=input_first_sample_position,
        reference=envelope.real,
    )
    output_y, output_x = spatial_sample_positions(
        sample_counts=sample_counts,
        signed_spacing=output_signed_spacing,
        first_sample_position=output_first_sample_position,
        reference=envelope.real,
    )
    phase_curvature = math.pi / wavelength_distance
    input_chirp = quadratic_phase_factor(
        position_y=input_y,
        position_x=input_x,
        phase_curvature=phase_curvature,
    )
    chirped = envelope * input_chirp
    is_backward = wavelength_distance < 0.0
    directed = torch.where(is_backward, chirped.conj(), chirped)
    transformed = to_frequency(
        directed,
        is_centered=True,
        normalization="ortho",
    )
    transformed = torch.where(is_backward, transformed.conj(), transformed)
    frequency_y = output_y / wavelength_distance
    frequency_x = output_x / wavelength_distance
    origin_cycles = -(
        frequency_y[:, None] * input_y[0] + frequency_x[None, :] * input_x[0]
    )
    output_chirp = quadratic_phase_factor(
        position_y=output_y,
        position_x=output_x,
        phase_curvature=phase_curvature,
    )
    output_chirp = output_chirp * _unit_phasor_from_cycles(origin_cycles)
    input_area = input_signed_spacing[0].abs() * input_signed_spacing[1].abs()
    output_area = output_signed_spacing[0].abs() * output_signed_spacing[1].abs()
    amplitude_scale = torch.sqrt(input_area / output_area)
    phase_scale = -1j * torch.sign(wavelength_distance) * amplitude_scale
    return transformed * output_chirp * phase_scale

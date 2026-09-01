from __future__ import annotations

import math

import torch

from chromatix_next._numerics.spatial_sampling import (
    quadratic_phase_factor,
    spatial_sample_positions,
)

from .complex_phase import _unit_phasor_from_cycles
from .wave_number import medium_wave_numbers


def optical_path_phase_factor(
    *,
    wavelengths: torch.Tensor,
    optical_path_variation: torch.Tensor,
) -> torch.Tensor:
    """
    计算逐谱空间光程相位 ``exp(i 2π ΔL / λ)``

    """

    vacuum_wave_number = medium_wave_numbers(
        wavelengths=wavelengths,
        refractive_indices=1.0,
    ).reshape(-1, 1, 1)
    # 真空波数 k = 2π/λ 以 rad/m 表达；按周期送入 phasor：k·ΔL/(2π) = ΔL/λ
    cycles = (
        vacuum_wave_number
        * optical_path_variation.unsqueeze(0)
        / (2.0 * math.pi)
    )
    return _unit_phasor_from_cycles(cycles)

def ideal_thin_lens_phase_factor(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    focal_length: torch.Tensor,
    lens_center: tuple[torch.Tensor, torch.Tensor],
) -> torch.Tensor:
    """
    计算前向会聚薄透镜的 Goodman 负二次相位

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
    return quadratic_phase_factor(
        position_y=position_y,
        position_x=position_x,
        phase_curvature=-wave_number / (2.0 * focal_length),
        center_y=lens_center[0],
        center_x=lens_center[1],
    )

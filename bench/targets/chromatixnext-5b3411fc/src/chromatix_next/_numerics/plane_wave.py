from __future__ import annotations

import math

import torch

from chromatix_next._numerics._certified_predicates import (
    scaled_squared_norm_difference_sign,
)
from chromatix_next._numerics.complex_phase import _unit_phasor_from_cycles
from chromatix_next._numerics.spatial_sampling import spatial_sample_positions
from chromatix_next._numerics.wave_number import medium_wave_numbers
from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

_TAU = 2.0 * math.pi

_SAMPLING_INSUFFICIENT_EXPLANATION = (
    "平面波载波无法在该横向网格上被严格采样：每个横向轴上每样本的相位增量须严格"
    "小于半周期（按每个物理 (n_i, λ_i) 对与每个横向轴独立判定，不取 max(n)/min(λ)），"
    "且共享横向波矢须落在每个光谱分量的辐射支持内（κ_y²+κ_x² < (2π·n_i/λ_i)²，"
    "掠射等同条件不支持）。请减小方向余弦或横向波矢、缩短采样间距，"
    "或改用更高折射率、更短波长的介质。"
)



def power_normalized_amplitude(
    *,
    total_power: torch.Tensor,
    spectral_weights: torch.Tensor,
    sample_counts: tuple[int, int],
    cell_area: torch.Tensor,
) -> torch.Tensor:
    """
    计算总功率归一化振幅

    """

    sample_count = sample_counts[0] * sample_counts[1]
    represented_area = sample_count * cell_area.to(
        device=total_power.device,
        dtype=total_power.dtype,
    )
    represented_power = spectral_weights.sum() * represented_area
    return torch.sqrt(total_power / represented_power)


def _reject_if_any_axis_fails_strict_nyquist(
    half_cycle: torch.Tensor,
    delta_cycles_y: torch.Tensor,
    delta_cycles_x: torch.Tensor,
) -> None:
    for delta_cycles in (delta_cycles_y, delta_cycles_x):
        sign = scaled_squared_norm_difference_sign(
            reference=half_cycle,
            vector=delta_cycles.reshape(-1, 1),
        )
        if is_value_readable(sign) and bool((sign < 1).any()):
            raise _errors.OpticalValueError(
                "plane_wave_sampling_insufficient",
                _SAMPLING_INSUFFICIENT_EXPLANATION,
            )


def _assert_plane_wave_sampling(
    *,
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    propagation_direction: tuple[torch.Tensor, torch.Tensor] | None,
    transverse_wavevector: tuple[torch.Tensor, torch.Tensor] | None,
) -> None:
    spacing_y, spacing_x = signed_spacing
    half_cycle = torch.tensor(
        0.5,
        dtype=wavelengths.dtype,
        device=wavelengths.device,
    )
    if propagation_direction is not None:
        direction_y, direction_x = propagation_direction
        delta_cycles_y = (
            refractive_indices * direction_y * spacing_y / wavelengths
        )
        delta_cycles_x = (
            refractive_indices * direction_x * spacing_x / wavelengths
        )
        _reject_if_any_axis_fails_strict_nyquist(
            half_cycle,
            delta_cycles_y,
            delta_cycles_x,
        )
        return
    assert transverse_wavevector is not None
    transverse_wavevector_y, transverse_wavevector_x = transverse_wavevector
    transverse_cycles_per_meter_y = transverse_wavevector_y / _TAU
    transverse_cycles_per_meter_x = transverse_wavevector_x / _TAU
    _reject_if_any_axis_fails_strict_nyquist(
        half_cycle,
        transverse_cycles_per_meter_y * spacing_y,
        transverse_cycles_per_meter_x * spacing_x,
    )
    medium_cycles_per_meter = refractive_indices / wavelengths
    transverse_cycles = torch.stack(
        (
            transverse_cycles_per_meter_y.expand_as(medium_cycles_per_meter),
            transverse_cycles_per_meter_x.expand_as(medium_cycles_per_meter),
        ),
        dim=-1,
    )
    radiative_sign = scaled_squared_norm_difference_sign(
        reference=medium_cycles_per_meter,
        vector=transverse_cycles,
    )
    if is_value_readable(radiative_sign) and bool((radiative_sign < 1).any()):
        raise _errors.OpticalValueError(
            "plane_wave_sampling_insufficient",
            _SAMPLING_INSUFFICIENT_EXPLANATION,
        )


def plane_wave_envelope(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    polarization_state: torch.Tensor,
    propagation_direction: tuple[torch.Tensor, torch.Tensor] | None,
    transverse_wavevector: tuple[torch.Tensor, torch.Tensor] | None,
) -> torch.Tensor:
    """
    合成形状为 (光谱, 偏振, 高, 宽) 的定向平面波单位包络

    """

    _assert_plane_wave_sampling(
        signed_spacing=signed_spacing,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        propagation_direction=propagation_direction,
        transverse_wavevector=transverse_wavevector,
    )
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
    if propagation_direction is not None:
        transverse_wavevector_y = (
            wave_number * propagation_direction[0]
        )
        transverse_wavevector_x = (
            wave_number * propagation_direction[1]
        )
    else:
        assert transverse_wavevector is not None
        transverse_wavevector_y = torch.ones_like(wave_number) * (
            transverse_wavevector[0]
        )
        transverse_wavevector_x = torch.ones_like(wave_number) * (
            transverse_wavevector[1]
        )
    cycles = (
        transverse_wavevector_y.reshape(-1, 1, 1)
        * position_y.reshape(1, -1, 1)
        + transverse_wavevector_x.reshape(-1, 1, 1)
        * position_x.reshape(1, 1, -1)
    ) / (2.0 * math.pi)
    spatial_phasor = _unit_phasor_from_cycles(cycles)
    return spatial_phasor.unsqueeze(1) * polarization_state.reshape(
        1,
        -1,
        1,
        1,
    )

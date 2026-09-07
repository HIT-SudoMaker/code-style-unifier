from __future__ import annotations

from typing import NamedTuple

import torch

from chromatix_next._numerics._certified_predicates import (
    squared_reference_minus_squared_factor_extra_factor_sign,
)
from chromatix_next._numerics.complex_phase import _unit_phasor_from_cycles
from chromatix_next._numerics.spatial_sampling import spatial_sample_positions


def point_source_power_amplitude(
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

class PointSourceSamplingFacts(NamedTuple):
    """
    逐相邻对逐光谱球面波半周期采样判定与诊断

    严格判据（``is_sufficient`` 承载）：对每对相邻 y 样本（同 x 列）与每对相邻 x
    样本（同 y 行），对每条光谱，per-sample 相位周期增量 ``|Δcycles_i|`` 须严格
    小于 0.5；任一对/任一光谱达到或超过半周期即整体采样不足。判据不经
    ``sqrt(v)-sqrt(u)`` 舍入：以两阶段多项式符号判定实现（见
    ``point_source_sampling_fence``）。``worst_y_cycles_per_sample`` /
    ``worst_x_cycles_per_sample`` 是逐对逐光谱 ``|Δcycles|`` 最大值的舍入诊断，仅供
    报错信息使用；严格判定只读 ``is_sufficient``。

    """

    is_sufficient: torch.Tensor
    worst_y_cycles_per_sample: torch.Tensor
    worst_x_cycles_per_sample: torch.Tensor
    half_cycle_threshold: torch.Tensor


def _adjacent_pair_half_cycle_sufficient(
    *,
    smaller_radius_squared: torch.Tensor,
    radius_squared_difference: torch.Tensor,
    refractive_index_per_spectrum: torch.Tensor,
    wavelengths_per_spectrum: torch.Tensor,
) -> torch.Tensor:

    twice_refractive_index_per_spectrum = (
        2.0 * refractive_index_per_spectrum
    )
    lambdas = wavelengths_per_spectrum
    first_stage_margin_sign = squared_reference_minus_squared_factor_extra_factor_sign(
        reference=lambdas,
        squared_factor=twice_refractive_index_per_spectrum,
        extra_factor=radius_squared_difference,
    )
    is_first_stage_sufficient = first_stage_margin_sign > 0

    is_smaller_radius_squared_zero = smaller_radius_squared == 0.0
    second_stage_residual = (
        twice_refractive_index_per_spectrum
        * twice_refractive_index_per_spectrum
        * radius_squared_difference
        - lambdas * lambdas
    )
    second_stage_scale = (
        2.0 * twice_refractive_index_per_spectrum * lambdas
    )
    sign_quad = squared_reference_minus_squared_factor_extra_factor_sign(
        reference=second_stage_residual,
        squared_factor=second_stage_scale,
        extra_factor=smaller_radius_squared,
    )
    accept_via_quad = (~is_smaller_radius_squared_zero) & (sign_quad < 0)

    return is_first_stage_sufficient | accept_via_quad


def _worst_abs_cycles_per_pair(
    *,
    radius_squared_a: torch.Tensor,
    radius_squared_b: torch.Tensor,
    refractive_indices_per_spectrum: torch.Tensor,
    wavelengths_per_spectrum: torch.Tensor,
) -> torch.Tensor:

    real_dtype = wavelengths_per_spectrum.dtype
    device = wavelengths_per_spectrum.device
    if radius_squared_a.numel() == 0:
        return torch.zeros((), dtype=real_dtype, device=device)
    radius_a = torch.sqrt(radius_squared_a)
    radius_b = torch.sqrt(radius_squared_b)
    abs_delta_radius = (radius_b - radius_a).abs()
    abs_delta_cycles = (
        refractive_indices_per_spectrum
        * abs_delta_radius.unsqueeze(0)
        / wavelengths_per_spectrum
    )
    return abs_delta_cycles.max()


def point_source_sampling_fence(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    source_position_yxz: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
) -> PointSourceSamplingFacts:
    """
    返回逐相邻对逐光谱的严格半周期采样判定与诊断

    在 grid 的每对相邻 y 样本与每对相邻 x 样本上，逐光谱以两阶段多项式符号判定
    ``|Δcycles_i| < 0.5`` 严格。判据不经 ``sqrt(v)-sqrt(u)`` 舍入（``sqrt`` 仅出现
    在诊断 ``worst_*_cycles_per_sample`` 的舍入路径，承载判定的 ``is_sufficient``
    只走多项式符号）。

    """

    position_y, position_x = spatial_sample_positions(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        reference=wavelengths,
    )
    source_y, source_x, source_z = source_position_yxz
    delta_y = position_y.reshape(-1, 1) - source_y
    delta_x = position_x.reshape(1, -1) - source_x
    radius_squared = (
        delta_y * delta_y + delta_x * delta_x + source_z * source_z
    )

    radius_squared_y_a = radius_squared[:-1, :]
    radius_squared_y_b = radius_squared[1:, :]
    smaller_radius_squared_y_pairs = torch.minimum(
        radius_squared_y_a,
        radius_squared_y_b,
    )
    radius_squared_difference_y_pairs = (
        torch.maximum(
            radius_squared_y_a,
            radius_squared_y_b,
        )
        - smaller_radius_squared_y_pairs
    )

    radius_squared_x_a = radius_squared[:, :-1]
    radius_squared_x_b = radius_squared[:, 1:]
    smaller_radius_squared_x_pairs = torch.minimum(
        radius_squared_x_a,
        radius_squared_x_b,
    )
    radius_squared_difference_x_pairs = (
        torch.maximum(
            radius_squared_x_a,
            radius_squared_x_b,
        )
        - smaller_radius_squared_x_pairs
    )

    refractive_index_per_spectrum = refractive_indices.reshape(-1, 1, 1)
    wavelengths_per_spectrum = wavelengths.reshape(-1, 1, 1)

    y_pair_sufficient = _adjacent_pair_half_cycle_sufficient(
        smaller_radius_squared=smaller_radius_squared_y_pairs.unsqueeze(0),
        radius_squared_difference=radius_squared_difference_y_pairs.unsqueeze(0),
        refractive_index_per_spectrum=refractive_index_per_spectrum,
        wavelengths_per_spectrum=wavelengths_per_spectrum,
    )
    x_pair_sufficient = _adjacent_pair_half_cycle_sufficient(
        smaller_radius_squared=smaller_radius_squared_x_pairs.unsqueeze(0),
        radius_squared_difference=radius_squared_difference_x_pairs.unsqueeze(0),
        refractive_index_per_spectrum=refractive_index_per_spectrum,
        wavelengths_per_spectrum=wavelengths_per_spectrum,
    )

    is_sufficient = (
        y_pair_sufficient.all() & x_pair_sufficient.all()
    ).detach()

    worst_y_cycles = _worst_abs_cycles_per_pair(
        radius_squared_a=radius_squared_y_a,
        radius_squared_b=radius_squared_y_b,
        refractive_indices_per_spectrum=refractive_index_per_spectrum,
        wavelengths_per_spectrum=wavelengths_per_spectrum,
    )
    worst_x_cycles = _worst_abs_cycles_per_pair(
        radius_squared_a=radius_squared_x_a,
        radius_squared_b=radius_squared_x_b,
        refractive_indices_per_spectrum=refractive_index_per_spectrum,
        wavelengths_per_spectrum=wavelengths_per_spectrum,
    )

    half_cycle_threshold = torch.tensor(
        0.5,
        dtype=wavelengths.dtype,
        device=wavelengths.device,
    )
    return PointSourceSamplingFacts(
        is_sufficient=is_sufficient,
        worst_y_cycles_per_sample=worst_y_cycles,
        worst_x_cycles_per_sample=worst_x_cycles,
        half_cycle_threshold=half_cycle_threshold,
    )


def point_source_unit_envelope(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    source_position_yxz: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    is_inverse_distance: bool,
    polarization_state: torch.Tensor,
) -> torch.Tensor:
    """
    合成形状为 (光谱, 偏振, 高, 宽) 的球面波单位包络

    """

    position_y, position_x = spatial_sample_positions(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        reference=wavelengths,
    )
    source_y, source_x, source_z = source_position_yxz
    delta_y = position_y.reshape(1, -1, 1) - source_y
    delta_x = position_x.reshape(1, 1, -1) - source_x
    axial_distance_squared = source_z * source_z
    radius_squared = (
        delta_y * delta_y
        + delta_x * delta_x
        + axial_distance_squared
    )
    radius = torch.sqrt(radius_squared)
    cycles = (
        refractive_indices.reshape(-1, 1, 1)
        * radius
        / wavelengths.reshape(-1, 1, 1)
    )
    if is_inverse_distance:
        amplitude_factor = torch.reciprocal(radius)
    else:
        amplitude_factor = torch.ones_like(radius)
    scalar_envelope = amplitude_factor * _unit_phasor_from_cycles(cycles)
    return scalar_envelope.unsqueeze(1) * polarization_state.reshape(
        1,
        -1,
        1,
        1,
    )

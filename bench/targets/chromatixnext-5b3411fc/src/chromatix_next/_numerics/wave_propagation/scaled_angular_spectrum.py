from __future__ import annotations

from typing import NamedTuple

import torch

from chromatix_next._numerics.complex_phase import _unit_phasor_from_cycles
from chromatix_next._numerics.wave_propagation.chirp_z_transform import (
    chirp_z_transform,
)
from chromatix_next._numerics.wave_propagation.radiative_spectrum import (
    _embed_computational_window,
    _radiative_spectrum_facts,
)


class ScaledAngularSpectrumCalculation(NamedTuple):
    """
    标量辐射角谱残差传递张量及其窄带事实

    """

    transfer: torch.Tensor
    has_narrow_alias_band: torch.Tensor


def scaled_angular_spectrum_calculation(
    *,
    computational_counts: tuple[int, int],
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    axial_distance: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    device: torch.device,
) -> ScaledAngularSpectrumCalculation:
    """
    在源计算网格上构造标量辐射角谱残差传递张量

    """

    zero_displacement = (
        torch.zeros((), dtype=real_dtype, device=device),
        torch.zeros((), dtype=real_dtype, device=device),
    )
    facts = _radiative_spectrum_facts(
        computational_counts=computational_counts,
        signed_spacing=input_signed_spacing,
        displacement=zero_displacement,
        axial_distance=axial_distance,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        real_dtype=real_dtype,
        device=device,
    )
    support = (facts.radiative_support & facts.alias_support).detach()
    transfer = torch.where(
        support,
        _unit_phasor_from_cycles(facts.axial_cycles),
        torch.zeros_like(facts.axial_cycles),
    ).to(dtype=complex_dtype)
    return ScaledAngularSpectrumCalculation(
        transfer=transfer,
        has_narrow_alias_band=facts.has_narrow_alias_band,
    )


def scaled_angular_spectrum_destination_sampling_too_coarse(
    *,
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    real_dtype: torch.dtype,
    device: torch.device,
) -> torch.Tensor:
    """
    判断目标采样是否足以表示精确角谱传播后的连续场（CZT 目标采样事实）

    """

    spacing_in_y = input_signed_spacing[0].to(dtype=real_dtype, device=device)
    spacing_in_x = input_signed_spacing[1].to(dtype=real_dtype, device=device)
    spacing_out_y = output_signed_spacing[0].to(dtype=real_dtype, device=device)
    spacing_out_x = output_signed_spacing[1].to(dtype=real_dtype, device=device)
    wavelengths_real = wavelengths.to(dtype=real_dtype, device=device)
    refractive_real = refractive_indices.to(
        dtype=real_dtype,
        device=device,
    )
    radiative_spacing = (
        wavelengths_real / (2.0 * refractive_real)
    ).reshape(-1, 1)
    spacing_limit_y = torch.maximum(
        spacing_in_y.abs().reshape(1, -1),
        radiative_spacing,
    )
    spacing_limit_x = torch.maximum(
        spacing_in_x.abs().reshape(1, -1),
        radiative_spacing,
    )
    source_dtype = input_signed_spacing[0].dtype
    source_eps = torch.finfo(source_dtype).eps
    relative_tolerance = 8.0 * source_eps
    is_too_coarse = torch.any(
        (
            (
                spacing_out_y.abs().reshape(1, -1)
                > spacing_limit_y * (1.0 + relative_tolerance)
            )
            | (
                spacing_out_x.abs().reshape(1, -1)
                > spacing_limit_x * (1.0 + relative_tolerance)
            )
        ).detach(),
    )
    return is_too_coarse


def propagate_scaled_angular_spectrum(
    *,
    envelope: torch.Tensor,
    transfer: torch.Tensor,
    computational_counts: tuple[int, int],
    padding: tuple[int, int],
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    input_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    output_sample_counts: tuple[int, int],
    output_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_first_sample_position: tuple[torch.Tensor, torch.Tensor],
) -> torch.Tensor:
    """
    以辐射角谱残差传递与可分离 chirp_z 评估目标网格包络

    """

    embedded = _embed_computational_window(
        envelope=envelope,
        computational_counts=computational_counts,
        padding=padding,
    )
    computational_first_height = (
        input_first_sample_position[0]
        - padding[0] * input_signed_spacing[0]
    )
    computational_first_width = (
        input_first_sample_position[1]
        - padding[1] * input_signed_spacing[1]
    )
    spectrum = torch.fft.fftn(embedded, dim=(-2, -1))
    transferred = spectrum * transfer.unsqueeze(-3)
    transferred_centered = torch.fft.fftshift(
        transferred,
        dim=(-2, -1),
    )
    evaluated_x = _evaluate_chirp_z_axis(
        transferred_centered,
        computational_count=computational_counts[1],
        input_signed_spacing=input_signed_spacing[1],
        input_first_sample_position=computational_first_width,
        output_count=output_sample_counts[1],
        output_signed_spacing=output_signed_spacing[1],
        output_first_sample_position=output_first_sample_position[1],
    )
    evaluated_xy = _evaluate_chirp_z_axis(
        evaluated_x.movedim(-2, -1),
        computational_count=computational_counts[0],
        input_signed_spacing=input_signed_spacing[0],
        input_first_sample_position=computational_first_height,
        output_count=output_sample_counts[0],
        output_signed_spacing=output_signed_spacing[0],
        output_first_sample_position=output_first_sample_position[0],
    ).movedim(-1, -2)
    evaluated_xy = _apply_axis_frequency_offset(
        evaluated_xy,
        axis=-1,
        computational_count=computational_counts[1],
        input_signed_spacing=input_signed_spacing[1],
        input_first_sample_position=computational_first_width,
        output_count=output_sample_counts[1],
        output_signed_spacing=output_signed_spacing[1],
        output_first_sample_position=output_first_sample_position[1],
    )
    evaluated_xy = _apply_axis_frequency_offset(
        evaluated_xy,
        axis=-2,
        computational_count=computational_counts[0],
        input_signed_spacing=input_signed_spacing[0],
        input_first_sample_position=computational_first_height,
        output_count=output_sample_counts[0],
        output_signed_spacing=output_signed_spacing[0],
        output_first_sample_position=output_first_sample_position[0],
    )
    normalization = transferred.new_tensor(
        1.0 / (computational_counts[0] * computational_counts[1]),
    )
    return evaluated_xy * normalization


def _evaluate_chirp_z_axis(
    values: torch.Tensor,
    *,
    computational_count: int,
    input_signed_spacing: torch.Tensor,
    input_first_sample_position: torch.Tensor,
    output_count: int,
    output_signed_spacing: torch.Tensor,
    output_first_sample_position: torch.Tensor,
) -> torch.Tensor:
    reference = values.real
    spacing_in = input_signed_spacing.to(
        dtype=reference.dtype,
        device=reference.device,
    )
    origin_in = input_first_sample_position.to(
        dtype=reference.dtype,
        device=reference.device,
    )
    spacing_out = output_signed_spacing.to(
        dtype=reference.dtype,
        device=reference.device,
    )
    origin_out = output_first_sample_position.to(
        dtype=reference.dtype,
        device=reference.device,
    )
    denominator = computational_count * spacing_in
    starting_cycles = (origin_out - origin_in) / denominator
    cycles_step = spacing_out / denominator
    return chirp_z_transform(
        values,
        output_count=output_count,
        starting_cycles=starting_cycles,
        cycles_step=cycles_step,
    )


def _apply_axis_frequency_offset(
    values: torch.Tensor,
    *,
    axis: int,
    computational_count: int,
    input_signed_spacing: torch.Tensor,
    input_first_sample_position: torch.Tensor,
    output_count: int,
    output_signed_spacing: torch.Tensor,
    output_first_sample_position: torch.Tensor,
) -> torch.Tensor:
    reference = values.real
    spacing_in = input_signed_spacing.to(
        dtype=reference.dtype,
        device=reference.device,
    )
    origin_in = input_first_sample_position.to(
        dtype=reference.dtype,
        device=reference.device,
    )
    spacing_out = output_signed_spacing.to(
        dtype=reference.dtype,
        device=reference.device,
    )
    origin_out = output_first_sample_position.to(
        dtype=reference.dtype,
        device=reference.device,
    )
    denominator = computational_count * spacing_in
    # 频移补偿相位以周期表达：弧度原式 -2π·(N//2)·(...) / (N·Δx_in) 除 2π 即周期
    correction_cycles = (
        -(computational_count // 2)
        * (
            origin_out
            - origin_in
            + torch.arange(
                output_count,
                dtype=reference.dtype,
                device=reference.device,
            )
            * spacing_out
        )
        / denominator
    )
    shape = [1] * values.dim()
    shape[axis] = output_count
    correction = _unit_phasor_from_cycles(correction_cycles).reshape(shape)
    return values * correction.to(dtype=values.dtype)

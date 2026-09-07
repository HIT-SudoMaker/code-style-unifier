from __future__ import annotations

from typing import NamedTuple

import torch

from chromatix_next._numerics.complex_phase import _unit_phasor_from_cycles
from chromatix_next._numerics.spatial_sampling import spatial_sample_positions
from chromatix_next._numerics.wave_propagation.chirp_z_transform import (
    chirp_z_transform,
)
from chromatix_next._numerics.wave_propagation.radiative_spectrum import (
    _embed_computational_window,
)


class ScaledFresnelCalculation(NamedTuple):
    """
    带尺度 Fresnel 的输入/输出二次相位、归一化与 chirp_z 参数

    所有相位量（输入/输出啁啾、输出相位偏移、chirp_z 起始与步进）均以周期表达；
    chirp_z 入参命名 ``starting_cycles``/``cycles_step``。前因子 ``beta_cycles``
    对应原 ``β / (2π) = n / (λ |d|)``，使所有二次项直接落在周期单位下。

    """

    input_chirp: torch.Tensor
    output_chirp: torch.Tensor
    normalization: torch.Tensor
    output_phase_offset_y: torch.Tensor
    output_phase_offset_x: torch.Tensor
    starting_cycles_x: torch.Tensor
    cycles_step_x: torch.Tensor
    starting_cycles_y: torch.Tensor
    cycles_step_y: torch.Tensor


class ScaledFresnelSamplingFacts(NamedTuple):
    """
    近轴 Collins/Fresnel 方程要求的输入到输出采样事实

    三条事实各自逐轴、逐光谱判定；任一轴任一光谱窄带即整体窄带。每条事实对应
    一个独立必要条件——任一窄带都使 Collins 离散和不再忠实表示连续积分，必须
    在物理动作处给出独立稳定身份后失败，绝不静默退化或替换方法。magnification
    （目标相对源几何的隐含放大率）与双向 bilinear 耦合共享变换耦合事实：放大率
    由 Δx_out / Δx_in 之比携带，进入正向与反向耦合不等式，无独立不等式。
    shift（源与目标首样本位置的相对位移）对周期外部天然合法，对孤立外部由
    ``isolated_destination_within_tripled_window`` 单独保有。

    """

    input_chirp_too_narrow: torch.Tensor
    output_chirp_too_narrow: torch.Tensor
    transform_coupling_too_narrow: torch.Tensor


def scaled_fresnel_sampling_facts(
    *,
    input_counts: tuple[int, int],
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_counts: tuple[int, int],
    output_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    axial_distance: torch.Tensor,
    real_dtype: torch.dtype,
    device: torch.device,
) -> ScaledFresnelSamplingFacts:
    """
    返回近轴 Collins 方程要求的输入啁啾、输出啁啾与变换耦合奈奎斯特事实

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
    distance_abs = axial_distance.abs().to(dtype=real_dtype, device=device)
    input_chirp_limit_y = (
        wavelengths_real * distance_abs
        / (refractive_real * input_counts[0] * spacing_in_y.square())
    )
    input_chirp_limit_x = (
        wavelengths_real * distance_abs
        / (refractive_real * input_counts[1] * spacing_in_x.square())
    )
    # 输出二次相位在目标窗口角点 R_out 处同理：λ|d| / (n N_out Δx_out²) ≥ 1
    output_chirp_limit_y = (
        wavelengths_real * distance_abs
        / (refractive_real * output_counts[0] * spacing_out_y.square())
    )
    output_chirp_limit_x = (
        wavelengths_real * distance_abs
        / (refractive_real * output_counts[1] * spacing_out_x.square())
    )
    coupling_forward_y = (
        wavelengths_real
        * distance_abs
        / (
            refractive_real
            * input_counts[0]
            * spacing_in_y.abs()
            * spacing_out_y.abs()
        )
    )
    coupling_forward_x = (
        wavelengths_real
        * distance_abs
        / (
            refractive_real
            * input_counts[1]
            * spacing_in_x.abs()
            * spacing_out_x.abs()
        )
    )
    coupling_reverse_y = (
        wavelengths_real
        * distance_abs
        / (
            refractive_real
            * output_counts[0]
            * spacing_out_y.abs()
            * spacing_in_y.abs()
        )
    )
    coupling_reverse_x = (
        wavelengths_real
        * distance_abs
        / (
            refractive_real
            * output_counts[1]
            * spacing_out_x.abs()
            * spacing_in_x.abs()
        )
    )
    is_input_narrow = torch.any(
        ((input_chirp_limit_y < 1.0) | (input_chirp_limit_x < 1.0)).detach(),
    )
    is_output_narrow = torch.any(
        ((output_chirp_limit_y < 1.0) | (output_chirp_limit_x < 1.0)).detach(),
    )
    is_coupling_narrow = torch.any(
        (
            (coupling_forward_y < 1.0)
            | (coupling_forward_x < 1.0)
            | (coupling_reverse_y < 1.0)
            | (coupling_reverse_x < 1.0)
        ).detach(),
    )
    return ScaledFresnelSamplingFacts(
        input_chirp_too_narrow=is_input_narrow,
        output_chirp_too_narrow=is_output_narrow,
        transform_coupling_too_narrow=is_coupling_narrow,
    )


def scaled_fresnel_calculation(
    *,
    computational_counts: tuple[int, int],
    computational_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_sample_counts: tuple[int, int],
    output_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    axial_distance: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    device: torch.device,
) -> ScaledFresnelCalculation:
    """
    构造带尺度 Fresnel 的二次相位、归一化与 chirp_z 参数

    """

    wavelengths_real = wavelengths.to(dtype=real_dtype, device=device)
    refractive_real = refractive_indices.to(
        dtype=real_dtype,
        device=device,
    )
    distance = axial_distance.to(dtype=real_dtype, device=device)
    distance_abs = distance.abs()
    input_y, input_x = spatial_sample_positions(
        sample_counts=computational_counts,
        signed_spacing=input_signed_spacing,
        first_sample_position=computational_first_sample_position,
        reference=torch.zeros((), dtype=real_dtype, device=device),
    )
    output_y, output_x = spatial_sample_positions(
        sample_counts=output_sample_counts,
        signed_spacing=output_signed_spacing,
        first_sample_position=output_first_sample_position,
        reference=torch.zeros((), dtype=real_dtype, device=device),
    )
    cycles_curvature = (
        refractive_real / (2.0 * wavelengths_real * distance_abs)
    ).reshape(-1, 1, 1)
    input_cycles = cycles_curvature * (
        input_y[:, None].square() + input_x[None, :].square()
    )
    output_cycles = cycles_curvature * (
        output_y[:, None].square() + output_x[None, :].square()
    )
    input_chirp = _unit_phasor_from_cycles(input_cycles).to(dtype=complex_dtype)
    output_chirp = _unit_phasor_from_cycles(output_cycles).to(dtype=complex_dtype)
    prefactor = -1j * refractive_real / (wavelengths_real * distance_abs)
    source_cell_area = (
        input_signed_spacing[0].to(dtype=real_dtype, device=device).abs()
        * input_signed_spacing[1].to(dtype=real_dtype, device=device).abs()
    )
    normalization = (prefactor * source_cell_area).to(dtype=complex_dtype)
    beta_cycles = refractive_real / (wavelengths_real * distance_abs)
    spacing_in_y = input_signed_spacing[0].to(dtype=real_dtype, device=device)
    spacing_in_x = input_signed_spacing[1].to(dtype=real_dtype, device=device)
    spacing_out_y = output_signed_spacing[0].to(
        dtype=real_dtype,
        device=device,
    )
    spacing_out_x = output_signed_spacing[1].to(
        dtype=real_dtype,
        device=device,
    )
    origin_in_y = computational_first_sample_position[0].to(
        dtype=real_dtype,
        device=device,
    )
    origin_in_x = computational_first_sample_position[1].to(
        dtype=real_dtype,
        device=device,
    )
    origin_out_y = output_first_sample_position[0].to(
        dtype=real_dtype,
        device=device,
    )
    origin_out_x = output_first_sample_position[1].to(
        dtype=real_dtype,
        device=device,
    )
    starting_cycles_x = -beta_cycles * spacing_in_x * origin_out_x
    cycles_step_x = -beta_cycles * spacing_in_x * spacing_out_x
    starting_cycles_y = -beta_cycles * spacing_in_y * origin_out_y
    cycles_step_y = -beta_cycles * spacing_in_y * spacing_out_y
    output_phase_offset_y = _unit_phasor_from_cycles(
        (-beta_cycles).reshape(-1, 1) * (origin_in_y * output_y).reshape(1, -1),
    ).to(dtype=complex_dtype)
    output_phase_offset_x = _unit_phasor_from_cycles(
        (-beta_cycles).reshape(-1, 1) * (origin_in_x * output_x).reshape(1, -1),
    ).to(dtype=complex_dtype)
    return ScaledFresnelCalculation(
        input_chirp=input_chirp,
        output_chirp=output_chirp,
        normalization=normalization,
        output_phase_offset_y=output_phase_offset_y,
        output_phase_offset_x=output_phase_offset_x,
        starting_cycles_x=starting_cycles_x,
        cycles_step_x=cycles_step_x,
        starting_cycles_y=starting_cycles_y,
        cycles_step_y=cycles_step_y,
    )


def propagate_scaled_fresnel(
    *,
    envelope: torch.Tensor,
    calculation: ScaledFresnelCalculation,
    computational_counts: tuple[int, int],
    padding: tuple[int, int],
    output_sample_counts: tuple[int, int],
    axial_distance: torch.Tensor,
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    device: torch.device,
) -> torch.Tensor:
    """
    以二次相位啁啾与逐光谱可分离 chirp_z 评估目标网格上的 Collins 包络

    """

    embedded = _embed_computational_window(
        envelope=envelope,
        computational_counts=computational_counts,
        padding=padding,
    )
    spectrum_count = embedded.shape[-4]
    backward_check = (
        axial_distance.to(dtype=real_dtype, device=device) < 0.0
    ).detach()
    is_backward = bool(backward_check) if not backward_check.is_meta else False
    embedded_by_spectrum = embedded.movedim(-4, 0)
    outputs: list[torch.Tensor] = []
    for spectrum_index in range(spectrum_count):
        slice_s = embedded_by_spectrum[spectrum_index]
        source = slice_s.conj() if is_backward else slice_s
        chirped = source * calculation.input_chirp[spectrum_index]
        evaluated_x = chirp_z_transform(
            chirped,
            output_count=output_sample_counts[1],
            starting_cycles=calculation.starting_cycles_x[spectrum_index],
            cycles_step=calculation.cycles_step_x[spectrum_index],
        )
        evaluated_xy = chirp_z_transform(
            evaluated_x.movedim(-2, -1),
            output_count=output_sample_counts[0],
            starting_cycles=calculation.starting_cycles_y[spectrum_index],
            cycles_step=calculation.cycles_step_y[spectrum_index],
        ).movedim(-1, -2)
        offset_y = calculation.output_phase_offset_y[spectrum_index].reshape(
            output_sample_counts[0],
            1,
        )
        offset_x = calculation.output_phase_offset_x[spectrum_index].reshape(
            1,
            output_sample_counts[1],
        )
        evaluated_xy = evaluated_xy * offset_y.to(dtype=evaluated_xy.dtype)
        evaluated_xy = evaluated_xy * offset_x.to(dtype=evaluated_xy.dtype)
        output_chirp = calculation.output_chirp[spectrum_index]
        propagated = (
            evaluated_xy
            * output_chirp.to(dtype=evaluated_xy.dtype)
            * calculation.normalization[spectrum_index]
        )
        if is_backward:
            propagated = propagated.conj()
        outputs.append(propagated)
    result = torch.stack(outputs, dim=0).movedim(0, -4)
    return result.to(dtype=complex_dtype)

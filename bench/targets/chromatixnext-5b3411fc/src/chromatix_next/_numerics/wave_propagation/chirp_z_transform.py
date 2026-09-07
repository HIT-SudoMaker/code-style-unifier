from __future__ import annotations

import torch

from ..complex_phase import _unit_phasor_from_cycles


def chirp_z_transform(
    values: torch.Tensor,
    *,
    output_count: int,
    starting_cycles: torch.Tensor,
    cycles_step: torch.Tensor,
) -> torch.Tensor:
    """
    以 Bluestein 圆卷积计算末轴未归一化 Chirp-Z 复和

    相位以周期（cycles）传入：起始相位 ``starting_cycles`` 与每索引相位步进
    ``cycles_step``，二者均在周期单位下与原解析式
    ``exp(i·2π·(s·n + 0.5·p·n²))`` 严格一致。调用方负责把任何弧度量在传入前
    除以 ``2π``，避免在生产核内部构造巨弧度。

    """

    input_count = values.shape[-1]
    convolution_count = 1 << (input_count + output_count - 2).bit_length()
    input_index = torch.arange(
        input_count,
        dtype=values.real.dtype,
        device=values.device,
    )
    output_index = torch.arange(
        output_count,
        dtype=values.real.dtype,
        device=values.device,
    )
    input_cycles = (
        input_index * starting_cycles[..., None]
        + 0.5 * input_index.square() * cycles_step[..., None]
    )
    chirped_values = values * _unit_phasor_from_cycles(input_cycles)
    positive_kernel_cycles = (
        -0.5 * output_index.square() * cycles_step[..., None]
    )
    negative_index = torch.arange(
        -(input_count - 1),
        0,
        dtype=values.real.dtype,
        device=values.device,
    )
    negative_kernel_cycles = (
        -0.5 * negative_index.square() * cycles_step[..., None]
    )
    gap_count = convolution_count - output_count - input_count + 1
    convolution_kernel = torch.cat(
        (
            _unit_phasor_from_cycles(positive_kernel_cycles),
            torch.zeros(
                (*cycles_step.shape, gap_count),
                dtype=values.dtype,
                device=values.device,
            ),
            _unit_phasor_from_cycles(negative_kernel_cycles),
        ),
        dim=-1,
    )
    convolved = torch.fft.ifft(
        torch.fft.fft(
            chirped_values,
            n=convolution_count,
            dim=-1,
        )
        * torch.fft.fft(
            convolution_kernel,
            n=convolution_count,
            dim=-1,
        ),
        n=convolution_count,
        dim=-1,
    )
    output_cycles = 0.5 * output_index.square() * cycles_step[..., None]
    return convolved[..., :output_count] * _unit_phasor_from_cycles(output_cycles)


from __future__ import annotations

import torch

import chromatix_next.errors as _errors


def sampled_field_power_amplitude(
    *,
    total_power: torch.Tensor,
    spectral_weights: torch.Tensor,
    unit_envelope: torch.Tensor,
    cell_area: torch.Tensor,
) -> torch.Tensor:
    """
    由总功率与采样单位包络的模方导出标量振幅

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

def spectral_intensity_reduction(
    envelope: torch.Tensor,
    spectral_weights: torch.Tensor,
) -> torch.Tensor:
    """
    计算参考 ``|E|²`` 偏振求和与光谱加权约减，返回实数空间张量

    """
    if not torch.is_complex(envelope):
        raise _errors.OpticalValueError(
            "spectral_intensity_reduction_envelope_not_complex",
            "光强约减要求复数包络，收到的是实数张量，"
            "请确认上游返回的是光场而不是已经约减过的光强",
        )
    if envelope.dim() < 4:
        raise _errors.OpticalValueError(
            "spectral_intensity_reduction_envelope_rank_invalid",
            "光强约减要求包络至少有光谱、偏振与两个空间轴共四个维度，"
            f"收到的包络只有 {envelope.dim()} 个维度",
        )
    if spectral_weights.dim() != 1:
        raise _errors.OpticalValueError(
            "spectral_intensity_reduction_weights_not_1d",
            "光谱权重必须是一维张量，每个波长一个权重，"
            f"收到的权重有 {spectral_weights.dim()} 个维度",
        )
    if spectral_weights.shape[0] != envelope.shape[-4]:
        raise _errors.OpticalValueError(
            "spectral_intensity_reduction_spectrum_mismatch",
            f"光谱权重的长度 {spectral_weights.shape[0]} 与包络的光谱维长度 "
            f"{envelope.shape[-4]} 不一致，二者必须逐波长对应",
        )

    # 模方以实/虚部分别平方求和，避免 abs 在零点处的梯度奇异
    squared = envelope.real ** 2 + envelope.imag ** 2
    aligned_weights = spectral_weights.to(dtype=squared.dtype)

    polarization_reduced = squared.sum(dim=-3)
    weight_shape = [1] * (polarization_reduced.dim() - 3) + [
        polarization_reduced.shape[-3],
        1,
        1,
    ]
    weighted = polarization_reduced * aligned_weights.reshape(weight_shape)
    return weighted.sum(dim=-3)

from __future__ import annotations

import torch

import chromatix_next.errors as _errors

from .complex_phase import _unit_phasor_from_cycles


def normalize_optical_path_lengths(
    values: tuple[float | torch.Tensor, ...],
) -> tuple[float | torch.Tensor, ...]:
    """
    规范光程长度；Python 实数保持实数，张量保持设备与 float64 精度

    上游 OpticalPathReference 已严格拒绝非 float64 张量。本函数只保留合格张量的
    当前设备与计算图，并把 Python 实数折算为 Python float；不承担升精度策略。

    """

    return tuple(
        value
        if isinstance(value, torch.Tensor)
        else float(value)
        for value in values
    )

def _stacked_reference_lengths(
    values: tuple[float | torch.Tensor, ...],
    *,
    device: torch.device,
) -> torch.Tensor:
    # 含张量时必须用 stack：torch.tensor 会脱离计算图，使可训练参考长度丢失梯度
    if any(
        isinstance(value, torch.Tensor) and value.device != device
        for value in values
    ):
        raise _errors.OpticalValueError(
            "optical_path_reference_device_mismatch",
            "以张量给出的光程参考必须与承载它的光场位于同一设备；"
            "数值核不会静默搬运光程参考",
        )
    if any(isinstance(value, torch.Tensor) for value in values):
        return torch.stack(
            [
                value
                if isinstance(value, torch.Tensor)
                else torch.tensor(
                    value,
                    device=device,
                    dtype=torch.float64,
                )
                for value in values
            ],
        )
    return torch.tensor(
        values,
        device=device,
        dtype=torch.float64,
    )


def accumulate_optical_path_lengths(
    values: tuple[float | torch.Tensor, ...],
    increment: float | torch.Tensor,
    *,
    device: torch.device,
) -> tuple[torch.Tensor, ...]:
    """
    在设备本地 float64 域把逐光谱或公共增量累加到光程长度

    """

    current = _stacked_reference_lengths(values, device=device)
    added = torch.as_tensor(
        increment,
        device=device,
        dtype=torch.float64,
    )
    if added.dim() == 0:
        added = added.expand(len(values))
    if added.dim() != 1 or added.shape[0] != len(values):
        raise _errors.OpticalValueError(
            "optical_path_increment_spectrum_mismatch",
            "光程增量要么是公共标量，要么逐光谱给出一维张量；"
            f"预期 {len(values)} 项，收到的形状是 {tuple(added.shape)}",
        )
    return tuple(current + added)


def express_envelope_in_optical_path_reference(
    *,
    envelope: torch.Tensor,
    wavelengths: tuple[float, ...],
    source_reference_lengths: tuple[float | torch.Tensor, ...],
    destination_reference_lengths: tuple[float | torch.Tensor, ...],
) -> torch.Tensor:
    """
    把复包络从源光程参考表达至目标光程参考

    """

    wavelength_values = torch.tensor(
        wavelengths,
        device=envelope.device,
        dtype=torch.float64,
    )
    source_values = _stacked_reference_lengths(
        source_reference_lengths,
        device=envelope.device,
    )
    destination_values = _stacked_reference_lengths(
        destination_reference_lengths,
        device=envelope.device,
    )
    cycles = (source_values - destination_values) / wavelength_values
    carrier = _unit_phasor_from_cycles(cycles).to(dtype=envelope.dtype)
    carrier_shape = [1] * (envelope.dim() - 4) + [
        envelope.shape[-4],
        1,
        1,
        1,
    ]
    return envelope * carrier.reshape(carrier_shape)


def sum_envelopes_in_optical_path_reference(
    *,
    destination_envelope: torch.Tensor,
    added_envelope: torch.Tensor,
    wavelengths: tuple[float, ...],
    destination_reference_lengths: tuple[float | torch.Tensor, ...],
    added_reference_lengths: tuple[float | torch.Tensor, ...],
) -> torch.Tensor:
    """
    把 added 包络表达至 destination 光程参考后执行复包络相加

    """

    expressed_added_envelope = express_envelope_in_optical_path_reference(
        envelope=added_envelope,
        wavelengths=wavelengths,
        source_reference_lengths=added_reference_lengths,
        destination_reference_lengths=destination_reference_lengths,
    )
    return destination_envelope + expressed_added_envelope

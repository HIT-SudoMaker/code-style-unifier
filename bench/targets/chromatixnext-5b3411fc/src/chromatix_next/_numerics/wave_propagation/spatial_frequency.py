from __future__ import annotations

from typing import Literal

import torch


def to_frequency(
    spatial_values: torch.Tensor,
    *,
    is_centered: bool = False,
    normalization: Literal["backward", "ortho"] = "backward",
) -> torch.Tensor:
    """
    把最后两个空间轴变换到指定排列与归一化的频域

    """
    frequency_values = torch.fft.fftn(
        spatial_values,
        dim=(-2, -1),
        norm=normalization,
    )
    return (
        torch.fft.fftshift(
            frequency_values,
            dim=(-2, -1),
        )
        if is_centered
        else frequency_values
    )

def to_space(
    frequency_values: torch.Tensor,
    *,
    is_centered: bool = False,
    normalization: Literal["backward", "ortho"] = "backward",
) -> torch.Tensor:
    """
    把指定排列与归一化的最后两个频率轴变换回空域

    """
    ordered_values = (
        torch.fft.ifftshift(
            frequency_values,
            dim=(-2, -1),
        )
        if is_centered
        else frequency_values
    )
    return torch.fft.ifftn(
        ordered_values,
        dim=(-2, -1),
        norm=normalization,
    )


def apply_frequency_transfer(
    spatial_values: torch.Tensor,
    frequency_transfer: torch.Tensor,
) -> torch.Tensor:
    """
    在相同空间网格的频域逐光谱作用传递函数

    """
    frequency_values = to_frequency(spatial_values)
    transfer_by_polarization = frequency_transfer.unsqueeze(-3)
    return to_space(
        frequency_values * transfer_by_polarization,
    )

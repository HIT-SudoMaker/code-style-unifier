from __future__ import annotations

import math

import torch


def medium_wave_numbers(
    *,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor | float,
) -> torch.Tensor:
    """
    由真空波长与折射率计算介质波数 ``2πn/λ``

    """

    return 2.0 * math.pi * refractive_indices / wavelengths

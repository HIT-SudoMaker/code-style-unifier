from __future__ import annotations

import math

import torch

_TAU = 2.0 * math.pi



def _unit_phasor_from_cycles(
    cycles: torch.Tensor,
) -> torch.Tensor:
    fraction = torch.remainder(cycles, 1.0)
    centred = torch.where(fraction >= 0.5, fraction - 1.0, fraction)
    radians = _TAU * centred
    return torch.polar(torch.ones_like(radians), radians)

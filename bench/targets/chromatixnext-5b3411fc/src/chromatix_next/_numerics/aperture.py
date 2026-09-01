from __future__ import annotations

import torch

from chromatix_next._numerics.spatial_sampling import spatial_sample_positions


def circular_aperture_mask(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    radius: torch.Tensor,
) -> torch.Tensor:
    """
    合成含闭边界的圆形二元孔径掩膜

    """

    position_y, position_x = spatial_sample_positions(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        reference=radius,
    )
    return (
        position_y[:, None].square() + position_x[None, :].square()
        <= radius.square()
    ).detach().to(dtype=radius.dtype)

def square_aperture_mask(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    width: torch.Tensor,
) -> torch.Tensor:
    """
    合成含闭边界的方形二元孔径掩膜

    """

    position_y, position_x = spatial_sample_positions(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        reference=width,
    )
    return (
        torch.maximum(
            position_y[:, None].abs(),
            position_x[None, :].abs(),
        )
        <= width / 2.0
    ).detach().to(dtype=width.dtype)

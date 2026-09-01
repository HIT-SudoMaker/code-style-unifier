from __future__ import annotations

import torch

from .spatial_sampling import spatial_sample_positions


def collimated_launch_positions(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    launch_origin: torch.Tensor,
    launch_tangent_x: torch.Tensor,
    launch_tangent_y: torch.Tensor,
    reference: torch.Tensor,
) -> torch.Tensor:
    """
    返回 (ray_count, 3) 全局位置；ray_count = N_y * N_x，按行优先展平

    """

    counts_y, counts_x = sample_counts
    coords_y, coords_x = spatial_sample_positions(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        reference=reference,
    )
    grid_y, grid_x = torch.meshgrid(coords_y, coords_x, indexing="ij")
    grid_y_flat = grid_y.reshape(-1)
    grid_x_flat = grid_x.reshape(-1)
    origin = launch_origin.to(
        device=reference.device,
        dtype=reference.dtype,
    ).view(1, 3)
    tangent_x = launch_tangent_x.to(
        device=reference.device,
        dtype=reference.dtype,
    ).view(1, 3)
    tangent_y = launch_tangent_y.to(
        device=reference.device,
        dtype=reference.dtype,
    ).view(1, 3)
    del counts_y, counts_x
    return (
        origin
        + grid_y_flat.view(-1, 1) * tangent_y
        + grid_x_flat.view(-1, 1) * tangent_x
    )

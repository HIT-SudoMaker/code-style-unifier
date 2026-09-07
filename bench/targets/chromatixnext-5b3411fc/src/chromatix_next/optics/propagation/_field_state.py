from __future__ import annotations

import torch

from chromatix_next._numerics.optical_path_reference import (
    accumulate_optical_path_lengths,
)

from ..field import OpticalField, OpticalPathReference


def _propagation_spectrum(
    field: OpticalField,
    axial_distance: float | torch.Tensor,
    *,
    reference: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    distance = torch.as_tensor(
        axial_distance,
        device=reference.device,
        dtype=reference.dtype,
    )
    wavelengths = torch.as_tensor(
        field.spectrum.wavelengths,
        device=reference.device,
        dtype=reference.dtype,
    )
    return (
        distance,
        wavelengths,
        field.medium.refractive_index(wavelengths),
    )

def _advance_path_reference(
    *,
    field: OpticalField,
    axial_distances: tuple[float | torch.Tensor, ...],
) -> OpticalPathReference:
    device = field.envelope.device
    wavelengths = torch.tensor(
        field.spectrum.wavelengths,
        device=device,
        dtype=torch.float64,
    )
    refractive_indices = field.medium.refractive_index(wavelengths)
    total_distance = torch.zeros(
        (),
        device=device,
        dtype=torch.float64,
    )
    for axial_distance in axial_distances:
        total_distance = total_distance + torch.as_tensor(
            axial_distance,
            device=device,
            dtype=torch.float64,
        )
    return OpticalPathReference(
        lengths=accumulate_optical_path_lengths(
            field.path_reference.lengths,
            refractive_indices * total_distance,
            device=device,
        ),
    )

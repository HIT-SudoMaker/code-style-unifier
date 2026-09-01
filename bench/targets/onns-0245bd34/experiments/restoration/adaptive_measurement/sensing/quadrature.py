from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import torch

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.observations import OpticalObservation


@dataclass(frozen=True, slots=True, eq=False)
class QuadratureFieldEstimate:
    """Image-plane cross term inferred from four calibrated phase steps."""

    cross_term: torch.Tensor
    incoherent_intensity: torch.Tensor
    design_condition_number: float
    observation_ids: tuple[str, ...]


def demodulate_phase_shifted_observations(
    observations: Sequence[OpticalObservation],
) -> QuadratureFieldEstimate:
    """Recover the image-plane cross term from four delivered piston states."""
    frames = tuple(observations)
    _validate_quadrature_frames(frames)
    device = frames[0].intensity.device
    dtype = frames[0].intensity.dtype
    pistons = torch.tensor(
        [frame.delivered_piston_radians for frame in frames],
        device=device,
        dtype=dtype,
    )
    design = torch.stack(
        (
            torch.ones_like(pistons),
            2.0 * torch.cos(pistons),
            -2.0 * torch.sin(pistons),
        ),
        dim=1,
    )
    singular_values = torch.linalg.svdvals(design)
    if float(singular_values[-1].item()) <= torch.finfo(dtype).eps:
        raise invalid_restoration_contract(
            "delivered piston states do not identify a complex cross term"
        )
    intensity_stack = torch.stack([frame.intensity for frame in frames], dim=0)
    coefficients = torch.einsum(
        "cf,f...->c...",
        torch.linalg.pinv(design),
        intensity_stack,
    )
    cross_term = torch.complex(coefficients[1], coefficients[2])
    return QuadratureFieldEstimate(
        cross_term=cross_term,
        incoherent_intensity=coefficients[0],
        design_condition_number=float(
            (singular_values[0] / singular_values[-1]).item()
        ),
        observation_ids=tuple(frame.observation_id for frame in frames),
    )


def _validate_quadrature_frames(
    observations: tuple[OpticalObservation, ...],
) -> None:
    if len(observations) != 4:
        raise invalid_restoration_contract(
            "quadrature demodulation requires exactly four observations"
        )
    first = observations[0]
    if any(not isinstance(frame, OpticalObservation) for frame in observations):
        raise TypeError("observations must contain OpticalObservation values")
    if any(not frame.is_reference_enabled for frame in observations):
        raise invalid_restoration_contract(
            "quadrature observations must keep the coherent reference enabled"
        )
    if len({frame.observation_id for frame in observations}) != 4:
        raise invalid_restoration_contract(
            "quadrature observations must have distinct identities"
        )
    if any(frame.intensity.shape != first.intensity.shape for frame in observations):
        raise invalid_restoration_contract(
            "quadrature observations must have matching intensity shapes"
        )
    if any(
        not torch.allclose(
            frame.command_phase_radians,
            first.command_phase_radians,
        )
        for frame in observations[1:]
    ):
        raise invalid_restoration_contract(
            "quadrature observations must share one spatial phase action"
        )

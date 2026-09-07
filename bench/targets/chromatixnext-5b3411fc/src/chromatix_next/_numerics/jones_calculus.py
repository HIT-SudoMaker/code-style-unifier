from __future__ import annotations

import torch

from .complex_phase import _unit_phasor_from_cycles


def _eigenstate_jones_vector(
    *,
    azimuth_radians: torch.Tensor,
    ellipticity_radians: torch.Tensor,
) -> torch.Tensor:
    cosine_azimuth = torch.cos(azimuth_radians)
    sine_azimuth = torch.sin(azimuth_radians)
    cosine_ellipticity = torch.cos(ellipticity_radians)
    sine_ellipticity = torch.sin(ellipticity_radians)
    eigenstate_x_component = (
        cosine_ellipticity * cosine_azimuth
        - 1j * sine_ellipticity * sine_azimuth
    )
    eigenstate_y_component = (
        cosine_ellipticity * sine_azimuth
        + 1j * sine_ellipticity * cosine_azimuth
    )
    return torch.stack((eigenstate_x_component, eigenstate_y_component))

def _eigenstate_projector_from_jones_vector(
    *,
    eigenstate: torch.Tensor,
) -> torch.Tensor:
    return torch.outer(eigenstate, eigenstate.conj())


def _retarder_matrix(
    *,
    retardance_cycles: torch.Tensor,
    retarded_eigenstate_projector: torch.Tensor,
) -> torch.Tensor:
    retarded_eigenstate_phasor = _unit_phasor_from_cycles(
        retardance_cycles / 2.0,
    )
    orthogonal_eigenstate_phasor = _unit_phasor_from_cycles(
        -retardance_cycles / 2.0,
    )
    polarization_identity_matrix = torch.eye(
        2,
        dtype=retarded_eigenstate_projector.dtype,
        device=retarded_eigenstate_projector.device,
    )
    orthogonal_eigenstate_projector = (
        polarization_identity_matrix - retarded_eigenstate_projector
    )
    retarder_matrix = (
        retarded_eigenstate_phasor * retarded_eigenstate_projector
        + orthogonal_eigenstate_phasor * orthogonal_eigenstate_projector
    )
    return retarder_matrix


def _retarder_envelope(
    *,
    envelope: torch.Tensor,
    retardance_cycles: torch.Tensor,
    retarded_eigenstate_azimuth_radians: torch.Tensor,
    retarded_eigenstate_ellipticity_radians: torch.Tensor,
) -> torch.Tensor:
    retarded_eigenstate = _eigenstate_jones_vector(
        azimuth_radians=retarded_eigenstate_azimuth_radians,
        ellipticity_radians=retarded_eigenstate_ellipticity_radians,
    )
    retarded_eigenstate_projector = _eigenstate_projector_from_jones_vector(
        eigenstate=retarded_eigenstate,
    )
    retarder_matrix = _retarder_matrix(
        retardance_cycles=retardance_cycles,
        retarded_eigenstate_projector=retarded_eigenstate_projector,
    )
    output_envelope = torch.einsum(
        "ij,...jhw->...ihw",
        retarder_matrix,
        envelope,
    )
    return output_envelope

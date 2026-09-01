from __future__ import annotations

import math
from typing import Literal

import torch

_PupilPolarization = Literal[
    "laboratory_x",
    "radial",
    "azimuthal",
]


def _fourier_bessel_focus(
    *,
    polarization: _PupilPolarization,
    radial_sample_count: int,
    destination_y: torch.Tensor,
    destination_x: torch.Tensor,
    wavelength: float,
    refractive_index: float,
    focal_length: float,
    maximum_convergence_angle: float,
    axial_distance_from_focus: float,
) -> torch.Tensor:
    dtype = torch.float64
    radius_limit = (
        focal_length * math.sin(maximum_convergence_angle)
    )
    radial_spacing = radius_limit / radial_sample_count
    pupil_radius = (
        torch.arange(radial_sample_count, dtype=dtype) + 0.5
    ) * radial_spacing
    sine_theta = pupil_radius / focal_length
    cosine_theta = torch.sqrt(1.0 - sine_theta.square())
    destination_coordinate_y, destination_coordinate_x = torch.meshgrid(
        destination_y.to(dtype=dtype),
        destination_x.to(dtype=dtype),
        indexing="ij",
    )
    destination_radius = torch.sqrt(
        destination_coordinate_y.square()
        + destination_coordinate_x.square(),
    )
    destination_azimuth = torch.atan2(
        destination_coordinate_y,
        destination_coordinate_x,
    )
    wave_number = 2.0 * math.pi * refractive_index / wavelength
    bessel_argument = (
        wave_number
        * pupil_radius[:, None, None]
        * destination_radius[None, :, :]
        / focal_length
    )
    bessel_0 = torch.special.bessel_j0(bessel_argument)
    bessel_1 = torch.special.bessel_j1(bessel_argument)
    bessel_2 = _bessel_j2(bessel_argument, bessel_0, bessel_1)
    angular_field = _angular_field(
        polarization=polarization,
        sine_theta=sine_theta,
        cosine_theta=cosine_theta,
        destination_azimuth=destination_azimuth,
        bessel_0=bessel_0,
        bessel_1=bessel_1,
        bessel_2=bessel_2,
    )
    cosine_theta_minus_one = (
        -sine_theta.square() / (1.0 + cosine_theta)
    )
    radial_weight = (
        -1j
        * wave_number
        / (2.0 * math.pi * focal_length)
        * pupil_radius
        * radial_spacing
        / cosine_theta
        * torch.exp(
            1j
            * wave_number
            * cosine_theta_minus_one
            * axial_distance_from_focus,
        )
    )
    return (
        angular_field
        * radial_weight[:, None, None, None]
    ).sum(dim=0)


def _angular_field(
    *,
    polarization: _PupilPolarization,
    sine_theta: torch.Tensor,
    cosine_theta: torch.Tensor,
    destination_azimuth: torch.Tensor,
    bessel_0: torch.Tensor,
    bessel_1: torch.Tensor,
    bessel_2: torch.Tensor,
) -> torch.Tensor:
    root_cosine = torch.sqrt(cosine_theta)[:, None, None]
    sine = sine_theta[:, None, None]
    cosine = cosine_theta[:, None, None]
    cosine_azimuth = torch.cos(destination_azimuth)[None, :, :]
    sine_azimuth = torch.sin(destination_azimuth)[None, :, :]
    if polarization == "laboratory_x":
        return torch.stack(
            (
                math.pi
                * root_cosine
                * (
                    (1.0 + cosine) * bessel_0
                    + (1.0 - cosine)
                    * bessel_2
                    * torch.cos(2.0 * destination_azimuth)[None, :, :]
                ),
                math.pi
                * root_cosine
                * (1.0 - cosine)
                * bessel_2
                * torch.sin(2.0 * destination_azimuth)[None, :, :],
                -2j
                * math.pi
                * root_cosine
                * sine
                * bessel_1
                * cosine_azimuth,
            ),
            dim=1,
        )
    if polarization == "radial":
        return torch.stack(
            (
                -2j
                * math.pi
                * root_cosine
                * cosine
                * bessel_1
                * cosine_azimuth,
                -2j
                * math.pi
                * root_cosine
                * cosine
                * bessel_1
                * sine_azimuth,
                2.0 * math.pi * root_cosine * sine * bessel_0,
            ),
            dim=1,
        )
    return torch.stack(
        (
            2j
            * math.pi
            * root_cosine
            * bessel_1
            * sine_azimuth,
            -2j
            * math.pi
            * root_cosine
            * bessel_1
            * cosine_azimuth,
            torch.zeros_like(bessel_0),
        ),
        dim=1,
    )


def _bessel_j2(
    argument: torch.Tensor,
    bessel_0: torch.Tensor,
    bessel_1: torch.Tensor,
) -> torch.Tensor:
    small = argument.abs() < 1.0e-3
    safe_argument = torch.where(
        small,
        torch.ones_like(argument),
        argument,
    )
    recurrence = 2.0 * bessel_1 / safe_argument - bessel_0
    squared = argument.square()
    series = (
        squared / 8.0
        - squared.square() / 96.0
        + squared.pow(3) / 3072.0
        - squared.pow(4) / 184320.0
    )
    return torch.where(small, series, recurrence)

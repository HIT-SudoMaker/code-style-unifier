from __future__ import annotations

from dataclasses import dataclass
import math

import torch


@dataclass(frozen=True, slots=True)
class _AplanaticReferenceResult:
    complete_field: torch.Tensor
    residual_envelope: torch.Tensor
    output_path_lengths: torch.Tensor


def _reference_sphere_field(
    pupil_envelope: torch.Tensor,
    *,
    pupil_y: torch.Tensor,
    pupil_x: torch.Tensor,
    focal_length: float,
    maximum_convergence_angle: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    # 独立构造正弦条件参考球上的完整笛卡尔电场
    coordinate_y, coordinate_x = torch.meshgrid(
        pupil_y,
        pupil_x,
        indexing="ij",
    )
    radius = torch.sqrt(coordinate_x.square() + coordinate_y.square())
    focal = torch.as_tensor(
        focal_length,
        dtype=torch.float64,
        device=pupil_envelope.device,
    )
    maximum_angle = torch.as_tensor(
        maximum_convergence_angle,
        dtype=torch.float64,
        device=pupil_envelope.device,
    )
    support = (radius <= focal * torch.sin(maximum_angle)).detach()
    sin_theta = torch.where(
        support,
        radius / focal,
        torch.zeros_like(radius),
    )
    cos_theta = torch.sqrt(1.0 - sin_theta.square())
    azimuth = torch.atan2(coordinate_y, coordinate_x)
    cos_azimuth = torch.cos(azimuth)
    sin_azimuth = torch.sin(azimuth)
    field_x = pupil_envelope[..., 0, :, :]
    field_y = pupil_envelope[..., 1, :, :]
    field_radial = field_x * cos_azimuth + field_y * sin_azimuth
    field_azimuthal = -field_x * sin_azimuth + field_y * cos_azimuth
    apodization = torch.sqrt(cos_theta)
    sphere_x = apodization * (
        field_radial * cos_theta * cos_azimuth
        - field_azimuthal * sin_azimuth
    )
    sphere_y = apodization * (
        field_radial * cos_theta * sin_azimuth
        + field_azimuthal * cos_azimuth
    )
    sphere_z = apodization * field_radial * sin_theta
    sphere = torch.stack(
        (sphere_x, sphere_y, sphere_z),
        dim=-3,
    )
    sphere = sphere * support
    return sphere, sin_theta, cos_theta, support


def _direct_aplanatic_focus(
    pupil_envelope: torch.Tensor,
    *,
    pupil_y: torch.Tensor,
    pupil_x: torch.Tensor,
    destination_y: torch.Tensor,
    destination_x: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    input_path_lengths: torch.Tensor,
    focal_length: float,
    maximum_convergence_angle: float,
    axial_distance_from_focus: float,
) -> _AplanaticReferenceResult:
    # 以 complex128 固体角直接求和构造完整场、残余包络与输出光程
    sphere, sin_theta, cos_theta, support = _reference_sphere_field(
        pupil_envelope,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_convergence_angle,
    )
    pupil_coordinate_y, pupil_coordinate_x = torch.meshgrid(
        pupil_y,
        pupil_x,
        indexing="ij",
    )
    destination_coordinate_y, destination_coordinate_x = torch.meshgrid(
        destination_y,
        destination_x,
        indexing="ij",
    )
    radius = torch.sqrt(
        pupil_coordinate_x.square() + pupil_coordinate_y.square(),
    )
    safe_radius = torch.where(
        radius > 0.0,
        radius,
        torch.ones_like(radius),
    )
    cos_azimuth = torch.where(
        radius > 0.0,
        pupil_coordinate_x / safe_radius,
        torch.ones_like(radius),
    )
    sin_azimuth = torch.where(
        radius > 0.0,
        pupil_coordinate_y / safe_radius,
        torch.zeros_like(radius),
    )
    focal = torch.tensor(focal_length, dtype=torch.float64)
    axial_distance = torch.tensor(
        axial_distance_from_focus,
        dtype=torch.float64,
    )
    cell_area = (pupil_y[1] - pupil_y[0]).abs() * (
        pupil_x[1] - pupil_x[0]
    ).abs()
    focused_spectra: list[torch.Tensor] = []
    for spectral_index in range(wavelengths.numel()):
        wavelength = wavelengths[spectral_index]
        refractive_index = refractive_indices[spectral_index]
        wave_number = 2.0 * math.pi * refractive_index / wavelength
        lateral_projection = sin_theta[..., None, None] * (
            cos_azimuth[..., None, None] * destination_coordinate_x
            + sin_azimuth[..., None, None] * destination_coordinate_y
        )
        phase = wave_number * (
            focal
            + cos_theta[..., None, None] * axial_distance
            - lateral_projection
        )
        cartesian_weight = (
            -1j
            * wave_number
            * cell_area
            / (2.0 * math.pi * focal * cos_theta)
            * support
        )
        quadrature_kernel = cartesian_weight[..., None, None] * torch.exp(
            1j * phase,
        )
        focused = torch.einsum(
            "...cpq,pqhw->...chw",
            sphere[..., spectral_index, :, :, :],
            quadrature_kernel,
        )
        input_carrier = torch.exp(
            1j
            * (2.0 * math.pi / wavelength)
            * input_path_lengths[spectral_index]
        )
        focused_spectra.append(focused * input_carrier)
    complete_field = torch.stack(focused_spectra, dim=-4)
    output_path_lengths = input_path_lengths + refractive_indices * (
        focal + axial_distance
    )
    carrier_shape = (
        (1,) * len(pupil_envelope.shape[:-4])
        + (wavelengths.numel(), 1, 1, 1)
    )
    output_carrier = torch.exp(
        1j
        * (2.0 * math.pi / wavelengths)
        * output_path_lengths
    ).reshape(carrier_shape)
    return _AplanaticReferenceResult(
        complete_field=complete_field,
        residual_envelope=complete_field / output_carrier,
        output_path_lengths=output_path_lengths,
    )

from __future__ import annotations

from dataclasses import dataclass
import math

import torch

from chromatix_next._numerics.complex_phase import _unit_phasor_from_cycles
from chromatix_next._numerics.spatial_sampling import spatial_sample_positions
from chromatix_next._numerics.wave_number import medium_wave_numbers
from chromatix_next._numerics.wave_propagation.chirp_z_transform import (
    chirp_z_transform,
)


@dataclass(frozen=True, slots=True)
class _PupilGeometry:
    """
    承载消球差聚焦使用的瞳面角坐标事实

    """

    coordinate_y: torch.Tensor
    coordinate_x: torch.Tensor
    sine_squared: torch.Tensor
    cosine_polar_angle: torch.Tensor
    support: torch.Tensor
    cosine_azimuth: torch.Tensor
    sine_azimuth: torch.Tensor

def aplanatic_focus_applicability(
    *,
    input_sample_counts: tuple[int, int],
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    input_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    output_sample_counts: tuple[int, int],
    output_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    focal_length: torch.Tensor,
    maximum_convergence_angle: torch.Tensor,
    axial_distance_from_focus: torch.Tensor,
    reference: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    计算目标平面、完整入瞳与相位采样三个适用性谓词

    """

    pupil_y, pupil_x = spatial_sample_positions(
        input_sample_counts,
        input_signed_spacing,
        input_first_sample_position,
        reference,
    )
    destination_y, destination_x = spatial_sample_positions(
        output_sample_counts,
        output_signed_spacing,
        output_first_sample_position,
        reference,
    )
    geometry = _pupil_geometry(
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_convergence_angle,
    )
    footprint_contains_disk = _footprint_contains_disk(
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        input_signed_spacing=input_signed_spacing,
        aperture_radius=(
            focal_length * torch.sin(maximum_convergence_angle)
        ),
        reference=reference,
    )
    maximum_increment = _maximum_phase_increment(
        geometry=geometry,
        destination_y=destination_y,
        destination_x=destination_x,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        focal_length=focal_length,
        axial_distance_from_focus=axial_distance_from_focus,
    )
    return (
        focal_length + axial_distance_from_focus > 0.0,
        footprint_contains_disk,
        maximum_increment,
    )


def aplanatic_focus_envelope(
    *,
    envelope: torch.Tensor,
    input_sample_counts: tuple[int, int],
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    input_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    output_sample_counts: tuple[int, int],
    output_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    focal_length: torch.Tensor,
    maximum_convergence_angle: torch.Tensor,
    axial_distance_from_focus: torch.Tensor,
) -> torch.Tensor:
    """
    以两次带符号坐标的 Chirp-Z 变换计算残差 Debye–Wolf 光场

    """

    reference = envelope.real
    pupil_y, pupil_x = spatial_sample_positions(
        input_sample_counts,
        input_signed_spacing,
        input_first_sample_position,
        reference,
    )
    destination_y, destination_x = spatial_sample_positions(
        output_sample_counts,
        output_signed_spacing,
        output_first_sample_position,
        reference,
    )
    geometry = _pupil_geometry(
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_convergence_angle,
    )
    reference_sphere = _reference_sphere(
        envelope=envelope,
        geometry=geometry,
    )
    wave_numbers = medium_wave_numbers(
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
    )
    field_wave_number = wave_numbers.reshape(
        (1,) * (envelope.dim() - 4)
        + (wavelengths.shape[0], 1, 1, 1),
    )
    original_sine_squared = geometry.sine_squared
    cosine_polar_angle_minus_one = (
        -original_sine_squared / (1.0 + geometry.cosine_polar_angle)
    )
    cell_area = (
        _as_real(input_signed_spacing[0], reference).abs()
        * _as_real(input_signed_spacing[1], reference).abs()
    )
    axial_distance_cycles = (
        field_wave_number
        * cosine_polar_angle_minus_one
        * axial_distance_from_focus
        / (2.0 * math.pi)
    )
    weighted_sphere = (
        reference_sphere
        * geometry.support
        * (
            -1j
            * field_wave_number
            * cell_area
            / (
                2.0
                * math.pi
                * focal_length
                * geometry.cosine_polar_angle
            )
        )
        * _unit_phasor_from_cycles(axial_distance_cycles)
    )
    return _separable_aplanatic_czt(
        values=weighted_sphere,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        destination_y=destination_y,
        destination_x=destination_x,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        focal_length=focal_length,
        input_signed_spacing=input_signed_spacing,
        output_signed_spacing=output_signed_spacing,
    )


def _pupil_geometry(
    *,
    pupil_y: torch.Tensor,
    pupil_x: torch.Tensor,
    focal_length: torch.Tensor,
    maximum_convergence_angle: torch.Tensor,
) -> _PupilGeometry:
    coordinate_y, coordinate_x = torch.meshgrid(
        pupil_y,
        pupil_x,
        indexing="ij",
    )
    radius_squared = coordinate_y.square() + coordinate_x.square()
    unmasked_sine_squared = radius_squared / focal_length.square()
    support = (
        unmasked_sine_squared
        <= torch.sin(maximum_convergence_angle).square()
    ).detach()
    sine_squared = torch.where(
        support,
        unmasked_sine_squared,
        torch.zeros_like(unmasked_sine_squared),
    )
    cosine_polar_angle = torch.sqrt(1.0 - sine_squared)
    safe_radius = torch.where(
        radius_squared > 0.0,
        torch.sqrt(radius_squared),
        torch.ones_like(radius_squared),
    )
    return _PupilGeometry(
        coordinate_y=coordinate_y,
        coordinate_x=coordinate_x,
        sine_squared=sine_squared,
        cosine_polar_angle=cosine_polar_angle,
        support=support,
        cosine_azimuth=torch.where(
            radius_squared > 0.0,
            coordinate_x / safe_radius,
            torch.ones_like(radius_squared),
        ),
        sine_azimuth=torch.where(
            radius_squared > 0.0,
            coordinate_y / safe_radius,
            torch.zeros_like(radius_squared),
        ),
    )


def _reference_sphere(
    *,
    envelope: torch.Tensor,
    geometry: _PupilGeometry,
) -> torch.Tensor:
    sine_polar_angle = torch.sqrt(geometry.sine_squared)
    field_x = envelope[..., 0, :, :]
    field_y = envelope[..., 1, :, :]
    field_radial = (
        field_x * geometry.cosine_azimuth
        + field_y * geometry.sine_azimuth
    )
    field_azimuthal = (
        -field_x * geometry.sine_azimuth
        + field_y * geometry.cosine_azimuth
    )
    apodization = torch.sqrt(geometry.cosine_polar_angle)
    return torch.stack(
        (
            apodization
            * (
                field_radial
                * geometry.cosine_polar_angle
                * geometry.cosine_azimuth
                - field_azimuthal * geometry.sine_azimuth
            ),
            apodization
            * (
                field_radial
                * geometry.cosine_polar_angle
                * geometry.sine_azimuth
                + field_azimuthal * geometry.cosine_azimuth
            ),
            apodization * field_radial * sine_polar_angle,
        ),
        dim=-3,
    )


def _footprint_contains_disk(
    *,
    pupil_y: torch.Tensor,
    pupil_x: torch.Tensor,
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    aperture_radius: torch.Tensor,
    reference: torch.Tensor,
) -> torch.Tensor:
    spacing_y = _as_real(input_signed_spacing[0], reference).abs()
    spacing_x = _as_real(input_signed_spacing[1], reference).abs()
    footprint_scale = torch.stack(
        (
            aperture_radius.abs(),
            pupil_y[0].abs(),
            pupil_y[-1].abs(),
            pupil_x[0].abs(),
            pupil_x[-1].abs(),
        ),
    ).amax()
    tolerance = (
        64.0 * torch.finfo(reference.dtype).eps * footprint_scale
    )
    return (
        torch.minimum(pupil_y[0], pupil_y[-1]) - spacing_y / 2.0
        <= -aperture_radius + tolerance
    ) & (
        torch.maximum(pupil_y[0], pupil_y[-1]) + spacing_y / 2.0
        >= aperture_radius - tolerance
    ) & (
        torch.minimum(pupil_x[0], pupil_x[-1]) - spacing_x / 2.0
        <= -aperture_radius + tolerance
    ) & (
        torch.maximum(pupil_x[0], pupil_x[-1]) + spacing_x / 2.0
        >= aperture_radius - tolerance
    )


def _separable_aplanatic_czt(
    *,
    values: torch.Tensor,
    pupil_y: torch.Tensor,
    pupil_x: torch.Tensor,
    destination_y: torch.Tensor,
    destination_x: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    focal_length: torch.Tensor,
    input_signed_spacing: tuple[torch.Tensor, torch.Tensor],
    output_signed_spacing: tuple[torch.Tensor, torch.Tensor],
) -> torch.Tensor:
    reference = values.real
    batch_rank = values.dim() - 4
    wave_numbers = medium_wave_numbers(
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
    )
    transform_wave_number = wave_numbers.reshape(
        (1,) * batch_rank + (wavelengths.shape[0], 1, 1),
    )
    input_spacing_y = _as_real(input_signed_spacing[0], reference)
    input_spacing_x = _as_real(input_signed_spacing[1], reference)
    output_spacing_y = _as_real(output_signed_spacing[0], reference)
    output_spacing_x = _as_real(output_signed_spacing[1], reference)
    focused_x = chirp_z_transform(
        values,
        output_count=destination_x.shape[0],
        starting_cycles=(
            -transform_wave_number
            * input_spacing_x
            * destination_x[0]
            / (2.0 * math.pi * focal_length)
        ),
        cycles_step=(
            -transform_wave_number
            * input_spacing_x
            * output_spacing_x
            / (2.0 * math.pi * focal_length)
        ),
    )
    focused_xy = chirp_z_transform(
        focused_x.movedim(-2, -1),
        output_count=destination_y.shape[0],
        starting_cycles=(
            -transform_wave_number
            * input_spacing_y
            * destination_y[0]
            / (2.0 * math.pi * focal_length)
        ),
        cycles_step=(
            -transform_wave_number
            * input_spacing_y
            * output_spacing_y
            / (2.0 * math.pi * focal_length)
        ),
    ).movedim(-1, -2)
    origin_cycles = (
        -wave_numbers[:, None, None]
        / (2.0 * math.pi * focal_length)
        * (
            pupil_y[0] * destination_y[:, None]
            + pupil_x[0] * destination_x[None, :]
        )
    ).reshape(
        (1,) * batch_rank
        + (
            wavelengths.shape[0],
            1,
            destination_y.shape[0],
            destination_x.shape[0],
        ),
    )
    return focused_xy * _unit_phasor_from_cycles(origin_cycles)


def _maximum_phase_increment(
    *,
    geometry: _PupilGeometry,
    destination_y: torch.Tensor,
    destination_x: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    focal_length: torch.Tensor,
    axial_distance_from_focus: torch.Tensor,
) -> torch.Tensor:
    corner_y, corner_x = torch.meshgrid(
        torch.stack((destination_y[0], destination_y[-1])),
        torch.stack((destination_x[0], destination_x[-1])),
        indexing="ij",
    )
    wave_numbers = medium_wave_numbers(
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
    )
    maximum_increment = torch.zeros(
        (),
        dtype=geometry.coordinate_y.dtype,
        device=geometry.coordinate_y.device,
    )
    for axis in (-2, -1):
        maximum_increment = torch.maximum(
            maximum_increment,
            _axis_phase_increment(
                axis=axis,
                geometry=geometry,
                corner_y=corner_y,
                corner_x=corner_x,
                wave_numbers=wave_numbers,
                focal_length=focal_length,
                axial_distance_from_focus=axial_distance_from_focus,
            ),
        )
    return maximum_increment


def _axis_phase_increment(
    *,
    axis: int,
    geometry: _PupilGeometry,
    corner_y: torch.Tensor,
    corner_x: torch.Tensor,
    wave_numbers: torch.Tensor,
    focal_length: torch.Tensor,
    axial_distance_from_focus: torch.Tensor,
) -> torch.Tensor:
    if geometry.support.shape[axis] < 2:
        return torch.zeros(
            (),
            dtype=geometry.coordinate_y.dtype,
            device=geometry.coordinate_y.device,
        )
    first_slice = [slice(None), slice(None)]
    second_slice = [slice(None), slice(None)]
    first_slice[axis] = slice(None, -1)
    second_slice[axis] = slice(1, None)
    first = tuple(first_slice)
    second = tuple(second_slice)
    adjacent_support = (
        geometry.support[first] & geometry.support[second]
    )
    cosine_polar_angle_difference = (
        geometry.sine_squared[first] - geometry.sine_squared[second]
    ) / (
        geometry.cosine_polar_angle[first] + geometry.cosine_polar_angle[second]
    )
    coordinate_y_difference = (
        geometry.coordinate_y[second] - geometry.coordinate_y[first]
    )
    coordinate_x_difference = (
        geometry.coordinate_x[second] - geometry.coordinate_x[first]
    )
    phase_increment = wave_numbers[:, None, None, None, None] * (
        cosine_polar_angle_difference[None, :, :, None, None]
        * axial_distance_from_focus
        - (
            coordinate_y_difference[None, :, :, None, None]
            * corner_y[None, None, None, :, :]
            + coordinate_x_difference[None, :, :, None, None]
            * corner_x[None, None, None, :, :]
        )
        / focal_length
    )
    return torch.where(
        adjacent_support[None, :, :, None, None],
        phase_increment.abs(),
        torch.zeros_like(phase_increment),
    ).amax()


def _as_real(value: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    return value.to(
        dtype=reference.dtype,
        device=reference.device,
    )

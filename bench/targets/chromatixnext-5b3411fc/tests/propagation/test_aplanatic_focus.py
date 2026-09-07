from __future__ import annotations

import copy
from dataclasses import replace
import math

import pytest
import torch

from chromatix_next.errors import OpticalError
from chromatix_next.optics import (
    Assembly,
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PolarizationRepresentation,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    TabulatedMedium,
    Vacuum,
)
from chromatix_next.optics.combination import coherent_combination
from chromatix_next.optics.detection import intensity_detection
from chromatix_next.optics.propagation import AplanaticFocus, aplanatic_focus
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation

from ._aplanatic_reference import _direct_aplanatic_focus


def _coordinates(grid: SpatialGrid) -> tuple[torch.Tensor, torch.Tensor]:
    position_y = (
        torch.arange(grid.sample_counts[0], dtype=torch.float64)
        * grid.signed_spacing[0]
        + grid.first_sample_position[0]
    )
    position_x = (
        torch.arange(grid.sample_counts[1], dtype=torch.float64)
        * grid.signed_spacing[1]
        + grid.first_sample_position[1]
    )
    return position_y, position_x


def _airy_amplitude(argument: torch.Tensor) -> torch.Tensor:
    amplitude = torch.ones_like(argument)
    is_nonzero = argument != 0.0
    amplitude[is_nonzero] = (
        2.0
        * torch.special.bessel_j1(argument[is_nonzero])
        / argument[is_nonzero]
    )
    return amplitude


def _direct_reference_objective(
    envelope: torch.Tensor,
    *,
    grid: SpatialGrid,
    destination_grid: SpatialGrid,
    wavelength: float,
    input_path_length: float,
    focal_length: float,
    maximum_convergence_angle: float,
    axial_distance_from_focus: float,
    output_weights: torch.Tensor,
) -> torch.Tensor:
    pupil_y, pupil_x = _coordinates(grid)
    destination_y, destination_x = _coordinates(destination_grid)
    reference = _direct_aplanatic_focus(
        envelope,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        destination_y=destination_y,
        destination_x=destination_x,
        wavelengths=torch.tensor((wavelength,), dtype=torch.float64),
        refractive_indices=torch.tensor((1.0,), dtype=torch.float64),
        input_path_lengths=torch.tensor(
            (input_path_length,),
            dtype=torch.float64,
        ),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_convergence_angle,
        axial_distance_from_focus=axial_distance_from_focus,
    )
    return (
        reference.residual_envelope * output_weights
    ).sum().real


def _independent_phase_increments(
    *,
    pupil_grid: SpatialGrid,
    destination_grid: SpatialGrid,
    wavelengths: tuple[float, ...],
    refractive_indices: tuple[float, ...],
    focal_length: float,
    maximum_convergence_angle: float,
    axial_distance_from_focus: float,
) -> torch.Tensor:
    pupil_y, pupil_x = _coordinates(pupil_grid)
    destination_y, destination_x = _coordinates(destination_grid)
    coordinate_y, coordinate_x = torch.meshgrid(
        pupil_y,
        pupil_x,
        indexing="ij",
    )
    sine_squared = (
        coordinate_y.square() + coordinate_x.square()
    ) / focal_length**2
    support = (
        sine_squared
        <= math.sin(maximum_convergence_angle) ** 2
    )
    cosine_theta = torch.sqrt(1.0 - sine_squared)
    corners = tuple(
        (corner_y, corner_x)
        for corner_y in (destination_y[0], destination_y[-1])
        for corner_x in (destination_x[0], destination_x[-1])
    )
    increments = torch.zeros(
        (len(wavelengths), 2, len(corners)),
        dtype=torch.float64,
    )
    for spectral_index, (
        wavelength,
        refractive_index,
    ) in enumerate(
        zip(wavelengths, refractive_indices, strict=True),
    ):
        wave_number = (
            2.0 * math.pi * refractive_index / wavelength
        )
        for axis_index, axis in enumerate((0, 1)):
            first_slice = [slice(None), slice(None)]
            second_slice = [slice(None), slice(None)]
            first_slice[axis] = slice(None, -1)
            second_slice[axis] = slice(1, None)
            first = tuple(first_slice)
            second = tuple(second_slice)
            admitted = support[first] & support[second]
            delta_cosine = (
                cosine_theta[second] - cosine_theta[first]
            )
            delta_y = coordinate_y[second] - coordinate_y[first]
            delta_x = coordinate_x[second] - coordinate_x[first]
            for corner_index, (
                corner_y,
                corner_x,
            ) in enumerate(corners):
                phase = wave_number * (
                    delta_cosine * axial_distance_from_focus
                    - (
                        delta_y * corner_y
                        + delta_x * corner_x
                    )
                    / focal_length
                )
                increments[
                    spectral_index,
                    axis_index,
                    corner_index,
                ] = torch.where(
                    admitted,
                    phase.abs(),
                    torch.zeros_like(phase),
                ).amax()
    return increments


def _aplanatic_field(
    *,
    grid: SpatialGrid,
    wavelengths: tuple[float, ...],
    refractive_indices: tuple[float, ...],
) -> OpticalField:
    medium = (
        Vacuum()
        if len(wavelengths) == 1
        and refractive_indices == (1.0,)
        else TabulatedMedium(
            wavelengths=wavelengths,
            refractive_indices=refractive_indices,
        )
    )
    return OpticalField(
        envelope=torch.ones(
            (
                len(wavelengths),
                2,
                *grid.sample_counts,
            ),
            dtype=torch.complex128,
        ),
        grid=grid,
        spectrum=Spectrum(
            wavelengths=wavelengths,
            weights=tuple(1.0 for _ in wavelengths),
        ),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=medium,
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=tuple(0.0 for _ in wavelengths),
        ),
    )


def test_function_and_component_match_independent_rectangular_reference() -> None:
    """
    验证配对聚焦入口在非方网格上匹配独立固体角参考
    """

    pupil_grid = SpatialGrid.centered(
        sample_counts=(17, 21),
        sample_spacing=(0.45e-6, 0.37e-6),
    )
    destination_grid = SpatialGrid(
        sample_counts=(3, 5),
        sample_spacing=(0.21e-6, 0.18e-6),
        first_sample_position=(-0.17e-6, -0.31e-6),
    )
    generator = torch.Generator().manual_seed(42)
    envelope = torch.complex(
        torch.randn(
            (1, 2, 17, 21),
            generator=generator,
            dtype=torch.float64,
        ),
        torch.randn(
            (1, 2, 17, 21),
            generator=generator,
            dtype=torch.float64,
        ),
    )
    field = OpticalField(
        envelope=envelope,
        grid=pupil_grid,
        spectrum=Spectrum.monochromatic(0.532e-6),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.2e-6,)),
    )
    focal_length = 8.0e-6
    maximum_angle = 0.4
    axial_distance = 0.23e-6

    direct = aplanatic_focus(
        field,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=axial_distance,
        destination_grid=destination_grid,
    )
    component = AplanaticFocus(
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=axial_distance,
        destination_grid=destination_grid,
    )(field)

    pupil_y, pupil_x = _coordinates(pupil_grid)
    destination_y, destination_x = _coordinates(destination_grid)
    reference = _direct_aplanatic_focus(
        envelope,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        destination_y=destination_y,
        destination_x=destination_x,
        wavelengths=torch.tensor((0.532e-6,), dtype=torch.float64),
        refractive_indices=torch.tensor((1.0,), dtype=torch.float64),
        input_path_lengths=torch.tensor((0.2e-6,), dtype=torch.float64),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=axial_distance,
    )
    scale = float(reference.residual_envelope.abs().max())
    tolerance = (
        64.0
        * torch.finfo(torch.float64).eps
        * pupil_y.numel()
        * pupil_x.numel()
        * max(scale, 1.0)
    )
    assert direct.polarization_representation is PolarizationRepresentation.FULL
    assert direct.grid.is_physically_equivalent_to(destination_grid)
    assert torch.allclose(
        direct.envelope,
        reference.residual_envelope,
        rtol=0.0,
        atol=tolerance,
    ), (direct.envelope - reference.residual_envelope).abs().max()
    assert torch.equal(component.envelope, direct.envelope)
    assert component.path_reference == direct.path_reference
    assert direct.path_reference.lengths == (
        0.2e-6 + focal_length + axial_distance,
    )


def test_aplanatic_discrete_sampling_residual_contracts_with_pupil_refinement() -> None:
    """
    离散采样证据：完整采样瞳孔细化时，公共消球差动作趋近独立角度求积
    高分辨率参照仍是同一理想 Richards-Wolf 方程，不声称材料物镜收敛。
    """

    focal_length = 10.0e-6
    maximum_angle = 0.6
    axial_distance = 0.3e-6
    pupil_radius = focal_length * math.sin(maximum_angle)
    destination_grid = SpatialGrid(
        sample_counts=(5, 7),
        sample_spacing=(0.21e-6, 0.18e-6),
        first_sample_position=(-0.42e-6, -0.54e-6),
    )
    destination_y, destination_x = _coordinates(destination_grid)
    wavelength_tensor = torch.tensor((0.532e-6,), dtype=torch.float64)
    refractive_index_tensor = torch.tensor((1.0,), dtype=torch.float64)
    path_length_tensor = torch.tensor((0.0,), dtype=torch.float64)

    def _sampled_action_and_reference(
        sample_count: int,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        span = 2.2 * pupil_radius
        spacing = span / (sample_count - 1)
        pupil_grid = SpatialGrid.centered(
            sample_counts=(sample_count, sample_count),
            sample_spacing=(spacing, spacing),
        )
        pupil_y, pupil_x = _coordinates(pupil_grid)
        radius_squared = pupil_y[:, None].square() + pupil_x[None, :].square()
        taper = torch.clamp(
            1.0 - radius_squared / pupil_radius**2,
            min=0.0,
        ).square()
        envelope = torch.stack(
            (taper / math.sqrt(2.0), 1j * taper / math.sqrt(2.0)),
        ).unsqueeze(0)
        field = OpticalField(
            envelope=envelope,
            grid=pupil_grid,
            spectrum=Spectrum.monochromatic(0.532e-6),
            polarization_representation=PolarizationRepresentation.TRANSVERSE,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        actual = aplanatic_focus(
            field,
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=axial_distance,
            destination_grid=destination_grid,
        ).envelope
        reference = _direct_aplanatic_focus(
            envelope,
            pupil_y=pupil_y,
            pupil_x=pupil_x,
            destination_y=destination_y,
            destination_x=destination_x,
            wavelengths=wavelength_tensor,
            refractive_indices=refractive_index_tensor,
            input_path_lengths=path_length_tensor,
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=axial_distance,
        )
        return actual, reference.residual_envelope

    _high_resolution_action, high_resolution_reference = (
        _sampled_action_and_reference(129)
    )
    del _high_resolution_action
    residuals: list[float] = []
    for sample_count in (17, 33, 65):
        actual, _reference = _sampled_action_and_reference(sample_count)
        alignment = (actual.conj() * high_resolution_reference).sum() / (
            actual.abs().square().sum()
        )
        residuals.append(
            float(
                (alignment * actual - high_resolution_reference).abs().max()
            )
            / float(high_resolution_reference.abs().max())
        )

    assert residuals[1] < residuals[0]
    assert residuals[2] < residuals[1]


def test_batched_dispersive_field_matches_shifted_scaled_reference() -> None:
    """
    批量多光谱色散场在平移缩放目标网格上匹配独立积分
    """

    pupil_grid = SpatialGrid.centered(
        sample_counts=(13, 15),
        sample_spacing=(0.5e-6, 0.4e-6),
    )
    destination_grid = SpatialGrid(
        sample_counts=(4, 6),
        sample_spacing=(0.23e-6, 0.17e-6),
        first_sample_position=(-0.29e-6, -0.41e-6),
    )
    generator = torch.Generator().manual_seed(42)
    envelope = torch.complex(
        torch.randn(
            (2, 2, 2, 13, 15),
            generator=generator,
            dtype=torch.float64,
        ),
        torch.randn(
            (2, 2, 2, 13, 15),
            generator=generator,
            dtype=torch.float64,
        ),
    )
    wavelengths = (0.50e-6, 0.62e-6)
    indices = (1.12, 1.19)
    field = OpticalField(
        envelope=envelope,
        grid=pupil_grid,
        spectrum=Spectrum(
            wavelengths=wavelengths,
            weights=(0.4, 0.6),
        ),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=TabulatedMedium(
            wavelengths=wavelengths,
            refractive_indices=indices,
        ),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.1e-6, 0.3e-6),
        ),
    )
    focal_length = 10.0e-6
    maximum_angle = 0.25
    axial_distance = -0.15e-6

    output = aplanatic_focus(
        field,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=axial_distance,
        destination_grid=destination_grid,
    )
    pupil_y, pupil_x = _coordinates(pupil_grid)
    destination_y, destination_x = _coordinates(destination_grid)
    reference = _direct_aplanatic_focus(
        envelope,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        destination_y=destination_y,
        destination_x=destination_x,
        wavelengths=torch.tensor(wavelengths, dtype=torch.float64),
        refractive_indices=torch.tensor(indices, dtype=torch.float64),
        input_path_lengths=torch.tensor(
            (0.1e-6, 0.3e-6),
            dtype=torch.float64,
        ),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=axial_distance,
    )

    assert output.envelope.shape == (2, 2, 3, 4, 6)
    assert torch.allclose(
        output.envelope,
        reference.residual_envelope,
        rtol=2.0e-12,
        atol=2.0e-12,
    )


def test_low_numerical_aperture_circular_pupil_reaches_airy_limit() -> None:
    """
    低数值孔径圆形入瞳的复振幅与强度收敛到独立 Airy 极限
    """

    focal_length = 1.0e-3
    maximum_angle = 0.04
    wavelength = 0.55e-6
    sample_count = 201
    pupil_radius = focal_length * math.sin(maximum_angle)
    sample_spacing = 2.0 * pupil_radius / (sample_count - 3)
    pupil_grid = SpatialGrid.centered(
        sample_counts=(sample_count, sample_count),
        sample_spacing=(sample_spacing, sample_spacing),
    )
    airy_arguments = torch.arange(6, dtype=torch.float64)
    destination_spacing = 1.0 / (
        2.0
        * math.pi
        / wavelength
        * math.sin(maximum_angle)
    )
    destination_grid = SpatialGrid(
        sample_counts=(1, airy_arguments.numel()),
        sample_spacing=(destination_spacing, destination_spacing),
        first_sample_position=(0.0, 0.0),
    )
    envelope = torch.zeros(
        (1, 2, sample_count, sample_count),
        dtype=torch.complex128,
    )
    envelope[:, 0, :, :] = 1.0
    field = OpticalField(
        envelope=envelope,
        grid=pupil_grid,
        spectrum=Spectrum.monochromatic(wavelength),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )

    output = AplanaticFocus(
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=0.0,
        destination_grid=destination_grid,
    )(field)

    normalized_amplitude = (
        output.envelope[0, 0, 0, :]
        / output.envelope[0, 0, 0, 0]
    )
    airy_amplitude = _airy_amplitude(airy_arguments)
    assert torch.allclose(
        normalized_amplitude,
        airy_amplitude.to(dtype=torch.complex128),
        rtol=0.0,
        atol=7.0e-4,
    )
    assert torch.allclose(
        normalized_amplitude.abs().square(),
        airy_amplitude.square(),
        rtol=0.0,
        atol=6.0e-4,
    )
    fine_amplitude_error = (
        normalized_amplitude - airy_amplitude
    ).abs().amax()
    fine_intensity_error = (
        normalized_amplitude.abs().square()
        - airy_amplitude.square()
    ).abs().amax()

    coarse_count = 101
    coarse_spacing = 2.0 * pupil_radius / (coarse_count - 3)
    coarse_grid = SpatialGrid.centered(
        sample_counts=(coarse_count, coarse_count),
        sample_spacing=(coarse_spacing, coarse_spacing),
    )
    coarse_envelope = torch.zeros(
        (1, 2, coarse_count, coarse_count),
        dtype=torch.complex128,
    )
    coarse_envelope[:, 0, :, :] = 1.0
    coarse_field = replace(
        field,
        envelope=coarse_envelope,
        grid=coarse_grid,
    )
    coarse_output = AplanaticFocus(
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=0.0,
        destination_grid=destination_grid,
    )(coarse_field)
    coarse_amplitude = (
        coarse_output.envelope[0, 0, 0, :]
        / coarse_output.envelope[0, 0, 0, 0]
    )
    coarse_amplitude_error = (
        coarse_amplitude - airy_amplitude
    ).abs().amax()
    coarse_intensity_error = (
        coarse_amplitude.abs().square()
        - airy_amplitude.square()
    ).abs().amax()
    assert fine_amplitude_error < 0.4 * coarse_amplitude_error
    assert fine_intensity_error < 0.7 * coarse_intensity_error


def test_envelope_and_axial_distance_match_independent_derivatives() -> None:
    """
    包络与离焦距离的梯度匹配独立固体角参考的中心有限差分
    """

    grid = SpatialGrid.centered(
        sample_counts=(9, 11),
        sample_spacing=(0.6e-6, 0.5e-6),
    )
    destination = SpatialGrid.centered(
        sample_counts=(2, 3),
        sample_spacing=(0.2e-6, 0.18e-6),
    )
    generator = torch.Generator().manual_seed(42)
    envelope = torch.complex(
        torch.randn(
            (1, 2, 9, 11),
            generator=generator,
            dtype=torch.float64,
        ),
        torch.randn(
            (1, 2, 9, 11),
            generator=generator,
            dtype=torch.float64,
        ),
    )
    envelope.requires_grad_(True)
    distance_value = 0.17e-6
    distance = torch.tensor(
        distance_value,
        dtype=torch.float64,
        requires_grad=True,
    )
    output_weights = torch.complex(
        torch.randn(
            (1, 3, 2, 3),
            generator=generator,
            dtype=torch.float64,
        ),
        torch.randn(
            (1, 3, 2, 3),
            generator=generator,
            dtype=torch.float64,
        ),
    )
    input_path_length = 0.31e-6
    wavelength = 0.55e-6
    focal_length = 9.0e-6
    maximum_angle = 0.28
    field = OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=Spectrum.monochromatic(wavelength),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(input_path_length,),
        ),
    )

    output = aplanatic_focus(
        field,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=distance,
        destination_grid=destination,
    )
    objective = (output.envelope * output_weights).sum().real
    envelope_gradient, distance_gradient = torch.autograd.grad(
        objective,
        (envelope, distance),
    )

    envelope_step = 1.0e-6
    selected_index = (0, 1, 5, 7)
    finite_differences: list[torch.Tensor] = []
    for perturbation in (1.0, 1.0j):
        positive = envelope.detach().clone()
        negative = envelope.detach().clone()
        positive[selected_index] += envelope_step * perturbation
        negative[selected_index] -= envelope_step * perturbation
        positive_objective = _direct_reference_objective(
            positive,
            grid=grid,
            destination_grid=destination,
            wavelength=wavelength,
            input_path_length=input_path_length,
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=distance_value,
            output_weights=output_weights,
        )
        negative_objective = _direct_reference_objective(
            negative,
            grid=grid,
            destination_grid=destination,
            wavelength=wavelength,
            input_path_length=input_path_length,
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=distance_value,
            output_weights=output_weights,
        )
        finite_differences.append(
            (positive_objective - negative_objective)
            / (2.0 * envelope_step),
        )
    assert torch.allclose(
        envelope_gradient[selected_index].real,
        finite_differences[0],
        rtol=2.0e-8,
        atol=2.0e-10,
    )
    assert torch.allclose(
        envelope_gradient[selected_index].imag,
        finite_differences[1],
        rtol=2.0e-8,
        atol=2.0e-10,
    )

    distance_step = 1.0e-10
    positive_distance = _direct_reference_objective(
        envelope.detach(),
        grid=grid,
        destination_grid=destination,
        wavelength=wavelength,
        input_path_length=input_path_length,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=distance_value + distance_step,
        output_weights=output_weights,
    )
    negative_distance = _direct_reference_objective(
        envelope.detach(),
        grid=grid,
        destination_grid=destination,
        wavelength=wavelength,
        input_path_length=input_path_length,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=distance_value - distance_step,
        output_weights=output_weights,
    )
    distance_finite_difference = (
        positive_distance - negative_distance
    ) / (2.0 * distance_step)
    assert torch.allclose(
        distance_gradient,
        distance_finite_difference,
        rtol=2.0e-7,
        atol=2.0e-5,
    )

    output_path = output.path_reference.lengths[0]
    assert isinstance(output_path, torch.Tensor)
    assert output_path.dtype is torch.float64
    assert output_path.requires_grad
    path_gradient = torch.autograd.grad(
        output_path,
        distance,
    )[0]
    assert torch.equal(
        path_gradient,
        torch.ones_like(distance),
    )


def test_coherent_recombination_keeps_axial_carrier_gradient() -> None:
    """
    同目标聚焦双臂的最终光强保留离焦调整的完整载波梯度
    """

    grid = SpatialGrid.centered(
        sample_counts=(9, 11),
        sample_spacing=(0.6e-6, 0.5e-6),
    )
    destination = SpatialGrid.centered(
        sample_counts=(2, 3),
        sample_spacing=(0.2e-6, 0.18e-6),
    )
    field = _aplanatic_field(
        grid=grid,
        wavelengths=(0.55e-6,),
        refractive_indices=(1.0,),
    )
    focal_length = 9.0e-6
    maximum_angle = 0.28

    def _combined_intensity(
        axial_adjustment: float | torch.Tensor,
    ) -> torch.Tensor:
        reference_arm = aplanatic_focus(
            field,
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=0.0,
            destination_grid=destination,
        )
        adjusted_arm = aplanatic_focus(
            field,
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=axial_adjustment,
            destination_grid=destination,
        )
        return intensity_detection(
            coherent_combination(
                reference_arm,
                adjusted_arm,
            ),
        ).values.sum()

    adjustment_value = 0.17e-6
    adjustment = torch.tensor(
        adjustment_value,
        dtype=torch.float64,
        requires_grad=True,
    )
    objective = _combined_intensity(adjustment)
    gradient = torch.autograd.grad(
        objective,
        adjustment,
    )[0]
    step = 1.0e-11
    finite_difference = (
        _combined_intensity(adjustment_value + step)
        - _combined_intensity(adjustment_value - step)
    ) / (2.0 * step)

    assert gradient.abs() > 1.0e6
    assert torch.allclose(
        gradient,
        finite_difference,
        rtol=1.0e-7,
        atol=1.0e-3,
    )


def test_low_angle_single_ray_keeps_stable_residual_phase() -> None:
    """
    低会聚角单光线保留稳定的轴向残差相位
    """

    focal_length = 1.0
    sine_theta = 2.0e-4
    axial_distance = 1.0
    wavelength = 1.0e-6
    spacing = focal_length * sine_theta
    grid = SpatialGrid.centered(
        sample_counts=(5, 5),
        sample_spacing=(spacing, spacing),
    )
    envelope = torch.zeros((1, 2, 5, 5), dtype=torch.complex128)
    envelope[0, 1, 2, 3] = 1.0
    field = OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=Spectrum.monochromatic(wavelength),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )
    destination = SpatialGrid.centered(
        sample_counts=(1, 1),
        sample_spacing=(1.0e-6, 1.0e-6),
    )

    output = aplanatic_focus(
        field,
        focal_length=focal_length,
        maximum_convergence_angle=3.0e-4,
        axial_distance_from_focus=axial_distance,
        destination_grid=destination,
    )

    sine_squared = torch.tensor(sine_theta**2, dtype=torch.float64)
    cosine_theta = torch.sqrt(1.0 - sine_squared)
    cosine_theta_minus_one = (
        -sine_squared / (1.0 + cosine_theta)
    )
    wave_number = torch.tensor(
        2.0 * torch.pi / wavelength,
        dtype=torch.float64,
    )
    cell_area = torch.tensor(spacing**2, dtype=torch.float64)
    expected_y = (
        torch.sqrt(cosine_theta)
        * (
            -1j
            * wave_number
            * cell_area
            / (2.0 * torch.pi * focal_length * cosine_theta)
        )
        * torch.exp(
            1j
            * wave_number
            * cosine_theta_minus_one
            * axial_distance,
        )
    )

    assert torch.allclose(
        output.envelope[0, 1, 0, 0],
        expected_y,
        rtol=2.0e-10,
        atol=2.0e-12,
    )


@pytest.mark.parametrize(
    ("change", "identity"),
    (
        (
            {
                "focal_length": torch.tensor(
                    8.0e-6,
                    dtype=torch.float64,
                    requires_grad=True,
                ),
            },
            "aplanatic_focus_focal_length_requires_grad",
        ),
        (
            {
                "maximum_convergence_angle": torch.tensor(
                    0.3,
                    dtype=torch.float64,
                    requires_grad=True,
                ),
            },
            "aplanatic_focus_maximum_convergence_angle_requires_grad",
        ),
        (
            {"axial_distance_from_focus": -8.0e-6},
            "aplanatic_focus_plane_not_beyond_objective",
        ),
    ),
)
def test_invalid_geometry_fails_with_stable_identity(
    change: dict[str, object],
    identity: str,
) -> None:
    """
    固定几何与物镜之后平面以稳定标识提前拒绝
    """

    grid = SpatialGrid.centered(
        sample_counts=(11, 11),
        sample_spacing=(0.6e-6, 0.6e-6),
    )
    field = OpticalField(
        envelope=torch.ones((1, 2, 11, 11), dtype=torch.complex128),
        grid=grid,
        spectrum=Spectrum.monochromatic(0.55e-6),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )
    arguments: dict[str, object] = {
        "focal_length": 8.0e-6,
        "maximum_convergence_angle": 0.3,
        "axial_distance_from_focus": 0.0,
        "destination_grid": SpatialGrid.centered(
            sample_counts=(3, 3),
            sample_spacing=(0.2e-6, 0.2e-6),
        ),
    }
    arguments.update(change)

    with pytest.raises(OpticalError) as caught:
        aplanatic_focus(field, **arguments)  # type: ignore[arg-type]

    assert caught.value.identity == identity


@pytest.mark.parametrize(
    ("parameter_name", "identity"),
    (
        ("focal_length", "aplanatic_focus_focal_length_invalid"),
        (
            "maximum_convergence_angle",
            "aplanatic_focus_maximum_convergence_angle_invalid",
        ),
        (
            "axial_distance_from_focus",
            "aplanatic_focus_axial_distance_invalid",
        ),
    ),
)
def test_aplanatic_focus_rejects_float32_geometry_parameter(
    parameter_name: str,
    identity: str,
) -> None:
    """
    AplanaticFocus 的三个公开几何标量均拒绝 float32
    """

    arguments: dict[str, object] = {
        "focal_length": 8.0e-6,
        "maximum_convergence_angle": 0.4,
        "axial_distance_from_focus": 0.23e-6,
        "destination_grid": SpatialGrid.centered(
            sample_counts=(3, 3),
            sample_spacing=(0.2e-6, 0.2e-6),
        ),
    }
    arguments[parameter_name] = torch.nn.Parameter(
        torch.tensor(1.0e-6, dtype=torch.float32),
    )
    with pytest.raises(OpticalError) as caught:
        AplanaticFocus(**arguments)  # type: ignore[arg-type]
    assert caught.value.identity == identity


def test_aplanatic_axial_distance_parameter_keeps_optimizer_identity() -> None:
    """
    合法离焦距离 Parameter 保持同一注册对象并对优化器可见
    """

    axial_distance = torch.nn.Parameter(
        torch.tensor(0.23e-6, dtype=torch.float64),
    )
    focus = AplanaticFocus(
        focal_length=8.0e-6,
        maximum_convergence_angle=0.4,
        axial_distance_from_focus=axial_distance,
        destination_grid=SpatialGrid.centered(
            sample_counts=(3, 3),
            sample_spacing=(0.2e-6, 0.2e-6),
        ),
    )

    assert focus.axial_distance_from_focus is axial_distance
    assert (
        dict(focus.named_parameters())["axial_distance_from_focus"]
        is axial_distance
    )


@pytest.mark.parametrize("spectral_index", (0, 1))
@pytest.mark.parametrize("axis", (0, 1))
@pytest.mark.parametrize("endpoint", (0, 1))
def test_lateral_applicability_checks_each_spectrum_axis_and_window_end(
    spectral_index: int,
    axis: int,
    endpoint: int,
) -> None:
    """
    每个谱段、入瞳轴和目标窗端点都能独立越过 π 适用性边界
    """

    focal_length = 10.0e-6
    maximum_angle = 0.2
    wavelengths = (0.50e-6, 0.60e-6)
    refractive_indices = (
        (2.0, 1.0)
        if spectral_index == 0
        else (1.0, 2.0)
    )
    pupil_spacing = (
        (0.8e-6, 0.2e-6)
        if axis == 0
        else (0.2e-6, 0.8e-6)
    )
    pupil_radius = focal_length * math.sin(maximum_angle)
    sample_counts = tuple(
        2
        * math.ceil(
            (pupil_radius + spacing / 2.0) / spacing,
        )
        + 1
        for spacing in pupil_spacing
    )
    pupil_grid = SpatialGrid.centered(
        sample_counts=(sample_counts[0], sample_counts[1]),
        sample_spacing=(
            torch.tensor(pupil_spacing[0], dtype=torch.float64),
            torch.tensor(pupil_spacing[1], dtype=torch.float64),
        ),
    )
    outer_position = -10.0e-6 if endpoint == 0 else 8.0e-6
    first_position = (
        (outer_position, 0.0)
        if axis == 0
        else (0.0, outer_position)
    )
    base_spacing = (
        (2.0e-6, 1.0e-6)
        if axis == 0
        else (1.0e-6, 2.0e-6)
    )
    base_destination = SpatialGrid(
        sample_counts=(2, 2),
        sample_spacing=(
            torch.tensor(base_spacing[0], dtype=torch.float64),
            torch.tensor(base_spacing[1], dtype=torch.float64),
        ),
        first_sample_position=(
            torch.tensor(first_position[0], dtype=torch.float64),
            torch.tensor(first_position[1], dtype=torch.float64),
        ),
    )
    increments = _independent_phase_increments(
        pupil_grid=pupil_grid,
        destination_grid=base_destination,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=0.0,
    )
    corner_index = (
        2 * endpoint
        if axis == 0
        else endpoint
    )
    target_increment = increments[
        spectral_index,
        axis,
        corner_index,
    ]
    assert torch.equal(target_increment, increments.amax())
    field = _aplanatic_field(
        grid=pupil_grid,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
    )

    for boundary_factor, should_reject in (
        (0.98, False),
        (1.02, True),
    ):
        scale = (
            boundary_factor
            * math.pi
            / float(target_increment)
        )
        destination = SpatialGrid(
            sample_counts=(2, 2),
            sample_spacing=(
                torch.tensor(
                    scale * base_spacing[0],
                    dtype=torch.float64,
                ),
                torch.tensor(
                    scale * base_spacing[1],
                    dtype=torch.float64,
                ),
            ),
            first_sample_position=(
                torch.tensor(
                    scale * first_position[0],
                    dtype=torch.float64,
                ),
                torch.tensor(
                    scale * first_position[1],
                    dtype=torch.float64,
                ),
            ),
        )
        scaled_increment = _independent_phase_increments(
            pupil_grid=pupil_grid,
            destination_grid=destination,
            wavelengths=wavelengths,
            refractive_indices=refractive_indices,
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=0.0,
        ).amax()
        assert bool(scaled_increment > math.pi) is should_reject
        if should_reject:
            with pytest.raises(OpticalError) as caught:
                aplanatic_focus(
                    field,
                    focal_length=focal_length,
                    maximum_convergence_angle=maximum_angle,
                    axial_distance_from_focus=0.0,
                    destination_grid=destination,
                )
            assert (
                caught.value.identity
                == "aplanatic_focus_phase_increment_aliased"
            )
        else:
            output = aplanatic_focus(
                field,
                focal_length=focal_length,
                maximum_convergence_angle=maximum_angle,
                axial_distance_from_focus=0.0,
                destination_grid=destination,
            )
            assert output.grid.is_physically_equivalent_to(destination)


def test_axial_applicability_crosses_pi_on_both_sides() -> None:
    """
    轴向相位增量在 π 两侧分别通过和拒绝，不能被横向项代替
    """

    focal_length = 10.0e-6
    maximum_angle = 0.2
    wavelength = 0.55e-6
    pupil_grid = SpatialGrid.centered(
        sample_counts=(11, 11),
        sample_spacing=(
            torch.tensor(0.45e-6, dtype=torch.float64),
            torch.tensor(0.45e-6, dtype=torch.float64),
        ),
    )
    destination = SpatialGrid.centered(
        sample_counts=(2, 2),
        sample_spacing=(
            torch.tensor(1.0e-15, dtype=torch.float64),
            torch.tensor(1.0e-15, dtype=torch.float64),
        ),
    )
    unit_distance_increment = _independent_phase_increments(
        pupil_grid=pupil_grid,
        destination_grid=destination,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=1.0,
    ).amax()
    field = _aplanatic_field(
        grid=pupil_grid,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
    )

    for boundary_factor, should_reject in (
        (0.98, False),
        (1.02, True),
    ):
        distance = (
            boundary_factor
            * math.pi
            / float(unit_distance_increment)
        )
        increment = _independent_phase_increments(
            pupil_grid=pupil_grid,
            destination_grid=destination,
            wavelengths=(wavelength,),
            refractive_indices=(1.0,),
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=distance,
        ).amax()
        assert bool(increment > math.pi) is should_reject
        if should_reject:
            with pytest.raises(OpticalError) as caught:
                aplanatic_focus(
                    field,
                    focal_length=focal_length,
                    maximum_convergence_angle=maximum_angle,
                    axial_distance_from_focus=distance,
                    destination_grid=destination,
                )
            assert (
                caught.value.identity
                == "aplanatic_focus_phase_increment_aliased"
            )
        else:
            output = aplanatic_focus(
                field,
                focal_length=focal_length,
                maximum_convergence_angle=maximum_angle,
                axial_distance_from_focus=distance,
                destination_grid=destination,
            )
            assert output.grid.is_physically_equivalent_to(destination)


def test_signed_lateral_and_axial_phase_reinforce_across_pi() -> None:
    """
    同号横向与轴向相位必须先带符号相加再跨越 π 边界
    """

    focal_length = 10.0e-6
    maximum_angle = 0.2
    wavelength = 0.55e-6
    pupil_grid = SpatialGrid.centered(
        sample_counts=(11, 11),
        sample_spacing=(
            torch.tensor(0.45e-6, dtype=torch.float64),
            torch.tensor(0.45e-6, dtype=torch.float64),
        ),
    )
    base_destination = SpatialGrid(
        sample_counts=(2, 2),
        sample_spacing=(
            torch.tensor(0.1e-6, dtype=torch.float64),
            torch.tensor(0.1e-6, dtype=torch.float64),
        ),
        first_sample_position=(
            torch.tensor(8.0e-6, dtype=torch.float64),
            torch.tensor(8.0e-6, dtype=torch.float64),
        ),
    )
    zero_destination = SpatialGrid(
        sample_counts=(1, 1),
        sample_spacing=(
            torch.tensor(1.0e-15, dtype=torch.float64),
            torch.tensor(1.0e-15, dtype=torch.float64),
        ),
        first_sample_position=(
            torch.tensor(0.0, dtype=torch.float64),
            torch.tensor(0.0, dtype=torch.float64),
        ),
    )
    unit_axial_increment = _independent_phase_increments(
        pupil_grid=pupil_grid,
        destination_grid=zero_destination,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=1.0,
    ).amax()
    unit_lateral_increment = _independent_phase_increments(
        pupil_grid=pupil_grid,
        destination_grid=base_destination,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=0.0,
    ).amax()
    field = _aplanatic_field(
        grid=pupil_grid,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
    )

    for contribution_factor, should_reject in (
        (0.49, False),
        (0.51, True),
    ):
        contribution = contribution_factor * math.pi
        distance = contribution / float(unit_axial_increment)
        lateral_scale = contribution / float(
            unit_lateral_increment,
        )
        destination = SpatialGrid(
            sample_counts=(2, 2),
            sample_spacing=(
                torch.tensor(
                    lateral_scale * 0.1e-6,
                    dtype=torch.float64,
                ),
                torch.tensor(
                    lateral_scale * 0.1e-6,
                    dtype=torch.float64,
                ),
            ),
            first_sample_position=(
                torch.tensor(
                    lateral_scale * 8.0e-6,
                    dtype=torch.float64,
                ),
                torch.tensor(
                    lateral_scale * 8.0e-6,
                    dtype=torch.float64,
                ),
            ),
        )
        axial_increment = _independent_phase_increments(
            pupil_grid=pupil_grid,
            destination_grid=zero_destination,
            wavelengths=(wavelength,),
            refractive_indices=(1.0,),
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=distance,
        ).amax()
        lateral_increment = _independent_phase_increments(
            pupil_grid=pupil_grid,
            destination_grid=destination,
            wavelengths=(wavelength,),
            refractive_indices=(1.0,),
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=0.0,
        ).amax()
        combined_increment = _independent_phase_increments(
            pupil_grid=pupil_grid,
            destination_grid=destination,
            wavelengths=(wavelength,),
            refractive_indices=(1.0,),
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=distance,
        ).amax()
        assert torch.allclose(
            axial_increment,
            torch.tensor(contribution, dtype=torch.float64),
            rtol=2.0e-14,
            atol=2.0e-14,
        )
        assert torch.allclose(
            lateral_increment,
            torch.tensor(contribution, dtype=torch.float64),
            rtol=2.0e-14,
            atol=2.0e-14,
        )
        assert torch.allclose(
            combined_increment,
            torch.tensor(
                2.0 * contribution,
                dtype=torch.float64,
            ),
            rtol=2.0e-14,
            atol=2.0e-14,
        )
        if should_reject:
            with pytest.raises(OpticalError) as caught:
                aplanatic_focus(
                    field,
                    focal_length=focal_length,
                    maximum_convergence_angle=maximum_angle,
                    axial_distance_from_focus=distance,
                    destination_grid=destination,
                )
            assert (
                caught.value.identity
                == "aplanatic_focus_phase_increment_aliased"
            )
        else:
            output = aplanatic_focus(
                field,
                focal_length=focal_length,
                maximum_convergence_angle=maximum_angle,
                axial_distance_from_focus=distance,
                destination_grid=destination,
            )
            assert output.grid.is_physically_equivalent_to(destination)


def test_signed_lateral_and_axial_phase_can_cancel_below_pi() -> None:
    """
    反号横向与轴向相位允许在各自越界时相消到 π 以内
    """

    focal_length = 1.0e-3
    maximum_angle = math.asin(0.095)
    wavelength = 0.55e-6
    pupil_grid = SpatialGrid(
        sample_counts=(3, 3),
        sample_spacing=(
            torch.tensor(0.1e-3, dtype=torch.float64),
            torch.tensor(0.1e-3, dtype=torch.float64),
        ),
        first_sample_position=(
            torch.tensor(-0.045e-3, dtype=torch.float64),
            torch.tensor(-0.045e-3, dtype=torch.float64),
        ),
    )
    base_destination = SpatialGrid(
        sample_counts=(2, 2),
        sample_spacing=(
            torch.tensor(0.005e-3, dtype=torch.float64),
            torch.tensor(0.005e-3, dtype=torch.float64),
        ),
        first_sample_position=(
            torch.tensor(0.8e-3, dtype=torch.float64),
            torch.tensor(0.8e-3, dtype=torch.float64),
        ),
    )
    zero_destination = SpatialGrid(
        sample_counts=(1, 1),
        sample_spacing=(
            torch.tensor(1.0e-15, dtype=torch.float64),
            torch.tensor(1.0e-15, dtype=torch.float64),
        ),
        first_sample_position=(
            torch.tensor(0.0, dtype=torch.float64),
            torch.tensor(0.0, dtype=torch.float64),
        ),
    )
    unit_axial_increment = _independent_phase_increments(
        pupil_grid=pupil_grid,
        destination_grid=zero_destination,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=1.0,
    ).amax()
    unit_lateral_increment = _independent_phase_increments(
        pupil_grid=pupil_grid,
        destination_grid=base_destination,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=0.0,
    ).amax()
    contribution = 1.2 * math.pi
    distance = -contribution / float(unit_axial_increment)
    lateral_scale = contribution / float(unit_lateral_increment)
    destination = SpatialGrid(
        sample_counts=(2, 2),
        sample_spacing=(
            torch.tensor(
                lateral_scale * 0.005e-3,
                dtype=torch.float64,
            ),
            torch.tensor(
                lateral_scale * 0.005e-3,
                dtype=torch.float64,
            ),
        ),
        first_sample_position=(
            torch.tensor(
                lateral_scale * 0.8e-3,
                dtype=torch.float64,
            ),
            torch.tensor(
                lateral_scale * 0.8e-3,
                dtype=torch.float64,
            ),
        ),
    )
    axial_increment = _independent_phase_increments(
        pupil_grid=pupil_grid,
        destination_grid=zero_destination,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=distance,
    ).amax()
    lateral_increment = _independent_phase_increments(
        pupil_grid=pupil_grid,
        destination_grid=destination,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=0.0,
    ).amax()
    combined_increment = _independent_phase_increments(
        pupil_grid=pupil_grid,
        destination_grid=destination,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=distance,
    ).amax()
    assert axial_increment > math.pi
    assert lateral_increment > math.pi
    assert combined_increment < 0.01 * math.pi
    assert focal_length + distance > 0.0

    field = _aplanatic_field(
        grid=pupil_grid,
        wavelengths=(wavelength,),
        refractive_indices=(1.0,),
    )
    output = aplanatic_focus(
        field,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=distance,
        destination_grid=destination,
    )

    assert output.grid.is_physically_equivalent_to(destination)


def test_incomplete_pupil_and_aliased_destination_fail_before_focus() -> None:
    """
    不完整入瞳与过大目标窗口在进入 CZT 前分别拒绝
    """

    envelope = torch.ones((1, 2, 9, 9), dtype=torch.complex128)
    small_grid = SpatialGrid.centered(
        sample_counts=(9, 9),
        sample_spacing=(0.2e-6, 0.2e-6),
    )
    field = OpticalField(
        envelope=envelope,
        grid=small_grid,
        spectrum=Spectrum.monochromatic(0.5e-6),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )
    destination = SpatialGrid.centered(
        sample_counts=(3, 3),
        sample_spacing=(0.2e-6, 0.2e-6),
    )
    with pytest.raises(OpticalError) as caught:
        aplanatic_focus(
            field,
            focal_length=8.0e-6,
            maximum_convergence_angle=0.3,
            axial_distance_from_focus=0.0,
            destination_grid=destination,
        )
    assert (
        caught.value.identity
        == "aplanatic_focus_objective_disk_not_contained"
    )

    wide_grid = SpatialGrid.centered(
        sample_counts=(17, 17),
        sample_spacing=(0.4e-6, 0.4e-6),
    )
    field = replace(
        field,
        envelope=torch.ones((1, 2, 17, 17), dtype=torch.complex128),
        grid=wide_grid,
    )
    aliased_destination = SpatialGrid(
        sample_counts=(2, 2),
        sample_spacing=(0.2e-6, 0.2e-6),
        first_sample_position=(0.0, 80.0e-6),
    )
    with pytest.raises(OpticalError) as caught:
        aplanatic_focus(
            field,
            focal_length=8.0e-6,
            maximum_convergence_angle=0.3,
            axial_distance_from_focus=0.0,
            destination_grid=aliased_destination,
        )
    assert caught.value.identity == "aplanatic_focus_phase_increment_aliased"


@pytest.mark.parametrize(
    ("representation", "normalization", "identity"),
    (
        (
            PolarizationRepresentation.SCALAR,
            FieldNormalization.RELATIVE,
            "aplanatic_focus_polarization_unsupported",
        ),
        (
            PolarizationRepresentation.FULL,
            FieldNormalization.RELATIVE,
            "aplanatic_focus_polarization_unsupported",
        ),
        (
            PolarizationRepresentation.TRANSVERSE,
            FieldNormalization.POWER,
            "aplanatic_focus_normalization_unsupported",
        ),
    ),
)
def test_unsupported_field_meaning_fails_with_stable_identity(
    representation: PolarizationRepresentation,
    normalization: FieldNormalization,
    identity: str,
) -> None:
    """
    非横向表示与非相对归一化在物理入口稳定拒绝
    """

    grid = SpatialGrid.centered(
        sample_counts=(11, 11),
        sample_spacing=(0.6e-6, 0.6e-6),
    )
    field = OpticalField(
        envelope=torch.ones(
            (1, representation.component_count, 11, 11),
            dtype=torch.complex128,
        ),
        grid=grid,
        spectrum=Spectrum.monochromatic(0.55e-6),
        polarization_representation=representation,
        medium=Vacuum(),
        normalization=normalization,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )

    with pytest.raises(OpticalError) as caught:
        aplanatic_focus(
            field,
            focal_length=8.0e-6,
            maximum_convergence_angle=0.3,
            axial_distance_from_focus=0.0,
            destination_grid=SpatialGrid.centered(
                sample_counts=(3, 3),
                sample_spacing=(0.2e-6, 0.2e-6),
            ),
        )

    assert caught.value.identity == identity


def test_gradient_enabled_input_and_destination_grids_are_rejected() -> None:
    """
    输入与目标网格分别拒绝可训练坐标几何
    """

    fixed_spacing = torch.tensor(0.6e-6, dtype=torch.float64)
    trainable_spacing = torch.tensor(
        0.6e-6,
        dtype=torch.float64,
        requires_grad=True,
    )
    input_grid = SpatialGrid.centered(
        sample_counts=(11, 11),
        sample_spacing=(trainable_spacing, fixed_spacing),
    )
    field = OpticalField(
        envelope=torch.ones((1, 2, 11, 11), dtype=torch.complex128),
        grid=input_grid,
        spectrum=Spectrum.monochromatic(0.55e-6),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )
    fixed_destination = SpatialGrid.centered(
        sample_counts=(3, 3),
        sample_spacing=(0.2e-6, 0.2e-6),
    )
    with pytest.raises(OpticalError) as caught:
        aplanatic_focus(
            field,
            focal_length=8.0e-6,
            maximum_convergence_angle=0.3,
            axial_distance_from_focus=0.0,
            destination_grid=fixed_destination,
        )
    assert (
        caught.value.identity
        == "aplanatic_focus_input_grid_requires_grad"
    )

    fixed_grid = SpatialGrid.centered(
        sample_counts=(11, 11),
        sample_spacing=(0.6e-6, 0.6e-6),
    )
    field = replace(field, grid=fixed_grid)
    destination = SpatialGrid.centered(
        sample_counts=(3, 3),
        sample_spacing=(
            torch.tensor(
                0.2e-6,
                dtype=torch.float64,
                requires_grad=True,
            ),
            torch.tensor(0.2e-6, dtype=torch.float64),
        ),
    )
    with pytest.raises(OpticalError) as caught:
        aplanatic_focus(
            field,
            focal_length=8.0e-6,
            maximum_convergence_angle=0.3,
            axial_distance_from_focus=0.0,
            destination_grid=destination,
        )
    assert (
        caught.value.identity
        == "aplanatic_focus_destination_grid_requires_grad"
    )


def test_meta_component_preserves_derived_shape_dtype_and_grid() -> None:
    """
    meta 前向运行真实数值路径并推导完整矢量目标场
    """

    grid = SpatialGrid.centered(
        sample_counts=(11, 13),
        sample_spacing=(0.5e-6, 0.45e-6),
    )
    destination = SpatialGrid.centered(
        sample_counts=(3, 5),
        sample_spacing=(0.2e-6, 0.18e-6),
    )
    field = OpticalField(
        envelope=torch.empty(
            (2, 1, 2, 11, 13),
            dtype=torch.complex128,
            device="meta",
        ),
        grid=grid.to(device="meta", dtype=torch.float64),
        spectrum=Spectrum.monochromatic(0.55e-6),
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )
    component = AplanaticFocus(
        focal_length=8.0e-6,
        maximum_convergence_angle=0.3,
        axial_distance_from_focus=0.1e-6,
        destination_grid=destination,
    )
    component = copy.deepcopy(component)
    component.to_empty(device="meta")

    output = component(field)

    assert output.envelope.shape == (2, 1, 3, 3, 5)
    assert output.envelope.dtype is torch.complex128
    assert output.envelope.device.type == "meta"
    assert output.grid.sample_counts == (3, 5)


def test_frozen_assembly_runs_aplanatic_focus_on_cpu() -> None:
    """
    冻结汇编通过 CPU 工作站运行聚焦组件（固定 double 精度）
    """

    grid = SpatialGrid.centered(
        sample_counts=(11, 13),
        sample_spacing=(0.5e-6, 0.45e-6),
    )
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(0.55e-6),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    propagation = AplanaticFocus(
        focal_length=8.0e-6,
        maximum_convergence_angle=0.3,
        axial_distance_from_focus=0.1e-6,
        destination_grid=SpatialGrid.centered(
            sample_counts=(3, 5),
            sample_spacing=(0.2e-6, 0.18e-6),
        ),
    )
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(propagation, name="propagation")
    assembly.connect(source, propagation)
    assembly.expose(propagation, name="field")
    assembly.freeze()
    workstation = Workstation.cpu()
    workstation.host(assembly)

    outputs, _ = workstation.run(assembly)

    output = outputs["field"]
    assert isinstance(output, OpticalField)
    assert output.envelope.dtype is torch.complex128
    assert output.envelope.shape == (1, 3, 3, 5)


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="Windows CUDA evidence requires an available CUDA device",
)
def test_available_windows_cuda_matches_cpu() -> None:
    """
    可用 Windows CUDA 与 CPU 聚焦保持同精度数值一致
    """

    grid = SpatialGrid.centered(
        sample_counts=(13, 15),
        sample_spacing=(0.5e-6, 0.4e-6),
    )
    generator = torch.Generator().manual_seed(42)
    envelope = torch.complex(
        torch.randn((1, 2, 13, 15), generator=generator, dtype=torch.float64),
        torch.randn((1, 2, 13, 15), generator=generator, dtype=torch.float64),
    )

    def field(values: torch.Tensor, device: str) -> OpticalField:
        """
        在指定设备构造共享物理定义的横向测试光场
        """
        return OpticalField(
            envelope=values.to(device=device),
            grid=grid.to(device=device, dtype=torch.float64),
            spectrum=Spectrum.monochromatic(0.55e-6),
            polarization_representation=(
                PolarizationRepresentation.TRANSVERSE
            ),
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )

    destination = SpatialGrid.centered(
        sample_counts=(4, 6),
        sample_spacing=(0.2e-6, 0.18e-6),
    )
    cpu = aplanatic_focus(
        field(envelope, "cpu"),
        focal_length=9.0e-6,
        maximum_convergence_angle=0.25,
        axial_distance_from_focus=0.13e-6,
        destination_grid=destination,
    )
    cuda = aplanatic_focus(
        field(envelope, "cuda"),
        focal_length=9.0e-6,
        maximum_convergence_angle=0.25,
        axial_distance_from_focus=0.13e-6,
        destination_grid=destination.to(
            device="cuda",
            dtype=torch.float64,
        ),
    )

    # Issue 16 冻结 FFT 族预算：max|CPU-CUDA| <= 1e-10 * max|CPU|；零峰须恰为零
    maximum_error = float((cpu.envelope - cuda.envelope.cpu()).abs().max())
    reference_peak = float(cpu.envelope.abs().max())
    allowed = 1.0e-10 * reference_peak
    if reference_peak == 0.0:
        assert maximum_error == 0.0, (
            f"零参考峰预算违规：maximum_error={maximum_error:.3e}，"
            f"reference_peak={reference_peak:.3e}，allowed={allowed:.3e}"
        )
    assert maximum_error <= allowed, (
        f"FFT 峰值预算违规：maximum_error={maximum_error:.3e} > "
        f"allowed={allowed:.3e}（reference_peak={reference_peak:.3e}）"
    )

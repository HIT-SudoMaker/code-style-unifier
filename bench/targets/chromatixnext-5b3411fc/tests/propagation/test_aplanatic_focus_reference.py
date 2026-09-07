from __future__ import annotations

import math
from pathlib import Path

import torch

from tests.architecture._python_import_facts import read_python_imports

from . import _aplanatic_reference
from ._aplanatic_reference import _direct_aplanatic_focus, _reference_sphere_field

_TESTS_ROOT = Path(__file__).resolve().parents[1]
_DOUBLE_EPSILON = torch.finfo(torch.float64).eps


def _roundoff_tolerance(scale: float, *, summed_terms: int = 1) -> float:
    return 64.0 * _DOUBLE_EPSILON * summed_terms * max(scale, 1.0)


def _smooth_circular_pupil(
    pupil_y: torch.Tensor,
    pupil_x: torch.Tensor,
    *,
    pupil_radius: float,
) -> torch.Tensor:
    coordinate_y, coordinate_x = torch.meshgrid(
        pupil_y,
        pupil_x,
        indexing="ij",
    )
    normalized_radius_squared = (
        coordinate_y.square() + coordinate_x.square()
    ) / pupil_radius**2
    taper = torch.clamp(
        1.0 - normalized_radius_squared,
        min=0.0,
    ).square()
    pupil = torch.empty(
        (1, 2, pupil_y.numel(), pupil_x.numel()),
        dtype=torch.complex128,
    )
    pupil[0, 0] = taper / math.sqrt(2.0)
    pupil[0, 1] = 1j * taper / math.sqrt(2.0)
    return pupil


def test_reference_module_has_no_production_dependency() -> None:
    """
    验证独立参考不导入任何生产实现
    """

    source_path = Path(_aplanatic_reference.__file__)
    imported_roots = {
        module.split(".", maxsplit=1)[0]
        for module in read_python_imports(
            source_path,
            _TESTS_ROOT,
        ).imported_modules
    }
    assert "chromatix_next" not in imported_roots


def test_zero_angle_preserves_transverse_cartesian_components() -> None:
    """
    验证零会聚角样本保持横向笛卡尔分量
    """

    pupil_y = torch.tensor((-1.0, 0.0, 1.0), dtype=torch.float64)
    pupil_x = torch.tensor((-1.0, 0.0, 1.0), dtype=torch.float64)
    pupil = torch.zeros((1, 2, 3, 3), dtype=torch.complex128)
    pupil[0, 0, 1, 1] = torch.tensor(
        0.7 - 0.2j,
        dtype=torch.complex128,
    )
    pupil[0, 1, 1, 1] = torch.tensor(
        -0.1 + 0.9j,
        dtype=torch.complex128,
    )

    sphere, _sin_theta, _cos_theta, support = _reference_sphere_field(
        pupil,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        focal_length=4.0,
        maximum_convergence_angle=math.asin(0.5),
    )

    expected = torch.tensor(
        (0.7 - 0.2j, -0.1 + 0.9j, 0.0j),
        dtype=torch.complex128,
    )
    assert support[1, 1]
    assert torch.allclose(
        sphere[0, :, 1, 1],
        expected,
        rtol=0.0,
        atol=_roundoff_tolerance(float(expected.abs().max())),
    )


def test_reference_sphere_is_transverse_and_preserves_discrete_energy() -> None:
    """
    验证参考球偏振横向性以及 Jacobian 能量恒等式
    """

    generator = torch.Generator().manual_seed(42)
    pupil_y = torch.linspace(-3.5, 3.5, 7, dtype=torch.float64)
    pupil_x = torch.linspace(-3.6, 3.6, 9, dtype=torch.float64)
    real = torch.randn(
        (2, 3, 2, 7, 9),
        generator=generator,
        dtype=torch.float64,
    )
    imaginary = torch.randn(
        (2, 3, 2, 7, 9),
        generator=generator,
        dtype=torch.float64,
    )
    pupil = torch.complex(real, imaginary)
    focal_length = 5.0

    sphere, sin_theta, cos_theta, support = _reference_sphere_field(
        pupil,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        focal_length=focal_length,
        maximum_convergence_angle=math.asin(0.72),
    )

    coordinate_y, coordinate_x = torch.meshgrid(
        pupil_y,
        pupil_x,
        indexing="ij",
    )
    radius = torch.sqrt(coordinate_x.square() + coordinate_y.square())
    safe_radius = torch.where(radius > 0.0, radius, torch.ones_like(radius))
    cos_azimuth = coordinate_x / safe_radius
    sin_azimuth = coordinate_y / safe_radius
    cos_azimuth = torch.where(
        radius > 0.0,
        cos_azimuth,
        torch.ones_like(cos_azimuth),
    )
    sin_azimuth = torch.where(
        radius > 0.0,
        sin_azimuth,
        torch.zeros_like(sin_azimuth),
    )
    ray_x = -sin_theta * cos_azimuth
    ray_y = -sin_theta * sin_azimuth
    ray_z = cos_theta
    residual = (
        ray_x * sphere[..., 0, :, :]
        + ray_y * sphere[..., 1, :, :]
        + ray_z * sphere[..., 2, :, :]
    )
    scale = float(sphere.abs().max())
    assert torch.allclose(
        residual,
        torch.zeros_like(residual),
        rtol=0.0,
        atol=_roundoff_tolerance(scale),
    )

    cell_area = (pupil_y[1] - pupil_y[0]).abs() * (
        pupil_x[1] - pupil_x[0]
    ).abs()
    incident_energy = (
        pupil.abs().square().sum(dim=-3) * support * cell_area
    ).sum(dim=(-2, -1))
    sphere_energy = (
        sphere.abs().square().sum(dim=-3)
        * support
        * cell_area
        / cos_theta
    ).sum(dim=(-2, -1))
    energy_scale = float(incident_energy.abs().max())
    assert torch.allclose(
        sphere_energy,
        incident_energy,
        rtol=0.0,
        atol=_roundoff_tolerance(
            energy_scale,
            summed_terms=pupil_y.numel() * pupil_x.numel(),
        ),
    )


def test_on_axis_closed_form_preserves_input_carrier_and_output_path() -> None:
    """
    验证光轴闭式值、输入载波与输出光程分解
    """

    pupil_y = torch.tensor((-0.4e-6, 0.0, 0.4e-6), dtype=torch.float64)
    pupil_x = torch.tensor((-0.5e-6, 0.0, 0.5e-6), dtype=torch.float64)
    pupil = torch.zeros((1, 2, 3, 3), dtype=torch.complex128)
    incident = torch.tensor((0.7 - 0.1j, -0.2 + 0.4j), dtype=torch.complex128)
    pupil[0, :, 1, 1] = incident
    wavelength = 0.55e-6
    refractive_index = 1.3
    focal_length = 4.0e-6
    axial_distance = 0.2e-6
    input_path = 0.37e-6

    result = _direct_aplanatic_focus(
        pupil,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        destination_y=torch.tensor((0.0,), dtype=torch.float64),
        destination_x=torch.tensor((0.0,), dtype=torch.float64),
        wavelengths=torch.tensor((wavelength,), dtype=torch.float64),
        refractive_indices=torch.tensor(
            (refractive_index,),
            dtype=torch.float64,
        ),
        input_path_lengths=torch.tensor((input_path,), dtype=torch.float64),
        focal_length=focal_length,
        maximum_convergence_angle=math.asin(0.5),
        axial_distance_from_focus=axial_distance,
    )

    wave_number = 2.0 * math.pi * refractive_index / wavelength
    vacuum_wave_number = 2.0 * math.pi / wavelength
    cell_area = (pupil_y[1] - pupil_y[0]).abs() * (
        pupil_x[1] - pupil_x[0]
    ).abs()
    expected_vector = torch.cat(
        (incident, torch.zeros(1, dtype=torch.complex128)),
    )
    expected_complete = (
        -1j
        * wave_number
        * cell_area
        / (2.0 * math.pi * focal_length)
        * expected_vector
        * torch.exp(
            1j
            * torch.tensor(
                vacuum_wave_number * input_path
                + wave_number * (focal_length + axial_distance),
                dtype=torch.float64,
            )
        )
    )
    expected_path = input_path + refractive_index * (
        focal_length + axial_distance
    )
    tolerance = _roundoff_tolerance(float(expected_complete.abs().max()))
    assert torch.allclose(
        result.complete_field[0, :, 0, 0],
        expected_complete,
        rtol=0.0,
        atol=tolerance,
    )
    assert torch.allclose(
        result.output_path_lengths,
        torch.tensor((expected_path,), dtype=torch.float64),
        rtol=0.0,
        atol=_roundoff_tolerance(expected_path),
    )
    expected_residual = expected_complete * torch.exp(
        -1j
        * torch.tensor(
            vacuum_wave_number * expected_path,
            dtype=torch.float64,
        )
    )
    assert torch.allclose(
        result.residual_envelope[0, :, 0, 0],
        expected_residual,
        rtol=0.0,
        atol=tolerance,
    )


def test_finite_angle_cell_matches_absolute_complex_vector_closed_form() -> None:
    """
    验证有限角度单元的负横向相位、固体角 Jacobian 与完整载波
    """

    pupil_y = torch.tensor((-0.3e-6, 0.0, 0.3e-6), dtype=torch.float64)
    pupil_x = torch.tensor((-0.4e-6, 0.0, 0.4e-6), dtype=torch.float64)
    field_x = torch.tensor(0.7 - 0.2j, dtype=torch.complex128)
    field_y = torch.tensor(-0.3 + 0.9j, dtype=torch.complex128)
    pupil = torch.zeros((1, 2, 3, 3), dtype=torch.complex128)
    pupil[0, 0, 2, 2] = field_x
    pupil[0, 1, 2, 2] = field_y
    destination_y = torch.tensor((0.17e-6,), dtype=torch.float64)
    destination_x = torch.tensor((-0.23e-6,), dtype=torch.float64)
    wavelength = 0.532e-6
    refractive_index = 1.31
    input_path = 0.19e-6
    focal_length = 4.0e-6
    axial_distance = -0.27e-6

    result = _direct_aplanatic_focus(
        pupil,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        destination_y=destination_y,
        destination_x=destination_x,
        wavelengths=torch.tensor((wavelength,), dtype=torch.float64),
        refractive_indices=torch.tensor(
            (refractive_index,),
            dtype=torch.float64,
        ),
        input_path_lengths=torch.tensor((input_path,), dtype=torch.float64),
        focal_length=focal_length,
        maximum_convergence_angle=math.asin(0.3),
        axial_distance_from_focus=axial_distance,
    )

    pupil_position_y = pupil_y[2]
    pupil_position_x = pupil_x[2]
    radius = torch.sqrt(
        pupil_position_x.square() + pupil_position_y.square(),
    )
    sin_theta = radius / focal_length
    cos_theta = torch.sqrt(1.0 - sin_theta.square())
    cos_azimuth = pupil_position_x / radius
    sin_azimuth = pupil_position_y / radius
    field_radial = (
        field_x * cos_azimuth + field_y * sin_azimuth
    )
    field_azimuthal = (
        -field_x * sin_azimuth + field_y * cos_azimuth
    )
    apodization = torch.sqrt(cos_theta)
    sphere = torch.stack(
        (
            apodization
            * (
                field_radial * cos_theta * cos_azimuth
                - field_azimuthal * sin_azimuth
            ),
            apodization
            * (
                field_radial * cos_theta * sin_azimuth
                + field_azimuthal * cos_azimuth
            ),
            apodization * field_radial * sin_theta,
        ),
    )
    wave_number = 2.0 * math.pi * refractive_index / wavelength
    vacuum_wave_number = 2.0 * math.pi / wavelength
    cell_area = (pupil_y[1] - pupil_y[0]).abs() * (
        pupil_x[1] - pupil_x[0]
    ).abs()
    solid_angle = cell_area / (focal_length**2 * cos_theta)
    lateral_projection = sin_theta * (
        cos_azimuth * destination_x[0]
        + sin_azimuth * destination_y[0]
    )
    phase = wave_number * (
        focal_length
        + cos_theta * axial_distance
        - lateral_projection
    )
    input_carrier = torch.exp(
        1j
        * torch.tensor(
            vacuum_wave_number * input_path,
            dtype=torch.float64,
        ),
    )
    expected = (
        -1j
        * wave_number
        * focal_length
        / (2.0 * math.pi)
        * solid_angle
        * sphere
        * torch.exp(1j * phase)
        * input_carrier
    )
    tolerance = _roundoff_tolerance(float(expected.abs().max()))
    actual = result.complete_field[0, :, 0, 0]
    assert torch.allclose(
        actual,
        expected,
        rtol=0.0,
        atol=tolerance,
    )

    wrong_lateral_phase = wave_number * (
        focal_length
        + cos_theta * axial_distance
        + lateral_projection
    )
    wrong_lateral = expected * torch.exp(
        1j * (wrong_lateral_phase - phase),
    )
    wrong_jacobian = expected * cos_theta
    assert float((actual - wrong_lateral).abs().max()) > 1.0e3 * tolerance
    assert float((actual - wrong_jacobian).abs().max()) > 1.0e3 * tolerance


def test_off_axis_single_ray_fixes_signed_axial_phase() -> None:
    """
    验证离轴单射线在正负焦外距离上的完整与残余相位
    """

    pupil_y = torch.tensor((-0.4e-6, 0.0, 0.4e-6), dtype=torch.float64)
    pupil_x = torch.tensor((-0.4e-6, 0.0, 0.4e-6), dtype=torch.float64)
    pupil = torch.zeros((1, 2, 3, 3), dtype=torch.complex128)
    pupil[0, 0, 1, 2] = torch.tensor(
        1.0 + 0.2j,
        dtype=torch.complex128,
    )
    wavelength = 0.532e-6
    focal_length = 4.0e-6
    distance = 0.3e-6
    common = {
        "pupil_y": pupil_y,
        "pupil_x": pupil_x,
        "destination_y": torch.tensor((0.0,), dtype=torch.float64),
        "destination_x": torch.tensor((0.0,), dtype=torch.float64),
        "wavelengths": torch.tensor((wavelength,), dtype=torch.float64),
        "refractive_indices": torch.tensor((1.0,), dtype=torch.float64),
        "input_path_lengths": torch.tensor((0.0,), dtype=torch.float64),
        "focal_length": focal_length,
        "maximum_convergence_angle": math.asin(0.5),
    }

    forward = _direct_aplanatic_focus(
        pupil,
        axial_distance_from_focus=distance,
        **common,
    )
    backward = _direct_aplanatic_focus(
        pupil,
        axial_distance_from_focus=-distance,
        **common,
    )

    sin_theta = pupil_x[2] / focal_length
    cos_theta = torch.sqrt(1.0 - sin_theta.square())
    wave_number = 2.0 * math.pi / wavelength
    complete_ratio = torch.exp(
        1j * 2.0 * wave_number * cos_theta * distance,
    )
    residual_ratio = torch.exp(
        1j * 2.0 * wave_number * (cos_theta - 1.0) * distance,
    )
    scale = float(forward.complete_field.abs().max())
    tolerance = _roundoff_tolerance(scale, summed_terms=9)
    assert torch.allclose(
        forward.complete_field,
        backward.complete_field * complete_ratio,
        rtol=0.0,
        atol=tolerance,
    )
    assert torch.allclose(
        forward.residual_envelope,
        backward.residual_envelope * residual_ratio,
        rtol=0.0,
        atol=tolerance,
    )


def test_positive_cell_area_makes_coordinate_reversal_invariant() -> None:
    """
    验证正采样面积使坐标朝向反转不引入全局负号
    """

    generator = torch.Generator().manual_seed(42)
    pupil_y = torch.linspace(-1.2e-6, 1.2e-6, 5, dtype=torch.float64)
    pupil_x = torch.linspace(-1.5e-6, 1.5e-6, 7, dtype=torch.float64)
    real = torch.randn(
        (1, 2, 5, 7),
        generator=generator,
        dtype=torch.float64,
    )
    imaginary = torch.randn(
        (1, 2, 5, 7),
        generator=generator,
        dtype=torch.float64,
    )
    pupil = torch.complex(real, imaginary)
    common = {
        "pupil_y": pupil_y,
        "destination_y": torch.tensor(
            (-0.13e-6, 0.21e-6),
            dtype=torch.float64,
        ),
        "destination_x": torch.tensor(
            (-0.31e-6, 0.02e-6, 0.35e-6),
            dtype=torch.float64,
        ),
        "wavelengths": torch.tensor((0.55e-6,), dtype=torch.float64),
        "refractive_indices": torch.tensor((1.2,), dtype=torch.float64),
        "input_path_lengths": torch.tensor((0.1e-6,), dtype=torch.float64),
        "focal_length": 4.0e-6,
        "maximum_convergence_angle": math.asin(0.5),
        "axial_distance_from_focus": 0.17e-6,
    }

    increasing = _direct_aplanatic_focus(
        pupil,
        pupil_x=pupil_x,
        **common,
    )
    decreasing = _direct_aplanatic_focus(
        torch.flip(pupil, dims=(-1,)),
        pupil_x=torch.flip(pupil_x, dims=(-1,)),
        **common,
    )

    scale = float(increasing.complete_field.abs().max())
    assert torch.allclose(
        decreasing.complete_field,
        increasing.complete_field,
        rtol=0.0,
        atol=_roundoff_tolerance(
            scale,
            summed_terms=pupil_y.numel() * pupil_x.numel(),
        ),
    )


def test_circular_pupil_and_circular_polarization_have_c4_intensity() -> None:
    """
    验证圆光瞳与圆偏振焦场的四重旋转强度对称性
    """

    focal_length = 10.0e-6
    maximum_angle = 0.6
    pupil_radius = focal_length * math.sin(maximum_angle)
    pupil_y = torch.linspace(
        -1.1 * pupil_radius,
        1.1 * pupil_radius,
        33,
        dtype=torch.float64,
    )
    pupil_x = pupil_y.clone()
    pupil = torch.empty((1, 2, 33, 33), dtype=torch.complex128)
    pupil[0, 0] = 1.0 / math.sqrt(2.0)
    pupil[0, 1] = torch.tensor(
        1j / math.sqrt(2.0),
        dtype=torch.complex128,
    )
    destination = torch.tensor(
        (-0.4e-6, 0.0, 0.4e-6),
        dtype=torch.float64,
    )

    result = _direct_aplanatic_focus(
        pupil,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        destination_y=destination,
        destination_x=destination,
        wavelengths=torch.tensor((0.532e-6,), dtype=torch.float64),
        refractive_indices=torch.tensor((1.0,), dtype=torch.float64),
        input_path_lengths=torch.tensor((0.0,), dtype=torch.float64),
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=0.0,
    )

    intensity = result.complete_field.abs().square().sum(dim=-3)
    rotated = torch.rot90(intensity, 1, dims=(-2, -1))
    scale = float(intensity.max())
    assert torch.allclose(
        intensity,
        rotated,
        rtol=0.0,
        atol=_roundoff_tolerance(
            scale,
            summed_terms=pupil_y.numel() * pupil_x.numel(),
        ),
    )


def test_reference_expresses_batched_multispectral_shifted_scaled_grids() -> None:
    """
    验证同一网格上的批量多光谱非方偏移缩放案例
    """

    focal_length = 8.0e-6
    maximum_angle = 0.55
    pupil_radius = focal_length * math.sin(maximum_angle)
    pupil_y = (
        torch.linspace(
            -1.08 * pupil_radius,
            1.08 * pupil_radius,
            17,
            dtype=torch.float64,
        )
        + 0.02 * pupil_radius
    )
    pupil_x = (
        torch.linspace(
            -1.10 * pupil_radius,
            1.10 * pupil_radius,
            21,
            dtype=torch.float64,
        )
        - 0.01 * pupil_radius
    )
    generator = torch.Generator().manual_seed(42)
    real = torch.randn(
        (2, 2, 17, 21),
        generator=generator,
        dtype=torch.float64,
    )
    imaginary = torch.randn(
        (2, 2, 17, 21),
        generator=generator,
        dtype=torch.float64,
    )
    base = torch.complex(real, imaginary)
    batch_scale = torch.tensor(0.4 + 0.7j, dtype=torch.complex128)
    pupil = torch.stack((base, base * batch_scale))
    wavelengths = torch.tensor(
        (0.532e-6, 0.633e-6),
        dtype=torch.float64,
    )
    input_paths = torch.tensor(
        (0.21e-6, -0.34e-6),
        dtype=torch.float64,
    )

    result = _direct_aplanatic_focus(
        pupil,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        destination_y=torch.tensor(
            (-0.23e-6, -0.06e-6, 0.11e-6),
            dtype=torch.float64,
        ),
        destination_x=torch.tensor(
            (-0.41e-6, -0.20e-6, 0.01e-6, 0.22e-6, 0.43e-6),
            dtype=torch.float64,
        ),
        wavelengths=wavelengths,
        refractive_indices=torch.tensor((1.0, 1.33), dtype=torch.float64),
        input_path_lengths=input_paths,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_angle,
        axial_distance_from_focus=0.27e-6,
    )

    assert result.complete_field.shape == (2, 2, 3, 3, 5)
    assert result.complete_field.dtype is torch.complex128
    assert result.residual_envelope.dtype is torch.complex128
    assert result.output_path_lengths.dtype is torch.float64
    scale = float(result.complete_field.abs().max())
    tolerance = _roundoff_tolerance(
        scale,
        summed_terms=pupil_y.numel() * pupil_x.numel(),
    )
    assert torch.allclose(
        result.complete_field[1],
        result.complete_field[0] * batch_scale,
        rtol=0.0,
        atol=tolerance,
    )
    output_carrier = torch.exp(
        1j
        * (2.0 * math.pi / wavelengths)
        * result.output_path_lengths
    ).reshape(1, 2, 1, 1, 1)
    assert torch.allclose(
        result.residual_envelope * output_carrier,
        result.complete_field,
        rtol=0.0,
        atol=tolerance,
    )


def test_pupil_refinement_contracts_the_direct_quadrature_error() -> None:
    """
    验证独立固体角求积随光瞳细化稳定收敛
    """

    focal_length = 10.0e-6
    maximum_angle = 0.6
    pupil_radius = focal_length * math.sin(maximum_angle)
    destination_y = torch.linspace(
        -0.33e-6,
        0.47e-6,
        5,
        dtype=torch.float64,
    )
    destination_x = torch.linspace(
        -0.58e-6,
        0.62e-6,
        7,
        dtype=torch.float64,
    )
    fields: list[torch.Tensor] = []
    for sample_count in (17, 33, 65):
        pupil_y = torch.linspace(
            -1.1 * pupil_radius,
            1.1 * pupil_radius,
            sample_count,
            dtype=torch.float64,
        )
        pupil_x = pupil_y.clone()
        result = _direct_aplanatic_focus(
            _smooth_circular_pupil(
                pupil_y,
                pupil_x,
                pupil_radius=pupil_radius,
            ),
            pupil_y=pupil_y,
            pupil_x=pupil_x,
            destination_y=destination_y,
            destination_x=destination_x,
            wavelengths=torch.tensor((0.532e-6,), dtype=torch.float64),
            refractive_indices=torch.tensor((1.0,), dtype=torch.float64),
            input_path_lengths=torch.tensor((0.0,), dtype=torch.float64),
            focal_length=focal_length,
            maximum_convergence_angle=maximum_angle,
            axial_distance_from_focus=0.3e-6,
        )
        fields.append(result.complete_field)

    coarse_delta = float((fields[1] - fields[0]).abs().max())
    fine_delta = float((fields[2] - fields[1]).abs().max())
    assert fine_delta < 0.35 * coarse_delta
    richardson_remaining = fine_delta / 3.0
    roundoff = _roundoff_tolerance(
        float(fields[2].abs().max()),
        summed_terms=65 * 65,
    )
    independently_derived_tolerance = 2.0 * richardson_remaining + roundoff
    assert independently_derived_tolerance < coarse_delta


def test_nested_destination_grids_agree_at_shared_physical_samples() -> None:
    """
    验证嵌套目标网格在共享物理坐标上给出同一复场
    """

    focal_length = 10.0e-6
    maximum_angle = 0.6
    pupil_radius = focal_length * math.sin(maximum_angle)
    pupil_y = torch.linspace(
        -1.1 * pupil_radius,
        1.1 * pupil_radius,
        33,
        dtype=torch.float64,
    )
    pupil_x = pupil_y.clone()
    pupil = _smooth_circular_pupil(
        pupil_y,
        pupil_x,
        pupil_radius=pupil_radius,
    )
    coarse_y = torch.linspace(
        -0.33e-6,
        0.47e-6,
        5,
        dtype=torch.float64,
    )
    coarse_x = torch.linspace(
        -0.58e-6,
        0.62e-6,
        7,
        dtype=torch.float64,
    )
    fine_y = torch.linspace(
        -0.33e-6,
        0.47e-6,
        9,
        dtype=torch.float64,
    )
    fine_x = torch.linspace(
        -0.58e-6,
        0.62e-6,
        13,
        dtype=torch.float64,
    )
    common = {
        "pupil_y": pupil_y,
        "pupil_x": pupil_x,
        "wavelengths": torch.tensor((0.532e-6,), dtype=torch.float64),
        "refractive_indices": torch.tensor((1.0,), dtype=torch.float64),
        "input_path_lengths": torch.tensor((0.17e-6,), dtype=torch.float64),
        "focal_length": focal_length,
        "maximum_convergence_angle": maximum_angle,
        "axial_distance_from_focus": -0.2e-6,
    }
    coarse = _direct_aplanatic_focus(
        pupil,
        destination_y=coarse_y,
        destination_x=coarse_x,
        **common,
    )
    fine = _direct_aplanatic_focus(
        pupil,
        destination_y=fine_y,
        destination_x=fine_x,
        **common,
    )

    shared = fine.complete_field[..., ::2, ::2]
    assert torch.allclose(
        shared,
        coarse.complete_field,
        rtol=0.0,
        atol=_roundoff_tolerance(
            float(coarse.complete_field.abs().max()),
            summed_terms=pupil_y.numel() * pupil_x.numel(),
        ),
    )

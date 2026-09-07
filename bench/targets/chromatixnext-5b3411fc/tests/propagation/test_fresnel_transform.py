from __future__ import annotations

import copy
from dataclasses import replace
import math
from unittest.mock import Mock

import pytest
import torch

from chromatix_next.errors import AssemblyError, OpticalError, OpticalValueError
from chromatix_next.optics import (
    Assembly,
    ConstantMedium,
    FieldNormalization,
    Medium,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PolarizationRepresentation,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.element import CircularPupil
from chromatix_next.optics.grid import PropagationExterior
from chromatix_next.optics.propagation import (
    FresnelTransform,
    fresnel_transform,
    scaled_angular_spectrum,
)
from chromatix_next.optics.source import PlaneWave


def _field(
    *,
    sample_counts: tuple[int, int] = (8, 10),
    sample_spacing: tuple[float, float] = (4.0e-6, 5.0e-6),
    medium: Medium = Vacuum(),
    orientation: tuple[str, str] = ("increasing", "increasing"),
) -> OpticalField:
    grid = SpatialGrid.centered(
        sample_counts=sample_counts,
        sample_spacing=sample_spacing,
        orientation=orientation,
    )
    return PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=600.0e-9),
        polarization=Polarization.scalar(),
        medium=medium,
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )(grid)


def _applicability_field(
    representation: PolarizationRepresentation,
) -> OpticalField:
    grid = SpatialGrid.centered(
        sample_counts=(8, 10),
        sample_spacing=(4.0e-6, 5.0e-6),
    )
    spectrum = Spectrum.monochromatic(wavelength=600.0e-9)
    return OpticalField(
        envelope=torch.ones(
            (spectrum.count, representation.component_count, *grid.sample_counts),
            dtype=torch.complex128,
        ),
        grid=grid,
        spectrum=spectrum,
        polarization_representation=representation,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )


@pytest.mark.parametrize(
    "representation",
    (PolarizationRepresentation.SCALAR, PolarizationRepresentation.TRANSVERSE),
    ids=("scalar", "transverse"),
)
def test_fresnel_transform_preserves_supported_representation(
    representation: PolarizationRepresentation,
) -> None:
    """
    菲涅耳变换保留其支持的标量或横向表征
    """
    field = _applicability_field(representation)
    output = fresnel_transform(field, axial_distance=20.0e-3)
    assert output.polarization_representation is representation


def test_fresnel_transform_rejects_full_before_expensive_transform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    完整矢量场在距离校验与数值变换之前被拒绝
    """
    transforms = tuple(Mock() for _ in range(6))
    for name, transform in zip(
        ("fft", "ifft", "fftn", "ifftn", "fft2", "ifft2"),
        transforms,
    ):
        monkeypatch.setattr(torch.fft, name, transform)
    field = _applicability_field(PolarizationRepresentation.FULL)
    with pytest.raises(OpticalError) as information:
        fresnel_transform(field, axial_distance=float("nan"))
    assert information.value.identity == (
        "fresnel_transform_polarization_full_unsupported"
    )
    assert all(not transform.called for transform in transforms)


def _coordinates(grid: SpatialGrid) -> tuple[torch.Tensor, torch.Tensor]:
    position_y = (
        torch.arange(
            grid.sample_counts[0],
            dtype=grid.sample_spacing[0].dtype,
        )
        * grid.signed_spacing[0]
        + grid.first_sample_position[0]
    )
    position_x = (
        torch.arange(
            grid.sample_counts[1],
            dtype=grid.sample_spacing[1].dtype,
        )
        * grid.signed_spacing[1]
        + grid.first_sample_position[1]
    )
    return position_y, position_x


def test_fresnel_transform_derives_one_dynamic_output_grid() -> None:
    """
    函数与组件从同一物理解析器得到由距离决定的输出采样
    """

    field = _field()
    distance = 20.0e-3
    direct = fresnel_transform(
        field,
        axial_distance=distance,
    )
    delegated = FresnelTransform(
        axial_distance=distance,
    )(field)
    wavelength = field.spectrum.wavelengths[0]
    expected_spacing = (
        wavelength
        * abs(distance)
        / (
            field.grid.sample_counts[0]
            * float(field.grid.sample_spacing[0])
        ),
        wavelength
        * abs(distance)
        / (
            field.grid.sample_counts[1]
            * float(field.grid.sample_spacing[1])
        ),
    )

    assert torch.equal(delegated.envelope, direct.envelope)
    assert direct.grid.sample_counts == field.grid.sample_counts
    assert direct.grid.orientation == field.grid.orientation
    assert torch.allclose(
        torch.stack(direct.grid.sample_spacing),
        torch.tensor(expected_spacing, dtype=torch.float64),
    )


def test_assembly_check_rejects_wrong_grid_after_fresnel_transform() -> None:
    """
    汇编以真实动态网格拒绝 Fresnel 传播后的错误固定网格
    """

    input_grid = SpatialGrid.centered(
        sample_counts=(8, 10),
        sample_spacing=(4.0e-6, 5.0e-6),
    )
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=600.0e-9),
        polarization=Polarization.scalar(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    propagation = FresnelTransform(
        axial_distance=20.0e-3,
    )
    wrong_pupil = CircularPupil(
        grid=input_grid,
        radius=10.0e-6,
    )
    assembly = Assembly()
    assembly.include(source, name="source", grid=input_grid)
    assembly.include(propagation, name="propagation")
    assembly.include(wrong_pupil, name="pupil")
    assembly.connect(source, propagation)
    assembly.connect(propagation, wrong_pupil)
    assembly.expose(wrong_pupil, name="output")

    with pytest.raises(AssemblyError) as information:
        assembly.check()

    assert "circular_pupil_grid_mismatch" in information.value.identity


@pytest.mark.parametrize(
    "orientation",
    (
        ("increasing", "increasing"),
        ("decreasing", "increasing"),
    ),
)
def test_signed_distance_preserves_orientation_and_round_trips(
    orientation: tuple[str, str],
) -> None:
    """
    正向 FFT 与反向 FFT 保持坐标朝向并返回原采样网格和包络
    """

    field = _field(orientation=orientation)
    generator = torch.Generator().manual_seed(42)
    envelope = torch.complex(
        torch.randn(
            field.envelope.shape,
            dtype=torch.float64,
            generator=generator,
        ),
        torch.randn(
            field.envelope.shape,
            dtype=torch.float64,
            generator=generator,
        ),
    )
    field = replace(field, envelope=envelope)

    propagated = fresnel_transform(
        field,
        axial_distance=20.0e-3,
    )
    returned = fresnel_transform(
        propagated,
        axial_distance=-20.0e-3,
    )

    assert propagated.grid.orientation == orientation
    assert returned.grid.is_physically_equivalent_to(field.grid)
    assert torch.allclose(
        returned.envelope,
        field.envelope,
        rtol=1.0e-12,
        atol=1.0e-12,
    )


def test_fresnel_transform_preserves_integrated_power() -> None:
    """
    正交离散变换保持含网格面积的积分功率
    """

    field = _field()
    generator = torch.Generator().manual_seed(42)
    envelope = torch.complex(
        torch.randn(
            field.envelope.shape,
            dtype=torch.float64,
            generator=generator,
        ),
        torch.randn(
            field.envelope.shape,
            dtype=torch.float64,
            generator=generator,
        ),
    )
    field = replace(field, envelope=envelope)

    output = fresnel_transform(
        field,
        axial_distance=20.0e-3,
    )

    input_power = field.envelope.abs().square().sum() * field.grid.cell_area
    output_power = output.envelope.abs().square().sum() * output.grid.cell_area
    tolerance = 1.0e-12
    assert torch.allclose(
        output_power,
        input_power,
        rtol=tolerance,
        atol=tolerance,
    )


def test_fresnel_transform_matches_analytic_gaussian_beam() -> None:
    """
    数值幅相与含古伊相位的解析高斯光束一致
    """

    wavelength = 600.0e-9
    waist_radius = 80.0e-6
    distance = 5.0e-3
    field = _field(
        sample_counts=(128, 128),
        sample_spacing=(5.0e-6, 5.0e-6),
    )
    input_y, input_x = _coordinates(field.grid)
    input_radius_squared = (
        input_y[:, None].square() + input_x[None, :].square()
    )
    field = replace(
        field,
        envelope=torch.exp(
            -input_radius_squared / waist_radius**2,
        )[None, None].to(torch.complex128),
    )

    output = fresnel_transform(
        field,
        axial_distance=distance,
    )

    output_y, output_x = _coordinates(output.grid)
    output_radius_squared = (
        output_y[:, None].square() + output_x[None, :].square()
    )
    rayleigh_range = math.pi * waist_radius**2 / wavelength
    propagated_radius = waist_radius * math.sqrt(
        1.0 + (distance / rayleigh_range) ** 2,
    )
    curvature_radius = distance * (
        1.0 + (rayleigh_range / distance) ** 2
    )
    gouy_phase = math.atan(distance / rayleigh_range)
    wave_number = 2.0 * math.pi / wavelength
    expected_magnitude = (
        waist_radius
        / propagated_radius
        * torch.exp(
            -output_radius_squared / propagated_radius**2,
        )
    )
    expected_phase = (
        wave_number * output_radius_squared / (2.0 * curvature_radius)
        - gouy_phase
    )
    expected = torch.polar(
        expected_magnitude,
        expected_phase,
    )[None, None]

    assert torch.allclose(
        output.envelope,
        expected,
        rtol=2.0e-5,
        atol=2.0e-6,
    )


def test_fresnel_transform_preserves_distance_gradient() -> None:
    """
    距离参数保留身份且 autograd 与独立有限差分一致
    """

    field = _field()
    distance = torch.nn.Parameter(
        torch.tensor(20.0e-3, dtype=torch.float64),
    )
    component = FresnelTransform(
        axial_distance=distance,
    )

    output = component(field)
    output_path = output.path_reference.lengths[0]
    assert isinstance(output_path, torch.Tensor)
    assert output_path.dtype is torch.float64
    assert output_path.requires_grad
    path_gradient = torch.autograd.grad(
        output_path,
        distance,
        retain_graph=True,
    )[0]
    objective = output.envelope[..., 1, 2].real.sum()
    gradient = torch.autograd.grad(objective, distance)[0]
    step = 1.0e-7
    positive = fresnel_transform(
        field,
        axial_distance=float(distance.detach() + step),
    ).envelope[..., 1, 2].real.sum()
    negative = fresnel_transform(
        field,
        axial_distance=float(distance.detach() - step),
    ).envelope[..., 1, 2].real.sum()
    finite_difference = (positive - negative) / (2.0 * step)

    assert component.axial_distance is distance
    assert dict(component.named_parameters())["axial_distance"] is distance
    assert torch.equal(
        path_gradient,
        torch.ones_like(distance),
    )
    assert torch.allclose(
        gradient,
        finite_difference,
        rtol=2.0e-5,
        atol=2.0e-5,
    )


def test_output_spacing_preserves_distance_gradient() -> None:
    """
    动态输出间距对轴向距离的 autograd 与有限差分一致
    """

    field = _field()
    distance = torch.nn.Parameter(
        torch.tensor(20.0e-3, dtype=torch.float64),
    )

    spacing = fresnel_transform(
        field,
        axial_distance=distance,
    ).grid.sample_spacing[0]
    gradient = torch.autograd.grad(spacing, distance)[0]
    step = 1.0e-7
    positive = fresnel_transform(
        field,
        axial_distance=float(distance.detach() + step),
    ).grid.sample_spacing[0]
    negative = fresnel_transform(
        field,
        axial_distance=float(distance.detach() - step),
    ).grid.sample_spacing[0]
    finite_difference = (positive - negative) / (2.0 * step)

    assert torch.allclose(
        gradient,
        finite_difference,
        rtol=1.0e-9,
        atol=1.0e-9,
    )


def test_fresnel_transform_meta_forward_preserves_shape_and_dtype() -> None:
    """
    meta 前向保持真实计算的场形状、精度和动态网格结构
    """

    real_field = _field()
    meta_field = replace(
        real_field,
        envelope=torch.empty_like(
            real_field.envelope,
            device="meta",
        ),
        grid=real_field.grid.to(
            device="meta",
            dtype=real_field.envelope.real.dtype,
        ),
    )
    component = FresnelTransform(
        axial_distance=20.0e-3,
    )
    isolated = copy.deepcopy(component)
    isolated.to_empty(device="meta")

    output = isolated(meta_field)

    assert output.envelope.device.type == "meta"
    assert output.envelope.shape == real_field.envelope.shape
    assert output.envelope.dtype is real_field.envelope.dtype
    assert output.grid.sample_counts == real_field.grid.sample_counts
    assert output.grid.sample_spacing[0].device.type == "meta"


def test_fresnel_transform_rejects_multispectral_field() -> None:
    """
    多光谱场以稳定身份拒绝而不隐藏选择参考波长
    """

    grid = SpatialGrid.centered(
        sample_counts=(8, 10),
        sample_spacing=(4.0e-6, 5.0e-6),
    )
    field = PlaneWave(
        spectrum=Spectrum(
            wavelengths=(500.0e-9, 600.0e-9),
            weights=(0.5, 0.5),
        ),
        polarization=Polarization.scalar(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )(grid)

    with pytest.raises(OpticalValueError) as information:
        fresnel_transform(
            field,
            axial_distance=20.0e-3,
        )

    assert (
        information.value.identity
        == "fresnel_transform_spectrum_not_monochromatic"
    )


@pytest.mark.parametrize(
    "invalid_distance",
    (
        0.0,
        float("nan"),
        True,
        torch.tensor([1.0]),
    ),
)
def test_fresnel_transform_rejects_invalid_distances(
    invalid_distance: object,
) -> None:
    """
    变换传播拒绝零值和非有限或非标量距离
    """

    with pytest.raises(OpticalValueError) as information:
        FresnelTransform(
            axial_distance=invalid_distance,  # type: ignore[arg-type]
        )

    assert (
        information.value.identity
        == "fresnel_transform_axial_distance_invalid"
    )


def test_fresnel_transform_rejects_float32_distance_parameter() -> None:
    """
    FresnelTransform 在自己的边界拒绝单精度轴向距离
    """

    with pytest.raises(
        OpticalValueError,
        match="fresnel_transform_axial_distance_invalid",
    ):
        FresnelTransform(
            axial_distance=torch.nn.Parameter(
                torch.tensor(2.0e-6, dtype=torch.float32),
            ),
        )


def test_fresnel_transform_rejects_zero_distance() -> None:
    """
    单变换 Fresnel 在构造边界拒绝退化零传播距离
    """

    with pytest.raises(
        OpticalValueError,
        match="fresnel_transform_axial_distance_invalid",
    ):
        FresnelTransform(axial_distance=0.0)


def test_output_sampling_uses_propagation_medium() -> None:
    """
    输出间距使用介质内波长而不是重复的真空假设
    """

    field = _field(
        medium=ConstantMedium(index=1.5),
    )

    output = fresnel_transform(
        field,
        axial_distance=20.0e-3,
    )

    vacuum_spacing = (
        field.spectrum.wavelengths[0]
        * 20.0e-3
        / (
            field.grid.sample_counts[0]
            * float(field.grid.sample_spacing[0])
        )
    )
    assert torch.allclose(
        output.grid.sample_spacing[0],
        torch.tensor(vacuum_spacing / 1.5, dtype=torch.float64),
    )


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_fresnel_transform_public_action_matches_cpu_on_cuda() -> None:
    """
    FresnelTransform 公共动作在 CUDA 上保持与 CPU 相同的复包络
    """

    cpu_field = _field()
    cuda_field = replace(cpu_field, envelope=cpu_field.envelope.cuda())

    cpu_output = fresnel_transform(cpu_field, axial_distance=20.0e-3)
    cuda_output = fresnel_transform(cuda_field, axial_distance=20.0e-3)

    # Issue 16 冻结 FFT 族预算：max|CPU-CUDA| <= 1e-10 * max|CPU|；零峰须恰为零
    maximum_error = float(
        (cpu_output.envelope - cuda_output.envelope.cpu()).abs().max(),
    )
    reference_peak = float(cpu_output.envelope.abs().max())
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


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_cuda_distance_parameter_keeps_identity_and_gradient() -> None:
    """
    CUDA 轴向距离 Parameter 保持注册身份并接收有限非零梯度
    """

    distance = torch.nn.Parameter(
        torch.tensor(20.0e-3, dtype=torch.float64, device="cuda"),
    )
    component = FresnelTransform(axial_distance=distance).cuda()
    cpu_field = _field()
    field = replace(cpu_field, envelope=cpu_field.envelope.cuda())

    output = component(field)
    observation = output.envelope[..., 1, 2].real.sum()
    gradient = torch.autograd.grad(observation, distance)[0]

    assert component.axial_distance is distance
    assert dict(component.named_parameters())["axial_distance"] is distance
    assert torch.isfinite(gradient)
    assert not torch.equal(gradient, torch.zeros_like(gradient))


def test_fresnel_richer_model_residual_decreases_with_phase_error() -> None:
    """
    近似模型证据：占用横向带宽变窄时，单变换 Fresnel 方程趋近标量角谱
    每次参照均使用 FresnelTransform 推导的精确输出 Grid。
    """

    base_field = _field(
        sample_counts=(64, 64),
        sample_spacing=(0.5e-6, 0.5e-6),
    )
    input_y, input_x = _coordinates(base_field.grid)
    residuals: list[float] = []
    for waist in (1.5e-6, 2.0e-6, 3.0e-6):
        field = replace(
            base_field,
            envelope=torch.exp(
                -(input_y[:, None].square() + input_x[None, :].square())
                / waist**2,
            )[None, None].to(torch.complex128),
        )
        fresnel_output = fresnel_transform(
            field,
            axial_distance=20.0e-6,
        )
        angular_output = scaled_angular_spectrum(
            field,
            axial_distance=20.0e-6,
            destination_grid=fresnel_output.grid,
            exterior=PropagationExterior.PERIODIC,
        )
        actual = angular_output.envelope
        expected = fresnel_output.envelope
        alignment = (actual.conj() * expected).sum() / actual.abs().square().sum()
        residuals.append(
            float((alignment * actual - expected).abs().max())
            / float(expected.abs().max())
        )

    assert residuals[1] < residuals[0]
    assert residuals[2] < residuals[1]

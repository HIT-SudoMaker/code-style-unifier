
from __future__ import annotations

import inspect
import math
from pathlib import Path
from unittest.mock import Mock

import pytest
import torch

from chromatix_next._numerics.wave_propagation.scalar_angular_spectrum import (
    scalar_angular_spectrum_calculation,
)
from chromatix_next.errors import AssemblyError, OpticalError
import chromatix_next.optics as optics_module
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
    TabulatedMedium,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import CircularPupil, IdealThinLens
from chromatix_next.optics.grid import PropagationExterior
from chromatix_next.optics.propagation import (
    ScalarAngularSpectrum,
    scalar_angular_spectrum,
    vector_angular_spectrum,
)
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


def _grid(
    counts: tuple[int, int] = (16, 16),
    spacing: tuple[float, float] = (1.0e-6, 1.0e-6),
) -> SpatialGrid:
    # 构造中心对齐的横向网格（样本物理对齐原点，递增朝向）
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=(
            torch.tensor(spacing[0], dtype=torch.float64),
            torch.tensor(spacing[1], dtype=torch.float64),
        ),
    )


def _applicability_field(
    representation: PolarizationRepresentation,
) -> OpticalField:
    grid = _grid()
    spectrum = _monochromatic()
    envelope = torch.ones(
        (spectrum.count, representation.component_count, *grid.sample_counts),
        dtype=torch.complex128,
    )
    return OpticalField(
        envelope=envelope,
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
def test_scalar_angular_spectrum_preserves_supported_representation(
    representation: PolarizationRepresentation,
) -> None:
    """
    标量角谱传播保留其支持的标量或横向表征
    """
    field = _applicability_field(representation)
    output = scalar_angular_spectrum(field, axial_distance=1.0e-6)
    assert output.polarization_representation is representation


def test_scalar_angular_spectrum_rejects_full_before_expensive_transform(
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
        scalar_angular_spectrum(field, axial_distance=float("nan"))
    assert information.value.identity == (
        "scalar_angular_spectrum_polarization_full_unsupported"
    )
    assert all(not transform.called for transform in transforms)


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    # 构造单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _constant_field(
    grid: SpatialGrid,
    spectrum: Spectrum,
    medium: Medium = None,  # type: ignore[assignment]
    amplitude: complex = 1.0 + 0.0j,
) -> OpticalField:
    # 构造均匀常幅零相位输入光场（轴向平面波）
    if medium is None:
        medium = Vacuum()
    counts_y, counts_x = grid.sample_counts
    envelope = torch.full(
        (spectrum.count, 1, counts_y, counts_x),
        amplitude,
        dtype=torch.complex128,
    )
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=spectrum,
        polarization_representation=(Polarization.scalar()).representation,
        medium=medium,
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


def _gaussian_field(
    grid: SpatialGrid,
    spectrum: Spectrum,
    waist: float,
    centre: tuple[float, float] = (0.0, 0.0),
    medium: Medium = None,  # type: ignore[assignment]
) -> OpticalField:
    # 构造二维高斯振幅光场（实包络、零相位）
    if medium is None:
        medium = Vacuum()
    counts_y, counts_x = grid.sample_counts
    signed_spacing_y, signed_spacing_x = grid.signed_spacing
    first_y, first_x = grid.first_sample_position
    position_y = (
        torch.arange(counts_y, dtype=torch.float64) * float(signed_spacing_y)
        + float(first_y)
    )
    position_x = (
        torch.arange(counts_x, dtype=torch.float64) * float(signed_spacing_x)
        + float(first_x)
    )
    radius_squared = (position_y[:, None] - centre[0]).square() + (
        position_x[None, :] - centre[1]
    ).square()
    amplitude = torch.exp(-radius_squared / (waist**2))
    envelope = amplitude.unsqueeze(0).unsqueeze(0).to(dtype=torch.complex128)
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=spectrum,
        polarization_representation=(Polarization.scalar()).representation,
        medium=medium,
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


def _tilted_field(
    grid: SpatialGrid,
    spectrum: Spectrum,
    transverse_wavevector: tuple[float, float],
    medium: Medium = None,  # type: ignore[assignment]
) -> OpticalField:
    # 构造单横向波矢平面波（与某 FFT 频率箱对齐以使频谱为单一 δ）
    if medium is None:
        medium = Vacuum()
    counts_y, counts_x = grid.sample_counts
    signed_spacing_y, signed_spacing_x = grid.signed_spacing
    first_y, first_x = grid.first_sample_position
    position_y = (
        torch.arange(counts_y, dtype=torch.float64) * float(signed_spacing_y)
        + float(first_y)
    )
    position_x = (
        torch.arange(counts_x, dtype=torch.float64) * float(signed_spacing_x)
        + float(first_x)
    )
    wavevector_y, wavevector_x = transverse_wavevector
    phase = (
        wavevector_y * position_y[:, None]
        + wavevector_x * position_x[None, :]
    )
    envelope = (
        torch.complex(torch.zeros_like(phase), phase)
        .exp()
        .unsqueeze(0)
        .unsqueeze(0)
    )
    return OpticalField(
        envelope=envelope.to(dtype=torch.complex128),
        grid=grid,
        spectrum=spectrum,
        polarization_representation=(Polarization.scalar()).representation,
        medium=medium,
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


class _CountingMedium(Medium):
    # 测试替身：记录公共 Medium 查询次数，折射率恒为 1

    def __init__(self) -> None:
        """
        建立空的查询精度记录
        """

        self.query_dtypes: list[torch.dtype] = []

    @property
    def query_count(self) -> int:
        """
        返回已经通过公共 Medium 接口完成的查询次数
        """

        return len(self.query_dtypes)

    # 记录查询并返回与波长同形的单位折射率
    def _evaluate_refractive_index(
        self,
        wavelengths: torch.Tensor,
    ) -> torch.Tensor:
        self.query_dtypes.append(wavelengths.dtype)
        return torch.ones_like(wavelengths)

    # 返回计数介质的稳定物理身份
    def _physical_identity(self) -> tuple[object, ...]:
        return ("counting",)


def _random_field(
    grid: SpatialGrid,
    spectrum: Spectrum,
    medium: Medium | None = None,
) -> OpticalField:
    # 构造固定种子的随机复场，避免仅以 DC 或单一频率箱验证传播
    generator = torch.Generator(device="cpu")
    generator.manual_seed(42)
    real = torch.randn(grid.sample_counts, generator=generator, dtype=torch.float64)
    imaginary = torch.randn(
        grid.sample_counts,
        generator=generator,
        dtype=torch.float64,
    )
    envelope = torch.complex(real, imaginary).unsqueeze(0).unsqueeze(0)
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=spectrum,
        polarization_representation=(Polarization.scalar()).representation,
        medium=medium or Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(1.25e-6,) * spectrum.count,
        ),
    )


def _dft_bins(count: int) -> torch.Tensor:
    # 返回与离散傅里叶定义一致的无量纲频率箱顺序，不调用 torch.fft
    bins = torch.arange(count, dtype=torch.float64)
    return torch.where(bins <= (count - 1) // 2, bins, bins - count)


def _direct_dft_propagation(
    field: OpticalField,
    *,
    output_grid: SpatialGrid,
    axial_distance: float,
    exterior: PropagationExterior,
) -> torch.Tensor:
    # 以显式 DFT 矩阵和完整亥姆霍兹传递式构造独立完整场参照，不复用生产 FFT
    input_height, input_width = field.grid.sample_counts
    displacement = (
        output_grid.first_sample_position[0]
        - field.grid.first_sample_position[0],
        output_grid.first_sample_position[1]
        - field.grid.first_sample_position[1],
    )
    if exterior is PropagationExterior.PERIODIC:
        computational_counts = field.grid.sample_counts
        padding = (0, 0)
    else:
        computational_counts = (
            3 * input_height,
            3 * input_width,
        )
        padding = (input_height, input_width)

    height, width = computational_counts
    sample_y = torch.arange(height, dtype=torch.float64)
    sample_x = torch.arange(width, dtype=torch.float64)
    bins_y = _dft_bins(height)
    bins_x = _dft_bins(width)
    forward_y = torch.exp(
        -2j * math.pi * bins_y[:, None] * sample_y[None, :] / height,
    )
    forward_x = torch.exp(
        -2j * math.pi * bins_x[:, None] * sample_x[None, :] / width,
    )
    inverse_y = torch.exp(
        2j * math.pi * sample_y[:, None] * bins_y[None, :] / height,
    ) / height
    inverse_x = torch.exp(
        2j * math.pi * sample_x[:, None] * bins_x[None, :] / width,
    ) / width

    sign_y = 1.0 if field.grid.orientation[0] == "increasing" else -1.0
    sign_x = 1.0 if field.grid.orientation[1] == "increasing" else -1.0
    frequency_y = (
        bins_y / (height * field.grid.sample_spacing[0]) * sign_y
    )
    frequency_x = (
        bins_x / (width * field.grid.sample_spacing[1]) * sign_x
    )
    frequency_grid_y, frequency_grid_x = torch.meshgrid(
        frequency_y,
        frequency_x,
        indexing="ij",
    )
    wavelengths = torch.tensor(field.spectrum.wavelengths, dtype=torch.float64)
    refractive_indices = field.medium.refractive_index(wavelengths)
    path_lengths = field.path_reference.lengths
    complete_outputs: list[torch.Tensor] = []
    for spectral_index, (wavelength, refractive_index) in enumerate(
        zip(wavelengths, refractive_indices, strict=True),
    ):
        wave_number = 2.0 * math.pi * float(refractive_index) / float(wavelength)
        longitudinal_wave_number = torch.sqrt(
            wave_number**2
            - (2.0 * math.pi * frequency_grid_y) ** 2
            - (2.0 * math.pi * frequency_grid_x) ** 2,
        )
        phase = (
            longitudinal_wave_number * axial_distance
            + 2.0
            * math.pi
            * (
                frequency_grid_y * displacement[0]
                + frequency_grid_x * displacement[1]
            )
        )
        transfer = torch.exp(1j * phase)
        carrier_phase = (
            2.0
            * math.pi
            * path_lengths[spectral_index]
            / float(wavelength)
        )
        carrier = complex(
            math.cos(carrier_phase),
            math.sin(carrier_phase),
        )
        polarization_outputs: list[torch.Tensor] = []
        for polarization_index in range(field.envelope.shape[-3]):
            embedded = torch.zeros((height, width), dtype=torch.complex128)
            embedded[
                padding[0] : padding[0] + input_height,
                padding[1] : padding[1] + input_width,
            ] = (
                field.envelope[spectral_index, polarization_index].to(
                    dtype=torch.complex128,
                )
                * carrier
            )
            spectrum_values = forward_y @ embedded @ forward_x.T
            propagated = (
                inverse_y @ (spectrum_values * transfer) @ inverse_x.T
            )
            polarization_outputs.append(
                propagated[
                    padding[0] : padding[0] + input_height,
                    padding[1] : padding[1] + input_width,
                ],
            )
        complete_outputs.append(torch.stack(polarization_outputs))
    return torch.stack(complete_outputs)


# 从包络与逐光谱光程参考独立重建完整复场，不调用传播实现
def _complete_field(field: OpticalField) -> torch.Tensor:
    wavelengths = torch.tensor(
        field.spectrum.wavelengths,
        dtype=field.envelope.real.dtype,
        device=field.envelope.device,
    )
    path_lengths = torch.tensor(
        field.path_reference.lengths,
        dtype=field.envelope.real.dtype,
        device=field.envelope.device,
    )
    phase = 2.0 * math.pi * path_lengths / wavelengths
    carrier = torch.complex(torch.zeros_like(phase), phase).exp()
    return field.envelope * carrier.reshape(-1, 1, 1, 1)


class TestPhysicalInvariants:
    """
    证据层 1：物理不变量
    """

    def test_function_and_component_are_the_same_physical_action(self) -> None:
        """
        直接函数与状态组件在相同物理参数下返回同一个传播结果
        """
        grid = _grid(counts=(5, 6), spacing=(4.0e-6, 5.0e-6))
        field = _random_field(grid, _monochromatic(wavelength=0.8e-6))
        axial_distance = 1.1e-6
        direct_output = scalar_angular_spectrum(
            field,
            axial_distance=axial_distance,
        )
        component_output = ScalarAngularSpectrum(
            axial_distance=axial_distance,
        )(field)
        assert direct_output.grid is component_output.grid
        assert direct_output.path_reference == component_output.path_reference
        assert torch.equal(
            direct_output.envelope,
            component_output.envelope,
        )

    def test_diagnostic_is_a_stateless_query_of_the_same_support(self) -> None:
        """
        诊断返回真实保留功率与存活频点，且不写入组件状态
        """
        grid = _grid(counts=(8, 8), spacing=(0.25e-6, 0.25e-6))
        field = _random_field(
            grid,
            _monochromatic(wavelength=1.0e-6),
        )
        field.envelope.requires_grad_(True)
        propagation = ScalarAngularSpectrum(axial_distance=0.0)
        state_before = {
            name: value.clone()
            for name, value in propagation.state_dict().items()
        }

        diagnostic = propagation.diagnose(field)
        diagnostic.retained_power_ratio.sum().backward()

        assert diagnostic.retained_power_ratio.shape == (1,)
        assert torch.all(
            (diagnostic.retained_power_ratio > 0.0)
            & (diagnostic.retained_power_ratio < 1.0)
        )
        assert torch.equal(
            diagnostic.surviving_frequency_count,
            torch.tensor([13]),
        )
        assert field.envelope.grad is not None
        assert torch.all(torch.isfinite(field.envelope.grad))
        assert tuple(propagation.state_dict()) == tuple(state_before)
        for name, value in propagation.state_dict().items():
            assert torch.equal(value, state_before[name])

    def test_diagnostic_preserves_batch_and_spectrum_on_meta(self) -> None:
        """
        诊断的功率比保留批次与光谱轴，meta 查询不读取数值
        """
        grid = _grid(counts=(8, 8), spacing=(0.25e-6, 0.25e-6))
        spectrum = Spectrum(
            wavelengths=(0.8e-6, 1.0e-6),
            weights=(0.5, 0.5),
        )
        field = OpticalField(
            envelope=torch.empty(
                (3, 2, 1, 8, 8),
                dtype=torch.complex128,
                device="meta",
            ),
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0, 0.0)),
        )

        diagnostic = ScalarAngularSpectrum(axial_distance=0.0).diagnose(field)

        assert diagnostic.retained_power_ratio.shape == (3, 2)
        assert diagnostic.retained_power_ratio.dtype == torch.float64
        assert diagnostic.retained_power_ratio.device.type == "meta"
        assert diagnostic.surviving_frequency_count.shape == (2,)
        assert diagnostic.surviving_frequency_count.dtype == torch.int64
        assert diagnostic.surviving_frequency_count.device.type == "meta"

    def test_onaxis_plane_wave_moves_carrier_to_path_reference(self) -> None:
        """
        轴向平面波的残差包络不变，均匀载波仅进入逐谱光程参考
        """
        grid = _grid()
        spectrum = _monochromatic(wavelength=2.0e-6)
        field = _constant_field(grid, spectrum, Vacuum(), amplitude=1.0 + 0.0j)
        axial_distance = 3.0e-6
        output = ScalarAngularSpectrum(axial_distance=axial_distance)(field)
        assert torch.equal(output.envelope, field.envelope)
        assert output.path_reference.lengths == pytest.approx(
            (axial_distance,),
        )

    def test_tilted_plane_wave_acquires_longitudinal_phase(self) -> None:
        """
        倾斜平面波残差相位为 (kz-k)·d，均匀 k·d 进入光程参考
        """
        counts = (16, 16)
        spacing = (1.0e-6, 1.0e-6)
        grid = SpatialGrid.centered(sample_counts=counts, sample_spacing=spacing)
        spectrum = _monochromatic(wavelength=2.0e-6)
        # 与频率箱对齐：ky = 2π·m_y/(N_y·Δy)，kx = 2π·m_x/(N_x·Δx)
        bin_y, bin_x = 2, 1
        wavevector_y = 2.0 * math.pi * bin_y / (counts[0] * spacing[0])
        wavevector_x = 2.0 * math.pi * bin_x / (counts[1] * spacing[1])
        field = _tilted_field(grid, spectrum, (wavevector_y, wavevector_x))
        axial_distance = 2.5e-6
        output = ScalarAngularSpectrum(axial_distance=axial_distance)(field)
        wave_number = 2.0 * math.pi / 2.0e-6
        kz = math.sqrt(
            wave_number**2 - wavevector_y**2 - wavevector_x**2,
        )
        expected_phase = (kz - wave_number) * axial_distance
        ratio = output.envelope[0, 0] / field.envelope[0, 0]
        expected_ratio = complex(
            math.cos(expected_phase),
            math.sin(expected_phase),
        )
        assert torch.allclose(
            ratio,
            torch.full(
                grid.sample_counts,
                expected_ratio,
                dtype=torch.complex128,
            ),
            atol=1e-9,
        )

    def test_signed_axial_distance_forward_backward_is_identity(self) -> None:
        """
        先按正轴向距离传播再按相反距离传播，残差包络回到原场
        """
        grid = _grid(counts=(64, 64), spacing=(0.5e-6, 0.5e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=3.0e-6)
        axial_distance = 4.0e-6
        forward = ScalarAngularSpectrum(
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )
        backward = ScalarAngularSpectrum(
            axial_distance=-axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )
        round_trip = backward(forward(field))
        assert torch.allclose(round_trip.envelope, field.envelope, atol=1e-11)

    def test_free_space_power_conserved_within_bandlimit(self) -> None:
        """
        带限内自由空间传播守恒总传播功率（角谱在传播+带限支撑上幺正）
        """
        grid = _grid(counts=(48, 48), spacing=(0.4e-6, 0.4e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        # 充分包含的紧致高斯 ⇒ 频谱集中于 DC 附近，远在混叠安全带内
        field = _gaussian_field(grid, spectrum, waist=4.0e-6)
        axial_distance = 3.0e-6
        output = ScalarAngularSpectrum(
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )(field)
        input_power = field.envelope.abs().square().sum()
        output_power = output.envelope.abs().square().sum()
        relative_error = (
            (output_power - input_power).abs() / input_power
        ).item()
        assert relative_error < 1.0e-5

    def test_input_grid_destination_preserves_input_grid(self) -> None:
        """
        省略或显式复用输入网格时，输出保留同一网格对象身份
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum)
        implicit_output = ScalarAngularSpectrum(
            axial_distance=2.0e-6,
        )(field)
        explicit_output = ScalarAngularSpectrum(
            axial_distance=2.0e-6,
            destination_grid=grid,
        )(field)
        assert implicit_output.grid is grid
        assert explicit_output.grid.is_physically_equivalent_to(grid)

    def test_translated_destination_grid_preserves_geometry(self) -> None:
        """
        平移目标网格是完整 SpatialGrid，仅首样本位置不同
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum)
        translated_position = (
            torch.tensor(0.7e-6, dtype=torch.float64),
            torch.tensor(-0.4e-6, dtype=torch.float64),
        )
        destination_grid = SpatialGrid(
            sample_counts=grid.sample_counts,
            sample_spacing=grid.sample_spacing,
            first_sample_position=translated_position,
            orientation=grid.orientation,
        )
        output = ScalarAngularSpectrum(
            axial_distance=2.0e-6,
            destination_grid=destination_grid,
        )(field)
        assert output.grid.is_physically_equivalent_to(destination_grid)

    def test_translated_destination_imposes_phase_ramp(self) -> None:
        """
        平移目标网格使倾斜平面波相对输入网格输出增加线性相位
        """
        counts = (16, 16)
        spacing = (1.0e-6, 1.0e-6)
        grid = SpatialGrid.centered(sample_counts=counts, sample_spacing=spacing)
        spectrum = _monochromatic(wavelength=2.0e-6)
        bin_y, bin_x = 2, -1
        wavevector_y = 2.0 * math.pi * bin_y / (counts[0] * spacing[0])
        wavevector_x = 2.0 * math.pi * bin_x / (counts[1] * spacing[1])
        field = _tilted_field(grid, spectrum, (wavevector_y, wavevector_x))
        displacement = (0.65e-6, -0.35e-6)
        input_grid_output = ScalarAngularSpectrum(
            axial_distance=1.5e-6,
            destination_grid=grid,
        )(field)
        destination_grid = SpatialGrid(
            sample_counts=grid.sample_counts,
            sample_spacing=grid.sample_spacing,
            first_sample_position=(
                grid.first_sample_position[0] + displacement[0],
                grid.first_sample_position[1] + displacement[1],
            ),
            orientation=grid.orientation,
        )
        translated_grid_output = ScalarAngularSpectrum(
            axial_distance=1.5e-6,
            destination_grid=destination_grid,
        )(field)
        ratio = (
            translated_grid_output.envelope[0, 0]
            / input_grid_output.envelope[0, 0]
        )
        expected_phase = (
            wavevector_y * displacement[0] + wavevector_x * displacement[1]
        )
        expected = complex(math.cos(expected_phase), math.sin(expected_phase))
        assert torch.allclose(
            ratio,
            torch.full(grid.sample_counts, expected, dtype=torch.complex128),
            atol=1e-9,
        )

    def test_path_reference_advances_by_signed_axial_distance(self) -> None:
        """
        真空输出逐谱光程参考 = 输入参考 + 带符号轴向距离
        """
        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum)
        output = ScalarAngularSpectrum(axial_distance=2.5e-6)(field)
        assert output.path_reference.lengths == pytest.approx((2.5e-6,))

    def test_signed_distance_and_medium_advance_path_reference(self) -> None:
        """
        带符号距离与介质折射率共同决定光程参考的推进量
        """
        grid = _grid()
        base_field = _random_field(grid, _monochromatic())
        medium = ConstantMedium(index=1.4)
        field = OpticalField(
            envelope=base_field.envelope,
            grid=base_field.grid,
            spectrum=base_field.spectrum,
            polarization_representation=base_field.polarization_representation,
            medium=medium,
            normalization=base_field.normalization,
            path_reference=base_field.path_reference,
        )
        propagator = ScalarAngularSpectrum(axial_distance=-0.75e-6)
        output = propagator(field)
        expected_reference = (
            field.path_reference.lengths[0] + 1.4 * -0.75e-6,
        )
        assert output.path_reference.lengths == pytest.approx(
            expected_reference,
        )
        assert output.medium is medium

    def test_unsupported_destination_geometry_rejected_by_assembly_check(
        self,
    ) -> None:
        """
        Assembly.check 在运行前保留目标网格适用性错误的稳定身份
        """
        grid = _grid()
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=grid.sample_counts,
            sample_spacing=grid.sample_spacing,
            orientation=("decreasing", "increasing"),
        )
        propagator = ScalarAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(propagator, name="propagation")
        assembly.include(detector, name="detection")
        assembly.connect(source, propagator)
        assembly.connect(propagator, detector)
        assembly.expose(detector, name="intensity")
        with pytest.raises(
            AssemblyError,
            match="scalar_angular_spectrum_destination_grid_not_applicable",
        ):
            assembly.check()

    def test_unsupported_destination_geometry_rejected_before_medium_query(
        self,
    ) -> None:
        """
        direct forward 对不适用目标先拒绝，不查询介质、更不会进入 FFT
        """
        grid = _grid()
        medium = _CountingMedium()
        field = _constant_field(grid, _monochromatic(), medium)
        destination_grid = SpatialGrid.centered(
            sample_counts=(12, 16),
            sample_spacing=grid.sample_spacing,
        )
        propagator = ScalarAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )
        with pytest.raises(
            ValueError,
            match="scalar_angular_spectrum_destination_grid_not_applicable",
        ):
            propagator(field)
        assert medium.query_count == 0

    @pytest.mark.parametrize(
        ("entry_point", "mismatch"),
        [
            ("forward", "sample_counts"),
            ("forward", "sample_spacing"),
            ("forward", "orientation"),
            ("assembly_check", "sample_counts"),
            ("assembly_check", "sample_spacing"),
            ("assembly_check", "orientation"),
        ],
    )
    def test_destination_mismatch_rejected_before_fft_at_every_entry(
        self,
        entry_point: str,
        mismatch: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        三类目标几何失配在计算与装配检查入口均先于 FFT 拒绝
        """
        grid = _grid()
        medium = _CountingMedium()
        field = _constant_field(grid, _monochromatic(), medium)
        if mismatch == "sample_counts":
            destination_grid = SpatialGrid.centered(
                sample_counts=(12, 16),
                sample_spacing=grid.sample_spacing,
                orientation=grid.orientation,
            )
        elif mismatch == "sample_spacing":
            destination_grid = SpatialGrid.centered(
                sample_counts=grid.sample_counts,
                sample_spacing=(1.5e-6, 1.0e-6),
                orientation=grid.orientation,
            )
        else:
            destination_grid = SpatialGrid.centered(
                sample_counts=grid.sample_counts,
                sample_spacing=grid.sample_spacing,
                orientation=("decreasing", "increasing"),
            )
        propagator = ScalarAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )

        def reject_fft(*_arguments: object, **_keywords: object) -> torch.Tensor:
            """
            拒绝适用性失败后仍进入 FFT 的非法执行
            """
            error_identity = "fft_called_after_applicability_failure"
            raise AssertionError(error_identity)

        monkeypatch.setattr(torch.fft, "fftn", reject_fft)
        monkeypatch.setattr(torch.fft, "ifftn", reject_fft)

        with pytest.raises(
            (ValueError, AssemblyError),
            match="scalar_angular_spectrum_destination_grid_not_applicable",
        ):
            if entry_point == "forward":
                propagator(field)
            else:
                source = PlaneWave(
                    spectrum=field.spectrum,
                    polarization=Polarization.scalar(),
                    medium=medium,
                    propagation_direction=PropagationDirection.forward(),
                    relative_amplitude=1.0,
                )
                detector = IntensityDetection()
                assembly = Assembly()
                assembly.include(source, name="source", grid=grid)
                assembly.include(propagator, name="propagation")
                assembly.include(detector, name="detection")
                assembly.connect(source, propagator)
                assembly.connect(propagator, detector)
                assembly.expose(detector, name="intensity")
                assembly.check()
        assert medium.query_count == 0

    def test_medium_is_the_only_refractive_index_validation_owner(self) -> None:
        """
        包络与参考各经 Medium 公共边界解析其精度域，不设传播层重复验证
        """
        medium = _CountingMedium()
        field = _constant_field(_grid(), _monochromatic(), medium)
        ScalarAngularSpectrum(axial_distance=1.0e-6)(field)
        assert len(medium.query_dtypes) >= 1
        assert all(
            dtype is torch.float64 for dtype in medium.query_dtypes
        )
        source = Path(
            "src/chromatix_next/optics/propagation/scalar_angular_spectrum.py",
        ).read_text(encoding="utf-8")
        assert "_validate_indices" not in source

    def test_non_finite_axial_distance_rejected_at_construction(self) -> None:
        """
        非有限轴向距离以稳定身份在构造处拒绝
        """
        with pytest.raises(
            ValueError,
            match="scalar_angular_spectrum_axial_distance_invalid",
        ):
            ScalarAngularSpectrum(axial_distance=float("inf"))
        with pytest.raises(
            ValueError,
            match="scalar_angular_spectrum_axial_distance_invalid",
        ):
            ScalarAngularSpectrum(axial_distance=float("nan"))

    def test_float32_axial_distance_rejected_at_construction(self) -> None:
        """
        ScalarAngularSpectrum 在自己的边界拒绝单精度轴向距离
        """

        with pytest.raises(
            ValueError,
            match="scalar_angular_spectrum_axial_distance_invalid",
        ):
            ScalarAngularSpectrum(
                axial_distance=torch.nn.Parameter(
                    torch.tensor(2.0e-6, dtype=torch.float32),
                ),
            )

    def test_float64_axial_distance_parameter_keeps_optimizer_identity(
        self,
    ) -> None:
        """
        合法轴向距离 Parameter 保持同一注册对象并对优化器可见
        """

        axial_distance = torch.nn.Parameter(
            torch.tensor(2.0e-6, dtype=torch.float64),
        )
        propagator = ScalarAngularSpectrum(axial_distance=axial_distance)

        assert propagator.axial_distance is axial_distance
        assert (
            dict(propagator.named_parameters())["axial_distance"]
            is axial_distance
        )

    def test_invalid_exterior_rejected(self) -> None:
        """
        非 PropagationExterior 的外部以稳定身份拒绝
        """
        with pytest.raises(TypeError, match="scalar_angular_spectrum_exterior_invalid"):
            ScalarAngularSpectrum(
                axial_distance=1.0e-6,
                exterior="periodic",  # type: ignore[arg-type]
            )

    def test_invalid_destination_grid_rejected(self) -> None:
        """
        非 SpatialGrid 的目标网格以稳定身份拒绝
        """
        with pytest.raises(
            TypeError,
            match="scalar_angular_spectrum_destination_grid_invalid",
        ):
            ScalarAngularSpectrum(
                axial_distance=1.0e-6,
                destination_grid="not-a-grid",  # type: ignore[arg-type]
            )

    def test_non_optical_field_input_rejected(self) -> None:
        """
        非 OpticalField 输入以稳定身份拒绝
        """
        propagator = ScalarAngularSpectrum(axial_distance=1.0e-6)
        with pytest.raises(TypeError, match="scalar_angular_spectrum_field_invalid"):
            propagator("not a field")  # type: ignore[arg-type]

    def test_non_physical_medium_index_rejected(self) -> None:
        """
        非正/非有限折射率由 Medium 公共输出边界稳定拒绝
        """

        class _BadMedium(Medium):
            # 返回非有限折射率以触发公共输出守卫
            def _evaluate_refractive_index(
                self,
                wavelengths: torch.Tensor,
            ) -> torch.Tensor:
                return torch.full_like(wavelengths, float("nan"))

            # 声明该非法介质替身的确定身份
            def _physical_identity(self) -> tuple[object, ...]:
                return ("_bad_medium",)

        grid = _grid()
        spectrum = _monochromatic()
        field = _constant_field(grid, spectrum, _BadMedium())
        propagator = ScalarAngularSpectrum(axial_distance=1.0e-6)
        with pytest.raises(
            ValueError,
            match="medium_refractive_index_output_invalid",
        ):
            propagator(field)

    def test_unresolved_alias_band_rejects_without_substitution(self) -> None:
        """
        混叠安全带窄于首个频率箱时拒绝，不静默退化或替换传播方法
        """
        grid = _grid(counts=(24, 24), spacing=(0.5e-6, 0.5e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=4.0e-6)
        with pytest.raises(
            ValueError,
            match="scalar_angular_spectrum_alias_band_too_narrow",
        ):
            ScalarAngularSpectrum(
                axial_distance=1.0e-3,
                exterior=PropagationExterior.ISOLATED,
            )(field)

    def test_periodic_and_isolated_agree_for_contained_field(self) -> None:
        """
        充分包含的紧致场在两种外部下中心区域须一致（无绕回、无截断差异）
        """
        counts = (48, 48)
        spacing = (0.4e-6, 0.4e-6)
        grid = SpatialGrid.centered(sample_counts=counts, sample_spacing=spacing)
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=3.0e-6)
        periodic_output = ScalarAngularSpectrum(
            axial_distance=2.0e-6,
            exterior=PropagationExterior.PERIODIC,
        )(field)
        isolated_output = ScalarAngularSpectrum(
            axial_distance=2.0e-6,
            exterior=PropagationExterior.ISOLATED,
        )(field)
        peak = periodic_output.envelope.abs().max().item()
        # 中心区域两外部须一致（边缘因 48 vs 144 频率箱采样差异略有不同）
        centre_slice = (slice(None), slice(None), slice(12, 36), slice(12, 36))
        assert torch.allclose(
            periodic_output.envelope[centre_slice],
            isolated_output.envelope[centre_slice],
            atol=5.0e-6 * peak,
        )

    def test_isolated_suppresses_periodic_wraparound(self) -> None:
        """
        近边高斯：Periodic 在对边出现延拓能量；Isolated 抑制之（外部语义差异）
        """
        counts = (32, 32)
        spacing = (0.5e-6, 0.5e-6)
        grid = SpatialGrid.centered(sample_counts=counts, sample_spacing=spacing)
        spectrum = _monochromatic(wavelength=0.5e-6)
        # 高斯中心偏向角点，使尾部溢出窗口、在周期假设下绕回
        centre_bin = (counts[0] // 2 - 6, counts[1] // 2 - 6)
        centre_metres = (
            float(grid.first_sample_position[0]) + centre_bin[0] * spacing[0],
            float(grid.first_sample_position[1]) + centre_bin[1] * spacing[1],
        )
        field = _gaussian_field(
            grid,
            spectrum,
            waist=3.0e-6,
            centre=centre_metres,
        )
        periodic_output = ScalarAngularSpectrum(
            axial_distance=8.0e-6,
            exterior=PropagationExterior.PERIODIC,
        )(field)
        isolated_output = ScalarAngularSpectrum(
            axial_distance=8.0e-6,
            exterior=PropagationExterior.ISOLATED,
        )(field)
        periodic_intensity = periodic_output.envelope[0, 0].abs().square()
        isolated_intensity = isolated_output.envelope[0, 0].abs().square()
        # 对角（远离源）区域：Periodic 须比 Isolated 携带更多绕回能量
        far_corner = periodic_intensity[-6:, -6:].sum().item()
        far_corner_isolated = isolated_intensity[-6:, -6:].sum().item()
        assert far_corner > far_corner_isolated

class TestIndependentReference:
    """
    证据层 2：独立解析参照（解析高斯光束 1/q 形式）
    """

    @pytest.mark.parametrize(
        ("axial_distance", "displacement"),
        [
            (1.3e-6, (0.0, 0.0)),
            (-0.8e-6, (1.1e-6, -1.7e-6)),
            (0.0, (-0.9e-6, 1.3e-6)),
        ],
        ids=("forward-same-grid", "backward-translated-grid", "zero-translated-grid"),
    )
    def test_multispectral_dispersion_reconstructs_complete_asm_field(
        self,
        axial_distance: float,
        displacement: tuple[float, float],
    ) -> None:
        """
        非零输入参考、多谱色散、带符号距离和平移经公开因子分解重建完整 ASM
        """
        reference_type = getattr(optics_module, "OpticalPathReference")
        grid = _grid(counts=(4, 5), spacing=(4.0e-6, 5.0e-6))
        spectrum = Spectrum(
            wavelengths=(0.7e-6, 0.9e-6),
            weights=(0.4, 0.6),
        )
        medium = TabulatedMedium(
            wavelengths=(0.6e-6, 1.0e-6),
            refractive_indices=(1.45, 1.55),
        )
        generator = torch.Generator(device="cpu")
        generator.manual_seed(42)
        envelope = torch.complex(
            torch.randn((2, 1, 4, 5), generator=generator, dtype=torch.float64),
            torch.randn((2, 1, 4, 5), generator=generator, dtype=torch.float64),
        )
        field = OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=medium,
            normalization=FieldNormalization.RELATIVE,
            path_reference=reference_type(lengths=(0.3e-6, -0.2e-6)),
        )
        destination_grid = SpatialGrid(
            sample_counts=grid.sample_counts,
            sample_spacing=grid.sample_spacing,
            first_sample_position=(
                grid.first_sample_position[0] + displacement[0],
                grid.first_sample_position[1] + displacement[1],
            ),
            orientation=grid.orientation,
        )
        propagator = ScalarAngularSpectrum(
            axial_distance=axial_distance,
            destination_grid=destination_grid,
        )
        output = propagator(field)
        complete_reference = _direct_dft_propagation(
            field,
            output_grid=destination_grid,
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )
        assert torch.allclose(
            _complete_field(output),
            complete_reference,
            atol=3.0e-11,
        )

    def test_random_field_matches_direct_dft_reference(self) -> None:
        """
        随机带限复场的对齐传播匹配显式 DFT 参照，而非仅核验 DC
        """
        grid = _grid(counts=(5, 6), spacing=(4.0e-6, 5.0e-6))
        field = _random_field(grid, _monochromatic(wavelength=0.8e-6))
        axial_distance = 1.1e-6
        output = ScalarAngularSpectrum(
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )(field)
        reference = _direct_dft_propagation(
            field,
            output_grid=grid,
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )
        assert torch.allclose(_complete_field(output), reference, atol=2.0e-11)

    @pytest.mark.parametrize(
        ("orientation", "exterior"),
        [
            (
                ("increasing", "increasing"),
                PropagationExterior.PERIODIC,
            ),
            (
                ("decreasing", "increasing"),
                PropagationExterior.PERIODIC,
            ),
            (
                ("increasing", "decreasing"),
                PropagationExterior.PERIODIC,
            ),
            (
                ("decreasing", "decreasing"),
                PropagationExterior.PERIODIC,
            ),
            (
                ("increasing", "increasing"),
                PropagationExterior.ISOLATED,
            ),
            (
                ("decreasing", "increasing"),
                PropagationExterior.ISOLATED,
            ),
            (
                ("increasing", "decreasing"),
                PropagationExterior.ISOLATED,
            ),
            (
                ("decreasing", "decreasing"),
                PropagationExterior.ISOLATED,
            ),
        ],
        ids=(
            "increasing-increasing-periodic",
            "decreasing-increasing-periodic",
            "increasing-decreasing-periodic",
            "decreasing-decreasing-periodic",
            "increasing-increasing-isolated",
            "decreasing-increasing-isolated",
            "increasing-decreasing-isolated",
            "decreasing-decreasing-isolated",
        ),
    )
    def test_subsample_shift_matches_direct_dft_reference(
        self,
        orientation: tuple[str, str],
        exterior: PropagationExterior,
    ) -> None:
        """
        非整数位移在四种朝向和两种外部语义下匹配显式 DFT 参照
        """
        grid = SpatialGrid.centered(
            sample_counts=(4, 5),
            sample_spacing=(4.0e-6, 5.0e-6),
            orientation=orientation,
        )
        field = _random_field(grid, _monochromatic(wavelength=0.8e-6))
        displacement = (1.3e-6, -2.1e-6)
        destination_grid = SpatialGrid(
            sample_counts=grid.sample_counts,
            sample_spacing=grid.sample_spacing,
            first_sample_position=(
                grid.first_sample_position[0] + displacement[0],
                grid.first_sample_position[1] + displacement[1],
            ),
            orientation=grid.orientation,
        )
        axial_distance = 0.9e-6
        output = ScalarAngularSpectrum(
            axial_distance=axial_distance,
            exterior=exterior,
            destination_grid=destination_grid,
        )(field)
        reference = _direct_dft_propagation(
            field,
            output_grid=destination_grid,
            axial_distance=axial_distance,
            exterior=exterior,
        )
        assert torch.allclose(_complete_field(output), reference, atol=3.0e-11)

    def test_isolated_gaussian_matches_analytic_shape_and_gouy_phase(
        self,
    ) -> None:
        """
        大腰斑高斯的孤立传播须匹配解析 1/q 形状与中心古伊相位
        """
        counts = (48, 48)
        spacing = (0.4e-6, 0.4e-6)
        grid = SpatialGrid.centered(sample_counts=counts, sample_spacing=spacing)
        wavelength = 0.5e-6
        spectrum = _monochromatic(wavelength=wavelength)
        waist = 5.0e-6
        field = _gaussian_field(grid, spectrum, waist=waist)
        axial_distance = 15.0e-6

        output = ScalarAngularSpectrum(
            axial_distance=axial_distance,
            exterior=PropagationExterior.ISOLATED,
        )(field)

        wave_number = 2.0 * math.pi / wavelength
        rayleigh_range = wave_number * waist**2 / 2.0
        dimensionless_distance = axial_distance / rayleigh_range
        # 1/q 形式参考包络：复参数 q = 1 + i·d/z_R；均匀载波由光程参考承担
        q_complex = complex(1.0, dimensionless_distance)
        signed_spacing_y, signed_spacing_x = grid.signed_spacing
        first_y, first_x = grid.first_sample_position
        position_y = (
            torch.arange(counts[0], dtype=torch.float64) * float(signed_spacing_y)
            + float(first_y)
        )
        position_x = (
            torch.arange(counts[1], dtype=torch.float64) * float(signed_spacing_x)
            + float(first_x)
        )
        radius_squared = position_y[:, None] ** 2 + position_x[None, :] ** 2
        q_torch = torch.tensor(q_complex, dtype=torch.complex128)
        exponent = -radius_squared / (waist**2 * q_torch)
        reference_spatial = (1.0 / q_torch) * exponent.exp()
        reference = reference_spatial.unsqueeze(0).unsqueeze(0)

        # 中心区域比较（避免边缘混叠/截断影响）：内 24×24
        centre_slice = (slice(None), slice(None), slice(12, 36), slice(12, 36))
        output_centre = output.envelope[centre_slice]
        reference_centre = reference[centre_slice]
        peak = reference_centre.abs().max().item()
        assert torch.allclose(
            output_centre,
            reference_centre,
            atol=0.02 * peak,
            rtol=0.02,
        )
        measured_gouy_phase = torch.angle(
            output.envelope[0, 0, counts[0] // 2, counts[1] // 2],
        )
        expected_gouy_phase = -math.atan(dimensionless_distance)
        assert float(measured_gouy_phase) == pytest.approx(
            expected_gouy_phase,
            abs=0.02,
        )

    def test_kernel_matches_reference_transfer_formula(self) -> None:
        """
        残差核在 DC 处恒为一，均匀载波不重复写入包络
        """
        # DC 处 kz=k，故残差 exp(i·(kz-k)·d) = 1
        counts = (8, 8)
        spacing = (1.0e-6, 1.0e-6)
        axial_distance_value = 1.3e-6
        wavelengths = torch.tensor([2.0e-6], dtype=torch.float64)
        indices = torch.tensor([1.0], dtype=torch.float64)
        transfer = scalar_angular_spectrum_calculation(
            computational_counts=counts,
            signed_spacing=(
                torch.tensor(spacing[0], dtype=torch.float64),
                torch.tensor(spacing[1], dtype=torch.float64),
            ),
            displacement=(
                torch.tensor(0.0, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
            ),
            axial_distance=torch.tensor(axial_distance_value, dtype=torch.float64),
            wavelengths=wavelengths,
            refractive_indices=indices,
            real_dtype=torch.float64,
            complex_dtype=torch.complex128,
            device=torch.device("cpu"),
        ).transfer
        assert torch.allclose(
            transfer[0, 0, 0],
            torch.tensor(1.0 + 0.0j, dtype=torch.complex128),
            atol=1e-12,
        )

class TestComponentState:
    """
    可复用组件的固定状态、精度与设备行为
    """

    def test_loaded_fixed_distance_matches_fresh_component(self) -> None:
        """
        固定轴向距离经公共状态加载改变后仍匹配相同状态的全新组件
        """
        field = _random_field(
            _grid(counts=(5, 6), spacing=(4.0e-6, 5.0e-6)),
            _monochromatic(wavelength=0.8e-6),
        )
        reused = ScalarAngularSpectrum(axial_distance=1.0e-6)
        reused(field)
        changed_state = ScalarAngularSpectrum(axial_distance=1.4e-6).state_dict()
        reused.load_state_dict(changed_state)
        output = reused(field)
        fresh_output = ScalarAngularSpectrum(axial_distance=1.4e-6)(field)
        assert output.path_reference == fresh_output.path_reference
        assert torch.allclose(
            output.envelope,
            fresh_output.envelope,
        )

    def test_destination_grid_is_registered_and_moves_to_meta(self) -> None:
        """
        显式目标网格进入传播元件的状态树并随模块迁移
        """
        destination_grid = SpatialGrid(
            sample_counts=(5, 6),
            sample_spacing=(
                torch.tensor(4.0e-6, dtype=torch.float64),
                torch.tensor(5.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-8.0e-6, dtype=torch.float64),
                torch.tensor(-15.0e-6, dtype=torch.float64),
            ),
        )
        propagation = ScalarAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )

        assert len(tuple(propagation.buffers())) == 5

        propagation.to(device="meta")

        assert propagation.destination_grid is not None
        assert all(
            value.device.type == "meta"
            for value in (
                *propagation.destination_grid.sample_spacing,
                *propagation.destination_grid.first_sample_position,
            )
        )

    def test_destination_grid_roundtrips_through_state_dict(self) -> None:
        """
        目标网格的间距与原点随传播元件 state_dict 一同恢复
        """
        source_grid = SpatialGrid(
            sample_counts=(5, 6),
            sample_spacing=(
                torch.tensor(4.0e-6, dtype=torch.float64),
                torch.tensor(5.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-8.0e-6, dtype=torch.float64),
                torch.tensor(-15.0e-6, dtype=torch.float64),
            ),
        )
        restored_grid = SpatialGrid(
            sample_counts=(5, 6),
            sample_spacing=(
                torch.tensor(6.0e-6, dtype=torch.float64),
                torch.tensor(7.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(0.0, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
            ),
        )
        source = ScalarAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=source_grid,
        )
        restored = ScalarAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=restored_grid,
        )

        restored.load_state_dict(source.state_dict())

        assert restored.destination_grid is not None
        assert source.destination_grid is not None
        assert restored.destination_grid.is_physically_equivalent_to(
            source.destination_grid,
        )

    def test_unhosted_cuda_field_owns_transfer_device(self) -> None:
        """
        CUDA 输入可驱动未托管组件在同一设备计算，不受 CPU 距离 Buffer 设备污染
        """
        if not torch.cuda.is_available():
            pytest.skip("CUDA-capable PyTorch runtime is not available.")
        base = _random_field(_grid(), _monochromatic(wavelength=0.8e-6))
        field = OpticalField(
            envelope=base.envelope.to(device="cuda:0", dtype=torch.complex128),
            grid=base.grid,
            spectrum=base.spectrum,
            polarization_representation=base.polarization_representation,
            medium=base.medium,
            normalization=base.normalization,
            path_reference=base.path_reference,
        )
        propagator = ScalarAngularSpectrum(axial_distance=1.0e-6)
        output = propagator(field)
        fresh_output = ScalarAngularSpectrum(axial_distance=1.0e-6)(field)
        assert output.envelope.device == field.envelope.device
        assert output.envelope.dtype is field.envelope.dtype
        assert output.path_reference == fresh_output.path_reference
        assert torch.allclose(output.envelope, fresh_output.envelope)

    @pytest.mark.cuda
    def test_public_action_matches_cpu_on_cuda(self) -> None:
        """
        公共动作在 CUDA 上保持与 CPU 相同的复包络与平移目标网格
        预算依据 Issue 16 方程预算族的 FFT 类（1e-10 峰值相对量级）。
        """
        if not torch.cuda.is_available():
            pytest.skip("CUDA-capable PyTorch runtime is not available.")
        base = _random_field(_grid(), _monochromatic(wavelength=0.8e-6))
        field = OpticalField(
            envelope=base.envelope.to(device="cuda:0", dtype=torch.complex128),
            grid=base.grid,
            spectrum=base.spectrum,
            polarization_representation=base.polarization_representation,
            medium=base.medium,
            normalization=base.normalization,
            path_reference=base.path_reference,
        )
        destination_grid = SpatialGrid(
            sample_counts=(16, 16),
            sample_spacing=(
                torch.tensor(1.0e-6, dtype=torch.float64),
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-9.5e-6, dtype=torch.float64),
                torch.tensor(-9.5e-6, dtype=torch.float64),
            ),
        )
        cpu_output = scalar_angular_spectrum(
            base,
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )
        cuda_output = scalar_angular_spectrum(
            field,
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )
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
        # 输出网格由动作按 destination_grid 语义重导出，采样数与间距逐项一致
        assert cpu_output.grid.sample_counts == (16, 16)
        assert cuda_output.grid.sample_counts == (16, 16)
        for cpu_spacing, cuda_spacing in zip(
            cpu_output.grid.sample_spacing,
            cuda_output.grid.sample_spacing,
        ):
            torch.testing.assert_close(
                cpu_spacing,
                cuda_spacing,
                rtol=0.0,
                atol=0.0,
            )

class TestGradientEvidence:
    """
    证据层 3：梯度证据（双精度，经组件→实部约减）
    """

    def test_gradcheck_on_trainable_axial_distance(self) -> None:
        """
        对可训练轴向距离做 gradcheck（经传播→包络实部和）
        """
        grid = _grid(counts=(16, 16), spacing=(0.5e-6, 0.5e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=3.0e-6)
        axial_distance = torch.nn.Parameter(
            torch.tensor(2.0e-6, dtype=torch.float64),
        )
        propagator = ScalarAngularSpectrum(
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )

        def run(distance_value: torch.Tensor) -> torch.Tensor:
            """
            返回当前轴向距离下的输出包络实部和（依赖相位 via cos）
            """
            return propagator(field).envelope.real.sum()

        assert torch.autograd.gradcheck(
            run,
            (axial_distance,),
            eps=1e-9,
            raise_exception=True,
        )

    def test_local_intensity_retains_nonzero_distance_gradient(self) -> None:
        """
        非平凡局部光强观测保留有限且非零的残差传播梯度
        """
        grid = _grid(counts=(12, 12), spacing=(0.6e-6, 0.6e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=2.2e-6)
        axial_distance = torch.nn.Parameter(
            torch.tensor(3.0e-6, dtype=torch.float64),
        )
        propagator = ScalarAngularSpectrum(
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )
        detector = IntensityDetection()

        def observe(distance_value: torch.Tensor) -> torch.Tensor:
            """
            返回离中心一个采样位置处的传播光强
            """
            assert distance_value is axial_distance
            return detector(propagator(field)).values[4, 7]

        observed = observe(axial_distance)
        gradient = torch.autograd.grad(observed, axial_distance)[0]
        assert bool(torch.isfinite(gradient))
        assert abs(float(gradient)) > 1.0e-6
        assert torch.autograd.gradcheck(
            observe,
            (axial_distance,),
            eps=1.0e-9,
            raise_exception=True,
        )


class TestIndependentFocusingEvidence:
    """
    圆光瞳、理想薄透镜与传播组合后的独立焦平面证据
    """

    def test_circular_pupil_focus_resolves_analytic_airy_first_zero(
        self,
    ) -> None:
        """
        仿真焦平面第一暗环半径匹配圆孔衍射解析值
        """

        counts = (128, 128)
        sample_spacing = 2.0e-6
        wavelength = 0.5e-6
        aperture_diameter = 80.0e-6
        focal_length = 5.0e-3
        grid = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=(sample_spacing, sample_spacing),
        )
        field = PlaneWave(
            spectrum=Spectrum.monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )(grid)
        field = CircularPupil(
            grid=grid,
            radius=aperture_diameter / 2.0,
        )(field)
        field = IdealThinLens(
            grid=grid,
            focal_length=focal_length,
        )(field)
        field = ScalarAngularSpectrum(
            axial_distance=focal_length,
            exterior=PropagationExterior.ISOLATED,
        )(field)
        intensity = IntensityDetection()(field).values
        centre = counts[0] // 2
        radial_line = intensity[centre, centre:] / intensity[centre, centre]

        first_bessel_zero = 3.8317059702075125
        expected_radius = (
            first_bessel_zero
            * wavelength
            * focal_length
            / (math.pi * aperture_diameter)
        )
        expected_index = int(round(expected_radius / sample_spacing))
        search_start = expected_index - 2
        search_stop = expected_index + 3
        measured_index = search_start + int(
            torch.argmin(radial_line[search_start:search_stop]),
        )
        measured_radius = measured_index * sample_spacing

        assert measured_radius == pytest.approx(
            expected_radius,
            abs=sample_spacing,
        )
        assert float(radial_line[measured_index]) < 1.0e-3


class TestHostedFocusing:
    """
    托管端到端：PlaneWave → 圆光瞳 → 理想薄透镜 → ScalarAngularSpectrum → 探测
    """

    def test_focal_plane_central_peak(self) -> None:
        """
        焦平面传播 ⇒ 光强全局峰位于中心，且远高于均值（会聚聚焦）
        """
        counts = (32, 32)
        spacing = (1.0e-6, 1.0e-6)
        grid = SpatialGrid.centered(sample_counts=counts, sample_spacing=spacing)
        spectrum = _monochromatic(wavelength=1.0e-6)
        focal_length = 40.0e-6
        aperture_radius = 8.0e-6

        workstation = Workstation.cpu()
        source = workstation.host(
            PlaneWave(
                spectrum=spectrum,
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                propagation_direction=PropagationDirection.forward(),
                relative_amplitude=1.0,
            )
        )
        pupil = workstation.host(
            CircularPupil(
                grid=SpatialGrid.centered(
                    sample_counts=counts,
                    sample_spacing=spacing,
                ),
                radius=aperture_radius,
            ),
        )
        lens = workstation.host(
            IdealThinLens(
                grid=SpatialGrid.centered(
                    sample_counts=counts,
                    sample_spacing=spacing,
                ),
                focal_length=focal_length,
            ),
        )
        propagator = workstation.host(
            ScalarAngularSpectrum(
                axial_distance=focal_length,
                exterior=PropagationExterior.ISOLATED,
            )
        )
        detection = workstation.host(IntensityDetection())

        field = source(grid)
        pupil_field = pupil(field)
        lensed = lens(pupil_field)
        propagated = propagator(lensed)
        intensity = detection(propagated)

        values = intensity.values
        centre = (values.shape[-2] // 2, values.shape[-1] // 2)
        # 全局峰须位于中心邻域（±1 像素，容许离散对中）
        flat_argmax = int(values.argmax().item())
        peak_y = flat_argmax // values.shape[-1]
        peak_x = flat_argmax % values.shape[-1]
        assert abs(peak_y - centre[0]) <= 1
        assert abs(peak_x - centre[1]) <= 1
        # 会聚锐峰：中心光强远高于均值
        central_value = values[centre[0], centre[1]].item()
        mean_value = values.mean().item()
        assert central_value > 5.0 * mean_value


def test_scalar_richer_model_residual_to_vector_decreases_at_low_angle() -> None:
    """
    近似模型证据：占用横向频率比例趋近零时，标量传播趋近横向矢量传播
    残差只保留纵向矢量分量；两种动作使用同一辐射模态和有符号距离。
    """

    sample_count = 32
    wavelength = 0.5e-6
    axial_distance = 1.0e-6
    residuals: list[float] = []
    for transverse_fraction in (0.4, 0.2, 0.1):
        spacing = wavelength / (sample_count * transverse_fraction)
        grid = SpatialGrid.centered(
            sample_counts=(sample_count, sample_count),
            sample_spacing=(spacing, spacing),
        )
        position_x = (
            torch.arange(sample_count, dtype=torch.float64)
            * grid.signed_spacing[1]
            + grid.first_sample_position[1]
        )
        wavevector_x = 2.0 * math.pi / (sample_count * spacing)
        phase = wavevector_x * position_x
        phasor = torch.complex(torch.zeros_like(phase), phase).exp()
        phasor = phasor.unsqueeze(0).expand(sample_count, sample_count)
        spectrum = Spectrum.monochromatic(wavelength=wavelength)
        path_reference = OpticalPathReference(lengths=(0.0,))
        scalar_field = OpticalField(
            envelope=phasor.unsqueeze(0).unsqueeze(0),
            grid=grid,
            spectrum=spectrum,
            polarization_representation=Polarization.scalar().representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=path_reference,
        )
        vector_field = OpticalField(
            envelope=torch.stack((phasor, torch.zeros_like(phasor))).unsqueeze(0),
            grid=grid,
            spectrum=spectrum,
            polarization_representation=PolarizationRepresentation.TRANSVERSE,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=path_reference,
        )
        scalar_output = scalar_angular_spectrum(
            scalar_field,
            axial_distance=axial_distance,
        )
        vector_output = vector_angular_spectrum(
            vector_field,
            axial_distance=axial_distance,
        )
        scalar_as_vector = torch.zeros_like(vector_output.envelope)
        scalar_as_vector[:, 0] = scalar_output.envelope[:, 0]
        residuals.append(
            float((vector_output.envelope - scalar_as_vector).abs().max())
            / float(vector_output.envelope.abs().max())
        )

    assert residuals[1] < residuals[0]
    assert residuals[2] < residuals[1]

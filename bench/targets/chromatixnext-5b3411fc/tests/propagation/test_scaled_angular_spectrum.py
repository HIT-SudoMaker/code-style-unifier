
from __future__ import annotations

import math
from unittest.mock import Mock

import pytest
import torch

from chromatix_next._numerics.optical_path_reference import (
    express_envelope_in_optical_path_reference,
)
from chromatix_next.errors import AssemblyError, OpticalError
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
from chromatix_next.optics.grid import PropagationExterior
from chromatix_next.optics.propagation import (
    ScalarAngularSpectrum,
    ScaledAngularSpectrum,
    scaled_angular_spectrum,
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


def _random_field(
    grid: SpatialGrid,
    spectrum: Spectrum,
    medium: Medium | None = None,
) -> OpticalField:
    # 构造固定种子的随机复场，避免仅以 DC 或单一频率箱验证传播
    generator = torch.Generator(device="cpu")
    generator.manual_seed(42)
    real = torch.randn(
        grid.sample_counts,
        generator=generator,
        dtype=torch.float64,
    )
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
            lengths=(0.0,) * spectrum.count,
        ),
    )


def _dft_bins(count: int) -> torch.Tensor:
    # 返回与离散傅里叶定义一致的无量纲频率箱顺序，不调用 torch.fft
    bins = torch.arange(count, dtype=torch.float64)
    return torch.where(bins <= (count - 1) // 2, bins, bins - count)


def _direct_dft_scaled(
    field: OpticalField,
    *,
    destination_grid: SpatialGrid,
    axial_distance: float,
    exterior: PropagationExterior,
) -> torch.Tensor:
    input_height, input_width = field.grid.sample_counts
    if exterior is PropagationExterior.PERIODIC:
        computational_counts = field.grid.sample_counts
        padding = (0, 0)
    else:
        computational_counts = (3 * input_height, 3 * input_width)
        padding = (input_height, input_width)
    height, width = computational_counts

    sign_y = 1.0 if field.grid.orientation[0] == "increasing" else -1.0
    sign_x = 1.0 if field.grid.orientation[1] == "increasing" else -1.0
    spacing_y_in = float(field.grid.sample_spacing[0])
    spacing_x_in = float(field.grid.sample_spacing[1])
    first_y_in = float(field.grid.first_sample_position[0])
    first_x_in = float(field.grid.first_sample_position[1])

    out_counts_y, out_counts_x = destination_grid.sample_counts
    spacing_y_out = float(destination_grid.signed_spacing[0])
    spacing_x_out = float(destination_grid.signed_spacing[1])
    first_y_out = float(destination_grid.first_sample_position[0])
    first_x_out = float(destination_grid.first_sample_position[1])

    # 目标样本位置（按作者带符号间距与首样本位置展开）
    sample_index_y = torch.arange(out_counts_y, dtype=torch.float64)
    sample_index_x = torch.arange(out_counts_x, dtype=torch.float64)
    position_y_out = sample_index_y * spacing_y_out + first_y_out
    position_x_out = sample_index_x * spacing_x_out + first_x_out

    bins_y = _dft_bins(height)
    bins_x = _dft_bins(width)
    sample_index_in_y = torch.arange(height, dtype=torch.float64)
    sample_index_in_x = torch.arange(width, dtype=torch.float64)
    forward_y = torch.exp(
        -2j
        * math.pi
        * bins_y[:, None]
        * sample_index_in_y[None, :]
        / height,
    )
    forward_x = torch.exp(
        -2j
        * math.pi
        * bins_x[:, None]
        * sample_index_in_x[None, :]
        / width,
    )
    frequency_y = (
        bins_y / (height * spacing_y_in) * sign_y
    )
    frequency_x = (
        bins_x / (width * spacing_x_in) * sign_x
    )
    frequency_grid_y, frequency_grid_x = torch.meshgrid(
        frequency_y,
        frequency_x,
        indexing="ij",
    )

    wavelengths = torch.tensor(
        field.spectrum.wavelengths,
        dtype=torch.float64,
    )
    refractive_indices = field.medium.refractive_index(wavelengths)
    path_lengths = field.path_reference.lengths
    computational_first_y = first_y_in - padding[0] * sign_y * spacing_y_in
    computational_first_x = first_x_in - padding[1] * sign_x * spacing_x_in
    outputs: list[torch.Tensor] = []
    for spectral_index, (wavelength, refractive_index) in enumerate(
        zip(wavelengths, refractive_indices, strict=True),
    ):
        wave_number = (
            2.0 * math.pi * float(refractive_index) / float(wavelength)
        )
        longitudinal_wave_number = torch.sqrt(
            wave_number**2
            - (2.0 * math.pi * frequency_grid_y) ** 2
            - (2.0 * math.pi * frequency_grid_x) ** 2,
        )
        # 倏逝分量（纵向波数平方为负）置零，与生产辐射支撑掩膜一致
        is_radiative = (
            wave_number**2
            - (2.0 * math.pi * frequency_grid_y) ** 2
            - (2.0 * math.pi * frequency_grid_x) ** 2
        ) >= 0.0
        axial_phase = torch.where(
            is_radiative,
            longitudinal_wave_number * axial_distance,
            torch.zeros_like(longitudinal_wave_number),
        )
        transfer = torch.where(
            is_radiative,
            torch.exp(1j * axial_phase),
            torch.zeros_like(axial_phase),
        )
        carrier_phase = (
            2.0
            * math.pi
            * float(path_lengths[spectral_index])
            / float(wavelength)
        )
        carrier = complex(math.cos(carrier_phase), math.sin(carrier_phase))
        polarization_outputs: list[torch.Tensor] = []
        for polarization_index in range(field.envelope.shape[-3]):
            embedded = torch.zeros((height, width), dtype=torch.complex128)
            embedded[
                padding[0] : padding[0] + input_height,
                padding[1] : padding[1] + input_width,
            ] = (
                field.envelope[spectral_index, polarization_index]
                .to(dtype=torch.complex128)
                .clone()
                * carrier
            )
            spectrum_values = forward_y @ embedded @ forward_x.T
            transferred = spectrum_values * transfer
            # 按目标位置评估逆和：1/(N_y N_x) Σ_m [...]*exp(i 2π f·(y_out, x_out))
            phase_y = (
                2.0
                * math.pi
                * frequency_y[:, None]
                * (position_y_out[None, :] - computational_first_y)
            )
            phase_x = (
                2.0
                * math.pi
                * frequency_x[:, None]
                * (position_x_out[None, :] - computational_first_x)
            )
            inverse_y = torch.exp(1j * phase_y) / height
            inverse_x = torch.exp(1j * phase_x) / width
            propagated = (
                inverse_y.T @ transferred @ inverse_x
            )
            polarization_outputs.append(propagated)
        outputs.append(torch.stack(polarization_outputs))
    return torch.stack(outputs)


def _complete_field(field: OpticalField) -> torch.Tensor:
    # 从包络与逐光谱光程参考独立重建完整复场
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


def _align_to_reference(
    source: OpticalField,
    reference: OpticalField,
) -> torch.Tensor:
    # 把源场载波对齐到参照场的逐谱光程参考，返回对齐后的包络
    return express_envelope_in_optical_path_reference(
        envelope=source.envelope,
        wavelengths=source.spectrum.wavelengths,
        source_reference_lengths=source.path_reference.lengths,
        destination_reference_lengths=reference.path_reference.lengths,
    )


def _applicability_field(
    representation: PolarizationRepresentation,
) -> OpticalField:
    grid = _grid(counts=(5, 6), spacing=(4.0e-6, 5.0e-6))
    spectrum = Spectrum.monochromatic(wavelength=0.8e-6)
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


def _applicability_destination() -> SpatialGrid:
    return _grid(counts=(4, 5), spacing=(3.0e-6, 4.0e-6))


@pytest.mark.parametrize(
    "representation",
    (PolarizationRepresentation.SCALAR, PolarizationRepresentation.TRANSVERSE),
    ids=("scalar", "transverse"),
)
def test_scaled_angular_spectrum_preserves_supported_representation(
    representation: PolarizationRepresentation,
) -> None:
    """
    带尺度角谱传播保留其支持的标量或横向表征
    """
    output = scaled_angular_spectrum(
        _applicability_field(representation),
        axial_distance=1.1e-6,
        destination_grid=_applicability_destination(),
    )
    assert output.polarization_representation is representation


def test_scaled_angular_spectrum_rejects_full_before_expensive_transform(
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
    with pytest.raises(OpticalError) as information:
        scaled_angular_spectrum(
            _applicability_field(PolarizationRepresentation.FULL),
            axial_distance=float("nan"),
            destination_grid=_applicability_destination(),
        )
    assert information.value.identity == (
        "scaled_angular_spectrum_polarization_full_unsupported"
    )
    assert all(not transform.called for transform in transforms)


class TestPhysicalInvariants:
    """
    证据层 1：物理不变量与稳定失败身份
    """

    def test_function_and_component_are_the_same_physical_action(self) -> None:
        """
        直接函数与状态组件在相同物理参数下返回同一个传播结果
        """
        grid = _grid(counts=(5, 6), spacing=(4.0e-6, 5.0e-6))
        field = _random_field(grid, _monochromatic(wavelength=0.8e-6))
        destination_grid = SpatialGrid.centered(
            sample_counts=(4, 5),
            sample_spacing=(3.0e-6, 4.0e-6),
        )
        direct_output = scaled_angular_spectrum(
            field,
            axial_distance=1.1e-6,
            destination_grid=destination_grid,
        )
        component_output = ScaledAngularSpectrum(
            axial_distance=1.1e-6,
            destination_grid=destination_grid,
        )(field)
        assert direct_output.grid.is_physically_equivalent_to(
            component_output.grid,
        )
        assert direct_output.path_reference == component_output.path_reference
        assert torch.equal(
            direct_output.envelope,
            component_output.envelope,
        )

    def test_onaxis_plane_wave_preserves_envelope_and_advances_reference(
        self,
    ) -> None:
        """
        轴向平面波残差包络恒定，均匀载波仅进入逐谱光程参考
        """
        grid = _grid()
        spectrum = _monochromatic(wavelength=2.0e-6)
        field = _constant_field(grid, spectrum, Vacuum())
        destination_grid = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(0.8e-6, 0.8e-6),
        )
        output = ScaledAngularSpectrum(
            axial_distance=3.0e-6,
            destination_grid=destination_grid,
        )(field)
        # 轴向平面波在带尺度目标上仍为均匀常幅（DC 分量只有均匀载波）
        assert torch.allclose(
            output.envelope,
            torch.ones_like(output.envelope),
            atol=1.0e-12,
        )
        assert output.path_reference.lengths == pytest.approx((3.0e-6,))

    def test_signed_distance_medium_advance_path_reference(self) -> None:
        """
        带符号距离与介质折射率共同决定光程参考推进量
        """
        grid = _grid()
        base_field = _random_field(grid, _monochromatic())
        medium = ConstantMedium(index=1.4)
        field = OpticalField(
            envelope=base_field.envelope,
            grid=base_field.grid,
            spectrum=base_field.spectrum,
            polarization_representation=(
                base_field.polarization_representation
            ),
            medium=medium,
            normalization=base_field.normalization,
            path_reference=base_field.path_reference,
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.9e-6, 0.9e-6),
        )
        propagator = ScaledAngularSpectrum(
            axial_distance=-0.75e-6,
            destination_grid=destination_grid,
        )
        output = propagator(field)
        expected_reference = (
            field.path_reference.lengths[0] + 1.4 * -0.75e-6,
        )
        assert output.path_reference.lengths == pytest.approx(
            expected_reference,
        )
        assert output.medium is medium

    def test_signed_distance_round_trip_is_identity(self) -> None:
        """
        周期外部下正负距离往返恢复原场（带限内严格幺正）
        """
        grid = _grid(counts=(64, 64), spacing=(0.5e-6, 0.5e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=3.0e-6)
        axial_distance = 4.0e-6
        forward = ScaledAngularSpectrum(
            axial_distance=axial_distance,
            destination_grid=grid,
            exterior=PropagationExterior.PERIODIC,
        )
        backward = ScaledAngularSpectrum(
            axial_distance=-axial_distance,
            destination_grid=grid,
            exterior=PropagationExterior.PERIODIC,
        )
        round_trip = backward(forward(field))
        assert torch.allclose(
            round_trip.envelope,
            field.envelope,
            atol=1.0e-12,
        )

    def test_destination_grid_is_required(self) -> None:
        """
        目标网格为必显式参数，非空间网格以稳定身份拒绝
        """
        grid = _grid()
        field = _constant_field(grid, _monochromatic())
        with pytest.raises(
            TypeError,
            match="scaled_angular_spectrum_destination_grid_invalid",
        ):
            scaled_angular_spectrum(
                field,
                axial_distance=1.0e-6,
                destination_grid="not-a-grid",  # type: ignore[arg-type]
            )
        # 目标网格在公开函数与组件构造器上均无默认值（必显式）
        function_keywords = scaled_angular_spectrum.__kwdefaults__ or {}
        assert "destination_grid" not in function_keywords

    def test_non_optical_field_input_rejected(self) -> None:
        """
        非 OpticalField 输入以稳定身份拒绝
        """
        grid = _grid()
        propagator = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=grid,
        )
        with pytest.raises(
            TypeError,
            match="scaled_angular_spectrum_field_invalid",
        ):
            propagator("not a field")  # type: ignore[arg-type]

    def test_non_finite_axial_distance_rejected_at_construction(self) -> None:
        """
        非有限轴向距离以稳定身份在构造处拒绝
        """
        grid = _grid()
        with pytest.raises(
            ValueError,
            match="scaled_angular_spectrum_axial_distance_invalid",
        ):
            ScaledAngularSpectrum(
                axial_distance=float("inf"),
                destination_grid=grid,
            )

    def test_float32_axial_distance_rejected_at_construction(self) -> None:
        """
        ScaledAngularSpectrum 在自己的边界拒绝单精度轴向距离
        """

        with pytest.raises(
            ValueError,
            match="scaled_angular_spectrum_axial_distance_invalid",
        ):
            ScaledAngularSpectrum(
                axial_distance=torch.nn.Parameter(
                    torch.tensor(2.0e-6, dtype=torch.float32),
                ),
                destination_grid=_grid(),
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
        propagator = ScaledAngularSpectrum(
            axial_distance=axial_distance,
            destination_grid=_grid(),
        )

        assert propagator.axial_distance is axial_distance
        assert (
            dict(propagator.named_parameters())["axial_distance"]
            is axial_distance
        )

    def test_zero_axial_distance_materializes_as_fixed_double_buffer(
        self,
    ) -> None:
        """
        允许的零轴向距离按 fixed-double 缓冲注册
        """

        propagator = ScaledAngularSpectrum(
            axial_distance=0.0,
            destination_grid=_grid(),
        )

        assert propagator.axial_distance.dtype is torch.float64
        assert torch.equal(
            propagator.axial_distance,
            torch.zeros((), dtype=torch.float64),
        )
        assert dict(propagator.named_buffers())["axial_distance"] is (
            propagator.axial_distance
        )

    def test_invalid_exterior_rejected(self) -> None:
        """
        非 PropagationExterior 的外部以稳定身份拒绝
        """
        grid = _grid()
        with pytest.raises(
            TypeError,
            match="scaled_angular_spectrum_exterior_invalid",
        ):
            ScaledAngularSpectrum(
                axial_distance=1.0e-6,
                destination_grid=grid,
                exterior="periodic",  # type: ignore[arg-type]
            )

    def test_orientation_mismatch_rejected(self) -> None:
        """
        目标朝向与源不一致以稳定身份拒绝（不静默翻转）
        """
        grid = _grid()
        field = _constant_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(1.0e-6, 1.0e-6),
            orientation=("decreasing", "increasing"),
        )
        propagator = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )
        with pytest.raises(
            ValueError,
            match="scaled_angular_spectrum_orientation_mismatch",
        ):
            propagator(field)

    def test_isolated_destination_outside_support_rejected(self) -> None:
        """
        孤立外部下目标足迹超出计算窗口以稳定身份拒绝
        """
        grid = _grid(counts=(8, 8), spacing=(1.0e-6, 1.0e-6))
        field = _constant_field(grid, _monochromatic())
        destination_grid = SpatialGrid(
            sample_counts=(8, 8),
            sample_spacing=(
                torch.tensor(1.0e-6, dtype=torch.float64),
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(50.0e-6, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
            ),
        )
        propagator = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.ISOLATED,
        )
        with pytest.raises(
            ValueError,
            match=(
                "scaled_angular_spectrum_"
                "isolated_destination_outside_support"
            ),
        ):
            propagator(field)

    def test_isolated_destination_noncentered_source_judged_relative_to_window(
        self,
    ) -> None:
        """
        非中心源网格下孤立外部足迹判据相对源窗口中心而非绝对原点
        """

        grid = SpatialGrid(
            sample_counts=(8, 8),
            sample_spacing=(
                torch.tensor(1.0e-6, dtype=torch.float64),
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(100.0e-6, dtype=torch.float64),
                torch.tensor(100.0e-6, dtype=torch.float64),
            ),
        )
        field = _constant_field(grid, _monochromatic())
        destination_grid = SpatialGrid(
            sample_counts=(8, 8),
            sample_spacing=(
                torch.tensor(1.0e-6, dtype=torch.float64),
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(100.0e-6, dtype=torch.float64),
                torch.tensor(100.0e-6, dtype=torch.float64),
            ),
        )
        propagator = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.ISOLATED,
        )
        output = propagator(field)
        assert output.envelope.shape == field.envelope.shape

    def test_alias_band_too_narrow_rejected_without_substitution(self) -> None:
        """
        混叠安全带窄于首个频率箱时拒绝，不静默退化或替换方法
        """
        grid = _grid(counts=(24, 24), spacing=(0.5e-6, 0.5e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=4.0e-6)
        destination_grid = SpatialGrid.centered(
            sample_counts=(24, 24),
            sample_spacing=(0.5e-6, 0.5e-6),
        )
        with pytest.raises(
            ValueError,
            match="scaled_angular_spectrum_alias_band_too_narrow",
        ):
            ScaledAngularSpectrum(
                axial_distance=1.0e-3,
                destination_grid=destination_grid,
                exterior=PropagationExterior.ISOLATED,
            )(field)

    def test_destination_sampling_too_coarse_rejected(self) -> None:
        """
        目标间距粗于传播后场逐轴带宽时以独立稳定身份拒绝（不借近轴判据）
        """
        grid = _grid(counts=(16, 16), spacing=(1.0e-6, 1.0e-6))
        spectrum = _monochromatic(wavelength=2.0e-6)
        field = _gaussian_field(grid, spectrum, waist=4.0e-6)
        destination_grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(3.0e-6, 3.0e-6),
        )
        with pytest.raises(
            ValueError,
            match="scaled_angular_spectrum_destination_sampling_too_coarse",
        ):
            scaled_angular_spectrum(
                field,
                axial_distance=2.0e-6,
                destination_grid=destination_grid,
                exterior=PropagationExterior.PERIODIC,
            )

    def test_orientation_mismatch_rejected_before_medium_query(
        self,
    ) -> None:
        """
        不适用目标几何在介质查询前先拒绝
        """

        class _CountingMedium(Medium):
            # 测试替身：记录公共 Medium 查询次数
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

            def _evaluate_refractive_index(
                self,
                wavelengths: torch.Tensor,
            ) -> torch.Tensor:
                self.query_dtypes.append(wavelengths.dtype)
                return torch.ones_like(wavelengths)

            def _physical_identity(self) -> tuple[object, ...]:
                return ("counting",)

        grid = _grid()
        medium = _CountingMedium()
        field = _constant_field(grid, _monochromatic(), medium)
        destination_grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(1.0e-6, 1.0e-6),
            orientation=("decreasing", "increasing"),
        )
        propagator = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )
        with pytest.raises(
            ValueError,
            match="scaled_angular_spectrum_orientation_mismatch",
        ):
            propagator(field)
        assert medium.query_count == 0

    def test_assembly_check_preserves_orientation_failure_identity(
        self,
    ) -> None:
        """
        Assembly.check 在运行前保留目标朝向失配的稳定身份
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
            sample_counts=(8, 8),
            sample_spacing=(1.0e-6, 1.0e-6),
            orientation=("decreasing", "increasing"),
        )
        propagator = ScaledAngularSpectrum(
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
            match="scaled_angular_spectrum_orientation_mismatch",
        ):
            assembly.check()


class TestIndependentReference:
    """
    证据层 2：独立显式 DFT 参照（覆盖尺度、平移、离轴载波、非真空介质）
    """

    @pytest.mark.parametrize(
        (
            "input_counts",
            "input_spacing",
            "destination_counts",
            "destination_spacing",
            "destination_shift",
        ),
        [
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (6, 7),
                (4.0e-6, 5.0e-6),
                (0.0, 0.0),
            ),
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (3, 4),
                (4.0e-6, 5.0e-6),
                (0.0, 0.0),
            ),
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (9, 11),
                (3.0e-6, 4.0e-6),
                (0.0, 0.0),
            ),
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (6, 7),
                (4.0e-6, 5.0e-6),
                (1.5e-6, -2.5e-6),
            ),
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (4, 5),
                (3.0e-6, 4.0e-6),
                (-1.8e-6, 2.2e-6),
            ),
        ],
        ids=(
            "unity-scale-no-shift",
            "smaller-count-same-scale",
            "finer-scale",
            "same-scale-positive-shift",
            "finer-scale-negative-shift",
        ),
    )
    def test_random_field_matches_direct_dft_reference(
        self,
        input_counts: tuple[int, int],
        input_spacing: tuple[float, float],
        destination_counts: tuple[int, int],
        destination_spacing: tuple[float, float],
        destination_shift: tuple[float, float],
    ) -> None:
        """
        随机带限复场的带尺度传播匹配显式 DFT 矩阵参照
        """
        grid = SpatialGrid.centered(
            sample_counts=input_counts,
            sample_spacing=input_spacing,
        )
        field = _random_field(grid, _monochromatic(wavelength=0.8e-6))
        first_y_in = float(grid.first_sample_position[0])
        first_x_in = float(grid.first_sample_position[1])
        destination_grid = SpatialGrid(
            sample_counts=destination_counts,
            sample_spacing=(
                torch.tensor(destination_spacing[0], dtype=torch.float64),
                torch.tensor(destination_spacing[1], dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(
                    first_y_in + destination_shift[0],
                    dtype=torch.float64,
                ),
                torch.tensor(
                    first_x_in + destination_shift[1],
                    dtype=torch.float64,
                ),
            ),
        )
        axial_distance = 1.1e-6
        output = scaled_angular_spectrum(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        reference = _direct_dft_scaled(
            field,
            destination_grid=destination_grid,
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )
        assert torch.allclose(
            _complete_field(output),
            reference,
            atol=2.0e-11,
        )

    def test_offaxis_carrier_matches_direct_dft(self) -> None:
        """
        离轴平面波载波（rad/m 与 cycles/m 分立）匹配独立参照
        """
        counts = (8, 8)
        spacing = (4.0e-6, 5.0e-6)
        grid = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=spacing,
        )
        spectrum = _monochromatic(wavelength=0.8e-6)
        bin_y, bin_x = 1, -2
        wavevector_y = 2.0 * math.pi * bin_y / (counts[0] * spacing[0])
        wavevector_x = 2.0 * math.pi * bin_x / (counts[1] * spacing[1])
        field = _tilted_field(
            grid,
            spectrum,
            (wavevector_y, wavevector_x),
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(1.6e-6, 1.4e-6),
        )
        axial_distance = 0.9e-6
        output = scaled_angular_spectrum(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        reference = _direct_dft_scaled(
            field,
            destination_grid=destination_grid,
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )
        assert torch.allclose(
            _complete_field(output),
            reference,
            atol=2.0e-11,
        )

    def test_nonvacuum_medium_matches_direct_dft(self) -> None:
        """
        非真空介质下带尺度传播匹配独立参照（介质带限单一所有者）
        """
        grid = _grid(counts=(6, 7), spacing=(4.0e-6, 5.0e-6))
        spectrum = _monochromatic(wavelength=0.8e-6)
        medium = ConstantMedium(index=1.3)
        field = _random_field(grid, spectrum, medium)
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(3.0e-6, 4.0e-6),
        )
        axial_distance = 1.6e-6
        output = scaled_angular_spectrum(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        reference = _direct_dft_scaled(
            field,
            destination_grid=destination_grid,
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )
        assert torch.allclose(
            _complete_field(output),
            reference,
            atol=2.0e-11,
        )

    def test_isolated_exterior_matches_direct_dft(self) -> None:
        """
        孤立外部下带尺度传播匹配显式 DFT（含 3 倍零延拓）
        """
        grid = _grid(counts=(6, 7), spacing=(4.0e-6, 5.0e-6))
        field = _random_field(grid, _monochromatic(wavelength=0.8e-6))
        destination_grid = SpatialGrid(
            sample_counts=(4, 5),
            sample_spacing=(
                torch.tensor(3.0e-6, dtype=torch.float64),
                torch.tensor(4.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-9.0e-6, dtype=torch.float64),
                torch.tensor(-12.0e-6, dtype=torch.float64),
            ),
        )
        axial_distance = 0.7e-6
        output = scaled_angular_spectrum(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.ISOLATED,
        )
        reference = _direct_dft_scaled(
            field,
            destination_grid=destination_grid,
            axial_distance=axial_distance,
            exterior=PropagationExterior.ISOLATED,
        )
        assert torch.allclose(
            _complete_field(output),
            reference,
            atol=2.0e-11,
        )


class TestCrossMethodComplexField:
    """
    跨方法复场证据：与现有 ScalarAngularSpectrum 在同网格目标上经 OPR 对齐后一致
    """

    def test_same_grid_matches_scalar_angular_spectrum_opr_aligned(self) -> None:
        """
        同网格目标下，本方法与 ScalarAngularSpectrum 经 OPR 对齐后复场一致
        """
        grid = _grid(counts=(6, 7), spacing=(4.0e-6, 5.0e-6))
        field = _random_field(grid, _monochromatic(wavelength=0.8e-6))
        axial_distance = 1.3e-6
        scalar_output = ScalarAngularSpectrum(
            axial_distance=axial_distance,
            exterior=PropagationExterior.PERIODIC,
        )(field)
        scaled_output = scaled_angular_spectrum(
            field,
            axial_distance=axial_distance,
            destination_grid=grid,
            exterior=PropagationExterior.PERIODIC,
        )
        aligned_scalar = _align_to_reference(scalar_output, scaled_output)
        aligned_scaled = _align_to_reference(scaled_output, scaled_output)
        peak = aligned_scalar.abs().max().item()
        # 强度对齐不足；必须比较 OPR 对齐后的完整复场
        intensity_diff = (
            (scalar_output.envelope.abs() - scaled_output.envelope.abs())
            .abs()
            .max()
            .item()
            / peak
        )
        assert torch.allclose(aligned_scaled, aligned_scalar, atol=1.0e-12)
        assert intensity_diff < 1.0e-10


class TestSamplingPaddingConvergence:
    """
    采样与补零收敛：周期/孤立外部一致；加密采样收敛（物理精度而非单网格巧合）
    """

    def test_periodic_and_isolated_agree_for_contained_field(self) -> None:
        """
        充分包含的紧致场在两种外部下中心区域须一致
        """
        counts = (32, 32)
        spacing = (0.4e-6, 0.4e-6)
        grid = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=spacing,
        )
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=3.0e-6)
        destination_grid = SpatialGrid.centered(
            sample_counts=(24, 24),
            sample_spacing=(0.4e-6, 0.4e-6),
        )
        periodic_output = ScaledAngularSpectrum(
            axial_distance=2.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )(field)
        isolated_output = ScaledAngularSpectrum(
            axial_distance=2.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.ISOLATED,
        )(field)
        peak = periodic_output.envelope.abs().max().item()
        centre_slice = (slice(None), slice(None), slice(6, 18), slice(6, 18))
        assert torch.allclose(
            periodic_output.envelope[centre_slice],
            isolated_output.envelope[centre_slice],
            atol=2.0e-3 * peak,
        )

    def test_finer_sampling_converges_to_reference(self) -> None:
        """
        加密源采样使带尺度输出向同分辨率直接参照收敛（非单网格巧合）
        """
        reference_grid = _grid(counts=(16, 16), spacing=(1.0e-6, 1.0e-6))
        spectrum = _monochromatic(wavelength=2.0e-6)
        reference_field = _gaussian_field(
            reference_grid,
            spectrum,
            waist=4.0e-6,
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(12, 12),
            sample_spacing=(1.0e-6, 1.0e-6),
        )
        reference_output = scaled_angular_spectrum(
            reference_field,
            axial_distance=2.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        finer_grid = SpatialGrid.centered(
            sample_counts=(32, 32),
            sample_spacing=(0.5e-6, 0.5e-6),
        )
        finer_field = _gaussian_field(finer_grid, spectrum, waist=4.0e-6)
        finer_output = scaled_angular_spectrum(
            finer_field,
            axial_distance=2.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        centre_slice = (slice(None), slice(None), slice(2, 10), slice(2, 10))
        peak = reference_output.envelope.abs().max().item()
        assert torch.allclose(
            finer_output.envelope[centre_slice],
            reference_output.envelope[centre_slice],
            atol=5.0e-3 * peak,
        )


class TestGradientEvidence:
    """
    证据层 3：梯度证据（双精度，可训练轴向距离）

    注意：本类的轴向距离 gradcheck 观察的是包络实部**聚合和**——轴向距离是
    平滑标量，聚合和在数值上 well-conditioned。但聚合和**不是**目标网格（间距/位置）梯度
    证据：目标网格各坐标对输出的影响在聚合上相消，单坐标导数不可由聚合和观察。目标网格
    的坐标敏感复可观测量梯度证据见 ``TestDestinationGridGradientEvidence``。
    """

    def test_gradcheck_on_trainable_axial_distance(self) -> None:
        """
        对可训练轴向距离做 gradcheck（经传播→包络实部和）

        这是轴向距离（平滑标量）证据，**非**目标网格证据（见类 docstring）。
        """
        grid = _grid(counts=(10, 10), spacing=(0.6e-6, 0.6e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=2.4e-6)
        axial_distance = torch.nn.Parameter(
            torch.tensor(2.0e-6, dtype=torch.float64),
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.5e-6, 0.5e-6),
        )
        propagator = ScaledAngularSpectrum(
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )

        def run(distance_value: torch.Tensor) -> torch.Tensor:
            """
            返回当前轴向距离下的输出包络实部和
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
        grid = _grid(counts=(10, 10), spacing=(0.6e-6, 0.6e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(grid, spectrum, waist=2.2e-6)
        axial_distance = torch.nn.Parameter(
            torch.tensor(3.0e-6, dtype=torch.float64),
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.5e-6, 0.5e-6),
        )
        propagator = ScaledAngularSpectrum(
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        detector = IntensityDetection()

        def observe(distance_value: torch.Tensor) -> torch.Tensor:
            """
            返回离中心一个采样位置处的传播光强
            """
            assert distance_value is axial_distance
            return detector(propagator(field)).values[3, 5]

        observed = observe(axial_distance)
        gradient = torch.autograd.grad(observed, axial_distance)[0]
        assert bool(torch.isfinite(gradient))
        assert abs(float(gradient)) > 1.0e-6


class TestDestinationGridGradientEvidence:
    """
    证据层 3b：目标网格（间距/位置）坐标敏感复可观测量梯度证据

    与轴向距离不同，目标网格坐标对输出的影响在包络实部聚合和上相消（显式逆 DFT 的
    相消残差），故聚合和不可作目标网格梯度证据。本类观察单个离轴、非边缘目标像素的
    复包络（坐标敏感、无聚合相消），其 ``real`` 与 ``imag`` 两个实标量分别对目标间距/
    位置求 ``autograd`` 反向梯度，并与同一前向的独立中心差分比对（反向解析与正向数值
    摄动两条独立方法交叉确认）。几何选在远离非光滑适用边界（采样充分细于
    ``λ/(2n)``、中等轴向距离、周期外部、紧致高斯场）。

    显式声明的不可训练结构网格事实：目标 ``sample_counts``（int）与 ``orientation``
    （str 元组）非可微；中心对齐网格的 ``first_sample_position`` 由间距导出（非独立
    量），故位置梯度必须用显式非中心网格（见 ``test_destination_position_gradient``）。
    """

    _OBSERVE_PIXEL: tuple[int, int] = (6, 7)
    _FINITE_DIFF_STEP: float = 1.0e-9

    def _well_contained_geometry(
        self,
        *,
        destination_spacing_y: torch.Tensor,
        destination_spacing_x: torch.Tensor,
        destination_first_y: torch.Tensor,
        destination_first_x: torch.Tensor,
    ) -> tuple[OpticalField, SpatialGrid]:
        source_grid = _grid(counts=(16, 16), spacing=(0.5e-6, 0.5e-6))
        spectrum = _monochromatic(wavelength=1.0e-6)
        field = _gaussian_field(source_grid, spectrum, waist=3.0e-6)
        destination_grid = SpatialGrid(
            sample_counts=(10, 10),
            sample_spacing=(
                destination_spacing_y,
                destination_spacing_x,
            ),
            first_sample_position=(destination_first_y, destination_first_x),
        )
        return field, destination_grid

    def _propagate(
        self,
        field: OpticalField,
        destination_grid: SpatialGrid,
    ) -> torch.Tensor:
        # 固定轴向距离的带尺度传播，返回目标包络（保持计算图）
        output = scaled_angular_spectrum(
            field,
            axial_distance=2.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        return output.envelope

    def _destination_grid_value_at(
        self,
        *,
        spacing_y: float,
        spacing_x: float,
        first_y: float,
        first_x: float,
    ) -> torch.Tensor:
        # 以给定标量目标网格参数构造一次前向，返回观察像素的复包络标量（detach）
        spacing_y_tensor = torch.tensor(spacing_y, dtype=torch.float64)
        spacing_x_tensor = torch.tensor(spacing_x, dtype=torch.float64)
        first_y_tensor = torch.tensor(first_y, dtype=torch.float64)
        first_x_tensor = torch.tensor(first_x, dtype=torch.float64)
        field, destination_grid = self._well_contained_geometry(
            destination_spacing_y=spacing_y_tensor,
            destination_spacing_x=spacing_x_tensor,
            destination_first_y=first_y_tensor,
            destination_first_x=first_x_tensor,
        )
        envelope = self._propagate(field, destination_grid)
        py, px = self._OBSERVE_PIXEL
        return envelope[0, 0, py, px].detach()

    def _central_difference(
        self,
        *,
        spacing_y: float,
        spacing_x: float,
        first_y: float,
        first_x: float,
        coordinate: str,
        step: float,
    ) -> tuple[float, float]:
        # 同一前向的独立中心差分（正向数值摄动），返回观察像素 real/imag 两分量的梯度
        coordinate_value = {
            "spacing_y": spacing_y,
            "spacing_x": spacing_x,
            "first_y": first_y,
            "first_x": first_x,
        }[coordinate]
        plus = dict(
            spacing_y=spacing_y,
            spacing_x=spacing_x,
            first_y=first_y,
            first_x=first_x,
        )
        minus = dict(plus)
        plus[coordinate] = coordinate_value + step
        minus[coordinate] = coordinate_value - step
        plus_value = self._destination_grid_value_at(**plus)
        minus_value = self._destination_grid_value_at(**minus)
        real = (float(plus_value.real) - float(minus_value.real)) / (2.0 * step)
        imag = (float(plus_value.imag) - float(minus_value.imag)) / (2.0 * step)
        return real, imag

    def test_structural_grid_facts_are_deliberately_non_trainable(self) -> None:
        """
        目标 sample_counts(int) 与 orientation(str 元组) 非可微；中心对齐网格的
        first_sample_position 由间距导出（非独立量）
        """

        grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.4e-6, 0.4e-6),
        )
        counts_y, counts_x = grid.sample_counts
        # sample_counts 是 Python int（结构事实），非可微张量
        assert isinstance(counts_y, int)
        assert isinstance(counts_x, int)
        # orientation 是 str 元组（结构事实），非可微张量
        assert isinstance(grid.orientation, tuple)
        assert all(isinstance(axis, str) for axis in grid.orientation)
        assert grid._first_sample_position is None  # noqa: SLF001
        # 派生性证据：把间距加倍，first_sample_position 按同一倍数改变（中心对齐约定）
        grid_doubled = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.8e-6, 0.8e-6),
        )
        ratio = (
            grid_doubled.first_sample_position[0]
            / grid.first_sample_position[0]
        )
        assert torch.isclose(ratio, torch.tensor(2.0, dtype=torch.float64))

    def test_destination_spacing_gradient_matches_central_difference(self) -> None:
        """
        目标 y 间距为可训练叶子：单离轴像素 real/imag 的 autograd 与独立中心差分一致
        （远离非光滑边界；聚合和不可作此证据——显式逆 DFT 上相消）
        """

        spacing_y = torch.tensor(0.4e-6, dtype=torch.float64, requires_grad=True)
        spacing_x = torch.tensor(0.4e-6, dtype=torch.float64)
        first_y = torch.tensor(-1.8e-6, dtype=torch.float64)
        first_x = torch.tensor(-1.8e-6, dtype=torch.float64)
        field, destination_grid = self._well_contained_geometry(
            destination_spacing_y=spacing_y,
            destination_spacing_x=spacing_x,
            destination_first_y=first_y,
            destination_first_x=first_x,
        )
        envelope = self._propagate(field, destination_grid)
        py, px = self._OBSERVE_PIXEL
        pixel = envelope[0, 0, py, px]
        # real 与 imag 两个坐标敏感实标量分别反向：覆盖复可观测量两分量
        real_grad = torch.autograd.grad(
            pixel.real,
            spacing_y,
            retain_graph=True,
        )[0]
        imag_grad = torch.autograd.grad(pixel.imag, spacing_y)[0]
        assert torch.isfinite(real_grad)
        assert torch.isfinite(imag_grad)
        central_real, central_imag = self._central_difference(
            spacing_y=0.4e-6,
            spacing_x=0.4e-6,
            first_y=-1.8e-6,
            first_x=-1.8e-6,
            coordinate="spacing_y",
            step=self._FINITE_DIFF_STEP,
        )
        assert math.isclose(
            float(real_grad),
            central_real,
            rel_tol=1.0e-4,
            abs_tol=1.0e2,
        )
        assert math.isclose(
            float(imag_grad),
            central_imag,
            rel_tol=1.0e-4,
            abs_tol=1.0e2,
        )

    def test_destination_position_gradient_matches_central_difference(self) -> None:
        """
        显式（非中心）目标网格的 first_sample_position_y 为可训练叶子：单离轴像素
        real/imag 的 autograd 与独立中心差分一致

        位置梯度必须用显式非中心网格——中心网格的 first_sample_position 由间距导出，
        无独立位置梯度（用中心网格会是测试设计错误，见结构事实测试）。
        """

        spacing_y = torch.tensor(0.4e-6, dtype=torch.float64)
        spacing_x = torch.tensor(0.4e-6, dtype=torch.float64)
        first_y = torch.tensor(-1.8e-6, dtype=torch.float64, requires_grad=True)
        first_x = torch.tensor(-1.8e-6, dtype=torch.float64)
        field, destination_grid = self._well_contained_geometry(
            destination_spacing_y=spacing_y,
            destination_spacing_x=spacing_x,
            destination_first_y=first_y,
            destination_first_x=first_x,
        )
        # 显式非中心网格：first_sample_position 是独立存储叶子（非由间距导出）
        assert destination_grid._first_sample_position is not None  # noqa: SLF001
        envelope = self._propagate(field, destination_grid)
        py, px = self._OBSERVE_PIXEL
        pixel = envelope[0, 0, py, px]
        real_grad = torch.autograd.grad(
            pixel.real,
            first_y,
            retain_graph=True,
        )[0]
        imag_grad = torch.autograd.grad(pixel.imag, first_y)[0]
        assert torch.isfinite(real_grad)
        assert torch.isfinite(imag_grad)
        central_real, central_imag = self._central_difference(
            spacing_y=0.4e-6,
            spacing_x=0.4e-6,
            first_y=-1.8e-6,
            first_x=-1.8e-6,
            coordinate="first_y",
            step=self._FINITE_DIFF_STEP,
        )
        assert math.isclose(
            float(real_grad),
            central_real,
            rel_tol=1.0e-4,
            abs_tol=1.0e2,
        )
        assert math.isclose(
            float(imag_grad),
            central_imag,
            rel_tol=1.0e-4,
            abs_tol=1.0e2,
        )


class TestComponentState:
    """
    组件状态、精度与设备行为
    """

    def test_loaded_fixed_distance_matches_fresh_component(self) -> None:
        """
        固定轴向距离经公共状态加载改变后仍匹配相同状态的全新组件
        """
        grid = _grid(counts=(6, 7), spacing=(4.0e-6, 5.0e-6))
        field = _random_field(grid, _monochromatic(wavelength=0.8e-6))
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(3.0e-6, 4.0e-6),
        )
        reused = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )
        reused(field)
        changed_state = ScaledAngularSpectrum(
            axial_distance=1.4e-6,
            destination_grid=destination_grid,
        ).state_dict()
        reused.load_state_dict(changed_state)
        output = reused(field)
        fresh_output = ScaledAngularSpectrum(
            axial_distance=1.4e-6,
            destination_grid=destination_grid,
        )(field)
        assert output.path_reference == fresh_output.path_reference
        assert torch.allclose(
            output.envelope,
            fresh_output.envelope,
        )

    def test_destination_grid_roundtrips_through_state_dict(self) -> None:
        """
        目标网格随传播元件 state_dict 一同恢复
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
        source = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=source_grid,
        )
        restored = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=restored_grid,
        )
        restored.load_state_dict(source.state_dict())
        assert restored.destination_grid.is_physically_equivalent_to(
            source.destination_grid,
        )

    def test_unhosted_cuda_field_owns_transfer_device(self) -> None:
        """
        CUDA 输入可驱动未托管组件在同一设备计算
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
        destination_grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.9e-6, 0.9e-6),
        )
        propagator = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )
        output = propagator(field)
        fresh_output = ScaledAngularSpectrum(
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )(field)
        assert output.envelope.device == field.envelope.device
        assert output.envelope.dtype is field.envelope.dtype
        assert output.path_reference == fresh_output.path_reference
        assert torch.allclose(output.envelope, fresh_output.envelope)

    @pytest.mark.cuda
    def test_public_action_matches_cpu_on_cuda(self) -> None:
        """
        公共动作在 CUDA 上保持与 CPU 相同的复包络与带尺度目标网格
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
        destination_grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.9e-6, 0.9e-6),
        )
        cpu_output = scaled_angular_spectrum(
            base,
            axial_distance=1.0e-6,
            destination_grid=destination_grid,
        )
        cuda_output = scaled_angular_spectrum(
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
        assert cpu_output.grid.sample_counts == (8, 8)
        assert cuda_output.grid.sample_counts == (8, 8)
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


class TestHostedFocusing:
    """
    托管端到端：PlaneWave → 圆光瞳 → 理想薄透镜 → ScaledAngularSpectrum → 探测
    """

    def test_scaled_focal_plane_central_peak(self) -> None:
        """
        带尺度焦平面传播 ⇒ 光强全局峰位于中心且远高于均值
        """
        counts = (32, 32)
        spacing = (1.0e-6, 1.0e-6)
        grid = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=spacing,
        )
        spectrum = _monochromatic(wavelength=1.0e-6)
        focal_length = 40.0e-6
        aperture_radius = 8.0e-6
        destination_grid = SpatialGrid.centered(
            sample_counts=(24, 24),
            sample_spacing=(0.8e-6, 0.8e-6),
        )
        workstation = Workstation.cpu()
        from chromatix_next.optics.element import CircularPupil, IdealThinLens

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
            ScaledAngularSpectrum(
                axial_distance=focal_length,
                destination_grid=destination_grid,
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
        flat_argmax = int(values.argmax().item())
        peak_y = flat_argmax // values.shape[-1]
        peak_x = flat_argmax % values.shape[-1]
        assert abs(peak_y - centre[0]) <= 1
        assert abs(peak_x - centre[1]) <= 1
        central_value = values[centre[0], centre[1]].item()
        mean_value = values.mean().item()
        assert central_value > 5.0 * mean_value

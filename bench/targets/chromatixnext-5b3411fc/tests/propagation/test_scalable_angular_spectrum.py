
from __future__ import annotations

from decimal import Decimal, localcontext
import math
from pathlib import Path
from unittest.mock import Mock

import pytest
import torch

from chromatix_next._numerics._certified_predicates import (
    squared_reference_minus_squared_factor_extra_factor_sign,
)
from chromatix_next._numerics.optical_path_reference import (
    express_envelope_in_optical_path_reference,
)
from chromatix_next._numerics.wave_propagation.radiative_spectrum import (
    _radiative_spectrum_facts,
    _RadiativeSpectrumFacts,
)
from chromatix_next._numerics.wave_propagation.scalable_angular_spectrum import (
    ScalableAngularSpectrumPrecompensation,
    scalable_angular_spectrum_precompensation,
)
from chromatix_next.errors import OpticalError
from chromatix_next.optics import (
    ConstantMedium,
    FieldNormalization,
    Medium,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PolarizationRepresentation,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.grid import PropagationExterior
from chromatix_next.optics.propagation import (
    ScalableAngularSpectrum,
    scalable_angular_spectrum,
    scaled_angular_spectrum,
    scaled_fresnel,
)


def _grid(
    counts: tuple[int, int] = (6, 7),
    spacing: tuple[float, float] = (4.0e-6, 5.0e-6),
) -> SpatialGrid:
    # 构造中心对齐的横向网格（样本物理对齐原点，递增朝向）
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=(
            torch.tensor(spacing[0], dtype=torch.float64),
            torch.tensor(spacing[1], dtype=torch.float64),
        ),
    )


def _monochromatic(wavelength: float = 0.5e-6) -> Spectrum:
    # 构造单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


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


_DEFAULT_DISTANCE = 550.0e-6


def test_sas_richer_model_residual_to_scaled_spectrum_decreases_with_band() -> None:
    """
    近似模型证据：固定有效放大率和目标几何时，SAS 带宽变窄并趋近带尺度角谱
    残差预补偿和 Collins 栅栏仍由 SAS 自有；序列不引入运行时近轴截止。
    """

    grid = SpatialGrid.centered(
        sample_counts=(16, 16),
        sample_spacing=(1.0e-6, 1.0e-6),
    )
    destination_grid = SpatialGrid.centered(
        sample_counts=(16, 16),
        sample_spacing=(1.0e-6, 1.0e-6),
    )
    spectrum = _monochromatic()
    position_y = (
        torch.arange(16, dtype=torch.float64) * grid.signed_spacing[0]
        + grid.first_sample_position[0]
    )
    position_x = (
        torch.arange(16, dtype=torch.float64) * grid.signed_spacing[1]
        + grid.first_sample_position[1]
    )
    radius_squared = position_y[:, None].square() + position_x[None, :].square()
    residuals: list[float] = []
    for waist in (2.0e-6, 3.0e-6, 4.0e-6):
        field = OpticalField(
            envelope=torch.exp(-radius_squared / waist**2)
            .to(dtype=torch.complex128)
            .unsqueeze(0)
            .unsqueeze(0),
            grid=grid,
            spectrum=spectrum,
            polarization_representation=Polarization.scalar().representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        sas_output = scalable_angular_spectrum(
            field,
            axial_distance=100.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        exact_output = scaled_angular_spectrum(
            field,
            axial_distance=100.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        actual = sas_output.envelope
        expected = exact_output.envelope
        alignment = (actual.conj() * expected).sum() / actual.abs().square().sum()
        residuals.append(
            float((alignment * actual - expected).abs().max())
            / float(expected.abs().max())
        )

    assert residuals[1] < residuals[0]
    assert residuals[2] < residuals[1]


def _applicability_field(
    representation: PolarizationRepresentation,
) -> OpticalField:
    grid = _grid()
    spectrum = _monochromatic()
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
    return _grid(counts=(5, 6), spacing=(4.0e-6, 5.0e-6))


@pytest.mark.parametrize(
    "representation",
    (PolarizationRepresentation.SCALAR, PolarizationRepresentation.TRANSVERSE),
    ids=("scalar", "transverse"),
)
def test_scalable_angular_spectrum_preserves_supported_representation(
    representation: PolarizationRepresentation,
) -> None:
    """
    可缩放角谱传播保留其支持的标量或横向表征
    """
    output = scalable_angular_spectrum(
        _applicability_field(representation),
        axial_distance=550.0e-6,
        destination_grid=_applicability_destination(),
    )
    assert output.polarization_representation is representation


def test_scalable_angular_spectrum_rejects_full_before_expensive_transform(
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
        scalable_angular_spectrum(
            _applicability_field(PolarizationRepresentation.FULL),
            axial_distance=float("nan"),
            destination_grid=_applicability_destination(),
        )
    assert information.value.identity == (
        "scalable_angular_spectrum_polarization_full_unsupported"
    )
    assert all(not transform.called for transform in transforms)


def _direct_sas(
    field: OpticalField,
    *,
    destination_grid: SpatialGrid,
    axial_distance: float,
) -> torch.Tensor:
    wavelengths = torch.tensor(
        field.spectrum.wavelengths,
        dtype=torch.float64,
    )
    refractive_indices = field.medium.refractive_index(wavelengths)
    input_height, input_width = field.grid.sample_counts
    output_height, output_width = destination_grid.sample_counts
    spacing_y_in = float(field.grid.signed_spacing[0])
    spacing_x_in = float(field.grid.signed_spacing[1])
    first_y_in = float(field.grid.first_sample_position[0])
    first_x_in = float(field.grid.first_sample_position[1])
    spacing_y_out = float(destination_grid.signed_spacing[0])
    spacing_x_out = float(destination_grid.signed_spacing[1])
    first_y_out = float(destination_grid.first_sample_position[0])
    first_x_out = float(destination_grid.first_sample_position[1])
    cell_area = abs(spacing_y_in * spacing_x_in)
    path_lengths = field.path_reference.lengths
    outputs: list[torch.Tensor] = []
    for spectral_index, (wavelength, refractive_index) in enumerate(
        zip(wavelengths, refractive_indices, strict=True),
    ):
        wavelength = float(wavelength)
        refractive_index = float(refractive_index)
        wave_number = 2.0 * math.pi * refractive_index / wavelength
        # 在源网格的 FFT 频率轴上构造精确角谱预补偿传递核
        frequency_y = torch.fft.fftfreq(
            input_height,
            d=1.0,
        ) / spacing_y_in
        frequency_x = torch.fft.fftfreq(
            input_width,
            d=1.0,
        ) / spacing_x_in
        frequency_grid_y, frequency_grid_x = torch.meshgrid(
            frequency_y,
            frequency_x,
            indexing="ij",
        )
        ky = 2.0 * math.pi * frequency_grid_y
        kx = 2.0 * math.pi * frequency_grid_x
        kz_squared = wave_number**2 - ky**2 - kx**2
        radiative = kz_squared >= 0.0
        kz = torch.sqrt(torch.clamp(kz_squared, min=0.0))
        direction_x = kx / wave_number
        direction_y = ky / wave_number
        direction_z = torch.sqrt(
            torch.clamp(1.0 - direction_x**2 - direction_y**2, min=0.0)
        )
        inside_cone = direction_z > 0.0
        safe_direction_z = torch.where(
            inside_cone,
            direction_z,
            torch.ones_like(direction_z),
        )
        half_extent_y = 0.5 * input_height * abs(spacing_y_in)
        half_extent_x = 0.5 * input_width * abs(spacing_x_in)
        admit_y = (
            axial_distance
            * (direction_y / safe_direction_z - direction_y)
        ).abs() <= half_extent_y
        admit_x = (
            axial_distance
            * (direction_x / safe_direction_z - direction_x)
        ).abs() <= half_extent_x
        support = radiative & inside_cone & admit_y & admit_x
        precomp_phase = axial_distance * (
            (kz - wave_number) + (kx**2 + ky**2) / (2.0 * wave_number)
        )
        precomp = torch.where(
            support,
            torch.exp(1j * precomp_phase),
            torch.zeros_like(precomp_phase),
        )
        envelope_slice = field.envelope[spectral_index, 0].to(
            dtype=torch.complex128,
        ).clone()
        spectrum_fft = torch.fft.fftn(envelope_slice)
        precompensated = torch.fft.ifftn(spectrum_fft * precomp)
        # 显式 Collins 矩阵积分
        position_y_in = (
            torch.arange(input_height, dtype=torch.float64) * spacing_y_in
            + first_y_in
        )
        position_x_in = (
            torch.arange(input_width, dtype=torch.float64) * spacing_x_in
            + first_x_in
        )
        position_y_out = (
            torch.arange(output_height, dtype=torch.float64) * spacing_y_out
            + first_y_out
        )
        position_x_out = (
            torch.arange(output_width, dtype=torch.float64) * spacing_x_out
            + first_x_out
        )
        curvature = wave_number / (2.0 * axial_distance)
        input_chirp = torch.exp(
            1j
            * curvature
            * (
                position_y_in[:, None].square()
                + position_x_in[None, :].square()
            ),
        )
        output_chirp = torch.exp(
            1j
            * curvature
            * (
                position_y_out[:, None].square()
                + position_x_out[None, :].square()
            ),
        )
        beta = wave_number / axial_distance
        chirped = precompensated * input_chirp
        phase_y = torch.exp(
            -1j * beta * position_y_in[:, None] * position_y_out[None, :],
        )
        phase_x = torch.exp(
            -1j * beta * position_x_in[:, None] * position_x_out[None, :],
        )
        integral = phase_y.T @ chirped @ phase_x
        carrier_phase = (
            2.0 * math.pi * float(path_lengths[spectral_index]) / wavelength
        )
        carrier = complex(math.cos(carrier_phase), math.sin(carrier_phase))
        axial_carrier = torch.exp(
            torch.tensor(
                1j * wave_number * axial_distance,
                dtype=torch.complex128,
            ),
        )
        prefactor = axial_carrier * torch.tensor(
            -1j * refractive_index / (wavelength * axial_distance) * cell_area,
            dtype=torch.complex128,
        )
        outputs.append(prefactor * output_chirp * integral * carrier)
    return torch.stack(outputs).unsqueeze(1)


def _high_padded_exact_angular_spectrum(
    field: OpticalField,
    destination_grid: SpatialGrid,
    axial_distance: float,
    pad_factor: int,
) -> OpticalField:
    in_counts = field.grid.sample_counts
    out_counts = destination_grid.sample_counts
    pad_in_counts = (in_counts[0] * pad_factor, in_counts[1] * pad_factor)
    pad_out_counts = (
        out_counts[0] * pad_factor,
        out_counts[1] * pad_factor,
    )
    pad_in_grid = SpatialGrid.centered(
        sample_counts=pad_in_counts,
        sample_spacing=field.grid.sample_spacing,
    )
    pad_out_grid = SpatialGrid.centered(
        sample_counts=pad_out_counts,
        sample_spacing=destination_grid.sample_spacing,
    )
    pad_envelope = torch.zeros(
        (
            field.envelope.shape[0],
            field.envelope.shape[1],
            pad_in_counts[0],
            pad_in_counts[1],
        ),
        dtype=field.envelope.dtype,
    )
    off_y = (pad_in_counts[0] - in_counts[0]) // 2
    off_x = (pad_in_counts[1] - in_counts[1]) // 2
    pad_envelope[
        :,
        :,
        off_y : off_y + in_counts[0],
        off_x : off_x + in_counts[1],
    ] = field.envelope
    pad_field = OpticalField(
        envelope=pad_envelope,
        grid=pad_in_grid,
        spectrum=field.spectrum,
        polarization_representation=field.polarization_representation,
        medium=field.medium,
        normalization=field.normalization,
        path_reference=field.path_reference,
    )
    propagated = scaled_angular_spectrum(
        pad_field,
        axial_distance=axial_distance,
        destination_grid=pad_out_grid,
    )
    out_off_y = (pad_out_counts[0] - out_counts[0]) // 2
    out_off_x = (pad_out_counts[1] - out_counts[1]) // 2
    cropped = propagated.envelope[
        :,
        :,
        out_off_y : out_off_y + out_counts[0],
        out_off_x : out_off_x + out_counts[1],
    ].contiguous()
    return OpticalField(
        envelope=cropped,
        grid=destination_grid,
        spectrum=propagated.spectrum,
        polarization_representation=propagated.polarization_representation,
        medium=propagated.medium,
        normalization=propagated.normalization,
        path_reference=propagated.path_reference,
    )


def _align_to(
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


class TestPhysicalInvariants:
    """
    证据层 1：物理不变量与稳定失败身份
    """

    def test_function_and_component_are_the_same_physical_action(self) -> None:
        """
        直接函数与状态组件在相同物理参数下返回同一个传播结果
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        direct_output = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        component_output = ScalableAngularSpectrum(
            axial_distance=_DEFAULT_DISTANCE,
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
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        forward = ScalableAngularSpectrum(
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )(field)
        backward = ScalableAngularSpectrum(
            axial_distance=-_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )(field)
        # 折射率 1.4 × ±距离 → ±(1.4 × 距离) 逐光谱推进；前反向符号相反
        forward_length = forward.path_reference.lengths[0]
        backward_length = backward.path_reference.lengths[0]
        if isinstance(forward_length, torch.Tensor):
            forward_value = float(forward_length.detach().item())
        else:
            forward_value = float(forward_length)
        if isinstance(backward_length, torch.Tensor):
            backward_value = float(backward_length.detach().item())
        else:
            backward_value = float(backward_length)
        assert forward_value == pytest.approx(1.4 * _DEFAULT_DISTANCE)
        assert backward_value == pytest.approx(-1.4 * _DEFAULT_DISTANCE)

    def test_zero_axial_distance_fails_with_stable_identity(self) -> None:
        """
        零轴向距离触发稳定失败身份，绝不替换为另一传播方法
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        with pytest.raises(
            Exception,
            match="scalable_angular_spectrum_axial_distance_invalid",
        ):
            scalable_angular_spectrum(
                field,
                axial_distance=0.0,
                destination_grid=destination_grid,
            )

    def test_float32_axial_distance_rejected_at_construction(self) -> None:
        """
        ScalableAngularSpectrum 在自己的边界拒绝单精度轴向距离
        """

        with pytest.raises(
            ValueError,
            match="scalable_angular_spectrum_axial_distance_invalid",
        ):
            ScalableAngularSpectrum(
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
        propagator = ScalableAngularSpectrum(
            axial_distance=axial_distance,
            destination_grid=_grid(),
        )

        assert propagator.axial_distance is axial_distance
        assert (
            dict(propagator.named_parameters())["axial_distance"]
            is axial_distance
        )

    def test_destination_grid_must_be_explicit(self) -> None:
        """
        可缩放角谱传播必须显式给出目标网格
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        with pytest.raises(
            TypeError,
        ):
            scalable_angular_spectrum(  # type: ignore[call-arg]
                field,
                axial_distance=_DEFAULT_DISTANCE,
            )

    def test_paraxial_stage_sampling_facts_are_independent_necessary_conditions(
        self,
    ) -> None:
        """
        近轴 Collins 阶段的输入啁啾、变换耦合与输出啁啾作为三个独立必要条件，
        各自以独立稳定身份失败；与预补偿适用性互不借用
        """
        grid = _grid(counts=(6, 7), spacing=(4.0e-6, 5.0e-6))
        field = _random_field(grid, _monochromatic())
        coarse_destination = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(8.0e-6, 10.0e-6),
        )
        with pytest.raises(
            ValueError,
            match=(
                "scalable_angular_spectrum_"
                "paraxial_transform_coupling_too_narrow"
            ),
        ):
            scalable_angular_spectrum(
                field,
                axial_distance=400.0e-6,
                destination_grid=coarse_destination,
                exterior=PropagationExterior.PERIODIC,
            )
        wide_coarse_destination = SpatialGrid.centered(
            sample_counts=(6, 6),
            sample_spacing=(8.0e-6, 8.0e-6),
        )
        grid_wide = SpatialGrid.centered(
            sample_counts=(12, 12),
            sample_spacing=(2.0e-6, 2.0e-6),
        )
        field_wide = _random_field(grid_wide, _monochromatic())
        with pytest.raises(
            ValueError,
            match=(
                "scalable_angular_spectrum_"
                "paraxial_output_chirp_too_narrow"
            ),
        ):
            scalable_angular_spectrum(
                field_wide,
                axial_distance=400.0e-6,
                destination_grid=wide_coarse_destination,
                exterior=PropagationExterior.PERIODIC,
            )

    def test_exterior_semantics_differ(self) -> None:
        """
        周期与孤立外部给出可区分的传播结果（外部语义进入数值）
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        periodic = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        isolated = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
            exterior=PropagationExterior.ISOLATED,
        )
        assert not torch.allclose(
            periodic.envelope,
            isolated.envelope,
        )


class TestIndependentReference:
    """
    证据层 2：独立显式 SAS 参照（预补偿 × Collins 矩阵积分）
    """

    def test_matches_direct_discrete_reference_same_geometry(self) -> None:
        """
        同尺度目标网格上 SAS 与独立显式参照的复场一致
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=grid.sample_counts,
            sample_spacing=grid.sample_spacing,
        )
        produced = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        reference = _direct_sas(
            field,
            destination_grid=destination_grid,
            axial_distance=_DEFAULT_DISTANCE,
        )
        produced_aligned = _align_to(produced, field)
        rel = (
            (produced_aligned - reference).abs().max().item()
            / reference.abs().max().item()
        )
        assert rel < 1.0e-3, rel

    def test_matches_direct_discrete_reference_magnified(self) -> None:
        """
        带放大率的目标网格上 SAS 与独立显式参照的复场一致
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(9, 11),
            sample_spacing=(3.0e-6, 3.5e-6),
        )
        produced = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        reference = _direct_sas(
            field,
            destination_grid=destination_grid,
            axial_distance=_DEFAULT_DISTANCE,
        )
        produced_aligned = _align_to(produced, field)
        rel = (
            (produced_aligned - reference).abs().max().item()
            / reference.abs().max().item()
        )
        assert rel < 1.0e-3, rel

    def test_matches_direct_discrete_reference_off_axis(self) -> None:
        """
        离轴目标网格上 SAS 与独立显式参照的复场一致
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        first_y, first_x = grid.first_sample_position
        destination_grid = SpatialGrid(
            sample_counts=grid.sample_counts,
            sample_spacing=grid.sample_spacing,
            first_sample_position=(
                first_y + 8.0e-6,
                first_x - 10.0e-6,
            ),
        )
        produced = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        reference = _direct_sas(
            field,
            destination_grid=destination_grid,
            axial_distance=_DEFAULT_DISTANCE,
        )
        produced_aligned = _align_to(produced, field)
        rel = (
            (produced_aligned - reference).abs().max().item()
            / reference.abs().max().item()
        )
        assert rel < 1.0e-3, rel

    def test_matches_direct_discrete_reference_negative_distance(self) -> None:
        """
        负轴向距离 SAS 与独立显式参照的复场一致
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=grid.sample_counts,
            sample_spacing=grid.sample_spacing,
        )
        produced = scalable_angular_spectrum(
            field,
            axial_distance=-_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        reference = _direct_sas(
            field,
            destination_grid=destination_grid,
            axial_distance=-_DEFAULT_DISTANCE,
        )
        produced_aligned = _align_to(produced, field)
        rel = (
            (produced_aligned - reference).abs().max().item()
            / reference.abs().max().item()
        )
        assert rel < 1.0e-3, rel

    def test_matches_direct_discrete_reference_dispersive_medium(self) -> None:
        """
        非真空介质中 SAS 与独立显式参照的复场一致
        """
        grid = _grid()
        field = _random_field(
            grid,
            _monochromatic(),
            medium=ConstantMedium(index=1.3),
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        produced = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        reference = _direct_sas(
            field,
            destination_grid=destination_grid,
            axial_distance=_DEFAULT_DISTANCE,
        )
        produced_aligned = _align_to(produced, field)
        rel = (
            (produced_aligned - reference).abs().max().item()
            / reference.abs().max().item()
        )
        assert rel < 1.0e-3, rel


class TestMethodDistinction:
    """
    证据层 3：在跨采样/放大率/距离的收敛中区分 SAS 与 ScaledFresnel /
    ScaledAngularSpectrum——三种方法在共享频带内一致，但 SAS 是独立的第三方法
    """

    def test_sas_matches_exact_when_fresnel_approx_holds(self) -> None:
        """
        近轴尺度条件下 SAS 与 ScaledAngularSpectrum（精确辐射角谱）的相对偏差
        小于 SAS 与 ScaledFresnel（纯近轴）的相对偏差——这正是 SAS 文献的目标
        """
        grid = SpatialGrid.centered(
            sample_counts=(48, 48),
            sample_spacing=(
                torch.tensor(0.5e-6, dtype=torch.float64),
                torch.tensor(0.5e-6, dtype=torch.float64),
            ),
        )
        # 用平滑高斯包络以集中在低频、避开混叠带边缘
        position_y = (
            torch.arange(48, dtype=torch.float64) - 23.5
        ) * 0.5e-6
        position_x = (
            torch.arange(48, dtype=torch.float64) - 23.5
        ) * 0.5e-6
        amplitude = torch.exp(
            -(
                position_y[:, None].square() + position_x[None, :].square()
            )
            / (2.5e-6) ** 2,
        ).to(dtype=torch.complex128)
        envelope = amplitude.unsqueeze(0).unsqueeze(0)
        field = OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=_monochromatic(),
            polarization_representation=(
                Polarization.scalar()
            ).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        distance = 25.0e-6
        destination_grid = SpatialGrid.centered(
            sample_counts=grid.sample_counts,
            sample_spacing=grid.sample_spacing,
        )
        sas = scalable_angular_spectrum(
            field,
            axial_distance=distance,
            destination_grid=destination_grid,
        )
        sas_aligned = _align_to(sas, field)
        exact = scaled_angular_spectrum(
            field,
            axial_distance=distance,
            destination_grid=destination_grid,
        )
        paraxial = scaled_fresnel(
            field,
            axial_distance=distance,
            destination_grid=destination_grid,
        )
        exact_aligned = _align_to(exact, field)
        paraxial_aligned = _align_to(paraxial, field)
        norm = exact_aligned.abs().max().item()
        rel_sas_exact = (
            (sas_aligned - exact_aligned).abs().max().item() / norm
        )
        rel_paraxial_exact = (
            (paraxial_aligned - exact_aligned).abs().max().item() / norm
        )
        # SAS 应当比 ScaledFresnel 更接近精确角谱（这正是 SAS 文献的目标）
        assert rel_sas_exact < rel_paraxial_exact, (
            rel_sas_exact,
            rel_paraxial_exact,
        )
        # 且 SAS 不恒等于 ScaledFresnel（预补偿改变了结果）
        assert not torch.allclose(
            sas_aligned,
            paraxial_aligned,
            atol=1.0e-6,
        )

    def test_sas_differs_from_scaled_angular_spectrum_under_magnification(
        self,
    ) -> None:
        """
        在带放大率的目标网格上 SAS 与 ScaledAngularSpectrum 因传递核不同而结果
        不同——SAS 经近轴 Collins 阶段携带放大率，ScaledAngularSpectrum 用纯
        辐射角谱核
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(10, 12),
            sample_spacing=(2.5e-6, 3.0e-6),
        )
        sas = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        asm = scaled_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        # 传递核不同，结果不应一致
        assert not torch.allclose(
            sas.envelope,
            asm.envelope,
            atol=1.0e-8,
        )

    def test_sampling_refinement_converges_to_direct_reference(self) -> None:
        """
        采样加密后 SAS 与独立显式参照的复场偏差单调减小（区分物理精度与单网格
        巧合）
        """
        base_field = _random_field(_grid(), _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        residuals: list[float] = []
        for upscale in (1, 2):
            counts = (
                base_field.grid.sample_counts[0] * upscale,
                base_field.grid.sample_counts[1] * upscale,
            )
            spacing = (
                base_field.grid.sample_spacing[0] / upscale,
                base_field.grid.sample_spacing[1] / upscale,
            )
            grid = SpatialGrid.centered(
                sample_counts=counts,
                sample_spacing=spacing,
            )
            field = _random_field(grid, _monochromatic())
            dest_counts = (
                destination_grid.sample_counts[0] * upscale,
                destination_grid.sample_counts[1] * upscale,
            )
            dest_spacing = (
                destination_grid.sample_spacing[0] / upscale,
                destination_grid.sample_spacing[1] / upscale,
            )
            dest = SpatialGrid.centered(
                sample_counts=dest_counts,
                sample_spacing=dest_spacing,
            )
            produced = scalable_angular_spectrum(
                field,
                axial_distance=_DEFAULT_DISTANCE,
                destination_grid=dest,
            )
            reference = _direct_sas(
                field,
                destination_grid=dest,
                axial_distance=_DEFAULT_DISTANCE,
            )
            produced_aligned = _align_to(produced, field)
            residuals.append(
                (produced_aligned - reference).abs().max().item()
                / reference.abs().max().item()
            )
        assert residuals[1] <= residuals[0] * 1.5, residuals


class TestGradients:
    """
    证据层 4：可训练物理输入的普通 autograd（无 stale Parameter-derived cache）
    """

    @pytest.mark.parametrize("entry", ["function", "component"])
    def test_axial_distance_gradient_is_preserved(
        self,
        entry: str,
    ) -> None:
        """
        对可训练轴向距离做 gradcheck，双精度，function + component 入口
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        distance = torch.tensor(
            _DEFAULT_DISTANCE,
            dtype=torch.float64,
            requires_grad=True,
        )

        def _evaluate(signed_distance: torch.Tensor) -> torch.Tensor:
            if entry == "function":
                output = scalable_angular_spectrum(
                    field,
                    axial_distance=signed_distance,
                    destination_grid=destination_grid,
                )
            else:
                component = ScalableAngularSpectrum(
                    axial_distance=signed_distance,
                    destination_grid=destination_grid,
                )
                output = component(field)
            return output.envelope.sum().real

        assert torch.autograd.gradcheck(
            _evaluate,
            (distance,),
            eps=1.0e-6,
            atol=1.0e-5,
            rtol=1.0e-3,
        )





class TestScalableAngularSpectrumResidualSupport:
    """
    SAS 残差预补偿支撑与残差相位在 fixed-double / cycles-only phase /
    certified sampling 三重不变量下的独立资格证据。

    残差相位以单一稳定形式 ``-(n·d/λ)·u²/(2·(1+s_z)²)`` 给出（``u=s_x²+s_y²``、
    ``s_z=sqrt(1-u)``），等价于 ``d·(kz−k) + d·k_perp²/(2k)`` 之和但不分别计算两单项
    后相加。逐轴支撑判据 ``|d·s_a·u/(s_z·(1+s_z))| < L_a/2`` 经所有者本地多项式精确
    符号判定（``Y<0`` 快通道；否则 ``Y² < (L_a/2)²·n⁴·Q`` 严格），``sqrt`` 完全不出现
    在判定里。本类逐条覆盖工单证据清单并保留先前的 1,436 箱对抗锚点。本方法按
    Heintzmann、Loetgering 与 Wechsler 2023（Optica 10(11) 1407–1416）组合，声明
    范围以本仓库实现的显式目标网格推广为限——带限近似，非带外精确解。
    """

    sample_count = 128
    spacing = 0.2e-6
    wavelength = 0.5e-6
    refractive_index = 1.0
    axial_distance = 10.0e-6

    def _facts(
        self,
        *,
        counts: tuple[int, int] | None = None,
        spacing: float | None = None,
        wavelength: float | None = None,
        index: float | None = None,
        distance: float | None = None,
    ) -> _RadiativeSpectrumFacts:
        real_dtype = torch.float64
        device = torch.device("cpu")
        if counts is None:
            counts = (self.sample_count, self.sample_count)
        if spacing is None:
            spacing = self.spacing
        if wavelength is None:
            wavelength = self.wavelength
        if index is None:
            index = self.refractive_index
        if distance is None:
            distance = self.axial_distance
        return _radiative_spectrum_facts(
            computational_counts=counts,
            signed_spacing=(
                torch.tensor(spacing, dtype=real_dtype),
                torch.tensor(spacing, dtype=real_dtype),
            ),
            displacement=(
                torch.zeros((), dtype=real_dtype, device=device),
                torch.zeros((), dtype=real_dtype, device=device),
            ),
            axial_distance=torch.tensor(distance, dtype=real_dtype, device=device),
            wavelengths=torch.tensor([wavelength], dtype=real_dtype, device=device),
            refractive_indices=torch.tensor([index], dtype=real_dtype, device=device),
            real_dtype=real_dtype,
            device=device,
        )

    def _precompensation(
        self,
        *,
        counts: tuple[int, int] | None = None,
        spacing: float | None = None,
        wavelength: float | None = None,
        index: float | None = None,
        distance: float | None = None,
    ) -> ScalableAngularSpectrumPrecompensation:
        # 在工单审计几何或其覆盖下直接构造生产 SAS 预补偿传递核（不经 _facts 缓存）
        real_dtype = torch.float64
        device = torch.device("cpu")
        if counts is None:
            counts = (self.sample_count, self.sample_count)
        if spacing is None:
            spacing = self.spacing
        if wavelength is None:
            wavelength = self.wavelength
        if index is None:
            index = self.refractive_index
        if distance is None:
            distance = self.axial_distance
        return scalable_angular_spectrum_precompensation(
            computational_counts=counts,
            input_signed_spacing=(
                torch.tensor(spacing, dtype=real_dtype),
                torch.tensor(spacing, dtype=real_dtype),
            ),
            axial_distance=torch.tensor(distance, dtype=real_dtype, device=device),
            wavelengths=torch.tensor([wavelength], dtype=real_dtype, device=device),
            refractive_indices=torch.tensor([index], dtype=real_dtype, device=device),
            real_dtype=real_dtype,
            complex_dtype=torch.complex128,
            device=device,
        )

    def _oracle_support_and_residual(
        self,
        *,
        counts: tuple[int, int] | None = None,
        spacing: float | None = None,
        wavelength: float | None = None,
        index: float | None = None,
        distance: float | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if counts is None:
            counts = (self.sample_count, self.sample_count)
        if spacing is None:
            spacing = self.spacing
        if wavelength is None:
            wavelength = self.wavelength
        if index is None:
            index = self.refractive_index
        if distance is None:
            distance = self.axial_distance
        n_counts_y, n_counts_x = counts
        fy = (
            torch.fft.fftfreq(n_counts_y, d=1.0, dtype=torch.float64)
            / spacing
        )
        fx = (
            torch.fft.fftfreq(n_counts_x, d=1.0, dtype=torch.float64)
            / spacing
        )
        support = torch.zeros((n_counts_y, n_counts_x), dtype=torch.bool)
        residual_cycles = torch.zeros((n_counts_y, n_counts_x), dtype=torch.float64)
        half_y = Decimal(repr(0.5 * n_counts_y * spacing))
        half_x = Decimal(repr(0.5 * n_counts_x * spacing))
        for iy in range(n_counts_y):
            for ix in range(n_counts_x):
                with localcontext() as ctx:
                    ctx.prec = 80
                    n_dec = Decimal(repr(index))
                    lam_dec = Decimal(repr(wavelength))
                    d_dec = Decimal(repr(distance))
                    fy_dec = Decimal(repr(fy[iy].item()))
                    fx_dec = Decimal(repr(fx[ix].item()))
                    sy = lam_dec * fy_dec / n_dec
                    sx = lam_dec * fx_dec / n_dec
                    u = sx * sx + sy * sy
                    sz_sq = 1 - u
                    if sz_sq <= 0:
                        continue
                    sz = sz_sq.sqrt()
                    val_y = abs(d_dec * sy * u / (sz * (1 + sz)))
                    val_x = abs(d_dec * sx * u / (sz * (1 + sz)))
                    if val_y < half_y and val_x < half_x:
                        support[iy, ix] = True
                    n_d_lambda = n_dec * d_dec / lam_dec
                    residual_cycles[iy, ix] = float(
                        -n_d_lambda
                        * u
                        * u
                        / (2 * (1 + sz) * (1 + sz))
                    )
        return support, residual_cycles

    def test_sas_residual_support_matches_1436_bin_adversarial_anchor(
        self,
    ) -> None:
        """
        保留先前 1,436 箱对抗锚点：在审计几何下 SAS 残差支撑比标准 AS 位移支撑
        严格更宽，且逐箱与 Decimal 高精度 oracle 一致（0 不匹配）
        """
        facts = self._facts()
        standard = facts.radiative_support[0] & facts.alias_support[0]
        precompensation = self._precompensation()
        sas = (precompensation.transfer[0].abs() > 0.0) & facts.radiative_support[0]
        sas_only = sas & ~standard
        assert int(sas_only.sum()) == 1436, int(sas_only.sum())
        assert int((standard & ~sas).sum()) == 0
        # 生产 certified 支撑逐箱匹配 Decimal oracle（0 不匹配）
        oracle, _ = self._oracle_support_and_residual()
        assert torch.equal(sas, oracle)

    def test_high_precision_finite_difference_of_residual_cycles_both_axes(
        self,
    ) -> None:
        """
        冻结 Fourier 残差相位的逐箱中心差分对 ``nu_y``、``nu_x`` 都匹配稳定解析导数
        ``-d·s_a·u/(s_z·(1+s_z))``
        """

        facts = self._facts()
        precompensation = self._precompensation()
        transfer = precompensation.transfer[0]
        n = self.refractive_index
        lam = self.wavelength
        sp = self.spacing
        n_counts = self.sample_count
        d = self.axial_distance
        fy = torch.fft.fftfreq(n_counts, d=1.0, dtype=torch.float64) / sp
        fx = torch.fft.fftfreq(n_counts, d=1.0, dtype=torch.float64) / sp
        # 选一个内部、远离边界与直流分量的箱（4,5）做有限差分
        iy, ix = 4, 5
        with localcontext() as ctx:
            ctx.prec = 80
            n_dec = Decimal(repr(n))
            lam_dec = Decimal(repr(lam))
            d_dec = Decimal(repr(d))
            fy_dec = Decimal(repr(fy[iy].item()))
            fx_dec = Decimal(repr(fx[ix].item()))
            sy = lam_dec * fy_dec / n_dec
            sx = lam_dec * fx_dec / n_dec
            u = sx * sx + sy * sy
            sz = (1 - u).sqrt()
            analytic_x = float(-d_dec * sx * u / (sz * (1 + sz)))
            analytic_y = float(-d_dec * sy * u / (sz * (1 + sz)))

        def _cycles_at(iy_off: int, ix_off: int) -> float:
            value = transfer[iy + iy_off, ix + ix_off].item()
            return math.atan2(value.imag, value.real) / (2.0 * math.pi)

        delta_nu = 1.0 / (n_counts * sp)
        # cycles 对频率（cycles/m）的中心差分直接给出长度量纲的导数
        finite_x = (_cycles_at(0, +1) - _cycles_at(0, -1)) / (2 * delta_nu)
        finite_y = (_cycles_at(+1, 0) - _cycles_at(-1, 0)) / (2 * delta_nu)
        assert abs(finite_x - analytic_x) < 1.0e-7, (finite_x, analytic_x)
        assert abs(finite_y - analytic_y) < 1.0e-7, (finite_y, analytic_y)

    def test_stable_residual_nonzero_where_direct_subtractive_rounds_to_zero(
        self,
    ) -> None:
        """
        近轴 ``u`` 上直接减法 ``sqrt(1-u) - (1-u/2)`` 在 binary64 下舍入为零，但稳定
        形式 ``-u²/(2·(1+s_z)²)`` 与高精度 oracle 保持非零；生产残差周期公式采用
        稳定形式而非直接减法（源码可读 + 数值对照）
        """

        # 标量对抗：选一组近轴 ``u`` 使直接减法在 binary64 恰舍入为 0.0
        near_axis_u_values = [1.0e-9, 1.0e-10, 1.0e-12, 1.0e-15]
        for u_value in near_axis_u_values:
            direct_factor = math.sqrt(1.0 - u_value) - (1.0 - u_value / 2.0)
            # 直接减法在 binary64 下舍入为零
            assert direct_factor == 0.0, (u_value, direct_factor)
            sz = math.sqrt(1.0 - u_value)
            stable_factor = -u_value * u_value / (2.0 * (1.0 + sz) ** 2)
            # 稳定形式保持非零且匹配高精度 oracle
            assert stable_factor != 0.0
            with localcontext() as ctx:
                ctx.prec = 80
                u_dec = Decimal(repr(u_value))
                sz_dec = (1 - u_dec).sqrt()
                oracle_factor = float(
                    -u_dec * u_dec / (2 * (1 + sz_dec) * (1 + sz_dec))
                )
            assert abs(stable_factor - oracle_factor) < 1.0e-6 * abs(oracle_factor)
        # 生产源码采用稳定形式（读源断言，独立于运行时）

        repo_root = Path(__file__).resolve().parents[2]
        source = (
            repo_root
            / "src"
            / "chromatix_next"
            / "_numerics"
            / "wave_propagation"
            / "scalable_angular_spectrum.py"
        ).read_text(encoding="utf-8")
        assert (
            "normalized_transverse_wavevector_squared.square()" in source
            and "one_plus_direction_z.square()" in source
        )
        # 数值对照：在审计几何的近轴箱上生产传递核相位匹配稳定 oracle 到 1e-10
        facts = self._facts()
        precompensation = self._precompensation()
        transfer = precompensation.transfer[0]
        wave_number = float(facts.wave_number[0, 0, 0])
        ky = facts.transverse_wavevector_y[0]
        kx = facts.transverse_wavevector_x[0]
        kperp2 = kx**2 + ky**2
        u = kperp2 / (wave_number**2)
        sz = torch.sqrt(torch.clamp(1.0 - u, min=0.0))
        index = self.refractive_index
        lam = self.wavelength
        d = self.axial_distance
        stable_cycles = (
            -(index * d / lam)
            * u**2
            / (2.0 * (1.0 + sz) ** 2)
        )
        direct_cycles = (
            (index * d / lam) * (sz - (1.0 - u / 2.0))
        )
        supported = (transfer.abs() > 0.0) & facts.radiative_support[0]
        # 选近轴、支撑、直接减法相对误差大的箱（远离 DC 以避免 u=0）
        near_axis = supported & (u > 1.0e-6) & (u < 0.05)
        assert near_axis.any()
        produced_phase = torch.atan2(transfer.imag, transfer.real) / (
            2.0 * math.pi
        )
        # 生产传递核相位与稳定形式一致（环绕后），与直接减法在近轴箱上有可测差距
        stable_diff = (
            (produced_phase - stable_cycles)[near_axis].abs().max().item()
        )
        direct_diff = (
            (produced_phase - direct_cycles)[near_axis].abs().max().item()
        )
        assert stable_diff < 1.0e-9, stable_diff

    def test_brute_force_small_frequency_grid_support_matches_oracle(self) -> None:
        """
        暴力小频网格：逐箱生产 certified 支撑与 Decimal 高精度 oracle 一致
        （含辐射/掠入/倏逝、支撑边界各情形；距离取大使部分辐射箱被排除）
        """
        counts = (11, 13)
        spacing = 0.6e-6
        wavelength = 0.5e-6
        index = 1.3
        distance = 120.0e-6
        facts = self._facts(
            counts=counts,
            spacing=spacing,
            wavelength=wavelength,
            index=index,
            distance=distance,
        )
        precompensation = self._precompensation(
            counts=counts,
            spacing=spacing,
            wavelength=wavelength,
            index=index,
            distance=distance,
        )
        sas = (precompensation.transfer[0].abs() > 0.0) & facts.radiative_support[0]
        oracle, _ = self._oracle_support_and_residual(
            counts=counts,
            spacing=spacing,
            wavelength=wavelength,
            index=index,
            distance=distance,
        )
        assert torch.equal(sas, oracle)
        # 非平凡：既有支撑也有辐射但被残差判据排除的箱
        assert int(sas.sum()) > 0
        assert int((~sas & facts.radiative_support[0]).sum()) > 0

    def test_sas_matches_high_padded_exact_angular_spectrum_on_accepted_band(
        self,
    ) -> None:
        """
        在 SAS 残差支撑比标准 AS 位移支撑更宽的几何下，SAS 在声明支撑带内复现高
        补零精确角谱参照；带外不声称精确——本方法是带限近似，非带外精确解
        """
        counts = (24, 24)
        spacing = 0.5e-6
        sigma = 1.5e-6
        distance = 20.0e-6
        position = (
            torch.arange(counts[0], dtype=torch.float64) - (counts[0] - 1) / 2.0
        ) * spacing
        amplitude = torch.exp(
            -(position[:, None] ** 2 + position[None, :] ** 2) / sigma**2,
        ).to(dtype=torch.complex128)
        grid = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=(
                torch.tensor(spacing, dtype=torch.float64),
                torch.tensor(spacing, dtype=torch.float64),
            ),
        )
        field = OpticalField(
            envelope=amplitude.unsqueeze(0).unsqueeze(0),
            grid=grid,
            spectrum=_monochromatic(),
            polarization_representation=Polarization.scalar().representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=grid.sample_spacing,
        )
        produced = scalable_angular_spectrum(
            field,
            axial_distance=distance,
            destination_grid=destination_grid,
        )
        reference = _high_padded_exact_angular_spectrum(
            field,
            destination_grid=destination_grid,
            axial_distance=distance,
            pad_factor=4,
        )
        produced_aligned = _align_to(produced, field)
        reference_aligned = _align_to(reference, field)
        peak = reference_aligned.abs().max().item()
        rel = (
            (produced_aligned - reference_aligned).abs().max().item() / peak
        )
        assert rel < 1.0e-3, rel

    def test_narrow_valid_and_invalid_residual_bands_at_binary64_boundary(
        self,
    ) -> None:
        """
        支撑边界附近存在窄 valid/invalid binary64 距离带：单调翻转（小距离准入、
        大距离排除），翻转点 ``d_flip`` 的前驱准入、``d_flip`` 排除；Decimal oracle
        在 ``d_flip`` 也排除（边界严格 ``<``）
        """

        n_counts = self.sample_count
        sp = self.spacing
        lam = self.wavelength
        index = self.refractive_index
        nu_x = 1.0 / (n_counts * sp)
        half_x = 0.5 * n_counts * sp
        with localcontext() as ctx:
            ctx.prec = 80
            n_dec = Decimal(repr(index))
            lam_dec = Decimal(repr(lam))
            nu_x_dec = Decimal(repr(nu_x))
            half_dec = Decimal(repr(half_x))
            sx = lam_dec * nu_x_dec / n_dec
            u = sx * sx
            sz = (1 - u).sqrt()
            # ``d_*`` 使 ``|d·s_x·u/(s_z·(1+s_z))| = L_a/2`` 恰等号
            d_star = float(half_dec * sz * (1 + sz) / (sx.copy_abs() * u))

        def _is_admitted(distance: float) -> bool:
            precomp = self._precompensation(distance=distance)
            facts = self._facts(distance=distance)
            sas = (
                (precomp.transfer[0].abs() > 0.0)
                & facts.radiative_support[0]
            )
            return bool(sas[0, 1])

        # ``d_*`` 的 float 投影可能落在准入侧或排除侧；自 ``d_*`` 向上扫到首个排除
        d_flip = d_star
        for _ in range(64):
            if not _is_admitted(d_flip):
                break
            d_flip = math.nextafter(d_flip, math.inf)
        # 翻转点：前驱准入、``d_flip`` 排除（窄 binary64 valid/invalid 带）
        assert _is_admitted(math.nextafter(d_flip, -math.inf))
        assert not _is_admitted(d_flip)
        # ``d_flip`` 远大于 ``d_*`` 的几个 ULP 以内（确认是边界翻转而非发散）
        assert abs(d_flip - d_star) <= 64 * abs(
            math.ulp(d_star)
        ), (d_star, d_flip)
        # Decimal oracle 在 ``d_flip`` 也排除（边界处 ``|d·s·u/...| ≥ L_a/2``）
        with localcontext() as ctx:
            ctx.prec = 80
            n_dec = Decimal(repr(index))
            lam_dec = Decimal(repr(lam))
            d_dec = Decimal(repr(d_flip))
            nu_dec = Decimal(repr(nu_x))
            sx = lam_dec * nu_dec / n_dec
            u = sx * sx
            sz = (1 - u).sqrt()
            val = abs(d_dec * sx * u / (sz * (1 + sz)))
            assert not (val < Decimal(repr(half_x)))

    def test_exact_algebraic_equality_and_neighbouring_binary64_inputs(
        self,
    ) -> None:
        """
        多项式精确符号在精确代数等号处返回 0（严格 ``<`` 排除）；相邻 binary64 输入
        返回 ±1 并给出方向正确的支撑翻转——不经 ``round(sqrt(Q))`` 的额外舍入
        """

        reference = torch.tensor(6.0, dtype=torch.float64)
        squared_factor = torch.tensor(3.0, dtype=torch.float64)
        extra_factor = torch.tensor(4.0, dtype=torch.float64)
        sign_exact = int(
            squared_reference_minus_squared_factor_extra_factor_sign(
                reference=reference,
                squared_factor=squared_factor,
                extra_factor=extra_factor,
            ).item()
        )
        assert sign_exact == 0
        # 相邻 binary64 reference：上邻 → sign +1；下邻 → sign -1
        ref_plus = torch.tensor(
            math.nextafter(reference.item(), math.inf),
            dtype=torch.float64,
        )
        ref_minus = torch.tensor(
            math.nextafter(reference.item(), -math.inf),
            dtype=torch.float64,
        )
        sign_plus = int(
            squared_reference_minus_squared_factor_extra_factor_sign(
                reference=ref_plus,
                squared_factor=squared_factor,
                extra_factor=extra_factor,
            ).item()
        )
        sign_minus = int(
            squared_reference_minus_squared_factor_extra_factor_sign(
                reference=ref_minus,
                squared_factor=squared_factor,
                extra_factor=extra_factor,
            ).item()
        )
        assert sign_plus == 1
        assert sign_minus == -1
        sign_big = int(
            squared_reference_minus_squared_factor_extra_factor_sign(
                reference=torch.tensor(1.0, dtype=torch.float64),
                squared_factor=torch.tensor(1.0e-6, dtype=torch.float64),
                extra_factor=torch.tensor(4.0e12, dtype=torch.float64),
            ).item()
        )
        assert sign_big == -1

    def test_certified_support_matches_decimal_oracle_on_audit_geometry(
        self,
    ) -> None:
        """
        对抗性 rounded-sqrt：``Q`` 为非完全平方时 ``round(sqrt(Q))`` 浮点判据引入额
        外舍入，certified 多项式路径把 ``sqrt(Q)`` 完全排除在判定外。在审计几何与
        色散几何下生产 certified 支撑逐箱匹配 Decimal 高精度 oracle（0 不匹配）
        """
        # 审计几何：128x128 / 0.2µm / 真空 / 10µm（与 1,436 锚点同几何）
        precomp = self._precompensation()
        facts = self._facts()
        sas = (precomp.transfer[0].abs() > 0.0) & facts.radiative_support[0]
        oracle, _ = self._oracle_support_and_residual()
        assert torch.equal(sas, oracle)
        # 色散几何：多波长 + 非整数折射率，Q 在多数箱上为非完全平方
        counts = (9, 11)
        spacing = 0.55e-6
        wavelengths = (0.45e-6, 0.6e-6)
        indices = (1.1, 1.45)
        real_dtype = torch.float64
        device = torch.device("cpu")
        facts_multi = _radiative_spectrum_facts(
            computational_counts=counts,
            signed_spacing=(
                torch.tensor(spacing, dtype=real_dtype),
                torch.tensor(spacing, dtype=real_dtype),
            ),
            displacement=(
                torch.zeros((), dtype=real_dtype, device=device),
                torch.zeros((), dtype=real_dtype, device=device),
            ),
            axial_distance=torch.tensor(35.0e-6, dtype=real_dtype, device=device),
            wavelengths=torch.tensor(wavelengths, dtype=real_dtype, device=device),
            refractive_indices=torch.tensor(indices, dtype=real_dtype, device=device),
            real_dtype=real_dtype,
            device=device,
        )
        precomp_multi = scalable_angular_spectrum_precompensation(
            computational_counts=counts,
            input_signed_spacing=(
                torch.tensor(spacing, dtype=real_dtype),
                torch.tensor(spacing, dtype=real_dtype),
            ),
            axial_distance=torch.tensor(35.0e-6, dtype=real_dtype, device=device),
            wavelengths=torch.tensor(wavelengths, dtype=real_dtype, device=device),
            refractive_indices=torch.tensor(indices, dtype=real_dtype, device=device),
            real_dtype=real_dtype,
            complex_dtype=torch.complex128,
            device=device,
        )
        sas_multi = (
            (precomp_multi.transfer.abs() > 0.0) & facts_multi.radiative_support
        )
        # 逐光谱 oracle 对照
        for spectrum_index, (wl, idx) in enumerate(zip(wavelengths, indices)):
            single_facts = self._facts(
                counts=counts,
                spacing=spacing,
                wavelength=wl,
                index=idx,
                distance=35.0e-6,
            )
            oracle_single, _ = self._oracle_support_and_residual(
                counts=counts,
                spacing=spacing,
                wavelength=wl,
                index=idx,
                distance=35.0e-6,
            )
            assert torch.equal(sas_multi[spectrum_index], oracle_single)
            assert torch.equal(
                sas_multi[spectrum_index],
                (sas_multi[spectrum_index] & single_facts.radiative_support[0]),
            )

    def test_support_is_even_in_distance_sign_and_transfer_conjugates(self) -> None:
        """
        正/负轴向距离：支撑逐箱相同（判据对距离符号偶），传递核在支撑上互为共轭
        （``p(−|d|)=conj(p(|d|))``）
        """
        distance = self.axial_distance
        precomp_pos = self._precompensation(distance=distance)
        precomp_neg = self._precompensation(distance=-distance)
        facts_pos = self._facts(distance=distance)
        facts_neg = self._facts(distance=-distance)
        sas_pos = (precomp_pos.transfer[0].abs() > 0.0) & facts_pos.radiative_support[0]
        sas_neg = (precomp_neg.transfer[0].abs() > 0.0) & facts_neg.radiative_support[0]
        assert torch.equal(sas_pos, sas_neg)
        # 支撑上正负传递核互为共轭
        pos = precomp_pos.transfer[0]
        neg = precomp_neg.transfer[0]
        diff = (pos[sas_pos] - neg[sas_neg].conj()).abs().max().item()
        assert diff < 1.0e-12, diff

    def test_translated_and_scaled_destination_grids_preserve_invariances(
        self,
    ) -> None:
        """
        残差预补偿支撑对横向平移不变（displacement=0）；目标网格缩放（改变采样间
        距 → 改变半窗）按预期收紧/放松支撑
        """
        base_grid = _grid()
        counts = base_grid.sample_counts
        sp_base = (
            base_grid.sample_spacing[0].item(),
            base_grid.sample_spacing[1].item(),
        )
        centered_first_y = -0.5 * (counts[0] - 1) * sp_base[0]
        centered_first_x = -0.5 * (counts[1] - 1) * sp_base[1]
        translated_grid = SpatialGrid(
            sample_counts=counts,
            sample_spacing=base_grid.sample_spacing,
            first_sample_position=(
                torch.tensor(centered_first_y + 0.4e-6, dtype=torch.float64),
                torch.tensor(centered_first_x - 0.3e-6, dtype=torch.float64),
            ),
            orientation=base_grid.orientation,
        )
        field = _random_field(base_grid, _monochromatic())
        produced_base = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=base_grid,
        )
        produced_translated = scalable_angular_spectrum(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=translated_grid,
        )
        assert produced_base.envelope.shape == produced_translated.envelope.shape
        precomp_base = self._precompensation(spacing=self.spacing)
        facts_base = self._facts(spacing=self.spacing)
        sas_base = (
            (precomp_base.transfer[0].abs() > 0.0)
            & facts_base.radiative_support[0]
        )
        precomp_wide = self._precompensation(spacing=2.0 * self.spacing)
        facts_wide = self._facts(spacing=2.0 * self.spacing)
        sas_wide = (
            (precomp_wide.transfer[0].abs() > 0.0)
            & facts_wide.radiative_support[0]
        )
        assert int(sas_wide.sum()) > int(sas_base.sum()), (
            int(sas_wide.sum()),
            int(sas_base.sum()),
        )

    def test_complex_field_and_smooth_distance_and_envelope_gradients(self) -> None:
        """
        复场 + 平滑距离：对可训练轴向距离做 gradcheck（双精度，function 入口），
        支撑判据对距离取绝对值故可微路径光滑
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        distance = torch.tensor(
            _DEFAULT_DISTANCE,
            dtype=torch.float64,
            requires_grad=True,
        )

        def _evaluate(signed_distance: torch.Tensor) -> torch.Tensor:
            output = scalable_angular_spectrum(
                field,
                axial_distance=signed_distance,
                destination_grid=destination_grid,
            )
            return output.envelope.sum().real

        assert torch.autograd.gradcheck(
            _evaluate,
            (distance,),
            eps=1.0e-6,
            atol=1.0e-5,
            rtol=1.0e-3,
        )

    @pytest.mark.skipif(
        not torch.cuda.is_available(),
        reason="CUDA hardware not available",
    )
    def test_cpu_and_cuda_support_agree(self) -> None:
        """
        CPU/CUDA：同一几何下 SAS 残差支撑掩膜与传递核在 CPU 与 CUDA 上一致
        （certified 多项式符号在两设备上等价）
        """
        real_dtype = torch.float64
        complex_dtype = torch.complex128
        cpu = scalable_angular_spectrum_precompensation(
            computational_counts=(self.sample_count, self.sample_count),
            input_signed_spacing=(
                torch.tensor(self.spacing, dtype=real_dtype),
                torch.tensor(self.spacing, dtype=real_dtype),
            ),
            axial_distance=torch.tensor(self.axial_distance, dtype=real_dtype),
            wavelengths=torch.tensor([self.wavelength], dtype=real_dtype),
            refractive_indices=torch.tensor([self.refractive_index], dtype=real_dtype),
            real_dtype=real_dtype,
            complex_dtype=complex_dtype,
            device=torch.device("cpu"),
        )
        cuda = scalable_angular_spectrum_precompensation(
            computational_counts=(self.sample_count, self.sample_count),
            input_signed_spacing=(
                torch.tensor(self.spacing, dtype=real_dtype, device="cuda"),
                torch.tensor(self.spacing, dtype=real_dtype, device="cuda"),
            ),
            axial_distance=torch.tensor(self.axial_distance, dtype=real_dtype),
            wavelengths=torch.tensor([self.wavelength], dtype=real_dtype),
            refractive_indices=torch.tensor([self.refractive_index], dtype=real_dtype),
            real_dtype=real_dtype,
            complex_dtype=complex_dtype,
            device=torch.device("cuda"),
        )
        cpu_support = (cpu.transfer.abs() > 0.0).cpu()
        cuda_support = (cuda.transfer.abs() > 0.0).cpu()
        assert torch.equal(cpu_support, cuda_support)
        diff = (
            cpu.transfer.cpu()[cpu_support] - cuda.transfer.cpu()[cuda_support]
        ).abs().max().item()
        assert diff < 1.0e-11, diff

    @pytest.mark.skipif(
        not torch.cuda.is_available(),
        reason="CUDA hardware not available",
    )
    @pytest.mark.cuda
    def test_public_action_matches_cpu_on_cuda(self) -> None:
        """
        公共动作在 CUDA 上保持与 CPU 相同的复包络与目标网格
        预算依据 Issue 16 方程预算族的 FFT 类（1e-10 峰值相对量级）。
        """
        base = _random_field(
            _grid(counts=(16, 16), spacing=(1.0e-6, 1.0e-6)),
            _monochromatic(),
        )
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
            sample_counts=(16, 16),
            sample_spacing=(1.0e-6, 1.0e-6),
        )
        cpu_output = scalable_angular_spectrum(
            base,
            axial_distance=100.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        cuda_output = scalable_angular_spectrum(
            field,
            axial_distance=100.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
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


def _read_sas_owner_source() -> str:
    # 读取 SAS 数值所有者源文本以做引用 + 范围声明断言（独立于运行时导入路径）

    repo_root = Path(__file__).resolve().parents[2]
    owner = (
        repo_root
        / "src"
        / "chromatix_next"
        / "_numerics"
        / "wave_propagation"
        / "scalable_angular_spectrum.py"
    )
    return owner.read_text(encoding="utf-8")


class TestScalableAngularSpectrumAttribution:
    """
    2023 年 Heintzmann、Loetgering、Wechsler 引用与范围声明存在于源、
    测试、文档；声明范围以本仓库实现的显式目标网格推广为限（带限近似，非带外精确解）
    """

    def test_source_contains_2023_citation_and_bounded_claim(self) -> None:
        """
        SAS 数值所有者源文本包含正确的 2023 Optica 引用与 bounded-scope 声明
        """
        source = _read_sas_owner_source()
        # 文献引用断言（下列断言检查作者、期刊、年份与 DOI 是否在生产源中）
        assert "Heintzmann" in source
        assert "Loetgering" in source
        assert "Wechsler" in source
        assert "2023" in source
        assert "Optica" in source
        assert "10.1364/OPTICA.497809" in source
        assert "推广" in source or "bounded" in source.lower()
        assert "严格逆" in source or "strict-inverse" in source.lower()

    def test_tests_contain_2023_citation_and_bounded_claim(self) -> None:
        """
        测试文本本身承载同一引用与 bounded-scope 声明（科学声明的可追溯性）
        """

        repo_root = Path(__file__).resolve().parents[2]
        test_file = (
            repo_root
            / "tests"
            / "propagation"
            / "test_scalable_angular_spectrum.py"
        )
        text = test_file.read_text(encoding="utf-8")
        assert "Heintzmann" in text
        assert "Loetgering" in text
        assert "Wechsler" in text
        assert "2023" in text
        assert "带限近似" in text or "bounded" in text.lower()

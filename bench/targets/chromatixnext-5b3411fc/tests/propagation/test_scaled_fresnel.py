
from __future__ import annotations

import math
from unittest.mock import Mock

import pytest
import torch

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
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.grid import PropagationExterior
from chromatix_next.optics.propagation import (
    ScaledFresnel,
    scaled_angular_spectrum,
    scaled_fresnel,
)
from chromatix_next.optics.source import PlaneWave


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


# 近轴混叠带条件 d >= n N dx^2 / lambda 的安全距离，适配默认 6x7 / 4,5um 网格
_DEFAULT_DISTANCE = 400.0e-6


def _direct_collins(
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
    cell_area = abs(spacing_y_in * spacing_x_in)
    path_lengths = field.path_reference.lengths
    outputs: list[torch.Tensor] = []
    for spectral_index, (wavelength, refractive_index) in enumerate(
        zip(wavelengths, refractive_indices, strict=True),
    ):
        wavelength = float(wavelength)
        refractive_index = float(refractive_index)
        signed_distance = float(axial_distance)
        wave_number = 2.0 * math.pi * refractive_index / wavelength
        curvature = wave_number / (2.0 * signed_distance)
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
        beta = wave_number / signed_distance
        carrier_phase = (
            2.0 * math.pi * float(path_lengths[spectral_index]) / wavelength
        )
        carrier = complex(math.cos(carrier_phase), math.sin(carrier_phase))
        envelope_slice = (
            field.envelope[spectral_index, 0].to(dtype=torch.complex128).clone()
            * carrier
        )
        chirped = envelope_slice * input_chirp
        phase_y = torch.exp(
            -1j * beta * position_y_in[:, None] * position_y_out[None, :],
        )
        phase_x = torch.exp(
            -1j * beta * position_x_in[:, None] * position_x_out[None, :],
        )
        integral = phase_y.T @ chirped @ phase_x
        axial_carrier = torch.exp(
            torch.tensor(
                1j * wave_number * signed_distance,
                dtype=torch.complex128,
            ),
        )
        prefactor = axial_carrier * torch.tensor(
            -1j * refractive_index / (wavelength * signed_distance) * cell_area,
            dtype=torch.complex128,
        )
        outputs.append(prefactor * output_chirp * integral)
    return torch.stack(outputs).unsqueeze(1)


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
def test_scaled_fresnel_preserves_supported_representation(
    representation: PolarizationRepresentation,
) -> None:
    """
    带尺度菲涅耳传播保留其支持的标量或横向表征
    """
    output = scaled_fresnel(
        _applicability_field(representation),
        axial_distance=400.0e-6,
        destination_grid=_applicability_destination(),
    )
    assert output.polarization_representation is representation


def test_scaled_fresnel_rejects_full_before_expensive_transform(
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
        scaled_fresnel(
            _applicability_field(PolarizationRepresentation.FULL),
            axial_distance=float("nan"),
            destination_grid=_applicability_destination(),
        )
    assert information.value.identity == (
        "scaled_fresnel_polarization_full_unsupported"
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
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        direct_output = scaled_fresnel(
            field,
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        component_output = ScaledFresnel(
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
        propagator = ScaledFresnel(
            axial_distance=-600.0e-6,
            destination_grid=destination_grid,
        )
        output = propagator(field)
        expected_reference = (
            field.path_reference.lengths[0] + 1.4 * -600.0e-6,
        )
        assert output.path_reference.lengths == pytest.approx(
            expected_reference,
        )
        assert output.medium is medium

    def test_forward_backward_match_independent_reference(self) -> None:
        """
        正负距离各匹配独立 Collins 参照（近轴方法的直接物理验证）
        """
        grid = _grid()
        spectrum = _monochromatic(wavelength=0.5e-6)
        field = _gaussian_field(grid, spectrum, waist=2.0e-6)
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        axial_distance = 400.0e-6
        forward_output = scaled_fresnel(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        forward_reference = _direct_collins(
            field,
            destination_grid=destination_grid,
            axial_distance=axial_distance,
        )
        backward_output = scaled_fresnel(
            field,
            axial_distance=-axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        backward_reference = _direct_collins(
            field,
            destination_grid=destination_grid,
            axial_distance=-axial_distance,
        )
        assert torch.allclose(
            _complete_field(forward_output),
            forward_reference,
            atol=2.0e-11,
        )
        assert torch.allclose(
            _complete_field(backward_output),
            backward_reference,
            atol=2.0e-11,
        )

    def test_destination_grid_is_required(self) -> None:
        """
        目标网格为必显式参数，非空间网格以稳定身份拒绝
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        with pytest.raises(
            TypeError,
            match="scaled_fresnel_destination_grid_invalid",
        ):
            scaled_fresnel(
                field,
                axial_distance=_DEFAULT_DISTANCE,
                destination_grid="not-a-grid",  # type: ignore[arg-type]
            )
        function_keywords = scaled_fresnel.__kwdefaults__ or {}
        assert "destination_grid" not in function_keywords

    def test_non_optical_field_input_rejected(self) -> None:
        """
        非 OpticalField 输入以稳定身份拒绝
        """
        grid = _grid()
        propagator = ScaledFresnel(
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=grid,
        )
        with pytest.raises(
            TypeError,
            match="scaled_fresnel_field_invalid",
        ):
            propagator("not a field")  # type: ignore[arg-type]

    def test_zero_axial_distance_rejected_at_construction(self) -> None:
        """
        零轴向距离以稳定身份在构造处拒绝（近轴积分需要非零距离）
        """
        grid = _grid()
        with pytest.raises(
            ValueError,
            match="scaled_fresnel_axial_distance_invalid",
        ):
            ScaledFresnel(
                axial_distance=0.0,
                destination_grid=grid,
            )

    def test_non_finite_axial_distance_rejected_at_construction(self) -> None:
        """
        非有限轴向距离以稳定身份在构造处拒绝
        """
        grid = _grid()
        with pytest.raises(
            ValueError,
            match="scaled_fresnel_axial_distance_invalid",
        ):
            ScaledFresnel(
                axial_distance=float("inf"),
                destination_grid=grid,
            )

    def test_float32_axial_distance_rejected_at_construction(self) -> None:
        """
        ScaledFresnel 在自己的边界拒绝单精度轴向距离
        """

        with pytest.raises(
            ValueError,
            match="scaled_fresnel_axial_distance_invalid",
        ):
            ScaledFresnel(
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
        propagator = ScaledFresnel(
            axial_distance=axial_distance,
            destination_grid=_grid(),
        )

        assert propagator.axial_distance is axial_distance
        assert (
            dict(propagator.named_parameters())["axial_distance"]
            is axial_distance
        )

    def test_invalid_exterior_rejected(self) -> None:
        """
        非 PropagationExterior 的外部以稳定身份拒绝
        """
        grid = _grid()
        with pytest.raises(
            TypeError,
            match="scaled_fresnel_exterior_invalid",
        ):
            ScaledFresnel(
                axial_distance=_DEFAULT_DISTANCE,
                destination_grid=grid,
                exterior="periodic",  # type: ignore[arg-type]
            )

    def test_orientation_mismatch_rejected(self) -> None:
        """
        目标朝向与源不一致以稳定身份拒绝（不静默翻转）
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic())
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
            orientation=("decreasing", "increasing"),
        )
        propagator = ScaledFresnel(
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        with pytest.raises(
            ValueError,
            match="scaled_fresnel_orientation_mismatch",
        ):
            propagator(field)

    def test_isolated_destination_outside_support_rejected(self) -> None:
        """
        孤立外部下目标足迹超出计算窗口以稳定身份拒绝
        """
        grid = _grid(counts=(8, 8), spacing=(1.0e-6, 1.0e-6))
        field = _random_field(grid, _monochromatic())
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
        propagator = ScaledFresnel(
            axial_distance=200.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.ISOLATED,
        )
        with pytest.raises(
            ValueError,
            match=(
                "scaled_fresnel_"
                "isolated_destination_outside_support"
            ),
        ):
            propagator(field)

    def test_input_chirp_too_narrow_rejected_without_substitution(self) -> None:
        """
        输入啁啾超出输入采样奈奎斯特时以独立稳定身份拒绝，不静默退化或替换方法
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
            match="scaled_fresnel_input_chirp_too_narrow",
        ):
            ScaledFresnel(
                axial_distance=1.0e-6,
                destination_grid=destination_grid,
                exterior=PropagationExterior.ISOLATED,
            )(field)

    def test_transform_coupling_too_narrow_rejected(self) -> None:
        """
        双线性变换耦合（携带放大率）超出正反向奈奎斯特时以独立稳定身份拒绝
        """
        grid = _grid(counts=(6, 7), spacing=(4.0e-6, 5.0e-6))
        field = _random_field(grid, _monochromatic(wavelength=0.5e-6))
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(8.0e-6, 10.0e-6),
        )
        with pytest.raises(
            ValueError,
            match="scaled_fresnel_transform_coupling_too_narrow",
        ):
            scaled_fresnel(
                field,
                axial_distance=400.0e-6,
                destination_grid=destination_grid,
                exterior=PropagationExterior.PERIODIC,
            )

    def test_output_chirp_too_narrow_rejected(self) -> None:
        """
        输出二次相位啁啾超出目标奈奎斯特时以独立稳定身份拒绝（与变换耦合独立）
        """
        grid = SpatialGrid.centered(
            sample_counts=(12, 12),
            sample_spacing=(2.0e-6, 2.0e-6),
        )
        field = _random_field(grid, _monochromatic(wavelength=0.5e-6))
        destination_grid = SpatialGrid.centered(
            sample_counts=(6, 6),
            sample_spacing=(8.0e-6, 8.0e-6),
        )
        with pytest.raises(
            ValueError,
            match="scaled_fresnel_output_chirp_too_narrow",
        ):
            scaled_fresnel(
                field,
                axial_distance=400.0e-6,
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
        field = _random_field(grid, _monochromatic(), medium)
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
            orientation=("decreasing", "increasing"),
        )
        propagator = ScaledFresnel(
            axial_distance=_DEFAULT_DISTANCE,
            destination_grid=destination_grid,
        )
        with pytest.raises(
            ValueError,
            match="scaled_fresnel_orientation_mismatch",
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
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
            orientation=("decreasing", "increasing"),
        )
        propagator = ScaledFresnel(
            axial_distance=_DEFAULT_DISTANCE,
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
            match="scaled_fresnel_orientation_mismatch",
        ):
            assembly.check()

class TestIndependentReference:
    """
    证据层 2：独立显式 Collins 矩阵参照（覆盖尺度、平移、正负距离、非真空介质）
    """

    @pytest.mark.parametrize(
        (
            "input_counts",
            "input_spacing",
            "destination_counts",
            "destination_spacing",
            "destination_shift",
            "axial_distance",
        ),
        [
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (6, 7),
                (4.0e-6, 5.0e-6),
                (0.0, 0.0),
                400.0e-6,
            ),
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (3, 4),
                (4.0e-6, 5.0e-6),
                (0.0, 0.0),
                400.0e-6,
            ),
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (9, 9),
                (3.0e-6, 4.0e-6),
                (0.0, 0.0),
                400.0e-6,
            ),
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (5, 6),
                (3.0e-6, 4.0e-6),
                (-1.8e-6, 2.2e-6),
                400.0e-6,
            ),
            (
                (6, 7),
                (4.0e-6, 5.0e-6),
                (5, 6),
                (4.0e-6, 5.0e-6),
                (0.0, 0.0),
                -400.0e-6,
            ),
        ],
        ids=(
            "unity-scale-no-shift",
            "smaller-count-same-scale",
            "finer-scale",
            "finer-scale-off-axis",
            "backward-distance",
        ),
    )
    def test_random_field_matches_direct_collins_reference(
        self,
        input_counts: tuple[int, int],
        input_spacing: tuple[float, float],
        destination_counts: tuple[int, int],
        destination_spacing: tuple[float, float],
        destination_shift: tuple[float, float],
        axial_distance: float,
    ) -> None:
        """
        随机带限复场的带尺度 Fresnel 传播匹配显式 Collins 矩阵参照
        """
        grid = SpatialGrid.centered(
            sample_counts=input_counts,
            sample_spacing=input_spacing,
        )
        field = _random_field(grid, _monochromatic(wavelength=0.5e-6))
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
        output = scaled_fresnel(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        reference = _direct_collins(
            field,
            destination_grid=destination_grid,
            axial_distance=axial_distance,
        )
        assert torch.allclose(
            _complete_field(output),
            reference,
            atol=2.0e-11,
        )

    def test_nonvacuum_medium_matches_direct_collins(self) -> None:
        """
        非真空介质下带尺度 Fresnel 传播匹配独立参照
        """
        grid = _grid()
        spectrum = _monochromatic(wavelength=0.5e-6)
        medium = ConstantMedium(index=1.3)
        field = _random_field(grid, spectrum, medium)
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        axial_distance = 600.0e-6
        output = scaled_fresnel(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        reference = _direct_collins(
            field,
            destination_grid=destination_grid,
            axial_distance=axial_distance,
        )
        assert torch.allclose(
            _complete_field(output),
            reference,
            atol=2.0e-11,
        )

    def test_isolated_exterior_matches_direct_collins(self) -> None:
        """
        孤立外部下带尺度 Fresnel 传播匹配显式 Collins
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic(wavelength=0.5e-6))
        destination_grid = SpatialGrid(
            sample_counts=(4, 5),
            sample_spacing=(
                torch.tensor(4.0e-6, dtype=torch.float64),
                torch.tensor(5.0e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-9.0e-6, dtype=torch.float64),
                torch.tensor(-12.0e-6, dtype=torch.float64),
            ),
        )
        axial_distance = 400.0e-6
        output = scaled_fresnel(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.ISOLATED,
        )
        reference = _direct_collins(
            field,
            destination_grid=destination_grid,
            axial_distance=axial_distance,
        )
        assert torch.allclose(
            _complete_field(output),
            reference,
            atol=2.0e-11,
        )

    def test_polychromatic_field_matches_direct_collins(self) -> None:
        """
        多波长光场的带尺度 Fresnel 传播匹配逐波长独立参照
        """
        grid = _grid()
        spectrum = Spectrum(
            wavelengths=(0.45e-6, 0.55e-6),
            weights=(0.5, 0.5),
        )
        generator = torch.Generator(device="cpu")
        generator.manual_seed(42)
        real = torch.randn(
            (spectrum.count, 1, *grid.sample_counts),
            generator=generator,
            dtype=torch.float64,
        )
        imaginary = torch.randn(
            (spectrum.count, 1, *grid.sample_counts),
            generator=generator,
            dtype=torch.float64,
        )
        field = OpticalField(
            envelope=torch.complex(real, imaginary),
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(
                Polarization.scalar()
            ).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(0.0,) * spectrum.count,
            ),
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        axial_distance = 450.0e-6
        output = scaled_fresnel(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        reference = _direct_collins(
            field,
            destination_grid=destination_grid,
            axial_distance=axial_distance,
        )
        assert torch.allclose(
            _complete_field(output),
            reference,
            atol=2.0e-11,
        )


class TestCrossMethodComplexField:
    """
    跨方法复场证据：与 FresnelTransform 在共享的近轴频带上复场一致

    自然网格（FresnelTransform 的输出网格）的输出间距 λ|d|/(N Δx) 恰使输出啁啾的
    局部频率落在目标奈奎斯特上——输入啁啾通过则输出啁啾边界失败，二者互为倒数。
    自采样边界收紧后，自然网格几何不再落入 ScaledFresnel 的适用域；跨方法
    数值一致性由 TestIndependentReference 的独立显式 Collins 矩阵参照承担
    （后者覆盖放大、缩小、平移、正负距离与非真空介质）。
    """

    def test_natural_grid_now_fails_output_chirp_fence(self) -> None:
        """
        自然网格的输出啁啾超出目标奈奎斯特，以稳定身份显式失败而非给出欠采样场
        """
        counts = (8, 8)
        spacing = (2.0e-6, 2.0e-6)
        grid = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=spacing,
        )
        spectrum = _monochromatic(wavelength=0.5e-6)
        field = _gaussian_field(grid, spectrum, waist=3.0e-6)
        axial_distance = 200.0e-6
        wavelength_distance = 0.5e-6 * axial_distance
        output_spacing_y = wavelength_distance / (counts[0] * spacing[0])
        output_spacing_x = wavelength_distance / (counts[1] * spacing[1])
        destination_grid = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=(output_spacing_y, output_spacing_x),
        )
        with pytest.raises(
            ValueError,
            match="scaled_fresnel_output_chirp_too_narrow",
        ):
            scaled_fresnel(
                field,
                axial_distance=axial_distance,
                destination_grid=destination_grid,
                exterior=PropagationExterior.PERIODIC,
            )


class TestSamplingPaddingConvergence:
    """
    采样与补零收敛：周期/孤立外部一致；加密采样收敛
    """

    def test_periodic_and_isolated_agree_for_contained_field(self) -> None:
        """
        充分包含的紧致场在两种外部下中心区域须一致
        """
        counts = (16, 16)
        spacing = (1.0e-6, 1.0e-6)
        grid = SpatialGrid.centered(
            sample_counts=counts,
            sample_spacing=spacing,
        )
        spectrum = _monochromatic(wavelength=0.4e-6)
        field = _gaussian_field(grid, spectrum, waist=2.5e-6)
        destination_grid = SpatialGrid.centered(
            sample_counts=(12, 12),
            sample_spacing=(1.2e-6, 1.2e-6),
        )
        periodic_output = ScaledFresnel(
            axial_distance=100.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )(field)
        isolated_output = ScaledFresnel(
            axial_distance=100.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.ISOLATED,
        )(field)
        peak = periodic_output.envelope.abs().max().item()
        centre_slice = (slice(None), slice(None), slice(2, 10), slice(2, 10))
        assert torch.allclose(
            periodic_output.envelope[centre_slice],
            isolated_output.envelope[centre_slice],
            atol=5.0e-3 * peak,
        )

    def test_finer_source_sampling_converges(self) -> None:
        """
        加密源采样使带尺度 Fresnel 输出向高分辨率参照收敛
        """
        spectrum = _monochromatic(wavelength=0.5e-6)
        destination_grid = SpatialGrid.centered(
            sample_counts=(10, 10),
            sample_spacing=(1.5e-6, 1.5e-6),
        )
        axial_distance = 300.0e-6
        coarse_grid = SpatialGrid.centered(
            sample_counts=(6, 6),
            sample_spacing=(4.0e-6, 4.0e-6),
        )
        coarse_field = _gaussian_field(coarse_grid, spectrum, waist=4.0e-6)
        coarse_output = scaled_fresnel(
            coarse_field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        fine_grid = SpatialGrid.centered(
            sample_counts=(12, 12),
            sample_spacing=(2.0e-6, 2.0e-6),
        )
        fine_field = _gaussian_field(fine_grid, spectrum, waist=4.0e-6)
        fine_output = scaled_fresnel(
            fine_field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        centre_slice = (slice(None), slice(None), slice(2, 8), slice(2, 8))
        peak = fine_output.envelope.abs().max().item()
        assert torch.allclose(
            fine_output.envelope[centre_slice],
            coarse_output.envelope[centre_slice],
            atol=5.0e-2 * peak,
        )

    def test_boundary_near_destination_retains_complex_field_carrier_and_gradient(
        self,
    ) -> None:
        """
        边界附近（输出啁啾极限接近 1）的合法目标仍保留复场、载波、dtype 与梯度
        """
        grid = _grid(counts=(8, 8), spacing=(4.0e-6, 4.0e-6))
        spectrum = _monochromatic(wavelength=0.5e-6)
        field = _gaussian_field(grid, spectrum, waist=3.0e-6)
        destination_grid = SpatialGrid.centered(
            sample_counts=(6, 6),
            sample_spacing=(4.0e-6, 4.0e-6),
        )
        axial_distance = torch.nn.Parameter(
            torch.tensor(300.0e-6, dtype=torch.float64),
        )
        output = scaled_fresnel(
            field,
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        # 复场与 dtype 保留
        assert output.envelope.dtype is torch.complex128
        assert torch.is_complex(output.envelope)
        # 载波（光程参考）按介质折射率与带符号距离推进
        propagated_length = output.path_reference.lengths[0]
        if isinstance(propagated_length, torch.Tensor):
            propagated_length = float(propagated_length.detach().item())
        assert propagated_length == pytest.approx(300.0e-6)
        # 能量（有限非零）保留
        peak = output.envelope.abs().max().item()
        assert math.isfinite(peak) and peak > 0.0
        # 梯度可微
        gradient = torch.autograd.grad(
            output.envelope.real.sum(),
            axial_distance,
        )[0]
        assert bool(torch.isfinite(gradient))


class TestGradientEvidence:
    """
    证据层 3：梯度证据（双精度，function + component 入口）
    """

    def test_gradcheck_on_trainable_axial_distance_function(self) -> None:
        """
        对可训练轴向距离做 gradcheck（函数入口）
        """
        grid = _grid()
        spectrum = _monochromatic(wavelength=0.5e-6)
        field = _gaussian_field(grid, spectrum, waist=2.0e-6)
        axial_distance = torch.nn.Parameter(
            torch.tensor(400.0e-6, dtype=torch.float64),
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )

        def run(distance_value: torch.Tensor) -> torch.Tensor:
            """
            返回当前轴向距离下的输出包络实部和
            """
            return scaled_fresnel(
                field,
                axial_distance=distance_value,
                destination_grid=destination_grid,
                exterior=PropagationExterior.PERIODIC,
            ).envelope.real.sum()

        assert torch.autograd.gradcheck(
            run,
            (axial_distance,),
            eps=1e-9,
            raise_exception=True,
        )

    def test_gradcheck_on_trainable_axial_distance_component(self) -> None:
        """
        对可训练轴向距离做 gradcheck（组件入口）
        """
        grid = _grid()
        spectrum = _monochromatic(wavelength=0.5e-6)
        field = _gaussian_field(grid, spectrum, waist=2.0e-6)
        axial_distance = torch.nn.Parameter(
            torch.tensor(400.0e-6, dtype=torch.float64),
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        propagator = ScaledFresnel(
            axial_distance=axial_distance,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )

        def run(distance_value: torch.Tensor) -> torch.Tensor:
            """
            返回当前轴向距离下的组件输出包络实部和
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
        grid = _grid()
        spectrum = _monochromatic(wavelength=0.5e-6)
        field = _gaussian_field(grid, spectrum, waist=2.2e-6)
        axial_distance = torch.nn.Parameter(
            torch.tensor(400.0e-6, dtype=torch.float64),
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        propagator = ScaledFresnel(
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
            return detector(propagator(field)).values[2, 3]

        observed = observe(axial_distance)
        gradient = torch.autograd.grad(observed, axial_distance)[0]
        assert bool(torch.isfinite(gradient))
        assert abs(float(gradient)) > 1.0e-8


class TestComponentState:
    """
    组件状态、精度与设备行为
    """

    def test_loaded_fixed_distance_matches_fresh_component(self) -> None:
        """
        固定轴向距离经公共状态加载改变后仍匹配全新组件
        """
        grid = _grid()
        field = _random_field(grid, _monochromatic(wavelength=0.5e-6))
        destination_grid = SpatialGrid.centered(
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        reused = ScaledFresnel(
            axial_distance=400.0e-6,
            destination_grid=destination_grid,
        )
        reused(field)
        changed_state = ScaledFresnel(
            axial_distance=450.0e-6,
            destination_grid=destination_grid,
        ).state_dict()
        reused.load_state_dict(changed_state)
        output = reused(field)
        fresh_output = ScaledFresnel(
            axial_distance=450.0e-6,
            destination_grid=destination_grid,
        )(field)
        assert output.path_reference == fresh_output.path_reference
        assert torch.allclose(
            output.envelope,
            fresh_output.envelope,
        )

    def test_unhosted_cuda_field_owns_transfer_device(self) -> None:
        """
        CUDA 输入可驱动未托管组件在同一设备计算
        """
        if not torch.cuda.is_available():
            pytest.skip("CUDA-capable PyTorch runtime is not available.")
        base = _random_field(_grid(), _monochromatic(wavelength=0.5e-6))
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
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        propagator = ScaledFresnel(
            axial_distance=400.0e-6,
            destination_grid=destination_grid,
        )
        output = propagator(field)
        fresh_output = ScaledFresnel(
            axial_distance=400.0e-6,
            destination_grid=destination_grid,
        )(field)
        assert output.envelope.device == field.envelope.device
        assert output.envelope.dtype is field.envelope.dtype
        assert output.path_reference == fresh_output.path_reference
        assert torch.allclose(output.envelope, fresh_output.envelope)

    @pytest.mark.cuda
    def test_public_action_matches_cpu_on_cuda(self) -> None:
        """
        公共动作在 CUDA 上保持与 CPU 相同的复包络与目标网格
        预算依据 Issue 16 方程预算族的 FFT 类（1e-10 峰值相对量级）。
        """
        if not torch.cuda.is_available():
            pytest.skip("CUDA-capable PyTorch runtime is not available.")
        base = _random_field(_grid(), _monochromatic(wavelength=0.5e-6))
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
            sample_counts=(5, 6),
            sample_spacing=(4.0e-6, 5.0e-6),
        )
        cpu_output = scaled_fresnel(
            base,
            axial_distance=400.0e-6,
            destination_grid=destination_grid,
        )
        cuda_output = scaled_fresnel(
            field,
            axial_distance=400.0e-6,
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
        assert cpu_output.grid.sample_counts == (5, 6)
        assert cuda_output.grid.sample_counts == (5, 6)
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


def test_scaled_fresnel_richer_model_residual_decreases_with_phase_error() -> None:
    """
    近似模型证据：占用横向带宽变窄时，标量 Collins/Fresnel 趋近带尺度角谱
    目标几何、介质、距离和周期支撑固定，独立参照使用同一目标 Grid。
    """

    grid = _grid(
        counts=(64, 64),
        spacing=(0.5e-6, 0.5e-6),
    )
    destination_grid = SpatialGrid.centered(
        sample_counts=grid.sample_counts,
        sample_spacing=(0.5e-6, 0.5e-6),
    )
    spectrum = _monochromatic()
    residuals: list[float] = []
    for waist in (1.5e-6, 2.5e-6, 4.0e-6):
        field = _gaussian_field(
            grid,
            spectrum,
            waist=waist,
        )
        fresnel_output = scaled_fresnel(
            field,
            axial_distance=100.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        angular_output = scaled_angular_spectrum(
            field,
            axial_distance=100.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )
        actual = fresnel_output.envelope
        expected = angular_output.envelope
        alignment = (actual.conj() * expected).sum() / actual.abs().square().sum()
        residuals.append(
            float((alignment * actual - expected).abs().max())
            / float(expected.abs().max())
        )

    assert residuals[1] < residuals[0]
    assert residuals[2] < residuals[1]

from __future__ import annotations

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
from chromatix_next.optics.propagation import (
    VectorAngularSpectrum,
    vector_angular_spectrum,
)
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


def _vector_field(
    envelope: torch.Tensor,
    *,
    grid: SpatialGrid,
    wavelengths: tuple[float, ...] = (4.0e-6,),
    representation: PolarizationRepresentation = (
        PolarizationRepresentation.TRANSVERSE
    ),
    normalization: FieldNormalization = FieldNormalization.RELATIVE,
    medium: Vacuum | TabulatedMedium | None = None,
) -> OpticalField:
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=Spectrum(
            wavelengths=wavelengths,
            weights=(1.0 / len(wavelengths),) * len(wavelengths),
        ),
        polarization_representation=representation,
        medium=medium or Vacuum(),
        normalization=normalization,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * len(wavelengths),
        ),
    )


def _bin_aligned_phase(
    grid: SpatialGrid,
    *,
    bin_y: int,
    bin_x: int,
    dtype: torch.dtype = torch.float64,
) -> tuple[torch.Tensor, float, float]:
    height, width = grid.sample_counts
    spacing_y = float(grid.signed_spacing[0])
    spacing_x = float(grid.signed_spacing[1])
    wavevector_y = 2.0 * math.pi * bin_y / (height * spacing_y)
    wavevector_x = 2.0 * math.pi * bin_x / (width * spacing_x)
    position_y = (
        torch.arange(height, dtype=dtype) * spacing_y
        + float(grid.first_sample_position[0])
    )
    position_x = (
        torch.arange(width, dtype=dtype) * spacing_x
        + float(grid.first_sample_position[1])
    )
    phase = (
        wavevector_y * position_y[:, None]
        + wavevector_x * position_x[None, :]
    )
    phasor = torch.complex(torch.zeros_like(phase), phase).exp()
    return phasor, wavevector_y, wavevector_x


def test_transverse_oblique_plane_wave_reconstructs_full_field() -> None:
    """
    FFT 频箱对齐的横向斜入射场重建纵向分量并传播
    """
    grid = SpatialGrid.centered(
        sample_counts=(8, 10),
        sample_spacing=(1.0e-6, 1.25e-6),
    )
    phasor, wavevector_y, wavevector_x = _bin_aligned_phase(
        grid,
        bin_y=1,
        bin_x=1,
    )
    envelope = torch.stack(
        (
            phasor,
            0.25j * phasor,
        ),
    ).unsqueeze(0)
    field = _vector_field(envelope, grid=grid)
    axial_distance = 1.7e-6

    output = vector_angular_spectrum(
        field,
        axial_distance=axial_distance,
    )

    wave_number = 2.0 * math.pi / 4.0e-6
    longitudinal_wave_number = math.sqrt(
        wave_number**2 - wavevector_y**2 - wavevector_x**2,
    )
    longitudinal = -(
        wavevector_x * envelope[:, 0]
        + wavevector_y * envelope[:, 1]
    ) / longitudinal_wave_number
    expected = torch.cat((envelope, longitudinal.unsqueeze(1)), dim=1)
    expected_phase = (
        longitudinal_wave_number - wave_number
    ) * axial_distance
    expected = expected * complex(
        math.cos(expected_phase),
        math.sin(expected_phase),
    )
    tolerance = 512.0 * torch.finfo(torch.float64).eps
    assert output.polarization_representation is PolarizationRepresentation.FULL
    assert torch.allclose(
        output.envelope,
        expected,
        rtol=tolerance,
        atol=tolerance,
    )
    assert output.path_reference.lengths == pytest.approx((axial_distance,))


def test_function_and_component_are_the_same_vector_action() -> None:
    """
    直接函数与状态组件执行同一矢量传播动作
    """
    grid = SpatialGrid.centered(
        sample_counts=(7, 9),
        sample_spacing=(2.0e-6, 1.5e-6),
    )
    generator = torch.Generator(device="cpu").manual_seed(42)
    real = torch.randn((2, 7, 9), generator=generator, dtype=torch.float64)
    imaginary = torch.randn((2, 7, 9), generator=generator, dtype=torch.float64)
    field = _vector_field(
        torch.complex(real, imaginary).unsqueeze(0),
        grid=grid,
    )

    direct = vector_angular_spectrum(field, axial_distance=-0.7e-6)
    component = VectorAngularSpectrum(axial_distance=-0.7e-6)(field)

    assert direct.grid is component.grid
    assert direct.path_reference == component.path_reference
    assert torch.equal(direct.envelope, component.envelope)


def test_vector_angular_spectrum_rejects_float32_distance_parameter() -> None:
    """
    VectorAngularSpectrum 在自己的边界拒绝单精度轴向距离
    """

    with pytest.raises(
        ValueError,
        match="vector_angular_spectrum_axial_distance_invalid",
    ):
        VectorAngularSpectrum(
            axial_distance=torch.nn.Parameter(
                torch.tensor(2.0e-6, dtype=torch.float32),
            ),
        )


def test_vector_distance_parameter_keeps_optimizer_identity() -> None:
    """
    合法轴向距离 Parameter 保持同一注册对象并对优化器可见
    """

    axial_distance = torch.nn.Parameter(
        torch.tensor(2.0e-6, dtype=torch.float64),
    )
    propagator = VectorAngularSpectrum(axial_distance=axial_distance)

    assert propagator.axial_distance is axial_distance
    assert dict(propagator.named_parameters())["axial_distance"] is axial_distance


@pytest.mark.parametrize(
    ("representation", "normalization", "identity"),
    (
        (
            PolarizationRepresentation.SCALAR,
            FieldNormalization.RELATIVE,
            "vector_angular_spectrum_polarization_scalar_unsupported",
        ),
        (
            PolarizationRepresentation.TRANSVERSE,
            FieldNormalization.POWER,
            "vector_angular_spectrum_normalization_unsupported",
        ),
    ),
)
def test_unsupported_field_meaning_fails_with_stable_identity(
    representation: PolarizationRepresentation,
    normalization: FieldNormalization,
    identity: str,
) -> None:
    """
    不受支持的偏振或归一化以稳定标识拒绝
    """
    grid = SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(2.0e-6, 2.0e-6),
    )
    field = _vector_field(
        torch.ones(
            (
                1,
                representation.component_count,
                4,
                4,
            ),
            dtype=torch.complex128,
        ),
        grid=grid,
        representation=representation,
        normalization=normalization,
    )

    with pytest.raises(OpticalError) as caught:
        vector_angular_spectrum(field, axial_distance=0.0)

    assert caught.value.identity == identity


def test_full_sparse_transverse_field_is_accepted_and_corruption_is_rejected() -> None:
    """
    全局谱残差接受稀疏横向场并拒绝真实纵向破坏
    """
    grid = SpatialGrid.centered(
        sample_counts=(8, 10),
        sample_spacing=(1.0e-6, 1.25e-6),
    )
    phasor, _, _ = _bin_aligned_phase(grid, bin_y=1, bin_x=-1)
    transverse = _vector_field(
        torch.stack((phasor, 0.5 * phasor)).unsqueeze(0),
        grid=grid,
    )
    full = vector_angular_spectrum(transverse, axial_distance=0.0)

    accepted = vector_angular_spectrum(full, axial_distance=0.0)

    assert torch.allclose(accepted.envelope, full.envelope)
    corrupted_envelope = full.envelope.clone()
    corrupted_envelope[:, 2] = corrupted_envelope[:, 2] + 0.1
    corrupted = _vector_field(
        corrupted_envelope,
        grid=grid,
        representation=PolarizationRepresentation.FULL,
    )
    with pytest.raises(OpticalError) as caught:
        vector_angular_spectrum(corrupted, axial_distance=0.0)
    assert (
        caught.value.identity
        == "vector_angular_spectrum_full_field_not_transverse"
    )


def test_meta_execution_is_structural_and_changes_polarization_axis() -> None:
    """
    Meta 执行只检查结构并把偏振轴扩展为完整表示
    """
    grid = SpatialGrid.centered(
        sample_counts=(5, 7),
        sample_spacing=(2.0e-6, 1.5e-6),
    )
    field = _vector_field(
        torch.empty(
            (3, 1, 2, 5, 7),
            dtype=torch.complex128,
            device="meta",
        ),
        grid=grid,
    )

    output = vector_angular_spectrum(field, axial_distance=0.4e-6)

    assert output.envelope.shape == (3, 1, 3, 5, 7)
    assert output.envelope.dtype is torch.complex128
    assert output.envelope.device.type == "meta"
    assert output.polarization_representation is PolarizationRepresentation.FULL


def test_envelope_and_axial_distance_pass_gradcheck() -> None:
    """
    输入包络与轴向距离共同通过公开动作的梯度检查
    """
    grid = SpatialGrid.centered(
        sample_counts=(4, 5),
        sample_spacing=(2.0e-6, 2.5e-6),
    )
    generator = torch.Generator(device="cpu").manual_seed(42)
    real = torch.randn((1, 2, 4, 5), generator=generator, dtype=torch.float64)
    imaginary = torch.randn(
        (1, 2, 4, 5),
        generator=generator,
        dtype=torch.float64,
    )
    envelope = torch.complex(real, imaginary).requires_grad_(True)
    distance = torch.tensor(
        0.3e-6,
        dtype=torch.float64,
        requires_grad=True,
    )

    def action(
        values: torch.Tensor,
        axial_distance: torch.Tensor,
    ) -> torch.Tensor:
        """
        返回公开传播动作的实部总和
        """
        field = _vector_field(values, grid=grid)
        return vector_angular_spectrum(
            field,
            axial_distance=axial_distance,
        ).envelope.real.sum()

    assert torch.autograd.gradcheck(
        action,
        (envelope, distance),
        eps=1.0e-9,
        atol=1.0e-5,
        rtol=1.0e-4,
    )


def test_trainable_input_grid_is_rejected() -> None:
    """
    矢量传播拒绝可训练输入网格以冻结几何边界
    """
    spacing_y = torch.tensor(
        2.0e-6,
        dtype=torch.float64,
        requires_grad=True,
    )
    grid = SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(
            spacing_y,
            torch.tensor(2.0e-6, dtype=torch.float64),
        ),
    )
    field = _vector_field(
        torch.ones((1, 2, 4, 4), dtype=torch.complex128),
        grid=grid,
    )

    with pytest.raises(OpticalError) as caught:
        vector_angular_spectrum(field, axial_distance=0.0)

    assert (
        caught.value.identity
        == "vector_angular_spectrum_input_grid_requires_grad"
    )


def test_frozen_assembly_runs_vector_propagation_on_cpu() -> None:
    """
    冻结汇编通过 CPU 工作站运行矢量传播（固定 double 精度）
    """
    grid = SpatialGrid.centered(
        sample_counts=(6, 8),
        sample_spacing=(2.0e-6, 2.0e-6),
    )
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=4.0e-6),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    propagation = VectorAngularSpectrum(axial_distance=0.6e-6)
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(propagation, name="propagation")
    assembly.connect(source, propagation)
    assembly.expose(propagation, name="field")
    assembly.freeze()
    workstation = Workstation.cpu()
    workstation.host(assembly)

    outputs, record = workstation.run(assembly)

    field = outputs["field"]
    assert isinstance(field, OpticalField)
    assert field.polarization_representation is PolarizationRepresentation.FULL
    assert field.envelope.dtype is torch.complex128
    assert record.peak_memory_bytes >= 0


def test_batched_multispectrum_dispersion_and_translation_match_modes() -> None:
    """
    批量多谱色散在平移目标与负距离下逐模匹配解析解
    """
    grid = SpatialGrid.centered(
        sample_counts=(8, 10),
        sample_spacing=(1.0e-6, 1.25e-6),
    )
    phasor, wavevector_y, wavevector_x = _bin_aligned_phase(
        grid,
        bin_y=1,
        bin_x=-1,
    )
    spectrum_envelope = torch.stack(
        (
            torch.stack((phasor, 0.2j * phasor)),
            torch.stack((0.7 * phasor, -0.3j * phasor)),
        ),
    )
    envelope = torch.stack((spectrum_envelope, 1.4 * spectrum_envelope))
    wavelengths = (3.8e-6, 4.2e-6)
    medium = TabulatedMedium(
        wavelengths=wavelengths,
        refractive_indices=(1.1, 1.3),
    )
    field = _vector_field(
        envelope,
        grid=grid,
        wavelengths=wavelengths,
        medium=medium,
    )
    displacement = (0.35e-6, -0.2e-6)
    destination = SpatialGrid(
        sample_counts=grid.sample_counts,
        sample_spacing=grid.sample_spacing,
        first_sample_position=(
            grid.first_sample_position[0] + displacement[0],
            grid.first_sample_position[1] + displacement[1],
        ),
        orientation=grid.orientation,
    )
    axial_distance = -0.8e-6

    output = vector_angular_spectrum(
        field,
        axial_distance=axial_distance,
        destination_grid=destination,
    )
    actual_displacement = (
        float(
            destination.first_sample_position[0]
            - grid.first_sample_position[0],
        ),
        float(
            destination.first_sample_position[1]
            - grid.first_sample_position[1],
        ),
    )

    expected_spectra: list[torch.Tensor] = []
    for spectral_index, (wavelength, index) in enumerate(
        zip(wavelengths, (1.1, 1.3), strict=True),
    ):
        wave_number = 2.0 * math.pi * index / wavelength
        longitudinal_wave_number = math.sqrt(
            wave_number**2 - wavevector_y**2 - wavevector_x**2,
        )
        transverse = envelope[:, spectral_index]
        longitudinal = -(
            wavevector_x * transverse[:, 0]
            + wavevector_y * transverse[:, 1]
        ) / longitudinal_wave_number
        vector = torch.cat(
            (transverse, longitudinal.unsqueeze(1)),
            dim=1,
        )
        phase = (
            (longitudinal_wave_number - wave_number) * axial_distance
            + wavevector_y * actual_displacement[0]
            + wavevector_x * actual_displacement[1]
        )
        expected_spectra.append(
            vector * complex(math.cos(phase), math.sin(phase)),
        )
    expected = torch.stack(expected_spectra, dim=1)
    tolerance = 65536.0 * torch.finfo(torch.float64).eps
    assert output.grid.is_physically_equivalent_to(destination)
    maximum_error = (output.envelope - expected).abs().max()
    assert float(maximum_error) <= tolerance
    assert tuple(
        float(value) for value in output.path_reference.lengths
    ) == pytest.approx(
        (
            1.1 * axial_distance,
            1.3 * axial_distance,
        ),
    )


def test_two_distinct_vector_modes_match_independent_analytic_superposition() -> None:
    """
    两个不同波矢与复矢量振幅按独立解析解重建并叠加
    """
    grid = SpatialGrid.centered(
        sample_counts=(12, 14),
        sample_spacing=(1.0e-6, 1.0e-6),
    )
    mode_definitions = (
        ((1, 2), (0.7 + 0.2j, -0.1 + 0.35j)),
        ((-2, 1), (-0.25 + 0.4j, 0.6 - 0.15j)),
    )
    transverse = torch.zeros((2, *grid.sample_counts), dtype=torch.complex128)
    analytic_modes: list[
        tuple[torch.Tensor, float, float, complex, complex]
    ] = []
    for (bin_y, bin_x), (amplitude_x, amplitude_y) in mode_definitions:
        phasor, wavevector_y, wavevector_x = _bin_aligned_phase(
            grid,
            bin_y=bin_y,
            bin_x=bin_x,
        )
        transverse[0] = transverse[0] + amplitude_x * phasor
        transverse[1] = transverse[1] + amplitude_y * phasor
        analytic_modes.append(
            (
                phasor,
                wavevector_y,
                wavevector_x,
                amplitude_x,
                amplitude_y,
            ),
        )
    field = _vector_field(transverse.unsqueeze(0), grid=grid, wavelengths=(5e-6,))
    displacement = (0.2e-6, -0.3e-6)
    destination = SpatialGrid(
        sample_counts=grid.sample_counts,
        sample_spacing=grid.sample_spacing,
        first_sample_position=(
            grid.first_sample_position[0] + displacement[0],
            grid.first_sample_position[1] + displacement[1],
        ),
        orientation=grid.orientation,
    )
    axial_distance = 0.4e-6

    output = vector_angular_spectrum(
        field,
        axial_distance=axial_distance,
        destination_grid=destination,
    )

    expected = torch.zeros((3, *grid.sample_counts), dtype=torch.complex128)
    wave_number = 2.0 * math.pi / 5.0e-6
    actual_displacement = (
        float(destination.first_sample_position[0] - grid.first_sample_position[0]),
        float(destination.first_sample_position[1] - grid.first_sample_position[1]),
    )
    for phasor, wavevector_y, wavevector_x, amplitude_x, amplitude_y in (
        analytic_modes
    ):
        longitudinal_wave_number = math.sqrt(
            wave_number**2 - wavevector_y**2 - wavevector_x**2,
        )
        amplitude_z = -(
            wavevector_x * amplitude_x + wavevector_y * amplitude_y
        ) / longitudinal_wave_number
        phase = (
            (longitudinal_wave_number - wave_number) * axial_distance
            + wavevector_y * actual_displacement[0]
            + wavevector_x * actual_displacement[1]
        )
        transfer = complex(math.cos(phase), math.sin(phase))
        expected = expected + torch.stack(
            (
                amplitude_x * phasor * transfer,
                amplitude_y * phasor * transfer,
                amplitude_z * phasor * transfer,
            ),
        )
    tolerance = 65536.0 * torch.finfo(torch.float64).eps
    assert torch.allclose(
        output.envelope[0],
        expected,
        rtol=tolerance,
        atol=tolerance,
    )


def test_evanescent_modes_are_zero_and_propagation_stays_finite() -> None:
    """
    倏逝（``Q<0``）频箱被严格 ``Q>0`` 分类归零；近掠入（``Q`` 小正）
    频箱不再被任意 ``sqrt(eps)`` 截断，但仍给出有限传播结果——非有限时由既有物理
    有限化所有者承担。
    """
    wavelength = 4.0e-6
    grid = SpatialGrid.centered(
        sample_counts=(4, 8),
        sample_spacing=(2.0e-6, 0.5e-6),
    )
    evanescent, _, _ = _bin_aligned_phase(grid, bin_y=0, bin_x=2)
    field = _vector_field(
        torch.stack(
            (
                evanescent,
                torch.zeros_like(evanescent),
            ),
        ).unsqueeze(0).to(dtype=torch.complex128),
        grid=grid,
        wavelengths=(wavelength,),
    )

    output = vector_angular_spectrum(field, axial_distance=0.0)

    assert bool(torch.isfinite(output.envelope).all())
    assert torch.allclose(
        output.envelope,
        torch.zeros_like(output.envelope),
        atol=2.0e-6,
        rtol=0.0,
    )


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="Windows CUDA evidence requires an available CUDA device",
)
def test_available_windows_cuda_matches_cpu() -> None:
    """
    可用 Windows CUDA 路径与 CPU 矢量传播保持一致
    """
    grid = SpatialGrid.centered(
        sample_counts=(8, 10),
        sample_spacing=(1.0e-6, 1.25e-6),
    )
    phasor, _, _ = _bin_aligned_phase(grid, bin_y=1, bin_x=1)
    cpu_field = _vector_field(
        torch.stack((phasor, 0.25j * phasor)).unsqueeze(0).to(
            dtype=torch.complex128,
        ),
        grid=grid,
    )
    cuda_field = _vector_field(
        cpu_field.envelope.to(device="cuda"),
        grid=grid.to(device="cuda", dtype=torch.float64),
    )

    cpu_output = vector_angular_spectrum(
        cpu_field,
        axial_distance=0.9e-6,
    )
    cuda_output = vector_angular_spectrum(
        cuda_field,
        axial_distance=0.9e-6,
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


def test_vector_equation_transverse_modal_mapping_holds_across_radiative_band() -> None:
    """
    方程证据：每个准入横向模态均保持矢量 Helmholtz 纵向映射
    这是 VectorAngularSpectrum 的方程证据，不是近似精度或标量截止。
    """

    sample_count = 32
    wavelength = 0.5e-6
    axial_distance = 1.0e-6
    wave_number = 2.0 * math.pi / wavelength
    for transverse_fraction in (0.4, 0.2, 0.1):
        spacing = wavelength / (sample_count * transverse_fraction)
        grid = SpatialGrid.centered(
            sample_counts=(sample_count, sample_count),
            sample_spacing=(spacing, spacing),
        )
        phasor, wavevector_y, wavevector_x = _bin_aligned_phase(
            grid,
            bin_y=0,
            bin_x=1,
        )
        envelope = torch.stack(
            (phasor, torch.zeros_like(phasor)),
        ).unsqueeze(0)
        output = vector_angular_spectrum(
            _vector_field(envelope, grid=grid, wavelengths=(wavelength,)),
            axial_distance=axial_distance,
        )
        longitudinal_wave_number = math.sqrt(
            wave_number**2 - wavevector_y**2 - wavevector_x**2,
        )
        expected_ratio = -wavevector_x / longitudinal_wave_number
        actual_ratio = output.envelope[:, 2] / output.envelope[:, 0]
        assert torch.allclose(
            actual_ratio,
            torch.full_like(actual_ratio, expected_ratio),
            rtol=2.0e-12,
            atol=2.0e-12,
        )

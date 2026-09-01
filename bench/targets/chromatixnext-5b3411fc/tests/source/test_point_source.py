
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next import install_state
from chromatix_next.errors import AssemblyError
from chromatix_next.optics import (
    Assembly,
    ConstantMedium,
    FieldNormalization,
    Intensity,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PolarizationRepresentation,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics._meta_inference import _meta_inference
from chromatix_next.optics.combination import CoherentCombination
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.grid import PropagationExterior
from chromatix_next.optics.propagation import scaled_angular_spectrum
from chromatix_next.optics.source import PointSource
from chromatix_next.workstation import Workstation

_cuda_unavailable = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA 不可用",
)


def _grid(
    counts: tuple[int, int] = (8, 8),
    spacing: tuple[float, float] = (0.2e-6, 0.2e-6),
) -> SpatialGrid:
    # 构造中心对齐的横向网格
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )


def _monochromatic(wavelength: float = 0.5e-6) -> Spectrum:
    # 构造单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _forward_on_meta(source: PointSource, grid: SpatialGrid) -> OpticalField:
    # 在 meta 设备上执行光源自己的前向，只得到形状与数据类型
    missing = object()
    original_forward = source.__dict__.get("forward", missing)
    with _meta_inference((source,)) as sandbox:
        assert source.__dict__.get("forward", missing) is original_forward
        result = sandbox.module(source)(grid)
    assert source.__dict__.get("forward", missing) is original_forward
    return result


def _independent_spherical_phasor(
    grid: SpatialGrid,
    wavelength: float,
    position_yxz: tuple[float, float, float],
    real_dtype: torch.dtype,
) -> tuple[torch.Tensor, torch.Tensor]:
    counts_y, counts_x = grid.sample_counts
    spacing_y, spacing_x = grid.sample_spacing
    first_y, first_x = grid.first_sample_position
    position_y = (
        torch.arange(counts_y, dtype=real_dtype) * float(spacing_y) + float(first_y)
    )
    position_x = (
        torch.arange(counts_x, dtype=real_dtype) * float(spacing_x) + float(first_x)
    )
    source_y, source_x, source_z = position_yxz
    delta_y = position_y.reshape(-1, 1) - source_y
    delta_x = position_x.reshape(1, -1) - source_x
    radius = torch.sqrt(
        delta_y * delta_y + delta_x * delta_x + source_z * source_z
    )
    wave_number = 2.0 * math.pi / wavelength
    phase = wave_number * radius
    phasor = torch.complex(torch.cos(phase), torch.sin(phase))
    return radius, phasor


@pytest.mark.cuda
@_cuda_unavailable
def test_point_source_public_source_matches_cpu_on_cuda() -> None:
    """
    PointSource 公共源在 CUDA 上保持与 CPU 相同的复包络
    """

    cpu_source = PointSource(
        spectrum=_monochromatic(),
        polarization=Polarization.scalar(),
        position=(0.0, 0.0, 2.0e-6),
        relative_amplitude=1.0,
    )
    cuda_source = PointSource(
        spectrum=_monochromatic(),
        polarization=Polarization.scalar(),
        position=(0.0, 0.0, 2.0e-6),
        relative_amplitude=1.0,
    ).cuda()

    cpu_field = cpu_source(_grid())
    cuda_field = cuda_source(_grid())

    torch.testing.assert_close(cpu_field.envelope, cuda_field.envelope.cpu())


class TestPhysicalInvariants:
    """
    证据层 1：物理不变量
    """

    def test_relative_amplitude_yields_relative_field(self) -> None:
        """
        仅提供相对振幅时输出光场归一化为 RELATIVE
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 2.0e-6),
            relative_amplitude=1.5,
        )
        field = source(_grid())
        assert isinstance(field, OpticalField)
        assert field.normalization is FieldNormalization.RELATIVE

    def test_total_power_yields_power_field(self) -> None:
        """
        仅提供总功率时输出光场归一化为 POWER
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 2.0e-6),
            total_power=1.0e-3,
        )
        field = source(_grid())
        assert field.normalization is FieldNormalization.POWER

    def test_relative_synthesis_matches_frozen_value_and_gradient(self) -> None:
        """
        共享生命周期前后的相对归一化值与梯度逐位相同
        """
        relative_amplitude = torch.nn.Parameter(
            torch.tensor(1.25, dtype=torch.float64),
        )
        source = PointSource(
            spectrum=_monochromatic(wavelength=2.0e-6),
            polarization=Polarization.scalar(),
            position=(0.0, 0.0, 2.0e-6),
            relative_amplitude=relative_amplitude,
        )
        envelope = source(
            _grid(counts=(2, 2), spacing=(1.0e-6, 1.0e-6)),
        ).envelope
        expected_envelope = torch.tensor(
            (
                complex(
                    float.fromhex("0x1.9486615239ae2p-3"),
                    float.fromhex("0x1.3bfac8330316ap+0"),
                ),
                complex(
                    float.fromhex("0x1.d7ea84591623ep-1"),
                    float.fromhex("0x1.b050546e8bf18p-1"),
                ),
                complex(
                    float.fromhex("0x1.d7ea84591623ep-1"),
                    float.fromhex("0x1.b050546e8bf18p-1"),
                ),
                complex(float.fromhex("0x1.4000000000000p+0"), 0.0),
            ),
            dtype=torch.complex128,
        ).reshape(1, 1, 2, 2)

        assert torch.equal(envelope, expected_envelope)
        observation = envelope.real.sum() + 0.25 * envelope.imag.sum()
        gradient = torch.autograd.grad(observation, relative_amplitude)[0]
        assert torch.equal(
            gradient,
            torch.tensor(
                float.fromhex("0x1.9bd26fde4d3e5p+1"),
                dtype=torch.float64,
            ),
        )

    def test_power_synthesis_matches_frozen_value_and_gradient(self) -> None:
        """
        共享生命周期前后的功率归一化值与梯度逐位相同
        """
        total_power = torch.nn.Parameter(
            torch.tensor(1.0, dtype=torch.float64),
        )
        source = PointSource(
            spectrum=_monochromatic(wavelength=2.0e-6),
            polarization=Polarization.scalar(),
            position=(0.0, 0.0, 2.0e-6),
            total_power=total_power,
        )
        envelope = source(
            _grid(counts=(2, 2), spacing=(1.0e-6, 1.0e-6)),
        ).envelope
        expected_envelope = torch.tensor(
            (
                complex(
                    float.fromhex("0x1.16d90d385f53ap+16"),
                    float.fromhex("0x1.b39f90237ba29p+18"),
                ),
                complex(
                    float.fromhex("0x1.6459bd7428ab5p+18"),
                    float.fromhex("0x1.4672402d50fa8p+18"),
                ),
                complex(
                    float.fromhex("0x1.6459bd7428ab5p+18"),
                    float.fromhex("0x1.4672402d50fa8p+18"),
                ),
                complex(float.fromhex("0x1.0e286ab9bba76p+19"), 0.0),
            ),
            dtype=torch.complex128,
        ).reshape(1, 1, 2, 2)

        assert torch.equal(envelope, expected_envelope)
        observation = envelope.real.sum() + 0.25 * envelope.imag.sum()
        gradient = torch.autograd.grad(observation, total_power)[0]
        assert torch.equal(
            gradient,
            torch.tensor(
                float.fromhex("0x1.8eb6e5f259f81p+19"),
                dtype=torch.float64,
            ),
        )

    def test_neither_normalization_rejected(self) -> None:
        """
        既不提供相对振幅也不提供总功率须以稳定身份拒绝
        """
        with pytest.raises(
            ValueError,
            match="point_source_normalization_missing",
        ):
            PointSource(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                position=(0.0, 0.0, 2.0e-6),
            )

    def test_both_normalizations_rejected(self) -> None:
        """
        同时提供相对振幅与总功率须以稳定身份拒绝
        """
        with pytest.raises(
            ValueError,
            match="point_source_normalization_exclusive",
        ):
            PointSource(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                position=(0.0, 0.0, 2.0e-6),
                relative_amplitude=1.0,
                total_power=1.0,
            )

    @pytest.mark.parametrize(
        ("parameter_name", "identity"),
        (
            ("relative_amplitude", "point_source_relative_amplitude_invalid"),
            ("total_power", "point_source_total_power_invalid"),
        ),
    )
    def test_scale_parameter_obeys_fixed_double_admission(
        self,
        parameter_name: str,
        identity: str,
    ) -> None:
        """
        每个公开尺度参数拒绝 float32 Parameter 与普通 Tensor
        """

        base_arguments: dict[str, object] = {
            "spectrum": _monochromatic(),
            "polarization": Polarization.scalar(),
            "position": (0.0, 0.0, 2.0e-6),
        }
        for invalid_value in (
            torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float32)),
            torch.tensor(1.0, dtype=torch.float64),
        ):
            arguments = dict(base_arguments)
            arguments[parameter_name] = invalid_value
            with pytest.raises((TypeError, ValueError), match=identity):
                PointSource(**arguments)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "parameter_name",
        ("relative_amplitude", "total_power"),
    )
    def test_scale_parameter_keeps_optimizer_identity(
        self,
        parameter_name: str,
    ) -> None:
        """
        每个合法尺度 Parameter 保持同一注册对象并对优化器可见
        """

        parameter = torch.nn.Parameter(
            torch.tensor(1.0, dtype=torch.float64),
        )
        arguments: dict[str, object] = {
            "spectrum": _monochromatic(),
            "polarization": Polarization.scalar(),
            "position": (0.0, 0.0, 2.0e-6),
            parameter_name: parameter,
        }
        source = PointSource(**arguments)  # type: ignore[arg-type]

        assert getattr(source, parameter_name) is parameter
        assert dict(source.named_parameters())[parameter_name] is parameter

    @pytest.mark.parametrize(
        "invalid_position",
        [
            (float("nan"), 0.0, 1.0),
            (0.0, float("inf"), 1.0),
            (0.0, 0.0, float("nan")),
        ],
    )
    def test_non_finite_position_rejected(
        self,
        invalid_position: tuple[float, float, float],
    ) -> None:
        """
        位置含非有限分量须以稳定身份拒绝
        """
        with pytest.raises(
            ValueError,
            match="point_source_position_invalid",
        ):
            PointSource(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                position=invalid_position,
                relative_amplitude=1.0,
            )

    def test_wrong_shape_position_tensor_rejected(self) -> None:
        """
        形状非 (3,) 的位置张量须以稳定身份拒绝
        """
        bad_position = torch.nn.Parameter(
            torch.tensor([0.0, 1.0], dtype=torch.float64)
        )
        with pytest.raises(
            ValueError,
            match="point_source_position_invalid",
        ):
            PointSource(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                position=bad_position,
                relative_amplitude=1.0,
            )

    def test_output_envelope_has_fixed_axes_and_complex_dtype(self) -> None:
        """
        输出包络遵循固定轴布局且为复数
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 2.0e-6),
            relative_amplitude=1.5,
        )
        field = source(_grid())
        assert field.envelope.shape == (1, 1, 8, 8)
        assert torch.is_complex(field.envelope)
        assert field.batch_shape == ()
        assert field.envelope.device.type == "cpu"

    def test_zero_path_reference_at_source(self) -> None:
        """
        源的光程参考从零起算（与 PlaneWave/GaussianBeam 的 OPR 约定一致）
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            position=(0.0, 0.0, 2.0e-6),
            relative_amplitude=1.0,
        )
        field = source(_grid())
        assert field.path_reference == OpticalPathReference(lengths=(0.0,))

    def test_user_parameter_identity_preserved(self) -> None:
        """
        用户 supplied Parameter 须保持身份注册，不被克隆
        """
        position = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 2.0e-6), dtype=torch.float64)
        )
        amplitude = torch.nn.Parameter(torch.tensor(1.5, dtype=torch.float64))
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=position,
            relative_amplitude=amplitude,
        )
        assert source.position is position
        assert source.relative_amplitude is amplitude
        assert position in set(source.parameters())
        assert amplitude in set(source.parameters())

    def test_fixed_grid_reuses_registered_unit_envelope(self) -> None:
        """
        相同固定点源与网格连续前向复用同一份单位包络缓存
        """
        grid = _grid()
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            position=(0.0, 0.0, 2.0e-6),
            relative_amplitude=1.0,
        )

        source(grid)
        first_cache = dict(source.named_buffers())["_unit_envelope_cache"]
        source(grid)
        second_cache = dict(source.named_buffers())["_unit_envelope_cache"]

        assert first_cache is not None
        assert second_cache is first_cache

    def test_total_power_rejects_zero_weight_spectrum(self) -> None:
        """
        零权重光谱与总功率组合须在源边界以稳定身份拒绝
        """
        wavelengths = (0.5e-6,)
        weights = (0.0,)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        source = PointSource(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 2.0e-6),
            total_power=1.0e-3,
        )
        with pytest.raises(
            ValueError,
            match="point_source_total_power_spectrum_weight_sum_invalid",
        ):
            source(_grid())


class TestIndependentReference:
    """
    证据层 2：独立解析参照
    """

    def test_on_axis_spherical_phase_matches_independent_reference(self) -> None:
        """
        轴上点源（位于 grid 中心正上方）球面相位与独立 exp(ikr) 参照一致
        """
        wavelength = 0.5e-6
        position = (0.0, 0.0, 2.0e-6)
        grid = _grid()
        source = PointSource(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=position,
            relative_amplitude=1.0,
        )
        field = source(grid)
        _radius, reference_phasor = _independent_spherical_phasor(
            grid,
            wavelength,
            position,
            torch.float64,
        )
        assert torch.allclose(field.envelope[0, 0], reference_phasor, atol=1e-12)

    def test_off_axis_spherical_phase_matches_independent_reference(self) -> None:
        """
        偏轴点源（y、x、z 均偏离 grid 中心）球面相位与独立参照一致
        """
        wavelength = 0.5e-6
        position = (0.3e-6, -0.2e-6, 1.5e-6)
        grid = _grid(counts=(9, 7), spacing=(0.25e-6, 0.2e-6))
        source = PointSource(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=position,
            relative_amplitude=1.0,
        )
        field = source(grid)
        _radius, reference_phasor = _independent_spherical_phasor(
            grid,
            wavelength,
            position,
            torch.float64,
        )
        assert torch.allclose(field.envelope[0, 0], reference_phasor, atol=1e-12)

    def test_power_amplitude_decays_as_one_over_radius(self) -> None:
        """
        POWER 模式下振幅按 1/r 衰减：相同方位上更远点的振幅严格小于更近点
        """
        grid = _grid()
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 2.0e-6),
            total_power=1.0e-3,
        )
        field = source(grid)
        center_modulus = float(field.envelope[0, 0, 4, 4].abs())
        neighbour_modulus = float(field.envelope[0, 0, 3, 4].abs())
        # 中心 r = 2e-6；邻点 r = sqrt(0.2² + 2²) e-6 > 2e-6，振幅更小
        assert neighbour_modulus < center_modulus
        # 严格 1/r：中心与邻点的模长比等于半径比的倒数
        r_center = 2.0e-6
        r_neighbour = math.sqrt(0.2e-6 ** 2 + 2.0e-6 ** 2)
        ratio = centre_to_neighbour_ratio(center_modulus, neighbour_modulus)
        assert math.isclose(ratio, r_neighbour / r_center, rel_tol=1e-9)

    def test_rotational_symmetry_around_source_axis(self) -> None:
        """
        绕源轴等距点的复包络严格相同（球面波旋转对称）
        """
        grid = _grid(counts=(5, 5), spacing=(0.2e-6, 0.2e-6))
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 1.0e-6),
            relative_amplitude=1.0,
        )
        field = source(grid)
        neighbours = (
            field.envelope[0, 0, 1, 1],
            field.envelope[0, 0, 1, 3],
            field.envelope[0, 0, 3, 1],
            field.envelope[0, 0, 3, 3],
        )
        for value in neighbours[1:]:
            assert torch.allclose(value, neighbours[0], atol=1e-12)

    def test_non_vacuum_medium_uses_medium_wave_number(self) -> None:
        """
        非真空介质中球面相位按介质波数 k = 2π n / λ 合成
        """
        wavelength = 0.5e-6
        index = 1.5
        position = (0.0, 0.0, 2.0e-6)
        grid = _grid()
        source = PointSource(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=ConstantMedium(index=index),
            position=position,
            relative_amplitude=1.0,
        )
        field = source(grid)
        # 独立参照：相位 = 2π n r / λ
        counts_y, counts_x = grid.sample_counts
        spacing_y, spacing_x = grid.sample_spacing
        first_y, first_x = grid.first_sample_position
        position_y = (
            torch.arange(counts_y, dtype=torch.float64) * float(spacing_y)
            + float(first_y)
        )
        position_x = (
            torch.arange(counts_x, dtype=torch.float64) * float(spacing_x)
            + float(first_x)
        )
        radius = torch.sqrt(
            (position_y.reshape(-1, 1)) ** 2
            + (position_x.reshape(1, -1)) ** 2
            + position[2] ** 2
        )
        phase = 2.0 * math.pi * index * radius / wavelength
        reference_angle = torch.remainder(phase, 2.0 * math.pi)
        # 把 (-π, π] 与 [0, 2π) 两种表示统一比较：直接比复数值更稳
        reference_phasor = torch.complex(torch.cos(phase), torch.sin(phase))
        assert torch.allclose(field.envelope[0, 0], reference_phasor, atol=1e-12)
        # angle 检查留作断言 reference_angle 不被消费——避免未使用变量告警
        assert reference_angle.shape == radius.shape

    def test_multispectral_envelope_shape(self) -> None:
        """
        多光谱多分量偏振输出形状遵循 (光谱, 偏振, 高, 宽)
        """
        wavelengths = (0.45e-6, 0.55e-6, 0.65e-6)
        weights = (0.3, 0.4, 0.3)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        source = PointSource(
            spectrum=spectrum,
            polarization=Polarization.linear_y(),
            medium=ConstantMedium(index=1.3),
            position=(0.0, 0.0, 3.0e-6),
            relative_amplitude=1.0,
        )
        field = source(_grid())
        assert field.envelope.shape == (3, 2, 8, 8)


def centre_to_neighbour_ratio(center: float, neighbour: float) -> float:
    """
    返回中心振幅与邻点振幅之比
    """
    return center / neighbour


class TestFiniteOriginGuard:
    """
    finite-origin 适用域守护：奇点与采样不足以稳定身份拒绝，无 epsilon 软化
    """

    def test_origin_on_grid_plane_rejected(self) -> None:
        """
        源 z 分量为零（落在 grid 平面上）须以稳定身份拒绝
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            position=(0.0, 0.0, 0.0),
            relative_amplitude=1.0,
        )
        with pytest.raises(
            ValueError,
            match="point_source_origin_on_grid",
        ):
            source(_grid())

    def test_origin_with_zero_trainable_z_rejected_at_forward(self) -> None:
        """
        可训练 z 分量在 forward 时取零须以稳定身份拒绝（构造期允许，运行时守护）
        """
        position = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 0.0), dtype=torch.float64)
        )
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            position=position,
            relative_amplitude=1.0,
        )
        with pytest.raises(
            ValueError,
            match="point_source_origin_on_grid",
        ):
            source(_grid())

    def test_insufficient_sampling_rejected(self) -> None:
        """
        grid 采样不足以分辨球面波横向相位须以稳定身份拒绝
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            position=(0.0, 0.0, 1.0e-6),
            relative_amplitude=1.0,
        )
        coarse_grid = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(5.0e-6, 5.0e-6),
        )
        with pytest.raises(
            ValueError,
            match="point_source_sampling_insufficient",
        ):
            source(coarse_grid)

    def test_origin_on_grid_rejected_before_sampling_check(self) -> None:
        """
        z=0 奇点优先于采样检查（更根本的物理错误）
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            position=(0.0, 0.0, 0.0),
            relative_amplitude=1.0,
        )
        coarse_grid = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(5.0e-6, 5.0e-6),
        )
        with pytest.raises(
            ValueError,
            match="point_source_origin_on_grid",
        ):
            source(coarse_grid)


class TestGeometryAwareSamplingBoundary:
    """
    几何感知采样栅栏：居中/偏轴/近场/远场/掠射与边界两侧的准入和拒绝
    """

    _BOUNDARY_GRID = SpatialGrid.centered(
        sample_counts=(8, 8),
        sample_spacing=(0.5e-6, 0.5e-6),
    )

    def test_centered_boundary_valid_admitted(self) -> None:
        """
        centered 源在 sz=4 μm（advance < π）被准入并产出球面波包络
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 4.0e-6),
            relative_amplitude=1.0,
        )
        field = source(self._BOUNDARY_GRID)
        assert field.envelope.shape == (1, 1, 8, 8)

    def test_centered_boundary_invalid_rejected(self) -> None:
        """
        centered 源在 sz=3 μm（advance > π）以稳定身份被拒绝
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 3.0e-6),
            relative_amplitude=1.0,
        )
        with pytest.raises(
            ValueError,
            match="point_source_sampling_insufficient",
        ):
            source(self._BOUNDARY_GRID)

    def test_off_axis_boundary_valid_admitted(self) -> None:
        """
        off-axis 源（横向投影在窗口外）在 sz=10 μm 被准入：真实局部 phase demand < π
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(3.0e-6, 0.0, 10.0e-6),
            relative_amplitude=1.0,
        )
        field = source(self._BOUNDARY_GRID)
        assert field.envelope.shape == (1, 1, 8, 8)

    def test_off_axis_boundary_invalid_rejected(self) -> None:
        """
        off-axis 源（横向投影在窗口外）在 sz=7 μm 以稳定身份被拒绝：advance > π
        """
        # sz=7 μm → 相位推进 ≈ 3.53 弧度 > π（拒绝）
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(3.0e-6, 0.0, 7.0e-6),
            relative_amplitude=1.0,
        )
        with pytest.raises(
            ValueError,
            match="point_source_sampling_insufficient",
        ):
            source(self._BOUNDARY_GRID)

    def test_off_axis_grazing_source_rejected(self) -> None:
        """
        源横向投影远离窗口（掠射几何）即使 sz 较大也被拒绝：ρ/r 接近 1
        """
        # 源在 (100,0,5) μm，y 向最远 ≈ 102 μm，ρ/r ≈ 0.999，每样本相位推进 ≈ 6.28
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(100.0e-6, 0.0, 5.0e-6),
            relative_amplitude=1.0,
        )
        with pytest.raises(
            ValueError,
            match="point_source_sampling_insufficient",
        ):
            source(self._BOUNDARY_GRID)

    def test_near_field_fine_grid_admitted(self) -> None:
        """
        近场（sz=0.5 μm）在加密网格下被准入：小窗口使 advance 远低于 π
        """
        near_grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.1e-6, 0.1e-6),
        )
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 0.5e-6),
            relative_amplitude=1.0,
        )
        field = source(near_grid)
        assert field.envelope.shape == (1, 1, 8, 8)

    def test_far_field_coarse_grid_admitted(self) -> None:
        """
        远场（sz=100 μm）即使较粗网格也被准入：ρ/r 很小，advance 远低于 π
        """
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 100.0e-6),
            relative_amplitude=1.0,
        )
        field = source(self._BOUNDARY_GRID)
        assert field.envelope.shape == (1, 1, 8, 8)

    def test_oversampled_grid_admitted_where_coarse_rejected(  # noqa: PLR6301
        self,
    ) -> None:
        """
        加密网格在同一 centered 源下被准入而粗网格被拒，且加密包络与独立 phasor 一致
        """
        coarse = self._BOUNDARY_GRID
        fine = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.1e-6, 0.1e-6),
        )
        position = (0.0, 0.0, 2.0e-6)
        coarse_source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=position,
            relative_amplitude=1.0,
        )
        with pytest.raises(
            ValueError,
            match="point_source_sampling_insufficient",
        ):
            coarse_source(coarse)
        fine_source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=position,
            relative_amplitude=1.0,
        )
        field = fine_source(fine)
        _radius, reference_phasor = _independent_spherical_phasor(
            fine,
            0.5e-6,
            position,
            torch.float64,
        )
        assert torch.allclose(field.envelope[0, 0], reference_phasor, atol=1e-12)


class TestGradientEvidence:
    """
    证据层 3：梯度证据（连续点源位置与强度参数经源→探测链路保持 autograd）
    """

    def test_gradcheck_on_trainable_relative_amplitude(self) -> None:
        """
        对可训练相对振幅经 PointSource→IntensityDetection 链路做 gradcheck
        """
        amplitude = torch.nn.Parameter(torch.tensor(1.25, dtype=torch.float64))
        grid = _grid()
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 2.0e-6),
            relative_amplitude=amplitude,
        )
        detection = IntensityDetection()

        def run(amplitude_value: torch.Tensor) -> torch.Tensor:
            """
            返回给定振幅下的光强总和（实数标量）
            """
            return detection(source(grid)).values.sum()

        assert torch.autograd.gradcheck(run, (amplitude,), raise_exception=True)

    def test_gradcheck_on_trainable_total_power(self) -> None:
        """
        对可训练总功率经 PointSource→IntensityDetection 链路做 gradcheck
        """
        total_power = torch.nn.Parameter(torch.tensor(1.0e-3, dtype=torch.float64))
        grid = _grid()
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 2.0e-6),
            total_power=total_power,
        )
        detection = IntensityDetection()

        def run(total_power_value: torch.Tensor) -> torch.Tensor:
            """
            返回给定总功率下的光强空间总和
            """
            return detection(source(grid)).values.sum()

        assert torch.autograd.gradcheck(run, (total_power,), raise_exception=True)

    def test_gradcheck_on_trainable_position(self) -> None:
        """
        对可训练 position 经 ``PointSource``→``IntensityDetection`` 链路做梯度校验
        """
        position = torch.nn.Parameter(
            torch.tensor((0.1e-6, -0.1e-6, 2.0e-6), dtype=torch.float64)
        )
        grid = _grid()
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=position,
            relative_amplitude=1.0,
        )
        detection = IntensityDetection()

        def run(position_value: torch.Tensor) -> torch.Tensor:
            """
            返回给定位置下的光强总和
            """
            return detection(source(grid)).values.sum()

        assert torch.autograd.gradcheck(
            run,
            (position,),
            eps=1e-10,
            atol=1e-4,
            rtol=1e-3,
            raise_exception=True,
        )

    def test_position_z_gradient_matches_finite_difference(self) -> None:
        """
        可训练 z 的解析梯度与中心有限差分一致
        """
        position = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 2.0e-6), dtype=torch.float64)
        )
        grid = _grid()
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=position,
            relative_amplitude=1.0,
        )
        detection = IntensityDetection()

        def observe(z_value: float) -> float:
            """
            返回给定 z 下的光强总和（有限差分采样点）
            """
            local_source = PointSource(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                position=(0.0, 0.0, z_value),
                relative_amplitude=1.0,
            )
            return float(detection(local_source(grid)).values.sum())

        automatic_gradient = torch.autograd.grad(
            detection(source(grid)).values.sum(),
            position,
        )[0]
        z_automatic = float(automatic_gradient[2])
        step = 1.0e-12
        origin = float(position.detach()[2])
        finite_difference = (
            observe(origin + step) - observe(origin - step)
        ) / (2.0 * step)
        assert z_automatic == pytest.approx(
            finite_difference,
            rel=1.0e-6,
        )


class TestHostedExecution:
    """
    托管端到端：POWER 归一化与 Workstation replay
    """

    def test_hosted_power_source_total_power_integral(self) -> None:
        """
        托管 POWER 点源：Intensity 空间积分 × 单元面积 = 总功率
        """
        total_power = 2.5e-3
        grid = _grid(counts=(32, 32), spacing=(0.1e-6, 0.1e-6))
        workstation = Workstation.cpu()
        source = workstation.host(
            PointSource(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                position=(0.0, 0.0, 5.0e-6),
                total_power=total_power,
            ),
        )
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        assert field.normalization is FieldNormalization.POWER
        intensity = detection(field)
        integral = float(intensity.values.sum().item()) * grid.cell_area
        assert math.isclose(integral, total_power, rel_tol=1e-6)

    def test_frozen_assembly_preserves_point_source_and_total_power(self) -> None:
        """
        冻结装配托管运行保留偏振与声明总功率
        """
        grid = _grid(counts=(32, 32), spacing=(0.1e-6, 0.1e-6))
        total_power = 1.5e-3
        source = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.right_circular(),
            medium=ConstantMedium(index=1.3),
            position=(0.0, 0.0, 5.0e-6),
            total_power=total_power,
        )
        detection = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(detection, name="detection")
        assembly.connect(source, detection)
        assembly.expose(source, name="field")
        assembly.expose(detection, name="intensity")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        outputs, _record = workstation.run(assembly)
        field = outputs["field"]
        intensity = outputs["intensity"]
        assert isinstance(field, OpticalField)
        assert isinstance(intensity, Intensity)
        assert (
            field.polarization_representation
            is PolarizationRepresentation.TRANSVERSE
        )
        integral = float(intensity.values.sum().item()) * grid.cell_area
        assert math.isclose(integral, total_power, rel_tol=1e-6)


class TestMetaInference:
    """
    meta 设备上的形状与物理轮廓推导契约
    """

    def test_meta_forward_carries_full_physical_outline(self) -> None:
        """
        meta 上的前向给出与真实执行相同的网格、光谱、介质、偏振与归一化
        """
        spectrum = _monochromatic()
        polarization = Polarization.scalar()
        source = PointSource(
            spectrum=spectrum,
            polarization=polarization,
            medium=Vacuum(),
            position=(0.0, 0.0, 2.0e-6),
            total_power=1.0e-3,
        )
        grid = _grid()
        field = _forward_on_meta(source, grid)
        assert field.envelope.device.type == "meta"
        assert field.grid.sample_counts == grid.sample_counts
        assert field.spectrum == spectrum
        assert field.medium == Vacuum()
        assert field.normalization is FieldNormalization.POWER
        assert field.batch_shape == ()
        assert field.envelope_shape == (1, 1, 8, 8)
        assert field.envelope_shape == source(grid).envelope_shape


class TestSourceLineage:
    """
    Source Lineage 稳定：state_dict 加载不转移谱系
    """

    def test_loading_state_does_not_transfer_lineage(self) -> None:
        """
        载入另一源的状态字典后，两源仍判为不同谱系，相干组合以稳定身份拒绝
        """
        grid = _grid()
        original = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            position=(0.0, 0.0, 2.0e-6),
            relative_amplitude=1.0,
        )
        restored = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            position=(0.0, 0.0, 2.0e-6),
            relative_amplitude=1.0,
        )
        workstation = Workstation.cpu()
        workstation.host(original)
        install_state(restored, original.state_dict())
        original_field = original(grid)
        field = restored(grid)
        assert field.envelope.shape == original_field.envelope.shape
        with pytest.raises(
            AssemblyError,
            match="coherent_combination_source_lineage_mismatch",
        ):
            CoherentCombination()(original_field, field)


class TestStateRoundTrip:
    """
    点源固定物理状态的 PyTorch 序列化契约
    """

    def test_state_round_trip_preserves_named_physical_metadata(self) -> None:
        """
        命名载荷逐位恢复光谱与偏振，且单位包络缓存失效
        """
        grid = _grid()
        original = PointSource(
            spectrum=Spectrum(
                wavelengths=(0.48e-6, 0.63e-6),
                weights=(0.4, 0.6),
            ),
            polarization=Polarization.linear_y(),
            medium=ConstantMedium(index=1.4),
            position=(0.2e-6, -0.1e-6, 3.0e-6),
            relative_amplitude=1.0,
        )
        restored = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=ConstantMedium(index=1.4),
            position=(0.0, 0.0, 2.0e-6),
            relative_amplitude=1.0,
        )
        workstation = Workstation.cpu()
        workstation.host(original)
        install_state(restored, original.state_dict())
        original_field = original(grid)
        field = restored(grid)
        assert field.spectrum == original_field.spectrum
        assert (
            field.polarization_representation
            is original_field.polarization_representation
        )
        assert field.envelope.shape == (2, 2, 8, 8)
        assert torch.allclose(
            field.envelope,
            original_field.envelope,
            atol=1e-12,
        )


def test_point_power_richer_model_residual_decreases_with_plane_refinement() -> None:
    """
    近似模型证据：两平面共同细化时，标量 POWER 球面场趋近孤立角谱参照
    全局复相位对齐只去除独立载波；源位置、支撑和总功率保持不变。
    """

    source_range = 5.0e-6
    axial_distance = 5.0e-6
    residuals: list[float] = []
    for sample_count, spacing in (
        (24, 0.25e-6),
        (32, 0.20e-6),
        (48, 0.15e-6),
    ):
        grid = SpatialGrid.centered(
            sample_counts=(sample_count, sample_count),
            sample_spacing=(spacing, spacing),
        )
        first_plane = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, source_range),
            total_power=1.0e-3,
        )(grid)
        second_plane = PointSource(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, source_range + axial_distance),
            total_power=1.0e-3,
        )(grid)
        propagated = scaled_angular_spectrum(
            first_plane,
            axial_distance=axial_distance,
            destination_grid=grid,
            exterior=PropagationExterior.ISOLATED,
        )
        actual = propagated.envelope
        expected = second_plane.envelope
        alignment = (actual.conj() * expected).sum() / actual.abs().square().sum()
        residuals.append(
            float((alignment * actual - expected).abs().max())
            / float(expected.abs().max())
        )

    assert residuals[1] < residuals[0]
    assert residuals[2] < residuals[1]

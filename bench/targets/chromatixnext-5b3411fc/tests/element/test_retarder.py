
from __future__ import annotations

import copy
import math

import pytest
import torch

from chromatix_next.errors import OpticalTypeError, OpticalValueError
from chromatix_next.optics import (
    FieldNormalization,
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
from chromatix_next.optics.element import Retarder, retarder
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


def _grid(
    counts: tuple[int, int] = (5, 6),
    spacing: tuple[float, float] = (1.0e-6, 1.0e-6),
) -> SpatialGrid:
    # 中心对齐的横向网格
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )


def _spectrum(wavelength: float = 532.0e-9) -> Spectrum:
    # 单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _transverse_field(
    envelope: torch.Tensor,
    *,
    grid: SpatialGrid | None = None,
    spectrum: Spectrum | None = None,
) -> OpticalField:
    # 以显式横向包络构造光场
    if grid is None:
        counts_y, counts_x = envelope.shape[-2:]
        grid = SpatialGrid.centered(
            sample_counts=(counts_y, counts_x),
            sample_spacing=(1.0e-6, 1.0e-6),
        )
    if spectrum is None:
        spectrum = _spectrum()
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=spectrum,
        polarization_representation=PolarizationRepresentation.TRANSVERSE,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


def _constant_transverse_envelope(
    components: tuple[complex, complex],
    *,
    counts: tuple[int, int] = (5, 6),
) -> torch.Tensor:
    # 均匀常幅横向二分量包络
    counts_y, counts_x = counts
    component_x = torch.full(
        (counts_y, counts_x),
        components[0],
        dtype=torch.complex128,
    )
    component_y = torch.full(
        (counts_y, counts_x),
        components[1],
        dtype=torch.complex128,
    )
    return torch.stack((component_x, component_y)).unsqueeze(0)


def _random_transverse_envelope(
    counts: tuple[int, int] = (5, 6),
    *,
    seed: int = 42,
) -> torch.Tensor:
    # 随机横向二分量包络
    counts_y, counts_x = counts
    generator = torch.Generator().manual_seed(seed)
    real_part = torch.randn(
        (2, counts_y, counts_x),
        generator=generator,
        dtype=torch.float64,
    )
    imag_part = torch.randn(
        (2, counts_y, counts_x),
        generator=generator,
        dtype=torch.float64,
    )
    return torch.complex(real_part, imag_part).unsqueeze(0)


def _rotation_matrix(azimuth_radians: float) -> torch.Tensor:
    # 标准二维旋转矩阵，第一列为线本征态；与生产本征态公式独立
    cosine = math.cos(azimuth_radians)
    sine = math.sin(azimuth_radians)
    return torch.tensor(
        [[cosine, -sine], [sine, cosine]],
        dtype=torch.float64,
    )


def _diagonal_phasor_matrix(retardance_cycles: float) -> torch.Tensor:
    # 对角相位参照，用 torch.polar 独立构造，不复用周期相位私有所有者
    radians = math.pi * retardance_cycles
    positive_phasor = torch.polar(
        torch.tensor(1.0, dtype=torch.float64),
        torch.tensor(radians, dtype=torch.float64),
    )
    negative_phasor = torch.polar(
        torch.tensor(1.0, dtype=torch.float64),
        torch.tensor(-radians, dtype=torch.float64),
    )
    zero = torch.tensor(0.0, dtype=torch.complex128)
    return torch.stack(
        (
            torch.stack((positive_phasor, zero)),
            torch.stack((zero, negative_phasor)),
        ),
    )


def _independent_linear_eigenstate_retarder_matrix(
    retardance_cycles: float,
    azimuth_radians: float,
) -> torch.Tensor:
    # 线本征态延迟矩阵的独立参照：旋转、对角、旋转共轭三连乘
    rotation = _rotation_matrix(azimuth_radians).to(torch.complex128)
    diagonal = _diagonal_phasor_matrix(retardance_cycles)
    return rotation @ diagonal @ rotation.T


def _apply_matrix_to_envelope(
    matrix: torch.Tensor,
    envelope: torch.Tensor,
) -> torch.Tensor:
    # 把 Jones 矩阵逐点作用到横向二分量包络，独立于生产收缩记号
    component_x = (
        matrix[0, 0] * envelope[..., 0, :, :]
        + matrix[0, 1] * envelope[..., 1, :, :]
    )
    component_y = (
        matrix[1, 0] * envelope[..., 0, :, :]
        + matrix[1, 1] * envelope[..., 1, :, :]
    )
    return torch.stack((component_x, component_y), dim=-3)


def _conventional_quarter_wave_plate_matrix(
    retarded_axis_angle: float,
) -> torch.Tensor:
    # 约定四分之一波片 Jones 矩阵（恒定四分之一周期正延迟），独立量化公共相位移除
    cosine = math.cos(retarded_axis_angle)
    sine = math.sin(retarded_axis_angle)
    axis_x_factor = complex(sine * sine, cosine * cosine)
    axis_y_factor = complex(cosine * cosine, sine * sine)
    cross_axis_factor = complex(-1.0, 1.0) * cosine * sine
    return torch.tensor(
        [
            [axis_x_factor, cross_axis_factor],
            [cross_axis_factor, axis_y_factor],
        ],
        dtype=torch.complex128,
    )


class TestRetarderDuality:
    """
    延迟器函数与组件共享同一物理动作
    """

    def test_function_and_component_return_the_same_field(self) -> None:
        """
        同一延迟参数经直接函数与有状态组件得到相同强物理值
        """
        grid = _grid()
        spectrum = _spectrum()
        field = _transverse_field(
            _constant_transverse_envelope((1.0, 0.3 + 0.2j)),
            grid=grid,
            spectrum=spectrum,
        )

        direct = retarder(
            field,
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.pi / 7.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 10.0,
        )
        component = Retarder(
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.pi / 7.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 10.0,
        )
        delegated = component(field)

        assert torch.equal(delegated.envelope, direct.envelope)
        assert delegated.path_reference == direct.path_reference
        assert (
            delegated.polarization_representation
            is field.polarization_representation
        )

    def test_function_and_component_infer_the_same_meta_result(self) -> None:
        """
        直接函数与隔离组件在 meta 设备上推导相同形状与精度
        """
        grid = _grid()
        spectrum = _spectrum()
        real_field = _transverse_field(
            _constant_transverse_envelope((1.0, 0.0)),
            grid=grid,
            spectrum=spectrum,
        )
        meta_field = OpticalField(
            envelope=torch.empty_like(
                real_field.envelope,
                device="meta",
            ),
            grid=real_field.grid.to(
                device="meta",
                dtype=real_field.envelope.real.dtype,
            ),
            spectrum=real_field.spectrum,
            polarization_representation=real_field.polarization_representation,
            medium=real_field.medium,
            normalization=real_field.normalization,
            path_reference=real_field.path_reference,
        )
        component = Retarder(
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.pi / 7.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 10.0,
        )
        isolated = copy.deepcopy(component)
        isolated.to_empty(device="meta")

        direct = retarder(
            meta_field,
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.pi / 7.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 10.0,
        )
        delegated = isolated(meta_field)

        assert delegated.envelope.shape == direct.envelope.shape
        assert delegated.envelope.dtype is direct.envelope.dtype
        assert delegated.envelope.device.type == "meta"
        assert direct.envelope.device.type == "meta"


class TestRetarderPhysicalInvariants:
    """
    证据层 1：解析 SU(2) 不变量
    """

    def test_zero_retardance_is_bit_exact_identity(self) -> None:
        """
        零延迟时输出逐位等于输入（零均值规范下的严格单位矩阵）
        """
        grid = _grid()
        field = _transverse_field(_random_transverse_envelope(), grid=grid)

        output = retarder(
            field,
            retardance_cycles=0.0,
            retarded_eigenstate_azimuth_radians=math.pi / 5.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 9.0,
        )

        assert torch.equal(output.envelope, field.envelope)

    def test_inverse_is_negated_retardance_on_same_branch(self) -> None:
        """
        正负延迟复合回到输入，同一本征基、同一 SU(2) 支
        """
        grid = _grid()
        spectrum = _spectrum()
        envelope = _constant_transverse_envelope(
            (0.4 + 0.7j, -0.2 + 0.5j),
        )
        field = _transverse_field(envelope, grid=grid, spectrum=spectrum)
        shared_orientation = dict(
            retarded_eigenstate_azimuth_radians=math.pi / 6.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 11.0,
        )

        forward = retarder(
            field,
            retardance_cycles=0.37,
            **shared_orientation,
        )
        round_trip = retarder(
            forward,
            retardance_cycles=-0.37,
            **shared_orientation,
        )

        assert torch.allclose(
            round_trip.envelope,
            field.envelope,
            rtol=1.0e-12,
            atol=1.0e-12,
        )

    def test_same_eigenbasis_composition_adds_retardance(self) -> None:
        """
        同本征基下两次延迟复合等于一次延迟量为两者之和
        """
        grid = _grid()
        field = _transverse_field(
            _random_transverse_envelope(seed=7),
            grid=grid,
        )
        shared_orientation = dict(
            retarded_eigenstate_azimuth_radians=math.pi / 8.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 13.0,
        )

        first = retarder(
            field,
            retardance_cycles=0.19,
            **shared_orientation,
        )
        sequential = retarder(
            first,
            retardance_cycles=0.27,
            **shared_orientation,
        )
        combined = retarder(
            field,
            retardance_cycles=0.19 + 0.27,
            **shared_orientation,
        )

        assert torch.allclose(
            sequential.envelope,
            combined.envelope,
            rtol=1.0e-12,
            atol=1.0e-12,
        )

    def test_matrix_has_determinant_one(self) -> None:
        """
        延迟矩阵行列式为 1（由作用于基向量重构矩阵再求行列式）
        """
        grid = _grid()
        basis_x = _transverse_field(
            _constant_transverse_envelope((1.0, 0.0)),
            grid=grid,
        )
        basis_y = _transverse_field(
            _constant_transverse_envelope((0.0, 1.0)),
            grid=grid,
        )
        kwargs = dict(
            retardance_cycles=0.23,
            retarded_eigenstate_azimuth_radians=math.pi / 5.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 12.0,
        )
        column_x = retarder(basis_x, **kwargs).envelope[:, :, 0, 0]
        column_y = retarder(basis_y, **kwargs).envelope[:, :, 0, 0]
        reconstructed = torch.stack((column_x[0], column_y[0]), dim=1)
        determinant = torch.linalg.det(reconstructed)

        assert torch.allclose(
            determinant,
            torch.tensor(1.0, dtype=torch.complex128),
            rtol=1.0e-12,
            atol=1.0e-12,
        )

    def test_pointwise_complex_norm_preserved(self) -> None:
        """
        酉变换逐点保持横向二分量的复功率之和
        """
        grid = _grid()
        field = _transverse_field(
            _random_transverse_envelope(seed=11),
            grid=grid,
        )

        output = retarder(
            field,
            retardance_cycles=0.41,
            retarded_eigenstate_azimuth_radians=math.pi / 4.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 16.0,
        )

        input_power = field.envelope.abs().square().sum(dim=-3)
        output_power = output.envelope.abs().square().sum(dim=-3)
        assert torch.allclose(
            output_power,
            input_power,
            rtol=1.0e-12,
            atol=1.0e-12,
        )

    def test_retardance_is_not_reduced_modulo_one(self) -> None:
        """
        延迟量不做取模：整数周期差在零均值规范下使输出反号
        """
        grid = _grid()
        field = _transverse_field(
            _random_transverse_envelope(seed=3),
            grid=grid,
        )
        shared_orientation = dict(
            retarded_eigenstate_azimuth_radians=math.pi / 5.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 12.0,
        )

        base = retarder(
            field,
            retardance_cycles=0.23,
            **shared_orientation,
        )
        shifted = retarder(
            field,
            retardance_cycles=1.23,
            **shared_orientation,
        )

        assert torch.allclose(
            shifted.envelope,
            -base.envelope,
            rtol=1.0e-12,
            atol=1.0e-12,
        )

    def test_sign_continuity_under_parameter_sweep(self) -> None:
        """
        整式构造使延迟量扫描下输出连续（相邻步给出相邻输出）
        """
        grid = _grid()
        base_field = _transverse_field(
            _constant_transverse_envelope((1.0, 0.5j)),
            grid=grid,
        )
        retardance_values = torch.linspace(
            -0.6,
            1.6,
            steps=25,
            dtype=torch.float64,
        )
        step = float(retardance_values[1] - retardance_values[0])
        shared_orientation = dict(
            retarded_eigenstate_azimuth_radians=math.pi / 5.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 12.0,
        )
        previous = retarder(
            base_field,
            retardance_cycles=float(retardance_values[0]),
            **shared_orientation,
        ).envelope
        max_jump = torch.tensor(0.0, dtype=torch.float64)
        for value in retardance_values[1:]:
            current = retarder(
                base_field,
                retardance_cycles=float(value),
                **shared_orientation,
            ).envelope
            jump = (current - previous).abs().max()
            max_jump = torch.maximum(max_jump, jump)
            previous = current
        assert float(max_jump) < 10.0 * step

    @pytest.mark.parametrize("ellipticity_sign", (1.0, -1.0))
    def test_redundant_azimuth_has_no_effect_at_circular_poles(
        self,
        ellipticity_sign: float,
    ) -> None:
        """
        圆偏振极点处冗余方位角无任何可观测效应（逐位相等，且极点处有限）
        """
        grid = _grid()
        field = _transverse_field(
            _random_transverse_envelope(seed=5),
            grid=grid,
        )
        pole_ellipticity = ellipticity_sign * math.pi / 4.0
        azimuths = (
            0.0,
            math.pi / 6.0,
            math.pi / 4.0,
            math.pi / 2.0,
            math.pi,
        )

        outputs = [
            retarder(
                field,
                retardance_cycles=0.29,
                retarded_eigenstate_azimuth_radians=azimuth,
                retarded_eigenstate_ellipticity_radians=pole_ellipticity,
            ).envelope
            for azimuth in azimuths
        ]
        for output in outputs:
            assert torch.isfinite(output).all()
        reference = outputs[0]
        for output in outputs[1:]:
            assert torch.allclose(
                output,
                reference,
                rtol=1.0e-14,
                atol=1.0e-14,
            )


class TestIndependentReference:
    """
    证据层 2：独立 Jones/Stokes 参照
    """

    def test_linear_eigenstate_at_x_matches_diagonal_phasor_reference(self) -> None:
        """
        方位角与椭率均为零时矩阵须为对角相位参照
        """
        grid = _grid()
        retardance = 0.23
        field = _transverse_field(
            _random_transverse_envelope(seed=1),
            grid=grid,
        )

        output = retarder(
            field,
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        reference_matrix = _diagonal_phasor_matrix(retardance)
        reference_envelope = _apply_matrix_to_envelope(
            reference_matrix,
            field.envelope,
        )

        assert torch.allclose(
            output.envelope,
            reference_envelope,
            rtol=1.0e-12,
            atol=1.0e-12,
        )

    def test_linear_eigenstate_at_authorized_azimuth_matches_rotation_reference(
        self,
    ) -> None:
        """
        授权方位角下的线本征态须与旋转对角旋转共轭参照一致
        """
        grid = _grid()
        retardance = 0.31
        azimuth = math.pi / 5.0
        field = _transverse_field(
            _random_transverse_envelope(seed=2),
            grid=grid,
        )

        output = retarder(
            field,
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        reference_matrix = _independent_linear_eigenstate_retarder_matrix(
            retardance,
            azimuth,
        )
        reference_envelope = _apply_matrix_to_envelope(
            reference_matrix,
            field.envelope,
        )

        assert torch.allclose(
            output.envelope,
            reference_envelope,
            rtol=1.0e-12,
            atol=1.0e-12,
        )

    def test_right_circular_eigenstate_is_eigenstate_of_retarder(self) -> None:
        """
        右圆本征态输入得其正相位本征值，左圆正交输入得负相位本征值
        """
        grid = _grid()
        retardance = 0.27
        inverse_sqrt_two = 1.0 / math.sqrt(2.0)
        right_circular_x = complex(inverse_sqrt_two, 0.0)
        right_circular_y = complex(0.0, inverse_sqrt_two)
        left_circular_x = complex(inverse_sqrt_two, 0.0)
        left_circular_y = complex(0.0, -inverse_sqrt_two)
        right_field = _transverse_field(
            _constant_transverse_envelope((right_circular_x, right_circular_y)),
            grid=grid,
        )
        left_field = _transverse_field(
            _constant_transverse_envelope((left_circular_x, left_circular_y)),
            grid=grid,
        )
        retarded_phasor = torch.polar(
            torch.tensor(1.0, dtype=torch.float64),
            torch.tensor(math.pi * retardance, dtype=torch.float64),
        )
        orthogonal_phasor = torch.polar(
            torch.tensor(1.0, dtype=torch.float64),
            torch.tensor(-math.pi * retardance, dtype=torch.float64),
        )

        right_output = retarder(
            right_field,
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 4.0,
        )
        left_output = retarder(
            left_field,
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 4.0,
        )

        right_ratio = right_output.envelope[:, 0, 0, 0] / right_circular_x
        left_ratio = left_output.envelope[:, 0, 0, 0] / left_circular_x
        assert torch.allclose(
            right_ratio,
            retarded_phasor,
            rtol=1.0e-12,
            atol=1.0e-12,
        )
        assert torch.allclose(
            left_ratio,
            orthogonal_phasor,
            rtol=1.0e-12,
            atol=1.0e-12,
        )

    def test_quarter_wave_parameterization_recovers_right_circular(self) -> None:
        """
        四分之一波参数化把 x 线偏振变为右圆，且移除旧公共相位
        """
        grid = _grid()
        field = _transverse_field(
            _constant_transverse_envelope((1.0, 0.0)),
            grid=grid,
        )

        output = retarder(
            field,
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=math.pi / 4.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        conventional_matrix = _conventional_quarter_wave_plate_matrix(math.pi / 4.0)
        conventional_output_envelope = _apply_matrix_to_envelope(
            conventional_matrix,
            field.envelope,
        )
        common_phase_to_remove = torch.polar(
            torch.tensor(1.0, dtype=torch.float64),
            torch.tensor(-math.pi / 4.0, dtype=torch.float64),
        )
        expected_envelope = conventional_output_envelope * common_phase_to_remove

        assert torch.allclose(
            output.envelope,
            expected_envelope,
            rtol=1.0e-12,
            atol=1.0e-12,
        )
        inverse_sqrt_two = 1.0 / math.sqrt(2.0)
        right_circular_x = complex(inverse_sqrt_two, 0.0)
        right_circular_y = complex(0.0, inverse_sqrt_two)
        assert torch.allclose(
            output.envelope[:, 0],
            torch.full_like(
                output.envelope[:, 0],
                right_circular_x,
            ),
            rtol=1.0e-12,
            atol=1.0e-12,
        )
        assert torch.allclose(
            output.envelope[:, 1],
            torch.full_like(
                output.envelope[:, 1],
                right_circular_y,
            ),
            rtol=1.0e-12,
            atol=1.0e-12,
        )

    def test_half_wave_parameterization_flips_linear_polarization(self) -> None:
        """
        半波参数化把 x 线偏振翻转至 y 线偏振（公共相位除外）
        """
        grid = _grid()
        retardance = 0.5
        azimuth = math.pi / 4.0
        field = _transverse_field(
            _constant_transverse_envelope((1.0, 0.0)),
            grid=grid,
        )

        output = retarder(
            field,
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        reference_matrix = _independent_linear_eigenstate_retarder_matrix(
            retardance,
            azimuth,
        )
        reference_envelope = _apply_matrix_to_envelope(
            reference_matrix,
            field.envelope,
        )
        assert torch.allclose(
            output.envelope,
            reference_envelope,
            rtol=1.0e-12,
            atol=1.0e-12,
        )
        assert torch.allclose(
            output.envelope[:, 0].abs(),
            torch.zeros_like(output.envelope[:, 0].abs()),
            rtol=1.0e-12,
            atol=1.0e-12,
        )


class TestGradientEvidence:
    """
    证据层 3：autograd gradcheck 与独立有限差分
    """

    def test_gradcheck_on_three_trainable_parameters(self) -> None:
        """
        对延迟量、方位角、椭率角三个可训练参数做 gradcheck
        """
        grid = _grid()
        field = _transverse_field(
            _constant_transverse_envelope((0.6 + 0.4j, 0.2 - 0.3j)),
            grid=grid,
        )
        retardance = torch.nn.Parameter(
            torch.tensor(0.23, dtype=torch.float64),
        )
        azimuth = torch.nn.Parameter(
            torch.tensor(math.pi / 5.0, dtype=torch.float64),
        )
        ellipticity = torch.nn.Parameter(
            torch.tensor(math.pi / 12.0, dtype=torch.float64),
        )
        component = Retarder(
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )

        def run(
            retardance_value: torch.Tensor,
            azimuth_value: torch.Tensor,
            ellipticity_value: torch.Tensor,
        ) -> torch.Tensor:
            """
            返回当前三参数下的输出包络实部和
            """

            return component(field).envelope.real.sum()

        assert torch.autograd.gradcheck(
            run,
            (retardance, azimuth, ellipticity),
            eps=1.0e-8,
            raise_exception=True,
        )

    @pytest.mark.parametrize(
        ("short_name", "attribute_name"),
        (
            ("retardance", "retardance_cycles"),
            ("azimuth", "retarded_eigenstate_azimuth_radians"),
            ("ellipticity", "retarded_eigenstate_ellipticity_radians"),
        ),
    )
    def test_finite_difference_matches_autograd(
        self,
        short_name: str,
        attribute_name: str,
    ) -> None:
        """
        独立中心有限差分与 autograd 一致（函数路径独立于组件路径）
        """
        del short_name
        grid = _grid()
        field = _transverse_field(
            _constant_transverse_envelope((0.7 + 0.2j, -0.1 + 0.5j)),
            grid=grid,
        )
        retardance = torch.nn.Parameter(
            torch.tensor(0.23, dtype=torch.float64),
        )
        azimuth = torch.nn.Parameter(
            torch.tensor(math.pi / 5.0, dtype=torch.float64),
        )
        ellipticity = torch.nn.Parameter(
            torch.tensor(math.pi / 12.0, dtype=torch.float64),
        )
        component = Retarder(
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )

        objective = component(field).envelope.real.sum()
        gradient = torch.autograd.grad(
            objective,
            getattr(component, attribute_name),
        )[0]
        step = 1.0e-6
        parameter_values = {
            "retardance_cycles": float(retardance.detach()),
            "retarded_eigenstate_azimuth_radians": float(azimuth.detach()),
            "retarded_eigenstate_ellipticity_radians": float(
                ellipticity.detach()
            ),
        }
        positive_values = dict(parameter_values)
        negative_values = dict(parameter_values)
        positive_values[attribute_name] += step
        negative_values[attribute_name] -= step
        positive_output = retarder(
            field,
            retardance_cycles=positive_values["retardance_cycles"],
            retarded_eigenstate_azimuth_radians=(
                positive_values["retarded_eigenstate_azimuth_radians"]
            ),
            retarded_eigenstate_ellipticity_radians=(
                positive_values["retarded_eigenstate_ellipticity_radians"]
            ),
        ).envelope.real.sum()
        negative_output = retarder(
            field,
            retardance_cycles=negative_values["retardance_cycles"],
            retarded_eigenstate_azimuth_radians=(
                negative_values["retarded_eigenstate_azimuth_radians"]
            ),
            retarded_eigenstate_ellipticity_radians=(
                negative_values["retarded_eigenstate_ellipticity_radians"]
            ),
        ).envelope.real.sum()
        finite_difference = (
            (positive_output - negative_output) / (2.0 * step)
        )

        assert torch.allclose(
            gradient,
            finite_difference,
            rtol=1.0e-7,
            atol=1.0e-7,
        )

    def test_user_parameters_retain_identity(self) -> None:
        """
        用户 Parameter 经注册保持同一对象身份
        """
        retardance = torch.nn.Parameter(
            torch.tensor(0.23, dtype=torch.float64),
        )
        azimuth = torch.nn.Parameter(
            torch.tensor(math.pi / 5.0, dtype=torch.float64),
        )
        ellipticity = torch.nn.Parameter(
            torch.tensor(math.pi / 12.0, dtype=torch.float64),
        )
        component = Retarder(
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )

        assert component.retardance_cycles is retardance
        assert component.retarded_eigenstate_azimuth_radians is azimuth
        assert (
            component.retarded_eigenstate_ellipticity_radians is ellipticity
        )


class TestRetarderApplicability:
    """
    偏振适用性与稳定错误身份
    """

    @pytest.mark.parametrize(
        ("parameter_name", "identity"),
        (
            ("retardance_cycles", "retarder_retardance_cycles_invalid"),
            (
                "retarded_eigenstate_azimuth_radians",
                "retarder_retarded_eigenstate_azimuth_radians_invalid",
            ),
            (
                "retarded_eigenstate_ellipticity_radians",
                "retarder_retarded_eigenstate_ellipticity_radians_invalid",
            ),
        ),
    )
    def test_float32_parameter_rejected_with_owner_identity(
        self,
        parameter_name: str,
        identity: str,
    ) -> None:
        """
        每个公开标量参数都在 Retarder 边界拒绝 float32
        """

        arguments: dict[str, object] = {
            "retardance_cycles": 0.25,
            "retarded_eigenstate_azimuth_radians": 0.0,
            "retarded_eigenstate_ellipticity_radians": 0.0,
        }
        arguments[parameter_name] = torch.nn.Parameter(
            torch.tensor(0.25, dtype=torch.float32),
        )
        with pytest.raises(OpticalValueError) as information:
            Retarder(**arguments)  # type: ignore[arg-type]
        assert information.value.identity == identity

    @pytest.mark.parametrize(
        ("polarization", "expected_count"),
        (
            (Polarization.scalar(), 1),
            (Polarization.full(components=(1.0, 0.0, 0.0)), 3),
        ),
    )
    def test_nontransverse_fields_rejected_with_stable_identity(
        self,
        polarization: Polarization,
        expected_count: int,
    ) -> None:
        """
        标量与完整三分量表示以同一稳定身份被拒
        """
        grid = _grid()
        field = PlaneWave(
            spectrum=_spectrum(),
            polarization=polarization,
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )(grid)
        assert field.envelope.shape[-3] == expected_count

        with pytest.raises(OpticalValueError) as information:
            retarder(
                field,
                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )

        assert (
            information.value.identity
            == "retarder_polarization_representation_invalid"
        )

    @pytest.mark.parametrize(
        ("retardance", "azimuth", "ellipticity", "identity"),
        (
            (
                float("nan"),
                0.0,
                0.0,
                "retarder_retardance_cycles_invalid",
            ),
            (
                0.25,
                float("nan"),
                0.0,
                "retarder_retarded_eigenstate_azimuth_radians_invalid",
            ),
            (
                0.25,
                0.0,
                float("nan"),
                "retarder_retarded_eigenstate_ellipticity_radians_invalid",
            ),
            (
                0.25,
                0.0,
                math.pi / 3.0,
                "retarder_retarded_eigenstate_ellipticity_radians_invalid",
            ),
            (
                0.25,
                0.0,
                -math.pi / 3.0,
                "retarder_retarded_eigenstate_ellipticity_radians_invalid",
            ),
        ),
    )
    def test_invalid_parameters_rejected_with_stable_identity(
        self,
        retardance: float,
        azimuth: float,
        ellipticity: float,
        identity: str,
    ) -> None:
        """
        非法延迟量或本征态取向以对应稳定身份被拒
        """
        with pytest.raises(OpticalValueError) as information:
            Retarder(
                retardance_cycles=retardance,
                retarded_eigenstate_azimuth_radians=azimuth,
                retarded_eigenstate_ellipticity_radians=ellipticity,
            )

        assert information.value.identity == identity

    def test_non_optical_field_rejected(self) -> None:
        """
        非光场输入以稳定身份被拒
        """
        with pytest.raises(OpticalTypeError) as information:
            retarder(
                object(),  # type: ignore[arg-type]
                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )

        assert information.value.identity == "retarder_field_invalid"

    @pytest.mark.parametrize(
        "attribute_and_identity",
        (
            ("retardance_cycles", "retarder_retardance_cycles_invalid"),
            (
                "retarded_eigenstate_azimuth_radians",
                "retarder_retarded_eigenstate_azimuth_radians_invalid",
            ),
            (
                "retarded_eigenstate_ellipticity_radians",
                "retarder_retarded_eigenstate_ellipticity_radians_invalid",
            ),
        ),
    )
    def test_revalidation_rejects_in_place_mutation(
        self,
        attribute_and_identity: tuple[str, str],
    ) -> None:
        """
        原位破坏为非有限值后重新校验以对应稳定身份拒绝
        """
        attribute, identity = attribute_and_identity
        component = Retarder(
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=math.pi / 5.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 12.0,
        )
        getattr(component, attribute).fill_(float("nan"))

        with pytest.raises(OpticalValueError) as information:
            component._validate_physical_state()

        assert information.value.identity == identity

    def test_out_of_range_ellipticity_mutation_rejected(self) -> None:
        """
        椭率角越出正则区间后重新校验以稳定身份拒绝
        """
        component = Retarder(
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        component.retarded_eigenstate_ellipticity_radians.fill_(
            math.pi / 3.0,
        )

        with pytest.raises(OpticalValueError) as information:
            component._validate_physical_state()

        assert (
            information.value.identity
            == "retarder_retarded_eigenstate_ellipticity_radians_invalid"
        )


class TestRetarderLifecycle:
    """
    元推理、状态安装、托管与序列化保持普通组件生命周期
    """

    def test_meta_inference_preserves_shape_dtype_and_transverse(self) -> None:
        """
        meta 推导保持形状、精度与横向表示
        """
        grid = _grid()
        real_field = _transverse_field(
            _constant_transverse_envelope((1.0, 0.0)),
            grid=grid,
        )
        meta_field = OpticalField(
            envelope=torch.empty_like(
                real_field.envelope,
                device="meta",
            ),
            grid=real_field.grid.to(
                device="meta",
                dtype=real_field.envelope.real.dtype,
            ),
            spectrum=real_field.spectrum,
            polarization_representation=real_field.polarization_representation,
            medium=real_field.medium,
            normalization=real_field.normalization,
            path_reference=real_field.path_reference,
        )
        component = Retarder(
            retardance_cycles=0.37,
            retarded_eigenstate_azimuth_radians=math.pi / 6.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 14.0,
        )
        isolated = copy.deepcopy(component)
        isolated.to_empty(device="meta")

        output = isolated(meta_field)

        assert output.envelope.device.type == "meta"
        assert output.envelope.shape == real_field.envelope.shape
        assert output.envelope.dtype is real_field.envelope.dtype
        assert (
            output.polarization_representation
            is PolarizationRepresentation.TRANSVERSE
        )

    def test_state_dict_round_trip_restores_parameters(self) -> None:
        """
        加载状态字典后三个物理标量恢复为源值
        """
        source = Retarder(
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.pi / 5.0,
            retarded_eigenstate_ellipticity_radians=math.pi / 11.0,
        )
        target = Retarder(
            retardance_cycles=0.0,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )

        target.load_state_dict(source.state_dict())

        assert torch.allclose(
            target.retardance_cycles,
            source.retardance_cycles,
        )
        assert torch.allclose(
            target.retarded_eigenstate_azimuth_radians,
            source.retarded_eigenstate_azimuth_radians,
        )
        assert torch.allclose(
            target.retarded_eigenstate_ellipticity_radians,
            source.retarded_eigenstate_ellipticity_radians,
        )

    def test_hosted_retarder_yields_finite_nonnegative_intensity(self) -> None:
        """
        托管 PlaneWave、延迟器、光强检测给出有限非负光强
        """
        grid = _grid()
        spectrum = _spectrum()
        workstation = Workstation.cpu()
        source = workstation.host(
            PlaneWave(
                spectrum=spectrum,
                polarization=Polarization.linear_x(),
                medium=Vacuum(),
                propagation_direction=PropagationDirection.forward(),
                relative_amplitude=1.0,
            )
        )
        retarder_component = workstation.host(
            Retarder(
                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=math.pi / 4.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )
        )
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        delayed = retarder_component(field)
        intensity = detection(delayed)

        assert torch.isfinite(intensity.values).all()
        assert bool((intensity.values >= 0.0).all())
        assert torch.allclose(
            intensity.values,
            torch.ones_like(intensity.values),
            rtol=1.0e-9,
            atol=1.0e-9,
        )


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_retarder_public_action_matches_cpu_on_cuda() -> None:
    """
    Retarder 公共动作在 CUDA 上保持与 CPU 相同的横向复包络
    """

    cpu_envelope = _constant_transverse_envelope((1.0 + 0.0j, 0.0 + 0.0j))
    cpu_field = _transverse_field(cpu_envelope)
    cuda_field = _transverse_field(cpu_envelope.cuda())
    parameters = {
        "retardance_cycles": 0.25,
        "retarded_eigenstate_azimuth_radians": 0.37,
        "retarded_eigenstate_ellipticity_radians": -0.11,
    }

    cpu_output = retarder(cpu_field, **parameters)
    cuda_output = retarder(cuda_field, **parameters)

    torch.testing.assert_close(cpu_output.envelope, cuda_output.envelope.cpu())


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_cuda_retardance_parameter_keeps_identity_and_gradient() -> None:
    """
    CUDA retardance Parameter 保持注册身份并接收有限非零梯度
    """

    retardance = torch.nn.Parameter(
        torch.tensor(0.21, dtype=torch.float64, device="cuda"),
    )
    component = Retarder(
        retardance_cycles=retardance,
        retarded_eigenstate_azimuth_radians=0.37,
        retarded_eigenstate_ellipticity_radians=-0.11,
    ).cuda()
    field = _transverse_field(
        _constant_transverse_envelope(
            (1.0 + 0.2j, 0.3 - 0.4j),
        ).cuda(),
    )

    output = component(field)
    observation = output.envelope.real.sum() + 0.37 * output.envelope.imag.sum()
    gradient = torch.autograd.grad(observation, retardance)[0]

    assert component.retardance_cycles is retardance
    assert (
        dict(component.named_parameters())["retardance_cycles"]
        is retardance
    )
    assert torch.isfinite(gradient)
    assert not torch.equal(gradient, torch.zeros_like(gradient))


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_cuda_retarder_rejects_float32_tensor() -> None:
    """
    CUDA Retarder 在自己的边界拒绝单精度张量
    """

    with pytest.raises(
        ValueError,
        match="retarder_retardance_cycles_invalid",
    ):
        Retarder(
            retardance_cycles=torch.tensor(
                0.25,
                dtype=torch.float32,
                device="cuda",
            ),
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )

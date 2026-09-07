
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
    SellmeierMedium,
    SpatialGrid,
    Spectrum,
    TabulatedMedium,
    Vacuum,
)
from chromatix_next.optics._meta_inference import _meta_inference
from chromatix_next.optics.combination import CoherentCombination
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.grid import PropagationExterior
from chromatix_next.optics.propagation import scalar_angular_spectrum
from chromatix_next.optics.source import GaussianBeam
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


def _forward_on_meta(source: GaussianBeam, grid: SpatialGrid) -> OpticalField:
    # 在 meta 设备上执行光源自己的前向，只得到形状与数据类型
    missing = object()
    original_forward = source.__dict__.get("forward", missing)
    with _meta_inference((source,)) as sandbox:
        assert source.__dict__.get("forward", missing) is original_forward
        result = sandbox.module(source)(grid)
    assert source.__dict__.get("forward", missing) is original_forward
    return result


def _independent_waist_envelope(
    grid: SpatialGrid,
    wavelength: float,
    waist: float,
    real_dtype: torch.dtype,
) -> torch.Tensor:
    # waist 平面独立参照：envelope = exp(-r^2/w0^2)，实数路径
    counts_y, counts_x = grid.sample_counts
    spacing_y, spacing_x = grid.sample_spacing
    first_y, first_x = grid.first_sample_position
    position_y = (
        torch.arange(counts_y, dtype=real_dtype) * float(spacing_y) + float(first_y)
    )
    position_x = (
        torch.arange(counts_x, dtype=real_dtype) * float(spacing_x) + float(first_x)
    )
    radius_squared = (
        position_y.reshape(-1, 1) ** 2 + position_x.reshape(1, -1) ** 2
    )
    return torch.exp(-radius_squared / (waist * waist))


@pytest.mark.cuda
@_cuda_unavailable
def test_gaussian_beam_public_source_matches_cpu_on_cuda() -> None:
    """
    GaussianBeam 公共源在 CUDA 上保持与 CPU 相同的复包络
    """

    cpu_source = GaussianBeam(
        spectrum=_monochromatic(),
        polarization=Polarization.scalar(),
        waist=2.0e-6,
        relative_amplitude=1.0,
    )
    cuda_source = GaussianBeam(
        spectrum=_monochromatic(),
        polarization=Polarization.scalar(),
        waist=2.0e-6,
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
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=2.0e-6,
            relative_amplitude=1.5,
        )
        field = source(_grid())
        assert isinstance(field, OpticalField)
        assert field.normalization is FieldNormalization.RELATIVE

    def test_total_power_yields_power_field(self) -> None:
        """
        仅提供总功率时输出光场归一化为 POWER
        """
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=2.0e-6,
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
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            waist=2.0e-6,
            waist_location=0.0,
            relative_amplitude=relative_amplitude,
        )
        envelope = source(
            _grid(counts=(2, 2), spacing=(1.0e-6, 1.0e-6)),
        ).envelope
        expected_envelope = torch.tensor(
            (
                complex(float.fromhex("0x1.842dfbb8b7b8cp-1"), 0.0),
                complex(float.fromhex("0x1.f26eb8657a28ep-1"), 0.0),
                complex(float.fromhex("0x1.f26eb8657a28ep-1"), 0.0),
                complex(float.fromhex("0x1.4000000000000p+0"), 0.0),
            ),
            dtype=torch.complex128,
        ).reshape(1, 1, 2, 2)

        assert torch.equal(envelope, expected_envelope)
        gradient = torch.autograd.grad(
            envelope.real.sum(),
            relative_amplitude,
        )[0]
        assert torch.equal(
            gradient,
            torch.tensor(
                float.fromhex("0x1.950248e722688p+1"),
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
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            waist=2.0e-6,
            waist_location=0.0,
            total_power=total_power,
        )
        envelope = source(
            _grid(counts=(2, 2), spacing=(1.0e-6, 1.0e-6)),
        ).envelope
        expected_envelope = torch.tensor(
            (
                complex(float.fromhex("0x1.70b12acd96bc9p+18"), 0.0),
                complex(float.fromhex("0x1.d968f421eaa8cp+18"), 0.0),
                complex(float.fromhex("0x1.d968f421eaa8cp+18"), 0.0),
                complex(float.fromhex("0x1.2fef6a9934a1bp+19"), 0.0),
            ),
            dtype=torch.complex128,
        ).reshape(1, 1, 2, 2)

        assert torch.equal(envelope, expected_envelope)
        gradient = torch.autograd.grad(envelope.real.sum(), total_power)[0]
        assert torch.equal(
            gradient,
            torch.tensor(
                float.fromhex("0x1.e0d87a10f5547p+19"),
                dtype=torch.float64,
            ),
        )

    def test_neither_normalization_rejected(self) -> None:
        """
        既不提供相对振幅也不提供总功率须以稳定身份拒绝
        """
        with pytest.raises(
            ValueError,
            match="gaussian_beam_normalization_missing",
        ):
            GaussianBeam(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                waist=2.0e-6,
            )

    def test_both_normalizations_rejected(self) -> None:
        """
        同时提供相对振幅与总功率须以稳定身份拒绝
        """
        with pytest.raises(
            ValueError,
            match="gaussian_beam_normalization_exclusive",
        ):
            GaussianBeam(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                waist=2.0e-6,
                relative_amplitude=1.0,
                total_power=1.0,
            )

    @pytest.mark.parametrize(
        ("parameter_name", "identity"),
        (
            ("relative_amplitude", "gaussian_beam_relative_amplitude_invalid"),
            ("total_power", "gaussian_beam_total_power_invalid"),
            ("waist", "gaussian_beam_waist_invalid"),
            ("waist_location", "gaussian_beam_waist_location_invalid"),
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
            "waist": 2.0e-6,
        }
        if parameter_name not in {"relative_amplitude", "total_power"}:
            base_arguments["relative_amplitude"] = 1.0
        for invalid_value in (
            torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float32)),
            torch.tensor(1.0, dtype=torch.float64),
        ):
            arguments = dict(base_arguments)
            arguments[parameter_name] = invalid_value
            with pytest.raises((TypeError, ValueError), match=identity):
                GaussianBeam(**arguments)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("parameter_name", "parameter_value"),
        (
            ("relative_amplitude", 1.0),
            ("total_power", 1.0e-3),
            ("waist", 2.0e-6),
            ("waist_location", 0.3e-6),
        ),
    )
    def test_scale_parameter_keeps_optimizer_identity(
        self,
        parameter_name: str,
        parameter_value: float,
    ) -> None:
        """
        每个合法尺度 Parameter 保持同一注册对象并对优化器可见
        """

        parameter = torch.nn.Parameter(
            torch.tensor(parameter_value, dtype=torch.float64),
        )
        arguments: dict[str, object] = {
            "spectrum": _monochromatic(),
            "polarization": Polarization.scalar(),
            "waist": 2.0e-6,
            parameter_name: parameter,
        }
        if parameter_name not in {"relative_amplitude", "total_power"}:
            arguments["relative_amplitude"] = 1.0
        source = GaussianBeam(**arguments)  # type: ignore[arg-type]

        assert getattr(source, parameter_name) is parameter
        assert dict(source.named_parameters())[parameter_name] is parameter

    @pytest.mark.parametrize(
        "invalid_waist",
        [0.0, -1.0e-6, float("nan"), float("inf")],
    )
    def test_waist_must_be_positive_finite(self, invalid_waist: float) -> None:
        """
        waist 须为正有限值；waist->0 使 Rayleigh range 退化为非物理
        """
        with pytest.raises(ValueError, match="gaussian_beam_waist_invalid"):
            GaussianBeam(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                waist=invalid_waist,
                relative_amplitude=1.0,
            )

    def test_positive_waist_with_nonpositive_rayleigh_range_rejected(self) -> None:
        """
        正有限束腰若在 binary64 中导出零 Rayleigh range 须以稳定身份拒绝
        """
        smallest_positive_waist = float.fromhex("0x0.0000000000001p-1022")
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            waist=smallest_positive_waist,
            relative_amplitude=1.0,
        )

        with pytest.raises(
            ValueError,
            match="gaussian_beam_rayleigh_range_invalid",
        ):
            source(_grid())

    def test_output_envelope_has_fixed_axes_and_complex_dtype(self) -> None:
        """
        输出包络遵循固定轴布局且为复数
        """
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=2.0e-6,
            relative_amplitude=1.5,
        )
        field = source(_grid())
        assert field.envelope.shape == (1, 1, 8, 8)
        assert torch.is_complex(field.envelope)
        assert field.batch_shape == ()
        assert field.envelope.device.type == "cpu"

    def test_zero_path_reference_at_source(self) -> None:
        """
        源的光程参考从零起算（与 PlaneWave 的 OPR 约定一致）
        """
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            waist=2.0e-6,
            relative_amplitude=1.0,
        )
        field = source(_grid())
        assert field.path_reference == OpticalPathReference(lengths=(0.0,))

    def test_user_parameter_identity_preserved(self) -> None:
        """
        用户 supplied Parameter 须保持身份注册，不被克隆
        """
        waist = torch.nn.Parameter(torch.tensor(2.0e-6, dtype=torch.float64))
        amplitude = torch.nn.Parameter(torch.tensor(1.5, dtype=torch.float64))
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            relative_amplitude=amplitude,
        )
        assert source.waist is waist
        assert source.relative_amplitude is amplitude
        assert waist in set(source.parameters())
        assert amplitude in set(source.parameters())

    def test_fixed_grid_reuses_registered_unit_envelope(self) -> None:
        """
        相同固定高斯光束与网格连续前向复用同一份单位包络缓存
        """
        grid = _grid()
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            waist=2.0e-6,
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
        source = GaussianBeam(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=2.0e-6,
            total_power=1.0e-3,
        )
        with pytest.raises(
            ValueError,
            match="gaussian_beam_total_power_spectrum_weight_sum_invalid",
        ):
            source(_grid())


class TestIndependentReference:
    """
    证据层 2：独立解析参照
    """

    def test_waist_plane_envelope_matches_independent_reference(self) -> None:
        """
        waist 平面（z=0）包络与独立 exp(-r^2/w0^2) 参照一致
        """
        waist = 2.0e-6
        grid = _grid()
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            relative_amplitude=1.0,
        )
        field = source(grid)
        reference = _independent_waist_envelope(grid, 0.5e-6, waist, torch.float64)
        assert torch.allclose(field.envelope[0, 0].real, reference, atol=1e-12)
        assert torch.allclose(
            field.envelope[0, 0].imag.abs(),
            torch.zeros_like(reference),
            atol=1e-12,
        )

    def test_beam_radius_at_rayleigh_range(self) -> None:
        """
        z=zR 处束腰展宽至 w0 sqrt(2)，中心振幅因子为 1/sqrt(2)
        """
        waist = 2.0e-6
        wavelength = 0.5e-6
        rayleigh_range = math.pi * waist * waist / wavelength
        source = GaussianBeam(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=rayleigh_range,
            relative_amplitude=1.0,
        )
        field = source(_grid())
        center_modulus = float(field.envelope[0, 0, 4, 4].abs())
        assert math.isclose(center_modulus, 1.0 / math.sqrt(2.0), rel_tol=1e-12)

    def test_gouy_phase_at_rayleigh_range(self) -> None:
        """
        z=zR 处 Gouy 相位取 -arctan(1) = -pi/4（exp(-i ω t) 约定下负 Gouy）
        """
        waist = 2.0e-6
        wavelength = 0.5e-6
        rayleigh_range = math.pi * waist * waist / wavelength
        source = GaussianBeam(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=rayleigh_range,
            relative_amplitude=1.0,
        )
        field = source(_grid())
        center_phase = float(field.envelope[0, 0, 4, 4].angle())
        assert math.isclose(center_phase, -math.pi / 4.0, abs_tol=1e-12)

    def test_curvature_phase_vanishes_at_waist(self) -> None:
        """
        waist 平面波前曲率为零，包络为实正数
        """
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=1.5e-6,
            relative_amplitude=1.0,
        )
        field = source(_grid())
        assert torch.all(field.envelope[0, 0].imag.abs() <= 1e-14)
        assert torch.all(field.envelope[0, 0].real > 0)

    def test_negative_waist_location_is_pre_waist_plane(self) -> None:
        """
        负 waist_location 遵循 exp(-i ω t) 约定的复共轭对称
        """
        waist = 2.0e-6
        wavelength = 0.5e-6
        rayleigh_range = math.pi * waist * waist / wavelength
        grid = _grid()
        positive_source = GaussianBeam(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=rayleigh_range,
            relative_amplitude=1.0,
        )
        negative_source = GaussianBeam(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=-rayleigh_range,
            relative_amplitude=1.0,
        )
        positive = positive_source(grid).envelope
        negative = negative_source(grid).envelope
        assert torch.allclose(negative, positive.conj(), atol=1e-14, rtol=1e-14)
        center_phase = float(negative[0, 0, 4, 4].angle())
        assert math.isclose(center_phase, math.pi / 4.0, abs_tol=1e-12)

    def test_non_vacuum_medium_uses_medium_wave_number(self) -> None:
        """
        非真空介质中 Rayleigh range 与波前曲率由介质波数 k=2 pi n/lambda 决定
        """
        waist = 2.0e-6
        wavelength = 0.5e-6
        index = 1.5
        glass_rayleigh = math.pi * waist * waist * index / wavelength
        source = GaussianBeam(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=ConstantMedium(index=index),
            waist=waist,
            waist_location=glass_rayleigh,
            relative_amplitude=1.0,
        )
        field = source(_grid())
        # 玻璃中 z=zR_glass：振幅因子 1/sqrt(2)，Gouy 相位 -pi/4（负 Gouy 约定）
        center_modulus = float(field.envelope[0, 0, 4, 4].abs())
        assert math.isclose(center_modulus, 1.0 / math.sqrt(2.0), rel_tol=1e-12)
        center_phase = float(field.envelope[0, 0, 4, 4].angle())
        assert math.isclose(center_phase, -math.pi / 4.0, abs_tol=1e-12)

    def test_multispectral_envelope_shape(self) -> None:
        """
        多光谱多分量偏振输出形状遵循 (光谱, 偏振, 高, 宽)
        """
        wavelengths = (0.45e-6, 0.55e-6, 0.65e-6)
        weights = (0.3, 0.4, 0.3)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        source = GaussianBeam(
            spectrum=spectrum,
            polarization=Polarization.linear_y(),
            medium=SellmeierMedium(
                b_coefficients=(1.03961212, 0.231792344, 1.01046945),
                c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.03560653e2),
                wavelength_min=0.3e-6,
                wavelength_max=2.5e-6,
            ),
            waist=2.5e-6,
            relative_amplitude=1.0,
        )
        field = source(_grid())
        assert field.envelope.shape == (3, 2, 8, 8)


class TestGradientEvidence:
    """
    证据层 3：梯度证据（连续 beam 参数经源->探测链路保持 autograd）
    """

    def test_gradcheck_on_trainable_relative_amplitude(self) -> None:
        """
        对可训练相对振幅经 GaussianBeam->IntensityDetection 链路做 gradcheck
        """
        amplitude = torch.nn.Parameter(torch.tensor(1.25, dtype=torch.float64))
        grid = _grid()
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=2.0e-6,
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
        对可训练总功率经 GaussianBeam->IntensityDetection 链路做 gradcheck
        """
        total_power = torch.nn.Parameter(torch.tensor(1.0e-3, dtype=torch.float64))
        grid = _grid()
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=2.0e-6,
            total_power=total_power,
        )
        detection = IntensityDetection()

        def run(total_power_value: torch.Tensor) -> torch.Tensor:
            """
            返回给定总功率下的光强空间总和
            """
            return detection(source(grid)).values.sum()

        assert torch.autograd.gradcheck(run, (total_power,), raise_exception=True)

    def test_gradcheck_on_trainable_waist(self) -> None:
        """
        对可训练束腰经 ``GaussianBeam``→``IntensityDetection`` 链路做梯度校验
        """
        waist = torch.nn.Parameter(torch.tensor(2.0e-6, dtype=torch.float64))
        grid = _grid()
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            relative_amplitude=1.0,
        )
        detection = IntensityDetection()

        def run(waist_value: torch.Tensor) -> torch.Tensor:
            """
            返回给定 waist 下的光强总和
            """
            return detection(source(grid)).values.sum()

        assert torch.autograd.gradcheck(
            run,
            (waist,),
            eps=1e-10,
            atol=1e-4,
            rtol=1e-3,
            raise_exception=True,
        )

    def test_gradcheck_on_trainable_waist_location(self) -> None:
        """
        对可训练束腰位置经 ``GaussianBeam``→``IntensityDetection`` 链路做梯度校验
        """
        waist_location = torch.nn.Parameter(
            torch.tensor(5.0e-6, dtype=torch.float64),
        )
        grid = _grid()
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=2.0e-6,
            waist_location=waist_location,
            relative_amplitude=1.0,
        )
        detection = IntensityDetection()

        def run(location_value: torch.Tensor) -> torch.Tensor:
            """
            返回给定 waist_location 下的光强总和
            """
            return detection(source(grid)).values.sum()

        assert torch.autograd.gradcheck(
            run,
            (waist_location,),
            eps=1e-10,
            atol=1e-4,
            rtol=1e-3,
            raise_exception=True,
        )

    def test_waist_gradient_matches_finite_difference(self) -> None:
        """
        可训练 waist 的解析梯度与中心有限差分一致
        """
        waist = torch.nn.Parameter(torch.tensor(2.0e-6, dtype=torch.float64))
        grid = _grid()
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=0.0,
            relative_amplitude=1.0,
        )
        detection = IntensityDetection()

        def observe(waist_value: float) -> float:
            """
            返回给定 waist 下的光强总和（有限差分采样点）
            """
            local_source = GaussianBeam(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                waist=waist_value,
                relative_amplitude=1.0,
            )
            return float(detection(local_source(grid)).values.sum())

        automatic_gradient = torch.autograd.grad(
            detection(source(grid)).values.sum(),
            waist,
        )[0]
        step = 1.0e-12
        origin = float(waist.detach())
        finite_difference = (
            observe(origin + step) - observe(origin - step)
        ) / (2.0 * step)
        assert float(automatic_gradient) == pytest.approx(
            finite_difference,
            rel=1.0e-6,
        )


class TestConstructionMatchesPropagation:
    """
    证据层 2 补充：直接构造与 waist 正向传播在复域一致（exp(-i ω t) 相位语言）
    """

    def _paraxial_grid(self) -> SpatialGrid:
        return SpatialGrid.centered(
            sample_counts=(192, 192),
            sample_spacing=(0.15e-6, 0.15e-6),
        )

    def _construct(
        self,
        grid: SpatialGrid,
        waist: float,
        waist_location: float,
    ) -> OpticalField:
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=waist_location,
            relative_amplitude=1.0,
        )
        return source(grid)

    def _propagate_waist(
        self,
        grid: SpatialGrid,
        waist: float,
        distance: float,
    ) -> OpticalField:
        waist_source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=0.0,
            relative_amplitude=1.0,
        )
        return scalar_angular_spectrum(
            waist_source(grid),
            axial_distance=distance,
        )

    @pytest.mark.parametrize("distance_factor", [0.1, 0.25, 0.5, 0.75])
    def test_construct_envelope_matches_waist_propagation_complex(
        self,
        distance_factor: float,
    ) -> None:
        """
        在 axial distance 构造的 beam 与 waist 传播到该 plane 在复域一致
        """

        waist = 4.0e-6
        wavelength = 0.5e-6
        rayleigh_range = math.pi * waist * waist / wavelength
        distance = distance_factor * rayleigh_range
        grid = self._paraxial_grid()
        constructed = self._construct(grid, waist, waist_location=distance)
        propagated = self._propagate_waist(grid, waist, distance=distance)
        max_abs = constructed.envelope.abs().max().item()
        diff = (constructed.envelope - propagated.envelope).abs().max().item()
        # 容差由角谱周期外部的尾卷绕主导（强度已达同等量级），不是相位符号残差
        assert diff / max_abs < 5.0e-4

    def test_construct_envelope_matches_waist_propagation_at_rayleigh(self) -> None:
        """
        d=zR 处构造与传播的复域一致（更高分辨率网格压低尾卷绕）
        """

        waist = 4.0e-6
        wavelength = 0.5e-6
        rayleigh_range = math.pi * waist * waist / wavelength
        grid = SpatialGrid.centered(
            sample_counts=(256, 256),
            sample_spacing=(0.12e-6, 0.12e-6),
        )
        constructed = self._construct(
            grid,
            waist,
            waist_location=rayleigh_range,
        )
        propagated = self._propagate_waist(
            grid,
            waist,
            distance=rayleigh_range,
        )
        max_abs = constructed.envelope.abs().max().item()
        diff = (constructed.envelope - propagated.envelope).abs().max().item()
        assert diff / max_abs < 1.0e-3


class TestIndependentAnalyticReferences:
    """
    证据层 2 补充：独立的轴向、波前曲率、束腰半径、Gouy 相位与总功率解析参照
    """

    def test_axial_amplitude_factor_follows_waist_ratio(self) -> None:
        """
        轴向中心振幅等于 w0/w(z)（独立束腰半径比）
        """

        waist = 2.0e-6
        wavelength = 0.5e-6
        rayleigh_range = math.pi * waist * waist / wavelength
        # 选取三个轴向距离直接对照独立解析 w0/w(z)
        for factor in (0.3, 0.7, 1.5):
            distance = factor * rayleigh_range
            beam_radius = waist * math.sqrt(1.0 + (distance / rayleigh_range) ** 2)
            expected = waist / beam_radius
            source = GaussianBeam(
                spectrum=_monochromatic(wavelength=wavelength),
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                waist=waist,
                waist_location=distance,
                relative_amplitude=1.0,
            )
            field = source(_grid())
            center_modulus = float(field.envelope[0, 0, 4, 4].abs())
            assert math.isclose(center_modulus, expected, rel_tol=1e-12)

    def test_curvature_phase_matches_independent_wavefront_radius(self) -> None:
        """
        偏轴像素的复相位与独立 1/R(z) 二次相位 + Gouy 一致（正曲率、负 Gouy）
        """

        waist = 2.5e-6
        wavelength = 0.5e-6
        rayleigh_range = math.pi * waist * waist / wavelength
        k = 2.0 * math.pi / wavelength
        distance = 0.5 * rayleigh_range
        grid = _grid()
        source = GaussianBeam(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=distance,
            relative_amplitude=1.0,
        )
        field = source(grid)
        # 独立参照：振幅因子乘横向衰减，再合成正曲率相位与负 Gouy 相位
        spacing_y, spacing_x = grid.sample_spacing
        first_y, first_x = grid.first_sample_position
        position_y = (
            torch.arange(8, dtype=torch.float64) * float(spacing_y) + float(first_y)
        )
        position_x = (
            torch.arange(8, dtype=torch.float64) * float(spacing_x) + float(first_x)
        )
        radius_squared = position_y.reshape(-1, 1) ** 2 + position_x.reshape(1, -1) ** 2
        beam_radius = waist * math.sqrt(1.0 + (distance / rayleigh_range) ** 2)
        inverse_two_R = distance / (2.0 * (distance * distance + rayleigh_range**2))
        gouy = math.atan(distance / rayleigh_range)
        amplitude = waist / beam_radius
        transverse = torch.exp(-radius_squared / (beam_radius**2))
        phase = k * radius_squared * inverse_two_R - gouy
        reference = amplitude * transverse * torch.complex(
            torch.cos(phase),
            torch.sin(phase),
        )
        assert torch.allclose(
            field.envelope[0, 0],
            reference,
            atol=1e-12,
            rtol=1e-12,
        )

    def test_total_power_amplitude_matches_independent_integral(self) -> None:
        """
        POWER 归一化振幅与独立 |A|^2 sum = total_power/cell_area 解析一致
        """

        waist = 2.0e-6
        total_power = 1.0e-3
        grid = _grid(counts=(16, 16), spacing=(0.1e-6, 0.1e-6))
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=0.0,
            total_power=total_power,
        )
        field = source(grid)
        intensity_sum = float(field.envelope.abs().square().sum().item())
        cell_area = float(grid.cell_area)
        assert math.isclose(
            intensity_sum * cell_area,
            total_power,
            rel_tol=1e-6,
        )


class TestHostedExecution:
    """
    托管端到端：POWER 归一化与 Workstation replay
    """

    def test_hosted_power_source_total_power_integral(self) -> None:
        """
        托管 POWER 高斯光束：Intensity 空间积分 x 单元面积 = 总功率
        """
        total_power = 2.5e-3
        grid = _grid(counts=(32, 32), spacing=(0.1e-6, 0.1e-6))
        workstation = Workstation.cpu()
        source = workstation.host(
            GaussianBeam(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                waist=2.0e-6,
                waist_location=0.0,
                total_power=total_power,
            ),
        )
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        assert field.normalization is FieldNormalization.POWER
        intensity = detection(field)
        integral = float(intensity.values.sum().item()) * grid.cell_area
        assert math.isclose(integral, total_power, rel_tol=1e-6)

    def test_frozen_assembly_preserves_beam_and_total_power(self) -> None:
        """
        冻结装配托管运行保留偏振与声明总功率
        """
        grid = _grid(counts=(32, 32), spacing=(0.1e-6, 0.1e-6))
        total_power = 1.5e-3
        source = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.right_circular(),
            medium=ConstantMedium(index=1.3),
            waist=2.0e-6,
            waist_location=0.0,
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
        source = GaussianBeam(
            spectrum=spectrum,
            polarization=polarization,
            medium=Vacuum(),
            waist=2.0e-6,
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
        original = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            waist=2.0e-6,
            relative_amplitude=1.0,
        )
        restored = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            waist=2.0e-6,
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
    高斯光束固定物理状态的 PyTorch 序列化契约
    """

    def test_state_round_trip_preserves_named_physical_metadata(self) -> None:
        """
        命名载荷逐位恢复光谱与偏振，且单位包络缓存失效
        """
        grid = _grid()
        original = GaussianBeam(
            spectrum=Spectrum(
                wavelengths=(0.48e-6, 0.63e-6),
                weights=(0.4, 0.6),
            ),
            polarization=Polarization.linear_y(),
            medium=ConstantMedium(index=1.4),
            waist=2.0e-6,
            waist_location=1.0e-6,
            relative_amplitude=1.0,
        )
        restored = GaussianBeam(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=ConstantMedium(index=1.4),
            waist=3.0e-6,
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


def test_gaussian_beam_richer_model_residual_decreases_with_divergence() -> None:
    """
    近似模型证据：增大 ``k * waist`` 时，高斯源趋近标量 Helmholtz 参照
    固定采样、窗口比例和归一化轴向距离；参照由孤立标量角谱传播给出。
    """

    waist = 4.0e-6
    grid = SpatialGrid.centered(
        sample_counts=(96, 96),
        sample_spacing=(0.25e-6, 0.25e-6),
    )
    residuals: list[float] = []
    for wavelength in (1.0e-6, 0.5e-6, 0.25e-6):
        rayleigh_range = math.pi * waist * waist / wavelength
        distance = 0.5 * rayleigh_range
        waist_source = GaussianBeam(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=0.0,
            relative_amplitude=1.0,
        )
        propagated = scalar_angular_spectrum(
            waist_source(grid),
            axial_distance=distance,
            exterior=PropagationExterior.ISOLATED,
        )
        paraxial = GaussianBeam(
            spectrum=_monochromatic(wavelength=wavelength),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=distance,
            relative_amplitude=1.0,
        )(grid)
        actual = propagated.envelope
        expected = paraxial.envelope
        alignment = (actual.conj() * expected).sum() / actual.abs().square().sum()
        residuals.append(
            float((alignment * actual - expected).abs().max())
            / float(expected.abs().max())
        )

    assert residuals[1] < residuals[0]
    assert residuals[2] < residuals[1]

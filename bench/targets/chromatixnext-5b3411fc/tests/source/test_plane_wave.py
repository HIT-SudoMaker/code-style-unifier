
from __future__ import annotations

import inspect
import math

import pytest
import torch

from chromatix_next import install_state
from chromatix_next.errors import AssemblyError, OpticalRuntimeError
from chromatix_next.optics import (
    Assembly,
    ConstantMedium,
    FieldNormalization,
    Intensity,
    OpticalField,
    Polarization,
    PolarizationRepresentation,
    PropagationDirection,
    SellmeierMedium,
    SpatialGrid,
    Spectrum,
    TabulatedMedium,
    TransverseWavevector,
    Vacuum,
)
from chromatix_next.optics._meta_inference import _meta_inference
from chromatix_next.optics.combination import CoherentCombination
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


def _grid(
    counts: tuple[int, int] = (8, 8),
    spacing: tuple[float, float] = (0.5e-6, 0.5e-6),
) -> SpatialGrid:
    # 构造中心对齐的横向网格
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )


def _forward_on_meta(source: PlaneWave, grid: SpatialGrid) -> OpticalField:
    # 在 meta 设备上执行光源自己的前向，只得到形状与数据类型
    missing = object()
    original_forward = source.__dict__.get("forward", missing)
    with _meta_inference((source,)) as sandbox:
        assert source.__dict__.get("forward", missing) is original_forward
        result = sandbox.module(source)(grid)
    assert source.__dict__.get("forward", missing) is original_forward
    return result


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    # 构造单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _independent_phasor_from_direction(
    grid: SpatialGrid,
    spectrum: Spectrum,
    medium: Vacuum | ConstantMedium,
    direction: PropagationDirection,
    real_dtype: torch.dtype,
) -> torch.Tensor:
    counts_y, counts_x = grid.sample_counts
    spacing_y, spacing_x = grid.sample_spacing
    first_y, first_x = grid.first_sample_position
    position_y = (
        torch.arange(counts_y, dtype=real_dtype) * float(spacing_y) + float(first_y)
    )
    position_x = (
        torch.arange(counts_x, dtype=real_dtype) * float(spacing_x) + float(first_x)
    )
    wavelengths = torch.tensor(spectrum.wavelengths, dtype=real_dtype)
    indices = medium.refractive_index(wavelengths).to(dtype=real_dtype)
    wave_number = 2.0 * math.pi * indices / wavelengths
    cos_y = float(direction.direction_cosine_y)
    cos_x = float(direction.direction_cosine_x)
    phase = wave_number.reshape(-1, 1, 1) * (
        cos_y * position_y.reshape(1, -1, 1)
        + cos_x * position_x.reshape(1, 1, -1)
    )
    return torch.polar(torch.ones_like(phase), phase)


def _independent_phasor_from_transverse(
    grid: SpatialGrid,
    carrier: TransverseWavevector,
    real_dtype: torch.dtype,
    spectral_count: int,
) -> torch.Tensor:
    # 共享横向波矢 ⇒ 相幅与波长无关：phase = ky·y + kx·x，在光谱轴上广播
    counts_y, counts_x = grid.sample_counts
    spacing_y, spacing_x = grid.sample_spacing
    first_y, first_x = grid.first_sample_position
    position_y = (
        torch.arange(counts_y, dtype=real_dtype) * float(spacing_y) + float(first_y)
    )
    position_x = (
        torch.arange(counts_x, dtype=real_dtype) * float(spacing_x) + float(first_x)
    )
    phase = (
        float(carrier.wavevector_y) * position_y.reshape(-1, 1)
        + float(carrier.wavevector_x) * position_x.reshape(1, -1)
    )
    phase_batch = phase.unsqueeze(0).expand(spectral_count, -1, -1)
    return torch.polar(torch.ones_like(phase_batch), phase_batch)


class TestPhysicalInvariants:
    """
    证据层 1：物理不变量
    """

    def test_relative_amplitude_yields_relative_field(self) -> None:
        """
        仅提供相对振幅时输出光场归一化为 RELATIVE
        """
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=2.0,
        )
        field = source(_grid())
        assert isinstance(field, OpticalField)
        assert field.normalization is FieldNormalization.RELATIVE

    def test_total_power_yields_power_field(self) -> None:
        """
        仅提供总功率时输出光场归一化为 POWER
        """
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
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
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=relative_amplitude,
        )
        envelope = source(
            _grid(counts=(2, 2), spacing=(0.5e-6, 0.5e-6)),
        ).envelope
        expected_envelope = torch.full(
            (1, 1, 2, 2),
            complex(float.fromhex("0x1.4000000000000p+0"), 0.0),
            dtype=torch.complex128,
        )

        assert torch.equal(envelope, expected_envelope)
        gradient = torch.autograd.grad(
            envelope.real.sum(),
            relative_amplitude,
        )[0]
        assert torch.equal(
            gradient,
            torch.tensor(
                float.fromhex("0x1.0000000000000p+2"),
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
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection.forward(),
            total_power=total_power,
        )
        envelope = source(
            _grid(counts=(2, 2), spacing=(0.5e-6, 0.5e-6)),
        ).envelope
        expected_envelope = torch.full(
            (1, 1, 2, 2),
            complex(float.fromhex("0x1.e848000000000p+19"), 0.0),
            dtype=torch.complex128,
        )

        assert torch.equal(envelope, expected_envelope)
        gradient = torch.autograd.grad(envelope.real.sum(), total_power)[0]
        assert torch.equal(
            gradient,
            torch.tensor(
                float.fromhex("0x1.e848000000000p+20"),
                dtype=torch.float64,
            ),
        )

    def test_neither_normalization_rejected(self) -> None:
        """
        既不提供相对振幅也不提供总功率须以稳定身份拒绝
        """
        with pytest.raises(ValueError, match="plane_wave_normalization_missing"):
            PlaneWave(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                propagation_direction=PropagationDirection.forward(),
            )

    def test_both_normalizations_rejected(self) -> None:
        """
        同时提供相对振幅与总功率须以稳定身份拒绝
        """
        with pytest.raises(ValueError, match="plane_wave_normalization_exclusive"):
            PlaneWave(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                propagation_direction=PropagationDirection.forward(),
                relative_amplitude=1.0,
                total_power=1.0,
            )

    @pytest.mark.parametrize(
        ("parameter_name", "identity"),
        (
            ("relative_amplitude", "plane_wave_relative_amplitude_invalid"),
            ("total_power", "plane_wave_total_power_invalid"),
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
            "propagation_direction": PropagationDirection.forward(),
        }
        for invalid_value in (
            torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float32)),
            torch.tensor(1.0, dtype=torch.float64),
        ):
            arguments = dict(base_arguments)
            arguments[parameter_name] = invalid_value
            with pytest.raises((TypeError, ValueError), match=identity):
                PlaneWave(**arguments)  # type: ignore[arg-type]

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
            "propagation_direction": PropagationDirection.forward(),
            parameter_name: parameter,
        }
        source = PlaneWave(**arguments)  # type: ignore[arg-type]

        assert getattr(source, parameter_name) is parameter
        assert dict(source.named_parameters())[parameter_name] is parameter

    @pytest.mark.parametrize(
        "invalid_amplitude",
        [0.0, -1.0, float("nan"), float("inf")],
    )
    def test_relative_amplitude_must_be_positive_finite(
        self,
        invalid_amplitude: float,
    ) -> None:
        """
        相对振幅须为正有限值
        """
        with pytest.raises(ValueError):
            PlaneWave(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                propagation_direction=PropagationDirection.forward(),
                relative_amplitude=invalid_amplitude,
            )

    @pytest.mark.parametrize("invalid_power", [0.0, -1.0e-3, float("nan")])
    def test_total_power_must_be_positive_finite(self, invalid_power: float) -> None:
        """
        总功率须为正有限值
        """
        with pytest.raises(ValueError):
            PlaneWave(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                propagation_direction=PropagationDirection.forward(),
                total_power=invalid_power,
            )

    def test_output_envelope_has_fixed_axes_and_complex_dtype(self) -> None:
        """
        输出包络遵循固定轴布局（光谱、偏振、高度、宽度）且为复数
        """
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.5,
        )
        field = source(_grid())
        assert field.envelope.shape == (1, 1, 8, 8)
        assert torch.is_complex(field.envelope)
        assert field.batch_shape == ()
        assert field.envelope.device.type == "cpu"

    @pytest.mark.parametrize("default_real_dtype", (torch.float32, torch.float64))
    def test_output_dtype_ignores_process_default(
        self,
        default_real_dtype: torch.dtype,
    ) -> None:
        """
        源输出精度来自 fixed-double 契约，而非进程默认 dtype
        """

        previous_default = torch.get_default_dtype()
        try:
            torch.set_default_dtype(default_real_dtype)
            source = PlaneWave(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                propagation_direction=PropagationDirection.forward(),
                relative_amplitude=1.0,
            )
            field = source(_grid())
        finally:
            torch.set_default_dtype(previous_default)

        assert field.envelope.dtype is torch.complex128

    def test_relative_phasor_has_unit_modulus(self) -> None:
        """
        相对振幅平面波：包络模除以振幅处处为 1（纯空间相幅单位模）
        """
        amplitude = 1.5
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection(0.3, 0.4),
            relative_amplitude=amplitude,
        )
        field = source(_grid())
        modulus = field.envelope[0, 0].abs()
        assert torch.allclose(
            modulus,
            torch.full_like(modulus, amplitude),
            atol=1e-5,
        )

    def test_user_parameter_identity_preserved(self) -> None:
        """
        用户 supplied Parameter 须保持身份注册，不被克隆
        """
        amplitude = torch.nn.Parameter(torch.tensor(2.0, dtype=torch.float64))
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=amplitude,
        )
        assert source.relative_amplitude is amplitude
        assert any(parameter is amplitude for parameter in source.parameters())

    def test_total_power_rejects_zero_weight_spectrum(self) -> None:
        """零权重光谱与总功率组合须在源边界以稳定身份拒绝，而非产生 inf/nan

        ``Spectrum`` 仅要求 ``weights >= 0``，故全零权重合法；此时 POWER 振幅导出
        分母为零，会产生 inf/nan 包络并被静默传播，违反"非法物理在所属边界失败"
        的规约。此处验证源边界守护：调用源须以稳定身份
        ``plane_wave_total_power_spectrum_weight_sum_invalid`` 抛出 ValueError。
        """
        wavelengths = (2.0e-6,)
        weights = (0.0,)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            total_power=1.0e-3,
        )
        with pytest.raises(

            ValueError,

            match="plane_wave_total_power_spectrum_weight_sum_invalid",

        ):
            source(_grid())


class TestDirectionSpecification:
    """
    方向规格互斥与类型契约（规约"Plane Wave"）
    """

    def test_exactly_one_direction_required(self) -> None:
        """
        既不提供传播方向也不提供横向波矢须以稳定身份拒绝
        """
        with pytest.raises(

            ValueError,

            match="plane_wave_direction_specification_missing",

        ):
            PlaneWave(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                relative_amplitude=1.0,
            )

    def test_both_directions_rejected(self) -> None:
        """
        同时提供传播方向与横向波矢须以稳定身份拒绝
        """
        with pytest.raises(

            ValueError,

            match="plane_wave_direction_specification_exclusive",

        ):
            PlaneWave(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                propagation_direction=PropagationDirection.forward(),
                transverse_wavevector=TransverseWavevector(0.0, 0.0),
                relative_amplitude=1.0,
            )

    def test_wrong_direction_type_rejected(self) -> None:
        """
        传播方向参数须为 ``PropagationDirection`` 类型
        """
        with pytest.raises(

            TypeError,

            match="plane_wave_propagation_direction_invalid",

        ):
            PlaneWave(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                propagation_direction=(0.0, 0.0),  # type: ignore[arg-type]
                relative_amplitude=1.0,
            )


class TestIndependentReference:
    """
    证据层 2：独立解析参照

    独立参照一律在双精度下计算；产品固定双精度（ADR-0005），两侧精度一致，
    可逐位比对。
    """

    def test_tilted_monochromatic_phasor_matches(self) -> None:
        """单色倾斜平面波相幅须与独立计算的 exp(i k·r) 一致

        独立参照见 ``_independent_phasor_from_direction`` 说明；振幅取 1.0
        使包络即相幅。
        """
        direction = PropagationDirection(0.3, 0.4)
        spectrum = _monochromatic(wavelength=2.0e-6)
        grid = _grid()
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=direction,
            relative_amplitude=1.0,
        )
        field = source(grid)
        reference = _independent_phasor_from_direction(
            grid,
            spectrum,
            Vacuum(),
            direction,
            torch.float64,
        )
        assert torch.allclose(field.envelope[0, 0], reference[0])

    def test_multispectral_constant_medium_phasor_matches(self) -> None:
        """多光谱 + 恒定介质：每个光谱分量相幅须与独立计算一致

        介质折射率进入波数 ``k = 2 pi n / lambda``；一个传播方向 ⇒ 所有分量共享
        (cy,cx)，|k| 随 λ 变化。独立参照逐波长独立计算相幅，振幅 2.0 在各分量上一致。
        """
        direction = PropagationDirection(0.2, -0.1)
        wavelengths = (2.0e-6, 3.0e-6)
        weights = (0.4, 0.6)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        medium = ConstantMedium(index=1.5)
        grid = _grid()
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=medium,
            propagation_direction=direction,
            relative_amplitude=2.0,
        )
        field = source(grid)
        reference = _independent_phasor_from_direction(
            grid,
            spectrum,
            medium,
            direction,
            torch.float64,
        )
        assert torch.allclose(field.envelope[:, 0], 2.0 * reference)

    def test_multispectral_source_starts_with_zero_path_reference(self) -> None:
        """
        多光谱源的计算与描述从同一逐光谱零光程参考开始
        """
        spectrum = Spectrum(
            wavelengths=(0.45e-6, 0.55e-6, 0.65e-6),
            weights=(0.2, 0.3, 0.5),
        )
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=ConstantMedium(index=1.4),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        grid = _grid()
        field_reference = source(grid).path_reference
        assert len(field_reference.lengths) == spectrum.count
        assert field_reference.lengths == (0.0,) * spectrum.count

    def test_common_direction_implies_per_wavelength_wavevector_magnitude(
        self,
    ) -> None:
        """一个传播方向 ⇒ 各分量方向相同，|k| 随 λ 与介质独立给出

        证据层 2：|k(λ)| = 2π n(λ)/λ 经独立勾股关系给出横向波矢 |k|·(cy,cx)。断言 Source
        内部相幅等价于 |k(λ)|·(cy·y + cx·x)。使用 Sellmeier 介质以同时验证色散路径。
        """
        direction = PropagationDirection(0.2, 0.1)
        wavelengths = torch.tensor([0.45e-6, 0.55e-6], dtype=torch.float64)
        spectrum = Spectrum(
            wavelengths=(0.45e-6, 0.55e-6),
            weights=(0.5, 0.5),
        )
        medium = SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.01046945),
            c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.03560653e2),
            wavelength_min=0.3e-6,
            wavelength_max=2.5e-6,
        )
        grid = _grid()
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=medium,
            propagation_direction=direction,
            relative_amplitude=1.0,
        )
        field = source(grid)
        # 独立参照：每波长 |k| 由介质查询独立给出，乘以共享 (cy,cx)
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
        indices = medium.refractive_index(wavelengths)
        wave_number = 2.0 * math.pi * indices / wavelengths
        phase = wave_number.reshape(-1, 1, 1) * (
            0.2 * position_y.reshape(1, -1, 1)
            + 0.1 * position_x.reshape(1, 1, -1)
        )
        reference = torch.polar(torch.ones_like(phase), phase)
        assert torch.allclose(field.envelope[:, 0], reference)

    def test_shared_transverse_wavevector_phasor_matches(self) -> None:
        """共享横向波矢 ⇒ 相幅与波长无关：phase = ky·y + kx·x 跨光谱广播

        规约"Transverse Wavevector"：共享 (ky,kx) 产生随波长变化的方向，但横向相幅
        本身（跨光谱）相同。独立参照见 ``_independent_phasor_from_transverse``。
        """
        carrier = TransverseWavevector(2.0e5, -1.0e5)
        wavelengths = (0.45e-6, 0.65e-6)
        weights = (0.5, 0.5)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        grid = _grid()
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            transverse_wavevector=carrier,
            relative_amplitude=1.0,
        )
        field = source(grid)
        reference = _independent_phasor_from_transverse(
            grid,
            carrier,
            torch.float64,
            spectral_count=2,
        )
        assert torch.allclose(field.envelope[:, 0], reference)


class TestTransverseWavevectorPropagatingCondition:
    """
    共享横向波矢：每光谱分量独立判定传播条件，倏逝分量须拒绝（无静默裁剪）
    """

    def test_evanescent_per_component_rejects_whole_source(self) -> None:
        """某分量倏逝 ⇒ 整源以稳定身份拒绝，不静默裁剪

        规约横向波矢条目规避项：静默倏逝裁剪。构造双波长光谱：短波长 |k|
        大（传播），长波长 |k| 小（倏逝）；共享 (ky,kx) 使长波长分量违反传播条件。
        源须在调用边界以稳定身份拒绝，而非裁剪或静默输出。该拒绝属于
        逐对采样栅栏，稳定身份为 ``plane_wave_sampling_insufficient``。
        """
        wavelengths = (0.5e-6, 2.0e-6)
        weights = (0.5, 0.5)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        # 选 ky = 4.0e6 rad/m：对 2.0 µm 倏逝（16e12 > 9.87e12），对 0.5 µm 传播
        carrier = TransverseWavevector(4.0e6, 0.0)
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            transverse_wavevector=carrier,
            relative_amplitude=1.0,
        )
        with pytest.raises(

            ValueError,

            match="plane_wave_sampling_insufficient",

        ):
            source(_grid())

    def test_all_components_propagating_accepted(self) -> None:
        """
        所有分量均满足传播条件 ⇒ 接受，输出正常包络
        """
        wavelengths = (0.45e-6, 0.65e-6)
        weights = (0.5, 0.5)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        # ky = 1.0e6 对两波长均远小于 |k|
        carrier = TransverseWavevector(1.0e6, 0.5e6)
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            transverse_wavevector=carrier,
            relative_amplitude=1.0,
        )
        field = source(_grid())
        assert field.envelope.shape == (2, 1, 8, 8)


class TestCarrierSamplingFence:
    """
    逐对严格采样栅栏证据

    每条 PlaneWave 公共创建路径在合成场前以 精确符号原语判定载波能否在
    横向网格上被严格采样。逐轴 Nyquist（|Δcycles| < 0.5，按每物理 (n_i, λ_i) 对）
    与逐光谱辐射支持（κ_y²+κ_x² < (2π·n_i/λ_i)²，掠射不支持）均以同一稳定身份
    ``plane_wave_sampling_insufficient`` 拒绝；恰等半周期与掠射等号精确返回 0 被拒。
    """

    def test_y_only_carrier_within_nyquist_accepted(self) -> None:
        """
        仅纵向轴载波、每样本周期增量严格小于半周期 ⇒ 接受并给出解析一致的相邻相位增量
        """
        spectrum = _monochromatic(wavelength=1.0e-6)
        grid = SpatialGrid.centered(
            sample_counts=(8, 2),
            sample_spacing=(0.4e-6, 1.0e-6),
        )
        # 纵向每样本周期增量 = 1·0.5·0.4e-6/1.0e-6 = 0.2 < 0.5
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection(0.5, 0.0),
            relative_amplitude=1.0,
        )
        field = source(grid)
        # 相邻样本相位增量 = 2π·0.2 = 0.4π 弧度；解析相幅增量 = exp(i·0.4π)
        phasor_increment = (
            field.envelope[0, 0, 4, 0] / field.envelope[0, 0, 3, 0]
        )
        expected = torch.tensor(
            math.cos(0.4 * math.pi) + 1j * math.sin(0.4 * math.pi),
            dtype=torch.complex128,
        )
        assert torch.allclose(
            phasor_increment,
            expected,
            atol=1e-12,
            rtol=1e-12,
        )

    def test_x_only_carrier_within_nyquist_accepted(self) -> None:
        """
        仅横向轴载波、每样本周期增量绝对值严格小于半周期 ⇒ 接受
        """
        spectrum = _monochromatic(wavelength=1.0e-6)
        grid = SpatialGrid.centered(
            sample_counts=(2, 8),
            sample_spacing=(1.0e-6, 0.4e-6),
        )
        # 横向每样本周期增量 = 1·(−0.5)·0.4e-6/1.0e-6 = −0.2，绝对值 < 0.5
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection(0.0, -0.5),
            relative_amplitude=1.0,
        )
        field = source(grid)
        assert field.envelope.shape == (1, 1, 2, 8)

    def test_both_axis_carrier_within_nyquist_accepted(self) -> None:
        """
        纵横向同时载波、两轴每样本周期增量均严格小于半周期 ⇒ 接受
        """
        spectrum = _monochromatic(wavelength=1.0e-6)
        grid = _grid()
        # 纵向增量 = 0.15；横向增量 = 0.05；两者均 < 0.5
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection(0.3, 0.1),
            relative_amplitude=1.0,
        )
        field = source(grid)
        assert field.envelope.shape == (1, 1, 8, 8)

    @pytest.mark.parametrize(
        "orientation",
        [
            ("increasing", "increasing"),
            ("decreasing", "increasing"),
            ("increasing", "decreasing"),
            ("decreasing", "decreasing"),
        ],
    )
    def test_positive_and_negative_spacing_treated_symmetrically(
        self,
        orientation: tuple[str, str],
    ) -> None:
        """
        带符号间距翻转（朝向）不改每样本周期增量的绝对值：四种朝向均通过
        """
        spectrum = _monochromatic(wavelength=1.0e-6)
        grid = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.4e-6, 0.4e-6),
            orientation=orientation,
        )
        # 纵向增量 = 0.2；横向增量 = 0.16；两者均 < 0.5
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection(0.5, 0.4),
            relative_amplitude=1.0,
        )
        field = source(grid)
        # 全 4 朝向的相幅增量绝对值相同（仅符号随朝向翻转）
        assert field.envelope.shape == (1, 1, 8, 8)

    def test_dispersive_spectrum_uses_physical_pairs_not_cross_paired_extrema(
        self,
    ) -> None:
        """栅栏按每个物理 (n_i, λ_i) 对独立判定，不取 max(n)/min(λ) 交叉极值

        构造反常色散 TabulatedMedium：短波长配低折射率、长波长配高折射率，使
        max(n)/min(λ) 交叉极值远大于任一真实物理对的 n/λ。spacing = 0.20 µm 时
        最坏物理对 |Δcycles| ≈ 0.40 < 0.5（栅栏接受），但交叉极值 |Δcycles| ≈
        0.60 > 0.5（错误取交叉极值则会误拒）。略增间距到 0.30 µm 使最坏物理对
        越界（≈ 0.60 > 0.5），栅栏正确拒绝——证明判定确实走在物理对上。
        """
        medium = TabulatedMedium(
            wavelengths=(0.45e-6, 0.70e-6),
            refractive_indices=(1.00, 1.50),
        )
        wavelengths = (0.45e-6, 0.70e-6)
        weights = (0.5, 0.5)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=medium,
            propagation_direction=PropagationDirection(0.9, 0.0),
            relative_amplitude=1.0,
        )
        grid_pass = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.20e-6, 0.20e-6),
        )
        field = source(grid_pass)
        assert field.envelope.shape == (2, 1, 8, 8)
        # spacing 0.30 µm：最坏物理对 Δcycles ≈ 2.222e6·0.9·0.30e-6 ≈ 0.60 > 0.5
        grid_fail = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.30e-6, 0.30e-6),
        )
        with pytest.raises(
            ValueError,
            match="plane_wave_sampling_insufficient",
        ):
            source(grid_fail)

    def test_three_point_six_pi_carrier_rejected_on_both_paths(self) -> None:
        """每样本 3.6π 弧度（1.8 周期）载波在两条方向路径上均被拒绝

        若无栅栏，1.8 周期/样本经 phasor 折叠后等价于 −0.2 周期，造成静默混叠。
        """
        grid = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(2.0, 1.0),
        )
        # 传播方向路径：Δcycles = 1·0.9·2.0/1.0 = 1.8（= 3.6π rad/样本）
        direction_source = PlaneWave(
            spectrum=Spectrum.monochromatic(wavelength=1.0),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection(0.9, 0.0),
            relative_amplitude=1.0,
        )
        with pytest.raises(
            ValueError,
            match="plane_wave_sampling_insufficient",
        ):
            direction_source(grid)
        # 横向波矢路径：κ_y = 2π·0.9 ⇒ ν_y = 0.9；Δcycles_y = 0.9·2.0 = 1.8
        transverse_source = PlaneWave(
            spectrum=Spectrum.monochromatic(wavelength=1.0),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            transverse_wavevector=TransverseWavevector(
                2.0 * math.pi * 0.9,
                0.0,
            ),
            relative_amplitude=1.0,
        )
        with pytest.raises(
            ValueError,
            match="plane_wave_sampling_insufficient",
        ):
            transverse_source(grid)

    def test_direction_and_transverse_paths_yield_same_field_when_equivalent(
        self,
    ) -> None:
        """两条方向路径物理上不同，但对等效载波给出同一光场

        单色真空、传播方向 (cy, cx) 对应横向波矢 κ = (2π/λ)·(cy, cx)。两条路径
        在数值核内以不同的张量化路径到达同一周期相位，逐样本相幅须一致。
        """
        spectrum = _monochromatic(wavelength=0.5e-6)
        grid = _grid()
        direction = PropagationDirection(0.3, -0.2)
        direction_field = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=direction,
            relative_amplitude=1.0,
        )(grid)
        kappa_y = 2.0 * math.pi * 0.3 / 0.5e-6
        kappa_x = 2.0 * math.pi * (-0.2) / 0.5e-6
        transverse_field = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            transverse_wavevector=TransverseWavevector(kappa_y, kappa_x),
            relative_amplitude=1.0,
        )(grid)
        assert torch.allclose(
            direction_field.envelope,
            transverse_field.envelope,
            atol=1e-12,
            rtol=1e-12,
        )

    def test_fence_preserves_supported_gradient_through_source(self) -> None:
        """栅栏不破坏可训练间距的载波梯度（源→光场后向给出有限非零梯度）

        精确梯度一致性由 ``tests/_numerics/test_plane_wave.py`` 的两个 gradcheck
        用例（间距、折射率）直接覆盖——它们驱动现在内置栅栏的 ``plane_wave_envelope``。
        此处补充源级证据：栅栏通过后，可训练 spacing 进入包络并保留有限非零梯度。
        """
        from chromatix_next._numerics.plane_wave import plane_wave_envelope

        wavelengths = torch.tensor(
            (1.0,),
            dtype=torch.float64,
            requires_grad=False,
        )
        spacing_y = torch.tensor(
            0.25,
            dtype=torch.float64,
            requires_grad=True,
        )
        envelope = plane_wave_envelope(
            sample_counts=(4, 4),
            signed_spacing=(spacing_y, torch.tensor(0.30, dtype=torch.float64)),
            first_sample_position=(
                torch.tensor(0.0, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
            ),
            wavelengths=wavelengths,
            refractive_indices=torch.tensor((1.0,), dtype=torch.float64),
            polarization_state=torch.ones(1, dtype=torch.complex128),
            propagation_direction=(
                torch.tensor(0.2, dtype=torch.float64),
                torch.tensor(0.1, dtype=torch.float64),
            ),
            transverse_wavevector=None,
        )
        envelope.real.sum().backward()
        assert spacing_y.grad is not None
        assert bool(torch.isfinite(spacing_y.grad))
        assert bool(spacing_y.grad != 0.0)


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is unavailable",
)
class TestCarrierSamplingFenceOnCUDA:
    """
    栅栏在 CUDA 上的判定与数值与 CPU 一致
    """

    def test_cuda_rejects_unsamplable_carrier_with_same_identity(self) -> None:
        """
        CUDA 上无法采样的载波以同一稳定身份拒绝
        """
        spectrum = _monochromatic(wavelength=1.0e-6)
        grid = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(2.0e-6, 1.0e-6),
        ).to(device="cuda", dtype=torch.float64)
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection(0.9, 0.0),
            relative_amplitude=1.0,
        )
        with pytest.raises(
            ValueError,
            match="plane_wave_sampling_insufficient",
        ):
            source(grid)

    def test_cuda_accepts_samplable_carrier_matching_cpu(self) -> None:
        """
        CUDA 上可通过栅栏的载波与 CPU 逐样本一致
        """
        spectrum = _monochromatic(wavelength=0.5e-6)
        cpu_grid = _grid()
        cuda_grid = cpu_grid.to(device="cuda", dtype=torch.float64)
        direction = PropagationDirection(0.2, 0.1)
        cpu_field = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=direction,
            relative_amplitude=1.0,
        )(cpu_grid)
        cuda_field = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=direction,
            relative_amplitude=1.0,
        )(cuda_grid)
        assert torch.allclose(
            cpu_field.envelope,
            cuda_field.envelope.cpu(),
            atol=1e-12,
            rtol=1e-12,
        )


class TestMediumRangeRejection:
    """
    PlaneWave 经表格/Sellmeier 介质：表外光谱须在介质边界拒绝
    """

    def test_tabulated_medium_rejects_out_of_range_spectrum(self) -> None:
        """光谱落在表格范围外 ⇒ 介质边界以稳定身份拒绝

        规约传播介质条目规避项：静默外推。折射率查询在介质边界失败，错误身份
        为 ``tabulated_medium_wavelength_out_of_range``。
        """
        medium = TabulatedMedium(
            wavelengths=(0.40e-6, 0.70e-6),
            refractive_indices=(1.53, 1.50),
        )
        spectrum = Spectrum.monochromatic(wavelength=0.80e-6)
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=medium,
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        with pytest.raises(

            ValueError,

            match="tabulated_medium_wavelength_out_of_range",

        ):
            source(_grid())

    def test_sellmeier_medium_rejects_out_of_range_spectrum(self) -> None:
        """
        光谱落在 Sellmeier 声明范围外 ⇒ 介质边界以稳定身份拒绝
        """
        medium = SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.01046945),
            c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.03560653e2),
            wavelength_min=0.3e-6,
            wavelength_max=2.5e-6,
        )
        spectrum = Spectrum.monochromatic(wavelength=3.0e-6)
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=medium,
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        with pytest.raises(

            ValueError,

            match="sellmeier_medium_wavelength_out_of_range",

        ):
            source(_grid())


class TestNoDuplicateRefractiveIndexArgument:
    """
    规约"Propagation Medium"：折射率由源声明的介质给出，下游组件不接受重复折射率参数
    """

    def test_planewave_signature_has_no_refractive_index_parameter(self) -> None:
        """
        ``PlaneWave`` 构造签名不含 ``refractive_index`` 参数
        """
        signature = inspect.signature(PlaneWave.__init__)
        assert "refractive_index" not in signature.parameters
        assert "index" not in signature.parameters

    def test_intensity_detection_signature_has_no_refractive_index_parameter(
        self,
    ) -> None:
        """
        ``IntensityDetection`` 不接受重复折射率参数
        """
        signature = inspect.signature(IntensityDetection.__init__)
        assert "refractive_index" not in signature.parameters
        assert "index" not in signature.parameters


class TestGradientEvidence:
    """
    证据层 3：梯度证据（方向/介质为固定物理值；可训练振幅经新路径保持可微）
    """

    def test_gradcheck_on_trainable_relative_amplitude(self) -> None:
        """对可训练相对振幅经 PlaneWave→IntensityDetection 链路做 gradcheck

        可训练相对振幅为 float64 叶子 Parameter，注册身份保持；整条链处处可微。
        """
        amplitude = torch.nn.Parameter(torch.tensor(1.25, dtype=torch.float64))
        grid = _grid()
        spectrum = _monochromatic()
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection(0.2, 0.1),
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
        对可训练总功率经 PlaneWave→IntensityDetection 链路做 gradcheck
        """
        total_power = torch.nn.Parameter(torch.tensor(1.0e-3, dtype=torch.float64))
        grid = _grid()
        spectrum = _monochromatic()
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            total_power=total_power,
        )
        detection = IntensityDetection()

        def run(total_power_value: torch.Tensor) -> torch.Tensor:
            """
            返回给定总功率下的光强空间总和（实数标量）
            """
            return detection(source(grid)).values.sum()

        assert torch.autograd.gradcheck(run, (total_power,), raise_exception=True)

    def test_gradcheck_through_tabulated_medium_path(self) -> None:
        """经 TabulatedMedium 路径对可训练相对振幅做 gradcheck（介质为固定值）

        方向/介质为固定物理值（Buffer 语义，非可训练 Parameter）；此处验证经色散介质
        路径整条链仍处处可微。
        """
        amplitude = torch.nn.Parameter(torch.tensor(1.1, dtype=torch.float64))
        grid = _grid()
        wavelengths = (0.45e-6, 0.55e-6)
        weights = (0.5, 0.5)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        medium = TabulatedMedium(
            wavelengths=(0.40e-6, 0.50e-6, 0.60e-6, 0.70e-6),
            refractive_indices=(1.53, 1.52, 1.51, 1.50),
        )
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=medium,
            propagation_direction=PropagationDirection(0.1, 0.05),
            relative_amplitude=amplitude,
        )
        detection = IntensityDetection()

        def run(amplitude_value: torch.Tensor) -> torch.Tensor:
            """
            返回给定振幅下的光强总和
            """
            return detection(source(grid)).values.sum()

        assert torch.autograd.gradcheck(run, (amplitude,), raise_exception=True)

    def test_gradcheck_through_transverse_wavevector_path(self) -> None:
        """经共享横向波矢路径对可训练相对振幅做 gradcheck（方向为固定值）

        横向波矢为固定物理值；此处验证经横向波矢路径整条链仍处处可微。
        """
        amplitude = torch.nn.Parameter(torch.tensor(1.2, dtype=torch.float64))
        grid = _grid()
        wavelengths = (0.45e-6, 0.65e-6)
        weights = (0.5, 0.5)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        source = PlaneWave(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            transverse_wavevector=TransverseWavevector(5.0e4, 3.0e4),
            relative_amplitude=amplitude,
        )
        detection = IntensityDetection()

        def run(amplitude_value: torch.Tensor) -> torch.Tensor:
            """
            返回给定振幅下的光强总和
            """
            return detection(source(grid)).values.sum()

        assert torch.autograd.gradcheck(run, (amplitude,), raise_exception=True)

    def test_explicit_grid_origin_gradient_matches_finite_difference(
        self,
    ) -> None:
        """倾斜平面波对显式首样本位置的梯度与中心有限差分一致

        1e-10 步长中心有限差分与自动微分逐位对账。``plane_wave_envelope``
        帧内非确定性归约顺序使反向与正向在末位抖动，全量套件负载下偶发
        越过 ``rel=1e-8``；根因为线程并行非确定性，单线程上下文执行对账即
        稳定消除，仍保留 1e-8 严格契约。
        """

        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            transverse_wavevector=TransverseWavevector(2.0e5, 0.0),
            relative_amplitude=1.0,
        )
        first_position_y = torch.nn.Parameter(
            torch.tensor(-2.0e-6, dtype=torch.float64),
        )

        def observe(position_y: float | torch.Tensor) -> torch.Tensor:
            """
            返回首样本处包络虚部作为显式坐标的相位观测
            """

            grid = SpatialGrid(
                sample_counts=(4, 4),
                sample_spacing=(
                    torch.tensor(0.5e-6, dtype=torch.float64),
                    torch.tensor(0.5e-6, dtype=torch.float64),
                ),
                first_sample_position=(
                    (
                        position_y
                        if isinstance(position_y, torch.Tensor)
                        else torch.tensor(position_y, dtype=torch.float64)
                    ),
                    torch.tensor(-1.0e-6, dtype=torch.float64),
                ),
            )
            return source(grid).envelope[0, 0, 0, 0].imag

        saved_thread_count = torch.get_num_threads()
        torch.set_num_threads(1)
        try:
            automatic_gradient = torch.autograd.grad(
                observe(first_position_y),
                first_position_y,
            )[0]
            step = 1.0e-10
            origin = float(first_position_y.detach())
            finite_difference = (
                float(observe(origin + step))
                - float(observe(origin - step))
            ) / (2.0 * step)
        finally:
            torch.set_num_threads(saved_thread_count)

        assert float(automatic_gradient) == pytest.approx(
            finite_difference,
            rel=1.0e-8,
        )


class TestDeviceAndCache:
    """
    输出设备一致性与可训练网格缓存重建（固定双精度）
    """

    @pytest.mark.parametrize(
        "device",
        [
            pytest.param("cpu", id="cpu"),
            pytest.param(
                "cuda",
                id="cuda",
                marks=pytest.mark.skipif(
                    not torch.cuda.is_available(),
                    reason="CUDA is not available",
                ),
            ),
        ],
    )
    def test_output_grid_follows_source_device(
        self,
        device: str,
    ) -> None:
        """
        输出网格与包络共同服从光源所在设备，并保持固定双精度
        """
        grid = SpatialGrid(
            sample_counts=(6, 8),
            sample_spacing=(
                torch.tensor(0.4e-6, dtype=torch.float64),
                torch.tensor(0.5e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-1.2e-6, dtype=torch.float64),
                torch.tensor(-2.0e-6, dtype=torch.float64),
            ),
        )
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        ).to(device=device)

        field = source(grid)
        grid_values = (
            *field.grid.sample_spacing,
            *field.grid.first_sample_position,
        )

        assert field.envelope.device.type == device
        assert field.envelope.dtype is torch.complex128
        assert all(value.device.type == device for value in grid_values)
        assert all(value.dtype is torch.float64 for value in grid_values)

    def test_fixed_grid_reuses_registered_unit_envelope(self) -> None:
        """
        相同固定光源与网格连续前向复用同一份单位包络缓存
        """
        grid = _grid()
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )

        source(grid)
        first_cache = dict(source.named_buffers())["_unit_envelope_cache"]
        source(grid)
        second_cache = dict(source.named_buffers())["_unit_envelope_cache"]

        assert first_cache is not None
        assert second_cache is first_cache

    def test_trainable_grid_rebuilds_cache_for_each_backward(self) -> None:
        """
        可训练采样间距连续两次前向与反传均重建当前计算图
        """
        spacing_y = torch.nn.Parameter(
            torch.tensor(0.4e-6, dtype=torch.float64),
        )
        grid = SpatialGrid.centered(
            sample_counts=(6, 8),
            sample_spacing=(
                spacing_y,
                torch.tensor(0.5e-6, dtype=torch.float64),
            ),
        )
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection(0.2, 0.1),
            relative_amplitude=1.0,
        )
        gradients: list[torch.Tensor] = []

        for _ in range(2):
            source(grid).envelope.real.sum().backward()
            assert spacing_y.grad is not None
            gradients.append(spacing_y.grad.detach().clone())
            spacing_y.grad = None

        assert torch.isfinite(torch.stack(gradients)).all()
        assert torch.count_nonzero(gradients[0]) == 1
        assert torch.equal(gradients[0], gradients[1])


class TestHostedExecution:
    """
    托管端到端：经 IntensityDetection 验证归一化语义
    """

    def test_hosted_relative_source_through_detection(self) -> None:
        """托管 RELATIVE 平面波经 IntensityDetection 仍为相对光强

        相对振幅 2.0、单位模相幅、标量偏振、单位光谱权重：每像素光强 = 4，无 W/m² 主张。
        """
        workstation = Workstation.cpu()
        source = workstation.host(
            PlaneWave(
                spectrum=_monochromatic(),
                polarization=Polarization.scalar(),
                medium=Vacuum(),
                propagation_direction=PropagationDirection.forward(),
                relative_amplitude=2.0,
            ),
        )
        detection = workstation.host(IntensityDetection())
        field = source(_grid())
        assert field.envelope.dtype is torch.complex128
        intensity = detection(field)
        assert intensity.normalization is FieldNormalization.RELATIVE
        expected = torch.full((8, 8), 4.0, dtype=torch.float64)
        assert torch.allclose(intensity.values, expected, atol=1e-5)

    def test_plane_wave_materializes_jones_state_from_buffers(self) -> None:
        """
        平面波由注册 Buffer 生成空间相位与 Jones 向量乘积
        """

        source = PlaneWave(
            spectrum=Spectrum(
                wavelengths=(0.5e-6, 0.6e-6),
                weights=(0.4, 0.6),
            ),
            polarization=Polarization.linear_y(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=2.0,
        )
        field = source(_grid())
        buffers = dict(source.named_buffers())

        assert {
            "wavelengths",
            "spectral_weights",
            "polarization_state",
        } <= buffers.keys()
        assert field.envelope.shape == (2, 2, 8, 8)
        assert torch.count_nonzero(field.envelope[:, 0]) == 0
        assert torch.allclose(
            field.envelope[:, 1].abs(),
            torch.full((2, 8, 8), 2.0, dtype=torch.float64),
        )
        assert {
            "wavelengths",
            "spectral_weights",
            "polarization_state",
        } <= source.state_dict().keys()

    def test_tilted_plane_wave_keeps_laboratory_polarization_state(self) -> None:
        """
        倾斜标量传播不投影或改写实验室坐标偏振标签
        """

        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.left_circular(),
            propagation_direction=PropagationDirection(0.2, 0.1),
            relative_amplitude=1.0,
        )

        field = source(_grid())

        assert torch.allclose(
            field.envelope[:, 1],
            -1j * field.envelope[:, 0],
            atol=1.0e-12,
        )

    def test_frozen_assembly_preserves_polarization_and_total_power(self) -> None:
        """
        冻结装配托管运行同时保留偏振状态与声明总功率
        """

        grid = _grid()
        total_power = 2.5e-3
        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.right_circular(),
            propagation_direction=PropagationDirection.forward(),
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
        assert torch.allclose(
            field.envelope[:, 1],
            1j * field.envelope[:, 0],
            atol=1.0e-6,
        )
        integral = float(intensity.values.sum().item()) * grid.cell_area
        assert math.isclose(integral, total_power, rel_tol=1.0e-4)

    @pytest.mark.parametrize(
        "polarization",
        [Polarization.scalar(), Polarization.transverse()],
        ids=["scalar", "transverse"],
    )
    def test_hosted_power_source_total_power_integral(
        self,
        polarization: Polarization,
    ) -> None:
        """托管 POWER 平面波：Intensity 空间积分 × 单元面积 = 总功率（跨偏振表示）

        直接验证外部 Physical Value：探测的 Intensity 作为功率密度，其空间积分给出
        源声明的总功率，断言二者在容差内相等。横向偏振情形下振幅集中在单一分量，
        而 ``IntensityDetection`` 在偏振轴上求和，证明该不变量在偏振集中分布时仍成立。
        """
        total_power = 2.5e-3
        grid = _grid()
        workstation = Workstation.cpu()
        source = workstation.host(
            PlaneWave(
                spectrum=_monochromatic(),
                polarization=polarization,
                medium=Vacuum(),
                propagation_direction=PropagationDirection.forward(),
                total_power=total_power,
            ),
        )
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        assert field.normalization is FieldNormalization.POWER
        intensity = detection(field)
        integral = float(intensity.values.sum().item()) * grid.cell_area
        assert math.isclose(integral, total_power, rel_tol=1e-4)

    def test_multispectral_hosted_planewave_through_detection(self) -> None:
        """多光谱托管 PlaneWave 经 IntensityDetection 端到端

        多波长（Sellmeier 介质）传播方向平面波经托管源→探测链路：光强为实数、非负，
        形状仅保留空间轴，归一化语义保持。
        """
        wavelengths = (0.45e-6, 0.55e-6, 0.65e-6)
        weights = (0.3, 0.4, 0.3)
        spectrum = Spectrum(wavelengths=wavelengths, weights=weights)
        medium = SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.01046945),
            c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.03560653e2),
            wavelength_min=0.3e-6,
            wavelength_max=2.5e-6,
        )
        grid = _grid()
        workstation = Workstation.cpu()
        source = workstation.host(
            PlaneWave(
                spectrum=spectrum,
                polarization=Polarization.scalar(),
                medium=medium,
                propagation_direction=PropagationDirection(0.15, 0.10),
                total_power=1.0e-3,
            ),
        )
        detection = workstation.host(IntensityDetection())
        field = source(grid)
        assert field.envelope.shape == (3, 1, 8, 8)
        intensity = detection(field)
        assert intensity.normalization is FieldNormalization.POWER
        integral = float(intensity.values.sum().item()) * grid.cell_area
        assert math.isclose(integral, 1.0e-3, rel_tol=1e-4)


class TestMetaInference:
    """
    meta 设备上的形状与物理轮廓推导契约（供装配检查使用）
    """

    def test_meta_forward_carries_full_physical_outline(self) -> None:
        """
        meta 上的前向给出与真实执行相同的网格、光谱、介质、偏振与归一化
        """
        spectrum = _monochromatic()
        polarization = Polarization.scalar()
        source = PlaneWave(
            spectrum=spectrum,
            polarization=polarization,
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            total_power=1.0e-3,
        )
        grid = _grid()
        field = _forward_on_meta(source, grid)
        assert field.envelope.device.type == "meta"
        assert field.grid.sample_counts == grid.sample_counts
        assert field.grid.orientation == grid.orientation
        assert all(
            spacing.dtype is field.envelope.real.dtype
            for spacing in field.grid.sample_spacing
        )
        assert field.spectrum == spectrum
        assert (
            field.polarization_representation
            is polarization.representation
        )
        assert field.medium == Vacuum()
        assert field.normalization is FieldNormalization.POWER
        assert field.batch_shape == ()
        assert field.envelope_shape == (1, 1, 8, 8)
        assert field.envelope_shape == source(grid).envelope_shape

    def test_normalization_mirrors_input_choice(self) -> None:
        """
        归一化随相对振幅或总功率的选择镜像
        """
        grid = _grid()
        relative_source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        assert (
            relative_source(grid).normalization
            is FieldNormalization.RELATIVE
        )


class TestStateRoundTrip:
    """
    平面波固定物理状态的 PyTorch 序列化契约
    """

    def test_loading_state_restores_metadata_and_clears_unit_envelope(
        self,
    ) -> None:
        """
        热缓存后加载另一源状态须同步描述、计算 Buffer，并使单位包络缓存失效
        """

        grid = _grid()
        workstation = Workstation.cpu()
        target = PlaneWave(
            spectrum=Spectrum.monochromatic(wavelength=0.55e-6),
            polarization=Polarization.linear_x(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        donor = PlaneWave(
            spectrum=Spectrum(
                wavelengths=(0.50e-6, 0.65e-6),
                weights=(0.25, 0.75),
            ),
            polarization=Polarization.linear_y(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        workstation.host(donor)

        target(grid)
        warmed_cache = dict(target.named_buffers())["_unit_envelope_cache"]
        install_state(target, donor.state_dict())

        assert dict(target.named_buffers()).get("_unit_envelope_cache") is None
        expected_field = donor(grid)
        field = target(grid)

        assert field.spectrum == expected_field.spectrum
        assert (
            field.polarization_representation
            is expected_field.polarization_representation
        )
        assert field.envelope.shape == (2, 2, 8, 8)
        assert torch.count_nonzero(field.envelope[:, 0]) == 0
        assert torch.count_nonzero(field.envelope[:, 1]) > 0
        restored_cache = dict(target.named_buffers())["_unit_envelope_cache"]
        assert restored_cache is not warmed_cache

    @pytest.mark.parametrize(
        "polarization",
        [
            Polarization.left_circular(),
            Polarization.full(
                components=(
                    1.0 + 1.0j,
                    2.0 - 1.0j,
                    -0.5j,
                ),
            ),
        ],
        ids=["canonical", "custom_full"],
    )
    def test_state_round_trip_preserves_named_physical_metadata(
        self,
        polarization: Polarization,
    ) -> None:
        """
        双精度下规范与自定义完整偏振均由命名载荷逐位恢复，但不转移 Source Lineage
        """

        grid = _grid()
        spectrum = Spectrum(
            wavelengths=(0.48e-6, 0.63e-6),
            weights=(0.4, 0.6),
        )
        original = PlaneWave(
            spectrum=spectrum,
            polarization=polarization,
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        restored = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        workstation = Workstation.cpu()
        workstation.host(original)

        install_state(restored, original.state_dict())

        original_field = original(grid)
        field = restored(grid)
        assert field.batch_shape == original_field.batch_shape
        assert field.grid.is_physically_equivalent_to(original_field.grid)
        assert field.spectrum == spectrum
        assert (
            field.polarization_representation
            is original_field.polarization_representation
        )
        assert field.medium == original_field.medium
        assert field.normalization == original_field.normalization
        assert field.path_reference == original_field.path_reference
        with pytest.raises(
            AssemblyError,
            match="coherent_combination_source_lineage_mismatch",
        ):
            CoherentCombination()(original_field, field)
        assert field.envelope.shape[0] == spectrum.count
        assert field.envelope.shape[1] == polarization.component_count

    def test_partial_physical_state_is_rejected_before_mutation(self) -> None:
        """
        install_state 不接受缺少命名附加状态的子集，且不改变既有对象
        """

        grid = _grid()
        target = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        donor = PlaneWave(
            spectrum=Spectrum(
                wavelengths=(0.50e-6, 0.65e-6),
                weights=(0.25, 0.75),
            ),
            polarization=Polarization.linear_y(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        field_before = target(grid)
        buffers_before = {
            name: value.detach().clone()
            for name, value in target.named_buffers()
        }
        cache_before = dict(target.named_buffers())["_unit_envelope_cache"]
        partial_state = donor.state_dict()
        del partial_state["_extra_state"]

        with pytest.raises(
            OpticalRuntimeError,
            match="state_installation_keys_mismatch",
        ):
            install_state(target, partial_state)

        field_after = target(grid)
        assert field_after.spectrum == field_before.spectrum
        assert (
            field_after.polarization_representation
            is field_before.polarization_representation
        )
        buffers_after = dict(target.named_buffers())
        assert buffers_after["_unit_envelope_cache"] is cache_before
        for name, value_before in buffers_before.items():
            assert torch.equal(buffers_after[name], value_before)

    def test_loading_rejects_metadata_and_buffer_disagreement(self) -> None:
        """
        状态字典中命名物理载荷与计算 Buffer 不一致时须稳定拒绝
        """

        source = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )
        inconsistent_state = source.state_dict()
        inconsistent_state["polarization_state"] = torch.tensor(
            (0.0 + 0.0j, 1.0 + 0.0j),
            dtype=torch.complex128,
        )
        restored = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )

        with pytest.raises(
            RuntimeError,
            match="plane_wave_extra_state_buffer_mismatch",
        ):
            restored.load_state_dict(inconsistent_state)

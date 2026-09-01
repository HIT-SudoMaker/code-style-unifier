
from __future__ import annotations

import pytest
import torch

from chromatix_next.optics import (
    FieldNormalization,
    Intensity,
    OpticalField,
    OpticalPathReference,
    Polarization,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection, intensity_detection
from chromatix_next.workstation import Workstation


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(1.0e-6, 1.0e-6),
    )


def _spectrum(weights: torch.Tensor) -> Spectrum:
    count = int(weights.numel())
    wavelengths = tuple(500.0e-6 for _ in range(count))
    python_weights = tuple(weights.tolist())
    return Spectrum(wavelengths=wavelengths, weights=python_weights)


def _field(
    envelope: torch.Tensor,
    *,
    weights: torch.Tensor,
    polarization: Polarization | None = None,
    normalization: FieldNormalization = FieldNormalization.RELATIVE,
) -> OpticalField:
    if polarization is None:
        polarization = Polarization.scalar()
    spectrum = _spectrum(weights)
    return OpticalField(
        envelope=envelope,
        grid=_grid(),
        spectrum=spectrum,
        polarization_representation=(polarization).representation,
        medium=Vacuum(),
        normalization=normalization,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


class TestFunctionComponentDuality:
    """
    无状态函数与 PyTorch Component 的公开对偶
    """

    def test_function_and_component_return_the_same_intensity(self) -> None:
        """
        同一光场经两种公开形态得到完全相同的强光强值
        """
        envelope = torch.randn((2, 3, 2, 4, 4), dtype=torch.complex128)
        weights = torch.tensor([0.2, 0.5, 0.3], dtype=torch.float64)
        field = _field(
            envelope,
            weights=weights,
            polarization=Polarization.transverse(),
        )

        functional = intensity_detection(field)
        component = IntensityDetection()(field)

        assert type(functional) is type(component)
        assert functional.grid.is_physically_equivalent_to(component.grid)
        assert functional.normalization is component.normalization
        assert torch.equal(functional.values, component.values)

    def test_function_and_component_share_meta_shape_and_dtype(self) -> None:
        """
        两种公开形态在 meta 推导中给出相同的光强形状与实数精度
        """
        envelope = torch.empty(
            (2, 3, 2, 4, 4),
            dtype=torch.complex128,
            device="meta",
        )
        field = _field(
            envelope,
            weights=torch.tensor([0.2, 0.5, 0.3]),
            polarization=Polarization.transverse(),
        )

        functional = intensity_detection(field)
        component = IntensityDetection()(field)

        assert functional.values.is_meta
        assert component.values.is_meta
        assert functional.values.shape == component.values.shape
        assert functional.values.dtype == component.values.dtype

    def test_detection_reduces_scalar_and_transverse_fields_to_one_grid(
        self,
    ) -> None:
        """
        偏振分量和光谱分量均在探测边界约减为空间光强
        """

        scalar_field = _field(
            torch.ones((1, 1, 4, 4), dtype=torch.complex128),
            weights=torch.ones(1, dtype=torch.float64),
        )
        transverse_field = _field(
            torch.ones((2, 2, 4, 4), dtype=torch.complex128),
            weights=torch.full((2,), 0.5, dtype=torch.float64),
            polarization=Polarization.transverse(),
        )

        scalar_intensity = IntensityDetection()(scalar_field)
        transverse_intensity = IntensityDetection()(transverse_field)

        assert scalar_intensity.values.shape == (4, 4)
        assert transverse_intensity.values.shape == (4, 4)

    @pytest.mark.parametrize("default_real_dtype", (torch.float32, torch.float64))
    def test_detection_dtype_ignores_process_default(
        self,
        default_real_dtype: torch.dtype,
    ) -> None:
        """
        探测输出精度由固定双精度物理值决定，而非进程默认值
        """

        previous_default = torch.get_default_dtype()
        try:
            torch.set_default_dtype(default_real_dtype)
            field = _field(
                torch.ones((1, 1, 4, 4), dtype=torch.complex128),
                weights=torch.ones(1, dtype=torch.float64),
            )
            intensity = IntensityDetection()(field)
        finally:
            torch.set_default_dtype(previous_default)

        assert intensity.values.dtype is torch.float64


class TestPhysicalInvariants:
    """
    证据层 1：物理不变量
    """

    def test_intensity_is_real_and_nonnegative(self) -> None:
        """
        Intensity 数值为实数、非负且保留批量与空间轴
        """
        envelope = torch.randn((2, 3, 1, 4, 4), dtype=torch.complex128)
        weights = torch.tensor([0.2, 0.5, 0.3], dtype=torch.float64)
        field = _field(envelope, weights=weights)
        intensity = IntensityDetection()(field)
        assert isinstance(intensity, Intensity)
        assert not torch.is_complex(intensity.values)
        assert intensity.values.shape == (2, 4, 4)
        assert torch.all(intensity.values >= 0)
        assert intensity.grid.is_physically_equivalent_to(field.grid)

    def test_relative_field_carries_relative_semantics(self) -> None:
        """
        相对归一化光场产生的 Intensity 仍为相对量
        """
        envelope = torch.ones((1, 1, 1, 4, 4), dtype=torch.complex128)
        weights = torch.ones(1, dtype=torch.float64)
        field = _field(
            envelope,
            weights=weights,
            normalization=FieldNormalization.RELATIVE,
        )
        intensity = IntensityDetection()(field)
        assert intensity.normalization is FieldNormalization.RELATIVE
        assert intensity.units == "dimensionless"
        assert intensity.spectral_reduction == "weighted_sum"
        assert intensity.axis_meaning == (
            "batch_0",
            "height",
            "width",
        )

    def test_power_field_spatial_integral_equals_total_power(self) -> None:
        """功率光场：Intensity 空间积分等于光谱加权的总功率

        直接验证约减的载荷部分：积分 = sum_s w_s * sum_p integral(|E_sp|²)，
        即 Intensity 作为功率密度，其空间积分给出总功率。绝对幅值的最终标定由
        光源负责；本测试确认密度到积分的物理关系与光谱加权。
        """
        envelope = torch.randn((1, 2, 1, 4, 4), dtype=torch.complex128)
        weights = torch.tensor([0.4, 0.6], dtype=torch.float64)
        field = _field(
            envelope,
            weights=weights,
            normalization=FieldNormalization.POWER,
        )
        intensity = IntensityDetection()(field)
        assert intensity.normalization is FieldNormalization.POWER

        cell_area = field.grid.cell_area
        integral = intensity.values.sum() * cell_area

        # 独立参照：逐光谱、逐偏振取模方，按权重加权后对空间积分
        squared = (envelope * envelope.conj()).real
        per_spectrum = squared.sum(dim=-3).sum(dim=(-2, -1)).squeeze(0)
        expected = (per_spectrum * weights).sum() * cell_area
        assert torch.allclose(integral, expected)
        assert intensity.units == "watts_per_square_metre"

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_intensity_rejects_nonfinite_values(
        self,
        invalid_value: float,
    ) -> None:
        """
        光强中的 NaN 与正负无穷须由 Intensity 拒绝
        """

        values = torch.ones((4, 4), dtype=torch.float64)
        values[0, 0] = invalid_value
        with pytest.raises(
            ValueError,
            match="intensity_values_nonfinite",
        ):
            Intensity(
                values=values,
                grid=_grid(),
                normalization=FieldNormalization.RELATIVE,
            )

    @pytest.mark.parametrize(
        "dtype",
        [torch.bool, torch.int32, torch.int64],
    )
    def test_intensity_rejects_nonfloating_payload(
        self,
        dtype: torch.dtype,
    ) -> None:
        """
        光强拒绝会绕过工作站精度声明的布尔或整数载荷
        """
        with pytest.raises(
            TypeError,
            match="intensity_values_dtype_invalid",
        ):
            Intensity(
                values=torch.ones((4, 4), dtype=dtype),
                grid=_grid(),
                normalization=FieldNormalization.RELATIVE,
            )

    def test_intensity_rejects_invalid_grid_before_axis_lookup(self) -> None:
        """
        光强先确认网格类型，再读取 sample_counts
        """

        with pytest.raises(TypeError, match="intensity_grid_invalid"):
            Intensity(
                values=torch.ones((4, 4), dtype=torch.float64),
                grid=object(),  # type: ignore[arg-type]
                normalization=FieldNormalization.RELATIVE,
            )

    def test_detection_rejects_invalid_field_before_tensor_lookup(self) -> None:
        """
        探测计算入口先确认 OpticalField，再读取 envelope 与 Spectrum
        """

        with pytest.raises(
            TypeError,
            match="intensity_detection_field_invalid",
        ):
            IntensityDetection()(object())  # type: ignore[arg-type]


class TestIndependentReference:
    """
    证据层 2：独立解析参照
    """

    def test_detection_matches_analytic_reduction(self) -> None:
        """IntensityDetection 结果须与独立解析约减一致

        独立参照 deliberately 采用显式实/虚部平方、独立偏振求和与广播加权，与核
        的负索引路径区分，以交叉验证约减形式（提取自迁移源
        optics/evaluation/intensity.py 的 abs().square() 与偏振求和，并按光谱约减契约
        不变量补足光谱加权）。
        """
        torch.manual_seed(11)
        envelope = torch.randn((2, 3, 2, 4, 4), dtype=torch.complex128)
        weights = torch.tensor([0.2, 0.5, 0.3], dtype=torch.float64)
        field = _field(
            envelope,
            weights=weights,
            polarization=Polarization.transverse(),
        )
        intensity = IntensityDetection()(field)

        squared = envelope.real ** 2 + envelope.imag ** 2
        pol_reduced = squared.sum(dim=-3)
        weighted = (pol_reduced * weights.reshape(1, -1, 1, 1)).sum(dim=1)
        assert torch.allclose(intensity.values, weighted)
        assert intensity.batch_shape == (2,)
        assert intensity.spectral_reduction == "weighted_sum"
        assert intensity.axis_meaning == (
            "batch_0",
            "height",
            "width",
        )

    def test_power_reduction_preserves_each_batch_total_power(self) -> None:
        """
        多批量、多光谱、双偏振功率场经非均匀权重约减后逐批空间积分守恒
        """

        torch.manual_seed(23)
        envelope = torch.randn((2, 3, 2, 4, 4), dtype=torch.complex128)
        weights = torch.tensor([0.1, 0.3, 0.6], dtype=torch.float64)
        target_power = torch.tensor([2.0e-3, 5.0e-3], dtype=torch.float64)
        squared = envelope.real.square() + envelope.imag.square()
        weighted_density = (
            squared.sum(dim=-3) * weights.reshape(1, -1, 1, 1)
        ).sum(dim=1)
        current_power = weighted_density.sum(dim=(-2, -1)) * _grid().cell_area
        scale = torch.sqrt(target_power / current_power).reshape(2, 1, 1, 1, 1)
        normalized_envelope = envelope * scale
        field = _field(
            normalized_envelope,
            weights=weights,
            polarization=Polarization.transverse(),
            normalization=FieldNormalization.POWER,
        )

        intensity = IntensityDetection()(field)
        observed_power = (
            intensity.values.sum(dim=(-2, -1)) * intensity.grid.cell_area
        )

        assert torch.allclose(observed_power, target_power)
        assert intensity.units == "watts_per_square_metre"


class TestPolarizationComponentReduction:
    """
    探测以显式分量模方约减而非忽略偏振轴假设
    """

    def test_full_three_component_reduction_matches_dim_minus_three_sum(self) -> None:
        """
        完整三分量光场的强度约减等价于在偏振轴（dim=-3）上显式求和
        """
        torch.manual_seed(19)
        envelope = torch.randn((2, 3, 3, 4, 4), dtype=torch.complex128)
        weights = torch.tensor([0.2, 0.5, 0.3], dtype=torch.float64)
        field = _field(
            envelope,
            weights=weights,
            polarization=Polarization.full(),
        )

        intensity = IntensityDetection()(field)

        squared = envelope.real.square() + envelope.imag.square()
        expected = (squared.sum(dim=-3) * weights.reshape(1, -1, 1, 1)).sum(dim=1)
        assert torch.allclose(intensity.values, expected)
        assert intensity.batch_shape == (2,)

    def test_isolated_single_component_contributes_its_own_magnitude_squared(
        self,
    ) -> None:
        """
        单分量非零（Ex≠0、Ey=Ez=0）⇒ 强度恰为 |Ex|²；三分量等量 ⇒ 3|Ex|²
        """
        weights = torch.tensor([1.0], dtype=torch.float64)
        counts_y, counts_x = _grid().sample_counts
        generator = torch.Generator(device="cpu").manual_seed(5)
        ex = torch.complex(
            torch.randn(counts_y, counts_x, generator=generator, dtype=torch.float64),
            torch.randn(counts_y, counts_x, generator=generator, dtype=torch.float64),
        )
        zeros = torch.zeros_like(ex)
        full_only_x = torch.stack((ex, zeros, zeros)).unsqueeze(0)
        field_only_x = _field(
            full_only_x,
            weights=weights,
            polarization=Polarization.full(),
        )
        intensity_only_x = IntensityDetection()(field_only_x)
        expected_only_x = ex.real.square() + ex.imag.square()
        assert torch.allclose(intensity_only_x.values, expected_only_x)

        # 三分量等量 ⇒ 3|Ex|²（显式逐分量约减，不是把偏振轴当作不存在）
        full_equal = torch.stack((ex, ex, ex)).unsqueeze(0)
        field_equal = _field(
            full_equal,
            weights=weights,
            polarization=Polarization.full(),
        )
        intensity_equal = IntensityDetection()(field_equal)
        assert torch.allclose(intensity_equal.values, 3.0 * expected_only_x)


class TestGradientEvidence:
    """
    证据层 3：梯度证据
    """

    def test_gradcheck_on_trainable_amplitude(self) -> None:
        """对可训练实振幅经 IntensityDetection 的梯度做 gradcheck

        可训练振幅为 float64 叶子张量，经复数化与固定相幅相乘构造包络；整条链
        amp -> 复包络 -> |E|² -> 偏振/光谱约减 处处可微，解析梯度须与有限差分一致。
        """
        phasor = torch.randn((1, 1, 1, 4, 4), dtype=torch.complex128)
        weights = torch.ones(1, dtype=torch.float64)
        grid = _grid()
        spectrum = _spectrum(weights)
        detection = IntensityDetection()

        def detect(amplitude: torch.Tensor) -> torch.Tensor:
            """
            返回给定振幅下的光强值张量
            """
            envelope = torch.complex(
                amplitude,
                torch.zeros_like(amplitude),
            ) * phasor
            field = OpticalField(
                envelope=envelope,
                grid=grid,
                spectrum=spectrum,
                polarization_representation=(Polarization.scalar()).representation,
                medium=Vacuum(),
                normalization=FieldNormalization.RELATIVE,
                path_reference=OpticalPathReference(
                    lengths=(0.0,) * spectrum.count,
                ),
            )
            return detection(field).values

        amplitude = torch.randn(
            (1, 1, 1, 4, 4),
            dtype=torch.float64,
            requires_grad=True,
        )
        assert torch.autograd.gradcheck(detect, (amplitude,), raise_exception=True)

    def test_detection_has_no_trainable_parameters(self) -> None:
        """
        验证光强探测固定且仅对输入光场求导
        """

        assert tuple(IntensityDetection().parameters()) == ()


class TestHostedExecution:
    """
    托管执行验证
    """

    def test_hosted_detection_produces_correct_intensity(self) -> None:
        """
        断言托管后光强值为全 1 且归一化为功率

        使用固定双精度工作站托管 IntensityDetection，再直接调用一个功率光场，
        断言返回的 Intensity 为实数、非负且归一化语义与源光场一致。
        """
        workstation = Workstation.cpu()
        detection = IntensityDetection()
        hosted = workstation.host(detection)
        assert hosted is detection

        envelope = torch.ones((1, 1, 1, 4, 4), dtype=torch.complex128)
        field = _field(
            envelope,
            weights=torch.ones(1),
            normalization=FieldNormalization.POWER,
        )
        intensity = detection(field)
        assert isinstance(intensity, Intensity)
        assert intensity.normalization is FieldNormalization.POWER
        assert torch.allclose(
            intensity.values,
            torch.ones((1, 4, 4), dtype=torch.float64),
        )
        assert not torch.is_complex(intensity.values)


class TestZeroBatchField:
    """
    0 批量光场（CONTEXT Field Axes：batch... 可为零或更多）契约
    """

    def test_hosted_detection_accepts_zero_batch_field(self) -> None:
        """0 批量光场经托管 IntensityDetection 产生合法 (h,w) Intensity

        构造无批量维的 OpticalField（包络形状 (spectrum, polarization, height, width)，
        即 0 批量），在工作站上托管 IntensityDetection 后直接调用，断言返回的
        Intensity 为实数、非负、空间形状与网格一致，且 batch_shape 为空元组。
        Intensity 不得拒绝 0 批量光场。
        """
        workstation = Workstation.cpu()
        detection = workstation.host(IntensityDetection())

        envelope = torch.ones((2, 1, 4, 4), dtype=torch.complex128)
        spectrum = _spectrum(torch.tensor([0.4, 0.6]))
        field = OpticalField(
            envelope=envelope,
            grid=_grid(),
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(0.0,) * spectrum.count,
            ),
        )
        intensity = detection(field)

        assert isinstance(intensity, Intensity)
        assert not torch.is_complex(intensity.values)
        assert intensity.values.shape == (4, 4)
        assert intensity.batch_shape == ()
        assert torch.all(intensity.values >= 0)
        assert intensity.grid.is_physically_equivalent_to(field.grid)


class TestBatchedBatchShape:
    """
    批量维光场的 ``Intensity.batch_shape`` 回归（用户故事 #16）
    """

    def test_batched_field_intensity_carries_batch_shape(self) -> None:
        """批量光场经托管 IntensityDetection 后 batch_shape 保留批量维

        光强张量布局为 (批量..., 高度, 宽度)——仅两个空间尾轴，故批量部分为
        ``values.shape[:-2]``（与光场 envelope 的 ``shape[:-4]`` 剥离 S/P/H/W 相对应）。
        本回归覆盖 ``[:-3]`` off-by-one：错误切片会把批量维误剥为 ``shape[:-3]``，
        对 (2, H, W) 张量返回 ``()`` 而非 ``(2,)``。该边界由具名批量维度证据
        直接固定，不依赖唯一的
        ``batch_shape`` 断言使用 0 批量光场（``() == ()`` 平凡成立）。
        """
        workstation = Workstation.cpu()
        detection = workstation.host(IntensityDetection())

        envelope = torch.ones((2, 1, 1, 4, 4), dtype=torch.complex128)
        spectrum = _spectrum(torch.ones(1))
        field = OpticalField(
            envelope=envelope,
            grid=_grid(),
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(0.0,) * spectrum.count,
            ),
        )
        intensity = detection(field)

        assert isinstance(intensity, Intensity)
        # 空间尾轴恰好两条（高度、宽度）；批量维被保留
        assert intensity.values.shape == (2, 4, 4)
        # off-by-one ``[:-3]`` 在此会返回 ``()``；正确批量形状是 ``(2,)``
        assert intensity.batch_shape == (2,)


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_intensity_detection_public_action_matches_cpu_on_cuda() -> None:
    """
    IntensityDetection 公共动作在 CUDA 上保持与 CPU 相同的强度
    """

    weights = torch.tensor([0.4, 0.6], dtype=torch.float64)
    cpu_envelope = torch.tensor(
        [[[[1.0 + 0.5j] * 4] * 4], [[[0.25 - 0.75j] * 4] * 4]],
        dtype=torch.complex128,
    )
    cpu_field = _field(cpu_envelope, weights=weights)
    cuda_field = _field(cpu_envelope.cuda(), weights=weights)

    cpu_output = intensity_detection(cpu_field)
    cuda_output = intensity_detection(cuda_field)

    torch.testing.assert_close(cpu_output.values, cuda_output.values.cpu())

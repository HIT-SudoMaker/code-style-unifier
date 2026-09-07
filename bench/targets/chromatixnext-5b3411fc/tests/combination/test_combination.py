
from __future__ import annotations

import copy
import math

import pytest
import torch

from chromatix_next.errors import AssemblyError, OpticalTypeError
from chromatix_next.optics import (
    ConstantMedium,
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
from chromatix_next.optics.combination import (
    CoherentCombination,
    IntensityCombination,
    coherent_combination,
    intensity_combination,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import OpticalPathModulation
from chromatix_next.optics.intensity import Intensity
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation


def _grid(
    counts: tuple[int, int] = (5, 5),
    spacing: tuple[float, float] = (0.5e-6, 0.5e-6),
) -> SpatialGrid:
    # 中心对齐的横向网格
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    # 单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _field(
    grid: SpatialGrid,
    spectrum: Spectrum,
    *,
    amplitude: complex = 1.0 + 0.0j,
    medium: Vacuum | ConstantMedium | None = None,
    normalization: FieldNormalization = FieldNormalization.RELATIVE,
    polarization: Polarization | None = None,
    path_reference: OpticalPathReference | None = None,
    dtype: torch.dtype = torch.complex128,
    device: torch.device | str | None = None,
) -> OpticalField:
    # 构造可控包络的输入光场；偏振轴长度跟随偏振表示
    resolved_polarization = polarization or Polarization.scalar()
    counts_y, counts_x = grid.sample_counts
    envelope = torch.full(
        (
            spectrum.count,
            resolved_polarization.component_count,
            counts_y,
            counts_x,
        ),
        amplitude,
        dtype=dtype,
        device=device,
    )
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=spectrum,
        polarization_representation=(
            resolved_polarization
        ).representation,
        medium=medium if medium is not None else Vacuum(),
        normalization=normalization,
        path_reference=path_reference
        or OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


def _coherent_pair(field: OpticalField) -> tuple[OpticalField, OpticalField]:
    # 相干组合测试只需要同谱系的两路输入；方向性分束由其独立证据拥有
    return field, copy.copy(field)


class TestFunctionComponentDuality:
    """
    组合函数与组合组件共享同一物理计算
    """

    def test_real_calls_preserve_values_and_gradients(self) -> None:
        """
        两种公开形态在真实张量上给出相同结果并保留两路输入梯度
        """
        grid = _grid()
        spectrum = _monochromatic()
        envelope = torch.full(
            (1, 1, *grid.sample_counts),
            complex(0.75, 0.25),
            dtype=torch.complex128,
            requires_grad=True,
        )
        field = OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        field_1, field_2 = _coherent_pair(field)

        functional_field = coherent_combination(field_1, field_2)
        component_field = CoherentCombination()(field_1, field_2)

        assert torch.equal(
            functional_field.envelope,
            component_field.envelope,
        )
        functional_gradients = torch.autograd.grad(
            functional_field.envelope.abs().square().sum(),
            (field_1.envelope, field_2.envelope),
            retain_graph=True,
        )
        component_gradients = torch.autograd.grad(
            component_field.envelope.abs().square().sum(),
            (field_1.envelope, field_2.envelope),
        )
        assert torch.equal(functional_gradients[0], component_gradients[0])
        assert torch.equal(functional_gradients[1], component_gradients[1])

        values_1 = torch.full(
            grid.sample_counts,
            0.25,
            dtype=torch.float64,
            requires_grad=True,
        )
        values_2 = torch.full(
            grid.sample_counts,
            0.75,
            dtype=torch.float64,
            requires_grad=True,
        )
        intensity_1 = Intensity(
            values=values_1,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        intensity_2 = Intensity(
            values=values_2,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )

        functional_intensity = intensity_combination(
            intensity_1,
            intensity_2,
        )
        component_intensity = IntensityCombination()(
            intensity_1,
            intensity_2,
        )

        assert torch.equal(
            functional_intensity.values,
            component_intensity.values,
        )
        functional_gradients = torch.autograd.grad(
            functional_intensity.values.sum(),
            (values_1, values_2),
            retain_graph=True,
        )
        component_gradients = torch.autograd.grad(
            component_intensity.values.sum(),
            (values_1, values_2),
        )
        assert torch.equal(functional_gradients[0], component_gradients[0])
        assert torch.equal(functional_gradients[1], component_gradients[1])

    def test_meta_calls_preserve_shape_and_dtype(self) -> None:
        """
        两种公开形态在 meta 推导中给出相同的形状与精度
        """
        grid = _grid()
        spectrum = _monochromatic()
        meta_envelope = torch.empty(
            (1, 1, *grid.sample_counts),
            dtype=torch.complex128,
            device="meta",
        )
        field = OpticalField(
            envelope=meta_envelope,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        field_1, field_2 = _coherent_pair(field)

        functional_field = coherent_combination(field_1, field_2)
        component_field = CoherentCombination()(field_1, field_2)

        assert functional_field.envelope.is_meta
        assert functional_field.envelope.shape == component_field.envelope.shape
        assert functional_field.envelope.dtype == component_field.envelope.dtype

        meta_values = torch.empty(
            grid.sample_counts,
            dtype=torch.float64,
            device="meta",
        )
        intensity_1 = Intensity(
            values=meta_values,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        intensity_2 = Intensity(
            values=meta_values.clone(),
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )

        functional_intensity = intensity_combination(
            intensity_1,
            intensity_2,
        )
        component_intensity = IntensityCombination()(
            intensity_1,
            intensity_2,
        )

        assert functional_intensity.values.is_meta
        assert (
            functional_intensity.values.shape
            == component_intensity.values.shape
        )
        assert (
            functional_intensity.values.dtype
            == component_intensity.values.dtype
        )


class TestCoherentCombinationPhysicalInvariants:
    """
    证据层 1（相干组合）：物理不变量
    """

    def test_adds_envelopes_and_inherits_first_input(self) -> None:
        """相干输出包络 = E_a + E_b，并继承第一输入的全部物理轮廓与光程参考
        """
        grid = _grid()
        spectrum = _monochromatic()
        field_a, field_b = _coherent_pair(
            _field(grid, spectrum, amplitude=complex(1.0, 0.0))
        )
        combiner = CoherentCombination()
        output = combiner(field_a, field_b)
        expected = field_a.envelope + field_b.envelope
        assert torch.allclose(output.envelope, expected, atol=1e-12)
        # 继承第一输入物理身份
        assert output.grid is field_a.grid
        assert output.spectrum is field_a.spectrum
        assert (
            output.polarization_representation
            is field_a.polarization_representation
        )
        assert output.medium is field_a.medium
        assert output.normalization is field_a.normalization
        assert output.path_reference == field_a.path_reference

    def test_batched_inputs_add_per_batch(self) -> None:
        """批量轴保留：逐批量相干相加
        """
        grid = _grid()
        spectrum = _monochromatic()
        batched_shape = (2, spectrum.count, 1, 5, 5)
        envelope_a = torch.complex(
            torch.randn(batched_shape, dtype=torch.float64),
            torch.randn(batched_shape, dtype=torch.float64),
        )
        input_field = OpticalField(
            envelope=envelope_a,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(0.0,) * spectrum.count,
            ),
        )
        field_a, field_b = _coherent_pair(input_field)
        output = CoherentCombination()(field_a, field_b)
        assert output.envelope.shape == (2, spectrum.count, 1, 5, 5)
        expected = field_a.envelope + field_b.envelope
        assert torch.allclose(output.envelope, expected, atol=1e-12)

    def test_unequal_references_contribute_relative_carrier(self) -> None:
        """
        同源四分之一波长光程差以相对载波进入相干和
        """

        grid = _grid()
        wavelength = 2.0e-6
        spectrum = _monochromatic(wavelength)
        field_1, field_2 = _coherent_pair(_field(grid, spectrum))
        delayed_field_2 = OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.zeros(
                grid.sample_counts,
                dtype=torch.float64,
            ),
            optical_path_baseline=wavelength / 4.0,
        )(field_2)
        output = CoherentCombination()(field_1, delayed_field_2)
        expected = field_1.envelope + 1.0j * delayed_field_2.envelope
        assert torch.allclose(output.envelope, expected, atol=1e-12)
        assert output.path_reference == field_1.path_reference

    def test_multispectral_reference_alignment_is_wavelength_specific(
        self,
    ) -> None:
        """
        同一均匀光程差按各波长产生不同相对载波
        """

        grid = _grid()
        spectrum = Spectrum(
            wavelengths=(2.0e-6, 4.0e-6),
            weights=(0.5, 0.5),
        )
        field_1, field_2 = _coherent_pair(_field(grid, spectrum))
        delayed_field_2 = OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.zeros(
                grid.sample_counts,
                dtype=torch.float64,
            ),
            optical_path_baseline=1.0e-6,
        )(field_2)
        output = CoherentCombination()(field_1, delayed_field_2)
        relative_carrier = torch.tensor(
            [-1.0 + 0.0j, 0.0 + 1.0j],
            dtype=torch.complex128,
        ).reshape(2, 1, 1, 1)
        expected = (
            field_1.envelope
            + relative_carrier * delayed_field_2.envelope
        )
        assert torch.allclose(output.envelope, expected, atol=1e-12)

    def test_swapped_input_reference_preserves_reconstructed_field(
        self,
    ) -> None:
        """
        交换有序输入只改变输出参考表达，不改变重建后的物理场
        """

        grid = _grid()
        wavelength = 2.0e-6
        spectrum = _monochromatic(wavelength)
        field_1, field_2 = _coherent_pair(_field(grid, spectrum))
        delayed_field_2 = OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.zeros(
                grid.sample_counts,
                dtype=torch.float64,
            ),
            optical_path_baseline=wavelength / 4.0,
        )(field_2)
        output_12 = CoherentCombination()(field_1, delayed_field_2)
        output_21 = CoherentCombination()(delayed_field_2, field_1)

        assert output_12.path_reference == field_1.path_reference
        assert output_21.path_reference == delayed_field_2.path_reference
        assert torch.allclose(
            output_12.envelope,
            1.0j * output_21.envelope,
            atol=1e-12,
        )

class TestCoherentCombinationAdmission:
    """
    证据层 1（相干组合）：八维相干兼容性，每维不匹配 ⇒ AssemblyError（稳定身份）

    固定双精度下精度维度不再可失配（所有场一律 complex128），故兼容维度由九减为八。
    """

    @pytest.mark.parametrize(
        "dimension",
        [
            "frequency",
            "spectral_weight",
            "polarization",
            "medium",
            "grid",
            "normalization",
            "axis",
            "lineage",
        ],
    )
    def test_mismatch_raises_assembly_error(self, dimension: str) -> None:
        """每一相干维度的失配须以稳定身份抛出 AssemblyError（物理读序）
        """
        grid = _grid()
        spectrum = _monochromatic()
        field_a = _field(grid, spectrum)
        field_b = self._perturb(field_a, grid, spectrum, dimension)
        combiner = CoherentCombination()
        with pytest.raises(AssemblyError) as information:
            combiner(field_a, field_b)
        # 稳定身份按物理读序纳入消息
        assert dimension in str(information.value)

    def test_representation_and_source_lineage_mismatches_share_ordered_error(
        self,
    ) -> None:
        """
        独立且表征不同的两路源场按物理读序报告两类不相容
        """
        grid = _grid()
        scalar_field = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )(grid)
        transverse_field = PlaneWave(
            spectrum=_monochromatic(),
            polarization=Polarization.transverse(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=1.0,
        )(grid)

        with pytest.raises(AssemblyError) as information:
            coherent_combination(scalar_field, transverse_field)

        assert information.value.identity == (
            "coherent_combination_polarization_mismatch; "
            "coherent_combination_axis_mismatch; "
            "coherent_combination_source_lineage_mismatch"
        )

    @staticmethod
    def _perturb(
        field_a: OpticalField,
        grid: SpatialGrid,
        spectrum: Spectrum,
        dimension: str,
    ) -> OpticalField:
        # 对指定维度构造一个失配的第二输入，其余维度与第一输入一致
        if dimension == "frequency":
            other_spectrum = Spectrum.monochromatic(wavelength=2.1e-6)
            return _field(grid, other_spectrum, amplitude=complex(1.0, 0.0))
        if dimension == "spectral_weight":
            other_spectrum = Spectrum(
                wavelengths=spectrum.wavelengths,
                weights=(0.5,),
            )
            return _field(grid, other_spectrum, amplitude=complex(1.0, 0.0))
        if dimension == "polarization":
            # 构造合法的横向偏振场（包络偏振轴=2，与表示一致）；与标量输入偏振表示不同
            counts_y, counts_x = grid.sample_counts
            envelope = torch.full(
                (spectrum.count, 2, counts_y, counts_x),
                complex(1.0, 0.0),
                dtype=torch.complex128,
            )
            return OpticalField(
                envelope=envelope,
                grid=grid,
                spectrum=spectrum,
                polarization_representation=(Polarization.transverse()).representation,
                medium=Vacuum(),
                normalization=FieldNormalization.RELATIVE,
                path_reference=field_a.path_reference,
            )
        if dimension == "medium":
            return _field(
                grid,
                spectrum,
                amplitude=complex(1.0, 0.0),
                medium=ConstantMedium(index=1.5),
            )
        if dimension == "grid":
            other_grid = SpatialGrid.centered(
                sample_counts=(5, 5),
                sample_spacing=(0.4e-6, 0.4e-6),
            )
            return _field(other_grid, spectrum, amplitude=complex(1.0, 0.0))
        if dimension == "normalization":
            return _field(
                grid,
                spectrum,
                amplitude=complex(1.0, 0.0),
                normalization=FieldNormalization.POWER,
            )
        if dimension == "axis":
            # 批量轴长度不同（第二输入多一个批量项）
            counts_y, counts_x = grid.sample_counts
            envelope = torch.full(
                (2, spectrum.count, 1, counts_y, counts_x),
                complex(1.0, 0.0),
                dtype=torch.complex128,
            )
            return OpticalField(
                envelope=envelope,
                grid=grid,
                spectrum=spectrum,
                polarization_representation=(Polarization.scalar()).representation,
                medium=Vacuum(),
                normalization=FieldNormalization.RELATIVE,
                path_reference=field_a.path_reference,
            )
        if dimension == "lineage":
            return _field(
                grid,
                spectrum,
                amplitude=complex(1.0, 0.0),
                path_reference=OpticalPathReference(
                    lengths=(1.5,) * spectrum.count,
                ),
            )
        error_identity = "unknown_perturb_dimension"
        raise AssertionError(error_identity)

    def test_incompatible_inputs_raise_single_ordered_error(self) -> None:
        """多个失配项须在一次 AssemblyError 中按物理读序列出
        """
        grid = _grid()
        spectrum = _monochromatic()
        field_a = _field(grid, spectrum)
        # 同时扰动频率、偏振（含轴）、归一化三个维度
        counts_y, counts_x = grid.sample_counts
        envelope_b = torch.full(
            (spectrum.count, 2, counts_y, counts_x),
            complex(1.0, 0.0),
            dtype=torch.complex128,
        )
        field_b = OpticalField(
            envelope=envelope_b,
            grid=grid,
            spectrum=Spectrum.monochromatic(wavelength=2.1e-6),
            polarization_representation=(Polarization.transverse()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.POWER,
            path_reference=OpticalPathReference(
                lengths=(0.5e-6,) * spectrum.count,
            ),
        )
        with pytest.raises(AssemblyError) as information:
            CoherentCombination()(field_a, field_b)
        message = str(information.value)
        # 物理读序：频率先于偏振，偏振先于归一化
        position_frequency = message.find("frequency")
        position_polarization = message.find("polarization")
        position_normalization = message.find("normalization")
        assert position_frequency != -1
        assert position_polarization != -1
        assert position_normalization != -1
        assert position_frequency < position_polarization < position_normalization
        assert "光程参考可以不同" in information.value.explanation
        assert "光程参考上全部一致" not in information.value.explanation

    def test_device_finding_follows_physical_findings_before_arithmetic(
        self,
    ) -> None:
        """
        设备失配在张量算术前失败并排在物理相干发现之后
        """

        grid = _grid()
        spectrum = _monochromatic()
        field_1 = _field(grid, spectrum)
        field_2 = copy.copy(field_1)
        object.__setattr__(field_2, "envelope", field_2.envelope.to("meta"))
        object.__setattr__(field_2, "_source_lineage", object())
        with pytest.raises(AssemblyError) as information:
            coherent_combination(field_1, field_2)
        assert information.value.identity == (
            "coherent_combination_source_lineage_mismatch; "
            "coherent_combination_device_mismatch"
        )


class TestCoherentCombinationIndependentReference:
    """
    证据层 2（相干组合）：独立参照（独立包络加法）
    """

    def test_coherent_sum_matches_analytic_envelope_addition(self) -> None:
        """相干和须与独立构造的解析包络加法逐元素一致
        """
        grid = _grid()
        spectrum = _monochromatic()
        counts_y, counts_x = grid.sample_counts
        field_shape = (spectrum.count, 1, counts_y, counts_x)
        envelope_a = torch.complex(
            torch.randn(field_shape, dtype=torch.float64),
            torch.randn(field_shape, dtype=torch.float64),
        )
        input_field = OpticalField(
            envelope=envelope_a,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(0.0,) * spectrum.count,
            ),
        )
        field_a, field_b = _coherent_pair(input_field)
        output = CoherentCombination()(field_a, field_b)
        # 独立解析参照：逐元素复包络加法
        assert torch.allclose(
            output.envelope,
            field_a.envelope + field_b.envelope,
            atol=1e-12,
        )


class TestCoherentCombinationGradientEvidence:
    """
    证据层 3（相干组合）：梯度证据

    规约"组件证据"：梯度证据针对**每可训练声明**。``CoherentCombination`` 无可训练
    Parameter（纯包络加法，无相对相位自由度），故该层为空。以断言空 Parameter 集合
    诚实记录该决断。
    """

    def test_coherent_combination_has_no_trainable_parameters(self) -> None:
        """相干组合无可训练 Parameter
        """
        combiner = CoherentCombination()
        assert list(combiner.parameters()) == []

    def test_input_gradient_reaches_unequal_reference_branches(self) -> None:
        """
        验证参考对齐在固定双精度下不截断任一复光场输入
        """

        grid = _grid()
        spectrum = _monochromatic()
        envelope = torch.full(
            (1, 1, *grid.sample_counts),
            complex(1.0, 0.5),
            dtype=torch.complex128,
            requires_grad=True,
        )
        field = OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        field_1, field_2 = _coherent_pair(field)
        field_2 = OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.zeros(
                grid.sample_counts,
                dtype=torch.float64,
            ),
            optical_path_baseline=spectrum.wavelengths[0] / 5.0,
        )(field_2)
        field_1.envelope.retain_grad()
        field_2.envelope.retain_grad()
        output = CoherentCombination()(field_1, field_2)
        output.envelope.abs().square().sum().backward()
        assert field_1.envelope.grad is not None
        assert field_2.envelope.grad is not None
        assert torch.count_nonzero(field_1.envelope.grad) > 0
        assert torch.count_nonzero(field_2.envelope.grad) > 0


class TestIntensityCombinationPhysicalInvariants:
    """
    证据层 1（光强组合）：物理不变量
    """

    def test_adds_intensities_and_inherits_first_input(self) -> None:
        """非相干输出 = I_a + I_b（实数非负），继承第一输入网格与归一化
        """
        grid = _grid()
        values_a = torch.full((5, 5), 0.3, dtype=torch.float64)
        values_b = torch.full((5, 5), 0.7, dtype=torch.float64)
        intensity_a = Intensity(
            values=values_a,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        intensity_b = Intensity(
            values=values_b,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        combiner = IntensityCombination()
        output = combiner(intensity_a, intensity_b)
        assert torch.allclose(output.values, values_a + values_b, atol=1e-12)
        assert output.grid is intensity_a.grid
        assert output.normalization is intensity_a.normalization

    def test_output_is_real_and_nonnegative(self) -> None:
        """非相干输出为实数且非负（绝不发明复包络或相位）
        """
        grid = _grid()
        values_a = torch.rand(5, 5, dtype=torch.float64)
        values_b = torch.rand(5, 5, dtype=torch.float64)
        intensity_a = Intensity(
            values=values_a,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        intensity_b = Intensity(
            values=values_b,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        output = IntensityCombination()(intensity_a, intensity_b)
        assert not torch.is_complex(output.values)
        assert torch.all(output.values >= 0)

    def test_never_introduces_relative_phase(self) -> None:
        """光强组合不发明相对相位：两路单位光强 ⇒ 输出恰为 2（非 4）
        """
        # 相干同相叠加会给出 (|E|+|E|)² = 4；非相干给出 |E|²+|E|² = 2。本件须给 2
        grid = _grid()
        unit_a = torch.ones(5, 5, dtype=torch.float64)
        unit_b = torch.ones(5, 5, dtype=torch.float64)
        intensity_a = Intensity(
            values=unit_a,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        intensity_b = Intensity(
            values=unit_b,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        output = IntensityCombination()(intensity_a, intensity_b)
        assert torch.allclose(
            output.values,
            torch.full((5, 5), 2.0, dtype=torch.float64),
            atol=1e-12,
        )

class TestIntensityCombinationAdmission:
    """
    证据层 1（光强组合）：光强域兼容性，不匹配 ⇒ AssemblyError
    """

    @pytest.mark.parametrize("dimension", ["grid", "normalization", "axis"])
    def test_mismatch_raises_assembly_error(self, dimension: str) -> None:
        """光强域每一兼容维度的失配须以稳定身份抛出 AssemblyError
        """
        grid = _grid()
        intensity_a = Intensity(
            values=torch.full((5, 5), 0.4, dtype=torch.float64),
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        if dimension == "grid":
            other_grid = SpatialGrid.centered(
                sample_counts=(5, 5),
                sample_spacing=(0.4e-6, 0.4e-6),
            )
            intensity_b = Intensity(
                values=torch.full((5, 5), 0.4, dtype=torch.float64),
                grid=other_grid,
                normalization=FieldNormalization.RELATIVE,
            )
        elif dimension == "normalization":
            intensity_b = Intensity(
                values=torch.full((5, 5), 0.4, dtype=torch.float64),
                grid=grid,
                normalization=FieldNormalization.POWER,
            )
        else:
            intensity_b = Intensity(
                values=torch.full((2, 5, 5), 0.4, dtype=torch.float64),
                grid=grid,
                normalization=FieldNormalization.RELATIVE,
            )
        with pytest.raises(AssemblyError) as information:
            IntensityCombination()(intensity_a, intensity_b)
        assert dimension in str(information.value)

    def test_invalid_input_positions_keep_stable_identities(self) -> None:
        """
        两路类型错误分别使用与物理输入位置一致的稳定身份
        """

        intensity = Intensity(
            values=torch.ones((5, 5), dtype=torch.float64),
            grid=_grid(),
            normalization=FieldNormalization.POWER,
        )
        with pytest.raises(OpticalTypeError) as first_information:
            intensity_combination(object(), intensity)  # type: ignore[arg-type]
        with pytest.raises(OpticalTypeError) as second_information:
            intensity_combination(intensity, object())  # type: ignore[arg-type]
        assert first_information.value.identity == (
            "intensity_combination_intensity_1_invalid"
        )
        assert second_information.value.identity == (
            "intensity_combination_intensity_2_invalid"
        )

    def test_findings_follow_grid_normalization_axis_device_order(self) -> None:
        """
        多项光强失配按网格、归一化、轴与设备顺序聚合
        """

        intensity_1 = Intensity(
            values=torch.ones((5, 5), dtype=torch.float64),
            grid=_grid(),
            normalization=FieldNormalization.POWER,
        )
        second_grid = SpatialGrid.centered(
            sample_counts=(2, 5),
            sample_spacing=(1.5e-6, 2.0e-6),
        )
        intensity_2 = Intensity(
            values=torch.ones((2, 5), dtype=torch.float64, device="meta"),
            grid=second_grid,
            normalization=FieldNormalization.RELATIVE,
        )
        with pytest.raises(AssemblyError) as information:
            IntensityCombination()(intensity_1, intensity_2)
        assert information.value.identity == (
            "intensity_combination_grid_mismatch; "
            "intensity_combination_normalization_mismatch; "
            "intensity_combination_axis_mismatch; "
            "intensity_combination_device_mismatch"
        )


class TestIntensityCombinationIndependentReference:
    """
    证据层 2（光强组合）：独立参照（独立光强加法）
    """

    def test_intensity_sum_matches_analytic_addition(self) -> None:
        """光强和须与独立构造的解析光强加法逐元素一致
        """
        grid = _grid()
        values_a = torch.rand(5, 5, dtype=torch.float64) * 0.5
        values_b = torch.rand(5, 5, dtype=torch.float64) * 0.5
        intensity_a = Intensity(
            values=values_a,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        intensity_b = Intensity(
            values=values_b,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        output = IntensityCombination()(intensity_a, intensity_b)
        assert torch.allclose(output.values, values_a + values_b, atol=1e-12)


class TestIntensityCombinationGradientEvidence:
    """
    证据层 3（光强组合）：梯度证据

    ``IntensityCombination`` 无可训练 Parameter（纯光强加法），故该层为空。
    """

    def test_intensity_combination_has_no_trainable_parameters(self) -> None:
        """光强组合无可训练 Parameter
        """
        assert list(IntensityCombination().parameters()) == []

    def test_input_gradient_reaches_both_intensity_inputs(self) -> None:
        """
        验证固定非相干求和保留两个光强导数
        """

        grid = _grid()
        values_1 = torch.full(
            grid.sample_counts,
            0.3,
            dtype=torch.float64,
            requires_grad=True,
        )
        values_2 = torch.full(
            grid.sample_counts,
            0.7,
            dtype=torch.float64,
            requires_grad=True,
        )
        intensity_1 = Intensity(
            values=values_1,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        intensity_2 = Intensity(
            values=values_2,
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        output = IntensityCombination()(intensity_1, intensity_2)
        output.values.sum().backward()
        assert values_1.grad is not None
        assert values_2.grad is not None
        assert torch.allclose(values_1.grad, torch.ones_like(values_1))
        assert torch.allclose(values_2.grad, torch.ones_like(values_2))


class TestHostedIntensityCombination:
    """
    托管端到端：两路平面波经 IntensityDetection 探测后由 IntensityCombination 相加

        两个独立（不同谱系/相位）的单位平面波各自探测为光强 1；光强组合给出 2，
        而非相干同相叠加的 4。这区别于相干组合，验证光强域加法。
    """

    def test_two_independent_plane_waves_intensity_sum(self) -> None:
        """两路独立单位平面波 ⇒ 非相干光强和处处为 2
        """
        grid = _grid()
        spectrum = _monochromatic()
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
        detection = workstation.host(IntensityDetection())
        intensity_combiner = workstation.host(IntensityCombination())
        field = source(grid)
        intensity_a = detection(field)
        intensity_b = detection(field)
        combined = intensity_combiner(intensity_a, intensity_b)
        expected = torch.full((5, 5), 2.0, dtype=torch.float64)
        assert torch.allclose(combined.values, expected, atol=1e-12)


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is unavailable",
)
class TestCombinationCudaConsistency:
    """
    相干包络与非相干光强组合在 CUDA 上保持 CPU 参考结果
    """

    def test_coherent_and_intensity_sums_match_cpu(self) -> None:
        """
        两种组合在固定双精度下保持 CPU/CUDA 数值一致
        """

        grid = _grid()
        spectrum = _monochromatic()
        cpu_field = _field(
            grid,
            spectrum,
            amplitude=complex(0.75, 0.25),
        )
        cuda_field = _field(
            grid,
            spectrum,
            amplitude=complex(0.75, 0.25),
            device="cuda:0",
        )
        cpu_branches = _coherent_pair(cpu_field)
        cuda_branches = _coherent_pair(cuda_field)
        cpu_coherent = CoherentCombination()(*cpu_branches)
        cuda_coherent = CoherentCombination()(*cuda_branches)
        cpu_intensity_1 = Intensity(
            values=torch.full(
                grid.sample_counts,
                0.25,
                dtype=torch.float64,
            ),
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        cpu_intensity_2 = Intensity(
            values=torch.full(
                grid.sample_counts,
                0.75,
                dtype=torch.float64,
            ),
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        cuda_intensity_1 = Intensity(
            values=cpu_intensity_1.values.cuda(),
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        cuda_intensity_2 = Intensity(
            values=cpu_intensity_2.values.cuda(),
            grid=grid,
            normalization=FieldNormalization.RELATIVE,
        )
        cpu_intensity = IntensityCombination()(
            cpu_intensity_1,
            cpu_intensity_2,
        )
        cuda_intensity = IntensityCombination()(
            cuda_intensity_1,
            cuda_intensity_2,
        )

        tolerance = 1e-12
        assert torch.allclose(
            cpu_coherent.envelope,
            cuda_coherent.envelope.cpu(),
            atol=tolerance,
            rtol=tolerance,
        )
        assert torch.allclose(
            cpu_intensity.values,
            cuda_intensity.values.cpu(),
            atol=tolerance,
            rtol=tolerance,
        )


class TestCoherentCombinationPolarizationMixing:
    """
    相干组合在横向与完整表示上逐分量混合，相对载波同时作用于每个分量，
    输出帧继承第一输入。
    """

    @pytest.mark.parametrize(
        ("representation", "component_count"),
        (
            (PolarizationRepresentation.TRANSVERSE, 2),
            (PolarizationRepresentation.FULL, 3),
        ),
        ids=["transverse", "full"],
    )
    def test_same_reference_mixes_each_component_by_addition(
        self,
        representation: PolarizationRepresentation,
        component_count: int,
    ) -> None:
        """
        同光程参考下逐分量相干叠加：Ex=Ex1+Ex2、Ey=Ey1+Ey2（、Ez=Ez1+Ez2）
        """
        grid = _grid()
        spectrum = _monochromatic()
        counts_y, counts_x = grid.sample_counts
        shape = (spectrum.count, component_count, counts_y, counts_x)
        generator = torch.Generator(device="cpu").manual_seed(11)
        envelope = torch.complex(
            torch.randn(shape, generator=generator, dtype=torch.float64),
            torch.randn(shape, generator=generator, dtype=torch.float64),
        )
        input_field = OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(0.0,) * spectrum.count,
            ),
        )
        field_1, field_2 = _coherent_pair(input_field)

        output = CoherentCombination()(field_1, field_2)

        assert output.polarization_representation is representation
        # 帧继承第一输入
        assert output.path_reference == field_1.path_reference
        assert output.grid is field_1.grid
        # 同参考 ⇒ 纯逐分量包络加法
        assert torch.allclose(
            output.envelope,
            field_1.envelope + field_2.envelope,
            atol=1e-12,
        )

    @pytest.mark.parametrize(
        "representation",
        (
            PolarizationRepresentation.TRANSVERSE,
            PolarizationRepresentation.FULL,
        ),
        ids=["transverse", "full"],
    )
    def test_relative_carrier_applies_identically_to_every_component(
        self,
        representation: PolarizationRepresentation,
    ) -> None:
        """
        不同光程参考下，相对载波同时且相同地作用于每个分量

        证据独立于载波公式：由每个分量反推的载波 (out_c - in1_c) / in2_c 在全部分量
        上逐元素相等，证明同一载波施加于每个偏振分量。第二输入的光程参考以零空间
        变化的均匀基线推进，包络不变，故除法良态。
        """
        grid = _grid()
        spectrum = _monochromatic()
        component_count = representation.component_count
        counts_y, counts_x = grid.sample_counts
        shape = (spectrum.count, component_count, counts_y, counts_x)
        generator = torch.Generator(device="cpu").manual_seed(23)
        envelope = torch.complex(
            torch.randn(shape, generator=generator, dtype=torch.float64),
            torch.randn(shape, generator=generator, dtype=torch.float64),
        )
        input_field = OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=spectrum,
            polarization_representation=representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(0.0,) * spectrum.count,
            ),
        )
        field_1, field_2 = _coherent_pair(input_field)
        # 零空间变化 ⇒ 包络不变；均匀基线只推进第二路的光程参考
        field_2 = OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.zeros(
                grid.sample_counts,
                dtype=torch.float64,
            ),
            optical_path_baseline=spectrum.wavelengths[0] / 5.0,
        )(field_2)

        output = CoherentCombination()(field_1, field_2)

        assert output.polarization_representation is representation
        assert output.path_reference == field_1.path_reference
        # 由每个分量反推的载波须在全部分量上相同（field_2 各点非零）
        carriers = []
        for index in range(component_count):
            component_out = output.envelope[:, index]
            component_1 = field_1.envelope[:, index]
            component_2 = field_2.envelope[:, index]
            carrier = (component_out - component_1) / component_2
            carriers.append(carrier)
        reference_carrier = carriers[0]
        for carrier in carriers[1:]:
            assert torch.allclose(carrier, reference_carrier, atol=1e-12)
        # 载波是逐光谱标量（在每个分量、每个空间点上同值），幅度为 1（纯相位对齐）
        assert torch.allclose(
            reference_carrier.abs(),
            torch.ones_like(reference_carrier.abs()),
            atol=1e-12,
        )

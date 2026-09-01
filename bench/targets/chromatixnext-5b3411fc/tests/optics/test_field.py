
from __future__ import annotations

from dataclasses import fields, is_dataclass
import math

import pytest
import torch

from chromatix_next.errors import OpticalValueError
import chromatix_next.optics as optics_module
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


def _scalar_grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(0.5e-6, 0.5e-6),
    )


def _monochromatic_spectrum() -> Spectrum:
    return Spectrum.monochromatic(wavelength=488.0e-6)


def _zero_reference(spectrum: Spectrum) -> OpticalPathReference:
    return OpticalPathReference(lengths=(0.0,) * spectrum.count)


def _make_field(
    *,
    normalization: FieldNormalization = FieldNormalization.RELATIVE,
    envelope: torch.Tensor | None = None,
) -> OpticalField:
    if envelope is None:
        envelope = torch.ones((1, 1, 4, 4), dtype=torch.complex128)
    spectrum = _monochromatic_spectrum()
    return OpticalField(
        envelope=envelope,
        grid=_scalar_grid(),
        spectrum=spectrum,
        polarization_representation=(Polarization.scalar()).representation,
        medium=Vacuum(),
        normalization=normalization,
        path_reference=_zero_reference(spectrum),
    )


class _TensorSlotMediumBase(Medium):
    __slots__ = ("refractive_indices",)

    def __init__(self) -> None:
        """
        把隐藏 Tensor 写入基类声明的 slot
        """

        self.refractive_indices = torch.tensor([1.0, 1.5])

    def _evaluate_refractive_index(
        self,
        wavelengths: torch.Tensor,
    ) -> torch.Tensor:
        # 返回同形占位折射率
        return torch.ones_like(wavelengths)

    def _physical_identity(self) -> tuple[object, ...]:
        return ("tensor_slot",)


class TestOpticalPathReference:
    """
    逐光谱光程参考强值契约
    """

    def test_lengths_are_nonempty_finite_real_and_immutable(self) -> None:
        """
        强值只承载非空有限实数长度元组，不接受裸标量或张量状态
        """
        reference_type = getattr(optics_module, "OpticalPathReference")
        reference = reference_type(lengths=(0.0, 1.5e-6))
        assert reference.lengths == (0.0, 1.5e-6)
        with pytest.raises(AttributeError):
            reference.lengths = (0.0,)  # type: ignore[misc]
        for invalid in ((), (float("nan"),), torch.tensor([0.0])):
            with pytest.raises((TypeError, ValueError)):
                reference_type(lengths=invalid)

    def test_float32_tensor_lengths_rejected_at_owner(self) -> None:
        """
        float32 张量长度直接被 owner 拒绝

        固定双精度核要求 owner **显式拒绝**非 float64 张量，不允许静默升精度。
        f64-trainable
        的图保留证据由下个用例覆盖。
        """
        f32_source = torch.tensor(
            0.25,
            dtype=torch.float32,
            requires_grad=True,
        )
        with pytest.raises(
            TypeError,
            match="optical_path_reference_lengths_invalid",
        ):
            OpticalPathReference(lengths=(f32_source,))

        non_trainable_f32 = torch.tensor(0.25, dtype=torch.float32)
        with pytest.raises(
            TypeError,
            match="optical_path_reference_lengths_invalid",
        ):
            OpticalPathReference(lengths=(non_trainable_f32,))

        meta_f32 = torch.empty(
            (),
            device="meta",
            dtype=torch.float32,
            requires_grad=True,
        )
        with pytest.raises(
            TypeError,
            match="optical_path_reference_lengths_invalid",
        ):
            OpticalPathReference(lengths=(meta_f32,))

    def test_float64_trainable_tensor_lengths_keep_graph(self) -> None:
        """
        trainable **float64** 长度保留计算图

        f32 被拒绝后，可训练的 f64 张量仍证明梯度通路完整，下游
        OpticalField/组合件经此传播。这是 OpticalPathReference 契约
        "fp64 graph-bearing lengths" 的真实含义——长度本身是 fp64 且可训练。
        """
        source = torch.tensor(
            0.25,
            dtype=torch.float64,
            requires_grad=True,
        )
        reference = OpticalPathReference(lengths=(source,))
        length = reference.lengths[0]
        assert isinstance(length, torch.Tensor)
        assert length.device == source.device
        assert length.dtype is torch.float64
        assert length.requires_grad

        (3.0 * length).backward()
        assert source.grad is not None
        torch.testing.assert_close(
            source.grad,
            torch.tensor(3.0, dtype=torch.float64),
        )

        meta_f64 = torch.empty(
            (),
            device="meta",
            dtype=torch.float64,
            requires_grad=True,
        )
        meta_length = OpticalPathReference(
            lengths=(meta_f64,),
        ).lengths[0]
        assert isinstance(meta_length, torch.Tensor)
        assert meta_length.device.type == "meta"
        assert meta_length.dtype is torch.float64
        assert meta_length.requires_grad

    def test_field_requires_spectrum_length_match(self) -> None:
        """
        光场拒绝光程分量数和 Spectrum 不匹配
        """
        reference_type = getattr(optics_module, "OpticalPathReference")
        spectrum = _monochromatic_spectrum()
        wrong_reference = reference_type(lengths=(0.0, 0.0))
        with pytest.raises(
            ValueError,
            match="optical_field_path_reference_spectrum_mismatch",
        ):
            OpticalField(
                envelope=torch.ones((1, 1, 4, 4), dtype=torch.complex128),
                grid=_scalar_grid(),
                spectrum=spectrum,
                polarization_representation=(Polarization.scalar()).representation,
                medium=Vacuum(),
                normalization=FieldNormalization.RELATIVE,
                path_reference=wrong_reference,
            )


class _PrivateTensorSlotMediumBase(Medium):
    __slots__ = ("__hidden_refractive_indices",)

    def __init__(self) -> None:
        """
        把 Tensor 写入需要名称改写的双下划线基类 slot
        """

        self.__hidden_refractive_indices = torch.tensor([1.0, 1.5])

    def _evaluate_refractive_index(
        self,
        wavelengths: torch.Tensor,
    ) -> torch.Tensor:
        # 返回同形占位折射率
        return torch.ones_like(wavelengths)

    def _physical_identity(self) -> tuple[object, ...]:
        return ("private_tensor_slot",)


class TestSpatialGrid:
    """
    横向采样网格的物理契约
    """

    def test_centered_grid_places_origin_at_zero(self) -> None:
        """
        中心对齐网格的首采样位置使物理中心落在原点
        """
        grid = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(1.0e-6, 2.0e-6),
        )
        # 偶数采样时首样本位于 -(N//2)*spacing 处
        assert grid.first_sample_position == pytest.approx((-2.0e-6, -4.0e-6))
        assert grid.sample_counts == (4, 4)
        assert grid.sample_spacing == (1.0e-6, 2.0e-6)

    def test_cell_area_is_product_of_spacings(self) -> None:
        """
        横向单元面积为两方向间距的乘积
        """
        grid = SpatialGrid(
            sample_counts=(3, 5),
            sample_spacing=(0.25e-6, 0.5e-6),
            first_sample_position=(0.0, 0.0),
        )
        assert grid.cell_area == pytest.approx(0.125e-12)

    def test_grid_is_immutable(self) -> None:
        """
        网格为不可变物理值
        """
        grid = _scalar_grid()
        with pytest.raises(AttributeError):
            grid.sample_counts = (8, 8)  # type: ignore[misc]

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_grid_rejects_nonfinite_sample_spacing(
        self,
        invalid_value: float,
    ) -> None:
        """
        网格间距中的 NaN 与正负无穷须由 SpatialGrid 拒绝
        """

        with pytest.raises(
            ValueError,
            match="spatial_grid_sample_spacing_nonfinite",
        ):
            SpatialGrid(
                sample_counts=(4, 4),
                sample_spacing=(invalid_value, 1.0e-6),
                first_sample_position=(0.0, 0.0),
            )

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_grid_rejects_nonfinite_first_sample_position(
        self,
        invalid_value: float,
    ) -> None:
        """
        首样本位置中的 NaN 与正负无穷须由 SpatialGrid 拒绝
        """

        with pytest.raises(
            ValueError,
            match="spatial_grid_first_sample_position_nonfinite",
        ):
            SpatialGrid(
                sample_counts=(4, 4),
                sample_spacing=(1.0e-6, 1.0e-6),
                first_sample_position=(invalid_value, 0.0),
            )


class TestSpectrumAndPolarization:
    """
    最小光谱与偏振状态契约
    """

    def test_monochromatic_spectrum_has_unit_weight(self) -> None:
        """
        单波长光谱携带唯一波长与权重 1
        """
        spectrum = _monochromatic_spectrum()
        assert spectrum.count == 1
        assert spectrum.weights == (1.0,)
        assert spectrum.wavelengths[0] == pytest.approx(488.0e-6)

    def test_polarization_component_counts(self) -> None:
        """
        标量、横向、完整偏振分别对应 1、2、3 个分量
        """
        assert Polarization.scalar().component_count == 1
        assert Polarization.transverse().component_count == 2
        assert Polarization.full().component_count == 3

    def test_spectrum_and_polarization_are_recursively_tensor_free(self) -> None:
        """
        光谱与偏振元数据递归不持有 Tensor
        """

        def _is_tensor_present(value: object) -> bool:
            if isinstance(value, torch.Tensor):
                return True
            if is_dataclass(value):
                return any(
                    _is_tensor_present(getattr(value, field.name))
                    for field in fields(value)
                )
            if isinstance(value, tuple):
                return any(_is_tensor_present(item) for item in value)
            return False

        spectrum = Spectrum(
            wavelengths=(488.0e-9, 633.0e-9),
            weights=(0.4, 0.6),
        )
        polarization = Polarization.left_circular()

        assert not _is_tensor_present(spectrum)
        assert not _is_tensor_present(polarization)

    def test_circular_states_follow_frozen_time_convention(self) -> None:
        """
        时间演化独立验证正向传播圆偏振手性约定
        """

        scale = 1.0 / math.sqrt(2.0)
        left = Polarization.left_circular()
        right = Polarization.right_circular()

        assert left.components == pytest.approx((scale + 0j, -1j * scale))
        assert right.components == pytest.approx((scale + 0j, 1j * scale))

        quarter_period = -1j
        left_quarter = tuple(
            (component * quarter_period).real for component in left.components
        )
        right_quarter = tuple(
            (component * quarter_period).real for component in right.components
        )
        assert left_quarter == pytest.approx((0.0, -scale))
        assert right_quarter == pytest.approx((0.0, scale))

    def test_polarization_normalizes_and_rejects_zero_state(self) -> None:
        """
        显式偏振态归一化并拒绝零向量
        """

        transverse = Polarization.transverse(components=(3.0, 4.0j))
        norm = sum(abs(component) ** 2 for component in transverse.components)

        assert norm == pytest.approx(1.0)
        with pytest.raises(OpticalValueError) as rejected:
            Polarization.full(components=(0.0, 0.0, 0.0))
        assert rejected.value.identity == "polarization_state_zero"
        assert rejected.value.explanation

    def test_scalar_representation_is_not_linear_x(self) -> None:
        """
        标量表示与实验室坐标 x 线偏振保持不同身份
        """

        scalar = Polarization.scalar()
        linear_x = Polarization.linear_x()

        assert scalar.representation is PolarizationRepresentation.SCALAR
        assert linear_x.representation is PolarizationRepresentation.TRANSVERSE
        assert scalar != linear_x

    def test_optical_field_carries_representation_not_source_state(
        self,
    ) -> None:
        """
        光场只携带偏振轴表示，实际 Jones 分量由复包络承载
        """
        grid = _scalar_grid()
        field = OpticalField(
            envelope=torch.ones(
                (1, 2, *grid.sample_counts),
                dtype=torch.complex128,
            ),
            grid=grid,
            spectrum=_monochromatic_spectrum(),
            polarization_representation=(
                PolarizationRepresentation.TRANSVERSE
            ),
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )

        assert (
            field.polarization_representation
            is PolarizationRepresentation.TRANSVERSE
        )
        assert not hasattr(field, "polarization")

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_spectrum_rejects_nonfinite_wavelength(
        self,
        invalid_value: float,
    ) -> None:
        """
        光谱波长中的 NaN 与正负无穷须由 Spectrum 拒绝
        """

        with pytest.raises(
            ValueError,
            match="spectrum_wavelength_nonfinite",
        ):
            Spectrum(
                wavelengths=(invalid_value,),
                weights=(1.0,),
            )

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_spectrum_rejects_nonfinite_weight(
        self,
        invalid_value: float,
    ) -> None:
        """
        光谱约减权重中的 NaN 与正负无穷须由 Spectrum 拒绝
        """

        with pytest.raises(
            ValueError,
            match="spectrum_weight_nonfinite",
        ):
            Spectrum(
                wavelengths=(0.5e-6,),
                weights=(invalid_value,),
            )

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_polarization_rejects_nonfinite_component(
        self,
        invalid_value: float,
    ) -> None:
        """
        Jones 分量实部或虚部非有限时须由 Polarization 拒绝
        """

        with pytest.raises(
            ValueError,
            match="polarization_state_nonfinite",
        ):
            Polarization.transverse(
                components=(
                    complex(invalid_value, 0.0),
                    1.0 + 0.0j,
                ),
            )


class TestMedium:
    """
    介质折射率契约与可扩展介质接口
    """

    def test_vacuum_refractive_index_is_one(self) -> None:
        """
        真空对所有波长返回折射率 1
        """
        wavelengths = torch.tensor(
            [488.0e-6, 633.0e-6],
            dtype=torch.float64,
        )
        indices = Vacuum().refractive_index(wavelengths)
        assert torch.allclose(indices, torch.ones(2, dtype=torch.float64))

    def test_constant_medium_refractive_index(self) -> None:
        """
        均匀介质对所有波长返回恒定折射率
        """
        wavelengths = torch.tensor(
            [488.0e-6, 633.0e-6],
            dtype=torch.float64,
        )
        indices = ConstantMedium(index=1.33).refractive_index(wavelengths)
        assert torch.allclose(
            indices,
            torch.full((2,), 1.33, dtype=torch.float64),
        )

    def test_medium_is_extensible_without_rewrite(self) -> None:
        """
        实现 refractive_index 的子类即被视为介质
        """
        wavelengths = torch.tensor([500.0e-6], dtype=torch.float64)

        class _LinearMedium(Medium):
            def _evaluate_refractive_index(
                self,
                wavelengths: torch.Tensor,
            ) -> torch.Tensor:
                # 仅用于验证可扩展契约，非物理色散模型
                return 1.0 + wavelengths

            def _physical_identity(self) -> tuple[object, ...]:
                return ("linear",)

        indices = _LinearMedium().refractive_index(wavelengths)
        assert torch.allclose(indices, 1.0 + wavelengths)


class TestOpticalField:
    """
    光场的固定轴、不可变性与 meta 前向契约
    """

    def test_field_carries_fixed_axes_layout(self) -> None:
        """
        光场包络遵循固定轴布局（批量、光谱、偏振、高度、宽度）
        """
        envelope = torch.randn((2, 3, 1, 4, 4), dtype=torch.complex128)
        spectrum = Spectrum(
            wavelengths=(488.0e-6, 532.0e-6, 633.0e-6),
            weights=(0.2, 0.5, 0.3),
        )
        field = OpticalField(
            envelope=envelope,
            grid=_scalar_grid(),
            spectrum=spectrum,
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=_zero_reference(spectrum),
        )
        assert field.batch_shape == (2,)
        assert field.spectral_count == 3
        assert field.envelope_shape == (2, 3, 1, 4, 4)

    def test_field_axes_follow_spectrum_and_polarization_content(self) -> None:
        """
        光谱轴和偏振轴只携带物理内容要求的长度
        """

        scalar_spectrum = Spectrum.monochromatic(wavelength=532.0e-9)
        scalar_field = OpticalField(
            envelope=torch.ones((1, 1, 4, 4), dtype=torch.complex128),
            grid=_scalar_grid(),
            spectrum=scalar_spectrum,
            polarization_representation=Polarization.scalar().representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=_zero_reference(scalar_spectrum),
        )
        transverse_spectrum = Spectrum(
            wavelengths=(488.0e-9, 633.0e-9),
            weights=(0.5, 0.5),
        )
        transverse_field = OpticalField(
            envelope=torch.ones((2, 2, 4, 4), dtype=torch.complex128),
            grid=_scalar_grid(),
            spectrum=transverse_spectrum,
            polarization_representation=Polarization.transverse().representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=_zero_reference(transverse_spectrum),
        )

        assert scalar_field.envelope_shape == (1, 1, 4, 4)
        assert transverse_field.envelope_shape == (2, 2, 4, 4)

    def test_field_rejects_polarization_axis_mismatch(self) -> None:
        """
        偏振分量数须与包络偏振轴长度一致
        """
        envelope = torch.ones((1, 1, 2, 4, 4), dtype=torch.complex128)
        with pytest.raises(ValueError):
            _make_field(envelope=envelope)

    def test_field_rejects_non_complex_envelope(self) -> None:
        """
        光场包络须为复数张量
        """
        envelope = torch.ones((1, 1, 1, 4, 4), dtype=torch.float32)
        with pytest.raises((TypeError, ValueError)):
            OpticalField(
                envelope=envelope,
                grid=_scalar_grid(),
                spectrum=_monochromatic_spectrum(),
                polarization_representation=(Polarization.scalar()).representation,
                medium=Vacuum(),
                normalization=FieldNormalization.RELATIVE,
                path_reference=_zero_reference(_monochromatic_spectrum()),
            )

    def test_field_is_immutable(self) -> None:
        """
        光场为不可变物理值
        """
        field = _make_field()
        with pytest.raises(AttributeError):
            field.normalization = FieldNormalization.POWER  # type: ignore[misc]

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_field_rejects_nonfinite_envelope(
        self,
        invalid_value: float,
    ) -> None:
        """
        复包络任一分量非有限时须由 OpticalField 拒绝
        """

        envelope = torch.ones((1, 1, 4, 4), dtype=torch.complex128)
        envelope[0, 0, 0, 0] = torch.tensor(
            complex(invalid_value, 0.0),
            dtype=torch.complex128,
        )
        with pytest.raises(
            ValueError,
            match="optical_field_envelope_nonfinite",
        ):
            _make_field(envelope=envelope)

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_field_rejects_nonfinite_path_reference(
        self,
        invalid_value: float,
    ) -> None:
        """
        光程参考非有限时须由强值自身拒绝
        """

        with pytest.raises(
            ValueError,
            match="optical_path_reference_lengths_nonfinite",
        ):
            OpticalPathReference(lengths=(invalid_value,))


class TestFieldPhysicalValueGuards:
    """
    光场对物理值类型的先行确认契约
    """

    @pytest.mark.parametrize(
        ("invalid_field", "error_identity"),
        [
            ("grid", "optical_field_grid_invalid"),
            ("spectrum", "optical_field_spectrum_invalid"),
            (
                "polarization_representation",
                "optical_field_polarization_representation_invalid",
            ),
        ],
    )
    def test_field_rejects_invalid_physical_value_before_axis_lookup(
        self,
        invalid_field: str,
        error_identity: str,
    ) -> None:
        """
        光场先确认物理值类型，再读取 count、component_count 或 sample_counts
        """

        arguments = {
            "envelope": torch.ones((1, 1, 4, 4), dtype=torch.complex128),
            "grid": _scalar_grid(),
            "spectrum": _monochromatic_spectrum(),
            "polarization_representation": (
                PolarizationRepresentation.SCALAR
            ),
            "medium": Vacuum(),
            "normalization": FieldNormalization.RELATIVE,
            "path_reference": _zero_reference(_monochromatic_spectrum()),
        }
        arguments[invalid_field] = object()
        with pytest.raises(TypeError, match=error_identity):
            OpticalField(**arguments)  # type: ignore[arg-type]

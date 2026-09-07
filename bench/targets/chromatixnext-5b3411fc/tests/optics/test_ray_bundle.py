
from __future__ import annotations

import dataclasses

import pytest
import torch

from chromatix_next.errors import OpticalTypeError, OpticalValueError
from chromatix_next.optics import ConstantMedium, Medium, RayBundle, Spectrum, Vacuum
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
    RAY_STATUS_VIGNETTED,
)


def _monochromatic_spectrum() -> Spectrum:
    # 单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=2.0e-6)


def _unit_z_direction(spectral_count: int, ray_count: int) -> torch.Tensor:
    direction = torch.zeros((spectral_count, ray_count, 3), dtype=torch.float64)
    direction[..., 2] = 1.0
    return direction


def _linear_x_transverse_polarization(
    ray_prefix_shape: tuple[int, ...],
) -> torch.Tensor:
    polarization = torch.zeros(
        (*ray_prefix_shape, 3),
        dtype=torch.complex128,
    )
    polarization[..., 0] = 1.0
    return polarization


def _refractive_index_per_ray(
    *,
    spectrum: Spectrum,
    spectral_count: int,
    ray_count: int,
    real_dtype: torch.dtype,
    medium: Medium,
) -> torch.Tensor:
    wavelengths = torch.tensor(
        spectrum.wavelengths,
        dtype=real_dtype,
    )
    indices = medium.refractive_index(wavelengths).to(real_dtype)
    return indices.view(spectral_count, 1).expand(spectral_count, ray_count)


def _valid_bundle(
    *,
    spectrum: Spectrum | None = None,
    medium: Medium | None = None,
    spectral_count: int = 1,
    ray_count: int = 4,
    real_dtype: torch.dtype = torch.float64,
) -> RayBundle:
    # 构造通过全部校验的最小光线束：单位 +z 方向、单位功率、零光程、全 active
    if spectrum is None:
        if spectral_count == 1:
            spectrum_value: Spectrum = _monochromatic_spectrum()
        else:
            spectrum_value = Spectrum(
                wavelengths=tuple(
                    (1.0e-6 + 0.1e-6 * index) for index in range(spectral_count)
                ),
                weights=tuple(1.0 for _ in range(spectral_count)),
            )
    else:
        spectrum_value = spectrum
    resolved_medium = medium or Vacuum()
    positions = torch.zeros((spectral_count, ray_count, 3), dtype=real_dtype)
    directions = _unit_z_direction(spectral_count, ray_count).to(real_dtype)
    power = torch.ones((spectral_count, ray_count), dtype=real_dtype)
    refractive_index = _refractive_index_per_ray(
        spectrum=spectrum_value,
        spectral_count=spectral_count,
        ray_count=ray_count,
        real_dtype=real_dtype,
        medium=resolved_medium,
    )
    optical_path = torch.zeros(
        (spectral_count, ray_count),
        dtype=torch.float64,
    )
    status = torch.full(
        (spectral_count, ray_count),
        RAY_STATUS_ACTIVE,
        dtype=torch.uint8,
    )
    polarization_vector = _linear_x_transverse_polarization(
        (spectral_count, ray_count),
    ).to(dtype=torch.complex128)
    return RayBundle(
        position=positions,
        direction=directions,
        polarization_vector=polarization_vector,
        power=power,
        refractive_index=refractive_index,
        optical_path=optical_path,
        status=status,
        spectrum=spectrum_value,
    )


class TestRayBundleAxesAndDtypes:
    """
    光线束轴布局、dtype 契约与 axis 含义
    """

    @pytest.mark.parametrize(
        ("real_dtype",),
        ((torch.float64,),),
    )
    def test_axes_layout_matches_specification(
        self,
        real_dtype: torch.dtype,
    ) -> None:
        """
        位置/方向尾维为 xyz；功率/光程/状态尾维无 xyz，前置前缀一致
        """
        bundle = _valid_bundle(real_dtype=real_dtype)
        assert bundle.position.shape == (1, 4, 3)
        assert bundle.direction.shape == (1, 4, 3)
        assert bundle.power.shape == (1, 4)
        assert bundle.optical_path.shape == (1, 4)
        assert bundle.status.shape == (1, 4)

    def test_real_state_is_float64_and_path_is_float64(self) -> None:
        """
        位置/方向/功率/折射率为固定双精度 float64，光程始终 device-local float64
        """
        bundle = _valid_bundle()
        assert bundle.position.dtype is torch.float64
        assert bundle.direction.dtype is torch.float64
        assert bundle.power.dtype is torch.float64
        assert bundle.refractive_index.dtype is torch.float64
        assert bundle.optical_path.dtype is torch.float64
        assert bundle.status.dtype is torch.uint8

    def test_axis_meaning_and_counts(self) -> None:
        """
        批量、光谱、光线、笛卡尔分量轴含义可读；count 属性返回正确数值
        """
        bundle = _valid_bundle(spectral_count=2, ray_count=3)
        assert bundle.spectral_count == 2
        assert bundle.ray_count == 3
        assert bundle.batch_shape == ()
        assert bundle.axis_meaning == ("spectrum", "ray", "xyz")

    def test_batch_axes_are_preserved(self) -> None:
        """
        批量维前置光谱轴；axis_meaning 反映读序
        """
        spectrum = Spectrum(
            wavelengths=(1.0e-6, 2.0e-6),
            weights=(0.4, 0.6),
        )
        position = torch.zeros((5, 2, 7, 3), dtype=torch.float64)
        direction = _unit_z_direction(2, 7).expand(5, 2, 7, 3).contiguous()
        direction = direction.to(torch.float64)
        power = torch.ones((5, 2, 7), dtype=torch.float64)
        optical_path = torch.zeros((5, 2, 7), dtype=torch.float64)
        status = torch.full((5, 2, 7), RAY_STATUS_ACTIVE, dtype=torch.uint8)
        bundle = RayBundle(
            position=position,
            direction=direction,
            polarization_vector=_linear_x_transverse_polarization((5, 2, 7)),
            power=power,
            refractive_index=torch.ones_like(power),
            optical_path=optical_path,
            status=status,
            spectrum=spectrum,
        )
        assert bundle.batch_shape == (5,)
        assert bundle.spectral_count == 2
        assert bundle.ray_count == 7
        assert bundle.axis_meaning == (
            "batch_0",
            "spectrum",
            "ray",
            "xyz",
        )


class TestRayBundleStatusContract:
    """
    status 字段是非浮点位掩码：active/missed/vignetted/TIR 各占一位
    """

    @pytest.mark.parametrize(
        ("flag",),
        (
            (RAY_STATUS_ACTIVE,),
            (RAY_STATUS_SURFACE_MISSED,),
            (RAY_STATUS_VIGNETTED,),
            (RAY_STATUS_TOTAL_INTERNAL_REFLECTION,),
        ),
    )
    def test_single_known_flag_is_accepted(self, flag: int) -> None:
        """
        四种已知终止状态的单一标志都构造通过
        """
        spectrum = _monochromatic_spectrum()
        positions = torch.zeros((1, 3, 3), dtype=torch.float64)
        directions = _unit_z_direction(1, 3)
        power = torch.ones((1, 3), dtype=torch.float64)
        optical_path = torch.zeros((1, 3), dtype=torch.float64)
        status = torch.full((1, 3), flag, dtype=torch.uint8)
        bundle = RayBundle(
            position=positions,
            direction=directions,
            polarization_vector=_linear_x_transverse_polarization((1, 3)),
            power=power,
            refractive_index=torch.ones_like(power),
            optical_path=optical_path,
            status=status,
            spectrum=spectrum,
        )
        assert bundle.status.dtype is torch.uint8

    def test_combined_finished_flags_rejected(self) -> None:
        """
        多终止态并集（如 vignetted + missed）⇒ 拒绝；每条 ray 恰好一个终止原因
        """
        combined = (
            RAY_STATUS_SURFACE_MISSED | RAY_STATUS_VIGNETTED
        )
        spectrum = _monochromatic_spectrum()
        positions = torch.zeros((1, 2, 3), dtype=torch.float64)
        directions = _unit_z_direction(1, 2)
        power = torch.zeros((1, 2), dtype=torch.float64)
        optical_path = torch.zeros((1, 2), dtype=torch.float64)
        status = torch.full((1, 2), combined, dtype=torch.uint8)
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=positions,
                direction=directions,
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=power,
                refractive_index=torch.ones_like(power),
                optical_path=optical_path,
                status=status,
                spectrum=spectrum,
            )
        assert (
            rejected.value.identity
            == "ray_bundle_status_multiple_finished"
        )

    def test_zero_state_rejected(self) -> None:
        """
        零状态（无位置位）⇒ 拒绝；每条 ray 必须被指派一个已知状态
        """
        spectrum = _monochromatic_spectrum()
        status = torch.zeros((1, 3), dtype=torch.uint8)
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 3, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 3),
                polarization_vector=_linear_x_transverse_polarization((1, 3)),
                power=torch.ones((1, 3), dtype=torch.float64),
                refractive_index=torch.ones((1, 3), dtype=torch.float64),
                optical_path=torch.zeros((1, 3), dtype=torch.float64),
                status=status,
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_status_zero"

    def test_active_and_finished_combination_rejected(self) -> None:
        """
        active 与 Finished Ray 原因同时置位 ⇒ 拒绝
        """
        combined = RAY_STATUS_ACTIVE | RAY_STATUS_VIGNETTED
        spectrum = _monochromatic_spectrum()
        status = torch.full((1, 3), combined, dtype=torch.uint8)
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 3, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 3),
                polarization_vector=_linear_x_transverse_polarization((1, 3)),
                power=torch.ones((1, 3), dtype=torch.float64),
                refractive_index=torch.ones((1, 3), dtype=torch.float64),
                optical_path=torch.zeros((1, 3), dtype=torch.float64),
                status=status,
                spectrum=spectrum,
            )
        assert (
            rejected.value.identity
            == "ray_bundle_status_active_and_finished"
        )

    def test_inactive_rays_keep_finite_payload(self) -> None:
        """
        inactive rays 保留有限 last 物理值；NaN payload 被构造拒绝
        """
        spectrum = _monochromatic_spectrum()
        positions = torch.zeros((1, 2, 3), dtype=torch.float64)
        positions[..., 0] = float("nan")
        directions = _unit_z_direction(1, 2)
        power = torch.ones((1, 2), dtype=torch.float64)
        optical_path = torch.zeros((1, 2), dtype=torch.float64)
        status = torch.full(
            (1, 2),
            RAY_STATUS_VIGNETTED,
            dtype=torch.uint8,
        )
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=positions,
                direction=directions,
                polarization_vector=_linear_x_transverse_polarization((1, 2)),
                power=power,
                refractive_index=torch.ones_like(power),
                optical_path=optical_path,
                status=status,
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_position_nonfinite"


class TestRayBundleConstructionRejections:
    """
    构造拒绝且不静默修复：malformed axes、非单位方向、负功率、
    非有限、不一致光谱 metadata、未知 status 位、浮点 status dtype
    """

    def test_mismatched_position_direction_prefix_rejected(self) -> None:
        """
        位置前缀 (spectrum, ray) 与方向不一致 ⇒ 稳定域错误
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=torch.zeros((1, 5, 3), dtype=torch.float64),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_axes_mismatched"

    def test_mismatched_power_shape_rejected(self) -> None:
        """
        功率形状 (spectrum, ray) 与位置前缀不一致 ⇒ 稳定域错误
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 3), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_axes_mismatched"

    def test_non_unit_direction_rejected(self) -> None:
        """
        非单位方向 ⇒ 拒绝；构造不会静默归一化 authored 物理
        """
        spectrum = _monochromatic_spectrum()
        bad_direction = torch.zeros((1, 4, 3), dtype=torch.float64)
        bad_direction[..., 2] = 0.5
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=bad_direction,
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_direction_not_unit"

    def test_negative_power_rejected(self) -> None:
        """
        负功率 ⇒ 拒绝；理想几何交互不发明负能量
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=-torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_power_negative"

    def test_nonfinite_position_rejected(self) -> None:
        """
        位置非有限 ⇒ 拒绝；inactive rays 也要保留有限 last 物理值
        """
        spectrum = _monochromatic_spectrum()
        bad_position = torch.zeros((1, 4, 3), dtype=torch.float64)
        bad_position[..., 1] = float("inf")
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=bad_position,
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_position_nonfinite"

    def test_nonfinite_optical_path_rejected(self) -> None:
        """
        光程非有限 ⇒ 拒绝
        """
        spectrum = _monochromatic_spectrum()
        bad_path = torch.full((1, 4), float("nan"), dtype=torch.float64)
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=bad_path,
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_optical_path_nonfinite"

    def test_inconsistent_spectrum_metadata_rejected(self) -> None:
        """
        光谱分量数与位置 spectrum 轴不一致 ⇒ 拒绝
        """
        mismatched = Spectrum(
            wavelengths=(1.0e-6, 2.0e-6),
            weights=(1.0, 1.0),
        )
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=mismatched,
            )
        assert rejected.value.identity == "ray_bundle_spectrum_axis_mismatch"

    def test_unknown_status_bits_rejected(self) -> None:
        """
        status 含未知位（非已知 mask 子集）⇒ 拒绝
        """
        spectrum = _monochromatic_spectrum()
        unknown = torch.full((1, 4), 32, dtype=torch.uint8)
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=unknown,
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_status_bits_unknown"

    def test_floating_status_dtype_rejected(self) -> None:
        """
        status 浮点 dtype ⇒ 拒绝；状态必须用非浮点 bitmask 表达
        """
        spectrum = _monochromatic_spectrum()
        float_status = torch.full(
            (1, 4),
            float(RAY_STATUS_ACTIVE),
            dtype=torch.float32,
        )
        with pytest.raises(OpticalTypeError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=float_status,
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_status_dtype_invalid"

    def test_complex_position_dtype_rejected(self) -> None:
        """
        复数位置 ⇒ 拒绝；位置/方向/功率是实数可观测量
        """
        spectrum = _monochromatic_spectrum()
        complex_position = torch.complex(
            torch.zeros((1, 4, 3)),
            torch.zeros((1, 4, 3)),
        )
        with pytest.raises(OpticalTypeError) as rejected:
            RayBundle(
                position=complex_position,
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_position_dtype_invalid"

    def test_float32_optical_path_rejected(self) -> None:
        """
        光程必须 device-local float64；float32 会被拒绝
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalTypeError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float32),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_optical_path_dtype_invalid"

    def test_scalar_position_rank_rejected_without_index_error(self) -> None:
        """
        0 维标量位置 ⇒ 稳定域错误；低秩 malformed 输入不泄漏 IndexError
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.tensor(0.0, dtype=torch.float64),
                direction=torch.tensor(0.0, dtype=torch.float64),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.tensor(1.0, dtype=torch.float64),
                refractive_index=torch.tensor(1.0, dtype=torch.float64),
                optical_path=torch.tensor(0.0, dtype=torch.float64),
                status=torch.full((), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_position_axis_invalid"

    def test_rank_one_position_rejected_without_index_error(self) -> None:
        """
        1 维位置（只有 xyz 尾维）⇒ 稳定域错误；shape[-3] 不在低秩输入上触发 IndexError
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((3,), dtype=torch.float64),
                direction=torch.zeros((3,), dtype=torch.float64),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1,), dtype=torch.float64),
                refractive_index=torch.ones((1,), dtype=torch.float64),
                optical_path=torch.zeros((1,), dtype=torch.float64),
                status=torch.full((1,), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_position_axis_invalid"

    def test_scalar_direction_rank_rejected_without_index_error(self) -> None:
        """
        位置秩充足但方向 0 维 ⇒ 方向轴稳定域错误（秩守卫覆盖每条向量场）
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 2, 3), dtype=torch.float64),
                direction=torch.tensor(0.0, dtype=torch.float64),
                polarization_vector=_linear_x_transverse_polarization((1, 2)),
                power=torch.ones((1, 2), dtype=torch.float64),
                refractive_index=torch.ones((1, 2), dtype=torch.float64),
                optical_path=torch.zeros((1, 2), dtype=torch.float64),
                status=torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_direction_axis_invalid"


class TestRayBundlePlacementInvariants:
    """
    同一光线束的全部张量位于同一设备；实精度一致
    """

    def test_float32_real_state_rejected(self) -> None:
        """
        固定双精度下实张量必须为 float64；float32 实状态被稳定身份拒绝
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalTypeError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float32),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_position_dtype_invalid"


class TestRayBundlePerRayRefractiveIndex:
    """
    光线束携带逐 ray 正实折射率，与 Spectrum 元数据并列；不含复振幅、偏振或横向网格
    """

    def test_carries_evaluated_refractive_index(self) -> None:
        """
        介质在 authored 波长上评估后的折射率以逐 ray 张量承载，替代一份共享 Medium
        """
        medium = ConstantMedium(index=1.5)
        bundle = _valid_bundle(medium=medium)
        assert isinstance(bundle.refractive_index, torch.Tensor)
        assert bundle.refractive_index.shape == (1, 4)
        assert torch.allclose(
            bundle.refractive_index,
            torch.full_like(bundle.refractive_index, 1.5),
        )

    def test_polychromatic_evaluation_uses_wavelength_axis(self) -> None:
        """
        多波长光谱：每条 ray 在每个波长层各取该波长的介质折射率（spectrum 轴展开）
        """
        spectrum = Spectrum(
            wavelengths=(1.0e-6, 2.0e-6),
            weights=(0.5, 0.5),
        )
        bundle = _valid_bundle(
            spectrum=spectrum,
            medium=ConstantMedium(index=1.3),
            spectral_count=2,
            ray_count=3,
        )
        assert bundle.refractive_index.shape == (2, 3)
        assert torch.allclose(
            bundle.refractive_index,
            torch.full((2, 3), 1.3, dtype=bundle.refractive_index.dtype),
        )

    def test_nonpositive_refractive_index_rejected(self) -> None:
        """
        折射率必须处处严格为正：零或负值 ⇒ 拒绝
        """
        spectrum = _monochromatic_spectrum()
        bad_index = torch.full((1, 4), 0.0, dtype=torch.float64)
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4).to(torch.float64),
                polarization_vector=_linear_x_transverse_polarization((1, 4)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=bad_index,
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert (
            rejected.value.identity
            == "ray_bundle_refractive_index_nonpositive"
        )

    def test_carries_mandatory_polarization_vector_and_no_complex_amplitude(
        self,
    ) -> None:
        """
        光线束字段集合恰为 8 项；强制携带 polarization_vector，但仍不含
        envelope / 复振幅 / grid / medium
        """
        bundle = _valid_bundle()
        expected_fields = {
            "position",
            "direction",
            "polarization_vector",
            "power",
            "refractive_index",
            "optical_path",
            "status",
            "spectrum",
        }
        actual = {field.name for field in dataclasses.fields(bundle)}
        assert actual == expected_fields


class TestRayBundlePolarizationVector:
    """
    polarization_vector：固定 complex128、与位置同形、有限、复单位、横向；
    malformed 公共输入以稳定的 RayBundle 错误身份拒绝，绝不静默归一化或投影
    """

    def test_polarization_is_complex128_and_transverse_to_unit_direction(self) -> None:
        """
        偏振方向固定 complex128，横截于实单位 ray 方向，复单位范数
        """
        bundle = _valid_bundle()
        assert bundle.polarization_vector.dtype is torch.complex128
        assert bundle.polarization_vector.shape == bundle.position.shape
        projection = (
            bundle.polarization_vector * bundle.direction
        ).sum(dim=-1)
        assert torch.allclose(projection.real, torch.zeros_like(projection.real))
        assert torch.allclose(projection.imag, torch.zeros_like(projection.imag))
        norm_sq = (bundle.polarization_vector.real**2).sum(-1) + (
            bundle.polarization_vector.imag**2
        ).sum(-1)
        assert torch.allclose(norm_sq, torch.ones_like(norm_sq))

    def test_missing_polarization_field_is_rejected_as_type_error(self) -> None:
        """
        polarization_vector 是强制字段，缺失即 TypeError（无默认、无可空状态）
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(TypeError):
            RayBundle(  # type: ignore[call-arg]
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )

    def test_real_polarization_dtype_rejected(self) -> None:
        """
        实 dtype 偏振 ⇒ 拒绝（必须 complex128）
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalTypeError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=torch.zeros((1, 4, 3), dtype=torch.float64),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert (
            rejected.value.identity
            == "ray_bundle_polarization_vector_dtype_invalid"
        )

    def test_complex64_polarization_dtype_rejected(self) -> None:
        """
        complex64 偏振 ⇒ 拒绝（固定双精度核：必须 complex128）
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalTypeError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization(
                    (1, 4)
                ).to(torch.complex64),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert (
            rejected.value.identity
            == "ray_bundle_polarization_vector_dtype_invalid"
        )

    def test_mismatched_polarization_shape_rejected(self) -> None:
        """
        偏振形状与位置前缀不一致 ⇒ axes_mismatched
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=_linear_x_transverse_polarization((1, 3)),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert rejected.value.identity == "ray_bundle_axes_mismatched"

    def test_nonfinite_polarization_rejected(self) -> None:
        """
        偏振方向含非数 ⇒ 拒绝；终止 ray 也保留有限偏振
        """
        spectrum = _monochromatic_spectrum()
        bad = _linear_x_transverse_polarization((1, 4))
        bad = bad.clone()
        bad[0, 0, 1] = torch.tensor(complex(float("inf"), 0.0))
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=bad,
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert (
            rejected.value.identity
            == "ray_bundle_polarization_vector_nonfinite"
        )

    def test_zero_polarization_rejected(self) -> None:
        """
        全零偏振 ⇒ 非单位拒绝；构造不静默归一化
        """
        spectrum = _monochromatic_spectrum()
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=torch.zeros((1, 4, 3), dtype=torch.complex128),
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert (
            rejected.value.identity
            == "ray_bundle_polarization_vector_not_unit"
        )

    def test_longitudinal_polarization_rejected(self) -> None:
        """
        纵向偏振（沿 ray 方向）⇒ 横向性拒绝；构造不静默正交化
        """
        spectrum = _monochromatic_spectrum()
        longitudinal = torch.zeros((1, 4, 3), dtype=torch.complex128)
        longitudinal[..., 2] = 1.0  # 与 +z 方向共线
        with pytest.raises(OpticalValueError) as rejected:
            RayBundle(
                position=torch.zeros((1, 4, 3), dtype=torch.float64),
                direction=_unit_z_direction(1, 4),
                polarization_vector=longitudinal,
                power=torch.ones((1, 4), dtype=torch.float64),
                refractive_index=torch.ones((1, 4), dtype=torch.float64),
                optical_path=torch.zeros((1, 4), dtype=torch.float64),
                status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=spectrum,
            )
        assert (
            rejected.value.identity
            == "ray_bundle_polarization_vector_longitudinal"
        )

    def test_finished_rays_keep_finite_transverse_polarization(self) -> None:
        """
        终止 ray 仍携带有限、单位、横向偏振方向；零功率通道亦是
        """
        spectrum = _monochromatic_spectrum()
        polarization = _linear_x_transverse_polarization((1, 4))
        bundle = RayBundle(
            position=torch.zeros((1, 4, 3), dtype=torch.float64),
            direction=_unit_z_direction(1, 4),
            polarization_vector=polarization,
            power=torch.zeros((1, 4), dtype=torch.float64),
            refractive_index=torch.ones((1, 4), dtype=torch.float64),
            optical_path=torch.zeros((1, 4), dtype=torch.float64),
            status=torch.full((1, 4), RAY_STATUS_VIGNETTED, dtype=torch.uint8),
            spectrum=spectrum,
        )
        assert torch.isfinite(bundle.polarization_vector).all()
        norm_sq = (bundle.polarization_vector.real**2).sum(-1) + (
            bundle.polarization_vector.imag**2
        ).sum(-1)
        assert torch.allclose(norm_sq, torch.ones_like(norm_sq))

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import torch

from chromatix_next._numerics.gaussian_beam import gaussian_beam_unit_envelope
from chromatix_next._numerics.intensity import sampled_field_power_amplitude
from chromatix_next._numerics.wave_number import medium_wave_numbers
from chromatix_next._tensors import (
    _register_fixed_double_scalar_parameter_or_buffer,
    _validate_fixed_double_real_scalar,
    cache_identity,
    is_value_readable,
)
import chromatix_next.errors as _errors

from .._role_contract import _SourceRole
from .._sampled_wave_synthesis import _SampledWaveSource
from .._source_lifecycle import (
    _decode_wave_extra_state_fields,
    _encode_source_identity_fields,
    _read_named_parameter_or_buffer,
    _register_named_physical_state,
    _SourceStatePlan,
    _validate_source_physical_buffer_projection,
)
from ..field import FieldNormalization, OpticalField, _SourceLineage
from ..grid import SpatialGrid, _is_centered_grid
from ..medium import Medium, Vacuum
from ..polarization import Polarization
from ..spectrum import Spectrum


def _beam_scalar_messages(name: str, is_positive: bool) -> dict[str, str]:
    sign_word = "正" if is_positive else "有限"
    return {
        "tensor_message": (
            f"高斯光束的 {name} 必须是{sign_word}的有限实数标量，"
            "不能是复数或多分量张量，收到的是 {value!r}"
        ),
        "scalar_message": (
            f"高斯光束的 {name} 必须是{sign_word}的有限实数，"
            "收到的是 {value!r}"
        ),
    }

def _encode_gaussian_beam_extra_state(source: GaussianBeam) -> dict[str, object]:
    payload = _encode_source_identity_fields(
        spectrum=source._spectrum_value,
        polarization=source._polarization_value,
        medium_identity=source._medium_value.physical_identity(),
    )
    payload["normalization"] = source._normalization.value
    return payload


def _plan_gaussian_beam_state_installation(
    source: GaussianBeam,
    state: object,
    *,
    projected_buffers: Mapping[str, torch.Tensor] | None = None,
) -> _SourceStatePlan:
    try:
        payload = cast(dict[str, object], state)
        spectrum, polarization, medium_identity, normalization = (
            _decode_wave_extra_state_fields(payload)
        )
    except (KeyError, TypeError, ValueError) as error:
        raise _errors.OpticalRuntimeError(
            "gaussian_beam_extra_state_invalid",
            "高斯光束的附加状态缺字段或字段类型不对，无法恢复物理身份",
        ) from error
    if (
        medium_identity != source._medium_value.physical_identity()
        or normalization != source._normalization.value
    ):
        raise _errors.OpticalRuntimeError(
            "gaussian_beam_extra_state_structure_mismatch",
            "载入的介质或归一化与当前高斯光束不一致；"
            "状态字典只能载回结构相同的光源",
        )
    if projected_buffers is None:
        projected_buffers = {
            "wavelengths": source._buffer("wavelengths"),
            "spectral_weights": source._buffer("spectral_weights"),
            "polarization_state": source._buffer("polarization_state"),
        }
    _validate_source_physical_buffer_projection(
        spectrum=spectrum,
        polarization=polarization,
        wavelengths=projected_buffers["wavelengths"],
        spectral_weights=projected_buffers["spectral_weights"],
        polarization_state=projected_buffers["polarization_state"],
        error_identity="gaussian_beam_extra_state_buffer_mismatch",
    )
    return _SourceStatePlan(
        spectrum=spectrum,
        polarization=polarization,
        buffer_shapes=(
            ("wavelengths", torch.Size((spectrum.count,))),
            ("spectral_weights", torch.Size((spectrum.count,))),
            ("polarization_state", torch.Size((len(polarization.components),))),
        ),
        invalidate_envelope_cache=True,
    )


class GaussianBeam(_SampledWaveSource):
    """
    在横向网格上产生 paraxial 高斯光束包络的源组件

    Args:
        spectrum: 光谱采样、权重与波长语义
        polarization: 发射光的偏振表示与分量
        medium: 光所在位置的折射率模型
        waist: 高斯束腰沿两个网格方向的半径
        waist_location: 束腰相对发射面的轴向位置
        relative_amplitude: 各光谱与偏振分量的相对复振幅
        total_power: 源在整个采样面上的总功率

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    _encode_extra_state_payload = staticmethod(_encode_gaussian_beam_extra_state)
    _plan_state_installation = staticmethod(_plan_gaussian_beam_state_installation)

    @property
    def role(self) -> _SourceRole:
        """
        源角色字面量

        Returns:
            返回该 Source 组件的稳定角色标识 "source"

        """

        return "source"

    def __init__(  # noqa: PLR0913
        self,
        *,
        spectrum: Spectrum,
        polarization: Polarization,
        medium: Medium = Vacuum(),
        waist: float | torch.nn.Parameter,
        waist_location: float | torch.nn.Parameter = 0.0,
        relative_amplitude: float | torch.nn.Parameter | None = None,
        total_power: float | torch.nn.Parameter | None = None,
    ) -> None:
        super().__init__()
        self._source_lineage = _SourceLineage()
        self._validate_normalization_exclusive(relative_amplitude, total_power)
        self._validate_physical_values(spectrum, polarization, medium)
        self._validate_waist_value(waist)
        self._validate_waist_location_value(waist_location)

        self._spectrum_value = spectrum
        self._polarization_value = polarization
        self._medium_value = medium
        _register_named_physical_state(
            self,
            spectrum=spectrum,
            polarization=polarization,
        )

        if total_power is not None:
            self._normalization = FieldNormalization.POWER
        else:
            self._normalization = FieldNormalization.RELATIVE

        # waist 与 waist_location：Parameter 保持身份；普通数值 -> float64 固定 Buffer
        self._register_beam_parameter(
            "waist",
            waist,
            is_positive=True,
        )
        self._register_beam_parameter(
            "waist_location",
            waist_location,
            is_positive=False,
        )

        # 归一化振幅：用户 Parameter 保持身份；普通数值 -> float64 固定 Buffer
        if total_power is not None:
            scale_name = "total_power"
            scale_value: float | torch.nn.Parameter = total_power
        else:
            assert relative_amplitude is not None
            scale_name = "relative_amplitude"
            scale_value = relative_amplitude
        _register_fixed_double_scalar_parameter_or_buffer(
            self,
            name=scale_name,
            value=scale_value,
            is_positive=True,
            error_identity=f"gaussian_beam_{scale_name}_invalid",
            **_beam_scalar_messages(scale_name, True),
        )

        self._register_unit_envelope_cache()

    def forward(self, grid: SpatialGrid) -> OpticalField:  # type: ignore[override]
        """
        在给定网格上计算高斯光束包络并返回归一化光场

        Args:
            grid: 定义采样位置与间距的空间网格

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        Raises:
            OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

        """
        if not isinstance(grid, SpatialGrid):
            message = (
                "高斯光束要在横向网格上取样才能给出包络，"
                f"收到的是 {type(grid).__name__}"
            )
            raise _errors.OpticalTypeError(
                "gaussian_beam_grid_invalid",
                message,
            )
        return self._synthesize_sampled_wave(grid)

    @staticmethod
    def _validate_normalization_exclusive(
        relative_amplitude: object,
        total_power: object,
    ) -> None:
        is_exactly_one = (relative_amplitude is not None) ^ (
            total_power is not None
        )
        if not is_exactly_one:
            if relative_amplitude is not None:
                raise _errors.OpticalValueError(
                    "gaussian_beam_normalization_exclusive",
                    "同一束高斯光束的幅值只能有一种归一化，"
                    "相对幅值与总功率请删去其一，"
                    f"收到的是 {relative_amplitude!r} 与 {total_power!r}",
                )
            raise _errors.OpticalValueError(
                "gaussian_beam_normalization_missing",
                "高斯光束的幅值必须由一种归一化定出，"
                "请在相对幅值与总功率里任选其一给出，两者都没有收到",
            )

    @staticmethod
    def _validate_physical_values(
        spectrum: object,
        polarization: object,
        medium: object,
    ) -> None:
        if not isinstance(spectrum, Spectrum):
            message = (
                "高斯光束的光谱必须由波长与权重成对给出，"
                f"收到的是 {type(spectrum).__name__}"
            )
            raise _errors.OpticalTypeError(
                "gaussian_beam_spectrum_invalid",
                message,
            )
        if not isinstance(polarization, Polarization):
            message = (
                "高斯光束的偏振必须是归一化的琼斯状态，"
                "分量不由名称猜测，"
                f"收到的是 {type(polarization).__name__}"
            )
            raise _errors.OpticalTypeError(
                "gaussian_beam_polarization_invalid",
                message,
            )
        if not isinstance(medium, Medium):
            message = (
                "高斯光束的折射率只从所在介质取得，"
                f"收到的介质是 {type(medium).__name__}"
            )
            raise _errors.OpticalTypeError(
                "gaussian_beam_medium_invalid",
                message,
            )

    @staticmethod
    def _validate_waist_value(waist: object) -> None:
        _validate_fixed_double_real_scalar(
            value=waist,
            is_positive=True,
            error_identity="gaussian_beam_waist_invalid",
            **_beam_scalar_messages("waist", True),
        )

    @staticmethod
    def _validate_waist_location_value(waist_location: object) -> None:
        _validate_fixed_double_real_scalar(
            value=waist_location,
            is_positive=False,
            error_identity="gaussian_beam_waist_location_invalid",
            **_beam_scalar_messages("waist_location", False),
        )

    def _register_beam_parameter(
        self,
        name: str,
        value: float | torch.nn.Parameter,
        *,
        is_positive: bool,
    ) -> None:
        _register_fixed_double_scalar_parameter_or_buffer(
            self,
            name=name,
            value=value,
            is_positive=is_positive,
            error_identity=f"gaussian_beam_{name}_invalid",
            **_beam_scalar_messages(name, is_positive),
        )

    @property
    def _waist_value(self) -> torch.Tensor:
        return _read_named_parameter_or_buffer(self, name="waist")

    @property
    def _waist_location_value(self) -> torch.Tensor:
        return _read_named_parameter_or_buffer(self, name="waist_location")

    def _unit_envelope_cache_key_for(self, grid: SpatialGrid) -> tuple[Any, ...]:
        wavelengths = self._buffer("wavelengths")
        weights = self._buffer("spectral_weights")
        polarization = self._buffer("polarization_state")
        if not is_value_readable(wavelengths):
            return (object(),)
        position_identity: tuple[object, ...]
        if _is_centered_grid(grid):
            position_identity = ("centered",)
        else:
            position_identity = tuple(
                cache_identity(value)
                for value in grid.first_sample_position
            )
        return (
            "gaussian_beam_unit_envelope",
            grid.sample_counts,
            tuple(cache_identity(value) for value in grid.signed_spacing),
            position_identity,
            tuple(grid.orientation),
            self._spectrum_value.wavelengths,
            self._spectrum_value.weights,
            self._polarization_value.components,
            cache_identity(wavelengths),
            cache_identity(weights),
            cache_identity(polarization),
            self._medium_value.physical_identity(),
            self._normalization.value,
            cache_identity(self._waist_value),
            cache_identity(self._waist_location_value),
            str(wavelengths.device),
            str(self._fixed_complex_dtype()),
        )

    def _validate_rayleigh_range_positive(
        self,
        wave_number: torch.Tensor,
    ) -> None:
        waist = self._waist_value
        if not is_value_readable(waist):
            return
        waist_squared = waist * waist
        rayleigh_range = 0.5 * wave_number * waist_squared
        is_strictly_positive = (rayleigh_range > 0).all()
        if is_value_readable(is_strictly_positive) and not bool(
            is_strictly_positive
        ):
            raise _errors.OpticalValueError(
                "gaussian_beam_rayleigh_range_invalid",
                "高斯光束的 waist 须使每光谱分量的 Rayleigh range 严格为正，"
                "过小的 waist 相对波长会令 beam 退化为非物理，"
                f"收到的 waist 是 {waist!r}",
            )

    def _compute_unit_envelope(self, grid: SpatialGrid) -> torch.Tensor:
        # 对齐固定状态并委托私有数值核合成含偏振状态的单位包络
        device = self._buffer("wavelengths").device
        real_dtype = self._fixed_real_dtype()
        complex_dtype = self._fixed_complex_dtype()
        wavelengths = self._buffer("wavelengths").to(
            device=device,
            dtype=real_dtype,
        )
        indices = self._medium_value.refractive_index(wavelengths).to(
            device=device,
            dtype=real_dtype,
        )
        wave_number = medium_wave_numbers(
            wavelengths=wavelengths,
            refractive_indices=indices,
        )
        self._validate_rayleigh_range_positive(wave_number)
        waist_radius = self._waist_value.to(device=device, dtype=real_dtype)
        waist_location = self._waist_location_value.to(
            device=device,
            dtype=real_dtype,
        )
        polarization_state = self._buffer("polarization_state").to(
            device=device,
            dtype=complex_dtype,
        )
        return gaussian_beam_unit_envelope(
            sample_counts=grid.sample_counts,
            signed_spacing=grid.signed_spacing,
            first_sample_position=grid.first_sample_position,
            wavelengths=wavelengths,
            refractive_indices=indices,
            waist_radius=waist_radius,
            waist_location=waist_location,
            polarization_state=polarization_state,
        )

    def _validate_physical_state(self) -> None:
        _validate_fixed_double_real_scalar(
            value=self._waist_value,
            is_positive=True,
            error_identity="gaussian_beam_waist_invalid",
            **_beam_scalar_messages("waist", True),
        )
        _validate_fixed_double_real_scalar(
            value=self._waist_location_value,
            is_positive=False,
            error_identity="gaussian_beam_waist_location_invalid",
            **_beam_scalar_messages("waist_location", False),
        )
        scale_name = (
            "total_power"
            if self._normalization is FieldNormalization.POWER
            else "relative_amplitude"
        )
        _validate_fixed_double_real_scalar(
            value=self._scale_value,
            is_positive=True,
            error_identity=f"gaussian_beam_{scale_name}_invalid",
            **_beam_scalar_messages(scale_name, True),
        )

    def _power_amplitude(self, grid: SpatialGrid) -> torch.Tensor:
        # 由总功率与单位包络模方导出标量振幅，使空间积分给出声明总功率
        total_power = self._scale_value
        weights = self._buffer("spectral_weights")
        # 源边界守护：全零权重使功率无处分配，以稳定身份拒绝而非输出非有限包络
        if sum(self._spectrum_value.weights) <= 0.0:
            raise _errors.OpticalValueError(
                "gaussian_beam_total_power_spectrum_weight_sum_invalid",
                "按总功率归一化时光谱权重之和必须为正，否则功率无处分配，"
                f"收到的权重是 {self._spectrum_value.weights!r}",
            )
        unit_envelope = self._unit_envelope_for(grid)
        return sampled_field_power_amplitude(
            total_power=total_power,
            spectral_weights=weights.to(
                device=total_power.device,
                dtype=total_power.dtype,
            ),
            unit_envelope=unit_envelope,
            cell_area=grid.cell_area,
        )

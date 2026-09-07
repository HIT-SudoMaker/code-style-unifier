from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import torch

from chromatix_next._numerics.intensity import sampled_field_power_amplitude
from chromatix_next._numerics.point_source import (
    point_source_sampling_fence,
    point_source_unit_envelope,
)
from chromatix_next._tensors import (
    _materialize_finite_fixed_double_three_vector,
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

_SCALE_TENSOR_MESSAGE = (
    "可训练的归一化取值必须是正的有限实数标量，不能是复数或多分量张量，"
    "收到的是 {value!r}"
)

_SCALE_SCALAR_MESSAGE = (
    "点源的归一化取值必须是正的有限实数，零和负数没有物理意义，"
    "收到的是 {value!r}"
)



def _materialize_point_source_position(value: object) -> torch.Tensor:
    position = _materialize_finite_fixed_double_three_vector(value)
    if position is not None:
        return position
    if isinstance(value, torch.Tensor):
        message = (
            "点源位置必须是长度 3 的有限 float64 实张量，坐标顺序为 (y, x, z)，"
            f"收到的形状是 {tuple(value.shape)}、dtype 是 {value.dtype}"
        )
    else:
        message = (
            "点源位置必须是三个有限实数组成的 (y, x, z) 元组，"
            f"收到的是 {value!r}"
        )
    raise _errors.OpticalValueError(
        "point_source_position_invalid",
        message,
    )


def _encode_point_source_extra_state(source: PointSource) -> dict[str, object]:
    payload = _encode_source_identity_fields(
        spectrum=source._spectrum_value,
        polarization=source._polarization_value,
        medium_identity=source._medium_value.physical_identity(),
    )
    payload["normalization"] = source._normalization.value
    return payload


def _plan_point_source_state_installation(
    source: PointSource,
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
            "point_source_extra_state_invalid",
            "点源的附加状态缺字段或字段类型不对，无法恢复物理身份",
        ) from error
    if (
        medium_identity != source._medium_value.physical_identity()
        or normalization != source._normalization.value
    ):
        raise _errors.OpticalRuntimeError(
            "point_source_extra_state_structure_mismatch",
            "载入的介质或归一化与当前点源不一致；"
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
        error_identity="point_source_extra_state_buffer_mismatch",
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


class PointSource(_SampledWaveSource):
    """
    在横向网格上产生球面波包络的源组件

    Args:
        spectrum: 光谱采样、权重与波长语义
        polarization: 发射光的偏振表示与分量
        medium: 光所在位置的折射率模型
        position: 光线位置或点源位置的笛卡尔坐标
        relative_amplitude: 各光谱与偏振分量的相对复振幅
        total_power: 源在整个采样面上的总功率

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    _encode_extra_state_payload = staticmethod(_encode_point_source_extra_state)
    _plan_state_installation = staticmethod(_plan_point_source_state_installation)

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
        position: tuple[float, float, float] | torch.nn.Parameter,
        relative_amplitude: float | torch.nn.Parameter | None = None,
        total_power: float | torch.nn.Parameter | None = None,
    ) -> None:
        super().__init__()
        self._source_lineage = _SourceLineage()
        self._validate_normalization_exclusive(relative_amplitude, total_power)
        self._validate_physical_values(spectrum, polarization, medium)
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

        self._register_position(position)

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
            error_identity=f"point_source_{scale_name}_invalid",
            tensor_message=_SCALE_TENSOR_MESSAGE,
            scalar_message=_SCALE_SCALAR_MESSAGE,
        )

        self._register_unit_envelope_cache()

    def forward(self, grid: SpatialGrid) -> OpticalField:  # type: ignore[override]
        """
        在给定网格上计算球面波包络并返回归一化光场

        Args:
            grid: 定义采样位置与间距的空间网格

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        Raises:
            OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

        """
        if not isinstance(grid, SpatialGrid):
            message = (
                "点源要在横向网格上取样才能给出球面波包络，"
                f"收到的是 {type(grid).__name__}"
            )
            raise _errors.OpticalTypeError(
                "point_source_grid_invalid",
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
                    "point_source_normalization_exclusive",
                    "同一个点源的幅值只能有一种归一化，"
                    "相对幅值与总功率请删去其一，"
                    f"收到的是 {relative_amplitude!r} 与 {total_power!r}",
                )
            raise _errors.OpticalValueError(
                "point_source_normalization_missing",
                "点源的幅值必须由一种归一化定出，"
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
                "点源的光谱必须由波长与权重成对给出，"
                f"收到的是 {type(spectrum).__name__}"
            )
            raise _errors.OpticalTypeError(
                "point_source_spectrum_invalid",
                message,
            )
        if not isinstance(polarization, Polarization):
            message = (
                "点源的偏振必须是归一化的琼斯状态，"
                "分量不由名称猜测，"
                f"收到的是 {type(polarization).__name__}"
            )
            raise _errors.OpticalTypeError(
                "point_source_polarization_invalid",
                message,
            )
        if not isinstance(medium, Medium):
            message = (
                "点源的折射率只从所在介质取得，"
                f"收到的介质是 {type(medium).__name__}"
            )
            raise _errors.OpticalTypeError(
                "point_source_medium_invalid",
                message,
            )

    @staticmethod
    def _validate_scale(
        *,
        name: str,
        value: object,
    ) -> None:
        _validate_fixed_double_real_scalar(
            value=value,
            is_positive=True,
            error_identity=f"point_source_{name}_invalid",
            tensor_message=_SCALE_TENSOR_MESSAGE,
            scalar_message=_SCALE_SCALAR_MESSAGE,
        )

    def _register_position(
        self,
        value: tuple[float, float, float] | torch.nn.Parameter,
    ) -> None:
        if isinstance(value, torch.Tensor) and not isinstance(
            value,
            torch.nn.Parameter,
        ):
            message = (
                "position 作为张量提供时必须是 torch.nn.Parameter；"
                f"若不需要训练请传 Python 三元组，收到的是 {value!r}"
            )
            raise _errors.OpticalTypeError(
                "point_source_position_invalid",
                message,
            )
        position = _materialize_point_source_position(value)
        if isinstance(position, torch.nn.Parameter):
            self.register_parameter("position", position)
            return
        self.register_buffer("position", position)

    @property
    def _position_value(self) -> torch.Tensor:
        return _read_named_parameter_or_buffer(self, name="position")

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
            "point_source_unit_envelope",
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
            cache_identity(self._position_value),
            str(wavelengths.device),
            str(self._fixed_complex_dtype()),
        )

    def _validate_point_source_applicability(
        self,
        wavelengths: torch.Tensor,
        refractive_indices: torch.Tensor,
        grid: SpatialGrid,
    ) -> None:
        position = self._position_value
        source_z = position[2]
        is_z_finite = torch.isfinite(source_z)
        if is_value_readable(is_z_finite) and not bool(is_z_finite):
            message = (
                "点源的轴向位置必须是有限实数，"
                f"收到的 z 分量是 {source_z!r}"
            )
            raise _errors.OpticalValueError(
                "point_source_position_invalid",
                message,
            )
        is_zero = source_z == 0.0
        if is_value_readable(is_zero) and bool(is_zero):
            raise _errors.OpticalValueError(
                "point_source_origin_on_grid",
                "点源的轴向位置（grid 平面外的 z 分量）必须非零；"
                "落在网格所在平面上的点源会让球面波 1/r 振幅发散，"
                "请把点源移到网格平面之外。",
            )
        spacing_y = grid.signed_spacing[0]
        spacing_x = grid.signed_spacing[1]
        first_y, first_x = grid.first_sample_position
        real_dtype = wavelengths.dtype
        source_y = position[0].to(dtype=real_dtype)
        source_x = position[1].to(dtype=real_dtype)
        source_z_real = source_z.to(dtype=real_dtype)
        facts = point_source_sampling_fence(
            sample_counts=grid.sample_counts,
            signed_spacing=(spacing_y, spacing_x),
            first_sample_position=(first_y, first_x),
            wavelengths=wavelengths,
            refractive_indices=refractive_indices,
            source_position_yxz=(source_y, source_x, source_z_real),
        )
        is_sufficient = facts.is_sufficient
        if is_value_readable(is_sufficient) and not bool(is_sufficient):
            message = (
                "网格采样不足以分辨球面波相位：存在至少一对相邻样本（y 或 x）与光谱"
                f"使 per-sample 周期增量 |Δcycles| 达到或超过半周期阈值 "
                f"{facts.half_cycle_threshold!r}。"
                f"窗口内 y 轴最坏 |Δcycles| ≈ {facts.worst_y_cycles_per_sample!r}，"
                f"x 轴最坏 |Δcycles| ≈ {facts.worst_x_cycles_per_sample!r}。"
                f"源位置 (y, x, z) ≈ ({source_y!r}, {source_x!r}, {source_z_real!r})。"
                "请提高网格密度、增大点源到网格平面的距离，或收窄有效窗口。"
            )
            raise _errors.OpticalValueError(
                "point_source_sampling_insufficient",
                message,
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
        self._validate_point_source_applicability(wavelengths, indices, grid)
        position = self._position_value.to(device=device, dtype=real_dtype)
        source_y = position[0]
        source_x = position[1]
        source_z = position[2]
        polarization_state = self._buffer("polarization_state").to(
            device=device,
            dtype=complex_dtype,
        )
        return point_source_unit_envelope(
            sample_counts=grid.sample_counts,
            signed_spacing=grid.signed_spacing,
            first_sample_position=grid.first_sample_position,
            wavelengths=wavelengths,
            refractive_indices=indices,
            source_position_yxz=(source_y, source_x, source_z),
            is_inverse_distance=(
                self._normalization is FieldNormalization.POWER
            ),
            polarization_state=polarization_state,
        )

    def _validate_physical_state(self) -> None:
        _materialize_point_source_position(self._position_value)
        scale_name = (
            "total_power"
            if self._normalization is FieldNormalization.POWER
            else "relative_amplitude"
        )
        self._validate_scale(name=scale_name, value=self._scale_value)

    def _power_amplitude(self, grid: SpatialGrid) -> torch.Tensor:
        # 由总功率与单位包络模方导出标量振幅，使空间积分给出声明总功率
        total_power = self._scale_value
        weights = self._buffer("spectral_weights")
        # 源边界守护：全零权重使功率无处分配，以稳定身份拒绝而非输出非有限包络
        if sum(self._spectrum_value.weights) <= 0.0:
            raise _errors.OpticalValueError(
                "point_source_total_power_spectrum_weight_sum_invalid",
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

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, NamedTuple, cast

import torch

from chromatix_next._numerics.plane_wave import (
    plane_wave_envelope,
    power_normalized_amplitude,
)
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
    _register_named_physical_state,
    _SourceStatePlan,
    _validate_source_physical_buffer_projection,
)
from ..field import (
    FieldNormalization,
    OpticalField,
    PropagationDirection,
    TransverseWavevector,
    _SourceLineage,
)
from ..grid import SpatialGrid, _is_centered_grid
from ..medium import Medium, Vacuum
from ..polarization import Polarization
from ..spectrum import Spectrum

_SCALE_TENSOR_MESSAGE = (
    "可训练的归一化取值必须是正的有限实数标量，不能是复数或多分量张量，"
    "收到的是 {value!r}"
)

_SCALE_SCALAR_MESSAGE = (
    "平面波的归一化取值必须是正的有限实数，零和负数没有物理意义，"
    "收到的是 {value!r}"
)



def _encode_plane_wave_extra_state(source: PlaneWave) -> dict[str, object]:
    payload = _encode_source_identity_fields(
        spectrum=source._spectrum_value,
        polarization=source._polarization_value,
        medium_identity=source._medium_value.physical_identity(),
    )
    payload["direction_kind"] = (
        "propagation" if source._is_propagation_direction_kind else "transverse"
    )
    payload["normalization"] = source._normalization.value
    return payload


def _plan_plane_wave_state_installation(
    source: PlaneWave,
    state: object,
    *,
    projected_buffers: Mapping[str, torch.Tensor] | None = None,
) -> _SourceStatePlan:
    try:
        payload = cast(dict[str, object], state)
        spectrum, polarization, medium_identity, normalization = (
            _decode_wave_extra_state_fields(payload)
        )
        direction_kind = cast(str, payload["direction_kind"])
    except (KeyError, TypeError, ValueError) as error:
        raise _errors.OpticalRuntimeError(
            "plane_wave_extra_state_invalid",
            "平面波的附加状态缺字段或字段类型不对，无法恢复物理身份",
        ) from error
    expected_direction_kind = (
        "propagation" if source._is_propagation_direction_kind else "transverse"
    )
    if (
        medium_identity != source._medium_value.physical_identity()
        or direction_kind != expected_direction_kind
        or normalization != source._normalization.value
    ):
        raise _errors.OpticalRuntimeError(
            "plane_wave_extra_state_structure_mismatch",
            "载入的介质、方向表达或归一化与当前平面波不一致；"
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
        error_identity="plane_wave_extra_state_buffer_mismatch",
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


class _DirectionSpec(NamedTuple):

    """
    承载平面波传播方向的互斥参数化

    """

    kind: Literal["propagation", "transverse"]
    component_y: torch.Tensor
    component_x: torch.Tensor


class PlaneWave(_SampledWaveSource):
    """
    在横向网格上产生归一化平面波包络的源组件

    Args:
        spectrum: 光谱采样、权重与波长语义
        polarization: 发射光的偏振表示与分量
        medium: 光所在位置的折射率模型
        propagation_direction: 平面波相对网格法向的传播方向
        transverse_wavevector: 平面波的横向波矢参数化
        relative_amplitude: 各光谱与偏振分量的相对复振幅
        total_power: 源在整个采样面上的总功率

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    _encode_extra_state_payload = staticmethod(_encode_plane_wave_extra_state)
    _plan_state_installation = staticmethod(_plan_plane_wave_state_installation)

    @property
    def role(self) -> _SourceRole:
        """
        源角色字面量

        Returns:
            返回该 Source 组件的稳定角色标识 "source"

        """

        return "source"

    def __init__(
        self,
        *,
        spectrum: Spectrum,
        polarization: Polarization,
        medium: Medium = Vacuum(),
        propagation_direction: PropagationDirection | None = None,
        transverse_wavevector: TransverseWavevector | None = None,
        relative_amplitude: float | torch.nn.Parameter | None = None,
        total_power: float | torch.nn.Parameter | None = None,
    ) -> None:
        super().__init__()
        self._source_lineage = _SourceLineage()
        self._validate_normalization_exclusive(relative_amplitude, total_power)
        self._validate_physical_values(spectrum, polarization, medium)
        self._validate_direction_specification(
            propagation_direction,
            transverse_wavevector,
        )

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

        if propagation_direction is not None:
            self._is_propagation_direction_kind = True
            self.register_buffer(
                "direction_cosine_y",
                torch.tensor(
                    float(propagation_direction.direction_cosine_y),
                    dtype=torch.float64,
                ),
            )
            self.register_buffer(
                "direction_cosine_x",
                torch.tensor(
                    float(propagation_direction.direction_cosine_x),
                    dtype=torch.float64,
                ),
            )
        else:
            assert transverse_wavevector is not None
            self._is_propagation_direction_kind = False
            self.register_buffer(
                "transverse_wavevector_y",
                torch.tensor(
                    float(transverse_wavevector.wavevector_y),
                    dtype=torch.float64,
                ),
            )
            self.register_buffer(
                "transverse_wavevector_x",
                torch.tensor(
                    float(transverse_wavevector.wavevector_x),
                    dtype=torch.float64,
                ),
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
            error_identity=f"plane_wave_{scale_name}_invalid",
            tensor_message=_SCALE_TENSOR_MESSAGE,
            scalar_message=_SCALE_SCALAR_MESSAGE,
        )

        self._register_unit_envelope_cache()

    def forward(self, grid: SpatialGrid) -> OpticalField:  # type: ignore[override]
        """
        在给定网格上计算平面波包络并返回归一化光场

        Args:
            grid: 定义采样位置与间距的空间网格

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        Raises:
            OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

        """
        if not isinstance(grid, SpatialGrid):
            raise _errors.OpticalTypeError(
                "plane_wave_grid_invalid",
                "平面波要在横向网格上取样才能给出包络，"
                f"收到的是 {type(grid).__name__}",
            )
        return self._synthesize_sampled_wave(grid)

    @staticmethod
    def _validate_normalization_exclusive(
        relative_amplitude: object,
        total_power: object,
    ) -> None:
        is_exactly_one = (relative_amplitude is not None) ^ (total_power is not None)
        if not is_exactly_one:
            if relative_amplitude is not None:
                raise _errors.OpticalValueError(
                    "plane_wave_normalization_exclusive",
                    "同一束平面波的幅值只能有一种归一化，"
                    "相对幅值与总功率请删去其一，"
                    f"收到的是 {relative_amplitude!r} 与 {total_power!r}",
                )
            raise _errors.OpticalValueError(
                "plane_wave_normalization_missing",
                "平面波的幅值必须由一种归一化定出，"
                "请在相对幅值与总功率里任选其一给出，两者都没有收到",
            )

    @staticmethod
    def _validate_physical_values(
        spectrum: object,
        polarization: object,
        medium: object,
    ) -> None:
        if not isinstance(spectrum, Spectrum):
            raise _errors.OpticalTypeError(
                "plane_wave_spectrum_invalid",
                "平面波的光谱必须由波长与权重成对给出，"
                f"收到的是 {type(spectrum).__name__}",
            )
        if not isinstance(polarization, Polarization):
            raise _errors.OpticalTypeError(
                "plane_wave_polarization_invalid",
                "平面波的偏振必须是归一化的琼斯状态，分量不由名称猜测，"
                f"收到的是 {type(polarization).__name__}",
            )
        if not isinstance(medium, Medium):
            raise _errors.OpticalTypeError(
                "plane_wave_medium_invalid",
                "平面波的折射率只从所在介质取得，不另行接受折射率参数，"
                f"收到的介质是 {type(medium).__name__}",
            )

    @staticmethod
    def _validate_direction_specification(
        propagation_direction: object,
        transverse_wavevector: object,
    ) -> None:
        is_exactly_one = (propagation_direction is not None) ^ (
            transverse_wavevector is not None
        )
        if not is_exactly_one:
            if propagation_direction is not None:
                raise _errors.OpticalValueError(
                    "plane_wave_direction_specification_exclusive",
                    "同一束平面波的方向只能有一种表达，"
                    "传播方向与横向波矢请删去其一，"
                    f"收到的是 {propagation_direction!r} "
                    f"与 {transverse_wavevector!r}",
                )
            raise _errors.OpticalValueError(
                "plane_wave_direction_specification_missing",
                "平面波朝哪里传播必须显式声明，"
                "请在传播方向与横向波矢里任选其一给出，两者都没有收到",
            )
        if (
            propagation_direction is not None
            and not isinstance(propagation_direction, PropagationDirection)
        ):
            raise _errors.OpticalTypeError(
                "plane_wave_propagation_direction_invalid",
                "传播方向必须由一对方向余弦给出，各光谱分量共用它，"
                f"收到的是 {type(propagation_direction).__name__}",
            )
        if (
            transverse_wavevector is not None
            and not isinstance(transverse_wavevector, TransverseWavevector)
        ):
            raise _errors.OpticalTypeError(
                "plane_wave_transverse_wavevector_invalid",
                "横向波矢必须由纵横两个分量给出，各光谱分量共用它，"
                f"收到的是 {type(transverse_wavevector).__name__}",
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
            error_identity=f"plane_wave_{name}_invalid",
            tensor_message=_SCALE_TENSOR_MESSAGE,
            scalar_message=_SCALE_SCALAR_MESSAGE,
        )

    def _direction_spec(self) -> _DirectionSpec:
        if self._is_propagation_direction_kind:
            return _DirectionSpec(
                "propagation",
                self._buffer("direction_cosine_y"),
                self._buffer("direction_cosine_x"),
            )
        return _DirectionSpec(
            "transverse",
            self._buffer("transverse_wavevector_y"),
            self._buffer("transverse_wavevector_x"),
        )

    def _unit_envelope_cache_key_for(self, grid: SpatialGrid) -> tuple[Any, ...]:
        wavelengths = self._buffer("wavelengths")
        weights = self._buffer("spectral_weights")
        polarization = self._buffer("polarization_state")
        if not is_value_readable(wavelengths):
            return (object(),)
        direction = self._direction_spec()
        direction_kind = direction.kind
        direction_y = direction.component_y
        direction_x = direction.component_x
        position_identity: tuple[object, ...]
        if _is_centered_grid(grid):
            position_identity = ("centered",)
        else:
            position_identity = tuple(
                cache_identity(value)
                for value in grid.first_sample_position
            )
        return (
            "plane_wave_unit_envelope",
            grid.sample_counts,
            tuple(cache_identity(value) for value in grid.sample_spacing),
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
            direction_kind,
            cache_identity(direction_y),
            cache_identity(direction_x),
            str(wavelengths.device),
            str(self._fixed_complex_dtype()),
        )

    def _compute_unit_envelope(self, grid: SpatialGrid) -> torch.Tensor:
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
        direction = self._direction_spec()
        if direction.kind == "propagation":
            propagation_direction = (
                direction.component_y.to(device=device, dtype=real_dtype),
                direction.component_x.to(device=device, dtype=real_dtype),
            )
            transverse_wavevector = None
        else:
            propagation_direction = None
            transverse_wavevector = (
                direction.component_y.to(device=device, dtype=real_dtype),
                direction.component_x.to(device=device, dtype=real_dtype),
            )
        polarization_state = self._buffer("polarization_state").to(
            device=device,
            dtype=complex_dtype,
        )
        return plane_wave_envelope(
            sample_counts=grid.sample_counts,
            signed_spacing=grid.signed_spacing,
            first_sample_position=grid.first_sample_position,
            wavelengths=wavelengths,
            refractive_indices=indices,
            polarization_state=polarization_state,
            propagation_direction=propagation_direction,
            transverse_wavevector=transverse_wavevector,
        )

    def _validate_physical_state(self) -> None:
        name = (
            "total_power"
            if self._normalization is FieldNormalization.POWER
            else "relative_amplitude"
        )
        self._validate_scale(name=name, value=self._scale_value)

    def _power_amplitude(self, grid: SpatialGrid) -> torch.Tensor:
        total_power = self._scale_value
        weights = self._buffer("spectral_weights")
        if sum(self._spectrum_value.weights) <= 0.0:
            raise _errors.OpticalValueError(
                "plane_wave_total_power_spectrum_weight_sum_invalid",
                "按总功率归一化时光谱权重之和必须为正，否则功率无处分配，"
                f"收到的权重是 {self._spectrum_value.weights!r}",
            )
        return power_normalized_amplitude(
            total_power=total_power,
            spectral_weights=weights,
            sample_counts=grid.sample_counts,
            cell_area=grid.cell_area,
        )

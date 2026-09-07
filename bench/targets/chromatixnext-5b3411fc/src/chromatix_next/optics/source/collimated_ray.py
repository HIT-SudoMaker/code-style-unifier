from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import torch

from chromatix_next._numerics.collimated_ray_source import collimated_launch_positions
from chromatix_next._numerics.ray_polarization import (
    embed_collimated_polarization_in_global_frame,
)
from chromatix_next._tensors import (
    _REAL_DTYPE,
    _register_fixed_double_scalar_parameter_or_buffer,
    _validate_fixed_double_real_scalar,
)
import chromatix_next.errors as _errors

from .._orthonormal_basis import (
    _materialize_authored_three_vector,
    _require_authored_orthonormal_basis,
    _require_authored_unit_three_vector,
)
from .._role_contract import _SourceRole
from .._source_lifecycle import (
    _decode_polarization_block,
    _decode_spectrum_block,
    _encode_source_identity_fields,
    _LifecycleSource,
    _read_named_parameter_or_buffer,
    _register_named_physical_state,
    _SourceStatePlan,
    _validate_source_physical_buffer_projection,
)
from ..field import _SourceLineage
from ..grid import SpatialGrid
from ..medium import ConstantMedium, Medium, Vacuum
from ..polarization import Polarization, PolarizationRepresentation
from ..ray_bundle import RAY_STATUS_ACTIVE, RayBundle
from ..spectrum import Spectrum

_COLLIMATED_THREE_VECTOR_TENSOR_REQUIREMENT = (
    "必须是长度为 3 的有限 float64 实张量"
)
_COLLIMATED_THREE_VECTOR_TUPLE_REQUIREMENT = (
    "必须是三个有限实数构成的元组"
)



def _collimated_scale_messages(name: str) -> dict[str, str]:
    return {
        "tensor_message": (
            f"准直光线源的 {name} 必须是正的有限实数标量，"
            "不能是复数或多分量张量，收到的是 {value!r}"
        ),
        "scalar_message": (
            f"准直光线源的 {name} 必须是正的有限实数，零和负数没有物理意义，"
            "收到的是 {value!r}"
        ),
        "non_parameter_tensor_message": (
            f"准直光线源的 {name} 作为张量提供时必须是 torch.nn.Parameter；"
            "若不需要训练请传 Python 标量，收到的是 {value!r}"
        ),
    }


def _encode_collimated_ray_source_extra_state(
    source: CollimatedRaySource,
) -> dict[str, object]:
    return _encode_source_identity_fields(
        spectrum=source._spectrum_value,
        polarization=source._polarization_value,
        medium_identity=source._medium_value.physical_identity(),
    )


def _plan_collimated_ray_source_state_installation(
    source: CollimatedRaySource,
    state: object,
    *,
    projected_buffers: Mapping[str, torch.Tensor] | None = None,
) -> _SourceStatePlan:
    try:
        payload = cast(dict[str, object], state)
        spectrum = _decode_spectrum_block(cast(dict[str, object], payload["spectrum"]))
        polarization = _decode_polarization_block(
            cast(dict[str, object], payload["polarization"]),
        )
        medium_identity = cast(tuple[Any, ...], payload["medium_identity"])
    except (KeyError, TypeError, ValueError) as error:
        raise _errors.OpticalRuntimeError(
            "collimated_ray_source_extra_state_invalid",
            "准直源的附加状态缺字段或字段类型不对，无法恢复物理身份",
        ) from error
    if polarization.representation is not PolarizationRepresentation.TRANSVERSE:
        raise _errors.OpticalRuntimeError(
            "collimated_ray_source_extra_state_structure_mismatch",
            "载入的偏振表示不是横向（transverse），"
            "准直光线源只接受横向琼斯偏振",
        )
    if medium_identity != source._medium_value.physical_identity():
        raise _errors.OpticalRuntimeError(
            "collimated_ray_source_extra_state_structure_mismatch",
            "载入的介质身份与当前准直源不一致；"
            "状态字典只能载回结构相同的光源",
        )
    projected_buffer_values = {
        buffer_name: source._buffer(buffer_name)
        for buffer_name in (
            "wavelengths",
            "spectral_weights",
            "polarization_state",
            "launch_origin",
            "launch_tangent_x",
            "launch_tangent_y",
        )
    }
    if projected_buffers is not None:
        projected_buffer_values.update(projected_buffers)
    _validate_collimated_launch_pose_values(
        launch_origin=projected_buffer_values["launch_origin"],
        launch_tangent_x=projected_buffer_values["launch_tangent_x"],
        launch_tangent_y=projected_buffer_values["launch_tangent_y"],
    )
    _validate_source_physical_buffer_projection(
        spectrum=spectrum,
        polarization=polarization,
        wavelengths=projected_buffer_values["wavelengths"],
        spectral_weights=projected_buffer_values["spectral_weights"],
        polarization_state=projected_buffer_values["polarization_state"],
        error_identity="collimated_ray_source_extra_state_buffer_mismatch",
    )
    return _SourceStatePlan(
        spectrum=spectrum,
        polarization=polarization,
        buffer_shapes=(
            ("wavelengths", torch.Size((spectrum.count,))),
            ("spectral_weights", torch.Size((spectrum.count,))),
            ("polarization_state", torch.Size((2,))),
        ),
        invalidate_envelope_cache=False,
    )


def _require_unit_vector(
    value: torch.Tensor,
    *,
    field_name: str,
    error_identity: str,
) -> None:
    _require_authored_unit_three_vector(
        value,
        error_identity=error_identity,
        message=(
            f"{field_name} 必须是单位向量，源不会静默归一化 authored 物理，"
            f"收到的是 {value!r}"
        ),
    )


def _require_collimated_launch_orthonormal_basis(
    tangent_x: torch.Tensor,
    tangent_y: torch.Tensor,
) -> None:
    _require_authored_orthonormal_basis(
        tangent_x,
        tangent_y,
        not_orthogonal_identity=(
            "collimated_ray_source_launch_basis_not_orthogonal"
        ),
        not_orthogonal_message=(
            "发射面的两个切向量必须正交，源不会静默旋转 authored 平面，"
            f"收到的 tangent_x 是 {tangent_x!r}，tangent_y 是 {tangent_y!r}"
        ),
    )


def _validate_collimated_launch_pose_values(
    *,
    launch_origin: object,
    launch_tangent_x: object,
    launch_tangent_y: object,
) -> None:

    origin = _materialize_authored_three_vector(
        launch_origin,
        field_name="发射原点",
        error_identity="collimated_ray_source_launch_origin_invalid",
        tensor_requirement=_COLLIMATED_THREE_VECTOR_TENSOR_REQUIREMENT,
        tuple_requirement=_COLLIMATED_THREE_VECTOR_TUPLE_REQUIREMENT,
    )
    tangent_x = _materialize_authored_three_vector(
        launch_tangent_x,
        field_name="发射 tangent_x",
        error_identity="collimated_ray_source_launch_tangent_x_invalid",
        tensor_requirement=_COLLIMATED_THREE_VECTOR_TENSOR_REQUIREMENT,
        tuple_requirement=_COLLIMATED_THREE_VECTOR_TUPLE_REQUIREMENT,
    )
    tangent_y = _materialize_authored_three_vector(
        launch_tangent_y,
        field_name="发射 tangent_y",
        error_identity="collimated_ray_source_launch_tangent_y_invalid",
        tensor_requirement=_COLLIMATED_THREE_VECTOR_TENSOR_REQUIREMENT,
        tuple_requirement=_COLLIMATED_THREE_VECTOR_TUPLE_REQUIREMENT,
    )
    _require_unit_vector(
        tangent_x,
        field_name="发射 tangent_x",
        error_identity="collimated_ray_source_launch_tangent_x_not_unit",
    )
    _require_unit_vector(
        tangent_y,
        field_name="发射 tangent_y",
        error_identity="collimated_ray_source_launch_tangent_y_not_unit",
    )
    _require_collimated_launch_orthonormal_basis(tangent_x, tangent_y)
    del origin


class CollimatedRaySource(_LifecycleSource):
    """
    把横向网格映射到全局 SI frame 的准直光线源组件

    Args:
        spectrum: 光谱采样、权重与波长语义
        polarization: 发射光的偏振表示与分量
        medium: 光所在位置的折射率模型
        launch_origin: 准直光线束中心光线的发射原点
        launch_tangent_x: 发射平面局部 x 切向量
        launch_tangent_y: 发射平面局部 y 切向量
        ray_power: 分配给每条采样光线的功率

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface

    """

    _encode_extra_state_payload = staticmethod(
        _encode_collimated_ray_source_extra_state
    )
    _plan_state_installation = staticmethod(
        _plan_collimated_ray_source_state_installation
    )

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
        launch_origin: tuple[float, float, float] | torch.Tensor = (
            0.0,
            0.0,
            0.0,
        ),
        launch_tangent_x: tuple[float, float, float] | torch.Tensor = (
            1.0,
            0.0,
            0.0,
        ),
        launch_tangent_y: tuple[float, float, float] | torch.Tensor = (
            0.0,
            1.0,
            0.0,
        ),
        ray_power: float | torch.nn.Parameter,
    ) -> None:
        super().__init__()
        self._source_lineage = _SourceLineage()
        self._validate_physical_values(spectrum, polarization, medium)

        origin = _materialize_authored_three_vector(
            launch_origin,
            field_name="发射面原点",
            error_identity=(
                "collimated_ray_source_launch_origin_invalid"
            ),
            tensor_requirement=_COLLIMATED_THREE_VECTOR_TENSOR_REQUIREMENT,
            tuple_requirement=_COLLIMATED_THREE_VECTOR_TUPLE_REQUIREMENT,
        )
        tangent_x = _materialize_authored_three_vector(
            launch_tangent_x,
            field_name="发射面 tangent_x",
            error_identity=(
                "collimated_ray_source_launch_tangent_x_invalid"
            ),
            tensor_requirement=_COLLIMATED_THREE_VECTOR_TENSOR_REQUIREMENT,
            tuple_requirement=_COLLIMATED_THREE_VECTOR_TUPLE_REQUIREMENT,
        )
        tangent_y = _materialize_authored_three_vector(
            launch_tangent_y,
            field_name="发射面 tangent_y",
            error_identity=(
                "collimated_ray_source_launch_tangent_y_invalid"
            ),
            tensor_requirement=_COLLIMATED_THREE_VECTOR_TENSOR_REQUIREMENT,
            tuple_requirement=_COLLIMATED_THREE_VECTOR_TUPLE_REQUIREMENT,
        )
        _require_unit_vector(
            tangent_x,
            field_name="发射面 tangent_x",
            error_identity=(
                "collimated_ray_source_launch_tangent_x_not_unit"
            ),
        )
        _require_unit_vector(
            tangent_y,
            field_name="发射面 tangent_y",
            error_identity=(
                "collimated_ray_source_launch_tangent_y_not_unit"
            ),
        )
        _require_collimated_launch_orthonormal_basis(tangent_x, tangent_y)
        self._register_scale("ray_power", ray_power)

        self._spectrum_value = spectrum
        self._polarization_value = polarization
        self._medium_value = medium
        _register_named_physical_state(
            self,
            spectrum=spectrum,
            polarization=polarization,
        )
        self.register_buffer("launch_origin", origin)
        self.register_buffer("launch_tangent_x", tangent_x)
        self.register_buffer("launch_tangent_y", tangent_y)

    def forward(self, grid: SpatialGrid) -> RayBundle:  # type: ignore[override]
        """
        在给定发射面网格上构造完整准直光线束

        Args:
            grid: 定义采样位置与间距的空间网格

        Returns:
            输出更新后的 RayBundle，保留射线状态和谱道顺序

        Raises:
            OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

        """
        if not isinstance(grid, SpatialGrid):
            message = (
                "准直光线源要在横向网格上取样才能给出光线位置，"
                f"收到的是 {type(grid).__name__}"
            )
            raise _errors.OpticalTypeError(
                "collimated_ray_source_grid_invalid",
                message,
            )
        self._validate_physical_state()
        device = self._buffer("wavelengths").device
        real_dtype = self._fixed_real_dtype()
        output_grid = grid.to(device=device, dtype=real_dtype)
        positions_two_dim = self._launch_positions_on_plane(output_grid)
        direction = self._launch_direction()
        ray_count = int(positions_two_dim.shape[0])
        spectral_count = self._spectrum_value.count
        position = positions_two_dim.unsqueeze(0).expand(
            spectral_count,
            ray_count,
            3,
        )
        direction_broadcast = direction.view(1, 1, 3).expand(
            spectral_count,
            ray_count,
            3,
        )
        power = self._scale_value.view(1, 1).expand(spectral_count, ray_count)
        wavelengths = self._buffer("wavelengths").to(
            device=device,
            dtype=real_dtype,
        )
        indices_per_wavelength = self._medium_value.refractive_index(
            wavelengths,
        ).to(device=device, dtype=real_dtype)
        refractive_index = indices_per_wavelength.view(spectral_count, 1).expand(
            spectral_count,
            ray_count,
        )
        optical_path = torch.zeros(
            (spectral_count, ray_count),
            dtype=torch.float64,
            device=device,
        )
        status = torch.full(
            (spectral_count, ray_count),
            RAY_STATUS_ACTIVE,
            dtype=torch.uint8,
            device=device,
        )
        jones_components = self._buffer("polarization_state").to(
            device=device,
            dtype=torch.complex128,
        )
        polarization_direction = embed_collimated_polarization_in_global_frame(
            jones_components=jones_components,
            launch_tangent_x=self._buffer("launch_tangent_x"),
            launch_tangent_y=self._buffer("launch_tangent_y"),
            reference=self._buffer("wavelengths").to(
                device=device,
                dtype=real_dtype,
            ),
        )
        polarization_vector = polarization_direction.view(1, 1, 3).expand(
            spectral_count,
            ray_count,
            3,
        )
        return RayBundle(
            position=position,
            direction=direction_broadcast,
            polarization_vector=polarization_vector,
            power=power,
            refractive_index=refractive_index,
            optical_path=optical_path,
            status=status,
            spectrum=self._spectrum_value,
        )

    def _validate_physical_state(self) -> None:
        self._validate_scale(name="ray_power", value=self._scale_value)
        _validate_collimated_launch_pose_values(
            launch_origin=self._buffer("launch_origin"),
            launch_tangent_x=self._buffer("launch_tangent_x"),
            launch_tangent_y=self._buffer("launch_tangent_y"),
        )

    @staticmethod
    def _validate_physical_values(
        spectrum: object,
        polarization: object,
        medium: object,
    ) -> None:
        if not isinstance(spectrum, Spectrum):
            message = (
                "准直光线源的光谱必须由波长与权重成对给出，"
                f"收到的是 {type(spectrum).__name__}"
            )
            raise _errors.OpticalTypeError(
                "collimated_ray_source_spectrum_invalid",
                message,
            )
        if not isinstance(polarization, Polarization):
            message = (
                "准直光线源必须显式给出一个横向琼斯偏振，"
                "源不会注入隐式默认偏振，"
                f"收到的是 {type(polarization).__name__}"
            )
            raise _errors.OpticalTypeError(
                "collimated_ray_source_polarization_invalid",
                message,
            )
        if (
            polarization.representation
            is not PolarizationRepresentation.TRANSVERSE
        ):
            message = (
                "准直光线源的偏振必须是横向（transverse）琼斯表示，"
                "标量与完整表示都不被支持，"
                f"收到的是 {polarization.representation.value!r}"
            )
            raise _errors.OpticalTypeError(
                "collimated_ray_source_polarization_representation_invalid",
                message,
            )
        if not isinstance(medium, Medium):
            message = (
                "准直光线源的折射率只从所在介质取得，"
                f"收到的介质是 {type(medium).__name__}"
            )
            raise _errors.OpticalTypeError(
                "collimated_ray_source_medium_invalid",
                message,
            )
        if not isinstance(medium, (Vacuum, ConstantMedium)):
            message = (
                "准直光线源初始模型只接受真空或恒定折射率介质，"
                "可训练色散介质不在支持范围内"
            )
            raise _errors.OpticalTypeError(
                "collimated_ray_source_medium_unsupported",
                message,
            )

    def _register_scale(
        self,
        name: str,
        value: float | torch.nn.Parameter,
    ) -> None:
        _register_fixed_double_scalar_parameter_or_buffer(
            self,
            name=name,
            value=value,
            is_positive=True,
            error_identity=f"collimated_ray_source_{name}_invalid",
            **_collimated_scale_messages(name),
        )

    @staticmethod
    def _validate_scale(
        *,
        name: str,
        value: object,
    ) -> None:
        messages = _collimated_scale_messages(name)
        _validate_fixed_double_real_scalar(
            value=value,
            is_positive=True,
            error_identity=f"collimated_ray_source_{name}_invalid",
            tensor_message=messages["tensor_message"],
            scalar_message=messages["scalar_message"],
        )

    def _buffer(self, name: str) -> torch.Tensor:
        candidate = self._buffers.get(name)
        assert candidate is not None
        return candidate

    @property
    def _scale_value(self) -> torch.Tensor:
        return _read_named_parameter_or_buffer(self, name="ray_power")

    def _fixed_real_dtype(self) -> torch.dtype:
        return _REAL_DTYPE

    def _launch_positions_on_plane(self, grid: SpatialGrid) -> torch.Tensor:
        device = self._buffer("wavelengths").device
        real_dtype = self._fixed_real_dtype()
        return collimated_launch_positions(
            sample_counts=grid.sample_counts,
            signed_spacing=grid.signed_spacing,
            first_sample_position=grid.first_sample_position,
            launch_origin=self._buffer("launch_origin"),
            launch_tangent_x=self._buffer("launch_tangent_x"),
            launch_tangent_y=self._buffer("launch_tangent_y"),
            reference=self._buffer("wavelengths").to(
                device=device,
                dtype=real_dtype,
            ),
        )

    def _launch_direction(self) -> torch.Tensor:
        device = self._buffer("wavelengths").device
        real_dtype = self._fixed_real_dtype()
        tangent_x = self._buffer("launch_tangent_x").to(
            device=device,
            dtype=real_dtype,
        )
        tangent_y = self._buffer("launch_tangent_y").to(
            device=device,
            dtype=real_dtype,
        )
        return torch.linalg.cross(tangent_x, tangent_y)

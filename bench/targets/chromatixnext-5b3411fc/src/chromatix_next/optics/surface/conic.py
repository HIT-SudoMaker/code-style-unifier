from __future__ import annotations

from collections.abc import Mapping
import math

import torch

from chromatix_next._numerics.surface_geometry.conic import conic_encounter
from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter
from chromatix_next._tensors import is_finite_fixed_double_scalar, is_value_readable
import chromatix_next.errors as _errors

from .._orthonormal_basis import _materialize_authored_three_vector
from ._pose_state import (
    _register_hard_aperture,
    _register_surface_pose,
    _require_positive_finite_scalar,
    _require_surface_orthonormal_basis,
    _require_unit_vector,
    _require_valid_surface_pose,
)

_SURFACE_THREE_VECTOR_TENSOR_REQUIREMENT = (
    "必须是长度为 3 的有限 float64 实张量"
)
_SURFACE_THREE_VECTOR_TUPLE_REQUIREMENT = "必须是三个有限实数构成的元组"


def _materialize_conic_even_coefficients(value: object) -> torch.Tensor:
    if isinstance(value, torch.Tensor):
        is_structure_invalid = value.dim() != 1 or value.dtype is not torch.float64
        is_value_invalid = False
        if not is_structure_invalid and is_value_readable(value):
            is_value_invalid = not bool(torch.isfinite(value).all())
        if not is_structure_invalid and not is_value_invalid:
            return value
        message = (
            "even_coefficients 必须是一维有限 float64 实张量，"
            f"收到的形状是 {tuple(value.shape)}、dtype 是 {value.dtype}"
        )
        raise _errors.OpticalValueError(
            "conic_even_coefficients_invalid",
            message,
        )
    if not isinstance(value, (tuple, list)) or any(
        isinstance(component, bool)
        or not isinstance(component, (int, float))
        or not math.isfinite(float(component))
        for component in value
    ):
        message = (
            "even_coefficients 必须是有限实数组成的 tuple 或 list，"
            f"收到的是 {value!r}"
        )
        raise _errors.OpticalValueError(
            "conic_even_coefficients_invalid",
            message,
        )
    return torch.tensor(
        tuple(float(component) for component in value),
        dtype=torch.float64,
    )

class ConicEvenAsphere(torch.nn.Module):
    """
    拥有全局姿态、曲率、圆锥常数与偶次系数的圆锥偶次非球面

    Args:
        vertex: 曲面顶点的空间位置
        tangent_x: 表面局部 x 方向的 authored 切向量
        tangent_y: 表面局部 y 方向的 authored 切向量
        curvature: 以长度倒数表示的顶点曲率
        conic_constant: 圆锥母面的无量纲圆锥常数
        even_coefficients: 按偶次径向幂排列的非球面系数
        clear_aperture_radius: 以表面局部坐标定义的通光孔径半径

    Raises:
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    vertex: torch.Tensor
    tangent_x: torch.Tensor
    tangent_y: torch.Tensor
    curvature: torch.Tensor
    conic_constant: torch.Tensor
    even_coefficients: torch.Tensor
    clear_aperture_radius: torch.Tensor

    def __init__(
        self,
        *,
        vertex: (
            tuple[float, float, float] | torch.Tensor | torch.nn.Parameter
        ) = (
            0.0,
            0.0,
            0.0,
        ),
        tangent_x: tuple[float, float, float] | torch.Tensor = (
            1.0,
            0.0,
            0.0,
        ),
        tangent_y: tuple[float, float, float] | torch.Tensor = (
            0.0,
            1.0,
            0.0,
        ),
        curvature: float | torch.nn.Parameter = 0.0,
        conic_constant: float | torch.nn.Parameter = 0.0,
        even_coefficients: (
            tuple[float, ...]
            | list[float]
            | torch.Tensor
            | torch.nn.Parameter
        ) = (),
        clear_aperture_radius: float | torch.Tensor | None = None,
    ) -> None:

        super().__init__()
        _register_surface_pose(
            self,
            surface_name="conic",
            origin=vertex,
            tangent_x=tangent_x,
            tangent_y=tangent_y,
        )
        self._register_curvature(curvature)
        self._register_conic_constant(conic_constant)
        self._register_even_coefficients(even_coefficients)
        self._register_aperture(
            "clear_aperture_radius",
            clear_aperture_radius,
        )
        self._validate_physical_state()

    @property
    def normal(self) -> torch.Tensor:
        """
        顶点处单位法线（tangent_x × tangent_y），定义面朝向与 sag 增长方向

        Returns:
            顶点处的 float64 单位法线张量

        """

        return torch.linalg.cross(self.tangent_x, self.tangent_y)

    def forward(self) -> None:  # type: ignore[override]
        """
        圆锥面是被动 state adapter，没有独立 forward 计算

        Raises:
            OpticalRuntimeError: 调用时的状态或拓扑不满足该 Interface 契约

        """

        raise _errors.OpticalRuntimeError(
            "conic_even_asphere_has_no_forward_action",
            "ConicEvenAsphere 是被动 Surface adapter，由 trace/refract/reflect action "
            "消费，不暴露独立 forward",
        )

    def _encounter(
        self,
        ray_origin: torch.Tensor,
        ray_direction: torch.Tensor,
    ) -> SurfaceEncounter:
        device = ray_origin.device
        real_dtype = ray_origin.dtype
        vertex = self.vertex.to(device=device, dtype=real_dtype)
        tangent_x = self.tangent_x.to(device=device, dtype=real_dtype)
        tangent_y = self.tangent_y.to(device=device, dtype=real_dtype)
        curvature = self.curvature.to(device=device, dtype=real_dtype)
        conic_constant = self.conic_constant.to(
            device=device,
            dtype=real_dtype,
        )
        even_coefficients = self.even_coefficients.to(
            device=device,
            dtype=real_dtype,
        )
        aperture = self._aperture_on(device=device, dtype=real_dtype)
        return conic_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            conic_vertex=vertex,
            conic_tangent_x=tangent_x,
            conic_tangent_y=tangent_y,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even_coefficients,
            clear_aperture_radius=aperture,
        )

    def _aperture_on(
        self,
        *,
        device: torch.device,
        dtype: torch.dtype,
    ) -> torch.Tensor | None:
        aperture = self._aperture_value
        if aperture is None:
            return None
        return aperture.to(device=device, dtype=dtype)

    def _register_curvature(self, value: float | torch.nn.Parameter) -> None:
        if isinstance(value, torch.nn.Parameter):
            if not is_finite_fixed_double_scalar(value):
                message = (
                    "curvature 作为可训练参数必须是有限实数标量，"
                    f"收到的是 {value!r}"
                )
                raise _errors.OpticalValueError(
                    "conic_curvature_invalid",
                    message,
                )
            self.register_parameter("curvature", value)
            return
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            message = (
                "curvature 必须是有限实数标量（曲率 = 1/R），"
                f"收到的是 {value!r}"
            )
            raise _errors.OpticalValueError(
                "conic_curvature_invalid",
                message,
            )
        self.register_buffer(
            "curvature",
            torch.tensor(float(value), dtype=torch.float64),
        )

    def _register_conic_constant(
        self,
        value: float | torch.nn.Parameter,
    ) -> None:
        if isinstance(value, torch.nn.Parameter):
            if not is_finite_fixed_double_scalar(value):
                message = (
                    "conic_constant 作为可训练参数必须是有限实数标量，"
                    f"收到的是 {value!r}"
                )
                raise _errors.OpticalValueError(
                    "conic_constant_invalid",
                    message,
                )
            self.register_parameter("conic_constant", value)
            return
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            message = (
                "conic_constant 必须是有限实数标量，"
                f"收到的是 {value!r}"
            )
            raise _errors.OpticalValueError(
                "conic_constant_invalid",
                message,
            )
        self.register_buffer(
            "conic_constant",
            torch.tensor(float(value), dtype=torch.float64),
        )

    def _register_even_coefficients(
        self,
        value: (
            tuple[float, ...]
            | list[float]
            | torch.Tensor
            | torch.nn.Parameter
        ),
    ) -> None:
        coefficients = _materialize_conic_even_coefficients(value)
        if isinstance(coefficients, torch.nn.Parameter):
            self.register_parameter("even_coefficients", coefficients)
            return
        self.register_buffer("even_coefficients", coefficients)

    def _register_aperture(
        self,
        name: str,
        value: float | torch.Tensor | None,
    ) -> None:
        _register_hard_aperture(
            self,
            name=name,
            value=value,
            owner_identity=f"conic_{name}_invalid",
        )

    def _validate_physical_state(self) -> None:
        _require_valid_surface_pose(
            surface_name="conic",
            origin=self.vertex,
            tangent_x=self.tangent_x,
            tangent_y=self.tangent_y,
        )
        if not is_finite_fixed_double_scalar(self.curvature):
            message = (
                "curvature 必须是有限实数标量（曲率 = 1/R），"
                f"收到的是 {self.curvature!r}"
            )
            raise _errors.OpticalValueError(
                "conic_curvature_invalid",
                message,
            )
        if not is_finite_fixed_double_scalar(self.conic_constant):
            message = (
                "conic_constant 必须是有限实数标量，"
                f"收到的是 {self.conic_constant!r}"
            )
            raise _errors.OpticalValueError(
                "conic_constant_invalid",
                message,
            )
        _materialize_conic_even_coefficients(self.even_coefficients)
        self._require_clear_aperture_for_even_asphere()
        aperture = self._aperture_value
        if aperture is None:
            return
        _require_positive_finite_scalar(
            aperture,
            field_name="clear_aperture_radius",
            error_identity="conic_clear_aperture_radius_invalid",
        )
        _require_aperture_inside_real_domain(
            curvature=self.curvature,
            conic_constant=self.conic_constant,
            aperture=aperture,
        )

    def _require_clear_aperture_for_even_asphere(self) -> None:
        if self.even_coefficients.numel() == 0:
            return
        if self._aperture_value is None:
            message = (
                "非空 even_coefficients 必须配合正有限 clear_aperture_radius："
                "多项式非球面求交证明依赖孔径柱面导出有限搜索区间"
            )
            raise _errors.OpticalValueError(
                "conic_even_asphere_clear_aperture_required",
                message,
            )

    @property
    def _aperture_value(self) -> torch.Tensor | None:
        candidate = self._parameters.get("clear_aperture_radius")
        if candidate is not None:
            return candidate
        return self._buffers.get("clear_aperture_radius")


def _validate_conic_state_installation(
    conic: ConicEvenAsphere,
    local_state: Mapping[str, object],
) -> None:
    del conic
    tangent_x = _required_local_tensor(local_state, "tangent_x")
    tangent_y = _required_local_tensor(local_state, "tangent_y")
    _require_unit_vector(
        tangent_x,
        field_name="圆锥面tangent_x",
        error_identity="conic_tangent_x_not_unit",
    )
    _require_unit_vector(
        tangent_y,
        field_name="圆锥面tangent_y",
        error_identity="conic_tangent_y_not_unit",
    )
    _require_surface_orthonormal_basis(
        tangent_x,
        tangent_y,
        not_orthogonal_identity="conic_basis_not_orthogonal",
    )
    vertex = _required_local_tensor(local_state, "vertex")
    _materialize_authored_three_vector(
        vertex,
        field_name="圆锥面顶点",
        error_identity="conic_vertex_invalid",
        tensor_requirement=_SURFACE_THREE_VECTOR_TENSOR_REQUIREMENT,
        tuple_requirement=_SURFACE_THREE_VECTOR_TUPLE_REQUIREMENT,
    )
    curvature = _required_local_tensor(local_state, "curvature")
    if not is_finite_fixed_double_scalar(curvature):
        message = "curvature 必须是有限实数标量，状态字典给出非法值"
        raise _errors.OpticalValueError(
            "conic_curvature_invalid",
            message,
        )
    conic_constant = _required_local_tensor(local_state, "conic_constant")
    if not is_finite_fixed_double_scalar(conic_constant):
        message = "conic_constant 必须是有限实数标量，状态字典给出非法值"
        raise _errors.OpticalValueError(
            "conic_constant_invalid",
            message,
        )
    coefficients = _required_local_tensor(local_state, "even_coefficients")
    _materialize_conic_even_coefficients(coefficients)
    aperture = local_state.get("clear_aperture_radius")
    if coefficients.numel() != 0 and aperture is None:
        message = (
            "非空 even_coefficients 必须配合正有限 clear_aperture_radius"
        )
        raise _errors.OpticalValueError(
            "conic_even_asphere_clear_aperture_required",
            message,
        )
    if aperture is None:
        return
    if not isinstance(aperture, torch.Tensor):
        message = "clear_aperture_radius 必须是张量标量，状态字典给出非法类型"
        raise _errors.OpticalTypeError(
            "conic_clear_aperture_radius_invalid",
            message,
        )
    _require_positive_finite_scalar(
        aperture,
        field_name="clear_aperture_radius",
        error_identity="conic_clear_aperture_radius_invalid",
    )
    _require_aperture_inside_real_domain(
        curvature=curvature,
        conic_constant=conic_constant,
        aperture=aperture,
    )


def _required_local_tensor(
    local_state: Mapping[str, object],
    name: str,
) -> torch.Tensor:
    value = local_state.get(name)
    if not isinstance(value, torch.Tensor):
        message = f"{name} 必须以张量形式出现在状态字典里，收到的是 {value!r}"
        raise _errors.OpticalTypeError(
            f"{name}_invalid",
            message,
        )
    return value


def _require_aperture_inside_real_domain(
    *,
    curvature: torch.Tensor,
    conic_constant: torch.Tensor,
    aperture: torch.Tensor,
) -> None:
    radicand_factor = (1.0 + conic_constant) * curvature * curvature
    if not is_value_readable(radicand_factor):
        return
    if not bool(radicand_factor > 0.0):
        return
    aperture_squared = aperture * aperture
    radicand = 1.0 - radicand_factor * aperture_squared
    if not is_value_readable(radicand):
        return
    if not bool(radicand >= 0.0):
        message = (
            "clear_aperture_radius 越过圆锥偶次非球面的实数域："
            "需 1 − (1+k)c²·R_a² ≥ 0"
        )
        raise _errors.OpticalValueError(
            "conic_even_asphere_aperture_outside_real_domain",
            message,
        )

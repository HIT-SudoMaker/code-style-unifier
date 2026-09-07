from __future__ import annotations

from enum import Enum
import math

import torch

import chromatix_next._numerics.cube_response as _cube_response
from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

from ._directional_geometry import (
    _derive_terminal_frame,
    _prepare_fixed_geometry_vector,
    _require_fixed_orthogonal_axes,
    _require_fixed_unit_vector,
    _TerminalFrame,
)

__all__ = [
    "CubeCoatingDiagonal",
    "CubeTerminal",
    "IdealNonpolarizingCubeBeamSplitter",
    "IdealPolarizingCubeBeamSplitter",
]


class CubeTerminal(str, Enum):
    """
    理想自由空间 Cube owner 的四个封闭物理 Terminal

    """

    LEFT = "left"
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"


class CubeCoatingDiagonal(str, Enum):
    """
    Cube 内部 coating plane 的两个封闭对角方向

    """

    RISING = "rising"
    FALLING = "falling"


_TERMINAL_ORDER = (
    CubeTerminal.LEFT,
    CubeTerminal.TOP,
    CubeTerminal.RIGHT,
    CubeTerminal.BOTTOM,
)

_TRANSMITTED_TERMINAL = {
    CubeTerminal.LEFT: CubeTerminal.RIGHT,
    CubeTerminal.TOP: CubeTerminal.BOTTOM,
    CubeTerminal.RIGHT: CubeTerminal.LEFT,
    CubeTerminal.BOTTOM: CubeTerminal.TOP,
}

_RISING_REFLECTED_TERMINAL = {
    CubeTerminal.LEFT: CubeTerminal.TOP,
    CubeTerminal.TOP: CubeTerminal.LEFT,
    CubeTerminal.RIGHT: CubeTerminal.BOTTOM,
    CubeTerminal.BOTTOM: CubeTerminal.RIGHT,
}

_FALLING_REFLECTED_TERMINAL = {
    CubeTerminal.LEFT: CubeTerminal.BOTTOM,
    CubeTerminal.TOP: CubeTerminal.RIGHT,
    CubeTerminal.RIGHT: CubeTerminal.TOP,
    CubeTerminal.BOTTOM: CubeTerminal.LEFT,
}

_RISING_REFLECTION_INPUT_INDICES = (1, 0, 3, 2)

_FALLING_REFLECTION_INPUT_INDICES = (3, 2, 1, 0)

def _prepare_cube_geometry(
    *,
    owner_label: str,
    origin: object,
    route_right: object,
    route_top: object,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    prepared_origin = _prepare_fixed_geometry_vector(
        origin,
        owner_label=owner_label,
        field_name="origin",
        identity_prefix="cube_geometry_origin",
    )
    prepared_route_right = _prepare_fixed_geometry_vector(
        route_right,
        owner_label=owner_label,
        field_name="route_right",
        identity_prefix="cube_geometry_route_right",
    )
    prepared_route_top = _prepare_fixed_geometry_vector(
        route_top,
        owner_label=owner_label,
        field_name="route_top",
        identity_prefix="cube_geometry_route_top",
    )
    _require_fixed_unit_vector(
        prepared_route_right,
        owner_label=owner_label,
        field_name="route_right",
        error_identity="cube_geometry_route_right_not_unit",
    )
    _require_fixed_unit_vector(
        prepared_route_top,
        owner_label=owner_label,
        field_name="route_top",
        error_identity="cube_geometry_route_top_not_unit",
    )
    _require_fixed_orthogonal_axes(
        prepared_route_right,
        prepared_route_top,
        owner_label=owner_label,
        first_name="route_right",
        second_name="route_top",
        error_identity="cube_geometry_axes_not_orthogonal",
    )
    return prepared_origin, prepared_route_right, prepared_route_top


def _prepare_coating_diagonal(
    coating_diagonal: object,
    *,
    owner_label: str,
) -> torch.Tensor:
    if not isinstance(coating_diagonal, CubeCoatingDiagonal):
        raise _errors.OpticalTypeError(
            "cube_coating_diagonal_invalid",
            f"{owner_label} 的 coating_diagonal 必须是 CubeCoatingDiagonal，"
            f"收到的是 {type(coating_diagonal).__name__}；请使用封闭枚举值",
        )
    code = 0 if coating_diagonal is CubeCoatingDiagonal.RISING else 1
    return torch.tensor(code, dtype=torch.uint8)


def _prepare_mixing_angle(value: object) -> torch.Tensor:
    if isinstance(value, torch.Tensor):
        if value.dtype is not torch.float64:
            raise _errors.OpticalTypeError(
                "cube_beam_splitter_mixing_angle_dtype_invalid",
                "IdealNonpolarizingCubeBeamSplitter 的 mixing_angle Tensor 必须是 "
                f"float64，收到的 dtype 是 {value.dtype}；请以 fixed-double 重建",
            )
        if value.shape != ():
            raise _errors.OpticalValueError(
                "cube_beam_splitter_mixing_angle_shape_invalid",
                "IdealNonpolarizingCubeBeamSplitter 的 mixing_angle 必须是零维标量，"
                f"收到的形状是 {tuple(value.shape)}；请移除批次或分量轴",
            )
        if is_value_readable(value) and not bool(torch.isfinite(value)):
            raise _errors.OpticalValueError(
                "cube_beam_splitter_mixing_angle_nonfinite",
                "IdealNonpolarizingCubeBeamSplitter 的 mixing_angle 必须是有限实数，"
                f"收到的是 {value!r}；请移除 NaN 或 Inf",
            )
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _errors.OpticalTypeError(
            "cube_beam_splitter_mixing_angle_type_invalid",
            "IdealNonpolarizingCubeBeamSplitter 的 mixing_angle 必须是 Python 实数、"
            "float64 Tensor 或 Parameter，"
            f"收到的是 {type(value).__name__}；请提供有限标量",
        )
    try:
        materialized = float(value)
    except OverflowError as error:
        raise _errors.OpticalValueError(
            "cube_beam_splitter_mixing_angle_nonfinite",
            "IdealNonpolarizingCubeBeamSplitter 的 mixing_angle 必须能表示为有限 "
            f"float64，收到的是 {value!r}；请缩小该标量",
        ) from error
    if not math.isfinite(materialized):
        raise _errors.OpticalValueError(
            "cube_beam_splitter_mixing_angle_nonfinite",
            "IdealNonpolarizingCubeBeamSplitter 的 mixing_angle 必须是有限实数，"
            f"收到的是 {value!r}；请移除 NaN 或 Inf",
        )
    return torch.tensor(materialized, dtype=torch.float64)


def _register_cube_state(
    owner: torch.nn.Module,
    *,
    origin: torch.Tensor,
    route_right: torch.Tensor,
    route_top: torch.Tensor,
    coating_diagonal_code: torch.Tensor,
) -> None:
    owner.register_buffer("origin", origin)
    owner.register_buffer("route_right", route_right)
    owner.register_buffer("route_top", route_top)
    owner.register_buffer("_coating_diagonal_code", coating_diagonal_code)


def _require_valid_diagonal_code(value: object, *, owner_label: str) -> None:
    is_structure_valid = (
        isinstance(value, torch.Tensor)
        and value.dtype is torch.uint8
        and value.shape == ()
    )
    is_value_valid = is_structure_valid and (
        not is_value_readable(value)
        or torch.equal(
            value,
            torch.zeros((), dtype=torch.uint8, device=value.device),
        )
        or torch.equal(
            value,
            torch.ones((), dtype=torch.uint8, device=value.device),
        )
    )
    if is_value_valid:
        return
    raise _errors.OpticalTypeError(
        "cube_coating_diagonal_invalid",
        f"{owner_label} 的持久 coating_diagonal 状态必须编码一个封闭枚举值；"
        "请从有效 owner checkpoint 恢复 rising 或 falling",
    )


def _coating_diagonal_from_code(value: torch.Tensor) -> CubeCoatingDiagonal:
    if value.is_meta:
        raise _errors.OpticalRuntimeError(
            "cube_beam_splitter_response_invariant_violated",
            "meta coating_diagonal 没有可读离散值；请在 Freeze 前从真实 owner 派生拓扑",
        )
    zero = torch.zeros((), dtype=torch.uint8, device=value.device)
    if torch.equal(value, zero):
        return CubeCoatingDiagonal.RISING
    return CubeCoatingDiagonal.FALLING


def _outward_direction(
    *,
    terminal: CubeTerminal,
    route_right: torch.Tensor,
    route_top: torch.Tensor,
) -> torch.Tensor:
    if terminal is CubeTerminal.LEFT:
        return -route_right
    if terminal is CubeTerminal.TOP:
        return route_top.clone()
    if terminal is CubeTerminal.RIGHT:
        return route_right.clone()
    return -route_top


def _reflection_map(
    diagonal: CubeCoatingDiagonal,
) -> dict[CubeTerminal, CubeTerminal]:
    if diagonal is CubeCoatingDiagonal.RISING:
        return _RISING_REFLECTED_TERMINAL
    return _FALLING_REFLECTED_TERMINAL


def _reflection_input_indices(
    diagonal: CubeCoatingDiagonal,
) -> tuple[int, int, int, int]:
    if diagonal is CubeCoatingDiagonal.RISING:
        return _RISING_REFLECTION_INPUT_INDICES
    return _FALLING_REFLECTION_INPUT_INDICES


def _derive_coating_normal(
    *,
    diagonal: CubeCoatingDiagonal,
    route_right: torch.Tensor,
    route_top: torch.Tensor,
) -> torch.Tensor:
    top_sign = -1.0 if diagonal is CubeCoatingDiagonal.RISING else 1.0
    candidate = route_right + top_sign * route_top
    return candidate / torch.linalg.vector_norm(candidate)


def _derive_coating_p_s_basis(
    *,
    direction: torch.Tensor,
    coating_normal: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    s_axis = torch.linalg.cross(coating_normal, direction)
    s_axis = s_axis / torch.linalg.vector_norm(s_axis)
    p_axis = torch.linalg.cross(direction, s_axis)
    return p_axis, s_axis


def _require_canonical_response_invariant(
    *,
    incident: torch.Tensor,
    outgoing: torch.Tensor,
    error_identity: str,
    owner_label: str,
) -> None:
    is_structurally_valid = (
        outgoing.shape == incident.shape
        and outgoing.dtype is incident.dtype
        and outgoing.device == incident.device
    )
    if not is_structurally_valid:
        raise _errors.OpticalRuntimeError(
            error_identity,
            f"{owner_label} 的闭合响应改变了内部模态结构；请恢复经资格验证的响应实现",
        )
    if incident.is_meta:
        return
    if not bool(torch.isfinite(incident).all()):
        return
    if not bool(torch.isfinite(outgoing).all()):
        raise _errors.OpticalRuntimeError(
            error_identity,
            f"{owner_label} 从有限输入产生了非有限响应；请恢复经资格验证的闭合代数",
        )
    if bool(
        _cube_response.closed_response_preserves_finite_power(
            incident_terminal_p_s_values=incident,
            outgoing_terminal_p_s_values=outgoing,
        )
    ):
        return
    raise _errors.OpticalRuntimeError(
        error_identity,
        f"{owner_label} 的闭合响应违反无损功率不变量；请恢复反射 i 相位与封闭拓扑",
    )


def _require_canonical_response_input(value: torch.Tensor) -> None:
    if (
        not isinstance(value, torch.Tensor)
        or value.dtype is not torch.complex128
        or value.shape[-2:] != (4, 2)
    ):
        raise _errors.OpticalRuntimeError(
            "cube_beam_splitter_response_invariant_violated",
            "private Cube response 只接受 complex128 [..., 4, 2] Terminal p/s 值；"
            "请恢复经资格验证的 Encounter adapter",
        )


class IdealNonpolarizingCubeBeamSplitter(torch.nn.Module):
    """
    拥有固定四 Terminal 几何与唯一混合角的理想无损 NBS Cube

    Args:
        origin: owner 原点，单位为米
        route_right: 从原点指向 right Terminal 的固定单位方向
        route_top: 从原点指向 top Terminal 且与 route_right 正交的固定单位方向
        coating_diagonal: rising 或 falling 封闭 coating 对角方向
        mixing_angle: 完整无损响应的唯一有限实数混合角

    Raises:
        OpticalTypeError: 几何、对角方向或混合角的类型/dtype 不符合契约
        OpticalValueError: 几何、对角方向或混合角的形状/有限性/单位性不符合契约

    """

    origin: torch.Tensor
    route_right: torch.Tensor
    route_top: torch.Tensor
    mixing_angle: torch.Tensor
    _coating_diagonal_code: torch.Tensor

    def __init__(
        self,
        *,
        origin: tuple[float, float, float] | torch.Tensor,
        route_right: tuple[float, float, float] | torch.Tensor,
        route_top: tuple[float, float, float] | torch.Tensor,
        coating_diagonal: CubeCoatingDiagonal,
        mixing_angle: float | torch.Tensor | torch.nn.Parameter,
    ) -> None:
        super().__init__()
        prepared_origin, prepared_route_right, prepared_route_top = (
            _prepare_cube_geometry(
                owner_label=type(self).__name__,
                origin=origin,
                route_right=route_right,
                route_top=route_top,
            )
        )
        prepared_diagonal = _prepare_coating_diagonal(
            coating_diagonal,
            owner_label=type(self).__name__,
        )
        prepared_mixing_angle = _prepare_mixing_angle(mixing_angle)
        _register_cube_state(
            self,
            origin=prepared_origin,
            route_right=prepared_route_right,
            route_top=prepared_route_top,
            coating_diagonal_code=prepared_diagonal,
        )
        if isinstance(prepared_mixing_angle, torch.nn.Parameter):
            self.register_parameter("mixing_angle", prepared_mixing_angle)
        else:
            self.register_buffer("mixing_angle", prepared_mixing_angle)

    @property
    def coating_diagonal(self) -> CubeCoatingDiagonal:
        """
        返回持久离散状态所表示的 coating 对角方向

        Returns:
            当前 owner 的 rising 或 falling 封闭枚举值

        Raises:
            OpticalTypeError: 持久离散状态不再编码封闭 coating 对角方向

        """
        _require_valid_diagonal_code(
            self._coating_diagonal_code,
            owner_label=type(self).__name__,
        )
        return _coating_diagonal_from_code(self._coating_diagonal_code)

    def forward(self) -> None:  # type: ignore[override]
        """
        拒绝脱离 Assembly Encounter 的独立 owner 执行

        Raises:
            OpticalRuntimeError: directional owner 没有 standalone forward action

        """
        raise _errors.OpticalRuntimeError(
            "ideal_nonpolarizing_cube_beam_splitter_has_no_forward_action",
            "IdealNonpolarizingCubeBeamSplitter 是 state-only directional owner；"
            "请在 Assembly 中声明 WaveEncounter 或 RayEncounter",
        )

    def _canonical_response(
        self,
        incident_terminal_p_s_values: torch.Tensor,
    ) -> torch.Tensor:
        _require_canonical_response_input(incident_terminal_p_s_values)
        self._validate_physical_state()
        outgoing = _cube_response.apply_closed_nonpolarizing_cube_response(
            incident_terminal_p_s_values=incident_terminal_p_s_values,
            mixing_angle=self.mixing_angle,
            reflection_input_indices=_reflection_input_indices(
                self.coating_diagonal
            ),
        )
        _require_canonical_response_invariant(
            incident=incident_terminal_p_s_values,
            outgoing=outgoing,
            error_identity="cube_beam_splitter_response_invariant_violated",
            owner_label=type(self).__name__,
        )
        return outgoing

    def _coating_normal(self) -> torch.Tensor:
        self._validate_physical_state()
        return _derive_coating_normal(
            diagonal=self.coating_diagonal,
            route_right=self.route_right,
            route_top=self.route_top,
        )

    def _coating_p_s_basis(
        self,
        direction: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        normal = self._coating_normal().to(
            device=direction.device,
            dtype=direction.dtype,
        )
        return _derive_coating_p_s_basis(
            direction=direction,
            coating_normal=normal,
        )

    def _reflected_terminal(
        self,
        incident_terminal: CubeTerminal,
    ) -> CubeTerminal:
        return _reflection_map(self.coating_diagonal)[incident_terminal]

    def _terminal_frame(self, terminal: CubeTerminal) -> _TerminalFrame:
        self._validate_physical_state()
        vertical = torch.linalg.cross(self.route_right, self.route_top)
        return _derive_terminal_frame(
            origin=self.origin,
            outward_direction=_outward_direction(
                terminal=terminal,
                route_right=self.route_right,
                route_top=self.route_top,
            ),
            vertical_direction=vertical,
        )

    def _transmitted_terminal(
        self,
        incident_terminal: CubeTerminal,
    ) -> CubeTerminal:
        return _TRANSMITTED_TERMINAL[incident_terminal]

    def _validate_physical_state(self) -> None:
        _prepare_cube_geometry(
            owner_label=type(self).__name__,
            origin=self.origin,
            route_right=self.route_right,
            route_top=self.route_top,
        )
        _require_valid_diagonal_code(
            self._coating_diagonal_code,
            owner_label=type(self).__name__,
        )
        _prepare_mixing_angle(self.mixing_angle)


class IdealPolarizingCubeBeamSplitter(torch.nn.Module):
    """
    拥有固定四 Terminal 几何且无泄漏参数的理想 p 透射、s 反射 PBS Cube

    Args:
        origin: owner 原点，单位为米
        route_right: 从原点指向 right Terminal 的固定单位方向
        route_top: 从原点指向 top Terminal 且与 route_right 正交的固定单位方向
        coating_diagonal: rising 或 falling 封闭 coating 对角方向

    Raises:
        OpticalTypeError: 几何或对角方向的类型/dtype 不符合契约
        OpticalValueError: 几何或对角方向的形状/有限性/单位性不符合契约

    """

    origin: torch.Tensor
    route_right: torch.Tensor
    route_top: torch.Tensor
    _coating_diagonal_code: torch.Tensor

    def __init__(
        self,
        *,
        origin: tuple[float, float, float] | torch.Tensor,
        route_right: tuple[float, float, float] | torch.Tensor,
        route_top: tuple[float, float, float] | torch.Tensor,
        coating_diagonal: CubeCoatingDiagonal,
    ) -> None:
        super().__init__()
        prepared_origin, prepared_route_right, prepared_route_top = (
            _prepare_cube_geometry(
                owner_label=type(self).__name__,
                origin=origin,
                route_right=route_right,
                route_top=route_top,
            )
        )
        prepared_diagonal = _prepare_coating_diagonal(
            coating_diagonal,
            owner_label=type(self).__name__,
        )
        _register_cube_state(
            self,
            origin=prepared_origin,
            route_right=prepared_route_right,
            route_top=prepared_route_top,
            coating_diagonal_code=prepared_diagonal,
        )

    @property
    def coating_diagonal(self) -> CubeCoatingDiagonal:
        """
        返回持久离散状态所表示的 coating 对角方向

        Returns:
            当前 owner 的 rising 或 falling 封闭枚举值

        Raises:
            OpticalTypeError: 持久离散状态不再编码封闭 coating 对角方向

        """
        _require_valid_diagonal_code(
            self._coating_diagonal_code,
            owner_label=type(self).__name__,
        )
        return _coating_diagonal_from_code(self._coating_diagonal_code)

    def forward(self) -> None:  # type: ignore[override]
        """
        拒绝脱离 Assembly Encounter 的独立 owner 执行

        Raises:
            OpticalRuntimeError: directional owner 没有 standalone forward action

        """
        raise _errors.OpticalRuntimeError(
            "ideal_polarizing_cube_beam_splitter_has_no_forward_action",
            "IdealPolarizingCubeBeamSplitter 是 state-only directional owner；"
            "请在 Assembly 中声明 WaveEncounter 或 RayEncounter",
        )

    def _canonical_response(
        self,
        incident_terminal_p_s_values: torch.Tensor,
    ) -> torch.Tensor:
        _require_canonical_response_input(incident_terminal_p_s_values)
        self._validate_physical_state()
        outgoing = _cube_response.apply_closed_polarizing_cube_response(
            incident_terminal_p_s_values=incident_terminal_p_s_values,
            reflection_input_indices=_reflection_input_indices(
                self.coating_diagonal
            ),
        )
        _require_canonical_response_invariant(
            incident=incident_terminal_p_s_values,
            outgoing=outgoing,
            error_identity="cube_beam_splitter_response_invariant_violated",
            owner_label=type(self).__name__,
        )
        return outgoing

    def _coating_normal(self) -> torch.Tensor:
        self._validate_physical_state()
        return _derive_coating_normal(
            diagonal=self.coating_diagonal,
            route_right=self.route_right,
            route_top=self.route_top,
        )

    def _coating_p_s_basis(
        self,
        direction: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        normal = self._coating_normal().to(
            device=direction.device,
            dtype=direction.dtype,
        )
        return _derive_coating_p_s_basis(
            direction=direction,
            coating_normal=normal,
        )

    def _reflected_terminal(
        self,
        incident_terminal: CubeTerminal,
    ) -> CubeTerminal:
        return _reflection_map(self.coating_diagonal)[incident_terminal]

    def _terminal_frame(self, terminal: CubeTerminal) -> _TerminalFrame:
        self._validate_physical_state()
        vertical = torch.linalg.cross(self.route_right, self.route_top)
        return _derive_terminal_frame(
            origin=self.origin,
            outward_direction=_outward_direction(
                terminal=terminal,
                route_right=self.route_right,
                route_top=self.route_top,
            ),
            vertical_direction=vertical,
        )

    def _transmitted_terminal(
        self,
        incident_terminal: CubeTerminal,
    ) -> CubeTerminal:
        return _TRANSMITTED_TERMINAL[incident_terminal]

    def _validate_physical_state(self) -> None:
        _prepare_cube_geometry(
            owner_label=type(self).__name__,
            origin=self.origin,
            route_right=self.route_right,
            route_top=self.route_top,
        )
        _require_valid_diagonal_code(
            self._coating_diagonal_code,
            owner_label=type(self).__name__,
        )

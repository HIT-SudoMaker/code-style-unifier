from __future__ import annotations

from enum import Enum

import torch

import chromatix_next._numerics.reflection as _reflection
import chromatix_next.errors as _errors

from ._directional_geometry import (
    _derive_terminal_frame,
    _prepare_fixed_geometry_vector,
    _require_fixed_orthogonal_axes,
    _require_fixed_unit_vector,
    _TerminalFrame,
)

__all__ = [
    "IdealPlanarMirror",
    "MirrorTerminal",
]


class MirrorTerminal(str, Enum):
    """
    第一增量理想平面 Mirror 的唯一物理 Terminal

    """

    FRONT = "front"


def _prepare_mirror_geometry(
    *,
    origin: object,
    outward_normal: object,
    transverse_up: object,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    owner_label = "IdealPlanarMirror"
    prepared_origin = _prepare_fixed_geometry_vector(
        origin,
        owner_label=owner_label,
        field_name="origin",
        identity_prefix="ideal_planar_mirror_origin",
    )
    prepared_outward_normal = _prepare_fixed_geometry_vector(
        outward_normal,
        owner_label=owner_label,
        field_name="outward_normal",
        identity_prefix="ideal_planar_mirror_outward_normal",
    )
    prepared_transverse_up = _prepare_fixed_geometry_vector(
        transverse_up,
        owner_label=owner_label,
        field_name="transverse_up",
        identity_prefix="ideal_planar_mirror_transverse_up",
    )
    _require_fixed_unit_vector(
        prepared_outward_normal,
        owner_label=owner_label,
        field_name="outward_normal",
        error_identity="ideal_planar_mirror_outward_normal_not_unit",
    )
    _require_fixed_unit_vector(
        prepared_transverse_up,
        owner_label=owner_label,
        field_name="transverse_up",
        error_identity="ideal_planar_mirror_transverse_up_not_unit",
    )
    _require_fixed_orthogonal_axes(
        prepared_outward_normal,
        prepared_transverse_up,
        owner_label=owner_label,
        first_name="outward_normal",
        second_name="transverse_up",
        error_identity="ideal_planar_mirror_axes_not_orthogonal",
    )
    return prepared_origin, prepared_outward_normal, prepared_transverse_up


def _ideal_wave_response(values: torch.Tensor) -> torch.Tensor:
    return -values


class IdealPlanarMirror(torch.nn.Module):
    """
    拥有固定单 Terminal 几何的理想法向入射 Wave/Ray 平面 Mirror

    Args:
        origin: Mirror Terminal 的全局原点，单位为米
        outward_normal: 从 Mirror FRONT 指向外部的固定单位法线
        transverse_up: 与 outward_normal 正交的固定横向上方向

    Raises:
        OpticalTypeError: 几何的类型或 dtype 不符合契约
        OpticalValueError: 几何的形状、有限性、单位性或正交性不符合契约

    """

    origin: torch.Tensor
    outward_normal: torch.Tensor
    transverse_up: torch.Tensor

    def __init__(
        self,
        *,
        origin: tuple[float, float, float] | torch.Tensor,
        outward_normal: tuple[float, float, float] | torch.Tensor,
        transverse_up: tuple[float, float, float] | torch.Tensor,
    ) -> None:
        super().__init__()
        prepared_origin, prepared_outward_normal, prepared_transverse_up = (
            _prepare_mirror_geometry(
                origin=origin,
                outward_normal=outward_normal,
                transverse_up=transverse_up,
            )
        )
        self.register_buffer("origin", prepared_origin)
        self.register_buffer("outward_normal", prepared_outward_normal)
        self.register_buffer("transverse_up", prepared_transverse_up)

    def forward(self) -> None:  # type: ignore[override]
        """
        拒绝脱离 Assembly Encounter 的独立 owner 执行

        Raises:
            OpticalRuntimeError: directional owner 没有 standalone forward action

        """
        raise _errors.OpticalRuntimeError(
            "ideal_planar_mirror_has_no_forward_action",
            "IdealPlanarMirror 是 state-only directional owner；"
            "请在 Assembly 中声明 WaveEncounter 或 RayEncounter",
        )

    def _ray_direction_response(
        self,
        incident_direction: torch.Tensor,
        *,
        unit_normal: torch.Tensor,
    ) -> torch.Tensor:
        self._validate_physical_state()
        reflected = _reflection._householder_reflect(
            vector=incident_direction,
            unit_normal=unit_normal,
        )
        return reflected

    def _terminal_frame(
        self,
        terminal: MirrorTerminal,
    ) -> _TerminalFrame:
        self._validate_physical_state()
        if terminal is not MirrorTerminal.FRONT:
            raise _errors.OpticalRuntimeError(
                "ideal_planar_mirror_response_invariant_violated",
                "private Mirror frame 只接受 MirrorTerminal.FRONT；"
                "请恢复经资格验证的 Encounter adapter",
            )
        return _derive_terminal_frame(
            origin=self.origin,
            outward_direction=self.outward_normal,
            vertical_direction=self.transverse_up,
        )

    def _validate_physical_state(self) -> None:
        _prepare_mirror_geometry(
            origin=self.origin,
            outward_normal=self.outward_normal,
            transverse_up=self.transverse_up,
        )

    def _wave_response(self, values: torch.Tensor) -> torch.Tensor:
        self._validate_physical_state()
        response = _ideal_wave_response(values)
        if not values.is_meta and not torch.equal(response, -values):
            raise _errors.OpticalRuntimeError(
                "ideal_planar_mirror_response_invariant_violated",
                "IdealPlanarMirror 的法向入射 Wave 响应必须逐分量精确等于输入乘 -1；"
                "请恢复经资格验证的理想标量响应",
            )
        return response

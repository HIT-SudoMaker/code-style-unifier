from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TypeAlias, cast

import torch

import chromatix_next.errors as _errors

from .element.ideal_cube_beam_splitter import (
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
)
from .element.ideal_planar_mirror import IdealPlanarMirror, MirrorTerminal
from .grid import SpatialGrid

_Vector3: TypeAlias = torch.Tensor

_RouteScalar: TypeAlias = float | torch.Tensor

_SignedPermutation2: TypeAlias = tuple[
    tuple[int, int],
    tuple[int, int],
]

_UNIT_ROUNDOFF = 2.0**-53

_DIRECTION_TOLERANCE = 128.0 * _UNIT_ROUNDOFF

_MINIMUM_NORMAL_SCALE = 2.0**-1022


@dataclass(frozen=True, slots=True)
class _TerminalFrameInput:
    """
    承载 Freeze 期间读取的一组 owner Terminal 几何纯值

    """

    owner_name: str
    terminal: str
    origin: _Vector3
    incident_direction: _Vector3
    incident_horizontal: _Vector3
    incident_vertical: _Vector3
    outgoing_direction: _Vector3
    outgoing_horizontal: _Vector3
    outgoing_vertical: _Vector3


@dataclass(frozen=True, slots=True)
class _RouteBasisTransport:
    """
    记录同一物理横向基在采样轴与 Jones 分量上的有符号置换

    """

    destination_yx_from_source_yx: _SignedPermutation2
    destination_hv_from_source_hv: _SignedPermutation2


@dataclass(frozen=True, slots=True)
class _RouteValidation:
    """
    返回不携带传播距离的 Route 几何验证结论

    """

    basis_transport: _RouteBasisTransport | None
    failure: str | None


def _directional_owner_kind(owner: object) -> str | None:
    # 三个闭合 owner 的 nominal recognition 只存在于几何边界
    if isinstance(
        owner,
        (
            IdealNonpolarizingCubeBeamSplitter,
            IdealPolarizingCubeBeamSplitter,
        ),
    ):
        return "cube"
    if isinstance(owner, IdealPlanarMirror):
        return "mirror"
    return None


def _directional_owner_topology(
    owner: object,
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]] | None:
    # 返回固定 owner 的封闭 Terminal 顺序与允许 route，不建立 registry
    if isinstance(
        owner,
        (
            IdealNonpolarizingCubeBeamSplitter,
            IdealPolarizingCubeBeamSplitter,
        ),
    ):
        terminal_order = tuple(
            terminal.value
            for terminal in CubeTerminal
        )
        routes = tuple(
            (
                incident.value,
                outgoing.value,
            )
            for incident in CubeTerminal
            for outgoing in (
                owner._transmitted_terminal(incident),
                owner._reflected_terminal(incident),
            )
        )
        return terminal_order, routes
    if isinstance(owner, IdealPlanarMirror):
        front = MirrorTerminal.FRONT.value
        return (front,), ((front, front),)
    return None


def _owner_terminal_type(
    owner: object,
) -> type[CubeTerminal] | type[MirrorTerminal] | None:
    # 保持 exact enum type check，拒绝字符串或形似 Terminal 的对象
    if isinstance(
        owner,
        (
            IdealNonpolarizingCubeBeamSplitter,
            IdealPolarizingCubeBeamSplitter,
        ),
    ):
        return CubeTerminal
    if isinstance(owner, IdealPlanarMirror):
        return MirrorTerminal
    return None


def _owner_terminal_frames(
    *,
    owner_name: str,
    owner: object,
    terminal_order: tuple[str, ...],
) -> tuple[_TerminalFrameInput, ...]:
    # 在闭合物理边界提取 nominal owner frame，Assembly 不导入 Element
    terminal_type = _owner_terminal_type(owner)
    if terminal_type is None:
        raise _errors.AssemblyError(
            _assembly_locator(
                "assembly_include_directional_owner_invalid",
                owner=owner_name,
            ),
            f"directional owner {owner_name} 不属于封闭 Cube/Mirror owner 集合；"
            "请通过 Assembly.include_directional 纳入受支持的 owner",
        )
    terminal_frame = getattr(owner, "_terminal_frame")
    return tuple(
        _terminal_frame_input(
            owner_name=owner_name,
            terminal=terminal_name,
            frame=terminal_frame(terminal_type(terminal_name)),
        )
        for terminal_name in terminal_order
    )


def _terminal_frame_input(
    *,
    owner_name: str,
    terminal: str,
    frame: object,
) -> _TerminalFrameInput:
    # 仅在 Freeze 边界把固定 owner frame 读取为可序列化纯值
    return _TerminalFrameInput(
        owner_name=owner_name,
        terminal=terminal,
        origin=_fixed_vector(getattr(frame, "origin", None)),
        incident_direction=_fixed_vector(
            getattr(frame, "incident_direction", None),
        ),
        incident_horizontal=_fixed_vector(
            getattr(frame, "incident_horizontal", None),
        ),
        incident_vertical=_fixed_vector(
            getattr(frame, "incident_vertical", None),
        ),
        outgoing_direction=_fixed_vector(
            getattr(frame, "outgoing_direction", None),
        ),
        outgoing_horizontal=_fixed_vector(
            getattr(frame, "outgoing_horizontal", None),
        ),
        outgoing_vertical=_fixed_vector(
            getattr(frame, "outgoing_vertical", None),
        ),
    )


def _resolved_scalar(value: object) -> _RouteScalar | None:
    # 在设备本地解析 Freeze 标量；返回值只参与临时验证，不进入 frozen facts
    if isinstance(value, torch.Tensor):
        if (
            value.dim() != 0
            or torch.is_complex(value)
            or value.dtype is not torch.float64
            or value.is_meta
        ):
            return None
        detached = value.detach()
        if not bool(torch.isfinite(detached)):
            return None
        return detached
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        return None
    return float(value)


def _validate_route(
    *,
    source: _TerminalFrameInput,
    destination: _TerminalFrameInput,
    propagation_displacements: tuple[_RouteScalar | None, ...],
) -> _RouteValidation:
    # 严格按规范的 route-local 顺序验证，不生成传播或相位状态
    if any(value is None for value in propagation_displacements):
        return _RouteValidation(
            basis_transport=None,
            failure="distance_unresolvable",
        )
    resolved_displacements = tuple(
        value
        for value in propagation_displacements
        if value is not None
    )
    if any(
        not _route_scalar_is_finite(value)
        for value in resolved_displacements
    ):
        return _RouteValidation(
            basis_transport=None,
            failure="distance_unresolvable",
        )

    vectors = (
        source.origin,
        source.outgoing_direction,
        source.outgoing_horizontal,
        source.outgoing_vertical,
        destination.origin,
        destination.incident_direction,
        destination.incident_horizontal,
        destination.incident_vertical,
    )
    if not _route_values_share_device(
        vectors=vectors,
        scalars=resolved_displacements,
    ):
        return _RouteValidation(
            basis_transport=None,
            failure="distance_unresolvable",
        )

    source_direction = source.outgoing_direction
    destination_direction = destination.incident_direction
    direction_residual = torch.amax(
        torch.abs(source_direction - destination_direction)
    )
    delta = destination.origin - source.origin
    geometric_displacement = _dot(delta, source_direction)
    transverse_residual = delta - geometric_displacement * source_direction
    propagated_displacement = torch.zeros(
        (),
        dtype=torch.float64,
        device=source_direction.device,
    )
    for displacement in resolved_displacements:
        propagated_displacement = (
            propagated_displacement
            + torch.as_tensor(
                displacement,
                dtype=torch.float64,
                device=source_direction.device,
            )
        )
    length_tolerance = _length_tolerance(
        delta=delta,
        propagation_displacements=resolved_displacements,
    )
    geometry_mismatched = (
        bool(direction_residual > _DIRECTION_TOLERANCE)
        or bool(_norm(transverse_residual) > length_tolerance)
        or bool(geometric_displacement < -length_tolerance)
        or any(
            _route_scalar_is_negative(displacement)
            for displacement in resolved_displacements
        )
        or bool(torch.abs(
            propagated_displacement - geometric_displacement
        ) > length_tolerance)
    )
    if geometry_mismatched:
        return _RouteValidation(
            basis_transport=None,
            failure="geometry_mismatched",
        )

    basis_transport = _basis_transport(
        source_horizontal=source.outgoing_horizontal,
        source_vertical=source.outgoing_vertical,
        destination_horizontal=destination.incident_horizontal,
        destination_vertical=destination.incident_vertical,
    )
    if basis_transport is None:
        return _RouteValidation(
            basis_transport=None,
            failure="basis_incompatible",
        )
    return _RouteValidation(
        basis_transport=basis_transport,
        failure=None,
    )


def _length_tolerance(
    *,
    delta: _Vector3 | tuple[float, float, float],
    propagation_displacements: tuple[_RouteScalar, ...],
) -> _RouteScalar:
    count = len(propagation_displacements)
    if isinstance(delta, torch.Tensor):
        absolute_sum = torch.zeros(
            (),
            dtype=torch.float64,
            device=delta.device,
        )
        for value in propagation_displacements:
            absolute_sum = absolute_sum + torch.abs(
                torch.as_tensor(
                    value,
                    dtype=torch.float64,
                    device=delta.device,
                )
            )
        scale = torch.maximum(
            _norm(delta),
            torch.maximum(
                absolute_sum,
                torch.as_tensor(
                    _MINIMUM_NORMAL_SCALE,
                    dtype=torch.float64,
                    device=delta.device,
                ),
            ),
        )
        return max(128, 32 * (count + 4)) * _UNIT_ROUNDOFF * scale
    pure_displacements = cast(
        tuple[float, ...],
        propagation_displacements,
    )
    scale = max(
        math.sqrt(sum(value * value for value in delta)),
        sum(abs(value) for value in pure_displacements),
        _MINIMUM_NORMAL_SCALE,
    )
    return max(128, 32 * (count + 4)) * _UNIT_ROUNDOFF * scale


def _basis_transport(
    *,
    source_horizontal: _Vector3,
    source_vertical: _Vector3,
    destination_horizontal: _Vector3,
    destination_vertical: _Vector3,
) -> _RouteBasisTransport | None:
    destination_yx_from_source_yx = _signed_permutation(
        (
            (
                _dot(destination_vertical, source_vertical),
                _dot(destination_vertical, source_horizontal),
            ),
            (
                _dot(destination_horizontal, source_vertical),
                _dot(destination_horizontal, source_horizontal),
            ),
        )
    )
    if destination_yx_from_source_yx is None:
        return None
    destination_hv_from_source_hv = (
        (
            destination_yx_from_source_yx[1][1],
            destination_yx_from_source_yx[1][0],
        ),
        (
            destination_yx_from_source_yx[0][1],
            destination_yx_from_source_yx[0][0],
        ),
    )
    return _RouteBasisTransport(
        destination_yx_from_source_yx=(
            destination_yx_from_source_yx
        ),
        destination_hv_from_source_hv=(
            destination_hv_from_source_hv
        ),
    )


def _transport_sampling_values(
    values: torch.Tensor,
    *,
    transport: _RouteBasisTransport,
) -> torch.Tensor:
    mapping = transport.destination_yx_from_source_yx
    destination_y_source_axis = _source_axis(mapping[0])
    destination_x_source_axis = _source_axis(mapping[1])
    if (
        destination_y_source_axis == 1
        and destination_x_source_axis == 0
    ):
        return values.transpose(-2, -1)
    return values


def _transport_jones_values(
    values: torch.Tensor,
    *,
    transport: _RouteBasisTransport,
) -> torch.Tensor:
    if values.shape[-3] != 2:
        raise _errors.AssemblyError(
            _assembly_locator("assembly_route_segment_basis_incompatible"),
            "Route Jones transport 只接受恰好两个 transverse 分量；"
            f"收到的分量数是 {values.shape[-3]}，请修复上游偏振表示",
        )
    matrix = torch.tensor(
        transport.destination_hv_from_source_hv,
        dtype=values.dtype,
        device=values.device,
    )
    horizontal = (
        matrix[0, 0] * values[..., 0, :, :]
        + matrix[0, 1] * values[..., 1, :, :]
    )
    vertical = (
        matrix[1, 0] * values[..., 0, :, :]
        + matrix[1, 1] * values[..., 1, :, :]
    )
    return torch.stack((horizontal, vertical), dim=-3)


def _transport_grid(
    grid: SpatialGrid,
    *,
    transport: _RouteBasisTransport,
) -> SpatialGrid:
    mapping = transport.destination_yx_from_source_yx
    source_axes = (
        _source_axis(mapping[0]),
        _source_axis(mapping[1]),
    )
    signs = (
        _source_sign(mapping[0]),
        _source_sign(mapping[1]),
    )
    source_orientation_signs = tuple(
        1 if value == "increasing" else -1
        for value in grid.orientation
    )
    destination_orientation_signs = tuple(
        signs[index] * source_orientation_signs[source_axis]
        for index, source_axis in enumerate(source_axes)
    )
    orientation = tuple(
        "increasing" if value > 0 else "decreasing"
        for value in destination_orientation_signs
    )
    first_sample_position = tuple(
        signs[index] * grid.first_sample_position[source_axis]
        for index, source_axis in enumerate(source_axes)
    )
    return SpatialGrid(
        sample_counts=tuple(
            grid.sample_counts[source_axis]
            for source_axis in source_axes
        ),
        sample_spacing=tuple(
            grid.sample_spacing[source_axis]
            for source_axis in source_axes
        ),
        first_sample_position=first_sample_position,
        orientation=orientation,
    )


def _grids_coregister_after_transport(
    source: SpatialGrid,
    destination: SpatialGrid,
    *,
    transport: _RouteBasisTransport,
) -> bool:
    transformed = _transport_grid(
        source,
        transport=transport,
    )
    return transformed.is_inference_compatible_with(destination)


def _fixed_vector(value: object) -> _Vector3:
    if (
        not isinstance(value, torch.Tensor)
        or value.shape != (3,)
        or value.dtype is not torch.float64
        or value.is_meta
    ):
        raise _errors.AssemblyError(
            _assembly_locator("assembly_route_segment_geometry_mismatched"),
            "Route Terminal Frame 必须提供真实设备上的有限 float64 三向量；"
            "请修复 directional owner 的固定几何状态后重试 Freeze",
        )
    detached = value.detach()
    if not bool(torch.isfinite(detached).all()):
        raise _errors.AssemblyError(
            _assembly_locator("assembly_route_segment_geometry_mismatched"),
            "Route Terminal Frame 的固定三向量必须全部有限；"
            "请移除 owner 几何中的 NaN 或 Inf 后重试 Freeze",
        )
    return detached


def _signed_permutation(
    values: tuple[tuple[torch.Tensor, torch.Tensor], ...],
) -> _SignedPermutation2 | None:
    rows: list[tuple[int, int]] = []
    for row in values:
        canonical = tuple(
            _canonical_basis_coefficient(value)
            for value in row
        )
        if any(value is None for value in canonical):
            return None
        resolved = tuple(
            value
            for value in canonical
            if value is not None
        )
        rows.append((resolved[0], resolved[1]))
    result = (rows[0], rows[1])
    if (
        sum(value != 0 for value in result[0]) != 1
        or sum(value != 0 for value in result[1]) != 1
        or sum(result[row][0] != 0 for row in range(2)) != 1
        or sum(result[row][1] != 0 for row in range(2)) != 1
    ):
        return None
    return result


def _canonical_basis_coefficient(value: torch.Tensor) -> int | None:
    for candidate in (-1, 0, 1):
        if bool(torch.abs(value - candidate) <= _DIRECTION_TOLERANCE):
            return candidate
    return None


def _source_axis(row: tuple[int, int]) -> int:
    return 0 if row[0] != 0 else 1


def _source_sign(row: tuple[int, int]) -> int:
    return row[_source_axis(row)]


def _dot(first: _Vector3, second: _Vector3) -> torch.Tensor:
    return torch.dot(first, second)


def _norm(value: _Vector3) -> torch.Tensor:
    return torch.sqrt(_dot(value, value))


def _route_scalar_is_finite(value: _RouteScalar) -> bool:
    if isinstance(value, torch.Tensor):
        return bool(torch.isfinite(value))
    return math.isfinite(value)


def _route_scalar_is_negative(value: _RouteScalar) -> bool:
    if isinstance(value, torch.Tensor):
        return bool(value < 0.0)
    return value < 0.0


def _route_values_share_device(
    *,
    vectors: tuple[_Vector3, ...],
    scalars: tuple[_RouteScalar, ...],
) -> bool:
    devices = {
        value.device
        for value in vectors
    } | {
        value.device
        for value in scalars
        if isinstance(value, torch.Tensor)
    }
    return len(devices) == 1


def _assembly_locator(
    base: str,
    *,
    owner: str = "-",
) -> str:
    return (
        f"{base}:owner={owner}:encounter=-:incident=-:outgoing=-:route=-:"
        "underlying=-"
    )

from __future__ import annotations

from dataclasses import dataclass

import torch

from chromatix_next._numerics._certified_predicates import dot_sign
from chromatix_next._numerics.ray_polarization import reflect_polarization_direction
from chromatix_next._numerics.surface_geometry.plane import plane_encounter
import chromatix_next.errors as _errors

from . import _assembly_facts, _route_geometry, _wave_directional
from ._ray_surface_advance import advance_ray_surface
from .element.ideal_planar_mirror import IdealPlanarMirror, MirrorTerminal
from .field import OpticalField, _transform_field
from .polarization import PolarizationRepresentation
from .ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)


@dataclass(frozen=True, slots=True)
class _MirrorRayGeometryProjection:
    """
    已准入 Mirror basis 在一次 Ray 计算中的无状态单位几何投影

    """

    origin: torch.Tensor
    unit_normal: torch.Tensor
    tangent_x: torch.Tensor
    tangent_y: torch.Tensor


def _scale_first_unit_vector(vector: torch.Tensor) -> torch.Tensor:
    # 先按最大分量缩放，避免已准入非零三向量在求单位向量时丢失尺度
    scale = vector.abs().amax()
    scaled = vector / scale
    return scaled / torch.linalg.vector_norm(scaled)


def _mirror_ray_geometry_projection(
    mirror: IdealPlanarMirror,
    *,
    reference: torch.Tensor,
) -> _MirrorRayGeometryProjection:
    origin = mirror.origin.to(
        device=reference.device,
        dtype=torch.float64,
    )
    authored_normal = mirror.outward_normal.to(
        device=reference.device,
        dtype=torch.float64,
    )
    authored_up = mirror.transverse_up.to(
        device=reference.device,
        dtype=torch.float64,
    )
    unit_normal = _scale_first_unit_vector(authored_normal)
    transverse_up = authored_up - (
        (authored_up * unit_normal).sum() * unit_normal
    )
    unit_up = _scale_first_unit_vector(transverse_up)
    tangent_x = _scale_first_unit_vector(
        torch.linalg.cross(unit_up, unit_normal),
    )
    tangent_y = _scale_first_unit_vector(
        torch.linalg.cross(unit_normal, tangent_x),
    )
    frame_normal = torch.linalg.cross(tangent_x, tangent_y)
    return _MirrorRayGeometryProjection(
        origin=origin,
        unit_normal=(
            frame_normal / torch.linalg.vector_norm(frame_normal)
        ),
        tangent_x=tangent_x,
        tangent_y=tangent_y,
    )


def _wave_mirror_outputs(
    *,
    owner: object,
    owner_name: str,
    encounter_name: str,
    structural_routes: tuple[tuple[str, str], ...],
    incident: _wave_directional._WaveIncident,
    outgoing_terminals: tuple[str, ...],
) -> tuple[OpticalField, ...]:
    # Mirror 的局部标量响应与 Terminal 基变换是两个相邻但独立的事实
    mirror = _require_mirror_owner(
        owner=owner,
        owner_name=owner_name,
        encounter_name=encounter_name,
    )
    _require_single_front_route(
        owner_name=owner_name,
        encounter_name=encounter_name,
        structural_routes=structural_routes,
        incident_terminal=incident.terminal,
        outgoing_terminals=outgoing_terminals,
    )
    field = _require_wave_input(
        owner_name=owner_name,
        encounter_name=encounter_name,
        incident=incident,
    )
    if incident.route_transport is not None:
        field = _wave_directional._transport_field(  # noqa: SLF001
            field,
            transport=incident.route_transport,
        )
    reflected = _transform_field(
        field,
        envelope=mirror._wave_response(field.envelope),  # noqa: SLF001
    )
    transport = _route_geometry._RouteBasisTransport(
        destination_yx_from_source_yx=((1, 0), (0, -1)),
        destination_hv_from_source_hv=((-1, 0), (0, 1)),
    )
    return (
        _wave_directional._transport_field(  # noqa: SLF001
            reflected,
            transport=transport,
        ),
    )


def _ray_mirror_outputs(
    *,
    owner: object,
    owner_name: str,
    encounter_name: str,
    structural_routes: tuple[tuple[str, str], ...],
    incident_terminal: str,
    bundle: RayBundle,
    outgoing_terminals: tuple[str, ...],
) -> tuple[RayBundle, ...]:
    mirror = _require_mirror_owner(
        owner=owner,
        owner_name=owner_name,
        encounter_name=encounter_name,
    )
    _require_single_front_route(
        owner_name=owner_name,
        encounter_name=encounter_name,
        structural_routes=structural_routes,
        incident_terminal=incident_terminal,
        outgoing_terminals=outgoing_terminals,
    )
    if not isinstance(bundle, RayBundle):
        raise _errors.AssemblyError(
            "assembly_connection_domain_mismatch",
            "Ray Mirror Encounter 的唯一 incident value 必须是 RayBundle",
        )
    if not mirror.origin.is_meta:
        mirror._validate_physical_state()  # noqa: SLF001
    ray_geometry = _mirror_ray_geometry_projection(
        mirror,
        reference=bundle.direction,
    )
    incident_direction = -ray_geometry.unit_normal
    is_active = bundle.status == RAY_STATUS_ACTIVE
    enters_front_half_space = dot_sign(
        bundle.direction,
        incident_direction,
    ) > 0
    admitted_status = torch.where(
        is_active & (~enters_front_half_space),
        torch.full_like(bundle.status, RAY_STATUS_SURFACE_MISSED),
        bundle.status,
    )
    admitted_bundle = RayBundle(
        position=bundle.position,
        direction=bundle.direction,
        polarization_vector=bundle.polarization_vector,
        power=bundle.power,
        refractive_index=bundle.refractive_index,
        optical_path=bundle.optical_path,
        status=admitted_status,
        spectrum=bundle.spectrum,
    )
    encounter = plane_encounter(
        ray_origin=admitted_bundle.position,
        ray_direction=admitted_bundle.direction,
        plane_origin=ray_geometry.origin,
        plane_tangent_x=ray_geometry.tangent_x,
        plane_tangent_y=ray_geometry.tangent_y,
        clear_aperture_radius=None,
    )
    advance = advance_ray_surface(
        admitted_bundle,
        encounter,
        active_status_value=RAY_STATUS_ACTIVE,
        missed_status_value=RAY_STATUS_SURFACE_MISSED,
        vignetted_status_value=RAY_STATUS_VIGNETTED,
    )
    reflected_direction = mirror._ray_direction_response(  # noqa: SLF001
        bundle.direction,
        unit_normal=advance.unit_normal,
    )
    reflected_polarization = reflect_polarization_direction(
        ray_polarization=bundle.polarization_vector,
        unit_normal=advance.unit_normal,
        is_interacted=advance.is_interacted,
    )
    output = RayBundle(
        position=advance.position,
        direction=torch.where(
            advance.is_interacted.unsqueeze(-1),
            reflected_direction,
            bundle.direction,
        ),
        polarization_vector=reflected_polarization,
        power=bundle.power,
        refractive_index=bundle.refractive_index,
        optical_path=advance.optical_path,
        status=advance.status,
        spectrum=bundle.spectrum,
    )
    return (output,)


def _require_mirror_owner(
    *,
    owner: object,
    owner_name: str,
    encounter_name: str,
) -> IdealPlanarMirror:
    if isinstance(owner, IdealPlanarMirror):
        return owner
    raise _errors.AssemblyError(
        _assembly_facts._directional_finding(
            "assembly_encounter_owner_unsupported",
            owner=owner_name,
            encounter=encounter_name,
        ),
        "Mirror Encounter 只能消费冻结计划中的 IdealPlanarMirror owner",
    )


def _require_single_front_route(
    *,
    owner_name: str,
    encounter_name: str,
    structural_routes: tuple[tuple[str, str], ...],
    incident_terminal: str,
    outgoing_terminals: tuple[str, ...],
) -> None:
    front = MirrorTerminal.FRONT.value
    if (
        structural_routes == ((front, front),)
        and incident_terminal == front
        and outgoing_terminals == (front,)
    ):
        return
    raise _errors.AssemblyError(
        _assembly_facts._directional_finding(
            "assembly_connect_structural_zero",
            owner=owner_name,
            encounter=encounter_name,
            incident=incident_terminal,
            outgoing=(
                outgoing_terminals[0]
                if len(outgoing_terminals) == 1
                else "-"
            ),
        ),
        "Mirror Encounter 的冻结结构必须恰好是 FRONT 到 FRONT",
    )


def _require_wave_input(
    *,
    owner_name: str,
    encounter_name: str,
    incident: _wave_directional._WaveIncident,
) -> OpticalField:
    field = incident.field
    underlying = "-"
    if not isinstance(field, OpticalField):
        underlying = "wave_mirror_input_value_invalid"
    elif field.envelope.dtype is not torch.complex128:
        underlying = "optical_field_envelope_dtype_invalid"
    elif (
        field.polarization_representation
        is not PolarizationRepresentation.TRANSVERSE
        or field.envelope.shape[-3] != 2
    ):
        underlying = "wave_mirror_polarization_representation_invalid"
    elif not field.envelope.is_meta and not bool(
        torch.isfinite(field.envelope).all()
    ):
        underlying = "optical_field_envelope_nonfinite"
    if underlying == "-":
        return field
    raise _errors.AssemblyError(
        _assembly_facts._directional_finding(
            "assembly_wave_contributors_incompatible",
            owner=owner_name,
            encounter=encounter_name,
            incident=incident.terminal,
            route=incident.route_name or "-",
            underlying=underlying,
        ),
        "Wave Mirror contributor 必须是有限、transverse、fixed-double OpticalField",
    )

from __future__ import annotations

from typing import TypeAlias

import torch

from chromatix_next._numerics._certified_predicates import dot_sign
from chromatix_next._numerics.ray_polarization import reflect_polarization_direction
from chromatix_next._numerics.reflection import reflect_direction
from chromatix_next._numerics.surface_geometry.plane import plane_encounter
from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

from .element.ideal_cube_beam_splitter import (
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
    _outward_direction,
)
from .ray_bundle import RAY_STATUS_ACTIVE, RAY_STATUS_SURFACE_MISSED, RayBundle

_CubeOwner: TypeAlias = (
    IdealNonpolarizingCubeBeamSplitter
    | IdealPolarizingCubeBeamSplitter
)

_UNIT_ROUND_OFF = 2.0 ** -53


def _ray_cube_outputs(
    *,
    owner: object,
    owner_name: str,
    encounter_name: str,
    structural_routes: tuple[tuple[str, str], ...],
    incident_terminal: str,
    bundle: RayBundle,
    outgoing_terminals: tuple[str, ...],
) -> tuple[RayBundle, ...]:
    if not isinstance(
        owner,
        (
            IdealNonpolarizingCubeBeamSplitter,
            IdealPolarizingCubeBeamSplitter,
        ),
    ):
        raise _errors.AssemblyError(
            "assembly_encounter_owner_unsupported",
            "Ray Cube Encounter 只能消费冻结计划中的理想 NBS/PBS Cube owner",
        )
    if not isinstance(bundle, RayBundle):
        raise _errors.AssemblyError(
            "assembly_connection_domain_mismatch",
            "Ray Cube Encounter 的唯一 incident value 必须是 RayBundle",
        )
    if not owner.origin.is_meta:
        owner._validate_physical_state()  # noqa: SLF001
    incident = CubeTerminal(incident_terminal)
    transmitted = owner._transmitted_terminal(incident)  # noqa: SLF001
    structural_outgoing = tuple(
        outgoing
        for incoming, outgoing in structural_routes
        if incoming == incident_terminal
    )
    if (
        len(structural_outgoing) != 2
        or transmitted.value not in structural_outgoing
        or tuple(outgoing_terminals) != tuple(
            terminal.value
            for terminal in CubeTerminal
            if terminal.value in structural_outgoing
        )
    ):
        raise _errors.AssemblyError(
            "assembly_connect_structural_zero",
            "Ray Cube Encounter 的冻结输出必须恰好来自同一 owner 的透射与反射拓扑",
        )
    reflected = CubeTerminal(
        next(
            terminal
            for terminal in structural_outgoing
            if terminal != transmitted.value
        )
    )
    aligned_geometry = _aligned_cube_geometry(owner, reference=bundle.position)
    incident_direction = -_outward_direction(
        terminal=incident,
        route_right=aligned_geometry[1],
        route_top=aligned_geometry[2],
    )
    reflected_direction = _outward_direction(
        terminal=reflected,
        route_right=aligned_geometry[1],
        route_top=aligned_geometry[2],
    )
    coating_normal = _coating_normal_from_closed_routes(
        incident_direction=incident_direction,
        reflected_direction=reflected_direction,
    )
    coating_vertical = torch.linalg.cross(
        aligned_geometry[1],
        aligned_geometry[2],
    )
    coating_tangent = torch.linalg.cross(
        coating_normal,
        coating_vertical,
    )
    encounter = plane_encounter(
        ray_origin=bundle.position,
        ray_direction=bundle.direction,
        plane_origin=aligned_geometry[0],
        plane_tangent_x=coating_vertical,
        plane_tangent_y=coating_tangent,
        clear_aperture_radius=None,
    )
    is_active = bundle.status == RAY_STATUS_ACTIVE
    enters_incident_half_space = dot_sign(
        bundle.direction,
        incident_direction,
    ) > 0
    is_candidate_interaction = (
        is_active
        & encounter.is_encountered
        & enters_incident_half_space
    )
    unresolvable = (
        is_candidate_interaction
        & (~encounter.is_continuous_distance_resolvable)
    )
    if is_value_readable(unresolvable) and bool(unresolvable.any()):
        raise _errors.OpticalValueError(
            "ray_surface_distance_unresolvable",
            "精确拓扑确认活动 Ray lane 与 Cube coating plane 相交，"
            "但 fixed-double 无法表示连续交点距离；请调整光路尺度",
        )
    is_interacted = (
        is_candidate_interaction
        & encounter.is_continuous_distance_resolvable
    )
    position = torch.where(
        is_interacted.unsqueeze(-1),
        encounter.intersection,
        bundle.position,
    )
    optical_path = torch.where(
        is_interacted,
        bundle.optical_path
        + bundle.refractive_index * encounter.distance.to(torch.float64),
        bundle.optical_path,
    )
    status = torch.where(
        is_active,
        torch.where(
            is_interacted,
            torch.full_like(bundle.status, RAY_STATUS_ACTIVE),
            torch.full_like(bundle.status, RAY_STATUS_SURFACE_MISSED),
        ),
        bundle.status,
    )
    reflected_ray_direction = reflect_direction(
        ray_direction=bundle.direction,
        unit_normal=encounter.unit_normal,
        is_interacted=is_interacted,
    )
    if isinstance(owner, IdealNonpolarizingCubeBeamSplitter):
        transmitted_polarization = bundle.polarization_vector
        reflected_polarization = reflect_polarization_direction(
            ray_polarization=bundle.polarization_vector,
            unit_normal=encounter.unit_normal,
            is_interacted=is_interacted,
        )
        aligned_angle = owner.mixing_angle.to(
            device=bundle.power.device,
            dtype=torch.float64,
        )
        transmitted_fraction = torch.cos(aligned_angle).square()
        reflected_fraction = torch.sin(aligned_angle).square()
        interacted_transmitted_power = (
            bundle.power * transmitted_fraction
        )
        interacted_reflected_power = bundle.power * reflected_fraction
    else:
        p_axis, s_axis = _ray_p_s_basis(
            ray_direction=bundle.direction,
            coating_normal=coating_normal,
            deterministic_s_axis=coating_vertical,
        )
        p_projection = (
            bundle.polarization_vector * p_axis
        ).sum(dim=-1)
        s_projection = (
            bundle.polarization_vector * s_axis
        ).sum(dim=-1)
        p_fraction = p_projection.real.square() + p_projection.imag.square()
        s_fraction = s_projection.real.square() + s_projection.imag.square()
        interacted_transmitted_power = bundle.power * p_fraction
        interacted_reflected_power = bundle.power * s_fraction
        transmitted_polarization = _projected_unit_polarization(
            projection=p_projection,
            unit_axis=p_axis,
            is_interacted=is_interacted,
            incident_polarization=bundle.polarization_vector,
        )
        reflected_incident_polarization = _projected_unit_polarization(
            projection=s_projection,
            unit_axis=s_axis,
            is_interacted=is_interacted,
            incident_polarization=bundle.polarization_vector,
        )
        reflected_polarization = reflect_polarization_direction(
            ray_polarization=reflected_incident_polarization,
            unit_normal=encounter.unit_normal,
            is_interacted=is_interacted,
        )
    transmitted_power = torch.where(
        is_interacted,
        interacted_transmitted_power,
        bundle.power,
    )
    reflected_power = torch.where(
        is_interacted,
        interacted_reflected_power,
        torch.zeros_like(bundle.power),
    )
    _require_outgoing_half_space(
        direction=bundle.direction,
        is_interacted=is_interacted,
        owner_name=owner_name,
        encounter_name=encounter_name,
        incident_terminal=incident,
        outgoing_terminal=transmitted,
        route_right=aligned_geometry[1],
        route_top=aligned_geometry[2],
    )
    _require_outgoing_half_space(
        direction=reflected_ray_direction,
        is_interacted=is_interacted,
        owner_name=owner_name,
        encounter_name=encounter_name,
        incident_terminal=incident,
        outgoing_terminal=reflected,
        route_right=aligned_geometry[1],
        route_top=aligned_geometry[2],
    )
    _require_power_conservation(
        input_power=bundle.power,
        transmitted_power=transmitted_power,
        reflected_power=reflected_power,
        interacted_transmitted_power=interacted_transmitted_power,
        interacted_reflected_power=interacted_reflected_power,
        is_interacted=is_interacted,
    )
    transmitted_bundle = RayBundle(
        position=position,
        direction=bundle.direction,
        polarization_vector=transmitted_polarization,
        power=transmitted_power,
        refractive_index=bundle.refractive_index,
        optical_path=optical_path,
        status=status,
        spectrum=bundle.spectrum,
    )
    reflected_bundle = RayBundle(
        position=position,
        direction=reflected_ray_direction,
        polarization_vector=reflected_polarization,
        power=reflected_power,
        refractive_index=bundle.refractive_index,
        optical_path=optical_path,
        status=status,
        spectrum=bundle.spectrum,
    )
    output_by_terminal = {
        transmitted.value: transmitted_bundle,
        reflected.value: reflected_bundle,
    }
    return tuple(output_by_terminal[terminal] for terminal in outgoing_terminals)


def _aligned_cube_geometry(
    owner: _CubeOwner,
    *,
    reference: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    return tuple(
        value.to(device=reference.device, dtype=torch.float64)
        for value in (
            owner.origin,
            owner.route_right,
            owner.route_top,
        )
    )  # type: ignore[return-value]


def _coating_normal_from_closed_routes(
    *,
    incident_direction: torch.Tensor,
    reflected_direction: torch.Tensor,
) -> torch.Tensor:
    candidate = incident_direction - reflected_direction
    return candidate / torch.linalg.vector_norm(candidate)


def _scale_first_unit_vector(
    vector: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    scale = vector.abs().amax(dim=-1)
    has_scale = torch.isfinite(scale) & (scale > 0.0)
    safe_scale = torch.where(has_scale, scale, torch.ones_like(scale))
    scaled = vector / safe_scale.unsqueeze(-1)
    norm = torch.linalg.vector_norm(scaled, dim=-1)
    has_norm = torch.isfinite(norm) & (norm > 0.0)
    safe_norm = torch.where(has_norm, norm, torch.ones_like(norm))
    normalized = scaled / safe_norm.unsqueeze(-1)
    return normalized, has_scale & has_norm


def _ray_p_s_basis(
    *,
    ray_direction: torch.Tensor,
    coating_normal: torch.Tensor,
    deterministic_s_axis: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    expanded_normal = coating_normal.expand_as(ray_direction)
    s_candidate = torch.linalg.cross(expanded_normal, ray_direction)
    normalized_s, has_s = _scale_first_unit_vector(s_candidate)
    expanded_s = deterministic_s_axis.expand_as(ray_direction)
    s_axis = torch.where(has_s.unsqueeze(-1), normalized_s, expanded_s)
    p_candidate = torch.linalg.cross(ray_direction, s_axis)
    p_axis, _has_p = _scale_first_unit_vector(p_candidate)
    return p_axis, s_axis


def _projected_unit_polarization(
    *,
    projection: torch.Tensor,
    unit_axis: torch.Tensor,
    is_interacted: torch.Tensor,
    incident_polarization: torch.Tensor,
) -> torch.Tensor:
    magnitude = projection.abs()
    safe_magnitude = torch.where(
        magnitude > 0.0,
        magnitude,
        torch.ones_like(magnitude),
    )
    phase = torch.where(
        magnitude > 0.0,
        projection / safe_magnitude,
        torch.ones_like(projection),
    )
    projected = phase.unsqueeze(-1) * unit_axis
    return torch.where(
        is_interacted.unsqueeze(-1),
        projected,
        incident_polarization,
    )


def _require_outgoing_half_space(
    *,
    direction: torch.Tensor,
    is_interacted: torch.Tensor,
    owner_name: str,
    encounter_name: str,
    incident_terminal: CubeTerminal,
    outgoing_terminal: CubeTerminal,
    route_right: torch.Tensor,
    route_top: torch.Tensor,
) -> None:
    outgoing_direction = _outward_direction(
        terminal=outgoing_terminal,
        route_right=route_right,
        route_top=route_top,
    )
    inconsistent = is_interacted & (
        dot_sign(direction, outgoing_direction) <= 0
    )
    if not is_value_readable(inconsistent) or not bool(inconsistent.any()):
        return
    raise _errors.OpticalValueError(
        "ray_cube_outgoing_terminal_inconsistent",
        f"Cube owner {owner_name} 的 Ray Encounter {encounter_name} 从 "
        f"{incident_terminal.value} 入射后，计算结果不属于声明的 "
        f"{outgoing_terminal.value} outgoing Terminal 半空间；"
        "请修正入射 lane 几何，结果不会被自动改道",
    )


def _require_power_conservation(
    *,
    input_power: torch.Tensor,
    transmitted_power: torch.Tensor,
    reflected_power: torch.Tensor,
    interacted_transmitted_power: torch.Tensor,
    interacted_reflected_power: torch.Tensor,
    is_interacted: torch.Tensor,
) -> None:
    if not is_value_readable(input_power):
        return
    interacted_sum = (
        interacted_transmitted_power + interacted_reflected_power
    )
    interacted_residual = torch.where(
        is_interacted,
        interacted_sum - input_power,
        torch.zeros_like(input_power),
    )
    total_residual = transmitted_power + reflected_power - input_power
    scale = torch.maximum(input_power.abs(), torch.ones_like(input_power))
    budget = 256.0 * _UNIT_ROUND_OFF * scale
    if bool(
        (interacted_residual.abs() > budget).any()
        or (total_residual.abs() > budget).any()
    ):
        raise _errors.OpticalRuntimeError(
            "cube_beam_splitter_response_invariant_violated",
            "Ray Cube 响应必须只守恒 active interacted power，且含历史 lane 的"
            "逐输出总功率仍必须等于输入功率",
        )

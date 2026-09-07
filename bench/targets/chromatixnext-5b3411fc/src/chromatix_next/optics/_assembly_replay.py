from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any, TypeAlias, cast

import torch

import chromatix_next.errors as _errors

from . import (
    _assembly_facts,
    _meta_inference,
    _mirror_directional,
    _ray_directional,
    _route_geometry,
    _wave_directional,
)
from ._assembly_facts import (
    _ComponentValueCoordinate,
    _DirectionalValueCoordinate,
    _ExecutionStep,
    _FrozenAssembly,
    _ValueIdentity,
)
from .field import OpticalField
from .grid import SpatialGrid
from .intensity import Intensity
from .ray_bundle import RayBundle

if TYPE_CHECKING:
    from .assembly import Assembly

_PhysicalValue: TypeAlias = OpticalField | Intensity | RayBundle

_StableValueCoordinate: TypeAlias = (
    _ComponentValueCoordinate | _DirectionalValueCoordinate
)



def _nested_error_identity(error: Exception) -> str:
    if isinstance(error, _errors.OpticalError):
        return error.identity
    message = str(error)
    if message and message.isascii() and all(
        character.isalnum() or character in "_:-"
        for character in message
    ):
        return message
    return type(error).__name__


def _step_failure_finding(
    assembly: Assembly,
    step: _ExecutionStep,
    error: Exception,
) -> str:
    role = assembly._contracts[step.component_name].role  # noqa: SLF001
    return (
        f"assembly_{role}_forward_failed:"
        f"{step.component_name}:{_nested_error_identity(error)}"
    )


def _replay(
    assembly: Assembly,
    *,
    generator_for: Callable[[str], torch.Generator] | None = None,
    validate_value: (
        Callable[[_PhysicalValue], None] | None
    ) = None,
) -> Mapping[str, _PhysicalValue]:
    return _replay_facts(
        assembly,
        assembly._execution_facts(),  # noqa: SLF001
        generator_for=generator_for,
        validate_value=validate_value,
        findings=None,
        real_grid_assembly=None,
    )


def _replay_facts(
    assembly: Assembly,
    facts: _FrozenAssembly,
    *,
    generator_for: Callable[[str], torch.Generator] | None,
    validate_value: (
        Callable[[_PhysicalValue], None] | None
    ),
    findings: list[str] | None,
    real_grid_assembly: Assembly | None,
) -> Mapping[str, _PhysicalValue]:
    return _replay_plan_facts(
        assembly,
        facts,
        generator_for=generator_for,
        validate_value=validate_value,
        findings=findings,
        real_grid_assembly=real_grid_assembly,
    )


def _replay_plan_facts(
    assembly: Assembly,
    facts: _FrozenAssembly,
    *,
    generator_for: Callable[[str], torch.Generator] | None,
    validate_value: (
        Callable[[_PhysicalValue], None] | None
    ),
    findings: list[str] | None,
    real_grid_assembly: Assembly | None,
) -> Mapping[str, _PhysicalValue]:
    # 按唯一 frozen replay_order 交错执行 Component 与 state-free Encounter
    step_by_name = {
        step.component_name: step
        for step in facts.steps
    }
    encounter_by_name = {
        step.encounter_name: step
        for step in facts.directional_steps
    }
    owner_fact_by_name = {
        owner.owner_name: owner
        for owner in facts.directional_owners
    }
    ordinary_coordinates = _ordinary_output_coordinates(facts)
    source_by_destination = {
        flow.destination_value: flow.source_value
        for flow in facts.value_flows
    }
    route_by_destination = {
        route.destination_value: route
        for route in facts.route_segments
    }
    values: dict[_StableValueCoordinate, _PhysicalValue] = {}
    failed_values: set[_StableValueCoordinate] = set()
    real_grids: dict[_StableValueCoordinate, SpatialGrid] = {}
    releases_by_step = {
        replay_step: tuple(
            release.value
            for release in facts.releases
            if release.after_step == replay_step
        )
        for replay_step in facts.replay_order
    }
    for replay_step in facts.replay_order:
        if replay_step.category == "component":
            step = step_by_name[replay_step.name]
            output_coordinates = tuple(
                ordinary_coordinates[value_identity]
                for value_identity in step.output_values
            )
            input_coordinates = _component_input_sources(
                assembly=assembly,
                component_name=step.component_name,
                source_by_destination=source_by_destination,
            )
            if any(
                coordinate in failed_values or coordinate not in values
                for coordinate in input_coordinates
            ):
                failed_values.update(output_coordinates)
                continue
            inputs: tuple[Any, ...] = (
                (assembly._anchor_grid(step.component_name),)  # noqa: SLF001
                if step.is_source
                else tuple(values[coordinate] for coordinate in input_coordinates)
            )
            component = assembly._component(step.component_name)  # noqa: SLF001
            try:
                real_output_grid = _real_output_grid_for_plan_step(
                    assembly=assembly,
                    step=step,
                    inputs=inputs,
                    input_coordinates=input_coordinates,
                    real_grids=real_grids,
                    real_grid_assembly=real_grid_assembly,
                )
                result = _call_component(
                    component,
                    component_name=step.component_name,
                    inputs=inputs,
                    generator_for=generator_for,
                    is_generator_accepted=step.is_generator_accepted,
                )
                outputs = _validated_outputs(step, result)
                if validate_value is not None:
                    for output in outputs:
                        validate_value(output)
            except Exception as error:
                if findings is None:
                    if isinstance(
                        error,
                        (_errors.OpticalError, torch.OutOfMemoryError),
                    ):
                        raise
                    raise _errors.AssemblyError(
                        _step_failure_finding(assembly, step, error),
                        f"组件 {step.component_name} 的物理计算失败",
                    ) from error
                if isinstance(error, _errors.AssemblyError):
                    findings.append(error.identity)
                else:
                    findings.append(_step_failure_finding(assembly, step, error))
                failed_values.update(output_coordinates)
                continue
            for coordinate, output in zip(
                output_coordinates,
                outputs,
                strict=True,
            ):
                values[coordinate] = output
                if real_output_grid is not None:
                    real_grids[coordinate] = real_output_grid
        else:
            step = encounter_by_name[replay_step.name]
            source_coordinates = tuple(
                source_by_destination[input_value]
                for input_value in step.input_values
            )
            if any(
                coordinate in failed_values or coordinate not in values
                for coordinate in source_coordinates
            ):
                failed_values.update(step.output_values)
                continue
            owner_fact = owner_fact_by_name[step.owner_name]
            owner = assembly._component(step.owner_name)  # noqa: SLF001
            real_output_grids: tuple[SpatialGrid, ...] | None = None
            try:
                if step.domain == "wave":
                    incidents = tuple(
                        _wave_directional._WaveIncident(
                            terminal=input_value.terminal,
                            field=cast(
                                OpticalField,
                                values[source_coordinate],
                            ),
                            route_name=(
                                route_by_destination[
                                    input_value
                                ].route_name
                                if input_value in route_by_destination
                                else None
                            ),
                            route_transport=(
                                route_by_destination[
                                    input_value
                                ].basis_transport
                                if input_value in route_by_destination
                                else None
                            ),
                        )
                        for input_value, source_coordinate in zip(
                            step.input_values,
                            source_coordinates,
                            strict=True,
                        )
                    )
                    if _route_geometry._directional_owner_kind(owner) == "mirror":
                        if len(incidents) != 1:
                            raise _errors.AssemblyError(
                                _assembly_facts._directional_finding(
                                    "assembly_encounter_owner_unsupported",
                                    owner=step.owner_name,
                                    encounter=step.encounter_name,
                                ),
                                "Wave Mirror Encounter 必须恰有一个 FRONT 入射",
                            )
                        outputs = _mirror_directional._wave_mirror_outputs(
                            owner=owner,
                            owner_name=step.owner_name,
                            encounter_name=step.encounter_name,
                            structural_routes=owner_fact.routes,
                            incident=incidents[0],
                            outgoing_terminals=tuple(
                                value.terminal
                                for value in step.output_values
                            ),
                        )
                    else:
                        outputs = _wave_directional._wave_cube_outputs(
                            owner=owner,
                            owner_name=step.owner_name,
                            encounter_name=step.encounter_name,
                            terminal_order=owner_fact.terminal_order,
                            structural_routes=owner_fact.routes,
                            incidents=incidents,
                            outgoing_terminals=tuple(
                                value.terminal
                                for value in step.output_values
                            ),
                        )
                    real_output_grids = (
                        _real_wave_output_grids_for_encounter(
                            step=step,
                            owner=owner,
                            owner_fact=owner_fact,
                            incidents=incidents,
                            outputs=cast(tuple[OpticalField, ...], outputs),
                            source_coordinates=source_coordinates,
                            real_grids=real_grids,
                        )
                        if real_grid_assembly is not None
                        else None
                    )
                elif step.domain == "ray" and len(source_coordinates) == 1:
                    if _route_geometry._directional_owner_kind(owner) == "mirror":
                        outputs = _mirror_directional._ray_mirror_outputs(
                            owner=owner,
                            owner_name=step.owner_name,
                            encounter_name=step.encounter_name,
                            structural_routes=owner_fact.routes,
                            incident_terminal=step.input_values[0].terminal,
                            bundle=cast(
                                RayBundle,
                                values[source_coordinates[0]],
                            ),
                            outgoing_terminals=tuple(
                                value.terminal
                                for value in step.output_values
                            ),
                        )
                    else:
                        outputs = _ray_directional._ray_cube_outputs(
                            owner=owner,
                            owner_name=step.owner_name,
                            encounter_name=step.encounter_name,
                            structural_routes=owner_fact.routes,
                            incident_terminal=step.input_values[0].terminal,
                            bundle=cast(
                                RayBundle,
                                values[source_coordinates[0]],
                            ),
                            outgoing_terminals=tuple(
                                value.terminal
                                for value in step.output_values
                            ),
                        )
                else:
                    raise _errors.AssemblyError(
                        _assembly_facts._directional_finding(
                            "assembly_encounter_owner_unsupported",
                            owner=step.owner_name,
                            encounter=step.encounter_name,
                        ),
                        "冻结 Encounter 必须是受支持的 Wave 或单入射 Ray 作用域",
                    )
                if validate_value is not None:
                    for output in outputs:
                        validate_value(output)
            except Exception as error:
                if findings is None:
                    if isinstance(
                        error,
                        (_errors.OpticalError, torch.OutOfMemoryError),
                    ):
                        raise
                    raise _errors.AssemblyError(
                        _encounter_failure_finding(step, error),
                        f"{step.domain} Encounter {step.encounter_name} 的物理计算失败",
                    ) from error
                if isinstance(error, _errors.AssemblyError):
                    findings.append(error.identity)
                else:
                    findings.append(_encounter_failure_finding(step, error))
                failed_values.update(step.output_values)
                continue
            for coordinate, output in zip(
                step.output_values,
                outputs,
                strict=True,
            ):
                values[coordinate] = output
            if real_output_grids is not None:
                for coordinate, real_output_grid in zip(
                    step.output_values,
                    real_output_grids,
                    strict=True,
                ):
                    real_grids[coordinate] = real_output_grid
        for value in releases_by_step[replay_step]:
            values.pop(value, None)
            real_grids.pop(value, None)
    exposure_coordinates = {
        name: ordinary_coordinates[value]
        for name, value in facts.exposures
    } | {
        exposure.name: exposure.value
        for exposure in facts.directional_exposures
    }
    return {
        name: values[exposure_coordinates[name]]
        for name in facts.exposure_order
        if exposure_coordinates[name] in values
    }


def _ordinary_output_coordinates(
    facts: _FrozenAssembly,
) -> dict[_ValueIdentity, _ComponentValueCoordinate]:
    return {
        value: _ComponentValueCoordinate(
            component_name=step.component_name,
            port=port,
            direction="output",
        )
        for step in facts.steps
        for port, value in zip(
            step.output_ports,
            step.output_values,
            strict=True,
        )
    }


def _component_input_sources(
    *,
    assembly: Assembly,
    component_name: str,
    source_by_destination: dict[
        _StableValueCoordinate,
        _StableValueCoordinate,
    ],
) -> tuple[_StableValueCoordinate, ...]:
    contract = assembly._contracts[component_name]  # noqa: SLF001
    return tuple(
        source_by_destination[
            _ComponentValueCoordinate(
                component_name=component_name,
                port=port,
                direction="input",
            )
        ]
        for port in contract.input_ports
    )


def _encounter_failure_finding(
    step: _assembly_facts._DirectionalExecutionStep,
    error: Exception,
) -> str:
    return _assembly_facts._directional_finding(
        f"assembly_{step.domain}_encounter_forward_failed",
        owner=step.owner_name,
        encounter=step.encounter_name,
        underlying=_nested_error_identity(error),
    )


def _real_wave_output_grids_for_encounter(
    *,
    step: _assembly_facts._DirectionalExecutionStep,
    owner: torch.nn.Module,
    owner_fact: _assembly_facts._DirectionalOwnerFact,
    incidents: tuple[_wave_directional._WaveIncident, ...],
    outputs: tuple[OpticalField, ...],
    source_coordinates: tuple[_StableValueCoordinate, ...],
    real_grids: dict[_StableValueCoordinate, SpatialGrid],
) -> tuple[SpatialGrid, ...]:
    real_grid_by_terminal = {
        incident.terminal: real_grids[source_coordinate]
        for incident, source_coordinate in zip(
            incidents,
            source_coordinates,
            strict=True,
        )
    }
    owner_kind = _route_geometry._directional_owner_kind(owner)
    if owner_kind == "mirror":
        return (
            _real_grid_after_meta_transport(
                source_meta_grid=incidents[0].field.grid,
                destination_meta_grid=outputs[0].grid,
                source_real_grid=real_grid_by_terminal[
                    incidents[0].terminal
                ],
            ),
        )
    coating_projection = (
        _wave_directional._incident_field_in_coating_basis  # noqa: SLF001
    )
    coating_fields = {
        incident.terminal: coating_projection(
            owner=owner,
            owner_name=step.owner_name,
            encounter_name=step.encounter_name,
            incident=_bounded_wave_incident(incident),
        )
        for incident in incidents
    }
    real_coating_grids = {
        incident.terminal: _real_grid_after_meta_transport(
            source_meta_grid=incident.field.grid,
            destination_meta_grid=coating_fields[incident.terminal].grid,
            source_real_grid=real_grid_by_terminal[incident.terminal],
        )
        for incident in incidents
    }
    incident_by_terminal = {
        incident.terminal: incident
        for incident in incidents
    }
    output_grids: list[SpatialGrid] = []
    for output_value, output in zip(
        step.output_values,
        outputs,
        strict=True,
    ):
        contributor_terminals = tuple(
            terminal
            for terminal in owner_fact.terminal_order
            if terminal in coating_fields
            and (terminal, output_value.terminal) in owner_fact.routes
        )
        reference_terminal = contributor_terminals[0]
        reference_grid = real_coating_grids[reference_terminal]
        for terminal in contributor_terminals[1:]:
            with _meta_inference._real_grid_precheck():
                if reference_grid.is_physically_equivalent_to(
                    real_coating_grids[terminal],
                ):
                    continue
            incident = incident_by_terminal[terminal]
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_wave_contributors_incompatible",
                    owner=step.owner_name,
                    encounter=step.encounter_name,
                    incident=terminal,
                    outgoing=output_value.terminal,
                    route=incident.route_name or "-",
                    underlying="grid_mismatch",
                ),
                "同一 outgoing Terminal 的结构贡献者必须在基变换后"
                "位于完全相同的真实空间网格",
            )
        output_grids.append(
            _real_grid_after_meta_transport(
                source_meta_grid=coating_fields[reference_terminal].grid,
                destination_meta_grid=output.grid,
                source_real_grid=reference_grid,
            )
        )
    return tuple(output_grids)


def _bounded_wave_incident(
    incident: _wave_directional._WaveIncident,
) -> _wave_directional._WaveIncident:
    field = incident.field
    bounded_grid = SpatialGrid(
        sample_counts=(1, 1),
        sample_spacing=field.grid.sample_spacing,
        first_sample_position=field.grid.first_sample_position,
        orientation=field.grid.orientation,
    )
    return replace(
        incident,
        field=replace(
            field,
            envelope=field.envelope[..., :1, :1],
            grid=bounded_grid,
        ),
    )


def _real_grid_after_meta_transport(
    *,
    source_meta_grid: SpatialGrid,
    destination_meta_grid: SpatialGrid,
    source_real_grid: SpatialGrid,
) -> SpatialGrid:
    source_axes = tuple(
        next(
            (
                index
                for index, source_spacing in enumerate(
                    source_meta_grid.sample_spacing,
                )
                if destination_spacing is source_spacing
            ),
            None,
        )
        for destination_spacing in destination_meta_grid.sample_spacing
    )
    if None in source_axes:
        raise _errors.AssemblyError(
            "component_output_grid_invalid",
            "Encounter 输出网格必须由入射网格的有符号采样轴置换得到",
        )
    rows = tuple(
        tuple(
            (
                _grid_orientation_sign(
                    destination_meta_grid.orientation[destination_axis],
                )
                * _grid_orientation_sign(
                    source_meta_grid.orientation[source_axis],
                )
                if candidate_axis == source_axis
                else 0
            )
            for candidate_axis in range(2)
        )
        for destination_axis, source_axis in enumerate(source_axes)
    )
    transport = _route_geometry._RouteBasisTransport(
        destination_yx_from_source_yx=cast(
            "_route_geometry._SignedPermutation2",
            rows,
        ),
        destination_hv_from_source_hv=((1, 0), (0, 1)),
    )
    with _meta_inference._real_grid_precheck():
        return _route_geometry._transport_grid(
            source_real_grid,
            transport=transport,
        )


def _grid_orientation_sign(orientation: str) -> int:
    return 1 if orientation == "increasing" else -1


def _real_output_grid_for_plan_step(
    *,
    assembly: Assembly,
    step: _ExecutionStep,
    inputs: tuple[Any, ...],
    input_coordinates: tuple[_StableValueCoordinate, ...],
    real_grids: dict[_StableValueCoordinate, SpatialGrid],
    real_grid_assembly: Assembly | None,
) -> SpatialGrid | None:
    del assembly
    if real_grid_assembly is None:
        return None
    if RayBundle in step.output_value_kinds:
        return None
    with _meta_inference._real_grid_precheck():
        if step.is_source:
            return real_grid_assembly._anchor_grid(  # noqa: SLF001
                step.component_name
            )
        input_grids = tuple(
            real_grids[coordinate]
            for coordinate in input_coordinates
        )
        output_grid = input_grids[0]
        if any(
            not output_grid.is_physically_equivalent_to(grid)
            for grid in input_grids[1:]
        ):
            raise _errors.AssemblyError(
                "component_input_grid_mismatch",
                "同一个光学动作的全部输入必须位于完全相同的空间网格",
            )
        original_component = real_grid_assembly._component(  # noqa: SLF001
            step.component_name
        )
        resolver = getattr(
            original_component,
            "_output_grid_for",
            None,
        )
        if not callable(resolver):
            return output_grid
        real_grid_inputs = tuple(
            replace(value, grid=grid)
            for value, grid in zip(
                inputs,
                input_grids,
                strict=True,
            )
        )
        resolved_grid = resolver(*real_grid_inputs)
        if not isinstance(resolved_grid, SpatialGrid):
            raise _errors.AssemblyError(
                "component_output_grid_invalid",
                "组件的输出网格解析必须返回 SpatialGrid",
            )
        return resolved_grid


def _call_component(
    component: torch.nn.Module,
    *,
    component_name: str,
    inputs: tuple[Any, ...],
    generator_for: Callable[[str], torch.Generator] | None,
    is_generator_accepted: bool,
) -> object:
    if not is_generator_accepted or generator_for is None:
        return component(*inputs)
    return component(
        *inputs,
        generator=generator_for(component_name),
    )


def _validated_outputs(
    step: _ExecutionStep,
    result: object,
) -> tuple[_PhysicalValue, ...]:
    raw_values = result if isinstance(result, tuple) else (result,)
    if not raw_values or not all(
        isinstance(value, (OpticalField, Intensity, RayBundle))
        for value in raw_values
    ):
        raise _errors.AssemblyError(
            f"assembly_output_value_invalid:{step.component_name}",
            f"组件 {step.component_name} 只能返回 OpticalField、"
            "Intensity、RayBundle 或由它们构成的元组",
        )
    is_tuple_result = isinstance(result, tuple)
    if is_tuple_result and len(result) != len(step.output_ports):
        raise _errors.AssemblyError(
            "assembly_output_port_arity_mismatch:"
            f"{step.component_name}:"
            f"expected_{len(step.output_ports)}_got_{len(result)}",
            f"组件 {step.component_name} 的返回数量必须与输出端口一致",
        )
    if not is_tuple_result and step.output_ports != (None,):
        raise _errors.AssemblyError(
            "assembly_output_port_arity_mismatch:"
            f"{step.component_name}:expected_"
            f"{len(step.output_ports)}_got_1",
            f"多输出组件 {step.component_name} 必须返回元组",
        )
    values = cast(tuple[_PhysicalValue, ...], tuple(raw_values))
    for value, kind in zip(values, step.output_value_kinds, strict=True):
        if not isinstance(value, kind):
            raise _errors.AssemblyError(
                f"assembly_output_value_kind_mismatch:"
                f"{step.component_name}",
                f"组件 {step.component_name} 的输出端口声明产出 "
                f"{kind.__name__}，实际返回了 {type(value).__name__}",
            )
    return values


def _collect_physical_state_findings(
    assembly: Assembly,
    *,
    facts: _FrozenAssembly,
    findings: list[str],
) -> None:
    for step in facts.steps:
        component = assembly._component(step.component_name)  # noqa: SLF001
        validator = getattr(component, "_validate_physical_state", None)
        if not callable(validator):
            continue
        try:
            validator()
        except Exception as error:
            findings.append(
                _step_failure_finding(assembly, step, error)
            )


def _collect_meta_inference_findings(
    assembly: Assembly,
    *,
    facts: _FrozenAssembly,
    findings: list[str],
) -> None:
    try:
        with _meta_inference._meta_inference(
            tuple(assembly.modules()),
        ) as sandbox:
            meta_assembly = cast(
                "Assembly",
                sandbox.module(assembly),
            )
            _replay_facts(
                meta_assembly,
                facts,
                generator_for=None,
                validate_value=None,
                findings=findings,
                real_grid_assembly=assembly,
            )
    except Exception as error:
        findings.append(
            "assembly_meta_inference_failed:"
            f"{_nested_error_identity(error)}"
        )

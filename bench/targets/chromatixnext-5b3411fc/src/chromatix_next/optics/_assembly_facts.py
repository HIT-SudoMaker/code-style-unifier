from __future__ import annotations

from dataclasses import dataclass, replace

from . import _route_geometry
from ._role_contract import _ComponentContract, _domain_of, _PhysicalValueKind


@dataclass(frozen=True, slots=True)
class _Connection:
    """
    记录一个已命名输出到已命名输入的作者连接

    """

    source_name: str
    source_port: str | None
    destination_name: str
    destination_port: str | None

@dataclass(frozen=True, slots=True)
class _Exposure:
    """
    记录一个组件输出的非消耗作者暴露

    """

    component_name: str
    port: str | None
    name: str


@dataclass(frozen=True, slots=True)
class _DirectionalOwnerFact:
    """
    记录一个 directional owner 的稳定名称与封闭 Terminal 拓扑

    """

    owner_name: str
    terminal_order: tuple[str, ...]
    routes: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class _EncounterDeclaration:
    """
    记录 Freeze 输入的一次 state-free Encounter 声明

    """

    encounter_name: str
    owner_name: str
    domain: str
    incident_terminals: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _DirectionalValueCoordinate:
    """
    用稳定名称标识一次 Encounter 的 incident 或 outgoing 值

    """

    encounter_name: str
    owner_name: str
    terminal: str
    direction: str


@dataclass(frozen=True, slots=True)
class _ComponentValueCoordinate:
    """
    用稳定 Component 名称与 Port 标识普通 value endpoint

    """

    component_name: str
    port: str | None
    direction: str


@dataclass(frozen=True, slots=True)
class _PlanConnectionDeclaration:
    """
    记录 Port/Terminal 类别不混用的一条冻结 value-flow 输入

    """

    source_name: str
    destination_name: str
    source_port: str | None = None
    destination_port: str | None = None
    source_terminal: str | None = None
    destination_terminal: str | None = None


@dataclass(frozen=True, slots=True)
class _ValueFlowFact:
    """
    记录普通与 directional endpoint 之间的一条稳定值流

    """

    source_value: _ComponentValueCoordinate | _DirectionalValueCoordinate
    destination_value: _ComponentValueCoordinate | _DirectionalValueCoordinate


@dataclass(frozen=True, slots=True)
class _ReplayStepCoordinate:
    """
    定位唯一合并 replay order 中的普通 Component 或 Encounter

    """

    category: str
    name: str
    owner_name: str | None


@dataclass(frozen=True, slots=True)
class _ReleaseFact:
    """
    记录一个 produced value 在统一 replay order 中的最后使用位置

    """

    value: _ComponentValueCoordinate | _DirectionalValueCoordinate
    after_step: _ReplayStepCoordinate


@dataclass(frozen=True, slots=True)
class _EncounterFact:
    """
    记录一次有限 Wave 或 Ray Encounter 的冻结执行事实

    """

    encounter_name: str
    owner_name: str
    domain: str
    incident_terminals: tuple[str, ...]
    incident_values: tuple[_DirectionalValueCoordinate, ...]
    outgoing_values: tuple[_DirectionalValueCoordinate, ...]


@dataclass(frozen=True, slots=True)
class _RouteDeclaration:
    """
    记录两个 Encounter endpoint 之间待冻结的有限 Route

    """

    source_encounter_name: str
    source_terminal: str
    destination_encounter_name: str
    destination_terminal: str
    inline_component_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _RouteSegmentFact:
    """
    记录只拥有 endpoint、兼容性与基传输定位的 Route Segment

    """

    route_name: str
    source_value: _DirectionalValueCoordinate
    destination_value: _DirectionalValueCoordinate
    inline_component_names: tuple[str, ...]
    source_frame: _route_geometry._TerminalFrameInput | None = None
    destination_frame: _route_geometry._TerminalFrameInput | None = None
    basis_transport: _route_geometry._RouteBasisTransport | None = None


@dataclass(frozen=True, slots=True)
class _RouteEndDeclaration:
    """
    记录一个 outgoing directional value 的显式系统边界声明

    """

    encounter_name: str
    terminal: str
    reason: str = "outside_modeled_system"


@dataclass(frozen=True, slots=True)
class _RouteEndFact:
    """
    记录一个不计算、不测量且无状态的 Route End

    """

    value: _DirectionalValueCoordinate
    reason: str


@dataclass(frozen=True, slots=True)
class _DirectionalExposureDeclaration:
    """
    记录一个 outgoing directional value 的作者暴露

    """

    encounter_name: str
    terminal: str
    name: str


@dataclass(frozen=True, slots=True)
class _DirectionalExposureFact:
    """
    记录一个 directional Named Output 的稳定值坐标

    """

    name: str
    value: _DirectionalValueCoordinate


@dataclass(frozen=True, slots=True)
class _DirectionalDispositionFact:
    """
    汇总一个 produced directional value 的连接、暴露与 Route End 投影

    """

    value: _DirectionalValueCoordinate
    connection_targets: tuple[
        _ComponentValueCoordinate | _DirectionalValueCoordinate,
        ...,
    ]
    route_names: tuple[str, ...]
    exposure_names: tuple[str, ...]
    route_end_reason: str | None


@dataclass(frozen=True, slots=True)
class _DirectionalAncestryFact:
    """
    记录从唯一 produced-value 计划派生的因果祖先坐标

    """

    value: _ComponentValueCoordinate | _DirectionalValueCoordinate
    ancestors: tuple[
        _ComponentValueCoordinate | _DirectionalValueCoordinate,
        ...,
    ]


@dataclass(frozen=True, slots=True)
class _DirectionalExecutionStep:
    """
    记录一次 Encounter 的冻结 replay 与 release 投影

    """

    encounter_name: str
    owner_name: str
    domain: str
    input_values: tuple[_DirectionalValueCoordinate, ...]
    output_values: tuple[_DirectionalValueCoordinate, ...]
    release_values: tuple[_DirectionalValueCoordinate, ...]


@dataclass(frozen=True, slots=True)
class _ValueIdentity:
    """
    标识冻结执行步骤产生的一个物理值

    """

    step_index: int
    output_ordinal: int


@dataclass(frozen=True, slots=True)
class _ExecutionStep:
    """
    记录冻结汇编中的单个组件重放步骤

    """

    component_name: str
    is_source: bool
    is_generator_accepted: bool
    input_values: tuple[_ValueIdentity, ...]
    output_ports: tuple[str | None, ...]
    output_values: tuple[_ValueIdentity, ...]
    output_value_kinds: tuple[_PhysicalValueKind, ...]
    release_values: tuple[_ValueIdentity, ...]


@dataclass(frozen=True, slots=True)
class _FrozenAssembly:
    """
    承载汇编检查后可重复使用的执行事实

    """

    steps: tuple[_ExecutionStep, ...]
    exposures: tuple[tuple[str, _ValueIdentity], ...]
    connections: tuple[_Connection, ...] = ()
    directional_owners: tuple[_DirectionalOwnerFact, ...] = ()
    encounters: tuple[_EncounterFact, ...] = ()
    route_segments: tuple[_RouteSegmentFact, ...] = ()
    route_ends: tuple[_RouteEndFact, ...] = ()
    directional_steps: tuple[_DirectionalExecutionStep, ...] = ()
    ancestry: tuple[_DirectionalAncestryFact, ...] = ()
    dispositions: tuple[_DirectionalDispositionFact, ...] = ()
    directional_exposures: tuple[_DirectionalExposureFact, ...] = ()
    exposure_order: tuple[str, ...] = ()
    value_flows: tuple[_ValueFlowFact, ...] = ()
    replay_order: tuple[_ReplayStepCoordinate, ...] = ()
    releases: tuple[_ReleaseFact, ...] = ()


def _build_facts(
    *,
    component_names: tuple[str, ...],
    contracts: dict[str, _ComponentContract],
    connections: list[_Connection],
    exposures: list[_Exposure],
) -> tuple[_FrozenAssembly | None, list[str]]:
    findings = list(
        _assembly_empty_output_findings(
            executable_names=component_names,
            exposed_names=tuple(exposure.name for exposure in exposures),
        )
    )
    if not component_names:
        return None, findings

    incoming, outgoing = _adjacency(
        component_names=component_names,
        connections=connections,
    )
    ordered_names, cyclic_names = _topological_names(
        component_names=component_names,
        incoming=incoming,
        outgoing=outgoing,
    )
    if cyclic_names is not None:
        findings.append(
            f"assembly_topology_cycle:{'->'.join(sorted(cyclic_names))}"
        )
        return None, findings

    prior_connections: list[_Connection] = []
    for connection in connections:
        connection_finding = _connection_value_finding(
            contracts=contracts,
            connection=connection,
        )
        if connection_finding is not None:
            findings.append(connection_finding)
        output_finding = _output_port_reused_finding(
            connections=prior_connections,
            candidate=connection,
        )
        if output_finding is not None:
            findings.append(output_finding)
        prior_connections.append(connection)

    prior_exposures: list[_Exposure] = []
    for exposure in exposures:
        exposure_finding = _exposure_conflict_finding(
            exposures=prior_exposures,
            candidate=exposure,
        )
        if exposure_finding is not None:
            findings.append(exposure_finding)
        prior_exposures.append(exposure)

    for component_name in ordered_names:
        contract = contracts[component_name]
        component_inputs = incoming[component_name]
        if contract.role == "source":
            if component_inputs:
                findings.append(
                    f"assembly_input_port_count_mismatch:{component_name}"
                )
            continue
        prior_component_inputs: list[_Connection] = []
        for connection in component_inputs:
            input_finding = _input_port_reused_finding(
                connections=prior_component_inputs,
                candidate=connection,
            )
            if input_finding is not None:
                findings.append(input_finding)
            prior_component_inputs.append(connection)
        for port in contract.input_ports:
            port_count = sum(
                connection.destination_port == port
                for connection in component_inputs
            )
            if port_count == 0:
                findings.append(
                    f"assembly_input_missing:{component_name}:{port}"
                )
        if len(component_inputs) != len(contract.input_ports) and not any(
            finding.startswith(f"assembly_input_missing:{component_name}:")
            or finding.startswith(
                f"assembly_input_port_count_mismatch:{component_name}"
            )
            for finding in findings
        ):
            findings.append(
                f"assembly_input_arity_mismatch:{component_name}:"
                f"expected_{len(contract.input_ports)}_"
                f"got_{len(component_inputs)}"
            )
    if findings:
        return None, findings

    findings.extend(
        _exposed_path_component_findings(
            component_names=component_names,
            incoming_names={
                component_name: tuple(
                    connection.source_name
                    for connection in component_incoming
                )
                for component_name, component_incoming in incoming.items()
            },
            exposed_names=tuple(
                exposure.component_name
                for exposure in exposures
            ),
        )
    )
    if findings:
        return None, findings

    identity_by_anchor: dict[
        tuple[str, str | None],
        _ValueIdentity,
    ] = {}
    steps: list[_ExecutionStep] = []
    for step_index, component_name in enumerate(ordered_names):
        contract = contracts[component_name]
        output_values = tuple(
            _ValueIdentity(step_index, output_ordinal)
            for output_ordinal in range(len(contract.output_ports))
        )
        for port, value_identity in zip(
            contract.output_ports,
            output_values,
            strict=True,
        ):
            identity_by_anchor[(component_name, port)] = value_identity
        component_inputs = _ordered_connections(
            component_name=component_name,
            connections=incoming[component_name],
            contracts=contracts,
        )
        input_values = tuple(
            identity_by_anchor[
                (
                    connection.source_name,
                    connection.source_port,
                )
            ]
            for connection in component_inputs
        )
        steps.append(
            _ExecutionStep(
                component_name=component_name,
                is_source=contract.role == "source",
                is_generator_accepted=contract.is_generator_accepted,
                input_values=input_values,
                output_ports=contract.output_ports,
                output_values=output_values,
                output_value_kinds=contract.output_values,
                release_values=(),
            )
        )

    exposure_facts = tuple(
        (
            exposure.name,
            identity_by_anchor[
                (exposure.component_name, exposure.port)
            ],
        )
        for exposure in exposures
    )
    released_steps = _with_release_facts(
        steps=tuple(steps),
        exposures=exposure_facts,
    )
    value_flows = _ordinary_value_flows(
        steps=released_steps,
        connections=tuple(connections),
    )
    replay_order = tuple(
        _ReplayStepCoordinate(
            category="component",
            name=step.component_name,
            owner_name=None,
        )
        for step in released_steps
    )
    return (
        _FrozenAssembly(
            steps=released_steps,
            exposures=exposure_facts,
            connections=tuple(connections),
            exposure_order=tuple(name for name, _value in exposure_facts),
            value_flows=value_flows,
            replay_order=replay_order,
            releases=_unified_release_facts(
                steps=released_steps,
                encounters=(),
                value_flows=value_flows,
                replay_order=replay_order,
                ordinary_exposures=exposure_facts,
                directional_exposures=(),
            ),
        ),
        findings,
    )


def _build_directional_facts(
    *,
    ordinary_facts: _FrozenAssembly | None = None,
    ordinary_names: tuple[str, ...] = (),
    owners: tuple[_DirectionalOwnerFact, ...],
    encounters: tuple[_EncounterDeclaration, ...],
    plan_connections: tuple[_PlanConnectionDeclaration, ...] = (),
    routes: tuple[_RouteDeclaration, ...] = (),
    route_ends: tuple[_RouteEndDeclaration, ...] = (),
    exposures: tuple[_DirectionalExposureDeclaration, ...] = (),
    exposure_order: tuple[str, ...] | None = None,
    route_terminal_frames: tuple[
        _route_geometry._TerminalFrameInput,
        ...,
    ] = (),
    propagation_displacements: tuple[
        tuple[str, float | None],
        ...,
    ] = (),
) -> tuple[_FrozenAssembly | None, list[str]]:
    # 从稳定字符串声明构造唯一有限 directional frozen fact
    base_facts = ordinary_facts or _FrozenAssembly(steps=(), exposures=())
    findings: list[str] = []
    owner_by_name = _validated_directional_owners(
        ordinary_names=ordinary_names,
        owners=owners,
        findings=findings,
    )
    encounter_facts = _validated_encounters(
        ordinary_names=ordinary_names,
        owners=owners,
        owner_by_name=owner_by_name,
        encounters=encounters,
        findings=findings,
    )
    if findings:
        return None, findings

    encounter_by_name = {
        encounter.encounter_name: encounter
        for encounter in encounter_facts
    }
    route_facts = _validated_route_segments(
        routes=routes,
        encounter_by_name=encounter_by_name,
        route_terminal_frames=(),
        propagation_displacements=(),
        findings=findings,
    )
    route_end_facts = _validated_route_ends(
        route_ends=route_ends,
        encounter_by_name=encounter_by_name,
        findings=findings,
    )
    exposure_facts = _validated_directional_exposures(
        exposures=exposures,
        encounter_by_name=encounter_by_name,
        findings=findings,
    )
    if findings:
        return None, findings

    value_flows = _validated_plan_value_flows(
        base_facts=base_facts,
        encounters=encounter_facts,
        connections=plan_connections,
        findings=findings,
    )
    if findings:
        return None, findings
    if route_terminal_frames:
        route_facts = _validated_route_segments(
            routes=routes,
            encounter_by_name=encounter_by_name,
            route_terminal_frames=route_terminal_frames,
            propagation_displacements=propagation_displacements,
            findings=findings,
        )
        if findings:
            return None, findings
    value_flows = value_flows + tuple(
        _ValueFlowFact(
            source_value=route.source_value,
            destination_value=route.destination_value,
        )
        for route in route_facts
        if not route.inline_component_names
        and _ValueFlowFact(
            source_value=route.source_value,
            destination_value=route.destination_value,
        )
        not in value_flows
    )

    ordered_encounters, cycle_route = _ordered_directional_encounters(
        encounters=encounter_facts,
        routes=route_facts,
    )
    if cycle_route is not None:
        findings.append(
            _directional_finding(
                "assembly_produced_value_cycle",
                route=cycle_route,
            )
        )
        return None, findings

    replay_order, cycle_coordinate = _unified_replay_order(
        steps=base_facts.steps,
        encounters=ordered_encounters,
        value_flows=value_flows,
        routes=route_facts,
    )
    if cycle_coordinate is not None:
        findings.append(
            _directional_finding(
                "assembly_produced_value_cycle",
                route=cycle_coordinate,
            )
        )
        return None, findings

    ordinary_coordinates = _ordinary_value_coordinates(base_facts.steps)
    incoming_names: dict[str, list[str]] = {
        step.name: []
        for step in replay_order
    }
    for flow in value_flows:
        source_name = _step_coordinate_for_value(flow.source_value).name
        destination_name = _step_coordinate_for_value(
            flow.destination_value
        ).name
        if source_name not in incoming_names[destination_name]:
            incoming_names[destination_name].append(source_name)
    exposed_names = tuple(
        ordinary_coordinates[value].component_name
        for _name, value in base_facts.exposures
    ) + tuple(
        exposure.value.encounter_name
        for exposure in exposure_facts
    )
    if exposed_names:
        findings.extend(
            _exposed_path_component_findings(
                component_names=ordinary_names,
                incoming_names={
                    name: tuple(predecessors)
                    for name, predecessors in incoming_names.items()
                },
                exposed_names=exposed_names,
            )
        )
    if findings:
        return None, findings

    dispositions = _directional_dispositions(
        encounters=ordered_encounters,
        value_flows=value_flows,
        routes=route_facts,
        route_ends=route_end_facts,
        exposures=exposure_facts,
        findings=findings,
    )
    if findings:
        return None, findings
    findings.extend(
        _assembly_empty_output_findings(
            executable_names=(
                ordinary_names
                + tuple(
                    encounter.encounter_name
                    for encounter in ordered_encounters
                )
            ),
            exposed_names=exposed_names,
        )
    )
    if findings:
        return None, findings
    ancestry = _unified_ancestry(
        steps=base_facts.steps,
        encounters=ordered_encounters,
        value_flows=value_flows,
        replay_order=replay_order,
        owner_by_name=owner_by_name,
    )
    directional_steps = _directional_execution_steps(
        encounters=ordered_encounters,
        routes=route_facts,
        route_ends=route_end_facts,
        exposures=exposure_facts,
    )
    ordered_exposure_names = (
        exposure_order
        if exposure_order is not None
        else (
            base_facts.exposure_order
            + tuple(exposure.name for exposure in exposure_facts)
        )
    )
    known_exposure_names = {
        name
        for name, _value in base_facts.exposures
    } | {
        exposure.name
        for exposure in exposure_facts
    }
    if (
        len(ordered_exposure_names) != len(known_exposure_names)
        or set(ordered_exposure_names) != known_exposure_names
    ):
        findings.append(
            _directional_finding(
                "assembly_expose_duplicate_name",
            )
        )
        return None, findings
    return (
        replace(
            base_facts,
            directional_owners=owners,
            encounters=ordered_encounters,
            route_segments=route_facts,
            route_ends=route_end_facts,
            directional_steps=directional_steps,
            ancestry=ancestry,
            dispositions=dispositions,
            directional_exposures=exposure_facts,
            exposure_order=ordered_exposure_names,
            value_flows=value_flows,
            replay_order=replay_order,
            releases=_unified_release_facts(
                steps=base_facts.steps,
                encounters=ordered_encounters,
                value_flows=value_flows,
                replay_order=replay_order,
                ordinary_exposures=base_facts.exposures,
                directional_exposures=exposure_facts,
            ),
        ),
        findings,
    )


def _build_mixed_facts(
    *,
    component_names: tuple[str, ...],
    contracts: dict[str, _ComponentContract],
    ordinary_exposures: tuple[_Exposure, ...],
    owners: tuple[_DirectionalOwnerFact, ...],
    encounters: tuple[_EncounterDeclaration, ...],
    plan_connections: tuple[_PlanConnectionDeclaration, ...],
    routes: tuple[_RouteDeclaration, ...] = (),
    route_ends: tuple[_RouteEndDeclaration, ...] = (),
    directional_exposures: tuple[_DirectionalExposureDeclaration, ...] = (),
    exposure_order: tuple[str, ...] | None = None,
    route_terminal_frames: tuple[
        _route_geometry._TerminalFrameInput,
        ...,
    ] = (),
    propagation_displacements: tuple[
        tuple[str, float | None],
        ...,
    ] = (),
) -> tuple[_FrozenAssembly | None, list[str]]:
    # 从 ordinary contracts 与四种 endpoint flow 构造统一 mixed plan
    ordinary_facts, findings = _ordinary_mixed_seed(
        component_names=component_names,
        contracts=contracts,
        connections=plan_connections,
        exposures=ordinary_exposures,
    )
    if findings or ordinary_facts is None:
        return None, findings
    derived_routes = (
        routes
        if routes
        else _derive_route_declarations(
            encounters=encounters,
            plan_connections=plan_connections,
        )
    )
    return _build_directional_facts(
        ordinary_facts=ordinary_facts,
        ordinary_names=component_names,
        owners=owners,
        encounters=encounters,
        plan_connections=plan_connections,
        routes=derived_routes,
        route_ends=route_ends,
        exposures=directional_exposures,
        exposure_order=exposure_order,
        route_terminal_frames=route_terminal_frames,
        propagation_displacements=propagation_displacements,
    )


def _ordinary_mixed_seed(
    *,
    component_names: tuple[str, ...],
    contracts: dict[str, _ComponentContract],
    connections: tuple[_PlanConnectionDeclaration, ...],
    exposures: tuple[_Exposure, ...],
) -> tuple[_FrozenAssembly | None, list[str]]:
    findings: list[str] = []
    missing_contract = next(
        (
            name
            for name in component_names
            if name not in contracts
        ),
        None,
    )
    if missing_contract is not None:
        return None, [f"assembly_component_unknown:{missing_contract}"]
    identity_by_anchor: dict[tuple[str, str | None], _ValueIdentity] = {}
    steps: list[_ExecutionStep] = []
    for step_index, component_name in enumerate(component_names):
        contract = contracts[component_name]
        output_values = tuple(
            _ValueIdentity(step_index, output_ordinal)
            for output_ordinal in range(len(contract.output_ports))
        )
        for port, value in zip(
            contract.output_ports,
            output_values,
            strict=True,
        ):
            identity_by_anchor[(component_name, port)] = value
        steps.append(
            _ExecutionStep(
                component_name=component_name,
                is_source=contract.role == "source",
                is_generator_accepted=contract.is_generator_accepted,
                input_values=(),
                output_ports=contract.output_ports,
                output_values=output_values,
                output_value_kinds=contract.output_values,
                release_values=(),
            )
        )
    completed_steps: list[_ExecutionStep] = []
    component_name_set = set(component_names)
    for step in steps:
        contract = contracts[step.component_name]
        incoming = tuple(
            connection
            for connection in connections
            if connection.destination_name == step.component_name
        )
        if contract.role == "source" and incoming:
            findings.append(
                f"assembly_input_port_count_mismatch:{step.component_name}"
            )
            completed_steps.append(step)
            continue
        input_values: list[_ValueIdentity] = []
        for port in contract.input_ports:
            producers = tuple(
                connection
                for connection in incoming
                if connection.destination_port == port
                and connection.destination_terminal is None
            )
            if not producers:
                findings.append(
                    f"assembly_input_missing:{step.component_name}:{port}"
                )
                continue
            if len(producers) != 1:
                findings.append(
                    "assembly_input_port_count_mismatch:"
                    f"{step.component_name}:{port}"
                )
                continue
            producer = producers[0]
            if producer.source_name in component_name_set:
                source_identity = identity_by_anchor.get(
                    (producer.source_name, producer.source_port)
                )
                if source_identity is None:
                    findings.append(
                        "assembly_connect_endpoint_category_invalid:"
                        f"{producer.source_name}:{producer.source_port}"
                    )
                    continue
                input_values.append(source_identity)
        completed_steps.append(
            replace(
                step,
                input_values=tuple(input_values),
            )
        )
    exposure_facts: list[tuple[str, _ValueIdentity]] = []
    for exposure in exposures:
        value = identity_by_anchor.get(
            (exposure.component_name, exposure.port)
        )
        if value is None:
            findings.append(
                "assembly_expose_output_unknown:"
                f"{exposure.component_name}:{exposure.port}"
            )
            continue
        exposure_facts.append((exposure.name, value))
    if findings:
        return None, findings
    ordinary_connections = tuple(
        _Connection(
            source_name=connection.source_name,
            source_port=connection.source_port,
            destination_name=connection.destination_name,
            destination_port=connection.destination_port,
        )
        for connection in connections
        if connection.source_name in component_name_set
        and connection.destination_name in component_name_set
    )
    return (
        _FrozenAssembly(
            steps=tuple(completed_steps),
            exposures=tuple(exposure_facts),
            connections=ordinary_connections,
            exposure_order=tuple(name for name, _value in exposure_facts),
        ),
        findings,
    )


def _directional_finding(
    base: str,
    *,
    owner: str = "-",
    encounter: str = "-",
    incident: str = "-",
    outgoing: str = "-",
    route: str = "-",
    underlying: str = "-",
) -> str:
    return (
        f"{base}:owner={owner}:encounter={encounter}:incident={incident}:"
        f"outgoing={outgoing}:route={route}:underlying={underlying}"
    )


def _ordinary_value_coordinates(
    steps: tuple[_ExecutionStep, ...],
) -> dict[_ValueIdentity, _ComponentValueCoordinate]:
    coordinates: dict[_ValueIdentity, _ComponentValueCoordinate] = {}
    for step in steps:
        for port, value in zip(
            step.output_ports,
            step.output_values,
            strict=True,
        ):
            coordinates[value] = _ComponentValueCoordinate(
                component_name=step.component_name,
                port=port,
                direction="output",
            )
    return coordinates


def _ordinary_value_flows(
    *,
    steps: tuple[_ExecutionStep, ...],
    connections: tuple[_Connection, ...],
) -> tuple[_ValueFlowFact, ...]:
    output_by_anchor = {
        (coordinate.component_name, coordinate.port): coordinate
        for coordinate in _ordinary_value_coordinates(steps).values()
    }
    return tuple(
        _ValueFlowFact(
            source_value=output_by_anchor[
                (connection.source_name, connection.source_port)
            ],
            destination_value=_ComponentValueCoordinate(
                component_name=connection.destination_name,
                port=connection.destination_port,
                direction="input",
            ),
        )
        for connection in connections
    )


def _validated_plan_value_flows(
    *,
    base_facts: _FrozenAssembly,
    encounters: tuple[_EncounterFact, ...],
    connections: tuple[_PlanConnectionDeclaration, ...],
    findings: list[str],
) -> tuple[_ValueFlowFact, ...]:
    component_steps = {
        step.component_name: step
        for step in base_facts.steps
    }
    encounter_by_name = {
        encounter.encounter_name: encounter
        for encounter in encounters
    }
    ordinary_flows = (
        base_facts.value_flows
        if base_facts.value_flows
        else _ordinary_value_flows(
            steps=base_facts.steps,
            connections=base_facts.connections,
        )
    )
    flows = list(ordinary_flows)
    for connection in connections:
        source_step = component_steps.get(connection.source_name)
        source_encounter = encounter_by_name.get(connection.source_name)
        destination_step = component_steps.get(connection.destination_name)
        destination_encounter = encounter_by_name.get(
            connection.destination_name
        )
        source_categories = sum(
            candidate is not None
            for candidate in (source_step, source_encounter)
        )
        destination_categories = sum(
            candidate is not None
            for candidate in (destination_step, destination_encounter)
        )
        if source_categories != 1 or destination_categories != 1:
            findings.append(
                _directional_finding(
                    "assembly_connect_endpoint_category_invalid",
                    encounter=(
                        connection.source_name
                        if source_categories != 1
                        else connection.destination_name
                    ),
                )
            )
            continue
        source_value = _plan_source_value(
            connection=connection,
            component_step=source_step,
            encounter=source_encounter,
            findings=findings,
        )
        destination_value = _plan_destination_value(
            connection=connection,
            component_step=destination_step,
            encounter=destination_encounter,
            findings=findings,
        )
        if source_value is None or destination_value is None:
            continue
        flow = _ValueFlowFact(
            source_value=source_value,
            destination_value=destination_value,
        )
        if flow not in flows:
            flows.append(flow)
    return tuple(flows)


def _plan_source_value(
    *,
    connection: _PlanConnectionDeclaration,
    component_step: _ExecutionStep | None,
    encounter: _EncounterFact | None,
    findings: list[str],
) -> _ComponentValueCoordinate | _DirectionalValueCoordinate | None:
    if component_step is not None:
        if (
            connection.source_terminal is not None
            or connection.source_port not in component_step.output_ports
        ):
            findings.append(
                _directional_finding(
                    "assembly_connect_endpoint_category_invalid",
                )
            )
            return None
        return _ComponentValueCoordinate(
            component_name=component_step.component_name,
            port=connection.source_port,
            direction="output",
        )
    assert encounter is not None
    if connection.source_port is not None or connection.source_terminal is None:
        findings.append(
            _directional_finding(
                "assembly_connect_endpoint_category_invalid",
                owner=encounter.owner_name,
                encounter=encounter.encounter_name,
            )
        )
        return None
    value = _value_at_terminal(
        encounter.outgoing_values,
        connection.source_terminal,
    )
    if value is None:
        findings.append(
            _directional_finding(
                "assembly_connect_structural_zero",
                owner=encounter.owner_name,
                encounter=encounter.encounter_name,
                outgoing=connection.source_terminal,
            )
        )
    return value


def _plan_destination_value(
    *,
    connection: _PlanConnectionDeclaration,
    component_step: _ExecutionStep | None,
    encounter: _EncounterFact | None,
    findings: list[str],
) -> _ComponentValueCoordinate | _DirectionalValueCoordinate | None:
    if component_step is not None:
        if connection.destination_terminal is not None:
            findings.append(
                _directional_finding(
                    "assembly_connect_endpoint_category_invalid",
                )
            )
            return None
        return _ComponentValueCoordinate(
            component_name=component_step.component_name,
            port=connection.destination_port,
            direction="input",
        )
    assert encounter is not None
    if (
        connection.destination_port is not None
        or connection.destination_terminal is None
    ):
        findings.append(
            _directional_finding(
                "assembly_connect_endpoint_category_invalid",
                owner=encounter.owner_name,
                encounter=encounter.encounter_name,
            )
        )
        return None
    value = _value_at_terminal(
        encounter.incident_values,
        connection.destination_terminal,
    )
    if value is None:
        findings.append(
            _directional_finding(
                "assembly_connect_terminal_direction_invalid",
                owner=encounter.owner_name,
                encounter=encounter.encounter_name,
                incident=connection.destination_terminal,
            )
        )
    return value


def _validated_directional_owners(
    *,
    ordinary_names: tuple[str, ...],
    owners: tuple[_DirectionalOwnerFact, ...],
    findings: list[str],
) -> dict[str, _DirectionalOwnerFact]:
    owner_by_name: dict[str, _DirectionalOwnerFact] = {}
    occupied_names = set(ordinary_names)
    for owner in owners:
        if owner.owner_name in occupied_names:
            findings.append(
                _directional_finding(
                    "assembly_include_directional_owner_duplicate",
                    owner=owner.owner_name,
                )
            )
            continue
        occupied_names.add(owner.owner_name)
        terminals_are_stable = (
            owner.terminal_order
            and len(set(owner.terminal_order)) == len(owner.terminal_order)
            and all(
                isinstance(terminal, str) and terminal
                for terminal in owner.terminal_order
            )
        )
        routes_are_stable = all(
            isinstance(incident, str)
            and isinstance(outgoing, str)
            and incident in owner.terminal_order
            and outgoing in owner.terminal_order
            for incident, outgoing in owner.routes
        )
        if not terminals_are_stable or not routes_are_stable:
            findings.append(
                _directional_finding(
                    "assembly_include_directional_owner_invalid",
                    owner=owner.owner_name,
                )
            )
            continue
        owner_by_name[owner.owner_name] = owner
    return owner_by_name


def _validated_encounters(
    *,
    ordinary_names: tuple[str, ...],
    owners: tuple[_DirectionalOwnerFact, ...],
    owner_by_name: dict[str, _DirectionalOwnerFact],
    encounters: tuple[_EncounterDeclaration, ...],
    findings: list[str],
) -> tuple[_EncounterFact, ...]:
    occupied_names = set(ordinary_names) | {
        owner.owner_name
        for owner in owners
    }
    encounter_facts: list[_EncounterFact] = []
    for encounter in encounters:
        if encounter.encounter_name in occupied_names:
            findings.append(
                _directional_finding(
                    "assembly_encounter_duplicate_name",
                    owner=encounter.owner_name,
                    encounter=encounter.encounter_name,
                )
            )
            continue
        occupied_names.add(encounter.encounter_name)
        owner = owner_by_name.get(encounter.owner_name)
        if owner is None:
            findings.append(
                _directional_finding(
                    "assembly_encounter_owner_unknown",
                    owner=encounter.owner_name,
                    encounter=encounter.encounter_name,
                )
            )
            continue
        if not encounter.incident_terminals:
            findings.append(
                _directional_finding(
                    "assembly_encounter_incident_empty",
                    owner=encounter.owner_name,
                    encounter=encounter.encounter_name,
                )
            )
            continue
        duplicate_terminal = _first_duplicate(encounter.incident_terminals)
        if duplicate_terminal is not None:
            findings.append(
                _directional_finding(
                    "assembly_encounter_incident_duplicate",
                    owner=encounter.owner_name,
                    encounter=encounter.encounter_name,
                    incident=duplicate_terminal,
                )
            )
            continue
        unknown_terminal = next(
            (
                terminal
                for terminal in encounter.incident_terminals
                if terminal not in owner.terminal_order
            ),
            None,
        )
        if unknown_terminal is not None:
            findings.append(
                _directional_finding(
                    "assembly_encounter_terminal_unknown",
                    owner=encounter.owner_name,
                    encounter=encounter.encounter_name,
                    incident=unknown_terminal,
                )
            )
            continue
        if encounter.domain not in ("wave", "ray"):
            findings.append(
                _directional_finding(
                    "assembly_encounter_owner_unsupported",
                    owner=encounter.owner_name,
                    encounter=encounter.encounter_name,
                )
            )
            continue
        if encounter.domain == "ray" and len(encounter.incident_terminals) != 1:
            findings.append(
                _directional_finding(
                    "assembly_encounter_ray_multiple_incident",
                    owner=encounter.owner_name,
                    encounter=encounter.encounter_name,
                    incident=encounter.incident_terminals[1],
                )
            )
            continue
        incident_set = set(encounter.incident_terminals)
        canonical_incidents = tuple(
            terminal
            for terminal in owner.terminal_order
            if terminal in incident_set
        )
        outgoing_terminals = tuple(
            terminal
            for terminal in owner.terminal_order
            if any(
                incident in incident_set and outgoing == terminal
                for incident, outgoing in owner.routes
            )
        )
        incident_values = tuple(
            _DirectionalValueCoordinate(
                encounter_name=encounter.encounter_name,
                owner_name=encounter.owner_name,
                terminal=terminal,
                direction="incident",
            )
            for terminal in canonical_incidents
        )
        outgoing_values = tuple(
            _DirectionalValueCoordinate(
                encounter_name=encounter.encounter_name,
                owner_name=encounter.owner_name,
                terminal=terminal,
                direction="outgoing",
            )
            for terminal in outgoing_terminals
        )
        encounter_facts.append(
            _EncounterFact(
                encounter_name=encounter.encounter_name,
                owner_name=encounter.owner_name,
                domain=encounter.domain,
                incident_terminals=canonical_incidents,
                incident_values=incident_values,
                outgoing_values=outgoing_values,
            )
        )
    return tuple(encounter_facts)


def _first_duplicate(values: tuple[str, ...]) -> str | None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


def _derive_route_declarations(
    *,
    encounters: tuple[_EncounterDeclaration, ...],
    plan_connections: tuple[_PlanConnectionDeclaration, ...],
) -> tuple[_RouteDeclaration, ...]:
    # Route 只从冻结的 produced-value path 派生，不作自动光路发现
    encounter_names = {
        encounter.encounter_name
        for encounter in encounters
    }
    routes: list[_RouteDeclaration] = []
    for connection in plan_connections:
        if (
            connection.source_name not in encounter_names
            or connection.source_terminal is None
        ):
            continue
        _follow_route_path(
            source_encounter_name=connection.source_name,
            source_terminal=connection.source_terminal,
            connection=connection,
            encounter_names=encounter_names,
            plan_connections=plan_connections,
            inline_component_names=(),
            visited_component_names=(),
            routes=routes,
        )
    return tuple(dict.fromkeys(routes))


def _follow_route_path(
    *,
    source_encounter_name: str,
    source_terminal: str,
    connection: _PlanConnectionDeclaration,
    encounter_names: set[str],
    plan_connections: tuple[_PlanConnectionDeclaration, ...],
    inline_component_names: tuple[str, ...],
    visited_component_names: tuple[str, ...],
    routes: list[_RouteDeclaration],
) -> None:
    destination_name = connection.destination_name
    if destination_name in encounter_names:
        if connection.destination_terminal is None:
            return
        routes.append(
            _RouteDeclaration(
                source_encounter_name=source_encounter_name,
                source_terminal=source_terminal,
                destination_encounter_name=destination_name,
                destination_terminal=connection.destination_terminal,
                inline_component_names=inline_component_names,
            )
        )
        return
    if destination_name in visited_component_names:
        return
    next_inline_names = (*inline_component_names, destination_name)
    next_visited_names = (*visited_component_names, destination_name)
    for next_connection in plan_connections:
        if next_connection.source_name != destination_name:
            continue
        _follow_route_path(
            source_encounter_name=source_encounter_name,
            source_terminal=source_terminal,
            connection=next_connection,
            encounter_names=encounter_names,
            plan_connections=plan_connections,
            inline_component_names=next_inline_names,
            visited_component_names=next_visited_names,
            routes=routes,
        )


def _route_name(route: _RouteDeclaration) -> str:
    return (
        f"{route.source_encounter_name}.{route.source_terminal}.outgoing__to__"
        f"{route.destination_encounter_name}.{route.destination_terminal}.incident"
    )


def _value_at_terminal(
    values: tuple[_DirectionalValueCoordinate, ...],
    terminal: str,
) -> _DirectionalValueCoordinate | None:
    return next(
        (
            value
            for value in values
            if value.terminal == terminal
        ),
        None,
    )


def _validated_route_segments(
    *,
    routes: tuple[_RouteDeclaration, ...],
    encounter_by_name: dict[str, _EncounterFact],
    route_terminal_frames: tuple[
        _route_geometry._TerminalFrameInput,
        ...,
    ],
    propagation_displacements: tuple[
        tuple[str, float | None],
        ...,
    ],
    findings: list[str],
) -> tuple[_RouteSegmentFact, ...]:
    frame_by_anchor = {
        (frame.owner_name, frame.terminal): frame
        for frame in route_terminal_frames
    }
    displacement_by_component = dict(propagation_displacements)
    route_facts: list[_RouteSegmentFact] = []
    for route in routes:
        source = encounter_by_name.get(route.source_encounter_name)
        destination = encounter_by_name.get(route.destination_encounter_name)
        route_name = _route_name(route)
        if source is None or destination is None:
            missing = source if destination is None else destination
            findings.append(
                _directional_finding(
                    "assembly_connect_endpoint_category_invalid",
                    owner="-" if missing is None else missing.owner_name,
                    encounter=(
                        route.source_encounter_name
                        if source is None
                        else route.destination_encounter_name
                    ),
                    outgoing=route.source_terminal,
                    route=route_name,
                )
            )
            continue
        source_value = _value_at_terminal(
            source.outgoing_values,
            route.source_terminal,
        )
        destination_value = _value_at_terminal(
            destination.incident_values,
            route.destination_terminal,
        )
        if source_value is None:
            findings.append(
                _directional_finding(
                    "assembly_connect_structural_zero",
                    owner=source.owner_name,
                    encounter=source.encounter_name,
                    outgoing=route.source_terminal,
                    route=route_name,
                )
            )
            continue
        if destination_value is None:
            findings.append(
                _directional_finding(
                    "assembly_connect_terminal_direction_invalid",
                    owner=destination.owner_name,
                    encounter=destination.encounter_name,
                    incident=route.destination_terminal,
                    route=route_name,
                )
            )
            continue
        source_frame = frame_by_anchor.get(
            (source.owner_name, route.source_terminal)
        )
        destination_frame = frame_by_anchor.get(
            (destination.owner_name, route.destination_terminal)
        )
        basis_transport: _route_geometry._RouteBasisTransport | None = None
        if route_terminal_frames:
            if source_frame is None or destination_frame is None:
                findings.append(
                    _route_validation_finding(
                        "assembly_route_segment_geometry_mismatched",
                        route=route,
                        source=source,
                    )
                )
                continue
            displacements = tuple(
                displacement_by_component[name]
                for name in route.inline_component_names
                if name in displacement_by_component
            )
            validation = _route_geometry._validate_route(
                source=source_frame,
                destination=destination_frame,
                propagation_displacements=displacements,
            )
            if validation.failure is not None:
                failure_identity = {
                    "distance_unresolvable": (
                        "assembly_route_segment_distance_unresolvable"
                    ),
                    "geometry_mismatched": (
                        "assembly_route_segment_geometry_mismatched"
                    ),
                    "basis_incompatible": (
                        "assembly_route_segment_basis_incompatible"
                    ),
                }[validation.failure]
                findings.append(
                    _route_validation_finding(
                        failure_identity,
                        route=route,
                        source=source,
                    )
                )
                continue
            basis_transport = validation.basis_transport
        route_facts.append(
            _RouteSegmentFact(
                route_name=route_name,
                source_value=source_value,
                destination_value=destination_value,
                inline_component_names=route.inline_component_names,
                source_frame=source_frame,
                destination_frame=destination_frame,
                basis_transport=basis_transport,
            )
        )
    return tuple(route_facts)


def _route_validation_finding(
    base: str,
    *,
    route: _RouteDeclaration,
    source: _EncounterFact,
) -> str:
    return _directional_finding(
        base,
        owner=source.owner_name,
        encounter=source.encounter_name,
        incident=route.destination_terminal,
        outgoing=route.source_terminal,
        route=_route_name(route),
    )


def _validated_route_ends(
    *,
    route_ends: tuple[_RouteEndDeclaration, ...],
    encounter_by_name: dict[str, _EncounterFact],
    findings: list[str],
) -> tuple[_RouteEndFact, ...]:
    route_end_facts: list[_RouteEndFact] = []
    for route_end in route_ends:
        encounter = encounter_by_name.get(route_end.encounter_name)
        if encounter is None:
            findings.append(
                _directional_finding(
                    "assembly_route_end_output_unknown",
                    encounter=route_end.encounter_name,
                    outgoing=route_end.terminal,
                )
            )
            continue
        value = _value_at_terminal(
            encounter.outgoing_values,
            route_end.terminal,
        )
        if value is None:
            findings.append(
                _directional_finding(
                    "assembly_route_end_output_unknown",
                    owner=encounter.owner_name,
                    encounter=encounter.encounter_name,
                    outgoing=route_end.terminal,
                )
            )
            continue
        if route_end.reason != "outside_modeled_system":
            findings.append(
                _directional_finding(
                    "assembly_route_end_reason_invalid",
                    owner=encounter.owner_name,
                    encounter=encounter.encounter_name,
                    outgoing=route_end.terminal,
                )
            )
            continue
        route_end_facts.append(
            _RouteEndFact(
                value=value,
                reason=route_end.reason,
            )
        )
    return tuple(route_end_facts)


def _validated_directional_exposures(
    *,
    exposures: tuple[_DirectionalExposureDeclaration, ...],
    encounter_by_name: dict[str, _EncounterFact],
    findings: list[str],
) -> tuple[_DirectionalExposureFact, ...]:
    exposure_facts: list[_DirectionalExposureFact] = []
    seen_names: set[str] = set()
    for exposure in exposures:
        encounter = encounter_by_name.get(exposure.encounter_name)
        value = (
            None
            if encounter is None
            else _value_at_terminal(
                encounter.outgoing_values,
                exposure.terminal,
            )
        )
        if value is None:
            findings.append(
                _directional_finding(
                    "assembly_connect_terminal_direction_invalid",
                    owner="-" if encounter is None else encounter.owner_name,
                    encounter=exposure.encounter_name,
                    outgoing=exposure.terminal,
                )
            )
            continue
        if exposure.name in seen_names:
            findings.append(
                _directional_finding(
                    "assembly_expose_duplicate_name",
                    owner=value.owner_name,
                    encounter=value.encounter_name,
                    outgoing=value.terminal,
                )
            )
            continue
        seen_names.add(exposure.name)
        exposure_facts.append(
            _DirectionalExposureFact(
                name=exposure.name,
                value=value,
            )
        )
    return tuple(exposure_facts)


def _ordered_directional_encounters(
    *,
    encounters: tuple[_EncounterFact, ...],
    routes: tuple[_RouteSegmentFact, ...],
) -> tuple[tuple[_EncounterFact, ...], str | None]:
    insertion_index = {
        encounter.encounter_name: index
        for index, encounter in enumerate(encounters)
    }
    encounter_by_name = {
        encounter.encounter_name: encounter
        for encounter in encounters
    }
    outgoing_routes = {
        encounter.encounter_name: []
        for encounter in encounters
    }
    degrees = {
        encounter.encounter_name: 0
        for encounter in encounters
    }
    for route in routes:
        source_name = route.source_value.encounter_name
        destination_name = route.destination_value.encounter_name
        outgoing_routes[source_name].append(route)
        degrees[destination_name] += 1
    remaining = set(degrees)
    ordered: list[_EncounterFact] = []
    while remaining:
        available = [
            name
            for name in remaining
            if degrees[name] == 0
        ]
        if not available:
            cycle_routes = [
                route.route_name
                for route in routes
                if route.source_value.encounter_name in remaining
                and route.destination_value.encounter_name in remaining
            ]
            return tuple(ordered), min(cycle_routes)
        name = min(
            available,
            key=lambda candidate: insertion_index[candidate],
        )
        ordered.append(encounter_by_name[name])
        remaining.remove(name)
        for route in outgoing_routes[name]:
            degrees[route.destination_value.encounter_name] -= 1
    return tuple(ordered), None


def _step_coordinate_for_value(
    value: _ComponentValueCoordinate | _DirectionalValueCoordinate,
) -> _ReplayStepCoordinate:
    if isinstance(value, _ComponentValueCoordinate):
        return _ReplayStepCoordinate(
            category="component",
            name=value.component_name,
            owner_name=None,
        )
    return _ReplayStepCoordinate(
        category="encounter",
        name=value.encounter_name,
        owner_name=value.owner_name,
    )


def _unified_replay_order(
    *,
    steps: tuple[_ExecutionStep, ...],
    encounters: tuple[_EncounterFact, ...],
    value_flows: tuple[_ValueFlowFact, ...],
    routes: tuple[_RouteSegmentFact, ...],
) -> tuple[tuple[_ReplayStepCoordinate, ...], str | None]:
    nodes = tuple(
        _ReplayStepCoordinate(
            category="component",
            name=step.component_name,
            owner_name=None,
        )
        for step in steps
    ) + tuple(
        _ReplayStepCoordinate(
            category="encounter",
            name=encounter.encounter_name,
            owner_name=encounter.owner_name,
        )
        for encounter in encounters
    )
    insertion_index = {
        node: index
        for index, node in enumerate(nodes)
    }
    successors = {
        node: []
        for node in nodes
    }
    degrees = {
        node: 0
        for node in nodes
    }
    edges: list[tuple[_ReplayStepCoordinate, _ReplayStepCoordinate, str]] = []
    for flow in value_flows:
        source = _step_coordinate_for_value(flow.source_value)
        destination = _step_coordinate_for_value(flow.destination_value)
        coordinate = (
            f"{source.category}.{source.name}__to__"
            f"{destination.category}.{destination.name}"
        )
        edges.append((source, destination, coordinate))
    for route in routes:
        source = _step_coordinate_for_value(route.source_value)
        destination = _step_coordinate_for_value(route.destination_value)
        edges.append((source, destination, route.route_name))
    for source, destination, _coordinate in edges:
        if source == destination or destination in successors[source]:
            continue
        successors[source].append(destination)
        degrees[destination] += 1
    remaining = set(nodes)
    ordered: list[_ReplayStepCoordinate] = []
    while remaining:
        available = [
            node
            for node in remaining
            if degrees[node] == 0
        ]
        if not available:
            cycle_coordinates = [
                coordinate
                for source, destination, coordinate in edges
                if source in remaining and destination in remaining
            ]
            return tuple(ordered), min(cycle_coordinates)
        node = min(
            available,
            key=lambda candidate: insertion_index[candidate],
        )
        ordered.append(node)
        remaining.remove(node)
        for destination in successors[node]:
            degrees[destination] -= 1
    return tuple(ordered), None


def _unified_release_facts(
    *,
    steps: tuple[_ExecutionStep, ...],
    encounters: tuple[_EncounterFact, ...],
    value_flows: tuple[_ValueFlowFact, ...],
    replay_order: tuple[_ReplayStepCoordinate, ...],
    ordinary_exposures: tuple[tuple[str, _ValueIdentity], ...],
    directional_exposures: tuple[_DirectionalExposureFact, ...],
) -> tuple[_ReleaseFact, ...]:
    ordinary_coordinates = _ordinary_value_coordinates(steps)
    exposed_values = {
        ordinary_coordinates[value]
        for _name, value in ordinary_exposures
        if value in ordinary_coordinates
    } | {
        exposure.value
        for exposure in directional_exposures
    }
    produced_values = tuple(
        coordinate
        for step in steps
        for coordinate in (
            _ComponentValueCoordinate(
                component_name=step.component_name,
                port=port,
                direction="output",
            )
            for port in step.output_ports
        )
    ) + tuple(
        value
        for encounter in encounters
        for value in encounter.outgoing_values
    )
    order_index = {
        coordinate: index
        for index, coordinate in enumerate(replay_order)
    }
    releases: list[_ReleaseFact] = []
    for value in produced_values:
        if value in exposed_values:
            continue
        consumer_steps = tuple(
            _step_coordinate_for_value(flow.destination_value)
            for flow in value_flows
            if flow.source_value == value
        )
        after_step = (
            _step_coordinate_for_value(value)
            if not consumer_steps
            else max(
                consumer_steps,
                key=lambda coordinate: order_index[coordinate],
            )
        )
        releases.append(
            _ReleaseFact(
                value=value,
                after_step=after_step,
            )
        )
    return tuple(releases)


def _directional_dispositions(
    *,
    encounters: tuple[_EncounterFact, ...],
    value_flows: tuple[_ValueFlowFact, ...],
    routes: tuple[_RouteSegmentFact, ...],
    route_ends: tuple[_RouteEndFact, ...],
    exposures: tuple[_DirectionalExposureFact, ...],
    findings: list[str],
) -> tuple[_DirectionalDispositionFact, ...]:
    dispositions: list[_DirectionalDispositionFact] = []
    for encounter in encounters:
        for value in encounter.outgoing_values:
            connection_targets = tuple(
                flow.destination_value
                for flow in value_flows
                if flow.source_value == value
            )
            route_names = tuple(
                route.route_name
                for route in routes
                if route.source_value == value
            )
            exposure_names = tuple(
                exposure.name
                for exposure in exposures
                if exposure.value == value
            )
            ending = next(
                (
                    route_end
                    for route_end in route_ends
                    if route_end.value == value
                ),
                None,
            )
            if ending is not None and (
                connection_targets or route_names or exposure_names
            ):
                findings.append(
                    _directional_finding(
                        "assembly_route_end_output_disposed",
                        owner=value.owner_name,
                        encounter=value.encounter_name,
                        outgoing=value.terminal,
                    )
                )
                continue
            if (
                not connection_targets
                and not route_names
                and not exposure_names
                and ending is None
            ):
                findings.append(
                    _directional_finding(
                        "assembly_directional_output_disposition_missing",
                        owner=value.owner_name,
                        encounter=value.encounter_name,
                        outgoing=value.terminal,
                    )
                )
                continue
            dispositions.append(
                _DirectionalDispositionFact(
                    value=value,
                    connection_targets=connection_targets,
                    route_names=route_names,
                    exposure_names=exposure_names,
                    route_end_reason=(
                        None if ending is None else ending.reason
                    ),
                )
            )
    return tuple(dispositions)


def _unified_ancestry(
    *,
    steps: tuple[_ExecutionStep, ...],
    encounters: tuple[_EncounterFact, ...],
    value_flows: tuple[_ValueFlowFact, ...],
    replay_order: tuple[_ReplayStepCoordinate, ...],
    owner_by_name: dict[str, _DirectionalOwnerFact],
) -> tuple[_DirectionalAncestryFact, ...]:
    stable_value = _ComponentValueCoordinate | _DirectionalValueCoordinate
    ancestors_by_value: dict[stable_value, tuple[stable_value, ...]] = {}
    facts: list[_DirectionalAncestryFact] = []
    source_by_destination = {
        flow.destination_value: flow.source_value
        for flow in value_flows
    }
    step_by_name = {
        step.component_name: step
        for step in steps
    }
    encounter_by_name = {
        encounter.encounter_name: encounter
        for encounter in encounters
    }
    for replay_step in replay_order:
        if replay_step.category == "component":
            step = step_by_name[replay_step.name]
            input_values = tuple(
                destination
                for destination in source_by_destination
                if isinstance(destination, _ComponentValueCoordinate)
                and destination.component_name == step.component_name
                and destination.direction == "input"
            )
            output_values: tuple[stable_value, ...] = tuple(
                _ComponentValueCoordinate(
                    component_name=step.component_name,
                    port=port,
                    direction="output",
                )
                for port in step.output_ports
            )
            contributors_by_output = {
                output: input_values
                for output in output_values
            }
        else:
            encounter = encounter_by_name[replay_step.name]
            input_values = encounter.incident_values
            output_values = encounter.outgoing_values
            incident_by_terminal = {
                value.terminal: value
                for value in encounter.incident_values
            }
            contributors_by_output = {
                output: tuple(
                    incident_by_terminal[incident]
                    for incident, terminal in owner_by_name[
                        encounter.owner_name
                    ].routes
                    if terminal == output.terminal
                    and incident in incident_by_terminal
                )
                for output in output_values
            }
        for input_value in input_values:
            predecessor = source_by_destination.get(input_value)
            ancestors = (
                ()
                if predecessor is None
                else _append_unique(
                    ancestors_by_value[predecessor],
                    (predecessor,),
                )
            )
            ancestors_by_value[input_value] = ancestors
            facts.append(
                _DirectionalAncestryFact(
                    value=input_value,
                    ancestors=ancestors,
                )
            )
        for output_value in output_values:
            ancestors: tuple[stable_value, ...] = ()
            for contributor in contributors_by_output[output_value]:
                ancestors = _append_unique(
                    ancestors,
                    ancestors_by_value[contributor] + (contributor,),
                )
            ancestors_by_value[output_value] = ancestors
            facts.append(
                _DirectionalAncestryFact(
                    value=output_value,
                    ancestors=ancestors,
                )
            )
    return tuple(facts)


def _append_unique(
    values: tuple[
        _ComponentValueCoordinate | _DirectionalValueCoordinate,
        ...,
    ],
    additions: tuple[
        _ComponentValueCoordinate | _DirectionalValueCoordinate,
        ...,
    ],
) -> tuple[_ComponentValueCoordinate | _DirectionalValueCoordinate, ...]:
    result = list(values)
    for addition in additions:
        if addition not in result:
            result.append(addition)
    return tuple(result)


def _directional_execution_steps(
    *,
    encounters: tuple[_EncounterFact, ...],
    routes: tuple[_RouteSegmentFact, ...],
    route_ends: tuple[_RouteEndFact, ...],
    exposures: tuple[_DirectionalExposureFact, ...],
) -> tuple[_DirectionalExecutionStep, ...]:
    exposed_values = {
        exposure.value
        for exposure in exposures
    }
    ending_values = {
        route_end.value
        for route_end in route_ends
    }
    source_by_destination = {
        route.destination_value: route.source_value
        for route in routes
    }
    remaining_consumers = {
        route.source_value: 1
        for route in routes
    }
    steps: list[_DirectionalExecutionStep] = []
    for encounter in encounters:
        release_values: list[_DirectionalValueCoordinate] = []
        for input_value in encounter.incident_values:
            source_value = source_by_destination.get(input_value)
            if source_value is None:
                continue
            remaining_consumers[source_value] -= 1
            if (
                remaining_consumers[source_value] == 0
                and source_value not in exposed_values
            ):
                release_values.append(source_value)
        for output_value in encounter.outgoing_values:
            if output_value in ending_values:
                release_values.append(output_value)
        steps.append(
            _DirectionalExecutionStep(
                encounter_name=encounter.encounter_name,
                owner_name=encounter.owner_name,
                domain=encounter.domain,
                input_values=encounter.incident_values,
                output_values=encounter.outgoing_values,
                release_values=tuple(release_values),
            )
        )
    return tuple(steps)


def _with_release_facts(
    *,
    steps: tuple[_ExecutionStep, ...],
    exposures: tuple[tuple[str, _ValueIdentity], ...],
) -> tuple[_ExecutionStep, ...]:
    remaining_consumers = {
        value_identity: 0
        for step in steps
        for value_identity in step.output_values
    }
    exposed_values = {
        value_identity
        for _name, value_identity in exposures
    }
    for step in steps:
        for value_identity in step.input_values:
            remaining_consumers[value_identity] += 1
    released_steps: list[_ExecutionStep] = []
    for step in steps:
        release_values: list[_ValueIdentity] = []
        for value_identity in step.input_values:
            remaining_consumers[value_identity] -= 1
            if (
                remaining_consumers[value_identity] == 0
                and value_identity not in exposed_values
                and value_identity not in release_values
            ):
                release_values.append(value_identity)
        for value_identity in step.output_values:
            if (
                remaining_consumers[value_identity] == 0
                and value_identity not in exposed_values
            ):
                release_values.append(value_identity)
        released_steps.append(
            replace(
                step,
                release_values=tuple(release_values),
            )
        )
    return tuple(released_steps)


def _adjacency(
    *,
    component_names: tuple[str, ...],
    connections: list[_Connection],
) -> tuple[
    dict[str, list[_Connection]],
    dict[str, list[_Connection]],
]:
    incoming = {
        component_name: []
        for component_name in component_names
    }
    outgoing = {
        component_name: []
        for component_name in component_names
    }
    for connection in connections:
        incoming[connection.destination_name].append(connection)
        outgoing[connection.source_name].append(connection)
    return incoming, outgoing


def _exposed_path_component_findings(
    *,
    component_names: tuple[str, ...],
    incoming_names: dict[str, tuple[str, ...]],
    exposed_names: tuple[str, ...],
) -> tuple[str, ...]:
    reachable = set(exposed_names)
    frontier = list(reachable)
    while frontier:
        name = frontier.pop()
        for source_name in incoming_names.get(name, ()):
            if source_name not in reachable:
                reachable.add(source_name)
                frontier.append(source_name)
    return tuple(
        f"assembly_component_not_on_exposed_path:{component_name}"
        for component_name in component_names
        if component_name not in reachable
    )


def _assembly_empty_output_findings(
    *,
    executable_names: tuple[str, ...],
    exposed_names: tuple[str, ...],
) -> tuple[str, ...]:
    if not executable_names:
        return ("assembly_empty",)
    if not exposed_names:
        return ("assembly_output_not_exposed",)
    return ()


def _topological_names(
    *,
    component_names: tuple[str, ...],
    incoming: dict[str, list[_Connection]],
    outgoing: dict[str, list[_Connection]],
) -> tuple[list[str], list[str] | None]:
    insertion_index = {
        component_name: index
        for index, component_name in enumerate(component_names)
    }
    degrees = {
        component_name: len(connections)
        for component_name, connections in incoming.items()
    }
    remaining = set(degrees)
    ordered: list[str] = []
    while remaining:
        available = [
            component_name
            for component_name in remaining
            if degrees[component_name] == 0
        ]
        if not available:
            return ordered, list(remaining)
        component_name = min(
            available,
            key=lambda name: insertion_index[name],
        )
        ordered.append(component_name)
        remaining.remove(component_name)
        for connection in outgoing[component_name]:
            degrees[connection.destination_name] -= 1
    return ordered, None


def _ordered_connections(
    *,
    component_name: str,
    connections: list[_Connection],
    contracts: dict[str, _ComponentContract],
) -> tuple[_Connection, ...]:
    ports = contracts[component_name].input_ports
    port_index = {
        port: index
        for index, port in enumerate(ports)
    }
    return tuple(
        sorted(
            connections,
            key=lambda connection: port_index[
                connection.destination_port
            ],
        )
    )


def _value_kind_at_port(
    contract: _ComponentContract,
    port: str | None,
    *,
    direction: str,
) -> _PhysicalValueKind:
    ports = (
        contract.input_ports if direction == "input" else contract.output_ports
    )
    values = (
        contract.input_values
        if direction == "input"
        else contract.output_values
    )
    index = ports.index(port)
    return values[index]


def _connection_value_finding(
    *,
    contracts: dict[str, _ComponentContract],
    connection: _Connection,
) -> str | None:
    source_contract = contracts[connection.source_name]
    destination_contract = contracts[connection.destination_name]
    source_kind = _value_kind_at_port(
        source_contract,
        connection.source_port,
        direction="output",
    )
    destination_kind = _value_kind_at_port(
        destination_contract,
        connection.destination_port,
        direction="input",
    )
    if source_kind is destination_kind:
        return None
    source_domain = _domain_of(source_kind)
    destination_domain = _domain_of(destination_kind)
    if source_domain != destination_domain:
        return (
            "assembly_connection_domain_mismatch:"
            f"{connection.source_name}:"
            f"{connection.source_port}->{connection.destination_name}:"
            f"{connection.destination_port}"
        )
    return (
        "assembly_connection_value_mismatch:"
        f"{connection.source_name}:"
        f"{connection.source_port}->{connection.destination_name}:"
        f"{connection.destination_port}"
    )


def _output_port_reused_finding(
    *,
    connections: list[_Connection],
    candidate: _Connection,
) -> str | None:
    for existing in connections:
        if (
            existing.source_name == candidate.source_name
            and existing.source_port == candidate.source_port
        ):
            return (
                "assembly_output_port_reused:"
                f"{candidate.source_name}:{candidate.source_port}"
            )
    return None


def _input_port_reused_finding(
    *,
    connections: list[_Connection],
    candidate: _Connection,
) -> str | None:
    for existing in connections:
        if (
            existing.destination_name == candidate.destination_name
            and existing.destination_port == candidate.destination_port
        ):
            return (
                "assembly_input_port_count_mismatch:"
                f"{candidate.destination_name}:"
                f"{candidate.destination_port}"
            )
    return None


def _exposure_conflict_finding(
    *,
    exposures: list[_Exposure],
    candidate: _Exposure,
) -> str | None:
    for existing in exposures:
        if (
            existing.component_name == candidate.component_name
            and existing.port == candidate.port
        ):
            return (
                "assembly_expose_output_reused:"
                f"{candidate.component_name}:{candidate.port}"
            )
    for existing in exposures:
        if existing.name == candidate.name:
            return f"assembly_expose_duplicate_name:{candidate.name}"
    return None

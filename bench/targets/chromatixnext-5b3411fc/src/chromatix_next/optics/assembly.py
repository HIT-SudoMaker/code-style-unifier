from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any, NoReturn, cast

import torch

import chromatix_next.errors as _errors

from . import _assembly_facts, _assembly_replay, _route_geometry
from ._assembly_facts import (
    _Connection,
    _DirectionalExposureDeclaration,
    _DirectionalOwnerFact,
    _EncounterDeclaration,
    _Exposure,
    _FrozenAssembly,
    _PlanConnectionDeclaration,
    _RouteEndDeclaration,
)
from ._grid_state import _GridState
from ._role_contract import _component_contract_of, _ComponentContract, _domain_of
from .field import OpticalField
from .grid import SpatialGrid
from .intensity import Intensity
from .ray_bundle import RayBundle

_ENCOUNTER_ISSUER = object()


@dataclass(frozen=True, slots=True, eq=False, init=False)
class WaveEncounter:
    """
    将一次 coherent Wave Encounter 定位回签发它的 Assembly

    引用只携带私有作用域令牌和稳定名称；它不是 Module、图节点或 builder，
    也不持有 owner、Tensor、物理值或执行状态。

    Args:
        _issuer: 仅供 Assembly 使用的私有签发令牌
        _scope: 签发 Assembly 的私有作用域令牌
        _name: Encounter 的稳定作者名称

    Raises:
        AssemblyError: 调用方不是签发该引用的 Assembly

    """

    _scope: object
    _name: str

    def __init__(
        self,
        *,
        _issuer: object,
        _scope: object,
        _name: str,
    ) -> None:
        if _issuer is not _ENCOUNTER_ISSUER:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_encounter_owner_unknown",
                ),
                "WaveEncounter 只能由 Assembly.wave_encounter 签发",
            )
        object.__setattr__(self, "_scope", _scope)
        object.__setattr__(self, "_name", _name)


@dataclass(frozen=True, slots=True, eq=False, init=False)
class RayEncounter:
    """
    将一次有限 Ray Encounter 定位回签发它的 Assembly

    引用只携带私有作用域令牌和稳定名称；它不是 Module、图节点或 builder，
    也不持有 owner、Tensor、物理值或执行状态。Ray 账户没有相干振幅或
    lane 间相干求和；这个特意的不对称不声称各 Ray 互不相干。

    Args:
        _issuer: 仅供 Assembly 使用的私有签发令牌
        _scope: 签发 Assembly 的私有作用域令牌
        _name: Encounter 的稳定作者名称

    Raises:
        AssemblyError: 调用方不是签发该引用的 Assembly

    """

    _scope: object
    _name: str

    def __init__(
        self,
        *,
        _issuer: object,
        _scope: object,
        _name: str,
    ) -> None:
        if _issuer is not _ENCOUNTER_ISSUER:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_encounter_owner_unknown",
                ),
                "RayEncounter 只能由 Assembly.ray_encounter 签发",
            )
        object.__setattr__(self, "_scope", _scope)
        object.__setattr__(self, "_name", _name)


class Assembly(torch.nn.Module):
    """
    保留普通 include、connect、expose 语法并支持定向路由的完整光学结构

    汇编拥有组件树、物理值连接、作者暴露、拓扑与全路径兼容性。
    include_directional 纳入一个状态 owner，wave_encounter 和 ray_encounter 签发
    有限 Encounter，Terminal-aware connect/expose 连接或命名产生值，end_route
    以 Route End 显式处置离开建模系统的 outgoing Terminal。
    Workstation 私下重放冻结事实；汇编不拥有设备、内存估算或公开执行入口。

    """

    def __init__(self) -> None:

        super().__init__()
        self._component_names: tuple[str, ...] = ()
        self._contracts: dict[str, _ComponentContract] = {}
        self._connections: list[_Connection] = []
        self._exposures: list[_Exposure] = []
        self._directional_owner_names: tuple[str, ...] = ()
        self._directional_owner_facts: tuple[_DirectionalOwnerFact, ...] = ()
        self._encounters: tuple[_EncounterDeclaration, ...] = ()
        self._plan_connections: tuple[_PlanConnectionDeclaration, ...] = ()
        self._directional_exposures: tuple[
            _DirectionalExposureDeclaration,
            ...,
        ] = ()
        self._route_ends: tuple[_RouteEndDeclaration, ...] = ()
        self._exposure_order: tuple[str, ...] = ()
        self._encounter_scope = object()
        self._frozen = False
        self._frozen_facts: _FrozenAssembly | None = None

    @property
    def is_frozen(self) -> bool:
        """
        拓扑永久冻结标记

        为真后普通或定向的 authoring 拓扑变更均被拒绝；
        工作站托管也以此标记为前置条件。

        Returns:
            返回 Assembly 是否已经冻结

        """

        return self._frozen

    def exposed_names(self) -> tuple[str, ...]:
        """
        返回作者顺序中的输出名称

        Returns:
            当前已暴露输出名称的元组，顺序与 expose 调用顺序一致

        """

        return self._exposure_order

    def include(
        self,
        component: torch.nn.Module,
        *,
        name: str,
        grid: SpatialGrid | None = None,
    ) -> None:
        """
        在唯一稳定名称下纳入一个光学组件

        源角色组件必须在同一作者操作中给出自己的空间网格采样锚（``grid``）；
        非源角色组件不接受采样锚。汇编不持有也不默认任何 Assembly 级共配准网格，
        每个源的锚仅初始化该源，下游网格由各组件按自有规则解析。

        Args:
            component: 要纳入汇编的光学组件
            name: 作者为组件或暴露结果指定的稳定名称
            grid: 定义采样位置与间距的空间网格

        Raises:
            AssemblyError: 调用时的状态或拓扑不满足该 Interface 契约

        """

        self._reject_if_frozen("include")
        contract = self._validate_component(component)
        self._validate_name(name)
        if name in (
            self._component_names
            + self._directional_owner_names
            + tuple(
                encounter.encounter_name
                for encounter in self._encounters
            )
        ):
            raise _errors.AssemblyError(
                f"assembly_include_duplicate_name:{name}",
                f"汇编中已经有名为 {name} 的组件，请使用另一个名称",
            )
        self._validate_name_available(name)
        prior_name = next(
            (
                included_name
                for included_name in self._component_names
                if self._component(included_name) is component
            ),
            None,
        )
        if prior_name is not None:
            raise _errors.AssemblyError(
                f"assembly_include_component_duplicate:{prior_name}",
                f"这个组件实例已经以 {prior_name} 纳入汇编；"
                "需要两份组件时应分别构造",
            )
        is_source = contract.role == "source"
        anchor_state: _GridState | None
        if is_source:
            if not isinstance(grid, SpatialGrid):
                raise _errors.AssemblyError(
                    f"assembly_include_source_anchor_missing:{name}",
                    f"纳入源角色组件 {name} 时必须在同一作者操作中给出"
                    "它的空间网格采样锚（grid=...）",
                )
            anchor_state = _GridState(grid)
        else:
            if grid is not None:
                raise _errors.AssemblyError(
                    f"assembly_include_non_source_anchor_forbidden:{name}",
                    f"只有源角色组件才能带采样锚；{name} 的角色是 "
                    f"{contract.role}，不能给出 grid",
                )
            anchor_state = None
        updated_names = (*self._component_names, name)
        updated_contracts = {**self._contracts, name: contract}
        self._register_component(name, component)
        if anchor_state is not None:
            torch.nn.Module.add_module(
                self,
                self._anchor_name(name),
                anchor_state,
            )
        self._component_names = updated_names
        self._contracts = updated_contracts

    def include_directional(
        self,
        owner: torch.nn.Module,
        *,
        name: str,
    ) -> None:
        """
        在唯一稳定名称下纳入一个封闭 directional owner

        Args:
            owner: Cube 或 Mirror 的 state-only directional owner
            name: owner 在 Assembly 中的稳定名称

        Raises:
            AssemblyError: owner、名称、状态或作者生命周期无效
            OpticalRuntimeError: owner 的封闭 Terminal 拓扑无法派生

        """

        self._reject_if_frozen("include_directional")
        if self._directional_owner_kind(owner) is None:
            self._directional_owner_fact(owner, name=name)
        self._validate_directional_name(
            name,
            identity="assembly_include_directional_owner_invalid",
            owner=(
                name
                if isinstance(name, str)
                and name.isidentifier()
                and not name.startswith("_")
                else "-"
            ),
        )
        occupied_names = self._authored_topology_names()
        if name in occupied_names:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_include_directional_owner_duplicate",
                    owner=name,
                ),
                f"名称 {name!r} 已被同一 Assembly 的 Component、owner 或 "
                "Encounter 使用；请提供唯一稳定名称",
            )
        self._validate_name_available(name)
        prior_name = next(
            (
                owner_name
                for owner_name in self._directional_owner_names
                if self._component(owner_name) is owner
            ),
            None,
        )
        if prior_name is not None:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_include_directional_owner_duplicate",
                    owner=prior_name,
                ),
                f"这个 directional owner 已经以 {prior_name} 纳入 Assembly；"
                "一个物理 owner 只能注册一次，重复使用请声明多个 Encounter",
            )
        self._validate_directional_owner_state(owner, owner_name=name)
        owner_fact = self._directional_owner_fact(owner, name=name)
        updated_names = (*self._directional_owner_names, name)
        updated_facts = (*self._directional_owner_facts, owner_fact)
        self._register_component(name, owner)
        self._directional_owner_names = updated_names
        self._directional_owner_facts = updated_facts

    def wave_encounter(
        self,
        owner: torch.nn.Module,
        *,
        name: str,
        incident_terminals: tuple[object, ...],
    ) -> WaveEncounter:
        """
        声明一次有限 coherent Wave Encounter

        Args:
            owner: 已由同一 Assembly 纳入的 directional owner
            name: Encounter 的稳定名称
            incident_terminals: 非空且无重复的封闭 incident Terminal 元组

        Returns:
            仅能交回本 Assembly 的私有、冻结、无状态 Encounter 引用

        Raises:
            AssemblyError: 名称、owner 或 incidence 声明无效

        """

        authored_terminals: tuple[object, ...]
        if isinstance(incident_terminals, tuple):
            authored_terminals = incident_terminals
        else:
            authored_terminals = (incident_terminals,)
        encounter_name = self._declare_encounter(
            owner,
            name=name,
            domain="wave",
            incident_terminals=authored_terminals,
        )
        return WaveEncounter(
            _issuer=_ENCOUNTER_ISSUER,
            _scope=self._encounter_scope,
            _name=encounter_name,
        )

    def ray_encounter(
        self,
        owner: torch.nn.Module,
        *,
        name: str,
        incident_terminal: object,
    ) -> RayEncounter:
        """
        声明一次恰有一个 incident Terminal 的有限 Ray Encounter

        Args:
            owner: 已由同一 Assembly 纳入的 directional owner
            name: Encounter 的稳定名称
            incident_terminal: 唯一封闭 incident Terminal

        Returns:
            仅能交回本 Assembly 的私有、冻结、无状态 Encounter 引用

        Raises:
            AssemblyError: 名称、owner 或 incidence 声明无效

        """

        terminals: tuple[object, ...]
        if (
            isinstance(incident_terminal, (tuple, list))
            and len(incident_terminal) != 1
        ):
            terminals = tuple(incident_terminal)
        else:
            terminals = (incident_terminal,)
        encounter_name = self._declare_encounter(
            owner,
            name=name,
            domain="ray",
            incident_terminals=terminals,
        )
        return RayEncounter(
            _issuer=_ENCOUNTER_ISSUER,
            _scope=self._encounter_scope,
            _name=encounter_name,
        )

    def connect(
        self,
        source: object,
        destination: object,
        *,
        source_port: str | None = None,
        destination_port: str | None = None,
        source_terminal: object | None = None,
        destination_terminal: object | None = None,
    ) -> None:
        """
        声明一个组件输出到另一个组件输入的物理值流

        在改变作者态之前完成全部校验：成员关系、端口记号、声明端口、物理值兼容性、
        源输出端口占用与目标输入端口占用。任一校验失败都以稳定身份抛出 AssemblyError
        且不改变既有作者态——被拒连接不会进入既有拓扑，故一次作者失误无需重建光路。

        Args:
            source: 连接起点的已纳入 Component 或本 Assembly Encounter
            destination: 连接终点的已纳入 Component 或本 Assembly Encounter
            source_port: Component 起点的命名输出 Port
            destination_port: Component 终点的命名输入 Port
            source_terminal: Encounter 起点的 produced outgoing Terminal
            destination_terminal: Encounter 终点的 declared incident Terminal

        Raises:
            AssemblyError: 拓扑/端口/冻结状态不满足前置条件

        """

        self._reject_if_frozen("connect")
        source_category, source_name = self._connection_endpoint(
            source,
            direction="source",
        )
        destination_category, destination_name = self._connection_endpoint(
            destination,
            direction="destination",
        )
        source_token = self._validated_connection_source_token(
            category=source_category,
            name=source_name,
            source_port=source_port,
            source_terminal=source_terminal,
        )
        destination_token = self._validated_connection_destination_token(
            category=destination_category,
            name=destination_name,
            destination_port=destination_port,
            destination_terminal=destination_terminal,
        )
        candidate = _PlanConnectionDeclaration(
            source_name=source_name,
            source_port=(
                source_token if source_category == "component" else None
            ),
            source_terminal=(
                source_token if source_category == "encounter" else None
            ),
            destination_name=destination_name,
            destination_port=(
                destination_token
                if destination_category == "component"
                else None
            ),
            destination_terminal=(
                destination_token
                if destination_category == "encounter"
                else None
            ),
        )
        self._require_unoccupied_plan_endpoints(
            candidate,
            source_category=source_category,
            destination_category=destination_category,
        )
        self._require_compatible_plan_connection(
            candidate,
            source_category=source_category,
            destination_category=destination_category,
        )
        updated_plan = (*self._plan_connections, candidate)
        if source_category == destination_category == "component":
            ordinary_candidate = _Connection(
                source_name=source_name,
                source_port=source_token,
                destination_name=destination_name,
                destination_port=destination_token,
            )
            self._connections.append(ordinary_candidate)
        self._plan_connections = updated_plan

    def expose(
        self,
        source: object,
        *,
        name: str,
        source_port: str | None = None,
        source_terminal: object | None = None,
        port: str | None = None,
    ) -> None:
        """
        为一个计算物理值声明非消耗的用户可读名称（成为最终 Named Output）

        Exposure 不执行 Optical Role，也不模型化分束、Detection、传感器、物理抽头或能量
        损失；它不消耗所命名的物理值，只把一个稳定 Component-output 锚点的计算结果命名
        为最终 Named Output。同一输出端口可同时驱动一条下游连接并拥有一个 Authored
        Exposure。一个稳定 Component-output 锚点至多一个 Authored Exposure——为同一物理
        事实二次命名在此以稳定身份拒绝
        （``assembly_expose_output_reused:<component>:<port>``），且该被拒操作不改变既有
        作者暴露态。普通 Component 的不同输出 Port 仍按作者序独立可暴露；
        定向设备侧面是 Encounter 的 produced outgoing Terminal，不是相对分支 Port。
        两个不同锚点争同一用户名仍由 ``assembly_expose_duplicate_name`` 作为独立缺陷
        拒绝。

        Args:
            source: 要命名的已纳入 Component 或本 Assembly Encounter
            name: 作者为组件或暴露结果指定的稳定名称
            source_port: Component 上要暴露的命名输出 Port
            source_terminal: Encounter 上要暴露的 produced outgoing Terminal
            port: T25 原子词汇切换前保留的普通 Component Port 拼写

        Raises:
            AssemblyError: 拓扑/端口/冻结状态不满足前置条件

        """

        self._reject_if_frozen("expose")
        category, source_name = self._exposure_endpoint(source)
        self._validate_name(name)
        if category == "component":
            if source_terminal is not None or (
                source_port is not None and port is not None
            ):
                self._raise_endpoint_category_invalid()
            selected_port = source_port if source_port is not None else port
            self._validate_port_token(
                selected_port,
                "assembly_expose_port_invalid",
            )
            self._require_declared_port(
                source_name,
                selected_port,
                direction="output",
            )
            candidate = _Exposure(
                component_name=source_name,
                port=selected_port,
                name=name,
            )
            self._require_available_exposure(candidate)
            if any(
                exposure.name == name
                for exposure in self._directional_exposures
            ):
                raise _errors.AssemblyError(
                    f"assembly_expose_duplicate_name:{name}",
                    f"已经声明过名为 {name} 的输出，输出名称必须互不相同",
                )
            self._exposures.append(candidate)
        else:
            if source_port is not None or port is not None:
                self._raise_endpoint_category_invalid(
                    owner=self._encounter_owner_name(source_name),
                    encounter=source_name,
                )
            terminal = self._validated_outgoing_terminal(
                encounter_name=source_name,
                terminal=source_terminal,
                structural_identity="assembly_connect_terminal_direction_invalid",
            )
            self._require_directional_output_not_ended(
                encounter_name=source_name,
                terminal=terminal,
            )
            if any(
                exposure.encounter_name == source_name
                and exposure.terminal == terminal
                for exposure in self._directional_exposures
            ):
                raise _errors.AssemblyError(
                    _assembly_facts._directional_finding(
                        "assembly_expose_output_reused",
                        owner=self._encounter_owner_name(source_name),
                        encounter=source_name,
                        outgoing=terminal,
                    ),
                    f"Encounter 输出 {source_name}:{terminal} 已经有一个 Exposure；"
                    "每个 outgoing Terminal 至多一个非消耗命名",
                )
            if name in self._exposure_order:
                raise _errors.AssemblyError(
                    _assembly_facts._directional_finding(
                        "assembly_expose_duplicate_name",
                        owner=self._encounter_owner_name(source_name),
                        encounter=source_name,
                        outgoing=terminal,
                    ),
                    f"已经声明过名为 {name} 的输出，输出名称必须互不相同",
                )
            directional_candidate = _DirectionalExposureDeclaration(
                encounter_name=source_name,
                terminal=terminal,
                name=name,
            )
            self._directional_exposures = (
                *self._directional_exposures,
                directional_candidate,
            )
        self._exposure_order = (*self._exposure_order, name)

    def end_route(
        self,
        source_encounter: object,
        *,
        source_terminal: object,
        reason: str,
    ) -> None:
        """
        将一个 outgoing Terminal 显式终止在建模系统边界

        Args:
            source_encounter: 本 Assembly 签发的 Encounter 引用
            source_terminal: 要终止的 produced outgoing Terminal
            reason: 必须精确为 ``outside_modeled_system``

        Raises:
            AssemblyError: 引用、输出、原因或 disposition 冲突无效

        """

        self._reject_if_frozen("end_route")
        encounter_name = self._encounter_reference_name(
            source_encounter,
            identity="assembly_route_end_output_unknown",
        )
        terminal = self._validated_outgoing_terminal(
            encounter_name=encounter_name,
            terminal=source_terminal,
            structural_identity="assembly_route_end_output_unknown",
        )
        if reason != "outside_modeled_system":
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_route_end_reason_invalid",
                    owner=self._encounter_owner_name(encounter_name),
                    encounter=encounter_name,
                    outgoing=terminal,
                ),
                "Route End reason 只能是精确的 outside_modeled_system；"
                "它表示值离开本次建模边界，不执行计算或测量",
            )
        if self._directional_output_is_disposed(
            encounter_name=encounter_name,
            terminal=terminal,
        ):
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_route_end_output_disposed",
                    owner=self._encounter_owner_name(encounter_name),
                    encounter=encounter_name,
                    outgoing=terminal,
                ),
                f"Encounter 输出 {encounter_name}:{terminal} 已经连接、暴露或终止；"
                "Route End 不能与任何其他 disposition 共存",
            )
        candidate = _RouteEndDeclaration(
            encounter_name=encounter_name,
            terminal=terminal,
            reason=reason,
        )
        self._route_ends = (*self._route_ends, candidate)

    def check(self) -> None:
        """
        验证全部拓扑与物理兼容性

        Raises:
            AssemblyError: 拓扑/端口/冻结状态不满足前置条件

        """

        self._validated_facts()

    def freeze(self) -> None:
        """
        验证汇编并永久冻结拓扑

        Raises:
            AssemblyError: 拓扑/端口/冻结状态不满足前置条件

        """

        self._frozen_facts = self._validated_facts()
        self._frozen = True

    @staticmethod
    def _anchor_name(component_name: str) -> str:
        return f"_anchor_{component_name}"

    def _anchor_grid(self, source_name: str) -> SpatialGrid:
        anchor = self._modules.get(self._anchor_name(source_name))
        if not isinstance(anchor, _GridState):
            raise _errors.AssemblyError(
                f"assembly_source_anchor_missing:{source_name}",
                f"源 {source_name} 没有已注册的采样锚；"
                "include 源角色组件时必须在同一作者操作中给出 grid",
            )
        return anchor.value

    def _assume_frozen_facts(self, facts: _FrozenAssembly) -> None:
        # 采用既定执行事实进入冻结态；供 meta 副本复用真执行的 facts
        self._frozen_facts = facts
        self._frozen = True

    def _validated_facts(self) -> _FrozenAssembly:
        owner_state_findings: list[str] = []
        self._collect_directional_owner_state_findings(
            owner_state_findings,
        )
        if self._frozen and self._frozen_facts is not None:
            facts, structural_findings = self._frozen_facts, []
        elif self._has_directional_authoring():
            route_terminal_frames = (
                self._route_terminal_frames()
                if not owner_state_findings
                else ()
            )
            facts, structural_findings = _assembly_facts._build_mixed_facts(
                component_names=self._component_names,
                contracts=self._contracts,
                ordinary_exposures=tuple(self._exposures),
                owners=self._directional_owner_facts,
                encounters=self._encounters,
                plan_connections=self._plan_connections,
                route_ends=self._route_ends,
                directional_exposures=self._directional_exposures,
                exposure_order=self._exposure_order,
                route_terminal_frames=route_terminal_frames,
                propagation_displacements=(
                    self._propagation_displacements()
                ),
            )
        else:
            facts, structural_findings = _assembly_facts._build_facts(
                component_names=self._component_names,
                contracts=self._contracts,
                connections=self._connections,
                exposures=self._exposures,
            )
        if facts is not None:
            facts = self._without_route_validation_tensors(facts)
        findings = owner_state_findings + structural_findings
        if facts is not None:
            _assembly_replay._collect_physical_state_findings(
                self,
                facts=facts,
                findings=findings,
            )
        if facts is not None and not findings:
            _assembly_replay._collect_meta_inference_findings(
                self,
                facts=facts,
                findings=findings,
            )
        if findings:
            raise _errors.AssemblyError(
                "; ".join(findings),
                "汇编检查按物理顺序列出了全部缺陷；"
                "修正连接、暴露或组件物理状态后才能冻结",
            )
        assert facts is not None
        return facts

    def _execution_facts(self) -> _FrozenAssembly:
        if self._frozen:
            assert self._frozen_facts is not None
            return self._frozen_facts
        if self._has_directional_authoring():
            facts, findings = _assembly_facts._build_mixed_facts(
                component_names=self._component_names,
                contracts=self._contracts,
                ordinary_exposures=tuple(self._exposures),
                owners=self._directional_owner_facts,
                encounters=self._encounters,
                plan_connections=self._plan_connections,
                route_ends=self._route_ends,
                directional_exposures=self._directional_exposures,
                exposure_order=self._exposure_order,
                route_terminal_frames=self._route_terminal_frames(),
                propagation_displacements=(
                    self._propagation_displacements()
                ),
            )
        else:
            facts, findings = _assembly_facts._build_facts(
                component_names=self._component_names,
                contracts=self._contracts,
                connections=self._connections,
                exposures=self._exposures,
            )
        if findings or facts is None:
            raise _errors.AssemblyError(
                "assembly_execution_facts_invalid",
                "汇编拓扑尚未通过检查，不能建立冻结执行事实",
            )
        return self._without_route_validation_tensors(facts)

    def _replay(
        self,
        *,
        generator_for: Callable[[str], torch.Generator] | None = None,
        validate_value: (
            Callable[[OpticalField | Intensity | RayBundle], None] | None
        ) = None,
    ) -> Mapping[str, OpticalField | Intensity | RayBundle]:
        return _assembly_replay._replay(
            self,
            generator_for=generator_for,
            validate_value=validate_value,
        )

    def _authored_topology_names(self) -> set[str]:
        return (
            set(self._component_names)
            | set(self._directional_owner_names)
            | {
                encounter.encounter_name
                for encounter in self._encounters
            }
        )

    def _has_directional_authoring(self) -> bool:
        return bool(
            self._directional_owner_names
            or self._encounters
            or self._directional_exposures
            or self._route_ends
        )

    def _route_terminal_frames(
        self,
    ) -> tuple[_route_geometry._TerminalFrameInput, ...]:
        # Freeze 读取 owner 派生 frame，但冻结事实不保留 owner 或 Tensor
        frames: list[_route_geometry._TerminalFrameInput] = []
        for owner_fact in self._directional_owner_facts:
            owner = self._component(owner_fact.owner_name)
            frames.extend(
                _route_geometry._owner_terminal_frames(
                    owner_name=owner_fact.owner_name,
                    owner=owner,
                    terminal_order=owner_fact.terminal_order,
                )
            )
        return tuple(frames)

    @staticmethod
    def _without_route_validation_tensors(
        facts: _FrozenAssembly,
    ) -> _FrozenAssembly:
        # Terminal Frame Tensor 仅服务 Freeze 校验；冻结计划保留 endpoint 与纯 basis
        if not any(
            route.source_frame is not None
            or route.destination_frame is not None
            for route in facts.route_segments
        ):
            return facts
        return replace(
            facts,
            route_segments=tuple(
                replace(
                    route,
                    source_frame=None,
                    destination_frame=None,
                )
                for route in facts.route_segments
            ),
        )

    def _propagation_displacements(
        self,
    ) -> tuple[tuple[str, float | None], ...]:
        # 每个 Propagation 只贡献一个当前可验证的 route-local 位移
        displacements: list[tuple[str, float | None]] = []
        for component_name in self._component_names:
            if self._contracts[component_name].role != "propagation":
                continue
            component = self._component(component_name)
            displacement = cast(
                float | None,
                _route_geometry._resolved_scalar(
                    getattr(component, "axial_distance", None),
                ),
            )
            if (
                displacement is None
                and hasattr(component, "focal_length")
                and hasattr(component, "axial_distance_from_focus")
            ):
                focal_length = cast(
                    float | None,
                    _route_geometry._resolved_scalar(
                        getattr(component, "focal_length"),
                    ),
                )
                axial_offset = cast(
                    float | None,
                    _route_geometry._resolved_scalar(
                        getattr(component, "axial_distance_from_focus"),
                    ),
                )
                if focal_length is not None and axial_offset is not None:
                    displacement = focal_length + axial_offset
            displacements.append((component_name, displacement))
        return tuple(displacements)

    @staticmethod
    def _directional_owner_kind(owner: object) -> str | None:
        return _route_geometry._directional_owner_kind(owner)

    @staticmethod
    def _directional_owner_fact(
        owner: object,
        *,
        name: str,
    ) -> _DirectionalOwnerFact:
        topology = _route_geometry._directional_owner_topology(owner)
        if topology is not None:
            terminal_order, routes = topology
            return _DirectionalOwnerFact(
                owner_name=name,
                terminal_order=terminal_order,
                routes=routes,
            )
        raise _errors.AssemblyError(
            _assembly_facts._directional_finding(
                "assembly_include_directional_owner_invalid",
                owner=name if isinstance(name, str) else "-",
            ),
            "include_directional 只接受封闭的 IdealNonpolarizingCubeBeamSplitter、"
            "IdealPolarizingCubeBeamSplitter 或 IdealPlanarMirror owner；"
            f"收到的是 {type(owner).__name__}，不会自动注册或推断能力",
        )

    @staticmethod
    def _validate_directional_name(
        name: object,
        *,
        identity: str,
        owner: str = "-",
        encounter: str = "-",
    ) -> None:
        if (
            isinstance(name, str)
            and name.isidentifier()
            and not name.startswith("_")
        ):
            return
        raise _errors.AssemblyError(
            _assembly_facts._directional_finding(
                identity,
                owner=owner,
                encounter=encounter,
            ),
            "directional owner 与 Encounter 名称必须是不以下划线开头的 "
            f"Python 标识符，收到的是 {name!r}",
        )

    def _validate_directional_owner_state(
        self,
        owner: torch.nn.Module,
        *,
        owner_name: str,
    ) -> None:
        validator = getattr(owner, "_validate_physical_state", None)
        try:
            if not callable(validator):
                raise _errors.OpticalRuntimeError(
                    "directional_owner_validator_missing",
                    "directional owner 缺少封闭状态校验",
                )
            validator()
        except Exception as error:
            underlying = (
                error.identity
                if isinstance(error, _errors.OpticalError)
                else type(error).__name__
            )
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_directional_owner_state_invalid",
                    owner=owner_name,
                    underlying=underlying,
                ),
                f"directional owner {owner_name} 的实时物理状态无效；"
                f"底层身份为 {underlying}，请修复 owner 状态后重试",
            ) from error

    def _collect_directional_owner_state_findings(
        self,
        findings: list[str],
    ) -> None:
        for owner_name in self._directional_owner_names:
            try:
                self._validate_directional_owner_state(
                    self._component(owner_name),
                    owner_name=owner_name,
                )
            except _errors.AssemblyError as error:
                findings.append(error.identity)

    def _declare_encounter(
        self,
        owner: torch.nn.Module,
        *,
        name: str,
        domain: str,
        incident_terminals: tuple[object, ...],
    ) -> str:
        self._reject_if_frozen(f"{domain}_encounter")
        owner_name = self._directional_owner_name(owner)
        self._validate_directional_name(
            name,
            identity="assembly_encounter_name_invalid",
            owner="-" if owner_name is None else owner_name,
            encounter=(
                name
                if isinstance(name, str)
                and name.isidentifier()
                and not name.startswith("_")
                else "-"
            ),
        )
        if name in self._authored_topology_names():
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_encounter_duplicate_name",
                    owner="-" if owner_name is None else owner_name,
                    encounter=name,
                ),
                f"名称 {name!r} 已被 Component、owner 或 Encounter 使用；"
                "三类作者名称共享一个 Assembly namespace",
            )
        if owner_name is None:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_encounter_owner_unknown",
                    encounter=name,
                ),
                "Encounter owner 尚未由同一 Assembly include_directional；"
                "不会自动注册 owner",
            )
        if domain not in ("wave", "ray"):
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_encounter_owner_unsupported",
                    owner=owner_name,
                    encounter=name,
                ),
                f"owner {owner_name} 不支持 Encounter domain {domain!r}",
            )
        if not incident_terminals:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_encounter_incident_empty",
                    owner=owner_name,
                    encounter=name,
                ),
                "Wave Encounter 必须声明至少一个 incident Terminal；"
                "Ray Encounter 必须声明恰好一个",
            )
        if domain == "ray" and len(incident_terminals) != 1:
            extra = incident_terminals[1]
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_encounter_ray_multiple_incident",
                    owner=owner_name,
                    encounter=name,
                    incident=self._terminal_locator(extra),
                ),
                "Ray Encounter 只接受一个 incident Terminal；"
                "Ray lane 不执行 coherent 多输入混合",
            )
        duplicate = self._first_duplicate_terminal(incident_terminals)
        if duplicate is not None:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_encounter_incident_duplicate",
                    owner=owner_name,
                    encounter=name,
                    incident=self._terminal_locator(duplicate),
                ),
                "Encounter incidence 中每个 Terminal 只能出现一次",
            )
        terminal_values = tuple(
            self._validated_owner_terminal(
                owner_name=owner_name,
                terminal=terminal,
                identity="assembly_encounter_terminal_unknown",
                encounter=name,
                incident=True,
            )
            for terminal in incident_terminals
        )
        owner_fact = self._owner_fact(owner_name)
        terminal_set = set(terminal_values)
        canonical_terminals = tuple(
            terminal
            for terminal in owner_fact.terminal_order
            if terminal in terminal_set
        )
        self._validate_directional_owner_state(owner, owner_name=owner_name)
        declaration = _EncounterDeclaration(
            encounter_name=name,
            owner_name=owner_name,
            domain=domain,
            incident_terminals=canonical_terminals,
        )
        self._encounters = (*self._encounters, declaration)
        return name

    @staticmethod
    def _first_duplicate_terminal(
        terminals: tuple[object, ...],
    ) -> object | None:
        for index, terminal in enumerate(terminals):
            if terminal in terminals[:index]:
                return terminal
        return None

    def _directional_owner_name(self, owner: object) -> str | None:
        return next(
            (
                name
                for name in self._directional_owner_names
                if self._component(name) is owner
            ),
            None,
        )

    def _owner_fact(self, owner_name: str) -> _DirectionalOwnerFact:
        return next(
            fact
            for fact in self._directional_owner_facts
            if fact.owner_name == owner_name
        )

    def _encounter_declaration(
        self,
        encounter_name: str,
    ) -> _EncounterDeclaration:
        return next(
            encounter
            for encounter in self._encounters
            if encounter.encounter_name == encounter_name
        )

    def _encounter_owner_name(self, encounter_name: str) -> str:
        return self._encounter_declaration(encounter_name).owner_name

    def _encounter_reference_name(
        self,
        value: object,
        *,
        identity: str,
    ) -> str:
        if (
            isinstance(value, (WaveEncounter, RayEncounter))
            and value._scope is self._encounter_scope
            and any(
                encounter.encounter_name == value._name
                for encounter in self._encounters
            )
        ):
            return value._name
        raise _errors.AssemblyError(
            _assembly_facts._directional_finding(identity),
            "Encounter 引用必须由当前 Assembly 签发；"
            "不接受字符串路径、foreign/stale 引用或 public graph node",
        )

    @staticmethod
    def _terminal_locator(terminal: object) -> str:
        value = getattr(terminal, "value", None)
        if isinstance(value, str):
            return value
        return "-"

    def _validated_owner_terminal(
        self,
        *,
        owner_name: str,
        terminal: object,
        identity: str,
        encounter: str,
        incident: bool = False,
        outgoing: bool = False,
    ) -> str:
        owner = self._component(owner_name)
        valid_type = _route_geometry._owner_terminal_type(owner)
        if valid_type is None:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_encounter_owner_unsupported",
                    owner=owner_name,
                    encounter=encounter,
                ),
                f"Encounter {encounter} 引用的 owner {owner_name} 不属于封闭的 "
                "Cube/Mirror owner 集合；请修复作者状态后重试",
            )
        if type(terminal) is valid_type:
            return terminal.value
        raise _errors.AssemblyError(
            _assembly_facts._directional_finding(
                identity,
                owner=owner_name,
                encounter=encounter,
                incident=self._terminal_locator(terminal) if incident else "-",
                outgoing=self._terminal_locator(terminal) if outgoing else "-",
            ),
            f"owner {owner_name} 只接受 {valid_type.__name__} 的封闭值；"
            f"收到的是 {type(terminal).__name__}，不接受 generic Terminal string",
        )

    def _connection_endpoint(
        self,
        value: object,
        *,
        direction: str,
    ) -> tuple[str, str]:
        if isinstance(value, (WaveEncounter, RayEncounter)):
            return (
                "encounter",
                self._encounter_reference_name(
                    value,
                    identity="assembly_connect_endpoint_category_invalid",
                ),
            )
        if isinstance(value, torch.nn.Module):
            name = next(
                (
                    component_name
                    for component_name in self._component_names
                    if self._component(component_name) is value
                ),
                None,
            )
            if name is not None:
                return "component", name
            if value in tuple(
                self._component(name)
                for name in self._directional_owner_names
            ):
                self._raise_endpoint_category_invalid()
            error_identity = (
                "assembly_connect_source_unknown"
                if direction == "source"
                else "assembly_connect_destination_unknown"
            )
            raise _errors.AssemblyError(
                error_identity,
                "组件尚未纳入汇编；请先 include，再 connect",
            )
        self._raise_endpoint_category_invalid()

    def _exposure_endpoint(self, value: object) -> tuple[str, str]:
        if isinstance(value, (WaveEncounter, RayEncounter)):
            return (
                "encounter",
                self._encounter_reference_name(
                    value,
                    identity="assembly_connect_endpoint_category_invalid",
                ),
            )
        if isinstance(value, torch.nn.Module):
            name = next(
                (
                    component_name
                    for component_name in self._component_names
                    if self._component(component_name) is value
                ),
                None,
            )
            if name is not None:
                return "component", name
            if value in tuple(
                self._component(name)
                for name in self._directional_owner_names
            ):
                self._raise_endpoint_category_invalid()
            raise _errors.AssemblyError(
                "assembly_expose_component_unknown",
                "组件尚未纳入汇编；请先 include，再 expose",
            )
        self._raise_endpoint_category_invalid()

    @staticmethod
    def _raise_endpoint_category_invalid(
        *,
        owner: str = "-",
        encounter: str = "-",
    ) -> NoReturn:
        raise _errors.AssemblyError(
            _assembly_facts._directional_finding(
                "assembly_connect_endpoint_category_invalid",
                owner=owner,
                encounter=encounter,
            ),
            "Component endpoint 只接受 Port，Encounter endpoint 只接受 Terminal；"
            "两类端点不能替代，也不接受字符串路径或 directional owner 本身",
        )

    def _validated_connection_source_token(
        self,
        *,
        category: str,
        name: str,
        source_port: str | None,
        source_terminal: object,
    ) -> str | None:
        if category == "component":
            if source_terminal is not None:
                self._raise_endpoint_category_invalid()
            self._validate_port_token(
                source_port,
                "assembly_connect_source_port_invalid",
            )
            self._require_declared_port(
                name,
                source_port,
                direction="output",
            )
            return source_port
        if source_port is not None or source_terminal is None:
            self._raise_endpoint_category_invalid(
                owner=self._encounter_owner_name(name),
                encounter=name,
            )
        return self._validated_outgoing_terminal(
            encounter_name=name,
            terminal=source_terminal,
            structural_identity="assembly_connect_structural_zero",
        )

    def _validated_connection_destination_token(
        self,
        *,
        category: str,
        name: str,
        destination_port: str | None,
        destination_terminal: object,
    ) -> str | None:
        if category == "component":
            if destination_terminal is not None:
                self._raise_endpoint_category_invalid()
            self._validate_port_token(
                destination_port,
                "assembly_connect_destination_port_invalid",
            )
            self._require_declared_port(
                name,
                destination_port,
                direction="input",
            )
            return destination_port
        if destination_port is not None or destination_terminal is None:
            self._raise_endpoint_category_invalid(
                owner=self._encounter_owner_name(name),
                encounter=name,
            )
        declaration = self._encounter_declaration(name)
        terminal = self._validated_owner_terminal(
            owner_name=declaration.owner_name,
            terminal=destination_terminal,
            identity="assembly_connect_terminal_direction_invalid",
            encounter=name,
            incident=True,
        )
        if terminal not in declaration.incident_terminals:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_connect_terminal_direction_invalid",
                    owner=declaration.owner_name,
                    encounter=name,
                    incident=terminal,
                ),
                f"Terminal {terminal} 不是 Encounter {name} 声明的 incident 输入；"
                "Terminal omission 或方向推断均不允许",
            )
        return terminal

    def _validated_outgoing_terminal(
        self,
        *,
        encounter_name: str,
        terminal: object,
        structural_identity: str,
    ) -> str:
        declaration = self._encounter_declaration(encounter_name)
        terminal_value = self._validated_owner_terminal(
            owner_name=declaration.owner_name,
            terminal=terminal,
            identity=structural_identity,
            encounter=encounter_name,
            outgoing=True,
        )
        owner_fact = self._owner_fact(declaration.owner_name)
        is_produced = any(
            incident in declaration.incident_terminals
            and outgoing == terminal_value
            for incident, outgoing in owner_fact.routes
        )
        if not is_produced:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    structural_identity,
                    owner=declaration.owner_name,
                    encounter=encounter_name,
                    outgoing=terminal_value,
                ),
                f"Encounter {encounter_name} 的 incidence mask 不会在 "
                f"{terminal_value} 产生输出；结构零不能连接、暴露或终止",
            )
        return terminal_value

    def _require_unoccupied_plan_endpoints(
        self,
        candidate: _PlanConnectionDeclaration,
        *,
        source_category: str,
        destination_category: str,
    ) -> None:
        source_token = (
            candidate.source_port
            if source_category == "component"
            else candidate.source_terminal
        )
        destination_token = (
            candidate.destination_port
            if destination_category == "component"
            else candidate.destination_terminal
        )
        if any(
            existing.source_name == candidate.source_name
            and (
                existing.source_port
                if source_category == "component"
                else existing.source_terminal
            )
            == source_token
            for existing in self._plan_connections
        ):
            if source_category == "encounter":
                identity = _assembly_facts._directional_finding(
                    "assembly_output_port_reused",
                    owner=self._encounter_owner_name(candidate.source_name),
                    encounter=candidate.source_name,
                    outgoing=cast(str, candidate.source_terminal),
                )
            else:
                identity = (
                    f"assembly_output_port_reused:"
                    f"{candidate.source_name}:{source_token}"
                )
            raise _errors.AssemblyError(
                identity,
                f"输出 {candidate.source_name}:{source_token} 已经驱动一条下游连接；"
                "每个 produced value 至多一个下游消费者",
            )
        if source_category == "encounter":
            self._require_directional_output_not_ended(
                encounter_name=candidate.source_name,
                terminal=cast(str, candidate.source_terminal),
            )
        if any(
            existing.destination_name == candidate.destination_name
            and (
                existing.destination_port
                if destination_category == "component"
                else existing.destination_terminal
            )
            == destination_token
            for existing in self._plan_connections
        ):
            if destination_category == "encounter":
                identity = _assembly_facts._directional_finding(
                    "assembly_input_port_count_mismatch",
                    owner=self._encounter_owner_name(
                        candidate.destination_name
                    ),
                    encounter=candidate.destination_name,
                    incident=cast(str, candidate.destination_terminal),
                )
            else:
                identity = (
                    "assembly_input_port_count_mismatch:"
                    f"{candidate.destination_name}:{destination_token}"
                )
            raise _errors.AssemblyError(
                identity,
                f"输入 {candidate.destination_name}:{destination_token} 已有生产者；"
                "每个 incident value 恰有一个生产者",
            )

    def _require_compatible_plan_connection(
        self,
        candidate: _PlanConnectionDeclaration,
        *,
        source_category: str,
        destination_category: str,
    ) -> None:
        if source_category == "component":
            source_kind = _assembly_facts._value_kind_at_port(
                self._contracts[candidate.source_name],
                candidate.source_port,
                direction="output",
            )
        else:
            source_kind = self._encounter_value_kind(candidate.source_name)
        if destination_category == "component":
            destination_kind = _assembly_facts._value_kind_at_port(
                self._contracts[candidate.destination_name],
                candidate.destination_port,
                direction="input",
            )
        else:
            destination_kind = self._encounter_value_kind(
                candidate.destination_name
            )
        if source_kind is destination_kind:
            return
        source_token = candidate.source_port or candidate.source_terminal
        destination_token = (
            candidate.destination_port or candidate.destination_terminal
        )
        if _domain_of(source_kind) != _domain_of(destination_kind):
            identity = "assembly_connection_domain_mismatch"
        else:
            identity = "assembly_connection_value_mismatch"
        if source_category == "encounter":
            identity = _assembly_facts._directional_finding(
                identity,
                owner=self._encounter_owner_name(candidate.source_name),
                encounter=candidate.source_name,
                outgoing=cast(str, candidate.source_terminal),
            )
        elif destination_category == "encounter":
            identity = _assembly_facts._directional_finding(
                identity,
                owner=self._encounter_owner_name(
                    candidate.destination_name
                ),
                encounter=candidate.destination_name,
                incident=cast(str, candidate.destination_terminal),
            )
        else:
            identity = (
                f"{identity}:{candidate.source_name}:{source_token}->"
                f"{candidate.destination_name}:{destination_token}"
            )
        raise _errors.AssemblyError(
            identity,
            f"连接源产出 {source_kind.__name__}，目标只接受 "
            f"{destination_kind.__name__}；不会隐式转换 Wave、Ray 或 Intensity",
        )

    def _encounter_value_kind(
        self,
        encounter_name: str,
    ) -> type[OpticalField] | type[RayBundle]:
        domain = self._encounter_declaration(encounter_name).domain
        return OpticalField if domain == "wave" else RayBundle

    def _require_directional_output_not_ended(
        self,
        *,
        encounter_name: str,
        terminal: str,
    ) -> None:
        if not any(
            route_end.encounter_name == encounter_name
            and route_end.terminal == terminal
            for route_end in self._route_ends
        ):
            return
        raise _errors.AssemblyError(
            _assembly_facts._directional_finding(
                "assembly_route_end_output_disposed",
                owner=self._encounter_owner_name(encounter_name),
                encounter=encounter_name,
                outgoing=terminal,
            ),
            f"Encounter 输出 {encounter_name}:{terminal} 已经由 Route End 终止；"
            "Route End 不能与连接或 Exposure 共存",
        )

    def _directional_output_is_disposed(
        self,
        *,
        encounter_name: str,
        terminal: str,
    ) -> bool:
        return (
            any(
                connection.source_name == encounter_name
                and connection.source_terminal == terminal
                for connection in self._plan_connections
            )
            or any(
                exposure.encounter_name == encounter_name
                and exposure.terminal == terminal
                for exposure in self._directional_exposures
            )
            or any(
                route_end.encounter_name == encounter_name
                and route_end.terminal == terminal
                for route_end in self._route_ends
            )
        )

    def _included_name(
        self,
        component: torch.nn.Module,
        error_identity: str,
    ) -> str:
        component_name = next(
            (
                name
                for name in self._component_names
                if self._component(name) is component
            ),
            None,
        )
        if component_name is None:
            raise _errors.AssemblyError(
                error_identity,
                "组件尚未纳入汇编；请先 include，再 connect 或 expose",
            )
        return component_name

    def _component(self, name: str) -> torch.nn.Module:
        component = self._modules.get(name)
        if not isinstance(component, torch.nn.Module):
            raise _errors.AssemblyError(
                f"assembly_component_missing:{name}",
                f"汇编注册树中缺少已纳入组件 {name}",
            )
        return component

    def _register_component(
        self,
        name: str,
        component: torch.nn.Module,
    ) -> None:
        torch.nn.Module.add_module(self, name, component)

    def _require_declared_port(
        self,
        component_name: str,
        port: str | None,
        *,
        direction: str,
    ) -> None:
        contract = self._contracts[component_name]
        ports = (
            contract.input_ports
            if direction == "input"
            else contract.output_ports
        )
        if port not in ports:
            raise _errors.AssemblyError(
                f"assembly_{direction}_port_unknown:"
                f"{component_name}:{port}",
                f"组件 {component_name} 没有 {port!r} {direction} 端口；"
                f"合法端口为 {ports!r}",
            )

    def _require_compatible_connection_value(
        self,
        connection: _Connection,
    ) -> None:
        finding = _assembly_facts._connection_value_finding(
            contracts=self._contracts,
            connection=connection,
        )
        if finding is None:
            return
        source_kind = _assembly_facts._value_kind_at_port(
            self._contracts[connection.source_name],
            connection.source_port,
            direction="output",
        )
        destination_kind = _assembly_facts._value_kind_at_port(
            self._contracts[connection.destination_name],
            connection.destination_port,
            direction="input",
        )
        if finding.startswith("assembly_connection_domain_mismatch"):
            source_domain = _domain_of(source_kind)
            destination_domain = _domain_of(destination_kind)
            raise _errors.AssemblyError(
                finding,
                f"不能把 {source_domain} 物理值（{source_kind.__name__}）"
                f"连到 {destination_domain} 物理值端口"
                f"（{destination_kind.__name__}）；"
                "Wave 与 Ray 是闭合物理域，需要显式物理转换器才能互通",
            )
        raise _errors.AssemblyError(
            finding,
            f"端口物理值种类不匹配：源产出 {source_kind.__name__}，"
            f"目标只接受 {destination_kind.__name__}",
        )

    def _require_unoccupied_ports(
        self,
        connection: _Connection,
    ) -> None:
        output_finding = _assembly_facts._output_port_reused_finding(
            connections=self._connections,
            candidate=connection,
        )
        if output_finding is not None:
            raise _errors.AssemblyError(
                output_finding,
                f"输出端口 {connection.source_name}:"
                f"{connection.source_port} 已经驱动一条下游连接；"
                "一个输出端口至多一条下游连接，"
                "分支须经声明的多输出动作（如分束器）的命名端口提供",
            )
        input_finding = _assembly_facts._input_port_reused_finding(
            connections=self._connections,
            candidate=connection,
        )
        if input_finding is not None:
            raise _errors.AssemblyError(
                input_finding,
                f"目标输入端口 {connection.destination_name}:"
                f"{connection.destination_port} 已经有一个生产者；"
                "每个输入端口恰一个生产者，"
                "多路汇聚须经声明多输入的角色"
                "（如 Combination 或互易散射）的命名端口提供",
            )

    def _require_available_exposure(
        self,
        exposure: _Exposure,
    ) -> None:
        finding = _assembly_facts._exposure_conflict_finding(
            exposures=self._exposures,
            candidate=exposure,
        )
        if finding is None:
            return
        if finding.startswith("assembly_expose_output_reused"):
            raise _errors.AssemblyError(
                finding,
                f"输出端口 {exposure.component_name}:{exposure.port} "
                "已经声明一个 Authored Exposure；"
                "一个稳定的 Component-output 锚点至多一个非消耗命名，"
                "需要为另一物理事实命名时请使用不同的输出端口",
            )
        raise _errors.AssemblyError(
            finding,
            f"已经声明过名为 {exposure.name} 的输出，输出名称必须互不相同",
        )

    @staticmethod
    def _validate_component(component: object) -> _ComponentContract:
        if not isinstance(component, torch.nn.Module):
            raise _errors.AssemblyError(
                "assembly_include_component_invalid",
                "汇编只接受普通 PyTorch Module 形式的光学组件，"
                f"收到的是 {type(component).__name__}",
            )
        contract, finding = _component_contract_of(component)
        if finding is not None:
            raise _errors.AssemblyError(
                finding,
                "组件必须声明且只声明一个合法光学角色",
            )
        assert contract is not None
        return contract

    @staticmethod
    def _validate_name(name: object) -> None:
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or name.startswith("_")
        ):
            raise _errors.AssemblyError(
                f"assembly_name_invalid:{name}",
                "名称必须是不以下划线开头的 Python 标识符，"
                f"收到的是 {name!r}",
            )

    def _validate_name_available(self, name: str) -> None:
        if (
            hasattr(self, name)
            or name in self._modules
            or name in self._parameters
            or name in self._buffers
        ):
            raise _errors.AssemblyError(
                f"assembly_include_name_reserved:{name}",
                f"名称 {name} 已被 Assembly 或 PyTorch 注册树保留；"
                "请为组件选择一个未占用的自然语言名称",
            )

    @staticmethod
    def _validate_port_token(
        port: object,
        error_identity: str,
    ) -> None:
        if port is None:
            return
        if (
            not isinstance(port, str)
            or not port.isidentifier()
            or port.startswith("_")
        ):
            raise _errors.AssemblyError(
                f"{error_identity}:{port}",
                "端口必须是 None 或不以下划线开头的 Python 标识符，"
                f"收到的是 {port!r}",
            )

    def _reject_if_frozen(self, action: str) -> None:
        if self._frozen:
            raise _errors.AssemblyError(
                f"assembly_frozen:{action}",
                f"汇编已经冻结，不能再执行 {action}；"
                "需要改变拓扑时请构造新的 Assembly",
            )

    def __setattr__(self, name: str, value: object) -> None:

        component_names = self.__dict__.get("_component_names", ())
        directional_owner_names = self.__dict__.get(
            "_directional_owner_names",
            (),
        )
        registered_names = component_names + directional_owner_names
        if name in registered_names:
            current = self._modules.get(name)
            if value is not current:
                raise _errors.AssemblyError(
                    f"assembly_component_replacement_forbidden:{name}",
                    f"组件 {name} 已经通过 include 纳入汇编；"
                    "不能绕过 include、connect、expose 作者语法替换",
                )
        elif isinstance(value, torch.nn.Module):
            raise _errors.AssemblyError(
                f"assembly_component_registration_forbidden:{name}",
                f"模块 {name} 不能通过属性赋值纳入汇编，请使用 include",
            )
        super().__setattr__(name, cast(Any, value))

    def __delattr__(self, name: str) -> None:

        component_names = self.__dict__.get("_component_names", ())
        directional_owner_names = self.__dict__.get(
            "_directional_owner_names",
            (),
        )
        if name in component_names + directional_owner_names:
            raise _errors.AssemblyError(
                f"assembly_component_replacement_forbidden:{name}",
                f"组件 {name} 已经通过 include 纳入汇编；"
                "不能绕过 include、connect、expose 作者语法删除",
            )
        contracts = self.__dict__.get("_contracts", {})
        anchor_names = {
            self._anchor_name(component_name)
            for component_name in component_names
            if contracts.get(component_name) is not None
            and contracts[component_name].role == "source"
        }
        if name in anchor_names:
            raise _errors.AssemblyError(
                f"assembly_source_anchor_replacement_forbidden:{name}",
                "源采样锚随源组件一起纳入汇编；"
                "不能绕过 include 作者语法删除",
            )
        super().__delattr__(name)

    def add_module(
        self,
        name: str,
        module: torch.nn.Module | None,
    ) -> None:
        """
        拒绝直接注册组件

        Args:
            name: 作者为组件或暴露结果指定的稳定名称
            module: 被拒绝直接注册、应改由 include 纳入的 PyTorch 模块

        Raises:
            AssemblyError: 调用时的状态或拓扑不满足该 Interface 契约

        """

        registered_names = self.__dict__.get(
            "_component_names",
            (),
        ) + self.__dict__.get("_directional_owner_names", ())
        if name in registered_names:
            raise _errors.AssemblyError(
                f"assembly_component_replacement_forbidden:{name}",
                f"组件 {name} 已经通过 include 纳入汇编，不能由 add_module 替换",
            )
        raise _errors.AssemblyError(
            f"assembly_component_registration_forbidden:{name}",
            f"模块 {name} 不能通过 add_module 纳入汇编，请使用 include",
        )


__all__ = ["Assembly", "RayEncounter", "WaveEncounter"]

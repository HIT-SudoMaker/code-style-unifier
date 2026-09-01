from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import pickle

import pytest
import torch

from chromatix_next.optics._assembly_facts import (
    _build_directional_facts,
    _build_mixed_facts,
    _Connection,
    _DirectionalExposureDeclaration,
    _DirectionalOwnerFact,
    _EncounterDeclaration,
    _ExecutionStep,
    _Exposure,
    _FrozenAssembly,
    _PlanConnectionDeclaration,
    _RouteDeclaration,
    _RouteEndDeclaration,
    _ValueIdentity,
)
from chromatix_next.optics._role_contract import _ComponentContract
from chromatix_next.optics.field import OpticalField
from chromatix_next.optics.intensity import Intensity

_TERMINALS = ("left", "top", "right", "bottom")

_RISING_ROUTES = (
    ("left", "right"),
    ("left", "top"),
    ("top", "bottom"),
    ("top", "left"),
    ("right", "left"),
    ("right", "bottom"),
    ("bottom", "top"),
    ("bottom", "right"),
)


def _cube_owner(name: str = "cube") -> _DirectionalOwnerFact:
    return _DirectionalOwnerFact(
        owner_name=name,
        terminal_order=_TERMINALS,
        routes=_RISING_ROUTES,
    )


def _repeated_owner_facts() -> _FrozenAssembly:
    source_value = _ValueIdentity(
        step_index=0,
        output_ordinal=0,
    )
    ordinary_value = _ValueIdentity(
        step_index=1,
        output_ordinal=0,
    )
    ordinary_facts = _FrozenAssembly(
        steps=(
            _ExecutionStep(
                component_name="source",
                is_source=True,
                is_generator_accepted=False,
                input_values=(),
                output_ports=(None,),
                output_values=(source_value,),
                output_value_kinds=(OpticalField,),
                release_values=(),
            ),
            _ExecutionStep(
                component_name="propagation",
                is_source=False,
                is_generator_accepted=False,
                input_values=(source_value,),
                output_ports=(None,),
                output_values=(ordinary_value,),
                output_value_kinds=(OpticalField,),
                release_values=(source_value,),
            ),
        ),
        exposures=(("ordinary_field", ordinary_value),),
        connections=(
            _Connection(
                source_name="source",
                source_port=None,
                destination_name="propagation",
                destination_port=None,
            ),
        ),
        exposure_order=("ordinary_field",),
    )
    facts, findings = _build_directional_facts(
        ordinary_facts=ordinary_facts,
        ordinary_names=("source", "propagation"),
        owners=(_cube_owner(),),
        encounters=(
            _EncounterDeclaration(
                encounter_name="outward_cube",
                owner_name="cube",
                domain="wave",
                incident_terminals=("left",),
            ),
            _EncounterDeclaration(
                encounter_name="return_cube",
                owner_name="cube",
                domain="wave",
                incident_terminals=("right", "top"),
            ),
        ),
        routes=(
            _RouteDeclaration(
                source_encounter_name="outward_cube",
                source_terminal="right",
                destination_encounter_name="return_cube",
                destination_terminal="right",
            ),
            _RouteDeclaration(
                source_encounter_name="outward_cube",
                source_terminal="top",
                destination_encounter_name="return_cube",
                destination_terminal="top",
            ),
        ),
        route_ends=(
            _RouteEndDeclaration(
                encounter_name="return_cube",
                terminal="bottom",
            ),
        ),
        exposures=(
            _DirectionalExposureDeclaration(
                encounter_name="return_cube",
                terminal="left",
                name="bright_field",
            ),
        ),
        exposure_order=("ordinary_field", "bright_field"),
    )
    assert findings == []
    assert facts is not None
    return facts


def _finding(
    base: str,
    *,
    owner: str = "-",
    encounter: str = "-",
    incident: str = "-",
    outgoing: str = "-",
    route: str = "-",
) -> str:
    return (
        f"{base}:owner={owner}:encounter={encounter}:incident={incident}:"
        f"outgoing={outgoing}:route={route}:underlying=-"
    )


def _contains_forbidden_runtime_value(value: object) -> bool:
    if isinstance(value, (torch.nn.Module, torch.Tensor)) or callable(value):
        return True
    if is_dataclass(value) and not isinstance(value, type):
        return any(
            _contains_forbidden_runtime_value(getattr(value, field.name))
            for field in fields(value)
        )
    if isinstance(value, (tuple, list)):
        return any(_contains_forbidden_runtime_value(item) for item in value)
    if isinstance(value, dict):
        return any(
            _contains_forbidden_runtime_value(key)
            or _contains_forbidden_runtime_value(item)
            for key, item in value.items()
        )
    return False


class TestStableDirectionalCoordinates:
    def test_one_owner_two_encounters_have_distinct_complete_coordinates(
        self,
    ) -> None:
        facts = _repeated_owner_facts()

        assert len(facts.directional_owners) == 1
        assert tuple(
            encounter.owner_name
            for encounter in facts.encounters
        ) == ("cube", "cube")
        outward, returning = facts.encounters
        outward_right = next(
            value
            for value in outward.outgoing_values
            if value.terminal == "right"
        )
        return_right = next(
            value
            for value in returning.incident_values
            if value.terminal == "right"
        )

        assert outward_right != return_right
        assert (
            outward_right.encounter_name,
            outward_right.owner_name,
            outward_right.terminal,
            outward_right.direction,
        ) == ("outward_cube", "cube", "right", "outgoing")
        assert (
            return_right.encounter_name,
            return_right.owner_name,
            return_right.terminal,
            return_right.direction,
        ) == ("return_cube", "cube", "right", "incident")

    def test_repeated_owner_is_a_finite_acyclic_plan_not_a_cycle_record(
        self,
    ) -> None:
        facts = _repeated_owner_facts()

        assert tuple(
            step.encounter_name
            for step in facts.directional_steps
        ) == ("outward_cube", "return_cube")
        assert len(facts.directional_owners) == 1
        assert len(facts.encounters) == 2
        assert not any(
            forbidden in field.name
            for field in fields(facts)
            for forbidden in ("cycle", "recurrence", "pass_policy")
        )


class TestOneFrozenProjectionOwner:
    def test_one_fact_holds_ordinary_and_directional_plan_projections(
        self,
    ) -> None:
        facts = _repeated_owner_facts()

        assert facts.connections == (
            _Connection("source", None, "propagation", None),
        )
        assert tuple(
            route.route_name
            for route in facts.route_segments
        ) == (
            "outward_cube.right.outgoing__to__return_cube.right.incident",
            "outward_cube.top.outgoing__to__return_cube.top.incident",
        )
        assert facts.exposure_order == ("ordinary_field", "bright_field")
        assert tuple(
            exposure.name
            for exposure in facts.directional_exposures
        ) == ("bright_field",)
        assert len(facts.ancestry) == 10
        assert len(facts.dispositions) == 4
        assert tuple(
            value.terminal
            for value in facts.directional_steps[-1].release_values
        ) == ("top", "right", "bottom")

    def test_ancestry_uses_occurrence_coordinates_from_the_same_plan(
        self,
    ) -> None:
        facts = _repeated_owner_facts()
        return_left = next(
            value
            for value in facts.encounters[-1].outgoing_values
            if value.terminal == "left"
        )
        ancestry = next(
            fact.ancestors
            for fact in facts.ancestry
            if fact.value == return_left
        )

        assert (
            "outward_cube",
            "cube",
            "right",
            "outgoing",
        ) in {
            (
                value.encounter_name,
                value.owner_name,
                value.terminal,
                value.direction,
            )
            for value in ancestry
        }
        assert (
            "return_cube",
            "cube",
            "right",
            "incident",
        ) in {
            (
                value.encounter_name,
                value.owner_name,
                value.terminal,
                value.direction,
            )
            for value in ancestry
        }

    def test_cross_category_flows_have_one_interleaved_replay_order(
        self,
    ) -> None:
        contracts = {
            "source": _ComponentContract(
                role="source",
                input_ports=(),
                output_ports=(None,),
                input_values=(),
                output_values=(OpticalField,),
                is_generator_accepted=False,
            ),
            "relay": _ComponentContract(
                role="propagation",
                input_ports=(None,),
                output_ports=(None,),
                input_values=(OpticalField,),
                output_values=(OpticalField,),
                is_generator_accepted=False,
            ),
            "detector": _ComponentContract(
                role="detection",
                input_ports=(None,),
                output_ports=(None,),
                input_values=(OpticalField,),
                output_values=(Intensity,),
                is_generator_accepted=False,
            ),
        }
        facts, findings = _build_mixed_facts(
            component_names=("source", "relay", "detector"),
            contracts=contracts,
            ordinary_exposures=(
                _Exposure("detector", None, "detected"),
            ),
            owners=(_cube_owner(),),
            encounters=(
                _EncounterDeclaration(
                    "outward_cube",
                    "cube",
                    "wave",
                    ("left",),
                ),
                _EncounterDeclaration(
                    "return_cube",
                    "cube",
                    "wave",
                    ("right",),
                ),
            ),
            plan_connections=(
                _PlanConnectionDeclaration(
                    "source",
                    "outward_cube",
                    source_port=None,
                    destination_terminal="left",
                ),
                _PlanConnectionDeclaration(
                    "outward_cube",
                    "relay",
                    source_terminal="right",
                    destination_port=None,
                ),
                _PlanConnectionDeclaration(
                    "relay",
                    "return_cube",
                    source_port=None,
                    destination_terminal="right",
                ),
                _PlanConnectionDeclaration(
                    "return_cube",
                    "detector",
                    source_terminal="left",
                    destination_port=None,
                ),
            ),
            routes=(
                _RouteDeclaration(
                    "outward_cube",
                    "right",
                    "return_cube",
                    "right",
                    inline_component_names=("relay",),
                ),
            ),
            route_ends=(
                _RouteEndDeclaration("outward_cube", "top"),
                _RouteEndDeclaration("return_cube", "bottom"),
            ),
            exposure_order=("detected",),
        )

        assert findings == []
        assert facts is not None
        assert tuple(
            (step.category, step.name)
            for step in facts.replay_order
        ) == (
            ("component", "source"),
            ("encounter", "outward_cube"),
            ("component", "relay"),
            ("encounter", "return_cube"),
            ("component", "detector"),
        )
        assert tuple(
            (
                type(flow.source_value).__name__,
                type(flow.destination_value).__name__,
            )
            for flow in facts.value_flows
        ) == (
            ("_ComponentValueCoordinate", "_DirectionalValueCoordinate"),
            ("_DirectionalValueCoordinate", "_ComponentValueCoordinate"),
            ("_ComponentValueCoordinate", "_DirectionalValueCoordinate"),
            ("_DirectionalValueCoordinate", "_ComponentValueCoordinate"),
        )
        release_by_value = {
            release.value: release.after_step
            for release in facts.releases
        }
        return_left = next(
            value
            for value in facts.encounters[-1].outgoing_values
            if value.terminal == "left"
        )
        assert release_by_value[return_left].name == "detector"


class TestStateFreeImmutableFacts:
    def test_encounter_route_end_and_plan_facts_hold_no_runtime_state(
        self,
    ) -> None:
        facts = _repeated_owner_facts()

        assert not _contains_forbidden_runtime_value(facts.directional_owners)
        assert not _contains_forbidden_runtime_value(facts.encounters)
        assert not _contains_forbidden_runtime_value(facts.route_segments)
        assert not _contains_forbidden_runtime_value(facts.route_ends)
        forbidden_route_fields = {
            "module",
            "tensor",
            "parameter",
            "buffer",
            "callable",
            "medium",
            "distance",
            "phase",
            "checkpoint",
        }
        assert forbidden_route_fields.isdisjoint(
            field.name
            for field in fields(facts.route_segments[0])
        )

    def test_facts_are_frozen_equal_and_deterministically_serializable(
        self,
    ) -> None:
        first = _repeated_owner_facts()
        second = _repeated_owner_facts()

        assert first == second
        assert pickle.dumps(first, protocol=5) == pickle.dumps(
            second,
            protocol=5,
        )
        assert pickle.loads(pickle.dumps(first, protocol=5)) == first
        with pytest.raises(FrozenInstanceError):
            first.exposure_order = ()  # type: ignore[misc]


class TestDeterministicDirectionalFindings:
    @pytest.mark.parametrize(
        ("owners", "encounters", "expected"),
        (
            (
                (_cube_owner(), _cube_owner()),
                (),
                _finding(
                    "assembly_include_directional_owner_duplicate",
                    owner="cube",
                ),
            ),
            (
                (_cube_owner(),),
                (
                    _EncounterDeclaration(
                        "cube",
                        "cube",
                        "wave",
                        ("left",),
                    ),
                ),
                _finding(
                    "assembly_encounter_duplicate_name",
                    owner="cube",
                    encounter="cube",
                ),
            ),
            (
                (_cube_owner(),),
                (
                    _EncounterDeclaration(
                        "missing_owner_encounter",
                        "missing_owner",
                        "wave",
                        ("left",),
                    ),
                ),
                _finding(
                    "assembly_encounter_owner_unknown",
                    owner="missing_owner",
                    encounter="missing_owner_encounter",
                ),
            ),
            (
                (_cube_owner(),),
                (
                    _EncounterDeclaration(
                        "empty",
                        "cube",
                        "wave",
                        (),
                    ),
                ),
                _finding(
                    "assembly_encounter_incident_empty",
                    owner="cube",
                    encounter="empty",
                ),
            ),
            (
                (_cube_owner(),),
                (
                    _EncounterDeclaration(
                        "duplicate_incidence",
                        "cube",
                        "wave",
                        ("left", "left"),
                    ),
                ),
                _finding(
                    "assembly_encounter_incident_duplicate",
                    owner="cube",
                    encounter="duplicate_incidence",
                    incident="left",
                ),
            ),
            (
                (_cube_owner(),),
                (
                    _EncounterDeclaration(
                        "ray_many",
                        "cube",
                        "ray",
                        ("left", "top"),
                    ),
                ),
                _finding(
                    "assembly_encounter_ray_multiple_incident",
                    owner="cube",
                    encounter="ray_many",
                    incident="top",
                ),
            ),
        ),
    )
    def test_invalid_fact_inputs_have_exact_stable_coordinates(
        self,
        owners: tuple[_DirectionalOwnerFact, ...],
        encounters: tuple[_EncounterDeclaration, ...],
        expected: str,
    ) -> None:
        facts, findings = _build_directional_facts(
            owners=owners,
            encounters=encounters,
        )

        assert facts is None
        assert findings == [expected]

    def test_structural_zero_endpoint_has_exact_stable_coordinate(
        self,
    ) -> None:
        route_name = (
            "split.bottom.outgoing__to__combine.right.incident"
        )
        facts, findings = _build_directional_facts(
            owners=(_cube_owner(),),
            encounters=(
                _EncounterDeclaration(
                    "split",
                    "cube",
                    "wave",
                    ("left",),
                ),
                _EncounterDeclaration(
                    "combine",
                    "cube",
                    "wave",
                    ("right",),
                ),
            ),
            routes=(
                _RouteDeclaration(
                    "split",
                    "bottom",
                    "combine",
                    "right",
                ),
            ),
        )

        assert facts is None
        assert findings == [
            _finding(
                "assembly_connect_structural_zero",
                owner="cube",
                encounter="split",
                outgoing="bottom",
                route=route_name,
            ),
        ]

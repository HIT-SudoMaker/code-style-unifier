from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pytest
import torch

from chromatix_next.optics import _assembly_facts
from chromatix_next.optics.assembly import RayEncounter, WaveEncounter
from tests.architecture._negative_space_facts import (
    architecture_surface_findings,
    format_findings,
    opr_advance_findings,
    physical_value_wrapper_findings,
    production_findings,
    replay_findings,
    tensor_fact_findings,
)
from tests.architecture._python_symbol_facts import read_python_call_facts

PACKAGE = Path("src/chromatix_next")


def _finding_identities(findings: tuple[object, ...]) -> set[str]:
    return {
        finding.identity  # type: ignore[attr-defined]
        for finding in findings
    }


def test_complete_production_tree_obeys_section_18_negative_space() -> None:
    """
    Every prohibited production surface remains absent with owned diagnostics.
    """

    findings = production_findings()
    assert not findings, format_findings(findings)


@pytest.mark.parametrize(
    ("expected_identity", "source"),
    (
        (
            "state_unification",
            "class OpticalState:\n    pass\n",
        ),
        (
            "generic_scattering",
            "class NPortScatteringMatrix:\n    pass\n",
        ),
        (
            "public_governance",
            "class DirectionalElementBase:\n    pass\n",
        ),
        (
            "recurrence",
            "class AutomaticRouteSearch:\n    pass\n",
        ),
        (
            "evidence_runtime",
            "class EvidenceGraph:\n    pass\n",
        ),
        (
            "evidence_runtime",
            "class Experiment:\n    pass\n",
        ),
        (
            "public_governance",
            "class ComponentRegistry:\n    pass\n",
        ),
        (
            "public_governance",
            "class OpticalSystemRoot:\n    pass\n",
        ),
        (
            "generic_scattering",
            "class GenericNPort:\n    pass\n",
        ),
    ),
)
def test_architecture_surface_guard_rejects_each_speculative_family(
    expected_identity: str,
    source: str,
) -> None:
    """
    One local mutation per speculative family fails for its owning reason.
    """

    findings = architecture_surface_findings(
        source,
        "chromatix_next.counterfactual",
    )
    assert expected_identity in _finding_identities(findings)
    for finding in findings:
        assert finding.owner
        assert finding.rationale
        assert finding.evidence.startswith("chromatix_next.counterfactual")


@pytest.mark.parametrize(
    "source",
    (
        "import torch\n"
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class _RouteFact:\n"
        "    distance: torch.Tensor\n",
        "import torch\n"
        "class _EncounterFact(torch.nn.Module):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        self.register_buffer('state', torch.ones(()))\n",
        "import torch as tensor_module\n"
        "TensorAlias = tensor_module.Tensor\n"
        "class _ClaimFact:\n"
        "    response: TensorAlias\n",
    ),
)
def test_route_encounter_and_claim_fact_guard_rejects_tensor_state(
    source: str,
) -> None:
    """
    Tensor annotations, Module inheritance, aliases, and registration are visible.
    """

    findings = tensor_fact_findings(
        source,
        "chromatix_next.optics._counterfactual_facts",
    )
    assert _finding_identities(findings) == {"tensor_fact_state"}


def test_current_route_encounter_and_ancestry_facts_have_no_tensor_state() -> None:
    """
    Frozen occurrence and route projections carry immutable structural values only.
    """

    fact_types = tuple(
        value
        for name, value in vars(_assembly_facts).items()
        if isinstance(value, type)
        and any(word in name for word in ("Route", "Encounter", "Ancestry"))
    )
    assert fact_types
    for fact_type in fact_types:
        assert not issubclass(fact_type, torch.nn.Module)
        assert all(
            "Tensor" not in str(field.type)
            and "Parameter" not in str(field.type)
            and "Module" not in str(field.type)
            for field in fields(fact_type)
        )
    for encounter_type in (WaveEncounter, RayEncounter):
        assert not issubclass(encounter_type, torch.nn.Module)
        assert not hasattr(encounter_type, "state_dict")


@pytest.mark.parametrize(
    "source",
    (
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class OpticalField:\n"
        "    reference_plane: object\n",
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class RayBundle:\n"
        "    optical_state: object\n",
    ),
)
def test_physical_value_guard_rejects_universal_pose_or_state(
    source: str,
) -> None:
    """
    Per-value reference planes and universal state wrappers fail explicitly.
    """

    findings = physical_value_wrapper_findings(
        source,
        "chromatix_next.optics.counterfactual_value",
    )
    assert _finding_identities(findings) == {"field_pose"}


@pytest.mark.parametrize(
    "source",
    (
        "from chromatix_next.optics.propagation._field_state import "
        "_advance_path_reference\n"
        "def helper(field, distance):\n"
        "    return _advance_path_reference(field, distance)\n",
        "from chromatix_next.optics.propagation._field_state import "
        "_advance_path_reference\n"
        "advance = _advance_path_reference\n"
        "def helper(field, distance):\n"
        "    return advance(field, distance)\n",
        "import chromatix_next.optics.propagation._field_state as state\n"
        "def helper(field, distance):\n"
        "    return state._advance_path_reference(field, distance)\n",
        "from chromatix_next.optics.propagation._field_state import *\n"
        "def helper(field, distance):\n"
        "    return _advance_path_reference(field, distance)\n",
    ),
)
def test_opr_authority_rejects_helper_alias_module_and_star_mutations(
    source: str,
) -> None:
    """
    Every requested import spelling of a second Wave OPR advance is rejected.
    """

    findings = opr_advance_findings(
        source,
        "chromatix_next.optics.element.counterfactual",
    )
    assert "opr_advance" in _finding_identities(findings)


def test_opr_accumulation_helper_cannot_be_copied_to_another_scope() -> None:
    """
    A direct accumulation copy fails even when it avoids the advance helper name.
    """

    source = (
        "from chromatix_next._numerics.optical_path_reference import "
        "accumulate_optical_path_lengths\n"
        "def helper(lengths, increment):\n"
        "    return accumulate_optical_path_lengths(lengths, increment)\n"
    )
    findings = opr_advance_findings(
        source,
        "chromatix_next.optics.element.counterfactual",
    )
    assert _finding_identities(findings) == {"opr_advance"}


def test_workstation_reaches_one_private_assembly_replay() -> None:
    """
    Workstation, Assembly, and the private replay module form one exact spine.
    """

    workstation_source = Path("src/chromatix_next/workstation.py").read_text(
        encoding="utf-8"
    )
    workstation_tree = ast.parse(workstation_source)
    workstation_calls = [
        node
        for node in ast.walk(workstation_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_replay"
    ]
    assert len(workstation_calls) == 1
    workstation_call = workstation_calls[0]
    assert isinstance(workstation_call.func, ast.Attribute)
    replay_receiver = workstation_call.func.value
    assert isinstance(replay_receiver, ast.Name)
    assert replay_receiver.id == "root"

    assembly_path = Path("src/chromatix_next/optics/assembly.py")
    assembly_calls = read_python_call_facts(
        ast.parse(assembly_path.read_text(encoding="utf-8")),
        "chromatix_next.optics.assembly",
    )
    replay_calls = [
        call
        for call in assembly_calls
        if call.source == "chromatix_next.optics._assembly_replay._replay"
    ]
    assert len(replay_calls) == 1
    assert replay_calls[0].scope_name == "_replay"


def test_replay_guard_rejects_a_second_runtime_and_ancestry_graph() -> None:
    """
    A second replay implementation and persisted ancestry graph fail together.
    """

    source = (
        "class _AncestryGraph:\n"
        "    pass\n"
        "def _replay(assembly):\n"
        "    return {}\n"
    )
    findings = replay_findings(
        source,
        "chromatix_next.optics._alternate_runtime",
    )
    assert _finding_identities(findings) == {"replay"}


@pytest.mark.parametrize(
    "route_kind",
    (
        "direct",
        "qualified",
        "star",
        "module_object",
        "package_root",
        "alias",
        "descendant_attribute",
    ),
)
def test_retired_splitter_guard_covers_all_seven_reachability_shapes(
    route_kind: str,
) -> None:
    """
    Direct through descendant attribute compatibility paths remain detectable.
    """

    stem = "nonpolarizing" + "_beam_splitter"
    public_name = "Nonpolarizing" + "BeamSplitter"
    sources = {
        "direct": f"from chromatix_next.optics.element.{stem} import {public_name}\n",
        "qualified": f"from chromatix_next.optics.element import {public_name}\n",
        "star": f"from chromatix_next.optics.element.{stem} import *\n",
        "module_object": (
            "import chromatix_next.optics.element as element_module\n"
            f"legacy = element_module.{public_name}\n"
        ),
        "package_root": (
            "import chromatix_next\n"
            f"legacy = chromatix_next.{public_name}\n"
        ),
        "alias": (
            "from chromatix_next.optics.element import "
            f"{public_name} as LegacySplitter\n"
        ),
        "descendant_attribute": (
            "import chromatix_next\n"
            f"legacy = chromatix_next.optics.element.{stem}.{public_name}\n"
        ),
    }
    findings = architecture_surface_findings(
        sources[route_kind],
        "chromatix_next.counterfactual",
    )
    assert "retired_splitter" in _finding_identities(findings)

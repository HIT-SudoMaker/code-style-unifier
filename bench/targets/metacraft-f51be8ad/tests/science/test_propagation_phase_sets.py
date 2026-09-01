from __future__ import annotations

import hashlib

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import math
from pathlib import Path

import numpy
import pytest

from metacraft.authority import (
    Authority,
    Document,
    Proposal,
    Reference,
    Structure,
    reference_for,
)
from metacraft.science.metalens.aperture import Cell, Circle, Material
from metacraft.science import compile_study
from metacraft.science.metalens.propagation_phase import (
    CELL_LIBRARY_SCHEMA,
    PhaseSelection,
    PhaseSet,
    PropagationCellLibrary,
    PropagationResponse,
    assign_aperture,
    assess_phase_sets,
    form_phase_sets,
)
from metacraft.science.phase import FULL_TURN
from metacraft.science.result import EvidenceOrigin
from metacraft.science.study import Binding, Capability, Study
from tests.brief_fixtures import propagation_brief
from tests.domain_fixtures import compile_with_facts


def _reference_hash(name: str) -> str:
    return f"sha256:{hashlib.sha256(name.encode()).hexdigest()}"

def _reference(name: str) -> Reference:
    return Reference(
        content_hash=_reference_hash(name),
        media_type="application/json",
        metadata_content_hash=_reference_hash("metadata-" + name),
        size_bytes=len(name),
    )


def _admit_record(authority: Authority, name: str) -> Reference:
    decision = authority.decide(
        Proposal.record(Document(f"fixture.{name}", {"name": name})),
        at=authority.view().revision,
    )
    assert decision.body_reference is not None
    return decision.body_reference


def _matching_reference(document: Document) -> Reference:
    return reference_for(document.to_bytes())


def _cell(
    *,
    diameter_nm: int,
    source: Reference,
    atom: str = "silicon nitride",
) -> Cell:
    return Cell(
        identity=f"cell-{atom}-{diameter_nm}",
        atom=Material(atom, "solver native"),
        substrate=Material("silicon dioxide", "solver native"),
        period_nm=220,
        height_nm=500,
        geometry=Circle(diameter_nm),
        source=source,
    )


def _rebuild(
    source: PropagationCellLibrary,
    responses: tuple[PropagationResponse, ...],
    *,
    exact_reference: bool = True,
) -> PropagationCellLibrary:
    document = PropagationCellLibrary.document_from(
        binding_reference=source.binding_reference,
        height_choice_reference=source.height_choice_reference,
        phase_planes=source.phase_planes,
        responses=responses,
    )
    return PropagationCellLibrary(
        binding_reference=source.binding_reference,
        height_choice_reference=source.height_choice_reference,
        evidence_reference=(
            _matching_reference(document)
            if exact_reference
            else _reference("unrelated-library")
        ),
        phase_planes=source.phase_planes,
        responses=responses,
    )


def _library(
    tmp_path: Path,
    *,
    count: int = 16,
    reverse: bool = False,
    collapsed: bool = False,
) -> PropagationCellLibrary:
    tmp_path.mkdir(parents=True, exist_ok=True)
    authority = Authority(tmp_path / "workspace")
    binding = _admit_record(authority, "binding")
    height_choice = _admit_record(authority, "height_choice")
    responses = []
    for level in range(count):
        source = _admit_record(authority, f"observation_{level:02d}")
        responses.append(
            PropagationResponse(
            binding_reference=binding,
            height_choice_reference=height_choice,
            phase_planes="grating_s_params",
            cell=_cell(
                diameter_nm=65 + 5 * level,
                source=source,
            ),
            transmission_real=Decimal(
                str(math.cos(level * math.tau / count))
            ),
            transmission_imaginary=Decimal(
                str(math.sin(level * math.tau / count))
            ),
            realized_phase=Decimal(
                "0" if collapsed else str(level * math.tau / count)
            ),
            useful_power=Decimal("0.82"),
            leakage_power=Decimal("0.08"),
            solver_status="complete",
            warnings=(),
            is_construction_valid=True,
            execution_origin=EvidenceOrigin.SYNTHETIC,
            source_reference=source,
            )
        )
    responses = tuple(responses)
    if reverse:
        responses = tuple(reversed(responses))
    document = PropagationCellLibrary.document_from(
        binding_reference=binding,
        height_choice_reference=height_choice,
        phase_planes="grating_s_params",
        responses=responses,
    )
    references = (
        binding,
        height_choice,
        *(response.source_reference for response in responses),
    )
    structure = Structure.for_document(document, references=references)
    structure_decision = authority.decide(
        Proposal.structure(structure),
        at=authority.view().revision,
    )
    assert structure_decision.body_reference is not None
    decision = authority.decide(
        Proposal.structured(
            document,
            structure_reference=structure_decision.body_reference,
            references=references,
        ),
        at=structure_decision.resulting_revision,
    )
    assert decision.body_reference is not None
    return PropagationCellLibrary(
        binding_reference=binding,
        height_choice_reference=height_choice,
        evidence_reference=decision.body_reference,
        phase_planes="grating_s_params",
        responses=responses,
    )


def test_phase_sets_fail_closed_without_distinct_phase_coverage(
    tmp_path: Path,
) -> None:
    available = assess_phase_sets(
        _library(tmp_path / "insufficient", count=15)
    )
    collapsed = assess_phase_sets(
        _library(tmp_path / "collapsed", collapsed=True)
    )

    assert tuple(item.levels for item in available.phase_sets) == (8, 12)
    assert tuple(item.levels for item in available.refusals) == (16,)
    assert available.as_mapping()["delivered"] == [8, 12]
    refusal_mapping = available.as_mapping()["refused"][0]
    assert {
        key: refusal_mapping[key]
        for key in (
            "available_cells",
            "levels",
            "qualified_cells",
            "reason",
            "required_cells",
        )
    } == {
        "available_cells": 15,
        "levels": 16,
        "qualified_cells": 15,
        "reason": "cell_library_insufficient",
        "required_cells": 16,
    }
    assert refusal_mapping["coverage_diagnostic"][
        "has_necessary_qualified_span"
    ]
    assert collapsed.phase_sets == ()
    assert collapsed.as_mapping()["delivered"] == []
    assert [
        (item["levels"], item["reason"])
        for item in collapsed.as_mapping()["refused"]
    ] == [
        (levels, "cell_library_coverage_inadequate")
        for levels in (8, 12, 16)
    ]


def test_phase_coverage_is_a_constraint_before_power_tradeoffs(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    costly_covered = tuple(
        replace(
            response,
            useful_power=Decimal("0.2"),
            leakage_power=Decimal("10"),
        )
        for response in library.responses
    )
    tempting_uncovered = []
    for index, response in enumerate(library.responses):
        source = _reference(f"outside-bin-{index:02d}")
        tempting_uncovered.append(
            replace(
                response,
                cell=replace(
                    response.cell,
                    identity=f"outside-bin-{index:02d}",
                    geometry=Circle(160 + index * 3),
                    source=source,
                ),
                realized_phase=Decimal("0"),
                useful_power=Decimal("1"),
                leakage_power=Decimal("0"),
                source_reference=source,
            )
        )
    tempting_uncovered = tuple(tempting_uncovered)
    expanded = _rebuild(library, (*costly_covered, *tempting_uncovered))

    phase_sets = form_phase_sets(
        expanded,
        PhaseSelection(useful_power_floor=Decimal("0.1")),
    )

    sixteen = phase_sets[-1]
    assert all(
        state.phase_error <= Decimal("0.1963495408493620774039152115")
        for state in sixteen.states
    )


@pytest.mark.parametrize("levels", (8, 12, 16))
def test_shifted_library_records_the_deterministic_global_phase_offset(
    tmp_path: Path,
    levels: int,
) -> None:
    library = _library(tmp_path, count=levels)
    offset = Decimal("0.17")
    shifted = tuple(
        replace(
            response,
            realized_phase=(
                offset + FULL_TURN * Decimal(level) / Decimal(levels)
            ),
        )
        for level, response in enumerate(library.responses)
    )

    formation = assess_phase_sets(_rebuild(library, shifted))

    phase_set = next(
        item for item in formation.phase_sets if item.levels == levels
    )
    assert phase_set.global_phase_offset == offset
    assert phase_set.useful_power_floor == Decimal(0)
    assert all(
        state.phase_error <= Decimal("1e-24")
        for state in phase_set.states
    )


def test_complete_shifted_library_fails_when_no_response_passes_power_gate(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path, count=16)
    offset = Decimal("0.17")
    shifted_without_power = tuple(
        replace(
            response,
            realized_phase=(
                offset + FULL_TURN * Decimal(level) / Decimal(16)
            ),
            useful_power=Decimal(0),
        )
        for level, response in enumerate(library.responses)
    )

    formation = assess_phase_sets(
        _rebuild(library, shifted_without_power),
    )

    assert formation.phase_sets == ()
    assert tuple(refusal.levels for refusal in formation.refusals) == (
        8,
        12,
        16,
    )
    assert {
        refusal.reason for refusal in formation.refusals
    } == {"cell_library_useful_power_inadequate"}
    refusal = formation.refusals[0]
    assert refusal.available_cells == 16
    assert refusal.qualified_cells == 0
    assert refusal.coverage_diagnostic.response_phase_span >= (
        FULL_TURN * Decimal(6) / Decimal(8)
    )
    assert not refusal.coverage_diagnostic.has_necessary_qualified_span


def test_three_pi_over_two_span_is_only_a_coverage_diagnostic(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path, count=8)
    phase_groups = (
        Decimal(0),
        Decimal(0),
        FULL_TURN / Decimal(5),
        FULL_TURN / Decimal(5),
        FULL_TURN * Decimal(2) / Decimal(5),
        FULL_TURN * Decimal(2) / Decimal(5),
        FULL_TURN * Decimal(3) / Decimal(5),
        FULL_TURN * Decimal(4) / Decimal(5),
    )
    responses = tuple(
        replace(response, realized_phase=phase)
        for response, phase in zip(
            library.responses,
            phase_groups,
            strict=True,
        )
    )

    formation = assess_phase_sets(_rebuild(library, responses))

    refusal = formation.refusals[0]
    assert refusal.levels == 8
    assert refusal.reason == "cell_library_coverage_inadequate"
    assert refusal.coverage_diagnostic.necessary_phase_span == (
        FULL_TURN * Decimal(6) / Decimal(8)
    )
    assert refusal.coverage_diagnostic.has_necessary_qualified_span
    assert refusal.coverage_diagnostic.evaluated_global_offsets > 0


def test_phase_set_document_round_trip_retains_offset_and_power_gate(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path, count=8)
    offset = Decimal("0.11")
    responses = tuple(
        replace(
            response,
            realized_phase=(
                offset + FULL_TURN * Decimal(level) / Decimal(8)
            ),
        )
        for level, response in enumerate(library.responses)
    )
    policy = PhaseSelection(useful_power_floor=Decimal("0.8"))

    phase_set = form_phase_sets(_rebuild(library, responses), policy)[0]

    assert PhaseSet.from_document(phase_set.document()) == phase_set


def test_fixed_height_library_forms_three_distinct_uniform_phase_sets(
    tmp_path: Path,
) -> None:
    phase_sets = form_phase_sets(_library(tmp_path))

    assert tuple(phase_set.levels for phase_set in phase_sets) == (8, 12, 16)
    for phase_set in phase_sets:
        assert len(phase_set.states) == phase_set.levels
        assert len({state.cell_id for state in phase_set.states}) == (
            phase_set.levels
        )
    first = _library(tmp_path / "typed").responses[0]
    assert first.cell.shape == "circular pillar"
    assert first.cell.atom == Material("silicon nitride", "solver native")
    assert first.cell.substrate == Material(
        "silicon dioxide",
        "solver native",
    )
    assert first.cell.period_nm == 220
    assert first.cell.height_nm == 500
    assert first.cell.geometry == Circle(65)
    assert first.cell.identity == "cell-silicon nitride-65"
    assert first.transmission_real.is_finite()
    assert first.solver_status == "complete"
    assert first.source_reference


def test_one_admitted_library_forms_all_three_quantized_apertures(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    phase_sets = form_phase_sets(library)
    phase_set_references = tuple(
        _matching_reference(phase_set.document()) for phase_set in phase_sets
    )
    apertures = tuple(
        assign_aperture(
            _study_awaiting_aperture(
                library,
                phase_set_reference,
            ),
            library,
            phase_set,
            phase_set_reference,
        )
        for phase_set, phase_set_reference in zip(
            phase_sets,
            phase_set_references,
            strict=True,
        )
    )

    assert tuple(len(aperture.states) for aperture in apertures) == (
        8,
        12,
        16,
    )
    assert all(
        library.evidence_reference in aperture.evidence
        for aperture in apertures
    )
    assert all(
        numpy.array_equal(
            apertures[0].coordinates_nm,
            aperture.coordinates_nm,
        )
        for aperture in apertures[1:]
    )


def test_propagation_aperture_rejects_a_foreign_library_fact(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    phase_set = form_phase_sets(library)[0]
    phase_set_reference = _matching_reference(phase_set.document())
    foreign_library_reference = _matching_reference(
        Document(CELL_LIBRARY_SCHEMA, {"foreign": True})
    )
    study = _study_awaiting_aperture(
        library,
        phase_set_reference,
        library_reference=foreign_library_reference,
    )

    with pytest.raises(ValueError, match="cell_library_evidence_mismatch"):
        assign_aperture(
            study,
            library,
            phase_set,
            phase_set_reference,
        )


def _study_awaiting_aperture(
    library: PropagationCellLibrary,
    phase_set_reference: Reference,
    *,
    library_reference: Reference | None = None,
) -> Study:
    brief = replace(
        propagation_brief(),
        cell_period_nm=220,
        atom_height_nm=500,
    )
    initial = compile_study(brief)
    capability_names = tuple(
        dict.fromkeys(
            claim.capability
            for claim in initial.proof.claims
            if claim.capability is not None
        )
    )
    capabilities = tuple(Capability(name) for name in capability_names)
    bindings = tuple(
        Binding(
            name,
            (
                library.binding_reference
                if name == "periodic_transmission_response"
                else _reference(f"binding-{name}")
            ),
        )
        for name in capability_names
    )
    references: dict[str, Reference] = {}
    for claim in initial.proof.claims:
        if claim.name == "aperture":
            break
        references[claim.name] = (
            library.height_choice_reference
            if claim.name == "height_choice"
            else (
                library_reference or library.evidence_reference
                if claim.name == "cell_library"
                else (
                    phase_set_reference
                    if claim.name == "phase_set"
                    else _reference(f"evidence-{claim.name}")
                )
            )
        )
    study, _ = compile_with_facts(
        brief,
        references,
        capabilities=capabilities,
        bindings=bindings,
    )
    if tuple(task.claim for task in study.ready_tasks) != ("aperture",):
        raise AssertionError("fixture did not reach aperture task")
    return study


def test_admitted_cell_library_restores_its_scientific_cells_directly(
    tmp_path: Path,
) -> None:
    """
    Restore admitted cells from their exact aggregate, not solver candidates.
    """

    library = _library(tmp_path)

    restored = PropagationCellLibrary.from_document(
        library.document(),
        evidence_reference=library.evidence_reference,
        binding_reference=library.binding_reference,
        height_choice_reference=library.height_choice_reference,
    )

    assert restored == library
    assert tuple(response.cell for response in restored.responses) == tuple(
        response.cell for response in library.responses
    )
    assert all(
        response.cell.source == response.source_reference
        for response in restored.responses
    )


def test_cell_library_restore_rejects_tamper_and_stale_closure(
    tmp_path: Path,
) -> None:
    """
    Reject altered cells and aggregates detached from the current proof.
    """

    library = _library(tmp_path)

    def restore(values):
        document = Document(
            library.document().schema_identifier,
            values,
        )
        return PropagationCellLibrary.from_document(
            document,
            evidence_reference=reference_for(document.to_bytes()),
            binding_reference=library.binding_reference,
            height_choice_reference=library.height_choice_reference,
        )

    extra = deepcopy(library.document().values)
    extra["unexpected"] = True
    with pytest.raises(ValueError, match="propagation_library_document_invalid"):
        restore(extra)

    wrong_key = deepcopy(library.document().values)
    identity, response = next(iter(wrong_key["responses"].items()))
    del wrong_key["responses"][identity]
    wrong_key["responses"]["another-cell"] = response
    with pytest.raises(ValueError, match="propagation_library_cell_key_mismatch"):
        restore(wrong_key)

    wrong_source = deepcopy(library.document().values)
    response = next(iter(wrong_source["responses"].values()))
    response["cell"]["source"] = _reference("another-source").as_mapping()
    with pytest.raises(ValueError, match="propagation_cell_source_mismatch"):
        restore(wrong_source)

    for field, finding in (
        ("binding_reference", "propagation_library_binding_mixed"),
        ("height_choice_reference", "propagation_library_height_choice_mixed"),
        ("phase_planes", "propagation_library_phase_planes_mixed"),
    ):
        changed = deepcopy(library.document().values)
        response = next(iter(changed["responses"].values()))
        response[field] = (
            "another-plane"
            if field == "phase_planes"
            else _reference(f"another-{field}").as_mapping()
        )
        with pytest.raises(ValueError, match=finding):
            restore(changed)

    document = library.document()
    with pytest.raises(ValueError, match="propagation_library_binding_stale"):
        PropagationCellLibrary.from_document(
            document,
            evidence_reference=library.evidence_reference,
            binding_reference=_reference("stale-binding"),
            height_choice_reference=library.height_choice_reference,
        )
    with pytest.raises(
        ValueError,
        match="propagation_library_height_choice_stale",
    ):
        PropagationCellLibrary.from_document(
            document,
            evidence_reference=library.evidence_reference,
            binding_reference=library.binding_reference,
            height_choice_reference=_reference("stale-height"),
        )


def test_fixed_height_library_refuses_blurred_or_incomplete_evidence(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    first, second, *remaining = library.responses

    with pytest.raises(ValueError, match="propagation_library_height_mixed"):
        _rebuild(
            library,
            (
                first,
                replace(
                    second,
                    cell=replace(second.cell, height_nm=650),
                ),
                *remaining,
            ),
        )
    with pytest.raises(ValueError, match="propagation_library_period_mixed"):
        _rebuild(
            library,
            (
                first,
                replace(
                    second,
                    cell=replace(second.cell, period_nm=670),
                ),
                *remaining,
            ),
        )
    with pytest.raises(ValueError, match="propagation_library_binding_mixed"):
        _rebuild(
            library,
            (
                first,
                replace(second, binding_reference=_reference("other-binding")),
                *remaining,
            ),
        )
    with pytest.raises(
        ValueError,
        match="propagation_library_phase_planes_mixed",
    ):
        _rebuild(
            library,
            (
                first,
                replace(second, phase_planes="another_phase_origin"),
                *remaining,
            ),
        )
    with pytest.raises(
        ValueError,
        match="propagation_library_atom_material_mixed",
    ):
        _rebuild(
            library,
            (
                first,
                replace(
                    second,
                    cell=replace(
                        second.cell,
                        atom=Material(
                            "titanium dioxide",
                            "solver native",
                        ),
                    ),
                ),
                *remaining,
            ),
        )
    with pytest.raises(
        ValueError,
        match="propagation_library_geometry_duplicate",
    ):
        _rebuild(
            library,
            (
                first,
                replace(
                    second,
                    cell=replace(
                        second.cell,
                        identity=first.cell.identity,
                        geometry=first.cell.geometry,
                    ),
                ),
                *remaining,
            ),
        )
    with pytest.raises(
        ValueError,
        match="propagation_library_evidence_duplicate",
    ):
        _rebuild(
            library,
            (
                first,
                replace(
                    second,
                    cell=replace(
                        second.cell,
                        source=first.source_reference,
                    ),
                    source_reference=first.source_reference,
                ),
                *remaining,
            ),
        )
    with pytest.raises(
        ValueError,
        match="propagation_library_reference_mismatch",
    ):
        _rebuild(library, library.responses, exact_reference=False)
    with pytest.raises(ValueError, match="propagation_response_not_finite"):
        replace(first, transmission_real=Decimal("NaN"))
    with pytest.raises(ValueError, match="propagation_construction_invalid"):
        replace(first, is_construction_valid=False)


def test_phase_set_identity_and_selection_ignore_candidate_input_order(
    tmp_path: Path,
) -> None:
    ascending_library = _library(tmp_path / "ascending")
    descending_library = _library(tmp_path / "descending", reverse=True)

    ascending = form_phase_sets(ascending_library)
    descending = form_phase_sets(descending_library)

    assert tuple(item.canonical_bytes() for item in ascending) == tuple(
        item.canonical_bytes() for item in descending
    )
    for phase_set in ascending:
        mapping = phase_set.as_mapping()
        assert mapping["identity"] == phase_set.identity
        assert mapping["library_reference"] == (
            ascending_library.evidence_reference.as_mapping()
        )
        assert mapping["height_choice_reference"] == (
            ascending_library.height_choice_reference.as_mapping()
        )
        for state in phase_set.states:
            assert state.source_reference in ascending_library.source_references
            assert mapping["states"][state.state_id]["cell_id"] == state.cell_id
        assert tuple(state.phase_level for state in phase_set.states) == tuple(
            range(phase_set.levels)
        )
        assert all(
            math.isclose(
                float(state.target_phase),
                level * math.tau / phase_set.levels,
                abs_tol=1e-12,
            )
            for level, state in enumerate(phase_set.states)
        )


def test_negative_solver_phase_uses_the_same_normalized_integer_key(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    last = library.responses[-1]
    negative_last = replace(
        last,
        realized_phase=last.realized_phase - FULL_TURN,
    )

    assert negative_last.realized_phase == last.realized_phase
    assert negative_last.phase_key == last.phase_key

    normalized = form_phase_sets(
        _rebuild(library, (*library.responses[:-1], negative_last))
    )
    assert normalized[-1].states[-1].cell_id == last.cell.identity
    assert normalized[-1].states[-1].realized_phase > 0


def test_computed_full_turn_enters_phase_sets_as_zero(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    first = replace(
        library.responses[0],
        realized_phase=FULL_TURN * Decimal(2),
    )

    phase_set = form_phase_sets(
        _rebuild(library, (first, *library.responses[1:]))
    )[-1]

    assert first.realized_phase == Decimal(0)
    assert phase_set.states[0].realized_phase == Decimal(0)


def test_equidistant_branch_candidates_have_one_input_independent_choice(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    first = library.responses[0]
    below_cut = replace(first, realized_phase=Decimal("-0.01"))
    above_source = _reference("above-cut")
    above_cut = replace(
        first,
        cell=replace(
            first.cell,
            identity="cell-silicon nitride-81",
            geometry=Circle(81),
            source=above_source,
        ),
        realized_phase=Decimal("0.01"),
        source_reference=above_source,
    )
    responses = (below_cut, *library.responses[1:], above_cut)

    ascending = form_phase_sets(_rebuild(library, responses))[-1]
    descending = form_phase_sets(
        _rebuild(library, tuple(reversed(responses)))
    )[-1]

    assert ascending.states[0].cell_id == above_cut.cell.identity
    assert descending.states[0].cell_id == above_cut.cell.identity
    assert ascending.canonical_bytes() == descending.canonical_bytes()


def test_phase_identity_uses_normalized_keys_and_exact_sources(
    tmp_path: Path,
) -> None:
    phase_set = form_phase_sets(_library(tmp_path))[0]
    state = phase_set.states[1]
    equivalent = replace(
        state,
        target_phase=state.target_phase + Decimal("0.00000000000001"),
        realized_phase=state.realized_phase + Decimal("0.00000000000001"),
        phase_error=state.phase_error + Decimal("0.00000000000001"),
        transmission_real=Decimal(
            f"{state.transmission_real}000"
        ),
        useful_power=Decimal("0.8200"),
        leakage_power=Decimal("0.0800"),
        loss=state.loss + Decimal("0.00000000000001"),
    )
    changed_source = replace(
        equivalent,
        source_reference=_reference("different-observation"),
    )

    assert equivalent.state_id == state.state_id
    assert changed_source.state_id != state.state_id
    with pytest.raises(ValueError, match="phase_set_coverage_invalid"):
        replace(
            phase_set,
            states=(
                phase_set.states[0],
                equivalent,
                *phase_set.states[2:],
            ),
        )


def test_phase_set_crosses_authority_with_its_exact_reference(
    tmp_path: Path,
) -> None:
    library = _library(tmp_path)
    phase_set = form_phase_sets(library)[0]
    authority = Authority(tmp_path / "workspace")
    document = phase_set.document()
    references = phase_set.references()
    structure = Structure.for_document(document, references=references)
    structure_decision = authority.decide(
        Proposal.structure(structure),
        at=authority.view().revision,
    )
    assert structure_decision.body_reference is not None
    decision = authority.decide(
        Proposal.structured(
            document,
            structure_reference=structure_decision.body_reference,
            references=references,
        ),
        at=structure_decision.resulting_revision,
    )

    assert decision.body_reference is not None
    assert phase_set.reference_matches(decision.body_reference)
    assert not phase_set.reference_matches(
        replace(
            decision.body_reference,
            metadata_content_hash="sha256:" + "0" * 64,
        )
    )
    assert Document.from_bytes(authority.fetch(decision.body_reference)) == (
        document
    )
    assert not replace(
        phase_set,
        phase_planes="another_reference_plane",
    ).reference_matches(decision.body_reference)

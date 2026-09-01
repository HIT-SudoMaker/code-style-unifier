from __future__ import annotations

from copy import copy, deepcopy
from dataclasses import dataclass, replace
import inspect
from pathlib import Path

import pytest

from metacraft.authority import Authority
from metacraft.authority.protocol import Document
from metacraft.authority.reference import reference_for
from metacraft.authority.session import AuthoritySession
from metacraft.science.metalens.checkpoint import (
    FRONTIER_SCHEMA,
    StudyFrontier,
)
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.study import (
    Binding,
    Capability,
    Evidence,
    Finding,
    FindingKind,
    Study,
)
from tests.brief_fixtures import propagation_brief
from tests.domain_fixtures import evidence_fact_for


@dataclass(frozen=True, slots=True)
class _FixtureAdvice:
    value: str

    def canonical_value(self) -> dict[str, str]:
        return {"value": self.value}


def _brief():
    return replace(
        propagation_brief(),
        cell_period_nm=200,
        atom_height_nm=600,
    )


def _tampered(study: Study, **changes: object) -> Study:
    successor = copy(study)
    for name, value in changes.items():
        object.__setattr__(successor, name, value)
    return successor


def test_frontier_restore_requires_one_authority_session() -> None:
    session = inspect.signature(StudyFrontier.from_document).parameters[
        "session"
    ]

    assert session.default is inspect.Parameter.empty


def test_frontier_checkpoint_round_trips_ordered_complete_studies(
    tmp_path: Path,
) -> None:
    brief = _brief()
    initial = compile_metalens(brief)
    optical = compile_metalens(
        brief,
        capabilities=(Capability("optical_material"),),
    )
    fabrication = compile_metalens(
        brief,
        capabilities=(Capability("fabrication_constraint"),),
    )
    frontier = StudyFrontier.start(initial).replace(
        initial.identity,
        (optical, fabrication),
    )

    restored = StudyFrontier.from_document(
        frontier.document(),
        brief=brief,
        session=AuthoritySession(Authority(tmp_path / "authority")),
    )

    assert frontier.document().schema_identifier == FRONTIER_SCHEMA
    assert tuple(study.identity for study in restored.studies) == (
        optical.identity,
        fabrication.identity,
    )
    assert restored.document().to_bytes() == frontier.document().to_bytes()


def test_frontier_transition_preserves_siblings_and_collapses_convergence() -> None:
    brief = _brief()
    initial = compile_metalens(brief)
    optical = compile_metalens(
        brief,
        capabilities=(Capability("optical_material"),),
    )
    fabrication = compile_metalens(
        brief,
        capabilities=(Capability("fabrication_constraint"),),
    )
    converged = compile_metalens(
        brief,
        capabilities=(
            Capability("fabrication_constraint"),
            Capability("optical_material"),
        ),
    )
    frontier = StudyFrontier.start(initial).replace(
        initial.identity,
        (optical, fabrication),
    )

    after_first = frontier.replace(optical.identity, (converged,))
    after_second = after_first.replace(fabrication.identity, (converged,))

    assert after_first.studies == (converged, fabrication)
    assert after_second.studies == (converged,)


def test_frontier_rejects_a_successor_that_loses_scientific_meaning() -> None:
    brief = _brief()
    predecessor = compile_metalens(
        brief,
        capabilities=(Capability("optical_material"),),
    )
    lossy_successor = compile_metalens(brief)

    with pytest.raises(RuntimeError, match="frontier_capability_lost"):
        StudyFrontier.start(predecessor).replace(
            predecessor.identity,
            (lossy_successor,),
        )


def test_frontier_rejects_a_different_finding_for_the_same_claim() -> None:
    brief = _brief()
    predecessor = compile_metalens(
        brief,
        reported_findings=(
            Finding(
                claim="material_binding",
                kind=FindingKind.UNAVAILABLE,
                needs=("material_unavailable:registration_absent:silicon",),
            ),
        ),
    )
    changed_reason = compile_metalens(
        brief,
        reported_findings=(
            Finding(
                claim="material_binding",
                kind=FindingKind.UNAVAILABLE,
                needs=(
                    "material_unavailable:native_material_absent:"
                    "silicon:Si",
                ),
            ),
        ),
    )

    with pytest.raises(RuntimeError, match="frontier_finding_lost"):
        StudyFrontier.start(predecessor).replace(
            predecessor.identity,
            (changed_reason,),
        )


def test_frontier_rejects_duplicate_or_missing_predecessor_identity() -> None:
    study = compile_metalens(_brief())

    with pytest.raises(ValueError, match="frontier_study_duplicate"):
        StudyFrontier((study, study))

    with pytest.raises(RuntimeError, match="frontier_study_missing"):
        StudyFrontier.start(study).replace("sha256:" + "0" * 64, (study,))


def test_frontier_rejects_empty_or_unchanged_successors() -> None:
    study = compile_metalens(_brief())
    frontier = StudyFrontier.start(study)

    with pytest.raises(ValueError, match="frontier_successors_empty"):
        frontier.replace(study.identity, ())
    with pytest.raises(RuntimeError, match="frontier_successor_unchanged"):
        frontier.replace(study.identity, (study,))


@pytest.mark.parametrize(
    ("change", "reason"),
    (
        ("brief", "frontier_brief_changed"),
        ("design", "frontier_design_changed"),
        ("route", "frontier_proof_changed"),
        ("proof", "frontier_proof_changed"),
    ),
)
def test_frontier_rejects_each_changed_scientific_identity(
    change: str,
    reason: str,
) -> None:
    predecessor = compile_metalens(_brief())
    if change == "brief":
        successor = _tampered(
            predecessor,
            brief=replace(predecessor.brief, wording="Changed brief wording."),
        )
    elif change == "design":
        successor = _tampered(
            predecessor,
            design=replace(predecessor.design, budget="changed design budget"),
        )
    elif change == "route":
        successor = _tampered(
            predecessor,
            route=replace(predecessor.route, applicability="changed route"),
        )
    else:
        successor = _tampered(
            predecessor,
            proof=replace(predecessor.proof, terminal_claims=("changed",)),
        )

    with pytest.raises(RuntimeError, match=reason):
        StudyFrontier.start(predecessor).replace(
            predecessor.identity,
            (successor,),
        )


@pytest.mark.parametrize(
    ("lost", "reason"),
    (
        ("advice", "frontier_advice_lost"),
        ("evidence", "frontier_evidence_lost"),
        ("capability", "frontier_capability_lost"),
        ("binding", "frontier_binding_lost"),
    ),
)
def test_frontier_rejects_each_lost_scientific_collection(
    lost: str,
    reason: str,
) -> None:
    successor = compile_metalens(_brief())
    if lost == "advice":
        predecessor = _tampered(
            successor,
            advice=(_FixtureAdvice("preserve me"),),
        )
    elif lost == "evidence":
        task = successor.ready_tasks[0]
        predecessor = _tampered(
            successor,
            evidence=(
                Evidence(
                    task_identity=task.identity,
                    claim=task.claim,
                    schema=task.schema,
                    reference=reference_for(b"frontier evidence"),
                    binding_reference=task.binding_reference,
                    consultations=task.consultations,
                ),
            ),
        )
    elif lost == "capability":
        predecessor = compile_metalens(
            _brief(),
            capabilities=(Capability("optical_material"),),
        )
    else:
        predecessor = _tampered(
            successor,
            bindings=(
                Binding(
                    "optical_material",
                    reference_for(b"frontier binding"),
                ),
            ),
        )

    with pytest.raises(RuntimeError, match=reason):
        StudyFrontier.start(predecessor).replace(
            predecessor.identity,
            (successor,),
        )


def test_frontier_rejects_unaccounted_prerequisite_loss() -> None:
    predecessor = compile_metalens(_brief())
    successor = _tampered(predecessor, findings=())

    with pytest.raises(RuntimeError, match="frontier_finding_lost"):
        StudyFrontier.start(predecessor).replace(
            predecessor.identity,
            (successor,),
        )


def test_frontier_accepts_monotonic_prerequisite_advancement() -> None:
    brief = _brief()
    predecessor = compile_metalens(brief)
    target_phase = evidence_fact_for(
        brief,
        "target_phase",
        reference_for(b"target phase"),
    )
    successor = compile_metalens(brief, evidence=(target_phase,))

    replaced = StudyFrontier.start(predecessor).replace(
        predecessor.identity,
        (successor,),
    )

    assert replaced.studies == (successor,)


def test_frontier_accepts_findings_accounted_by_ready_task_or_evidence() -> None:
    brief = _brief()
    target_phase = evidence_fact_for(
        brief,
        "target_phase",
        reference_for(b"target phase"),
    )
    predecessor = compile_metalens(brief, evidence=(target_phase,))
    capability = Capability("optical_material")
    binding = Binding(
        "optical_material",
        reference_for(b"optical material binding"),
    )
    ready_successor = compile_metalens(
        brief,
        evidence=(target_phase,),
        capabilities=(capability,),
        bindings=(binding,),
    )
    material_binding = evidence_fact_for(
        brief,
        "material_binding",
        reference_for(b"material binding"),
        evidence=(target_phase,),
        capabilities=(capability,),
        bindings=(binding,),
    )
    evidence_successor = compile_metalens(
        brief,
        evidence=(target_phase, material_binding),
        capabilities=(capability,),
        bindings=(binding,),
    )

    ready_frontier = StudyFrontier.start(predecessor).replace(
        predecessor.identity,
        (ready_successor,),
    )
    evidence_frontier = StudyFrontier.start(predecessor).replace(
        predecessor.identity,
        (evidence_successor,),
    )

    assert ready_frontier.studies == (ready_successor,)
    assert evidence_frontier.studies == (evidence_successor,)


def test_frontier_checkpoint_rejects_tampered_nested_study(
    tmp_path: Path,
) -> None:
    brief = _brief()
    checkpoint = StudyFrontier.start(
        compile_metalens(brief)
    ).document()
    values = deepcopy(dict(checkpoint.values))
    values["studies"]["study_001"]["values"]["brief"]["wording"] = (
        "tampered"
    )

    with pytest.raises(ValueError, match="study_frontier_invalid"):
        StudyFrontier.from_document(
            Document(FRONTIER_SCHEMA, values),
            brief=brief,
            session=AuthoritySession(Authority(tmp_path / "authority")),
        )


def test_frontier_references_cover_every_study_reference_once() -> None:
    brief = _brief()
    first = compile_metalens(brief)
    second = compile_metalens(
        brief,
        capabilities=(Capability("optical_material"),),
    )
    frontier = StudyFrontier((first, second))
    expected = tuple(
        dict.fromkeys(
            (
                *first.direct_references(),
                *second.direct_references(),
            )
        )
    )

    assert frontier.references() == expected

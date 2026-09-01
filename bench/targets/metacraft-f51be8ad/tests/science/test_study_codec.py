from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from metacraft.authority import Document, reference_for
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.study import (
    Binding,
    Capability,
    Finding,
    FindingKind,
    STUDY_SCHEMA,
    Study,
)
from tests.brief_fixtures import geometric_brief, propagation_brief
from tests.domain_fixtures import compile_with_facts


_STUDY_KEYS = {
    "advice",
    "bindings",
    "brief",
    "brief_identity",
    "capabilities",
    "design",
    "evidence",
    "findings",
    "proof",
    "ready_tasks",
    "route",
}


@pytest.mark.parametrize(
    "brief_factory",
    (propagation_brief, geometric_brief),
)
def test_compiled_study_owns_one_complete_canonical_document(
    brief_factory,
) -> None:
    capability = Capability("fabrication_constraint")
    binding = Binding(
        "fabrication_constraint",
        reference_for(b"fabrication binding"),
    )
    study = compile_metalens(
        brief_factory(),
        capabilities=(capability,),
        bindings=(binding,),
    )

    document = study.document()
    restored = Study.from_document(document)

    assert document.schema_identifier == STUDY_SCHEMA
    assert set(document.values) == _STUDY_KEYS
    assert study.canonical_bytes() == document.to_bytes()
    assert restored.document().to_bytes() == document.to_bytes()
    assert restored.capabilities == (capability,)
    assert restored.bindings == (binding,)
    assert restored.route == study.route
    assert restored.proof == study.proof
    assert restored.ready_tasks == study.ready_tasks
    assert restored.findings == study.findings


def test_generic_study_restores_aim_owned_advice_as_opaque_structure() -> None:
    """Generic science preserves advice without knowing its private schema."""

    document = compile_metalens(propagation_brief()).document()
    values = deepcopy(dict(document.values))
    values["advice"] = {
        "advice_001": {
            "brief_identity": "sha256:brief",
            "conclusion": {
                "candidate_identity": "sha256:candidate",
                "kind": "recommendation",
                "reason": "one exact scientific conclusion",
            },
            "grounds": {
                "ground_001": {
                    "identity": "sha256:ground",
                    "kind": "constraint",
                    "source_identity": "sha256:domain",
                    "statement": "period is inside the admitted domain",
                }
            },
        }
    }

    restored = Study.from_document(Document(STUDY_SCHEMA, values))

    assert restored.document().to_bytes() == Document(
        STUDY_SCHEMA,
        values,
    ).to_bytes()


def test_study_restore_rejects_extra_state() -> None:
    document = compile_metalens(propagation_brief()).document()
    values = deepcopy(dict(document.values))
    values["progress"] = "running"

    with pytest.raises(ValueError, match="study_document_invalid"):
        Study.from_document(Document(STUDY_SCHEMA, values))


def test_study_restore_rejects_route_proof_disagreement() -> None:
    document = compile_metalens(propagation_brief()).document()
    values = deepcopy(dict(document.values))
    values["proof"]["route"]["applicability"] = "conflicting route"

    with pytest.raises(ValueError, match="study_proof_mismatch"):
        Study.from_document(Document(STUDY_SCHEMA, values))


def _study_states() -> tuple[Study, Study, Study, Study]:
    brief = replace(
        propagation_brief(),
        cell_period_nm=200,
        atom_height_nm=600,
    )
    base = compile_metalens(brief)
    references = {
        claim.name: reference_for(claim.name.encode("utf-8"))
        for claim in base.proof.claims
    }
    waiting, _ = compile_with_facts(
        brief,
        {"target_phase": references["target_phase"]},
    )
    optical_binding = Binding(
        "optical_material",
        reference_for(b"optical binding"),
    )
    ready, _ = compile_with_facts(
        brief,
        {"target_phase": references["target_phase"]},
        capabilities=(Capability("optical_material"),),
        bindings=(optical_binding,),
    )
    capability_names = tuple(
        dict.fromkeys(
            claim.capability
            for claim in base.proof.claims
            if claim.capability is not None
        )
    )
    binding_reference = reference_for(b"all bindings")
    complete, _ = compile_with_facts(
        brief,
        references,
        capabilities=tuple(
            Capability(name) for name in capability_names
        ),
        bindings=tuple(
            Binding(name, binding_reference)
            for name in capability_names
        ),
    )
    return base, waiting, ready, complete


def test_initial_waiting_ready_and_complete_studies_round_trip() -> None:
    for study in _study_states():
        restored = Study.from_document(study.document())

        assert restored.document().to_bytes() == study.document().to_bytes()


def test_external_unavailability_round_trips_as_a_typed_finding() -> None:
    finding = Finding(
        claim="material_binding",
        kind=FindingKind.UNAVAILABLE,
        needs=("selected material registration is absent",),
    )
    study = compile_metalens(
        propagation_brief(),
        reported_findings=(finding,),
    )

    restored = Study.from_document(study.document())

    assert finding in restored.findings
    assert restored.document().to_bytes() == study.document().to_bytes()


@pytest.mark.parametrize(
    ("needs", "record_references"),
    (
        ((), ()),
        (("",), ()),
        ((1,), ()),
        (["diagnostic"], ()),
        (("first", "second"), ()),
        (("diagnostic",), (reference_for(b"diagnostic"),)),
    ),
)
def test_external_unavailability_has_one_inline_reason_only(
    needs,
    record_references,
) -> None:
    with pytest.raises(ValueError, match="finding_unavailable_invalid"):
        Finding(
            claim="material_binding",
            kind=FindingKind.UNAVAILABLE,
            needs=needs,
            record_references=record_references,
        )


def test_metalens_compiler_rejects_unavailability_for_an_unowned_claim() -> None:
    with pytest.raises(ValueError, match="reported_finding_invalid"):
        compile_metalens(
            propagation_brief(),
            reported_findings=(
                Finding(
                    claim="target_phase",
                    kind=FindingKind.UNAVAILABLE,
                    needs=("external source unavailable",),
                ),
            ),
        )


def test_study_restore_rejects_a_foreign_task_identity() -> None:
    complete = _study_states()[-1]
    values = deepcopy(dict(complete.document().values))
    evidence = values["evidence"]
    evidence["evidence_001"]["task_identity"] = (
        evidence["evidence_002"]["task_identity"]
    )

    with pytest.raises(ValueError, match="study_evidence_invalid"):
        Study.from_document(Document(STUDY_SCHEMA, values))


def test_study_restore_rejects_a_task_without_its_binding() -> None:
    ready = _study_states()[2]
    values = deepcopy(dict(ready.document().values))
    values["bindings"] = {}

    with pytest.raises(ValueError, match="study_task_invalid"):
        Study.from_document(Document(STUDY_SCHEMA, values))


def test_study_restore_rejects_duplicate_complete_state() -> None:
    complete = _study_states()[-1]
    values = deepcopy(dict(complete.document().values))
    values["capabilities"].append(values["capabilities"][0])

    with pytest.raises(ValueError, match="study_capability_invalid"):
        Study.from_document(Document(STUDY_SCHEMA, values))


def test_generic_study_module_does_not_select_metalens() -> None:
    source = Path("src/metacraft/science/study.py").read_text(
        encoding="utf-8"
    )

    assert "science.metalens" not in source
    assert "from .metalens" not in source

from __future__ import annotations

from dataclasses import replace

import pytest

from metacraft.authority import (
    Authority,
    Document,
    Proposal,
    Reference,
    Structure,
    reference_for,
)
from tests.brief_fixtures import propagation_brief
from tests.domain_fixtures import compile_with_facts
from metacraft.science import compile_study
from metacraft.science.study import Binding, Capability
from metacraft.science.result import (
    BoundDocument,
    ResultClosure,
)
from metacraft.science.result import (
    brief_document,
    design_document,
    study_document,
)


def _reference(name: str) -> Reference:
    document = Document(f"fixture.{name}", {"name": name})
    return _document_reference(document)


def _document_reference(document: Document) -> Reference:
    return reference_for(document.to_bytes())


def _admit(
    authority: Authority,
    document: Document,
    *,
    references: tuple[Reference, ...] = (),
) -> Reference:
    revision = authority.view().revision
    if not references:
        decision = authority.decide(Proposal.record(document), at=revision)
    else:
        structure = Structure.for_document(document, references=references)
        structure_decision = authority.decide(
            Proposal.structure(structure),
            at=revision,
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
    return decision.body_reference


def _capability_and_binding_pairs(
    proof,
    binding_reference: Reference,
) -> tuple[tuple[Capability, ...], tuple[Binding, ...]]:
    """
    Pair one Capability and one Binding with each capability named by the
    proof, all sharing the same admitted binding reference.
    """

    capability_names = tuple(
        dict.fromkeys(
            obligation.capability
            for obligation in proof.claims
            if obligation.capability is not None
        )
    )
    capabilities = tuple(Capability(name) for name in capability_names)
    bindings = tuple(
        Binding(name, binding_reference) for name in capability_names
    )
    return capabilities, bindings


def _non_terminal_obligations(proof) -> tuple[str, ...]:
    """
    Name every proof obligation that supplies evidence to the closure.

    The terminal ``result`` claim, when present, is established by the
    closure itself rather than by admitted evidence.
    """

    return tuple(
        obligation.name
        for obligation in proof.claims
        if obligation.name != "result"
    )


def _closed_brief():
    """
    Return the propagation brief with its fabrication knobs preresolved.

    The closure tests exercise ``ResultClosure``'s structural invariants,
    not the LLM-driven height consultation. Pinning the cell period and
    atom height keeps the proof honest while letting every obligation
    become ready without synthesising advice documents.
    """

    return replace(
        propagation_brief(),
        cell_period_nm=200,
        atom_height_nm=600,
    )


def _ready_study():
    brief = _closed_brief()
    base = compile_study(brief)
    binding_reference = _reference("binding")
    capabilities, bindings = _capability_and_binding_pairs(
        base.proof,
        binding_reference,
    )
    references = {
        name: _reference(name)
        for name in _non_terminal_obligations(base.proof)
    }
    study, _facts = compile_with_facts(
        brief,
        references,
        capabilities=capabilities,
        bindings=bindings,
    )
    return brief, study


def _closure(brief, study) -> ResultClosure:
    brief_record = brief_document(brief)
    brief_reference = _document_reference(brief_record)
    design_record = design_document(study, brief_reference)
    design_reference = _document_reference(design_record)
    compiled_record = study_document(
        study,
        brief_reference,
        design_reference,
    )
    study_reference = _document_reference(compiled_record)
    return ResultClosure.bind(
        study,
        brief=BoundDocument(brief_reference, brief_record),
        design=BoundDocument(design_reference, design_record),
        study=BoundDocument(study_reference, compiled_record),
    )


def test_result_closure_binds_the_exact_compiled_study() -> None:
    brief, study = _ready_study()

    closure = _closure(brief, study)

    closure.validate(study)
    assert closure.evidence == tuple(fact.reference for fact in study.evidence)
    assert closure.bindings == tuple(
        dict.fromkeys(
            fact.binding_reference
            for fact in study.evidence
            if fact.binding_reference is not None
        )
    )


@pytest.mark.parametrize(
    ("part", "finding"),
    (
        ("brief", "result_brief_mismatch"),
        ("design", "result_design_mismatch"),
        ("study", "result_study_mismatch"),
    ),
)
def test_result_closure_rejects_a_tampered_top_record(
    part: str,
    finding: str,
) -> None:
    brief, study = _ready_study()
    closure = _closure(brief, study)
    current = getattr(closure, part)
    tampered = Document(
        current.document.schema_identifier,
        {**current.document.values, "unrelated": True},
    )
    altered = replace(
        closure,
        **{
            part: BoundDocument(
                _document_reference(tampered),
                tampered,
            )
        },
    )

    with pytest.raises(ValueError, match=finding):
        altered.validate(study)


@pytest.mark.parametrize(
    ("part", "finding"),
    (
        ("evidence", "result_evidence_closure_mismatch"),
        ("bindings", "result_binding_closure_mismatch"),
    ),
)
def test_result_closure_rejects_an_unrelated_extra_reference(
    part: str,
    finding: str,
) -> None:
    brief, study = _ready_study()
    closure = _closure(brief, study)
    altered = replace(
        closure,
        **{part: (*getattr(closure, part), _reference(f"extra-{part}"))},
    )

    with pytest.raises(ValueError, match=finding):
        altered.validate(study)


def test_authority_proves_the_exact_top_level_closure(tmp_path) -> None:
    authority = Authority(tmp_path / "workspace")
    brief = _closed_brief()
    base = compile_study(brief)
    binding = _admit(
        authority,
        Document("fixture.binding", {"name": "binding"}),
    )
    capabilities, bindings = _capability_and_binding_pairs(
        base.proof,
        binding,
    )
    references: dict[str, Reference] = {}
    for name in _non_terminal_obligations(base.proof):
        references[name] = _admit(
            authority,
            Document(
                f"fixture.{name}",
                {"obligation": name},
            ),
        )
    study, _facts = compile_with_facts(
        brief,
        references,
        capabilities=capabilities,
        bindings=bindings,
    )
    brief_record = brief_document(brief)
    brief_reference = _admit(authority, brief_record)
    design_record = design_document(study, brief_reference)
    design_reference = _admit(
        authority,
        design_record,
        references=(brief_reference,),
    )
    compiled_record = study_document(
        study,
        brief_reference,
        design_reference,
    )
    study_references = tuple(
        dict.fromkeys(
            (
                brief_reference,
                design_reference,
                binding,
                *(fact.reference for fact in study.evidence),
            )
        )
    )
    study_reference = _admit(
        authority,
        compiled_record,
        references=study_references,
    )
    closure = ResultClosure.bind(
        study,
        brief=BoundDocument(brief_reference, brief_record),
        design=BoundDocument(design_reference, design_record),
        study=BoundDocument(study_reference, compiled_record),
    )
    result = Document(
        "metacraft.science.fixture.result",
        {"closure": closure.as_mapping()},
    )
    unrelated = _admit(
        authority,
        Document("fixture.unrelated", {"name": "unrelated"}),
    )
    result_references = closure.references()
    structure = Structure.for_document(
        result,
        references=result_references,
    )
    structure_decision = authority.decide(
        Proposal.structure(structure),
        at=authority.view().revision,
    )
    assert structure_decision.body_reference is not None
    rejected = authority.decide(
        Proposal.structured(
            result,
            structure_reference=structure_decision.body_reference,
            references=(unrelated, *result_references[1:]),
        ),
        at=structure_decision.resulting_revision,
    )
    assert not rejected.admitted

    admitted = authority.decide(
        Proposal.structured(
            result,
            structure_reference=structure_decision.body_reference,
            references=result_references,
        ),
        at=authority.view().revision,
    )
    assert admitted.admitted

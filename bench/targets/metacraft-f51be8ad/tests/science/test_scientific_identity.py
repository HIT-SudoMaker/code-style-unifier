"""
Ticket 02 — Let proof identify meaning and task identify work.

These seams keep the scientific identity system honest:

1. identical inputs produce identical route, proof, and task identities;
2. a changed method changes proof and task identity;
3. a changed brief, prerequisite reference, consultation, choice, or
   binding changes task identity without inventing a new route label;
4. same-schema evidence from the neighboring brief cannot close the task;
5. one exact admitted fact closes the intended task and survives replay.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from metacraft.authority import (
    Authority,
    Document,
    Proposal,
    Reference,
    reference_for,
)
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.material import (
    MATERIAL_BINDING_SCHEMA,
    BoundMaterial,
    MaterialBinding,
)
from metacraft.science.metalens.brief import (
    ApertureExtent,
    ApertureIntent,
    AtomIntent,
    ControlStrategy,
    MaterialIntent,
    MetalensBrief,
    Polarization,
)
from metacraft.science.metalens.height import (
    HEIGHT_DOMAIN_SCHEMA,
)
from metacraft.science.study import (
    Binding,
    Capability,
    Claim,
    Evidence,
    Route,
    RouteChoice,
    Proof,
    Study,
    Task,
)
from tests.brief_fixtures import geometric_brief, propagation_brief


def _route(
    *,
    aim: str = "metalens",
    applicability: str = "declared propagation phase",
    choices: tuple[RouteChoice, ...] = (
        RouteChoice(
            claim="target_phase",
            method="derive_target_phase",
            requires=(),
        ),
    ),
) -> Route:
    return Route(
        aim=aim,
        objectives=("focus",),
        applicability=applicability,
        choices=choices,
    )


def _proof(route: Route | None = None) -> Proof:
    selected = route or _route()
    return Proof(
        route=selected,
        terminal_claims=("target_phase",),
        claims=(
            Claim(
                name="target_phase",
                requires=(),
                capability=None,
                schema="metacraft.science.metalens.target_phase",
            ),
        ),
    )


def _task(
    *,
    proof_identity: str,
    brief_identity: str = "sha256:brief",
    design_identity: str = "sha256:design",
    method: str = "derive_target_phase",
    prerequisite_evidence: tuple[Reference, ...] = (),
    consultations: tuple[Reference, ...] = (),
    binding_reference: Reference | None = None,
    capacity_scope: str | None = None,
) -> Task:
    return Task(
        proof_identity=proof_identity,
        claim="target_phase",
        method=method,
        schema="metacraft.science.metalens.target_phase",
        brief_identity=brief_identity,
        design_identity=design_identity,
        prerequisite_evidence=prerequisite_evidence,
        consultations=consultations,
        binding_reference=binding_reference,
        capacity_scope=capacity_scope,
    )


def _reference(seed: str) -> Reference:
    return reference_for(
        Document("fixture.reference", {"seed": seed}).to_bytes()
    )


def test_identical_inputs_produce_identical_route_proof_and_task_identities() -> None:
    first_route = _route()
    second_route = _route()

    assert first_route.identity == second_route.identity
    assert _proof(first_route).identity == _proof(second_route).identity

    first_task = _task(proof_identity=_proof(first_route).identity)
    second_task = _task(proof_identity=_proof(second_route).identity)
    assert first_task.identity == second_task.identity


def test_science_renames_preserve_canonical_identities() -> None:
    """
    Python vocabulary may change while established canonical bytes do not.
    """

    proof = _proof()
    task = _task(proof_identity=proof.identity)
    study = compile_metalens(propagation_brief())

    assert proof.identity.startswith("sha256:")
    assert task.identity.startswith("sha256:")
    assert study.identity.startswith("sha256:")
    assert proof.canonical_bytes() == _proof().canonical_bytes()
    assert task.identity == _task(proof_identity=proof.identity).identity
    assert study.canonical_bytes() == study.document().to_bytes()


def test_study_keeps_established_claim_storage_keys() -> None:
    """
    New Python claim names map explicitly to established Study storage keys.
    """

    brief = propagation_brief()
    initial = compile_metalens(brief)
    task = initial.ready_tasks[0]
    evidence = Evidence(
        task_identity=task.identity,
        claim=task.claim,
        schema=task.schema,
        reference=_reference("target-phase"),
    )

    encoded = compile_metalens(
        brief,
        evidence=(evidence,),
    ).document().values

    assert encoded["proof"]["terminals"] == ["focus"]
    assert "terminal_claims" not in encoded["proof"]
    assert "obligations" in encoded["proof"]
    assert "claims" not in encoded["proof"]
    fact = encoded["evidence"]["evidence_001"]
    assert fact["obligation"] == "target_phase"
    assert "claim" not in fact


def test_a_changed_method_changes_proof_and_task_identity() -> None:
    base_route = _route(
        choices=(
            RouteChoice(
                claim="target_phase",
                method="derive_target_phase",
                requires=(),
            ),
        ),
    )
    renamed_route = _route(
        choices=(
            RouteChoice(
                claim="target_phase",
                method="derive_phase_target",  # renamed method
                requires=(),
            ),
        ),
    )

    assert base_route.identity != renamed_route.identity
    assert _proof(base_route).identity != _proof(renamed_route).identity

    base_task = _task(
        proof_identity=_proof(base_route).identity,
        method="derive_target_phase",
    )
    renamed_task = _task(
        proof_identity=_proof(renamed_route).identity,
        method="derive_phase_target",
    )
    assert base_task.identity != renamed_task.identity


def test_a_changed_binding_changes_task_identity_without_a_new_route_label() -> None:
    route = _route()
    proof_identity = _proof(route).identity
    binding_a = _reference("binding-a")
    binding_b = _reference("binding-b")

    task_unbound = _task(proof_identity=proof_identity)
    task_bound_a = _task(
        proof_identity=proof_identity,
        binding_reference=binding_a,
        capacity_scope="solver:fixture",
    )
    task_bound_b = _task(
        proof_identity=proof_identity,
        binding_reference=binding_b,
        capacity_scope="solver:fixture",
    )

    assert task_unbound.identity != task_bound_a.identity
    assert task_bound_a.identity != task_bound_b.identity
    # Route identity is independent of binding scope.
    assert route.identity == _route().identity


def test_changed_brief_or_consultation_changes_task_identity() -> None:
    proof_identity = _proof().identity
    consultation = _reference("advice")

    base_task = _task(proof_identity=proof_identity)
    briefed_task = _task(
        proof_identity=proof_identity,
        brief_identity="sha256:different-brief",
    )
    design_task = _task(
        proof_identity=proof_identity,
        design_identity="sha256:different-design",
    )
    consulted_task = _task(
        proof_identity=proof_identity,
        consultations=(consultation,),
    )

    identities = {
        base_task.identity,
        briefed_task.identity,
        design_task.identity,
        consulted_task.identity,
    }
    assert len(identities) == 4


def test_same_schema_evidence_from_a_foreign_task_cannot_close_the_task() -> None:
    """
    Evidence cites one exact task_identity; another task's evidence
    cannot close the proof even when its schema happens to match.
    """

    brief = propagation_brief()
    study = compile_metalens(brief)
    assert isinstance(study, Study)
    task = study.ready_tasks[0]

    own_reference = _reference("own-observation")
    foreign_reference = _reference("foreign-observation")
    own_fact = Evidence(
        task_identity=task.identity,
        claim=task.claim,
        schema=task.schema,
        reference=own_reference,
    )
    foreign_fact = Evidence(
        task_identity="sha256:foreign-task-identity",
        claim=task.claim,
        schema=task.schema,
        reference=foreign_reference,
    )

    own_replay = compile_metalens(brief, evidence=(own_fact,))
    assert tuple(fact.claim for fact in own_replay.evidence) == (
        "target_phase",
    )

    with pytest.raises(ValueError, match="evidence_task_identity_mismatch"):
        compile_metalens(brief, evidence=(foreign_fact,))


def test_one_admitted_fact_closes_the_intended_task_and_survives_replay(
    tmp_path: Path,
) -> None:
    """
    After authority admits the target_phase observation, recompiling from
    the recorded Evidence produces the same study and closes the task.
    """

    authority = Authority(tmp_path / "workspace")
    brief = propagation_brief()
    study = compile_metalens(brief)
    task = study.ready_tasks[0]

    decision = authority.decide(
        Proposal.record(
            Document(
                task.schema,
                {"operation": task.method},
            )
        ),
        at=authority.view().revision,
    )
    assert decision.body_reference is not None

    fact = Evidence(
        task_identity=task.identity,
        claim=task.claim,
        schema=task.schema,
        reference=decision.body_reference,
    )
    first = compile_metalens(brief, evidence=(fact,))
    replayed = compile_metalens(brief, evidence=(fact,))

    assert first == replayed
    assert tuple(fact.claim for fact in first.evidence) == (
        "target_phase",
    )
    assert not first.ready_tasks or all(
        existing.claim != "target_phase"
        for existing in first.ready_tasks
    )


def test_route_identity_is_canonical_content_not_a_strategy_label() -> None:
    """
    Route carries no hand-written name; identity comes from content.
    """

    route = _route()
    assert not hasattr(route, "name")
    # Identity is the canonical digest of route content; it does not embed
    # the applicability sentence verbatim as a label.
    assert route.identity.startswith("sha256:")
    assert "propagation" not in route.identity


def test_method_declares_schema_owned_by_its_module() -> None:
    """
    Each scientific value Module owns a stable schema identifier; methods
    declare that identifier rather than synthesising it from a route string.
    """

    from metacraft.science.metalens.material import MATERIAL_BINDING_SCHEMA
    from metacraft.science.metalens.height import (
        HEIGHT_CHOICE_SCHEMA,
        HEIGHT_DOMAIN_SCHEMA,
    )
    from metacraft.science.metalens.period import (
        PERIOD_CHOICE_SCHEMA,
        PERIOD_DOMAIN_SCHEMA,
    )
    from metacraft.science.metalens.design import (
        TargetPhase,
        require_metalens_design,
    )

    target = TargetPhase.from_design(
        require_metalens_design(compile_metalens(propagation_brief()))
    )
    assert TargetPhase.from_document(target.document()) == target
    assert MATERIAL_BINDING_SCHEMA == (
        "metacraft.science.metalens.material_binding"
    )
    assert PERIOD_DOMAIN_SCHEMA == "metacraft.science.metalens.period_domain"
    assert PERIOD_CHOICE_SCHEMA == "metacraft.science.metalens.period_choice"
    assert HEIGHT_DOMAIN_SCHEMA == "metacraft.science.metalens.height_domain"
    assert HEIGHT_CHOICE_SCHEMA == "metacraft.science.metalens.height_choice"


def test_no_dotted_route_constants_remain_in_production() -> None:
    """
    The historical LOW_NA_*_ROUTE constants are removed.
    """

    from metacraft.science import relationships

    for forbidden in (
        "LOW_NA_PROPAGATION_ROUTE",
        "LOW_NA_GEOMETRIC_ROUTE",
    ):
        assert not hasattr(relationships, forbidden), forbidden

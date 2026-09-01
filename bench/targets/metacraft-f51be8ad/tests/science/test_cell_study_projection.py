from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from metacraft.science.consultation import ConsultationAnswer, Recommendation
from metacraft.science.metalens.aperture import Circle, Rectangle
from metacraft.science.metalens.cell_study import (
    CellInputBasis,
    CellStudyOption,
    LocalPbCellStudy,
    PropagationCellStudy,
    accept_cell_study_answer,
    form_cell_study_consultation,
)
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.periodic_request import project_cell_study_work
from metacraft.science.study import Task
from tests.brief_fixtures import geometric_brief, propagation_brief
from tests.domain_fixtures import height_choice, height_domain, material_binding


def _task(study, binding, claim: str, method: str) -> Task:
    return Task(
        proof_identity="fixture-proof",
        claim=claim,
        method=method,
        schema="fixture.periodic",
        brief_identity=study.brief_identity,
        design_identity="fixture-design",
        prerequisite_evidence=(),
        consultations=(),
        binding_reference=binding.solver_binding_reference,
        capacity_scope="fixture",
    )


def _plan(domain, option):
    choice, choice_reference = height_choice(domain, height_nm=option.height_nm)
    request = form_cell_study_consultation(
        domain,
        (option,),
        height_choice=choice,
        height_choice_reference=choice_reference,
        maximum_periodic_solver_tasks=option.work_count,
    )
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=Recommendation(
            candidate_identity=option.identity,
            reason="Use the exact bounded option.",
            decisive_ground_identities=(request.grounds[0].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )
    return accept_cell_study_answer(request, answer)


def test_plan_projection_preserves_exact_propagation_work() -> None:
    study = compile_metalens(replace(propagation_brief(), cell_period_nm=300))
    binding = material_binding(study)
    domain = height_domain(study)
    option = CellStudyOption(
        height_nm=500,
        study=PropagationCellStudy.from_geometries(
            (Circle(80), Circle(100)),
            input_basis=CellInputBasis.X_LINEAR,
        ),
    )
    plan = _plan(domain, option)
    request = project_cell_study_work(
        SimpleNamespace(brief_identity=study.brief_identity, design=study.design),
        plan,
        task=_task(study, binding, "periodic_transmission", "observe_periodic_transmission"),
        material_binding=binding,
    )
    assert len(request.items) == plan.work_count == 2
    assert [item.input_basis for item in request.items] == ["x linear", "x linear"]
    assert [item.height_nm for item in request.items] == [500, 500]


def test_plan_projection_creates_only_the_two_pb_basis_tasks() -> None:
    study = compile_metalens(geometric_brief())
    binding = material_binding(study)
    domain = height_domain(study)
    option = CellStudyOption(
        height_nm=500,
        study=LocalPbCellStudy.from_geometries(
            (Rectangle(short_side_nm=80, long_side_nm=100),)
        ),
    )
    plan = _plan(domain, option)
    request = project_cell_study_work(
        SimpleNamespace(brief_identity=study.brief_identity, design=study.design),
        plan,
        task=_task(study, binding, "jones_library", "observe_periodic_polarization"),
        material_binding=binding,
    )
    assert len(request.items) == plan.work_count == 2
    assert [item.input_basis for item in request.items] == ["x linear", "y linear"]
    assert all("orientation" not in item.cell_identity for item in request.items)


def test_projection_rejects_a_task_claim_from_the_other_route() -> None:
    study = compile_metalens(replace(propagation_brief(), cell_period_nm=300))
    binding = material_binding(study)
    domain = height_domain(study)
    option = CellStudyOption(
        height_nm=500,
        study=PropagationCellStudy.from_geometries(
            (Circle(80),), input_basis=CellInputBasis.X_LINEAR
        ),
    )
    plan = _plan(domain, option)
    with pytest.raises(ValueError, match="cell_study_plan_task_claim_invalid"):
        project_cell_study_work(
            SimpleNamespace(brief_identity=study.brief_identity, design=study.design),
            plan,
            task=_task(study, binding, "wrong_claim", "observe_periodic_transmission"),
            material_binding=binding,
        )

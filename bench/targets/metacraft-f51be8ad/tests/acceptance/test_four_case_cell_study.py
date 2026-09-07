from __future__ import annotations

import sys

import pytest

from examples import metalens_benchmark_cases
from metacraft.science.consultation import ConsultationAnswer, Recommendation
from metacraft.science.metalens.cell_study import (
    CellStudyPlan,
    CellStudyRoute,
    LocalPbCellStudy,
    PropagationCellStudy,
    accept_cell_study_answer,
    form_cell_study_consultation,
)
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.brief import require_monochromatic_wavelength
from tests.domain_fixtures import height_choice, height_domain


@pytest.mark.parametrize("case", metalens_benchmark_cases(), ids=lambda item: item.name)
def test_four_benchmark_briefs_close_one_bounded_cell_study(
    case,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the blind brief seam finite, deterministic, and solver-free."""

    solver_imports_before = {
        name
        for name in sys.modules
        if name == "metacraft.solvers" or name.startswith("metacraft.solvers.")
    }
    study = compile_metalens(case.brief)
    domain = height_domain(study)
    choice, choice_reference = height_choice(domain)

    request = form_cell_study_consultation(
        domain,
        height_choice=choice,
        height_choice_reference=choice_reference,
        maximum_periodic_solver_tasks=4,
    )
    replay = form_cell_study_consultation(
        domain,
        height_choice=choice,
        height_choice_reference=choice_reference,
        maximum_periodic_solver_tasks=4,
    )

    assert request.document().to_bytes() == replay.document().to_bytes()
    assert request.brief_identity == study.brief_identity
    assert request.wavelength_nm == require_monochromatic_wavelength(
        case.brief.operating_spectrum
    )
    assert request.period_nm == domain.period_nm
    assert request.order_regime == domain.order_regime
    assert request.maximum_periodic_solver_tasks == 4
    assert request.prompt.endswith("Solver evidence comes later.")
    assert all(option.work_count <= 4 for option in request.options)
    assert all(option.height_nm == choice.height_nm for option in request.options)
    assert all(
        option.study.route
        == (
            CellStudyRoute.PROPAGATION_PHASE
            if case.brief.control_strategy.value == "propagation phase"
            else CellStudyRoute.LOCAL_PB
        )
        for option in request.options
    )

    selected = request.options[0]
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=Recommendation(
            candidate_identity=selected.identity,
            reason="Select the first offered option as a conservative review point.",
            decisive_ground_identities=(request.grounds[0].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )
    plan = accept_cell_study_answer(request, answer)

    assert isinstance(plan, CellStudyPlan)
    assert plan.work == selected.work
    assert plan.work_count == len(selected.work)
    assert plan.height_nm == selected.height_nm
    assert plan.height_choice_reference == choice_reference
    assert CellStudyPlan.from_document(plan.document()) == plan
    if case.brief.control_strategy.value == "propagation phase":
        assert isinstance(plan.study, PropagationCellStudy)
        assert all(len(work.response_channels) == 1 for work in plan.work)
    else:
        assert isinstance(plan.study, LocalPbCellStudy)
        assert plan.work_count % 2 == 0
        assert tuple(work.input_basis.value for work in plan.work) == tuple(
            value
            for _ in range(plan.work_count // 2)
            for value in ("x_linear", "y_linear")
        )

    solver_imports_after = {
        name
        for name in sys.modules
        if name == "metacraft.solvers" or name.startswith("metacraft.solvers.")
    }
    assert solver_imports_after == solver_imports_before

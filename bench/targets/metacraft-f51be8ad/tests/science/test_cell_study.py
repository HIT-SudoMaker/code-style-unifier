from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from metacraft.authority.reference import reference_for
from metacraft.science.consultation import (
    ConsultationAnswer,
    EvidenceRequired,
    Recommendation,
    ResearchMode,
)
from metacraft.science.metalens.aperture import Circle, Rectangle
from metacraft.science.metalens.cell_study import (
    CellInputBasis,
    CellResponseChannel,
    CellResponseWork,
    CellStudyEvidenceRequirement,
    CellStudyFormationError,
    CellStudyOption,
    CellStudyPlan,
    InvalidCellStudyAnswer,
    LocalPbCellStudy,
    PropagationCellStudy,
    accept_cell_study_answer,
    form_cell_study_consultation,
    build_bounded_cell_study_options,
)
from metacraft.science.metalens.compiler import compile_metalens
from tests.brief_fixtures import geometric_brief, propagation_brief
from tests.domain_fixtures import height_choice, height_domain


def _pb_domain():
    return height_domain(compile_metalens(geometric_brief()))


def _propagation_domain():
    brief = replace(propagation_brief(), cell_period_nm=300)
    return height_domain(compile_metalens(brief))


def _answer_for(request, option) -> ConsultationAnswer:
    return ConsultationAnswer(
        request_identity=request.identity,
        conclusion=Recommendation(
            candidate_identity=option.identity,
            reason="Prefer the bounded option with conservative coverage.",
            decisive_ground_identities=(request.grounds[0].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )


def _form(
    domain,
    options: tuple[CellStudyOption, ...] | None = None,
    *,
    maximum_periodic_solver_tasks: int,
    research_mode: ResearchMode = ResearchMode.SOURCE_GROUNDED,
):
    selected_height_nm = (
        domain.heights_nm[-1] if options is None else options[0].height_nm
    )
    choice, choice_reference = height_choice(
        domain,
        height_nm=selected_height_nm,
    )
    return form_cell_study_consultation(
        domain,
        options,
        height_choice=choice,
        height_choice_reference=choice_reference,
        maximum_periodic_solver_tasks=maximum_periodic_solver_tasks,
        research_mode=research_mode,
    )


def test_plan_copies_one_exact_height_choice_without_reselecting_height() -> None:
    domain = _propagation_domain()
    choice, choice_reference = height_choice(
        domain,
        height_nm=domain.heights_nm[-1],
    )

    request = form_cell_study_consultation(
        domain,
        height_choice=choice,
        height_choice_reference=choice_reference,
        maximum_periodic_solver_tasks=2,
    )
    plan = accept_cell_study_answer(
        request,
        _answer_for(request, request.options[0]),
    )

    assert all(option.height_nm == choice.height_nm for option in request.options)
    assert isinstance(plan, CellStudyPlan)
    assert plan.height_choice_reference == choice_reference
    assert plan.height_nm == choice.height_nm


def test_form_rejects_a_stale_height_choice_or_a_second_height_owner() -> None:
    domain = _propagation_domain()
    choice, choice_reference = height_choice(
        domain,
        height_nm=domain.heights_nm[-1],
    )
    other_height_nm = domain.heights_nm[0]
    fabrication = domain.resolve_fabrication_range(other_height_nm)
    option = CellStudyOption(
        height_nm=other_height_nm,
        study=PropagationCellStudy.from_geometries(
            (Circle(fabrication.minimum_feature_nm),),
            input_basis=CellInputBasis.X_LINEAR,
        ),
    )

    with pytest.raises(CellStudyFormationError) as stale:
        form_cell_study_consultation(
            domain,
            height_choice=choice,
            height_choice_reference=reference_for(b"stale height choice"),
            maximum_periodic_solver_tasks=1,
        )
    with pytest.raises(CellStudyFormationError) as duplicate_owner:
        form_cell_study_consultation(
            domain,
            (option,),
            height_choice=choice,
            height_choice_reference=choice_reference,
            maximum_periodic_solver_tasks=1,
        )

    assert stale.value.reason == "height_choice_reference_mismatch"
    assert duplicate_owner.value.reason == "cell_study_height_choice_mismatch"


def test_propagation_plan_owns_exact_work_and_round_trips() -> None:
    option = CellStudyOption(
        height_nm=500,
        study=PropagationCellStudy.from_geometries(
            (Circle(80), Circle(100)),
            input_basis=CellInputBasis.X_LINEAR,
        ),
        cautions=("phase coverage remains a forecast until solved",),
    )
    request = _form(
        _propagation_domain(),
        (option,),
        maximum_periodic_solver_tasks=2,
        research_mode=ResearchMode.CLOSED_BOOK,
    )

    plan = accept_cell_study_answer(request, _answer_for(request, option))

    assert isinstance(plan, CellStudyPlan)
    assert plan.work_count == 2
    assert plan.work == option.work
    assert plan.response_channels == (
        CellResponseChannel.COMPLEX_TRANSMISSION,
    )
    assert CellStudyPlan.from_mapping(plan.as_mapping()) == plan
    assert CellStudyPlan.from_document(plan.document()) == plan
    assert CellStudyOption.from_mapping(option.as_mapping()) == option
    assert CellResponseWork.from_mapping(option.work[0].as_mapping()) == (
        option.work[0]
    )
    with pytest.raises(FrozenInstanceError):
        plan.work_count = 3  # type: ignore[misc]


def test_local_pb_studies_only_unrotated_x_y_work() -> None:
    option = CellStudyOption(
        height_nm=500,
        study=LocalPbCellStudy.from_geometries(
            (
                Rectangle(short_side_nm=80, long_side_nm=100),
                Rectangle(short_side_nm=100, long_side_nm=120),
            )
        ),
    )
    request = _form(
        _pb_domain(),
        (option,),
        maximum_periodic_solver_tasks=4,
    )

    plan = accept_cell_study_answer(request, _answer_for(request, option))

    assert isinstance(plan, CellStudyPlan)
    assert plan.work_count == 4
    assert tuple(item.input_basis for item in plan.work) == (
        CellInputBasis.X_LINEAR,
        CellInputBasis.Y_LINEAR,
        CellInputBasis.X_LINEAR,
        CellInputBasis.Y_LINEAR,
    )
    assert plan.response_channels == (
        CellResponseChannel.JONES_XX,
        CellResponseChannel.JONES_YX,
        CellResponseChannel.JONES_XY,
        CellResponseChannel.JONES_YY,
    )
    assert b"orientation" not in plan.canonical_bytes()
    assert CellStudyPlan.from_mapping(plan.as_mapping()) == plan


def test_evidence_requirement_is_not_an_executable_plan() -> None:
    option = CellStudyOption(
        height_nm=500,
        study=PropagationCellStudy.from_geometries(
            (Circle(80),),
            input_basis=CellInputBasis.X_LINEAR,
        ),
    )
    request = _form(
        _propagation_domain(),
        (option,),
        maximum_periodic_solver_tasks=1,
    )
    answer = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=EvidenceRequired(
            missing_fact="material dispersion near the design wavelength",
            reason="No local or sourced ground closes the forecast.",
        ),
        external_claims=(),
    )

    result = accept_cell_study_answer(request, answer)

    assert isinstance(result, CellStudyEvidenceRequirement)
    assert not isinstance(result, CellStudyPlan)
    assert result.request_identity == request.identity


def test_form_rejects_work_beyond_the_explicit_task_limit() -> None:
    option = CellStudyOption(
        height_nm=500,
        study=LocalPbCellStudy.from_geometries(
            (
                Rectangle(short_side_nm=80, long_side_nm=100),
                Rectangle(short_side_nm=100, long_side_nm=120),
            )
        ),
    )

    with pytest.raises(CellStudyFormationError) as raised:
        _form(
            _pb_domain(),
            (option,),
            maximum_periodic_solver_tasks=3,
        )

    assert raised.value.reason == "cell_study_task_limit_exceeded"


def test_bounded_builder_forms_exact_route_work_without_full_grid() -> None:
    domain = _pb_domain()
    options = build_bounded_cell_study_options(
        domain,
        maximum_periodic_solver_tasks=4,
    )
    assert options
    assert all(option.work_count <= 4 for option in options)
    assert all(option.work_count % 2 == 0 for option in options)
    assert all(
        item.input_basis in {CellInputBasis.X_LINEAR, CellInputBasis.Y_LINEAR}
        for option in options
        for item in option.work
    )
    choice, choice_reference = height_choice(
        domain,
        height_nm=options[-1].height_nm,
    )
    selected_options = tuple(
        option for option in options if option.height_nm == choice.height_nm
    )
    request = form_cell_study_consultation(
        domain,
        height_choice=choice,
        height_choice_reference=choice_reference,
        maximum_periodic_solver_tasks=4,
    )
    assert tuple(option.identity for option in request.options) == tuple(
        option.identity for option in selected_options
    )


def test_accept_rejects_stale_and_unknown_option_identities() -> None:
    option = CellStudyOption(
        height_nm=500,
        study=PropagationCellStudy.from_geometries(
            (Circle(80),),
            input_basis=CellInputBasis.X_LINEAR,
        ),
    )
    request = _form(
        _propagation_domain(),
        (option,),
        maximum_periodic_solver_tasks=1,
    )
    stale = ConsultationAnswer(
        request_identity="sha256:" + "0" * 64,
        conclusion=_answer_for(request, option).conclusion,
        external_claims=(),
    )
    unknown = ConsultationAnswer(
        request_identity=request.identity,
        conclusion=Recommendation(
            candidate_identity="sha256:" + "1" * 64,
            reason="Choose a nonexistent option.",
            decisive_ground_identities=(request.grounds[0].identity,),
            external_claim_identities=(),
        ),
        external_claims=(),
    )

    with pytest.raises(InvalidCellStudyAnswer) as stale_error:
        accept_cell_study_answer(request, stale)
    with pytest.raises(InvalidCellStudyAnswer) as unknown_error:
        accept_cell_study_answer(request, unknown)

    assert stale_error.value.reason == "cell_study_answer_request_mismatch"
    assert unknown_error.value.reason == "cell_study_option_unknown"

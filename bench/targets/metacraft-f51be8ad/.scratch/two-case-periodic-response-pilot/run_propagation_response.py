"""Gather and assess one complete propagation-cell library."""

from __future__ import annotations

import math
from pathlib import Path
import sys

from examples import select_metalens_benchmark_case
from metacraft.authority import Document
from metacraft.authority.session import AuthoritySession
from metacraft.canonical import encode_bytes
from metacraft.materials import SolverMaterialLibrary
from metacraft.science._application_root import open_existing_application_root
from metacraft.science.conduct import _recall_frontier, _try_admit_frontier
from metacraft.science.consultation import ConsultationAnswer, Recommendation
from metacraft.science.metalens.cell_study import (
    accept_cell_study_answer,
    form_cell_study_consultation,
)
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.evidence import MetalensEvidence
from metacraft.science.metalens.periodic_cell_evidence import (
    PropagationEvidenceBatch,
    validate_cell_study_batch,
)
from metacraft.science.metalens.periodic_request import project_cell_study_work
from metacraft.science.metalens.propagation_execution import (
    _restore_periodic_transmission,
)
from metacraft.science.metalens.propagation_phase import assess_phase_sets
from metacraft.science.periodic_response import (
    ObservedPeriodicTransmission,
    PeriodicResponseUnavailable,
)
from metacraft.solvers.lumerical_fdtd import (
    LumericalConfig,
    read_lumerical_environment,
)
from metacraft.solvers.lumerical_fdtd.metalens_evidence import (
    LumericalMetalensEvidence,
)
from propagation_cases import PropagationPilotCase, propagation_case


REPOSITORY = Path(__file__).parents[2]
PILOT = Path(__file__).parent


def main(arguments: list[str] | None = None) -> None:
    values = sys.argv[1:] if arguments is None else arguments
    if len(values) != 1:
        raise ValueError("propagation_pilot_case_required")
    case = propagation_case(values[0])
    application_root = PILOT / "acceptance" / f"{case.stem}-live-root"
    brief = select_metalens_benchmark_case(case.benchmark_name).brief
    opened = open_existing_application_root(application_root)
    session = AuthoritySession(opened.authority)
    initial = compile_metalens(brief)
    frontier, frontier_reference = _recall_frontier(
        session,
        brief=brief,
        initial=initial,
    )
    if frontier_reference is None or len(frontier.studies) != 1:
        raise RuntimeError("propagation_frontier_missing")
    study = frontier.studies[0]
    evidence = MetalensEvidence(session)
    height = evidence.height_choice(study)
    domain = evidence.height_domain(study)
    material_binding = evidence.material_binding(study)
    if (height.period_nm, height.height_nm) != (
        case.period_nm,
        case.height_nm,
    ):
        raise RuntimeError("propagation_period_height_drift")

    expected_work_count = (
        (height.maximum_feature_nm - height.minimum_feature_nm)
        // height.dimension_step_nm
        + 1
    )
    consultation = form_cell_study_consultation(
        domain,
        maximum_periodic_solver_tasks=expected_work_count,
    )
    options = tuple(
        option
        for option in consultation.options
        if option.height_nm == height.height_nm
    )
    if len(options) != 1 or options[0].work_count != expected_work_count:
        raise RuntimeError("propagation_complete_cell_study_missing")
    option = options[0]
    answer = ConsultationAnswer(
        request_identity=consultation.identity,
        conclusion=Recommendation(
            candidate_identity=option.identity,
            reason=(
                "Execute every legal lateral diameter at the admitted period "
                "and height."
            ),
            decisive_ground_identities=tuple(
                ground.identity for ground in consultation.grounds
            ),
            external_claim_identities=(),
        ),
        external_claims=(),
    )
    plan = accept_cell_study_answer(consultation, answer)
    _write(case, "cell-study-request.json", consultation.document().to_bytes())
    _write(case, "cell-study-answer.json", answer.document().to_bytes())
    _write(case, "cell-study-plan.json", plan.document().to_bytes())
    session.admit_document(consultation.document())
    session.admit_document(answer.document())
    session.admit_document(plan.document())

    has_response = any(
        fact.claim == "periodic_transmission" for fact in study.evidence
    )
    response_study = (
        compile_metalens(
            study.brief,
            advice=study.advice,
            evidence=tuple(
                fact
                for fact in study.evidence
                if fact.claim
                in {
                    "target_phase",
                    "material_binding",
                    "period_domain",
                    "period_choice",
                    "height_domain",
                    "phase_envelope",
                    "height_choice",
                }
            ),
            capabilities=study.capabilities,
            bindings=study.bindings,
        )
        if has_response
        else study
    )
    tasks = tuple(
        task
        for task in response_study.ready_tasks
        if task.claim == "periodic_transmission"
    )
    if len(tasks) != 1:
        raise RuntimeError("propagation_periodic_task_missing")
    task = tasks[0]
    request = project_cell_study_work(
        response_study,
        plan,
        task=task,
        material_binding=material_binding,
    )
    diameters = tuple(item.geometry.diameter_nm for item in request.items)
    expected_diameters = tuple(
        range(
            height.minimum_feature_nm,
            height.maximum_feature_nm + 1,
            height.dimension_step_nm,
        )
    )
    if diameters != expected_diameters:
        raise RuntimeError("propagation_complete_diameter_grid_invalid")
    print(f"case={case.stem}", flush=True)
    print(f"planned_work_count={len(request.items)}", flush=True)
    print(f"diameter_range={diameters[0]}..{diameters[-1]}", flush=True)

    if has_response:
        observed = _restore_periodic_transmission(evidence, study, request)
        batch_reference = evidence.fact(study, "periodic_transmission").reference
    else:
        environment = read_lumerical_environment(REPOSITORY / ".env.lumerical")
        config = LumericalConfig.from_environ(environment)
        library = SolverMaterialLibrary.decode_bytes(
            (REPOSITORY / "materials" / "lumerical.toml").read_bytes()
        )
        periodic, _materials = LumericalMetalensEvidence(config, library).open(
            authority=opened.authority,
            runs_directory=opened.runs_directory,
        )
        if (
            periodic.context.binding_reference
            != material_binding.solver_binding_reference
        ):
            raise RuntimeError("propagation_solver_binding_drift")
        observed = periodic.observe(request)
        if isinstance(observed, PeriodicResponseUnavailable):
            raise RuntimeError(
                "propagation_periodic_response_unavailable:"
                f"{observed.reason.value}"
            )
    if not isinstance(observed, ObservedPeriodicTransmission):
        raise RuntimeError("propagation_periodic_response_type_invalid")
    validate_cell_study_batch(plan, request, observed)
    batch = PropagationEvidenceBatch(request, observed)
    if not has_response:
        for source in batch.body_references:
            evidence.observe_admitted(source)
        batch_reference = evidence.admit_task(
            task,
            Document(task.schema, batch.as_mapping()),
            sources=(batch.binding_reference, *batch.body_references),
        )
        successor = evidence.with_fact(study, task, batch_reference)
        proposed = frontier.replace(study.identity, (successor,))
        admitted_frontier = _try_admit_frontier(
            session,
            proposed,
            supersedes=frontier_reference,
        )
        if admitted_frontier is None:
            raise RuntimeError("propagation_frontier_admission_conflict")

    height_reference = evidence.fact(study, "height_choice").reference
    library_document = batch.cell_library_document(
        response_study,
        height,
        height_choice_reference=height_reference,
    )
    library_reference = session.admit_document(
        library_document,
        references=(
            batch.binding_reference,
            height_reference,
            *batch.body_references,
        ),
    )
    fixed_library = batch.as_fixed_library(
        response_study,
        height,
        height_choice_reference=height_reference,
        evidence_reference=library_reference,
    )
    assessment = assess_phase_sets(fixed_library)
    diameter_by_cell = {
        response.cell.identity: response.cell.geometry.diameter_nm
        for response in fixed_library.responses
    }
    ordered_phases = sorted(
        float(response.realized_phase) % math.tau
        for response in fixed_library.responses
    )
    cyclic_gaps = tuple(
        right - left
        for left, right in zip(
            ordered_phases,
            (*ordered_phases[1:], ordered_phases[0] + math.tau),
            strict=True,
        )
    )
    summary = {
        "application_root": str(application_root),
        "batch_reference": batch_reference.as_mapping(),
        "benchmark_case": case.benchmark_name,
        "binding_reference": batch.binding_reference.as_mapping(),
        "cell_library_reference": library_reference.as_mapping(),
        "diameters_nm": list(diameters),
        "height_nm": height.height_nm,
        "order_regime": height.order_regime,
        "period_nm": height.period_nm,
        "phase_assessment": assessment.as_mapping(),
        "phase_sets": [
            {
                "global_phase_offset_radians": format(
                    phase_set.global_phase_offset,
                    "f",
                ),
                "levels": phase_set.levels,
                "maximum_phase_error_radians": format(
                    max(state.phase_error for state in phase_set.states),
                    "f",
                ),
                "minimum_useful_power": format(
                    min(state.useful_power for state in phase_set.states),
                    "f",
                ),
                "states": [
                    {
                        "diameter_nm": diameter_by_cell[state.cell_id],
                        "phase_error_radians": format(state.phase_error, "f"),
                        "phase_level": state.phase_level,
                        "realized_phase_radians": format(
                            state.realized_phase,
                            "f",
                        ),
                        "useful_power": format(state.useful_power, "f"),
                    }
                    for state in phase_set.states
                ],
            }
            for phase_set in assessment.phase_sets
        ],
        "response_phase_covering_arc_radians": format(
            math.tau - max(cyclic_gaps),
            ".17g",
        ),
        "responses": [
            {
                "diameter_nm": response.cell.geometry.diameter_nm,
                "leakage_power": format(response.leakage_power, "f"),
                "realized_phase_radians": format(
                    response.realized_phase,
                    "f",
                ),
                "useful_power": format(response.useful_power, "f"),
            }
            for response in fixed_library.responses
        ],
        "schema": "metacraft.acceptance.propagation_response_pilot",
        "work_count": len(request.items),
    }
    _write(case, "response-summary.json", encode_bytes(summary))
    print(f"observed_work_count={len(observed.items)}")
    print(f"delivered_phase_sets={[item.levels for item in assessment.phase_sets]}")
    print(
        "refused_phase_sets="
        + str([(item.levels, item.reason) for item in assessment.refusals])
    )


def _write(case: PropagationPilotCase, suffix: str, content: bytes) -> None:
    (PILOT / "acceptance" / f"{case.stem}-{suffix}").write_bytes(content)


if __name__ == "__main__":
    main()

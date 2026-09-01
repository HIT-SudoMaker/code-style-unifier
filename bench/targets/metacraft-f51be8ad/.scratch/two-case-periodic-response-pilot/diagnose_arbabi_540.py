"""Replay the failed Arbabi 540 nm response without solving again."""

from __future__ import annotations

import json
from pathlib import Path

import numpy

from examples import select_metalens_benchmark_case
from metacraft.authority import Document
from metacraft.authority.session import AuthoritySession
from metacraft.science._application_root import open_existing_application_root
from metacraft.science.conduct import _recall_frontier
from metacraft.science.metalens.cell_study import CellStudyPlan
from metacraft.science.metalens.compiler import compile_metalens
from metacraft.science.metalens.evidence import MetalensEvidence
from metacraft.science.metalens.periodic_request import project_cell_study_work
from metacraft.solvers.lumerical_fdtd import (
    LumericalConfig,
    read_lumerical_environment,
)
from metacraft.solvers.lumerical_fdtd.periodic_execution import (
    _transmission_observation,
)
from metacraft.solvers.lumerical_fdtd.project_execution import ProjectExecution
from metacraft.solvers.lumerical_fdtd.session import LumericalSession, open_engine
from metacraft.solvers.lumerical_fdtd.template.periodic import ConstructionManifest


REPOSITORY = Path(__file__).parents[2]
PILOT = Path(__file__).parent
APPLICATION_ROOT = (
    PILOT / "acceptance" / "arbabi-1000fs-diagnostic-root"
)
FAILED_DIRECTORY = (
    PILOT
    / "acceptance"
    / "arbabi-1000fs-diagnostic-root"
    / "runs"
    / "r"
    / "f3b5cba08b834196"
    / "circular-pillar-height-0900nm-diameter-0540nm"
)


def _print_native_dataset(label: str, dataset: object) -> None:
    if not isinstance(dataset, dict):
        print(
            f"[DEBUG-a540] {label}: "
            f"{type(dataset).__name__}={dataset!r}"
        )
        return
    for key, value in dataset.items():
        array = numpy.asarray(value)
        if array.size <= 12:
            summary = array.squeeze().tolist()
        else:
            summary = f"shape={array.shape}, dtype={array.dtype}"
        print(f"[DEBUG-a540] {label}.{key}={summary!r}")


def main() -> None:
    brief = select_metalens_benchmark_case(
        "arbabi-2015-high-na-propagation"
    ).brief
    opened = open_existing_application_root(APPLICATION_ROOT)
    session = AuthoritySession(opened.authority)
    frontier, reference = _recall_frontier(
        session,
        brief=brief,
        initial=compile_metalens(brief),
    )
    if reference is None or len(frontier.studies) != 1:
        raise RuntimeError("arbabi_frontier_missing")
    study = frontier.studies[0]
    evidence = MetalensEvidence(session)
    plan = CellStudyPlan.from_document(
        Document.from_bytes(
            (PILOT / "acceptance" / "arbabi-cell-study-plan.json").read_bytes()
        )
    )
    tasks = tuple(
        task for task in study.ready_tasks if task.claim == "periodic_transmission"
    )
    if len(tasks) != 1:
        raise RuntimeError("arbabi_periodic_task_missing")
    request = project_cell_study_work(
        study,
        plan,
        task=tasks[0],
        material_binding=evidence.material_binding(study),
    )
    work = next(
        item
        for item in request.items
        if item.geometry.diameter_nm == 540
    )

    config = LumericalConfig.from_environ(
        read_lumerical_environment(REPOSITORY / ".env.lumerical")
    )
    if config.python_api is None:
        raise RuntimeError("lumerical_python_api_missing")
    engine = open_engine(
        config.python_api,
        should_hide=True,
        license_server=config.license_server,
    )
    replay = LumericalSession(engine)
    try:
        engine.load(str(FAILED_DIRECTORY / "after.fsp"))
        engine.runanalysis("grating_response")
        _print_native_dataset(
            "solver_status",
            engine.getresult("FDTD", "status"),
        )
        _print_native_dataset(
            "S",
            engine.getresult("grating_response", "S"),
        )
        _print_native_dataset(
            "T",
            engine.getresult("grating_response", "T"),
        )
        raw = replay.result("grating_response", "propagation")
        coefficient = complex(raw["complex_transmission"])
        print(f"real={coefficient.real!r}")
        print(f"imaginary={coefficient.imag!r}")
        print(f"power={raw['power_transmission']!r}")
        execution = ProjectExecution.from_mapping(
            json.loads((FAILED_DIRECTORY / "execution.json").read_text())
        )
        _transmission_observation(
            work,
            ConstructionManifest(
                template="periodic_transmission",
                expected={},
                observed={},
                mismatches=(),
            ),
            raw,
            execution,
            reference_surface=None,
        )
    finally:
        replay.close()


if __name__ == "__main__":
    main()

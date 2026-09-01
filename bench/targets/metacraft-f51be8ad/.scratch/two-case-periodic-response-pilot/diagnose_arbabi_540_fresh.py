"""Solve the failed Arbabi cell once in a fresh native session."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

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
from metacraft.solvers.lumerical_fdtd.session import open_session
from metacraft.solvers.lumerical_fdtd.template import (
    prepare_periodic_construction,
)


REPOSITORY = Path(__file__).parents[2]
PILOT = Path(__file__).parent
APPLICATION_ROOT = (
    PILOT / "acceptance" / "arbabi-1000fs-diagnostic-root"
)


def main(arguments: list[str] | None = None) -> None:
    values = sys.argv[1:] if arguments is None else arguments
    simulation_time_fs = int(values[0]) if values else 1_000
    diameter_nm = int(values[1]) if len(values) > 1 else 540
    brief = select_metalens_benchmark_case(
        "arbabi-2015-high-na-propagation"
    ).brief
    opened = open_existing_application_root(APPLICATION_ROOT)
    authority = AuthoritySession(opened.authority)
    frontier, reference = _recall_frontier(
        authority,
        brief=brief,
        initial=compile_metalens(brief),
    )
    if reference is None or len(frontier.studies) != 1:
        raise RuntimeError("arbabi_frontier_missing")
    study = frontier.studies[0]
    evidence = MetalensEvidence(authority)
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
        item for item in request.items if item.geometry.diameter_nm == diameter_nm
    )
    construction = replace(
        prepare_periodic_construction(work),
        simulation_time_fs=simulation_time_fs,
    )

    output = (
        PILOT
        / "diagnostics"
        / f"arbabi-{diameter_nm:04d}-fresh-{simulation_time_fs:04d}fs"
    )
    output.mkdir(parents=True, exist_ok=True)
    before = (output / "before.fsp").resolve()
    after = (output / "after.fsp").resolve()
    config = LumericalConfig.from_environ(
        read_lumerical_environment(REPOSITORY / ".env.lumerical")
    )
    if config.python_api is None:
        raise RuntimeError("lumerical_python_api_missing")
    session = open_session(
        config.python_api,
        should_hide=True,
        license_server=config.license_server,
    )
    try:
        manifest = construction.build_in(session)
        print(f"[DEBUG-arbabi] diameter_nm={diameter_nm}", flush=True)
        print(f"[DEBUG-arbabi] simulation_time_fs={simulation_time_fs}", flush=True)
        print(f"[DEBUG-arbabi] construction_mismatches={manifest.mismatches!r}", flush=True)
        session.solve(before, after)
        native_status = session.result("FDTD", "status")
        raw = session.result("grating_response", "propagation")
        coefficient = complex(raw["complex_transmission"])
        print(f"[DEBUG-arbabi] native_status={native_status!r}", flush=True)
        print(f"[DEBUG-arbabi] real={coefficient.real!r}", flush=True)
        print(f"[DEBUG-arbabi] imaginary={coefficient.imag!r}", flush=True)
        print(f"[DEBUG-arbabi] power={raw['power_transmission']!r}", flush=True)
        print(f"[DEBUG-arbabi] before={before}", flush=True)
        print(f"[DEBUG-arbabi] after={after}", flush=True)
    finally:
        session.close()


if __name__ == "__main__":
    main()

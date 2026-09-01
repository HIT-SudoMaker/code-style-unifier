"""Validate ADR 0025 on one existing Arbabi work item in a fresh session."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import json
import math
import sys

from examples import select_metalens_benchmark_case
from metacraft.authority import Document
from metacraft.authority.session import AuthoritySession
from metacraft.canonical import encode_bytes
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
from metacraft.solvers.lumerical_fdtd.session import Session, open_session
from metacraft.solvers.lumerical_fdtd.template import (
    PeriodicConstruction,
    prepare_periodic_construction,
)
from metacraft.solvers.lumerical_fdtd.time_budget import (
    SolverTermination,
    reference_surface_response_change,
    transmission_response_change,
)


REPOSITORY = Path(__file__).parents[2]
PILOT = Path(__file__).parent
APPLICATION_ROOT = PILOT / "acceptance" / "arbabi-1000fs-diagnostic-root"


@dataclass(frozen=True, slots=True)
class NativeAttempt:
    maximum_time_fs: int
    termination: SolverTermination
    response: Mapping[str, object]
    surface: Mapping[str, object]


def main(arguments: list[str] | None = None) -> None:
    values = sys.argv[1:] if arguments is None else arguments
    diameter_nm = int(values[0]) if values else 650
    work = _arbabi_work(diameter_nm)
    construction = prepare_periodic_construction(work)
    output = (
        PILOT
        / "diagnostics"
        / f"arbabi-{diameter_nm:04d}-time-budget-native"
    )
    output.mkdir(parents=True, exist_ok=False)
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
        if manifest.mismatches:
            raise RuntimeError("arbabi_time_budget_construction_mismatch")
        ordinary = _solve_attempt(
            session,
            construction,
            output / "ordinary",
            maximum_time_fs=(
                construction.time_budget.ordinary_maximum_fs
            ),
        )
        attempts = [ordinary]
        response_change = None
        surface_change = None
        disposition = "autoshutoff"
        selected = ordinary
        if ordinary.termination.outcome == "diverged":
            raise RuntimeError("periodic_solver_diverged")
        ordinary_power = Decimal(
            str(ordinary.response["power_transmission"])
        )
        should_extend = (
            ordinary.termination.outcome == "maximum_time"
            or ordinary_power.is_finite()
            and not Decimal(0) <= ordinary_power <= Decimal(1)
        )
        if should_extend:
            session.change_maximum_time(
                "solver",
                construction.time_budget.extended_maximum_fs,
            )
            extended = _solve_attempt(
                session,
                construction,
                output / "extended",
                maximum_time_fs=(
                    construction.time_budget.extended_maximum_fs
                ),
            )
            attempts.append(extended)
            selected = extended
            if extended.termination.outcome == "diverged":
                raise RuntimeError("periodic_solver_diverged")
            extended_power = Decimal(
                str(extended.response["power_transmission"])
            )
            if (
                not extended_power.is_finite()
                or not Decimal(0) <= extended_power <= Decimal(1)
            ):
                raise RuntimeError("periodic_time_budget_exhausted")
            response_converged, response_change = (
                transmission_response_change(
                    ordinary.response,
                    extended.response,
                )
            )
            surface_converged, surface_change = (
                reference_surface_response_change(
                    ordinary.surface,
                    extended.surface,
                )
            )
            if extended.termination.outcome == "autoshutoff":
                disposition = "autoshutoff_after_extension"
            elif response_converged and surface_converged:
                disposition = "converged_by_extension"
            else:
                raise RuntimeError("periodic_time_budget_exhausted")
        response = selected.response
        coefficient = complex(response["complex_transmission"])
        power = float(response["power_transmission"])
        if not 0 <= power <= 1:
            raise RuntimeError("periodic_transmission_response_invalid")
        summary = {
            "attempts": [
                {
                    "maximum_time_fs": attempt.maximum_time_fs,
                    "termination": attempt.termination.as_mapping(),
                }
                for attempt in attempts
            ],
            "benchmark_case": "arbabi-2015-high-na-propagation",
            "construction": construction.as_mapping(),
            "diameter_nm": diameter_nm,
            "disposition": disposition,
            "response_change": response_change,
            "schema": "metacraft.acceptance.periodic_time_budget_native",
            "selected_phase_radians": repr(
                math.atan2(coefficient.imag, coefficient.real)
            ),
            "selected_power": repr(power),
            "surface_change": surface_change,
        }
        summary_path = (
            PILOT
            / "acceptance"
            / f"arbabi-{diameter_nm:04d}-time-budget-native-summary.json"
        )
        summary_path.write_bytes(encode_bytes(summary))
        print(json.dumps(summary, indent=2), flush=True)
    finally:
        session.close()


def _solve_attempt(
    session: Session,
    construction: PeriodicConstruction,
    directory: Path,
    *,
    maximum_time_fs: int,
) -> NativeAttempt:
    directory.mkdir(parents=True)
    session.solve(
        (directory / "before.fsp").resolve(),
        (directory / "after.fsp").resolve(),
    )
    termination = SolverTermination.from_mapping(
        _mapping(session.result("solver", "termination"))
    )
    if termination.outcome == "diverged":
        return NativeAttempt(
            maximum_time_fs=maximum_time_fs,
            termination=termination,
            response={},
            surface={},
        )
    response = _mapping(
        session.result("grating_response", "propagation")
    )
    surface = _mapping(
        session.result("grating_response", "reference_surface")
    )
    return NativeAttempt(
        maximum_time_fs=maximum_time_fs,
        termination=termination,
        response=response,
        surface=surface,
    )


def _arbabi_work(diameter_nm: int):
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
            (
                PILOT
                / "acceptance"
                / "arbabi-cell-study-plan.json"
            ).read_bytes()
        )
    )
    tasks = tuple(
        task
        for task in study.ready_tasks
        if task.claim == "periodic_transmission"
    )
    if len(tasks) != 1:
        raise RuntimeError("arbabi_periodic_task_missing")
    request = project_cell_study_work(
        study,
        plan,
        task=tasks[0],
        material_binding=evidence.material_binding(study),
    )
    matches = tuple(
        item
        for item in request.items
        if item.geometry.diameter_nm == diameter_nm
    )
    if len(matches) != 1:
        raise RuntimeError("arbabi_diameter_missing")
    return matches[0]


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise TypeError("native_response_mapping_required")
    return value


if __name__ == "__main__":
    main()

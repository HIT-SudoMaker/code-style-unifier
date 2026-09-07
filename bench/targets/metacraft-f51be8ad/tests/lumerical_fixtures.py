from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any
from unittest.mock import patch

from metacraft.authority import (
    Authority,
    Document,
    Proposal,
    Reference,
    Revision,
)
from metacraft.authority.session import AuthoritySession
from metacraft.canonical import encode_bytes
from metacraft.materials import (
    AdmittedSolverMaterial,
    SolverMaterial,
)
from metacraft.science import compile_study
from metacraft.science.metalens.material import MaterialBinding
from metacraft.science.study import (
    Study,
)
from metacraft.solvers.lumerical_fdtd import LumericalConfig
from metacraft.solvers.lumerical_fdtd.artifacts import RunDirectory
from metacraft.solvers.lumerical_fdtd.periodic_response import (
    LumericalPeriodicResponse,
)
import metacraft.solvers.lumerical_fdtd.periodic_response as response_module
from metacraft.solvers.lumerical_fdtd.qualification import (
    CapacityObservation,
    InstallationObservation,
    LumericalBinding,
)
from metacraft.workstation import (
    Demand,
    Host,
    LogicalProcessor,
    Layout,
    Memory,
    plan,
)

from tests.domain_fixtures import material_binding


GIBIBYTE = 1024**3


def _reference_hash(name: str) -> str:
    return f"sha256:{hashlib.sha256(name.encode()).hexdigest()}"


def _fixture_reference(name: str) -> Reference:
    """
    Form one stable fake reference used only as a task-identity consultation.
    """

    return Reference(
        content_hash=_reference_hash(name),
        media_type="application/json",
        metadata_content_hash=_reference_hash("metadata-" + name),
        size_bytes=len(name),
    )


def admit_solver_materials(
    authority: Authority,
    catalogue: dict[str, str],
) -> tuple[AdmittedSolverMaterial, ...]:
    """
    Admit exact fixture registrations before invoking the Adapter.
    """

    admitted: list[AdmittedSolverMaterial] = []
    for family, native_name in sorted(catalogue.items()):
        material = SolverMaterial(
            solver="lumerical fdtd",
            family=family,
            native_name=native_name,
            provenance="reviewed fixture",
        )
        decision = authority.decide(
            Proposal.record(material.document()),
            at=authority.view().revision,
        )
        if not decision.admitted or decision.body_reference is None:
            raise RuntimeError("fixture_solver_material_rejected")
        admitted.append(AdmittedSolverMaterial(material, decision.body_reference))
    return tuple(admitted)


def lumerical_config(tmp_path: Path) -> LumericalConfig:
    """
    Create one isolated fake Lumerical installation.
    """

    installation = tmp_path / "Lumerical"
    executable = installation / "bin" / "fdtd-solutions.exe"
    engine = installation / "bin" / "fdtd-engine.exe"
    python_api = installation / "api" / "python" / "lumapi.py"
    license_utility = installation.parent / "licensingclient" / "winx64" / "lmutil.exe"
    executable.parent.mkdir(parents=True)
    python_api.parent.mkdir(parents=True)
    license_utility.parent.mkdir(parents=True)
    executable.write_bytes(b"fixture")
    engine.write_bytes(b"fixture")
    python_api.write_text("# fixture", encoding="utf-8")
    license_utility.write_bytes(b"fixture")
    return LumericalConfig(
        executable=executable,
        python_api=python_api,
        license_utility=license_utility,
        license_server="fixture-license",
        freshness_seconds=300,
        runs_directory=tmp_path / "runs",
    )


def probe_facts(now: datetime) -> InstallationObservation:
    """
    Record one qualified fake solver observation.
    """

    return InstallationObservation(
        product_version="2026 r1",
        api_identity="fixture-api",
        lumerical_gui_limit=2,
        lumerical_solve_limit=2,
        resource_identity="local-cpu",
        observed_at=now,
    )


def workstation_layout(
    now: datetime,
    *,
    physical_cores: int = 12,
) -> Layout:
    """
    Form one deterministic local-workstation placement.
    """

    return plan(
        Demand(workers=8, worker_memory_bytes=GIBIBYTE),
        host=Host(
            identity="fixture-workstation",
            logical_processors=tuple(
                LogicalProcessor(
                    identifier=identifier,
                    processor_group=0,
                    logical_processor=0,
                    core=identifier,
                    last_level_cache=0,
                    numa_node=0,
                )
                for identifier in range(physical_cores)
            ),
            memory=(Memory(numa_node=0, available_bytes=64 * GIBIBYTE),),
            observed_at=now,
        ),
        now=now,
    )


def fixed_planner(layout: Layout) -> Callable[[Demand], Layout]:
    """
    Bind one deterministic layout behind the planner seam for qualification.
    """

    return lambda _demand: layout


def fake_periodic_response(
    *,
    authority: Authority,
    config: LumericalConfig,
    probe: Any,
    planner: Any,
    now: datetime | None = None,
) -> LumericalPeriodicResponse:
    """
    Open the periodic-response Adapter through its observation seam.
    """

    del now
    with (
        patch.object(
            response_module,
            "ProductProbe",
            return_value=probe,
        ),
        patch.object(response_module, "plan", planner),
    ):
        return LumericalPeriodicResponse(
            authority=authority,
            config=config,
            run=RunDirectory(config.runs_directory),
        )


def jones_response(objects: dict[str, Any]) -> dict[str, Any]:
    """
    Return deterministic orthogonal linear-basis observations.
    """

    assert set(objects) == {
        "grating_response",
        "meta_atom",
        "solver",
        "substrate",
    }
    assert objects["grating_response"]["kind"] == "grating_response"
    polarization_angle = objects["grating_response"]["polarization_angle_degrees"]
    if polarization_angle == 0:
        return {
            "output_x": complex(1, 0),
            "output_y": complex(0, 0),
            "phase_planes": "grating_s_params",
            "solver_status": "complete",
            "warnings": [],
        }
    return {
        "output_x": complex(0, 0),
        "output_y": complex(-1, 0),
        "phase_planes": "grating_s_params",
        "solver_status": "complete",
        "warnings": [],
    }


def task_material(
    study: Study,
    binding_reference: Reference,
) -> MaterialBinding:
    """
    Bind fixture material evidence to one exact solver realization.
    """

    return replace(
        material_binding(study),
        solver_binding_reference=binding_reference,
    )


def admit_capacity(
    authority: Authority,
    binding: LumericalBinding,
    capacity: CapacityObservation,
) -> tuple[Reference, Reference]:
    """
    Admit one fake binding and its matching capacity.
    """

    binding_decision = authority.decide(
        Proposal.record(
            Document(
                "metacraft.solver.lumerical_binding",
                binding.as_mapping(),
            )
        ),
        at=Revision.root(),
    )
    assert binding_decision.body_reference is not None
    session = AuthoritySession(authority)
    observation_reference = session.admit_object(
        encode_bytes(capacity.as_mapping()),
        media_type=("application/vnd.metacraft." "lumerical-capacity-observation+json"),
        descriptive_metadata={"object_kind": "LumericalCapacityObservation"},
    )
    capacity_reference = session.admit_capacity(
        scope=capacity.scope,
        limit=capacity.limit,
        qualification_references=(
            binding_decision.body_reference,
            observation_reference,
        ),
    )
    return binding_decision.body_reference, capacity_reference

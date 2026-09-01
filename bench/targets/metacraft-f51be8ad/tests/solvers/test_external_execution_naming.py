from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from inspect import signature
from pathlib import Path

import pytest

from metacraft.solvers.lumerical_fdtd.project_execution import ProjectExecution
from metacraft.solvers.lumerical_fdtd.artifacts import (
    WorkRecord,
    native_solve_sidecar,
)
from metacraft.solvers.lumerical_fdtd.lane import SessionLease
from metacraft.solvers.lumerical_fdtd.qualification import (
    CapacityObservation,
    LumericalConfig,
    LumericalQualification,
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseQualification,
    PeriodicResponseProof,
)
from metacraft.solvers.lumerical_fdtd.session import (
    open_engine,
    open_session,
)
from metacraft.workstation import LogicalProcessor


def test_native_execution_uses_positive_python_names_and_stable_evidence() -> None:
    """
    Python states native execution positively while evidence keeps its schema.
    """

    record = ProjectExecution(
        source="fixture",
        is_native=True,
        project="completed.fsp",
        return_code=0,
        placement={"lane": "lane-01"},
    )

    assert record.is_native
    assert not hasattr(record, "native")
    assert record.as_mapping() == {
        "native": True,
        "placement": {"lane": "lane-01"},
        "project": "completed.fsp",
        "return_code": 0,
        "source": "fixture",
    }
    assert ProjectExecution.from_mapping(record.as_mapping()) == record


def test_qualification_names_exact_product_truth_without_changing_labels(
    tmp_path: Path,
) -> None:
    """
    Configuration and response proof names describe the facts they answer.
    """

    config = LumericalConfig(
        executable=tmp_path / "fdtd-solutions.exe",
        python_api=tmp_path / "lumapi.py",
        license_utility=tmp_path / "lmutil.exe",
        license_server="fixture-license",
    )
    proof = PeriodicResponseProof(
        response_qualifications=(
            PeriodicResponseQualification.qualified(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        )
    )

    assert config.has_required_settings()
    assert not hasattr(config, "complete")
    assert proof.capabilities == (
        "periodic_transmission_response",
        "periodic_reference_surface_response",
    )
    assert not hasattr(proof, "transmission")
    assert not hasattr(proof, "polarization")
    assert not hasattr(proof, "reference_surface")


def test_availability_reuse_and_host_predicates_have_positive_polarity() -> None:
    """
    Availability and reuse are explicit predicates at their owning seams.
    """

    now = datetime(2026, 7, 30, tzinfo=UTC)
    capacity = CapacityObservation(
        scope="lumerical-fdtd/fixture",
        limit=1,
        observed_at=now,
        fresh_until=now + timedelta(minutes=1),
        lumerical_gui_limit=1,
        lumerical_solve_limit=1,
        workstation_limit=1,
    )
    qualification = LumericalQualification(
        reached=("qualified",),
        findings=(),
        binding=None,
        capacity=capacity,
    )
    processor = LogicalProcessor(
        identifier=0,
        processor_group=0,
        logical_processor=0,
        core=0,
        last_level_cache=0,
        numa_node=0,
        is_available=False,
    )

    assert not qualification.is_available_at(now)
    assert not hasattr(qualification, "available_at")
    assert not processor.is_available
    assert not hasattr(processor, "available")
    assert {field.name for field in fields(SessionLease)} >= {"is_reused"}
    assert "reused" not in {field.name for field in fields(SessionLease)}


def test_internal_boolean_parameters_state_their_policy() -> None:
    """
    Private work-life policy parameters still follow the production contract.
    """

    assert "is_session_reused" in {
        field.name for field in fields(WorkRecord)
    }
    assert "session_reused" not in {
        field.name for field in fields(WorkRecord)
    }
    for opener in (open_engine, open_session):
        parameters = signature(opener).parameters
        assert "should_hide" in parameters
        assert "hide" not in parameters


def test_native_solve_sidecar_belongs_to_the_exact_constructed_project(
    tmp_path: Path,
) -> None:
    constructed_project = tmp_path / "before.fsp"

    assert native_solve_sidecar(constructed_project) == (
        tmp_path / "before_p0.log"
    )
    for filename in ("after.fsp", "renamed.fsp", "BEFORE.fsp"):
        with pytest.raises(
            ValueError,
            match="lumerical_constructed_project_name_invalid",
        ):
            native_solve_sidecar(tmp_path / filename)

    assert set(WorkRecord.artifact_manifest().values()) == {
        "after.fsp",
        "before.fsp",
        "construction.json",
        "execution.json",
        "observation.json",
        "solver.log",
        "work.json",
    }
    assert "before_p0.log" not in WorkRecord.artifact_manifest().values()

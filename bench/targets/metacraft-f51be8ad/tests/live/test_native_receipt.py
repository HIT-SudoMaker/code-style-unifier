from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import os
from pathlib import Path

import pytest

from metacraft.authority import Authority
from metacraft.science._application_root import authority_workspace_path

from examples.native_receipt import (
    NATIVE_RECEIPT_RECORD,
    native_receipt_application_root_path,
    run_native_receipt,
    write_native_receipt_record,
)


ROOT = Path(__file__).parents[2]
pytestmark = pytest.mark.lumerical_canary


def _configured_application_root() -> Path:
    if os.environ.get("METACRAFT_RUN_LUMERICAL_CANARY") != "1":
        pytest.skip("live Lumerical receipt canary is disabled")
    if "METACRAFT_CANARY_APPLICATION_ROOT" not in os.environ:
        pytest.skip("METACRAFT_CANARY_APPLICATION_ROOT is absent")
    if not (ROOT / ".env.lumerical").is_file():
        pytest.skip(".env.lumerical is absent")
    return native_receipt_application_root_path(os.environ)


def _mapping(value: object) -> Mapping[str, object]:
    assert isinstance(value, Mapping)
    return value


def _activity(owner: Mapping[str, object]) -> Mapping[str, object]:
    return _mapping(owner["activity"])


def test_one_fresh_application_root_closes_and_replays_five_native_solves() -> None:
    application_root = _configured_application_root()
    assert application_root.is_absolute()
    assert not application_root.exists()

    closure = run_native_receipt(
        repository_root=ROOT,
        application_root=application_root,
        environ=os.environ,
    )
    record = closure.as_mapping()

    assert application_root.is_dir()
    assert record["verification"] == "verified"
    product = _mapping(record["product"])
    assert tuple(product["response_capabilities"]) == (
        "periodic_transmission_response",
        "periodic_polarization_response",
        "periodic_reference_surface_response",
    )
    assert product["binding_reference"]
    assert product["capacity_reference"]
    assert product["material_observation_reference"]

    qualification = _mapping(record["qualification"])
    qualification_activity = _activity(qualification)
    assert qualification_activity["origin"] == "native"
    assert qualification_activity["acquired_authority_work_count"] == 0
    assert qualification_activity["started_external_execution_count"] == 3
    projects = tuple(qualification["completed_projects"])
    assert len(projects) == 3
    assert tuple(_mapping(project)["purpose"] for project in projects) == (
        "transmission_and_reference_surface",
        "x_linear_polarization",
        "y_linear_polarization",
    )

    materials = _mapping(record["materials"])
    materials_activity = _activity(materials)
    assert materials_activity["origin"] == "native"
    assert materials_activity["started_external_execution_count"] == 0
    assert materials_activity["opened_product_session_count"] == 1
    assert materials_activity["closed_product_session_count"] == 1

    candidate = _mapping(record["candidate"])
    assert candidate["height_nm"] == 600
    assert candidate["short_side_nm"] == 100
    assert candidate["long_side_nm"] == 220
    candidate_activity = _activity(candidate)
    assert candidate_activity["origin"] == "native"
    assert candidate_activity["acquired_authority_work_count"] == 2
    assert candidate_activity["settled_authority_work_count"] == 2
    assert candidate_activity["started_external_execution_count"] == 2
    assert candidate_activity["settled_external_execution_count"] == 2
    executions = tuple(_mapping(execution) for execution in candidate["executions"])
    assert tuple(execution["input_basis"] for execution in executions) == (
        "x linear",
        "y linear",
    )
    assert len({execution["work_identity"] for execution in executions}) == 2
    assert (
        len({str(execution["observation_reference"]) for execution in executions}) == 2
    )
    assert len({str(execution["receipt_reference"]) for execution in executions}) == 2
    assert all(execution["execution_origin"] == "native" for execution in executions)

    formation = _mapping(record["formation"])
    assert formation["algorithm"] == "periodic_rectilinear_bilinear_v1"
    formed_surface = _mapping(formation["surface"])
    assert formed_surface["shape"] == [24, 24]
    assert float(str(formed_surface["spacing_m"])) * 24 == pytest.approx(
        400e-9,
        abs=1e-15,
    )
    qualification_reference = formation["qualification_reference"]
    formed = tuple(_mapping(item) for item in formation["surfaces"])
    assert tuple(item["input_basis"] for item in formed) == (
        "x linear",
        "y linear",
    )
    assert tuple(item["raw_observation_reference"] for item in formed) == tuple(
        execution["observation_reference"] for execution in executions
    )
    assert tuple(item["source_references"] for item in formed) == tuple(
        [execution["observation_reference"], qualification_reference]
        for execution in executions
    )
    assert len({str(item["formed_surface_reference"]) for item in formed}) == 2

    candidate_directory = application_root / str(candidate["directory"])
    assert candidate_directory.is_dir()
    assert tuple(
        directory
        for directory in candidate_directory.parent.iterdir()
        if directory.is_dir()
        and (directory / "from-x").is_dir()
        and (directory / "from-y").is_dir()
    ) == (candidate_directory,)
    closure.verify_application_root(application_root)
    assert not tuple(
        permit
        for permit in Authority(authority_workspace_path(application_root)).view().permits
        if permit.state == "open"
    )

    recovery = _mapping(record["recovery"])
    recovery_activity = _activity(recovery)
    assert recovery_activity == {
        "origin": "recorded",
        "acquired_authority_work_count": 0,
        "settled_authority_work_count": 0,
        "started_external_execution_count": 0,
        "settled_external_execution_count": 0,
        "opened_product_session_count": 0,
        "closed_product_session_count": 0,
        "opened_local_placement_count": 0,
        "closed_local_placement_count": 0,
    }
    assert tuple(recovery["work_identities"]) == tuple(
        execution["work_identity"] for execution in executions
    )
    assert tuple(recovery["observation_references"]) == tuple(
        execution["observation_reference"] for execution in executions
    )
    assert tuple(recovery["receipt_references"]) == tuple(
        execution["receipt_reference"] for execution in executions
    )

    native_inventory = tuple(_mapping(entry) for entry in record["native_inventory"])
    recovery_inventory = tuple(
        _mapping(entry) for entry in record["recovery_inventory"]
    )
    assert native_inventory == recovery_inventory
    assert Counter(str(entry["category"]) for entry in native_inventory) == {
        "authority_store": 3,
        "qualification_run": 12,
        "candidate_response": 3,
        "candidate_x_linear_work": 10,
        "candidate_y_linear_work": 10,
    }
    starts = tuple(
        int(_activity(owner)["started_external_execution_count"])
        for owner in (qualification, materials, candidate)
    )
    assert starts == (3, 0, 2)
    assert record["solve_count"] == sum(starts)

    prohibited = {
        "aperture",
        "cell_library",
        "field_propagation",
        "focus",
        "metalens_benchmark_case",
        "project_comparison",
        "scientific_result",
    }
    assert prohibited.isdisjoint(record)

    write_native_receipt_record(
        closure,
        application_root=application_root,
        destination=ROOT / NATIVE_RECEIPT_RECORD,
    )

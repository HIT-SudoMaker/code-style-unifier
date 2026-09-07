from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import json
from pathlib import Path

from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.fixed_measurement.evidence.integrity import sha256_file
from experiments.restoration.fixed_measurement.protocol.inputs import verify_protocol_inputs
from experiments.restoration.fixed_measurement.evidence.studies import (
    REQUIRED_STUDY_ARTIFACT_PATHS,
    build_study_artifacts,
    load_completed_study_result,
)
from experiments.restoration.fixed_measurement.protocol.records import ExperimentReport
from experiments.restoration.fixed_measurement.protocol.plan import (
    FIXED_PLAN_ID,
    compile_fixed_experiment_plan,
)
from experiments.restoration.fixed_measurement.protocol.settings import ProtocolInputs


NATIVE_ARCHIVE_SCHEMA_VERSION = "fixed_measurement_native_archive_v2"
NATIVE_GATE_RELATIVE_PATH = Path(
    "results/restoration/fixed_measurement/native_gate.json"
)


def load_native_fixed_archive(inputs: ProtocolInputs) -> ExperimentReport:
    """Load and verify the native 45-run archive directly."""
    verify_protocol_inputs(inputs)
    project_root = Path(inputs.project_root).resolve()
    gate_path = project_root / NATIVE_GATE_RELATIVE_PATH
    gate = _read_json_object(gate_path, artifact_name="native Fixed gate")
    active_device = gate.get("active_device")
    if (
        gate.get("schema_version") != NATIVE_ARCHIVE_SCHEMA_VERSION
        or gate.get("status") != "PASS"
        or gate.get("study_count") != 45
        or gate.get("plan_id") != FIXED_PLAN_ID
        or not isinstance(active_device, str)
        or gate.get("protocol_identity") != native_protocol_identity(inputs)
    ):
        raise invalid_restoration_contract(
            "native Fixed gate does not match the active protocol"
        )
    plan = compile_fixed_experiment_plan(
        replace(inputs, device=active_device),
    )
    artifact_sha256 = gate.get("artifact_sha256")
    if not isinstance(artifact_sha256, Mapping):
        raise invalid_restoration_contract(
            "native Fixed gate must hash every study artifact"
        )
    expected_paths = {
        _relative_path(project_root, artifacts.run_dir / relative_path)
        for study in plan.studies
        for artifacts in (build_study_artifacts(study, project_root=project_root),)
        for relative_path in REQUIRED_STUDY_ARTIFACT_PATHS
    }
    if set(artifact_sha256) != expected_paths:
        raise invalid_restoration_contract(
            "native Fixed gate does not exactly cover the active studies"
        )
    for relative_path in sorted(expected_paths):
        path = _project_path(project_root, relative_path)
        if not path.is_file() or sha256_file(path) != artifact_sha256[relative_path]:
            raise invalid_restoration_contract(
                f"native Fixed artifact hash mismatch: {relative_path}"
            )

    results = tuple(
        load_completed_study_result(
            study,
            artifacts=build_study_artifacts(study, project_root=project_root),
        )
        for study in plan.studies
    )
    if any(result.status != "PASS" for result in results):
        raise invalid_restoration_contract(
            "native Fixed archive contains a non-passing study"
        )
    report_path = _gated_path(project_root, gate.get("report_path"))
    if sha256_file(report_path) != gate.get("report_sha256"):
        raise invalid_restoration_contract("native Fixed report hash mismatch")
    summary_path = _gated_path(project_root, gate.get("summary_path"))
    if sha256_file(summary_path) != gate.get("summary_sha256"):
        raise invalid_restoration_contract("native Fixed summary hash mismatch")
    return ExperimentReport(
        plan_id=plan.plan_id,
        status="PASS",
        studies=results,
        report_dir=report_path.parent,
        report_json=report_path,
        summary_md=summary_path,
        skipped_run_ids=(),
    )


def native_protocol_identity(inputs: ProtocolInputs) -> dict[str, object]:
    """Return the sealed archive's data and optics identity."""
    return {
        "dataset_root": Path(inputs.dataset_root).as_posix(),
        "split_manifest_hash": compute_config_hash(inputs.split_manifest),
        "operating_point_sha256": sha256_file(inputs.operating_point_path),
    }


def _read_json_object(path: Path, *, artifact_name: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise invalid_restoration_contract(
            f"{artifact_name} is unreadable: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise invalid_restoration_contract(f"{artifact_name} must be a JSON object")
    return payload


def _gated_path(project_root: Path, value: object) -> Path:
    if not isinstance(value, str):
        raise invalid_restoration_contract(
            "native Fixed gate paths must be project-relative strings"
        )
    path = _project_path(project_root, value)
    if not path.is_file():
        raise invalid_restoration_contract(
            f"native Fixed gate path is missing: {value}"
        )
    return path


def _project_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise invalid_restoration_contract(
            "native Fixed archive paths must be project-relative"
        )
    resolved = (project_root / path).resolve()
    if not resolved.is_relative_to(project_root):
        raise invalid_restoration_contract(
            "native Fixed archive path escapes project root"
        )
    return resolved


def _relative_path(project_root: Path, path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(project_root):
        raise invalid_restoration_contract(
            f"native Fixed artifact escapes project root: {path}"
        )
    return resolved.relative_to(project_root).as_posix()

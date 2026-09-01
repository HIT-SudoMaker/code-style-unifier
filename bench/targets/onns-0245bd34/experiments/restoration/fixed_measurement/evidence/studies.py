from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Literal

from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash, write_json
from experiments.restoration.fixed_measurement.protocol.records import StudyConfig, StudyResult
from experiments.restoration.fixed_measurement.protocol.vocabulary import FIXED_TRAINING_ROLES


STUDY_PROVENANCE_SCHEMA_VERSION = "fixed_measurement_study_v1"
STUDY_RESULT_SCHEMA_VERSION = "fixed_measurement_study_result_v1"
REQUIRED_STUDY_ARTIFACT_PATHS = (
    Path("checkpoints/best.pt"),
    Path("checkpoints/last.pt"),
    Path("config.json"),
    Path("provenance.json"),
    Path("runtime.json"),
    Path("checks.json"),
    Path("epoch_metrics.csv"),
    Path("final_metrics.json"),
    Path("operating_point_used.json"),
    Path("study_result.json"),
    Path("summary.md"),
)

_RUN_COMPLETE = "study run {run_id} is already complete"
_PROVENANCE_MISSING = "existing study run is missing provenance.json"
_PROVENANCE_UNREADABLE = "existing study run has unreadable provenance.json"
_PROVENANCE_OBJECT_REQUIRED = "existing study run provenance must be an object"
_FINGERPRINT_MISMATCH = "existing study run config fingerprint does not match"
_PROVENANCE_IDENTITY_MISMATCH = "existing study run provenance identity does not match"
_RESULT_UNREADABLE = "completed study run has unreadable study_result.json"
_RESULT_OBJECT_REQUIRED = "completed study result must be an object"
_RESULT_SCHEMA_MISMATCH = "completed study result schema does not match"
_RESULT_IDENTITY_MISMATCH = "completed study result identity does not match"
_RESULT_STATUS_REQUIRED = "completed study result status must be PASS or FAIL"
_RESULT_METRICS_REQUIRED = "completed study result metrics must be an object"


class StudyRunExistsError(RuntimeError):
    """
    琛ㄧず宸插畬鎴愬師瀛愯繍琛岀姝㈣鐩?    """


class StudyRunProvenanceError(StudyRunExistsError):
    """
    琛ㄧず宸叉湁杩愯鐩綍鏉ユ簮涓嶅吋瀹?    """


@dataclass(frozen=True, slots=True)
class StudyArtifacts:
    """
    璁板綍鍗曟涓嶅彲鍙樼爺绌惰繍琛岀殑鍏ㄩ儴浜х墿
    """

    run_dir: Path
    checkpoints_dir: Path
    best_checkpoint: Path
    last_checkpoint: Path
    figures_dir: Path
    examples_dir: Path
    phase_masks_dir: Path
    operating_point_used_json: Path
    config_json: Path
    provenance_json: Path
    runtime_json: Path
    checks_json: Path
    epoch_metrics_csv: Path
    final_metrics_json: Path
    study_result_json: Path
    summary_md: Path
    failure_records_dir: Path

    def as_training_paths(self) -> Mapping[str, Path]:
        """
        杩斿洖璁粌瀹炵幇浣跨敤鐨勪骇鐗╄矾寰勬槧灏?        """
        return {
            "run_dir": self.run_dir,
            "figures_dir": self.figures_dir,
            "checkpoints_dir": self.checkpoints_dir,
            "best_checkpoint": self.best_checkpoint,
            "last_checkpoint": self.last_checkpoint,
            "operating_point_used_json": self.operating_point_used_json,
            "checks_json": self.checks_json,
            "phase_masks_dir": self.phase_masks_dir,
            "epoch_metrics_csv": self.epoch_metrics_csv,
            "final_metrics_json": self.final_metrics_json,
            "summary_md": self.summary_md,
            "config_json": self.config_json,
            "runtime_json": self.runtime_json,
        }


@dataclass(frozen=True, slots=True)
class PreparedStudyRun:
    """
    璁板綍浜х墿鏍戝強鏂板缓鎴栫画璁姸鎬?    """

    artifacts: StudyArtifacts
    disposition: Literal["new", "resume"]


@dataclass(frozen=True, slots=True)
class StudyArtifactState:
    """
    鎻忚堪姝ｅ紡鐮旂┒鑳藉惁澶嶇敤銆佺画璁垨閲嶆柊寮€濮?    """

    run_id: str
    run_dir: Path
    status: Literal["missing", "resumable", "completed", "invalid"]
    training_status: Literal["PASS", "FAIL"] | None = None
    reason: str = ""


def build_study_artifacts(
    config: StudyConfig,
    *,
    project_root: str | Path,
) -> StudyArtifacts:
    """
    灏嗙爺绌惰韩浠芥槧灏勫埌鍥哄畾娴嬮噺缁撴灉鏍?    """
    config.validate_configuration_unchanged()
    run_dir = (
        Path(project_root)
        / "results"
        / "restoration"
        / "fixed_measurement"
        / config.study_id
        / config.method_id
        / config.run_id
    )
    checkpoints_dir = run_dir / "checkpoints"
    return StudyArtifacts(
        run_dir=run_dir,
        checkpoints_dir=checkpoints_dir,
        best_checkpoint=checkpoints_dir / "best.pt",
        last_checkpoint=checkpoints_dir / "last.pt",
        figures_dir=run_dir / "figures",
        examples_dir=run_dir / "examples",
        phase_masks_dir=run_dir / "phase_masks",
        operating_point_used_json=run_dir / "operating_point_used.json",
        config_json=run_dir / "config.json",
        provenance_json=run_dir / "provenance.json",
        runtime_json=run_dir / "runtime.json",
        checks_json=run_dir / "checks.json",
        epoch_metrics_csv=run_dir / "epoch_metrics.csv",
        final_metrics_json=run_dir / "final_metrics.json",
        study_result_json=run_dir / "study_result.json",
        summary_md=run_dir / "summary.md",
        failure_records_dir=run_dir / "failures",
    )


def prepare_study_run(
    config: StudyConfig,
    *,
    project_root: str | Path,
) -> PreparedStudyRun:
    """
    鏂板缓鎴栨仮澶嶅師瀛愯繍琛屼笖涓嶈鐩栧畬鎴愯瘉鎹?    """
    artifacts = build_study_artifacts(config, project_root=project_root)
    if artifacts.study_result_json.exists():
        message = _RUN_COMPLETE.format(run_id=config.run_id)
        try:
            load_completed_study_result(config, artifacts=artifacts)
        except StudyRunProvenanceError as exc:
            detail = f"{message}: {exc}"
            raise StudyRunProvenanceError(detail) from exc
        raise StudyRunExistsError(message)

    disposition: Literal["new", "resume"]
    if artifacts.run_dir.exists():
        if artifacts.provenance_json.is_file():
            _validate_existing_provenance(artifacts, config)
            disposition = "resume"
        elif _has_run_directory_evidence(artifacts):
            raise StudyRunProvenanceError(_PROVENANCE_MISSING)
        else:
            disposition = "new"
    else:
        artifacts.run_dir.mkdir(parents=True, exist_ok=False)
        disposition = "new"

    if disposition == "new":
        write_json(
            artifacts.provenance_json,
            {
                "schema_version": STUDY_PROVENANCE_SCHEMA_VERSION,
                "study_family": "fixed_measurement",
                "study_id": config.study_id,
                "method_id": config.method_id,
                "profile_name": config.profile_name,
                "seed": config.seed,
                "replicate_id": config.replicate_id,
                "run_id": config.run_id,
                "config_fingerprint": config.config_fingerprint,
                "configuration_hash": compute_config_hash(config.configuration),
                "upstream_run_ids": config.upstream_run_ids,
                "scientific_role": config.study_id,
            },
        )

    for directory in (
        artifacts.checkpoints_dir,
        artifacts.figures_dir,
        artifacts.examples_dir,
        artifacts.phase_masks_dir,
        artifacts.failure_records_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return PreparedStudyRun(artifacts=artifacts, disposition=disposition)


def inspect_study_run(config: StudyConfig) -> StudyArtifactState:
    """
    鍙褰掔被宸叉湁姝ｅ紡鐮旂┒浜х墿
    """
    artifacts = build_study_artifacts(config, project_root=config.project_root)
    if artifacts.study_result_json.is_file():
        try:
            result = load_completed_study_result(config, artifacts=artifacts)
        except StudyRunProvenanceError as exc:
            return StudyArtifactState(
                run_id=config.run_id,
                run_dir=artifacts.run_dir,
                status="invalid",
                reason=str(exc),
            )
        return StudyArtifactState(
            run_id=config.run_id,
            run_dir=artifacts.run_dir,
            status="completed",
            training_status=result.status,  # type: ignore[arg-type]
        )
    if not artifacts.run_dir.exists() or not _has_run_directory_evidence(
        artifacts
    ):
        return StudyArtifactState(
            run_id=config.run_id,
            run_dir=artifacts.run_dir,
            status="missing",
        )
    try:
        _validate_existing_provenance(artifacts, config)
    except StudyRunProvenanceError as exc:
        return StudyArtifactState(
            run_id=config.run_id,
            run_dir=artifacts.run_dir,
            status="invalid",
            reason=str(exc),
        )
    return StudyArtifactState(
        run_id=config.run_id,
        run_dir=artifacts.run_dir,
        status="resumable",
    )


def load_completed_study_result(
    config: StudyConfig,
    *,
    artifacts: StudyArtifacts | None = None,
) -> StudyResult:
    """
    璇诲彇骞舵牎楠屽凡瀹屾垚鍘熷瓙鐮旂┒缁撴灉
    """
    config.validate_configuration_unchanged()
    resolved_artifacts = artifacts or build_study_artifacts(
        config,
        project_root=config.project_root,
    )
    _validate_existing_provenance(resolved_artifacts, config)
    try:
        payload = json.loads(
            resolved_artifacts.study_result_json.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise StudyRunProvenanceError(_RESULT_UNREADABLE) from exc
    if not isinstance(payload, dict):
        raise StudyRunProvenanceError(_RESULT_OBJECT_REQUIRED)
    if payload.get("schema_version") != STUDY_RESULT_SCHEMA_VERSION:
        raise StudyRunProvenanceError(_RESULT_SCHEMA_MISMATCH)
    expected_identity = {
        "study_id": config.study_id,
        "method_id": config.method_id,
        "run_id": config.run_id,
        "config_fingerprint": config.config_fingerprint,
    }
    if config.study_id in FIXED_TRAINING_ROLES:
        expected_identity.update(
            {
                "profile_name": config.profile_name,
                "seed": config.seed,
                "replicate_id": config.replicate_id,
                "upstream_run_ids": list(config.upstream_run_ids),
                "scientific_role": config.study_id,
            }
        )
    if any(payload.get(name) != value for name, value in expected_identity.items()):
        raise StudyRunProvenanceError(_RESULT_IDENTITY_MISMATCH)
    status = payload.get("status")
    if status not in {"PASS", "FAIL"}:
        raise StudyRunProvenanceError(_RESULT_STATUS_REQUIRED)
    metrics = payload.get("metrics")
    if not isinstance(metrics, Mapping):
        raise StudyRunProvenanceError(_RESULT_METRICS_REQUIRED)
    return StudyResult(
        study_id=config.study_id,
        status=status,
        run_id=config.run_id,
        run_dir=resolved_artifacts.run_dir,
        metrics=dict(metrics),
    )


def write_study_failure(
    artifacts: StudyArtifacts,
    config: StudyConfig,
    error: Exception,
) -> Path:
    """Append one execution failure without completing or overwriting the run."""
    artifacts.failure_records_dir.mkdir(parents=True, exist_ok=True)
    existing_indices = [
        int(path.stem.removeprefix("failure_"))
        for path in artifacts.failure_records_dir.glob("failure_*.json")
        if path.stem.removeprefix("failure_").isdigit()
    ]
    next_index = max(existing_indices, default=0) + 1
    failure_name = f"failure_{next_index:04d}.json"
    failure_path = artifacts.failure_records_dir / failure_name
    if failure_path.exists():
        raise StudyRunProvenanceError(
            f"failure record already exists: {failure_path}"
        )
    return write_json(
        failure_path,
        {
            "schema_version": "fixed_measurement_failure_v1",
            "study_id": config.study_id,
            "method_id": config.method_id,
            "profile_name": config.profile_name,
            "seed": config.seed,
            "replicate_id": config.replicate_id,
            "run_id": config.run_id,
            "config_fingerprint": config.config_fingerprint,
            "upstream_run_ids": config.upstream_run_ids,
            "scientific_role": config.study_id,
            "status": "ERROR",
            "error_type": type(error).__name__,
            "error_message": str(error),
        },
    )


def _validate_existing_provenance(
    artifacts: StudyArtifacts,
    config: StudyConfig,
) -> None:
    if not artifacts.provenance_json.is_file():
        raise StudyRunProvenanceError(_PROVENANCE_MISSING)
    try:
        payload = json.loads(artifacts.provenance_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StudyRunProvenanceError(_PROVENANCE_UNREADABLE) from exc
    if not isinstance(payload, dict):
        raise StudyRunProvenanceError(_PROVENANCE_OBJECT_REQUIRED)
    if payload.get("config_fingerprint") != config.config_fingerprint:
        raise StudyRunProvenanceError(_FINGERPRINT_MISMATCH)
    expected_identity = {
        "schema_version": STUDY_PROVENANCE_SCHEMA_VERSION,
        "study_family": "fixed_measurement",
        "study_id": config.study_id,
        "method_id": config.method_id,
        "profile_name": config.profile_name,
        "seed": config.seed,
        "replicate_id": config.replicate_id,
        "run_id": config.run_id,
    }
    if config.study_id in FIXED_TRAINING_ROLES:
        expected_identity.update(
            {
                "configuration_hash": compute_config_hash(config.configuration),
                "upstream_run_ids": list(config.upstream_run_ids),
                "scientific_role": config.study_id,
            }
        )
    if any(payload.get(name) != value for name, value in expected_identity.items()):
        raise StudyRunProvenanceError(_PROVENANCE_IDENTITY_MISMATCH)


def _has_run_directory_evidence(artifacts: StudyArtifacts) -> bool:
    recoverable_directories = {
        artifacts.checkpoints_dir,
        artifacts.figures_dir,
        artifacts.examples_dir,
        artifacts.phase_masks_dir,
    }
    return any(
        path not in recoverable_directories
        for path in artifacts.run_dir.rglob("*")
    )

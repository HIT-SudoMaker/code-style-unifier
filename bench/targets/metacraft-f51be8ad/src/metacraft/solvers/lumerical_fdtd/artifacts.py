from __future__ import annotations

from collections.abc import Mapping
from dataclasses import InitVar, dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import tempfile
from types import MappingProxyType
from typing import Any, ClassVar

from ...authority import Reference
from ...canonical import encode_bytes
from ...science.study import Caution

from .project_execution import ProjectExecution
from .qualification import CapacityObservation

_SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_CONTENT_IDENTITY = re.compile(r"^sha256:([0-9a-f]{64})$")
_CONSTRUCTED_PROJECT_NAME = "before.fsp"
_NATIVE_SOLVE_SIDECAR_NAME = "before_p0.log"


def native_solve_sidecar(constructed_project: Path) -> Path:
    """
    Name the engine-produced log for one exact constructed project.

    Lumerical derives ``before_p0.log`` from ``before.fsp``.  This artifact is
    product output rather than one of the durable MetaCraft work documents,
    so it deliberately remains outside ``WorkRecord.artifact_manifest``.
    """

    if constructed_project.name != _CONSTRUCTED_PROJECT_NAME:
        raise ValueError("lumerical_constructed_project_name_invalid")
    return constructed_project.with_name(_NATIVE_SOLVE_SIDECAR_NAME)


@dataclass(frozen=True, slots=True)
class WorkRecord:
    """
    Owns every durable fact produced by one native solver work item.
    """

    work_identity: str
    session_identity: str
    lane_identity: str
    is_session_reused: bool
    construction: Mapping[str, object]
    execution: ProjectExecution
    observation: Mapping[str, object]
    log: str
    capacity: CapacityObservation
    capacity_reference: Reference
    lease_placement: InitVar[Mapping[str, object]]

    _ARTIFACTS: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "completed_project": "after.fsp",
            "constructed_project": _CONSTRUCTED_PROJECT_NAME,
            "construction": "construction.json",
            "execution": "execution.json",
            "log": "solver.log",
            "observation": "observation.json",
            "record": "work.json",
        }
    )

    def __post_init__(
        self,
        lease_placement: Mapping[str, object],
    ) -> None:
        """
        Freeze one unambiguous set of durable work facts.
        """

        identities = (
            self.work_identity,
            self.session_identity,
            self.lane_identity,
        )
        if any(not value.strip() for value in identities):
            raise ValueError("work_record_identity_required")
        if len(set(identities)) != len(identities):
            raise ValueError("work_record_identity_ambiguous")
        if dict(self.execution.placement) != dict(lease_placement):
            raise ValueError("work_record_placement_mismatch")
        lane = self.execution.placement.get("lane")
        if not isinstance(lane, Mapping) or lane.get("identity") != self.lane_identity:
            raise ValueError("work_record_lane_mismatch")
        observation = dict(self.observation)
        observed_execution = observation.pop("execution", None)
        if observed_execution is not None and (
            not isinstance(observed_execution, Mapping)
            or dict(observed_execution) != self.execution.as_mapping()
        ):
            raise ValueError("work_record_execution_mismatch")
        object.__setattr__(
            self,
            "construction",
            MappingProxyType(dict(self.construction)),
        )
        object.__setattr__(
            self,
            "observation",
            MappingProxyType(observation),
        )

    @property
    def placement(self) -> Mapping[str, object]:
        """
        Derive placement from the sole execution fact.
        """

        return self.execution.placement

    def complete_observation(self) -> dict[str, object]:
        """
        Restore scientific observation with its one execution fact.
        """

        return {
            **dict(self.observation),
            "execution": self.execution.as_mapping(),
        }

    @classmethod
    def artifact_manifest(cls) -> dict[str, str]:
        """
        Return the one standard native-work artifact vocabulary.
        """

        return dict(cls._ARTIFACTS)

    def as_mapping(self) -> dict[str, object]:
        """
        Return the complete canonical work record.
        """

        return {
            "artifacts": self.artifact_manifest(),
            "capacity": self.capacity.as_mapping(),
            "capacity_reference": self.capacity_reference.as_mapping(),
            "construction": dict(self.construction),
            "execution": self.execution.as_mapping(),
            "lane_identity": self.lane_identity,
            "log": self.log,
            "observation": dict(self.observation),
            "session_identity": self.session_identity,
            "session_reused": self.is_session_reused,
            "work_identity": self.work_identity,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> WorkRecord:
        """
        Restore one exact record while rejecting another artifact vocabulary.
        """

        if set(value) != {
            "artifacts",
            "capacity",
            "capacity_reference",
            "construction",
            "execution",
            "lane_identity",
            "log",
            "observation",
            "session_identity",
            "session_reused",
            "work_identity",
        }:
            raise RuntimeError("work_record_fields_invalid")
        artifacts = value.get("artifacts")
        if not isinstance(artifacts, Mapping) or dict(artifacts) != (
            cls.artifact_manifest()
        ):
            raise RuntimeError("work_record_manifest_invalid")
        execution = ProjectExecution.from_mapping(_object(value, "execution"))
        capacity = CapacityObservation.from_mapping(_object(value, "capacity"))
        capacity_reference_value = value.get("capacity_reference")
        if not isinstance(capacity_reference_value, Mapping):
            raise RuntimeError("work_record_capacity_reference_invalid")
        record = cls(
            work_identity=_text(value, "work_identity"),
            session_identity=_text(value, "session_identity"),
            lane_identity=_text(value, "lane_identity"),
            is_session_reused=_require_truth(value, "session_reused"),
            construction=_object(value, "construction"),
            execution=execution,
            observation=_object(value, "observation"),
            log=_text(value, "log", is_empty_allowed=True),
            capacity=capacity,
            capacity_reference=Reference.from_mapping(capacity_reference_value),
            lease_placement=execution.placement,
        )
        if record.as_mapping() != dict(value):
            raise RuntimeError("work_record_invalid")
        return record


@dataclass(frozen=True, slots=True)
class RunDirectory:
    """
    Restricts all artifacts to one named run.
    """

    root: Path

    def for_response(self, request_identity: str) -> RunDirectory:
        """
        Isolate one sealed response and retain its deterministic recovery path.
        """

        matched = _CONTENT_IDENTITY.fullmatch(request_identity)
        if matched is None:
            raise ValueError("response_request_identity_invalid")
        # The locator stays short enough for native Windows artifact paths;
        # request.json below remains the complete identity authority.
        root = self.root / "r" / matched.group(1)[:16]
        root.mkdir(parents=True, exist_ok=True)
        _write_bytes_once(
            root / "request.json",
            encode_bytes({"request_identity": request_identity}),
            finding="response_request_identity_collision",
        )
        return RunDirectory(root)

    def record_response_capacity(
        self,
        *,
        capacity_reference: Reference,
        admitted_lanes: int,
        lumerical_gui_limit: int,
        lumerical_solve_limit: int,
        workstation_lanes: int,
    ) -> None:
        """
        Record the product-native and local limits that admitted this run.
        """

        if (
            min(
                admitted_lanes,
                lumerical_gui_limit,
                lumerical_solve_limit,
                workstation_lanes,
            )
            <= 0
        ):
            raise ValueError("run_response_capacity_invalid")
        expected = {
            "admitted_lanes": admitted_lanes,
            "capacity_reference": capacity_reference.as_mapping(),
            "native_capacity": {
                "lumerical_gui": lumerical_gui_limit,
                "lumerical_solve": lumerical_solve_limit,
            },
            "workstation_lanes": workstation_lanes,
        }
        matched = _CONTENT_IDENTITY.fullmatch(capacity_reference.content_hash)
        if matched is None:
            raise ValueError("run_capacity_reference_invalid")
        path = self.root / "capacity" / f"capacity-{matched.group(1)[:32]}.json"
        _write_bytes_once(
            path,
            encode_bytes(expected),
            finding="run_response_capacity_mismatch",
        )

    def response_capacity_record(
        self,
        capacity_reference: Reference,
    ) -> Mapping[str, Any]:
        """
        Restore one exact capacity generation used by this response.
        """

        matched = _CONTENT_IDENTITY.fullmatch(capacity_reference.content_hash)
        if matched is None:
            raise ValueError("run_capacity_reference_invalid")
        return self._read_json(
            self.root / "capacity" / f"capacity-{matched.group(1)[:32]}.json"
        )

    def candidate(self, name: str) -> Path:
        """
        Return one safe candidate directory beneath this run.
        """

        if not _SAFE_NAME.fullmatch(name):
            raise ValueError("candidate_name_invalid")
        return self.root / name

    def record_manifest(
        self,
        *,
        period_nm: int,
        order_regime: str,
        cautions: tuple[Caution, ...],
    ) -> None:
        """
        Record one run's cell physics and non-blocking limitations.
        """

        if period_nm <= 0:
            raise ValueError("run_period_invalid")
        if order_regime not in {"zeroth order", "multi order"}:
            raise ValueError("run_order_regime_invalid")
        manifest = encode_bytes(
            {
                "cautions": [caution.as_mapping() for caution in cautions],
                "order_regime": order_regime,
                "period_nm": period_nm,
            }
        )
        path = self.root / "manifest.json"
        _write_bytes_once(
            path,
            manifest,
            finding="run_manifest_mismatch",
        )

    def prepare_candidate(
        self,
        name: str,
        value: Any,
        *,
        work_identity: str | None = None,
        should_adopt_identity: bool = False,
    ) -> Path:
        """
        Open one candidate only under its exact input and work identity.
        """

        directory = self.candidate(name)
        input_path = directory / "input.json"
        identity_path = directory / "identity.json"
        expected = encode_bytes(value)
        identity = (
            None if work_identity is None else encode_bytes({"work": work_identity})
        )
        if not directory.exists():
            directory.mkdir(parents=True)
            input_path.write_bytes(expected)
            if identity is not None:
                identity_path.write_bytes(identity)
            return directory
        if not directory.is_dir():
            raise RuntimeError("candidate_artifact_not_directory")
        if not input_path.is_file():
            raise RuntimeError("candidate_artifact_identity_missing")
        if input_path.read_bytes() != expected:
            raise RuntimeError("candidate_artifact_identity_mismatch")
        if identity is not None:
            if not identity_path.is_file():
                if not should_adopt_identity:
                    raise RuntimeError("candidate_artifact_identity_mismatch")
                identity_path.write_bytes(identity)
            elif identity_path.read_bytes() != identity:
                raise RuntimeError("candidate_artifact_identity_mismatch")
        return directory

    def basis_work(self, directory: Path, basis: str) -> Path:
        """
        Locate one linear-basis work directory.
        """

        _require_within(directory, self.root)
        if basis not in {"x", "y"}:
            raise ValueError("candidate_basis_invalid")
        return directory / f"from-{basis}"

    def prepare_basis(
        self,
        directory: Path,
        basis: str,
        value: Any,
        *,
        work_identity: str,
        should_adopt_identity: bool = False,
    ) -> Path:
        """
        Open one independently receipted linear-basis work directory.
        """

        _require_within(directory, self.root)
        child = self.basis_work(directory, basis)
        input_path = child / "input.json"
        identity_path = child / "identity.json"
        expected = encode_bytes(value)
        identity = encode_bytes({"work": work_identity})
        if not child.exists():
            child.mkdir(parents=True)
            input_path.write_bytes(expected)
            identity_path.write_bytes(identity)
            return child
        if (
            not child.is_dir()
            or not input_path.is_file()
            or input_path.read_bytes() != expected
        ):
            raise RuntimeError("candidate_work_identity_mismatch")
        if not identity_path.is_file():
            if not should_adopt_identity:
                raise RuntimeError("candidate_work_identity_mismatch")
            identity_path.write_bytes(identity)
        elif identity_path.read_bytes() != identity:
            raise RuntimeError("candidate_work_identity_mismatch")
        return child

    def native_projects(self, directory: Path) -> tuple[Path, Path]:
        """
        Name the constructed and completed native projects inside one work.
        """

        _require_within(directory, self.root)
        artifacts = WorkRecord.artifact_manifest()
        return (
            directory / artifacts["constructed_project"],
            directory / artifacts["completed_project"],
        )

    def archived_ordinary_projects(
        self,
        directory: Path,
    ) -> tuple[Path, Path]:
        """
        Name the ordinary projects retained only when extension is required.
        """

        _require_within(directory, self.root)
        attempt_directory = directory / "ordinary"
        attempt_directory.mkdir(parents=True, exist_ok=True)
        return self.native_projects(attempt_directory)

    def archive_ordinary_attempt(
        self,
        directory: Path,
    ) -> None:
        """
        Move an unaccepted root attempt aside before its sole extension.
        """

        sources = self.native_projects(directory)
        targets = self.archived_ordinary_projects(directory)
        artifacts = WorkRecord.artifact_manifest()
        source_files = (
            *sources,
            directory / artifacts["execution"],
            directory / "termination.json",
        )
        target_directory = targets[0].parent
        target_files = (
            *targets,
            target_directory / artifacts["execution"],
            target_directory / "termination.json",
        )
        sidecar = native_solve_sidecar(sources[0])
        if sidecar.is_file():
            source_files = (*source_files, sidecar)
            target_files = (
                *target_files,
                native_solve_sidecar(targets[0]),
            )
        for source, target in zip(source_files, target_files, strict=True):
            _archive_native_file_once(source, target)

    def record_current_termination(
        self,
        directory: Path,
        termination: Mapping[str, object],
    ) -> None:
        """
        Preserve why the current root native solve stopped.
        """

        _write_json_once(
            self,
            directory / "termination.json",
            termination,
        )

    def record_numerical_refusal(
        self,
        directory: Path,
        refusal: Mapping[str, object],
    ) -> None:
        """
        Preserve one bounded time-ladder refusal without a false work record.
        """

        _require_within(directory, self.root)
        _write_json_once(
            self,
            directory / "numerical-refusal.json",
            refusal,
        )

    def record_work(
        self,
        directory: Path,
        record: WorkRecord,
    ) -> None:
        """
        Persist one complete standard work record idempotently.
        """

        _require_within(directory, self.root)
        identity = self._read_json(directory / "identity.json")
        if identity.get("work") != record.work_identity:
            raise RuntimeError("work_record_identity_mismatch")
        constructed, completed = self.native_projects(directory)
        if not constructed.is_file() or not completed.is_file():
            raise RuntimeError("work_record_native_project_missing")
        artifacts = WorkRecord.artifact_manifest()
        _write_json_once(
            self,
            directory / artifacts["construction"],
            record.construction,
        )
        self.record_execution(directory, record.execution)
        _write_json_once(
            self,
            directory / artifacts["observation"],
            record.observation,
        )
        _write_text_once(
            self,
            directory / artifacts["log"],
            record.log,
        )
        _write_json_once(
            self,
            directory / artifacts["record"],
            record.as_mapping(),
        )

    def find_work(self, directory: Path) -> WorkRecord | None:
        """
        Return one complete work record when its standard manifest exists.
        """

        _require_within(directory, self.root)
        record = directory / WorkRecord.artifact_manifest()["record"]
        if not record.exists():
            return None
        return self.restore_work(directory)

    def restore_work(self, directory: Path) -> WorkRecord:
        """
        Restore and verify one complete standard work record.
        """

        _require_within(directory, self.root)
        artifacts = WorkRecord.artifact_manifest()
        record_path = directory / artifacts["record"]
        record = WorkRecord.from_mapping(self._read_json(record_path))
        if record_path.read_bytes() != encode_bytes(record.as_mapping()):
            raise RuntimeError("work_record_bytes_mismatch")
        identity = self._read_json(directory / "identity.json")
        if identity.get("work") != record.work_identity:
            raise RuntimeError("work_record_identity_mismatch")
        constructed, completed = self.native_projects(directory)
        if not constructed.is_file() or not completed.is_file():
            raise RuntimeError("work_record_native_project_missing")
        expected = (
            ("construction", record.construction),
            ("execution", record.execution.as_mapping()),
            ("observation", record.observation),
        )
        for name, value in expected:
            if name == "execution":
                if self.restore_execution(directory) != record.execution:
                    raise RuntimeError("work_record_execution_mismatch")
                continue
            if self._read_json(directory / artifacts[name]) != value:
                raise RuntimeError(f"work_record_{name}_mismatch")
        if (directory / artifacts["log"]).read_text(encoding="utf-8") != record.log:
            raise RuntimeError("work_record_log_mismatch")
        return record

    def record_execution(
        self,
        directory: Path,
        execution: ProjectExecution,
    ) -> None:
        """
        Persist one completed native project execution idempotently.
        """

        _require_within(directory, self.root)
        _constructed, completed = self.native_projects(directory)
        if (
            not completed.is_file()
            or execution.project != completed.name
        ):
            raise RuntimeError("execution_completed_project_missing")
        _write_json_once(
            self,
            directory / WorkRecord.artifact_manifest()["execution"],
            execution.as_mapping(),
        )

    def restore_execution(self, directory: Path) -> ProjectExecution:
        """
        Restore one exact canonical completed-project execution.
        """

        _require_within(directory, self.root)
        _constructed, completed = self.native_projects(directory)
        if not completed.is_file():
            raise RuntimeError("execution_completed_project_missing")
        path = directory / WorkRecord.artifact_manifest()["execution"]
        execution = ProjectExecution.from_mapping(self._read_json(path))
        if execution.project != completed.name:
            raise RuntimeError("execution_completed_project_missing")
        if path.read_bytes() != encode_bytes(execution.as_mapping()):
            raise RuntimeError("execution_record_bytes_mismatch")
        return execution

    def record_summary(
        self,
        directory: Path,
        *,
        observation: Mapping[str, object],
        log: str,
    ) -> None:
        """
        Record a derived multi-work summary without inventing another manifest.
        """

        _require_within(directory, self.root)
        _write_json_once(
            self,
            directory / "summary.json",
            observation,
        )
        _write_text_once(self, directory / "summary.log", log)

    def _read_json(self, path: Path) -> Mapping[str, Any]:
        """
        Read one canonical object artifact without leaving this run.
        """

        _require_within(path, self.root)
        raw = path.read_bytes()
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("artifact_json_invalid") from error
        if not isinstance(value, dict) or encode_bytes(value) != raw:
            raise RuntimeError("artifact_json_invalid")
        return value

    def _write_json(self, path: Path, value: Any) -> None:
        """
        Write canonical JSON only inside this run.
        """

        _require_within(path, self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode_bytes(value))

    def _write_text(self, path: Path, value: str) -> None:
        """
        Write UTF-8 text only inside this run.
        """

        _require_within(path, self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")


class RunStore:
    """
    Owns the sole application-root-local tree for solver artifacts.
    """

    def __init__(self, application_root: Path, root: Path | None = None) -> None:
        """
        Confine the selected root beneath the application runs directory.
        """

        root_path = application_root.resolve()
        allowed = (root_path / "runs").resolve()
        selected = allowed if root is None else root.resolve()
        if not selected.is_relative_to(allowed):
            raise ValueError("run_root_outside_application_root")
        self._root = selected

    def open(
        self,
        *,
        aim: str,
        run_key: str,
        observed_at: datetime | None = None,
    ) -> RunDirectory:
        """
        Create one naturally named immutable run directory.
        """

        for value in (aim, run_key):
            if not _SAFE_NAME.fullmatch(value):
                raise ValueError("run_name_invalid")
        timestamp = (observed_at or datetime.now(UTC)).astimezone(UTC)
        stamp = timestamp.strftime("%Y%m%dt%H%M%Sz").lower()
        root = self._root / f"{stamp}-{aim}-{run_key}"
        root.mkdir(parents=True, exist_ok=False)
        return RunDirectory(root)


def _require_within(path: Path, root: Path) -> None:
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("artifact_path_outside_run")


def _write_json_once(
    run: RunDirectory,
    path: Path,
    value: Mapping[str, object],
) -> None:
    _require_within(path, run.root)
    _write_bytes_once(
        path,
        encode_bytes(value),
        finding=f"artifact_mismatch:{path.name}",
    )


def _write_text_once(run: RunDirectory, path: Path, value: str) -> None:
    _require_within(path, run.root)
    _write_bytes_once(
        path,
        value.encode("utf-8"),
        finding=f"artifact_mismatch:{path.name}",
    )


def _write_bytes_once(
    path: Path,
    value: bytes,
    *,
    finding: str,
) -> None:
    """
    Publish complete immutable bytes without exposing a partial target.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != value:
            raise RuntimeError(finding)
        return
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=".p",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
        if path.read_bytes() != value:
            raise RuntimeError(finding)
    finally:
        temporary.unlink(missing_ok=True)


def _archive_native_file_once(source: Path, target: Path) -> None:
    """
    Archive one unpublished root artifact without copying its native bytes.
    """

    if not source.is_file():
        raise RuntimeError("native_attempt_project_missing")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, target)
    except FileExistsError:
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            raise RuntimeError("native_attempt_archive_mismatch")
    if not target.is_file():
        raise RuntimeError("native_attempt_archive_missing")
    source.unlink()


def _object(
    value: Mapping[str, object],
    name: str,
) -> Mapping[str, object]:
    item = value.get(name)
    if not isinstance(item, Mapping):
        raise RuntimeError(f"work_record_{name}_invalid")
    return {str(key): nested for key, nested in item.items()}


def _text(
    value: Mapping[str, object],
    name: str,
    *,
    is_empty_allowed: bool = False,
) -> str:
    item = value.get(name)
    if not isinstance(item, str) or (not is_empty_allowed and not item.strip()):
        raise RuntimeError(f"work_record_{name}_invalid")
    return item


def _require_truth(value: Mapping[str, object], name: str) -> bool:
    item = value.get(name)
    if not isinstance(item, bool):
        raise RuntimeError(f"work_record_{name}_invalid")
    return item

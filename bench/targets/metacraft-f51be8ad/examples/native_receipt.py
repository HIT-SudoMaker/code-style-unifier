from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import tempfile
from types import MappingProxyType
from typing import TypedDict

from metacraft.authority import Authority, Reference
from metacraft.science._application_root import (
    authority_workspace_path,
    create_authority_in_new_application_root,
)
from metacraft.authority.session import AuthoritySession
from metacraft.canonical import encode_bytes
from metacraft.external_activity import (
    ExternalActivityClosure,
    ExternalActivityOrigin,
)
from metacraft.materials import (
    MaterialObservationRequest,
    MaterialUnavailable,
    ObservedMaterials,
    SolverMaterialLibrary,
    open_material_response,
)
from metacraft.science.periodic_response import (
    ObservedPeriodicPolarization,
    PeriodicMaterials,
    PeriodicPolarizationRequest,
    PeriodicResponseContext,
    PeriodicWork,
    RectangularCrossSection,
    periodic_request_identity,
)
from metacraft.science.metalens.reference_surface_evidence import (
    admit_reference_surfaces,
)
from metacraft.solvers.lumerical_fdtd import (
    LumericalConfig,
    LumericalPeriodicResponse,
)
from metacraft.solvers.lumerical_fdtd.project_execution import ProjectExecution
from metacraft.solvers.lumerical_fdtd.artifacts import (
    RunDirectory,
    RunStore,
    WorkRecord,
    native_solve_sidecar,
)
from metacraft.solvers.lumerical_fdtd.material_response import (
    LumericalMaterialVerifier,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    LumericalBinding,
    PeriodicResponseQualification,
    read_lumerical_environment,
)
from metacraft.solvers.recorded_periodic_response import (
    RecordedPeriodicResponse,
)


NATIVE_RECEIPT_RECORD = Path(".scratch/sonnet-deep-architecture/NATIVE-RECEIPT.json")

_RESPONSE_CAPABILITIES = (
    "periodic_transmission_response",
    "periodic_polarization_response",
    "periodic_reference_surface_response",
)
_QUALIFICATION_PURPOSES = (
    "transmission_and_reference_surface",
    "x_linear_polarization",
    "y_linear_polarization",
)
_INPUT_BASES = ("x linear", "y linear")
_OBSERVATION_SCHEMA = "metacraft.canary.periodic_polarization"
_CELL_IDENTITY = "rectangular-fin-height-0600nm-length-0220nm-width-0100nm"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CONTENT_IDENTITY = re.compile(r"^sha256:[0-9a-f]{64}$")
_CAPACITY_ARTIFACT = re.compile(r"^capacity-[0-9a-f]{32}\.json$")
_MEDIA_TYPE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/"
    r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$"
)
_WINDOWS_ABSOLUTE_FRAGMENT = re.compile(
    r"(?i)(?:[a-z]:[\\/]|\\\\[^\\/\s]+[\\/][^\\/\s]+)"
)
_POSIX_ABSOLUTE_FRAGMENT = re.compile(
    r"(?i)(?:^|[\s\"'=:(])/(?:home|users|root|tmp|var|etc|opt|mnt|srv|usr)" r"(?:/|$)"
)
_SENSITIVE_TEXT = re.compile(
    r"(?i)\b(?:"
    r"api[_ -]?key|command(?:[_ -]?line)?|credential(?:s)?|environment|"
    r"license(?:[_ -]?server)?|password|raw[_ -]?(?:product[_ -]?)?log|"
    r"secret|token"
    r")\b"
)
_ACTIVITY_COUNT_FIELDS = (
    "acquired_authority_work_count",
    "settled_authority_work_count",
    "started_external_execution_count",
    "settled_external_execution_count",
    "opened_product_session_count",
    "closed_product_session_count",
    "opened_local_placement_count",
    "closed_local_placement_count",
)
_AUTHORITY_STORE_FILES = frozenset(
    {
        "authority/workspace.marker",
        "authority/workspace.sqlite3",
        "authority/workspace.writer.lock",
    }
)
_WORK_ARTIFACTS = MappingProxyType(WorkRecord.artifact_manifest())
_NATIVE_SOLVE_SIDECAR = native_solve_sidecar(
    Path(_WORK_ARTIFACTS["constructed_project"])
).name
_QUALIFICATION_ARTIFACT_FILES = frozenset(
    {
        _WORK_ARTIFACTS["completed_project"],
        _WORK_ARTIFACTS["constructed_project"],
        _WORK_ARTIFACTS["execution"],
        _NATIVE_SOLVE_SIDECAR,
    }
)
_CANDIDATE_WORK_FILES = frozenset(
    {
        "input.json",
        "identity.json",
        *_WORK_ARTIFACTS.values(),
        _NATIVE_SOLVE_SIDECAR,
    }
)
_INVENTORY_CATEGORIES = frozenset(
    {
        "authority_store",
        "qualification_run",
        "candidate_response",
        "candidate_x_linear_work",
        "candidate_y_linear_work",
    }
)
_FORBIDDEN_RECORD_KEYS = frozenset(
    {
        "aperture",
        "cell_library",
        "command",
        "command_line",
        "credential",
        "environment",
        "field_propagation",
        "focus",
        "license",
        "license_server",
        "metalens_benchmark_case",
        "project_comparison",
        "raw_product_log",
        "scientific_result",
        "token",
    }
)


class _ActivityRecord(TypedDict):
    origin: str
    acquired_authority_work_count: int
    settled_authority_work_count: int
    started_external_execution_count: int
    settled_external_execution_count: int
    opened_product_session_count: int
    closed_product_session_count: int
    opened_local_placement_count: int
    closed_local_placement_count: int


class NativeReceiptQualificationIncomplete(RuntimeError):
    """
    Stop the canary with only redacted, closed qualification evidence.
    """

    __slots__ = (
        "_open_permit_count",
        "_qualification_activity",
        "_response_qualifications",
    )

    def __init__(
        self,
        *,
        response_qualifications: tuple[PeriodicResponseQualification, ...],
        qualification_activity: ExternalActivityClosure,
        open_permit_count: int,
    ) -> None:
        self._response_qualifications = response_qualifications
        self._qualification_activity = qualification_activity
        self._open_permit_count = open_permit_count
        super().__init__("native_receipt_capabilities_incomplete")

    @property
    def response_qualifications(
        self,
    ) -> tuple[PeriodicResponseQualification, ...]:
        """
        Return the ordered redacted result for every response kind.
        """

        return self._response_qualifications

    @property
    def qualification_activity(self) -> ExternalActivityClosure:
        """
        Return the immutable closed activity from product qualification.
        """

        return self._qualification_activity

    @property
    def open_permit_count(self) -> int:
        """
        Return the exact public Authority open-permit count at the stop.
        """

        return self._open_permit_count


@dataclass(frozen=True, slots=True)
class NativeReceiptClosure:
    """
    Preserve one redacted, bounded native-receipt verification.
    """

    _record: Mapping[str, object]

    def __post_init__(self) -> None:
        canonical = _canonical_mapping(self._record)
        _validate_closure_record(canonical)
        object.__setattr__(
            self,
            "_record",
            MappingProxyType(canonical),
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> NativeReceiptClosure:
        return cls(value)

    def as_mapping(self) -> dict[str, object]:
        """
        Return a detached canonical mapping suitable for the tracked record.
        """

        return _canonical_mapping(self._record)

    def verify_application_root(self, application_root: Path) -> None:
        """
        Match the exhaustive classified application_root after recorded recovery.
        """

        application_root_root = application_root.resolve()
        if not application_root_root.is_dir():
            raise ValueError("native_receipt_application_root_missing")
        observed = _collect_application_root_inventory(
            application_root_root,
            qualification_projects=_qualification_projects_from_record(self._record),
            candidate_executions=_candidate_executions_from_record(self._record),
            candidate_directory=_relative_path(
                _mapping(
                    self._record.get("candidate"),
                    "native_receipt_candidate_invalid",
                ).get("directory"),
                finding="native_receipt_path_not_redacted",
            ),
        )
        expected = tuple(
            _mapping(entry, "native_receipt_inventory_invalid")
            for entry in _sequence(
                self._record.get("recovery_inventory"),
                "native_receipt_inventory_invalid",
            )
        )
        if tuple(observed) != expected:
            raise ValueError("native_receipt_inventory_mismatch")


def native_receipt_application_root_path(
    environ: Mapping[str, str],
) -> Path:
    """
    Validate the opt-in and return the explicit absolute application_root path.

    Absence is intentionally not checked here. ``run_native_receipt`` claims
    the path through the application-owned create-only composition operation.
    """

    if environ.get("METACRAFT_RUN_LUMERICAL_CANARY") != "1":
        raise RuntimeError("lumerical_canary_disabled")
    raw_application_root = environ.get("METACRAFT_CANARY_APPLICATION_ROOT")
    if raw_application_root is None or not raw_application_root.strip():
        raise ValueError("native_receipt_application_root_required")
    selected = Path(raw_application_root).expanduser()
    if not selected.is_absolute():
        raise ValueError("native_receipt_application_root_must_be_absolute")
    return selected.resolve()


def run_native_receipt(
    *,
    repository_root: Path,
    application_root: Path,
    environ: Mapping[str, str],
) -> NativeReceiptClosure:
    """
    Execute exactly three qualification and two candidate native solves.
    """

    selected_application_root = native_receipt_application_root_path(environ)
    if application_root.resolve() != selected_application_root:
        raise ValueError("native_receipt_application_root_mismatch")
    authority = create_authority_in_new_application_root(selected_application_root)
    root = repository_root.resolve()
    environment_path = root / ".env.lumerical"
    material_library_path = root / "materials" / "lumerical.toml"
    if not environment_path.is_file():
        raise FileNotFoundError("lumerical_environment_missing")
    if not material_library_path.is_file():
        raise FileNotFoundError("solver_material_library_missing")

    authority_session = AuthoritySession(authority)
    run = RunStore(selected_application_root).open(
        aim="metalens",
        run_key="native-receipt",
    )
    environment = read_lumerical_environment(
        environment_path,
        inherited=environ,
    )
    config = replace(
        LumericalConfig.from_environ(environment),
        runs_directory=selected_application_root / "runs" / "qualification",
    )
    if not config.has_required_settings():
        raise RuntimeError("lumerical_configuration_incomplete")

    response = LumericalPeriodicResponse.open(
        authority=authority,
        config=config,
        run=run,
    )
    context = response.context
    _require_complete_qualification(
        response=response,
        context=context,
        authority=authority,
    )

    observed_materials = _observe_canary_materials(
        root,
        session=authority_session,
        response=response,
        config=config,
    )
    request = _candidate_request(
        observed_materials,
        binding_reference=context.binding_reference,
        capacity_scope=context.capacity_scope,
    )
    observed = response.observe(request)
    if not isinstance(observed, ObservedPeriodicPolarization):
        reason = getattr(observed, "reason", "unavailable")
        raise RuntimeError(f"native_receipt_candidate_unavailable:{reason}")
    if len(observed.items) != 2:
        raise RuntimeError("native_receipt_candidate_observation_invalid")

    formation = _form_candidate_reference_surfaces(
        request,
        observed,
        authority_session=authority_session,
    )

    response_run = run.for_response(request.request_identity)
    candidate_directory = response_run.candidate(_CELL_IDENTITY)
    work_records = tuple(
        response_run.restore_work(response_run.basis_work(candidate_directory, basis))
        for basis in ("x", "y")
    )
    capacity_references = {record.capacity_reference for record in work_records}
    if len(capacity_references) != 1:
        raise RuntimeError("native_receipt_capacity_ambiguous")
    capacity_reference = next(iter(capacity_references))

    qualification_projects = _qualification_projects(
        config.runs_directory,
        application_root=selected_application_root,
    )
    candidate_executions = _candidate_executions(
        observed,
        work_records=work_records,
        response_run=response_run,
        candidate_directory=candidate_directory,
        application_root=selected_application_root,
    )
    view_after_native_work = authority.view()
    open_permits = tuple(
        permit for permit in view_after_native_work.permits if permit.state == "open"
    )
    if open_permits:
        raise RuntimeError("native_receipt_permit_open")

    qualification_activity = _activity_mapping(context.qualification_closure)
    materials_activity = _activity_mapping(observed_materials.activity)
    candidate_activity = _activity_mapping(observed.closure.observation)
    native_phase_solve_counts = (
        qualification_activity["started_external_execution_count"],
        materials_activity["started_external_execution_count"],
        candidate_activity["started_external_execution_count"],
    )
    if native_phase_solve_counts != (3, 0, 2):
        raise RuntimeError("native_receipt_activity_invalid")
    native_solve_count = sum(native_phase_solve_counts)

    native_inventory = _collect_application_root_inventory(
        selected_application_root,
        qualification_projects=qualification_projects,
        candidate_executions=candidate_executions,
        candidate_directory=PurePosixPath(
            _application_root_relative(candidate_directory, selected_application_root)
        ),
    )
    recovery = _recover_candidate(
        application_root=selected_application_root,
        request=request,
        context=response.context,
        expected=observed,
    )
    recovery_inventory = _collect_application_root_inventory(
        selected_application_root,
        qualification_projects=qualification_projects,
        candidate_executions=candidate_executions,
        candidate_directory=PurePosixPath(
            _application_root_relative(candidate_directory, selected_application_root)
        ),
    )
    if native_inventory != recovery_inventory:
        raise RuntimeError("native_receipt_recovery_changed_application_root")
    if authority.view() != view_after_native_work:
        raise RuntimeError("native_receipt_recovery_changed_authority")

    closure = NativeReceiptClosure.from_mapping(
        {
            "schema": "metacraft.native_receipt",
            "verification": "verified",
            "product": {
                "binding_reference": (context.binding_reference.as_mapping()),
                "capacity_reference": capacity_reference.as_mapping(),
                "material_observation_reference": (
                    observed_materials.sample_reference.as_mapping()
                ),
                "response_capabilities": list(_RESPONSE_CAPABILITIES),
            },
            "qualification": {
                "activity": qualification_activity,
                "completed_projects": list(qualification_projects),
            },
            "materials": {
                "activity": materials_activity,
            },
            "candidate": {
                "activity": candidate_activity,
                "directory": _application_root_relative(
                    candidate_directory,
                    selected_application_root,
                ),
                "height_nm": 600,
                "short_side_nm": 100,
                "long_side_nm": 220,
                "executions": list(candidate_executions),
            },
            "formation": formation,
            "recovery": recovery,
            "native_inventory": list(native_inventory),
            "recovery_inventory": list(recovery_inventory),
            "solve_count": native_solve_count,
        }
    )
    closure.verify_application_root(selected_application_root)
    return closure


def _require_complete_qualification(
    *,
    response: LumericalPeriodicResponse,
    context: PeriodicResponseContext,
    authority: Authority,
) -> None:
    """
    Stop before materials unless binding, context, activity, and permits agree.
    """

    binding = LumericalBinding.from_mapping(response.product_binding)
    response_qualifications = binding.response_qualifications
    qualified_response_kinds = tuple(
        result.response_kind
        for result in response_qualifications
        if result.is_qualified
    )
    context_response_kinds = tuple(
        response_kind.value for response_kind in context.response_kinds
    )
    if context_response_kinds != qualified_response_kinds:
        raise ValueError("native_receipt_qualification_evidence_conflict")
    qualification_activity = _materialize_qualification_activity(
        context.qualification_closure
    )
    open_permit_count = sum(
        permit.state == "open" for permit in authority.view().permits
    )
    if qualified_response_kinds != _RESPONSE_CAPABILITIES:
        raise NativeReceiptQualificationIncomplete(
            response_qualifications=response_qualifications,
            qualification_activity=qualification_activity,
            open_permit_count=open_permit_count,
        )
    if open_permit_count != 0:
        raise RuntimeError("native_receipt_qualification_permit_open")


def _materialize_qualification_activity(
    activity: ExternalActivityClosure,
) -> ExternalActivityClosure:
    """
    Copy and validate the exact closed three-solve qualification activity.
    """

    if type(activity) is not ExternalActivityClosure:
        raise TypeError("native_receipt_qualification_activity_invalid")
    materialized = ExternalActivityClosure(
        origin=activity.origin,
        acquired_authority_work_count=activity.acquired_authority_work_count,
        settled_authority_work_count=activity.settled_authority_work_count,
        started_external_execution_count=(
            activity.started_external_execution_count
        ),
        settled_external_execution_count=(
            activity.settled_external_execution_count
        ),
        opened_product_session_count=activity.opened_product_session_count,
        closed_product_session_count=activity.closed_product_session_count,
        opened_local_placement_count=activity.opened_local_placement_count,
        closed_local_placement_count=activity.closed_local_placement_count,
    )
    if (
        materialized.origin is not ExternalActivityOrigin.NATIVE
        or materialized.acquired_authority_work_count != 0
        or materialized.settled_authority_work_count != 0
        or materialized.started_external_execution_count != 3
        or materialized.settled_external_execution_count != 3
    ):
        raise ValueError("native_receipt_qualification_activity_invalid")
    return materialized


def write_native_receipt_record(
    closure: NativeReceiptClosure,
    *,
    application_root: Path,
    destination: Path,
) -> None:
    """
    Atomically write one canonical redacted record outside the native application_root.
    """

    validated_snapshot = NativeReceiptClosure.from_mapping(closure.as_mapping())
    validated_snapshot.verify_application_root(application_root)
    application_root_root = application_root.resolve()
    destination_path = destination.resolve()
    if destination_path.is_relative_to(application_root_root):
        raise ValueError("native_receipt_record_inside_application_root")
    encoded = encode_bytes(validated_snapshot.as_mapping()) + b"\n"
    if str(application_root_root).encode("utf-8") in encoded:
        raise ValueError("native_receipt_record_not_redacted")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination_path.parent,
            prefix=f".{destination_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _observe_canary_materials(
    repository_root: Path,
    *,
    session: AuthoritySession,
    response: LumericalPeriodicResponse,
    config: LumericalConfig,
) -> ObservedMaterials:
    library = SolverMaterialLibrary.decode_bytes(
        (repository_root / "materials" / "lumerical.toml").read_bytes()
    )
    verifier = LumericalMaterialVerifier(
        session=session,
        config=config,
        binding_reference=response.context.binding_reference,
    )
    materials = open_material_response(
        session=session,
        library=library,
        binding_reference=response.context.binding_reference,
        capacity_scope=response.context.capacity_scope,
        verify_materials=verifier.verify,
    ).observe(
        MaterialObservationRequest(
            ("silicon nitride", "silica"),
            400,
        )
    )
    if isinstance(materials, MaterialUnavailable):
        raise RuntimeError(
            "native_receipt_material_unavailable:"
            f"{materials.reason.value}:{materials.family}"
        )
    return materials


def _candidate_request(
    materials: ObservedMaterials,
    *,
    binding_reference: Reference,
    capacity_scope: str,
) -> PeriodicPolarizationRequest:
    by_family = {material.family: material for material in materials.materials}
    if set(by_family) != {"silica", "silicon nitride"}:
        raise RuntimeError("native_receipt_material_observation_invalid")
    sources = tuple(
        dict.fromkeys(
            (
                materials.sample_reference,
                materials.product_sample_reference,
                *(selection.reference for selection in materials.selections),
            )
        )
    )
    geometry = RectangularCrossSection(100, 220)
    material_pair = PeriodicMaterials(
        atom_native_identity=(by_family["silicon nitride"].native_name),
        atom_refractive_index=(
            by_family["silicon nitride"].refractive_index
        ),
        atom_source_reference=materials.sample_reference,
        substrate_native_identity=by_family["silica"].native_name,
        substrate_refractive_index=by_family["silica"].refractive_index,
        substrate_source_reference=materials.sample_reference,
    )
    identities = tuple(
        _candidate_work_identity(
            basis=basis,
            geometry=geometry,
            materials=material_pair,
            sources=sources,
            binding_reference=binding_reference,
            capacity_scope=capacity_scope,
        )
        for basis in _INPUT_BASES
    )
    work = tuple(
        PeriodicWork(
            cell_identity=_CELL_IDENTITY,
            work_identity=identity,
            observation_schema=_OBSERVATION_SCHEMA,
            wavelength_nm=400,
            period_nm=400,
            height_nm=600,
            geometry=geometry,
            materials=material_pair,
            source_references=sources,
            binding_reference=binding_reference,
            capacity_scope=capacity_scope,
            input_basis=basis,
            output_basis="cartesian",
            order_regime="multi order",
        )
        for basis, identity in zip(
            _INPUT_BASES,
            identities,
            strict=True,
        )
    )
    return PeriodicPolarizationRequest(
        periodic_request_identity("polarization", identities),
        work,
    )


def _candidate_work_identity(
    *,
    basis: str,
    geometry: RectangularCrossSection,
    materials: PeriodicMaterials,
    sources: tuple[Reference, ...],
    binding_reference: Reference,
    capacity_scope: str,
) -> str:
    preimage = encode_bytes(
        {
            "canary": "native receipt",
            "candidate": {
                "geometry": {
                    "long_side_nm": geometry.long_side_nm,
                    "short_side_nm": geometry.short_side_nm,
                },
                "height_nm": 600,
                "identity": _CELL_IDENTITY,
                "period_nm": 400,
                "wavelength_nm": 400,
            },
            "input_basis": basis,
            "materials": {
                "atom_native_identity": (materials.atom_native_identity),
                "atom_source_reference": (materials.atom_source_reference.as_mapping()),
                "substrate_native_identity": (materials.substrate_native_identity),
                "substrate_source_reference": (
                    materials.substrate_source_reference.as_mapping()
                ),
            },
            "product": {
                "binding_reference": binding_reference.as_mapping(),
                "capacity_scope": capacity_scope,
            },
            "source_references": [reference.as_mapping() for reference in sources],
        }
    )
    return "sha256:" + hashlib.sha256(preimage).hexdigest()


def _qualification_projects(
    qualification_root: Path,
    *,
    application_root: Path,
) -> tuple[dict[str, object], ...]:
    directories = tuple(sorted(qualification_root.glob("lumerical-qualification-*")))
    if len(directories) != 1:
        raise RuntimeError("native_receipt_qualification_directory_invalid")
    root = directories[0]
    locations = (
        (
            "transmission_and_reference_surface",
            root / "transmission",
        ),
        (
            "x_linear_polarization",
            root / "polarization" / "x-input",
        ),
        (
            "y_linear_polarization",
            root / "polarization" / "y-input",
        ),
    )
    projects = []
    for purpose, directory in locations:
        files = tuple(sorted(path for path in directory.iterdir() if path.is_file()))
        expected_files = {
            directory / filename
            for filename in _QUALIFICATION_ARTIFACT_FILES
        }
        if set(files) != expected_files:
            raise RuntimeError("native_receipt_qualification_artifacts_incomplete")
        execution = ProjectExecution.from_mapping(
            _canonical_file_mapping(
                directory / _WORK_ARTIFACTS["execution"]
            )
        )
        if (
            not execution.is_native
            or execution.return_code != 0
            or execution.source != "lumerical_fdtd_native_session"
        ):
            raise RuntimeError("native_receipt_qualification_not_native")
        projects.append(
            {
                "purpose": purpose,
                "artifacts": _artifact_entries(
                    files,
                    application_root=application_root,
                ),
            }
        )
    return tuple(projects)


def _candidate_executions(
    observed: ObservedPeriodicPolarization,
    *,
    work_records: tuple[WorkRecord, ...],
    response_run: RunDirectory,
    candidate_directory: Path,
    application_root: Path,
) -> tuple[dict[str, object], ...]:
    if tuple(item.work_identity for item in observed.items) != tuple(
        record.work_identity for record in work_records
    ):
        raise RuntimeError("native_receipt_work_identity_mismatch")
    executions = []
    for basis, admitted, record in zip(
        _INPUT_BASES,
        observed.items,
        work_records,
        strict=True,
    ):
        axis = basis[0]
        work_directory = response_run.basis_work(
            candidate_directory,
            axis,
        )
        files = tuple(
            sorted(path for path in work_directory.iterdir() if path.is_file())
        )
        if (
            {path.name for path in files} != _CANDIDATE_WORK_FILES
            or not record.execution.is_native
            or record.execution.return_code != 0
            or record.execution.source != "lumerical_fdtd_native_session"
        ):
            raise RuntimeError("native_receipt_candidate_artifacts_incomplete")
        executions.append(
            {
                "input_basis": basis,
                "work_identity": admitted.work_identity,
                "observation_reference": (admitted.body_reference.as_mapping()),
                "receipt_reference": (admitted.receipt_reference.as_mapping()),
                "execution_origin": admitted.execution_origin.value,
                "artifacts": _artifact_entries(
                    files,
                    application_root=application_root,
                ),
            }
        )
    return tuple(executions)


def _form_candidate_reference_surfaces(
    request: PeriodicPolarizationRequest,
    observed: ObservedPeriodicPolarization,
    *,
    authority_session: AuthoritySession,
) -> dict[str, object]:
    """Form and admit both candidate bases before the recovery baseline."""

    admitted = admit_reference_surfaces(
        request,
        observed,
        cell_identity=_CELL_IDENTITY,
        admit_object=authority_session.admit_object,
        admit_document=authority_session.admit_document,
    )
    if len(admitted) != 2:
        raise RuntimeError("native_receipt_formation_invalid")
    fields = tuple(item.response.field for item in admitted)
    common_surface = fields[0].surface
    raw_references = tuple(item.body_reference for item in observed.items)
    qualification_references = tuple(
        field.source_references[1]
        for field in fields
        if len(field.source_references) == 2
    )
    if (
        tuple(
            item.response.requested_input_basis.value for item in admitted
        )
        != _INPUT_BASES
        or common_surface.shape != (24, 24)
        or any(field.surface != common_surface for field in fields)
        or len(qualification_references) != 2
        or len(set(qualification_references)) != 1
        or any(
            field.source_references
            != (raw_reference, qualification_references[0])
            for field, raw_reference in zip(
                fields,
                raw_references,
                strict=True,
            )
        )
    ):
        raise RuntimeError("native_receipt_formation_invalid")
    qualification_reference = qualification_references[0]
    return {
        "algorithm": "periodic_rectilinear_bilinear_v1",
        "qualification_reference": qualification_reference.as_mapping(),
        "surface": {
            "position_m": format(common_surface.position_m, ".17g"),
            "shape": list(common_surface.shape),
            "spacing_m": format(common_surface.spacing_m, ".17g"),
        },
        "surfaces": [
            {
                "formed_surface_reference": item.reference.as_mapping(),
                "input_basis": item.response.requested_input_basis.value,
                "raw_observation_reference": raw_reference.as_mapping(),
                "source_references": [
                    source.as_mapping()
                    for source in item.response.field.source_references
                ],
            }
            for item, raw_reference in zip(
                admitted,
                raw_references,
                strict=True,
            )
        ],
    }


def _recover_candidate(
    *,
    application_root: Path,
    request: PeriodicPolarizationRequest,
    context: PeriodicResponseContext,
    expected: ObservedPeriodicPolarization,
) -> dict[str, object]:
    reopened_authority = Authority(authority_workspace_path(application_root))
    before = reopened_authority.view()
    restored = RecordedPeriodicResponse(
        AuthoritySession(reopened_authority),
        context=context,
    ).observe(request)
    after = reopened_authority.view()
    if before != after:
        raise RuntimeError("native_receipt_recovery_not_read_only")
    if not isinstance(restored, ObservedPeriodicPolarization):
        raise RuntimeError("native_receipt_recovery_missing")
    if restored.items != expected.items:
        raise RuntimeError("native_receipt_recovery_mismatch")
    return {
        "activity": _activity_mapping(restored.closure.observation),
        "work_identities": [item.work_identity for item in restored.items],
        "observation_references": [
            item.body_reference.as_mapping() for item in restored.items
        ],
        "receipt_references": [
            item.receipt_reference.as_mapping() for item in restored.items
        ],
    }


def _validate_closure_record(record: Mapping[str, object]) -> None:
    _validate_redaction(record)
    if set(record) != {
        "candidate",
        "formation",
        "materials",
        "native_inventory",
        "product",
        "qualification",
        "recovery",
        "recovery_inventory",
        "schema",
        "solve_count",
        "verification",
    }:
        raise ValueError("native_receipt_record_not_redacted")
    if (
        record.get("schema") != "metacraft.native_receipt"
        or record.get("verification") != "verified"
    ):
        raise ValueError("native_receipt_record_invalid")

    product = _mapping(record.get("product"), "native_receipt_product_invalid")
    if set(product) != {
        "binding_reference",
        "capacity_reference",
        "material_observation_reference",
        "response_capabilities",
    }:
        raise ValueError("native_receipt_product_invalid")
    for name in (
        "binding_reference",
        "capacity_reference",
        "material_observation_reference",
    ):
        _reference(product.get(name), "native_receipt_product_invalid")
    if (
        tuple(
            _sequence(
                product.get("response_capabilities"),
                "native_receipt_product_invalid",
            )
        )
        != _RESPONSE_CAPABILITIES
    ):
        raise ValueError("native_receipt_product_invalid")

    qualification = _mapping(
        record.get("qualification"),
        "native_receipt_qualification_invalid",
    )
    if set(qualification) != {"activity", "completed_projects"}:
        raise ValueError("native_receipt_qualification_invalid")
    qualification_activity = _validate_activity(
        qualification.get("activity"),
        finding="native_receipt_qualification_invalid",
        origin=ExternalActivityOrigin.NATIVE,
        required_counts={
            "acquired_authority_work_count": 0,
            "settled_authority_work_count": 0,
            "started_external_execution_count": 3,
            "settled_external_execution_count": 3,
        },
    )
    projects = _sequence(
        qualification.get("completed_projects"),
        "native_receipt_qualification_invalid",
    )
    if (
        len(projects) != 3
        or tuple(
            _mapping(
                project,
                "native_receipt_qualification_invalid",
            ).get("purpose")
            for project in projects
        )
        != _QUALIFICATION_PURPOSES
    ):
        raise ValueError("native_receipt_qualification_invalid")
    for project in projects:
        values = _mapping(
            project,
            "native_receipt_qualification_invalid",
        )
        if set(values) != {"artifacts", "purpose"}:
            raise ValueError("native_receipt_qualification_invalid")
        _validate_artifact_collection(values.get("artifacts"))

    materials = _mapping(
        record.get("materials"),
        "native_receipt_materials_invalid",
    )
    if set(materials) != {"activity"}:
        raise ValueError("native_receipt_materials_invalid")
    materials_activity = _validate_activity(
        materials.get("activity"),
        finding="native_receipt_materials_invalid",
        origin=ExternalActivityOrigin.NATIVE,
        required_counts={
            "acquired_authority_work_count": 0,
            "settled_authority_work_count": 0,
            "started_external_execution_count": 0,
            "settled_external_execution_count": 0,
            "opened_product_session_count": 1,
            "closed_product_session_count": 1,
            "opened_local_placement_count": 0,
            "closed_local_placement_count": 0,
        },
    )

    candidate = _mapping(
        record.get("candidate"),
        "native_receipt_candidate_invalid",
    )
    if (
        set(candidate)
        != {
            "directory",
            "executions",
            "height_nm",
            "long_side_nm",
            "short_side_nm",
            "activity",
        }
        or candidate.get("height_nm") != 600
        or candidate.get("short_side_nm") != 100
        or candidate.get("long_side_nm") != 220
    ):
        raise ValueError("native_receipt_candidate_invalid")

    candidate_activity = _validate_activity(
        candidate.get("activity"),
        finding="native_receipt_candidate_invalid",
        origin=ExternalActivityOrigin.NATIVE,
        required_counts={
            "acquired_authority_work_count": 2,
            "settled_authority_work_count": 2,
            "started_external_execution_count": 2,
            "settled_external_execution_count": 2,
        },
    )
    _relative_path(
        candidate.get("directory"),
        finding="native_receipt_path_not_redacted",
    )
    executions = _sequence(
        candidate.get("executions"),
        "native_receipt_candidate_invalid",
    )
    if len(executions) != 2:
        raise ValueError("native_receipt_candidate_invalid")
    work_identities = []
    observation_references = []
    receipt_references = []
    for expected_basis, execution in zip(
        _INPUT_BASES,
        executions,
        strict=True,
    ):
        values = _mapping(
            execution,
            "native_receipt_candidate_invalid",
        )
        if (
            set(values)
            != {
                "artifacts",
                "execution_origin",
                "input_basis",
                "observation_reference",
                "receipt_reference",
                "work_identity",
            }
            or values.get("input_basis") != expected_basis
            or values.get("execution_origin") != "native"
            or not isinstance(values.get("work_identity"), str)
            or _CONTENT_IDENTITY.fullmatch(str(values.get("work_identity"))) is None
        ):
            raise ValueError("native_receipt_candidate_invalid")
        work_identities.append(values["work_identity"])
        observation_references.append(
            _reference(
                values.get("observation_reference"),
                "native_receipt_candidate_invalid",
            ).as_mapping()
        )
        receipt_references.append(
            _reference(
                values.get("receipt_reference"),
                "native_receipt_candidate_invalid",
            ).as_mapping()
        )
        _validate_artifact_collection(values.get("artifacts"))
    if (
        len(set(work_identities)) != 2
        or len({encode_bytes(reference) for reference in observation_references}) != 2
        or len({encode_bytes(reference) for reference in receipt_references}) != 2
    ):
        raise ValueError("native_receipt_candidate_invalid")

    formation = _mapping(
        record.get("formation"),
        "native_receipt_formation_invalid",
    )
    if set(formation) != {
        "algorithm",
        "qualification_reference",
        "surface",
        "surfaces",
    } or formation.get("algorithm") != "periodic_rectilinear_bilinear_v1":
        raise ValueError("native_receipt_formation_invalid")
    qualification_reference = _reference(
        formation.get("qualification_reference"),
        "native_receipt_formation_invalid",
    ).as_mapping()
    surface = _mapping(
        formation.get("surface"),
        "native_receipt_formation_invalid",
    )
    if (
        set(surface) != {"position_m", "shape", "spacing_m"}
        or surface.get("shape") != [24, 24]
        or not isinstance(surface.get("position_m"), str)
        or not isinstance(surface.get("spacing_m"), str)
    ):
        raise ValueError("native_receipt_formation_invalid")
    try:
        position_m = float(str(surface["position_m"]))
        spacing_m = float(str(surface["spacing_m"]))
    except (TypeError, ValueError) as error:
        raise ValueError("native_receipt_formation_invalid") from error
    if (
        not math.isfinite(position_m)
        or not math.isfinite(spacing_m)
        or spacing_m <= 0
        or not math.isclose(24 * spacing_m, 400e-9, rel_tol=0, abs_tol=1e-15)
    ):
        raise ValueError("native_receipt_formation_invalid")
    formed = _sequence(
        formation.get("surfaces"),
        "native_receipt_formation_invalid",
    )
    if len(formed) != 2:
        raise ValueError("native_receipt_formation_invalid")
    formed_references = []
    for expected_basis, raw_reference, value in zip(
        _INPUT_BASES,
        observation_references,
        formed,
        strict=True,
    ):
        item = _mapping(value, "native_receipt_formation_invalid")
        if set(item) != {
            "formed_surface_reference",
            "input_basis",
            "raw_observation_reference",
            "source_references",
        } or item.get("input_basis") != expected_basis:
            raise ValueError("native_receipt_formation_invalid")
        observed_raw = _reference(
            item.get("raw_observation_reference"),
            "native_receipt_formation_invalid",
        ).as_mapping()
        formed_reference = _reference(
            item.get("formed_surface_reference"),
            "native_receipt_formation_invalid",
        ).as_mapping()
        sources = tuple(
            _reference(source, "native_receipt_formation_invalid").as_mapping()
            for source in _sequence(
                item.get("source_references"),
                "native_receipt_formation_invalid",
            )
        )
        if (
            observed_raw != raw_reference
            or sources != (raw_reference, qualification_reference)
        ):
            raise ValueError("native_receipt_formation_invalid")
        formed_references.append(formed_reference)
    if (
        len({encode_bytes(reference) for reference in formed_references}) != 2
        or any(
            reference == qualification_reference
            for reference in (*observation_references, *formed_references)
        )
    ):
        raise ValueError("native_receipt_formation_invalid")

    recovery = _mapping(
        record.get("recovery"),
        "native_receipt_recovery_invalid",
    )
    if (
        set(recovery)
        != {
            "activity",
            "observation_references",
            "receipt_references",
            "work_identities",
        }
        or _sequence(
            recovery.get("work_identities"),
            "native_receipt_recovery_invalid",
        )
        != tuple(work_identities)
        or tuple(
            _reference(
                value,
                "native_receipt_recovery_invalid",
            ).as_mapping()
            for value in _sequence(
                recovery.get("observation_references"),
                "native_receipt_recovery_invalid",
            )
        )
        != tuple(observation_references)
        or tuple(
            _reference(
                value,
                "native_receipt_recovery_invalid",
            ).as_mapping()
            for value in _sequence(
                recovery.get("receipt_references"),
                "native_receipt_recovery_invalid",
            )
        )
        != tuple(receipt_references)
    ):
        raise ValueError("native_receipt_recovery_invalid")
    _validate_activity(
        recovery.get("activity"),
        finding="native_receipt_recovery_invalid",
        origin=ExternalActivityOrigin.RECORDED,
        required_counts={name: 0 for name in _ACTIVITY_COUNT_FIELDS},
    )

    native_inventory = _validate_inventory_collection(record.get("native_inventory"))
    recovery_inventory = _validate_inventory_collection(
        record.get("recovery_inventory")
    )
    if native_inventory != recovery_inventory:
        raise ValueError("native_receipt_recovery_changed_application_root")
    _validate_inventory_coverage(
        native_inventory,
        qualification_projects=tuple(
            _mapping(project, "native_receipt_qualification_invalid")
            for project in projects
        ),
        candidate_executions=tuple(
            _mapping(execution, "native_receipt_candidate_invalid")
            for execution in executions
        ),
        candidate_directory=_relative_path(
            candidate.get("directory"),
            finding="native_receipt_path_not_redacted",
        ),
    )

    native_solve_count = sum(
        activity.started_external_execution_count
        for activity in (
            qualification_activity,
            materials_activity,
            candidate_activity,
        )
    )
    if record.get("solve_count") != native_solve_count or (
        qualification_activity.started_external_execution_count,
        materials_activity.started_external_execution_count,
        candidate_activity.started_external_execution_count,
    ) != (3, 0, 2):
        raise ValueError("native_receipt_solve_count_invalid")


def _validate_activity(
    value: object,
    *,
    finding: str,
    origin: ExternalActivityOrigin,
    required_counts: Mapping[str, int],
) -> ExternalActivityClosure:
    values = _mapping(value, finding)
    if set(values) != {"origin", *_ACTIVITY_COUNT_FIELDS}:
        raise ValueError(finding)
    try:
        closure = ExternalActivityClosure(
            origin=ExternalActivityOrigin(str(values.get("origin"))),
            acquired_authority_work_count=_activity_count(
                values, "acquired_authority_work_count", finding
            ),
            settled_authority_work_count=_activity_count(
                values, "settled_authority_work_count", finding
            ),
            started_external_execution_count=_activity_count(
                values, "started_external_execution_count", finding
            ),
            settled_external_execution_count=_activity_count(
                values, "settled_external_execution_count", finding
            ),
            opened_product_session_count=_activity_count(
                values, "opened_product_session_count", finding
            ),
            closed_product_session_count=_activity_count(
                values, "closed_product_session_count", finding
            ),
            opened_local_placement_count=_activity_count(
                values, "opened_local_placement_count", finding
            ),
            closed_local_placement_count=_activity_count(
                values, "closed_local_placement_count", finding
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(finding) from error
    if closure.origin is not origin or any(
        getattr(closure, name) != count for name, count in required_counts.items()
    ):
        raise ValueError(finding)
    return closure


def _activity_count(
    values: Mapping[str, object],
    name: str,
    finding: str,
) -> int:
    value = values.get(name)
    if type(value) is not int:
        raise ValueError(finding)
    return value


def _activity_mapping(
    closure: ExternalActivityClosure,
) -> _ActivityRecord:
    return {
        "origin": closure.origin.value,
        "acquired_authority_work_count": (closure.acquired_authority_work_count),
        "settled_authority_work_count": (closure.settled_authority_work_count),
        "started_external_execution_count": (closure.started_external_execution_count),
        "settled_external_execution_count": (closure.settled_external_execution_count),
        "opened_product_session_count": closure.opened_product_session_count,
        "closed_product_session_count": closure.closed_product_session_count,
        "opened_local_placement_count": closure.opened_local_placement_count,
        "closed_local_placement_count": closure.closed_local_placement_count,
    }


def _validate_artifact_collection(value: object) -> None:
    artifacts = _sequence(value, "native_receipt_artifact_invalid")
    if not artifacts:
        raise ValueError("native_receipt_artifact_invalid")
    paths = []
    for artifact in artifacts:
        values = _mapping(
            artifact,
            "native_receipt_artifact_invalid",
        )
        if set(values) != {"relative_path", "sha256", "size_bytes"}:
            raise ValueError("native_receipt_artifact_invalid")
        relative = _relative_path(
            values.get("relative_path"),
            finding="native_receipt_path_not_redacted",
        )
        digest = values.get("sha256")
        size = values.get("size_bytes")
        if (
            not isinstance(digest, str)
            or _SHA256.fullmatch(digest) is None
            or type(size) is not int
            or size < 0
        ):
            raise ValueError("native_receipt_artifact_invalid")
        paths.append(relative.as_posix())
    if len(paths) != len(set(paths)):
        raise ValueError("native_receipt_artifact_invalid")


def _validate_redaction(value: object) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("native_receipt_record_not_redacted")
            normalized = key.casefold().replace("-", "_").replace(" ", "_")
            if any(forbidden in normalized for forbidden in _FORBIDDEN_RECORD_KEYS):
                raise ValueError("native_receipt_record_not_redacted")
            _validate_redaction(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_redaction(child)
    elif isinstance(value, str):
        _validate_safe_record_string(value)


def _validate_safe_record_string(value: str) -> None:
    if _is_absolute_text_path(value):
        raise ValueError("native_receipt_path_not_redacted")
    if (
        _WINDOWS_ABSOLUTE_FRAGMENT.search(value) is not None
        or _POSIX_ABSOLUTE_FRAGMENT.search(value) is not None
    ):
        raise ValueError("native_receipt_record_not_redacted")
    if _SENSITIVE_TEXT.search(value) is not None or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise ValueError("native_receipt_record_not_redacted")


def _qualification_projects_from_record(
    record: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    qualification = _mapping(
        record.get("qualification"),
        "native_receipt_qualification_invalid",
    )
    return tuple(
        _mapping(project, "native_receipt_qualification_invalid")
        for project in _sequence(
            qualification.get("completed_projects"),
            "native_receipt_qualification_invalid",
        )
    )


def _candidate_executions_from_record(
    record: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    candidate = _mapping(
        record.get("candidate"),
        "native_receipt_candidate_invalid",
    )
    return tuple(
        _mapping(execution, "native_receipt_candidate_invalid")
        for execution in _sequence(
            candidate.get("executions"),
            "native_receipt_candidate_invalid",
        )
    )


def _artifact_mappings(
    owner: object,
) -> tuple[Mapping[str, object], ...]:
    values = _mapping(owner, "native_receipt_artifact_invalid")
    return tuple(
        _mapping(artifact, "native_receipt_artifact_invalid")
        for artifact in _sequence(
            values.get("artifacts"),
            "native_receipt_artifact_invalid",
        )
    )


def _artifact_entries(
    paths: tuple[Path, ...],
    *,
    application_root: Path,
) -> list[dict[str, object]]:
    return [
        {
            "relative_path": _application_root_relative(path, application_root),
            "sha256": _file_sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(paths)
    ]


def _validate_inventory_collection(
    value: object,
) -> tuple[Mapping[str, object], ...]:
    entries = tuple(
        _mapping(entry, "native_receipt_inventory_invalid")
        for entry in _sequence(value, "native_receipt_inventory_invalid")
    )
    if not entries:
        raise ValueError("native_receipt_inventory_invalid")
    paths: list[str] = []
    for entry in entries:
        if set(entry) != {
            "category",
            "relative_path",
            "sha256",
            "size_bytes",
        }:
            raise ValueError("native_receipt_inventory_invalid")
        relative = _relative_path(
            entry.get("relative_path"),
            finding="native_receipt_inventory_invalid",
        )
        category = entry.get("category")
        digest = entry.get("sha256")
        size = entry.get("size_bytes")
        if (
            category not in _INVENTORY_CATEGORIES
            or not isinstance(digest, str)
            or _SHA256.fullmatch(digest) is None
            or type(size) is not int
            or size < 0
        ):
            raise ValueError("native_receipt_inventory_invalid")
        paths.append(relative.as_posix())
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("native_receipt_inventory_invalid")
    return entries


def _validate_inventory_coverage(
    inventory: tuple[Mapping[str, object], ...],
    *,
    qualification_projects: tuple[Mapping[str, object], ...],
    candidate_executions: tuple[Mapping[str, object], ...],
    candidate_directory: PurePosixPath,
) -> None:
    inventory_by_path = {str(entry["relative_path"]): entry for entry in inventory}
    categories = _inventory_category_contract(
        qualification_projects=qualification_projects,
        candidate_executions=candidate_executions,
        candidate_directory=candidate_directory,
        inventory_paths=tuple(inventory_by_path),
    )
    if {
        path: entry["category"] for path, entry in inventory_by_path.items()
    } != categories:
        raise ValueError("native_receipt_inventory_unclassified")
    manifest_entries = {
        str(artifact["relative_path"]): artifact
        for owner in (*qualification_projects, *candidate_executions)
        for artifact in _artifact_mappings(owner)
    }
    if len(manifest_entries) != sum(
        len(_artifact_mappings(owner))
        for owner in (*qualification_projects, *candidate_executions)
    ):
        raise ValueError("native_receipt_artifact_invalid")
    for path, artifact in manifest_entries.items():
        inventoried = inventory_by_path.get(path)
        if inventoried is None or any(
            inventoried[name] != artifact[name] for name in ("sha256", "size_bytes")
        ):
            raise ValueError("native_receipt_inventory_mismatch")


def _collect_application_root_inventory(
    application_root: Path,
    *,
    qualification_projects: tuple[Mapping[str, object], ...],
    candidate_executions: tuple[Mapping[str, object], ...],
    candidate_directory: PurePosixPath,
) -> tuple[dict[str, object], ...]:
    application_root_root = application_root.resolve()
    if not application_root_root.is_dir():
        raise ValueError("native_receipt_application_root_missing")
    observed_directories: set[str] = set()
    observed_files: dict[str, Path] = {}
    for current, directory_names, file_names in os.walk(
        application_root_root,
        followlinks=False,
    ):
        current_path = Path(current)
        for name in (*directory_names, *file_names):
            path = current_path / name
            if not path.resolve().is_relative_to(application_root_root):
                raise ValueError("native_receipt_symlink_escape")
        for name in directory_names:
            relative = _application_root_relative(
                current_path / name,
                application_root_root,
            )
            if relative in observed_directories:
                raise ValueError("native_receipt_inventory_duplicate")
            observed_directories.add(relative)
        for name in file_names:
            path = current_path / name
            relative = _application_root_relative(path, application_root_root)
            if relative in observed_files:
                raise ValueError("native_receipt_inventory_duplicate")
            observed_files[relative] = path

    categories = _inventory_category_contract(
        qualification_projects=qualification_projects,
        candidate_executions=candidate_executions,
        candidate_directory=candidate_directory,
        inventory_paths=tuple(observed_files),
    )
    expected_directories = {
        parent.as_posix()
        for relative_path in categories
        for parent in PurePosixPath(relative_path).parents
        if parent != PurePosixPath(".")
    }
    if observed_directories != expected_directories:
        raise ValueError("native_receipt_application_root_directory_invalid")
    return tuple(
        {
            "category": categories[relative_path],
            "relative_path": relative_path,
            "sha256": _file_sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for relative_path, path in sorted(observed_files.items())
    )


def _inventory_category_contract(
    *,
    qualification_projects: tuple[Mapping[str, object], ...],
    candidate_executions: tuple[Mapping[str, object], ...],
    candidate_directory: PurePosixPath,
    inventory_paths: tuple[str, ...],
) -> dict[str, str]:
    if len(qualification_projects) != 3 or len(candidate_executions) != 2:
        raise ValueError("native_receipt_inventory_invalid")
    categories = {name: "authority_store" for name in _AUTHORITY_STORE_FILES}

    qualification_root: PurePosixPath | None = None
    expected_locations = (
        PurePosixPath("transmission"),
        PurePosixPath("polarization/x-input"),
        PurePosixPath("polarization/y-input"),
    )
    for project, expected_location in zip(
        qualification_projects,
        expected_locations,
        strict=True,
    ):
        artifact_paths = tuple(
            _relative_path(
                artifact.get("relative_path"),
                finding="native_receipt_artifact_invalid",
            )
            for artifact in _artifact_mappings(project)
        )
        parents = {path.parent for path in artifact_paths}
        if (
            len(parents) != 1
            or {path.name for path in artifact_paths} != _QUALIFICATION_ARTIFACT_FILES
        ):
            raise ValueError("native_receipt_qualification_invalid")
        parent = next(iter(parents))
        root = parent
        for _ in expected_location.parts:
            root = root.parent
        if parent != root / expected_location:
            raise ValueError("native_receipt_qualification_invalid")
        if qualification_root is None:
            qualification_root = root
        elif root != qualification_root:
            raise ValueError("native_receipt_qualification_invalid")
        categories.update(
            {path.as_posix(): "qualification_run" for path in artifact_paths}
        )
    assert qualification_root is not None
    if (
        len(qualification_root.parts) != 3
        or qualification_root.parts[:2] != ("runs", "qualification")
        or not qualification_root.name.startswith("lumerical-qualification-")
        or qualification_root.name == "lumerical-qualification-"
    ):
        raise ValueError("native_receipt_qualification_invalid")

    if (
        len(candidate_directory.parts) != 5
        or candidate_directory.parts[0] != "runs"
        or not candidate_directory.parts[1].endswith("-metalens-native-receipt")
        or candidate_directory.parts[2] != "r"
        or re.fullmatch(r"[0-9a-f]{16}", candidate_directory.parts[3]) is None
        or candidate_directory.name != _CELL_IDENTITY
    ):
        raise ValueError("native_receipt_candidate_invalid")
    for axis, execution in zip(
        ("x", "y"),
        candidate_executions,
        strict=True,
    ):
        artifact_paths = tuple(
            _relative_path(
                artifact.get("relative_path"),
                finding="native_receipt_artifact_invalid",
            )
            for artifact in _artifact_mappings(execution)
        )
        expected_parent = candidate_directory / f"from-{axis}"
        if {path.parent for path in artifact_paths} != {expected_parent} or {
            path.name for path in artifact_paths
        } != _CANDIDATE_WORK_FILES:
            raise ValueError("native_receipt_candidate_invalid")
        category = f"candidate_{axis}_linear_work"
        categories.update({path.as_posix(): category for path in artifact_paths})

    response_directory = candidate_directory.parent
    response_paths = {
        path
        for path in inventory_paths
        if PurePosixPath(path).is_relative_to(response_directory)
        and not PurePosixPath(path).is_relative_to(candidate_directory)
    }
    fixed_response_paths = {
        (response_directory / "request.json").as_posix(),
        (response_directory / "manifest.json").as_posix(),
    }
    capacity_paths = {
        path
        for path in response_paths
        if PurePosixPath(path).parent == response_directory / "capacity"
        and _CAPACITY_ARTIFACT.fullmatch(PurePosixPath(path).name)
    }
    if (
        len(capacity_paths) != 1
        or response_paths != fixed_response_paths | capacity_paths
    ):
        raise ValueError("native_receipt_candidate_response_invalid")
    categories.update({path: "candidate_response" for path in response_paths})
    if set(inventory_paths) != set(categories):
        raise ValueError("native_receipt_inventory_unclassified")
    return categories


def _canonical_file_mapping(path: Path) -> Mapping[str, object]:
    raw = path.read_bytes()
    try:
        values = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("native_receipt_artifact_json_invalid") from error
    if not isinstance(values, dict) or encode_bytes(values) != raw:
        raise RuntimeError("native_receipt_artifact_json_invalid")
    return values


def _canonical_mapping(
    value: Mapping[str, object],
) -> dict[str, object]:
    try:
        decoded = json.loads(encode_bytes(value))
    except (TypeError, ValueError) as error:
        raise ValueError("native_receipt_record_invalid") from error
    if not isinstance(decoded, dict):
        raise ValueError("native_receipt_record_invalid")
    return decoded


def _mapping(value: object, finding: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value


def _sequence(value: object, finding: str) -> tuple[object, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(finding)
    return tuple(value)


def _reference(value: object, finding: str) -> Reference:
    try:
        if not isinstance(value, Mapping):
            raise TypeError("reference_mapping_required")
        reference = Reference.from_mapping(value)
    except (TypeError, ValueError) as error:
        raise ValueError(finding) from error
    if reference.as_mapping() != dict(value):
        raise ValueError(finding)
    if _MEDIA_TYPE.fullmatch(reference.media_type) is None:
        raise ValueError(finding)
    return reference


def _relative_path(value: object, *, finding: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ValueError(finding)
    if _is_absolute_text_path(value):
        raise ValueError(finding)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value.replace("\\", "/")
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(finding)
    return path


def _is_absolute_text_path(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _application_root_relative(path: Path, application_root: Path) -> str:
    resolved = path.resolve()
    root = application_root.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("native_receipt_artifact_outside_application_root")
    return resolved.relative_to(root).as_posix()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

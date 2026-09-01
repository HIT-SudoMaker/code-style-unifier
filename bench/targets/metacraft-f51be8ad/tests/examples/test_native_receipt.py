from __future__ import annotations

from collections.abc import Iterator, Mapping
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import numpy

from examples.native_receipt import (
    NATIVE_RECEIPT_RECORD,
    NativeReceiptClosure,
    NativeReceiptQualificationIncomplete,
    _form_candidate_reference_surfaces,
    native_receipt_application_root_path,
    run_native_receipt,
    write_native_receipt_record,
)
from metacraft.authority import Authority, Reference
from metacraft.authority.session import AuthoritySession
from metacraft.field.reference_surface import (
    AdmittedReferenceSurface,
    ReferenceSurfaceResponse,
    RequestedInputBasis,
)
from metacraft.field.sample import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from metacraft.external_activity import (
    ExternalActivityClosure,
    ExternalActivityOrigin,
)
from metacraft.science.periodic_response import (
    PeriodicResponseContext,
    PeriodicResponseKind,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseQualification,
)


RESPONSE_CAPABILITIES = (
    "periodic_transmission_response",
    "periodic_polarization_response",
    "periodic_reference_surface_response",
)
QUALIFICATION_PURPOSES = (
    "transmission_and_reference_surface",
    "x_linear_polarization",
    "y_linear_polarization",
)
QUALIFICATION_LOCATIONS = (
    "transmission",
    "polarization/x-input",
    "polarization/y-input",
)
INPUT_BASES = ("x linear", "y linear")
QUALIFICATION_ROOT = "runs/qualification/lumerical-qualification-20260801T000000000000Z"
RESPONSE_ROOT = "runs/20260801t000000z-metalens-native-receipt/r/0123456789abcdef"
CANDIDATE_DIRECTORY = (
    f"{RESPONSE_ROOT}/" "rectangular-fin-height-0600nm-length-0220nm-width-0100nm"
)
QUALIFICATION_FILES = (
    "after.fsp",
    "before.fsp",
    "before_p0.log",
    "execution.json",
)
CANDIDATE_FILES = (
    "after.fsp",
    "before.fsp",
    "before_p0.log",
    "construction.json",
    "execution.json",
    "identity.json",
    "input.json",
    "observation.json",
    "solver.log",
    "work.json",
)
FORBIDDEN_RECORD_TERMS = frozenset(
    {
        "aperture",
        "cell_library",
        "command_line",
        "credential",
        "environment",
        "field_propagation",
        "focus",
        "license_server",
        "metalens_benchmark_case",
        "project_comparison",
        "raw_product_log",
        "scientific_result",
        "token",
    }
)


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reference(name: str) -> dict[str, object]:
    return {
        "content_hash": _digest(name),
        "media_type": "application/json",
        "metadata_content_hash": _digest(f"{name}:metadata"),
        "size_bytes": len(name),
    }


def _artifact(relative_path: str, body: bytes) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "sha256": hashlib.sha256(body).hexdigest(),
        "size_bytes": len(body),
    }


def _activity(
    origin: str,
    *,
    authority_work: int = 0,
    external_execution: int = 0,
    product_session: int = 0,
    local_placement: int = 0,
) -> dict[str, object]:
    return {
        "origin": origin,
        "acquired_authority_work_count": authority_work,
        "settled_authority_work_count": authority_work,
        "started_external_execution_count": external_execution,
        "settled_external_execution_count": external_execution,
        "opened_product_session_count": product_session,
        "closed_product_session_count": product_session,
        "opened_local_placement_count": local_placement,
        "closed_local_placement_count": local_placement,
    }


def _application_root_bodies() -> dict[str, bytes]:
    bodies = {
        "authority/workspace.marker": b"workspace\n",
        "authority/workspace.sqlite3": b"sqlite",
        "authority/workspace.writer.lock": b"",
        f"{RESPONSE_ROOT}/request.json": b"request",
        f"{RESPONSE_ROOT}/manifest.json": b"manifest",
        (
            f"{RESPONSE_ROOT}/capacity/"
            "capacity-0123456789abcdef0123456789abcdef.json"
        ): b"capacity",
    }
    for purpose, location in zip(
        QUALIFICATION_PURPOSES,
        QUALIFICATION_LOCATIONS,
        strict=True,
    ):
        for filename in QUALIFICATION_FILES:
            bodies[f"{QUALIFICATION_ROOT}/{location}/{filename}"] = (
                f"{purpose}:{filename}".encode("utf-8")
            )
    for axis in ("x", "y"):
        for filename in CANDIDATE_FILES:
            bodies[f"{CANDIDATE_DIRECTORY}/from-{axis}/{filename}"] = (
                f"{axis}:{filename}".encode("utf-8")
            )
    return bodies


def _category(relative_path: str) -> str:
    if "/qualification/" in relative_path:
        return "qualification_run"
    if "/from-x/" in relative_path:
        return "candidate_x_linear_work"
    if "/from-y/" in relative_path:
        return "candidate_y_linear_work"
    if relative_path.startswith(f"{RESPONSE_ROOT}/"):
        return "candidate_response"
    return "authority_store"


def _valid_record() -> dict[str, object]:
    bodies = _application_root_bodies()
    qualification_projects = [
        {
            "purpose": purpose,
            "artifacts": [
                _artifact(path, bodies[path])
                for filename in QUALIFICATION_FILES
                for path in (f"{QUALIFICATION_ROOT}/{location}/{filename}",)
            ],
        }
        for purpose, location in zip(
            QUALIFICATION_PURPOSES,
            QUALIFICATION_LOCATIONS,
            strict=True,
        )
    ]
    executions = [
        {
            "input_basis": basis,
            "work_identity": _digest(f"work:{basis}"),
            "observation_reference": _reference(f"observation:{basis}"),
            "receipt_reference": _reference(f"receipt:{basis}"),
            "execution_origin": "native",
            "artifacts": [
                _artifact(path, bodies[path])
                for filename in CANDIDATE_FILES
                for path in (f"{CANDIDATE_DIRECTORY}/from-{axis}/{filename}",)
            ],
        }
        for basis, axis in zip(INPUT_BASES, ("x", "y"), strict=True)
    ]
    inventory = [
        {
            "category": _category(path),
            **_artifact(path, body),
        }
        for path, body in sorted(bodies.items())
    ]
    formation_qualification = _reference("surface-formation-qualification")
    formed_surfaces = [
        {
            "input_basis": basis,
            "raw_observation_reference": execution["observation_reference"],
            "formed_surface_reference": _reference(f"formed-surface:{basis}"),
            "source_references": [
                execution["observation_reference"],
                formation_qualification,
            ],
        }
        for basis, execution in zip(INPUT_BASES, executions, strict=True)
    ]
    return {
        "schema": "metacraft.native_receipt",
        "verification": "verified",
        "product": {
            "binding_reference": _reference("binding"),
            "capacity_reference": _reference("capacity"),
            "material_observation_reference": _reference("material-observation"),
            "response_capabilities": list(RESPONSE_CAPABILITIES),
        },
        "qualification": {
            "activity": _activity(
                "native",
                external_execution=3,
                product_session=1,
                local_placement=1,
            ),
            "completed_projects": qualification_projects,
        },
        "materials": {
            "activity": _activity("native", product_session=1),
        },
        "candidate": {
            "activity": _activity(
                "native",
                authority_work=2,
                external_execution=2,
                product_session=1,
                local_placement=1,
            ),
            "directory": CANDIDATE_DIRECTORY,
            "height_nm": 600,
            "short_side_nm": 100,
            "long_side_nm": 220,
            "executions": executions,
        },
        "formation": {
            "algorithm": "periodic_rectilinear_bilinear_v1",
            "qualification_reference": formation_qualification,
            "surface": {
                "position_m": "0.0000007",
                "shape": [24, 24],
                "spacing_m": "0.000000016666666666666667",
            },
            "surfaces": formed_surfaces,
        },
        "recovery": {
            "activity": _activity("recorded"),
            "work_identities": [execution["work_identity"] for execution in executions],
            "observation_references": [
                execution["observation_reference"] for execution in executions
            ],
            "receipt_references": [
                execution["receipt_reference"] for execution in executions
            ],
        },
        "native_inventory": inventory,
        "recovery_inventory": [dict(entry) for entry in inventory],
        "solve_count": sum((3, 0, 2)),
    }


def _walk(value: object) -> Iterator[object]:
    yield value
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield key
            yield from _walk(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk(child)


def _write_application_root(application_root: Path) -> None:
    for relative_path, body in _application_root_bodies().items():
        path = application_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


def _short_application_root(tmp_path: Path) -> Path:
    suffix = hashlib.sha256(str(tmp_path).encode("utf-8")).hexdigest()[:8]
    application_root = tmp_path.parent / f"w-{suffix}"
    application_root.mkdir()
    return application_root


def _replace_nested(
    record: dict[str, object],
    path: tuple[str | int, ...],
    value: object,
) -> None:
    target: object = record
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]


def _qualification_activity() -> ExternalActivityClosure:
    return ExternalActivityClosure(
        origin=ExternalActivityOrigin.NATIVE,
        acquired_authority_work_count=0,
        settled_authority_work_count=0,
        started_external_execution_count=3,
        settled_external_execution_count=3,
        opened_product_session_count=3,
        closed_product_session_count=3,
        opened_local_placement_count=3,
        closed_local_placement_count=3,
    )


def _qualification_only_response(
    *,
    qualifications: tuple[PeriodicResponseQualification, ...],
    context_kinds: tuple[PeriodicResponseKind, ...] | None = None,
) -> SimpleNamespace:
    qualified_kinds = tuple(
        PeriodicResponseKind(result.response_kind)
        for result in qualifications
        if result.is_qualified
    )
    return SimpleNamespace(
        product_binding={
            "api_identity": "fixture-api",
            "engine": "fixture-engine",
            "executable": "fixture-executable",
            "license_server": "fixture-server",
            "native_license_features": (
                "lumerical_gui",
                "lumerical_solve",
            ),
            "product_version": "fixture-version",
            "python_api": "fixture-python-api",
            "resource_identity": "fixture-resource",
            "response_qualifications": tuple(
                result.as_mapping() for result in qualifications
            ),
        },
        context=PeriodicResponseContext(
            binding_reference=Reference.from_mapping(_reference("binding")),
            capacity_scope="lumerical-fdtd/fixture",
            response_kinds=(
                qualified_kinds if context_kinds is None else context_kinds
            ),
            qualification_closure=_qualification_activity(),
        ),
    )


def _canary_inputs(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "materials").mkdir()
    (repository / "materials" / "lumerical.toml").write_text(
        "fixture",
        encoding="utf-8",
    )
    (repository / ".env.lumerical").write_text(
        "\n".join(
            (
                f"LUMERICAL_FDTD_PATH={tmp_path / 'fdtd-solutions.exe'}",
                f"LUMERICAL_PYTHON_API_PATH={tmp_path / 'lumapi.py'}",
                f"LUMERICAL_LICENSE_UTILITY_PATH={tmp_path / 'lmutil.exe'}",
                "ANSYSLMD_LICENSE_FILE=fixture-server",
            )
        ),
        encoding="utf-8",
    )
    application_root = (tmp_path / "application_root").resolve()
    environ = {
        "METACRAFT_RUN_LUMERICAL_CANARY": "1",
        "METACRAFT_CANARY_APPLICATION_ROOT": str(application_root),
    }
    return repository, application_root, environ


def test_canary_gate_requires_one_explicit_absolute_application_root(
    tmp_path: Path,
) -> None:
    absent = (tmp_path / "native-receipt-application_root").resolve()

    with pytest.raises(RuntimeError, match="lumerical_canary_disabled"):
        native_receipt_application_root_path({})
    with pytest.raises(ValueError, match="native_receipt_application_root_required"):
        native_receipt_application_root_path({"METACRAFT_RUN_LUMERICAL_CANARY": "1"})
    with pytest.raises(
        ValueError,
        match="native_receipt_application_root_must_be_absolute",
    ):
        native_receipt_application_root_path(
            {
                "METACRAFT_RUN_LUMERICAL_CANARY": "1",
                "METACRAFT_CANARY_APPLICATION_ROOT": "relative-application_root",
            }
        )

    assert (
        native_receipt_application_root_path(
            {
                "METACRAFT_RUN_LUMERICAL_CANARY": "1",
                "METACRAFT_CANARY_APPLICATION_ROOT": str(absent),
            }
        )
        == absent
    )
    assert not absent.exists()


def test_canary_rejects_a_preexisting_application_root_before_prerequisites(
    tmp_path: Path,
) -> None:
    application_root = (tmp_path / "preexisting").resolve()
    application_root.mkdir()
    sentinel = application_root / "belongs-to-another-run"
    sentinel.write_bytes(b"untouched")

    with pytest.raises(
        FileExistsError,
        match="^application_root_must_be_new$",
    ):
        run_native_receipt(
            repository_root=tmp_path / "missing-repository",
            application_root=application_root,
            environ={
                "METACRAFT_RUN_LUMERICAL_CANARY": "1",
                "METACRAFT_CANARY_APPLICATION_ROOT": str(application_root),
            },
        )

    assert sentinel.read_bytes() == b"untouched"
    assert tuple(application_root.iterdir()) == (sentinel,)


def test_failed_new_application_root_claim_is_never_reused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application_root = (tmp_path / "claimed-once").resolve()
    environ = {
        "METACRAFT_RUN_LUMERICAL_CANARY": "1",
        "METACRAFT_CANARY_APPLICATION_ROOT": str(application_root),
    }

    with pytest.raises(FileNotFoundError, match="lumerical_environment_missing"):
        run_native_receipt(
            repository_root=tmp_path / "missing-repository",
            application_root=application_root,
            environ=environ,
        )

    opened_product = False

    def must_not_open(**_kwargs: object) -> None:
        nonlocal opened_product
        opened_product = True

    monkeypatch.setattr(
        "examples.native_receipt.LumericalPeriodicResponse.open",
        must_not_open,
    )
    with pytest.raises(
        FileExistsError,
        match="^application_root_must_be_new$",
    ):
        run_native_receipt(
            repository_root=tmp_path / "still-missing",
            application_root=application_root,
            environ=environ,
        )

    assert not opened_product
    assert (application_root / "authority" / "workspace.marker").is_file()


def test_tracked_record_has_one_relative_repository_location() -> None:
    assert NATIVE_RECEIPT_RECORD == Path(
        ".scratch/sonnet-deep-architecture/NATIVE-RECEIPT.json"
    )
    assert not NATIVE_RECEIPT_RECORD.is_absolute()


def test_tracked_native_receipt_is_one_strict_five_solve_closure() -> None:
    closure = NativeReceiptClosure.from_mapping(
        json.loads(NATIVE_RECEIPT_RECORD.read_text(encoding="utf-8"))
    )

    record = closure.as_mapping()
    assert record["solve_count"] == 5
    formation = record["formation"]
    assert isinstance(formation, dict)
    assert formation["algorithm"] == "periodic_rectilinear_bilinear_v1"
    surface = formation["surface"]
    assert isinstance(surface, dict)
    assert surface["shape"] == [24, 24]


def test_partial_qualification_stops_before_material_or_candidate_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, application_root, environ = _canary_inputs(tmp_path)
    qualifications = (
        PeriodicResponseQualification.qualified(
            PERIODIC_TRANSMISSION_RESPONSE
        ),
        PeriodicResponseQualification.qualified(
            PERIODIC_POLARIZATION_RESPONSE
        ),
        PeriodicResponseQualification.response_not_returned(
            PERIODIC_REFERENCE_SURFACE_RESPONSE
        ),
    )
    response = _qualification_only_response(
        qualifications=qualifications,
    )
    monkeypatch.setattr(
        "examples.native_receipt.LumericalPeriodicResponse.open",
        lambda **_kwargs: response,
    )
    monkeypatch.setattr(
        "examples.native_receipt._observe_canary_materials",
        lambda *_args, **_kwargs: pytest.fail("materials must not open"),
    )

    with pytest.raises(
        NativeReceiptQualificationIncomplete,
        match="^native_receipt_capabilities_incomplete$",
    ) as caught:
        run_native_receipt(
            repository_root=repository,
            application_root=application_root,
            environ=environ,
        )

    assert caught.value.response_qualifications == qualifications
    assert caught.value.qualification_activity == _qualification_activity()
    assert (
        caught.value.qualification_activity.started_external_execution_count
        == 3
    )
    assert (
        caught.value.qualification_activity.settled_external_execution_count
        == 3
    )
    assert caught.value.open_permit_count == 0
    assert caught.value.args == ("native_receipt_capabilities_incomplete",)
    assert all(
        set(result.as_mapping()) == {"response_kind", "status"}
        for result in caught.value.response_qualifications
    )
    assert not any(
        sensitive in str(caught.value).casefold()
        for sensitive in (
            "application_root",
            "license",
            "session",
            "lane",
            "process",
            "fixture-server",
        )
    )
    assert not (application_root / "runs" / "qualification").exists()


@pytest.mark.parametrize(
    "binding_change",
    (
        "qualification_missing",
        "qualification_out_of_order",
        "context_conflict",
    ),
)
def test_canary_rejects_malformed_or_conflicting_qualification_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    binding_change: str,
) -> None:
    repository, application_root, environ = _canary_inputs(tmp_path)
    qualifications = (
        PeriodicResponseQualification.qualified(
            PERIODIC_TRANSMISSION_RESPONSE
        ),
        PeriodicResponseQualification.qualified(
            PERIODIC_POLARIZATION_RESPONSE
        ),
        PeriodicResponseQualification.qualified(
            PERIODIC_REFERENCE_SURFACE_RESPONSE
        ),
    )
    context_kinds = None
    if binding_change == "context_conflict":
        context_kinds = (
            PeriodicResponseKind.TRANSMISSION,
            PeriodicResponseKind.POLARIZATION,
        )
    response = _qualification_only_response(
        qualifications=qualifications,
        context_kinds=context_kinds,
    )
    if binding_change == "qualification_missing":
        del response.product_binding["response_qualifications"]
    elif binding_change == "qualification_out_of_order":
        response.product_binding["response_qualifications"] = tuple(
            reversed(response.product_binding["response_qualifications"])
        )
    monkeypatch.setattr(
        "examples.native_receipt.LumericalPeriodicResponse.open",
        lambda **_kwargs: response,
    )
    monkeypatch.setattr(
        "examples.native_receipt._observe_canary_materials",
        lambda *_args, **_kwargs: pytest.fail("materials must not open"),
    )

    with pytest.raises(
        (TypeError, ValueError),
        match=(
            "lumerical_binding_fields_invalid|"
            "binding_response_qualifications_invalid|"
            "native_receipt_qualification_evidence_conflict"
        ),
    ):
        run_native_receipt(
            repository_root=repository,
            application_root=application_root,
            environ=environ,
        )


def test_complete_qualification_continues_to_material_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, application_root, environ = _canary_inputs(tmp_path)
    qualifications = tuple(
        PeriodicResponseQualification.qualified(response_kind)
        for response_kind in RESPONSE_CAPABILITIES
    )
    response = _qualification_only_response(
        qualifications=qualifications,
    )
    monkeypatch.setattr(
        "examples.native_receipt.LumericalPeriodicResponse.open",
        lambda **_kwargs: response,
    )

    class MaterialBoundaryReached(RuntimeError):
        pass

    def material_boundary(*_args: object, **_kwargs: object) -> None:
        raise MaterialBoundaryReached

    monkeypatch.setattr(
        "examples.native_receipt._observe_canary_materials",
        material_boundary,
    )

    with pytest.raises(MaterialBoundaryReached):
        run_native_receipt(
            repository_root=repository,
            application_root=application_root,
            environ=environ,
        )


def test_closure_derives_five_solves_from_owner_activity() -> None:
    record = _valid_record()

    restored = NativeReceiptClosure.from_mapping(record).as_mapping()

    assert restored == record
    starts = tuple(
        restored[phase]["activity"]["started_external_execution_count"]
        for phase in ("qualification", "materials", "candidate")
    )
    assert starts == (3, 0, 2)
    assert restored["solve_count"] == sum(starts)
    assert restored["recovery"]["activity"] == _activity("recorded")
    assert restored["native_inventory"] == restored["recovery_inventory"]


@pytest.mark.parametrize(
    ("path", "value", "finding"),
    [
        (("solve_count",), 6, "native_receipt_solve_count_invalid"),
        (
            (
                "qualification",
                "activity",
                "started_external_execution_count",
            ),
            4,
            "native_receipt_qualification_invalid",
        ),
        (
            ("materials", "activity", "opened_product_session_count"),
            2,
            "native_receipt_materials_invalid",
        ),
        (
            (
                "candidate",
                "activity",
                "acquired_authority_work_count",
            ),
            3,
            "native_receipt_candidate_invalid",
        ),
        (
            (
                "recovery",
                "activity",
                "started_external_execution_count",
            ),
            1,
            "native_receipt_recovery_invalid",
        ),
        (
            ("candidate", "height_nm"),
            700,
            "native_receipt_candidate_invalid",
        ),
        (
            ("candidate", "executions", 0, "execution_origin"),
            "recorded",
            "native_receipt_candidate_invalid",
        ),
    ],
)
def test_closure_rejects_invented_or_unsettled_activity(
    path: tuple[str | int, ...],
    value: object,
    finding: str,
) -> None:
    record = _valid_record()
    _replace_nested(record, path, value)

    with pytest.raises(ValueError, match=finding):
        NativeReceiptClosure.from_mapping(record)


def test_closure_requires_recovery_to_repeat_exact_native_evidence() -> None:
    changed_reference = _valid_record()
    recovery = changed_reference["recovery"]
    assert isinstance(recovery, dict)
    recovery["receipt_references"] = [_reference("different-receipt")]
    with pytest.raises(ValueError, match="native_receipt_recovery_invalid"):
        NativeReceiptClosure.from_mapping(changed_reference)

    changed_inventory = _valid_record()
    inventory = changed_inventory["recovery_inventory"]
    assert isinstance(inventory, list)
    assert isinstance(inventory[0], dict)
    inventory[0]["size_bytes"] = 99
    with pytest.raises(
        ValueError,
        match="native_receipt_recovery_changed_application_root",
    ):
        NativeReceiptClosure.from_mapping(changed_inventory)


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("formation", "algorithm"), "another_algorithm"),
        (("formation", "surface", "shape"), [24, 23]),
        (
            ("formation", "surfaces", 0, "input_basis"),
            "y linear",
        ),
        (
            ("formation", "surfaces", 1, "source_references", 0),
            _reference("wrong-raw-source"),
        ),
        (
            ("formation", "surfaces", 0, "source_references", 1),
            _reference("wrong-qualification"),
        ),
    ),
)
def test_closure_requires_exact_common_surface_formation(
    path: tuple[str | int, ...],
    value: object,
) -> None:
    record = _valid_record()
    _replace_nested(record, path, value)

    with pytest.raises(ValueError, match="native_receipt_formation_invalid"):
        NativeReceiptClosure.from_mapping(record)


def test_canary_forms_both_candidate_surfaces_once_with_exact_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_references = tuple(
        Reference.from_mapping(_reference(f"observation:{basis}"))
        for basis in INPUT_BASES
    )
    qualification_reference = Reference.from_mapping(
        _reference("surface-formation-qualification")
    )
    values = numpy.zeros((24, 24), dtype=numpy.complex128)
    values.setflags(write=False)
    common_surface = PlaneSurface(700e-9, 400e-9 / 24, (24, 24))
    admitted = tuple(
        AdmittedReferenceSurface(
            ReferenceSurfaceResponse(
                field=Field(
                    wavelength_m=400e-9,
                    surface=common_surface,
                    frame=CoordinateFrame(),
                    medium=Medium("air"),
                    basis=ComponentBasis.CARTESIAN,
                    electric_components=tuple(
                        FieldComponent(name, values)
                        for name in ("x", "y", "z")
                    ),
                    source_references=(raw, qualification_reference),
                    incident_reference_power=1.0,
                ),
                requested_input_basis=RequestedInputBasis(basis),
                order_regime="multi order",
                transmitted_power=0.5,
            ),
            Reference.from_mapping(_reference(f"formed-surface:{basis}")),
        )
        for basis, raw in zip(INPUT_BASES, raw_references, strict=True)
    )
    calls = 0

    def form_once(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        assert kwargs["cell_identity"] == (
            "rectangular-fin-height-0600nm-length-0220nm-width-0100nm"
        )
        return admitted

    monkeypatch.setattr(
        "examples.native_receipt.admit_reference_surfaces",
        form_once,
    )
    observed = SimpleNamespace(
        items=tuple(
            SimpleNamespace(body_reference=reference)
            for reference in raw_references
        )
    )
    session = AuthoritySession(Authority(tmp_path / "authority"))

    evidence = _form_candidate_reference_surfaces(
        SimpleNamespace(),  # type: ignore[arg-type]
        observed,  # type: ignore[arg-type]
        authority_session=session,
    )

    assert calls == 1
    assert evidence["surface"] == {
        "position_m": "6.9999999999999997e-07",
        "shape": [24, 24],
        "spacing_m": "1.6666666666666667e-08",
    }
    surfaces = evidence["surfaces"]
    assert isinstance(surfaces, list)
    assert [item["input_basis"] for item in surfaces] == list(INPUT_BASES)
    assert [item["source_references"] for item in surfaces] == [
        [raw.as_mapping(), qualification_reference.as_mapping()]
        for raw in raw_references
    ]


@pytest.mark.parametrize(
    "extra_relative_path",
    [
        f"{QUALIFICATION_ROOT}/polarization/z-input/after.fsp",
        f"{CANDIDATE_DIRECTORY}/from-z/after.fsp",
        f"{RESPONSE_ROOT}/Result.mat",
        "runs/unclassified.bin",
    ],
)
def test_application_root_rejects_every_extra_or_unclassified_file(
    tmp_path: Path,
    extra_relative_path: str,
) -> None:
    application_root = _short_application_root(tmp_path)
    _write_application_root(application_root)
    closure = NativeReceiptClosure.from_mapping(_valid_record())
    extra = application_root / extra_relative_path
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_bytes(b"extra")

    with pytest.raises(
        ValueError,
        match=("native_receipt_(inventory_unclassified|" "candidate_response_invalid)"),
    ):
        closure.verify_application_root(application_root)


def test_application_root_rejects_extra_directories_and_symlink_escape(
    tmp_path: Path,
) -> None:
    application_root = _short_application_root(tmp_path)
    _write_application_root(application_root)
    closure = NativeReceiptClosure.from_mapping(_valid_record())

    (application_root / "runs" / "unused-candidate").mkdir()
    with pytest.raises(
        ValueError,
        match="native_receipt_application_root_directory_invalid",
    ):
        closure.verify_application_root(application_root)
    (application_root / "runs" / "unused-candidate").rmdir()

    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside")
    link = application_root / "escape.bin"
    try:
        os.symlink(outside, link)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="native_receipt_symlink_escape"):
        closure.verify_application_root(application_root)


@pytest.mark.parametrize(
    ("owner_directory", "replacement"),
    (
        (
            f"{QUALIFICATION_ROOT}/transmission",
            None,
        ),
        (
            f"{QUALIFICATION_ROOT}/polarization/x-input",
            "before_p1.log",
        ),
        (
            f"{CANDIDATE_DIRECTORY}/from-y",
            "renamed.log",
        ),
    ),
)
def test_application_root_requires_exactly_one_native_solve_sidecar_per_solve(
    tmp_path: Path,
    owner_directory: str,
    replacement: str | None,
) -> None:
    application_root = _short_application_root(tmp_path)
    _write_application_root(application_root)
    closure = NativeReceiptClosure.from_mapping(_valid_record())
    sidecar = application_root / owner_directory / "before_p0.log"
    sidecar.unlink()
    if replacement is not None:
        (sidecar.parent / replacement).write_bytes(b"renamed")

    with pytest.raises(
        ValueError,
        match=(
            "native_receipt_(inventory_unclassified|inventory_mismatch|"
            "application_root_directory_invalid)"
        ),
    ):
        closure.verify_application_root(application_root)


def test_application_root_rejects_an_additional_native_log() -> None:
    record = _valid_record()
    native_inventory = record["native_inventory"]
    recovery_inventory = record["recovery_inventory"]
    assert isinstance(native_inventory, list)
    assert isinstance(recovery_inventory, list)
    extra_path = f"{CANDIDATE_DIRECTORY}/from-x/before_p1.log"
    extra = {
        "category": "candidate_x_linear_work",
        **_artifact(extra_path, b"additional"),
    }
    native_inventory.append(extra)
    recovery_inventory.append(dict(extra))
    native_inventory.sort(key=lambda entry: str(entry["relative_path"]))
    recovery_inventory.sort(key=lambda entry: str(entry["relative_path"]))

    with pytest.raises(
        ValueError,
        match="native_receipt_(candidate_invalid|inventory_unclassified)",
    ):
        NativeReceiptClosure.from_mapping(record)


def test_inventory_rejects_traversal_duplicates_and_wrong_category() -> None:
    traversal = _valid_record()
    traversal_inventory = traversal["native_inventory"]
    assert isinstance(traversal_inventory, list)
    assert isinstance(traversal_inventory[0], dict)
    traversal_inventory[0]["relative_path"] = "../escape"
    with pytest.raises(ValueError, match="native_receipt_inventory_invalid"):
        NativeReceiptClosure.from_mapping(traversal)

    duplicate = _valid_record()
    native = duplicate["native_inventory"]
    recovery = duplicate["recovery_inventory"]
    assert isinstance(native, list) and isinstance(recovery, list)
    native.insert(1, dict(native[0]))
    recovery.insert(1, dict(recovery[0]))
    with pytest.raises(ValueError, match="native_receipt_inventory_invalid"):
        NativeReceiptClosure.from_mapping(duplicate)

    wrong_category = _valid_record()
    native = wrong_category["native_inventory"]
    recovery = wrong_category["recovery_inventory"]
    assert isinstance(native, list) and isinstance(recovery, list)
    authority_index = next(
        index
        for index, entry in enumerate(native)
        if isinstance(entry, dict)
        and entry["relative_path"] == "authority/workspace.marker"
    )
    assert isinstance(native[authority_index], dict)
    assert isinstance(recovery[authority_index], dict)
    native[authority_index]["category"] = "candidate_response"
    recovery[authority_index]["category"] = "candidate_response"
    with pytest.raises(
        ValueError,
        match="native_receipt_inventory_unclassified",
    ):
        NativeReceiptClosure.from_mapping(wrong_category)


def test_redacted_record_rejects_paths_and_sensitive_output_keys(
    tmp_path: Path,
) -> None:
    absolute = _valid_record()
    candidate = absolute["candidate"]
    assert isinstance(candidate, dict)
    candidate["directory"] = str((tmp_path / "private").resolve())
    with pytest.raises(ValueError, match="native_receipt_path_not_redacted"):
        NativeReceiptClosure.from_mapping(absolute)

    for key in ("license_server", "raw_command", "api_token"):
        secret = _valid_record()
        product = secret["product"]
        assert isinstance(product, dict)
        product[key] = "private"
        with pytest.raises(
            ValueError,
            match="native_receipt_record_not_redacted",
        ):
            NativeReceiptClosure.from_mapping(secret)


@pytest.mark.parametrize(
    "concealed_text",
    [
        "application/json LICENSE_SERVER=secret-host",
        r"application/json C:\Users\operator\private.env",
        r"application/json \\fileserver\private\receipt.env",
        "application/json /home/operator/private.env",
        "application/json command=tasklist token=secret",
        "application/json PASSWORD=hunter2 raw_log=solver-output",
    ],
)
def test_redaction_rejects_sensitive_text_hidden_in_allowed_fields(
    concealed_text: str,
) -> None:
    record = _valid_record()
    product = record["product"]
    assert isinstance(product, dict)
    binding = product["binding_reference"]
    assert isinstance(binding, dict)
    binding["media_type"] = concealed_text

    with pytest.raises(
        ValueError,
        match="native_receipt_record_not_redacted",
    ):
        NativeReceiptClosure.from_mapping(record)


def test_reference_media_type_is_one_closed_mime_token() -> None:
    record = _valid_record()
    product = record["product"]
    assert isinstance(product, dict)
    binding = product["binding_reference"]
    assert isinstance(binding, dict)
    binding["media_type"] = "application/json; charset=utf-8"

    with pytest.raises(ValueError, match="native_receipt_product_invalid"):
        NativeReceiptClosure.from_mapping(record)


def test_record_contains_no_science_or_secret_output() -> None:
    values = tuple(
        _walk(NativeReceiptClosure.from_mapping(_valid_record()).as_mapping())
    )
    words = {item.casefold() for item in values if isinstance(item, str)}

    assert words.isdisjoint(FORBIDDEN_RECORD_TERMS)


def test_exhaustive_application_root_inventory_matches_every_byte(
    tmp_path: Path,
) -> None:
    application_root = _short_application_root(tmp_path)
    _write_application_root(application_root)
    closure = NativeReceiptClosure.from_mapping(_valid_record())

    closure.verify_application_root(application_root)

    changed = application_root / CANDIDATE_DIRECTORY / "from-x" / "after.fsp"
    changed.write_bytes(b"changed")
    with pytest.raises(ValueError, match="native_receipt_inventory_mismatch"):
        closure.verify_application_root(application_root)


def test_redacted_record_write_is_canonical_and_outside_application_root(
    tmp_path: Path,
) -> None:
    application_root = _short_application_root(tmp_path)
    _write_application_root(application_root)
    closure = NativeReceiptClosure.from_mapping(_valid_record())
    destination = tmp_path / "native-receipt.json"

    write_native_receipt_record(
        closure,
        application_root=application_root,
        destination=destination,
    )

    encoded = destination.read_bytes()
    assert json.loads(encoded) == closure.as_mapping()
    assert encoded.endswith(b"\n")
    assert str(application_root).encode("utf-8") not in encoded
    assert b"license_server" not in encoded
    assert b"raw_command" not in encoded


@pytest.mark.parametrize(
    "injected_media_type",
    [
        "application/json LICENSE_SERVER=secret",
        r"application/json C:\Users\operator\private.env",
    ],
)
def test_record_write_revalidates_a_detached_snapshot_before_application_root_use(
    tmp_path: Path,
    injected_media_type: str,
) -> None:
    application_root = _short_application_root(tmp_path)
    _write_application_root(application_root)
    closure = NativeReceiptClosure.from_mapping(_valid_record())
    product = closure._record["product"]
    assert isinstance(product, dict)
    binding = product["binding_reference"]
    assert isinstance(binding, dict)
    binding["media_type"] = injected_media_type
    destination = tmp_path / "must-not-exist.json"

    with pytest.raises(
        ValueError,
        match="native_receipt_record_not_redacted",
    ):
        write_native_receipt_record(
            closure,
            application_root=application_root,
            destination=destination,
        )

    assert not destination.exists()

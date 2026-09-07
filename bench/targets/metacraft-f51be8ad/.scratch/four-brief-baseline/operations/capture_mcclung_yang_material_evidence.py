"""Capture read-only Lumerical material receipts for McClung and Yang.

This is a bounded operator script, not production code.  It opens exactly one
hidden empty FDTD session only when ``--execute`` is supplied.  The live
session is exposed through a read-only facade that has no project, geometry,
save, sweep, or solve method.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import uuid4


REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY / "src"))

from metacraft.authority import Authority, Document, Reference  # noqa: E402
from metacraft.authority.session import AuthoritySession  # noqa: E402
from metacraft.canonical import encode_bytes  # noqa: E402
from metacraft.external_activity import _native_activity  # noqa: E402
from metacraft.materials import (  # noqa: E402
    MaterialObservationRequest,
    SolverMaterialLibrary,
)
from metacraft.materials.response import (  # noqa: E402
    RecordedMaterialResponse,
    open_material_response,
)
from metacraft.materials.verification import MaterialUnavailable  # noqa: E402
from metacraft.solvers.lumerical_fdtd.material import (  # noqa: E402
    LumericalMaterialSample,
    NativeIndexPoint,
    NativeMaterialSample,
    sample_frequency_hz,
)
from metacraft.solvers.lumerical_fdtd.material_response import (  # noqa: E402
    LumericalMaterialVerifier,
)
from metacraft.solvers.lumerical_fdtd.periodic_response import (  # noqa: E402
    restore_material_sample,
)
from metacraft.solvers.lumerical_fdtd.probe import _sample_materials  # noqa: E402
from metacraft.solvers.lumerical_fdtd.qualification import (  # noqa: E402
    LumericalConfig,
    read_lumerical_environment,
)
from metacraft.solvers.lumerical_fdtd.session import open_engine  # noqa: E402


REQUESTS = {
    "mcclung-550nm": (
        550,
        {
            "silicon nitride": "Si3N4 (Silicon Nitride) - Luke",
            "fused silica": "SiO2 (Glass) - Palik",
        },
    ),
    "yang-1550nm": (
        1550,
        {
            "silicon": "Si (Silicon) - Palik",
            "silicon dioxide": "SiO2 (Glass) - Palik",
        },
    ),
}
EXPECTED_PYTHON = Path(
    r"C:\Users\Administrator\miniforge3\envs\research_env\python.exe"
).resolve()
FDTD_EXECUTABLE = Path(
    r"C:\Program Files\ANSYS Inc\v252\Lumerical\bin\fdtd-solutions.exe"
).resolve()
FDTD_ENGINE = FDTD_EXECUTABLE.with_name("fdtd-engine.exe").resolve()
PYTHON_API = Path(
    r"C:\Program Files\ANSYS Inc\v252\Lumerical\api\python\lumapi.py"
).resolve()
ZERO_ACTIVITY = {
    "project_loads": 0,
    "geometries_created": 0,
    "material_mutations": 0,
    "saves": 0,
    "solves": 0,
    "sweeps": 0,
}


class ReadOnlyMaterialEngine:
    """Expose only the six read/close methods required by this receipt."""

    __slots__ = ("_calls", "_engine")

    def __init__(self, engine: object, calls: dict[str, int]) -> None:
        self._engine = engine
        self._calls = calls

    def version(self) -> object:
        self._calls["version_reads"] += 1
        return self._engine.version()

    def materialexists(self, native_name: str) -> object:
        self._calls["material_exists_reads"] += 1
        return self._engine.materialexists(native_name)

    def getmaterial(self, native_name: str, property_name: str) -> object:
        self._calls["material_property_reads"] += 1
        return self._engine.getmaterial(native_name, property_name)

    def getindex(self, native_name: str, frequencies: object) -> object:
        self._calls["tabulated_index_reads"] += 1
        return self._engine.getindex(native_name, frequencies)

    def getfdtdindex(
        self,
        native_name: str,
        frequencies: object,
        minimum_frequency: float,
        maximum_frequency: float,
    ) -> object:
        self._calls["fdtd_fit_index_reads"] += 1
        return self._engine.getfdtdindex(
            native_name,
            frequencies,
            minimum_frequency,
            maximum_frequency,
        )

    def close(self) -> object:
        result = self._engine.close()
        self._calls["session_closes"] += 1
        return result


class CapturedProbe:
    """Replay the sole live capture into the existing admission boundary."""

    __slots__ = ("_samples",)

    def __init__(self, samples: dict[str, LumericalMaterialSample]) -> None:
        self._samples = samples

    def sample_materials(
        self,
        config: LumericalConfig,
        native_names: dict[str, str],
        wavelength_nm: int,
    ) -> tuple[LumericalMaterialSample, object]:
        for request_name, (expected_wavelength, expected_names) in REQUESTS.items():
            if native_names == expected_names and wavelength_nm == expected_wavelength:
                return self._samples[request_name], _native_activity(
                    product_session_count=1
                )
        raise ValueError("captured_material_request_changed")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--restore", type=Path, metavar="EVIDENCE_ROOT")
    arguments = parser.parse_args()
    _require_research_environment()
    if arguments.restore is not None:
        _restore_in_fresh_process(arguments.restore)
        return

    config = _load_config()
    library = SolverMaterialLibrary.decode_bytes(
        (REPOSITORY / "materials" / "lumerical.toml").read_bytes()
    )
    _validate_retention_pipeline(library, config)
    if arguments.self_test:
        print("offline-material-retention-self-test-ok")
        return

    for path in (
        FDTD_EXECUTABLE,
        FDTD_ENGINE,
        PYTHON_API,
        config.license_utility,
    ):
        assert path is not None
        if not path.is_file():
            raise FileNotFoundError(path)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    root = (
        config.runs_directory
        / "evidence"
        / f"lumerical-material-mcclung-yang-{stamp}-{uuid4().hex[:8]}"
    )
    root.mkdir(parents=True, exist_ok=False)
    session, configuration_binding_reference = _prepare_evidence_root(
        root,
        config,
    )
    calls = {
        "session_opens": 0,
        "session_closes": 0,
        "version_reads": 0,
        "material_exists_reads": 0,
        "material_property_reads": 0,
        "tabulated_index_reads": 0,
        "fdtd_fit_index_reads": 0,
        **ZERO_ACTIVITY,
    }
    started_at = _timestamp()
    raw_engine = None
    engine = None
    primary_error: BaseException | None = None
    cleanup_error: BaseException | None = None
    samples: dict[str, LumericalMaterialSample] | None = None
    version: str | None = None
    try:
        assert config.python_api is not None
        raw_engine = open_engine(
            config.python_api,
            should_hide=True,
            license_server=config.license_server,
        )
        calls["session_opens"] += 1
        engine = ReadOnlyMaterialEngine(raw_engine, calls)
        version = str(engine.version())
        native_names = tuple(
            dict.fromkeys(
                native_name
                for _, materials in REQUESTS.values()
                for native_name in materials.values()
            )
        )
        missing = [
            native_name
            for native_name in native_names
            if not bool(engine.materialexists(native_name))
        ]
        if missing:
            raise RuntimeError("native_material_absent:" + ",".join(missing))
        samples = {}
        for request_name, (wavelength_nm, materials) in REQUESTS.items():
            samples[request_name] = _sample_materials(
                engine,
                materials,
                wavelengths_nm=(wavelength_nm,),
            )
            # Preserve each completed request before another native query,
            # session cleanup, or Authority post-processing can fail.  This
            # recovery object is not admission.
            _write_json_atomic(
                root / "raw-query-recovery.json",
                _raw_recovery(samples=samples, version=version, calls=calls),
            )
    except BaseException as error:
        primary_error = error
    finally:
        try:
            if engine is not None:
                engine.close()
            elif raw_engine is not None:
                raw_engine.close()
                calls["session_closes"] += 1
        except BaseException as error:
            cleanup_error = error

    if primary_error is not None or cleanup_error is not None:
        _write_json_atomic(
            root / "failure.json",
            {
                "activity": calls,
                "cleanup_error": (
                    None if cleanup_error is None else repr(cleanup_error)
                ),
                "primary_error": (
                    None if primary_error is None else repr(primary_error)
                ),
            },
        )
        if primary_error is not None and cleanup_error is not None:
            raise BaseExceptionGroup(
                "material_capture_and_cleanup_failed",
                [primary_error, cleanup_error],
            )
        raise primary_error if primary_error is not None else cleanup_error

    if calls["session_opens"] != 1 or calls["session_closes"] != 1:
        raise RuntimeError("material_session_not_exactly_once")
    if any(calls[name] for name in ZERO_ACTIVITY):
        raise RuntimeError("prohibited_activity_observed")

    assert samples is not None and version is not None
    _admit_and_export(
        root=root,
        session=session,
        configuration_binding_reference=configuration_binding_reference,
        samples=samples,
        version=version,
        calls=calls,
        started_at=started_at,
        library=library,
        config=config,
    )
    print(root)


def _require_research_environment() -> None:
    if Path(sys.executable).resolve() != EXPECTED_PYTHON:
        raise SystemExit(
            "research_env_python_required:"
            f"{EXPECTED_PYTHON}"
        )


def _load_config() -> LumericalConfig:
    environment = read_lumerical_environment(
        REPOSITORY / ".env.lumerical",
        inherited={},
    )
    config = LumericalConfig.from_environ(environment)
    if config.executable is None or config.executable.resolve() != FDTD_EXECUTABLE:
        raise RuntimeError("configured_fdtd_executable_changed")
    if config.python_api is None or config.python_api.resolve() != PYTHON_API:
        raise RuntimeError("configured_lumapi_changed")
    if config.license_utility is None:
        raise RuntimeError("configured_license_utility_missing")
    if config.runs_directory != config.runs_directory.resolve():
        raise RuntimeError("configured_runs_directory_not_absolute")
    return config


def _prepare_evidence_root(
    root: Path,
    config: LumericalConfig,
) -> tuple[AuthoritySession, Reference]:
    assert config.license_utility is not None
    configuration_binding = Document(
        "metacraft.evidence.lumerical_material_query_configuration_binding",
        {
            "api": _file_identity(PYTHON_API),
            "engine": _file_identity(FDTD_ENGINE),
            "executable": _file_identity(FDTD_EXECUTABLE),
            "license": {
                "server_is_configured": bool(config.license_server),
                "server_source": (
                    "explicit-environment"
                    if config.license_server
                    else "product-system-default"
                ),
                "utility": _file_identity(config.license_utility),
            },
            "python": _file_identity(EXPECTED_PYTHON),
            "query_contract": {
                "is_hidden": True,
                "is_material_read_only": True,
                "requests": {
                    request_name: {
                        "families": list(materials),
                        "native_names": list(materials.values()),
                        "wavelength_nm": wavelength_nm,
                    }
                    for request_name, (wavelength_nm, materials) in REQUESTS.items()
                },
                "zero_activity": ZERO_ACTIVITY,
            },
        },
    )
    authority = Authority(root / "authority")
    session = AuthoritySession(authority)
    configuration_binding_reference = session.admit_document(
        configuration_binding,
    )
    _write_json_atomic(
        root / "configuration-binding.json",
        json.loads(session.fetch(configuration_binding_reference)),
    )
    return session, configuration_binding_reference


def _raw_recovery(
    *,
    samples: dict[str, LumericalMaterialSample],
    version: str,
    calls: dict[str, int],
) -> dict[str, object]:
    return {
        "schema": "metacraft.evidence.lumerical_raw_material_recovery",
        "activity_at_capture": dict(calls),
        "is_complete": tuple(samples) == tuple(REQUESTS),
        "requests": {
            request_name: {
                "wavelength_nm": REQUESTS[request_name][0],
                "materials": {
                    family: material.as_mapping()
                    for family, material in sample.materials.items()
                },
            }
            for request_name, sample in samples.items()
        },
        "product_version": version,
    }


def _admit_and_export(
    *,
    root: Path,
    session: AuthoritySession,
    configuration_binding_reference: Reference,
    samples: dict[str, LumericalMaterialSample],
    version: str,
    calls: dict[str, int],
    started_at: str,
    library: SolverMaterialLibrary,
    config: LumericalConfig,
) -> None:
    binding = Document(
        "metacraft.evidence.lumerical_material_query_binding",
        {
            "configuration_binding_reference": (
                configuration_binding_reference.as_mapping()
            ),
            "product_version": version,
        },
    )
    binding_reference = session.admit_document(
        binding,
        references=(configuration_binding_reference,),
    )
    verifier = LumericalMaterialVerifier(
        session=session,
        config=config,
        binding_reference=binding_reference,
        probe=CapturedProbe(samples),
    )
    (root / "binding.json").write_bytes(session.fetch(binding_reference) + b"\n")
    references: dict[str, dict[str, object]] = {}
    for request_name, (wavelength_nm, materials) in REQUESTS.items():
        request = MaterialObservationRequest(tuple(materials), wavelength_nm)
        response = open_material_response(
            session=session,
            library=library,
            binding_reference=binding_reference,
            capacity_scope=(
                f"lumerical-fdtd/material-read-only/{request_name}"
            ),
            verify_materials=verifier.verify,
        )
        observation = response.observe(request)
        if isinstance(observation, MaterialUnavailable):
            raise RuntimeError(
                "material_unavailable:"
                f"{observation.reason.value}:{observation.family}"
            )
        sample_reference = observation.product_sample_reference
        observation_reference = observation.sample_reference
        (root / f"{request_name}-material-sample.json").write_bytes(
            session.fetch(sample_reference) + b"\n"
        )
        (root / f"{request_name}-material-observation.json").write_bytes(
            session.fetch(observation_reference) + b"\n"
        )

        references[request_name] = {
            "capacity_scope": response.context.capacity_scope,
            "material_sample": sample_reference.as_mapping(),
            "material_observation": observation_reference.as_mapping(),
        }

    _write_json_atomic(
        root / "restore-request.json",
        {
            "binding_reference": binding_reference.as_mapping(),
            "requests": {
                request_name: {
                    **references[request_name],
                    "families": list(materials),
                    "wavelength_nm": wavelength_nm,
                }
                for request_name, (wavelength_nm, materials) in REQUESTS.items()
            },
        },
    )
    _run_fresh_restore(root)

    _write_json(
        root / "provenance.json",
        {
            "schema": "metacraft.evidence.lumerical_material_query_provenance",
            "activity": calls,
            "completed_at": _timestamp(),
            "requests": {
                request_name: {
                    "families": materials,
                    "wavelength_nm": wavelength_nm,
                    "references": references[request_name],
                }
                for request_name, (wavelength_nm, materials) in REQUESTS.items()
            },
            "references": {
                "binding": binding_reference.as_mapping(),
            },
            "restore": {
                "fresh_process_completed": True,
                "material_observation_byte_exact": True,
                "material_sample_byte_exact": True,
            },
            "started_at": started_at,
        },
    )
    manifest = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "workspace.writer.lock":
            manifest[path.relative_to(root).as_posix()] = {
                "sha256": _hash(path),
                "size_bytes": path.stat().st_size,
            }
    _write_json(root / "manifest.json", {"files": manifest})


def _run_fresh_restore(root: Path) -> None:
    completed = subprocess.run(
        [
            str(EXPECTED_PYTHON),
            str(Path(__file__).resolve()),
            "--restore",
            str(root.resolve()),
        ],
        cwd=REPOSITORY,
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "fresh_process_restore_failed:"
            f"exit_{completed.returncode}"
        )
    result_path = root / "fresh-process-restore.json"
    if not result_path.is_file():
        raise RuntimeError("fresh_process_restore_receipt_missing")
    result = json.loads(result_path.read_bytes())
    if result != {
        "material_observation_byte_exact": True,
        "material_sample_byte_exact": True,
        "request_names": list(REQUESTS),
        "schema": "metacraft.evidence.lumerical_material_fresh_restore",
    }:
        raise RuntimeError("fresh_process_restore_receipt_invalid")


def _restore_in_fresh_process(root: Path) -> None:
    root = root.resolve(strict=True)
    request_path = root / "restore-request.json"
    authority_path = root / "authority"
    if not request_path.is_file() or not authority_path.is_dir():
        raise RuntimeError("fresh_restore_root_invalid")
    plan = json.loads(request_path.read_bytes())
    if not isinstance(plan, dict) or set(plan) != {
        "binding_reference",
        "requests",
    }:
        raise RuntimeError("fresh_restore_plan_invalid")
    binding_mapping = plan["binding_reference"]
    requests = plan["requests"]
    if not isinstance(binding_mapping, dict) or not isinstance(requests, dict):
        raise RuntimeError("fresh_restore_plan_invalid")
    if tuple(requests) != tuple(REQUESTS):
        raise RuntimeError("fresh_restore_request_set_changed")

    authority = Authority(authority_path)
    session = AuthoritySession(authority)
    binding_reference = Reference.from_mapping(binding_mapping)
    session.observe_admitted(binding_reference)
    for request_name, (expected_wavelength, expected_materials) in REQUESTS.items():
        value = requests[request_name]
        if not isinstance(value, dict) or set(value) != {
            "capacity_scope",
            "families",
            "material_observation",
            "material_sample",
            "wavelength_nm",
        }:
            raise RuntimeError("fresh_restore_request_invalid")
        if (
            value["families"] != list(expected_materials)
            or value["wavelength_nm"] != expected_wavelength
            or value["capacity_scope"]
            != f"lumerical-fdtd/material-read-only/{request_name}"
        ):
            raise RuntimeError("fresh_restore_request_changed")
        sample_mapping = value["material_sample"]
        observation_mapping = value["material_observation"]
        if not isinstance(sample_mapping, dict) or not isinstance(
            observation_mapping,
            dict,
        ):
            raise RuntimeError("fresh_restore_reference_invalid")
        sample_reference = Reference.from_mapping(sample_mapping)
        observation_reference = Reference.from_mapping(observation_mapping)
        restored_sample, restored_reference = restore_material_sample(
            authority,
            sample_reference=sample_reference,
        )
        request = MaterialObservationRequest(
            tuple(expected_materials),
            expected_wavelength,
        )
        restored_observation = RecordedMaterialResponse(
            session,
            context=_material_response_context(
                binding_reference=binding_reference,
                capacity_scope=value["capacity_scope"],
            ),
        ).observe(request)
        if isinstance(restored_observation, MaterialUnavailable):
            raise RuntimeError("fresh_restore_material_unavailable")
        if (
            restored_reference != sample_reference
            or restored_sample.to_document().to_bytes()
            != authority.fetch(sample_reference)
            or restored_observation.sample_reference != observation_reference
            or restored_observation.document().to_bytes()
            != authority.fetch(observation_reference)
        ):
            raise RuntimeError("fresh_restore_changed")
    _write_json_atomic(
        root / "fresh-process-restore.json",
        {
            "schema": "metacraft.evidence.lumerical_material_fresh_restore",
            "request_names": list(REQUESTS),
            "material_sample_byte_exact": True,
            "material_observation_byte_exact": True,
        },
    )


def _material_response_context(
    *,
    binding_reference: Reference,
    capacity_scope: object,
) -> object:
    # Keep the subprocess decoder beside the only place that needs it.
    from metacraft.materials.verification import MaterialResponseContext

    if not isinstance(capacity_scope, str):
        raise RuntimeError("fresh_restore_capacity_scope_invalid")
    return MaterialResponseContext(
        binding_reference=binding_reference,
        capacity_scope=capacity_scope,
    )


def _validate_retention_pipeline(
    library: SolverMaterialLibrary,
    config: LumericalConfig,
) -> None:
    if tuple(REQUESTS) != ("mcclung-550nm", "yang-1550nm"):
        raise RuntimeError("material_capture_request_set_changed")
    if tuple(REQUESTS["yang-1550nm"][1]) != (
        "silicon",
        "silicon dioxide",
    ):
        raise RuntimeError("yang_material_pair_changed")

    class FailingClose:
        def close(self) -> None:
            raise RuntimeError("synthetic_close_failure")

    close_calls = {"session_closes": 0}
    try:
        ReadOnlyMaterialEngine(FailingClose(), close_calls).close()
    except RuntimeError as error:
        if str(error) != "synthetic_close_failure":
            raise
    else:
        raise RuntimeError("synthetic_close_did_not_fail")
    if close_calls["session_closes"] != 0:
        raise RuntimeError("failed_close_counted_as_success")

    samples = {}
    for request_name, (wavelength_nm, native_names) in REQUESTS.items():
        frequency = Decimal(str(sample_frequency_hz(wavelength_nm)))
        materials = {}
        for family, native_name in native_names.items():
            materials[family] = NativeMaterialSample(
                family=family,
                native_name=native_name,
                fit_tolerance=Decimal("0.1"),
                fit_maximum_coefficients=6,
                minimum_tabulated_frequency_hz=Decimal("1"),
                maximum_tabulated_frequency_hz=Decimal("1e20"),
                points=(
                    NativeIndexPoint(
                        wavelength_nm=wavelength_nm,
                        frequency_hz=frequency,
                        refractive_index=(
                            Decimal("2")
                            if family in {"silicon nitride", "silicon"}
                            else Decimal("1.45")
                        ),
                        extinction_coefficient=Decimal("0"),
                        fit_residual=Decimal("0"),
                    ),
                ),
                findings=(),
            )
        samples[request_name] = LumericalMaterialSample(
            grid_wavelengths_nm=(wavelength_nm,),
            minimum_fit_frequency_hz=frequency,
            maximum_fit_frequency_hz=frequency,
            materials=materials,
        )
    with tempfile.TemporaryDirectory(prefix="metacraft-550-preflight-") as directory:
        root = Path(directory)
        session, configuration_binding_reference = _prepare_evidence_root(
            root,
            config,
        )
        _admit_and_export(
            root=root,
            session=session,
            configuration_binding_reference=configuration_binding_reference,
            samples=samples,
            version="synthetic-preflight-not-physical-truth",
            calls={"session_opens": 0, "session_closes": 0, **ZERO_ACTIVITY},
            started_at=_timestamp(),
            library=library,
            config=config,
        )


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _file_identity(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": _hash(path)}


def _write_json(path: Path, value: object) -> None:
    _write_json_atomic(path, value)


def _write_json_atomic(path: Path, value: object) -> None:
    payload = encode_bytes(value) + b"\n"
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()

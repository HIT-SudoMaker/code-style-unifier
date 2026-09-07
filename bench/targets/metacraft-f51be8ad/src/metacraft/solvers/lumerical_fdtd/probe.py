from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import math
from pathlib import Path
import re
import subprocess
from typing import TYPE_CHECKING, Any

import numpy

from ...canonical import encode_bytes
from ...external_activity import ExternalActivityClosure, _native_activity
from ...workstation import Demand, LANE_MEMORY_BYTES, plan

from .artifacts import RunDirectory
from .lane import SessionLease, SessionPool, WorkstationExecution
from .material import (
    LumericalMaterialSample,
    MaterialVerificationRefusal,
    MaterialVerificationRefusalKind,
    NativeIndexPoint,
    NativeMaterialSample,
    sample_frequency_hz,
)
from .qualification import (
    InstallationObservation,
    LicenseCapacity,
    LumericalConfig,
    LumericalUnavailable,
    PeriodicResponseQualification,
    PeriodicResponseProof,
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    _lumerical_absences,
)
from .project_execution import ExecutedProject
from .session import (
    _OptionalResult,
    open_engine,
)
from .time_budget import SolverTermination


if TYPE_CHECKING:
    from .template import PeriodicConstruction


class ProductProbe:
    """
    Observes one configured local FDTD installation conservatively.

    Observation (``observe``) reads version, resource, and license facts
    without constructing scientific geometry. ``verify_periodic_responses``
    performs each periodic response's own native fixture through the native
    session dialect as the engine acceptance check; it never runs during
    observation or license refresh.
    """

    def observe(self, config: LumericalConfig) -> InstallationObservation:
        """
        Read product version, resource, and license facts only.
        """

        if config.executable is None:
            raise ValueError("executable_required")
        if config.python_api is None:
            raise ValueError("python_api_required")
        if config.license_utility is None:
            raise LumericalUnavailable("license_utility_not_found")
        expected_executable = (
            config.python_api.parents[2] / "bin" / "fdtd-solutions.exe"
        )
        if (
            not expected_executable.is_file()
            or not config.executable.samefile(expected_executable)
        ):
            raise LumericalUnavailable("lumerical_installation_mismatch")
        if not config.license_utility.is_file():
            raise LumericalUnavailable("license_utility_not_found")
        engine = open_engine(
            config.python_api,
            should_hide=True,
            license_server=config.license_server,
        )
        try:
            resource = _cpu_resource(engine)
            estimate = engine.getlicenseestimate(
                "FDTD",
                str(resource["index"]),
            )
            solve_feature = _license_feature(str(estimate["feature"]))
            if solve_feature != "lumerical_solve":
                raise RuntimeError(
                    f"solve_license_feature_unexpected:{solve_feature}"
                )
            lumerical_gui_limit = _license_capacity(
                config,
                "lumerical_gui",
            )
            lumerical_solve_limit = _license_capacity(
                config,
                solve_feature,
            )
            license_observed_at = datetime.now(UTC)
            if (
                lumerical_gui_limit <= 0
                or lumerical_solve_limit <= 0
            ):
                raise LumericalUnavailable("license_unavailable")
            engine.checkout(solve_feature)
            processes = int(resource["processes"])
            threads = int(resource["threads"])
            product_version = str(engine.version())
            api_identity = _file_identity(config.python_api)
            resource_identity = (
                f"{resource['name']}/cpu/"
                f"processes-{processes}/threads-{threads}"
            )
        except BaseException as primary:
            try:
                engine.close()
            except BaseException as cleanup:
                raise BaseExceptionGroup(
                    "lumerical_installation_observation_failed",
                    [primary, cleanup],
                ) from primary
            raise
        engine.close()
        return InstallationObservation(
            product_version=product_version,
            api_identity=api_identity,
            lumerical_gui_limit=lumerical_gui_limit,
            lumerical_solve_limit=lumerical_solve_limit,
            resource_identity=resource_identity,
            observed_at=license_observed_at,
            activity_closure=_native_activity(
                product_session_count=1,
            ),
        )

    def verify_periodic_responses(
        self,
        config: LumericalConfig,
    ) -> PeriodicResponseProof:
        """
        Prove each periodic response through its own native fixture.
        """

        return verify_periodic_responses(config)

    def sample_materials(
        self,
        config: LumericalConfig,
        catalogue: Mapping[str, str],
        wavelength_nm: int,
    ) -> tuple[
        LumericalMaterialSample | MaterialVerificationRefusal,
        ExternalActivityClosure,
    ]:
        """
        Sample only one task's exact native materials and wavelength.
        """

        if config.python_api is None:
            raise ValueError("python_api_required")
        engine = open_engine(
            config.python_api,
            should_hide=True,
            license_server=config.license_server,
        )
        try:
            outcome: LumericalMaterialSample | MaterialVerificationRefusal
            for family, native_name in catalogue.items():
                if not bool(engine.materialexists(native_name)):
                    outcome = MaterialVerificationRefusal(
                        kind=(
                            MaterialVerificationRefusalKind
                            .NATIVE_MATERIAL_ABSENT
                        ),
                        family=family,
                        native_name=native_name,
                        wavelength_nm=wavelength_nm,
                    )
                    break
            else:
                outcome = _sample_materials(
                    engine,
                    catalogue,
                    wavelengths_nm=(wavelength_nm,),
                )
        except BaseException as primary:
            try:
                engine.close()
            except BaseException as cleanup:
                raise BaseExceptionGroup(
                    "lumerical_material_sampling_failed",
                    [primary, cleanup],
                ) from primary
            raise
        engine.close()
        return outcome, _native_activity(product_session_count=1)

    def refresh_capacity(
        self,
        config: LumericalConfig,
    ) -> LicenseCapacity:
        """
        Refresh only the transient license fact of an established binding.
        """

        if config.license_utility is None:
            raise LumericalUnavailable("license_utility_not_found")
        if not config.license_utility.is_file():
            raise LumericalUnavailable("license_utility_not_found")
        lumerical_gui_limit = _license_capacity(
            config,
            "lumerical_gui",
        )
        lumerical_solve_limit = _license_capacity(
            config,
            "lumerical_solve",
        )
        if lumerical_gui_limit <= 0 or lumerical_solve_limit <= 0:
            raise LumericalUnavailable("license_unavailable")
        return LicenseCapacity(
            lumerical_gui_limit=lumerical_gui_limit,
            lumerical_solve_limit=lumerical_solve_limit,
            observed_at=datetime.now(UTC),
        )


def _cpu_resource(engine: Any) -> dict[str, str | int]:
    count = int(engine.getresource("FDTD"))
    for index in range(1, count + 1):
        active = str(engine.getresource("FDTD", index, "active"))
        device = str(engine.getresource("FDTD", index, "device type"))
        if active != "1" or device.upper() != "CPU":
            continue
        return {
            "capacity": str(engine.getresource("FDTD", index, "capacity")),
            "index": index,
            "name": str(engine.getresource("FDTD", index, "name")),
            "processes": str(engine.getresource("FDTD", index, "processes")),
            "threads": str(engine.getresource("FDTD", index, "threads")),
            "total cores": str(engine.getresource("FDTD", index, "total cores")),
        }
    raise RuntimeError("active_cpu_resource_missing")


def _file_identity(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _license_feature(requirement: str) -> str:
    parts = requirement.split()
    if not parts:
        raise RuntimeError("license_requirement_missing")
    if parts[0].isdigit():
        if len(parts) < 2:
            raise RuntimeError("license_feature_missing")
        return parts[1]
    return parts[0]


def _sample_materials(
    engine: Any,
    catalogue: Mapping[str, str],
    *,
    wavelengths_nm: tuple[int, ...],
) -> LumericalMaterialSample:
    frequencies = tuple(
        sample_frequency_hz(wavelength)
        for wavelength in wavelengths_nm
    )
    span = min(frequencies), max(frequencies)
    materials = {}
    for family, native_name in catalogue.items():
        materials[family] = _sample_material(
            engine,
            family=family,
            native_name=native_name,
            wavelengths_nm=wavelengths_nm,
            frequencies=frequencies,
            fit_span=span,
        )
    return LumericalMaterialSample(
        grid_wavelengths_nm=wavelengths_nm,
        minimum_fit_frequency_hz=Decimal(str(span[0])),
        maximum_fit_frequency_hz=Decimal(str(span[1])),
        materials=materials,
    )


def _sample_material(
    engine: Any,
    *,
    family: str,
    native_name: str,
    wavelengths_nm: tuple[int, ...],
    frequencies: tuple[float, ...],
    fit_span: tuple[float, float],
) -> NativeMaterialSample:
    table = numpy.asarray(
        engine.getmaterial(native_name, "sampled data")
    )
    if table.ndim != 2 or table.shape[0] < 2 or table.shape[1] < 2:
        raise RuntimeError(f"material_table_unreadable:{native_name}")
    tabulated_frequencies = numpy.real(table[:, 0]).astype(float)
    tabulated_band = (
        float(tabulated_frequencies.min()),
        float(tabulated_frequencies.max()),
    )
    covered = tuple(
        (wavelength, frequency)
        for wavelength, frequency in zip(
            wavelengths_nm,
            frequencies,
            strict=True,
        )
        if tabulated_band[0] <= frequency <= tabulated_band[1]
    )
    findings = tuple(
        f"wavelength_out_of_band:{wavelength}"
        for wavelength, frequency in zip(
            wavelengths_nm,
            frequencies,
            strict=True,
        )
        if not tabulated_band[0] <= frequency <= tabulated_band[1]
    )
    points = _sample_points(
        engine,
        native_name=native_name,
        covered=covered,
        fit_span=fit_span,
    )
    return NativeMaterialSample(
        family=family,
        native_name=native_name,
        fit_tolerance=Decimal(
            str(float(engine.getmaterial(native_name, "tolerance")))
        ),
        fit_maximum_coefficients=_fit_maximum_coefficients(
            engine,
            native_name,
        ),
        minimum_tabulated_frequency_hz=Decimal(str(tabulated_band[0])),
        maximum_tabulated_frequency_hz=Decimal(str(tabulated_band[1])),
        points=points,
        findings=findings,
    )


def _sample_points(
    engine: Any,
    *,
    native_name: str,
    covered: tuple[tuple[int, float], ...],
    fit_span: tuple[float, float],
) -> tuple[NativeIndexPoint, ...]:
    if not covered:
        return ()
    requested = numpy.asarray(
        [frequency for _, frequency in covered],
        dtype=float,
    )
    recorded = numpy.asarray(
        engine.getindex(native_name, requested)
    ).reshape(-1)
    fitted = numpy.asarray(
        engine.getfdtdindex(
            native_name,
            requested,
            fit_span[0],
            fit_span[1],
        )
    ).reshape(-1)
    if len(recorded) != len(covered) or len(fitted) != len(covered):
        raise RuntimeError(f"material_index_shape_invalid:{native_name}")
    points = []
    for grid_point, table_value, fit_value in zip(
        covered,
        recorded,
        fitted,
        strict=True,
    ):
        points.append(
            _index_point(
                grid_point,
                complex(table_value),
                complex(fit_value),
            )
        )
    return tuple(points)


def _index_point(
    grid_point: tuple[int, float],
    table_value: complex,
    fit_value: complex,
) -> NativeIndexPoint:
    wavelength_nm, frequency_hz = grid_point
    residual = abs(fit_value - table_value)
    if not all(
        math.isfinite(component)
        for component in (
            table_value.real,
            table_value.imag,
            residual,
        )
    ):
        raise RuntimeError(f"material_index_not_finite:{wavelength_nm}")
    return NativeIndexPoint(
        wavelength_nm=wavelength_nm,
        frequency_hz=Decimal(str(frequency_hz)),
        refractive_index=Decimal(str(table_value.real)),
        extinction_coefficient=Decimal(str(table_value.imag)),
        fit_residual=Decimal(str(residual)),
    )


def _fit_maximum_coefficients(engine: Any, native_name: str) -> int:
    try:
        value = engine.getmaterial(native_name, "max coefficients")
    except Exception:
        value = engine.getmaterial(native_name, "max coefficient")
    return int(float(value))


def parse_license_capacity(status: str) -> int:
    """
    Read remaining seats from one FlexNet feature report.
    """

    match = re.search(
        r"Total of (\d+) licenses? issued;\s+"
        r"Total of (\d+) licenses? in use",
        status,
    )
    if match is None:
        raise RuntimeError("license_capacity_unreadable")
    issued, in_use = (int(value) for value in match.groups())
    return max(0, issued - in_use)


def _license_capacity(
    config: LumericalConfig,
    feature: str,
) -> int:
    if (
        config.license_utility is None
        or not config.license_utility.is_file()
    ):
        raise LumericalUnavailable("license_utility_not_found")
    if config.license_server is None:
        raise ValueError("license_capacity_configuration_incomplete")
    try:
        result = subprocess.run(
            (
                str(config.license_utility),
                "lmstat",
                "-f",
                feature,
                "-c",
                config.license_server,
            ),
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as error:
        raise LumericalUnavailable(
            "license_utility_not_found"
        ) from error
    return parse_license_capacity(f"{result.stdout}\n{result.stderr}")


def verify_periodic_responses(
    config: LumericalConfig,
) -> PeriodicResponseProof:
    """
    Qualify each periodic response through its own native fixture.

    Periodic transmission is proven by one propagation construction, engine
    execution, and a finite complex-transmission observation. Periodic
    polarization is proven by both independent input bases needed for one
    finite Jones response. Each fixture runs independently inside one placed
    lane; the failure of one never suppresses the proven sibling. The shared
    session pool is closed on every outcome.
    """

    from .template import prepare_qualification_constructions

    if (
        config.executable is None
        or config.python_api is None
        or config.license_server is None
    ):
        raise ValueError("execution_configuration_required")
    layout = plan(
        Demand(workers=1, worker_memory_bytes=LANE_MEMORY_BYTES)
    )
    if not layout.lanes:
        raise RuntimeError("qualification_lane_unavailable")
    execution = WorkstationExecution(
        config.python_api,
        config.license_server,
    )
    sessions = SessionPool(execution, layout.lanes[:1])
    directory = _qualification_directory(config.runs_directory)
    constructions = prepare_qualification_constructions(
        atom_material="<Object defined dielectric>",
        substrate_material="<Object defined dielectric>",
    )
    failures: list[Exception] = []
    activity_closure = None
    try:
        periodic_outputs = _attempt_output(
            lambda: _periodic_outputs(
                sessions,
                directory / "transmission",
                constructions.transmission,
            ),
            failures,
        )
        transmission_qualification = (
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_TRANSMISSION_RESPONSE
            )
            if periodic_outputs is None
            else _attempt_response_qualification(
                lambda: _qualify_returned_response(
                    PERIODIC_TRANSMISSION_RESPONSE,
                    periodic_outputs["transmission"],
                    _validate_transmission_response,
                ),
                response_kind=PERIODIC_TRANSMISSION_RESPONSE,
                failures=failures,
            )
        )
        reference_surface_qualification = (
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            )
            if periodic_outputs is None
            else _attempt_response_qualification(
                lambda: _qualify_returned_response(
                    PERIODIC_REFERENCE_SURFACE_RESPONSE,
                    periodic_outputs["reference_surface"],
                    lambda value: _validate_reference_surface_response(
                        value,
                        constructions.transmission,
                    ),
                ),
                response_kind=PERIODIC_REFERENCE_SURFACE_RESPONSE,
                failures=failures,
            )
        )
        polarization_qualification = _attempt_response_qualification(
            lambda: _qualify_polarization_response(
                sessions,
                directory / "polarization",
                constructions.polarization,
            ),
            response_kind=PERIODIC_POLARIZATION_RESPONSE,
            failures=failures,
        )
    except BaseException as primary:
        try:
            sessions.close()
        except BaseException as cleanup:
            raise BaseExceptionGroup(
                "periodic_response_fixture_terminalization_failed",
                [primary, cleanup],
            ) from primary
        raise
    try:
        activity_closure = sessions.close()
    except BaseException as cleanup:
        _raise_fixture_failures(
            failures,
            cleanup_failure=cleanup,
        )
    _raise_fixture_failures(failures, cleanup_failure=None)
    if activity_closure is None:
        raise RuntimeError("qualification_activity_closure_missing")
    return PeriodicResponseProof(
        response_qualifications=(
            transmission_qualification,
            polarization_qualification,
            reference_surface_qualification,
        ),
        activity_closure=activity_closure,
    )


def _attempt_output(
    observe: Callable[[], dict[str, Any]],
    failures: list[Exception],
) -> dict[str, Any] | None:
    """
    Acquire one shared native solve before independent response validation.
    """

    try:
        return observe()
    except Exception as error:
        failures.append(error)
        return None


def _attempt_response_qualification(
    qualify_response: Callable[[], PeriodicResponseQualification],
    *,
    response_kind: str,
    failures: list[Exception],
) -> PeriodicResponseQualification:
    """
    Attempt one sibling result while retaining faults for terminalization.
    """

    try:
        return qualify_response()
    except Exception as error:
        failures.append(error)
        return PeriodicResponseQualification.response_not_returned(
            response_kind
        )


def _raise_fixture_failures(
    failures: list[Exception],
    *,
    cleanup_failure: BaseException | None,
) -> None:
    """
    Raise implementation drift before expected product absence.

    Both siblings have already been attempted and the shared pool has already
    closed. A programming or invariant failure must never hide behind a
    simultaneous product absence. Multiple implementation failures remain one
    ordinary ``ExceptionGroup``; no solver-specific hierarchy is invented.
    """

    if cleanup_failure is not None:
        if not failures:
            raise cleanup_failure
        raise BaseExceptionGroup(
            "periodic_response_fixture_terminalization_failed",
            [*failures, cleanup_failure],
        )

    absent: list[LumericalUnavailable] = []
    unexpected: list[Exception] = []
    for error in failures:
        absences = _lumerical_absences(error)
        if absences is None:
            unexpected.append(error)
        else:
            absent.extend(absences)
    if len(unexpected) == 1:
        raise unexpected[0]
    if unexpected:
        raise ExceptionGroup(
            "periodic_response_fixture_failed",
            unexpected,
        )
    if absent:
        first = absent[0]
        for sibling in absent[1:]:
            first.add_note(
                "Sibling periodic response was also unavailable: "
                f"{sibling.reason}"
            )
        raise first


def _periodic_outputs(
    sessions: SessionPool,
    directory: Path,
    construction: PeriodicConstruction,
) -> dict[str, _OptionalResult]:
    """
    Acquire one solve, then read G0 and the sampled surface independently.
    """

    return _solve_fixture(
        sessions,
        directory,
        construction,
        lambda session: {
            "transmission": _optional_result(
                session,
                "propagation",
            ),
            "reference_surface": _optional_result(
                session,
                "reference_surface",
            ),
        },
    )


def _qualify_returned_response(
    response_kind: str,
    outcome: _OptionalResult,
    validate: Callable[[object], None],
) -> PeriodicResponseQualification:
    """
    Close one response as qualified or explicitly not returned.
    """

    if outcome.response is None:
        return PeriodicResponseQualification.response_not_returned(
            response_kind
        )
    validate(outcome.response)
    return PeriodicResponseQualification.qualified(response_kind)


def _validate_transmission_response(response: object) -> None:
    """
    Validate only the finite G0 transmission observation.
    """

    if not isinstance(response, Mapping):
        raise TypeError("periodic_transmission_response_mapping_required")
    coefficient = complex(response["complex_transmission"])
    power = float(response["power_transmission"])
    if not (
        math.isfinite(coefficient.real)
        and math.isfinite(coefficient.imag)
        and math.isfinite(power)
        and 0 <= power <= 1
    ):
        raise ValueError("periodic_transmission_response_invalid")


def _validate_reference_surface_response(
    value: object,
    construction: PeriodicConstruction,
) -> None:
    """
    Qualify only an exact finite sampled patch returned by the native solve.
    """

    from ...authority.reference import reference_for
    from ...field.reference_surface import RequestedInputBasis
    from ...field.sample import Medium
    from .reference_surface import (
        decode_reference_surface,
        periodic_reference_surface_request,
    )

    if not isinstance(value, Mapping):
        raise TypeError("reference_surface_response_mapping_required")
    expected = periodic_reference_surface_request(
        value,
        wavelength_m=construction.wavelength_nm * 1e-9,
        period_m=construction.period_nm * 1e-9,
        transmission_plane_m=(
            construction.transmission_plane_z_nm * 1e-9
        ),
        medium=Medium("transmission medium"),
        requested_input_basis=(
            RequestedInputBasis.X_LINEAR
            if construction.incident_axis == "x"
            else RequestedInputBasis.Y_LINEAR
        ),
        order_regime="multi order",
        source_references=(reference_for(b"qualification fixture"),),
    )
    decode_reference_surface(value, expected=expected)


def _qualify_polarization_response(
    sessions: SessionPool,
    directory: Path,
    constructions: tuple[PeriodicConstruction, ...],
) -> PeriodicResponseQualification:
    """
    Prove one finite periodic polarization response from both input bases.

    A finite Jones response needs both independent input bases. Each geometric
    construction is executed once through the linear-transmission observation;
    the fixture qualifies polarization only when every basis yields finite
    output on both orthogonal components. A one-basis or non-finite result
    cannot qualify the polarization response.
    """

    if (
        len(constructions) != 2
        or {construction.incident_axis for construction in constructions}
        != {"x", "y"}
    ):
        raise RuntimeError("polarization_qualification_constructions_invalid")
    is_response_complete = True
    for construction in constructions:
        outcome = _run_fixture(
            sessions,
            directory / f"{construction.incident_axis}-input",
            construction,
            "linear_transmission",
        )
        if outcome.response is None:
            is_response_complete = False
            continue
        response = outcome.response
        if not isinstance(response, Mapping):
            raise TypeError("periodic_polarization_response_mapping_required")
        output_x = complex(response["output_x"])
        output_y = complex(response["output_y"])
        if not (
            math.isfinite(output_x.real)
            and math.isfinite(output_x.imag)
            and math.isfinite(output_y.real)
            and math.isfinite(output_y.imag)
        ):
            raise ValueError("periodic_polarization_response_invalid")
    if is_response_complete:
        return PeriodicResponseQualification.qualified(
            PERIODIC_POLARIZATION_RESPONSE
        )
    return PeriodicResponseQualification.response_not_returned(
        PERIODIC_POLARIZATION_RESPONSE
    )


def _qualification_directory(runs_directory: Path) -> Path:
    root = runs_directory.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    directory = root / f"lumerical-qualification-{timestamp}"
    directory.mkdir()
    return directory


def _run_fixture(
    sessions: SessionPool,
    directory: Path,
    construction: PeriodicConstruction,
    result_name: str,
) -> _OptionalResult:
    return _solve_fixture(
        sessions,
        directory,
        construction,
        lambda session: _optional_result(session, result_name),
    )


def _solve_fixture(
    sessions: SessionPool,
    directory: Path,
    construction: PeriodicConstruction,
    observe: Callable[[Any], Any],
) -> Any:
    """
    Construct and close one qualification fixture within the reviewed ladder.
    """

    directory.mkdir(parents=True)
    run = RunDirectory(directory)
    with sessions.lease() as lease:
        session = lease.session
        manifest = construction.build_in(session)
        if manifest.mismatches:
            raise RuntimeError("execution_fixture_construction_mismatch")
        completed, termination = _solve_qualification_attempt(
            sessions,
            lease,
            run,
            directory,
        )
        if termination.outcome == "maximum_time":
            run.archive_ordinary_attempt(directory)
            session.change_maximum_time(
                "solver",
                construction.time_budget.extended_maximum_fs,
            )
            completed, termination = _solve_qualification_attempt(
                sessions,
                lease,
                run,
                directory,
            )
        if termination.outcome == "diverged":
            raise RuntimeError("periodic_qualification_solver_diverged")
        if termination.outcome != "autoshutoff":
            raise RuntimeError(
                "periodic_qualification_time_budget_exhausted"
            )
        return observe(completed.session)


def _solve_qualification_attempt(
    sessions: SessionPool,
    lease: SessionLease,
    run: RunDirectory,
    directory: Path,
) -> tuple[ExecutedProject, SolverTermination]:
    """
    Retain one native qualification attempt and its stop evidence.
    """

    before, after = run.native_projects(directory)
    completed = sessions.solve(lease, before, after)
    run.record_execution(directory, completed.execution)
    raw_termination = completed.session.result("solver", "termination")
    if not isinstance(raw_termination, Mapping):
        raise TypeError("solver_termination_mapping_required")
    termination = SolverTermination.from_mapping(raw_termination)
    run.record_current_termination(
        directory,
        termination.as_mapping(),
    )
    return completed, termination


def _optional_result(
    session: Any,
    result_name: str,
) -> _OptionalResult:
    """
    Preserve only the explicit internal response-not-returned value.
    """

    outcome = session.optional_result("grating_response", result_name)
    if type(outcome) is not _OptionalResult:
        raise TypeError("optional_result_required")
    return outcome

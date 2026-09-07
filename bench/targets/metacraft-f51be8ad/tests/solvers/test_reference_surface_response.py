from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
import json
import math
from pathlib import Path

import numpy
import pytest
import torch

import metacraft.solvers.lumerical_fdtd.probe as probe_module
import metacraft.field.reference_surface as reference_surface_module
from metacraft.authority import Document, Reference
from metacraft.authority.reference import reference_for
from metacraft.canonical import encode_bytes
from metacraft.field.reference_surface import (
    AdmittedReferenceSurface,
    LOCALLY_PERIODIC,
    ReferenceSurfaceResponse,
    RequestedInputBasis,
    compare_reference_surfaces,
    restore_reference_surface,
)
from metacraft.field.rectilinear import RectilinearPlane
from metacraft.field.sample import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from metacraft.science.metalens.aperture import (
    Aperture,
    Cell,
    Circle,
    Material,
    Response,
    State,
    form_reference_surface_field,
    reference_surface_cautions,
)
from metacraft.solvers.lumerical_fdtd.artifacts import WorkRecord
from metacraft.solvers.lumerical_fdtd.lane import (
    SessionPool as NativeSessionPool,
)
from metacraft.solvers.lumerical_fdtd.qualification import (
    LumericalBinding,
    PERIODIC_POLARIZATION_RESPONSE,
    PERIODIC_REFERENCE_SURFACE_RESPONSE,
    PERIODIC_TRANSMISSION_RESPONSE,
    PeriodicResponseQualification,
    PeriodicResponseProof,
)
from metacraft.solvers.lumerical_fdtd.reference_surface import (
    ReferenceSurfaceRequest,
    decode_reference_surface,
    periodic_reference_surface_request,
)
from metacraft.solvers.lumerical_fdtd.session import LumericalSession
from tests.lumerical_fixtures import (
    lumerical_config,
    workstation_layout,
)
from tests.solver_fakes import ActiveEngines, FakeSessionFactory


def _now():
    from datetime import UTC, datetime

    return datetime(2026, 7, 30, tzinfo=UTC)


def _samples(values: object) -> numpy.ndarray:
    array = numpy.asarray(values, dtype="<c16", order="C")
    array.setflags(write=False)
    return array


def _request(source: Reference) -> ReferenceSurfaceRequest:
    return ReferenceSurfaceRequest(
        wavelength_m=400e-9,
        surface=RectilinearPlane(
            position_m=1e-6,
            horizontal_coordinates_m=numpy.asarray((-200e-9, 0.0, 200e-9)),
            vertical_coordinates_m=numpy.asarray((-200e-9, 0.0, 200e-9)),
        ),
        frame=CoordinateFrame(),
        medium=Medium("transmission medium"),
        output_basis=ComponentBasis.TRANSVERSE_LINEAR,
        requested_input_basis=RequestedInputBasis.X_LINEAR,
        order_regime="multi order",
        source_references=(source,),
        incident_reference_power=1.0,
    )


def _raw_patch(
    x: tuple[tuple[complex, complex], tuple[complex, complex]] = (
        (1 + 0j, 2 + 1j),
        (3 - 1j, 4 + 0j),
    ),
) -> dict[str, object]:
    def component(
        values: tuple[tuple[complex, complex], tuple[complex, complex]],
    ) -> dict[str, object]:
        closed = (
            (values[0][0], values[0][1], values[0][0]),
            (values[1][0], values[1][1], values[1][0]),
            (values[0][0], values[0][1], values[0][0]),
        )
        return {
            "imaginary": [
                [value.imag for value in row] for row in closed
            ],
            "real": [[value.real for value in row] for row in closed],
        }

    zero = ((0j, 0j), (0j, 0j))
    return {
        "electric_components": {
            "x": component(x),
            "y": component(zero),
        },
        "frame": {
            "normal_axis": "z",
            "propagation_direction": "positive",
            "sample_order": ["y", "x"],
        },
        "incident_reference_power": "1",
        "medium": "transmission medium",
        "order_regime": "multi order",
        "output_basis": "transverse linear",
        "requested_input_basis": "x linear",
        "surface": {
            "position_m": "9e-7",
            "x_coordinates_m": ["-3.3e-7", "0", "3.3e-7"],
            "y_coordinates_m": ["-3.3e-7", "0", "3.3e-7"],
        },
        "transmitted_power": "0.75",
        "wavelength_m": "4e-7",
    }


def _exact_raw_patch() -> dict[str, object]:
    value = _raw_patch()
    value["surface"] = {
        "position_m": "1e-6",
        "x_coordinates_m": ["-2e-7", "0", "2e-7"],
        "y_coordinates_m": ["-2e-7", "0", "2e-7"],
    }
    return value


def _field(
    values: object,
    source: Reference,
) -> Field:
    return Field(
        wavelength_m=400e-9,
        surface=PlaneSurface(1e-6, 200e-9, (2, 2)),
        frame=CoordinateFrame(),
        medium=Medium("transmission medium"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            FieldComponent("x", _samples(values)),
            FieldComponent("y", _samples(numpy.zeros((2, 2)))),
        ),
        source_references=(source,),
        incident_reference_power=1.0,
    )


def _response(values: object, source: Reference) -> ReferenceSurfaceResponse:
    return ReferenceSurfaceResponse(
        field=_field(values, source),
        requested_input_basis=RequestedInputBasis.X_LINEAR,
        order_regime="multi order",
        transmitted_power=0.75,
    )


def _patch_store() -> tuple[
    dict[Reference, bytes],
    object,
    object,
]:
    objects: dict[Reference, bytes] = {}

    def admit_object(
        body: bytes,
        *,
        media_type: str,
        descriptive_metadata: Mapping[str, object],
    ) -> Reference:
        reference = reference_for(
            body,
            media_type=media_type,
            descriptive_metadata=descriptive_metadata,
        )
        objects[reference] = body
        return reference

    def admit_document(
        document: Document,
        *,
        references: tuple[Reference, ...],
    ) -> Reference:
        assert references
        body = document.to_bytes()
        reference = reference_for(body)
        objects[reference] = body
        return reference

    return objects, admit_object, admit_document


def _aperture(source: Reference) -> Aperture:
    axis = numpy.asarray((-400, 0, 400))
    x, y = numpy.meshgrid(axis, axis)
    coordinates = numpy.stack((x, y), axis=-1)
    occupied = numpy.hypot(x, y) <= 400
    identities = numpy.full((3, 3), "", dtype="<U3")
    identities[occupied] = ("one", "two", "one", "two", "one")
    target = numpy.zeros((3, 3))
    cell = Cell(
        identity="cell",
        atom=Material("silicon", "fixture"),
        substrate=Material("silica", "fixture"),
        period_nm=400,
        height_nm=600,
        geometry=Circle(100),
        source=source,
    )

    def state(identity: str) -> State:
        return State(
            identity=identity,
            cell_identity="cell",
            responses=(
                Response(
                    channel="x",
                    real_part=Decimal(1),
                    imaginary_part=Decimal(0),
                    power=Decimal(1),
                ),
            ),
            source=source,
            target_phase=Decimal(0),
            realized_phase=Decimal(0),
            useful_power=Decimal(1),
            leakage_power=Decimal(0),
        )

    return Aperture(
        cells=(cell,),
        states=(state("one"), state("two")),
        coordinates_nm=coordinates,
        is_occupied=occupied,
        target_phase=target,
        state_identities=identities,
        spacing_nm=400,
        half_span_nm=400,
        evidence=(source,),
    )


def test_reference_surface_capability_is_an_independent_sibling() -> None:
    proof = PeriodicResponseProof(
        response_qualifications=(
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_TRANSMISSION_RESPONSE
            ),
            PeriodicResponseQualification.response_not_returned(
                PERIODIC_POLARIZATION_RESPONSE
            ),
            PeriodicResponseQualification.qualified(
                PERIODIC_REFERENCE_SURFACE_RESPONSE
            ),
        ),
    )

    assert proof.capabilities == (PERIODIC_REFERENCE_SURFACE_RESPONSE,)
    assert PeriodicResponseProof(
        response_qualifications=(
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
    ).capabilities == (
        PERIODIC_TRANSMISSION_RESPONSE,
        PERIODIC_POLARIZATION_RESPONSE,
    )


def test_capabilities_have_no_reverse_evidence_constructor() -> None:
    assert not hasattr(PeriodicResponseProof, "from_capabilities")
    assert not hasattr(LumericalBinding, "from_capabilities")


def test_binding_round_trip_persists_ordered_redacted_response_results(
    tmp_path: Path,
) -> None:
    response_qualifications = (
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
    binding = LumericalBinding(
        executable=str(tmp_path / "fdtd-solutions.exe"),
        engine=str(tmp_path / "fdtd-engine.exe"),
        python_api=str(tmp_path / "lumapi.py"),
        product_version="2026 r1",
        api_identity="fixture-api",
        license_server="fixture-license",
        resource_identity="fixture-cpu",
        response_qualifications=response_qualifications,
    )

    encoded = binding.as_mapping()

    assert encoded["response_qualifications"] == (
        {
            "response_kind": PERIODIC_TRANSMISSION_RESPONSE,
            "status": "qualified",
        },
        {
            "response_kind": PERIODIC_POLARIZATION_RESPONSE,
            "status": "response_not_returned",
        },
        {
            "response_kind": PERIODIC_REFERENCE_SURFACE_RESPONSE,
            "status": "qualified",
        },
    )
    forbidden = {
        "exception",
        "lane",
        "machine",
        "path",
        "payload",
        "process",
        "session",
    }
    for result in encoded["response_qualifications"]:
        assert set(result).isdisjoint(forbidden)
    restored = LumericalBinding.from_mapping(
        json.loads(encode_bytes(encoded))
    )
    assert restored == binding
    assert restored.as_mapping() == encoded


def test_binding_has_fixed_canonical_qualification_bytes() -> None:
    binding = LumericalBinding(
        executable="fixture/fdtd-solutions.exe",
        engine="fixture/fdtd-engine.exe",
        python_api="fixture/lumapi.py",
        product_version="2026 r1",
        api_identity="fixture-api",
        license_server="fixture-license",
        resource_identity="fixture-cpu",
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
        ),
    )

    assert encode_bytes(binding.as_mapping()) == (
        b'{"api_identity":"fixture-api",'
        b'"engine":"fixture/fdtd-engine.exe",'
        b'"executable":"fixture/fdtd-solutions.exe",'
        b'"license_server":"fixture-license",'
        b'"native_license_features":["lumerical_gui","lumerical_solve"],'
        b'"product_version":"2026 r1",'
        b'"python_api":"fixture/lumapi.py",'
        b'"resource_identity":"fixture-cpu",'
        b'"response_qualifications":['
        b'{"response_kind":"periodic_transmission_response",'
        b'"status":"qualified"},'
        b'{"response_kind":"periodic_polarization_response",'
        b'"status":"response_not_returned"},'
        b'{"response_kind":"periodic_reference_surface_response",'
        b'"status":"qualified"}]}'
    )


def test_periodic_surface_request_owns_the_declared_medium_context() -> None:
    source = reference_for(b"qualification surface")

    request = periodic_reference_surface_request(
        _exact_raw_patch(),
        wavelength_m=400e-9,
        period_m=400e-9,
        transmission_plane_m=1e-6,
        medium=Medium("transmission medium"),
        requested_input_basis=RequestedInputBasis.X_LINEAR,
        order_regime="multi order",
        source_references=(source,),
    )

    assert request.medium == Medium("transmission medium")
    assert request.surface == RectilinearPlane(
        position_m=1e-6,
        horizontal_coordinates_m=numpy.asarray((-200e-9, 0.0, 200e-9)),
        vertical_coordinates_m=numpy.asarray((-200e-9, 0.0, 200e-9)),
    )


def test_nearest_mesh_cell_position_cannot_replace_the_declared_t_plane() -> None:
    source = reference_for(b"nearest mesh surface")
    value = _exact_raw_patch()
    value["surface"] = {
        "position_m": "6.04347826e-7",
        "x_coordinates_m": ["-2e-7", "0", "2e-7"],
        "y_coordinates_m": ["-2e-7", "0", "2e-7"],
    }

    with pytest.raises(
        ValueError,
        match="reference_surface_construction_mismatch",
    ):
        periodic_reference_surface_request(
            value,
            wavelength_m=400e-9,
            period_m=400e-9,
            transmission_plane_m=600e-9,
            medium=Medium("transmission medium"),
            requested_input_basis=RequestedInputBasis.X_LINEAR,
            order_regime="multi order",
            source_references=(source,),
        )


def test_reference_surface_is_validated_before_recovery() -> None:
    source = reference_for(b"period choice")

    with pytest.raises(
        ValueError,
        match="reference_surface_observation_mismatch",
    ):
        decode_reference_surface(
            _raw_patch(),
            expected=_request(source),
        )

    assert _request(source).source_references == (source,)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value["electric_components"]["x"]["real"].__setitem__(
            0,
            [math.nan, 0],
        ),
        lambda value: value.__setitem__("requested_input_basis", "y linear"),
        lambda value: value["surface"].__setitem__("position_m", "2e-6"),
        lambda value: value.__setitem__("medium", "foreign medium"),
    ),
)
def test_malformed_or_foreign_reference_surface_is_rejected(mutate) -> None:
    source = reference_for(b"period choice")
    value = _exact_raw_patch()
    mutate(value)

    with pytest.raises(ValueError):
        decode_reference_surface(value, expected=_request(source))


def test_reference_surface_decode_retains_raw_context() -> None:
    source = reference_for(b"period choice")
    observation = decode_reference_surface(
        _exact_raw_patch(),
        expected=_request(source),
    )

    assert observation.requested_input_basis == "x linear"
    assert observation.order_regime == "multi order"
    assert observation.transmitted_power == Decimal("0.75")
    assert observation.surface == _request(source).surface
    assert observation.frame == _request(source).frame
    assert observation.medium == _request(source).medium
    assert _request(source).source_references == (source,)
    numpy.testing.assert_array_equal(
        observation.electric_components[0].values,
        numpy.asarray(
            ((1, 2 + 1j, 1), (3 - 1j, 4, 3 - 1j), (1, 2 + 1j, 1)),
            dtype="<c16",
        ),
    )


def test_aperture_forms_one_field_from_patches_not_coefficients() -> None:
    source = reference_for(b"aperture source")
    aperture = _aperture(source)
    one = AdmittedReferenceSurface(
        _response(((1, 2), (3, 4)), source),
        reference_for(b"surface one"),
    )
    two = AdmittedReferenceSurface(
        _response(((5, 6), (7, 8)), source),
        reference_for(b"surface two"),
    )

    field = form_reference_surface_field(
        aperture,
        responses={"one": one, "two": two},
        aperture_reference=reference_for(b"aperture"),
    )

    assert field.surface.shape == (6, 6)
    assert set(numpy.unique(field.electric("x"))) == {
        0j,
        1 + 0j,
        2 + 0j,
        3 + 0j,
        4 + 0j,
        5 + 0j,
        6 + 0j,
        7 + 0j,
        8 + 0j,
    }
    assert field.incident_reference_power == aperture.site_count
    assert field.source_references == (
        reference_for(b"aperture"),
        one.reference,
        two.reference,
    )
    assert tuple(
        caution.concern
        for caution in reference_surface_cautions(
            one.response,
            one.reference,
        )
    ) == ("higher orders possible", "locally periodic assembly")


def test_aperture_rejects_one_mismatched_patch_context() -> None:
    source = reference_for(b"aperture source")
    aperture = _aperture(source)
    one = AdmittedReferenceSurface(
        _response(((1, 2), (3, 4)), source),
        reference_for(b"surface one"),
    )
    foreign_field = replace(
        one.response.field,
        surface=PlaneSurface(2e-6, 200e-9, (2, 2)),
    )
    two = AdmittedReferenceSurface(
        replace(one.response, field=foreign_field),
        reference_for(b"surface two"),
    )

    with pytest.raises(
        ValueError,
        match="reference_surface_response_context_mismatch",
    ):
        form_reference_surface_field(
            aperture,
            responses={"one": one, "two": two},
            aperture_reference=reference_for(b"aperture"),
        )


def test_small_aperture_comparison_reports_without_a_verdict() -> None:
    source = reference_for(b"source")
    local = _field(((1, 1), (1, 1)), source)
    full_wave = _field(((2, 2), (2, 2)), source)

    report = compare_reference_surfaces(
        local,
        full_wave,
        locally_periodic_reference=reference_for(b"local"),
        full_wave_reference=reference_for(b"full wave"),
        locally_periodic_transmitted_power=0.25,
        full_wave_transmitted_power=1.0,
        maximum_samples=4,
    )

    assert report.complex_field_difference["x"] == pytest.approx(0.5)
    assert report.power_difference == pytest.approx(-0.75)
    assert "qualified" not in report.document().values
    assert "passed" not in report.document().values


def test_small_aperture_comparison_uses_one_torch_complex_kernel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = reference_for(b"source")
    local = _field(((1, 1), (1, 1)), source)
    full_wave = _field(((2, 2), (2, 2)), source)
    original_tensor = torch.tensor
    observed: list[tuple[torch.dtype, str]] = []

    def record_tensor(
        values: object,
        *,
        dtype: torch.dtype,
        device: torch.device,
    ) -> torch.Tensor:
        observed.append((dtype, str(device)))
        return original_tensor(values, dtype=dtype, device=device)

    monkeypatch.setattr(
        reference_surface_module.torch.cuda,
        "is_available",
        lambda: False,
    )
    monkeypatch.setattr(
        reference_surface_module.torch,
        "tensor",
        record_tensor,
    )

    report = compare_reference_surfaces(
        local,
        full_wave,
        locally_periodic_reference=reference_for(b"local"),
        full_wave_reference=reference_for(b"full wave"),
        locally_periodic_transmitted_power=0.25,
        full_wave_transmitted_power=1.0,
        maximum_samples=4,
    )

    assert report.complex_field_difference["x"] == pytest.approx(0.5)
    assert observed
    assert set(observed) == {(torch.complex128, "cpu")}


def test_native_fixture_does_not_infer_surface_from_g0(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = {
        "complex_transmission": 1 + 0j,
        "output_x": 1 + 0j,
        "output_y": 0 + 0j,
        "phase_planes": "metamaterial_surfaces",
        "power_transmission": 0.9,
        "solver_status": "complete",
        "warnings": (),
    }
    active = ActiveEngines()
    factory = FakeSessionFactory(
        active=active,
        result={
            "_responses": {
                "linear_transmission": result,
                "propagation": result,
            }
        },
    )
    layout = workstation_layout(_now(), physical_cores=8)
    monkeypatch.setattr(probe_module, "plan", lambda _demand: layout)
    monkeypatch.setattr(
        probe_module,
        "SessionPool",
        lambda execution, lanes: NativeSessionPool(
            execution,
            lanes,
            _open_session=factory,
        ),
    )
    monkeypatch.setattr(
        WorkRecord,
        "artifact_manifest",
        classmethod(
            lambda _cls: {
                "completed_project": "qualified.fsp",
                "constructed_project": "constructed.fsp",
                "execution": "qualification.json",
            }
        ),
    )

    proof = probe_module.verify_periodic_responses(
        lumerical_config(tmp_path)
    )

    assert proof.capabilities == (
        PERIODIC_TRANSMISSION_RESPONSE,
        PERIODIC_POLARIZATION_RESPONSE,
    )
    assert proof.response_qualifications[-1].status == (
        "response_not_returned"
    )


def test_malformed_result_faults_after_session_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native_result = {
        "complex_transmission": 1 + 0j,
        "output_x": 1 + 0j,
        "output_y": 0 + 0j,
        "power_transmission": 0.9,
    }
    responses: dict[str, object] = {
        "linear_transmission": native_result,
        "propagation": native_result,
    }
    responses["reference_surface"] = object()
    factory = FakeSessionFactory(
        active=ActiveEngines(),
        result={"_responses": responses},
    )
    layout = workstation_layout(_now(), physical_cores=8)
    monkeypatch.setattr(probe_module, "plan", lambda _demand: layout)
    monkeypatch.setattr(
        probe_module,
        "SessionPool",
        lambda execution, lanes: NativeSessionPool(
            execution,
            lanes,
            _open_session=factory,
        ),
    )
    monkeypatch.setattr(
        WorkRecord,
        "artifact_manifest",
        classmethod(
            lambda _cls: {
                "completed_project": "qualified.fsp",
                "constructed_project": "constructed.fsp",
                "execution": "qualification.json",
            }
        ),
    )

    with pytest.raises(TypeError, match="optional_result_response_invalid"):
        probe_module.verify_periodic_responses(lumerical_config(tmp_path))

    assert factory.sessions
    assert all(session._closed for session in factory.sessions)


def test_nonfinite_g0_faults_after_the_surface_sibling_is_observed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch = _exact_raw_patch()
    patch["electric_components"] = {
        **patch["electric_components"],
        "z": {
            "imaginary": [[0.0] * 3 for _ in range(3)],
            "real": [[0.1] * 3 for _ in range(3)],
        },
    }
    patch["output_basis"] = "cartesian"
    patch["surface"] = {
        "position_m": "6e-7",
        "x_coordinates_m": ["-3.3e-7", "0", "3.3e-7"],
        "y_coordinates_m": ["-3.3e-7", "0", "3.3e-7"],
    }
    transmission = {
        "complex_transmission": complex(math.nan, 0),
        "output_x": 1 + 0j,
        "output_y": 0 + 0j,
        "phase_planes": "metamaterial_surfaces",
        "power_transmission": 0.9,
        "solver_status": "complete",
        "warnings": (),
    }
    result = {
        "_responses": {
            "linear_transmission": transmission,
            "propagation": transmission,
            "reference_surface": patch,
        }
    }
    active = ActiveEngines()
    factory = FakeSessionFactory(active=active, result=result)
    layout = workstation_layout(_now(), physical_cores=8)
    monkeypatch.setattr(probe_module, "plan", lambda _demand: layout)
    monkeypatch.setattr(
        probe_module,
        "SessionPool",
        lambda execution, lanes: NativeSessionPool(
            execution,
            lanes,
            _open_session=factory,
        ),
    )
    monkeypatch.setattr(
        WorkRecord,
        "artifact_manifest",
        classmethod(
            lambda _cls: {
                "completed_project": "qualified.fsp",
                "constructed_project": "constructed.fsp",
                "execution": "qualification.json",
            }
        ),
    )

    with pytest.raises(
        ValueError,
        match="periodic_transmission_response_invalid",
    ):
        probe_module.verify_periodic_responses(lumerical_config(tmp_path))

    assert factory.sessions
    assert all(session._closed for session in factory.sessions)


def test_native_session_reads_the_grating_groups_internal_t_plane() -> None:
    class Engine:
        def __init__(self) -> None:
            self.queries = []

        def addobject(self, kind):
            assert kind == "grating_s_params"

        def set(self, name, value):
            pass

        def runanalysis(self, name):
            assert name == "grating_response"

        def haveresult(self, name, result_name):
            self.queries.append((name, f"has:{result_name}"))
            return True

        def getnamed(self, name, property_name):
            assert name == "grating_response"
            if property_name == "polarization angle":
                return 0
            if property_name == "start wavelength":
                return 400e-9
            raise KeyError(property_name)

        def getresult(self, name, result_name):
            self.queries.append((name, result_name))
            assert name == "grating_response::T"
            if result_name == "T":
                return {"T": numpy.asarray((0.8,))}
            assert result_name == "E"
            electric = numpy.zeros((43, 43, 1, 1, 3), dtype=complex)
            unique_samples = (
                numpy.arange(42)[:, None] * 100
                + numpy.arange(42)[None, :]
            )
            electric[:42, :42, 0, 0, 0] = unique_samples + 0.5j
            electric[42, :42, ...] = electric[0, :42, ...]
            electric[:, 42, ...] = electric[:, 0, ...]
            return {
                "E": electric,
                "x": numpy.linspace(-330e-9, 330e-9, 43),
                "y": numpy.linspace(-330e-9, 330e-9, 43),
                "z": numpy.asarray((800e-9,)),
            }

    engine = Engine()
    session = LumericalSession(engine)
    session.create("grating_response", "grating_response", {})

    outcome = session.optional_result(
        "grating_response",
        "reference_surface",
    )
    assert outcome.response is not None
    response = outcome.response

    assert engine.queries == [
        ("grating_response::T", "has:E"),
        ("grating_response::T", "has:T"),
        ("grating_response::T", "E"),
        ("grating_response::T", "T"),
    ]
    assert response["output_basis"] == "cartesian"
    assert response["surface"] == {
        "position_m": "7.9999999999999996e-07",
        "x_coordinates_m": [
            format(value, ".17g")
            for value in numpy.linspace(-330e-9, 330e-9, 43)
        ],
        "y_coordinates_m": [
            format(value, ".17g")
            for value in numpy.linspace(-330e-9, 330e-9, 43)
        ],
    }
    assert len(response["electric_components"]["x"]["real"]) == 43
    assert len(response["electric_components"]["x"]["real"][0]) == 43
    assert response["electric_components"]["x"]["real"][5][7] == 705
    assert response["electric_components"]["x"]["imaginary"][5][7] == 0.5
    assert response["electric_components"]["x"]["real"][-1][-1] == 0
    assert response["transmitted_power"] == "0.80000000000000004"


@pytest.mark.parametrize(
    ("result_name", "missing_result", "expected_inventory"),
    (
        (
            "propagation",
            "T",
            (
                ("grating_response", "S"),
                ("grating_response", "T"),
            ),
        ),
        (
            "linear_transmission",
            "S_polarization",
            (("grating_response", "S_polarization"),),
        ),
        (
            "reference_surface",
            "E",
            (
                ("grating_response::T", "E"),
                ("grating_response::T", "T"),
            ),
        ),
    ),
)
def test_native_session_reports_only_inventory_proven_result_absence(
    result_name: str,
    missing_result: str,
    expected_inventory: tuple[tuple[str, str], ...],
) -> None:
    class Engine:
        def __init__(self) -> None:
            self.inventory_queries: list[tuple[str, str]] = []

        def addobject(self, kind):
            assert kind == "grating_s_params"

        def set(self, name, value):
            pass

        def runanalysis(self, name):
            assert name == "grating_response"

        def haveresult(self, name, native_result):
            self.inventory_queries.append((name, native_result))
            return native_result != missing_result

        def getresult(self, name, native_result):
            raise AssertionError(
                f"absent result was read:{name}:{native_result}"
            )

    engine = Engine()
    session = LumericalSession(engine)
    session.create("grating_response", "grating_response", {})

    outcome = session.optional_result("grating_response", result_name)

    assert outcome.response is None
    assert tuple(engine.inventory_queries) == expected_inventory


@pytest.mark.parametrize(
    ("result_name", "expected_inventory", "expected_response"),
    (
        (
            "propagation",
            (
                ("grating_response", "S"),
                ("grating_response", "T"),
            ),
            {
                "complex_transmission": 1 + 0j,
                "phase_planes": "metamaterial_surfaces",
                "power_transmission": 0.8,
                "solver_status": "complete",
                "warnings": (),
            },
        ),
        (
            "linear_transmission",
            (("grating_response", "S_polarization"),),
            {
                "output_x": 0j,
                "output_y": 1 + 0j,
                "phase_planes": "metamaterial_surfaces",
                "solver_status": "complete",
                "warnings": (),
            },
        ),
    ),
)
def test_native_session_reads_present_group_results_after_inventory_check(
    result_name: str,
    expected_inventory: tuple[tuple[str, str], ...],
    expected_response: dict[str, object],
) -> None:
    class Engine:
        def __init__(self) -> None:
            self.inventory_queries: list[tuple[str, str]] = []

        def addobject(self, kind):
            assert kind == "grating_s_params"

        def set(self, name, value):
            pass

        def runanalysis(self, name):
            assert name == "grating_response"

        def haveresult(self, name, native_result):
            self.inventory_queries.append((name, native_result))
            return True

        def getresult(self, name, native_result):
            if native_result == "S":
                return {"S21_Gn": numpy.asarray((1 + 0j,))}
            if native_result == "T":
                return {"T_Gn": numpy.asarray((0.8,))}
            assert native_result == "S_polarization"
            return {"S21_Gn": numpy.asarray((1 + 0j, 0j))}

    engine = Engine()
    session = LumericalSession(engine)
    session.create("grating_response", "grating_response", {})

    outcome = session.optional_result("grating_response", result_name)

    assert outcome.response == expected_response
    assert tuple(engine.inventory_queries) == expected_inventory


def test_native_optional_result_keeps_malformed_present_payload_direct() -> None:
    class Engine:
        def addobject(self, kind):
            assert kind == "grating_s_params"

        def set(self, name, value):
            pass

        def runanalysis(self, name):
            assert name == "grating_response"

        def haveresult(self, name, native_result):
            return True

        def getresult(self, name, native_result):
            if native_result == "S":
                return {}
            return {"T_Gn": numpy.asarray((0.8,))}

    session = LumericalSession(Engine())
    session.create("grating_response", "grating_response", {})

    with pytest.raises(KeyError, match="S21_Gn"):
        session.optional_result("grating_response", "propagation")


def test_native_session_preserves_a_nonuniform_closed_reference_grid() -> None:
    x_coordinates = numpy.asarray(
        (-200e-9, -90e-9, 20e-9, 140e-9, 200e-9)
    )
    y_coordinates = numpy.asarray((-200e-9, -50e-9, 70e-9, 200e-9))

    class Engine:
        def addobject(self, kind):
            assert kind == "grating_s_params"

        def set(self, name, value):
            pass

        def runanalysis(self, name):
            assert name == "grating_response"

        def getnamed(self, name, property_name):
            assert name == "grating_response"
            return 0 if property_name == "polarization angle" else 400e-9

        def getresult(self, name, result_name):
            if result_name == "T":
                return {"T": numpy.asarray((0.8,))}
            electric = numpy.zeros((5, 4, 1, 1, 3), dtype=complex)
            electric[:4, :3, 0, 0, 0] = (
                numpy.arange(4)[:, None] * 10 + numpy.arange(3)[None, :]
            )
            electric[4, :3, ...] = electric[0, :3, ...]
            electric[:, 3, ...] = electric[:, 0, ...]
            return {
                "E": electric,
                "x": x_coordinates,
                "y": y_coordinates,
                "z": numpy.asarray((800e-9,)),
            }

    session = LumericalSession(Engine())
    session.create("grating_response", "grating_response", {})

    response = session.result("grating_response", "reference_surface")

    assert response["surface"] == {
        "position_m": "7.9999999999999996e-07",
        "x_coordinates_m": [format(value, ".17g") for value in x_coordinates],
        "y_coordinates_m": [format(value, ".17g") for value in y_coordinates],
    }
    assert response["electric_components"]["x"]["real"] == [
        [0.0, 10.0, 20.0, 30.0, 0.0],
        [1.0, 11.0, 21.0, 31.0, 1.0],
        [2.0, 12.0, 22.0, 32.0, 2.0],
        [0.0, 10.0, 20.0, 30.0, 0.0],
    ]


@pytest.mark.parametrize(
    ("defect", "finding"),
    (
        ("endpoint_span", "reference_surface_native_closed_grid_invalid"),
        ("terminal_plane", "reference_surface_native_closed_grid_invalid"),
        ("rank", "reference_surface_native_shape_invalid"),
        ("nonfinite", "reference_surface_native_shape_invalid"),
    ),
)
def test_native_session_rejects_malformed_closed_reference_grids(
    defect: str,
    finding: str,
) -> None:
    class Engine:
        def addobject(self, kind):
            assert kind == "grating_s_params"

        def set(self, name, value):
            pass

        def runanalysis(self, name):
            assert name == "grating_response"

        def getresult(self, name, result_name):
            if result_name == "T":
                return {"T": numpy.asarray((0.8,))}
            electric = numpy.zeros((43, 43, 1, 1, 3), dtype=complex)
            y_coordinates = numpy.linspace(-330e-9, 330e-9, 43)
            if defect == "endpoint_span":
                y_coordinates = numpy.linspace(-330e-9, 320e-9, 43)
            if defect == "terminal_plane":
                electric[-1, ..., 0] = 1
            if defect == "nonfinite":
                electric[10, 10, ..., 0] = complex(math.nan, 0)
            return {
                "E": (
                    electric[:, :, 0, :, :]
                    if defect == "rank"
                    else electric
                ),
                "x": numpy.linspace(-330e-9, 330e-9, 43),
                "y": y_coordinates,
                "z": numpy.asarray((800e-9,)),
            }

    session = LumericalSession(Engine())
    session.create("grating_response", "grating_response", {})

    with pytest.raises(ValueError, match=finding):
        session.result("grating_response", "reference_surface")

from __future__ import annotations

import ast
from dataclasses import replace
from importlib import import_module
from pathlib import Path

import pytest

from metacraft.authority import Document, Reference
from metacraft.science.metalens.geometric_phase import JONES_LIBRARY_SCHEMA
from metacraft.science.metalens.propagation_phase import (
    PERIODIC_TRANSMISSION_SCHEMA,
)
from metacraft.science.study import Task
from metacraft.work_execution import PERMITTED_WORK_SCHEMA


_PROPAGATION_WORK_IDENTITY = (
    "sha256:20127af26c51bf6a7fce61f90069671b" "455e5b98678da3cfb251634be78fd0d4"
)
_GEOMETRIC_X_WORK_IDENTITY = (
    "sha256:24ae7283a961df7ba267de9e498af5ef" "47f160dafa2a7a9eef4845c82254865b"
)
_PROPAGATION_PERMITTED_WORK_BYTES = (
    b'{"schema_identifier":"metacraft.science.permitted_work","values":'
    b'{"work":"sha256:20127af26c51bf6a7fce61f90069671b455e5b98678da'
    b'3cfb251634be78fd0d4"}}'
)
_GEOMETRIC_X_PERMITTED_WORK_BYTES = (
    b'{"schema_identifier":"metacraft.science.permitted_work","values":'
    b'{"work":"sha256:24ae7283a961df7ba267de9e498af5ef47f160dafa2a7a'
    b'9eef4845c82254865b"}}'
)
_PROPAGATION_RECEIPT_BYTES = (
    b'{"schema_identifier":"metacraft.science.metalens.propagation_phase.'
    b'periodic_transmission","values":{"candidate":{"diameter_nm":180,'
    b'"height_nm":600,"name":"circular-pillar-height-0600nm-diameter-'
    b'0180nm","shape":"circular pillar"},"construction_valid":true,'
    b'"execution":{"native":false,"placement":{"cores":[1,2,3,4],"lane":'
    b'"fixture-lane","processor_group":0},"project":"fixture-periodic.fsp",'
    b'"return_code":0,"source":"golden fixture"},"phase":{"value":'
    b'"6.116840651000000"},"phase_planes":"metamaterial_surfaces","power":'
    b'{"leakage":"0.421875","useful":"0.578125"},"solver_status":'
    b'"complete","transmission":{"imaginary_part":"-0.125","real_part":'
    b'"0.75"},"warnings":["fixture warning"]}}'
)
_GEOMETRIC_X_RECEIPT_BYTES = (
    b'{"schema_identifier":"metacraft.science.metalens.geometric_phase.'
    b'jones_library","values":{"basis":"x","candidate":{"geometry":'
    b'{"length_nm":140,"width_nm":80},"height_nm":600,"name":'
    b'"rectangular-fin-height-0600nm-length-0140nm-width-0080nm","shape":'
    b'"rectangular fin"},"execution":{"native":false,"placement":{"cores":'
    b'[1,2,3,4],"lane":"fixture-lane","processor_group":0},"project":'
    b'"fixture-periodic.fsp","return_code":0,"source":"golden fixture"},'
    b'"output_x":{"imaginary_part":"0.125","real_part":"0.875"},'
    b'"output_y":{"imaginary_part":"0.5","real_part":"-0.25"},'
    b'"phase_planes":"grating_s_params","solver_status":"complete",'
    b'"warnings":[]}}'
)


def _reference(character: str, size_bytes: int) -> Reference:
    return Reference(
        content_hash=f"sha256:{character * 64}",
        media_type="application/json",
        metadata_content_hash=f"sha256:{character.upper() * 64}",
        size_bytes=size_bytes,
    )


def _height_choice_reference() -> Reference:
    return _reference("a", 101)


def _propagation_task() -> Task:
    return Task(
        proof_identity=f"sha256:{'1' * 64}",
        claim="periodic_transmission",
        method="observe_periodic_transmission",
        schema=PERIODIC_TRANSMISSION_SCHEMA,
        brief_identity=f"sha256:{'2' * 64}",
        design_identity=f"sha256:{'3' * 64}",
        prerequisite_evidence=(_reference("c", 303),),
        consultations=(_reference("d", 404),),
        binding_reference=_reference("b", 202),
        capacity_scope="lumerical-fdtd:fixture",
    )


def _geometric_task() -> Task:
    return Task(
        proof_identity=f"sha256:{'4' * 64}",
        claim="jones_library",
        method="observe_periodic_polarization",
        schema=JONES_LIBRARY_SCHEMA,
        brief_identity=f"sha256:{'5' * 64}",
        design_identity=f"sha256:{'6' * 64}",
        prerequisite_evidence=(
            _reference("c", 303),
            _height_choice_reference(),
        ),
        consultations=(),
        binding_reference=_reference("b", 202),
        capacity_scope="lumerical-fdtd:fixture",
    )


def _execution_mapping() -> dict[str, object]:
    return {
        "native": False,
        "placement": {
            "lane": "fixture-lane",
            "processor_group": 0,
            "cores": (1, 2, 3, 4),
        },
        "project": "fixture-periodic.fsp",
        "return_code": 0,
        "source": "golden fixture",
    }


def test_periodic_work_identities_keep_the_stable_protocol_literals() -> None:
    periodic_response = import_module("metacraft.science.periodic_response")
    metalens_request = import_module("metacraft.science.metalens.periodic_request")
    propagation_candidate = metalens_request.PeriodicCellCandidate(
        height_nm=600,
        geometry=periodic_response.CircularCrossSection(diameter_nm=180),
    )
    geometric_candidate = metalens_request.PeriodicCellCandidate(
        height_nm=600,
        geometry=periodic_response.RectangularCrossSection(
            short_side_nm=80,
            long_side_nm=140,
        ),
    )

    propagation = metalens_request.periodic_cell_work_identity(
        _propagation_task(),
        propagation_candidate,
        _height_choice_reference(),
    )
    geometric_x = metalens_request.polarization_basis_work_identity(
        _geometric_task(),
        geometric_candidate,
        "x",
        _height_choice_reference(),
    )

    assert propagation == _PROPAGATION_WORK_IDENTITY
    assert geometric_x == _GEOMETRIC_X_WORK_IDENTITY


def test_periodic_request_rejects_an_unknown_authority_work_method() -> None:
    periodic_response = import_module("metacraft.science.periodic_response")
    metalens_request = import_module("metacraft.science.metalens.periodic_request")
    candidate = metalens_request.PeriodicCellCandidate(
        height_nm=600,
        geometry=periodic_response.CircularCrossSection(diameter_nm=180),
    )

    with pytest.raises(
        ValueError,
        match="periodic_work_method_unsupported",
    ):
        metalens_request.periodic_cell_work_identity(
            replace(_propagation_task(), method="unknown_periodic_method"),
            candidate,
            _height_choice_reference(),
        )


def test_metalens_periodic_modules_follow_one_way_change_dependencies() -> None:
    metalens_directory = (
        Path(__file__).parents[2] / "src" / "metacraft" / "science" / "metalens"
    )

    def local_imports(module_name: str) -> set[str]:
        tree = ast.parse(
            (metalens_directory / f"{module_name}.py").read_text(encoding="utf-8")
        )
        return {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.level == 1
            and node.module is not None
        }

    request = import_module("metacraft.science.metalens.periodic_request")
    response = import_module("metacraft.science.metalens.periodic_cell_evidence")
    surface = import_module("metacraft.science.metalens.reference_surface_evidence")

    assert hasattr(request, "PeriodicCellCandidate")
    assert hasattr(request, "plan_periodic_transmission_request")
    assert not hasattr(request, "PropagationEvidenceBatch")
    assert not hasattr(request, "plan_reference_surface_request")

    assert hasattr(response, "PropagationEvidenceBatch")
    assert hasattr(response, "JonesEvidenceBatch")
    assert not hasattr(response, "PeriodicCellCandidate")
    assert not hasattr(response, "plan_reference_surface_request")

    assert hasattr(surface, "admit_reference_surfaces")
    assert not hasattr(surface, "plan_reference_surface_request")
    assert not hasattr(surface, "PropagationEvidenceBatch")
    assert not hasattr(surface, "PeriodicCellCandidate")

    assert not local_imports("periodic_request") & {
        "periodic_cell_evidence",
        "reference_surface_evidence",
    }
    assert local_imports("periodic_cell_evidence") & {
        "periodic_request",
        "reference_surface_evidence",
    } == {"periodic_request"}
    assert local_imports("reference_surface_evidence") & {
        "periodic_request",
        "periodic_cell_evidence",
    } == {"periodic_cell_evidence"}


def test_permitted_work_keeps_its_stable_canonical_bytes() -> None:
    propagation = Document(
        PERMITTED_WORK_SCHEMA,
        {"work": _PROPAGATION_WORK_IDENTITY},
    )
    geometric_x = Document(
        PERMITTED_WORK_SCHEMA,
        {"work": _GEOMETRIC_X_WORK_IDENTITY},
    )

    assert propagation.to_bytes() == _PROPAGATION_PERMITTED_WORK_BYTES
    assert geometric_x.to_bytes() == _GEOMETRIC_X_PERMITTED_WORK_BYTES


def test_periodic_receipts_keep_their_stable_canonical_bytes() -> None:
    periodic_response = import_module("metacraft.science.periodic_response")
    propagation_document = periodic_response.decode_periodic_transmission(
        {
            "candidate": {
                "diameter_nm": 180,
                "height_nm": 600,
                "name": ("circular-pillar-height-0600nm-diameter-0180nm"),
                "shape": "circular pillar",
            },
            "construction_valid": True,
            "execution": _execution_mapping(),
            "phase": {"value": "6.116840651000000"},
            "phase_planes": "metamaterial_surfaces",
            "power": {
                "leakage": "0.421875",
                "useful": "0.578125",
            },
            "solver_status": "complete",
            "transmission": {
                "imaginary_part": "-0.125",
                "real_part": "0.75",
            },
            "warnings": ("fixture warning",),
        }
    )
    geometric_x_document = periodic_response.decode_periodic_polarization(
        {
            "basis": "x",
            "candidate": {
                "geometry": {
                    "length_nm": 140,
                    "width_nm": 80,
                },
                "height_nm": 600,
                "name": ("rectangular-fin-height-0600nm-" "length-0140nm-width-0080nm"),
                "shape": "rectangular fin",
            },
            "execution": _execution_mapping(),
            "output_x": {
                "imaginary_part": "0.125",
                "real_part": "0.875",
            },
            "output_y": {
                "imaginary_part": "0.5",
                "real_part": "-0.25",
            },
            "phase_planes": "grating_s_params",
            "solver_status": "complete",
            "warnings": (),
        }
    )

    assert (
        Document(
            PERIODIC_TRANSMISSION_SCHEMA,
            propagation_document.as_mapping(),
        ).to_bytes()
        == _PROPAGATION_RECEIPT_BYTES
    )
    assert (
        Document(
            JONES_LIBRARY_SCHEMA,
            geometric_x_document.as_mapping(),
        ).to_bytes()
        == _GEOMETRIC_X_RECEIPT_BYTES
    )


def test_periodic_response_interface_has_one_observe_method() -> None:
    periodic_response = import_module("metacraft.science.periodic_response")
    interface = periodic_response.PeriodicResponse

    public_methods = {
        name
        for name, member in vars(interface).items()
        if not name.startswith("_") and callable(member)
    }

    assert public_methods == {"observe"}


def test_reference_surfaces_remain_embedded_without_a_second_request() -> None:
    periodic_response = import_module("metacraft.science.periodic_response")

    assert hasattr(periodic_response, "PeriodicReferenceSurfaceObservation")
    for retired_name in (
        "AdmittedPeriodicReferenceSurface",
        "ObservedPeriodicReferenceSurface",
        "PeriodicReferenceSurfaceRequest",
        "ReferenceSurfaceWork",
    ):
        assert not hasattr(periodic_response, retired_name)


def test_recorded_response_is_an_outer_solver_adapter() -> None:
    periodic_response = import_module("metacraft.science.periodic_response")
    recorded_response = import_module("metacraft.solvers.recorded_periodic_response")

    assert not hasattr(periodic_response, "RecordedPeriodicResponse")
    assert (
        recorded_response.RecordedPeriodicResponse.__module__
        == "metacraft.solvers.recorded_periodic_response"
    )


def test_lumerical_runtime_source_contains_no_metalens_meaning() -> None:
    source_root = (
        Path(__file__).parents[2] / "src" / "metacraft" / "solvers" / "lumerical_fdtd"
    )
    forbidden = (
        "science.metalens",
        "Study",
        "HeightChoice",
        "ControlStrategy",
    )
    violations = {
        path.relative_to(source_root).as_posix(): tuple(
            token for token in forbidden if token in source
        )
        for path in sorted(source_root.rglob("*.py"))
        if (source := path.read_text(encoding="utf-8-sig"))
        and any(token in source for token in forbidden)
    }

    assert violations == {}

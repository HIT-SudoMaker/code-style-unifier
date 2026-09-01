from __future__ import annotations

from dataclasses import fields, replace
from inspect import signature

import numpy
import pytest

import metacraft.field.reference_surface_formation as formation_module
from metacraft.authority.reference import reference_for
from metacraft.field.rectilinear import RectilinearPlane
from metacraft.field.reference_surface_formation import (
    ReferenceSurfaceFormationInput,
    UniformReferenceSurfaceFormation,
    form_uniform_reference_surfaces,
    uniform_reference_surface_formation_qualification_document,
)
from metacraft.field.sample import (
    ComponentBasis,
    CoordinateFrame,
    FieldComponent,
    Medium,
)


def _triangle(value: numpy.ndarray) -> numpy.ndarray:
    return numpy.where(value <= 0.25, value / 0.25, (1.0 - value) / 0.75)


def _input(name: str = "raw") -> ReferenceSurfaceFormationInput:
    x = numpy.asarray((0.0, 0.1, 0.25, 0.7, 1.0))
    y = numpy.asarray((0.0, 0.2, 0.25, 0.8, 1.0))
    values = _triangle(x)[None, :] + 1j * _triangle(y)[:, None]
    values.setflags(write=False)
    return ReferenceSurfaceFormationInput(
        wavelength_m=1.55,
        surface=RectilinearPlane(
            position_m=2.0,
            horizontal_coordinates_m=x,
            vertical_coordinates_m=y,
        ),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.CARTESIAN,
        electric_components=tuple(
            FieldComponent(component, values)
            for component in ("x", "y", "z")
        ),
        source_references=(reference_for(name.encode()),),
        incident_reference_power=1.0,
    )


def _qualification() -> UniformReferenceSurfaceFormation:
    document = uniform_reference_surface_formation_qualification_document()
    return UniformReferenceSurfaceFormation(
        realization_identity="periodic_rectilinear_bilinear_v1",
        qualification_reference=reference_for(document.to_bytes()),
    )


def test_formation_interface_has_only_the_frozen_public_fields() -> None:
    assert tuple(field.name for field in fields(ReferenceSurfaceFormationInput)) == (
        "wavelength_m",
        "surface",
        "frame",
        "medium",
        "basis",
        "electric_components",
        "source_references",
        "incident_reference_power",
    )
    assert tuple(field.name for field in fields(UniformReferenceSurfaceFormation)) == (
        "realization_identity",
        "qualification_reference",
    )
    assert tuple(signature(form_uniform_reference_surfaces).parameters) == (
        "observations",
        "formation",
    )
    assert not hasattr(
        formation_module,
        "RectilinearReferenceSurfaceInput",
    )
    assert not hasattr(
        formation_module,
        "QualifiedUniformReferenceSurfaceFormation",
    )


def test_qualified_formation_uses_one_fixed_half_open_realization() -> None:
    qualification = _qualification()
    qualification_reference = qualification.qualification_reference
    raw = _input()

    (formed,) = form_uniform_reference_surfaces((raw,), qualification)

    target = numpy.arange(24, dtype=numpy.float64) / 24
    expected = _triangle(target)[None, :] + 1j * _triangle(target)[:, None]
    assert qualification.realization_identity == "periodic_rectilinear_bilinear_v1"
    assert qualification.samples_per_period == 24
    assert qualification.maximum_batch_size == 256
    assert qualification.accepted_thresholds == {
        "maximum_error": 0.0093,
        "power_change": 0.0006,
        "relative_l2_error": 0.0081,
    }
    assert formed.surface.position_m == raw.surface.position_m
    assert formed.surface.shape == (24, 24)
    assert formed.surface.spacing_m == 1.0 / 24
    assert numpy.allclose(formed.electric("x"), expected, rtol=0, atol=2e-15)
    assert formed.electric("x").dtype == numpy.complex128
    assert formed.source_references == (
        *raw.source_references,
        qualification_reference,
    )


def test_formation_preflights_one_common_bounded_batch() -> None:
    qualification = _qualification()
    first = _input("first")
    second = replace(
        _input("second"),
        surface=RectilinearPlane(
            position_m=2.0,
            horizontal_coordinates_m=numpy.asarray((0.1, 0.2, 0.35, 0.8, 1.1)),
            vertical_coordinates_m=numpy.asarray((0.0, 0.2, 0.25, 0.8, 1.0)),
        ),
    )

    with pytest.raises(
        ValueError,
        match="reference_surface_formation_batch_mismatch",
    ):
        form_uniform_reference_surfaces((first, second), qualification)
    with pytest.raises(
        ValueError,
        match="reference_surface_formation_batch_mismatch",
    ):
        form_uniform_reference_surfaces((), qualification)
    with pytest.raises(
        ValueError,
        match="reference_surface_formation_batch_mismatch",
    ):
        form_uniform_reference_surfaces((first,) * 257, qualification)


def test_formation_input_uses_the_frozen_observation_faults() -> None:
    observation = _input()
    with pytest.raises(
        ValueError,
        match="periodic_reference_surface_observation_invalid",
    ):
        replace(observation, wavelength_m="invalid")  # type: ignore[arg-type]

    mismatched_surface = RectilinearPlane(
        position_m=observation.surface.position_m,
        horizontal_coordinates_m=numpy.asarray((0.0, 0.2, 0.8, 1.0)),
        vertical_coordinates_m=observation.surface.vertical_coordinates_m,
    )
    with pytest.raises(ValueError, match="rectilinear_component_shape_mismatch"):
        replace(observation, surface=mismatched_surface)

    open_seam = observation.electric_components[0].values.copy()
    open_seam[0, 0] += 1.0
    open_seam.setflags(write=False)
    with pytest.raises(
        ValueError,
        match="reference_surface_formation_periodic_seam_mismatch",
    ):
        replace(
            observation,
            electric_components=(
                FieldComponent("x", open_seam),
                *observation.electric_components[1:],
            ),
        )


def test_formation_preserves_batch_order_and_rejects_reused_provenance() -> None:
    qualification = _qualification()
    qualification_reference = qualification.qualification_reference
    first = _input("first")
    second = _input("second")

    formed = form_uniform_reference_surfaces((second, first), qualification)

    assert tuple(field.source_references[0] for field in formed) == (
        second.source_references[0],
        first.source_references[0],
    )
    with pytest.raises(
        ValueError,
        match="reference_surface_formation_batch_mismatch",
    ):
        form_uniform_reference_surfaces(
            (
                first,
                replace(first, source_references=(qualification_reference,)),
            ),
            qualification,
        )


def test_formation_qualification_requires_its_exact_independent_document() -> None:
    document = uniform_reference_surface_formation_qualification_document()

    with pytest.raises(
        ValueError,
        match="reference_surface_formation_unqualified",
    ):
        UniformReferenceSurfaceFormation(
            realization_identity="periodic_rectilinear_bilinear_v1",
            qualification_reference=reference_for(b"another qualification"),
        )
    with pytest.raises(
        ValueError,
        match="reference_surface_formation_unqualified",
    ):
        UniformReferenceSurfaceFormation(
            realization_identity="another_realization",
            qualification_reference=reference_for(document.to_bytes()),
        )

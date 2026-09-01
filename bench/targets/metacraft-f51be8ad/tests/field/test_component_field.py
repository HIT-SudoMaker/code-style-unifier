from __future__ import annotations

from decimal import Decimal

import numpy
import pytest

from metacraft.authority import Document, Reference, reference_for
from metacraft.field import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from metacraft.field.evidence import (
    admit_components,
    field_document,
    restore_field,
)
from metacraft.science.metalens.focus_evidence import (
    focal_region_document,
    restore_focal_region,
)
from metacraft.science.metalens.aperture import (
    Aperture,
    Cell,
    Circle,
    Material,
    Response,
    State,
    form_field as form_aperture_field,
)
from tests.field_fixtures import recorded_focal_region


def _admitted_components(
    electric_components: tuple[FieldComponent, ...],
    magnetic_components: tuple[FieldComponent, ...] = (),
) -> tuple[
    dict[str, Reference],
    dict[str, Reference],
    dict[Reference, bytes],
]:
    bodies: dict[Reference, bytes] = {}

    def admit(
        body: bytes,
        *,
        media_type: str,
        descriptive_metadata: dict[str, object],
    ) -> Reference:
        reference = reference_for(
            body,
            media_type=media_type,
            descriptive_metadata=descriptive_metadata,
        )
        bodies[reference] = body
        return reference

    electric, magnetic = admit_components(
        electric_components,
        magnetic_components,
        admit,
    )
    return electric, magnetic, bodies


def test_aperture_forms_one_immutable_component_field() -> None:
    """
    Carry one component Field through propagation and evaluation.
    """

    size = 23
    spacing_m = 200e-9
    wavelength_m = 400e-9
    axis = (numpy.arange(size) - size // 2) * spacing_m
    position_x, position_y = numpy.meshgrid(axis, axis)
    occupied = numpy.hypot(position_x, position_y) <= 2.2e-6
    aperture_reference = reference_for(b"exact aperture")
    cell_reference = reference_for(b"exact cell")
    state_reference = reference_for(b"exact state")
    aperture = Aperture(
        cells=(
            Cell(
                identity="cell",
                atom=Material("silicon nitride", "solver native"),
                substrate=Material("silica", "solver native"),
                period_nm=200,
                height_nm=500,
                geometry=Circle(100),
                source=cell_reference,
            ),
        ),
        states=(
            State(
                identity="state",
                cell_identity="cell",
                responses=(
                    Response(
                        "transmission",
                        Decimal("1"),
                        Decimal("0"),
                        Decimal("1"),
                    ),
                ),
                source=state_reference,
                target_phase=Decimal("0"),
                realized_phase=Decimal("0"),
                useful_power=Decimal("1"),
                leakage_power=Decimal("0"),
            ),
        ),
        coordinates_nm=numpy.rint(
            numpy.stack((position_x, position_y), axis=-1) * 1e9
        ).astype(numpy.int64),
        is_occupied=occupied,
        target_phase=numpy.zeros(occupied.shape),
        state_identities=numpy.where(occupied, "state", ""),
        spacing_nm=200,
        half_span_nm=2_200,
        evidence=(state_reference,),
    )

    field = form_aperture_field(
        aperture,
        wavelength_m=wavelength_m,
        surface_position_m=0.0,
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        component_channels={
            "x": "transmission",
            "y": None,
        },
        aperture_reference=aperture_reference,
    )

    assert field.component_names == ("x", "y")
    assert field.electric("x").dtype == numpy.dtype("<c16")
    assert field.electric("x").flags.c_contiguous
    assert not field.electric("x").flags.writeable
    assert not field.electric("y").flags.writeable

    assert field.source_references == (aperture_reference,)


def test_field_component_rejects_a_mutable_array() -> None:
    """
    Reject mutable component authority objects.
    """

    with pytest.raises(ValueError, match="field_component_mutable"):
        FieldComponent(
            "x",
            numpy.ones((2, 2), dtype=numpy.dtype("<c16")),
        )


def test_field_manifest_closes_electric_and_magnetic_components() -> None:
    """
    Round-trip electric and magnetic component manifests.
    """

    electric = _immutable(numpy.ones((2, 2), dtype="<c16"))
    magnetic = _immutable(2 * numpy.ones((2, 2), dtype="<c16"))
    source = reference_for(b"source")
    field = Field(
        wavelength_m=400e-9,
        surface=PlaneSurface(0.0, 200e-9, (2, 2)),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            FieldComponent("x", electric),
            FieldComponent("y", _immutable(numpy.zeros((2, 2), dtype="<c16"))),
        ),
        magnetic_components=(
            FieldComponent("x", magnetic),
            FieldComponent("y", _immutable(numpy.zeros((2, 2), dtype="<c16"))),
        ),
        source_references=(source,),
        incident_reference_power=4.0,
    )
    electric_references, magnetic_references, bodies = (
        _admitted_components(
            field.electric_components,
            field.magnetic_components,
        )
    )
    document = field_document(
        "metacraft.science.fixture.field",
        field,
        electric_references,
        magnetic_component_references=magnetic_references,
    )

    restored = restore_field(document, bodies.__getitem__)

    assert numpy.array_equal(restored.electric("x"), electric)
    assert numpy.array_equal(restored.magnetic("x"), magnetic)
    assert document.values["storage"] == {
        "dtype": "<c16",
        "order": "C",
        "unit": "V/m",
    }


def test_focal_region_manifest_closes_recorded_component_evidence() -> None:
    """
    Round-trip one admitted-style focal region without propagating again.
    """

    region = recorded_focal_region(
        numpy.ones((2, 2), dtype=numpy.complex128),
        axial_distances_m=(1.6e-6, 2e-6, 2.4e-6),
        axial_peak_intensities=(0.5, 1.0, 0.5),
        found_focus_m=2e-6,
        expected_focus_m=2e-6,
        incident_reference_power=4.0,
        transmitted_x_power=4.0,
    )
    region_references, magnetic_references, region_bodies = (
        _admitted_components(
            region.electric_components,
            region.magnetic_components,
        )
    )
    propagation_binding = reference_for(b"angular spectrum binding")
    region_document = focal_region_document(
        region,
        region_references,
        binding_reference=propagation_binding,
        field_reference=region.source_references[0],
        magnetic_component_references=magnetic_references,
    )

    restored_region = restore_focal_region(
        region_document,
        region_bodies.__getitem__,
    )

    assert numpy.array_equal(restored_region.electric("x"), region.electric("x"))
    assert region_document.values["binding"] == (
        propagation_binding.as_mapping()
    )
    assert region_document.values["realization"]["identity"] == (
        "metacraft.field.angular_spectrum"
    )


def test_field_decoder_rejects_the_wrong_component_media_type() -> None:
    """
    Reject a component object with the wrong media type.
    """

    values = _immutable(numpy.ones((2, 2), dtype="<c16"))
    component = FieldComponent("x", values)
    references, _magnetic, bodies = _admitted_components((component,))
    raw = bodies[references["x"]]
    wrong_reference = reference_for(raw, media_type="application/x-npy")
    manifest = Document(
        "metacraft.science.fixture.field",
        {
            "basis": "transverse linear",
            "electric_components": {
                "x": wrong_reference.as_mapping(),
                "y": wrong_reference.as_mapping(),
            },
            "frame": {
                "normal_axis": "z",
                "propagation_direction": "positive",
                "sample_order": ["y", "x"],
            },
            "incident_reference_power": "4",
            "magnetic_components": {},
            "medium": {"identity": "air"},
            "source_references": {
                "source_001": reference_for(b"source").as_mapping(),
            },
            "storage": {
                "dtype": "<c16",
                "order": "C",
                "unit": "V/m",
            },
            "surface": {
                "kind": "plane",
                "position_m": "0",
                "shape": [2, 2],
                "spacing_m": "2e-7",
            },
            "wavelength_m": "4e-7",
        },
    )

    with pytest.raises(ValueError, match="field_evidence_mismatch"):
        restore_field(manifest, lambda _: raw)


def _immutable(values: numpy.ndarray) -> numpy.ndarray:
    frozen = numpy.array(values, dtype="<c16", order="C", copy=True)
    frozen.setflags(write=False)
    return frozen

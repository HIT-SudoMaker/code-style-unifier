from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
from pathlib import Path

import numpy
import pytest
import torch

from metacraft.authority import Document, Reference, reference_for
from metacraft.field import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)
import metacraft.field as field_package
from metacraft.field._storage import (
    ARRAY_DTYPE,
    ARRAY_MEDIA_TYPE,
    ARRAY_ORDER,
    array_bytes,
)
from metacraft.field.evidence import (
    admit_components,
    field_document,
    restore_field,
)
from metacraft.field.vector_angular_spectrum import LongitudinalPowerPlane
from metacraft.science.metalens.focus_evidence import (
    LONGITUDINAL_POWER_MEDIA_TYPE,
    focal_region_document,
    longitudinal_power_bytes,
    longitudinal_power_metadata,
    restore_focal_region,
)
from tests.field_fixtures import recorded_focal_region


ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "src" / "metacraft"


def _immutable(values: numpy.ndarray) -> numpy.ndarray:
    frozen = numpy.array(values, dtype="<c16", order="C", copy=True)
    frozen.setflags(write=False)
    return frozen


def _field_references(
    field: Field,
) -> tuple[
    dict[str, Reference],
    dict[str, Reference],
    dict[Reference, bytes],
]:
    return _component_references(
        field.electric_components,
        field.magnetic_components,
    )


def _component_references(
    electric_components: tuple[FieldComponent, ...],
    magnetic_components: tuple[FieldComponent, ...],
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


def _electric_only_field() -> Field:
    electric_x = _immutable(numpy.ones((3, 4), dtype="<c16"))
    electric_y = _immutable(numpy.zeros((3, 4), dtype="<c16"))
    return Field(
        wavelength_m=400e-9,
        surface=PlaneSurface(0.0, 200e-9, (3, 4)),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            FieldComponent("x", electric_x),
            FieldComponent("y", electric_y),
        ),
        source_references=(reference_for(b"source"),),
        incident_reference_power=4.0,
    )


def test_component_admission_keeps_one_raw_object_contract() -> None:
    """
    Electric and magnetic evidence share bytes while naming their quantity.
    """

    electric = FieldComponent(
        "x",
        _immutable(numpy.ones((2, 3), dtype="<c16")),
    )
    magnetic = FieldComponent(
        "x",
        _immutable(2 * numpy.ones((2, 3), dtype="<c16")),
    )
    observed: list[
        tuple[bytes, str, dict[str, object], Reference]
    ] = []

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
        observed.append(
            (body, media_type, descriptive_metadata, reference)
        )
        return reference

    electric_references, magnetic_references = admit_components(
        (electric,),
        (magnetic,),
        admit,
    )

    assert [item[:3] for item in observed] == [
        (
            array_bytes(electric.values),
            ARRAY_MEDIA_TYPE,
            {
                "component": "x",
                "dtype": ARRAY_DTYPE,
                "order": ARRAY_ORDER,
                "quantity": "electric field",
                "shape": [2, 3],
                "unit": "V/m",
            },
        ),
        (
            array_bytes(magnetic.values),
            ARRAY_MEDIA_TYPE,
            {
                "component": "x",
                "dtype": ARRAY_DTYPE,
                "order": ARRAY_ORDER,
                "quantity": "magnetic field",
                "shape": [2, 3],
                "unit": "V/m",
            },
        ),
    ]
    assert electric_references == {"x": observed[0][3]}
    assert magnetic_references == {"x": observed[1][3]}


def test_field_round_trip_closes_an_electric_only_component_field() -> None:
    """
    An electric-only Field round-trips through the shared storage mechanics.
    """

    field = _electric_only_field()
    electric, _magnetic, by_reference = _field_references(field)
    document = field_document(
        "metacraft.science.fixture.field",
        field,
        electric,
    )

    restored = restore_field(document, by_reference.__getitem__)

    assert numpy.array_equal(restored.electric("x"), field.electric("x"))
    assert numpy.array_equal(restored.electric("y"), field.electric("y"))
    assert restored.magnetic_components == ()
    assert document.schema_identifier == "metacraft.science.fixture.field"
    assert document.values["storage"] == {
        "dtype": ARRAY_DTYPE,
        "order": ARRAY_ORDER,
        "unit": "V/m",
    }


def test_focal_region_round_trip_closes_a_multi_plane_observation() -> None:
    """
    A multi-plane FocalRegion (magnetic + many axial distances) round-trips.
    """

    principal = _immutable(
        numpy.full((5, 6), 0.5 + 0.25j, dtype="<c16")
    )
    region = recorded_focal_region(
        principal,
        axial_distances_m=(1.6e-6, 1.8e-6, 2e-6, 2.2e-6, 2.4e-6),
        axial_peak_intensities=(0.1, 0.4, 1.0, 0.4, 0.1),
        found_focus_m=2e-6,
        expected_focus_m=2e-6,
        incident_reference_power=4.0,
        transmitted_x_power=4.0,
    )
    electric, magnetic, by_reference = _component_references(
        region.electric_components,
        region.magnetic_components,
    )
    binding = reference_for(b"angular spectrum binding")
    document = focal_region_document(
        region,
        electric,
        binding_reference=binding,
        field_reference=region.source_references[0],
        magnetic_component_references=magnetic,
    )

    restored = restore_focal_region(document, by_reference.__getitem__)

    assert numpy.array_equal(
        restored.electric("x"), region.electric("x")
    )
    assert numpy.array_equal(
        restored.electric("y"), region.electric("y")
    )
    assert restored.axial_distances_m == region.axial_distances_m
    assert document.values["binding"] == binding.as_mapping()


def test_vector_focal_region_restores_its_exact_power_plane_bytes() -> None:
    """A selected Cartesian field and its Poynting plane stay one fact."""

    base = recorded_focal_region(
        _immutable(numpy.ones((2, 3), dtype="<c16")),
        axial_distances_m=(1.6e-6, 2e-6, 2.4e-6),
        axial_peak_intensities=(0.5, 1.0, 0.5),
        found_focus_m=2e-6,
        expected_focus_m=2e-6,
    )
    zeros = _immutable(numpy.zeros((2, 3), dtype="<c16"))
    surface = PlaneSurface(2e-6, base.spacing_m, (2, 3))
    power_plane = LongitudinalPowerPlane(
        surface,
        torch.arange(6, dtype=torch.float64).reshape(2, 3),
    )
    region = replace(
        base,
        basis=ComponentBasis.CARTESIAN,
        observed_components=("x", "y", "z"),
        electric_components=(
            FieldComponent("x", base.electric("x")),
            FieldComponent("y", zeros),
            FieldComponent("z", zeros),
        ),
        component_axial_peak_intensities={
            "x": base.axial_peak_intensities,
            "y": (0.0, 0.0, 0.0),
            "z": (0.0, 0.0, 0.0),
        },
        transmitted_aperture_power={},
        vector_input_power_w=2.0,
        vector_output_power_w=1.0,
        longitudinal_power_plane=power_plane,
    )
    electric, magnetic, by_reference = _component_references(
        region.electric_components,
        region.magnetic_components,
    )
    power_body = longitudinal_power_bytes(power_plane)
    power_reference = reference_for(
        power_body,
        media_type=LONGITUDINAL_POWER_MEDIA_TYPE,
        descriptive_metadata=longitudinal_power_metadata(surface),
    )
    by_reference[power_reference] = power_body
    document = focal_region_document(
        region,
        electric,
        binding_reference=reference_for(b"vector binding"),
        field_reference=region.source_references[0],
        magnetic_component_references=magnetic,
        longitudinal_power_reference=power_reference,
    )

    restored = restore_focal_region(document, by_reference.__getitem__)

    assert restored.longitudinal_power_plane is not None
    assert restored.longitudinal_power_plane.surface == surface
    assert torch.equal(
        restored.longitudinal_power_plane.power_density_w_per_m2,
        power_plane.power_density_w_per_m2,
    )
    assert restored.vector_input_power_w == 2.0
    assert restored.vector_output_power_w == 1.0

    with pytest.raises(ValueError, match="focal_region_vector_power_invalid"):
        replace(
            region,
            focus_plane_position_m=region.focus_plane_position_m + 1e-9,
        )


def test_fixed_point_focal_region_is_a_stale_immutable_witness(
    tmp_path: Path,
) -> None:
    """The pre-cutover manifest remains audit-only and fails closed."""

    region = recorded_focal_region(
        numpy.ones((2, 2), dtype="<c16"),
        axial_distances_m=(1.6e-6, 2e-6, 2.4e-6),
        axial_peak_intensities=(0.5, 1.0, 0.5),
        found_focus_m=2e-6,
        expected_focus_m=2e-6,
    )
    electric, magnetic, by_reference = _component_references(
        region.electric_components,
        region.magnetic_components,
    )
    current = focal_region_document(
        region,
        electric,
        binding_reference=reference_for(b"binding"),
        field_reference=region.source_references[0],
        magnetic_component_references=magnetic,
    )
    old_values = dict(current.values)
    old_values.pop("vector_input_power_w")
    old_values.pop("longitudinal_power_plane")
    old_values.pop("focus_plane_position_m")
    assert current.schema_identifier == (
        "metacraft.science.metalens.retained_focal_region"
    )
    old = Document(
        "metacraft.science.metalens.focal_region",
        old_values,
    )
    witness = tmp_path / "focal-region-v1.json"
    witness.write_bytes(old.to_bytes())
    before = witness.read_bytes()

    assert hashlib.sha256(before).hexdigest() == (
        "dab15e54fbb3168a40c09ff6e2884d303af86f94ea781b65f0035eca007beadc"
    )
    with pytest.raises(ValueError, match="focal_region_schema_invalid"):
        restore_focal_region(
            Document.from_bytes(witness.read_bytes()),
            by_reference.__getitem__,
        )
    assert witness.read_bytes() == before


def test_field_decoder_rejects_same_size_bytes_from_another_reference() -> None:
    """
    A Field restores only the raw bytes named by its component references.
    """

    field = _electric_only_field()
    electric, _magnetic, _by_reference = _field_references(field)
    document = field_document(
        "metacraft.science.fixture.field",
        field,
        electric,
    )
    wrong_body = b"\xa5" * electric["x"].size_bytes

    with pytest.raises(ValueError, match="field_evidence_mismatch"):
        restore_field(document, lambda _reference: wrong_body)


def test_focal_region_decoder_rejects_same_size_bytes_from_another_reference() -> None:
    """
    A FocalRegion restores only the raw bytes named by its component references.
    """

    region = recorded_focal_region(
        _immutable(numpy.ones((2, 2), dtype="<c16")),
        axial_distances_m=(1.6e-6, 2e-6, 2.4e-6),
        axial_peak_intensities=(0.5, 1.0, 0.5),
        found_focus_m=2e-6,
        expected_focus_m=2e-6,
    )
    electric, magnetic, _by_reference = _component_references(
        region.electric_components,
        region.magnetic_components,
    )
    document = focal_region_document(
        region,
        electric,
        binding_reference=reference_for(b"binding"),
        field_reference=region.source_references[0],
        magnetic_component_references=magnetic,
    )
    wrong_body = b"\xa5" * electric["x"].size_bytes

    with pytest.raises(
        ValueError,
        match="focal_region_evidence_mismatch",
    ):
        restore_focal_region(document, lambda _reference: wrong_body)


def test_field_decoder_rejects_a_wrong_storage_dtype() -> None:
    """
    Field admission refuses a manifest declaring the wrong component dtype.
    """

    field = _electric_only_field()
    electric, _magnetic, by_reference = _field_references(field)
    document = field_document(
        "metacraft.science.fixture.field",
        field,
        electric,
    )
    broken = Document(
        document.schema_identifier,
        {**document.values, "storage": {"dtype": "<f8", "order": "C", "unit": "V/m"}},
    )

    with pytest.raises(ValueError, match="field_evidence_mismatch"):
        restore_field(broken, by_reference.__getitem__)


def test_field_decoder_rejects_a_wrong_component_shape() -> None:
    """
    Field admission refuses bytes whose size disagrees with the manifest shape.
    """

    field = _electric_only_field()
    electric, _magnetic, _by_reference = _field_references(field)
    # Re-declare the manifest shape as (2, 2) while the bytes encode (3, 4).
    document = field_document(
        "metacraft.science.fixture.field",
        field,
        electric,
    )
    values = dict(document.values)
    surface = dict(values["surface"])  # type: ignore[arg-type]
    surface["shape"] = [2, 2]
    values["surface"] = surface
    broken = Document(document.schema_identifier, values)
    fetch_bytes = array_bytes(field.electric("x"))

    with pytest.raises(ValueError, match="field_evidence_mismatch"):
        restore_field(broken, lambda _reference: fetch_bytes)


def test_field_decoder_rejects_an_incomplete_component_reference_set() -> None:
    """
    Field admission refuses a manifest missing one required component reference.
    """

    field = _electric_only_field()
    electric, _magnetic, _by_reference = _field_references(field)
    incomplete = {name: ref for name, ref in electric.items() if name == "x"}
    with pytest.raises(ValueError, match="field_component_references_incomplete"):
        field_document(
            "metacraft.science.fixture.field",
            field,
            incomplete,
        )


def test_focal_region_decoder_rejects_a_wrong_storage_dtype() -> None:
    """
    FocalRegion admission refuses a manifest declaring the wrong dtype.
    """

    region = recorded_focal_region(
        _immutable(numpy.ones((2, 2), dtype="<c16")),
        axial_distances_m=(1.6e-6, 2e-6, 2.4e-6),
        axial_peak_intensities=(0.5, 1.0, 0.5),
        found_focus_m=2e-6,
        expected_focus_m=2e-6,
    )
    electric, magnetic, by_reference = _component_references(
        region.electric_components,
        region.magnetic_components,
    )
    document = focal_region_document(
        region,
        electric,
        binding_reference=reference_for(b"binding"),
        field_reference=region.source_references[0],
        magnetic_component_references=magnetic,
    )
    broken = Document(
        document.schema_identifier,
        {
            **document.values,
            "storage": {
                "dtype": "<f4",
                "order": ARRAY_ORDER,
                "unit": "V/m",
            },
        },
    )

    with pytest.raises(ValueError, match="focal_region_evidence_mismatch"):
        restore_focal_region(broken, by_reference.__getitem__)


def test_focal_region_decoder_rejects_a_wrong_component_media_type() -> None:
    """
    FocalRegion admission refuses a component object of the wrong media type.
    """

    region = recorded_focal_region(
        _immutable(numpy.ones((2, 2), dtype="<c16")),
        axial_distances_m=(1.6e-6, 2e-6, 2.4e-6),
        axial_peak_intensities=(0.5, 1.0, 0.5),
        found_focus_m=2e-6,
        expected_focus_m=2e-6,
    )
    raw = array_bytes(region.electric("x"))
    wrong = reference_for(raw, media_type="application/x-npy")
    document = Document(
        "metacraft.science.metalens.retained_focal_region",
        {
            "axial_distances_m": ["1.6e-6", "2e-6", "2.4e-6"],
            "axial_peak_intensities": ["0.5", "1.0", "0.5"],
            "basis": "transverse linear",
            "binding": reference_for(b"binding").as_mapping(),
            "component_axial_peak_intensities": {
                "x": ["0.5", "1.0", "0.5"],
                "y": ["0", "0", "0"],
            },
            "electric_components": {
                "x": wrong.as_mapping(),
                "y": wrong.as_mapping(),
            },
            "expected_focus_m": "2e-6",
            "found_focus_m": "2e-6",
            "frame": {
                "normal_axis": "z",
                "propagation_direction": "positive",
                "sample_order": ["y", "x"],
            },
            "incident_reference_power": "1",
            "magnetic_components": {},
            "medium": {"identity": "air"},
            "observed_components": ["x"],
            "realization": {
                "identity": "metacraft.field.angular_spectrum"
            },
            "shape": [2, 2],
            "source_field": reference_for(b"field").as_mapping(),
            "source_references": {
                "source_001": reference_for(b"src").as_mapping(),
            },
            "spacing_m": "1e-7",
            "storage": {
                "dtype": ARRAY_DTYPE,
                "order": ARRAY_ORDER,
                "unit": "V/m",
            },
            "transmitted_aperture_power": {"x": "1", "y": "0"},
            "wavelength_m": "4e-7",
        },
    )

    with pytest.raises(ValueError, match="focal_region_evidence_mismatch"):
        restore_focal_region(document, lambda _reference: raw)


def test_focal_region_decoder_rejects_a_wrong_component_shape() -> None:
    """
    FocalRegion admission refuses bytes that disagree with the manifest shape.
    """

    region = recorded_focal_region(
        _immutable(numpy.ones((2, 2), dtype="<c16")),
        axial_distances_m=(1.6e-6, 2e-6, 2.4e-6),
        axial_peak_intensities=(0.5, 1.0, 0.5),
        found_focus_m=2e-6,
        expected_focus_m=2e-6,
    )
    electric, magnetic, by_reference = _component_references(
        region.electric_components,
        region.magnetic_components,
    )
    document = focal_region_document(
        region,
        electric,
        binding_reference=reference_for(b"binding"),
        field_reference=region.source_references[0],
        magnetic_component_references=magnetic,
    )
    values = dict(document.values)
    values["shape"] = [3, 3]
    broken = Document(document.schema_identifier, values)

    with pytest.raises(ValueError, match="focal_region_evidence_mismatch"):
        restore_focal_region(broken, by_reference.__getitem__)


def test_identical_binary_facts_receive_identical_storage_treatment() -> None:
    """
    The same immutable component array encodes and restores to one canonical
    form regardless of which scientific document wraps it.
    """

    base = numpy.full((4, 4), 0.75 - 0.25j, dtype="<c16")
    field = Field(
        wavelength_m=400e-9,
        surface=PlaneSurface(0.0, 200e-9, (4, 4)),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            FieldComponent("x", _immutable(base)),
            FieldComponent("y", _immutable(numpy.zeros_like(base))),
        ),
        source_references=(reference_for(b"source"),),
        incident_reference_power=4.0,
    )
    region = recorded_focal_region(
        _immutable(base),
        axial_distances_m=(1.6e-6, 2e-6, 2.4e-6),
        axial_peak_intensities=(0.5, 1.0, 0.5),
        found_focus_m=2e-6,
        expected_focus_m=2e-6,
    )

    assert array_bytes(field.electric("x")) == array_bytes(
        region.electric("x")
    )
    assert array_bytes(field.electric("x")) == array_bytes(
        _immutable(base)
    )
    # Repeated encoding is deterministic and restores exactly.
    encoded = array_bytes(_immutable(base))
    restored = numpy.frombuffer(
        encoded, dtype=ARRAY_DTYPE
    ).reshape((4, 4), order=ARRAY_ORDER)
    assert numpy.array_equal(restored, base)


def test_the_shared_storage_module_is_not_exported_from_metacraft_field() -> None:
    """
    The private field-storage helper stays out of the package's public surface.

    Python exposes any imported submodule as an attribute of its parent
    package, so ``_storage`` becomes reachable as ``field._storage`` once a
    sibling Module imports it. The binding contract is therefore the package
    manifest: the private helper is not named in ``__all__`` and the package
    ``__init__`` never imports it.
    """

    public_names = set(field_package.__all__)
    storage_names = {
        name
        for name in dir(field_package)
        if "storage" in name.casefold()
    }
    assert public_names.isdisjoint(storage_names)
    assert "_storage" not in public_names
    assert not any(
        name.startswith("_storage") for name in public_names
    )

    # The package __init__ never imports the private module or its names.
    init_path = PACKAGE / "field" / "__init__.py"
    init_tree = ast.parse(init_path.read_text(encoding="utf-8-sig"))
    init_imports_storage = False
    for node in ast.walk(init_tree):
        if isinstance(node, ast.ImportFrom) and (
            (node.module or "").endswith("_storage")
            or any(alias.name == "_storage" for alias in node.names)
        ):
            init_imports_storage = True
        elif isinstance(node, ast.Import) and any(
            alias.name.endswith("_storage") for alias in node.names
        ):
            init_imports_storage = True
    assert not init_imports_storage


def test_the_shared_storage_module_owns_the_binary_array_rules() -> None:
    """
    The private module owns byte restoration and media-type validation, so the
    scientific evidence modules delegate rather than re-implement them.
    """

    storage_path = PACKAGE / "field" / "_storage.py"
    assert storage_path.exists(), "shared storage module must exist"
    source = storage_path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    exported = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    # The rules named in the ticket live here, not in the scientific modules.
    assert {"array_bytes", "restore_array"}.issubset(exported)
    # The storage module imports no scientific or solver meaning.
    forbidden_roots = {
        "_local",
        "advice",
        "local",
        "runner",
        "science",
        "solvers",
        "workstation",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            roots = node.module.split(".")
        elif isinstance(node, ast.Import):
            roots = [
                part
                for alias in node.names
                for part in alias.name.split(".")
            ]
        else:
            continue
        assert not (
            set(roots) & forbidden_roots
        ), f"storage imports forbidden root: {set(roots) & forbidden_roots}"

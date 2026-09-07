from __future__ import annotations

import math
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import numpy
import pytest
import torch

import metacraft.science.metalens._aplanatic_reference as aplanatic_reference_module
from metacraft.authority import Document, Reference
from metacraft.authority.reference import reference_for
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
from metacraft.field.vector_angular_spectrum import LongitudinalPowerPlane
from metacraft.field.debye import DebyeObservation
from metacraft.field.fast_debye import (
    CZT_DEBYE_REALIZATION,
    CZTDebyeRealization,
    FFTDebyeRealization,
)
from metacraft.field.debye_qualification import form_aplanatic_reference
from metacraft.science.metalens.aperture import (
    Aperture,
    Cell,
    Circle,
    Material,
    Rectangle,
    Response,
    State,
    aperture_document,
    lattice_for,
)
from metacraft.science.metalens.brief import (
    ControlStrategy,
    MonochromaticSpectrum,
)
from metacraft.science.metalens.focal_field_comparison import (
    FocalComparisonComponentsMismatch,
    FocalComparisonGridMismatch,
    FocalFieldComparison,
    compare_vector_fields,
    require_matching_focal_field,
)
from metacraft.science.metalens.focus import FocalRegion, Focus, evaluate_vector_focus
from metacraft.science.metalens.geometric_phase import OrientationRelation
from metacraft.science.metalens.pointwise import (
    CellSurface,
    CellSurfaceTable,
    assign_pointwise_cells,
    derive_geometric_surface_transform,
    form_geometric_surface_field,
    form_pointwise_surface_field,
    identify_geometric_surface_cautions,
    restrict_surfaces_to_aperture,
    select_pointwise_cells,
)
from metacraft.science.metalens.propagation_phase import (
    PropagationCellLibrary,
    PropagationResponse,
)
from metacraft.science.phase import FULL_TURN, canonical_phase
from metacraft.science.result import EvidenceOrigin
from tests.field_fixtures import recorded_focal_region
from tests.metalens_field_fixtures import (
    cartesian_focal_region as _cartesian_focal_region,
    metalens_design as _design,
)


def test_pointwise_selection_is_cyclic_powered_and_order_independent() -> None:
    weak_z = _propagation_response("z-cell", "0", magnitude="0.4")
    strong_z = _propagation_response("a-cell", "0", magnitude="0.9")
    strong_a = _propagation_response("b-cell", "0", magnitude="0.9")
    opposite = _propagation_response(
        "opposite",
        str(FULL_TURN / 2),
        magnitude="1",
    )
    targets = numpy.asarray(
        (0.0, float(FULL_TURN) - 1e-13, math.pi),
        dtype=numpy.float64,
    )

    selected = select_pointwise_cells(
        targets,
        (weak_z, strong_a, opposite, strong_z),
        device="cpu",
        maximum_sites_per_chunk=2,
    )
    reversed_selection = select_pointwise_cells(
        targets,
        (opposite, strong_z, strong_a, weak_z),
        device="cpu",
        maximum_sites_per_chunk=3,
    )

    assert selected.tolist() == ["a-cell", "a-cell", "opposite"]
    numpy.testing.assert_array_equal(selected, reversed_selection)


def test_pointwise_selection_chunks_one_million_sites_without_identity_drift() -> None:
    candidates = (
        _propagation_response("zero", "0", magnitude="0.8"),
        _propagation_response(
            "half",
            str(FULL_TURN / 2),
            magnitude="0.8",
        ),
    )
    phases = numpy.linspace(
        0,
        float(FULL_TURN),
        1_000_000,
        endpoint=False,
        dtype=numpy.float64,
    )

    small = select_pointwise_cells(
        phases,
        candidates,
        device="cpu",
        maximum_sites_per_chunk=4_096,
    )
    large = select_pointwise_cells(
        phases,
        tuple(reversed(candidates)),
        device="cpu",
        maximum_sites_per_chunk=131_072,
    )

    numpy.testing.assert_array_equal(small, large)
    assert small.shape == phases.shape


def test_pointwise_aperture_uses_the_complete_admitted_surface_table() -> None:
    responses = tuple(
        _propagation_response(
            f"cell-{index}",
            str(FULL_TURN * index / 4),
            magnitude=str(0.7 + 0.05 * index),
            diameter_nm=40 + 10 * index,
        )
        for index in range(4)
    )
    library = _library(responses)
    surfaces = _surface_table(
        library.evidence_reference,
        tuple(response.cell.identity for response in responses),
        basis=RequestedInputBasis.X_LINEAR,
    )
    surfaces_reference = reference_for(surfaces.document().to_bytes())

    aperture = assign_pointwise_cells(
        _design(ControlStrategy.PROPAGATION_PHASE),
        library,
        surfaces,
        surfaces_reference=surfaces_reference,
        device="cpu",
        maximum_sites_per_chunk=3,
    )
    reordered = assign_pointwise_cells(
        _design(ControlStrategy.PROPAGATION_PHASE),
        _library(tuple(reversed(responses))),
        CellSurfaceTable(
            surfaces.source_reference,
            tuple(reversed(surfaces.surfaces)),
        ),
        surfaces_reference=surfaces_reference,
        device="cpu",
        maximum_sites_per_chunk=17,
    )

    assert aperture.phase_levels is None
    assert {cell.identity for cell in aperture.cells} == {
        response.cell.identity for response in responses
    }
    assert surfaces_reference in aperture.evidence
    assert aperture_document(aperture).to_bytes() == (
        aperture_document(reordered).to_bytes()
    )
    used_surfaces = restrict_surfaces_to_aperture(aperture, surfaces)
    assert set(used_surfaces) == set(
        aperture.state_identities[aperture.is_occupied].tolist()
    )
    formed = form_pointwise_surface_field(
        aperture,
        surfaces,
        aperture_reference=reference_for(aperture_document(aperture).to_bytes()),
    )
    assert formed.basis is ComponentBasis.TRANSVERSE_LINEAR
    assert formed.component_names == ("x", "y")
    assert formed.surface.shape == tuple(
        dimension * 2 for dimension in aperture.is_occupied.shape
    )


def test_geometric_surface_applies_declared_twice_orientation_phase_only() -> None:
    design = _design(ControlStrategy.GEOMETRIC_PHASE)
    lattice = lattice_for(design, spacing_nm=200)
    choice_reference = reference_for(b"one admitted cell choice")
    convention_reference = reference_for(b"one convention")
    source_x = reference_for(b"x response")
    source_y = reference_for(b"y response")
    orientations = OrientationRelation(
        cell_id="fin",
        converted_phase=Decimal(0),
        phase_sign=1,
        cell_choice_reference=choice_reference,
        binding_reference=reference_for(b"polarization binding"),
        library_reference=reference_for(b"jones library"),
        convention_reference=convention_reference,
        source_references=(source_x, source_y),
    )
    orientations_reference = reference_for(orientations.document().to_bytes())
    cell = Cell(
        identity="fin",
        atom=Material("titanium dioxide", "solver native"),
        substrate=Material("glass", "solver native"),
        period_nm=200,
        height_nm=600,
        geometry=Rectangle(50, 100),
        source=source_x,
    )
    states = []
    identities = numpy.full(lattice.shape, "", dtype="<U24")
    for index, phase in enumerate(lattice.target_phase[lattice.is_occupied]):
        target = canonical_phase(Decimal(str(float(phase))))
        orientation = orientations.for_phase(target)
        identity = f"orientation-{index:06d}"
        states.append(
            State(
                identity=identity,
                cell_identity=cell.identity,
                responses=(
                    Response(
                        "converted",
                        Decimal(1),
                        Decimal(0),
                        Decimal(1),
                    ),
                ),
                source=orientations_reference,
                target_phase=target,
                realized_phase=orientations.realized_phase(orientation),
                useful_power=Decimal(1),
                leakage_power=Decimal(0),
                orientation_rad=orientation,
            )
        )
        position = tuple(numpy.argwhere(lattice.is_occupied)[index])
        identities[position] = identity
    aperture = Aperture(
        cells=(cell,),
        states=tuple(states),
        coordinates_nm=lattice.coordinates_nm,
        is_occupied=lattice.is_occupied,
        target_phase=lattice.target_phase,
        state_identities=identities,
        spacing_nm=lattice.spacing_nm,
        half_span_nm=lattice.half_span_nm,
        evidence=(choice_reference, orientations_reference),
        footprint=lattice.footprint,
        phase_levels=None,
    )
    x_linear = AdmittedReferenceSurface(
        _surface_response(
            RequestedInputBasis.X_LINEAR,
            cell.identity,
            half_wave_axis="x",
        ),
        reference_for(b"one x-linear sampled surface"),
    )
    y_linear = AdmittedReferenceSurface(
        _surface_response(
            RequestedInputBasis.Y_LINEAR,
            cell.identity,
            half_wave_axis="y",
        ),
        reference_for(b"one y-linear sampled surface"),
    )
    transform = derive_geometric_surface_transform(
        orientations,
        x_linear,
        y_linear,
        relation_reference=orientations_reference,
        requested_input_basis=RequestedInputBasis.RIGHT_CIRCULAR,
    )
    transform_reference = reference_for(transform.document().to_bytes())

    field = form_geometric_surface_field(
        aperture,
        orientations,
        x_linear,
        y_linear,
        transform,
        aperture_reference=reference_for(aperture_document(aperture).to_bytes()),
        transform_reference=transform_reference,
        device="cpu",
        maximum_sites_per_chunk=2,
    )

    assert field.basis is ComponentBasis.TRANSVERSE_LINEAR
    assert field.component_names == ("x", "y")
    first_row, first_column = numpy.argwhere(aperture.is_occupied)[0]
    block_x = field.electric("x")[
        first_row * 2 : (first_row + 1) * 2,
        first_column * 2 : (first_column + 1) * 2,
    ]
    expected_phase = numpy.exp(1j * aperture.target_phase[first_row, first_column])
    numpy.testing.assert_allclose(
        block_x,
        expected_phase / math.sqrt(2),
        atol=1e-12,
    )
    cautions = identify_geometric_surface_cautions(
        transform,
        transform_reference,
        x_linear.response,
        y_linear.response,
    )
    assert tuple(caution.concern for caution in cautions) == (
        "higher orders possible",
        "locally periodic assembly",
        "analytic geometric-phase surface transform",
    )
    assert transform.spatial_rule == "sampled coordinates remain unrotated"


def test_focal_comparison_retains_qualified_bindings_without_thresholds() -> None:
    actual = {
        name: numpy.asarray(((1 + 1j, 2),), dtype=numpy.complex128)
        for name in ("x", "y", "z")
    }
    ideal = tuple(
        torch.tensor(values, dtype=torch.complex128) for values in actual.values()
    )
    actual_binding = reference_for(b"qualified vector angular spectrum")
    ideal_binding = reference_for(b"qualified Debye acceleration")
    comparison = compare_vector_fields(
        actual,
        ideal,  # type: ignore[arg-type]
        observed_field_reference=reference_for(b"actual field"),
        ideal_field_reference=reference_for(b"ideal field"),
        observed_binding_reference=actual_binding,
        ideal_binding_reference=ideal_binding,
        observed_method="vector angular spectrum",
        ideal_method="qualified Debye",
        input_longitudinal_power_w=1,
        output_longitudinal_power_w=0.99,
    )

    restored = FocalFieldComparison.from_document(comparison.document())

    assert restored == comparison
    assert restored.observed_binding_reference == actual_binding
    assert restored.ideal_binding_reference == ideal_binding
    assert restored.aligned_complex_error == 0
    assert restored.unit_integral_intensity_error == 0
    assert restored.observed_to_ideal_scale == 1 + 0j
    assert "qualified" not in restored.document().values
    assert "passed" not in restored.document().values

    retired = dict(restored.document().values)
    retired["source_comparisons"] = []
    with pytest.raises(ValueError, match="focal_comparison_document_invalid"):
        FocalFieldComparison.from_document(
            Document(restored.document().schema_identifier, retired)
        )


def test_focal_comparison_owns_component_and_grid_failures() -> None:
    reference = reference_for(b"comparison fault fixture")
    keywords = {
        "observed_field_reference": reference,
        "ideal_field_reference": reference,
        "observed_binding_reference": reference,
        "ideal_binding_reference": reference,
        "observed_method": "vector angular spectrum",
        "ideal_method": "CZT Richards--Wolf",
        "input_longitudinal_power_w": 1.0,
        "output_longitudinal_power_w": 1.0,
    }
    one = numpy.ones((1, 1), dtype=numpy.complex128)
    with pytest.raises(FocalComparisonComponentsMismatch):
        compare_vector_fields(
            {"x": one},
            tuple(torch.ones((1, 1), dtype=torch.complex128) for _ in range(3)),
            **keywords,
        )
    with pytest.raises(FocalComparisonGridMismatch):
        compare_vector_fields(
            {name: one for name in ("x", "y", "z")},
            tuple(torch.ones((2, 2), dtype=torch.complex128) for _ in range(3)),
            **keywords,
        )


@pytest.mark.parametrize(
    ("found_focus_m", "focus_plane_position_m", "expected_offset_m"),
    (
        (8e-6, 11e-6, -1e-6),
        (9e-6, 12e-6, 0.0),
        (10e-6, 13e-6, 1e-6),
    ),
    ids=("negative", "zero", "positive"),
)
def test_focal_region_keeps_distance_and_world_focus_coordinates_distinct(
    found_focus_m: float,
    focus_plane_position_m: float,
    expected_offset_m: float,
) -> None:
    """
    Relate a shifted propagation focus to its physical comparison plane.
    """

    region = recorded_focal_region(
        numpy.ones((5, 5), dtype=numpy.complex128),
        axial_distances_m=(8e-6, 9e-6, 10e-6),
        axial_peak_intensities=(0.2, 1.0, 0.3),
        expected_focus_m=9e-6,
        found_focus_m=found_focus_m,
    )
    region = replace(
        region,
        focus_plane_position_m=focus_plane_position_m,
    )

    assert region.aplanatic_axial_offset_m == pytest.approx(expected_offset_m)


@pytest.mark.parametrize(
    ("found_focus_m", "focus_plane_position_m", "expected_offset_m"),
    (
        (8e-6, 11e-6, -1e-6),
        (9e-6, 12e-6, 0.0),
        (10e-6, 13e-6, 1e-6),
    ),
    ids=("negative", "zero", "positive"),
)
def test_aplanatic_reference_is_calculated_and_stored_on_one_true_plane(
    monkeypatch: pytest.MonkeyPatch,
    found_focus_m: float,
    focus_plane_position_m: float,
    expected_offset_m: float,
) -> None:
    """
    Keep every aplanatic coordinate aligned with stored world metadata.
    """

    region = _cartesian_focal_region(
        found_focus_m=found_focus_m,
        focus_plane_position_m=focus_plane_position_m,
    )
    fft_realization = FFTDebyeRealization(device="cpu", pupil_samples=65)
    czt_realization = CZTDebyeRealization(device="cpu", pupil_samples=65)
    binding = Document("fixture.joint-aplanatic-binding", {})
    binding_reference = reference_for(binding.to_bytes())
    target_reference = reference_for(b"target phase")
    admitted: list[Field] = []
    observed_axial_offsets: list[float] = []

    class EvidenceBoundary:
        def fetch(self, reference: Reference) -> bytes:
            assert reference == binding_reference
            return binding.to_bytes()

        def restore_focal_region(self, _study: object) -> FocalRegion:
            return region

        def fact(self, _study: object, claim: str) -> object:
            assert claim == "target_phase"
            return SimpleNamespace(reference=target_reference)

        def admit_field(self, _task: object, field: Field) -> Reference:
            admitted.append(field)
            return reference_for(b"ideal field")

        def with_fact(
            self,
            study: object,
            _task: object,
            _reference: Reference,
        ) -> object:
            return study

    def observe_coordinates(*args, axial_offset_m, **kwargs):
        observed_axial_offsets.append(axial_offset_m)
        return form_aplanatic_reference(
            *args,
            axial_offset_m=axial_offset_m,
            **kwargs,
        )

    monkeypatch.setattr(
        aplanatic_reference_module,
        "form_aplanatic_reference",
        observe_coordinates,
    )
    monkeypatch.setattr(
        aplanatic_reference_module,
        "restore_aplanatic_reference_binding",
        lambda _document, _fetch: (fft_realization, czt_realization),
    )
    design = replace(
        _design(ControlStrategy.PROPAGATION_PHASE),
        operating_spectrum=MonochromaticSpectrum(532),
        numerical_aperture=Decimal("0.8"),
        focal_length_um=Decimal("9"),
    )

    aplanatic_reference_module.admit_aplanatic_reference(
        EvidenceBoundary(),  # type: ignore[arg-type]
        SimpleNamespace(design=design),  # type: ignore[arg-type]
        SimpleNamespace(binding_reference=binding_reference),  # type: ignore[arg-type]
    )

    assert observed_axial_offsets == pytest.approx([expected_offset_m])
    assert admitted[0].surface.position_m == focus_plane_position_m


@pytest.mark.parametrize(
    ("changed_field", "comparison_shape"),
    (
        ({"wavelength_m": 633e-9}, (5, 5)),
        ({"medium": Medium("glass")}, (5, 5)),
        ({"surface": PlaneSurface(11e-6, 100e-9, (5, 5))}, (5, 5)),
        ({"surface": PlaneSurface(10e-6, 110e-9, (5, 5))}, (5, 5)),
        ({}, (3, 3)),
    ),
    ids=("wavelength", "medium", "position", "spacing", "shape"),
)
def test_focal_comparison_rejects_physical_grid_mismatch_before_agreement(
    changed_field: dict[str, object],
    comparison_shape: tuple[int, int],
) -> None:
    """
    Reject unlike physical planes before comparing their sample values.
    """

    region = recorded_focal_region(
        numpy.ones((5, 5), dtype=numpy.complex128),
        axial_distances_m=(8e-6, 10e-6, 12e-6),
        axial_peak_intensities=(0.2, 1.0, 0.3),
        expected_focus_m=10e-6,
        found_focus_m=10e-6,
        wavelength_m=532e-9,
    )
    reference = Field(
        wavelength_m=region.wavelength_m,
        surface=PlaneSurface(
            region.focus_plane_position_m,
            region.spacing_m,
            region.shape,
        ),
        frame=region.frame,
        medium=region.medium,
        basis=region.basis,
        electric_components=region.electric_components,
        source_references=(reference_for(b"aplanatic reference"),),
        incident_reference_power=1.0,
    )

    with pytest.raises(
        FocalComparisonGridMismatch,
        match="focal_comparison_grid_mismatch",
    ):
        require_matching_focal_field(
            region,
            replace(reference, **changed_field),
            comparison_shape=comparison_shape,
        )


def test_vector_focus_keeps_low_na_boundary_and_uses_poynting_powers() -> None:
    values = numpy.asarray(
        (
            (0.1, 0.2, 0.3, 0.2, 0.1),
            (0.2, 0.5, 0.7, 0.5, 0.2),
            (0.3, 0.7, 1.0, 0.7, 0.3),
            (0.2, 0.5, 0.7, 0.5, 0.2),
            (0.1, 0.2, 0.3, 0.2, 0.1),
        ),
        dtype=numpy.float64,
    )
    electric_x = numpy.sqrt(values).astype(numpy.complex128)
    zeros = numpy.zeros_like(electric_x)
    electric_x.setflags(write=False)
    zeros.setflags(write=False)
    source = reference_for(b"vector focal field")
    expected_focus = 1e-6
    region = FocalRegion(
        wavelength_m=532e-9,
        spacing_m=100e-9,
        expected_focus_m=expected_focus,
        found_focus_m=expected_focus,
        focus_plane_position_m=expected_focus,
        observed_components=("x", "y", "z"),
        axial_distances_m=(0.8e-6, 0.9e-6, 1e-6, 1.1e-6, 1.2e-6),
        axial_peak_intensities=(0.1, 0.5, 1.0, 0.5, 0.1),
        component_axial_peak_intensities={
            "x": (0.1, 0.5, 1.0, 0.5, 0.1),
            "y": (0, 0, 0, 0, 0),
            "z": (0, 0, 0, 0, 0),
        },
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.CARTESIAN,
        electric_components=(
            FieldComponent("x", electric_x),
            FieldComponent("y", zeros),
            FieldComponent("z", zeros),
        ),
        source_references=(source,),
        incident_reference_power=1,
        transmitted_aperture_power={},
        vector_input_power_w=2,
        vector_output_power_w=1,
        longitudinal_power_plane=LongitudinalPowerPlane(
            PlaneSurface(
                expected_focus,
                100e-9,
                values.shape,
            ),
            torch.full(values.shape, 1e12, dtype=torch.float64),
        ),
        realization={"identity": "qualified vector angular spectrum"},
    )

    focus = evaluate_vector_focus(
        region,
        numerical_aperture=0.8,
    )

    assert isinstance(focus, Focus)
    assert focus.transmitted_fraction == 0.5
    assert math.isclose(focus.focused_fraction, 0.25)
    assert math.isclose(focus.focus_efficiency, 0.125)
    assert focus.found_focus_m == expected_focus
    assert focus.x_half_maximum.is_bracketed
    assert focus.y_half_maximum.is_bracketed
    assert focus.depth_of_focus.is_bracketed


def _propagation_response(
    identity: str,
    phase: str,
    *,
    magnitude: str,
    diameter_nm: int = 40,
) -> PropagationResponse:
    source = reference_for(f"{identity} source".encode())
    magnitude_value = Decimal(magnitude)
    return PropagationResponse(
        binding_reference=reference_for(b"transmission binding"),
        height_choice_reference=reference_for(b"height choice"),
        phase_planes="substrate-to-superstrate",
        cell=Cell(
            identity=identity,
            atom=Material("silicon", "fixture"),
            substrate=Material("silica", "fixture"),
            period_nm=200,
            height_nm=600,
            geometry=Circle(diameter_nm),
            source=source,
        ),
        transmission_real=magnitude_value,
        transmission_imaginary=Decimal(0),
        realized_phase=Decimal(phase),
        useful_power=magnitude_value * magnitude_value,
        leakage_power=Decimal(0),
        solver_status="complete",
        warnings=(),
        is_construction_valid=True,
        execution_origin=EvidenceOrigin.SYNTHETIC,
        source_reference=source,
    )


def _library(
    responses: tuple[PropagationResponse, ...],
) -> PropagationCellLibrary:
    document = PropagationCellLibrary.document_from(
        binding_reference=responses[0].binding_reference,
        height_choice_reference=responses[0].height_choice_reference,
        phase_planes=responses[0].phase_planes,
        responses=responses,
    )
    return PropagationCellLibrary(
        binding_reference=responses[0].binding_reference,
        height_choice_reference=responses[0].height_choice_reference,
        evidence_reference=reference_for(document.to_bytes()),
        phase_planes=responses[0].phase_planes,
        responses=responses,
    )


def _surface_table(
    source_reference: Reference,
    identities: tuple[str, ...],
    *,
    basis: RequestedInputBasis,
) -> CellSurfaceTable:
    return CellSurfaceTable(
        source_reference,
        tuple(
            CellSurface(
                identity,
                AdmittedReferenceSurface(
                    _surface_response(basis, identity),
                    reference_for(f"{identity} surface".encode()),
                ),
            )
            for identity in identities
        ),
    )


def _surface_response(
    basis: RequestedInputBasis,
    identity: str,
    *,
    half_wave_axis: str | None = None,
) -> ReferenceSurfaceResponse:
    source = reference_for(f"{identity} patch source".encode())
    if half_wave_axis == "x":
        electric_x = numpy.ones((2, 2), dtype=complex)
        electric_y = numpy.zeros((2, 2), dtype=complex)
    elif half_wave_axis == "y":
        electric_x = numpy.zeros((2, 2), dtype=complex)
        electric_y = -numpy.ones((2, 2), dtype=complex)
    else:
        electric_x = numpy.ones((2, 2), dtype=complex)
        electric_y = numpy.zeros((2, 2), dtype=complex)
    electric_z = numpy.zeros((2, 2), dtype=complex)
    for values in (electric_x, electric_y, electric_z):
        values.setflags(write=False)
    field = Field(
        wavelength_m=800e-9,
        surface=PlaneSurface(600e-9, 100e-9, (2, 2)),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.CARTESIAN,
        electric_components=(
            FieldComponent("x", electric_x),
            FieldComponent("y", electric_y),
            FieldComponent("z", electric_z),
        ),
        source_references=(source,),
        incident_reference_power=1,
    )
    return ReferenceSurfaceResponse(
        field=field,
        requested_input_basis=basis,
        order_regime="multi order",
        transmitted_power=0.8,
    )

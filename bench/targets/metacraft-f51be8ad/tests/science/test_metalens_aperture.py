from __future__ import annotations

import hashlib

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

import numpy as np
import pytest

from metacraft.authority import Document, Reference, reference_for
from metacraft.science import compile_study
from metacraft.science.metalens.aperture import (
    Aperture,
    ApertureIntentMismatch,
    Cell,
    Circle,
    Material,
    Lattice,
    Rectangle,
    Response,
    State,
    aperture_document,
    assign_discrete_orientations,
    assign_continuous_orientations,
    assign_quantized,
    lattice_for,
    resolve_lattice,
)
from metacraft.science.metalens.brief import (
    ApertureExtent,
    ApertureFootprint,
    ApertureIntent,
)
from metacraft.science.metalens.design import (
    MetalensDesign,
    require_metalens_design,
)
from metacraft.science.metalens.height import HeightAdviceBasis
from metacraft.science.phase import nearest_phase_levels, uniform_targets
from metacraft.science.result import EvidenceOrigin
from metacraft.science.study import Study
from metacraft.science.metalens.geometric_phase import (
    CellChoice,
    ComplexCoefficient,
    JonesResponse,
    LEGACY_PB_RESPONSE_RANKING,
    PolarizationConvention,
)
from metacraft.science.metalens.geometric_phase import (
    derive_orientation_relation,
    form_orientation_sets,
)
from examples import select_metalens_benchmark_case
from tests.brief_fixtures import (
    continuous_achromatic_brief,
    continuous_achromatic_publication_brief,
    geometric_brief,
    propagation_brief,
)


def _reference_hash(name: str) -> str:
    return f"sha256:{hashlib.sha256(name.encode()).hexdigest()}"

def _reference(name: str) -> Reference:
    return Reference(
        content_hash=_reference_hash(name),
        media_type="application/json",
        metadata_content_hash=_reference_hash("metadata-" + name),
        size_bytes=len(name),
    )


def _propagation_design() -> MetalensDesign:
    return require_metalens_design(compile_study(propagation_brief()))


def _geometric_design() -> MetalensDesign:
    return require_metalens_design(compile_study(geometric_brief()))


def _continuous_design() -> MetalensDesign:
    outcome = compile_study(continuous_achromatic_brief())
    assert isinstance(outcome, Study)
    return require_metalens_design(outcome)


def _continuous_publication_design() -> MetalensDesign:
    outcome = compile_study(continuous_achromatic_publication_brief())
    assert isinstance(outcome, Study)
    return require_metalens_design(outcome)


def _quantized_states(levels: int) -> tuple[tuple[Cell, ...], tuple[State, ...]]:
    targets = uniform_targets(levels)
    cells = tuple(
        Cell(
            identity=f"cell:circle:{level:03d}",
            atom=Material("silicon nitride", "solver native"),
            substrate=Material("silica", "solver native"),
            period_nm=200,
            height_nm=600,
            geometry=Circle(diameter_nm=80 + level),
            source=_reference(f"cell-{level}"),
        )
        for level in range(levels)
    )
    states = tuple(
        State(
            identity=f"state:level:{level:03d}",
            cell_identity=cells[level].identity,
            responses=(
                Response(
                    channel="transmission",
                    real_part=Decimal(str(round(level / levels, 3))),
                    imaginary_part=Decimal("0"),
                    power=Decimal("1"),
                ),
            ),
            source=_reference(f"state-{level}"),
            target_phase=targets[level],
            realized_phase=targets[level],
            useful_power=Decimal("1"),
            leakage_power=Decimal("0"),
            phase_level=level,
        )
        for level in range(levels)
    )
    return cells, states


def _geometric_choice() -> tuple[CellChoice, Reference]:
    convention = PolarizationConvention(circular_input="right")
    convention_reference = reference_for(convention.document().to_bytes())
    source_x = _reference("basis-x")
    source_y = _reference("basis-y")
    choice = CellChoice(
        cell=Cell(
            identity="cell:fin:080x140",
            atom=Material("titanium dioxide", "solver native"),
            substrate=Material("silica", "solver native"),
            period_nm=200,
            height_nm=600,
            geometry=Rectangle(short_side_nm=80, long_side_nm=140),
            source=source_x,
        ),
        jones=JonesResponse(
            output_x_from_input_x=ComplexCoefficient(Decimal("0.8"), Decimal(0)),
            output_y_from_input_x=ComplexCoefficient(Decimal("0.1"), Decimal(0)),
            output_x_from_input_y=ComplexCoefficient(Decimal("0.1"), Decimal(0)),
            output_y_from_input_y=ComplexCoefficient(
                Decimal("-0.8"), Decimal(0)
            ),
        ),
        converted=ComplexCoefficient(Decimal("0.7"), Decimal("0.1")),
        converted_phase=Decimal("0.1418970546041639"),
        retained=ComplexCoefficient(Decimal("0.1"), Decimal("-0.02")),
        retained_phase=Decimal("-0.1973955598498808"),
        useful_power=Decimal("0.50"),
        leakage_power=Decimal("0.0104"),
        loss=Decimal("-0.4896"),
        binding_reference=_reference("binding"),
        height_domain_reference=_reference("height-domain"),
        height_basis=HeightAdviceBasis(_reference("height-advice")),
        height_choice_reference=_reference("height-choice"),
        library_reference=_reference("jones-library"),
        convention=convention,
        convention_reference=convention_reference,
        source_references=(source_x, source_y),
        cautions=(),
        execution_origin=EvidenceOrigin.SYNTHETIC,
        selection_contract=LEGACY_PB_RESPONSE_RANKING,
    )
    return choice, reference_for(choice.document().to_bytes())


def test_aperture_restores_its_complete_lattice_and_placement() -> None:
    design = _propagation_design()
    cells, states = _quantized_states(8)
    aperture = assign_quantized(
        design,
        spacing_nm=200,
        cells=cells,
        states=states,
        evidence=(_reference("phase-set"),),
    )

    restored = Aperture.from_document(aperture_document(aperture))

    assert np.array_equal(restored.coordinates_nm, aperture.coordinates_nm)
    assert np.array_equal(restored.is_occupied, aperture.is_occupied)
    assert np.array_equal(restored.target_phase, aperture.target_phase)
    assert np.array_equal(restored.state_identities, aperture.state_identities)
    assert np.array_equal(restored.phase_levels, aperture.phase_levels)
    assert restored.cells == aperture.cells
    assert restored.states == aperture.states
    assert restored.evidence == aperture.evidence


@pytest.mark.parametrize(
    "tamper",
    ("spacing", "duplicate", "missing mask"),
)
def test_aperture_restoration_rejects_an_incomplete_centered_lattice(
    tamper: str,
) -> None:
    cells, states = _quantized_states(8)
    aperture = assign_quantized(
        _propagation_design(),
        spacing_nm=200,
        cells=cells,
        states=states,
        evidence=(_reference("phase-set"),),
    )
    original = aperture_document(aperture)
    values = deepcopy(original.values)
    if tamper == "spacing":
        values["coordinates_nm"][0][0][0] += 1
    elif tamper == "duplicate":
        values["coordinates_nm"][0][1] = values["coordinates_nm"][0][0]
    else:
        center = len(values["occupied"]) // 2
        values["occupied"][center][center] = False
        values["state_identities"][center][center] = ""
        values["phase_levels"][center][center] = -1

    with pytest.raises(ValueError, match="aperture_document_invalid"):
        Aperture.from_document(
            Document(original.schema_identifier, values)
        )


def test_assign_quantized_places_eight_states_across_the_phase_seam() -> None:
    design = _propagation_design()
    cells, states = _quantized_states(8)

    aperture = assign_quantized(
        design,
        spacing_nm=200,
        cells=cells,
        states=states,
        evidence=(_reference("phase-set"),),
    )

    expected_levels = nearest_phase_levels(
        np.where(aperture.is_occupied, aperture.target_phase, 0),
        8,
    )
    expected_levels[~aperture.is_occupied] = -1
    assert np.array_equal(aperture.phase_levels, expected_levels)
    assert set(
        aperture.state_identities[aperture.is_occupied].tolist()
    ) == {
        state.identity for state in states
    }
    canonical = np.remainder(aperture.target_phase, 2 * np.pi)
    near_zero = aperture.is_occupied & (canonical < np.pi / 8)
    near_two_pi = aperture.is_occupied & (
        canonical > 2 * np.pi - np.pi / 8
    )
    assert np.any(near_zero)
    assert np.any(near_two_pi)
    assert np.all(aperture.phase_levels[near_zero] == 0)
    assert np.all(aperture.phase_levels[near_two_pi] == 0)


@pytest.mark.parametrize("levels", [12, 16])
def test_assign_quantized_places_each_supported_higher_phase_set(
    levels: int,
) -> None:
    design = _propagation_design()
    cells, states = _quantized_states(levels)

    aperture = assign_quantized(
        design,
        spacing_nm=200,
        cells=cells,
        states=states,
        evidence=(_reference("phase-set"),),
    )

    assert len(aperture.states) == levels
    expected_levels = nearest_phase_levels(
        np.where(aperture.is_occupied, aperture.target_phase, 0),
        levels,
    )
    expected_levels[~aperture.is_occupied] = -1
    assert np.array_equal(aperture.phase_levels, expected_levels)
    placed = set(
        aperture.state_identities[aperture.is_occupied].tolist()
    )
    assert len(placed) == levels


def test_assign_oriented_places_one_continuous_geometric_aperture() -> None:
    design = _geometric_design()
    choice, choice_reference = _geometric_choice()
    orientations = derive_orientation_relation(
        choice,
        choice_reference=choice_reference,
    )
    orientations_reference = reference_for(orientations.document().to_bytes())

    aperture = assign_continuous_orientations(
        design,
        spacing_nm=200,
        choice=choice,
        orientation_relation=orientations,
        choice_reference=choice_reference,
        orientation_relation_reference=orientations_reference,
    )

    assert aperture.phase_levels is None
    assert len(aperture.cells) == 1
    assert aperture.cells[0].identity == choice.cell.identity
    distinct_targets = {state.target_phase for state in aperture.states}
    assert len(aperture.states) == len(distinct_targets)
    for state in aperture.states:
        assert state.phase_level is None
        assert state.orientation_rad is not None
        recovered = orientations.realized_phase(
            orientations.for_phase(state.target_phase)
        )
        assert recovered == state.realized_phase


@pytest.mark.parametrize("count", (8, 12, 16))
def test_assign_discrete_orientations_keeps_one_cell_and_one_relation(
    count: int,
) -> None:
    choice, choice_reference = _geometric_choice()
    orientations = derive_orientation_relation(
        choice,
        choice_reference=choice_reference,
    )
    orientations_reference = reference_for(
        orientations.document().to_bytes()
    )
    orientation_set = next(
        item
        for item in form_orientation_sets(
            orientations,
            relation_reference=orientations_reference,
        )
        if item.count == count
    )
    orientation_set_reference = reference_for(
        orientation_set.document().to_bytes()
    )

    aperture = assign_discrete_orientations(
        _geometric_design(),
        spacing_nm=200,
        choice=choice,
        orientation_relation=orientations,
        orientation_set=orientation_set,
        choice_reference=choice_reference,
        orientation_relation_reference=orientations_reference,
        orientation_set_reference=orientation_set_reference,
    )

    assert len(aperture.cells) == 1
    assert len(aperture.states) == count
    assert aperture.phase_levels is None
    assert orientation_set_reference in aperture.evidence
    assert orientations_reference in aperture.evidence
    assert all(state.phase_level is None for state in aperture.states)
    assert {
        state.orientation_rad for state in aperture.states
    } == {
        state.orientation_rad for state in orientation_set.states
    }


def test_yang_intent_forms_its_exact_fifteen_by_fifteen_square() -> None:
    design = require_metalens_design(
        compile_study(
            select_metalens_benchmark_case(
                "yang-2018-low-na-geometric"
            ).brief
        )
    )

    lattice = lattice_for(design, spacing_nm=1500)

    assert lattice.footprint is ApertureFootprint.SQUARE
    assert lattice.shape == (15, 15)
    assert lattice.site_count == 225
    assert lattice.half_span_nm == 11_250
    assert np.all(lattice.is_occupied)
    assert lattice.coordinates_nm[0, 0].tolist() == [-10_500, -10_500]
    assert lattice.coordinates_nm[-1, -1].tolist() == [10_500, 10_500]


def test_square_intent_cannot_silently_round_an_even_declared_span() -> None:
    design = replace(
        require_metalens_design(
            compile_study(
                select_metalens_benchmark_case(
                    "yang-2018-low-na-geometric"
                ).brief
            )
        ),
        aperture=ApertureIntent(
            site_count=14,
            extent=ApertureExtent.DIAMETER,
            footprint=ApertureFootprint.SQUARE,
        ),
    )

    resolved = resolve_lattice(design, spacing_nm=1500)

    assert resolved == ApertureIntentMismatch(
        declared_site_count=14,
        compiled_site_count=15,
    )


def test_continuous_lattice_retains_the_legacy_aperture_mismatch() -> None:
    resolved = resolve_lattice(_continuous_design(), spacing_nm=320)

    assert resolved == ApertureIntentMismatch(
        declared_site_count=51,
        compiled_site_count=63,
    )


def test_publication_brief_resolves_one_canonical_physical_lattice() -> None:
    legacy = continuous_achromatic_brief()
    publication = continuous_achromatic_publication_brief()

    assert publication.canonical_bytes() != legacy.canonical_bytes()
    period_reference = reference_for(b"publication period choice")
    resolved = resolve_lattice(
        _continuous_publication_design(),
        spacing_nm=320,
        spacing_source_reference=period_reference,
    )
    assert isinstance(resolved, Lattice)
    assert resolved.span_provenance == "brief aperture intent"
    assert resolved.declared_span_site_count == 63
    assert resolved.declared_span_extent is ApertureExtent.DIAMETER
    assert resolved.central_diameter_site_count == 63
    assert resolved.shape == (65, 65)
    assert resolved.site_count == 3069

    restored = Lattice.from_document(resolved.document())
    assert restored.spacing_source_reference == period_reference
    assert restored.document().to_bytes() == resolved.document().to_bytes()
    assert np.array_equal(restored.coordinates_nm, resolved.coordinates_nm)
    assert np.array_equal(restored.is_occupied, resolved.is_occupied)
    assert np.array_equal(restored.target_phase, resolved.target_phase)
    assert not restored.coordinates_nm.flags.writeable
    assert not restored.is_occupied.flags.writeable
    assert not restored.target_phase.flags.writeable


def test_omitted_aperture_records_derived_lattice_provenance() -> None:
    publication = continuous_achromatic_publication_brief()
    omitted = replace(
        publication,
        wording=(
            "Design one transmissive continuous-achromatic metalens from "
            "470 to 590 nm with a fixed 49 um focus and NA 0.2; derive the "
            "circular aperture from those optical facts after period selection."
        ),
        aperture=None,
        omissions=(*publication.omissions, "aperture intent"),
    )
    outcome = compile_study(omitted)
    assert isinstance(outcome, Study)
    design = require_metalens_design(outcome)

    resolved = resolve_lattice(design, spacing_nm=320)

    assert isinstance(resolved, Lattice)
    assert resolved.span_provenance == "derived from focal length and numerical aperture"
    assert resolved.declared_span_site_count is None
    assert resolved.declared_span_extent is None
    assert resolved.central_diameter_site_count == 63


def test_circular_intent_is_checked_against_the_actual_rounded_lattice() -> None:
    publication = continuous_achromatic_publication_brief()
    intent = publication.aperture
    assert intent is not None
    near_boundary = replace(
        publication,
        focal_length_um=Decimal("48.59591690502402692575555821490512050349"),
        aperture=replace(intent, site_count=61),
    )
    outcome = compile_study(near_boundary)
    assert isinstance(outcome, Study)
    design = require_metalens_design(outcome)

    resolved = resolve_lattice(design, spacing_nm=320)

    assert resolved == ApertureIntentMismatch(
        declared_site_count=61,
        compiled_site_count=63,
    )


def test_assignment_consumes_and_retains_the_exact_physical_lattice_reference() -> None:
    design = _propagation_design()
    cells, states = _quantized_states(8)
    period_reference = reference_for(b"admitted period choice")
    lattice = resolve_lattice(
        design,
        spacing_nm=200,
        spacing_source_reference=period_reference,
    )
    assert isinstance(lattice, Lattice)
    lattice_reference = reference_for(lattice.document().to_bytes())

    aperture = assign_quantized(
        design,
        spacing_nm=200,
        cells=cells,
        states=states,
        evidence=(),
        lattice=lattice,
        lattice_reference=lattice_reference,
    )

    assert lattice_reference in aperture.evidence
    assert np.array_equal(aperture.coordinates_nm, lattice.coordinates_nm)
    assert np.array_equal(aperture.is_occupied, lattice.is_occupied)
    assert np.array_equal(aperture.target_phase, lattice.target_phase)
    with pytest.raises(ValueError, match="physical_lattice_evidence_mismatch"):
        assign_quantized(
            design,
            spacing_nm=200,
            cells=cells,
            states=states,
            evidence=(),
            lattice=lattice,
            lattice_reference=reference_for(b"foreign lattice"),
        )


def test_oriented_aperture_rejects_a_foreign_orientation_relation() -> None:
    choice, choice_reference = _geometric_choice()
    foreign_choice = replace(
        choice,
        cell=replace(choice.cell, identity="cell:fin:foreign"),
    )
    foreign_reference = reference_for(
        foreign_choice.document().to_bytes()
    )
    foreign_orientations = derive_orientation_relation(
        foreign_choice,
        choice_reference=foreign_reference,
    )

    with pytest.raises(ValueError, match="orientation_choice_mismatch"):
        assign_continuous_orientations(
            _geometric_design(),
            spacing_nm=200,
            choice=choice,
            orientation_relation=foreign_orientations,
            choice_reference=choice_reference,
            orientation_relation_reference=reference_for(
                foreign_orientations.document().to_bytes()
            ),
        )


def test_both_strategies_share_one_circular_lattice_for_one_metalens_design() -> None:
    prop_cells, prop_states = _quantized_states(8)
    propagation_aperture = assign_quantized(
        _propagation_design(),
        spacing_nm=200,
        cells=prop_cells,
        states=prop_states,
        evidence=(_reference("phase-set"),),
    )
    choice, choice_reference = _geometric_choice()
    orientations = derive_orientation_relation(
        choice,
        choice_reference=choice_reference,
    )
    geometric_aperture = assign_continuous_orientations(
        _geometric_design(),
        spacing_nm=200,
        choice=choice,
        orientation_relation=orientations,
        choice_reference=choice_reference,
        orientation_relation_reference=reference_for(
            orientations.document().to_bytes()
        ),
    )
    assert np.array_equal(
        propagation_aperture.is_occupied,
        geometric_aperture.is_occupied,
    )
    assert np.array_equal(
        propagation_aperture.coordinates_nm,
        geometric_aperture.coordinates_nm,
    )
    assert np.array_equal(
        propagation_aperture.target_phase,
        geometric_aperture.target_phase,
    )
    assert propagation_aperture.spacing_nm == geometric_aperture.spacing_nm
    assert propagation_aperture.half_span_nm == (
        geometric_aperture.half_span_nm
    )


def test_stable_identity_lookup_performs_no_per_site_cell_library_search() -> None:
    design = _propagation_design()
    cells, states = _quantized_states(8)

    aperture = assign_quantized(
        design,
        spacing_nm=200,
        cells=cells,
        states=states,
        evidence=(_reference("phase-set"),),
    )

    assert len(aperture.states) == 8
    assert aperture.site_count > 8
    assert len(aperture.cells) == 8

    choice, choice_reference = _geometric_choice()
    orientations = derive_orientation_relation(
        choice,
        choice_reference=choice_reference,
    )
    oriented = assign_continuous_orientations(
        _geometric_design(),
        spacing_nm=200,
        choice=choice,
        orientation_relation=orientations,
        choice_reference=choice_reference,
        orientation_relation_reference=reference_for(
            orientations.document().to_bytes()
        ),
    )
    assert len(oriented.cells) == 1
    assert oriented.site_count >= len(oriented.states)
    distinct_state_targets = {state.target_phase for state in oriented.states}
    assert len(oriented.states) == len(distinct_state_targets)

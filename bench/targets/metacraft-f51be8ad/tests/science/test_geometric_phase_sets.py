import hashlib
from dataclasses import replace
from decimal import Decimal

import pytest

from metacraft.authority import Document, Reference, reference_for
from metacraft.science.metalens.aperture import Cell, Material, Rectangle
from metacraft.science.metalens.height import HeightAdviceBasis
from metacraft.science.phase import cyclic_distance
from metacraft.science.result import EvidenceOrigin
from metacraft.science.metalens.geometric_phase import (
    CellChoice,
    ComplexCoefficient,
    JonesResponse,
    LEGACY_PB_RESPONSE_RANKING,
    PolarizationConvention,
)
from metacraft.science.metalens.geometric_phase import (
    HALF_TURN,
    derive_orientation_relation,
    form_orientation_sets,
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


def _matching_reference(document: Document) -> Reference:
    return reference_for(document.to_bytes())


def _choice(handedness: str = "right") -> tuple[CellChoice, Reference]:
    convention = PolarizationConvention(circular_input=handedness)
    convention_reference = _matching_reference(convention.document())
    source_x = _reference("basis-x")
    source_y = _reference("basis-y")
    choice = CellChoice(
        cell=Cell(
            identity="selected-cell",
            atom=Material("titanium dioxide", "solver native"),
            substrate=Material("silica", "solver native"),
            period_nm=220,
            height_nm=600,
            geometry=Rectangle(short_side_nm=80, long_side_nm=140),
            source=source_x,
        ),
        jones=JonesResponse(
            output_x_from_input_x=ComplexCoefficient(Decimal("0.8"), Decimal(0)),
            output_y_from_input_x=ComplexCoefficient(Decimal("0.1"), Decimal(0)),
            output_x_from_input_y=ComplexCoefficient(Decimal("0.1"), Decimal(0)),
            output_y_from_input_y=ComplexCoefficient(Decimal("-0.8"), Decimal(0)),
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
    return choice, _matching_reference(choice.document())


def test_one_cell_forms_one_continuous_orientation_rule() -> None:
    choice, choice_reference = _choice()

    orientations = derive_orientation_relation(
        choice,
        choice_reference=choice_reference,
    )
    target = Decimal("1.23456789")
    physical_orientation = orientations.for_phase(target)

    assert Decimal(0) <= physical_orientation < HALF_TURN
    assert cyclic_distance(
        orientations.realized_phase(physical_orientation),
        target,
    ) < Decimal("1e-24")
    assert orientations.cell_id == choice.cell.identity
    assert orientations.source_references == choice.source_references
    assert orientations.reference_matches(
        _matching_reference(orientations.document())
    )
    mapping = orientations.as_mapping()
    assert "levels" not in mapping
    assert "states" not in mapping
    assert "phase_level" not in str(mapping)
    assert "orientation_index" not in str(mapping)


def test_handedness_reverses_continuous_orientation_without_quantization() -> None:
    right, right_reference = _choice("right")
    left, left_reference = _choice("left")
    right_orientations = derive_orientation_relation(
        right,
        choice_reference=right_reference,
    )
    left_orientations = derive_orientation_relation(
        left,
        choice_reference=left_reference,
    )
    target = Decimal("0.731")

    assert right_orientations.for_phase(target) != left_orientations.for_phase(
        target
    )
    assert cyclic_distance(
        right_orientations.realized_phase(
            right_orientations.for_phase(target)
        ),
        target,
    ) < Decimal("1e-24")
    assert cyclic_distance(
        left_orientations.realized_phase(left_orientations.for_phase(target)),
        target,
    ) < Decimal("1e-24")


@pytest.mark.parametrize("handedness", ("right", "left"))
def test_one_relation_forms_three_ordered_orientation_sets(
    handedness: str,
) -> None:
    choice, choice_reference = _choice(handedness)
    orientations = derive_orientation_relation(
        choice,
        choice_reference=choice_reference,
    )
    orientations_reference = _matching_reference(
        orientations.document()
    )

    orientation_sets = form_orientation_sets(
        orientations,
        relation_reference=orientations_reference,
    )

    assert tuple(item.count for item in orientation_sets) == (8, 12, 16)
    assert {
        item.orientation_relation_reference for item in orientation_sets
    } == {orientations_reference}
    assert {
        item.cell_id for item in orientation_sets
    } == {choice.cell.identity}
    for orientation_set in orientation_sets:
        assert tuple(state.index for state in orientation_set.states) == (
            tuple(range(orientation_set.count))
        )
        assert all(
            cyclic_distance(state.realized_phase, state.target_phase)
            < Decimal("1e-24")
            for state in orientation_set.states
        )
        restored = type(orientation_set).from_document(
            orientation_set.document()
        )
        assert restored == orientation_set
        assert restored.reference_matches(
            _matching_reference(restored.document())
        )


def test_orientation_set_rejects_a_forged_phase_or_rotation() -> None:
    choice, choice_reference = _choice()
    orientations = derive_orientation_relation(
        choice,
        choice_reference=choice_reference,
    )
    orientation_set = form_orientation_sets(
        orientations,
        relation_reference=_matching_reference(
            orientations.document()
        ),
    )[0]
    first = orientation_set.states[0]

    with pytest.raises(ValueError, match="orientation_target_invalid"):
        replace(
            orientation_set,
            states=(
                replace(first, target_phase=Decimal("0.1")),
                *orientation_set.states[1:],
            ),
        )
    with pytest.raises(ValueError, match="orientation_relation_invalid"):
        replace(
            orientation_set,
            states=(
                replace(first, orientation_rad=Decimal("0.1")),
                *orientation_set.states[1:],
            ),
        )

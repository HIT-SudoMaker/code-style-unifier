from __future__ import annotations

import hashlib

from dataclasses import replace
from decimal import Decimal

import numpy as np
import pytest

from metacraft.authority import Reference
from metacraft.field import (
    ComponentBasis,
    Medium,
)
from metacraft.science.metalens.aperture import (
    Aperture,
    Cell,
    Circle,
    Ellipse,
    Material,
    Rectangle,
    Response,
    Square,
    State,
    form_field as form_aperture_field,
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


def _cell() -> Cell:
    return Cell(
        identity="cell:round:180",
        atom=Material("silicon nitride", "solver native"),
        substrate=Material("silicon dioxide", "solver native"),
        period_nm=660,
        height_nm=600,
        geometry=Circle(diameter_nm=180),
        source=_reference("cell"),
    )


def _state(identity: str = "state:pointwise") -> State:
    return State(
        identity=identity,
        cell_identity="cell:round:180",
        responses=(
            Response(
                channel="transmission",
                real_part=Decimal("0.6"),
                imaginary_part=Decimal("0.8"),
                power=Decimal("1"),
            ),
        ),
        source=_reference(identity),
        target_phase=Decimal("0"),
        realized_phase=Decimal("0.9272952180016122"),
        useful_power=Decimal("1"),
        leakage_power=Decimal("0"),
    )


def _field(aperture: Aperture):
    return form_aperture_field(
        aperture,
        wavelength_m=400e-9,
        surface_position_m=0.0,
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        component_channels={"x": "transmission", "y": None},
        aperture_reference=_reference("aperture"),
    )


def _coordinates(
    shape: tuple[int, int],
    spacing_nm: int,
) -> np.ndarray:
    y_axis = (np.arange(shape[0]) - (shape[0] - 1) / 2) * spacing_nm
    x_axis = (np.arange(shape[1]) - (shape[1] - 1) / 2) * spacing_nm
    position_x, position_y = np.meshgrid(x_axis, y_axis)
    return np.stack((position_x, position_y), axis=-1).astype(np.int64)


def test_aperture_represents_pointwise_layout_without_phase_levels() -> None:
    occupied = np.array(
        [
            [False, True, False],
            [True, True, True],
            [False, True, False],
        ],
        dtype=np.bool_,
    )
    identities = np.array(
        [
            ["", "state:pointwise", ""],
            ["state:pointwise", "state:pointwise", "state:pointwise"],
            ["", "state:pointwise", ""],
        ],
        dtype=np.str_,
    )

    aperture = Aperture(
        cells=(_cell(),),
        states=(_state(),),
        coordinates_nm=_coordinates(occupied.shape, 660),
        is_occupied=occupied,
        target_phase=np.zeros(occupied.shape),
        state_identities=identities,
        spacing_nm=660,
        half_span_nm=660,
        evidence=(_reference("aperture"),),
    )

    assert aperture.site_count == 5
    assert aperture.phase_levels is None
    assert aperture.state_identities.tolist() == identities.tolist()
    assert aperture.as_mapping()["phase_levels"] is None
    assert aperture.as_mapping()["states"]["state:pointwise"][
        "phase_level"
    ] is None
    assert np.array_equal(
        _field(aperture).electric("x"),
        np.array(
            [
                [0, 0.6 + 0.8j, 0],
                [0.6 + 0.8j, 0.6 + 0.8j, 0.6 + 0.8j],
                [0, 0.6 + 0.8j, 0],
            ]
        ),
    )
    assert not aperture.is_occupied.flags.writeable
    assert not aperture.state_identities.flags.writeable


def test_aperture_rejects_duplicate_state_identity() -> None:
    with pytest.raises(ValueError, match="state_identity_duplicate"):
        Aperture(
            cells=(_cell(),),
            states=(_state(), _state()),
            coordinates_nm=_coordinates((1, 1), 660),
            is_occupied=np.ones((1, 1), dtype=np.bool_),
            target_phase=np.zeros((1, 1)),
            state_identities=np.array([["state:pointwise"]], dtype=np.str_),
            spacing_nm=660,
            half_span_nm=800,
            evidence=(_reference("aperture"),),
        )


def test_cell_geometry_is_one_unambiguous_shape() -> None:
    geometries = (
        (Circle(diameter_nm=180), "circular pillar", {"diameter_nm": 180}),
        (Square(width_nm=180), "square pillar", {"width_nm": 180}),
        (
            Rectangle(short_side_nm=100, long_side_nm=240),
            "rectangular fin",
            {"length_nm": 240, "width_nm": 100},
        ),
        (
            Ellipse(minor_axis_nm=100, major_axis_nm=240),
            "elliptical pillar",
            {"major_nm": 240, "minor_nm": 100},
        ),
    )

    for index, (geometry, shape, dimensions) in enumerate(geometries):
        cell = Cell(
            identity=f"cell:{index}",
            atom=Material("silicon nitride", "solver native"),
            substrate=Material("silicon dioxide", "solver native"),
            period_nm=660,
            height_nm=600,
            geometry=geometry,
            source=_reference(f"cell-{index}"),
        )
        assert cell.shape == shape
        assert cell.as_mapping()["geometry"] == dimensions


def test_cell_rejects_geometry_that_exceeds_its_period() -> None:
    with pytest.raises(ValueError, match="cell_exceeds_period"):
        Cell(
            identity="cell:too-large",
            atom=Material("silicon nitride", "solver native"),
            substrate=Material("silicon dioxide", "solver native"),
            period_nm=660,
            height_nm=600,
            geometry=Circle(diameter_nm=700),
            source=_reference("too-large"),
        )


def test_cell_rejects_untyped_geometry() -> None:
    with pytest.raises(ValueError, match="cell_geometry_unsupported"):
        Cell(
            identity="cell:untyped",
            atom=Material("silicon nitride", "solver native"),
            substrate=Material("silicon dioxide", "solver native"),
            period_nm=660,
            height_nm=600,
            geometry=object(),  # type: ignore[arg-type]
            source=_reference("untyped"),
        )


def test_aperture_identity_placement_drives_the_realized_field() -> None:
    states = tuple(
        State(
            identity=f"state:{level}",
            cell_identity="cell:round:180",
            responses=(
                Response(
                    channel="transmission",
                    real_part=Decimal(str(real)),
                    imaginary_part=Decimal(str(imaginary)),
                    power=Decimal("1"),
                ),
            ),
            source=_reference(f"state-{level}"),
            target_phase=Decimal(str(level * np.pi / 2)),
            realized_phase=Decimal(str(level * np.pi / 2)),
            useful_power=Decimal("1"),
            leakage_power=Decimal("0"),
            phase_level=level,
        )
        for level, (real, imaginary) in enumerate(
            ((1, 0), (0, 1), (-1, 0), (0, -1))
        )
    )
    aperture = Aperture(
        cells=(_cell(),),
        states=states,
        coordinates_nm=_coordinates((3, 3), 660),
        is_occupied=np.array(
            [
                [False, True, False],
                [True, True, True],
                [False, True, False],
            ],
            dtype=np.bool_,
        ),
        target_phase=np.array(
            [
                [0, 0, 0],
                [np.pi / 2, np.pi, 3 * np.pi / 2],
                [0, 0, 0],
            ],
            dtype=np.float64,
        ),
        state_identities=np.array(
            [
                ["", "state:0", ""],
                ["state:1", "state:2", "state:3"],
                ["", "state:0", ""],
            ],
            dtype=np.str_,
        ),
        spacing_nm=660,
        half_span_nm=660,
        evidence=(_reference("phase-set"),),
        phase_levels=np.array(
            [
                [-1, 0, -1],
                [1, 2, 3],
                [-1, 0, -1],
            ],
            dtype=np.int64,
        ),
    )

    assert aperture.state_identities.tolist() == [
        ["", "state:0", ""],
        ["state:1", "state:2", "state:3"],
        ["", "state:0", ""],
    ]
    assert aperture.phase_levels.tolist() == [
        [-1, 0, -1],
        [1, 2, 3],
        [-1, 0, -1],
    ]
    assert np.array_equal(
        _field(aperture).electric("x"),
        np.array(
            [
                [0, 1, 0],
                [1j, -1, -1j],
                [0, 1, 0],
            ],
            dtype=np.complex128,
        ),
    )

def test_aperture_rejects_phase_level_that_disagrees_with_state_identity() -> None:
    occupied = np.array(
        [
            [False, True, False],
            [True, True, True],
            [False, True, False],
        ],
        dtype=np.bool_,
    )
    identities = np.full((3, 3), "", dtype="<U20")
    identities[occupied] = "state:pointwise"
    levels = np.full((3, 3), -1, dtype=np.int64)
    levels[occupied] = 0
    with pytest.raises(ValueError, match="phase_level_state_mismatch"):
        Aperture(
            cells=(_cell(),),
            states=(_state(),),
            coordinates_nm=_coordinates((3, 3), 660),
            is_occupied=occupied,
            target_phase=np.zeros((3, 3)),
            state_identities=identities,
            spacing_nm=660,
            half_span_nm=660,
            evidence=(_reference("aperture"),),
            phase_levels=levels,
        )


def test_aperture_rejects_occupied_site_outside_declared_radius() -> None:
    occupied = np.zeros((3, 3), dtype=np.bool_)
    occupied[0, 0] = True
    identities = np.full((3, 3), "", dtype="<U20")
    identities[0, 0] = "state:pointwise"

    with pytest.raises(ValueError, match="aperture_mask_invalid"):
        Aperture(
            cells=(_cell(),),
            states=(_state(),),
            coordinates_nm=_coordinates((3, 3), 660),
            is_occupied=occupied,
            target_phase=np.zeros((3, 3)),
            state_identities=identities,
            spacing_nm=660,
            half_span_nm=500,
            evidence=(_reference("aperture"),),
        )


def test_state_rejects_an_invalid_continuous_orientation() -> None:
    with pytest.raises(ValueError, match="orientation_invalid"):
        replace(_state(), orientation_rad=Decimal("-0.1"))

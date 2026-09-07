from __future__ import annotations

import math

import numpy as np
import pytest

from metacraft.authority import reference_for
from metacraft.science import FindingKind
from metacraft.field import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from metacraft.field.angular_spectrum import (
    observe_angular_spectrum,
    propagate_field,
    qualify_angular_spectrum,
)
from metacraft.science.metalens import (
    Focus,
    FocusSurvey,
    evaluate_focus,
)
from metacraft.science.metalens.focus import focus_document
from metacraft.science.metalens.focus import observe_focal_region
from tests.field_fixtures import recorded_focal_region


def _ideal_lens(
    *,
    wavelength_m: float = 400e-9,
    focal_length_m: float = 20e-6,
    numerical_aperture: float = 0.4,
    spacing_m: float = 150e-9,
) -> tuple[np.ndarray, np.ndarray, float, float, float, float]:
    radius_m = (
        focal_length_m
        * numerical_aperture
        / math.sqrt(1 - numerical_aperture**2)
    )
    half_cells = math.ceil(radius_m / spacing_m)
    axis = np.arange(-half_cells, half_cells + 1) * spacing_m
    x_grid, y_grid = np.meshgrid(axis, axis)
    radial = np.hypot(x_grid, y_grid)
    occupied = radial <= radius_m
    phase = (
        -2
        * np.pi
        / wavelength_m
        * (np.sqrt(focal_length_m**2 + radial**2) - focal_length_m)
    )
    field = np.zeros(occupied.shape, dtype=np.complex128)
    field[occupied] = 0.8 * np.exp(1j * phase[occupied])
    return (
        field,
        occupied,
        spacing_m,
        wavelength_m,
        focal_length_m,
        numerical_aperture,
    )


def test_focus_search_refines_realized_lens_across_the_focal_window() -> None:
    """
    Retain complete metrics under the qualified realization.
    """

    field, occupied, spacing, wavelength, expected, na = _ideal_lens()
    aperture_field = _field(field, spacing=spacing, wavelength=wavelength)
    realization = observe_angular_spectrum()
    qualification = qualify_angular_spectrum(realization)
    assert qualification.is_qualified
    assert qualification.realization == realization

    propagation = propagate_field(
        aperture_field,
        distance_range_m=(0.8 * expected, 1.2 * expected),
        preferred_distance_m=expected,
        components=("x",),
        realization=realization,
    )
    region = observe_focal_region(
        propagation,
        field_reference=reference_for(b"focus fixture field"),
        expected_focus_m=expected,
    )
    focus = evaluate_focus(
        region,
        numerical_aperture=na,
    )

    assert isinstance(focus, Focus)
    assert math.isclose(focus.found_focus_m, expected, rel_tol=0.02)
    assert abs(focus.focal_shift_m) <= expected * 0.02
    assert focus.is_focus_bracketed
    assert focus.x_half_maximum.is_bracketed
    assert focus.y_half_maximum.is_bracketed
    assert focus.depth_of_focus.is_bracketed
    assert focus.is_complete
    assert focus.x_half_maximum.width_m is not None
    assert focus.y_half_maximum.width_m is not None
    assert math.isclose(focus.x_half_maximum.width_m, focus.y_half_maximum.width_m, rel_tol=0.05)
    assert math.isclose(focus.transmitted_fraction, 0.64, rel_tol=1e-12)
    assert math.isclose(
        focus.focus_efficiency,
        focus.transmitted_fraction * focus.focused_fraction,
        rel_tol=1e-12,
    )
    assert focus.airy_radius_m == 0.61 * wavelength / na
    assert focus.observed_components == ("x",)
    assert focus.convergence.is_locally_refined
    assert region.electric("x").shape == field.shape
    assert np.array_equal(region.electric("y"), np.zeros_like(field))
    assert region.realization["implementation"] == "torch"
    assert region.realization["device"] == realization.device
    assert region.realization["convention"]["padding_factor"] == 2
    assert region.incident_reference_power == float(
        np.count_nonzero(occupied)
    )
    assert math.isclose(
        region.transmitted_aperture_power["x"],
        0.64 * np.count_nonzero(occupied),
        rel_tol=1e-12,
    )
    assert region.transmitted_aperture_power["y"] == 0.0


def test_converted_focus_and_retained_leakage_share_one_observed_plane() -> None:
    """
    Keep separated converted and retained peaks on one truthful plane.
    """

    wavelength = 400e-9
    spacing = 200e-9
    expected = 10e-6
    axis = (np.arange(41) - 20) * spacing
    position_x, position_y = np.meshgrid(axis, axis)
    radius = np.hypot(position_x, position_y)
    occupied = radius <= 3.8e-6
    wave_number = 2 * np.pi / wavelength

    def lens(focal_length: float, amplitude: float) -> np.ndarray:
        values = np.zeros(radius.shape, dtype=np.complex128)
        values[occupied] = amplitude * np.exp(
            -1j
            * wave_number
            * (
                np.sqrt(focal_length**2 + radius[occupied] ** 2)
                - focal_length
            )
        )
        return _immutable(values)

    right = lens(8.5e-6, 1.0)
    left = lens(11.5e-6, 0.7)
    field = Field(
        wavelength_m=wavelength,
        surface=PlaneSurface(0.0, spacing, right.shape),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.CIRCULAR,
        electric_components=(
            FieldComponent("right", right),
            FieldComponent("left", left),
        ),
        source_references=(reference_for(b"separated circular field"),),
        incident_reference_power=float(np.count_nonzero(occupied) * 2),
    )

    propagation = propagate_field(
        field,
        distance_range_m=(0.8 * expected, 1.2 * expected),
        preferred_distance_m=expected,
        components=("left",),
        realization=observe_angular_spectrum(),
    )
    region = observe_focal_region(
        propagation,
        field_reference=reference_for(b"separated focal evidence"),
        expected_focus_m=expected,
    )
    focus = evaluate_focus(
        region,
        numerical_aperture=0.3,
        leakage_component="right",
    )

    left_index = int(
        np.argmax(region.component_axial_peak_intensities["left"])
    )
    right_index = int(
        np.argmax(region.component_axial_peak_intensities["right"])
    )
    observed_index = region.axial_distances_m.index(
        region.found_focus_m
    )
    assert left_index != right_index
    assert observed_index == left_index
    assert region.observed_components == ("left",)
    assert focus.observed_components == ("left",)
    assert focus.found_focus_m == region.found_focus_m
    assert focus.leakage is not None
    assert focus.leakage.observed_distance_m == region.found_focus_m
    assert np.max(np.abs(region.electric("left")) ** 2) == pytest.approx(
        region.component_axial_peak_intensities["left"][
            observed_index
        ]
    )
    assert focus.leakage.peak_intensity == pytest.approx(
        region.component_axial_peak_intensities["right"][
            observed_index
        ]
    )


def test_focus_result_is_explicitly_incomplete_when_crossings_are_unbracketed() -> None:
    """
    Report an edge-clipped survey as incomplete.
    """

    field = np.ones((8, 8), dtype=np.complex128)
    occupied = np.ones(field.shape, dtype=np.bool_)

    region = recorded_focal_region(
        field,
        axial_distances_m=(8e-6, 10e-6, 12e-6),
        axial_peak_intensities=(1.0, 2.0, 3.0),
        found_focus_m=12e-6,
        expected_focus_m=10e-6,
        incident_reference_power=64.0,
        transmitted_x_power=64.0,
    )
    focus = evaluate_focus(
        region,
        numerical_aperture=0.3,
    )

    assert type(focus) is FocusSurvey
    assert focus.status == "incomplete"
    assert not focus.is_focus_bracketed
    assert not focus.depth_of_focus.is_bracketed
    assert focus.depth_of_focus.width_m is None
    assert focus.found_focus_m == region.axial_distances_m[-1]
    assert focus.as_mapping()["status"] == "incomplete"
    with pytest.raises(ValueError, match="focus_incomplete"):
        focus_document(
            focal_region_reference=reference_for(
                b"incomplete focal region"
            ),
            focus=focus,
        )
    diagnostic = reference_for(b"incomplete focus survey")
    finding = focus.finding(diagnostic)
    assert finding.claim == "focus"
    assert finding.kind is FindingKind.INCOMPLETE
    assert finding.needs == ("focus_incomplete",)
    assert finding.record_references == (diagnostic,)


def test_focal_region_names_incident_and_transmitted_power() -> None:
    """
    Keep incident reference and transmitted aperture power distinct.
    """

    region = recorded_focal_region(
        np.ones((5, 5), dtype=np.complex128),
        axial_distances_m=(4e-6, 5e-6, 6e-6),
        axial_peak_intensities=(0.5, 1.0, 0.5),
        found_focus_m=5e-6,
        expected_focus_m=5e-6,
        incident_reference_power=25.0,
        transmitted_x_power=16.0,
    )

    assert region.incident_reference_power == 25.0
    assert region.transmitted_aperture_power["x"] == 16.0
    assert region.transmitted_aperture_power["y"] == 0.0
    assert not hasattr(region, "source_power")


def _field(
    electric_field_x: np.ndarray,
    *,
    spacing: float,
    wavelength: float,
) -> Field:
    electric_field_x = _immutable(electric_field_x)
    return Field(
        wavelength_m=wavelength,
        surface=PlaneSurface(0.0, spacing, electric_field_x.shape),
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            FieldComponent("x", electric_field_x),
            FieldComponent(
                "y",
                _immutable(np.zeros_like(electric_field_x)),
            ),
        ),
        source_references=(reference_for(b"focus fixture aperture"),),
        incident_reference_power=float(
            np.count_nonzero(np.abs(electric_field_x) > 0)
        ),
    )


def _immutable(values: np.ndarray) -> np.ndarray:
    frozen = np.array(values, dtype="<c16", order="C", copy=True)
    frozen.setflags(write=False)
    return frozen

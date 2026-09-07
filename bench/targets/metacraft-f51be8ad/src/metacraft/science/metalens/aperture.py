from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import math
from typing import TYPE_CHECKING

import numpy
from numpy.typing import NDArray

from ...authority.protocol import Document, Reference
from ...authority.reference import reference_matches
from ...canonical import encode_bytes
from ...field.reference_surface import (
    AdmittedReferenceSurface,
    ReferenceSurfaceResponse,
)
from ...field.sample import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)

from ..phase import (
    FULL_TURN,
    PHASE_KEY_SCALE,
    canonical_phase,
    nearest_phase_levels,
)
from ..study import Caution

from .brief import (
    ApertureExtent,
    ApertureFootprint,
    ContinuousBandSpectrum,
    require_monochromatic_wavelength,
)
from .period import ORDER_CAUTION, ORDER_CAUTION_EXPLANATION

if TYPE_CHECKING:
    from .design import MetalensDesign
    from .geometric_phase import (
        CellChoice,
        OrientationRelation,
        OrientationSet,
    )


APERTURE_SCHEMA = "metacraft.science.metalens.aperture"
PHYSICAL_LATTICE_SCHEMA = "metacraft.science.metalens.physical_lattice"
_LOCAL_ASSEMBLY_CONCERN = "locally periodic assembly"
_LOCAL_ASSEMBLY_EXPLANATION = (
    "The aperture is assembled from independently periodic cell responses; "
    "neighbor coupling and finite-aperture edge effects remain unmodeled."
)


@dataclass(frozen=True, slots=True)
class Circle:
    """
    Gives the diameter of one circular pillar.
    """

    diameter_nm: int

    def __post_init__(self) -> None:
        """
        Require a positive circular diameter.
        """

        if self.diameter_nm <= 0:
            raise ValueError("circle_diameter_invalid")

    @property
    def shape(self) -> str:
        """
        Name the circular cross-section.
        """

        return "circular pillar"

    @property
    def span_nm(self) -> int:
        """
        Return the circle's enclosing span.
        """

        return self.diameter_nm

    def as_mapping(self) -> dict[str, int]:
        """
        Return the circle in evidence-safe form.
        """

        return {"diameter_nm": self.diameter_nm}


@dataclass(frozen=True, slots=True)
class Square:
    """
    Gives the width of one square pillar.
    """

    width_nm: int

    def __post_init__(self) -> None:
        """
        Require a positive square width.
        """

        if self.width_nm <= 0:
            raise ValueError("square_width_invalid")

    @property
    def shape(self) -> str:
        """
        Name the square cross-section.
        """

        return "square pillar"

    @property
    def span_nm(self) -> int:
        """
        Return the square's enclosing span.
        """

        return self.width_nm

    def as_mapping(self) -> dict[str, int]:
        """
        Return the square in evidence-safe form.
        """

        return {"width_nm": self.width_nm}


@dataclass(frozen=True, slots=True)
class Rectangle:
    """
    Gives the short and long dimensions of one rectangular fin.
    """

    short_side_nm: int
    long_side_nm: int

    def __post_init__(self) -> None:
        """
        Require positive rectangular dimensions.
        """

        if self.short_side_nm <= 0 or self.long_side_nm <= self.short_side_nm:
            raise ValueError("rectangle_dimensions_invalid")

    @property
    def shape(self) -> str:
        """
        Name the rectangular cross-section.
        """

        return "rectangular fin"

    @property
    def span_nm(self) -> int:
        """
        Return the rectangle's largest span.
        """

        return self.long_side_nm

    def as_mapping(self) -> dict[str, int]:
        """
        Return the rectangle in evidence-safe form.
        """

        return {
            "length_nm": self.long_side_nm,
            "width_nm": self.short_side_nm,
        }


@dataclass(frozen=True, slots=True)
class Ellipse:
    """
    Gives the minor and major dimensions of one elliptical pillar.
    """

    minor_axis_nm: int
    major_axis_nm: int

    def __post_init__(self) -> None:
        """
        Require positive ordered ellipse axes.
        """

        if self.minor_axis_nm <= 0 or self.major_axis_nm <= self.minor_axis_nm:
            raise ValueError("ellipse_dimensions_invalid")

    @property
    def shape(self) -> str:
        """
        Name the elliptical cross-section.
        """

        return "elliptical pillar"

    @property
    def span_nm(self) -> int:
        """
        Return the ellipse's major span.
        """

        return self.major_axis_nm

    def as_mapping(self) -> dict[str, int]:
        """
        Return the ellipse in evidence-safe form.
        """

        return {
            "major_nm": self.major_axis_nm,
            "minor_nm": self.minor_axis_nm,
        }


Geometry = Circle | Square | Rectangle | Ellipse


@dataclass(frozen=True, slots=True)
class Material:
    """
    Names one material and the registered source of that identity.
    """

    name: str
    source: str

    def __post_init__(self) -> None:
        """
        Require a named material and source.
        """

        if not self.name or not self.source:
            raise ValueError("material_identity_incomplete")

    def as_mapping(self) -> dict[str, str]:
        """
        Return the material identity in evidence-safe form.
        """

        return {"name": self.name, "source": self.source}


@dataclass(frozen=True, slots=True)
class Cell:
    """
    Describes one fabricable meta-atom.
    """

    identity: str
    atom: Material
    substrate: Material
    period_nm: int
    height_nm: int
    geometry: Geometry
    source: Reference

    def __post_init__(self) -> None:
        """
        Require a fabricable cell with explicit provenance.
        """

        if not self.identity:
            raise ValueError("cell_identity_invalid")
        if not isinstance(self.atom, Material) or not isinstance(
            self.substrate,
            Material,
        ):
            raise ValueError("cell_material_invalid")
        if self.period_nm <= 0 or self.height_nm <= 0:
            raise ValueError("cell_scale_invalid")
        if not isinstance(self.geometry, (Circle, Square, Rectangle, Ellipse)):
            raise ValueError("cell_geometry_unsupported")
        if self.geometry.span_nm >= self.period_nm:
            raise ValueError("cell_exceeds_period")

    @property
    def shape(self) -> str:
        """
        Return the cross-section's natural shape name.
        """

        return self.geometry.shape

    def as_mapping(self) -> dict[str, object]:
        """
        Return the cell in evidence-safe form.
        """

        return {
            "atom": self.atom.as_mapping(),
            "geometry": self.geometry.as_mapping(),
            "height_nm": self.height_nm,
            "identity": self.identity,
            "period_nm": self.period_nm,
            "shape": self.shape,
            "source": self.source.as_mapping(),
            "substrate": self.substrate.as_mapping(),
        }


@dataclass(frozen=True, slots=True)
class Response:
    """
    Gives one state's realized complex response in a named optical channel.
    """

    channel: str
    real_part: Decimal
    imaginary_part: Decimal
    power: Decimal

    def __post_init__(self) -> None:
        """
        Require one finite complex response.
        """

        if not self.channel:
            raise ValueError("response_channel_invalid")
        if not all(
            value.is_finite()
            for value in (self.real_part, self.imaginary_part, self.power)
        ):
            raise ValueError("response_not_finite")
        if self.power < 0:
            raise ValueError("response_power_invalid")

    @property
    def complex_value(self) -> complex:
        """
        Reconstruct the complex response value.
        """

        return complex(float(self.real_part), float(self.imaginary_part))

    def as_mapping(self) -> dict[str, object]:
        """
        Return the response in evidence-safe form.
        """

        return {
            "channel": self.channel,
            "imaginary": format(self.imaginary_part, "f"),
            "power": format(self.power, "f"),
            "real": format(self.real_part, "f"),
        }


@dataclass(frozen=True, slots=True)
class State:
    """
    Binds one stable optical identity to a cell and realized responses.
    """

    identity: str
    cell_identity: str
    responses: tuple[Response, ...]
    source: Reference
    target_phase: Decimal
    realized_phase: Decimal
    useful_power: Decimal
    leakage_power: Decimal
    phase_level: int | None = None
    orientation_rad: Decimal | None = None

    def __post_init__(self) -> None:
        """
        Require one coherent state identity and response set.
        """

        if not self.identity or not self.cell_identity:
            raise ValueError("state_identity_invalid")
        if not self.responses:
            raise ValueError("state_responses_empty")
        values = (
            self.target_phase,
            self.realized_phase,
            self.useful_power,
            self.leakage_power,
        )
        if not all(value.is_finite() for value in values):
            raise ValueError("state_value_not_finite")
        object.__setattr__(
            self,
            "target_phase",
            canonical_phase(self.target_phase),
        )
        object.__setattr__(
            self,
            "realized_phase",
            canonical_phase(self.realized_phase),
        )
        if self.useful_power < 0 or self.leakage_power < 0:
            raise ValueError("state_power_invalid")
        channels = tuple(response.channel for response in self.responses)
        if len(set(channels)) != len(channels):
            raise ValueError("response_channel_duplicate")
        if self.phase_level is not None and self.phase_level < 0:
            raise ValueError("phase_level_invalid")
        if self.orientation_rad is not None and (
            not self.orientation_rad.is_finite() or self.orientation_rad < 0
        ):
            raise ValueError("orientation_invalid")

    def response(self, channel: str) -> Response:
        """
        Return the response carried by one named channel.
        """

        for response in self.responses:
            if response.channel == channel:
                return response
        raise ValueError(f"state_channel_missing:{channel}")

    def as_mapping(self) -> dict[str, object]:
        """
        Return the state in evidence-safe form.
        """

        return {
            "cell": self.cell_identity,
            "identity": self.identity,
            "leakage_power": format(self.leakage_power, "f"),
            "phase_level": self.phase_level,
            "realized_phase": format(self.realized_phase, "f"),
            "responses": {
                response.channel: response.as_mapping() for response in self.responses
            },
            "orientation_rad": (
                None
                if self.orientation_rad is None
                else format(self.orientation_rad, "f")
            ),
            "source": self.source.as_mapping(),
            "target_phase": format(self.target_phase, "f"),
            "useful_power": format(self.useful_power, "f"),
        }


@dataclass(frozen=True, slots=True)
class Lattice:
    """
    Carries one metalens footprint before optical states are assigned.
    """

    spacing_nm: int
    half_span_nm: int
    footprint: ApertureFootprint
    span_provenance: str
    declared_span_site_count: int | None
    declared_span_extent: ApertureExtent | None
    spacing_source_reference: Reference | None
    coordinates_nm: NDArray[numpy.integer]
    is_occupied: NDArray[numpy.bool_]
    target_phase: NDArray[numpy.floating]

    def __post_init__(self) -> None:
        """
        Require one finite lattice consistent with its declared footprint.
        """

        if self.spacing_nm <= 0 or self.half_span_nm <= 0:
            raise ValueError("aperture_scale_invalid")
        if self.span_provenance not in {
            "brief aperture intent",
            "derived from focal length and numerical aperture",
        }:
            raise ValueError("aperture_span_provenance_invalid")
        if (
            (self.declared_span_site_count is None)
            != (self.declared_span_extent is None)
            or (
                self.span_provenance == "brief aperture intent"
                and (
                    self.declared_span_site_count is None
                    or self.declared_span_site_count <= 0
                )
            )
            or (
                self.span_provenance
                == "derived from focal length and numerical aperture"
                and self.declared_span_site_count is not None
            )
        ):
            raise ValueError("aperture_span_provenance_invalid")
        coordinates = numpy.array(
            self.coordinates_nm,
            dtype=numpy.int64,
            copy=True,
        )
        is_occupied = numpy.array(
            self.is_occupied,
            dtype=numpy.bool_,
            copy=True,
        )
        target = numpy.array(self.target_phase, dtype=numpy.float64, copy=True)
        if (
            is_occupied.ndim != 2
            or coordinates.shape != (*is_occupied.shape, 2)
            or target.shape != is_occupied.shape
        ):
            raise ValueError("aperture_lattice_shape_invalid")
        if not numpy.any(is_occupied):
            raise ValueError("aperture_empty")
        if not numpy.isfinite(target[is_occupied]).all():
            raise ValueError("target_phase_not_finite")
        if self.footprint is ApertureFootprint.CIRCULAR:
            distance_nm = numpy.hypot(
                coordinates[..., 0],
                coordinates[..., 1],
            )
        elif self.footprint is ApertureFootprint.SQUARE:
            distance_nm = numpy.maximum(
                numpy.abs(coordinates[..., 0]),
                numpy.abs(coordinates[..., 1]),
            )
        else:
            raise ValueError("aperture_footprint_invalid")
        if numpy.any(distance_nm[is_occupied] > self.half_span_nm):
            raise ValueError("aperture_site_outside_footprint")
        coordinates.setflags(write=False)
        is_occupied.setflags(write=False)
        target.setflags(write=False)
        object.__setattr__(self, "coordinates_nm", coordinates)
        object.__setattr__(self, "is_occupied", is_occupied)
        object.__setattr__(self, "target_phase", target)

    @property
    def shape(self) -> tuple[int, int]:
        """
        Return the lattice grid shape.
        """

        shape = self.is_occupied.shape
        return int(shape[0]), int(shape[1])

    @property
    def site_count(self) -> int:
        """
        Return the number of occupied lattice sites.
        """

        return int(numpy.count_nonzero(self.is_occupied))

    @property
    def central_diameter_site_count(self) -> int:
        """Count occupied sites across the central row of the physical lattice."""

        return int(numpy.count_nonzero(self.is_occupied[self.shape[0] // 2]))

    def document(self) -> Document:
        """Encode the resolved physical lattice without rebuilding it."""

        return Document(
            PHYSICAL_LATTICE_SCHEMA,
            {
                "coordinates_nm": self.coordinates_nm.tolist(),
                "declared_span_extent": (
                    None
                    if self.declared_span_extent is None
                    else self.declared_span_extent.value
                ),
                "declared_span_site_count": self.declared_span_site_count,
                "footprint": self.footprint.value,
                "half_span_nm": self.half_span_nm,
                "occupied": self.is_occupied.tolist(),
                "spacing_nm": self.spacing_nm,
                "spacing_source_reference": (
                    None
                    if self.spacing_source_reference is None
                    else self.spacing_source_reference.as_mapping()
                ),
                "span_provenance": self.span_provenance,
                "target_phase": [
                    [format(float(value), ".17g") for value in row]
                    for row in self.target_phase
                ],
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> Lattice:
        """Restore the exact physical lattice without re-deriving its extent."""

        if document.schema_identifier != PHYSICAL_LATTICE_SCHEMA:
            raise ValueError("physical_lattice_schema_mismatch")
        values = document.values
        if set(values) != {
            "coordinates_nm",
            "declared_span_extent",
            "declared_span_site_count",
            "footprint",
            "half_span_nm",
            "occupied",
            "spacing_nm",
            "spacing_source_reference",
            "span_provenance",
            "target_phase",
        }:
            raise ValueError("physical_lattice_document_invalid")
        try:
            lattice = cls(
                spacing_nm=_integer(values["spacing_nm"]),
                half_span_nm=_integer(values["half_span_nm"]),
                footprint=ApertureFootprint(str(values["footprint"])),
                span_provenance=str(values["span_provenance"]),
                declared_span_site_count=(
                    None
                    if values["declared_span_site_count"] is None
                    else _integer(values["declared_span_site_count"])
                ),
                declared_span_extent=(
                    None
                    if values["declared_span_extent"] is None
                    else ApertureExtent(str(values["declared_span_extent"]))
                ),
                spacing_source_reference=(
                    None
                    if values["spacing_source_reference"] is None
                    else Reference.from_mapping(
                        _mapping(
                            values["spacing_source_reference"],
                            "physical_lattice_document_invalid",
                        )
                    )
                ),
                coordinates_nm=numpy.asarray(values["coordinates_nm"], dtype=numpy.int64),
                is_occupied=numpy.asarray(values["occupied"], dtype=numpy.bool_),
                target_phase=numpy.asarray(values["target_phase"], dtype=numpy.float64),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("physical_lattice_document_invalid") from error
        if lattice.document().to_bytes() != document.to_bytes():
            raise ValueError("physical_lattice_document_mismatch")
        return lattice


@dataclass(frozen=True, slots=True)
class ApertureIntentMismatch:
    """Retain an incompatible declared and physically compiled span count."""

    declared_site_count: int
    compiled_site_count: int

    def __post_init__(self) -> None:
        if self.declared_site_count <= 0 or self.compiled_site_count <= 0:
            raise ValueError("aperture_intent_mismatch_invalid")

    @property
    def reason(self) -> str:
        """Return the existing typed refusal vocabulary with both counts."""

        return (
            "aperture_intent_mismatch:"
            f"{self.declared_site_count}:{self.compiled_site_count}"
        )


def resolve_lattice(
    design: MetalensDesign,
    *,
    spacing_nm: int,
    spacing_source_reference: Reference | None = None,
) -> Lattice | ApertureIntentMismatch:
    """Resolve one physical lattice or retain an incompatible aperture intent."""

    if spacing_nm <= 0:
        raise ValueError("aperture_spacing_invalid")
    focal_length_nm = design.focal_length_um * Decimal(1_000)
    numerical_aperture = design.numerical_aperture
    intent = design.aperture
    footprint = ApertureFootprint.CIRCULAR if intent is None else intent.footprint
    if footprint is ApertureFootprint.SQUARE:
        if intent is None:
            raise ValueError("square_aperture_intent_missing")
        half_span_nm = intent.site_count * spacing_nm // 2
    else:
        radius_nm = (
            focal_length_nm
            * numerical_aperture
            / (Decimal(1) - numerical_aperture**2).sqrt()
        )
        half_span_nm = int(round(float(radius_nm)))
    coordinates_nm, is_occupied = _centered_grid(
        spacing_nm=spacing_nm,
        half_span_nm=half_span_nm,
        footprint=footprint,
    )
    if intent is not None:
        central_span_site_count = int(
            numpy.count_nonzero(is_occupied[is_occupied.shape[0] // 2])
        )
        compiled_site_count = (
            (central_span_site_count + 1) // 2
            if intent.extent is ApertureExtent.RADIUS
            else central_span_site_count
        )
        if intent.site_count != compiled_site_count:
            return ApertureIntentMismatch(
                declared_site_count=intent.site_count,
                compiled_site_count=compiled_site_count,
            )
    x_nm = coordinates_nm[..., 0]
    y_nm = coordinates_nm[..., 1]
    radial_nm = numpy.hypot(x_nm, y_nm)
    spectrum = design.operating_spectrum
    wavelength_nm = (
        (spectrum.lower_wavelength_nm + spectrum.upper_wavelength_nm) // 2
        if isinstance(spectrum, ContinuousBandSpectrum)
        else require_monochromatic_wavelength(spectrum)
    )
    focal_phase = (
        -2
        * numpy.pi
        / wavelength_nm
        * (numpy.sqrt(float(focal_length_nm) ** 2 + radial_nm**2) - float(focal_length_nm))
    )
    return Lattice(
        spacing_nm=spacing_nm,
        half_span_nm=half_span_nm,
        footprint=footprint,
        span_provenance=(
            "derived from focal length and numerical aperture"
            if intent is None
            else "brief aperture intent"
        ),
        declared_span_site_count=(None if intent is None else intent.site_count),
        declared_span_extent=(None if intent is None else intent.extent),
        spacing_source_reference=spacing_source_reference,
        coordinates_nm=coordinates_nm,
        is_occupied=is_occupied,
        target_phase=focal_phase,
    )


def lattice_for(
    design: MetalensDesign,
    *,
    spacing_nm: int,
) -> Lattice:
    """
    Form one declared footprint and its hyperbolic target phase.

    One metalens design and one admitted cell period resolve the lattice
    coordinates, occupied mask, and target phase exactly once. Propagation
    and geometric placement share this aim-local seam.
    """

    resolved = resolve_lattice(design, spacing_nm=spacing_nm)
    if isinstance(resolved, ApertureIntentMismatch):
        raise ValueError(resolved.reason)
    return resolved


@dataclass(frozen=True, slots=True)
class Aperture:
    """
    Labels physical sites by stable optical-state identity.
    """

    cells: tuple[Cell, ...]
    states: tuple[State, ...]
    coordinates_nm: NDArray[numpy.integer]
    is_occupied: NDArray[numpy.bool_]
    target_phase: NDArray[numpy.floating]
    state_identities: NDArray[numpy.str_]
    spacing_nm: int
    half_span_nm: int
    evidence: tuple[Reference, ...]
    footprint: ApertureFootprint = ApertureFootprint.CIRCULAR
    phase_levels: NDArray[numpy.integer] | None = None

    def __post_init__(self) -> None:
        """
        Require a complete, rectangular aperture assignment.
        """

        if self.spacing_nm <= 0 or self.half_span_nm <= 0:
            raise ValueError("aperture_scale_invalid")
        if not self.cells or not self.states or not self.evidence:
            raise ValueError("aperture_table_empty")
        cell_ids = tuple(cell.identity for cell in self.cells)
        state_ids = tuple(state.identity for state in self.states)
        if len(set(cell_ids)) != len(cell_ids):
            raise ValueError("cell_identity_duplicate")
        if len(set(state_ids)) != len(state_ids):
            raise ValueError("state_identity_duplicate")
        if not {state.cell_identity for state in self.states}.issubset(cell_ids):
            raise ValueError("state_cell_missing")
        if len(set(self.evidence)) != len(self.evidence):
            raise ValueError("aperture_evidence_duplicate")

        coordinates = numpy.array(
            self.coordinates_nm,
            dtype=numpy.int64,
            copy=True,
        )
        is_occupied = numpy.array(
            self.is_occupied,
            dtype=numpy.bool_,
            copy=True,
        )
        target = numpy.array(self.target_phase, dtype=numpy.float64, copy=True)
        identities = numpy.array(
            self.state_identities,
            dtype=numpy.str_,
            copy=True,
        )
        if (
            is_occupied.ndim != 2
            or coordinates.shape != (*is_occupied.shape, 2)
            or target.shape != is_occupied.shape
            or identities.shape != is_occupied.shape
        ):
            raise ValueError("aperture_map_shape_invalid")
        expected_coordinates, expected_occupied = _centered_grid(
            spacing_nm=self.spacing_nm,
            half_span_nm=self.half_span_nm,
            footprint=self.footprint,
        )
        if not numpy.array_equal(coordinates, expected_coordinates):
            raise ValueError("aperture_coordinates_invalid")
        if not numpy.array_equal(is_occupied, expected_occupied):
            raise ValueError("aperture_mask_invalid")
        if not numpy.any(is_occupied):
            raise ValueError("aperture_empty")
        if numpy.any(identities[~is_occupied] != ""):
            raise ValueError("unoccupied_site_labelled")
        if numpy.any(identities[is_occupied] == ""):
            raise ValueError("occupied_site_unlabelled")
        if not set(identities[is_occupied].tolist()).issubset(state_ids):
            raise ValueError("aperture_state_missing")
        if not numpy.isfinite(target[is_occupied]).all():
            raise ValueError("target_phase_not_finite")
        coordinates.setflags(write=False)
        is_occupied.setflags(write=False)
        target.setflags(write=False)
        identities.setflags(write=False)
        object.__setattr__(self, "coordinates_nm", coordinates)
        object.__setattr__(self, "is_occupied", is_occupied)
        object.__setattr__(self, "target_phase", target)
        object.__setattr__(self, "state_identities", identities)

        if self.phase_levels is not None:
            levels = numpy.array(self.phase_levels, dtype=numpy.int64, copy=True)
            if levels.shape != is_occupied.shape:
                raise ValueError("phase_level_map_shape_invalid")
            if numpy.any(levels[is_occupied] < 0) or numpy.any(
                levels[~is_occupied] != -1
            ):
                raise ValueError("phase_level_map_invalid")
            ordered_states = tuple(
                sorted(self.states, key=lambda state: state.identity)
            )
            state_keys = numpy.asarray(
                [state.identity for state in ordered_states],
                dtype=numpy.str_,
            )
            state_levels = numpy.asarray(
                [
                    -1 if state.phase_level is None else state.phase_level
                    for state in ordered_states
                ],
                dtype=numpy.int64,
            )
            selected = identities[is_occupied]
            selected_indices = numpy.searchsorted(state_keys, selected)
            if numpy.any(state_levels[selected_indices] != levels[is_occupied]):
                raise ValueError("phase_level_state_mismatch")
            levels.setflags(write=False)
            object.__setattr__(self, "phase_levels", levels)

    @property
    def site_count(self) -> int:
        """
        Return the number of assigned lattice sites.
        """

        return int(numpy.count_nonzero(self.is_occupied))

    def as_mapping(self) -> dict[str, object]:
        """
        Return the aperture in evidence-safe form.
        """

        return {
            "cells": {cell.identity: cell.as_mapping() for cell in self.cells},
            "coordinates_nm": self.coordinates_nm.tolist(),
            "evidence": {
                reference.content_hash: reference.as_mapping()
                for reference in self.evidence
            },
            "occupied": self.is_occupied.tolist(),
            "phase_levels": (
                None if self.phase_levels is None else self.phase_levels.tolist()
            ),
            "footprint": self.footprint.value,
            "half_span_nm": self.half_span_nm,
            "spacing_nm": self.spacing_nm,
            "state_identities": self.state_identities.tolist(),
            "states": {state.identity: state.as_mapping() for state in self.states},
            "target_phase": [
                [format(float(value), ".17g") for value in row]
                for row in self.target_phase
            ],
        }

    @classmethod
    def from_document(cls, document: Document) -> Aperture:
        """
        Restore one complete aperture without rebuilding its lattice.
        """

        if document.schema_identifier != APERTURE_SCHEMA:
            raise ValueError("aperture_schema_mismatch")
        values = document.values
        try:
            cells = tuple(
                _cell_from_mapping(value, identity=identity)
                for identity, value in sorted(
                    _mapping(values["cells"], "aperture_cells_invalid").items()
                )
            )
            states = tuple(
                _state_from_mapping(value, identity=identity)
                for identity, value in sorted(
                    _mapping(values["states"], "aperture_states_invalid").items()
                )
            )
            evidence = tuple(
                _reference(value)
                for _identity, value in sorted(
                    _mapping(
                        values["evidence"],
                        "aperture_evidence_invalid",
                    ).items()
                )
            )
            raw_levels = values["phase_levels"]
            aperture = cls(
                cells=cells,
                states=states,
                coordinates_nm=numpy.asarray(
                    values["coordinates_nm"],
                    dtype=numpy.int64,
                ),
                is_occupied=numpy.asarray(
                    values["occupied"],
                    dtype=numpy.bool_,
                ),
                target_phase=numpy.asarray(
                    values["target_phase"],
                    dtype=numpy.float64,
                ),
                state_identities=numpy.asarray(
                    values["state_identities"],
                    dtype=numpy.str_,
                ),
                spacing_nm=_integer(values["spacing_nm"]),
                half_span_nm=_integer(values["half_span_nm"]),
                evidence=evidence,
                footprint=ApertureFootprint(str(values["footprint"])),
                phase_levels=(
                    None
                    if raw_levels is None
                    else numpy.asarray(raw_levels, dtype=numpy.int64)
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("aperture_document_invalid") from error
        if aperture_document(aperture).to_bytes() != document.to_bytes():
            raise ValueError("aperture_document_mismatch")
        return aperture


def form_field(
    aperture: Aperture,
    *,
    wavelength_m: float,
    surface_position_m: float,
    medium: Medium,
    basis: ComponentBasis,
    component_channels: Mapping[str, str | None],
    aperture_reference: Reference,
) -> Field:
    """
    Form one explicit component field on a metalens aperture plane.
    """

    ordered = tuple(
        FieldComponent(
            name,
            _aperture_response(aperture, component_channels[name]),
        )
        for name in basis.components
        if name in component_channels
    )
    shape = ordered[0].values.shape if ordered else (0, 0)
    return Field(
        wavelength_m=wavelength_m,
        surface=PlaneSurface(
            surface_position_m,
            aperture.spacing_nm * 1e-9,
            shape,
        ),
        frame=CoordinateFrame(),
        medium=medium,
        basis=basis,
        electric_components=ordered,
        source_references=(aperture_reference,),
        incident_reference_power=float(numpy.count_nonzero(aperture.is_occupied)),
    )


def form_reference_surface_field(
    aperture: Aperture,
    *,
    responses: Mapping[str, AdmittedReferenceSurface],
    aperture_reference: Reference,
) -> Field:
    """
    Form an aperture field from exact sampled patches, never G0 coefficients.

    Stable state identities select one admitted patch through one vectorized
    lookup. The assembly scales with the field array, not with repeated scans
    of the response table at every aperture site.
    """

    used_identities = tuple(
        sorted(set(aperture.state_identities[aperture.is_occupied].tolist()))
    )
    if tuple(sorted(responses)) != used_identities:
        raise ValueError("reference_surface_response_table_mismatch")
    ordered = tuple(responses[identity] for identity in used_identities)
    if not ordered:
        raise ValueError("reference_surface_responses_empty")
    reference = ordered[0].response
    _require_matching_reference_surfaces(
        aperture,
        tuple(item.response for item in ordered),
    )

    state_keys = numpy.asarray(used_identities, dtype=numpy.str_)
    selected = aperture.state_identities[aperture.is_occupied]
    selected_indices = numpy.searchsorted(state_keys, selected)
    if numpy.any(selected_indices >= len(state_keys)) or numpy.any(
        state_keys[selected_indices] != selected
    ):
        raise ValueError("reference_surface_state_missing")
    index_map = numpy.zeros(aperture.is_occupied.shape, dtype=numpy.int64)
    index_map[aperture.is_occupied] = selected_indices

    field = reference.field
    electric = _assemble_reference_components(
        aperture.is_occupied,
        index_map,
        tuple(item.response.field.electric_components for item in ordered),
    )
    magnetic = _assemble_reference_components(
        aperture.is_occupied,
        index_map,
        tuple(item.response.field.magnetic_components for item in ordered),
    )
    patch_rows, patch_columns = field.surface.shape
    aperture_rows, aperture_columns = aperture.is_occupied.shape
    counts = numpy.bincount(
        selected_indices,
        minlength=len(ordered),
    )
    incident_power = sum(
        int(count) * item.response.field.incident_reference_power
        for count, item in zip(counts, ordered, strict=True)
    )
    return Field(
        wavelength_m=field.wavelength_m,
        surface=PlaneSurface(
            position_m=field.surface.position_m,
            spacing_m=field.surface.spacing_m,
            shape=(
                aperture_rows * patch_rows,
                aperture_columns * patch_columns,
            ),
        ),
        frame=field.frame,
        medium=field.medium,
        basis=field.basis,
        electric_components=electric,
        magnetic_components=magnetic,
        source_references=tuple(
            dict.fromkeys(
                (
                    aperture_reference,
                    *(item.reference for item in ordered),
                )
            )
        ),
        incident_reference_power=float(incident_power),
    )


def reference_surface_cautions(
    response: ReferenceSurfaceResponse,
    response_reference: Reference,
) -> tuple[Caution, ...]:
    """
    Interpret route-neutral response facts as metalens limitations.
    """

    local = Caution(
        concern=_LOCAL_ASSEMBLY_CONCERN,
        explanation=_LOCAL_ASSEMBLY_EXPLANATION,
        source_reference=response_reference,
    )
    if response.order_regime == "zeroth order":
        return (local,)
    return (
        Caution(
            concern=ORDER_CAUTION,
            explanation=ORDER_CAUTION_EXPLANATION,
            source_reference=response_reference,
        ),
        local,
    )


def _require_matching_reference_surfaces(
    aperture: Aperture,
    responses: tuple[ReferenceSurfaceResponse, ...],
) -> None:
    """
    Require every state patch to describe one common physical output plane.
    """

    first = responses[0]
    field = first.field
    row_span = field.surface.shape[0] * field.surface.spacing_m
    column_span = field.surface.shape[1] * field.surface.spacing_m
    period_m = aperture.spacing_nm * 1e-9
    if not (
        math.isclose(row_span, period_m, rel_tol=0, abs_tol=1e-15)
        and math.isclose(column_span, period_m, rel_tol=0, abs_tol=1e-15)
    ):
        raise ValueError("reference_surface_patch_span_mismatch")
    for response in responses[1:]:
        candidate = response.field
        if (
            candidate.wavelength_m != field.wavelength_m
            or candidate.surface != field.surface
            or candidate.frame != field.frame
            or candidate.medium != field.medium
            or candidate.basis is not field.basis
            or candidate.component_names != field.component_names
            or tuple(component.name for component in candidate.magnetic_components)
            != tuple(component.name for component in field.magnetic_components)
            or response.requested_input_basis is not first.requested_input_basis
            or response.order_regime != first.order_regime
            or response.assembly_model != first.assembly_model
        ):
            raise ValueError("reference_surface_response_context_mismatch")


def _assemble_reference_components(
    is_occupied: NDArray[numpy.bool_],
    index_map: NDArray[numpy.integer],
    component_sets: tuple[tuple[FieldComponent, ...], ...],
) -> tuple[FieldComponent, ...]:
    """
    Mosaic every component through one state-index array.
    """

    if not component_sets[0]:
        if any(component_sets):
            raise ValueError("reference_surface_components_mismatch")
        return ()
    component_names = tuple(component.name for component in component_sets[0])
    if any(
        tuple(component.name for component in components) != component_names
        for components in component_sets
    ):
        raise ValueError("reference_surface_components_mismatch")
    formed = []
    for component_index, name in enumerate(component_names):
        patches = numpy.stack(
            tuple(components[component_index].values for components in component_sets)
        )
        selected = patches[index_map]
        selected = numpy.where(
            is_occupied[..., None, None],
            selected,
            0,
        )
        rows, columns, patch_rows, patch_columns = selected.shape
        values = (
            selected.transpose(0, 2, 1, 3)
            .reshape(rows * patch_rows, columns * patch_columns)
            .astype("<c16", copy=False)
        )
        values.setflags(write=False)
        formed.append(FieldComponent(name, values))
    return tuple(formed)


def _aperture_response(
    aperture: Aperture,
    channel: str | None,
) -> NDArray[numpy.complex128]:
    if channel is None:
        return _immutable_field_samples(
            numpy.zeros(
                aperture.is_occupied.shape,
                dtype=numpy.complex128,
            )
        )
    ordered = tuple(sorted(aperture.states, key=lambda state: state.identity))
    identities = numpy.asarray(
        [state.identity for state in ordered],
        dtype=numpy.str_,
    )
    responses = numpy.asarray(
        [state.response(channel).complex_value for state in ordered],
        dtype=numpy.complex128,
    )
    selected = aperture.state_identities[aperture.is_occupied]
    indices = numpy.searchsorted(identities, selected)
    if numpy.any(indices >= identities.size) or numpy.any(
        identities[indices] != selected
    ):
        raise ValueError("aperture_state_missing")
    values = numpy.zeros(
        aperture.is_occupied.shape,
        dtype=numpy.complex128,
    )
    values[aperture.is_occupied] = responses[indices]
    return _immutable_field_samples(values)


def _immutable_field_samples(
    values: NDArray[numpy.complexfloating],
) -> NDArray[numpy.complex128]:
    samples = numpy.array(values, dtype="<c16", order="C", copy=True)
    samples.setflags(write=False)
    return samples


def _centered_grid(
    *,
    spacing_nm: int,
    half_span_nm: int,
    footprint: ApertureFootprint,
) -> tuple[NDArray[numpy.integer], NDArray[numpy.bool_]]:
    """
    Form the unique complete centered grid implied by aperture scale.
    """

    half_cells = (
        math.floor(half_span_nm / spacing_nm)
        if footprint is ApertureFootprint.SQUARE
        else math.ceil(half_span_nm / spacing_nm)
    )
    axis_nm = numpy.arange(-half_cells, half_cells + 1) * spacing_nm
    x_nm, y_nm = numpy.meshgrid(axis_nm, axis_nm)
    coordinates_nm = numpy.stack((x_nm, y_nm), axis=-1)
    is_occupied = (
        numpy.maximum(numpy.abs(x_nm), numpy.abs(y_nm)) <= half_span_nm
        if footprint is ApertureFootprint.SQUARE
        else numpy.hypot(x_nm, y_nm) <= half_span_nm
    )
    return coordinates_nm, is_occupied


def aperture_document(aperture: Aperture) -> Document:
    """
    Encode one realized aperture as metalens evidence.
    """

    return Document(
        APERTURE_SCHEMA,
        aperture.as_mapping(),
    )


def require_assignment_lattice(
    design: MetalensDesign,
    *,
    spacing_nm: int,
    lattice: Lattice | None,
    lattice_reference: Reference | None,
) -> tuple[Lattice, tuple[Reference, ...]]:
    """Use an exact admitted lattice when supplied, retaining legacy direct calls."""

    if lattice is None and lattice_reference is None:
        return lattice_for(design, spacing_nm=spacing_nm), ()
    if lattice is None or lattice_reference is None:
        raise ValueError("physical_lattice_evidence_incomplete")
    expected = resolve_lattice(
        design,
        spacing_nm=spacing_nm,
        spacing_source_reference=lattice.spacing_source_reference,
    )
    if (
        isinstance(expected, ApertureIntentMismatch)
        or not reference_matches(lattice_reference, lattice.document().to_bytes())
        or expected.document().to_bytes() != lattice.document().to_bytes()
    ):
        raise ValueError("physical_lattice_evidence_mismatch")
    return lattice, (lattice_reference,)


def assign_discrete_orientations(
    design: MetalensDesign,
    *,
    spacing_nm: int,
    choice: CellChoice,
    orientation_relation: OrientationRelation,
    orientation_set: OrientationSet,
    choice_reference: Reference,
    orientation_relation_reference: Reference,
    orientation_set_reference: Reference,
    lattice: Lattice | None = None,
    lattice_reference: Reference | None = None,
) -> Aperture:
    """
    Place one admitted orientation set without calling a solver per rotation.
    """

    if not choice.reference_matches(choice_reference):
        raise ValueError("cell_choice_reference_mismatch")
    if not orientation_relation.reference_matches(orientation_relation_reference):
        raise ValueError("orientations_reference_mismatch")
    if not orientation_set.reference_matches(orientation_set_reference):
        raise ValueError("orientation_set_reference_mismatch")
    if (
        orientation_relation.cell_choice_reference != choice_reference
        or orientation_relation.cell_id != choice.cell.identity
        or orientation_relation.binding_reference != choice.binding_reference
        or orientation_relation.library_reference != choice.library_reference
        or orientation_relation.convention_reference != choice.convention_reference
        or orientation_relation.source_references != choice.source_references
        or orientation_set.cell_id != choice.cell.identity
        or orientation_set.orientation_relation_identity
        != orientation_relation.identity
        or orientation_set.orientation_relation_reference
        != orientation_relation_reference
    ):
        raise ValueError("orientation_set_choice_mismatch")

    lattice, lattice_evidence = require_assignment_lattice(
        design,
        spacing_nm=spacing_nm,
        lattice=lattice,
        lattice_reference=lattice_reference,
    )
    is_occupied = lattice.is_occupied
    orientation_indices = nearest_phase_levels(
        numpy.where(is_occupied, lattice.target_phase, 0),
        orientation_set.count,
    )
    orientation_indices[~is_occupied] = -1
    amplitude = math.sqrt(float(choice.useful_power))
    states = tuple(
        State(
            identity=_discrete_orientation_identity(
                choice.cell.identity,
                orientation_set_reference,
                state.index,
                state.orientation_rad,
            ),
            cell_identity=choice.cell.identity,
            responses=(
                Response(
                    channel="converted",
                    real_part=Decimal(
                        str(amplitude * math.cos(float(state.realized_phase)))
                    ),
                    imaginary_part=Decimal(
                        str(amplitude * math.sin(float(state.realized_phase)))
                    ),
                    power=choice.useful_power,
                ),
                Response(
                    channel="retained",
                    real_part=choice.retained.real_part,
                    imaginary_part=choice.retained.imaginary_part,
                    power=choice.leakage_power,
                ),
            ),
            source=orientation_set_reference,
            target_phase=state.target_phase,
            realized_phase=state.realized_phase,
            useful_power=choice.useful_power,
            leakage_power=choice.leakage_power,
            orientation_rad=state.orientation_rad,
        )
        for state in orientation_set.states
    )
    state_lookup = numpy.asarray(
        [state.identity for state in states],
        dtype=numpy.str_,
    )
    identities = numpy.full(
        is_occupied.shape,
        "",
        dtype=state_lookup.dtype,
    )
    identities[is_occupied] = state_lookup[orientation_indices[is_occupied]]
    evidence = tuple(
        dict.fromkeys(
            (
                choice_reference,
                orientation_relation_reference,
                orientation_set_reference,
                choice.height_domain_reference,
                choice.height_choice_reference,
                choice.library_reference,
                choice.convention_reference,
                *lattice_evidence,
                *choice.source_references,
            )
        )
    )
    return Aperture(
        cells=(choice.cell,),
        states=states,
        coordinates_nm=lattice.coordinates_nm,
        is_occupied=is_occupied,
        target_phase=lattice.target_phase,
        state_identities=identities,
        spacing_nm=lattice.spacing_nm,
        half_span_nm=lattice.half_span_nm,
        evidence=evidence,
        footprint=lattice.footprint,
        phase_levels=None,
    )


def assign_continuous_orientations(
    design: MetalensDesign,
    *,
    spacing_nm: int,
    choice: CellChoice,
    orientation_relation: OrientationRelation,
    choice_reference: Reference,
    orientation_relation_reference: Reference,
    lattice: Lattice | None = None,
    lattice_reference: Reference | None = None,
) -> Aperture:
    """
    Place one admitted anisotropic cell without manufactured phase levels.

    The Aperture Module forms the lattice, derives stable oriented states, and
    labels every occupied site through one vectorized identity lookup.
    """

    if not choice.reference_matches(choice_reference):
        raise ValueError("cell_choice_reference_mismatch")
    if not orientation_relation.reference_matches(orientation_relation_reference):
        raise ValueError("orientations_reference_mismatch")
    if (
        orientation_relation.cell_choice_reference != choice_reference
        or orientation_relation.cell_id != choice.cell.identity
        or orientation_relation.binding_reference != choice.binding_reference
        or orientation_relation.library_reference != choice.library_reference
        or orientation_relation.convention_reference != choice.convention_reference
        or orientation_relation.source_references != choice.source_references
    ):
        raise ValueError("orientation_choice_mismatch")
    lattice, lattice_evidence = require_assignment_lattice(
        design,
        spacing_nm=spacing_nm,
        lattice=lattice,
        lattice_reference=lattice_reference,
    )
    is_occupied = lattice.is_occupied
    target_phase = lattice.target_phase
    keys = numpy.full(is_occupied.shape, -1, dtype=numpy.int64)
    keys[is_occupied] = numpy.rint(
        numpy.remainder(
            target_phase[is_occupied],
            float(FULL_TURN),
        )
        * int(PHASE_KEY_SCALE)
    ).astype(
        numpy.int64,
    )
    unique_keys = numpy.unique(keys[is_occupied])
    amplitude = math.sqrt(float(choice.useful_power))
    states = []
    state_identities_by_key = []
    for key in unique_keys:
        target = canonical_phase(Decimal(int(key)) / PHASE_KEY_SCALE)
        orientation = orientation_relation.for_phase(target)
        realized = orientation_relation.realized_phase(orientation)
        identity = _oriented_state_identity(
            choice.cell.identity,
            choice_reference,
            orientation_relation_reference,
            int(key),
            orientation,
        )
        states.append(
            State(
                identity=identity,
                cell_identity=choice.cell.identity,
                responses=(
                    Response(
                        channel="converted",
                        real_part=Decimal(str(amplitude * math.cos(float(realized)))),
                        imaginary_part=Decimal(
                            str(amplitude * math.sin(float(realized)))
                        ),
                        power=choice.useful_power,
                    ),
                    Response(
                        channel="retained",
                        real_part=choice.retained.real_part,
                        imaginary_part=choice.retained.imaginary_part,
                        power=choice.leakage_power,
                    ),
                ),
                source=orientation_relation_reference,
                target_phase=target,
                realized_phase=realized,
                useful_power=choice.useful_power,
                leakage_power=choice.leakage_power,
                orientation_rad=orientation,
            )
        )
        state_identities_by_key.append(identity)
    state_lookup = numpy.asarray(state_identities_by_key, dtype=numpy.str_)
    state_identities = numpy.full(
        is_occupied.shape,
        "",
        dtype=state_lookup.dtype,
    )
    state_identities[is_occupied] = state_lookup[
        numpy.searchsorted(unique_keys, keys[is_occupied])
    ]
    evidence = tuple(
        dict.fromkeys(
            (
                choice_reference,
                orientation_relation_reference,
                choice.height_domain_reference,
                choice.height_choice_reference,
                choice.library_reference,
                choice.convention_reference,
                *lattice_evidence,
                *choice.source_references,
            )
        )
    )
    return Aperture(
        cells=(choice.cell,),
        states=tuple(states),
        coordinates_nm=lattice.coordinates_nm,
        is_occupied=is_occupied,
        target_phase=target_phase,
        state_identities=state_identities,
        spacing_nm=lattice.spacing_nm,
        half_span_nm=lattice.half_span_nm,
        evidence=evidence,
        footprint=lattice.footprint,
        phase_levels=None,
    )


def assign_quantized(
    design: MetalensDesign,
    *,
    spacing_nm: int,
    cells: tuple[Cell, ...],
    states: tuple[State, ...],
    evidence: tuple[Reference, ...],
    lattice: Lattice | None = None,
    lattice_reference: Reference | None = None,
) -> Aperture:
    """
    Assign uniformly quantized phase through one array lookup.
    """

    lattice, lattice_evidence = require_assignment_lattice(
        design,
        spacing_nm=spacing_nm,
        lattice=lattice,
        lattice_reference=lattice_reference,
    )
    is_occupied = lattice.is_occupied
    target = lattice.target_phase
    if not states:
        raise ValueError("phase_states_empty")
    ordered = tuple(
        sorted(
            states,
            key=lambda state: (-1 if state.phase_level is None else state.phase_level),
        )
    )
    levels = tuple(state.phase_level for state in ordered)
    if levels != tuple(range(len(ordered))):
        raise ValueError("phase_levels_incomplete")

    level_map = nearest_phase_levels(
        numpy.where(is_occupied, target, 0),
        len(ordered),
    )
    level_map[~is_occupied] = -1
    state_lookup = numpy.asarray(
        [state.identity for state in ordered],
        dtype=numpy.str_,
    )
    identities = numpy.full(
        is_occupied.shape,
        "",
        dtype=state_lookup.dtype,
    )
    identities[is_occupied] = state_lookup[level_map[is_occupied]]
    return Aperture(
        cells=cells,
        states=ordered,
        coordinates_nm=lattice.coordinates_nm,
        is_occupied=is_occupied,
        target_phase=target,
        state_identities=identities,
        spacing_nm=lattice.spacing_nm,
        half_span_nm=lattice.half_span_nm,
        evidence=tuple(dict.fromkeys((*evidence, *lattice_evidence))),
        footprint=lattice.footprint,
        phase_levels=level_map,
    )


def _oriented_state_identity(
    cell_identity: str,
    choice_reference: Reference,
    orientation_relation_reference: Reference,
    target_phase_key: int,
    orientation: Decimal,
) -> str:
    value = encode_bytes(
        {
            "cell": cell_identity,
            "cell_choice_reference": choice_reference,
            "orientation": format(orientation, "f"),
            "orientations_reference": orientation_relation_reference,
            "target_phase_key": target_phase_key,
        }
    )
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _discrete_orientation_identity(
    cell_identity: str,
    orientation_set_reference: Reference,
    index: int,
    orientation: Decimal,
) -> str:
    value = encode_bytes(
        {
            "cell": cell_identity,
            "index": index,
            "orientation": format(orientation, "f"),
            "orientation_set_reference": orientation_set_reference,
        }
    )
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _cell_from_mapping(value: object, *, identity: str) -> Cell:
    values = _mapping(value, "aperture_cell_invalid")
    geometry_values = _mapping(
        values.get("geometry"),
        "aperture_geometry_invalid",
    )
    if set(geometry_values) == {"diameter_nm"}:
        geometry: Geometry = Circle(_integer(geometry_values["diameter_nm"]))
    elif set(geometry_values) == {"width_nm"}:
        geometry = Square(_integer(geometry_values["width_nm"]))
    elif set(geometry_values) == {"length_nm", "width_nm"}:
        geometry = Rectangle(
            short_side_nm=_integer(geometry_values["width_nm"]),
            long_side_nm=_integer(geometry_values["length_nm"]),
        )
    elif set(geometry_values) == {"major_nm", "minor_nm"}:
        geometry = Ellipse(
            minor_axis_nm=_integer(geometry_values["minor_nm"]),
            major_axis_nm=_integer(geometry_values["major_nm"]),
        )
    else:
        raise ValueError("aperture_geometry_invalid")
    cell = Cell(
        identity=str(values["identity"]),
        atom=_material_from_mapping(values["atom"]),
        substrate=_material_from_mapping(values["substrate"]),
        period_nm=_integer(values["period_nm"]),
        height_nm=_integer(values["height_nm"]),
        geometry=geometry,
        source=_reference(values["source"]),
    )
    if cell.identity != identity or str(values["shape"]) != cell.shape:
        raise ValueError("aperture_cell_identity_mismatch")
    return cell


def _state_from_mapping(value: object, *, identity: str) -> State:
    values = _mapping(value, "aperture_state_invalid")
    response_values = _mapping(
        values["responses"],
        "aperture_responses_invalid",
    )
    responses = tuple(
        _response_from_mapping(response, channel=channel)
        for channel, response in sorted(response_values.items())
    )
    orientation = values["orientation_rad"]
    state = State(
        identity=str(values["identity"]),
        cell_identity=str(values["cell"]),
        responses=responses,
        source=_reference(values["source"]),
        target_phase=Decimal(str(values["target_phase"])),
        realized_phase=Decimal(str(values["realized_phase"])),
        useful_power=Decimal(str(values["useful_power"])),
        leakage_power=Decimal(str(values["leakage_power"])),
        phase_level=(
            None if values["phase_level"] is None else _integer(values["phase_level"])
        ),
        orientation_rad=(None if orientation is None else Decimal(str(orientation))),
    )
    if state.identity != identity:
        raise ValueError("aperture_state_identity_mismatch")
    return state


def _response_from_mapping(value: object, *, channel: str) -> Response:
    values = _mapping(value, "aperture_response_invalid")
    response = Response(
        channel=str(values["channel"]),
        real_part=Decimal(str(values["real"])),
        imaginary_part=Decimal(str(values["imaginary"])),
        power=Decimal(str(values["power"])),
    )
    if response.channel != channel:
        raise ValueError("aperture_response_channel_mismatch")
    return response


def _material_from_mapping(value: object) -> Material:
    values = _mapping(value, "aperture_material_invalid")
    return Material(str(values["name"]), str(values["source"]))


def _reference(value: object) -> Reference:
    return Reference.from_mapping(_mapping(value, "aperture_reference_invalid"))


def _mapping(value: object, finding: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("aperture_integer_invalid")
    return value

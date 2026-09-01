from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math

import numpy

from ...authority import Reference
from ...field.rectilinear import RectilinearPlane
from ...field.reference_surface import RequestedInputBasis
from ...field.sample import ComponentBasis, CoordinateFrame, Medium
from ...science.periodic_response import (
    PeriodicReferenceSurfaceObservation,
    decode_periodic_reference_surface,
)


@dataclass(frozen=True, slots=True)
class ReferenceSurfaceRequest:
    """
    State the construction facts used to validate one native patch.
    """

    wavelength_m: float
    surface: RectilinearPlane
    frame: CoordinateFrame
    medium: Medium
    output_basis: ComponentBasis
    requested_input_basis: RequestedInputBasis
    order_regime: str
    source_references: tuple[Reference, ...]
    incident_reference_power: float

    def __post_init__(self) -> None:
        """
        Refuse incomplete or nonphysical observation expectations.
        """

        if (
            not math.isfinite(self.wavelength_m)
            or self.wavelength_m <= 0
            or type(self.surface) is not RectilinearPlane
            or self.order_regime not in {"zeroth order", "multi order"}
            or not self.source_references
            or not math.isfinite(self.incident_reference_power)
            or self.incident_reference_power <= 0
        ):
            raise ValueError("reference_surface_request_invalid")


def periodic_reference_surface_request(
    value: Mapping[str, object],
    *,
    wavelength_m: float,
    period_m: float,
    transmission_plane_m: float,
    medium: Medium,
    requested_input_basis: RequestedInputBasis,
    order_regime: str,
    source_references: tuple[Reference, ...],
) -> ReferenceSurfaceRequest:
    """
    Bind one native rectilinear patch to its independent construction facts.

    The native payload owns exact sample coordinates.  Construction owns the
    physical period and transmission-plane position; no inferred spacing is
    allowed to validate either fact.
    """

    surface = _rectilinear_surface(value.get("surface"))
    covered_x = (
        surface.horizontal_coordinates_m[-1]
        - surface.horizontal_coordinates_m[0]
    )
    covered_y = (
        surface.vertical_coordinates_m[-1]
        - surface.vertical_coordinates_m[0]
    )
    if (
        not math.isclose(
            surface.position_m,
            transmission_plane_m,
            rel_tol=0,
            abs_tol=1e-15,
        )
        or not math.isclose(
            covered_x,
            period_m,
            rel_tol=1e-9,
            abs_tol=1e-15,
        )
        or not math.isclose(
            covered_y,
            period_m,
            rel_tol=1e-9,
            abs_tol=1e-15,
        )
    ):
        raise ValueError("reference_surface_construction_mismatch")
    return ReferenceSurfaceRequest(
        wavelength_m=wavelength_m,
        surface=surface,
        frame=CoordinateFrame(),
        medium=medium,
        output_basis=ComponentBasis.CARTESIAN,
        requested_input_basis=requested_input_basis,
        order_regime=order_regime,
        source_references=source_references,
        incident_reference_power=1.0,
    )


def decode_reference_surface(
    value: Mapping[str, object],
    *,
    expected: ReferenceSurfaceRequest,
) -> PeriodicReferenceSurfaceObservation:
    """
    Validate one raw observation without forming a uniform field.
    """

    try:
        normalized = _normalize_observation(value)
        observation = decode_periodic_reference_surface(
            normalized
        ).observation
        requested_input_basis = RequestedInputBasis(
            observation.requested_input_basis
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("reference_surface_observation_invalid") from error
    if (
        not math.isclose(
            float(observation.wavelength_m),
            expected.wavelength_m,
            rel_tol=1e-12,
            abs_tol=0,
        )
        or observation.surface != expected.surface
        or observation.frame != expected.frame
        or observation.medium != expected.medium
        or observation.output_basis is not expected.output_basis
        or requested_input_basis is not expected.requested_input_basis
        or observation.order_regime != expected.order_regime
        or not math.isclose(
            float(observation.incident_reference_power),
            expected.incident_reference_power,
            rel_tol=1e-12,
            abs_tol=0,
        )
    ):
        raise ValueError("reference_surface_observation_mismatch")
    return observation


def reference_surface_fixture_succeeds(
    value: object,
    *,
    expected: ReferenceSurfaceRequest,
) -> bool:
    """
    Report whether a fixture returned its finite exact raw observation.
    """

    if not isinstance(value, Mapping):
        return False
    try:
        decode_reference_surface(value, expected=expected)
    except ValueError:
        return False
    return True


def _rectilinear_surface(value: object) -> RectilinearPlane:
    if not isinstance(value, Mapping) or set(value) != {
        "position_m",
        "x_coordinates_m",
        "y_coordinates_m",
    }:
        raise ValueError("reference_surface_surface_invalid")
    try:
        x_coordinates = _coordinates(value["x_coordinates_m"])
        y_coordinates = _coordinates(value["y_coordinates_m"])
        return RectilinearPlane(
            position_m=float(str(value["position_m"])),
            horizontal_coordinates_m=x_coordinates,
            vertical_coordinates_m=y_coordinates,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("reference_surface_surface_invalid") from error


def _coordinates(value: object) -> numpy.ndarray:
    if not isinstance(value, (list, tuple)):
        raise ValueError("reference_surface_coordinates_invalid")
    coordinates = numpy.asarray(
        tuple(float(str(item)) for item in value),
        dtype=numpy.float64,
    )
    if not numpy.isfinite(coordinates).all():
        raise ValueError("reference_surface_coordinates_invalid")
    return coordinates


def _normalize_observation(
    value: Mapping[str, object],
) -> dict[str, object]:
    components = value.get("electric_components")
    surface = value.get("surface")
    if not isinstance(components, Mapping) or not isinstance(surface, Mapping):
        raise ValueError("reference_surface_observation_invalid")
    return {
        **value,
        "electric_components": {
            str(name): {
                str(part): _canonical_samples(samples)
                for part, samples in _required_mapping(encoded).items()
            }
            for name, encoded in components.items()
        },
        "incident_reference_power": _canonical_number(
            value.get("incident_reference_power")
        ),
        "surface": {
            **surface,
            "position_m": _canonical_number(surface.get("position_m")),
            "x_coordinates_m": _canonical_samples(
                surface.get("x_coordinates_m")
            ),
            "y_coordinates_m": _canonical_samples(
                surface.get("y_coordinates_m")
            ),
        },
        "transmitted_power": _canonical_number(
            value.get("transmitted_power")
        ),
        "wavelength_m": _canonical_number(value.get("wavelength_m")),
    }


def _required_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("reference_surface_component_invalid")
    return value


def _canonical_samples(value: object) -> list[object]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("reference_surface_component_invalid")
    return [
        (
            _canonical_samples(item)
            if isinstance(item, (list, tuple))
            else _canonical_number(item)
        )
        for item in value
    ]


def _canonical_number(value: object) -> str:
    if isinstance(value, bool):
        raise ValueError("reference_surface_number_invalid")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("reference_surface_number_invalid") from error
    if not number.is_finite():
        raise ValueError("reference_surface_number_invalid")
    return format(number, "f")

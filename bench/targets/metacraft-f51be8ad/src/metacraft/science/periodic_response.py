from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import math
from types import MappingProxyType
from typing import Generic, Protocol, TypeAlias, TypeVar, final

import numpy

from ..authority import Reference
from ..canonical import canonicalize, encode_text
from ..external_activity import ExternalActivityClosure, ExternalActivityOrigin
from ..field.sample import (
    ComponentBasis,
    CoordinateFrame,
    FieldComponent,
    Medium,
)
from ..field.rectilinear import RectilinearPlane
from .phase import canonical_phase


_LINEAR_INPUT_BASES = frozenset({"x linear", "y linear"})
_INPUT_BASES = _LINEAR_INPUT_BASES | frozenset({"left circular", "right circular"})
_OUTPUT_BASES = frozenset({"cartesian", "circular", "transverse linear"})
_ORDER_REGIMES = frozenset({"zeroth order", "multi order"})
PERIODIC_OBSERVATION_INCOMPLETE_SCHEMA = (
    "metacraft.science.periodic_observation_incomplete"
)

_TRANSMISSION_FIELDS = frozenset(
    {
        "candidate",
        "construction_valid",
        "execution",
        "phase",
        "phase_planes",
        "power",
        "solver_status",
        "transmission",
        "warnings",
    }
)
_POLARIZATION_FIELDS = frozenset(
    {
        "basis",
        "candidate",
        "execution",
        "output_x",
        "output_y",
        "phase_planes",
        "solver_status",
        "warnings",
    }
)
_REFERENCE_SURFACE_FIELDS = frozenset(
    {
        "electric_components",
        "frame",
        "incident_reference_power",
        "medium",
        "order_regime",
        "output_basis",
        "requested_input_basis",
        "surface",
        "transmitted_power",
        "wavelength_m",
    }
)


def _require_positive_integer(value: object, finding: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(finding)
    return value


def _require_name(value: str, finding: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(finding)


def _freeze(value: object) -> object:
    """
    Retain a recursively immutable copy of one canonical observation mapping.
    """

    normalized = canonicalize(value)
    if isinstance(normalized, dict):
        return MappingProxyType(
            {key: _freeze(child) for key, child in normalized.items()}
        )
    if isinstance(normalized, list):
        return tuple(_freeze(child) for child in normalized)
    return normalized


def _frozen_mapping(
    value: Mapping[str, object],
    finding: str,
) -> Mapping[str, object]:
    frozen = _freeze(value)
    if not isinstance(frozen, Mapping):
        raise ValueError(finding)
    return frozen


def _mapping(value: object, finding: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value


def _finite_decimal(value: object, finding: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(finding)
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(finding) from error
    if not number.is_finite():
        raise ValueError(finding)
    return number


def _validate_complex(value: object, finding: str) -> None:
    parts = _mapping(value, finding)
    if set(parts) != {"imaginary_part", "real_part"}:
        raise ValueError(finding)
    _finite_decimal(parts["real_part"], finding)
    _finite_decimal(parts["imaginary_part"], finding)


def _canonical_complex(
    value: object,
    finding: str,
) -> dict[str, str]:
    parts = _mapping(value, finding)
    return {
        "imaginary_part": format(
            _finite_decimal(parts["imaginary_part"], finding),
            "f",
        ),
        "real_part": format(
            _finite_decimal(parts["real_part"], finding),
            "f",
        ),
    }


def _validate_execution(value: object, finding: str) -> None:
    execution = _mapping(value, finding)
    if set(execution) != {
        "native",
        "placement",
        "project",
        "return_code",
        "source",
    }:
        raise ValueError(finding)
    if (
        type(execution["native"]) is not bool
        or type(execution["return_code"]) is not int
        or execution["return_code"] != 0
        or not isinstance(execution["placement"], Mapping)
    ):
        raise ValueError(finding)
    project = execution["project"]
    source = execution["source"]
    if not isinstance(project, str) or not isinstance(source, str):
        raise ValueError(finding)
    _require_name(project, finding)
    _require_name(source, finding)


def _validate_warnings(value: object, finding: str) -> None:
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) for item in value
    ):
        raise ValueError(finding)


def _canonical_warnings(value: object, finding: str) -> list[str]:
    _validate_warnings(value, finding)
    assert isinstance(value, (list, tuple))
    return list(value)


def _validate_candidate(value: object, finding: str) -> None:
    candidate = _mapping(value, finding)
    name = candidate.get("name")
    shape = candidate.get("shape")
    height_nm = candidate.get("height_nm")
    if (
        not isinstance(name, str)
        or not isinstance(shape, str)
        or type(height_nm) is not int
    ):
        raise ValueError(finding)
    try:
        if shape == "circular pillar":
            diameter_nm = candidate["diameter_nm"]
            if type(diameter_nm) is not int:
                raise ValueError(finding)
            geometry: PeriodicCrossSection = CircularCrossSection(diameter_nm)
        elif shape == "square pillar":
            width_nm = candidate["width_nm"]
            if type(width_nm) is not int:
                raise ValueError(finding)
            geometry = SquareCrossSection(width_nm)
        elif shape == "rectangular fin":
            encoded = _mapping(candidate["geometry"], finding)
            if set(encoded) != {"length_nm", "width_nm"}:
                raise ValueError(finding)
            width_nm = encoded["width_nm"]
            length_nm = encoded["length_nm"]
            if type(width_nm) is not int or type(length_nm) is not int:
                raise ValueError(finding)
            geometry = RectangularCrossSection(
                width_nm,
                length_nm,
            )
        elif shape == "elliptical pillar":
            encoded = _mapping(candidate["geometry"], finding)
            if set(encoded) != {"major_nm", "minor_nm"}:
                raise ValueError(finding)
            minor_nm = encoded["minor_nm"]
            major_nm = encoded["major_nm"]
            if type(minor_nm) is not int or type(major_nm) is not int:
                raise ValueError(finding)
            geometry = EllipticalCrossSection(
                minor_nm,
                major_nm,
            )
        else:
            raise ValueError(finding)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(finding) from error
    if canonicalize(candidate) != periodic_cell_mapping(
        cell_identity=name,
        height_nm=height_nm,
        geometry=geometry,
    ):
        raise ValueError(finding)


def _validate_reference_surface_values(
    values: Mapping[str, object],
    finding: str,
) -> None:
    surface_value = _mapping(values["surface"], finding)
    if set(surface_value) != {
        "position_m",
        "x_coordinates_m",
        "y_coordinates_m",
    }:
        raise ValueError(finding)
    try:
        x_coordinates = _coordinate_values(
            surface_value["x_coordinates_m"],
            finding,
        )
        y_coordinates = _coordinate_values(
            surface_value["y_coordinates_m"],
            finding,
        )
        surface = RectilinearPlane(
            position_m=float(str(surface_value["position_m"])),
            horizontal_coordinates_m=x_coordinates,
            vertical_coordinates_m=y_coordinates,
        )
        frame_value = _mapping(values["frame"], finding)
        if set(frame_value) != {
            "normal_axis",
            "propagation_direction",
            "sample_order",
        }:
            raise ValueError(finding)
        order = frame_value["sample_order"]
        if not isinstance(order, (list, tuple)) or len(order) != 2:
            raise ValueError(finding)
        if (
            any(not isinstance(item, str) for item in order)
            or not isinstance(frame_value["normal_axis"], str)
            or not isinstance(
                frame_value["propagation_direction"],
                str,
            )
            or not isinstance(values["medium"], str)
            or not isinstance(values["output_basis"], str)
        ):
            raise ValueError(finding)
        CoordinateFrame(
            sample_order=(order[0], order[1]),
            normal_axis=frame_value["normal_axis"],
            propagation_direction=frame_value["propagation_direction"],
        )
        Medium(values["medium"])
        basis = ComponentBasis(values["output_basis"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(finding) from error
    components = _mapping(values["electric_components"], finding)
    if set(components) != set(basis.components):
        raise ValueError(finding)
    for name in basis.components:
        encoded = _mapping(components[name], finding)
        if set(encoded) != {"imaginary", "real"}:
            raise ValueError(finding)
        _validate_sample_grid(encoded["real"], surface.shape, finding)
        _validate_sample_grid(
            encoded["imaginary"],
            surface.shape,
            finding,
        )
        real = numpy.asarray(encoded["real"], dtype=numpy.float64)
        imaginary = numpy.asarray(encoded["imaginary"], dtype=numpy.float64)
        samples = real + 1j * imaginary
        if not (
            numpy.allclose(samples[0], samples[-1], rtol=1e-9, atol=1e-15)
            and numpy.allclose(
                samples[:, 0],
                samples[:, -1],
                rtol=1e-9,
                atol=1e-15,
            )
        ):
            raise ValueError(finding)


def _coordinate_values(
    value: object,
    finding: str,
) -> numpy.ndarray:
    if not isinstance(value, (list, tuple)):
        raise ValueError(finding)
    return numpy.asarray(
        tuple(float(_finite_decimal(item, finding)) for item in value),
        dtype=numpy.float64,
    )


def _sequence(value: object, finding: str) -> tuple[object, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(finding)
    return tuple(value)


def _validate_sample_grid(
    value: object,
    shape: tuple[int, int],
    finding: str,
) -> None:
    if not isinstance(value, (list, tuple)) or len(value) != shape[0]:
        raise ValueError(finding)
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) != shape[1]:
            raise ValueError(finding)
        for sample in row:
            _finite_decimal(sample, finding)


def _canonical_sample_grid(
    value: object,
    finding: str,
) -> list[list[str]]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(finding)
    rows: list[list[str]] = []
    for row in value:
        if not isinstance(row, (list, tuple)):
            raise ValueError(finding)
        rows.append([format(_finite_decimal(sample, finding), "f") for sample in row])
    return rows


def _canonical_reference_surface(
    values: Mapping[str, object],
    finding: str,
) -> dict[str, object]:
    surface = _mapping(values["surface"], finding)
    frame = _mapping(values["frame"], finding)
    components = _mapping(values["electric_components"], finding)
    sample_order = frame["sample_order"]
    if not isinstance(sample_order, (list, tuple)):
        raise ValueError(finding)
    return {
        "electric_components": {
            name: {
                part: _canonical_sample_grid(encoded[part], finding)
                for part in ("imaginary", "real")
            }
            for name, value in components.items()
            for encoded in (_mapping(value, finding),)
        },
        "frame": {
            "normal_axis": frame["normal_axis"],
            "propagation_direction": frame["propagation_direction"],
            "sample_order": list(sample_order),
        },
        "incident_reference_power": format(
            _finite_decimal(
                values["incident_reference_power"],
                finding,
            ),
            "f",
        ),
        "medium": values["medium"],
        "order_regime": values["order_regime"],
        "output_basis": values["output_basis"],
        "requested_input_basis": values["requested_input_basis"],
        "surface": {
            "position_m": format(
                _finite_decimal(surface["position_m"], finding),
                "f",
            ),
            "x_coordinates_m": [
                format(_finite_decimal(value, finding), "f")
                for value in _sequence(
                    surface["x_coordinates_m"],
                    finding,
                )
            ],
            "y_coordinates_m": [
                format(_finite_decimal(value, finding), "f")
                for value in _sequence(
                    surface["y_coordinates_m"],
                    finding,
                )
            ],
        },
        "transmitted_power": format(
            _finite_decimal(values["transmitted_power"], finding),
            "f",
        ),
        "wavelength_m": format(
            _finite_decimal(values["wavelength_m"], finding),
            "f",
        ),
    }


def _require_exact_projection(
    original: Mapping[str, object],
    projected: Mapping[str, object],
    finding: str,
) -> None:
    if canonicalize(original) != canonicalize(projected):
        raise ValueError(finding)


@final
@dataclass(frozen=True, slots=True)
class CircularCrossSection:
    """
    Describe one circular periodic pillar cross-section.
    """

    diameter_nm: int

    def __post_init__(self) -> None:
        _require_positive_integer(
            self.diameter_nm,
            "circular_cross_section_diameter_invalid",
        )


@final
@dataclass(frozen=True, slots=True)
class SquareCrossSection:
    """
    Describe one square periodic pillar cross-section.
    """

    width_nm: int

    def __post_init__(self) -> None:
        _require_positive_integer(
            self.width_nm,
            "square_cross_section_width_invalid",
        )


@final
@dataclass(frozen=True, slots=True)
class RectangularCrossSection:
    """
    Describe one rectangular periodic fin cross-section.
    """

    short_side_nm: int
    long_side_nm: int

    def __post_init__(self) -> None:
        _require_positive_integer(
            self.short_side_nm,
            "rectangular_cross_section_dimensions_invalid",
        )
        if (
            type(self.long_side_nm) is not int
            or self.long_side_nm <= self.short_side_nm
        ):
            raise ValueError("rectangular_cross_section_dimensions_invalid")


@final
@dataclass(frozen=True, slots=True)
class EllipticalCrossSection:
    """
    Describe one elliptical periodic pillar cross-section.
    """

    minor_axis_nm: int
    major_axis_nm: int

    def __post_init__(self) -> None:
        _require_positive_integer(
            self.minor_axis_nm,
            "elliptical_cross_section_dimensions_invalid",
        )
        if (
            type(self.major_axis_nm) is not int
            or self.major_axis_nm <= self.minor_axis_nm
        ):
            raise ValueError("elliptical_cross_section_dimensions_invalid")


PeriodicCrossSection: TypeAlias = (
    CircularCrossSection
    | SquareCrossSection
    | RectangularCrossSection
    | EllipticalCrossSection
)


def periodic_cell_mapping(
    *,
    cell_identity: str,
    height_nm: int,
    geometry: PeriodicCrossSection,
) -> dict[str, object]:
    """
    Encode the one exact cell value used by work, artifacts, and receipts.
    """

    _require_name(cell_identity, "periodic_cell_identity_required")
    _require_positive_integer(height_nm, "periodic_height_invalid")
    common: dict[str, object] = {
        "height_nm": height_nm,
        "name": cell_identity,
    }
    if type(geometry) is CircularCrossSection:
        return {
            "diameter_nm": geometry.diameter_nm,
            **common,
            "shape": "circular pillar",
        }
    if type(geometry) is SquareCrossSection:
        return {
            **common,
            "shape": "square pillar",
            "width_nm": geometry.width_nm,
        }
    if type(geometry) is RectangularCrossSection:
        return {
            "geometry": {
                "length_nm": geometry.long_side_nm,
                "width_nm": geometry.short_side_nm,
            },
            **common,
            "shape": "rectangular fin",
        }
    if type(geometry) is EllipticalCrossSection:
        return {
            "geometry": {
                "major_nm": geometry.major_axis_nm,
                "minor_nm": geometry.minor_axis_nm,
            },
            **common,
            "shape": "elliptical pillar",
        }
    raise TypeError("periodic_cross_section_unsupported")


@final
@dataclass(frozen=True, slots=True)
class PeriodicMaterials:
    """
    Bind solver-native material names to their admitted project selections.
    """

    atom_native_identity: str
    atom_refractive_index: Decimal
    atom_source_reference: Reference
    substrate_native_identity: str
    substrate_refractive_index: Decimal
    substrate_source_reference: Reference

    def __post_init__(self) -> None:
        _require_name(
            self.atom_native_identity,
            "periodic_atom_native_identity_required",
        )
        _require_name(
            self.substrate_native_identity,
            "periodic_substrate_native_identity_required",
        )
        for value, finding in (
            (
                self.atom_refractive_index,
                "periodic_atom_refractive_index_invalid",
            ),
            (
                self.substrate_refractive_index,
                "periodic_substrate_refractive_index_invalid",
            ),
        ):
            if type(value) is not Decimal or not value.is_finite() or value <= 0:
                raise ValueError(finding)

    @property
    def source_references(self) -> tuple[Reference, Reference]:
        """
        Return the atom and substrate material evidence references.
        """

        return (
            self.atom_source_reference,
            self.substrate_source_reference,
        )


@final
@dataclass(frozen=True, slots=True)
class PeriodicWork:
    """
    Describe one internally planned physical periodic observation.

    This sealed value is not a public package export. The metalens canonical
    planner is its sole supported constructor and is the identity authority
    for every field that the admitted receipt does not itself carry. Product
    and recorded Adapters treat ``work_identity`` as the opaque Authority key;
    they strictly validate every physical fact that the receipt does carry.
    """

    cell_identity: str
    work_identity: str
    observation_schema: str
    wavelength_nm: int
    period_nm: int
    height_nm: int
    geometry: PeriodicCrossSection
    materials: PeriodicMaterials
    source_references: tuple[Reference, ...]
    binding_reference: Reference
    capacity_scope: str
    input_basis: str
    output_basis: str
    order_regime: str

    def __post_init__(self) -> None:
        for value, finding in (
            (self.cell_identity, "periodic_cell_identity_required"),
            (self.work_identity, "periodic_work_identity_required"),
            (
                self.observation_schema,
                "periodic_observation_schema_required",
            ),
            (self.capacity_scope, "periodic_capacity_scope_required"),
        ):
            _require_name(value, finding)
        for value, finding in (
            (self.wavelength_nm, "periodic_wavelength_invalid"),
            (self.period_nm, "periodic_period_invalid"),
            (self.height_nm, "periodic_height_invalid"),
        ):
            _require_positive_integer(value, finding)
        if self.input_basis not in _INPUT_BASES:
            raise ValueError("periodic_input_basis_invalid")
        if self.output_basis not in _OUTPUT_BASES:
            raise ValueError("periodic_output_basis_invalid")
        if self.order_regime not in _ORDER_REGIMES:
            raise ValueError("periodic_order_regime_invalid")
        if not self.source_references or len(set(self.source_references)) != len(
            self.source_references
        ):
            raise ValueError("periodic_source_references_invalid")

    def candidate_mapping(self) -> dict[str, object]:
        """
        Return the exact cell value bound to this Authority work identity.
        """

        return periodic_cell_mapping(
            cell_identity=self.cell_identity,
            height_nm=self.height_nm,
            geometry=self.geometry,
        )


def _validate_batch(
    request_identity: str,
    items: tuple[PeriodicWork, ...],
    *,
    response_kind: str,
) -> None:
    _require_name(
        request_identity,
        "periodic_response_request_identity_required",
    )
    if not items:
        raise ValueError("periodic_response_items_required")
    identities = tuple(item.work_identity for item in items)
    if len(set(identities)) != len(identities):
        raise ValueError("periodic_response_work_duplicate")
    if any(_batch_context(item) != _batch_context(items[0]) for item in items[1:]):
        raise ValueError("periodic_response_batch_context_mismatch")
    if request_identity != periodic_request_identity(
        response_kind,
        identities,
    ):
        raise ValueError("periodic_response_request_identity_mismatch")


def _batch_context(work: PeriodicWork) -> tuple[object, ...]:
    """
    Identify the physical and execution facts shared by one native batch.

    Cell geometry remains item-local because one complete library spans its
    lateral feature axis. Height is one selected library context.
    """

    return (
        work.observation_schema,
        work.wavelength_nm,
        work.period_nm,
        work.height_nm,
        work.materials,
        work.source_references,
        work.binding_reference,
        work.capacity_scope,
        work.order_regime,
    )


def _polarization_context(work: PeriodicWork) -> tuple[object, ...]:
    """
    Identify every Jones-pair fact except input basis and work identity.
    """

    return (
        work.cell_identity,
        work.observation_schema,
        work.wavelength_nm,
        work.period_nm,
        work.height_nm,
        work.geometry,
        work.materials,
        work.source_references,
        work.binding_reference,
        work.capacity_scope,
        work.output_basis,
        work.order_regime,
    )


def periodic_request_identity(
    response_kind: str,
    work_identities: tuple[str, ...],
) -> str:
    """
    Bind one sealed batch identity to its variant and exact ordered work.
    """

    if response_kind not in {
        "transmission",
        "polarization",
    }:
        raise ValueError("periodic_response_kind_unsupported")
    if (
        not work_identities
        or any(
            not isinstance(identity, str) or not identity.strip()
            for identity in work_identities
        )
        or len(set(work_identities)) != len(work_identities)
    ):
        raise ValueError("periodic_response_work_identity_invalid")
    request = encode_text(
        {
            "response_kind": response_kind,
            "work_identities": work_identities,
        }
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(request).hexdigest()


@final
@dataclass(frozen=True, slots=True)
class PeriodicTransmissionRequest:
    """
    Request one sealed batch of periodic transmission observations.
    """

    request_identity: str
    items: tuple[PeriodicWork, ...]

    def __post_init__(self) -> None:
        _validate_batch(
            self.request_identity,
            self.items,
            response_kind="transmission",
        )
        if any(
            type(item.geometry) not in {CircularCrossSection, SquareCrossSection}
            or item.input_basis not in _LINEAR_INPUT_BASES
            or item.output_basis != "transverse linear"
            for item in self.items
        ) or any(
            item.input_basis != self.items[0].input_basis for item in self.items[1:]
        ):
            raise ValueError("periodic_transmission_variant_invalid")


@final
@dataclass(frozen=True, slots=True)
class PeriodicPolarizationRequest:
    """
    Request paired linear-basis polarization observations.
    """

    request_identity: str
    items: tuple[PeriodicWork, ...]

    def __post_init__(self) -> None:
        _validate_batch(
            self.request_identity,
            self.items,
            response_kind="polarization",
        )
        bases_by_cell: dict[str, list[str]] = {}
        work_by_cell: dict[str, list[PeriodicWork]] = {}
        for item in self.items:
            if (
                type(item.geometry)
                not in {
                    RectangularCrossSection,
                    EllipticalCrossSection,
                }
                or item.input_basis not in _LINEAR_INPUT_BASES
                or item.output_basis != "cartesian"
            ):
                raise ValueError("periodic_polarization_variant_invalid")
            bases_by_cell.setdefault(item.cell_identity, []).append(item.input_basis)
            work_by_cell.setdefault(item.cell_identity, []).append(item)
        if any(
            Counter(bases) != Counter({"x linear": 1, "y linear": 1})
            for bases in bases_by_cell.values()
        ):
            raise ValueError("periodic_polarization_bases_incomplete")
        for pair in work_by_cell.values():
            if len(pair) != 2 or _polarization_context(
                pair[0]
            ) != _polarization_context(pair[1]):
                raise ValueError("periodic_polarization_context_mismatch")


PeriodicResponseRequest: TypeAlias = (
    PeriodicTransmissionRequest | PeriodicPolarizationRequest
)


@final
@dataclass(frozen=True, slots=True)
class PeriodicCellObservation:
    """
    Identify the exact periodic cell represented by one observation.
    """

    cell_identity: str
    height_nm: int
    geometry: PeriodicCrossSection

    def __post_init__(self) -> None:
        """
        Require one named, positive, closed-geometry cell.
        """

        _require_name(self.cell_identity, "periodic_cell_identity_required")
        _require_positive_integer(
            self.height_nm,
            "periodic_height_invalid",
        )
        if type(self.geometry) not in {
            CircularCrossSection,
            SquareCrossSection,
            RectangularCrossSection,
            EllipticalCrossSection,
        }:
            raise TypeError("periodic_cross_section_unsupported")


@final
@dataclass(frozen=True, slots=True)
class PeriodicComplexValue:
    """
    Retain one finite complex response as an exact Decimal pair.
    """

    real_part: Decimal
    imaginary_part: Decimal

    def __post_init__(self) -> None:
        """
        Reject non-Decimal and non-finite complex parts.
        """

        if (
            type(self.real_part) is not Decimal
            or type(self.imaginary_part) is not Decimal
            or not self.real_part.is_finite()
            or not self.imaginary_part.is_finite()
        ):
            raise ValueError("periodic_complex_value_invalid")


@final
@dataclass(frozen=True, slots=True)
class PeriodicTransmissionObservation:
    """
    Expose one completed periodic transmission as typed physical values.
    """

    cell: PeriodicCellObservation
    transmission: PeriodicComplexValue
    useful_power: Decimal
    leakage_power: Decimal
    realized_phase: Decimal
    phase_planes: str
    warnings: tuple[str, ...]
    reference_surface: PeriodicReferenceSurfaceObservation | None

    def __post_init__(self) -> None:
        finding = "periodic_transmission_observation_invalid"
        if not (
            type(self.cell) is PeriodicCellObservation
            and type(self.transmission) is PeriodicComplexValue
            and type(self.useful_power) is Decimal
            and self.useful_power.is_finite()
            and Decimal(0) <= self.useful_power <= Decimal(1)
            and type(self.leakage_power) is Decimal
            and self.leakage_power.is_finite()
            and Decimal(0) <= self.leakage_power <= Decimal(1)
            and self.leakage_power == Decimal(1) - self.useful_power
            and type(self.realized_phase) is Decimal
            and self.realized_phase.is_finite()
            and self.realized_phase == canonical_phase(self.realized_phase)
            and isinstance(self.warnings, tuple)
            and all(isinstance(warning, str) for warning in self.warnings)
            and (
                self.reference_surface is None
                or type(self.reference_surface) is PeriodicReferenceSurfaceObservation
            )
        ):
            raise ValueError(finding)
        _require_name(self.phase_planes, finding)


@final
@dataclass(frozen=True, slots=True)
class PeriodicPolarizationObservation:
    """
    Expose one completed linear-basis polarization response.
    """

    input_basis: str
    cell: PeriodicCellObservation
    output_x: PeriodicComplexValue
    output_y: PeriodicComplexValue
    phase_planes: str
    warnings: tuple[str, ...]
    reference_surface: PeriodicReferenceSurfaceObservation | None

    def __post_init__(self) -> None:
        finding = "periodic_polarization_observation_invalid"
        if (
            self.input_basis not in {"x", "y"}
            or type(self.cell) is not PeriodicCellObservation
            or type(self.output_x) is not PeriodicComplexValue
            or type(self.output_y) is not PeriodicComplexValue
            or not isinstance(self.warnings, tuple)
            or any(not isinstance(warning, str) for warning in self.warnings)
            or (
                self.reference_surface is not None
                and type(self.reference_surface)
                is not PeriodicReferenceSurfaceObservation
            )
        ):
            raise ValueError(finding)
        _require_name(self.phase_planes, finding)


@final
@dataclass(frozen=True, slots=True, eq=False)
class PeriodicReferenceSurfaceObservation:
    """
    Expose one finite native rectilinear reference-surface observation.
    """

    requested_input_basis: str
    output_basis: ComponentBasis
    order_regime: str
    surface: RectilinearPlane
    frame: CoordinateFrame
    medium: Medium
    electric_components: tuple[FieldComponent, ...]
    incident_reference_power: Decimal
    transmitted_power: Decimal
    wavelength_m: Decimal

    def __post_init__(self) -> None:
        finding = "periodic_reference_surface_observation_invalid"
        if (
            self.requested_input_basis not in _INPUT_BASES
            or type(self.output_basis) is not ComponentBasis
            or self.order_regime not in _ORDER_REGIMES
            or type(self.surface) is not RectilinearPlane
            or type(self.frame) is not CoordinateFrame
            or type(self.medium) is not Medium
            or not isinstance(self.electric_components, tuple)
            or tuple(component.name for component in self.electric_components)
            != self.output_basis.components
            or any(
                component.values.shape != self.surface.shape
                for component in self.electric_components
            )
            or any(
                not (
                    numpy.allclose(
                        component.values[0],
                        component.values[-1],
                        rtol=1e-9,
                        atol=1e-15,
                    )
                    and numpy.allclose(
                        component.values[:, 0],
                        component.values[:, -1],
                        rtol=1e-9,
                        atol=1e-15,
                    )
                )
                for component in self.electric_components
            )
            or type(self.incident_reference_power) is not Decimal
            or not self.incident_reference_power.is_finite()
            or self.incident_reference_power <= 0
            or type(self.transmitted_power) is not Decimal
            or not self.transmitted_power.is_finite()
            or self.transmitted_power < 0
            or type(self.wavelength_m) is not Decimal
            or not self.wavelength_m.is_finite()
            or self.wavelength_m <= 0
        ):
            raise ValueError(finding)

    def __eq__(self, other: object) -> bool:
        """
        Compare physical values without NumPy's ambiguous array truth.
        """

        if type(other) is not PeriodicReferenceSurfaceObservation:
            return NotImplemented
        return (
            self.requested_input_basis == other.requested_input_basis
            and self.output_basis is other.output_basis
            and self.order_regime == other.order_regime
            and self.surface == other.surface
            and self.frame == other.frame
            and self.medium == other.medium
            and self.incident_reference_power == other.incident_reference_power
            and self.transmitted_power == other.transmitted_power
            and self.wavelength_m == other.wavelength_m
            and len(self.electric_components) == len(other.electric_components)
            and all(
                left.name == right.name and numpy.array_equal(left.values, right.values)
                for left, right in zip(
                    self.electric_components,
                    other.electric_components,
                    strict=True,
                )
            )
        )


_PeriodicObservation = TypeVar(
    "_PeriodicObservation",
    PeriodicTransmissionObservation,
    PeriodicPolarizationObservation,
    PeriodicReferenceSurfaceObservation,
)


@final
@dataclass(frozen=True, slots=True)
class PeriodicObservationDocument(Generic[_PeriodicObservation]):
    """
    Keep one typed observation beside its exact private admission value.
    """

    observation: _PeriodicObservation
    _values: Mapping[str, object] = field(repr=False)
    execution_origin: ExternalActivityOrigin

    def as_mapping(self) -> Mapping[str, object]:
        """
        Return a detached canonical value for Authority admission.
        """

        return canonicalize(self._values)


def decode_periodic_transmission(
    values: Mapping[str, object],
) -> PeriodicObservationDocument[PeriodicTransmissionObservation]:
    """
    Strictly decode one canonical transmission admission value.
    """

    finding = "periodic_transmission_observation_invalid"
    frozen = _frozen_mapping(values, finding)
    fields = frozenset(frozen)
    if fields not in {
        _TRANSMISSION_FIELDS,
        _TRANSMISSION_FIELDS | {"reference_surface"},
    }:
        raise ValueError(finding)
    cell = _decode_periodic_cell(frozen["candidate"], finding)
    if frozen["construction_valid"] is not True:
        raise ValueError(finding)
    execution_origin = _decode_execution_origin(frozen["execution"], finding)
    transmission = _decode_complex_value(frozen["transmission"], finding)
    power = _mapping(frozen["power"], finding)
    if set(power) != {"leakage", "useful"}:
        raise ValueError(finding)
    useful_power = _finite_decimal(power["useful"], finding)
    leakage_power = _finite_decimal(power["leakage"], finding)
    phase = _mapping(frozen["phase"], finding)
    if set(phase) != {"value"}:
        raise ValueError(finding)
    realized_phase = canonical_phase(_finite_decimal(phase["value"], finding))
    phase_planes = frozen["phase_planes"]
    if not isinstance(phase_planes, str):
        raise ValueError(finding)
    _require_name(phase_planes, finding)
    warnings = _decode_warnings(frozen["warnings"], finding)
    if frozen.get("solver_status") != "complete":
        raise ValueError(finding)
    encoded_surface = frozen.get("reference_surface")
    surface_document = (
        None
        if encoded_surface is None
        else decode_periodic_reference_surface(_mapping(encoded_surface, finding))
    )
    canonical_values: dict[str, object] = {
        "candidate": canonicalize(frozen["candidate"]),
        "construction_valid": True,
        "execution": canonicalize(frozen["execution"]),
        "phase": {"value": format(realized_phase, "f")},
        "phase_planes": phase_planes,
        "power": {
            "leakage": format(leakage_power, "f"),
            "useful": format(useful_power, "f"),
        },
        "solver_status": "complete",
        "transmission": _canonical_complex(frozen["transmission"], finding),
        "warnings": list(warnings),
    }
    if surface_document is not None:
        canonical_values["reference_surface"] = surface_document.as_mapping()
    _require_exact_projection(frozen, canonical_values, finding)
    observation = PeriodicTransmissionObservation(
        cell=cell,
        transmission=transmission,
        useful_power=useful_power,
        leakage_power=leakage_power,
        realized_phase=realized_phase,
        phase_planes=phase_planes,
        warnings=warnings,
        reference_surface=(
            None if surface_document is None else surface_document.observation
        ),
    )
    return PeriodicObservationDocument(
        observation,
        _frozen_mapping(canonical_values, finding),
        execution_origin,
    )


def decode_periodic_polarization(
    values: Mapping[str, object],
) -> PeriodicObservationDocument[PeriodicPolarizationObservation]:
    """
    Strictly decode one canonical polarization admission value.
    """

    finding = "periodic_polarization_observation_invalid"
    frozen = _frozen_mapping(values, finding)
    fields = frozenset(frozen)
    if fields not in {
        _POLARIZATION_FIELDS,
        _POLARIZATION_FIELDS | {"reference_surface"},
    }:
        raise ValueError(finding)
    input_basis = frozen.get("basis")
    if not isinstance(input_basis, str) or input_basis not in {"x", "y"}:
        raise ValueError(finding)
    cell = _decode_periodic_cell(frozen["candidate"], finding)
    execution_origin = _decode_execution_origin(frozen["execution"], finding)
    output_x = _decode_complex_value(frozen["output_x"], finding)
    output_y = _decode_complex_value(frozen["output_y"], finding)
    phase_planes = frozen["phase_planes"]
    if not isinstance(phase_planes, str):
        raise ValueError(finding)
    _require_name(phase_planes, finding)
    warnings = _decode_warnings(frozen["warnings"], finding)
    if frozen.get("solver_status") != "complete":
        raise ValueError(finding)
    encoded_surface = frozen.get("reference_surface")
    surface_document = (
        None
        if encoded_surface is None
        else decode_periodic_reference_surface(_mapping(encoded_surface, finding))
    )
    canonical_values: dict[str, object] = {
        "basis": input_basis,
        "candidate": canonicalize(frozen["candidate"]),
        "execution": canonicalize(frozen["execution"]),
        "output_x": _canonical_complex(frozen["output_x"], finding),
        "output_y": _canonical_complex(frozen["output_y"], finding),
        "phase_planes": phase_planes,
        "solver_status": "complete",
        "warnings": list(warnings),
    }
    if surface_document is not None:
        canonical_values["reference_surface"] = surface_document.as_mapping()
    _require_exact_projection(frozen, canonical_values, finding)
    observation = PeriodicPolarizationObservation(
        input_basis=input_basis,
        cell=cell,
        output_x=output_x,
        output_y=output_y,
        phase_planes=phase_planes,
        warnings=warnings,
        reference_surface=(
            None if surface_document is None else surface_document.observation
        ),
    )
    return PeriodicObservationDocument(
        observation,
        _frozen_mapping(canonical_values, finding),
        execution_origin,
    )


def decode_periodic_reference_surface(
    values: Mapping[str, object],
) -> PeriodicObservationDocument[PeriodicReferenceSurfaceObservation]:
    """
    Strictly decode one canonical sampled-surface admission value.
    """

    finding = "periodic_reference_surface_observation_invalid"
    frozen = _frozen_mapping(values, finding)
    if frozenset(frozen) != _REFERENCE_SURFACE_FIELDS:
        raise ValueError(finding)
    if frozen.get("requested_input_basis") not in _INPUT_BASES:
        raise ValueError(finding)
    if frozen.get("output_basis") not in _OUTPUT_BASES:
        raise ValueError(finding)
    if frozen.get("order_regime") not in _ORDER_REGIMES:
        raise ValueError(finding)
    _validate_reference_surface_values(frozen, finding)
    canonical_values = _canonical_reference_surface(frozen, finding)
    _require_exact_projection(frozen, canonical_values, finding)
    surface_values = _mapping(canonical_values["surface"], finding)
    frame_values = _mapping(canonical_values["frame"], finding)
    order_values = frame_values["sample_order"]
    if not isinstance(order_values, list):
        raise ValueError(finding)
    output_basis = ComponentBasis(str(canonical_values["output_basis"]))
    component_values = _mapping(
        canonical_values["electric_components"],
        finding,
    )
    surface = RectilinearPlane(
        position_m=float(str(surface_values["position_m"])),
        horizontal_coordinates_m=_coordinate_values(
            surface_values["x_coordinates_m"],
            finding,
        ),
        vertical_coordinates_m=_coordinate_values(
            surface_values["y_coordinates_m"],
            finding,
        ),
    )
    components = tuple(
        FieldComponent(
            name,
            _decode_component_samples(
                component_values[name],
                surface.shape,
                finding,
            ),
        )
        for name in output_basis.components
    )
    observation = PeriodicReferenceSurfaceObservation(
        requested_input_basis=str(canonical_values["requested_input_basis"]),
        output_basis=output_basis,
        order_regime=str(canonical_values["order_regime"]),
        surface=surface,
        frame=CoordinateFrame(
            sample_order=(str(order_values[0]), str(order_values[1])),
            normal_axis=str(frame_values["normal_axis"]),
            propagation_direction=str(frame_values["propagation_direction"]),
        ),
        medium=Medium(str(canonical_values["medium"])),
        electric_components=components,
        incident_reference_power=Decimal(
            str(canonical_values["incident_reference_power"])
        ),
        transmitted_power=Decimal(str(canonical_values["transmitted_power"])),
        wavelength_m=Decimal(str(canonical_values["wavelength_m"])),
    )
    return PeriodicObservationDocument(
        observation,
        _frozen_mapping(canonical_values, finding),
        ExternalActivityOrigin.NONE,
    )


def _decode_periodic_cell(
    value: object,
    finding: str,
) -> PeriodicCellObservation:
    _validate_candidate(value, finding)
    candidate = _mapping(value, finding)
    shape = candidate["shape"]
    if shape == "circular pillar":
        geometry: PeriodicCrossSection = CircularCrossSection(
            _exact_integer(candidate["diameter_nm"], finding)
        )
    elif shape == "square pillar":
        geometry = SquareCrossSection(_exact_integer(candidate["width_nm"], finding))
    elif shape == "rectangular fin":
        encoded = _mapping(candidate["geometry"], finding)
        geometry = RectangularCrossSection(
            _exact_integer(encoded["width_nm"], finding),
            _exact_integer(encoded["length_nm"], finding),
        )
    elif shape == "elliptical pillar":
        encoded = _mapping(candidate["geometry"], finding)
        geometry = EllipticalCrossSection(
            _exact_integer(encoded["minor_nm"], finding),
            _exact_integer(encoded["major_nm"], finding),
        )
    else:
        raise ValueError(finding)
    return PeriodicCellObservation(
        cell_identity=str(candidate["name"]),
        height_nm=_exact_integer(candidate["height_nm"], finding),
        geometry=geometry,
    )


def _decode_complex_value(
    value: object,
    finding: str,
) -> PeriodicComplexValue:
    _validate_complex(value, finding)
    encoded = _mapping(value, finding)
    return PeriodicComplexValue(
        real_part=_finite_decimal(encoded["real_part"], finding),
        imaginary_part=_finite_decimal(encoded["imaginary_part"], finding),
    )


def _exact_integer(value: object, finding: str) -> int:
    if type(value) is not int:
        raise ValueError(finding)
    return value


def _decode_execution_origin(
    value: object,
    finding: str,
) -> ExternalActivityOrigin:
    _validate_execution(value, finding)
    execution = _mapping(value, finding)
    return (
        ExternalActivityOrigin.NATIVE
        if execution["native"] is True
        else ExternalActivityOrigin.RECORDED
    )


def _decode_warnings(value: object, finding: str) -> tuple[str, ...]:
    _validate_warnings(value, finding)
    assert isinstance(value, (list, tuple))
    return tuple(value)


def _decode_component_samples(
    value: object,
    shape: tuple[int, int],
    finding: str,
) -> numpy.ndarray:
    encoded = _mapping(value, finding)
    real = numpy.asarray(encoded["real"], dtype=numpy.float64)
    imaginary = numpy.asarray(encoded["imaginary"], dtype=numpy.float64)
    if real.shape != shape or imaginary.shape != shape:
        raise ValueError(finding)
    samples = numpy.asarray(real + 1j * imaginary, dtype="<c16", order="C")
    samples.setflags(write=False)
    return samples


@final
@dataclass(frozen=True, slots=True)
class PeriodicResponseClosure:
    """
    Bind one request to settled qualification and observation activity.
    """

    request_identity: str
    qualification: ExternalActivityClosure
    observation: ExternalActivityClosure

    def __post_init__(self) -> None:
        """
        Require one named request and two exact shared closure values.
        """

        _require_name(
            self.request_identity,
            "periodic_response_request_identity_required",
        )
        if (
            type(self.qualification) is not ExternalActivityClosure
            or type(self.observation) is not ExternalActivityClosure
        ):
            raise TypeError("periodic_response_closure_invalid")


class PeriodicObservationIncompleteReason(str, Enum):
    """
    Name bounded numerical outcomes that produced no physical observation.
    """

    SOLVER_DIVERGED = "periodic_solver_diverged"
    TIME_BUDGET_EXHAUSTED = "periodic_time_budget_exhausted"


@final
@dataclass(frozen=True, slots=True)
class PeriodicObservationIncomplete:
    """
    Retain one settled numerical incompletion as replayable evidence.
    """

    work_identity: str
    reason: PeriodicObservationIncompleteReason
    time_budget: Mapping[str, object]
    attempts: tuple[Mapping[str, object], ...]
    response_change: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        values = _canonical_periodic_incompletion(
            self.work_identity,
            self.reason,
            self.time_budget,
            self.attempts,
            self.response_change,
        )
        object.__setattr__(
            self,
            "time_budget",
            _frozen_mapping(
                _mapping(values["time_budget"], "periodic_incompletion_invalid"),
                "periodic_incompletion_invalid",
            ),
        )
        encoded_attempts = values["attempts"]
        assert isinstance(encoded_attempts, list)
        object.__setattr__(
            self,
            "attempts",
            tuple(
                _frozen_mapping(item, "periodic_incompletion_invalid")
                for item in encoded_attempts
            ),
        )
        encoded_change = values["response_change"]
        object.__setattr__(
            self,
            "response_change",
            (
                None
                if encoded_change is None
                else _frozen_mapping(
                    _mapping(encoded_change, "periodic_incompletion_invalid"),
                    "periodic_incompletion_invalid",
                )
            ),
        )

    def as_mapping(self) -> Mapping[str, object]:
        """
        Return the exact canonical receipt body.
        """

        return _canonical_periodic_incompletion(
            self.work_identity,
            self.reason,
            self.time_budget,
            self.attempts,
            self.response_change,
        )


def _canonical_periodic_incompletion(
    work_identity: str,
    reason: PeriodicObservationIncompleteReason,
    time_budget: Mapping[str, object],
    attempts: tuple[Mapping[str, object], ...],
    response_change: Mapping[str, object] | None,
) -> dict[str, object]:
    finding = "periodic_incompletion_invalid"
    _require_name(work_identity, finding)
    if type(reason) is not PeriodicObservationIncompleteReason:
        raise TypeError(finding)
    budget = _mapping(time_budget, finding)
    if set(budget) != {
        "autoshutoff_threshold",
        "causal_floor_fs",
        "extended_maximum_fs",
        "ordinary_maximum_fs",
        "resonance_guard_fs",
    }:
        raise ValueError(finding)
    durations = {
        name: _require_positive_integer(budget[name], finding)
        for name in (
            "causal_floor_fs",
            "extended_maximum_fs",
            "ordinary_maximum_fs",
            "resonance_guard_fs",
        )
    }
    ordinary_maximum_fs = durations["ordinary_maximum_fs"]
    extended_maximum_fs = durations["extended_maximum_fs"]
    if (
        ordinary_maximum_fs
        < max(
            durations["causal_floor_fs"],
            durations["resonance_guard_fs"],
        )
        or extended_maximum_fs != 2 * ordinary_maximum_fs
    ):
        raise ValueError(finding)
    threshold = _finite_decimal(budget["autoshutoff_threshold"], finding)
    if not Decimal(0) < threshold < Decimal(1):
        raise ValueError(finding)
    if len(attempts) not in {1, 2}:
        raise ValueError(finding)
    canonical_attempts: list[object] = []
    termination_outcomes: list[str] = []
    expected_maxima = (ordinary_maximum_fs, extended_maximum_fs)
    for index, attempt in enumerate(attempts):
        encoded = _mapping(attempt, finding)
        if set(encoded) != {"maximum_time_fs", "termination"}:
            raise ValueError(finding)
        maximum_time_fs = _require_positive_integer(
            encoded["maximum_time_fs"],
            finding,
        )
        if maximum_time_fs != expected_maxima[index]:
            raise ValueError(finding)
        termination = _mapping(encoded["termination"], finding)
        if set(termination) != {
            "autoshutoff_threshold",
            "native_status",
            "outcome",
            "simulated_time_fs",
            "terminal_autoshutoff",
        }:
            raise ValueError(finding)
        status = termination["native_status"]
        outcome = termination["outcome"]
        expected_outcome = {
            1: "maximum_time",
            2: "autoshutoff",
            3: "diverged",
        }
        if type(status) is not int or type(outcome) is not str:
            raise ValueError(finding)
        if expected_outcome.get(status) != outcome:
            raise ValueError(finding)
        attempt_threshold = _finite_decimal(
            termination["autoshutoff_threshold"],
            finding,
        )
        simulated_time_fs = _finite_decimal(
            termination["simulated_time_fs"],
            finding,
        )
        terminal_autoshutoff = _finite_decimal(
            termination["terminal_autoshutoff"],
            finding,
        )
        if (
            attempt_threshold != threshold
            or simulated_time_fs <= 0
            or simulated_time_fs > Decimal(maximum_time_fs + 1)
            or terminal_autoshutoff < 0
        ):
            raise ValueError(finding)
        termination_outcomes.append(outcome)
        canonical_attempts.append(canonicalize(encoded))
    if reason is PeriodicObservationIncompleteReason.SOLVER_DIVERGED:
        if termination_outcomes[-1] != "diverged" or response_change is not None:
            raise ValueError(finding)
    elif len(attempts) != 2 or termination_outcomes[-1] == "diverged":
        raise ValueError(finding)
    canonical_change: dict[str, str] | None = None
    if response_change is not None:
        if not response_change:
            raise ValueError(finding)
        canonical_change = {}
        for name, value in response_change.items():
            _require_name(name, finding)
            if name == "response":
                if not isinstance(value, str):
                    raise ValueError(finding)
                _require_name(value, finding)
                canonical_change[name] = value
                continue
            number = _finite_decimal(value, finding)
            if number < 0:
                raise ValueError(finding)
            canonical_change[name] = format(number, "f")
    return {
        "attempts": canonical_attempts,
        "reason": reason.value,
        "response_change": canonical_change,
        "time_budget": canonicalize(budget),
        "work_identity": work_identity,
    }


def decode_periodic_observation_incomplete(
    values: Mapping[str, object],
) -> PeriodicObservationIncomplete:
    """
    Strictly restore one settled numerical incompletion receipt.
    """

    finding = "periodic_incompletion_invalid"
    if set(values) != {
        "attempts",
        "reason",
        "response_change",
        "time_budget",
        "work_identity",
    }:
        raise ValueError(finding)
    encoded_attempts = values["attempts"]
    if not isinstance(encoded_attempts, (list, tuple)):
        raise ValueError(finding)
    encoded_change = values["response_change"]
    if encoded_change is not None and not isinstance(encoded_change, Mapping):
        raise ValueError(finding)
    try:
        outcome = PeriodicObservationIncomplete(
            work_identity=str(values["work_identity"]),
            reason=PeriodicObservationIncompleteReason(str(values["reason"])),
            time_budget=_mapping(values["time_budget"], finding),
            attempts=tuple(_mapping(item, finding) for item in encoded_attempts),
            response_change=(
                None
                if encoded_change is None
                else {str(name): str(value) for name, value in encoded_change.items()}
            ),
        )
    except (TypeError, ValueError) as error:
        raise ValueError(finding) from error
    if canonicalize(values) != outcome.as_mapping():
        raise ValueError(finding)
    return outcome


@final
@dataclass(frozen=True, slots=True)
class AdmittedPeriodicObservationIncomplete:
    """
    Couple one typed numerical incompletion to its Authority receipt.
    """

    work_identity: str
    outcome: PeriodicObservationIncomplete
    body_reference: Reference
    receipt_reference: Reference

    def __post_init__(self) -> None:
        if self.work_identity != self.outcome.work_identity:
            raise ValueError("periodic_incompletion_work_identity_mismatch")


@final
@dataclass(frozen=True, slots=True)
class AdmittedPeriodicTransmission:
    """
    Couple one typed transmission to its exact Authority receipt.
    """

    work_identity: str
    observation: PeriodicTransmissionObservation
    body_reference: Reference
    receipt_reference: Reference
    _document: PeriodicObservationDocument[PeriodicTransmissionObservation] = field(
        repr=False,
        compare=False,
    )

    @property
    def execution_origin(self) -> ExternalActivityOrigin:
        """
        Return the typed origin validated by the private codec.
        """

        return self._document.execution_origin


@final
@dataclass(frozen=True, slots=True)
class AdmittedPeriodicPolarization:
    """
    Couple one typed polarization response to its Authority receipt.
    """

    work_identity: str
    observation: PeriodicPolarizationObservation
    body_reference: Reference
    receipt_reference: Reference
    _document: PeriodicObservationDocument[PeriodicPolarizationObservation] = field(
        repr=False,
        compare=False,
    )

    @property
    def execution_origin(self) -> ExternalActivityOrigin:
        """
        Return the typed origin validated by the private codec.
        """

        return self._document.execution_origin


def form_admitted_periodic_transmission(
    work_identity: str,
    document: PeriodicObservationDocument[PeriodicTransmissionObservation],
    body_reference: Reference,
    receipt_reference: Reference,
) -> AdmittedPeriodicTransmission:
    """
    Form one admitted typed transmission from its private document.
    """

    return AdmittedPeriodicTransmission(
        work_identity,
        document.observation,
        body_reference,
        receipt_reference,
        document,
    )


def form_admitted_periodic_polarization(
    work_identity: str,
    document: PeriodicObservationDocument[PeriodicPolarizationObservation],
    body_reference: Reference,
    receipt_reference: Reference,
) -> AdmittedPeriodicPolarization:
    """
    Form one admitted typed polarization from its private document.
    """

    return AdmittedPeriodicPolarization(
        work_identity,
        document.observation,
        body_reference,
        receipt_reference,
        document,
    )


def periodic_observation_mapping(
    item: AdmittedPeriodicTransmission | AdmittedPeriodicPolarization,
) -> Mapping[str, object]:
    """
    Return the exact private document retained by one admitted item.
    """

    return item._document.as_mapping()


@final
@dataclass(frozen=True, slots=True)
class ObservedPeriodicTransmission:
    """
    Return one complete admitted transmission batch and its closure.
    """

    request_identity: str
    items: tuple[AdmittedPeriodicTransmission, ...]
    closure: PeriodicResponseClosure

    def __post_init__(self) -> None:
        """
        Keep the operational closure bound to this exact request.
        """

        _validate_outcome_closure(self.request_identity, self.closure)


@final
@dataclass(frozen=True, slots=True)
class ObservedPeriodicPolarization:
    """
    Return one complete admitted polarization batch and its closure.
    """

    request_identity: str
    items: tuple[AdmittedPeriodicPolarization, ...]
    closure: PeriodicResponseClosure

    def __post_init__(self) -> None:
        """
        Keep the operational closure bound to this exact request.
        """

        _validate_outcome_closure(self.request_identity, self.closure)


@final
@dataclass(frozen=True, slots=True)
class PeriodicTransmissionIncomplete:
    """
    Return one settled transmission batch containing numerical incompletions.
    """

    request_identity: str
    items: tuple[AdmittedPeriodicTransmission, ...]
    incomplete_items: tuple[AdmittedPeriodicObservationIncomplete, ...]
    closure: PeriodicResponseClosure

    def __post_init__(self) -> None:
        if not self.incomplete_items:
            raise ValueError("periodic_incomplete_items_required")
        _validate_outcome_closure(self.request_identity, self.closure)


@final
@dataclass(frozen=True, slots=True)
class PeriodicPolarizationIncomplete:
    """
    Return one settled polarization batch containing numerical incompletions.
    """

    request_identity: str
    items: tuple[AdmittedPeriodicPolarization, ...]
    incomplete_items: tuple[AdmittedPeriodicObservationIncomplete, ...]
    closure: PeriodicResponseClosure

    def __post_init__(self) -> None:
        if not self.incomplete_items:
            raise ValueError("periodic_incomplete_items_required")
        _validate_outcome_closure(self.request_identity, self.closure)


class PeriodicResponseUnavailableReason(str, Enum):
    """
    Name the closed expected-absence reasons at the response seam.
    """

    CONFIGURATION_INCOMPLETE = "configuration_incomplete"
    LICENSE_UNAVAILABLE = "license_unavailable"
    CAPACITY_NOT_POSITIVE = "capacity_not_positive"
    CAPACITY_STALE = "capacity_stale"
    TRANSMISSION_RESPONSE_UNQUALIFIED = "transmission_response_unqualified"
    POLARIZATION_RESPONSE_UNQUALIFIED = "polarization_response_unqualified"
    REFERENCE_SURFACE_RESPONSE_UNQUALIFIED = "reference_surface_response_unqualified"
    NATIVE_UNAVAILABLE = "native_unavailable"
    RECORDED_RESPONSE_MISSING = "recorded_periodic_response_missing"


@final
@dataclass(frozen=True, slots=True)
class PeriodicResponseUnavailable:
    """
    Return expected response absence with fully settled activity.
    """

    request_identity: str
    reason: PeriodicResponseUnavailableReason
    closure: PeriodicResponseClosure

    def __post_init__(self) -> None:
        _require_name(
            self.request_identity,
            "periodic_response_request_identity_required",
        )
        if type(self.reason) is not PeriodicResponseUnavailableReason:
            raise TypeError("periodic_response_unavailable_reason_invalid")
        _validate_outcome_closure(self.request_identity, self.closure)


PeriodicResponseOutcome: TypeAlias = (
    ObservedPeriodicTransmission
    | ObservedPeriodicPolarization
    | PeriodicTransmissionIncomplete
    | PeriodicPolarizationIncomplete
    | PeriodicResponseUnavailable
)


@final
@dataclass(frozen=True, slots=True)
class PeriodicResponseContext:
    """
    Expose immutable route-neutral facts needed to compile response work.

    This value carries no product object or callback. Product execution stays
    behind ``PeriodicResponse.observe``.
    """

    binding_reference: Reference
    capacity_scope: str
    response_kinds: tuple[PeriodicResponseKind, ...]
    qualification_closure: ExternalActivityClosure = ExternalActivityClosure.none()

    def __post_init__(self) -> None:
        expected = tuple(
            kind for kind in PeriodicResponseKind if kind in self.response_kinds
        )
        if (
            not self.capacity_scope.strip()
            or not self.response_kinds
            or any(
                type(kind) is not PeriodicResponseKind for kind in self.response_kinds
            )
            or self.response_kinds != expected
            or len(set(self.response_kinds)) != len(self.response_kinds)
            or type(self.qualification_closure) is not ExternalActivityClosure
        ):
            raise ValueError("periodic_response_context_invalid")


class PeriodicResponseKind(str, Enum):
    """
    Name the three independently qualified periodic response abilities.
    """

    TRANSMISSION = "periodic_transmission_response"
    POLARIZATION = "periodic_polarization_response"
    REFERENCE_SURFACE = "periodic_reference_surface_response"


class PeriodicResponse(Protocol):
    """
    Observe sealed periodic requests through one route-neutral method.
    """

    @property
    def context(self) -> PeriodicResponseContext:
        """
        Return exact immutable response facts used to compile requests.
        """

        ...

    def observe(
        self,
        request: PeriodicResponseRequest,
    ) -> PeriodicResponseOutcome:
        """
        Observe one sealed request and return a closed typed outcome.
        """

        ...


def _validate_outcome_closure(
    request_identity: str,
    closure: PeriodicResponseClosure,
) -> None:
    if (
        type(closure) is not PeriodicResponseClosure
        or closure.request_identity != request_identity
    ):
        raise ValueError("periodic_response_closure_identity_mismatch")

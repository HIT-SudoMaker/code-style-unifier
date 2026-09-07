from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy
import torch

from ...authority import Document, Reference
from ...authority import reference_matches
from ...field.evidence import (
    describe_components,
    restore_components,
)
from ...field.sample import (
    ComponentBasis,
    CoordinateFrame,
    Medium,
    PlaneSurface,
)
from ...field.vector_angular_spectrum import LongitudinalPowerPlane
from .focus import FOCAL_REGION_SCHEMA, FocalRegion

LONGITUDINAL_POWER_MEDIA_TYPE = (
    "application/vnd.metacraft.longitudinal-power-density"
)


def focal_region_document(
    region: FocalRegion,
    component_references: Mapping[str, Reference],
    *,
    binding_reference: Reference,
    field_reference: Reference,
    magnetic_component_references: (
        Mapping[str, Reference] | None
    ) = None,
    longitudinal_power_reference: Reference | None = None,
) -> Document:
    """
    Build the manifest that closes one exact focal-region claim.
    """

    components = describe_components(
        region.electric_components,
        component_references,
        magnetic_components=region.magnetic_components,
        magnetic_references=magnetic_component_references,
    )
    shape = region.electric_components[0].values.shape
    power_plane = region.longitudinal_power_plane
    if (power_plane is None) != (longitudinal_power_reference is None):
        raise ValueError("focal_region_power_reference_mismatch")
    if power_plane is not None:
        if longitudinal_power_reference is None:
            raise ValueError("focal_region_power_reference_mismatch")
        power_reference_mapping = longitudinal_power_reference.as_mapping()
    else:
        power_reference_mapping = None
    return Document(
        FOCAL_REGION_SCHEMA,
        {
            "axial_distances_m": [
                _number(value) for value in region.axial_distances_m
            ],
            "axial_peak_intensities": [
                _number(value)
                for value in region.axial_peak_intensities
            ],
            "basis": region.basis.value,
            "binding": binding_reference.as_mapping(),
            "component_axial_peak_intensities": {
                name: [
                    _number(value)
                    for value in (
                        region.component_axial_peak_intensities[name]
                    )
                ]
                for name in region.component_names
            },
            **components,
            "expected_focus_m": _number(region.expected_focus_m),
            "found_focus_m": _number(region.found_focus_m),
            "focus_plane_position_m": _number(region.focus_plane_position_m),
            "frame": _frame_mapping(region.frame),
            "incident_reference_power": _number(
                region.incident_reference_power
            ),
            "medium": {"identity": region.medium.identity},
            "observed_components": list(region.observed_components),
            "realization": dict(region.realization),
            "shape": list(shape),
            "source_field": field_reference.as_mapping(),
            "source_references": _references_mapping(
                region.source_references
            ),
            "spacing_m": _number(region.spacing_m),
            "transmitted_aperture_power": {
                name: _number(
                    region.transmitted_aperture_power[name]
                )
                for name in sorted(region.transmitted_aperture_power)
            },
            "vector_input_power_w": (
                None
                if region.vector_input_power_w is None
                else _number(region.vector_input_power_w)
            ),
            "vector_output_power_w": (
                None
                if region.vector_output_power_w is None
                else _number(region.vector_output_power_w)
            ),
            "longitudinal_power_plane": (
                None
                if power_plane is None
                else {
                    "reference": power_reference_mapping,
                    "surface": _surface_mapping(power_plane.surface),
                    "storage": {
                        "dtype": "<f8",
                        "order": "C",
                        "quantity": "longitudinal Poynting power density",
                        "unit": "W/m^2",
                    },
                }
            ),
            "wavelength_m": _number(region.wavelength_m),
        },
    )


def restore_focal_region(
    document: Document,
    fetch: Callable[[Reference], bytes],
) -> FocalRegion:
    """
    Restore one exact focal region without rerunning propagation.
    """

    if document.schema_identifier != FOCAL_REGION_SCHEMA:
        raise ValueError("focal_region_schema_invalid")
    try:
        values = document.values
        basis = ComponentBasis(str(values["basis"]))
        shape_value = values["shape"]
        if not isinstance(shape_value, list):
            raise ValueError("focal_region_shape_invalid")
        shape = tuple(int(str(item)) for item in shape_value)
        if len(shape) != 2:
            raise ValueError("focal_region_shape_invalid")
        transmitted_power = _mapping(
            values["transmitted_aperture_power"]
        )
        power_plane = _restore_power_plane(
            values["longitudinal_power_plane"],
            shape=shape,
            fetch=fetch,
        )
        component_curves = _mapping(
            values["component_axial_peak_intensities"]
        )
        electric_components, magnetic_components = restore_components(
            values,
            basis=basis,
            shape=shape,
            fetch=fetch,
        )
        return FocalRegion(
            wavelength_m=float(values["wavelength_m"]),
            spacing_m=float(values["spacing_m"]),
            expected_focus_m=float(values["expected_focus_m"]),
            found_focus_m=float(values["found_focus_m"]),
            focus_plane_position_m=float(values["focus_plane_position_m"]),
            observed_components=tuple(
                str(value)
                for value in _sequence(values["observed_components"])
            ),
            axial_distances_m=tuple(
                float(str(value))
                for value in _sequence(values["axial_distances_m"])
            ),
            axial_peak_intensities=tuple(
                float(str(value))
                for value in _sequence(
                    values["axial_peak_intensities"]
                )
            ),
            component_axial_peak_intensities={
                name: tuple(
                    float(str(value))
                    for value in _sequence(component_curves[name])
                )
                for name in basis.components
            },
            frame=_frame(values["frame"]),
            medium=Medium(
                str(_mapping(values["medium"])["identity"])
            ),
            basis=basis,
            electric_components=electric_components,
            magnetic_components=magnetic_components,
            source_references=_restore_references(
                values["source_references"]
            ),
            incident_reference_power=float(
                values["incident_reference_power"]
            ),
            transmitted_aperture_power={
                name: float(transmitted_power[name])
                for name in sorted(transmitted_power)
            },
            vector_input_power_w=(
                None
                if values["vector_input_power_w"] is None
                else float(values["vector_input_power_w"])
            ),
            vector_output_power_w=(
                None
                if values["vector_output_power_w"] is None
                else float(values["vector_output_power_w"])
            ),
            longitudinal_power_plane=power_plane,
            realization=_mapping(values["realization"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("focal_region_evidence_mismatch") from error


def longitudinal_power_bytes(plane: LongitudinalPowerPlane) -> bytes:
    """
    Encode one immutable float64 power-density plane.
    """

    values = plane.power_density_w_per_m2.numpy()
    if values.dtype != numpy.dtype("<f8") or not values.flags.c_contiguous:
        raise ValueError("longitudinal_power_storage_invalid")
    return values.tobytes(order="C")


def longitudinal_power_metadata(
    surface: PlaneSurface,
) -> dict[str, object]:
    """
    Describe one power-density object without embedding its samples.
    """

    return {
        "dtype": "<f8",
        "order": "C",
        "quantity": "longitudinal Poynting power density",
        "shape": list(surface.shape),
        "surface": _surface_mapping(surface),
        "unit": "W/m^2",
    }


def _restore_power_plane(
    value: object,
    *,
    shape: tuple[int, int],
    fetch: Callable[[Reference], bytes],
) -> LongitudinalPowerPlane | None:
    if value is None:
        return None
    values = _mapping(value)
    if _mapping(values["storage"]) != {
        "dtype": "<f8",
        "order": "C",
        "quantity": "longitudinal Poynting power density",
        "unit": "W/m^2",
    }:
        raise ValueError("longitudinal_power_storage_invalid")
    surface = _surface(values["surface"])
    if surface.shape != shape:
        raise ValueError("longitudinal_power_shape_mismatch")
    reference = Reference.from_mapping(_mapping(values["reference"]))
    body = fetch(reference)
    if not reference_matches(
        reference,
        body,
        media_type=LONGITUDINAL_POWER_MEDIA_TYPE,
        descriptive_metadata=longitudinal_power_metadata(surface),
    ):
        raise ValueError("longitudinal_power_reference_mismatch")
    expected_bytes = int(numpy.prod(shape)) * numpy.dtype("<f8").itemsize
    if len(body) != expected_bytes:
        raise ValueError("longitudinal_power_size_mismatch")
    samples = numpy.frombuffer(body, dtype="<f8").reshape(shape, order="C")
    return LongitudinalPowerPlane(surface, torch.from_numpy(samples.copy()))


def _surface_mapping(surface: PlaneSurface) -> dict[str, object]:
    return {
        "kind": "plane",
        "position_m": _number(surface.position_m),
        "shape": list(surface.shape),
        "spacing_m": _number(surface.spacing_m),
    }


def _surface(value: object) -> PlaneSurface:
    values = _mapping(value)
    shape = _sequence(values["shape"])
    if values.get("kind") != "plane" or len(shape) != 2:
        raise ValueError("longitudinal_power_surface_invalid")
    return PlaneSurface(
        float(values["position_m"]),
        float(values["spacing_m"]),
        (int(str(shape[0])), int(str(shape[1]))),
    )


def _frame_mapping(frame: CoordinateFrame) -> dict[str, object]:
    return {
        "normal_axis": frame.normal_axis,
        "propagation_direction": frame.propagation_direction,
        "sample_order": list(frame.sample_order),
    }


def _frame(value: object) -> CoordinateFrame:
    values = _mapping(value)
    order = values["sample_order"]
    if not isinstance(order, list) or len(order) != 2:
        raise ValueError("frame_sample_order_unsupported")
    return CoordinateFrame(
        sample_order=(str(order[0]), str(order[1])),
        normal_axis=str(values["normal_axis"]),
        propagation_direction=str(
            values["propagation_direction"]
        ),
    )


def _references_mapping(
    references: tuple[Reference, ...],
) -> dict[str, object]:
    return {
        f"source_{index:03d}": reference.as_mapping()
        for index, reference in enumerate(references, start=1)
    }


def _restore_references(value: object) -> tuple[Reference, ...]:
    values = _mapping(value)
    return tuple(
        Reference.from_mapping(_mapping(values[name]))
        for name in sorted(values)
    )


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("field_manifest_mapping_invalid")
    return value


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("field_manifest_sequence_invalid")
    return value


def _number(value: float) -> str:
    return format(value, ".17g")

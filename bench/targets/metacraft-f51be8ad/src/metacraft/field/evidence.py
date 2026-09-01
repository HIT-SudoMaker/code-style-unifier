from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..authority import Document, Reference
from .sample import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)

from ._storage import (
    ARRAY_DTYPE as _ARRAY_DTYPE,
    ARRAY_MEDIA_TYPE as _ARRAY_MEDIA_TYPE,
    ARRAY_ORDER as _ARRAY_ORDER,
    array_bytes as _array_bytes,
    array_metadata as _array_metadata,
    require_raw_media as _require_raw_media,
    require_references as _require_references,
    require_storage as _require_storage,
    resolve_component_references as _resolve_component_references,
    restore_components as _restore_components,
)

__all__ = [
    "FIELD_SCHEMA",
    "admit_components",
    "describe_components",
    "field_document",
    "restore_components",
    "restore_field",
]

FIELD_SCHEMA = "metacraft.science.field"


def admit_components(
    electric_components: tuple[FieldComponent, ...],
    magnetic_components: tuple[FieldComponent, ...],
    admit: Callable[..., Reference],
) -> tuple[dict[str, Reference], dict[str, Reference]]:
    """
    Admit exact electric and magnetic component objects.
    """

    return (
        _admit_components(
            electric_components,
            quantity="electric field",
            admit=admit,
        ),
        _admit_components(
            magnetic_components,
            quantity="magnetic field",
            admit=admit,
        ),
    )


def describe_components(
    electric_components: tuple[FieldComponent, ...],
    electric_references: Mapping[str, Reference],
    *,
    magnetic_components: tuple[FieldComponent, ...] = (),
    magnetic_references: Mapping[str, Reference] | None = None,
) -> dict[str, object]:
    """
    Describe exact component references in the one field storage format.
    """

    electric_names = tuple(
        component.name for component in electric_components
    )
    resolved_magnetic_references = magnetic_references or {}
    magnetic_names = tuple(
        component.name for component in magnetic_components
    )
    _require_references(electric_names, electric_references)
    _require_references(magnetic_names, resolved_magnetic_references)
    _require_raw_media(electric_references.values())
    _require_raw_media(resolved_magnetic_references.values())
    return {
        "electric_components": {
            name: electric_references[name].as_mapping()
            for name in electric_names
        },
        "magnetic_components": {
            name: resolved_magnetic_references[name].as_mapping()
            for name in magnetic_names
        },
        "storage": {
            "dtype": _ARRAY_DTYPE,
            "order": _ARRAY_ORDER,
            "unit": "V/m",
        },
    }


def restore_components(
    values: Mapping[str, Any],
    *,
    basis: ComponentBasis,
    shape: tuple[int, ...],
    fetch: Callable[[Reference], bytes],
) -> tuple[
    tuple[FieldComponent, ...],
    tuple[FieldComponent, ...],
]:
    """
    Restore exact electric and optional magnetic component evidence.
    """

    try:
        _require_storage(values["storage"])
        electric_references = _resolve_component_references(
            values["electric_components"],
            basis.components,
        )
        magnetic_references = _resolve_component_references(
            values["magnetic_components"],
            basis.components,
            is_optional=True,
        )
    except KeyError as error:
        raise ValueError("field_components_incomplete") from error
    return (
        _restore_components(
            electric_references,
            shape,
            fetch,
            quantity="electric field",
        ),
        _restore_components(
            magnetic_references,
            shape,
            fetch,
            quantity="magnetic field",
        ),
    )


def field_document(
    schema_identifier: str,
    field: Field,
    component_references: Mapping[str, Reference],
    *,
    magnetic_component_references: Mapping[str, Reference] | None = None,
) -> Document:
    """
    Build the small manifest that closes one field claim.
    """

    components = describe_components(
        field.electric_components,
        component_references,
        magnetic_components=field.magnetic_components,
        magnetic_references=magnetic_component_references,
    )
    return Document(
        schema_identifier,
        {
            "basis": field.basis.value,
            **components,
            "frame": _frame_mapping(field.frame),
            "incident_reference_power": _number(
                field.incident_reference_power
            ),
            "medium": {"identity": field.medium.identity},
            "source_references": _references_mapping(
                field.source_references
            ),
            "surface": {
                "kind": "plane",
                "position_m": _number(field.surface.position_m),
                "shape": list(field.surface.shape),
                "spacing_m": _number(field.surface.spacing_m),
            },
            "wavelength_m": _number(field.wavelength_m),
        },
    )


def restore_field(
    document: Document,
    fetch: Callable[[Reference], bytes],
) -> Field:
    """
    Restore one exact component field from its manifest and raw objects.
    """

    manifest = document.values
    try:
        surface = _surface(manifest["surface"])
        basis = ComponentBasis(str(manifest["basis"]))
        wavelength_m = float(manifest["wavelength_m"])
        frame = _frame(manifest["frame"])
        medium = Medium(str(_mapping(manifest["medium"])["identity"]))
        source_references = _restore_references(
            manifest["source_references"]
        )
        incident_reference_power = float(
            manifest["incident_reference_power"]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("field_evidence_mismatch") from error

    try:
        components, magnetic_components = restore_components(
            manifest,
            basis=basis,
            shape=surface.shape,
            fetch=fetch,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("field_evidence_mismatch") from error

    try:
        return Field(
            wavelength_m=wavelength_m,
            surface=surface,
            frame=frame,
            medium=medium,
            basis=basis,
            electric_components=components,
            magnetic_components=magnetic_components,
            source_references=source_references,
            incident_reference_power=incident_reference_power,
        )
    except ValueError as error:
        raise ValueError("field_evidence_mismatch") from error


def _admit_components(
    components: tuple[FieldComponent, ...],
    *,
    quantity: str,
    admit: Callable[..., Reference],
) -> dict[str, Reference]:
    return {
        component.name: admit(
            _array_bytes(component.values),
            media_type=_ARRAY_MEDIA_TYPE,
            descriptive_metadata=_array_metadata(
                name=component.name,
                shape=component.values.shape,
                quantity=quantity,
            ),
        )
        for component in components
    }


def _surface(value: object) -> PlaneSurface:
    values = _mapping(value)
    if values.get("kind") != "plane":
        raise ValueError("field_surface_unsupported")
    shape_value = values["shape"]
    if not isinstance(shape_value, list) or len(shape_value) != 2:
        raise ValueError("surface_shape_invalid")
    return PlaneSurface(
        position_m=float(values["position_m"]),
        spacing_m=float(values["spacing_m"]),
        shape=(int(shape_value[0]), int(shape_value[1])),
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
        propagation_direction=str(values["propagation_direction"]),
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


def _number(value: float) -> str:
    return format(value, ".17g")

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

import numpy
from numpy.typing import NDArray

from ..authority import Reference, reference_matches
from .sample import FieldComponent

ARRAY_MEDIA_TYPE = "application/vnd.metacraft.ndarray"
ARRAY_DTYPE = "<c16"
ARRAY_ORDER = "C"


def array_bytes(values: NDArray[numpy.complex128]) -> bytes:
    """
    Encode immutable complex samples in the one field-object byte format.
    """

    if (
        values.dtype != numpy.dtype(ARRAY_DTYPE)
        or not values.flags.c_contiguous
        or values.flags.writeable
    ):
        raise ValueError("field_component_storage_invalid")
    return values.tobytes(order=ARRAY_ORDER)


def array_metadata(
    *,
    name: str,
    shape: tuple[int, ...],
    quantity: str,
) -> dict[str, object]:
    """
    Describe one raw component object without duplicating its values.
    """

    return {
        "component": name,
        "dtype": ARRAY_DTYPE,
        "order": ARRAY_ORDER,
        "quantity": quantity,
        "shape": list(shape),
        "unit": "V/m",
    }


def restore_array(
    body: bytes,
    shape: tuple[int, ...],
) -> NDArray[numpy.complex128]:
    """
    Restore one validated component array from its immutable bytes.
    """

    expected = int(numpy.prod(shape)) * numpy.dtype(ARRAY_DTYPE).itemsize
    if len(body) != expected:
        raise ValueError("field_component_size_mismatch")
    return numpy.frombuffer(body, dtype=ARRAY_DTYPE).reshape(
        shape,
        order=ARRAY_ORDER,
    )


def restore_components(
    references: Iterable[tuple[str, Reference]],
    shape: tuple[int, ...],
    fetch: Callable[[Reference], bytes],
    *,
    quantity: str,
) -> tuple[FieldComponent, ...]:
    """
    Fetch and restore one ordered tuple of immutable component arrays.

    This is the shared fetch-and-restore step: each caller resolves its
    manifest references and common transverse shape, and this routine applies
    one byte restoration rule for every named component.
    """

    components: list[FieldComponent] = []
    for name, reference in references:
        body = fetch(reference)
        if not reference_matches(
            reference,
            body,
            media_type=ARRAY_MEDIA_TYPE,
            descriptive_metadata=array_metadata(
                name=name,
                shape=shape,
                quantity=quantity,
            ),
        ):
            raise ValueError("field_component_reference_mismatch")
        samples = restore_array(body, shape)
        components.append(FieldComponent(name, samples))
    return tuple(components)


def require_storage(value: object) -> None:
    """
    Require the shared storage descriptor carried by one manifest.
    """

    if _mapping(value) != {
        "dtype": ARRAY_DTYPE,
        "order": ARRAY_ORDER,
        "unit": "V/m",
    }:
        raise ValueError("field_component_storage_invalid")


def require_raw_media(references: Iterable[Reference]) -> None:
    """
    Require every component reference to name the array media type.
    """

    if any(
        reference.media_type != ARRAY_MEDIA_TYPE
        for reference in references
    ):
        raise ValueError("field_component_media_type_invalid")


def require_references(
    names: tuple[str, ...],
    references: Mapping[str, Reference],
) -> None:
    """
    Require one reference for each component name and nothing extra.
    """

    if set(references) != set(names):
        raise ValueError("field_component_references_incomplete")


def resolve_component_references(
    value: object,
    names: tuple[str, ...],
    *,
    is_optional: bool = False,
) -> tuple[tuple[str, Reference], ...]:
    """
    Resolve a manifest component group into ordered name, reference pairs.
    """

    values = _mapping(value)
    if is_optional and not values:
        return ()
    if tuple(sorted(values)) != tuple(sorted(names)):
        raise ValueError("field_components_incomplete")
    references = tuple(
        (name, Reference.from_mapping(_mapping(values[name])))
        for name in names
    )
    require_raw_media(reference for _, reference in references)
    return references


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("field_manifest_mapping_invalid")
    return value

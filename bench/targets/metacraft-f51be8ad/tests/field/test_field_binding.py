from __future__ import annotations

import inspect

from metacraft.field.angular_spectrum import (
    FieldPropagation,
    propagate_field,
)


def test_field_propagation_requires_one_admitted_realization() -> None:
    """
    Bind one component intent and every numerical choice explicitly.
    """

    assert tuple(inspect.signature(propagate_field).parameters) == (
        "field",
        "distance_range_m",
        "preferred_distance_m",
        "components",
        "realization",
    )
    assert not hasattr(FieldPropagation, "observe")
    assert not hasattr(FieldPropagation, "at")

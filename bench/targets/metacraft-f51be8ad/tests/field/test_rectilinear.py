from __future__ import annotations

from dataclasses import fields

import numpy
import pytest

import metacraft.field.rectilinear as rectilinear_module
from metacraft.field.rectilinear import RectilinearPlane


def test_rectilinear_plane_owns_exact_immutable_coordinate_values() -> None:
    horizontal_owner = numpy.arange(8, dtype=numpy.float32)
    horizontal = horizontal_owner[::2]
    vertical = numpy.asarray((0.0, 0.25), dtype=numpy.float32)

    plane = RectilinearPlane(
        position_m=1.5,
        horizontal_coordinates_m=horizontal,
        vertical_coordinates_m=vertical,
    )
    equal_plane = RectilinearPlane(
        position_m=1.5,
        horizontal_coordinates_m=numpy.asarray((0.0, 2.0, 4.0, 6.0)),
        vertical_coordinates_m=numpy.asarray((0.0, 0.25)),
    )

    horizontal_owner[:] = -1
    assert plane == equal_plane
    assert tuple(field.name for field in fields(RectilinearPlane)) == (
        "position_m",
        "horizontal_coordinates_m",
        "vertical_coordinates_m",
    )
    assert plane.shape == (2, 4)
    assert plane.period_m == 6.0
    for coordinates in (
        plane.horizontal_coordinates_m,
        plane.vertical_coordinates_m,
    ):
        assert coordinates.dtype == numpy.float64
        assert coordinates.flags.c_contiguous
        assert not coordinates.flags.writeable
    assert not hasattr(rectilinear_module, "RectilinearReferenceSurface")


@pytest.mark.parametrize(
    ("arguments", "fault_code"),
    (
        ({"position_m": numpy.inf}, "rectilinear_surface_position_invalid"),
        (
            {"horizontal_coordinates_m": numpy.asarray(((0.0, 1.0),))},
            "rectilinear_surface_coordinates_invalid",
        ),
        (
            {"vertical_coordinates_m": numpy.asarray((0.0,))},
            "rectilinear_surface_coordinates_invalid",
        ),
        (
            {
                "vertical_coordinates_m": numpy.asarray(
                    (0.0 + 1.0j, 1.0 + 2.0j)
                )
            },
            "rectilinear_surface_coordinates_invalid",
        ),
        (
            {"horizontal_coordinates_m": numpy.asarray((0.0, 0.0))},
            "rectilinear_surface_coordinates_not_increasing",
        ),
    ),
)
def test_rectilinear_plane_rejects_invalid_coordinates(
    arguments: dict[str, object],
    fault_code: str,
) -> None:
    values: dict[str, object] = {
        "position_m": 0.0,
        "horizontal_coordinates_m": numpy.asarray((0.0, 1.0)),
        "vertical_coordinates_m": numpy.asarray((0.0, 1.0)),
    }
    values.update(arguments)

    with pytest.raises(ValueError, match=fault_code):
        RectilinearPlane(**values)  # type: ignore[arg-type]

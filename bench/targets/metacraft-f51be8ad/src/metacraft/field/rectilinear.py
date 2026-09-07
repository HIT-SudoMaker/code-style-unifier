from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import final

import numpy
from numpy.typing import NDArray


@final
@dataclass(frozen=True, slots=True, eq=False)
class RectilinearPlane:
    """
    Retain one observed plane on its native rectilinear coordinates.
    """

    position_m: float
    horizontal_coordinates_m: NDArray[numpy.float64]
    vertical_coordinates_m: NDArray[numpy.float64]

    def __post_init__(self) -> None:
        """
        Own finite, immutable, strictly increasing coordinate vectors.
        """

        if (
            isinstance(self.position_m, bool)
            or not isinstance(self.position_m, Real)
            or not math.isfinite(self.position_m)
        ):
            raise ValueError("rectilinear_surface_position_invalid")

        object.__setattr__(self, "position_m", float(self.position_m))
        object.__setattr__(
            self,
            "horizontal_coordinates_m",
            _coordinate_copy(self.horizontal_coordinates_m),
        )
        object.__setattr__(
            self,
            "vertical_coordinates_m",
            _coordinate_copy(self.vertical_coordinates_m),
        )

    def __eq__(self, other: object) -> bool:
        """
        Compare planes by exact scalar and array values without ambiguity.
        """

        if type(other) is not RectilinearPlane:
            return NotImplemented
        return (
            self.position_m == other.position_m
            and numpy.array_equal(
                self.horizontal_coordinates_m,
                other.horizontal_coordinates_m,
            )
            and numpy.array_equal(
                self.vertical_coordinates_m,
                other.vertical_coordinates_m,
            )
        )

    @property
    def shape(self) -> tuple[int, int]:
        """
        Return sample counts in vertical-then-horizontal field order.
        """

        return (
            self.vertical_coordinates_m.size,
            self.horizontal_coordinates_m.size,
        )

    @property
    def period_m(self) -> float:
        """
        Return the horizontal span of the closed periodic observation.
        """

        return float(
            self.horizontal_coordinates_m[-1]
            - self.horizontal_coordinates_m[0]
        )


def _coordinate_copy(coordinates: object) -> NDArray[numpy.float64]:
    if (
        type(coordinates) is not numpy.ndarray
        or coordinates.dtype.kind not in {"f", "i", "u"}
    ):
        raise ValueError("rectilinear_surface_coordinates_invalid")
    try:
        owned = numpy.array(
            coordinates,
            dtype=numpy.float64,
            order="C",
            copy=True,
        )
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("rectilinear_surface_coordinates_invalid") from error
    if (
        owned.ndim != 1
        or owned.size < 2
        or not numpy.isfinite(owned).all()
    ):
        raise ValueError("rectilinear_surface_coordinates_invalid")
    if not numpy.all(numpy.diff(owned) > 0):
        raise ValueError("rectilinear_surface_coordinates_not_increasing")
    owned.setflags(write=False)
    return owned

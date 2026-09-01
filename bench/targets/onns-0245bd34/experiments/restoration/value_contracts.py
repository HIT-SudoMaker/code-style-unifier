from __future__ import annotations

import math
from numbers import Integral, Real

from experiments.restoration.errors import invalid_restoration_contract


def finite_real(name: str, value: object) -> float:
    """Return one finite real value or raise the restoration contract error."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    return normalized


def normalize_array_resolution(
    name: str,
    value: object,
    *,
    minimum_size: int = 1,
) -> tuple[int, int]:
    """Return a two-axis integer resolution above a declared sampling floor."""
    if (
        isinstance(minimum_size, bool)
        or not isinstance(minimum_size, Integral)
        or int(minimum_size) <= 0
    ):
        raise invalid_restoration_contract("minimum_size must be a positive integer")
    if not isinstance(value, tuple) or len(value) != 2:
        raise invalid_restoration_contract(f"{name} must contain height and width")
    normalized: list[int] = []
    for index, item in enumerate(value):
        if (
            isinstance(item, bool)
            or not isinstance(item, Integral)
            or int(item) < int(minimum_size)
        ):
            raise invalid_restoration_contract(
                f"{name}[{index}] must be an integer of at least {minimum_size}"
            )
        normalized.append(int(item))
    return normalized[0], normalized[1]

from __future__ import annotations

import math
from numbers import Integral, Real


def _invalid(name: str, expected: str, actual: object) -> ValueError:
    return ValueError(f"{name} must be {expected}; got {actual!r}")


def _format_supported_values(
    name: str,
    supported: object,
    actual: object,
) -> str:
    return f"{name} must be one of {supported}; got {actual!r}"


def normalize_resolution_pair(
    name: str,
    value: tuple[int, int],
) -> tuple[int, int]:
    try:
        height, width = value
    except (TypeError, ValueError):
        raise _invalid(name, "a pair of positive integers", value) from None
    validate_positive_int(f"{name}[0]", height)
    validate_positive_int(f"{name}[1]", width)
    return int(height), int(width)


def validate_optional_positive_int(name: str, value: int | None) -> None:
    if value is not None:
        validate_positive_int(name, value)


def validate_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise _invalid(name, "a positive integer", value)


def validate_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise _invalid(name, "an integer", value)


def validate_non_negative_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise _invalid(name, "a non-negative integer", value)


def validate_optional_non_negative_number(
    name: str,
    value: float | None,
) -> None:
    if value is not None:
        validate_non_negative_number(name, value)


def validate_non_negative_number(name: str, value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
        or value < 0
    ):
        raise _invalid(name, "a finite non-negative number", value)


def validate_optional_positive_number(
    name: str,
    value: float | None,
) -> None:
    if value is not None:
        validate_positive_number(name, value)


def validate_positive_number(name: str, value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
        or value <= 0
    ):
        raise _invalid(name, "a finite positive number", value)


def validate_optional_positive_odd_int(
    name: str,
    value: int | None,
) -> None:
    if value is not None:
        validate_positive_odd_int(name, value)


def validate_positive_odd_int(name: str, value: int) -> None:
    validate_positive_int(name, value)
    if int(value) % 2 == 0:
        raise _invalid(name, "a positive odd integer", value)


def validate_bool(name: str, value: object) -> None:
    if not isinstance(value, bool):
        raise _invalid(name, "a boolean", value)


def validate_label_index(
    label: int,
    class_count: int,
    *,
    dataset_name: str,
) -> int:
    validate_int("label", label)
    validate_positive_int("class_count", class_count)
    normalized_label = int(label)
    if normalized_label < 0 or normalized_label >= class_count:
        raise ValueError(
            f"{dataset_name} label out of range: "
            f"label={normalized_label}, class_count={class_count}"
        )
    return normalized_label

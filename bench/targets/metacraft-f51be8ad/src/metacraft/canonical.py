from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
import json
from typing import Any


def canonicalize(value: Any) -> Any:
    """
    Return a JSON-shaped value with stable scientific scalars.

    Decimal values remain exact strings. Binary floating-point values are
    rejected at authority seams so callers must choose their precision.
    """

    if is_dataclass(value):
        return {
            field.name: canonicalize(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return canonicalize(value.value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {
            str(key): canonicalize(child)
            for key, child in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, tuple):
        return [canonicalize(child) for child in value]
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [canonicalize(child) for child in value]
    if isinstance(value, float):
        raise TypeError("binary_float_requires_explicit_precision")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported_canonical_value:{type(value).__name__}")


def encode_text(value: Any) -> str:
    """
    Encode the supported JSON subset in canonical member order.
    """

    return json.dumps(
        canonicalize(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def encode_bytes(value: Any) -> bytes:
    """
    Encode the supported JSON subset as UTF-8.
    """

    return encode_text(value).encode("utf-8")

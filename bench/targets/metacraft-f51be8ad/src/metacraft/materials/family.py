from __future__ import annotations

from typing import TypeGuard


def is_canonical_material_family(value: object) -> TypeGuard[str]:
    """
    Recognize one natural lowercase material-family identity.
    """

    return (
        isinstance(value, str)
        and bool(value)
        and value == value.casefold()
        and value == " ".join(value.split())
    )

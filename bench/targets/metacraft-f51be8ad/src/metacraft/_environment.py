from __future__ import annotations

from collections.abc import Collection, Mapping
import os
from pathlib import Path


def read_allowed_environment(
    path: Path,
    *,
    allowed: Collection[str],
    allowed_prefixes: Collection[str] = (),
    family: str,
    inherited: Mapping[str, str] | None = None,
    is_optional: bool = False,
) -> dict[str, str]:
    """
    Read one allowlisted environment file without crossing configuration domains.
    """

    source = os.environ if inherited is None else inherited
    values = {
        key: value
        for key, value in source.items()
        if (
            key in allowed
            or any(key.startswith(prefix) for prefix in allowed_prefixes)
        )
        and value.strip()
    }
    if is_optional and not path.exists():
        return values
    seen: set[str] = set()
    for number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{family}_environment_line_invalid:{number}")
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in allowed and not any(
            key.startswith(prefix) for prefix in allowed_prefixes
        ):
            raise ValueError(f"{family}_environment_key_invalid:{key}")
        if key in seen:
            raise ValueError(f"{family}_environment_key_duplicate:{key}")
        seen.add(key)
        if value:
            values[key] = value
    return values

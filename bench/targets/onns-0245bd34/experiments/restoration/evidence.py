from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
from uuid import uuid4

from experiments.restoration.errors import (
    invalid_restoration_contract,
    invalid_restoration_type,
)


def _serializable(payload: object, *, is_for_hash: bool = False) -> object:
    if is_for_hash:
        hash_payload = getattr(payload, "_config_hash_payload", None)
        if callable(hash_payload):
            payload = hash_payload()
    if payload is None or isinstance(payload, (str, bool, int)):
        return payload
    if isinstance(payload, float):
        if not math.isfinite(payload):
            raise invalid_restoration_contract(
                "non-finite float values are not valid evidence"
            )
        return payload
    if isinstance(payload, Path):
        return payload.as_posix()
    if is_dataclass(payload) and not isinstance(payload, type):
        return {
            field.name: _serializable(
                getattr(payload, field.name),
                is_for_hash=is_for_hash,
            )
            for field in fields(payload)
        }
    if isinstance(payload, Mapping):
        return {
            str(key): _serializable(value, is_for_hash=is_for_hash)
            for key, value in sorted(payload.items(), key=lambda item: str(item[0]))
        }
    if isinstance(payload, (tuple, list)):
        return [
            _serializable(value, is_for_hash=is_for_hash) for value in payload
        ]
    item = getattr(payload, "item", None)
    if callable(item):
        try:
            scalar = item()
        except Exception as error:
            raise invalid_restoration_type(
                f"unsupported evidence value: {type(payload).__name__}"
            ) from error
        if isinstance(scalar, float) and not math.isfinite(scalar):
            raise invalid_restoration_contract(
                "non-finite float values are not valid evidence"
            )
        if scalar is None or isinstance(scalar, (str, int, float, bool)):
            return scalar
    raise invalid_restoration_type(
        f"unsupported evidence value: {type(payload).__name__}"
    )


def compute_config_hash(payload: object) -> str:
    """Return a deterministic SHA-256 identity for a configuration."""
    encoded = json.dumps(
        _serializable(payload, is_for_hash=True),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path | str, payload: object) -> Path:
    """Atomically write one deterministic JSON evidence object."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        _serializable(payload),
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    temporary_path = output_path.with_name(f"._{uuid4().hex[:12]}.tmp")
    try:
        temporary_path.write_text(serialized, encoding="utf-8")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return output_path


def write_runtime(path: Path | str, *, code_version: str | None = None) -> Path:
    """Write reproducibility metadata for one evidence-producing run."""
    metadata: dict[str, object] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
    }
    if code_version is not None:
        metadata["code_version"] = code_version
    for module_name in ("numpy", "torch"):
        try:
            module = __import__(module_name)
        except ImportError:
            metadata[module_name] = None
        else:
            metadata[module_name] = getattr(module, "__version__", None)
            if module_name == "torch":
                metadata["cuda_available"] = bool(module.cuda.is_available())
                metadata["cuda_version"] = module.version.cuda
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    else:
        commit = completed.stdout.strip()
        if commit:
            metadata["git_commit"] = commit
    return write_json(path, metadata)

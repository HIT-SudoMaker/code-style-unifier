"""Regenerate ``rust/SOURCE_MANIFEST.json`` from the working tree.

The manifest freezes the governed Rust baseline without Git, so the freeze
gate in ``tests/architecture/test_scientific_boundary.py`` runs inside a
source archive that has no ``.git``. The governance rule here must stay in
sync with the ``_governed_rust_paths`` helper in that test.

Governed paths (POSIX-relative to ``rust/``):

* ``Cargo.toml`` and ``Cargo.lock`` at the rust root;
* every ``*.rs`` under ``rust/src`` and ``rust/tests``;
* every fixture under ``rust/tests/fixtures``.

``rust/target`` (build output) and the manifest itself are never governed.
Hashes are SHA-256 of file bytes with CRLF normalized to LF, so the manifest
is identical on a Windows checkout (``core.autocrlf``) and in an LF source
archive.

Run from any directory with the project Python::

    C:\\Users\\Administrator\\miniforge3\\envs\\research_env\\python.exe rust/sync_source_manifest.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

_GOVERNED_ROOT_FILES = ("Cargo.toml", "Cargo.lock")
_GOVERNED_SOURCE_DIRS = ("src", "tests")
_FIXTURE_PREFIX = "tests/fixtures/"
_MANIFEST_NAME = "SOURCE_MANIFEST.json"


def _governed_paths(rust_root: Path) -> list[Path]:
    paths: list[Path] = []
    for name in _GOVERNED_ROOT_FILES:
        candidate = rust_root / name
        if candidate.is_file():
            paths.append(candidate)
    for sub in _GOVERNED_SOURCE_DIRS:
        base = rust_root / sub
        for file_path in sorted(base.rglob("*")):
            if not file_path.is_file():
                continue
            relative = file_path.relative_to(rust_root).as_posix()
            if file_path.suffix == ".rs" or relative.startswith(_FIXTURE_PREFIX):
                paths.append(file_path)
    manifest = rust_root / _MANIFEST_NAME
    return sorted({path for path in paths if path != manifest})


def _content_hash(path: Path) -> str:
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    return "sha256:" + hashlib.sha256(normalized).hexdigest()


def build_manifest(rust_root: Path) -> dict[str, str]:
    return {
        path.relative_to(rust_root).as_posix(): _content_hash(path)
        for path in _governed_paths(rust_root)
    }


def main() -> None:
    rust_root = Path(__file__).resolve().parent
    manifest = build_manifest(rust_root)
    target = rust_root / _MANIFEST_NAME
    # Write LF explicitly so the working tree matches the committed blob and a
    # source archive byte-for-byte (the .gitattributes policy is eol=lf).
    payload = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    target.write_bytes(payload.encode("utf-8"))
    print(f"wrote {target} with {len(manifest)} governed paths")


if __name__ == "__main__":
    main()

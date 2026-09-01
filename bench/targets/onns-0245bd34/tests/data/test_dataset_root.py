from __future__ import annotations

from pathlib import Path

from data.data_source.dataset_root import resolve_dataset_root


def test_resolve_dataset_root_accepts_pathlike_explicit_root(tmp_path: Path) -> None:
    root = tmp_path / "raw"

    assert resolve_dataset_root(root) == str(root)

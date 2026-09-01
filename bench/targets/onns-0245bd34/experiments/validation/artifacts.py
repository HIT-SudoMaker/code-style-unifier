from __future__ import annotations

from collections.abc import Iterable, Sequence
import csv
import os
from pathlib import Path
import shutil


def clear_output_dir(path: Path) -> Path:
    """
    安全清理并重建验证输出目录
    """
    _reject_unsafe_output_dir(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_output_dir(path: Path) -> Path:
    """
    确保验证输出目录存在
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_summary(
    output_dir: Path,
    lines: Sequence[str],
    *,
    name: str | None = None,
) -> Path:
    """
    写入验证摘要
    """
    filename = "summary.md" if name is None else f"{name}_summary.md"
    path = ensure_output_dir(output_dir) / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_metrics(
    output_dir: Path,
    rows: Sequence[dict[str, object]],
    *,
    name: str | None = None,
) -> Path:
    """
    写入验证指标
    """
    filename = "metrics.csv" if name is None else f"{name}_metrics.csv"
    path = ensure_output_dir(output_dir) / filename
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def aggregate_status(results: Iterable[dict[str, object]]) -> str:
    """
    聚合验证检查状态
    """
    return "FAIL" if any(result.get("status") == "FAIL" for result in results) else "PASS"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _reject_unsafe_output_dir(path: Path) -> None:
    resolved_path = path.resolve()
    repo_root = _repo_root().resolve()
    forbidden_paths = {
        repo_root,
        repo_root.parent.resolve(),
        Path.cwd().resolve(),
        Path.home().resolve(),
    }
    if resolved_path.anchor:
        forbidden_paths.add(Path(resolved_path.anchor).resolve())
    raw_roots = {repo_root / "data" / "raw"}
    configured_raw_root = os.getenv("ONN_DATASET_ROOT")
    if configured_raw_root:
        raw_roots.add(Path(configured_raw_root).resolve())
    targets_raw_data = any(
        resolved_path == raw_root
        or raw_root in resolved_path.parents
        or resolved_path in raw_root.parents
        for raw_root in raw_roots
    )
    if (
        resolved_path in forbidden_paths
        or resolved_path in repo_root.parents
        or targets_raw_data
    ):
        message = f"Unsafe validation output directory: {resolved_path}"
        raise ValueError(message)

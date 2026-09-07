from __future__ import annotations

from collections.abc import Iterable, Mapping
import os
from pathlib import Path
import shutil
import subprocess
import sys

_EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".pytest_cache",
        ".scratch",
        ".serena",
        ".spec-workflow",
        ".superpowers",
        "__pycache__",
        "build",
        "dist",
        "evidence",
        "reference",
    }
)


def copy_installable_project_tree(project_root: Path, destination: Path) -> None:
    """
    将发布候选复制到隔离目录并排除版本、构建与缓存产物
    """

    shutil.copytree(
        project_root,
        destination,
        ignore=shutil.ignore_patterns(
            *_EXCLUDED_DIRECTORY_NAMES,
            "*.egg-info",
            "*.pyc",
        ),
    )


def build_release(
    source: Path,
    output: Path,
    *,
    formats: Iterable[str],
) -> tuple[Path, ...]:
    """
    使用当前解释器构建指定发布格式并返回产物
    """

    command = [sys.executable, "-m", "build"]
    command.extend(f"--{release_format}" for release_format in formats)
    command.extend(("--outdir", str(output), str(source)))
    completed = subprocess.run(
        command,
        cwd=source.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    return tuple(sorted(output.iterdir()))


def install_wheel(wheel: Path, target: Path) -> None:
    """
    将 wheel 无依赖安装到临时目标目录
    """

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(target),
            str(wheel),
        ],
        cwd=target.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr


def run_isolated_python(
    script: str,
    *,
    working_directory: Path,
    environment: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    在隔离模式下运行一段 Python，并移除外部模块搜索路径
    """

    resolved_environment = dict(os.environ if environment is None else environment)
    resolved_environment.pop("PYTHONHOME", None)
    resolved_environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=working_directory,
        capture_output=True,
        text=True,
        env=resolved_environment,
        check=False,
    )

from __future__ import annotations

import ast
from pathlib import Path
import re

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_ROOT = PROJECT_ROOT / "src" / "chromatix_next"
BANNED_PHYSICAL_ABBREVIATIONS = frozenset({"asm", "sas", "abcd"})
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

RETAINED_PATH_DECISIONS = {
    "src/chromatix_next/optics/element/role.py": "contextual role module",
    "src/chromatix_next/optics/propagation/role.py": "contextual role module",
    "src/chromatix_next/optics/source/role.py": "contextual role module",
    "src/chromatix_next/optics/combination/role.py": "contextual role module",
    "src/chromatix_next/optics/detection/role.py": "contextual role module",
    "src/chromatix_next/optics/field.py": "complete domain noun",
    "src/chromatix_next/optics/grid.py": "complete domain noun",
    "src/chromatix_next/optics/medium.py": "complete domain noun",
    "src/chromatix_next/optics/surface/plane.py": "complete domain noun",
    "src/chromatix_next/optics/surface/sphere.py": "complete domain noun",
    "src/chromatix_next/optics/surface/conic.py": "complete domain noun",
    "src/chromatix_next/_numerics/complex_phase.py": "cross-cut numerical leaf",
    "src/chromatix_next/_numerics/spatial_sampling.py": (
        "cross-cut numerical leaf"
    ),
    "src/chromatix_next/_numerics/wave_number.py": "cross-cut numerical leaf",
    "src/chromatix_next/_numerics/optical_path_reference.py": (
        "cross-cut numerical leaf"
    ),
    "src/chromatix_next/_numerics/_certified_predicates.py": (
        "cross-cut numerical leaf"
    ),
    "src/chromatix_next/_tensors.py": "cohesive tensor boundary",
}


def _is_banned_token(value: str) -> bool:
    tokens = (token.lower() for token in value.split("_"))
    return any(token in BANNED_PHYSICAL_ABBREVIATIONS for token in tokens)


def _is_banned_path(path: Path) -> bool:
    parts = list(path.parts)
    if path.suffix:
        parts[-1] = path.stem
    return any(_is_banned_token(part) for part in parts)


def _candidate_identifier_values(tree: ast.AST) -> list[str]:
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            values.append(node.id)
        elif isinstance(node, ast.arg):
            values.append(node.arg)
        elif isinstance(node, ast.Attribute):
            values.append(node.attr)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            values.append(node.name)
        elif isinstance(node, ast.alias):
            values.extend(node.name.split("."))
            if node.asname is not None:
                values.append(node.asname)
        elif isinstance(node, ast.keyword) and node.arg is not None:
            values.append(node.arg)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            values.extend(node.names)
        elif isinstance(node, ast.ExceptHandler) and isinstance(node.name, str):
            values.append(node.name)
        elif isinstance(node, ast.MatchAs) and node.name is not None:
            values.append(node.name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if IDENTIFIER_PATTERN.fullmatch(node.value):
                values.append(node.value)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", None)
            if isinstance(module, str):
                values.extend(module.split("."))
    return values


def _source_naming_violations(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    return tuple(
        sorted(
            {
                value
                for value in _candidate_identifier_values(tree)
                if _is_banned_token(value)
            }
        )
    )


def _production_python_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted(PRODUCTION_ROOT.rglob("*.py"))
        if "__pycache__" not in path.parts
    )


def test_production_identifiers_and_stable_tokens_use_complete_names() -> None:
    """
    生产路径、AST 标识符与稳定字符串不得使用物理算法缩写
    """

    violations: list[str] = []
    for path in _production_python_paths():
        if _is_banned_path(path.relative_to(PRODUCTION_ROOT)):
            violations.append(path.relative_to(PROJECT_ROOT).as_posix())
        violations.extend(
            f"{path.relative_to(PROJECT_ROOT)}:{value}"
            for value in _source_naming_violations(
                path.read_text(encoding="utf-8")
            )
        )
    assert violations == []


@pytest.mark.parametrize(
    "source",
    (
        "from package import asm",
        "import package.asm",
        "import package.sas.kernel",
        "import package.abcd.compose",
        "def evaluate(scalar_asm):\n    return scalar_asm",
        "sas_kernel = object()",
        "abcd_compose_empty = 'error'",
        "__all__ = ('scalar_asm',)",
        "state = {'abcd_compose_empty': 'error'}",
    ),
)
def test_guard_rejects_representative_banned_names(source: str) -> None:
    """
    代表性的文件段、模块段、标识符与稳定错误词均被拒绝
    """

    assert _source_naming_violations(source)


@pytest.mark.parametrize(
    "source",
    (
        "def scalar_angular_spectrum(value):\n    return value",
        "def scalable_angular_spectrum(value):\n    return value",
        "def paraxial_ray_transfer(value):\n    return value",
        "cpu = cuda = fft = 'platform vocabulary'",
    ),
)
def test_guard_accepts_complete_names_and_platform_terms(source: str) -> None:
    """
    完整物理名称与约定平台术语保持可用
    """

    assert _source_naming_violations(source) == ()


@pytest.mark.parametrize(
    ("filename", "is_banned"),
    (
        ("asm.py", True),
        ("scalar_asm.py", True),
        ("sas_kernel.py", True),
        ("abcd_compose.py", True),
        ("scalar_angular_spectrum.py", False),
        ("scalable_angular_spectrum.py", False),
        ("paraxial_ray_transfer.py", False),
    ),
)
def test_guard_classifies_representative_filenames(
    filename: str,
    is_banned: bool,
) -> None:
    """
    文件名分类与标识符分类共享同一物理词边界
    """

    assert _is_banned_path(Path(filename)) is is_banned


def test_retained_paths_record_contextual_and_cohesive_decisions() -> None:
    """
    角色、完整名词、数值叶与张量边界保留原路径并记录原因
    """

    assert all(RETAINED_PATH_DECISIONS.values())
    missing = [
        relative_path
        for relative_path in RETAINED_PATH_DECISIONS
        if not (PROJECT_ROOT / relative_path).is_file()
    ]
    assert missing == []

    role_paths = {
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in _production_python_paths()
        if path.name == "role.py"
    }
    retained_role_paths = {
        path
        for path, reason in RETAINED_PATH_DECISIONS.items()
        if reason == "contextual role module"
    }
    assert role_paths == retained_role_paths

from __future__ import annotations

import ast
from pathlib import Path


TESTS = Path(__file__).parents[1]


def test_test_cases_import_only_dedicated_support_modules() -> None:
    """
    Keep reusable evidence builders independent of test-case collection.
    """

    imports: list[str] = []
    for path in sorted(TESTS.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            imported = []
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            if any(
                any(
                    part.startswith("test_")
                    for part in module.split(".")
                )
                for module in imported
            ):
                imports.append(
                    f"{path.relative_to(TESTS).as_posix()}:{node.lineno}"
                )

    assert imports == []

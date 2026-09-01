from __future__ import annotations

import ast
from pathlib import Path


def _imports(source: str) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    return imported


def test_production_debye_realizations_depend_on_torch_not_numpy() -> None:
    """
    Keep FFT and CZT production mathematics entirely in Torch.
    """

    field_root = (
        Path(__file__).parents[2]
        / "src"
        / "metacraft"
        / "field"
    )
    imports = {
        path.name: _imports(path.read_text(encoding="utf-8"))
        for path in field_root.glob("*debye*.py")
    }

    assert "fast_debye.py" in imports
    assert "direct_debye.py" not in imports
    for name, imported in imports.items():
        forbidden = {
            module
            for module in imported
            if module.split(".", maxsplit=1)[0] in {"numpy", "scipy"}
        }
        assert not forbidden, f"{name}: {sorted(forbidden)}"


def test_fast_debye_has_no_direct_quadrature_dependency() -> None:
    """
    Let qualification compare realizations without coupling their kernels.
    """

    source = (
        Path(__file__).parents[2]
        / "src"
        / "metacraft"
        / "field"
        / "fast_debye.py"
    ).read_text(encoding="utf-8")

    assert not any(
        imported.endswith("direct_debye")
        for imported in _imports(source)
    )


def test_qualification_uses_analytic_facts_without_direct_quadrature() -> None:
    """
    Keep reference comparison at one seam while both kernels stay independent.
    """

    source = (
        Path(__file__).parents[2]
        / "src"
        / "metacraft"
        / "field"
        / "debye_qualification.py"
    ).read_text(encoding="utf-8")
    imported = _imports(source)

    local_imports = {
        module.rsplit(".", maxsplit=1)[-1] for module in imported
    }
    assert "fast_debye" in local_imports
    assert "direct_debye" not in local_imports

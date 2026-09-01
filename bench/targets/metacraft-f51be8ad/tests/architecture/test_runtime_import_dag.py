from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "src" / "metacraft"
EXAMPLES = ROOT / "examples"


@dataclass(frozen=True, slots=True)
class _ImportEdge:
    source: str
    target: str
    path: Path
    line: int


def _module_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in SOURCE.rglob("*.py"):
        parts = list(path.relative_to(ROOT / "src").with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        paths[".".join(parts)] = path
    return paths


def _example_module_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in EXAMPLES.rglob("*.py"):
        parts = list(path.relative_to(ROOT).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        paths[".".join(parts)] = path
    return paths


def _type_checking_bindings(tree: ast.Module) -> frozenset[str]:
    canonical: dict[int, str] = {}
    for statement in tree.body:
        if (
            isinstance(statement, ast.ImportFrom)
            and statement.level == 0
            and statement.module == "typing"
        ):
            for alias in statement.names:
                if alias.name == "TYPE_CHECKING" and alias.asname is None:
                    canonical[id(alias)] = "TYPE_CHECKING"
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name == "typing" and alias.asname is None:
                    canonical[id(alias)] = "typing"

    rebound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.alias) and id(node) not in canonical:
            rebound.add(node.asname or node.name.split(".", 1)[0])
        elif isinstance(node, ast.Name) and isinstance(
            node.ctx,
            (ast.Store, ast.Del),
        ):
            rebound.add(node.id)
        elif isinstance(node, ast.arg):
            rebound.add(node.arg)
        elif isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            rebound.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name is not None:
            rebound.add(node.name)

    return frozenset(set(canonical.values()) - rebound)


def _is_type_checking_guard(
    node: ast.AST,
    bindings: frozenset[str],
) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "TYPE_CHECKING" and node.id in bindings
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "TYPE_CHECKING"
        and isinstance(node.value, ast.Name)
        and node.value.id == "typing"
        and node.value.id in bindings
    )


def _import_targets(
    node: ast.Import | ast.ImportFrom,
    *,
    module: str,
    is_package: bool,
    modules: set[str],
) -> tuple[str, ...]:
    targets: list[str] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            candidate = alias.name
            while candidate and candidate not in modules:
                candidate = candidate.rpartition(".")[0]
            if candidate in modules:
                targets.append(candidate)
        return tuple(targets)

    if node.level:
        package = module.split(".") if is_package else module.split(".")[:-1]
        anchor = package[: len(package) - (node.level - 1)]
        suffix = [] if node.module is None else node.module.split(".")
        base = ".".join((*anchor, *suffix))
    else:
        base = node.module or ""
    if base in modules and not (
        node.module is None and base == module
    ):
        targets.append(base)
    for alias in node.names:
        candidate = f"{base}.{alias.name}" if base else alias.name
        if candidate in modules:
            targets.append(candidate)
    return tuple(targets)


def _runtime_edges(
    source: str,
    *,
    module: str,
    path: Path,
    is_package: bool,
    modules: set[str],
) -> tuple[_ImportEdge, ...]:
    edges: list[_ImportEdge] = []
    tree = ast.parse(source)
    bindings = _type_checking_bindings(tree)

    class Visitor(ast.NodeVisitor):
        def visit_If(self, node: ast.If) -> None:
            if _is_type_checking_guard(node.test, bindings):
                for statement in node.orelse:
                    self.visit(statement)
                return
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:
            self._remember(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            self._remember(node)

        def _remember(
            self,
            node: ast.Import | ast.ImportFrom,
        ) -> None:
            for target in _import_targets(
                node,
                module=module,
                is_package=is_package,
                modules=modules,
            ):
                edges.append(
                    _ImportEdge(
                        source=module,
                        target=target,
                        path=path,
                        line=node.lineno,
                    )
                )

    Visitor().visit(tree)
    return tuple(edges)


def _runtime_graph() -> tuple[
    dict[str, set[str]],
    tuple[_ImportEdge, ...],
]:
    paths = _module_paths()
    modules = set(paths)
    edges = tuple(
        edge
        for module, path in paths.items()
        for edge in _runtime_edges(
            path.read_text(encoding="utf-8-sig"),
            module=module,
            path=path,
            is_package=path.name == "__init__.py",
            modules=modules,
        )
    )
    graph = {module: set() for module in modules}
    for edge in edges:
        graph[edge.source].add(edge.target)
    return graph, edges


def _examples_runtime_graph() -> tuple[
    dict[str, set[str]],
    tuple[_ImportEdge, ...],
]:
    paths = _example_module_paths()
    modules = set(paths)
    edges = tuple(
        edge
        for module, path in paths.items()
        for edge in _runtime_edges(
            path.read_text(encoding="utf-8-sig"),
            module=module,
            path=path,
            is_package=path.name == "__init__.py",
            modules=modules,
        )
    )
    graph = {module: set() for module in modules}
    for edge in edges:
        graph[edge.source].add(edge.target)
    return graph, edges


def _strong_components(graph: dict[str, set[str]]) -> tuple[set[str], ...]:
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    active: set[str] = set()
    components: list[set[str]] = []

    def visit(module: str) -> None:
        nonlocal index
        indices[module] = index
        lowlinks[module] = index
        index += 1
        stack.append(module)
        active.add(module)
        for target in sorted(graph[module]):
            if target not in indices:
                visit(target)
                lowlinks[module] = min(lowlinks[module], lowlinks[target])
            elif target in active:
                lowlinks[module] = min(lowlinks[module], indices[target])
        if lowlinks[module] != indices[module]:
            return
        component: set[str] = set()
        while True:
            target = stack.pop()
            active.remove(target)
            component.add(target)
            if target == module:
                break
        components.append(component)

    for module in sorted(graph):
        if module not in indices:
            visit(module)
    return tuple(components)


def _cycle_report(
    components: tuple[set[str], ...],
    edges: tuple[_ImportEdge, ...],
) -> str:
    sections = []
    for component in components:
        internal = tuple(
            edge
            for edge in edges
            if edge.source in component and edge.target in component
        )
        lines = [f"SCC: {', '.join(sorted(component))}"]
        lines.extend(
            (
                f"  {edge.source} -> {edge.target} "
                f"({edge.path.relative_to(ROOT)}:{edge.line})"
            )
            for edge in sorted(
                internal,
                key=lambda item: (
                    item.source,
                    item.target,
                    str(item.path),
                    item.line,
                ),
            )
        )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def _cyclic_components(
    graph: dict[str, set[str]],
) -> tuple[set[str], ...]:
    return tuple(
        component
        for component in _strong_components(graph)
        if len(component) > 1
        or any(module in graph[module] for module in component)
    )


def test_runtime_import_graph_is_a_dag_without_an_allowlist() -> None:
    graph, edges = _runtime_graph()
    cycles = _cyclic_components(graph)

    assert not cycles, "runtime import cycles:\n" + _cycle_report(cycles, edges)


def test_external_examples_import_graph_is_a_dag_without_an_allowlist() -> None:
    graph, edges = _examples_runtime_graph()
    cycles = _cyclic_components(graph)

    assert not cycles, "example import cycles:\n" + _cycle_report(cycles, edges)


def test_runtime_graph_counts_local_imports_and_excludes_type_checking() -> None:
    modules = {
        "metacraft.sample",
        "metacraft.runtime_target",
        "metacraft.type_target",
        "metacraft.qualified_type_target",
    }
    source = """
import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .type_target import TypeOnly

if typing.TYPE_CHECKING:
    from .qualified_type_target import QualifiedTypeOnly

def load() -> None:
    from .runtime_target import RuntimeValue
"""

    edges = _runtime_edges(
        source,
        module="metacraft.sample",
        path=Path("sample.py"),
        is_package=False,
        modules=modules,
    )

    assert {edge.target for edge in edges} == {
        "metacraft.runtime_target"
    }


def test_runtime_graph_keeps_and_rejects_one_self_import() -> None:
    module = "metacraft.sample"
    edges = _runtime_edges(
        f"import {module}",
        module=module,
        path=Path("sample.py"),
        is_package=False,
        modules={module},
    )
    graph = {module: {edge.target for edge in edges}}

    assert tuple(edge.target for edge in edges) == (module,)
    assert _cyclic_components(graph) == ({module},)

    child = f"{module}.child"
    package_edges = _runtime_edges(
        "from . import child",
        module=module,
        path=Path("__init__.py"),
        is_package=True,
        modules={module, child},
    )
    assert tuple(edge.target for edge in package_edges) == (child,)


def test_runtime_graph_counts_a_rebound_type_checking_import() -> None:
    modules = {
        "metacraft.sample",
        "metacraft.runtime_target",
    }
    source = """
from typing import TYPE_CHECKING

TYPE_CHECKING = True
if TYPE_CHECKING:
    from .runtime_target import RuntimeValue
"""

    edges = _runtime_edges(
        source,
        module="metacraft.sample",
        path=Path("sample.py"),
        is_package=False,
        modules=modules,
    )

    assert {edge.target for edge in edges} == {
        "metacraft.runtime_target"
    }


def test_generic_values_import_no_aim_or_platform_consumer() -> None:
    graph, _edges = _runtime_graph()

    for module in (
        "metacraft.science.study",
        "metacraft.science.compiler",
    ):
        assert not {
            target
            for target in graph[module]
            if target.startswith("metacraft.science.metalens")
        }
    assert {
        target
        for target in graph["metacraft.science.conduct"]
        if target.startswith("metacraft.science.metalens")
    } == {
        "metacraft.science.metalens.checkpoint",
        "metacraft.science.metalens.consultation",
        "metacraft.science.metalens.conduct",
            "metacraft.science.metalens.evidence_adapter",
        "metacraft.science.metalens.result",
    }
    assert not {
        target
        for target in graph["metacraft.science.relationships"]
        if target.startswith("metacraft.science.metalens")
    }
    assert (
        "metacraft.workstation.windows"
        not in graph["metacraft.workstation.model"]
    )


def test_materials_import_no_application_science_or_solver_consumer() -> None:
    """
    Keep project material selection below each consuming layer.
    """

    graph, _edges = _runtime_graph()
    for module, targets in graph.items():
        if not module.startswith("metacraft.materials"):
            continue
        assert not {
            target
            for target in targets
            if target.startswith(
                (
                    "metacraft._local",
                    "metacraft.local",
                    "metacraft.science",
                    "metacraft.solvers",
                )
            )
        }, module


def test_science_imports_no_lumerical_product_module() -> None:
    """
    Keep Lumerical verification below solver-neutral scientific meaning.
    """

    graph, _edges = _runtime_graph()
    for module, targets in graph.items():
        if not module.startswith("metacraft.science"):
            continue
        assert not {
            target
            for target in targets
            if target.startswith(
                "metacraft.solvers.lumerical_fdtd"
            )
        }, module

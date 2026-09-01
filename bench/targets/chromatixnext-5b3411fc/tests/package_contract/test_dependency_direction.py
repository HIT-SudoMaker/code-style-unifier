from __future__ import annotations

from pathlib import Path

from tests.architecture._python_import_facts import read_python_imports

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "src" / "chromatix_next"


def _production_import_graph(
    *,
    is_runtime_only: bool,
) -> dict[str, frozenset[str]]:
    facts = tuple(
        read_python_imports(module_path, PACKAGE_ROOT.parent)
        for module_path in sorted(PACKAGE_ROOT.rglob("*.py"))
    )
    module_names = frozenset(fact.module_name for fact in facts)
    graph: dict[str, frozenset[str]] = {}
    for fact in facts:
        dependencies: set[str] = set()
        imported_targets = (
            fact.runtime_imported_targets
            if is_runtime_only
            else fact.imported_targets
        )
        for imported_target in imported_targets:
            target_parts = imported_target.split(".")
            dependency = next(
                (
                    ".".join(target_parts[:part_count])
                    for part_count in range(len(target_parts), 0, -1)
                    if ".".join(target_parts[:part_count]) in module_names
                ),
                None,
            )
            if dependency is not None and dependency != fact.module_name:
                dependencies.add(dependency)
        graph[fact.module_name] = frozenset(dependencies)
    return graph


def _has_forbidden_import(
    module_paths: list[Path],
    forbidden: tuple[str, ...],
) -> bool:
    for module_path in module_paths:
        imports = read_python_imports(module_path, PACKAGE_ROOT.parent)
        for imported_module in imports.imported_modules:
            if any(
                imported_module == prefix
                or imported_module.startswith(prefix + ".")
                for prefix in forbidden
            ):
                return True
    return False


def test_production_dependencies_flow_workstation_to_optics_to_numerics() -> None:
    """
    生产层依赖单向无环
    """

    numerical_modules = sorted((PACKAGE_ROOT / "_numerics").rglob("*.py"))
    optical_modules = sorted((PACKAGE_ROOT / "optics").rglob("*.py"))
    assert numerical_modules
    assert optical_modules
    assert not _has_forbidden_import(
        numerical_modules,
        (
            "chromatix_next.optics",
            "chromatix_next.workstation",
            "chromatix_next._state_installation",
        ),
    )
    assert not _has_forbidden_import(
        optical_modules,
        (
            "chromatix_next.workstation",
            "chromatix_next._state_installation",
        ),
    )


def test_complete_production_import_graph_is_acyclic() -> None:
    """
    完整生产导入图可按依赖顺序耗尽
    """

    remaining_dependencies = {
        module_name: set(dependencies)
        for module_name, dependencies in _production_import_graph(
            is_runtime_only=True,
        ).items()
    }
    while remaining_dependencies:
        ready_modules = frozenset(
            module_name
            for module_name, dependencies in remaining_dependencies.items()
            if not dependencies
        )
        assert ready_modules, (
            "production import cycle: "
            f"{sorted(remaining_dependencies)}"
        )
        for module_name in ready_modules:
            del remaining_dependencies[module_name]
        for dependencies in remaining_dependencies.values():
            dependencies.difference_update(ready_modules)


def test_static_type_cycle_is_visible_but_absent_from_runtime_graph() -> None:
    """
    Assembly replay 的类型依赖保持可见且不污染完整运行导入图
    """

    assembly = "chromatix_next.optics.assembly"
    replay = "chromatix_next.optics._assembly_replay"
    static_graph = _production_import_graph(is_runtime_only=False)
    runtime_graph = _production_import_graph(is_runtime_only=True)
    assert replay in static_graph[assembly]
    assert assembly in static_graph[replay]
    assert replay in runtime_graph[assembly]
    assert assembly not in runtime_graph[replay]


def test_production_package_has_no_fourth_public_seam() -> None:
    """
    根包不发布额外框架、运行时或治理入口
    """

    root_init = (PACKAGE_ROOT / "__init__.py").read_text(encoding="utf-8")
    forbidden_names = (
        "Runtime",
        "Engine",
        "Graph",
        "Optimizer",
        "Registry",
        "Manager",
    )
    assert all(name not in root_init for name in forbidden_names)

from __future__ import annotations

import ast
from pathlib import Path
import re

from tests.architecture._python_import_facts import (
    inspect_python_imports,
    read_python_imports,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


PACKAGE = PROJECT_ROOT / "src" / "chromatix_next"


OPTICS = PACKAGE / "optics"


_ASSEMBLY_RUNTIME_ALLOWED_IMPORTERS = {
    "chromatix_next.optics.assembly",  # 定义本身
    "chromatix_next.optics",  # 公共再导出
    "chromatix_next.workstation",  # 唯一重放驱动运行时
    "chromatix_next.optics._assembly_replay",  # 静态类型提示（TYPE_CHECKING）
}


def _all_production_paths() -> tuple[Path, ...]:
    return tuple(PACKAGE.rglob("*.py"))


def _tree(path: Path) -> ast.Module:
    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def _is_assembly_target(targets: frozenset[str]) -> bool:
    return any(
        target == "chromatix_next.optics.assembly"
        or target.startswith("chromatix_next.optics.assembly.")
        or target in {
            "chromatix_next.optics.Assembly",
            "chromatix_next.optics.*",
        }
        for target in targets
    )


def _is_assembly_constructed(path: Path) -> bool:
    # 是否在生产中调用 Assembly() 构造器（应仅在测试/示例出现，生产中为零）
    tree = _tree(path)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Assembly"
        ):
            return True
    return False


def test_assembly_class_is_defined_in_exactly_one_module() -> None:
    """
    Assembly 类恰在一个生产模块中定义（optics/assembly.py）
    """

    definers: list[str] = []
    for path in _all_production_paths():
        tree = _tree(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Assembly":
                definers.append(
                    read_python_imports(path, PACKAGE.parent).module_name
                )
    assert definers == ["chromatix_next.optics.assembly"], definers


def test_assembly_is_imported_only_by_the_single_runtime_owner_set() -> None:
    """
    Assembly 只被合法运行时相关模块导入：公共再导出、唯一重放驱动、静态类型提示

    任何其它生产模块导入 Assembly 即构成嵌套 Assembly 运行时或第二条执行接缝。
    """

    importers: set[str] = set()
    for path in _all_production_paths():
        facts = read_python_imports(path, PACKAGE.parent)
        if _is_assembly_target(
            facts.imported_modules | facts.imported_targets
        ):
            importers.add(facts.module_name)
    assert importers <= _ASSEMBLY_RUNTIME_ALLOWED_IMPORTERS, (
        "Assembly 被允许集合之外的生产模块导入（嵌套运行时风险）："
        + ", ".join(sorted(importers - _ASSEMBLY_RUNTIME_ALLOWED_IMPORTERS))
    )


def test_no_production_module_constructs_an_assembly() -> None:
    """
    生产模块不构造 Assembly 实例

    Assembly 只由研究者代码（测试/示例）构造；生产中构造会形成嵌套
    运行时或第二个被驱动根。
    """

    offenders = [
        read_python_imports(path, PACKAGE.parent).module_name
        for path in _all_production_paths()
        if _is_assembly_constructed(path)
    ]
    assert not offenders, (
        "生产模块构造了 Assembly()，构成嵌套运行时：" + ", ".join(offenders)
    )


def test_assembly_topology_layer_imports_no_optical_physics() -> None:
    """
    Assembly 拓扑层（assembly.py、_assembly_facts.py）不导入任何光学物理实现

    拓扑层只持有作者语法、拓扑事实与重放编排；物理值类型（OpticalField/Intensity/
    RayBundle/SpatialGrid）作为类型与容器出现，但 element/propagation/combination/
    detection/source 的物理实现与 _numerics 数值支撑不得进入拓扑层。
    Source、Wave 与 Ray
    在拓扑层操作不触及光学方程的独立结构性证据。
    """

    physics_prefixes = (
        "chromatix_next.optics.source.",
        "chromatix_next.optics.element.",
        "chromatix_next.optics.propagation.",
        "chromatix_next.optics.combination.",
        "chromatix_next.optics.detection.",
        "chromatix_next._numerics",
    )
    topology_modules = (
        OPTICS / "assembly.py",
        OPTICS / "_assembly_facts.py",
    )
    offenders: list[str] = []
    for path in topology_modules:
        facts = read_python_imports(path, PACKAGE.parent)
        for imported in (facts.imported_modules | facts.imported_targets):
            if imported.startswith(physics_prefixes):
                offenders.append(
                    f"{path.name} 导入物理实现 {imported}"
                )
    assert not offenders, (
        "拓扑层导入了光学物理实现（方程漂移风险）：" + ", ".join(offenders)
    )


def test_assembly_facts_module_has_no_torch_dependency() -> None:
    """
    拓扑事实模块不依赖 torch：纯拓扑事实判定，不含任何张量数值
    """

    facts = read_python_imports(OPTICS / "_assembly_facts.py", PACKAGE.parent)
    imports = facts.imported_modules | facts.imported_targets
    assert not any(
        module == "torch" or module.startswith("torch.") for module in imports
    ), imports

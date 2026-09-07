
from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, TypeGuard

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src" / "chromatix_next"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".superpowers" / "sdd" / "final-seal"
PACKAGE_PREFIX = "chromatix_next"
SCHEMA_VERSION = 1


@dataclass(slots=True)
class _ModuleInfo:
    # 单一生产模块的 AST 事实：本地定义、外部导入与可选 __all__ 在同一次遍历收集

    dotted: str
    relative_path: str
    tree: ast.Module
    local_defs: dict[str, ast.stmt]
    imported_names: dict[str, str]
    all_names: tuple[str, ...] | None


def _dotted_module_name(path: Path) -> str:
    # 把 src/chromatix_next/.../foo.py 折算为点号模块名；__init__.py 退化为包名
    relative = path.relative_to(SRC_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join((PACKAGE_PREFIX, *parts))


def _extract_all_literal(node: ast.expr) -> tuple[str, ...] | None:
    # 从 __all__ = [...] 字面量按声明顺序抽出字符串条目；非列表/元组返回 None
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    names: list[str] = []
    for element in node.elts:
        if (
            isinstance(element, ast.Constant)
            and isinstance(element.value, str)
        ):
            names.append(element.value)
    return tuple(names) if names else None


def _assign_target_name(node: ast.Assign) -> str | None:
    # 对单目标 Name = ... 返回该名字；其他形态返回 None
    if len(node.targets) != 1:
        return None
    target = node.targets[0]
    if isinstance(target, ast.Name):
        return target.id
    return None


def _resolve_relative_import(
    anchor_parts: Sequence[str],
    node: ast.ImportFrom,
) -> str | None:
    # 把相对导入解析为绝对模块点号名；绝对导入直接返回 node.module
    level = node.level or 0
    if level == 0:
        return node.module
    drop = level - 1
    if drop >= len(anchor_parts):
        return None
    base = list(anchor_parts[: len(anchor_parts) - drop])
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base) if base else None


def _is_annotated_name_assignment(
    statement: ast.stmt,
) -> TypeGuard[ast.AnnAssign]:
    # AnnAssign 且目标为裸 Name 的统一判定，避免多处重复两行 isinstance 链
    return (
        isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
    )


def _parse_module(path: Path) -> _ModuleInfo:
    # 解析单个模块并收集本地定义、外部导入与 __all__，供后续跨模块符号解析
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    local_defs: dict[str, ast.stmt] = {}
    imported_names: dict[str, str] = {}
    all_names: tuple[str, ...] | None = None
    dotted = _dotted_module_name(path)
    anchor_parts = dotted.split(".")

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            local_defs[node.name] = node
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local_defs[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    all_names = _extract_all_literal(node.value)
            target_name = _assign_target_name(node)
            if target_name is not None:
                local_defs[target_name] = node
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                local_defs[node.target.id] = node
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                imported_names[bound] = alias.name
        elif isinstance(node, ast.ImportFrom):
            origin = _resolve_relative_import(anchor_parts, node)
            if origin is None:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname or alias.name
                imported_names[bound] = (
                    f"{origin}.{alias.name}" if alias.name else origin
                )

    relative = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    return _ModuleInfo(
        dotted=dotted,
        relative_path=relative,
        tree=tree,
        local_defs=local_defs,
        imported_names=imported_names,
        all_names=all_names,
    )


def _iter_source_modules() -> Iterator[Path]:
    # 遍历 src/chromatix_next 下所有 .py 文件（含 __init__），按路径排序保证确定性
    yield from sorted(SRC_ROOT.rglob("*.py"))


def _build_index() -> dict[str, _ModuleInfo]:
    # 构建点号模块名到 _ModuleInfo 的索引
    index: dict[str, _ModuleInfo] = {}
    for path in _iter_source_modules():
        info = _parse_module(path)
        index[info.dotted] = info
    return index



def _resolve_defining_node(
    index: dict[str, _ModuleInfo],
    module: _ModuleInfo,
    name: str,
) -> tuple[str, ast.stmt | None]:
    # 返回 (定义模块点号名, 定义 AST 节点)；找不到节点时定义节点为 None
    if name in module.local_defs:
        return module.dotted, module.local_defs[name]
    if name in module.imported_names:
        origin = module.imported_names[name]
        origin_module, _, origin_attr = origin.rpartition(".")
        if origin_attr and origin_module in index:
            return _resolve_defining_node(index, index[origin_module], origin_attr)
        return origin_module or module.dotted, None
    return module.dotted, None


def _signature_source(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    # 把函数节点重放为 (args) -> return 形式，不含函数体
    args = ast.unparse(node.args)
    if node.returns is not None:
        return f"({args}) -> {ast.unparse(node.returns)}"
    return f"({args})"


def _decorator_names(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, ...]:
    # 抽取装饰器简化点号名，用于识别 dataclass / property / override
    names: list[str] = []
    for decorator in node.decorator_list:
        text = ast.unparse(decorator)
        names.append(text.split("(", 1)[0].strip())
    return tuple(names)


def _base_names(node: ast.ClassDef) -> tuple[str, ...]:
    # 抽取基类简化名字，用于识别 Enum / NamedTuple 等构造
    names: list[str] = []
    for base in node.bases:
        text = ast.unparse(base)
        names.append(text.rsplit(".", 1)[-1])
    return tuple(names)


def _is_enum_class(node: ast.ClassDef) -> bool:
    return "Enum" in _base_names(node) or "Flag" in _base_names(node)


def _is_namedtuple_class(node: ast.ClassDef) -> bool:
    return "NamedTuple" in _base_names(node)


def _is_dataclass(node: ast.ClassDef) -> bool:
    return "dataclass" in _decorator_names(node)


def _enum_members(node: ast.ClassDef) -> list[dict[str, str]]:
    # 按声明顺序抽取 Enum 成员 (name, value)
    members: list[dict[str, str]] = []
    for statement in node.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    members.append(
                        {
                            "name": target.id,
                            "value": ast.unparse(statement.value),
                        }
                    )
    return members


def _annotated_fields(statement: ast.AnnAssign) -> dict[str, Any] | None:
    # 把单条 AnnAssign 折算为字段记录；不含 has_default 时由调用方补齐
    target = statement.target
    if not isinstance(target, ast.Name):
        return None
    annotation = (
        ast.unparse(statement.annotation)
        if statement.annotation is not None
        else ""
    )
    return {"name": target.id, "annotation": annotation}


def _dataclass_fields(node: ast.ClassDef) -> list[dict[str, Any]]:
    # 从 dataclass 类体按声明顺序抽出带标注字段
    fields: list[dict[str, Any]] = []
    for statement in node.body:
        if not _is_annotated_name_assignment(statement):
            continue
        record = _annotated_fields(statement)
        if record is None:
            continue
        record["has_default"] = statement.value is not None
        fields.append(record)
    return fields


def _namedtuple_fields(node: ast.ClassDef) -> list[dict[str, str]]:
    # 从 NamedTuple 类体按声明顺序抽出字段
    fields: list[dict[str, str]] = []
    for statement in node.body:
        if not _is_annotated_name_assignment(statement):
            continue
        record = _annotated_fields(statement)
        if record is not None:
            fields.append(record)
    return fields


def _public_members(node: ast.ClassDef) -> list[dict[str, Any]]:
    # 按声明顺序抽取类体内项目自定义的公开方法与属性（不含下划线开头成员）
    members: list[dict[str, Any]] = []
    for statement in node.body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = statement.name
            decorators = _decorator_names(statement)
            if name.startswith("_") and name != "__init__":
                continue
            kind = "method"
            if "property" in decorators:
                kind = "property"
            elif name == "__init__":
                kind = "constructor"
            members.append(
                {
                    "name": name,
                    "kind": kind,
                    "signature": _signature_source(statement),
                }
            )
        elif _is_annotated_name_assignment(statement):
            record = _annotated_fields(statement)
            if record is None:
                continue
            if record["name"].startswith("_"):
                continue
            record["kind"] = "annotated_attribute"
            members.append(record)
    return members


def _classify_class_node(node: ast.ClassDef) -> str:
    if _is_namedtuple_class(node):
        return "namedtuple_class"
    if _is_enum_class(node):
        return "enum_class"
    if _is_dataclass(node):
        return "dataclass_class"
    return "class"


def _build_export_entry(
    index: dict[str, _ModuleInfo],
    module: _ModuleInfo,
    name: str,
) -> dict[str, Any]:
    # 为单个 __all__ 条目构造规范化的导出记录
    defining_module, defining_node = _resolve_defining_node(index, module, name)
    qualified_name = f"{defining_module}.{name}"
    entry: dict[str, Any] = {
        "name": name,
        "defining_module": defining_module,
        "qualified_name": qualified_name,
    }
    if defining_node is None:
        entry["kind"] = "external"
        return entry
    if isinstance(defining_node, ast.ClassDef):
        _populate_class_entry(entry, defining_node)
    elif isinstance(defining_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        entry["kind"] = "function"
        entry["signature"] = _signature_source(defining_node)
    elif isinstance(defining_node, ast.Assign):
        entry["kind"] = "assignment"
        entry["value"] = ast.unparse(defining_node.value)
    elif isinstance(defining_node, ast.AnnAssign):
        entry["kind"] = "annotated_assignment"
        if defining_node.annotation is not None:
            entry["annotation"] = ast.unparse(defining_node.annotation)
    else:
        entry["kind"] = "other"
    return entry


def _populate_class_entry(entry: dict[str, Any], node: ast.ClassDef) -> None:
    # 把 ClassDef 的事实填入已存在的导出条目
    entry["kind"] = _classify_class_node(node)
    constructor = next(
        (
            statement
            for statement in node.body
            if isinstance(statement, ast.FunctionDef)
            and statement.name == "__init__"
        ),
        None,
    )
    entry["constructor_signature"] = (
        _signature_source(constructor) if constructor is not None else None
    )
    if entry["kind"] == "enum_class":
        entry["enum_members"] = _enum_members(node)
    elif entry["kind"] == "dataclass_class":
        entry["fields"] = _dataclass_fields(node)
    elif entry["kind"] == "namedtuple_class":
        entry["fields"] = _namedtuple_fields(node)
    entry["public_members"] = _public_members(node)


def _build_module_entry(
    index: dict[str, _ModuleInfo],
    module: _ModuleInfo,
) -> dict[str, Any]:
    # 构造单个带 __all__ 模块的导出快照（按 __all__ 声明顺序）
    assert module.all_names is not None
    exports = [
        _build_export_entry(index, module, name) for name in module.all_names
    ]
    return {
        "module": module.dotted,
        "source_path": module.relative_path,
        "all": list(module.all_names),
        "exports": exports,
    }


def _modules_with_all(index: dict[str, _ModuleInfo]) -> list[_ModuleInfo]:
    # 按模块点号名排序返回带显式 __all__ 的模块
    return sorted(
        (info for info in index.values() if info.all_names is not None),
        key=lambda info: info.dotted,
    )


_TYPE_TOKEN_DELIMITERS = "=:,|[]().<>'\"-"


def _build_project_type_names(index: dict[str, _ModuleInfo]) -> set[str]:
    names: set[str] = set()
    for module in index.values():
        for node in ast.walk(module.tree):
            if isinstance(node, ast.ClassDef):
                names.add(node.name)
    return names


def _collect_project_type_names(
    entries: Iterable[dict[str, Any]],
    project_types: set[str],
) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def _scan(text: str) -> None:
        cleaned = text
        for delim in _TYPE_TOKEN_DELIMITERS:
            cleaned = cleaned.replace(delim, " ")
        for chunk in cleaned.split():
            if chunk in project_types and chunk not in seen:
                seen.add(chunk)
                found.append(chunk)

    for entry in entries:
        for key in ("signature", "constructor_signature", "annotation", "value"):
            value = entry.get(key)
            if isinstance(value, str):
                _scan(value)
        for member in entry.get("public_members", []) or []:
            for key in ("signature", "annotation"):
                if isinstance(member.get(key), str):
                    _scan(member[key])
        for field in entry.get("fields", []) or []:
            annotation = field.get("annotation")
            if isinstance(annotation, str):
                _scan(annotation)
    return found


def _camel_to_snake(name: str) -> str:
    # 把 CamelCase 折算为 snake_case，与项目命名约定一致
    result: list[str] = []
    for index, character in enumerate(name):
        if character.isupper() and index and not name[index - 1].isupper():
            result.append("_")
        result.append(character.lower())
    return "".join(result)


def _function_component_pairs(role_all: Sequence[str]) -> list[list[str]]:
    # 在单一 role 包内匹配 lower + Upper 的函数/组件对；无配对的 lower 单列
    lower_names = {name for name in role_all if name.islower()}
    upper_names = {
        name for name in role_all if name and name[0].isupper()
    }
    pairs: list[list[str]] = []
    consumed_lower: set[str] = set()
    for upper in sorted(upper_names):
        snake = _camel_to_snake(upper)
        if snake in lower_names:
            pairs.append([snake, upper])
            consumed_lower.add(snake)
    for lower in sorted(lower_names - consumed_lower):
        pairs.append([lower])
    return pairs


def _role_clean_names(role_module: _ModuleInfo | None, marker: str) -> list[str]:
    # 抽出某 role 包除 marker 与诊断副产物外的 __all__ 条目
    if role_module is None or role_module.all_names is None:
        return []
    return [
        name
        for name in role_module.all_names
        if name != marker and not name.endswith("Diagnostic")
    ]


ROLE_PACKAGE_NAMES = (
    "source",
    "element",
    "propagation",
    "combination",
    "detection",
)


def _build_invariants(
    index: dict[str, _ModuleInfo],
    module_entries: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    # 聚合公共面不变量：角色、源、26 对、30 动作、3 Surface、近轴光线传递、错误类
    top_level = index.get(PACKAGE_PREFIX)
    top_all = (
        list(top_level.all_names)
        if top_level and top_level.all_names
        else []
    )

    role_packages: dict[str, list[str]] = {}
    pairs_by_role: dict[str, list[list[str]]] = {}
    pair_count = 0
    for role in ROLE_PACKAGE_NAMES:
        role_module = index.get(f"{PACKAGE_PREFIX}.optics.{role}")
        role_all = _role_clean_names(role_module, role.capitalize())
        role_packages[role] = role_all
        pairs = _function_component_pairs(role_all)
        pairs_by_role[role] = pairs
        pair_count += sum(1 for pair in pairs if len(pair) == 2)

    sources = role_packages.get("source", [])
    source_count = len(sources)
    surface_module = index.get(f"{PACKAGE_PREFIX}.optics.surface")
    surfaces = (
        list(surface_module.all_names)
        if surface_module and surface_module.all_names
        else []
    )
    paraxial_ray_transfer_module = index.get(
        f"{PACKAGE_PREFIX}.optics.paraxial_ray_transfer"
    )
    paraxial_ray_transfer_exports = (
        list(paraxial_ray_transfer_module.all_names)
        if paraxial_ray_transfer_module and paraxial_ray_transfer_module.all_names
        else []
    )
    errors_module = index.get(f"{PACKAGE_PREFIX}.errors")
    error_classes = (
        list(errors_module.all_names)
        if errors_module and errors_module.all_names
        else []
    )
    project_types = _build_project_type_names(index)
    all_export_entries = [
        export
        for module_entry in module_entries
        for export in module_entry["exports"]
    ]
    reachable_types = _collect_project_type_names(all_export_entries, project_types)
    optical_action_count = pair_count + source_count
    return {
        "top_level_exports": top_all,
        "top_level_count": len(top_all),
        "role_packages": list(ROLE_PACKAGE_NAMES),
        "source_exports": sources,
        "source_count": source_count,
        "function_component_pairs_by_role": pairs_by_role,
        "function_component_pair_count": pair_count,
        "optical_action_count": optical_action_count,
        "surface_exports": surfaces,
        "surface_count": len(surfaces),
        "paraxial_ray_transfer_exports": paraxial_ray_transfer_exports,
        "error_classes": error_classes,
        "project_type_names_reachable_from_public_annotations": reachable_types,
    }


def _current_head() -> str:
    # 读取当前工作树的 HEAD SHA；失败时回退到 unknown
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip()


def build_snapshot() -> dict[str, Any]:
    """
    组装完整的公共面快照字典
    """
    index = _build_index()
    module_entries = [
        _build_module_entry(index, module)
        for module in _modules_with_all(index)
    ]
    invariants = _build_invariants(index, module_entries)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_from": {
            "git_head": _current_head(),
            "tool": "tools/snapshot_public_surface.py",
            "source_root": "src/chromatix_next",
        },
        "modules": module_entries,
        "public_surface_invariants": invariants,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """
    命令行入口：构建快照并写到默认或显式指定的路径
    """
    parser = argparse.ArgumentParser(
        description=(
            "Emit a canonical AST-derived snapshot of the "
            "ChromatixNext public surface (read-only)."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Output JSON path; defaults to "
            ".superpowers/sdd/final-seal/public-surface-<head>.json"
        ),
    )
    arguments = parser.parse_args(argv)
    snapshot = build_snapshot()
    head = snapshot["generated_from"]["git_head"]
    output_path = arguments.output or (
        DEFAULT_OUTPUT_DIR / f"public-surface-{head[:7]}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Public-surface snapshot written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

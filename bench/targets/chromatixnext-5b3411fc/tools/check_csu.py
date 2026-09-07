from __future__ import annotations

import argparse
import ast
from collections import Counter
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
import tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "csu.toml"

_BANNED_COMMENT_PATTERNS = (
    re.compile(r"\bticket\b", re.IGNORECASE),
    re.compile(r"\bowner_ticket\b", re.IGNORECASE),
    re.compile(r"\bdeletion[- ]test\b", re.IGNORECASE),
    re.compile(r"\bgovernance\b", re.IGNORECASE),
    re.compile(r"\bacceptance\b", re.IGNORECASE),
    re.compile(r"\brow\s+\d+\b", re.IGNORECASE),
)

_DOCUMENT_POINTER_COMMENT_PATTERN = re.compile(
    r"^实现依据见\s*《[^》\r\n]+》(?:的\s*)?[“\"][^”\"\r\n]+[”\"]\s*条目$"
)

_COMMENT_TERMINATORS = (
    "\u3002",
    "\uff01",
    "\uff1f",
    "\uff1b",
    ".",
    "!",
    "?",
    ";",
)

_DOCUMENTED_NAME_PATTERN = re.compile(
    r"^\s+(\*{0,2}[A-Za-z_]\w*)(?:\s*\([^)]*\))?\s*:",
)

_SECTION_HEADER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z ]+:\s*$")

_GENERIC_RESULT_PATTERNS = (
    re.compile(r"该\s*Interface\s*计算或查询得到的结果"),
    re.compile(r"依照该物理作用变换后的光场"),
    re.compile(r"依照该几何或偏振作用更新后的光线束"),
    re.compile(r"按\s*Interface\s*声明顺序排列的物理结果"),
    re.compile(r"固定双精度语义下计算得到的张量结果"),
    re.compile(r"由输入采样与该作用共同确定的输出空间网格"),
    re.compile(r"按该\s*Interface\s*归一化语义得到的强度"),
    re.compile(r"输出按公开字段声明顺序排列的元组值"),
    re.compile(r"返回固定双精度语义下的物理张量"),
    re.compile(r"返回该作用定义的输出空间网格"),
    re.compile(
        r"返回\s*(?:Element|Source|Combination|Propagation)\s*组件"
        r"(?:作用后|执行后|在给定采样网格上)的物理(?:值|输出)"
    ),
)

_GENERIC_RAISES_PATTERN = re.compile(
    r"delegated validation rejects the physical input|"
    r"delegated validation rejects the input",
    re.IGNORECASE,
)

_TYPE_ONLY_RESULT_NAMES = frozenset(
    {
        "bool",
        "float",
        "int",
        "object",
        "str",
        "tensor",
        "torch.tensor",
        "torch.Tensor",
        "tuple",
        "typing.Tuple",
    }
)

_KNOWN_BUILTIN_EXCEPTION_NAMES = frozenset(
    {
        "AssertionError",
        "IndexError",
        "KeyError",
        "NotImplementedError",
        "RuntimeError",
        "TypeError",
        "ValueError",
    }
)

_SECTION_ENTRY_PATTERN = re.compile(
    r"^\s+(`{0,2}[A-Za-z_]\w*(?:\.{1}`{0,2}[A-Za-z_]\w*)?`{0,2})"
    r"(?:\s*\([^)]*\))?\s*:\s*(.*)$",
)

_VALIDATION_HELPER_PREFIXES = (
    "_as_finite",
    "_assert",
    "_check",
    "_prepare",
    "_raise_on",
    "_require",
    "_validate",
)

_MANAGED_DIRECTORY_PATHS = (
    Path("src"),
    Path("tests"),
    Path("tools"),
    Path("docs"),
)

_MANAGED_FILE_PATHS = (
    Path("AGENTS.md"),
    Path("CONTEXT.md"),
    Path("MISSION.md"),
    Path("README.md"),
    Path("MANIFEST.in"),
    Path("csu.toml"),
    Path("pyproject.toml"),
    Path("setup.py"),
)

_MANAGED_EXCLUDED_PATHS = frozenset(
    {
        Path("tests/package_contract/test_examples.py"),
    }
)

_MANAGED_IGNORED_DIRECTORY_NAMES = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
    }
)


def _managed_file_paths(project_root: Path = PROJECT_ROOT) -> tuple[Path, ...]:
    managed: set[Path] = set()
    for relative in _MANAGED_FILE_PATHS:
        path = project_root / relative
        if path.is_file():
            managed.add(path)
    for relative_root in _MANAGED_DIRECTORY_PATHS:
        root = project_root / relative_root
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(project_root)
            if relative in _MANAGED_EXCLUDED_PATHS:
                continue
            if any(
                part in _MANAGED_IGNORED_DIRECTORY_NAMES
                for part in relative.parts
            ):
                continue
            managed.add(path)
    return tuple(sorted(managed))


def _rejects_finding(finding: dict[str, object]) -> bool:
    kind = finding.get("kind")
    if kind == "hard_violation":
        return True
    if kind != "under_review":
        return False
    required_adjudication = (
        "adjudication_owner",
        "adjudication",
        "adjudication_evidence",
    )
    return not all(finding.get(name) for name in required_adjudication)


def _callable_parameter_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, ...]:
    names = [
        argument.arg
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
        if argument.arg not in {"self", "cls"}
    ]
    if node.args.vararg is not None:
        names.append(node.args.vararg.arg)
    if node.args.kwarg is not None:
        names.append(node.args.kwarg.arg)
    return tuple(names)


def _class_parameter_names(node: ast.ClassDef) -> tuple[str, ...]:
    initializer = next(
        (
            statement
            for statement in node.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            and statement.name == "__init__"
        ),
        None,
    )
    if initializer is not None:
        return _callable_parameter_names(initializer)
    return tuple(
        statement.target.id
        for statement in node.body
        if isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and not statement.target.id.startswith("_")
    )


def _expression_leaf_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Call):
        return _expression_leaf_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _target_owns_instance_state(node: ast.expr) -> bool:
    if isinstance(node, ast.Attribute):
        return isinstance(node.value, ast.Name) and node.value.id == "self"
    if isinstance(node, (ast.List, ast.Tuple)):
        return any(_target_owns_instance_state(element) for element in node.elts)
    return False


def _private_class_owns_durable_state(node: ast.ClassDef) -> bool:
    # Durable 类由实际状态形状识别，不依赖易漂移的类名清单
    if any(
        _expression_leaf_name(decorator) == "dataclass"
        for decorator in node.decorator_list
    ):
        return True
    if any(
        _expression_leaf_name(base) not in {None, "object"}
        for base in node.bases
    ):
        return True
    if any(
        isinstance(statement, (ast.AnnAssign, ast.Assign))
        for statement in node.body
    ):
        return True
    initializer = next(
        (
            statement
            for statement in node.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            and statement.name == "__init__"
        ),
        None,
    )
    if initializer is None:
        return False
    for statement in ast.walk(initializer):
        if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else (statement.target,)
            )
            if any(_target_owns_instance_state(target) for target in targets):
                return True
    return False


def _documented_names(
    docstring: str,
    section_names: tuple[str, ...],
) -> tuple[str, ...] | None:
    lines = docstring.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip() in {f"{name}:" for name in section_names}
        ),
        None,
    )
    if start is None:
        return None
    names: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped and _SECTION_HEADER_PATTERN.fullmatch(stripped):
            break
        match = _DOCUMENTED_NAME_PATTERN.match(line)
        if match is not None:
            names.append(match.group(1).lstrip("*"))
    return tuple(names)


def _section_lines(docstring: str, section_name: str) -> list[str]:
    lines = docstring.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip() == f"{section_name}:"
        ),
        None,
    )
    if start is None:
        return []
    result: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped and _SECTION_HEADER_PATTERN.fullmatch(stripped):
            break
        result.append(line)
    return result


def _section_entries(
    docstring: str,
    section_name: str,
) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    current_name: str | None = None
    current_description: list[str] = []
    for line in _section_lines(docstring, section_name):
        match = _SECTION_ENTRY_PATTERN.match(line)
        if match is not None:
            if current_name is not None:
                entries.append(
                    (
                        current_name,
                        " ".join(current_description).strip(),
                    )
                )
            current_name = match.group(1).strip("`")
            current_description = [match.group(2).strip()]
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if section_name in {"Returns", "Yields"}:
            current_description.append(stripped)
        elif current_name is not None:
            current_description.append(stripped)
    if current_name is not None:
        entries.append(
            (
                current_name,
                " ".join(current_description).strip(),
            )
        )
    elif section_name in {"Returns", "Yields"}:
        text = " ".join(
            line.strip()
            for line in _section_lines(docstring, section_name)
        )
        if text:
            entries.append(("", text))
    return tuple(entries)


def _normalized_doc_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("`", "")).strip()


def _is_semantic_description(
    text: str,
    annotation: ast.expr | None = None,
) -> bool:
    normalized = _normalized_doc_text(text)
    if not normalized:
        return False
    if any(pattern.search(normalized) for pattern in _GENERIC_RESULT_PATTERNS):
        return False
    annotation_text = ""
    if annotation is not None:
        annotation_text = _normalized_doc_text(ast.unparse(annotation))
    if annotation_text and normalized == annotation_text:
        return False
    if normalized in _TYPE_ONLY_RESULT_NAMES:
        return False
    return True


def _is_empty_or_type_only_description(
    text: str,
    annotation: ast.expr | None = None,
) -> bool:
    normalized = _normalized_doc_text(text)
    annotation_text = (
        _normalized_doc_text(ast.unparse(annotation))
        if annotation is not None
        else ""
    )
    return not normalized or normalized in _TYPE_ONLY_RESULT_NAMES or (
        bool(annotation_text) and normalized == annotation_text
    )


def _has_result_order_clause(text: str) -> bool:
    normalized = _normalized_doc_text(text).lower()
    if "," in normalized or "，" in normalized:
        return True
    return bool(
        re.search(
            r"\b(order|ordered|first|second|then)\b|顺序|第一|第二|先.+后",
            normalized,
        )
    )


def _tuple_item_name(value: ast.expr) -> str | None:
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Attribute):
        return value.attr
    if isinstance(value, ast.Constant) and isinstance(value.value, (str, int)):
        return str(value.value)
    if isinstance(value, ast.Constant) and value.value is None:
        return "None"
    return None


def _returned_tuple_orders(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[tuple[str, ...], ...]:
    orders: list[tuple[str, ...]] = []
    target_node = node

    class _ReturnVisitor(ast.NodeVisitor):
        def visit_Return(self, node: ast.Return) -> None:
            if not isinstance(node.value, ast.Tuple):
                return
            names = tuple(
                item_name
                for item in node.value.elts
                if (item_name := _tuple_item_name(item)) is not None
            )
            if len(names) == len(node.value.elts):
                orders.append(names)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node is not target_node:
                return
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if node is not target_node:
                return
            self.generic_visit(node)

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

    visitor = _ReturnVisitor()
    for statement in node.body:
        visitor.visit(statement)
    return tuple(dict.fromkeys(orders))


def _documented_tuple_orders(text: str) -> tuple[tuple[str, ...], ...]:
    orders: list[tuple[str, ...]] = []
    for match in re.finditer(r"\(([^()\n]*,[^()\n]*)\)", text):
        values = tuple(
            token.strip().strip("`'\"")
            for token in match.group(1).split(",")
            if token.strip()
        )
        if values and all(re.fullmatch(r"[A-Za-z_]\w*", value) for value in values):
            orders.append(values)
    return tuple(dict.fromkeys(orders))


def _annotated_tuple_orders(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[tuple[str, ...], ...]:
    annotation = node.returns
    if not isinstance(annotation, ast.Subscript):
        return ()
    if not isinstance(annotation.value, ast.Name) or annotation.value.id != "tuple":
        return ()
    slice_node = annotation.slice
    elements = slice_node.elts if isinstance(slice_node, ast.Tuple) else [slice_node]
    names = tuple(
        item_name
        for element in elements
        if (item_name := _tuple_item_name(element)) is not None
    )
    if len(names) != len(elements) or "..." in names:
        return ()
    return (names,)


def _returned_tuple_has_dynamic_members(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    class _ReturnVisitor(ast.NodeVisitor):
        found = False

        def visit_Return(self, node: ast.Return) -> None:
            if not isinstance(node.value, ast.Tuple):
                return
            if any(
                isinstance(item, (ast.Attribute, ast.Call, ast.Subscript))
                for item in node.value.elts
            ):
                self.found = True

    visitor = _ReturnVisitor()
    for statement in node.body:
        visitor.visit(statement)
    return visitor.found


def _has_exact_return_order(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    text: str,
) -> bool:
    expected_orders = _returned_tuple_orders(node)
    if not expected_orders:
        return True
    documented_orders = _documented_tuple_orders(text)
    if not documented_orders:
        return False
    annotated_orders = _annotated_tuple_orders(node)
    for expected in expected_orders:
        if expected in documented_orders:
            continue
        if any(order in documented_orders for order in annotated_orders):
            continue
        if _returned_tuple_has_dynamic_members(node) and any(
            len(order) == len(expected) for order in documented_orders
        ):
            continue
        if expected not in documented_orders:
            return False
    return True


def _is_multi_result(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if node.returns is None:
        return False
    annotation = ast.unparse(node.returns).replace("typing.", "")
    return annotation.startswith(("tuple[", "Tuple["))


def _exception_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _raised_exception_names(statements: list[ast.stmt]) -> tuple[str, ...]:
    names: set[str] = set()

    class _RaiseNameVisitor(ast.NodeVisitor):
        def visit_Raise(self, node: ast.Raise) -> None:
            if node.exc is not None:
                name = _exception_name(node.exc)
                if name is not None:
                    names.add(name)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            return

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            return

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            return

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

    visitor = _RaiseNameVisitor()
    for statement in statements:
        visitor.visit(statement)
    return tuple(sorted(names))


def _stable_exception_names(names: tuple[str, ...]) -> frozenset[str]:
    return frozenset(
        name
        for name in names
        if name.endswith("Error") or name in _KNOWN_BUILTIN_EXCEPTION_NAMES
    )


def _documented_exception_names(docstring: str) -> frozenset[str]:
    return frozenset(
        name.rsplit(".", 1)[-1]
        for name, _description in _section_entries(docstring, "Raises")
        if name
    )


def _private_raise_facts(
    tree: ast.Module,
) -> tuple[dict[str, frozenset[str]], dict[str, dict[str, frozenset[str]]]]:
    module_facts: dict[str, frozenset[str]] = {}
    class_facts: dict[str, dict[str, frozenset[str]]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith(_VALIDATION_HELPER_PREFIXES):
                module_facts[node.name] = _stable_exception_names(
                    _raised_exception_names(node.body)
                )
            continue
        if not isinstance(node, ast.ClassDef):
            continue
        facts: dict[str, frozenset[str]] = {}
        for member in node.body:
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if member.name.startswith(_VALIDATION_HELPER_PREFIXES):
                    facts[member.name] = _stable_exception_names(
                        _raised_exception_names(member.body)
                    )
        class_facts[node.name] = facts
    return module_facts, class_facts


def _direct_private_calls(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[tuple[str, bool], ...]:
    calls: list[tuple[str, bool]] = []

    class _CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            target = node.func
            if isinstance(target, ast.Name) and target.id.startswith("_"):
                calls.append((target.id, False))
            elif isinstance(target, ast.Attribute) and target.attr.startswith("_"):
                calls.append((target.attr, True))
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            return

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            return

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            return

    visitor = _CallVisitor()
    if isinstance(node, ast.ClassDef):
        for statement in node.body:
            if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if statement.name not in {"__init__", "__post_init__"}:
                continue
            for body_statement in statement.body:
                visitor.visit(body_statement)
    else:
        for statement in node.body:
            visitor.visit(statement)
    return tuple(calls)


def _delegated_exception_names(
    tree: ast.Module,
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    owner_class: str | None = None,
) -> frozenset[str]:
    module_facts, class_facts = _private_raise_facts(tree)
    names: set[str] = set()
    for name, is_method_call in _direct_private_calls(node):
        if is_method_call and owner_class is not None:
            names.update(class_facts.get(owner_class, {}).get(name, ()))
        elif not is_method_call:
            names.update(module_facts.get(name, ()))
    return frozenset(names)


def _has_section(docstring: str, name: str) -> bool:
    return any(line.strip() == f"{name}:" for line in docstring.splitlines())


def _returns_value(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    annotation = node.returns
    if annotation is None:
        return False
    if isinstance(annotation, ast.Constant) and annotation.value is None:
        return False
    if isinstance(annotation, ast.Name) and annotation.id == "None":
        return False
    return True


def _is_protocol_class(node: ast.ClassDef) -> bool:
    return any(
        (
            isinstance(base, ast.Name) and base.id == "Protocol"
        )
        or (
            isinstance(base, ast.Attribute) and base.attr == "Protocol"
        )
        for base in node.bases
    )


class _DirectRaiseVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.has_raise = False

    def visit_Raise(self, node: ast.Raise) -> None:
        self.has_raise = True

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def _statements_raise(statements: list[ast.stmt]) -> bool:
    visitor = _DirectRaiseVisitor()
    for statement in statements:
        visitor.visit(statement)
    return visitor.has_raise


def _public_interface_nodes(
    tree: ast.Module,
) -> tuple[
    tuple[
        str,
        str,
        ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
    ],
    ...,
    ]:
    rows: list[
        tuple[
            str,
            str,
            ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        ]
    ] = []
    classes = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }

    def base_name(base: ast.expr) -> str | None:
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        return None

    def inherited_methods(
        node: ast.ClassDef,
        seen: set[str],
    ) -> tuple[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef], ...]:
        if node.name in seen:
            return ()
        seen.add(node.name)
        local_names = {
            statement.name
            for statement in node.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        inherited: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
        for base in node.bases:
            resolved_name = base_name(base)
            resolved = classes.get(resolved_name or "")
            if resolved is None:
                continue
            for statement in resolved.body:
                if (
                    isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not statement.name.startswith("_")
                    and statement.name not in local_names
                ):
                    inherited.append((statement.name, statement))
            inherited.extend(inherited_methods(resolved, seen))
        return tuple(inherited)

    for node in tree.body:
        if not isinstance(
            node,
            (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue
        if node.name.startswith("_"):
            continue
        rows.append((node.name, node.name, node))
        if not isinstance(node, ast.ClassDef):
            continue
        for statement in node.body:
            if not isinstance(
                statement,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue
            if statement.name.startswith("_"):
                continue
            rows.append(
                (
                    node.name,
                    f"{node.name}.{statement.name}",
                    statement,
                )
            )
        direct_names = {
            statement.name
            for statement in node.body
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for method_name, method in inherited_methods(node, set()):
            if method_name in direct_names:
                continue
            rows.append(
                (
                    node.name,
                    f"{node.name}.{method_name}",
                    method,
                )
            )
    return tuple(rows)


def _interface_findings(
    tree: ast.Module,
    relative: str,
    exported_names: frozenset[str],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for top_level_name, symbol, node in _public_interface_nodes(tree):
        method_name = symbol.rsplit(".", 1)[-1] if "." in symbol else None
        local_owner = next(
            (
                candidate
                for candidate in tree.body
                if isinstance(candidate, ast.ClassDef)
                and candidate.name == top_level_name
            ),
            None,
        )
        if (
            method_name is not None
            and local_owner is not None
            and not any(
                isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
                and statement.name == method_name
                for statement in local_owner.body
            )
        ):
            inherited_owner = next(
                (
                    candidate
                    for candidate in tree.body
                    if isinstance(candidate, ast.ClassDef)
                    and any(child is node for child in candidate.body)
                ),
                None,
            )
            if (
                inherited_owner is None
                or inherited_owner.name not in exported_names
                or ast.get_docstring(node, clean=False) is None
            ):
                findings.append(
                    {
                        "rule": "SourceInterface001",
                        "kind": "hard_violation",
                        "path": relative,
                        "line": node.lineno,
                        "symbol": symbol,
                        "message": (
                            f"public Interface {symbol} must own a local docstring"
                        ),
                    }
                )
                continue
        docstring = ast.get_docstring(node, clean=True)
        if docstring is None:
            findings.append(
                {
                    "rule": "SourceInterface001",
                    "kind": "hard_violation",
                    "path": relative,
                    "line": node.lineno,
                    "symbol": symbol,
                    "message": f"public Interface {symbol} must own a local docstring",
                }
            )
            continue
        if top_level_name not in exported_names:
            continue
        if isinstance(node, ast.ClassDef):
            parameters = _class_parameter_names(node)
            argument_section = next(
                (
                    name
                    for name in ("Args", "Attributes")
                    if _has_section(docstring, name)
                ),
                None,
            )
            documented = (
                _documented_names(docstring, (argument_section,))
                if argument_section is not None
                else None
            )
            constructors = [
                statement
                for statement in node.body
                if isinstance(
                    statement,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                )
                and statement.name in {"__init__", "__post_init__"}
            ]
            direct_raise_names = _stable_exception_names(
                tuple(
                    name
                    for statement in constructors
                    for name in _raised_exception_names(statement.body)
                )
            )
            has_direct_raise = any(
                _statements_raise(statement.body) for statement in constructors
            )
            delegated_raise_names = _delegated_exception_names(tree, node, node.name)
        else:
            argument_section = "Args"
            parameters = _callable_parameter_names(node)
            documented = _documented_names(docstring, ("Args",))
            direct_raise_names = _stable_exception_names(
                _raised_exception_names(node.body)
            )
            has_direct_raise = _statements_raise(node.body)
            delegated_raise_names = _delegated_exception_names(
                tree,
                node,
                top_level_name if method_name is not None else None,
            )
        if parameters and documented is None:
            findings.append(
                {
                    "rule": "SourceInterface002",
                    "kind": "hard_violation",
                    "path": relative,
                    "line": node.lineno,
                    "symbol": symbol,
                    "message": f"public Interface {symbol} must document its arguments",
                }
            )
        elif documented is not None and set(documented) != set(parameters):
            findings.append(
                {
                    "rule": "SourceInterface005",
                    "kind": "hard_violation",
                    "path": relative,
                    "line": node.lineno,
                    "symbol": symbol,
                    "message": (
                        f"public Interface {symbol} argument documentation differs "
                        "from its Interface"
                    ),
                }
            )
        if documented is not None and argument_section is not None:
            argument_entries = _section_entries(docstring, argument_section)
            descriptions = {
                name: description for name, description in argument_entries
            }
            for parameter in parameters:
                if not _is_semantic_description(
                    descriptions.get(parameter, ""),
                ):
                    findings.append(
                        {
                            "rule": "SourceInterface008",
                            "kind": "hard_violation",
                            "path": relative,
                            "line": node.lineno,
                            "symbol": symbol,
                            "message": (
                                f"public Interface {symbol} argument {parameter} "
                                "must have semantic documentation"
                            ),
                        }
                    )
        is_property = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            isinstance(decorator, ast.Name) and decorator.id == "property"
            for decorator in node.decorator_list
        )
        is_protocol_property = (
            is_property
            and local_owner is not None
            and _is_protocol_class(local_owner)
        )
        requires_result_semantics = (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _returns_value(node)
            and (not is_property or is_protocol_property)
        )
        is_method = "." in symbol
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and requires_result_semantics
            and (not is_method or bool(parameters))
            and not (
                _has_section(docstring, "Returns")
                or _has_section(docstring, "Yields")
            )
        ):
            findings.append(
                {
                    "rule": "SourceInterface003",
                    "kind": "hard_violation",
                    "path": relative,
                    "line": node.lineno,
                    "symbol": symbol,
                    "message": f"public Interface {symbol} must document its result",
                }
            )
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and requires_result_semantics
        ):
            result_section = (
                "Returns"
                if _has_section(docstring, "Returns")
                else "Yields"
            )
            result_entries = _section_entries(docstring, result_section)
            result_text = " ".join(description for _name, description in result_entries)
            if not _is_semantic_description(result_text, node.returns):
                findings.append(
                    {
                        "rule": (
                            "SourceInterface009"
                            if _is_empty_or_type_only_description(
                                result_text,
                                node.returns,
                            )
                            else "SourceInterface007"
                        ),
                        "kind": "hard_violation",
                        "path": relative,
                        "line": node.lineno,
                        "symbol": symbol,
                        "message": f"public Interface {symbol} result must be semantic",
                    }
                )
            elif _is_multi_result(node) and not _has_result_order_clause(result_text):
                findings.append(
                    {
                        "rule": "SourceInterface010",
                        "kind": "hard_violation",
                        "path": relative,
                        "line": node.lineno,
                        "symbol": symbol,
                        "message": (
                            f"public Interface {symbol} multi-result documentation "
                            "must state its public order"
                        ),
                    }
                )
            elif _is_multi_result(node) and not _has_exact_return_order(
                node,
                result_text,
            ):
                findings.append(
                    {
                        "rule": "SourceInterface010",
                        "kind": "hard_violation",
                        "path": relative,
                        "line": node.lineno,
                        "symbol": symbol,
                        "message": (
                            f"public Interface {symbol} result documentation "
                            "does not match its returned tuple order"
                        ),
                    }
                )
        raises_entries = _section_entries(docstring, "Raises")
        if _has_section(docstring, "Raises"):
            malformed = not raises_entries or any(
                not name or not re.fullmatch(
                    r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?",
                    name,
                )
                for name, _description in raises_entries
            )
            if malformed:
                findings.append(
                    {
                        "rule": "SourceInterface011",
                        "kind": "hard_violation",
                        "path": relative,
                        "line": node.lineno,
                        "symbol": symbol,
                        "message": (
                            f"public Interface {symbol} Raises entries must name "
                            "exception types"
                        ),
                    }
                )
            for exception_name, description in raises_entries:
                if _GENERIC_RAISES_PATTERN.search(description):
                    findings.append(
                        {
                            "rule": "SourceInterface013",
                            "kind": "hard_violation",
                            "path": relative,
                            "line": node.lineno,
                            "symbol": symbol,
                            "message": (
                                f"public Interface {symbol} must state the "
                                f"condition for {exception_name}"
                            ),
                        }
                    )
        if has_direct_raise and not _has_section(docstring, "Raises"):
            findings.append(
                {
                    "rule": "SourceInterface004",
                    "kind": "hard_violation",
                    "path": relative,
                    "line": node.lineno,
                    "symbol": symbol,
                    "message": f"public Interface {symbol} must document its failures",
                }
            )
        documented_exceptions = _documented_exception_names(docstring)
        missing_delegated = delegated_raise_names - documented_exceptions
        if missing_delegated:
            findings.append(
                {
                    "rule": "SourceInterface012",
                    "kind": "hard_violation",
                    "path": relative,
                    "line": node.lineno,
                    "symbol": symbol,
                    "message": (
                        f"public Interface {symbol} must document delegated "
                        f"failures: {', '.join(sorted(missing_delegated))}"
                    ),
                }
            )
    return findings


def _module_name(source_root: Path, path: Path) -> str:
    relative = path.relative_to(source_root).with_suffix("")
    parts = [source_root.name, *relative.parts]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _literal_exports(tree: ast.Module) -> tuple[str, ...]:
    for statement in tree.body:
        value: ast.expr | None = None
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in statement.targets
        ):
            value = statement.value
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == "__all__"
        ):
            value = statement.value
        if value is None:
            continue
        try:
            exports = ast.literal_eval(value)
        except (TypeError, ValueError):
            return ()
        if isinstance(exports, (list, tuple)) and all(
            isinstance(name, str) for name in exports
        ):
            return tuple(exports)
    return ()


def _resolved_import_module(
    current_module: str,
    is_package: bool,
    statement: ast.ImportFrom,
) -> str:
    if statement.level == 0:
        return statement.module or ""
    package_parts = current_module.split(".")
    if not is_package:
        package_parts.pop()
    remove = statement.level - 1
    if remove:
        package_parts = package_parts[:-remove]
    if statement.module:
        package_parts.extend(statement.module.split("."))
    return ".".join(package_parts)


def _exported_definition_names(
    source_root: Path,
    parsed: dict[Path, ast.Module],
) -> dict[Path, frozenset[str]]:
    module_by_path = {
        path: _module_name(source_root, path) for path in parsed
    }
    path_by_module = {module: path for path, module in module_by_path.items()}
    definitions: dict[tuple[str, str], ast.AST] = {}
    imports: dict[tuple[str, str], tuple[str, str]] = {}
    exports: dict[str, tuple[str, ...]] = {}
    for path, tree in parsed.items():
        module = module_by_path[path]
        exports[module] = _literal_exports(tree)
        for statement in tree.body:
            if isinstance(
                statement,
                (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                definitions[(module, statement.name)] = statement
            elif isinstance(statement, ast.ImportFrom):
                imported_module = _resolved_import_module(
                    module,
                    path.name == "__init__.py",
                    statement,
                )
                for alias in statement.names:
                    if alias.name == "*":
                        continue
                    local_name = alias.asname or alias.name
                    imports[(module, local_name)] = (
                        imported_module,
                        alias.name,
                    )

    def resolve(module: str, name: str) -> tuple[str, str] | None:
        seen: set[tuple[str, str]] = set()
        current = (module, name)
        while current not in seen:
            seen.add(current)
            if current in definitions:
                return current
            if current not in imports:
                return None
            current = imports[current]
        return None

    names_by_path: dict[Path, set[str]] = {}
    for module, module_exports in exports.items():
        if not module_exports:
            continue
        for name in module_exports:
            resolved = resolve(module, name)
            if resolved is None:
                continue
            origin_module, origin_name = resolved
            origin_path = path_by_module.get(origin_module)
            if origin_path is None:
                continue
            names_by_path.setdefault(origin_path, set()).add(origin_name)
    return {
        path: frozenset(names) for path, names in names_by_path.items()
    }


def _source_structure_findings(scan_path: Path) -> list[dict[str, object]]:
    # 统一公共 Interface 文档与私有 Implementation 注释的所有权
    resolved = scan_path.resolve()
    source_root = resolved / "src" if (resolved / "src").is_dir() else resolved
    if source_root.name == "src":
        source_root = source_root / "chromatix_next"
    if not source_root.is_dir():
        return []
    findings: list[dict[str, object]] = []
    parsed: dict[Path, ast.Module] = {}
    texts: dict[Path, str] = {}
    for path in sorted(source_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path), type_comments=True)
        except SyntaxError:
            continue
        parsed[path] = tree
        texts[path] = text
    exported_names = _exported_definition_names(source_root, parsed)
    for path, tree in parsed.items():
        text = texts[path]
        relative = _relative_scan_path(path, resolved)
        if ast.get_docstring(tree, clean=False) is not None:
            findings.append(
                {
                    "rule": "SourceStructure001",
                    "kind": "hard_violation",
                    "path": relative,
                    "line": 1,
                    "message": "production modules must not have module docstrings",
                }
            )
        findings.extend(
            _interface_findings(
                tree,
                relative,
                exported_names.get(path, frozenset()),
            )
        )
        lines = text.splitlines()
        first_code = next(
            (
                index
                for index, line in enumerate(lines)
                if line.strip() and not line.lstrip().startswith("#")
            ),
            None,
        )
        if first_code is not None and any(
            line.lstrip().startswith("#") for line in lines[:first_code]
        ):
            findings.append(
                {
                    "rule": "SourceStructure002",
                    "kind": "hard_violation",
                    "path": relative,
                    "line": first_code + 1,
                    "message": "leading comment dossiers are not production source",
                }
            )
        for node in ast.walk(tree):
            if not isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            ):
                continue
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node, clean=False)
                if docstring is not None:
                    docstring_line = node.body[0].lineno
                    leading_comment_line = next(
                        (
                            line_number
                            for line_number in range(node.lineno + 1, docstring_line)
                            if lines[line_number - 1].lstrip().startswith("#")
                        ),
                        None,
                    )
                    if leading_comment_line is not None:
                        findings.append(
                            {
                                "rule": "SourceStructure009",
                                "kind": "hard_violation",
                                "path": relative,
                                "line": leading_comment_line,
                                "message": (
                                    f"class {node.name} contract docstring must "
                                    "precede local Implementation comments"
                                ),
                            }
                        )
                if (
                    node.name.startswith("_")
                    and not node.name.startswith("__")
                    and docstring is None
                    and _private_class_owns_durable_state(node)
                ):
                    findings.append(
                        {
                            "rule": "SourceStructure008",
                            "kind": "hard_violation",
                            "path": relative,
                            "line": node.lineno,
                            "message": (
                                f"durable private class {node.name} must own a "
                                "concise class docstring"
                            ),
                        }
                    )
                continue
            if not node.name.startswith("_") or node.name.startswith("__"):
                continue
            if ast.get_docstring(node, clean=False) is None:
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                private_class = any(
                    isinstance(candidate, ast.ClassDef)
                    and candidate.name.startswith("_")
                    and any(child is node for child in candidate.body)
                    for candidate in ast.walk(tree)
                )
                if private_class:
                    continue
            findings.append(
                {
                    "rule": "SourceStructure003",
                    "kind": "hard_violation",
                    "path": relative,
                    "line": node.lineno,
                    "message": f"private symbol {node.name} must not have a docstring",
                }
            )
        standalone_comment_lines: list[int] = []
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type != tokenize.COMMENT:
                continue
            prefix = lines[token.start[0] - 1][: token.start[1]]
            is_standalone = not prefix.strip()
            comment = token.string[1:].strip()
            if _DOCUMENT_POINTER_COMMENT_PATTERN.fullmatch(comment):
                findings.append(
                    {
                        "rule": "SourceStructure007",
                        "kind": "hard_violation",
                        "path": relative,
                        "line": token.start[0],
                        "message": (
                            "documentation-reference comments are not local "
                            "Implementation reasons"
                        ),
                    }
                )
            if is_standalone:
                standalone_comment_lines.append(token.start[0])
                if comment.endswith(_COMMENT_TERMINATORS):
                    findings.append(
                        {
                            "rule": "SourceStructure005",
                            "kind": "hard_violation",
                            "path": relative,
                            "line": token.start[0],
                            "message": (
                                "local Implementation comments do not end with "
                                "sentence punctuation"
                            ),
                        }
                    )
            for pattern in _BANNED_COMMENT_PATTERNS:
                if pattern.search(token.string):
                    findings.append(
                        {
                            "rule": "SourceStructure004",
                            "kind": "hard_violation",
                            "path": relative,
                            "line": token.start[0],
                            "message": (
                                "tracker or governance prose is not a source "
                                "comment"
                            ),
                        }
                    )
                    break
        if standalone_comment_lines:
            block_start = standalone_comment_lines[0]
            previous = block_start
            for line in (*standalone_comment_lines[1:], -1):
                if line == previous + 1:
                    previous = line
                    continue
                if previous > block_start:
                    findings.append(
                        {
                            "rule": "SourceStructure006",
                            "kind": "hard_violation",
                            "path": relative,
                            "line": block_start,
                            "message": (
                                "local Implementation comments express one intent "
                                "on one line"
                            ),
                        }
                    )
                block_start = line
                previous = line
    return findings


def _nonproduction_prose_findings(
    scan_path: Path,
) -> list[dict[str, object]]:
    resolved = scan_path.resolve()
    roots: list[Path] = []
    for name in ("tests", "tools"):
        candidate = resolved / name
        if candidate.is_dir():
            roots.append(candidate)
    if resolved.name in {"tests", "tools"} and resolved.is_dir():
        roots.append(resolved)
    frozen = (
        PROJECT_ROOT / "tests" / "package_contract" / "test_examples.py"
    ).resolve()
    findings: list[dict[str, object]] = []
    for root in dict.fromkeys(roots):
        for path in sorted(root.rglob("*.py")):
            if path.resolve() == frozen:
                continue
            text = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(text, filename=str(path), type_comments=True)
            except SyntaxError:
                continue
            relative = _relative_scan_path(path, resolved)
            if ast.get_docstring(tree, clean=False) is not None:
                findings.append(
                    {
                        "rule": "ProseStructure001",
                        "kind": "hard_violation",
                        "path": relative,
                        "line": 1,
                        "message": (
                            "test and tool modules must not use module docstrings"
                        ),
                    }
                )
            lines = text.splitlines()
            first_code = next(
                (
                    index
                    for index, line in enumerate(lines)
                    if line.strip() and not line.lstrip().startswith("#")
                ),
                None,
            )
            if first_code is not None and any(
                line.lstrip().startswith("#") for line in lines[:first_code]
            ):
                findings.append(
                    {
                        "rule": "ProseStructure002",
                        "kind": "hard_violation",
                        "path": relative,
                        "line": first_code + 1,
                        "message": (
                            "test and tool files must not begin with comment "
                            "dossiers"
                        ),
                    }
                )
            for node in ast.walk(tree):
                if not isinstance(
                    node,
                    (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                ) or not node.name.startswith("_") or node.name.startswith("__"):
                    continue
                if ast.get_docstring(node, clean=False) is not None:
                    findings.append(
                        {
                            "rule": "ProseStructure003",
                            "kind": "hard_violation",
                            "path": relative,
                            "line": node.lineno,
                            "message": (
                                "private test and tool implementation uses "
                                "local comments, not docstrings"
                            ),
                        }
                    )
            comments = [
                token
                for token in tokenize.generate_tokens(io.StringIO(text).readline)
                if token.type == tokenize.COMMENT
                and not lines[token.start[0] - 1][: token.start[1]].strip()
            ]
            previous_line: int | None = None
            for token in comments:
                comment = token.string[1:].strip()
                if comment.endswith(_COMMENT_TERMINATORS):
                    findings.append(
                        {
                            "rule": "ProseStructure004",
                            "kind": "hard_violation",
                            "path": relative,
                            "line": token.start[0],
                            "message": (
                                "test and tool comments do not end with "
                                "sentence punctuation"
                            ),
                        }
                    )
                if previous_line is not None and token.start[0] == previous_line + 1:
                    findings.append(
                        {
                            "rule": "ProseStructure005",
                            "kind": "hard_violation",
                            "path": relative,
                            "line": token.start[0],
                            "message": (
                                "test and tool comments state one local reason "
                                "per block"
                            ),
                        }
                    )
                previous_line = token.start[0]
    return findings


def _relative_scan_path(path: Path, scan_root: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.relative_to(scan_root).as_posix()


def _enabled_native_rules(
    profile_path: Path = PROFILE_PATH,
) -> frozenset[str]:
    with profile_path.open("rb") as profile_file:
        profile = tomllib.load(profile_file)
    configured_rules = profile.get("enabled_rules")
    if not isinstance(configured_rules, list) or not all(
        isinstance(rule, str) and rule for rule in configured_rules
    ):
        raise ValueError("csu_enabled_rules_invalid")
    return frozenset(configured_rules)


def _retain_enabled_native_findings(
    findings: list[dict[str, object]],
    enabled_rules: frozenset[str],
) -> list[dict[str, object]]:
    return [
        finding
        for finding in findings
        if str(finding.get("rule")) in enabled_rules
    ]


def _csu_executable() -> Path:
    command = shutil.which("csu")
    if command is not None:
        return Path(command)
    candidates = [PROJECT_ROOT / "csu" / "bin" / "csu"]
    if os.name == "nt":
        candidates.insert(0, PROJECT_ROOT / "csu" / "bin" / "csu.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    error_identity = "csu_executable_not_found"
    raise FileNotFoundError(error_identity)


def _scan(scan_path: Path) -> list[dict[str, object]]:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as output_file:
            temporary_path = Path(output_file.name)
        completed = subprocess.run(
            [
                str(_csu_executable()),
                "check",
                str(scan_path),
                "--profile-path",
                str(PROFILE_PATH),
                "--format",
                "json",
                "--output",
                str(temporary_path),
                "--no-history",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        if completed.returncode not in (0, 1):
            message = completed.stderr.strip() or completed.stdout.strip()
            error_message = f"csu_scan_failed: {message}"
            raise RuntimeError(error_message)
        findings = json.loads(temporary_path.read_text(encoding="utf-8"))
        if not isinstance(findings, list) or not all(
            isinstance(finding, dict) for finding in findings
        ):
            error_identity = "csu_output_invalid"
            raise ValueError(error_identity)
        return findings
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _collect_findings(scan_path: Path) -> list[dict[str, object]]:
    findings = _retain_enabled_native_findings(
        _scan(scan_path),
        _enabled_native_rules(),
    )
    findings.extend(_source_structure_findings(scan_path))
    findings.extend(_nonproduction_prose_findings(scan_path))
    findings.sort(
        key=lambda finding: json.dumps(
            finding,
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    return findings


def _collect_managed_findings() -> list[dict[str, object]]:
    with tempfile.TemporaryDirectory(prefix="chromatix-next-csu-") as directory:
        staged_root = Path(directory)
        for source in _managed_file_paths():
            relative = source.relative_to(PROJECT_ROOT)
            target = staged_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return _collect_findings(staged_root)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the complete ChromatixNext CSU quality gate.",
    )
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    """
    执行完整扫描并拒绝所有硬违规与待审项
    """
    arguments = _arguments()
    try:
        findings = (
            _collect_managed_findings()
            if arguments.path is None
            else _collect_findings(arguments.path)
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2

    rejected = [finding for finding in findings if _rejects_finding(finding)]
    kind_counts = Counter(str(finding.get("kind")) for finding in findings)
    rule_counts = Counter(str(finding.get("rule")) for finding in findings)
    summary = ", ".join(f"{rule}={rule_counts[rule]}" for rule in sorted(rule_counts))
    print(
        f"CSU {arguments.path or 'managed non-Example inventory'}: "
        f"{len(findings)} findings, "
        f"hard={kind_counts['hard_violation']}, "
        f"under_review={kind_counts['under_review']}, "
        f"soft={kind_counts['soft_violation']}",
    )
    if summary:
        print(summary)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(findings, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 1 if rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())

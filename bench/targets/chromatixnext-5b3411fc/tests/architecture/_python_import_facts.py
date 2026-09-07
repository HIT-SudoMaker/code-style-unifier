
from __future__ import annotations

import ast
from dataclasses import dataclass
import keyword
from pathlib import Path
import stat

__all__ = (
    "PythonImportFactError",
    "PythonImportFacts",
    "inspect_python_imports",
    "read_python_imports",
)


class PythonImportFactError(ValueError):
    """
    无法建立可信的静态 import facts 时抛出
    """



@dataclass(frozen=True)
class PythonImportFacts:
    """
    单个 Python 源单元的不可变静态 import facts
    """

    # module_name：源码所代表的模块
    module_name: str
    imported_modules: frozenset[str]
    imported_targets: frozenset[str]
    local_bindings: frozenset[str]
    runtime_imported_modules: frozenset[str]
    runtime_imported_targets: frozenset[str]
    runtime_local_bindings: frozenset[str]


class _ImportFactCollector:
    def __init__(self, package_parts: tuple[str, ...]) -> None:
        """
        累加静态与运行时导入事实
        """

        self.package_parts = package_parts
        self.modules: set[str] = set()
        self.targets: set[str] = set()
        self.bindings: set[str] = set()
        self.runtime_modules: set[str] = set()
        self.runtime_targets: set[str] = set()
        self.runtime_bindings: set[str] = set()
        self.is_runtime = True
        self.can_exclude_type_checking_body = False
        self.type_checking_names: set[str] = set()
        self.typing_module_names: set[str] = set()

    def _record(
        self,
        module: str,
        target: str,
        binding: str,
    ) -> None:
        self.modules.add(module)
        self.targets.add(target)
        self.bindings.add(binding)
        if self.is_runtime:
            self.runtime_modules.add(module)
            self.runtime_targets.add(target)
            self.runtime_bindings.add(binding)

    def _visit_nodes(
        self,
        nodes: list[ast.stmt],
        *,
        is_runtime: bool,
    ) -> None:
        previous_runtime = self.is_runtime
        previous_exclusion = self.can_exclude_type_checking_body
        self.is_runtime = previous_runtime and is_runtime
        self.can_exclude_type_checking_body = False
        for node in nodes:
            self._visit(node)
        self.is_runtime = previous_runtime
        self.can_exclude_type_checking_body = previous_exclusion

    def _visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.Module):
            for statement in node.body:
                self.can_exclude_type_checking_body = True
                self._visit(statement)
                self.can_exclude_type_checking_body = False
                self._update_module_bindings(statement)
            return
        if isinstance(node, ast.If) and self._is_type_checking_guard(node.test):
            self._visit_nodes(node.body, is_runtime=False)
            self._visit_nodes(node.orelse, is_runtime=True)
            return
        if isinstance(node, ast.Import):
            for alias in node.names:
                self._record(
                    alias.name,
                    alias.name,
                    alias.asname or alias.name.split(".")[0],
                )
            return
        if isinstance(node, ast.ImportFrom):
            base_module = _from_base_module(node, self.package_parts)
            for alias in node.names:
                target = (
                    f"{base_module}.*"
                    if alias.name == "*"
                    else f"{base_module}.{alias.name}"
                )
                binding = (
                    "*"
                    if alias.name == "*"
                    else alias.asname or alias.name
                )
                self._record(base_module, target, binding)
            return
        previous_exclusion = self.can_exclude_type_checking_body
        self.can_exclude_type_checking_body = False
        for child in ast.iter_child_nodes(node):
            self._visit(child)
        self.can_exclude_type_checking_body = previous_exclusion

    def _is_type_checking_guard(self, node: ast.expr) -> bool:
        return self.can_exclude_type_checking_body and (
            (
                isinstance(node, ast.Name)
                and node.id in self.type_checking_names
            )
            or (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in self.typing_module_names
                and node.attr == "TYPE_CHECKING"
            )
        )

    def _update_module_bindings(self, node: ast.stmt) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                binding = alias.asname or alias.name.split(".")[0]
                self.type_checking_names.discard(binding)
                self.typing_module_names.discard(binding)
                if alias.name == "typing":
                    self.typing_module_names.add(binding)
            return
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                binding = alias.asname or alias.name
                self.type_checking_names.discard(binding)
                self.typing_module_names.discard(binding)
                if node.module == "typing" and alias.name == "TYPE_CHECKING":
                    self.type_checking_names.add(binding)
            return
        names = _module_binding_changes(node)
        self.type_checking_names.difference_update(names)
        self.typing_module_names.difference_update(names)


def _module_binding_changes(node: ast.stmt) -> set[str]:
    names: set[str] = set()

    def _collect_changes(current: ast.AST) -> None:
        if isinstance(
            current,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            names.add(current.name)
            return
        if isinstance(current, ast.Import):
            names.update(
                alias.asname or alias.name.split(".")[0]
                for alias in current.names
            )
            return
        if isinstance(current, ast.ImportFrom):
            names.update(
                alias.asname or alias.name
                for alias in current.names
            )
            return
        if isinstance(
            current,
            (
                ast.Lambda,
                ast.ListComp,
                ast.SetComp,
                ast.DictComp,
                ast.GeneratorExp,
            ),
        ):
            return
        if isinstance(current, ast.Name) and isinstance(
            current.ctx,
            (ast.Store, ast.Del),
        ):
            names.add(current.id)
        if (
            isinstance(current, ast.Attribute)
            and isinstance(current.ctx, (ast.Store, ast.Del))
            and isinstance(current.value, ast.Name)
            and current.attr == "TYPE_CHECKING"
        ):
            names.add(current.value.id)
        if isinstance(current, ast.ExceptHandler) and current.name is not None:
            names.add(current.name)
        if isinstance(current, (ast.MatchAs, ast.MatchStar)):
            if current.name is not None:
                names.add(current.name)
        if isinstance(current, ast.MatchMapping) and current.rest is not None:
            names.add(current.rest)
        for child in ast.iter_child_nodes(current):
            _collect_changes(child)

    _collect_changes(node)
    return names


def inspect_python_imports(
    source: str,
    module_name: str,
    is_package: bool,
) -> PythonImportFacts:
    """
    为已给出的源码文本建立不可变 import facts
    """

    package_parts = _package_context(module_name, is_package)
    try:
        tree = ast.parse(source)
    except (SyntaxError, UnicodeError) as exc:
        reason = exc.msg if isinstance(exc, SyntaxError) else str(exc)
        raise PythonImportFactError(
            f"cannot parse import facts for module {module_name!r}: {reason}"
        ) from exc
    collector = _ImportFactCollector(package_parts)
    collector._visit(tree)
    return PythonImportFacts(
        module_name=module_name,
        imported_modules=frozenset(collector.modules),
        imported_targets=frozenset(collector.targets),
        local_bindings=frozenset(collector.bindings),
        runtime_imported_modules=frozenset(collector.runtime_modules),
        runtime_imported_targets=frozenset(collector.runtime_targets),
        runtime_local_bindings=frozenset(collector.runtime_bindings),
    )


def read_python_imports(
    path: Path | str,
    source_root: Path | str,
) -> PythonImportFacts:
    """
    读取 source_root 内的文件并建立其 import facts
    """

    try:
        resolved_path = Path(path).resolve()
        resolved_root = Path(source_root).resolve()
    except OSError as exc:
        raise PythonImportFactError(
            f"cannot resolve source file {path!s} under root {source_root!s}: "
            f"{exc}"
        ) from exc
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise PythonImportFactError(
            f"file {resolved_path} is outside source root {resolved_root}"
        ) from exc
    if relative == Path("."):
        raise PythonImportFactError(
            f"path {resolved_path} is the source root itself; no module name"
        )
    try:
        file_mode = resolved_path.stat().st_mode
    except OSError as exc:
        raise PythonImportFactError(
            f"cannot access Python source file {resolved_path}: {exc}"
        ) from exc
    if not stat.S_ISREG(file_mode):
        raise PythonImportFactError(
            f"Python source path {resolved_path} is not a regular file"
        )
    parts = list(relative.with_suffix("").parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts = parts[:-1]
    if not parts:
        raise PythonImportFactError(
            f"path {resolved_path} resolves to no module name under "
            f"{resolved_root}"
        )
    invalid_part = next(
        (part for part in parts if not _is_valid_module_identifier(part)),
        None,
    )
    if invalid_part is not None:
        raise PythonImportFactError(
            f"path {resolved_path} contains invalid module segment "
            f"{invalid_part!r} under source root {resolved_root}"
        )
    try:
        source = resolved_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PythonImportFactError(
            f"cannot read Python source file {resolved_path}: {exc}"
        ) from exc
    return inspect_python_imports(source, ".".join(parts), is_package)


def _package_context(
    module_name: str,
    is_package: bool,
) -> tuple[str, ...]:
    # 包初始化模块以自身为相对导入锚点；普通模块以其父包为锚点
    parts = _validated_module_parts(module_name)
    return parts if is_package else parts[:-1]


def _validated_module_parts(module_name: str) -> tuple[str, ...]:
    parts = tuple(module_name.split("."))
    invalid_part = next(
        (
            part
            for part in parts
            if not _is_valid_module_identifier(part)
        ),
        None,
    )
    if not module_name or invalid_part is not None:
        raise PythonImportFactError(
            f"module name {module_name!r} is not a dotted sequence of "
            "non-keyword Python identifiers"
        )
    return parts


def _is_valid_module_identifier(identifier: str) -> bool:
    return (
        bool(identifier)
        and identifier.isidentifier()
        and not keyword.iskeyword(identifier)
    )


def _from_base_module(
    node: ast.ImportFrom,
    package_parts: tuple[str, ...],
) -> str:
    if node.level == 0:
        if not node.module:
            raise PythonImportFactError(
                "absolute import-from without a module name is not valid Python"
            )
        return node.module
    ups = node.level - 1
    if ups >= len(package_parts):
        raise PythonImportFactError(
            f"relative import level {node.level} escapes above the package "
            f"or root of module context {list(package_parts)}"
        )
    base_parts = package_parts[: len(package_parts) - ups]
    if node.module:
        base_parts = (*base_parts, *node.module.split("."))
    if not base_parts:
        raise PythonImportFactError(
            f"relative import level {node.level} resolves to an empty base "
            f"module for context {list(package_parts)}"
        )
    return ".".join(base_parts)

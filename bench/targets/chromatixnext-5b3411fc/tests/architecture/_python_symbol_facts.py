from __future__ import annotations

import ast
from dataclasses import dataclass

__all__ = (
    "PythonCallFact",
    "PythonSymbolBindings",
    "PythonSymbolFactError",
    "read_module_symbol_bindings",
    "read_python_call_facts",
    "resolve_expression_source",
)

_ABSOLUTE_IMPORT_WITHOUT_MODULE = "absolute import has no module"
_GLOBAL_BINDING_UNSUPPORTED = "global and nonlocal bindings are unsupported"
_RELATIVE_IMPORT_OUTSIDE_PACKAGE = "relative import escapes package"
_WILDCARD_BINDING_UNKNOWN = "wildcard imports have unknown bindings"


class PythonSymbolFactError(ValueError):
    """
    无法确定静态符号绑定时抛出
    """


@dataclass(frozen=True)
class PythonSymbolBindings:
    """
    保存局部名称到完整来源或未知遮蔽的不可变绑定事实
    """

    entries: tuple[tuple[str, str | None], ...]

    def source_for(self, local_name: str) -> str | None:
        """
        返回名称的来源；未知或被遮蔽的名称返回空值
        """

        return dict(self.entries).get(local_name)

    def has_binding(self, local_name: str) -> bool:
        """
        判断名称是否在当前词法作用域中被绑定
        """

        return local_name in dict(self.entries)

    def items(self) -> tuple[tuple[str, str | None], ...]:
        """
        按绑定顺序返回全部事实
        """

        return self.entries


@dataclass(frozen=True)
class PythonCallFact:
    """
    不可变调用绑定事实

    `source` 是调用目标
    `positional_sources` 是直接位置参数调用的目标
    `keyword_names` 只记录关键字名称
    无法静态确定的来源均为空值
    """

    scope_name: str
    line: int
    source: str | None
    positional_sources: tuple[str | None, ...]
    keyword_names: tuple[str | None, ...]


def resolve_expression_source(
    expression: ast.expr,
    bindings: PythonSymbolBindings,
) -> str | None:
    """
    解析名称或属性表达式在当前绑定快照中的来源
    """

    if isinstance(expression, ast.Name):
        if bindings.has_binding(expression.id):
            return bindings.source_for(expression.id)
        return None
    if isinstance(expression, ast.Attribute):
        owner = resolve_expression_source(expression.value, bindings)
        return None if owner is None else f"{owner}.{expression.attr}"
    return None


def read_module_symbol_bindings(
    tree: ast.Module,
    module_name: str,
    *,
    is_package: bool = False,
) -> PythonSymbolBindings:
    """
    读取模块顶层按执行顺序形成的静态符号绑定
    """

    bindings: dict[str, str | None] = {}
    _read_module_bindings(
        tree.body,
        bindings,
        module_name,
        is_package=is_package,
    )
    return PythonSymbolBindings(tuple(bindings.items()))


def read_python_call_facts(
    tree: ast.Module,
    module_name: str,
    *,
    is_package: bool = False,
) -> tuple[PythonCallFact, ...]:
    """
    返回一个模块内全部词法作用域的调用绑定快照
    """

    facts: list[PythonCallFact] = []
    _visit_statements(
        tree.body,
        {},
        module_name,
        module_name,
        facts,
        is_package=is_package,
    )
    return tuple(facts)


def _read_function_call_facts(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    module_bindings: PythonSymbolBindings,
    module_name: str,
) -> tuple[PythonCallFact, ...]:
    # 词法绑定按语句顺序生效并在控制流合流处以未知值失败关闭
    outer_bindings = dict(module_bindings.items())
    facts: list[PythonCallFact] = []
    bindings = dict(outer_bindings)
    for argument in (
        *function.args.posonlyargs,
        *function.args.args,
        *function.args.kwonlyargs,
    ):
        bindings[argument.arg] = None
    if function.args.vararg is not None:
        bindings[function.args.vararg.arg] = None
    if function.args.kwarg is not None:
        bindings[function.args.kwarg.arg] = None
    _visit_statements(
        function.body,
        bindings,
        module_name,
        function.name,
        facts,
        is_package=False,
    )
    return tuple(facts)


def _binding_view(
    bindings: dict[str, str | None],
) -> PythonSymbolBindings:
    return PythonSymbolBindings(tuple(bindings.items()))


def _read_module_bindings(
    statements: list[ast.stmt],
    bindings: dict[str, str | None],
    module_name: str,
    *,
    is_package: bool,
) -> None:
    for statement in statements:
        if isinstance(
            statement,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            bindings[statement.name] = f"{module_name}.{statement.name}"
            continue
        if isinstance(statement, (ast.Global, ast.Nonlocal)):
            raise PythonSymbolFactError(_GLOBAL_BINDING_UNSUPPORTED)
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            _apply_import(
                statement,
                bindings,
                module_name,
                is_package=is_package,
            )
            continue
        if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            _apply_statement_binding(
                statement,
                bindings,
                module_name,
                is_package=is_package,
            )
            continue
        branches: list[list[ast.stmt]] = []
        if isinstance(statement, ast.If):
            branches = [statement.body, statement.orelse]
        elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
            branches = [statement.body, statement.orelse]
        elif isinstance(statement, (ast.With, ast.AsyncWith)):
            branches = [statement.body]
        elif isinstance(statement, (ast.Try, ast.TryStar)):
            branches = [
                statement.body,
                *(handler.body for handler in statement.handlers),
                statement.orelse,
                statement.finalbody,
            ]
        elif isinstance(statement, ast.Match):
            branches = [case.body for case in statement.cases]
        if not branches:
            continue
        exits: list[dict[str, str | None]] = []
        for branch in branches:
            branch_bindings = dict(bindings)
            _read_module_bindings(
                branch,
                branch_bindings,
                module_name,
                is_package=is_package,
            )
            exits.append(branch_bindings)
        if isinstance(statement, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Match)):
            exits.append(dict(bindings))
        bindings.clear()
        bindings.update(_merge_bindings(exits))


def _from_base(
    statement: ast.ImportFrom,
    module_name: str,
    *,
    is_package: bool,
) -> str:
    if statement.level == 0:
        if statement.module is None:
            raise PythonSymbolFactError(_ABSOLUTE_IMPORT_WITHOUT_MODULE)
        return statement.module
    package_parts = (
        module_name.split(".")
        if is_package
        else module_name.split(".")[:-1]
    )
    anchor_length = len(package_parts) - statement.level + 1
    if anchor_length <= 0:
        raise PythonSymbolFactError(_RELATIVE_IMPORT_OUTSIDE_PACKAGE)
    base_parts = package_parts[:anchor_length]
    if statement.module:
        base_parts.extend(statement.module.split("."))
    return ".".join(base_parts)


def _apply_import(
    statement: ast.Import | ast.ImportFrom,
    bindings: dict[str, str | None],
    module_name: str,
    *,
    is_package: bool,
) -> None:
    if isinstance(statement, ast.Import):
        for alias in statement.names:
            local_name = alias.asname or alias.name.split(".")[0]
            bindings[local_name] = alias.name
        return
    base = _from_base(statement, module_name, is_package=is_package)
    for alias in statement.names:
        if alias.name == "*":
            raise PythonSymbolFactError(_WILDCARD_BINDING_UNKNOWN)
        bindings[alias.asname or alias.name] = f"{base}.{alias.name}"


def _target_names(target: ast.expr) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_target_names(element))
        return tuple(names)
    return ()


def _pattern_names(pattern: ast.pattern) -> tuple[str, ...]:
    return tuple(
        node.id
        for node in ast.walk(pattern)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    ) + tuple(
        node.name
        for node in ast.walk(pattern)
        if isinstance(node, ast.MatchAs) and node.name is not None
    )


def _apply_statement_binding(
    statement: ast.stmt,
    bindings: dict[str, str | None],
    module_name: str,
    *,
    is_package: bool,
) -> None:
    if isinstance(statement, (ast.Import, ast.ImportFrom)):
        _apply_import(
            statement,
            bindings,
            module_name,
            is_package=is_package,
        )
        return
    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        bindings[statement.name] = f"{module_name}.{statement.name}"
        return
    if isinstance(statement, (ast.Global, ast.Nonlocal)):
        raise PythonSymbolFactError(_GLOBAL_BINDING_UNSUPPORTED)
    if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        value = statement.value
        targets = (
            statement.targets
            if isinstance(statement, ast.Assign)
            else (statement.target,)
        )
        source = (
            None
            if value is None or isinstance(statement, ast.AugAssign)
            else resolve_expression_source(value, _binding_view(bindings))
        )
        for target in targets:
            for name in _target_names(target):
                bindings[name] = source if isinstance(target, ast.Name) else None


def _record_expression_calls(
    expression: ast.expr,
    bindings: dict[str, str | None],
    scope_name: str,
    facts: list[PythonCallFact],
) -> None:
    if isinstance(expression, ast.Call) and isinstance(
        expression.func,
        ast.NamedExpr,
    ):
        _record_expression_calls(
            expression.func.value,
            bindings,
            scope_name,
            facts,
        )
        source = resolve_expression_source(
            expression.func.value,
            _binding_view(bindings),
        )
        for name in _target_names(expression.func.target):
            bindings[name] = source
        facts.append(_call_fact(expression, bindings, scope_name, source))
        for argument in expression.args:
            _record_expression_calls(argument, bindings, scope_name, facts)
        for keyword in expression.keywords:
            _record_expression_calls(keyword.value, bindings, scope_name, facts)
        return
    if isinstance(expression, ast.Lambda):
        for default in (*expression.args.defaults, *expression.args.kw_defaults):
            if default is not None:
                _record_expression_calls(default, bindings, scope_name, facts)
        lambda_bindings = dict(bindings)
        for argument in (
            *expression.args.posonlyargs,
            *expression.args.args,
            *expression.args.kwonlyargs,
        ):
            lambda_bindings[argument.arg] = None
        if expression.args.vararg is not None:
            lambda_bindings[expression.args.vararg.arg] = None
        if expression.args.kwarg is not None:
            lambda_bindings[expression.args.kwarg.arg] = None
        _record_expression_calls(
            expression.body,
            lambda_bindings,
            f"{scope_name}.<lambda>",
            facts,
        )
        return
    if isinstance(
        expression,
        (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp),
    ):
        comprehension_bindings = dict(bindings)
        for generator in expression.generators:
            _record_expression_calls(
                generator.iter,
                comprehension_bindings,
                scope_name,
                facts,
            )
            for name in _target_names(generator.target):
                comprehension_bindings[name] = None
            for condition in generator.ifs:
                _record_expression_calls(
                    condition,
                    comprehension_bindings,
                    scope_name,
                    facts,
                )
        outputs = (
            (expression.key, expression.value)
            if isinstance(expression, ast.DictComp)
            else (expression.elt,)
        )
        for output in outputs:
            _record_expression_calls(
                output,
                comprehension_bindings,
                f"{scope_name}.<comprehension>",
                facts,
            )
        return
    if isinstance(expression, ast.NamedExpr):
        _record_expression_calls(expression.value, bindings, scope_name, facts)
        source = resolve_expression_source(
            expression.value,
            _binding_view(bindings),
        )
        for name in _target_names(expression.target):
            bindings[name] = source
        return
    if isinstance(expression, ast.Call):
        facts.append(
            _call_fact(
                expression,
                bindings,
                scope_name,
                resolve_expression_source(
                    expression.func,
                    _binding_view(bindings),
                ),
            )
        )
    for child in ast.iter_child_nodes(expression):
        if isinstance(child, ast.expr):
            _record_expression_calls(child, bindings, scope_name, facts)


def _call_fact(
    expression: ast.Call,
    bindings: dict[str, str | None],
    scope_name: str,
    source: str | None,
) -> PythonCallFact:
    view = _binding_view(bindings)
    return PythonCallFact(
        scope_name=scope_name,
        line=expression.lineno,
        source=source,
        positional_sources=tuple(
            resolve_expression_source(argument.func, view)
            if isinstance(argument, ast.Call)
            else resolve_expression_source(argument, view)
            for argument in expression.args
        ),
        keyword_names=tuple(
            keyword.arg for keyword in expression.keywords
        ),
    )


def _record_function_header_calls(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    bindings: dict[str, str | None],
    scope_name: str,
    facts: list[PythonCallFact],
) -> None:
    expressions = [
        *function.decorator_list,
        *function.args.defaults,
        *(
            default
            for default in function.args.kw_defaults
            if default is not None
        ),
    ]
    annotations = [
        argument.annotation
        for argument in (
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        )
        if argument.annotation is not None
    ]
    if function.args.vararg and function.args.vararg.annotation:
        annotations.append(function.args.vararg.annotation)
    if function.args.kwarg and function.args.kwarg.annotation:
        annotations.append(function.args.kwarg.annotation)
    if function.returns is not None:
        annotations.append(function.returns)
    for expression in (*expressions, *annotations):
        _record_expression_calls(expression, bindings, scope_name, facts)


def _merge_bindings(
    entries: list[dict[str, str | None]],
) -> dict[str, str | None]:
    names = set().union(*(entry.keys() for entry in entries))
    merged: dict[str, str | None] = {}
    for name in names:
        values = {entry.get(name) for entry in entries}
        merged[name] = values.pop() if len(values) == 1 else None
    return merged


def _visit_branch(
    statements: list[ast.stmt],
    entry_bindings: dict[str, str | None],
    module_name: str,
    scope_name: str,
    facts: list[PythonCallFact],
    *,
    is_package: bool,
) -> dict[str, str | None]:
    branch_bindings = dict(entry_bindings)
    _visit_statements(
        statements,
        branch_bindings,
        module_name,
        scope_name,
        facts,
        is_package=is_package,
    )
    return branch_bindings


def _visit_statements(
    statements: list[ast.stmt],
    bindings: dict[str, str | None],
    module_name: str,
    scope_name: str,
    facts: list[PythonCallFact],
    *,
    is_package: bool,
) -> None:
    for statement in statements:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _record_function_header_calls(
                statement,
                bindings,
                scope_name,
                facts,
            )
            nested_bindings = _binding_view(bindings)
            facts.extend(
                _read_function_call_facts(
                    statement,
                    nested_bindings,
                    module_name,
                )
            )
            bindings[statement.name] = f"{module_name}.{statement.name}"
            continue
        if isinstance(statement, ast.ClassDef):
            for expression in (
                *statement.decorator_list,
                *statement.bases,
                *(keyword.value for keyword in statement.keywords),
            ):
                _record_expression_calls(
                    expression,
                    bindings,
                    scope_name,
                    facts,
                )
            class_bindings = dict(bindings)
            for class_statement in statement.body:
                if isinstance(
                    class_statement,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    _record_function_header_calls(
                        class_statement,
                        bindings,
                        statement.name,
                        facts,
                    )
                    facts.extend(
                        _read_function_call_facts(
                            class_statement,
                            _binding_view(bindings),
                            module_name,
                        )
                    )
                    class_bindings[class_statement.name] = (
                        f"{module_name}.{class_statement.name}"
                    )
                    continue
                _visit_statements(
                    [class_statement],
                    class_bindings,
                    module_name,
                    statement.name,
                    facts,
                    is_package=False,
                )
            bindings[statement.name] = f"{module_name}.{statement.name}"
            continue
        if isinstance(statement, (ast.Global, ast.Nonlocal)):
            raise PythonSymbolFactError(_GLOBAL_BINDING_UNSUPPORTED)
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            _apply_import(
                statement,
                bindings,
                module_name,
                is_package=is_package,
            )
            continue
        if isinstance(statement, ast.Expr):
            _record_expression_calls(statement.value, bindings, scope_name, facts)
            continue
        if isinstance(statement, ast.Return) and statement.value is not None:
            _record_expression_calls(statement.value, bindings, scope_name, facts)
            continue
        if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            value = statement.value
            if value is not None:
                _record_expression_calls(value, bindings, scope_name, facts)
            _apply_statement_binding(
                statement,
                bindings,
                module_name,
                is_package=is_package,
            )
            continue
        if isinstance(statement, ast.If):
            _record_expression_calls(statement.test, bindings, scope_name, facts)
            exits = [
                _visit_branch(
                    statement.body,
                    bindings,
                    module_name,
                    scope_name,
                    facts,
                    is_package=is_package,
                ),
                _visit_branch(
                    statement.orelse,
                    bindings,
                    module_name,
                    scope_name,
                    facts,
                    is_package=is_package,
                ),
            ]
            bindings.clear()
            bindings.update(_merge_bindings(exits))
            continue
        if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
            loop_entry = dict(bindings)
            if isinstance(statement, (ast.For, ast.AsyncFor)):
                _record_expression_calls(
                    statement.iter,
                    bindings,
                    scope_name,
                    facts,
                )
                body_entry = dict(bindings)
                for name in _target_names(statement.target):
                    body_entry[name] = None
            else:
                _record_expression_calls(statement.test, bindings, scope_name, facts)
                body_entry = dict(bindings)
            body_exit = _visit_branch(
                statement.body,
                body_entry,
                module_name,
                scope_name,
                facts,
                is_package=is_package,
            )
            else_exit = _visit_branch(
                statement.orelse,
                bindings,
                module_name,
                scope_name,
                facts,
                is_package=is_package,
            )
            bindings.clear()
            bindings.update(_merge_bindings([loop_entry, body_exit, else_exit]))
            continue
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            body_entry = dict(bindings)
            for item in statement.items:
                _record_expression_calls(
                    item.context_expr,
                    body_entry,
                    scope_name,
                    facts,
                )
                if item.optional_vars is not None:
                    for name in _target_names(item.optional_vars):
                        body_entry[name] = None
            body_exit = _visit_branch(
                statement.body,
                body_entry,
                module_name,
                scope_name,
                facts,
                is_package=is_package,
            )
            bindings.clear()
            bindings.update(body_exit)
            continue
        if isinstance(statement, (ast.Try, ast.TryStar)):
            body_exit = _visit_branch(
                statement.body,
                bindings,
                module_name,
                scope_name,
                facts,
                is_package=is_package,
            )
            exits = [body_exit]
            for handler in statement.handlers:
                handler_entry = dict(bindings)
                if handler.type is not None:
                    _record_expression_calls(
                        handler.type,
                        handler_entry,
                        scope_name,
                        facts,
                    )
                if handler.name:
                    handler_entry[handler.name] = None
                exits.append(
                    _visit_branch(
                        handler.body,
                        handler_entry,
                        module_name,
                        scope_name,
                        facts,
                        is_package=is_package,
                    )
                )
            normal_exit = _visit_branch(
                statement.orelse,
                body_exit,
                module_name,
                scope_name,
                facts,
                is_package=is_package,
            )
            exits[0] = normal_exit
            merged = _merge_bindings(exits)
            final_exit = _visit_branch(
                statement.finalbody,
                merged,
                module_name,
                scope_name,
                facts,
                is_package=is_package,
            )
            bindings.clear()
            bindings.update(final_exit)
            continue
        if isinstance(statement, ast.Match):
            _record_expression_calls(statement.subject, bindings, scope_name, facts)
            exits = [dict(bindings)]
            for case in statement.cases:
                case_entry = dict(bindings)
                for name in _pattern_names(case.pattern):
                    case_entry[name] = None
                if case.guard is not None:
                    _record_expression_calls(
                        case.guard,
                        case_entry,
                        scope_name,
                        facts,
                    )
                exits.append(
                    _visit_branch(
                        case.body,
                        case_entry,
                        module_name,
                        scope_name,
                        facts,
                        is_package=is_package,
                    )
                )
            bindings.clear()
            bindings.update(_merge_bindings(exits))
            continue
        for child in ast.iter_child_nodes(statement):
            if isinstance(child, ast.expr):
                _record_expression_calls(child, bindings, scope_name, facts)

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from tests.architecture._python_symbol_facts import (
    PythonSymbolFactError,
    read_module_symbol_bindings,
    read_python_call_facts,
    resolve_expression_source,
)


def _call_sources(source: str) -> tuple[str | None, ...]:
    tree = ast.parse(source)
    return tuple(
        fact.source
        for fact in read_python_call_facts(
            tree,
            "package.module",
        )
    )


def test_module_bindings_resolve_absolute_aliases_and_relative_packages() -> None:
    """
    模块绑定同时覆盖绝对别名与包相对导入
    """

    module_tree = ast.parse(
        "import torch as tensor\n"
        "from package.physics import action as apply_action\n"
        "alias = apply_action\n"
    )
    bindings = read_module_symbol_bindings(module_tree, "package.module")
    assert bindings.source_for("tensor") == "torch"
    assert bindings.source_for("apply_action") == "package.physics.action"
    assert bindings.source_for("alias") == "package.physics.action"

    package_tree = ast.parse("from .runtime import Workstation\n")
    package_bindings = read_module_symbol_bindings(
        package_tree,
        "package",
        is_package=True,
    )
    assert package_bindings.source_for("Workstation") == (
        "package.runtime.Workstation"
    )


def test_call_facts_follow_local_imports_aliases_and_execution_order() -> None:
    """
    局部导入和重绑定按语句位置解析
    """

    sources = _call_sources(
        "import torch\n"
        "def evaluate(angle):\n"
        "    import torch as tensor\n"
        "    polar = tensor.polar\n"
        "    polar(angle)\n"
        "    polar = replacement\n"
        "    polar(angle)\n"
    )
    assert sources == ("torch.polar", None)


def test_parameters_and_unknown_assignments_shadow_outer_bindings() -> None:
    """
    参数和未知赋值以失败关闭方式遮蔽外层绑定
    """

    assert _call_sources(
        "import torch\n"
        "def evaluate(torch, angle):\n"
        "    torch.polar(angle)\n"
    ) == (None,)
    assert _call_sources(
        "import torch\n"
        "def evaluate(angle):\n"
        "    builder = choose_builder()\n"
        "    builder(angle)\n"
    ) == (None, None)


def test_nested_scopes_do_not_rewrite_outer_bindings() -> None:
    """
    嵌套作用域不污染外层绑定
    """

    assert _call_sources(
        "import torch\n"
        "def evaluate(angle):\n"
        "    def nested(torch):\n"
        "        torch.polar(angle)\n"
        "    torch.polar(angle)\n"
    ) == (None, "torch.polar")
    assert _call_sources(
        "import torch\n"
        "async def evaluate(angle):\n"
        "    torch.polar(angle)\n"
    ) == ("torch.polar",)
    assert _call_sources(
        "import torch\n"
        "def evaluate(angle):\n"
        "    deferred = lambda: replacement.polar(angle)\n"
        "    torch.polar(angle)\n"
    ) == (None, "torch.polar")


@pytest.mark.parametrize(
    "expression",
    (
        "lambda: OpticalField()",
        "[OpticalField() for item in values]",
        "(OpticalField() for item in values)",
        "lambda: torch.polar(one, angle)",
        "[torch.polar(one, angle) for item in values]",
        "(torch.polar(one, angle) for item in values)",
    ),
)
def test_deferred_scopes_preserve_policy_relevant_calls(expression: str) -> None:
    """
    延迟作用域中的调用保持可见
    """

    source = (
        "import torch\n"
        "from package.field import OpticalField\n"
        "def evaluate(values, one, angle):\n"
        f"    return {expression}\n"
    )
    expected = (
        "package.field.OpticalField"
        if "OpticalField" in expression
        else "torch.polar"
    )
    assert expected in _call_sources(source)


def test_function_headers_preserve_policy_relevant_calls() -> None:
    """
    装饰器、默认值与注解中的调用保持可见
    """

    sources = _call_sources(
        "import torch\n"
        "from package.field import OpticalField\n"
        "@decorate(OpticalField())\n"
        "def evaluate(value=OpticalField(), annotation: build_type() = None):\n"
        "    return value\n"
    )
    assert sources.count("package.field.OpticalField") == 2
    assert "decorate" not in sources
    assert sources.count(None) >= 2


def test_branch_calls_use_entry_binding_before_rebinding() -> None:
    """
    分支内调用使用其语句位置的入口绑定
    """

    sources = _call_sources(
        "import torch\n"
        "def evaluate(angle, condition):\n"
        "    if condition:\n"
        "        torch.polar(angle)\n"
        "        torch = replacement\n"
        "    else:\n"
        "        torch.polar(angle)\n"
    )
    assert sources == ("torch.polar", "torch.polar")


def test_module_conditional_binding_merges_fail_closed() -> None:
    """
    模块分支绑定在出口保守合并
    """

    tree = ast.parse(
        "import torch\n"
        "if condition:\n"
        "    torch = replacement\n"
    )
    bindings = read_module_symbol_bindings(tree, "package.module")
    assert bindings.has_binding("torch")
    assert bindings.source_for("torch") is None


@pytest.mark.parametrize(
    ("import_statement", "class_binding", "call_source"),
    (
        ("import torch", "torch = replacement", "torch.polar"),
        (
            "from package.field import OpticalField",
            "OpticalField = replacement",
            "package.field.OpticalField",
        ),
    ),
)
def test_method_bare_names_use_module_globals_not_class_bindings(
    import_statement: str,
    class_binding: str,
    call_source: str,
) -> None:
    """
    方法裸名称跳过类命名空间并读取模块全局绑定
    """

    leaf_name = call_source.rsplit(".", 1)[-1]
    expression = (
        "torch.polar(angle)"
        if leaf_name == "polar"
        else "OpticalField()"
    )
    source = (
        f"{import_statement}\n"
        "class Example:\n"
        f"    {class_binding}\n"
        "    def evaluate(self, angle):\n"
        f"        return {expression}\n"
    )
    assert call_source in _call_sources(source)


def test_class_body_expression_uses_class_namespace() -> None:
    """
    类体直接表达式读取类命名空间
    """

    sources = _call_sources(
        "import torch\n"
        "class Example:\n"
        "    polar = torch.polar\n"
        "    sample = polar(angle)\n"
    )
    assert "torch.polar" in sources


@pytest.mark.parametrize(
    ("binding_expression", "expected_source"),
    (
        ("torch.polar", "torch.polar"),
        ("OpticalField", "package.field.OpticalField"),
        ("unknown", None),
    ),
)
def test_direct_walrus_callee_uses_value_source(
    binding_expression: str,
    expected_source: str | None,
) -> None:
    """
    直接海象调用先绑定值来源再记录调用目标
    """

    source = (
        "import torch\n"
        "from package.field import OpticalField\n"
        "def evaluate(value):\n"
        f"    return (action := {binding_expression})(value)\n"
    )
    assert _call_sources(source)[0] == expected_source


def test_walrus_call_fact_preserves_nested_positional_sources() -> None:
    """
    海象调用与普通调用共享位置参数来源
    """

    tree = ast.parse(
        "import torch\n"
        "def evaluate(phase):\n"
        "    return (builder := torch.complex)(\n"
        "        torch.cos(phase), torch.sin(phase)\n"
        "    )\n"
    )
    outer = read_python_call_facts(tree, "package.module")[0]
    assert outer.source == "torch.complex"
    assert outer.positional_sources == ("torch.cos", "torch.sin")


def test_alias_cycles_terminate_without_inventing_a_qualified_source() -> None:
    """
    未定义别名链不产生虚假限定来源
    """

    tree = ast.parse("first = second\nsecond = first\n")
    bindings = read_module_symbol_bindings(tree, "package.module")
    assert bindings.source_for("first") is None
    assert bindings.source_for("second") is None


def test_conditional_rebinding_fails_closed_after_the_branch() -> None:
    """
    条件重绑定后的来源保持失败关闭
    """

    assert _call_sources(
        "import torch\n"
        "def evaluate(angle, condition):\n"
        "    if condition:\n"
        "        torch = replacement\n"
        "    torch.polar(angle)\n"
    ) == (None,)
    assert _call_sources(
        "import torch\n"
        "def evaluate(angle):\n"
        "    try:\n"
        "        torch = replacement\n"
        "    except RuntimeError:\n"
        "        pass\n"
        "    torch.polar(angle)\n"
    ) == (None,)
    assert _call_sources(
        "import torch\n"
        "def evaluate(values, angle):\n"
        "    for torch in values:\n"
        "        torch.polar(angle)\n"
    ) == (None,)


@pytest.mark.parametrize(
    "source",
    (
        "from package import *\n",
        "from ....package import action\n",
        "value = 1\nglobal value\n",
    ),
)
def test_unsupported_binding_shapes_fail_closed(source: str) -> None:
    """
    不支持的绑定形状稳定失败关闭
    """

    with pytest.raises(PythonSymbolFactError):
        read_module_symbol_bindings(ast.parse(source), "package.module")


def test_expression_resolution_is_narrow_and_binding_facts_are_immutable() -> None:
    """
    表达式解析保持狭窄且绑定事实不可变
    """

    tree = ast.parse("import torch\n")
    bindings = read_module_symbol_bindings(tree, "package.module")
    assert resolve_expression_source(
        ast.parse("torch.polar", mode="eval").body,
        bindings,
    ) == "torch.polar"
    assert resolve_expression_source(
        ast.parse("factory()", mode="eval").body,
        bindings,
    ) is None
    assert resolve_expression_source(
        ast.parse("items[0]", mode="eval").body,
        bindings,
    ) is None
    mutable_view: Any = bindings
    with pytest.raises(FrozenInstanceError):
        mutable_view.entries = ()


def test_shared_owner_has_two_consumers_without_policy_or_duplicate_resolvers() -> None:
    """
    共享所有者服务两个消费者且不吸收政策
    """

    architecture = Path("tests/architecture")
    consumers = (
        architecture / "test_dependency_ownership.py",
        architecture / "test_phase_authority.py",
    )
    for path in consumers:
        source = path.read_text(encoding="utf-8")
        assert "_python_symbol_facts import" in source
        assert "def _resolve_expression_source" not in source
        assert "def _read_symbol_bindings" not in source
        assert "def _read_function_bindings" not in source

    shared_source = (architecture / "_python_symbol_facts.py").read_text(
        encoding="utf-8",
    )
    for policy_word in (
        "chromatix_next",
        "Workstation",
        "phasor",
        "field",
        "forbidden",
        "allowlist",
        "threshold",
        "finding",
    ):
        assert policy_word not in shared_source

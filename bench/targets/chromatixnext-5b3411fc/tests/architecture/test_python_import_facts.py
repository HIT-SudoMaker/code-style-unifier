from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tests.architecture._python_import_facts import (
    PythonImportFactError,
    inspect_python_imports,
    read_python_imports,
)


def test_absolute_imports_report_modules_targets_and_bindings() -> None:
    """
    绝对导入分别报告模块、目标与本地绑定
    """

    facts = inspect_python_imports(
        "import alpha.beta as dependency\nfrom gamma import delta as value\n",
        module_name="package.consumer",
        is_package=False,
    )

    assert facts.imported_modules == frozenset({"alpha.beta", "gamma"})
    assert facts.imported_targets == frozenset({"alpha.beta", "gamma.delta"})
    assert facts.local_bindings == frozenset({"dependency", "value"})
    assert facts.runtime_imported_modules == facts.imported_modules
    assert facts.runtime_imported_targets == facts.imported_targets
    assert facts.runtime_local_bindings == facts.local_bindings


def test_direct_type_checking_body_is_static_only() -> None:
    """
    直接 TYPE_CHECKING 主体仅进入完整静态投影
    """

    facts = inspect_python_imports(
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from package.types import Model\n",
        module_name="package.consumer",
        is_package=False,
    )

    assert "package.types.Model" in facts.imported_targets
    assert "package.types.Model" not in facts.runtime_imported_targets


def test_qualified_type_checking_else_remains_runtime() -> None:
    """
    typing.TYPE_CHECKING 主体排除而 else 导入保留在运行投影
    """

    facts = inspect_python_imports(
        "import typing\n"
        "if typing.TYPE_CHECKING:\n"
        "    import package.static_model\n"
        "else:\n"
        "    import package.runtime_model as model\n",
        module_name="package.consumer",
        is_package=False,
    )

    assert "package.static_model" in facts.imported_modules
    assert "package.static_model" not in facts.runtime_imported_modules
    assert "package.runtime_model" in facts.runtime_imported_modules
    assert "model" in facts.runtime_local_bindings


def test_nested_type_checking_body_stays_static_only() -> None:
    """
    TYPE_CHECKING 内嵌条件的全部导入仍只属于静态投影
    """

    facts = inspect_python_imports(
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    if condition:\n"
        "        import package.nested\n"
        "    else:\n"
        "        import package.alternate\n",
        module_name="package.consumer",
        is_package=False,
    )

    assert {"package.nested", "package.alternate"} <= facts.imported_modules
    assert not {
        "package.nested",
        "package.alternate",
    }.intersection(facts.runtime_imported_modules)


@pytest.mark.parametrize(
    ("binding", "guard"),
    (
        ("from typing import TYPE_CHECKING as checking", "checking"),
        ("import typing as typing_module", "typing_module.TYPE_CHECKING"),
    ),
)
def test_canonical_type_checking_aliases_are_resolved(
    binding: str,
    guard: str,
) -> None:
    """
    标准 typing 哨兵别名按真实绑定排除运行导入
    """

    facts = inspect_python_imports(
        f"{binding}\nif {guard}:\n    import package.static_only\n",
        module_name="package.consumer",
        is_package=False,
    )
    assert "package.static_only" in facts.imported_modules
    assert "package.static_only" not in facts.runtime_imported_modules


@pytest.mark.parametrize(
    "source",
    (
        "TYPE_CHECKING = True\nif TYPE_CHECKING:\n    import package.runtime\n",
        "from external import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import package.runtime\n",
        "import external as typing\n"
        "if typing.TYPE_CHECKING:\n    import package.runtime\n",
        "from typing import TYPE_CHECKING\n"
        "TYPE_CHECKING = True\n"
        "if TYPE_CHECKING:\n    import package.runtime\n",
        "import typing\n"
        "typing = replacement\n"
        "if typing.TYPE_CHECKING:\n    import package.runtime\n",
        "from typing import TYPE_CHECKING\n"
        "def TYPE_CHECKING():\n    return True\n"
        "if TYPE_CHECKING:\n    import package.runtime\n",
        "import typing as typing_module\n"
        "class typing_module:\n    TYPE_CHECKING = True\n"
        "if typing_module.TYPE_CHECKING:\n    import package.runtime\n",
        "from typing import TYPE_CHECKING\n"
        "from external import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import package.runtime\n",
        "from typing import TYPE_CHECKING\n"
        "if condition:\n    TYPE_CHECKING = True\n"
        "if TYPE_CHECKING:\n    import package.runtime\n",
    ),
)
def test_noncanonical_or_shadowed_guards_keep_runtime_edges(source: str) -> None:
    """
    非标准或被遮蔽哨兵保守保留真实运行依赖
    """

    facts = inspect_python_imports(
        source,
        module_name="package.consumer",
        is_package=False,
    )
    assert "package.runtime" in facts.runtime_imported_modules


@pytest.mark.parametrize(
    "nested_scope",
    (
        "def evaluate():\n"
        "    TYPE_CHECKING = True\n"
        "    if TYPE_CHECKING:\n"
        "        import package.runtime\n",
        "def evaluate():\n"
        "    from external import TYPE_CHECKING\n"
        "    if TYPE_CHECKING:\n"
        "        import package.runtime\n",
        "class Evaluation:\n"
        "    TYPE_CHECKING = True\n"
        "    if TYPE_CHECKING:\n"
        "        import package.runtime\n",
        "class Evaluation:\n"
        "    from external import TYPE_CHECKING\n"
        "    if TYPE_CHECKING:\n"
        "        import package.runtime\n",
    ),
)
def test_nested_scopes_never_inherit_module_type_checking_sentinel(
    nested_scope: str,
) -> None:
    """
    普通函数与类作用域不借用模块哨兵排除运行时依赖
    """

    facts = inspect_python_imports(
        "from typing import TYPE_CHECKING\n" + nested_scope,
        module_name="package.consumer",
        is_package=False,
    )
    assert "package.runtime" in facts.runtime_imported_modules


@pytest.mark.parametrize(
    "nested_scope",
    (
        "def evaluate():\n"
        "    if typing_module.TYPE_CHECKING:\n"
        "        import package.runtime\n",
        "class Evaluation:\n"
        "    if typing_module.TYPE_CHECKING:\n"
        "        import package.runtime\n",
    ),
)
def test_nested_qualified_guards_remain_runtime_visible(
    nested_scope: str,
) -> None:
    """
    嵌套作用域中的限定哨兵也不触发模块级运行时排除
    """

    facts = inspect_python_imports(
        "import typing as typing_module\n" + nested_scope,
        module_name="package.consumer",
        is_package=False,
    )
    assert "package.runtime" in facts.runtime_imported_modules


@pytest.mark.parametrize(
    "compound_statement",
    (
        "if condition:\n"
        "    from external import TYPE_CHECKING\n"
        "    if TYPE_CHECKING:\n"
        "        import package.runtime\n",
        "try:\n"
        "    from external import TYPE_CHECKING\n"
        "    if TYPE_CHECKING:\n"
        "        import package.runtime\n"
        "except ImportError:\n"
        "    pass\n",
        "for item in items:\n"
        "    from external import TYPE_CHECKING\n"
        "    if TYPE_CHECKING:\n"
        "        import package.runtime\n",
        "while condition:\n"
        "    from external import TYPE_CHECKING\n"
        "    if TYPE_CHECKING:\n"
        "        import package.runtime\n",
        "with context:\n"
        "    from external import TYPE_CHECKING\n"
        "    if TYPE_CHECKING:\n"
        "        import package.runtime\n",
        "match subject:\n"
        "    case _:\n"
        "        from external import TYPE_CHECKING\n"
        "        if TYPE_CHECKING:\n"
        "            import package.runtime\n",
    ),
)
def test_compound_statement_guards_never_hide_runtime_edges(
    compound_statement: str,
) -> None:
    """
    复合语句内部的重绑定与哨兵不由模块级投影解释
    """

    facts = inspect_python_imports(
        "from typing import TYPE_CHECKING\n" + compound_statement,
        module_name="package.consumer",
        is_package=False,
    )
    assert "package.runtime" in facts.runtime_imported_modules


@pytest.mark.parametrize(
    "conditional_rebinding",
    (
        "if condition:\n    from external import TYPE_CHECKING\n",
        "try:\n    from external import TYPE_CHECKING\n"
        "except ImportError:\n    pass\n",
        "match subject:\n"
        "    case True:\n"
        "        from external import TYPE_CHECKING\n",
        "match subject:\n    case TYPE_CHECKING:\n        pass\n",
    ),
)
def test_possible_module_rebinding_keeps_later_runtime_edge(
    conditional_rebinding: str,
) -> None:
    """
    模块复合语句任一分支可能重绑哨兵时后续依赖保守可见
    """

    facts = inspect_python_imports(
        "from typing import TYPE_CHECKING\n"
        + conditional_rebinding
        + "if TYPE_CHECKING:\n    import package.runtime\n",
        module_name="package.consumer",
        is_package=False,
    )
    assert "package.runtime" in facts.runtime_imported_modules


def test_relative_imports_resolve_from_module_package() -> None:
    """
    相对导入以当前模块的包语境解析
    """

    facts = inspect_python_imports(
        "from .sibling import value\nfrom ..shared import other\n",
        module_name="package.feature.consumer",
        is_package=False,
    )

    assert facts.imported_modules == frozenset(
        {"package.feature.sibling", "package.shared"},
    )


def test_package_relative_import_anchors_at_package_itself() -> None:
    """
    相对导入解析包上下文
    """

    facts = inspect_python_imports(
        "from .child import PublicName\n",
        module_name="package.feature",
        is_package=True,
    )

    assert facts.imported_targets == frozenset(
        {"package.feature.child.PublicName"},
    )


def test_wildcard_import_records_explicit_unknown_binding() -> None:
    """
    通配导入保留显式未知绑定而不猜测运行时名称
    """

    facts = inspect_python_imports(
        "from package.module import *\n",
        module_name="consumer",
        is_package=False,
    )

    assert facts.imported_targets == frozenset({"package.module.*"})
    assert facts.local_bindings == frozenset({"*"})


def test_facts_are_immutable() -> None:
    """
    导入事实对象在建立后不可变
    """

    facts = inspect_python_imports(
        "import dependency\n",
        module_name="consumer",
        is_package=False,
    )

    with pytest.raises(FrozenInstanceError):
        facts.module_name = "replacement"  # type: ignore[misc]


def test_syntax_error_fails_closed() -> None:
    """
    语法错误以稳定事实异常闭合失败
    """

    with pytest.raises(PythonImportFactError, match="cannot parse import facts"):
        inspect_python_imports(
            "from package import\n",
            module_name="consumer",
            is_package=False,
        )


def test_relative_import_above_package_fails_closed() -> None:
    """
    越过包顶层的相对导入闭合失败
    """

    with pytest.raises(PythonImportFactError, match="escapes above"):
        inspect_python_imports(
            "from ...outside import value\n",
            module_name="package.consumer",
            is_package=False,
        )


def test_invalid_module_context_fails_closed() -> None:
    """
    非法模块语境不产生猜测性的导入事实
    """

    with pytest.raises(PythonImportFactError, match="non-keyword"):
        inspect_python_imports(
            "import dependency\n",
            module_name="package.class",
            is_package=False,
        )


def test_reader_derives_module_name_and_package_context(tmp_path: Path) -> None:
    """
    文件读取入口从源根推导模块名与包语境
    """

    package = tmp_path / "sample"
    package.mkdir()
    source = package / "__init__.py"
    source.write_text("from .child import PublicName\n", encoding="utf-8")

    facts = read_python_imports(source, tmp_path)

    assert facts.module_name == "sample"
    assert facts.imported_targets == frozenset({"sample.child.PublicName"})


def test_reader_rejects_paths_outside_source_root(tmp_path: Path) -> None:
    """
    文件读取入口拒绝源根之外的路径
    """

    source_root = tmp_path / "source"
    source_root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("import dependency\n", encoding="utf-8")

    with pytest.raises(PythonImportFactError, match="outside source root"):
        read_python_imports(outside, source_root)


def test_reader_rejects_non_file_paths(tmp_path: Path) -> None:
    """
    文件读取入口拒绝目录等非普通文件
    """

    package = tmp_path / "package"
    package.mkdir()

    with pytest.raises(PythonImportFactError, match="not a regular file"):
        read_python_imports(package, tmp_path)

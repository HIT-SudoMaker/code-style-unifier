from __future__ import annotations

import ast
from pathlib import Path
import re

import pytest

from tests.architecture._python_import_facts import (
    PythonImportFactError,
    inspect_python_imports,
    read_python_imports,
)
from tests.architecture._python_symbol_facts import (
    PythonCallFact,
    read_module_symbol_bindings,
    read_python_call_facts,
)

PACKAGE = Path("src/chromatix_next")


OPTICS = PACKAGE / "optics"


NUMERICS = PACKAGE / "_numerics"


ROLE_NAMES = (
    "source",
    "element",
    "propagation",
    "combination",
    "detection",
)

def _field_call_sites(
    source: str,
    module_name: str,
) -> tuple[PythonCallFact, ...]:
    tree = ast.parse(source)
    sites = [
        call
        for call in read_python_call_facts(tree, module_name)
        if call.source
        in {
            "chromatix_next.optics.field.OpticalField",
            "chromatix_next.optics.field._transform_field",
        }
    ]
    return tuple(sites)


def _nested_binding_names(tree: ast.Module) -> tuple[str, ...]:
    # 消费者本地策略：递归收集定义与赋值绑定名（导入绑定归 import facts 所有）
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            names.extend(
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(
            node.target,
            ast.Name,
        ):
            names.append(node.target.id)
    return tuple(names)


def _name_words(name: str) -> tuple[str, ...]:
    words: list[str] = []
    for segment in name.split("_"):
        words.extend(
            match.casefold()
            for match in re.findall(
                r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+",
                segment,
            )
        )
    return tuple(words)


def _governance_findings(
    source: str,
    module_name: str,
    *,
    is_package: bool = False,
) -> tuple[str, ...]:
    tree = ast.parse(source)
    import_facts = inspect_python_imports(source, module_name, is_package)
    bound_names = (
        *sorted(import_facts.local_bindings),
        *_nested_binding_names(tree),
    )
    forbidden_words = {
        "propagator",
        "strategy",
        "solver",
        "registry",
        "provider",
        "manager",
        "family",
        "capability",
    }
    test_words = {
        "evidence",
        "fake",
        "fixture",
        "mock",
        "test",
        "testing",
    }
    findings = [
        f"forbidden_binding:{name}"
        for name in bound_names
        if not name.startswith("_")
        and (
            bool(forbidden_words.intersection(_name_words(name)))
            or "componentbase"
            in "".join(_name_words(name))
        )
    ]
    findings.extend(
        f"test_binding:{name}"
        for name in bound_names
        if not name.startswith("_")
        and bool(test_words.intersection(_name_words(name)))
    )
    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ) or node.name.startswith("_"):
            continue
        parent_class = next(
            (
                candidate
                for candidate in tree.body
                if isinstance(candidate, ast.ClassDef)
                and node in candidate.body
            ),
            None,
        )
        is_workstation_run = (
            module_name == "chromatix_next.workstation"
            and parent_class is not None
            and parent_class.name == "Workstation"
            and node.name == "run"
        )
        if node.name in {"run", "execute", "simulate", "replay"} and not (
            is_workstation_run
        ):
            findings.append(f"second_run:{node.name}")
    bindings = read_module_symbol_bindings(
        tree,
        module_name,
        is_package=is_package,
    )
    for local_name, binding in bindings.items():
        if binding not in {
            "chromatix_next.workstation.Workstation",
            "chromatix_next.workstation.Workstation.run",
        }:
            continue
        if local_name.startswith("_") or (
            binding == "chromatix_next.workstation.Workstation"
            and local_name == "Workstation"
        ):
            continue
        findings.append(
            f"compatibility_alias:{local_name}",
        )
    for dependency in import_facts.imported_modules:
        if (
            dependency == "tests"
            or dependency.startswith("tests.")
            or dependency == "chromatix_next.evidence"
            or dependency.startswith("chromatix_next.evidence.")
        ):
            findings.append(f"test_dependency:{dependency}")
    return tuple(findings)


def test_dependency_direction_and_numerical_ownership_are_closed() -> None:
    """
    每个数值模块都能反向追溯到生产物理所有者
    """

    production_paths = tuple(PACKAGE.rglob("*.py"))
    imports: dict[str, frozenset[str]] = {}
    package_modules: set[str] = set()
    for path in production_paths:
        facts = read_python_imports(
            path,
            PACKAGE.parent,
        )
        imports[facts.module_name] = facts.imported_modules
        if path.name == "__init__.py":
            package_modules.add(facts.module_name)
    reverse_dependencies = {
        module_name: {
            consumer
            for consumer, dependencies in imports.items()
            if module_name in dependencies
        }
        for module_name in imports
    }
    physics_prefixes = (
        "chromatix_next.optics.source.",
        "chromatix_next.optics.element.",
        "chromatix_next.optics.propagation.",
        "chromatix_next.optics.combination.",
        "chromatix_next.optics.detection.",
    )
    for numerical_module in reverse_dependencies:
        if (
            not numerical_module.startswith("chromatix_next._numerics.")
            or numerical_module in package_modules
        ):
            continue
        reached = {numerical_module}
        frontier = [numerical_module]
        while frontier:
            dependency = frontier.pop()
            for consumer in reverse_dependencies[dependency]:
                if consumer in reached:
                    continue
                reached.add(consumer)
                frontier.append(consumer)
        assert any(
            owner.startswith(physics_prefixes)
            for owner in reached
        ), f"{numerical_module} has no production physics owner"


def test_private_numerics_has_no_public_reexport() -> None:
    """
    私有数值包不定义聚合出口且公共包入口不转发数值符号
    """

    numerics_init = ast.parse(
        (NUMERICS / "__init__.py").read_text(encoding="utf-8"),
    )
    assert not any(
        isinstance(statement, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "__all__"
            for target in statement.targets
        )
        for statement in numerics_init.body
    )
    for init_path in (
        PACKAGE / "__init__.py",
        OPTICS / "__init__.py",
        *(OPTICS / role / "__init__.py" for role in ROLE_NAMES),
    ):
        assert all(
            not dependency.startswith("chromatix_next._numerics")
            for dependency in read_python_imports(
                init_path,
                PACKAGE.parent,
            ).imported_modules
        )


def test_field_transformation_has_one_constructor_authority() -> None:
    """
    验证派生光场只经唯一命名变换权威，采样波只经一个私有构造权威

    断言约束职责而不冻结私有模块、基类或方法的名字。
    """

    transformation_definitions: list[tuple[Path, int]] = []
    constructor_sites: list[tuple[Path, str]] = []
    transformation_calls: list[tuple[Path, PythonCallFact]] = []
    for path in OPTICS.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        transformation_definitions.extend(
            (path, node.lineno)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_transform_field"
        )
        for call in _field_call_sites(
            path.read_text(encoding="utf-8"),
            read_python_imports(
                path,
                PACKAGE.parent,
            ).module_name,
        ):
            if call.source and call.source.endswith(".OpticalField"):
                constructor_sites.append((path, call.scope_name))
            else:
                transformation_calls.append((path, call))

    assert [
        path.relative_to(OPTICS).as_posix()
        for path, _line in transformation_definitions
    ] == ["field.py"]
    relative_constructor_sites = {
        (
            path.relative_to(OPTICS).as_posix(),
            scope_name,
        )
        for path, scope_name in constructor_sites
    }
    assert ("field.py", "_transform_field") in relative_constructor_sites

    sampled_source_paths = {
        "source/gaussian_beam.py",
        "source/plane_wave.py",
        "source/point_source.py",
    }
    assert not {
        path
        for path, _scope_name in relative_constructor_sites
        if path in sampled_source_paths
    }

    private_constructor_sites = {
        (path, scope_name)
        for path, scope_name in relative_constructor_sites
        if path.startswith("_")
    }
    assert len(private_constructor_sites) == 1
    private_path, private_scope = next(iter(private_constructor_sites))
    assert private_path.endswith(".py")
    assert private_scope.startswith("_")

    allowed_constructor_sites = private_constructor_sites | {
        ("field.py", "_transform_field"),
    }
    assert relative_constructor_sites == allowed_constructor_sites
    assert transformation_calls
    for path, call in transformation_calls:
        keywords = set(call.keyword_names)
        assert "envelope" in keywords
        if path.parent.name == "propagation":
            assert {"grid", "path_reference"} <= keywords
        if path.name in {
            "aplanatic_focus.py",
            "vector_angular_spectrum.py",
        }:
            assert "polarization_representation" in keywords


def test_field_authority_gate_resolves_constructor_bindings() -> None:
    """
    派生光场别名仍经唯一命名变换权威
    """

    sources = (
        """
from chromatix_next.optics.field import OpticalField
Field = OpticalField

def derive():
    return Field()
""",
        """
import chromatix_next.optics.field as field_module

def derive():
    return field_module.OpticalField()
""",
    )
    for source in sources:
        sites = _field_call_sites(
            source,
            "chromatix_next.optics.counterfactual",
        )
        assert len(sites) == 1
        assert sites[0].source == "chromatix_next.optics.field.OpticalField"


def test_no_generic_governance_surface() -> None:
    """
    工作站公开面与唯一运行入口保持冻结
    """

    findings: list[str] = []
    for path in PACKAGE.rglob("*.py"):
        findings.extend(
            _governance_findings(
                path.read_text(encoding="utf-8"),
                read_python_imports(
                    path,
                    PACKAGE.parent,
                ).module_name,
                is_package=path.name == "__init__.py",
            ),
        )
    assert not findings


def test_governance_gate_covers_aliases_and_second_runtime() -> None:
    """
    治理门覆盖全部公开绑定但不误杀私有辅助函数
    """

    source = """
from chromatix_next.workstation import Workstation
from chromatix_next.workstation import Workstation as AlternateWorkstation
from tests.reference import known_result

execute = Workstation.run
Solver = Workstation
annotated_execute: object = Workstation.run
PublicEvidence = known_result

class AlternateRuntime:
    def replay(self):
        return None

def _execute():
    return None
"""
    findings = _governance_findings(
        source,
        "chromatix_next.counterfactual",
    )
    assert "compatibility_alias:execute" in findings
    assert "compatibility_alias:Solver" in findings
    assert "compatibility_alias:annotated_execute" in findings
    assert "compatibility_alias:AlternateWorkstation" in findings
    assert "second_run:replay" in findings
    assert "test_dependency:tests.reference" in findings
    assert "test_binding:PublicEvidence" in findings
    assert "second_run:_execute" not in findings


def test_governance_bindings_cover_relative_imports_in_package() -> None:
    """
    包锚点下的相对导入绑定名进入治理门且模块名本身不绑定
    """

    source = (
        "from .sibling import Strategy\n"
        "from .. import provider\n"
        "from . import nested_capability as capability_alias\n"
    )
    findings = _governance_findings(
        source,
        "chromatix_next.optics.feature",
        is_package=True,
    )
    assert set(findings) == {
        "forbidden_binding:Strategy",
        "forbidden_binding:provider",
        "forbidden_binding:capability_alias",
    }


def test_governance_bindings_cover_relative_imports_in_module() -> None:
    """
    普通模块锚点下的相对导入别名与下划线豁免保持治理语义
    """

    source = (
        "from .registry import solver as SolverAlias\n"
        "from .. import manager\n"
        "from .base import BaseSolver as _base\n"
    )
    findings = _governance_findings(
        source,
        "chromatix_next.optics.element.lens",
    )
    assert set(findings) == {
        "forbidden_binding:SolverAlias",
        "forbidden_binding:manager",
    }


def test_governance_bindings_prefer_alias_over_member_path() -> None:
    """
    asname 别名优先成为绑定名而无别名的点路径只绑定首段
    """

    source = (
        "import chromatix_next.optics.registry as Registry\n"
        "import chromatix_next.optics.registry\n"
        "from chromatix_next.workstation import Workstation as Manager\n"
    )
    findings = _governance_findings(
        source,
        "chromatix_next.counterfactual",
    )
    assert set(findings) == {
        "forbidden_binding:Registry",
        "forbidden_binding:Manager",
        "compatibility_alias:Manager",
    }


def test_governance_bindings_reach_nested_scopes() -> None:
    """
    函数与类体内的导入、赋值、注解赋值和 TYPE_CHECKING 导入全部可见
    """

    source = (
        "from typing import TYPE_CHECKING\n"
        "\n"
        "def outer():\n"
        "    from .sibling import Strategy\n"
        "    local_solver = 1\n"
        "\n"
        "    def inner_registry():\n"
        "        return None\n"
        "\n"
        "class Holder:\n"
        "    from .other import manager as nested_manager\n"
        "\n"
        "    annotated_capability: object = None\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from .static import Provider\n"
    )
    findings = _governance_findings(
        source,
        "chromatix_next.counterfactual",
    )
    assert set(findings) == {
        "forbidden_binding:Strategy",
        "forbidden_binding:local_solver",
        "forbidden_binding:inner_registry",
        "forbidden_binding:nested_manager",
        "forbidden_binding:annotated_capability",
        "forbidden_binding:Provider",
    }


def test_governance_fails_closed_on_relative_import_escape() -> None:
    """
    越过包顶层的相对导入以导入事实异常闭合失败
    """

    with pytest.raises(PythonImportFactError, match="escapes above"):
        _governance_findings(
            "from ...outside import Strategy\n",
            "chromatix_next.counterfactual",
        )

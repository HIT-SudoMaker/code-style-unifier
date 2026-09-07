from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture._python_import_facts import read_python_imports
from tests.architecture._python_symbol_facts import read_python_call_facts

PACKAGE = Path("src/chromatix_next")


NUMERICS = PACKAGE / "_numerics"

def _unit_phasor_definition_sites() -> list[tuple[str, int]]:
    sites: list[tuple[str, int]] = []
    for path in NUMERICS.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_unit_phasor_from_cycles"
            ):
                module_name = read_python_imports(
                    path,
                    PACKAGE.parent,
                ).module_name
                sites.append((module_name, node.lineno))
    return sites


def _has_cycle_name(expression: ast.expr) -> bool:
    if isinstance(expression, ast.Name):
        return "cycle" in expression.id.lower()
    if isinstance(expression, ast.Attribute):
        return "cycle" in expression.attr.lower() or (
            _has_cycle_name(expression.value)
        )
    for child in ast.iter_child_nodes(expression):
        if isinstance(child, ast.expr) and _has_cycle_name(child):
            return True
    return False


def _phasor_call_argument_sites(
    source: str,
    module_name: str,
) -> list[tuple[str, int, str, bool]]:
    tree = ast.parse(source)
    sites: list[tuple[str, int, str, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "_unit_phasor_from_cycles":
            continue
        if not node.args and not node.keywords:
            continue
        if node.keywords:
            keyword = node.keywords[0]
            argument_name = keyword.arg or "<expr>"
            is_cycles_named = "cycle" in argument_name.lower() or (
                isinstance(keyword.value, ast.expr)
                and _has_cycle_name(keyword.value)
            )
            sites.append((module_name, node.lineno, argument_name, is_cycles_named))
            continue
        argument = node.args[0]
        if isinstance(argument, ast.Name):
            argument_name = argument.id
        else:
            argument_name = "<expr>"
        is_cycles_named = _has_cycle_name(argument)
        sites.append((module_name, node.lineno, argument_name, is_cycles_named))
    return sites


def _phasor_primitive_sites(
    source: str,
    module_name: str,
) -> list[tuple[str, int]]:
    tree = ast.parse(source)
    sites: list[tuple[str, int]] = []
    for call in read_python_call_facts(tree, module_name):
        if call.source == "torch.polar":
            sites.append((module_name, call.line))
            continue
        if (
            call.source == "torch.complex"
            and call.positional_sources == ("torch.cos", "torch.sin")
        ):
            sites.append((module_name, call.line))
    return sites


def test_unit_phasor_has_one_numerical_authority() -> None:
    """
    单位复相位只由一个物理中性的私有数值模块按名拥有，且唯一接口以周期表达
    """

    sites = _unit_phasor_definition_sites()
    assert len(sites) == 1, sites
    assert sites[0][0] == "chromatix_next._numerics.complex_phase"


def test_unit_phasor_call_arguments_are_cycles_named() -> None:
    """
    唯一单位复相位入口的传参以周期命名
    """

    offenders: list[str] = []
    for path in NUMERICS.glob("*.py"):
        module_name = read_python_imports(
            path,
            PACKAGE.parent,
        ).module_name
        source = path.read_text(encoding="utf-8")
        for found_module, line, argument_name, is_cycles_named in (
            _phasor_call_argument_sites(source, module_name)
        ):
            if not is_cycles_named:
                offenders.append(
                    f"{found_module}:{line} 传入参数 {argument_name!r}"
                )
    assert not offenders, offenders


def test_phasor_call_argument_gate_detects_radians_regression() -> None:
    """
    钉住检测契约：弧度变量、关键字与纯算式直接送入 phasor 必须被识别器检出
    """

    counterfactuals = (
        "import torch\n"
        "from chromatix_next._numerics.complex_phase import "
        "_unit_phasor_from_cycles\n\n"
        "def rewrite(phase):\n"
        "    return _unit_phasor_from_cycles(phase)\n",
        "import torch\n"
        "from chromatix_next._numerics.complex_phase import "
        "_unit_phasor_from_cycles\n\n"
        "def rewrite(radians):\n"
        "    return _unit_phasor_from_cycles(radians)\n",
        "import torch\n"
        "from chromatix_next._numerics.complex_phase import "
        "_unit_phasor_from_cycles\n\n"
        "def rewrite(k, distance):\n"
        "    return _unit_phasor_from_cycles(k * distance)\n",
        "import torch\n"
        "from chromatix_next._numerics.complex_phase import "
        "_unit_phasor_from_cycles\n\n"
        "def rewrite(phase):\n"
        "    return _unit_phasor_from_cycles(angle=phase)\n",
    )
    for source in counterfactuals:
        sites = _phasor_call_argument_sites(
            source,
            "chromatix_next._numerics.counterfactual",
        )
        assert len(sites) == 1, source
        assert not sites[0][3], (
            f"识别器漏检的弧度入参改写：{source!r}"
        )


def test_unit_phasor_primitives_stay_in_complex_phase() -> None:
    """
    单位复相位的特征原语只在唯一权威 complex_phase.py 出现
    """

    offenders: list[str] = []
    for path in NUMERICS.glob("*.py"):
        module_name = read_python_imports(
            path,
            PACKAGE.parent,
        ).module_name
        for found_module, line in _phasor_primitive_sites(
            path.read_text(encoding="utf-8"),
            module_name,
        ):
            if found_module != "chromatix_next._numerics.complex_phase":
                offenders.append(f"{found_module}:{line}")
    assert not offenders, offenders


def test_unit_phasor_primitive_gate_detects_forbidden_forms() -> None:
    """
    特征原语（含函数局部别名）必须被识别器检出，钉住检测契约而非仅源码快照
    """

    counterfactuals = (
        "import torch\n\n"
        "def rewrite(angle):\n"
        "    return torch.polar(torch.ones_like(angle), angle)\n",
        "import torch\n\n"
        "def rewrite(phase):\n"
        "    return torch.complex(torch.cos(phase), torch.sin(phase))\n",
        "import torch\n\n"
        "def rewrite(phase):\n"
        "    polar_call = torch.polar\n"
        "    return polar_call(torch.ones_like(phase), phase)\n",
        "import torch\n\n"
        "def rewrite(phase):\n"
        "    builder = torch.complex\n"
        "    cosine = torch.cos\n"
        "    sine = torch.sin\n"
        "    return builder(cosine(phase), sine(phase))\n",
        "import torch\n\n"
        "def rewrite(phase):\n"
        "    return (builder := torch.complex)(\n"
        "        torch.cos(phase), torch.sin(phase)\n"
        "    )\n",
    )
    for source in counterfactuals:
        assert _phasor_primitive_sites(
            source,
            "chromatix_next._numerics.counterfactual",
        ), f"识别器漏检的单位复相位改写：{source!r}"

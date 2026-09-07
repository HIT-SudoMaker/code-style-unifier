from __future__ import annotations

import ast
import math
from pathlib import Path
import runpy

import pytest

from chromatix_next import Workstation
from chromatix_next.optics import Intensity
from examples.analytic_michelson_interferometer.example import (
    run as run_analytic_michelson,
)
from examples.basic_ideal_lens_focusing.example import run as run_lens
from examples.basic_plane_wave_intensity.example import run as run_plane_wave
from examples.propagation_scalar_angular_spectrum.example import (
    run as run_scalar_propagation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_ENTRIES = tuple(
    sorted((PROJECT_ROOT / "examples").rglob("example.py"))
)
DIRECT_LINEAR_EXAMPLE = (
    PROJECT_ROOT / "examples" / "minimal_optical_path" / "example.py"
)


def _scope_nodes(scope: ast.Module | ast.FunctionDef) -> tuple[ast.AST, ...]:
    # 函数与模块各自拥有别名；不跨入嵌套函数建立调用图。
    nodes: list[ast.AST] = []

    def _visit(node: ast.AST) -> None:
        nodes.append(node)
        if isinstance(
            node,
            (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef, ast.Lambda),
        ):
            return
        for child in ast.iter_child_nodes(node):
            _visit(child)

    for statement in scope.body:
        _visit(statement)
    return tuple(nodes)


def _workstation_import_names(
    tree: ast.Module,
) -> tuple[frozenset[str], frozenset[str]]:
    workstation_names = {"Workstation"}
    package_names = {"chromatix_next"}
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom) and (
            statement.module == "chromatix_next"
        ):
            workstation_names.update(
                alias.asname or alias.name
                for alias in statement.names
                if alias.name == "Workstation"
            )
        elif isinstance(statement, ast.Import):
            package_names.update(
                alias.asname or alias.name
                for alias in statement.names
                if alias.name == "chromatix_next"
            )
    return frozenset(workstation_names), frozenset(package_names)


def _workstation_selection_calls(
    scope: ast.Module | ast.FunctionDef,
    *,
    workstation_names: frozenset[str],
    package_names: frozenset[str],
) -> tuple[ast.Call, ...]:
    # 只追踪本作用域内直接绑定到公开 Workstation 工厂的简单名称。
    nodes = _scope_nodes(scope)

    def _is_factory_attribute(node: ast.AST) -> bool:
        if not isinstance(node, ast.Attribute) or node.attr not in {
            "cpu",
            "cuda",
        }:
            return False
        owner = node.value
        return (
            isinstance(owner, ast.Name)
            and owner.id in workstation_names
        ) or (
            isinstance(owner, ast.Attribute)
            and owner.attr == "Workstation"
            and isinstance(owner.value, ast.Name)
            and owner.value.id in package_names
        )

    factory_aliases: set[str] = set()
    for node in nodes:
        targets: tuple[ast.expr, ...] = ()
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets = tuple(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
            value = node.value
        elif isinstance(node, ast.NamedExpr):
            targets = (node.target,)
            value = node.value
        if value is not None and _is_factory_attribute(value):
            factory_aliases.update(
                target.id
                for target in targets
                if isinstance(target, ast.Name)
            )

    return tuple(
        node
        for node in nodes
        if isinstance(node, ast.Call)
        and (
            _is_factory_attribute(node.func)
            or (
                isinstance(node.func, ast.Name)
                and node.func.id in factory_aliases
            )
            or (
                isinstance(node.func, ast.NamedExpr)
                and _is_factory_attribute(node.func.value)
            )
        )
    )


def _example_workstation_selection_calls(
    tree: ast.Module,
    *,
    workstation_names: frozenset[str],
    package_names: frozenset[str],
    excluded_functions: tuple[ast.FunctionDef, ...] = (),
) -> tuple[ast.Call, ...]:
    calls = list(
        _workstation_selection_calls(
            tree,
            workstation_names=workstation_names,
            package_names=package_names,
        )
    )
    for statement in tree.body:
        if (
            isinstance(statement, ast.FunctionDef)
            and statement not in excluded_functions
        ):
            calls.extend(
                _workstation_selection_calls(
                    statement,
                    workstation_names=workstation_names,
                    package_names=package_names,
                )
            )
    return tuple(calls)


def _example_entry_findings(
    source: str,
    *,
    is_direct_linear_form: bool = False,
) -> tuple[str, ...]:
    # ordinary run 与显式 direct-linear 形态都必须完整、互斥且失败闭合。
    tree = ast.parse(source)
    workstation_names, package_names = _workstation_import_names(tree)
    run_functions = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run"
    )
    if is_direct_linear_form:
        if run_functions:
            return ("direct linear form defines run",)
        if _example_workstation_selection_calls(
            tree,
            workstation_names=workstation_names,
            package_names=package_names,
        ):
            return ("direct linear form selects a Workstation",)
        return ()
    if len(run_functions) != 1:
        return (f"run count {len(run_functions)}",)

    run_function = run_functions[0]
    parameter_names = {
        argument.arg
        for argument in (
            *run_function.args.args,
            *run_function.args.kwonlyargs,
        )
    }
    findings: list[str] = []
    if "workstation" not in parameter_names:
        findings.append("missing workstation")
    selector_parameters = sorted(
        name
        for name in parameter_names
        if name != "workstation"
        and any(
            token in name.casefold()
            for token in ("device", "precision", "backend")
        )
    )
    if selector_parameters:
        findings.append(f"accepts selectors {selector_parameters}")
    internal_factories = _workstation_selection_calls(
        run_function,
        workstation_names=workstation_names,
        package_names=package_names,
    )
    if internal_factories:
        findings.append("run selects another Workstation")

    module_factory_calls = _example_workstation_selection_calls(
        tree,
        workstation_names=workstation_names,
        package_names=package_names,
        excluded_functions=(run_function,),
    )
    if len(module_factory_calls) != 1:
        findings.append(
            f"module Workstation selection count {len(module_factory_calls)}"
        )
    return tuple(findings)


def test_example_entry_guard_rejects_missing_run() -> None:
    """
    普通案例缺少公开 run 入口时必须失败
    """
    assert _example_entry_findings("value = 1") == ("run count 0",)


def test_example_entry_guard_rejects_workstation_selection_inside_run() -> None:
    """
    run 内部再次选择 Workstation 时必须失败
    """
    source = """
from chromatix_next import Workstation

def run(*, workstation):
    return Workstation.cpu()

result = run(workstation=Workstation.cpu())
"""
    assert "run selects another Workstation" in _example_entry_findings(source)


def test_example_entry_guard_rejects_local_factory_alias_inside_run() -> None:
    """
    run 内通过简单局部别名再次选择 Workstation 时必须失败
    """
    source = """
from chromatix_next import Workstation

selected_workstation = Workstation.cpu()

def run(*, workstation):
    select_another = Workstation.cuda
    return select_another()

result = run(workstation=selected_workstation)
"""
    assert "run selects another Workstation" in _example_entry_findings(source)


def test_direct_linear_guard_rejects_local_factory_alias() -> None:
    """
    直接线性案例通过简单别名选择 Workstation 时必须失败
    """
    source = """
from chromatix_next import Workstation

select_workstation = Workstation.cpu
workstation = select_workstation()
"""
    assert _example_entry_findings(
        source,
        is_direct_linear_form=True,
    ) == ("direct linear form selects a Workstation",)


def test_example_entry_guard_rejects_immediate_walrus_factory_call() -> None:
    """
    内联设备选择必须失败
    """
    source = """
from chromatix_next import Workstation

selected_workstation = Workstation.cpu()

def run(*, workstation):
    return (select_another := Workstation.cuda)()

result = run(workstation=selected_workstation)
"""
    assert "run selects another Workstation" in _example_entry_findings(source)


def test_direct_linear_guard_rejects_immediate_walrus_factory_call() -> None:
    """
    直接案例的内联设备选择必须失败
    """
    source = """
from chromatix_next import Workstation

workstation = (select_workstation := Workstation.cpu)()
"""
    assert _example_entry_findings(
        source,
        is_direct_linear_form=True,
    ) == ("direct linear form selects a Workstation",)


def test_example_entry_guard_rejects_disguised_device_selector() -> None:
    """
    设备选择参数采用不同拼写时仍必须失败
    """
    source = """
from chromatix_next import Workstation

def run(*, workstation, device_index):
    return workstation, device_index

result = run(workstation=Workstation.cpu(), device_index=0)
"""
    assert "accepts selectors ['device_index']" in _example_entry_findings(
        source
    )


def test_examples_receive_one_preselected_workstation() -> None:
    """
    光路案例只接收一个预选工作站，不另建设备选择层
    """

    findings: list[str] = []
    for path in EXAMPLE_ENTRIES:
        source = path.read_text(encoding="utf-8")
        entry_findings = _example_entry_findings(
            source,
            is_direct_linear_form=path == DIRECT_LINEAR_EXAMPLE,
        )
        findings.extend(f"{path}:{finding}" for finding in entry_findings)

    assert findings == []


def test_minimal_optical_path_teaches_a_central_intensity_maximum() -> None:
    """
    最小光路执行后产生中心强度最大值
    """

    namespace = runpy.run_path(
        str(PROJECT_ROOT / "examples" / "minimal_optical_path" / "example.py"),
    )
    intensity = namespace["intensity"]
    assert isinstance(intensity, Intensity)
    assert intensity.values.shape[-2:] == (64, 64)
    assert intensity.values[32, 32] == intensity.values.max()


def test_plane_wave_teaches_unit_mean_intensity() -> None:
    """
    单位相对幅度平面波给出单位平均强度
    """

    result = run_plane_wave(
        workstation=Workstation.cpu(),
        sample_counts=(8, 8),
    )
    assert result.mean_intensity == pytest.approx(1.0)


def test_ideal_lens_teaches_a_finite_positive_central_focus() -> None:
    """
    理想薄透镜在中心形成有限正峰值
    """

    result = run_lens(
        workstation=Workstation.cpu(),
        sample_counts=(16, 16),
        sample_spacing=(10.0e-6, 10.0e-6),
        aperture_diameter=120.0e-6,
        focal_length=10.0e-3,
    )
    assert math.isfinite(result.peak_intensity)
    assert result.peak_intensity > 0.0
    assert result.peak_index == (8, 8)


def test_scalar_propagation_teaches_the_authored_destination_shift() -> None:
    """
    标量传播保留目标网格平移并给出有限结果
    """

    destination_shift = (6.0e-6, -3.0e-6)
    result = run_scalar_propagation(
        workstation=Workstation.cpu(),
        sample_counts=(16, 16),
        sample_spacing=(3.0e-6, 3.0e-6),
        aperture_diameter=30.0e-6,
        axial_distance=0.2e-3,
        destination_shift=destination_shift,
    )
    assert result.destination_shift == destination_shift
    assert math.isfinite(result.peak_intensity)
    assert math.isfinite(result.mean_intensity)


def test_analytic_michelson_teaches_complementary_relative_outputs() -> None:
    """
    单一 Cube owner 的四点 Michelson 扫相给出互补端口和单位可见度
    """

    result = run_analytic_michelson(workstation=Workstation.cpu())
    assert tuple(
        observation.relative_phase
        for observation in result.observations
    ) == (
        0.0,
        math.pi / 3.0,
        2.0 * math.pi / 3.0,
        math.pi,
    )
    assert all(
        observation.ratio_sum == pytest.approx(1.0, abs=2.0e-12)
        for observation in result.observations
    )
    assert result.left_visibility == pytest.approx(1.0, abs=2.0e-12)
    assert result.bottom_visibility == pytest.approx(1.0, abs=2.0e-12)

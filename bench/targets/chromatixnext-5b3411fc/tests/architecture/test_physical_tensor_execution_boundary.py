from __future__ import annotations

import ast
from pathlib import Path

# 持久主张是设备本地的物理 Tensor 执行边界


_SOURCE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "chromatix_next"
)
SIDECAR_STAGING_FUNCTIONS: frozenset[tuple[str, str, str]] = frozenset(
    {
        (
            "_numerics",
            "polynomial_conic_roots.py",
            "_stage_unresolved_lanes_to_host",
        )
    }
)
_EXTRACTION_METHODS = frozenset({"item", "numpy", "tolist"})
_SCALAR_CONSTRUCTORS = frozenset({"complex", "float", "int"})
_TENSOR_ATTRIBUTES = frozenset(
    {
        "cell_area",
        "envelope",
        "first_sample_position",
        "sample_spacing",
        "signed_spacing",
        "values",
    },
)
_STRUCTURAL_METHODS = frozenset({"element_size", "numel", "storage_offset"})
_NON_TENSOR_TORCH_CALLS = frozenset({"device"})


def _is_tensor_annotation(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    return "Tensor" in ast.unparse(annotation)


def _assigned_names(target: ast.expr) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.List, ast.Tuple)):
        return tuple(
            name
            for element in target.elts
            for name in _assigned_names(element)
        )
    return ()


def _is_tensor_expression(
    expression: ast.AST,
    tensor_names: frozenset[str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in tensor_names
    if isinstance(expression, ast.Attribute):
        if (
            expression.attr in _TENSOR_ATTRIBUTES
            or expression.attr.endswith("_buffer")
        ):
            return True
        return _is_tensor_expression(expression.value, tensor_names)
    if isinstance(expression, ast.Subscript):
        return _is_tensor_expression(expression.value, tensor_names)
    if isinstance(expression, ast.Call):
        if (
            isinstance(expression.func, ast.Attribute)
            and _is_tensor_expression(expression.func.value, tensor_names)
        ):
            return True
        if (
            isinstance(expression.func, ast.Attribute)
            and isinstance(expression.func.value, ast.Name)
            and expression.func.value.id == "torch"
            and expression.func.attr not in _NON_TENSOR_TORCH_CALLS
        ):
            return True
        return any(
            _is_tensor_expression(argument, tensor_names)
            for argument in expression.args
        )
    if isinstance(expression, (ast.BinOp, ast.BoolOp, ast.Compare)):
        return any(
            _is_tensor_expression(child, tensor_names)
            for child in ast.iter_child_nodes(expression)
        )
    if isinstance(expression, ast.UnaryOp):
        return _is_tensor_expression(expression.operand, tensor_names)
    return False


def _is_structural_tensor_expression(expression: ast.AST) -> bool:
    if isinstance(expression, ast.Subscript):
        return (
            isinstance(expression.value, ast.Attribute)
            and expression.value.attr == "shape"
        )
    if isinstance(expression, ast.Call):
        return (
            isinstance(expression.func, ast.Attribute)
            and expression.func.attr in _STRUCTURAL_METHODS
        )
    if isinstance(expression, ast.Attribute):
        return expression.attr == "_cdata"
    return False


def _tensor_names(function: ast.FunctionDef) -> frozenset[str]:
    names = {
        argument.arg
        for argument in (
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        )
                if _is_tensor_annotation(argument.annotation)
    }
    assignments = tuple(
        node
        for node in ast.walk(function)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
    )
    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            if isinstance(assignment, ast.Assign):
                value = assignment.value
                targets = tuple(
                    name
                    for target in assignment.targets
                    for name in _assigned_names(target)
                )
            else:
                value = assignment.value
                targets = _assigned_names(assignment.target)
                if _is_tensor_annotation(assignment.annotation):
                    for name in targets:
                        if name not in names:
                            names.add(name)
                            changed = True
            if (
                value is None
                or not _is_tensor_expression(
                    value,
                    frozenset(names),
                )
                or _is_structural_tensor_expression(value)
            ):
                continue
            for name in targets:
                if name not in names:
                    names.add(name)
                    changed = True
    return frozenset(names)


def _scalarization_findings(source: str, relative_path: str = "") -> tuple[str, ...]:
    parts = tuple(relative_path.split("/")) if relative_path else ()
    syntax = ast.parse(source)
    findings: list[str] = []
    for node in ast.walk(syntax):
        if isinstance(node, ast.FunctionDef):
            if (
                parts
                and (parts[0], parts[-1], node.name) in SIDECAR_STAGING_FUNCTIONS
            ):
                continue
            tensor_names = _tensor_names(node)
            calls = (
                child
                for child in ast.walk(node)
                if isinstance(child, ast.Call)
            )
            for call in calls:
                if (
                    isinstance(call.func, ast.Attribute)
                    and call.func.attr in _EXTRACTION_METHODS
                ):
                    findings.append(f"{call.lineno}:{call.func.attr}")
                    continue
                if (
                    not isinstance(call.func, ast.Name)
                    or call.func.id not in _SCALAR_CONSTRUCTORS
                    or len(call.args) != 1
                ):
                    continue
                argument = call.args[0]
                if (
                    _is_tensor_expression(argument, tensor_names)
                    and not _is_structural_tensor_expression(argument)
                ):
                    findings.append(f"{call.lineno}:{call.func.id}")
    return tuple(dict.fromkeys(findings))


def test_scalarization_probe_rejects_tensor_values_not_metadata() -> None:
    """
    AST 门禁拒绝物理张量取值但允许 Python 元数据与结构计数
    """
    probe = """
import torch

def invalid(distance: torch.Tensor, field: object) -> tuple[object, ...]:
    return (
        distance.item(),
        distance.tolist(),
        distance.numpy(),
        float(distance),
        float(distance.detach()),
        int(field.values.sum()),
        complex(distance.real),
    )

def valid(spectrum: object, tensor: torch.Tensor) -> tuple[float, int]:
    return float(spectrum.wavelengths[0]), int(tensor.numel())
"""

    assert _scalarization_findings(probe) == (
        "6:item",
        "7:tolist",
        "8:numpy",
        "9:float",
        "10:float",
        "11:int",
        "12:complex",
    )


def test_production_contains_no_physical_tensor_scalarization() -> None:
    """
    生产代码不把物理张量提取或构造成 Python 标量
    """
    findings = tuple(
        f"{path.relative_to(_SOURCE_ROOT)}:{finding}"
        for path in sorted(_SOURCE_ROOT.rglob("*.py"))
        for finding in _scalarization_findings(
            path.read_text(encoding="utf-8"),
            relative_path=path.relative_to(_SOURCE_ROOT).as_posix(),
        )
    )

    assert findings == ()

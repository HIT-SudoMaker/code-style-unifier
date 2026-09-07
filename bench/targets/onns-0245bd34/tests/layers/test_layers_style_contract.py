from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYERS_ROOT = PROJECT_ROOT / "layers"
LAYER_EXPORT_ORDER = (
    "DiffractionLayer",
    "LensLayer",
    "ModulationLayer",
    "DetectionLayer",
)
LAYER_IMPORT_ORDER = tuple(sorted(LAYER_EXPORT_ORDER))
VALIDATION_FUNCTION_ORDER = (
    "_format_invalid_value",
    "_format_supported_values",
    "_validate_finite_real_scalar",
    "validate_positive_scalar",
    "validate_nonzero_scalar",
    "validate_bool",
    "normalize_array_resolution",
    "validate_complex_input_field",
    "validate_same_device",
    "force_real_single_precision",
)
LAYER_CLASS_METHOD_ORDER: Dict[str, Tuple[str, ...]] = {
    "DiffractionLayer": (
        "__init__",
        "_register_physical_buffers",
        "_initialize_frequency_grid",
        "_validate_input_field",
        "_compute_transfer_function",
        "_clear_cache",
        "_apply",
        "forward",
        "get_transfer_function_information",
        "get_cache_statistics",
        "extra_repr",
    ),
    "LensLayer": (
        "__init__",
        "_initialize_lens_phase",
        "_validate_input_field",
        "_apply",
        "forward",
        "get_lens_phase_information",
        "extra_repr",
    ),
    "ModulationLayer": (
        "__init__",
        "_initialize_modulation_phase",
        "_validate_input_field",
        "_compute_effective_phase",
        "_apply",
        "forward",
        "get_modulation_phase_information",
        "extra_repr",
    ),
    "DetectionLayer": (
        "__init__",
        "_validate_input_field",
        "forward",
        "extra_repr",
    ),
}


def _parse_layer_source(source_path: Path) -> ast.Module:
    return ast.parse(source_path.read_text(encoding="utf-8"))


def _class_method_names(class_node: ast.ClassDef) -> List[str]:
    return [
        item.name
        for item in class_node.body
        if isinstance(item, ast.FunctionDef)
    ]


def _module_function_names(syntax_tree: ast.Module) -> List[str]:
    return [
        item.name
        for item in syntax_tree.body
        if isinstance(item, ast.FunctionDef)
    ]


def _public_interface_nodes(syntax_tree: ast.Module) -> List[ast.AST]:
    interface_nodes: List[ast.AST] = []
    for node in syntax_tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            interface_nodes.append(node)
        if isinstance(node, ast.ClassDef):
            interface_nodes.append(node)
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_") or (
                    isinstance(item, ast.FunctionDef) and item.name == "__init__"
                ):
                    interface_nodes.append(item)
    return interface_nodes


def _public_callable_nodes(syntax_tree: ast.Module) -> List[ast.FunctionDef]:
    callable_nodes: List[ast.FunctionDef] = []
    for node in syntax_tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            callable_nodes.append(node)
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and (
                    not item.name.startswith("_") or item.name == "__init__"
                ):
                    callable_nodes.append(item)
    return callable_nodes


def _external_parameter_names(function_node: ast.FunctionDef) -> List[str]:
    parameters = [
        argument.arg
        for argument in (
            list(function_node.args.posonlyargs)
            + list(function_node.args.args)
            + list(function_node.args.kwonlyargs)
        )
    ]
    return [
        parameter
        for parameter in parameters
        if parameter not in {"self", "cls"}
    ]


def test_layer_class_method_order_matches_standard_contract() -> None:
    """
    校验光学层类方法顺序
    """
    for class_name, expected_order in LAYER_CLASS_METHOD_ORDER.items():
        source_path = LAYERS_ROOT / f"{class_name.removesuffix('Layer').lower()}_layer.py"
        syntax_tree = _parse_layer_source(source_path)
        class_node = next(
            node
            for node in syntax_tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        )

        assert _class_method_names(class_node) == list(expected_order)


def test_validation_helpers_follow_mental_order() -> None:
    """
    校验 validation helper 按配置、输入和生命周期顺序组织
    """
    syntax_tree = _parse_layer_source(LAYERS_ROOT / "_validation.py")

    assert _module_function_names(syntax_tree) == list(VALIDATION_FUNCTION_ORDER)


def test_layers_root_follows_public_mental_order() -> None:
    """
    校验 layers 根接口的导入与导出顺序一致
    """
    syntax_tree = _parse_layer_source(LAYERS_ROOT / "__init__.py")
    imported_names = [
        alias.name
        for node in syntax_tree.body
        if isinstance(node, ast.ImportFrom) and node.module != "__future__"
        for alias in node.names
    ]
    export_assignment = next(
        node
        for node in syntax_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    )

    assert tuple(imported_names) == LAYER_IMPORT_ORDER
    assert ast.literal_eval(export_assignment.value) == LAYER_EXPORT_ORDER


def test_precision_contract_helpers_live_in_validation_module() -> None:
    """
    校验层精度契约工具归属于validation模块
    """
    assert not (LAYERS_ROOT / "_precision.py").exists()

    for source_path in [
        LAYERS_ROOT / "modulation_layer.py",
        LAYERS_ROOT / "lens_layer.py",
    ]:
        source_text = source_path.read_text(encoding="utf-8")
        assert "from ._precision import" not in source_text
        assert "from ._validation import" in source_text
        assert "force_real_single_precision" in source_text


def test_layers_public_interfaces_have_docstrings() -> None:
    """
    校验layers公有接口具备文档字符串
    """
    for source_path in LAYERS_ROOT.glob("*.py"):
        syntax_tree = _parse_layer_source(source_path)
        for interface_node in _public_interface_nodes(syntax_tree):
            assert ast.get_docstring(interface_node)


def test_layers_public_callables_document_parameters() -> None:
    """
    校验layers公有可调用接口记录参数契约
    """
    for source_path in LAYERS_ROOT.glob("*.py"):
        syntax_tree = _parse_layer_source(source_path)
        for callable_node in _public_callable_nodes(syntax_tree):
            parameter_names = _external_parameter_names(callable_node)
            if not parameter_names:
                continue

            docstring = ast.get_docstring(callable_node) or ""

            assert "Args:" in docstring
            for parameter_name in parameter_names:
                assert re.search(rf"(^|\n)\s+{parameter_name}\s*:", docstring)


def test_layers_args_blocks_align_field_colons() -> None:
    """
    校验layers参数字段块描述对齐
    """
    for source_path in LAYERS_ROOT.glob("*.py"):
        syntax_tree = _parse_layer_source(source_path)
        for callable_node in _public_callable_nodes(syntax_tree):
            docstring = ast.get_docstring(callable_node) or ""
            lines = docstring.splitlines()
            for line_index, line in enumerate(lines):
                if line.strip() != "Args:":
                    continue

                argument_lines: List[str] = []
                for argument_line in lines[line_index + 1:]:
                    if not argument_line.strip():
                        break
                    argument_lines.append(argument_line)

                if len(argument_lines) <= 1:
                    continue

                description_columns = []
                for argument_line in argument_lines:
                    assert re.match(r"^\s+[A-Za-z_][A-Za-z0-9_]*:\s+\S", argument_line)
                    colon_pos = argument_line.index(":")
                    after_colon = argument_line[colon_pos + 1:]
                    stripped = after_colon.lstrip()
                    description_columns.append(
                        colon_pos + 1 + len(after_colon) - len(stripped)
                    )

                assert len(set(description_columns)) == 1


def test_layers_args_blocks_keep_summary_indentation() -> None:
    """
    校验layers参数字段块物理缩进
    """
    for source_path in LAYERS_ROOT.glob("*.py"):
        source_lines = source_path.read_text(encoding="utf-8").splitlines()
        for line_index, line in enumerate(source_lines):
            if line.strip() != "Args:":
                continue

            previous_index = line_index - 1
            while previous_index >= 0 and not source_lines[previous_index].strip():
                previous_index -= 1

            assert previous_index >= 0
            assert len(line) - len(line.lstrip()) == len(source_lines[previous_index]) - len(source_lines[previous_index].lstrip())

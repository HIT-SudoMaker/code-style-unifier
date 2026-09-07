from __future__ import annotations

import ast
from pathlib import Path

_OPTICS = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "chromatix_next"
    / "optics"
)


_ROLE_PACKAGES = (
    _OPTICS / "source",
    _OPTICS / "element",
    _OPTICS / "propagation",
    _OPTICS / "combination",
    _OPTICS / "detection",
)


_NUMERICS = _OPTICS.parent / "_numerics"


_SPATIAL_SAMPLING_CALLERS = (
    _NUMERICS / "plane_wave.py",
    _NUMERICS / "gaussian_beam.py",
    _NUMERICS / "aperture.py",
    _NUMERICS / "thin_transmission.py",
)


_WAVE_NUMBER_AUTHORITY = _NUMERICS / "wave_number.py"


_CERTIFIED_PREDICATE_AUTHORITY = _NUMERICS / "_certified_predicates.py"


_EXACT_BINARY64_SIGN_AUTHORITY = _NUMERICS / "_exact_binary64_sign.py"


_WAVE_NUMBER_CALLERS = (
    _OPTICS / "source" / "gaussian_beam.py",
    _NUMERICS / "wave_propagation" / "aplanatic_focus.py",
    _NUMERICS / "plane_wave.py",
    _NUMERICS / "gaussian_beam.py",
    _NUMERICS / "wave_propagation" / "radiative_spectrum.py",
    _NUMERICS / "thin_transmission.py",
)


_SUBSTANTIVE_TENSOR_METHODS = frozenset(
    {
        "abs",
        "conj",
        "exp",
        "fftn",
        "ifftn",
        "log",
        "matmul",
        "mean",
        "norm",
        "prod",
        "square",
        "sqrt",
        "sum",
    },
)


_SUBSTANTIVE_TORCH_FUNCTIONS = frozenset(
    {
        "abs",
        "cat",
        "clamp",
        "einsum",
        "exp",
        "fftfreq",
        "fftn",
        "ifftn",
        "log",
        "matmul",
        "mean",
        "meshgrid",
        "norm",
        "prod",
        "roll",
        "square",
        "sqrt",
        "stack",
        "sum",
        "where",
    },
)


def _attribute_path(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return tuple(reversed(parts))


def _substantive_tensor_calls(path: Path) -> list[int]:
    syntax = ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )
    findings: list[int] = []
    for node in ast.walk(syntax):
        if not isinstance(node, ast.Call):
            continue
        call_path = _attribute_path(node.func)
        if not call_path:
            continue
        call_root = next(iter(call_path))
        call_name = next(reversed(call_path))
        is_tensor_method = (
            len(call_path) >= 2
            and call_name in _SUBSTANTIVE_TENSOR_METHODS
        )
        is_torch_function = (
            call_root == "torch"
            and call_name in _SUBSTANTIVE_TORCH_FUNCTIONS
        )
        is_torch_fft = call_path[:2] == ("torch", "fft")
        if is_tensor_method or is_torch_function or is_torch_fft:
            findings.append(node.lineno)
    return findings


def test_components_contain_no_substantive_tensor_algorithms() -> None:
    """
    约束 Component 不重复实现实质张量算法
    """

    findings = [
        f"{path.relative_to(_OPTICS)}:{line}"
        for package in _ROLE_PACKAGES
        for path in sorted(package.glob("*.py"))
        for line in _substantive_tensor_calls(path)
    ]

    assert findings == []


def test_certified_predicates_have_one_device_local_exact_sign_owner() -> None:
    """
    约束模糊通道只进入整数肢权威，不恢复浮点展开或主机有理旁路
    """

    exact_owner_definitions: list[str] = []
    exact_owner_imports: list[str] = []
    exact_owner_calls: list[str] = []
    forbidden_host_paths: list[str] = []
    forbidden_retired_symbol_names = (
        "_exact_sign_of_monomials",
        "_product_pieces",
        "_splitter_bits",
        "_two_product",
        "_two_sum",
    )
    for path in sorted(_NUMERICS.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        syntax = ast.parse(source, filename=str(path))
        for retired_symbol_name in forbidden_retired_symbol_names:
            if retired_symbol_name in source:
                forbidden_host_paths.append(f"{path.name}:{retired_symbol_name}")
        for node in ast.walk(syntax):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_exact_binary64_monomial_sum_sign"
            ):
                exact_owner_definitions.append(path.name)
            if isinstance(node, ast.ImportFrom) and any(
                alias.name == "_exact_binary64_monomial_sum_sign"
                for alias in node.names
            ):
                exact_owner_imports.append(path.name)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_exact_binary64_monomial_sum_sign"
            ):
                exact_owner_calls.append(path.name)
            if path.name != "conic_root_proof.py" and (
                isinstance(node, ast.Import)
                and any(alias.name == "fractions" for alias in node.names)
                or isinstance(node, ast.ImportFrom)
                and node.module == "fractions"
            ):
                forbidden_host_paths.append(
                    f"{path.name}:{node.lineno}:fractions",
                )

        authorized_cpu_calls = (
            {
                id(node)
                for definition in syntax.body
                if isinstance(definition, ast.FunctionDef)
                and definition.name == "_stage_unresolved_lanes_to_host"
                for node in ast.walk(definition)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "cpu"
            }
            if path.name == "polynomial_conic_roots.py"
            else set()
        )
        for node in ast.walk(syntax):
            if not isinstance(node, ast.Call) or not isinstance(
                node.func,
                ast.Attribute,
            ):
                continue
            if node.func.attr in {"numpy", "tolist"}:
                forbidden_host_paths.append(
                    f"{path.name}:{node.lineno}:{node.func.attr}",
                )
            if node.func.attr == "cpu" and id(node) not in authorized_cpu_calls:
                forbidden_host_paths.append(
                    f"{path.name}:{node.lineno}:cpu",
                )
            if node.func.attr == "to":
                device_values = (
                    *node.args[:1],
                    *(
                        keyword.value
                        for keyword in node.keywords
                        if keyword.arg == "device"
                    ),
                )
                if any(
                    isinstance(value, ast.Constant) and value.value == "cpu"
                    for value in device_values
                ):
                    forbidden_host_paths.append(
                        f"{path.name}:{node.lineno}:to_cpu",
                    )

    assert exact_owner_definitions == [_EXACT_BINARY64_SIGN_AUTHORITY.name]
    assert exact_owner_imports == [_CERTIFIED_PREDICATE_AUTHORITY.name]
    assert exact_owner_calls == [_CERTIFIED_PREDICATE_AUTHORITY.name]
    assert forbidden_host_paths == []


def test_spatial_sampling_has_one_numerical_authority() -> None:
    """
    约束空间采样坐标只由私有数值权威展开
    """

    findings: list[str] = []
    for path in _SPATIAL_SAMPLING_CALLERS:
        syntax = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        imports_authority = any(
            isinstance(node, ast.ImportFrom)
            and node.module
            == "chromatix_next._numerics.spatial_sampling"
            and any(
                alias.name == "spatial_sample_positions"
                for alias in node.names
            )
            for node in ast.walk(syntax)
        )
        calls_authority = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "spatial_sample_positions"
            for node in ast.walk(syntax)
        )
        rebuilds_coordinates = any(
            isinstance(node, ast.Call)
            and _attribute_path(node.func) == ("torch", "arange")
            for node in ast.walk(syntax)
        )
        if (
            not imports_authority
            or not calls_authority
            or rebuilds_coordinates
        ):
            findings.append(path.name)

    assert findings == []


def test_medium_wave_numbers_have_one_numerical_authority() -> None:
    """
    约束介质波数公式只归一处私有数值权威
    """

    findings: list[str] = []
    for path in _WAVE_NUMBER_CALLERS:
        syntax = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        imports_authority = any(
            isinstance(node, ast.ImportFrom)
            and (
                node.module
                == "chromatix_next._numerics.wave_number"
                or node.module == "wave_number"
            )
            and any(
                alias.name == "medium_wave_numbers"
                for alias in node.names
            )
            for node in ast.walk(syntax)
        )
        calls_authority = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "medium_wave_numbers"
            for node in ast.walk(syntax)
        )
        rebuilds_formula = any(
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Div)
            and any(
                _attribute_path(part) == ("math", "pi")
                for part in ast.walk(node)
            )
            and any(
                isinstance(part, ast.Name)
                and part.id.startswith("wavelength")
                for part in ast.walk(node)
            )
            for node in ast.walk(syntax)
        )
        if not imports_authority or not calls_authority or rebuilds_formula:
            findings.append(path.name)

    authority_syntax = ast.parse(
        _WAVE_NUMBER_AUTHORITY.read_text(encoding="utf-8"),
        filename=str(_WAVE_NUMBER_AUTHORITY),
    )
    numerical_definitions = [
        node
        for node in authority_syntax.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "medium_wave_numbers"
    ]

    assert findings == []
    assert len(numerical_definitions) == 1

from __future__ import annotations

import ast
import inspect
from pathlib import Path
import re
import textwrap
from types import FunctionType, ModuleType
from typing import get_type_hints

import torch

from chromatix_next.optics import (
    OpticalField,
    SpatialGrid,
    combination,
    detection,
    element,
    propagation,
    source,
)
from chromatix_next.optics._role_contract import _ROLE_SEMANTICS_BY_NAME
from chromatix_next.optics.assembly import Assembly

ROLE_PACKAGES: tuple[tuple[str, ModuleType], ...] = (
    ("source", source),
    ("element", element),
    ("propagation", propagation),
    ("combination", combination),
    ("detection", detection),
)

DIRECTIONAL_OWNER_NAMES = frozenset(
    {
        "IdealNonpolarizingCubeBeamSplitter",
        "IdealPlanarMirror",
        "IdealPolarizingCubeBeamSplitter",
    }
)


ROLE_INPUT_NAMES_BY_ROLE: dict[str, tuple[tuple[str, ...], ...]] = {
    "source": (
        ("grid",),
        ("grid",),
    ),
    "element": (
        ("field",),
        ("bundle",),
    ),
    "propagation": (
        ("field",),
        ("bundle",),
    ),
    "combination": (
        ("field_1", "field_2"),
        ("intensity_1", "intensity_2"),
    ),
    "detection": (
        ("field",),
    ),
}


def _function_name(component_name: str) -> str:
    separated_acronyms = re.sub(
        r"(.)([A-Z][a-z]+)",
        r"\1_\2",
        component_name,
    )
    return re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1_\2",
        separated_acronyms,
    ).lower()


def _published_components() -> tuple[
    tuple[str, ModuleType, type[torch.nn.Module]],
    ...,
]:
    components: list[
        tuple[str, ModuleType, type[torch.nn.Module]]
    ] = []
    for role, package in ROLE_PACKAGES:
        for name in getattr(package, "__all__", ()):
            component = getattr(package, name)
            if (
                isinstance(component, type)
                and issubclass(component, torch.nn.Module)
                and name not in DIRECTIONAL_OWNER_NAMES
            ):
                components.append((role, package, component))
    return tuple(components)


def _published_pairs() -> tuple[
    tuple[str, FunctionType, type[torch.nn.Module]],
    ...,
]:
    pairs: list[tuple[str, FunctionType, type[torch.nn.Module]]] = []
    for role, package, component in _published_components():
        if role == "source":
            continue
        function_name = _function_name(component.__name__)
        function = getattr(package, function_name, None)
        assert isinstance(function, FunctionType)
        pairs.append((role, function, component))
    return tuple(pairs)


def _has_matching_role_shape(
    *,
    role: str,
    parameter_names: tuple[str, ...],
    parameter_types: tuple[object, ...],
    result_type: object,
) -> bool:
    semantics = _ROLE_SEMANTICS_BY_NAME[role]
    for declared_names, calculation in zip(
        ROLE_INPUT_NAMES_BY_ROLE[role],
        semantics.calculations,
        strict=True,
    ):
        if (
            declared_names == parameter_names
            and calculation.parameters == parameter_types
            and calculation.result == result_type
        ):
            return True
    return False


def test_published_components_define_their_role_pairing() -> None:
    """
    从全部公开 Component 反向验证 Source 身份与动作对偶
    """
    components = _published_components()
    assert components
    for role, package, component in components:
        function_name = _function_name(component.__name__)
        published_names = getattr(package, "__all__", ())
        if role == "source":
            assert function_name not in published_names
            continue
        function = getattr(package, function_name, None)
        assert function_name in published_names
        assert isinstance(function, FunctionType)
        assert function.__module__ == component.__module__


def test_directional_owners_are_state_only_and_outside_optical_roles() -> None:
    """
    三个方向 owner 无可执行 Optical Role，不伪装成 Element 动作

    """

    assert DIRECTIONAL_OWNER_NAMES <= set(element.__all__)
    for name in DIRECTIONAL_OWNER_NAMES:
        owner = getattr(element, name)
        assert issubclass(owner, torch.nn.Module)
        assert "role" not in owner.__dict__
        assert "input_ports" not in owner.__dict__
        assert "output_ports" not in owner.__dict__
        assert _function_name(name) not in element.__all__


def test_optical_components_have_no_universal_base() -> None:
    """
    五个角色的公开 Component 不形成公开或跨角色的通用继承家族

    Source 可以复用私有生命周期实现，但测试不冻结其类名、文件位置或继承分组。
    其它角色的 Component 仍直接继承 torch.nn.Module。
    """
    for role, package in ROLE_PACKAGES:
        for name in getattr(package, "__all__", ()):
            component = getattr(package, name)
            if (
                isinstance(component, type)
                and issubclass(component, torch.nn.Module)
                and name not in DIRECTIONAL_OWNER_NAMES
            ):
                if role == "source":
                    assert len(component.__bases__) == 1
                    source_base = component.__bases__[0]
                    assert issubclass(source_base, torch.nn.Module)
                    assert source_base.__name__.startswith("_")
                    assert source_base.__module__.startswith(
                        "chromatix_next.optics."
                    )
                else:
                    assert component.__bases__ == (torch.nn.Module,)


def test_optical_roles_define_no_registry_or_catalog() -> None:
    """
    角色生产模块不建立函数、Component 或能力的注册表与目录层
    """
    forbidden_name_parts = ("registry", "catalog")
    for _role, package in ROLE_PACKAGES:
        package_file = package.__file__
        assert package_file is not None
        package_directory = Path(package_file).parent
        for module_path in package_directory.glob("*.py"):
            syntax = ast.parse(module_path.read_text(encoding="utf-8"))
            for node in ast.walk(syntax):
                identifier = ""
                if isinstance(node, ast.Name):
                    identifier = node.id
                elif isinstance(
                    node,
                    (
                        ast.ClassDef,
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):
                    identifier = node.name
                assert not any(
                    name_part in identifier.casefold()
                    for name_part in forbidden_name_parts
                )


def test_function_signature_is_forward_inputs_followed_by_owned_physics() -> None:
    """
    函数参数由完整角色输入块与 Component 构造物理量按顺序组成
    """
    for _role, function, component in _published_pairs():
        function_signature = inspect.signature(function)
        forward_signature = inspect.signature(component.forward)
        constructor_signature = inspect.signature(component)
        forward_parameters = tuple(forward_signature.parameters.values())[1:]
        constructor_parameters = tuple(
            constructor_signature.parameters.values()
        )
        expected_parameters = (
            *forward_parameters,
            *constructor_parameters,
        )

        assert tuple(function_signature.parameters.values()) == expected_parameters
        assert (
            function_signature.return_annotation
            == forward_signature.return_annotation
        )
        assert all(
            parameter.kind
            not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )
            for parameter in function_signature.parameters.values()
        )
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in constructor_parameters
        )
        has_optional_setting = False
        for parameter in constructor_parameters:
            if parameter.default is inspect.Parameter.empty:
                assert not has_optional_setting
            else:
                has_optional_setting = True


def test_published_function_inputs_follow_the_role_authority() -> None:
    """
    五个角色包共享既有语义权威，已迁移函数的输入块逐项匹配其 Component
    """
    role_names = tuple(role for role, _package in ROLE_PACKAGES)
    assert role_names == tuple(_ROLE_SEMANTICS_BY_NAME)
    assert role_names == tuple(ROLE_INPUT_NAMES_BY_ROLE)
    for role in role_names:
        semantics = _ROLE_SEMANTICS_BY_NAME[role]
        assert len(ROLE_INPUT_NAMES_BY_ROLE[role]) == len(
            semantics.calculations
        )
    for role, function, component in _published_pairs():
        annotations = get_type_hints(component.forward)
        parameters = tuple(inspect.signature(component.forward).parameters.values())[1:]
        input_types = tuple(annotations[parameter.name] for parameter in parameters)
        return_type = annotations["return"]
        has_matching_shape = _has_matching_role_shape(
            role=role,
            parameter_names=tuple(
                parameter.name for parameter in parameters
            ),
            parameter_types=input_types,
            result_type=return_type,
        )
        assert has_matching_shape
        assert not isinstance(function, torch.nn.Module)

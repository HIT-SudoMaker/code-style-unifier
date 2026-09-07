from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import inspect
from types import UnionType
from typing import Literal, TypeAlias, Union, get_args, get_origin, get_type_hints

import torch

import chromatix_next.errors as _errors

from .field import OpticalField
from .grid import SpatialGrid
from .intensity import Intensity
from .ray_bundle import RayBundle

_SourceRole: TypeAlias = Literal["source"]

_SourceCalculation: TypeAlias = (
    Callable[[SpatialGrid], OpticalField]
    | Callable[[SpatialGrid], RayBundle]
)

_ElementRole: TypeAlias = Literal["element"]

_ElementCalculation: TypeAlias = (
    Callable[[OpticalField], OpticalField]
    | Callable[[RayBundle], RayBundle]
)

_PropagationRole: TypeAlias = Literal["propagation"]

_PropagationCalculation: TypeAlias = (
    Callable[[OpticalField], OpticalField]
    | Callable[[RayBundle], RayBundle]
)

_CombinationRole: TypeAlias = Literal["combination"]

_CombinationCalculation: TypeAlias = (
    Callable[[OpticalField, OpticalField], OpticalField]
    | Callable[[Intensity, Intensity], Intensity]
)

_DetectionRole: TypeAlias = Literal["detection"]

_DetectionCalculation: TypeAlias = Callable[[OpticalField], Intensity]

_PhysicalValueKind: TypeAlias = type[OpticalField] | type[Intensity] | type[RayBundle]

_PHYSICAL_VALUE_KINDS: tuple[_PhysicalValueKind, ...] = (
    OpticalField,
    Intensity,
    RayBundle,
)

@dataclass(frozen=True, slots=True)
class _CallableShape:
    """
    承载组件的参数与返回形状

    """

    parameters: tuple[object, ...]
    result: object
    input_value_kinds: tuple[_PhysicalValueKind, ...]
    output_value_kinds: tuple[_PhysicalValueKind, ...]


@dataclass(frozen=True, slots=True)
class _RoleSemantics:
    """
    约束光学角色的输入输出与生成器

    """

    name: str
    role_annotation: object
    calculations: tuple[_CallableShape, ...]
    is_generator_allowed: bool


def _callable_shapes_of(annotation: object) -> tuple[_CallableShape, ...]:
    alternatives = (
        get_args(annotation)
        if get_origin(annotation) in (Union, UnionType)
        else (annotation,)
    )
    shapes: list[_CallableShape] = []
    for alternative in alternatives:
        if get_origin(alternative) is not Callable:
            raise _errors.OpticalTypeError(
                "optical_role_callable_authority_invalid",
                "角色契约权威中的调用形状必须写成可调用类型别名，"
                "这是 ChromatixNext 自身的契约表出了问题，请报告该缺陷",
            )
        parameters, result = get_args(alternative)
        if not isinstance(parameters, list):
            raise _errors.OpticalTypeError(
                "optical_role_callable_authority_invalid",
                "角色契约权威中的调用形状必须给出参数列表，"
                "这是 ChromatixNext 自身的契约表出了问题，请报告该缺陷",
            )
        input_value_kinds = _input_value_kinds_of(parameters)
        output_value_kinds = _output_value_kinds_of(result)
        shapes.append(
            _CallableShape(
                parameters=tuple(parameters),
                result=result,
                input_value_kinds=input_value_kinds,
                output_value_kinds=output_value_kinds,
            ),
        )
    return tuple(shapes)


def _physical_value_kind_of(
    annotation: object,
) -> _PhysicalValueKind | None:
    for kind in _PHYSICAL_VALUE_KINDS:
        if annotation is kind:
            return kind
    return None


def _domain_of(kind: _PhysicalValueKind) -> str:
    if kind is RayBundle:
        return "ray"
    return "wave"


def _input_value_kinds_of(
    parameters: list[object],
) -> tuple[_PhysicalValueKind, ...]:
    kinds: list[_PhysicalValueKind] = []
    for parameter in parameters:
        kind = _physical_value_kind_of(parameter)
        if kind is None:
            continue
        kinds.append(kind)
    return tuple(kinds)


def _output_value_kinds_of(
    result_annotation: object,
) -> tuple[_PhysicalValueKind, ...]:
    if get_origin(result_annotation) is tuple:
        candidates = tuple(
            _physical_value_kind_of(argument)
            for argument in get_args(result_annotation)
        )
    else:
        candidates = (_physical_value_kind_of(result_annotation),)
    if any(kind is None for kind in candidates):
        raise _errors.OpticalTypeError(
            "optical_role_callable_authority_invalid",
            "角色契约权威中的输出必须全部是闭合物理值，"
            "这是 ChromatixNext 自身的契约表出了问题，请报告该缺陷",
        )
    return candidates  # type: ignore[return-value]


def _role_semantics(
    *,
    role_annotation: object,
    calculation_annotation: object,
    is_generator_allowed: bool = False,
) -> _RoleSemantics:
    role_values = get_args(role_annotation)
    calculations = _callable_shapes_of(calculation_annotation)
    if len(role_values) != 1 or not isinstance(role_values[0], str):
        raise _errors.OpticalTypeError(
            "optical_role_semantic_authority_invalid",
            "角色契约权威必须给出恰好一个角色名，"
            "这是 ChromatixNext 自身的契约表出了问题，请报告该缺陷",
        )
    return _RoleSemantics(
        name=role_values[0],
        role_annotation=role_annotation,
        calculations=calculations,
        is_generator_allowed=is_generator_allowed,
    )


_ROLE_SEMANTICS = (
    _role_semantics(
        role_annotation=_SourceRole,
        calculation_annotation=_SourceCalculation,
        is_generator_allowed=True,
    ),
    _role_semantics(
        role_annotation=_ElementRole,
        calculation_annotation=_ElementCalculation,
    ),
    _role_semantics(
        role_annotation=_PropagationRole,
        calculation_annotation=_PropagationCalculation,
    ),
    _role_semantics(
        role_annotation=_CombinationRole,
        calculation_annotation=_CombinationCalculation,
    ),
    _role_semantics(
        role_annotation=_DetectionRole,
        calculation_annotation=_DetectionCalculation,
    ),
)
_ROLE_SEMANTICS_BY_NAME = {
    semantics.name: semantics for semantics in _ROLE_SEMANTICS
}


@dataclass(frozen=True, slots=True)
class _ComponentContract:
    """
    承载组件角色、端口和物理值类型契约

    """

    role: str
    input_ports: tuple[str | None, ...]
    output_ports: tuple[str | None, ...]
    input_values: tuple[_PhysicalValueKind, ...]
    output_values: tuple[_PhysicalValueKind, ...]
    is_generator_accepted: bool


def _component_contract_finding(component: object) -> str | None:
    contract, finding = _component_contract_of(component)
    del contract
    return finding


def _component_contract_of(
    component: object,
) -> tuple[_ComponentContract | None, str | None]:
    if not isinstance(component, torch.nn.Module):
        return None, "optical_component_role_invalid"
    role = _closed_role_of(component)
    if role is None:
        return None, "optical_component_role_invalid"
    semantics = _ROLE_SEMANTICS_BY_NAME[role]
    forward_signature = _method_signature_of(
        component,
        "forward",
        is_generator_allowed=semantics.is_generator_allowed,
    )
    if forward_signature is None:
        return None, f"optical_component_forward_signature_invalid:{role}"
    forward_parameters, forward_result, is_generator_accepted = forward_signature
    matching_calculation = next(
        (
            calculation
            for calculation in semantics.calculations
            if (forward_parameters, forward_result)
            == (calculation.parameters, calculation.result)
        ),
        None,
    )
    if matching_calculation is None:
        return None, f"optical_component_forward_signature_invalid:{role}"
    input_value_kinds = matching_calculation.input_value_kinds
    output_value_kinds = matching_calculation.output_value_kinds
    input_ports = _fixed_ports_of(
        component,
        direction="input",
        arity=len(input_value_kinds),
    )
    if input_ports is None:
        return None, "optical_component_input_ports_invalid"
    output_ports = _fixed_ports_of(
        component,
        direction="output",
        arity=len(output_value_kinds),
    )
    if output_ports is None:
        return None, "optical_component_output_ports_invalid"
    return (
        _ComponentContract(
            role=role,
            input_ports=input_ports,
            output_ports=output_ports,
            input_values=input_value_kinds,
            output_values=output_value_kinds,
            is_generator_accepted=is_generator_accepted,
        ),
        None,
    )


def _fixed_ports_of(
    component: torch.nn.Module,
    *,
    direction: str,
    arity: int,
) -> tuple[str | None, ...] | None:
    attribute_name = f"{direction}_ports"
    try:
        descriptor = inspect.getattr_static(
            type(component),
            attribute_name,
            None,
        )
        declared = getattr(component, attribute_name, None)
    except Exception:
        return None
    if arity == 0:
        if declared is None:
            return ()
        return None
    if arity == 1:
        if declared is None:
            return (None,)
        if (
            not isinstance(descriptor, property)
            or descriptor.fset is not None
            or declared != (None,)
        ):
            return None
        return (None,)
    if (
        not isinstance(descriptor, property)
        or descriptor.fset is not None
        or not isinstance(declared, tuple)
        or len(declared) != arity
        or len(set(declared)) != arity
        or any(
            not isinstance(port, str)
            or not port.isidentifier()
            or port.startswith("_")
            for port in declared
        )
    ):
        return None
    return declared


def _closed_role_of(component: torch.nn.Module) -> str | None:
    try:
        role = getattr(component, "role")
        descriptor = inspect.getattr_static(type(component), "role")
    except Exception:
        return None
    if (
        not isinstance(role, str)
        or role not in _ROLE_SEMANTICS_BY_NAME
        or not isinstance(descriptor, property)
        or descriptor.fset is not None
        or descriptor.fget is None
    ):
        return None
    try:
        annotation = get_type_hints(descriptor.fget).get("return")
    except (NameError, TypeError):
        return None
    semantics = _ROLE_SEMANTICS_BY_NAME[role]
    if annotation != semantics.role_annotation:
        return None
    return role


def _method_signature_of(
    component: torch.nn.Module,
    method_name: str,
    *,
    is_generator_allowed: bool = False,
) -> tuple[tuple[object, ...], object, bool] | None:
    method = inspect.getattr_static(type(component), method_name, None)
    if method is None or not callable(method):
        return None
    try:
        signature = inspect.signature(method)
        annotations = get_type_hints(method)
    except (NameError, TypeError, ValueError):
        return None
    parameters = list(signature.parameters.values())
    if not parameters or parameters[0].name != "self":
        return None
    physical_parameters: list[object] = []
    is_generator_accepted = False
    for parameter in parameters[1:]:
        if (
            is_generator_allowed
            and parameter.name == "generator"
            and parameter.kind is inspect.Parameter.KEYWORD_ONLY
        ):
            if parameter.default is not None:
                return None
            annotation = annotations.get(parameter.name)
            if not _is_optional_generator(annotation):
                return None
            is_generator_accepted = True
            continue
        if parameter.kind not in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            return None
        if parameter.default is not inspect.Parameter.empty:
            return None
        annotation = annotations.get(parameter.name)
        if annotation is None:
            return None
        physical_parameters.append(annotation)
    return_annotation = annotations.get("return")
    if return_annotation is None:
        return None
    return tuple(physical_parameters), return_annotation, is_generator_accepted


def _is_optional_generator(annotation: object) -> bool:
    if get_origin(annotation) not in (Union, UnionType):
        return False
    arguments = get_args(annotation)
    return (
        len(arguments) == 2
        and set(arguments) == {torch.Generator, type(None)}
    )

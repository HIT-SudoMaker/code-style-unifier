from __future__ import annotations

from collections.abc import Callable, Mapping
import copy
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

import torch

from chromatix_next import _ownership
from chromatix_next._ownership import _HostedStateLoadGuard
from chromatix_next._tensors import _COMPLEX_DTYPE, _REAL_DTYPE
import chromatix_next.errors as _errors
from chromatix_next.optics._assembly_facts import _FrozenAssembly
from chromatix_next.optics.element.ideal_cube_beam_splitter import (
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
    _prepare_cube_geometry,
    _prepare_mixing_angle,
    _require_valid_diagonal_code,
)
from chromatix_next.optics.element.ideal_planar_mirror import (
    IdealPlanarMirror,
    _prepare_mirror_geometry,
)
from chromatix_next.optics.source.collimated_ray import (
    CollimatedRaySource,
    _plan_collimated_ray_source_state_installation,
)
from chromatix_next.optics.source.gaussian_beam import (
    GaussianBeam,
    _plan_gaussian_beam_state_installation,
)
from chromatix_next.optics.source.plane_wave import (
    PlaneWave,
    _plan_plane_wave_state_installation,
    _SourceStatePlan,
)
from chromatix_next.optics.source.point_source import (
    PointSource,
    _plan_point_source_state_installation,
)
from chromatix_next.optics.surface.conic import (
    ConicEvenAsphere,
    _validate_conic_state_installation,
)

_EXTRA_STATE_SUFFIX = "_extra_state"

_SOURCE_PHYSICAL_BUFFERS = (
    "wavelengths", "spectral_weights", "polarization_state",
)

_SOURCE_DISPATCH: dict[
    type[torch.nn.Module],
    tuple[Callable[..., _SourceStatePlan], tuple[str, ...]],
] = {
    PlaneWave: (
        _plan_plane_wave_state_installation, _SOURCE_PHYSICAL_BUFFERS,
    ),
    GaussianBeam: (
        _plan_gaussian_beam_state_installation, _SOURCE_PHYSICAL_BUFFERS,
    ),
    PointSource: (
        _plan_point_source_state_installation, _SOURCE_PHYSICAL_BUFFERS,
    ),
    CollimatedRaySource: (
        _plan_collimated_ray_source_state_installation,
        _SOURCE_PHYSICAL_BUFFERS,
    ),
}

_DEFAULT_PERSISTENCE_METHODS = (
    "load_state_dict",
    "_load_from_state_dict",
    "state_dict",
    "_save_to_state_dict",
    "get_extra_state",
    "set_extra_state",
)

_INSTANCE_SHADOW_METHODS = (
    "load_state_dict",
    "_load_from_state_dict",
    "state_dict",
    "_save_to_state_dict",
)

_CONIC_LOCAL_NAMES = (
    "tangent_x",
    "tangent_y",
    "vertex",
    "curvature",
    "conic_constant",
    "even_coefficients",
    "clear_aperture_radius",
)

_ExactViewKey = tuple[
    int, int, tuple[int, ...], tuple[int, ...], torch.dtype,
]

_ROOT_UNSUPPORTED = "state_installation_root_unsupported"

_CHECKPOINT_INVALID = "state_installation_checkpoint_invalid"

_PERSISTENCE_UNSUPPORTED = "state_installation_persistence_unsupported"

_NATIVE_MODE_UNSUPPORTED = "state_installation_native_mode_unsupported"

_META_UNSUPPORTED = "state_installation_meta_unsupported"

_TENSOR_UNSUPPORTED = "state_installation_tensor_unsupported"

_DTYPE_UNSUPPORTED = "state_installation_dtype_unsupported"

_PARTIAL_VIEW = "state_installation_partial_storage_view"

_KEYS_MISMATCH = "state_installation_keys_mismatch"

_SHAPE_MISMATCH = "state_installation_shape_mismatch"

_RESIZE_ALIAS_CONFLICT = "state_installation_resize_alias_conflict"

_ALIAS_CONFLICT = "state_installation_alias_conflict"

_FROZEN_DIRECTIONAL_STATE_MISMATCH = (
    "state_installation_frozen_directional_state_mismatch"
)

_TARGET_CHANGED = "state_installation_target_changed"

_APPLICATION_FAILED = "state_installation_application_failed"

_ROLLBACK_FAILED = "state_installation_rollback_failed"



def install_state(
    root: torch.nn.Module,
    state_dict: Mapping[str, object],
) -> None:
    """
    在未托管根上原子载入一份严格的固定双精度 state_dict

    :param root: 当前未被任何工作站托管的整棵模块树
    :param state_dict: 字符串键物理量 Mapping；载入严格、不改写 dtype
    :return: 无返回值；载入后根仍非托管，须经显式 host 才能运行
    :raises OpticalError: 预检或载入失败以稳定身份拒绝，先于第一次原生张量复制

    Args:
        root: 接收状态的未托管模块树根
        state_dict: 按目标模块状态键组织的张量映射

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface

    """

    _assert_installation_root_supported(root)
    _ownership._run_unhosted_state_installation(
        root,
        lambda: _execute_state_installation(root, state_dict),
    )


def _execute_state_installation(
    root: torch.nn.Module,
    state_dict: Mapping[str, object],
) -> None:


    _assert_checkpoint_is_stable_mapping(state_dict)
    frozen_state_dict = MappingProxyType(
        {key: value for key, value in state_dict.items()},
    )
    plan = _plan_state_installation(root, frozen_state_dict)
    _apply_state_installation_plan(plan)


def _assert_installation_root_supported(
    root: torch.nn.Module,
) -> None:

    if isinstance(root, torch.Tensor):
        message = "状态安装的根必须是 nn.Module，不能是张量"
        raise _errors.OpticalTypeError(_ROOT_UNSUPPORTED, message)
    if not isinstance(root, torch.nn.Module):
        message = f"状态安装的根必须是 nn.Module，收到的是 {type(root).__name__}"
        raise _errors.OpticalTypeError(_ROOT_UNSUPPORTED, message)
    try:
        tuple(root.modules())
    except Exception as error:
        message = "状态安装的根无法枚举模块树"
        raise _errors.OpticalTypeError(_ROOT_UNSUPPORTED, message) from error


@dataclass(frozen=True, slots=True)
class _RegisteredStateIdentitySnapshot:



    """
    记录状态安装前的注册身份与拓扑

    """

    module_identities: frozenset[int]
    parameter_identities: tuple[tuple[str, int], ...]
    buffer_view_keys: tuple[tuple[str, _ExactViewKey], ...]
    source_lineage_identities: tuple[tuple[int, int], ...]
    topology: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _SourceBufferResize:


    """
    描述源缓冲区安装所需的受控形状调整

    """

    module: torch.nn.Module
    buffer_name: str
    target_shape: torch.Size
    full_name: str


@dataclass(frozen=True, slots=True)
class _StateInstallationPlan:



    """
    冻结通过预检后的原子状态安装计划

    """

    root: torch.nn.Module
    frozen_state_dict: Mapping[str, object]
    registered_identity_snapshot: _RegisteredStateIdentitySnapshot
    source_resizes: tuple[_SourceBufferResize, ...]
    alias_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class _StateApplicationSnapshot:
    """
    记录原子状态安装应用前的可回滚张量事实

    """

    persistent_state: Mapping[str, object]
    parameter_values: tuple[tuple[torch.nn.Parameter, torch.Tensor], ...]
    buffer_values: tuple[
        tuple[torch.nn.Module, str, torch.Tensor, torch.Tensor],
        ...,
    ]


def _plan_state_installation(
    root: torch.nn.Module,
    frozen_state_dict: Mapping[str, object],
) -> _StateInstallationPlan:


    module_by_name = tuple(root.named_modules(remove_duplicate=False))
    _assert_persistence_support(module_by_name)
    census = _take_registered_identity_snapshot(root, module_by_name)
    _assert_no_target_meta_or_unsupported_tensor(module_by_name)
    source_buffer_keys = _source_physical_buffer_keys(module_by_name)
    persistent_keys = frozenset(root.state_dict().keys())
    _assert_keys_match(persistent_keys, frozen_state_dict)
    _assert_expected_values_valid(root, frozen_state_dict, source_buffer_keys)
    _validate_directional_owner_state_installation(
        module_by_name,
        frozen_state_dict,
    )
    source_plans = _run_source_and_conic_planners(module_by_name, frozen_state_dict)
    source_resizes = _identify_source_resizes(module_by_name, source_plans)
    _assert_resize_aliases_distinct(source_resizes, module_by_name)
    alias_groups = _build_exact_alias_groups(root, frozen_state_dict)
    _assert_alias_groups_consistent(alias_groups, frozen_state_dict)
    _assert_frozen_directional_state_unchanged(
        module_by_name,
        frozen_state_dict,
    )
    _assert_registered_identity_snapshot_unchanged(root, census)
    return _StateInstallationPlan(
        root=root,
        frozen_state_dict=frozen_state_dict,
        registered_identity_snapshot=census,
        source_resizes=source_resizes,
        alias_groups=alias_groups,
    )


def _assert_checkpoint_is_stable_mapping(
    state_dict: Mapping[str, object],
) -> None:

    if not isinstance(state_dict, Mapping):
        kind = type(state_dict).__name__
        message = f"state_dict 必须是字符串键 Mapping，收到的是 {kind}"
        raise _errors.OpticalTypeError(_CHECKPOINT_INVALID, message)
    for key in state_dict:
        if not isinstance(key, str):
            message = f"state_dict 的键必须全部为字符串，收到非字符串键 {key!r}"
            raise _errors.OpticalTypeError(_CHECKPOINT_INVALID, message)


def _assert_persistence_support(
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
) -> None:


    for _name, module in module_by_name:
        _assert_no_instance_persistence_shadow(module)
        module_type = type(module)
        if module_type in _SOURCE_DISPATCH:
            continue
        if module_type is ConicEvenAsphere:
            continue
        _assert_default_persistence(module, module_type)


def _assert_no_instance_persistence_shadow(
    module: torch.nn.Module,
) -> None:



    for method_name in _INSTANCE_SHADOW_METHODS:
        if method_name in module.__dict__:
            message = f"模块实例 shadow 了 {method_name}，状态安装只接受默认持久化"
            raise _errors.OpticalRuntimeError(_PERSISTENCE_UNSUPPORTED, message)


def _assert_default_persistence(
    module: torch.nn.Module,
    module_type: type[torch.nn.Module],
) -> None:


    for method_name in _DEFAULT_PERSISTENCE_METHODS:
        module_attribute = getattr(module_type, method_name, None)
        base_attribute = getattr(torch.nn.Module, method_name, None)
        if module_attribute is not base_attribute:
            message = (
                f"模块 {module_type.__name__} 覆盖了 {method_name}，"
                "状态安装只接受默认持久化"
            )
            raise _errors.OpticalRuntimeError(_PERSISTENCE_UNSUPPORTED, message)
    _assert_hooks_supported(module)
    if isinstance(module, torch.Tensor):
        message = "模块树里包含作为 Tensor 子类的模块，状态安装不支持"
        raise _errors.OpticalRuntimeError(_PERSISTENCE_UNSUPPORTED, message)
    for parameter in module._parameters.values():
        if parameter is None:
            message = "模块树里包含惰性/未初始化参数槽，状态安装要求状态齐备"
            raise _errors.OpticalRuntimeError(_PERSISTENCE_UNSUPPORTED, message)
    if _is_swap_module_params_enabled(module):
        message = "模块启用了 swap-module-params 模式，与状态安装的固定载入契约冲突"
        raise _errors.OpticalRuntimeError(_NATIVE_MODE_UNSUPPORTED, message)


def _is_swap_module_params_enabled(module: torch.nn.Module) -> bool:

    return bool(getattr(module, "swap_module_params", False))


def _assert_hooks_supported(module: torch.nn.Module) -> None:



    project_guard_count = 0
    for hook in module._load_state_dict_pre_hooks.values():
        unwrapped = getattr(hook, "hook", hook)
        if isinstance(unwrapped, _HostedStateLoadGuard):
            project_guard_count += 1
            continue
        message = "模块带外部 load_state_dict 前置钩子，状态安装只接受默认持久化"
        raise _errors.OpticalRuntimeError(_PERSISTENCE_UNSUPPORTED, message)
    if project_guard_count > 1:
        message = "模块带多个项目托管守卫，状态安装至多接受一个惰性守卫"
        raise _errors.OpticalRuntimeError(_PERSISTENCE_UNSUPPORTED, message)
    if module._load_state_dict_post_hooks:
        message = "模块带 load_state_dict 后置钩子，状态安装只接受默认持久化"
        raise _errors.OpticalRuntimeError(_PERSISTENCE_UNSUPPORTED, message)
    state_pre = getattr(module, "_state_dict_pre_hooks", {})
    state_post = getattr(module, "_state_dict_post_hooks", {})
    if state_pre or state_post:
        message = "模块带 state_dict 前/后置钩子，状态安装只接受默认持久化"
        raise _errors.OpticalRuntimeError(_PERSISTENCE_UNSUPPORTED, message)


def _assert_no_target_meta_or_unsupported_tensor(
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
) -> None:

    view_by_storage: dict[int, list[_ExactViewKey]] = {}
    for _name, module in module_by_name:
        for tensor in _registered_tensors(module):
            _assert_target_tensor_supported(tensor)
            storage_identity = int(tensor.untyped_storage()._cdata)
            view_by_storage.setdefault(storage_identity, []).append(
                _exact_view_key(tensor),
            )
    for views in view_by_storage.values():
        if len(views) < 2:
            continue
        first = views[0]
        for other in views[1:]:
            if other != first:
                message = (
                    "目标树里同一底层存储上挂了两个不同的局部视图，"
                    "状态安装只接受精确别名"
                )
                raise _errors.OpticalRuntimeError(_PARTIAL_VIEW, message)


def _assert_target_tensor_supported(tensor: torch.Tensor) -> None:

    if tensor.is_meta:
        message = "目标张量位于 meta 设备，状态安装不支持 meta 状态"
        raise _errors.OpticalRuntimeError(_META_UNSUPPORTED, message)
    if tensor.is_sparse:
        message = "目标张量使用稀疏布局，状态安装只接受稠密张量"
        raise _errors.OpticalTypeError(_TENSOR_UNSUPPORTED, message)
    expected_dtype = _expected_fixed_dtype(tensor)
    if expected_dtype is not None and tensor.dtype is not expected_dtype:
        message = (
            f"目标张量 dtype 须为固定双精度 {expected_dtype}，"
            f"收到的是 {tensor.dtype}"
        )
        raise _errors.OpticalRuntimeError(_DTYPE_UNSUPPORTED, message)


def _expected_fixed_dtype(tensor: torch.Tensor) -> torch.dtype | None:

    if torch.is_complex(tensor):
        return _COMPLEX_DTYPE
    if tensor.is_floating_point():
        return _REAL_DTYPE
    return None


def _registered_tensors(
    module: torch.nn.Module,
) -> tuple[torch.Tensor, ...]:

    seen: dict[int, torch.Tensor] = {}
    for tensor in module._parameters.values():
        if tensor is not None:
            seen.setdefault(id(tensor), tensor)
    for tensor in module._buffers.values():
        if tensor is not None:
            seen.setdefault(id(tensor), tensor)
    return tuple(seen.values())


def _exact_view_key(tensor: torch.Tensor) -> _ExactViewKey:

    storage = tensor.untyped_storage()
    return (
        int(storage._cdata),
        int(tensor.storage_offset()),
        tuple(tensor.shape),
        tuple(tensor.stride()),
        tensor.dtype,
    )


def _take_registered_identity_snapshot(
    root: torch.nn.Module,
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
) -> _RegisteredStateIdentitySnapshot:


    del module_by_name
    module_identities = frozenset(id(module) for module in root.modules())
    parameter_identities = tuple(
        (name, id(parameter))
        for name, parameter in root.named_parameters(
            remove_duplicate=False,
        )
        if parameter is not None
    )
    persistent_names = set(root.state_dict().keys())
    buffer_view_keys = tuple(
        (name, _exact_view_key(buffer))
        for name, buffer in root.named_buffers(remove_duplicate=False)
        if buffer is not None and name in persistent_names
    )
    source_lineage_identities = tuple(
        (id(module), id(module.__dict__["_source_lineage"]))
        for module in root.modules()
        if "_source_lineage" in module.__dict__
    )
    named = root.named_modules(remove_duplicate=False)
    topology = tuple(name for name, _module in named)
    return _RegisteredStateIdentitySnapshot(
        module_identities=module_identities,
        parameter_identities=parameter_identities,
        buffer_view_keys=buffer_view_keys,
        source_lineage_identities=source_lineage_identities,
        topology=topology,
    )


def _source_physical_buffer_keys(
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
) -> frozenset[str]:

    keys: set[str] = set()
    for name, module in module_by_name:
        dispatch = _SOURCE_DISPATCH.get(type(module))
        if dispatch is None:
            continue
        _, physical_names = dispatch
        prefix = f"{name}." if name else ""
        for physical_name in physical_names:
            keys.add(prefix + physical_name)
    return frozenset(keys)


def _assert_keys_match(
    persistent_keys: frozenset[str],
    state_dict: Mapping[str, object],
) -> None:

    incoming_keys = set(state_dict.keys())
    missing = persistent_keys - incoming_keys
    unexpected = incoming_keys - persistent_keys
    if missing or unexpected:
        parts: list[str] = []
        if missing:
            parts.append(f"缺失键 {sorted(missing)}")
        if unexpected:
            parts.append(f"多余键 {sorted(unexpected)}")
        message = "状态字典键集不匹配：" + "；".join(parts)
        raise _errors.OpticalRuntimeError(_KEYS_MISMATCH, message)


def _assert_expected_values_valid(
    root: torch.nn.Module,
    state_dict: Mapping[str, object],
    source_buffer_keys: frozenset[str],
) -> None:


    target_state = root.state_dict()
    tensor_entries = tuple(
        (key, target_state[key])
        for key in target_state
        if not key.endswith(_EXTRA_STATE_SUFFIX)
    )
    for key, _target_value in tensor_entries:
        value = state_dict[key]
        if isinstance(value, torch.Tensor) and value.is_meta:
            message = f"键 {key!r} 的载入张量位于 meta 设备，状态安装不支持"
            raise _errors.OpticalRuntimeError(_META_UNSUPPORTED, message)
    for key, target_value in tensor_entries:
        value = state_dict[key]
        if not isinstance(value, torch.Tensor):
            kind = type(value).__name__
            message = f"键 {key!r} 的载入值必须是张量，收到的是 {kind}"
            raise _errors.OpticalTypeError(_TENSOR_UNSUPPORTED, message)
        if value.is_sparse:
            message = f"键 {key!r} 的载入张量使用稀疏布局，状态安装只接受稠密张量"
            raise _errors.OpticalTypeError(_TENSOR_UNSUPPORTED, message)
        if value.dtype is not target_value.dtype:
            message = f"键 {key!r} dtype 须为 {target_value.dtype}，收到 {value.dtype}"
            raise _errors.OpticalRuntimeError(_DTYPE_UNSUPPORTED, message)
        if key in source_buffer_keys:
            continue
        if value.shape != target_value.shape:
            want = tuple(target_value.shape)
            got = tuple(value.shape)
            message = f"键 {key!r} 形状须为 {want}，收到 {got}"
            raise _errors.OpticalRuntimeError(_SHAPE_MISMATCH, message)


def _run_source_and_conic_planners(
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
    state_dict: Mapping[str, object],
) -> tuple[tuple[torch.nn.Module, _SourceStatePlan], ...]:

    source_plans: list[tuple[torch.nn.Module, _SourceStatePlan]] = []
    for name, module in module_by_name:
        module_type = type(module)
        prefix = f"{name}." if name else ""
        if module_type in _SOURCE_DISPATCH:
            planner, physical_names = _SOURCE_DISPATCH[module_type]
            extra_state = state_dict[prefix + _EXTRA_STATE_SUFFIX]
            projected_buffers = {
                physical_name: state_dict[prefix + physical_name]
                for physical_name in physical_names
            }
            if module_type is CollimatedRaySource:
                projected_buffers.update(
                    {
                        "launch_origin": state_dict[
                            prefix + "launch_origin"
                        ],
                        "launch_tangent_x": state_dict[
                            prefix + "launch_tangent_x"
                        ],
                        "launch_tangent_y": state_dict[
                            prefix + "launch_tangent_y"
                        ],
                    }
                )
            plan = planner(module, extra_state, projected_buffers=projected_buffers)
            source_plans.append((module, plan))
        elif module_type is ConicEvenAsphere:
            local_state = {
                local_name: state_dict[prefix + local_name]
                for local_name in _CONIC_LOCAL_NAMES
                if (prefix + local_name) in state_dict
            }
            conic_module = cast(ConicEvenAsphere, module)
            _validate_conic_state_installation(conic_module, local_state)
    return tuple(source_plans)


def _validate_directional_owner_state_installation(
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
    state_dict: Mapping[str, object],
) -> None:
    # 三种 closed owner 只消费按稳定模块名前缀投影的完整 donor 状态
    for name, module in module_by_name:
        module_type = type(module)
        prefix = f"{name}." if name else ""
        if module_type in (
            IdealNonpolarizingCubeBeamSplitter,
            IdealPolarizingCubeBeamSplitter,
        ):
            origin = cast(torch.Tensor, state_dict[prefix + "origin"])
            route_right = cast(
                torch.Tensor,
                state_dict[prefix + "route_right"],
            )
            route_top = cast(
                torch.Tensor,
                state_dict[prefix + "route_top"],
            )
            _prepare_cube_geometry(
                owner_label=module_type.__name__,
                origin=origin,
                route_right=route_right,
                route_top=route_top,
            )
            _require_valid_diagonal_code(
                state_dict[prefix + "_coating_diagonal_code"],
                owner_label=module_type.__name__,
            )
            if module_type is IdealNonpolarizingCubeBeamSplitter:
                _prepare_mixing_angle(
                    state_dict[prefix + "mixing_angle"],
                )
            continue
        if module_type is IdealPlanarMirror:
            _prepare_mirror_geometry(
                origin=state_dict[prefix + "origin"],
                outward_normal=state_dict[prefix + "outward_normal"],
                transverse_up=state_dict[prefix + "transverse_up"],
            )


def _assert_frozen_directional_state_unchanged(
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
    state_dict: Mapping[str, object],
) -> None:
    module_by_path = dict(module_by_name)
    for assembly_name, module in module_by_name:
        facts = module.__dict__.get("_frozen_facts")
        if not isinstance(facts, _FrozenAssembly):
            continue
        for owner_fact in facts.directional_owners:
            owner_name = (
                f"{assembly_name}.{owner_fact.owner_name}"
                if assembly_name
                else owner_fact.owner_name
            )
            owner = module_by_path[owner_name]
            owner_type = type(owner)
            if owner_type in (
                IdealNonpolarizingCubeBeamSplitter,
                IdealPolarizingCubeBeamSplitter,
            ):
                fixed_names = (
                    "origin",
                    "route_right",
                    "route_top",
                    "_coating_diagonal_code",
                )
            elif owner_type is IdealPlanarMirror:
                fixed_names = (
                    "origin",
                    "outward_normal",
                    "transverse_up",
                )
            else:
                continue
            for fixed_name in fixed_names:
                incoming = cast(
                    torch.Tensor,
                    state_dict[f"{owner_name}.{fixed_name}"],
                )
                current = cast(torch.Tensor, getattr(owner, fixed_name))
                if _is_incoming_alias_value_equal(current, incoming):
                    continue
                assembly_label = assembly_name or "<root>"
                message = (
                    f"冻结 Assembly {assembly_label!r} 的 directional owner "
                    f"{owner_name!r} 固定字段 {fixed_name!r} 与载入值不一致；"
                    "拓扑或几何变化必须构造并 freeze 新 Assembly，"
                    "当前 frozen Assembly 只能安装相同固定状态"
                )
                raise _errors.OpticalRuntimeError(
                    _FROZEN_DIRECTIONAL_STATE_MISMATCH,
                    message,
                )


def _identify_source_resizes(
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
    source_plans: tuple[tuple[torch.nn.Module, _SourceStatePlan], ...],
) -> tuple[_SourceBufferResize, ...]:


    module_to_name = {
        id(module): name for name, module in module_by_name
    }
    resizes: list[_SourceBufferResize] = []
    seen_slots: set[tuple[int, str]] = set()
    for module, plan in source_plans:
        for buffer_name, target_shape in plan.buffer_shapes:
            slot = (id(module), buffer_name)
            if slot in seen_slots:
                continue
            current = module._buffers.get(buffer_name)
            if current is None or current.shape == target_shape:
                continue
            seen_slots.add(slot)
            owner_name = module_to_name[id(module)]
            prefix = f"{owner_name}." if owner_name else ""
            full_name = prefix + buffer_name
            resize = _SourceBufferResize(module, buffer_name, target_shape, full_name)
            resizes.append(resize)
    return tuple(resizes)


def _assert_resize_aliases_distinct(
    resizes: tuple[_SourceBufferResize, ...],
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
) -> None:

    if not resizes:
        return
    storage_slot_count = _build_storage_slot_count(module_by_name)
    for resize in resizes:
        current = resize.module._buffers[resize.buffer_name]
        assert current is not None
        storage_identity = int(current.untyped_storage()._cdata)
        if storage_slot_count.get(storage_identity, 0) > 1:
            message = (
                f"Source 缓冲 {resize.buffer_name} 注册槽与另一槽精确别名，"
                "无法 resize"
            )
            raise _errors.OpticalRuntimeError(_RESIZE_ALIAS_CONFLICT, message)


def _build_storage_slot_count(
    module_by_name: tuple[tuple[str, torch.nn.Module], ...],
) -> dict[int, int]:


    counts: dict[int, int] = {}
    seen_modules: set[int] = set()
    for _name, module in module_by_name:
        if id(module) in seen_modules:
            continue
        seen_modules.add(id(module))
        tensors = (
            *module._parameters.values(),
            *module._buffers.values(),
        )
        for tensor in tensors:
            if tensor is None:
                continue
            storage_identity = int(tensor.untyped_storage()._cdata)
            counts[storage_identity] = counts.get(storage_identity, 0) + 1
    return counts


def _build_exact_alias_groups(
    root: torch.nn.Module,
    state_dict: Mapping[str, object],
) -> tuple[tuple[str, ...], ...]:

    name_to_view: dict[str, _ExactViewKey] = {}
    for name, parameter in root.named_parameters(remove_duplicate=False):
        if parameter is not None and name in state_dict:
            name_to_view[name] = _exact_view_key(parameter)
    for name, buffer in root.named_buffers(remove_duplicate=False):
        if buffer is not None and name in state_dict:
            name_to_view[name] = _exact_view_key(buffer)
    grouped: dict[_ExactViewKey, list[str]] = {}
    for name, view_key in name_to_view.items():
        grouped.setdefault(view_key, []).append(name)
    return tuple(
        tuple(names) for names in grouped.values() if len(names) >= 2
    )


def _assert_alias_groups_consistent(
    alias_groups: tuple[tuple[str, ...], ...],
    state_dict: Mapping[str, object],
) -> None:

    for group in alias_groups:
        first_name = group[0]
        first_value = state_dict[first_name]
        if not isinstance(first_value, torch.Tensor):
            continue
        for other_name in group[1:]:
            other_value = state_dict[other_name]
            if not isinstance(other_value, torch.Tensor):
                continue
            if not _is_incoming_alias_value_equal(first_value, other_value):
                message = (
                    f"精确别名键 {first_name!r} 与 {other_name!r} 共享同一目标视图，"
                    "但值不一致"
                )
                raise _errors.OpticalRuntimeError(_ALIAS_CONFLICT, message)


def _is_incoming_alias_value_equal(
    first: torch.Tensor,
    other: torch.Tensor,
) -> bool:

    if first.dtype is not other.dtype:
        return False
    if tuple(first.shape) != tuple(other.shape):
        return False
    return bool(
        torch.equal(first.detach().cpu(), other.detach().cpu()),
    )


def _assert_registered_identity_snapshot_unchanged(
    root: torch.nn.Module,
    baseline: _RegisteredStateIdentitySnapshot,
) -> None:

    current_modules = tuple(root.named_modules(remove_duplicate=False))
    current = _take_registered_identity_snapshot(root, current_modules)
    if current.module_identities != baseline.module_identities:
        message = "状态安装规划期间目标模块树结构发生漂移"
        raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)
    if current.parameter_identities != baseline.parameter_identities:
        message = "状态安装规划期间目标参数身份发生漂移"
        raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)
    lineage_changed = (
        current.source_lineage_identities
        != baseline.source_lineage_identities
    )
    if lineage_changed:
        message = "状态安装规划期间目标 Source Lineage 发生漂移"
        raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)
    if current.topology != baseline.topology:
        message = "状态安装规划期间目标拓扑名发生漂移"
        raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)


def _apply_state_installation_plan(plan: _StateInstallationPlan) -> None:

    snapshot = _take_state_application_snapshot(plan.root)
    try:
        staged = _stage_source_resizes(plan.source_resizes)
        resized_views_by_id = {
            id(tensor): _exact_view_key(tensor)
            for tensor in staged
        }
        _rebind_source_resizes(plan.source_resizes, staged)
        _run_native_state_load(plan.root, plan.frozen_state_dict)
        _prove_postcondition(plan, resized_views_by_id)
    except Exception as error:
        try:
            _restore_state_application_snapshot(plan.root, snapshot)
        except Exception as rollback_error:
            message = "状态安装失败后的目标状态无法恢复"
            raise _errors.OpticalRuntimeError(
                _ROLLBACK_FAILED,
                message,
            ) from rollback_error
        if isinstance(error, _errors.OpticalError):
            raise
        message = "状态安装应用阶段失败，目标状态已恢复"
        raise _errors.OpticalRuntimeError(
            _APPLICATION_FAILED,
            message,
        ) from error


def _take_state_application_snapshot(
    root: torch.nn.Module,
) -> _StateApplicationSnapshot:
    persistent_state = {
        name: (
            value.detach().clone()
            if isinstance(value, torch.Tensor)
            else copy.deepcopy(value)
        )
        for name, value in root.state_dict().items()
    }
    parameter_values: list[tuple[torch.nn.Parameter, torch.Tensor]] = []
    seen_parameters: set[int] = set()
    buffer_values: list[
        tuple[torch.nn.Module, str, torch.Tensor, torch.Tensor]
    ] = []
    for module in root.modules():
        for parameter in module._parameters.values():
            if parameter is None or id(parameter) in seen_parameters:
                continue
            seen_parameters.add(id(parameter))
            parameter_values.append((parameter, parameter.detach().clone()))
        for name, buffer in module._buffers.items():
            if buffer is None:
                continue
            buffer_values.append(
                (module, name, buffer, buffer.detach().clone()),
            )
    return _StateApplicationSnapshot(
        persistent_state=MappingProxyType(persistent_state),
        parameter_values=tuple(parameter_values),
        buffer_values=tuple(buffer_values),
    )


def _restore_state_application_snapshot(
    root: torch.nn.Module,
    snapshot: _StateApplicationSnapshot,
) -> None:
    for module, name, buffer, _value in snapshot.buffer_values:
        module._buffers[name] = buffer
    with torch.no_grad():
        for parameter, value in snapshot.parameter_values:
            parameter.copy_(value)
        for _module, _name, buffer, value in snapshot.buffer_values:
            buffer.copy_(value)
    _run_native_state_load(root, snapshot.persistent_state)


def _stage_source_resizes(
    resizes: tuple[_SourceBufferResize, ...],
) -> tuple[torch.Tensor, ...]:

    staged: list[torch.Tensor] = []
    for resize in resizes:
        current = resize.module._buffers[resize.buffer_name]
        assert current is not None
        staged.append(
            torch.empty(
                resize.target_shape,
                dtype=current.dtype,
                device=current.device,
            ),
        )
    return tuple(staged)


def _rebind_source_resizes(
    resizes: tuple[_SourceBufferResize, ...],
    staged: tuple[torch.Tensor, ...],
) -> None:

    for resize, new_buffer in zip(resizes, staged, strict=True):
        resize.module._buffers[resize.buffer_name] = new_buffer


def _run_native_state_load(
    root: torch.nn.Module,
    frozen_state_dict: Mapping[str, object],
) -> None:


    torch.nn.Module.load_state_dict(
        root,
        frozen_state_dict,
        strict=True,
        assign=False,
    )


def _prove_postcondition(
    plan: _StateInstallationPlan,
    resized_views_by_id: Mapping[int, _ExactViewKey],
) -> None:



    root = plan.root
    current_modules = tuple(root.named_modules(remove_duplicate=False))
    current = _take_registered_identity_snapshot(root, current_modules)
    if current.module_identities != plan.registered_identity_snapshot.module_identities:
        message = "状态安装后目标模块拓扑改变，违反载入后件"
        raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)
    if (
        current.parameter_identities
        != plan.registered_identity_snapshot.parameter_identities
    ):
        message = "状态安装后 Parameter 身份改变，违反载入后件"
        raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)
    lineage_changed = (
        current.source_lineage_identities
        != plan.registered_identity_snapshot.source_lineage_identities
    )
    if lineage_changed:
        message = "状态安装后 Source Lineage 改变，违反载入后件"
        raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)
    if current.topology != plan.registered_identity_snapshot.topology:
        message = "状态安装后模块拓扑名改变，违反载入后件"
        raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)
    baseline_views = dict(plan.registered_identity_snapshot.buffer_view_keys)
    current_views = dict(current.buffer_view_keys)
    current_buffer_ids = {
        name: id(buffer)
        for name, buffer in root.named_buffers(remove_duplicate=False)
        if buffer is not None and name in current_views
    }
    for name, baseline_view in baseline_views.items():
        actual_view = current_views.get(name)
        current_id = current_buffer_ids.get(name)
        if current_id is not None and current_id in resized_views_by_id:
            expected_view = resized_views_by_id[current_id]
        else:
            expected_view = baseline_view
        if actual_view != expected_view:
            message = f"状态安装后命名缓冲 {name!r} 的存储/视图身份改变，违反载入后件"
            raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)
    current_alias_groups = _build_exact_alias_groups(root, plan.frozen_state_dict)
    if set(map(frozenset, current_alias_groups)) != set(
        map(frozenset, plan.alias_groups),
    ):
        message = "状态安装后精确别名分组改变，违反载入后件"
        raise _errors.OpticalRuntimeError(_TARGET_CHANGED, message)

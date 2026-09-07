from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os
import threading
from typing import Literal, TypeAlias, TypeVar, cast
import weakref

import torch

import chromatix_next.errors as _errors

_W = TypeVar("_W")

_HOST_PERSISTENCE_METHODS: tuple[str, ...] = (
    "load_state_dict",
    "_load_from_state_dict",
)

@dataclass(frozen=True, slots=True)
class _ImmutableHostedRootClaim:
    """
    冻结工作站对模块、Parameter、storage 与守卫的弱身份独占托管声明

    """

    workstation: weakref.ReferenceType[object]
    root: weakref.ReferenceType[torch.nn.Module]
    modules: tuple[weakref.ReferenceType[torch.nn.Module], ...]
    module_identities: frozenset[int]
    parameter_identities: frozenset[int]
    storage_identities: frozenset[int]
    guard_handles: tuple[
        tuple[weakref.ReferenceType[torch.nn.Module], object], ...
    ]

    def live_modules(self) -> tuple[torch.nn.Module, ...] | None:
        live_modules = tuple(reference() for reference in self.modules)
        if any(module is None for module in live_modules):
            return None
        return tuple(
            module
            for module in live_modules
            if isinstance(module, torch.nn.Module)
        )


@dataclass(frozen=True, slots=True)
class _WeakHostedClaimBinding:

    """
    以弱引用关联模块树与托管声明

    """

    reference: weakref.ReferenceType[object]
    claim: _ImmutableHostedRootClaim


_HOST_CLAIMS: weakref.WeakKeyDictionary[
    torch.nn.Module, _ImmutableHostedRootClaim
] = weakref.WeakKeyDictionary()
_HOST_CLAIMS_LOCK = threading.RLock()


_PARAMETER_CLAIMS: dict[int, _WeakHostedClaimBinding] = {}
_STORAGE_CLAIMS: dict[int, _WeakHostedClaimBinding] = {}
_WINDOWS_CUDA_WORKSTATION: weakref.ReferenceType[object] | None = None
_WINDOWS_CUDA_WORKSTATION_LOCK = threading.RLock()


def _is_windows_platform() -> bool:
    return os.name == "nt"


def _collect_module_parameters(
    modules: tuple[torch.nn.Module, ...],
) -> tuple[torch.nn.Parameter, ...]:
    # 共享 Parameter 按对象身份只登记一次

    seen: dict[int, torch.nn.Parameter] = {}
    for module in modules:
        for parameter in module._parameters.values():
            if parameter is None:
                continue
            seen.setdefault(id(parameter), parameter)
    return tuple(seen.values())


def _collect_module_storages(
    modules: tuple[torch.nn.Module, ...],
) -> tuple[object, ...]:
    # Storage 身份是跨别名与模块树的所有权键
    seen: dict[int, object] = {}
    for module in modules:
        for parameter in module._parameters.values():
            if parameter is None:
                continue
            storage = parameter.untyped_storage()
            seen.setdefault(int(storage._cdata), storage)
        for buffer in module._buffers.values():
            if buffer is None:
                continue
            storage = buffer.untyped_storage()
            seen.setdefault(int(storage._cdata), storage)
    return tuple(seen.values())


def _register_parameter_claim(
    parameter: torch.nn.Parameter,
    claim: _ImmutableHostedRootClaim,
) -> None:
    # 弱引用终结时清除 Parameter claim，避免身份复用误判
    identity = id(parameter)

    def _release(
        expired: weakref.ReferenceType[torch.nn.Parameter],
        identity: int = identity,
    ) -> None:
        with _HOST_CLAIMS_LOCK:
            binding = _PARAMETER_CLAIMS.get(identity)
            if binding is not None and binding.reference is expired:
                del _PARAMETER_CLAIMS[identity]

    reference = cast(
        weakref.ReferenceType[object],
        weakref.ref(parameter, _release),
    )
    _PARAMETER_CLAIMS[identity] = _WeakHostedClaimBinding(
        reference=reference,
        claim=claim,
    )


def _register_storage_claim(
    storage: object,
    claim: _ImmutableHostedRootClaim,
) -> None:
    # 弱引用终结时清除 storage claim，避免保留已释放存储

    identity = int(storage._cdata)  # type: ignore[attr-defined]

    def _release(
        expired: weakref.ReferenceType[object],
        identity: int = identity,
    ) -> None:
        with _HOST_CLAIMS_LOCK:
            binding = _STORAGE_CLAIMS.get(identity)
            if binding is not None and binding.reference is expired:
                del _STORAGE_CLAIMS[identity]

    reference = weakref.ref(storage, _release)
    _STORAGE_CLAIMS[identity] = _WeakHostedClaimBinding(
        reference=reference,
        claim=claim,
    )


def _lookup_parameter_claim(
    parameter: torch.nn.Parameter,
) -> _ImmutableHostedRootClaim | None:
    # 过期弱引用立即清理，返回当前 Parameter 所属 claim

    identity = id(parameter)
    binding = _PARAMETER_CLAIMS.get(identity)
    if binding is None:
        return None
    if binding.reference() is None:
        del _PARAMETER_CLAIMS[identity]
        return None
    return binding.claim


def _lookup_storage_claim(
    storage: object,
) -> _ImmutableHostedRootClaim | None:
    # 过期弱引用立即清理，返回当前 storage 所属 claim

    identity = int(storage._cdata)  # type: ignore[attr-defined]
    binding = _STORAGE_CLAIMS.get(identity)
    if binding is None:
        return None
    if binding.reference() is None:
        del _STORAGE_CLAIMS[identity]
        return None
    return binding.claim


def _clear_host_claim(claim: _ImmutableHostedRootClaim) -> None:
    # 清理模块、Parameter、storage 与托管期守卫的整组身份

    for module_reference in claim.modules:
        module = module_reference()
        if module is not None and _HOST_CLAIMS.get(module) is claim:
            del _HOST_CLAIMS[module]
    for parameter_identity in claim.parameter_identities:
        binding = _PARAMETER_CLAIMS.get(parameter_identity)
        if binding is not None and binding.claim is claim:
            del _PARAMETER_CLAIMS[parameter_identity]
    for storage_identity in claim.storage_identities:
        binding = _STORAGE_CLAIMS.get(storage_identity)
        if binding is not None and binding.claim is claim:
            del _STORAGE_CLAIMS[storage_identity]
    for module_reference, handle in claim.guard_handles:
        if module_reference() is not None:
            handle.remove()  # type: ignore[attr-defined]


def _is_hosted_tree_current(
    modules: tuple[torch.nn.Module, ...],
    claim: _ImmutableHostedRootClaim,
) -> bool:
    hosted_modules = claim.live_modules()
    if hosted_modules is None or len(modules) != len(hosted_modules):
        return False
    if any(
        current is not hosted
        for current, hosted in zip(modules, hosted_modules, strict=True)
    ):
        return False
    return (
        frozenset(id(module) for module in modules) == claim.module_identities
    )


def _preflight_host_tree(
    workstation: object,
    root: torch.nn.Module,
    modules: tuple[torch.nn.Module, ...],
    parameters: tuple[torch.nn.Parameter, ...],
    storages: tuple[object, ...],
) -> Literal["unhosted", "same_root"]:
    # 调用方持锁；这里原子判定整棵树的所有权

    module_claims = tuple(_HOST_CLAIMS.get(module) for module in modules)
    expired_claims: list[_ImmutableHostedRootClaim] = []
    for claim in module_claims:
        if (
            claim is not None
            and (claim.workstation() is None or claim.root() is None)
            and all(claim is not existing for existing in expired_claims)
        ):
            expired_claims.append(claim)
    for expired_claim in expired_claims:
        _clear_host_claim(expired_claim)
    if expired_claims:
        module_claims = tuple(_HOST_CLAIMS.get(module) for module in modules)
    parameter_claims = tuple(
        _lookup_parameter_claim(parameter) for parameter in parameters
    )
    storage_claims = tuple(_lookup_storage_claim(storage) for storage in storages)
    if (
        all(claim is None for claim in module_claims)
        and all(claim is None for claim in parameter_claims)
        and all(claim is None for claim in storage_claims)
    ):
        return "unhosted"
    root_claim = _HOST_CLAIMS.get(root)
    if root_claim is not None:
        owner = root_claim.workstation()
        claimed_root = root_claim.root()
        if owner is workstation and claimed_root is root:
            if not _is_hosted_tree_current(modules, root_claim):
                raise _errors.WorkstationError(
                    "workstation_host_tree_changed",
                    "这棵树上次托管之后结构变了，重复托管只对完全相同的树幂等",
                )
            if (
                all(claim is root_claim for claim in module_claims)
                and all(claim is root_claim for claim in parameter_claims)
                and all(claim is root_claim for claim in storage_claims)
            ):
                return "same_root"
            raise _errors.WorkstationError(
                "workstation_host_ownership_corrupted",
                "这棵树的托管记录不完整，无法通过重复托管修复",
            )
        if owner is not workstation:
            raise _errors.WorkstationError(
                "workstation_host_already_hosted",
                "这棵树已经被另一个工作站托管，托管不会跨工作站转移",
            )
    if (
        any(
            claim is not None and claim.workstation() is not workstation
            for claim in module_claims
        )
        or any(
            claim is not None and claim.workstation() is not workstation
            for claim in parameter_claims
        )
        or any(
            claim is not None and claim.workstation() is not workstation
            for claim in storage_claims
        )
    ):
        raise _errors.WorkstationError(
            "workstation_host_already_hosted",
            "这棵树里有模块、参数或张量存储已经被另一个工作站托管，"
            "托管不会跨工作站转移，也不会在失败前移动任何数据",
        )
    raise _errors.WorkstationError(
        "workstation_host_partial_ownership",
        "这棵树只有一部分被本工作站托管，或者它是经另一个根托管的；"
        "请托管完整的树，或先解除原来的托管",
    )


def _reject_persistence_override_or_shadow(
    modules: tuple[torch.nn.Module, ...],
) -> None:
    # 类型或实例覆盖会绕过 hosted-load 守卫，因此在放置前拒绝

    for module in modules:
        module_type = type(module)
        for method_name in _HOST_PERSISTENCE_METHODS:
            if (
                getattr(module_type, method_name, None)
                is not getattr(torch.nn.Module, method_name, None)
                or method_name in module.__dict__
            ):
                raise _errors.WorkstationError(
                    "workstation_host_persistence_unsupported",
                    f"模块 {module_type.__name__} 覆盖或实例 shadow 了 "
                    f"{method_name}，托管只接受默认持久化，"
                    "以使 hosted-load 守卫无法被绕过",
                )


_PartialViewKey: TypeAlias = tuple[
    int, tuple[int, ...], tuple[int, ...], torch.dtype
]


def _reject_partial_storage_views(
    modules: tuple[torch.nn.Module, ...],
) -> None:
    # 仅允许精确别名，不接受同 storage 的异形视图

    view_by_storage: dict[int, list[_PartialViewKey]] = {}
    for module in modules:
        for parameter in module._parameters.values():
            if parameter is None:
                continue
            storage = parameter.untyped_storage()
            view_by_storage.setdefault(int(storage._cdata), []).append(
                (
                    int(parameter.storage_offset()),
                    tuple(parameter.shape),
                    tuple(parameter.stride()),
                    parameter.dtype,
                )
            )
        for buffer in module._buffers.values():
            if buffer is None:
                continue
            storage = buffer.untyped_storage()
            view_by_storage.setdefault(int(storage._cdata), []).append(
                (
                    int(buffer.storage_offset()),
                    tuple(buffer.shape),
                    tuple(buffer.stride()),
                    buffer.dtype,
                )
            )
    for views in view_by_storage.values():
        if len(views) < 2:
            continue
        first = views[0]
        for other in views[1:]:
            if other != first:
                raise _errors.WorkstationError(
                    "workstation_host_partial_storage_view",
                    "这棵托管树里同一底层存储上挂了两个不同的局部视图；"
                    "托管只接受同一对象复用或精确别名"
                    "（偏移、形状、步长、dtype 全同），不接受局部重叠；"
                    "请显式解除别名或分别托管独立的存储",
                )


class _HostedStateLoadGuard:
    """
    以活 claim 阻断原生状态载入，并在未托管副本上保持惰性

    """

    __slots__ = ()

    def __call__(
        self,
        module: torch.nn.Module,
        state_dict: Mapping[str, object],
        prefix: str,
        local_metadata: Mapping[str, object],
        is_strict: bool,
        missing_keys: list[str],
        unexpected_keys: list[str],
        error_messages: list[str],
    ) -> None:
        # 托管期间载入会破坏注册身份，必须在 release 后进行
        del state_dict, prefix, local_metadata, is_strict, missing_keys
        del unexpected_keys, error_messages
        with _HOST_CLAIMS_LOCK:
            claim = _HOST_CLAIMS.get(module)
            if claim is None or claim.workstation() is None or claim.root() is None:
                return
        raise _errors.WorkstationError(
            "workstation_hosted_state_load_forbidden",
            "已托管根或其内部模块上禁止原生 load_state_dict；"
            "请先 release 再 install_state",
        )

    def __reduce__(self) -> tuple[object, ...]:
        return (_rebuild_hosted_state_load_guard, ())


def _rebuild_hosted_state_load_guard() -> _HostedStateLoadGuard:

    return _HostedStateLoadGuard()


def _install_hosted_state_load_guards(
    modules: tuple[torch.nn.Module, ...],
) -> tuple[
    tuple[tuple[weakref.ReferenceType[torch.nn.Module], object], ...],
    tuple[
        tuple[
            weakref.ReferenceType[torch.nn.Module],
            tuple[tuple[int, object], ...],
        ],
        ...,
    ],
]:
    # 安装前快照 hook 顺序；失败时恢复原顺序与旧守卫

    installed: list[tuple[torch.nn.Module, object]] = []
    pre_host_snapshot: list[
        tuple[weakref.ReferenceType[torch.nn.Module], tuple[tuple[int, object], ...]]
    ] = [
        (weakref.ref(module), tuple(module._load_state_dict_pre_hooks.items()))
        for module in modules
    ]
    try:
        for module in modules:
            stale_ids = [
                handle_id
                for handle_id, hook in module._load_state_dict_pre_hooks.items()
                if isinstance(getattr(hook, "hook", hook), _HostedStateLoadGuard)
            ]
            for handle_id in stale_ids:
                del module._load_state_dict_pre_hooks[handle_id]
            handle = module.register_load_state_dict_pre_hook(_HostedStateLoadGuard())
            module._load_state_dict_pre_hooks.move_to_end(  # type: ignore[attr-defined]
                handle.id,
                last=False,
            )
            installed.append((module, handle))
    except BaseException:
        _restore_pre_hooks_snapshot(tuple(pre_host_snapshot))
        raise
    return (
        tuple((weakref.ref(module), handle) for module, handle in installed),
        tuple(pre_host_snapshot),
    )


def _restore_pre_hooks_snapshot(
    pre_host_snapshot: tuple[
        tuple[
            weakref.ReferenceType[torch.nn.Module],
            tuple[tuple[int, object], ...],
        ],
        ...,
    ],
) -> None:
    # 回滚按原顺序恢复全部 hook

    for module_reference, items in pre_host_snapshot:
        module = module_reference()
        if module is None:
            continue
        hooks_dict = module._load_state_dict_pre_hooks
        hooks_dict.clear()
        for handle_id, hook in items:
            hooks_dict[handle_id] = cast("Callable[..., object]", hook)


@dataclass(frozen=True, slots=True)
class _TensorGraphSnapshot:


    """
    记录托管事务前的参数与缓冲区绑定

    """

    parameter_rebinds: tuple[tuple[torch.nn.Parameter, torch.Tensor], ...]
    buffer_rebinds: tuple[tuple[torch.nn.Module, str, torch.Tensor], ...]


def _snapshot_registered_tensor_graph(
    modules: tuple[torch.nn.Module, ...],
) -> _TensorGraphSnapshot:
    # 快照记录 Parameter 数据与 Buffer 对象，供原子回滚

    parameter_rebinds: list[tuple[torch.nn.Parameter, torch.Tensor]] = []
    buffer_rebinds: list[tuple[torch.nn.Module, str, torch.Tensor]] = []
    seen_parameters: set[int] = set()
    for module in modules:
        for parameter in module._parameters.values():
            if parameter is None or id(parameter) in seen_parameters:
                continue
            seen_parameters.add(id(parameter))
            parameter_rebinds.append((parameter, parameter.data))
        for name, buffer in module._buffers.items():
            if buffer is None:
                continue
            buffer_rebinds.append((module, name, buffer))
    return _TensorGraphSnapshot(
        parameter_rebinds=tuple(parameter_rebinds),
        buffer_rebinds=tuple(buffer_rebinds),
    )


def _restore_registered_tensor_graph(
    snapshot: _TensorGraphSnapshot,
) -> None:
    # placement 或 claim 失败时恢复注册张量图

    for parameter, original_data in snapshot.parameter_rebinds:
        parameter.data = original_data
    for module, name, original_buffer in snapshot.buffer_rebinds:
        module._buffers[name] = original_buffer


def _verify_placed_identity_graph(
    snapshot: _TensorGraphSnapshot,
    workstation: object,
) -> None:
    # placement 后验证设备、视图与精确别名分区

    device = workstation.device  # type: ignore[attr-defined]
    pairs: list[tuple[torch.Tensor, torch.Tensor]] = []
    for parameter, original_data in snapshot.parameter_rebinds:
        pairs.append((parameter.data, original_data))
    for module, name, original_buffer in snapshot.buffer_rebinds:
        current = module._buffers.get(name)
        if current is None:
            raise _errors.WorkstationError(
                "workstation_host_identity_graph_unstable",
                f"placement 后 {name!r} Buffer 槽变空，违反托管不变量",
            )
        pairs.append((current, original_buffer))
    storage_group_after: dict[int, set[int]] = {}
    for current, original in pairs:
        if (
            current.device != device
            or current.dtype is not original.dtype
            or int(current.storage_offset()) != int(original.storage_offset())
            or tuple(current.shape) != tuple(original.shape)
            or tuple(current.stride()) != tuple(original.stride())
        ):
            raise _errors.WorkstationError(
                "workstation_host_identity_graph_unstable",
                "placement 后 Parameter/Buffer 设备、dtype 或视图漂移，"
                "违反托管不变量",
            )
        old_cdata = int(original.untyped_storage()._cdata)
        new_cdata = int(current.untyped_storage()._cdata)
        storage_group_after.setdefault(old_cdata, set()).add(new_cdata)
    for new_cdatas in storage_group_after.values():
        if len(new_cdatas) > 1:
            raise _errors.WorkstationError(
                "workstation_host_identity_graph_unstable",
                "placement 后精确别名分组断开：共享同一 storage 的张量未被一起迁移，"
                "违反托管不变量",
            )


def _host_root(
    workstation: object,
    root: torch.nn.Module,
    modules: tuple[torch.nn.Module, ...],
    parameters: tuple[torch.nn.Parameter, ...],
    storages: tuple[object, ...],
    guard_handles: tuple[
        tuple[weakref.ReferenceType[torch.nn.Module], object], ...
    ],
) -> None:
    # claim 同时登记模块、Parameter 与 storage，保持整树所有权

    claim = _ImmutableHostedRootClaim(
        workstation=weakref.ref(workstation),
        root=weakref.ref(root),
        modules=tuple(weakref.ref(module) for module in modules),
        module_identities=frozenset(id(module) for module in modules),
        parameter_identities=frozenset(
            id(parameter) for parameter in parameters
        ),
        storage_identities=frozenset(
            int(storage._cdata) for storage in storages  # type: ignore[attr-defined]
        ),
        guard_handles=guard_handles,
    )
    try:
        for submodule in modules:
            _HOST_CLAIMS[submodule] = claim
        for parameter in parameters:
            _register_parameter_claim(parameter, claim)
        for storage in storages:
            _register_storage_claim(storage, claim)
    except BaseException:
        _clear_host_claim(claim)
        raise


def _commit_host(
    workstation: object,
    root: torch.nn.Module,
    place: Callable[[tuple[torch.nn.Module, ...]], None],
) -> None:
    # staging、验证、claim 在同一锁内提交；异常回滚全部可见状态

    modules = tuple(root.modules())
    parameters = _collect_module_parameters(modules)
    candidate_storages = _collect_module_storages(modules)
    with _HOST_CLAIMS_LOCK:
        state = _preflight_host_tree(
            workstation,
            root,
            modules,
            parameters,
            candidate_storages,
        )
        if state == "same_root":
            return
        _reject_partial_storage_views(modules)
        _reject_persistence_override_or_shadow(modules)
        guard_handles, pre_host_snapshot = _install_hosted_state_load_guards(modules)
        try:
            snapshot = _snapshot_registered_tensor_graph(modules)
            try:
                place(modules)
                _verify_placed_identity_graph(snapshot, workstation)
                owned_storages = _collect_module_storages(modules)
                _host_root(
                    workstation,
                    root,
                    modules,
                    parameters,
                    owned_storages,
                    guard_handles,
                )
            except BaseException:
                _restore_registered_tensor_graph(snapshot)
                raise
        except BaseException:
            # 失败时恢复 host 前的 hook 快照
            _restore_pre_hooks_snapshot(pre_host_snapshot)
            raise


def _release_root(
    workstation: object,
    component: torch.nn.Module,
    modules: tuple[torch.nn.Module, ...],
) -> None:


    with _HOST_CLAIMS_LOCK:
        root_claim = _HOST_CLAIMS.get(component)
        if root_claim is None:
            original_root_claims: list[_ImmutableHostedRootClaim] = []
            for registered_claim in _HOST_CLAIMS.values():
                if (
                    registered_claim.root() is component
                    and all(
                        registered_claim is not existing
                        for existing in original_root_claims
                    )
                ):
                    original_root_claims.append(registered_claim)
            if len(original_root_claims) == 1:
                root_claim = original_root_claims[0]
            visible_claims = tuple(
                _HOST_CLAIMS.get(module)
                for module in modules
                if _HOST_CLAIMS.get(module) is not None
            )
            if root_claim is None and visible_claims:
                raise _errors.WorkstationError(
                    "workstation_release_not_root",
                    "这棵树没有以当前对象为根托管；"
                    "请用首次传给 host 的完整根解除托管",
                )
            if root_claim is None:
                raise _errors.WorkstationError(
                    "workstation_release_not_hosted",
                    "这个对象没有被工作站托管，无需解除",
                )
        owner = root_claim.workstation()
        if owner is not workstation:
            raise _errors.WorkstationError(
                "workstation_release_hosted_elsewhere",
                "这个对象由另一个工作站托管，只能由拥有它的工作站解除托管",
            )
        if root_claim.root() is not component:
            raise _errors.WorkstationError(
                "workstation_release_not_root",
                "这个对象只是另一棵托管树的内部模块；"
                "请用首次传给 host 的完整根解除托管",
            )
        _clear_host_claim(root_claim)


def _assert_hosted(
    workstation: object,
    root: torch.nn.Module,
) -> tuple[torch.nn.Module, ...]:


    with _HOST_CLAIMS_LOCK:
        claim = _HOST_CLAIMS.get(root)
        if claim is None:
            raise _errors.WorkstationError(
                "workstation_run_not_hosted",
                "这个计算根还没有被托管，请先调用 host 再调用 run",
            )
        if claim.workstation() is not workstation or claim.root() is not root:
            raise _errors.WorkstationError(
                "workstation_run_hosted_elsewhere",
                "这个计算根由另一个工作站或另一个根托管，"
                "请在托管它的那个工作站上运行",
            )
        modules = tuple(root.modules())
        if not _is_hosted_tree_current(modules, claim):
            raise _errors.WorkstationError(
                "workstation_run_host_tree_changed",
                "托管之后模块树结构变了，请解除原托管后再运行",
            )
        if any(_HOST_CLAIMS.get(module) is not claim for module in modules):
            raise _errors.WorkstationError(
                "workstation_run_not_hosted",
                "托管树里有模块的所有权记录丢失或损坏，无法运行",
            )
        hosted_modules = claim.live_modules()
        if hosted_modules is None:
            raise _errors.WorkstationError(
                "workstation_run_host_tree_changed",
                "首次托管的模块树已不完整，无法运行",
            )
    return hosted_modules


def _is_windows_cuda_singleton_occupied() -> bool:

    live = (
        None
        if _WINDOWS_CUDA_WORKSTATION is None
        else _WINDOWS_CUDA_WORKSTATION()
    )
    return live is not None


def _occupy_windows_cuda_singleton(workstation: object) -> None:

    global _WINDOWS_CUDA_WORKSTATION
    _WINDOWS_CUDA_WORKSTATION = weakref.ref(workstation)


_WorkstationT = TypeVar("_WorkstationT")


def _claim_windows_cuda_singleton(
    factory: Callable[[], _WorkstationT],
) -> _WorkstationT:
    # Windows 单例占用在 factory 成功后才提交

    if not _is_windows_platform():
        return factory()
    with _WINDOWS_CUDA_WORKSTATION_LOCK:
        if _is_windows_cuda_singleton_occupied():
            raise _errors.WorkstationError(
                "workstation_windows_cuda_singleton_required",
                "Windows 本地工作站同一时刻只允许一个 CUDA 工作站；"
                "请先释放现有工作站对象再创建新的 CUDA 工作站",
            )
        workstation = factory()
        _occupy_windows_cuda_singleton(workstation)
        return workstation


def _run_unhosted_state_installation(
    root: torch.nn.Module,
    operation: Callable[[], None],
) -> None:
    # state 安装只在完全 unhosted 根上执行，operation 在锁内一次完成

    modules = tuple(root.modules())
    parameters = _collect_module_parameters(modules)
    storages = _collect_module_storages(modules)
    with _HOST_CLAIMS_LOCK:
        _reject_any_claimed_identity(modules, parameters, storages)
        operation()


def _reject_any_claimed_identity(
    modules: tuple[torch.nn.Module, ...],
    parameters: tuple[torch.nn.Parameter, ...],
    storages: tuple[object, ...],
) -> None:
    # 任一模块、Parameter 或 storage 已 claim 都拒绝安装

    reject_identity = "workstation_hosted_state_load_forbidden"
    reject_message = (
        "状态安装要求整棵模块树当前未被托管；请先 release 再 install_state"
    )
    for module in modules:
        claim = _HOST_CLAIMS.get(module)
        if claim is not None and (
            claim.workstation() is None or claim.root() is None
        ):
            _clear_host_claim(claim)
    if any(_HOST_CLAIMS.get(module) is not None for module in modules):
        raise _errors.WorkstationError(reject_identity, reject_message)
    for parameter in parameters:
        if _lookup_parameter_claim(parameter) is not None:
            raise _errors.WorkstationError(reject_identity, reject_message)
    for storage in storages:
        if _lookup_storage_claim(storage) is not None:
            raise _errors.WorkstationError(
                reject_identity,
                "这棵树里有张量存储与另一棵托管树共享；状态安装不接受跨根共享存储",
            )

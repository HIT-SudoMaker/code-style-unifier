from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence, Set
import contextlib
from contextvars import ContextVar
import copy
from dataclasses import dataclass
from typing import Any

import torch
from torch.overrides import TorchFunctionMode
from torch.utils._python_dispatch import TorchDispatchMode

import chromatix_next.errors as _errors

from .element.ideal_cube_beam_splitter import (
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
)
from .element.ideal_planar_mirror import IdealPlanarMirror

_META_DEVICE = torch.device("meta")

_IS_REAL_GRID_METADATA_ALLOWED = ContextVar(
    "is_real_grid_metadata_allowed",
    default=False,
)

_REAL_GRID_METADATA_ELEMENT_LIMIT = 1

_REAL_GRID_METADATA_STORAGE_IDS: ContextVar[frozenset[int]] = ContextVar(
    "real_grid_metadata_storage_ids",
    default=frozenset(),
)

_IS_META_INFERENCE_ACTIVE: ContextVar[bool] = ContextVar(
    "is_meta_inference_active",
    default=False,
)

_DIRECTIONAL_METADATA_STORAGE_IDS: ContextVar[frozenset[int]] = ContextVar(
    "directional_metadata_storage_ids",
    default=frozenset(),
)

_DIRECTIONAL_METADATA_OPERATION_NAMES = frozenset(
    {
        "aten::_local_scalar_dense",
        "aten::_to_copy",
        "aten::abs",
        "aten::add",
        "aten::all",
        "aten::clone",
        "aten::detach",
        "aten::div",
        "aten::dot",
        "aten::eq",
        "aten::equal",
        "aten::le",
        "aten::linalg_cross",
        "aten::linalg_vector_norm",
        "aten::mul",
        "aten::ne",
        "aten::neg",
        "aten::sqrt",
        "aten::sub",
    }
)

_DIRECTIONAL_CUBE_OWNER_TYPES = (
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
)

def _is_meta_inference_active() -> bool:
    # 返回当前是否处在 meta 推导沙箱上下文中

    return _IS_META_INFERENCE_ACTIVE.get()


@contextlib.contextmanager
def _real_grid_precheck() -> Iterator[None]:
    token = _IS_REAL_GRID_METADATA_ALLOWED.set(True)
    storage_token = _REAL_GRID_METADATA_STORAGE_IDS.set(frozenset())
    try:
        yield
    finally:
        _REAL_GRID_METADATA_STORAGE_IDS.reset(storage_token)
        _IS_REAL_GRID_METADATA_ALLOWED.reset(token)


def _require_meta_device(requested: object) -> None:
    # 所有推导模式共用同一设备解释与稳定错误，保证真实工厂在调用前即被拒绝
    if requested is None:
        return
    if not isinstance(requested, (str, int, torch.device)):
        raise _errors.OpticalRuntimeError(
            "meta_sandbox_device_request_invalid",
            "meta 推导收到无法解释的张量设备请求；"
            "组件只能跟随入射物理值的设备",
        )
    device = torch.device(requested)
    if device.type != "meta":
        raise _errors.OpticalRuntimeError(
            f"meta_sandbox_real_tensor_forbidden:{device.type}",
            "meta 推导期间组件显式请求了真实设备张量；"
            "检查只能产生不占真实存储的 meta 派生量",
        )


def _grid_metadata_payload_size(value: object) -> int:
    if isinstance(value, torch.Tensor):
        return value.numel()
    numel = getattr(value, "numel", None)
    if callable(numel):
        try:
            resolved_numel = numel()
            return (
                resolved_numel
                if isinstance(resolved_numel, int)
                else _REAL_GRID_METADATA_ELEMENT_LIMIT + 1
            )
        except (TypeError, ValueError):
            return _REAL_GRID_METADATA_ELEMENT_LIMIT + 1
    size = getattr(value, "size", None)
    if isinstance(size, int):
        return size
    if isinstance(value, Mapping):
        return sum(
            _grid_metadata_payload_size(item)
            for item in value.values()
        )
    if isinstance(value, (tuple, list, set, frozenset, Set)):
        return sum(_grid_metadata_payload_size(item) for item in value)
    return 1


def _raise_grid_metadata_too_large(
    function: object,
    *,
    stage: str,
) -> None:
    raise _errors.OpticalRuntimeError(
        f"meta_sandbox_grid_metadata_too_large:{stage}:{function}",
        "meta 推导只允许 _output_grid_for 计算单元素实际网格元数据；"
        "数组、扩展视图和场规模张量在执行前即被拒绝",
    )


def _is_single_value_grid_metadata_tensor(tensor: torch.Tensor) -> bool:
    if tensor.numel() <= _REAL_GRID_METADATA_ELEMENT_LIMIT:
        return True
    return (
        int(tensor.untyped_storage()._cdata)
        in _REAL_GRID_METADATA_STORAGE_IDS.get()
    )


def _remember_grid_metadata_tensor(tensor: torch.Tensor) -> None:
    storage_identity = int(tensor.untyped_storage()._cdata)
    _REAL_GRID_METADATA_STORAGE_IDS.set(
        _REAL_GRID_METADATA_STORAGE_IDS.get() | {storage_identity}
    )


_DirectionalMetadataSnapshot = tuple[
    torch.nn.Module, str, torch.Tensor, torch.Tensor, int
]


@contextlib.contextmanager
def _bind_directional_metadata_snapshots(
    snapshots: tuple[_DirectionalMetadataSnapshot, ...],
) -> Iterator[None]:
    storage_ids = frozenset(
        int(value.untyped_storage()._cdata)
        for _module, _name, _meta, value, _version in snapshots
    )
    token = _DIRECTIONAL_METADATA_STORAGE_IDS.set(storage_ids)
    try:
        for module, name, meta, value, _version in snapshots:
            current = module._buffers.get(name)
            if current is not meta:
                raise _errors.OpticalRuntimeError(
                    "meta_sandbox_registered_state_modified",
                    "closed directional owner 的 meta 元数据绑定在重放前已经改变",
                )
            module._buffers[name] = value
        yield
    finally:
        binding_changed = False
        for module, name, meta, value, version in snapshots:
            current = module._buffers.get(name)
            binding_changed = binding_changed or (
                current is not value or value._version != version
            )
            module._buffers[name] = meta
        _DIRECTIONAL_METADATA_STORAGE_IDS.reset(token)
        if binding_changed:
            raise _errors.OpticalRuntimeError(
                "meta_sandbox_registered_state_modified",
                "meta 重放修改或替换了 closed directional owner 的只读元数据快照",
            )


def _factory_device_request(
    function: object,
    arguments: tuple[object, ...],
    keywords: dict[str, object],
) -> object:
    # 设备参数只从关键字或支持的旧位置读取；此守卫不执行真实分配
    if "device" in keywords:
        return keywords["device"]
    if (
        function in (torch.tensor, torch.as_tensor, torch.asarray)
        and len(arguments) > 2
    ):
        return arguments[2]
    return None


def _is_scalar_uint8_topology_factory(
    function: object,
    arguments: tuple[object, ...],
    keywords: dict[str, object],
) -> bool:
    if not _DIRECTIONAL_METADATA_STORAGE_IDS.get():
        return False
    schema_name = getattr(getattr(function, "_schema", None), "name", "")
    if function not in (torch.ones, torch.zeros) and schema_name not in {
        "aten::ones",
        "aten::zeros",
    }:
        return False
    if len(arguments) != 1:
        return False
    try:
        shape = tuple(arguments[0])  # type: ignore[arg-type]
        device = torch.device(keywords.get("device"))  # type: ignore[arg-type]
    except (TypeError, RuntimeError):
        return False
    return (
        shape == ()
        and keywords.get("dtype") is torch.uint8
        and device.type == "cpu"
    )


def _is_directional_metadata_to(
    function: object,
    arguments: tuple[object, ...],
    keywords: dict[str, object],
) -> bool:
    tensor = arguments[0] if arguments else None
    if (
        getattr(function, "__name__", None) != "to"
        or not isinstance(tensor, torch.Tensor)
    ):
        return False
    try:
        device = torch.device(keywords.get("device", tensor.device))
    except (TypeError, RuntimeError):
        return False
    return (
        tensor.device.type == "cpu"
        and tensor.dtype in {torch.bool, torch.float64, torch.uint8}
        and tensor.numel() <= 3
        and int(tensor.untyped_storage()._cdata)
        in _DIRECTIONAL_METADATA_STORAGE_IDS.get()
        and keywords.get("dtype", tensor.dtype) is tensor.dtype
        and device.type in {"cpu", "meta"}
    )


@dataclass(frozen=True)
class _MetaSandbox:
    """
    隔离只允许 meta 形状推导并映射原模块身份的执行上下文

    """

    _module_by_identity: dict[int, torch.nn.Module]
    _readonly_tensors: tuple[torch.Tensor, ...]
    _owned_tensors: tuple[torch.Tensor, ...]
    _registered_states: tuple[_RegisteredState, ...]
    _directional_metadata_snapshots: tuple[
        _DirectionalMetadataSnapshot,
        ...,
    ]

    def module(self, original: torch.nn.Module) -> torch.nn.Module:
        """
        返回一个原模块在隔离模块树中的 meta 副本

        """
        return self._module_by_identity[id(original)]

    def require_registered_state_unchanged(self) -> None:
        """
        确认沙箱内的固定注册状态没有被原位修改或重新绑定

        """
        is_changed = any(
            state.current_tensor() is not state.tensor
            or int(state.tensor.untyped_storage()._cdata)
            != state.storage_identity
            or state.tensor._version != state.version
            for state in self._registered_states
        )
        if is_changed:
            raise _errors.OpticalRuntimeError(
                "meta_sandbox_registered_state_modified",
                "meta 推导期间有组件修改了固定注册状态；"
                "检查只能读取 Parameter 与持久 Buffer，"
                "派生缓存应写入非持久 Buffer",
            )


@dataclass(frozen=True)
class _RegisteredState:

    """
    记录 meta 推导前的注册张量及其存储身份

    """

    module: torch.nn.Module
    collection_name: str
    name: str
    tensor: torch.Tensor
    storage_identity: int
    version: int

    def current_tensor(self) -> torch.Tensor | None:
        """
        返回当前仍绑定在同一注册槽位的张量

        """
        collection = getattr(self.module, self.collection_name)
        return collection.get(self.name)


class _MetaFactoryGuard(TorchFunctionMode):

    """
    禁止 meta 推导物化真实张量

    """

    def __torch_function__(
        self,
        function: object,
        types: object,
        arguments: tuple[object, ...] = (),
        keywords: dict[str, object] | None = None,
    ) -> object:
        del types
        assert callable(function)
        resolved_keywords = keywords or {}
        is_grid_metadata = _IS_REAL_GRID_METADATA_ALLOWED.get()
        if is_grid_metadata and function in (
            torch.tensor,
            torch.as_tensor,
            torch.asarray,
        ):
            factory_payload = (
                arguments[0]
                if arguments
                else resolved_keywords.get("data")
            )
            if (
                factory_payload is not None
                and _grid_metadata_payload_size(factory_payload)
                > _REAL_GRID_METADATA_ELEMENT_LIMIT
            ):
                _raise_grid_metadata_too_large(
                    function,
                    stage="factory_payload",
                )
        if not is_grid_metadata:
            if not _is_scalar_uint8_topology_factory(
                function,
                arguments,
                resolved_keywords,
            ) and not _is_directional_metadata_to(
                function,
                arguments,
                resolved_keywords,
            ):
                _require_meta_device(
                    _factory_device_request(
                        function,
                        arguments,
                        resolved_keywords,
                    )
                )
        return function(*arguments, **resolved_keywords)


class _MetaDeviceGuard(TorchDispatchMode):
    """
    在算子执行前拒绝真实设备并守卫所有张量结果仍位于 meta

    """

    def __init__(self, readonly_tensors: Sequence[torch.Tensor]) -> None:
        super().__init__()
        self._readonly_tensor_ids = {
            id(tensor)
            for tensor in readonly_tensors
        }
        self._readonly_storage_ids = {
            int(tensor.untyped_storage()._cdata)
            for tensor in readonly_tensors
        }

    def __torch_dispatch__(
        self,
        function: object,
        types: object,
        arguments: tuple[object, ...] = (),
        keywords: dict[str, object] | None = None,
    ) -> object:
        del types
        assert callable(function)
        resolved_keywords = keywords or {}
        self._reject_registered_state_write(
            function,
            arguments,
            resolved_keywords,
        )
        real_inputs = tuple(
            tensor
            for tensor in self._argument_tensors(
                (arguments, resolved_keywords),
            )
            if tensor.device.type != "meta"
        )
        is_directional_metadata = self._is_directional_metadata_operation(
            function,
            real_inputs,
        )
        is_real_to_meta_projection = self._is_real_to_meta_projection(
            function,
            real_inputs,
            resolved_keywords,
        )
        if (
            real_inputs
            and not is_directional_metadata
            and not is_real_to_meta_projection
            and not _IS_REAL_GRID_METADATA_ALLOWED.get()
        ):
            raise _errors.OpticalRuntimeError(
                "meta_sandbox_real_tensor_forbidden:directional_metadata_input",
                "meta 推导只允许 fixed-double 输入作同 dtype 的 Meta 投影，"
                "或让 exact directional metadata 进入白名单小型运算",
            )
        self._reject_real_device_request(
            function,
            arguments,
            resolved_keywords,
            is_directional_metadata=is_directional_metadata,
        )
        self._preflight_grid_metadata_operation(
            function,
            arguments,
            resolved_keywords,
        )
        result = function(*arguments, **resolved_keywords)
        if (
            is_directional_metadata
            or _is_scalar_uint8_topology_factory(
                function,
                arguments,
                resolved_keywords,
            )
        ):
            self._remember_directional_metadata_results(result)
        self._require_derived_results(
            function,
            arguments,
            resolved_keywords,
            result,
        )
        return result

    def _reject_registered_state_write(
        self,
        function: object,
        arguments: tuple[object, ...],
        keywords: dict[str, object],
    ) -> None:
        schema = getattr(function, "_schema", None)
        schema_arguments = getattr(schema, "arguments", ())
        for index, schema_argument in enumerate(schema_arguments):
            alias_info = getattr(schema_argument, "alias_info", None)
            if alias_info is None or not getattr(alias_info, "is_write", False):
                continue
            value = (
                arguments[index]
                if index < len(arguments)
                else keywords.get(getattr(schema_argument, "name", ""))
            )
            if isinstance(value, torch.Tensor) and (
                id(value) in self._readonly_tensor_ids
                or int(value.untyped_storage()._cdata)
                in self._readonly_storage_ids
            ):
                raise _errors.OpticalRuntimeError(
                    "meta_sandbox_registered_state_modified",
                    "meta 推导期间有元件尝试原位修改共享的固定注册状态；"
                    "检查只能读取固定物理值，派生状态请写入元件副本自己的缓存槽",
                )

    @classmethod
    def _is_directional_metadata_operation(
        cls,
        function: object,
        real_inputs: tuple[torch.Tensor, ...],
    ) -> bool:
        storage_ids = _DIRECTIONAL_METADATA_STORAGE_IDS.get()
        schema_name = getattr(
            getattr(function, "_schema", None),
            "name",
            None,
        )
        return bool(real_inputs) and (
            schema_name in _DIRECTIONAL_METADATA_OPERATION_NAMES
            and all(
                tensor.device.type == "cpu"
                and tensor.dtype in {torch.bool, torch.float64, torch.uint8}
                and tensor.numel() <= 3
                and int(tensor.untyped_storage()._cdata) in storage_ids
                for tensor in real_inputs
            )
        )

    @staticmethod
    def _is_real_to_meta_projection(
        function: object,
        real_inputs: tuple[torch.Tensor, ...],
        keywords: dict[str, object],
    ) -> bool:
        schema_name = getattr(getattr(function, "_schema", None), "name", None)
        if schema_name != "aten::_to_copy" or len(real_inputs) != 1:
            return False
        tensor = real_inputs[0]
        requested_dtype = keywords.get("dtype") or tensor.dtype
        try:
            requested_device = torch.device(
                keywords.get("device"),  # type: ignore[arg-type]
            )
        except (TypeError, RuntimeError):
            return False
        return (
            requested_device.type == "meta"
            and tensor.dtype in {torch.float64, torch.complex128}
            and requested_dtype is tensor.dtype
            and tensor.layout is torch.strided
            and keywords.get("layout") in {None, torch.strided}
            and keywords.get("pin_memory") in {None, False}
            and keywords.get("memory_format") in {None, torch.preserve_format}
        )

    @classmethod
    def _remember_directional_metadata_results(cls, result: object) -> None:
        tensors = tuple(
            tensor
            for tensor in cls._result_tensors(result)
            if tensor.device.type != "meta"
        )
        if any(
            tensor.device.type != "cpu"
            or tensor.dtype not in {torch.bool, torch.float64, torch.uint8}
            or tensor.numel() > 3
            for tensor in tensors
        ):
            raise _errors.OpticalRuntimeError(
                "meta_sandbox_real_tensor_forbidden:directional_metadata_result",
                "closed directional owner 元数据只能派生三个以内的 CPU 分量",
            )
        storage_ids = {
            int(tensor.untyped_storage()._cdata)
            for tensor in tensors
        }
        _DIRECTIONAL_METADATA_STORAGE_IDS.set(
            _DIRECTIONAL_METADATA_STORAGE_IDS.get() | storage_ids,
        )

    @staticmethod
    def _reject_real_device_request(
        function: object,
        arguments: tuple[object, ...],
        keywords: dict[str, object],
        *,
        is_directional_metadata: bool,
    ) -> None:
        if _IS_REAL_GRID_METADATA_ALLOWED.get() or is_directional_metadata:
            return
        if _is_scalar_uint8_topology_factory(
            function,
            arguments,
            keywords,
        ):
            return
        schema = getattr(function, "_schema", None)
        schema_arguments = getattr(schema, "arguments", ())
        for index, schema_argument in enumerate(schema_arguments):
            if getattr(schema_argument, "name", None) != "device":
                continue
            requested = (
                arguments[index]
                if index < len(arguments)
                else keywords.get("device")
            )
            _require_meta_device(requested)

    @classmethod
    def _preflight_grid_metadata_operation(
        cls,
        function: object,
        arguments: tuple[object, ...],
        keywords: dict[str, object],
    ) -> None:
        if not _IS_REAL_GRID_METADATA_ALLOWED.get():
            return
        assert callable(function)
        input_tensors = tuple(
            cls._argument_tensors(arguments)
        ) + tuple(cls._argument_tensors(keywords))
        schema = getattr(function, "_schema", None)
        schema_arguments = getattr(schema, "arguments", ())
        requested_devices = tuple(
            (
                arguments[index]
                if index < len(arguments)
                else keywords.get("device")
            )
            for index, schema_argument in enumerate(schema_arguments)
            if getattr(schema_argument, "name", None) == "device"
        )
        has_real_device_request = any(
            requested is not None
            and (
                not isinstance(
                    requested,
                    (str, int, torch.device),
                )
                or torch.device(requested).type != "meta"
            )
            for requested in requested_devices
        )
        if (
            not any(
                tensor.device.type != "meta"
                for tensor in input_tensors
            )
            and not has_real_device_request
        ):
            return
        if any(
            tensor.device.type != "meta"
            and not _is_single_value_grid_metadata_tensor(tensor)
            for tensor in input_tensors
        ):
            _raise_grid_metadata_too_large(function, stage="operator_input")
        if getattr(schema, "name", None) in {
            "aten::_local_scalar_dense",
            "aten::equal",
            "aten::select",
            "aten::view_as_real",
        }:
            return
        meta_arguments = cls._meta_projection(arguments)
        meta_keywords = cls._meta_projection(keywords)
        assert isinstance(meta_arguments, tuple)
        assert isinstance(meta_keywords, dict)
        meta_arguments, meta_keywords = cls._project_device_arguments_to_meta(
            schema,
            meta_arguments,
            meta_keywords,
        )
        projected_result = function(
            *meta_arguments,
            **meta_keywords,
        )
        result_tensors = tuple(cls._result_tensors(projected_result))
        if any(
            tensor.numel() > _REAL_GRID_METADATA_ELEMENT_LIMIT
            for tensor in result_tensors
        ):
            _raise_grid_metadata_too_large(
                function,
                stage=(
                    "operator_result_"
                    + "_".join(
                        str(tuple(tensor.shape))
                        for tensor in result_tensors
                    )
                ),
            )

    @classmethod
    def _meta_projection(cls, value: object) -> object:
        if isinstance(value, torch.Tensor):
            return torch.empty_like(value, device=_META_DEVICE)
        if isinstance(value, tuple):
            return tuple(cls._meta_projection(item) for item in value)
        if isinstance(value, list):
            return [cls._meta_projection(item) for item in value]
        if isinstance(value, dict):
            return {
                key: cls._meta_projection(item)
                for key, item in value.items()
            }
        return value

    @staticmethod
    def _project_device_arguments_to_meta(
        schema: object,
        arguments: tuple[object, ...],
        keywords: dict[str, object],
    ) -> tuple[tuple[object, ...], dict[str, object]]:
        resolved_arguments = list(arguments)
        schema_arguments = getattr(schema, "arguments", ())
        for index, schema_argument in enumerate(schema_arguments):
            if getattr(schema_argument, "name", None) != "device":
                continue
            if index < len(arguments):
                resolved_arguments[index] = _META_DEVICE
            elif "device" in keywords:
                keywords["device"] = _META_DEVICE
        return tuple(resolved_arguments), keywords

    @classmethod
    def _argument_tensors(cls, value: object) -> Iterator[torch.Tensor]:
        if isinstance(value, torch.Tensor):
            yield value
            return
        if isinstance(value, (tuple, list)):
            for item in value:
                yield from cls._argument_tensors(item)
            return
        if isinstance(value, dict):
            for item in value.values():
                yield from cls._argument_tensors(item)

    @classmethod
    def _require_derived_results(
        cls,
        function: object,
        arguments: tuple[object, ...],
        keywords: dict[str, object],
        result: object,
    ) -> None:
        schema = getattr(function, "_schema", None)
        is_scalar_storage_view = (
            getattr(schema, "name", None) == "aten::view_as_real"
            and all(
                _is_single_value_grid_metadata_tensor(tensor)
                for tensor in cls._argument_tensors(
                    (
                        arguments,
                        keywords,
                    )
                )
            )
        )
        for tensor in cls._result_tensors(result):
            if tensor.device.type == "meta":
                continue
            if (
                tensor.device.type == "cpu"
                and tensor.dtype in {torch.bool, torch.float64, torch.uint8}
                and tensor.numel() <= 3
                and int(tensor.untyped_storage()._cdata)
                in _DIRECTIONAL_METADATA_STORAGE_IDS.get()
            ):
                continue
            if (
                _IS_REAL_GRID_METADATA_ALLOWED.get()
                and (
                    tensor.numel()
                    <= _REAL_GRID_METADATA_ELEMENT_LIMIT
                    or is_scalar_storage_view
                )
            ):
                _remember_grid_metadata_tensor(tensor)
                continue
            identity = (
                "meta_sandbox_grid_metadata_too_large"
                if _IS_REAL_GRID_METADATA_ALLOWED.get()
                else "meta_sandbox_real_tensor_forbidden"
            )
            raise _errors.OpticalRuntimeError(
                f"{identity}:operator_result:{tensor.numel()}:"
                f"{tensor.device.type}:{function}",
                "meta 推导只允许 _output_grid_for 短暂计算单元素实际网格元数据；"
                "场规模张量、批量张量和其他真实设备分配均被拒绝",
            )

    @classmethod
    def _result_tensors(cls, result: object) -> Iterator[torch.Tensor]:
        if isinstance(result, torch.Tensor):
            yield result
            return
        if isinstance(result, (tuple, list)):
            for item in result:
                yield from cls._result_tensors(item)
            return
        if isinstance(result, dict):
            for item in result.values():
                yield from cls._result_tensors(item)


@contextlib.contextmanager
def _meta_inference(
    modules: Sequence[torch.nn.Module],
) -> Iterator[_MetaSandbox]:
    sandbox = _copy_to_meta_sandbox(modules)
    active_token = _IS_META_INFERENCE_ACTIVE.set(True)
    try:
        with (
            _bind_directional_metadata_snapshots(
                sandbox._directional_metadata_snapshots,
            ),
            torch.device(_META_DEVICE),
            _MetaFactoryGuard(),
            _MetaDeviceGuard(sandbox._readonly_tensors),
        ):
            yield sandbox
    finally:
        _IS_META_INFERENCE_ACTIVE.reset(active_token)
        sandbox.require_registered_state_unchanged()


def _copy_to_meta_sandbox(
    modules: Sequence[torch.nn.Module],
) -> _MetaSandbox:
    _require_finite_registered_state(modules)
    memo: dict[int, Any] = {}
    for module in modules:
        for parameter in module._parameters.values():
            if parameter is None or id(parameter) in memo:
                continue
            memo[id(parameter)] = torch.nn.Parameter(
                _meta_counterpart(parameter),
                requires_grad=parameter.requires_grad,
            )
        for buffer in module._buffers.values():
            if buffer is None or id(buffer) in memo:
                continue
            memo[id(buffer)] = _meta_counterpart(buffer)

    try:
        for module in modules:
            if id(module) not in memo:
                copy.deepcopy(module, memo)
    except Exception as error:
        raise _errors.OpticalRuntimeError(
            f"meta_sandbox_copy_failed:{type(error).__name__}",
            "组件状态无法复制到隔离的 meta 沙箱；"
            "请把张量状态注册为 Parameter 或 Buffer，"
            "并避免在组件中持有不可复制的运行时资源",
        ) from error

    module_by_identity = {
        id(module): memo[id(module)]
        for module in modules
    }
    directional_metadata_snapshots = _directional_metadata_snapshots(
        modules,
        module_by_identity,
    )
    registered_states: list[_RegisteredState] = []
    for module in modules:
        sandbox_module = module_by_identity[id(module)]
        for name, parameter in module._parameters.items():
            if parameter is None:
                continue
            sandbox_parameter = sandbox_module._parameters[name]
            assert sandbox_parameter is not None
            registered_states.append(
                _capture_registered_state(
                    sandbox_module,
                    "_parameters",
                    name,
                    sandbox_parameter,
                )
            )
        for name, buffer in module._buffers.items():
            if buffer is None or name in module._non_persistent_buffers_set:
                continue
            sandbox_buffer = sandbox_module._buffers[name]
            assert sandbox_buffer is not None
            registered_states.append(
                _capture_registered_state(
                    sandbox_module,
                    "_buffers",
                    name,
                    sandbox_buffer,
                )
            )

    snapshot_values = tuple(
        snapshot[3] for snapshot in directional_metadata_snapshots
    )
    readonly_tensors = tuple(
        {
            id(tensor): tensor
            for tensor in (
                *(state.tensor for state in registered_states),
                *snapshot_values,
            )
        }.values()
    )
    owned_tensors = tuple(
        {
            id(tensor): tensor
            for tensor in (
                *(
                    tensor
                    for module in module_by_identity.values()
                    for tensor in (
                        *module._parameters.values(),
                        *module._buffers.values(),
                    )
                    if tensor is not None
                ),
                *snapshot_values,
            )
        }.values()
    )
    return _MetaSandbox(
        module_by_identity,
        readonly_tensors,
        owned_tensors,
        tuple(registered_states),
        directional_metadata_snapshots,
    )


def _directional_metadata_snapshots(
    modules: Sequence[torch.nn.Module],
    module_by_identity: Mapping[int, torch.nn.Module],
) -> tuple[_DirectionalMetadataSnapshot, ...]:
    snapshots: list[_DirectionalMetadataSnapshot] = []
    for module in modules:
        if type(module) in _DIRECTIONAL_CUBE_OWNER_TYPES:
            buffer_names = (
                "origin",
                "route_right",
                "route_top",
                "_coating_diagonal_code",
            )
        elif type(module) is IdealPlanarMirror:
            buffer_names = ("origin", "outward_normal", "transverse_up")
        else:
            continue
        module._validate_physical_state()  # type: ignore[attr-defined]  # noqa: SLF001
        sandbox_module = module_by_identity[id(module)]
        for buffer_name in buffer_names:
            is_diagonal = buffer_name == "_coating_diagonal_code"
            expected_shape = torch.Size(()) if is_diagonal else torch.Size((3,))
            expected_dtype = torch.uint8 if is_diagonal else torch.float64
            value = module._buffers.get(buffer_name)
            if (
                not isinstance(value, torch.Tensor)
                or value.shape != expected_shape
                or value.dtype is not expected_dtype
                or value.is_meta
            ):
                raise _errors.OpticalRuntimeError(
                    "meta_sandbox_copy_failed:directional_metadata_buffer",
                    "closed directional owner 的固定元数据必须保持冻结的 shape、"
                    "dtype 与真实设备状态",
                )
            value_snapshot = value.detach().to(device="cpu").clone()
            meta_buffer = sandbox_module._buffers.get(buffer_name)
            if (
                not isinstance(meta_buffer, torch.Tensor)
                or not meta_buffer.is_meta
            ):
                raise _errors.OpticalRuntimeError(
                    "meta_sandbox_copy_failed:directional_metadata_buffer",
                    "closed directional owner 的固定元数据没有形成 meta 沙箱副本",
                )
            snapshots.append(
                (
                    sandbox_module,
                    buffer_name,
                    meta_buffer,
                    value_snapshot,
                    value_snapshot._version,
                ),
            )
    return tuple(snapshots)


def _require_finite_registered_state(
    modules: Sequence[torch.nn.Module],
) -> None:
    # Parameter 与持久 Buffer 的有限性是取值预检，不属于形状/内存 meta 推导
    checked_tensors: set[int] = set()
    for module in modules:
        if callable(getattr(module, "_validate_physical_state", None)):
            continue
        registered_tensors = tuple(module._parameters.items()) + tuple(
            (
                name,
                buffer,
            )
            for name, buffer in module._buffers.items()
            if name not in module._non_persistent_buffers_set
        )
        for name, tensor in registered_tensors:
            if (
                tensor is None
                or id(tensor) in checked_tensors
                or tensor.is_meta
                or not (
                    tensor.is_floating_point()
                    or torch.is_complex(tensor)
                )
            ):
                continue
            checked_tensors.add(id(tensor))
            if not bool(torch.isfinite(tensor.detach()).all()):
                raise _errors.OpticalRuntimeError(
                    "meta_preflight_registered_state_nonfinite:"
                    f"{type(module).__name__}:{name}",
                    "装配预检发现 Parameter 或持久 Buffer 含有非有限值；"
                    "请在搭建或优化后恢复有限物理状态",
                )


def _capture_registered_state(
    module: torch.nn.Module,
    collection_name: str,
    name: str,
    tensor: torch.Tensor,
) -> _RegisteredState:
    return _RegisteredState(
        module=module,
        collection_name=collection_name,
        name=name,
        tensor=tensor,
        storage_identity=int(tensor.untyped_storage()._cdata),
        version=tensor._version,
    )


def _meta_counterpart(
    tensor: torch.Tensor,
) -> torch.Tensor:
    # 返回同形同类的 meta 张量；固定双精度（ADR-0005）下原 dtype 即目标 dtype
    return torch.empty_like(tensor, device=_META_DEVICE, dtype=tensor.dtype)

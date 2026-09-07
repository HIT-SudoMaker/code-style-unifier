from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
import contextlib
import ctypes
from dataclasses import fields, is_dataclass
import os
import weakref

import torch
from torch.overrides import TorchFunctionMode
from torch.utils._python_dispatch import TorchDispatchMode

import chromatix_next.errors as _errors

_COMPLEX_ITEMSIZE = torch.complex128.itemsize

_REAL_ITEMSIZE = torch.float64.itemsize

_CONSERVATIVE_ALLOCATION_GRANULARITY_BYTES = 512



def _windows_physical_memory_bytes() -> int:
    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(_MemoryStatusEx)
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        error_identity = "workstation_cpu_memory_probe_failed"
        raise OSError(error_identity)
    return int(status.ullTotalPhys)


class _MemoryStatusEx(ctypes.Structure):  # type: ignore[misc]
    """
    以稳定字段扩展平台内存状态

    """

    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _cpu_physical_memory_bytes() -> int:
    if os.name == "nt":
        try:
            return _windows_physical_memory_bytes()
        except OSError:
            return 1 << 30
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages) * int(page_size)
    except (ValueError, OSError, AttributeError):
        return 1 << 30


_CPU_MEMORY_RESERVE_NUMERATOR = 9
_CPU_MEMORY_RESERVE_DENOMINATOR = 10


def _default_memory_boundary_bytes(device: torch.device) -> int:
    # CPU 预留 10% 余量；CUDA 只承诺设备总显存
    if device.type == "cuda":
        index = device.index if device.index is not None else 0
        try:
            properties = torch.cuda.get_device_properties(index)
        except RuntimeError as cause:
            raise _errors.WorkstationError(
                "workstation_cuda_boundary_unknown",
                f"读不到第 {index} 号 CUDA 设备的显存总量，无法确定内存边界",
            ) from cause
        return int(properties.total_memory)
    if device.type == "cpu":
        total = _cpu_physical_memory_bytes()
        return total * _CPU_MEMORY_RESERVE_NUMERATOR // _CPU_MEMORY_RESERVE_DENOMINATOR
    raise _errors.WorkstationError(
        f"workstation_memory_boundary_bytes_unknown:{device.type}",
        f"只支持 cpu 与 cuda 两种设备的内存边界，收到的是 {device.type}",
    )

def _owned_memory_bytes(
    modules: Sequence[torch.nn.Module],
) -> int:
    owned_bytes = 0
    counted_storages: set[int] = set()
    for module in modules:
        tensors: list[torch.Tensor | None] = list(
            module._parameters.values()
        )
        tensors.extend(module._buffers.values())
        for tensor in tensors:
            if tensor is None:
                continue
            storage_identity = int(tensor.untyped_storage()._cdata)
            if storage_identity in counted_storages:
                continue
            counted_storages.add(storage_identity)
            owned_bytes += _conservative_allocation_bytes(
                _storage_bytes(tensor)
            )
    return owned_bytes


def _conservative_peak_bytes(
    *,
    owned_bytes: int,
    dynamic_bytes: int,
) -> int:
    return int(owned_bytes) + int(dynamic_bytes)


def _conservative_allocation_bytes(byte_count: int) -> int:
    # 按固定粒度向上取整，覆盖张量存储的保守分配
    if byte_count <= 0:
        return 0
    granularity = _CONSERVATIVE_ALLOCATION_GRANULARITY_BYTES
    return ((int(byte_count) + granularity - 1) // granularity) * granularity


def _wave_cube_validation_workspace_bytes(storage_bytes: int) -> int:
    # finite/power invariant 同时保留两个 complex normalization 工作集
    complex_workspace = 2 * _conservative_allocation_bytes(storage_bytes)
    # 两个 real magnitude/power 工作集各占 complex storage 的一半
    real_workspace = 2 * _conservative_allocation_bytes(storage_bytes // 2)
    # 标量、归约与布尔临时量最多占十个统一分配粒度
    scalar_workspace = 10 * _CONSERVATIVE_ALLOCATION_GRANULARITY_BYTES
    return complex_workspace + real_workspace + scalar_workspace


def _storage_bytes(tensor: torch.Tensor) -> int:
    if torch.is_complex(tensor):
        itemsize = _COMPLEX_ITEMSIZE
    elif tensor.is_floating_point():
        itemsize = _REAL_ITEMSIZE
    else:
        itemsize = tensor.element_size()
    storage_byte_count = tensor.untyped_storage().nbytes()
    element_byte_count = tensor.element_size()
    storage_elements = storage_byte_count // element_byte_count
    return storage_elements * itemsize


class _StorageLifetimeTrace(TorchDispatchMode):
    """
    跟踪一次执行中计入峰值的张量存储生命周期

    """

    # 通用计算按 storage 生命周期计量，不强持有临时 Tensor wrapper

    def __init__(
        self,
        *,
        excluded_tensors: Sequence[torch.Tensor] = (),
    ) -> None:

        super().__init__()
        self._excluded_storage_ids = {
            int(tensor.untyped_storage()._cdata)
            for tensor in excluded_tensors
        }
        self._has_directional_meta_snapshots = (
            any(tensor.is_meta for tensor in excluded_tensors)
            and any(
                tensor.device.type == "cpu"
                and (
                    (tensor.dtype is torch.float64 and tensor.shape == (3,))
                    or (tensor.dtype is torch.uint8 and tensor.shape == ())
                )
                for tensor in excluded_tensors
            )
        )
        self._largest_wave_cube_modal_storage_bytes = 0
        self._wrapper_references: dict[
            int,
            weakref.ReferenceType[torch.Tensor],
        ] = {}
        self._storage_by_wrapper: dict[int, int] = {}
        self._references_by_storage: dict[int, int] = {}
        self._bytes_by_storage: dict[int, int] = {}
        self._live_bytes = 0
        self._peak_bytes = 0
        self._lifetime_trace: list[int] = []

    @property
    def peak_bytes(self) -> int:

        if self._largest_wave_cube_modal_storage_bytes == 0:
            return self._peak_bytes
        return self._peak_bytes + _wave_cube_validation_workspace_bytes(
            self._largest_wave_cube_modal_storage_bytes,
        )

    @property
    def allocation_trace(self) -> tuple[int, ...]:

        return tuple(self._lifetime_trace)

    def observe_value(self, value: object) -> None:

        self._observe_value(value, visited=set())

    def _observe_value(
        self,
        value: object,
        *,
        visited: set[int],
    ) -> None:
        if isinstance(value, torch.Tensor):
            self._observe_tensor(value)
            return
        value_identity = id(value)
        if value_identity in visited:
            return
        if isinstance(value, (tuple, list)):
            visited.add(value_identity)
            for item in value:
                self._observe_value(item, visited=visited)
            return
        if isinstance(value, Mapping):
            visited.add(value_identity)
            for item in value.values():
                self._observe_value(item, visited=visited)
            return
        if is_dataclass(value) and not isinstance(value, type):
            visited.add(value_identity)
            for field in fields(value):
                self._observe_value(
                    getattr(value, field.name),
                    visited=visited,
                )

    def keep_saved_tensor(self, tensor: torch.Tensor) -> torch.Tensor:

        self._observe_tensor(tensor)
        return tensor

    @staticmethod
    def restore_saved_tensor(tensor: torch.Tensor) -> torch.Tensor:

        return tensor

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
        self.observe_value(arguments)
        self.observe_value(resolved_keywords)
        result = function(*arguments, **resolved_keywords)
        self.observe_value(result)
        return result

    def _observe_tensor(self, tensor: torch.Tensor) -> None:
        tensor_identity = id(tensor)
        existing_reference = self._wrapper_references.get(tensor_identity)
        if existing_reference is not None and existing_reference() is tensor:
            return
        storage_identity = int(tensor.untyped_storage()._cdata)
        if storage_identity in self._excluded_storage_ids:
            return
        if (
            self._has_directional_meta_snapshots
            and tensor.is_meta
            and tensor.dtype is torch.complex128
            and tensor.ndim >= 2
            and tensor.shape[-2:] == (4, 2)
        ):
            self._largest_wave_cube_modal_storage_bytes = max(
                self._largest_wave_cube_modal_storage_bytes,
                _storage_bytes(tensor),
            )
        def _release(
            expired: weakref.ReferenceType[torch.Tensor],
        ) -> None:
            self._release_wrapper(tensor_identity, expired)

        reference = weakref.ref(tensor, _release)
        self._wrapper_references[tensor_identity] = reference
        self._storage_by_wrapper[tensor_identity] = storage_identity
        reference_count = self._references_by_storage.get(
            storage_identity,
            0,
        )
        if reference_count == 0:
            byte_count = _conservative_allocation_bytes(
                tensor.untyped_storage().nbytes()
            )
            self._bytes_by_storage[storage_identity] = byte_count
            self._live_bytes += byte_count
            if self._live_bytes > self._peak_bytes:
                self._peak_bytes = self._live_bytes
                self._lifetime_trace.append(self._peak_bytes)
        self._references_by_storage[storage_identity] = reference_count + 1

    def _release_wrapper(
        self,
        tensor_identity: int,
        expired_reference: weakref.ReferenceType[torch.Tensor],
    ) -> None:
        current_reference = self._wrapper_references.get(tensor_identity)
        if current_reference is not expired_reference:
            return
        self._wrapper_references.pop(tensor_identity, None)
        storage_identity = self._storage_by_wrapper.pop(tensor_identity)
        reference_count = self._references_by_storage[storage_identity] - 1
        if reference_count > 0:
            self._references_by_storage[storage_identity] = reference_count
            return
        self._references_by_storage.pop(storage_identity, None)
        self._live_bytes -= self._bytes_by_storage.pop(storage_identity)


class _StorageFactoryTrace(TorchFunctionMode):
    """
    记录外部张量工厂产生的设备本地存储

    """

    # 补足不进入 dispatcher 的公开工厂，并在 meta 阶段沿用真实设备拒绝规则

    def __init__(self, trace: _StorageLifetimeTrace) -> None:

        super().__init__()
        self._trace = trace

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
        result = function(*arguments, **resolved_keywords)
        self._trace.observe_value(result)
        return result


@contextlib.contextmanager
def _trace_storage_lifetimes(
    *,
    excluded_tensors: Sequence[torch.Tensor] = (),
) -> Iterator[_StorageLifetimeTrace]:
    # Meta 与真实重放共用同一生命周期模型
    trace = _StorageLifetimeTrace(excluded_tensors=excluded_tensors)
    with (
        trace,
        _StorageFactoryTrace(trace),
        torch.autograd.graph.saved_tensors_hooks(
            trace.keep_saved_tensor,
            trace.restore_saved_tensor,
        ),
    ):
        yield trace

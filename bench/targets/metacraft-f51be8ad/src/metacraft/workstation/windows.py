from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import UTC, datetime
import os
from pathlib import Path
import platform
import subprocess
from threading import Lock
from typing import Any

from .model import (
    Command,
    Host,
    LANE_MEMORY_BYTES,
    Lane,
    LogicalProcessor,
    Memory,
    StaleLane,
)


_ERROR_INSUFFICIENT_BUFFER = 122
_CREATE_SUSPENDED = 0x00000004
_CREATE_NO_WINDOW = 0x08000000
_CREATE_UNICODE_ENVIRONMENT = 0x00000400
_INFINITE = 0xFFFFFFFF
_WAIT_OBJECT_0 = 0
_WAIT_TIMEOUT = 258
_STILL_ACTIVE = 259
_CLEANUP_TIMEOUT_MS = 5000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_GROUP_INFORMATION_EX = 14
_JOB_OBJECT_LIMIT_AFFINITY = 0x00000010
_JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_active_lanes: set[tuple[tuple[int, int], ...]] = set()
_active_lanes_lock = Lock()
_INHERITED_ENVIRONMENT = frozenset(
    name.casefold()
    for name in (
        "ALLUSERSPROFILE",
        "APPDATA",
        "COMMONPROGRAMFILES",
        "COMMONPROGRAMFILES(X86)",
        "COMMONPROGRAMW6432",
        "COMSPEC",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "OS",
        "PATH",
        "PATHEXT",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "PROGRAMW6432",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    )
)


class _CpuSet(ctypes.Structure):
    _fields_ = [
        ("identifier", wintypes.DWORD),
        ("group", wintypes.WORD),
        ("logical_processor", wintypes.BYTE),
        ("core", wintypes.BYTE),
        ("cache", wintypes.BYTE),
        ("node", wintypes.BYTE),
        ("efficiency", wintypes.BYTE),
        ("flags", wintypes.BYTE),
        ("reserved", wintypes.DWORD),
        ("allocation_tag", ctypes.c_ulonglong),
    ]


class _ProcessorNumber(ctypes.Structure):
    _fields_ = [
        ("group", wintypes.WORD),
        ("number", wintypes.BYTE),
        ("reserved", wintypes.BYTE),
    ]


class _GroupAffinity(ctypes.Structure):
    _fields_ = [
        ("mask", ctypes.c_size_t),
        ("group", wintypes.WORD),
        ("reserved", wintypes.WORD * 3),
    ]


class _StartupInfo(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD),
        ("reserved", wintypes.LPWSTR),
        ("desktop", wintypes.LPWSTR),
        ("title", wintypes.LPWSTR),
        ("x", wintypes.DWORD),
        ("y", wintypes.DWORD),
        ("x_size", wintypes.DWORD),
        ("y_size", wintypes.DWORD),
        ("x_count_chars", wintypes.DWORD),
        ("y_count_chars", wintypes.DWORD),
        ("fill_attribute", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("show_window", wintypes.WORD),
        ("reserved_size", wintypes.WORD),
        ("reserved_data", ctypes.POINTER(wintypes.BYTE)),
        ("standard_input", wintypes.HANDLE),
        ("standard_output", wintypes.HANDLE),
        ("standard_error", wintypes.HANDLE),
    ]


class _ProcessInformation(ctypes.Structure):
    _fields_ = [
        ("process", wintypes.HANDLE),
        ("thread", wintypes.HANDLE),
        ("process_id", wintypes.DWORD),
        ("thread_id", wintypes.DWORD),
    ]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("per_process_time", ctypes.c_longlong),
        ("per_job_time", ctypes.c_longlong),
        ("limit_flags", wintypes.DWORD),
        ("minimum_working_set", ctypes.c_size_t),
        ("maximum_working_set", ctypes.c_size_t),
        ("active_process_limit", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority_class", wintypes.DWORD),
        ("scheduling_class", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("read_operations", ctypes.c_ulonglong),
        ("write_operations", ctypes.c_ulonglong),
        ("other_operations", ctypes.c_ulonglong),
        ("read_bytes", ctypes.c_ulonglong),
        ("write_bytes", ctypes.c_ulonglong),
        ("other_bytes", ctypes.c_ulonglong),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("basic", _BasicLimitInformation),
        ("io", _IoCounters),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory", ctypes.c_size_t),
        ("peak_job_memory", ctypes.c_size_t),
    ]


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.DWORD),
        ("memory_load", wintypes.DWORD),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


class Worker:
    """
    Owns one verified Windows process tree and its containment handles.
    """

    __slots__ = (
        "_effective_cpu_sets",
        "_is_closed",
        "_is_tree_stopped",
        "_job",
        "_lane",
        "_memory_limit",
        "_process",
        "_process_id",
        "_reservation",
        "_returncode",
    )

    def __init__(
        self,
        *,
        process: int,
        process_id: int,
        job: int,
        lane: Lane,
        effective_cpu_sets: tuple[int, ...],
        memory_limit: int,
        reservation: tuple[tuple[int, int], ...],
    ) -> None:
        """
        Retain the verified process, job, placement, and reservation handles.
        """

        self._process = process
        self._process_id = process_id
        self._job = job
        self._lane = lane
        self._effective_cpu_sets = effective_cpu_sets
        self._memory_limit = memory_limit
        self._reservation = reservation
        self._returncode: int | None = None
        self._is_tree_stopped = False
        self._is_closed = False

    @property
    def pid(self) -> int:
        """
        Return the native worker process identifier.
        """

        return self._process_id

    def wait(self, *, timeout: float | None = None) -> int:
        """
        Wait for this worker and return its native exit code.
        """

        if self._returncode is not None:
            return self._returncode
        milliseconds = (
            _INFINITE
            if timeout is None
            else max(0, min(_INFINITE - 1, int(timeout * 1000)))
        )
        result = _kernel32().WaitForSingleObject(self._process, milliseconds)
        if result == _WAIT_TIMEOUT:
            raise TimeoutError("worker_timeout")
        if result != _WAIT_OBJECT_0:
            _raise_windows_error("worker_wait_failed")
        code = wintypes.DWORD()
        if not _kernel32().GetExitCodeProcess(self._process, ctypes.byref(code)):
            _raise_windows_error("worker_exit_code_failed")
        if code.value == _STILL_ACTIVE:
            raise RuntimeError("worker_exit_code_unavailable")
        self._returncode = int(code.value)
        return self._returncode

    def as_mapping(self) -> dict[str, object]:
        """
        Return verified placement and containment evidence.
        """

        return {
            "effective_cpu_sets": len(self._effective_cpu_sets),
            "job_memory_bytes": self._memory_limit,
            "lane": self._lane.as_mapping(),
            "pid": self._process_id,
        }

    def close(self) -> None:
        """
        End the process tree if needed and release all native handles.
        """

        if self._is_closed:
            return
        failures: list[Exception] = []
        if self._job:
            is_termination_requested = bool(
                _kernel32().TerminateJobObject(self._job, 1)
            )
            is_root_stopped = (
                not self._process or _wait_for_stop(self._process)
            )
            try:
                _close_handle(self._job, "worker_job_close_failed")
            except Exception as error:
                failures.append(error)
            else:
                self._job = 0
                self._is_tree_stopped = is_root_stopped
            if (
                not is_termination_requested
                and not self._is_tree_stopped
            ):
                failures.append(RuntimeError("worker_tree_stop_failed"))
        if self._process:
            try:
                _close_handle(self._process, "worker_process_close_failed")
            except Exception as error:
                failures.append(error)
            else:
                self._process = 0
        if (
            not self._job
            and not self._process
            and self._is_tree_stopped
        ):
            _release_lane(self._reservation)
            self._is_closed = True
        elif not failures and not self._job and not self._process:
            failures.append(RuntimeError("worker_tree_stop_unverified"))
        if failures:
            raise ExceptionGroup("worker_close_failed", failures)

    def __enter__(self) -> Worker:
        """
        Return this owned process-tree handle.
        """

        return self

    def __exit__(self, *_args: object) -> None:
        """
        Close the complete process tree when its context ends.
        """

        self.close()


def observe() -> Host:
    """
    Observe Windows CPU-set locality and available NUMA memory.
    """

    if os.name != "nt":
        raise OSError("windows_workstation_required")
    logical_processors = _observe_logical_processors()
    nodes = tuple(
        sorted(
            {
                processor.numa_node
                for processor in logical_processors
            }
        )
    )
    memory = tuple(
        Memory(numa_node=node, available_bytes=_available_memory(node))
        for node in nodes
    )
    identity = platform.node().strip().lower() or "local-workstation"
    return Host(
        identity=identity,
        logical_processors=logical_processors,
        memory=memory,
        observed_at=datetime.now(UTC),
    )


def start(command: Command, lane: Lane) -> Worker:
    """
    Start one worker suspended, place it, verify it, and resume it.
    """

    if os.name != "nt":
        raise OSError("windows_workstation_required")
    if not lane.is_fresh_at(datetime.now(UTC)):
        raise StaleLane("lane_stale")
    executable = command.executable.expanduser().resolve()
    if not executable.is_file():
        raise ValueError("worker_executable_not_found")
    reservation = _reserve_lane(lane)
    kernel = _kernel32()
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        _release_lane(reservation)
        _raise_windows_error("job_create_failed")
    process = 0
    thread = 0
    is_assigned = False
    try:
        affinity = _limit_job(job, lane)
        startup = _StartupInfo()
        startup.size = ctypes.sizeof(startup)
        information = _ProcessInformation()
        command_line = ctypes.create_unicode_buffer(
            subprocess.list2cmdline(
                (str(executable), *command.arguments),
            )
        )
        environment = ctypes.create_unicode_buffer(_environment(command))
        directory = (
            None
            if command.directory is None
            else str(command.directory.expanduser().resolve())
        )
        created = kernel.CreateProcessW(
            str(executable),
            command_line,
            None,
            None,
            False,
            _CREATE_SUSPENDED
            | _CREATE_NO_WINDOW
            | _CREATE_UNICODE_ENVIRONMENT,
            environment,
            directory,
            ctypes.byref(startup),
            ctypes.byref(information),
        )
        if not created:
            _raise_windows_error("worker_create_failed")
        process = _handle(information.process)
        thread = _handle(information.thread)
        selected = tuple(
            processor.identifier
            for processor in lane._logical_processors
        )
        _set_cpu_sets(process, thread, selected)
        if not kernel.AssignProcessToJobObject(job, process):
            _raise_windows_error("job_assignment_failed")
        is_assigned = True
        process_sets = _get_process_cpu_sets(process)
        effective = _get_thread_cpu_sets(thread)
        if process_sets != selected or effective != selected:
            raise RuntimeError("worker_placement_mismatch")
        memory_limit, effective_affinity = _job_limits(job)
        if (
            memory_limit != LANE_MEMORY_BYTES
            or effective_affinity != affinity
        ):
            raise RuntimeError("worker_memory_limit_mismatch")
        effective_group, effective_group_affinity = _job_group_affinity(job)
        if (
            effective_group != lane.processor_group
            or effective_group_affinity != affinity
        ):
            raise RuntimeError("worker_job_placement_mismatch")
        resumed = kernel.ResumeThread(thread)
        if resumed == _INFINITE:
            _raise_windows_error("worker_resume_failed")
        _close_handle(thread, "worker_thread_close_failed")
        thread = 0
        return Worker(
            process=process,
            process_id=int(information.process_id),
            job=_handle(job),
            lane=lane,
            effective_cpu_sets=effective,
            memory_limit=memory_limit,
            reservation=reservation,
        )
    except BaseException as error:
        notes: list[str] = []
        if is_assigned:
            if not kernel.TerminateJobObject(job, 1):
                notes.append("worker_job_termination_failed")
        elif process and not kernel.TerminateProcess(process, 1):
            notes.append("worker_process_termination_failed")
        try:
            _close_handle(job, "failed_job_close_failed")
        except Exception as cleanup_error:
            notes.append(str(cleanup_error))
            is_job_closed = False
        else:
            is_job_closed = True
        is_process_stopped = not process or _wait_for_stop(process)
        if thread:
            try:
                _close_handle(thread, "failed_thread_close_failed")
            except Exception as cleanup_error:
                notes.append(str(cleanup_error))
        if process:
            try:
                _close_handle(process, "failed_process_close_failed")
            except Exception as cleanup_error:
                notes.append(str(cleanup_error))
        is_lane_safe = is_process_stopped and (
            is_job_closed if is_assigned else True
        )
        if is_lane_safe:
            _release_lane(reservation)
        else:
            notes.append("lane_retained_after_unverified_cleanup")
        for note in notes:
            error.add_note(note)
        raise


def _kernel32() -> Any:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetSystemCpuSetInformation.argtypes = (
        ctypes.c_void_p,
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.HANDLE,
        wintypes.ULONG,
    )
    kernel.GetSystemCpuSetInformation.restype = wintypes.BOOL
    kernel.GetNumaAvailableMemoryNodeEx.argtypes = (
        wintypes.USHORT,
        ctypes.POINTER(ctypes.c_ulonglong),
    )
    kernel.GetNumaAvailableMemoryNodeEx.restype = wintypes.BOOL
    kernel.GetNumaProcessorNodeEx.argtypes = (
        ctypes.POINTER(_ProcessorNumber),
        ctypes.POINTER(wintypes.USHORT),
    )
    kernel.GetNumaProcessorNodeEx.restype = wintypes.BOOL
    kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.QueryInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel.QueryInformationJobObject.restype = wintypes.BOOL
    kernel.CreateProcessW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(_StartupInfo),
        ctypes.POINTER(_ProcessInformation),
    )
    kernel.CreateProcessW.restype = wintypes.BOOL
    kernel.SetProcessDefaultCpuSets.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.ULONG,
    )
    kernel.SetProcessDefaultCpuSets.restype = wintypes.BOOL
    kernel.GetProcessDefaultCpuSets.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
    )
    kernel.GetProcessDefaultCpuSets.restype = wintypes.BOOL
    kernel.SetThreadSelectedCpuSets.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.ULONG,
    )
    kernel.SetThreadSelectedCpuSets.restype = wintypes.BOOL
    kernel.GetThreadSelectedCpuSets.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
    )
    kernel.GetThreadSelectedCpuSets.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = (
        wintypes.HANDLE,
        wintypes.HANDLE,
    )
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.ResumeThread.argtypes = (wintypes.HANDLE,)
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetExitCodeProcess.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.TerminateProcess.restype = wintypes.BOOL
    kernel.TerminateJobObject.argtypes = (
        wintypes.HANDLE,
        wintypes.UINT,
    )
    kernel.TerminateJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel


def _observe_logical_processors() -> tuple[LogicalProcessor, ...]:
    kernel = _kernel32()
    length = wintypes.ULONG()
    process = kernel.GetCurrentProcess()
    ctypes.set_last_error(0)
    kernel.GetSystemCpuSetInformation(
        None,
        0,
        ctypes.byref(length),
        process,
        0,
    )
    error = ctypes.get_last_error()
    if not length.value or error not in (0, _ERROR_INSUFFICIENT_BUFFER):
        _raise_windows_error("cpu_sets_size_failed")
    buffer = ctypes.create_string_buffer(length.value)
    if not kernel.GetSystemCpuSetInformation(
        buffer,
        length.value,
        ctypes.byref(length),
        process,
        0,
    ):
        _raise_windows_error("cpu_sets_read_failed")
    logical_processors = []
    offset = 0
    address = ctypes.addressof(buffer)
    while offset < length.value:
        size = ctypes.c_ulong.from_address(address + offset).value
        kind = ctypes.c_int.from_address(address + offset + 4).value
        if size < 8 or offset + size > length.value:
            raise RuntimeError("cpu_set_record_invalid")
        if kind == 0:
            native = _CpuSet.from_address(address + offset + 8)
            is_parked = bool(native.flags & 0x01)
            is_allocated = bool(native.flags & 0x02)
            is_allocated_here = bool(native.flags & 0x04)
            logical_processors.append(
                LogicalProcessor(
                    identifier=int(native.identifier),
                    processor_group=int(native.group),
                    logical_processor=int(native.logical_processor),
                    core=int(native.core),
                    last_level_cache=int(native.cache),
                    numa_node=_global_numa_node(
                        int(native.group),
                        int(native.logical_processor),
                    ),
                    is_available=not is_parked
                    and (not is_allocated or is_allocated_here),
                )
            )
        offset += size
    if not logical_processors:
        raise RuntimeError("cpu_sets_empty")
    return tuple(logical_processors)


def _available_memory(node: int) -> int:
    available = ctypes.c_ulonglong()
    if not _kernel32().GetNumaAvailableMemoryNodeEx(
        node,
        ctypes.byref(available),
    ):
        _raise_windows_error("numa_memory_read_failed")
    return int(available.value)


def _limit_job(job: int, lane: Lane) -> int:
    affinity = sum(
        1 << processor.logical_processor
        for processor in lane._logical_processors
    )
    limits = _ExtendedLimitInformation()
    limits.basic.limit_flags = (
        _JOB_OBJECT_LIMIT_AFFINITY
        | _JOB_OBJECT_LIMIT_JOB_MEMORY
        | _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    limits.basic.affinity = affinity
    limits.job_memory_limit = LANE_MEMORY_BYTES
    if not _kernel32().SetInformationJobObject(
        job,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    ):
        _raise_windows_error("job_limit_failed")
    group = _GroupAffinity()
    group.mask = affinity
    group.group = lane.processor_group
    if not _kernel32().SetInformationJobObject(
        job,
        _JOB_OBJECT_GROUP_INFORMATION_EX,
        ctypes.byref(group),
        ctypes.sizeof(group),
    ):
        _raise_windows_error("job_group_placement_failed")
    return affinity


def _set_cpu_sets(
    process: int,
    thread: int,
    identifiers: tuple[int, ...],
) -> None:
    values = (wintypes.ULONG * len(identifiers))(*identifiers)
    if not _kernel32().SetProcessDefaultCpuSets(
        process,
        values,
        len(identifiers),
    ):
        _raise_windows_error("worker_placement_failed")
    if not _kernel32().SetThreadSelectedCpuSets(
        thread,
        values,
        len(identifiers),
    ):
        _raise_windows_error("worker_thread_placement_failed")


def _get_process_cpu_sets(process: int) -> tuple[int, ...]:
    required = wintypes.ULONG()
    ctypes.set_last_error(0)
    _kernel32().GetProcessDefaultCpuSets(
        process,
        None,
        0,
        ctypes.byref(required),
    )
    error = ctypes.get_last_error()
    if not required.value or error not in (0, _ERROR_INSUFFICIENT_BUFFER):
        _raise_windows_error("worker_placement_size_failed")
    values = (wintypes.ULONG * required.value)()
    if not _kernel32().GetProcessDefaultCpuSets(
        process,
        values,
        required.value,
        ctypes.byref(required),
    ):
        _raise_windows_error("worker_placement_read_failed")
    return tuple(int(values[index]) for index in range(required.value))


def _get_thread_cpu_sets(thread: int) -> tuple[int, ...]:
    required = wintypes.ULONG()
    ctypes.set_last_error(0)
    _kernel32().GetThreadSelectedCpuSets(
        thread,
        None,
        0,
        ctypes.byref(required),
    )
    error = ctypes.get_last_error()
    if not required.value or error not in (0, _ERROR_INSUFFICIENT_BUFFER):
        _raise_windows_error("worker_thread_placement_size_failed")
    values = (wintypes.ULONG * required.value)()
    if not _kernel32().GetThreadSelectedCpuSets(
        thread,
        values,
        required.value,
        ctypes.byref(required),
    ):
        _raise_windows_error("worker_thread_placement_read_failed")
    return tuple(int(values[index]) for index in range(required.value))


def _job_limits(job: int) -> tuple[int, int]:
    limits = _ExtendedLimitInformation()
    if not _kernel32().QueryInformationJobObject(
        job,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
        None,
    ):
        _raise_windows_error("job_limit_read_failed")
    return int(limits.job_memory_limit), int(limits.basic.affinity)


def _job_group_affinity(job: int) -> tuple[int, int]:
    group = _GroupAffinity()
    returned = wintypes.DWORD()
    if not _kernel32().QueryInformationJobObject(
        job,
        _JOB_OBJECT_GROUP_INFORMATION_EX,
        ctypes.byref(group),
        ctypes.sizeof(group),
        ctypes.byref(returned),
    ):
        _raise_windows_error("job_group_placement_read_failed")
    if returned.value != ctypes.sizeof(group):
        raise RuntimeError("job_group_placement_shape_invalid")
    return int(group.group), int(group.mask)


def _global_numa_node(group: int, logical_processor: int) -> int:
    processor = _ProcessorNumber(
        group=group,
        number=logical_processor,
        reserved=0,
    )
    node = wintypes.USHORT()
    if not _kernel32().GetNumaProcessorNodeEx(
        ctypes.byref(processor),
        ctypes.byref(node),
    ):
        _raise_windows_error("numa_node_read_failed")
    if node.value == 0xFFFF:
        raise RuntimeError("numa_node_unavailable")
    return int(node.value)


def _environment(command: Command) -> str:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() in _INHERITED_ENVIRONMENT
    }
    environment.update(command.environment)
    for key, value in environment.items():
        if not key or "\0" in key or "=" in key:
            raise ValueError("worker_environment_key_invalid")
        if "\0" in value:
            raise ValueError("worker_environment_value_invalid")
    return (
        "\0".join(
            f"{key}={value}"
            for key, value in sorted(
                environment.items(),
                key=lambda item: item[0].casefold(),
            )
        )
        + "\0\0"
    )


def _handle(value: Any) -> int:
    return int(value or 0)


def _reserve_lane(lane: Lane) -> tuple[tuple[int, int], ...]:
    reservation = tuple(
        sorted(
            (processor.processor_group, processor.core)
            for processor in lane._logical_processors
        )
    )
    with _active_lanes_lock:
        if reservation in _active_lanes:
            raise RuntimeError("lane_busy")
        _active_lanes.add(reservation)
    return reservation


def _release_lane(reservation: tuple[tuple[int, int], ...]) -> None:
    with _active_lanes_lock:
        _active_lanes.discard(reservation)


def _close_handle(handle: int, label: str) -> None:
    if not _kernel32().CloseHandle(handle):
        _raise_windows_error(label)


def _wait_for_stop(process: int) -> bool:
    return (
        _kernel32().WaitForSingleObject(
            process,
            _CLEANUP_TIMEOUT_MS,
        )
        == _WAIT_OBJECT_0
    )


def _raise_windows_error(label: str) -> None:
    error = ctypes.get_last_error()
    raise OSError(error, f"{label}:{ctypes.FormatError(error).strip()}")

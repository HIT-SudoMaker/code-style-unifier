from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os
import sys

import torch


@dataclass(frozen=True, slots=True)
class AvailableDeviceMemory:
    """
    Record the available bytes observed for one exact execution device.
    """

    device: str
    available_bytes: int

    def __post_init__(self) -> None:
        """
        Require one named device and an exact non-negative byte count.
        """

        if not isinstance(self.device, str) or not self.device.strip():
            raise ValueError("device_memory_device_invalid")
        if type(self.available_bytes) is not int or self.available_bytes < 0:
            raise ValueError("device_memory_available_bytes_invalid")


class _GlobalMemoryStatus(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load", ctypes.c_ulong),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


def observe_available_device_memory(device: str) -> AvailableDeviceMemory:
    """
    Observe currently available bytes for one exact execution device.
    """

    if device.startswith("cuda:"):
        free_bytes, _ = torch.cuda.mem_get_info(torch.device(device))
        return AvailableDeviceMemory(device, int(free_bytes))
    if sys.platform == "win32":
        status = _GlobalMemoryStatus()
        status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(
            ctypes.byref(status)
        ):
            raise OSError("memory_observation_failed")
        return AvailableDeviceMemory(device, int(status.available_physical))
    page_size = int(os.sysconf("SC_PAGE_SIZE"))
    available_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
    return AvailableDeviceMemory(device, page_size * available_pages)

from __future__ import annotations

from types import SimpleNamespace

import pytest

import metacraft.field._device_memory as device_memory_module
from metacraft.field._device_memory import AvailableDeviceMemory


def test_available_device_memory_records_zero_exact_bytes() -> None:
    observation = AvailableDeviceMemory("cpu", 0)

    assert observation.device == "cpu"
    assert observation.available_bytes == 0


@pytest.mark.parametrize("device", ("", " "))
def test_available_device_memory_requires_one_device_name(device: str) -> None:
    with pytest.raises(ValueError):
        AvailableDeviceMemory(device, 0)


@pytest.mark.parametrize("available_bytes", (True, -1, 1.0))
def test_available_device_memory_requires_exact_nonnegative_bytes(
    available_bytes: object,
) -> None:
    with pytest.raises(ValueError):
        AvailableDeviceMemory("cpu", available_bytes)  # type: ignore[arg-type]


def test_cuda_observation_reads_free_bytes_for_exact_selected_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    devices: list[object] = []

    def observe_cuda(device: object) -> tuple[int, int]:
        devices.append(device)
        return (1_500_000_000, 2_000_000_000)

    monkeypatch.setattr(
        device_memory_module.torch.cuda,
        "mem_get_info",
        observe_cuda,
    )

    observation = device_memory_module.observe_available_device_memory(
        "cuda:2"
    )

    assert observation == AvailableDeviceMemory("cuda:2", 1_500_000_000)
    assert devices == [device_memory_module.torch.device("cuda:2")]


def test_cuda_observation_propagates_the_original_torch_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    injected = RuntimeError("cuda_memory_unavailable")

    def fail_observation(_device: object) -> tuple[int, int]:
        raise injected

    monkeypatch.setattr(
        device_memory_module.torch.cuda,
        "mem_get_info",
        fail_observation,
    )

    with pytest.raises(RuntimeError) as raised:
        device_memory_module.observe_available_device_memory("cuda:0")

    assert raised.value is injected


def test_windows_observation_reads_available_physical_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_statuses: list[object] = []

    def observe_windows(status_pointer: object) -> bool:
        status = status_pointer._obj  # type: ignore[attr-defined]
        observed_statuses.append(status)
        status.available_physical = 3_000_000_000
        return True

    monkeypatch.setattr(device_memory_module.sys, "platform", "win32")
    monkeypatch.setattr(
        device_memory_module.ctypes,
        "windll",
        SimpleNamespace(
            kernel32=SimpleNamespace(
                GlobalMemoryStatusEx=observe_windows,
            )
        ),
        raising=False,
    )

    observation = device_memory_module.observe_available_device_memory("cpu")

    assert observation == AvailableDeviceMemory("cpu", 3_000_000_000)
    assert len(observed_statuses) == 1
    status = observed_statuses[0]
    assert status.length == device_memory_module.ctypes.sizeof(  # type: ignore[attr-defined]
        type(status)
    )


def test_windows_false_return_is_one_observation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(device_memory_module.sys, "platform", "win32")
    monkeypatch.setattr(
        device_memory_module.ctypes,
        "windll",
        SimpleNamespace(
            kernel32=SimpleNamespace(
                GlobalMemoryStatusEx=lambda _status: False,
            )
        ),
        raising=False,
    )

    with pytest.raises(OSError, match="^memory_observation_failed$"):
        device_memory_module.observe_available_device_memory("cpu")


def test_posix_observation_multiplies_available_pages_by_page_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names: list[str] = []

    def sysconf(name: str) -> int:
        names.append(name)
        return {
            "SC_PAGE_SIZE": 4_096,
            "SC_AVPHYS_PAGES": 250_000,
        }[name]

    monkeypatch.setattr(device_memory_module.sys, "platform", "linux")
    monkeypatch.setattr(
        device_memory_module.os,
        "sysconf",
        sysconf,
        raising=False,
    )

    observation = device_memory_module.observe_available_device_memory("cpu")

    assert observation == AvailableDeviceMemory("cpu", 1_024_000_000)
    assert names == ["SC_PAGE_SIZE", "SC_AVPHYS_PAGES"]

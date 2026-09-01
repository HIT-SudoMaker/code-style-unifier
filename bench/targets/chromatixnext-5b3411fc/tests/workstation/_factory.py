from __future__ import annotations

from unittest.mock import patch

from chromatix_next.workstation import Workstation


def cpu_workstation(
    memory_boundary_bytes: int,
) -> Workstation:
    """
    通过正式 CPU 工厂取得使用指定测试边界的工作站
    """
    with patch(
        "chromatix_next._execution_memory._default_memory_boundary_bytes",
        return_value=memory_boundary_bytes,
    ):
        return Workstation.cpu()


def cuda_workstation(
    memory_boundary_bytes: int,
    device_index: int = 0,
) -> Workstation:
    """
    通过正式 CUDA 工厂取得使用指定测试边界的工作站
    """
    with patch(
        "chromatix_next._execution_memory._default_memory_boundary_bytes",
        return_value=memory_boundary_bytes,
    ):
        return Workstation.cuda(device_index)

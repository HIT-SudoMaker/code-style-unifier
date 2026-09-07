from __future__ import annotations

from pathlib import Path

from chromatix_next.optics import Assembly

PROJECT_ROOT = Path(__file__).resolve().parents[2]


PRODUCTION = PROJECT_ROOT / "src" / "chromatix_next"


WORKSTATION = PRODUCTION / "workstation.py"


def test_execution_memory_belongs_to_workstation_boundary() -> None:
    """
    Workstation 消费唯一执行账簿，Assembly 不拥有峰值估算职责
    """
    assembly_source = (
        PRODUCTION / "optics" / "assembly.py"
    ).read_text(encoding="utf-8")
    workstation_source = WORKSTATION.read_text(encoding="utf-8")
    execution_memory_source = (
        PRODUCTION / "_execution_memory.py"
    ).read_text(encoding="utf-8")

    assert "_execution_memory" in workstation_source
    assert "_execution_memory" not in assembly_source
    assert "_default_memory_boundary_bytes" in execution_memory_source
    assert "_cpu_physical_memory_bytes" in execution_memory_source
    assert "_windows_physical_memory_bytes" in execution_memory_source
    assert "_MemoryStatusEx" in execution_memory_source
    assert "def _default_memory_boundary_bytes" not in workstation_source
    assert "_cpu_physical_memory_bytes" not in workstation_source
    assert "_windows_physical_memory_bytes" not in workstation_source
    assert "_MemoryStatusEx" not in workstation_source
    assert "import ctypes" not in workstation_source
    assert "import os" not in workstation_source
    assert "_meta_inference" in assembly_source
    assert "_components" not in assembly_source
    for name in (
        "_estimate_peak_memory",
        "_replay_on_meta",
        "_PeakMemoryWalk",
        "_FactoryMemoryWalk",
    ):
        assert name not in Assembly.__dict__
        assert name not in assembly_source
        assert name not in execution_memory_source


def test_workstation_imports_meta_inference_from_its_optics_owner() -> None:
    """
    Workstation 直接依赖 meta 推导所有者，内存账本不充当假转发边界
    """

    workstation_source = (
        PRODUCTION / "workstation.py"
    ).read_text(encoding="utf-8")
    execution_memory_source = (
        PRODUCTION / "_execution_memory.py"
    ).read_text(encoding="utf-8")

    assert (
        "from .optics._meta_inference import _meta_inference"
        in workstation_source
    )
    assert "_execution_memory._meta_inference" not in workstation_source
    assert "optics._meta_inference" not in execution_memory_source


def test_grid_metadata_guard_does_not_rewrite_private_mode_stack() -> None:
    """
    约束网格元数据窄相位不改写 PyTorch 私有 mode 栈
    """
    source = (
        PRODUCTION / "optics" / "_meta_inference.py"
    ).read_text(encoding="utf-8")

    assert "_disable_current_modes" not in source
    assert "_pop_mode_temporarily" not in source
    assert "ContextVar" in source

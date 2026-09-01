
from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch

from chromatix_next.errors import AssemblyError, WorkstationError
from chromatix_next.optics import (
    Assembly,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import IdealThinLens
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation
from tests.workstation._factory import cpu_workstation


def _grid(
    counts: tuple[int, int] = (4, 4),
    spacing: tuple[float, float] = (0.5e-6, 0.5e-6),
) -> SpatialGrid:
    # 中心对齐的小型横向网格
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )


def _spectrum(wavelength: float = 2.0e-6) -> Spectrum:
    # 单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _plane_wave(
    *,
    spectrum: Spectrum | None = None,
    relative_amplitude: float = 1.0,
) -> PlaneWave:
    # 沿法线传播的标量偏振平面波源
    return PlaneWave(
        spectrum=spectrum or _spectrum(),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=relative_amplitude,
    )


def _simple_detection_assembly(
    *,
    counts: tuple[int, int] = (4, 4),
) -> Assembly:
    # 单链装配：PlaneWave → IntensityDetection，并暴露命名输出 ``intensity``
    grid = _grid(counts=counts)
    source = _plane_wave()
    detector = IntensityDetection()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(detector, name="detector")
    assembly.connect(source, detector)
    assembly.expose(detector, name="intensity")
    return assembly


class TestExplicitFactories:
    """
    显式工厂选择设备（无自动发现、无回退）
    """




    def test_cuda_factory_selects_cuda_device_when_available(self) -> None:
        """有 CUDA 时 ``Workstation.cuda`` 显式锁定指定设备（固定双精度）
        """
        if not torch.cuda.is_available():
            pytest.skip("No CUDA-capable PyTorch runtime on this host.")
        workstation = Workstation.cuda(0)
        assert workstation.device.type == "cuda"
        assert workstation.device.index == 0
        assert workstation.memory_boundary_bytes > 0

    def test_cuda_factory_rejects_out_of_range_index(self) -> None:
        """越界 CUDA 设备索引 ⇒ ``WorkstationError``（显式选择，无静默回退）
        """
        if not torch.cuda.is_available():
            pytest.skip("No CUDA-capable PyTorch runtime on this host.")
        with pytest.raises(WorkstationError):
            Workstation.cuda(9999)


class TestWorkstationCheck:
    """
    ``Workstation.check``：装配检查之后的设备 + 内存可行性
    """

    def test_check_passes_for_feasible_assembly(self) -> None:
        """小型可行装配在 CPU 工作站上 ``check`` 通过（返回 None）
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assert workstation.check(assembly) is None

    def test_check_runs_after_assembly_check(self) -> None:
        """拓扑缺陷经 ``AssemblyError`` 抛出（先于工作站内存检查）
        """
        workstation = Workstation.cpu()
        grid = _grid()
        assembly = Assembly()
        # 两片理想薄透镜互连成环 ⇒ 装配检查在拓扑走查时失败
        first = IdealThinLens(grid=grid, focal_length=1.0e-3)
        second = IdealThinLens(grid=grid, focal_length=2.0e-3)
        assembly.include(first, name="first")
        assembly.include(second, name="second")
        assembly.connect(first, second)
        assembly.connect(second, first)
        with pytest.raises(AssemblyError) as exception:
            workstation.check(assembly)
        assert "assembly_topology_cycle" in str(exception.value)

    def test_check_rejects_infeasible_before_allocation(self) -> None:
        """巨大装配的保守峰值越界 ⇒ ``WorkstationError``，在任何张量分配之前

        构造一个采样数极大的装配：``check`` 在 meta 设备执行真实前向，不分配
        实体张量，并必须在内存检查阶段以稳定身份
        ``workstation_memory_check_infeasible`` 拒绝，绝不进入运行/分配路径。
        """
        workstation = Workstation.cpu()
        # 200000×200000 单波长标量场：保守峰值远超任何主机内存边界
        assembly = _simple_detection_assembly(counts=(200_000, 200_000))
        with pytest.raises(WorkstationError) as exception:
            workstation.check(assembly)
        assert "workstation_memory_check_infeasible" in str(exception.value)

    def test_check_rejects_pessimistically_at_borderline(self) -> None:
        """边界情形：实际内存可容但保守估计越界 ⇒ 拒绝，而非静默接受

        替换私有默认边界探针后经正式 CPU 工厂取得极小边界，迫使任何非空装配的
        保守峰值越界。该装配
        实际峰值远小于真实主机内存，但保守估计（高估）越过显式边界 ⇒ 必须拒绝。
        """
        # 1 字节边界：任何非空装配的保守峰值（至少一份输出场）均越界
        tiny_boundary = 1
        workstation = cpu_workstation(tiny_boundary)
        assembly = _simple_detection_assembly()
        with pytest.raises(WorkstationError) as exception:
            workstation.check(assembly)
        assert "workstation_memory_check_infeasible" in str(exception.value)

    def test_check_does_not_mutate_assembly_on_rejection(self) -> None:
        """内存拒绝后装配拓扑、命名输出与可作者性均不变（无回退、无副作用）
        """
        workstation = cpu_workstation(1)
        assembly = _simple_detection_assembly()
        exposed_before = assembly.exposed_names()
        component_count_before = len(list(assembly.named_modules()))

        with pytest.raises(WorkstationError):
            workstation.check(assembly)

        assert assembly.exposed_names() == exposed_before
        assert len(list(assembly.named_modules())) == component_count_before
        # 拒绝后装配仍可被再次检查（无部分状态）
        with pytest.raises(WorkstationError):
            workstation.check(assembly)

    def test_check_does_not_mutate_assembly_on_success(self) -> None:
        """通过检查不改变装配拓扑或命名输出注册
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        exposed_before = assembly.exposed_names()
        workstation.check(assembly)
        assert assembly.exposed_names() == exposed_before

    def test_check_rejects_non_assembly_subject(self) -> None:
        """非装配主体 ⇒ ``WorkstationError``（``check`` 仅接受装配）
        """
        workstation = Workstation.cpu()
        with pytest.raises(WorkstationError):
            workstation.check("not an assembly")  # type: ignore[arg-type]


class TestNoFallbackOnRejection:
    """
    拒绝时无回退：抛 ``WorkstationError``，不重试、不改装配
    """

    def test_rejected_assembly_remains_usable_on_larger_workstation(self) -> None:
        """被一台工作站内存拒绝的装配在更大边界工作站上可通过（无永久标记）
        """
        assembly = _simple_detection_assembly()
        tiny = cpu_workstation(1)
        large = Workstation.cpu()
        with pytest.raises(WorkstationError):
            tiny.check(assembly)
        # 同一装配在更大工作站上通过：拒绝未对装配留下任何状态
        assert large.check(assembly) is None


class TestCpuMemoryBoundaryHeadroom:
    """
    CPU 默认内存边界须保守地预留余量
    """

    def test_default_cpu_boundary_below_total_physical(self) -> None:
        """默认 CPU 边界小于主机物理内存总量（保守、不取 100%）

        ``_default_memory_boundary_bytes`` 为 CPU 保留系统余量，
        无任何余量留给操作系统或同行进程，并非严格保守。修复后取 ``total × 9//10``，
        使成功路径真正保守（每组件 3–4× 高估之外再闭合此缺口）。
        """
        from chromatix_next._execution_memory import _cpu_physical_memory_bytes

        workstation = Workstation.cpu()
        total_physical = _cpu_physical_memory_bytes()
        # 默认边界须严格小于物理总量，且为留有余量的保守值
        assert 0 < workstation.memory_boundary_bytes < total_physical
        # 保留比例为 10%（``total × 9//10``）
        assert workstation.memory_boundary_bytes == total_physical * 9 // 10

    def test_windows_probe_failure_uses_conservative_boundary(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Windows 物理内存探针失败时以 1 GiB 为总量并继续保留 10% 余量
        """
        from chromatix_next import _execution_memory

        def _fail_windows_probe() -> int:
            failure_identity = "workstation_cpu_memory_probe_failed"
            raise OSError(failure_identity)

        monkeypatch.setattr(
            _execution_memory,
            "os",
            SimpleNamespace(name="nt"),
        )
        monkeypatch.setattr(
            _execution_memory,
            "_windows_physical_memory_bytes",
            _fail_windows_probe,
        )

        fallback_total = 1 << 30
        assert _execution_memory._cpu_physical_memory_bytes() == fallback_total
        assert _execution_memory._default_memory_boundary_bytes(
            torch.device("cpu")
        ) == fallback_total * 9 // 10

    def test_posix_probe_uses_page_count_and_page_size(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        POSIX 总物理内存由页数与页大小相乘，CPU 边界仍保留 10% 余量
        """
        from chromatix_next import _execution_memory

        page_facts = {
            "SC_PHYS_PAGES": 1024,
            "SC_PAGE_SIZE": 4096,
        }
        monkeypatch.setattr(
            _execution_memory,
            "os",
            SimpleNamespace(
                name="posix",
                sysconf=page_facts.__getitem__,
            ),
        )

        total = page_facts["SC_PHYS_PAGES"] * page_facts["SC_PAGE_SIZE"]
        assert _execution_memory._cpu_physical_memory_bytes() == total
        assert _execution_memory._default_memory_boundary_bytes(
            torch.device("cpu")
        ) == total * 9 // 10

    def test_cuda_boundary_uses_full_device_memory(self) -> None:
        """CUDA 设备显存为专用，边界取 ``total_memory`` 全量（无主机那样的同行者）

        该断言锁定 CUDA 与 CPU 边界策略的有意差异：CPU 留余量、CUDA 取全量。
        """
        if not torch.cuda.is_available():
            pytest.skip("No CUDA-capable PyTorch runtime on this host.")
        workstation = Workstation.cuda(0)
        properties = torch.cuda.get_device_properties(0)
        assert workstation.memory_boundary_bytes == int(properties.total_memory)

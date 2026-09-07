from __future__ import annotations

from typing import Any, Literal

import pytest
import torch

from chromatix_next.errors import WorkstationError
from chromatix_next.optics import (
    Assembly,
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import RunRecord, Workstation
from tests.workstation._factory import (
    cuda_workstation as _cuda_workstation_with_boundary,
)

pytestmark = pytest.mark.cuda

requires_cuda = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="No CUDA-capable PyTorch runtime on this host.",
)

def _grid() -> SpatialGrid:
    # 32×32 中心对齐横向网格（与现有 hosted focusing 证据相同的物理配置）
    return SpatialGrid.centered(
        sample_counts=(32, 32),
        sample_spacing=(1.0e-6, 1.0e-6),
    )

def _spectrum() -> Spectrum:
    # 单位权重、1 µm 单波长光谱
    return Spectrum.monochromatic(wavelength=1.0e-6)

def _cuda_lifecycle_assembly() -> Assembly:
    # 构造暴露成对数值类型的最小托管波动光学路径
    grid = _grid()
    source = PlaneWave(
        spectrum=_spectrum(),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    propagator = ScalarAngularSpectrum(axial_distance=1.0e-6)
    detector = IntensityDetection()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(propagator, name="propagator")
    assembly.include(detector, name="detector")
    assembly.connect(source, propagator)
    assembly.connect(propagator, detector)
    assembly.expose(propagator, name="field")
    assembly.expose(detector, name="intensity")
    return assembly


def _run_cuda_lifecycle(*, device: str) -> tuple[Any, RunRecord]:
    # 在指定设备上运行并释放一份托管装配
    workstation = Workstation.cuda(0) if device == "cuda" else Workstation.cpu()
    hosted_assembly = _cuda_lifecycle_assembly()
    hosted_assembly.freeze()
    workstation.host(hosted_assembly)
    try:
        return workstation.run(hosted_assembly)
    finally:
        workstation.release(hosted_assembly)

class TestCudaDtypesDevice:
    """
    CUDA 运行使用固定双精度 dtype；输出张量位于 CUDA 设备
    """

    @requires_cuda
    def test_cuda_run_uses_paired_dtypes(self) -> None:
        """CUDA 路径上复包络为 ``torch.complex128``、光强为 ``torch.float64``
        （固定双精度）
        """
        outputs, _ = _run_cuda_lifecycle(device="cuda")
        propagated_field = outputs["field"]
        assert propagated_field.envelope.dtype is torch.complex128
        assert propagated_field.envelope.device.type == "cuda"
        assert propagated_field.envelope.device.index == 0
        path_length = propagated_field.path_reference.lengths[0]
        assert isinstance(path_length, torch.Tensor)
        assert path_length.dtype is torch.float64
        assert path_length.device.type == "cuda"
        assert path_length.device.index == 0
        intensity = outputs["intensity"]
        assert intensity.values.dtype is torch.float64
        assert intensity.values.device.type == "cuda"
        assert intensity.values.device.index == 0

class TestCudaRunRecord:
    """
    运行记录记录实际运行的 CUDA 设备 / 环境
    """

    @requires_cuda
    def test_run_record_reflects_cuda_path(self) -> None:
        """CUDA 运行记录的设备字段为 ``cuda:0``、CUDA 环境事实填写
        """
        _outputs, record = _run_cuda_lifecycle(device="cuda")
        assert isinstance(record, RunRecord)
        assert record.device == "cuda:0"
        assert record.implementation == "pytorch"
        assert record.seed == 42  # 默认根 seed
        assert record.peak_memory_bytes > 0
        assert record.memory_boundary_bytes > 0
        assert record.is_cuda_available is True
        assert record.cuda_device_name == torch.cuda.get_device_name(0)
        assert isinstance(record.torch_version, str) and record.torch_version
        assert isinstance(record.stream_derivation, str) and record.stream_derivation

    @requires_cuda
    def test_cpu_record_differs_from_cuda_record(self) -> None:
        """CPU 记录设备字段为 ``cpu``，CUDA 记录设备字段为 ``cuda:0``（路径可区分）
        """
        _outputs_cpu, record_cpu = _run_cuda_lifecycle(device="cpu")
        _outputs_cuda, record_cuda = _run_cuda_lifecycle(device="cuda")
        assert record_cpu.device == "cpu"
        assert record_cuda.device == "cuda:0"
        assert record_cpu.device != record_cuda.device

class TestCudaMemoryCheckRejection:
    """
    CUDA 工作站的保守 Memory Check 仍于任何张量分配前以 ``WorkstationError`` 拒绝
    """

    @requires_cuda
    def test_oversized_assembly_rejected_before_allocation_on_cuda(self) -> None:
        """显式极小 CUDA 内存边界 ⇒ 越界装配在 ``run`` 入口以 ``WorkstationError`` 拒绝

        替换私有默认边界探针后经正式 CUDA 工厂取得 1 字节边界；合法聚焦装配的
        保守峰值估计
        （每组件峰值工作区视为同时存活、按成对复数 dtype 字节宽度换算）必然越界。
        拒绝发生在任何张量分配之前（规约"Memory Check"），并以稳定身份
        ``workstation_memory_check_infeasible`` 抛出，绝不进入运行/分配路径。
        """
        cuda_workstation = _cuda_workstation_with_boundary(1)
        hosted_assembly = _cuda_lifecycle_assembly()
        hosted_assembly.freeze()
        cuda_workstation.host(hosted_assembly)
        try:
            with pytest.raises(WorkstationError) as exception:
                cuda_workstation.run(hosted_assembly)
            assert (
                "workstation_memory_check_infeasible" in str(exception.value)
            )
            del exception
        finally:
            cuda_workstation.release(hosted_assembly)

    @requires_cuda
    def test_cuda_check_rejects_oversized_without_run(self) -> None:
        """``Workstation.check`` 在 CUDA 上同样于分配前拒绝越界装配（无须运行）
        """
        workstation = _cuda_workstation_with_boundary(1)
        assembly = _cuda_lifecycle_assembly()
        assembly.freeze()
        # check 不要求托管；直接在冻结装配上运行保守内存检查
        with pytest.raises(WorkstationError) as exception:
            workstation.check(assembly)
        assert "workstation_memory_check_infeasible" in str(exception.value)
        del exception, assembly, workstation

class _ForcedOomSource(torch.nn.Module):

    @property
    def role(self) -> Literal["source"]:
        """
        返回测试 OOM 源的不可变源角色
        """

        return "source"

    def __init__(
        self,
        *,
        spectrum: Spectrum,
        polarization: Polarization,
        medium: Vacuum,
        expected_error: torch.cuda.OutOfMemoryError,
    ) -> None:
        """记录输出物理值与待透传的 OOM 实例
        """
        super().__init__()
        self._spectrum_value = spectrum
        self._polarization_value = polarization
        self._medium_value = medium
        self._expected_error = expected_error
        self._device_anchor: torch.Tensor
        self.register_buffer(
            "_device_anchor",
            torch.empty((), dtype=torch.float64),
            persistent=False,
        )

    def forward(self, grid: SpatialGrid) -> OpticalField:  # type: ignore[override]
        """meta 推导返回光场，真实执行抛出待透传 CUDA OOM
        """
        if self._device_anchor.device.type == "meta":
            counts_y, counts_x = grid.sample_counts
            complex_dtype = torch.complex128
            return OpticalField(
                envelope=torch.empty(
                    (
                        self._spectrum_value.count,
                        self._polarization_value.component_count,
                        counts_y,
                        counts_x,
                    ),
                    device=self._device_anchor.device,
                    dtype=complex_dtype,
                ),
                grid=grid,
                spectrum=self._spectrum_value,
                polarization_representation=(self._polarization_value).representation,
                medium=self._medium_value,
                normalization=FieldNormalization.RELATIVE,
                path_reference=OpticalPathReference(
                    lengths=(0.0,) * self._spectrum_value.count,
                ),
            )
        raise self._expected_error

class TestCudaOomPassThrough:
    """
    CUDA 运行期意外 OOM 原样透传（不包装为域异常、不触发回退）
    """

    @requires_cuda
    def test_cuda_runtime_oom_passes_through_unchanged(self) -> None:
        """CUDA 工作站上运行期 OOM 异常原样透传（不被包装为 ``WorkstationError``）

        覆盖规约"Workstation Error"：实际 PyTorch/CUDA OOM 异常原样透传，不包装、
        不触发回退或科学更改。CPU 侧等价透传由 ``tests/workstation/test_run.py``
        的 ``TestRunOomPassThrough`` 覆盖；此处补充 CUDA 工作站路径。
        """
        cuda_workstation = Workstation.cuda(0)
        grid = _grid()
        hosted_assembly = Assembly()
        expected_out_of_memory = torch.cuda.OutOfMemoryError(
            "CUDA out of memory. Tried to allocate 999 TiB."
        )
        source = _ForcedOomSource(
            spectrum=_spectrum(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            expected_error=expected_out_of_memory,
        )
        hosted_assembly.include(source, name="doom", grid=grid)
        hosted_assembly.expose(source, name="field")
        hosted_assembly.freeze()
        cuda_workstation.host(hosted_assembly)
        try:
            with pytest.raises(torch.cuda.OutOfMemoryError) as exception:
                cuda_workstation.run(hosted_assembly)
            # 不被包装成 WorkstationError：异常对象身份、类型与消息原样保持
            assert exception.value is expected_out_of_memory
            assert not isinstance(exception.value, WorkstationError)
            assert "CUDA out of memory" in str(exception.value)
            expected_out_of_memory.__traceback__ = None
            del exception
        finally:
            cuda_workstation.release(hosted_assembly)

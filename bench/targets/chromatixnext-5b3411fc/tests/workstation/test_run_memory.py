from __future__ import annotations

import contextlib
import copy
import gc
from typing import Literal

import pytest
import torch

from chromatix_next.errors import AssemblyError
from chromatix_next.optics import (
    Assembly,
    Intensity,
    OpticalField,
    Polarization,
    PropagationDirection,
    RayBundle,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import CircularPupil, IdealThinLens
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import Workstation

_CacheState = Literal["cold", "warm", "replacement"]


class _NativeConstantElement(torch.nn.Module):
    # 模拟课题组自定义元件：合法结构角色，但不知道框架的私有张量构造助手

    @property
    def role(self) -> Literal["element"]:
        """
        返回结构契约承认的元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        以原生张量构造加入一个同形常量场
        """
        spectrum_count, polarization_count, height, width = field.envelope.shape
        values = [
            [
                [
                    [1.0] * width
                    for _height_index in range(height)
                ]
                for _polarization_index in range(polarization_count)
            ]
            for _spectrum_index in range(spectrum_count)
        ]
        constant = torch.tensor(
            values,
            device=field.envelope.device,
            dtype=field.envelope.dtype,
        )
        result = copy.copy(field)
        object.__setattr__(result, "envelope", field.envelope + constant)
        return result


class _NativeOutputElement(torch.nn.Module):
    # 模拟直接返回原生构造物理载荷的外部元件，结果不再经过后续张量算子

    @property
    def role(self) -> Literal["element"]:
        """
        返回结构契约承认的元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        以原生张量构造直接替换同形包络
        """
        spectrum_count, polarization_count, height, width = field.envelope.shape
        values = [
            [
                [
                    [1.0] * width
                    for _height_index in range(height)
                ]
                for _polarization_index in range(polarization_count)
            ]
            for _spectrum_index in range(spectrum_count)
        ]
        result = copy.copy(field)
        object.__setattr__(
            result,
            "envelope",
            torch.tensor(
                values,
                device=field.envelope.device,
                dtype=field.envelope.dtype,
            ),
        )
        return result


class _NativeDiscardElement(torch.nn.Module):
    # 模拟只读取临时张量结构、随后直接丢弃的外部元件

    @property
    def role(self) -> Literal["element"]:
        """
        返回结构契约承认的元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        原生构造一块临时设备张量而不把它带入输出
        """
        temporary = torch.tensor(
            [1.0] * (1024 * 1024),
            device=field.envelope.device,
            dtype=field.envelope.dtype,
        )
        _shape = temporary.shape
        return field


class _RealDeviceDiscardElement(torch.nn.Module):
    # 模拟外部元件在 meta 预检中显式请求真实 CUDA 临时量

    @property
    def role(self) -> Literal["element"]:
        """
        返回结构契约承认的元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        请求一块随后丢弃的真实 CUDA 张量
        """
        temporary = torch.tensor(
            [1.0] * (1024 * 1024),
            device="cuda:0",
            dtype=torch.complex128,
        )
        _shape = temporary.shape
        return field


def _grid() -> SpatialGrid:
    # 该尺寸足以让 CUDA 分配舍入与可微保存状态进入可测区间，同时保持测试轻量
    return SpatialGrid.centered(
        sample_counts=(64, 64),
        sample_spacing=(0.5e-6, 0.5e-6),
    )


def _assembly(
    *,
    cache_state: _CacheState,
) -> tuple[
    Assembly,
    PlaneWave,
    CircularPupil,
    IdealThinLens,
]:
    grid = _grid()
    amplitude = torch.nn.Parameter(
        torch.tensor(
            1.0,
            dtype=torch.float64,
        )
    )
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=1.0e-6),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=amplitude,
    )
    pupil = CircularPupil(
        grid=grid,
        radius=12.0e-6,
    )
    lens = IdealThinLens(
        grid=grid,
        focal_length=1.0e-3,
    )
    detection = IntensityDetection()

    if cache_state == "replacement":
        incident = source(grid)
        pupil_output = pupil(incident)
        lens(pupil_output)

    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(pupil, name="pupil")
    assembly.include(lens, name="lens")
    assembly.include(detection, name="detection")
    assembly.connect(source, pupil)
    assembly.connect(pupil, lens)
    assembly.connect(lens, detection)
    assembly.expose(detection, name="intensity")
    assembly.freeze()
    return assembly, source, pupil, lens


class _IdentityPassthroughElement(torch.nn.Module):

    @property
    def role(self) -> Literal["element"]:
        """
        返回结构契约承认的元件角色
        """

        return "element"

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        原样返回输入光场（非消耗直通）
        """

        return field


def _storage_alias_assembly(
    *,
    has_alias_name: bool,
) -> Assembly:
    grid = _grid()
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=1.0e-6),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    identity = _IdentityPassthroughElement()
    detector = IntensityDetection()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(identity, name="identity")
    assembly.include(detector, name="detector")
    assembly.connect(source, identity)
    assembly.connect(identity, detector)
    if has_alias_name:
        assembly.expose(source, name="primary")
    assembly.expose(identity, name="field")
    assembly.expose(detector, name="intensity")
    assembly.freeze()
    return assembly


def _intermediate_exposure_assembly(
    *,
    is_intermediate_exposed: bool,
) -> Assembly:
    grid = _grid()
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=1.0e-6),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    lens_a = IdealThinLens(grid=grid, focal_length=1.0e-3)
    lens_b = IdealThinLens(grid=grid, focal_length=2.0e-3)
    lens_c = IdealThinLens(grid=grid, focal_length=3.0e-3)
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(lens_a, name="lens_a")
    assembly.include(lens_b, name="lens_b")
    assembly.include(lens_c, name="lens_c")
    assembly.connect(source, lens_a)
    assembly.connect(lens_a, lens_b)
    assembly.connect(lens_b, lens_c)
    if is_intermediate_exposed:
        assembly.expose(lens_a, name="intermediate")
    assembly.expose(lens_c, name="output")
    assembly.freeze()
    return assembly


def _external_component_assembly(
    element_type: type[torch.nn.Module] = _NativeConstantElement,
    *,
    is_frozen: bool = True,
) -> Assembly:
    grid = _grid()
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=1.0e-6),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    element = element_type()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(element, name="element")
    assembly.connect(source, element)
    assembly.expose(element, name="field")
    if is_frozen:
        assembly.freeze()
    return assembly


def _gradient_context(
    is_gradient_enabled: bool,
) -> contextlib.AbstractContextManager[None]:
    if is_gradient_enabled:
        return torch.enable_grad()
    return torch.no_grad()


def _named_tensor_state(
    assembly: Assembly,
) -> tuple[tuple[str, torch.Tensor, torch.Tensor], ...]:
    tensors: list[tuple[str, torch.Tensor, torch.Tensor]] = []
    tensors.extend(
        (
            f"parameter:{name}",
            parameter,
            parameter.detach().clone(),
        )
        for name, parameter in assembly.named_parameters()
    )
    tensors.extend(
        (
            f"buffer:{name}",
            buffer,
            buffer.detach().clone(),
        )
        for name, buffer in assembly.named_buffers()
    )
    return tuple(tensors)


def _assert_tensor_state_unchanged(
    assembly: Assembly,
    state: tuple[tuple[str, torch.Tensor, torch.Tensor], ...],
) -> None:
    current = {
        **{
            f"parameter:{name}": parameter
            for name, parameter in assembly.named_parameters()
        },
        **{
            f"buffer:{name}": buffer
            for name, buffer in assembly.named_buffers()
        },
    }
    for name, tensor, value in state:
        assert current[name] is tensor
        assert torch.equal(current[name], value)


def test_cpu_check_isolates_state_and_run_records_conservative_peak() -> None:
    """
    CPU 公共检查不泄漏缓存或张量状态，公共运行记录保留保守峰值
    """
    assembly, source, pupil, lens = _assembly(cache_state="cold")
    state = _named_tensor_state(assembly)
    source_key = source._unit_envelope_cache_key  # noqa: SLF001
    workstation = Workstation.cpu()

    assert workstation.check(assembly) is None

    _assert_tensor_state_unchanged(assembly, state)
    assert source._unit_envelope_cache_key == source_key  # noqa: SLF001
    assert source.get_buffer("_unit_envelope_cache") is None

    workstation.host(assembly)
    outputs, record = workstation.run(assembly)
    assert isinstance(outputs["intensity"], Intensity)
    assert record.peak_memory_bytes > 0
    assert record.peak_memory_bytes <= record.memory_boundary_bytes


def test_legal_output_alias_counts_shared_storage_once() -> None:
    """
    两个不同锚点指向同一物理值 storage 时，公共运行记录只计一次

    合法 storage-别名拓扑（source 与 identity 输出同一对象）下，为两个锚点分别命名
    不增加保守峰值——与只命名一个锚点的对照峰值一致。这取代了已退休的同锚点双暴露
    别名证据，仍证明 shared Tensor storage 在 Memory Estimate 中只计一次。
    """
    control = _storage_alias_assembly(has_alias_name=False)
    aliased = _storage_alias_assembly(has_alias_name=True)
    control_workstation = Workstation.cpu()
    aliased_workstation = Workstation.cpu()
    control_workstation.host(control)
    aliased_workstation.host(aliased)

    _control_outputs, control_record = control_workstation.run(control)
    aliased_outputs, aliased_record = aliased_workstation.run(aliased)

    # 两个用户名绑定同一物理值对象（共享 storage）
    assert tuple(aliased_outputs) == ("primary", "field", "intensity")
    assert aliased_outputs["primary"] is aliased_outputs["field"]
    # 别名拓扑的保守峰值与单名对照一致：shared storage 只计一次
    assert aliased_record.peak_memory_bytes == control_record.peak_memory_bytes


def test_intermediate_exposure_is_not_free_in_memory_estimate() -> None:
    """
    把早期中间值暴露为 Authored Exposure 会保留其 storage 至 Named Outputs，
    公共运行记录的保守峰值须高于同一拓扑不暴露该中间值的对照
    """

    control = _intermediate_exposure_assembly(is_intermediate_exposed=False)
    exposed = _intermediate_exposure_assembly(is_intermediate_exposed=True)
    control_workstation = Workstation.cpu()
    exposed_workstation = Workstation.cpu()
    control_workstation.host(control)
    exposed_workstation.host(exposed)

    control_outputs, control_record = control_workstation.run(control)
    exposed_outputs, exposed_record = exposed_workstation.run(exposed)

    assert tuple(control_outputs) == ("output",)
    assert tuple(exposed_outputs) == ("intermediate", "output")
    # 暴露中间值使其 storage 与 lens_c 计算同期存活：保守峰须严格更高（非零成本）
    assert exposed_record.peak_memory_bytes > control_record.peak_memory_bytes


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="external Component tensor-peak evidence requires a native CUDA device",
)
def test_cuda_estimate_covers_external_native_tensor_factories() -> None:
    """
    外部合法元件直接构造设备张量时，meta 估算仍覆盖 CUDA 总峰值
    """
    for element_type in (
        _NativeConstantElement,
        _NativeDiscardElement,
        _NativeOutputElement,
    ):
        assembly = _external_component_assembly(element_type)
        workstation = Workstation.cuda(0)
        assembly_baseline_bytes = torch.cuda.memory_allocated()
        workstation.host(assembly)

        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            outputs, record = workstation.run(assembly)
        torch.cuda.synchronize()
        measured_total = (
            torch.cuda.max_memory_allocated()
            - assembly_baseline_bytes
        )

        assert isinstance(outputs["field"], OpticalField)
        assert record.peak_memory_bytes >= measured_total
        del outputs, record, workstation, assembly
        gc.collect()


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="real-device factory guard evidence requires a native CUDA device",
)
def test_meta_preflight_rejects_real_factory_before_cuda_allocation() -> None:
    """
    meta 预检在公开工厂执行前拒绝真实设备，不允许检查自身分配显存
    """
    assembly = _external_component_assembly(
        _RealDeviceDiscardElement,
        is_frozen=False,
    )
    allocation_baseline = torch.cuda.memory_allocated()
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    with pytest.raises(
        AssemblyError,
        match="meta_sandbox_real_tensor_forbidden:cuda",
    ):
        assembly.freeze()

    torch.cuda.synchronize()
    allocation_peak = torch.cuda.max_memory_allocated()
    assert allocation_peak - allocation_baseline == 0


def test_workstation_conservative_peak_is_deterministic() -> None:
    """
    同一暖缓存装配与梯度模式的保守峰值不依赖 Python 垃圾回收时机
    """
    for is_gradient_enabled in (False, True):
        assembly, _source, _pupil, _lens = _assembly(cache_state="replacement")
        workstation = Workstation.cpu()
        workstation.host(assembly)
        estimates: list[int] = []
        with _gradient_context(is_gradient_enabled):
            workstation.run(assembly)
        for _repetition in range(5):
            with _gradient_context(is_gradient_enabled):
                _outputs, record = workstation.run(assembly)
                estimates.append(record.peak_memory_bytes)

        assert len(set(estimates)) == 1


def test_warm_cache_real_peak_stays_below_meta_conservative_peak() -> None:
    """
    meta 按设计冷失效值依赖缓存；暖真实运行可更小，但不得越过保守峰
    """

    assembly, _source, _pupil, _lens = _assembly(cache_state="cold")
    workstation = Workstation.cpu()
    workstation.host(assembly)
    workstation.run(assembly)
    request = workstation._prepare_replay_request(  # noqa: SLF001
        assembly,
        root=None,
        inputs=None,
    )

    meta_peak, _meta_trace, meta_schema = (
        workstation._measure_meta_replay(  # noqa: SLF001
            request,
            seed=42,
        )
    )
    _outputs, real_peak, _real_trace, real_schema = (
        workstation._measure_real_replay(  # noqa: SLF001
            request,
            seed=42,
        )
    )

    assert real_peak < meta_peak
    assert real_schema == meta_schema


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA tensor-peak evidence requires a native CUDA device",
)
def test_cuda_estimate_covers_measured_tensor_peaks() -> None:
    """
    公共 Assembly 的 meta 估算覆盖 CUDA 冷暖缓存、替换缓存及梯度前向张量峰值
    """
    for cache_state in ("cold", "warm", "replacement"):
        for is_gradient_enabled in (False, True):
            assembly, _source, _pupil, _lens = _assembly(
                cache_state=cache_state,
            )
            workstation = Workstation.cuda(0)
            assembly_baseline_bytes = torch.cuda.memory_allocated()
            workstation.host(assembly)
            if cache_state == "warm":
                with _gradient_context(is_gradient_enabled):
                    workstation.run(assembly)

            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            with _gradient_context(is_gradient_enabled):
                outputs, record = workstation.run(assembly)
            torch.cuda.synchronize()
            measured_total = (
                torch.cuda.max_memory_allocated()
                - assembly_baseline_bytes
            )

            intensity = outputs["intensity"]
            assert isinstance(intensity, Intensity)
            assert intensity.values.requires_grad is is_gradient_enabled
            assert record.peak_memory_bytes >= measured_total
            del outputs, record, workstation, assembly
            gc.collect()

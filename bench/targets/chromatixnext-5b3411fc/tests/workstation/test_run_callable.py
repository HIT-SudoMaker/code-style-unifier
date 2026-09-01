from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import threading
from typing import Literal
from unittest.mock import MagicMock

import pytest
import torch

from chromatix_next.errors import WorkstationError
from chromatix_next.optics import (
    Assembly,
    FieldNormalization,
    Intensity,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import AmplitudeTransmissionMap
from chromatix_next.optics.source import PlaneWave
from chromatix_next.workstation import NamedOutputs, Workstation

_FACTORY_DEVICES: list[str] = []
_METADATA_FACTORY_DEVICES: list[str] = []
_THREAD_REPLAY_BARRIER: threading.Barrier | None = None


def _field_inputs(
    device: torch.device,
) -> tuple[OpticalField]:
    _FACTORY_DEVICES.append(device.type)
    grid = SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(
            torch.tensor(
                1.0e-6,
                device=device,
                dtype=torch.float64,
            ),
            torch.tensor(
                1.0e-6,
                device=device,
                dtype=torch.float64,
            ),
        ),
    )
    envelope = torch.ones(
        (1, 1, *grid.sample_counts),
        device=device,
        dtype=torch.complex128,
    )
    return (
        OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=Spectrum.monochromatic(wavelength=532.0e-9),
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference((0.0,)),
        ),
    )


def _tensor_path_inputs(
    device: torch.device,
) -> tuple[OpticalField]:
    field = _field_inputs(
        device,
    )[0]
    return (
        OpticalField(
            envelope=field.envelope,
            grid=field.grid,
            spectrum=field.spectrum,
            polarization_representation=field.polarization_representation,
            medium=field.medium,
            normalization=field.normalization,
            path_reference=OpticalPathReference(
                lengths=(
                    torch.zeros(
                        (),
                        device=device,
                        dtype=torch.float64,
                    ),
                ),
            ),
        ),
    )


def _prebuilt_field(
    device: torch.device,
) -> OpticalField:
    grid = SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(
            torch.tensor(1.0e-6, device=device, dtype=torch.float64),
            torch.tensor(1.0e-6, device=device, dtype=torch.float64),
        ),
    )
    return OpticalField(
        envelope=torch.ones(
            (1, 1, 4, 4),
            device=device,
            dtype=torch.complex128,
        ),
        grid=grid,
        spectrum=Spectrum.monochromatic(wavelength=532.0e-9),
        polarization_representation=(Polarization.scalar()).representation,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            (torch.tensor(0.0, device=device, dtype=torch.float64),)
        ),
    )


_PREBUILT_FIELDS = {
    "cpu": _prebuilt_field(torch.device("cpu")),
    "meta": _prebuilt_field(torch.device("meta")),
}
_PATH_MISMATCH_FIELDS = {
    device_name: OpticalField(
        envelope=field.envelope,
        grid=field.grid,
        spectrum=field.spectrum,
        polarization_representation=field.polarization_representation,
        medium=field.medium,
        normalization=field.normalization,
        path_reference=OpticalPathReference(
            (torch.tensor(0.0, dtype=torch.float64),),
        ),
    )
    for device_name, field in _PREBUILT_FIELDS.items()
}


def _invalid_float32_path_reference(
    device: torch.device,
) -> OpticalPathReference:
    reference = OpticalPathReference(
        lengths=(0.0,),
    )
    object.__setattr__(
        reference,
        "lengths",
        (
            torch.tensor(
                0.0,
                device=device,
                dtype=torch.float32,
            ),
        ),
    )
    return reference


def _invalid_float32_grid(
    grid: SpatialGrid,
    device: torch.device,
) -> SpatialGrid:
    invalid = SpatialGrid.centered(
        sample_counts=grid.sample_counts,
        sample_spacing=(1.0e-6, 1.0e-6),
    )
    object.__setattr__(
        invalid,
        "sample_spacing",
        (
            torch.tensor(1.0e-6, device=device, dtype=torch.float32),
            torch.tensor(1.0e-6, device=device, dtype=torch.float32),
        ),
    )
    return invalid


_GRID_DTYPE_MISMATCH_FIELDS = {
    device_name: OpticalField(
        envelope=field.envelope,
        grid=_invalid_float32_grid(field.grid, field.envelope.device),
        spectrum=field.spectrum,
        polarization_representation=field.polarization_representation,
        medium=field.medium,
        normalization=field.normalization,
        path_reference=field.path_reference,
    )
    for device_name, field in _PREBUILT_FIELDS.items()
}


_PATH_DTYPE_MISMATCH_FIELDS = {
    device_name: OpticalField(
        envelope=field.envelope,
        grid=field.grid,
        spectrum=field.spectrum,
        polarization_representation=field.polarization_representation,
        medium=field.medium,
        normalization=field.normalization,
        path_reference=_invalid_float32_path_reference(
            field.envelope.device,
        ),
    )
    for device_name, field in _PREBUILT_FIELDS.items()
}


@dataclass(frozen=True)
class _NestedInput:
    field: OpticalField


def _prebuilt_nested_inputs(
    device: torch.device,
) -> tuple[Mapping[str, _NestedInput]]:
    return ({"incident": _NestedInput(_PREBUILT_FIELDS[device.type])},)


def _calculate_nested_identity(
    root: torch.nn.Module,
    values: Mapping[str, _NestedInput],
) -> Mapping[str, OpticalField]:
    del root
    return {"field": values["incident"].field}


def _path_mismatch_inputs(
    device: torch.device,
) -> tuple[OpticalField]:
    return (_PATH_MISMATCH_FIELDS[device.type],)


def _grid_dtype_mismatch_inputs(
    device: torch.device,
) -> tuple[OpticalField]:
    _METADATA_FACTORY_DEVICES.append(device.type)
    return (_GRID_DTYPE_MISMATCH_FIELDS[device.type],)


def _path_dtype_mismatch_inputs(
    device: torch.device,
) -> tuple[OpticalField]:
    _METADATA_FACTORY_DEVICES.append(device.type)
    return (_PATH_DTYPE_MISMATCH_FIELDS[device.type],)


def _calculate_identity(
    root: torch.nn.Module,
    field: OpticalField,
) -> Mapping[str, OpticalField]:
    del root
    return {"field": field}


class _FieldChain(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造透射与探测的透明组合根
        """

        super().__init__()
        grid = SpatialGrid.centered(
            sample_counts=(4, 4),
            sample_spacing=(
                torch.tensor(1.0e-6, dtype=torch.float64),
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
        )
        self.transmission = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=torch.full(
                (4, 4),
                0.5,
                dtype=torch.float64,
            ),
        )
        self.detector = IntensityDetection()


class _OwnedStateElement(torch.nn.Module):
    def __init__(self, *, is_alias_registered: bool) -> None:
        """
        构造可选注册同 storage 精确别名视图的测试元件
        """

        super().__init__()
        parameter = torch.nn.Parameter(torch.ones(16, dtype=torch.float64))
        self.register_parameter("values", parameter)
        if is_alias_registered:
            self.register_buffer("values_view", parameter.detach())

    @property
    def role(self) -> Literal["element"]:
        """
        返回测试元件角色
        """

        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        原样返回入射场
        """

        return field


class _IdentityElement(torch.nn.Module):
    @property
    def role(self) -> Literal["element"]:
        """
        返回无注册状态的测试元件角色
        """

        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        原样返回入射场
        """

        return field


class _OutputIdentityElement(_IdentityElement):
    def __init__(self) -> None:
        """
        构造以零字节 Buffer 携带阶段设备的测试元件
        """

        super().__init__()
        self.register_buffer("device_marker", torch.empty(0, dtype=torch.float64))


class _ReplacementElement(_OutputIdentityElement):
    def forward(self, field: OpticalField) -> OpticalField:
        """
        以阶段设备上的合法预存场替换入射场
        """

        del field
        device_marker = self.get_buffer("device_marker")
        assert device_marker is not None
        return _PREBUILT_FIELDS[device_marker.device.type]


class _ReplacementChain(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造只含替换元件的透明组合根
        """

        super().__init__()
        self.replacement = _ReplacementElement()


def _empty_inputs(
    device: torch.device,
) -> tuple[()]:
    del device
    return ()


def _calculate_prebuilt_output(
    root: _OutputIdentityElement,
) -> Mapping[str, OpticalField]:
    device_marker = root.get_buffer("device_marker")
    assert device_marker is not None
    return {"field": _PREBUILT_FIELDS[device_marker.device.type]}


def _calculate_after_invalid_intermediate(
    root: _ReplacementChain,
    field: OpticalField,
) -> Mapping[str, OpticalField]:
    invalid_intermediate = _GRID_DTYPE_MISMATCH_FIELDS[
        field.envelope.device.type
    ]
    return {"field": root.replacement(invalid_intermediate)}


def _calculate_owned_state(
    root: _OwnedStateElement,
    field: OpticalField,
) -> Mapping[str, OpticalField]:
    return {"field": root(field)}


def _calculate_after_thread_barrier(
    root: _OwnedStateElement,
    field: OpticalField,
) -> Mapping[str, OpticalField]:
    assert _THREAD_REPLAY_BARRIER is not None
    _THREAD_REPLAY_BARRIER.wait(timeout=10.0)
    return {"field": root(field)}


def _calculate_intensity(
    root: _FieldChain,
    field: OpticalField,
) -> Mapping[str, OpticalField | Intensity]:
    transmitted = root.transmission(field)
    return {"field": transmitted, "intensity": root.detector(transmitted)}


def _calculate_intensity_with_generator(
    root: _FieldChain,
    field: OpticalField,
    *,
    generator: torch.Generator,
) -> Mapping[str, OpticalField]:
    random_phase = torch.rand(
        field.envelope.shape,
        device=field.envelope.device,
        dtype=field.envelope.real.dtype,
        generator=generator,
    )
    randomized = OpticalField(
        envelope=field.envelope * torch.exp(1j * random_phase),
        grid=field.grid,
        spectrum=field.spectrum,
        polarization_representation=field.polarization_representation,
        medium=field.medium,
        normalization=field.normalization,
        path_reference=field.path_reference,
    )
    return {"field": root.transmission(randomized)}


def _calculate_with_runtime_module(
    root: torch.nn.Module,
    field: OpticalField,
) -> Mapping[str, Intensity]:
    del root
    detector = IntensityDetection()
    return {"intensity": detector(field)}


class _TemporaryElement(torch.nn.Module):
    @property
    def role(self) -> Literal["element"]:
        """
        返回测试元件角色
        """

        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        经两个短命中间量返回派生光场
        """

        first = field.envelope * 2.0
        second = first.square()
        del first
        return OpticalField(
            envelope=second,
            grid=field.grid,
            spectrum=field.spectrum,
            polarization_representation=field.polarization_representation,
            medium=field.medium,
            normalization=field.normalization,
            path_reference=field.path_reference,
        )


class _TemporaryChain(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造只含临时量元件的透明组合根
        """

        super().__init__()
        self.temporary = _TemporaryElement()


def _calculate_temporary(
    root: _TemporaryChain,
    field: OpticalField,
) -> Mapping[str, OpticalField]:
    return {"field": root.temporary(field)}


def _calculate_child_forward_directly(
    root: _TemporaryChain,
    field: OpticalField,
) -> Mapping[str, OpticalField]:
    return {"field": root.temporary.forward(field)}


def _calculate_temporary_forward_directly(
    root: torch.nn.Module,
    field: OpticalField,
) -> Mapping[str, OpticalField]:
    del root
    return {"field": _TemporaryElement().forward(field)}


def test_calculation_rejects_direct_forward_but_accepts_module_call() -> None:
    """
    Module 语义是元件进入运行守卫的唯一入口
    """

    root = _TemporaryChain()
    workstation = Workstation.cpu()
    workstation.host(root)

    outputs, _record = workstation.run(
        _calculate_temporary,
        root=root,
        inputs=_field_inputs,
    )
    assert isinstance(outputs["field"], OpticalField)

    for calculation in (
        _calculate_child_forward_directly,
        _calculate_temporary_forward_directly,
    ):
        with pytest.raises(
            WorkstationError,
            match="workstation_calculation_forward_call_forbidden",
        ):
            workstation.run(
                calculation,
                root=root,
                inputs=_field_inputs,
            )


def test_direct_calculation_runs_through_one_replay_boundary() -> None:
    """
    普通模块级计算经唯一 replay 边界返回有序物理值
    """

    root = _FieldChain()
    workstation = Workstation.cpu()
    workstation.host(root)

    outputs, record = workstation.run(
        _calculate_intensity,
        root=root,
        inputs=_field_inputs,
    )

    assert isinstance(outputs, NamedOutputs)
    assert tuple(outputs) == ("field", "intensity")
    field = outputs["field"]
    assert isinstance(field, OpticalField)
    assert field.envelope.dtype is torch.complex128
    assert field.envelope.device == workstation.device
    assert record.peak_memory_bytes > 0
    assert record.seed == 42


def test_replay_keeps_path_accumulator_device_local_float64() -> None:
    """
    meta 与 CPU 重放保持场与网格设备局部一致，并要求张量光程为 float64
    """

    _FACTORY_DEVICES.clear()
    root = _IdentityElement()
    workstation = Workstation.cpu()
    workstation.host(root)

    outputs, record = workstation.run(
        _calculate_identity,
        root=root,
        inputs=_tensor_path_inputs,
    )
    field = outputs["field"]
    assert isinstance(field, OpticalField)
    path_length = field.path_reference.lengths[0]
    assert isinstance(path_length, torch.Tensor)
    assert field.envelope.dtype is torch.complex128
    assert all(
        coordinate.dtype is torch.float64
        for coordinate in (
            *field.grid.sample_spacing,
            *field.grid.first_sample_position,
        )
    )
    assert path_length.dtype is torch.float64
    assert path_length.device == workstation.device
    assert _FACTORY_DEVICES == [
        "meta",
        "cpu",
    ]


def test_infeasible_direct_calculation_never_creates_real_inputs() -> None:
    """
    证明内存拒绝早于真实输入构造
    """

    _FACTORY_DEVICES.clear()
    root = _TemporaryChain()
    workstation = Workstation.cpu()
    workstation.host(root)
    object.__setattr__(workstation, "_memory_boundary_bytes", 1)

    with pytest.raises(
        WorkstationError,
        match="workstation_memory_check_infeasible",
    ):
        workstation.run(
            _calculate_temporary,
            root=root,
            inputs=_field_inputs,
        )

    assert _FACTORY_DEVICES == ["meta"]


def test_cold_direct_replay_has_equal_conservative_peak() -> None:
    """
    无缓存直接计算的 meta 与真实 storage 峰值严格相等
    """

    root = _TemporaryChain()
    workstation = Workstation.cpu()
    workstation.host(root)
    request = workstation._prepare_replay_request(  # noqa: SLF001
        _calculate_temporary,
        root=root,
        inputs=_field_inputs,
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

    assert real_peak == meta_peak
    assert real_schema == meta_schema


def test_direct_calculation_rejects_unhosted_and_foreign_roots() -> None:
    """
    普通计算只接受本工作站精确托管的根
    """

    root = _FieldChain()
    owner = Workstation.cpu()
    foreign = Workstation.cpu()

    with pytest.raises(
        WorkstationError,
        match="workstation_run_not_hosted",
    ):
        owner.run(
            _calculate_intensity,
            root=root,
            inputs=_field_inputs,
        )

    owner.host(root)
    with pytest.raises(
        WorkstationError,
        match="workstation_run_hosted_elsewhere",
    ):
        foreign.run(
            _calculate_intensity,
            root=root,
            inputs=_field_inputs,
        )


def test_direct_calculation_rejects_closure_and_runtime_module() -> None:
    """
    closure 与运行时临时 Module 均不进入可验证运行面
    """

    root = _FieldChain()
    workstation = Workstation.cpu()
    workstation.host(root)
    captured = root.detector

    def _calculation(
        injected_root: torch.nn.Module,
        field: OpticalField,
    ) -> Mapping[str, Intensity]:
        del injected_root
        return {"intensity": captured(field)}

    with pytest.raises(
        WorkstationError,
        match="workstation_calculation_module_function_required",
    ):
        workstation.run(
            _calculation,
            root=root,
            inputs=_field_inputs,
        )
    with pytest.raises(
        WorkstationError,
        match="workstation_calculation_runtime_module_forbidden",
    ):
        workstation.run(
            _calculate_with_runtime_module,
            root=root,
            inputs=_field_inputs,
        )


def test_named_generator_is_reproducible_without_global_rng_change() -> None:
    """
    命名生成器可复现且不推进全局随机状态
    """

    root = _FieldChain()
    workstation = Workstation.cpu()
    workstation.host(root)
    before = torch.random.get_rng_state().clone()

    first, _record = workstation.run(
        _calculate_intensity_with_generator,
        root=root,
        inputs=_field_inputs,
        seed=42,
    )
    second, _record = workstation.run(
        _calculate_intensity_with_generator,
        root=root,
        inputs=_field_inputs,
        seed=42,
    )

    first_field = first["field"]
    second_field = second["field"]
    assert isinstance(first_field, OpticalField)
    assert isinstance(second_field, OpticalField)
    assert torch.equal(first_field.envelope, second_field.envelope)
    assert torch.equal(before, torch.random.get_rng_state())
    manual_first = workstation.generator("phase", seed=42)
    manual_second = workstation.generator("phase", seed=42)
    assert torch.equal(
        torch.rand(4, generator=manual_first),
        torch.rand(4, generator=manual_second),
    )


def test_assembly_rejects_direct_calculation_keywords() -> None:
    """
    Assembly 便捷入口拒绝普通计算专属参数
    """

    grid = SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(1.0e-6, 1.0e-6),
    )
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=532.0e-9),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    detector = IntensityDetection()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(detector, name="detector")
    assembly.connect(source, detector)
    assembly.expose(detector, name="intensity")
    assembly.freeze()
    root = _FieldChain()
    workstation = Workstation.cpu()
    workstation.host(assembly)
    with pytest.raises(
        WorkstationError,
        match="workstation_run_assembly_arguments_forbidden",
    ):
        workstation.run(
            assembly,
            root=root,
            inputs=_field_inputs,
        )


def test_prebuilt_nested_physical_inputs_are_included_in_memory_peak() -> None:
    """
    预存于嵌套载荷的完整物理值仍进入运行内存账簿
    """

    root = _IdentityElement()
    workstation = Workstation.cpu()
    workstation.host(root)

    outputs, record = workstation.run(
        _calculate_nested_identity,
        root=root,
        inputs=_prebuilt_nested_inputs,
    )

    assert outputs["field"] is _PREBUILT_FIELDS["cpu"]
    assert record.peak_memory_bytes > 0


def test_prebuilt_final_physical_output_is_included_in_memory_peak() -> None:
    """
    未经张量算子的最终物理值仍显式进入运行内存账簿
    """

    root = _OutputIdentityElement()
    workstation = Workstation.cpu()
    workstation.host(root)

    outputs, record = workstation.run(
        _calculate_prebuilt_output,
        root=root,
        inputs=_empty_inputs,
    )

    assert outputs["field"] is _PREBUILT_FIELDS["cpu"]
    assert record.peak_memory_bytes > 0


def test_registered_state_views_share_one_owned_storage_charge() -> None:
    """
    Parameter 与 Buffer 视图共享的 storage 只计一次长期占用
    """

    single_root = _OwnedStateElement(is_alias_registered=False)
    alias_root = _OwnedStateElement(is_alias_registered=True)
    single_workstation = Workstation.cpu()
    alias_workstation = Workstation.cpu()
    single_workstation.host(single_root)
    alias_workstation.host(alias_root)

    _single_outputs, single_record = single_workstation.run(
        _calculate_owned_state,
        root=single_root,
        inputs=_prebuilt_cpu_or_meta_inputs,
    )
    _alias_outputs, alias_record = alias_workstation.run(
        _calculate_owned_state,
        root=alias_root,
        inputs=_prebuilt_cpu_or_meta_inputs,
    )

    assert alias_record.peak_memory_bytes == single_record.peak_memory_bytes


def _prebuilt_cpu_or_meta_inputs(
    device: torch.device,
) -> tuple[OpticalField]:
    return (_PREBUILT_FIELDS[device.type],)


def test_input_path_reference_must_follow_replay_device() -> None:
    """
    输入物理值的光程张量必须与该阶段重放设备一致
    """

    root = _FieldChain()
    workstation = Workstation.cpu()
    workstation.host(root)

    with pytest.raises(
        WorkstationError,
        match="workstation_replay_physical_value_device_invalid",
    ):
        workstation.run(
            _calculate_identity,
            root=root,
            inputs=_path_mismatch_inputs,
        )


@pytest.mark.parametrize(
    "inputs",
    (
        _grid_dtype_mismatch_inputs,
        _path_dtype_mismatch_inputs,
    ),
)
def test_input_metadata_must_follow_workstation_real_precision(
    inputs: Callable[[torch.device], tuple[OpticalField]],
) -> None:
    """
    输入网格与光程张量必须使用各自的工作站精度不变量
    """

    root = _IdentityElement()
    workstation = Workstation.cpu()
    workstation.host(root)
    _METADATA_FACTORY_DEVICES.clear()

    with pytest.raises(
        WorkstationError,
        match="workstation_run_physical_value_dtype_invalid",
    ):
        workstation.run(
            _calculate_identity,
            root=root,
            inputs=inputs,
        )
    assert _METADATA_FACTORY_DEVICES == ["meta"]


def test_invalid_intermediate_metadata_is_rejected_before_replacement() -> None:
    """
    下游替换前仍拒绝中间物理值的错误元数据精度
    """

    root = _ReplacementChain()
    workstation = Workstation.cpu()
    workstation.host(root)

    with pytest.raises(
        WorkstationError,
        match="workstation_run_physical_value_dtype_invalid",
    ):
        workstation.run(
            _calculate_after_invalid_intermediate,
            root=root,
            inputs=_prebuilt_cpu_or_meta_inputs,
        )


def test_runtime_module_guard_is_isolated_per_thread() -> None:
    """
    并发合法根只受所属线程的运行期 Module 守卫约束
    """

    global _THREAD_REPLAY_BARRIER
    _THREAD_REPLAY_BARRIER = threading.Barrier(2)
    roots = (
        _OwnedStateElement(is_alias_registered=False),
        _OwnedStateElement(is_alias_registered=False),
    )
    workstations = (
        Workstation.cpu(),
        Workstation.cpu(),
    )
    for workstation, root in zip(workstations, roots, strict=True):
        workstation.host(root)

    def _run(index: int) -> NamedOutputs:
        outputs, _record = workstations[index].run(
            _calculate_after_thread_barrier,
            root=roots[index],
            inputs=_prebuilt_cpu_or_meta_inputs,
        )
        return outputs

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outputs = tuple(executor.map(_run, (0, 1)))
    finally:
        _THREAD_REPLAY_BARRIER = None

    assert all(isinstance(values["field"], OpticalField) for values in outputs)


def test_run_rejects_invalid_seeds_before_replay() -> None:
    """
    非法根种子在重放前被稳定域错误拒绝

    公共 seed 契约 S1：覆盖 bool / 浮点 / 数字串 / 任意串 / None / 非整数对象，
    须在调用 input 工厂前失败；基线对其中多数会经 int() 静默规范化、或在真实
    replay 后才泄漏原生异常，缺乏 locality。
    """

    for invalid_seed in (True, 1.5, "42", "invalid", None, [1]):
        workstation = Workstation.cpu()
        root = _FieldChain()
        workstation.host(root)
        unused_inputs = MagicMock()
        with pytest.raises(
            WorkstationError,
            match="workstation_random_root_seed_invalid",
        ):
            workstation.run(
                _calculate_intensity,
                root=root,
                inputs=unused_inputs,
                seed=invalid_seed,  # type: ignore[arg-type]
            )
        unused_inputs.assert_not_called()


def _calc_with_positional_generator(
    root: torch.nn.Module,
    generator: OpticalField,
) -> Mapping[str, OpticalField]:
    # 位置 generator 参数（非法注入形状）：仅允许 keyword-only generator 注入
    del root, generator
    error_identity = "positional_generator_body_unreachable"
    raise AssertionError(error_identity)


def test_run_rejects_positional_generator_parameter() -> None:
    """
    位置 generator 参数被稳定域错误拒绝

    公共 callable 形状契约 S2：generator 仅经 keyword-only 注入；位置 generator
    会与 input 位置值重复绑定并泄漏原生 TypeError（缺陷 1）。
    """

    workstation = Workstation.cpu()
    root = _FieldChain()
    workstation.host(root)
    with pytest.raises(
        WorkstationError,
        match="workstation_calculation_generator_must_be_keyword_only",
    ):
        workstation.run(
            _calc_with_positional_generator,
            root=root,
            inputs=_field_inputs,
        )


def _calc_with_variadic_positionals(
    root: torch.nn.Module,
    *fields: OpticalField,
) -> Mapping[str, OpticalField]:
    # 变长位置参数让 input 数量契约不再闭合，必须在函数体执行前拒绝
    del root, fields
    error_identity = "variadic_positional_body_unreachable"
    raise AssertionError(error_identity)


def test_run_rejects_variadic_positional_parameters() -> None:
    """
    直接 calculation 的变长位置参数在执行前被稳定域错误拒绝
    """

    workstation = Workstation.cpu()
    root = _FieldChain()
    workstation.host(root)
    with pytest.raises(
        WorkstationError,
        match="workstation_calculation_invocation_incompatible",
    ):
        workstation.run(
            _calc_with_variadic_positionals,
            root=root,
            inputs=_field_inputs,
        )


def _calc_with_variadic_keywords(
    root: torch.nn.Module,
    field: OpticalField,
    **options: object,
) -> Mapping[str, OpticalField]:
    # 变长关键字参数会吞入未声明的调用形状，不能成为可重放 calculation
    del root, field, options
    error_identity = "variadic_keyword_body_unreachable"
    raise AssertionError(error_identity)


def test_run_rejects_variadic_keyword_parameters() -> None:
    """
    直接 calculation 的变长关键字参数在执行前被稳定域错误拒绝
    """

    workstation = Workstation.cpu()
    root = _FieldChain()
    workstation.host(root)
    with pytest.raises(
        WorkstationError,
        match="workstation_calculation_invocation_incompatible",
    ):
        workstation.run(
            _calc_with_variadic_keywords,
            root=root,
            inputs=_field_inputs,
        )


def _calc_requiring_two_inputs(
    root: torch.nn.Module,
    field_a: OpticalField,
    field_b: OpticalField,
) -> Mapping[str, OpticalField]:
    # 必需两个 input；测试工厂只给一个 ⇒ 必需参数不匹配（契约 S2b）
    del root, field_b
    return {"field": field_a}


def test_run_rejects_calculation_with_incompatible_required_parameters() -> None:
    """
    必需参数数与 input 不匹配时被稳定域错误拒绝

    公共 callable 形状契约 S2b：参数不兼容须在 calculation 执行前以域错误
    失败，不泄漏原生 TypeError。
    """

    workstation = Workstation.cpu()
    root = _FieldChain()
    workstation.host(root)
    with pytest.raises(
        WorkstationError,
        match="workstation_calculation_invocation_incompatible",
    ):
        workstation.run(
            _calc_requiring_two_inputs,
            root=root,
            inputs=_field_inputs,
        )

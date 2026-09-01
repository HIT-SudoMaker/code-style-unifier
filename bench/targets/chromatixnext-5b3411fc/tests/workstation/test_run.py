
from __future__ import annotations

from collections.abc import Mapping
import copy
import dataclasses
from typing import Literal

import pytest
import torch

import chromatix_next._ownership as _ownership
from chromatix_next.errors import AssemblyError, WorkstationError
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
from chromatix_next.workstation import NamedOutputs, RunRecord, Workstation
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


def _plane_wave(relative_amplitude: float = 1.0) -> PlaneWave:
    # 沿法线传播的标量偏振平面波源
    return PlaneWave(
        spectrum=_spectrum(),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=relative_amplitude,
    )


def _intensity_output(
    outputs: NamedOutputs,
    name: str,
) -> Intensity:
    # 读取命名强度，并在公共联合类型边界显式收窄

    value = outputs[name]
    assert isinstance(value, Intensity)
    return value


def _field_output(
    outputs: NamedOutputs,
    name: str,
) -> OpticalField:
    # 读取命名光场，并在公共联合类型边界显式收窄

    value = outputs[name]
    assert isinstance(value, OpticalField)
    return value


def _simple_detection_assembly(*, counts: tuple[int, int] = (4, 4)) -> Assembly:
    # 单链装配：PlaneWave → IntensityDetection，暴露命名输出 ``intensity``
    grid = _grid(counts=counts)
    source = _plane_wave()
    detector = IntensityDetection()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(detector, name="detector")
    assembly.connect(source, detector)
    assembly.expose(detector, name="intensity")
    return assembly


def _build_and_host(
    *,
    counts: tuple[int, int] = (4, 4),
) -> tuple[Workstation, Assembly]:
    # 构造 → 冻结 → 托管的完整公共路径，返回 (工作站, 已托管装配)
    workstation = Workstation.cpu()
    assembly = _simple_detection_assembly(counts=counts)
    assembly.freeze()
    workstation.host(assembly)
    return workstation, assembly






# ===== 测试用随机 / OOM 假元件 =====


class _MetadataPrecisionChangingElement(torch.nn.Module):
    # 测试用元件：只破坏网格配对精度或光程参考 float64 累加精度

    def __init__(self, *, quantity: Literal["grid", "path_reference"]) -> None:
        """
        记录要破坏的物理值元数据
        """
        super().__init__()
        self._quantity = quantity

    @property
    def role(self) -> Literal["element"]:
        """
        返回测试元件的不可变元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        返回包络正确但指定元数据错误精度的光场
        """
        grid = field.grid
        path_reference = field.path_reference
        if self._quantity == "grid":
            wrong_grid = copy.copy(field.grid)
            object.__setattr__(
                wrong_grid,
                "sample_spacing",
                (
                    wrong_grid.sample_spacing[0].to(dtype=torch.float32),
                    wrong_grid.sample_spacing[1].to(dtype=torch.float32),
                ),
            )
            grid = wrong_grid
        else:
            path_reference = OpticalPathReference(
                lengths=(0.0,) * len(field.path_reference.lengths),
            )
            object.__setattr__(
                path_reference,
                "lengths",
                tuple(
                    torch.zeros(
                        (),
                        device=field.envelope.device,
                        dtype=torch.float32,
                    )
                    for _ in field.path_reference.lengths
                ),
            )
        return OpticalField(
            envelope=field.envelope,
            grid=grid,
            spectrum=field.spectrum,
            polarization_representation=field.polarization_representation,
            medium=field.medium,
            normalization=field.normalization,
            path_reference=path_reference,
        )


class _RandomPhaseSource(torch.nn.Module):

    @property
    def role(self) -> Literal["source"]:
        """
        返回测试随机源的不可变源角色
        """

        return "source"

    def __init__(
        self,
        *,
        spectrum: Spectrum,
        polarization: Polarization,
        medium: Vacuum,
    ) -> None:
        """记录输出光场所需的强物理值
        """
        super().__init__()
        self._spectrum_value = spectrum
        self._polarization_value = polarization
        self._medium_value = medium
        self._device_anchor: torch.Tensor
        self.register_buffer(
            "_device_anchor",
            torch.empty((), dtype=torch.float64),
            persistent=False,
        )

    def forward(  # type: ignore[override]
        self,
        grid: SpatialGrid,
        *,
        generator: torch.Generator | None = None,
    ) -> OpticalField:
        """按给定 generator 采样随机相位并返回相对归一化光场
        """
        counts_y, counts_x = grid.sample_counts
        if (
            generator is None
            and self._device_anchor.device.type == "meta"
        ):
            generator = torch.Generator(device="cpu")
            generator.manual_seed(42)
        if generator is None:
            # 规约"Run Randomness"：随机组件运行外调用须显式 generator
            error_identity = "random_phase_source_generator_required"
            raise RuntimeError(error_identity)
        else:
            phase = torch.rand(
                (
                    self._spectrum_value.count,
                    self._polarization_value.component_count,
                    counts_y,
                    counts_x,
                ),
                device=self._device_anchor.device,
                generator=generator,
                dtype=torch.float64,
            )
            envelope = torch.exp(
                torch.complex(torch.zeros_like(phase), phase)
            )
        return OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=self._spectrum_value,
            polarization_representation=(self._polarization_value).representation,
            medium=self._medium_value,
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(
                lengths=(0.0,) * self._spectrum_value.count,
            ),
        )



def _random_phase_assembly(*, source_name: str) -> Assembly:
    # 含一个随机光源的装配，光源注册在 ``source_name`` 下并暴露其输出
    grid = _grid()
    spectrum = _spectrum()
    polarization = Polarization.scalar()
    medium = Vacuum()
    source = _RandomPhaseSource(
        spectrum=spectrum,
        polarization=polarization,
        medium=medium,
    )
    assembly = Assembly()
    assembly.include(source, name=source_name, grid=grid)
    assembly.expose(source, name="field")
    return assembly


class TestRunFullAssembly:
    """
    完整运行：命名输出仅含物理值、值正确；返回不可变运行记录
    """

    def test_run_returns_named_outputs_and_complete_immutable_record(self) -> None:
        """运行返回物理输出与完整、公开、不可变的固定双精度记录
        """
        workstation, assembly = _build_and_host()
        outputs, record = workstation.run(assembly)
        assert isinstance(outputs, NamedOutputs)
        assert isinstance(outputs, Mapping)
        assert isinstance(record, RunRecord)
        from chromatix_next.workstation import RunRecord as imported_record

        assert imported_record is RunRecord
        assert dataclasses.is_dataclass(RunRecord)
        fields = {field.name for field in dataclasses.fields(RunRecord)}
        assert {
            "device",
            "implementation",
            "seed",
            "peak_memory_bytes",
            "memory_boundary_bytes",
            "torch_version",
            "is_cuda_available",
            "cuda_device_name",
            "stream_derivation",
        }.issubset(fields)
        assert record.device == "cpu"
        assert record.implementation == "pytorch"
        assert record.seed == 42
        assert record.peak_memory_bytes > 0
        assert record.memory_boundary_bytes > 0
        assert isinstance(record.torch_version, str) and record.torch_version
        assert isinstance(record.is_cuda_available, bool)
        assert isinstance(record.stream_derivation, str) and record.stream_derivation
        assert (
            _intensity_output(outputs, "intensity").values.dtype
            is torch.float64
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.seed = 999  # type: ignore[misc]

    def test_named_outputs_cannot_be_constructed_outside_run(self) -> None:
        """即使值合法，用户也不能伪造一个成功运行结果
        """
        workstation, assembly = _build_and_host()
        outputs, _record = workstation.run(assembly)

        with pytest.raises(AssemblyError) as rejected:
            NamedOutputs(
                {
                    "intensity": outputs["intensity"],
                }
            )
        assert rejected.value.identity == "named_outputs_run_only"

    def test_named_outputs_contain_only_physical_values(self) -> None:
        """命名输出值仅为物理值（``Intensity``），无执行元数据
        """
        workstation, assembly = _build_and_host()
        outputs, _record = workstation.run(assembly)
        assert tuple(outputs) == ("intensity",)
        intensity = _intensity_output(outputs, "intensity")
        assert isinstance(intensity, Intensity)
        # 命名输出不得是裸张量或记录对象
        assert not isinstance(intensity, torch.Tensor)
        assert not isinstance(intensity, RunRecord)

    def test_named_outputs_are_read_only(self) -> None:
        """成功运行返回的命名结果映射不允许增删或替换物理值
        """
        workstation, assembly = _build_and_host()
        outputs, _record = workstation.run(assembly)
        with pytest.raises(TypeError):
            outputs["intensity"] = outputs["intensity"]  # type: ignore[index]






class TestRunRepeatsBothChecks:
    """
    每次运行重复装配检查 + 工作站内存检查（在执行前）
    """

    def test_run_repeats_assembly_check(self) -> None:
        """运行确实重复装配检查：把 ``Assembly.check`` 替换为抛错并断言 ``run`` 传播

        合法的冻结+托管装配本应通过检查；此处用 monkeypatch 把 ``check`` 替换为抛
        ``AssemblyError``，证明 ``run`` 不跳过装配检查（规约"Assembly Freeze"：run 仍
        重复两道检查）。同时验证未托管/他站托管的装配在运行入口即被拒绝。
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        workstation.host(assembly)

        def _defective_check() -> None:
            raise AssemblyError(
                "assembly_check_forced_failure_at_run",
                "这是测试注入的装配检查失败，用来证明运行会重复该检查",
            )

        assembly.check = _defective_check  # type: ignore[method-assign]
        with pytest.raises(AssemblyError) as exception:
            workstation.run(assembly)
        assert exception.value.identity == "assembly_check_forced_failure_at_run"

    def test_run_repeats_memory_check_even_when_check_passes(self) -> None:
        """运行在装配检查通过后仍执行内存检查（端到端经极小边界触发）

        替换私有默认边界探针后经正式 CPU 工厂取得极小边界，端到端验证：装配检查
        通过（合法小装配），但内存检查在运行时再次执行并拒绝。
        """
        tiny = cpu_workstation(1)
        assembly = _simple_detection_assembly()
        assembly.freeze()
        tiny.host(assembly)
        with pytest.raises(WorkstationError) as exception:
            tiny.run(assembly)
        assert "workstation_memory_check_infeasible" in str(exception.value)


    def test_run_rejects_unhosted_assembly(self) -> None:
        """未托管的装配 ⇒ ``WorkstationError``
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        with pytest.raises(WorkstationError) as exception:
            workstation.run(assembly)
        assert "workstation_run_not_hosted" in str(exception.value)

    def test_run_rejects_assembly_hosted_elsewhere(self) -> None:
        """被他站托管的装配 ⇒ ``WorkstationError``
        """
        first = Workstation.cpu()
        second = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        first.host(assembly)
        with pytest.raises(WorkstationError) as exception:
            second.run(assembly)
        assert "workstation_run_hosted_elsewhere" in str(exception.value)



class TestRunDeterminism:
    """
    决定性：默认 seed=42 跨运行一致；显式 seed 可复现；seed 重写生效
    """

    def test_default_seed_deterministic_across_runs(self) -> None:
        """同一装配同一工作站默认 seed ⇒ 命名输出跨运行逐元素一致
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        workstation.host(assembly)
        outputs_a, _ = workstation.run(assembly)
        outputs_b, _ = workstation.run(assembly)
        assert torch.allclose(
            _intensity_output(outputs_a, "intensity").values,
            _intensity_output(outputs_b, "intensity").values,
        )

    def test_explicit_seed_reproduces(self) -> None:
        """显式 seed=42 与默认 seed 结果一致；显式同 seed 跨运行一致
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        workstation.host(assembly)
        outputs_default, _ = workstation.run(assembly)
        outputs_explicit, _ = workstation.run(assembly, seed=42)
        outputs_repeat, _ = workstation.run(assembly, seed=42)
        assert torch.allclose(
            _intensity_output(outputs_default, "intensity").values,
            _intensity_output(outputs_explicit, "intensity").values,
        )
        assert torch.allclose(
            _intensity_output(outputs_explicit, "intensity").values,
            _intensity_output(outputs_repeat, "intensity").values,
        )

    def test_seed_recorded_in_record(self) -> None:
        """显式 seed 写入运行记录
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        workstation.host(assembly)
        _outputs, record = workstation.run(assembly, seed=31337)
        assert record.seed == 31337

    def test_run_does_not_mutate_global_random_state(self) -> None:
        """运行使用设备本地 generator，永不改全局随机状态（seed、CPU/CUDA RNG 字节流）
        """
        torch.manual_seed(123)
        global_seed_before = torch.initial_seed()
        cpu_state_before = torch.random.get_rng_state()
        cuda_states_before = (
            torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
        )
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        workstation.host(assembly)
        workstation.run(assembly)
        assert torch.initial_seed() == global_seed_before
        # 规约"Run Randomness"：全局 RNG 状态（含 CPU 字节流）逐字节不变
        assert torch.equal(cpu_state_before, torch.random.get_rng_state())
        if cuda_states_before is not None:
            cuda_states_after = torch.cuda.get_rng_state_all()
            # CUDA 不可用时本分支跳过；可用时所有设备流须逐字节一致
            assert len(cuda_states_after) == len(cuda_states_before)
            for before, after in zip(cuda_states_before, cuda_states_after):
                assert torch.equal(before, after)




class TestRunRandomStreams:
    """
    按名独立随机流：与稳定名绑定、与无关拓扑序无关；运行外须显式 generator
    """

    def test_random_component_outside_run_requires_generator(self) -> None:
        """随机光源在缺生成器时抛出 ``RuntimeError``
        """
        grid = _grid()
        source = _RandomPhaseSource(
            spectrum=_spectrum(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
        )
        with pytest.raises(RuntimeError) as exception:
            source(grid)
        assert "random_phase_source_generator_required" in str(exception.value)

    def test_random_stream_is_name_derived_and_independent(self) -> None:
        """同名 ⇒ 同流；异名 ⇒ 独立流（与是否存在其他元件无关）

        两个装配分别把同一随机光源注册为 ``alpha`` 与 ``beta``；默认 seed=42 下两者
        输出应不同（异名独立流）。再构造一个同时含 ``alpha`` 与 ``beta`` 的装配，两者
        的输出须分别与前两个单名装配一致——证明流按名决定、与拓扑中是否存在其他元件
        无关。
        """
        workstation = Workstation.cpu()

        assembly_alpha = _random_phase_assembly(source_name="alpha")
        assembly_alpha.freeze()
        workstation.host(assembly_alpha)
        outputs_alpha_only, _ = workstation.run(assembly_alpha)

        assembly_beta = _random_phase_assembly(source_name="beta")
        assembly_beta.freeze()
        workstation.host(assembly_beta)
        outputs_beta_only, _ = workstation.run(assembly_beta)

        # 异名 ⇒ 独立流 ⇒ 包络不同
        assert not torch.allclose(
            _field_output(outputs_alpha_only, "field").envelope,
            _field_output(outputs_beta_only, "field").envelope,
        )

        grid = _grid()
        spectrum = _spectrum()
        polarization = Polarization.scalar()
        medium = Vacuum()
        assembly_both = Assembly()
        alpha_source = _RandomPhaseSource(
            spectrum=spectrum,
            polarization=polarization,
            medium=medium,
        )
        beta_source = _RandomPhaseSource(
            spectrum=spectrum,
            polarization=polarization,
            medium=medium,
        )
        assembly_both.include(alpha_source, name="alpha", grid=grid)
        assembly_both.include(beta_source, name="beta", grid=grid)
        assembly_both.expose(alpha_source, name="alpha_field")
        assembly_both.expose(beta_source, name="beta_field")
        assembly_both.freeze()
        workstation.host(assembly_both)
        outputs_both, _ = workstation.run(assembly_both)
        assert torch.allclose(
            _field_output(outputs_alpha_only, "field").envelope,
            _field_output(outputs_both, "alpha_field").envelope,
        )
        assert torch.allclose(
            _field_output(outputs_beta_only, "field").envelope,
            _field_output(outputs_both, "beta_field").envelope,
        )

    def test_random_stream_seed_dependent(self) -> None:
        """同一名字、不同 seed ⇒ 不同流
        """
        workstation = Workstation.cpu()
        assembly = _random_phase_assembly(source_name="alpha")
        assembly.freeze()
        workstation.host(assembly)
        outputs_seed42, _ = workstation.run(assembly, seed=42)
        outputs_seed99, _ = workstation.run(assembly, seed=99)
        assert not torch.allclose(
            _field_output(outputs_seed42, "field").envelope,
            _field_output(outputs_seed99, "field").envelope,
        )

    def test_random_stream_reproducible_with_explicit_seed(self) -> None:
        """同一名字、同一显式 seed ⇒ 跨运行一致
        """
        workstation = Workstation.cpu()
        assembly = _random_phase_assembly(source_name="alpha")
        assembly.freeze()
        workstation.host(assembly)
        outputs_first, _ = workstation.run(assembly, seed=7)
        outputs_second, _ = workstation.run(assembly, seed=7)
        assert torch.allclose(
            _field_output(outputs_first, "field").envelope,
            _field_output(outputs_second, "field").envelope,
        )


class TestRunSeedContract:
    """
    公共 seed 契约：非法种子在重放前被稳定域错误拒绝，随机与非随机路径一致
    """

    def test_run_rejects_invalid_seeds_for_non_random_assembly(self) -> None:
        """
        非随机装配的非法根种子在重放前被稳定域错误拒绝

        非随机装配与随机装配都执行同一 seed 严格校验；随机
        路径共用入口校验，恢复 locality（契约 S3）。
        """

        for invalid_seed in (True, 1.5, "42", "invalid", None):
            workstation, assembly = _build_and_host()
            with pytest.raises(
                WorkstationError,
                match="workstation_random_root_seed_invalid",
            ):
                workstation.run(
                    assembly,
                    seed=invalid_seed,  # type: ignore[arg-type]
                )

    def test_run_rejects_invalid_seed_for_random_assembly_same_authority(
        self,
    ) -> None:
        """
        随机装配与非随机装配的非法种子经同一域错误身份拒绝

        同一公共 seed 参数不再因是否消费随机流而分歧（locality 见证）。
        """

        workstation = Workstation.cpu()
        assembly = _random_phase_assembly(source_name="source")
        assembly.freeze()
        workstation.host(assembly)
        with pytest.raises(
            WorkstationError,
            match="workstation_random_root_seed_invalid",
        ):
            workstation.run(
                assembly,
                seed="invalid",  # type: ignore[arg-type]  # 故意传入非法种子
            )

    def test_run_accepts_valid_integer_seeds_for_assembly(self) -> None:
        """
        合法整数根种子按文档范围通过并原样记入运行记录

        覆盖零、负、大整数；运行记录不经 int() 二次规范化（契约 S4）。
        """

        for valid_seed in (0, -1, 2**64):
            workstation, assembly = _build_and_host()
            _outputs, record = workstation.run(assembly, seed=valid_seed)
            assert record.seed == valid_seed




class TestHostAcceptsAssembly:
    """
    ``host`` 接受冻结装配；托管主体不能换工作站；身份不入 ``state_dict``
    """

    def test_host_accepts_frozen_assembly(self) -> None:
        """冻结装配可被 ``host`` 接受并把其元件参数/缓冲搬到目标精度/设备
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        returned = workstation.host(assembly)
        assert returned is assembly
        assert assembly.is_frozen is True

    def test_host_rejects_unfrozen_assembly(self) -> None:
        """未冻结装配 ⇒ ``WorkstationError``
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        with pytest.raises(WorkstationError) as exception:
            workstation.host(assembly)
        assert "workstation_host_assembly_not_frozen" in str(exception.value)

    def test_host_assembly_idempotent_on_same_workstation(self) -> None:
        """同一装配在同一工作站上重复托管幂等
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        first = workstation.host(assembly)
        second = workstation.host(assembly)
        assert first is assembly and second is assembly

    def test_host_rejects_same_root_with_changed_module_tree(self) -> None:
        """同根重复托管仍须匹配首次托管的完整模块树
        """
        amplitude = torch.nn.Parameter(
            torch.tensor(1.25, dtype=torch.float64),
        )
        source = PlaneWave(
            spectrum=_spectrum(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=amplitude,
        )
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        parameter_identity = id(amplitude)
        parameter_value = amplitude.detach().clone()
        assembly._modules.pop("source")  # noqa: SLF001

        with pytest.raises(
            WorkstationError,
            match="workstation_host_tree_changed",
        ):
            workstation.host(assembly)

        assert id(amplitude) == parameter_identity
        assert torch.equal(amplitude.detach(), parameter_value)

    def test_hosted_assembly_cannot_change_workstation(self) -> None:
        """已托管的装配不能再托管到他站
        """
        first = Workstation.cpu()
        second = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        first.host(assembly)
        with pytest.raises(WorkstationError):
            second.host(assembly)

    def test_nested_component_cannot_be_rehosted_on_another_workstation(
        self,
    ) -> None:
        """完整装配托管后，内含组件不能被另一工作站独立托管
        """
        amplitude = torch.nn.Parameter(
            torch.tensor(1.25, dtype=torch.float64),
        )
        source = PlaneWave(
            spectrum=_spectrum(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=amplitude,
        )
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        assembly.freeze()
        owner = Workstation.cpu()
        foreign = Workstation.cpu()
        owner.host(assembly)
        parameter_identity = id(amplitude)
        parameter_value = amplitude.detach().clone()
        parameter_device = amplitude.device
        buffer_state = {
            name: value.detach().clone()
            for name, value in source.named_buffers()
        }

        with pytest.raises(
            WorkstationError,
            match="workstation_host_already_hosted",
        ):
            foreign.host(source)

        assert id(amplitude) == parameter_identity
        assert amplitude.dtype is torch.float64
        assert amplitude.device == parameter_device
        assert torch.equal(amplitude.detach(), parameter_value)
        for name, value in source.named_buffers():
            expected = buffer_state[name]
            assert value.dtype is expected.dtype
            assert value.device == expected.device
            assert torch.equal(value, expected)
        outputs, _record = owner.run(assembly)
        assert _intensity_output(outputs, "intensity").values.dtype is torch.float64

    def test_foreign_nested_component_rejects_before_siblings_move(
        self,
    ) -> None:
        """他站预托管的内含组件使整棵装配在移动未托管 siblings 前拒绝
        """
        grid = _grid()
        source_amplitude = torch.nn.Parameter(
            torch.tensor(1.25, dtype=torch.float64),
        )
        source = PlaneWave(
            spectrum=_spectrum(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=source_amplitude,
        )
        transmission = torch.nn.Parameter(
            torch.full(
                grid.sample_counts,
                0.5,
                dtype=torch.float64,
            ),
        )
        element = AmplitudeTransmissionMap(
            grid=grid,
            amplitude_transmission=transmission,
        )
        detector = IntensityDetection()
        foreign = Workstation.cpu()
        owner = Workstation.cpu()
        foreign.host(source)
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(element, name="element")
        assembly.include(detector, name="detector")
        assembly.connect(source, element)
        assembly.connect(element, detector)
        assembly.expose(detector, name="intensity")
        assembly.freeze()
        siblings = (assembly, element, detector)
        sibling_snapshots = tuple(
            (
                sibling,
                tuple(
                    (
                        tensor,
                        id(tensor),
                        tensor.dtype,
                        tensor.device,
                        tensor.detach().clone(),
                    )
                    for tensor in (
                        *sibling.parameters(recurse=False),
                        *sibling.buffers(recurse=False),
                    )
                ),
            )
            for sibling in siblings
        )

        with pytest.raises(
            WorkstationError,
            match="workstation_host_already_hosted",
        ):
            owner.host(assembly)

        for _sibling, tensor_snapshots in sibling_snapshots:
            for tensor, identity, dtype, device, value in tensor_snapshots:
                assert id(tensor) == identity
                assert tensor.dtype is dtype
                assert tensor.device == device
                assert torch.equal(tensor.detach(), value)
        assert foreign.host(source) is source
        foreign_field = source(grid)
        assert foreign_field.envelope.dtype is torch.complex128
        assert source_amplitude.dtype is torch.float64

    def test_independently_hosted_component_makes_assembly_partial(
        self,
    ) -> None:
        """同站独立托管组件不能被静默吸收到后来冻结的完整装配
        """
        workstation = Workstation.cpu()
        source = _plane_wave()
        detector = IntensityDetection()
        workstation.host(source)
        assembly = Assembly()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        assembly.freeze()

        with pytest.raises(
            WorkstationError,
            match="workstation_host_partial_ownership",
        ):
            workstation.host(assembly)

        other = Workstation.cpu()
        assert other.host(detector) is detector

    def test_run_rejects_missing_nested_ownership(self) -> None:
        """运行前复检完整树，拒绝被移除托管身份的内部组件
        """
        source = _plane_wave()
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        del _ownership._HOST_CLAIMS[source]  # noqa: SLF001

        with pytest.raises(
            WorkstationError,
            match="workstation_run_not_hosted",
        ):
            workstation.run(assembly)

    @pytest.mark.parametrize(
        ("ownership_change", "error_identity"),
        [
            ("preserved", "workstation_run_host_tree_changed"),
            ("transferred", "workstation_run_not_hosted"),
        ],
    )
    def test_run_rejects_hosted_component_removed_from_module_tree(
        self,
        ownership_change: str,
        error_identity: str,
    ) -> None:
        """运行清单拒绝从注册树移除、但仍被冻结事实引用的组件
        """
        amplitude = torch.nn.Parameter(
            torch.tensor(1.25, dtype=torch.float64),
        )
        source = PlaneWave(
            spectrum=_spectrum(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=amplitude,
        )
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        parameter_identity = id(amplitude)
        parameter_value = amplitude.detach().clone()
        call_count = 0

        def _count_source_call(
            _module: torch.nn.Module,
            _arguments: tuple[object, ...],
        ) -> None:
            nonlocal call_count
            call_count += 1

        source.register_forward_pre_hook(_count_source_call)
        assembly._modules.pop("source")  # noqa: SLF001
        if ownership_change == "transferred":
            workstation.release(assembly)
            foreign = Workstation.cpu()
            foreign.host(source)

        with pytest.raises(
            WorkstationError,
            match=error_identity,
        ):
            workstation.run(assembly)

        assert call_count == 0
        assert id(amplitude) == parameter_identity
        assert torch.equal(amplitude.detach(), parameter_value)

    def test_run_rejects_nested_parameter_precision_drift(self) -> None:
        """运行前拒绝内部 Parameter 偏离工作站配对精度
        """
        amplitude = torch.nn.Parameter(
            torch.tensor(1.0, dtype=torch.float64),
        )
        source = PlaneWave(
            spectrum=_spectrum(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection.forward(),
            relative_amplitude=amplitude,
        )
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        amplitude.data = amplitude.data.to(dtype=torch.float32)

        with pytest.raises(
            WorkstationError,
            match="workstation_run_precision_mismatch",
        ):
            workstation.run(assembly)

    @pytest.mark.parametrize(
        "quantity",
        ["grid", "path_reference"],
    )
    def test_run_checks_every_physical_value_tensor(
        self,
        quantity: Literal["grid", "path_reference"],
    ) -> None:
        """
        网格与光程张量不能绕过各自的工作站精度不变量
        """
        source = _plane_wave()
        invalidator = _MetadataPrecisionChangingElement(
            quantity=quantity,
        )
        assembly = Assembly()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(invalidator, name="invalidator")
        assembly.connect(source, invalidator)
        assembly.expose(invalidator, name="field")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)

        with pytest.raises(
            WorkstationError,
            match="workstation_run_physical_value_dtype_invalid",
        ):
            workstation.run(assembly)

    def test_host_assembly_identity_absent_from_state_dict(self) -> None:
        """托管身份仅为运行时标记，不入 ``state_dict``
        """
        workstation = Workstation.cpu()
        assembly = _simple_detection_assembly()
        assembly.freeze()
        workstation.host(assembly)
        state = assembly.state_dict()
        assert all("host" not in key.lower() for key in state)
        assert all("chromatix" not in key.lower() for key in state)


# ===== 公共 API 导出校验：RunRecord 可由外部代码导入 =====

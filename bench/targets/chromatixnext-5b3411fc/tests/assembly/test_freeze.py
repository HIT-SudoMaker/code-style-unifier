from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import io
from typing import Literal

import numpy as np
import pytest
import torch
from torch.utils._python_dispatch import TorchDispatchMode

from chromatix_next.errors import AssemblyError
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
from chromatix_next.optics._assembly_facts import _Connection  # noqa: SLF001
from chromatix_next.optics._grid_state import _GridState
from chromatix_next.optics.combination import CoherentCombination
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealThinLens,
)
from chromatix_next.optics.source import PlaneWave

_REJECTED_GRID_MESSAGE = "rejected_grid_for_mode_restoration"

from chromatix_next.workstation import Workstation


def _grid(
    counts: tuple[int, int] = (6, 6),
    spacing: tuple[float, float] = (0.5e-6, 0.5e-6),
) -> SpatialGrid:
    # 中心对齐的小型横向网格，供马赫–曾德尔与单链拓扑使用
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )

def _spectrum(wavelength: float = 2.0e-6) -> Spectrum:
    # 单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)

def _plane_wave(
    *,
    spectrum: Spectrum,
    polarization: Polarization | None = None,
    relative_amplitude: float = 1.0,
) -> PlaneWave:
    # 沿法线传播的平面波源；默认标量偏振
    return PlaneWave(
        spectrum=spectrum,
        polarization=polarization or Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=relative_amplitude,
    )

class _GridChangingPropagation(torch.nn.Module):
    def __init__(self, output_grid: SpatialGrid) -> None:
        super().__init__()
        self._output_grid_state = _GridState(output_grid)

    @property
    def role(self) -> Literal["propagation"]:
        return "propagation"

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        assert field.spectrum.count == 1
        return self._output_grid_state.value

    def forward(self, field: OpticalField) -> OpticalField:
        return OpticalField(
            envelope=field.envelope,
            grid=self._output_grid_for(field),
            spectrum=field.spectrum,
            polarization_representation=field.polarization_representation,
            medium=field.medium,
            normalization=field.normalization,
            path_reference=field.path_reference,
        )

class _RejectedGridPropagation(torch.nn.Module):
    @property
    def role(self) -> Literal["propagation"]:
        return "propagation"

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        del field
        raise ValueError(_REJECTED_GRID_MESSAGE)

    def forward(self, field: OpticalField) -> OpticalField:
        return field

class _OversizedGridMetadataPropagation(torch.nn.Module):
    @property
    def role(self) -> Literal["propagation"]:
        return "propagation"

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        torch.ones(
            2,
            dtype=field.grid.sample_spacing[0].dtype,
            device=field.grid.sample_spacing[0].device,
        )
        return field.grid

    def forward(self, field: OpticalField) -> OpticalField:
        return field

class _ExpandedGridMetadataPropagation(torch.nn.Module):
    @property
    def role(self) -> Literal["propagation"]:
        return "propagation"

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        field.grid.sample_spacing[0].expand(2)
        return field.grid

    def forward(self, field: OpticalField) -> OpticalField:
        return field

class _ArrayPayloadGridMetadataPropagation(torch.nn.Module):
    @property
    def role(self) -> Literal["propagation"]:
        return "propagation"

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        torch.as_tensor(
            np.ones(2),
            device=field.grid.sample_spacing[0].device,
        )
        return field.grid

    def forward(self, field: OpticalField) -> OpticalField:
        return field

class _RealFactoryBodyProbe(TorchDispatchMode):
    def __init__(self) -> None:
        super().__init__()
        self.real_expand_calls = 0
        self.real_ones_calls = 0

    def __torch_dispatch__(
        self,
        function: object,
        types: object,
        arguments: tuple[object, ...] = (),
        keywords: dict[str, object] | None = None,
    ) -> object:
        """
        记录越界真实算子是否穿过被测执行前守卫
        """

        del types
        assert callable(function)
        resolved_keywords = keywords or {}
        schema = getattr(function, "_schema", None)
        if (
            getattr(schema, "name", None) == "aten::ones"
            and resolved_keywords.get("device") != torch.device("meta")
        ):
            self.real_ones_calls += 1
        if (
            getattr(schema, "name", None) == "aten::expand"
            and arguments
            and isinstance(arguments[0], torch.Tensor)
            and arguments[0].device.type != "meta"
        ):
            self.real_expand_calls += 1
        return function(*arguments, **resolved_keywords)

def _linear_assembly(
    *,
    grid: SpatialGrid | None = None,
    spectrum: Spectrum | None = None,
) -> tuple[Assembly, IntensityDetection]:
    # 构造合法马赫–曾德尔装配：单源 → 分束器 → 双臂 → 互易重组 → 探测
    grid = grid if grid is not None else _grid()
    spectrum = spectrum if spectrum is not None else _spectrum()
    source = _plane_wave(spectrum=spectrum, relative_amplitude=1.0)
    arm_upper = IdealThinLens(grid=grid, focal_length=1.0e-3)
    arm_lower = IdealThinLens(grid=grid, focal_length=2.0e-3)
    detector = IntensityDetection()

    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(arm_upper, name="arm_upper")
    assembly.include(arm_lower, name="arm_lower")
    assembly.include(detector, name="detector")

    assembly.connect(source, arm_upper)
    assembly.connect(arm_upper, arm_lower)
    assembly.connect(arm_lower, detector)
    assembly.expose(detector, name="intensity")
    return assembly, detector


@pytest.mark.parametrize(
    "include_unused_cube",
    (False, True),
    ids=("ordinary", "unused_cube"),
)
def test_dead_source_reachability_is_unchanged_by_unused_cube_and_retryable(
    include_unused_cube: bool,
) -> None:
    grid = _grid()
    live = _plane_wave(spectrum=_spectrum())
    dead = _plane_wave(spectrum=_spectrum())
    detector = IntensityDetection()
    assembly = Assembly()
    assembly.include(live, name="live", grid=grid)
    assembly.include(detector, name="detector")
    assembly.include(dead, name="dead", grid=grid)
    assembly.connect(live, detector)
    assembly.expose(detector, name="intensity")
    if include_unused_cube:
        assembly.include_directional(
            IdealNonpolarizingCubeBeamSplitter(
                origin=(0.0, 0.0, 0.0),
                route_right=(1.0, 0.0, 0.0),
                route_top=(0.0, 1.0, 0.0),
                coating_diagonal=CubeCoatingDiagonal.RISING,
                mixing_angle=0.37,
            ),
            name="unused_cube",
        )
    authored_state = (
        assembly._component_names,  # noqa: SLF001
        tuple(assembly._exposures),  # noqa: SLF001
        assembly._directional_owner_names,  # noqa: SLF001
    )

    with pytest.raises(AssemblyError) as rejected:
        assembly.freeze()

    assert rejected.value.identity == (
        "assembly_component_not_on_exposed_path:dead"
    )
    assert not assembly.is_frozen
    assert assembly._frozen_facts is None  # noqa: SLF001
    assert (
        assembly._component_names,  # noqa: SLF001
        tuple(assembly._exposures),  # noqa: SLF001
        assembly._directional_owner_names,  # noqa: SLF001
    ) == authored_state

    assembly.expose(dead, name="dead_field")
    assembly.freeze()

    assert assembly.is_frozen
    assert assembly._frozen_facts is not None  # noqa: SLF001
    assert assembly.exposed_names() == ("intensity", "dead_field")


@pytest.mark.parametrize(
    "include_unused_cube",
    (False, True),
    ids=("ordinary", "unused_cube"),
)
def test_no_exposure_rejection_is_unchanged_by_unused_cube_and_retryable(
    include_unused_cube: bool,
) -> None:
    source = _plane_wave(spectrum=_spectrum())
    detector = IntensityDetection()
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include(detector, name="detector")
    assembly.connect(source, detector)
    if include_unused_cube:
        assembly.include_directional(
            IdealNonpolarizingCubeBeamSplitter(
                origin=(0.0, 0.0, 0.0),
                route_right=(1.0, 0.0, 0.0),
                route_top=(0.0, 1.0, 0.0),
                coating_diagonal=CubeCoatingDiagonal.RISING,
                mixing_angle=0.37,
            ),
            name="unused_cube",
        )
    authored_state = (
        assembly._component_names,  # noqa: SLF001
        tuple(assembly._connections),  # noqa: SLF001
        tuple(assembly._exposures),  # noqa: SLF001
        assembly._directional_owner_names,  # noqa: SLF001
    )

    for operation in (assembly.check, assembly.freeze):
        with pytest.raises(AssemblyError) as rejected:
            operation()

        assert rejected.value.identity == "assembly_output_not_exposed"
        assert not assembly.is_frozen
        assert assembly._frozen_facts is None  # noqa: SLF001
        assert (
            assembly._component_names,  # noqa: SLF001
            tuple(assembly._connections),  # noqa: SLF001
            tuple(assembly._exposures),  # noqa: SLF001
            assembly._directional_owner_names,  # noqa: SLF001
        ) == authored_state

    assembly.expose(detector, name="intensity")
    assert assembly.check() is None
    assembly.freeze()

    assert assembly.is_frozen
    assert assembly._frozen_facts is not None  # noqa: SLF001
    assert tuple(assembly._replay()) == ("intensity",)  # noqa: SLF001


class TestCheck:
    """
    检查层（check）：无张量拓扑与物理兼容性
    """

    def test_grid_changing_component_owns_its_output_grid_rule(self) -> None:
        """
        新传播元件只实现窄私有 seam 即可参与全路径网格预检
        """
        input_grid = _grid()
        output_grid = SpatialGrid.centered(
            sample_counts=input_grid.sample_counts,
            sample_spacing=(0.75e-6, 0.75e-6),
            orientation=input_grid.orientation,
        )
        source = _plane_wave(spectrum=_spectrum())
        propagation = _GridChangingPropagation(output_grid)
        lens = IdealThinLens(grid=output_grid, focal_length=1.0e-3)
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=input_grid)
        assembly.include(propagation, name="propagation")
        assembly.include(lens, name="lens")
        assembly.include(detector, name="detector")
        assembly.connect(source, propagation)
        assembly.connect(propagation, lens)
        assembly.connect(lens, detector)
        assembly.expose(detector, name="intensity")

        assert assembly.check() is None

    def test_real_grid_precheck_restores_meta_modes_after_rejection(
        self,
    ) -> None:
        """
        真实网格解析失败后不泄漏或破坏后续 meta 推导模式
        """
        grid = _grid()
        source = _plane_wave(spectrum=_spectrum())
        rejected = _RejectedGridPropagation()
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(rejected, name="rejected")
        assembly.include(detector, name="detector")
        assembly.connect(source, rejected)
        assembly.connect(rejected, detector)
        assembly.expose(detector, name="intensity")

        with pytest.raises(
            AssemblyError,
            match="rejected_grid_for_mode_restoration",
        ):
            assembly.check()

        valid, _detector = _linear_assembly(grid=grid)
        assert valid.check() is None
        assert torch.ones(1).device.type == "cpu"

    def test_real_grid_precheck_is_thread_isolated(self) -> None:
        """
        并发汇编检查各自恢复 PyTorch mode 栈且互不污染
        """

        def _check_once(_ordinal: int) -> None:
            assembly, _detector = _linear_assembly()
            assert assembly.check() is None

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(_check_once, range(4)))

        assert results == (None, None, None, None)

    def test_real_grid_precheck_rejects_non_scalar_allocation(self) -> None:
        """
        输出网格解析只可计算单元素实际元数据，不可借机分配数组
        """
        grid = _grid()
        source = _plane_wave(spectrum=_spectrum())
        propagation = _OversizedGridMetadataPropagation()
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(propagation, name="propagation")
        assembly.include(detector, name="detector")
        assembly.connect(source, propagation)
        assembly.connect(propagation, detector)
        assembly.expose(detector, name="intensity")

        probe = _RealFactoryBodyProbe()
        with probe:
            with pytest.raises(
                AssemblyError,
                match="meta_sandbox_grid_metadata_too_large",
            ):
                assembly.check()

        assert probe.real_ones_calls == 0

    def test_real_grid_precheck_rejects_expansion_before_execution(
        self,
    ) -> None:
        """
        输出网格解析在真实 expand 算子执行前拒绝数组视图
        """
        grid = _grid()
        source = _plane_wave(spectrum=_spectrum())
        propagation = _ExpandedGridMetadataPropagation()
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(propagation, name="propagation")
        assembly.include(detector, name="detector")
        assembly.connect(source, propagation)
        assembly.connect(propagation, detector)
        assembly.expose(detector, name="intensity")

        probe = _RealFactoryBodyProbe()
        with probe:
            with pytest.raises(
                AssemblyError,
                match="meta_sandbox_grid_metadata_too_large",
            ):
                assembly.check()

        assert probe.real_expand_calls == 0

    def test_real_grid_precheck_rejects_array_payload_before_factory(
        self,
    ) -> None:
        """
        输出网格解析在 as_tensor 消费多元素 array-like 前拒绝载荷
        """
        grid = _grid()
        source = _plane_wave(spectrum=_spectrum())
        propagation = _ArrayPayloadGridMetadataPropagation()
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(propagation, name="propagation")
        assembly.include(detector, name="detector")
        assembly.connect(source, propagation)
        assembly.connect(propagation, detector)
        assembly.expose(detector, name="intensity")

        with pytest.raises(
            AssemblyError,
            match="meta_sandbox_grid_metadata_too_large:factory_payload",
        ):
            assembly.check()

    def test_valid_linear_assembly_returns_none(self) -> None:
        """合法线性拓扑：source → elements → detect，check 返回 None
        """
        assembly, _ = _linear_assembly()
        assert assembly.check() is None

    def test_check_reports_cycle_assembly_error(self) -> None:
        """
        含环私有事实（A → B → A）⇒ 一个 ``AssemblyError`` 含环稳定身份

        原子作者 connect 现在使环无法经公共文法产生：闭合并必然重用一个已被占用
        的目标输入端口，故在 connect 即被占用守卫拒绝（见
        ``test_assembly_connect_atomic``）。此处直接向私有 _connections 注入回边，
        模拟复制/还原/篡改事实，以证明全拓扑 check 仍把环作为防御性回扫权威拒绝。
        """
        grid = _grid()
        assembly = Assembly()
        source = _plane_wave(spectrum=_spectrum())
        lens_a = IdealThinLens(grid=grid, focal_length=1.0e-3)
        lens_b = IdealThinLens(grid=grid, focal_length=2.0e-3)
        assembly.include(source, name="source", grid=grid)
        assembly.include(lens_a, name="lens_a")
        assembly.include(lens_b, name="lens_b")
        assembly.connect(source, lens_a)
        assembly.connect(lens_a, lens_b)
        assembly.expose(lens_b, name="output")
        # 绕过公共 connect 直接注入回边 lens_b → lens_a，形成环（A → B → A）
        assembly._connections.append(  # noqa: SLF001
            _Connection(
                source_name="lens_b",
                source_port=None,
                destination_name="lens_a",
                destination_port=None,
            )
        )
        with pytest.raises(AssemblyError) as exception:
            assembly.check()
        message = str(exception.value)
        assert "assembly_topology_cycle" in message

    def test_check_reports_multiple_defects_in_physical_order(self) -> None:
        """含 ≥2 个兼容性缺陷的拓扑 ⇒ 一个 AssemblyError 按物理读序列出全部缺陷
        """
        grid = _grid()
        # 分支 1（物理读序在前）：相干组合两路光谱不一致 ⇒ frequency_mismatch
        spectrum_short = Spectrum.monochromatic(wavelength=1.0e-6)
        spectrum_long = Spectrum.monochromatic(wavelength=2.0e-6)
        source_x1 = _plane_wave(spectrum=spectrum_short)
        source_x2 = _plane_wave(spectrum=spectrum_long)
        bad_spectrum_recombiner = CoherentCombination()

        # 分支 2（物理读序在后）：相干组合两路偏振不一致 ⇒ polarization_mismatch
        source_y1 = _plane_wave(
            spectrum=spectrum_short,
            polarization=Polarization.scalar(),
        )
        source_y2 = _plane_wave(
            spectrum=spectrum_short,
            polarization=Polarization.transverse(),
        )
        bad_polarization_recombiner = CoherentCombination()

        assembly = Assembly()
        # 按物理读序注册：分支 1 优先
        assembly.include(source_x1, name="source_x1", grid=grid)
        assembly.include(source_x2, name="source_x2", grid=grid)
        assembly.include(bad_spectrum_recombiner, name="bad_spectrum_recombiner")
        assembly.include(source_y1, name="source_y1", grid=grid)
        assembly.include(source_y2, name="source_y2", grid=grid)
        assembly.include(
            bad_polarization_recombiner,
            name="bad_polarization_recombiner",
        )
        # 分支 1：两路进入同一相干组合（destination_port a/b）
        assembly.connect(
            source_x1,
            bad_spectrum_recombiner,
            destination_port="field_1",
        )
        assembly.connect(
            source_x2,
            bad_spectrum_recombiner,
            destination_port="field_2",
        )
        # 分支 2：两路进入同一相干组合（destination_port a/b）
        assembly.connect(
            source_y1,
            bad_polarization_recombiner,
            destination_port="field_1",
        )
        assembly.connect(
            source_y2,
            bad_polarization_recombiner,
            destination_port="field_2",
        )
        assembly.expose(bad_spectrum_recombiner, name="output_spectrum")
        assembly.expose(bad_polarization_recombiner, name="output_polarization")

        with pytest.raises(AssemblyError) as exception:
            assembly.check()
        message = str(exception.value)
        # 两个缺陷均出现
        assert "coherent_combination_frequency_mismatch" in message
        assert "coherent_combination_polarization_mismatch" in message
        # 物理读序：frequency_mismatch（分支 1）先于 polarization_mismatch（分支 2）
        frequency_index = message.find("coherent_combination_frequency_mismatch")
        polarization_index = message.find("coherent_combination_polarization_mismatch")
        assert 0 <= frequency_index < polarization_index

    def test_check_compares_polarization_representation_not_source_state(
        self,
    ) -> None:
        """
        同属横向表示的 Jones 状态不制造偏振不兼容，独立谱系仍被拒绝
        """

        grid = _grid()
        source_x = _plane_wave(
            spectrum=_spectrum(),
            polarization=Polarization.linear_x(),
        )
        source_y = _plane_wave(
            spectrum=_spectrum(),
            polarization=Polarization.linear_y(),
        )
        recombiner = CoherentCombination()
        assembly = Assembly()
        assembly.include(source_x, name="source_x", grid=grid)
        assembly.include(source_y, name="source_y", grid=grid)
        assembly.include(recombiner, name="recombiner")
        assembly.connect(source_x, recombiner, destination_port="field_1")
        assembly.connect(source_y, recombiner, destination_port="field_2")
        assembly.expose(recombiner, name="output")

        with pytest.raises(
            AssemblyError,
            match="coherent_combination_source_lineage_mismatch",
        ) as rejected:
            assembly.check()
        assert "polarization_mismatch" not in rejected.value.identity

    def test_check_aggregates_into_single_assembly_error(self) -> None:
        """多缺陷拓扑仅抛一个 AssemblyError（不是多次抛出）
        """
        grid = _grid()
        spectrum_a = Spectrum.monochromatic(wavelength=1.0e-6)
        spectrum_b = Spectrum.monochromatic(wavelength=2.0e-6)
        source_a = _plane_wave(spectrum=spectrum_a)
        source_b = _plane_wave(spectrum=spectrum_b)
        recombiner = CoherentCombination()
        assembly = Assembly()
        assembly.include(source_a, name="source_a", grid=grid)
        assembly.include(source_b, name="source_b", grid=grid)
        assembly.include(recombiner, name="recombiner")
        assembly.connect(source_a, recombiner, destination_port="field_1")
        assembly.connect(source_b, recombiner, destination_port="field_2")
        assembly.expose(recombiner, name="output")
        # 不在循环内逐次抛出；单次抛出一个 AssemblyError 即可
        try:
            assembly.check()
        except AssemblyError as error:
            # 一次抛出，消息包含全部缺陷（此处一条 frequency_mismatch）
            assert "coherent_combination_frequency_mismatch" in str(error)
        else:
            pytest.fail("check() should have raised AssemblyError")

class TestFreeze:
    """
    冻结层（freeze）：先 check 再锁定，子模块张量仍可发现
    """

    def test_freeze_runs_check_and_locks_authoring(self) -> None:
        """freeze() 先运行 check（合法拓扑 ⇒ 通过），再锁定全部作者动作
        """
        assembly, detector = _linear_assembly()
        assembly.freeze()
        # 三个作者动作均被拒绝
        with pytest.raises(AssemblyError):
            assembly.include(_plane_wave(spectrum=_spectrum()), name="late")
        with pytest.raises(AssemblyError):
            assembly.connect(
                detector,
                detector,
            )
        with pytest.raises(AssemblyError):
            assembly.expose(
                detector,
                name="late",
            )

    def test_freeze_propagates_check_failure(self) -> None:
        """含缺陷拓扑：freeze() 透传 check() 的 AssemblyError
        """
        grid = _grid()
        assembly = Assembly()
        source_a = _plane_wave(spectrum=Spectrum.monochromatic(wavelength=1.0e-6))
        source_b = _plane_wave(spectrum=Spectrum.monochromatic(wavelength=2.0e-6))
        recombiner = CoherentCombination()
        assembly.include(source_a, name="source_a", grid=grid)
        assembly.include(source_b, name="source_b", grid=grid)
        assembly.include(recombiner, name="recombiner")
        assembly.connect(source_a, recombiner, destination_port="field_1")
        assembly.connect(source_b, recombiner, destination_port="field_2")
        assembly.expose(recombiner, name="output")
        with pytest.raises(AssemblyError):
            assembly.freeze()
        # check 失败 ⇒ 未进入冻结态，作者动作仍许可
        assembly.include(IntensityDetection(), name="extra")
        assert isinstance(
            dict(assembly.named_modules())["extra"],
            IntensityDetection,
        )

    def test_freeze_rejects_an_assembly_without_an_exposed_output(
        self,
    ) -> None:
        """
        没有作者暴露输出的光路不能冻结为可执行结构
        """

        assembly = Assembly()
        assembly.include(
            _plane_wave(spectrum=_spectrum()),
            name="source",
            grid=_grid(),
        )

        with pytest.raises(
            AssemblyError,
            match="assembly_output_not_exposed",
        ):
            assembly.freeze()

    def test_check_names_every_missing_input_before_meta_execution(
        self,
    ) -> None:
        """
        缺失连接以组件名和端口名一次性报告，而不是退化为下游 forward 失败
        """

        source = _plane_wave(spectrum=_spectrum())
        recombiner = CoherentCombination()
        assembly = Assembly()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(recombiner, name="recombiner")
        assembly.connect(
            source,
            recombiner,
            destination_port="field_1",
        )
        assembly.expose(
            recombiner,
            name="output",
        )

        with pytest.raises(AssemblyError) as information:
            assembly.check()

        message = str(information.value)
        assert "assembly_input_missing:recombiner:field_2" in message
        assert "assembly_combination_forward_failed" not in message

    def test_frozen_assembly_copies_rebuild_component_relationships(
        self,
    ) -> None:
        """
        深复制后的冻结 Assembly 由稳定组件名重建当前实例关系并可重新托管运行
        """

        original, _detector = _linear_assembly()
        original.freeze()
        copied = copy.deepcopy(original)
        baseline_workstation = Workstation.cpu()
        baseline_workstation.host(original)
        baseline_outputs, _baseline_record = baseline_workstation.run(
            original
        )
        workstation = Workstation.cpu()
        workstation.host(copied)

        outputs, _record = workstation.run(copied)

        assert tuple(outputs) == ("intensity",)
        copied_intensity = outputs["intensity"]
        assert isinstance(copied_intensity, Intensity)
        baseline = baseline_outputs["intensity"]
        assert isinstance(baseline, Intensity)
        assert torch.equal(copied_intensity.values, baseline.values)

    def test_frozen_assembly_serialization_rebuilds_component_relationships(
        self,
    ) -> None:
        """
        同版本 torch.save 往返后的冻结 Assembly 无需身份缓存修补即可重新托管运行
        """

        original, _detector = _linear_assembly()
        original.freeze()
        stream = io.BytesIO()
        torch.save(original, stream)
        stream.seek(0)
        restored = torch.load(stream, weights_only=False)
        assert isinstance(restored, Assembly)
        baseline_workstation = Workstation.cpu()
        baseline_workstation.host(original)
        baseline_outputs, _baseline_record = baseline_workstation.run(
            original
        )
        workstation = Workstation.cpu()
        workstation.host(restored)

        outputs, _record = workstation.run(restored)

        assert tuple(outputs) == ("intensity",)
        restored_intensity = outputs["intensity"]
        assert isinstance(restored_intensity, Intensity)
        baseline = baseline_outputs["intensity"]
        assert isinstance(baseline, Intensity)
        assert torch.equal(restored_intensity.values, baseline.values)

    def test_parameters_and_buffers_remain_discoverable_across_freeze(
        self,
    ) -> None:
        """冻结后 named_parameters/named_buffers 仍揭示被纳入元件的可训练/固定张量
        """
        grid = _grid()
        spectrum = _spectrum()
        source = _plane_wave(spectrum=spectrum, relative_amplitude=1.0)
        # 焦距以可训练 Parameter 给出，便于在 named_parameters 中验证身份保留
        focal_length = torch.nn.Parameter(torch.tensor(1.5e-3, dtype=torch.float64))
        lens = IdealThinLens(grid=grid, focal_length=focal_length)
        detector = IntensityDetection()

        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(lens, name="lens")
        assembly.include(detector, name="detector")
        assembly.connect(source, lens)
        assembly.connect(lens, detector)
        assembly.expose(detector, name="intensity")

        authored_parameters = dict(assembly.named_parameters())
        assert authored_parameters["lens.focal_length"] is focal_length
        assembly.freeze()

        parameter_names = dict(assembly.named_parameters())
        # 透镜焦距以 "lens.focal_length" 路径出现，且身份保留（同一 Parameter 对象）
        assert "lens.focal_length" in parameter_names
        assert parameter_names["lens.focal_length"] is focal_length

        buffer_names = dict(assembly.named_buffers())
        # 透镜中心、源方向余弦等固定 Buffer 同样可发现
        assert "lens.lens_center_y" in buffer_names
        assert "lens.lens_center_x" in buffer_names
        assert "source.direction_cosine_y" in buffer_names

    def test_source_anchor_participates_in_module_state_lifecycle(self) -> None:
        """
        每个源的采样锚可发现、可迁移，并由源锚注册状态重建
        """
        spacing_y = torch.nn.Parameter(
            torch.tensor(0.5e-6, dtype=torch.float64),
        )
        grid = SpatialGrid.centered(
            sample_counts=(6, 6),
            sample_spacing=(
                spacing_y,
                torch.tensor(0.5e-6, dtype=torch.float64),
            ),
        )
        source = _plane_wave(spectrum=_spectrum())
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)

        # 可训练采样间距作为源锚 Parameter 保持身份注册，对优化器只出现一次
        assert any(parameter is spacing_y for parameter in assembly.parameters())

        assembly.to(device="meta")

        anchor_parameters = dict(assembly.named_parameters())
        anchor_buffers = dict(assembly.named_buffers())
        assert (
            anchor_parameters["_anchor_source.sample_spacing_y"].device.type
            == "meta"
        )
        assert (
            anchor_buffers["_anchor_source.sample_spacing_x"].device.type
            == "meta"
        )

    def test_check_rejects_real_grid_mismatch_before_meta_inference(
        self,
    ) -> None:
        """
        仅连续坐标值不同的元件网格也在 Assembly.check 中被拒绝
        """
        assembly_grid = _grid()
        element_grid = SpatialGrid.centered(
            sample_counts=assembly_grid.sample_counts,
            sample_spacing=(0.75e-6, 0.5e-6),
            orientation=assembly_grid.orientation,
        )
        source = _plane_wave(spectrum=_spectrum())
        lens = IdealThinLens(grid=element_grid, focal_length=1.0e-3)
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=assembly_grid)
        assembly.include(lens, name="lens")
        assembly.include(detector, name="detector")
        assembly.connect(source, lens)
        assembly.connect(lens, detector)
        assembly.expose(detector, name="intensity")

        with pytest.raises(
            AssemblyError,
            match="assembly_element_forward_failed:lens:"
            "ideal_thin_lens_grid_mismatch",
        ):
            assembly.check()

class _PortOrderProbe(torch.nn.Module):

    @property
    def role(self) -> Literal["combination"]:
        """
        返回测试探针的不可变组合角色
        """

        return "combination"

    @property
    def input_ports(self) -> tuple[str, str]:
        """
        返回测试探针固定输入端口顺序
        """

        return ("input_1", "input_2")

    def __init__(self) -> None:
        """
        构造含接收记录列表的最小测试探针元件
        """
        super().__init__()
        self.received: list[OpticalField] = []
        self.nested_state = {"visits": []}
        self.scale = torch.nn.Parameter(torch.tensor(1.0))
        self.register_buffer(
            "_derived_cache",
            None,
            persistent=False,
        )

    def forward(  # type: ignore[override]
        self,
        field_a: OpticalField,
        field_b: OpticalField,
    ) -> OpticalField:
        """
        记录接收顺序并返回第一输入光场作为单输出（供下游暴露走查）
        """
        assert (
            field_a.spectrum.wavelengths[0]
            < field_b.spectrum.wavelengths[0]
        )
        self.received.extend((field_a, field_b))
        self.nested_state["visits"].append(field_a.envelope)
        self._buffers["_derived_cache"] = torch.ones_like(field_a.envelope)
        return field_a

class _RealAllocatingSource(torch.nn.Module):
    @property
    def role(self) -> Literal["source"]:
        """
        声明光源角色
        """
        return "source"

    def forward(self, grid: SpatialGrid) -> OpticalField:
        """
        刻意请求 CPU 张量，以证明 meta 沙箱在分配前拒绝设备逃逸
        """
        return OpticalField(
            envelope=torch.ones(
                (1, 1, *grid.sample_counts),
                dtype=torch.complex64,
                device="cpu",
            ),
            grid=grid,
            spectrum=_spectrum(),
            polarization_representation=(Polarization.scalar()).representation,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )

class _RepairableRealAllocatingSource(_RealAllocatingSource):
    def __init__(self) -> None:
        """
        构造可在失败后切回合法 transverse Plane Wave 的测试 Source
        """
        super().__init__()
        self.request_real_tensor = True
        self.valid_source = _plane_wave(
            spectrum=_spectrum(),
            polarization=Polarization.linear_x(),
        )

    def forward(self, grid: SpatialGrid) -> OpticalField:
        """
        依测试开关请求非法真实张量或执行合法 Source
        """
        if self.request_real_tensor:
            return super().forward(grid)
        return self.valid_source(grid)

class _MutatingElement(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造刻意尝试原位修改固定状态的测试元件
        """
        super().__init__()
        self.register_buffer("scale", torch.tensor(1.0))

    @property
    def role(self) -> Literal["element"]:
        """
        声明元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        尝试修改沙箱共享的只读注册状态
        """
        scale = self.get_buffer("scale")
        assert scale is not None
        scale.add_(1.0)
        return field

class _RegisteredStateCloningElement(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造带大块固定 Buffer 的测试元件
        """
        super().__init__()
        self.register_buffer("fixed_map", torch.ones((1024, 1024)))

    @property
    def role(self) -> Literal["element"]:
        """
        声明元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        从固定 Buffer 派生同形张量并确认它仍在 meta
        """
        fixed_map = self.get_buffer("fixed_map")
        assert fixed_map is not None
        derived = torch.empty_like(fixed_map)
        assert derived.is_meta
        return field

class _RebindingElement(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造尝试重绑固定 Buffer 存储的测试元件
        """
        super().__init__()
        self.register_buffer("scale", torch.tensor(1.0))

    @property
    def role(self) -> Literal["element"]:
        """
        声明元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        绕过原位算子并重绑固定 Buffer 的底层存储
        """
        scale = self.get_buffer("scale")
        assert scale is not None
        scale.data = scale.detach().clone()
        return field

class _UncopyableElement(torch.nn.Module):
    def __init__(self) -> None:
        """
        构造无法进入隔离沙箱的测试元件
        """
        super().__init__()
        self.runtime_resource = _UncopyableResource()

    @property
    def role(self) -> Literal["element"]:
        """
        声明元件角色
        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        原样返回输入光场
        """
        return field

class _UncopyableResource:
    def __deepcopy__(self, memo: dict[int, object]) -> _UncopyableResource:
        """
        模拟线程锁等不能复制的运行期资源
        """
        del memo
        error_identity = "uncopyable_runtime_resource"
        raise TypeError(error_identity)

def test_check_rejects_forward_that_requests_a_real_tensor() -> None:
    """
    meta 检查拒绝显式真实设备输出，不把它悄悄当作有效推导结果
    """
    source = _RealAllocatingSource()
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.expose(source, name="field")

    with pytest.raises(
        AssemblyError,
        match="meta_sandbox_real_tensor_forbidden",
    ):
        assembly.check()

def test_mixed_directional_check_and_freeze_reject_meta_escape_atomically(
) -> None:
    """
    Wave Encounter 不得绕过 Source 的隔离 Meta 检查，失败后可修正并执行
    """
    source = _RepairableRealAllocatingSource()
    cube = IdealNonpolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=0.37,
    )
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include_directional(cube, name="cube")
    encounter = assembly.wave_encounter(
        cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    assembly.connect(
        source,
        encounter,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.expose(
        encounter,
        name="right_field",
        source_terminal=CubeTerminal.RIGHT,
    )
    assembly.end_route(
        encounter,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )
    authored_facts = (
        assembly._encounters,  # noqa: SLF001
        assembly._plan_connections,  # noqa: SLF001
        assembly._directional_exposures,  # noqa: SLF001
        assembly._route_ends,  # noqa: SLF001
    )
    expected_identity = (
        "assembly_source_forward_failed:source:"
        "meta_sandbox_real_tensor_forbidden:cpu"
    )

    with pytest.raises(AssemblyError) as check_failure:
        assembly.check()
    with pytest.raises(AssemblyError) as freeze_failure:
        assembly.freeze()

    assert check_failure.value.identity == expected_identity
    assert freeze_failure.value.identity == expected_identity
    assert not assembly.is_frozen
    assert assembly._frozen_facts is None  # noqa: SLF001
    assert (
        assembly._encounters,  # noqa: SLF001
        assembly._plan_connections,  # noqa: SLF001
        assembly._directional_exposures,  # noqa: SLF001
        assembly._route_ends,  # noqa: SLF001
    ) == authored_facts

    source.request_real_tensor = False
    assert assembly.check() is None
    assembly.freeze()
    workstation = Workstation.cpu()
    workstation.host(assembly)
    try:
        outputs, _record = workstation.run(assembly)
        field = outputs["right_field"]
        assert isinstance(field, OpticalField)
        assert field.envelope.dtype is torch.complex128
        assert field.envelope.device.type == "cpu"
    finally:
        workstation.release(assembly)

def test_check_rejects_registered_state_mutation_without_leaking_it() -> None:
    """
    非源注册状态在沙箱中只读，原位写入于执行前拒绝且原对象保持不变
    """
    source = _plane_wave(spectrum=_spectrum())
    element = _MutatingElement()
    scale = element.get_buffer("scale")
    assert scale is not None
    original_value = scale.detach().clone()
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include(element, name="element")
    assembly.connect(source, element)
    assembly.expose(element, name="field")

    with pytest.raises(
        AssemblyError,
        match="meta_sandbox_registered_state_modified",
    ):
        assembly.check()

    assert element.get_buffer("scale") is scale
    assert torch.equal(scale, original_value)

def test_check_projects_registered_state_before_derived_allocation() -> None:
    """
    固定注册张量先投影到 meta，like 工厂不会分配真实大张量
    """
    source = _plane_wave(spectrum=_spectrum())
    element = _RegisteredStateCloningElement()
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include(element, name="element")
    assembly.connect(source, element)
    assembly.expose(element, name="field")

    assert assembly.check() is None

def test_check_rejects_registered_storage_rebinding_without_leak() -> None:
    """
    沙箱拒绝固定 Buffer 存储重绑且原组件身份和值保持不变
    """
    source = _plane_wave(spectrum=_spectrum())
    element = _RebindingElement()
    scale = element.get_buffer("scale")
    assert scale is not None
    original_value = scale.detach().clone()
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include(element, name="element")
    assembly.connect(source, element)
    assembly.expose(element, name="field")

    with pytest.raises(
        AssemblyError,
        match="meta_sandbox_registered_state_modified",
    ):
        assembly.check()

    assert element.get_buffer("scale") is scale
    assert torch.equal(scale, original_value)

def test_check_maps_uncopyable_component_state_to_assembly_error() -> None:
    """
    不可隔离的运行期资源以稳定 AssemblyError 拒绝而不泄漏 TypeError
    """
    source = _plane_wave(spectrum=_spectrum())
    element = _UncopyableElement()
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include(element, name="element")
    assembly.connect(source, element)
    assembly.expose(element, name="field")

    with pytest.raises(
        AssemblyError,
        match="meta_sandbox_copy_failed:TypeError",
    ):
        assembly.check()

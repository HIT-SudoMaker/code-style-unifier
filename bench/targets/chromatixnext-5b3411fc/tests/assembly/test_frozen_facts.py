from __future__ import annotations

import copy
import io

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
from chromatix_next.optics._assembly_facts import _FrozenAssembly
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import IdealThinLens, ReflectAt
from chromatix_next.optics.propagation import TraceTo
from chromatix_next.optics.source import CollimatedRaySource, PlaneWave
from chromatix_next.optics.surface import Plane
from chromatix_next.workstation import NamedOutputs, Workstation


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

def _plane_wave(relative_amplitude: float | torch.nn.Parameter = 1.0) -> PlaneWave:
    # 沿法线传播的标量偏振平面波源
    return PlaneWave(
        spectrum=_spectrum(),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=relative_amplitude,
    )

def _collimated_ray_source(
    *,
    ray_power: float | torch.nn.Parameter = 1.0,
) -> CollimatedRaySource:
    # 沿 +z 方向的准直光线源
    return CollimatedRaySource(
        spectrum=_spectrum(),

        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        ray_power=ray_power,
    )

def _ray_trace_plane() -> TraceTo:
    # 命中 +z 前方平面的光线传播动作
    return TraceTo(
        surface=Plane(
            origin=(0.0, 0.0, 5.0e-6),
            clear_aperture_radius=5.0e-6,
        ),
    )

def _ray_reflect_at_origin() -> ReflectAt:
    # 在原点平面上的反射动作（顺序光线链的第二步）
    return ReflectAt(
        surface=Plane(origin=(0.0, 0.0, 0.0)),
    )

def _mixed_independent_assembly() -> Assembly:
    assembly = Assembly()
    wave_source = _plane_wave()
    wave_detector = IntensityDetection()
    ray_source = _collimated_ray_source()
    ray_trace = _ray_trace_plane()
    assembly.include(wave_source, name="wave_source", grid=_grid())
    assembly.include(wave_detector, name="wave_detector")
    assembly.include(ray_source, name="ray_source", grid=_grid())
    assembly.include(ray_trace, name="ray_trace")
    assembly.connect(wave_source, wave_detector)
    assembly.connect(ray_source, ray_trace)
    assembly.expose(wave_detector, name="wave_intensity")
    assembly.expose(ray_trace, name="ray_bundle")
    return assembly

class TestFrozenFactOwnership:
    """
    冻结、检查、复制与重放保持单一冻结事实所有权
    """

    def test_check_copy_and_replay_preserve_one_frozen_fact_per_assembly(
        self,
    ) -> None:
        """检查、复制与重复重放均不替换各自装配的冻结事实
        """

        assembly = _mixed_independent_assembly()
        assembly.freeze()
        frozen_facts = assembly._frozen_facts  # noqa: SLF001
        assert isinstance(frozen_facts, _FrozenAssembly)
        # 真实重放入口取到的是同一份冻结事实实例，不是等值副本
        assert assembly._execution_facts() is frozen_facts  # noqa: SLF001
        assembly.check()
        assert assembly._frozen_facts is frozen_facts  # noqa: SLF001
        workstation = Workstation.cpu()
        workstation.host(assembly)
        for _ in range(2):
            outputs, _record = workstation.run(assembly)
            assert tuple(outputs) == ("wave_intensity", "ray_bundle")
            assert assembly._frozen_facts is frozen_facts  # noqa: SLF001

    def test_deepcopy_owns_an_equal_independent_frozen_fact(self) -> None:
        """
        深拷贝独立持有等值冻结事实并可公开重放
        """

        assembly = _mixed_independent_assembly()
        assembly.freeze()
        copied = copy.deepcopy(assembly)
        copied_facts = copied._frozen_facts  # noqa: SLF001
        assert isinstance(copied_facts, _FrozenAssembly)
        assert copied_facts is not assembly._frozen_facts  # noqa: SLF001
        assert copied_facts == assembly._frozen_facts  # noqa: SLF001
        copied_workstation = Workstation.cpu()
        copied_workstation.host(copied)
        outputs, _record = copied_workstation.run(copied)
        assert tuple(outputs) == ("wave_intensity", "ray_bundle")
        assert copied._frozen_facts is copied_facts  # noqa: SLF001

requires_cuda = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="No CUDA-capable PyTorch runtime on this host.",
)

def _intensity_values(outputs: NamedOutputs, name: str) -> torch.Tensor:
    # 读取命名强度并在公共联合类型边界显式收窄，返回其底层的光强张量
    value = outputs[name]
    assert isinstance(value, Intensity)
    return value.values

class TestSharedParameterIdentity:
    """
    共享 Parameter 在多个被纳入组件中保持同一身份、对优化器只出现一次、
    累积全部合法梯度路径
    """

    def test_shared_parameter_appears_once_to_optimizer(self) -> None:
        """同一 Parameter 被两个被纳入源复用时，去重后对优化器只出现一次
        """
        shared = torch.nn.Parameter(torch.tensor(2.0, dtype=torch.float64))
        grid = _grid()
        source_a = _plane_wave(relative_amplitude=shared)
        source_b = _plane_wave(relative_amplitude=shared)
        detector_a = IntensityDetection()
        detector_b = IntensityDetection()
        assembly = Assembly()
        assembly.include(source_a, name="source_a", grid=grid)
        assembly.include(source_b, name="source_b", grid=grid)
        assembly.include(detector_a, name="detector_a")
        assembly.include(detector_b, name="detector_b")
        assembly.connect(source_a, detector_a)
        assembly.connect(source_b, detector_b)
        assembly.expose(detector_a, name="intensity_a")
        assembly.expose(detector_b, name="intensity_b")

        dedup_matches = [
            name
            for name, value in dict(
                assembly.named_parameters(remove_duplicate=True),
            ).items()
            if value is shared
        ]
        full_matches = [
            name
            for name, value in dict(
                assembly.named_parameters(remove_duplicate=False),
            ).items()
            if value is shared
        ]
        # 去重视图：同一 Parameter 只对优化器出现一次
        assert len(dedup_matches) == 1
        # 不去重视图：它在两个源下都暴露，证明两条梯度路径共载同一份 Parameter
        assert sorted(full_matches) == [
            "source_a.relative_amplitude",
            "source_b.relative_amplitude",
        ]

    def test_shared_parameter_accumulates_gradient_from_all_paths(
        self,
    ) -> None:
        """两个独立子图共享同一 Parameter 时，反向后两路径梯度都累加进同一份
        """
        # 单路径参考：捕获同一 Parameter 在单子图下的梯度
        single_amplitude = torch.nn.Parameter(
            torch.tensor(2.0, dtype=torch.float64),
        )
        single_assembly = Assembly()
        single_source = _plane_wave(relative_amplitude=single_amplitude)
        single_detector = IntensityDetection()
        single_assembly.include(single_source, name="source", grid=_grid())
        single_assembly.include(single_detector, name="detector")
        single_assembly.connect(single_source, single_detector)
        single_assembly.expose(single_detector, name="intensity")
        single_assembly.freeze()
        single_workstation = Workstation.cpu()
        single_workstation.host(single_assembly)
        single_outputs, _ = single_workstation.run(single_assembly)
        _intensity_values(single_outputs, "intensity").sum().backward()
        assert single_amplitude.grad is not None
        single_grad = single_amplitude.grad.detach().clone()

        # 双路径共享：两个独立子图复用同一 Parameter
        shared_amplitude = torch.nn.Parameter(
            torch.tensor(2.0, dtype=torch.float64),
        )
        shared_assembly = Assembly()
        source_a = _plane_wave(relative_amplitude=shared_amplitude)
        source_b = _plane_wave(relative_amplitude=shared_amplitude)
        detector_a = IntensityDetection()
        detector_b = IntensityDetection()
        shared_assembly.include(source_a, name="source_a", grid=_grid())
        shared_assembly.include(source_b, name="source_b", grid=_grid())
        shared_assembly.include(detector_a, name="detector_a")
        shared_assembly.include(detector_b, name="detector_b")
        shared_assembly.connect(source_a, detector_a)
        shared_assembly.connect(source_b, detector_b)
        shared_assembly.expose(detector_a, name="intensity_a")
        shared_assembly.expose(detector_b, name="intensity_b")
        shared_assembly.freeze()
        shared_workstation = Workstation.cpu()
        shared_workstation.host(shared_assembly)
        shared_outputs, _ = shared_workstation.run(shared_assembly)
        (
            _intensity_values(shared_outputs, "intensity_a").sum()
            + _intensity_values(shared_outputs, "intensity_b").sum()
        ).backward()
        assert shared_amplitude.grad is not None
        shared_grad = shared_amplitude.grad.detach().clone()

        # 共享双路径梯度恰为单路径的两倍——证明两条合法梯度路径共载同一份 Parameter
        assert torch.allclose(shared_grad, 2.0 * single_grad)

class TestSourceAnchorTopologyInvariant:
    """
    源采样锚与已纳入组件的删除均按作者语法守卫拒绝（该作者边界保持单一公共守卫）
    """

    def test_del_included_component_rejected(self) -> None:
        """删除已纳入组件按作者语法拒绝（与赋值守卫对称）
        """
        assembly = Assembly()
        assembly.include(_plane_wave(), name="source", grid=_grid())
        with pytest.raises(
            AssemblyError,
            match="assembly_component_replacement_forbidden:source",
        ):
            del assembly.source

    def test_del_source_anchor_rejected(self) -> None:
        """删除源采样锚以稳定身份拒绝，保护冻结拓扑不变量
        """
        assembly = Assembly()
        assembly.include(_plane_wave(), name="source", grid=_grid())
        with pytest.raises(
            AssemblyError,
            match="assembly_source_anchor_replacement_forbidden:_anchor_source",
        ):
            del assembly._anchor_source  # noqa: SLF001

    def test_del_source_anchor_rejected_after_freeze(self) -> None:
        """冻结后删除源采样锚仍被拒绝
        """
        source = _plane_wave()
        assembly = Assembly()
        assembly.include(source, name="source", grid=_grid())
        assembly.expose(source, name="field")
        assembly.freeze()
        with pytest.raises(
            AssemblyError,
            match="assembly_source_anchor_replacement_forbidden:_anchor_source",
        ):
            del assembly._anchor_source

class TestAliasPreservationAcrossCopy:
    """
    深复制与序列化保住跨组件别名；副本可重新托管运行
    """

    @staticmethod
    def _build_two_lens_assembly_with_shared_focal_length(
        focal_length: torch.nn.Parameter,
    ) -> Assembly:
        # 两条独立的 Wave 链共享焦距 Parameter；每条链把一个源接到一个透镜
        grid = _grid()
        source_a = _plane_wave()
        source_b = _plane_wave()
        lens_a = IdealThinLens(grid=grid, focal_length=focal_length)
        lens_b = IdealThinLens(grid=grid, focal_length=focal_length)
        assembly = Assembly()
        assembly.include(source_a, name="source_a", grid=grid)
        assembly.include(source_b, name="source_b", grid=grid)
        assembly.include(lens_a, name="lens_a")
        assembly.include(lens_b, name="lens_b")
        assembly.connect(source_a, lens_a)
        assembly.connect(source_b, lens_b)
        assembly.expose(lens_a, name="field_a")
        assembly.expose(lens_b, name="field_b")
        assembly.freeze()
        return assembly

    def test_deepcopy_preserves_cross_component_alias(self) -> None:
        """两个透镜共享焦距 Parameter，深复制后副本中两者仍共享同一份
        """
        focal_length = torch.nn.Parameter(
            torch.tensor(1.0e-3, dtype=torch.float64),
        )
        assembly = (
            self._build_two_lens_assembly_with_shared_focal_length(
                focal_length,
            )
        )
        copied = copy.deepcopy(assembly)
        copied_modules = dict(copied.named_modules())
        # 跨组件别名在深复制副本中保留：两个 lens 的 focal_length 是同一对象
        assert (
            copied_modules["lens_a"].focal_length
            is copied_modules["lens_b"].focal_length
        )
        # 副本可由另一工作站重新托管运行（不继承原根所有权）
        workstation = Workstation.cpu()
        workstation.host(copied)
        outputs, _ = workstation.run(copied)
        assert isinstance(outputs["field_a"], OpticalField)
        assert isinstance(outputs["field_b"], OpticalField)

    def test_serialization_preserves_cross_component_alias(self) -> None:
        """两个透镜共享焦距 Parameter，序列化往返后副本仍保住别名
        """
        focal_length = torch.nn.Parameter(
            torch.tensor(1.0e-3, dtype=torch.float64),
        )
        assembly = (
            self._build_two_lens_assembly_with_shared_focal_length(
                focal_length,
            )
        )
        stream = io.BytesIO()
        torch.save(assembly, stream)
        stream.seek(0)
        restored = torch.load(stream, weights_only=False)
        restored_modules = dict(restored.named_modules())
        assert (
            restored_modules["lens_a"].focal_length
            is restored_modules["lens_b"].focal_length
        )
        workstation = Workstation.cpu()
        workstation.host(restored)
        outputs, _ = workstation.run(restored)
        assert isinstance(outputs["field_a"], OpticalField)

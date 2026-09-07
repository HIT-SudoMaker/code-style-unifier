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
from chromatix_next.optics.element import IdealThinLens
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

def _linear_assembly(
    *,
    grid: SpatialGrid | None = None,
    spectrum: Spectrum | None = None,
) -> tuple[Assembly, IntensityDetection]:
    # 构造合法线性装配：单源 → 两个元件 → 探测
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

class TestInclude:
    """
    作者层 1（include）：唯一稳定名 + 子模块注册
    """

    def test_include_registers_component_under_unique_name(self) -> None:
        """include 在唯一稳定名下注册元件，named_modules 据此可发现
        """
        assembly = Assembly()
        source = _plane_wave(spectrum=_spectrum())
        assembly.include(source, name="source", grid=_grid())
        named = dict(assembly.named_modules())
        assert "source" in named
        assert named["source"] is source

    def test_include_duplicate_name_raises_assembly_error(self) -> None:
        """重复稳定名 ⇒ AssemblyError（唯一性在作者期立即失败）
        """
        assembly = Assembly()
        assembly.include(
            _plane_wave(spectrum=_spectrum()),
            name="source",
            grid=_grid(),
        )
        with pytest.raises(AssemblyError) as exception:
            assembly.include(_plane_wave(spectrum=_spectrum()), name="source")
        assert "assembly_include_duplicate_name" in str(exception.value)
        assert "source" in str(exception.value)

    def test_include_after_freeze_raises_assembly_error(self) -> None:
        """冻结后再纳入元件 ⇒ ``AssemblyError``
        """
        assembly, detector = _linear_assembly()
        assembly.freeze()
        with pytest.raises(AssemblyError) as exception:
            assembly.include(_plane_wave(spectrum=_spectrum()), name="late")
        assert "assembly_frozen" in str(exception.value)

    def test_include_rejects_non_module_component(self) -> None:
        """非 nn.Module 主体 ⇒ AssemblyError（装配只接 nn.Module 元件）
        """
        assembly = Assembly()
        with pytest.raises(AssemblyError) as exception:
            assembly.include("not a module", name="bad")  # type: ignore[arg-type]
        assert "assembly_include_component_invalid" in str(exception.value)

    def test_include_rejects_invalid_name(self) -> None:
        """非合法 Python 标识符稳定名 ⇒ AssemblyError
        """
        assembly = Assembly()
        for invalid in ("", "1up", "has space", "with-dash"):
            with pytest.raises(AssemblyError):
                assembly.include(_plane_wave(spectrum=_spectrum()), name=invalid)

    def test_include_rejects_reserved_name_without_polluting_assembly(
        self,
    ) -> None:
        """
        保留名称失败不改变汇编
        """

        assembly = Assembly()
        source = _plane_wave(spectrum=_spectrum())

        with pytest.raises(
            AssemblyError,
            match="assembly_include_name_reserved:is_frozen",
        ):
            assembly.include(source, name="is_frozen")

        assembly.include(source, name="source", grid=_grid())
        assembly.expose(source, name="field")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        outputs, _record = workstation.run(assembly)
        assert isinstance(outputs["field"], OpticalField)

    def test_included_component_cannot_be_replaced_outside_author_grammar(
        self,
    ) -> None:
        """
        已纳入组件不能绕过作者语法替换
        """

        assembly = Assembly()
        source = _plane_wave(spectrum=_spectrum())
        assembly.include(source, name="source", grid=_grid())
        assembly.expose(source, name="field")
        assembly.freeze()

        with pytest.raises(
            AssemblyError,
            match="assembly_component_replacement_forbidden:source",
        ):
            assembly.source = _plane_wave(spectrum=_spectrum())

        workstation = Workstation.cpu()
        workstation.host(assembly)
        outputs, _record = workstation.run(assembly)
        assert isinstance(outputs["field"], OpticalField)

    def test_add_module_cannot_bypass_include(self) -> None:
        """
        PyTorch 注册入口不能绕过 include
        """

        assembly = Assembly()
        source = _plane_wave(spectrum=_spectrum())
        assembly.include(source, name="source", grid=_grid())

        with pytest.raises(
            AssemblyError,
            match="assembly_component_replacement_forbidden:source",
        ):
            assembly.add_module(
                "source",
                _plane_wave(spectrum=_spectrum()),
            )
        with pytest.raises(
            AssemblyError,
            match="assembly_component_registration_forbidden:hidden",
        ):
            assembly.add_module(
                "hidden",
                _plane_wave(spectrum=_spectrum()),
            )

        assert "hidden" not in dict(assembly.named_modules())
        assert dict(assembly.named_modules())["source"] is source

    def test_module_attribute_cannot_bypass_include(self) -> None:
        """
        Module 属性赋值不能绕过 include
        """

        assembly = Assembly()

        with pytest.raises(
            AssemblyError,
            match="assembly_component_registration_forbidden:hidden",
        ):
            assembly.hidden = _plane_wave(spectrum=_spectrum())

        assert "hidden" not in dict(assembly.named_modules())

class TestSourceAnchorSampling:
    """
    每个源自带空间网格采样锚，多源多网格在同一装配内局部共存
    """

    def test_include_source_requires_anchor_in_same_operation(self) -> None:
        """源角色 include 必须在同一作者操作给出 grid，否则以稳定身份拒绝
        """
        assembly = Assembly()
        with pytest.raises(
            AssemblyError,
            match="assembly_include_source_anchor_missing:source",
        ):
            assembly.include(
                _plane_wave(spectrum=_spectrum()),
                name="source",
            )

    def test_include_non_source_rejects_anchor(self) -> None:
        """非源角色 include 带 grid 以稳定身份拒绝（无任何组件可借锚）
        """
        assembly = Assembly()
        with pytest.raises(
            AssemblyError,
            match="assembly_include_non_source_anchor_forbidden:lens",
        ):
            assembly.include(
                IdealThinLens(grid=_grid(), focal_length=1.0e-3),
                name="lens",
                grid=_grid(),
            )

    def test_assembly_has_no_global_or_ambient_grid(self) -> None:
        """汇编不再持有任何 Assembly 级共配准网格属性
        """
        assembly = Assembly()
        assert not hasattr(assembly, "grid")

    def test_fixed_anchor_values_registered_as_buffers(self) -> None:
        """固定采样锚值登记为 Buffer，不出现在 Parameter 集合中
        """
        assembly = Assembly()
        assembly.include(
            _plane_wave(spectrum=_spectrum()),
            name="source",
            grid=_grid(),
        )
        buffers = dict(assembly.named_buffers())
        parameters = dict(assembly.named_parameters())
        assert "_anchor_source.sample_spacing_y" in buffers
        assert "_anchor_source.sample_spacing_x" in buffers
        assert "_anchor_source.sample_spacing_y" not in parameters

    def test_trainable_anchor_accumulates_gradient(self) -> None:
        """可训练采样锚在装配运行反向后累积有限梯度（身份保持、计算图贯通）
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
        source = PlaneWave(
            spectrum=_spectrum(),
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            propagation_direction=PropagationDirection(0.2, 0.1),
            relative_amplitude=1.0,
        )
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        outputs, _record = workstation.run(assembly)
        intensity = outputs["intensity"]
        assert isinstance(intensity, Intensity)
        intensity.values.sum().backward()
        assert spacing_y.grad is not None
        assert torch.isfinite(spacing_y.grad).all()

    def test_two_sources_on_distinct_grids_keep_local_sampling(self) -> None:
        """两个源各自带不同采样锚：运行后各自子图保留源侧采样数，无隐藏重采样
        """
        grid_a = SpatialGrid.centered(
            sample_counts=(6, 6),
            sample_spacing=(0.5e-6, 0.5e-6),
        )
        grid_b = SpatialGrid.centered(
            sample_counts=(8, 8),
            sample_spacing=(0.4e-6, 0.4e-6),
        )
        assembly = Assembly()
        source_a = _plane_wave(spectrum=_spectrum(), relative_amplitude=1.0)
        source_b = _plane_wave(spectrum=_spectrum(), relative_amplitude=1.0)
        detector_a = IntensityDetection()
        detector_b = IntensityDetection()
        assembly.include(source_a, name="source_a", grid=grid_a)
        assembly.include(detector_a, name="detector_a")
        assembly.include(source_b, name="source_b", grid=grid_b)
        assembly.include(detector_b, name="detector_b")
        assembly.connect(source_a, detector_a)
        assembly.connect(source_b, detector_b)
        assembly.expose(detector_a, name="intensity_a")
        assembly.expose(detector_b, name="intensity_b")
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        outputs, _record = workstation.run(assembly)
        # 两子图各自保留源侧采样数，没有被强行重采样到任何公共网格
        intensity_a = outputs["intensity_a"]
        intensity_b = outputs["intensity_b"]
        assert isinstance(intensity_a, Intensity)
        assert isinstance(intensity_b, Intensity)
        assert intensity_a.values.shape == (6, 6)
        assert intensity_b.values.shape == (8, 8)
        assert bool(torch.isfinite(intensity_a.values).all())
        assert bool(torch.isfinite(intensity_b.values).all())

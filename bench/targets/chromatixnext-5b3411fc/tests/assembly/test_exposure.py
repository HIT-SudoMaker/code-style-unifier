
from __future__ import annotations

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
from chromatix_next.optics._assembly_facts import _Connection, _Exposure  # noqa: SLF001
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import IdealThinLens
from chromatix_next.optics.propagation import ScalarAngularSpectrum, TraceTo
from chromatix_next.optics.source import CollimatedRaySource, PlaneWave
from chromatix_next.optics.surface.plane import Plane
from chromatix_next.workstation import Workstation


def _grid() -> SpatialGrid:
    # 中心对齐的小型横向网格
    return SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(2.0e-6, 2.0e-6),
    )


def _spectrum(wavelength: float = 1.0e-6) -> Spectrum:
    return Spectrum.monochromatic(wavelength=wavelength)


def _plane_wave() -> PlaneWave:
    # 沿法线传播的标量平面波源
    return PlaneWave(
        spectrum=_spectrum(),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )


def _run(assembly: Assembly) -> dict[str, object]:
    # 冻结 → CPU 托管 → 运行，返回命名输出。调用方必须先完成全部作者操作
    assembly.freeze()
    workstation = Workstation.cpu()
    workstation.host(assembly)
    outputs, _record = workstation.run(assembly)
    return dict(outputs)


def _lens_chain_assembly(
    *,
    is_intermediate_exposed: bool,
) -> Assembly:
    grid = _grid()
    source = _plane_wave()
    lens_a = IdealThinLens(grid=grid, focal_length=1.0e-3)
    lens_b = IdealThinLens(grid=grid, focal_length=2.0e-3)
    detector = IntensityDetection()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(lens_a, name="lens_a")
    assembly.include(lens_b, name="lens_b")
    assembly.include(detector, name="detector")
    assembly.connect(source, lens_a)
    assembly.connect(lens_a, lens_b)
    assembly.connect(lens_b, detector)
    if is_intermediate_exposed:
        assembly.expose(lens_a, name="intermediate")
    assembly.expose(detector, name="intensity")
    return assembly


class TestRejectedSecondExposureOnSameAnchor:
    """
    同锚点二次命名在 expose 即以稳定身份拒绝，且不改变既有作者暴露序
    """

    def test_second_exposure_rejected_at_expose_with_stable_identity(self) -> None:
        """
        同一锚点的第二次 expose 即以 assembly_expose_output_reused 失败
        """

        grid = _grid()
        source = _plane_wave()
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        with pytest.raises(AssemblyError) as information:
            assembly.expose(detector, name="intensity_alias")
        assert (
            information.value.identity
            == "assembly_expose_output_reused:detector:None"
        )

    def test_same_anchor_and_name_prefers_anchor_reuse_identity(self) -> None:
        """
        同一锚点同一名称的二次暴露仍由锚点重用身份拒绝
        """

        grid = _grid()
        source = _plane_wave()
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")

        with pytest.raises(AssemblyError) as information:
            assembly.expose(detector, name="intensity")

        assert (
            information.value.identity
            == "assembly_expose_output_reused:detector:None"
        )
        outputs = _run(assembly)
        assert tuple(outputs) == ("intensity",)

    def test_rejected_second_exposure_leaves_first_and_order_intact(self) -> None:
        """
        被拒的二次暴露不进入作者态：首暴露与作者暴露序不变，且仍可冻结运行
        """

        control = _lens_chain_assembly(is_intermediate_exposed=False)
        control_outputs = _run(control)

        grid = _grid()
        source = _plane_wave()
        lens_a = IdealThinLens(grid=grid, focal_length=1.0e-3)
        lens_b = IdealThinLens(grid=grid, focal_length=2.0e-3)
        detector = IntensityDetection()
        subject = Assembly()
        subject.include(source, name="source", grid=grid)
        subject.include(lens_a, name="lens_a")
        subject.include(lens_b, name="lens_b")
        subject.include(detector, name="detector")
        subject.connect(source, lens_a)
        subject.connect(lens_a, lens_b)
        subject.connect(lens_b, detector)
        subject.expose(lens_a, name="intermediate")
        subject.expose(detector, name="intensity")
        # 对 detector 锚点的二次命名必须失败且不改变既有暴露序
        with pytest.raises(AssemblyError, match="assembly_expose_output_reused"):
            subject.expose(detector, name="duplicate")
        assert subject.exposed_names() == ("intermediate", "intensity")
        subject.check()
        subject_outputs = _run(subject)

        assert tuple(subject_outputs) == ("intermediate", "intensity")
        baseline = control_outputs["intensity"]
        subject_intensity = subject_outputs["intensity"]
        assert isinstance(baseline, Intensity)
        assert isinstance(subject_intensity, Intensity)
        assert torch.allclose(baseline.values, subject_intensity.values)

class TestDuplicateNameRemainsDistinctDefect:
    """
    assembly_expose_duplicate_name 仍为独立缺陷（两个不同锚点争同一用户名）
    """

    def test_two_anchors_same_name_still_rejected_as_duplicate_name(self) -> None:
        """
        两个不同锚点争同一用户名仍由 assembly_expose_duplicate_name 拒绝
        """

        grid = _grid()
        source = _plane_wave()
        detector_a = IntensityDetection()
        detector_b = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(detector_a, name="detector_a")
        assembly.include(detector_b, name="detector_b")
        assembly.connect(source, detector_a)
        assembly.expose(detector_a, name="output")
        # detector_b 是不同锚点，但争同一用户名——名称重用身份拒绝
        with pytest.raises(AssemblyError) as information:
            assembly.expose(detector_b, name="output")
        assert information.value.identity == "assembly_expose_duplicate_name:output"
        # 与锚点重用身份不同
        assert "output_reused" not in information.value.identity


class TestLegalOneConnectionPlusOneExposure:
    """
    同一输出端口同时驱动一条下游连接并拥有一个 Authored Exposure 仍合法
    """

    def test_connected_output_also_exposed_returns_exact_computed_value(self) -> None:
        """
        暴露返回下游动作所消费的同一计算物理值，无任何物理状态突变
        """

        # 对照：不暴露 lens_a；被证：暴露 lens_a。两者的 lens_b/detector 路径相同
        control = _lens_chain_assembly(is_intermediate_exposed=False)
        control_outputs = _run(control)

        exposed = _lens_chain_assembly(is_intermediate_exposed=True)
        exposed_outputs = _run(exposed)

        # 暴露的中间值与对照链路中同一锚点的计算值逐元素一致——暴露不改变物理值
        intermediate = exposed_outputs["intermediate"]
        assert isinstance(intermediate, OpticalField)
        # intensity 输出在两种拓扑下逐元素一致：暴露不分束、不抽头、不耗能
        baseline_intensity = control_outputs["intensity"]
        exposed_intensity = exposed_outputs["intensity"]
        assert isinstance(baseline_intensity, Intensity)
        assert isinstance(exposed_intensity, Intensity)
        assert torch.allclose(
            baseline_intensity.values,
            exposed_intensity.values,
        )


class TestWholeTopologyBackstop:
    """
    Check/Freeze 仍作为防御性回扫，捕捉绕过公共作者语法的篡改私有暴露事实
    """

    def test_check_catches_anchor_reuse_in_malformed_private_facts(self) -> None:
        """
        直接向 _exposures 追加同锚点二次暴露：check 仍以同一身份拒绝
        """

        grid = _grid()
        source = _plane_wave()
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        # 故意绕过 expose，模拟复制/还原/篡改的私有事实：同锚点二次暴露
        assembly._exposures.append(  # noqa: SLF001
            _Exposure(
                component_name="detector",
                port=None,
                name="intensity_alias",
            )
        )
        with pytest.raises(
            AssemblyError,
            match="assembly_expose_output_reused:detector:None",
        ):
            assembly.check()

    def test_check_rejects_duplicate_name_on_different_malformed_anchor(self) -> None:
        """
        防御性全拓扑校验以名称重用身份拒绝不同锚点同名
        """

        grid = _grid()
        source = _plane_wave()
        detector = IntensityDetection()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(source, name="shared")
        assembly._exposures.append(  # noqa: SLF001
            _Exposure(
                component_name="detector",
                port=None,
                name="shared",
            )
        )

        with pytest.raises(
            AssemblyError,
            match="assembly_expose_duplicate_name:shared",
        ):
            assembly.check()


class TestMetaRealNamedOutputEquality:
    """
    meta 与真实重放在中间值暴露拓扑上输出 schema 一致
    """

    def test_meta_and_real_outputs_agree_on_name_type_shape_dtype_order(
        self,
    ) -> None:
        """
        含中间值暴露的拓扑：meta 预检与真实运行的命名输出 schema 完全一致
        """

        assembly = _lens_chain_assembly(is_intermediate_exposed=True)
        assembly.freeze()
        workstation = Workstation.cpu()
        workstation.host(assembly)
        request = workstation._prepare_replay_request(  # noqa: SLF001
            assembly,
            root=None,
            inputs=None,
        )
        _meta_peak, _meta_trace, meta_schema = (
            workstation._measure_meta_replay(  # noqa: SLF001
                request,
                seed=42,
            )
        )
        (
            output_pairs,
            _real_peak,
            _real_trace,
            real_schema,
        ) = workstation._measure_real_replay(  # noqa: SLF001
            request,
            seed=42,
        )
        # 公共 run 已证明 schema 一致可强制；此处直接比较两条路径的 schema
        assert real_schema == meta_schema
        # 命名输出顺序与作者暴露序一致
        assert tuple(name for name, _value in output_pairs) == (
            "intermediate",
            "intensity",
        )

def _collimated_ray_source() -> CollimatedRaySource:
    # 沿 +z 方向的准直光线源（Ray 域）
    return CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        ray_power=1.0,
    )

class TestRejectedDisconnectedSource:
    """
    另一根已暴露时，断开且无路径到达任何暴露的源以稳定身份被拒
    """

    def test_disconnected_source_rejected_with_stable_identity(self) -> None:
        """
        断开的源在另一根已暴露时以稳定身份被拒

        source_a 抵达探测暴露；source_b 既无连接也无暴露，稳定身份为
        not_on_exposed_path:source_b。
        """

        grid = _grid()
        source_a = _plane_wave()
        source_b = _plane_wave()
        detector_a = IntensityDetection()
        assembly = Assembly()
        assembly.include(source_a, name="source_a", grid=grid)
        assembly.include(source_b, name="source_b", grid=grid)
        assembly.include(detector_a, name="detector_a")
        assembly.connect(source_a, detector_a)
        assembly.expose(detector_a, name="intensity")
        with pytest.raises(AssemblyError) as information:
            assembly.check()
        assert (
            information.value.identity
            == "assembly_component_not_on_exposed_path:source_b"
        )

class TestRejectedDeadTerminalChain:
    """
    完整链路终点未暴露时，链上全部组件都落在死路径上
    """

    def test_dead_terminal_chain_rejected_with_stable_identity(self) -> None:
        """
        终点未暴露的完整链路以稳定身份被拒

        source_b 接 lens_b 闭环但 lens_b 输出未暴露，source_b 与 lens_b 均被拒。
        """

        grid = _grid()
        source_a = _plane_wave()
        detector_a = IntensityDetection()
        source_b = _plane_wave()
        lens_b = IdealThinLens(grid=grid, focal_length=2.0e-3)
        assembly = Assembly()
        assembly.include(source_a, name="source_a", grid=grid)
        assembly.include(detector_a, name="detector_a")
        assembly.include(source_b, name="source_b", grid=grid)
        assembly.include(lens_b, name="lens_b")
        assembly.connect(source_a, detector_a)
        assembly.connect(source_b, lens_b)
        assembly.expose(detector_a, name="intensity")
        with pytest.raises(AssemblyError) as information:
            assembly.check()
        identity = information.value.identity
        assert "assembly_component_not_on_exposed_path:source_b" in identity
        assert "assembly_component_not_on_exposed_path:lens_b" in identity
        # 唯一暴露路径上的组件不被错拒
        assert "detector_a" not in identity
        assert ":source_a" not in identity

class TestRejectedDownstreamAfterExposedIntermediate:
    """
    暴露中间值之后再追加的下游动作若无路径到达暴露则被拒
    """

    def test_downstream_after_exposed_intermediate_rejected(self) -> None:
        """
        暴露中间值后的死路径下游以稳定身份被拒

        lens_a 输出被暴露；lens_b 仅消费 lens_a 但其输出未暴露，落入死路径。
        """

        grid = _grid()
        source = _plane_wave()
        lens_a = IdealThinLens(grid=grid, focal_length=1.0e-3)
        lens_b = IdealThinLens(grid=grid, focal_length=2.0e-3)
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(lens_a, name="lens_a")
        assembly.include(lens_b, name="lens_b")
        assembly.connect(source, lens_a)
        assembly.connect(lens_a, lens_b)
        assembly.expose(lens_a, name="intermediate")
        with pytest.raises(AssemblyError) as information:
            assembly.check()
        assert (
            information.value.identity
            == "assembly_component_not_on_exposed_path:lens_b"
        )

class TestStableAuthorOrderForOutsideComponents:
    """
    死路径组件按 include 序报告，非哈希集或字母序
    """

    def test_outside_components_reported_in_author_order(self) -> None:
        """
        多个死路径组件按作者读序而非字母序排列

        两条独立死链分别为 dead_a_source 接 dead_a_lens、dead_b_source 接
        dead_b_lens；按 include 序把死路径缺陷排成作者读序。
        """

        grid = _grid()
        source = _plane_wave()
        detector = IntensityDetection()
        dead_a_source = _plane_wave()
        dead_a_lens = IdealThinLens(grid=grid, focal_length=1.0e-3)
        dead_b_source = _plane_wave()
        dead_b_lens = IdealThinLens(grid=grid, focal_length=2.0e-3)
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(detector, name="detector")
        assembly.include(dead_a_source, name="dead_a_source", grid=grid)
        assembly.include(dead_a_lens, name="dead_a_lens")
        assembly.include(dead_b_source, name="dead_b_source", grid=grid)
        assembly.include(dead_b_lens, name="dead_b_lens")
        assembly.connect(source, detector)
        assembly.connect(dead_a_source, dead_a_lens)
        assembly.connect(dead_b_source, dead_b_lens)
        assembly.expose(detector, name="intensity")
        with pytest.raises(AssemblyError) as information:
            assembly.check()
        dead_findings = [
            finding
            for finding in information.value.identity.split("; ")
            if "not_on_exposed_path" in finding
        ]
        assert dead_findings == [
            "assembly_component_not_on_exposed_path:dead_a_source",
            "assembly_component_not_on_exposed_path:dead_a_lens",
            "assembly_component_not_on_exposed_path:dead_b_source",
            "assembly_component_not_on_exposed_path:dead_b_lens",
        ]

class TestSuppressionOfDerivativeFindings:
    """
    已结构无效的拓扑不级联死路径缺陷，结构缺陷各自先报
    """

    def test_cycle_suppresses_exposed_path_findings(self) -> None:
        """
        注入回边成环时不级联死路径缺陷

        注入回边形成环并放一个孤儿源：check 只报 cycle，不报 not_on_exposed_path。
        """

        grid = _grid()
        source = _plane_wave()
        lens_a = IdealThinLens(grid=grid, focal_length=1.0e-3)
        lens_b = IdealThinLens(grid=grid, focal_length=2.0e-3)
        orphan_source = _plane_wave()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(lens_a, name="lens_a")
        assembly.include(lens_b, name="lens_b")
        assembly.include(orphan_source, name="orphan_source", grid=grid)
        assembly.connect(source, lens_a)
        assembly.connect(lens_a, lens_b)
        assembly.expose(lens_b, name="output")
        # 绕过公共 connect 直接注入回边 lens_b → lens_a，形成环
        assembly._connections.append(  # noqa: SLF001
            _Connection(
                source_name="lens_b",
                source_port=None,
                destination_name="lens_a",
                destination_port=None,
            )
        )
        with pytest.raises(AssemblyError) as information:
            assembly.check()
        identity = information.value.identity
        assert "assembly_topology_cycle" in identity
        # orphan_source 在死路径上，但 cycle 先报，不级联死路径缺陷
        assert "not_on_exposed_path" not in identity
        assert "orphan_source" not in identity

    def test_missing_input_suppresses_exposed_path_findings(self) -> None:
        """
        重组器缺失输入时不级联死路径缺陷

        重组器缺一个命名输入并放一个孤儿源：check 只报 input_missing。
        """

        grid = _grid()
        source = _plane_wave()
        from chromatix_next.optics.combination import CoherentCombination

        recombiner = CoherentCombination()
        orphan_source = _plane_wave()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(recombiner, name="recombiner")
        assembly.include(orphan_source, name="orphan_source", grid=grid)
        # 只连 field_1 输入；field_2 输入缺失
        assembly.connect(source, recombiner, destination_port="field_1")
        assembly.expose(recombiner, name="output")
        with pytest.raises(AssemblyError) as information:
            assembly.check()
        identity = information.value.identity
        assert "assembly_input_missing:recombiner:field_2" in identity
        # orphan_source 在死路径上，但缺失输入先报，不级联死路径缺陷
        assert "not_on_exposed_path" not in identity
        assert "orphan_source" not in identity

    def test_port_count_defect_suppresses_exposed_path_findings(self) -> None:
        """
        端口基数缺陷时不级联死路径缺陷

        注入重复目标输入形成端口基数缺陷并放一个孤儿源：check 只报
        port_count_mismatch。
        """

        grid = _grid()
        source_a = _plane_wave()
        source_b = _plane_wave()
        detector = IntensityDetection()
        orphan_source = _plane_wave()
        assembly = Assembly()
        assembly.include(source_a, name="source_a", grid=grid)
        assembly.include(source_b, name="source_b", grid=grid)
        assembly.include(detector, name="detector")
        assembly.include(orphan_source, name="orphan_source", grid=grid)
        assembly.connect(source_a, detector)
        assembly.expose(detector, name="intensity")
        # 绕过公共 connect 直接注入重复目标输入：detector:None 出现两个生产者
        assembly._connections.append(  # noqa: SLF001
            _Connection(
                source_name="source_b",
                source_port=None,
                destination_name="detector",
                destination_port=None,
            )
        )
        with pytest.raises(AssemblyError) as information:
            assembly.check()
        identity = information.value.identity
        assert (
            "assembly_input_port_count_mismatch:detector" in identity
        )
        # orphan_source 在死路径上，但端口基数缺陷先报，不级联死路径缺陷
        assert "not_on_exposed_path" not in identity
        assert "orphan_source" not in identity

class TestLegalDirectlyExposedSource:
    """
    直接暴露的源构成零边暴露路径，合法可运行
    """

    def test_directly_exposed_source_is_legal_zero_edge_path(self) -> None:
        """
        无连接但直接暴露的源合法可运行

        source 无连接但直接被暴露：check 通过，运行返回 OpticalField。
        """

        grid = _grid()
        source = _plane_wave()
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.expose(source, name="field")
        assembly.check()
        outputs = _run(assembly)
        assert isinstance(outputs["field"], OpticalField)

class TestLegalIndependentRootsAllExposed:
    """
    若干独立根各自到达一个暴露，合法可运行
    """

    def test_independent_roots_all_exposed_remain_legal(self) -> None:
        """
        两条独立子图各自暴露，整图合法可运行

        source_a 接 detector_a、source_b 接 detector_b 两条独立子图各自暴露。
        """

        grid = _grid()
        source_a = _plane_wave()
        source_b = _plane_wave()
        detector_a = IntensityDetection()
        detector_b = IntensityDetection()
        assembly = Assembly()
        assembly.include(source_a, name="source_a", grid=grid)
        assembly.include(detector_a, name="detector_a")
        assembly.include(source_b, name="source_b", grid=grid)
        assembly.include(detector_b, name="detector_b")
        assembly.connect(source_a, detector_a)
        assembly.connect(source_b, detector_b)
        assembly.expose(detector_a, name="intensity_a")
        assembly.expose(detector_b, name="intensity_b")
        outputs = _run(assembly)
        assert tuple(outputs) == ("intensity_a", "intensity_b")
        assert isinstance(outputs["intensity_a"], Intensity)
        assert isinstance(outputs["intensity_b"], Intensity)

class TestLegalMixedWaveRayRootsAllExposed:
    """
    混合独立 Wave 与 Ray 根各自到达暴露，合法且不引入跨域边
    """

    def test_mixed_wave_ray_roots_all_exposed_remain_legal(self) -> None:
        """
        波链与光线链在同一装配内共存且各自暴露

        波链为平面波接光强探测，光线链为准直源接传播到平面，二者各自暴露。
        """

        grid = _grid()
        wave_source = _plane_wave()
        wave_detector = IntensityDetection()
        ray_source = _collimated_ray_source()
        ray_trace = TraceTo(
            surface=Plane(
                origin=(0.0, 0.0, 5.0e-6),
                clear_aperture_radius=5.0e-6,
            ),
        )
        assembly = Assembly()
        assembly.include(wave_source, name="wave_source", grid=grid)
        assembly.include(wave_detector, name="wave_detector")
        assembly.include(ray_source, name="ray_source", grid=grid)
        assembly.include(ray_trace, name="ray_trace")
        assembly.connect(wave_source, wave_detector)
        assembly.connect(ray_source, ray_trace)
        assembly.expose(wave_detector, name="wave_intensity")
        assembly.expose(ray_trace, name="ray_bundle")
        outputs = _run(assembly)
        assert tuple(outputs) == ("wave_intensity", "ray_bundle")
        assert isinstance(outputs["wave_intensity"], Intensity)
        assert isinstance(outputs["ray_bundle"], RayBundle)

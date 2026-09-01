
from __future__ import annotations

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
from chromatix_next.optics._assembly_facts import _Connection  # noqa: SLF001
from chromatix_next.optics.combination import IntensityCombination
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


def _source(*, wavelength: float = 1.0e-6) -> PlaneWave:
    # 沿法线传播的标量平面波源
    return PlaneWave(
        spectrum=_spectrum(wavelength),
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


def _two_independent_detector_assembly() -> tuple[Assembly, dict[str, object]]:
    assembly = Assembly()
    source_a = _source(wavelength=1.0e-6)
    source_b = _source(wavelength=2.0e-6)
    detector_a = IntensityDetection()
    detector_b = IntensityDetection()
    assembly.include(source_a, name="source_a", grid=_grid())
    assembly.include(source_b, name="source_b", grid=_grid())
    assembly.include(detector_a, name="detector_a")
    assembly.include(detector_b, name="detector_b")
    assembly.connect(source_a, detector_a)
    assembly.connect(source_b, detector_b)
    assembly.expose(detector_a, name="intensity_a")
    assembly.expose(detector_b, name="intensity_b")
    return assembly, {
        "source_a": source_a,
        "source_b": source_b,
        "detector_a": detector_a,
        "detector_b": detector_b,
    }


def _occupied_combination_input_assembly() -> tuple[Assembly, dict[str, object]]:
    assembly = Assembly()
    source_a = _source()
    source_b = _source(wavelength=1.5e-6)
    spare_source = _source(wavelength=2.0e-6)
    detector_a = IntensityDetection()
    detector_b = IntensityDetection()
    combination = IntensityCombination()
    assembly.include(source_a, name="source_a", grid=_grid())
    assembly.include(source_b, name="source_b", grid=_grid())
    assembly.include(spare_source, name="spare_source", grid=_grid())
    assembly.include(detector_a, name="detector_a")
    assembly.include(detector_b, name="detector_b")
    assembly.include(combination, name="combination")
    assembly.connect(source_a, detector_a)
    assembly.connect(source_b, detector_b)
    assembly.connect(detector_a, combination, destination_port="intensity_1")
    assembly.connect(detector_b, combination, destination_port="intensity_2")
    assembly.expose(combination, name="intensity")
    assembly.expose(spare_source, name="spare_field")
    return assembly, {
        "source": source_a,
        "spare_source": spare_source,
        "combination": combination,
    }


class TestRejectedSecondSourceConnection:
    """
    被拒的第二条源连接留下原拓扑仍可 Check/Freeze/Host/Run，且与对照逐元素一致
    """

    def test_second_source_connection_rejected_at_connect_with_stable_identity(
        self,
    ) -> None:
        """
        重用已占用的源输出端口，第二条 connect 即以占用身份失败

        失败身份为 assembly_output_port_reused。
        """

        assembly, parts = _two_independent_detector_assembly()
        with pytest.raises(AssemblyError) as information:
            assembly.connect(
                parts["source_a"],  # type: ignore[arg-type]
                parts["detector_b"],  # type: ignore[arg-type]
            )
        message = information.value.identity
        assert message == "assembly_output_port_reused:source_a:None"

    def test_rejected_source_connection_leaves_topology_runnable_like_control(
        self,
    ) -> None:
        """
        被拒后原拓扑仍冻结运行，命名输出与对照装配逐元素一致
        """

        control, _parts = _two_independent_detector_assembly()
        control_outputs = _run(control)

        subject, parts = _two_independent_detector_assembly()
        with pytest.raises(AssemblyError, match="assembly_output_port_reused"):
            subject.connect(
                parts["source_a"],  # type: ignore[arg-type]
                parts["detector_b"],  # type: ignore[arg-type]
            )
        # 被拒连接不进入作者态：作者暴露序不变，且可完整 Check/Freeze/Host/Run
        assert subject.exposed_names() == control.exposed_names()
        subject.check()
        subject_outputs = _run(subject)

        assert tuple(subject_outputs) == tuple(control_outputs)
        baseline_a = control_outputs["intensity_a"]
        subject_a = subject_outputs["intensity_a"]
        baseline_b = control_outputs["intensity_b"]
        subject_b = subject_outputs["intensity_b"]
        assert isinstance(baseline_a, Intensity) and isinstance(subject_a, Intensity)
        assert isinstance(baseline_b, Intensity) and isinstance(subject_b, Intensity)
        assert torch.allclose(baseline_a.values, subject_a.values)
        assert torch.allclose(baseline_b.values, subject_b.values)


class TestRejectedSecondDestinationConnection:
    """
    被拒的第二条目标连接留下原拓扑仍可 Check/Freeze/Host/Run，且与对照逐元素一致
    """

    def test_second_destination_connection_rejected_at_connect_with_stable_identity(
        self,
    ) -> None:
        """
        重用已占用的目标输入端口，connect 即以占用身份失败

        失败身份为 assembly_input_port_count_mismatch。
        """

        assembly, parts = _occupied_combination_input_assembly()
        with pytest.raises(AssemblyError) as information:
            assembly.connect(
                parts["spare_source"],  # type: ignore[arg-type]
                parts["combination"],  # type: ignore[arg-type]
                destination_port="intensity_1",
            )
        assert (
            information.value.identity
            == "assembly_input_port_count_mismatch:combination:intensity_1"
        )

    def test_rejected_destination_connection_leaves_topology_runnable_like_control(
        self,
    ) -> None:
        """
        被拒后原拓扑仍冻结运行，命名输出与对照装配逐元素一致
        """

        control, _parts = _occupied_combination_input_assembly()
        control_outputs = _run(control)

        subject, parts = _occupied_combination_input_assembly()
        with pytest.raises(
            AssemblyError,
            match="assembly_input_port_count_mismatch",
        ):
            subject.connect(
                parts["spare_source"],  # type: ignore[arg-type]
                parts["combination"],  # type: ignore[arg-type]
                destination_port="intensity_1",
            )
        assert subject.exposed_names() == control.exposed_names()
        subject.check()
        subject_outputs = _run(subject)

        assert tuple(subject_outputs) == tuple(control_outputs) == (
            "intensity",
            "spare_field",
        )
        baseline = control_outputs["intensity"]
        subject_intensity = subject_outputs["intensity"]
        assert (
            isinstance(baseline, Intensity)
            and isinstance(subject_intensity, Intensity)
        )
        assert torch.allclose(baseline.values, subject_intensity.values)


    def test_cycle_closing_edge_rejected_at_connect_as_destination_reuse(
        self,
    ) -> None:
        """
        闭合成必重用已占用目标输入，connect 即以占用契约拒绝

        任何经公共 connect 形成的环都必须把一条回边送进一个已有生产者的目标
        输入端口，故占用守卫在 append 之前即以 assembly_input_port_count_mismatch
        拒绝。环的防御性回扫（assembly_topology_cycle）仍由 Check/Freeze 对篡改
        私有事实保留（见 test_assembly.py::test_check_reports_cycle_assembly_error）。
        """

        grid = _grid()
        assembly = Assembly()
        source = _source()
        lens_a = IdealThinLens(grid=grid, focal_length=1.0e-3)
        lens_b = IdealThinLens(grid=grid, focal_length=2.0e-3)
        assembly.include(source, name="source", grid=grid)
        assembly.include(lens_a, name="lens_a")
        assembly.include(lens_b, name="lens_b")
        assembly.connect(source, lens_a)
        assembly.connect(lens_a, lens_b)
        assembly.expose(lens_b, name="output")
        # 回边 lens_b → lens_a：lens_a 输入已有 source，占用守卫在 connect 即拒绝
        with pytest.raises(AssemblyError) as information:
            assembly.connect(lens_b, lens_a)
        assert (
            information.value.identity
            == "assembly_input_port_count_mismatch:lens_a:None"
        )
        # 被拒回边不进入作者态：原无环链路仍可冻结运行
        outputs = _run(assembly)
        assert tuple(outputs) == ("output",)
        assert isinstance(outputs["output"], OpticalField)


class TestDuplicateEdgeRejectedByOccupancyContract:
    """
    完全重复的边由同一占用契约拒绝，不引入"重复边"概念
    """

    def test_duplicate_edge_rejected_as_source_output_reuse(self) -> None:
        """
        同一条边再次 connect：源输出端口重用身份拒绝（非新的重复边身份）
        """

        assembly = Assembly()
        source = _source()
        detector = IntensityDetection()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(detector, name="detector")
        assembly.connect(source, detector)
        assembly.expose(detector, name="intensity")
        with pytest.raises(AssemblyError) as information:
            assembly.connect(source, detector)
        # 完全重复的边首先命中源输出端口占用契约
        assert information.value.identity == "assembly_output_port_reused:source:None"
        # 不存在专用的"重复边"身份
        assert "duplicate_edge" not in information.value.identity

    def test_duplicate_edge_leaves_original_topology_runnable(self) -> None:
        """
        被拒的重复边不改变作者态；原拓扑仍与对照运行一致
        """

        control = Assembly()
        source = _source()
        detector = IntensityDetection()
        control.include(source, name="source", grid=_grid())
        control.include(detector, name="detector")
        control.connect(source, detector)
        control.expose(detector, name="intensity")
        control_outputs = _run(control)

        subject = Assembly()
        source_b = _source()
        detector_b = IntensityDetection()
        subject.include(source_b, name="source", grid=_grid())
        subject.include(detector_b, name="detector")
        subject.connect(source_b, detector_b)
        subject.expose(detector_b, name="intensity")
        with pytest.raises(AssemblyError, match="assembly_output_port_reused"):
            subject.connect(source_b, detector_b)
        subject_outputs = _run(subject)

        baseline = control_outputs["intensity"]
        subject_intensity = subject_outputs["intensity"]
        assert (
            isinstance(baseline, Intensity)
            and isinstance(subject_intensity, Intensity)
        )
        assert torch.allclose(baseline.values, subject_intensity.values)


class TestWholeTopologyBackstop:
    """
    Check/Freeze 仍作为防御性回扫，捕捉绕过公共作者语法的篡改私有事实
    """

    def test_check_catches_source_output_reuse_in_malformed_private_facts(
        self,
    ) -> None:
        """
        直接向 _connections 追加重复源输出：check 仍以同一身份拒绝（回扫权威）
        """

        assembly, _parts = _occupied_combination_input_assembly()
        # 故意绕过 connect，模拟复制/还原/篡改的私有事实：重复占用 source 的输出端口
        assembly._connections.append(  # noqa: SLF001
            _Connection(
                source_name="source_a",
                source_port=None,
                destination_name="detector_a",
                destination_port=None,
            )
        )
        with pytest.raises(
            AssemblyError,
            match="assembly_output_port_reused",
        ):
            assembly.check()

    def test_check_catches_destination_input_reuse_in_malformed_private_facts(
        self,
    ) -> None:
        """
        直接向 _connections 追加重复目标输入：check 仍以同一身份拒绝（回扫权威）
        """

        assembly, _parts = _occupied_combination_input_assembly()
        # 故意绕过 connect：让 detector 的未命名输入出现两个生产者
        assembly._connections.append(  # noqa: SLF001
            _Connection(
                source_name="spare_source",
                source_port=None,
                destination_name="combination",
                destination_port="intensity_1",
            )
        )
        with pytest.raises(
            AssemblyError,
            match="assembly_input_port_count_mismatch:combination",
        ):
            assembly.check()

    def test_backstop_reports_value_mismatch_before_output_reuse(self) -> None:
        """
        全拓扑回扫沿用作者期的兼容性先于占用判定顺序
        """

        grid = _grid()
        source = _source()
        detector = IntensityDetection()
        lens_a = IdealThinLens(grid=grid, focal_length=1.0e-3)
        lens_b = IdealThinLens(grid=grid, focal_length=2.0e-3)
        assembly = Assembly()
        assembly.include(source, name="source", grid=grid)
        assembly.include(detector, name="detector")
        assembly.include(lens_a, name="lens_a")
        assembly.include(lens_b, name="lens_b")
        assembly.connect(source, detector)
        assembly._connections.extend(  # noqa: SLF001
            (
                _Connection("detector", None, "lens_a", None),
                _Connection("detector", None, "lens_b", None),
            )
        )
        assembly.expose(lens_a, name="output")

        with pytest.raises(AssemblyError) as information:
            assembly.check()

        second_mismatch = (
            "assembly_connection_value_mismatch:"
            "detector:None->lens_b:None"
        )
        output_reuse = "assembly_output_port_reused:detector:None"
        identity = information.value.identity
        assert second_mismatch in identity
        assert output_reuse in identity
        assert identity.index(second_mismatch) < identity.index(output_reuse)


class TestCrossDomainAndValueMismatchRemainAtomic:
    """Wave→Ray / Ray→Wave / 同域值不匹配仍在作者期拒绝，且不改变作者暴露态

    这些守卫已由 test_assembly_connection_typing 覆盖；此处只确认连接原子性未削弱
    它们——拒绝仍在 connect 发生、身份稳定、且不改变作者暴露序。可运行性"被拒后原拓扑仍
    可执行"由占用类证据（TestRejected{Second}*Connection）完整证明。
    """

    def test_wave_to_ray_rejected_at_connect_without_exposure_mutation(self) -> None:
        """
        Wave→Ray 跨域连接在 connect 即以 domain_mismatch 拒绝；暴露序不变
        """

        assembly = Assembly()
        wave_source = _source()
        ray_trace = TraceTo(
            surface=Plane(
                origin=(0.0, 0.0, 5.0e-6),
                clear_aperture_radius=5.0e-6,
            ),
        )
        assembly.include(wave_source, name="wave_source", grid=_grid())
        assembly.include(ray_trace, name="ray_trace")
        with pytest.raises(AssemblyError) as information:
            assembly.connect(wave_source, ray_trace)
        assert "assembly_connection_domain_mismatch" in information.value.identity
        # 被拒连接未进入作者态：暴露序仍为空
        assert assembly.exposed_names() == ()

    def test_ray_to_wave_rejected_at_connect_without_exposure_mutation(self) -> None:
        """
        Ray→Wave 跨域连接在 connect 即以 domain_mismatch 拒绝；暴露序不变
        """

        assembly = Assembly()
        ray_source = CollimatedRaySource(
            spectrum=_spectrum(),
            polarization=Polarization.linear_x(),
            medium=Vacuum(),
            ray_power=1.0,
        )
        wave_detector = IntensityDetection()
        assembly.include(ray_source, name="ray_source", grid=_grid())
        assembly.include(wave_detector, name="wave_detector")
        with pytest.raises(AssemblyError) as information:
            assembly.connect(ray_source, wave_detector)
        assert "assembly_connection_domain_mismatch" in information.value.identity
        assert assembly.exposed_names() == ()

    def test_same_domain_value_mismatch_rejected_at_connect(self) -> None:
        """
        同波域异种（Intensity → 只接受 OpticalField 的元件）在 connect 即被拒
        """

        assembly = Assembly()
        source = _source()
        detector = IntensityDetection()
        lens = IdealThinLens(grid=_grid(), focal_length=1.0e-3)
        assembly.include(source, name="source", grid=_grid())
        assembly.include(detector, name="detector")
        assembly.include(lens, name="lens")
        assembly.connect(source, detector)
        with pytest.raises(AssemblyError) as information:
            assembly.connect(detector, lens)
        assert (
            "assembly_connection_value_mismatch" in information.value.identity
        )
        assert "domain_mismatch" not in information.value.identity
        assert assembly.exposed_names() == ()


class TestAtomicAuthoringOrder:
    """
    作者期校验序：物理值兼容性先于占用判定，占用先于 append
    """

    def test_rejected_connection_never_appends_partial_state(self) -> None:
        """
        被拒连接不留半截作者态：连一次合法、再连一次非法后，原拓扑仍可冻结运行
        """

        # 一条合法链路 + 一次被拒重用：最终可运行结果与只连合法链路的对照一致
        control, _parts = _occupied_combination_input_assembly()
        control_outputs = _run(control)

        subject, parts = _occupied_combination_input_assembly()
        with pytest.raises(AssemblyError, match="assembly_input_port_count_mismatch"):
            subject.connect(
                parts["spare_source"],  # type: ignore[arg-type]
                parts["combination"],  # type: ignore[arg-type]
                destination_port="intensity_1",
            )
        # 占用守卫在 append 之前抛出：作者态与对照等价，故可 Check/Freeze/Host/Run
        subject.check()
        subject_outputs = _run(subject)
        baseline = control_outputs["intensity"]
        subject_intensity = subject_outputs["intensity"]
        assert (
            isinstance(baseline, Intensity)
            and isinstance(subject_intensity, Intensity)
        )
        assert torch.allclose(baseline.values, subject_intensity.values)

def _collimated_ray_source(
    *,
    ray_power: float | torch.nn.Parameter = 1.0,
) -> CollimatedRaySource:
    # 默认沿 +z 发射的准直光线源；ray_power 可注入可训练 Parameter
    return CollimatedRaySource(
        spectrum=_spectrum(),

        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        ray_power=ray_power,
    )

def _ray_propagation_plane() -> Plane:
    # 位于 +z 前方的平面；默认光线源沿 +z 发射，正向命中
    return Plane(
        origin=(0.0, 0.0, 5.0e-6),
        clear_aperture_radius=5.0e-6,
    )

class TestPortPhysicalValueRecording:
    """接受条目 1：每个端口记录精确物理值；条目 2：合法性只来自角色 + 端口物理值
    """

    def test_wave_source_output_port_is_optical_field(self) -> None:
        """平面波源的输出端口产出光场（波域）
        """

        assembly = Assembly()
        source = _source()
        assembly.include(source, name="source", grid=_grid())
        contract = assembly._contracts["source"]  # noqa: SLF001
        assert contract.output_values == (OpticalField,)
        assert contract.input_values == ()

    def test_ray_source_output_port_is_ray_bundle(self) -> None:
        """准直光线源的输出端口产出光线束（光线域）
        """

        assembly = Assembly()
        source = _collimated_ray_source()
        assembly.include(source, name="source", grid=_grid())
        contract = assembly._contracts["source"]  # noqa: SLF001
        assert contract.output_values == (RayBundle,)
        assert contract.input_values == ()

    def test_detection_ports_are_wave_domain(self) -> None:
        """光强探测入端口光场、出端口光强（同属波域，异种但同域）
        """

        assembly = Assembly()
        detector = IntensityDetection()
        assembly.include(detector, name="detector")
        contract = assembly._contracts["detector"]  # noqa: SLF001
        assert contract.input_values == (OpticalField,)
        assert contract.output_values == (Intensity,)

    def test_ray_propagation_ports_are_ray_bundle(self) -> None:
        """光线传播动作的入/出端口都是光线束
        """

        assembly = Assembly()
        trace = TraceTo(surface=_ray_propagation_plane())
        assembly.include(trace, name="trace")
        contract = assembly._contracts["trace"]  # noqa: SLF001
        assert contract.input_values == (RayBundle,)
        assert contract.output_values == (RayBundle,)

class _LyingKindDetection(torch.nn.Module):

    @property
    def role(self) -> Literal["detection"]:
        """探测角色字面量
        """

        return "detection"

    def forward(self, field: OpticalField) -> Intensity:  # type: ignore[override]
        """故意返回与声明光强不符的入射光场
        """

        return field  # type: ignore[return-value]

class _LyingArityDetection(torch.nn.Module):

    @property
    def role(self) -> Literal["detection"]:
        """探测角色字面量
        """

        return "detection"

    def forward(self, field: OpticalField) -> Intensity:  # type: ignore[override]
        """故意返回与单端口不符的二元组
        """

        return (field, field)  # type: ignore[return-value]

class TestOutputReconciliationRejection:
    """
    接受条目 1/2 的负向证据：重放期结构对账与种类对账各以稳定身份拒绝
    """

    def test_wrong_length_tuple_rejected_as_port_arity_mismatch(self) -> None:
        """
        声明单端口的组件返回二元组时，以元数不匹配稳定身份拒绝（非 forward 失败）
        """

        assembly = Assembly()
        source = _source()
        lying = _LyingArityDetection()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(lying, name="lying")
        assembly.connect(source, lying)
        assembly.expose(lying, name="output")
        with pytest.raises(AssemblyError) as exception:
            assembly.check()
        message = str(exception.value)
        assert "assembly_output_port_arity_mismatch" in message
        assert "lying" in message
        # 关键回归断言：不会被改写成 forward 失败身份
        assert "forward_failed" not in message
        assert "ValueError" not in message

    def test_wrong_kind_output_rejected_as_value_kind_mismatch(self) -> None:
        """
        声明产出光强的端口实际返回光场时，以种类不匹配稳定身份拒绝
        """

        assembly = Assembly()
        source = _source()
        lying = _LyingKindDetection()
        assembly.include(source, name="source", grid=_grid())
        assembly.include(lying, name="lying")
        assembly.connect(source, lying)
        assembly.expose(lying, name="output")
        with pytest.raises(AssemblyError) as exception:
            assembly.check()
        message = str(exception.value)
        assert "assembly_output_value_kind_mismatch" in message
        assert "lying" in message

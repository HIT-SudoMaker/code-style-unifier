from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Literal

import pytest
import torch

from chromatix_next import Workstation
from chromatix_next.optics import (
    Assembly,
    ConstantMedium,
    Intensity,
    Polarization,
    PropagationDirection,
    RayBundle,
    SpatialGrid,
    Spectrum,
    Vacuum,
    _assembly_facts,
    _assembly_replay,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    ReflectAt,
    RefractAt,
    RetarderAt,
)
from chromatix_next.optics.field import (
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    _own_field_value,
    _SourceLineage,
)
from chromatix_next.optics.polarization import PolarizationRepresentation
from chromatix_next.optics.propagation import TraceTo
from chromatix_next.optics.source import CollimatedRaySource, PlaneWave
from chromatix_next.optics.surface import Plane


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(6, 6),
        sample_spacing=(0.5e-6, 0.5e-6),
    )


def _spectrum() -> Spectrum:
    return Spectrum.monochromatic(wavelength=1.0e-6)


def _run_on(workstation: Workstation, assembly: Assembly) -> Mapping[str, object]:
    workstation.host(assembly)
    outputs, _record = workstation.run(assembly)
    return outputs


# 记录私有 Meta 网格解析器收到的真实 SpatialGrid
class _GridResolvingPropagation(torch.nn.Module):
    resolved_grids: list[SpatialGrid]

    def __init__(self) -> None:
        super().__init__()
        self.resolved_grids = []

    @property
    def role(self) -> Literal["propagation"]:
        """
        返回测试 Propagation 的封闭角色

        Returns:
            propagation 角色字面量

        """

        return "propagation"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        保留输入光场以隔离 replay 网格账本

        Args:
            field: 上游 Wave Encounter 产生的光场

        Returns:
            未改写的同一 OpticalField

        """

        return field

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        self.resolved_grids.append(field.grid)
        return field.grid


_SHARED_TEST_LINEAGE = _SourceLineage()


# 在隔离 Meta 副本间仍显式共享测试 Source Lineage
class _SharedLineageFieldSource(torch.nn.Module):
    envelope: torch.Tensor

    def __init__(self) -> None:
        super().__init__()
        self.register_buffer(
            "envelope",
            torch.ones(
                (1, 2, 6, 6),
                dtype=torch.complex128,
            ),
        )

    @property
    def role(self) -> Literal["source"]:
        """
        返回测试 Source 的封闭角色

        Returns:
            source 角色字面量

        """

        return "source"

    def forward(self, grid: SpatialGrid) -> OpticalField:
        """
        在作者网格上构造共享谱系的 transverse OpticalField

        Args:
            grid: Assembly 注册的 Source 采样锚

        Returns:
            共享测试 Source Lineage 的 OpticalField

        """

        field = OpticalField(
            envelope=self.envelope,
            grid=grid,
            spectrum=Spectrum.monochromatic(wavelength=1.0e-6),
            polarization_representation=PolarizationRepresentation.TRANSVERSE,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        )
        return _own_field_value(field, _SHARED_TEST_LINEAGE)


def _cube() -> IdealNonpolarizingCubeBeamSplitter:
    return IdealNonpolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=0.37,
    )


def _transverse_plane_wave() -> PlaneWave:
    return PlaneWave(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )


def _mixed_wave_ray_multi_source_assembly() -> Assembly:
    grid = _grid()
    wave_source = PlaneWave(
        spectrum=_spectrum(),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    wave_detector = IntensityDetection()
    ray_source = CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        launch_origin=(0.0, 0.0, 0.0),
        launch_tangent_x=(1.0, 0.0, 0.0),
        launch_tangent_y=(0.0, 1.0, 0.0),
        ray_power=1.0,
    )
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
    assembly.freeze()
    return assembly


def test_mixed_sources_run_together_through_public_seam() -> None:
    """
    Wave 与 Ray 子图在同一次 Workstation 运行中按作者序暴露结果
    """

    outputs = _run_on(
        Workstation.cpu(),
        _mixed_wave_ray_multi_source_assembly(),
    )
    assert tuple(outputs) == ("wave_intensity", "ray_bundle")
    assert isinstance(outputs["wave_intensity"], Intensity)
    assert isinstance(outputs["ray_bundle"], RayBundle)
    assert outputs["wave_intensity"].values.device == torch.device("cpu")
    assert outputs["ray_bundle"].position.device == torch.device("cpu")


def test_public_assembly_executes_six_step_polarized_ray_path() -> None:
    """
    公共 Assembly 按追迹、延迟、反射、追迹、折射、延迟执行光路
    """

    grid = SpatialGrid.centered(
        sample_counts=(1, 1),
        sample_spacing=(1.0e-6, 1.0e-6),
    )
    direction_x = 0.3
    direction_z = math.sqrt(1.0 - direction_x**2)
    source = CollimatedRaySource(
        spectrum=Spectrum.monochromatic(wavelength=2.0e-6),
        polarization=Polarization.linear_x(),
        launch_origin=(0.0, 0.0, -1.0e-6),
        launch_tangent_x=(0.0, 1.0, 0.0),
        launch_tangent_y=(-direction_z, 0.0, direction_x),
        ray_power=1.0,
    )
    first_plane = Plane(
        origin=(0.0, 0.0, 0.0),
        clear_aperture_radius=10.0,
    )
    reflected_plane = Plane(
        origin=(0.0, 0.0, -2.0),
        clear_aperture_radius=10.0,
    )
    actions = (
        TraceTo(surface=first_plane),
        RetarderAt(
            surface=first_plane,
            retardance_cycles=0.18,
            retarded_eigenstate_azimuth_radians=math.radians(22.0),
            retarded_eigenstate_ellipticity_radians=0.0,
        ),
        ReflectAt(surface=first_plane),
        TraceTo(surface=reflected_plane),
        RefractAt(
            surface=reflected_plane,
            destination_medium=ConstantMedium(index=1.3),
        ),
        RetarderAt(
            surface=reflected_plane,
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.radians(15.0),
            retarded_eigenstate_ellipticity_radians=math.radians(3.0),
        ),
    )
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    for action_index, action in enumerate(actions, start=1):
        assembly.include(action, name=f"step_{action_index}")
    assembly.connect(source, actions[0])
    for upstream, downstream in zip(actions[:-1], actions[1:], strict=True):
        assembly.connect(upstream, downstream)
    assembly.expose(actions[-1], name="rays")
    assembly.freeze()

    outputs = _run_on(Workstation.cpu(), assembly)
    assert assembly.is_frozen
    assert assembly.exposed_names() == ("rays",)
    assert isinstance(outputs["rays"], RayBundle)


def test_wave_encounter_real_grid_reaches_and_releases_across_propagations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Wave Encounter 的真实网格可传递给下游解析器并随值一起释放
    """

    grid = SpatialGrid(
        sample_counts=(4, 6),
        sample_spacing=(7.0e-6, 11.0e-6),
        first_sample_position=(-13.0e-6, 19.0e-6),
    )
    source = _transverse_plane_wave()
    cube = _cube()
    first_propagation = _GridResolvingPropagation()
    second_propagation = _GridResolvingPropagation()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(first_propagation, name="first_propagation")
    assembly.include(second_propagation, name="second_propagation")
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
    assembly.connect(
        encounter,
        first_propagation,
        source_terminal=CubeTerminal.TOP,
    )
    assembly.connect(first_propagation, second_propagation)
    assembly.end_route(
        encounter,
        source_terminal=CubeTerminal.RIGHT,
        reason="outside_modeled_system",
    )
    assembly.expose(second_propagation, name="field")
    assembly.freeze()
    real_outputs = assembly._replay()  # noqa: SLF001

    grids_before_second: list[tuple[object, ...]] = []
    original_resolver = _assembly_replay._real_output_grid_for_plan_step

    def _recording_resolver(**kwargs: object) -> SpatialGrid | None:
        step = kwargs["step"]
        if getattr(step, "component_name", None) == "second_propagation":
            real_grids = kwargs["real_grids"]
            assert isinstance(real_grids, dict)
            grids_before_second.append(tuple(real_grids))
        return original_resolver(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        _assembly_replay,
        "_real_output_grid_for_plan_step",
        _recording_resolver,
    )
    first_propagation.resolved_grids.clear()
    second_propagation.resolved_grids.clear()
    findings: list[str] = []
    _assembly_replay._collect_meta_inference_findings(
        assembly,
        facts=assembly._execution_facts(),  # noqa: SLF001
        findings=findings,
    )

    assert findings == []
    assert len(first_propagation.resolved_grids) == 1
    assert first_propagation.resolved_grids[0].is_physically_equivalent_to(
        real_outputs["field"].grid,
    )
    assert len(second_propagation.resolved_grids) == 1
    assert second_propagation.resolved_grids[0].is_physically_equivalent_to(
        real_outputs["field"].grid,
    )
    assert len(grids_before_second) == 1
    assert not any(
        isinstance(
            coordinate,
            _assembly_facts._DirectionalValueCoordinate,  # noqa: SLF001
        )
        for coordinate in grids_before_second[0]
    )


def test_incompatible_incident_real_grids_fail_without_downstream_publish() -> None:
    """
    多入射 Wave Encounter 不从不等价真实网格中任择一个输出网格
    """

    left_source = _SharedLineageFieldSource()
    bottom_source = _SharedLineageFieldSource()
    probe = _GridResolvingPropagation()
    cube = _cube()
    assembly = Assembly()
    assembly.include(left_source, name="left_source", grid=_grid())
    assembly.include(
        bottom_source,
        name="bottom_source",
        grid=SpatialGrid.centered(
            sample_counts=(6, 6),
            sample_spacing=(0.75e-6, 0.5e-6),
        ),
    )
    assembly.include(probe, name="probe")
    assembly.include_directional(cube, name="cube")
    encounter = assembly.wave_encounter(
        cube,
        name="combine",
        incident_terminals=(CubeTerminal.LEFT, CubeTerminal.BOTTOM),
    )
    assembly.connect(
        left_source,
        encounter,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        bottom_source,
        encounter,
        destination_terminal=CubeTerminal.BOTTOM,
    )
    assembly.connect(
        encounter,
        probe,
        source_terminal=CubeTerminal.TOP,
    )
    assembly.end_route(
        encounter,
        source_terminal=CubeTerminal.RIGHT,
        reason="outside_modeled_system",
    )
    assembly.expose(probe, name="field")
    facts = assembly._execution_facts()  # noqa: SLF001
    findings: list[str] = []

    _assembly_replay._collect_meta_inference_findings(
        assembly,
        facts=facts,
        findings=findings,
    )

    assert findings == [
        "assembly_wave_contributors_incompatible:owner=cube:"
        "encounter=combine:incident=bottom:outgoing=top:route=-:"
        "underlying=grid_mismatch"
    ]
    assert probe.resolved_grids == []

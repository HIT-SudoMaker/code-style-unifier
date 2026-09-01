# 单一 Cube owner 的解析 Michelson 干涉仪教学案例。

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import cast

from chromatix_next import Workstation
from chromatix_next.optics import (
    Assembly,
    Intensity,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPlanarMirror,
    MirrorTerminal,
)
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave

WAVELENGTH = 632.8e-9
SPECTRAL_WEIGHT = 1.0
REFRACTIVE_INDEX = 1.0
SAMPLE_COUNTS = (8, 12)
SAMPLE_SPACING = (7.0e-6, 11.0e-6)
RIGHT_ARM_LENGTH = 1.0e-3
RELATIVE_PHASE_POINTS = (
    0.0,
    math.pi / 3.0,
    2.0 * math.pi / 3.0,
    math.pi,
)
TOP_ARM_OFFSETS = (
    0.0,
    WAVELENGTH / 12.0,
    WAVELENGTH / 6.0,
    WAVELENGTH / 4.0,
)
DENSE_COMPLEX_OPERATOR_MAX_ABSOLUTE_ERROR = 5.0e-13
PORT_RATIO_ABSOLUTE_ERROR = 2.0e-12
COMPLEMENTARY_SUM_ABSOLUTE_ERROR = 2.0e-12
VISIBILITY_ABSOLUTE_ERROR = 2.0e-12
MINIMUM_COUNTERFACTUAL_PORT_SEPARATION = 0.20


@dataclass(frozen=True, slots=True)
class MichelsonPhaseObservation:
    """
    保存一个冻结相位点的两个 RELATIVE 端口比
    """

    relative_phase: float
    top_arm_length: float
    left_ratio: float
    bottom_ratio: float
    ratio_sum: float


@dataclass(frozen=True, slots=True)
class AnalyticMichelsonResult:
    """
    保存四点解析扫相的少量可序列化摘要
    """

    wavelength: float
    spectral_weight: float
    refractive_index: float
    sample_counts: tuple[int, int]
    sample_spacing: tuple[float, float]
    right_arm_length: float
    observations: tuple[MichelsonPhaseObservation, ...]
    left_visibility: float
    bottom_visibility: float
    workstation_device: str


def _top_arm_length(relative_phase: float) -> float:
    try:
        index = RELATIVE_PHASE_POINTS.index(relative_phase)
    except ValueError as error:
        raise ValueError(
            "analytic_michelson_relative_phase_not_frozen"
        ) from error
    return RIGHT_ARM_LENGTH + TOP_ARM_OFFSETS[index]


def build_assembly(
    *,
    relative_phase: float = math.pi / 3.0,
) -> Assembly:
    """
    以同一 Cube owner 的 outward/return Encounters 构造冻结 Michelson
    """

    top_arm_length = _top_arm_length(relative_phase)
    grid = SpatialGrid.centered(
        sample_counts=SAMPLE_COUNTS,
        sample_spacing=SAMPLE_SPACING,
    )
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=WAVELENGTH),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    cube = IdealNonpolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=math.pi / 4.0,
    )
    right_mirror = IdealPlanarMirror(
        origin=(RIGHT_ARM_LENGTH, 0.0, 0.0),
        outward_normal=(-1.0, 0.0, 0.0),
        transverse_up=(0.0, 0.0, 1.0),
    )
    top_mirror = IdealPlanarMirror(
        origin=(0.0, top_arm_length, 0.0),
        outward_normal=(0.0, -1.0, 0.0),
        transverse_up=(0.0, 0.0, 1.0),
    )
    right_out = ScalarAngularSpectrum(
        axial_distance=RIGHT_ARM_LENGTH,
    )
    right_back = ScalarAngularSpectrum(
        axial_distance=RIGHT_ARM_LENGTH,
    )
    top_out = ScalarAngularSpectrum(
        axial_distance=top_arm_length,
    )
    top_back = ScalarAngularSpectrum(
        axial_distance=top_arm_length,
    )
    left_detector = IntensityDetection()
    bottom_detector = IntensityDetection()

    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    for name, component in (
        ("right_out", right_out),
        ("right_back", right_back),
        ("top_out", top_out),
        ("top_back", top_back),
        ("left_detector", left_detector),
        ("bottom_detector", bottom_detector),
    ):
        assembly.include(component, name=name)
    assembly.include_directional(cube, name="cube")
    assembly.include_directional(right_mirror, name="right_mirror")
    assembly.include_directional(top_mirror, name="top_mirror")

    outward_cube = assembly.wave_encounter(
        cube,
        name="outward_cube",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    right_mirror_turn = assembly.wave_encounter(
        right_mirror,
        name="right_mirror_turn",
        incident_terminals=(MirrorTerminal.FRONT,),
    )
    top_mirror_turn = assembly.wave_encounter(
        top_mirror,
        name="top_mirror_turn",
        incident_terminals=(MirrorTerminal.FRONT,),
    )
    return_cube = assembly.wave_encounter(
        cube,
        name="return_cube",
        incident_terminals=(CubeTerminal.TOP, CubeTerminal.RIGHT),
    )

    assembly.connect(
        source,
        outward_cube,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        outward_cube,
        right_out,
        source_terminal=CubeTerminal.RIGHT,
    )
    assembly.connect(
        right_out,
        right_mirror_turn,
        destination_terminal=MirrorTerminal.FRONT,
    )
    assembly.connect(
        right_mirror_turn,
        right_back,
        source_terminal=MirrorTerminal.FRONT,
    )
    assembly.connect(
        right_back,
        return_cube,
        destination_terminal=CubeTerminal.RIGHT,
    )
    assembly.connect(
        outward_cube,
        top_out,
        source_terminal=CubeTerminal.TOP,
    )
    assembly.connect(
        top_out,
        top_mirror_turn,
        destination_terminal=MirrorTerminal.FRONT,
    )
    assembly.connect(
        top_mirror_turn,
        top_back,
        source_terminal=MirrorTerminal.FRONT,
    )
    assembly.connect(
        top_back,
        return_cube,
        destination_terminal=CubeTerminal.TOP,
    )
    assembly.connect(
        return_cube,
        left_detector,
        source_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        return_cube,
        bottom_detector,
        source_terminal=CubeTerminal.BOTTOM,
    )
    assembly.expose(left_detector, name="left_intensity")
    assembly.expose(bottom_detector, name="bottom_intensity")
    assembly.freeze()
    return assembly


def _visibility(values: tuple[float, ...]) -> float:
    maximum = max(values)
    minimum = min(values)
    return (maximum - minimum) / (maximum + minimum)


def run(*, workstation: Workstation) -> AnalyticMichelsonResult:
    """
    在给定 Workstation 运行冻结的四个 RELATIVE 相位点
    """

    observations: list[MichelsonPhaseObservation] = []
    for relative_phase in RELATIVE_PHASE_POINTS:
        assembly = build_assembly(relative_phase=relative_phase)
        workstation.host(assembly)
        try:
            outputs, _record = workstation.run(assembly)
        finally:
            workstation.release(assembly)
        left = cast(Intensity, outputs["left_intensity"])
        bottom = cast(Intensity, outputs["bottom_intensity"])
        left_ratio = float(left.values.mean().item())
        bottom_ratio = float(bottom.values.mean().item())
        observations.append(
            MichelsonPhaseObservation(
                relative_phase=relative_phase,
                top_arm_length=_top_arm_length(relative_phase),
                left_ratio=left_ratio,
                bottom_ratio=bottom_ratio,
                ratio_sum=left_ratio + bottom_ratio,
            )
        )

    frozen_observations = tuple(observations)
    return AnalyticMichelsonResult(
        wavelength=WAVELENGTH,
        spectral_weight=SPECTRAL_WEIGHT,
        refractive_index=REFRACTIVE_INDEX,
        sample_counts=SAMPLE_COUNTS,
        sample_spacing=SAMPLE_SPACING,
        right_arm_length=RIGHT_ARM_LENGTH,
        observations=frozen_observations,
        left_visibility=_visibility(
            tuple(value.left_ratio for value in frozen_observations),
        ),
        bottom_visibility=_visibility(
            tuple(value.bottom_ratio for value in frozen_observations),
        ),
        workstation_device=str(workstation.device),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen four-point analytic Michelson sweep on a CPU."
        ),
    )
    parser.add_argument("--output", type=Path)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """
    运行命令行教学入口
    """

    parsed = _parser().parse_args(arguments)
    result = run(workstation=Workstation.cpu())
    print(
        "Analytic Michelson: "
        f"left visibility={result.left_visibility:.12f}, "
        f"bottom visibility={result.bottom_visibility:.12f}"
    )
    if parsed.output is not None:
        parsed.output.write_text(
            json.dumps(asdict(result), indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

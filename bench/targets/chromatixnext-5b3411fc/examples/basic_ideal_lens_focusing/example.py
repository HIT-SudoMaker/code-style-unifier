# 圆光瞳与理想薄透镜聚焦教学案例。

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from functools import partial
import json
from pathlib import Path
from typing import cast

import torch

from chromatix_next import Workstation
from chromatix_next.optics import (
    Intensity,
    OpticalField,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import CircularPupil, IdealThinLens
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave

MICROMETRE = 1.0e-6
MILLIMETRE = 1.0e-3


@dataclass(frozen=True, slots=True)
class IdealLensFocusingResult:
    """
    保存焦平面观测的少量可序列化摘要
    """

    sample_counts: tuple[int, int]
    wavelength: float
    aperture_diameter: float
    focal_length: float
    peak_intensity: float
    peak_index: tuple[int, int]
    airy_first_zero_radius: float
    workstation_device: str


def _build_root(
    *,
    grid: SpatialGrid,
    wavelength: float,
    aperture_diameter: float,
    focal_length: float,
) -> torch.nn.ModuleDict:
    # 光瞳透镜传播的托管组件根。
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=wavelength),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    pupil = CircularPupil(
        grid=grid,
        radius=aperture_diameter / 2.0,
    )
    lens = IdealThinLens(
        grid=grid,
        focal_length=focal_length,
    )
    propagation = ScalarAngularSpectrum(axial_distance=focal_length)
    detector = IntensityDetection()
    return torch.nn.ModuleDict(
        {
            "source": source,
            "pupil": pupil,
            "lens": lens,
            "propagation": propagation,
            "detector": detector,
        }
    )


def _inputs(
    device: torch.device,
    *,
    grid: SpatialGrid,
) -> tuple[SpatialGrid]:
    return (
        grid.to(
            device=device,
            dtype=torch.float64,
        ),
    )


def _calculate(
    root: torch.nn.ModuleDict,
    grid: SpatialGrid,
) -> Mapping[str, OpticalField | Intensity]:
    field = root["source"](grid)
    field = root["pupil"](field)
    field = root["lens"](field)
    field = root["propagation"](field)
    intensity = root["detector"](field)
    return {"focal_intensity": intensity}


def run(
    *,
    workstation: Workstation,
    sample_counts: tuple[int, int] = (64, 64),
    sample_spacing: tuple[float, float] = (
        5.0 * MICROMETRE,
        5.0 * MICROMETRE,
    ),
    wavelength: float = 0.5 * MICROMETRE,
    aperture_diameter: float = 160.0 * MICROMETRE,
    focal_length: float = 20.0 * MILLIMETRE,
) -> IdealLensFocusingResult:
    """
    在给定工作站运行逐行组合的光路
    """

    grid = SpatialGrid.centered(
        sample_counts=sample_counts,
        sample_spacing=sample_spacing,
    )
    root = _build_root(
        grid=grid,
        wavelength=wavelength,
        aperture_diameter=aperture_diameter,
        focal_length=focal_length,
    )
    workstation.host(root)
    outputs, _record = workstation.run(
        _calculate,
        root=root,
        inputs=partial(_inputs, grid=grid),
    )
    intensity = cast(Intensity, outputs["focal_intensity"])
    values = intensity.values
    flat_index = int(torch.argmax(values).item())
    peak_index = divmod(flat_index, values.shape[-1])
    return IdealLensFocusingResult(
        sample_counts=sample_counts,
        wavelength=wavelength,
        aperture_diameter=aperture_diameter,
        focal_length=focal_length,
        peak_intensity=float(values.flatten()[flat_index].item()),
        peak_index=peak_index,
        airy_first_zero_radius=(
            1.22 * wavelength * focal_length / aperture_diameter
        ),
        workstation_device=str(workstation.device),
    )


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        error_identity = "example_value_must_be_positive"
        raise argparse.ArgumentTypeError(error_identity)
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0.0:
        error_identity = "example_value_must_be_positive"
        raise argparse.ArgumentTypeError(error_identity)
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Focus a plane wave with an ideal lens on a CPU.",
    )
    parser.add_argument(
        "--sample-counts",
        type=_positive_integer,
        nargs=2,
        default=(64, 64),
    )
    parser.add_argument(
        "--sample-spacing",
        type=_positive_float,
        nargs=2,
        default=(5.0 * MICROMETRE, 5.0 * MICROMETRE),
        help="SI metres along (y, x).",
    )
    parser.add_argument(
        "--wavelength",
        type=_positive_float,
        default=0.5 * MICROMETRE,
    )
    parser.add_argument(
        "--aperture-diameter",
        type=_positive_float,
        default=160.0 * MICROMETRE,
    )
    parser.add_argument(
        "--focal-length",
        type=_positive_float,
        default=20.0 * MILLIMETRE,
    )
    parser.add_argument("--output", type=Path)
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """
    运行命令行教学入口
    """

    parsed = _parser().parse_args(arguments)
    result = run(
        workstation=Workstation.cpu(),
        sample_counts=tuple(parsed.sample_counts),
        sample_spacing=tuple(parsed.sample_spacing),
        wavelength=parsed.wavelength,
        aperture_diameter=parsed.aperture_diameter,
        focal_length=parsed.focal_length,
    )
    print(
        "Ideal lens: "
        f"focal length={result.focal_length / MILLIMETRE:.3f} mm, "
        f"peak intensity={result.peak_intensity:.6f}"
    )
    if parsed.output is not None:
        parsed.output.write_text(
            json.dumps(asdict(result), indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

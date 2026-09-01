# 光瞳场向显式平移目标网格传播的教学案例。

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
    PropagationExterior,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import CircularPupil
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave

MICROMETRE = 1.0e-6
MILLIMETRE = 1.0e-3


@dataclass(frozen=True, slots=True)
class ScalarAngularSpectrumPropagationResult:
    """
    保存传播观测的少量可序列化摘要
    """

    sample_counts: tuple[int, int]
    wavelength: float
    axial_distance: float
    destination_shift: tuple[float, float]
    destination_first_sample: tuple[float, float]
    peak_intensity: float
    mean_intensity: float
    workstation_device: str


def _build_root(
    *,
    grid: SpatialGrid,
    destination_grid: SpatialGrid,
    wavelength: float,
    aperture_diameter: float,
    axial_distance: float,
) -> torch.nn.ModuleDict:
    # 角谱传播的托管组件根。
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
    propagation = ScalarAngularSpectrum(
        axial_distance=axial_distance,
        exterior=PropagationExterior.PERIODIC,
        destination_grid=destination_grid,
    )
    detector = IntensityDetection()
    return torch.nn.ModuleDict(
        {
            "source": source,
            "pupil": pupil,
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
    field = root["propagation"](field)
    intensity = root["detector"](field)
    return {"propagated_intensity": intensity}


def run(
    *,
    workstation: Workstation,
    sample_counts: tuple[int, int] = (48, 48),
    sample_spacing: tuple[float, float] = (
        2.0 * MICROMETRE,
        2.0 * MICROMETRE,
    ),
    wavelength: float = 0.5 * MICROMETRE,
    aperture_diameter: float = 48.0 * MICROMETRE,
    axial_distance: float = 0.4 * MILLIMETRE,
    destination_shift: tuple[float, float] = (
        8.0 * MICROMETRE,
        -6.0 * MICROMETRE,
    ),
) -> ScalarAngularSpectrumPropagationResult:
    """
    在给定工作站运行逐行组合的光路
    """

    grid = SpatialGrid.centered(
        sample_counts=sample_counts,
        sample_spacing=sample_spacing,
    )
    destination_first_sample = (
        grid.first_sample_position[0] + destination_shift[0],
        grid.first_sample_position[1] + destination_shift[1],
    )
    destination_grid = SpatialGrid(
        sample_counts=sample_counts,
        sample_spacing=sample_spacing,
        first_sample_position=destination_first_sample,
        orientation=grid.orientation,
    )
    root = _build_root(
        grid=grid,
        destination_grid=destination_grid,
        wavelength=wavelength,
        aperture_diameter=aperture_diameter,
        axial_distance=axial_distance,
    )
    workstation.host(root)
    outputs, _record = workstation.run(
        _calculate,
        root=root,
        inputs=partial(_inputs, grid=grid),
    )
    intensity = cast(Intensity, outputs["propagated_intensity"])
    return ScalarAngularSpectrumPropagationResult(
        sample_counts=sample_counts,
        wavelength=wavelength,
        axial_distance=axial_distance,
        destination_shift=destination_shift,
        destination_first_sample=(
            float(
                intensity.grid.first_sample_position[0].detach().cpu(),
            ),
            float(
                intensity.grid.first_sample_position[1].detach().cpu(),
            ),
        ),
        peak_intensity=float(intensity.values.max().item()),
        mean_intensity=float(intensity.values.mean().item()),
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
        description=(
            "Propagate a scalar field to a shifted destination grid "
            "with the angular-spectrum method on a CPU."
        ),
    )
    parser.add_argument(
        "--sample-counts",
        type=_positive_integer,
        nargs=2,
        default=(48, 48),
    )
    parser.add_argument(
        "--sample-spacing",
        type=_positive_float,
        nargs=2,
        default=(2.0 * MICROMETRE, 2.0 * MICROMETRE),
    )
    parser.add_argument(
        "--wavelength",
        type=_positive_float,
        default=0.5 * MICROMETRE,
    )
    parser.add_argument(
        "--aperture-diameter",
        type=_positive_float,
        default=48.0 * MICROMETRE,
    )
    parser.add_argument(
        "--axial-distance",
        type=float,
        default=0.4 * MILLIMETRE,
        help="Signed SI metres.",
    )
    parser.add_argument(
        "--destination-shift",
        type=float,
        nargs=2,
        default=(8.0 * MICROMETRE, -6.0 * MICROMETRE),
        help="Signed SI metres along (y, x).",
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
        axial_distance=parsed.axial_distance,
        destination_shift=tuple(parsed.destination_shift),
    )
    print(
        "Scalar angular spectrum: "
        f"distance={result.axial_distance / MILLIMETRE:.3f} mm, "
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

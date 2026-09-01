# 线偏振平面波光强教学案例。

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
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.source import PlaneWave

MICROMETRE = 1.0e-6


@dataclass(frozen=True, slots=True)
class PlaneWaveIntensityResult:
    """
    保存平面波观测的少量可序列化摘要
    """

    sample_counts: tuple[int, int]
    wavelength: float
    polarization_components: tuple[
        tuple[float, float],
        tuple[float, float],
    ]
    mean_intensity: float
    workstation_device: str


def _build_root(
    *,
    grid: SpatialGrid,
    wavelength: float,
    relative_amplitude: float,
) -> torch.nn.ModuleDict:
    # 平面波观测的托管组件根。
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=wavelength),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=relative_amplitude,
    )
    detector = IntensityDetection()
    return torch.nn.ModuleDict(
        {
            "source": source,
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
) -> Mapping[str, Intensity]:
    field = root["source"](grid)
    intensity = root["detector"](field)
    return {"intensity": intensity}


def run(
    *,
    workstation: Workstation,
    sample_counts: tuple[int, int] = (32, 32),
    sample_spacing: tuple[float, float] = (
        1.0 * MICROMETRE,
        1.0 * MICROMETRE,
    ),
    wavelength: float = 0.5 * MICROMETRE,
    relative_amplitude: float = 1.0,
) -> PlaneWaveIntensityResult:
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
        relative_amplitude=relative_amplitude,
    )
    workstation.host(root)
    outputs, _record = workstation.run(
        _calculate,
        root=root,
        inputs=partial(_inputs, grid=grid),
    )
    intensity = cast(Intensity, outputs["intensity"])
    polarization = Polarization.linear_x()
    components = tuple(
        (component.real, component.imag)
        for component in polarization.components
    )
    return PlaneWaveIntensityResult(
        sample_counts=sample_counts,
        wavelength=wavelength,
        polarization_components=(components[0], components[1]),
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
        description="Observe a linearly polarized plane wave on a CPU.",
    )
    parser.add_argument(
        "--sample-counts",
        type=_positive_integer,
        nargs=2,
        default=(32, 32),
    )
    parser.add_argument(
        "--sample-spacing",
        type=_positive_float,
        nargs=2,
        default=(1.0 * MICROMETRE, 1.0 * MICROMETRE),
        help="SI metres along (y, x).",
    )
    parser.add_argument(
        "--wavelength",
        type=_positive_float,
        default=0.5 * MICROMETRE,
        help="SI metres.",
    )
    parser.add_argument(
        "--relative-amplitude",
        type=_positive_float,
        default=1.0,
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
        relative_amplitude=parsed.relative_amplitude,
    )
    print(
        "Plane wave: "
        f"wavelength={result.wavelength / MICROMETRE:.3f} um, "
        f"mean intensity={result.mean_intensity:.6f}"
    )
    if parsed.output is not None:
        parsed.output.write_text(
            json.dumps(asdict(result), indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

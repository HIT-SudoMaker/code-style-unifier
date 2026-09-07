from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
from numbers import Integral, Real

import numpy as np

from experiments.restoration.errors import invalid_restoration_contract


@dataclass(frozen=True, slots=True)
class ResolutionTarget:
    """
    定义分辨率靶标数据结构
    """
    image: np.ndarray
    metadata: dict[str, object]


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    numeric_value = int(value)
    if numeric_value <= 0:
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    return numeric_value


def _validate_resolution(resolution: object) -> tuple[int, int]:
    if (
        isinstance(resolution, (str, bytes))
        or not isinstance(resolution, Sequence)
        or len(resolution) != 2
    ):
        raise invalid_restoration_contract("resolution must have height and width")
    return (
        _positive_integer("resolution[0]", resolution[0]),
        _positive_integer("resolution[1]", resolution[1]),
    )


def _finite_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    return numeric_value


def _normalize(image: np.ndarray) -> np.ndarray:
    normalized = np.asarray(image, dtype=np.float32)
    minimum = float(np.min(normalized))
    maximum = float(np.max(normalized))
    if maximum == minimum:
        return np.zeros_like(normalized, dtype=np.float32)
    return ((normalized - minimum) / (maximum - minimum)).astype(np.float32)


def point_grid(resolution: tuple[int, int]) -> ResolutionTarget:
    """
    实现分辨率靶标辅助逻辑
    """
    height, width = _validate_resolution(resolution)
    image = np.zeros((height, width), dtype=np.float32)
    image[height // 2, width // 2] = 1.0
    return ResolutionTarget(
        image=image,
        metadata={
            "target_name": "point_grid",
            "target_variant": "center",
            "resolution": (height, width),
        },
    )


def slanted_edge(
    resolution: tuple[int, int],
    *,
    angle_degrees: float = 5.0,
) -> ResolutionTarget:
    """
    实现分辨率靶标辅助逻辑
    """
    height, width = _validate_resolution(resolution)
    angle = _finite_real("angle_degrees", angle_degrees)
    coordinate_y = np.linspace(-0.5, 0.5, height, dtype=np.float32)
    coordinate_x = np.linspace(-0.5, 0.5, width, dtype=np.float32)
    grid_y, grid_x = np.meshgrid(coordinate_y, coordinate_x, indexing="ij")
    angle_radians = math.radians(angle)
    signed_distance = grid_x * math.cos(angle_radians) + grid_y * math.sin(angle_radians)
    image = (signed_distance >= 0.0).astype(np.float32)
    return ResolutionTarget(
        image=_normalize(image),
        metadata={
            "target_name": "slanted_edge",
            "target_variant": f"{angle:g}_degrees",
            "angle_degrees": angle,
            "resolution": (height, width),
        },
    )


def sinusoidal_grating(
    resolution: tuple[int, int],
    *,
    cycles_per_image: int,
) -> ResolutionTarget:
    """
    实现分辨率靶标辅助逻辑
    """
    height, width = _validate_resolution(resolution)
    cycles = _positive_integer("cycles_per_image", cycles_per_image)
    if cycles >= width / 2:
        raise invalid_restoration_contract(
            "cycles_per_image must be less than half the image width"
        )
    coordinate_x = np.arange(width, dtype=np.float32) / np.float32(width)
    grating = 0.5 + 0.5 * np.sin(np.float32(2.0 * math.pi * cycles) * coordinate_x)
    image = np.tile(grating, (height, 1)).astype(np.float32)
    return ResolutionTarget(
        image=_normalize(image),
        metadata={
            "target_name": "sinusoidal_gratings",
            "target_variant": f"{cycles}_cycles",
            "cycles_per_image": cycles,
            "resolution": (height, width),
        },
    )


def _default_grating_cycles(width: int) -> list[int]:
    max_safe_cycle = (width - 1) // 2
    if max_safe_cycle < 1:
        raise invalid_restoration_contract(
            "resolution width must support at least one sinusoidal cycle"
        )
    frequency_fractions = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40)
    cycles = [
        min(max_safe_cycle, max(1, int(round(width * fraction))))
        for fraction in frequency_fractions
    ]
    if len(set(cycles)) < 2:
        cycles = [1, max_safe_cycle]
    return list(dict.fromkeys(cycles))


def usaf_bars(resolution: tuple[int, int]) -> ResolutionTarget:
    """
    实现分辨率靶标辅助逻辑
    """
    height, width = _validate_resolution(resolution)
    image = np.zeros((height, width), dtype=np.float32)
    bands = (
        (0, width // 3, 2),
        (width // 3, 2 * width // 3, 4),
        (2 * width // 3, width, 8),
    )
    for start, stop, period in bands:
        if start >= stop:
            continue
        local_x = np.arange(stop - start)
        image[:, start:stop] = ((local_x // max(1, period)) % 2).astype(np.float32)
    return ResolutionTarget(
        image=_normalize(image),
        metadata={
            "target_name": "usaf_bars",
            "target_variant": "three_frequency_bars",
            "resolution": (height, width),
        },
    )


def siemens_star(
    resolution: tuple[int, int],
    *,
    spokes: int | None = None,
) -> ResolutionTarget:
    """
    实现分辨率靶标辅助逻辑
    """
    height, width = _validate_resolution(resolution)
    if spokes is None:
        spoke_count = min(32, min(height, width))
        if spoke_count % 2 != 0:
            spoke_count -= 1
    else:
        spoke_count = _positive_integer("spokes", spokes)
    if spoke_count < 2:
        raise invalid_restoration_contract("spokes must be at least 2")
    if spoke_count % 2 != 0:
        raise invalid_restoration_contract("spokes must be even")
    if spoke_count > min(height, width):
        raise invalid_restoration_contract(
            "spokes must be resolvable for the image size"
        )
    coordinate_y = np.linspace(-1.0, 1.0, height, dtype=np.float32)
    coordinate_x = np.linspace(-1.0, 1.0, width, dtype=np.float32)
    grid_y, grid_x = np.meshgrid(coordinate_y, coordinate_x, indexing="ij")
    angle = np.arctan2(grid_y, grid_x)
    image = (np.cos(angle * (spoke_count / 2.0)) >= 0.0).astype(np.float32)
    return ResolutionTarget(
        image=_normalize(image),
        metadata={
            "target_name": "siemens_star",
            "target_variant": f"{spoke_count}_spokes",
            "spokes": spoke_count,
            "resolution": (height, width),
        },
    )


def build_resolution_targets(resolution: tuple[int, int]) -> list[ResolutionTarget]:
    """
    构建分辨率靶标产物
    """
    validated_resolution = _validate_resolution(resolution)
    _, width = validated_resolution
    gratings = [
        sinusoidal_grating(validated_resolution, cycles_per_image=cycles)
        for cycles in _default_grating_cycles(width)
    ]
    return [
        point_grid(validated_resolution),
        slanted_edge(validated_resolution),
        *gratings,
        usaf_bars(validated_resolution),
        siemens_star(validated_resolution),
    ]

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

NormalizationMethod: TypeAlias = Literal[
    "auto",
    "uint8",
    "uint16",
    "min_max",
    "percentile",
    "none",
]
ResizeMethod: TypeAlias = Literal["nearest", "bilinear", "bicubic"]
EncodingMethod: TypeAlias = Literal["intensity", "phase"]


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Select a registered data source."""

    dataset_name: str
    dataset_root: str | Path | None = None
    is_train: bool = True
    samples_per_class: int | None = None
    max_samples: int | None = None
    random_seed: int = 42


@dataclass(frozen=True, slots=True)
class PreparationConfig:
    """Configure normalization, resizing, padding, and edge tapering."""

    image_resolution: tuple[int, int] = (64, 64)
    array_resolution: tuple[int, int] = (128, 128)
    normalization_method: NormalizationMethod = "auto"
    resize_interpolation_method: ResizeMethod = "nearest"
    edge_taper_width: int = 0


@dataclass(frozen=True, slots=True)
class EncodingConfig:
    """Configure conversion from an image to a complex optical field."""

    encoding_method: EncodingMethod = "intensity"

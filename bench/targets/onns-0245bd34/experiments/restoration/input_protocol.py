from __future__ import annotations

from pathlib import Path
from typing import Final

from data.configs import EncodingConfig, PreparationConfig, SourceConfig


RESTORATION_IMAGE_RESOLUTION: Final[tuple[int, int]] = (256, 256)
RESTORATION_ARRAY_RESOLUTION: Final[tuple[int, int]] = (512, 512)
RESTORATION_RANDOM_SEED: Final[int] = 2026

STANDARD_RESTORATION_PREPARATION: Final[PreparationConfig] = PreparationConfig(
    image_resolution=RESTORATION_IMAGE_RESOLUTION,
    array_resolution=RESTORATION_ARRAY_RESOLUTION,
    normalization_method="auto",
    resize_interpolation_method="bilinear",
    edge_taper_width=0,
)
STANDARD_RESTORATION_ENCODING: Final[EncodingConfig] = EncodingConfig(
    encoding_method="intensity"
)


def build_restoration_source(
    dataset_root: str | Path | None = "data/raw",
) -> SourceConfig:
    """Build the source contract shared by Fixed and Adaptive experiments."""
    return SourceConfig(
        dataset_name="fmd",
        dataset_root=dataset_root,
        is_train=True,
        random_seed=RESTORATION_RANDOM_SEED,
    )

from __future__ import annotations

from torch.utils.data import Dataset

from data.configs import PreparationConfig
from data.configs.validation import validate_preparation
from data.preparation.dataset import PreparedDataset
from data.preparation.normalize import normalize_image
from data.preparation.resize import resize_image


def prepare(source: Dataset, config: PreparationConfig) -> PreparedDataset:
    """
    对数据集应用图像准备阶段。
    """
    if not isinstance(config, PreparationConfig):
        raise TypeError("config must be a PreparationConfig")
    validate_preparation(config)
    return PreparedDataset(
        source_dataset=source,
        image_resolution=config.image_resolution,
        array_resolution=config.array_resolution,
        normalization_method=config.normalization_method,
        resize_interpolation_method=config.resize_interpolation_method,
        edge_taper_width=config.edge_taper_width,
    )


__all__ = [
    "PreparedDataset",
    "normalize_image",
    "prepare",
    "resize_image",
]

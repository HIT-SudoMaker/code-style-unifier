from __future__ import annotations

from torch.utils.data import Dataset

from data.configs import EncodingConfig
from data.configs.validation import validate_encoding
from data.encoding.dataset import EncodedDataset
from data.encoding.optical_encode import encode_image_to_field


def encode(source: Dataset, config: EncodingConfig) -> EncodedDataset:
    """
    将图像数据集编码为光学输入场。
    """
    if not isinstance(config, EncodingConfig):
        raise TypeError("config must be an EncodingConfig")
    validate_encoding(config)
    return EncodedDataset(
        source_dataset=source,
        encoding_method=config.encoding_method,
    )


__all__ = [
    "EncodedDataset",
    "encode",
    "encode_image_to_field",
]

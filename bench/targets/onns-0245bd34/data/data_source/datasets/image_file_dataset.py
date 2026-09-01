from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PIL import Image
import numpy as np
import torch
from torch.utils.data import Dataset

from data.data_source.indexing.file_index import FileIndexRecord
from data.data_source.types import ChannelPolicy
from data.types import RawSample


class ImageFileDataset(Dataset):
    """
    基于文件索引记录读取原始图像样本的数据集
    """

    def __init__(
        self,
        *,
        dataset_root: str | Path,
        records: Sequence[FileIndexRecord],
        channel_policy: ChannelPolicy = "single",
    ) -> None:
        """
        文件图像数据集

        Args:
            dataset_root:   图像记录source_path的根目录
            records:        文件索引记录序列
            channel_policy: 彩色输入的处理策略

        Raises:
            ValueError: 当通道策略不受支持时抛出
        """
        super().__init__()
        if channel_policy not in {"single", "luminance"}:
            raise ValueError(
                f"不支持的channel_policy: {channel_policy}"
            )
        self.dataset_root = Path(dataset_root)
        self.records = list(records)
        self.channel_policy = channel_policy

    def __len__(self) -> int:
        """
        返回文件索引记录数量
        """
        return len(self.records)

    def __getitem__(self, index: int) -> RawSample:
        """
        读取指定索引的原始图像样本

        Args:
            index: 文件索引记录位置

        Returns:
            包含单通道图像张量和扩展来源信息的原始样本
        """
        record = self.records[index]
        image_array = self._read_single_channel(self.dataset_root / record.source_path)
        return {
            "image": torch.from_numpy(image_array).unsqueeze(0),
            "label": int(record.label),
            "category": record.category,
            "provenance": {
                "dataset_name": record.dataset_name,
                "split_name": record.split_name,
                "image_id": record.image_id,
                "source_index": int(record.source_index),
                "sampled_index": int(index),
                "source_path": record.source_path.as_posix(),
                "raw_resolution": tuple(image_array.shape),
                "provenance_url": record.provenance_url,
                "license": record.license_name,
                "source_metadata": dict(record.source_metadata),
            },
        }

    def _read_single_channel(self, path: Path) -> np.ndarray:
        with Image.open(path) as image:
            if image.mode in {"I;16", "I;16B", "I;16L"}:
                array = np.asarray(image, dtype=np.uint16)
            elif image.mode in {"1", "I", "F", "L", "P"}:
                array = np.asarray(image.convert("F"), dtype=np.float32)
            elif self.channel_policy == "luminance":
                array = np.asarray(image.convert("L"), dtype=np.float32)
            else:
                raise ValueError(
                    "ImageFileDataset仅接受单通道图像; "
                    "如需处理彩色图像请将channel_policy设为luminance"
                )
        if array.ndim != 2:
            raise ValueError(
                f"ImageFileDataset要求单通道二维数据，实际形状为: {array.shape}"
            )
        return np.array(array, copy=True)

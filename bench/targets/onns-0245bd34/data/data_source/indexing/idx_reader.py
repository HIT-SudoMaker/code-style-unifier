from __future__ import annotations

import gzip
from pathlib import Path
import struct
from typing import BinaryIO

import numpy as np


def read_idx_file(path: Path) -> np.ndarray:
    """
    读取IDX格式文件，支持gzip压缩

    Args:
        path: IDX文件路径，支持.gz后缀自动解压

    Returns:
        解析后的numpy数组

    Raises:
        ValueError: 当IDX数据类型不受支持时抛出
    """
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as file_handle:
            return _read_idx_stream(file_handle)
    with path.open("rb") as file_handle:
        return _read_idx_stream(file_handle)


def _read_idx_stream(file_handle: BinaryIO) -> np.ndarray:
    magic = struct.unpack(">I", file_handle.read(4))[0]
    data_type = (magic >> 8) & 0xFF
    num_dimensions = magic & 0xFF

    if data_type != 0x08:
        raise ValueError(
            "不支持的IDX数据类型"
        )

    dimensions = [
        struct.unpack(">I", file_handle.read(4))[0]
        for _ in range(num_dimensions)
    ]
    data = np.frombuffer(file_handle.read(), dtype=np.uint8)
    return data.reshape(dimensions)


class RawIDXVisionDataset:
    """
    IDX格式原始视觉数据集

    输入契约为IDX3-ubyte图像文件和IDX1-ubyte标签文件
    """

    def __init__(self, *, root: str, dataset_dir: str, is_train: bool) -> None:
        """
        IDX数据集

        Args:
            root:        数据集根目录
            dataset_dir: 数据集子目录名，如MNIST
            is_train:    是否为训练集

        Raises:
            FileNotFoundError: 当图像文件或标签文件缺失时抛出
        """
        split = "train" if is_train else "t10k"
        raw_root = Path(root) / dataset_dir / "raw"
        image_path = raw_root / f"{split}-images-idx3-ubyte"
        image_gz_path = raw_root / f"{split}-images-idx3-ubyte.gz"
        label_path = raw_root / f"{split}-labels-idx1-ubyte"
        label_gz_path = raw_root / f"{split}-labels-idx1-ubyte.gz"

        if image_path.exists():
            self.images = read_idx_file(image_path)
        elif image_gz_path.exists():
            self.images = read_idx_file(image_gz_path)
        else:
            raise FileNotFoundError(
                f"缺少图像文件: {dataset_dir}/{split}"
            )

        if label_path.exists():
            self.targets = read_idx_file(label_path)
        elif label_gz_path.exists():
            self.targets = read_idx_file(label_gz_path)
        else:
            raise FileNotFoundError(
                f"缺少标签文件: {dataset_dir}/{split}"
            )

    def __len__(self) -> int:
        """
        返回样本数量
        """
        return len(self.targets)

    def __getitem__(self, index: int) -> tuple[np.ndarray, int]:
        """
        获取指定索引的样本

        Args:
            index: 样本索引

        Returns:
            图像数组与标签整数组成的元组
        """
        return self.images[index], int(self.targets[index])

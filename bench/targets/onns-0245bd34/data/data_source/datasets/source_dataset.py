from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, TYPE_CHECKING, TypeAlias

import numpy as np
import torch
from torch.utils.data import Dataset

from data._validation import validate_label_index, validate_optional_positive_int
from data.data_source.indexing.sampling import build_stratified_indices
from data.types import RawSample

if TYPE_CHECKING:
    from PIL import Image

    _RawImage: TypeAlias = np.ndarray | Image.Image
else:
    _RawImage: TypeAlias = np.ndarray


class RawVisionDataset(Protocol):
    """
    原始视觉数据集协议

    Attributes:
        targets: 数据集标签序列
    """
    targets: Sequence[int] | np.ndarray

    def __len__(self) -> int:
        """
        返回原始样本总数
        """
        ...

    def __getitem__(self, index: int) -> tuple[_RawImage, int]:
        """
        返回指定索引的原始图像与标签
        """
        ...


class SourceImageDataset(Dataset):
    """
    图像源数据集基类
    """
    def __init__(
        self,
        *,
        raw_dataset: RawVisionDataset,
        class_names: list[str],
        dataset_name: str = "unknown",
        split_name: str = "unknown",
        samples_per_class: int | None,
        max_samples: int | None = None,
        random_seed: int = 42,
        provenance_url: str = "unknown",
        license_name: str = "unknown",
        source_metadata: Mapping[str, object] | None = None,
    ) -> None:
        """
        原始视觉数据集适配器

        Args:
            raw_dataset:       带targets字段的原始视觉数据集
            class_names:       按标签顺序排列的类别名称
            dataset_name:      写入provenance的数据集标识
            split_name:        写入provenance的数据划分标识
            samples_per_class: 每类分层采样数量，None表示不分层采样
            max_samples:       最大总采样数，None表示保留全部样本
            random_seed:       确定性采样随机种子
            provenance_url:    数据来源URL
            license_name:      数据许可名称
            source_metadata:   数据源补充元数据
        """
        super().__init__()
        self.raw_dataset = raw_dataset
        self.class_names = list(class_names)
        self.dataset_name = dataset_name
        self.split_name = split_name
        self.random_seed = random_seed
        self.provenance_url = provenance_url
        self.license_name = license_name
        self.source_metadata = dict(source_metadata or {})
        self.is_stratified_sampled = samples_per_class is not None
        self.sampled_indices = build_stratified_indices(
            targets=self.raw_dataset.targets,
            num_classes=len(self.class_names),
            samples_per_class=samples_per_class,
            random_seed=random_seed,
        )
        if max_samples is not None:
            validate_optional_positive_int("max_samples", max_samples)
            self.sampled_indices = self.sampled_indices[: int(max_samples)]

    def __len__(self) -> int:
        """
        返回采样后的样本总数
        """
        return len(self.sampled_indices)

    def __getitem__(self, index: int) -> RawSample:
        """
        根据索引获取源样本

        Args:
            index: 采样后数据集中的样本索引

        Returns:
            包含图像、标签、类别与来源信息的源样本

        Raises:
            ValueError: 当原始图像不是单通道二维数组时抛出
        """
        source_index = int(self.sampled_indices[index])
        raw_image, raw_label = self.raw_dataset[source_index]
        image_array = self._require_single_channel(raw_image)
        label = validate_label_index(
            int(raw_label),
            len(self.class_names),
            dataset_name=self.dataset_name,
        )
        return {
            "image": torch.from_numpy(image_array).unsqueeze(0),
            "label": label,
            "category": self.class_names[label],
            "provenance": {
                "dataset_name": self.dataset_name,
                "split_name": self.split_name,
                "image_id": f"{self.dataset_name}/{self.split_name}/{source_index}",
                "source_index": source_index,
                "sampled_index": int(index),
                "source_path": f"{self.split_name}/{source_index}",
                "provenance_url": self.provenance_url,
                "license": self.license_name,
                "source_metadata": dict(self.source_metadata),
                "sampling_seed": self.random_seed,
                "is_stratified_sampled": self.is_stratified_sampled,
                "raw_resolution": tuple(image_array.shape),
            },
        }

    def _require_single_channel(self, raw_image: _RawImage) -> np.ndarray:
        image_array = np.asarray(raw_image)
        if image_array.ndim == 3 and image_array.shape[0] == 1:
            image_array = image_array[0]
        if image_array.ndim != 2:
            raise ValueError(
                "data_source仅接受单通道原始图像; "
                f"收到形状 {image_array.shape}"
            )
        return image_array.astype(np.float32, copy=False)

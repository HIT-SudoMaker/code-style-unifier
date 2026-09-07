from __future__ import annotations

import torch
from torch.utils.data import Dataset

from data._sample_conversions import copy_provenance, to_numpy_image
from data.configs.stages import NormalizationMethod, ResizeMethod
from data.preparation.normalize import normalize_image
from data.preparation.resize import resize_image
from data.types import PreparedSample, RawSample


class PreparedDataset(Dataset):
    """
    对原始光学图像执行预处理的数据集包装器
    """

    def __init__(
        self,
        *,
        source_dataset: Dataset,
        image_resolution: tuple[int, int],
        array_resolution: tuple[int, int],
        normalization_method: NormalizationMethod = "auto",
        resize_interpolation_method: ResizeMethod = "nearest",
        edge_taper_width: int = 0,
    ) -> None:
        """
        预处理数据集包装器

        Args:
            source_dataset:              返回原始样本的源数据集
            image_resolution:            目标图像支撑分辨率
            array_resolution:            目标光学阵列分辨率
            normalization_method:        图像归一化策略
            resize_interpolation_method: 缩放插值策略
            edge_taper_width:            缩放后支撑区域内的边缘切趾宽度
        """
        self.source_dataset = source_dataset
        self.image_resolution = image_resolution
        self.array_resolution = array_resolution
        self.normalization_method = normalization_method
        self.resize_interpolation_method = resize_interpolation_method
        self.edge_taper_width = edge_taper_width

    def __len__(self) -> int:
        """
        返回源数据集的样本数量
        """
        return len(self.source_dataset)

    def __getitem__(self, index: int) -> PreparedSample:
        """
        返回预处理后的样本

        Args:
            index: 样本索引

        Returns:
            预处理后的图像、标签、类别与来源信息
        """
        raw_sample: RawSample = self.source_dataset[index]
        normalized_image = normalize_image(
            image=to_numpy_image(raw_sample["image"], context_name="PreparedDataset"),
            normalization_method=self.normalization_method,
        )
        prepared_image = resize_image(
            image=normalized_image,
            image_resolution=self.image_resolution,
            array_resolution=self.array_resolution,
            interpolation_method=self.resize_interpolation_method,
            edge_taper_width=self.edge_taper_width,
        )

        provenance = copy_provenance(raw_sample["provenance"])
        provenance["stage"] = "prepared"
        provenance["preparation"] = {
            "image_resolution": self.image_resolution,
            "array_resolution": self.array_resolution,
            "normalization_method": self.normalization_method,
            "resize_interpolation_method": self.resize_interpolation_method,
            "edge_taper_width": self.edge_taper_width,
        }

        return {
            "image": torch.from_numpy(prepared_image).unsqueeze(0),
            "label": int(raw_sample["label"]),
            "category": str(raw_sample["category"]),
            "provenance": provenance,
        }

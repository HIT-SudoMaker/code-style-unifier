from __future__ import annotations

from data.data_source.datasets.image_file_dataset import ImageFileDataset
from data.data_source.indexing.file_sources import build_file_source_records


class FMDDataset(ImageFileDataset):
    """
    FMD平均图像文件数据集
    """

    def __init__(
        self,
        dataset_root: str | None = None,
        is_train: bool = True,
        max_samples: int | None = None,
        random_seed: int = 42,
    ) -> None:
        """
        FMD平均图像数据集

        Args:
            dataset_root: 数据集根目录，None时按默认规则解析
            is_train:     是否构建训练集
            max_samples:  最大样本数，None表示不限制
            random_seed:  采样随机种子
        """
        source_root, records, channel_policy = build_file_source_records(
            source_name="fmd",
            dataset_root=dataset_root,
            is_train=is_train,
            max_samples=max_samples,
            random_seed=random_seed,
        )
        super().__init__(
            dataset_root=source_root,
            records=records,
            channel_policy=channel_policy,
        )

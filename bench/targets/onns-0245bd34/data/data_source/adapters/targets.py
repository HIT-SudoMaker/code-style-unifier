from __future__ import annotations

from pathlib import Path

from data.data_source.assets.organizers import prepare_generated_target_assets
from data.data_source.dataset_root import resolve_dataset_root
from data.data_source.datasets.image_file_dataset import ImageFileDataset
from data.data_source.indexing.file_index import FileIndexRecord
from data.data_source.indexing.file_sources import build_file_source_records
from data.data_source.types import ChannelPolicy


class TargetUSAFDataset(ImageFileDataset):
    """
    确定性USAF靶标数据集
    """

    def __init__(
        self,
        dataset_root: str | None = None,
        is_train: bool = True,
        max_samples: int | None = None,
        random_seed: int = 42,
    ) -> None:
        """
        USAF靶标数据集

        Args:
            dataset_root: 数据集根目录，None时按默认规则解析
            is_train:     是否构建训练集
            max_samples:  最大样本数，None表示不限制
            random_seed:  采样随机种子
        """
        source_root, records, channel_policy = _build_target_file_source(
            dataset_root=dataset_root,
            target_asset_id="target_usaf",
            is_train=is_train,
            max_samples=max_samples,
            random_seed=random_seed,
        )
        super().__init__(
            dataset_root=source_root,
            records=records,
            channel_policy=channel_policy,
        )


class TargetSiemensDataset(ImageFileDataset):
    """
    确定性Siemens星形靶标数据集
    """

    def __init__(
        self,
        dataset_root: str | None = None,
        is_train: bool = True,
        max_samples: int | None = None,
        random_seed: int = 42,
    ) -> None:
        """
        Siemens星形靶标数据集

        Args:
            dataset_root: 数据集根目录，None时按默认规则解析
            is_train:     是否构建训练集
            max_samples:  最大样本数，None表示不限制
            random_seed:  采样随机种子
        """
        source_root, records, channel_policy = _build_target_file_source(
            dataset_root=dataset_root,
            target_asset_id="target_siemens",
            is_train=is_train,
            max_samples=max_samples,
            random_seed=random_seed,
        )
        super().__init__(
            dataset_root=source_root,
            records=records,
            channel_policy=channel_policy,
        )


class TargetSlantedEdgeDataset(ImageFileDataset):
    """
    确定性斜边靶标数据集
    """

    def __init__(
        self,
        dataset_root: str | None = None,
        is_train: bool = True,
        max_samples: int | None = None,
        random_seed: int = 42,
    ) -> None:
        """
        斜边靶标数据集

        Args:
            dataset_root: 数据集根目录，None时按默认规则解析
            is_train:     是否构建训练集
            max_samples:  最大样本数，None表示不限制
            random_seed:  采样随机种子
        """
        source_root, records, channel_policy = _build_target_file_source(
            dataset_root=dataset_root,
            target_asset_id="target_slanted_edge",
            is_train=is_train,
            max_samples=max_samples,
            random_seed=random_seed,
        )
        super().__init__(
            dataset_root=source_root,
            records=records,
            channel_policy=channel_policy,
        )


class TargetLinePairsDataset(ImageFileDataset):
    """
    确定性线对靶标数据集
    """

    def __init__(
        self,
        dataset_root: str | None = None,
        is_train: bool = True,
        max_samples: int | None = None,
        random_seed: int = 42,
    ) -> None:
        """
        线对靶标数据集

        Args:
            dataset_root: 数据集根目录，None时按默认规则解析
            is_train:     是否构建训练集
            max_samples:  最大样本数，None表示不限制
            random_seed:  采样随机种子
        """
        source_root, records, channel_policy = _build_target_file_source(
            dataset_root=dataset_root,
            target_asset_id="target_line_pairs",
            is_train=is_train,
            max_samples=max_samples,
            random_seed=random_seed,
        )
        super().__init__(
            dataset_root=source_root,
            records=records,
            channel_policy=channel_policy,
        )


def _build_target_file_source(
    *,
    dataset_root: str | None,
    target_asset_id: str,
    is_train: bool,
    max_samples: int | None,
    random_seed: int,
) -> tuple[Path, list[FileIndexRecord], ChannelPolicy]:
    resolved_dataset_root = Path(resolve_dataset_root(dataset_root))
    prepare_generated_target_assets(dataset_root=resolved_dataset_root)
    return build_file_source_records(
        source_name=target_asset_id,
        dataset_root=resolved_dataset_root,
        is_train=is_train,
        max_samples=max_samples,
        random_seed=random_seed,
    )

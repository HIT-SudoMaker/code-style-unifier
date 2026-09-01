from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from data.data_source.dataset_root import resolve_dataset_root

BIOSR_SOURCE_URL = "https://figshare.com/articles/dataset/BioSR/13264793"
FMD_SOURCE_URL = (
    "https://curate.nd.edu/articles/dataset/"
    "Fluorescence_Microscopy_Denoising_FMD_dataset/24744648"
)
BBBC038_SOURCE_URL = "https://bbbc.broadinstitute.org/BBBC038"
BBBC038_STAGE1_TRAIN_URL = "https://data.broadinstitute.org/bbbc/BBBC038/stage1_train.zip"
BBBC039_SOURCE_URL = "https://bbbc.broadinstitute.org/BBBC039"
BBBC039_IMAGES_URL = "https://data.broadinstitute.org/bbbc/BBBC039/images.zip"

BIOSR_ARCHIVE_URLS: dict[str, str] = {
    "Microtubules.zip": "https://ndownloader.figshare.com/files/25714514",
    "CCPs.zip": "https://ndownloader.figshare.com/files/25714583",
    "ER.zip": "https://ndownloader.figshare.com/files/25714658",
    "F-actin_Nonlinear.zip": "https://ndownloader.figshare.com/files/25714772",
    "F-actin.zip": "https://ndownloader.figshare.com/files/25944599",
}

FMD_ARCHIVE_URLS: dict[str, str] = {
    "Confocal_BPAE_B.tar": "https://ndownloader.figshare.com/files/43648062",
    "Confocal_BPAE_G.tar": "https://ndownloader.figshare.com/files/43648065",
    "Confocal_BPAE_R.tar": "https://ndownloader.figshare.com/files/43648071",
    "Confocal_FISH.tar": "https://ndownloader.figshare.com/files/43648074",
    "Confocal_MICE.tar": "https://ndownloader.figshare.com/files/43648080",
    "TwoPhoton_BPAE_B.tar": "https://ndownloader.figshare.com/files/43648086",
    "TwoPhoton_BPAE_G.tar": "https://ndownloader.figshare.com/files/43648089",
    "TwoPhoton_BPAE_R.tar": "https://ndownloader.figshare.com/files/43648092",
    "TwoPhoton_MICE.tar": "https://ndownloader.figshare.com/files/43648095",
    "WideField_BPAE_B.tar": "https://ndownloader.figshare.com/files/43648098",
    "WideField_BPAE_G.tar": "https://ndownloader.figshare.com/files/43648113",
    "WideField_BPAE_R.tar": "https://ndownloader.figshare.com/files/43648116",
    "test_mix.tar": "https://ndownloader.figshare.com/files/43648128",
}

EXPECTED_RAW_DATASET_NAMES = (
    "mnist",
    "fashion_mnist",
    "biosr",
    "fmd",
    "bbbc038",
    "bbbc039",
    "targets",
)

# 资产API路径参数允许字符串、Path或None
PathInput: TypeAlias = str | Path | None
# 归档筛选列表使用None表示全部归档
ArchiveNames: TypeAlias = Sequence[str] | None
# 下载函数接收来源地址和目标路径
DownloadFunction: TypeAlias = Callable[[str, Path], None]


@dataclass(frozen=True)
class RawDatasetAsset:
    """
    统一原始数据资产目录契约

    Attributes:
        dataset_name: 数据集名称
        path_parts:   数据集资产相对目录片段
        source_url:   原始数据来源地址
        is_generated: 是否由项目确定性生成
    """

    dataset_name: str
    path_parts: tuple[str, ...]
    source_url: str
    is_generated: bool = False


@dataclass(frozen=True)
class RawDatasetAssetStatus:
    """
    统一原始数据资产本地状态

    Attributes:
        dataset_name:  数据集名称
        expected_path: 预期资产目录路径
        source_url:    原始数据来源地址
        is_ready:      本地资产目录是否存在
        is_generated:  是否由项目确定性生成
    """

    dataset_name: str
    expected_path: Path
    source_url: str
    is_ready: bool
    is_generated: bool = False


RAW_DATASET_ASSETS = (
    RawDatasetAsset("mnist", ("mnist",), "http://yann.lecun.com/exdb/mnist/"),
    RawDatasetAsset(
        "fashion_mnist",
        ("fashion_mnist",),
        "https://github.com/zalandoresearch/fashion-mnist",
    ),
    RawDatasetAsset("biosr", ("biosr", "clean"), BIOSR_SOURCE_URL),
    RawDatasetAsset("fmd", ("fmd", "averaged"), FMD_SOURCE_URL),
    RawDatasetAsset("bbbc038", ("bbbc038",), BBBC038_SOURCE_URL),
    RawDatasetAsset("bbbc039", ("bbbc039",), BBBC039_SOURCE_URL),
    RawDatasetAsset(
        "targets",
        ("targets",),
        "generated://deterministic-optical-targets",
        is_generated=True,
    ),
)


def inspect_raw_dataset_assets(dataset_root: PathInput = None) -> tuple[RawDatasetAssetStatus, ...]:
    """
    返回统一原始数据资产本地状态
    """
    root = Path(resolve_dataset_root(dataset_root))
    return tuple(
        RawDatasetAssetStatus(
            dataset_name=asset.dataset_name,
            expected_path=root.joinpath(*asset.path_parts),
            source_url=asset.source_url,
            is_ready=root.joinpath(*asset.path_parts).exists(),
            is_generated=asset.is_generated,
        )
        for asset in RAW_DATASET_ASSETS
    )

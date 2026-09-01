from __future__ import annotations

from dataclasses import dataclass, field

from torch.utils.data import Dataset

from data.configs import SourceConfig
from data.configs.validation import validate_source
from data.data_source.adapters.bbbc import BBBCDataset
from data.data_source.adapters.biosr import BioSRDataset
from data.data_source.adapters.fashion_mnist import BaseFashionMNISTDataset
from data.data_source.adapters.fmd import FMDDataset
from data.data_source.adapters.mnist import BaseMNISTDataset
from data.data_source.adapters.targets import (
    TargetLinePairsDataset,
    TargetSiemensDataset,
    TargetSlantedEdgeDataset,
    TargetUSAFDataset,
)
from data.data_source.dataset_root import resolve_dataset_root


@dataclass(frozen=True)
class RegistryEntry:
    """
    数据集构造注册项

    Attributes:
        builder:        数据集构造类
        default_kwargs: 注册表默认构造参数
    """

    builder: type
    default_kwargs: dict[str, object] = field(default_factory=dict)
    supports_class_sampling: bool = False


DATASET_REGISTRY: dict[str, RegistryEntry] = {
    "bbbc038": RegistryEntry(
        builder=BBBCDataset,
        default_kwargs={"accession": "BBBC038"},
    ),
    "bbbc039": RegistryEntry(
        builder=BBBCDataset,
        default_kwargs={"accession": "BBBC039"},
    ),
    "biosr": RegistryEntry(builder=BioSRDataset),
    "fashion_mnist": RegistryEntry(
        builder=BaseFashionMNISTDataset,
        supports_class_sampling=True,
    ),
    "fmd": RegistryEntry(builder=FMDDataset),
    "mnist": RegistryEntry(
        builder=BaseMNISTDataset,
        supports_class_sampling=True,
    ),
    "target_line_pairs": RegistryEntry(builder=TargetLinePairsDataset),
    "target_siemens": RegistryEntry(builder=TargetSiemensDataset),
    "target_slanted_edge": RegistryEntry(builder=TargetSlantedEdgeDataset),
    "target_usaf": RegistryEntry(builder=TargetUSAFDataset),
}


def resolve_dataset_entry(dataset_name: str) -> RegistryEntry:
    """
    返回指定公开数据集名称的注册页
    """
    try:
        return DATASET_REGISTRY[dataset_name]
    except KeyError as error:
        supported = ", ".join(sorted(DATASET_REGISTRY))
        raise ValueError(
            f"不支持的数据集名称: {dataset_name}; 可选值: {supported}"
        ) from error


def load(config: SourceConfig) -> Dataset:
    """
    按数据源配置加载原始样本。
    """
    if not isinstance(config, SourceConfig):
        raise TypeError("config must be a SourceConfig")
    validate_source(config)

    entry = resolve_dataset_entry(config.dataset_name)
    kwargs: dict[str, object] = {
        **entry.default_kwargs,
        "dataset_root": resolve_dataset_root(config.dataset_root),
        "is_train": config.is_train,
        "max_samples": config.max_samples,
        "random_seed": config.random_seed,
    }
    if entry.supports_class_sampling:
        kwargs["samples_per_class"] = config.samples_per_class
    return entry.builder(
        **{
            name: value
            for name, value in kwargs.items()
            if value is not None
        }
    )

from __future__ import annotations

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
from data.data_source.registry import (
    DATASET_REGISTRY,
    RegistryEntry,
    load,
    resolve_dataset_entry,
)

__all__ = [
    "BBBCDataset",
    "BioSRDataset",
    "DATASET_REGISTRY",
    "BaseFashionMNISTDataset",
    "BaseMNISTDataset",
    "FMDDataset",
    "RegistryEntry",
    "TargetLinePairsDataset",
    "TargetSiemensDataset",
    "TargetSlantedEdgeDataset",
    "TargetUSAFDataset",
    "load",
    "resolve_dataset_entry",
]

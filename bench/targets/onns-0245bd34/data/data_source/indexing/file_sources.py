from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from data.data_source.dataset_root import resolve_dataset_root
from data.data_source.indexing.file_index import (
    discover_image_files,
    FileIndexRecord,
    sample_max_indices,
    select_index_records,
)
from data.data_source.types import ChannelPolicy

RecordFilter = Callable[[FileIndexRecord], bool]


@dataclass(frozen=True)
class FileSourceSpec:
    """
    文件型原始数据源扫描契约

    Attributes:
        dataset_name:     数据集名称
        root_parts:       图像根目录相对片段
        category:         文件源类别
        provenance_url:   数据来源地址
        license_name:     数据许可名称
        source_metadata:  样本溯源附加元数据
        channel_policy:   通道处理策略
        record_filter:    文件记录过滤器
    """

    dataset_name: str
    root_parts: tuple[str, ...]
    category: str
    provenance_url: str
    license_name: str
    source_metadata: dict[str, object]
    channel_policy: ChannelPolicy = "single"
    record_filter: RecordFilter | None = None

def _target_file_record(target_file_name: str) -> RecordFilter:
    target_path = Path(target_file_name)
    return lambda record: record.source_path == target_path


FILE_SOURCE_SPECS: dict[str, FileSourceSpec] = {
    "biosr": FileSourceSpec(
        dataset_name="biosr",
        root_parts=("biosr", "clean"),
        category="biosr",
        provenance_url="https://figshare.com/articles/dataset/BioSR/13264793",
        license_name="CC BY 4.0",
        source_metadata={"clean_source": "clean", "official_split": False},
    ),
    "fmd": FileSourceSpec(
        dataset_name="fmd",
        root_parts=("fmd", "averaged"),
        category="fmd",
        provenance_url=(
            "https://curate.nd.edu/articles/dataset/"
            "Fluorescence_Microscopy_Denoising_FMD_dataset/24744648"
        ),
        license_name="CC BY-SA 4.0",
        source_metadata={"clean_source": "averaged", "official_split": False},
    ),
    "bbbc038": FileSourceSpec(
        dataset_name="bbbc038",
        root_parts=("bbbc038",),
        category="bbbc038",
        provenance_url="https://bbbc.broadinstitute.org/BBBC038",
        license_name="CC0",
        source_metadata={
            "collection_name": "Broad Bioimage Benchmark Collection",
            "accession": "BBBC038",
            "official_split": False,
        },
        channel_policy="luminance",
        record_filter=lambda record: (
            "__MACOSX" not in record.source_path.parts
            and not record.source_path.name.startswith("._")
            and "images" in record.source_path.parts
        ),
    ),
    "bbbc039": FileSourceSpec(
        dataset_name="bbbc039",
        root_parts=("bbbc039",),
        category="bbbc039",
        provenance_url="https://bbbc.broadinstitute.org/BBBC039",
        license_name="CC0",
        source_metadata={
            "collection_name": "Broad Bioimage Benchmark Collection",
            "accession": "BBBC039",
            "official_split": False,
        },
        channel_policy="luminance",
        record_filter=lambda record: (
            "__MACOSX" not in record.source_path.parts
            and not record.source_path.name.startswith("._")
            and record.source_path.parts[:1] == ("images",)
        ),
    ),
    "target_usaf": FileSourceSpec(
        dataset_name="target_usaf",
        root_parts=("targets",),
        category="target_usaf",
        provenance_url="generated://deterministic-optical-targets",
        license_name="project-generated",
        source_metadata={
            "target_type": "target_usaf",
            "generated": True,
            "official_split": False,
        },
        record_filter=_target_file_record("target_usaf.png"),
    ),
    "target_siemens": FileSourceSpec(
        dataset_name="target_siemens",
        root_parts=("targets",),
        category="target_siemens",
        provenance_url="generated://deterministic-optical-targets",
        license_name="project-generated",
        source_metadata={
            "target_type": "target_siemens",
            "generated": True,
            "official_split": False,
        },
        record_filter=_target_file_record("target_siemens.png"),
    ),
    "target_slanted_edge": FileSourceSpec(
        dataset_name="target_slanted_edge",
        root_parts=("targets",),
        category="target_slanted_edge",
        provenance_url="generated://deterministic-optical-targets",
        license_name="project-generated",
        source_metadata={
            "target_type": "target_slanted_edge",
            "generated": True,
            "official_split": False,
        },
        record_filter=_target_file_record("target_slanted_edge.png"),
    ),
    "target_line_pairs": FileSourceSpec(
        dataset_name="target_line_pairs",
        root_parts=("targets",),
        category="target_line_pairs",
        provenance_url="generated://deterministic-optical-targets",
        license_name="project-generated",
        source_metadata={
            "target_type": "target_line_pairs",
            "generated": True,
            "official_split": False,
        },
        record_filter=_target_file_record("target_line_pairs.png"),
    ),
}


def build_file_source_records(
    *,
    source_name: str,
    dataset_root: str | Path | None,
    is_train: bool,
    max_samples: int | None,
    random_seed: int,
) -> tuple[Path, list[FileIndexRecord], ChannelPolicy]:
    """
    根据已注册的文件源规格扫描并构建索引记录

    Returns:
        数据集根目录、文件索引记录列表和通道策略三元组
    """
    try:
        spec = FILE_SOURCE_SPECS[source_name]
    except KeyError as error:
        supported = ", ".join(sorted(FILE_SOURCE_SPECS))
        raise ValueError(
            f"不支持的文件数据源: {source_name}; 可选: {supported}"
        ) from error

    resolved_dataset_root = Path(
        resolve_dataset_root(
            str(dataset_root) if dataset_root is not None else None
        )
    )
    source_root = resolved_dataset_root.joinpath(*spec.root_parts)
    if not source_root.exists():
        raise FileNotFoundError(
            f"缺少{spec.dataset_name}图像目录: {source_root}"
        )

    split_name = "train" if is_train else "test"
    source_metadata = dict(spec.source_metadata)
    source_metadata["split_intent"] = split_name
    records = discover_image_files(
        dataset_name=spec.dataset_name,
        dataset_root=source_root,
        split_name=split_name,
        category=spec.category,
        provenance_url=spec.provenance_url,
        license_name=spec.license_name,
        source_metadata=source_metadata,
    )
    if spec.record_filter is not None:
        records = [record for record in records if spec.record_filter(record)]
    selected_indices = sample_max_indices(
        len(records),
        max_samples=max_samples,
        random_seed=random_seed,
    )
    return (
        source_root,
        select_index_records(records, selected_indices=selected_indices),
        spec.channel_policy,
    )

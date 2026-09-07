from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from data._validation import (
    validate_int,
    validate_non_negative_int,
    validate_optional_positive_int,
)

SUPPORTED_IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}


@dataclass(frozen=True)
class FileIndexRecord:
    """
    文件来源图像的稳定索引记录
    """

    dataset_name: str
    split_name: str
    image_id: str
    source_index: int
    source_path: Path
    category: str
    label: int
    provenance_url: str
    license_name: str
    source_metadata: Mapping[str, object]


def build_image_id(*, dataset_name: str, dataset_root: Path, image_path: Path) -> str:
    """
    生成基于数据集名称和相对路径主干的稳定图像标识
    """
    root = dataset_root.resolve()
    resolved_image_path = image_path.resolve()
    try:
        relative_path = resolved_image_path.relative_to(root)
    except ValueError as error:
        raise ValueError(
            "image_path必须位于dataset_root内部"
        ) from error
    relative_stem = relative_path.with_suffix("").as_posix()
    return f"{dataset_name}/{relative_stem}"


def discover_image_files(
    *,
    dataset_name: str,
    dataset_root: Path | str,
    split_name: str,
    category: str,
    provenance_url: str,
    license_name: str,
    source_metadata: Mapping[str, object] | None = None,
) -> list[FileIndexRecord]:
    """
    发现图像文件并返回稳定排序的索引记录
    """
    root = Path(dataset_root)
    paths = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    )
    records: list[FileIndexRecord] = []
    metadata = dict(source_metadata or {})
    resolved_root = root.resolve()
    for source_index, path in enumerate(paths):
        records.append(
            FileIndexRecord(
                dataset_name=dataset_name,
                split_name=split_name,
                image_id=build_image_id(
                    dataset_name=dataset_name,
                    dataset_root=root,
                    image_path=path,
                ),
                source_index=source_index,
                source_path=path.resolve().relative_to(resolved_root),
                category=category,
                label=0,
                provenance_url=provenance_url,
                license_name=license_name,
                source_metadata=dict(metadata),
            )
        )
    return records


def select_index_records(
    records: Sequence[FileIndexRecord],
    *,
    selected_indices: Iterable[int] | None,
) -> list[FileIndexRecord]:
    """
    按局部选择索引返回文件记录子集
    """
    if selected_indices is None:
        return list(records)
    selected: list[FileIndexRecord] = []
    for index in selected_indices:
        selected.append(replace(records[int(index)]))
    return selected


def sample_max_indices(
    total_count: int,
    *,
    max_samples: int | None,
    random_seed: int,
) -> list[int] | None:
    """
    生成确定性的最大样本数选择索引
    """
    if max_samples is None:
        return None
    validate_optional_positive_int("max_samples", max_samples)
    validate_non_negative_int("total_count", total_count)
    validate_int("random_seed", random_seed)
    if total_count == 0:
        return []
    random_generator = np.random.default_rng(random_seed)
    count = min(int(max_samples), int(total_count))
    return sorted(
        random_generator.choice(
            int(total_count),
            size=count,
            replace=False,
        )
        .astype(int)
        .tolist()
    )

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from json import dumps, loads
from pathlib import Path
from typing import cast, TypedDict


@dataclass(frozen=True)
class ManifestItem:
    """
    raw资产到可读图像的一条审计记录

    Attributes:
        dataset_name:    数据集名称
        source_archive:  原始归档名称
        source_member:   原始归档成员路径
        output_path:     输出图像相对路径
        image_id:        稳定图像标识
        operation:       资产整理操作名称
        channel_policy:  通道处理策略
        raw_resolution:  原始图像分辨率
        source_url:      原始数据来源地址
        license:         原始数据许可名称
    """

    dataset_name: str
    source_archive: str
    source_member: str
    output_path: str
    image_id: str
    operation: str
    channel_policy: str
    raw_resolution: tuple[int, int]
    source_url: str
    license: str


class ManifestPayload(TypedDict):
    """
    统一manifest文件载荷结构

    Attributes:
        version: manifest格式版本
        items:   资产条目字典列表
    """

    version: int
    items: list[dict[str, object]]


def write_manifest(manifest_path: str | Path, items: Iterable[ManifestItem]) -> Path:
    """
    写入统一manifest文件
    """
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "items": [
            {
                **asdict(item),
                "raw_resolution": list(item.raw_resolution),
            }
            for item in items
        ],
    }
    path.write_text(
        dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def read_manifest(manifest_path: str | Path) -> ManifestPayload:
    """
    读取统一manifest文件
    """
    return cast(ManifestPayload, loads(Path(manifest_path).read_text(encoding="utf-8")))


def validate_manifest_paths(manifest_path: str | Path) -> None:
    """
    校验manifest中记录的输出文件是否存在
    """
    path = Path(manifest_path)
    root = path.parent
    manifest = read_manifest(path)
    for item in manifest.get("items", []):
        output_path = item["output_path"]
        if not (root / output_path).exists():
            raise ValueError(
                f"manifest输出文件缺失: {output_path}"
            )

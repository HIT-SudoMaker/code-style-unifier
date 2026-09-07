from __future__ import annotations

import os
from pathlib import Path


def resolve_dataset_root(dataset_root: str | Path | None = None) -> str:
    """
    解析数据集根目录

    优先级：显式参数 > 环境变量ONN_DATASET_ROOT > 默认./data/raw
    """
    if dataset_root is not None:
        return str(dataset_root)

    env_dataset_root = os.getenv("ONN_DATASET_ROOT")
    if env_dataset_root:
        return env_dataset_root

    return "./data/raw"

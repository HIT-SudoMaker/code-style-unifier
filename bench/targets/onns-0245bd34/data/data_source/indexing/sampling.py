from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def build_stratified_indices(
    *,
    targets: Sequence[int] | np.ndarray,
    num_classes: int,
    samples_per_class: int | None,
    random_seed: int = 42,
) -> list[int]:
    """
    按类别分层构建采样索引

    Args:
        targets:           每个样本的类别标签
        num_classes:       总类别数
        samples_per_class: 每类采样数，None表示不采样
        random_seed:       随机种子

    Returns:
        采样后的索引列表
    """
    normalized_targets = np.asarray(targets)
    if samples_per_class is None:
        return list(range(len(normalized_targets)))

    random_generator = np.random.default_rng(random_seed)
    sampled_indices: list[int] = []
    for class_index in range(num_classes):
        class_indices = np.where(normalized_targets == class_index)[0]
        if len(class_indices) <= samples_per_class:
            sampled_indices.extend(class_indices.tolist())
        else:
            sampled_indices.extend(
                random_generator.choice(
                    class_indices,
                    size=samples_per_class,
                    replace=False,
                ).tolist()
            )
    return sampled_indices

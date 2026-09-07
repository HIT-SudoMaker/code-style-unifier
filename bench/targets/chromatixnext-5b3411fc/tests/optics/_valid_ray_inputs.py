
from __future__ import annotations

import torch


def _transverse_polarization_for_direction(
    direction: torch.Tensor,
) -> torch.Tensor:
    # 构造横截于给定实单位方向的复单位偏振向量
    real_direction = direction.to(dtype=torch.float64)
    min_indices = torch.argmin(real_direction.abs(), dim=-1)
    one_hot = torch.nn.functional.one_hot(min_indices, num_classes=3)
    one_hot = one_hot.to(dtype=torch.float64)
    projection = (one_hot * real_direction).sum(dim=-1, keepdim=True)
    transverse_real = one_hot - projection * real_direction
    norm = torch.linalg.norm(transverse_real, dim=-1, keepdim=True)
    transverse_unit = transverse_real / norm
    return transverse_unit.to(dtype=torch.complex128)

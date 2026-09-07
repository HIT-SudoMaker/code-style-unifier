from __future__ import annotations

import torch


def _householder_reflect(
    *,
    vector: torch.Tensor,
    unit_normal: torch.Tensor,
) -> torch.Tensor:

    # v · n̂ = Σ v_i n̂_i。n̂ 实；v 实 ⇒ 标量实；v 复 ⇒ 标量复（dtype 自动提升）
    projection = (vector * unit_normal).sum(dim=-1)
    return vector - (2.0 * projection).unsqueeze(-1) * unit_normal

def reflect_direction(
    *,
    ray_direction: torch.Tensor,
    unit_normal: torch.Tensor,
    is_interacted: torch.Tensor,
) -> torch.Tensor:
    """
    按向量反射律在命中+孔径内掩码上反射方向，其余光线保留入射方向

    """

    reflected_direction = _householder_reflect(
        vector=ray_direction,
        unit_normal=unit_normal,
    )
    return torch.where(
        is_interacted.unsqueeze(-1),
        reflected_direction,
        ray_direction,
    )

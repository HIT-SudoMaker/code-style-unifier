from __future__ import annotations

import torch

from experiments.restoration.errors import invalid_restoration_contract


def validate_single_channel_image(image: torch.Tensor) -> None:
    """
    校验复原后端的单通道图像张量
    """
    if not isinstance(image, torch.Tensor):
        raise invalid_restoration_contract("image must be a tensor")
    if image.ndim != 4 or image.shape[1] != 1:
        raise invalid_restoration_contract("image must have shape (B, 1, H, W)")
    if image.shape[2] <= 0 or image.shape[3] <= 0:
        raise invalid_restoration_contract(
            "image spatial dimensions must be positive"
        )

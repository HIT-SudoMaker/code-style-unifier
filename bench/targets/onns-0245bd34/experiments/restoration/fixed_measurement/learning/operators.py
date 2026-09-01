from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import torch
from torch.nn import functional as F

from data.configs.perturbation import DefocusBlurConfig
from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.errors import invalid_restoration_contract


def _disk_kernel(radius: int) -> np.ndarray:
    kernel_size = 2 * radius + 1
    coordinate = np.arange(kernel_size, dtype=np.float32) - float(radius)
    coordinate_y, coordinate_x = np.meshgrid(coordinate, coordinate, indexing="ij")
    disk = (coordinate_x**2 + coordinate_y**2) <= float(radius**2)
    kernel = disk.astype(np.float32)
    return kernel / float(kernel.sum())


class DefocusKnownOperator:
    """
    琛ㄧず鍙井鐨勫凡鐭ョ鐒﹀渾鐩樼畻瀛?    """

    def __init__(self, radius: int) -> None:
        """
        鍦嗙洏绂荤劍鏍稿崐寰?        """
        if isinstance(radius, bool) or not isinstance(radius, int) or radius <= 0:
            raise invalid_restoration_contract("radius must be a positive integer")
        self.radius = radius
        kernel = torch.from_numpy(_disk_kernel(radius))
        self._kernel = kernel[None, None]  # (1,1,k,k), cross-correlation matches cv2.filter2D

    def _validate(self, image: torch.Tensor) -> None:
        if not isinstance(image, torch.Tensor):
            raise invalid_restoration_contract("image must be a torch.Tensor")
        if image.ndim != 4 or image.shape[1] != 1:
            raise invalid_restoration_contract("image must have shape (B, 1, H, W)")

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        """
        浠ラ浂濉厖搴旂敤姝ｅ悜绂荤劍绠楀瓙
        """
        self._validate(image)
        kernel = self._kernel.to(device=image.device, dtype=image.dtype)
        return F.conv2d(image, kernel, padding=self.radius)

    def adjoint(self, image: torch.Tensor) -> torch.Tensor:
        """
        搴旂敤闆跺～鍏呯鐒︾畻瀛愮殑浼撮殢绠楀瓙
        """
        self._validate(image)
        kernel = self._kernel.to(device=image.device, dtype=image.dtype)
        return F.conv_transpose2d(image, kernel, padding=self.radius)

    def provenance_hash(self) -> str:
        """
        杩斿洖绂荤劍绠楀瓙閰嶇疆鎸囩汗
        """
        return compute_config_hash(DefocusBlurConfig(radius=self.radius))


def from_defocus_config(config: DefocusBlurConfig) -> DefocusKnownOperator:
    """
    浠庨€€鍖栭厤缃瀯閫犲凡鐭ョ鐒︾畻瀛?    """
    return DefocusKnownOperator(radius=config.radius)


def defocus_operator_for_dataset(dataset_config: object) -> DefocusKnownOperator | None:
    """
    浠庢暟鎹泦閫€鍖栭厤缃帹瀵煎敮涓€鐨勫凡鐭ョ畻瀛?
    Accepts either a ``RestorationDataConfig`` (has ``.perturbation``) or the standard
    wrapper dict ``{"dataset_config": RestorationDataConfig(...)}`` produced by
    ``build_standard_dataset_config``; returns ``None`` when no defocus op is present.
    """
    if isinstance(dataset_config, Mapping) and "dataset_config" in dataset_config:
        dataset_config = dataset_config["dataset_config"]
    perturbation = getattr(dataset_config, "perturbation", None)
    operations = getattr(perturbation, "operations", ()) if perturbation is not None else ()
    for operation in operations:
        if isinstance(operation, DefocusBlurConfig):
            return from_defocus_config(operation)
    return None

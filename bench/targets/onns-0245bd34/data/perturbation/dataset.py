from __future__ import annotations

import torch
from torch.utils.data import Dataset

from data._sample_conversions import copy_provenance, to_numpy_image
from data.configs.perturbation import PerturbationConfig
from data.configs.perturbation_registry import build_perturbation_provenance
from data.perturbation.executor import apply_perturbation_operations
from data.types import PerturbedSample, PreparedSample


class PerturbedDataset(Dataset):
    """
    对已准备数据集施加可选扰动的数据集包装器
    """

    def __init__(
        self,
        *,
        prepared_dataset: Dataset,
        perturbation_config: PerturbationConfig,
    ) -> None:
        """
        绑定已准备数据集和扰动阶段配置
        """
        self.prepared_dataset = prepared_dataset
        self._operations = list(perturbation_config.operations)
        self._degradation_seed = perturbation_config.degradation_seed

    def __len__(self) -> int:
        """
        返回底层已准备数据集的样本数量
        """
        return len(self.prepared_dataset)

    def __getitem__(self, index: int) -> PerturbedSample:
        """
        返回施加扰动并记录来源信息的样本
        """
        sample: PreparedSample = self.prepared_dataset[index]
        reference_image = sample["image"].clone()
        image = to_numpy_image(sample["image"], context_name="PerturbedDataset")
        image, applied_operations, extra_metadata = apply_perturbation_operations(
            image,
            self._operations,
            provenance=sample["provenance"],
            degradation_seed=self._degradation_seed,
        )
        perturbation = build_perturbation_provenance(
            operations=self._operations,
            applied_operations=applied_operations,
            degradation_seed=self._degradation_seed,
        )
        perturbation.update(extra_metadata)

        provenance = copy_provenance(sample["provenance"])
        provenance["stage"] = "perturbed"
        provenance["perturbation"] = perturbation

        perturbed_image = torch.from_numpy(image).unsqueeze(0)
        return {
            "image": perturbed_image,
            "reference_image": reference_image,
            "label": int(sample["label"]),
            "category": str(sample["category"]),
            "provenance": provenance,
        }

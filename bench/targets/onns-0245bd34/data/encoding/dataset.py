from __future__ import annotations

import torch
from torch.utils.data import Dataset

from data._sample_conversions import copy_provenance, to_numpy_image
from data.encoding.optical_encode import encode_image_to_field
from data.types import EncodedSample, PerturbedSample, PreparedSample


class EncodedDataset(Dataset):
    """Encode prepared or perturbed image samples as optical fields."""

    def __init__(self, *, source_dataset: Dataset, encoding_method: str) -> None:
        self.source_dataset = source_dataset
        self.encoding_method = encoding_method

    def __len__(self) -> int:
        return len(self.source_dataset)

    def __getitem__(self, index: int) -> EncodedSample:
        sample: PreparedSample | PerturbedSample = self.source_dataset[index]
        image = to_numpy_image(sample["image"], context_name="EncodedDataset")

        provenance = copy_provenance(sample["provenance"])
        provenance["stage"] = "encoded"
        provenance["encoding_method"] = self.encoding_method

        encoded_sample: EncodedSample = {
            "input_image": torch.from_numpy(image).unsqueeze(0),
            "input_field": encode_image_to_field(
                image=image,
                encoding_method=self.encoding_method,
            ),
            "label": int(sample["label"]),
            "category": str(sample["category"]),
            "provenance": provenance,
        }
        if "reference_image" in sample:
            encoded_sample["reference_image"] = sample["reference_image"].clone()
        return encoded_sample

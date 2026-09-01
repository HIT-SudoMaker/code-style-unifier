from __future__ import annotations

import pytest
import torch

from data import encode, load, perturb, prepare
from data.configs import (
    AdditiveGaussianNoiseConfig,
    EncodingConfig,
    PerturbationConfig,
    PreparationConfig,
    SourceConfig,
)
from data.data_source.registry import RegistryEntry
from data.encoding import EncodedDataset
from data.perturbation import PerturbedDataset
from data.preparation import PreparedDataset


class _FakeRawDataset:
    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> dict[str, object]:
        return {
            "image": torch.tensor([[[0.0, 255.0], [128.0, 64.0]]]),
            "label": 0,
            "category": "zero",
            "provenance": {
                "dataset_name": "mnist",
                "split_name": "train",
                "source_index": 0,
                "sampled_index": index,
                "sampling_seed": 7,
                "raw_resolution": (2, 2),
            },
        }


def test_public_stages_compose_without_a_pipeline_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "data.data_source.registry.DATASET_REGISTRY",
        {
            "mnist": RegistryEntry(
                builder=lambda **kwargs: _FakeRawDataset(),
                supports_class_sampling=True,
            )
        },
    )

    raw = load(SourceConfig(dataset_name="mnist", dataset_root="./data"))
    prepared = prepare(
        raw,
        PreparationConfig(
            image_resolution=(2, 2),
            array_resolution=(4, 4),
        ),
    )
    perturbed = perturb(
        prepared,
        PerturbationConfig(
            operations=(AdditiveGaussianNoiseConfig(sigma=0.0),)
        ),
    )
    encoded = encode(
        perturbed,
        EncodingConfig(encoding_method="intensity"),
    )
    sample = encoded[0]

    assert isinstance(prepared, PreparedDataset)
    assert isinstance(perturbed, PerturbedDataset)
    assert isinstance(encoded, EncodedDataset)
    assert sample["input_image"].shape == (1, 4, 4)
    assert sample["input_field"].dtype == torch.complex64
    assert sample["reference_image"].shape == (1, 4, 4)
    assert sample["provenance"]["stage"] == "encoded"


@pytest.mark.parametrize(
    "stage, config",
    [
        (load, object()),
        (prepare, object()),
        (perturb, object()),
        (encode, object()),
    ],
)
def test_public_stages_reject_the_wrong_config_type(
    stage: object,
    config: object,
) -> None:
    if stage is load:
        with pytest.raises(TypeError):
            load(config)  # type: ignore[arg-type]
        return
    with pytest.raises(TypeError):
        stage(_FakeRawDataset(), config)  # type: ignore[operator]


def test_data_package_has_four_explicit_stage_functions() -> None:
    import data

    assert data.__all__ == ("load", "prepare", "perturb", "encode")

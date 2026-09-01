from __future__ import annotations

from pathlib import Path
from typing import Literal, get_args, get_origin, get_type_hints

import numpy as np
import pytest

from data.configs import (
    AdditiveGaussianNoiseConfig,
    CannyEdgesConfig,
    DefocusBlurConfig,
    EncodingConfig,
    GaussianBlurConfig,
    LaplacianOfGaussianEdgesConfig,
    PerturbationConfig,
    PoissonGaussianNoiseConfig,
    PreparationConfig,
    PsfConvolutionConfig,
    SobelEdgesConfig,
    SourceConfig,
)


def _literal_values(type_hint: object) -> set[object]:
    if get_origin(type_hint) is Literal:
        return set(get_args(type_hint))
    return set()


def test_stage_config_defaults_are_independent() -> None:
    source = SourceConfig(dataset_name="mnist")
    preparation = PreparationConfig()
    perturbation = PerturbationConfig()
    encoding = EncodingConfig()

    assert source.dataset_root is None
    assert source.is_train is True
    assert source.samples_per_class is None
    assert source.max_samples is None
    assert source.random_seed == 42
    assert preparation.image_resolution == (64, 64)
    assert preparation.array_resolution == (128, 128)
    assert preparation.normalization_method == "auto"
    assert preparation.resize_interpolation_method == "nearest"
    assert preparation.edge_taper_width == 0
    assert perturbation.operations == ()
    assert perturbation.degradation_seed is None
    assert encoding.encoding_method == "intensity"


def test_source_config_requires_dataset_name() -> None:
    with pytest.raises(TypeError):
        SourceConfig()  # type: ignore[call-arg]


def test_perturbation_operation_configs_are_configuration_only() -> None:
    kernel = np.ones((3, 3), dtype=np.float32)
    operations = [
        AdditiveGaussianNoiseConfig(sigma=0.03),
        GaussianBlurConfig(kernel_size=5),
        DefocusBlurConfig(radius=2),
        PoissonGaussianNoiseConfig(peak_photons=100.0, read_noise_sigma=0.01),
        CannyEdgesConfig(),
        SobelEdgesConfig(kernel_size=3),
        LaplacianOfGaussianEdgesConfig(kernel_size=3, sigma=0.5),
        PsfConvolutionConfig(kernel=kernel),
    ]

    assert all(not hasattr(operation, "apply") for operation in operations)
    psf_config = operations[-1]
    assert isinstance(psf_config, PsfConvolutionConfig)
    assert not psf_config.kernel.flags.writeable
    kernel[0, 0] = 2.0
    assert psf_config.kernel[0, 0] == 1.0


def test_stage_config_fields_use_literal_types_for_closed_options() -> None:
    source_hints = get_type_hints(SourceConfig)
    preparation_hints = get_type_hints(PreparationConfig)
    encoding_hints = get_type_hints(EncodingConfig)

    assert Path in get_args(source_hints["dataset_root"])
    assert _literal_values(preparation_hints["normalization_method"]) == {
        "auto",
        "uint8",
        "uint16",
        "min_max",
        "percentile",
        "none",
    }
    assert _literal_values(preparation_hints["resize_interpolation_method"]) == {
        "nearest",
        "bilinear",
        "bicubic",
    }
    assert _literal_values(encoding_hints["encoding_method"]) == {
        "intensity",
        "phase",
    }


def test_config_package_exports_stage_types_only() -> None:
    import data.configs as configs

    assert configs.SourceConfig is SourceConfig
    assert configs.PreparationConfig is PreparationConfig
    assert configs.PerturbationConfig is PerturbationConfig
    assert configs.EncodingConfig is EncodingConfig
    assert "DataPipelineConfig" not in configs.__all__
    assert "PerturbedDataset" not in configs.__all__

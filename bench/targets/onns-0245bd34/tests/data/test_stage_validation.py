from __future__ import annotations

import numpy as np
import pytest

from data.configs import (
    AdditiveGaussianNoiseConfig,
    CannyEdgesConfig,
    EncodingConfig,
    GaussianBlurConfig,
    LaplacianOfGaussianEdgesConfig,
    PerturbationConfig,
    PoissonGaussianNoiseConfig,
    PreparationConfig,
    PsfConvolutionConfig,
    SobelEdgesConfig,
    SourceConfig,
    validate_encoding,
    validate_perturbation,
    validate_preparation,
    validate_source,
)


def test_validate_source_rejects_invalid_sampling_values() -> None:
    with pytest.raises(ValueError, match="samples_per_class"):
        validate_source(
            SourceConfig(dataset_name="mnist", samples_per_class=0)
        )


def test_validate_preparation_rejects_impossible_geometry() -> None:
    with pytest.raises(ValueError, match="fit inside"):
        validate_preparation(
            PreparationConfig(
                image_resolution=(8, 8),
                array_resolution=(4, 4),
            )
        )


def test_validate_preparation_rejects_taper_wider_than_image_support() -> None:
    with pytest.raises(ValueError, match="edge_taper_width"):
        validate_preparation(
            PreparationConfig(
                image_resolution=(2, 2),
                array_resolution=(4, 4),
                edge_taper_width=2,
            )
        )


def test_validate_encoding_rejects_invalid_method() -> None:
    with pytest.raises(ValueError, match="encoding_method"):
        validate_encoding(EncodingConfig(encoding_method="bogus"))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "operation, expected_message",
    [
        (AdditiveGaussianNoiseConfig(sigma=None), "noise_sigma"),
        (GaussianBlurConfig(kernel_size=None), "blur_kernel_size"),
        (
            PoissonGaussianNoiseConfig(
                peak_photons=None,
                read_noise_sigma=0.0,
            ),
            "poisson_peak_photons",
        ),
        (
            PoissonGaussianNoiseConfig(
                peak_photons=20.0,
                read_noise_sigma=None,
            ),
            "read_noise_sigma",
        ),
        (CannyEdgesConfig(threshold1=None, threshold2=20.0), "edge_threshold1"),
        (CannyEdgesConfig(threshold1=10.0, threshold2=None), "edge_threshold2"),
        (SobelEdgesConfig(kernel_size=None), "edge_kernel_size"),
        (
            LaplacianOfGaussianEdgesConfig(kernel_size=None, sigma=0.0),
            "edge_kernel_size",
        ),
        (
            LaplacianOfGaussianEdgesConfig(kernel_size=3, sigma=None),
            "edge_sigma",
        ),
    ],
)
def test_validate_perturbation_rejects_missing_operation_values(
    operation: object,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        validate_perturbation(PerturbationConfig(operations=(operation,)))


@pytest.mark.parametrize("sigma", [float("nan"), float("inf")])
def test_validate_perturbation_rejects_non_finite_noise(sigma: float) -> None:
    with pytest.raises(ValueError, match="noise_sigma"):
        validate_perturbation(
            PerturbationConfig(
                operations=(AdditiveGaussianNoiseConfig(sigma=sigma),)
            )
        )


@pytest.mark.parametrize(
    "kernel",
    [
        np.ones((3,), dtype=np.float32),
        np.array([[0.0, np.nan], [0.0, 0.0]], dtype=np.float32),
        np.zeros((3, 3), dtype=np.float32),
        np.array([[1.0, -0.1], [0.0, 0.0]], dtype=np.float32),
    ],
)
def test_validate_perturbation_rejects_invalid_psf(kernel: np.ndarray) -> None:
    with pytest.raises(ValueError, match="psf_kernel"):
        validate_perturbation(
            PerturbationConfig(operations=(PsfConvolutionConfig(kernel=kernel),))
        )


def test_validate_perturbation_accepts_ordered_operations() -> None:
    validate_perturbation(
        PerturbationConfig(
            operations=(
                AdditiveGaussianNoiseConfig(sigma=0.01),
                GaussianBlurConfig(kernel_size=3),
                SobelEdgesConfig(kernel_size=3),
            )
        )
    )

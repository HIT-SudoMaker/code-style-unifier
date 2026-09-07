from __future__ import annotations

import math

import pytest
import torch

from data.configs import DefocusBlurConfig, PoissonGaussianNoiseConfig
from experiments.restoration.degradation import restoration_profile
from experiments.restoration.fixed_measurement.learning.standard_configs import (
    STANDARD_BACKEND_CALIBRATION_SEARCH_SPACE,
    STANDARD_COMMON_BUDGET,
    STANDARD_FRONTEND_BUDGET,
    STANDARD_SPLITS,
    build_standard_dataset_config,
    degradation_hash_for_dataset_config,
    fourier_plane_pixel_pitch_m,
    validate_encoded_batch_invariants,
)


LEGACY_MEDIUM_PROFILE_NAME = "medium" + "_degraded"


def test_standard_dataset_config_uses_canonical_profile_names() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    wrapper = build_standard_dataset_config(
        profile_name="medium",
        split="train",
        split_manifest={"records": []},
    )

    assert wrapper["profile_name"] == "medium"
    assert wrapper["split"] == "train"
    assert STANDARD_SPLITS == ("train", "val", "test")

    dataset_config = wrapper["dataset_config"]
    assert dataset_config.preparation.image_resolution == (256, 256)
    assert dataset_config.preparation.array_resolution == (512, 512)
    assert dataset_config.preparation.edge_taper_width == 0
    assert dataset_config.encoding.encoding_method == "intensity"
    assert dataset_config.perturbation == restoration_profile("medium")
    assert restoration_profile("medium").operations == (
        DefocusBlurConfig(radius=6),
        PoissonGaussianNoiseConfig(peak_photons=5.0, read_noise_sigma=0.0),
    )


def test_standard_dataset_config_rejects_legacy_profile_aliases() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="profile_name.*light, medium, heavy") as exc:
        build_standard_dataset_config(
            profile_name=LEGACY_MEDIUM_PROFILE_NAME,
            split="train",
            split_manifest={"records": []},
        )
    assert LEGACY_MEDIUM_PROFILE_NAME in str(exc.value)


def test_standard_dataset_config_rejects_invalid_split() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="split.*train, val, test") as exc:
        build_standard_dataset_config(
            profile_name="medium",
            split="dev",
            split_manifest={"records": []},
        )
    assert "dev" in str(exc.value)


def test_standard_dataset_config_rejects_non_mapping_split_manifest() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="split_manifest"):
        build_standard_dataset_config(
            profile_name="medium",
            split="train",
            split_manifest=[],
        )


def test_degradation_hash_changes_with_profile() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    medium_config = build_standard_dataset_config(
        profile_name="medium",
        split="train",
        split_manifest={"records": []},
    )
    matching_medium_config = build_standard_dataset_config(
        profile_name="medium",
        split="val",
        split_manifest={"records": []},
    )
    heavy_config = build_standard_dataset_config(
        profile_name="heavy",
        split="train",
        split_manifest={"records": []},
    )

    medium_hash = degradation_hash_for_dataset_config(medium_config)
    assert medium_hash == degradation_hash_for_dataset_config(matching_medium_config)
    assert medium_hash != degradation_hash_for_dataset_config(heavy_config)


def test_degradation_hash_accepts_direct_dataset_config() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    wrapper = build_standard_dataset_config(
        profile_name="medium",
        split="train",
        split_manifest={"records": []},
    )

    assert degradation_hash_for_dataset_config(
        wrapper["dataset_config"]
    ) == degradation_hash_for_dataset_config(wrapper)


def test_validate_encoded_batch_invariants_accepts_expected_intensity() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    degraded_image = torch.tensor([[[[0.25, 1.0], [4.0, 9.0]]]], dtype=torch.float32)
    batch = {
        "clean_image": torch.zeros_like(degraded_image),
        "degraded_image": degraded_image,
        "input_field": torch.sqrt(degraded_image).to(torch.complex64),
    }

    validate_encoded_batch_invariants(batch, expected_shape=(1, 1, 2, 2))


def test_validate_encoded_batch_invariants_rejects_intensity_mismatch() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    degraded_image = torch.ones((1, 1, 2, 2), dtype=torch.float32)
    batch = {
        "clean_image": torch.zeros_like(degraded_image),
        "degraded_image": degraded_image,
        "input_field": torch.zeros_like(degraded_image).to(torch.complex64),
    }

    with pytest.raises(ValueError, match="input_field intensity"):
        validate_encoded_batch_invariants(batch, expected_shape=(1, 1, 2, 2))


def test_validate_encoded_batch_invariants_rejects_missing_clean_image() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    degraded_image = torch.ones((1, 1, 2, 2), dtype=torch.float32)
    batch = {
        "degraded_image": degraded_image,
        "input_field": torch.sqrt(degraded_image).to(torch.complex64),
    }

    with pytest.raises(ValueError, match="clean_image"):
        validate_encoded_batch_invariants(batch, expected_shape=(1, 1, 2, 2))


def test_validate_encoded_batch_invariants_rejects_non_complex_input_field() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    degraded_image = torch.ones((1, 1, 2, 2), dtype=torch.float32)
    batch = {
        "clean_image": torch.zeros_like(degraded_image),
        "degraded_image": degraded_image,
        "input_field": degraded_image,
    }

    with pytest.raises(ValueError, match="input_field.*complex"):
        validate_encoded_batch_invariants(batch, expected_shape=(1, 1, 2, 2))


def test_fourier_plane_pixel_pitch_m() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    pixel_pitch = fourier_plane_pixel_pitch_m(
        wavelength_m=638e-9,
        focal_length_m=0.1,
        sample_count=512,
        input_pixel_pitch_m=8e-6,
    )

    assert math.isfinite(pixel_pitch)
    assert pixel_pitch == pytest.approx(15.576e-6, rel=2e-4)


def test_fourier_plane_pixel_pitch_m_rejects_nonpositive_sample_count() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="sample_count"):
        fourier_plane_pixel_pitch_m(
            wavelength_m=638e-9,
            focal_length_m=0.1,
            sample_count=0,
            input_pixel_pitch_m=8e-6,
        )


def test_standard_training_budgets() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    assert STANDARD_COMMON_BUDGET == {
        "epochs": 50,
        "batch_size": 2,
        "optimizer_family": "Adam",
        "weight_decay": 0.0,
        "loss_l1_weight": 1.0,
        "loss_ssim_weight": 0.2,
        "intensity_normalization_policy": "fixed_dataset_level",
        "random_seed": 2026,
        "checkpoint_policy": "best_and_last",
    }
    assert STANDARD_FRONTEND_BUDGET["learning_rate"] == 0.003
    assert STANDARD_FRONTEND_BUDGET["loss_frequency_weight"] == 0.1
    assert STANDARD_FRONTEND_BUDGET["phase_smoothness_weight"] == 1e-4
    assert STANDARD_BACKEND_CALIBRATION_SEARCH_SPACE["learning_rate"] == (
        1e-4,
        3e-4,
        1e-3,
        3e-3,
    )
    assert STANDARD_BACKEND_CALIBRATION_SEARCH_SPACE["batch_size"] == (2,)

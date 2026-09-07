from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import torch

from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.fixed_measurement.learning.data_loading import RestorationDataConfig
from experiments.restoration.degradation import (
    STANDARD_RESTORATION_PROFILE_NAMES,
    restoration_profile,
)
from experiments.restoration.input_protocol import (
    STANDARD_RESTORATION_ENCODING,
    STANDARD_RESTORATION_PREPARATION,
    build_restoration_source,
)
from experiments.restoration.errors import invalid_restoration_contract

STANDARD_SPLITS = ("train", "val", "test")

STANDARD_COMMON_BUDGET = {
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

STANDARD_FRONTEND_BUDGET = {
    **STANDARD_COMMON_BUDGET,
    "learning_rate": 0.003,
    "loss_frequency_weight": 0.1,
    "phase_smoothness_weight": 1e-4,
    "phase_initialization": "zeros",
}

STANDARD_BACKEND_CALIBRATION_SEARCH_SPACE = {
    "learning_rate": (1e-4, 3e-4, 1e-3, 3e-3),
    "batch_size": (2,),
    "weight_decay": (0.0,),
    "loss_l1_weight": (1.0,),
    "loss_ssim_weight": (0.2,),
    "loss_frequency_weight": (0.0,),
    "phase_smoothness_weight": (0.0,),
}


def build_standard_dataset_config(
    *,
    profile_name: str,
    split: Literal["train", "val", "test"],
    split_manifest: Mapping[str, object],
    dataset_root: str | Path | None = "data/raw",
) -> dict[str, object]:
    """
    杩斿洖鏍囧噯鏁版嵁闆嗛厤缃?    """
    if profile_name not in STANDARD_RESTORATION_PROFILE_NAMES:
        allowed_profiles = ", ".join(STANDARD_RESTORATION_PROFILE_NAMES)
        raise invalid_restoration_contract(
            f"profile_name '{profile_name}' must be one of: {allowed_profiles}"
        )
    if split not in STANDARD_SPLITS:
        allowed_splits = ", ".join(STANDARD_SPLITS)
        raise invalid_restoration_contract(
            f"split '{split}' must be one of: {allowed_splits}"
        )
    if not isinstance(split_manifest, Mapping):
        raise invalid_restoration_contract("split_manifest must be a Mapping")

    dataset_config = RestorationDataConfig(
        source=build_restoration_source(dataset_root),
        preparation=STANDARD_RESTORATION_PREPARATION,
        perturbation=restoration_profile(profile_name),
        encoding=STANDARD_RESTORATION_ENCODING,
    )
    return {
        "dataset_config": dataset_config,
        "split_manifest": split_manifest,
        "split": split,
        "profile_name": profile_name,
    }


def degradation_hash_for_dataset_config(dataset_config: object) -> str:
    """
    杩斿洖鏁版嵁闆嗛€€鍖栧搱甯?    """
    if isinstance(dataset_config, Mapping) and "dataset_config" in dataset_config:
        dataset_config = dataset_config["dataset_config"]
    perturbation = getattr(dataset_config, "perturbation", None)
    if perturbation is None:
        raise invalid_restoration_contract(
            "dataset_config must provide a perturbation"
        )
    return compute_config_hash(perturbation)


def validate_encoded_batch_invariants(
    batch: Mapping[str, object],
    *,
    expected_shape: tuple[int, int, int, int] | None = None,
    atol: float = 1e-5,
) -> None:
    """
    鏍￠獙缂栫爜鎵规涓嶅彉閲?    """
    clean_image = _tensor_from_batch(batch, "clean_image")
    degraded_image = _tensor_from_batch(batch, "degraded_image")
    input_field = _tensor_from_batch(batch, "input_field")

    for name, tensor in (
        ("clean_image", clean_image),
        ("degraded_image", degraded_image),
        ("input_field", input_field),
    ):
        if tensor.ndim != 4:
            raise invalid_restoration_contract(f"{name} must be a 4D tensor")
        if expected_shape is not None and tuple(tensor.shape) != expected_shape:
            raise invalid_restoration_contract(
                f"{name} shape must be {expected_shape}"
            )

    if tuple(clean_image.shape) != tuple(degraded_image.shape) or tuple(
        input_field.shape
    ) != tuple(degraded_image.shape):
        raise invalid_restoration_contract(
            "clean_image, degraded_image, and input_field shape must match"
        )

    if not torch.is_complex(input_field):
        raise invalid_restoration_contract("input_field must be complex")

    input_intensity = input_field.abs().square().real.to(dtype=degraded_image.dtype)
    if not torch.allclose(input_intensity, degraded_image, atol=atol, rtol=0.0):
        raise invalid_restoration_contract(
            "input_field intensity does not match degraded_image"
        )


def fourier_plane_pixel_pitch_m(
    *,
    wavelength_m: float,
    focal_length_m: float,
    sample_count: int,
    input_pixel_pitch_m: float,
) -> float:
    """
    璁＄畻鍌呴噷鍙跺钩闈㈠儚绱犻棿璺?    """
    for parameter_name, value in (
        ("wavelength_m", wavelength_m),
        ("focal_length_m", focal_length_m),
        ("sample_count", sample_count),
        ("input_pixel_pitch_m", input_pixel_pitch_m),
    ):
        if value <= 0:
            raise invalid_restoration_contract(
                f"{parameter_name} must be positive"
            )
    return wavelength_m * focal_length_m / (sample_count * input_pixel_pitch_m)


def _tensor_from_batch(batch: Mapping[str, object], key: str) -> torch.Tensor:
    value = batch.get(key)
    if not isinstance(value, torch.Tensor):
        raise invalid_restoration_contract(f"{key} must be a torch.Tensor")
    return value

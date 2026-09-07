from __future__ import annotations

import importlib

import numpy as np
import pytest

from data.configs.perturbation import (
    AdditiveGaussianNoiseConfig,
    CannyEdgesConfig,
    DefocusBlurConfig,
    GaussianBlurConfig,
    LaplacianOfGaussianEdgesConfig,
    PoissonGaussianNoiseConfig,
    PsfConvolutionConfig,
    SobelEdgesConfig,
)
from data.perturbation.executor import apply_perturbation_operations
from data.perturbation.optics.circular_pupil_functions import build_circular_pupil_function
from data.perturbation.optics.coherent_imaging import point_spread_function_from_pupil_function


def _provenance() -> dict[str, object]:
    return {
        "dataset_name": "mnist",
        "split_name": "train",
        "source_index": 2,
        "sampled_index": 3,
        "sampling_seed": 7,
    }


def test_apply_perturbation_operations_preserves_operation_order() -> None:
    """
    验证扰动执行器会保留操作顺序
    """
    image = np.zeros((7, 7), dtype=np.float32)

    _, applied_operations, extra_metadata = apply_perturbation_operations(
        image,
        [
            AdditiveGaussianNoiseConfig(sigma=0.0),
            GaussianBlurConfig(kernel_size=3),
            DefocusBlurConfig(radius=1),
            PsfConvolutionConfig(kernel=np.ones((3, 3), dtype=np.float32)),
            PoissonGaussianNoiseConfig(peak_photons=100.0, read_noise_sigma=0.0),
            CannyEdgesConfig(),
            SobelEdgesConfig(kernel_size=3),
            LaplacianOfGaussianEdgesConfig(kernel_size=3, sigma=0.0),
        ],
        provenance=_provenance(),
        degradation_seed=11,
    )

    assert [operation["name"] for operation in applied_operations] == [
        "add_additive_gaussian_noise",
        "apply_gaussian_blur",
        "apply_defocus_blur",
        "apply_psf_kernel",
        "add_poisson_gaussian_noise",
        "build_canny_edge_map",
        "build_sobel_edge_map",
        "build_laplacian_of_gaussian_edge_map",
    ]
    assert extra_metadata["noise_rng"]["mode"] == "deterministic"


def test_additive_gaussian_noise_operation_is_deterministic_from_provenance() -> None:
    """
    验证加性高斯噪声会由样本来源稳定复现
    """
    image = np.full((4, 4), 0.5, dtype=np.float32)
    operation = AdditiveGaussianNoiseConfig(sigma=0.02)

    first, first_operations, first_metadata = apply_perturbation_operations(
        image,
        [operation],
        provenance=_provenance(),
    )
    second, second_operations, second_metadata = apply_perturbation_operations(
        image,
        [operation],
        provenance=_provenance(),
    )

    assert np.allclose(first, second)
    assert first_operations == second_operations
    assert first_operations == [
        {"name": "add_additive_gaussian_noise", "parameters": {"sigma": 0.02}}
    ]
    assert first_metadata == second_metadata
    assert first_metadata["noise_rng"]["sampling_seed"] == 7


def test_additive_gaussian_noise_uses_degradation_seed_without_sampling_seed() -> None:
    """
    验证加性高斯噪声可仅由退化种子稳定复现
    """
    image = np.full((4, 4), 0.5, dtype=np.float32)
    operation = AdditiveGaussianNoiseConfig(sigma=0.02)
    provenance = {
        "dataset_name": "biosr",
        "split_name": "train",
        "source_index": 4,
        "sampled_index": 0,
    }

    first, first_operations, first_metadata = apply_perturbation_operations(
        image,
        [operation],
        provenance=provenance,
        degradation_seed=23,
    )
    second, second_operations, second_metadata = apply_perturbation_operations(
        image,
        [operation],
        provenance=provenance,
        degradation_seed=23,
    )
    changed, _, changed_metadata = apply_perturbation_operations(
        image,
        [operation],
        provenance=provenance,
        degradation_seed=24,
    )

    assert np.allclose(first, second)
    assert not np.allclose(first, changed)
    assert first_operations == second_operations
    assert first_metadata == second_metadata
    assert first_metadata["noise_rng"]["mode"] == "deterministic"
    assert first_metadata["noise_rng"]["sampling_seed"] is None
    assert first_metadata["noise_rng"]["degradation_seed"] == 23
    assert changed_metadata["noise_rng"]["degradation_seed"] == 24


def test_degradation_seed_uses_stable_image_identity_instead_of_file_order() -> None:
    """
    验证同一图像重建索引后仍得到相同退化，不同图像得到不同退化
    """
    image = np.full((16, 16), 0.5, dtype=np.float32)
    operation = PoissonGaussianNoiseConfig(
        peak_photons=5.0,
        read_noise_sigma=0.01,
    )
    first_provenance = {
        "image_id": "fmd/Confocal_BPAE_G/1/avg50",
        "source_index": 3,
        "sampled_index": 7,
    }
    reordered_provenance = {
        "image_id": "fmd/Confocal_BPAE_G/1/avg50",
        "source_index": 103,
        "sampled_index": 207,
    }
    other_image_provenance = {
        "image_id": "fmd/Confocal_BPAE_G/2/avg50",
        "source_index": 3,
        "sampled_index": 7,
    }

    first, first_operations, _ = apply_perturbation_operations(
        image,
        [operation],
        provenance=first_provenance,
        degradation_seed=2026,
    )
    reordered, reordered_operations, _ = apply_perturbation_operations(
        image,
        [operation],
        provenance=reordered_provenance,
        degradation_seed=2026,
    )
    other, _, _ = apply_perturbation_operations(
        image,
        [operation],
        provenance=other_image_provenance,
        degradation_seed=2026,
    )

    np.testing.assert_array_equal(first, reordered)
    assert first_operations == reordered_operations
    assert not np.array_equal(first, other)


def test_poisson_gaussian_operation_uses_degradation_seed_and_provenance() -> None:
    """
    验证泊松高斯噪声会合成退化种子和样本来源
    """
    image = np.full((4, 4), 0.5, dtype=np.float32)
    operation = PoissonGaussianNoiseConfig(
        peak_photons=100.0,
        read_noise_sigma=0.01,
    )

    first, first_operations, _ = apply_perturbation_operations(
        image,
        [operation],
        provenance=_provenance(),
        degradation_seed=13,
    )
    second, second_operations, _ = apply_perturbation_operations(
        image,
        [operation],
        provenance=_provenance(),
        degradation_seed=13,
    )

    assert np.allclose(first, second)
    assert first_operations == second_operations
    assert first_operations[0]["name"] == "add_poisson_gaussian_noise"
    assert first_operations[0]["parameters"]["random_seed"] is not None


def test_defocus_and_psf_operation_parameters_are_recorded() -> None:
    """
    验证离焦和PSF操作会记录参数
    """
    image = np.zeros((5, 5), dtype=np.float32)
    image[2, 2] = 1.0

    output, applied_operations, extra_metadata = apply_perturbation_operations(
        image,
        [
            DefocusBlurConfig(radius=1),
            PsfConvolutionConfig(kernel=np.ones((3, 3), dtype=np.float32)),
        ],
        provenance=_provenance(),
    )

    assert output.shape == image.shape
    assert applied_operations == [
        {"name": "apply_defocus_blur", "parameters": {"radius": 1}},
        {
            "name": "apply_psf_kernel",
            "parameters": {"shape": (3, 3), "sum": 9.0},
        },
    ]
    assert extra_metadata == {}


def test_psf_convolution_clips_numerical_roundoff_to_unit_range() -> None:
    """
    验证PSF卷积会将浮点舍入误差裁剪回归一化强度范围
    """
    image = np.zeros((128, 128), dtype=np.float32)
    image[:, 64:] = 1.0
    pupil = build_circular_pupil_function(shape=(64, 64), radius_fraction=0.35)
    point_spread_function = point_spread_function_from_pupil_function(pupil)

    output, _, _ = apply_perturbation_operations(
        image,
        [PsfConvolutionConfig(kernel=point_spread_function)],
        provenance=_provenance(),
    )

    assert output.dtype == np.float32
    assert float(output.min()) >= 0.0
    assert float(output.max()) <= 1.0


def test_canny_operation_records_thresholds() -> None:
    """
    验证Canny操作会记录阈值
    """
    image = np.zeros((5, 5), dtype=np.float32)
    image[:, 2:] = 1.0

    output, applied_operations, extra_metadata = apply_perturbation_operations(
        image,
        [CannyEdgesConfig(threshold1=5.0, threshold2=15.0)],
        provenance=_provenance(),
    )

    assert output.dtype == np.float32
    assert applied_operations == [
        {
            "name": "build_canny_edge_map",
            "parameters": {"threshold1": 5.0, "threshold2": 15.0},
        }
    ]
    assert extra_metadata == {}


def test_sobel_and_log_operations_record_edge_parameters() -> None:
    """
    验证Sobel和LoG操作会记录边缘参数
    """
    image = np.zeros((9, 9), dtype=np.float32)
    image[3:6, 3:6] = 1.0

    output, applied_operations, extra_metadata = apply_perturbation_operations(
        image,
        [
            SobelEdgesConfig(kernel_size=3),
            LaplacianOfGaussianEdgesConfig(kernel_size=3, sigma=0.0),
        ],
        provenance=_provenance(),
    )

    assert output.dtype == np.float32
    assert output.shape == image.shape
    assert applied_operations == [
        {
            "name": "build_sobel_edge_map",
            "parameters": {"kernel_size": 3},
        },
        {
            "name": "build_laplacian_of_gaussian_edge_map",
            "parameters": {"kernel_size": 3, "sigma": 0.0},
        },
    ]
    assert extra_metadata == {}


def test_unknown_perturbation_operation_type_is_rejected() -> None:
    """
    验证未知扰动操作类型会被拒绝
    """
    with pytest.raises(TypeError, match="不支持的扰动算子配置类型"):
        apply_perturbation_operations(
            np.zeros((2, 2), dtype=np.float32),
            [object()],  # type: ignore[list-item]
            provenance=_provenance(),
        )


def test_config_and_perturbation_import_order_is_cycle_safe() -> None:
    """
    验证配置模块和扰动模块导入顺序安全
    """
    importlib.import_module("data.perturbation")
    importlib.import_module("data.configs")
    importlib.import_module("data.configs")
    importlib.import_module("data.perturbation")

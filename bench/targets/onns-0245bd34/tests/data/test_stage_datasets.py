from __future__ import annotations

import numpy as np
import pytest
import torch

from data import encode, prepare, perturb
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
)
from data.encoding.dataset import EncodedDataset
from data.perturbation.dataset import PerturbedDataset
from data.preparation.dataset import PreparedDataset


class _TinyRawDataset:
    def __len__(self) -> int:
        """
        返回固定样本数
        """
        return 1

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        返回带确定性采样种子的微型原始样本
        """
        return {
            "image": torch.tensor(
                [[[0.0, 64.0], [128.0, 255.0]]],
                dtype=torch.float32,
            ),
            "label": 1,
            "category": "one",
            "provenance": {
                "dataset_name": "mnist",
                "split_name": "train",
                "source_index": 3,
                "sampled_index": index,
                "sampling_seed": 7,
                "is_stratified_sampled": False,
                "raw_resolution": (2, 2),
            },
        }


class _UnseededRawDataset:
    def __len__(self) -> int:
        """
        返回固定样本数
        """
        return 1

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        返回不含采样种子的微型原始样本
        """
        return {
            "image": torch.full((1, 2, 2), 0.5, dtype=torch.float32),
            "label": 0,
            "category": "zero",
            "provenance": {
                "dataset_name": "mnist",
                "split_name": "test",
                "source_index": 0,
                "sampled_index": index,
                "sampling_seed": None,
                "is_stratified_sampled": False,
                "raw_resolution": (2, 2),
            },
        }


def test_prepare_builds_prepared_stage_from_config() -> None:
    dataset = prepare(
        _TinyRawDataset(),
        PreparationConfig(
            image_resolution=(2, 2),
            array_resolution=(4, 4),
        ),
    )

    sample = dataset[0]

    assert sample["image"].shape == (1, 4, 4)
    assert sample["provenance"]["stage"] == "prepared"


def test_perturb_builds_distinct_stage_with_reference_image() -> None:
    prepared = prepare(
        _TinyRawDataset(),
        PreparationConfig(
            image_resolution=(2, 2),
            array_resolution=(4, 4),
        ),
    )
    dataset = perturb(
        prepared,
        PerturbationConfig(
            operations=(GaussianBlurConfig(kernel_size=3),),
        ),
    )

    sample = dataset[0]

    assert torch.equal(sample["reference_image"], prepared[0]["image"])
    assert not torch.equal(sample["image"], sample["reference_image"])
    assert "clean_image" not in sample
    assert "degraded_image" not in sample


def test_encode_builds_optical_field_stage_from_config() -> None:
    prepared = prepare(
        _TinyRawDataset(),
        PreparationConfig(
            image_resolution=(2, 2),
            array_resolution=(4, 4),
        ),
    )
    dataset = encode(
        prepared,
        EncodingConfig(encoding_method="intensity"),
    )

    sample = dataset[0]

    assert sample["input_field"].shape == (1, 4, 4)
    assert sample["input_field"].dtype == torch.complex64
    assert sample["provenance"]["stage"] == "encoded"


def test_prepared_dataset_normalizes_and_resizes_raw_samples() -> None:
    """
    验证预处理数据集会归一化并居中填充样本
    """
    dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )

    sample = dataset[0]

    assert sample["image"].shape == (1, 4, 4)
    assert sample["image"].dtype == torch.float32
    assert torch.allclose(
        sample["image"][0, 1:3, 1:3],
        torch.tensor(
            [
                [0.0, 64.0 / 255.0],
                [128.0 / 255.0, 1.0],
            ],
            dtype=torch.float32,
        ),
    )
    assert torch.count_nonzero(sample["image"][0, 0]) == 0
    assert sample["provenance"]["stage"] == "prepared"
    assert sample["provenance"]["preparation"] == {
        "image_resolution": (2, 2),
        "array_resolution": (4, 4),
        "normalization_method": "auto",
        "resize_interpolation_method": "nearest",
        "edge_taper_width": 0,
    }


def test_perturbed_dataset_applies_optional_noise_and_blur_and_records_metadata() -> None:
    """
    验证扰动数据集会应用噪声和模糊并记录元数据
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    clean_sample = prepared_dataset[0]
    dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(
            operations=(
                AdditiveGaussianNoiseConfig(sigma=0.01),
                GaussianBlurConfig(kernel_size=3),
            ),
        ),
    )

    sample = dataset[0]

    assert sample["image"].shape == (1, 4, 4)
    assert sample["image"].dtype == torch.float32
    assert not torch.allclose(sample["image"], clean_sample["image"])
    assert sample["provenance"]["stage"] == "perturbed"
    assert sample["provenance"]["perturbation"]["noise_sigma"] == 0.01
    assert sample["provenance"]["perturbation"]["blur_kernel_size"] == 3
    assert sample["provenance"]["perturbation"]["edge_extraction"] == {
        "is_enabled": False,
        "threshold1": None,
        "threshold2": None,
    }
    assert sample["provenance"]["perturbation"]["applied_operations"] == [
        {
            "name": "add_additive_gaussian_noise",
            "parameters": {"sigma": 0.01},
        },
        {
            "name": "apply_gaussian_blur",
            "parameters": {"kernel_size": 3},
        },
    ]
    assert sample["provenance"]["perturbation"]["noise_rng"]["mode"] == "deterministic"


def test_perturbed_dataset_preserves_reference_and_current_images() -> None:
    """
    验证扰动数据集会保留参考图像和当前图像
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    clean_sample = prepared_dataset[0]
    dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(
            operations=(AdditiveGaussianNoiseConfig(sigma=0.01),),
            degradation_seed=13,
        ),
    )

    sample = dataset[0]

    assert torch.equal(sample["reference_image"], clean_sample["image"])
    assert not torch.equal(sample["reference_image"], sample["image"])


def test_encoded_dataset_propagates_reference_image() -> None:
    """
    验证编码数据集会透传上游参考图像
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    perturbed_dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(
            operations=(AdditiveGaussianNoiseConfig(sigma=0.01),),
            degradation_seed=13,
        ),
    )
    dataset = EncodedDataset(
        source_dataset=perturbed_dataset,
        encoding_method="intensity",
    )

    sample = dataset[0]

    perturbed_sample = perturbed_dataset[0]
    assert torch.equal(sample["input_image"], perturbed_sample["image"])
    assert torch.equal(sample["reference_image"], perturbed_sample["reference_image"])
    assert not torch.equal(sample["reference_image"], sample["input_image"])
    assert sample["provenance"]["stage"] == "encoded"
    assert sample["provenance"]["perturbation"]["degradation_seed"] == 13


def test_perturbed_dataset_records_enable_edge_extraction_details_and_order() -> None:
    """
    验证扰动数据集会记录边缘提取细节和执行顺序
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(
            operations=(
                GaussianBlurConfig(kernel_size=3),
                CannyEdgesConfig(),
            ),
        ),
    )

    sample = dataset[0]

    assert sample["provenance"]["stage"] == "perturbed"
    assert sample["provenance"]["perturbation"]["edge_extraction"] == {
        "is_enabled": True,
        "threshold1": 10.0,
        "threshold2": 20.0,
    }
    assert sample["provenance"]["perturbation"]["applied_operations"] == [
        {
            "name": "apply_gaussian_blur",
            "parameters": {"kernel_size": 3},
        },
        {
            "name": "build_canny_edge_map",
            "parameters": {"threshold1": 10.0, "threshold2": 20.0},
        },
    ]
    assert torch.all((sample["image"] == 0.0) | (sample["image"] == 1.0))


def test_perturbed_dataset_records_sobel_and_log_edge_operation_details() -> None:
    """
    验证扰动数据集会记录Sobel和LoG边缘操作细节
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(
            operations=(
                SobelEdgesConfig(kernel_size=3),
                LaplacianOfGaussianEdgesConfig(kernel_size=3, sigma=0.0),
            ),
        ),
    )

    sample = dataset[0]

    assert sample["provenance"]["perturbation"]["edge_extraction"] == {
        "is_enabled": True,
        "method": "sobel",
        "kernel_size": 3,
        "threshold1": None,
        "threshold2": None,
        "sigma": None,
    }
    assert sample["provenance"]["perturbation"]["applied_operations"] == [
        {
            "name": "build_sobel_edge_map",
            "parameters": {"kernel_size": 3},
        },
        {
            "name": "build_laplacian_of_gaussian_edge_map",
            "parameters": {"kernel_size": 3, "sigma": 0.0},
        },
    ]


def test_perturbed_dataset_keeps_unseeded_noise_stochastic_in_metadata() -> None:
    """
    验证无种子噪声会在元数据中标记为随机模式
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_UnseededRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(2, 2),
    )
    dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(
            operations=(AdditiveGaussianNoiseConfig(sigma=0.05),),
        ),
    )

    sample = dataset[0]

    assert sample["provenance"]["stage"] == "perturbed"
    assert sample["provenance"]["perturbation"]["applied_operations"] == [
        {
            "name": "add_additive_gaussian_noise",
            "parameters": {"sigma": 0.05},
        }
    ]
    assert sample["provenance"]["perturbation"]["noise_rng"] == {
        "mode": "stochastic",
        "sampling_seed": None,
    }


def test_encoded_dataset_builds_optical_input_and_records_encoding_method() -> None:
    """
    验证编码数据集会构建光学输入并记录编码方式
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    dataset = EncodedDataset(
        source_dataset=prepared_dataset,
        encoding_method="intensity",
    )

    sample = dataset[0]

    assert sample["input_image"].shape == (1, 4, 4)
    assert sample["input_image"].dtype == torch.float32
    assert sample["input_field"].shape == (1, 4, 4)
    assert sample["input_field"].dtype == torch.complex64
    assert torch.allclose(
        torch.abs(sample["input_field"]),
        torch.sqrt(sample["input_image"]),
    )
    assert sample["provenance"]["stage"] == "encoded"
    assert sample["provenance"]["encoding_method"] == "intensity"


def test_encoded_dataset_supports_phase_encoding_and_advances_stage() -> None:
    """
    验证编码数据集支持相位编码并推进阶段
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    dataset = EncodedDataset(
        source_dataset=prepared_dataset,
        encoding_method="phase",
    )

    sample = dataset[0]

    assert sample["provenance"]["stage"] == "encoded"
    assert sample["provenance"]["encoding_method"] == "phase"
    assert torch.allclose(
        torch.abs(sample["input_field"]),
        torch.ones_like(sample["input_image"]),
    )


def test_stage_datasets_do_not_alias_source_or_each_other() -> None:
    """
    验证各阶段样本不会共享可变图像张量
    """
    raw_dataset = _TinyRawDataset()
    prepared_dataset = PreparedDataset(
        source_dataset=raw_dataset,
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    encoded_dataset = EncodedDataset(
        source_dataset=prepared_dataset,
        encoding_method="intensity",
    )

    raw_sample = raw_dataset[0]
    prepared_sample = prepared_dataset[0]
    encoded_sample = encoded_dataset[0]

    raw_snapshot = raw_sample["image"].clone()
    encoded_snapshot = encoded_sample["input_image"].clone()

    prepared_sample["image"][0, 1, 1] = 9.0
    encoded_sample["input_image"][0, 1, 2] = 5.0

    assert torch.equal(raw_sample["image"], raw_snapshot)
    assert torch.equal(encoded_dataset[0]["input_image"], encoded_snapshot)


def test_perturbed_dataset_marks_stage_even_without_operations() -> None:
    """
    验证无扰动操作时仍会标记扰动阶段
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(),
    )

    sample = dataset[0]

    assert sample["provenance"]["stage"] == "perturbed"
    assert sample["provenance"]["perturbation"]["applied_operations"] == []
    assert sample["provenance"]["perturbation"]["noise_sigma"] is None
    assert sample["provenance"]["perturbation"]["blur_kernel_size"] is None
    assert sample["provenance"]["perturbation"]["poisson_peak_photons"] is None
    assert sample["provenance"]["perturbation"]["read_noise_sigma"] is None
    assert sample["provenance"]["perturbation"]["psf_kernel"] is None
    assert sample["provenance"]["perturbation"]["degradation_seed"] is None
    assert sample["provenance"]["perturbation"]["edge_extraction"] == {
        "is_enabled": False,
        "threshold1": None,
        "threshold2": None,
    }


def test_perturbed_dataset_applies_poisson_gaussian_noise_and_psf_kernel() -> None:
    """
    验证扰动数据集会应用泊松高斯噪声和PSF卷积核
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    psf_kernel = np.ones((3, 3), dtype=np.float32)
    dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(
            operations=(
                PsfConvolutionConfig(kernel=psf_kernel),
                PoissonGaussianNoiseConfig(
                    peak_photons=50.0,
                    read_noise_sigma=0.01,
                ),
            ),
            degradation_seed=13,
        ),
    )

    sample = dataset[0]

    assert sample["provenance"]["perturbation"]["poisson_peak_photons"] == 50.0
    assert sample["provenance"]["perturbation"]["read_noise_sigma"] == 0.01
    assert sample["provenance"]["perturbation"]["psf_kernel"] == {
        "shape": (3, 3),
        "sum": 9.0,
    }
    assert sample["provenance"]["perturbation"]["degradation_seed"] == 13
    applied_operations = sample["provenance"]["perturbation"]["applied_operations"]
    assert applied_operations[0]["name"] == "apply_psf_kernel"
    assert applied_operations[1]["name"] == "add_poisson_gaussian_noise"


def test_perturbed_dataset_uses_explicit_operation_sequence() -> None:
    """
    验证扰动数据集会按显式操作序列执行
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    psf_kernel = np.ones((3, 3), dtype=np.float32)
    dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(
            operations=(
                GaussianBlurConfig(kernel_size=3),
                PsfConvolutionConfig(kernel=psf_kernel),
                PoissonGaussianNoiseConfig(
                    peak_photons=50.0,
                    read_noise_sigma=0.01,
                ),
            ),
            degradation_seed=13,
        ),
    )

    sample = dataset[0]

    assert sample["provenance"]["perturbation"]["blur_kernel_size"] == 3
    assert sample["provenance"]["perturbation"]["psf_kernel"] == {
        "shape": (3, 3),
        "sum": 9.0,
    }
    assert sample["provenance"]["perturbation"]["degradation_seed"] == 13


def test_perturbed_dataset_applies_nested_defocus_config() -> None:
    """
    验证扰动数据集会应用嵌套离焦配置
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )
    dataset = PerturbedDataset(
        prepared_dataset=prepared_dataset,
        perturbation_config=PerturbationConfig(
            operations=(DefocusBlurConfig(radius=1),),
        ),
    )

    sample = dataset[0]

    assert sample["provenance"]["perturbation"]["applied_operations"] == [
        {"name": "apply_defocus_blur", "parameters": {"radius": 1}}
    ]
    assert "defocus_blur" not in sample["provenance"]["perturbation"]


def test_perturbed_dataset_rejects_missing_operation_config() -> None:
    """
    验证扰动数据集会拒绝缺失的扰动配置
    """
    prepared_dataset = PreparedDataset(
        source_dataset=_TinyRawDataset(),
        image_resolution=(2, 2),
        array_resolution=(4, 4),
    )

    with pytest.raises(TypeError):
        PerturbedDataset(
            prepared_dataset=prepared_dataset,
        )

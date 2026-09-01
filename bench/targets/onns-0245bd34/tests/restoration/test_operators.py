import numpy as np
import pytest
import torch

from data.configs.perturbation import (
    DefocusBlurConfig,
    PerturbationConfig,
    PoissonGaussianNoiseConfig,
)
from data.perturbation.blur.defocus_blur import apply_defocus_blur
from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.fixed_measurement.learning.operators import (
    DefocusKnownOperator,
    defocus_operator_for_dataset,
)


def _clean_image(seed: int = 0) -> np.ndarray:
    """
    鏋勫缓纭畾鎬у共鍑€鍥惧儚
    """
    rng = np.random.default_rng(seed)
    return rng.random((32, 32), dtype=np.float32)


def test_forward_matches_numpy_reference() -> None:
    """
    楠岃瘉鍓嶅悜绠楀瓙鍖归厤 NumPy 鍙傝€冨疄鐜?    """
    radius = 4
    clean = _clean_image()
    reference = apply_defocus_blur(clean, radius=radius)
    operator = DefocusKnownOperator(radius=radius)
    torch_input = torch.from_numpy(clean)[None, None]
    result = operator.forward(torch_input)[0, 0].numpy()
    assert result.shape == reference.shape
    np.testing.assert_allclose(result, reference, atol=1e-5)


def test_adjoint_satisfies_inner_product_identity() -> None:
    """
    楠岃瘉浼撮殢绠楀瓙婊¤冻鍐呯Н鎭掔瓑寮?    """
    operator = DefocusKnownOperator(radius=3)
    x = torch.rand(1, 1, 24, 24)
    y = torch.rand(1, 1, 24, 24)
    lhs = torch.sum(operator.forward(x) * y)
    rhs = torch.sum(x * operator.adjoint(y))
    assert torch.allclose(lhs, rhs, atol=1e-4)


def test_provenance_hash_binds_to_defocus_config() -> None:
    """
    楠岃瘉绠楀瓙鏉ユ簮鍝堝笇缁戝畾绂荤劍閰嶇疆
    """
    operator = DefocusKnownOperator(radius=6)
    assert operator.provenance_hash() == compute_config_hash(DefocusBlurConfig(radius=6))


def test_radius_must_be_positive_integer() -> None:
    """
    楠岃瘉绂荤劍鍗婂緞蹇呴』涓烘鏁存暟
    """
    with pytest.raises(ValueError):
        DefocusKnownOperator(radius=0)


class _DatasetConfigWithPerturbation:
    """
    鎻愪緵鎵板姩瀛楁鐨勬暟鎹厤缃浛韬?    """

    def __init__(self, perturbation: PerturbationConfig) -> None:
        """
        淇濆瓨鎵板姩閰嶇疆
        """
        self.perturbation = perturbation


def _medium_profile_config() -> PerturbationConfig:
    """
    鏋勫缓涓瓑閫€鍖栨壈鍔ㄩ厤缃?    """
    return PerturbationConfig(
        operations=(
            DefocusBlurConfig(radius=6),
            PoissonGaussianNoiseConfig(peak_photons=5.0, read_noise_sigma=0.0),
        )
    )


def test_defocus_operator_for_dataset_derives_medium_profile_operator() -> None:
    """
    楠岃瘉涓瓑閫€鍖栨暟鎹淳鐢熺鐒︾畻瀛?    """
    dataset_config = _DatasetConfigWithPerturbation(_medium_profile_config())

    operator = defocus_operator_for_dataset(dataset_config)

    assert operator is not None
    assert operator.radius == 6
    assert operator.provenance_hash() == compute_config_hash(DefocusBlurConfig(radius=6))


def test_defocus_operator_for_dataset_unwraps_standard_config_wrapper() -> None:
    """
    楠岃瘉绠楀瓙瑙ｆ瀽鏍囧噯鏁版嵁閰嶇疆鍖呰
    """
    dataset_config = {"dataset_config": _DatasetConfigWithPerturbation(_medium_profile_config())}

    operator = defocus_operator_for_dataset(dataset_config)

    assert operator is not None
    assert operator.radius == 6


def test_defocus_operator_for_dataset_returns_none_without_defocus() -> None:
    """
    楠岃瘉鏃犵鐒﹂€€鍖栨椂涓嶆瀯寤虹畻瀛?    """
    perturbation = PerturbationConfig(
        operations=(PoissonGaussianNoiseConfig(peak_photons=5.0, read_noise_sigma=0.0),)
    )
    dataset_config = _DatasetConfigWithPerturbation(perturbation)

    assert defocus_operator_for_dataset(dataset_config) is None


def test_defocus_operator_for_dataset_returns_none_for_opaque_config() -> None:
    """
    楠岃瘉涓嶉€忔槑閰嶇疆涓嶇寽娴嬬鐒︾畻瀛?    """
    assert defocus_operator_for_dataset({"kind": "tiny"}) is None

from __future__ import annotations

from torch.utils.data import Dataset

from data.configs import PerturbationConfig
from data.configs.validation import validate_perturbation
from data.perturbation.blur.defocus_blur import apply_defocus_blur
from data.perturbation.blur.gaussian_blur import apply_gaussian_blur
from data.perturbation.dataset import PerturbedDataset
from data.perturbation.edges.canny_edges import build_canny_edge_map
from data.perturbation.edges.laplacian_of_gaussian_edges import (
    build_laplacian_of_gaussian_edge_map,
)
from data.perturbation.edges.sobel_edges import build_sobel_edge_map
from data.perturbation.executor import apply_perturbation_operations
from data.perturbation.noise.additive_gaussian_noise import add_additive_gaussian_noise
from data.perturbation.noise.poisson_gaussian_noise import add_poisson_gaussian_noise
from data.perturbation.optics.circular_pupil_functions import build_circular_pupil_function
from data.perturbation.optics.coherent_imaging import (
    optical_transfer_function_from_point_spread_function,
    point_spread_function_from_pupil_function,
)
from data.perturbation.optics.low_pass_filters import build_ideal_low_pass_filter


def perturb(source: Dataset, config: PerturbationConfig) -> PerturbedDataset:
    """
    对数据集应用扰动阶段。
    """
    if not isinstance(config, PerturbationConfig):
        raise TypeError("config must be a PerturbationConfig")
    validate_perturbation(config)
    return PerturbedDataset(
        prepared_dataset=source,
        perturbation_config=config,
    )


__all__ = [
    "PerturbedDataset",
    "add_additive_gaussian_noise",
    "add_poisson_gaussian_noise",
    "apply_defocus_blur",
    "apply_gaussian_blur",
    "apply_perturbation_operations",
    "build_canny_edge_map",
    "build_circular_pupil_function",
    "build_ideal_low_pass_filter",
    "build_laplacian_of_gaussian_edge_map",
    "build_sobel_edge_map",
    "optical_transfer_function_from_point_spread_function",
    "point_spread_function_from_pupil_function",
    "perturb",
]

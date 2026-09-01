from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import hashlib
from typing import TypeAlias, TypeVar
import zlib

import numpy as np

from data._validation import (
    validate_non_negative_number,
    validate_positive_int,
    validate_positive_number,
    validate_positive_odd_int,
)
from data.configs.perturbation import (
    AdditiveGaussianNoiseConfig,
    CannyEdgesConfig,
    DefocusBlurConfig,
    GaussianBlurConfig,
    LaplacianOfGaussianEdgesConfig,
    PerturbationOperationConfig,
    PoissonGaussianNoiseConfig,
    PsfConvolutionConfig,
    SobelEdgesConfig,
)

SampleProvenance: TypeAlias = dict[str, object]
OperationConfigT = TypeVar("OperationConfigT")


@dataclass(slots=True, frozen=True)
class PerturbationExecutionContext:
    """
    表示单次扰动执行所需的上下文
    """

    provenance: SampleProvenance
    degradation_seed: int | None


@dataclass(slots=True, frozen=True)
class PerturbationOperationResult:
    """
    表示单个扰动算子的执行结果
    """

    image: np.ndarray
    operation_record: dict[str, object]
    extra_metadata: dict[str, object]


@dataclass(slots=True, frozen=True)
class PerturbationOperationSpec:
    """
    描述扰动算子的配置、校验和执行入口
    """

    config_type: type
    option_names: tuple[str, ...]
    validate: Callable[[object], None]
    apply: Callable[
        [np.ndarray, object, PerturbationExecutionContext],
        PerturbationOperationResult,
    ]
    update_provenance: Callable[[dict[str, object], object], None]


def operation_spec_for(operation: object) -> PerturbationOperationSpec:
    """
    返回与扰动配置实例匹配的算子规格
    """

    for spec in PERTURBATION_OPERATION_SPECS:
        if isinstance(operation, spec.config_type):
            return spec
    raise TypeError(
        f"不支持的扰动算子配置类型: {type(operation)}"
    )


def build_psf_kernel_metadata(psf_kernel: object | None) -> dict[str, object] | None:
    """
    构建 PSF 卷积核的可序列化元数据
    """

    if psf_kernel is None:
        return None
    kernel_array = np.asarray(psf_kernel, dtype=np.float32)
    return {
        "shape": tuple(kernel_array.shape),
        "sum": float(kernel_array.sum()),
    }


def build_perturbation_provenance(
    *,
    operations: Sequence[PerturbationOperationConfig],
    applied_operations: list[dict[str, object]],
    degradation_seed: int | None,
) -> dict[str, object]:
    """
    构建扰动阶段的 provenance 记录
    """

    provenance: dict[str, object] = {
        "noise_sigma": None,
        "blur_kernel_size": None,
        "edge_extraction": {
            "is_enabled": False,
            "threshold1": None,
            "threshold2": None,
        },
        "poisson_peak_photons": None,
        "read_noise_sigma": None,
        "psf_kernel": None,
        "degradation_seed": degradation_seed,
        "applied_operations": applied_operations,
    }
    for operation in operations:
        operation_spec_for(operation).update_provenance(provenance, operation)
    return provenance


def _operation_record(name: str, parameters: dict[str, object]) -> dict[str, object]:
    return {
        "name": name,
        "parameters": parameters,
    }


def _build_seed_parts(
    *,
    provenance: SampleProvenance,
    degradation_seed: int | None,
    operation_name: str | None = None,
) -> list[int] | None:
    sampling_seed = provenance.get("sampling_seed")
    if degradation_seed is None and sampling_seed is None:
        return None

    seed_parts: list[int] = []
    if degradation_seed is not None:
        seed_parts.append(int(degradation_seed))
    if sampling_seed is not None:
        seed_parts.append(int(sampling_seed))
    image_id = provenance.get("image_id")
    if isinstance(image_id, str) and image_id:
        stable_identity = hashlib.sha256(image_id.encode("utf-8")).digest()
        seed_parts.extend(
            int.from_bytes(stable_identity[offset : offset + 4], "big")
            for offset in range(0, 16, 4)
        )
    else:
        for key in ("source_index", "sampled_index"):
            value = provenance.get(key)
            if value is not None:
                seed_parts.append(int(value))
    if operation_name is not None:
        seed_parts.append(zlib.crc32(operation_name.encode("utf-8")))
    return seed_parts


def _build_noise_generator(
    provenance: SampleProvenance,
    *,
    degradation_seed: int | None,
) -> np.random.Generator | None:
    random_seed = _build_degradation_seed(
        provenance=provenance,
        degradation_seed=degradation_seed,
        operation_name="add_additive_gaussian_noise",
    )
    if random_seed is None:
        return None
    return np.random.default_rng(random_seed)


def _build_noise_rng_metadata(
    provenance: SampleProvenance,
    *,
    degradation_seed: int | None,
) -> dict[str, object]:
    random_seed = _build_degradation_seed(
        provenance=provenance,
        degradation_seed=degradation_seed,
        operation_name="add_additive_gaussian_noise",
    )
    sampling_seed = provenance.get("sampling_seed")
    if random_seed is None:
        return {
            "mode": "stochastic",
            "sampling_seed": None,
        }

    return {
        "mode": "deterministic",
        "sampling_seed": int(sampling_seed) if sampling_seed is not None else None,
        "degradation_seed": degradation_seed,
        "source_index": provenance.get("source_index"),
        "sampled_index": provenance.get("sampled_index"),
        "effective_seed": random_seed,
    }


def _build_degradation_seed(
    *,
    provenance: SampleProvenance,
    degradation_seed: int | None,
    operation_name: str | None = None,
) -> int | None:
    seed_parts = _build_seed_parts(
        provenance=provenance,
        degradation_seed=degradation_seed,
        operation_name=operation_name,
    )
    if seed_parts is None:
        return None
    return int(np.random.SeedSequence(seed_parts).generate_state(1)[0])


def _validate_additive_gaussian_noise(operation: object) -> None:
    operation = _as_operation(operation, AdditiveGaussianNoiseConfig)
    validate_non_negative_number("noise_sigma", operation.sigma)


def _apply_additive_gaussian_noise(
    image: np.ndarray,
    operation: object,
    context: PerturbationExecutionContext,
) -> PerturbationOperationResult:
    from data.perturbation.noise.additive_gaussian_noise import (
        add_additive_gaussian_noise,
    )

    operation = _as_operation(operation, AdditiveGaussianNoiseConfig)
    output = add_additive_gaussian_noise(
        image,
        sigma=operation.sigma,
        random_generator=_build_noise_generator(
            context.provenance,
            degradation_seed=context.degradation_seed,
        ),
    )
    return PerturbationOperationResult(
        image=output,
        operation_record=_operation_record(
            "add_additive_gaussian_noise",
            {"sigma": operation.sigma},
        ),
        extra_metadata={
            "noise_rng": _build_noise_rng_metadata(
                context.provenance,
                degradation_seed=context.degradation_seed,
            )
        },
    )


def _record_additive_gaussian_noise(
    provenance: dict[str, object],
    operation: object,
) -> None:
    if provenance["noise_sigma"] is not None:
        return
    operation = _as_operation(operation, AdditiveGaussianNoiseConfig)
    provenance["noise_sigma"] = operation.sigma


def _validate_gaussian_blur(operation: object) -> None:
    operation = _as_operation(operation, GaussianBlurConfig)
    validate_positive_odd_int("blur_kernel_size", operation.kernel_size)


def _apply_gaussian_blur(
    image: np.ndarray,
    operation: object,
    context: PerturbationExecutionContext,
) -> PerturbationOperationResult:
    from data.perturbation.blur.gaussian_blur import apply_gaussian_blur

    operation = _as_operation(operation, GaussianBlurConfig)
    return PerturbationOperationResult(
        image=apply_gaussian_blur(image, kernel_size=operation.kernel_size),
        operation_record=_operation_record(
            "apply_gaussian_blur",
            {"kernel_size": operation.kernel_size},
        ),
        extra_metadata={},
    )


def _record_gaussian_blur(provenance: dict[str, object], operation: object) -> None:
    if provenance["blur_kernel_size"] is not None:
        return
    operation = _as_operation(operation, GaussianBlurConfig)
    provenance["blur_kernel_size"] = operation.kernel_size


def _validate_defocus_blur(operation: object) -> None:
    operation = _as_operation(operation, DefocusBlurConfig)
    validate_positive_int("defocus_blur_radius", operation.radius)


def _apply_defocus_blur(
    image: np.ndarray,
    operation: object,
    context: PerturbationExecutionContext,
) -> PerturbationOperationResult:
    from data.perturbation.blur.defocus_blur import apply_defocus_blur

    operation = _as_operation(operation, DefocusBlurConfig)
    return PerturbationOperationResult(
        image=apply_defocus_blur(image, radius=operation.radius),
        operation_record=_operation_record(
            "apply_defocus_blur",
            {"radius": operation.radius},
        ),
        extra_metadata={},
    )


def _record_noop(provenance: dict[str, object], operation: object) -> None:
    return


def _validate_poisson_gaussian_noise(operation: object) -> None:
    operation = _as_operation(operation, PoissonGaussianNoiseConfig)
    validate_positive_number(
        "poisson_peak_photons",
        operation.peak_photons,
    )
    validate_non_negative_number(
        "read_noise_sigma",
        operation.read_noise_sigma,
    )


def _apply_poisson_gaussian_noise(
    image: np.ndarray,
    operation: object,
    context: PerturbationExecutionContext,
) -> PerturbationOperationResult:
    from data.perturbation.noise.poisson_gaussian_noise import (
        add_poisson_gaussian_noise,
    )

    operation = _as_operation(operation, PoissonGaussianNoiseConfig)
    poisson_seed = _build_degradation_seed(
        provenance=context.provenance,
        degradation_seed=context.degradation_seed,
        operation_name="add_poisson_gaussian_noise",
    )
    output = add_poisson_gaussian_noise(
        image,
        peak_photons=operation.peak_photons,
        read_noise_sigma=operation.read_noise_sigma,
        random_seed=poisson_seed,
    )
    return PerturbationOperationResult(
        image=output,
        operation_record=_operation_record(
            "add_poisson_gaussian_noise",
            {
                "peak_photons": operation.peak_photons,
                "read_noise_sigma": operation.read_noise_sigma,
                "random_seed": poisson_seed,
            },
        ),
        extra_metadata={},
    )


def _record_poisson_gaussian_noise(
    provenance: dict[str, object],
    operation: object,
) -> None:
    if provenance["poisson_peak_photons"] is not None:
        return
    operation = _as_operation(operation, PoissonGaussianNoiseConfig)
    provenance["poisson_peak_photons"] = operation.peak_photons
    provenance["read_noise_sigma"] = operation.read_noise_sigma


def _validate_canny_edges(operation: object) -> None:
    operation = _as_operation(operation, CannyEdgesConfig)
    validate_non_negative_number("edge_threshold1", operation.threshold1)
    validate_non_negative_number("edge_threshold2", operation.threshold2)


def _apply_canny_edges(
    image: np.ndarray,
    operation: object,
    context: PerturbationExecutionContext,
) -> PerturbationOperationResult:
    from data.perturbation.edges.canny_edges import build_canny_edge_map

    operation = _as_operation(operation, CannyEdgesConfig)
    return PerturbationOperationResult(
        image=build_canny_edge_map(
            image,
            threshold1=operation.threshold1,
            threshold2=operation.threshold2,
        ),
        operation_record=_operation_record(
            "build_canny_edge_map",
            {"threshold1": operation.threshold1, "threshold2": operation.threshold2},
        ),
        extra_metadata={},
    )


def _record_canny_edges(provenance: dict[str, object], operation: object) -> None:
    operation = _as_operation(operation, CannyEdgesConfig)
    provenance["edge_extraction"] = {
        "is_enabled": True,
        "threshold1": operation.threshold1,
        "threshold2": operation.threshold2,
    }


def _validate_sobel_edges(operation: object) -> None:
    operation = _as_operation(operation, SobelEdgesConfig)
    validate_positive_odd_int("edge_kernel_size", operation.kernel_size)


def _apply_sobel_edges(
    image: np.ndarray,
    operation: object,
    context: PerturbationExecutionContext,
) -> PerturbationOperationResult:
    from data.perturbation.edges.sobel_edges import build_sobel_edge_map

    operation = _as_operation(operation, SobelEdgesConfig)
    return PerturbationOperationResult(
        image=build_sobel_edge_map(image, kernel_size=operation.kernel_size),
        operation_record=_operation_record(
            "build_sobel_edge_map",
            {"kernel_size": operation.kernel_size},
        ),
        extra_metadata={},
    )


def _record_sobel_edges(provenance: dict[str, object], operation: object) -> None:
    edge_extraction = provenance.get("edge_extraction")
    if isinstance(edge_extraction, dict) and edge_extraction.get("is_enabled") is True:
        return
    operation = _as_operation(operation, SobelEdgesConfig)
    provenance["edge_extraction"] = {
        "is_enabled": True,
        "method": "sobel",
        "kernel_size": operation.kernel_size,
        "threshold1": None,
        "threshold2": None,
        "sigma": None,
    }


def _validate_laplacian_of_gaussian_edges(operation: object) -> None:
    operation = _as_operation(operation, LaplacianOfGaussianEdgesConfig)
    validate_positive_odd_int("edge_kernel_size", operation.kernel_size)
    validate_non_negative_number("edge_sigma", operation.sigma)


def _apply_laplacian_of_gaussian_edges(
    image: np.ndarray,
    operation: object,
    context: PerturbationExecutionContext,
) -> PerturbationOperationResult:
    from data.perturbation.edges.laplacian_of_gaussian_edges import (
        build_laplacian_of_gaussian_edge_map,
    )

    operation = _as_operation(operation, LaplacianOfGaussianEdgesConfig)
    return PerturbationOperationResult(
        image=build_laplacian_of_gaussian_edge_map(
            image,
            kernel_size=operation.kernel_size,
            sigma=operation.sigma,
        ),
        operation_record=_operation_record(
            "build_laplacian_of_gaussian_edge_map",
            {"kernel_size": operation.kernel_size, "sigma": operation.sigma},
        ),
        extra_metadata={},
    )


def _record_laplacian_of_gaussian_edges(
    provenance: dict[str, object],
    operation: object,
) -> None:
    edge_extraction = provenance.get("edge_extraction")
    if isinstance(edge_extraction, dict) and edge_extraction.get("is_enabled") is True:
        return
    operation = _as_operation(operation, LaplacianOfGaussianEdgesConfig)
    provenance["edge_extraction"] = {
        "is_enabled": True,
        "method": "laplacian_of_gaussian",
        "kernel_size": operation.kernel_size,
        "threshold1": None,
        "threshold2": None,
        "sigma": operation.sigma,
    }


def _validate_psf_convolution(operation: object) -> None:
    operation = _as_operation(operation, PsfConvolutionConfig)
    kernel_array = np.asarray(operation.kernel)
    if kernel_array.ndim != 2:
        raise ValueError(
            f"psf_kernel必须是二维数组，收到shape={kernel_array.shape}"
        )
    if not np.all(np.isfinite(kernel_array)):
        raise ValueError(
            "psf_kernel只能包含有限数值"
        )
    if np.any(kernel_array < 0.0):
        raise ValueError(
            "psf_kernel不能包含负值"
        )
    if float(kernel_array.sum()) <= 0.0:
        raise ValueError(
            "psf_kernel能量必须为正"
        )


def _apply_psf_convolution(
    image: np.ndarray,
    operation: object,
    context: PerturbationExecutionContext,
) -> PerturbationOperationResult:
    import cv2

    operation = _as_operation(operation, PsfConvolutionConfig)
    kernel_array = np.asarray(operation.kernel, dtype=np.float32)
    if kernel_array.ndim != 2:
        raise ValueError(
            "psf_kernel必须是二维数组"
        )
    kernel_sum = float(kernel_array.sum())
    if kernel_sum != 0.0:
        kernel_array = kernel_array / kernel_sum
    filtered_image = cv2.filter2D(
        image.astype(np.float32, copy=False),
        ddepth=-1,
        kernel=kernel_array,
        borderType=cv2.BORDER_REFLECT,
    )
    filtered_image = np.clip(filtered_image, 0.0, 1.0)
    return PerturbationOperationResult(
        image=filtered_image.astype(np.float32, copy=False),
        operation_record=_operation_record(
            "apply_psf_kernel",
            build_psf_kernel_metadata(operation.kernel) or {},
        ),
        extra_metadata={},
    )


def _record_psf_convolution(provenance: dict[str, object], operation: object) -> None:
    if provenance["psf_kernel"] is not None:
        return
    operation = _as_operation(operation, PsfConvolutionConfig)
    provenance["psf_kernel"] = build_psf_kernel_metadata(operation.kernel)

def _as_operation(
    operation: object,
    operation_type: type[OperationConfigT],
) -> OperationConfigT:
    if not isinstance(operation, operation_type):
        raise TypeError(
            f"不支持的扰动算子配置类型: {type(operation)}"
        )
    return operation


PERTURBATION_OPERATION_SPECS = (
    PerturbationOperationSpec(
        config_type=AdditiveGaussianNoiseConfig,
        option_names=("noise_sigma",),
        validate=_validate_additive_gaussian_noise,
        apply=_apply_additive_gaussian_noise,
        update_provenance=_record_additive_gaussian_noise,
    ),
    PerturbationOperationSpec(
        config_type=GaussianBlurConfig,
        option_names=("blur_kernel_size",),
        validate=_validate_gaussian_blur,
        apply=_apply_gaussian_blur,
        update_provenance=_record_gaussian_blur,
    ),
    PerturbationOperationSpec(
        config_type=DefocusBlurConfig,
        option_names=("defocus_blur",),
        validate=_validate_defocus_blur,
        apply=_apply_defocus_blur,
        update_provenance=_record_noop,
    ),
    PerturbationOperationSpec(
        config_type=PoissonGaussianNoiseConfig,
        option_names=("poisson_peak_photons", "read_noise_sigma"),
        validate=_validate_poisson_gaussian_noise,
        apply=_apply_poisson_gaussian_noise,
        update_provenance=_record_poisson_gaussian_noise,
    ),
    PerturbationOperationSpec(
        config_type=CannyEdgesConfig,
        option_names=("enable_edge_extraction",),
        validate=_validate_canny_edges,
        apply=_apply_canny_edges,
        update_provenance=_record_canny_edges,
    ),
    PerturbationOperationSpec(
        config_type=SobelEdgesConfig,
        option_names=("enable_edge_extraction", "edge_kernel_size"),
        validate=_validate_sobel_edges,
        apply=_apply_sobel_edges,
        update_provenance=_record_sobel_edges,
    ),
    PerturbationOperationSpec(
        config_type=LaplacianOfGaussianEdgesConfig,
        option_names=("enable_edge_extraction", "edge_kernel_size", "edge_sigma"),
        validate=_validate_laplacian_of_gaussian_edges,
        apply=_apply_laplacian_of_gaussian_edges,
        update_provenance=_record_laplacian_of_gaussian_edges,
    ),
    PerturbationOperationSpec(
        config_type=PsfConvolutionConfig,
        option_names=("psf_kernel",),
        validate=_validate_psf_convolution,
        apply=_apply_psf_convolution,
        update_provenance=_record_psf_convolution,
    ),
)

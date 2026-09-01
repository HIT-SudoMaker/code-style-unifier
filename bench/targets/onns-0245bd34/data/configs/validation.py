from __future__ import annotations

from typing import get_args

from data._validation import (
    _format_supported_values,
    normalize_resolution_pair,
    validate_bool,
    validate_int,
    validate_non_negative_int,
    validate_optional_positive_int,
)
from data.configs.perturbation import PerturbationConfig
from data.configs.perturbation_registry import operation_spec_for
from data.configs.stages import (
    EncodingConfig,
    EncodingMethod,
    NormalizationMethod,
    PreparationConfig,
    ResizeMethod,
    SourceConfig,
)

NORMALIZATION_METHODS = frozenset(get_args(NormalizationMethod))
RESIZE_METHODS = frozenset(get_args(ResizeMethod))
ENCODING_METHODS = frozenset(get_args(EncodingMethod))


def validate_source(config: SourceConfig) -> None:
    """Validate a source-stage configuration."""
    if not isinstance(config.dataset_name, str) or not config.dataset_name.strip():
        raise ValueError("dataset_name must be a non-empty string")
    validate_bool("source.is_train", config.is_train)
    validate_optional_positive_int("samples_per_class", config.samples_per_class)
    validate_optional_positive_int("max_samples", config.max_samples)
    validate_int("random_seed", config.random_seed)


def validate_preparation(config: PreparationConfig) -> None:
    """Validate a preparation-stage configuration."""
    image_resolution = normalize_resolution_pair(
        "image_resolution",
        config.image_resolution,
    )
    array_resolution = normalize_resolution_pair(
        "array_resolution",
        config.array_resolution,
    )
    if any(image > array for image, array in zip(image_resolution, array_resolution)):
        raise ValueError("image_resolution must fit inside array_resolution")

    validate_non_negative_int("edge_taper_width", config.edge_taper_width)
    if config.edge_taper_width > min(image_resolution) // 2:
        raise ValueError("edge_taper_width exceeds prepared image support")

    if config.normalization_method not in NORMALIZATION_METHODS:
        raise ValueError(
            _format_supported_values(
                "normalization_method",
                sorted(NORMALIZATION_METHODS),
                config.normalization_method,
            )
        )
    if config.resize_interpolation_method not in RESIZE_METHODS:
        raise ValueError(
            _format_supported_values(
                "resize_interpolation_method",
                sorted(RESIZE_METHODS),
                config.resize_interpolation_method,
            )
        )


def validate_perturbation(config: PerturbationConfig) -> None:
    """Validate an ordered perturbation recipe."""
    if config.degradation_seed is not None:
        validate_int("degradation_seed", config.degradation_seed)
    for operation in config.operations:
        operation_spec_for(operation).validate(operation)


def validate_encoding(config: EncodingConfig) -> None:
    """Validate an optical encoding configuration."""
    if config.encoding_method not in ENCODING_METHODS:
        raise ValueError(
            _format_supported_values(
                "encoding_method",
                sorted(ENCODING_METHODS),
                config.encoding_method,
            )
        )

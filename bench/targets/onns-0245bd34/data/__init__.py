from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from torch.utils.data import Dataset

    from data.configs import (
        EncodingConfig,
        PerturbationConfig,
        PreparationConfig,
        SourceConfig,
    )

__all__ = ("load", "prepare", "perturb", "encode")


def load(config: SourceConfig) -> Dataset:
    """Load a registered raw data source."""
    from data.data_source.registry import load as load_source

    return load_source(config)


def prepare(source: Dataset, config: PreparationConfig) -> Dataset:
    """Apply the preparation stage."""
    from data.preparation import prepare as prepare_source

    return prepare_source(source, config)


def perturb(source: Dataset, config: PerturbationConfig) -> Dataset:
    """Apply the perturbation stage."""
    from data.perturbation import perturb as perturb_source

    return perturb_source(source, config)


def encode(source: Dataset, config: EncodingConfig) -> Dataset:
    """Apply the optical encoding stage."""
    from data.encoding import encode as encode_source

    return encode_source(source, config)

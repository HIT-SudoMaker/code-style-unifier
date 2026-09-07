from __future__ import annotations

from types import MappingProxyType
from typing import Final

from data.configs import (
    DefocusBlurConfig,
    PerturbationConfig,
    PoissonGaussianNoiseConfig,
)
from experiments.restoration.errors import invalid_restoration_contract


STANDARD_RESTORATION_PROFILE_NAMES: Final[tuple[str, ...]] = (
    "light",
    "medium",
    "heavy",
)
RESTORATION_DEGRADATION_SEED: Final[int] = 2026

STANDARD_RESTORATION_PROFILES: Final[MappingProxyType[str, PerturbationConfig]] = (
    MappingProxyType(
        {
            "light": PerturbationConfig(
                degradation_seed=RESTORATION_DEGRADATION_SEED,
                operations=(
                    DefocusBlurConfig(radius=4),
                    PoissonGaussianNoiseConfig(
                        peak_photons=8.0,
                        read_noise_sigma=0.0,
                    ),
                ),
            ),
            "medium": PerturbationConfig(
                degradation_seed=RESTORATION_DEGRADATION_SEED,
                operations=(
                    DefocusBlurConfig(radius=6),
                    PoissonGaussianNoiseConfig(
                        peak_photons=5.0,
                        read_noise_sigma=0.0,
                    ),
                ),
            ),
            "heavy": PerturbationConfig(
                degradation_seed=RESTORATION_DEGRADATION_SEED,
                operations=(
                    DefocusBlurConfig(radius=6),
                    PoissonGaussianNoiseConfig(
                        peak_photons=3.0,
                        read_noise_sigma=0.0,
                    ),
                ),
            ),
        }
    )
)


def restoration_profile(name: str) -> PerturbationConfig:
    """Return one immutable degradation profile shared by both experiments."""
    if name not in STANDARD_RESTORATION_PROFILES:
        allowed = ", ".join(STANDARD_RESTORATION_PROFILE_NAMES)
        raise invalid_restoration_contract(f"profile_name must be one of: {allowed}")
    return STANDARD_RESTORATION_PROFILES[name]

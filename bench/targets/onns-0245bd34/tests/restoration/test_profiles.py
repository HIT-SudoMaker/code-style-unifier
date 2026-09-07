from __future__ import annotations

from types import MappingProxyType

import pytest

from data.configs import DefocusBlurConfig, PoissonGaussianNoiseConfig
from experiments.restoration.degradation import (
    RESTORATION_DEGRADATION_SEED,
    STANDARD_RESTORATION_PROFILE_NAMES,
    STANDARD_RESTORATION_PROFILES,
    restoration_profile,
)


LEGACY_DEGRADED_PROFILE_NAMES = tuple(
    f"{profile_name}_degraded" for profile_name in ("light", "medium", "heavy")
)


def test_standard_restoration_profiles_use_canonical_names() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    assert STANDARD_RESTORATION_PROFILE_NAMES == ("light", "medium", "heavy")
    assert tuple(STANDARD_RESTORATION_PROFILES) == ("light", "medium", "heavy")
    for legacy_profile_name in LEGACY_DEGRADED_PROFILE_NAMES:
        assert legacy_profile_name not in STANDARD_RESTORATION_PROFILES


def test_standard_restoration_profiles_registry_is_immutable() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    assert isinstance(STANDARD_RESTORATION_PROFILES, MappingProxyType)

    with pytest.raises(TypeError):
        STANDARD_RESTORATION_PROFILES["extra"] = restoration_profile("light")  # type: ignore[index]


def test_restoration_profile_returns_registered_instance() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    profile = restoration_profile("light")

    assert profile is STANDARD_RESTORATION_PROFILES["light"]


def test_standard_restoration_profiles_preserve_historical_values() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    light = restoration_profile("light")
    medium = restoration_profile("medium")
    heavy = restoration_profile("heavy")

    assert light.operations == (
        DefocusBlurConfig(radius=4),
        PoissonGaussianNoiseConfig(peak_photons=8.0, read_noise_sigma=0.0),
    )
    assert medium.operations == (
        DefocusBlurConfig(radius=6),
        PoissonGaussianNoiseConfig(peak_photons=5.0, read_noise_sigma=0.0),
    )
    assert heavy.operations == (
        DefocusBlurConfig(radius=6),
        PoissonGaussianNoiseConfig(peak_photons=3.0, read_noise_sigma=0.0),
    )


def test_standard_restoration_profiles_freeze_each_degradation_realization() -> None:
    """
    楠岃瘉鍥哄畾娴嬮噺鍗忚鐨勯€€鍖栦笉闅忚鍙栨鏁版垨璁粌杞婕傜Щ
    """
    assert RESTORATION_DEGRADATION_SEED == 2026
    assert {
        profile.degradation_seed
        for profile in STANDARD_RESTORATION_PROFILES.values()
    } == {RESTORATION_DEGRADATION_SEED}


@pytest.mark.parametrize(
    "legacy_name",
    LEGACY_DEGRADED_PROFILE_NAMES,
)
def test_restoration_profile_rejects_legacy_degraded_aliases(
    legacy_name: str,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="light, medium, heavy"):
        restoration_profile(legacy_name)

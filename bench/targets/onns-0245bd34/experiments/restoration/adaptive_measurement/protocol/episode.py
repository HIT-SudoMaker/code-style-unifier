from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Integral

import torch

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.pupil_aberrations import SUPPORTED_PUPIL_MODES
from experiments.restoration.value_contracts import finite_real


_MINIMUM_SAFE_OBSERVATION_COUNT = 5


@dataclass(frozen=True, slots=True)
class AdaptiveEpisodePolicy:
    """Freeze inference, admission, Echo, and observation-budget decisions."""

    fitted_mode_names: tuple[str, ...] = SUPPORTED_PUPIL_MODES
    fit_iteration_count: int = 150
    fit_learning_rate: float = 0.05
    coefficient_regularization: float = 1e-5
    coefficient_limit_radians: float = 3.0
    maximum_design_condition_number: float = 5.0
    maximum_fit_nrmse: float = 0.25
    maximum_reachability_residual_rms: float = 0.25
    minimum_predicted_gain_db: float = 1.0
    echo_conformity_threshold: float = 0.05
    maximum_observation_count: int = 9

    def __post_init__(self) -> None:
        modes = tuple(self.fitted_mode_names)
        if not modes or len(modes) != len(set(modes)):
            raise invalid_restoration_contract(
                "fitted_mode_names must be non-empty and unique"
            )
        if any(mode not in SUPPORTED_PUPIL_MODES for mode in modes):
            raise invalid_restoration_contract(
                "fitted_mode_names contains an unsupported mode"
            )
        object.__setattr__(self, "fitted_mode_names", modes)
        fit_iteration_count = self.fit_iteration_count
        if (
            isinstance(fit_iteration_count, bool)
            or not isinstance(fit_iteration_count, Integral)
            or int(fit_iteration_count) <= 0
        ):
            raise invalid_restoration_contract(
                "fit_iteration_count must be a positive integer"
            )
        object.__setattr__(self, "fit_iteration_count", int(fit_iteration_count))
        observation_count = self.maximum_observation_count
        if (
            isinstance(observation_count, bool)
            or not isinstance(observation_count, Integral)
            or int(observation_count) < _MINIMUM_SAFE_OBSERVATION_COUNT
        ):
            raise invalid_restoration_contract(
                "maximum_observation_count must be an integer of at least 5"
            )
        object.__setattr__(
            self,
            "maximum_observation_count",
            int(observation_count),
        )
        for name in (
            "fit_learning_rate",
            "coefficient_limit_radians",
            "maximum_design_condition_number",
            "maximum_fit_nrmse",
            "maximum_reachability_residual_rms",
            "echo_conformity_threshold",
        ):
            value = finite_real(name, getattr(self, name))
            if value <= 0.0:
                raise invalid_restoration_contract(f"{name} must be positive")
            object.__setattr__(self, name, value)
        regularization = finite_real(
            "coefficient_regularization",
            self.coefficient_regularization,
        )
        if regularization < 0.0:
            raise invalid_restoration_contract(
                "coefficient_regularization must be nonnegative"
            )
        object.__setattr__(self, "coefficient_regularization", regularization)
        object.__setattr__(
            self,
            "minimum_predicted_gain_db",
            finite_real(
                "minimum_predicted_gain_db",
                self.minimum_predicted_gain_db,
            ),
        )


@dataclass(frozen=True, slots=True, eq=False)
class AdaptiveEpisodeRequest:
    """Declare only policy-visible replay data and one episode policy."""

    episode_id: str
    displayed_replay_intensity: torch.Tensor
    policy: AdaptiveEpisodePolicy = field(default_factory=AdaptiveEpisodePolicy)

    def __post_init__(self) -> None:
        if not isinstance(self.episode_id, str) or not self.episode_id.strip():
            raise invalid_restoration_contract("episode_id must be non-empty")
        intensity = self.displayed_replay_intensity
        if (
            not isinstance(intensity, torch.Tensor)
            or intensity.ndim != 3
            or intensity.shape[0] != 1
            or torch.is_complex(intensity)
            or not bool(torch.isfinite(intensity).all())
            or bool(torch.any(intensity < 0.0))
        ):
            raise invalid_restoration_contract(
                "displayed_replay_intensity must be a finite nonnegative [1, height, width] tensor"
            )
        if not isinstance(self.policy, AdaptiveEpisodePolicy):
            raise TypeError("policy must be an AdaptiveEpisodePolicy")
        object.__setattr__(
            self,
            "displayed_replay_intensity",
            intensity.to(dtype=torch.float32).detach().clone(),
        )

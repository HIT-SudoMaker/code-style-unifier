from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral
from typing import Protocol, runtime_checkable

import torch
from torch.nn import functional

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    CoherentPupilBench,
    CoherentPupilScene,
)
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.observations import ObservationKind, OpticalObservation
from experiments.restoration.phase_control import PhaseCommand
from experiments.restoration.value_contracts import finite_real


@runtime_checkable
class DeliveredPhaseOracleBench(Protocol):
    """Acquire evaluator-only intensities from one bound physical scene."""

    def acquire(
        self,
        command: PhaseCommand,
        *,
        observation_id: str,
        kind: ObservationKind,
        sequence_index: int,
    ) -> OpticalObservation:
        """Acquire one observation under a candidate command."""


@dataclass(frozen=True, slots=True)
class BoundCoherentPupilEvaluator:
    """Bind a coherent scene once so an oracle can vary only its command."""

    bench: CoherentPupilBench
    scene: CoherentPupilScene

    def __post_init__(self) -> None:
        if not isinstance(self.bench, CoherentPupilBench):
            raise TypeError("bench must be a CoherentPupilBench")
        if not isinstance(self.scene, CoherentPupilScene):
            raise TypeError("scene must be a CoherentPupilScene")

    def acquire(
        self,
        command: PhaseCommand,
        *,
        observation_id: str,
        kind: ObservationKind,
        sequence_index: int,
    ) -> OpticalObservation:
        """Acquire from the bound scene without exposing it to the search."""
        return self.bench.acquire(
            self.scene,
            command,
            observation_id=observation_id,
            kind=kind,
            sequence_index=sequence_index,
        )


@dataclass(frozen=True, slots=True)
class DeliveredPhaseOracleCandidate:
    """One auditable command, raw observation, and evaluator-only score."""

    observation: OpticalObservation
    command_multiplier: float
    spatial_detail_strength: float
    mean_square_error: float

    def __post_init__(self) -> None:
        if not isinstance(self.observation, OpticalObservation):
            raise TypeError("observation must be an OpticalObservation")
        object.__setattr__(
            self,
            "command_multiplier",
            finite_real("command_multiplier", self.command_multiplier),
        )
        object.__setattr__(
            self,
            "spatial_detail_strength",
            finite_real("spatial_detail_strength", self.spatial_detail_strength),
        )
        mean_square_error = finite_real(
            "mean_square_error",
            self.mean_square_error,
        )
        if mean_square_error < 0.0:
            raise invalid_restoration_contract("mean_square_error must be nonnegative")
        object.__setattr__(self, "mean_square_error", mean_square_error)


@dataclass(frozen=True, slots=True)
class DeliveredPhaseOracleSearch:
    """An immutable candidate trace and its selected calibrated command."""

    command: PhaseCommand
    candidates: tuple[DeliveredPhaseOracleCandidate, ...]
    selected_candidate_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.command, PhaseCommand):
            raise TypeError("command must be a PhaseCommand")
        if (
            not isinstance(self.candidates, tuple)
            or not self.candidates
            or not all(
                isinstance(candidate, DeliveredPhaseOracleCandidate)
                for candidate in self.candidates
            )
        ):
            raise invalid_restoration_contract(
                "candidates must be a non-empty tuple of oracle candidates"
            )
        if (
            isinstance(self.selected_candidate_index, bool)
            or not isinstance(self.selected_candidate_index, Integral)
            or not 0 <= int(self.selected_candidate_index) < len(self.candidates)
        ):
            raise invalid_restoration_contract(
                "selected_candidate_index must identify one candidate"
            )
        object.__setattr__(
            self,
            "selected_candidate_index",
            int(self.selected_candidate_index),
        )
        selected = self.candidates[int(self.selected_candidate_index)]
        if not torch.allclose(
            self.command.phase_radians,
            selected.observation.command_phase_radians,
            atol=1e-7,
            rtol=1e-7,
        ) or not math.isclose(
            self.command.piston_radians,
            selected.observation.command_piston_radians,
            abs_tol=1e-9,
        ):
            raise invalid_restoration_contract(
                "command must match the selected candidate observation"
            )
        if any(
            candidate.mean_square_error < selected.mean_square_error
            for candidate in self.candidates
        ):
            raise invalid_restoration_contract(
                "selected candidate must minimize mean_square_error"
            )

    @property
    def candidate_count(self) -> int:
        """Return the number of physically evaluated candidates."""
        return len(self.candidates)

    @property
    def selected_candidate(self) -> DeliveredPhaseOracleCandidate:
        """Return the candidate from which the final command was named."""
        return self.candidates[self.selected_candidate_index]

    @property
    def selected_candidate_observation_id(self) -> str:
        """Return the raw observation that selected the final command."""
        return self.selected_candidate.observation.observation_id

    @property
    def selected_command_multiplier(self) -> float:
        """Return the selected calibrated command multiplier."""
        return self.selected_candidate.command_multiplier

    @property
    def selected_spatial_detail_strength(self) -> float:
        """Return the selected spatial-detail strength."""
        return self.selected_candidate.spatial_detail_strength

    @property
    def mean_square_error(self) -> float:
        """Return the selected candidate's evaluator-only error."""
        return self.selected_candidate.mean_square_error


@torch.no_grad()
def search_calibrated_delivered_phase(
    bench: DeliveredPhaseOracleBench,
    evaluator_target_intensity: torch.Tensor,
    calibrated_seed: PhaseCommand,
    *,
    pupil: torch.Tensor,
    command_multipliers: tuple[float, ...],
    spatial_detail_strengths: tuple[float, ...],
    command_id: str,
    observation_id_prefix: str,
    sequence_index_start: int,
) -> DeliveredPhaseOracleSearch:
    """Search around one calibrated command while keeping truth evaluator-only."""
    if not isinstance(bench, DeliveredPhaseOracleBench):
        raise TypeError("bench must satisfy DeliveredPhaseOracleBench")
    if not isinstance(calibrated_seed, PhaseCommand):
        raise TypeError("calibrated_seed must be a PhaseCommand")
    pupil_plane = _pupil_plane(pupil)
    resolution = tuple(pupil_plane.shape)
    target = _target_intensity(evaluator_target_intensity)
    if tuple(target.shape[-2:]) != resolution:
        raise invalid_restoration_contract(
            "evaluator_target_intensity must match the pupil resolution"
        )
    if tuple(calibrated_seed.phase_radians.shape) != resolution:
        raise invalid_restoration_contract(
            "calibrated_seed phase must match the pupil resolution"
        )
    multipliers = _finite_candidates(
        "command_multipliers",
        command_multipliers,
        must_be_positive=True,
    )
    detail_strengths = _finite_candidates(
        "spatial_detail_strengths",
        spatial_detail_strengths,
        must_be_positive=False,
    )
    for name, value in (
        ("command_id", command_id),
        ("observation_id_prefix", observation_id_prefix),
    ):
        if not isinstance(value, str) or not value.strip():
            raise invalid_restoration_contract(f"{name} must be non-empty")
    if (
        isinstance(sequence_index_start, bool)
        or not isinstance(sequence_index_start, Integral)
        or int(sequence_index_start) < 0
    ):
        raise invalid_restoration_contract(
            "sequence_index_start must be a nonnegative integer"
        )

    smoothed_phase = functional.avg_pool2d(
        calibrated_seed.phase_radians[None, None],
        kernel_size=3,
        stride=1,
        padding=1,
    )[0, 0]
    spatial_detail = (calibrated_seed.phase_radians - smoothed_phase) * pupil_plane.to(
        calibrated_seed.phase_radians.device
    )
    best_error = math.inf
    candidate_trace: list[DeliveredPhaseOracleCandidate] = []
    selected_candidate_index = -1
    candidate_index = 0

    for multiplier in multipliers:
        for detail_strength in detail_strengths:
            desired_spatial_phase = (
                calibrated_seed.phase_radians + detail_strength * spatial_detail
            ) * multiplier
            candidate = PhaseCommand(
                f"{command_id}-candidate-{candidate_index:03d}",
                desired_spatial_phase,
                piston_radians=calibrated_seed.piston_radians * multiplier,
            )
            observation = bench.acquire(
                candidate,
                observation_id=f"{observation_id_prefix}-{candidate_index:03d}",
                kind="science",
                sequence_index=int(sequence_index_start) + candidate_index,
            )
            error = float(torch.mean((observation.intensity - target).square()).item())
            candidate_trace.append(
                DeliveredPhaseOracleCandidate(
                    observation=observation,
                    command_multiplier=multiplier,
                    spatial_detail_strength=detail_strength,
                    mean_square_error=error,
                )
            )
            if error < best_error:
                best_error = error
                selected_candidate_index = candidate_index
            candidate_index += 1

    candidates = tuple(candidate_trace)
    selected_candidate = candidates[selected_candidate_index]
    selected_observation = selected_candidate.observation
    return DeliveredPhaseOracleSearch(
        command=PhaseCommand(
            command_id,
            selected_observation.command_phase_radians,
            piston_radians=selected_observation.command_piston_radians,
        ),
        candidates=candidates,
        selected_candidate_index=selected_candidate_index,
    )


def _target_intensity(value: torch.Tensor) -> torch.Tensor:
    if (
        not isinstance(value, torch.Tensor)
        or value.ndim < 2
        or value.numel() == 0
        or torch.is_complex(value)
        or not bool(torch.isfinite(value).all())
        or bool(torch.any(value < 0.0))
    ):
        raise invalid_restoration_contract(
            "evaluator_target_intensity must be a finite nonnegative tensor"
        )
    return value


def _pupil_plane(value: torch.Tensor) -> torch.Tensor:
    if (
        not isinstance(value, torch.Tensor)
        or value.ndim != 2
        or value.numel() == 0
        or torch.is_complex(value)
        or not bool(torch.isfinite(value).all())
        or bool(torch.any(value < 0.0))
        or float(value.sum().item()) <= 0.0
    ):
        raise invalid_restoration_contract(
            "pupil must be a finite nonnegative 2D tensor with positive support"
        )
    return value.detach().clone()


def _finite_candidates(
    name: str,
    values: tuple[float, ...],
    *,
    must_be_positive: bool,
) -> tuple[float, ...]:
    if not isinstance(values, tuple) or not values:
        raise invalid_restoration_contract(f"{name} must be a non-empty tuple")
    candidates = tuple(
        finite_real(f"{name}[{index}]", value) for index, value in enumerate(values)
    )
    if must_be_positive and any(value <= 0.0 for value in candidates):
        raise invalid_restoration_contract(f"{name} values must be positive")
    return candidates

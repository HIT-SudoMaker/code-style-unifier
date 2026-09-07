from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math

import torch

from experiments.restoration.adaptive_measurement.protocol.episode import (
    AdaptiveEpisodePolicy,
)
from experiments.restoration.adaptive_measurement.sensing.quadrature import (
    demodulate_phase_shifted_observations,
)
from experiments.restoration.adaptive_measurement.sensing.replay_conditioned_pupil_fit import (
    ReplayConditionedPupilEstimate,
    fit_replay_conditioned_pupil_phase,
)
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.observations import OpticalObservation
from experiments.restoration.optical_bench import (
    OpticalBenchConfig,
    propagate_interferometric_bench,
)
from experiments.restoration.phase_control import (
    DeliveredPhaseState,
    PhaseCommand,
    PhaseDelivery,
)


@dataclass(frozen=True, slots=True, eq=False)
class LockedActionPrediction:
    """Freeze the predicted Echo before a physical trial is observed."""

    calibration_id: str
    command_id: str
    cross_term: torch.Tensor

    def __post_init__(self) -> None:
        for name in ("calibration_id", "command_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise invalid_restoration_contract(f"{name} must be non-empty")
        if (
            not isinstance(self.cross_term, torch.Tensor)
            or not torch.is_complex(self.cross_term)
            or not bool(torch.isfinite(self.cross_term).all())
        ):
            raise invalid_restoration_contract(
                "cross_term must be a finite complex tensor"
            )
        object.__setattr__(self, "cross_term", self.cross_term.detach().clone())


@dataclass(frozen=True, slots=True, eq=False)
class DeliveredCorrectionProposal:
    """One calibrated correction proposal with its delivery and safety evidence."""

    estimate: ReplayConditionedPupilEstimate
    trial_command: PhaseCommand
    predicted_delivery: DeliveredPhaseState
    reachability_residual_rms: float
    predicted_removal_gain_db: float
    can_deliver: bool
    should_trial: bool
    locked_prediction: LockedActionPrediction


@dataclass(frozen=True, slots=True)
class ActionEchoAudit:
    """Compare a delivered four-frame Echo with its locked prediction."""

    observation_ids: tuple[str, ...]
    conformity_nrmse: float
    did_echo_conform: bool


class CalibratedReplayReachability:
    """Infer and project one replay-conditioned phase action behind the bench Seam."""

    __slots__ = (
        "_bench_config",
        "_calibration_id",
        "_phase_delivery",
        "_pupil",
        "_replay_input_field",
        "_replay_intensity",
    )

    def __init__(
        self,
        displayed_replay_intensity: torch.Tensor,
        bench_config: OpticalBenchConfig,
        pupil: torch.Tensor,
        phase_delivery: PhaseDelivery,
        *,
        calibration_id: str,
        device: torch.device | str = "cpu",
    ) -> None:
        if not isinstance(bench_config, OpticalBenchConfig):
            raise TypeError("bench_config must be an OpticalBenchConfig")
        bench_config.validate()
        if not hasattr(phase_delivery, "deliver") or not hasattr(
            phase_delivery,
            "project_delivered_phase",
        ):
            raise TypeError("phase_delivery must implement delivery and projection")
        if not isinstance(calibration_id, str) or not calibration_id.strip():
            raise invalid_restoration_contract("calibration_id must be non-empty")
        replay_intensity = _replay_intensity(
            displayed_replay_intensity,
            resolution=bench_config.input_array_resolution,
            device=torch.device(device),
        )
        pupil_plane = _pupil_plane(
            pupil,
            resolution=bench_config.input_array_resolution,
            device=torch.device(device),
        )
        self._replay_intensity = replay_intensity
        self._replay_input_field = torch.sqrt(replay_intensity).to(
            dtype=torch.complex64
        )
        self._bench_config = bench_config
        self._pupil = pupil_plane
        self._phase_delivery = phase_delivery
        self._calibration_id = calibration_id

    def propose_correction(
        self,
        observations: Sequence[OpticalObservation],
        displayed_replay_intensity: torch.Tensor,
        policy: AdaptiveEpisodePolicy,
        *,
        command_id: str,
    ) -> DeliveredCorrectionProposal:
        """Convert four causal intensities into one calibrated trial proposal."""
        if not isinstance(policy, AdaptiveEpisodePolicy):
            raise TypeError("policy must be an AdaptiveEpisodePolicy")
        displayed = _replay_intensity(
            displayed_replay_intensity,
            resolution=self._bench_config.input_array_resolution,
            device=self._replay_intensity.device,
        )
        if not torch.allclose(
            displayed,
            self._replay_intensity,
            atol=1e-7,
            rtol=1e-6,
        ):
            raise invalid_restoration_contract(
                "episode replay intensity does not match the calibrated bench input"
            )

        quadrature = demodulate_phase_shifted_observations(observations)
        estimate = fit_replay_conditioned_pupil_phase(
            quadrature,
            self._replay_input_field,
            self._bench_config,
            self._pupil,
            mode_names=policy.fitted_mode_names,
            iteration_count=policy.fit_iteration_count,
            learning_rate=policy.fit_learning_rate,
            coefficient_regularization=policy.coefficient_regularization,
            coefficient_limit_radians=policy.coefficient_limit_radians,
        )
        desired_phase = -estimate.estimated_phase_radians
        trial_command = self._phase_delivery.project_delivered_phase(
            command_id,
            desired_phase,
            pupil=self._pupil,
        )
        predicted_delivery = self._phase_delivery.deliver(
            trial_command,
            pupil=self._pupil,
        )
        safe_delivery = self._phase_delivery.deliver(
            PhaseCommand(
                f"{command_id}-safe-reference",
                torch.zeros_like(desired_phase),
            ),
            pupil=self._pupil,
        )
        reachability_residual = _supported_circular_rms(
            predicted_delivery.phase_radians - predicted_delivery.piston_radians,
            desired_phase,
            self._pupil,
        )
        ideal_cross_term = self._predict_cross_term(
            torch.zeros_like(estimate.estimated_phase_radians),
            safe_delivery.phase_radians - safe_delivery.piston_radians,
        )
        predicted_echo = self._predict_cross_term(
            estimate.estimated_phase_radians,
            predicted_delivery.phase_radians - predicted_delivery.piston_radians,
        )
        predicted_gain = _error_ratio_db(
            _mean_complex_error(quadrature.cross_term, ideal_cross_term),
            _mean_complex_error(predicted_echo, ideal_cross_term),
        )
        can_deliver = (
            policy.maximum_observation_count >= 9
            and quadrature.design_condition_number
            <= policy.maximum_design_condition_number
            and estimate.fitted_cross_term_nrmse <= policy.maximum_fit_nrmse
            and reachability_residual <= policy.maximum_reachability_residual_rms
        )
        should_trial = predicted_gain >= policy.minimum_predicted_gain_db
        return DeliveredCorrectionProposal(
            estimate=estimate,
            trial_command=trial_command,
            predicted_delivery=predicted_delivery,
            reachability_residual_rms=reachability_residual,
            predicted_removal_gain_db=predicted_gain,
            can_deliver=can_deliver,
            should_trial=should_trial,
            locked_prediction=LockedActionPrediction(
                calibration_id=self._calibration_id,
                command_id=trial_command.command_id,
                cross_term=predicted_echo,
            ),
        )

    def _predict_cross_term(
        self,
        estimated_aberration: torch.Tensor,
        delivered_spatial_action: torch.Tensor,
    ) -> torch.Tensor:
        fields = propagate_interferometric_bench(
            self._replay_input_field,
            delivered_spatial_action,
            self._bench_config,
            processing_aberration_radians=estimated_aberration,
            processing_pupil=self._pupil,
        )
        return torch.conj(fields.reference) * fields.processing


def audit_action_echo(
    observations: Sequence[OpticalObservation],
    proposal: DeliveredCorrectionProposal,
    *,
    conformity_threshold: float,
) -> ActionEchoAudit:
    """Audit a complete Echo burst against the pre-trial locked prediction."""
    if not isinstance(proposal, DeliveredCorrectionProposal):
        raise TypeError("proposal must be a DeliveredCorrectionProposal")
    threshold = float(conformity_threshold)
    if not math.isfinite(threshold) or threshold <= 0.0:
        raise invalid_restoration_contract(
            "conformity_threshold must be a positive finite number"
        )
    frames = tuple(observations)
    if any(
        frame.metadata.get("calibration_id")
        != proposal.locked_prediction.calibration_id
        for frame in frames
    ):
        raise invalid_restoration_contract(
            "Echo observations must use the locked calibration identity"
        )
    if any(
        not torch.allclose(
            frame.command_phase_radians,
            proposal.trial_command.phase_radians,
        )
        for frame in frames
    ):
        raise invalid_restoration_contract(
            "Echo observations must preserve the locked spatial trial action"
        )
    echo = demodulate_phase_shifted_observations(frames)
    conformity = _normalized_error(
        echo.cross_term,
        proposal.locked_prediction.cross_term,
    )
    return ActionEchoAudit(
        observation_ids=echo.observation_ids,
        conformity_nrmse=conformity,
        did_echo_conform=conformity <= threshold,
    )


def _replay_intensity(
    value: torch.Tensor,
    *,
    resolution: tuple[int, int],
    device: torch.device,
) -> torch.Tensor:
    if (
        not isinstance(value, torch.Tensor)
        or value.ndim != 3
        or value.shape[0] != 1
        or tuple(value.shape[-2:]) != resolution
        or torch.is_complex(value)
        or not bool(torch.isfinite(value).all())
        or bool(torch.any(value < 0.0))
    ):
        raise invalid_restoration_contract(
            "displayed_replay_intensity must be a finite nonnegative [1, height, width] tensor matching the bench"
        )
    return value.to(device=device, dtype=torch.float32)


def _pupil_plane(
    value: torch.Tensor,
    *,
    resolution: tuple[int, int],
    device: torch.device,
) -> torch.Tensor:
    if (
        not isinstance(value, torch.Tensor)
        or torch.is_complex(value)
        or tuple(value.shape) != resolution
        or not bool(torch.isfinite(value).all())
        or bool(torch.any(value < 0.0))
        or float(value.sum().item()) <= 0.0
    ):
        raise invalid_restoration_contract(
            "pupil must be a finite nonnegative plane matching the bench"
        )
    return value.to(device=device, dtype=torch.float32)


def _supported_circular_rms(
    delivered: torch.Tensor,
    desired: torch.Tensor,
    pupil: torch.Tensor,
) -> float:
    difference = torch.angle(torch.exp(1j * (delivered - desired)))
    support = pupil > 0.0
    return float(torch.sqrt(torch.mean(difference[support].square())).item())


def _mean_complex_error(value: torch.Tensor, reference: torch.Tensor) -> float:
    return float(torch.mean((value - reference).abs().square()).item())


def _normalized_error(value: torch.Tensor, reference: torch.Tensor) -> float:
    return float(
        (
            torch.linalg.vector_norm(value - reference)
            / (torch.linalg.vector_norm(reference) + 1e-12)
        ).item()
    )


def _error_ratio_db(baseline_error: float, corrected_error: float) -> float:
    return min(
        120.0,
        10.0 * math.log10(max(baseline_error, 1e-12) / max(corrected_error, 1e-12)),
    )

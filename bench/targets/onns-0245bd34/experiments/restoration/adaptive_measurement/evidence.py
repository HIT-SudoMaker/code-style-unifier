from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
from numbers import Real
import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

import torch

from experiments.restoration.adaptive_measurement.protocol.episode import (
    AdaptiveEpisodePolicy,
)
from experiments.restoration.adaptive_measurement.reachability import (
    ActionEchoAudit,
    DeliveredCorrectionProposal,
)
from experiments.restoration.observations import OpticalObservation
from experiments.restoration.phase_control import PhaseCommand


@dataclass(frozen=True, slots=True)
class EpisodeEventLedger:
    """Count every camera read, SLM state, dose, and causal time in one episode."""

    camera_read_count: int
    slm_state_count: int
    trial_count: int
    echo_observation_count: int
    revert_count: int
    exposure_dose: float
    settling_time_s: float
    transfer_time_s: float
    online_compute_time_s: float
    episode_elapsed_time_s: float
    trial_to_science_time_s: float


@dataclass(frozen=True, slots=True, eq=False)
class AdaptiveEpisodeRecord:
    """Canonical causal evidence for one completed Adaptive episode."""

    episode_id: str
    calibration_id: str
    displayed_replay_sha256: str
    policy: AdaptiveEpisodePolicy
    pre_observations: tuple[OpticalObservation, ...]
    proposal: DeliveredCorrectionProposal
    pre_echo_decision: Literal["trial", "abstain"]
    echo_observations: tuple[OpticalObservation, ...]
    echo_audit: ActionEchoAudit | None
    post_echo_decision: Literal["admit", "revert"] | None
    final_command: PhaseCommand
    science_observation: OpticalObservation
    event_ledger: EpisodeEventLedger


def build_episode_event_ledger(
    pre_observations: tuple[OpticalObservation, ...],
    echo_observations: tuple[OpticalObservation, ...],
    science_observation: OpticalObservation,
    *,
    trial_count: int,
    revert_count: int,
    online_compute_time_s: float,
) -> EpisodeEventLedger:
    """Aggregate one complete event ledger from the canonical observations."""
    observations = (*pre_observations, *echo_observations, science_observation)
    trial_to_science = (
        max(
            0.0,
            science_observation.elapsed_time_s - echo_observations[-1].elapsed_time_s,
        )
        if echo_observations
        else 0.0
    )
    return EpisodeEventLedger(
        camera_read_count=len(observations),
        slm_state_count=len({item.command_id for item in observations}),
        trial_count=trial_count,
        echo_observation_count=len(echo_observations),
        revert_count=revert_count,
        exposure_dose=sum(
            _metadata_float(item, "exposure_dose") for item in observations
        ),
        settling_time_s=sum(
            _metadata_float(item, "settling_time_s") for item in observations
        ),
        transfer_time_s=sum(
            _metadata_float(item, "transfer_time_s") for item in observations
        ),
        online_compute_time_s=max(0.0, float(online_compute_time_s)),
        episode_elapsed_time_s=science_observation.elapsed_time_s,
        trial_to_science_time_s=trial_to_science,
    )


def compute_replay_sha256(displayed_replay_intensity: torch.Tensor) -> str:
    """Identify the exact policy-visible SLM1 replay without storing a second copy."""
    tensor = displayed_replay_intensity.detach().cpu().contiguous()
    digest = hashlib.sha256()
    digest.update(str(tensor.dtype).encode("ascii"))
    digest.update(str(tuple(tensor.shape)).encode("ascii"))
    digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def write_adaptive_episode_evidence(
    path: Path | str,
    record: AdaptiveEpisodeRecord,
) -> Path:
    """Write one immutable, replayable episode artifact."""
    if not isinstance(record, AdaptiveEpisodeRecord):
        raise TypeError("record must be an AdaptiveEpisodeRecord")
    output_path = Path(path)
    if output_path.exists():
        raise FileExistsError(
            f"immutable Adaptive evidence already exists: {output_path}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f"._{uuid4().hex[:12]}.tmp")
    try:
        with temporary_path.open("xb") as stream:
            torch.save(_episode_payload(record), stream)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary_path, output_path)
        except FileExistsError as error:
            raise FileExistsError(
                f"immutable Adaptive evidence already exists: {output_path}"
            ) from error
    finally:
        temporary_path.unlink(missing_ok=True)
    return output_path


def _episode_payload(record: AdaptiveEpisodeRecord) -> dict[str, object]:
    proposal = record.proposal
    return {
        "schema_version": "adaptive_episode_v2",
        "episode_id": record.episode_id,
        "calibration_id": record.calibration_id,
        "displayed_replay_sha256": record.displayed_replay_sha256,
        "policy": asdict(record.policy),
        "pre_observations": tuple(
            build_optical_observation_payload(value)
            for value in record.pre_observations
        ),
        "proposal": {
            "estimated_phase_radians": (
                proposal.estimate.estimated_phase_radians.detach().cpu()
            ),
            "coefficients_radians": dict(proposal.estimate.coefficients_radians),
            "initial_cross_term_nrmse": (proposal.estimate.initial_cross_term_nrmse),
            "fitted_cross_term_nrmse": (proposal.estimate.fitted_cross_term_nrmse),
            "trial_command": _command_payload(proposal.trial_command),
            "predicted_delivery": {
                "command_id": proposal.predicted_delivery.command_id,
                "phase_radians": (
                    proposal.predicted_delivery.phase_radians.detach().cpu()
                ),
                "piston_radians": proposal.predicted_delivery.piston_radians,
                "delivery_model": proposal.predicted_delivery.delivery_model,
                "metadata": dict(proposal.predicted_delivery.metadata),
            },
            "reachability_residual_rms": proposal.reachability_residual_rms,
            "predicted_removal_gain_db": proposal.predicted_removal_gain_db,
            "can_deliver": proposal.can_deliver,
            "should_trial": proposal.should_trial,
            "locked_prediction": {
                "calibration_id": proposal.locked_prediction.calibration_id,
                "command_id": proposal.locked_prediction.command_id,
                "cross_term": (proposal.locked_prediction.cross_term.detach().cpu()),
            },
        },
        "pre_echo_decision": record.pre_echo_decision,
        "echo_observations": tuple(
            build_optical_observation_payload(value)
            for value in record.echo_observations
        ),
        "echo_audit": (
            None if record.echo_audit is None else asdict(record.echo_audit)
        ),
        "post_echo_decision": record.post_echo_decision,
        "final_command": _command_payload(record.final_command),
        "science_observation": build_optical_observation_payload(
            record.science_observation
        ),
        "event_ledger": asdict(record.event_ledger),
    }


def _command_payload(command: PhaseCommand) -> dict[str, object]:
    return {
        "command_id": command.command_id,
        "phase_radians": command.phase_radians.detach().cpu(),
        "piston_radians": command.piston_radians,
    }


def build_optical_observation_payload(
    observation: OpticalObservation,
) -> dict[str, object]:
    """Build one lossless, CPU-backed optical-observation evidence payload."""
    if not isinstance(observation, OpticalObservation):
        raise TypeError("observation must be an OpticalObservation")
    return {
        "observation_id": observation.observation_id,
        "kind": observation.kind,
        "sequence_index": observation.sequence_index,
        "intensity": observation.intensity.detach().cpu(),
        "command_id": observation.command_id,
        "command_phase_radians": observation.command_phase_radians.detach().cpu(),
        "delivered_phase_radians": (observation.delivered_phase_radians.detach().cpu()),
        "delivery_model": observation.delivery_model,
        "is_reference_enabled": observation.is_reference_enabled,
        "command_piston_radians": observation.command_piston_radians,
        "delivered_piston_radians": observation.delivered_piston_radians,
        "elapsed_time_s": observation.elapsed_time_s,
        "metadata": dict(observation.metadata),
    }


def _metadata_float(observation: OpticalObservation, name: str) -> float:
    value = observation.metadata.get(name, 0.0)
    if isinstance(value, bool) or not isinstance(value, Real):
        return 0.0
    normalized = float(value)
    return normalized if math.isfinite(normalized) else 0.0

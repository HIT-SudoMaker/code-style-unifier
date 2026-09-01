from __future__ import annotations

import math
import time
from collections.abc import Sequence
from typing import Literal, Protocol

import torch

from experiments.restoration.adaptive_measurement.evidence import (
    AdaptiveEpisodeRecord,
    build_episode_event_ledger,
    compute_replay_sha256,
)
from experiments.restoration.adaptive_measurement.protocol.episode import (
    AdaptiveEpisodePolicy,
    AdaptiveEpisodeRequest,
)
from experiments.restoration.adaptive_measurement.reachability import (
    DeliveredCorrectionProposal,
    audit_action_echo,
)
from experiments.restoration.observations import OpticalObservation
from experiments.restoration.phase_control import PhaseCommand


_PISTON_STEPS = (0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0)


class _EpisodeBench(Protocol):
    @property
    def calibration_id(self) -> str: ...

    def acquire(
        self,
        command: PhaseCommand,
        *,
        observation_id: str,
        kind: Literal["fixed", "calibration", "science"],
        sequence_index: int,
        is_reference_enabled: bool = True,
    ) -> OpticalObservation: ...

    def propose_correction(
        self,
        observations: Sequence[OpticalObservation],
        displayed_replay_intensity: torch.Tensor,
        policy: AdaptiveEpisodePolicy,
        *,
        command_id: str,
    ) -> DeliveredCorrectionProposal: ...


@torch.no_grad()
def run_adaptive_episode(
    request: AdaptiveEpisodeRequest,
    bench: _EpisodeBench,
) -> AdaptiveEpisodeRecord:
    """Run one truth-blind pre--trial--Echo--science episode."""
    if not isinstance(request, AdaptiveEpisodeRequest):
        raise TypeError("request must be an AdaptiveEpisodeRequest")
    if not all(
        hasattr(bench, operation)
        for operation in ("acquire", "calibration_id", "propose_correction")
    ):
        raise TypeError("bench must provide the Adaptive episode Seam")
    calibration_id = bench.calibration_id
    if not isinstance(calibration_id, str) or not calibration_id.strip():
        raise TypeError("bench.calibration_id must be a non-empty string")

    safe_command = PhaseCommand(
        f"{request.episode_id}-safe",
        torch.zeros(
            request.displayed_replay_intensity.shape[-2:],
            dtype=torch.float32,
            device=request.displayed_replay_intensity.device,
        ),
    )
    pre_observations = _acquire_quadrature_burst(
        bench,
        safe_command,
        prefix=f"{request.episode_id}-pre",
        sequence_offset=0,
    )
    proposal_started = time.perf_counter()
    proposal = bench.propose_correction(
        pre_observations,
        request.displayed_replay_intensity,
        request.policy,
        command_id=f"{request.episode_id}-trial",
    )
    online_compute_time_s = time.perf_counter() - proposal_started

    if not proposal.can_deliver or not proposal.should_trial:
        science_observation = bench.acquire(
            safe_command,
            observation_id=f"{request.episode_id}-science",
            kind="science",
            sequence_index=4,
        )
        return AdaptiveEpisodeRecord(
            episode_id=request.episode_id,
            calibration_id=calibration_id,
            displayed_replay_sha256=compute_replay_sha256(
                request.displayed_replay_intensity
            ),
            policy=request.policy,
            pre_observations=pre_observations,
            proposal=proposal,
            pre_echo_decision="abstain",
            echo_observations=(),
            echo_audit=None,
            post_echo_decision=None,
            final_command=safe_command,
            science_observation=science_observation,
            event_ledger=build_episode_event_ledger(
                pre_observations,
                (),
                science_observation,
                trial_count=0,
                revert_count=0,
                online_compute_time_s=online_compute_time_s,
            ),
        )

    echo_observations = _acquire_quadrature_burst(
        bench,
        proposal.trial_command,
        prefix=f"{request.episode_id}-echo",
        sequence_offset=4,
    )
    audit_started = time.perf_counter()
    echo_audit = audit_action_echo(
        echo_observations,
        proposal,
        conformity_threshold=request.policy.echo_conformity_threshold,
    )
    online_compute_time_s += time.perf_counter() - audit_started
    final_command = (
        proposal.trial_command if echo_audit.did_echo_conform else safe_command
    )
    science_observation = bench.acquire(
        final_command,
        observation_id=f"{request.episode_id}-science",
        kind="science",
        sequence_index=8,
    )
    return AdaptiveEpisodeRecord(
        episode_id=request.episode_id,
        calibration_id=calibration_id,
        displayed_replay_sha256=compute_replay_sha256(
            request.displayed_replay_intensity
        ),
        policy=request.policy,
        pre_observations=pre_observations,
        proposal=proposal,
        pre_echo_decision="trial",
        echo_observations=echo_observations,
        echo_audit=echo_audit,
        post_echo_decision="admit" if echo_audit.did_echo_conform else "revert",
        final_command=final_command,
        science_observation=science_observation,
        event_ledger=build_episode_event_ledger(
            pre_observations,
            echo_observations,
            science_observation,
            trial_count=1,
            revert_count=0 if echo_audit.did_echo_conform else 1,
            online_compute_time_s=online_compute_time_s,
        ),
    )


def _acquire_quadrature_burst(
    bench: _EpisodeBench,
    base_command: PhaseCommand,
    *,
    prefix: str,
    sequence_offset: int,
) -> tuple[OpticalObservation, ...]:
    return tuple(
        bench.acquire(
            PhaseCommand(
                f"{prefix}-{index}",
                base_command.phase_radians,
                piston_radians=base_command.piston_radians + piston_step,
            ),
            observation_id=f"{prefix}-{index}",
            kind="calibration",
            sequence_index=sequence_offset + index,
        )
        for index, piston_step in enumerate(_PISTON_STEPS)
    )

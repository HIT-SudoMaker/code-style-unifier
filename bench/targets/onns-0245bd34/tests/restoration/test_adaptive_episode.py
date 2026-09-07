from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import inspect
from pathlib import Path
from threading import Barrier

import pytest
import torch

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    SimulatedBench,
)
from experiments.restoration.adaptive_measurement import (
    AdaptiveEpisodePolicy,
    AdaptiveEpisodeRequest,
    run_adaptive_episode,
)
from experiments.restoration.adaptive_measurement.evidence import (
    write_adaptive_episode_evidence,
)
from experiments.restoration.adaptive_measurement import evidence as episode_evidence
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.phase_control import IdealPhaseDelivery, PhaseCommand
from experiments.restoration.pupil_aberrations import (
    PupilAberrationState,
    build_pupil_aberration_phase,
)


def test_adaptive_episode_admits_a_truth_blind_nine_frame_correction() -> None:
    resolution = (32, 32)
    bench_config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    generator = torch.Generator().manual_seed(2026)
    degraded_intensity = 0.2 + 0.8 * torch.rand(
        resolution,
        generator=generator,
    )
    displayed_replay_intensity = degraded_intensity[None]
    hidden_phase, pupil = build_pupil_aberration_phase(
        resolution,
        PupilAberrationState({"coma_horizontal": 0.8}),
    )
    delivery = IdealPhaseDelivery()
    bench = SimulatedBench(
        bench_config,
        delivery,
        displayed_replay_intensity,
        hidden_phase,
        pupil,
        calibration_id="sim-calibration-v1",
        frame_interval_s=1.0 / 60.0,
    )
    request = AdaptiveEpisodeRequest(
        episode_id="coma-episode",
        displayed_replay_intensity=displayed_replay_intensity,
        policy=AdaptiveEpisodePolicy(
            fitted_mode_names=("coma_horizontal",),
            fit_iteration_count=120,
            minimum_predicted_gain_db=1.0,
        ),
    )
    safe_observation = bench.acquire(
        PhaseCommand("evaluator-safe", torch.zeros(resolution)),
        observation_id="evaluator-safe",
        kind="science",
        sequence_index=20,
    )
    reference_bench = SimulatedBench(
        bench_config,
        delivery,
        displayed_replay_intensity,
        torch.zeros_like(hidden_phase),
        pupil,
        calibration_id="sim-reference-v1",
    )
    reference_observation = reference_bench.acquire(
        PhaseCommand("evaluator-reference", torch.zeros(resolution)),
        observation_id="evaluator-reference",
        kind="science",
        sequence_index=20,
    )

    record = run_adaptive_episode(request, bench)

    assert record.pre_echo_decision == "trial"
    assert record.post_echo_decision == "admit"
    assert len(record.pre_observations) == 4
    assert len(record.echo_observations) == 4
    assert record.science_observation.sequence_index == 8
    assert (
        record.science_observation.command_id
        == record.proposal.trial_command.command_id
    )
    assert (
        record.science_observation.metadata["emulator_mode"]
        == "same_device_differential_aberration"
    )
    assert record.event_ledger.camera_read_count == 9
    assert record.event_ledger.trial_count == 1
    assert record.event_ledger.revert_count == 0
    assert record.proposal.predicted_removal_gain_db > 6.0
    assert record.echo_audit is not None
    assert record.echo_audit.conformity_nrmse < 1e-3
    safe_error = torch.mean(
        (safe_observation.intensity - reference_observation.intensity).square()
    )
    science_error = torch.mean(
        (
            record.science_observation.intensity - reference_observation.intensity
        ).square()
    )
    assert science_error < safe_error * 1e-4
    assert (
        len(
            {
                observation.observation_id
                for observation in (
                    *record.pre_observations,
                    *record.echo_observations,
                    record.science_observation,
                )
            }
        )
        == 9
    )


def test_adaptive_episode_contract_cannot_accept_evaluator_truth() -> None:
    request_fields = tuple(AdaptiveEpisodeRequest.__dataclass_fields__)
    runner_parameters = tuple(inspect.signature(run_adaptive_episode).parameters)

    assert runner_parameters == ("request", "bench")
    assert request_fields == (
        "episode_id",
        "displayed_replay_intensity",
        "policy",
    )


def test_adaptive_policy_rejects_a_budget_below_one_safe_episode() -> None:
    with pytest.raises(ValueError, match="at least 5"):
        AdaptiveEpisodePolicy(maximum_observation_count=4)

    assert (
        AdaptiveEpisodePolicy(maximum_observation_count=5).maximum_observation_count
        == 5
    )


def test_adaptive_episode_reverts_a_nonconforming_trial_without_erasing_harm() -> None:
    bench_config, displayed_replay_intensity, hidden_phase, pupil = _episode_fixture()
    delivery = IdealPhaseDelivery()
    bench = SimulatedBench(
        bench_config,
        delivery,
        displayed_replay_intensity,
        hidden_phase,
        pupil,
        calibration_id="sim-calibration-v1",
        photon_count=1_000.0,
        read_noise_standard_deviation=0.001,
    )
    request = AdaptiveEpisodeRequest(
        episode_id="noisy-episode",
        displayed_replay_intensity=displayed_replay_intensity,
        policy=AdaptiveEpisodePolicy(
            fitted_mode_names=("coma_horizontal",),
            fit_iteration_count=80,
            maximum_fit_nrmse=10.0,
            maximum_reachability_residual_rms=3.2,
            minimum_predicted_gain_db=-120.0,
            echo_conformity_threshold=1e-8,
        ),
    )

    record = run_adaptive_episode(request, bench)

    assert record.pre_echo_decision == "trial"
    assert record.post_echo_decision == "revert"
    assert record.final_command.command_id.endswith("-safe")
    assert record.science_observation.command_id == record.final_command.command_id
    assert record.event_ledger.camera_read_count == 9
    assert record.event_ledger.trial_count == 1
    assert record.event_ledger.echo_observation_count == 4
    assert record.event_ledger.revert_count == 1


def test_adaptive_episode_abstains_when_the_echo_budget_is_unavailable() -> None:
    bench_config, displayed_replay_intensity, hidden_phase, pupil = _episode_fixture()
    delivery = IdealPhaseDelivery()
    bench = SimulatedBench(
        bench_config,
        delivery,
        displayed_replay_intensity,
        hidden_phase,
        pupil,
        calibration_id="sim-calibration-v1",
    )
    request = AdaptiveEpisodeRequest(
        episode_id="bounded-episode",
        displayed_replay_intensity=displayed_replay_intensity,
        policy=AdaptiveEpisodePolicy(
            fitted_mode_names=("coma_horizontal",),
            fit_iteration_count=80,
            maximum_observation_count=5,
        ),
    )

    record = run_adaptive_episode(request, bench)

    assert record.proposal.can_deliver is False
    assert record.pre_echo_decision == "abstain"
    assert record.post_echo_decision is None
    assert record.echo_observations == ()
    assert record.science_observation.sequence_index == 4
    assert record.event_ledger.camera_read_count == 5
    assert record.event_ledger.trial_count == 0


def test_adaptive_episode_evidence_preserves_the_locked_causal_chain(
    tmp_path: Path,
) -> None:
    bench_config, displayed_replay_intensity, hidden_phase, pupil = _episode_fixture()
    bench = SimulatedBench(
        bench_config,
        IdealPhaseDelivery(),
        displayed_replay_intensity,
        hidden_phase,
        pupil,
        calibration_id="evidence-calibration-v1",
    )
    request = AdaptiveEpisodeRequest(
        episode_id="evidence-episode",
        displayed_replay_intensity=displayed_replay_intensity,
        policy=AdaptiveEpisodePolicy(
            fitted_mode_names=("coma_horizontal",),
            fit_iteration_count=80,
        ),
    )
    record = run_adaptive_episode(request, bench)
    evidence_path = tmp_path / "episode.pt"

    write_adaptive_episode_evidence(evidence_path, record)
    payload = torch.load(evidence_path, map_location="cpu", weights_only=True)

    assert payload["schema_version"] == "adaptive_episode_v2"
    assert payload["calibration_id"] == "evidence-calibration-v1"
    assert len(payload["pre_observations"]) == 4
    assert len(payload["echo_observations"]) == 4
    assert (
        payload["proposal"]["locked_prediction"]["calibration_id"]
        == payload["calibration_id"]
    )
    assert payload["post_echo_decision"] == "admit"
    assert payload["event_ledger"]["camera_read_count"] == 9
    assert payload["science_observation"]["sequence_index"] == 8
    assert payload["science_observation"]["is_reference_enabled"] is True

    with pytest.raises(FileExistsError, match="immutable"):
        write_adaptive_episode_evidence(evidence_path, record)


def test_adaptive_episode_evidence_has_one_atomic_winner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bench_config, displayed_replay_intensity, hidden_phase, pupil = _episode_fixture()
    bench = SimulatedBench(
        bench_config,
        IdealPhaseDelivery(),
        displayed_replay_intensity,
        hidden_phase,
        pupil,
        calibration_id="concurrent-evidence-calibration-v1",
    )
    record = run_adaptive_episode(
        AdaptiveEpisodeRequest(
            episode_id="concurrent-evidence-episode",
            displayed_replay_intensity=displayed_replay_intensity,
            policy=AdaptiveEpisodePolicy(
                fitted_mode_names=("coma_horizontal",),
                fit_iteration_count=20,
            ),
        ),
        bench,
    )
    evidence_path = tmp_path / "episode.pt"
    save_barrier = Barrier(2)
    original_save = torch.save

    def synchronized_save(payload: object, destination: object) -> None:
        save_barrier.wait(timeout=10.0)
        original_save(payload, destination)

    monkeypatch.setattr(episode_evidence.torch, "save", synchronized_save)

    def attempt_write() -> str:
        try:
            write_adaptive_episode_evidence(evidence_path, record)
        except FileExistsError:
            return "already_exists"
        return "written"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(lambda _: attempt_write(), range(2)))

    assert sorted(outcomes) == ["already_exists", "written"]
    payload = torch.load(evidence_path, map_location="cpu", weights_only=True)
    assert payload["episode_id"] == record.episode_id


def _episode_fixture() -> tuple[
    OpticalBenchConfig,
    torch.Tensor,
    torch.Tensor,
    torch.Tensor,
]:
    resolution = (32, 32)
    bench_config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    generator = torch.Generator().manual_seed(2048)
    degraded_intensity = 0.2 + 0.8 * torch.rand(
        resolution,
        generator=generator,
    )
    displayed_replay_intensity = degraded_intensity[None]
    hidden_phase, pupil = build_pupil_aberration_phase(
        resolution,
        PupilAberrationState({"coma_horizontal": 0.8}),
    )
    return bench_config, displayed_replay_intensity, hidden_phase, pupil

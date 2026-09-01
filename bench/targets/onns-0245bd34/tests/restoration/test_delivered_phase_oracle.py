from __future__ import annotations

import pytest
import torch

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    CoherentPupilBench,
    CoherentPupilScene,
    SimulatedBench,
)
from experiments.restoration.adaptive_measurement.validation.delivered_phase_oracle import (
    BoundCoherentPupilEvaluator,
    search_calibrated_delivered_phase,
)
from experiments.restoration.adaptive_measurement.validation.oracle_evidence import (
    build_same_device_oracle_search_evidence,
)
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.phase_control import (
    IdealPhaseDelivery,
    PhaseCommand,
    SimulatedSlmPhaseDelivery,
)
from experiments.restoration.pupil_aberrations import (
    PupilAberrationState,
    build_pupil_aberration_phase,
)


def test_delivered_phase_oracle_compensates_gain_and_global_drift() -> None:
    resolution = (32, 32)
    bench_config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    generator = torch.Generator().manual_seed(29)
    replay_field = torch.sqrt(
        0.2 + 0.8 * torch.rand((1, 1, *resolution), generator=generator)
    ).to(torch.complex64)
    aberration_phase, pupil = build_pupil_aberration_phase(
        resolution,
        PupilAberrationState({"defocus": 0.8}),
    )
    clean_scene = CoherentPupilScene(
        replay_field,
        torch.zeros_like(aberration_phase),
        pupil,
    )
    aberrated_scene = CoherentPupilScene(replay_field, aberration_phase, pupil)
    safe_command = PhaseCommand("safe", torch.zeros(resolution))
    clean_target = CoherentPupilBench(
        bench_config,
        IdealPhaseDelivery(),
    ).acquire(
        clean_scene,
        safe_command,
        observation_id="clean-target",
        kind="science",
        sequence_index=0,
    )
    delivered_bench = CoherentPupilBench(
        bench_config,
        SimulatedSlmPhaseDelivery(response_gain=0.8, drift_radians=0.35),
    )
    uncorrected = delivered_bench.acquire(
        aberrated_scene,
        safe_command,
        observation_id="uncorrected",
        kind="science",
        sequence_index=1,
    )

    calibrated_seed = delivered_bench.phase_delivery.project_delivered_phase(
        "calibrated-seed",
        -aberration_phase,
        pupil=pupil,
    )
    result = search_calibrated_delivered_phase(
        BoundCoherentPupilEvaluator(delivered_bench, aberrated_scene),
        clean_target.intensity,
        calibrated_seed,
        pupil=pupil,
        command_multipliers=(1.0,),
        spatial_detail_strengths=(0.0,),
        command_id="delivered-oracle",
        observation_id_prefix="search",
        sequence_index_start=10,
    )
    corrected = delivered_bench.acquire(
        aberrated_scene,
        result.command,
        observation_id="corrected",
        kind="science",
        sequence_index=20,
    )

    uncorrected_error = torch.mean(
        (uncorrected.intensity - clean_target.intensity).square()
    )
    corrected_error = torch.mean(
        (corrected.intensity - clean_target.intensity).square()
    )

    assert result.candidate_count == 1
    assert result.selected_candidate_observation_id == "search-000"
    assert len(result.candidates) == 1
    assert result.candidates[0].observation.intensity.shape == (1, 1, 32, 32)
    assert result.candidates[0].mean_square_error == pytest.approx(
        result.mean_square_error
    )
    assert result.selected_command_multiplier == 1.0
    assert result.selected_spatial_detail_strength == 0.0
    assert result.command.piston_radians == pytest.approx(-0.35 / 0.8)
    assert corrected_error < uncorrected_error * 1e-3


def test_delivered_phase_oracle_searches_the_complete_same_device_state() -> None:
    resolution = (32, 32)
    bench_config = OpticalBenchConfig(
        input_array_resolution=resolution,
        phase_mask_resolution=32,
    )
    displayed_intensity = 0.2 + 0.8 * torch.rand(
        (1, *resolution),
        generator=torch.Generator().manual_seed(31),
    )
    replay_field = torch.sqrt(displayed_intensity).to(torch.complex64)[None]
    hidden_phase, pupil = build_pupil_aberration_phase(
        resolution,
        PupilAberrationState({"defocus": 0.8, "coma_vertical": 0.2}),
    )
    delivery = SimulatedSlmPhaseDelivery(
        phase_levels=32,
        response_gain=0.8,
        drift_radians=0.35,
        crosstalk_mix=0.15,
    )
    clean_target = CoherentPupilBench(bench_config, delivery).acquire(
        CoherentPupilScene(replay_field, torch.zeros_like(hidden_phase), pupil),
        PhaseCommand("safe", torch.zeros(resolution)),
        observation_id="clean-target",
        kind="science",
        sequence_index=0,
    )
    same_device_bench = SimulatedBench(
        bench_config,
        delivery,
        displayed_intensity,
        hidden_phase,
        pupil,
        calibration_id="same-device-oracle-v1",
    )

    result = search_calibrated_delivered_phase(
        same_device_bench,
        clean_target.intensity,
        PhaseCommand("same-device-seed", -hidden_phase),
        pupil=pupil,
        command_multipliers=(0.9, 1.0, 1.1),
        spatial_detail_strengths=(0.0,),
        command_id="same-device-oracle",
        observation_id_prefix="same-device-search",
        sequence_index_start=10,
    )

    composite_states = {
        state.observation_id: state
        for state in same_device_bench.read_evaluator_composite_states()
    }
    selected_candidate = result.selected_candidate
    composite_state = composite_states[selected_candidate.observation.observation_id]
    assert result.candidate_count == 3
    assert len(result.candidates) == 3
    assert result.selected_candidate_observation_id == "same-device-search-001"
    assert selected_candidate.command_multiplier == 1.0
    assert torch.allclose(
        selected_candidate.observation.command_phase_radians,
        result.command.phase_radians,
    )
    assert selected_candidate.observation.command_piston_radians == pytest.approx(
        result.command.piston_radians
    )
    assert torch.allclose(result.command.phase_radians, -hidden_phase)
    assert torch.allclose(
        composite_state.command.phase_radians,
        torch.zeros_like(hidden_phase),
        atol=1e-6,
        rtol=1e-6,
    )
    assert result.mean_square_error < 1e-10

    evidence = build_same_device_oracle_search_evidence(
        clean_target,
        result,
        tuple(composite_states.values()),
        calibration_id="same-device-oracle-v1",
    )
    assert evidence["schema_version"] == "same_device_b3_oracle_search_v1"
    assert evidence["search"]["selected_candidate_observation_id"] == (
        "same-device-search-001"
    )
    assert len(evidence["search"]["candidates"]) == 3
    assert len(evidence["candidate_composite_states"]) == 3

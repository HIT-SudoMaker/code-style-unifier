from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
from numbers import Integral, Real
from pathlib import Path
import time

import torch

from data.configs import SourceConfig
from experiments.restoration.adaptive_measurement import (
    AdaptiveEpisodePolicy,
    AdaptiveEpisodeRequest,
    run_adaptive_episode,
)
from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    CoherentPupilBench,
    CoherentPupilScene,
    SameDeviceCompositeState,
    SimulatedBench,
)
from experiments.restoration.adaptive_measurement.inputs.comparison_protocol import (
    DEFAULT_FIXED_SPLIT_MANIFEST,
    compute_file_sha256,
    select_aligned_replay_scene,
)
from experiments.restoration.adaptive_measurement.inputs.replay_scene import (
    AdaptiveReplayDataConfig,
    build_adaptive_replay_dataset,
)
from experiments.restoration.adaptive_measurement.evidence import (
    build_optical_observation_payload,
    write_adaptive_episode_evidence,
)
from experiments.restoration.adaptive_measurement.validation.delivered_phase_oracle import (
    DeliveredPhaseOracleSearch,
    search_calibrated_delivered_phase,
)
from experiments.restoration.adaptive_measurement.validation.oracle_evidence import (
    build_same_device_composite_payload,
    build_same_device_oracle_search_evidence,
)
from experiments.restoration.adaptive_measurement.sensing.replay_conditioned_pupil_fit import (
    ReplayConditionedPupilEstimate,
)
from experiments.restoration.degradation import restoration_profile
from experiments.restoration.evidence import (
    compute_config_hash,
    write_json,
    write_runtime,
)
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.input_protocol import (
    RESTORATION_RANDOM_SEED,
    build_restoration_source,
)
from experiments.restoration.metrics import (
    extract_center_image_region,
    normalize_intensity,
    psnr,
    ssim_global,
)
from experiments.restoration.observations import OpticalObservation
from experiments.restoration.optical_bench import (
    OpticalBenchConfig,
)
from experiments.restoration.phase_control import (
    PhaseCommand,
    SimulatedSlmPhaseDelivery,
)
from experiments.restoration.pupil_aberrations import (
    PupilAberrationState,
    build_pupil_aberration_phase,
)


_PSNR_CEILING_DB = 120.0


@dataclass(frozen=True, slots=True)
class DifferentialCorrectionStudyConfig:
    """Configure one truth-blind differential-correction study cell."""

    study_contract_version: str = field(
        init=False,
        default="auditable_same_device_oracle_search_v5",
    )
    project_root: Path | str = Path.cwd()
    source: SourceConfig = field(default_factory=build_restoration_source)
    degradation_profile_name: str = "medium"
    split_manifest_path: Path | str = DEFAULT_FIXED_SPLIT_MANIFEST
    evaluation_split: str = "val"
    scene_index: int = 0
    aberration: PupilAberrationState = field(default_factory=PupilAberrationState)
    policy: AdaptiveEpisodePolicy = field(default_factory=AdaptiveEpisodePolicy)
    phase_levels: int = 256
    response_gain: float = 0.97
    drift_radians: float = 0.015
    crosstalk_mix: float = 0.04
    photon_count: float | None = None
    read_noise_standard_deviation: float = 0.0
    minimum_b2_gain_db: float = 6.0
    minimum_b3_gain_db: float = 6.0
    seed: int = RESTORATION_RANDOM_SEED
    device: str = "cpu"

    def __post_init__(self) -> None:
        project_root = Path(self.project_root).resolve()
        manifest_path = Path(self.split_manifest_path)
        if not manifest_path.is_absolute():
            manifest_path = project_root / manifest_path
        source_root = self.source.dataset_root
        if source_root is not None:
            source_root = Path(source_root)
            if not source_root.is_absolute():
                source_root = project_root / source_root
            source_root = source_root.resolve()
        object.__setattr__(self, "project_root", project_root)
        object.__setattr__(self, "split_manifest_path", manifest_path.resolve())
        object.__setattr__(
            self, "source", replace(self.source, dataset_root=source_root)
        )
        restoration_profile(self.degradation_profile_name)
        if (
            self.source.dataset_name != "fmd"
            or not self.source.is_train
            or self.source.random_seed != RESTORATION_RANDOM_SEED
            or self.source.samples_per_class is not None
            or self.source.max_samples is not None
        ):
            raise invalid_restoration_contract(
                "differential comparison requires the canonical FMD source"
            )
        if self.evaluation_split not in {"train", "val", "test"}:
            raise invalid_restoration_contract(
                "evaluation_split must be train, val, or test"
            )
        _nonnegative_integer("scene_index", self.scene_index)
        _positive_integer("phase_levels", self.phase_levels)
        if not isinstance(self.policy, AdaptiveEpisodePolicy):
            raise TypeError("policy must be an AdaptiveEpisodePolicy")
        _positive_real("response_gain", self.response_gain)
        _finite_real("drift_radians", self.drift_radians)
        crosstalk = _nonnegative_real("crosstalk_mix", self.crosstalk_mix)
        if crosstalk > 1.0:
            raise invalid_restoration_contract(
                "crosstalk_mix must be between zero and one"
            )
        if self.photon_count is not None:
            _positive_real("photon_count", self.photon_count)
        _nonnegative_real(
            "read_noise_standard_deviation",
            self.read_noise_standard_deviation,
        )
        _finite_real("minimum_b2_gain_db", self.minimum_b2_gain_db)
        _finite_real("minimum_b3_gain_db", self.minimum_b3_gain_db)
        seed = _nonnegative_integer("seed", self.seed)
        if seed > 2**32 - 1:
            raise invalid_restoration_contract("seed must not exceed 4294967295")
        if self.device not in {"cpu", "cuda"}:
            raise invalid_restoration_contract("device must be cpu or cuda")

    def _config_hash_payload(self) -> dict[str, object]:
        return {
            "study_contract_version": self.study_contract_version,
            "source": self.source,
            "degradation_profile_name": self.degradation_profile_name,
            "degradation_profile": restoration_profile(self.degradation_profile_name),
            "split_manifest_sha256": compute_file_sha256(self.split_manifest_path),
            "evaluation_split": self.evaluation_split,
            "scene_index": self.scene_index,
            "aberration": self.aberration,
            "policy": self.policy,
            "phase_levels": self.phase_levels,
            "response_gain": self.response_gain,
            "drift_radians": self.drift_radians,
            "crosstalk_mix": self.crosstalk_mix,
            "photon_count": self.photon_count,
            "read_noise_standard_deviation": self.read_noise_standard_deviation,
            "minimum_b2_gain_db": self.minimum_b2_gain_db,
            "minimum_b3_gain_db": self.minimum_b3_gain_db,
            "seed": self.seed,
        }


@torch.no_grad()
def run_differential_correction_study(
    config: DifferentialCorrectionStudyConfig,
) -> Path:
    """Run the same-D B0/B1/B2/B3 differential-correction study."""
    if not isinstance(config, DifferentialCorrectionStudyConfig):
        raise TypeError("config must be a DifferentialCorrectionStudyConfig")
    if config.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    started = time.perf_counter()
    run_id = (
        f"differential_{config.degradation_profile_name}_"
        f"{config.evaluation_split}{config.scene_index}_s{config.seed}_"
        f"c{compute_config_hash(config)[:12]}"
    )
    run_dir = (
        Path(config.project_root)
        / "results/restoration/adaptive_measurement/differential_correction"
        / run_id
    )
    if run_dir.exists():
        raise FileExistsError(f"immutable differential run exists: {run_dir}")

    replay_data_config = AdaptiveReplayDataConfig(
        source=config.source,
        perturbation=restoration_profile(config.degradation_profile_name),
    )
    selection = select_aligned_replay_scene(
        build_adaptive_replay_dataset(replay_data_config),
        manifest_path=config.split_manifest_path,
        split=config.evaluation_split,
        scene_index=config.scene_index,
    )
    replay_scene = selection.scene
    device = torch.device(config.device)
    bench_config = OpticalBenchConfig()
    aberration_phase, pupil = build_pupil_aberration_phase(
        bench_config.input_array_resolution,
        config.aberration,
        device=device,
    )
    zero_phase = torch.zeros_like(aberration_phase)
    input_field = replay_scene.input_field.to(device)
    b0_scene = CoherentPupilScene(input_field, zero_phase, pupil)
    delivery = SimulatedSlmPhaseDelivery(
        phase_levels=config.phase_levels,
        response_gain=config.response_gain,
        drift_radians=config.drift_radians,
        crosstalk_mix=config.crosstalk_mix,
    )
    b0_bench = CoherentPupilBench(
        bench_config,
        delivery,
        photon_count=config.photon_count,
        read_noise_standard_deviation=config.read_noise_standard_deviation,
        seed=config.seed,
        device=device,
    )
    quiet_b0_bench = CoherentPupilBench(
        bench_config,
        delivery,
        seed=config.seed,
        device=device,
    )
    safe_command = PhaseCommand("safe-zero-phase", zero_phase)
    calibration_id = (
        f"simulated-slm-{config.phase_levels}-level-"
        f"response-{config.response_gain:g}"
    )
    episode_bench = SimulatedBench(
        bench_config,
        delivery,
        replay_scene.degraded_intensity.to(device),
        aberration_phase,
        pupil,
        calibration_id=calibration_id,
        photon_count=config.photon_count,
        read_noise_standard_deviation=config.read_noise_standard_deviation,
        seed=config.seed,
        device=device,
    )
    quiet_oracle_bench = SimulatedBench(
        bench_config,
        delivery,
        replay_scene.degraded_intensity.to(device),
        aberration_phase,
        pupil,
        calibration_id=calibration_id,
        seed=config.seed,
        device=device,
    )
    episode_record = run_adaptive_episode(
        AdaptiveEpisodeRequest(
            episode_id="b2-truth-blind-prospective",
            displayed_replay_intensity=(replay_scene.degraded_intensity.to(device)),
            policy=config.policy,
        ),
        episode_bench,
    )
    fitted = episode_record.proposal.estimate
    pre_observations = episode_record.pre_observations
    echo_observations = episode_record.echo_observations
    echo_conformity_nrmse = (
        None
        if episode_record.echo_audit is None
        else episode_record.echo_audit.conformity_nrmse
    )
    is_action_admitted = episode_record.post_echo_decision == "admit"

    b0 = b0_bench.acquire(
        b0_scene,
        safe_command,
        observation_id="b0-no-added-aberration",
        kind="science",
        sequence_index=20,
    )
    b1 = episode_bench.acquire(
        safe_command,
        observation_id="b1-aberrated-uncorrected",
        kind="science",
        sequence_index=21,
    )
    b2 = episode_record.science_observation
    quiet_b0 = quiet_b0_bench.acquire(
        b0_scene,
        safe_command,
        observation_id="b0-quiet-oracle-reference",
        kind="science",
        sequence_index=100,
    )
    b3_search = search_calibrated_delivered_phase(
        quiet_oracle_bench,
        quiet_b0.intensity,
        PhaseCommand("b3-ideal-phase", -aberration_phase),
        pupil=pupil,
        command_multipliers=tuple(
            float(value) for value in torch.linspace(0.9, 1.1, 17).tolist()
        ),
        spatial_detail_strengths=(0.0,),
        command_id="b3-delivered-space-oracle",
        observation_id_prefix="b3-search",
        sequence_index_start=200,
    )
    b3 = episode_bench.acquire(
        b3_search.command,
        observation_id="b3-delivered-space-oracle",
        kind="science",
        sequence_index=23,
    )

    metrics = _evaluate_metrics(
        replay_scene.degraded_intensity.to(device),
        replay_scene.evaluator_target_intensity.to(device),
        b0,
        b1,
        b2,
        b3,
    )
    phase_error = (fitted.estimated_phase_radians - aberration_phase) * pupil
    metrics.update(
        {
            "observation_count_b2": episode_record.event_ledger.camera_read_count,
            "fit_initial_cross_term_nrmse": fitted.initial_cross_term_nrmse,
            "fit_final_cross_term_nrmse": fitted.fitted_cross_term_nrmse,
            "echo_conformity_threshold": config.policy.echo_conformity_threshold,
            "is_action_admitted": is_action_admitted,
            "evaluator_only_phase_rmse_radians": _supported_rms(
                phase_error,
                pupil,
            ),
            "evaluator_only_true_phase_rms_radians": _supported_rms(
                aberration_phase,
                pupil,
            ),
            "simulation_wall_time_s": time.perf_counter() - started,
            "b3_search_candidate_count": float(b3_search.candidate_count),
            "b3_selected_command_multiplier": (b3_search.selected_command_multiplier),
            "b3_quiet_search_mse": b3_search.mean_square_error,
        }
    )
    if echo_conformity_nrmse is not None:
        metrics["echo_conformity_nrmse"] = echo_conformity_nrmse
    checks = {
        "delivered_oracle_has_headroom": (
            metrics["b3_aberration_removal_gain_db"] >= config.minimum_b3_gain_db
        ),
        "truth_blind_fit_improves_cross_term": (
            fitted.fitted_cross_term_nrmse < fitted.initial_cross_term_nrmse
        ),
        "action_echo_admits_delivered_trial": is_action_admitted,
        "truth_blind_action_reaches_gain_gate": (
            metrics["b2_aberration_removal_gain_db"] >= config.minimum_b2_gain_db
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"

    run_dir.mkdir(parents=True)
    write_json(run_dir / "config.json", config)
    write_runtime(run_dir / "runtime.json")
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "checks.json", checks)
    episode_evidence_path = write_adaptive_episode_evidence(
        run_dir / "episode.pt",
        episode_record,
    )
    evaluation_path = _write_evaluation_measurements(
        path=run_dir / "evaluation.pt",
        scene_id=replay_scene.scene_id,
        states={"b0": b0, "b1": b1, "b2": b2, "b3": b3},
        aberration_phase=aberration_phase,
        fitted=fitted,
        pupil=pupil,
        claim_composite_states=episode_bench.read_evaluator_composite_states(),
        oracle_target_observation=quiet_b0,
        oracle_search=b3_search,
        oracle_composite_states=(quiet_oracle_bench.read_evaluator_composite_states()),
        oracle_calibration_id=calibration_id,
    )
    figure_path = _write_comparison_figure(
        run_dir / "comparison.png",
        {"B0": b0, "B1": b1, "B2": b2, "B3": b3},
        aberration_phase,
        fitted.estimated_phase_radians,
        pupil,
    )
    write_json(
        run_dir / "result.json",
        {
            "schema_version": "differential_correction_study_v5",
            "status": status,
            "run_id": run_id,
            "evidence_level": (
                "simulation_only_controlled_amplitude_replay_"
                "processing_arm_differential_aberration"
            ),
            "scene_id": replay_scene.scene_id,
            "injection_location": "processing_arm_differential",
            "policy": {
                "name": "replay_conditioned_modal_pupil_fit",
                "allowed": [
                    "four_raw_camera_intensities",
                    "delivered_global_pistons",
                    "commanded_degraded_slm1_replay_intensity",
                    "frozen_optical_and_phase_delivery_calibration",
                ],
                "forbidden": [
                    "clean_target",
                    "injected_aberration_phase",
                    "injected_modal_coefficients",
                    "b0_evaluator_target",
                    "oracle_action",
                ],
                "fitted_coefficients_radians": dict(fitted.coefficients_radians),
            },
            "evaluator_truth": {
                "aberration_coefficients_radians": dict(
                    config.aberration.coefficients_radians
                ),
                "clean_target_role": "evaluator_only_after_policy_freeze",
                "b0_role": "evaluator_only_added_aberration_target",
            },
            "decision": {
                "pre_echo": episode_record.pre_echo_decision,
                "post_echo": episode_record.post_echo_decision,
            },
            "checks": checks,
            "metrics": metrics,
            "artifacts": {
                "comparison_png": figure_path,
                "episode_pt": episode_evidence_path,
                "evaluation_pt": evaluation_path,
            },
            "claim_limit": (
                "This run measures a same-model numerical differential pupil "
                "aberration on a commanded amplitude replay. It is not evidence "
                "of an independent physical aberrator or native microscopy AO."
            ),
        },
    )
    return run_dir


def _evaluate_metrics(
    degraded_intensity: torch.Tensor,
    clean_target: torch.Tensor,
    b0: OpticalObservation,
    b1: OpticalObservation,
    b2: OpticalObservation,
    b3: OpticalObservation,
) -> dict[str, float]:
    observations = {"b0": b0, "b1": b1, "b2": b2, "b3": b3}
    full_states = {
        name: _single_scene(observation.intensity)
        for name, observation in observations.items()
    }
    active_states = {
        name: extract_center_image_region(
            intensity,
            region_resolution=(256, 256),
        )
        for name, intensity in full_states.items()
    }
    b0_range = max(
        float((active_states["b0"].max() - active_states["b0"].min()).item()),
        1e-6,
    )
    removal_mse = {
        name: float(
            torch.mean((active_states[name] - active_states["b0"]).square()).item()
        )
        for name in ("b1", "b2", "b3")
    }
    metrics: dict[str, float] = {}
    for name in ("b1", "b2", "b3"):
        metrics[f"{name}_aberration_removal_mse"] = removal_mse[name]
        metrics[f"{name}_aberration_removal_psnr_db"] = min(
            _PSNR_CEILING_DB,
            psnr(active_states[name], active_states["b0"], data_range=b0_range),
        )
        metrics[f"{name}_aberration_removal_ssim"] = ssim_global(
            active_states[name],
            active_states["b0"],
            data_range=b0_range,
        )
    for name in ("b2", "b3"):
        metrics[f"{name}_aberration_removal_gain_db"] = _error_ratio_db(
            removal_mse["b1"],
            removal_mse[name],
        )

    normalized_clean_canvas = normalize_intensity(
        clean_target,
        policy="fixed_dataset_level",
        scale=1.0,
    )
    normalized_degraded_canvas = normalize_intensity(
        degraded_intensity,
        policy="fixed_dataset_level",
        scale=1.0,
    )
    clean_active_region = extract_center_image_region(
        normalized_clean_canvas,
        region_resolution=(256, 256),
    )
    degraded_active_region = extract_center_image_region(
        normalized_degraded_canvas,
        region_resolution=(256, 256),
    )
    metrics["slm1_degraded_active_clean_psnr_db"] = psnr(
        degraded_active_region,
        clean_active_region,
        data_range=1.0,
    )
    metrics["slm1_degraded_active_clean_ssim"] = ssim_global(
        degraded_active_region,
        clean_active_region,
        data_range=1.0,
    )
    metrics["slm1_degraded_fixed_aligned_clean_psnr_db"] = psnr(
        normalized_degraded_canvas,
        normalized_clean_canvas,
        data_range=1.0,
    )
    metrics["slm1_degraded_fixed_aligned_clean_ssim"] = ssim_global(
        normalized_degraded_canvas,
        normalized_clean_canvas,
        data_range=1.0,
    )
    active_clean_mse: dict[str, float] = {}
    fixed_aligned_clean_mse: dict[str, float] = {}
    for name in ("b0", "b1", "b2", "b3"):
        normalized_canvas = normalize_intensity(
            full_states[name],
            policy="fixed_dataset_level",
            scale=1.0,
        )
        normalized_active_region = extract_center_image_region(
            normalized_canvas,
            region_resolution=(256, 256),
        )
        active_clean_mse[name] = float(
            torch.mean((normalized_active_region - clean_active_region).square()).item()
        )
        fixed_aligned_clean_mse[name] = float(
            torch.mean((normalized_canvas - normalized_clean_canvas).square()).item()
        )
        metrics[f"{name}_active_clean_psnr_db"] = psnr(
            normalized_active_region,
            clean_active_region,
            data_range=1.0,
        )
        metrics[f"{name}_active_clean_ssim"] = ssim_global(
            normalized_active_region,
            clean_active_region,
            data_range=1.0,
        )
        metrics[f"{name}_fixed_aligned_clean_psnr_db"] = psnr(
            normalized_canvas,
            normalized_clean_canvas,
            data_range=1.0,
        )
        metrics[f"{name}_fixed_aligned_clean_ssim"] = ssim_global(
            normalized_canvas,
            normalized_clean_canvas,
            data_range=1.0,
        )
    metrics["b2_active_clean_gain_db_vs_b1"] = _error_ratio_db(
        active_clean_mse["b1"],
        active_clean_mse["b2"],
    )
    metrics["b3_active_clean_gain_db_vs_b1"] = _error_ratio_db(
        active_clean_mse["b1"],
        active_clean_mse["b3"],
    )
    metrics["b2_fixed_aligned_clean_gain_db_vs_b1"] = _error_ratio_db(
        fixed_aligned_clean_mse["b1"],
        fixed_aligned_clean_mse["b2"],
    )
    metrics["b3_fixed_aligned_clean_gain_db_vs_b1"] = _error_ratio_db(
        fixed_aligned_clean_mse["b1"],
        fixed_aligned_clean_mse["b3"],
    )
    return metrics


def _write_evaluation_measurements(
    path: Path,
    scene_id: str,
    states: dict[str, OpticalObservation],
    aberration_phase: torch.Tensor,
    fitted: ReplayConditionedPupilEstimate,
    pupil: torch.Tensor,
    claim_composite_states: tuple[SameDeviceCompositeState, ...],
    oracle_target_observation: OpticalObservation,
    oracle_search: DeliveredPhaseOracleSearch,
    oracle_composite_states: tuple[SameDeviceCompositeState, ...],
    oracle_calibration_id: str,
) -> Path:
    claim_state_observation_ids = _claim_state_observation_ids(
        states,
        claim_composite_states,
    )
    oracle_search_evidence = build_same_device_oracle_search_evidence(
        oracle_target_observation,
        oracle_search,
        oracle_composite_states,
        calibration_id=oracle_calibration_id,
    )
    temporary_path = path.with_suffix(".pt.tmp")
    try:
        torch.save(
            {
                "schema_version": "differential_correction_evaluation_v5",
                "scene_id": scene_id,
                "states": {
                    name: build_optical_observation_payload(value)
                    for name, value in states.items()
                },
                "evaluator_only_aberration_phase_radians": (
                    aberration_phase.detach().cpu()
                ),
                "truth_blind_estimated_phase_radians": (
                    fitted.estimated_phase_radians.detach().cpu()
                ),
                "pupil": pupil.detach().cpu(),
                "claim_state_observation_ids": claim_state_observation_ids,
                "evaluator_only_same_device_composite_states": tuple(
                    build_same_device_composite_payload(state)
                    for state in claim_composite_states
                ),
                "evaluator_only_b3_oracle_search": oracle_search_evidence,
            },
            temporary_path,
        )
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path


def _claim_state_observation_ids(
    states: dict[str, OpticalObservation],
    composite_states: tuple[SameDeviceCompositeState, ...],
) -> dict[str, str]:
    required_state_names = ("b1", "b2", "b3")
    observation_ids = {state.observation_id for state in composite_states}
    claim_state_ids: dict[str, str] = {}
    for state_name in required_state_names:
        observation = states.get(state_name)
        if observation is None:
            raise invalid_restoration_contract(
                f"evaluation states must include {state_name}"
            )
        if observation.observation_id not in observation_ids:
            raise invalid_restoration_contract(
                f"{state_name} must have an evaluator-only same-device composite state"
            )
        claim_state_ids[state_name] = observation.observation_id
    return claim_state_ids


def _write_comparison_figure(
    path: Path,
    states: dict[str, OpticalObservation],
    true_phase: torch.Tensor,
    estimated_phase: torch.Tensor,
    pupil: torch.Tensor,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    images = {
        name: extract_center_image_region(
            _single_scene(observation.intensity),
            region_resolution=(256, 256),
        )[0]
        .detach()
        .cpu()
        for name, observation in states.items()
    }
    image_maximum = max(float(image.max().item()) for image in images.values())
    true_phase_cpu = (true_phase * pupil).detach().cpu()
    estimated_phase_cpu = (estimated_phase * pupil).detach().cpu()
    residual_cpu = ((true_phase - estimated_phase) * pupil).detach().cpu()
    phase_limit = max(
        float(true_phase_cpu.abs().max().item()),
        float(estimated_phase_cpu.abs().max().item()),
        1e-6,
    )
    figure, axes = plt.subplots(2, 4, figsize=(12.0, 6.0), constrained_layout=True)
    for axis, (name, image) in zip(axes[0], images.items(), strict=True):
        axis.imshow(image, cmap="gray", vmin=0.0, vmax=image_maximum)
        axis.set_title(name)
        axis.axis("off")
    phase_panels = (
        ("Injected phase", true_phase_cpu),
        ("Fitted phase", estimated_phase_cpu),
        ("Fit residual", residual_cpu),
        ("Pupil", pupil.detach().cpu()),
    )
    for axis, (title, phase) in zip(axes[1], phase_panels, strict=True):
        if title == "Pupil":
            axis.imshow(phase, cmap="gray", vmin=0.0, vmax=1.0)
        else:
            axis.imshow(
                phase,
                cmap="twilight_shifted",
                vmin=-phase_limit,
                vmax=phase_limit,
            )
        axis.set_title(title)
        axis.axis("off")
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _single_scene(value: torch.Tensor) -> torch.Tensor:
    if value.ndim != 4 or value.shape[:2] != (1, 1):
        raise invalid_restoration_contract(
            "differential recovery requires one single-channel scene"
        )
    return value[0]


def _supported_rms(value: torch.Tensor, pupil: torch.Tensor) -> float:
    support = pupil > 0.0
    return float(torch.sqrt(torch.mean(value[support].square())).item())


def _error_ratio_db(baseline_error: float, corrected_error: float) -> float:
    ratio = max(baseline_error, 1e-12) / max(corrected_error, 1e-12)
    return min(_PSNR_CEILING_DB, 10.0 * math.log10(ratio))


def _finite_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise invalid_restoration_contract(f"{name} must be a finite real number")
    return normalized


def _positive_real(name: str, value: object) -> float:
    normalized = _finite_real(name, value)
    if normalized <= 0.0:
        raise invalid_restoration_contract(f"{name} must be positive")
    return normalized


def _nonnegative_real(name: str, value: object) -> float:
    normalized = _finite_real(name, value)
    if normalized < 0.0:
        raise invalid_restoration_contract(f"{name} must be nonnegative")
    return normalized


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    return int(value)


def _nonnegative_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise invalid_restoration_contract(f"{name} must be a nonnegative integer")
    return int(value)

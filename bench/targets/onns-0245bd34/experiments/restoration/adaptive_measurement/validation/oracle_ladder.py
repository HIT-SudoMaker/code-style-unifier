from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Literal

import torch
from torch.nn import functional

from experiments.restoration.adaptive_measurement.adapters.simulated_bench import (
    CoherentPupilBench,
    CoherentPupilScene,
)
from experiments.restoration.adaptive_measurement.protocol.oracle import (
    OracleLadderConfig,
    OracleLadderResult,
)
from experiments.restoration.adaptive_measurement.evidence import (
    build_optical_observation_payload,
)
from experiments.restoration.adaptive_measurement.validation.delivered_phase_oracle import (
    BoundCoherentPupilEvaluator,
    DeliveredPhaseOracleSearch,
    search_calibrated_delivered_phase,
)
from experiments.restoration.adaptive_measurement.validation.oracle_evidence import (
    build_delivered_phase_oracle_trace,
)
from experiments.restoration.adaptive_measurement.validation.target_visible_phase_oracle import (
    optimize_target_visible_phase,
)
from experiments.restoration.evidence import (
    compute_config_hash,
    write_json,
    write_runtime,
)
from experiments.restoration.metrics import psnr, ssim_global
from experiments.restoration.observations import OpticalObservation
from experiments.restoration.optical_bench import (
    DetectorNoiseModel,
    OpticalBenchConfig,
    build_phase_zero_transfer,
    propagate_interferometric_bench,
)
from experiments.restoration.optical_bench.evaluator import (
    propagate_evaluator_complex_transfer,
)
from experiments.restoration.phase_control import (
    IdealPhaseDelivery,
    PhaseCommand,
    SimulatedSlmPhaseDelivery,
)
from experiments.restoration.pupil_aberrations import build_pupil_aberration_phase
from experiments.restoration.targets import siemens_star, slanted_edge, usaf_bars


_PSNR_CEILING_DB = 120.0
_ACTION_SPACE_O1 = "arbitrary_complex_transfer"
_ACTION_SPACE_O2 = "ideal_reference_assisted_phase_only"
_ACTION_SPACE_O3 = "calibrated_delivered_phase_only"


@dataclass(frozen=True, slots=True, eq=False)
class _OracleObservation:
    observation_id: str
    intensity: torch.Tensor
    is_reference_enabled: bool
    action_space: str
    command_phase_radians: torch.Tensor | None = None
    delivered_phase_radians: torch.Tensor | None = None
    processing_transfer: torch.Tensor | None = None
    metadata: dict[str, object] | None = None


@torch.no_grad()
def run_oracle_ladder(config: OracleLadderConfig) -> OracleLadderResult:
    """Run physically distinct O1, O2, and O3 clean-endpoint upper bounds."""
    if not isinstance(config, OracleLadderConfig):
        raise TypeError("config must be an OracleLadderConfig")
    if config.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")

    config_hash = compute_config_hash(config)
    run_id = f"oracle_s{config.seed}_c{config_hash[:12]}"
    run_dir = (
        Path(config.project_root)
        / "results"
        / "restoration"
        / "adaptive_measurement"
        / "oracle_ladder"
        / run_id
    )
    if run_dir.exists():
        raise FileExistsError(f"immutable Oracle Ladder run already exists: {run_dir}")

    device = torch.device(config.device)
    target = _build_target(config)
    clean_intensity = torch.from_numpy(target.image).to(
        device=device,
        dtype=torch.float32,
    )[None, None]
    degraded_intensity = functional.avg_pool2d(
        clean_intensity,
        kernel_size=config.input_blur_kernel_size,
        stride=1,
        padding=config.input_blur_kernel_size // 2,
    )
    clean_field = torch.sqrt(torch.clamp(clean_intensity, min=0.0)).to(
        dtype=torch.complex64
    )
    degraded_field = torch.sqrt(torch.clamp(degraded_intensity, min=0.0)).to(
        dtype=torch.complex64
    )
    bench_config = OpticalBenchConfig(
        input_array_resolution=config.array_resolution,
        phase_mask_resolution=min(config.array_resolution),
    )
    aberration_phase, pupil = build_pupil_aberration_phase(
        config.array_resolution,
        config.aberration,
        device=device,
    )
    clean_scene = CoherentPupilScene(
        clean_field,
        torch.zeros_like(aberration_phase),
        pupil,
    )
    degraded_scene = CoherentPupilScene(
        degraded_field,
        aberration_phase,
        pupil,
    )
    zero_phase = torch.zeros(config.array_resolution, device=device)
    safe_command = PhaseCommand("safe_zero_phase", zero_phase)
    ideal_bench = _build_bench(config, IdealPhaseDelivery())
    quiet_ideal_bench = _build_bench(
        config,
        IdealPhaseDelivery(),
        include_noise=False,
    )
    delivered_phase = SimulatedSlmPhaseDelivery(
        phase_levels=config.phase_levels,
        response_gain=config.response_gain,
        drift_radians=config.drift_radians,
        crosstalk_mix=config.crosstalk_mix,
    )
    delivered_bench = _build_bench(config, delivered_phase)
    quiet_delivered_bench = _build_bench(
        config,
        delivered_phase,
        include_noise=False,
    )

    clean_endpoint = ideal_bench.acquire(
        clean_scene,
        safe_command,
        observation_id="diffraction_limited_science",
        kind="science",
        sequence_index=0,
    )
    quiet_clean_endpoint = quiet_ideal_bench.acquire(
        clean_scene,
        safe_command,
        observation_id="diffraction_limited_optimization_reference",
        kind="science",
        sequence_index=100,
    )
    safe = ideal_bench.acquire(
        degraded_scene,
        safe_command,
        observation_id="safe_science",
        kind="science",
        sequence_index=1,
    )

    complex_transfer = _solve_arbitrary_complex_transfer(
        degraded_field,
        quiet_clean_endpoint.intensity,
        aberration_phase,
        pupil,
        bench_config,
    )
    o1_fields = propagate_evaluator_complex_transfer(
        degraded_field,
        complex_transfer,
        bench_config,
    )
    o1 = _OracleObservation(
        observation_id="o1_science",
        intensity=DetectorNoiseModel(
            photon_count=config.photon_count,
            read_noise_standard_deviation=config.read_noise_standard_deviation,
            seed=config.seed,
        ).sample(
            o1_fields.combined_intensity,
            sequence_index=2,
        ),
        is_reference_enabled=True,
        action_space=_ACTION_SPACE_O1,
        processing_transfer=complex_transfer,
        metadata={"optimizer": "regularized_closed_form_complex_transfer"},
    )

    phase_oracle = optimize_target_visible_phase(
        degraded_input_field=degraded_field,
        evaluator_target_intensity=quiet_clean_endpoint.intensity,
        bench_config=bench_config,
        evaluation_resolution=config.array_resolution,
        iteration_count=config.phase_optimization_iteration_count,
        learning_rate=config.phase_optimization_learning_rate,
        response_gain=1.0,
        drift_radians=0.0,
        processing_aberration_radians=aberration_phase,
        processing_pupil=pupil,
    )
    o2_command = PhaseCommand(
        "o2_ideal_phase_oracle",
        phase_oracle.command.phase_radians,
        piston_radians=phase_oracle.command.piston_radians,
    )
    o2_observation = ideal_bench.acquire(
        degraded_scene,
        o2_command,
        observation_id="o2_science",
        kind="science",
        sequence_index=3,
    )
    o2 = _phase_observation(o2_observation, action_space=_ACTION_SPACE_O2)

    calibrated_o3_seed = delivered_phase.project_delivered_phase(
        "o3_calibrated_seed",
        o2_observation.delivered_phase_radians,
        pupil=pupil,
    )
    o3_search = search_calibrated_delivered_phase(
        BoundCoherentPupilEvaluator(quiet_delivered_bench, degraded_scene),
        quiet_clean_endpoint.intensity,
        calibrated_o3_seed,
        pupil=pupil,
        command_multipliers=tuple(
            float(value) for value in torch.linspace(0.9, 1.1, 17).tolist()
        ),
        spatial_detail_strengths=(0.0, 0.05, 0.10, 0.15, 0.20),
        command_id="o3_delivered_phase_oracle",
        observation_id_prefix="o3-search",
        sequence_index_start=100,
    )
    o3_observation = delivered_bench.acquire(
        degraded_scene,
        o3_search.command,
        observation_id="o3_science",
        kind="science",
        sequence_index=4,
    )
    o3 = _phase_observation(o3_observation, action_space=_ACTION_SPACE_O3)

    observations = {
        "diffraction_limited": _phase_observation(
            clean_endpoint,
            action_space="no_action_clean_endpoint",
        ),
        "safe": _phase_observation(safe, action_space="no_action_degraded_input"),
        "o1": o1,
        "o2": o2,
        "o3": o3,
    }
    metrics = _evaluate_ladder(observations)
    metrics.update(
        {
            "o3_search_candidate_count": float(o3_search.candidate_count),
            "o3_selected_command_multiplier": (o3_search.selected_command_multiplier),
            "o3_selected_sharpening_strength": (
                o3_search.selected_spatial_detail_strength
            ),
            "o3_search_mean_square_error": o3_search.mean_square_error,
        }
    )
    checks = _evaluate_checks(
        observations,
        metrics=metrics,
        minimum_o3_gain_db=config.minimum_o3_gain_db,
    )
    status: Literal["PASS", "FAIL"] = "PASS" if all(checks.values()) else "FAIL"

    run_dir.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir()
    config_json = write_json(run_dir / "config.json", config)
    runtime_json = write_runtime(run_dir / "runtime.json")
    metrics_json = write_json(run_dir / "metrics.json", metrics)
    checks_json = write_json(run_dir / "checks.json", checks)
    observations_pt = _write_observations(run_dir / "observations.pt", observations)
    o3_search_pt = _write_delivered_phase_search(
        run_dir / "o3_search.pt",
        quiet_clean_endpoint,
        o3_search,
        calibration_id=config_hash,
    )
    ladder = {
        "o1": _ACTION_SPACE_O1,
        "o2": _ACTION_SPACE_O2,
        "o3": _ACTION_SPACE_O3,
    }
    result_payload = {
        "schema_version": "adaptive_oracle_ladder_v3",
        "status": status,
        "run_id": run_id,
        "experiment_stage": "E1_oracle_ladder",
        "evidence_level": "simulation_sanity_check_not_e1_completion",
        "oracle_ladder": ladder,
        "checks": checks,
        "claim_limit": (
            "One deterministic clean-endpoint simulation checks the three action "
            "spaces; it does not establish robust E1 evidence, autonomous Adaptive "
            "performance, or an independent physical aberrator."
        ),
        "metrics": metrics,
        "artifacts": {
            "config_json": config_json,
            "runtime_json": runtime_json,
            "metrics_json": metrics_json,
            "checks_json": checks_json,
            "observations_pt": observations_pt,
            "o3_search_pt": o3_search_pt,
        },
        "target": target.metadata,
        "input_degradation": {
            "kind": "deterministic_average_blur",
            "kernel_size": config.input_blur_kernel_size,
        },
        "aberration_coefficients_radians": dict(config.aberration.coefficients_radians),
    }
    result_json = write_json(run_dir / "result.json", result_payload)
    summary_md = _write_summary(
        run_dir / "summary.md",
        status=status,
        run_id=run_id,
        metrics=metrics,
    )
    return OracleLadderResult(
        status=status,
        run_id=run_id,
        run_dir=run_dir,
        metrics=metrics,
        result_json=result_json,
        summary_md=summary_md,
    )


def _build_target(config: OracleLadderConfig):
    builders = {
        "siemens_star": siemens_star,
        "slanted_edge": slanted_edge,
        "usaf_bars": usaf_bars,
    }
    return builders[config.target_name](config.array_resolution)


def _build_bench(
    config: OracleLadderConfig,
    phase_delivery,
    *,
    include_noise: bool = True,
) -> CoherentPupilBench:
    return CoherentPupilBench(
        OpticalBenchConfig(
            input_array_resolution=config.array_resolution,
            phase_mask_resolution=min(config.array_resolution),
        ),
        phase_delivery,
        photon_count=config.photon_count if include_noise else None,
        read_noise_standard_deviation=(
            config.read_noise_standard_deviation if include_noise else 0.0
        ),
        seed=config.seed,
        device=config.device,
    )


def _solve_arbitrary_complex_transfer(
    degraded_field: torch.Tensor,
    clean_endpoint_intensity: torch.Tensor,
    aberration_phase: torch.Tensor,
    pupil: torch.Tensor,
    bench_config: OpticalBenchConfig,
) -> torch.Tensor:
    """Solve the scene-conditioned complex transfer needed by the O1 upper bound."""
    safe_fields = propagate_interferometric_bench(
        degraded_field,
        torch.zeros_like(aberration_phase),
        bench_config,
        processing_aberration_radians=aberration_phase,
        processing_pupil=pupil,
    )
    target_amplitude = torch.sqrt(torch.clamp(clean_endpoint_intensity, min=0.0))
    target_phase = torch.angle(safe_fields.combined)
    target_field = target_amplitude.to(degraded_field.dtype) * torch.exp(
        1j * target_phase
    )
    processing_scale = (
        math.sqrt(bench_config.split_ratio_process)
        * bench_config.amplitude_gain_process
    )
    if processing_scale <= 0.0:
        raise RuntimeError("O1 requires a nonzero processing-arm amplitude")
    desired_processing_field = (target_field - safe_fields.reference) / processing_scale
    input_spectrum = torch.fft.fftshift(
        torch.fft.fft2(degraded_field, dim=(-2, -1)),
        dim=(-2, -1),
    )
    desired_spectrum = torch.fft.fftshift(
        torch.fft.fft2(desired_processing_field, dim=(-2, -1)),
        dim=(-2, -1),
    )
    input_power = input_spectrum.abs().square()
    regularization = torch.clamp(input_power.amax() * 1e-8, min=1e-12)
    transfer = (
        desired_spectrum * torch.conj(input_spectrum) / (input_power + regularization)
    )[0, 0]
    physical_aperture = build_phase_zero_transfer(
        array_resolution=bench_config.input_array_resolution,
        pixel_size=bench_config.input_plane_pixel_size,
        aperture_policy=bench_config.aperture_policy,
        wavelength=bench_config.wavelength,
        focal_length=bench_config.focal_length,
        slm2_resolution=bench_config.slm2_resolution,
        slm2_pixel_size=bench_config.slm2_pixel_size,
        phase_mask_resolution=bench_config.phase_mask_resolution,
        slm2_active_area_policy=bench_config.slm2_active_area_policy,
        slm2_active_resolution=bench_config.slm2_active_resolution,
        device=degraded_field.device,
        dtype=degraded_field.real.dtype,
    )
    support = physical_aperture * (pupil > 0.0).to(physical_aperture.dtype)
    return transfer * support.to(transfer.dtype)


def _phase_observation(
    observation: OpticalObservation,
    *,
    action_space: str,
) -> _OracleObservation:
    return _OracleObservation(
        observation_id=observation.observation_id,
        intensity=observation.intensity,
        is_reference_enabled=observation.is_reference_enabled,
        action_space=action_space,
        command_phase_radians=observation.command_phase_radians,
        delivered_phase_radians=observation.delivered_phase_radians,
        metadata=dict(observation.metadata),
    )


def _evaluate_ladder(
    observations: dict[str, _OracleObservation],
) -> dict[str, float]:
    reference = observations["diffraction_limited"].intensity
    dynamic_range = max(float((reference.max() - reference.min()).item()), 1e-6)
    metrics: dict[str, float] = {}
    mean_square_errors: dict[str, float] = {}
    for name in ("safe", "o1", "o2", "o3"):
        intensity = observations[name].intensity
        mean_square_error = float(torch.mean((intensity - reference).square()).item())
        mean_square_errors[name] = mean_square_error
        metrics[f"{name}_psnr_db"] = min(
            float(psnr(intensity, reference, data_range=dynamic_range)),
            _PSNR_CEILING_DB,
        )
        metrics[f"{name}_ssim"] = ssim_global(
            intensity,
            reference,
            data_range=dynamic_range,
        )
        metrics[f"{name}_mean_square_error"] = mean_square_error
    for name in ("o1", "o2", "o3"):
        metrics[f"{name}_gain_db"] = _error_ratio_db(
            mean_square_errors["safe"],
            mean_square_errors[name],
        )
    metrics["o1_to_o2_control_gap_db"] = metrics["o1_psnr_db"] - metrics["o2_psnr_db"]
    metrics["o2_to_o3_delivery_loss_db"] = max(
        0.0,
        metrics["o2_psnr_db"] - metrics["o3_psnr_db"],
    )
    return metrics


def _evaluate_checks(
    observations: dict[str, _OracleObservation],
    *,
    metrics: dict[str, float],
    minimum_o3_gain_db: float,
) -> dict[str, bool]:
    observation_ids = [value.observation_id for value in observations.values()]
    action_spaces = {observations[name].action_space for name in ("o1", "o2", "o3")}
    o1_transfer = observations["o1"].processing_transfer
    assert o1_transfer is not None
    nonzero_amplitude = o1_transfer.abs()[o1_transfer.abs() > 1e-8]
    is_o1_amplitude_active = bool(
        nonzero_amplitude.numel()
        and torch.any(torch.abs(nonzero_amplitude - 1.0) > 1e-3)
    )
    return {
        "all_outputs_are_causally_distinct": len(set(observation_ids))
        == len(observation_ids),
        "all_science_observations_keep_reference": all(
            observation.is_reference_enabled for observation in observations.values()
        ),
        "oracle_action_spaces_are_physically_distinct": len(action_spaces) == 3,
        "o1_uses_non_phase_only_transfer_amplitude": is_o1_amplitude_active,
        "o1_is_not_worse_than_o2": metrics["o1_mean_square_error"]
        <= metrics["o2_mean_square_error"] + 1e-9,
        "o3_exceeds_preregistered_headroom": metrics["o3_gain_db"]
        >= minimum_o3_gain_db,
    }


def _error_ratio_db(baseline_error: float, corrected_error: float) -> float:
    ratio = max(baseline_error, 1e-12) / max(corrected_error, 1e-12)
    return min(_PSNR_CEILING_DB, 10.0 * math.log10(ratio))


def _write_observations(
    path: Path,
    observations: dict[str, _OracleObservation],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".pt.tmp")
    try:
        torch.save(
            {
                name: {
                    "observation_id": observation.observation_id,
                    "action_space": observation.action_space,
                    "command_phase_radians": _cpu_tensor(
                        observation.command_phase_radians
                    ),
                    "delivered_phase_radians": _cpu_tensor(
                        observation.delivered_phase_radians
                    ),
                    "processing_transfer": _cpu_tensor(observation.processing_transfer),
                    "intensity": observation.intensity.detach().cpu(),
                    "metadata": observation.metadata or {},
                }
                for name, observation in observations.items()
            },
            temporary_path,
        )
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path


def _write_delivered_phase_search(
    path: Path,
    target_observation: OpticalObservation,
    search: DeliveredPhaseOracleSearch,
    *,
    calibration_id: str,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".pt.tmp")
    try:
        torch.save(
            {
                "schema_version": "oracle_ladder_o3_search_v1",
                "calibration_id": calibration_id,
                "target_observation": build_optical_observation_payload(
                    target_observation
                ),
                "search": build_delivered_phase_oracle_trace(search),
            },
            temporary_path,
        )
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path


def _cpu_tensor(value: torch.Tensor | None) -> torch.Tensor | None:
    return None if value is None else value.detach().cpu()


def _write_summary(
    path: Path,
    *,
    status: str,
    run_id: str,
    metrics: dict[str, float],
) -> Path:
    lines = [
        "# Adaptive Oracle Ladder simulation",
        "",
        f"- Status: `{status}`",
        f"- Run: `{run_id}`",
        f"- O1 arbitrary-complex gain: `{metrics['o1_gain_db']:.3f} dB`",
        f"- O2 ideal phase-only gain: `{metrics['o2_gain_db']:.3f} dB`",
        f"- O3 delivered phase-only gain: `{metrics['o3_gain_db']:.3f} dB`",
        f"- O1-to-O2 control gap: `{metrics['o1_to_o2_control_gap_db']:.3f} dB`",
        f"- O2-to-O3 delivery loss: `{metrics['o2_to_o3_delivery_loss_db']:.3f} dB`",
        "",
        "This is one deterministic action-space check, not completion of E1.",
    ]
    temporary_path = path.with_suffix(".md.tmp")
    try:
        temporary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path

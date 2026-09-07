from __future__ import annotations

from collections.abc import Iterable, Mapping
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from experiments.restoration.evidence import (
    compute_config_hash,
    write_json,
    write_runtime,
)
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.fixed_measurement.learning.schemas import (
    BENCHMARK_BASELINE_FIELDS,
    BENCHMARK_EFFICIENCY_FIELDS,
    BENCHMARK_SAMPLE_FIELDS,
    BENCHMARK_SIGNIFICANCE_FIELDS,
    BOUNDARY_FAILURE_FIELDS,
    BOUNDARY_GRID_FIELDS,
    RESTORATION_MODEL_ROLES,
    backend_identity_strings,
)

if TYPE_CHECKING:
    from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
    from experiments.restoration.fixed_measurement.learning.config import BasicConfig


CHARACTERIZATION_METRIC_FIELDS = (
    "candidate_id",
    "sweep_step",
    "run_name",
    "target_name",
    "target_variant",
    "baseline_name",
    "focal_length",
    "phase_mask_resolution",
    "aperture_policy",
    "slm2_active_area_policy",
    "padding_policy",
    "phase_offset_reference",
    "camera_oversampling_factor",
    "camera_sampling",
    "camera_binning_policy",
    "spatial_frequency",
    "metric_name",
    "metric_value",
    "metric_unit",
    "status",
)

TRAINING_EPOCH_FIELDS = (
    "epoch",
    "split",
    "optimizer_updates",
    "loss_total",
    "loss_l1",
    "loss_ssim",
    "loss_frequency",
    "phase_smoothness",
    "psnr_raw",
    "ssim_raw",
    "psnr_normalized",
    "ssim_normalized",
    "energy_throughput",
    "clipping_ratio",
    "learning_rate",
    "phase_offset_reference",
    "optical_residual_gate",
    "operating_point_hash",
    "status",
)

_TRAINING_EPOCH_HEADER_INCOMPATIBLE = (
    "epoch_metrics.csv has an incompatible header"
)


def build_characterization_paths(basic: "BasicConfig") -> dict[str, Path]:
    """
    鏋勫缓琛ㄥ緛瀹為獙浜х墿璺緞
    """
    normalized = basic.normalized()
    run_dir = (
        Path(normalized.project_root)
        / "results"
        / "restoration"
        / "characterization"
        / normalized.run_name
    )
    return {
        "run_dir": run_dir,
        "figures_dir": run_dir / "figures",
        "metrics_csv": run_dir / "metrics.csv",
        "summary_md": run_dir / "summary.md",
        "config_json": run_dir / "config.json",
        "runtime_json": run_dir / "runtime.json",
        "operating_point_json": run_dir / "operating_point.json",
        "theoretical_resolution_budget_json": run_dir
        / "theoretical_resolution_budget.json",
    }


def build_training_paths(
    basic: "BasicConfig",
    *,
    model_role: str = "frontend_only",
    backend: "BackendConfig | None" = None,
) -> dict[str, Path]:
    """
    鏋勫缓璁粌浜х墿璺緞
    """
    normalized = basic.normalized()
    training_root = Path(normalized.project_root) / "results" / "restoration" / "training"
    valid_roles = tuple(role for role in RESTORATION_MODEL_ROLES if role != "deterministic")
    if model_role not in valid_roles:
        raise invalid_restoration_contract(
            f"model_role must be one of: {', '.join(valid_roles)}"
        )
    if model_role == "frontend_only":
        run_dir = training_root / "frontend_only" / normalized.run_name
    elif model_role == "backend_only":
        if backend is None:
            raise invalid_restoration_contract(
                "backend is required for non-frontend training roles"
            )
        backend_family, backend_model = backend_identity_strings(backend)
        run_dir = (
            training_root
            / "backend_only"
            / backend_family
            / backend_model
            / normalized.run_name
        )
    else:
        if backend is None:
            raise invalid_restoration_contract(
                "backend is required for non-frontend training roles"
            )
        backend_family, backend_model = backend_identity_strings(backend)
        run_dir = (
            training_root
            / "hybrid"
            / model_role
            / backend_family
            / backend_model
            / normalized.run_name
        )
    return {
        "run_dir": run_dir,
        "figures_dir": run_dir / "figures",
        "checkpoints_dir": run_dir / "checkpoints",
        "best_checkpoint": run_dir / "checkpoints" / "best.pt",
        "last_checkpoint": run_dir / "checkpoints" / "last.pt",
        "operating_point_used_json": run_dir / "operating_point_used.json",
        "checks_json": run_dir / "checks.json",
        "phase_masks_dir": run_dir / "phase_masks",
        "epoch_metrics_csv": run_dir / "epoch_metrics.csv",
        "final_metrics_json": run_dir / "final_metrics.json",
        "summary_md": run_dir / "summary.md",
        "config_json": run_dir / "config.json",
        "runtime_json": run_dir / "runtime.json",
        "optuna_dir": run_dir / "optuna",
        "optuna_study_json": run_dir / "optuna" / "study_summary.json",
    }


def build_backend_calibration_paths(
    project_root: str | Path,
    *,
    profile_name: str,
    backend_model: str,
) -> dict[str, Path]:
    """
    鏋勫缓鏁板瓧鍚庣鏍″噯浜х墿璺緞
    """
    run_dir = (
        Path(project_root)
        / "results"
        / "restoration"
        / "training"
        / "backend_calibration"
        / f"{profile_name}_{backend_model}"
    )
    return {
        "run_dir": run_dir,
        "backend_budget_json": run_dir / "backend_budget.json",
    }


def build_benchmark_paths(project_root: str | Path, *, study_name: str) -> dict[str, Path]:
    """
    鏋勫缓鍩哄噯璇勪及浜х墿璺緞
    """
    run_dir = Path(project_root) / "results" / "restoration" / "benchmark" / study_name
    return {
        "run_dir": run_dir,
        "figures_dir": run_dir / "figures",
        "examples_dir": run_dir / "examples",
        "config_json": run_dir / "config.json",
        "runtime_json": run_dir / "runtime.json",
        "dataset_manifest_json": run_dir / "dataset_manifest.json",
        "method_manifest_json": run_dir / "method_manifest.json",
        "sample_metrics_csv": run_dir / "sample_metrics.csv",
        "baseline_metrics_csv": run_dir / "baseline_metrics.csv",
        "significance_tests_csv": run_dir / "significance_tests.csv",
        "efficiency_metrics_csv": run_dir / "efficiency_metrics.csv",
        "summary_md": run_dir / "summary.md",
    }


def build_boundary_paths(project_root: str | Path, *, study_name: str) -> dict[str, Path]:
    """
    鏋勫缓杈圭晫鐮旂┒浜х墿璺緞
    """
    run_dir = Path(project_root) / "results" / "restoration" / "boundary" / study_name
    return {
        "run_dir": run_dir,
        "figures_dir": run_dir / "figures",
        "examples_dir": run_dir / "examples",
        "config_json": run_dir / "config.json",
        "runtime_json": run_dir / "runtime.json",
        "dataset_manifest_json": run_dir / "dataset_manifest.json",
        "method_manifest_json": run_dir / "method_manifest.json",
        "degradation_grid_csv": run_dir / "degradation_grid.csv",
        "boundary_metrics_csv": run_dir / "boundary_metrics.csv",
        "failure_boundary_csv": run_dir / "failure_boundary.csv",
        "summary_md": run_dir / "summary.md",
    }


def write_characterization_metrics(
    path: Path | str,
    rows: Iterable[Mapping[str, object]],
) -> Path:
    """
    鍐欏叆琛ㄥ緛瀹為獙鎸囨爣
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CHARACTERIZATION_METRIC_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {field: row.get(field) for field in CHARACTERIZATION_METRIC_FIELDS}
            )
    return output_path


def write_benchmark_sample_metrics(
    path: Path | str,
    rows: Iterable[Mapping[str, object]],
) -> Path:
    """
    鍐欏叆鍩哄噯璇勪及鏍锋湰绾ф寚鏍?    """
    return _write_csv_rows(path, BENCHMARK_SAMPLE_FIELDS, rows)


def write_benchmark_baseline_metrics(
    path: Path | str,
    rows: Iterable[Mapping[str, object]],
) -> Path:
    """
    鍐欏叆鍩哄噯璇勪及鑱氬悎鎸囨爣
    """
    return _write_csv_rows(path, BENCHMARK_BASELINE_FIELDS, rows)


def write_benchmark_significance_tests(
    path: Path | str,
    rows: Iterable[Mapping[str, object]],
) -> Path:
    """
    鍐欏叆鍩哄噯閰嶅鏄捐憲鎬ф楠岃褰?    """
    return _write_csv_rows(path, BENCHMARK_SIGNIFICANCE_FIELDS, rows)


def write_benchmark_efficiency_metrics(
    path: Path | str,
    rows: Iterable[Mapping[str, object]],
) -> Path:
    """
    鍐欏叆鍩哄噯妯″瀷鏁堢巼璁板綍
    """
    return _write_csv_rows(path, BENCHMARK_EFFICIENCY_FIELDS, rows)


def write_boundary_grid(
    path: Path | str,
    rows: Iterable[Mapping[str, object]],
) -> Path:
    """
    鍐欏叆杈圭晫鐮旂┒閫€鍖栫綉鏍?    """
    return _write_csv_rows(path, BOUNDARY_GRID_FIELDS, rows)


def write_failure_boundary(
    path: Path | str,
    rows: Iterable[Mapping[str, object]],
) -> Path:
    """
    鍐欏叆杈圭晫鐮旂┒澶辨晥杈圭晫
    """
    return _write_csv_rows(path, BOUNDARY_FAILURE_FIELDS, rows)


def _write_csv_rows(
    path: Path | str,
    fieldnames: tuple[str, ...],
    rows: Iterable[Mapping[str, object]],
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = _temporary_artifact_path(output_path)
    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return output_path


def append_training_epoch_metrics(
    path: Path | str,
    rows: Iterable[Mapping[str, object]],
) -> Path:
    """
    瀹炵幇浜х墿杈呭姪閫昏緫
    """
    output_path = Path(path)
    existing_rows: list[Mapping[str, object]] = []
    if output_path.is_file() and output_path.stat().st_size > 0:
        with output_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != TRAINING_EPOCH_FIELDS:
                raise ValueError(_TRAINING_EPOCH_HEADER_INCOMPATIBLE)
            existing_rows.extend(dict(row) for row in reader)
    existing_rows.extend(rows)
    return write_training_epoch_metrics(output_path, existing_rows)


def write_training_epoch_metrics(
    path: Path | str,
    rows: Iterable[Mapping[str, object]],
) -> Path:
    """
    鍘熷瓙鍐欏叆瀹屾暣璁粌杞鍘嗗彶
    """
    return _write_csv_rows(path, TRAINING_EPOCH_FIELDS, rows)


def _temporary_artifact_path(output_path: Path) -> Path:
    return output_path.with_name(f"._{uuid4().hex[:12]}.tmp")


def build_operating_point_payload(
    *,
    basic: object,
    model: object,
    characterization: object,
    theoretical_budget: Mapping[str, object],
    selected_values: Mapping[str, object],
    source_config_path: Path | str,
    source_metrics_path: Path | str,
    code_version: str | None = None,
) -> dict[str, object]:
    """
    鏋勫缓杩愯鐐逛骇鐗?    """
    selection_metrics = selected_values.get("selection_metrics", {})
    operating_point: dict[str, object] = {
        "wavelength": getattr(model, "wavelength"),
        "input_plane_pixel_size": getattr(model, "input_plane_pixel_size"),
        "slm1_pixel_size": getattr(model, "slm1_pixel_size"),
        "slm2_pixel_size": getattr(model, "slm2_pixel_size"),
        "camera_pixel_size": getattr(model, "camera_pixel_size"),
        "focal_length": getattr(model, "focal_length"),
        "propagation_distance": getattr(model, "focal_length"),
        "array_size": getattr(model, "input_array_resolution")[0],
        "phase_mask_resolution": getattr(model, "phase_mask_resolution"),
        "slm2_active_resolution": getattr(model, "slm2_active_resolution"),
        "aperture_policy": getattr(model, "aperture_policy"),
        "slm2_active_area_policy": getattr(model, "slm2_active_area_policy"),
        "camera_oversampling_factor": getattr(model, "camera_oversampling_factor"),
        "camera_sampling": "native_sensor",
        "camera_binning_policy": getattr(model, "camera_binning_policy"),
        "phase_offset_reference": getattr(model, "phase_offset_reference"),
        "aperture_cutoff_frequency": theoretical_budget["aperture_cutoff_frequency"],
        "fourier_plane_pixel_size_x": theoretical_budget.get(
            "fourier_plane_pixel_size_x"
        ),
        "fourier_plane_pixel_size_y": theoretical_budget.get(
            "fourier_plane_pixel_size_y"
        ),
        "fourier_plane_width": theoretical_budget.get("fourier_plane_width"),
        "fourier_plane_height": theoretical_budget.get("fourier_plane_height"),
        "slm2_active_window_size": theoretical_budget.get("slm2_active_window_size"),
        "measured_mtf50": selection_metrics.get("edge_mtf50_cycles_per_pixel", 0.0),
        "energy_throughput": selection_metrics.get("energy_throughput", 0.0),
        "interference_visibility": selection_metrics.get("interference_visibility", 0.0),
    }
    payload: dict[str, object] = {
        "stage": "characterization",
        "status": "PASS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config_hash": compute_config_hash(characterization),
        "geometry_hash": compute_config_hash(model),
        "source_config_path": str(Path(source_config_path)),
        "source_metrics_path": str(Path(source_metrics_path)),
        "selected_values": selected_values,
        "operating_point": operating_point,
        "basic": basic,
        "geometry": model,
        "characterization": characterization,
    }
    if code_version is not None:
        payload["code_version"] = code_version
    return payload


def write_operating_point(
    path: Path | str,
    *,
    basic: object,
    model: object,
    characterization: object,
    theoretical_budget: Mapping[str, object],
    selected_values: Mapping[str, object],
    source_config_path: Path | str,
    source_metrics_path: Path | str,
    code_version: str | None = None,
) -> Path:
    """
    鍐欏叆杩愯鐐逛骇鐗?    """
    payload = build_operating_point_payload(
        basic=basic,
        model=model,
        characterization=characterization,
        theoretical_budget=theoretical_budget,
        selected_values=selected_values,
        source_config_path=source_config_path,
        source_metrics_path=source_metrics_path,
        code_version=code_version,
    )
    return write_json(path, payload)

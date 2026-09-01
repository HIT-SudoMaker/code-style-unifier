from __future__ import annotations

from collections.abc import Mapping
import csv
from dataclasses import asdict, is_dataclass, replace
import json
import math
from numbers import Real
from pathlib import Path
import random

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from experiments.restoration.fixed_measurement.evidence.training_artifacts import (
    TRAINING_EPOCH_FIELDS,
    append_training_epoch_metrics,
    build_training_paths,
    compute_config_hash,
    write_json,
    write_runtime,
    write_training_epoch_metrics,
)
from experiments.restoration.fixed_measurement.learning.config import (
    TrainingConfig,
)
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.fixed_measurement.learning.checkpoints import (
    backend_payload,
    load_frontend_source_if_needed,
    restore_rng_state,
    save_checkpoint,
    verify_provenance,
)
from experiments.restoration.fixed_measurement.learning.data_loading import (
    build_restoration_loader,
    degraded_from_batch,
    ensure_batched_field,
    target_from_batch,
)
from experiments.restoration.fixed_measurement.learning.engine import (
    GradientAccumulationState,
    baseline_metrics,
    degraded_image_from_batch,
    run_epoch,
)
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.fixed_measurement.learning.model_assembly import (
    _effective_phase_for_model,
    _initial_phase_mask_for_model,
    _mechanism_parameter_stats,
    _phase_mask_stats,
    _reference_phase_offset_provenance,
    _trainable_parameter_names,
    assemble_model,
)
from experiments.restoration.fixed_measurement.learning.model_stats import count_model_macs, count_trainable_parameters
from experiments.restoration.metrics import normalize_intensity
from experiments.restoration.fixed_measurement.learning.operators import defocus_operator_for_dataset
from experiments.restoration.fixed_measurement.optics.reference_arm import inject_live_reference_arm
from experiments.restoration.fixed_measurement.learning.standard_configs import degradation_hash_for_dataset_config
from experiments.restoration.fixed_measurement.learning.visualize import (
    visualize_frequency_response_comparison,
    visualize_operating_point_trace,
    visualize_phase_mask_evolution,
    visualize_restoration_examples,
    visualize_training_dynamics,
)


_RESOLUTION_FIELDS = {
    "slm1_resolution",
    "slm2_resolution",
    "camera_resolution",
    "input_array_resolution",
    "slm2_active_resolution",
}

_REQUIRED_TRAINING_FIGURES = (
    "01_training_dynamics.png",
    "01_training_dynamics.svg",
    "02_restoration_examples.png",
    "02_restoration_examples.svg",
    "03_phase_mask_evolution.png",
    "03_phase_mask_evolution.svg",
    "04_frequency_response_comparison.png",
    "04_frequency_response_comparison.svg",
    "05_operating_point_trace.png",
    "05_operating_point_trace.svg",
)

_RESUME_HISTORY_EPOCH_MISMATCH = (
    "checkpoint epoch does not match epoch_metrics.csv history"
)
_RESUME_VALIDATION_HISTORY_REQUIRED = (
    "resume history must include validation rows"
)
_RESUME_CHECKPOINT_MISSING = "resume checkpoint does not exist: {path}"
_RESUME_CHECKPOINT_MAPPING_REQUIRED = "resume checkpoint must be a mapping"
_RESUME_MODEL_STATE_MAPPING_REQUIRED = (
    "resume checkpoint model_state_dict must be a mapping"
)
_RESUME_OPTIMIZER_STATE_MAPPING_REQUIRED = (
    "resume checkpoint optimizer_state_dict must be a mapping"
)
_RESUME_EPOCH_INVALID = "resume checkpoint epoch must be a positive integer"
_RESUME_METRICS_MISSING = "resume metrics do not exist: {path}"
_RESUME_METRICS_HEADER_INCOMPATIBLE = (
    "epoch_metrics.csv has an incompatible header"
)
_RESUME_METRICS_EMPTY = "epoch_metrics.csv must include at least one epoch"
_RESUME_BEST_CHECKPOINT_MISSING = "resume best checkpoint does not exist: {path}"
_OPERATING_POINT_MISSING = "operating point not found: {path}"
_OPERATING_POINT_OBJECT_REQUIRED = "operating point must be a JSON object"
_OPERATING_POINT_GEOMETRY_REQUIRED = "operating point must include geometry"
_DEGRADATION_HASH_MISMATCH = (
    "train_dataset_config and val_dataset_config degradation hashes must match: "
    "train={train_hash}; val={val_hash}"
)
_SPLIT_ROW_MISSING = "no {split} row available"
_PHASE_MASK_UNAVAILABLE = "phase mask is not available"
_GRADIENT_ACCUMULATION_MAPPING_REQUIRED = (
    "checkpoint gradient_accumulation must be a mapping"
)
_PENDING_GRADIENT_SAMPLES_INVALID = (
    "checkpoint pending gradient samples are invalid"
)
_PARAMETER_GRADIENTS_MAPPING_REQUIRED = (
    "checkpoint parameter_gradients must be a mapping"
)
_UNKNOWN_GRADIENT_PARAMETERS = (
    "checkpoint gradients reference unknown parameters: {parameter_names}"
)
_PARAMETER_GRADIENTS_TENSOR_REQUIRED = (
    "checkpoint parameter gradients must be tensors"
)
_PENDING_GRADIENTS_REQUIRED = (
    "pending gradient samples require parameter gradients"
)


def run_training(
    config: TrainingConfig,
    *,
    artifact_paths: Mapping[str, Path] | None = None,
    is_resume: bool = False,
) -> dict[str, object]:
    """
    杩愯璁粌浜х墿
    """
    normalized_config = _normalize_config(config)
    _set_random_seed(normalized_config.basic.seed)

    backend_config = getattr(normalized_config, "backend", None)
    if artifact_paths is None:
        paths = dict(
            build_training_paths(
                normalized_config.basic,
                model_role=normalized_config.model_role,
                backend=backend_config,
            )
        )
    else:
        paths = {name: Path(path) for name, path in artifact_paths.items()}
    paths["run_dir"].mkdir(parents=True, exist_ok=True)
    paths["figures_dir"].mkdir(parents=True, exist_ok=True)
    paths["checkpoints_dir"].mkdir(parents=True, exist_ok=True)
    paths["phase_masks_dir"].mkdir(parents=True, exist_ok=True)

    if not is_resume:
        write_json(paths["config_json"], normalized_config)
        write_runtime(paths["runtime_json"])

    operating_point = _load_operating_point(normalized_config.operating_point_path)
    geometry = _geometry_from_operating_point(operating_point)
    geometry_hash = compute_config_hash(geometry)
    degradation_hash = _degradation_hash_for_training_config(normalized_config)
    write_json(paths["operating_point_used_json"], operating_point)

    checks = [
        _check(
            "geometry_hash_matches",
            "PASS" if geometry_hash == operating_point.get("geometry_hash") else "FAIL",
            expected=operating_point.get("geometry_hash"),
            actual=geometry_hash,
        )
    ]
    if checks[-1]["status"] == "FAIL":
        final_metrics = _sanitize_metrics(
            {
                "failure_reason": "geometry_hash_mismatch",
                "operating_point_hash": operating_point.get("geometry_hash"),
                "computed_geometry_hash": geometry_hash,
            }
        )
        status = "FAIL"
        write_json(paths["final_metrics_json"], final_metrics)
        write_json(paths["checks_json"], checks)
        _write_summary(paths["summary_md"], normalized_config, status, checks, final_metrics)
        return {
            "status": status,
            "paths": paths,
            "checks": checks,
            "history": [],
            "final_metrics": final_metrics,
        }

    device = _resolve_device(normalized_config.basic.device)
    defocus_operator = defocus_operator_for_dataset(normalized_config.train_dataset_config)
    model = assemble_model(
        model_role=normalized_config.model_role,
        bench_config=geometry,
        phase_parameterization=normalized_config.phase_parameterization,
        phase_initialization=normalized_config.phase_initialization,
        trainable_parameters=normalized_config.trainable_parameters,
        backend=normalized_config.backend,
        connection_config=normalized_config.connection,
        defocus_operator=defocus_operator,
    ).to(device)
    load_frontend_source_if_needed(
        model,
        normalized_config,
        geometry_hash=geometry_hash,
        target_degradation_hash=degradation_hash,
    )
    inject_live_reference_arm(model)
    initial_phase_mask = _initial_phase_mask_for_model(model)
    trainable_names = _trainable_parameter_names(model, normalized_config)
    expected_trainable_names = list(normalized_config.trainable_parameters)
    checks.append(
        _check(
            "trainable_parameters_exact",
            "PASS" if trainable_names == expected_trainable_names else "FAIL",
            expected=expected_trainable_names,
            actual=trainable_names,
        )
    )

    train_loader = build_restoration_loader(
        normalized_config.train_dataset_config,
        normalized_config.batch_size,
        is_shuffle_enabled=True,
    )
    val_loader = build_restoration_loader(
        normalized_config.val_dataset_config,
        normalized_config.batch_size,
        is_shuffle_enabled=False,
    )
    checks.append(_check("train_loader_available", "PASS", batches=len(train_loader)))
    checks.append(_check("val_loader_available", "PASS", batches=len(val_loader)))

    example_input = _model_stats_example_input(val_loader, normalized_config, device)
    model_parameter_count = count_trainable_parameters(model)
    # 鎬绘垚鏈?= Conv2d MACs + 鍚勬ā鍧?.spectral_macs() 涔嬪拰;NAFNet 鏃犺氨椤?鈫?鏁板€间笌 conv-only 鐩稿悓
    model_conv2d_macs = count_model_macs(model, example_input)

    optimizer = _build_optimizer(model, normalized_config)
    gradient_accumulation = GradientAccumulationState()

    history_rows: list[dict[str, object]] = []
    best_val_loss = math.inf
    best_val_psnr = -math.inf
    best_val_ssim = -math.inf
    best_epoch = 0
    best_row: dict[str, object] | None = None
    start_epoch = 1
    optimizer_updates = 0
    if is_resume and paths["last_checkpoint"].is_file():
        resumed_epoch, gradient_accumulation = _restore_training_state(
            paths["last_checkpoint"],
            model=model,
            optimizer=optimizer,
            config=normalized_config,
            geometry_hash=geometry_hash,
            degradation_hash=degradation_hash,
            device=device,
        )
        history_rows = _committed_training_epoch_metrics(
            paths["epoch_metrics_csv"],
            checkpoint_epoch=resumed_epoch,
        )
        validation_rows = [
            row for row in history_rows if row.get("split") == "val"
        ]
        if not validation_rows:
            raise ValueError(_RESUME_VALIDATION_HISTORY_REQUIRED)
        best_row = max(
            validation_rows,
            key=lambda row: (
                float(row["psnr_normalized"]),
                float(row["ssim_normalized"]),
            ),
        )
        best_val_loss = float(best_row["loss_total"])
        best_val_psnr = float(best_row["psnr_normalized"])
        best_val_ssim = float(best_row["ssim_normalized"])
        best_epoch = int(best_row["epoch"])
        optimizer_updates = int(
            _last_row(history_rows, "train")["optimizer_updates"]
        )
        if best_epoch == resumed_epoch:
            save_checkpoint(
                paths["best_checkpoint"],
                model,
                optimizer,
                normalized_config,
                epoch=best_epoch,
                geometry_hash=geometry_hash,
                degradation_hash=degradation_hash,
                metrics=best_row,
                gradient_accumulation=_gradient_accumulation_payload(
                    model,
                    gradient_accumulation,
                ),
            )
        elif not paths["best_checkpoint"].is_file():
            message = _RESUME_BEST_CHECKPOINT_MISSING.format(
                path=paths["best_checkpoint"]
            )
            raise FileNotFoundError(message)
        start_epoch = resumed_epoch + 1
        checks.append(
            _check("training_resumed", "PASS", resumed_epoch=resumed_epoch)
        )
    elif is_resume:
        paths["epoch_metrics_csv"].unlink(missing_ok=True)
        paths["best_checkpoint"].unlink(missing_ok=True)
        checks.append(
            _check(
                "training_restarted",
                "PASS",
                reason="no committed last checkpoint",
            )
        )

    epoch = start_epoch - 1
    while (
        epoch < normalized_config.epochs
        if normalized_config.max_optimizer_updates is None
        else optimizer_updates < normalized_config.max_optimizer_updates
    ):
        epoch += 1
        updates_before_epoch = optimizer_updates
        train_row = run_epoch(
            model,
            train_loader,
            normalized_config,
            device,
            epoch=epoch,
            split="train",
            optimizer=optimizer,
            operating_point_hash=str(operating_point.get("geometry_hash", "")),
            optimizer_update_start=optimizer_updates,
            optimizer_update_limit=normalized_config.max_optimizer_updates,
            gradient_accumulation=gradient_accumulation,
        )
        optimizer_updates = int(train_row["optimizer_updates"])
        val_row = run_epoch(
            model,
            val_loader,
            normalized_config,
            device,
            epoch=epoch,
            split="val",
            optimizer=None,
            operating_point_hash=str(operating_point.get("geometry_hash", "")),
            optimizer_update_start=optimizer_updates,
        )
        train_output_row = _sanitize_metrics(train_row)
        val_output_row = _sanitize_metrics(val_row)
        append_training_epoch_metrics(
            paths["epoch_metrics_csv"],
            [train_output_row, val_output_row],
        )
        history_rows.extend([train_output_row, val_output_row])

        val_loss = float(val_row["loss_total"])
        save_checkpoint(
            paths["last_checkpoint"],
            model,
            optimizer,
            normalized_config,
            epoch=epoch,
            geometry_hash=geometry_hash,
            degradation_hash=degradation_hash,
            metrics=val_row,
            gradient_accumulation=_gradient_accumulation_payload(
                model,
                gradient_accumulation,
            ),
        )
        val_psnr = float(val_row["psnr_normalized"])
        val_ssim = float(val_row["ssim_normalized"])
        if val_psnr > best_val_psnr or (
            val_psnr == best_val_psnr and val_ssim > best_val_ssim
        ):
            best_val_loss = val_loss
            best_val_psnr = val_psnr
            best_val_ssim = val_ssim
            best_epoch = epoch
            best_row = val_row
            save_checkpoint(
                paths["best_checkpoint"],
                model,
                optimizer,
                normalized_config,
                epoch=epoch,
                geometry_hash=geometry_hash,
                degradation_hash=degradation_hash,
                metrics=val_row,
                gradient_accumulation=_gradient_accumulation_payload(
                    model,
                    gradient_accumulation,
                ),
            )
        if optimizer_updates == updates_before_epoch:
            raise invalid_restoration_contract(
                "training loader cannot form one effective batch; lower "
                "batch_size or effective_batch_size"
            )

    final_train_row = _last_row(history_rows, "train")
    final_val_row = _last_row(history_rows, "val")
    if best_row is None:
        best_row = final_val_row
        best_val_loss = float(best_row["loss_total"])
        best_val_psnr = float(best_row["psnr_normalized"])
        best_val_ssim = float(best_row["ssim_normalized"])
        best_epoch = int(best_row["epoch"])

    save_checkpoint(
        paths["last_checkpoint"],
        model,
        optimizer,
        normalized_config,
        epoch=epoch,
        geometry_hash=geometry_hash,
        degradation_hash=degradation_hash,
        metrics=final_val_row,
        gradient_accumulation=_gradient_accumulation_payload(
            model,
            gradient_accumulation,
        ),
    )

    baseline_metrics_values = baseline_metrics(model, val_loader, normalized_config, device)
    defocus_operator_provenance_hash = (
        defocus_operator.provenance_hash() if defocus_operator is not None else None
    )
    reference_phase_offset = _reference_phase_offset_provenance(model, normalized_config)
    final_metrics = _sanitize_metrics({
        "best_val_loss": best_val_loss,
        "best_epoch": best_epoch,
        "best_val_ssim": float(best_row["ssim_normalized"]),
        "best_val_psnr": float(best_row["psnr_normalized"]),
        "optimizer_updates": optimizer_updates,
        "effective_batch_size": (
            normalized_config.effective_batch_size or normalized_config.batch_size
        ),
        "device_micro_batch_size": normalized_config.batch_size,
        "final_train_loss": float(final_train_row["loss_total"]),
        "final_val_loss": float(final_val_row["loss_total"]),
        "final_train_ssim": float(final_train_row["ssim_normalized"]),
        "final_val_ssim": float(final_val_row["ssim_normalized"]),
        "final_train_psnr": float(final_train_row["psnr_normalized"]),
        "final_val_psnr": float(final_val_row["psnr_normalized"]),
        "phase_mask_stats": _phase_mask_stats(model),
        "mechanism_parameters": _mechanism_parameter_stats(model),
        "best_optical_residual_gate": best_row.get(
            "optical_residual_gate"
        ),
        "final_optical_residual_gate": final_val_row.get(
            "optical_residual_gate"
        ),
        "model_role": normalized_config.model_role,
        "backend": backend_config,
        "defocus_operator_provenance_hash": defocus_operator_provenance_hash,
        "reference_phase_offset": reference_phase_offset,
        "model_parameter_count": model_parameter_count,
        "model_conv2d_macs": model_conv2d_macs,
        "operating_point_path": str(Path(normalized_config.operating_point_path)),
        "operating_point_hash": operating_point.get("geometry_hash"),
        **baseline_metrics_values,
    })

    figure_check = _write_training_diagnostic_figures(
        model,
        val_loader,
        normalized_config,
        device,
        paths["figures_dir"],
        history_rows,
        initial_phase_mask,
        final_metrics,
        operating_point,
    )
    checks.append(figure_check)
    checks.append(
        _check(
            "finite_final_loss",
            "PASS" if _is_finite_number(final_metrics["final_val_loss"]) else "FAIL",
        )
    )
    checks.append(
        _check(
            "checkpoints_written",
            (
                "PASS"
                if paths["best_checkpoint"].exists()
                and paths["last_checkpoint"].exists()
                else "FAIL"
            ),
            best=str(paths["best_checkpoint"]),
            last=str(paths["last_checkpoint"]),
        )
    )

    status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    write_json(paths["final_metrics_json"], final_metrics)
    write_json(paths["checks_json"], checks)
    _write_summary(paths["summary_md"], normalized_config, status, checks, final_metrics)
    return {
        "status": status,
        "paths": paths,
        "checks": checks,
        "history": history_rows,
        "final_metrics": final_metrics,
    }


def _normalize_config(config: TrainingConfig) -> TrainingConfig:
    config.validate()
    normalized_basic = config.basic.normalized()
    normalized_config = replace(
        config,
        basic=normalized_basic,
        operating_point_path=Path(config.operating_point_path),
    )
    normalized_config.validate()
    return normalized_config


def _build_optimizer(
    model: torch.nn.Module,
    config: TrainingConfig,
) -> torch.optim.Optimizer:
    """
    鏋勫缓鏄惧紡鍖哄垎鑱斿悎鍓嶇瀛︿範鐜囩殑 Adam 鍙傛暟缁?    """
    trainable_parameters = [
        parameter for parameter in model.parameters() if parameter.requires_grad
    ]
    parameter_groups: object = trainable_parameters
    if config.model_role == "joint_optical_frontend_digital_backend":
        frontend = getattr(model, "frontend", None)
        if frontend is None:
            raise invalid_restoration_contract(
                "joint training model must expose frontend parameters"
            )
        frontend_parameters = [
            parameter for parameter in frontend.parameters() if parameter.requires_grad
        ]
        frontend_ids = {id(parameter) for parameter in frontend_parameters}
        backend_parameters = [
            parameter
            for parameter in trainable_parameters
            if id(parameter) not in frontend_ids
        ]
        parameter_groups = [
            {
                "params": frontend_parameters,
                "lr": config.learning_rate * config.frontend_to_backend_lr_ratio,
            },
            {"params": backend_parameters, "lr": config.learning_rate},
        ]
    return torch.optim.Adam(
        parameter_groups,  # type: ignore[arg-type]
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )


def _set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _restore_training_state(
    checkpoint_path: Path,
    *,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    config: TrainingConfig,
    geometry_hash: str,
    degradation_hash: str,
    device: torch.device,
) -> tuple[int, GradientAccumulationState]:
    if not checkpoint_path.is_file():
        message = _RESUME_CHECKPOINT_MISSING.format(path=checkpoint_path)
        raise FileNotFoundError(message)
    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=True,
    )
    if not isinstance(checkpoint, Mapping):
        raise ValueError(_RESUME_CHECKPOINT_MAPPING_REQUIRED)
    verify_provenance(
        checkpoint,
        {
            "config_hash": compute_config_hash(config),
            "geometry_hash": geometry_hash,
            "degradation_hash": degradation_hash,
            "model_role": config.model_role,
            "backend": backend_payload(config.backend),
        },
        fields=(
            "config_hash",
            "geometry_hash",
            "degradation_hash",
            "model_role",
            "backend",
        ),
        context=f"resume checkpoint {checkpoint_path}",
    )
    model_state = checkpoint.get("model_state_dict")
    optimizer_state = checkpoint.get("optimizer_state_dict")
    epoch = checkpoint.get("epoch")
    if not isinstance(model_state, Mapping):
        raise ValueError(_RESUME_MODEL_STATE_MAPPING_REQUIRED)
    if not isinstance(optimizer_state, Mapping):
        raise ValueError(_RESUME_OPTIMIZER_STATE_MAPPING_REQUIRED)
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch <= 0:
        raise ValueError(_RESUME_EPOCH_INVALID)
    model.load_state_dict(model_state)
    optimizer.load_state_dict(optimizer_state)
    gradient_accumulation = _restore_gradient_accumulation(
        checkpoint.get("gradient_accumulation"),
        model=model,
        effective_batch_size=config.effective_batch_size,
    )
    restore_rng_state(checkpoint.get("rng_state"))
    return epoch, gradient_accumulation


def _gradient_accumulation_payload(
    model: nn.Module,
    state: GradientAccumulationState,
) -> dict[str, object]:
    return {
        "pending_samples": state.pending_samples,
        "parameter_gradients": {
            name: parameter.grad.detach().cpu()
            for name, parameter in model.named_parameters()
            if parameter.grad is not None
        },
    }


def _restore_gradient_accumulation(
    payload: object,
    *,
    model: nn.Module,
    effective_batch_size: int | None,
) -> GradientAccumulationState:
    if not payload:
        return GradientAccumulationState()
    if not isinstance(payload, Mapping):
        raise ValueError(_GRADIENT_ACCUMULATION_MAPPING_REQUIRED)
    pending_samples = payload.get("pending_samples")
    parameter_gradients = payload.get("parameter_gradients")
    if (
        not isinstance(pending_samples, int)
        or isinstance(pending_samples, bool)
        or pending_samples < 0
        or (
            effective_batch_size is not None
            and pending_samples >= effective_batch_size
        )
    ):
        raise ValueError(_PENDING_GRADIENT_SAMPLES_INVALID)
    if not isinstance(parameter_gradients, Mapping):
        raise ValueError(_PARAMETER_GRADIENTS_MAPPING_REQUIRED)
    named_parameters = dict(model.named_parameters())
    unknown_names = set(parameter_gradients).difference(named_parameters)
    if unknown_names:
        raise ValueError(
            _UNKNOWN_GRADIENT_PARAMETERS.format(
                parameter_names=sorted(unknown_names)
            )
        )
    for name, gradient in parameter_gradients.items():
        if not isinstance(gradient, torch.Tensor):
            raise ValueError(_PARAMETER_GRADIENTS_TENSOR_REQUIRED)
        parameter = named_parameters[name]
        parameter.grad = gradient.to(
            device=parameter.device,
            dtype=parameter.dtype,
        )
    if pending_samples and not parameter_gradients:
        raise ValueError(_PENDING_GRADIENTS_REQUIRED)
    return GradientAccumulationState(pending_samples=pending_samples)


def _read_training_epoch_metrics(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        message = _RESUME_METRICS_MISSING.format(path=path)
        raise FileNotFoundError(message)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        if header != TRAINING_EPOCH_FIELDS:
            raise ValueError(_RESUME_METRICS_HEADER_INCOMPATIBLE)
        rows = [_parse_training_epoch_row(row) for row in reader]
    if not rows:
        raise ValueError(_RESUME_METRICS_EMPTY)
    return rows


def _committed_training_epoch_metrics(
    path: Path,
    *,
    checkpoint_epoch: int,
) -> list[dict[str, object]]:
    history_rows = _read_training_epoch_metrics(path)
    committed_rows = [
        row for row in history_rows if int(row["epoch"]) <= checkpoint_epoch
    ]
    if not committed_rows:
        raise ValueError(_RESUME_HISTORY_EPOCH_MISMATCH)
    history_epoch = max(int(row["epoch"]) for row in committed_rows)
    if history_epoch != checkpoint_epoch:
        raise ValueError(_RESUME_HISTORY_EPOCH_MISMATCH)
    for epoch in range(1, checkpoint_epoch + 1):
        epoch_splits = [
            str(row["split"])
            for row in committed_rows
            if int(row["epoch"]) == epoch
        ]
        if sorted(epoch_splits) != ["train", "val"]:
            raise ValueError(_RESUME_HISTORY_EPOCH_MISMATCH)
    if len(committed_rows) != len(history_rows):
        serialized_rows = [
            {**row, "epoch": float(row["epoch"])} for row in committed_rows
        ]
        write_training_epoch_metrics(path, serialized_rows)
    return committed_rows


def _parse_training_epoch_row(row: Mapping[str, str]) -> dict[str, object]:
    text_fields = {"split", "operating_point_hash", "status"}
    optional_float_fields = {
        "phase_offset_reference",
        "optical_residual_gate",
    }
    parsed: dict[str, object] = {}
    for field_name in TRAINING_EPOCH_FIELDS:
        value = row.get(field_name, "")
        if field_name == "epoch":
            parsed[field_name] = int(float(value))
        elif field_name in text_fields:
            parsed[field_name] = value
        elif field_name in optional_float_fields and value == "":
            parsed[field_name] = None
        else:
            parsed[field_name] = float(value)
    return parsed


def _resolve_device(requested: str) -> torch.device:
    if requested == "cuda":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "auto" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _check(name: str, status: str = "PASS", **details: object) -> dict[str, object]:
    return {"name": name, "status": status, "details": details}


def _load_operating_point(path: Path | str) -> dict[str, object]:
    operating_point_path = Path(path)
    if not operating_point_path.exists():
        message = _OPERATING_POINT_MISSING.format(path=operating_point_path)
        raise FileNotFoundError(message)
    payload = json.loads(operating_point_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(_OPERATING_POINT_OBJECT_REQUIRED)
    return payload


def _geometry_from_operating_point(
    payload: Mapping[str, object],
) -> OpticalBenchConfig:
    geometry_payload = payload.get("geometry")
    if not isinstance(geometry_payload, Mapping):
        raise ValueError(_OPERATING_POINT_GEOMETRY_REQUIRED)
    geometry_kwargs = {
        str(key): tuple(value) if key in _RESOLUTION_FIELDS and isinstance(value, list) else value
        for key, value in geometry_payload.items()
    }
    geometry = OpticalBenchConfig(**geometry_kwargs)
    geometry.validate()
    return geometry


def _degradation_hash_for_training_config(config: TrainingConfig) -> str:
    train_hash = _degradation_hash_for_dataset_config(config.train_dataset_config)
    if config.val_dataset_config is None:
        return train_hash
    val_hash = _degradation_hash_for_dataset_config(config.val_dataset_config)
    if train_hash != val_hash:
        message = _DEGRADATION_HASH_MISMATCH.format(
            train_hash=train_hash,
            val_hash=val_hash,
        )
        raise ValueError(message)
    return train_hash


def _degradation_hash_for_dataset_config(dataset_config: object) -> str:
    try:
        return degradation_hash_for_dataset_config(dataset_config)
    except ValueError:
        if (
            isinstance(dataset_config, Mapping)
            and "dataset_config" in dataset_config
        ):
            raise
        return compute_config_hash(dataset_config)


def _model_stats_example_input(
    loader: DataLoader,
    config: TrainingConfig,
    device: torch.device,
) -> torch.Tensor:
    first_batch = next(iter(loader))
    if config.model_role == "backend_only":
        return degraded_image_from_batch(first_batch).to(
            device=device,
            dtype=torch.float32,
        )[:1]
    input_field = ensure_batched_field(first_batch["input_field"])
    if torch.is_complex(input_field):
        return input_field.to(device)[:1]
    return input_field.to(device=device, dtype=torch.complex64)[:1]


def _last_row(rows: list[dict[str, object]], split: str) -> dict[str, object]:
    for row in reversed(rows):
        if row["split"] == split:
            return row
    message = _SPLIT_ROW_MISSING.format(split=split)
    raise ValueError(message)


def _write_training_diagnostic_figures(
    model: nn.Module,
    val_loader: DataLoader,
    config: TrainingConfig,
    device: torch.device,
    figures_dir: Path,
    history_rows: list[dict[str, object]],
    initial_phase_mask: torch.Tensor | None,
    final_metrics: Mapping[str, object],
    operating_point: Mapping[str, object],
) -> dict[str, object]:
    if config.model_role == "backend_only":
        return _check(
            "figures_written",
            "PASS",
            figures_dir=str(figures_dir),
            skipped="backend_only",
        )
    if initial_phase_mask is None:
        return _check(
            "figures_written",
            "FAIL",
            figures_dir=str(figures_dir),
            error=_PHASE_MASK_UNAVAILABLE,
        )
    error: str | None = None
    try:
        examples = _collect_restoration_examples(model, val_loader, config, device)
        final_phase_mask = _effective_phase_for_model(model)
        if final_phase_mask is None:
            raise ValueError(_PHASE_MASK_UNAVAILABLE)
        final_phase_mask = final_phase_mask.detach().cpu()
        visualize_training_dynamics(history_rows, figures_dir)
        visualize_restoration_examples(examples, figures_dir)
        visualize_phase_mask_evolution(initial_phase_mask, final_phase_mask, figures_dir)
        visualize_frequency_response_comparison(final_metrics, figures_dir)
        visualize_operating_point_trace(operating_point, figures_dir)
    except Exception as exc:  # pragma: no cover - details are surfaced in checks.
        error = f"{type(exc).__name__}: {exc}"

    missing = [
        figure_name
        for figure_name in _REQUIRED_TRAINING_FIGURES
        if not (figures_dir / figure_name).exists()
    ]
    details: dict[str, object] = {
        "figures_dir": str(figures_dir),
        "required": list(_REQUIRED_TRAINING_FIGURES),
        "missing": missing,
    }
    if error is not None:
        details["error"] = error
    status = "PASS" if error is None and not missing else "FAIL"
    return _check("figures_written", status, **details)


def _collect_restoration_examples(
    frontend: nn.Module,
    val_loader: DataLoader,
    config: TrainingConfig,
    device: torch.device,
) -> dict[str, torch.Tensor]:
    frontend.eval()
    first_batch = next(iter(val_loader))
    with torch.no_grad():
        sample_field = ensure_batched_field(first_batch["input_field"])
        if torch.is_complex(sample_field):
            sample_field = sample_field.to(device)
        else:
            sample_field = sample_field.to(device=device, dtype=torch.complex64)
        sample_field = sample_field[:1]
        sample_target = target_from_batch(first_batch)[:1].to(
            device=device,
            dtype=torch.float32,
        )
        phase_zero = frontend.phase_zero_baselines(sample_field)["image_full_frontend_phase_zero"]
        restored = normalize_intensity(
            frontend(sample_field),
            policy=config.intensity_normalization_policy,
            scale=1.0,
        )
        degraded_image = degraded_from_batch(first_batch)[:1].to(
            device=device,
            dtype=torch.float32,
        )
        return {
            "clean": normalize_intensity(
                sample_target,
                policy=config.intensity_normalization_policy,
                scale=1.0,
            ),
            "degraded": normalize_intensity(
                degraded_image,
                policy=config.intensity_normalization_policy,
                scale=1.0,
            ),
            "phase_zero": normalize_intensity(
                phase_zero,
                policy=config.intensity_normalization_policy,
                scale=1.0,
            ),
            "restored": restored,
        }


def _sanitize_metrics(value: object) -> object:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, Real):
        numeric_value = float(value)
        if math.isnan(numeric_value):
            return "nan"
        if numeric_value == math.inf:
            return "inf"
        if numeric_value == -math.inf:
            return "-inf"
        return numeric_value
    if isinstance(value, Mapping):
        return {str(key): _sanitize_metrics(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_sanitize_metrics(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return _sanitize_metrics(asdict(value))
    return value


def _is_finite_number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))


def _write_summary(
    path: Path,
    config: TrainingConfig,
    status: str,
    checks: list[dict[str, object]],
    final_metrics: Mapping[str, object],
) -> Path:
    pass_count = sum(1 for check in checks if check["status"] == "PASS")
    text = (
        "# Restoration Training\n\n"
        f"- Run name: {config.basic.run_name}\n"
        f"- Status: {status}\n"
        f"- Best epoch: {final_metrics.get('best_epoch', 'n/a')}\n"
        f"- Best validation loss: {final_metrics.get('best_val_loss', 'n/a')}\n"
        f"- Checks passed: {pass_count}/{len(checks)}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import random
from uuid import uuid4

import numpy as np
import torch
from torch import nn

from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
from experiments.restoration.fixed_measurement.learning.config import TrainingConfig
from experiments.restoration.fixed_measurement.learning.connection import ConnectionConfig
from experiments.restoration.fixed_measurement.learning.model_assembly import (
    _frontend_for_model,
    _mechanism_parameter_stats,
)


_FIELD_MISSING = "{field_name} missing{context_suffix}"
_FIELD_MISMATCH = (
    "{field_name} mismatch: expected {expected_value}; "
    "got {actual_value}{context_suffix}"
)
_VALUE_MISMATCH = (
    "{label} mismatch: expected {left_value}; got {right_value}{context_suffix}"
)
_RETIRED_BACKEND_IDENTITY = (
    "retired flat backend identity found in {context}; this checkpoint is "
    "outside the sealed Fixed protocol"
)
_RNG_MAPPING_REQUIRED = "checkpoint rng_state must be a mapping"
_PYTHON_RNG_INVALID = "checkpoint Python RNG state is invalid"
_NUMPY_RNG_INVALID = "checkpoint NumPy RNG state is invalid"
_NUMPY_RNG_TENSOR_INVALID = "checkpoint NumPy RNG tensor is invalid"
_TORCH_RNG_INVALID = "checkpoint Torch RNG state is invalid"
_CUDA_RNG_INVALID = "checkpoint CUDA RNG state is invalid"
_FRONTEND_SOURCE_REQUIRED = "frontend_source is required for hybrid training"
_FRONTEND_CHECKPOINT_MISSING = "frontend source checkpoint not found: {path}"
_FRONTEND_CHECKPOINT_MAPPING_REQUIRED = (
    "frontend source checkpoint must be a mapping"
)
_FRONTEND_STATE_MAPPING_REQUIRED = (
    "frontend source checkpoint model_state_dict must be a mapping"
)


def verify_provenance(
    checkpoint: Mapping[str, object],
    expected: Mapping[str, object],
    *,
    fields: Sequence[str],
    cross_equality: Sequence[tuple[str, object, object]] = (),
    context: str | None = None,
) -> None:
    """
    鏍￠獙妫€鏌ョ偣鏉ユ簮瀛楁
    """
    context_suffix = "" if context is None else f" for {context}"
    for field_name in fields:
        if field_name not in checkpoint:
            message = _FIELD_MISSING.format(
                field_name=field_name,
                context_suffix=context_suffix,
            )
            raise ValueError(message)
        expected_value = _normalized_provenance_value(
            field_name,
            expected.get(field_name),
        )
        actual_value = _normalized_provenance_value(
            field_name,
            checkpoint[field_name],
        )
        if actual_value != expected_value:
            message = _FIELD_MISMATCH.format(
                field_name=field_name,
                expected_value=expected_value,
                actual_value=actual_value,
                context_suffix=context_suffix,
            )
            raise ValueError(message)
    for label, left_value, right_value in cross_equality:
        if left_value != right_value:
            message = _VALUE_MISMATCH.format(
                label=label,
                left_value=left_value,
                right_value=right_value,
                context_suffix=context_suffix,
            )
            raise ValueError(message)


def _normalized_provenance_value(field_name: str, value: object) -> object:
    if not isinstance(value, Mapping):
        return value
    normalized = dict(value)
    if field_name == "backend" and normalized.get("trainable_passthrough_gain") is False:
        normalized.pop("trainable_passthrough_gain")
    if field_name == "connection" and normalized.get("mode") != "optical_residual_gate":
        normalized.pop("scalar_gate_initial_logit", None)
        normalized.pop("optical_residual_gate_logit", None)
    return normalized


def connection_payload(connection: ConnectionConfig) -> dict[str, object]:
    """
    杩斿洖杩炴帴閰嶇疆鏉ユ簮杞借嵎
    """
    if connection.mode == "optical_residual_gate":
        initial_gate = connection.initial_optical_residual_gate
        return {
            "mode": connection.mode,
            "initial_optical_residual_gate": initial_gate,
        }
    return {
        "mode": connection.mode,
    }


def backend_payload(backend: BackendConfig | None) -> dict[str, object] | None:
    """
    杩斿洖鏁板瓧鍚庣鏉ユ簮杞借嵎
    """
    if backend is None:
        return None
    return {
        "family": backend.family,
        "model_name": backend.model_name,
        "residual_learning": backend.residual_learning,
    }


def _require_nested_backend(checkpoint: Mapping[str, object], context: str) -> None:
    if "backend_family" in checkpoint or "backend_model" in checkpoint:
        message = _RETIRED_BACKEND_IDENTITY.format(context=context)
        raise ValueError(message)


def save_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    config: TrainingConfig,
    *,
    epoch: int,
    geometry_hash: str,
    degradation_hash: str,
    metrics: Mapping[str, object],
    gradient_accumulation: Mapping[str, object] | None = None,
) -> None:
    """
    淇濆瓨澶嶅師璁粌妫€鏌ョ偣
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    backend_config = getattr(config, "backend", None)
    train_dataset_config = config.train_dataset_config
    profile_name = None
    if isinstance(train_dataset_config, Mapping):
        profile_name = train_dataset_config.get("profile_name")
    payload = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "config_hash": compute_config_hash(config),
        "geometry_hash": geometry_hash,
        "degradation_hash": degradation_hash,
        "model_role": config.model_role,
        "seed": config.basic.seed,
        "profile_name": profile_name,
        "run_name": config.basic.run_name,
        "backend": backend_payload(backend_config),
        "phase_parameterization": config.phase_parameterization,
        "phase_initialization": config.phase_initialization,
        "connection": connection_payload(config.connection),
        "mechanism_parameters": _mechanism_parameter_stats(model),
        "metrics": dict(metrics),
        "rng_state": capture_rng_state(),
        "gradient_accumulation": dict(gradient_accumulation or {}),
    }
    temporary_path = path.with_name(f"._{uuid4().hex[:12]}.tmp")
    try:
        torch.save(payload, temporary_path)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def capture_rng_state() -> dict[str, object]:
    """
    鎹曡幏澶嶅師璁粌闅忔満鐘舵€?    """
    numpy_kind, numpy_state, numpy_position, has_gaussian, cached_gaussian = (
        np.random.get_state()
    )
    return {
        "python": random.getstate(),
        "numpy": {
            "kind": numpy_kind,
            "state": torch.from_numpy(numpy_state.copy()),
            "position": int(numpy_position),
            "has_gaussian": int(has_gaussian),
            "cached_gaussian": float(cached_gaussian),
        },
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def restore_rng_state(payload: object) -> None:
    """
    鎭㈠澶嶅師璁粌闅忔満鐘舵€?    """
    if not isinstance(payload, Mapping):
        raise ValueError(_RNG_MAPPING_REQUIRED)
    python_state = payload.get("python")
    numpy_payload = payload.get("numpy")
    torch_cpu_state = payload.get("torch_cpu")
    torch_cuda_state = payload.get("torch_cuda")
    if not isinstance(python_state, tuple):
        raise ValueError(_PYTHON_RNG_INVALID)
    if not isinstance(numpy_payload, Mapping):
        raise ValueError(_NUMPY_RNG_INVALID)
    numpy_state = numpy_payload.get("state")
    if not isinstance(numpy_state, torch.Tensor):
        raise ValueError(_NUMPY_RNG_TENSOR_INVALID)
    if not isinstance(torch_cpu_state, torch.Tensor):
        raise ValueError(_TORCH_RNG_INVALID)

    random.setstate(python_state)
    np.random.set_state(
        (
            str(numpy_payload["kind"]),
            numpy_state.cpu().numpy().astype(np.uint32, copy=False),
            int(numpy_payload["position"]),
            int(numpy_payload["has_gaussian"]),
            float(numpy_payload["cached_gaussian"]),
        )
    )
    torch.set_rng_state(torch_cpu_state.cpu())
    if torch.cuda.is_available():
        if not isinstance(torch_cuda_state, list) or not all(
            isinstance(state, torch.Tensor) and state.dtype == torch.uint8
            for state in torch_cuda_state
        ):
            raise ValueError(_CUDA_RNG_INVALID)
        # 璁粌鍏ュ彛閫氳繃 ``map_location=device`` 鎭㈠妫€鏌ョ偣锛屼絾 PyTorch 浠嶈姹?        # CUDA 鐢熸垚鍣ㄧ姸鎬佷负 CPU 瀛楄妭寮犻噺锛屼笌 ``torch.cuda.get_rng_state_all``
        # 杩斿洖鍊间繚鎸佷竴鑷达紝鍥犳浜よ繕鐢熸垚鍣ㄥ墠鍏堣鑼冨寲宸蹭繚瀛樼殑寮犻噺
        canonical_cuda_state = [
            state.detach().cpu().contiguous() for state in torch_cuda_state
        ]
        torch.cuda.set_rng_state_all(canonical_cuda_state)


def load_frontend_source_if_needed(
    model: nn.Module,
    config: TrainingConfig,
    *,
    geometry_hash: str,
    target_degradation_hash: str,
) -> None:
    """
    鎸夐渶鍔犺浇鍏夊鍓嶇鏉ユ簮妫€鏌ョ偣
    """
    if config.model_role not in {
        "frozen_optical_frontend_digital_backend",
        "joint_optical_frontend_digital_backend",
    }:
        return
    source = config.frontend_source
    if source is None:
        raise ValueError(_FRONTEND_SOURCE_REQUIRED)
    source.validate()
    checkpoint_path = Path(source.checkpoint_path)
    if not checkpoint_path.exists():
        message = _FRONTEND_CHECKPOINT_MISSING.format(path=checkpoint_path)
        raise FileNotFoundError(message)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, Mapping):
        raise ValueError(_FRONTEND_CHECKPOINT_MAPPING_REQUIRED)
    _require_nested_backend(checkpoint, f"frontend source checkpoint {checkpoint_path}")
    verify_provenance(
        checkpoint,
        {
            "config_hash": source.source_config_hash,
            "geometry_hash": source.source_geometry_hash,
            "degradation_hash": source.source_degradation_hash,
            "model_role": "frontend_only",
            "backend": None,
        },
        fields=(
            "config_hash",
            "geometry_hash",
            "degradation_hash",
            "model_role",
            "backend",
        ),
        cross_equality=(
            (
                "source_vs_target_geometry_hash",
                source.source_geometry_hash,
                geometry_hash,
            ),
            (
                "source_vs_target_degradation_hash",
                source.source_degradation_hash,
                target_degradation_hash,
            ),
        ),
    )
    if source.source_profile_name is not None:
        verify_provenance(
            checkpoint,
            {
                "seed": source.source_seed,
                "profile_name": source.source_profile_name,
                "run_name": source.source_run_key,
            },
            fields=("seed", "profile_name", "run_name"),
            context="seed-matched optical warm start",
        )
    state_dict = checkpoint.get("model_state_dict")
    if not isinstance(state_dict, Mapping):
        raise ValueError(_FRONTEND_STATE_MAPPING_REQUIRED)
    _frontend_for_model(model).load_state_dict(state_dict, strict=True)

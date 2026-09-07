from __future__ import annotations

import torch
from torch import nn

from experiments.restoration.fixed_measurement.learning.backend import BackendConfig, build_restoration_backend
from experiments.restoration.fixed_measurement.learning.config import TrainingConfig
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.fixed_measurement.learning.connection import ConnectionConfig, build_connection
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.fixed_measurement.optics.frontend import RestorationFrontend
from experiments.restoration.fixed_measurement.learning.hybrid import FrozenFrontendBackend, JointFrontendBackend
from experiments.restoration.fixed_measurement.optics.reference_arm import reference_arm_from_frontend


def assemble_model(
    *,
    model_role: str,
    bench_config: OpticalBenchConfig,
    phase_parameterization: str,
    phase_initialization: str,
    trainable_parameters: tuple[str, ...],
    backend: BackendConfig | None,
    connection_config: ConnectionConfig,
    defocus_operator: object | None,
) -> nn.Module:
    """
    鏋勫缓璁粌鎴栧熀鍑嗗姞杞芥墍闇€鐨勫鍘熸ā鍨?    """
    if model_role == "frontend_only":
        return RestorationFrontend(
            bench_config,
            phase_parameterization=phase_parameterization,
            phase_initialization=phase_initialization,
            is_phase_offset_reference_trainable=(
                "phase_offset_reference" in trainable_parameters
            ),
        )
    if model_role == "backend_only":
        if backend is None:
            raise invalid_restoration_contract(
                "backend config is required for backend_only training"
            )
        return build_restoration_backend(
            backend,
            defocus_operator=defocus_operator,
        )
    if model_role in {
        "frozen_optical_frontend_digital_backend",
        "joint_optical_frontend_digital_backend",
    }:
        if backend is None:
            raise invalid_restoration_contract(
                "backend config is required for hybrid training"
            )
        frontend = RestorationFrontend(
            bench_config,
            phase_parameterization=phase_parameterization,
            phase_initialization=phase_initialization,
            is_phase_offset_reference_trainable=(
                "phase_offset_reference" in trainable_parameters
            ),
        )
        built_backend = build_restoration_backend(
            backend,
            defocus_operator=defocus_operator,
            reference_arm=reference_arm_from_frontend(frontend),
        )
        connection = build_connection(connection_config)
        if model_role == "frozen_optical_frontend_digital_backend":
            return FrozenFrontendBackend(
                frontend,
                built_backend,
                connection=connection,
                is_connection_trainable="connection" in trainable_parameters,
            )
        return JointFrontendBackend(
            frontend,
            built_backend,
            connection=connection,
            is_connection_trainable="connection" in trainable_parameters,
        )
    raise invalid_restoration_contract(
        f"unsupported restoration model_role: {model_role}"
    )


def _reference_phase_offset_provenance(
    model: nn.Module,
    config: TrainingConfig,
) -> float | None:
    if config.model_role not in {
        "frozen_optical_frontend_digital_backend",
        "joint_optical_frontend_digital_backend",
    }:
        return None
    frontend = _frontend_for_model(model)
    return reference_arm_from_frontend(frontend).phase_offset()


def _initial_phase_mask_for_model(model: nn.Module) -> torch.Tensor | None:
    phase_source = _frontend_for_model(model)
    phase_getter = getattr(phase_source, "_effective_phase_mask", None)
    if not callable(phase_getter):
        return None
    return phase_getter().detach().cpu().clone()


def _trainable_parameter_names(
    model: nn.Module,
    config: TrainingConfig,
) -> list[str]:
    name_getter = getattr(model, "trainable_parameter_names", None)
    if callable(name_getter):
        return list(name_getter())
    if config.model_role == "backend_only" and any(
        parameter.requires_grad for parameter in model.parameters()
    ):
        return ["backend"]
    return []


def _effective_phase_for_model(model: nn.Module) -> torch.Tensor | None:
    phase_source = _frontend_for_model(model)
    phase_getter = getattr(phase_source, "_effective_phase_mask", None)
    if callable(phase_getter):
        return phase_getter()
    return None


def _phase_offset_reference_for_model(model: nn.Module) -> float:
    phase_source = _frontend_for_model(model)
    parameter = getattr(phase_source, "phase_offset_reference", None)
    if isinstance(parameter, torch.Tensor):
        return float(parameter.detach().cpu().item())
    bench_config = getattr(phase_source, "bench_config", None)
    value = getattr(bench_config, "phase_offset_reference", 0.0)
    return float(value)


def _frontend_for_model(model: nn.Module) -> nn.Module:
    frontend = getattr(model, "frontend", None)
    if isinstance(frontend, nn.Module):
        return frontend
    return model


def _connection_stats(model: nn.Module) -> dict[str, object]:
    connection = getattr(model, "connection", None)
    if connection is None:
        return {"connection_mode": "not_applicable"}
    mode = connection.__class__.__name__
    stats: dict[str, object] = {"connection_module": mode}
    optical_residual_gate = optical_residual_gate_for_model(model)
    if optical_residual_gate is not None:
        stats["connection_mode"] = "optical_residual_gate"
        stats["optical_residual_gate"] = optical_residual_gate
    elif mode == "SerialOpticalRestorationConnection":
        stats["connection_mode"] = "serial"
    elif mode == "DegradedImageConnection":
        stats["connection_mode"] = "degraded_image"
    elif mode == "DualChannelConnection":
        stats["connection_mode"] = "dual_channel"
    elif mode == "DualChannelOpticalZeroedConnection":
        stats["connection_mode"] = "dual_channel_optical_zeroed"
    else:
        stats["connection_mode"] = "unknown"
    return stats


def _mechanism_parameter_stats(model: nn.Module) -> dict[str, object]:
    """Return the active model's interpretable connection parameters."""
    stats: dict[str, object] = {}
    optical_residual_gate = optical_residual_gate_for_model(model)
    if optical_residual_gate is not None:
        stats["optical_residual_gate"] = optical_residual_gate
    return stats


def optical_residual_gate_for_model(model: nn.Module) -> float | None:
    """
    杩斿洖妯″瀷褰撳墠鐨勬爣閲忓厜瀛︽畫宸棬
    """
    connection = getattr(model, "connection", None)
    gate = getattr(connection, "optical_residual_gate", None)
    if not isinstance(gate, torch.Tensor) or gate.numel() != 1:
        return None
    return float(gate.detach().cpu().item())


def _phase_mask_stats(model: nn.Module) -> dict[str, object]:
    stats = _connection_stats(model)
    phase = _effective_phase_for_model(model)
    if phase is None:
        return {"status": "not_applicable", **stats}
    phase = phase.detach()
    return {
        "min": float(torch.min(phase).item()),
        "max": float(torch.max(phase).item()),
        "mean": float(torch.mean(phase).item()),
        "std": float(torch.std(phase).item()) if phase.numel() > 1 else 0.0,
        **stats,
    }

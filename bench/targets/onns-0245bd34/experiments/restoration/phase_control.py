from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from numbers import Integral
from types import MappingProxyType
from typing import Protocol

import torch
from torch.nn import functional

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.value_contracts import finite_real


_TWO_PI = 2.0 * math.pi


def _phase_plane(name: str, value: object) -> torch.Tensor:
    if not isinstance(value, torch.Tensor):
        raise invalid_restoration_contract(f"{name} must be a torch.Tensor")
    if value.ndim != 2 or value.numel() == 0:
        raise invalid_restoration_contract(f"{name} must be a non-empty 2D tensor")
    if torch.is_complex(value):
        raise invalid_restoration_contract(f"{name} must be real")
    phase = value.to(dtype=torch.float32)
    if not bool(torch.isfinite(phase).all()):
        raise invalid_restoration_contract(f"{name} must contain only finite values")
    return phase


def _nonempty_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise invalid_restoration_contract(f"{name} must be a non-empty string")
    return value


def _phase_weights(phase: torch.Tensor, pupil: torch.Tensor | None) -> torch.Tensor:
    if pupil is None:
        return torch.ones_like(phase)
    weights = _phase_plane("pupil", pupil).to(device=phase.device)
    if tuple(weights.shape) != tuple(phase.shape):
        raise invalid_restoration_contract("pupil must match the phase shape")
    if bool(torch.any(weights < 0)):
        raise invalid_restoration_contract("pupil must be nonnegative")
    if float(weights.sum().item()) <= 0.0:
        raise invalid_restoration_contract("pupil must contain positive support")
    return weights


def remove_phase_piston(
    phase_radians: torch.Tensor,
    *,
    pupil: torch.Tensor | None = None,
) -> torch.Tensor:
    """Return a phase plane in the pupil-weighted zero-mean piston gauge."""
    phase = _phase_plane("phase_radians", phase_radians)
    weights = _phase_weights(phase, pupil)
    piston = torch.sum(phase * weights) / torch.sum(weights)
    return phase - piston


def wrap_phase_radians(phase_radians: torch.Tensor) -> torch.Tensor:
    """Wrap a finite phase plane to the half-open interval [0, 2 pi)."""
    return torch.remainder(_phase_plane("phase_radians", phase_radians), _TWO_PI)


@dataclass(frozen=True, slots=True, eq=False)
class PhaseCommand:
    """A spatial phase action plus a separately identified global piston."""

    command_id: str
    phase_radians: torch.Tensor
    piston_radians: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "command_id", _nonempty_text("command_id", self.command_id)
        )
        object.__setattr__(
            self,
            "phase_radians",
            _phase_plane("phase_radians", self.phase_radians).detach().clone(),
        )
        object.__setattr__(
            self,
            "piston_radians",
            finite_real("piston_radians", self.piston_radians),
        )


@dataclass(frozen=True, slots=True, eq=False)
class DeliveredPhaseState:
    """The phase state used by an optical model after delivery effects."""

    command_id: str
    phase_radians: torch.Tensor
    delivery_model: str
    piston_radians: float = 0.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "command_id", _nonempty_text("command_id", self.command_id)
        )
        object.__setattr__(
            self,
            "delivery_model",
            _nonempty_text("delivery_model", self.delivery_model),
        )
        object.__setattr__(
            self,
            "phase_radians",
            wrap_phase_radians(self.phase_radians).detach().clone(),
        )
        object.__setattr__(
            self,
            "piston_radians",
            finite_real("piston_radians", self.piston_radians) % _TWO_PI,
        )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


class PhaseDelivery(Protocol):
    """Deliver one phase command in the modelled actuator coordinate system."""

    def deliver(
        self,
        command: PhaseCommand,
        *,
        pupil: torch.Tensor | None = None,
    ) -> DeliveredPhaseState:
        """Return the delivered state without mutating the command."""

    def project_delivered_phase(
        self,
        command_id: str,
        desired_phase_radians: torch.Tensor,
        *,
        pupil: torch.Tensor | None = None,
    ) -> PhaseCommand:
        """Map one desired delivered phase into calibrated command space."""


@dataclass(frozen=True, slots=True)
class IdealPhaseDelivery:
    """Deliver continuous phase exactly after fixing the piston gauge."""

    def deliver(
        self,
        command: PhaseCommand,
        *,
        pupil: torch.Tensor | None = None,
    ) -> DeliveredPhaseState:
        spatial_phase = remove_phase_piston(command.phase_radians, pupil=pupil)
        delivered_piston = float(command.piston_radians) % _TWO_PI
        phase = spatial_phase + delivered_piston
        return DeliveredPhaseState(
            command_id=command.command_id,
            phase_radians=phase,
            delivery_model="ideal_continuous_phase",
            piston_radians=delivered_piston,
            metadata={"phase_levels": None, "crosstalk_mix": 0.0},
        )

    def project_delivered_phase(
        self,
        command_id: str,
        desired_phase_radians: torch.Tensor,
        *,
        pupil: torch.Tensor | None = None,
    ) -> PhaseCommand:
        spatial_phase, piston = _split_phase_piston(
            desired_phase_radians,
            pupil=pupil,
        )
        return PhaseCommand(command_id, spatial_phase, piston_radians=piston)


@dataclass(frozen=True, slots=True)
class SimulatedSlmPhaseDelivery:
    """Model finite phase levels, response gain, drift, and local crosstalk."""

    phase_levels: int = 256
    response_gain: float = 1.0
    drift_radians: float = 0.0
    crosstalk_mix: float = 0.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.phase_levels, bool)
            or not isinstance(self.phase_levels, Integral)
            or int(self.phase_levels) < 2
        ):
            raise invalid_restoration_contract(
                "phase_levels must be an integer of at least 2"
            )
        for name, value in (
            ("response_gain", self.response_gain),
            ("drift_radians", self.drift_radians),
            ("crosstalk_mix", self.crosstalk_mix),
        ):
            finite_real(name, value)
        if self.response_gain <= 0.0:
            raise invalid_restoration_contract("response_gain must be positive")
        if not 0.0 <= self.crosstalk_mix <= 1.0:
            raise invalid_restoration_contract("crosstalk_mix must be between 0 and 1")

    def deliver(
        self,
        command: PhaseCommand,
        *,
        pupil: torch.Tensor | None = None,
    ) -> DeliveredPhaseState:
        gauge_fixed = remove_phase_piston(command.phase_radians, pupil=pupil)
        quantization_step = _TWO_PI / float(self.phase_levels)
        spatial_response = wrap_phase_radians(gauge_fixed * float(self.response_gain))
        quantized_spatial = (
            torch.round(spatial_response / quantization_step) * quantization_step
        )
        delivered_spatial = self._apply_crosstalk(quantized_spatial)
        piston_after_response = (
            float(command.piston_radians) * float(self.response_gain)
            + float(self.drift_radians)
        ) % _TWO_PI
        delivered_piston = (
            round(piston_after_response / quantization_step) * quantization_step
        ) % _TWO_PI
        delivered = delivered_spatial + delivered_piston
        return DeliveredPhaseState(
            command_id=command.command_id,
            phase_radians=delivered,
            delivery_model="simulated_slm_phase",
            piston_radians=delivered_piston,
            metadata={
                "phase_levels": int(self.phase_levels),
                "response_gain": float(self.response_gain),
                "drift_radians": float(self.drift_radians),
                "crosstalk_mix": float(self.crosstalk_mix),
                "command_piston_radians": float(command.piston_radians),
                "is_spatial_piston_separable": True,
            },
        )

    def project_delivered_phase(
        self,
        command_id: str,
        desired_phase_radians: torch.Tensor,
        *,
        pupil: torch.Tensor | None = None,
    ) -> PhaseCommand:
        spatial_phase, piston = _split_phase_piston(
            desired_phase_radians,
            pupil=pupil,
        )
        response_gain = float(self.response_gain)
        return PhaseCommand(
            command_id,
            spatial_phase / response_gain,
            piston_radians=(piston - float(self.drift_radians)) / response_gain,
        )

    def _apply_crosstalk(self, phase_radians: torch.Tensor) -> torch.Tensor:
        if self.crosstalk_mix == 0.0:
            return phase_radians
        phasor = torch.exp(1j * phase_radians)
        real_mean = functional.avg_pool2d(
            phasor.real[None, None],
            kernel_size=3,
            stride=1,
            padding=1,
        )[0, 0]
        imaginary_mean = functional.avg_pool2d(
            phasor.imag[None, None],
            kernel_size=3,
            stride=1,
            padding=1,
        )[0, 0]
        local_mean = torch.complex(real_mean, imaginary_mean)
        mixed = (1.0 - self.crosstalk_mix) * phasor + self.crosstalk_mix * local_mean
        return torch.angle(mixed)


def _split_phase_piston(
    phase_radians: torch.Tensor,
    *,
    pupil: torch.Tensor | None,
) -> tuple[torch.Tensor, float]:
    phase = _phase_plane("desired_phase_radians", phase_radians)
    weights = _phase_weights(phase, pupil)
    piston = torch.sum(phase * weights) / torch.sum(weights)
    return phase - piston, float(piston.item())

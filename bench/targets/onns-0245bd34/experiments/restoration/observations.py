from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from numbers import Integral, Real
from types import MappingProxyType
from typing import Literal

import torch

from experiments.restoration.errors import invalid_restoration_contract


ObservationKind = Literal["fixed", "calibration", "science"]


@dataclass(frozen=True, slots=True, eq=False)
class OpticalObservation:
    """One independently identified detector observation and its optical state."""

    observation_id: str
    kind: ObservationKind
    sequence_index: int
    intensity: torch.Tensor
    command_id: str
    command_phase_radians: torch.Tensor
    delivered_phase_radians: torch.Tensor
    delivery_model: str
    is_reference_enabled: bool
    command_piston_radians: float = 0.0
    delivered_piston_radians: float = 0.0
    elapsed_time_s: float = 0.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("observation_id", "command_id", "delivery_model"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise invalid_restoration_contract(
                    f"{field_name} must be a non-empty string"
                )
        if self.kind not in {"fixed", "calibration", "science"}:
            raise invalid_restoration_contract(
                "kind must be one of: fixed, calibration, science"
            )
        if (
            isinstance(self.sequence_index, bool)
            or not isinstance(self.sequence_index, Integral)
            or int(self.sequence_index) < 0
        ):
            raise invalid_restoration_contract(
                "sequence_index must be a nonnegative integer"
            )
        if not isinstance(self.intensity, torch.Tensor):
            raise invalid_restoration_contract("intensity must be a torch.Tensor")
        if self.intensity.ndim < 2 or self.intensity.numel() == 0:
            raise invalid_restoration_contract(
                "intensity must have at least two non-empty dimensions"
            )
        if torch.is_complex(self.intensity) or not bool(
            torch.isfinite(self.intensity).all()
        ):
            raise invalid_restoration_contract("intensity must be finite and real")
        if bool(torch.any(self.intensity < 0)):
            raise invalid_restoration_contract("intensity must be nonnegative")
        phase_shape = tuple(self.intensity.shape[-2:])
        for field_name in (
            "command_phase_radians",
            "delivered_phase_radians",
        ):
            phase = getattr(self, field_name)
            if (
                not isinstance(phase, torch.Tensor)
                or torch.is_complex(phase)
                or tuple(phase.shape) != phase_shape
            ):
                raise invalid_restoration_contract(
                    f"{field_name} must be a real 2D tensor matching intensity"
                )
            if not bool(torch.isfinite(phase).all()):
                raise invalid_restoration_contract(
                    f"{field_name} must contain only finite values"
                )
            object.__setattr__(
                self,
                field_name,
                phase.to(dtype=torch.float32).detach().clone(),
            )
        if not isinstance(self.is_reference_enabled, bool):
            raise invalid_restoration_contract("is_reference_enabled must be boolean")
        for field_name in (
            "command_piston_radians",
            "delivered_piston_radians",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(float(value))
            ):
                raise invalid_restoration_contract(
                    f"{field_name} must be a finite real number"
                )
            object.__setattr__(self, field_name, float(value))
        if (
            isinstance(self.elapsed_time_s, bool)
            or not isinstance(self.elapsed_time_s, Real)
            or float(self.elapsed_time_s) < 0.0
        ):
            raise invalid_restoration_contract("elapsed_time_s must be nonnegative")
        object.__setattr__(self, "sequence_index", int(self.sequence_index))
        object.__setattr__(
            self,
            "intensity",
            self.intensity.to(dtype=torch.float32).detach().clone(),
        )
        object.__setattr__(self, "elapsed_time_s", float(self.elapsed_time_s))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

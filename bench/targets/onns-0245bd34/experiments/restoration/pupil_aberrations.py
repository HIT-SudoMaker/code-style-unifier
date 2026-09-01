from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from numbers import Real
from types import MappingProxyType

import torch

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.value_contracts import normalize_array_resolution


SUPPORTED_PUPIL_MODES = (
    "defocus",
    "astigmatism_vertical",
    "astigmatism_oblique",
    "coma_vertical",
    "coma_horizontal",
    "spherical",
)


def _coefficient_mapping(value: object) -> Mapping[str, float]:
    if not isinstance(value, Mapping) or not value:
        raise invalid_restoration_contract(
            "coefficients_radians must be a non-empty mapping"
        )
    normalized: dict[str, float] = {}
    for mode_name, coefficient in value.items():
        if mode_name not in SUPPORTED_PUPIL_MODES:
            allowed = ", ".join(SUPPORTED_PUPIL_MODES)
            raise invalid_restoration_contract(f"pupil mode must be one of: {allowed}")
        if (
            isinstance(coefficient, bool)
            or not isinstance(coefficient, Real)
            or not math.isfinite(float(coefficient))
        ):
            raise invalid_restoration_contract(
                f"coefficient for {mode_name} must be a finite real number"
            )
        normalized[str(mode_name)] = float(coefficient)
    return MappingProxyType(normalized)


@dataclass(frozen=True, slots=True)
class PupilAberrationState:
    """A declared pupil-phase state in normalized orthogonal modes."""

    coefficients_radians: Mapping[str, float] = field(
        default_factory=lambda: {"defocus": 1.0}
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "coefficients_radians",
            _coefficient_mapping(self.coefficients_radians),
        )


def build_pupil_aberration_phase(
    array_resolution: tuple[int, int],
    state: PupilAberrationState,
    *,
    device: torch.device | str | None = None,
    dtype: torch.dtype = torch.float32,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Build a zero-piston phase and circular pupil for a declared state."""
    height, width = normalize_array_resolution("array_resolution", array_resolution)
    if not isinstance(state, PupilAberrationState):
        raise TypeError("state must be a PupilAberrationState")
    coordinate_y = torch.linspace(-1.0, 1.0, height, device=device, dtype=dtype)
    coordinate_x = torch.linspace(-1.0, 1.0, width, device=device, dtype=dtype)
    grid_y, grid_x = torch.meshgrid(coordinate_y, coordinate_x, indexing="ij")
    radius = torch.sqrt(grid_x.square() + grid_y.square())
    angle = torch.atan2(grid_y, grid_x)
    pupil = (radius <= 1.0).to(dtype=dtype)
    raw_modes = {
        "defocus": 2.0 * radius.square() - 1.0,
        "astigmatism_vertical": radius.square() * torch.cos(2.0 * angle),
        "astigmatism_oblique": radius.square() * torch.sin(2.0 * angle),
        "coma_vertical": (3.0 * radius.pow(3) - 2.0 * radius) * torch.sin(angle),
        "coma_horizontal": (3.0 * radius.pow(3) - 2.0 * radius) * torch.cos(angle),
        "spherical": 6.0 * radius.pow(4) - 6.0 * radius.square() + 1.0,
    }
    phase = torch.zeros((height, width), device=device, dtype=dtype)
    support = pupil > 0
    for mode_name, coefficient in state.coefficients_radians.items():
        mode = raw_modes[mode_name] * pupil
        supported = mode[support]
        centered = mode - torch.mean(supported) * pupil
        rms = torch.sqrt(torch.mean(centered[support].square()))
        if float(rms.item()) <= 0.0:
            raise invalid_restoration_contract(
                f"pupil mode {mode_name} has no resolvable support"
            )
        phase = phase + float(coefficient) * centered / rms
    return phase * pupil, pupil

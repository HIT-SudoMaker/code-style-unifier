from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral

import torch

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.value_contracts import finite_real


@dataclass(frozen=True, slots=True)
class DetectorNoiseModel:
    """Sample reproducible photon and read noise for one camera exposure."""

    photon_count: float | None = None
    read_noise_standard_deviation: float = 0.0
    seed: int = 2026

    def __post_init__(self) -> None:
        photon_count = self.photon_count
        if photon_count is not None:
            photon_count = finite_real("photon_count", photon_count)
            if photon_count <= 0.0:
                raise invalid_restoration_contract("photon_count must be positive")
        read_noise = finite_real(
            "read_noise_standard_deviation",
            self.read_noise_standard_deviation,
        )
        if read_noise < 0.0:
            raise invalid_restoration_contract(
                "read_noise_standard_deviation must be nonnegative"
            )
        if (
            isinstance(self.seed, bool)
            or not isinstance(self.seed, Integral)
            or not 0 <= int(self.seed) <= 2**32 - 1
        ):
            raise invalid_restoration_contract(
                "seed must be an integer between 0 and 4294967295"
            )
        object.__setattr__(self, "photon_count", photon_count)
        object.__setattr__(self, "read_noise_standard_deviation", read_noise)
        object.__setattr__(self, "seed", int(self.seed))

    def sample(
        self,
        intensity: torch.Tensor,
        *,
        sequence_index: int,
    ) -> torch.Tensor:
        """Return one noise realization identified by its exposure sequence."""
        if (
            not isinstance(intensity, torch.Tensor)
            or torch.is_complex(intensity)
            or intensity.numel() == 0
            or not bool(torch.isfinite(intensity).all())
            or bool(torch.any(intensity < 0.0))
        ):
            raise invalid_restoration_contract(
                "intensity must be a finite nonnegative real tensor"
            )
        if (
            isinstance(sequence_index, bool)
            or not isinstance(sequence_index, Integral)
            or int(sequence_index) < 0
        ):
            raise invalid_restoration_contract(
                "sequence_index must be a nonnegative integer"
            )
        if self.photon_count is None and self.read_noise_standard_deviation == 0.0:
            return intensity

        generator = torch.Generator(device=intensity.device)
        generator.manual_seed(self.seed + int(sequence_index))
        sampled = intensity
        if self.photon_count is not None:
            sampled = (
                torch.poisson(
                    sampled * self.photon_count,
                    generator=generator,
                )
                / self.photon_count
            )
        if self.read_noise_standard_deviation > 0.0:
            sampled = (
                sampled
                + torch.randn(
                    sampled.shape,
                    dtype=sampled.dtype,
                    device=sampled.device,
                    generator=generator,
                )
                * self.read_noise_standard_deviation
            )
        return torch.clamp(sampled, min=0.0)

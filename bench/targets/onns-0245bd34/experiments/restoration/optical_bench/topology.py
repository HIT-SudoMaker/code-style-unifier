from __future__ import annotations

from dataclasses import dataclass
import math

import torch

from experiments.restoration.errors import invalid_restoration_contract


@dataclass(frozen=True, slots=True)
class DualArmTopology:
    """Parameters shared by the Fixed and Adaptive interferometer."""

    reference_power_fraction: float = 0.5
    processing_power_fraction: float = 0.5
    reference_amplitude_gain: float = 1.0
    processing_amplitude_gain: float = 1.0
    reference_phase_offset_radians: float = 0.0
    fft_normalization: str | None = None

    def __post_init__(self) -> None:
        values = (
            self.reference_power_fraction,
            self.processing_power_fraction,
            self.reference_amplitude_gain,
            self.processing_amplitude_gain,
            self.reference_phase_offset_radians,
        )
        if any(not math.isfinite(value) for value in values):
            raise invalid_restoration_contract(
                "dual-arm topology values must be finite"
            )
        if self.reference_power_fraction < 0.0:
            raise invalid_restoration_contract(
                "reference_power_fraction must be nonnegative"
            )
        if self.processing_power_fraction < 0.0:
            raise invalid_restoration_contract(
                "processing_power_fraction must be nonnegative"
            )
        if self.reference_power_fraction + self.processing_power_fraction > 1.0:
            raise invalid_restoration_contract(
                "dual-arm power fractions must sum to at most one"
            )
        if self.reference_amplitude_gain < 0.0:
            raise invalid_restoration_contract(
                "reference_amplitude_gain must be nonnegative"
            )
        if self.processing_amplitude_gain < 0.0:
            raise invalid_restoration_contract(
                "processing_amplitude_gain must be nonnegative"
            )
        if self.fft_normalization not in {None, "backward", "forward", "ortho"}:
            raise invalid_restoration_contract(
                "fft_normalization must be None, backward, forward, or ortho"
            )


@dataclass(frozen=True, slots=True, eq=False)
class DualArmFields:
    """Complex fields produced by one dual-arm propagation."""

    reference: torch.Tensor
    processing: torch.Tensor
    combined: torch.Tensor

    @property
    def reference_intensity(self) -> torch.Tensor:
        return self.reference.abs().square().real

    @property
    def processing_intensity(self) -> torch.Tensor:
        return self.processing.abs().square().real

    @property
    def combined_intensity(self) -> torch.Tensor:
        return self.combined.abs().square().real

    @property
    def interference_term(self) -> torch.Tensor:
        return 2.0 * torch.real(self.reference * torch.conj(self.processing))


def propagate_dual_arm(
    input_field: torch.Tensor,
    processing_transfer: torch.Tensor,
    topology: DualArmTopology,
    *,
    is_reference_enabled: bool = True,
    is_processing_enabled: bool = True,
    reference_phase_offset_radians: torch.Tensor | None = None,
) -> DualArmFields:
    """Propagate one field through the shared reference/processing topology."""
    _validate_field(input_field)
    if (
        not isinstance(processing_transfer, torch.Tensor)
        or not torch.is_complex(processing_transfer)
        or tuple(processing_transfer.shape) != tuple(input_field.shape[-2:])
        or not bool(torch.isfinite(processing_transfer).all())
    ):
        raise invalid_restoration_contract(
            "processing_transfer must be a finite complex plane matching input_field"
        )
    if not isinstance(topology, DualArmTopology):
        raise TypeError("topology must be a DualArmTopology")
    if not isinstance(is_reference_enabled, bool):
        raise TypeError("is_reference_enabled must be boolean")
    if not isinstance(is_processing_enabled, bool):
        raise TypeError("is_processing_enabled must be boolean")

    reference_scale = math.sqrt(topology.reference_power_fraction)
    reference_scale *= topology.reference_amplitude_gain
    real_dtype = (
        torch.float64 if input_field.dtype == torch.complex128 else torch.float32
    )
    reference_phase = (
        torch.tensor(
            topology.reference_phase_offset_radians,
            device=input_field.device,
            dtype=real_dtype,
        )
        if reference_phase_offset_radians is None
        else reference_phase_offset_radians.to(
            device=input_field.device,
            dtype=real_dtype,
        )
    )
    reference = reference_scale * torch.exp(1j * reference_phase) * input_field

    spectrum = torch.fft.fftshift(
        torch.fft.fft2(
            input_field,
            dim=(-2, -1),
            norm=topology.fft_normalization,
        ),
        dim=(-2, -1),
    )
    processing = torch.fft.ifft2(
        torch.fft.ifftshift(spectrum * processing_transfer, dim=(-2, -1)),
        dim=(-2, -1),
        norm=topology.fft_normalization,
    )
    processing_scale = math.sqrt(topology.processing_power_fraction)
    processing_scale *= topology.processing_amplitude_gain
    processing = processing_scale * processing

    if not is_reference_enabled:
        reference = torch.zeros_like(reference)
    if not is_processing_enabled:
        processing = torch.zeros_like(processing)
    return DualArmFields(
        reference=reference,
        processing=processing,
        combined=reference + processing,
    )


def _validate_field(input_field: torch.Tensor) -> None:
    if not isinstance(input_field, torch.Tensor):
        raise TypeError("input_field must be a torch.Tensor")
    if input_field.ndim < 2 or input_field.numel() == 0:
        raise invalid_restoration_contract(
            "input_field must have at least two non-empty dimensions"
        )
    if not torch.is_complex(input_field) or not bool(torch.isfinite(input_field).all()):
        raise invalid_restoration_contract("input_field must be finite and complex")

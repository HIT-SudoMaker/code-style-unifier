from __future__ import annotations

from dataclasses import dataclass
from numbers import Real

import torch

from experiments.restoration.adaptive_measurement.sensing.quadrature import (
    QuadratureFieldEstimate,
)
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.phase_control import PhaseCommand, remove_phase_piston


@dataclass(frozen=True, slots=True, eq=False)
class IntensityOnlyPhaseConjugation:
    """A phase-conjugate action inferred only from demodulated intensities."""

    command: PhaseCommand
    estimated_input_intensity: torch.Tensor
    estimated_processing_transfer: torch.Tensor
    spectral_support_fraction: float


def infer_phase_conjugate_action(
    estimate: QuadratureFieldEstimate,
    bench_config: OpticalBenchConfig,
    spectral_support_threshold: float = 1e-3,
) -> IntensityOnlyPhaseConjugation:
    """Infer differential phase without reading a scene field or clean target."""
    if not isinstance(estimate, QuadratureFieldEstimate):
        raise TypeError("estimate must be a QuadratureFieldEstimate")
    if not isinstance(bench_config, OpticalBenchConfig):
        raise TypeError("bench_config must be an OpticalBenchConfig")
    bench_config.validate()
    threshold = _fraction("spectral_support_threshold", spectral_support_threshold)
    if tuple(estimate.cross_term.shape[-2:]) != bench_config.input_array_resolution:
        raise invalid_restoration_contract(
            "quadrature estimate must match the optical bench resolution"
        )

    reference_scale = (
        bench_config.split_ratio_reference**0.5 * bench_config.amplitude_gain_reference
    )
    processing_scale = (
        bench_config.split_ratio_process**0.5 * bench_config.amplitude_gain_process
    )
    if reference_scale <= 0.0 or processing_scale <= 0.0:
        raise invalid_restoration_contract(
            "intensity-only phase conjugation requires both arms"
        )

    cross_term = estimate.cross_term
    incoherent = estimate.incoherent_intensity
    discriminant = torch.clamp(
        incoherent.square() - 4.0 * cross_term.abs().square(),
        min=0.0,
    )
    larger_arm_intensity = 0.5 * (incoherent + torch.sqrt(discriminant))
    smaller_arm_intensity = 0.5 * (incoherent - torch.sqrt(discriminant))
    if abs(reference_scale - processing_scale) <= 1e-12:
        reference_intensity = 0.5 * incoherent
    else:
        reference_intensity = (
            larger_arm_intensity
            if reference_scale > processing_scale
            else smaller_arm_intensity
        )
    reference_phase = torch.as_tensor(
        bench_config.phase_offset_reference,
        device=cross_term.device,
        dtype=cross_term.real.dtype,
    )
    reference_field = torch.sqrt(torch.clamp(reference_intensity, min=0.0))
    reference_field = reference_field.to(cross_term.dtype) * torch.exp(
        1j * reference_phase
    )
    stable_reference = reference_field.abs() > (
        reference_field.abs().amax() * threshold
    )
    processing_field = torch.zeros_like(cross_term)
    processing_field[stable_reference] = cross_term[stable_reference] / torch.conj(
        reference_field[stable_reference]
    )
    input_field = reference_field / (reference_scale * torch.exp(1j * reference_phase))
    input_field = input_field.abs().to(cross_term.dtype)

    input_spectrum = _centered_fft(input_field)
    processing_spectrum = _centered_fft(processing_field / processing_scale)
    spectral_support = input_spectrum.abs() > (input_spectrum.abs().amax() * threshold)
    transfer = torch.zeros_like(input_spectrum)
    transfer[spectral_support] = (
        processing_spectrum[spectral_support] / input_spectrum[spectral_support]
    )
    transfer_phase = torch.zeros_like(input_spectrum.real)
    transfer_phase[spectral_support] = torch.angle(transfer[spectral_support])
    action = remove_phase_piston(-_single_plane(transfer_phase))
    return IntensityOnlyPhaseConjugation(
        command=PhaseCommand("intensity-only-phase-conjugation", action),
        estimated_input_intensity=input_field.abs().square().real.detach().clone(),
        estimated_processing_transfer=transfer.detach().clone(),
        spectral_support_fraction=float(spectral_support.float().mean().item()),
    )


def _centered_fft(field: torch.Tensor) -> torch.Tensor:
    return torch.fft.fftshift(
        torch.fft.fft2(field, dim=(-2, -1)),
        dim=(-2, -1),
    )


def _single_plane(value: torch.Tensor) -> torch.Tensor:
    return value.reshape((-1, *value.shape[-2:]))[0]


def _fraction(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a real number")
    normalized = float(value)
    if not 0.0 < normalized < 1.0:
        raise invalid_restoration_contract(f"{name} must be between zero and one")
    return normalized

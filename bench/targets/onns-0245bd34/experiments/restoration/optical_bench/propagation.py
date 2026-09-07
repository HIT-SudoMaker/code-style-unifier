from __future__ import annotations

import torch

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.optical_bench.configuration import OpticalBenchConfig
from experiments.restoration.optical_bench.fourier_relay import (
    build_phase_zero_transfer,
)
from experiments.restoration.optical_bench.topology import (
    DualArmFields,
    DualArmTopology,
    propagate_dual_arm,
)


def propagate_interferometric_bench(
    input_field: torch.Tensor,
    processing_phase_radians: torch.Tensor,
    bench_config: OpticalBenchConfig,
    *,
    processing_aberration_radians: torch.Tensor | None = None,
    processing_pupil: torch.Tensor | None = None,
    is_reference_enabled: bool = True,
    is_processing_enabled: bool = True,
    reference_phase_offset_radians: torch.Tensor | None = None,
) -> DualArmFields:
    """Propagate one field through the frozen shared interferometric bench."""
    if not isinstance(bench_config, OpticalBenchConfig):
        raise TypeError("bench_config must be an OpticalBenchConfig")
    bench_config.validate()
    _validate_input_field(input_field, bench_config.input_array_resolution)
    real_dtype = _real_dtype_for(input_field.dtype)
    device = input_field.device
    phase = _real_plane(
        "processing_phase_radians",
        processing_phase_radians,
        resolution=bench_config.input_array_resolution,
        device=device,
        dtype=real_dtype,
    )
    aberration = (
        torch.zeros_like(phase)
        if processing_aberration_radians is None
        else _real_plane(
            "processing_aberration_radians",
            processing_aberration_radians,
            resolution=bench_config.input_array_resolution,
            device=device,
            dtype=real_dtype,
        )
    )
    pupil = (
        torch.ones_like(phase)
        if processing_pupil is None
        else _real_plane(
            "processing_pupil",
            processing_pupil,
            resolution=bench_config.input_array_resolution,
            device=device,
            dtype=real_dtype,
        )
    )
    if bool(torch.any(pupil < 0.0)):
        raise invalid_restoration_contract("processing_pupil must be nonnegative")

    physical_aperture = build_phase_zero_transfer(
        array_resolution=bench_config.input_array_resolution,
        pixel_size=bench_config.input_plane_pixel_size,
        aperture_policy=bench_config.aperture_policy,
        wavelength=bench_config.wavelength,
        focal_length=bench_config.focal_length,
        slm2_resolution=bench_config.slm2_resolution,
        slm2_pixel_size=bench_config.slm2_pixel_size,
        phase_mask_resolution=bench_config.phase_mask_resolution,
        slm2_active_area_policy=bench_config.slm2_active_area_policy,
        slm2_active_resolution=bench_config.slm2_active_resolution,
        device=device,
        dtype=real_dtype,
    )
    processing_transfer = (
        physical_aperture.to(dtype=input_field.dtype)
        * pupil.to(dtype=input_field.dtype)
        * torch.exp(1j * (aberration + phase))
    )
    return _propagate_interferometric_transfer(
        input_field,
        processing_transfer,
        bench_config,
        is_reference_enabled=is_reference_enabled,
        is_processing_enabled=is_processing_enabled,
        reference_phase_offset_radians=reference_phase_offset_radians,
    )


def _propagate_interferometric_transfer(
    input_field: torch.Tensor,
    processing_transfer: torch.Tensor,
    bench_config: OpticalBenchConfig,
    *,
    is_reference_enabled: bool = True,
    is_processing_enabled: bool = True,
    reference_phase_offset_radians: torch.Tensor | None = None,
) -> DualArmFields:
    """Propagate one already validated complex processing transfer."""
    if not isinstance(bench_config, OpticalBenchConfig):
        raise TypeError("bench_config must be an OpticalBenchConfig")
    bench_config.validate()
    _validate_input_field(input_field, bench_config.input_array_resolution)
    if (
        not isinstance(processing_transfer, torch.Tensor)
        or not torch.is_complex(processing_transfer)
        or tuple(processing_transfer.shape)
        != tuple(bench_config.input_array_resolution)
        or not bool(torch.isfinite(processing_transfer).all())
    ):
        raise invalid_restoration_contract(
            "processing_transfer must be a finite complex plane matching the bench resolution"
        )
    topology = DualArmTopology(
        reference_power_fraction=bench_config.split_ratio_reference,
        processing_power_fraction=bench_config.split_ratio_process,
        reference_amplitude_gain=bench_config.amplitude_gain_reference,
        processing_amplitude_gain=bench_config.amplitude_gain_process,
        reference_phase_offset_radians=bench_config.phase_offset_reference,
    )
    return propagate_dual_arm(
        input_field,
        processing_transfer.to(device=input_field.device, dtype=input_field.dtype),
        topology,
        is_reference_enabled=is_reference_enabled,
        is_processing_enabled=is_processing_enabled,
        reference_phase_offset_radians=reference_phase_offset_radians,
    )


def _validate_input_field(
    input_field: torch.Tensor,
    resolution: tuple[int, int],
) -> None:
    if not isinstance(input_field, torch.Tensor):
        raise TypeError("input_field must be a torch.Tensor")
    if input_field.ndim < 2 or input_field.numel() == 0:
        raise invalid_restoration_contract(
            "input_field must have at least two non-empty dimensions"
        )
    if tuple(input_field.shape[-2:]) != tuple(resolution):
        raise invalid_restoration_contract(
            "input_field must match bench_config.input_array_resolution"
        )
    if not torch.is_complex(input_field) or not bool(torch.isfinite(input_field).all()):
        raise invalid_restoration_contract("input_field must be finite and complex")


def _real_plane(
    name: str,
    plane: torch.Tensor,
    *,
    resolution: tuple[int, int],
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    if (
        not isinstance(plane, torch.Tensor)
        or torch.is_complex(plane)
        or tuple(plane.shape) != tuple(resolution)
        or not bool(torch.isfinite(plane).all())
    ):
        raise invalid_restoration_contract(
            f"{name} must be a finite real plane matching the bench resolution"
        )
    return plane.to(device=device, dtype=dtype)


def _real_dtype_for(dtype: torch.dtype) -> torch.dtype:
    return torch.float64 if dtype == torch.complex128 else torch.float32

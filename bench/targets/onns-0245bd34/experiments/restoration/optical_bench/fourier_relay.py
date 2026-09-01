from __future__ import annotations

from decimal import Decimal
import math
from numbers import Integral, Real

import torch
import torch.nn.functional as functional

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.optical_bench.configuration import OpticalBenchConfig


def _positive_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(f"{name} must be a positive real number")
    numeric_value = float(value)
    if not math.isfinite(numeric_value) or numeric_value <= 0:
        raise invalid_restoration_contract(f"{name} must be a positive real number")
    return numeric_value


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    numeric_value = int(value)
    if numeric_value <= 0:
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    return numeric_value


def _resolution_pair(name: str, value: object) -> tuple[int, int]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise invalid_restoration_contract(f"{name} must have height and width")
    return (
        _positive_integer(f"{name}[0]", value[0]),
        _positive_integer(f"{name}[1]", value[1]),
    )


def _radius_fraction(name: str, value: object) -> float:
    numeric_value = _positive_real(name, value)
    if numeric_value > 1.0:
        raise invalid_restoration_contract(f"{name} must be at most 1.0")
    return numeric_value


def build_frequency_grid(
    array_resolution: tuple[int, int],
    *,
    pixel_size: float,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Build centred spatial-frequency grids for one sampled input plane."""
    height, width = _resolution_pair("array_resolution", array_resolution)
    physical_pixel_size = _positive_real("pixel_size", pixel_size)

    frequency_y = torch.fft.fftshift(
        torch.fft.fftfreq(height, d=physical_pixel_size, device=device, dtype=dtype)
    )
    frequency_x = torch.fft.fftshift(
        torch.fft.fftfreq(width, d=physical_pixel_size, device=device, dtype=dtype)
    )
    frequency_grid_y, frequency_grid_x = torch.meshgrid(
        frequency_y,
        frequency_x,
        indexing="ij",
    )
    return frequency_grid_y, frequency_grid_x


def spatial_frequency_nyquist_input(config: OpticalBenchConfig) -> float:
    """Return the input-plane Nyquist spatial frequency."""
    return 1.0 / (
        2.0 * _positive_real("input_plane_pixel_size", config.input_plane_pixel_size)
    )


def spatial_frequency_nyquist_camera(config: OpticalBenchConfig) -> float:
    """Return the object-space Nyquist frequency implied by the camera."""
    camera_pixel_size = _positive_real("camera_pixel_size", config.camera_pixel_size)
    system_magnification = _positive_real(
        "system_magnification", config.system_magnification
    )
    return system_magnification / (2.0 * camera_pixel_size)


def spatial_frequency_cutoff_aperture(
    *,
    aperture_radius_fourier: float,
    wavelength: float,
    focal_length: float,
) -> float:
    """Return the aperture-limited spatial-frequency cutoff."""
    radius = _positive_real("aperture_radius_fourier", aperture_radius_fourier)
    physical_wavelength = _positive_real("wavelength", wavelength)
    physical_focal_length = _positive_real("focal_length", focal_length)
    return float(
        Decimal(str(radius))
        / (Decimal(str(physical_wavelength)) * Decimal(str(physical_focal_length)))
    )


def build_circular_aperture(
    array_resolution: tuple[int, int],
    *,
    radius_fraction: float,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Build a circular support on normalized array coordinates."""
    height, width = _resolution_pair("array_resolution", array_resolution)
    radius = _radius_fraction("radius_fraction", radius_fraction)

    coordinate_y = torch.linspace(-1.0, 1.0, height, device=device, dtype=dtype)
    coordinate_x = torch.linspace(-1.0, 1.0, width, device=device, dtype=dtype)
    grid_y, grid_x = torch.meshgrid(coordinate_y, coordinate_x, indexing="ij")
    normalized_radius = torch.sqrt(grid_y.square() + grid_x.square())
    return (normalized_radius <= radius).to(dtype=dtype)


def _aperture_radius_fraction(aperture_policy: str) -> float:
    radius_by_policy = {
        "full_slm_active_area": 1.0,
        "radius_0_75": 0.75,
        "radius_0_50": 0.50,
    }
    try:
        return radius_by_policy[aperture_policy]
    except KeyError as exc:
        raise invalid_restoration_contract(
            "aperture_policy must be one of: full_slm_active_area, radius_0_75, radius_0_50"
        ) from exc


def _slm2_active_pixel_count(
    *,
    phase_mask_resolution: int,
    slm2_resolution: tuple[int, int],
    slm2_active_area_policy: str,
    slm2_active_resolution: tuple[int, int] | None = None,
) -> int:
    mask_resolution = _positive_integer("phase_mask_resolution", phase_mask_resolution)
    active_height, active_width = _resolution_pair("slm2_resolution", slm2_resolution)
    short_side = min(active_height, active_width)
    if slm2_active_area_policy == "center_square":
        if slm2_active_resolution is None:
            if mask_resolution > short_side:
                raise invalid_restoration_contract(
                    "phase_mask_resolution must not exceed SLM2 short side"
                )
            return mask_resolution
        active_resolution_height, active_resolution_width = _resolution_pair(
            "slm2_active_resolution",
            slm2_active_resolution,
        )
        if active_resolution_height != active_resolution_width:
            raise invalid_restoration_contract("slm2_active_resolution must be square")
        if active_resolution_height > short_side:
            raise invalid_restoration_contract(
                "slm2_active_resolution must not exceed SLM2 short side"
            )
        return active_resolution_height
    if slm2_active_area_policy == "full_slm_active_area":
        return short_side
    raise invalid_restoration_contract(
        "slm2_active_area_policy must be one of: center_square, full_slm_active_area"
    )


def slm2_active_window_size(
    *,
    phase_mask_resolution: int,
    slm2_resolution: tuple[int, int],
    slm2_pixel_size: float,
    slm2_active_area_policy: str,
    slm2_active_resolution: tuple[int, int] | None = None,
) -> float:
    """Return the physical width of the active SLM2 control window."""
    active_pixels = _slm2_active_pixel_count(
        phase_mask_resolution=phase_mask_resolution,
        slm2_resolution=slm2_resolution,
        slm2_active_area_policy=slm2_active_area_policy,
        slm2_active_resolution=slm2_active_resolution,
    )
    return active_pixels * _positive_real("slm2_pixel_size", slm2_pixel_size)


def build_phase_zero_transfer(
    *,
    array_resolution: tuple[int, int],
    pixel_size: float,
    aperture_policy: str,
    wavelength: float,
    focal_length: float,
    slm2_resolution: tuple[int, int],
    slm2_pixel_size: float,
    phase_mask_resolution: int,
    slm2_active_area_policy: str,
    slm2_active_resolution: tuple[int, int] | None = None,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Build the zero-phase pupil transfer of the frozen Fourier relay."""
    height, width = _resolution_pair("array_resolution", array_resolution)
    _positive_real("pixel_size", pixel_size)
    active_size = slm2_active_window_size(
        phase_mask_resolution=phase_mask_resolution,
        slm2_resolution=slm2_resolution,
        slm2_pixel_size=slm2_pixel_size,
        slm2_active_area_policy=slm2_active_area_policy,
        slm2_active_resolution=slm2_active_resolution,
    )
    aperture_radius = 0.5 * active_size * _aperture_radius_fraction(aperture_policy)
    cutoff_frequency = spatial_frequency_cutoff_aperture(
        aperture_radius_fourier=aperture_radius,
        wavelength=wavelength,
        focal_length=focal_length,
    )
    frequency_y, frequency_x = build_frequency_grid(
        (height, width),
        pixel_size=pixel_size,
        device=device,
        dtype=dtype,
    )
    frequency_radius = torch.sqrt(frequency_x.square() + frequency_y.square())
    return (frequency_radius <= cutoff_frequency).to(dtype=dtype)


def map_phase_mask_to_fourier_grid(
    phase_mask: torch.Tensor,
    *,
    array_resolution: tuple[int, int],
    input_plane_pixel_size: float,
    wavelength: float,
    focal_length: float,
    slm2_resolution: tuple[int, int],
    slm2_pixel_size: float,
    slm2_active_area_policy: str,
    slm2_active_resolution: tuple[int, int] | None = None,
    interpolation_policy: str,
    phase_wrap_policy: str,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Sample an SLM2 phase mask onto the physical Fourier grid."""
    if phase_mask.ndim != 2:
        raise invalid_restoration_contract("phase_mask must be a 2D tensor")
    height, width = _resolution_pair("array_resolution", array_resolution)
    phase_height, phase_width = _resolution_pair(
        "phase_mask.shape", tuple(phase_mask.shape)
    )
    active_size = slm2_active_window_size(
        phase_mask_resolution=min(phase_height, phase_width),
        slm2_resolution=slm2_resolution,
        slm2_pixel_size=slm2_pixel_size,
        slm2_active_area_policy=slm2_active_area_policy,
        slm2_active_resolution=slm2_active_resolution,
    )
    if interpolation_policy not in {"nearest", "bilinear", "bicubic"}:
        raise invalid_restoration_contract(
            "interpolation_policy must be one of: nearest, bilinear, bicubic"
        )
    if phase_wrap_policy != "wrap_to_2pi":
        raise invalid_restoration_contract("phase_wrap_policy must be wrap_to_2pi")

    frequency_y, frequency_x = build_frequency_grid(
        (height, width),
        pixel_size=input_plane_pixel_size,
        device=device,
        dtype=dtype,
    )
    coordinate_scale = _positive_real("wavelength", wavelength) * _positive_real(
        "focal_length",
        focal_length,
    )
    half_active_size = 0.5 * active_size
    normalized_x = frequency_x * coordinate_scale / half_active_size
    normalized_y = frequency_y * coordinate_scale / half_active_size
    sample_grid = torch.stack((normalized_x, normalized_y), dim=-1).unsqueeze(0)

    phase_nchw = phase_mask.to(device=device, dtype=dtype).unsqueeze(0).unsqueeze(0)
    # Physical coordinate endpoints coincide with the SLM active-window edge.
    sampled = functional.grid_sample(
        phase_nchw,
        sample_grid,
        mode=interpolation_policy,
        padding_mode="zeros",
        align_corners=True,
    )
    return torch.remainder(sampled.squeeze(0).squeeze(0), 2.0 * math.pi)


def map_phase_mask_to_slm2(
    phase_mask: torch.Tensor,
    *,
    output_resolution: tuple[int, int],
    interpolation_policy: str,
    phase_wrap_policy: str,
) -> torch.Tensor:
    """Resample a phase action onto the native SLM2 pixel grid."""
    if phase_mask.ndim != 2:
        raise invalid_restoration_contract("phase_mask must be a 2D tensor")
    height, width = _resolution_pair("output_resolution", output_resolution)
    if interpolation_policy not in {"nearest", "bilinear", "bicubic"}:
        raise invalid_restoration_contract(
            "interpolation_policy must be one of: nearest, bilinear, bicubic"
        )
    if phase_wrap_policy != "wrap_to_2pi":
        raise invalid_restoration_contract("phase_wrap_policy must be wrap_to_2pi")

    phase_nchw = phase_mask.unsqueeze(0).unsqueeze(0)
    if interpolation_policy == "nearest":
        mapped = functional.interpolate(
            phase_nchw,
            size=(height, width),
            mode=interpolation_policy,
        )
    else:
        # Preserve PyTorch's half-pixel convention during SLM resampling.
        mapped = functional.interpolate(
            phase_nchw,
            size=(height, width),
            mode=interpolation_policy,
            align_corners=False,
        )
    return torch.remainder(mapped.squeeze(0).squeeze(0), 2.0 * math.pi)


def bin_dense_camera_intensity(
    dense_intensity: torch.Tensor,
    *,
    factor: int,
    policy: str,
) -> torch.Tensor:
    """Aggregate a dense simulated intensity onto camera pixels."""
    binning_factor = _positive_integer("factor", factor)
    if policy != "average":
        raise invalid_restoration_contract("policy must be average")
    if dense_intensity.ndim != 4:
        raise invalid_restoration_contract("dense_intensity must be a 4D tensor")
    height, width = dense_intensity.shape[-2:]
    if height % binning_factor != 0 or width % binning_factor != 0:
        raise invalid_restoration_contract(
            "dense_intensity height and width must be divisible by factor"
        )

    return functional.avg_pool2d(
        dense_intensity,
        kernel_size=binning_factor,
        stride=binning_factor,
    )


def build_theoretical_resolution_budget(
    config: OpticalBenchConfig,
) -> dict[str, object]:
    """Summarize the sampling and aperture limits of the frozen bench."""
    config.validate()
    height, width = config.input_array_resolution
    active_window_size = slm2_active_window_size(
        phase_mask_resolution=config.phase_mask_resolution,
        slm2_resolution=config.slm2_resolution,
        slm2_pixel_size=config.slm2_pixel_size,
        slm2_active_area_policy=config.slm2_active_area_policy,
        slm2_active_resolution=config.slm2_active_resolution,
    )
    aperture_radius = (
        0.5 * active_window_size * _aperture_radius_fraction(config.aperture_policy)
    )
    frequency_step_x = 1.0 / (width * config.input_plane_pixel_size)
    frequency_step_y = 1.0 / (height * config.input_plane_pixel_size)
    frequency_step = max(frequency_step_x, frequency_step_y)
    fourier_plane_pixel_size_x = (
        config.wavelength
        * config.focal_length
        / (width * config.input_plane_pixel_size)
    )
    fourier_plane_pixel_size_y = (
        config.wavelength
        * config.focal_length
        / (height * config.input_plane_pixel_size)
    )
    aperture_cutoff = spatial_frequency_cutoff_aperture(
        aperture_radius_fourier=aperture_radius,
        wavelength=config.wavelength,
        focal_length=config.focal_length,
    )

    return {
        "wavelength": config.wavelength,
        "input_plane_pixel_size": config.input_plane_pixel_size,
        "slm1_pixel_size": config.slm1_pixel_size,
        "slm2_pixel_size": config.slm2_pixel_size,
        "camera_pixel_size": config.camera_pixel_size,
        "focal_length": config.focal_length,
        "system_magnification": config.system_magnification,
        "slm1_resolution": [config.slm1_resolution[0], config.slm1_resolution[1]],
        "slm2_resolution": [config.slm2_resolution[0], config.slm2_resolution[1]],
        "camera_resolution": [config.camera_resolution[0], config.camera_resolution[1]],
        "input_array_resolution": [height, width],
        "phase_mask_resolution": config.phase_mask_resolution,
        "slm2_active_resolution": [
            config.slm2_active_resolution[0],
            config.slm2_active_resolution[1],
        ],
        "camera_oversampling_factor": config.camera_oversampling_factor,
        "camera_binning_policy": config.camera_binning_policy,
        "aperture_policy": config.aperture_policy,
        "slm2_active_area_policy": config.slm2_active_area_policy,
        "slm2_active_pixel_count": _slm2_active_pixel_count(
            phase_mask_resolution=config.phase_mask_resolution,
            slm2_resolution=config.slm2_resolution,
            slm2_active_area_policy=config.slm2_active_area_policy,
            slm2_active_resolution=config.slm2_active_resolution,
        ),
        "slm2_active_window_size": active_window_size,
        "padding_policy": config.padding_policy,
        "fft_normalization_policy": config.fft_normalization_policy,
        "fft_shift_policy": config.fft_shift_policy,
        "spatial_frequency_unit": config.spatial_frequency_unit,
        "process_arm_model": config.process_arm_model,
        "input_nyquist_frequency": 1.0 / (2.0 * config.input_plane_pixel_size),
        "slm1_nyquist_frequency": 1.0 / (2.0 * config.slm1_pixel_size),
        "slm2_nyquist_frequency": 1.0 / (2.0 * config.slm2_pixel_size),
        "camera_nyquist_frequency": (
            config.system_magnification / (2.0 * config.camera_pixel_size)
        ),
        "aperture_radius_fourier": aperture_radius,
        "aperture_cutoff_frequency": aperture_cutoff,
        "fourier_plane_coordinate_scale": config.wavelength * config.focal_length,
        "fourier_plane_frequency_step": frequency_step,
        "fourier_plane_pixel_size_x": fourier_plane_pixel_size_x,
        "fourier_plane_pixel_size_y": fourier_plane_pixel_size_y,
        "fourier_plane_width": width * fourier_plane_pixel_size_x,
        "fourier_plane_height": height * fourier_plane_pixel_size_y,
        "expected_point_response_width": 1.0 / max(aperture_cutoff, 1e-12),
    }

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Literal

from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.value_contracts import (
    finite_real,
    normalize_array_resolution,
)


IntensityNormalizationPolicy = Literal[
    "fixed_dataset_level",
    "characterization_calibrated_gain",
    "per_image_min_max",
]


def _positive_real(name: str, value: object) -> float:
    normalized = finite_real(name, value)
    if normalized <= 0.0:
        raise invalid_restoration_contract(f"{name} must be positive")
    return normalized


def _nonnegative_real(name: str, value: object) -> float:
    normalized = finite_real(name, value)
    if normalized < 0.0:
        raise invalid_restoration_contract(f"{name} must be nonnegative")
    return normalized


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise invalid_restoration_contract(f"{name} must be a positive integer")
    return int(value)


@dataclass(frozen=True, slots=True)
class OpticalBenchConfig:
    """Freeze the physical and sampled geometry shared by every experiment."""

    wavelength: float = 638e-9
    input_plane_pixel_size: float = 8e-6
    slm1_pixel_size: float = 8e-6
    slm2_pixel_size: float = 8e-6
    camera_pixel_size: float = 2.9e-6
    slm1_resolution: tuple[int, int] = (1200, 1920)
    slm2_resolution: tuple[int, int] = (1200, 1920)
    camera_resolution: tuple[int, int] = (2160, 3840)
    input_array_resolution: tuple[int, int] = (512, 512)
    phase_mask_resolution: int = 512
    slm2_active_resolution: tuple[int, int] = (1024, 1024)
    focal_length: float = 0.1
    system_magnification: float = 1.0
    aperture_policy: str = "full_slm_active_area"
    slm2_active_area_policy: str = "center_square"
    padding_policy: str = "center_pad"
    camera_oversampling_factor: int = 1
    camera_binning_policy: str = "none"
    fft_normalization_policy: str = "pytorch_default"
    fft_shift_policy: str = "centered_frequency_grid"
    spatial_frequency_unit: str = "cycles_per_meter"
    phase_mask_to_slm2_interpolation_policy: str = "bilinear"
    phase_wrap_policy: str = "wrap_to_2pi"
    phase_quantization_levels: int | None = None
    intensity_normalization_policy: IntensityNormalizationPolicy = "fixed_dataset_level"
    split_ratio_reference: float = 0.5
    split_ratio_process: float = 0.5
    amplitude_gain_reference: float = 1.0
    amplitude_gain_process: float = 1.0
    phase_offset_reference: float = 0.0
    process_arm_model: str = "compact_fourier_4f_equivalent"

    def validate(self) -> None:
        """Reject geometry that cannot describe the frozen optical bench."""
        for field_name in (
            "wavelength",
            "input_plane_pixel_size",
            "slm1_pixel_size",
            "slm2_pixel_size",
            "camera_pixel_size",
            "focal_length",
            "system_magnification",
        ):
            _positive_real(field_name, getattr(self, field_name))
        for field_name in (
            "slm1_resolution",
            "slm2_resolution",
            "camera_resolution",
            "input_array_resolution",
            "slm2_active_resolution",
        ):
            normalize_array_resolution(field_name, getattr(self, field_name))
        _positive_integer("phase_mask_resolution", self.phase_mask_resolution)
        _positive_integer(
            "camera_oversampling_factor",
            self.camera_oversampling_factor,
        )
        if self.phase_quantization_levels is not None:
            _positive_integer(
                "phase_quantization_levels",
                self.phase_quantization_levels,
            )
        if self.intensity_normalization_policy not in {
            "fixed_dataset_level",
            "characterization_calibrated_gain",
            "per_image_min_max",
        }:
            raise invalid_restoration_contract(
                "intensity_normalization_policy must be one of: "
                "fixed_dataset_level, characterization_calibrated_gain, "
                "per_image_min_max"
            )
        finite_real("phase_offset_reference", self.phase_offset_reference)
        if self.fft_normalization_policy != "pytorch_default":
            raise invalid_restoration_contract(
                "fft_normalization_policy must be pytorch_default"
            )
        if self.fft_shift_policy != "centered_frequency_grid":
            raise invalid_restoration_contract(
                "fft_shift_policy must be centered_frequency_grid"
            )
        if self.spatial_frequency_unit != "cycles_per_meter":
            raise invalid_restoration_contract(
                "spatial_frequency_unit must be cycles_per_meter"
            )
        if self.process_arm_model != "compact_fourier_4f_equivalent":
            raise invalid_restoration_contract(
                "process_arm_model must be compact_fourier_4f_equivalent"
            )
        if self.slm2_active_area_policy not in {
            "center_square",
            "full_slm_active_area",
        }:
            raise invalid_restoration_contract(
                "slm2_active_area_policy must be one of: "
                "center_square, full_slm_active_area"
            )
        if self.phase_mask_resolution > min(self.slm2_resolution):
            raise invalid_restoration_contract(
                "phase_mask_resolution must not exceed SLM2 short side"
            )
        if self.slm2_active_resolution[0] != self.slm2_active_resolution[1]:
            raise invalid_restoration_contract("slm2_active_resolution must be square")
        if self.slm2_active_resolution[0] > self.slm2_resolution[0]:
            raise invalid_restoration_contract(
                "slm2_active_resolution height must not exceed SLM2 height"
            )
        if self.slm2_active_resolution[1] > self.slm2_resolution[1]:
            raise invalid_restoration_contract(
                "slm2_active_resolution width must not exceed SLM2 width"
            )
        reference_fraction = _nonnegative_real(
            "split_ratio_reference",
            self.split_ratio_reference,
        )
        processing_fraction = _nonnegative_real(
            "split_ratio_process",
            self.split_ratio_process,
        )
        if reference_fraction + processing_fraction > 1.0:
            raise invalid_restoration_contract("split ratios must sum to at most 1")
        _nonnegative_real(
            "amplitude_gain_reference",
            self.amplitude_gain_reference,
        )
        _nonnegative_real(
            "amplitude_gain_process",
            self.amplitude_gain_process,
        )

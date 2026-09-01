"""Shared physical bench used by Fixed and Adaptive measurement protocols."""

from experiments.restoration.optical_bench.configuration import (
    IntensityNormalizationPolicy,
    OpticalBenchConfig,
)
from experiments.restoration.optical_bench.detector import DetectorNoiseModel
from experiments.restoration.optical_bench.fourier_relay import (
    bin_dense_camera_intensity,
    build_circular_aperture,
    build_frequency_grid,
    build_phase_zero_transfer,
    build_theoretical_resolution_budget,
    map_phase_mask_to_fourier_grid,
    map_phase_mask_to_slm2,
    slm2_active_window_size,
    spatial_frequency_cutoff_aperture,
    spatial_frequency_nyquist_camera,
    spatial_frequency_nyquist_input,
)
from experiments.restoration.optical_bench.propagation import (
    propagate_interferometric_bench,
)
from experiments.restoration.optical_bench.topology import DualArmFields


__all__ = (
    "DualArmFields",
    "DetectorNoiseModel",
    "IntensityNormalizationPolicy",
    "OpticalBenchConfig",
    "bin_dense_camera_intensity",
    "build_circular_aperture",
    "build_frequency_grid",
    "build_phase_zero_transfer",
    "build_theoretical_resolution_budget",
    "map_phase_mask_to_fourier_grid",
    "map_phase_mask_to_slm2",
    "propagate_interferometric_bench",
    "slm2_active_window_size",
    "spatial_frequency_cutoff_aperture",
    "spatial_frequency_nyquist_camera",
    "spatial_frequency_nyquist_input",
)

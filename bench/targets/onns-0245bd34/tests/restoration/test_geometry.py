from __future__ import annotations

import math

import pytest
import torch

from experiments.restoration.optical_bench import (
    OpticalBenchConfig,
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


def test_frequency_grid_uses_cycles_per_meter_and_centered_shift() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    fy, fx = build_frequency_grid(
        (4, 4),
        pixel_size=0.5,
        device=torch.device("cpu"),
    )

    assert fy.shape == (4, 4)
    assert fx.shape == (4, 4)
    assert fx[0, 0].item() == -1.0
    assert fx[0, -1].item() == 0.5


def test_nyquist_formulas_use_explicit_pixel_fields() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    config = OpticalBenchConfig(
        input_plane_pixel_size=2.0,
        camera_pixel_size=4.0,
        system_magnification=2.0,
    )

    assert spatial_frequency_nyquist_input(config) == 0.25
    assert spatial_frequency_nyquist_camera(config) == 0.25


def test_aperture_cutoff_uses_wavelength_focal_length_and_radius() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    cutoff = spatial_frequency_cutoff_aperture(
        aperture_radius_fourier=0.001,
        wavelength=500e-9,
        focal_length=0.25,
    )

    assert cutoff == 8000.0


def test_phase_mask_mapping_wraps_to_two_pi() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    phase_mask = torch.tensor(
        [
            [-0.5, 0.0],
            [2 * math.pi, 3 * math.pi],
        ],
        dtype=torch.float32,
    )

    mapped = map_phase_mask_to_slm2(
        phase_mask,
        output_resolution=(4, 4),
        interpolation_policy="nearest",
        phase_wrap_policy="wrap_to_2pi",
    )

    assert mapped.shape == (4, 4)
    assert torch.all(mapped >= 0)
    assert torch.all(mapped < 2 * math.pi)


def test_phase_zero_transfer_is_binary_aperture_with_expected_shape() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    transfer = build_phase_zero_transfer(
        array_resolution=(8, 8),
        pixel_size=1.0,
        aperture_policy="radius_0_50",
        wavelength=1.0,
        focal_length=1.0,
        slm2_resolution=(4, 4),
        slm2_pixel_size=0.25,
        phase_mask_resolution=4,
        slm2_active_area_policy="center_square",
        device=torch.device("cpu"),
    )

    assert transfer.dtype == torch.float32
    assert transfer.shape == (8, 8)
    assert set(torch.unique(transfer).tolist()).issubset({0.0, 1.0})
    assert transfer.min().item() == 0.0
    assert transfer.max().item() == 1.0


def test_phase_zero_transfer_uses_physical_fourier_cutoff() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    transfer = build_phase_zero_transfer(
        array_resolution=(8, 8),
        pixel_size=1.0,
        aperture_policy="full_slm_active_area",
        wavelength=1.0,
        focal_length=1.0,
        slm2_resolution=(4, 4),
        slm2_pixel_size=0.125,
        phase_mask_resolution=4,
        slm2_active_area_policy="center_square",
        device=torch.device("cpu"),
    )
    frequency_y, frequency_x = build_frequency_grid(
        (8, 8),
        pixel_size=1.0,
        device=torch.device("cpu"),
    )
    expected = (
        torch.sqrt(frequency_x.square() + frequency_y.square()) <= 0.25
    ).to(torch.float32)

    torch.testing.assert_close(transfer, expected)


def test_slm2_center_square_active_window_uses_phase_mask_resolution() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    active_size = slm2_active_window_size(
        phase_mask_resolution=512,
        slm2_resolution=(1200, 1920),
        slm2_pixel_size=8e-6,
        slm2_active_area_policy="center_square",
    )

    assert active_size == pytest.approx(512 * 8e-6)


def test_slm2_center_square_active_window_can_use_configured_slm_region() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    active_size = slm2_active_window_size(
        phase_mask_resolution=512,
        slm2_resolution=(1200, 1920),
        slm2_pixel_size=8e-6,
        slm2_active_area_policy="center_square",
        slm2_active_resolution=(1024, 1024),
    )

    assert active_size == pytest.approx(1024 * 8e-6)


def test_phase_zero_transfer_uses_512_center_square_cutoff_for_w638_f030() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    transfer = build_phase_zero_transfer(
        array_resolution=(512, 512),
        pixel_size=8e-6,
        aperture_policy="full_slm_active_area",
        wavelength=638e-9,
        focal_length=0.3,
        slm2_resolution=(1200, 1920),
        slm2_pixel_size=8e-6,
        phase_mask_resolution=512,
        slm2_active_area_policy="center_square",
        slm2_active_resolution=(512, 512),
        device=torch.device("cpu"),
    )
    frequency_y, frequency_x = build_frequency_grid(
        (512, 512),
        pixel_size=8e-6,
        device=torch.device("cpu"),
    )
    expected_cutoff = (0.5 * 512 * 8e-6) / (638e-9 * 0.3)
    frequency_radius = torch.sqrt(frequency_x.square() + frequency_y.square())

    assert expected_cutoff == pytest.approx(10700.10449320794)
    assert torch.all(transfer[frequency_radius <= expected_cutoff] == 1.0)
    assert torch.all(transfer[frequency_radius > expected_cutoff] == 0.0)


def test_phase_mask_mapping_uses_fourier_plane_coordinates() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    phase_mask = torch.full((4, 4), 2.0, dtype=torch.float32)

    mapped = map_phase_mask_to_fourier_grid(
        phase_mask,
        array_resolution=(8, 8),
        input_plane_pixel_size=1.0,
        wavelength=1.0,
        focal_length=1.0,
        slm2_resolution=(4, 4),
        slm2_pixel_size=0.125,
        slm2_active_area_policy="center_square",
        interpolation_policy="nearest",
        phase_wrap_policy="wrap_to_2pi",
        device=torch.device("cpu"),
    )
    frequency_y, frequency_x = build_frequency_grid(
        (8, 8),
        pixel_size=1.0,
        device=torch.device("cpu"),
    )
    inside_slm = (frequency_x.abs() <= 0.25) & (frequency_y.abs() <= 0.25)

    assert torch.all(mapped[inside_slm] == 2.0)
    assert torch.all(mapped[~inside_slm] == 0.0)


def test_phase_mask_mapping_uses_configured_slm_active_region_not_mask_resolution() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    phase_mask = torch.full((4, 4), 2.0, dtype=torch.float32)

    mapped = map_phase_mask_to_fourier_grid(
        phase_mask,
        array_resolution=(8, 8),
        input_plane_pixel_size=1.0,
        wavelength=1.0,
        focal_length=1.0,
        slm2_resolution=(8, 8),
        slm2_pixel_size=0.125,
        slm2_active_area_policy="center_square",
        slm2_active_resolution=(8, 8),
        interpolation_policy="nearest",
        phase_wrap_policy="wrap_to_2pi",
        device=torch.device("cpu"),
    )
    frequency_y, frequency_x = build_frequency_grid(
        (8, 8),
        pixel_size=1.0,
        device=torch.device("cpu"),
    )
    inside_slm = (frequency_x.abs() <= 0.5) & (frequency_y.abs() <= 0.5)

    assert torch.all(mapped[inside_slm] == 2.0)


def test_dense_camera_binning_averages_blocks() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    dense_intensity = torch.tensor(
        [
            [
                [
                    [1.0, 2.0, 3.0, 4.0],
                    [5.0, 6.0, 7.0, 8.0],
                    [9.0, 10.0, 11.0, 12.0],
                    [13.0, 14.0, 15.0, 16.0],
                ]
            ]
        ],
        dtype=torch.float32,
    )

    binned = bin_dense_camera_intensity(
        dense_intensity,
        factor=2,
        policy="average",
    )

    expected = torch.tensor([[[[3.5, 5.5], [11.5, 13.5]]]], dtype=torch.float32)
    torch.testing.assert_close(binned, expected)


@pytest.mark.parametrize("array_resolution", [(4,), (0, 4), (-1, 4), (True, 4), (4, 4.5)])
def test_frequency_grid_rejects_invalid_resolution(array_resolution: object) -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        build_frequency_grid(
            array_resolution,  # type: ignore[arg-type]
            pixel_size=0.5,
            device=torch.device("cpu"),
        )


@pytest.mark.parametrize("pixel_size", [0.0, -0.5, True])
def test_frequency_grid_rejects_invalid_pixel_size(pixel_size: object) -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        build_frequency_grid(
            (4, 4),
            pixel_size=pixel_size,  # type: ignore[arg-type]
            device=torch.device("cpu"),
        )


@pytest.mark.parametrize("array_resolution", [(4,), (0, 4), (-1, 4), (True, 4), (4, 4.5)])
def test_circular_aperture_rejects_invalid_resolution(array_resolution: object) -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        build_circular_aperture(
            array_resolution,  # type: ignore[arg-type]
            radius_fraction=0.5,
            device=torch.device("cpu"),
        )


@pytest.mark.parametrize("radius_fraction", [0.0, -0.1, 1.1])
def test_circular_aperture_rejects_invalid_radius_fraction(radius_fraction: float) -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        build_circular_aperture(
            (8, 8),
            radius_fraction=radius_fraction,
            device=torch.device("cpu"),
        )


@pytest.mark.parametrize("array_resolution", [(4,), (0, 4), (-1, 4), (True, 4), (4, 4.5)])
def test_phase_zero_transfer_rejects_invalid_resolution(array_resolution: object) -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        build_phase_zero_transfer(
            array_resolution=array_resolution,  # type: ignore[arg-type]
            pixel_size=1.0,
            aperture_policy="radius_0_50",
            wavelength=1.0,
            focal_length=1.0,
            slm2_resolution=(4, 4),
            slm2_pixel_size=1.0,
            phase_mask_resolution=4,
            slm2_active_area_policy="center_square",
            device=torch.device("cpu"),
        )


@pytest.mark.parametrize("pixel_size", [0.0, -1.0, True])
def test_phase_zero_transfer_rejects_invalid_pixel_size(pixel_size: object) -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        build_phase_zero_transfer(
            array_resolution=(8, 8),
            pixel_size=pixel_size,  # type: ignore[arg-type]
            aperture_policy="radius_0_50",
            wavelength=1.0,
            focal_length=1.0,
            slm2_resolution=(4, 4),
            slm2_pixel_size=1.0,
            phase_mask_resolution=4,
            slm2_active_area_policy="center_square",
            device=torch.device("cpu"),
        )


def test_phase_zero_transfer_rejects_unsupported_aperture_policy() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        build_phase_zero_transfer(
            array_resolution=(8, 8),
            pixel_size=1.0,
            aperture_policy="unknown_policy",
            wavelength=1.0,
            focal_length=1.0,
            slm2_resolution=(4, 4),
            slm2_pixel_size=1.0,
            phase_mask_resolution=4,
            slm2_active_area_policy="center_square",
            device=torch.device("cpu"),
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"aperture_radius_fourier": 0.0, "wavelength": 500e-9, "focal_length": 0.25},
        {"aperture_radius_fourier": -0.001, "wavelength": 500e-9, "focal_length": 0.25},
        {"aperture_radius_fourier": 0.001, "wavelength": 0.0, "focal_length": 0.25},
        {"aperture_radius_fourier": 0.001, "wavelength": 500e-9, "focal_length": -0.25},
    ],
)
def test_aperture_cutoff_rejects_invalid_physical_inputs(kwargs: dict[str, float]) -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        spatial_frequency_cutoff_aperture(**kwargs)


def test_phase_mask_mapping_rejects_non_2d_phase_mask() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        map_phase_mask_to_slm2(
            torch.zeros((1, 2, 2)),
            output_resolution=(4, 4),
            interpolation_policy="nearest",
            phase_wrap_policy="wrap_to_2pi",
        )


def test_phase_mask_mapping_rejects_unsupported_interpolation_policy() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        map_phase_mask_to_slm2(
            torch.zeros((2, 2)),
            output_resolution=(4, 4),
            interpolation_policy="area",
            phase_wrap_policy="wrap_to_2pi",
        )


def test_phase_mask_mapping_rejects_unsupported_phase_wrap_policy() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        map_phase_mask_to_slm2(
            torch.zeros((2, 2)),
            output_resolution=(4, 4),
            interpolation_policy="nearest",
            phase_wrap_policy="clip",
        )


@pytest.mark.parametrize("output_resolution", [(4,), (0, 4), (-1, 4), (True, 4), (4, 4.5)])
def test_phase_mask_mapping_rejects_invalid_output_resolution(output_resolution: object) -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        map_phase_mask_to_slm2(
            torch.zeros((2, 2)),
            output_resolution=output_resolution,  # type: ignore[arg-type]
            interpolation_policy="nearest",
            phase_wrap_policy="wrap_to_2pi",
        )


def test_dense_camera_binning_rejects_non_4d_tensor() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        bin_dense_camera_intensity(
            torch.ones((4, 4)),
            factor=2,
            policy="average",
        )


@pytest.mark.parametrize("factor", [0, -1, True])
def test_dense_camera_binning_rejects_invalid_factor(factor: object) -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        bin_dense_camera_intensity(
            torch.ones((1, 1, 4, 4)),
            factor=factor,  # type: ignore[arg-type]
            policy="average",
        )


def test_dense_camera_binning_rejects_unsupported_policy() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        bin_dense_camera_intensity(
            torch.ones((1, 1, 4, 4)),
            factor=2,
            policy="sum",
        )


def test_dense_camera_binning_rejects_spatial_size_not_divisible_by_factor() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    with pytest.raises(ValueError):
        bin_dense_camera_intensity(
            torch.ones((1, 1, 3, 4)),
            factor=2,
            policy="average",
        )


def test_theoretical_resolution_budget_records_units_and_fft_policy() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    config = OpticalBenchConfig(
        input_array_resolution=(512, 512),
        phase_mask_resolution=512,
    )

    budget = build_theoretical_resolution_budget(config)

    assert budget["input_array_resolution"] == [512, 512]
    assert budget["phase_mask_resolution"] == 512
    assert budget["slm1_resolution"] == [1200, 1920]
    assert budget["slm2_resolution"] == [1200, 1920]
    assert budget["camera_resolution"] == [2160, 3840]
    assert budget["camera_pixel_size"] == pytest.approx(2.9e-6)
    assert "camera_dense_pixel_size" not in budget
    assert "camera_binned_pixel_size" not in budget
    assert budget["fft_normalization_policy"] == "pytorch_default"
    assert budget["fft_shift_policy"] == "centered_frequency_grid"
    assert budget["spatial_frequency_unit"] == "cycles_per_meter"
    assert budget["process_arm_model"] == "compact_fourier_4f_equivalent"
    assert budget["input_nyquist_frequency"] == pytest.approx(1.0 / (2.0 * 8e-6))
    assert budget["camera_nyquist_frequency"] == pytest.approx(1.0 / (2.0 * 2.9e-6))
    assert budget["camera_nyquist_frequency"] > budget["input_nyquist_frequency"]
    assert budget["focal_length"] == pytest.approx(0.1)
    assert budget["slm2_active_resolution"] == [1024, 1024]
    assert budget["slm2_active_window_size"] == pytest.approx(1024 * 8e-6)
    assert budget["aperture_radius_fourier"] == pytest.approx(0.5 * 1024 * 8e-6)
    assert budget["aperture_cutoff_frequency"] == pytest.approx(
        (0.5 * 1024 * 8e-6) / (638e-9 * 0.1)
    )
    assert budget["fourier_plane_coordinate_scale"] == pytest.approx(638e-9 * 0.1)
    assert budget["fourier_plane_pixel_size_x"] == pytest.approx(
        638e-9 * 0.1 / (512 * 8e-6)
    )
    assert budget["fourier_plane_width"] == pytest.approx(638e-9 * 0.1 / 8e-6)


def test_spatial_frequency_cutoff_uses_cycles_per_meter_formula() -> None:
    """
    鏍￠獙鍏夊鍑犱綍濂戠害
    """
    cutoff = spatial_frequency_cutoff_aperture(
        aperture_radius_fourier=1.0e-3,
        wavelength=532e-9,
        focal_length=0.25,
    )

    assert cutoff == pytest.approx(1.0e-3 / (532e-9 * 0.25))

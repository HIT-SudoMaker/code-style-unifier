from __future__ import annotations

import math

import pytest
import torch
import torch.nn.functional as functional

from experiments.restoration.metrics import (
    contrast_transfer,
    energy_throughput,
    extract_center_image_region,
    grating_contrast_transfer,
    interference_visibility,
    interference_reconstruction_error,
    michelson_contrast,
    phase_intensity_ratio,
    point_response_fwhm,
    point_response_peak_sidelobe_ratio,
    psnr,
    ringing_index_from_edge,
    slanted_edge_intensity_mtf,
    ssim_global,
)


def test_extract_center_image_region_preserves_leading_axes() -> None:
    image = torch.arange(2 * 6 * 8, dtype=torch.float32).reshape(2, 6, 8)

    region = extract_center_image_region(
        image,
        region_resolution=(2, 4),
    )

    assert region.shape == (2, 2, 4)
    assert torch.equal(region, image[..., 2:4, 2:6])


def test_extract_center_image_region_rejects_an_oversized_region() -> None:
    with pytest.raises(ValueError, match="fit within"):
        extract_center_image_region(
            torch.zeros((4, 4), dtype=torch.float32),
            region_resolution=(5, 4),
        )


def test_point_response_fwhm_reports_width_above_half_max() -> None:
    """
    校验评估指标契约
    """
    image = torch.zeros((9, 9), dtype=torch.float32)
    image[4, 3:6] = torch.tensor([0.6, 1.0, 0.6])

    assert point_response_fwhm(image) == 3.0


def test_point_response_peak_sidelobe_ratio_excludes_peak_neighborhood() -> None:
    """
    校验评估指标契约
    """
    image = torch.zeros((9, 9), dtype=torch.float32)
    image[4, 4] = 10.0
    image[1, 1] = 2.0

    assert point_response_peak_sidelobe_ratio(
        image, exclusion_radius=1
    ) == pytest.approx(0.2)


@pytest.mark.parametrize("invalid_value", [math.nan, math.inf, -math.inf])
def test_point_response_fwhm_rejects_nonfinite_tensors(invalid_value: float) -> None:
    """
    校验评估指标契约
    """
    image = torch.zeros((9, 9), dtype=torch.float32)
    image[4, 4] = invalid_value

    with pytest.raises(ValueError, match="finite"):
        point_response_fwhm(image)


def test_energy_throughput_is_output_over_input_sum() -> None:
    """
    校验评估指标契约
    """
    input_intensity = torch.ones((2, 2), dtype=torch.float32)
    output_intensity = torch.full((2, 2), 2.0, dtype=torch.float32)

    assert energy_throughput(input_intensity, output_intensity) == 2.0


@pytest.mark.parametrize("invalid_value", [math.nan, math.inf, -math.inf])
def test_energy_throughput_rejects_nonfinite_tensors(invalid_value: float) -> None:
    """
    校验评估指标契约
    """
    input_intensity = torch.ones((2, 2), dtype=torch.float32)
    output_intensity = torch.full((2, 2), invalid_value, dtype=torch.float32)

    with pytest.raises(ValueError, match="finite"):
        energy_throughput(input_intensity, output_intensity)


def test_interference_reconstruction_error_is_zero_for_consistent_terms() -> None:
    """
    校验评估指标契约
    """
    reference = torch.full((2, 2), 1.0, dtype=torch.float32)
    process = torch.full((2, 2), 2.0, dtype=torch.float32)
    interference = torch.full((2, 2), 0.5, dtype=torch.float32)
    full = reference + process + interference

    assert (
        interference_reconstruction_error(full, reference, process, interference) == 0.0
    )


def test_phase_intensity_ratio_detects_near_cancellation() -> None:
    """
    校验评估指标契约
    """
    full = torch.full((4, 4), 0.1, dtype=torch.float32)
    reference = torch.ones((4, 4), dtype=torch.float32)
    process = torch.ones((4, 4), dtype=torch.float32)

    assert phase_intensity_ratio(full=full, reference=reference, process=process) < 0.1


def test_ringing_index_from_edge_is_nonnegative() -> None:
    """
    校验评估指标契约
    """
    profile = torch.tensor([0.0, 0.0, 1.2, 1.0, 1.0], dtype=torch.float32)

    assert ringing_index_from_edge(profile) > 0.0


@pytest.mark.parametrize("invalid_value", [math.nan, math.inf, -math.inf])
def test_ringing_index_from_edge_rejects_nonfinite_tensors(
    invalid_value: float,
) -> None:
    """
    校验评估指标契约
    """
    profile = torch.tensor([0.0, invalid_value, 1.0], dtype=torch.float32)

    with pytest.raises(ValueError, match="finite"):
        ringing_index_from_edge(profile)


def test_contrast_transfer_handles_zero_input_contrast() -> None:
    """
    校验评估指标契约
    """
    assert contrast_transfer(input_contrast=0.0, output_contrast=1.0) == 0.0


def test_michelson_contrast_and_grating_ctf_measure_contrast_loss() -> None:
    """
    校验评估指标契约
    """
    coordinate = torch.linspace(0.0, 2.0 * math.pi, steps=64, dtype=torch.float32)
    input_image = 0.5 + 0.5 * torch.sin(coordinate).repeat(64, 1)
    output_image = 0.5 + 0.25 * torch.sin(coordinate).repeat(64, 1)

    assert michelson_contrast(input_image) == pytest.approx(1.0, abs=2e-3)
    assert grating_contrast_transfer(input_image, output_image) == pytest.approx(
        0.5, abs=3e-3
    )


def test_slanted_edge_intensity_mtf_reports_finite_cutoff_metrics() -> None:
    """
    校验评估指标契约
    """
    coordinate_y = torch.arange(96, dtype=torch.float32) - 47.5
    coordinate_x = torch.arange(96, dtype=torch.float32) - 47.5
    grid_y, grid_x = torch.meshgrid(coordinate_y, coordinate_x, indexing="ij")
    edge = (grid_x + grid_y * math.tan(math.radians(5.0)) >= 0.0).to(torch.float32)

    result = slanted_edge_intensity_mtf(edge, angle_degrees=5.0, pixel_size=8e-6)

    assert 0.0 < result["mtf50_cycles_per_pixel"] <= 0.5
    assert result["mtf50_cycles_per_pixel"] <= result["mtf10_cycles_per_pixel"] <= 0.5
    assert result["mtf50_cycles_per_meter"] == pytest.approx(
        result["mtf50_cycles_per_pixel"] / 8e-6
    )
    assert 0.0 <= result["nyquist_response"] <= 1.0
    assert result["mtf_auc"] > 0.0


def test_slanted_edge_intensity_mtf_drops_after_blur() -> None:
    """
    校验评估指标契约
    """
    coordinate_y = torch.arange(96, dtype=torch.float32) - 47.5
    coordinate_x = torch.arange(96, dtype=torch.float32) - 47.5
    grid_y, grid_x = torch.meshgrid(coordinate_y, coordinate_x, indexing="ij")
    edge = (grid_x + grid_y * math.tan(math.radians(5.0)) >= 0.0).to(torch.float32)
    blurred = functional.avg_pool2d(
        edge.unsqueeze(0).unsqueeze(0),
        kernel_size=9,
        stride=1,
        padding=4,
    ).squeeze()

    sharp_result = slanted_edge_intensity_mtf(edge, angle_degrees=5.0)
    blurred_result = slanted_edge_intensity_mtf(blurred, angle_degrees=5.0)

    assert (
        blurred_result["mtf50_cycles_per_pixel"]
        < sharp_result["mtf50_cycles_per_pixel"]
    )
    assert blurred_result["nyquist_response"] < sharp_result["nyquist_response"]


@pytest.mark.parametrize(
    ("input_contrast", "output_contrast"),
    [
        (math.nan, 1.0),
        (math.inf, 1.0),
        (1.0, -math.inf),
        (True, 1.0),
        (1.0, object()),
    ],
)
def test_contrast_transfer_rejects_invalid_scalar_inputs(
    input_contrast: object,
    output_contrast: object,
) -> None:
    """
    校验评估指标契约
    """
    with pytest.raises(ValueError, match="finite real"):
        contrast_transfer(
            input_contrast=input_contrast,  # type: ignore[arg-type]
            output_contrast=output_contrast,  # type: ignore[arg-type]
        )


def test_psnr_and_ssim_have_expected_identity_values() -> None:
    """
    校验评估指标契约
    """
    image = torch.ones((8, 8), dtype=torch.float32)

    assert math.isinf(psnr(image, image))
    assert ssim_global(image, image) == 1.0


@pytest.mark.parametrize("metric", [psnr, ssim_global])
@pytest.mark.parametrize("invalid_value", [math.nan, math.inf, -math.inf])
def test_psnr_and_ssim_reject_nonfinite_tensors(
    metric: object, invalid_value: float
) -> None:
    """
    校验评估指标契约
    """
    prediction = torch.zeros((4, 4), dtype=torch.float32)
    target = torch.zeros((4, 4), dtype=torch.float32)
    prediction[0, 0] = invalid_value

    with pytest.raises(ValueError, match="finite"):
        metric(prediction, target)  # type: ignore[operator]


def test_phase_intensity_ratio_is_full_over_reference_plus_process() -> None:
    """
    校验评估指标契约
    """
    full = torch.full((4, 4), 3.0, dtype=torch.float32)
    reference = torch.full((4, 4), 2.0, dtype=torch.float32)
    process = torch.full((4, 4), 4.0, dtype=torch.float32)

    assert phase_intensity_ratio(
        full=full, reference=reference, process=process
    ) == pytest.approx(3.0 / 6.0)


def test_interference_reconstruction_error_supports_reviewed_tolerance() -> None:
    """
    校验评估指标契约
    """
    reference = torch.ones((4, 4), dtype=torch.float32)
    process = torch.ones((4, 4), dtype=torch.float32)
    interference = torch.zeros((4, 4), dtype=torch.float32)
    full = reference + process + 5e-6

    assert interference_reconstruction_error(
        full,
        reference,
        process,
        interference,
        atol=1e-5,
        rtol=1e-5,
    ) == pytest.approx(0.0)


def test_interference_visibility_measures_cross_term_strength() -> None:
    """
    校验评估指标契约
    """
    reference = torch.ones((4, 4), dtype=torch.float32)
    process = torch.ones((4, 4), dtype=torch.float32)
    interference = torch.full((4, 4), 0.5, dtype=torch.float32)

    assert interference_visibility(
        reference=reference,
        process=process,
        interference=interference,
    ) == pytest.approx(0.25)

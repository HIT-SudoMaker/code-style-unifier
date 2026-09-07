import pytest
import torch

from layers import LensLayer


@pytest.mark.parametrize("wavelength", [True, float("nan"), float("inf"), "532e-9"])
def test_lens_layer_rejects_invalid_wavelength_values(wavelength: object) -> None:
    """
    验证透镜层拒绝非法工作波长
    """
    with pytest.raises(ValueError, match="工作波长"):
        LensLayer(wavelength, 0.1, 20e-6, (8, 8))


@pytest.mark.parametrize("focal_length", [True, float("nan"), float("inf"), "0.1"])
def test_lens_layer_rejects_invalid_focal_length_values(focal_length: object) -> None:
    """
    验证透镜层拒绝非法焦距
    """
    with pytest.raises(ValueError, match="透镜焦距"):
        LensLayer(532e-9, focal_length, 20e-6, (8, 8))


@pytest.mark.parametrize("pixel_size", [True, float("nan"), float("inf"), "20e-6"])
def test_lens_layer_rejects_invalid_pixel_size_values(pixel_size: object) -> None:
    """
    验证透镜层拒绝非法像素尺寸
    """
    with pytest.raises(ValueError, match="像素尺寸"):
        LensLayer(532e-9, 0.1, pixel_size, (8, 8))


def test_lens_layer_rejects_resolution_mismatch() -> None:
    layer = LensLayer(532e-9, 0.1, 20e-6, (8, 8))
    input_field = torch.ones(1, 1, 4, 8, dtype=torch.complex64)

    with pytest.raises(ValueError, match="分辨率"):
        layer(input_field)


def test_lens_layer_rejects_invalid_resolution_type() -> None:
    with pytest.raises(ValueError, match="长度为2"):
        LensLayer(532e-9, 0.1, 20e-6, 8)


def test_lens_layer_rejects_non_integer_resolution_values() -> None:
    with pytest.raises(ValueError, match="整数"):
        LensLayer(532e-9, 0.1, 20e-6, (8.9, 8.1))


def test_lens_layer_rejects_boolean_resolution_values() -> None:
    with pytest.raises(ValueError, match="布尔值"):
        LensLayer(532e-9, 0.1, 20e-6, (True, 8))


def test_lens_layer_rejects_zero_focal_length() -> None:
    with pytest.raises(ValueError, match="非零"):
        LensLayer(532e-9, 0.0, 20e-6, (8, 8))


def test_lens_layer_supports_converging_and_diverging_focal_lengths() -> None:
    converging = LensLayer(532e-9, 0.1, 20e-6, (8, 8))
    diverging = LensLayer(532e-9, -0.1, 20e-6, (8, 8))

    converging_mask = torch.exp(1j * converging.get_lens_phase_information())
    diverging_mask = torch.exp(1j * diverging.get_lens_phase_information())

    assert torch.allclose(diverging_mask, converging_mask.conj(), atol=1e-6, rtol=1e-6)


def test_lens_layer_rejects_device_mismatch() -> None:
    layer = LensLayer(532e-9, 0.1, 20e-6, (8, 8))
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64, device="meta")

    with pytest.raises(ValueError, match="同一设备"):
        layer(input_field)


def test_lens_layer_rejects_non_contract_complex_dtype() -> None:
    layer = LensLayer(532e-9, 0.1, 20e-6, (8, 8))
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex128)

    with pytest.raises(ValueError, match="complex64"):
        layer(input_field)


def test_lens_layer_returns_isolated_phase_tensor() -> None:
    layer = LensLayer(532e-9, 0.1, 20e-6, (8, 8))

    phase = layer.get_lens_phase_information()
    expected = phase.clone()

    phase.zero_()

    assert torch.allclose(layer.get_lens_phase_information(), expected)


def test_lens_layer_defaults_to_single_precision_contract() -> None:
    layer = LensLayer(532e-9, 0.1, 20e-6, (8, 8))
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    output_field = layer(input_field)

    assert layer.wavelength.dtype == torch.float32
    assert layer.focal_length.dtype == torch.float32
    assert layer.pixel_size.dtype == torch.float32
    assert layer.wavenumber.dtype == torch.float32
    assert layer.lens_phase.dtype == torch.float32
    assert output_field.dtype == torch.complex64


def test_lens_layer_defaults_are_independent_of_global_default_dtype() -> None:
    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    try:
        layer = LensLayer(532e-9, 0.1, 20e-6, (8, 8))
    finally:
        torch.set_default_dtype(previous_dtype)

    assert layer.wavelength.dtype == torch.float32
    assert layer.focal_length.dtype == torch.float32
    assert layer.pixel_size.dtype == torch.float32
    assert layer.wavenumber.dtype == torch.float32
    assert layer.lens_phase.dtype == torch.float32


def test_lens_layer_keeps_single_precision_contract_after_dtype_migration() -> None:
    layer = LensLayer(532e-9, 0.1, 20e-6, (8, 8))
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)
    expected_phase = layer.get_lens_phase_information()

    layer.to(dtype=torch.float64)
    output_field = layer(input_field)

    assert layer.wavelength.dtype == torch.float32
    assert layer.focal_length.dtype == torch.float32
    assert layer.pixel_size.dtype == torch.float32
    assert layer.wavenumber.dtype == torch.float32
    assert layer.lens_phase.dtype == torch.float32
    assert output_field.dtype == torch.complex64
    assert torch.allclose(layer.get_lens_phase_information(), expected_phase)


def test_lens_layer_complex_mask_matches_standard_thin_lens_formula() -> None:
    wavelength = 532e-9
    focal_length = 0.1
    pixel_size = 20e-6
    height, width = 6, 8
    layer = LensLayer(wavelength, focal_length, pixel_size, (height, width))

    y_coords = (torch.arange(height, dtype=torch.float32) - (height - 1) / 2.0) * pixel_size
    x_coords = (torch.arange(width, dtype=torch.float32) - (width - 1) / 2.0) * pixel_size
    y_grid, x_grid = torch.meshgrid(y_coords, x_coords, indexing="ij")

    radius_squared = x_grid.square() + y_grid.square()
    expected_phase = -(2.0 * torch.pi / wavelength) * radius_squared / (2.0 * focal_length)
    expected_mask = torch.exp(1j * expected_phase)
    actual_mask = torch.exp(1j * layer.get_lens_phase_information())

    assert torch.allclose(actual_mask, expected_mask, atol=1e-6, rtol=1e-6)


def test_lens_layer_repr_contains_key_configuration() -> None:
    layer = LensLayer(532e-9, 0.12, 20e-6, (16, 12))

    layer_repr = repr(layer)

    assert "wavelength=5.32e-07" in layer_repr
    assert "focal_length=0.12" in layer_repr
    assert "pixel_size=2e-05" in layer_repr
    assert "array_resolution=(16, 12)" in layer_repr

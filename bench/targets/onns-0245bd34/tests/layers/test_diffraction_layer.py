import pytest
import torch

from layers import DiffractionLayer


@pytest.mark.parametrize("wavelength", [True, float("nan"), float("inf"), "532e-9"])
def test_diffraction_layer_rejects_invalid_wavelength_values(wavelength: object) -> None:
    """
    验证衍射层拒绝非法工作波长。
    """
    with pytest.raises(ValueError, match="工作波长"):
        DiffractionLayer(wavelength, 20e-6, (8, 8))


@pytest.mark.parametrize("pixel_size", [True, float("nan"), float("inf"), "20e-6"])
def test_diffraction_layer_rejects_invalid_pixel_size_values(pixel_size: object) -> None:
    """
    验证衍射层拒绝非法像素尺寸。
    """
    with pytest.raises(ValueError, match="像素尺寸"):
        DiffractionLayer(532e-9, pixel_size, (8, 8))


@pytest.mark.parametrize("is_cache_enabled", [1, 0, "false", None])
def test_diffraction_layer_rejects_non_boolean_cache_flag(is_cache_enabled: object) -> None:
    """
    验证衍射层拒绝非布尔缓存开关。
    """
    with pytest.raises(ValueError, match="is_cache_enabled"):
        DiffractionLayer(532e-9, 20e-6, (8, 8), is_cache_enabled=is_cache_enabled)


@pytest.mark.parametrize("propagation_distance", [True, float("nan"), float("inf"), "0.01"])
def test_diffraction_layer_rejects_invalid_propagation_distance_values(propagation_distance: object) -> None:
    """
    验证衍射层前向传播拒绝非法传播距离。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8))
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    with pytest.raises(ValueError, match="传播距离"):
        layer(input_field, propagation_distance)


@pytest.mark.parametrize("propagation_distance", [True, float("nan"), float("inf"), "0.01"])
def test_diffraction_layer_information_rejects_invalid_distance_values(propagation_distance: object) -> None:
    """
    验证传递函数信息接口拒绝非法传播距离。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8))

    with pytest.raises(ValueError, match="传播距离"):
        layer.get_transfer_function_information(propagation_distance, "complex")


def test_diffraction_layer_rejects_non_complex_input() -> None:
    """
    验证 DiffractionLayer 拒绝非复数输入。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8))
    input_field = torch.zeros(1, 1, 8, 8, dtype=torch.float32)

    with pytest.raises(ValueError, match="复数"):
        layer(input_field, 0.01)


def test_diffraction_layer_rejects_non_contract_complex_dtype() -> None:
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8))
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex128)

    with pytest.raises(ValueError, match="complex64"):
        layer(input_field, 0.01)


def test_diffraction_layer_rejects_invalid_resolution_type() -> None:
    """
    验证 DiffractionLayer 拒绝非法分辨率类型。
    """
    with pytest.raises(ValueError, match="分辨率"):
        DiffractionLayer(532e-9, 20e-6, 8)


def test_diffraction_layer_rejects_non_integer_resolution_values() -> None:
    """
    验证 DiffractionLayer 拒绝非整数分辨率值。
    """
    with pytest.raises(ValueError, match="整数"):
        DiffractionLayer(532e-9, 20e-6, (8.9, 8.1))


def test_diffraction_layer_rejects_boolean_resolution_values() -> None:
    """
    验证 DiffractionLayer 拒绝布尔分辨率值。
    """
    with pytest.raises(ValueError, match="布尔"):
        DiffractionLayer(532e-9, 20e-6, (True, 8))


def test_diffraction_layer_rejects_non_positive_distance() -> None:
    """
    验证 DiffractionLayer 拒绝非正传播距离。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8))
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    with pytest.raises(ValueError, match="正数"):
        layer(input_field, 0.0)


def test_diffraction_layer_extra_repr_contains_key_configuration() -> None:
    layer = DiffractionLayer(
        wavelength=532e-9,
        pixel_size=2e-6,
        array_resolution=(16, 16),
        is_cache_enabled=True,
    )

    extra_repr = layer.extra_repr()

    assert "wavelength=5.32e-07" in extra_repr
    assert "pixel_size=2e-06" in extra_repr
    assert "array_resolution=(16, 16)" in extra_repr
    assert "is_cache_enabled=True" in extra_repr


def test_diffraction_layer_defaults_to_single_precision_contract() -> None:
    layer = DiffractionLayer(
        wavelength=532e-9,
        pixel_size=20e-6,
        array_resolution=(8, 8),
        is_cache_enabled=True,
    )
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    output_field = layer(input_field, 0.01)
    transfer_function = layer.get_transfer_function_information(0.01, "complex")

    assert layer.wavelength.dtype == torch.float32
    assert layer.wavenumber.dtype == torch.float32
    assert layer.pixel_size.dtype == torch.float32
    assert layer.frequency_grid_squared.dtype == torch.float32
    assert layer.frequency_mask.dtype == torch.bool
    assert output_field.dtype == torch.complex64
    assert transfer_function.dtype == torch.complex64


def test_diffraction_layer_defaults_are_independent_of_global_default_dtype() -> None:
    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    try:
        layer = DiffractionLayer(
            wavelength=532e-9,
            pixel_size=20e-6,
            array_resolution=(8, 8),
            is_cache_enabled=True,
        )
    finally:
        torch.set_default_dtype(previous_dtype)

    assert layer.wavelength.dtype == torch.float32
    assert layer.wavenumber.dtype == torch.float32
    assert layer.pixel_size.dtype == torch.float32
    assert layer.frequency_grid_squared.dtype == torch.float32


def test_diffraction_layer_forward_matches_public_transfer_function() -> None:
    layer = DiffractionLayer(
        wavelength=532e-9,
        pixel_size=20e-6,
        array_resolution=(8, 8),
        is_cache_enabled=False,
    )
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)
    propagation_distance = 0.01

    output_field = layer(input_field, propagation_distance)
    wavelength = layer.wavelength.detach().to(dtype=torch.float32)
    pixel_size = layer.pixel_size.detach().to(dtype=torch.float32)
    wavenumber = 2.0 * torch.pi / wavelength
    frequency_u = torch.fft.fftshift(
        torch.fft.fftfreq(8, d=pixel_size.item(), dtype=pixel_size.dtype)
    )
    frequency_v = torch.fft.fftshift(
        torch.fft.fftfreq(8, d=pixel_size.item(), dtype=pixel_size.dtype)
    )
    frequency_u_grid, frequency_v_grid = torch.meshgrid(
        frequency_u,
        frequency_v,
        indexing="ij",
    )
    frequency_grid_squared = (
        frequency_u_grid.square() + frequency_v_grid.square() + 1e-10
    )
    propagation_factor = torch.clamp(
        1.0 - wavelength.square() * frequency_grid_squared,
        min=0.0,
    ).to(torch.complex64)
    transfer_function = torch.exp(
        1j
        * wavenumber.to(torch.complex64)
        * torch.sqrt(propagation_factor)
        * propagation_distance
    ) * (frequency_grid_squared <= (1.0 / wavelength.item()) ** 2)
    expected = torch.fft.ifft2(
        torch.fft.ifftshift(
            torch.fft.fftshift(torch.fft.fft2(input_field), dim=(-2, -1))
            * transfer_function,
            dim=(-2, -1),
        )
    )

    assert torch.allclose(output_field, expected)


def test_diffraction_layer_extra_repr_preserves_cache_state() -> None:
    layer = DiffractionLayer(
        wavelength=532e-9,
        pixel_size=2e-6,
        array_resolution=(16, 16),
        is_cache_enabled=True,
    )
    input_field = torch.ones(1, 1, 16, 16, dtype=torch.complex64)

    layer(input_field, 0.01)
    cache_statistics_before = layer.get_cache_statistics()

    _ = layer.extra_repr()

    assert layer.get_cache_statistics() == cache_statistics_before

    layer(input_field, 0.01)
    assert layer.get_cache_statistics()["hits"] == cache_statistics_before["hits"] + 1


def test_diffraction_layer_cache_is_scoped_by_distance() -> None:
    """
    验证 DiffractionLayer 缓存按传播距离区分。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8), is_cache_enabled=True)
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    layer(input_field, 0.01)
    layer(input_field, 0.02)

    assert layer.get_cache_statistics()["entries"] == 2


def test_diffraction_layer_cache_keeps_distinct_close_distances() -> None:
    """
    验证 DiffractionLayer 不会合并非常接近但不同的传播距离。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8), is_cache_enabled=True)
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    layer(input_field, 0.01)
    layer(input_field, 0.01000004)

    assert layer.get_cache_statistics()["entries"] == 2


def test_diffraction_layer_cache_keeps_at_most_ten_entries() -> None:
    """
    验证 DiffractionLayer 缓存最多保留 10 条记录。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8), is_cache_enabled=True)
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    for index in range(11):
        distance = 0.01 + index * 0.001
        layer(input_field, distance)

    assert layer.get_cache_statistics()["entries"] == 10


def test_diffraction_layer_keeps_single_precision_contract_after_dtype_migration() -> None:
    """
    验证 DiffractionLayer 在 dtype 迁移后仍保持单精度契约。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8), is_cache_enabled=True)
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    layer(input_field, 0.01)
    assert layer.get_cache_statistics()["entries"] == 1

    layer.to(dtype=torch.float64)

    assert layer.get_cache_statistics()["entries"] == 0
    assert layer.wavelength.dtype == torch.float32
    assert layer.wavenumber.dtype == torch.float32
    assert layer.pixel_size.dtype == torch.float32
    assert layer.frequency_grid_squared.dtype == torch.float32

    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)
    layer(input_field, 0.01)

    assert layer.get_cache_statistics()["entries"] == 1


def test_diffraction_layer_rebuilds_grid_and_clears_cache_after_state_load() -> None:
    source = DiffractionLayer(532e-9, 2e-6, (16, 16), is_cache_enabled=True)
    loaded = DiffractionLayer(633e-9, 3e-6, (16, 16), is_cache_enabled=True)
    fresh = DiffractionLayer(532e-9, 2e-6, (16, 16), is_cache_enabled=True)
    input_field = torch.ones(1, 1, 16, 16, dtype=torch.complex64)

    loaded(input_field, 0.01)
    assert loaded.get_cache_statistics()["entries"] == 1

    loaded.load_state_dict(source.state_dict())

    assert loaded.get_cache_statistics()["entries"] == 0
    assert torch.allclose(
        loaded(input_field, 0.01),
        fresh(input_field, 0.01),
        atol=1e-6,
        rtol=1e-6,
    )


def test_diffraction_layer_reports_cache_hits_and_misses() -> None:
    """
    验证 DiffractionLayer 正确统计缓存命中和未命中次数。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8), is_cache_enabled=True)
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)
    layer(input_field, 0.01)
    assert layer.get_cache_statistics()["misses"] == 1
    layer(input_field, 0.01)
    assert layer.get_cache_statistics()["hits"] == 1


def test_diffraction_layer_cache_statistics_use_explicit_enabled_state_key() -> None:
    """
    验证 DiffractionLayer 缓存统计使用显式状态键。
    """
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8), is_cache_enabled=True)

    cache_statistics = layer.get_cache_statistics()

    assert cache_statistics["is_enabled"] is True
    assert "enabled" not in cache_statistics


def test_diffraction_layer_returns_isolated_transfer_function_tensor() -> None:
    layer = DiffractionLayer(532e-9, 20e-6, (8, 8), is_cache_enabled=True)

    transfer_function = layer.get_transfer_function_information(0.01, "complex")
    expected = transfer_function.clone()

    transfer_function.zero_()

    assert torch.allclose(
        layer.get_transfer_function_information(0.01, "complex"),
        expected,
    )


def test_diffraction_layer_propagates_discrete_plane_wave_by_analytic_phase() -> None:
    layer = DiffractionLayer(
        wavelength=532e-9,
        pixel_size=10e-6,
        array_resolution=(32, 32),
        is_cache_enabled=False,
    )
    distance = 0.003
    cycles = 3
    x_coordinates = torch.arange(32, dtype=torch.float32)
    plane_wave = torch.exp(1j * 2.0 * torch.pi * cycles * x_coordinates / 32)
    input_field = plane_wave.expand(32, 32).unsqueeze(0).unsqueeze(0)

    output_field = layer(input_field, distance)

    spatial_frequency = cycles / (32 * layer.pixel_size.item())
    expected_phase = (
        layer.wavenumber.item()
        * distance
        * (1.0 - (layer.wavelength.item() * spatial_frequency) ** 2) ** 0.5
    )
    expected_field = input_field * torch.exp(
        torch.tensor(1j * expected_phase, dtype=torch.complex64)
    )

    assert torch.allclose(output_field, expected_field, atol=2e-5, rtol=2e-5)


def test_diffraction_layer_plane_wave_energy_is_conserved() -> None:
    layer = DiffractionLayer(
        wavelength=532e-9,
        pixel_size=10e-6,
        array_resolution=(32, 32),
        is_cache_enabled=False,
    )
    x_coordinates = torch.arange(32, dtype=torch.float32)
    y_coordinates = torch.arange(32, dtype=torch.float32)
    y_grid, x_grid = torch.meshgrid(y_coordinates, x_coordinates, indexing="ij")
    input_field = torch.exp(
        1j * 2.0 * torch.pi * (2 * x_grid + y_grid) / 32
    ).unsqueeze(0).unsqueeze(0)

    output_field = layer(input_field, 0.004)

    input_energy = torch.sum(torch.abs(input_field) ** 2)
    output_energy = torch.sum(torch.abs(output_field) ** 2)
    assert torch.isclose(output_energy, input_energy, rtol=2e-6, atol=2e-6)

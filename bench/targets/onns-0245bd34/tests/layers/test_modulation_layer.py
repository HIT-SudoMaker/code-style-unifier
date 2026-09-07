import pytest
import torch

from layers import ModulationLayer


def test_modulation_layer_rejects_non_complex_input() -> None:
    layer = ModulationLayer((8, 8))
    input_field = torch.zeros(1, 1, 8, 8, dtype=torch.float32)

    with pytest.raises(ValueError, match="复数"):
        layer(input_field)


def test_modulation_layer_rejects_invalid_resolution_type() -> None:
    with pytest.raises(ValueError, match="长度为2"):
        ModulationLayer(8)


def test_modulation_layer_rejects_non_integer_resolution_values() -> None:
    with pytest.raises(ValueError, match="整数"):
        ModulationLayer((8.9, 8.1))


def test_modulation_layer_rejects_boolean_resolution_values() -> None:
    with pytest.raises(ValueError, match="布尔值"):
        ModulationLayer((True, 8))


def test_modulation_layer_rejects_device_mismatch() -> None:
    layer = ModulationLayer((8, 8))
    input_field = torch.zeros(1, 1, 8, 8, dtype=torch.complex64, device="meta")

    with pytest.raises(ValueError, match="同一设备"):
        layer(input_field)


def test_modulation_layer_rejects_non_contract_complex_dtype() -> None:
    layer = ModulationLayer((8, 8))
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex128)

    with pytest.raises(ValueError, match="complex64"):
        layer(input_field)


def test_modulation_layer_repr_contains_key_configuration() -> None:
    layer = ModulationLayer(
        (16, 12),
        phase_parameterization="direct",
        phase_initialization="zeros",
    )

    layer_repr = repr(layer)

    assert "array_resolution=(16, 12)" in layer_repr
    assert "phase_parameterization=direct" in layer_repr
    assert "phase_initialization=zeros" in layer_repr


def test_modulation_layer_defaults_to_single_precision_contract() -> None:
    layer = ModulationLayer((8, 8))
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    output_field = layer(input_field)

    assert layer.modulation_phase.dtype == torch.float32
    assert layer.get_modulation_phase_information().dtype == torch.float32
    assert output_field.dtype == torch.complex64


@pytest.mark.parametrize("phase_initialization", ["normal", "uniform", "zeros"])
def test_modulation_layer_defaults_are_independent_of_global_default_dtype(
    phase_initialization: str,
) -> None:
    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    try:
        layer = ModulationLayer((8, 8), phase_initialization=phase_initialization)
    finally:
        torch.set_default_dtype(previous_dtype)

    assert layer.modulation_phase.dtype == torch.float32
    assert layer.get_modulation_phase_information().dtype == torch.float32


def test_modulation_layer_keeps_single_precision_contract_after_dtype_migration() -> None:
    layer = ModulationLayer((8, 8), phase_initialization="zeros")
    input_field = torch.ones(1, 1, 8, 8, dtype=torch.complex64)

    layer(input_field).imag.sum().backward()
    assert layer.modulation_phase.grad is not None

    layer.to(dtype=torch.float64)
    output_field = layer(input_field)

    assert layer.modulation_phase.dtype == torch.float32
    assert layer.modulation_phase.grad.dtype == torch.float32
    assert layer.get_modulation_phase_information().dtype == torch.float32
    assert output_field.dtype == torch.complex64


def test_modulation_layer_direct_parameterization_returns_wrapped_effective_phase() -> None:
    layer = ModulationLayer(
        (1, 4),
        phase_parameterization="direct",
        phase_initialization="zeros",
    )
    raw_phase = torch.tensor([[-0.25, 0.0, 0.5, 1.25]])
    with torch.no_grad():
        layer.modulation_phase.copy_(raw_phase)

    effective_phase = layer.get_modulation_phase_information()

    assert torch.allclose(effective_phase, torch.remainder(raw_phase * 2 * torch.pi, 2 * torch.pi))


def test_modulation_layer_uniform_initialization_uses_unit_interval() -> None:
    torch.manual_seed(0)
    layer = ModulationLayer(
        (8, 8),
        phase_parameterization="direct",
        phase_initialization="uniform",
    )

    assert torch.all(layer.modulation_phase >= 0)
    assert torch.all(layer.modulation_phase < 1)


def test_modulation_layer_rejects_unknown_phase_parameterization() -> None:
    with pytest.raises(ValueError, match="phase_parameterization"):
        ModulationLayer((8, 8), phase_parameterization="unsupported")


def test_modulation_layer_rejects_unknown_phase_initialization() -> None:
    with pytest.raises(ValueError, match="phase_initialization"):
        ModulationLayer((8, 8), phase_initialization="unsupported")

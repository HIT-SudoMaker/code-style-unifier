
from __future__ import annotations

from collections.abc import Callable
import copy

import pytest
import torch

from chromatix_next.optics import (
    Assembly,
    OpticalField,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.element import (
    AmplitudeTransmissionMap,
    CircularPupil,
    IdealThinLens,
    OpticalPathModulation,
    SquarePupil,
)
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave

SAMPLE_COUNTS = (8, 8)


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=SAMPLE_COUNTS,
        sample_spacing=(1.5e-6, 1.5e-6),
    )


def _source(
    *,
    relative_amplitude: float | torch.nn.Parameter = 1.0,
) -> PlaneWave:
    return PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=532.0e-9),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=relative_amplitude,
    )


def _field_with_structure() -> OpticalField:
    field = _source()(_grid())
    coordinate_y = torch.linspace(
        -5.25e-6,
        5.25e-6,
        SAMPLE_COUNTS[0],
        dtype=torch.float64,
    )
    coordinate_x = torch.linspace(
        -5.25e-6,
        5.25e-6,
        SAMPLE_COUNTS[1],
        dtype=torch.float64,
    )
    position_y, position_x = torch.meshgrid(
        coordinate_y,
        coordinate_x,
        indexing="ij",
    )
    amplitude = torch.exp(
        -(position_y.square() + position_x.square()) / (3.0e-6**2)
    )
    envelope = torch.complex(
        amplitude,
        0.15 * amplitude * position_x / 5.25e-6,
    ).reshape(1, 1, *SAMPLE_COUNTS)
    structured = copy.copy(field)
    object.__setattr__(structured, "envelope", envelope)
    return structured


def _carrier(
    value: OpticalField | tuple[OpticalField, OpticalField],
) -> torch.Tensor:
    if isinstance(value, tuple):
        return value[0].envelope
    return value.envelope


def _trainable_case(
    case_name: str,
) -> tuple[
    torch.nn.Module,
    tuple[object, ...],
    torch.nn.Parameter,
]:
    grid = _grid()
    field = _field_with_structure()
    if case_name == "plane_wave":
        parameter = torch.nn.Parameter(torch.tensor(0.8, dtype=torch.float64))
        return _source(relative_amplitude=parameter), (grid,), parameter
    if case_name == "amplitude_transmission":
        parameter = torch.nn.Parameter(
            torch.full(SAMPLE_COUNTS, 0.7, dtype=torch.float64)
        )
        return (
            AmplitudeTransmissionMap(
                grid=grid,
                amplitude_transmission=parameter,
            ),
            (field,),
            parameter,
        )
    if case_name == "optical_path_modulation":
        parameter = torch.nn.Parameter(
            torch.full(SAMPLE_COUNTS, 70.0e-9, dtype=torch.float64)
        )
        return (
            OpticalPathModulation(
                grid=grid,
                optical_path_variation=parameter,
            ),
            (field,),
            parameter,
        )
    if case_name == "ideal_thin_lens":
        parameter = torch.nn.Parameter(torch.tensor(15.0e-3, dtype=torch.float64))
        return IdealThinLens(grid=grid, focal_length=parameter), (field,), parameter
    if case_name == "scalar_angular_spectrum":
        parameter = torch.nn.Parameter(torch.tensor(80.0e-6, dtype=torch.float64))
        return ScalarAngularSpectrum(axial_distance=parameter), (field,), parameter
    raise AssertionError(case_name)


@pytest.mark.parametrize(
    "case_name",
    (
        "plane_wave",
        "amplitude_transmission",
        "optical_path_modulation",
        "ideal_thin_lens",
        "scalar_angular_spectrum",
    ),
)
def test_trainable_component_state_remains_in_the_forward_graph(
    case_name: str,
) -> None:
    """
    可训练物理状态由 Component 持有，真实 forward 对该 Parameter 保留有限非零梯度
    """
    component, inputs, parameter = _trainable_case(case_name)

    result = component(*inputs)
    carrier = _carrier(result)
    if case_name == "scalar_angular_spectrum":
        objective = carrier.abs().square()[..., 2, 5].sum()
    else:
        objective = carrier.real.sum() + 0.37 * carrier.imag.sum()
    objective.backward()

    assert any(owned is parameter for owned in component.parameters())
    assert parameter.grad is not None
    assert bool(torch.isfinite(parameter.grad).all())
    assert bool(torch.count_nonzero(parameter.grad))


def _cached_components() -> tuple[torch.nn.Module, ...]:
    grid = _grid()
    return (
        OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.zeros(
                SAMPLE_COUNTS,
                dtype=torch.float64,
            ),
        ),
        CircularPupil(grid=grid, radius=4.0e-6),
        SquarePupil(grid=grid, width=6.0e-6),
        IdealThinLens(grid=grid, focal_length=15.0e-3),
        ScalarAngularSpectrum(axial_distance=80.0e-6),
    )


def _tensor_state(
    module: torch.nn.Module,
) -> dict[str, tuple[int, torch.device, torch.dtype, torch.Size]]:
    return {
        name: (id(tensor), tensor.device, tensor.dtype, tensor.shape)
        for name, tensor in module.named_buffers()
        if tensor is not None
    }


def _persistent_state(
    module: torch.nn.Module,
) -> dict[str, torch.Tensor]:
    return {
        name: tensor.detach().clone()
        for name, tensor in module.state_dict().items()
    }


@pytest.mark.parametrize(
    "component",
    _cached_components(),
    ids=(
        "optical_path_modulation",
        "circular_pupil",
        "square_pupil",
        "ideal_thin_lens",
        "scalar_angular_spectrum",
    ),
)
def test_meta_preflight_restores_state_and_warm_forward_storage(
    component: torch.nn.Module,
) -> None:
    """
    Assembly 的 meta 预检重放真实 forward，但不得替换 Parameter、Buffer 或热缓存
    """
    grid = _grid()
    source = _source()
    field = source(grid)
    expected = component(field)
    assert isinstance(expected, OpticalField)
    parameter_identities = tuple(id(parameter) for parameter in component.parameters())
    persistent_before = _persistent_state(component)
    tensor_state_before = _tensor_state(component)

    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(component, name="component")
    assembly.connect(source, component)
    assembly.expose(component, name="field")

    assert assembly.check() is None

    actual = component(field)
    assert isinstance(actual, OpticalField)
    assert tuple(id(parameter) for parameter in component.parameters()) == (
        parameter_identities
    )
    assert _tensor_state(component) == tensor_state_before
    assert persistent_before.keys() == component.state_dict().keys()
    for name, expected_tensor in persistent_before.items():
        assert torch.equal(component.state_dict()[name], expected_tensor)
    assert actual.envelope.shape == expected.envelope.shape
    assert actual.envelope.dtype == expected.envelope.dtype
    assert torch.equal(actual.envelope, expected.envelope)


@pytest.mark.parametrize(
    "component_factory",
    (
        lambda grid: OpticalPathModulation(
            grid=grid,
            optical_path_variation=torch.zeros(
                SAMPLE_COUNTS,
                dtype=torch.float64,
            ),
        ),
        lambda grid: CircularPupil(grid=grid, radius=4.0e-6),
        lambda grid: SquarePupil(grid=grid, width=6.0e-6),
        lambda grid: IdealThinLens(grid=grid, focal_length=15.0e-3),
        lambda grid: ScalarAngularSpectrum(axial_distance=80.0e-6),
    ),
)
def test_state_dict_round_trip_preserves_forward_shape_dtype_and_value(
    component_factory: Callable[[SpatialGrid], torch.nn.Module],
) -> None:
    """
    固定物理状态通过 PyTorch state_dict 往返后保持 forward 的形状、dtype 与数值
    """
    grid = _grid()
    field = _field_with_structure()
    expected_component = component_factory(grid)
    restored_component = component_factory(grid)
    restored_component.load_state_dict(expected_component.state_dict())

    expected = expected_component(field)
    actual = restored_component(field)

    assert isinstance(expected, OpticalField)
    assert isinstance(actual, OpticalField)
    assert actual.envelope.shape == expected.envelope.shape
    assert actual.envelope.dtype == expected.envelope.dtype
    assert torch.equal(actual.envelope, expected.envelope)

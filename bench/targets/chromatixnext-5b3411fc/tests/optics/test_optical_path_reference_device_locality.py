from __future__ import annotations

from collections.abc import Callable
import copy
import math

import pytest
import torch

from chromatix_next.errors import AssemblyError
from chromatix_next.optics import (
    OpticalField,
    OpticalPathReference,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.combination import coherent_combination
from chromatix_next.optics.source import PlaneWave

_CoherentResult = OpticalField | tuple[OpticalField, OpticalField]
_CoherentOperation = Callable[
    [OpticalField, OpticalField],
    _CoherentResult,
]


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(2, 3),
        sample_spacing=(1.0e-6, 1.0e-6),
    )


def _source_field(*, spectrum: Spectrum | None = None) -> OpticalField:
    diagonal_component = math.sqrt(0.5)
    if spectrum is None:
        spectrum = Spectrum.monochromatic(wavelength=532.0e-9)
    source = PlaneWave(
        spectrum=spectrum,
        polarization=Polarization.transverse(
            components=(diagonal_component, diagonal_component),
        ),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    return source(_grid())


def _fields_with_cross_device_reference(
    *,
    envelope_device: torch.device,
    reference_device: torch.device,
    reference_field_index: int,
) -> tuple[OpticalField, OpticalField]:
    source_field = _source_field()
    fields = [copy.copy(source_field), copy.copy(source_field)]
    for field in fields:
        object.__setattr__(
            field,
            "envelope",
            field.envelope.to(device=envelope_device),
        )
    reference_length = torch.tensor(
        0.125e-6,
        dtype=torch.float64,
        device=reference_device,
    )
    object.__setattr__(
        fields[reference_field_index],
        "path_reference",
        OpticalPathReference(lengths=(reference_length,)),
    )
    return fields[0], fields[1]


def _coherent_combination(
    field_1: OpticalField,
    field_2: OpticalField,
) -> _CoherentResult:
    return coherent_combination(field_1, field_2)


_OPERATION_CASES: tuple[tuple[_CoherentOperation, str], ...] = (
    (
        _coherent_combination,
        "coherent_combination_device_mismatch",
    ),
)


@pytest.mark.cuda
@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA 双向设备局部性反例只在原生 CUDA 可用时执行",
)
@pytest.mark.parametrize(
    ("envelope_device", "reference_device"),
    (
        (torch.device("cpu"), torch.device("cuda")),
        (torch.device("cuda"), torch.device("cpu")),
    ),
)
@pytest.mark.parametrize("reference_field_index", (0, 1))
@pytest.mark.parametrize(("operation", "expected_identity"), _OPERATION_CASES)
def test_public_coherent_operations_reject_cross_device_reference_before_mixing(
    operation: _CoherentOperation,
    expected_identity: str,
    reference_field_index: int,
    envelope_device: torch.device,
    reference_device: torch.device,
) -> None:
    """
    三条公共相干操作都在载波或散射运算前拒绝任一输入场的跨设备光程参考
    """

    field_1, field_2 = _fields_with_cross_device_reference(
        envelope_device=envelope_device,
        reference_device=reference_device,
        reference_field_index=reference_field_index,
    )

    with pytest.raises(AssemblyError) as information:
        operation(field_1, field_2)

    assert information.value.identity == expected_identity


@pytest.mark.cuda
@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA 多光谱设备局部性反例只在原生 CUDA 可用时执行",
)
@pytest.mark.parametrize(("operation", "expected_identity"), _OPERATION_CASES)
def test_each_tensor_reference_length_participates_in_device_preflight(
    operation: _CoherentOperation,
    expected_identity: str,
) -> None:
    """
    每个光谱分量的张量光程参考都进入公共操作的设备预检
    """

    spectrum = Spectrum(
        wavelengths=(532.0e-9, 633.0e-9),
        weights=(0.5, 0.5),
    )
    source_field = _source_field(spectrum=spectrum)
    fields = [copy.copy(source_field), copy.copy(source_field)]
    object.__setattr__(
        fields[1],
        "path_reference",
        OpticalPathReference(
            lengths=(
                torch.tensor(0.0, dtype=torch.float64),
                torch.tensor(
                    0.125e-6,
                    dtype=torch.float64,
                    device="cuda",
                ),
            ),
        ),
    )

    with pytest.raises(AssemblyError) as information:
        operation(fields[0], fields[1])

    assert information.value.identity == expected_identity


@pytest.mark.cuda
@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA 多重设备错配证据只在原生 CUDA 可用时执行",
)
@pytest.mark.parametrize(("operation", "expected_identity"), _OPERATION_CASES)
def test_each_operation_reports_one_device_finding_for_multiple_placement_mismatches(
    operation: _CoherentOperation,
    expected_identity: str,
) -> None:
    """
    包络与两路光程参考同时错配时每条操作仍只报告一次自己的设备身份
    """

    field_1, field_2 = _fields_with_cross_device_reference(
        envelope_device=torch.device("cpu"),
        reference_device=torch.device("cuda"),
        reference_field_index=0,
    )
    object.__setattr__(
        field_2,
        "envelope",
        field_2.envelope.to(device="cuda"),
    )
    object.__setattr__(
        field_2,
        "path_reference",
        OpticalPathReference(
            lengths=(torch.tensor(0.0, dtype=torch.float64),),
        ),
    )

    with pytest.raises(AssemblyError) as information:
        operation(field_1, field_2)

    assert information.value.identity == expected_identity


@pytest.mark.parametrize(
    "device",
    (
        torch.device("cpu"),
        pytest.param(
            torch.device("cuda"),
            marks=(
                pytest.mark.cuda,
                pytest.mark.skipif(
                    not torch.cuda.is_available(),
                    reason="CUDA 同设备梯度证据只在原生 CUDA 可用时执行",
                ),
            ),
        ),
    ),
)
@pytest.mark.parametrize(("operation", "_expected_identity"), _OPERATION_CASES)
def test_same_device_reference_remains_trainable_through_each_operation(
    operation: _CoherentOperation,
    _expected_identity: str,
    device: torch.device,
) -> None:
    """
    三条公共操作在同设备路径上保留光程参考叶张量及其非零有限梯度
    """

    source_field = _source_field()
    fields = [copy.copy(source_field), copy.copy(source_field)]
    for field in fields:
        object.__setattr__(
            field,
            "envelope",
            field.envelope.to(device=device),
        )
    reference_length = torch.tensor(
        0.125e-6,
        dtype=torch.float64,
        device=device,
        requires_grad=True,
    )
    object.__setattr__(
        fields[1],
        "path_reference",
        OpticalPathReference(lengths=(reference_length,)),
    )

    result = operation(fields[0], fields[1])
    observed_field = result if isinstance(result, OpticalField) else result[0]
    loss = (
        observed_field.envelope.real.sum()
        + 0.37 * observed_field.envelope.imag.sum()
    )
    (reference_gradient,) = torch.autograd.grad(loss, reference_length)

    assert reference_gradient.device == reference_length.device
    assert torch.isfinite(reference_gradient)
    assert torch.count_nonzero(reference_gradient) == 1

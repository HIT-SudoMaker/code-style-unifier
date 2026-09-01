from __future__ import annotations

from collections.abc import Callable
import copy
import math
from typing import TypeVar

import pytest
import torch

from chromatix_next.optics import (
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.combination import CoherentCombination
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import OpticalPathModulation
from chromatix_next.optics.field import OpticalField
from chromatix_next.optics.propagation import (
    ScalarAngularSpectrum,
    VectorAngularSpectrum,
)
from chromatix_next.optics.source import PlaneWave

WAVELENGTH = 500.0e-9
BASELINE = 100.0e-9


def _grid() -> SpatialGrid:
    # 返回干涉证据使用的最小空间网格
    return SpatialGrid.centered(
        sample_counts=(16, 16),
        sample_spacing=(5.0e-6, 5.0e-6),
    )


def _interferometer_inputs(field: OpticalField) -> tuple[OpticalField, OpticalField]:
    amplitude = 2.0**-0.5
    return (
        _with_envelope(field, amplitude * field.envelope),
        _with_envelope(field, 1j * amplitude * field.envelope),
    )


def _with_envelope(field: OpticalField, envelope: torch.Tensor) -> OpticalField:
    result = copy.copy(field)
    object.__setattr__(result, "envelope", envelope)
    return result


def _first_interferometer_output(
    first: OpticalField,
    second: OpticalField,
) -> OpticalField:
    rotated_second = _with_envelope(second, 1j * second.envelope)
    combined = CoherentCombination()(first, rotated_second)
    return _with_envelope(combined, 2.0**-0.5 * combined.envelope)


def _modulation_mach_zehnder_mean_intensity(
    baseline: float | torch.Tensor,
) -> tuple[torch.Tensor, OpticalPathModulation]:
    grid = _grid()
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=WAVELENGTH),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    transmitted, reflected = _interferometer_inputs(source(grid))
    modulator = OpticalPathModulation(
        grid=grid,
        optical_path_variation=torch.zeros(16, 16, dtype=torch.float64),
        optical_path_baseline=baseline,
    )
    reflected = modulator(reflected)
    first_output = _first_interferometer_output(
        transmitted,
        reflected,
    )
    return IntensityDetection()(first_output).values.mean(), modulator




def _scalar_mach_zehnder_mean_intensity(
    axial_distance: float | torch.Tensor,
) -> tuple[torch.Tensor, ScalarAngularSpectrum]:
    grid = _grid()
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=WAVELENGTH),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    transmitted, reflected = _interferometer_inputs(source(grid))
    propagator = ScalarAngularSpectrum(axial_distance=axial_distance)
    propagated = propagator(reflected)
    first_output = _first_interferometer_output(transmitted, propagated)
    return IntensityDetection()(first_output).values.mean(), propagator


def _vector_mach_zehnder_mean_intensity(
    axial_distance: float | torch.Tensor,
) -> tuple[torch.Tensor, VectorAngularSpectrum]:
    grid = _grid()
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=WAVELENGTH),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    transmitted, reflected = _interferometer_inputs(source(grid))
    transmitted_reference = VectorAngularSpectrum(axial_distance=0.0)(transmitted)
    propagator = VectorAngularSpectrum(axial_distance=axial_distance)
    propagated = propagator(reflected)
    first_output = _first_interferometer_output(
        transmitted_reference,
        propagated,
    )
    return IntensityDetection()(first_output).values.mean(), propagator


_CarrierOwner = TypeVar(
    "_CarrierOwner",
    OpticalPathModulation,
    ScalarAngularSpectrum,
    VectorAngularSpectrum,
)


def _assert_mach_zehnder_leaf_carrier_gradient(
    *,
    calculate_mean_intensity: Callable[
        [float | torch.Tensor],
        tuple[torch.Tensor, _CarrierOwner],
    ],
    leaf: torch.Tensor,
    path_difference: float,
    wavelength: float,
) -> _CarrierOwner:
    # 验证给定叶张量对 Mach–Zehnder 最终平均强度的载波梯度
    step = 1.0e-12
    forward_output, _ = calculate_mean_intensity(path_difference + step)
    backward_output, _ = calculate_mean_intensity(path_difference - step)
    finite_difference = (float(forward_output) - float(backward_output)) / (
        2.0 * step
    )

    output, owner = calculate_mean_intensity(leaf)
    output.backward()

    assert leaf.grad is not None
    gradient = float(leaf.grad)
    assert math.isfinite(gradient)
    assert gradient != 0.0
    assert math.isfinite(finite_difference)
    assert finite_difference != 0.0
    assert gradient == pytest.approx(finite_difference, rel=1.0e-6)

    # 独立解析锚点：I(d) = (1 - cos(2πd/λ)) / 2
    analytic_derivative = math.pi / wavelength * math.sin(
        2.0 * math.pi * path_difference / wavelength,
    )
    assert analytic_derivative != 0.0
    assert gradient * analytic_derivative > 0.0
    assert gradient == pytest.approx(analytic_derivative, rel=1.0e-9)
    return owner


def _assert_mach_zehnder_parameter_carrier_gradient(
    *,
    calculate_mean_intensity: Callable[
        [float | torch.Tensor],
        tuple[torch.Tensor, _CarrierOwner],
    ],
    leaf: torch.nn.Parameter,
    path_difference: float,
    wavelength: float,
) -> _CarrierOwner:
    # 验证 leaf Parameter 的 Mach–Zehnder 载波梯度与公开注册生命周期
    owner = _assert_mach_zehnder_leaf_carrier_gradient(
        calculate_mean_intensity=calculate_mean_intensity,
        leaf=leaf,
        path_difference=path_difference,
        wavelength=wavelength,
    )
    assert any(
        parameter is leaf
        for _name, parameter in owner.named_parameters()
    )
    return owner


def test_uniform_optical_path_carries_a_true_gradient() -> None:
    """
    断言均匀光程（以普通 Tensor 而非 nn.Parameter 进入）仍承载真实载波梯度

    entry-form 维度：本条与三条 end-to-end 用例互补——后者以 nn.Parameter 进入，
    本条以 requires_grad=True 的普通叶 Tensor 进入，证明非 Parameter 注册路径
    同样把载波梯度带到 Mach-Zehnder 一路的平均光强上。
    """

    baseline = torch.tensor(BASELINE, dtype=torch.float64, requires_grad=True)
    owner = _assert_mach_zehnder_leaf_carrier_gradient(
        calculate_mean_intensity=_modulation_mach_zehnder_mean_intensity,
        leaf=baseline,
        path_difference=BASELINE,
        wavelength=WAVELENGTH,
    )
    named_buffers = dict(owner.named_buffers())
    assert "optical_path_baseline" in named_buffers
    assert named_buffers["optical_path_baseline"].requires_grad
    assert not tuple(owner.named_parameters())


def test_scalar_distance_tensor_closes_buffer_lifecycle_evidence() -> None:
    """
    标量传播普通叶张量经 Buffer 生命周期到达最终干涉强度
    """

    axial_distance = torch.tensor(
        BASELINE,
        dtype=torch.float64,
        requires_grad=True,
    )
    owner = _assert_mach_zehnder_leaf_carrier_gradient(
        calculate_mean_intensity=_scalar_mach_zehnder_mean_intensity,
        leaf=axial_distance,
        path_difference=BASELINE,
        wavelength=WAVELENGTH,
    )
    named_buffers = dict(owner.named_buffers())
    assert "axial_distance" in named_buffers
    assert named_buffers["axial_distance"].requires_grad
    assert not tuple(owner.named_parameters())


def test_vector_distance_tensor_closes_buffer_lifecycle_evidence() -> None:
    """
    矢量传播普通叶张量经 Buffer 生命周期到达最终干涉强度
    """

    axial_distance = torch.tensor(
        BASELINE,
        dtype=torch.float64,
        requires_grad=True,
    )
    owner = _assert_mach_zehnder_leaf_carrier_gradient(
        calculate_mean_intensity=_vector_mach_zehnder_mean_intensity,
        leaf=axial_distance,
        path_difference=BASELINE,
        wavelength=WAVELENGTH,
    )
    named_buffers = dict(owner.named_buffers())
    assert "axial_distance" in named_buffers
    assert named_buffers["axial_distance"].requires_grad
    assert not tuple(owner.named_parameters())


def test_optical_path_baseline_parameter_closes_end_to_end_evidence() -> None:
    """
    断言光程基线 leaf Parameter 经完整 Mach-Zehnder 反向得到解析一致的梯度
    """
    baseline = torch.nn.Parameter(
        torch.tensor(BASELINE, dtype=torch.float64),
    )
    owner = _assert_mach_zehnder_parameter_carrier_gradient(
        calculate_mean_intensity=_modulation_mach_zehnder_mean_intensity,
        leaf=baseline,
        path_difference=BASELINE,
        wavelength=WAVELENGTH,
    )
    assert owner.optical_path_baseline is baseline
    named_parameters = dict(owner.named_parameters())
    assert tuple(named_parameters) == ("optical_path_baseline",)
    assert named_parameters["optical_path_baseline"] is baseline


def test_scalar_propagation_distance_parameter_closes_end_to_end_evidence() -> None:
    """
    断言标量角谱轴向距离 leaf Parameter 经完整 Mach-Zehnder 反向得到解析梯度
    """
    axial_distance = torch.nn.Parameter(
        torch.tensor(BASELINE, dtype=torch.float64),
    )
    owner = _assert_mach_zehnder_parameter_carrier_gradient(
        calculate_mean_intensity=_scalar_mach_zehnder_mean_intensity,
        leaf=axial_distance,
        path_difference=BASELINE,
        wavelength=WAVELENGTH,
    )
    assert owner.axial_distance is axial_distance
    named_parameters = dict(owner.named_parameters())
    assert tuple(named_parameters) == ("axial_distance",)
    assert named_parameters["axial_distance"] is axial_distance


def test_vector_propagation_distance_parameter_closes_end_to_end_evidence() -> None:
    """
    断言矢量角谱轴向距离 leaf Parameter 经完整 Mach-Zehnder 反向得到解析梯度
    """
    axial_distance = torch.nn.Parameter(
        torch.tensor(BASELINE, dtype=torch.float64),
    )
    owner = _assert_mach_zehnder_parameter_carrier_gradient(
        calculate_mean_intensity=_vector_mach_zehnder_mean_intensity,
        leaf=axial_distance,
        path_difference=BASELINE,
        wavelength=WAVELENGTH,
    )
    assert owner.axial_distance is axial_distance
    named_parameters = dict(owner.named_parameters())
    assert tuple(named_parameters) == ("axial_distance",)
    assert named_parameters["axial_distance"] is axial_distance

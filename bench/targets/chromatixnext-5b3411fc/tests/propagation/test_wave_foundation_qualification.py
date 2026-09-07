
from __future__ import annotations

import pytest
import torch

from chromatix_next.optics import (
    FieldNormalization,
    OpticalField,
    Polarization,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.grid import PropagationExterior
from chromatix_next.optics.propagation import (
    ScalarAngularSpectrum,
    ScaledAngularSpectrum,
    ScaledFresnel,
)
from chromatix_next.optics.source import GaussianBeam, PointSource


def _grid(
    counts: tuple[int, int] = (32, 32),
    spacing: tuple[float, float] = (0.5e-6, 0.5e-6),
) -> SpatialGrid:
    # 构造中心对齐的横向网格（充分采样、场在边缘充分衰减）
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=(
            torch.tensor(spacing[0], dtype=torch.float64),
            torch.tensor(spacing[1], dtype=torch.float64),
        ),
    )


def _monochromatic(wavelength: float = 1.0e-6) -> Spectrum:
    # 构造单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _total_power(field: OpticalField) -> torch.Tensor:
    # 按 POWER 归一化语义累加 |包络|^2 × 单元面积 × 光谱权重
    weights = torch.tensor(
        field.spectrum.weights,
        dtype=field.envelope.real.dtype,
        device=field.envelope.device,
    ).reshape(-1, 1, 1, 1)
    power_density = field.envelope.abs().square()
    return (power_density * field.grid.cell_area * weights).sum()


class TestCombinedPowerConservation:
    """
    POWER 归一化新 Source 经严格幺正标量角谱传播后总功率守恒
    """

    def test_power_gaussian_beam_total_power_preserved_through_scalar_propagation(
        self,
    ) -> None:
        """
        高斯光束 POWER 场经标量角谱传播后空间积分仍等于声明总功率
        """
        grid = _grid()
        spectrum = _monochromatic(wavelength=1.0e-6)
        declared_power = 2.5
        source = GaussianBeam(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=4.0e-6,
            waist_location=0.0,
            total_power=declared_power,
        )
        propagator = ScalarAngularSpectrum(
            axial_distance=4.0e-6,
            exterior=PropagationExterior.PERIODIC,
        )
        input_field = source(grid)
        assert input_field.normalization is FieldNormalization.POWER
        output_field = propagator(input_field)
        preserved = _total_power(output_field).item()
        assert preserved == pytest.approx(declared_power, rel=1.0e-3)

    def test_power_point_source_total_power_preserved_through_scalar_propagation(
        self,
    ) -> None:
        """
        点源 POWER 场经标量角谱传播后空间积分仍等于声明总功率
        """
        grid = _grid()
        spectrum = _monochromatic(wavelength=1.0e-6)
        declared_power = 1.0
        source = PointSource(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=(0.0, 0.0, 100.0e-6),
            total_power=declared_power,
        )
        propagator = ScalarAngularSpectrum(
            axial_distance=20.0e-6,
            exterior=PropagationExterior.PERIODIC,
        )
        input_field = source(grid)
        assert input_field.normalization is FieldNormalization.POWER
        output_field = propagator(input_field)
        preserved = _total_power(output_field).item()
        assert preserved == pytest.approx(declared_power, rel=5.0e-3)


class TestCombinedSourcePropagationGradients:
    """
    Source 叶端 Parameter 经 propagation 链路保留计算图（双精度 gradcheck）
    """

    def test_gaussian_beam_waist_gradient_through_scaled_propagation(self) -> None:
        """
        高斯光束可训练 waist 经带尺度角谱传播仍可微（端到端 gradcheck）
        """
        grid = _grid(counts=(16, 16), spacing=(1.0e-6, 1.0e-6))
        spectrum = _monochromatic(wavelength=2.0e-6)
        waist = torch.nn.Parameter(torch.tensor(4.0e-6, dtype=torch.float64))
        source = GaussianBeam(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            waist=waist,
            waist_location=0.0,
            total_power=2.0,
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(12, 12),
            sample_spacing=(
                torch.tensor(0.8e-6, dtype=torch.float64),
                torch.tensor(0.8e-6, dtype=torch.float64),
            ),
        )
        propagator = ScaledAngularSpectrum(
            axial_distance=8.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )

        def run(waist_value: torch.Tensor) -> torch.Tensor:
            """
            返回当前 waist 下端到端输出的包络实部和
            """
            return propagator(source(grid)).envelope.real.sum()

        assert torch.autograd.gradcheck(
            run,
            (waist,),
            eps=1e-9,
            raise_exception=True,
        )

    def test_point_source_position_gradient_through_scaled_fresnel_propagation(
        self,
    ) -> None:
        """
        点源可训练位置经带尺度 Fresnel 传播仍可微（端到端 gradcheck）
        """
        grid = _grid(counts=(16, 16), spacing=(1.0e-6, 1.0e-6))
        spectrum = _monochromatic(wavelength=2.0e-6)
        position = torch.nn.Parameter(
            torch.tensor(
                (0.0, 0.0, 200.0e-6),
                dtype=torch.float64,
            ),
        )
        source = PointSource(
            spectrum=spectrum,
            polarization=Polarization.scalar(),
            medium=Vacuum(),
            position=position,
            total_power=1.0,
        )
        destination_grid = SpatialGrid.centered(
            sample_counts=(12, 12),
            sample_spacing=(
                torch.tensor(1.2e-6, dtype=torch.float64),
                torch.tensor(1.2e-6, dtype=torch.float64),
            ),
        )
        propagator = ScaledFresnel(
            axial_distance=150.0e-6,
            destination_grid=destination_grid,
            exterior=PropagationExterior.PERIODIC,
        )

        def run(position_value: torch.Tensor) -> torch.Tensor:
            """
            返回当前位置下端到端输出的包络实部和
            """
            return propagator(source(grid)).envelope.real.sum()

        assert torch.autograd.gradcheck(
            run,
            (position,),
            eps=1e-9,
            raise_exception=True,
        )

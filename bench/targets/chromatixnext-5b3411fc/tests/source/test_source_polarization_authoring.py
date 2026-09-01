
from __future__ import annotations

from collections.abc import Callable

import pytest
import torch

from chromatix_next.optics import (
    OpticalField,
    Polarization,
    PolarizationRepresentation,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.source import GaussianBeam, PlaneWave, PointSource


def _grid() -> SpatialGrid:
    # 中心对齐横向网格；PointSource 原点轴向距离 10e-6 与 0.5e-6 采样满足有限原点守护
    return SpatialGrid.centered(
        sample_counts=(8, 8),
        sample_spacing=(0.5e-6, 0.5e-6),
    )


def _spectrum() -> Spectrum:
    # 单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=2.0e-6)


def _polarization_for(
    representation: PolarizationRepresentation,
) -> Polarization:
    # 按被作者表示构造对应偏振：标量、横向（线偏 X）、完整（含纵向单位 X 分量）
    if representation is PolarizationRepresentation.SCALAR:
        return Polarization.scalar()
    if representation is PolarizationRepresentation.TRANSVERSE:
        return Polarization.linear_x()
    return Polarization.full(components=(1.0, 0.0, 0.0))


_SOURCE_FACTORIES: dict[str, Callable[[Polarization], torch.nn.Module]] = {
    "PlaneWave": lambda polarization: PlaneWave(
        spectrum=_spectrum(),
        polarization=polarization,
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    ),
    "GaussianBeam": lambda polarization: GaussianBeam(
        spectrum=_spectrum(),
        polarization=polarization,
        medium=Vacuum(),
        waist=2.0e-6,
        relative_amplitude=1.0,
    ),
    "PointSource": lambda polarization: PointSource(
        spectrum=_spectrum(),
        polarization=polarization,
        medium=Vacuum(),
        position=(0.0, 0.0, 10.0e-6),
        relative_amplitude=1.0,
    ),
}

_REPRESENTATIONS = (
    PolarizationRepresentation.SCALAR,
    PolarizationRepresentation.TRANSVERSE,
    PolarizationRepresentation.FULL,
)
_REPRESENTATION_IDS = ["scalar", "transverse", "full"]


@pytest.mark.parametrize(
    "source_name",
    tuple(_SOURCE_FACTORIES),
    ids=tuple(_SOURCE_FACTORIES),
)
@pytest.mark.parametrize(
    "representation",
    _REPRESENTATIONS,
    ids=_REPRESENTATION_IDS,
)
def test_source_authors_declared_polarization_representation(
    source_name: str,
    representation: PolarizationRepresentation,
) -> None:
    """
    波源以正确的分量数与固定双精度 dtype 作者声明的偏振表示
    """

    source = _SOURCE_FACTORIES[source_name](_polarization_for(representation))
    field = source(_grid())
    assert isinstance(field, OpticalField)
    assert field.polarization_representation is representation
    assert field.envelope.dtype is torch.complex128
    assert field.envelope.shape[-3] == representation.component_count
    assert field.envelope.shape[0] == _spectrum().count
    assert tuple(field.envelope.shape[-2:]) == _grid().sample_counts


@pytest.mark.parametrize(
    "source_name",
    tuple(_SOURCE_FACTORIES),
    ids=tuple(_SOURCE_FACTORIES),
)
def test_source_envelope_polarization_axis_matches_representation_count(
    source_name: str,
) -> None:
    """
    波源包络偏振轴长度在三种表示上逐项等于表示分量数
    """

    source_factory = _SOURCE_FACTORIES[source_name]
    grid = _grid()
    for representation in _REPRESENTATIONS:
        source = source_factory(_polarization_for(representation))
        field = source(grid)
        assert field.envelope.shape[-3] == representation.component_count
        assert field.polarization_representation is representation

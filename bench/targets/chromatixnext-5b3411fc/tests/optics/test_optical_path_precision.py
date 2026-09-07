from __future__ import annotations

import math

import pytest
import torch

from chromatix_next.optics import (
    FieldNormalization,
    Medium,
    OpticalField,
    OpticalPathReference,
    Polarization,
    SellmeierMedium,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.combination import CoherentCombination
from chromatix_next.optics.detection import intensity_detection
from chromatix_next.optics.element import OpticalPathModulation
from chromatix_next.optics.propagation import scalar_angular_spectrum

_WAVELENGTH = 500.0e-9
_COMMON_LENGTH = 10.0
_ADJUSTMENT = 100.0e-9


def _grid() -> SpatialGrid:
    spacing = torch.tensor(1.0, dtype=torch.float64)
    return SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(
            spacing,
            spacing.clone(),
        ),
    )


def _field(
    *,
    is_vector: bool = False,
    medium: Medium | None = None,
) -> OpticalField:
    grid = _grid()
    polarization = (
        Polarization.linear_x()
        if is_vector
        else Polarization.scalar()
    )
    envelope = torch.zeros(
        (
            1,
            polarization.component_count,
            *grid.sample_counts,
        ),
        dtype=torch.complex128,
    )
    envelope[:, 0] = 1.0
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=Spectrum.monochromatic(
            wavelength=_WAVELENGTH,
        ),
        polarization_representation=polarization.representation,
        medium=medium if medium is not None else Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,),
        ),
    )


def _modulator(
    field: OpticalField,
    *,
    baseline: float,
) -> OpticalPathModulation:
    return OpticalPathModulation(
        grid=field.grid,
        optical_path_variation=torch.zeros(
            field.grid.sample_counts,
            dtype=field.envelope.real.dtype,
        ),
        optical_path_baseline=baseline,
    )


def test_coherent_combination_aligns_long_unequal_references() -> None:
    """
    相干组合在十米公共参考上恢复百纳米相对载波
    """

    field = _field()
    arm_1 = _modulator(
        field,
        baseline=_COMMON_LENGTH,
    )(field)
    arm_2 = _modulator(
        arm_1,
        baseline=_ADJUSTMENT,
    )(arm_1)
    combined = CoherentCombination()(arm_1, arm_2)
    intensity = intensity_detection(combined).values
    phase = 2.0 * math.pi * _ADJUSTMENT / _WAVELENGTH
    expected_value = 2.0 + 2.0 * math.cos(phase)

    assert torch.allclose(
        intensity,
        torch.full_like(
            intensity,
            expected_value,
        ),
        rtol=2.0e-6,
        atol=2.0e-6,
    )


def test_dispersive_reference_queries_medium_in_float64() -> None:
    """
    色散参考直接使用 float64 波长与折射率（固定双精度）

    float32 波长查询被介质入口直接拒绝，以证明
    路径长度用 float64 计算；Medium 入口直接拒绝
    非 float64 波长查询。本测试反演：f32 查询被 owner 拒绝，f64 查询给出与路径
    长度一致的结果。
    """

    medium = SellmeierMedium(
        b_coefficients=(
            0.6961663,
            0.4079426,
            0.8974794,
        ),
        c_coefficients=(
            0.0684043**2,
            0.1162414**2,
            9.896161**2,
        ),
        wavelength_min=0.21e-6,
        wavelength_max=3.71e-6,
    )
    field = _field(medium=medium)
    output = scalar_angular_spectrum(
        field,
        axial_distance=_COMMON_LENGTH,
    )
    path_length = output.path_reference.lengths[0]
    wavelengths_64 = torch.tensor(
        (_WAVELENGTH,),
        dtype=torch.float64,
    )
    wavelengths_32 = wavelengths_64.to(dtype=torch.float32)
    expected = (
        medium.refractive_index(wavelengths_64)[0]
        * _COMMON_LENGTH
    )

    # f32 查询现在直接被 Medium 公共入口拒绝（不再镜像输入 dtype）
    with pytest.raises(
        ValueError,
        match="medium_wavelength_query_invalid",
    ):
        medium.refractive_index(wavelengths_32)

    assert isinstance(path_length, torch.Tensor)
    assert path_length.dtype is torch.float64
    assert torch.equal(path_length, expected)

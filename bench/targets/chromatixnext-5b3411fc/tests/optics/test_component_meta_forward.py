from __future__ import annotations

import copy

import pytest
import torch

from chromatix_next.optics import (
    Polarization,
    PropagationDirection,
    PropagationExterior,
    SellmeierMedium,
    SpatialGrid,
    Spectrum,
    TabulatedMedium,
    Vacuum,
)
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave

_SAMPLE_COUNTS = (17, 17)


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=_SAMPLE_COUNTS,
        sample_spacing=(0.5e-6, 0.5e-6),
    )


def test_real_and_meta_forward_preserve_dynamic_field_axes() -> None:
    """
    内容决定的批量、光谱与偏振轴在真实与 meta 路径保持一致
    """

    grid = _grid()
    spectrum = Spectrum(
        wavelengths=(4.0e-6, 5.0e-6),
        weights=(0.4, 0.6),
    )
    source = PlaneWave(
        spectrum=spectrum,
        polarization=Polarization.transverse(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    real_field = source(grid)
    meta_field = copy.copy(real_field)
    object.__setattr__(
        meta_field,
        "envelope",
        torch.empty(
            (3, *real_field.envelope.shape),
            dtype=real_field.envelope.dtype,
            device="meta",
        ),
    )
    object.__setattr__(
        real_field,
        "envelope",
        real_field.envelope.expand(3, *real_field.envelope.shape).clone(),
    )
    component = ScalarAngularSpectrum(
        axial_distance=1.0e-6,
        exterior=PropagationExterior.PERIODIC,
    )

    real_output = component(real_field)
    meta_output = component(meta_field)

    expected_shape = (
        3,
        spectrum.count,
        real_field.polarization_representation.component_count,
        *_SAMPLE_COUNTS,
    )
    assert real_output.envelope.shape == expected_shape
    assert meta_output.envelope.shape == expected_shape
    assert meta_output.envelope.dtype == real_output.envelope.dtype


@pytest.mark.parametrize(
    "medium",
    (
        TabulatedMedium(
            wavelengths=(3.0e-6, 6.0e-6),
            refractive_indices=(1.50, 1.52),
        ),
        SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.01046945),
            c_coefficients=(0.00600069867, 0.0200179144, 103.560653),
            wavelength_min=3.0e-6,
            wavelength_max=6.0e-6,
        ),
    ),
)
def test_real_and_meta_forward_preserve_dispersive_medium(
    medium: TabulatedMedium | SellmeierMedium,
) -> None:
    """
    色散介质在真实与 meta 标量传播中保持形状和固定精度
    """

    grid = _grid()
    source = PlaneWave(
        spectrum=Spectrum(
            wavelengths=(4.0e-6, 5.0e-6),
            weights=(0.4, 0.6),
        ),
        polarization=Polarization.scalar(),
        medium=medium,
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    real_field = source(grid)
    meta_field = copy.copy(real_field)
    object.__setattr__(
        meta_field,
        "envelope",
        torch.empty_like(real_field.envelope, device="meta"),
    )
    component = ScalarAngularSpectrum(
        axial_distance=1.0e-6,
        exterior=PropagationExterior.PERIODIC,
    )

    real_output = component(real_field)
    meta_output = component(meta_field)

    assert meta_output.envelope.shape == real_output.envelope.shape
    assert meta_output.envelope.dtype == real_output.envelope.dtype

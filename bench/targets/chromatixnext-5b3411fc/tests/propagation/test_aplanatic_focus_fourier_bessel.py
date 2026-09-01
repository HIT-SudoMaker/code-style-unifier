from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

import pytest
import torch

from chromatix_next.optics import (
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    PolarizationRepresentation,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
import chromatix_next.optics.propagation as _propagation
from chromatix_next.optics.propagation import aplanatic_focus
from tests.architecture._python_import_facts import read_python_imports

from ._aplanatic_reference import _direct_aplanatic_focus
from ._fourier_bessel_reference import _fourier_bessel_focus

_TESTS_ROOT = Path(__file__).resolve().parents[1]

_Polarization = Literal[
    "laboratory_x",
    "radial",
    "azimuthal",
]
_FOCAL_LENGTH = 8.0e-6
_MAXIMUM_ANGLE = 0.45
_WAVELENGTH = 0.532e-6
_AXIAL_DISTANCE = 0.18e-6
_DESTINATION_Y = torch.tensor(
    (-0.28e-6, 0.0, 0.28e-6),
    dtype=torch.float64,
)
_DESTINATION_X = torch.tensor(
    (-0.35e-6, 0.0, 0.35e-6),
    dtype=torch.float64,
)


def _even_pupil(
    sample_count: int,
    polarization: _Polarization,
) -> tuple[OpticalField, torch.Tensor, torch.Tensor]:
    radius_limit = _FOCAL_LENGTH * math.sin(_MAXIMUM_ANGLE)
    spacing = torch.tensor(
        2.0 * radius_limit / sample_count,
        dtype=torch.float64,
    )
    first_position = -(sample_count - 1) * spacing / 2.0
    grid = SpatialGrid(
        sample_counts=(sample_count, sample_count),
        sample_spacing=(spacing, spacing),
        first_sample_position=(first_position, first_position),
    )
    position = (
        torch.arange(sample_count, dtype=torch.float64) * spacing
        + first_position
    )
    coordinate_y, coordinate_x = torch.meshgrid(
        position,
        position,
        indexing="ij",
    )
    radius = torch.sqrt(
        coordinate_y.square() + coordinate_x.square(),
    )
    assert not bool((radius == 0.0).any())
    if polarization == "laboratory_x":
        field_x = torch.ones_like(radius)
        field_y = torch.zeros_like(radius)
    elif polarization == "radial":
        field_x = coordinate_x / radius
        field_y = coordinate_y / radius
    else:
        field_x = -coordinate_y / radius
        field_y = coordinate_x / radius
    envelope = torch.stack(
        (field_x, field_y),
    ).unsqueeze(0).to(dtype=torch.complex128)
    return (
        OpticalField(
            envelope=envelope,
            grid=grid,
            spectrum=Spectrum.monochromatic(_WAVELENGTH),
            polarization_representation=(
                PolarizationRepresentation.TRANSVERSE
            ),
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,)),
        ),
        position,
        position,
    )


def _direct_focus(
    sample_count: int,
    polarization: _Polarization,
) -> tuple[OpticalField, torch.Tensor]:
    field, pupil_y, pupil_x = _even_pupil(
        sample_count,
        polarization,
    )
    direct = _direct_aplanatic_focus(
        field.envelope,
        pupil_y=pupil_y,
        pupil_x=pupil_x,
        destination_y=_DESTINATION_Y,
        destination_x=_DESTINATION_X,
        wavelengths=torch.tensor(
            (_WAVELENGTH,),
            dtype=torch.float64,
        ),
        refractive_indices=torch.ones(1, dtype=torch.float64),
        input_path_lengths=torch.zeros(1, dtype=torch.float64),
        focal_length=_FOCAL_LENGTH,
        maximum_convergence_angle=_MAXIMUM_ANGLE,
        axial_distance_from_focus=_AXIAL_DISTANCE,
    )
    return field, direct.residual_envelope[0]


def _bessel_focus(
    polarization: _Polarization,
    radial_sample_count: int,
) -> torch.Tensor:
    return _fourier_bessel_focus(
        polarization=polarization,
        radial_sample_count=radial_sample_count,
        destination_y=_DESTINATION_Y,
        destination_x=_DESTINATION_X,
        wavelength=_WAVELENGTH,
        refractive_index=1.0,
        focal_length=_FOCAL_LENGTH,
        maximum_convergence_angle=_MAXIMUM_ANGLE,
        axial_distance_from_focus=_AXIAL_DISTANCE,
    )


def test_fourier_bessel_reference_has_no_production_numerical_import() -> None:
    """
    Fourier–Bessel 证据不导入生产聚焦或 Chirp-Z 数值实现
    """

    source_path = Path(
        __file__,
    ).with_name("_fourier_bessel_reference.py")
    imported_modules = read_python_imports(
        source_path,
        _TESTS_ROOT,
    ).imported_modules

    assert all(
        not module.startswith("chromatix_next")
        for module in imported_modules
    )
    assert all(
        term not in name.lower()
        for name in _propagation.__all__
        for term in ("bessel", "fourier", "hankel", "radial")
    )


def test_laboratory_x_retains_j0_j1_and_j2_complex_content() -> None:
    """
    均匀实验室 x 偏振保留三个阶次产生的完整复场分量
    """

    focused = _bessel_focus("laboratory_x", 4096)

    assert focused[0, 1, 1].abs() > 0.0
    assert focused[2, 1, 2].abs() > 0.0
    assert focused[1, 2, 2].abs() > 0.0
    assert not focused.requires_grad


@pytest.mark.parametrize(
    "polarization",
    ("laboratory_x", "radial", "azimuthal"),
)
def test_fourier_bessel_converges_to_direct_and_production_complex_field(
    polarization: _Polarization,
) -> None:
    """
    三种圆瞳偏振的复场共同收敛到直接积分与生产结果
    """

    bessel_coarse = _bessel_focus(polarization, 1024)
    bessel_fine = _bessel_focus(polarization, 2048)
    bessel_reference = _bessel_focus(polarization, 4096)
    coarse_change = (
        bessel_coarse - bessel_reference
    ).abs().max()
    fine_change = (
        bessel_fine - bessel_reference
    ).abs().max()
    bessel_tolerance = (
        4.0 * fine_change
        + 64.0
        * torch.finfo(torch.float64).eps
        * bessel_reference.abs().max()
    )
    assert fine_change < coarse_change
    assert fine_change <= bessel_tolerance

    direct_coarse = _direct_focus(40, polarization)[1]
    direct_fine = _direct_focus(72, polarization)[1]
    field, direct_reference = _direct_focus(104, polarization)
    coarse_error = (
        direct_coarse - bessel_reference
    ).abs().max()
    fine_error = (
        direct_fine - bessel_reference
    ).abs().max()
    reference_error = (
        direct_reference - bessel_reference
    ).abs().max()
    cartesian_tolerance = (
        direct_reference - direct_fine
    ).abs().max() + bessel_tolerance
    assert fine_error < coarse_error
    assert reference_error < fine_error
    assert reference_error <= cartesian_tolerance

    destination_grid = SpatialGrid(
        sample_counts=(3, 3),
        sample_spacing=(
            _DESTINATION_Y[1] - _DESTINATION_Y[0],
            _DESTINATION_X[1] - _DESTINATION_X[0],
        ),
        first_sample_position=(
            _DESTINATION_Y[0],
            _DESTINATION_X[0],
        ),
    )
    production = aplanatic_focus(
        field,
        focal_length=_FOCAL_LENGTH,
        maximum_convergence_angle=_MAXIMUM_ANGLE,
        axial_distance_from_focus=_AXIAL_DISTANCE,
        destination_grid=destination_grid,
    ).envelope[0]
    production_tolerance = (
        256.0
        * torch.finfo(torch.float64).eps
        * field.grid.sample_counts[0]
        * field.grid.sample_counts[1]
        * max(float(direct_reference.abs().max()), 1.0)
    )
    assert torch.allclose(
        production,
        direct_reference,
        rtol=0.0,
        atol=production_tolerance,
    )
    assert torch.allclose(
        production,
        bessel_reference,
        rtol=0.0,
        atol=float(cartesian_tolerance),
    )


def test_radial_axis_is_longitudinal_and_azimuthal_axis_is_null() -> None:
    """
    径向偏振轴上仅有纵向场而方位偏振轴上保持中心零场
    """

    radial = _bessel_focus("radial", 4096)
    azimuthal = _bessel_focus("azimuthal", 4096)
    scale = max(
        float(radial.abs().max()),
        float(azimuthal.abs().max()),
        1.0,
    )
    tolerance = (
        256.0 * torch.finfo(torch.float64).eps * scale
    )

    assert radial[2, 1, 1].abs() > 1.0e-3 * scale
    assert radial[:2, 1, 1].abs().max() <= tolerance
    assert azimuthal[:, 1, 1].abs().max() <= tolerance

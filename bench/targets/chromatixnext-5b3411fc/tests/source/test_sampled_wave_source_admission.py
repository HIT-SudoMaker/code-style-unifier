from __future__ import annotations

from typing import cast

import pytest

from chromatix_next.errors import OpticalError
from chromatix_next.optics import (
    Medium,
    Polarization,
    PropagationDirection,
    Spectrum,
    TransverseWavevector,
    Vacuum,
)
from chromatix_next.optics.source import GaussianBeam, PlaneWave, PointSource


def _spectrum() -> Spectrum:
    return Spectrum.monochromatic(wavelength=532.0e-9)


@pytest.mark.parametrize(
    ("source_name", "invalid_physical_value", "expected_identity"),
    (
        ("PlaneWave", "spectrum", "plane_wave_spectrum_invalid"),
        ("PlaneWave", "polarization", "plane_wave_polarization_invalid"),
        ("PlaneWave", "medium", "plane_wave_medium_invalid"),
        (
            "PlaneWave",
            "transverse_wavevector",
            "plane_wave_transverse_wavevector_invalid",
        ),
        ("GaussianBeam", "spectrum", "gaussian_beam_spectrum_invalid"),
        (
            "GaussianBeam",
            "polarization",
            "gaussian_beam_polarization_invalid",
        ),
        ("GaussianBeam", "medium", "gaussian_beam_medium_invalid"),
        ("PointSource", "spectrum", "point_source_spectrum_invalid"),
        (
            "PointSource",
            "polarization",
            "point_source_polarization_invalid",
        ),
        ("PointSource", "medium", "point_source_medium_invalid"),
    ),
)
def test_public_source_rejects_invalid_physical_value(
    source_name: str,
    invalid_physical_value: str,
    expected_identity: str,
) -> None:
    """
    每个 sampled Wave Source 的公共构造缝保留稳定物理值身份
    """

    invalid_value = object()
    spectrum: Spectrum = _spectrum()
    polarization = Polarization.linear_x()
    medium: Medium = Vacuum()
    if invalid_physical_value == "spectrum":
        spectrum = cast(Spectrum, invalid_value)
    elif invalid_physical_value == "polarization":
        polarization = cast(Polarization, invalid_value)
    elif invalid_physical_value == "medium":
        medium = cast(Medium, invalid_value)

    with pytest.raises(OpticalError) as rejected:
        if source_name == "PlaneWave":
            transverse_wavevector: TransverseWavevector | None = None
            propagation_direction: PropagationDirection | None = (
                PropagationDirection.forward()
            )
            if invalid_physical_value == "transverse_wavevector":
                transverse_wavevector = cast(
                    TransverseWavevector,
                    invalid_value,
                )
                propagation_direction = None
            PlaneWave(
                spectrum=spectrum,
                polarization=polarization,
                medium=medium,
                propagation_direction=propagation_direction,
                transverse_wavevector=transverse_wavevector,
                relative_amplitude=1.0,
            )
        elif source_name == "GaussianBeam":
            GaussianBeam(
                spectrum=spectrum,
                polarization=polarization,
                medium=medium,
                waist=1.0e-3,
                relative_amplitude=1.0,
            )
        elif source_name == "PointSource":
            PointSource(
                spectrum=spectrum,
                polarization=polarization,
                medium=medium,
                position=(0.0, 0.0, 1.0e-3),
                relative_amplitude=1.0,
            )
        else:
            pytest.fail(f"unknown source: {source_name}")

    assert rejected.value.identity == expected_identity

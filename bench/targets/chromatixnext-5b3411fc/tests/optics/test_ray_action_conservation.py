
from __future__ import annotations

import torch

from chromatix_next.optics import RayBundle, Spectrum
from chromatix_next.optics.element import reflect_at
from chromatix_next.optics.propagation import trace_to
from chromatix_next.optics.ray_bundle import RAY_STATUS_ACTIVE
from chromatix_next.optics.surface import ConicEvenAsphere, Plane, Sphere
from tests.optics._valid_ray_inputs import _transverse_polarization_for_direction


def test_reflect_and_trace_preserve_power_and_incident_index() -> None:
    """
    两个非折射动作均守恒功率与入射折射率
    """

    positions = torch.tensor([[[0.0, 0.0, -3.0e-6]]], dtype=torch.float64)
    directions = torch.tensor([[[0.0, 0.0, 1.0]]], dtype=torch.float64)
    bundle = RayBundle(
        position=positions,
        direction=directions,
        polarization_vector=_transverse_polarization_for_direction(directions),
        power=torch.tensor([[0.7]], dtype=torch.float64),
        refractive_index=torch.tensor([[1.3]], dtype=torch.float64),
        optical_path=torch.zeros((1, 1), dtype=torch.float64),
        status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
        spectrum=Spectrum.monochromatic(wavelength=2.0e-6),
    )
    radius = 5.0e-6
    surfaces = (
        Plane(),
        Sphere(radius_of_curvature=radius),
        ConicEvenAsphere(curvature=1.0 / radius, conic_constant=0.0),
    )

    for surface in surfaces:
        reflected = reflect_at(bundle, surface=surface)
        traced = trace_to(bundle, surface=surface)
        assert torch.equal(reflected.power, bundle.power)
        assert torch.equal(reflected.refractive_index, bundle.refractive_index)
        assert torch.equal(traced.power, bundle.power)
        assert torch.equal(traced.refractive_index, bundle.refractive_index)

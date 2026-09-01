from __future__ import annotations

import math

import torch

from chromatix_next import Workstation
from chromatix_next.optics import (
    Assembly,
    Polarization,
    RayBundle,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.element import RetarderAt
from chromatix_next.optics.source import CollimatedRaySource
from chromatix_next.optics.surface import Plane


def test_ray_retarder_composes_through_public_assembly_seam() -> None:
    """
    准直偏振光线经延迟器后由公开装配边界保持功率与可微状态
    """

    grid = SpatialGrid.centered(
        sample_counts=(3, 3),
        sample_spacing=(2.0e-6, 2.0e-6),
    )
    retardance = torch.nn.Parameter(torch.tensor(0.25, dtype=torch.float64))
    source = CollimatedRaySource(
        spectrum=Spectrum.monochromatic(wavelength=0.5e-6),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        launch_origin=(0.0, 0.0, 0.0),
        launch_tangent_x=(1.0, 0.0, 0.0),
        launch_tangent_y=(0.0, 1.0, 0.0),
        ray_power=1.0,
    )
    retarder = RetarderAt(
        surface=Plane(origin=(0.0, 0.0, 0.0)),
        retardance_cycles=retardance,
        retarded_eigenstate_azimuth_radians=math.pi / 4.0,
        retarded_eigenstate_ellipticity_radians=0.0,
    )
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(retarder, name="retarder")
    assembly.connect(source, retarder)
    assembly.expose(retarder, name="rays")
    assembly.freeze()

    workstation = Workstation.cpu()
    workstation.host(assembly)
    outputs, _record = workstation.run(assembly)
    rays = outputs["rays"]
    assert isinstance(rays, RayBundle)
    assert torch.equal(rays.power, torch.ones_like(rays.power))
    rays.polarization_vector.real.sum().backward()
    assert retardance.grad is not None
    assert bool(torch.isfinite(retardance.grad))

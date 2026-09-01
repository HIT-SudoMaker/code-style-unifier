from __future__ import annotations

from decimal import Decimal

import numpy
import torch

from metacraft.authority.reference import reference_for
from metacraft.field.sample import (
    ComponentBasis,
    CoordinateFrame,
    FieldComponent,
    Medium,
    PlaneSurface,
)
from metacraft.field.vector_angular_spectrum import LongitudinalPowerPlane
from metacraft.materials import MaterialSource
from metacraft.science.metalens.brief import (
    AtomIntent,
    ControlStrategy,
    MaterialIntent,
    MonochromaticSpectrum,
    Polarization,
)
from metacraft.science.metalens.design import (
    MetalensDesign,
    MethodApplicability,
    MethodAssessment,
)
from metacraft.science.metalens.focus import FocalRegion


def metalens_design(strategy: ControlStrategy) -> MetalensDesign:
    polarization = (
        Polarization(kind="linear", axis="x")
        if strategy is ControlStrategy.PROPAGATION_PHASE
        else Polarization(kind="circular", handedness="right")
    )
    return MetalensDesign(
        aim="metalens",
        objectives=("focus",),
        capabilities=(),
        budget="fixture",
        operating_spectrum=MonochromaticSpectrum(800),
        numerical_aperture=Decimal("0.8"),
        focal_length_um=Decimal("0.25"),
        incident_polarization=polarization,
        control_strategy=strategy,
        atom=AtomIntent(
            (
                "circular pillar"
                if strategy is ControlStrategy.PROPAGATION_PHASE
                else "rectangular fin"
            ),
            MaterialIntent("test atom", MaterialSource.SOLVER_NATIVE),
        ),
        substrate=MaterialIntent(
            "test substrate",
            MaterialSource.SOLVER_NATIVE,
        ),
        aspect_limit=8,
        sampling_ceiling_nm=Decimal(500),
        aperture=None,
        method_assessments=(
            MethodAssessment(
                method=f"monochromatic {strategy.value} vector",
                applicability=MethodApplicability.SELECTED,
                grounds=(
                    "monochromatic operating spectrum",
                    f"declared {strategy.value}",
                    "numerical aperture vector regime",
                ),
            ),
        ),
    )


def cartesian_focal_region(
    *,
    found_focus_m: float,
    focus_plane_position_m: float,
) -> FocalRegion:
    values = numpy.ones((5, 5), dtype=numpy.complex128)
    zeros = numpy.zeros_like(values)
    values.setflags(write=False)
    zeros.setflags(write=False)
    components = (
        FieldComponent("x", values),
        FieldComponent("y", zeros),
        FieldComponent("z", zeros),
    )
    power_surface = PlaneSurface(
        focus_plane_position_m,
        100e-9,
        values.shape,
    )
    return FocalRegion(
        wavelength_m=532e-9,
        spacing_m=100e-9,
        expected_focus_m=9e-6,
        found_focus_m=found_focus_m,
        focus_plane_position_m=focus_plane_position_m,
        observed_components=("x", "y", "z"),
        axial_distances_m=(8e-6, 9e-6, 10e-6),
        axial_peak_intensities=(0.2, 1.0, 0.3),
        component_axial_peak_intensities={
            "x": (0.2, 1.0, 0.3),
            "y": (0.0, 0.0, 0.0),
            "z": (0.0, 0.0, 0.0),
        },
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.CARTESIAN,
        electric_components=components,
        source_references=(reference_for(b"focal region"),),
        incident_reference_power=1.0,
        transmitted_aperture_power={},
        realization={"device": "cpu"},
        vector_input_power_w=1.0,
        vector_output_power_w=1.0,
        longitudinal_power_plane=LongitudinalPowerPlane(
            power_surface,
            torch.ones(values.shape, dtype=torch.float64),
        ),
    )

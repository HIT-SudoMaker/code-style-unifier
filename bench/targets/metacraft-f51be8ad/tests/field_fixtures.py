from __future__ import annotations

from collections.abc import Sequence

import numpy

from metacraft.authority import Reference, reference_for
from metacraft.field import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
)
from metacraft.science.metalens import FocalRegion


def recorded_focal_region(
    principal_x: numpy.ndarray,
    *,
    axial_distances_m: Sequence[float],
    axial_peak_intensities: Sequence[float],
    found_focus_m: float,
    expected_focus_m: float,
    spacing_m: float = 100e-9,
    wavelength_m: float = 400e-9,
    incident_reference_power: float = 1.0,
    transmitted_x_power: float = 1.0,
) -> FocalRegion:
    """
    Form compact admitted-style focal evidence without propagating again.
    """

    electric_x = _immutable(principal_x)
    electric_y = _immutable(numpy.zeros_like(electric_x))
    distances = tuple(float(value) for value in axial_distances_m)
    peaks = tuple(float(value) for value in axial_peak_intensities)
    return FocalRegion(
        wavelength_m=wavelength_m,
        spacing_m=spacing_m,
        expected_focus_m=expected_focus_m,
        found_focus_m=found_focus_m,
        focus_plane_position_m=found_focus_m,
        observed_components=("x",),
        axial_distances_m=distances,
        axial_peak_intensities=peaks,
        component_axial_peak_intensities={
            "x": peaks,
            "y": tuple(0.0 for _ in distances),
        },
        frame=CoordinateFrame(),
        medium=Medium("air"),
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            FieldComponent("x", electric_x),
            FieldComponent("y", electric_y),
        ),
        source_references=(reference_for(b"recorded focal field"),),
        incident_reference_power=incident_reference_power,
        transmitted_aperture_power={
            "x": transmitted_x_power,
            "y": 0.0,
        },
        realization={
            "identity": "metacraft.field.angular_spectrum",
            "implementation": "torch",
            "device": "cpu",
            "complex_dtype": "complex128",
            "real_dtype": "float64",
            "convention": {"padding_factor": 2},
            "working_memory_bytes": 1024**3,
            "actual_working_memory_bytes": 1024**3,
            "axial_batch_size": 3,
        },
    )


def reviewed_focus_region(
    field: Field,
    *,
    field_reference: Reference,
    expected_focus_m: float,
    principal_component: str,
) -> FocalRegion:
    """
    Record one compact bracketed focus from an already established Field.
    """

    if principal_component not in field.component_names:
        raise ValueError("principal_component_unknown")
    rows, columns = field.surface.shape
    row_axis = numpy.arange(rows, dtype=numpy.float64) - (rows - 1) / 2
    column_axis = (
        numpy.arange(columns, dtype=numpy.float64) - (columns - 1) / 2
    )
    position_x, position_y = numpy.meshgrid(column_axis, row_axis)
    width = max(1.0, min(rows, columns) / 12)
    profile = numpy.exp(
        -(position_x**2 + position_y**2) / (2 * width**2)
    )
    transmitted = {
        name: float(numpy.sum(numpy.abs(field.electric(name)) ** 2))
        for name in field.component_names
    }
    retained_power = transmitted[principal_component]
    desired_focus_power = max(
        numpy.finfo(numpy.float64).tiny,
        retained_power / 2,
    )
    profile *= numpy.sqrt(
        desired_focus_power / float(numpy.sum(profile**2))
    )
    components = tuple(
        FieldComponent(
            name,
            _immutable(
                profile
                if name == principal_component
                else numpy.zeros_like(profile)
            ),
        )
        for name in field.component_names
    )
    distances = tuple(
        expected_focus_m * fraction
        for fraction in (0.8, 0.9, 1.0, 1.1, 1.2)
    )
    peak = float(numpy.max(numpy.abs(profile) ** 2))
    principal_curve = tuple(
        peak * fraction for fraction in (0.1, 0.4, 1.0, 0.4, 0.1)
    )
    return FocalRegion(
        wavelength_m=field.wavelength_m,
        spacing_m=field.surface.spacing_m,
        expected_focus_m=expected_focus_m,
        found_focus_m=expected_focus_m,
        focus_plane_position_m=(
            field.surface.position_m + expected_focus_m
        ),
        observed_components=(principal_component,),
        axial_distances_m=distances,
        axial_peak_intensities=principal_curve,
        component_axial_peak_intensities={
            name: (
                principal_curve
                if name == principal_component
                else tuple(0.0 for _ in distances)
            )
            for name in field.component_names
        },
        frame=field.frame,
        medium=field.medium,
        basis=field.basis,
        electric_components=components,
        source_references=(field_reference,),
        incident_reference_power=field.incident_reference_power,
        transmitted_aperture_power=transmitted,
        realization={
            "identity": "metacraft.field.angular_spectrum",
            "implementation": "torch",
            "device": "cpu",
            "complex_dtype": "complex128",
            "real_dtype": "float64",
            "convention": {"padding_factor": 2},
            "working_memory_bytes": 1024**3,
            "actual_working_memory_bytes": 1024**3,
            "axial_batch_size": len(distances),
        },
    )


def _immutable(values: numpy.ndarray) -> numpy.ndarray:
    samples = numpy.array(values, dtype="<c16", order="C", copy=True)
    samples.setflags(write=False)
    return samples

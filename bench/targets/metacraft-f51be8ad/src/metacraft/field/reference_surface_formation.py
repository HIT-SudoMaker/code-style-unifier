from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import ClassVar, final

import numpy

from ..authority import Document, Reference
from ..authority.reference import reference_matches
from .rectilinear import RectilinearPlane
from .sample import (
    ComponentBasis,
    CoordinateFrame,
    Field,
    FieldComponent,
    Medium,
    PlaneSurface,
)


@final
@dataclass(frozen=True, slots=True)
class ReferenceSurfaceFormationInput:
    """
    Bind one raw periodic observation to its field context and sources.
    """

    wavelength_m: float
    surface: RectilinearPlane
    frame: CoordinateFrame
    medium: Medium
    basis: ComponentBasis
    electric_components: tuple[FieldComponent, ...]
    source_references: tuple[Reference, ...]
    incident_reference_power: float

    def __post_init__(self) -> None:
        """
        Require one complete closed periodic observation.
        """

        if (
            not _is_positive_finite(self.wavelength_m)
            or type(self.surface) is not RectilinearPlane
            or type(self.frame) is not CoordinateFrame
            or type(self.medium) is not Medium
            or type(self.basis) is not ComponentBasis
            or type(self.electric_components) is not tuple
            or any(
                type(component) is not FieldComponent
                for component in self.electric_components
            )
            or tuple(component.name for component in self.electric_components)
            != self.basis.components
            or type(self.source_references) is not tuple
            or not self.source_references
            or any(type(reference) is not Reference for reference in self.source_references)
            or len(set(self.source_references)) != len(self.source_references)
            or not _is_positive_finite(self.incident_reference_power)
            or not math.isclose(
                self.surface.period_m,
                float(
                    self.surface.vertical_coordinates_m[-1]
                    - self.surface.vertical_coordinates_m[0]
                ),
                rel_tol=1e-9,
                abs_tol=1e-15,
            )
        ):
            raise ValueError("periodic_reference_surface_observation_invalid")

        values = tuple(component.values for component in self.electric_components)
        if any(value.shape != self.surface.shape for value in values):
            raise ValueError("rectilinear_component_shape_mismatch")
        if any(
            not (
                numpy.allclose(value[0], value[-1], rtol=1e-9, atol=1e-15)
                and numpy.allclose(
                    value[:, 0],
                    value[:, -1],
                    rtol=1e-9,
                    atol=1e-15,
                )
            )
            for value in values
        ):
            raise ValueError("reference_surface_formation_periodic_seam_mismatch")


@final
@dataclass(frozen=True, slots=True)
class UniformReferenceSurfaceFormation:
    """
    Bind the frozen formation realization to its exact qualification.
    """

    realization_identity: str
    qualification_reference: Reference

    samples_per_period: ClassVar[int] = 24
    maximum_batch_size: ClassVar[int] = 256

    def __post_init__(self) -> None:
        """
        Accept only the exact independent qualification reference.
        """

        expected_document = uniform_reference_surface_formation_qualification_document()
        if (
            self.realization_identity != "periodic_rectilinear_bilinear_v1"
            or type(self.qualification_reference) is not Reference
            or not reference_matches(
                self.qualification_reference,
                expected_document.to_bytes(),
            )
        ):
            raise ValueError("reference_surface_formation_unqualified")

    @property
    def accepted_thresholds(self) -> dict[str, float]:
        """
        Return the frozen qualification thresholds.
        """

        return {
            "maximum_error": 0.0093,
            "power_change": 0.0006,
            "relative_l2_error": 0.0081,
        }

    @property
    def accepted_evidence(self) -> dict[str, dict[str, float]]:
        """
        Return the read-only Native evidence used to freeze realization.
        """

        return {
            "x": {
                "maximum_error": 0.00926499,
                "power_change_20_to_24": 0.000571006,
                "relative_l2_error": 0.00798322,
            },
            "y": {
                "maximum_error": 0.00811822,
                "power_change_20_to_24": 0.000236897,
                "relative_l2_error": 0.00789876,
            },
        }


def uniform_reference_surface_formation_qualification_document() -> Document:
    """
    Return the exact independently admissible frozen qualification.
    """

    return Document(
        "metacraft.field.uniform_reference_surface_formation_qualification",
        {
            "algorithm": "periodic_rectilinear_bilinear_v1",
            "batch": {"maximum_size": 256, "order_preserving": True},
            "complex_dtype": "complex128",
            "device": "cpu",
            "evidence": {
                "x": {
                    "maximum_error": "0.00926499",
                    "power_change_20_to_24": "0.000571006",
                    "relative_l2_error": "0.00798322",
                },
                "y": {
                    "maximum_error": "0.00811822",
                    "power_change_20_to_24": "0.000236897",
                    "relative_l2_error": "0.00789876",
                },
            },
            "qualified": True,
            "sampling": {
                "axes": "origin + index * period / samples_per_period",
                "boundary": "closed raw axes to half-open uniform axes",
                "extrapolation": False,
                "normalization": False,
                "samples_per_period": 24,
            },
            "thresholds": {
                "maximum_error": "0.0093",
                "power_change": "0.0006",
                "relative_l2_error": "0.0081",
            },
        },
    )


def form_uniform_reference_surfaces(
    observations: tuple[ReferenceSurfaceFormationInput, ...],
    formation: UniformReferenceSurfaceFormation,
) -> tuple[Field, ...]:
    """
    Form one bounded common-grid batch after complete preflight.
    """

    _preflight(observations, formation)
    return tuple(_form_one(observation, formation) for observation in observations)


def _preflight(
    observations: tuple[ReferenceSurfaceFormationInput, ...],
    formation: UniformReferenceSurfaceFormation,
) -> None:
    if type(formation) is not UniformReferenceSurfaceFormation:
        raise ValueError("reference_surface_formation_unqualified")
    if (
        type(observations) is not tuple
        or not observations
        or len(observations) > formation.maximum_batch_size
        or any(
            type(observation) is not ReferenceSurfaceFormationInput
            for observation in observations
        )
    ):
        raise ValueError("reference_surface_formation_batch_mismatch")

    context = _context(observations[0])
    if any(_context(observation) != context for observation in observations[1:]):
        raise ValueError("reference_surface_formation_batch_mismatch")

    source_references = tuple(
        reference
        for observation in observations
        for reference in observation.source_references
    )
    if (
        formation.qualification_reference in source_references
        or len(set(source_references)) != len(source_references)
    ):
        raise ValueError("reference_surface_formation_batch_mismatch")


def _context(observation: ReferenceSurfaceFormationInput) -> tuple[object, ...]:
    return (
        observation.surface.period_m,
        float(observation.surface.horizontal_coordinates_m[0]),
        float(observation.surface.vertical_coordinates_m[0]),
        observation.surface.position_m,
        observation.frame,
        observation.medium,
        observation.basis,
        observation.wavelength_m,
    )


def _is_positive_finite(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    numeric_value = float(value)
    return math.isfinite(numeric_value) and numeric_value > 0


def _form_one(
    observation: ReferenceSurfaceFormationInput,
    formation: UniformReferenceSurfaceFormation,
) -> Field:
    period_m = observation.surface.period_m
    sample_count = formation.samples_per_period
    horizontal_targets_m = (
        observation.surface.horizontal_coordinates_m[0]
        + numpy.arange(sample_count, dtype=numpy.float64)
        * (period_m / sample_count)
    )
    vertical_targets_m = (
        observation.surface.vertical_coordinates_m[0]
        + numpy.arange(sample_count, dtype=numpy.float64)
        * (period_m / sample_count)
    )
    components = tuple(
        FieldComponent(
            component.name,
            _periodic_bilinear(
                component.values,
                observation.surface,
                horizontal_targets_m,
                vertical_targets_m,
            ),
        )
        for component in observation.electric_components
    )
    return Field(
        wavelength_m=observation.wavelength_m,
        surface=PlaneSurface(
            position_m=observation.surface.position_m,
            spacing_m=period_m / sample_count,
            shape=(sample_count, sample_count),
        ),
        frame=observation.frame,
        medium=observation.medium,
        basis=observation.basis,
        electric_components=components,
        source_references=(
            *observation.source_references,
            formation.qualification_reference,
        ),
        incident_reference_power=observation.incident_reference_power,
    )


def _periodic_bilinear(
    values: numpy.ndarray,
    surface: RectilinearPlane,
    horizontal_targets_m: numpy.ndarray,
    vertical_targets_m: numpy.ndarray,
) -> numpy.ndarray:
    horizontal_coordinates_m = surface.horizontal_coordinates_m
    vertical_coordinates_m = surface.vertical_coordinates_m
    samples = numpy.asarray(values, dtype=numpy.complex128)
    horizontal_left = (
        numpy.searchsorted(
            horizontal_coordinates_m,
            horizontal_targets_m,
            side="right",
        )
        - 1
    )
    vertical_left = (
        numpy.searchsorted(
            vertical_coordinates_m,
            vertical_targets_m,
            side="right",
        )
        - 1
    )
    if (
        numpy.any(horizontal_left < 0)
        or numpy.any(horizontal_left >= horizontal_coordinates_m.size - 1)
        or numpy.any(vertical_left < 0)
        or numpy.any(vertical_left >= vertical_coordinates_m.size - 1)
    ):
        raise ValueError("reference_surface_formation_extrapolation_required")

    horizontal_weight = (
        horizontal_targets_m - horizontal_coordinates_m[horizontal_left]
    ) / (
        horizontal_coordinates_m[horizontal_left + 1]
        - horizontal_coordinates_m[horizontal_left]
    )
    along_horizontal = (
        samples[:, horizontal_left] * (1.0 - horizontal_weight)[None, :]
        + samples[:, horizontal_left + 1] * horizontal_weight[None, :]
    )
    vertical_weight = (
        vertical_targets_m - vertical_coordinates_m[vertical_left]
    ) / (
        vertical_coordinates_m[vertical_left + 1]
        - vertical_coordinates_m[vertical_left]
    )
    formed = (
        along_horizontal[vertical_left, :] * (1.0 - vertical_weight)[:, None]
        + along_horizontal[vertical_left + 1, :] * vertical_weight[:, None]
    )
    result = numpy.asarray(formed, dtype=numpy.complex128, order="C")
    if (
        result.shape
        != (UniformReferenceSurfaceFormation.samples_per_period,) * 2
        or result.dtype != numpy.dtype(numpy.complex128)
        or not result.flags.c_contiguous
        or not numpy.isfinite(result).all()
    ):
        raise ValueError("reference_surface_formation_numerical_contract_failed")
    result.setflags(write=False)
    return result

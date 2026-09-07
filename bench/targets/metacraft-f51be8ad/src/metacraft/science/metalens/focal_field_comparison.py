from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math

import numpy
import torch

from ...authority import Document, Reference
from ...field import Field, PlaneSurface
from ...field.agreement import (
    FieldAgreementGridMismatch,
    compare_complex_vector_fields,
)
from .focus import FocalRegion

FOCAL_FIELD_COMPARISON_SCHEMA = (
    "metacraft.science.metalens.unit_integral_focal_field_comparison"
)


class FocalComparisonComponentsMismatch(ValueError):
    """
    Report a focal comparison without the complete Cartesian field.
    """


class FocalComparisonGridMismatch(ValueError):
    """
    Report focal fields sampled on different comparison grids.
    """


def require_matching_focal_field(
    focal_region: FocalRegion,
    reference_field: Field,
    *,
    comparison_shape: tuple[int, int],
) -> None:
    """
    Require one reference on the observed physical comparison grid.
    """

    comparison_surface = PlaneSurface(
        focal_region.focus_plane_position_m,
        focal_region.spacing_m,
        comparison_shape,
    )
    if (
        reference_field.wavelength_m != focal_region.wavelength_m
        or reference_field.medium != focal_region.medium
        or reference_field.frame != focal_region.frame
        or reference_field.surface != comparison_surface
    ):
        raise FocalComparisonGridMismatch("focal_comparison_grid_mismatch")


def focal_comparison_slices(
    focal_region: FocalRegion,
    *,
    numerical_aperture: float,
) -> tuple[slice, slice]:
    """
    Select the centered comparison region for one focal-field contract.
    """

    target_samples = (
        math.ceil(
            4.0
            * focal_region.wavelength_m
            / (numerical_aperture * focal_region.spacing_m)
        )
        + 1
    )
    comparison_shape = tuple(
        _matching_parity_count(target_samples, available)
        for available in focal_region.shape
    )
    return centered_focal_slices(
        focal_region.shape,
        (comparison_shape[0], comparison_shape[1]),
    )


def centered_focal_slices(
    available_shape: tuple[int, int],
    selected_shape: tuple[int, int],
) -> tuple[slice, slice]:
    """
    Center one parity-matched focal region inside an available plane.
    """

    slices = []
    for available, selected in zip(
        available_shape,
        selected_shape,
        strict=True,
    ):
        if selected < 1 or selected > available or selected % 2 != available % 2:
            raise FocalComparisonGridMismatch("focal_comparison_grid_mismatch")
        start = (available - selected) // 2
        slices.append(slice(start, start + selected))
    return slices[0], slices[1]


def _matching_parity_count(requested: int, available: int) -> int:
    selected = min(max(requested, 2), available)
    if selected % 2 != available % 2:
        selected -= 1
    return max(selected, 1)


@dataclass(frozen=True, slots=True)
class FocalFieldComparison:
    """
    Compares one realized vector field with one ideal aplanatic reference.
    """

    observed_field_reference: Reference
    ideal_field_reference: Reference
    observed_binding_reference: Reference
    ideal_binding_reference: Reference
    observed_method: str
    ideal_method: str
    aligned_complex_error: float
    unit_integral_intensity_error: float
    observed_to_ideal_scale: complex
    input_longitudinal_power_w: float
    output_longitudinal_power_w: float

    def __post_init__(self) -> None:
        """
        Freeze one complete, finite, threshold-free comparison.
        """

        if not self.observed_method or not self.ideal_method:
            raise ValueError("focal_comparison_method_empty")
        if (
            not math.isfinite(self.aligned_complex_error)
            or self.aligned_complex_error < 0
            or not math.isfinite(self.unit_integral_intensity_error)
            or self.unit_integral_intensity_error < 0
            or not math.isfinite(self.observed_to_ideal_scale.real)
            or not math.isfinite(self.observed_to_ideal_scale.imag)
            or not math.isfinite(self.input_longitudinal_power_w)
            or self.input_longitudinal_power_w < 0
            or not math.isfinite(self.output_longitudinal_power_w)
            or self.output_longitudinal_power_w < 0
        ):
            raise ValueError("focal_comparison_value_invalid")

    def document(self) -> Document:
        """
        Encode observed-versus-ideal field evidence without outside truth.
        """

        return Document(
            FOCAL_FIELD_COMPARISON_SCHEMA,
            {
                "observed_field_reference": (
                    self.observed_field_reference.as_mapping()
                ),
                "observed_binding_reference": (
                    self.observed_binding_reference.as_mapping()
                ),
                "observed_method": self.observed_method,
                "aligned_complex_error": format(
                    self.aligned_complex_error,
                    ".17g",
                ),
                "unit_integral_intensity_error": format(
                    self.unit_integral_intensity_error,
                    ".17g",
                ),
                "observed_to_ideal_scale": {
                    "real": format(self.observed_to_ideal_scale.real, ".17g"),
                    "imaginary": format(
                        self.observed_to_ideal_scale.imag,
                        ".17g",
                    ),
                },
                "ideal_field_reference": (self.ideal_field_reference.as_mapping()),
                "ideal_binding_reference": (self.ideal_binding_reference.as_mapping()),
                "ideal_method": self.ideal_method,
                "input_longitudinal_power_w": format(
                    self.input_longitudinal_power_w,
                    ".17g",
                ),
                "output_longitudinal_power_w": format(
                    self.output_longitudinal_power_w,
                    ".17g",
                ),
            },
        )

    @classmethod
    def from_document(cls, document: Document) -> FocalFieldComparison:
        """
        Restore one comparison without rerunning either field method.
        """

        if document.schema_identifier != FOCAL_FIELD_COMPARISON_SCHEMA:
            raise ValueError("focal_comparison_schema_invalid")
        values = _mapping(
            document.values,
            "focal_comparison_document_invalid",
        )
        if set(values) != {
            "observed_field_reference",
            "observed_binding_reference",
            "observed_method",
            "aligned_complex_error",
            "unit_integral_intensity_error",
            "observed_to_ideal_scale",
            "ideal_field_reference",
            "ideal_binding_reference",
            "ideal_method",
            "input_longitudinal_power_w",
            "output_longitudinal_power_w",
        }:
            raise ValueError("focal_comparison_document_invalid")
        scale = _mapping(
            values["observed_to_ideal_scale"],
            "focal_comparison_document_invalid",
        )
        if set(scale) != {"real", "imaginary"}:
            raise ValueError("focal_comparison_document_invalid")
        restored = cls(
            observed_field_reference=_reference(values["observed_field_reference"]),
            observed_binding_reference=_reference(values["observed_binding_reference"]),
            ideal_field_reference=_reference(values["ideal_field_reference"]),
            ideal_binding_reference=_reference(values["ideal_binding_reference"]),
            observed_method=str(values["observed_method"]),
            ideal_method=str(values["ideal_method"]),
            aligned_complex_error=float(str(values["aligned_complex_error"])),
            unit_integral_intensity_error=float(
                str(values["unit_integral_intensity_error"])
            ),
            observed_to_ideal_scale=complex(
                float(str(scale["real"])),
                float(str(scale["imaginary"])),
            ),
            input_longitudinal_power_w=float(str(values["input_longitudinal_power_w"])),
            output_longitudinal_power_w=float(
                str(values["output_longitudinal_power_w"])
            ),
        )
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("focal_comparison_document_mismatch")
        return restored


def compare_vector_fields(
    observed_components: Mapping[str, numpy.ndarray],
    ideal_components: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    *,
    observed_field_reference: Reference,
    ideal_field_reference: Reference,
    observed_binding_reference: Reference,
    ideal_binding_reference: Reference,
    observed_method: str,
    ideal_method: str,
    input_longitudinal_power_w: float,
    output_longitudinal_power_w: float,
) -> FocalFieldComparison:
    """
    Compare complex x/y/z samples after both methods establish one grid.
    """

    if set(observed_components) != {"x", "y", "z"}:
        raise FocalComparisonComponentsMismatch(
            "focal_comparison_components_incomplete"
        )
    ideal_by_component: dict[str, torch.Tensor] = dict(
        zip(("x", "y", "z"), ideal_components, strict=True)
    )
    try:
        agreement = compare_complex_vector_fields(
            observed_components,
            ideal_by_component,
        )
    except FieldAgreementGridMismatch as error:
        raise FocalComparisonGridMismatch("focal_comparison_grid_mismatch") from error
    return FocalFieldComparison(
        observed_field_reference=observed_field_reference,
        ideal_field_reference=ideal_field_reference,
        observed_binding_reference=observed_binding_reference,
        ideal_binding_reference=ideal_binding_reference,
        observed_method=observed_method,
        ideal_method=ideal_method,
        aligned_complex_error=agreement.aligned_complex_error,
        unit_integral_intensity_error=(agreement.unit_integral_intensity_error),
        observed_to_ideal_scale=agreement.observed_to_reference_scale,
        input_longitudinal_power_w=input_longitudinal_power_w,
        output_longitudinal_power_w=output_longitudinal_power_w,
    )


def _reference(value: object) -> Reference:
    try:
        return Reference.from_mapping(
            _mapping(value, "focal_comparison_reference_invalid")
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("focal_comparison_reference_invalid") from error


def _mapping(
    value: object,
    finding: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value

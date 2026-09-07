from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
import math

import torch

from ..authority import Document, Reference
from ..authority.reference import reference_matches
from .evidence import (
    admit_components,
    field_document,
    restore_field,
)
from .sample import Field


REFERENCE_SURFACE_SCHEMA = "metacraft.science.reference_surface_response"
REFERENCE_SURFACE_COMPARISON_SCHEMA = (
    "metacraft.science.reference_surface_comparison"
)

LOCALLY_PERIODIC = "locally periodic"


class RequestedInputBasis(str, Enum):
    """
    Names the exact incident basis requested from one periodic response.
    """

    X_LINEAR = "x linear"
    Y_LINEAR = "y linear"
    RIGHT_CIRCULAR = "right circular"
    LEFT_CIRCULAR = "left circular"


@dataclass(frozen=True, slots=True)
class ReferenceSurfaceResponse:
    """
    Retains one sampled complex response without collapsing it to G0.
    """

    field: Field
    requested_input_basis: RequestedInputBasis
    order_regime: str
    transmitted_power: float
    assembly_model: str = LOCALLY_PERIODIC

    def __post_init__(self) -> None:
        """
        Keep the two exact physical annotations closed and route-neutral.
        """

        if self.order_regime not in {"zeroth order", "multi order"}:
            raise ValueError("reference_surface_order_regime_invalid")
        if (
            not math.isfinite(self.transmitted_power)
            or self.transmitted_power < 0
        ):
            raise ValueError("reference_surface_transmitted_power_invalid")
        if self.assembly_model != LOCALLY_PERIODIC:
            raise ValueError("reference_surface_assembly_model_invalid")


@dataclass(frozen=True, slots=True)
class AdmittedReferenceSurface:
    """
    Couples one restored response to its exact admitted document reference.
    """

    response: ReferenceSurfaceResponse
    reference: Reference

    def __post_init__(self) -> None:
        if self.reference.media_type != "application/json":
            raise ValueError("reference_surface_reference_invalid")


@dataclass(frozen=True, slots=True)
class ReferenceSurfaceComparison:
    """
    Reports a bounded diagnostic without turning it into a success threshold.
    """

    complex_field_difference: Mapping[str, float]
    power_difference: float
    locally_periodic_transmitted_power: float
    full_wave_transmitted_power: float
    sample_count: int
    locally_periodic_reference: Reference
    full_wave_reference: Reference

    def __post_init__(self) -> None:
        values = tuple(self.complex_field_difference.values())
        if (
            not self.complex_field_difference
            or not all(math.isfinite(value) and value >= 0 for value in values)
            or not math.isfinite(self.power_difference)
            or not math.isfinite(self.locally_periodic_transmitted_power)
            or not math.isfinite(self.full_wave_transmitted_power)
            or self.locally_periodic_transmitted_power < 0
            or self.full_wave_transmitted_power < 0
            or self.sample_count <= 0
        ):
            raise ValueError("reference_surface_comparison_invalid")

    def document(self) -> Document:
        """
        Encode measured differences only; no hidden verdict is added.
        """

        return Document(
            REFERENCE_SURFACE_COMPARISON_SCHEMA,
            {
                "complex_field_difference": {
                    name: format(value, ".17g")
                    for name, value in sorted(
                        self.complex_field_difference.items()
                    )
                },
                "locally_periodic": (
                    self.locally_periodic_reference.as_mapping()
                ),
                "locally_periodic_transmitted_power": format(
                    self.locally_periodic_transmitted_power,
                    ".17g",
                ),
                "power_difference": format(self.power_difference, ".17g"),
                "sample_count": self.sample_count,
                "full_wave_reference": self.full_wave_reference.as_mapping(),
                "full_wave_transmitted_power": format(
                    self.full_wave_transmitted_power,
                    ".17g",
                ),
            },
        )


def admit_response_components(
    response: ReferenceSurfaceResponse,
    admit: Callable[..., Reference],
) -> tuple[dict[str, Reference], dict[str, Reference]]:
    """
    Admit the exact complex arrays before their small response manifest.
    """

    return admit_components(
        response.field.electric_components,
        response.field.magnetic_components,
        admit,
    )


def reference_surface_document(
    response: ReferenceSurfaceResponse,
    electric_references: Mapping[str, Reference],
    *,
    magnetic_references: Mapping[str, Reference] | None = None,
) -> Document:
    """
    Encode one route-neutral reference-surface response.
    """

    base = field_document(
        REFERENCE_SURFACE_SCHEMA,
        response.field,
        electric_references,
        magnetic_component_references=magnetic_references,
    )
    return Document(
        REFERENCE_SURFACE_SCHEMA,
        {
            **base.values,
            "assembly_model": response.assembly_model,
            "order_regime": response.order_regime,
            "requested_input_basis": response.requested_input_basis.value,
            "transmitted_power": format(response.transmitted_power, ".17g"),
        },
    )


def restore_reference_surface(
    reference: Reference,
    fetch: Callable[[Reference], bytes],
) -> AdmittedReferenceSurface:
    """
    Restore one admitted response and all exact component objects it cites.
    """

    body = fetch(reference)
    if not reference_matches(reference, body):
        raise ValueError("reference_surface_reference_mismatch")
    try:
        document = Document.from_bytes(body)
    except ValueError as error:
        raise ValueError("reference_surface_document_invalid") from error
    if document.schema_identifier != REFERENCE_SURFACE_SCHEMA:
        raise ValueError("reference_surface_schema_mismatch")
    try:
        field = restore_field(document, fetch)
        assembly_model = str(document.values["assembly_model"])
        order_regime = str(document.values["order_regime"])
        requested_input_basis = RequestedInputBasis(
            str(document.values["requested_input_basis"])
        )
        transmitted_power = float(
            str(document.values["transmitted_power"])
        )
        response = ReferenceSurfaceResponse(
            field=field,
            requested_input_basis=requested_input_basis,
            order_regime=order_regime,
            transmitted_power=transmitted_power,
            assembly_model=assembly_model,
        )
        electric, magnetic = _component_references(document.values)
        rebuilt = reference_surface_document(
            response,
            electric,
            magnetic_references=magnetic,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("reference_surface_document_invalid") from error
    if rebuilt.to_bytes() != body:
        raise ValueError("reference_surface_document_mismatch")
    return AdmittedReferenceSurface(response, reference)


def compare_reference_surfaces(
    locally_periodic: Field,
    full_wave: Field,
    *,
    locally_periodic_reference: Reference,
    full_wave_reference: Reference,
    locally_periodic_transmitted_power: float,
    full_wave_transmitted_power: float,
    maximum_samples: int = 65_536,
) -> ReferenceSurfaceComparison:
    """
    Compare one bounded small aperture without declaring a pass threshold.
    """

    _require_matching_fields(locally_periodic, full_wave)
    sample_count = math.prod(locally_periodic.surface.shape)
    if sample_count > maximum_samples:
        raise ValueError("reference_surface_comparison_unbounded")
    differences: dict[str, float] = {}
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    for name in locally_periodic.component_names:
        local = torch.tensor(
            locally_periodic.electric(name),
            dtype=torch.complex128,
            device=device,
        )
        full_wave_component = torch.tensor(
            full_wave.electric(name),
            dtype=torch.complex128,
            device=device,
        )
        residual = torch.linalg.vector_norm(local - full_wave_component)
        scale = torch.linalg.vector_norm(full_wave_component)
        normalized = residual if scale.item() == 0 else residual / scale
        differences[name] = normalized.item()
    if (
        not math.isfinite(locally_periodic_transmitted_power)
        or not math.isfinite(full_wave_transmitted_power)
        or locally_periodic_transmitted_power < 0
        or full_wave_transmitted_power < 0
    ):
        raise ValueError("reference_surface_power_invalid")
    power_difference = (
        locally_periodic_transmitted_power - full_wave_transmitted_power
        if full_wave_transmitted_power == 0
        else (
            locally_periodic_transmitted_power - full_wave_transmitted_power
        )
        / full_wave_transmitted_power
    )
    return ReferenceSurfaceComparison(
        complex_field_difference=differences,
        power_difference=power_difference,
        locally_periodic_transmitted_power=(
            locally_periodic_transmitted_power
        ),
        full_wave_transmitted_power=full_wave_transmitted_power,
        sample_count=sample_count,
        locally_periodic_reference=locally_periodic_reference,
        full_wave_reference=full_wave_reference,
    )


def _require_matching_fields(first: Field, second: Field) -> None:
    if (
        first.wavelength_m != second.wavelength_m
        or first.surface != second.surface
        or first.frame != second.frame
        or first.medium != second.medium
        or first.basis is not second.basis
        or first.component_names != second.component_names
    ):
        raise ValueError("reference_surface_comparison_context_mismatch")


def _component_references(
    values: Mapping[str, object],
) -> tuple[dict[str, Reference], dict[str, Reference]]:
    def restore(value: object) -> dict[str, Reference]:
        """
        Restore one named component-reference mapping.
        """

        if not isinstance(value, Mapping):
            raise ValueError("reference_surface_components_invalid")
        restored = {}
        for name, reference in value.items():
            if not isinstance(name, str) or not isinstance(
                reference,
                Mapping,
            ):
                raise ValueError("reference_surface_components_invalid")
            restored[name] = Reference.from_mapping(reference)
        return restored

    electric = restore(values["electric_components"])
    magnetic = restore(values["magnetic_components"])
    return electric, magnetic

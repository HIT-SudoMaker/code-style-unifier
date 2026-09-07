from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math

import numpy
import torch


class FieldAgreementGridMismatch(ValueError):
    """
    Report component arrays that do not share one comparison grid.
    """


@dataclass(frozen=True, slots=True)
class ComplexVectorFieldAgreement:
    """
    Separate convention, vector-shape, and intensity disagreement.
    """

    component_names: tuple[str, ...]
    raw_complex_error: float
    aligned_complex_error: float
    unit_integral_intensity_error: float
    observed_to_reference_scale: complex

    def __post_init__(self) -> None:
        """
        Require one finite non-negative comparison result.
        """

        scale = complex(self.observed_to_reference_scale)
        errors = (
            self.raw_complex_error,
            self.aligned_complex_error,
            self.unit_integral_intensity_error,
        )
        if (
            not self.component_names
            or len(set(self.component_names)) != len(self.component_names)
            or any(not name for name in self.component_names)
            or any(not math.isfinite(value) or value < 0 for value in errors)
            or not math.isfinite(scale.real)
            or not math.isfinite(scale.imag)
        ):
            raise ValueError("field_agreement_invalid")
        object.__setattr__(self, "observed_to_reference_scale", scale)


def compare_complex_vector_fields(
    observed_components: Mapping[
        str,
        numpy.ndarray | torch.Tensor,
    ],
    reference_components: Mapping[
        str,
        numpy.ndarray | torch.Tensor,
    ],
) -> ComplexVectorFieldAgreement:
    """
    Compare corresponding complex vector samples on one established grid.
    """

    if not observed_components or set(observed_components) != set(reference_components):
        raise ValueError("field_agreement_components_mismatch")
    component_names = tuple(sorted(observed_components))
    device = _comparison_device(
        tuple(reference_components.values()),
        tuple(observed_components.values()),
    )
    observed = tuple(
        _complex_samples(observed_components[name], device=device)
        for name in component_names
    )
    reference = tuple(
        _complex_samples(reference_components[name], device=device)
        for name in component_names
    )
    shapes = {tuple(component.shape) for component in (*observed, *reference)}
    if len(shapes) != 1:
        raise FieldAgreementGridMismatch("field_agreement_grid_mismatch")
    observed_vector = torch.cat(tuple(component.reshape(-1) for component in observed))
    reference_vector = torch.cat(
        tuple(component.reshape(-1) for component in reference)
    )
    reference_norm = torch.linalg.vector_norm(reference_vector)
    observed_energy = torch.vdot(observed_vector, observed_vector).real
    if reference_norm == 0:
        raise ValueError("field_agreement_reference_zero")
    if observed_energy == 0:
        raise ValueError("field_agreement_observed_zero")
    alignment = torch.vdot(observed_vector, reference_vector) / observed_energy
    raw_error = (
        torch.linalg.vector_norm(observed_vector - reference_vector) / reference_norm
    )
    aligned_error = (
        torch.linalg.vector_norm(alignment * observed_vector - reference_vector)
        / reference_norm
    )
    observed_intensity = (
        torch.stack(tuple(component.abs().square() for component in observed))
        .sum(dim=0)
        .reshape(-1)
    )
    reference_intensity = (
        torch.stack(tuple(component.abs().square() for component in reference))
        .sum(dim=0)
        .reshape(-1)
    )
    observed_intensity_sum = torch.sum(observed_intensity)
    reference_intensity_sum = torch.sum(reference_intensity)
    if (
        not bool(torch.isfinite(observed_intensity_sum).item())
        or not bool(torch.isfinite(reference_intensity_sum).item())
        or bool((observed_intensity_sum <= 0).item())
        or bool((reference_intensity_sum <= 0).item())
    ):
        raise ValueError("field_agreement_intensity_zero")
    observed_distribution = observed_intensity / observed_intensity_sum
    reference_distribution = reference_intensity / reference_intensity_sum
    reference_distribution_norm = torch.linalg.vector_norm(
        reference_distribution
    )
    intensity_error = (
        torch.linalg.vector_norm(
            observed_distribution - reference_distribution
        )
        / reference_distribution_norm
    )
    return ComplexVectorFieldAgreement(
        component_names=component_names,
        raw_complex_error=float(raw_error.detach().cpu()),
        aligned_complex_error=float(aligned_error.detach().cpu()),
        unit_integral_intensity_error=float(intensity_error.detach().cpu()),
        observed_to_reference_scale=complex(alignment.detach().cpu()),
    )


def _comparison_device(
    first: tuple[numpy.ndarray | torch.Tensor, ...],
    second: tuple[numpy.ndarray | torch.Tensor, ...],
) -> torch.device:
    for component in (*first, *second):
        if isinstance(component, torch.Tensor):
            return component.device
    return torch.device("cpu")


def _complex_samples(
    values: numpy.ndarray | torch.Tensor,
    *,
    device: torch.device,
) -> torch.Tensor:
    samples = (
        values.to(device=device, dtype=torch.complex128)
        if isinstance(values, torch.Tensor)
        else torch.tensor(values, dtype=torch.complex128, device=device)
    )
    if samples.ndim < 1 or not bool(torch.isfinite(samples).all()):
        raise ValueError("field_agreement_samples_invalid")
    return samples


__all__ = [
    "ComplexVectorFieldAgreement",
    "FieldAgreementGridMismatch",
    "compare_complex_vector_fields",
]

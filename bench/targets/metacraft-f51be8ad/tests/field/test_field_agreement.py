from __future__ import annotations

import pytest
import torch

from metacraft.field.agreement import (
    FieldAgreementGridMismatch,
    compare_complex_vector_fields,
)


def test_field_agreement_separates_global_convention_from_shape_error() -> None:
    """Do not report one common complex scale as propagation instability."""

    observed = {
        "x": torch.tensor([1 + 1j, 2 - 0.5j], dtype=torch.complex128),
        "y": torch.tensor([0.2j, -0.3 + 0.1j], dtype=torch.complex128),
        "z": torch.tensor([0.1, -0.2j], dtype=torch.complex128),
    }
    common_scale = 1.7 * torch.exp(
        torch.tensor(0.4j, dtype=torch.complex128)
    )
    reference = {
        name: common_scale * component
        for name, component in observed.items()
    }

    agreement = compare_complex_vector_fields(observed, reference)

    assert agreement.raw_complex_error > 0.5
    assert agreement.aligned_complex_error < 1e-15
    assert agreement.unit_integral_intensity_error < 1e-15
    assert agreement.component_names == ("x", "y", "z")


def test_field_agreement_compares_unit_integral_intensity_distributions() -> None:
    observed = {
        "x": torch.sqrt(
            torch.tensor([1.0, 3.0], dtype=torch.float64)
        ).to(torch.complex128)
    }
    reference = {
        "x": torch.sqrt(
            torch.tensor([2.0, 2.0], dtype=torch.float64)
        ).to(torch.complex128)
    }

    agreement = compare_complex_vector_fields(observed, reference)

    assert agreement.unit_integral_intensity_error == pytest.approx(0.5)


def test_field_agreement_grid_mismatch_has_one_typed_owner() -> None:
    with pytest.raises(FieldAgreementGridMismatch):
        compare_complex_vector_fields(
            {"x": torch.ones(2, dtype=torch.complex128)},
            {"x": torch.ones(3, dtype=torch.complex128)},
        )


@pytest.mark.parametrize(
    ("observed", "reason"),
    (
        (torch.zeros(2, dtype=torch.complex128), "field_agreement_observed_zero"),
        (
            torch.tensor([complex("nan"), 1.0], dtype=torch.complex128),
            "field_agreement_samples_invalid",
        ),
    ),
)
def test_field_agreement_rejects_invalid_intensity_before_normalization(
    observed: torch.Tensor,
    reason: str,
) -> None:
    with pytest.raises(ValueError, match=reason):
        compare_complex_vector_fields(
            {"x": observed},
            {"x": torch.ones(2, dtype=torch.complex128)},
        )

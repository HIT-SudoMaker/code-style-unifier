from __future__ import annotations

import pytest
import torch

from chromatix_next._numerics._certified_predicates import (
    _binary_rounding_could_change_sign,
    dot_sign,
    quadratic_discriminant_sign,
    scaled_squared_norm_difference_sign,
    squared_reference_minus_squared_factor_extra_factor_sign,
    triple_product_sign,
)

FIXED_DOUBLE = torch.float64


def test_rounding_certificate_closes_smallest_subnormal_boundary() -> None:
    """
    渐进下溢界在等号处回退，紧邻上界才允许快速符号
    """

    zero = torch.tensor(0.0, dtype=FIXED_DOUBLE)
    smallest_subnormal = torch.nextafter(
        zero,
        torch.tensor(torch.inf, dtype=FIXED_DOUBLE),
    )
    bound_value = 5.0 * smallest_subnormal
    next_value = torch.nextafter(
        bound_value,
        torch.tensor(torch.inf, dtype=FIXED_DOUBLE),
    )
    certificate_arguments = {
        "magnitude_envelope": zero,
        "operation_count": 1,
        "underflow_amplification": torch.tensor(1.0, dtype=FIXED_DOUBLE),
    }

    assert bool(
        _binary_rounding_could_change_sign(
            rounded_value=smallest_subnormal,
            **certificate_arguments,
        )
    )
    assert bool(
        _binary_rounding_could_change_sign(
            rounded_value=bound_value,
            **certificate_arguments,
        )
    )
    assert not bool(
        _binary_rounding_could_change_sign(
            rounded_value=next_value,
            **certificate_arguments,
        )
    )


@pytest.mark.parametrize(
    ("rounded_value", "magnitude_envelope", "amplification"),
    (
        (torch.inf, 0.0, 1.0),
        (torch.nan, 0.0, 1.0),
        (0.0, torch.inf, 1.0),
        (0.0, -1.0, 1.0),
        (0.0, 0.0, torch.inf),
        (0.0, 0.0, -1.0),
    ),
)
def test_rounding_certificate_rejects_invalid_or_overflowed_inputs(
    rounded_value: float,
    magnitude_envelope: float,
    amplification: float,
) -> None:
    """
    非有限快速值、包络、放大或负证书输入一律进入精确核
    """

    ambiguous = _binary_rounding_could_change_sign(
        rounded_value=torch.tensor(rounded_value, dtype=FIXED_DOUBLE),
        magnitude_envelope=torch.tensor(magnitude_envelope, dtype=FIXED_DOUBLE),
        operation_count=8,
        underflow_amplification=torch.tensor(amplification, dtype=FIXED_DOUBLE),
    )
    assert bool(ambiguous)


def test_family_operation_counts_and_amplifications_are_decisive() -> None:
    """
    合成边界杀死固定宽度、单位放大与遗漏额外因子的证书变异
    """

    zero = torch.tensor(0.0, dtype=FIXED_DOUBLE)
    smallest_subnormal = torch.nextafter(
        zero,
        torch.tensor(torch.inf, dtype=FIXED_DOUBLE),
    )

    def _is_ambiguous(
        multiple: int,
        operation_count: int,
        amplification: float,
    ) -> bool:
        return bool(
            _binary_rounding_could_change_sign(
                rounded_value=multiple * smallest_subnormal,
                magnitude_envelope=zero,
                operation_count=operation_count,
                underflow_amplification=torch.tensor(amplification, dtype=FIXED_DOUBLE),
            )
        )

    assert _is_ambiguous(15, 19, 1.0)
    assert not _is_ambiguous(15, 5, 1.0)
    assert _is_ambiguous(12, 10, 1.0)
    assert not _is_ambiguous(12, 5, 1.0)
    assert _is_ambiguous(100, 18, 9.0)
    assert not _is_ambiguous(100, 18, 1.0)
    assert _is_ambiguous(20, 8, 4.0)
    assert not _is_ambiguous(20, 8, 1.0)
    assert _is_ambiguous(100, 8, 32.0)
    assert not _is_ambiguous(100, 8, 1.0)


def test_predicate_families_supply_audited_certificate_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    五类公开判定把真实宽度计数与各自下溢放大事实交给同一证书核
    """

    import chromatix_next._numerics._certified_predicates as predicates

    observed_facts: list[tuple[int, float]] = []

    def _record_certificate_facts(
        *,
        rounded_value: torch.Tensor,
        magnitude_envelope: torch.Tensor,
        operation_count: int,
        underflow_amplification: torch.Tensor,
    ) -> torch.Tensor:
        del magnitude_envelope
        observed_facts.append(
            (operation_count, float(underflow_amplification.item())),
        )
        return torch.zeros_like(rounded_value, dtype=torch.bool)

    monkeypatch.setattr(
        predicates,
        "_binary_rounding_could_change_sign",
        _record_certificate_facts,
    )
    four_vector = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=FIXED_DOUBLE)
    predicates.dot_sign(four_vector, four_vector)
    predicates.scaled_squared_norm_difference_sign(
        torch.tensor(2.0, dtype=FIXED_DOUBLE),
        four_vector,
    )
    first_axis = torch.tensor([1.0, 0.0, 0.0], dtype=FIXED_DOUBLE)
    second_axis = torch.tensor([0.0, 1.0, 0.0], dtype=FIXED_DOUBLE)
    third_axis = torch.tensor([0.0, 0.0, 1.0], dtype=FIXED_DOUBLE)
    predicates.triple_product_sign(first_axis, second_axis, third_axis)
    predicates.quadratic_discriminant_sign(
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
        torch.tensor(3.0, dtype=FIXED_DOUBLE),
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
    )
    predicates.squared_reference_minus_squared_factor_extra_factor_sign(
        torch.tensor(8.0, dtype=FIXED_DOUBLE),
        torch.tensor(1.0, dtype=FIXED_DOUBLE),
        torch.tensor(32.0, dtype=FIXED_DOUBLE),
    )

    assert observed_facts == [
        (7, 1.0),
        (12, 1.0),
        (18, 9.0),
        (8, 4.0),
        (8, 32.0),
    ]


def test_rounding_certificate_preserves_batch_and_meta_structure() -> None:
    """
    渐进下溢证书保留批形状，Meta 保守进入精确路径
    """

    rounded_values = torch.tensor([0.0, 1.0], dtype=FIXED_DOUBLE)
    ambiguous = _binary_rounding_could_change_sign(
        rounded_value=rounded_values,
        magnitude_envelope=torch.tensor([0.0, 1.0], dtype=FIXED_DOUBLE),
        operation_count=5,
        underflow_amplification=torch.ones(2, dtype=FIXED_DOUBLE),
    )
    meta_ambiguous = _binary_rounding_could_change_sign(
        rounded_value=torch.empty((2, 3), dtype=FIXED_DOUBLE, device="meta"),
        magnitude_envelope=torch.empty((2, 3), dtype=FIXED_DOUBLE, device="meta"),
        operation_count=5,
        underflow_amplification=torch.empty((2, 3), dtype=FIXED_DOUBLE, device="meta"),
    )

    assert torch.equal(ambiguous, torch.tensor([True, False]))
    assert meta_ambiguous.shape == (2, 3)
    assert meta_ambiguous.dtype == torch.bool
    assert meta_ambiguous.device.type == "meta"


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is unavailable")
def test_rounding_certificate_matches_cpu_on_native_cuda() -> None:
    """
    渐进下溢证书在原生 CUDA 与 CPU 逐通道一致
    """

    rounded_values = torch.tensor([0.0, 1.0, torch.inf], dtype=FIXED_DOUBLE)
    magnitude_envelope = torch.tensor([0.0, 1.0, torch.inf], dtype=FIXED_DOUBLE)
    amplification = torch.tensor([1.0, 4.0, 9.0], dtype=FIXED_DOUBLE)
    cpu_result = _binary_rounding_could_change_sign(
        rounded_value=rounded_values,
        magnitude_envelope=magnitude_envelope,
        operation_count=18,
        underflow_amplification=amplification,
    )
    cuda_result = _binary_rounding_could_change_sign(
        rounded_value=rounded_values.cuda(),
        magnitude_envelope=magnitude_envelope.cuda(),
        operation_count=18,
        underflow_amplification=amplification.cuda(),
    )
    assert torch.equal(cuda_result.cpu(), cpu_result)

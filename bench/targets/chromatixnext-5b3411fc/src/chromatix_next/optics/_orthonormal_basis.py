from __future__ import annotations

import torch

from chromatix_next._tensors import (
    _materialize_finite_fixed_double_three_vector,
    is_value_readable,
)
import chromatix_next.errors as _errors

_UNIT_ROUND_OFF: float = 2.0 ** -53

_GAMMA_3: float = 3.0 * _UNIT_ROUND_OFF / (1.0 - 3.0 * _UNIT_ROUND_OFF)

AUTHORED_BASIS_ADMISSIBILITY_BUDGET: float = 8.0 * _GAMMA_3



def _materialize_authored_three_vector(
    value: object,
    *,
    field_name: str,
    error_identity: str,
    tensor_requirement: str,
    tuple_requirement: str,
) -> torch.Tensor:
    materialized = _materialize_finite_fixed_double_three_vector(value)
    if materialized is not None:
        return materialized
    if isinstance(value, torch.Tensor):
        message = (
            f"{field_name} {tensor_requirement}，"
            f"收到的形状是 {tuple(value.shape)}、dtype 是 {value.dtype}"
        )
        raise _errors.OpticalValueError(error_identity, message)
    message = f"{field_name} {tuple_requirement}，收到的是 {value!r}"
    raise _errors.OpticalValueError(error_identity, message)


def _require_authored_unit_three_vector(
    value: torch.Tensor,
    *,
    error_identity: str,
    message: str,
) -> None:
    if value.is_meta:
        return
    squared_norm = torch.dot(value, value)
    if not is_value_readable(squared_norm):
        return
    residual = (squared_norm - 1.0).abs()
    budget = AUTHORED_BASIS_ADMISSIBILITY_BUDGET
    if not bool(residual <= budget):
        raise _errors.OpticalValueError(error_identity, message)


def _require_authored_orthonormal_basis(
    tangent_x: torch.Tensor,
    tangent_y: torch.Tensor,
    *,
    not_orthogonal_identity: str,
    not_orthogonal_message: str,
) -> None:
    if tangent_x.is_meta or tangent_y.is_meta:
        return
    dot = torch.dot(tangent_x, tangent_y)
    tangent_x_squared = torch.dot(tangent_x, tangent_x)
    tangent_y_squared = torch.dot(tangent_y, tangent_y)
    if not (
        is_value_readable(dot)
        and is_value_readable(tangent_x_squared)
        and is_value_readable(tangent_y_squared)
    ):
        return
    orthogonality_budget = AUTHORED_BASIS_ADMISSIBILITY_BUDGET * torch.sqrt(
        tangent_x_squared * tangent_y_squared
    )
    if not bool(dot.abs() <= orthogonality_budget):
        raise _errors.OpticalValueError(
            not_orthogonal_identity,
            not_orthogonal_message,
        )

from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._tensors import (
    _materialize_finite_fixed_double_three_vector,
    _register_fixed_double_scalar_parameter_or_buffer,
    is_finite_fixed_double_scalar,
    is_finite_fixed_double_scalar_in_closed_interval,
    is_value_readable,
    register_fixed_double_real_scalar,
)
from chromatix_next.errors import OpticalValueError


def test_three_vector_materialization_preserves_authored_tensor_identity() -> None:
    """
    三向量只物化 Python 元组，并原样保留合格张量的身份、设备与精度
    """

    authored = torch.tensor((1.0, 2.0, 3.0), dtype=torch.float64)

    materialized = _materialize_finite_fixed_double_three_vector(authored)
    from_tuple = _materialize_finite_fixed_double_three_vector((1.0, 2.0, 3.0))

    assert materialized is authored
    assert from_tuple is not None
    assert from_tuple.dtype is torch.float64
    assert from_tuple.device.type == "cpu"
    assert torch.equal(from_tuple, authored)


def test_scalar_registration_preserves_parameter_and_buffer_roles() -> None:
    """
    标量注册对 Parameter 保持身份，对张量保持 Buffer 身份，对实数物化为 Buffer
    """

    module = torch.nn.Module()
    trainable = torch.nn.Parameter(torch.tensor(2.0, dtype=torch.float64))
    authored_buffer = torch.tensor(3.0, dtype=torch.float64)

    register_fixed_double_real_scalar(
        module,
        name="trainable",
        value=trainable,
    )
    register_fixed_double_real_scalar(
        module,
        name="authored_buffer",
        value=authored_buffer,
    )
    register_fixed_double_real_scalar(
        module,
        name="literal_buffer",
        value=4.0,
    )

    assert module.get_parameter("trainable") is trainable
    assert module.get_buffer("authored_buffer") is authored_buffer
    assert module.get_buffer("literal_buffer").dtype is torch.float64
    assert "trainable" not in dict(module.named_buffers())
    assert "authored_buffer" not in dict(module.named_parameters())


def test_parameter_or_buffer_registration_keeps_trainable_identity() -> None:
    """
    身份型标量入口保留 Parameter 与梯度图，并把 Python 实数登记为固定双精度 Buffer
    """

    module = torch.nn.Module()
    trainable = torch.nn.Parameter(torch.tensor(1.5, dtype=torch.float64))
    _register_fixed_double_scalar_parameter_or_buffer(
        module,
        name="trainable_distance",
        value=trainable,
        is_positive=True,
        error_identity="distance_invalid",
        tensor_message="invalid {value}",
        scalar_message="invalid {value}",
    )
    _register_fixed_double_scalar_parameter_or_buffer(
        module,
        name="fixed_distance",
        value=2.5,
        is_positive=True,
        error_identity="distance_invalid",
        tensor_message="invalid {value}",
        scalar_message="invalid {value}",
    )

    trainable.square().backward()

    assert module.get_parameter("trainable_distance") is trainable
    assert trainable.grad is not None
    assert float(trainable.grad) == 3.0
    assert module.get_buffer("fixed_distance").dtype is torch.float64


def test_meta_readability_is_structural_and_invalid_dtype_fails_readably() -> None:
    """
    meta 标量只通过结构判定，错误精度则以稳定域错误拒绝而不读取数值
    """

    meta_scalar = torch.empty((), dtype=torch.float64, device="meta")

    assert not is_value_readable(meta_scalar)
    assert is_finite_fixed_double_scalar(meta_scalar)

    with pytest.raises(OpticalValueError) as rejected:
        _register_fixed_double_scalar_parameter_or_buffer(
            torch.nn.Module(),
            name="distance",
            value=torch.nn.Parameter(
                torch.empty((), dtype=torch.float32, device="meta"),
            ),
            is_positive=True,
            error_identity="distance_invalid",
            tensor_message="invalid tensor {value}",
            scalar_message="invalid scalar {value}",
        )

    assert rejected.value.identity == "distance_invalid"
    assert "invalid tensor" in rejected.value.explanation


@pytest.mark.parametrize(
    ("value", "is_expected"),
    [
        (-0.25, False),
        (0, True),
        (0.5, True),
        (1, True),
        (1.25, False),
    ],
)
def test_closed_interval_admits_python_real_scalar_inclusively(
    value: int | float,
    is_expected: bool,
) -> None:
    """
    Python 有限实数包含闭区间端点，并拒绝区间外取值
    """

    assert (
        is_finite_fixed_double_scalar_in_closed_interval(
            value,
            lower_bound=0.0,
            upper_bound=1.0,
        )
        is is_expected
    )


@pytest.mark.parametrize(
    ("value", "is_expected"),
    [
        (0.0, True),
        (1.0, True),
        (-0.25, False),
        (1.25, False),
    ],
)
def test_closed_interval_admits_float64_tensor_inclusively(
    value: float,
    is_expected: bool,
) -> None:
    """
    可读零维 float64 张量包含闭区间端点，并拒绝区间外取值
    """

    tensor_value = torch.tensor(value, dtype=torch.float64)
    assert (
        is_finite_fixed_double_scalar_in_closed_interval(
            tensor_value,
            lower_bound=0.0,
            upper_bound=1.0,
        )
        is is_expected
    )


def test_closed_interval_admits_meta_float64_scalar_structurally() -> None:
    """
    Meta float64 标量仅按结构和精度准入，不读取物理值
    """

    meta_value = torch.empty((), dtype=torch.float64, device="meta")
    assert is_finite_fixed_double_scalar_in_closed_interval(
        meta_value,
        lower_bound=0.0,
        upper_bound=1.0,
    )


@pytest.mark.parametrize(
    "value",
    [
        True,
        complex(0.5, 0.0),
        float("nan"),
        float("inf"),
        -float("inf"),
        torch.tensor(0.5, dtype=torch.float32),
        torch.tensor(0.5, dtype=torch.complex128),
        torch.tensor([0.5], dtype=torch.float64),
        torch.tensor(math.nan, dtype=torch.float64),
        torch.tensor(math.inf, dtype=torch.float64),
    ],
)
def test_closed_interval_rejects_non_fixed_double_finite_scalar(
    value: object,
) -> None:
    """
    布尔、复数、非有限、非标量和非 float64 输入均被拒绝
    """

    assert not is_finite_fixed_double_scalar_in_closed_interval(
        value,
        lower_bound=0.0,
        upper_bound=1.0,
    )


def test_closed_interval_rejects_meta_non_float64_scalar() -> None:
    """
    Meta 不可读性不豁免 fixed-double 精度要求
    """

    meta_value = torch.empty((), dtype=torch.float32, device="meta")
    assert not is_finite_fixed_double_scalar_in_closed_interval(
        meta_value,
        lower_bound=0.0,
        upper_bound=1.0,
    )

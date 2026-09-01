
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next.errors import OpticalTypeError, OpticalValueError
from chromatix_next.optics.surface import Sphere


def _sphere(radius_of_curvature: object) -> Sphere:
    # 经公开构造器作者有符号曲率半径
    return Sphere(
        radius_of_curvature=radius_of_curvature,  # type: ignore[arg-type]
    )


def _assert_rejected(radius_of_curvature: object) -> None:
    # 断言曲率半径保留 Sphere 的稳定领域错误身份
    with pytest.raises(OpticalValueError) as rejected:
        _sphere(radius_of_curvature)
    assert rejected.value.identity == "sphere_radius_of_curvature_invalid"


def test_float32_parameter_is_rejected() -> None:
    """
    单精度 Parameter 不得静默进入球面状态
    """

    radius = torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float32))

    _assert_rejected(radius)


@pytest.mark.parametrize("dtype", (torch.float32, torch.float64))
def test_plain_tensor_keeps_public_type_error_priority(
    dtype: torch.dtype,
) -> None:
    """
    普通 Tensor 不越过只接受 Python scalar 或 Parameter 的接口
    """

    radius = torch.tensor(1.0, dtype=dtype)

    with pytest.raises(OpticalTypeError) as rejected:
        _sphere(radius)

    assert rejected.value.identity == "sphere_radius_of_curvature_invalid"


@pytest.mark.parametrize("radius_value", (2.0, -2.0))
def test_python_radius_materializes_as_signed_cpu_float64(
    radius_value: float,
) -> None:
    """
    Python 半径物化为 CPU float64 并保留曲率符号
    """

    sphere = _sphere(radius_value)

    assert sphere.radius_of_curvature.dtype is torch.float64
    assert sphere.radius_of_curvature.device.type == "cpu"
    assert float(sphere.radius_of_curvature) == radius_value


def test_float64_parameter_keeps_identity_and_gradient() -> None:
    """
    合格 Parameter 保留注册身份与计算图
    """

    authored = torch.nn.Parameter(torch.tensor(-2.0, dtype=torch.float64))
    sphere = _sphere(authored)

    assert sphere.radius_of_curvature is authored
    sphere.radius_of_curvature.square().backward()
    assert authored.grad is not None


def test_meta_float64_parameter_checks_only_structure() -> None:
    """
    meta Parameter 只检查零维结构与固定精度
    """

    authored = torch.nn.Parameter(
        torch.empty((), device="meta", dtype=torch.float64),
    )
    sphere = _sphere(authored)

    assert sphere.radius_of_curvature is authored


@pytest.mark.parametrize(
    "invalid_radius",
    (
        torch.nn.Parameter(torch.tensor(0.0, dtype=torch.float64)),
        torch.nn.Parameter(torch.tensor(math.nan, dtype=torch.float64)),
        torch.nn.Parameter(torch.tensor(math.inf, dtype=torch.float64)),
        torch.nn.Parameter(torch.tensor(1.0, dtype=torch.complex128)),
        torch.nn.Parameter(torch.ones((1,), dtype=torch.float64)),
    ),
)
def test_invalid_parameter_keeps_stable_identity(
    invalid_radius: torch.nn.Parameter,
) -> None:
    """
    零、非有限、复数或非标量 Parameter 稳定拒绝
    """

    _assert_rejected(invalid_radius)


def test_direct_consumption_rejects_float32_parameter_drift() -> None:
    """
    构造后 Parameter 精度漂移在消费缝复核
    """

    radius = torch.nn.Parameter(torch.tensor(2.0, dtype=torch.float64))
    sphere = _sphere(radius)
    radius.data = radius.data.to(dtype=torch.float32)

    with pytest.raises(OpticalValueError) as rejected:
        sphere._validate_physical_state()  # noqa: SLF001

    assert rejected.value.identity == "sphere_radius_of_curvature_invalid"


@pytest.mark.cuda
def test_cuda_float64_parameter_keeps_identity_device_and_gradient() -> None:
    """
    CUDA 曲率半径 Parameter 不被复制或搬回 CPU
    """

    authored = torch.nn.Parameter(
        torch.tensor(-2.0, device=torch.device("cuda", 0), dtype=torch.float64),
    )
    sphere = _sphere(authored)

    assert sphere.radius_of_curvature is authored
    assert sphere.radius_of_curvature.device == authored.device
    sphere.radius_of_curvature.square().backward()
    assert authored.grad is not None


from __future__ import annotations

import math

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics.surface import ConicEvenAsphere, Plane, Sphere

_SURFACE_NAMES = ("plane", "sphere", "conic")


def _surface_with_position(
    surface_name: str,
    position: object,
) -> torch.nn.Module:
    # 经三个公开 Surface 构造器之一作者 pose 原点
    if surface_name == "plane":
        return Plane(origin=position)  # type: ignore[arg-type]
    if surface_name == "sphere":
        return Sphere(
            vertex=position,  # type: ignore[arg-type]
            radius_of_curvature=1.0,
        )
    if surface_name == "conic":
        return ConicEvenAsphere(vertex=position)  # type: ignore[arg-type]
    unknown_surface = f"未知 Surface：{surface_name}"
    raise AssertionError(unknown_surface)


def _position_state(surface_name: str, surface: torch.nn.Module) -> torch.Tensor:
    # 读取公开 Surface 对应的命名原点状态
    return getattr(surface, "origin" if surface_name == "plane" else "vertex")


def _position_error_identity(surface_name: str) -> str:
    # 给出 Surface 原点的稳定领域错误身份
    return (
        "plane_origin_invalid"
        if surface_name == "plane"
        else f"{surface_name}_vertex_invalid"
    )


@pytest.mark.parametrize("surface_name", _SURFACE_NAMES)
def test_float32_tensor_is_rejected_by_every_surface(
    surface_name: str,
) -> None:
    """
    三个公开 Surface 都不得静默升精度
    """

    origin = torch.tensor((0.0, 0.0, 0.0), dtype=torch.float32)

    with pytest.raises(OpticalValueError) as rejected:
        _surface_with_position(surface_name, origin)

    assert rejected.value.identity == _position_error_identity(surface_name)


@pytest.mark.parametrize("surface_name", _SURFACE_NAMES)
def test_python_three_tuple_materializes_as_cpu_float64(
    surface_name: str,
) -> None:
    """
    三元组在每个 Surface 内都成为 CPU float64 状态
    """

    surface = _surface_with_position(surface_name, (1, 2.5, -3.0))
    origin = _position_state(surface_name, surface)

    assert origin.dtype is torch.float64
    assert origin.device.type == "cpu"


@pytest.mark.parametrize("surface_name", _SURFACE_NAMES)
def test_float64_tensor_keeps_identity(
    surface_name: str,
) -> None:
    """
    合格固定 Tensor 以原身份成为 Surface 缓冲
    """

    authored_origin = torch.tensor(
        (1.0, 2.0, 3.0),
        dtype=torch.float64,
        requires_grad=True,
    )
    surface = _surface_with_position(surface_name, authored_origin)

    assert _position_state(surface_name, surface) is authored_origin


@pytest.mark.parametrize("surface_name", _SURFACE_NAMES)
def test_float64_parameter_keeps_parameter_identity_and_gradient(
    surface_name: str,
) -> None:
    """
    合格可训练原点保持 Parameter 注册与梯度连接
    """

    authored_origin = torch.nn.Parameter(
        torch.tensor((1.0, 2.0, 3.0), dtype=torch.float64),
    )
    surface = _surface_with_position(surface_name, authored_origin)
    registered_origin = _position_state(surface_name, surface)

    assert registered_origin is authored_origin
    registered_origin.square().sum().backward()
    assert authored_origin.grad is not None
    assert torch.equal(
        authored_origin.grad,
        2.0 * authored_origin.detach(),
    )


@pytest.mark.parametrize("surface_name", _SURFACE_NAMES)
def test_meta_float64_tensor_checks_only_structure(
    surface_name: str,
) -> None:
    """
    meta 原点不触发不可执行的有限性读取
    """

    authored_origin = torch.empty((3,), device="meta", dtype=torch.float64)
    surface = _surface_with_position(surface_name, authored_origin)

    assert _position_state(surface_name, surface) is authored_origin


@pytest.mark.parametrize(
    "origin",
    (
        torch.tensor((0.0, math.inf, 0.0), dtype=torch.float64),
        torch.tensor((0.0, math.nan, 0.0), dtype=torch.float64),
        torch.tensor((0.0, 0.0, 0.0), dtype=torch.complex128),
        torch.tensor((False, False, False), dtype=torch.bool),
        torch.tensor((0, 0, 0), dtype=torch.int64),
        torch.zeros((1, 3), dtype=torch.float64),
        (0.0, math.nan, 0.0),
        (0.0, False, 0.0),
        [0.0, 0.0, 0.0],
    ),
)
def test_invalid_origin_keeps_surface_error_identity(
    origin: object,
) -> None:
    """
    其余结构和值错误仍由 Surface 身份解释
    """

    with pytest.raises(OpticalValueError) as rejected:
        _surface_with_position("plane", origin)

    assert rejected.value.identity == "plane_origin_invalid"


@pytest.mark.parametrize("surface_name", _SURFACE_NAMES)
def test_float32_parameter_is_rejected_by_every_surface(
    surface_name: str,
) -> None:
    """
    Parameter 也服从 exact-float64 准入而非仅检查浮点类别
    """

    origin = torch.nn.Parameter(
        torch.tensor((0.0, 0.0, 0.0), dtype=torch.float32),
    )

    with pytest.raises(OpticalValueError) as rejected:
        _surface_with_position(surface_name, origin)

    assert rejected.value.identity == _position_error_identity(surface_name)


@pytest.mark.cuda
@pytest.mark.parametrize("surface_name", _SURFACE_NAMES)
def test_cuda_float64_tensor_keeps_device_and_identity(
    surface_name: str,
) -> None:
    """
    Surface 不移动合格 CUDA authored 原点
    """

    authored_origin = torch.tensor(
        (1.0, 2.0, 3.0),
        device=torch.device("cuda", 0),
        dtype=torch.float64,
        requires_grad=True,
    )
    surface = _surface_with_position(surface_name, authored_origin)
    registered_origin = _position_state(surface_name, surface)

    assert registered_origin is authored_origin
    assert registered_origin.device == authored_origin.device
    registered_origin.sum().backward()
    assert authored_origin.grad is not None


from __future__ import annotations

import math
from typing import cast

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics import Polarization, Spectrum
from chromatix_next.optics.source import CollimatedRaySource


def _source_with_origin(origin: object) -> CollimatedRaySource:
    # 经公开构造器作者 launch-plane 原点
    return CollimatedRaySource(
        spectrum=Spectrum.monochromatic(wavelength=550.0e-9),
        polarization=Polarization.linear_x(),
        launch_origin=origin,  # type: ignore[arg-type]
        ray_power=1.0,
    )


def test_python_three_tuple_materializes_as_cpu_float64() -> None:
    """
    有限实数三元组物化为新的 CPU float64 缓冲
    """

    source = _source_with_origin((1, 2.5, -3.0))
    registered_origin = cast(torch.Tensor, source.launch_origin)

    assert registered_origin.dtype is torch.float64
    assert registered_origin.device.type == "cpu"
    assert torch.equal(
        registered_origin,
        torch.tensor((1.0, 2.5, -3.0), dtype=torch.float64),
    )


def test_float64_tensor_keeps_identity_and_gradient() -> None:
    """
    合格 Tensor 不克隆、不迁移且保留原计算图
    """

    origin = torch.tensor(
        (1.0, 2.0, 3.0),
        dtype=torch.float64,
        requires_grad=True,
    )
    source = _source_with_origin(origin)
    registered_origin = cast(torch.Tensor, source.launch_origin)

    assert registered_origin is origin
    registered_origin.square().sum().backward()
    assert origin.grad is not None
    assert torch.equal(origin.grad, 2.0 * origin.detach())


def test_meta_float64_tensor_checks_structure_without_reading_value() -> None:
    """
    meta Tensor 只以形状和精度通过构造
    """

    origin = torch.empty((3,), device="meta", dtype=torch.float64)
    source = _source_with_origin(origin)

    assert source.launch_origin is origin
    assert source.launch_origin.is_meta


@pytest.mark.parametrize(
    "origin",
    (
        torch.tensor((0.0, 0.0, 0.0), dtype=torch.float32),
        torch.tensor((0.0, math.inf, 0.0), dtype=torch.float64),
        torch.tensor((0.0, math.nan, 0.0), dtype=torch.float64),
        torch.tensor((0.0, 0.0, 0.0), dtype=torch.complex128),
        torch.tensor((False, False, False), dtype=torch.bool),
        torch.tensor((0, 0, 0), dtype=torch.int64),
        torch.zeros((1, 3), dtype=torch.float64),
        (0.0, math.inf, 0.0),
        (0.0, True, 0.0),
        [0.0, 0.0, 0.0],
    ),
)
def test_invalid_authored_origin_keeps_source_error_identity(
    origin: object,
) -> None:
    """
    非 fixed-double 三维有限实向量以源的稳定身份拒绝
    """

    with pytest.raises(OpticalValueError) as rejected:
        _source_with_origin(origin)

    assert (
        rejected.value.identity
        == "collimated_ray_source_launch_origin_invalid"
    )


@pytest.mark.cuda
def test_cuda_float64_tensor_keeps_device_and_identity() -> None:
    """
    CUDA authored Tensor 不被静默搬回 CPU
    """

    origin = torch.tensor(
        (1.0, 2.0, 3.0),
        device=torch.device("cuda", 0),
        dtype=torch.float64,
        requires_grad=True,
    )
    source = _source_with_origin(origin)
    registered_origin = cast(torch.Tensor, source.launch_origin)

    assert registered_origin is origin
    assert registered_origin.device == origin.device
    registered_origin.sum().backward()
    assert origin.grad is not None

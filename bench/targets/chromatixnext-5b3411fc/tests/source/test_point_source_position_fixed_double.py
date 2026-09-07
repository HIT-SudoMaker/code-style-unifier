
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next.errors import OpticalTypeError, OpticalValueError
from chromatix_next.optics import Polarization, SpatialGrid, Spectrum
from chromatix_next.optics.source import PointSource
from chromatix_next.workstation import Workstation


def _grid() -> SpatialGrid:
    # 构造足以执行点源的中心网格
    return SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(0.2e-6, 0.2e-6),
    )


def _source(position: object) -> PointSource:
    # 经公开构造器作者点源位置
    return PointSource(
        spectrum=Spectrum.monochromatic(wavelength=0.5e-6),
        polarization=Polarization.scalar(),
        position=position,  # type: ignore[arg-type]
        relative_amplitude=1.0,
    )


def _assert_value_rejected(position: object) -> None:
    # 断言位置错误保留 PointSource 的稳定领域身份
    with pytest.raises(OpticalValueError) as rejected:
        _source(position)
    assert rejected.value.identity == "point_source_position_invalid"


def test_float32_parameter_is_rejected() -> None:
    """
    单精度 Parameter 不得静默升精度
    """

    position = torch.nn.Parameter(
        torch.tensor((0.0, 0.0, 2.0e-6), dtype=torch.float32),
    )

    _assert_value_rejected(position)


@pytest.mark.parametrize("dtype", (torch.float32, torch.float64))
def test_plain_tensor_keeps_public_type_error_priority(
    dtype: torch.dtype,
) -> None:
    """
    普通 Tensor 不越过只接受 Python 三元组或 Parameter 的接口
    """

    position = torch.tensor((0.0, 0.0, 2.0e-6), dtype=dtype)

    with pytest.raises(OpticalTypeError) as rejected:
        _source(position)

    assert rejected.value.identity == "point_source_position_invalid"


def test_python_tuple_materializes_as_cpu_float64() -> None:
    """
    有限 Python 三元组物化为 CPU float64 位置
    """

    source = _source((0, 0.5e-6, 2.0e-6))

    assert source.position.dtype is torch.float64
    assert source.position.device.type == "cpu"


def test_float64_parameter_keeps_identity_device_and_gradient() -> None:
    """
    合格 Parameter 保留身份、设备与计算图
    """

    authored = torch.nn.Parameter(
        torch.tensor(
            (0.0, 0.0, 2.0e-6),
            dtype=torch.float64,
        ),
    )
    source = _source(authored)
    registered_position = source._position_value  # noqa: SLF001

    assert source.position is authored
    assert registered_position is authored
    torch.square(registered_position).sum().backward()
    assert authored.grad is not None


def test_meta_float64_position_checks_only_structure() -> None:
    """
    meta 位置只检查三维结构与固定精度
    """

    authored = torch.nn.Parameter(
        torch.empty((3,), device="meta", dtype=torch.float64),
    )
    source = _source(authored)

    assert source.position is authored


@pytest.mark.parametrize(
    "invalid_tensor",
    (
        torch.tensor((0.0, math.nan, 1.0), dtype=torch.float64),
        torch.tensor((0.0, 0.0, 1.0), dtype=torch.complex128),
        torch.tensor((0, 0, 1), dtype=torch.int64),
        torch.zeros((1, 3), dtype=torch.float64),
    ),
)
def test_other_plain_tensors_keep_public_type_error_priority(
    invalid_tensor: torch.Tensor,
) -> None:
    """
    其它普通 Tensor 也先由冻结的公开类型契约拒绝
    """

    with pytest.raises(OpticalTypeError) as rejected:
        _source(invalid_tensor)

    assert rejected.value.identity == "point_source_position_invalid"


@pytest.mark.parametrize(
    "invalid_position",
    (
        (0.0, False, 1.0),
        (0.0, math.nan, 1.0),
        [0.0, 0.0, 1.0],
    ),
)
def test_invalid_python_position_keeps_value_identity(
    invalid_position: object,
) -> None:
    """
    非有限或非元组 Python 输入保留 PointSource 值错误身份
    """

    _assert_value_rejected(invalid_position)


def test_module_dtype_drift_is_rejected_at_consumption() -> None:
    """
    整模块转为 float32 后位置在消费缝稳定拒绝
    """

    source = _source((0.0, 0.0, 2.0e-6))
    with pytest.warns(UserWarning, match="Casting complex values to real"):
        source.to(dtype=torch.float32)

    with pytest.raises(OpticalValueError) as rejected:
        source._validate_physical_state()  # noqa: SLF001

    assert rejected.value.identity == "point_source_position_invalid"


def test_direct_and_hosted_execution_preserve_same_position_result() -> None:
    """
    直接与托管执行消费同一合法位置契约
    """

    direct = _source((0.0, 0.0, 2.0e-6))
    hosted = _source((0.0, 0.0, 2.0e-6))
    workstation = Workstation.cpu()
    hosted = workstation.host(hosted)  # type: ignore[assignment]

    assert torch.equal(direct(_grid()).envelope, hosted(_grid()).envelope)
    workstation.release(hosted)


@pytest.mark.cuda
def test_cuda_float64_position_keeps_identity_device_and_gradient() -> None:
    """
    CUDA authored 位置不被复制或搬回 CPU
    """

    authored = torch.nn.Parameter(
        torch.tensor(
            (0.0, 0.0, 2.0e-6),
            device=torch.device("cuda", 0),
            dtype=torch.float64,
        ),
    )
    source = _source(authored)
    registered_position = source._position_value  # noqa: SLF001

    assert source.position is authored
    assert registered_position is authored
    assert registered_position.device == authored.device
    torch.sum(registered_position).backward()
    assert authored.grad is not None

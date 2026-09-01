
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics.surface import ConicEvenAsphere
from chromatix_next.optics.surface.conic import _validate_conic_state_installation


def _conic(even_coefficients: object) -> ConicEvenAsphere:
    # 经公开构造器作者非空或空偶次系数；有限孔径闭合非空系数的求交域
    return ConicEvenAsphere(
        curvature=0.0,
        conic_constant=0.0,
        even_coefficients=even_coefficients,  # type: ignore[arg-type]
        clear_aperture_radius=1.0,
    )


def _assert_rejected(even_coefficients: object) -> None:
    # 断言偶次系数保留 Conic 的稳定领域错误身份
    with pytest.raises(OpticalValueError) as rejected:
        _conic(even_coefficients)
    assert rejected.value.identity == "conic_even_coefficients_invalid"


@pytest.mark.parametrize(
    "even_coefficients",
    (
        torch.tensor((1.0, -2.0), dtype=torch.float32),
        torch.nn.Parameter(torch.tensor((1.0, -2.0), dtype=torch.float32)),
    ),
)
def test_float32_tensor_and_parameter_are_rejected(
    even_coefficients: torch.Tensor,
) -> None:
    """
    普通 Tensor 与 Parameter 都不得静默升精度
    """

    _assert_rejected(even_coefficients)


@pytest.mark.parametrize("sequence", ((1, -2.5), [1, -2.5]))
def test_python_sequence_materializes_as_cpu_float64(
    sequence: tuple[float, ...] | list[float],
) -> None:
    """
    有限 Python tuple/list 物化为 CPU float64 系数
    """

    conic = _conic(sequence)

    assert conic.even_coefficients.dtype is torch.float64
    assert conic.even_coefficients.device.type == "cpu"


@pytest.mark.parametrize("is_parameter", (False, True))
def test_float64_tensor_keeps_identity_device_and_gradient(
    is_parameter: bool,
) -> None:
    """
    合格 Tensor 保留身份、设备与计算图
    """

    values = torch.tensor(
        (1.0, -2.0),
        dtype=torch.float64,
        requires_grad=not is_parameter,
    )
    authored = torch.nn.Parameter(values) if is_parameter else values
    conic = _conic(authored)

    assert conic.even_coefficients is authored
    conic.even_coefficients.square().sum().backward()
    assert authored.grad is not None


def test_meta_float64_coefficients_check_only_structure() -> None:
    """
    meta 系数只检查一维结构与固定精度
    """

    authored = torch.empty((2,), device="meta", dtype=torch.float64)
    conic = _conic(authored)

    assert conic.even_coefficients is authored


@pytest.mark.parametrize(
    "invalid_coefficients",
    (
        torch.tensor((1.0, math.nan), dtype=torch.float64),
        torch.tensor((1.0, 2.0), dtype=torch.complex128),
        torch.tensor((1, 2), dtype=torch.int64),
        torch.zeros((1, 2), dtype=torch.float64),
        (1.0, False),
        [1.0, math.inf],
    ),
)
def test_invalid_coefficients_keep_stable_identity(
    invalid_coefficients: object,
) -> None:
    """
    非一维、非实双精度或非有限输入稳定拒绝
    """

    _assert_rejected(invalid_coefficients)


def test_direct_consumption_rejects_float32_drift() -> None:
    """
    构造后系数精度漂移在直接消费缝复核
    """

    conic = _conic((1.0,))
    conic.even_coefficients = torch.tensor((1.0,), dtype=torch.float32)

    with pytest.raises(OpticalValueError) as rejected:
        conic._validate_physical_state()  # noqa: SLF001

    assert rejected.value.identity == "conic_even_coefficients_invalid"


def test_state_installation_rejects_float32_coefficients() -> None:
    """
    状态安装规划与构造期共享 exact-float64 领域契约
    """

    conic = _conic((1.0,))
    local_state = dict(conic.state_dict())
    local_state["even_coefficients"] = torch.tensor(
        (1.0,),
        dtype=torch.float32,
    )

    with pytest.raises(OpticalValueError) as rejected:
        _validate_conic_state_installation(conic, local_state)

    assert rejected.value.identity == "conic_even_coefficients_invalid"


@pytest.mark.cuda
def test_cuda_float64_coefficients_keep_identity_device_and_gradient() -> None:
    """
    CUDA authored 系数不被复制或搬回 CPU
    """

    authored = torch.tensor(
        (1.0, -2.0),
        device=torch.device("cuda", 0),
        dtype=torch.float64,
        requires_grad=True,
    )
    conic = _conic(authored)

    assert conic.even_coefficients is authored
    assert conic.even_coefficients.device == authored.device
    conic.even_coefficients.sum().backward()
    assert authored.grad is not None

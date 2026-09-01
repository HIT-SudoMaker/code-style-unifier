from __future__ import annotations

import cmath
import inspect
import math

import pytest
import torch

from chromatix_next._numerics.optical_path_reference import (
    accumulate_optical_path_lengths,
    express_envelope_in_optical_path_reference,
    normalize_optical_path_lengths,
    sum_envelopes_in_optical_path_reference,
)
from chromatix_next.errors import OpticalValueError


def _independent_reference_expression(
    envelope: torch.Tensor,
    *,
    wavelengths: tuple[float, ...],
    source_reference_lengths: tuple[float, ...],
    destination_reference_lengths: tuple[float, ...],
) -> torch.Tensor:
    # 用 Python 复指数独立重建参考变换，不复用生产 phasor
    phasors = torch.tensor(
        [
            cmath.exp(
                complex(
                    0.0,
                    2.0
                    * math.pi
                    * math.remainder(
                        (source_length - destination_length) / wavelength,
                        1.0,
                    ),
                )
            )
            for wavelength, source_length, destination_length in zip(
                wavelengths,
                source_reference_lengths,
                destination_reference_lengths,
                strict=True,
            )
        ],
        dtype=torch.complex128,
        device=envelope.device,
    )
    phasor_shape = [1] * (envelope.dim() - 4) + [
        envelope.shape[-4],
        1,
        1,
        1,
    ]
    return envelope * phasors.reshape(phasor_shape)


def test_public_numerical_interfaces_use_reference_domain_names() -> None:
    """
    深数值所有者的两个公开私有接口以光程参考领域命名
    """

    express_parameters = tuple(
        inspect.signature(
            express_envelope_in_optical_path_reference
        ).parameters
    )
    sum_parameters = tuple(
        inspect.signature(sum_envelopes_in_optical_path_reference).parameters
    )

    assert express_parameters == (
        "envelope",
        "wavelengths",
        "source_reference_lengths",
        "destination_reference_lengths",
    )
    assert sum_parameters == (
        "destination_envelope",
        "added_envelope",
        "wavelengths",
        "destination_reference_lengths",
        "added_reference_lengths",
    )


def test_accumulation_casts_before_large_and_small_lengths_are_added(
) -> None:
    """
    公共长度与独立微小增量先进入 float64 再相加并保留梯度
    """

    adjustment = torch.tensor(
        100.0e-9,
        dtype=torch.float32,
        requires_grad=True,
    )
    accumulated = accumulate_optical_path_lengths(
        (
            torch.tensor(
                10.0,
                dtype=torch.float32,
            ),
        ),
        adjustment,
        device=torch.device("cpu"),
    )[0]

    assert accumulated.dtype is torch.float64
    assert accumulated > 10.0
    torch.testing.assert_close(
        accumulated - 10.0,
        adjustment.detach().to(dtype=torch.float64),
        rtol=0.0,
        atol=1.0e-15,
    )
    accumulated.backward()
    assert adjustment.grad is not None
    assert torch.equal(adjustment.grad, torch.ones_like(adjustment))


def test_accumulation_rejects_wrong_spectral_increment_count() -> None:
    """
    逐光谱增量数量失配时保留稳定的光学域失败身份
    """

    with pytest.raises(OpticalValueError) as caught:
        accumulate_optical_path_lengths(
            (0.0,),
            torch.zeros(2, dtype=torch.float64),
            device=torch.device("cpu"),
        )

    assert caught.value.identity == "optical_path_increment_spectrum_mismatch"


def test_normalization_preserves_python_and_tensor_ownership() -> None:
    """
    Python 长度保持 Python 实数，Tensor 保留对象、设备与计算图
    """

    trainable_length = torch.tensor(
        0.25,
        dtype=torch.float64,
        requires_grad=True,
    )
    normalized = normalize_optical_path_lengths((1, trainable_length))

    assert normalized[0] == 1.0
    assert isinstance(normalized[0], float)
    assert normalized[1] is trainable_length


@pytest.mark.parametrize(
    "cycles",
    (0.0, 0.25, -0.5, 2.0, 2_000_000.75),
)
def test_reference_expression_matches_independent_complex_oracle(
    cycles: float,
) -> None:
    """
    相同、不同、整数、半整数与大周期参考均匹配独立复指数
    """

    wavelength = 500.0e-9
    envelope = torch.tensor(
        [[[[1.25 - 0.75j]]]],
        dtype=torch.complex128,
    )
    source_reference_lengths = (cycles * wavelength,)
    destination_reference_lengths = (0.0,)

    expressed = express_envelope_in_optical_path_reference(
        envelope=envelope,
        wavelengths=(wavelength,),
        source_reference_lengths=source_reference_lengths,
        destination_reference_lengths=destination_reference_lengths,
    )
    expected = _independent_reference_expression(
        envelope,
        wavelengths=(wavelength,),
        source_reference_lengths=source_reference_lengths,
        destination_reference_lengths=destination_reference_lengths,
    )

    torch.testing.assert_close(expressed, expected, rtol=1.0e-12, atol=1.0e-12)


def test_sum_first_expresses_added_envelope_in_destination_reference() -> None:
    """
    求和只把 added 包络表达至 destination 参考，再执行复包络相加
    """

    wavelengths = (500.0e-9, 700.0e-9)
    destination_reference_lengths = (0.1e-6, -0.3e-6)
    added_reference_lengths = (0.35e-6, 0.4e-6)
    destination_envelope = torch.tensor(
        [[[[1.0 + 0.5j]]], [[[0.25 - 0.75j]]]],
        dtype=torch.complex128,
    )
    added_envelope = torch.tensor(
        [[[[0.4 - 0.2j]]], [[[-0.5 + 0.1j]]]],
        dtype=torch.complex128,
    )

    produced = sum_envelopes_in_optical_path_reference(
        destination_envelope=destination_envelope,
        added_envelope=added_envelope,
        wavelengths=wavelengths,
        destination_reference_lengths=destination_reference_lengths,
        added_reference_lengths=added_reference_lengths,
    )
    expected = destination_envelope + _independent_reference_expression(
        added_envelope,
        wavelengths=wavelengths,
        source_reference_lengths=added_reference_lengths,
        destination_reference_lengths=destination_reference_lengths,
    )

    torch.testing.assert_close(produced, expected, rtol=1.0e-12, atol=1.0e-12)


def test_equal_reference_sum_is_observably_input_exchange_invariant() -> None:
    """
    同一参考下交换两路输入仍得到同一复包络可观测结果
    """

    envelope_1 = torch.tensor([[[[1.0 + 0.5j]]]], dtype=torch.complex128)
    envelope_2 = torch.tensor([[[[-0.25 + 0.75j]]]], dtype=torch.complex128)
    reference_lengths = (0.75e-6,)
    arguments = {
        "wavelengths": (500.0e-9,),
        "destination_reference_lengths": reference_lengths,
        "added_reference_lengths": reference_lengths,
    }

    forward = sum_envelopes_in_optical_path_reference(
        destination_envelope=envelope_1,
        added_envelope=envelope_2,
        **arguments,
    )
    exchanged = sum_envelopes_in_optical_path_reference(
        destination_envelope=envelope_2,
        added_envelope=envelope_1,
        **arguments,
    )

    assert torch.equal(forward, exchanged)


def test_sum_has_analytical_gradients_for_both_envelopes_and_references(
) -> None:
    """
    两路复包络与两路可训练参考都保留非零且解析一致的梯度
    """

    wavelength = 2.0
    destination_envelope = torch.tensor(
        [[[[1.0 + 0.5j]]]],
        dtype=torch.complex128,
        requires_grad=True,
    )
    added_envelope = torch.tensor(
        [[[[0.25 - 0.4j]]]],
        dtype=torch.complex128,
        requires_grad=True,
    )
    destination_reference = torch.tensor(
        0.1,
        dtype=torch.float64,
        requires_grad=True,
    )
    added_reference = torch.tensor(
        0.35,
        dtype=torch.float64,
        requires_grad=True,
    )

    output = sum_envelopes_in_optical_path_reference(
        destination_envelope=destination_envelope,
        added_envelope=added_envelope,
        wavelengths=(wavelength,),
        destination_reference_lengths=(destination_reference,),
        added_reference_lengths=(added_reference,),
    )
    loss = output.abs().square().sum()
    loss.backward()

    phasor = torch.tensor(
        cmath.exp(
            complex(
                0.0,
                2.0 * math.pi * (0.35 - 0.1) / wavelength,
            )
        ),
        dtype=torch.complex128,
    )
    expected_output = destination_envelope.detach() + (
        added_envelope.detach() * phasor
    )
    expected_destination_envelope_gradient = 2.0 * expected_output
    expected_added_envelope_gradient = 2.0 * expected_output * phasor.conj()
    phase_derivative = 2.0 * math.pi / wavelength
    expressed_added = added_envelope.detach() * phasor
    expected_added_reference_gradient = 2.0 * torch.real(
        expected_output.conj() * (1.0j * phase_derivative * expressed_added)
    ).sum()

    assert destination_envelope.grad is not None
    assert added_envelope.grad is not None
    assert destination_reference.grad is not None
    assert added_reference.grad is not None
    torch.testing.assert_close(
        destination_envelope.grad,
        expected_destination_envelope_gradient,
    )
    torch.testing.assert_close(
        added_envelope.grad,
        expected_added_envelope_gradient,
    )
    torch.testing.assert_close(
        added_reference.grad,
        expected_added_reference_gradient,
    )
    torch.testing.assert_close(
        destination_reference.grad,
        -expected_added_reference_gradient,
    )
    assert torch.count_nonzero(destination_envelope.grad) > 0
    assert torch.count_nonzero(added_envelope.grad) > 0
    assert torch.count_nonzero(destination_reference.grad) > 0
    assert torch.count_nonzero(added_reference.grad) > 0


def test_reference_operations_preserve_cpu_inputs_dtype_device_and_values(
) -> None:
    """
    CPU 数值核输出保持 complex128 与设备，且不修改任一路输入
    """

    destination_envelope = torch.tensor(
        [[[[1.0 + 0.5j]]]],
        dtype=torch.complex128,
    )
    added_envelope = torch.tensor(
        [[[[0.25 - 0.4j]]]],
        dtype=torch.complex128,
    )
    destination_before = destination_envelope.clone()
    added_before = added_envelope.clone()

    produced = sum_envelopes_in_optical_path_reference(
        destination_envelope=destination_envelope,
        added_envelope=added_envelope,
        wavelengths=(500.0e-9,),
        destination_reference_lengths=(0.0,),
        added_reference_lengths=(0.125e-6,),
    )

    assert produced.dtype is torch.complex128
    assert produced.device.type == "cpu"
    assert torch.equal(destination_envelope, destination_before)
    assert torch.equal(added_envelope, added_before)


def test_reference_operations_preserve_meta_shape_dtype_and_device() -> None:
    """
    meta 预演只传播复包络轮廓、固定精度与设备，不读取数值
    """

    destination_envelope = torch.empty(
        (2, 1, 3, 4),
        dtype=torch.complex128,
        device="meta",
    )
    added_envelope = torch.empty_like(destination_envelope)

    produced = sum_envelopes_in_optical_path_reference(
        destination_envelope=destination_envelope,
        added_envelope=added_envelope,
        wavelengths=(500.0e-9, 700.0e-9),
        destination_reference_lengths=(0.0, 0.1e-6),
        added_reference_lengths=(0.2e-6, -0.3e-6),
    )

    assert produced.shape == destination_envelope.shape
    assert produced.dtype is torch.complex128
    assert produced.device.type == "meta"


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_reference_operations_match_cpu_on_cuda() -> None:
    """
    CUDA 与 CPU 在固定双精度下给出相同参考表达和包络求和
    """

    destination_cpu = torch.tensor(
        [[[[1.0 + 0.5j]]], [[[0.25 - 0.75j]]]],
        dtype=torch.complex128,
    )
    added_cpu = torch.tensor(
        [[[[0.4 - 0.2j]]], [[[-0.5 + 0.1j]]]],
        dtype=torch.complex128,
    )
    arguments = {
        "wavelengths": (500.0e-9, 700.0e-9),
        "destination_reference_lengths": (0.1e-6, -0.3e-6),
        "added_reference_lengths": (0.35e-6, 0.4e-6),
    }
    cpu_output = sum_envelopes_in_optical_path_reference(
        destination_envelope=destination_cpu,
        added_envelope=added_cpu,
        **arguments,
    )
    cuda_output = sum_envelopes_in_optical_path_reference(
        destination_envelope=destination_cpu.to(device="cuda"),
        added_envelope=added_cpu.to(device="cuda"),
        **arguments,
    )

    assert cuda_output.device.type == "cuda"
    torch.testing.assert_close(
        cuda_output.cpu(),
        cpu_output,
        rtol=1.0e-12,
        atol=1.0e-12,
    )


@pytest.mark.cuda
@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA 双向设备局部性反例只在原生 CUDA 可用时执行",
)
@pytest.mark.parametrize(
    ("operation_name", "envelope_device", "reference_device"),
    (
        ("express", torch.device("cpu"), torch.device("cuda")),
        ("express", torch.device("cuda"), torch.device("cpu")),
        ("accumulate", torch.device("cpu"), torch.device("cuda")),
        ("accumulate", torch.device("cuda"), torch.device("cpu")),
    ),
)
def test_numerical_owner_rejects_cross_device_reference_without_preflight(
    operation_name: str,
    envelope_device: torch.device,
    reference_device: torch.device,
) -> None:
    """
    数值所有者稳定拒绝跨设备光程参考
    """

    reference_length = torch.tensor(
        0.125e-6,
        dtype=torch.float64,
        device=reference_device,
    )

    with pytest.raises(OpticalValueError) as information:
        if operation_name == "express":
            express_envelope_in_optical_path_reference(
                envelope=torch.ones(
                    (1, 1, 2, 3),
                    dtype=torch.complex128,
                    device=envelope_device,
                ),
                wavelengths=(532.0e-9,),
                source_reference_lengths=(reference_length,),
                destination_reference_lengths=(0.0,),
            )
        else:
            accumulate_optical_path_lengths(
                (reference_length,),
                0.25e-6,
                device=envelope_device,
            )

    assert information.value.identity == (
        "optical_path_reference_device_mismatch"
    )

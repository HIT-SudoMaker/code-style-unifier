from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest
import torch

import chromatix_next._numerics.wave_propagation.chirp_z_transform as chirp_z_module
from chromatix_next._numerics.wave_propagation.chirp_z_transform import (
    chirp_z_transform,
)


def test_chirp_z_matches_independent_direct_matrix() -> None:
    """
    验证末轴 Chirp-Z 与独立定义矩阵的未归一化复和一致
    """

    generator = torch.Generator().manual_seed(42)
    real = torch.randn((2, 3, 4, 7), generator=generator, dtype=torch.float64)
    imaginary = torch.randn(
        (2, 3, 4, 7),
        generator=generator,
        dtype=torch.float64,
    )
    values = torch.complex(real, imaginary)
    starting_cycles = torch.tensor(
        ((-0.31,), (0.17,), (0.43,)),
        dtype=torch.float64,
    ).reshape(1, 3, 1) / (2.0 * math.pi)
    cycles_step = torch.tensor(
        ((-0.27,), (-0.19,), (0.13,)),
        dtype=torch.float64,
    ).reshape(1, 3, 1) / (2.0 * math.pi)
    output_count = 5

    actual = chirp_z_transform(
        values,
        output_count=output_count,
        starting_cycles=starting_cycles,
        cycles_step=cycles_step,
    )

    input_index = torch.arange(values.shape[-1], dtype=torch.float64)
    output_index = torch.arange(output_count, dtype=torch.float64)
    matrix = torch.exp(
        1j
        * 2.0
        * math.pi
        * input_index[:, None]
        * (
            starting_cycles[..., None, None]
            + output_index * cycles_step[..., None, None]
        ),
    )
    expected = (values[..., None] * matrix).sum(dim=-2)
    assert torch.allclose(actual, expected, rtol=0.0, atol=3.0e-13)


@pytest.mark.parametrize(
    ("complex_dtype", "real_dtype", "tolerance"),
    (
        (torch.complex64, torch.float32, 2.0e-5),
        (torch.complex128, torch.float64, 2.0e-12),
    ),
)
def test_chirp_z_fft_special_case_matches_unnormalized_fft(
    complex_dtype: torch.dtype,
    real_dtype: torch.dtype,
    tolerance: float,
) -> None:
    """
    验证每索引负一周/N 步长特例与 PyTorch 未归一化前向 FFT 一致
    """

    generator = torch.Generator().manual_seed(42)
    values = torch.complex(
        torch.randn((2, 3, 7), generator=generator, dtype=real_dtype),
        torch.randn((2, 3, 7), generator=generator, dtype=real_dtype),
    ).to(dtype=complex_dtype)
    # 周期单位下 FFT 特例步长为 -1/N（弧度原 -2π/N 除以 2π）
    starting_cycles = torch.zeros((1, 1), dtype=real_dtype)
    cycles_step = torch.full(
        (1, 1),
        -1.0 / values.shape[-1],
        dtype=real_dtype,
    )

    actual = chirp_z_transform(
        values,
        output_count=values.shape[-1],
        starting_cycles=starting_cycles,
        cycles_step=cycles_step,
    )

    assert actual.dtype is complex_dtype
    assert torch.allclose(
        actual,
        torch.fft.fft(values, dim=-1),
        rtol=tolerance,
        atol=tolerance,
    )


def test_chirp_z_retains_input_gradient() -> None:
    """
    验证 Bluestein 实现保留复输入值的自动微分图
    """

    generator = torch.Generator().manual_seed(42)
    values = torch.complex(
        torch.randn((2, 5), generator=generator, dtype=torch.float64),
        torch.randn((2, 5), generator=generator, dtype=torch.float64),
    ).requires_grad_(True)
    starting_cycles = torch.tensor((-0.2, 0.3), dtype=torch.float64) / (
        2.0 * math.pi
    )
    cycles_step = torch.tensor((-0.17, 0.11), dtype=torch.float64) / (
        2.0 * math.pi
    )

    assert torch.autograd.gradcheck(
        lambda candidate: chirp_z_transform(
            candidate,
            output_count=4,
            starting_cycles=starting_cycles,
            cycles_step=cycles_step,
        ),
        (values,),
        eps=1.0e-6,
        atol=2.0e-5,
        rtol=2.0e-4,
    )


def test_chirp_z_meta_matches_real_shape_and_dtype() -> None:
    """
    验证 meta 与真实 Chirp-Z 路径具有相同输出结构
    """

    real_values = torch.empty((2, 3, 4, 7), dtype=torch.complex128)
    real_cycles = torch.empty((1, 3, 1), dtype=torch.float64)
    meta_values = torch.empty(
        real_values.shape,
        dtype=real_values.dtype,
        device="meta",
    )
    meta_cycles = torch.empty(
        real_cycles.shape,
        dtype=real_cycles.dtype,
        device="meta",
    )

    real_output = chirp_z_transform(
        real_values,
        output_count=5,
        starting_cycles=real_cycles,
        cycles_step=real_cycles,
    )
    meta_output = chirp_z_transform(
        meta_values,
        output_count=5,
        starting_cycles=meta_cycles,
        cycles_step=meta_cycles,
    )

    assert meta_output.shape == real_output.shape
    assert meta_output.dtype is real_output.dtype
    assert meta_output.device.type == "meta"


def test_chirp_z_production_contains_no_dense_transform_matrix() -> None:
    """
    验证生产实现不构造输入数乘输出数的稠密变换矩阵
    """

    source_path = Path(chirp_z_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden_calls = {
        "einsum",
        "matmul",
        "mm",
        "outer",
    }
    called_names = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    assert called_names.isdisjoint(forbidden_calls)


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="Windows CUDA evidence requires an available CUDA device",
)
def test_chirp_z_available_windows_cuda_matches_cpu() -> None:
    """
    可用 Windows CUDA 与 CPU 末轴 Chirp-Z 保持同精度一致
    """

    generator = torch.Generator().manual_seed(42)
    values = torch.complex(
        torch.randn((2, 3, 9), generator=generator),
        torch.randn((2, 3, 9), generator=generator),
    )
    starting_cycles = (
        torch.tensor((-0.21, 0.13, 0.37)).reshape(1, 3) / (2.0 * math.pi)
    )
    cycles_step = (
        torch.tensor((-0.17, 0.09, -0.11)).reshape(1, 3) / (2.0 * math.pi)
    )

    cpu = chirp_z_transform(
        values,
        output_count=7,
        starting_cycles=starting_cycles,
        cycles_step=cycles_step,
    )
    cuda = chirp_z_transform(
        values.cuda(),
        output_count=7,
        starting_cycles=starting_cycles.cuda(),
        cycles_step=cycles_step.cuda(),
    )

    assert torch.allclose(
        cuda.cpu(),
        cpu,
        rtol=2.0e-5,
        atol=2.0e-5,
    )


from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.wave_propagation.spatial_frequency import (
    apply_frequency_transfer,
    to_frequency,
    to_space,
)


def _complex_tolerance(dtype: torch.dtype) -> tuple[float, float]:
    # 给出与复数精度配对的绝对和相对容差
    if dtype == torch.complex64:
        return 2.0e-5, 2.0e-5
    return 2.0e-12, 2.0e-12


def _fourier_mode(
    *,
    height: int,
    width: int,
    mode_y: int,
    mode_x: int,
    dtype: torch.dtype,
    device: torch.device | str = "cpu",
) -> torch.Tensor:
    # 构造恰好落在未移位 FFT 正频率索引上的二维模式
    real_dtype = torch.float32 if dtype == torch.complex64 else torch.float64
    sample_y = torch.arange(height, dtype=real_dtype, device=device)
    sample_x = torch.arange(width, dtype=real_dtype, device=device)
    phase_y = 2.0 * math.pi * float(mode_y) * sample_y / float(height)
    phase_x = 2.0 * math.pi * float(mode_x) * sample_x / float(width)
    phase = phase_y[:, None] + phase_x[None, :]
    return torch.complex(
        torch.cos(phase),
        torch.sin(phase),
    ).to(dtype=dtype)


def _frequency_grid(
    *,
    height: int,
    width: int,
    spacing: float,
    dtype: torch.dtype,
) -> tuple[torch.Tensor, torch.Tensor]:
    # 按现有未移位约定构造每米周期数网格
    real_dtype = torch.float32 if dtype == torch.complex64 else torch.float64
    frequency_y = torch.fft.fftfreq(
        height,
        d=spacing,
        dtype=real_dtype,
    )
    frequency_x = torch.fft.fftfreq(
        width,
        d=spacing,
        dtype=real_dtype,
    )
    frequency_grid_y, frequency_grid_x = torch.meshgrid(
        frequency_y,
        frequency_x,
        indexing="ij",
    )
    return frequency_grid_y, frequency_grid_x


@pytest.mark.parametrize("dtype", (torch.complex128,))
def test_frequency_and_space_are_inverse(
    dtype: torch.dtype,
) -> None:
    """
    空域与频域变换在最后两个轴上互逆
    """
    envelope = _fourier_mode(
        height=7,
        width=9,
        mode_y=2,
        mode_x=3,
        dtype=dtype,
    ).reshape(1, 1, 7, 9)
    absolute_tolerance, relative_tolerance = _complex_tolerance(dtype)

    restored = to_space(to_frequency(envelope))

    assert torch.allclose(
        restored,
        envelope,
        atol=absolute_tolerance,
        rtol=relative_tolerance,
    )


@pytest.mark.parametrize("dtype", (torch.complex128,))
def test_centered_orthogonal_frequency_and_space_are_inverse(
    dtype: torch.dtype,
) -> None:
    """
    居中正交空频变换保持双精度对偶
    """

    envelope = _fourier_mode(
        height=7,
        width=9,
        mode_y=2,
        mode_x=3,
        dtype=dtype,
    ).reshape(1, 1, 7, 9)
    absolute_tolerance, relative_tolerance = _complex_tolerance(dtype)

    frequency = to_frequency(
        envelope,
        is_centered=True,
        normalization="ortho",
    )
    restored = to_space(
        frequency,
        is_centered=True,
        normalization="ortho",
    )

    assert torch.allclose(
        restored,
        envelope,
        atol=absolute_tolerance,
        rtol=relative_tolerance,
    )


@pytest.mark.parametrize("dtype", (torch.complex128,))
def test_backward_fft_obeys_parseval_energy_scaling(
    dtype: torch.dtype,
) -> None:
    """
    backward 归一化下频域能量等于空间能量乘以空间样本数
    """

    generator = torch.Generator(device="cpu").manual_seed(42)
    real_dtype = torch.float32 if dtype == torch.complex64 else torch.float64
    real = torch.randn(
        (2, 3, 7, 9),
        generator=generator,
        dtype=real_dtype,
    )
    imaginary = torch.randn(
        (2, 3, 7, 9),
        generator=generator,
        dtype=real_dtype,
    )
    spatial_values = torch.complex(real, imaginary).to(dtype=dtype)
    frequency_values = to_frequency(spatial_values)
    spatial_energy = spatial_values.abs().square().sum(dim=(-2, -1))
    frequency_energy = frequency_values.abs().square().sum(dim=(-2, -1))
    sample_count = spatial_values.shape[-2] * spatial_values.shape[-1]
    absolute_tolerance, relative_tolerance = _complex_tolerance(dtype)

    assert torch.allclose(
        frequency_energy,
        spatial_energy * sample_count,
        atol=absolute_tolerance * sample_count,
        rtol=relative_tolerance,
    )


@pytest.mark.parametrize("dtype", (torch.complex128,))
def test_identity_transfer_preserves_the_envelope(
    dtype: torch.dtype,
) -> None:
    """
    恒等传递函数保持包络、形状与精度
    """
    envelope = _fourier_mode(
        height=8,
        width=10,
        mode_y=1,
        mode_x=2,
        dtype=dtype,
    ).reshape(1, 1, 8, 10)
    frequency_transfer = torch.ones((1, 8, 10), dtype=dtype)
    absolute_tolerance, relative_tolerance = _complex_tolerance(dtype)

    result = apply_frequency_transfer(
        envelope,
        frequency_transfer,
    )

    assert result.shape == envelope.shape
    assert result.dtype == dtype
    assert torch.allclose(
        result,
        envelope,
        atol=absolute_tolerance,
        rtol=relative_tolerance,
    )


@pytest.mark.parametrize("dtype", (torch.complex128,))
def test_scalar_angular_spectrum_shaped_transfer_scales_its_fourier_mode(
    dtype: torch.dtype,
) -> None:
    """
    角谱形传递函数按未移位频率索引缩放单一模式
    """
    height, width = 8, 10
    mode_y, mode_x = 1, 2
    spacing = 1.5e-6
    wavelength = 532.0e-9
    axial_distance = 4.0e-6
    envelope = _fourier_mode(
        height=height,
        width=width,
        mode_y=mode_y,
        mode_x=mode_x,
        dtype=dtype,
    ).reshape(1, 1, height, width)
    frequency_y, frequency_x = _frequency_grid(
        height=height,
        width=width,
        spacing=spacing,
        dtype=dtype,
    )
    wave_number = 2.0 * math.pi / wavelength
    longitudinal_wave_number = torch.sqrt(
        wave_number**2
        - (2.0 * math.pi * frequency_y) ** 2
        - (2.0 * math.pi * frequency_x) ** 2,
    )
    residual_phase = (
        longitudinal_wave_number - wave_number
    ) * axial_distance
    frequency_transfer = torch.complex(
        torch.zeros_like(residual_phase),
        residual_phase,
    ).exp().to(dtype=dtype).reshape(1, height, width)
    expected = envelope * frequency_transfer[0, mode_y, mode_x]
    absolute_tolerance, relative_tolerance = _complex_tolerance(dtype)

    result = apply_frequency_transfer(
        envelope,
        frequency_transfer,
    )

    assert torch.allclose(
        result,
        expected,
        atol=absolute_tolerance,
        rtol=relative_tolerance,
    )


@pytest.mark.parametrize("dtype", (torch.complex128,))
def test_fresnel_shaped_transfer_scales_its_fourier_mode(
    dtype: torch.dtype,
) -> None:
    """
    Fresnel 形传递函数按同一频率约定缩放单一模式
    """
    height, width = 8, 10
    mode_y, mode_x = 2, 1
    spacing = 2.0e-6
    wavelength = 633.0e-9
    axial_distance = 8.0e-6
    envelope = _fourier_mode(
        height=height,
        width=width,
        mode_y=mode_y,
        mode_x=mode_x,
        dtype=dtype,
    ).reshape(1, 1, height, width)
    frequency_y, frequency_x = _frequency_grid(
        height=height,
        width=width,
        spacing=spacing,
        dtype=dtype,
    )
    phase = (
        -math.pi
        * wavelength
        * axial_distance
        * (frequency_y**2 + frequency_x**2)
    )
    frequency_transfer = torch.complex(
        torch.zeros_like(phase),
        phase,
    ).exp().to(dtype=dtype).reshape(1, height, width)
    expected = envelope * frequency_transfer[0, mode_y, mode_x]
    absolute_tolerance, relative_tolerance = _complex_tolerance(dtype)

    result = apply_frequency_transfer(
        envelope,
        frequency_transfer,
    )

    assert torch.allclose(
        result,
        expected,
        atol=absolute_tolerance,
        rtol=relative_tolerance,
    )


def test_transfer_preserves_gradient_through_the_multiplier() -> None:
    """
    传递函数中的可训练相位保持梯度
    """
    envelope = _fourier_mode(
        height=6,
        width=8,
        mode_y=1,
        mode_x=2,
        dtype=torch.complex128,
    ).reshape(1, 1, 6, 8)
    phase = torch.tensor(0.37, dtype=torch.float64, requires_grad=True)
    selected_value = torch.complex(
        torch.cos(phase),
        torch.sin(phase),
    )
    frequency_transfer = torch.ones((1, 6, 8), dtype=torch.complex128)
    frequency_transfer = frequency_transfer.index_put(
        (
            torch.tensor([0]),
            torch.tensor([1]),
            torch.tensor([2]),
        ),
        selected_value.reshape(1),
    )

    result = apply_frequency_transfer(
        envelope,
        frequency_transfer,
    )
    objective = result[0, 0, 0, 0].real
    objective.backward()

    assert phase.grad is not None
    assert phase.grad.item() == pytest.approx(
        -math.sin(phase.detach().item()),
        rel=1.0e-12,
        abs=1.0e-12,
    )


@pytest.mark.parametrize("dtype", (torch.complex128,))
def test_transfer_infers_shape_and_dtype_on_meta(
    dtype: torch.dtype,
) -> None:
    """
    meta 执行保持真实执行的形状与 dtype 契约
    """
    envelope = torch.empty(
        (2, 3, 1, 7, 9),
        dtype=dtype,
        device="meta",
    )
    frequency_transfer = torch.empty(
        (3, 7, 9),
        dtype=dtype,
        device="meta",
    )

    frequency = to_frequency(envelope)
    restored = to_space(frequency)
    result = apply_frequency_transfer(
        envelope,
        frequency_transfer,
    )

    assert frequency.device.type == "meta"
    assert restored.device.type == "meta"
    assert result.device.type == "meta"
    assert frequency.shape == envelope.shape
    assert restored.shape == envelope.shape
    assert result.shape == envelope.shape
    assert frequency.dtype == dtype
    assert restored.dtype == dtype
    assert result.dtype == dtype


def test_transfer_accepts_paired_real_precision() -> None:
    """
    配对实数传递量保持输入包络的复数精度（固定双精度证据）

    ``apply_frequency_transfer`` 接受任意复数精度（内部精度无关工具）。
    保留固定双精度分支作为方程专属证据；早先的 c64/f32 配对兼容性证据已删除。
    """
    complex_dtype = torch.complex128
    real_dtype = torch.float64
    envelope = torch.ones(
        (1, 1, 8, 8),
        dtype=complex_dtype,
    )
    frequency_transfer = torch.full(
        (1, 8, 8),
        0.5,
        dtype=real_dtype,
    )

    result = apply_frequency_transfer(
        envelope,
        frequency_transfer,
    )

    assert result.dtype == complex_dtype
    assert torch.allclose(
        result,
        envelope * 0.5,
    )

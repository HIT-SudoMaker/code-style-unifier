from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.thin_transmission import (
    ideal_thin_lens_phase_factor,
    optical_path_phase_factor,
)


def _scalar_pair(
    value_y: float,
    value_x: float,
    *,
    dtype: torch.dtype,
    device: torch.device | str = "cpu",
) -> tuple[torch.Tensor, torch.Tensor]:
    return (
        torch.tensor(value_y, dtype=dtype, device=device),
        torch.tensor(value_x, dtype=dtype, device=device),
    )


@pytest.mark.parametrize(
    ("real_dtype", "complex_dtype", "tolerance"),
    [
        (torch.float32, torch.complex64, 2e-6),
        (torch.float64, torch.complex128, 1e-12),
    ],
)
def test_optical_path_phase_matches_independent_multispectral_reference(
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    tolerance: float,
) -> None:
    """
    已定义光程变化按每个波长产生正号空间相位
    """

    wavelengths = torch.tensor((2.0e-6, 4.0e-6), dtype=real_dtype)
    variation = torch.tensor(
        [
            [0.0, 0.5e-6],
            [1.0e-6, 1.5e-6],
        ],
        dtype=real_dtype,
    )
    phase_factor = optical_path_phase_factor(
        wavelengths=wavelengths,
        optical_path_variation=variation,
    )
    phase = (
        2.0
        * math.pi
        * variation.unsqueeze(0)
        / wavelengths.reshape(-1, 1, 1)
    )
    expected = torch.complex(
        torch.cos(phase),
        torch.sin(phase),
    )

    assert phase_factor.dtype is complex_dtype
    assert torch.allclose(
        phase_factor,
        expected,
        atol=tolerance,
        rtol=tolerance,
    )


@pytest.mark.parametrize(
    ("real_dtype", "complex_dtype", "tolerance"),
    [
        (torch.float32, torch.complex64, 2e-6),
        (torch.float64, torch.complex128, 1e-12),
    ],
)
def test_ideal_thin_lens_uses_goodman_converging_sign(
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    tolerance: float,
) -> None:
    """
    正焦距前向会聚薄透镜使用 Goodman 约定的负二次相位
    """

    wavelength = 2.0e-6
    focal_length = torch.tensor(8.0e-6, dtype=real_dtype)
    phase_factor = ideal_thin_lens_phase_factor(
        sample_counts=(2, 3),
        signed_spacing=_scalar_pair(
            0.4e-6,
            -0.3e-6,
            dtype=real_dtype,
        ),
        first_sample_position=_scalar_pair(
            -0.2e-6,
            0.3e-6,
            dtype=real_dtype,
        ),
        wavelengths=torch.tensor((wavelength,), dtype=real_dtype),
        refractive_indices=torch.tensor((1.4,), dtype=real_dtype),
        focal_length=focal_length,
        lens_center=(
            torch.tensor(0.1e-6, dtype=real_dtype),
            torch.tensor(-0.2e-6, dtype=real_dtype),
        ),
    )

    position_y = (
        torch.arange(2, dtype=real_dtype) * 0.4e-6 - 0.2e-6
    )
    position_x = (
        torch.arange(3, dtype=real_dtype) * -0.3e-6 + 0.3e-6
    )
    radius_squared = (
        position_y[:, None] - 0.1e-6
    ).square() + (
        position_x[None, :] + 0.2e-6
    ).square()
    phase = (
        -2.0
        * math.pi
        * 1.4
        * radius_squared
        / (wavelength * 2.0 * focal_length)
    )
    expected = torch.complex(
        torch.cos(phase),
        torch.sin(phase),
    ).unsqueeze(0)

    assert phase_factor.dtype is complex_dtype
    assert torch.allclose(
        phase_factor,
        expected,
        atol=tolerance,
        rtol=tolerance,
    )
    assert torch.all(phase <= 0.0)


def test_thin_transmission_kernels_preserve_autograd() -> None:
    """
    空间光程与焦距的可训练值均保持完整双精度计算图
    """

    wavelengths = torch.tensor((2.0e-6,), dtype=torch.float64)
    variation = torch.tensor(
        [[0.15e-6, 0.3e-6]],
        dtype=torch.float64,
        requires_grad=True,
    )
    focal_length = torch.tensor(
        12.0e-6,
        dtype=torch.float64,
        requires_grad=True,
    )

    assert torch.autograd.gradcheck(
        lambda value: torch.view_as_real(
            optical_path_phase_factor(
                wavelengths=wavelengths,
                optical_path_variation=value,
            ),
        ),
        (variation,),
        eps=1e-9,
        atol=1e-5,
        rtol=1e-3,
    )
    assert torch.autograd.gradcheck(
        lambda value: torch.view_as_real(
            ideal_thin_lens_phase_factor(
                sample_counts=(1, 2),
                signed_spacing=_scalar_pair(
                    1.0e-6,
                    0.5e-6,
                    dtype=torch.float64,
                ),
                first_sample_position=_scalar_pair(
                    0.0,
                    -0.25e-6,
                    dtype=torch.float64,
                ),
                wavelengths=wavelengths,
                refractive_indices=torch.tensor((1.2,), dtype=torch.float64),
                focal_length=value,
                lens_center=(
                    torch.tensor(0.0, dtype=torch.float64),
                    torch.tensor(0.0, dtype=torch.float64),
                ),
            ),
        ),
        (focal_length,),
        eps=1e-9,
        atol=1e-5,
        rtol=1e-3,
    )


def test_ideal_thin_lens_passes_spacing_gradcheck() -> None:
    """
    薄透镜二次相位对空间采样间距保留有限差分梯度
    """

    spacing_y = torch.tensor(
        0.4e-6,
        dtype=torch.float64,
        requires_grad=True,
    )

    def _phase_as_real(spacing: torch.Tensor) -> torch.Tensor:
        phase = ideal_thin_lens_phase_factor(
            sample_counts=(2, 3),
            signed_spacing=(
                spacing,
                torch.tensor(-0.3e-6, dtype=torch.float64),
            ),
            first_sample_position=(
                torch.tensor(-0.2e-6, dtype=torch.float64),
                torch.tensor(0.3e-6, dtype=torch.float64),
            ),
            wavelengths=torch.tensor((2.0e-6,), dtype=torch.float64),
            refractive_indices=torch.tensor((1.4,), dtype=torch.float64),
            focal_length=torch.tensor(8.0e-6, dtype=torch.float64),
            lens_center=(
                torch.tensor(0.1e-6, dtype=torch.float64),
                torch.tensor(-0.2e-6, dtype=torch.float64),
            ),
        )
        return torch.view_as_real(phase)

    assert torch.autograd.gradcheck(
        _phase_as_real,
        (spacing_y,),
        eps=1e-10,
        atol=1e-5,
        rtol=1e-3,
    )


def test_ideal_thin_lens_runs_with_tensor_grid_on_meta() -> None:
    """
    meta 执行经同一张量网格路径推导薄透镜相位形状与精度
    """

    real_dtype = torch.float64
    phase = ideal_thin_lens_phase_factor(
        sample_counts=(2, 3),
        signed_spacing=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        first_sample_position=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        wavelengths=torch.empty((2,), dtype=real_dtype, device="meta"),
        refractive_indices=torch.empty(
            (2,),
            dtype=real_dtype,
            device="meta",
        ),
        focal_length=torch.empty((), dtype=real_dtype, device="meta"),
        lens_center=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
    )

    assert phase.shape == (2, 2, 3)
    assert phase.dtype == torch.complex128
    assert phase.device.type == "meta"


@pytest.mark.cuda
@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is unavailable",
)
def test_thin_transmission_kernels_match_cpu_on_cuda() -> None:
    """
    同一组薄透射参考核在 CPU 与可用 CUDA 设备上保持一致
    """

    wavelengths = torch.tensor((2.0e-6,), dtype=torch.float32)
    variation = torch.tensor([[0.15e-6, 0.3e-6]], dtype=torch.float32)
    refractive_indices = torch.tensor((1.2,), dtype=torch.float32)
    focal_length = torch.tensor(12.0e-6, dtype=torch.float32)
    lens_center = (
        torch.tensor(0.0, dtype=torch.float32),
        torch.tensor(0.0, dtype=torch.float32),
    )

    cpu_values = (
        optical_path_phase_factor(
            wavelengths=wavelengths,
            optical_path_variation=variation,
        ),
        ideal_thin_lens_phase_factor(
            sample_counts=(1, 2),
            signed_spacing=_scalar_pair(
                1.0e-6,
                0.5e-6,
                dtype=torch.float32,
            ),
            first_sample_position=_scalar_pair(
                0.0,
                -0.25e-6,
                dtype=torch.float32,
            ),
            wavelengths=wavelengths,
            refractive_indices=refractive_indices,
            focal_length=focal_length,
            lens_center=lens_center,
        ),
    )
    cuda_values = (
        optical_path_phase_factor(
            wavelengths=wavelengths.cuda(),
            optical_path_variation=variation.cuda(),
        ),
        ideal_thin_lens_phase_factor(
            sample_counts=(1, 2),
            signed_spacing=_scalar_pair(
                1.0e-6,
                0.5e-6,
                dtype=torch.float32,
                device="cuda",
            ),
            first_sample_position=_scalar_pair(
                0.0,
                -0.25e-6,
                dtype=torch.float32,
                device="cuda",
            ),
            wavelengths=wavelengths.cuda(),
            refractive_indices=refractive_indices.cuda(),
            focal_length=focal_length.cuda(),
            lens_center=(
                lens_center[0].cuda(),
                lens_center[1].cuda(),
            ),
        ),
    )

    for cpu_value, cuda_value in zip(cpu_values, cuda_values, strict=True):
        assert torch.allclose(
            cpu_value,
            cuda_value.cpu(),
            atol=2e-6,
            rtol=2e-6,
        )

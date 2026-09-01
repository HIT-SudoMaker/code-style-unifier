
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.wave_propagation.radiative_spectrum import (
    _computational_window_facts,
)
from chromatix_next._numerics.wave_propagation.scalar_angular_spectrum import (
    propagate_scalar_angular_spectrum,
    scalar_angular_spectrum_calculation,
    scalar_angular_spectrum_support_statistics,
)


def scalar_angular_spectrum_transfer(**arguments: object) -> torch.Tensor:
    """
    返回独立数值证据所需的中性传递张量
    """

    return scalar_angular_spectrum_calculation(
        **arguments,  # type: ignore[arg-type]
    ).transfer


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


def test_rationalized_residual_phase_avoids_complex64_cancellation() -> None:
    """
    单精度残差相位显著优于纵向波数直接相减
    """
    sample_count = 64
    sample_spacing = 1.0e-6
    wavelength = 633.0e-9
    axial_distance = 1.0e-3
    transfer = scalar_angular_spectrum_transfer(
        computational_counts=(sample_count, sample_count),
        signed_spacing=_scalar_pair(
            sample_spacing,
            sample_spacing,
            dtype=torch.float32,
        ),
        displacement=_scalar_pair(0.0, 0.0, dtype=torch.float32),
        axial_distance=torch.tensor(axial_distance, dtype=torch.float32),
        wavelengths=torch.tensor([wavelength], dtype=torch.float32),
        refractive_indices=torch.tensor([1.0], dtype=torch.float32),
        real_dtype=torch.float32,
        complex_dtype=torch.complex64,
        device=torch.device("cpu"),
    )

    frequency = 1.0 / (sample_count * sample_spacing)
    wave_number = 2.0 * math.pi / wavelength
    transverse_wave_number = 2.0 * math.pi * frequency
    reference_phase = (
        math.sqrt(wave_number**2 - transverse_wave_number**2)
        - wave_number
    ) * axial_distance
    single_wave_number = torch.tensor(wave_number, dtype=torch.float32)
    single_transverse_wave_number = torch.tensor(
        transverse_wave_number,
        dtype=torch.float32,
    )
    subtractive_float32_phase = (
        torch.sqrt(
            single_wave_number.square()
            - single_transverse_wave_number.square(),
        )
        - single_wave_number
    ) * axial_distance
    subtractive_float32_error = abs(float(subtractive_float32_phase) - reference_phase)
    production_phase = float(torch.angle(transfer[0, 1, 0]))
    production_error = abs(production_phase - reference_phase)

    assert subtractive_float32_error == pytest.approx(5.1678e-4, rel=2.0e-3)
    assert production_error < 1.0e-6
    assert production_error < subtractive_float32_error / 1000.0


def test_complex64_reliable_sampling_distance_is_3_2_millimetres() -> None:
    """
    单精度在最后合法采样距离匹配双精度，下一边界样本被拒绝
    """
    geometric_arguments = {
        "computational_counts": (64, 64),
    }
    complex64_arguments = {
        **geometric_arguments,
        "signed_spacing": _scalar_pair(
            1.0e-6,
            1.0e-6,
            dtype=torch.float32,
        ),
        "displacement": _scalar_pair(
            0.0,
            0.0,
            dtype=torch.float32,
        ),
        "wavelengths": torch.tensor([633.0e-9], dtype=torch.float32),
        "refractive_indices": torch.tensor([1.0], dtype=torch.float32),
        "real_dtype": torch.float32,
        "complex_dtype": torch.complex64,
        "device": torch.device("cpu"),
    }
    accepted = scalar_angular_spectrum_transfer(
        axial_distance=torch.tensor(3.2e-3, dtype=torch.float32),
        **complex64_arguments,  # type: ignore[arg-type]
    )
    reference = scalar_angular_spectrum_transfer(
        axial_distance=torch.tensor(3.2e-3, dtype=torch.float64),
        wavelengths=torch.tensor([633.0e-9], dtype=torch.float64),
        refractive_indices=torch.tensor([1.0], dtype=torch.float64),
        real_dtype=torch.float64,
        complex_dtype=torch.complex128,
        device=torch.device("cpu"),
        signed_spacing=_scalar_pair(
            1.0e-6,
            1.0e-6,
            dtype=torch.float64,
        ),
        displacement=_scalar_pair(
            0.0,
            0.0,
            dtype=torch.float64,
        ),
        **geometric_arguments,  # type: ignore[arg-type]
    )
    accepted_support = accepted.abs() > 0.0
    reference_support = reference.abs() > 0.0
    phase_error = torch.angle(
        accepted.to(dtype=torch.complex128)[accepted_support]
        * reference[reference_support].conj(),
    ).abs()

    assert torch.equal(accepted_support, reference_support)
    assert int(torch.count_nonzero(accepted)) == 9
    assert float(phase_error.max()) < 1.0e-6
    rejected = scalar_angular_spectrum_calculation(
        axial_distance=torch.tensor(3.3e-3, dtype=torch.float32),
        **complex64_arguments,  # type: ignore[arg-type]
    )

    assert bool(rejected.has_narrow_alias_band)


def test_evanescent_frequencies_are_zero_and_propagation_stays_finite() -> None:
    """
    合法混叠带内的倏逝频率严格归零且不产生非有限传播值
    """
    transfer = scalar_angular_spectrum_transfer(
        computational_counts=(8, 8),
        signed_spacing=_scalar_pair(
            0.25e-6,
            0.25e-6,
            dtype=torch.float64,
        ),
        displacement=_scalar_pair(0.0, 0.0, dtype=torch.float64),
        axial_distance=torch.tensor(0.0, dtype=torch.float64),
        wavelengths=torch.tensor([1.0e-6], dtype=torch.float64),
        refractive_indices=torch.tensor([1.0], dtype=torch.float64),
        real_dtype=torch.float64,
        complex_dtype=torch.complex128,
        device=torch.device("cpu"),
    )
    envelope = torch.zeros((1, 1, 8, 8), dtype=torch.complex128)
    envelope[0, 0, 0, 0] = 1.0

    propagated = propagate_scalar_angular_spectrum(
        envelope=envelope,
        transfer=transfer,
        computational_counts=(8, 8),
        window_counts=(8, 8),
        padding=(0, 0),
    )

    assert bool(torch.isfinite(transfer).all())
    assert bool(torch.isfinite(propagated).all())
    assert bool((transfer == 0.0).any())
    assert int(torch.count_nonzero(transfer)) == 13


def test_support_statistics_report_surviving_frequency_count_and_ratio() -> None:
    """
    角谱统计报告存活频点、支持占比与真实保留功率
    """
    transfer = scalar_angular_spectrum_transfer(
        computational_counts=(8, 8),
        signed_spacing=_scalar_pair(
            0.25e-6,
            0.25e-6,
            dtype=torch.float64,
        ),
        displacement=_scalar_pair(0.0, 0.0, dtype=torch.float64),
        axial_distance=torch.tensor(0.0, dtype=torch.float64),
        wavelengths=torch.tensor([1.0e-6], dtype=torch.float64),
        refractive_indices=torch.tensor([1.0], dtype=torch.float64),
        real_dtype=torch.float64,
        complex_dtype=torch.complex128,
        device=torch.device("cpu"),
    )

    impulse = torch.zeros((1, 1, 8, 8), dtype=torch.complex128)
    impulse[0, 0, 0, 0] = 1.0
    constant = torch.ones_like(impulse)
    envelope = torch.stack((impulse, constant), dim=0)
    statistics = scalar_angular_spectrum_support_statistics(
        envelope=envelope,
        transfer=transfer,
        computational_counts=(8, 8),
        padding=(0, 0),
    )

    assert torch.equal(
        statistics.surviving_frequency_count,
        torch.tensor([13]),
    )
    assert torch.allclose(
        statistics.support_ratio,
        torch.tensor([13.0 / 64.0], dtype=torch.float64),
    )
    assert torch.allclose(
        statistics.retained_power_ratio,
        torch.tensor(
            (
                (13.0 / 64.0,),
                (1.0,),
            ),
            dtype=torch.float64,
        ),
    )

    zero_statistics = scalar_angular_spectrum_support_statistics(
        envelope=torch.zeros_like(envelope),
        transfer=transfer,
        computational_counts=(8, 8),
        padding=(0, 0),
    )
    assert torch.equal(
        zero_statistics.retained_power_ratio,
        torch.zeros((2, 1), dtype=torch.float64),
    )


def test_propagation_scales_an_aligned_frequency_mode() -> None:
    """
    传播核按传递张量缩放对齐的单一频率模式（固定双精度证据）

    保留固定双精度分支作为方程专属证据；c64 兼容性 parametrize 已删除。
    """
    dtype = torch.complex128
    real_dtype = torch.float64
    height, width = 8, 10
    mode_y, mode_x = 1, 2
    sample_y = torch.arange(height, dtype=real_dtype)
    sample_x = torch.arange(width, dtype=real_dtype)
    phase = (
        2.0 * math.pi * float(mode_y) * sample_y[:, None] / float(height)
        + 2.0 * math.pi * float(mode_x) * sample_x[None, :] / float(width)
    )
    envelope = torch.complex(
        torch.cos(phase),
        torch.sin(phase),
    ).to(dtype=dtype).reshape(1, 1, height, width)
    selected_phase = torch.tensor(0.37, dtype=real_dtype)
    selected_transfer = torch.complex(
        torch.cos(selected_phase),
        torch.sin(selected_phase),
    )
    transfer = torch.ones((1, height, width), dtype=dtype)
    transfer[0, mode_y, mode_x] = selected_transfer

    propagated = propagate_scalar_angular_spectrum(
        envelope=envelope,
        transfer=transfer,
        computational_counts=(height, width),
        window_counts=(height, width),
        padding=(0, 0),
    )

    tolerance = 2.0e-12
    assert torch.allclose(
        propagated,
        envelope * selected_transfer,
        atol=tolerance,
        rtol=tolerance,
    )


def test_propagation_owns_isolated_padding_and_cropping() -> None:
    """
    孤立外部的恒等频域作用经居中零延拓后裁回原窗口
    """
    real = torch.arange(15, dtype=torch.float64).reshape(3, 5)
    envelope = torch.complex(real, real.flip((-2, -1))).reshape(1, 1, 3, 5)
    transfer = torch.ones((1, 7, 9), dtype=torch.complex128)

    propagated = propagate_scalar_angular_spectrum(
        envelope=envelope,
        transfer=transfer,
        computational_counts=(7, 9),
        window_counts=(3, 5),
        padding=(2, 2),
    )

    assert propagated.shape == envelope.shape
    assert torch.allclose(propagated, envelope, atol=1.0e-12, rtol=1.0e-12)


def test_transfer_retains_axial_distance_gradient() -> None:
    """
    双精度残差传递保留轴向距离的有限差分梯度证据
    """
    axial_distance = torch.tensor(
        1.0e-6,
        dtype=torch.float64,
        requires_grad=True,
    )

    def observe(distance: torch.Tensor) -> torch.Tensor:
        """
        返回当前距离下角谱传递张量的实部和
        """
        transfer = scalar_angular_spectrum_transfer(
            computational_counts=(8, 8),
            signed_spacing=_scalar_pair(
                1.0e-6,
                1.0e-6,
                dtype=torch.float64,
            ),
            displacement=_scalar_pair(
                0.0,
                0.0,
                dtype=torch.float64,
            ),
            axial_distance=distance,
            wavelengths=torch.tensor([1.0e-6], dtype=torch.float64),
            refractive_indices=torch.tensor([1.0], dtype=torch.float64),
            real_dtype=torch.float64,
            complex_dtype=torch.complex128,
            device=torch.device("cpu"),
        )
        return transfer.real.sum()

    assert torch.autograd.gradcheck(
        observe,
        (axial_distance,),
        eps=1.0e-9,
        raise_exception=True,
    )


def test_transfer_retains_sample_spacing_gradient() -> None:
    """
    频率轴以单位样本频率除以张量间距并保留有限差分梯度
    """

    spacing_y = torch.tensor(
        1.0e-6,
        dtype=torch.float64,
        requires_grad=True,
    )
    spacing_x = torch.tensor(1.1e-6, dtype=torch.float64)

    def observe(spacing: torch.Tensor) -> torch.Tensor:
        transfer = scalar_angular_spectrum_transfer(
            computational_counts=(8, 8),
            signed_spacing=(spacing, spacing_x),
            displacement=(
                torch.tensor(0.0, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
            ),
            axial_distance=torch.tensor(1.0e-6, dtype=torch.float64),
            wavelengths=torch.tensor([1.0e-6], dtype=torch.float64),
            refractive_indices=torch.tensor([1.0], dtype=torch.float64),
            real_dtype=torch.float64,
            complex_dtype=torch.complex128,
            device=torch.device("cpu"),
        )
        return transfer.real.sum()

    assert torch.autograd.gradcheck(
        observe,
        (spacing_y,),
        eps=1.0e-10,
        atol=1.0e-5,
        rtol=1.0e-3,
        raise_exception=True,
    )


def test_isolated_computational_support_is_fixed_by_sample_counts() -> None:
    """
    孤立外部始终使用三倍计算窗口与一倍输入窗口的居中 padding
    """

    facts = _computational_window_facts(
        input_counts=(8, 10),
        sample_spacing=(
            torch.tensor(1.0e-6, dtype=torch.float64),
            torch.tensor(2.0e-6, dtype=torch.float64),
        ),
        displacement=(
            torch.tensor(8.0e-6, dtype=torch.float64),
            torch.tensor(-20.0e-6, dtype=torch.float64),
        ),
        exterior="isolated",
    )

    assert facts.computational_counts == (24, 30)
    assert facts.padding == (8, 10)


def test_isolated_computational_support_rejects_excess_displacement() -> None:
    """
    可读位移超过固定零延拓支撑时以稳定标识拒绝
    """

    facts = _computational_window_facts(
        input_counts=(8, 10),
        sample_spacing=(
            torch.tensor(1.0e-6, dtype=torch.float64),
            torch.tensor(2.0e-6, dtype=torch.float64),
        ),
        displacement=(
            torch.tensor(8.1e-6, dtype=torch.float64),
            torch.tensor(0.0, dtype=torch.float64),
        ),
        exterior="isolated",
    )

    assert bool(facts.is_outside_support)


def test_periodic_support_does_not_limit_displacement() -> None:
    """
    周期外部直接在输入窗口传播，不应用孤立零延拓的位移边界
    """

    facts = _computational_window_facts(
        input_counts=(8, 10),
        sample_spacing=(
            torch.tensor(1.0e-6, dtype=torch.float64),
            torch.tensor(2.0e-6, dtype=torch.float64),
        ),
        displacement=(
            torch.tensor(1.0, dtype=torch.float64),
            torch.tensor(-1.0, dtype=torch.float64),
        ),
        exterior="periodic",
    )

    assert facts.computational_counts == (8, 10)
    assert facts.padding == (0, 0)


def test_isolated_computational_support_runs_on_meta() -> None:
    """
    meta 路径跳过不可读取的位移值但保持固定计算形状
    """

    spacing = (
        torch.empty((), dtype=torch.float32, device="meta"),
        torch.empty((), dtype=torch.float32, device="meta"),
    )
    displacement = (
        torch.empty((), dtype=torch.float32, device="meta"),
        torch.empty((), dtype=torch.float32, device="meta"),
    )

    facts = _computational_window_facts(
        input_counts=(8, 10),
        sample_spacing=spacing,
        displacement=displacement,
        exterior="isolated",
    )

    assert facts.computational_counts == (24, 30)
    assert facts.padding == (8, 10)


def test_transfer_statistics_and_propagation_run_on_meta() -> None:
    """
    meta 路径仅推导传递、统计与裁剪结果的形状和精度
    """
    transfer = scalar_angular_spectrum_transfer(
        computational_counts=(8, 10),
        signed_spacing=(
            torch.empty((), dtype=torch.float32, device="meta"),
            torch.empty((), dtype=torch.float32, device="meta"),
        ),
        displacement=(
            torch.empty((), dtype=torch.float32, device="meta"),
            torch.empty((), dtype=torch.float32, device="meta"),
        ),
        axial_distance=torch.empty((), dtype=torch.float32, device="meta"),
        wavelengths=torch.empty((2,), dtype=torch.float32, device="meta"),
        refractive_indices=torch.empty((2,), dtype=torch.float32, device="meta"),
        real_dtype=torch.float32,
        complex_dtype=torch.complex64,
        device=torch.device("meta"),
    )
    envelope = torch.empty(
        (4, 2, 1, 4, 6),
        dtype=torch.complex64,
        device="meta",
    )
    statistics = scalar_angular_spectrum_support_statistics(
        envelope=envelope,
        transfer=transfer,
        computational_counts=(8, 10),
        padding=(2, 2),
    )

    propagated = propagate_scalar_angular_spectrum(
        envelope=envelope,
        transfer=transfer,
        computational_counts=(8, 10),
        window_counts=(4, 6),
        padding=(2, 2),
    )

    assert transfer.shape == (2, 8, 10)
    assert transfer.dtype == torch.complex64
    assert transfer.device.type == "meta"
    assert statistics.surviving_frequency_count.shape == (2,)
    assert statistics.surviving_frequency_count.dtype == torch.int64
    assert statistics.surviving_frequency_count.device.type == "meta"
    assert statistics.support_ratio.shape == (2,)
    assert statistics.support_ratio.dtype == torch.float32
    assert statistics.support_ratio.device.type == "meta"
    assert statistics.retained_power_ratio.shape == (4, 2)
    assert statistics.retained_power_ratio.dtype == torch.float32
    assert statistics.retained_power_ratio.device.type == "meta"
    assert propagated.shape == envelope.shape
    assert propagated.dtype == torch.complex64
    assert propagated.device.type == "meta"

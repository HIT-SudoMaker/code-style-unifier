
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.gaussian_beam import gaussian_beam_unit_envelope
from chromatix_next._numerics.intensity import sampled_field_power_amplitude


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


def _independent_unit_envelope(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    waist_radius: torch.Tensor,
    waist_location: torch.Tensor,
    polarization_state: torch.Tensor,
) -> torch.Tensor:
    counts_y, counts_x = sample_counts
    spacing_y, spacing_x = signed_spacing
    first_y, first_x = first_sample_position
    position_y = torch.arange(counts_y, dtype=wavelengths.dtype) * spacing_y + first_y
    position_x = torch.arange(counts_x, dtype=wavelengths.dtype) * spacing_x + first_x
    wave_number = 2.0 * math.pi * refractive_indices / wavelengths
    waist_squared = waist_radius * waist_radius
    rayleigh_range = 0.5 * wave_number * waist_squared
    rayleigh_squared = rayleigh_range * rayleigh_range
    axial_squared = waist_location * waist_location
    beam_radius = waist_radius * torch.sqrt(1.0 + axial_squared / rayleigh_squared)
    curvature_factor = waist_location / (2.0 * (axial_squared + rayleigh_squared))
    gouy_phase = torch.atan(waist_location / rayleigh_range)
    radius_squared = (
        position_y.reshape(1, -1, 1) ** 2
        + position_x.reshape(1, 1, -1) ** 2
    )
    amplitude_factor = (waist_radius / beam_radius).reshape(-1, 1, 1)
    beam_radius_squared = (beam_radius * beam_radius).reshape(-1, 1, 1)
    transverse = torch.exp(-radius_squared / beam_radius_squared)
    # 正曲率相位 +k r^2 / (2 R(z))：与 forward propagation 复域一致
    curvature_arg = (wave_number * curvature_factor).reshape(-1, 1, 1) * radius_squared
    curvature_phase = torch.complex(
        torch.cos(curvature_arg),
        torch.sin(curvature_arg),
    )
    # 负 Gouy 相位 -arctan(z/zR)：与 forward propagation 复域一致
    gouy_arg = (-gouy_phase).reshape(-1, 1, 1)
    gouy_phasor = torch.complex(torch.cos(gouy_arg), torch.sin(gouy_arg))
    scalar = amplitude_factor * transverse * curvature_phase * gouy_phasor
    return scalar.unsqueeze(1) * polarization_state.reshape(1, -1, 1, 1)


@pytest.mark.parametrize(
    ("real_dtype", "complex_dtype", "tolerance"),
    [
        (torch.float32, torch.complex64, 2e-6),
        (torch.float64, torch.complex128, 1e-12),
    ],
)
def test_waist_plane_envelope_matches_independent_reference(
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    tolerance: float,
) -> None:
    """
    waist 平面（z=0）单位包络与独立解析参照一致
    """

    wavelengths = torch.tensor((0.5e-6,), dtype=real_dtype)
    indices = torch.tensor((1.0,), dtype=real_dtype)
    waist = torch.tensor(2.0e-6, dtype=real_dtype)
    waist_location = torch.tensor(0.0, dtype=real_dtype)
    polarization = torch.ones(1, dtype=complex_dtype)
    envelope = gaussian_beam_unit_envelope(
        sample_counts=(5, 7),
        signed_spacing=_scalar_pair(0.2e-6, 0.2e-6, dtype=real_dtype),
        first_sample_position=_scalar_pair(-0.4e-6, -0.6e-6, dtype=real_dtype),
        wavelengths=wavelengths,
        refractive_indices=indices,
        waist_radius=waist,
        waist_location=waist_location,
        polarization_state=polarization,
    )
    reference = _independent_unit_envelope(
        sample_counts=(5, 7),
        signed_spacing=_scalar_pair(0.2e-6, 0.2e-6, dtype=real_dtype),
        first_sample_position=_scalar_pair(-0.4e-6, -0.6e-6, dtype=real_dtype),
        wavelengths=wavelengths,
        refractive_indices=indices,
        waist_radius=waist,
        waist_location=waist_location,
        polarization_state=polarization,
    )
    assert envelope.dtype is complex_dtype
    assert torch.allclose(envelope, reference, atol=tolerance, rtol=tolerance)


def test_envelope_at_rayleigh_range_has_sqrt_two_beam_radius() -> None:
    """
    z=zR 处束腰半径 w(zR)=w0 sqrt(2)，中心振幅因子 w0/w(zR)=1/sqrt(2)
    """

    wavelength = 0.5e-6
    waist = 2.0e-6
    rayleigh_range = math.pi * waist * waist / wavelength
    envelope = gaussian_beam_unit_envelope(
        sample_counts=(1, 1),
        signed_spacing=_scalar_pair(1.0, 1.0, dtype=torch.float64),
        first_sample_position=_scalar_pair(0.0, 0.0, dtype=torch.float64),
        wavelengths=torch.tensor((wavelength,), dtype=torch.float64),
        refractive_indices=torch.tensor((1.0,), dtype=torch.float64),
        waist_radius=torch.tensor(waist, dtype=torch.float64),
        waist_location=torch.tensor(rayleigh_range, dtype=torch.float64),
        polarization_state=torch.ones(1, dtype=torch.complex128),
    )
    center_modulus = float(envelope[0, 0, 0, 0].abs())
    assert math.isclose(center_modulus, 1.0 / math.sqrt(2.0), rel_tol=1e-12)


def test_gouy_phase_at_rayleigh_range_is_negative_pi_over_four() -> None:
    """
    瑞利距离 z=zR 处 Gouy 相移取 -arctan(1) = -π/4

    仓库 ``exp(-i ω t)`` 约定下 forward beam 移除共享轴向载波后用负 Gouy 相位，
    与角谱正向传播在复域一致；z>0 给出 -arctan(z/zR)。
    """

    wavelength = 0.5e-6
    waist = 2.0e-6
    rayleigh_range = math.pi * waist * waist / wavelength
    envelope = gaussian_beam_unit_envelope(
        sample_counts=(1, 1),
        signed_spacing=_scalar_pair(1.0, 1.0, dtype=torch.float64),
        first_sample_position=_scalar_pair(0.0, 0.0, dtype=torch.float64),
        wavelengths=torch.tensor((wavelength,), dtype=torch.float64),
        refractive_indices=torch.tensor((1.0,), dtype=torch.float64),
        waist_radius=torch.tensor(waist, dtype=torch.float64),
        waist_location=torch.tensor(rayleigh_range, dtype=torch.float64),
        polarization_state=torch.tensor((1.0 + 0.0j,), dtype=torch.complex128),
    )
    # 中心 r=0：横向项=1、曲率相位=exp(i k 0/(2R))=1，故相位只来自 Gouy
    center_phase = float(envelope[0, 0, 0, 0].angle())
    assert math.isclose(center_phase, -math.pi / 4.0, abs_tol=1e-12)


def test_curvature_phase_vanishes_at_waist() -> None:
    """
    waist 平面（z=0）曲率相位为 1：包络在实轴上无二次相位
    """

    envelope = gaussian_beam_unit_envelope(
        sample_counts=(3, 3),
        signed_spacing=_scalar_pair(0.3e-6, 0.3e-6, dtype=torch.float64),
        first_sample_position=_scalar_pair(-0.3e-6, -0.3e-6, dtype=torch.float64),
        wavelengths=torch.tensor((0.5e-6,), dtype=torch.float64),
        refractive_indices=torch.tensor((1.0,), dtype=torch.float64),
        waist_radius=torch.tensor(1.0e-6, dtype=torch.float64),
        waist_location=torch.tensor(0.0, dtype=torch.float64),
        polarization_state=torch.ones(1, dtype=torch.complex128),
    )
    # waist 平面 Gouy=0、曲率=0，包络为正实数（振幅衰减 × exp(-r^2/w0^2)）
    assert torch.all(envelope.imag.abs() <= 1e-14)
    assert torch.all(envelope.real > 0)


def test_off_waist_envelope_matches_independent_reference() -> None:
    """
    z=zR 处单位包络与独立解析参照在复域一致（负 Gouy、正曲率）
    """

    wavelength = 0.5e-6
    waist = 1.5e-6
    rayleigh_range = math.pi * waist * waist / wavelength
    sample_counts = (6, 5)
    signed_spacing = _scalar_pair(0.2e-6, 0.25e-6, dtype=torch.float64)
    first_sample_position = _scalar_pair(-0.5e-6, -0.5e-6, dtype=torch.float64)
    wavelengths = torch.tensor((wavelength,), dtype=torch.float64)
    indices = torch.tensor((1.0,), dtype=torch.float64)
    waist_radius = torch.tensor(waist, dtype=torch.float64)
    waist_location = torch.tensor(rayleigh_range, dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)
    envelope = gaussian_beam_unit_envelope(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        wavelengths=wavelengths,
        refractive_indices=indices,
        waist_radius=waist_radius,
        waist_location=waist_location,
        polarization_state=polarization,
    )
    reference = _independent_unit_envelope(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        wavelengths=wavelengths,
        refractive_indices=indices,
        waist_radius=waist_radius,
        waist_location=waist_location,
        polarization_state=polarization,
    )
    # 复域逐像素一致（独立 cos/sin 路径对照 torch.polar 路径）
    assert torch.allclose(envelope, reference, atol=1e-12, rtol=1e-12)


def test_negative_waist_location_follows_conjugate_symmetry() -> None:
    """
    z<0 满足 env(-z) = conj(env(z))（exp(-i ω t) 约定的共轭对称）
    """

    sample_counts = (5, 5)
    signed_spacing = _scalar_pair(0.25e-6, 0.25e-6, dtype=torch.float64)
    first_sample_position = _scalar_pair(-0.5e-6, -0.5e-6, dtype=torch.float64)
    wavelengths = torch.tensor((0.5e-6,), dtype=torch.float64)
    indices = torch.tensor((1.0,), dtype=torch.float64)
    waist_radius = torch.tensor(1.5e-6, dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)
    positive = gaussian_beam_unit_envelope(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        wavelengths=wavelengths,
        refractive_indices=indices,
        waist_radius=waist_radius,
        waist_location=torch.tensor(3.0e-6, dtype=torch.float64),
        polarization_state=polarization,
    )
    negative = gaussian_beam_unit_envelope(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        wavelengths=wavelengths,
        refractive_indices=indices,
        waist_radius=waist_radius,
        waist_location=torch.tensor(-3.0e-6, dtype=torch.float64),
        polarization_state=polarization,
    )
    assert torch.allclose(negative, positive.conj(), atol=1e-14, rtol=1e-14)


def test_non_vacuum_medium_changes_rayleigh_range() -> None:
    """
    非真空介质中 zR = pi w0^2 n / lambda，相同 waist 下束腰展宽更慢
    """

    wavelength = 0.5e-6
    waist = 2.0e-6
    vacuum_zr = math.pi * waist * waist / wavelength
    glass_zr = math.pi * waist * waist * 1.5 / wavelength
    # 在 z=vacuum_zR 处：真空 w/w0=sqrt(2)，玻璃（zR 更大）更接近 1
    envelope_vacuum = gaussian_beam_unit_envelope(
        sample_counts=(1, 1),
        signed_spacing=_scalar_pair(1.0, 1.0, dtype=torch.float64),
        first_sample_position=_scalar_pair(0.0, 0.0, dtype=torch.float64),
        wavelengths=torch.tensor((wavelength,), dtype=torch.float64),
        refractive_indices=torch.tensor((1.0,), dtype=torch.float64),
        waist_radius=torch.tensor(waist, dtype=torch.float64),
        waist_location=torch.tensor(vacuum_zr, dtype=torch.float64),
        polarization_state=torch.ones(1, dtype=torch.complex128),
    )
    envelope_glass = gaussian_beam_unit_envelope(
        sample_counts=(1, 1),
        signed_spacing=_scalar_pair(1.0, 1.0, dtype=torch.float64),
        first_sample_position=_scalar_pair(0.0, 0.0, dtype=torch.float64),
        wavelengths=torch.tensor((wavelength,), dtype=torch.float64),
        refractive_indices=torch.tensor((1.5,), dtype=torch.float64),
        waist_radius=torch.tensor(waist, dtype=torch.float64),
        waist_location=torch.tensor(vacuum_zr, dtype=torch.float64),
        polarization_state=torch.ones(1, dtype=torch.complex128),
    )
    vacuum_mod = float(envelope_vacuum[0, 0, 0, 0].abs())
    glass_mod = float(envelope_glass[0, 0, 0, 0].abs())
    # 真空在自身 zR 处：1/sqrt(2)。玻璃 zR 更大，故此位置更接近 waist，振幅更高
    assert math.isclose(vacuum_mod, 1.0 / math.sqrt(2.0), rel_tol=1e-12)
    expected_glass = 1.0 / math.sqrt(1.0 + (vacuum_zr / glass_zr) ** 2)
    assert math.isclose(glass_mod, expected_glass, rel_tol=1e-12)


def test_multispectral_envelope_preserves_spectral_order() -> None:
    """
    多光谱单位包络逐分量沿光谱轴排列，偏振按规范顺序展开
    """

    polarization = torch.tensor(
        (math.sqrt(0.5) + 0.0j, 0.0 + math.sqrt(0.5) * 1.0j),
        dtype=torch.complex128,
    )
    wavelengths = torch.tensor((0.45e-6, 0.65e-6), dtype=torch.float64)
    indices = torch.tensor((1.0, 1.5), dtype=torch.float64)
    envelope = gaussian_beam_unit_envelope(
        sample_counts=(1, 1),
        signed_spacing=_scalar_pair(1.0, 1.0, dtype=torch.float64),
        first_sample_position=_scalar_pair(0.0, 0.0, dtype=torch.float64),
        wavelengths=wavelengths,
        refractive_indices=indices,
        waist_radius=torch.tensor(2.0e-6, dtype=torch.float64),
        waist_location=torch.tensor(0.0, dtype=torch.float64),
        polarization_state=polarization,
    )
    assert envelope.shape == (2, 2, 1, 1)
    # waist 平面两分量振幅因子均为 1，故两偏振分量严格等于 polarization_state
    assert torch.allclose(envelope[:, :, 0, 0], polarization.unsqueeze(0))


def test_envelope_passes_refractive_index_gradcheck() -> None:
    """
    折射率进入 Rayleigh range 与曲率相位，保留完整计算图
    """

    indices = torch.tensor((1.2, 1.4), dtype=torch.float64, requires_grad=True)
    wavelengths = torch.tensor((1.0, 1.5), dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)

    def _envelope_as_real(refractive_indices: torch.Tensor) -> torch.Tensor:
        envelope = gaussian_beam_unit_envelope(
            sample_counts=(3, 3),
            signed_spacing=_scalar_pair(0.25, 0.5, dtype=torch.float64),
            first_sample_position=_scalar_pair(-0.25, -0.25, dtype=torch.float64),
            wavelengths=wavelengths,
            refractive_indices=refractive_indices,
            waist_radius=torch.tensor(0.8, dtype=torch.float64),
            waist_location=torch.tensor(0.4, dtype=torch.float64),
            polarization_state=polarization,
        )
        return torch.view_as_real(envelope)

    assert torch.autograd.gradcheck(
        _envelope_as_real,
        (indices,),
        eps=1e-7,
        atol=1e-5,
        rtol=1e-3,
    )


def test_envelope_passes_waist_gradcheck() -> None:
    """
    waist 作为可训练参数进入束腰与振幅因子，保留有限差分梯度
    """

    waist = torch.tensor(0.9, dtype=torch.float64, requires_grad=True)

    def _envelope_as_real(waist_value: torch.Tensor) -> torch.Tensor:
        envelope = gaussian_beam_unit_envelope(
            sample_counts=(3, 3),
            signed_spacing=_scalar_pair(0.25, 0.5, dtype=torch.float64),
            first_sample_position=_scalar_pair(-0.25, -0.25, dtype=torch.float64),
            wavelengths=torch.tensor((1.0,), dtype=torch.float64),
            refractive_indices=torch.tensor((1.3,), dtype=torch.float64),
            waist_radius=waist_value,
            waist_location=torch.tensor(0.2, dtype=torch.float64),
            polarization_state=torch.ones(1, dtype=torch.complex128),
        )
        return torch.view_as_real(envelope)

    assert torch.autograd.gradcheck(
        _envelope_as_real,
        (waist,),
        eps=1e-7,
        atol=1e-5,
        rtol=1e-3,
    )


def test_envelope_passes_waist_location_gradcheck() -> None:
    """
    waist_location 进入 Gouy 相位、曲率与束腰半径，保留有限差分梯度
    """

    waist_location = torch.tensor(0.3, dtype=torch.float64, requires_grad=True)

    def _envelope_as_real(location: torch.Tensor) -> torch.Tensor:
        envelope = gaussian_beam_unit_envelope(
            sample_counts=(3, 3),
            signed_spacing=_scalar_pair(0.25, 0.5, dtype=torch.float64),
            first_sample_position=_scalar_pair(-0.25, -0.25, dtype=torch.float64),
            wavelengths=torch.tensor((1.0,), dtype=torch.float64),
            refractive_indices=torch.tensor((1.3,), dtype=torch.float64),
            waist_radius=torch.tensor(0.8, dtype=torch.float64),
            waist_location=location,
            polarization_state=torch.ones(1, dtype=torch.complex128),
        )
        return torch.view_as_real(envelope)

    assert torch.autograd.gradcheck(
        _envelope_as_real,
        (waist_location,),
        eps=1e-7,
        atol=1e-5,
        rtol=1e-3,
    )


def test_envelope_runs_with_tensor_grid_on_meta() -> None:
    """
    meta 执行以同一张量网格路径推导高斯包络形状与精度
    """

    real_dtype = torch.float32
    envelope = gaussian_beam_unit_envelope(
        sample_counts=(3, 5),
        signed_spacing=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        first_sample_position=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        wavelengths=torch.empty((2,), dtype=real_dtype, device="meta"),
        refractive_indices=torch.empty((2,), dtype=real_dtype, device="meta"),
        waist_radius=torch.empty((), dtype=real_dtype, device="meta"),
        waist_location=torch.empty((), dtype=real_dtype, device="meta"),
        polarization_state=torch.empty((1,), dtype=torch.complex64, device="meta"),
    )
    assert envelope.shape == (2, 1, 3, 5)
    assert envelope.dtype == torch.complex64
    assert envelope.device.type == "meta"


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is unavailable",
)
def test_envelope_matches_cpu_on_cuda() -> None:
    """
    同一私有数值核在 CPU 与可用 CUDA 设备上保持一致
    """

    wavelengths = torch.tensor((0.5, 0.8), dtype=torch.float32)
    indices = torch.tensor((1.0, 1.4), dtype=torch.float32)
    polarization = torch.tensor(
        (1.0 + 0.0j, 0.0 + 1.0j),
        dtype=torch.complex64,
    )
    waist = torch.tensor(0.9, dtype=torch.float32)
    waist_location = torch.tensor(0.2, dtype=torch.float32)
    cpu = gaussian_beam_unit_envelope(
        sample_counts=(4, 3),
        signed_spacing=_scalar_pair(0.2, -0.3, dtype=torch.float32),
        first_sample_position=_scalar_pair(-0.3, 0.3, dtype=torch.float32),
        wavelengths=wavelengths,
        refractive_indices=indices,
        waist_radius=waist,
        waist_location=waist_location,
        polarization_state=polarization,
    )
    cuda = gaussian_beam_unit_envelope(
        sample_counts=(4, 3),
        signed_spacing=_scalar_pair(
            0.2,
            -0.3,
            dtype=torch.float32,
            device="cuda",
        ),
        first_sample_position=_scalar_pair(
            -0.3,
            0.3,
            dtype=torch.float32,
            device="cuda",
        ),
        wavelengths=wavelengths.cuda(),
        refractive_indices=indices.cuda(),
        waist_radius=waist.cuda(),
        waist_location=waist_location.cuda(),
        polarization_state=polarization.cuda(),
    )
    assert torch.allclose(cpu, cuda.cpu(), atol=2e-6, rtol=2e-6)


def test_power_amplitude_matches_analytic_integral() -> None:
    """
    总功率归一化振幅使 |A|^2 cell_area sum_s w_s sum_xy |unit_s|^2 = total_power
    """

    wavelengths = torch.tensor((0.5e-6, 0.65e-6), dtype=torch.float64)
    indices = torch.tensor((1.0, 1.2), dtype=torch.float64)
    weights = torch.tensor((0.4, 0.6), dtype=torch.float64)
    unit_envelope = gaussian_beam_unit_envelope(
        sample_counts=(6, 6),
        signed_spacing=_scalar_pair(0.2e-6, 0.2e-6, dtype=torch.float64),
        first_sample_position=_scalar_pair(-0.4e-6, -0.4e-6, dtype=torch.float64),
        wavelengths=wavelengths,
        refractive_indices=indices,
        waist_radius=torch.tensor(1.5e-6, dtype=torch.float64),
        waist_location=torch.tensor(0.0, dtype=torch.float64),
        polarization_state=torch.ones(1, dtype=torch.complex128),
    )
    total_power = torch.tensor(2.5e-3, dtype=torch.float64)
    cell_area = torch.tensor(0.2e-6 * 0.2e-6, dtype=torch.float64)
    amplitude = sampled_field_power_amplitude(
        total_power=total_power,
        spectral_weights=weights,
        unit_envelope=unit_envelope,
        cell_area=cell_area,
    )
    modulus_squared = unit_envelope.real.square() + unit_envelope.imag.square()
    per_spectrum = modulus_squared.sum(dim=-3).sum(dim=(-2, -1))
    represented = float((weights * per_spectrum).sum() * cell_area)
    expected = math.sqrt(float(total_power) / represented)
    assert math.isclose(float(amplitude), expected, rel_tol=1e-12)


def test_power_amplitude_preserves_total_power_gradient() -> None:
    """
    保留总功率归一化梯度
    """

    total_power = torch.tensor(2.0, dtype=torch.float64, requires_grad=True)
    weights = torch.tensor((0.4, 0.6), dtype=torch.float64)
    unit_envelope = torch.ones(
        (2, 1, 2, 2),
        dtype=torch.complex128,
    )

    def _amplitude(power: torch.Tensor) -> torch.Tensor:
        return sampled_field_power_amplitude(
            total_power=power,
            spectral_weights=weights,
            unit_envelope=unit_envelope,
            cell_area=torch.tensor(0.25, dtype=torch.float64),
        )

    assert torch.autograd.gradcheck(
        _amplitude,
        (total_power,),
        eps=1e-7,
        atol=1e-5,
        rtol=1e-3,
    )

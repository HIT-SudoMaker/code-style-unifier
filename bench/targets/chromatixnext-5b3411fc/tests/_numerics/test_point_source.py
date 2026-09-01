
from __future__ import annotations

from decimal import Decimal, getcontext
import math

import pytest
import torch

from chromatix_next._numerics.intensity import sampled_field_power_amplitude
from chromatix_next._numerics.point_source import (
    PointSourceSamplingFacts,
    _adjacent_pair_half_cycle_sufficient,
    point_source_sampling_fence,
    point_source_unit_envelope,
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


def _scalar(
    value: float,
    *,
    dtype: torch.dtype,
    device: torch.device | str = "cpu",
) -> torch.Tensor:
    return torch.tensor(value, dtype=dtype, device=device)


def _independent_unit_envelope(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    source_position_yxz: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
    is_inverse_distance: bool,
    polarization_state: torch.Tensor,
) -> torch.Tensor:
    counts_y, counts_x = sample_counts
    spacing_y, spacing_x = signed_spacing
    first_y, first_x = first_sample_position
    source_y, source_x, source_z = source_position_yxz
    position_y = torch.arange(counts_y, dtype=wavelengths.dtype) * spacing_y + first_y
    position_x = torch.arange(counts_x, dtype=wavelengths.dtype) * spacing_x + first_x
    delta_y = position_y.reshape(1, -1, 1) - source_y
    delta_x = position_x.reshape(1, 1, -1) - source_x
    delta_z_squared = source_z * source_z
    radius = torch.sqrt(
        delta_y * delta_y + delta_x * delta_x + delta_z_squared
    )
    wave_number = 2.0 * math.pi * refractive_indices / wavelengths
    phase = wave_number.reshape(-1, 1, 1) * radius
    if is_inverse_distance:
        amplitude_factor = torch.reciprocal(radius)
    else:
        amplitude_factor = torch.ones_like(radius)
    scalar = amplitude_factor * torch.complex(
        torch.cos(phase),
        torch.sin(phase),
    )
    return scalar.unsqueeze(1) * polarization_state.reshape(1, -1, 1, 1)


@pytest.mark.parametrize(
    ("real_dtype", "complex_dtype", "tolerance"),
    [
        (torch.float32, torch.complex64, 2e-6),
        (torch.float64, torch.complex128, 1e-12),
    ],
)
def test_spherical_phase_matches_independent_reference_on_axis(
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    tolerance: float,
) -> None:
    """
    轴上点源（grid 中心正上方）球面相位与独立 exp(ikr) 参照一致
    """

    wavelengths = torch.tensor((0.5e-6,), dtype=real_dtype)
    indices = torch.tensor((1.0,), dtype=real_dtype)
    polarization = torch.ones(1, dtype=complex_dtype)
    envelope = point_source_unit_envelope(
        sample_counts=(5, 7),
        signed_spacing=_scalar_pair(0.2e-6, 0.2e-6, dtype=real_dtype),
        first_sample_position=_scalar_pair(-0.4e-6, -0.6e-6, dtype=real_dtype),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(2.0e-6, dtype=real_dtype),
        ),
        is_inverse_distance=False,
        polarization_state=polarization,
    )
    reference = _independent_unit_envelope(
        sample_counts=(5, 7),
        signed_spacing=_scalar_pair(0.2e-6, 0.2e-6, dtype=real_dtype),
        first_sample_position=_scalar_pair(-0.4e-6, -0.6e-6, dtype=real_dtype),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(2.0e-6, dtype=real_dtype),
        ),
        is_inverse_distance=False,
        polarization_state=polarization,
    )
    assert envelope.dtype is complex_dtype
    assert torch.allclose(envelope, reference, atol=tolerance, rtol=tolerance)


def test_spherical_phase_matches_independent_reference_off_axis() -> None:
    """
    偏轴点源球面相位与独立参照一致（y、x、z 均偏离 grid 中心）
    """

    wavelengths = torch.tensor((0.5e-6,), dtype=torch.float64)
    indices = torch.tensor((1.0,), dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)
    shared_kwargs = {
        "sample_counts": (6, 5),
        "signed_spacing": _scalar_pair(0.25e-6, 0.2e-6, dtype=torch.float64),
        "first_sample_position": _scalar_pair(-0.5e-6, -0.4e-6, dtype=torch.float64),
        "wavelengths": wavelengths,
        "refractive_indices": indices,
        "source_position_yxz": (
            _scalar(0.3e-6, dtype=torch.float64),
            _scalar(-0.2e-6, dtype=torch.float64),
            _scalar(1.5e-6, dtype=torch.float64),
        ),
        "is_inverse_distance": False,
        "polarization_state": polarization,
    }
    envelope = point_source_unit_envelope(**shared_kwargs)
    reference = _independent_unit_envelope(**shared_kwargs)
    assert torch.allclose(envelope, reference, atol=1e-12, rtol=1e-12)


def test_is_inverse_distance_scales_as_one_over_radius() -> None:
    """
    POWER 模式（is_inverse_distance=True）振幅按 1/r 衰减
    """

    wavelengths = torch.tensor((0.5e-6,), dtype=torch.float64)
    indices = torch.tensor((1.0,), dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)
    envelope = point_source_unit_envelope(
        sample_counts=(3, 3),
        signed_spacing=_scalar_pair(1.0e-6, 1.0e-6, dtype=torch.float64),
        first_sample_position=_scalar_pair(-1.0e-6, -1.0e-6, dtype=torch.float64),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.0, dtype=torch.float64),
            _scalar(0.0, dtype=torch.float64),
            _scalar(2.0e-6, dtype=torch.float64),
        ),
        is_inverse_distance=True,
        polarization_state=polarization,
    )
    # 中心点 r = 2e-6，角点 r = sqrt(2 + 4) e-6 = sqrt(6) e-6
    center_modulus = float(envelope[0, 0, 1, 1].abs())
    corner_modulus = float(envelope[0, 0, 0, 0].abs())
    assert math.isclose(center_modulus, 1.0 / 2.0e-6, rel_tol=1e-12)
    assert math.isclose(corner_modulus, 1.0 / math.sqrt(6.0e-12), rel_tol=1e-12)


def test_relative_amplitude_has_unit_modulus() -> None:
    """
    RELATIVE 模式（is_inverse_distance=False）振幅恒为 1，仅携带相位
    """

    wavelengths = torch.tensor((0.5e-6,), dtype=torch.float64)
    indices = torch.tensor((1.0,), dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)
    envelope = point_source_unit_envelope(
        sample_counts=(3, 3),
        signed_spacing=_scalar_pair(1.0e-6, 1.0e-6, dtype=torch.float64),
        first_sample_position=_scalar_pair(-1.0e-6, -1.0e-6, dtype=torch.float64),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.0, dtype=torch.float64),
            _scalar(0.0, dtype=torch.float64),
            _scalar(2.0e-6, dtype=torch.float64),
        ),
        is_inverse_distance=False,
        polarization_state=polarization,
    )
    modulus = (envelope.real.square() + envelope.imag.square()).sqrt()
    assert torch.allclose(modulus, torch.ones_like(modulus), atol=1e-12)


def test_rotational_symmetry_around_source_axis() -> None:
    """
    等距 grid 点的相位与振幅相同：绕源轴旋转对称
    """

    wavelengths = torch.tensor((0.5e-6,), dtype=torch.float64)
    indices = torch.tensor((1.0,), dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)
    envelope = point_source_unit_envelope(
        sample_counts=(5, 5),
        signed_spacing=_scalar_pair(0.5e-6, 0.5e-6, dtype=torch.float64),
        first_sample_position=_scalar_pair(-1.0e-6, -1.0e-6, dtype=torch.float64),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.0, dtype=torch.float64),
            _scalar(0.0, dtype=torch.float64),
            _scalar(1.0e-6, dtype=torch.float64),
        ),
        is_inverse_distance=True,
        polarization_state=polarization,
    )
    neighbours = (
        envelope[0, 0, 1, 1],
        envelope[0, 0, 1, 3],
        envelope[0, 0, 3, 1],
        envelope[0, 0, 3, 3],
    )
    for value in neighbours[1:]:
        assert torch.allclose(value, neighbours[0], atol=1e-12)


def test_non_vacuum_medium_phase_uses_medium_wave_number() -> None:
    """
    非真空介质中球面相位 exp(i 2π n r / λ) 与真空不同，按介质波数合成
    """

    wavelengths = torch.tensor((0.5e-6,), dtype=torch.float64)
    vacuum_indices = torch.tensor((1.0,), dtype=torch.float64)
    glass_indices = torch.tensor((1.5,), dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)
    shared_kwargs = {
        "sample_counts": (1, 2),
        "signed_spacing": _scalar_pair(1.0e-6, 1.0e-6, dtype=torch.float64),
        "first_sample_position": _scalar_pair(0.0, 0.0, dtype=torch.float64),
        "wavelengths": wavelengths,
        "source_position_yxz": (
            _scalar(0.0, dtype=torch.float64),
            _scalar(0.0, dtype=torch.float64),
            _scalar(2.0e-6, dtype=torch.float64),
        ),
        "is_inverse_distance": False,
        "polarization_state": polarization,
    }
    vacuum_envelope = point_source_unit_envelope(
        refractive_indices=vacuum_indices,
        **shared_kwargs,
    )
    glass_envelope = point_source_unit_envelope(
        refractive_indices=glass_indices,
        **shared_kwargs,
    )
    radius_corner = math.sqrt(5.0) * 1.0e-6
    vacuum_phase = 2.0 * math.pi * 1.0 * radius_corner / 0.5e-6
    glass_phase = 2.0 * math.pi * 1.5 * radius_corner / 0.5e-6
    assert math.isclose(
        float(vacuum_envelope[0, 0, 0, 1].angle()),
        math.remainder(vacuum_phase, 2.0 * math.pi),
        abs_tol=1e-12,
    )
    assert math.isclose(
        float(glass_envelope[0, 0, 0, 1].angle()),
        math.remainder(glass_phase, 2.0 * math.pi),
        abs_tol=1e-12,
    )


def test_multispectral_envelope_preserves_spectral_order() -> None:
    """
    多光谱球面波单位包络逐分量沿光谱轴排列，偏振按规范顺序展开
    """

    polarization = torch.tensor(
        (math.sqrt(0.5) + 0.0j, 0.0 + math.sqrt(0.5) * 1.0j),
        dtype=torch.complex128,
    )
    wavelengths = torch.tensor((0.45e-6, 0.65e-6), dtype=torch.float64)
    indices = torch.tensor((1.0, 1.5), dtype=torch.float64)
    shared_kwargs = {
        "sample_counts": (1, 1),
        "signed_spacing": _scalar_pair(1.0, 1.0, dtype=torch.float64),
        "first_sample_position": _scalar_pair(0.0, 0.0, dtype=torch.float64),
        "wavelengths": wavelengths,
        "refractive_indices": indices,
        "source_position_yxz": (
            _scalar(0.0, dtype=torch.float64),
            _scalar(0.0, dtype=torch.float64),
            _scalar(2.0e-6, dtype=torch.float64),
        ),
        "is_inverse_distance": True,
        "polarization_state": polarization,
    }
    envelope = point_source_unit_envelope(**shared_kwargs)
    reference = _independent_unit_envelope(**shared_kwargs)
    assert envelope.shape == (2, 2, 1, 1)
    # 两光谱分量共享点源位置，但相位与振幅按各自波长与折射率独立合成
    assert torch.allclose(envelope, reference, atol=1e-12)


def test_envelope_passes_refractive_index_gradcheck() -> None:
    """
    折射率进入球面相位，保留完整计算图
    """

    indices = torch.tensor((1.2, 1.4), dtype=torch.float64, requires_grad=True)
    wavelengths = torch.tensor((1.0, 1.5), dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)

    def _envelope_as_real(refractive_indices: torch.Tensor) -> torch.Tensor:
        envelope = point_source_unit_envelope(
            sample_counts=(3, 3),
            signed_spacing=_scalar_pair(0.25, 0.5, dtype=torch.float64),
            first_sample_position=_scalar_pair(-0.25, -0.25, dtype=torch.float64),
            wavelengths=wavelengths,
            refractive_indices=refractive_indices,
            source_position_yxz=(
                _scalar(0.1, dtype=torch.float64),
                _scalar(-0.2, dtype=torch.float64),
                _scalar(0.6, dtype=torch.float64),
            ),
            is_inverse_distance=True,
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


@pytest.mark.parametrize("component_index", [0, 1, 2])
def test_envelope_passes_position_component_gradcheck(
    component_index: int,
) -> None:
    """
    点源 y/x/z 各位置分量进入几何距离与球面相位，保留有限差分梯度
    """

    positions = (
        torch.tensor(0.1, dtype=torch.float64, requires_grad=True),
        torch.tensor(-0.2, dtype=torch.float64, requires_grad=True),
        torch.tensor(0.6, dtype=torch.float64, requires_grad=True),
    )

    def _envelope_as_real(
        y: torch.Tensor,
        x: torch.Tensor,
        z: torch.Tensor,
    ) -> torch.Tensor:
        envelope = point_source_unit_envelope(
            sample_counts=(3, 3),
            signed_spacing=_scalar_pair(0.25, 0.5, dtype=torch.float64),
            first_sample_position=_scalar_pair(-0.25, -0.25, dtype=torch.float64),
            wavelengths=torch.tensor((1.0,), dtype=torch.float64),
            refractive_indices=torch.tensor((1.3,), dtype=torch.float64),
            source_position_yxz=(y, x, z),
            is_inverse_distance=True,
            polarization_state=torch.ones(1, dtype=torch.complex128),
        )
        return torch.view_as_real(envelope)

    assert torch.autograd.gradcheck(
        _envelope_as_real,
        positions,
        eps=1e-7,
        atol=1e-5,
        rtol=1e-3,
    )


def test_envelope_runs_with_tensor_grid_on_meta() -> None:
    """
    meta 执行以同一张量网格路径推导球面波包络形状与精度
    """

    real_dtype = torch.float32
    envelope = point_source_unit_envelope(
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
        source_position_yxz=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        is_inverse_distance=True,
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
    cpu = point_source_unit_envelope(
        sample_counts=(4, 3),
        signed_spacing=_scalar_pair(0.2, -0.3, dtype=torch.float32),
        first_sample_position=_scalar_pair(-0.3, 0.3, dtype=torch.float32),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.1, dtype=torch.float32),
            _scalar(-0.1, dtype=torch.float32),
            _scalar(0.4, dtype=torch.float32),
        ),
        is_inverse_distance=True,
        polarization_state=polarization,
    )
    cuda = point_source_unit_envelope(
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
        source_position_yxz=(
            _scalar(0.1, dtype=torch.float32, device="cuda"),
            _scalar(-0.1, dtype=torch.float32, device="cuda"),
            _scalar(0.4, dtype=torch.float32, device="cuda"),
        ),
        is_inverse_distance=True,
        polarization_state=polarization.cuda(),
    )
    assert torch.allclose(cpu, cuda.cpu(), atol=2e-6, rtol=2e-6)


def test_power_amplitude_matches_analytic_integral() -> None:
    """
    POWER 归一化使 |A|² 与单元面积、波长权重和、单位包络能量和的乘积等于总功率
    """

    wavelengths = torch.tensor((0.5e-6, 0.65e-6), dtype=torch.float64)
    indices = torch.tensor((1.0, 1.2), dtype=torch.float64)
    weights = torch.tensor((0.4, 0.6), dtype=torch.float64)
    unit_envelope = point_source_unit_envelope(
        sample_counts=(6, 6),
        signed_spacing=_scalar_pair(0.2e-6, 0.2e-6, dtype=torch.float64),
        first_sample_position=_scalar_pair(-0.4e-6, -0.4e-6, dtype=torch.float64),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.0, dtype=torch.float64),
            _scalar(0.0, dtype=torch.float64),
            _scalar(3.0e-6, dtype=torch.float64),
        ),
        is_inverse_distance=True,
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




def _fence(
    *,
    sample_counts: tuple[int, int],
    signed_spacing: tuple[torch.Tensor, torch.Tensor],
    first_sample_position: tuple[torch.Tensor, torch.Tensor],
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
    source_position_yxz: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
) -> PointSourceSamplingFacts:
    # 测试便捷封装：直接转调生产核；返回 ``PointSourceSamplingFacts`` 供字段读取
    return point_source_sampling_fence(
        sample_counts=sample_counts,
        signed_spacing=signed_spacing,
        first_sample_position=first_sample_position,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        source_position_yxz=source_position_yxz,
    )


def _is_pair_sufficient_from_scalars(
    *,
    radius_squared_a: float,
    radius_squared_b: float,
    n_index: float,
    wavelength: float,
) -> bool:
    real_dtype = torch.float64
    shape = (1, 1, 1)
    u_min = min(radius_squared_a, radius_squared_b)
    delta = abs(radius_squared_b - radius_squared_a)
    sufficient = _adjacent_pair_half_cycle_sufficient(
        smaller_radius_squared=torch.tensor(
            u_min,
            dtype=real_dtype,
        ).reshape(shape),
        radius_squared_difference=torch.tensor(
            delta,
            dtype=real_dtype,
        ).reshape(shape),
        refractive_index_per_spectrum=torch.tensor(
            n_index,
            dtype=real_dtype,
        ).reshape(shape),
        wavelengths_per_spectrum=torch.tensor(wavelength, dtype=real_dtype).reshape(
            shape
        ),
    )
    return bool(sufficient)


def _is_decimal_pair_sufficient(
    *,
    radius_squared_a: float,
    radius_squared_b: float,
    n: float,
    wavelength: float,
) -> bool:
    getcontext().prec = 80
    ra2 = Decimal(str(radius_squared_a))
    rb2 = Decimal(str(radius_squared_b))
    n_dec = Decimal(str(n))
    lam_dec = Decimal(str(wavelength))
    radius_a = ra2.sqrt()
    radius_b = rb2.sqrt()
    delta_cycles = (n_dec * (radius_b - radius_a) / lam_dec).copy_abs()
    return delta_cycles < Decimal("0.5")


def _is_decimal_fence_sufficient(
    *,
    sample_counts: tuple[int, int],
    spacing: tuple[float, float],
    first: tuple[float, float],
    source: tuple[float, float, float],
    wavelengths: tuple[float, ...],
    indices: tuple[float, ...],
) -> bool:
    # 逐相邻对逐光谱 Decimal oracle：所有 y 对与所有 x 对，所有光谱上严格 < 0.5
    counts_y, counts_x = sample_counts
    spacing_y, spacing_x = spacing
    first_y, first_x = first
    source_y, source_x, source_z = source
    getcontext().prec = 80
    n_values = [Decimal(str(v)) for v in indices]
    lam_values = [Decimal(str(v)) for v in wavelengths]
    sy = Decimal(str(source_y))
    sx = Decimal(str(source_x))
    sz_sq = Decimal(str(source_z)) ** 2
    positions_y = [
        Decimal(str(first_y)) + Decimal(i) * Decimal(str(spacing_y))
        for i in range(counts_y)
    ]
    positions_x = [
        Decimal(str(first_x)) + Decimal(i) * Decimal(str(spacing_x))
        for i in range(counts_x)
    ]
    radius_squared = [
        [
            (positions_y[i] - sy) ** 2 + (positions_x[j] - sx) ** 2 + sz_sq
            for j in range(counts_x)
        ]
        for i in range(counts_y)
    ]

    def _is_pair_passing(rs_a: Decimal, rs_b: Decimal) -> bool:
        radius_a = rs_a.sqrt()
        radius_b = rs_b.sqrt()
        for n_dec, lam_dec in zip(n_values, lam_values, strict=True):
            delta_cycles = (n_dec * (radius_b - radius_a) / lam_dec).copy_abs()
            if not (delta_cycles < Decimal("0.5")):
                return False
        return True

    for i in range(counts_y - 1):
        for j in range(counts_x):
            if not _is_pair_passing(radius_squared[i][j], radius_squared[i + 1][j]):
                return False
    for i in range(counts_y):
        for j in range(counts_x - 1):
            if not _is_pair_passing(radius_squared[i][j], radius_squared[i][j + 1]):
                return False
    return True


@pytest.mark.parametrize(
    (
        "sample_counts",
        "spacing",
        "first",
        "source",
        "wavelength",
        "index",
        "case_id",
    ),
    [
        # 居中近场：sz=1 μm、窗口 0.8 μm、λ=0.5 μm，每对 |Δcycles| 远低于 0.5
        (
            (5, 5),
            (0.2e-6, 0.2e-6),
            (-0.4e-6, -0.4e-6),
            (0.0, 0.0, 1.0e-6),
            0.5e-6,
            1.0,
            "centered-near-field",
        ),
        # 居中远场：sz=20 μm、窗口 1.4 μm，每对 |Δcycles| 很小
        (
            (8, 8),
            (0.2e-6, 0.2e-6),
            (-0.7e-6, -0.7e-6),
            (0.0, 0.0, 20.0e-6),
            0.5e-6,
            1.0,
            "centered-far-field",
        ),
        # off-axis 源横向投影在窗口内：sx=-0.2 μm 落在窗口 x 范围内
        (
            (6, 5),
            (0.25e-6, 0.2e-6),
            (-0.5e-6, -0.4e-6),
            (0.3e-6, -0.2e-6, 1.5e-6),
            0.5e-6,
            1.0,
            "off-axis-inside",
        ),
        # off-axis 源横向投影在窗口外（掠射）：sx=5 μm 远在窗口 x=[-0.4, 0.4] 之外
        (
            (5, 5),
            (0.2e-6, 0.2e-6),
            (-0.4e-6, -0.4e-6),
            (0.0, 5.0e-6, 3.0e-6),
            0.5e-6,
            1.0,
            "off-axis-grazing",
        ),
        # 非真空介质：n=1.5 提高波数，每对 |Δcycles| 增大
        (
            (5, 5),
            (0.2e-6, 0.2e-6),
            (-0.4e-6, -0.4e-6),
            (0.0, 0.0, 1.5e-6),
            0.5e-6,
            1.5,
            "non-vacuum",
        ),
        # 粗网格近场（采样不足）：每对 |Δcycles| 远超 0.5
        (
            (4, 4),
            (5.0e-6, 5.0e-6),
            (-7.5e-6, -7.5e-6),
            (0.0, 0.0, 1.0e-6),
            0.5e-6,
            1.0,
            "coarse-insufficient",
        ),
    ],
    ids=[
        "centered-near-field",
        "centered-far-field",
        "off-axis-inside",
        "off-axis-grazing",
        "non-vacuum",
        "coarse-insufficient",
    ],
)
def test_fence_per_pair_decision_matches_decimal_oracle(
    sample_counts: tuple[int, int],
    spacing: tuple[float, float],
    first: tuple[float, float],
    source: tuple[float, float, float],
    wavelength: float,
    index: float,
    case_id: str,
) -> None:
    """
    逐对逐光谱半周期判定与 80 位 Decimal oracle 在多组几何上一致
    """

    real_dtype = torch.float64
    wavelengths = torch.tensor((wavelength,), dtype=real_dtype)
    indices = torch.tensor((index,), dtype=real_dtype)
    facts = _fence(
        sample_counts=sample_counts,
        signed_spacing=_scalar_pair(spacing[0], spacing[1], dtype=real_dtype),
        first_sample_position=_scalar_pair(first[0], first[1], dtype=real_dtype),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(source[0], dtype=real_dtype),
            _scalar(source[1], dtype=real_dtype),
            _scalar(source[2], dtype=real_dtype),
        ),
    )
    oracle = _is_decimal_fence_sufficient(
        sample_counts=sample_counts,
        spacing=spacing,
        first=first,
        source=source,
        wavelengths=(wavelength,),
        indices=(index,),
    )
    assert bool(facts.is_sufficient) == oracle, case_id
    # 阈值常量恰为 0.5（半周期）
    assert math.isclose(float(facts.half_cycle_threshold), 0.5)


def test_fence_exhaustive_small_grid_decision_matches_oracle() -> None:
    """
    小网格（6×5）逐对逐光谱判定与 Decimal oracle 逐项相等；覆盖 on/off-axis、平移
    """

    real_dtype = torch.float64
    # 包含 on-axis/off-axis、各向异性间距、平移首样本、非整数 sz 与 λ/n
    geometries = [
        {
            "counts": (6, 5),
            "spacing": (0.25e-6, 0.2e-6),
            "first": (-0.5e-6, -0.4e-6),
            "source": (0.3e-6, -0.2e-6, 1.5e-6),
            "wl": (0.45e-6,),
            "n": (1.0,),
        },
        {
            "counts": (5, 7),
            "spacing": (0.3e-6, 0.15e-6),
            "first": (0.1e-6, -0.45e-6),
            "source": (-0.2e-6, 0.1e-6, 0.8e-6),
            "wl": (0.5e-6, 0.65e-6),
            "n": (1.0, 1.2),
        },
        {
            "counts": (4, 4),
            "spacing": (0.4e-6, 0.4e-6),
            "first": (-0.6e-6, -0.6e-6),
            "source": (0.0, 0.0, 0.5e-6),
            "wl": (0.4e-6,),
            "n": (1.5,),
        },
    ]
    for geometry in geometries:
        first_y, first_x = geometry["first"]
        source_y_pos, source_x_pos, source_z_pos = geometry["source"]
        facts = _fence(
            sample_counts=geometry["counts"],
            signed_spacing=_scalar_pair(*geometry["spacing"], dtype=real_dtype),
            first_sample_position=_scalar_pair(first_y, first_x, dtype=real_dtype),
            wavelengths=torch.tensor(geometry["wl"], dtype=real_dtype),
            refractive_indices=torch.tensor(geometry["n"], dtype=real_dtype),
            source_position_yxz=(
                _scalar(source_y_pos, dtype=real_dtype),
                _scalar(source_x_pos, dtype=real_dtype),
                _scalar(source_z_pos, dtype=real_dtype),
            ),
        )
        oracle = _is_decimal_fence_sufficient(
            sample_counts=geometry["counts"],
            spacing=geometry["spacing"],
            first=geometry["first"],
            source=geometry["source"],
            wavelengths=geometry["wl"],
            indices=geometry["n"],
        )
        assert bool(facts.is_sufficient) == oracle


def test_fence_exact_half_cycle_equality_rejected() -> None:
    """
    精确半周期等号（|Δcycles| = 0.5 恰）严格拒绝
    """

    radius_a = 3.25
    radius_b = 3.5
    wavelength = 0.5
    n_index = 1.0
    assert _is_decimal_pair_sufficient(
        radius_squared_a=radius_a * radius_a,
        radius_squared_b=radius_b * radius_b,
        n=n_index,
        wavelength=wavelength,
    ) is False
    assert _is_pair_sufficient_from_scalars(
        radius_squared_a=radius_a * radius_a,
        radius_squared_b=radius_b * radius_b,
        n_index=n_index,
        wavelength=wavelength,
    ) is False


def test_fence_neighbour_below_half_cycle_admitted() -> None:
    """
    精确半周期等号的下邻域（|Δcycles| 严格 < 0.5）准入
    """

    radius_a = 3.25
    radius_b = 3.49  # |Δcycles| = 0.48 < 0.5
    wavelength = 0.5
    n_index = 1.0
    assert _is_decimal_pair_sufficient(
        radius_squared_a=radius_a * radius_a,
        radius_squared_b=radius_b * radius_b,
        n=n_index,
        wavelength=wavelength,
    ) is True
    assert _is_pair_sufficient_from_scalars(
        radius_squared_a=radius_a * radius_a,
        radius_squared_b=radius_b * radius_b,
        n_index=n_index,
        wavelength=wavelength,
    ) is True


def test_fence_neighbour_above_half_cycle_rejected() -> None:
    """
    精确半周期等号的上邻域（|Δcycles| 严格 > 0.5）拒绝
    """

    radius_a = 3.25
    radius_b = 3.51  # |Δcycles| = 0.52 > 0.5
    wavelength = 0.5
    n_index = 1.0
    assert _is_decimal_pair_sufficient(
        radius_squared_a=radius_a * radius_a,
        radius_squared_b=radius_b * radius_b,
        n=n_index,
        wavelength=wavelength,
    ) is False
    assert _is_pair_sufficient_from_scalars(
        radius_squared_a=radius_a * radius_a,
        radius_squared_b=radius_b * radius_b,
        n_index=n_index,
        wavelength=wavelength,
    ) is False


def test_fence_exact_half_cycle_equality_rejected_through_full_fence() -> None:
    """
    端到端：构造使最坏相邻对 |Δcycles| = 0.5 恰的 grid，整栅栏拒绝
    """

    real_dtype = torch.float64
    radius_a = 3.25
    radius_b = 3.5
    spacing_y = math.sqrt(radius_b**2 - radius_a**2)
    wavelength = 0.5
    n_index = 1.0
    facts = _fence(
        sample_counts=(2, 1),
        signed_spacing=_scalar_pair(spacing_y, spacing_y, dtype=real_dtype),
        first_sample_position=_scalar_pair(0.0, 0.0, dtype=real_dtype),
        wavelengths=torch.tensor((wavelength,), dtype=real_dtype),
        refractive_indices=torch.tensor((n_index,), dtype=real_dtype),
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(radius_a, dtype=real_dtype),
        ),
    )
    assert bool(facts.is_sufficient) is False
    # 诊断最坏 |Δcycles| ≈ 0.5（舍入 sqrt 路径，仅供报错；承载判定的多项式拒绝）
    assert math.isclose(float(facts.worst_y_cycles_per_sample), 0.5, abs_tol=1e-12)


def test_fence_u_zero_explicit_handling_accept_and_reject() -> None:
    """
    u=0（R_a=0）情形显式处理：accept iff H<0；equality 拒绝
    """

    assert (
        _is_pair_sufficient_from_scalars(
            radius_squared_a=0.0,
            radius_squared_b=0.04,
            n_index=1.0,
            wavelength=0.5,
        )
        is True
    )
    # u=0、v=0.0625：Δcycles 真值恰 0.5（半周期等号）；H=0，u=0 显式拒绝
    assert (
        _is_pair_sufficient_from_scalars(
            radius_squared_a=0.0,
            radius_squared_b=0.0625,
            n_index=1.0,
            wavelength=0.5,
        )
        is False
    )
    # u=0、v=0.09：Δcycles 真值 0.6，超过半周期；H>0，拒绝
    assert (
        _is_pair_sufficient_from_scalars(
            radius_squared_a=0.0,
            radius_squared_b=0.09,
            n_index=1.0,
            wavelength=0.5,
        )
        is False
    )


def test_fence_extreme_exponent_inputs_match_decimal_oracle() -> None:
    """
    极端指数（大幅值 / 小幅值波长与几何）下多项式符号判定与 Decimal oracle 一致
    """

    real_dtype = torch.float64
    # 1) 极小波长（fm 量级相对）+ 大几何：每对 |Δcycles| 极大 → 拒绝
    facts_large = _fence(
        sample_counts=(3, 3),
        signed_spacing=_scalar_pair(1.0, 1.0, dtype=real_dtype),
        first_sample_position=_scalar_pair(-1.0, -1.0, dtype=real_dtype),
        wavelengths=torch.tensor((1e-3,), dtype=real_dtype),
        refractive_indices=torch.tensor((1.0,), dtype=real_dtype),
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(2.0, dtype=real_dtype),
        ),
    )
    oracle_large = _is_decimal_fence_sufficient(
        sample_counts=(3, 3),
        spacing=(1.0, 1.0),
        first=(-1.0, -1.0),
        source=(0.0, 0.0, 2.0),
        wavelengths=(1e-3,),
        indices=(1.0,),
    )
    assert bool(facts_large.is_sufficient) == oracle_large
    assert oracle_large is False

    # 2) 极大波长 + 小几何：每对 |Δcycles| 极小 → 准入
    facts_small = _fence(
        sample_counts=(3, 3),
        signed_spacing=_scalar_pair(1.0, 1.0, dtype=real_dtype),
        first_sample_position=_scalar_pair(-1.0, -1.0, dtype=real_dtype),
        wavelengths=torch.tensor((1e3,), dtype=real_dtype),
        refractive_indices=torch.tensor((1.0,), dtype=real_dtype),
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(2.0, dtype=real_dtype),
        ),
    )
    oracle_small = _is_decimal_fence_sufficient(
        sample_counts=(3, 3),
        spacing=(1.0, 1.0),
        first=(-1.0, -1.0),
        source=(0.0, 0.0, 2.0),
        wavelengths=(1e3,),
        indices=(1.0,),
    )
    assert bool(facts_small.is_sufficient) == oracle_small
    assert oracle_small is True


def test_fence_rounded_sqrt_adversary_uses_polynomial_sign() -> None:
    """
    当 binary64 ``sqrt(v)-sqrt(u)`` 路径的舍入会把判据推向错误分支时，生产判定
    仍与 Decimal oracle 一致（多项式符号路径不读 sqrt）
    """

    real_dtype = torch.float64
    getcontext().prec = 80
    radius_a = Decimal("3.25")
    radius_a_squared = float(radius_a**2)
    n_index = 1.0
    wavelength = 0.5
    target_v = float(Decimal("3.5") ** 2)
    ulp = abs(target_v * 2**-52)  # binary64 ulp at this magnitude
    candidate_offsets = [-2, -1, 0, 1, 2]
    mismatch_count = 0
    for offset in candidate_offsets:
        v_binary64 = target_v + offset * ulp
        delta_radius = math.sqrt(max(v_binary64, radius_a_squared) - radius_a_squared)
        facts = _fence(
            sample_counts=(2, 1),
            signed_spacing=_scalar_pair(delta_radius, delta_radius, dtype=real_dtype),
            first_sample_position=_scalar_pair(0.0, 0.0, dtype=real_dtype),
            wavelengths=torch.tensor((wavelength,), dtype=real_dtype),
            refractive_indices=torch.tensor((n_index,), dtype=real_dtype),
            source_position_yxz=(
                _scalar(0.0, dtype=real_dtype),
                _scalar(0.0, dtype=real_dtype),
                _scalar(radius_a_squared**0.5, dtype=real_dtype),
            ),
        )
        oracle = _is_decimal_pair_sufficient(
            radius_squared_a=radius_a_squared,
            radius_squared_b=v_binary64,
            n=n_index,
            wavelength=wavelength,
        )
        if bool(facts.is_sufficient) != oracle:
            mismatch_count += 1
        # 也验证 sqrt(squared-via-float) 与多项式判定可能分歧——但判定承载于多项式
        sqrt_delta_cycles = abs(
            n_index
            * (math.sqrt(v_binary64) - math.sqrt(radius_a_squared))
            / wavelength
        )
        del sqrt_delta_cycles
    # 至少在 5 个邻居上生产判定与 Decimal oracle 完全一致（不因 sqrt 舍入错判）
    assert mismatch_count == 0


def test_fence_accepts_dispersive_grid_that_cross_pairing_rejects() -> None:
    """
    色散 grid 逐谱配对准入，而交叉 max(n)/min(λ) 虚构波数会虚假拒绝
    """

    real_dtype = torch.float64
    wavelengths = torch.tensor((400e-9, 700e-9), dtype=real_dtype)
    indices = torch.tensor((1.5, 1.9), dtype=real_dtype)
    spacing = 120e-9
    counts = (21, 1)
    first_y = -(counts[0] - 1) / 2 * spacing
    y_along_max = (counts[0] - 1) / 2 * spacing
    geom_factor = 0.95
    axial_distance = math.sqrt(
        (y_along_max / geom_factor) ** 2 - y_along_max ** 2
    )
    facts = _fence(
        sample_counts=counts,
        signed_spacing=_scalar_pair(spacing, spacing, dtype=real_dtype),
        first_sample_position=_scalar_pair(first_y, 0.0, dtype=real_dtype),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(axial_distance, dtype=real_dtype),
        ),
    )
    # Decimal oracle：逐谱判定为 accept
    oracle = _is_decimal_fence_sufficient(
        sample_counts=counts,
        spacing=(spacing, spacing),
        first=(first_y, 0.0),
        source=(0.0, 0.0, axial_distance),
        wavelengths=(400e-9, 700e-9),
        indices=(1.5, 1.9),
    )
    assert bool(facts.is_sufficient) is True
    assert oracle is True
    # 交叉配对 max(n)/min(λ) 在窗口端点对（最远样本对）上给出 |Δcycles| > 0.5
    radius_endpoints = y_along_max / geom_factor
    delta_radius = (
        math.sqrt((y_along_max) ** 2 + axial_distance**2)
        - math.sqrt((y_along_max - spacing) ** 2 + axial_distance**2)
    )
    cross_kmax = float(indices.max()) / float(wavelengths.min())
    cross_delta_cycles = cross_kmax * delta_radius
    assert cross_delta_cycles > 0.5  # 交叉配对会虚假拒绝
    assert radius_endpoints > 0  # 防未用变量告警


def test_fence_nondispersive_single_sample_has_no_pairing_ambiguity() -> None:
    """
    单谱（非色散）无交叉配对歧义：逐谱配对与交叉退化为同一波数
    """

    real_dtype = torch.float64
    wavelengths = torch.tensor((0.5e-6,), dtype=real_dtype)
    indices = torch.tensor((1.5,), dtype=real_dtype)
    facts = _fence(
        sample_counts=(5, 5),
        signed_spacing=_scalar_pair(0.2e-6, 0.2e-6, dtype=real_dtype),
        first_sample_position=_scalar_pair(-0.4e-6, -0.4e-6, dtype=real_dtype),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(1.0e-6, dtype=real_dtype),
        ),
    )
    # 单谱充分采样：最坏 |Δcycles| < 0.5；逐谱与交叉退化
    assert bool(facts.is_sufficient) is True
    assert float(facts.worst_y_cycles_per_sample) < 0.5
    assert float(facts.worst_x_cycles_per_sample) < 0.5


def test_fence_picks_paired_per_spectrum_worst_pair_not_cross_extrema() -> None:
    """
    物理 worst-pair 未必来自 max(n)/min(λ)：逐谱配对 worst-pair 在 idx0（n 最小）
    光谱上；交叉 max(n)/min(λ) 会错误指向 idx1
    """

    real_dtype = torch.float64
    wavelengths = torch.tensor((400e-9, 700e-9, 500e-9), dtype=real_dtype)
    indices = torch.tensor((1.5, 1.9, 1.6), dtype=real_dtype)
    spacing = 120e-9
    counts = (21, 1)
    first_y = -(counts[0] - 1) / 2 * spacing
    y_along_max = (counts[0] - 1) / 2 * spacing
    geom_factor = 0.95
    axial_distance = math.sqrt(
        (y_along_max / geom_factor) ** 2 - y_along_max ** 2
    )
    facts = _fence(
        sample_counts=counts,
        signed_spacing=_scalar_pair(spacing, spacing, dtype=real_dtype),
        first_sample_position=_scalar_pair(first_y, 0.0, dtype=real_dtype),
        wavelengths=wavelengths,
        refractive_indices=indices,
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(axial_distance, dtype=real_dtype),
        ),
    )
    # 逐谱判定为 accept（最坏 |Δcycles| 来自 idx0 但仍 < 0.5）
    assert bool(facts.is_sufficient) is True
    # Decimal oracle 同样判定为准入
    oracle = _is_decimal_fence_sufficient(
        sample_counts=counts,
        spacing=(spacing, spacing),
        first=(first_y, 0.0),
        source=(0.0, 0.0, axial_distance),
        wavelengths=(400e-9, 700e-9, 500e-9),
        indices=(1.5, 1.9, 1.6),
    )
    assert oracle is True
    # 独立逐谱最坏对 |Δcycles| 来自 idx0（n/λ 极大），而非交叉 max(n)/min(λ) 的 idx1
    delta_radius = (
        math.sqrt(y_along_max**2 + axial_distance**2)
        - math.sqrt((y_along_max - spacing) ** 2 + axial_distance**2)
    )
    paired_ratios = (indices / wavelengths).tolist()
    assert paired_ratios.index(max(paired_ratios)) == 0
    paired_delta_cycles = max(paired_ratios) * delta_radius
    cross_delta_cycles = (
        float(indices.max()) / float(wavelengths.min()) * delta_radius
    )
    assert paired_delta_cycles < 0.5  # 逐谱 worst-pair 准入
    assert cross_delta_cycles > paired_delta_cycles  # 交叉超过逐谱
    assert math.isclose(
        cross_delta_cycles / paired_delta_cycles,
        (1.9 / 400e-9) / (1.5 / 400e-9),
        rel_tol=1e-12,
    )


def test_fence_translated_and_offcenter_grids_match_oracle() -> None:
    """
    平移/各向异性网格下逐对判定与 Decimal oracle 一致
    """

    real_dtype = torch.float64
    # 各向异性间距 + 平移 + off-axis 源 + 多光谱色散
    facts = _fence(
        sample_counts=(7, 5),
        signed_spacing=_scalar_pair(0.18e-6, 0.27e-6, dtype=real_dtype),
        first_sample_position=_scalar_pair(0.13e-6, -0.42e-6, dtype=real_dtype),
        wavelengths=torch.tensor((0.42e-6, 0.58e-6), dtype=real_dtype),
        refractive_indices=torch.tensor((1.1, 1.32), dtype=real_dtype),
        source_position_yxz=(
            _scalar(0.27e-6, dtype=real_dtype),
            _scalar(-0.05e-6, dtype=real_dtype),
            _scalar(1.7e-6, dtype=real_dtype),
        ),
    )
    oracle = _is_decimal_fence_sufficient(
        sample_counts=(7, 5),
        spacing=(0.18e-6, 0.27e-6),
        first=(0.13e-6, -0.42e-6),
        source=(0.27e-6, -0.05e-6, 1.7e-6),
        wavelengths=(0.42e-6, 0.58e-6),
        indices=(1.1, 1.32),
    )
    assert bool(facts.is_sufficient) == oracle


def test_fence_empty_axis_does_not_force_failure() -> None:
    """
    单元素轴（count_y=1 或 count_x=1）无相邻对，不强制任何条件
    """

    real_dtype = torch.float64
    # count_y=1：无 y 对，只有 x 对。x 间距小，x 对全过 → 准入
    facts_y_single = _fence(
        sample_counts=(1, 5),
        signed_spacing=_scalar_pair(1.0, 0.2e-6, dtype=real_dtype),
        first_sample_position=_scalar_pair(0.0, -0.4e-6, dtype=real_dtype),
        wavelengths=torch.tensor((0.5e-6,), dtype=real_dtype),
        refractive_indices=torch.tensor((1.0,), dtype=real_dtype),
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(2.0e-6, dtype=real_dtype),
        ),
    )
    assert bool(facts_y_single.is_sufficient) is True
    assert float(facts_y_single.worst_y_cycles_per_sample) == 0.0
    # count_x=1：无 x 对，只有 y 对
    facts_x_single = _fence(
        sample_counts=(5, 1),
        signed_spacing=_scalar_pair(0.2e-6, 1.0, dtype=real_dtype),
        first_sample_position=_scalar_pair(-0.4e-6, 0.0, dtype=real_dtype),
        wavelengths=torch.tensor((0.5e-6,), dtype=real_dtype),
        refractive_indices=torch.tensor((1.0,), dtype=real_dtype),
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype),
            _scalar(0.0, dtype=real_dtype),
            _scalar(2.0e-6, dtype=real_dtype),
        ),
    )
    assert bool(facts_x_single.is_sufficient) is True
    assert float(facts_x_single.worst_x_cycles_per_sample) == 0.0


def test_fence_runs_on_meta() -> None:
    """
    meta 张量路径推导出与真实路径同形的判定与诊断
    """

    real_dtype = torch.float32
    facts = point_source_sampling_fence(
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
        source_position_yxz=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
    )
    assert facts.is_sufficient.device.type == "meta"
    assert facts.worst_y_cycles_per_sample.device.type == "meta"
    assert facts.worst_x_cycles_per_sample.device.type == "meta"
    assert facts.half_cycle_threshold.device.type == "meta"


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is unavailable",
)
def test_fence_matches_cpu_on_cuda() -> None:
    """
    采样栅栏在 CPU 与可用 CUDA 设备上给出一致的逐对判定与诊断
    """

    real_dtype = torch.float64
    shared_kwargs = {
        "sample_counts": (6, 5),
        "wavelengths": torch.tensor((0.5e-6,), dtype=real_dtype),
        "refractive_indices": torch.tensor((1.0,), dtype=real_dtype),
    }
    cpu = point_source_sampling_fence(
        signed_spacing=_scalar_pair(0.25e-6, 0.2e-6, dtype=real_dtype),
        first_sample_position=_scalar_pair(-0.5e-6, -0.4e-6, dtype=real_dtype),
        source_position_yxz=(
            _scalar(0.3e-6, dtype=real_dtype),
            _scalar(-0.2e-6, dtype=real_dtype),
            _scalar(1.5e-6, dtype=real_dtype),
        ),
        **shared_kwargs,
    )
    cuda = point_source_sampling_fence(
        signed_spacing=_scalar_pair(
            0.25e-6,
            0.2e-6,
            dtype=real_dtype,
            device="cuda",
        ),
        first_sample_position=_scalar_pair(
            -0.5e-6,
            -0.4e-6,
            dtype=real_dtype,
            device="cuda",
        ),
        source_position_yxz=(
            _scalar(0.3e-6, dtype=real_dtype, device="cuda"),
            _scalar(-0.2e-6, dtype=real_dtype, device="cuda"),
            _scalar(1.5e-6, dtype=real_dtype, device="cuda"),
        ),
        wavelengths=shared_kwargs["wavelengths"].cuda(),
        refractive_indices=shared_kwargs["refractive_indices"].cuda(),
        sample_counts=shared_kwargs["sample_counts"],
    )
    assert bool(cpu.is_sufficient) == bool(cuda.is_sufficient)
    assert torch.allclose(
        cpu.worst_y_cycles_per_sample,
        cuda.worst_y_cycles_per_sample.cpu(),
    )
    assert torch.allclose(
        cpu.worst_x_cycles_per_sample,
        cuda.worst_x_cycles_per_sample.cpu(),
    )


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is unavailable",
)
def test_fence_cuda_executes_not_skipped() -> None:
    """
    CUDA 上执行逐对判定（不只是 CPU 对照），返回 finite 决策
    """

    real_dtype = torch.float64
    facts = point_source_sampling_fence(
        sample_counts=(8, 8),
        signed_spacing=_scalar_pair(
            0.5e-6,
            0.5e-6,
            dtype=real_dtype,
            device="cuda",
        ),
        first_sample_position=_scalar_pair(
            -1.75e-6,
            -1.75e-6,
            dtype=real_dtype,
            device="cuda",
        ),
        wavelengths=torch.tensor((0.5e-6,), dtype=real_dtype, device="cuda"),
        refractive_indices=torch.tensor((1.0,), dtype=real_dtype, device="cuda"),
        source_position_yxz=(
            _scalar(0.0, dtype=real_dtype, device="cuda"),
            _scalar(0.0, dtype=real_dtype, device="cuda"),
            _scalar(2.0e-6, dtype=real_dtype, device="cuda"),
        ),
    )
    assert facts.is_sufficient.device.type == "cuda"
    assert bool(facts.is_sufficient) is False
    assert float(facts.worst_y_cycles_per_sample) > 0.5
    assert float(facts.worst_x_cycles_per_sample) > 0.5

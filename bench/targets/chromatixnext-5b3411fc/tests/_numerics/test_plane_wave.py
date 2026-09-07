from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.plane_wave import (
    plane_wave_envelope,
    power_normalized_amplitude,
)

_FD = torch.float64


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
def test_directional_plane_wave_matches_known_multispectral_phase(
    real_dtype: torch.dtype,
    complex_dtype: torch.dtype,
    tolerance: float,
) -> None:
    """
    共享传播方向按各波长波数生成已知空间相位
    """

    root_half = math.sqrt(0.5)
    envelope = plane_wave_envelope(
        sample_counts=(2, 1),
        signed_spacing=_scalar_pair(1.0, 1.0, dtype=real_dtype),
        first_sample_position=_scalar_pair(0.0, 0.0, dtype=real_dtype),
        wavelengths=torch.tensor((1.0, 2.0), dtype=real_dtype),
        refractive_indices=torch.ones(2, dtype=real_dtype),
        polarization_state=torch.ones(1, dtype=complex_dtype),
        propagation_direction=(
            torch.tensor(0.25, dtype=real_dtype),
            torch.tensor(0.0, dtype=real_dtype),
        ),
        transverse_wavevector=None,
    )
    expected = torch.tensor(
        [
            [
                [
                    [1.0 + 0.0j],
                    [0.0 + 1.0j],
                ],
            ],
            [
                [
                    [1.0 + 0.0j],
                    [root_half + root_half * 1.0j],
                ],
            ],
        ],
        dtype=complex_dtype,
    )

    assert envelope.dtype is complex_dtype
    assert torch.allclose(
        envelope,
        expected,
        atol=tolerance,
        rtol=tolerance,
    )


def test_transverse_wavevector_preserves_spectral_order_and_polarization(
) -> None:
    """
    共享横向波矢跨光谱保持同相位，并按规范顺序展开偏振分量
    """

    polarization = torch.tensor(
        (math.sqrt(0.5) + 0.0j, 0.0 + math.sqrt(0.5) * 1.0j),
        dtype=torch.complex128,
    )
    envelope = plane_wave_envelope(
        sample_counts=(2, 1),
        signed_spacing=_scalar_pair(1.0, 1.0, dtype=torch.float64),
        first_sample_position=_scalar_pair(0.0, 0.0, dtype=torch.float64),
        wavelengths=torch.tensor((1.0, 2.0), dtype=torch.float64),
        refractive_indices=torch.ones(2, dtype=torch.float64),
        polarization_state=polarization,
        propagation_direction=None,
        transverse_wavevector=(
            torch.tensor(math.pi / 2.0, dtype=torch.float64),
            torch.tensor(0.0, dtype=torch.float64),
        ),
    )
    expected_phase = torch.tensor(
        (1.0 + 0.0j, 0.0 + 1.0j),
        dtype=torch.complex128,
    ).reshape(1, 1, 2, 1)
    expected = (
        expected_phase
        * polarization.reshape(1, 2, 1, 1)
    ).expand(2, -1, -1, -1)

    assert torch.allclose(envelope, expected, atol=1e-12, rtol=1e-12)


def test_plane_wave_envelope_passes_refractive_index_gradcheck() -> None:
    """
    每次合成保留折射率进入空间相位的完整计算图
    """

    refractive_indices = torch.tensor(
        (1.2, 1.4),
        dtype=torch.float64,
        requires_grad=True,
    )
    wavelengths = torch.tensor((1.0, 1.5), dtype=torch.float64)
    polarization = torch.ones(1, dtype=torch.complex128)
    direction = (
        torch.tensor(0.2, dtype=torch.float64),
        torch.tensor(-0.1, dtype=torch.float64),
    )

    def _envelope_as_real(indices: torch.Tensor) -> torch.Tensor:
        # 将复包络展开为 gradcheck 所需的实数视图
        envelope = plane_wave_envelope(
            sample_counts=(2, 2),
            signed_spacing=_scalar_pair(
                0.25,
                0.5,
                dtype=torch.float64,
            ),
            first_sample_position=_scalar_pair(
                -0.125,
                -0.25,
                dtype=torch.float64,
            ),
            wavelengths=wavelengths,
            refractive_indices=indices,
            polarization_state=polarization,
            propagation_direction=direction,
            transverse_wavevector=None,
        )
        return torch.view_as_real(envelope)

    assert torch.autograd.gradcheck(
        _envelope_as_real,
        (refractive_indices,),
        eps=1e-7,
        atol=1e-5,
        rtol=1e-3,
    )


def test_plane_wave_envelope_passes_spacing_gradcheck() -> None:
    """
    空间采样间距作为物理张量进入平面波坐标并保留有限差分梯度
    """

    spacing_y = torch.tensor(
        0.25,
        dtype=torch.float64,
        requires_grad=True,
    )
    fixed_spacing_x = torch.tensor(0.5, dtype=torch.float64)
    origin = (
        torch.tensor(-0.125, dtype=torch.float64),
        torch.tensor(-0.25, dtype=torch.float64),
    )

    def _envelope_as_real(spacing: torch.Tensor) -> torch.Tensor:
        envelope = plane_wave_envelope(
            sample_counts=(3, 2),
            signed_spacing=(spacing, fixed_spacing_x),
            first_sample_position=origin,
            wavelengths=torch.tensor((1.0,), dtype=torch.float64),
            refractive_indices=torch.tensor((1.2,), dtype=torch.float64),
            polarization_state=torch.ones(1, dtype=torch.complex128),
            propagation_direction=(
                torch.tensor(0.2, dtype=torch.float64),
                torch.tensor(-0.1, dtype=torch.float64),
            ),
            transverse_wavevector=None,
        )
        return torch.view_as_real(envelope)

    assert torch.autograd.gradcheck(
        _envelope_as_real,
        (spacing_y,),
        eps=1e-7,
        atol=1e-5,
        rtol=1e-3,
    )


def test_plane_wave_envelope_runs_with_tensor_grid_on_meta() -> None:
    """
    meta 执行以同一张量网格路径推导平面波形状与精度
    """

    real_dtype = torch.float32
    envelope = plane_wave_envelope(
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
        refractive_indices=torch.empty(
            (2,),
            dtype=real_dtype,
            device="meta",
        ),
        polarization_state=torch.empty(
            (1,),
            dtype=torch.complex64,
            device="meta",
        ),
        propagation_direction=(
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        transverse_wavevector=None,
    )

    assert envelope.shape == (2, 1, 3, 5)
    assert envelope.dtype == torch.complex64
    assert envelope.device.type == "meta"


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is unavailable",
)
def test_plane_wave_envelope_matches_cpu_on_cuda() -> None:
    """
    同一私有数值核在 CPU 与可用 CUDA 设备上保持一致
    """

    wavelengths = torch.tensor((0.5, 0.8), dtype=torch.float32)
    refractive_indices = torch.tensor((1.0, 1.4), dtype=torch.float32)
    polarization = torch.tensor(
        (1.0 + 0.0j, 0.0 + 1.0j),
        dtype=torch.complex64,
    )
    direction = (
        torch.tensor(0.15, dtype=torch.float32),
        torch.tensor(-0.05, dtype=torch.float32),
    )
    cpu = plane_wave_envelope(
        sample_counts=(4, 3),
        signed_spacing=_scalar_pair(0.2, -0.3, dtype=torch.float32),
        first_sample_position=_scalar_pair(-0.3, 0.3, dtype=torch.float32),
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        polarization_state=polarization,
        propagation_direction=direction,
        transverse_wavevector=None,
    )
    cuda = plane_wave_envelope(
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
        refractive_indices=refractive_indices.cuda(),
        polarization_state=polarization.cuda(),
        propagation_direction=(
            direction[0].cuda(),
            direction[1].cuda(),
        ),
        transverse_wavevector=None,
    )

    assert torch.allclose(cpu, cuda.cpu(), atol=2e-6, rtol=2e-6)


@pytest.mark.parametrize(
    ("dtype", "tolerance"),
    [
        (torch.float32, 2e-6),
        (torch.float64, 1e-12),
    ],
)
def test_power_normalized_amplitude_matches_analytic_reference(
    dtype: torch.dtype,
    tolerance: float,
) -> None:
    """
    对照总功率归一化解析值
    """

    total_power = torch.tensor(6.0, dtype=dtype)
    weights = torch.tensor((0.25, 0.75), dtype=dtype)

    amplitude = power_normalized_amplitude(
        total_power=total_power,
        spectral_weights=weights,
        sample_counts=(2, 3),
        cell_area=torch.tensor(0.5, dtype=dtype),
    )
    expected = math.sqrt(2.0)

    assert amplitude.dtype is dtype
    assert math.isclose(
        float(amplitude.item()),
        expected,
        rel_tol=tolerance,
        abs_tol=tolerance,
    )


def test_power_normalized_amplitude_preserves_total_power_gradient() -> None:
    """
    保留总功率归一化梯度
    """

    total_power = torch.tensor(
        2.0,
        dtype=torch.float64,
        requires_grad=True,
    )
    weights = torch.tensor((0.4, 0.6), dtype=torch.float64)

    def _amplitude(power: torch.Tensor) -> torch.Tensor:
        return power_normalized_amplitude(
            total_power=power,
            spectral_weights=weights,
            sample_counts=(2, 2),
            cell_area=torch.tensor(0.25, dtype=torch.float64),
        )

    assert torch.autograd.gradcheck(
        _amplitude,
        (total_power,),
        eps=1e-7,
        atol=1e-5,
        rtol=1e-3,
    )


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is unavailable",
)
def test_power_normalized_amplitude_matches_cpu_on_cuda() -> None:
    """
    对齐 CPU 与 CUDA 总功率归一化
    """

    total_power = torch.tensor(2.0, dtype=torch.float32)
    weights = torch.tensor((0.4, 0.6), dtype=torch.float32)
    cpu = power_normalized_amplitude(
        total_power=total_power,
        spectral_weights=weights,
        sample_counts=(8, 4),
        cell_area=torch.tensor(0.125, dtype=torch.float32),
    )
    cuda = power_normalized_amplitude(
        total_power=total_power.cuda(),
        spectral_weights=weights.cuda(),
        sample_counts=(8, 4),
        cell_area=torch.tensor(0.125, dtype=torch.float32, device="cuda"),
    )

    assert torch.allclose(cpu, cuda.cpu(), atol=2e-6, rtol=2e-6)




def _direction_envelope(
    *,
    direction_y: float,
    direction_x: float,
    spacing_y: float,
    spacing_x: float,
    wavelengths: tuple[float, ...],
    refractive_indices: tuple[float, ...],
    real_dtype: torch.dtype = _FD,
) -> torch.Tensor:
    # 传播方向路径的薄包装：方向与波长配对送入数值核
    return plane_wave_envelope(
        sample_counts=(4, 4),
        signed_spacing=_scalar_pair(spacing_y, spacing_x, dtype=real_dtype),
        first_sample_position=_scalar_pair(0.0, 0.0, dtype=real_dtype),
        wavelengths=torch.tensor(wavelengths, dtype=real_dtype),
        refractive_indices=torch.tensor(
            refractive_indices,
            dtype=real_dtype,
        ),
        polarization_state=torch.ones(1, dtype=torch.complex128),
        propagation_direction=_scalar_pair(
            direction_y,
            direction_x,
            dtype=real_dtype,
        ),
        transverse_wavevector=None,
    )


def test_strict_nyquist_rejects_exact_half_cycle_per_sample() -> None:
    """|Δcycles| = 0.5 恰等被严格拒绝（不取容差近通过的等号）

    单色真空、direction_y = 0.5、spacing_y = 1.0 m、λ = 1.0 m ⇒
    Δcycles = n·cy·Δy/λ = 1·0.5·1/1 = 0.5 恰等半周期。0.5² = 0.25 在 binary64
    精确，故 0.25 − 0.25 = 0 给出精确符号 0，整源拒绝。
    """

    with pytest.raises(ValueError, match="plane_wave_sampling_insufficient"):
        _direction_envelope(
            direction_y=0.5,
            direction_x=0.0,
            spacing_y=1.0,
            spacing_x=1.0,
            wavelengths=(1.0,),
            refractive_indices=(1.0,),
        )


def test_strict_nyquist_splits_neighbouring_binary64_around_half_cycle() -> None:
    """0.5 的下邻位 binary64 通过、上邻位 binary64 拒绝

    取 spacing_y 使 Δcycles 落在恰等、下邻位、上邻位三个 binary64 值上。
    0.5 是 2 的幂（2⁻¹），乘 0.5 只移指数故精确；下邻 spacing 给出 Δcycles 的下邻，
    上邻 spacing 给出上邻，栅栏按精确符号分裂二者。
    """

    half = 0.5
    below = math.nextafter(half, 0.0)
    above = math.nextafter(half, math.inf)
    envelope_below = _direction_envelope(
        direction_y=0.5,
        direction_x=0.0,
        spacing_y=2.0 * below,
        spacing_x=1.0,
        wavelengths=(1.0,),
        refractive_indices=(1.0,),
    )
    assert envelope_below.shape == (1, 1, 4, 4)
    # 上邻位：增量 = 0.5 × (2·above) = above > 0.5 ⇒ 拒绝
    with pytest.raises(ValueError, match="plane_wave_sampling_insufficient"):
        _direction_envelope(
            direction_y=0.5,
            direction_x=0.0,
            spacing_y=2.0 * above,
            spacing_x=1.0,
            wavelengths=(1.0,),
            refractive_indices=(1.0,),
        )


def test_strict_nyquist_rejects_three_point_six_pi_carrier() -> None:
    """每样本 3.6π 弧度（1.8 周期）的载波现在被拒绝

    若无栅栏，每样本 1.8 周期的增量经 ``_unit_phasor_from_cycles`` 折到 [-0.5, 0.5]
    后等价于 −0.2 周期，静默混叠成低频载波。严格采样栅栏以 |1.8| > 0.5 拒绝。
    """

    with pytest.raises(ValueError, match="plane_wave_sampling_insufficient"):
        _direction_envelope(
            direction_y=0.9,
            direction_x=0.0,
            spacing_y=2.0,
            spacing_x=1.0,
            wavelengths=(1.0,),
            refractive_indices=(1.0,),
        )


def test_radiative_grazing_equality_rejected_and_neighbours_split() -> None:
    """横向波矢辐射支持：掠射等号（ν_y²+ν_x² = (n/λ)²）拒绝，邻位按符号分裂

    单色真空、λ = 1 m ⇒ n/λ = 1 cycles/m。取 κ_y = 2π（即 ν_y = 1），ν_x = 0；
    (κ_y/(2π))² = 1 = (n/λ)² 给出精确符号 0（掠射，cz = 0），拒绝。κ_y 的下邻使
    ν_y 略小于 1 ⇒ 通过；上邻使 ν_y 略大于 1 ⇒ 倏逝拒绝。逐轴 Nyquist 同步通过
    （spacing = 0.25 m ⇒ |Δcycles| = 0.25 < 0.5），故失败仅由辐射支持决定。
    """

    tau = 2.0 * math.pi
    spacing = _scalar_pair(0.25, 0.25, dtype=_FD)
    wavelengths = torch.tensor((1.0,), dtype=_FD)

    def _envelope(kappa_y: float) -> torch.Tensor:
        return plane_wave_envelope(
            sample_counts=(4, 4),
            signed_spacing=spacing,
            first_sample_position=_scalar_pair(0.0, 0.0, dtype=_FD),
            wavelengths=wavelengths,
            refractive_indices=torch.tensor((1.0,), dtype=_FD),
            polarization_state=torch.ones(1, dtype=torch.complex128),
            propagation_direction=None,
            transverse_wavevector=_scalar_pair(kappa_y, 0.0, dtype=_FD),
        )

    # 掠射等号：κ_y = 2π ⇒ ν_y = 1.0 恰等 (n/λ) ⇒ 拒绝
    with pytest.raises(ValueError, match="plane_wave_sampling_insufficient"):
        _envelope(tau)
    # 下邻位：ν_y 略小于 1 ⇒ 通过
    assert _envelope(math.nextafter(tau, 0.0)).shape == (1, 1, 4, 4)
    # 上邻位：ν_y 略大于 1 ⇒ 倏逝拒绝
    with pytest.raises(ValueError, match="plane_wave_sampling_insufficient"):
        _envelope(math.nextafter(tau, math.inf))

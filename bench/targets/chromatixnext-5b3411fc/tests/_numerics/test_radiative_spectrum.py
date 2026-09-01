
from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
import math

import torch

from chromatix_next._numerics._certified_predicates import (
    scaled_squared_norm_difference_sign,
)
from chromatix_next._numerics.wave_propagation.radiative_spectrum import (
    _radiative_plane_transfer,
    _RadiativePlaneTransfer,
    _RadiativeSpectrumFacts,
)


def _pair(
    value_y: float,
    value_x: float,
    *,
    dtype: torch.dtype,
) -> tuple[torch.Tensor, torch.Tensor]:
    # 构造一对同 dtype 零维间距/位移张量
    return (
        torch.tensor(value_y, dtype=dtype),
        torch.tensor(value_x, dtype=dtype),
    )


def _build(
    *,
    n: float,
    axial_distance: float,
    sample_count: int = 8,
    spacing: float = 0.25e-6,
    wavelength: float = 1.0e-6,
) -> torch.Tensor:
    # 在固定几何下构造标量/矢量共用的平行平面传递张量（标量与矢量同支撑）
    return _radiative_plane_transfer(
        computational_counts=(sample_count, sample_count),
        signed_spacing=_pair(spacing, spacing, dtype=torch.float64),
        displacement=_pair(0.0, 0.0, dtype=torch.float64),
        axial_distance=torch.tensor(axial_distance, dtype=torch.float64),
        wavelengths=torch.tensor([wavelength], dtype=torch.float64),
        refractive_indices=torch.tensor([n], dtype=torch.float64),
        real_dtype=torch.float64,
        complex_dtype=torch.complex128,
        device=torch.device("cpu"),
    ).transfer


def _bin_frequency(bin_index: int, sample_count: int, spacing: float) -> float:
    # 返回某 FFT 频箱（含负箱）对应的 cycles/m
    signed = bin_index if bin_index <= sample_count // 2 else bin_index - sample_count
    return signed / (sample_count * spacing)


def _decimal_sign(value: Decimal) -> int:
    # decimal.Decimal 的符号到 -1/0/+1
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _analytic_transfer(
    *,
    n: float,
    axial_distance: float,
    frequency_y: float,
    frequency_x: float,
    sample_count: int,
    spacing: float,
    wavelength: float,
    displacement_y: float = 0.0,
    displacement_x: float = 0.0,
) -> complex:
    decimal_precision = 80
    with localcontext() as ctx:
        ctx.prec = decimal_precision
        n_dec = Decimal(repr(n))
        lambda_dec = Decimal(repr(wavelength))
        nu_y_dec = Decimal(repr(frequency_y))
        nu_x_dec = Decimal(repr(frequency_x))
        d_dec = Decimal(repr(axial_distance))
        dy_dec = Decimal(repr(displacement_y))
        dx_dec = Decimal(repr(displacement_x))
        spacing_dec = Decimal(repr(spacing))
        sample_count_dec = Decimal(sample_count)
        q_value = (
            n_dec * n_dec
            - (lambda_dec * lambda_dec)
            * (nu_y_dec * nu_y_dec + nu_x_dec * nu_x_dec)
        )
        if q_value <= 0:
            return 0.0j
        sqrt_q = q_value.sqrt()
        half_extent = (sample_count_dec * spacing_dec) / Decimal(2)
        admit_y = (
            dy_dec - d_dec * lambda_dec * nu_y_dec / sqrt_q
        ).copy_abs() < half_extent
        admit_x = (
            dx_dec - d_dec * lambda_dec * nu_x_dec / sqrt_q
        ).copy_abs() < half_extent
        if not (admit_y and admit_x):
            return 0.0j
    wave_number = 2.0 * math.pi * n / wavelength
    transverse_y = 2.0 * math.pi * frequency_y
    transverse_x = 2.0 * math.pi * frequency_x
    transverse_squared = (
        (transverse_y / wave_number) ** 2
        + (transverse_x / wave_number) ** 2
    )
    direction_z = math.sqrt(max(0.0, 1.0 - transverse_squared))
    longitudinal = direction_z * wave_number
    phase = (longitudinal - wave_number) * axial_distance
    phase += transverse_y * displacement_y + transverse_x * displacement_x
    return complex(math.cos(phase), math.sin(phase))


class TestRadiativeSupport:
    """
    light cone 内/上/外孤立模态的辐射支撑与传播相位证据
    """

    def test_inside_mode_propagates_with_residual_phase(self) -> None:
        """
        light cone 内的孤立模态按残差相位 (kz-k)d 传播且模长为一
        """
        sample_count = 8
        spacing = 0.25e-6
        wavelength = 1.0e-6
        n = 1.5
        # n=1.5 时边界 |f|=n/lambda=1.5e6 cycles/m；|m|=1 -> 5e5，远在 cone 内
        transfer = _build(
            n=n,
            axial_distance=0.4e-6,
            sample_count=sample_count,
            spacing=spacing,
            wavelength=wavelength,
        )
        for (bin_y, bin_x) in ((1, 0), (0, 1), (1, 1), (-1, 2)):
            index_y = bin_y % sample_count
            index_x = bin_x % sample_count
            frequency_y = _bin_frequency(bin_y, sample_count, spacing)
            frequency_x = _bin_frequency(bin_x, sample_count, spacing)
            expected = _analytic_transfer(
                n=n,
                axial_distance=0.4e-6,
                frequency_y=frequency_y,
                frequency_x=frequency_x,
                sample_count=sample_count,
                spacing=spacing,
                wavelength=wavelength,
            )
            production = transfer[0, index_y, index_x].item()
            assert abs(abs(production) - abs(expected)) < 1.0e-12
            assert abs(production - expected) < 1.0e-12

    def test_evanescent_mode_is_explicitly_removed_not_passed(self) -> None:
        """
        light cone 外的倏逝模态被 radiative-only 显式置零，而非 unchanged 传递
        """
        transfer = _build(
            n=1.5,
            axial_distance=0.3e-6,
        )
        # |m|=4 on-axis -> |f|=2.0e6 > 边界 1.5e6；倏逝，须严格为零
        for (bin_y, bin_x) in ((4, 0), (0, 4), (4, 4), (-3, 4)):
            index_y = bin_y % 8
            index_x = bin_x % 8
            assert transfer[0, index_y, index_x] == 0.0

    def test_non_vacuum_light_cone_shrinks_relative_to_vacuum(self) -> None:
        """
        非真空（n>1）的 light cone 内缩后保留模态不多于真空情形
        """
        vacuum = _build(n=1.0, axial_distance=0.0)
        medium = _build(n=1.5, axial_distance=0.0)
        vacuum_count = int(torch.count_nonzero(vacuum))
        medium_count = int(torch.count_nonzero(medium))
        assert medium_count > vacuum_count

    def test_alias_band_removes_inside_cone_mode_at_large_distance(self) -> None:
        """
        light cone 内但超出 alias 带的模态被带限移除（区分 propagation 与 alias）
        """
        sample_count = 8
        spacing = 0.25e-6
        wavelength = 1.0e-6
        n = 1.5
        large_distance = 8.0e-6
        transfer = _build(
            n=n,
            axial_distance=large_distance,
            sample_count=sample_count,
            spacing=spacing,
            wavelength=wavelength,
        )
        frequency_y = _bin_frequency(2, sample_count, spacing)
        frequency_x = _bin_frequency(0, sample_count, spacing)
        expected = _analytic_transfer(
            n=n,
            axial_distance=large_distance,
            frequency_y=frequency_y,
            frequency_x=frequency_x,
            sample_count=sample_count,
            spacing=spacing,
            wavelength=wavelength,
        )
        assert expected == 0.0j
        assert transfer[0, 2, 0] == 0.0


class TestScalarVectorShareSupport:
    """
    移除矢量专用 ``sqrt(eps)`` 掠入截断后，标量与矢量同 ``Q>0`` 分类、
    同联合二维位移支撑；下游矢量亥姆霍兹纵向除法有限性由既有物理所有者承担。
    """

    def test_scalar_and_vector_support_are_identical(self) -> None:
        """
        移除 grazing_cutoff 后标量与矢量支撑逐模态相同（同 ``Q>0`` 联合二维判据）
        """
        sample_count = 8
        spacing = 0.5e-6
        wavelength = 1.0e-6
        n = 1.0
        common = dict(
            n=n,
            axial_distance=0.0,
            sample_count=sample_count,
            spacing=spacing,
            wavelength=wavelength,
        )
        scalar = _build(**common)  # type: ignore[arg-type]
        vector = _build(**common)  # type: ignore[arg-type]
        # 标量与矢量传递在全网格上完全一致（同支撑、同传递相位）
        assert torch.equal(scalar, vector)
        assert torch.equal(scalar != 0, vector != 0)

    def test_scalar_and_vector_transfers_match_on_full_grid(self) -> None:
        """
        非真空下标量与矢量传递在全网格（含近边界）逐模态严格相等
        """
        common = dict(
            n=1.5,
            axial_distance=0.4e-6,
            sample_count=8,
            spacing=0.25e-6,
            wavelength=1.0e-6,
        )
        scalar = _build(**common)  # type: ignore[arg-type]
        vector = _build(**common)  # type: ignore[arg-type]
        assert torch.equal(scalar, vector)


class TestRadiativeSupportExcludesExactGrazing:
    """
    ``Q>0`` 严格分类把精确掠入（``Q==0``）排除在辐射支撑之外
    """

    def test_strict_q_positive_excludes_exact_cone_boundary_bins(self) -> None:
        """
        on-cone 边界箱（``|f|=n/λ`` ⇒ ``Q=0``）被严格 ``Q>0`` 分类排除
        """
        sample_count = 8
        spacing = 0.25e-6
        wavelength = 1.0e-6
        plane = _radiative_plane_transfer(
            computational_counts=(sample_count, sample_count),
            signed_spacing=_pair(spacing, spacing, dtype=torch.float64),
            displacement=_pair(0.0, 0.0, dtype=torch.float64),
            axial_distance=torch.tensor(0.0, dtype=torch.float64),
            wavelengths=torch.tensor([wavelength], dtype=torch.float64),
            refractive_indices=torch.tensor([1.5], dtype=torch.float64),
            real_dtype=torch.float64,
            complex_dtype=torch.complex128,
            device=torch.device("cpu"),
        )
        # on-cone 边界轴向箱 (3,0)/(0,3)：在严格 ``Q>0`` 分类下被排除
        for (index_y, index_x) in ((3, 0), (0, 3)):
            assert plane.transfer[0, index_y, index_x] == 0.0
        # light cone 外倏逝 (4,0)/(0,4)/(4,4) 仍严格归零
        for (index_y, index_x) in ((4, 0), (0, 4), (4, 4)):
            assert plane.transfer[0, index_y, index_x] == 0.0
        # 远边界内部模态仍非零：bin (2,0) 处 |f|=1.0e6<1.5e6，``Q>0`` 严格
        assert plane.transfer[0, 2, 0] != 0.0


class TestSignedDistance:
    """
    带符号轴向距离的 signed radiative 语义
    """

    def test_support_is_identical_for_both_distance_signs(self) -> None:
        """
        正负轴向距离的辐射支撑掩膜逐模态相同
        """
        positive = _build(n=1.5, axial_distance=0.6e-6)
        negative = _build(n=1.5, axial_distance=-0.6e-6)
        assert torch.equal(positive != 0, negative != 0)

    def test_positive_transfer_is_conjugate_of_negative_on_support(self) -> None:
        """
        支撑内 +d 传递恰为 -d 传递的复共轭（反向传播）
        """
        positive = _build(n=1.5, axial_distance=0.6e-6)
        negative = _build(n=1.5, axial_distance=-0.6e-6)
        support = positive != 0
        assert torch.allclose(
            positive[support],
            negative[support].conj(),
            atol=1.0e-12,
        )

    def test_negative_distance_does_not_recover_evanescent(self) -> None:
        """
        反向传播不声称代数恢复已移除的倏逝分量（边界外仍严格为零）
        """
        negative = _build(n=1.5, axial_distance=-0.6e-6)
        for (index_y, index_x) in ((4, 0), (0, 4), (4, 4)):
            assert negative[0, index_y, index_x] == 0.0


class TestMediumBandLimit:
    """
    band-limit 随介质波长缩放的独立解析证据
    """

    def test_alias_narrow_threshold_scales_with_medium_wavelength(self) -> None:
        """
        has_narrow_alias_band 触发距离按 n/lambda 缩放，与独立解析公式一致
        """
        sample_count = 8
        spacing = 0.25e-6
        wavelength = 1.0e-6
        window = sample_count * spacing

        def _analytic_threshold(n: float) -> float:
            # 解析：安全带窄于首个非零频率箱当 (n/lambda)/sqrt(1+(2d/L)^2) < 1/L
            return (window / 2.0) * math.sqrt(
                max(0.0, (n * window / wavelength) ** 2 - 1.0),
            )

        def _is_narrow(n: float, axial_distance: float) -> bool:
            facts = _radiative_plane_transfer(
                computational_counts=(sample_count, sample_count),
                signed_spacing=_pair(spacing, spacing, dtype=torch.float64),
                displacement=_pair(0.0, 0.0, dtype=torch.float64),
                axial_distance=torch.tensor(axial_distance, dtype=torch.float64),
                wavelengths=torch.tensor([wavelength], dtype=torch.float64),
                refractive_indices=torch.tensor([n], dtype=torch.float64),
                real_dtype=torch.float64,
                complex_dtype=torch.complex128,
                device=torch.device("cpu"),
            )
            return bool(facts.has_narrow_alias_band)

        for n in (1.0, 1.25, 1.5):
            threshold = _analytic_threshold(n)
            # 阈值下界（安全可传播）与上界（已触发带限）锁定解析公式
            assert not _is_narrow(n, 0.999 * threshold)
            assert _is_narrow(n, 1.001 * threshold)
        # 介质折射率提升使同几何可传播更远才触发带限——锁定带限用同一 n
        assert _analytic_threshold(1.5) > _analytic_threshold(1.0)


class TestJointDisplacedAliasSupport:
    """
    联合二维位移判据的掩码计数与逐箱符号证据
    """

    sample_count = 128
    spacing = 0.2e-6
    wavelength = 0.5e-6
    refractive_index = 1.0
    axial_distance = 10.0e-6

    def _support(self, dx: float, dy: float, d: float) -> torch.Tensor:
        # 指定位移与带符号轴向距离下的标准 AS 支撑掩膜
        plane = _radiative_plane_transfer(
            computational_counts=(self.sample_count, self.sample_count),
            signed_spacing=_pair(self.spacing, self.spacing, dtype=torch.float64),
            displacement=_pair(dy, dx, dtype=torch.float64),
            axial_distance=torch.tensor(d, dtype=torch.float64),
            wavelengths=torch.tensor([self.wavelength], dtype=torch.float64),
            refractive_indices=torch.tensor(
                [self.refractive_index],
                dtype=torch.float64,
            ),
            real_dtype=torch.float64,
            complex_dtype=torch.complex128,
            device=torch.device("cpu"),
        )
        return plane.support

    def test_support_count_matches_joint_reference_at_dx_zero(self) -> None:
        """
        dx=0 时联合判据支撑计数为 5533（逐轴矩形判据接纳 6409）
        """
        d = self.axial_distance
        assert int(self._support(0.0, 0.0, d).sum()) == 5533

    def test_support_count_drops_under_transverse_displacement(self) -> None:
        """
        |dx|=3µm 时支撑降至 5413（逐轴矩形判据不响应联合位移）
        """
        d = self.axial_distance
        assert int(self._support(3.0e-6, 0.0, d).sum()) == 5413
        assert int(self._support(-3.0e-6, 0.0, d).sum()) == 5413

    def test_displacement_sign_changes_set_not_count(self) -> None:
        """
        +dx 与 −dx 准入不同频箱集合但计数相同（位移符号物理上有意义）
        """
        d = self.axial_distance
        positive = self._support(3.0e-6, 0.0, d)
        negative = self._support(-3.0e-6, 0.0, d)
        assert int(positive.sum()) == int(negative.sum())
        assert not torch.equal(positive, negative)

    def test_distance_sign_leaves_support_unchanged(self) -> None:
        """
        +d 与 −d 的支撑逐模态相同（判据对轴向距离偶；反向仅取共轭相位）
        """
        d = self.axial_distance
        assert torch.equal(
            self._support(0.0, 0.0, d),
            self._support(0.0, 0.0, -d),
        )

    def test_transfer_phase_derivative_sign_matches_displacement(self) -> None:
        """
        逐箱传递相位导数 dphi/dkx = dx − d·kx/kz，符号为 +dx（无翻转）
        """
        n = self.refractive_index
        wave_number = 2.0 * math.pi * n / self.wavelength
        frequency = (
            torch.fft.fftfreq(self.sample_count, d=1.0, dtype=torch.float64)
            / self.spacing
        )
        iy = 0
        center = 1
        kx_p = 2.0 * math.pi * frequency[center + 1]
        kx_m = 2.0 * math.pi * frequency[center - 1]
        kx = 2.0 * math.pi * frequency[center]
        ky = 2.0 * math.pi * frequency[iy]
        kz = math.sqrt(max(0.0, wave_number**2 - ky**2 - kx**2))
        d = self.axial_distance
        ip = center + 1
        im = center - 1

        def _phase_slope(dx: float) -> float:
            # 对实际传递张量的相位做中心差分，返回 dphi/dkx 的数值估计
            transfer = _radiative_plane_transfer(
                computational_counts=(self.sample_count, self.sample_count),
                signed_spacing=_pair(self.spacing, self.spacing, dtype=torch.float64),
                displacement=_pair(0.0, dx, dtype=torch.float64),
                axial_distance=torch.tensor(d, dtype=torch.float64),
                wavelengths=torch.tensor([self.wavelength], dtype=torch.float64),
                refractive_indices=torch.tensor([n], dtype=torch.float64),
                real_dtype=torch.float64,
                complex_dtype=torch.complex128,
                device=torch.device("cpu"),
            ).transfer
            head = transfer[0, iy, ip].item()
            tail = transfer[0, iy, im].item()
            return (
                math.atan2(head.imag, head.real)
                - math.atan2(tail.imag, tail.real)
            ) / (kx_p - kx_m)

        for dx in (3.0e-6, -3.0e-6):
            finite = _phase_slope(dx)
            analytic = dx - d * kx / kz
            assert abs(finite - analytic) < 1.0e-7
            assert math.copysign(1.0, finite) == math.copysign(1.0, dx)

    def test_full_grid_analytic_mask_is_displacement_aware_and_matches_production(
        self,
    ) -> None:
        """
        _analytic_transfer 逐箱独立重建全网格掩码（位移感知）并与生产支撑逐模态一致
        """
        n = self.refractive_index
        wl = self.wavelength
        sp = self.spacing
        N = self.sample_count
        d = self.axial_distance
        fy = torch.fft.fftfreq(N, d=1.0, dtype=torch.float64) / sp
        fx = torch.fft.fftfreq(N, d=1.0, dtype=torch.float64) / sp
        anchors = {0.0: 5533, 3.0e-6: 5413, -3.0e-6: 5413}
        for dx, anchor in anchors.items():
            production = self._support(dx, 0.0, d)
            independent = torch.zeros((N, N), dtype=torch.bool)
            for iy in range(N):
                for ix in range(N):
                    value = _analytic_transfer(
                        n=n,
                        axial_distance=d,
                        frequency_y=fy[iy].item(),
                        frequency_x=fx[ix].item(),
                        sample_count=N,
                        spacing=sp,
                        wavelength=wl,
                        displacement_x=dx,
                    )
                    independent[iy, ix] = value != 0.0j
            assert int(independent.sum()) == anchor
            assert torch.equal(independent, production[0])

    def test_nonzero_displacement_phase_matches_analytic_transfer(self) -> None:
        """
        非零位移下逐箱传递相位与 _analytic_transfer 一致（位移相位项 + 准入）
        """
        n = self.refractive_index
        wl = self.wavelength
        sp = self.spacing
        N = self.sample_count
        d = self.axial_distance
        fy = torch.fft.fftfreq(N, d=1.0, dtype=torch.float64) / sp
        fx = torch.fft.fftfreq(N, d=1.0, dtype=torch.float64) / sp
        iy, ix = 0, 1
        positive = _analytic_transfer(
            n=n,
            axial_distance=d,
            frequency_y=fy[iy].item(),
            frequency_x=fx[ix].item(),
            sample_count=N,
            spacing=sp,
            wavelength=wl,
            displacement_x=3.0e-6,
        )
        negative = _analytic_transfer(
            n=n,
            axial_distance=d,
            frequency_y=fy[iy].item(),
            frequency_x=fx[ix].item(),
            sample_count=N,
            spacing=sp,
            wavelength=wl,
            displacement_x=-3.0e-6,
        )
        # +dx 与 −dx 在同一箱给出不同相位（位移相位项生效）
        assert abs(positive - negative) > 1.0e-9
        for dx, expected in ((3.0e-6, positive), (-3.0e-6, negative)):
            plane = _radiative_plane_transfer(
                computational_counts=(N, N),
                signed_spacing=_pair(sp, sp, dtype=torch.float64),
                displacement=_pair(0.0, dx, dtype=torch.float64),
                axial_distance=torch.tensor(d, dtype=torch.float64),
                wavelengths=torch.tensor([wl], dtype=torch.float64),
                refractive_indices=torch.tensor([n], dtype=torch.float64),
                real_dtype=torch.float64,
                complex_dtype=torch.complex128,
                device=torch.device("cpu"),
            )
            production = plane.transfer[0, iy, ix].item()
            assert abs(production - expected) < 1.0e-12


class TestJointSupportCertifiedSignEvidence:
    """
    联合二维位移支撑的多项式精确符号证据。覆盖高精度有限差分（两轴）、
    严格等号与相邻浮点的支撑判定、对抗性 ``round(sqrt(Q))`` 反转、轴交换/共轭/形变
    对称、多色/色散情形，以及保留的 6,409 过收矩形反例。
    """

    sample_count = 128
    spacing = 0.2e-6
    wavelength = 0.5e-6
    refractive_index = 1.0
    axial_distance = 10.0e-6

    def _plane(
        self,
        *,
        dx: float = 0.0,
        dy: float = 0.0,
        d: float | None = None,
        n: float | None = None,
        wavelengths: tuple[float, ...] | None = None,
        refractive_indices: tuple[float, ...] | None = None,
    ) -> _RadiativePlaneTransfer:
        if d is None:
            d = self.axial_distance
        if wavelengths is None:
            wavelengths = (self.wavelength,)
        if refractive_indices is None:
            refractive_indices = tuple(
                self.refractive_index for _ in wavelengths
            )
        if n is not None:
            refractive_indices = (n,)
        return _radiative_plane_transfer(
            computational_counts=(self.sample_count, self.sample_count),
            signed_spacing=_pair(self.spacing, self.spacing, dtype=torch.float64),
            displacement=_pair(dy, dx, dtype=torch.float64),
            axial_distance=torch.tensor(d, dtype=torch.float64),
            wavelengths=torch.tensor(wavelengths, dtype=torch.float64),
            refractive_indices=torch.tensor(refractive_indices, dtype=torch.float64),
            real_dtype=torch.float64,
            complex_dtype=torch.complex128,
            device=torch.device("cpu"),
        )

    def test_high_precision_finite_difference_of_frozen_transfer_cycles_both_axes(
        self,
    ) -> None:
        """
        冻结 Fourier 传递相位 ``C`` 的逐箱中心差分对 ``nu_y``、``nu_x`` 都匹配解析
        导数 ``displacement_a - d·lambda·nu_a/sqrt(Q)``
        """
        n = self.refractive_index
        lam = self.wavelength
        sp = self.spacing
        N = self.sample_count
        d = self.axial_distance
        dx = 3.0e-6
        dy = -2.0e-6
        plane = self._plane(dx=dx, dy=dy)
        fy = (
            torch.fft.fftfreq(N, d=1.0, dtype=torch.float64) / sp
        )
        fx = (
            torch.fft.fftfreq(N, d=1.0, dtype=torch.float64) / sp
        )
        # 选一个内部、远离边界的箱做有限差分：bin (4, 5)
        iy, ix = 4, 5
        # 解析导数（高精度 oracle，不复刻生产路径）
        with localcontext() as ctx:
            ctx.prec = 60
            nu_y = Decimal(repr(fy[iy].item()))
            nu_x = Decimal(repr(fx[ix].item()))
            n_dec = Decimal(repr(n))
            lam_dec = Decimal(repr(lam))
            d_dec = Decimal(repr(d))
            dx_dec = Decimal(repr(dx))
            dy_dec = Decimal(repr(dy))
            q_dec = n_dec * n_dec - lam_dec * lam_dec * (
                nu_y * nu_y + nu_x * nu_x
            )
            sqrt_q = q_dec.sqrt()
            analytic_x = float(dx_dec - d_dec * lam_dec * nu_x / sqrt_q)
            analytic_y = float(dy_dec - d_dec * lam_dec * nu_y / sqrt_q)

        def _phase_at(iy_off: int, ix_off: int) -> float:
            transfer = plane.transfer[0, iy + iy_off, ix + ix_off].item()
            return math.atan2(transfer.imag, transfer.real)

        delta_cycles = 1.0 / (N * sp)
        finite_x = (
            _phase_at(0, +1) - _phase_at(0, -1)
        ) / (2 * delta_cycles * 2 * math.pi)
        finite_y = (
            _phase_at(+1, 0) - _phase_at(-1, 0)
        ) / (2 * delta_cycles * 2 * math.pi)
        assert abs(finite_x - analytic_x) < 1.0e-6
        assert abs(finite_y - analytic_y) < 1.0e-6

    def test_strict_equality_excludes_boundary_and_neighbour_admits(self) -> None:
        """
        严格 ``<``：恰等边界的频箱被排除；两个相邻可表示浮点位移给出可控的支撑翻转
        """
        N = self.sample_count
        sp = self.spacing
        lam = self.wavelength
        n = self.refractive_index
        nu_x = 1.0 / (N * sp)
        with localcontext() as ctx:
            ctx.prec = 60
            n_dec = Decimal(repr(n)) ** 2
            lam_dec = Decimal(repr(lam)) ** 2
            nu_dec = Decimal(repr(nu_x)) ** 2
            q_dec = n_dec - lam_dec * nu_dec
            sqrt_q = q_dec.sqrt()
            d_exact_dec = (
                (Decimal(N) * Decimal(repr(sp)) / Decimal(2))
                * sqrt_q
                / (Decimal(repr(lam)) * Decimal(repr(nu_x)))
            )
        d_exact = float(d_exact_dec)
        # 在恰边界 ``d`` 下，箱 (0,1) 必须排除（严格 ``<``）
        plane_boundary = self._plane(d=d_exact)
        assert not bool(plane_boundary.support[0, 0, 1])
        # 邻近浮点 ``d``（小 1 ULP）：``|X|`` 减小，使 ``|X|<L/2·sqrt(Q)`` 成立 → 准入
        d_smaller = math.nextafter(d_exact, -math.inf)
        plane_smaller = self._plane(d=d_smaller)
        assert bool(plane_smaller.support[0, 0, 1])
        # 邻近浮点 ``d``（大 1 ULP）：``|X|`` 增大，使严格不等失败 → 排除
        d_larger = math.nextafter(d_exact, +math.inf)
        plane_larger = self._plane(d=d_larger)
        assert not bool(plane_larger.support[0, 0, 1])

    def test_adversarial_rounded_sqrt_q_does_not_reverse_decision(self) -> None:
        """
        对抗性：``X²-A²Q`` 多项式精确符号在精确等号处返回 0（严格 ``<`` 排除），在两个
        相邻可表示浮点上返回 ±1；多项式路径不引入 ``round(sqrt(Q))`` 的额外舍入
        """
        from chromatix_next._numerics._certified_predicates import (
            squared_reference_minus_squared_factor_extra_factor_sign,
        )

        # 精确等号：A=3, Q=4, X=6 → X²-A²Q = 36-36 = 0
        a = torch.tensor(3.0, dtype=torch.float64)
        q = torch.tensor(4.0, dtype=torch.float64)
        x_exact = torch.tensor(6.0, dtype=torch.float64)
        sign_exact = int(
            squared_reference_minus_squared_factor_extra_factor_sign(
                reference=x_exact,
                squared_factor=a,
                extra_factor=q,
            ).item()
        )
        assert sign_exact == 0
        assert not (a.item() * math.sqrt(q.item()) < x_exact.item())

        x_plus = torch.tensor(
            math.nextafter(x_exact.item(), math.inf),
            dtype=torch.float64,
        )
        x_minus = torch.tensor(
            math.nextafter(x_exact.item(), -math.inf),
            dtype=torch.float64,
        )
        sign_plus = int(
            squared_reference_minus_squared_factor_extra_factor_sign(
                reference=x_plus,
                squared_factor=a,
                extra_factor=q,
            ).item()
        )
        sign_minus = int(
            squared_reference_minus_squared_factor_extra_factor_sign(
                reference=x_minus,
                squared_factor=a,
                extra_factor=q,
            ).item()
        )
        assert sign_plus == 1
        assert sign_minus == -1
        sqrt_q_float = math.sqrt(q.item())
        assert a.item() * sqrt_q_float < x_plus.item()
        assert not (a.item() * sqrt_q_float < x_minus.item())

        a_big = torch.tensor(1.0e-6, dtype=torch.float64)
        q_big = torch.tensor(4.0e12, dtype=torch.float64)
        x_big = torch.tensor(1.0, dtype=torch.float64)
        sign_big = int(
            squared_reference_minus_squared_factor_extra_factor_sign(
                reference=x_big,
                squared_factor=a_big,
                extra_factor=q_big,
            ).item()
        )
        assert sign_big == -1

    def test_axis_swap_invariance(self) -> None:
        """
        轴交换（``(dx,dy)→(dy,dx)``）下支撑计数与逐模态转置一致（计算网格为方形）
        """
        d = self.axial_distance
        plane_xy = self._plane(dx=3.0e-6, dy=-2.0e-6, d=d)
        plane_yx = self._plane(dx=-2.0e-6, dy=3.0e-6, d=d)
        # 转置支撑掩膜后逐模态相等（轴交换等价于计算网格的 ij 转置）
        assert torch.equal(
            plane_xy.support[0],
            plane_yx.support[0].t(),
        )

    def test_distance_sign_invariance_at_zero_displacement(self) -> None:
        """
        ``±d`` 在零位移下给出相同支撑（判据对 ``d`` 偶仅在 ``displacement=0`` 时成立）
        """
        d = self.axial_distance
        plane_pos = self._plane(dx=0.0, dy=0.0, d=d)
        plane_neg = self._plane(dx=0.0, dy=0.0, d=-d)
        assert torch.equal(plane_pos.support, plane_neg.support)

    def test_polychromatic_and_dispersive_share_per_spectrum_classification(
        self,
    ) -> None:
        """
        多色与色散：每光谱独立 ``Q>0`` 分类；逐光谱支撑与对应单色几何一致
        """
        wavelengths = (0.4e-6, 0.5e-6, 0.6e-6)
        refractive_indices = (1.0, 1.2, 1.5)  # 色散
        multi = self._plane(
            wavelengths=wavelengths,
            refractive_indices=refractive_indices,
        )
        for spectrum_index, (wl, n) in enumerate(
            zip(wavelengths, refractive_indices)
        ):
            single = self._plane(wavelengths=(wl,), refractive_indices=(n,))
            assert torch.equal(
                multi.support[spectrum_index],
                single.support[0],
            )

    def test_rectangular_support_over_admits_relative_to_joint_support(self) -> None:
        """
        比较 6,409 个逐轴矩形接纳箱与 5,533/5,413 个联合二维支撑箱：内接矩形并集必然
        过收（其计数大于联合二维判据），联合判据是它的真子集
        """
        n = self.refractive_index
        lam = self.wavelength
        sp = self.spacing
        N = self.sample_count
        fy = (
            torch.fft.fftfreq(N, d=1.0, dtype=torch.float64) / sp
        )
        fx = (
            torch.fft.fftfreq(N, d=1.0, dtype=torch.float64) / sp
        )
        # 独立轴并集（内接矩形）：两轴 ``|nu_a| < n/lambda`` 的 AND
        rectangular_mask = torch.zeros((N, N), dtype=torch.bool)
        for iy in range(N):
            for ix in range(N):
                if abs(fy[iy].item()) < n / lam and abs(fx[ix].item()) < n / lam:
                    rectangular_mask[iy, ix] = True
        rectangular_count = int(rectangular_mask.sum())
        production = self._plane()
        joint_count = int(production.support.sum())
        assert joint_count == 5533
        assert joint_count < rectangular_count
        assert bool((production.support[0] <= rectangular_mask).all())
        # |dx|=3µm 锚点：联合判据降至 5,413（位移判据收紧）
        assert int(self._plane(dx=3.0e-6).support.sum()) == 5413
        assert int(self._plane(dx=-3.0e-6).support.sum()) == 5413


class TestCertifiedRadiativeSupportAtGrazingRounding:
    """
    grazing 舍入边界反例：``fl(k²) − fl(k_t²) = 0`` 而精确 ``k² − k_t² > 0``
    的有限 binary64 频箱。radiative support 委托 certified 精确符号（与
    shifted-support 同一标准），连续路径携带保守占位并保持有限。
    """

    # 反例常数来自 nextafter 邻域搜索且仅在双分量 bin 上成立
    _CASES = (
        # (sample_count, spacing, wavelength, n, bin_y, bin_x)
        (8, 2.4999999999997924e-07, 9.48683298050435e-07, 1.5, 3, 1),
        (16, 1.9999999999998954e-07, 6.585545669471995e-07, 1.2, 5, 3),
    )

    def _plane(
        self,
        sample_count: int,
        spacing: float,
        wavelength: float,
        n: float,
    ) -> _RadiativePlaneTransfer:
        # 以反例几何构造平行平面辐射传递事实（位移为零、固定正轴向距离）
        return _radiative_plane_transfer(
            computational_counts=(sample_count, sample_count),
            signed_spacing=_pair(spacing, spacing, dtype=torch.float64),
            displacement=_pair(0.0, 0.0, dtype=torch.float64),
            axial_distance=torch.tensor(0.4e-6, dtype=torch.float64),
            wavelengths=torch.tensor([wavelength], dtype=torch.float64),
            refractive_indices=torch.tensor([n], dtype=torch.float64),
            real_dtype=torch.float64,
            complex_dtype=torch.complex128,
            device=torch.device("cpu"),
        )

    def _rounded_longitudinal_squared(
        self,
        facts: _RadiativeSpectrumFacts,
        index_y: int,
        index_x: int,
    ) -> float:
        # 以模块同一操作顺序复算已舍入的 k²−k_t²
        rounded = facts.wave_number.square() + -(
            facts.transverse_wavevector_y.square()
            + facts.transverse_wavevector_x.square()
        )
        return float(rounded[0, index_y, index_x].item())

    def test_rounded_zero_exact_positive_bin_is_radiative(self) -> None:
        """
        精确为正而普通舍入差为 0 的频箱按 certified 符号判为传播模态
        """
        sample_count, spacing, wavelength, n, index_y, index_x = self._CASES[0]
        plane = self._plane(sample_count, spacing, wavelength, n)
        facts = plane.facts
        # 独立 Fraction oracle：精确 k² − k_y² − k_x² > 0（反例在浮点输入上成立）
        exact = (
            Fraction(facts.wave_number[0, 0, 0].item()) ** 2
            - Fraction(facts.transverse_wavevector_y[0, index_y, index_x].item()) ** 2
            - Fraction(facts.transverse_wavevector_x[0, index_y, index_x].item()) ** 2
        )
        assert exact > 0
        # 模块算术的普通舍入差恰为 0：普通浮点比较必然丢失该传播模态
        assert self._rounded_longitudinal_squared(facts, index_y, index_x) == 0.0
        # certified 家族成员在模块原始操作数上给出精确 +1
        certified = scaled_squared_norm_difference_sign(
            reference=facts.wave_number,
            vector=torch.stack(
                (
                    facts.transverse_wavevector_y,
                    facts.transverse_wavevector_x,
                ),
                dim=-1,
            ),
        )
        assert int(certified[0, index_y, index_x].item()) == 1
        # radiative support 与 shifted-support 统一标准：同一事实一种判定
        assert bool(facts.radiative_support[0, index_y, index_x])

    def test_all_rounding_boundary_cases_match_certified_classification(
        self,
    ) -> None:
        """
        全部反例几何的 radiative 事实与 certified 符号逐箱一致
        """
        for case in self._CASES:
            sample_count, spacing, wavelength, n, index_y, index_x = case
            plane = self._plane(sample_count, spacing, wavelength, n)
            certified = scaled_squared_norm_difference_sign(
                reference=plane.facts.wave_number,
                vector=torch.stack(
                    (
                        plane.facts.transverse_wavevector_y,
                        plane.facts.transverse_wavevector_x,
                    ),
                    dim=-1,
                ),
            )
            assert int(certified[0, index_y, index_x].item()) == 1
            assert bool(plane.facts.radiative_support[0, index_y, index_x])

    def test_degenerate_continuous_outputs_carry_placeholder_and_stay_finite(
        self,
    ) -> None:
        """
        exact-positive-but-rounded-0 通道的连续纵向波数携带保守 0 占位，
        全部连续输出有限、无 NaN；shifted-support 以已舍入 0 为操作数时
        保守排除该箱，组合 support 不翻转
        """
        for case in self._CASES:
            sample_count, spacing, wavelength, n, index_y, index_x = case
            plane = self._plane(sample_count, spacing, wavelength, n)
            facts = plane.facts
            assert facts.longitudinal_wave_number[0, index_y, index_x] == 0.0
            assert bool(torch.isfinite(facts.longitudinal_wave_number).all())
            assert bool(torch.isfinite(facts.axial_cycles).all())
            assert bool(torch.isfinite(facts.shift_cycles).all())
            assert bool(torch.isfinite(plane.transfer.real).all())
            assert bool(torch.isfinite(plane.transfer.imag).all())
            assert not bool(plane.support[0, index_y, index_x])
            assert plane.transfer[0, index_y, index_x] == 0.0


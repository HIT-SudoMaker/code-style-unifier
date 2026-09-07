
from __future__ import annotations

import torch

from chromatix_next._numerics.intensity import spectral_intensity_reduction


class TestSpectralIntensityReduction:
    """
    参考核的物理不变量与独立参照
    """

    def test_kernel_produces_real_spatial_tensor(self) -> None:
        """
        核输出为实数张量且保留批量与空间轴
        """
        envelope = torch.randn((2, 3, 1, 4, 5), dtype=torch.complex128)
        weights = torch.tensor([0.2, 0.5, 0.3], dtype=torch.float64)
        intensity = spectral_intensity_reduction(envelope, weights)
        assert not torch.is_complex(intensity)
        assert intensity.shape == (2, 4, 5)

    def test_kernel_is_nonnegative(self) -> None:
        """
        核输出处处非负
        """
        envelope = torch.randn((1, 2, 2, 4, 4), dtype=torch.complex128)
        weights = torch.tensor([0.5, 0.5], dtype=torch.float64)
        intensity = spectral_intensity_reduction(envelope, weights)
        assert torch.all(intensity >= 0)

    def test_kernel_matches_independent_reference(self) -> None:
        """核结果须与独立计算的偏振求和、光谱加权模方一致

        独立参照使用 (envelope * envelope.conj()).real 求模方、显式偏振求和、
        与 reshape 广播加权，与核的负索引路径不同，以交叉验证约减顺序与广播。
        """
        torch.manual_seed(7)
        envelope = torch.randn((2, 3, 2, 4, 5), dtype=torch.complex128)
        weights = torch.tensor([0.2, 0.5, 0.3], dtype=torch.float64)

        kernel_result = spectral_intensity_reduction(envelope, weights)

        squared = (envelope * envelope.conj()).real
        pol_reduced = squared.sum(dim=-3)
        weight_view = weights.reshape(1, -1, 1, 1)
        spectral_weighted = (pol_reduced * weight_view).sum(dim=1)
        assert torch.allclose(kernel_result, spectral_weighted)

    def test_kernel_sums_polarization_then_weights_spectrum(self) -> None:
        """
        核先消去偏振轴、再用光谱权重加权求和
        """
        envelope = torch.randn((1, 2, 3, 2, 2), dtype=torch.complex128)
        weights = torch.tensor([1.0, 0.0], dtype=torch.float64)
        intensity = spectral_intensity_reduction(envelope, weights)
        # 权重 [1, 0] 令结果仅来自第一光谱分量的偏振求和
        expected = (envelope[:, 0] * envelope[:, 0].conj()).real.sum(dim=-3)
        assert torch.allclose(intensity, expected)

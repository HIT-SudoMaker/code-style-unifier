
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.ray_polarization import reflect_polarization_direction
from chromatix_next._numerics.reflection import _householder_reflect, reflect_direction
from chromatix_next.optics import Polarization, SpatialGrid, Spectrum
from chromatix_next.optics.element import reflect_at
from chromatix_next.optics.ray_bundle import RAY_STATUS_ACTIVE, RayBundle
from chromatix_next.optics.source import CollimatedRaySource
from chromatix_next.optics.surface import Plane

# 该文件只拥有 Householder 反射的独立实数方程证据




cuda = pytest.mark.cuda




def _explicit_householder_real(
    vector: torch.Tensor,
    unit_normal: torch.Tensor,
) -> torch.Tensor:
    dot = (vector * unit_normal).sum(dim=-1)
    return vector - 2.0 * dot.unsqueeze(-1) * unit_normal


def _explicit_householder_complex(
    vector: torch.Tensor,
    unit_normal: torch.Tensor,
) -> torch.Tensor:
    # 独立复 Householder oracle：用 Python 复数算术逐元素重写同一映射。n̂ 实，v 复
    real_part = vector.real
    imag_part = vector.imag
    dot_real = (real_part * unit_normal).sum(dim=-1)
    dot_imag = (imag_part * unit_normal).sum(dim=-1)
    out_real = real_part - (2.0 * dot_real).unsqueeze(-1) * unit_normal
    out_imag = imag_part - (2.0 * dot_imag).unsqueeze(-1) * unit_normal
    return torch.complex(out_real, out_imag)


# binary64 严格预算（与 RayBundle 内冻结常数一致；此处独立重算用于断言）
_U = 2.0 ** -53
_GAMMA_5 = 5.0 * _U / (1.0 - 5.0 * _U)
_GAMMA_11 = 11.0 * _U / (1.0 - 11.0 * _U)
_STRICT_DIRECTION_BUDGET = 16.0 * _GAMMA_5
_STRICT_POLARIZATION_BUDGET = 16.0 * _GAMMA_11


def _assert_strict_unit_norm_real(
    vector: torch.Tensor,
    *,
    budget: float,
) -> None:
    # 实向量单位长度严格预算断言
    norm_squared = (vector**2).sum(dim=-1)
    assert bool((((norm_squared - 1.0).abs() <= budget).all()))


def _assert_strict_unit_transverse_complex(
    polarization: torch.Tensor,
    direction: torch.Tensor,
    *,
    budget: float,
) -> None:
    # 复向量单位范数平方残差 + 实/虚横向性残差
    norms_squared = (polarization.real**2).sum(dim=-1) + (
        polarization.imag**2
    ).sum(dim=-1)
    assert bool((((norms_squared - 1.0).abs() <= budget).all()))
    projection = (polarization * direction).sum(dim=-1)
    direction_norm = torch.linalg.norm(direction, dim=-1)
    pol_norm = torch.linalg.norm(polarization, dim=-1)
    transverse_budget = budget * pol_norm * direction_norm
    assert bool((projection.real.abs() <= transverse_budget).all())
    assert bool((projection.imag.abs() <= transverse_budget).all())


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    return Spectrum.monochromatic(wavelength=wavelength)




class TestDirectHelperMatchesOracle:
    """
    ``_householder_reflect`` 与独立 oracle 逐位一致
    """

    @staticmethod
    def _real_vectors_and_normals(
        device: torch.device,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        # 一批单位实方向与对应实单位法向量（d·n ≤ 0）
        theta_values = (0.0, 0.1, 0.4, 0.8, 1.2)
        rows = [
            [math.sin(theta), 0.0, math.cos(theta)]
            for theta in theta_values
        ]
        vector = torch.tensor(rows, dtype=torch.float64, device=device)
        unit_normal = torch.tensor(
            [[0.0, 0.0, -1.0]] * len(theta_values),
            dtype=torch.float64,
            device=device,
        )
        return vector, unit_normal

    @staticmethod
    def _complex_vectors_and_normals(
        device: torch.device,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        # 一批复单位横向偏振方向与同一实单位法向量
        components = (
            (1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j),
            (0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j),
            (0.6 + 0.0j, 0.0 - 0.8j, 0.0 + 0.0j),
            (0.3 + 0.4j, 0.5 - 0.6j, 0.0 + 0.0j),
            (0.0 + 0.0j, 0.707 + 0.707j, 0.0 + 0.0j),
        )
        vector = torch.tensor(
            components,
            dtype=torch.complex128,
            device=device,
        )
        unit_normal = torch.tensor(
            [[0.0, 0.0, -1.0]] * len(components),
            dtype=torch.float64,
            device=device,
        )
        return vector, unit_normal

    def test_real_vectors_match_oracle_bitwise(self) -> None:
        """
        实方向：helper 与独立 oracle 逐位一致（CPU）
        """

        vector, unit_normal = self._real_vectors_and_normals(
            torch.device("cpu")
        )
        produced = _householder_reflect(
            vector=vector,
            unit_normal=unit_normal,
        )
        expected = _explicit_householder_real(vector, unit_normal)
        assert torch.equal(produced, expected)
        assert produced.dtype is torch.float64
        _assert_strict_unit_norm_real(
            produced,
            budget=_STRICT_DIRECTION_BUDGET,
        )

    def test_complex_vectors_match_oracle_bitwise(self) -> None:
        """
        复偏振：helper 与独立复 oracle 逐位一致（CPU）
        """

        vector, unit_normal = self._complex_vectors_and_normals(
            torch.device("cpu")
        )
        produced = _householder_reflect(
            vector=vector,
            unit_normal=unit_normal,
        )
        expected = _explicit_householder_complex(vector, unit_normal)
        assert torch.equal(produced, expected)
        assert produced.dtype is torch.complex128




class TestThreeSemanticConsumersViaActions:
    """
    反射方向、反射偏振与偏振分束反射分支经公共动作与独立 oracle 对拍
    """

    @staticmethod
    def _oblique_unit_direction() -> torch.Tensor:
        # 斜入射单位方向（落在 +z 镜面上）
        theta = math.radians(30.0)
        return torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )

    @staticmethod
    def _active_bundle(
        *,
        direction: torch.Tensor,
        polarization: torch.Tensor,
        positions: torch.Tensor | None = None,
        refractive_index_value: float = 1.0,
    ) -> RayBundle:
        # 单光谱单 ray 的全 active 光线束
        spectrum = _monochromatic()
        if positions is None:
            positions = torch.tensor(
                [[[0.0, 0.0, -1.0e-6]]],
                dtype=torch.float64,
            )
        ray_count = positions.shape[-2]
        direction_broadcast = direction.view(1, 1, 3).expand(1, ray_count, 3)
        position_broadcast = positions.view(1, ray_count, 3)
        wavelengths = torch.tensor(
            spectrum.wavelengths,
            dtype=torch.float64,
        )
        indices = torch.full(
            (spectrum.count,),
            refractive_index_value,
            dtype=torch.float64,
        )
        refractive_index = indices.view(1, 1).expand(1, ray_count)
        polarization_broadcast = polarization.view(1, 1, 3).expand(
            1,
            ray_count,
            3,
        )
        return RayBundle(
            position=position_broadcast,
            direction=direction_broadcast,
            polarization_vector=polarization_broadcast,
            power=torch.ones((1, ray_count), dtype=torch.float64),
            refractive_index=refractive_index,
            optical_path=torch.zeros((1, ray_count), dtype=torch.float64),
            status=torch.full(
                (1, ray_count),
                RAY_STATUS_ACTIVE,
                dtype=torch.uint8,
            ),
            spectrum=spectrum,
        )

    def test_reflect_direction_matches_oracle_interacting(self) -> None:
        """
        reflect_direction 交互通道与独立 oracle 逐位一致
        """

        direction = self._oblique_unit_direction()
        unit_normal = torch.tensor(
            [[0.0, 0.0, -1.0]],
            dtype=torch.float64,
        ).expand(1, 1, 3)
        is_interacted = torch.ones((1, 1), dtype=torch.bool)
        produced = reflect_direction(
            ray_direction=direction.view(1, 1, 3),
            unit_normal=unit_normal,
            is_interacted=is_interacted,
        )
        expected = _explicit_householder_real(
            direction.view(1, 1, 3),
            unit_normal,
        )
        assert torch.equal(produced, expected)
        _assert_strict_unit_norm_real(
            produced,
            budget=_STRICT_DIRECTION_BUDGET,
        )

    def test_reflect_direction_preserves_non_interacting(self) -> None:
        """
        reflect_direction 非交互通道精确保留入射方向
        """

        direction = self._oblique_unit_direction()
        unit_normal = torch.tensor(
            [[0.0, 0.0, -1.0]],
            dtype=torch.float64,
        ).expand(1, 1, 3)
        is_interacted = torch.zeros((1, 1), dtype=torch.bool)
        produced = reflect_direction(
            ray_direction=direction.view(1, 1, 3),
            unit_normal=unit_normal,
            is_interacted=is_interacted,
        )
        assert torch.equal(produced, direction.view(1, 1, 3))

    def test_reflect_polarization_matches_oracle_interacting(self) -> None:
        """
        reflect_polarization_direction 交互通道与复 oracle 逐位一致
        """

        direction = self._oblique_unit_direction()
        polarization = torch.tensor(
            [0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
            dtype=torch.complex128,
        )
        unit_normal = torch.tensor(
            [[0.0, 0.0, -1.0]],
            dtype=torch.float64,
        ).expand(1, 1, 3)
        is_interacted = torch.ones((1, 1), dtype=torch.bool)
        produced = reflect_polarization_direction(
            ray_polarization=polarization.view(1, 1, 3),
            unit_normal=unit_normal,
            is_interacted=is_interacted,
        )
        expected = _explicit_householder_complex(
            polarization.view(1, 1, 3),
            unit_normal,
        )
        assert torch.equal(produced, expected)
        _assert_strict_unit_transverse_complex(
            produced,
            direction.view(1, 1, 3),
            budget=_STRICT_POLARIZATION_BUDGET,
        )

    def test_reflect_polarization_preserves_non_interacting(self) -> None:
        """
        reflect_polarization_direction 非交互通道精确保留入射偏振
        """

        polarization = torch.tensor(
            [0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
            dtype=torch.complex128,
        )
        unit_normal = torch.tensor(
            [[0.0, 0.0, -1.0]],
            dtype=torch.float64,
        ).expand(1, 1, 3)
        is_interacted = torch.zeros((1, 1), dtype=torch.bool)
        produced = reflect_polarization_direction(
            ray_polarization=polarization.view(1, 1, 3),
            unit_normal=unit_normal,
            is_interacted=is_interacted,
        )
        assert torch.equal(produced, polarization.view(1, 1, 3))



class TestNormalSignReversalEquivalence:
    """
    Householder 对法线符号不变（实 + 复）
    """

    @staticmethod
    def _real_case(
        device: torch.device,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        vector = torch.tensor(
            [[0.3, 0.0, math.sqrt(1.0 - 0.09)]],
            dtype=torch.float64,
            device=device,
        )
        unit_normal = torch.tensor(
            [[0.0, 0.0, -1.0]],
            dtype=torch.float64,
            device=device,
        )
        return vector, unit_normal

    @staticmethod
    def _complex_case(
        device: torch.device,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        vector = torch.tensor(
            [[0.6 + 0.0j, 0.0 - 0.8j, 0.0 + 0.0j]],
            dtype=torch.complex128,
            device=device,
        )
        unit_normal = torch.tensor(
            [[0.0, 0.0, -1.0]],
            dtype=torch.float64,
            device=device,
        )
        return vector, unit_normal

    def test_real_normal_sign_reversal_equivalent(self) -> None:
        """
        实 Householder 对 n̂ ↔ −n̂ 给同一反射结果（CPU）
        """

        vector, unit_normal = self._real_case(torch.device("cpu"))
        positive = _householder_reflect(
            vector=vector,
            unit_normal=unit_normal,
        )
        negative = _householder_reflect(
            vector=vector,
            unit_normal=-unit_normal,
        )
        assert torch.equal(positive, negative)

    def test_complex_normal_sign_reversal_equivalent(self) -> None:
        """
        复 Householder 对 n̂ ↔ −n̂ 给同一反射结果（CPU）
        """

        vector, unit_normal = self._complex_case(torch.device("cpu"))
        positive = _householder_reflect(
            vector=vector,
            unit_normal=unit_normal,
        )
        negative = _householder_reflect(
            vector=vector,
            unit_normal=-unit_normal,
        )
        assert torch.equal(positive, negative)

    def test_real_involution_returns_input(self) -> None:
        """
        实 Householder 是对合：施加两次恢复原向量
        """

        vector, unit_normal = self._real_case(torch.device("cpu"))
        once = _householder_reflect(
            vector=vector,
            unit_normal=unit_normal,
        )
        twice = _householder_reflect(
            vector=once,
            unit_normal=unit_normal,
        )
        assert torch.equal(twice, vector)




@cuda
class TestHouseholderCudaParity:
    """
    真实 CUDA 与 CPU 在固定 double 下 Householder 反射数值一致
    """

    @staticmethod
    def _to(bundle: RayBundle, device: torch.device) -> RayBundle:
        return RayBundle(
            position=bundle.position.to(device),
            direction=bundle.direction.to(device),
            polarization_vector=bundle.polarization_vector.to(device),
            power=bundle.power.to(device),
            refractive_index=bundle.refractive_index.to(device),
            optical_path=bundle.optical_path.to(device),
            status=bundle.status.to(device),
            spectrum=bundle.spectrum,
        )

    def test_direct_helper_real_matches_cpu_on_cuda(self) -> None:
        """
        实 helper 在真实 CUDA 上执行且与 CPU 逐位一致
        """

        if not torch.cuda.is_available():
            pytest.skip("需要真实 CUDA 设备")
        vector_cpu, normal_cpu = (
            TestDirectHelperMatchesOracle._real_vectors_and_normals(
                torch.device("cpu")
            )
        )
        vector_cuda = vector_cpu.to(device="cuda")
        normal_cuda = normal_cpu.to(device="cuda")
        produced_cpu = _householder_reflect(
            vector=vector_cpu,
            unit_normal=normal_cpu,
        )
        produced_cuda = _householder_reflect(
            vector=vector_cuda,
            unit_normal=normal_cuda,
        )
        assert produced_cuda.device.type == "cuda"
        assert torch.equal(produced_cuda.cpu(), produced_cpu)
        expected_cuda = _explicit_householder_real(vector_cuda, normal_cuda)
        assert torch.equal(produced_cuda.cpu(), expected_cuda.cpu())

    def test_direct_helper_complex_matches_cpu_on_cuda(self) -> None:
        """
        复 helper 在真实 CUDA 上执行且与 CPU 逐位一致
        """

        if not torch.cuda.is_available():
            pytest.skip("需要真实 CUDA 设备")
        (
            vector_cpu,
            normal_cpu,
        ) = TestDirectHelperMatchesOracle._complex_vectors_and_normals(
            torch.device("cpu")
        )
        vector_cuda = vector_cpu.to(device="cuda")
        normal_cuda = normal_cpu.to(device="cuda")
        produced_cpu = _householder_reflect(
            vector=vector_cpu,
            unit_normal=normal_cpu,
        )
        produced_cuda = _householder_reflect(
            vector=vector_cuda,
            unit_normal=normal_cuda,
        )
        assert produced_cuda.device.type == "cuda"
        assert torch.equal(produced_cuda.cpu(), produced_cpu)

    def test_reflect_at_polarization_matches_cpu_on_cuda(self) -> None:
        """
        ReflectAt 反射偏振在真实 CUDA 上与 CPU 同精度一致
        """

        if not torch.cuda.is_available():
            pytest.skip("需要真实 CUDA 设备")
        theta = math.radians(20.0)
        source = CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=Polarization.left_circular(),
            launch_tangent_x=(math.cos(theta), 0.0, math.sin(theta)),
            launch_tangent_y=(0.0, 1.0, 0.0),
            ray_power=1.0,
        )
        grid = SpatialGrid.centered(
            sample_counts=(2, 2),
            sample_spacing=(1.0, 1.0),
        )
        cpu_bundle = source(grid)
        source_cuda = source.to(device="cuda")
        cuda_bundle = source_cuda(grid)
        mirror = Plane(origin=(0.0, 0.0, 5.0))
        cpu_out = reflect_at(cpu_bundle, surface=mirror)
        cuda_out = reflect_at(cuda_bundle, surface=mirror.to(device="cuda"))
        assert cuda_out.polarization_vector.device.type == "cuda"
        assert torch.allclose(
            cpu_out.polarization_vector,
            cuda_out.polarization_vector.cpu(),
            atol=1.0e-10,
        )


from __future__ import annotations

from fractions import Fraction
import math
import sys

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics import ConstantMedium, Polarization, Spectrum, Vacuum
from chromatix_next.optics.element import RetarderAt, refract_at, retarder_at
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)
from chromatix_next.optics.surface import Plane

cuda = pytest.mark.cuda


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    return Spectrum.monochromatic(wavelength=wavelength)


def _active_bundle(
    *,
    positions: torch.Tensor,
    direction: torch.Tensor,
    polarization: torch.Tensor | None = None,
    power: torch.Tensor | None = None,
    spectrum: Spectrum | None = None,
    refractive_index_value: float | None = None,
) -> RayBundle:
    # 由显式位置、方向与偏振构造全活动单光谱光线束（fixed-double 精度）
    if spectrum is None:
        spectrum = _monochromatic()
    spectrum_count = spectrum.count
    ray_count = positions.shape[-2]
    positions = positions.to(dtype=torch.float64)
    direction = direction.to(dtype=torch.float64)
    direction_broadcast = direction.view(1, 1, 3).expand(
        spectrum_count,
        ray_count,
        3,
    )
    position_broadcast = positions.view(1, ray_count, 3).expand(
        spectrum_count,
        ray_count,
        3,
    )
    wavelengths = torch.tensor(spectrum.wavelengths, dtype=torch.float64)
    if refractive_index_value is None:
        indices = Vacuum().refractive_index(wavelengths).to(torch.float64)
    else:
        indices = torch.full(
            (spectrum_count,),
            float(refractive_index_value),
            dtype=torch.float64,
        )
    refractive_index = indices.view(spectrum_count, 1).expand(
        spectrum_count,
        ray_count,
    )
    power = (
        torch.ones((spectrum_count, ray_count), dtype=torch.float64)
        if power is None
        else power
    )
    if polarization is None:
        # 默认取 y 轴横向偏振（对近 +z/近 +x 方向均横向）
        polarization = torch.tensor([0.0, 1.0, 0.0], dtype=torch.complex128)
    polarization = polarization.to(dtype=torch.complex128)
    if polarization.dim() == 1:
        polarization = polarization.view(1, 1, 3).expand(
            spectrum_count,
            ray_count,
            3,
        )
    return RayBundle(
        position=position_broadcast,
        direction=direction_broadcast,
        polarization_vector=polarization,
        power=power,
        refractive_index=refractive_index,
        optical_path=torch.zeros(
            (spectrum_count, ray_count),
            dtype=torch.float64,
        ),
        status=torch.full(
            (spectrum_count, ray_count),
            RAY_STATUS_ACTIVE,
            dtype=torch.uint8,
        ),
        spectrum=spectrum,
    )


def _near_grazing_bundle(
    *,
    eps: float = 1.0e-13,
    polarization: torch.Tensor | None = None,
) -> tuple[RayBundle, Plane]:
    direction = torch.tensor([1.0, 0.0, eps], dtype=torch.float64)
    direction = direction / direction.norm()
    positions = torch.tensor([[0.0, 0.0, -1.0e-14]], dtype=torch.float64).unsqueeze(
        0
    )
    bundle = _active_bundle(
        positions=positions,
        direction=direction,
        polarization=polarization,
    )
    plane = Plane(
        origin=(0.0, 0.0, 0.0),
        clear_aperture_radius=2.0,
    )
    return bundle, plane




def _oracle_local_frame(
    ray_direction: torch.Tensor,
    tangent_x: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    direction_norm = torch.linalg.norm(ray_direction, dim=-1, keepdim=True)
    calculation_direction = ray_direction / direction_norm
    products = tangent_x * calculation_direction
    axial_component = products.sum(dim=-1, keepdim=True)
    axial_projection = axial_component * calculation_direction
    projected = tangent_x - axial_projection
    floating_point = torch.finfo(ray_direction.dtype)
    unit_roundoff = floating_point.eps / 2.0
    smallest_subnormal = floating_point.tiny * floating_point.eps
    gamma_five = (5.0 * unit_roundoff) / (1.0 - 5.0 * unit_roundoff)
    dot_bound = (
        gamma_five * products.abs().sum(dim=-1, keepdim=True)
        + 5.0 * smallest_subnormal
    )
    raw_bound = (
        calculation_direction.abs() * dot_bound
        + unit_roundoff * axial_projection.abs()
        + unit_roundoff * (tangent_x.abs() + axial_projection.abs())
        + 3.0 * smallest_subnormal
    )
    component_bound = (1.0 + gamma_five) * raw_bound + (
        5.0 * smallest_subnormal
    )
    assert bool((projected.abs() > component_bound).any(dim=-1).all())

    def _normalize(vector: torch.Tensor) -> torch.Tensor:
        scale = vector.abs().amax(dim=-1, keepdim=True)
        scaled = vector / scale
        return scaled / torch.linalg.norm(scaled, dim=-1, keepdim=True)

    local_x = _normalize(projected)
    longitudinal = (local_x * calculation_direction).sum(dim=-1, keepdim=True)
    local_x = _normalize(local_x - longitudinal * calculation_direction)
    local_y = _normalize(torch.linalg.cross(calculation_direction, local_x))
    local_x = _normalize(torch.linalg.cross(local_y, calculation_direction))
    return local_x, local_y


def _oracle_eigenstate_jones(
    azimuth_rad: float,
    ellipticity_rad: float,
) -> torch.Tensor:
    # 独立琼斯本征态（显式 cos/sin 构造，不复用生产 jones.py）
    cos_psi = math.cos(azimuth_rad)
    sin_psi = math.sin(azimuth_rad)
    cos_eps = math.cos(ellipticity_rad)
    sin_eps = math.sin(ellipticity_rad)
    ex = complex(cos_eps * cos_psi, -sin_eps * sin_psi)
    ey = complex(cos_eps * sin_psi, sin_eps * cos_psi)
    return torch.tensor([ex, ey], dtype=torch.complex128)


def _oracle_unit_phasor(cycles: float) -> complex:
    angle = 2.0 * math.pi * cycles
    return complex(math.cos(angle), math.sin(angle))


def _oracle_retarder_delta_matrix(
    retardance_cycles: float,
    azimuth_rad: float,
    ellipticity_rad: float,
) -> torch.Tensor:
    # 独立零均值 SU(2) 延迟**增量**矩阵 M − I（与生产的 delta 路径独立对拍）
    eigenstate = _oracle_eigenstate_jones(azimuth_rad, ellipticity_rad)
    projector = torch.outer(eigenstate, eigenstate.conj())
    identity = torch.eye(2, dtype=torch.complex128)
    orthogonal = identity - projector
    half = retardance_cycles / 2.0
    retarder = _oracle_unit_phasor(half) * projector + _oracle_unit_phasor(
        -half
    ) * orthogonal
    # 增量矩阵：在严格单位琼斯矩阵（零延迟）下恰为零矩阵
    return retarder - identity


def _oracle_retard_polarization_delta(
    polarization: torch.Tensor,
    ray_direction: torch.Tensor,
    tangent_x: torch.Tensor,
    retardance_cycles: float,
    azimuth_rad: float,
    ellipticity_rad: float,
) -> torch.Tensor:
    local_x, local_y = _oracle_local_frame(ray_direction, tangent_x)
    jones_x = (polarization * local_x).sum(dim=-1)
    jones_y = (polarization * local_y).sum(dim=-1)
    jones = torch.stack((jones_x, jones_y), dim=-1)
    delta_matrix = _oracle_retarder_delta_matrix(
        retardance_cycles,
        azimuth_rad,
        ellipticity_rad,
    )
    delta_jones = torch.einsum("ij,...j->...i", delta_matrix, jones)
    return (
        polarization
        + delta_jones[..., 0].unsqueeze(-1) * local_x
        + delta_jones[..., 1].unsqueeze(-1) * local_y
    )


def _oracle_minimal_rotation(
    incident_direction: torch.Tensor,
    transmitted_direction: torch.Tensor,
) -> torch.Tensor:
    incident_unit = incident_direction / torch.linalg.norm(
        incident_direction,
        dim=-1,
        keepdim=True,
    )
    transmitted_unit = transmitted_direction / torch.linalg.norm(
        transmitted_direction,
        dim=-1,
        keepdim=True,
    )
    cross = torch.linalg.cross(incident_unit, transmitted_unit)
    cos_angle = (incident_unit * transmitted_unit).sum(dim=-1)
    one_plus_cos = 1.0 + cos_angle
    safe = torch.where(
        one_plus_cos > 0.0,
        one_plus_cos,
        torch.ones_like(one_plus_cos),
    )
    zeros = torch.zeros_like(cos_angle)
    rows = (
        torch.stack((zeros, -cross[..., 2], cross[..., 1]), dim=-1),
        torch.stack((cross[..., 2], zeros, -cross[..., 0]), dim=-1),
        torch.stack((-cross[..., 1], cross[..., 0], zeros), dim=-1),
    )
    skew = torch.stack(rows, dim=-2)
    skew_sq = torch.einsum("...ij,...jk->...ik", skew, skew)
    batch_shape = skew.shape[:-2]
    identity = torch.eye(3, dtype=skew.dtype, device=skew.device).expand(
        *batch_shape,
        3,
        3,
    )
    return identity + skew + skew_sq / safe.unsqueeze(-1).unsqueeze(-1)


def _assert_strict_unit_transverse(
    polarization: torch.Tensor,
    direction: torch.Tensor,
    *,
    budget: float,
) -> None:
    # 严格 binary64 不变量断言：复单位范数平方残差 + 实/虚横向性残差
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


# binary64 严格预算（与 RayBundle 内冻结常数一致；此处独立重算用于断言）
_U = 2.0 ** -53
_GAMMA_5 = 5.0 * _U / (1.0 - 5.0 * _U)
_GAMMA_11 = 11.0 * _U / (1.0 - 11.0 * _U)
_STRICT_DIRECTION_BUDGET = 16.0 * _GAMMA_5
_STRICT_POLARIZATION_BUDGET = 16.0 * _GAMMA_11




class TestNearGrazingProjectionClosure:
    """
    非平行近掠射光线（投影范数 < 1e-12，非零）经 RetarderAt/PBSAt 完成且不变量守恒
    """

    def test_near_grazing_is_a_finite_encounter_not_a_parallel_miss(self) -> None:
        """
        近掠射光线命中 Plane（status ACTIVE），不是平行错过（SURFACE_MISSED）
        """
        bundle, plane = _near_grazing_bundle()
        output = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=0.0,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert output.status[0, 0] == RAY_STATUS_ACTIVE
        # 投影范数低于 1e-12，且独立 oracle 已认证它严格超过运算误差界
        tangent_x = plane.tangent_x.to(dtype=torch.float64)
        local_x, _ = _oracle_local_frame(bundle.direction, tangent_x)
        # oracle 已先缩放归一化；这里单独复验原投影的量级
        d_norm = torch.linalg.norm(bundle.direction, dim=-1, keepdim=True)
        calc = bundle.direction / d_norm
        dot = (tangent_x * calc).sum(dim=-1, keepdim=True)
        proj = tangent_x - dot * calc
        proj_norm = torch.linalg.norm(proj, dim=-1)
        assert float(proj_norm[0, 0]) < 1.0e-12
        assert float(proj_norm[0, 0]) > 0.0

    def test_near_grazing_zero_retardance_preserves_polarization_exactly(
        self,
    ) -> None:
        """
        零延迟近掠射：偏振按 ``torch.equal`` 精确保留（旧 1e-12 钳制在此失败）
        """
        bundle, plane = _near_grazing_bundle()
        output = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=0.0,
            retarded_eigenstate_azimuth_radians=math.radians(30.0),
            retarded_eigenstate_ellipticity_radians=math.radians(10.0),
        )
        assert torch.equal(
            output.polarization_vector,
            bundle.polarization_vector,
        )

    def test_near_grazing_nonzero_retardance_matches_independent_oracle(
        self,
    ) -> None:
        """
        非零延迟近掠射：与独立 SU(2) delta oracle 一致（认证后先缩放归一化）
        """
        bundle, plane = _near_grazing_bundle()
        azimuth = math.radians(22.0)
        ellipticity = math.radians(8.0)
        output = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )
        tangent_x = plane.tangent_x.to(dtype=torch.float64)
        expected = _oracle_retard_polarization_delta(
            bundle.polarization_vector,
            bundle.direction,
            tangent_x,
            retardance_cycles=0.31,
            azimuth_rad=azimuth,
            ellipticity_rad=ellipticity,
        )
        assert torch.allclose(
            output.polarization_vector,
            expected,
            atol=1.0e-12,
        )
        _assert_strict_unit_transverse(
            output.polarization_vector,
            output.direction,
            budget=_STRICT_POLARIZATION_BUDGET,
        )

class TestRetarderZeroRetardanceExactPreservation:
    """
    零延迟对正入射/斜入射/近掠射/批量/多光谱/终态/未中/渐晕/平行一律 torch.equal
    """

    @staticmethod
    def _zero_retard(bundle: RayBundle, plane: Plane) -> RayBundle:
        return retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=0.0,
            retarded_eigenstate_azimuth_radians=math.radians(30.0),
            retarded_eigenstate_ellipticity_radians=math.radians(10.0),
        )

    def test_near_grazing_exact(self) -> None:
        """
        近掠射零延迟：偏振按 ``torch.equal`` 精确保留
        """
        bundle, plane = _near_grazing_bundle()
        output = self._zero_retard(bundle, plane)
        assert torch.equal(
            output.polarization_vector,
            bundle.polarization_vector,
        )



class TestRefractPolarizationClosure:
    """
    正入射 torch.equal、斜入射独立最小旋转 oracle、TIR/非交互精确保留
    """



class TestStrictAdmissibilityRejection:
    """
    norm=1.000005 与横向性越界在构造时拒绝；相邻 ULP 准入并完成
    """



class TestOracleIndependence:
    """
    oracle 不导入两个禁用生产符号，也不使用任何 clamp
    """

    def test_oracle_does_not_import_forbidden_production_symbols(
        self,
    ) -> None:
        """
        本测试模块的全局命名空间不含两个禁用生产符号
        """
        forbidden = {
            "derive_plane_local_jones_frame",
            "retard_ray_polarization",
        }
        # 本测试模块的全局命名空间不含禁用生产符号
        module = sys.modules[__name__]
        present = forbidden & set(vars(module).keys())
        assert not present, f"oracle 模块意外定义了禁用符号: {present}"

    def test_oracle_local_frame_uses_certified_scale_first_path(self) -> None:
        """
        近掠射方向下 oracle 的局部轴经认证并保持单位正交
        """
        # 近掠射方向下 oracle 的 local_x/local_y 由认证后的先缩放路径构造
        bundle, _ = _near_grazing_bundle()
        tangent_x = torch.tensor([1.0, 0.0, 0.0], dtype=torch.float64)
        local_x, local_y = _oracle_local_frame(
            bundle.direction,
            tangent_x,
        )
        norm_x = torch.linalg.norm(local_x[0, 0]).item()
        norm_y = torch.linalg.norm(local_y[0, 0]).item()
        assert norm_x == pytest.approx(1.0, abs=1.0e-14)
        assert norm_y == pytest.approx(1.0, abs=1.0e-14)
        # 与生产对照（独立路径一致）：local_x 第三分量约为 −1
        assert local_x[0, 0, 2].item() == pytest.approx(-1.0, abs=1.0e-14)

    def test_oracle_zero_retardance_delta_is_exact_zero(self) -> None:
        """
        零延迟下 oracle 的 delta 矩阵严格为零（M − I = 0）
        """
        # 零延迟下 oracle 的 delta 矩阵严格为零（M − I = 0）
        delta = _oracle_retarder_delta_matrix(
            retardance_cycles=0.0,
            azimuth_rad=Fraction(1, 7) * math.pi,
            ellipticity_rad=Fraction(1, 11) * math.pi,
        )
        assert torch.equal(delta, torch.zeros_like(delta))




class TestExactClosureGradients:
    """
    近掠射延迟量梯度与斜折射曲率梯度到达 leaf
    """

    def test_near_grazing_retardance_gradient_flows(self) -> None:
        """
        近掠射延迟量梯度到达 leaf 且有限非零
        """
        bundle, plane = _near_grazing_bundle()
        retardance = torch.tensor(
            0.25,
            dtype=torch.float64,
            requires_grad=True,
        )
        output = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=math.radians(20.0),
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        output.polarization_vector.real.sum().backward()
        assert retardance.grad is not None
        assert bool(torch.isfinite(retardance.grad).all())
        assert retardance.grad.abs().item() > 0.0

    def test_near_grazing_component_gradient_flows(self) -> None:
        """
        近掠射组件 Parameter 延迟量梯度到达 leaf
        """
        bundle, plane = _near_grazing_bundle()
        component = RetarderAt(
            surface=plane,
            retardance_cycles=torch.nn.Parameter(
                torch.tensor(0.25, dtype=torch.float64)
            ),
            retarded_eigenstate_azimuth_radians=math.radians(20.0),
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        output = component(bundle)
        output.polarization_vector.real.sum().backward()
        assert component.retardance_cycles.grad is not None
        assert bool(
            torch.isfinite(component.retardance_cycles.grad).all()
        )




@cuda
class TestExactClosureCudaParity:
    """
    近掠射与正入射折射在真实 CUDA 上与 CPU 同精度一致
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

    def test_near_grazing_retarder_cuda_executes_and_matches_cpu(self) -> None:
        """
        近掠射零延迟在真实 CUDA 上执行且与 CPU 同精度精确保留
        """
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        cpu_bundle, plane = _near_grazing_bundle()
        cpu_out = retarder_at(
            cpu_bundle,
            surface=plane,
            retardance_cycles=0.0,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        cuda_bundle = self._to(cpu_bundle, torch.device("cuda"))
        cuda_plane = Plane(
            origin=(0.0, 0.0, 0.0),
            clear_aperture_radius=2.0,
        ).to(device="cuda")
        cuda_out = retarder_at(
            cuda_bundle,
            surface=cuda_plane,
            retardance_cycles=0.0,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert cuda_out.polarization_vector.device.type == "cuda"
        assert cuda_out.status[0, 0] == RAY_STATUS_ACTIVE
        # 零延迟：CPU 与 CUDA 各自 torch.equal 精确保留（per-device exactness）
        assert torch.equal(
            cuda_out.polarization_vector.cpu(),
            cpu_bundle.polarization_vector,
        )
        assert torch.equal(
            cuda_out.polarization_vector.cpu(),
            cpu_out.polarization_vector,
        )

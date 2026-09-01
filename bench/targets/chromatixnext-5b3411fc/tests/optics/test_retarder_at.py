
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics import (
    ConstantMedium,
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    Polarization,
    PolarizationRepresentation,
    RayBundle,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.element import RetarderAt, retarder, retarder_at
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)
from chromatix_next.optics.source import CollimatedRaySource
from chromatix_next.optics.surface import ConicEvenAsphere, Plane, Sphere
from tests.optics._valid_ray_inputs import _transverse_polarization_for_direction

cuda = pytest.mark.cuda


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    # 单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _grid(counts: tuple[int, int] = (3, 4)) -> SpatialGrid:
    # 中心对齐小型横向网格
    return SpatialGrid.centered(sample_counts=counts, sample_spacing=(1.0, 1.0))


def _active_bundle(
    *,
    positions: torch.Tensor,
    direction: torch.Tensor,
    medium: Vacuum | ConstantMedium | None = None,
    polarization: torch.Tensor | None = None,
) -> RayBundle:
    # 由显式位置与单一方向构造全活动单光谱光线束
    spectrum = _monochromatic()
    spectrum_count = spectrum.count
    ray_count = positions.shape[-2]
    positions = positions.to(dtype=torch.float64)
    direction_unit = direction.to(dtype=torch.float64)
    direction_broadcast = direction_unit.view(1, ray_count, 3).expand(
        spectrum_count,
        ray_count,
        3,
    )
    position_broadcast = positions.view(1, ray_count, 3).expand(
        spectrum_count,
        ray_count,
        3,
    )
    resolved_medium = medium or Vacuum()
    wavelengths = torch.tensor(spectrum.wavelengths, dtype=torch.float64)
    indices = resolved_medium.refractive_index(wavelengths).to(torch.float64)
    refractive_index = indices.view(spectrum_count, 1).expand(spectrum_count, ray_count)
    power = torch.ones((spectrum_count, ray_count), dtype=torch.float64)
    optical_path = torch.zeros((spectrum_count, ray_count), dtype=torch.float64)
    status = torch.full(
        (spectrum_count, ray_count),
        RAY_STATUS_ACTIVE,
        dtype=torch.uint8,
    )
    if polarization is None:
        polarization = _transverse_polarization_for_direction(direction_broadcast)
    polarization = polarization.to(dtype=torch.complex128)
    if polarization.dim() == 1:
        polarization = polarization.view(1, 1, 3).expand(spectrum_count, ray_count, 3)
    return RayBundle(
        position=position_broadcast,
        direction=direction_broadcast,
        polarization_vector=polarization,
        power=power,
        refractive_index=refractive_index,
        optical_path=optical_path,
        status=status,
        spectrum=spectrum,
    )




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
    # 独立琼斯本征态构造（方位角与椭率角）
    cos_psi = math.cos(azimuth_rad)
    sin_psi = math.sin(azimuth_rad)
    cos_eps = math.cos(ellipticity_rad)
    sin_eps = math.sin(ellipticity_rad)
    ex = complex(cos_eps * cos_psi, -sin_eps * sin_psi)
    ey = complex(cos_eps * sin_psi, sin_eps * cos_psi)
    return torch.tensor([ex, ey], dtype=torch.complex128)


def _oracle_unit_phasor(cycles: float) -> complex:
    # 独立单位相位构造
    angle = 2.0 * math.pi * cycles
    return complex(math.cos(angle), math.sin(angle))


def _oracle_retarder_matrix(
    retardance_cycles: float,
    azimuth_rad: float,
    ellipticity_rad: float,
) -> torch.Tensor:
    # 独立零均值 SU(2) 延迟矩阵
    eigenstate = _oracle_eigenstate_jones(azimuth_rad, ellipticity_rad)
    projector = torch.outer(eigenstate, eigenstate.conj())
    identity = torch.eye(2, dtype=torch.complex128)
    orthogonal = identity - projector
    half = retardance_cycles / 2.0
    return _oracle_unit_phasor(half) * projector + _oracle_unit_phasor(
        -half
    ) * orthogonal


def _oracle_retard_polarization(
    polarization: torch.Tensor,
    ray_direction: torch.Tensor,
    tangent_x: torch.Tensor,
    retardance_cycles: float,
    azimuth_rad: float,
    ellipticity_rad: float,
) -> torch.Tensor:
    # 独立 oracle：3D 到琼斯到 SU(2) 再回 3D
    local_x, local_y = _oracle_local_frame(ray_direction, tangent_x)
    jones_x = (polarization * local_x).sum(dim=-1)
    jones_y = (polarization * local_y).sum(dim=-1)
    jones = torch.stack((jones_x, jones_y), dim=-1)
    matrix = _oracle_retarder_matrix(retardance_cycles, azimuth_rad, ellipticity_rad)
    retarded_jones = torch.einsum("ij,...j->...i", matrix, jones)
    retarded_x = retarded_jones[..., 0]
    retarded_y = retarded_jones[..., 1]
    return retarded_x.unsqueeze(-1) * local_x + retarded_y.unsqueeze(-1) * local_y


def _default_tangent_x(plane: Plane) -> torch.Tensor:
    # 读取 Plane 的 tangent_x 副本
    return plane.tangent_x.detach().clone()


def _normal_incidence_bundle() -> RayBundle:
    # 正入射单光线活动束（z<0 沿 +z 命中 z=0 平面）
    positions = torch.tensor([[0.0, 0.0, -1.0e-6]], dtype=torch.float64).unsqueeze(0)
    return _active_bundle(positions=positions, direction=torch.tensor([0.0, 0.0, 1.0]))


def _unsupported_surface(kind: str) -> object:
    if kind == "sphere":
        return Sphere(radius_of_curvature=5.0e-6)
    if kind == "conic":
        return ConicEvenAsphere(curvature=1.0 / 5.0e-6, conic_constant=0.0)

    class _FakeSurface:
        # 不具备 Plane 身份的鸭子类型占位
        tangent_x = torch.tensor([1.0, 0.0, 0.0])

    return _FakeSurface()




class TestRetarderAtPublicContract:
    """
    Surface 收窄、bundle 类型、参数契约与 Function/Component 对偶
    """

    def test_unresolvable_plane_local_projection_has_action_identity(
        self,
    ) -> None:
        """
        精确非退化但不可表示的局部投影由 RetarderAt 稳定拒绝
        """

        direction = torch.tensor(
            (0.8125095448101878, 0.13732140544081897, 0.5665430885644089),
            dtype=torch.float64,
        )
        surface = Plane(
            origin=(0.0, 0.0, 0.0),
            tangent_x=(
                0.8125095448101878,
                0.13732140544081894,
                0.566543088564409,
            ),
            tangent_y=(
                0.28578369479692706,
                -0.9408913256009701,
                -0.18179987127901373,
            ),
        )
        bundle = _active_bundle(
            positions=(-direction).reshape(1, 1, 3),
            direction=direction,
        )

        with pytest.raises(OpticalValueError) as rejected:
            retarder_at(
                bundle,
                surface=surface,
                retardance_cycles=0.1,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )

        assert (
            rejected.value.identity
            == "retarder_at_plane_local_projection_unresolvable"
        )

    def test_noninteracting_cancellation_witness_preserves_polarization(
        self,
    ) -> None:
        """
        同一消去见证未命中时不消费局部帧，并精确保留偏振
        """

        direction = torch.tensor(
            (0.8125095448101878, 0.13732140544081897, 0.5665430885644089),
            dtype=torch.float64,
        )
        surface = Plane(
            origin=(0.0, 0.0, 0.0),
            tangent_x=(
                0.8125095448101878,
                0.13732140544081894,
                0.566543088564409,
            ),
            tangent_y=(
                0.28578369479692706,
                -0.9408913256009701,
                -0.18179987127901373,
            ),
        )
        bundle = _active_bundle(
            positions=direction.reshape(1, 1, 3),
            direction=direction,
        )

        output = retarder_at(
            bundle,
            surface=surface,
            retardance_cycles=0.1,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )

        assert torch.equal(output.polarization_vector, bundle.polarization_vector)
        assert torch.equal(output.power, bundle.power)

    def test_binary64_projection_below_square_range_reaches_public_action(
        self,
    ) -> None:
        """
        具有 2^-600 非零局部投影的有效 Plane 光路完成公共延迟动作
        """

        tiny_projection = math.ldexp(1.0, -600)
        direction = torch.tensor(
            (0.0, tiny_projection, 1.0),
            dtype=torch.float64,
        )
        bundle = _active_bundle(
            positions=torch.zeros((1, 1, 3), dtype=torch.float64),
            direction=direction,
            polarization=torch.tensor(
                (1.0, 0.0, 0.0),
                dtype=torch.complex128,
            ),
        )
        surface = Plane(
            origin=direction,
            tangent_x=(0.0, 0.0, 1.0),
            tangent_y=(1.0, 0.0, 0.0),
        )

        output = retarder_at(
            bundle,
            surface=surface,
            retardance_cycles=0.0,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )

        assert torch.equal(output.position, direction.reshape(1, 1, 3))
        assert torch.equal(
            output.polarization_vector,
            bundle.polarization_vector,
        )

    def test_function_rejects_non_raybundle(self) -> None:
        """
        非光线束输入以稳定身份拒绝
        """
        bundle = _normal_incidence_bundle()
        with pytest.raises(Exception):  # noqa: PT011
            retarder_at(
                "not a bundle",  # type: ignore[arg-type]
                surface=Plane(),
                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )

    def test_function_rejects_sphere_surface(self) -> None:
        """
        球面以稳定身份拒绝（Plane-only 收窄）
        """
        bundle = _normal_incidence_bundle()
        with pytest.raises(Exception):  # noqa: PT011
            retarder_at(
                bundle,
                surface=Sphere(radius_of_curvature=5.0e-6),  # type: ignore[arg-type]

                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )

    def test_function_rejects_conic_surface(self) -> None:
        """
        圆锥非球面以稳定身份拒绝（Plane-only 收窄）
        """
        bundle = _normal_incidence_bundle()
        with pytest.raises(Exception):  # noqa: PT011
            retarder_at(
                bundle,
                surface=ConicEvenAsphere(  # type: ignore[arg-type]
                    curvature=1.0 / 5.0e-6,
                    conic_constant=0.0,
                ),

                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )

    def test_function_rejects_duck_typed_surface(self) -> None:
        """
        任意鸭子类型对象以稳定身份拒绝
        """

        class _FakeSurface:
            # 不具备 Plane 身份的鸭子类型占位
            tangent_x = torch.tensor([1.0, 0.0, 0.0])

        bundle = _normal_incidence_bundle()
        with pytest.raises(Exception):  # noqa: PT011
            retarder_at(  # type: ignore[arg-type]
                bundle,
                surface=_FakeSurface(),  # type: ignore[arg-type]
                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )

    @pytest.mark.parametrize("kind", ("sphere", "conic", "duck"))
    def test_function_rejects_unsupported_surface_with_stable_identity(
        self,
        kind: str,
    ) -> None:
        """
        函数入口对 Sphere/ConicEvenAsphere/非 Surface 对象抛稳定 surface 身份
        """
        bundle = _normal_incidence_bundle()
        with pytest.raises(Exception) as information:  # noqa: PT011
            retarder_at(
                bundle,
                surface=_unsupported_surface(kind),  # type: ignore[arg-type]
                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )
        assert "retarder_at_surface_invalid" in str(information.value)

    @pytest.mark.parametrize("kind", ("sphere", "conic", "duck"))
    def test_component_rejects_unsupported_surface_with_stable_identity(
        self,
        kind: str,
    ) -> None:
        """
        组件构造期对 Sphere/ConicEvenAsphere/非 Surface 对象抛稳定 surface 身份
        """
        with pytest.raises(Exception) as information:  # noqa: PT011
            RetarderAt(
                surface=_unsupported_surface(kind),  # type: ignore[arg-type]
                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )
        assert "retarder_at_surface_invalid" in str(information.value)

    def test_function_and_component_accept_plane(self) -> None:
        """
        Plane 在函数与组件两条路径上都被接受（删除别名后契约不变）
        """
        bundle = _normal_incidence_bundle()
        function_output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert isinstance(function_output, RayBundle)
        component = RetarderAt(
            surface=Plane(),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert isinstance(component(bundle), RayBundle)

    def test_function_rejects_non_finite_retardance(self) -> None:
        """
        非有限延迟量以稳定身份拒绝
        """
        bundle = _normal_incidence_bundle()
        for bad in (float("nan"), float("inf"), -float("inf")):
            with pytest.raises(Exception):  # noqa: PT011
                retarder_at(
                    bundle,
                    surface=Plane(),
                    retardance_cycles=bad,
                    retarded_eigenstate_azimuth_radians=0.0,
                    retarded_eigenstate_ellipticity_radians=0.0,
                )

    def test_function_rejects_ellipticity_outside_interval(self) -> None:
        """
        椭率角超出正则区间以稳定身份拒绝
        """
        bundle = _normal_incidence_bundle()
        for bad in (math.pi / 4.0 + 1.0e-3, -math.pi / 4.0 - 1.0e-3):
            with pytest.raises(Exception):  # noqa: PT011
                retarder_at(
                    bundle,
                    surface=Plane(),
                    retardance_cycles=0.25,
                    retarded_eigenstate_azimuth_radians=0.0,
                    retarded_eigenstate_ellipticity_radians=bad,
                )

    def test_function_accepts_ellipticity_endpoints(self) -> None:
        """
        椭率角正则区间端点（圆偏振）被接受
        """
        bundle = _normal_incidence_bundle()
        for endpoint in (math.pi / 4.0, -math.pi / 4.0):
            output = retarder_at(
                bundle,
                surface=Plane(),
                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=endpoint,
            )
            assert isinstance(output, RayBundle)

    def test_component_construction_rejects_sphere(self) -> None:
        """
        组件构造期同样拒绝球面
        """
        with pytest.raises(Exception):  # noqa: PT011
            RetarderAt(
                surface=Sphere(radius_of_curvature=5.0e-6),  # type: ignore[arg-type]
                retardance_cycles=0.25,
                retarded_eigenstate_azimuth_radians=0.0,
                retarded_eigenstate_ellipticity_radians=0.0,
            )

    def test_component_delegates_one_calculation(self) -> None:
        """
        组件 forward 与函数入口逐位一致
        """
        bundle = _normal_incidence_bundle()
        component = RetarderAt(
            surface=Plane(),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        function_output = retarder_at(
            bundle,
            surface=component.surface,
            retardance_cycles=component.retardance_cycles,
            retarded_eigenstate_azimuth_radians=(
                component.retarded_eigenstate_azimuth_radians
            ),
            retarded_eigenstate_ellipticity_radians=(
                component.retarded_eigenstate_ellipticity_radians
            ),
        )
        component_output = component(bundle)
        assert torch.equal(
            function_output.polarization_vector,
            component_output.polarization_vector,
        )
        assert torch.equal(component_output.position, function_output.position)

    def test_component_role_is_element(self) -> None:
        """
        组件角色字面量为 element
        """
        component = RetarderAt(
            surface=Plane(),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert component.role == "element"




class TestRetarderAtAnalyticOracle:
    """
    线性、对角、圆、一般椭圆；正/斜入射；旋转姿态下的独立 oracle 对拍
    """

    @pytest.mark.parametrize(
        ("azimuth_deg", "ellipticity_deg"),
        (
            (0.0, 0.0),
            (90.0, 0.0),
            (45.0, 0.0),
            (0.0, 45.0),
            (0.0, -45.0),
            (30.0, 20.0),
            (-60.0, -10.0),
        ),
    )
    @pytest.mark.parametrize(
        ("direction", "label"),
        (
            ([0.0, 0.0, 1.0], "normal"),
            ([0.3, 0.0, math.sqrt(1.0 - 0.3 * 0.3)], "oblique-xz"),
            (
                [0.2, 0.1, math.sqrt(1.0 - 0.2 * 0.2 - 0.1 * 0.1)],
                "oblique-general",
            ),
        ),
    )
    def test_retarded_polarization_matches_oracle(
        self,
        azimuth_deg: float,
        ellipticity_deg: float,
        direction: list[float],
        label: str,
    ) -> None:
        """
        延迟后偏振与独立 oracle 逐位一致
        """
        del label
        azimuth = math.radians(azimuth_deg)
        ellipticity = math.radians(ellipticity_deg)
        direction_tensor = torch.tensor(direction, dtype=torch.float64)
        direction_tensor = direction_tensor / direction_tensor.norm()
        positions = torch.tensor([[[0.0, 0.0, -1.0e-6]]], dtype=torch.float64)
        bundle = _active_bundle(positions=positions, direction=direction_tensor)
        plane = Plane(origin=(0.0, 0.0, 0.0))
        output = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=0.125,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )
        expected = _oracle_retard_polarization(
            bundle.polarization_vector,
            bundle.direction,
            _default_tangent_x(plane),
            retardance_cycles=0.125,
            azimuth_rad=azimuth,
            ellipticity_rad=ellipticity,
        )
        assert torch.allclose(output.polarization_vector, expected, atol=1.0e-12)

    def test_rotated_plane_pose_uses_posed_axis_y(self) -> None:
        """
        旋转姿态下 local 帧由旋转后的 tangent_x 派生
        """
        theta = math.radians(35.0)
        plane = Plane(
            origin=(0.0, 0.0, 0.0),
            tangent_x=(math.cos(theta), math.sin(theta), 0.0),
            tangent_y=(-math.sin(theta), math.cos(theta), 0.0),
        )
        direction = torch.tensor(
            [0.2, 0.1, math.sqrt(1.0 - 0.04 - 0.01)],
            dtype=torch.float64,
        )
        direction = direction / direction.norm()
        positions = torch.tensor([[[0.0, 0.0, -1.0e-6]]], dtype=torch.float64)
        bundle = _active_bundle(positions=positions, direction=direction)
        output = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=0.3,
            retarded_eigenstate_azimuth_radians=math.radians(20.0),
            retarded_eigenstate_ellipticity_radians=math.radians(5.0),
        )
        expected = _oracle_retard_polarization(
            bundle.polarization_vector,
            bundle.direction,
            _default_tangent_x(plane),
            retardance_cycles=0.3,
            azimuth_rad=math.radians(20.0),
            ellipticity_rad=math.radians(5.0),
        )
        assert torch.allclose(output.polarization_vector, expected, atol=1.0e-12)




class TestRetarderAtInvariants:
    """
    零延迟恒等、范数守恒、可逆/合成、有限输出、透传
    """

    def test_zero_retardance_is_exactly_identity(self) -> None:
        """
        零延迟按位恒等
        """
        bundle = _normal_incidence_bundle()
        output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=0.0,
            retarded_eigenstate_azimuth_radians=math.radians(30.0),
            retarded_eigenstate_ellipticity_radians=math.radians(10.0),
        )
        assert torch.equal(output.polarization_vector, bundle.polarization_vector)

    def test_full_cycle_retardance_is_global_phase_only(self) -> None:
        """
        整周期延迟给全局 π 相位，偏振态不变
        """
        bundle = _normal_incidence_bundle()
        output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=1.0,
            retarded_eigenstate_azimuth_radians=math.radians(30.0),
            retarded_eigenstate_ellipticity_radians=math.radians(15.0),
        )
        assert torch.allclose(
            output.polarization_vector,
            -bundle.polarization_vector,
            atol=1.0e-12,
        )

    def test_two_full_cycles_is_exact_identity(self) -> None:
        """
        两整周期延迟严格恒等
        """
        bundle = _normal_incidence_bundle()
        output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=2.0,
            retarded_eigenstate_azimuth_radians=math.radians(30.0),
            retarded_eigenstate_ellipticity_radians=math.radians(15.0),
        )
        assert torch.allclose(
            output.polarization_vector,
            bundle.polarization_vector,
            atol=1.0e-12,
        )

    def test_polarization_norm_is_conserved(self) -> None:
        """
        延迟后复单位范数守恒
        """
        bundle = _normal_incidence_bundle()
        output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=0.37,
            retarded_eigenstate_azimuth_radians=math.radians(22.0),
            retarded_eigenstate_ellipticity_radians=math.radians(8.0),
        )
        input_norm = (
            bundle.polarization_vector.real**2
            + bundle.polarization_vector.imag**2
        ).sum(dim=-1)
        output_norm = (
            output.polarization_vector.real**2
            + output.polarization_vector.imag**2
        ).sum(dim=-1)
        assert torch.allclose(input_norm, output_norm, atol=1.0e-12)

    def test_output_is_finite_everywhere(self) -> None:
        """
        输出偏振/位置/方向处处有限
        """
        bundle = _normal_incidence_bundle()
        output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=0.42,
            retarded_eigenstate_azimuth_radians=math.radians(11.0),
            retarded_eigenstate_ellipticity_radians=math.radians(3.0),
        )
        assert bool(torch.isfinite(output.polarization_vector).all())
        assert bool(torch.isfinite(output.position).all())
        assert bool(torch.isfinite(output.direction).all())

    def test_double_application_composes_to_single_application(self) -> None:
        """
        两次半周期合成等价于一次整周期
        """
        bundle = _normal_incidence_bundle()
        plane = Plane()
        azimuth = math.radians(30.0)
        ellipticity = math.radians(10.0)
        half = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=0.5,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )
        composed = retarder_at(
            half,
            surface=plane,
            retardance_cycles=0.5,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )
        single_full = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=1.0,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )
        assert torch.allclose(
            composed.polarization_vector,
            single_full.polarization_vector,
            atol=1.0e-9,
        )

    def test_inverse_retardance_restores_polarization(self) -> None:
        """
        正负延迟对消恢复入射偏振
        """
        bundle = _normal_incidence_bundle()
        plane = Plane()
        forward = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.radians(25.0),
            retarded_eigenstate_ellipticity_radians=math.radians(7.0),
        )
        restored = retarder_at(
            forward,
            surface=plane,
            retardance_cycles=-0.31,
            retarded_eigenstate_azimuth_radians=math.radians(25.0),
            retarded_eigenstate_ellipticity_radians=math.radians(7.0),
        )
        assert torch.allclose(
            restored.polarization_vector,
            bundle.polarization_vector,
            atol=1.0e-9,
        )

    def test_direction_power_index_status_pass_through(self) -> None:
        """
        方向/功率/折射率/状态透传不变
        """
        positions = torch.tensor([[[0.0, 0.0, -1.0e-6]]], dtype=torch.float64)
        bundle = _active_bundle(
            positions=positions,
            direction=torch.tensor([0.0, 0.0, 1.0]),
            medium=ConstantMedium(index=1.3),
        )
        output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert torch.equal(output.direction, bundle.direction)
        assert torch.equal(output.power, bundle.power)
        assert torch.equal(output.refractive_index, bundle.refractive_index)
        assert output.status[0, 0] == RAY_STATUS_ACTIVE




class TestRetarderAtNonInteractingLanes:
    """
    孔径未中、终态、平行退化通道精确保留入射偏振
    """

    def test_missed_ray_preserves_polarization(self) -> None:
        """
        未命中光线状态置位且偏振透传
        """
        positions = torch.tensor([[[0.0, 0.0, -1.0e-6]]], dtype=torch.float64)
        bundle = _active_bundle(
            positions=positions,
            direction=torch.tensor([1.0, 0.0, 0.0]),
        )
        output = retarder_at(
            bundle,
            surface=Plane(origin=(0.0, 0.0, 0.0)),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert output.status[0, 0] == RAY_STATUS_SURFACE_MISSED
        assert torch.equal(output.polarization_vector, bundle.polarization_vector)

    def test_out_of_aperture_preserves_polarization(self) -> None:
        """
        孔径外命中标渐晕且偏振透传
        """
        positions = torch.tensor([[[0.0, 5.0e-4, -3.0e-6]]], dtype=torch.float64)
        bundle = _active_bundle(
            positions=positions,
            direction=torch.tensor([0.0, 0.0, 1.0]),
        )
        surface = Plane(
            origin=(0.0, 0.0, 0.0),
            clear_aperture_radius=2.0e-4,
        )
        output = retarder_at(
            bundle,
            surface=surface,
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert output.status[0, 0] == RAY_STATUS_VIGNETTED
        assert torch.equal(output.polarization_vector, bundle.polarization_vector)

    def test_terminal_ray_preserves_polarization(self) -> None:
        """
        已终态光线进入延迟面偏振不动
        """
        positions = torch.tensor([[[0.0, 0.0, -1.0e-6]]], dtype=torch.float64)
        spectrum = _monochromatic()
        direction = torch.tensor([0.0, 0.0, 1.0], dtype=torch.float64).view(1, 1, 3)
        polarization = _transverse_polarization_for_direction(direction)
        bundle = RayBundle(
            position=positions,
            direction=direction,
            polarization_vector=polarization,
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.ones((1, 1), dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full((1, 1), RAY_STATUS_VIGNETTED, dtype=torch.uint8),
            spectrum=spectrum,
        )
        output = retarder_at(
            bundle,
            surface=Plane(origin=(0.0, 0.0, 0.0)),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert output.status[0, 0] == RAY_STATUS_VIGNETTED
        assert torch.equal(output.polarization_vector, bundle.polarization_vector)

    def test_parallel_ray_does_not_produce_nan(self) -> None:
        """
        光线平行于 Plane 时不产生非数
        """
        positions = torch.tensor([[[0.0, 0.0, -1.0e-6]]], dtype=torch.float64)
        bundle = _active_bundle(
            positions=positions,
            direction=torch.tensor([1.0, 0.0, 0.0]),
        )
        output = retarder_at(
            bundle,
            surface=Plane(origin=(0.0, 0.0, 0.0)),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert bool(torch.isfinite(output.polarization_vector).all())
        assert torch.equal(output.polarization_vector, bundle.polarization_vector)




class TestRetarderAtBatching:
    """
    多光谱、多光线、批量下逐光线独立作用
    """

    def test_multi_spectrum_multi_ray_matches_oracle(self) -> None:
        """
        多光谱多光线逐通道与 oracle 一致
        """
        spectrum = Spectrum(
            wavelengths=(1.0e-6, 1.5e-6, 2.0e-6),
            weights=(0.3, 0.3, 0.4),
        )
        source = CollimatedRaySource(
            spectrum=spectrum,
            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        bundle = source(_grid(counts=(2, 3)))
        plane = Plane(origin=(0.0, 0.0, 0.0))
        positions = bundle.position.clone()
        positions[..., 2] = -1.0e-6
        moved = RayBundle(
            position=positions,
            direction=bundle.direction,
            polarization_vector=bundle.polarization_vector,
            power=bundle.power,
            refractive_index=bundle.refractive_index,
            optical_path=bundle.optical_path,
            status=bundle.status,
            spectrum=bundle.spectrum,
        )
        output = retarder_at(
            moved,
            surface=plane,
            retardance_cycles=0.18,
            retarded_eigenstate_azimuth_radians=math.radians(15.0),
            retarded_eigenstate_ellipticity_radians=math.radians(6.0),
        )
        expected = _oracle_retard_polarization(
            moved.polarization_vector,
            moved.direction,
            _default_tangent_x(plane),
            retardance_cycles=0.18,
            azimuth_rad=math.radians(15.0),
            ellipticity_rad=math.radians(6.0),
        )
        assert torch.allclose(output.polarization_vector, expected, atol=1.0e-12)
        assert (
            output.polarization_vector.shape
            == moved.polarization_vector.shape
        )

    def test_batch_dimension_broadcast_matches_oracle(self) -> None:
        """
        显式批量维下广播正确
        """
        batch, spectral, ray = 2, 2, 3
        direction = torch.tensor([0.0, 0.0, 1.0], dtype=torch.float64)
        positions = torch.zeros((batch, spectral, ray, 3), dtype=torch.float64)
        positions[..., 2] = -1.0e-6
        direction_broadcast = direction.view(1, 1, 1, 3).expand(batch, spectral, ray, 3)
        polarization = torch.zeros((batch, spectral, ray, 3), dtype=torch.complex128)
        polarization[..., 0] = 1.0
        spectrum = Spectrum(wavelengths=(1.0e-6, 2.0e-6), weights=(0.5, 0.5))
        wavelengths = torch.tensor(spectrum.wavelengths, dtype=torch.float64)
        indices = Vacuum().refractive_index(wavelengths).to(torch.float64)
        refractive_index = indices.view(1, spectral, 1).expand(batch, spectral, ray)
        bundle = RayBundle(
            position=positions,
            direction=direction_broadcast,
            polarization_vector=polarization,
            power=torch.ones((batch, spectral, ray), dtype=torch.float64),
            refractive_index=refractive_index,
            optical_path=torch.zeros((batch, spectral, ray), dtype=torch.float64),
            status=torch.full(
                (batch, spectral, ray),
                RAY_STATUS_ACTIVE,
                dtype=torch.uint8,
            ),
            spectrum=spectrum,
        )
        plane = Plane(origin=(0.0, 0.0, 0.0))
        output = retarder_at(
            bundle,
            surface=plane,
            retardance_cycles=0.21,
            retarded_eigenstate_azimuth_radians=math.radians(18.0),
            retarded_eigenstate_ellipticity_radians=math.radians(4.0),
        )
        expected = _oracle_retard_polarization(
            bundle.polarization_vector,
            bundle.direction,
            _default_tangent_x(plane),
            retardance_cycles=0.21,
            azimuth_rad=math.radians(18.0),
            ellipticity_rad=math.radians(4.0),
        )
        assert torch.allclose(output.polarization_vector, expected, atol=1.0e-12)
        assert output.polarization_vector.shape == (
            batch,
            spectral,
            ray,
            3,
        )

    def test_mixed_active_missed_terminal_lanes_all_finite(self) -> None:
        """
        混合通道下命中/未命中/终态各自行为正确
        """
        spectrum = _monochromatic()
        positions = torch.tensor(
            [
                [0.0, 0.0, -3.0e-6],
                [0.0, 0.0, -3.0e-6],
                [0.0, 0.0, -3.0e-6],
            ],
            dtype=torch.float64,
        ).unsqueeze(0)
        directions = torch.tensor(
            [[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            dtype=torch.float64,
        )
        polarization = torch.zeros((1, 3, 3), dtype=torch.complex128)
        polarization[0, 0, 0] = 1.0
        polarization[0, 1, 1] = 1.0
        polarization[0, 2, 0] = 1.0
        statuses = torch.tensor(
            [RAY_STATUS_ACTIVE, RAY_STATUS_ACTIVE, RAY_STATUS_VIGNETTED],
            dtype=torch.uint8,
        )
        bundle = RayBundle(
            position=positions,
            direction=directions.unsqueeze(0).expand(1, 3, 3),
            polarization_vector=polarization.expand(1, 3, 3),
            power=torch.ones((1, 3), dtype=torch.float64),
            refractive_index=torch.ones((1, 3), dtype=torch.float64),
            optical_path=torch.zeros((1, 3), dtype=torch.float64),
            status=statuses.view(1, 3).expand(1, 3),
            spectrum=spectrum,
        )
        output = retarder_at(
            bundle,
            surface=Plane(origin=(0.0, 0.0, 0.0)),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        assert output.status[0, 0] == RAY_STATUS_ACTIVE
        assert output.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert output.status[0, 2] == RAY_STATUS_VIGNETTED
        expected_ray0 = _oracle_retard_polarization(
            bundle.polarization_vector[:, 0:1],
            bundle.direction[:, 0:1],
            _default_tangent_x(Plane()),
            retardance_cycles=0.25,
            azimuth_rad=0.0,
            ellipticity_rad=0.0,
        )
        assert torch.allclose(
            output.polarization_vector[:, 0:1],
            expected_ray0,
            atol=1.0e-12,
        )
        assert torch.equal(
            output.polarization_vector[:, 1],
            bundle.polarization_vector[:, 1],
        )
        assert torch.equal(
            output.polarization_vector[:, 2],
            bundle.polarization_vector[:, 2],
        )
        assert bool(torch.isfinite(output.polarization_vector).all())




class TestWaveRayCorrespondence:
    """
    同一 SU(2) 律在波与光线上的归一化偏振空间定量对应
    """

    def test_normal_incidence_ray_jones_matches_matrix(self) -> None:
        """
        正入射默认姿态下光线琼斯投影与独立矩阵作用一致
        """
        retardance_cycles = 0.125
        azimuth = math.radians(20.0)
        ellipticity = math.radians(5.0)
        bundle = _normal_incidence_bundle()
        authored_pol = torch.tensor([1.0, 0.0, 0.0], dtype=torch.complex128)
        pol_vec = authored_pol.view(1, 1, 3).expand_as(
            bundle.polarization_vector
        )
        bundle_with_pol = RayBundle(
            position=bundle.position,
            direction=bundle.direction,
            polarization_vector=pol_vec,
            power=bundle.power,
            refractive_index=bundle.refractive_index,
            optical_path=bundle.optical_path,
            status=bundle.status,
            spectrum=bundle.spectrum,
        )
        ray_output = retarder_at(
            bundle_with_pol,
            surface=Plane(),
            retardance_cycles=retardance_cycles,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )
        ray_jones = torch.stack(
            (
                ray_output.polarization_vector[0, 0, 0],
                ray_output.polarization_vector[0, 0, 1],
            ),
            dim=-1,
        )
        retarder_matrix = _oracle_retarder_matrix(
            retardance_cycles,
            azimuth_rad=azimuth,
            ellipticity_rad=ellipticity,
        )
        wave_jones = retarder_matrix @ torch.tensor(
            [1.0 + 0j, 0.0 + 0j],
            dtype=torch.complex128,
        )
        assert torch.allclose(ray_jones, wave_jones, atol=1.0e-12)

    def test_wave_retarder_agrees_with_ray(self) -> None:
        """
        波延迟器作用于匹配包络与光线延迟器输出投影对拍
        """
        retardance_cycles = 0.25
        azimuth = math.radians(0.0)
        ellipticity = math.radians(0.0)
        spatial_grid = SpatialGrid.centered(
            sample_counts=(1, 1),
            sample_spacing=(1.0, 1.0),
        )
        spectrum = Spectrum.monochromatic(wavelength=2.0e-6)
        envelope = torch.zeros((1, 2, 1, 1), dtype=torch.complex128)
        scale = 1.0 / math.sqrt(2.0)
        envelope[0, 0, 0, 0] = torch.tensor(scale, dtype=torch.complex128)
        envelope[0, 1, 0, 0] = torch.tensor(scale, dtype=torch.complex128)
        field = OpticalField(
            envelope=envelope,
            grid=spatial_grid,
            spectrum=spectrum,
            polarization_representation=PolarizationRepresentation.TRANSVERSE,
            medium=Vacuum(),
            normalization=FieldNormalization.RELATIVE,
            path_reference=OpticalPathReference(lengths=(0.0,) * spectrum.count,),
        )
        wave_output = retarder(
            field,
            retardance_cycles=retardance_cycles,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )
        wave_jones_out = wave_output.envelope[0, :, 0, 0]
        bundle = _normal_incidence_bundle()
        authored_pol = torch.tensor([scale, scale, 0.0], dtype=torch.complex128)
        pol_vec = authored_pol.view(1, 1, 3).expand_as(
            bundle.polarization_vector
        )
        bundle_with_pol = RayBundle(
            position=bundle.position,
            direction=bundle.direction,
            polarization_vector=pol_vec,
            power=bundle.power,
            refractive_index=bundle.refractive_index,
            optical_path=bundle.optical_path,
            status=bundle.status,
            spectrum=bundle.spectrum,
        )
        ray_output = retarder_at(
            bundle_with_pol,
            surface=Plane(),
            retardance_cycles=retardance_cycles,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )
        ray_jones_out = torch.stack(
            (
                ray_output.polarization_vector[0, 0, 0],
                ray_output.polarization_vector[0, 0, 1],
            ),
            dim=-1,
        )
        assert torch.allclose(ray_jones_out, wave_jones_out, atol=1.0e-12)




class TestRetarderAtGradients:
    """
    延迟量、本征态参数的梯度到达 leaf
    """

    def test_retardance_gradient_flows(self) -> None:
        """
        延迟量梯度有限且非零
        """
        bundle = _normal_incidence_bundle()
        retardance = torch.tensor(0.2, dtype=torch.float64, requires_grad=True)
        output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=math.radians(30.0),
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        loss = output.polarization_vector.real.sum()
        loss.backward()
        assert retardance.grad is not None
        assert bool(torch.isfinite(retardance.grad).all())
        assert retardance.grad.abs().item() > 0.0

    def test_azimuth_gradient_flows(self) -> None:
        """
        方位角梯度有限
        """
        bundle = _normal_incidence_bundle()
        azimuth = torch.tensor(
            math.radians(20.0),
            dtype=torch.float64,
            requires_grad=True,
        )
        output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=azimuth,
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        loss = output.polarization_vector.real.sum()
        loss.backward()
        assert azimuth.grad is not None
        assert bool(torch.isfinite(azimuth.grad).all())

    def test_ellipticity_gradient_flows(self) -> None:
        """
        椭率角梯度有限
        """
        bundle = _normal_incidence_bundle()
        ellipticity = torch.tensor(
            math.radians(10.0),
            dtype=torch.float64,
            requires_grad=True,
        )
        output = retarder_at(
            bundle,
            surface=Plane(),
            retardance_cycles=0.25,
            retarded_eigenstate_azimuth_radians=0.0,
            retarded_eigenstate_ellipticity_radians=ellipticity,
        )
        loss = output.polarization_vector.real.sum()
        loss.backward()
        assert ellipticity.grad is not None
        assert bool(torch.isfinite(ellipticity.grad).all())

    def test_component_retardance_parameter_gradient(self) -> None:
        """
        组件 Parameter 延迟量梯度到达 leaf
        """
        bundle = _normal_incidence_bundle()
        retardance = torch.nn.Parameter(torch.tensor(0.2, dtype=torch.float64),)
        component = RetarderAt(
            surface=Plane(),
            retardance_cycles=retardance,
            retarded_eigenstate_azimuth_radians=math.radians(30.0),
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        output = component(bundle)
        loss = output.polarization_vector.real.sum()
        loss.backward()
        assert retardance.grad is not None
        assert bool(torch.isfinite(retardance.grad).all())




@cuda
class TestRetarderAtCudaParity:
    """
    CPU 与真实 CUDA 设备上同精度一致
    """

    def test_cuda_output_matches_cpu(self) -> None:
        """
        CUDA 输出与 CPU 逐位一致（同精度）
        """
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        cpu_bundle = _normal_incidence_bundle()
        cpu_output = retarder_at(
            cpu_bundle,
            surface=Plane(),
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.radians(25.0),
            retarded_eigenstate_ellipticity_radians=math.radians(7.0),
        )
        cuda_bundle = RayBundle(
            position=cpu_bundle.position.cuda(),
            direction=cpu_bundle.direction.cuda(),
            polarization_vector=cpu_bundle.polarization_vector.cuda(),
            power=cpu_bundle.power.cuda(),
            refractive_index=cpu_bundle.refractive_index.cuda(),
            optical_path=cpu_bundle.optical_path.cuda(),
            status=cpu_bundle.status.cuda(),
            spectrum=cpu_bundle.spectrum,
        )
        cuda_output = retarder_at(
            cuda_bundle,
            surface=Plane(),
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.radians(25.0),
            retarded_eigenstate_ellipticity_radians=math.radians(7.0),
        )
        assert cuda_output.polarization_vector.device.type == "cuda"
        assert torch.allclose(
            cuda_output.polarization_vector.cpu(),
            cpu_output.polarization_vector,
            atol=1.0e-12,
        )

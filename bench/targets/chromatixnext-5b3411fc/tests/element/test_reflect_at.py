
from __future__ import annotations

import inspect
import math

import pytest
import torch

from chromatix_next.errors import OpticalTypeError, OpticalValueError
from chromatix_next.optics import (
    ConstantMedium,
    Medium,
    Polarization,
    RayBundle,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics._meta_inference import _meta_inference
from chromatix_next.optics.element import ReflectAt, reflect_at
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_VIGNETTED,
)
from chromatix_next.optics.source import CollimatedRaySource
from chromatix_next.optics.surface import ConicEvenAsphere, Plane, Sphere
from tests.optics._valid_ray_inputs import _transverse_polarization_for_direction


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    # 单色光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _unit_z(real_dtype: torch.dtype = torch.float64) -> torch.Tensor:
    # 沿 +z 的单位方向
    direction = torch.zeros(3, dtype=real_dtype)
    direction[2] = 1.0
    return direction


def _bundle(
    *,
    position: torch.Tensor,
    direction: torch.Tensor,
    spectrum: Spectrum | None = None,
    medium: Medium | None = None,
    real_dtype: torch.dtype = torch.float64,
    requires_grad: bool = False,
    device: torch.device | str = "cpu",
) -> RayBundle:
    # 由显式位置/方向构造最小光线束（单光谱、单 ray 或多 ray 由调用者决定形状）
    if spectrum is None:
        spectrum = _monochromatic()
    spectrum_count = spectrum.count
    ray_count = position.shape[-2]
    position = position.to(dtype=real_dtype, device=device)
    if requires_grad:
        position.requires_grad_(True)
    direction_unit = direction.to(dtype=real_dtype, device=device)
    direction_broadcast = direction_unit.view(1, 1, 3).expand(
        spectrum_count,
        ray_count,
        3,
    )
    power = torch.ones(
        (spectrum_count, ray_count),
        dtype=real_dtype,
        device=device,
    )
    resolved_medium = medium or Vacuum()
    wavelengths = torch.tensor(
        spectrum.wavelengths,
        dtype=real_dtype,
        device=device,
    )
    indices = resolved_medium.refractive_index(wavelengths).to(real_dtype)
    refractive_index = indices.view(spectrum_count, 1).expand(
        spectrum_count,
        ray_count,
    )
    optical_path = torch.zeros(
        (spectrum_count, ray_count),
        dtype=torch.float64,
        device=device,
    )
    status = torch.full(
        (spectrum_count, ray_count),
        RAY_STATUS_ACTIVE,
        dtype=torch.uint8,
        device=device,
    )
    return RayBundle(
        position=position,
        direction=direction_broadcast,
        polarization_vector=_transverse_polarization_for_direction(
            direction_broadcast
        ),
        power=power,
        refractive_index=refractive_index,
        optical_path=optical_path,
        status=status,
        spectrum=spectrum,
    )


def _bundle_at_origin(
    *,
    direction: torch.Tensor,
    medium: Medium | None = None,
    ray_count: int = 4,
    real_dtype: torch.dtype = torch.float64,
    requires_grad: bool = False,
) -> RayBundle:
    # 位于原点、共享单位方向的最小光线束
    positions = torch.zeros(
        (1, ray_count, 3),
        dtype=real_dtype,
        requires_grad=requires_grad,
    )
    return _bundle(
        position=positions,
        direction=direction,
        medium=medium,
        real_dtype=real_dtype,
    )


def _assert_no_nan(bundle: RayBundle) -> None:
    # 三态有限性：所有张量处处有限
    assert torch.isfinite(bundle.position).all()
    assert torch.isfinite(bundle.direction).all()
    assert torch.isfinite(bundle.power).all()
    assert torch.isfinite(bundle.optical_path).all()


def _mixed_surface_bundle() -> RayBundle:
    # 构造命中、错过、既终态与孔径外四条证据通道
    positions = torch.tensor(
        [
            [0.0, 0.0, -3.0e-6],
            [0.0, 0.0, -3.0e-6],
            [0.0, 0.0, -3.0e-6],
            [3.0e-6, 0.0, -3.0e-6],
        ],
        dtype=torch.float64,
    ).unsqueeze(0)
    directions = torch.tensor(
        [
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=torch.float64,
    ).unsqueeze(0)
    statuses = torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8)
    statuses[0, 2] = RAY_STATUS_VIGNETTED
    optical_path = torch.zeros((1, 4), dtype=torch.float64)
    optical_path[0, 3] = 0.25
    return RayBundle(
        position=positions,
        direction=directions,
        polarization_vector=_transverse_polarization_for_direction(directions),
        power=torch.ones((1, 4), dtype=torch.float64),
        refractive_index=torch.full((1, 4), 1.3, dtype=torch.float64),
        optical_path=optical_path,
        status=statuses,
        spectrum=_monochromatic(),
    )


def _analytic_reflect(
    direction: torch.Tensor,
    normal: torch.Tensor,
) -> torch.Tensor:
    # 独立解析的向量反射律 d_r = d − 2(d·n̂)n̂；与生产核分开实现
    cos_incident = (direction * normal).sum(dim=-1)
    return direction - (2.0 * cos_incident).unsqueeze(-1) * normal


def _analytic_sphere_distance(
    origin: torch.Tensor,
    direction: torch.Tensor,
    center: torch.Tensor,
    radius: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    # 独立解析的 ray-sphere 最近正向距离、交点与外法线（指向入射介质侧）
    offset = origin - center
    b = (offset * direction).sum(dim=-1)
    c = (offset * offset).sum(dim=-1) - radius * radius
    disc = b * b - c
    sqrt_disc = torch.sqrt(torch.clamp(disc, min=0.0))
    near = -b - sqrt_disc
    far = -b + sqrt_disc
    distance = torch.where(near >= 0, near, far)
    intersection = origin + distance.unsqueeze(-1) * direction
    normal = (intersection - center) / radius
    cos_to_ray = (direction * normal).sum(dim=-1)
    normal = torch.where(
        (cos_to_ray > 0).unsqueeze(-1),
        -normal,
        normal,
    )
    return distance, intersection, normal


class TestReflectAtRoleAndErrorIdentity:
    """
    配对接口的元件角色契约与稳定错误身份
    """

    @pytest.mark.parametrize(
        "surface",
        (
            Plane(origin=(0.0, 0.0, 1.0e-6)),
            Sphere(radius_of_curvature=5.0e-6),
        ),
    )
    def test_role_is_element_literal(self, surface: Plane | Sphere) -> None:
        """
        ReflectAt 声明唯一不可改写的 element 角色
        """

        component = ReflectAt(surface=surface)
        assert component.role == "element"
        with pytest.raises(AttributeError):
            component.role = "propagation"  # type: ignore[misc]

    def test_forward_returns_ray_bundle(self) -> None:
        """
        真实前向只产生 RayBundle 强物理值
        """

        component = ReflectAt(
            surface=Plane(origin=(0.0, 0.0, 1.0e-6)),
        )
        bundle = component(_bundle_at_origin(direction=_unit_z()))
        assert isinstance(bundle, RayBundle)

    def test_reflect_at_signature_omits_destination_medium(self) -> None:
        """
        reflect_at 不接收目标介质：反射留入射介质，与 refract_at 签名区别
        """

        signature = inspect.signature(reflect_at)
        assert "surface" in signature.parameters
        assert "destination_medium" not in signature.parameters

    def test_reflect_at_rejects_unsupported_surface(self) -> None:
        """
        reflect_at 只接受 Plane 与 Sphere；其他对象类型拒绝（稳定错误身份）
        """

        bundle = _bundle_at_origin(direction=_unit_z())
        with pytest.raises(OpticalTypeError) as rejected:
            reflect_at(
                bundle,
                surface=object(),  # type: ignore[arg-type]
            )
        assert rejected.value.identity == "reflect_at_surface_invalid"

    def test_reflect_at_rejects_non_bundle_input(self) -> None:
        """
        reflect_at 只能作用于 RayBundle；其他类型拒绝
        """

        with pytest.raises(OpticalTypeError) as rejected:
            reflect_at(
                object(),  # type: ignore[arg-type]
                surface=Plane(),
            )
        assert rejected.value.identity == "reflect_at_bundle_invalid"


class TestPlaneReflectionAnalytic:
    """
    平面反射的独立解析锚点：正入射、斜入射、可逆、未命中、孔径遮挡
    """

    def test_normal_incidence_flips_direction(self) -> None:
        """
        正入射（ray 沿面法线）⇒ 方向严格翻转，位置前进到交点
        """

        axial_distance = 1.5e-6
        positions = torch.tensor(
            [[0.0, 0.0, 0.0]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        plane = Plane(origin=(0.0, 0.0, axial_distance))
        reflected = reflect_at(bundle, surface=plane)
        expected_direction = torch.tensor(
            [[0.0, 0.0, -1.0]],
            dtype=torch.float64,
        ).unsqueeze(0)
        assert torch.allclose(
            reflected.direction,
            expected_direction,
            atol=1.0e-12,
        )
        assert torch.allclose(
            reflected.position[..., 2],
            torch.tensor(axial_distance, dtype=torch.float64),
        )
        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        _assert_no_nan(reflected)

    def test_oblique_direction_matches_analytic_law(self) -> None:
        """
        斜入射：反射方向与独立解析 d_r = d − 2(d·n̂)n̂ 一致
        """

        theta = math.radians(25.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.zeros((1, 3), dtype=torch.float64).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        plane = Plane(origin=(0.0, 0.0, 2.0e-6))
        reflected = reflect_at(bundle, surface=plane)
        expected = _analytic_reflect(direction, plane.normal)
        assert torch.allclose(
            reflected.direction[0, 0],
            expected,
            atol=1.0e-12,
        )
        _assert_no_nan(reflected)

    def test_reflection_is_involution_at_plane(self) -> None:
        """
        反射律可逆：对同一法线再施加一次反射律恢复原方向
        """

        theta = math.radians(35.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        plane = Plane(origin=(0.0, 0.0, 2.0e-6))
        once = _analytic_reflect(direction, plane.normal)
        twice = _analytic_reflect(once, plane.normal)
        assert torch.allclose(twice, direction, atol=1.0e-12)

    def test_parallel_ray_marked_missed(self) -> None:
        """
        沿 +x 的 ray 与 z=d 平面不相交 ⇒ 全部 missed，保留原位/方向/光程
        """

        along_x = torch.tensor([1.0, 0.0, 0.0])
        bundle = _bundle_at_origin(direction=along_x)
        plane = Plane(origin=(0.0, 0.0, 1.0e-6))
        reflected = reflect_at(bundle, surface=plane)
        assert torch.equal(
            reflected.status,
            torch.full_like(reflected.status, RAY_STATUS_SURFACE_MISSED),
        )
        assert torch.equal(reflected.position, bundle.position)
        assert torch.equal(reflected.direction, bundle.direction)
        assert torch.equal(reflected.optical_path, bundle.optical_path)
        _assert_no_nan(reflected)

    def test_aperture_boundary_splits_active_and_vignetted(self) -> None:
        """
        圆形 aperture：径向在内 ⇒ active；在外 ⇒ vignetted；边界分段，不声称导数
        """

        radius = 1.0e-6
        positions = torch.tensor(
            [[0.5e-6, 0.0, 0.0], [2.0e-6, 0.0, 0.0]],
            dtype=torch.float64,
        ).unsqueeze(0)
        direction = _unit_z().view(1, 1, 3).expand(1, 2, 3)
        bundle = RayBundle(
            position=positions,
            direction=direction,
            polarization_vector=_transverse_polarization_for_direction(
                direction
            ),
            power=torch.ones((1, 2), dtype=torch.float64),
            refractive_index=torch.ones((1, 2), dtype=torch.float64),
            optical_path=torch.zeros((1, 2), dtype=torch.float64),
            status=torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        plane = Plane(
            origin=(0.0, 0.0, 1.0e-6),
            clear_aperture_radius=radius,
        )
        reflected = reflect_at(bundle, surface=plane)
        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        assert reflected.status[0, 1] == RAY_STATUS_VIGNETTED
        # vignetted ray 仍前进到孔径平面交点（有限 last position）
        assert torch.isclose(
            reflected.position[0, 1, 2],
            torch.tensor(1.0e-6, dtype=torch.float64),
            atol=1.0e-12,
        )
        _assert_no_nan(reflected)


class TestAuthoredBudgetPlaneAdmissionClosure:
    """
    ADR-0010 admission promise：authored 8γ₃ 预算内的 Plane 切向量必须被
    reflect_at 完整接纳，不得在输出方向单位性验收处以不相关容差失败
    """

    def test_authored_budget_tangents_reflect_without_not_unit_rejection(
        self,
    ) -> None:
        """
        复核反例：|a²−1| ≈ 2.66e-15 ≤ 8γ₃ 被 Plane 验收接受，45° 入射经
        reflect_at 反射后不抛 ``ray_bundle_direction_not_unit`` 且结果有限
        """

        # a = 1.0000000000000013：a² 的 squared-norm 残差落在 authored 预算内
        a = 1.0000000000000013
        plane = Plane(
            tangent_x=(a, 0.0, 0.0),
            tangent_y=(0.0, a, 0.0),
        )
        diagonal = math.sqrt(0.5)
        direction = torch.tensor(
            [diagonal, 0.0, diagonal],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -2.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        reflected = reflect_at(bundle, surface=plane)
        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        assert bool(torch.isfinite(reflected.position).all())
        assert bool(torch.isfinite(reflected.direction).all())
        # 45° 入射对归一化法线 (0,0,1) 的解析反射律：z 分量翻转
        expected_direction = torch.tensor(
            [[diagonal, 0.0, -diagonal]],
            dtype=torch.float64,
        ).unsqueeze(0)
        assert torch.allclose(
            reflected.direction,
            expected_direction,
            atol=1.0e-12,
        )
        _assert_no_nan(reflected)


class TestSphereReflectionAnalytic:
    """
    球面反射的独立解析锚点：凸/凹两种曲率符号、正/斜入射、近切线、未命中
    """

    def test_convex_normal_incidence_flips(self) -> None:
        """
        凸面（R>0）正入射：反射方向严格翻转，位置到达顶点
        """

        radius = 5.0e-6
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(radius_of_curvature=radius)
        reflected = reflect_at(bundle, surface=sphere)
        expected = torch.tensor(
            [[0.0, 0.0, -1.0]],
            dtype=torch.float64,
        ).unsqueeze(0)
        assert torch.allclose(reflected.direction, expected, atol=1.0e-12)
        assert torch.allclose(
            reflected.position[..., 2],
            torch.tensor(0.0, dtype=torch.float64),
            atol=1.0e-12,
        )
        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        _assert_no_nan(reflected)

    def test_concave_normal_incidence_flips(self) -> None:
        """
        凹面（R<0）正入射：ray 起点在球内 ⇒ far_root 命中顶点侧；方向翻转
        """

        radius = -5.0e-6
        positions = torch.tensor(
            [[0.0, 0.0, -2.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(radius_of_curvature=radius)
        reflected = reflect_at(bundle, surface=sphere)
        expected = torch.tensor(
            [[0.0, 0.0, -1.0]],
            dtype=torch.float64,
        ).unsqueeze(0)
        assert torch.allclose(reflected.direction, expected, atol=1.0e-12)
        _assert_no_nan(reflected)

    def test_oblique_matches_analytic_law(self) -> None:
        """
        斜入射：交点、法线、反射方向与独立解析一致
        """

        radius = 5.0e-6
        center = torch.tensor(
            [0.0, 0.0, radius],
            dtype=torch.float64,
        )
        theta = math.radians(20.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        sphere = Sphere(radius_of_curvature=radius)
        reflected = reflect_at(bundle, surface=sphere)
        expected_distance, expected_point, expected_normal = (
            _analytic_sphere_distance(
                positions,
                direction,
                center,
                radius,
            )
        )
        assert torch.allclose(
            reflected.position,
            expected_point,
            atol=1.0e-12,
        )
        expected_direction = _analytic_reflect(direction, expected_normal[0, 0])
        assert torch.allclose(
            reflected.direction[0, 0],
            expected_direction,
            atol=1.0e-12,
        )
        assert torch.allclose(
            reflected.optical_path,
            expected_distance.to(torch.float64),
            atol=1.0e-18,
        )
        _assert_no_nan(reflected)

    def test_near_tangent_remains_stable(self) -> None:
        """
        近切线（判别式近零）：交点有限、不发散，状态 active
        """

        radius = 5.0e-6
        delta = 1.0e-9
        start = torch.tensor(
            [radius - delta, 0.0, -2.0 * radius],
            dtype=torch.float64,
        )
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(
            vertex=(0.0, 0.0, -radius),
            radius_of_curvature=radius,
        )
        reflected = reflect_at(bundle, surface=sphere)
        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        assert torch.isfinite(reflected.position).all()
        assert torch.isfinite(reflected.direction).all()

    def test_missed_ray_retains_last_state(self) -> None:
        """
        未命中（判别式 < 0）：保留原位/方向/光程/介质，状态 SURFACE_MISSED
        """

        radius = 1.0e-6
        start = torch.tensor(
            [5.0e-6, 0.0, -2.0e-6],
            dtype=torch.float64,
        )
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(radius_of_curvature=radius)
        reflected = reflect_at(bundle, surface=sphere)
        assert reflected.status[0, 0] == RAY_STATUS_SURFACE_MISSED
        assert torch.equal(reflected.position, bundle.position)
        assert torch.equal(reflected.direction, bundle.direction)
        assert torch.equal(reflected.optical_path, bundle.optical_path)
        # 反射不换介质：missed 光线精确保留入射 per-ray 折射率
        assert torch.equal(reflected.refractive_index, bundle.refractive_index)
        _assert_no_nan(reflected)


class TestReflectionLawInvariants:
    """
    反射律不变量：单位长度、法线符号不敏感、功率不变、介质保留
    """

    @pytest.mark.parametrize(
        "surface",
        (
            Plane(origin=(0.0, 0.0, 2.0e-6)),
            Sphere(radius_of_curvature=5.0e-6),
        ),
    )
    def test_reflected_direction_is_unit_norm(
        self,
        surface: Plane | Sphere,
    ) -> None:
        """
        Householder 构造保单位：反射后方向逐条仍为单位向量
        """

        theta = math.radians(22.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        reflected = reflect_at(bundle, surface=surface)
        norms = torch.linalg.norm(reflected.direction[0, 0], dim=-1)
        assert torch.isclose(
            norms,
            torch.ones_like(norms),
            atol=1.0e-9,
        )

    def test_reflection_insensitive_to_normal_sign(self) -> None:
        """
        反射律对法线符号不变：n̂ 与 −n̂ 给同一 d_r（consistent normal orientation）
        """

        theta = math.radians(18.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        normal = torch.tensor([0.0, 0.0, 1.0], dtype=torch.float64)
        reflected_with_positive = _analytic_reflect(direction, normal)
        reflected_with_negative = _analytic_reflect(direction, -normal)
        assert torch.allclose(
            reflected_with_positive,
            reflected_with_negative,
            atol=1.0e-12,
        )

    def test_power_unchanged_across_reflection(self) -> None:
        """
        理想几何反射不发明 Fresnel：成功光线功率不变
        """

        radius = 5.0e-6
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(radius_of_curvature=radius)
        reflected = reflect_at(bundle, surface=sphere)
        assert torch.equal(reflected.power, bundle.power)

    def test_medium_preserved_on_active_reflection(self) -> None:
        """
        反射留入射介质：输出 Medium 与入射 Medium 同一对象（无介质切换）
        """

        incident = ConstantMedium(index=1.3)
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z(), medium=incident)
        sphere = Sphere(radius_of_curvature=5.0e-6)
        reflected = reflect_at(bundle, surface=sphere)
        # 反射留入射介质：per-ray 折射率逐元素保持入射评估值（1.3）
        assert torch.equal(reflected.refractive_index, bundle.refractive_index)
        assert torch.allclose(
            reflected.refractive_index,
            torch.full_like(reflected.refractive_index, 1.3),
        )


class TestReflectionOpticalPath:
    """
    光程按入射介质 n × 几何距离累加；float64 graph-bearing
    """

    @pytest.mark.parametrize(
        ("index", "expected_factor"),
        ((1.0, 1.0), (1.3, 1.3), (1.5, 1.5)),
    )
    def test_optical_path_accumulates_incident_index_times_distance(
        self,
        index: float,
        expected_factor: float,
    ) -> None:
        """
        OP += n_incident × distance；反射用入射介质 n（不换介质）
        """

        axial_distance = 2.0e-6
        positions = torch.zeros((1, 1, 3), dtype=torch.float64)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=index),
        )
        plane = Plane(origin=(0.0, 0.0, axial_distance))
        reflected = reflect_at(bundle, surface=plane)
        assert reflected.optical_path.dtype is torch.float64
        expected = torch.full(
            (1, 1),
            expected_factor * axial_distance,
            dtype=torch.float64,
        )
        assert torch.allclose(
            reflected.optical_path,
            expected,
            atol=1.0e-18,
        )

    def test_optical_path_graph_bears_trainable_spacing(self) -> None:
        """
        可训练姿态（origin.z 为 Parameter）的光程保持 autograd 计算图
        """

        origin = torch.nn.Parameter(
            torch.tensor([0.0, 0.0, 2.0e-6], dtype=torch.float64),
        )
        positions = torch.zeros((1, 1, 3), dtype=torch.float64)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=1.5),
        )
        plane = Plane(origin=origin)
        reflected = reflect_at(bundle, surface=plane)
        reflected.optical_path.sum().backward()
        assert origin.grad is not None
        assert torch.isclose(
            origin.grad[2],
            torch.tensor(1.5, dtype=torch.float64),
        )

    def test_optical_path_graph_bears_trainable_curvature(self) -> None:
        """
        可训练球面曲率半径的光程保持 autograd 图
        """

        radius_param = torch.nn.Parameter(
            torch.tensor(5.0e-6, dtype=torch.float64),
        )
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=1.5),
        )
        sphere = Sphere(radius_of_curvature=radius_param)
        reflected = reflect_at(bundle, surface=sphere)
        reflected.optical_path.sum().backward()
        assert radius_param.grad is not None


class TestReflectAtFunctionComponentDuality:
    """
    reflect_at 与 ReflectAt 行为完全一致；Source→ReflectAt 链路产出 RayBundle
    """

    @pytest.mark.parametrize(
        "surface",
        (
            Plane(origin=(0.0, 0.0, 2.0e-6)),
            Sphere(radius_of_curvature=5.0e-6),
        ),
    )
    def test_function_and_component_agree(
        self,
        surface: Plane | Sphere,
    ) -> None:
        """
        同一入射 bundle、同一面：function 与 component 输出逐元素一致
        """

        theta = math.radians(15.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        component = ReflectAt(surface=surface)
        function_output = reflect_at(bundle, surface=surface)
        component_output = component(bundle)
        assert torch.equal(function_output.position, component_output.position)
        assert torch.equal(function_output.direction, component_output.direction)
        assert torch.equal(
            function_output.optical_path,
            component_output.optical_path,
        )
        assert torch.equal(function_output.status, component_output.status)

    def test_reflect_at_consumes_authored_ray_bundle(self) -> None:
        """
        准直光源产出的光线束可直接进入 ``ReflectAt`` 反射动作
        """

        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        from chromatix_next.optics import SpatialGrid

        launch_grid = SpatialGrid.centered(
            sample_counts=(3, 3),
            sample_spacing=(0.4e-6, 0.4e-6),
        )
        bundle = source(launch_grid)
        sphere = Sphere(
            vertex=(0.0, 0.0, 5.0e-6),
            radius_of_curvature=5.0e-6,
        )
        reflected = reflect_at(bundle, surface=sphere)
        assert reflected.position.shape == bundle.position.shape
        # 反射留入射介质：per-ray 折射率逐元素保持入射评估值
        assert torch.equal(reflected.refractive_index, bundle.refractive_index)


class TestReflectionStatusPropagation:
    """
    inactive ray 不再参与；三态（active/missed/vignetted）同 bundle 可诊断
    """

    def test_inactive_ray_retains_last_state(self) -> None:
        """
        已终止的 ray 再次反射不前进、不改状态、不累加光程
        """

        positions = torch.zeros((1, 2, 3), dtype=torch.float64)
        positions[0, 1, 0] = 5.0e-6
        direction = _unit_z().view(1, 1, 3).expand(1, 2, 3)
        status = torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8)
        status[0, 1] = RAY_STATUS_VIGNETTED
        bundle = RayBundle(
            position=positions,
            direction=direction,
            polarization_vector=_transverse_polarization_for_direction(
                direction
            ),
            power=torch.ones((1, 2), dtype=torch.float64),
            refractive_index=torch.ones((1, 2), dtype=torch.float64),
            optical_path=torch.full((1, 2), 0.7, dtype=torch.float64),
            status=status,
            spectrum=_monochromatic(),
        )
        sphere = Sphere(radius_of_curvature=5.0e-6)
        reflected = reflect_at(bundle, surface=sphere)
        assert reflected.status[0, 1] == RAY_STATUS_VIGNETTED
        assert torch.equal(reflected.position[0, 1], positions[0, 1])
        assert torch.isclose(
            reflected.optical_path[0, 1],
            torch.tensor(0.7, dtype=torch.float64),
        )

    def test_three_terminal_states_distinguishable(self) -> None:
        """
        active/missed/vignetted 三态在同一 bundle 内可同时诊断（平面 + 球面各一例）
        """

        radius = 5.0e-6
        aperture = 4.5e-6
        positions = torch.zeros((3, 3), dtype=torch.float64).unsqueeze(0)
        positions[0, 0] = torch.tensor([0.0, 0.0, -3.0e-6])
        positions[0, 1] = torch.tensor([8.0e-6, 0.0, -3.0e-6])
        positions[0, 2] = torch.tensor([4.8e-6, 0.0, -3.0e-6])
        directions = _unit_z().view(1, 1, 3).expand(1, 3, 3)
        bundle = RayBundle(
            position=positions,
            direction=directions,
            polarization_vector=_transverse_polarization_for_direction(
                directions
            ),
            power=torch.ones((1, 3), dtype=torch.float64),
            refractive_index=torch.ones((1, 3), dtype=torch.float64),
            optical_path=torch.zeros((1, 3), dtype=torch.float64),
            status=torch.full((1, 3), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        sphere = Sphere(
            vertex=(0.0, 0.0, 0.0),
            radius_of_curvature=radius,
            clear_aperture_radius=aperture,
        )
        reflected = reflect_at(bundle, surface=sphere)
        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        assert reflected.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert reflected.status[0, 2] == RAY_STATUS_VIGNETTED
        _assert_no_nan(reflected)


class TestReflectAtSurfaceIntegration:
    """
    三类公共表面各自承载反射动作的复合证据
    """

    @pytest.mark.parametrize(
        "surface",
        (
            Plane(clear_aperture_radius=2.0e-6),
            Sphere(
                radius_of_curvature=5.0e-6,
                clear_aperture_radius=2.0e-6,
            ),
            ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=0.0,
                clear_aperture_radius=2.0e-6,
            ),
        ),
        ids=("plane", "sphere", "conic"),
    )
    def test_hit_miss_terminal_and_action_invariants(
        self,
        surface: Plane | Sphere | ConicEvenAsphere,
    ) -> None:
        """
        每类表面均保留推进状态，且只对命中光线施加反射
        """

        bundle = _mixed_surface_bundle()
        reflected = reflect_at(bundle, surface=surface)

        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        assert torch.allclose(
            reflected.position[0, 0],
            torch.zeros(3, dtype=torch.float64),
            atol=1.0e-12,
        )
        assert torch.allclose(
            reflected.direction[0, 0],
            torch.tensor([0.0, 0.0, -1.0], dtype=torch.float64),
            atol=1.0e-12,
        )
        assert torch.isclose(
            reflected.optical_path[0, 0],
            torch.tensor(1.3 * 3.0e-6, dtype=torch.float64),
            atol=1.0e-15,
        )
        assert reflected.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert torch.equal(reflected.position[0, 1], bundle.position[0, 1])
        assert torch.equal(reflected.direction[0, 1], bundle.direction[0, 1])
        assert torch.equal(
            reflected.polarization_vector[0, 1],
            bundle.polarization_vector[0, 1],
        )
        assert torch.equal(reflected.power[0, 1], bundle.power[0, 1])
        assert torch.equal(
            reflected.refractive_index[0, 1],
            bundle.refractive_index[0, 1],
        )
        assert torch.equal(
            reflected.optical_path[0, 1],
            bundle.optical_path[0, 1],
        )
        assert torch.equal(reflected.position[0, 2], bundle.position[0, 2])
        assert torch.equal(reflected.direction[0, 2], bundle.direction[0, 2])
        assert torch.equal(
            reflected.polarization_vector[0, 2],
            bundle.polarization_vector[0, 2],
        )
        assert torch.equal(reflected.power[0, 2], bundle.power[0, 2])
        assert torch.equal(
            reflected.refractive_index[0, 2],
            bundle.refractive_index[0, 2],
        )
        assert torch.equal(
            reflected.optical_path[0, 2],
            bundle.optical_path[0, 2],
        )
        assert reflected.status[0, 2] == RAY_STATUS_VIGNETTED
        assert torch.equal(reflected.power, bundle.power)
        assert torch.equal(reflected.refractive_index, bundle.refractive_index)
        _assert_no_nan(reflected)

        if isinstance(surface, Plane):
            assert reflected.status[0, 3] == RAY_STATUS_VIGNETTED
            assert torch.allclose(
                reflected.position[0, 3],
                torch.tensor([3.0e-6, 0.0, 0.0], dtype=torch.float64),
                atol=1.0e-12,
            )
            assert torch.isclose(
                reflected.optical_path[0, 3],
                bundle.optical_path[0, 3]
                + bundle.refractive_index[0, 3]
                * torch.tensor(3.0e-6, dtype=torch.float64),
                atol=1.0e-15,
            )
            assert (
                reflected.refractive_index[0, 3]
                == bundle.refractive_index[0, 3]
            )
            assert reflected.power[0, 3] == bundle.power[0, 3]
            assert torch.equal(
                reflected.direction[0, 3],
                bundle.direction[0, 3],
            )
            assert torch.equal(
                reflected.polarization_vector[0, 3],
                bundle.polarization_vector[0, 3],
            )


class TestReflectionGradient:
    """
    smooth 路径的 autograd 与中心差分一致；边界显式声明分段
    """

    def test_launch_position_gradient_matches_central_difference(self) -> None:
        """
        可训练 launch x：交点 x 的解析导数与中心差分一致（平面）
        """

        axial_distance = 2.0e-6

        def _intersection_x(launch_x_value: float) -> float:
            # 中心差分参考：给定 launch x，返回反射后交点 x 的标量值
            origin = torch.nn.Parameter(
                torch.tensor(
                    [launch_x_value, 0.0, 0.0],
                    dtype=torch.float64,
                ),
            )
            bundle = _bundle(position=origin.view(1, 1, 3), direction=_unit_z())
            plane = Plane(origin=(0.0, 0.0, axial_distance))
            reflected = reflect_at(bundle, surface=plane)
            return float(reflected.position[0, 0, 0].detach())

        launch = torch.nn.Parameter(
            torch.tensor([0.3e-6, 0.0, 0.0], dtype=torch.float64),
        )
        bundle = _bundle(position=launch.view(1, 1, 3), direction=_unit_z())
        plane = Plane(origin=(0.0, 0.0, axial_distance))
        reflected = reflect_at(bundle, surface=plane)
        reflected.position[0, 0, 0].backward()
        assert launch.grad is not None
        autograd = float(launch.grad[0].detach())
        step = 1.0e-9
        central = (
            _intersection_x(0.3e-6 + step) - _intersection_x(0.3e-6 - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-5, abs_tol=1.0e-7)

    def test_curvature_gradient_matches_central_difference(self) -> None:
        """
        可训练曲率半径：反射方向的解析导数与中心差分一致（球面，远离根切换）
        """

        theta = math.radians(15.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)

        def _direction_x(radius_value: float) -> float:
            # 中心差分参考：给定曲率半径，返回反射后方向 x 分量的标量值
            radius_param = torch.nn.Parameter(
                torch.tensor(radius_value, dtype=torch.float64),
            )
            bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
            sphere = Sphere(radius_of_curvature=radius_param)
            reflected = reflect_at(bundle, surface=sphere)
            return float(reflected.direction[0, 0, 0].detach())

        radius_param = torch.nn.Parameter(
            torch.tensor(5.0e-6, dtype=torch.float64),
        )
        bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
        component = ReflectAt(surface=Sphere(radius_of_curvature=radius_param))
        reflected = component(bundle)
        reflected.direction[0, 0, 0].backward()
        assert radius_param.grad is not None
        autograd = float(radius_param.grad.detach())
        step = 1.0e-11
        central = (
            _direction_x(5.0e-6 + step) - _direction_x(5.0e-6 - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e-2)

    def test_aperture_boundary_is_piecewise_non_differentiable(self) -> None:
        """
        aperture 边界两侧 status 从 active 翻转为 vignetted；不声称跨边界连续导数
        """

        radius = 1.0e-6
        positions = torch.tensor(
            [[0.9e-6, 0.0, 0.0], [1.1e-6, 0.0, 0.0]],
            dtype=torch.float64,
        ).unsqueeze(0)
        direction = _unit_z().view(1, 1, 3).expand(1, 2, 3)
        bundle = RayBundle(
            position=positions,
            direction=direction,
            polarization_vector=_transverse_polarization_for_direction(
                direction
            ),
            power=torch.ones((1, 2), dtype=torch.float64),
            refractive_index=torch.ones((1, 2), dtype=torch.float64),
            optical_path=torch.zeros((1, 2), dtype=torch.float64),
            status=torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        plane = Plane(
            origin=(0.0, 0.0, 1.0e-6),
            clear_aperture_radius=radius,
        )
        reflected = reflect_at(bundle, surface=plane)
        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        assert reflected.status[0, 1] == RAY_STATUS_VIGNETTED


class TestReflectionDevicePlacement:
    """
    设备放置同 meta/real 模式一致
    """

    def test_real_dtype_propagated_to_state(self) -> None:
        """
        输出的位置、方向、功率固定为 float64
        """

        real_dtype = torch.float64
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=real_dtype,
        ).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(real_dtype),
            real_dtype=real_dtype,
        )
        sphere = Sphere(radius_of_curvature=5.0e-6)
        reflected = reflect_at(bundle, surface=sphere)
        assert reflected.position.dtype is real_dtype
        assert reflected.direction.dtype is real_dtype
        assert reflected.power.dtype is real_dtype
        assert reflected.optical_path.dtype is torch.float64
        assert reflected.status.dtype is torch.uint8

    def test_meta_forward_preserves_shape_and_dtype(self) -> None:
        """
        meta 设备上前向返回同形同 dtype RayBundle（供 Workstation 预检推导）
        """

        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        from chromatix_next.optics import SpatialGrid

        grid = SpatialGrid.centered(
            sample_counts=(2, 2),
            sample_spacing=(1.0e-6, 1.0e-6),
        )
        reflect = ReflectAt(surface=Sphere(radius_of_curvature=5.0e-6))
        with _meta_inference((source, reflect)) as sandbox:
            bundle = sandbox.module(source)(grid)
            reflected = sandbox.module(reflect)(bundle)
        assert reflected.position.is_meta
        assert reflected.position.dtype is torch.float64
        assert reflected.optical_path.dtype is torch.float64
        assert reflected.status.dtype is torch.uint8


class TestReflectionImmutability:
    """
    reflect_at 不修改输入 RayBundle（不可变物理值）
    """

    def test_input_bundle_tensors_unchanged(self) -> None:
        """
        reflect_at 返回新对象；输入张量不被修改
        """

        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        original_position = bundle.position.clone()
        original_direction = bundle.direction.clone()
        original_optical_path = bundle.optical_path.clone()
        sphere = Sphere(radius_of_curvature=5.0e-6)
        reflected = reflect_at(bundle, surface=sphere)
        assert reflected is not bundle
        assert torch.equal(bundle.position, original_position)
        assert torch.equal(bundle.direction, original_direction)
        assert torch.equal(bundle.optical_path, original_optical_path)


class TestConicEvenAsphereReflection:
    """
    reflect_at/ReflectAt 在 ConicEvenAsphere 上的证据：球面极限反射方向一致、单位
    长度、功率不变、function/component duality、可训练曲率梯度、meta/real schema
    """

    def test_spherical_limit_matches_sphere_reflection(self) -> None:
        """
        k=0/α=0 退化球面：圆锥反射方向与等价 Sphere 一致
        """

        radius = 5.0e-6
        theta = math.radians(20.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        sphere = Sphere(radius_of_curvature=radius)
        conic = ConicEvenAsphere(
            curvature=1.0 / radius,
            conic_constant=0.0,
        )
        sphere_reflected = reflect_at(bundle, surface=sphere)
        conic_reflected = reflect_at(bundle, surface=conic)
        assert torch.allclose(
            sphere_reflected.direction,
            conic_reflected.direction,
            atol=1.0e-12,
        )
        _assert_no_nan(conic_reflected)

    def test_reflected_direction_is_unit_norm_on_conic(self) -> None:
        """
        斜入射非球面：反射后方向逐条仍为单位向量（Householder 构造保单位）
        """

        radius = 5.0e-6
        theta = math.radians(22.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.4e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        conic = ConicEvenAsphere(
            curvature=1.0 / radius,
            conic_constant=-0.7,
            even_coefficients=(1.0e3,),

        clear_aperture_radius=5.0e-6,)
        reflected = reflect_at(bundle, surface=conic)
        norms = torch.linalg.norm(reflected.direction[0, 0], dim=-1)
        assert torch.isclose(
            norms,
            torch.ones_like(norms),
            atol=1.0e-9,
        )

    def test_power_unchanged_across_conic_reflection(self) -> None:
        """
        圆锥反射功率不变（不发明 Fresnel）
        """

        radius = 5.0e-6
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        conic = ConicEvenAsphere(curvature=1.0 / radius, conic_constant=0.0)
        reflected = reflect_at(bundle, surface=conic)
        assert torch.equal(reflected.power, bundle.power)

    def test_function_component_duality_on_conic(self) -> None:
        """
        reflect_at 函数与 ReflectAt 组件在圆锥面上输出完全一致
        """

        radius = 6.0e-6
        theta = math.radians(15.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.2e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        conic = ConicEvenAsphere(
            curvature=1.0 / radius,
            conic_constant=0.4,
            even_coefficients=(1.2e3,),

        clear_aperture_radius=5.0e-6,)
        component = ReflectAt(surface=conic)
        function_output = reflect_at(bundle, surface=conic)
        component_output = component(bundle)
        assert torch.equal(function_output.position, component_output.position)
        assert torch.equal(function_output.direction, component_output.direction)
        assert torch.equal(
            function_output.optical_path,
            component_output.optical_path,
        )
        assert torch.equal(function_output.status, component_output.status)

    def test_curvature_gradient_matches_central_difference(self) -> None:
        """
        可训练曲率：反射方向 x 分量的 autograd 与中心差分一致（远离根切换）
        """

        theta = math.radians(15.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)

        def direction_x(curvature_value: float) -> float:
            """
            给定曲率返回反射后方向 x 分量的中心差分参考
            """
            curvature_param = torch.nn.Parameter(
                torch.tensor(curvature_value, dtype=torch.float64),
            )
            conic = ConicEvenAsphere(curvature=curvature_param)
            bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
            reflected = reflect_at(bundle, surface=conic)
            return float(reflected.direction[0, 0, 0].detach())

        curvature_param = torch.nn.Parameter(
            torch.tensor(1.0 / 5.0e-6, dtype=torch.float64),
        )
        bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
        component = ReflectAt(
            surface=ConicEvenAsphere(curvature=curvature_param),
        )
        reflected = component(bundle)
        reflected.direction[0, 0, 0].backward()
        assert curvature_param.grad is not None
        autograd = float(curvature_param.grad.detach())
        step = 1.0
        base = 1.0 / 5.0e-6
        central = (direction_x(base + step) - direction_x(base - step)) / (
            2.0 * step
        )
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e2)

    def test_conic_constant_gradient_matches_central_difference(self) -> None:
        """
        可训练圆锥常数：反射方向 x 分量的 autograd 与中心差分一致（远离根切换）
        """

        theta = math.radians(15.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        base_conic_constant = -0.3
        step = 0.1

        def direction_x(conic_constant_value: float) -> float:
            """
            给定圆锥常数返回反射后方向 x 分量的中心差分参考
            """
            conic = ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=torch.nn.Parameter(
                    torch.tensor(conic_constant_value, dtype=torch.float64),
                ),
            )
            bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
            reflected = reflect_at(bundle, surface=conic)
            return float(reflected.direction[0, 0, 0].detach())

        conic_constant_param = torch.nn.Parameter(
            torch.tensor(base_conic_constant, dtype=torch.float64),
        )
        bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
        component = ReflectAt(
            surface=ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=conic_constant_param,
            ),
        )
        reflected = component(bundle)
        reflected.direction[0, 0, 0].backward()
        assert conic_constant_param.grad is not None
        autograd = float(conic_constant_param.grad.detach())
        central = (
            direction_x(base_conic_constant + step)
            - direction_x(base_conic_constant - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e-10)

    def test_even_coefficients_gradient_matches_central_difference(self) -> None:
        """
        可训练偶次系数：反射方向 x 分量的 autograd 与中心差分一致（远离根切换）
        """

        theta = math.radians(15.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        base_coefficient = 2.0e3
        step = 1.0e3

        def direction_x(coefficient_value: float) -> float:
            """
            给定偶次系数返回反射后方向 x 分量的中心差分参考
            """
            conic = ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                even_coefficients=torch.nn.Parameter(
                    torch.tensor([coefficient_value], dtype=torch.float64),
                ),

            clear_aperture_radius=5.0e-6,)
            bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
            reflected = reflect_at(bundle, surface=conic)
            return float(reflected.direction[0, 0, 0].detach())

        coefficient_param = torch.nn.Parameter(
            torch.tensor([base_coefficient], dtype=torch.float64),
        )
        bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
        component = ReflectAt(
            surface=ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                even_coefficients=coefficient_param,

            clear_aperture_radius=5.0e-6,),
        )
        reflected = component(bundle)
        reflected.direction[0, 0, 0].backward()
        assert coefficient_param.grad is not None
        autograd = float(coefficient_param.grad[0].detach())
        central = (
            direction_x(base_coefficient + step)
            - direction_x(base_coefficient - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e-10)

    def test_meta_forward_preserves_shape_and_dtype(self) -> None:
        """
        meta 设备上前向返回同形同 dtype RayBundle（迭代计算下 schema 仍一致）
        """

        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        from chromatix_next.optics import SpatialGrid

        grid = SpatialGrid.centered(
            sample_counts=(2, 2),
            sample_spacing=(1.0e-6, 1.0e-6),
        )
        reflect = ReflectAt(
            surface=ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=-0.5,
            ),
        )
        with _meta_inference((source, reflect)) as sandbox:
            bundle = sandbox.module(source)(grid)
            reflected = sandbox.module(reflect)(bundle)
        assert reflected.position.is_meta
        assert reflected.position.dtype is torch.float64
        assert reflected.optical_path.dtype is torch.float64
        assert reflected.status.dtype is torch.uint8


def _analytic_conic_normal_at(
    point: torch.Tensor,
    *,
    vertex: torch.Tensor,
    curvature: float,
    conic_constant: float,
    even_coefficients: tuple[float, ...] = (),
) -> torch.Tensor:
    local = point - vertex
    x = local[..., 0]
    y = local[..., 1]
    q = x * x + y * y
    c = float(curvature)
    k = float(conic_constant)
    u = 1.0 - (1.0 + k) * c * c * q
    sqrt_u = torch.sqrt(torch.clamp(u, min=1.0e-30))
    denom = 1.0 + sqrt_u
    base = c / denom + (1.0 + k) * (c**3) * q / (2.0 * sqrt_u * denom * denom)
    ds_dq = base
    for index, alpha in enumerate(even_coefficients, start=1):
        ds_dq = ds_dq + index * float(alpha) * q ** (index - 1)
    normal = torch.stack(
        [-2.0 * x * ds_dq, -2.0 * y * ds_dq, torch.ones_like(x)],
        dim=-1,
    )
    return normal / normal.norm(dim=-1, keepdim=True)


class TestConicReflectionAnalytic:
    """
    圆锥面反射的独立解析锚点：以独立解析的圆锥法线（非球面极限匹配）证
    反射方向、位置前进、折射率保留、光程累加与 active/missed/vignetted 三态——镜像球面
    覆盖模式（``TestSphereReflectionAnalytic``）。
    """

    def test_oblique_reflected_direction_matches_independent_conic_normal(self) -> None:
        """
        斜入射：反射方向与独立解析圆锥法线下的 Householder d−2(d·n̂)n̂ 一致
        （非球面极限匹配；独立法线 oracle）
        """

        curvature = 1.0 / 5.0e-6
        theta = math.radians(15.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        conic = ConicEvenAsphere(
            curvature=curvature,
            conic_constant=-0.3,
            even_coefficients=(1.0e3,),
            clear_aperture_radius=5.0e-6,
        )
        reflected = reflect_at(bundle, surface=conic)
        # 独立解析法线（在观测交点处）：与生产 encounter 法线分开实现
        vertex = torch.zeros(3, dtype=torch.float64)
        normal = _analytic_conic_normal_at(
            reflected.position[0, 0],
            vertex=vertex,
            curvature=curvature,
            conic_constant=-0.3,
            even_coefficients=(1.0e3,),
        )
        expected_direction = _analytic_reflect(direction, normal)
        assert torch.allclose(
            reflected.direction[0, 0],
            expected_direction,
            atol=1.0e-7,
        )
        # 反射方向保单位长度
        norm = reflected.direction[0, 0].norm()
        assert torch.isclose(norm, torch.ones_like(norm), atol=1.0e-9)
        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        _assert_no_nan(reflected)

    def test_position_advances_and_optical_path_accumulates(self) -> None:
        """
        位置前进到交点；光程 = 入射折射率 × 几何距离；折射率保留入射
        """

        curvature = 1.0 / 5.0e-6
        incident = ConstantMedium(index=1.3)
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z(), medium=incident)
        conic = ConicEvenAsphere(
            curvature=curvature,
            conic_constant=0.0,
        )
        reflected = reflect_at(bundle, surface=conic)
        # 位置前进：z 到达顶点（沿轴正入射命中顶点）
        assert torch.isclose(
            reflected.position[0, 0, 2],
            torch.tensor(0.0, dtype=torch.float64),
            atol=1.0e-12,
        )
        # 光程 = 入射折射率 × |距离|，距离 = 3.0e-6
        expected_optical_path = torch.tensor(
            [[1.3 * 3.0e-6]],
            dtype=torch.float64,
        )
        assert torch.allclose(
            reflected.optical_path,
            expected_optical_path,
            atol=1.0e-18,
        )
        # 反射留入射介质：per-ray 折射率精确保留入射评估值
        assert torch.equal(
            reflected.refractive_index,
            bundle.refractive_index,
        )

    def test_missed_ray_marked_missed_on_conic(self) -> None:
        """
        在顶点下方水平行进的 ray（z<0 恒定）与凸圆锥面（z≥0）不相交 ⇒ SURFACE_MISSED，
        保留原位/方向/光程/折射率
        """

        along_x = torch.tensor([1.0, 0.0, 0.0])
        positions = torch.zeros((1, 4, 3), dtype=torch.float64)
        positions[..., 2] = -2.0e-6
        bundle = _bundle(position=positions, direction=along_x)
        conic = ConicEvenAsphere(curvature=1.0 / 5.0e-6, conic_constant=0.0)
        reflected = reflect_at(bundle, surface=conic)
        assert torch.equal(
            reflected.status,
            torch.full_like(reflected.status, RAY_STATUS_SURFACE_MISSED),
        )
        assert torch.equal(reflected.position, bundle.position)
        assert torch.equal(reflected.direction, bundle.direction)
        assert torch.equal(reflected.optical_path, bundle.optical_path)
        # 反射不换介质：missed 光线精确保留入射 per-ray 折射率
        assert torch.equal(reflected.refractive_index, bundle.refractive_index)
        _assert_no_nan(reflected)

    def test_aperture_boundary_splits_active_and_vignetted_on_conic(self) -> None:
        """
        圆形 aperture：径向在内 ⇒ active；在外 ⇒ vignetted（圆锥面边界分段）
        """

        curvature = 1.0 / 5.0e-6
        positions = torch.tensor(
            [[0.3e-6, 0.0, -3.0e-6], [4.8e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        direction = _unit_z().view(1, 1, 3).expand(1, 2, 3)
        bundle = RayBundle(
            position=positions,
            direction=direction,
            polarization_vector=_transverse_polarization_for_direction(
                direction
            ),
            power=torch.ones((1, 2), dtype=torch.float64),
            refractive_index=torch.ones((1, 2), dtype=torch.float64),
            optical_path=torch.zeros((1, 2), dtype=torch.float64),
            status=torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        conic = ConicEvenAsphere(
            curvature=curvature,
            conic_constant=0.0,
            clear_aperture_radius=2.0e-6,
        )
        reflected = reflect_at(bundle, surface=conic)
        assert reflected.status[0, 0] == RAY_STATUS_ACTIVE
        assert reflected.status[0, 1] == RAY_STATUS_VIGNETTED
        _assert_no_nan(reflected)


class TestPlaneStateValidatedAtConsumption:
    """
    平面消费期状态验证：变异 trainable origin/aperture 后，
    stateless 入口数值工作前抛稳定身份；direct 与 replay 路径一致
    """

    def _bundle_at_plane(self) -> RayBundle:
        # 沿 +z 入射、位于平面原点前方的最小光线束
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        return _bundle(position=positions, direction=_unit_z())

    def test_mutated_origin_non_finite_rejected(self) -> None:
        """
        构造后把可训练平面原点改成 NaN ⇒ consumption 期抛 ``plane_origin_invalid``
        （direct 与 replay 一致；构造期验证不覆盖 optimizer 变异后）
        """

        origin_param = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 0.0), dtype=torch.float64),
        )
        plane = Plane(origin=origin_param)
        component = ReflectAt(surface=plane)
        bundle = self._bundle_at_plane()
        with torch.no_grad():
            origin_param[1].fill_(float("nan"))
        with pytest.raises(OpticalValueError) as direct_call:
            reflect_at(bundle, surface=plane)
        assert direct_call.value.identity == "plane_origin_invalid"
        with pytest.raises(OpticalValueError) as replay_path:
            component(bundle)
        assert replay_path.value.identity == "plane_origin_invalid"

    def test_mutated_plane_aperture_non_positive_rejected(self) -> None:
        """
        构造后把硬孔径 Buffer 改成负数 ⇒ consumption 期抛孔径身份
        """

        plane = Plane(clear_aperture_radius=1.0e-5)
        component = ReflectAt(surface=plane)
        bundle = self._bundle_at_plane()
        with torch.no_grad():
            plane.clear_aperture_radius.fill_(-2.0)
        with pytest.raises(OpticalValueError) as rejected:
            component(bundle)
        assert (
            rejected.value.identity == "plane_clear_aperture_radius_invalid"
        )

    def test_valid_trainable_plane_preserves_gradient_at_consumption(
        self,
    ) -> None:
        """
        valid trainable Plane 的 consumption 验证不破坏计算图：梯度仍流过可训练原点
        """

        origin_param = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 0.0), dtype=torch.float64),
        )
        plane = Plane(origin=origin_param)
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        reflected = reflect_at(bundle, surface=plane)
        reflected.position.sum().backward()
        assert origin_param.grad is not None
        assert torch.isfinite(origin_param.grad).all()


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_reflect_at_surface_families_match_cpu_on_cuda() -> None:
    """
    ReflectAt 在三类曲面上保持全部 Ray Bundle 量与 CPU 一致
    """

    positions = torch.tensor(
        [[[-0.2e-6, 0.0, -3.0e-6], [0.2e-6, 0.0, -3.0e-6]]],
        dtype=torch.float64,
    )
    for surface in (
        Plane(),
        Sphere(radius_of_curvature=5.0e-6),
        ConicEvenAsphere(
            curvature=1.0 / 1.0e-6,
            conic_constant=-0.5,
        ),
    ):
        cpu_bundle = _bundle(position=positions, direction=_unit_z())
        cuda_bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            device="cuda:0",
        )
        cpu_output = reflect_at(cpu_bundle, surface=surface)
        cuda_output = reflect_at(cuda_bundle, surface=surface.cuda())
        for quantity in (
            "position",
            "direction",
            "polarization_vector",
            "power",
            "refractive_index",
            "optical_path",
            "status",
        ):
            torch.testing.assert_close(
                getattr(cpu_output, quantity),
                getattr(cuda_output, quantity).cpu(),
            )


def test_reflect_at_reports_uncertifiable_conic_with_stable_identity() -> None:
    """
    公开圆锥反射对超出冻结证明预算的偶次处方给出稳定收敛失败身份
    """

    direction = torch.tensor(
        [
            math.sin(math.radians(12.0)),
            0.0,
            math.cos(math.radians(12.0)),
        ],
        dtype=torch.float64,
    )
    position = torch.tensor(
        [[[0.5e-6, 0.0, -3.0e-6]]],
        dtype=torch.float64,
    )
    bundle = _bundle(position=position, direction=direction)
    surface = ConicEvenAsphere(
        curvature=1.0 / 8.0e-6,
        conic_constant=0.5,
        even_coefficients=(0.0,) * 64 + (1.0,),
        clear_aperture_radius=5.0e-6,
    )
    with pytest.raises(OpticalValueError) as rejected:
        reflect_at(bundle, surface=surface)
    assert rejected.value.identity == "conic_intersection_not_converged"


from __future__ import annotations

from collections.abc import Callable
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
from chromatix_next.optics.element import RefractAt, reflect_at, refract_at
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
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


def _posed_plane(
    pose_point: (
        tuple[float, float, float] | torch.Tensor | torch.nn.Parameter
    ) = (
        0.0,
        0.0,
        0.0,
    ),
) -> Plane:
    # 消费边界复核证据用的平面；默认固定 Buffer 原点，传 Parameter 走可训练原点路径
    return Plane(origin=pose_point)


def _posed_sphere(
    pose_point: (
        tuple[float, float, float] | torch.Tensor | torch.nn.Parameter
    ) = (
        0.0,
        0.0,
        0.0,
    ),
) -> Sphere:
    # 凸球面；默认固定 Buffer 原点，传 Parameter 走可训练原点路径
    return Sphere(vertex=pose_point, radius_of_curvature=5.0e-6)


def _posed_conic(
    pose_point: (
        tuple[float, float, float] | torch.Tensor | torch.nn.Parameter
    ) = (
        0.0,
        0.0,
        0.0,
    ),
) -> ConicEvenAsphere:
    # 凸圆锥偶次非球面；默认固定 Buffer 原点，传 Parameter 走可训练原点路径
    return ConicEvenAsphere(
        vertex=pose_point,
        curvature=1.0 / 1.0e-6,
        conic_constant=-0.5,
    )


# 基线 reflect_at 是唯一同时接受三种面的公共消费边界，证据统一经它消费
_SurfaceFactory = Callable[..., Plane | Sphere | ConicEvenAsphere]


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
    # 四态有限性：所有张量处处有限
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


def _analytic_sphere_distance(
    origin: torch.Tensor,
    direction: torch.Tensor,
    center: torch.Tensor,
    radius: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
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


def _analytic_plane_refracted(
    direction: torch.Tensor,
    normal: torch.Tensor,
    eta: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    cos_incident = -(direction * normal).sum(dim=-1)
    sin_squared_incident = 1.0 - cos_incident * cos_incident
    sin_squared_transmitted = (eta * eta) * sin_squared_incident
    return (
        eta * direction
        + (eta * cos_incident - torch.sqrt(1.0 - sin_squared_transmitted)).unsqueeze(
            -1,
        )
        * normal,
        sin_squared_transmitted,
    )


class TestPlaneRefraction:
    """
    平面折射的公共接口独立解析锚点：斜入射向量 Snell（切向比 = n_i/n_t、
    单位长度、光密介质偏向法线、反向可逆）、TIR 有限终止、位置前进/光程累加/逐光线
    折射率切换。该节点在公共接口直接证明斜入射透射与折射率切换。
    """

    def test_oblique_tangential_ratio_unit_length_and_bend_toward_normal(self) -> None:
        """
        斜入射光密目标介质：切向分量比 = ``n_i/n_t``；折射方向保单位；折射角 < 入射角
        """

        n_i = 1.0
        n_t = 1.5
        eta = n_i / n_t
        theta = math.radians(25.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -2.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        plane = Plane(origin=(0.0, 0.0, 0.0))
        refracted = refract_at(
            bundle,
            surface=plane,
            destination_medium=ConstantMedium(index=n_t),
        )
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        outgoing = refracted.direction[0, 0]
        # 折射后方向保单位长度（向量 Snell 构造性不变量）
        assert torch.isclose(
            outgoing.norm(),
            torch.ones_like(outgoing.norm()),
            atol=1.0e-9,
        )
        # 切向分量比 = n_i/n_t（平面法线恒定 = ê_z；切向 = x 分量）
        ratio = outgoing[0] / direction[0]
        assert math.isclose(float(ratio), eta, rel_tol=1.0e-9)
        # 光密介质：折射角更小 ⇒ z 分量更大
        assert float(outgoing[2]) > float(direction[2])
        # 成功透射光线逐光线折射率切到目标介质评估值
        assert torch.allclose(
            refracted.refractive_index,
            torch.full_like(refracted.refractive_index, n_t),
        )
        _assert_no_nan(refracted)

    def test_refraction_is_reversible_with_media_swapped(self) -> None:
        """
        反向可逆：把折射光反向送回原平面、介质互换 ⇒ 恢复原入射方向
        """

        n_i = 1.0
        n_t = 1.5
        theta = math.radians(20.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -2.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        plane = Plane(origin=(0.0, 0.0, 0.0))
        forward_bundle = _bundle(
            position=positions,
            direction=direction,
            medium=ConstantMedium(index=n_i),
        )
        forward = refract_at(
            forward_bundle,
            surface=plane,
            destination_medium=ConstantMedium(index=n_t),
        )
        reverse_bundle = _bundle(
            position=forward.position,
            direction=-forward.direction[0, 0],
            medium=ConstantMedium(index=n_t),
        )
        reverse = refract_at(
            reverse_bundle,
            surface=plane,
            destination_medium=ConstantMedium(index=n_i),
        )
        recovered = -reverse.direction[0, 0]
        assert torch.allclose(recovered, direction, atol=1.0e-9)
        assert reverse.status[0, 0] == RAY_STATUS_ACTIVE

    def test_total_internal_reflection_terminates_transmission_on_plane(self) -> None:
        """
        光密→光疏 + 大入射角（>临界角 arcsin(n_t/n_i)）⇒ 平面 TIR：状态终止、方向保留
        入射、逐光线折射率保留入射、功率不变（公共接口）
        """

        n_i = 1.5
        n_t = 1.0
        # 60° 入射角 > 临界角 arcsin(1/1.5) ≈ 41.8°
        angle_rad = math.radians(60.0)
        direction = torch.tensor(
            [math.sin(angle_rad), 0.0, math.cos(angle_rad)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -2.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=direction,
            medium=ConstantMedium(index=n_i),
        )
        plane = Plane(origin=(0.0, 0.0, 0.0))
        refracted = refract_at(
            bundle,
            surface=plane,
            destination_medium=Vacuum(),
        )
        assert (
            refracted.status[0, 0] == RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        )
        # TIR 不改写为反射：方向保留入射方向
        assert torch.allclose(refracted.direction[0, 0], direction, atol=1.0e-12)
        # 逐光线折射率精确保留入射值（不被目标介质改写）
        assert torch.allclose(
            refracted.refractive_index,
            torch.full_like(refracted.refractive_index, n_i),
        )
        # 功率不变（不发明 Fresnel）
        assert torch.equal(refracted.power, bundle.power)
        _assert_no_nan(refracted)

    def test_exact_critical_angle_remains_a_finite_transmission(self) -> None:
        incident_index = 1.3333333333333333
        direction = torch.tensor(
            [0.7500000000000001, 0.0, -0.6614378277661475],
            dtype=torch.float64,
        )
        bundle = _bundle(
            position=torch.tensor(
                [[[0.0, 0.0, 2.0e-6]]],
                dtype=torch.float64,
            ),
            direction=direction,
            medium=ConstantMedium(index=incident_index),
        )

        refracted = refract_at(
            bundle,
            surface=Plane(origin=(0.0, 0.0, 0.0)),
            destination_medium=Vacuum(),
        )

        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        assert torch.isfinite(refracted.direction).all()
        assert torch.allclose(
            refracted.direction[0, 0],
            torch.tensor([1.0, 0.0, 0.0], dtype=torch.float64),
            rtol=0.0,
            atol=8.0 * torch.finfo(torch.float64).eps,
        )
        assert refracted.refractive_index[0, 0] == 1.0

    def test_position_advance_optical_path_and_destination_index(self) -> None:
        """
        成功透射：位置前进到平面交点；光程 = n_incident × 几何距离；逐光线折射率切目标
        """

        n_i = 1.3
        n_t = 1.5
        axial_distance = 2.0e-6
        positions = torch.tensor(
            [[0.0, 0.0, -axial_distance]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=n_i),
        )
        plane = Plane(origin=(0.0, 0.0, 0.0))
        refracted = refract_at(
            bundle,
            surface=plane,
            destination_medium=ConstantMedium(index=n_t),
        )
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        # 位置前进到平面交点 z=0
        assert torch.isclose(
            refracted.position[0, 0, 2],
            torch.tensor(0.0, dtype=torch.float64),
            atol=1.0e-12,
        )
        # 光程 = n_incident × 几何距离（正入射，distance = axial_distance）
        assert torch.allclose(
            refracted.optical_path,
            torch.tensor([[n_i * axial_distance]], dtype=torch.float64),
            atol=1.0e-18,
        )
        # 逐光线折射率切到目标介质
        assert torch.allclose(
            refracted.refractive_index,
            torch.full_like(refracted.refractive_index, n_t),
        )


class TestSpherePoseAndStateValidation:
    """
    球面姿态、曲率半径与 aperture 校验
    """

    def test_role_is_element_literal(self) -> None:
        """
        RefractAt 声明唯一不可改写的 element 角色
        """

        component = RefractAt(
            surface=Sphere(radius_of_curvature=5.0e-6),
            destination_medium=ConstantMedium(index=1.5),
        )
        assert component.role == "element"
        with pytest.raises(AttributeError):
            component.role = "propagation"  # type: ignore[misc]

    def test_forward_returns_ray_bundle(self) -> None:
        """
        真实前向只产生 RayBundle 强物理值
        """

        component = RefractAt(
            surface=Sphere(
                vertex=(0.0, 0.0, 5.0e-6),
                radius_of_curvature=5.0e-6,
            ),
            destination_medium=ConstantMedium(index=1.5),
        )
        bundle = component(_bundle_at_origin(direction=_unit_z()))
        assert isinstance(bundle, RayBundle)

    def test_default_normal_yields_plus_z(self) -> None:
        """
        默认 tangent_x=ê_x、tangent_y=ê_y
        ⇒ 顶点法线 = cross(tangent_x, tangent_y) = +ê_z
        """

        sphere = Sphere(radius_of_curvature=5.0e-6)
        normal = sphere.normal
        assert torch.allclose(
            normal,
            torch.tensor([0.0, 0.0, 1.0], dtype=normal.dtype),
            atol=1.0e-6,
        )

    def test_non_unit_axis_rejected(self) -> None:
        """
        非单位 axis ⇒ 拒绝；球面不静默归一化
        """

        with pytest.raises(OpticalValueError) as rejected:
            Sphere(
                radius_of_curvature=5.0e-6,
                tangent_x=(2.0, 0.0, 0.0),
            )
        assert rejected.value.identity == "sphere_tangent_x_not_unit"

    def test_non_orthogonal_basis_rejected(self) -> None:
        """
        平行两轴 ⇒ 非正交拒绝
        """

        with pytest.raises(OpticalValueError) as rejected:
            Sphere(
                radius_of_curvature=5.0e-6,
                tangent_x=(1.0, 0.0, 0.0),
                tangent_y=(1.0, 0.0, 0.0),
            )
        assert rejected.value.identity == "sphere_basis_not_orthogonal"

    @pytest.mark.parametrize(
        "invalid_radius",
        (0.0, -0.0, float("nan"), float("inf")),
    )
    def test_non_finite_or_zero_curvature_rejected(
        self,
        invalid_radius: float,
    ) -> None:
        """
        零、非有限曲率半径 ⇒ 拒绝
        """

        with pytest.raises(OpticalValueError) as rejected:
            Sphere(radius_of_curvature=invalid_radius)
        assert (
            rejected.value.identity
            == "sphere_radius_of_curvature_invalid"
        )

    @pytest.mark.parametrize(
        "invalid_aperture",
        (0.0, -1.0, float("nan")),
    )
    def test_non_positive_aperture_rejected(
        self,
        invalid_aperture: float,
    ) -> None:
        """
        零、负、非有限 aperture ⇒ 拒绝
        """

        with pytest.raises(OpticalValueError) as rejected:
            Sphere(
                radius_of_curvature=5.0e-6,
                clear_aperture_radius=invalid_aperture,
            )
        assert rejected.value.identity == "sphere_clear_aperture_radius_invalid"

    def test_plain_non_parameter_tensor_radius_rejected(self) -> None:
        """
        普通（非 Parameter）张量 ⇒ 稳定域类型错误，不泄漏裸断言
        """

        with pytest.raises(OpticalTypeError) as rejected:
            Sphere(
                radius_of_curvature=torch.tensor(5.0e-6),  # type: ignore[arg-type]
            )
        assert (
            rejected.value.identity
            == "sphere_radius_of_curvature_invalid"
        )

    def test_plain_non_parameter_tensor_aperture_rejected(self) -> None:
        """
        普通（非 Parameter）张量 ⇒ 稳定域类型错误，不泄漏裸断言
        """

        with pytest.raises(OpticalTypeError) as rejected:
            Sphere(
                radius_of_curvature=5.0e-6,
                clear_aperture_radius=torch.tensor(4.0e-6),  # type: ignore[arg-type]
            )
        assert (
            rejected.value.identity
            == "sphere_clear_aperture_radius_invalid"
        )

    def test_refract_at_rejects_unregistered_surface(self) -> None:
        """
        refract_at 只接受已注册的面类型；未注册的对象类型拒绝
        """

        bundle = _bundle_at_origin(direction=_unit_z())
        with pytest.raises(OpticalTypeError) as rejected:
            refract_at(
                bundle,
                surface=object(),  # type: ignore[arg-type]
                destination_medium=ConstantMedium(index=1.5),
            )
        assert rejected.value.identity == "refract_at_surface_invalid"

    def test_refract_at_rejects_non_bundle_input(self) -> None:
        """
        refract_at 只能作用于 RayBundle；其他类型拒绝
        """

        with pytest.raises(OpticalTypeError) as rejected:
            refract_at(
                object(),  # type: ignore[arg-type]
                surface=Sphere(radius_of_curvature=5.0e-6),
                destination_medium=ConstantMedium(index=1.5),
            )
        assert rejected.value.identity == "refract_at_bundle_invalid"

    def test_refract_at_rejects_non_medium_destination(self) -> None:
        """
        目标介质必须是 Medium 物理值
        """

        bundle = _bundle_at_origin(direction=_unit_z())
        with pytest.raises(OpticalTypeError) as rejected:
            refract_at(
                bundle,
                surface=Sphere(radius_of_curvature=5.0e-6),
                destination_medium=object(),  # type: ignore[arg-type]
            )
        assert rejected.value.identity == "refract_at_destination_medium_invalid"


class TestSphereAnalyticIntersection:
    """
    独立解析的球面交集：凸/凹两种符号、斜入射、近切线、未命中与后向
    """

    def test_convex_on_axis_matches_vertex(self) -> None:
        """
        凸面（R>0）：沿轴 ray 命中顶点，交点 z = vertex_z，距离 = 起点到顶点
        """

        radius = 5.0e-6
        vertex_z = 0.0
        start_z = -5.0e-6
        positions = torch.tensor(
            [[0.0, 0.0, start_z]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(
            vertex=(0.0, 0.0, vertex_z),
            radius_of_curvature=radius,
        )
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert torch.allclose(
            refracted.position[..., 2],
            torch.tensor(vertex_z, dtype=torch.float64),
        )
        assert torch.equal(
            refracted.status,
            torch.full_like(refracted.status, RAY_STATUS_ACTIVE),
        )
        _assert_no_nan(refracted)

    def test_concave_on_axis_matches_vertex(self) -> None:
        """
        凹面（R<0）：ray 起点在曲率球内 ⇒ far_root 命中顶点侧
        """

        radius = -5.0e-6
        vertex_z = 0.0
        start_z = -2.0e-6  # 在曲率球（z∈[-10e-6, 0]）内部
        positions = torch.tensor(
            [[0.0, 0.0, start_z]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(
            vertex=(0.0, 0.0, vertex_z),
            radius_of_curvature=radius,
        )
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert torch.allclose(
            refracted.position[..., 2],
            torch.tensor(vertex_z, dtype=torch.float64),
        )
        _assert_no_nan(refracted)

    def test_oblique_intersection_matches_analytic(self) -> None:
        """
        斜入射 ray 的交点与独立解析二次解一致（凸面，两种符号各覆盖）
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
        sphere = Sphere(
            vertex=(0.0, 0.0, 0.0),
            radius_of_curvature=radius,
        )
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        expected_distance, expected_point, _expected_normal = (
            _analytic_sphere_distance(
                positions,
                direction,
                center,
                radius,
            )
        )
        assert torch.allclose(
            refracted.position,
            expected_point,
            atol=1.0e-12,
        )
        assert torch.allclose(
            refracted.optical_path,
            expected_distance.to(torch.float64),
            atol=1.0e-18,
        )
        _assert_no_nan(refracted)

    def test_near_tangent_remains_stable(self) -> None:
        """
        近切线（判别式近零）：交点有限、不发散，状态 active
        """

        radius = 5.0e-6
        # ray 在 x = R - δ 处沿 +z，几乎擦着球面侧面；δ 远小于 R
        delta = 1.0e-9
        start = torch.tensor(
            [radius - delta, 0.0, -2.0 * radius],
            dtype=torch.float64,
        )
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        # 球心置于原点：顶点 = -R × 法向（法向=+ê_z），使球心与原点重合
        sphere = Sphere(
            vertex=(0.0, 0.0, -radius),
            radius_of_curvature=radius,
        )
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        assert torch.isfinite(refracted.position).all()
        assert torch.isfinite(refracted.direction).all()

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
        sphere = Sphere(
            vertex=(0.0, 0.0, 0.0),
            radius_of_curvature=radius,
        )
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert refracted.status[0, 0] == RAY_STATUS_SURFACE_MISSED
        assert torch.equal(refracted.position, bundle.position)
        assert torch.equal(refracted.direction, bundle.direction)
        assert torch.equal(refracted.optical_path, bundle.optical_path)
        assert torch.equal(refracted.refractive_index, bundle.refractive_index)
        _assert_no_nan(refracted)

    def test_rear_facing_ray_marked_missed(self) -> None:
        """
        沿 -z 的 ray 背离凸面顶点 ⇒ 两根均负 ⇒ 未命中
        """

        backward = torch.tensor([0.0, 0.0, -1.0])
        bundle = _bundle_at_origin(direction=backward)
        sphere = Sphere(
            vertex=(0.0, 0.0, 5.0e-6),
            radius_of_curvature=5.0e-6,
        )
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert torch.equal(
            refracted.status,
            torch.full_like(refracted.status, RAY_STATUS_SURFACE_MISSED),
        )
        assert torch.equal(refracted.position, bundle.position)


class TestSphereSnellRefraction:
    """
    向量 Snell 不变量：切向比、单位长度、法向守恒、反向可逆
    """

    def test_normal_incidence_no_bend(self) -> None:
        """
        正入射（ray 沿顶点法线）⇒ 方向不变
        """

        radius = 5.0e-6
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(radius_of_curvature=radius)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert torch.allclose(refracted.direction, bundle.direction, atol=1.0e-12)

    def test_oblique_tangential_ratio_matches_snell(self) -> None:
        """
        折射前后切向分量比 = n_i/n_t；折射后方向仍为单位向量
        """

        n_i = 1.0
        n_t = 1.5
        radius = 5.0e-6
        center = torch.tensor([0.0, 0.0, radius], dtype=torch.float64)
        theta = math.radians(25.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        sphere = Sphere(radius_of_curvature=radius)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=n_t),
        )
        _distance, _point, normal = _analytic_sphere_distance(
            positions,
            direction,
            center,
            radius,
        )
        # 切向投影算子：I − n nᵀ
        tangential_incident = direction - (direction * normal).sum(-1) * normal
        tangential_refracted = (
            refracted.direction[0, 0]
            - (refracted.direction[0, 0] * normal[0, 0]).sum(-1)
            * normal[0, 0]
        )
        # 切向分量比 = n_i/n_t（任取非零切向幅值比较）
        ratio = tangential_refracted.norm() / tangential_incident[0, 0].norm()
        assert math.isclose(float(ratio), n_i / n_t, rel_tol=1.0e-6)
        # 折射后仍为单位向量
        outgoing = refracted.direction[0, 0]
        assert torch.isclose(
            outgoing.norm(),
            torch.ones_like(outgoing.norm()),
            atol=1.0e-9,
        )

    def test_refraction_bends_toward_normal_in_dense_medium(self) -> None:
        """
        进入光密介质（n_t > n_i）⇒ 折射光线偏向法线（折射角 < 入射角）
        """

        radius = 5.0e-6
        center = torch.tensor([0.0, 0.0, radius], dtype=torch.float64)
        theta = math.radians(30.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        sphere = Sphere(radius_of_curvature=radius)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        _d, _p, normal = _analytic_sphere_distance(
            positions,
            direction,
            center,
            radius,
        )
        cos_incident = -(direction * normal[0, 0]).sum(-1)
        cos_refracted = -(refracted.direction[0, 0] * normal[0, 0]).sum(-1)
        # 光密介质：折射角更小 ⇒ cos 更大
        assert float(cos_refracted) > float(cos_incident)

    def test_reverse_direction_recovers_incident(self) -> None:
        """
        反向可逆：把折射光反向送回原面、介质互换 ⇒ 恢复原入射方向
        """

        n_i = 1.0
        n_t = 1.5
        radius = 5.0e-6
        theta = math.radians(20.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        positions = start.unsqueeze(0).unsqueeze(0)
        sphere = Sphere(radius_of_curvature=radius)
        forward_bundle = _bundle(
            position=positions,
            direction=direction,
            medium=ConstantMedium(index=n_i),
        )
        forward = refract_at(
            forward_bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=n_t),
        )
        # 反向：从交点以 -d_t 出发，介质互换（n_t → n_i）
        reverse_positions = forward.position.clone()
        reverse_direction = -forward.direction[0, 0]
        reverse_bundle = _bundle(
            position=reverse_positions,
            direction=reverse_direction,
            medium=ConstantMedium(index=n_t),
        )
        reverse = refract_at(
            reverse_bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=n_i),
        )
        # 反向折射后方向应恢复原入射的反方向，即 -d
        recovered = -reverse.direction[0, 0]
        assert torch.allclose(
            recovered,
            direction,
            atol=1.0e-9,
        )


class TestSphereTotalInternalReflection:
    """
    全内反射以有限状态终止透射路径，绝不改写为反射
    """

    def test_tir_terminates_with_finite_status(self) -> None:
        """
        光密→光疏 + 大入射角 ⇒ TIR；status 有限、无 NaN
        """

        # 沿 +z 偏轴 ray 命中凸面侧面（大入射角）；n_i=1.5 → n_t=1.0 ⇒ 临界角 41.8°
        radius = 5.0e-6
        start = torch.tensor(
            [4.0e-6, 0.0, -3.0e-6],
            dtype=torch.float64,
        )
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=1.5),
        )
        sphere = Sphere(radius_of_curvature=radius)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=Vacuum(),
        )
        assert refracted.status[0, 0] == RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        _assert_no_nan(refracted)

    def test_tir_preserves_incident_direction_and_power(self) -> None:
        """
        TIR 不改写为反射：方向保持入射方向，功率不变
        """

        radius = 5.0e-6
        start = torch.tensor(
            [4.0e-6, 0.0, -3.0e-6],
            dtype=torch.float64,
        )
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=1.5),
        )
        sphere = Sphere(radius_of_curvature=radius)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=Vacuum(),
        )
        assert refracted.status[0, 0] == RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        # 方向 = 入射方向（未改写为反射方向）
        assert torch.allclose(refracted.direction[0, 0], _unit_z())
        # 功率不变（不发明 Fresnel）
        assert torch.equal(refracted.power, bundle.power)

    def test_tir_advances_position_to_intersection(self) -> None:
        """
        TIR 光线仍前进到交点并累加入射介质光程（有限可诊断）
        """

        radius = 5.0e-6
        center = torch.tensor([0.0, 0.0, radius], dtype=torch.float64)
        start = torch.tensor(
            [4.0e-6, 0.0, -3.0e-6],
            dtype=torch.float64,
        )
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=1.5),
        )
        sphere = Sphere(radius_of_curvature=radius)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=Vacuum(),
        )
        expected_distance, _point, _normal = _analytic_sphere_distance(
            positions,
            _unit_z(),
            center,
            radius,
        )
        # 光程 = n_i × distance（入射介质累积，与平面动作一致）
        assert torch.allclose(
            refracted.optical_path,
            1.5 * expected_distance.to(torch.float64),
            atol=1.0e-18,
        )
        # 位置已前进到交点（不再停在起点）
        assert not torch.allclose(refracted.position, bundle.position)



class TestSphereMediumAndOpticalPath:
    """
    目标介质、功率守恒与光程累加
    """

    def test_successful_ray_enters_destination_medium(self) -> None:
        """
        成功折射的光线进入显式命名的目标介质；功率与光谱不变
        """

        destination = ConstantMedium(index=1.5)
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(radius_of_curvature=5.0e-6)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=destination,
        )
        assert torch.allclose(
            refracted.refractive_index,
            torch.full_like(refracted.refractive_index, 1.5),
        )
        assert torch.equal(refracted.power, bundle.power)
        assert refracted.spectrum is bundle.spectrum

    def test_optical_path_accumulates_incident_index_times_distance(self) -> None:
        """
        光程增量 = n_incident × 距离；真空 n=1，恒定介质取其折射率
        """

        radius = 5.0e-6
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=1.3),
        )
        sphere = Sphere(radius_of_curvature=radius)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert refracted.optical_path.dtype is torch.float64
        assert torch.allclose(
            refracted.optical_path,
            torch.tensor(1.3 * 3.0e-6, dtype=torch.float64),
            atol=1.0e-18,
        )

    def test_optical_path_graph_bears_trainable_spacing(self) -> None:
        """
        可训练顶点 z（Parameter）的 OP 保持 autograd 图
        """

        origin = torch.nn.Parameter(
            torch.tensor([0.0, 0.0, 0.0], dtype=torch.float64),
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
        sphere = Sphere(
            vertex=origin,
            radius_of_curvature=5.0e-6,
        )
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.6),
        )
        refracted.optical_path.sum().backward()
        assert origin.grad is not None
        assert torch.isclose(
            origin.grad[2],
            torch.tensor(1.5, dtype=torch.float64),
        )


class TestRefractAtFunctionComponentDuality:
    """
    refract_at 与 RefractAt 行为完全一致；Source→RefractAt 链路产出 RayBundle
    """

    def test_function_and_component_agree(self) -> None:
        """
        同一入射 bundle、同一 Sphere/介质：两端输出逐元素一致
        """

        radius = 5.0e-6
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
        sphere = Sphere(radius_of_curvature=radius)
        component = RefractAt(
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        function_output = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        component_output = component(bundle)
        assert torch.equal(function_output.position, component_output.position)
        assert torch.equal(function_output.direction, component_output.direction)
        assert torch.equal(
            function_output.optical_path,
            component_output.optical_path,
        )
        assert torch.equal(function_output.status, component_output.status)

    def test_refract_at_consumes_authored_ray_bundle(self) -> None:
        """
        准直光源产出的光线束可直接进入 ``RefractAt`` 折射动作
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
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert refracted.position.shape == bundle.position.shape
        assert not torch.equal(
            refracted.refractive_index,
            bundle.refractive_index,
        )


class TestSphereStatusPropagation:
    """
    inactive ray 不再参与；四态有限可诊断；vignetted 区别于 active
    """

    def test_inactive_ray_retains_last_state(self) -> None:
        """
        已终止的 ray 再次折射不前进、不改状态
        """

        positions = torch.zeros((1, 2, 3), dtype=torch.float64)
        positions[0, 1, 0] = 5.0e-6
        direction = _unit_z().view(1, 1, 3).expand(1, 2, 3)
        status = torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8)
        status[0, 1] = RAY_STATUS_VIGNETTED
        spectrum = _monochromatic()
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
            spectrum=spectrum,
        )
        sphere = Sphere(radius_of_curvature=5.0e-6)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        # inactive ray：保留原 status、位置、方向与光程
        assert refracted.status[0, 1] == RAY_STATUS_VIGNETTED
        assert torch.equal(refracted.position[0, 1], positions[0, 1])
        assert torch.isclose(
            refracted.optical_path[0, 1],
            torch.tensor(0.7, dtype=torch.float64),
        )

    def test_four_terminal_states_distinguishable(self) -> None:
        """
        active/missed/vignetted/TIR 四态在同一 bundle 内可同时诊断
        """

        radius = 5.0e-6
        aperture = 4.5e-6
        positions = torch.zeros((4, 3), dtype=torch.float64).unsqueeze(0)
        positions[0, 0] = torch.tensor([0.0, 0.0, -3.0e-6])
        positions[0, 1] = torch.tensor([8.0e-6, 0.0, -3.0e-6])
        positions[0, 2] = torch.tensor([4.8e-6, 0.0, -3.0e-6])
        positions[0, 3] = torch.tensor([4.0e-6, 0.0, -3.0e-6])
        directions = _unit_z().view(1, 1, 3).expand(1, 4, 3).clone()
        spectrum = _monochromatic()
        bundle = RayBundle(
            position=positions,
            direction=directions,
            polarization_vector=_transverse_polarization_for_direction(
                directions
            ),
            power=torch.ones((1, 4), dtype=torch.float64),
            refractive_index=torch.full(
                (1, 4),
                1.5,
                dtype=torch.float64,
            ),
            optical_path=torch.zeros((1, 4), dtype=torch.float64),
            status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=spectrum,
        )
        sphere = Sphere(
            vertex=(0.0, 0.0, 0.0),
            radius_of_curvature=radius,
            clear_aperture_radius=aperture,
        )
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=Vacuum(),
        )
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        assert refracted.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert refracted.status[0, 2] == RAY_STATUS_VIGNETTED
        assert refracted.status[0, 3] == RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        _assert_no_nan(refracted)


class TestRefractAtSurfaceIntegration:
    """
    三类公共表面各自承载折射动作的复合证据
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
        每类表面均推进相遇通道，且只对命中光线施加折射
        """

        bundle = _mixed_surface_bundle()
        refracted = refract_at(
            bundle,
            surface=surface,
            destination_medium=ConstantMedium(index=1.5),
        )

        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        assert torch.allclose(
            refracted.position[0, 0],
            torch.zeros(3, dtype=torch.float64),
            atol=1.0e-12,
        )
        assert torch.allclose(
            refracted.direction[0, 0],
            torch.tensor([0.0, 0.0, 1.0], dtype=torch.float64),
            atol=1.0e-12,
        )
        assert torch.isclose(
            refracted.optical_path[0, 0],
            torch.tensor(1.3 * 3.0e-6, dtype=torch.float64),
            atol=1.0e-15,
        )
        assert refracted.refractive_index[0, 0] == 1.5
        assert refracted.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert torch.equal(refracted.position[0, 1], bundle.position[0, 1])
        assert torch.equal(refracted.direction[0, 1], bundle.direction[0, 1])
        assert torch.equal(
            refracted.polarization_vector[0, 1],
            bundle.polarization_vector[0, 1],
        )
        assert torch.equal(refracted.power[0, 1], bundle.power[0, 1])
        assert torch.equal(
            refracted.refractive_index[0, 1],
            bundle.refractive_index[0, 1],
        )
        assert torch.equal(
            refracted.optical_path[0, 1],
            bundle.optical_path[0, 1],
        )
        assert torch.equal(refracted.position[0, 2], bundle.position[0, 2])
        assert torch.equal(refracted.direction[0, 2], bundle.direction[0, 2])
        assert torch.equal(
            refracted.polarization_vector[0, 2],
            bundle.polarization_vector[0, 2],
        )
        assert torch.equal(refracted.power[0, 2], bundle.power[0, 2])
        assert torch.equal(
            refracted.refractive_index[0, 2],
            bundle.refractive_index[0, 2],
        )
        assert torch.equal(
            refracted.optical_path[0, 2],
            bundle.optical_path[0, 2],
        )
        assert refracted.status[0, 2] == RAY_STATUS_VIGNETTED
        assert torch.equal(refracted.power, bundle.power)
        assert torch.equal(
            refracted.refractive_index[0, 1:],
            bundle.refractive_index[0, 1:],
        )
        _assert_no_nan(refracted)

        if isinstance(surface, Plane):
            assert refracted.status[0, 3] == RAY_STATUS_VIGNETTED
            assert torch.allclose(
                refracted.position[0, 3],
                torch.tensor([3.0e-6, 0.0, 0.0], dtype=torch.float64),
                atol=1.0e-12,
            )
            assert torch.isclose(
                refracted.optical_path[0, 3],
                bundle.optical_path[0, 3]
                + bundle.refractive_index[0, 3]
                * torch.tensor(3.0e-6, dtype=torch.float64),
                atol=1.0e-15,
            )
            assert (
                refracted.refractive_index[0, 3]
                == bundle.refractive_index[0, 3]
            )
            assert refracted.power[0, 3] == bundle.power[0, 3]
            assert torch.equal(
                refracted.direction[0, 3],
                bundle.direction[0, 3],
            )
            assert torch.equal(
                refracted.polarization_vector[0, 3],
                bundle.polarization_vector[0, 3],
            )


class TestSphereGradient:
    """
    smooth 路径的 autograd 与中心差分一致；边界显式声明分段
    """

    def test_launch_position_propagates_to_intersection(self) -> None:
        """
        可训练 launch x：交点 x 的解析导数与中心差分一致
        """

        radius = 5.0e-6

        def intersection_x(launch_x_value: float) -> float:
            """
            给定发射 x 返回折射交点 x 分量的中心差分参考
            """
            origin = torch.nn.Parameter(
                torch.tensor(
                    [launch_x_value, 0.0, -3.0e-6],
                    dtype=torch.float64,
                ),
            )
            bundle = _bundle(
                position=origin.view(1, 1, 3),
                direction=_unit_z(),
            )
            sphere = Sphere(radius_of_curvature=radius)
            refracted = refract_at(
                bundle,
                surface=sphere,
                destination_medium=ConstantMedium(index=1.5),
            )
            return float(refracted.position[0, 0, 0].detach())

        launch = torch.nn.Parameter(
            torch.tensor([0.3e-6, 0.0, -3.0e-6], dtype=torch.float64),
        )
        bundle = _bundle(
            position=launch.view(1, 1, 3),
            direction=_unit_z(),
        )
        sphere = Sphere(radius_of_curvature=radius)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        refracted.position[0, 0, 0].backward()
        assert launch.grad is not None
        autograd = float(launch.grad[0].detach())
        step = 1.0e-9
        central = (
            intersection_x(0.3e-6 + step)
            - intersection_x(0.3e-6 - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-5, abs_tol=1.0e-7)

    def test_curvature_gradient_matches_central_difference(self) -> None:
        """
        可训练曲率半径：折射方向的解析导数与中心差分一致（远离 TIR/根切换）
        """

        theta = math.radians(15.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)

        def direction_x(radius_value: float) -> float:
            """
            给定球面半径返回折射后方向 x 分量的中心差分参考
            """
            radius_param = torch.nn.Parameter(
                torch.tensor(radius_value, dtype=torch.float64),
            )
            bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
            sphere = Sphere(radius_of_curvature=radius_param)
            refracted = refract_at(
                bundle,
                surface=sphere,
                destination_medium=ConstantMedium(index=1.5),
            )
            return float(refracted.direction[0, 0, 0].detach())

        radius_param = torch.nn.Parameter(
            torch.tensor(5.0e-6, dtype=torch.float64),
        )
        bundle = _bundle(position=start.view(1, 1, 3), direction=direction)
        sphere = RefractAt(
            surface=Sphere(radius_of_curvature=radius_param),
            destination_medium=ConstantMedium(index=1.5),
        )
        refracted = sphere(bundle)
        refracted.direction[0, 0, 0].backward()
        assert radius_param.grad is not None
        autograd = float(radius_param.grad.detach())
        step = 1.0e-11
        central = (
            direction_x(5.0e-6 + step) - direction_x(5.0e-6 - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e-2)

    def test_tir_boundary_is_piecewise_non_differentiable(self) -> None:
        """
        TIR 边界切换：临界角两侧 status 从 active 翻转为 TIR，不声称连续导数
        """

        radius = 5.0e-6
        # n_i=1.5, n_t=1.0 ⇒ 临界角 θ_c = arcsin(1/1.5) ≈ 41.81°
        critical = math.degrees(math.asin(1.0 / 1.5))
        eps_deg = 0.01
        positions = torch.zeros((2, 3), dtype=torch.float64).unsqueeze(0)
        directions = torch.zeros((2, 3), dtype=torch.float64).unsqueeze(0)
        for index, deg in enumerate(
            (critical - eps_deg, critical + eps_deg),
        ):
            rad = math.radians(deg)
            directions[0, index] = torch.tensor(
                [math.sin(rad), 0.0, math.cos(rad)],
                dtype=torch.float64,
            )
        spectrum = _monochromatic()
        bundle = RayBundle(
            position=positions,
            direction=directions,
            polarization_vector=_transverse_polarization_for_direction(
                directions
            ),
            power=torch.ones((1, 2), dtype=torch.float64),
            refractive_index=torch.full(
                (1, 2),
                1.5,
                dtype=torch.float64,
            ),
            optical_path=torch.zeros((1, 2), dtype=torch.float64),
            status=torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=spectrum,
        )
        sphere = Sphere(radius_of_curvature=radius)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=Vacuum(),
        )
        # 临界角以下：透射 active；以上：TIR
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        assert refracted.status[0, 1] == RAY_STATUS_TOTAL_INTERNAL_REFLECTION


class TestSphereDevicePlacement:
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
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert refracted.position.dtype is real_dtype
        assert refracted.direction.dtype is real_dtype
        assert refracted.power.dtype is real_dtype
        assert refracted.optical_path.dtype is torch.float64
        assert refracted.status.dtype is torch.uint8

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
        refract = RefractAt(
            surface=Sphere(radius_of_curvature=5.0e-6),
            destination_medium=ConstantMedium(index=1.5),
        )
        with _meta_inference((source, refract)) as sandbox:
            bundle = sandbox.module(source)(grid)
            refracted = sandbox.module(refract)(bundle)
        assert refracted.position.is_meta
        assert refracted.position.dtype is torch.float64
        assert refracted.optical_path.dtype is torch.float64
        assert refracted.status.dtype is torch.uint8


class TestSphereTrainableState:
    """
    可训练曲率/aperture Parameter 路径与 state_dict 往返
    """

    def test_trainable_curvature_refracts_correctly(self) -> None:
        """
        Parameter 曲率半径与 float 曲率行为一致
        """

        radius_param = torch.nn.Parameter(
            torch.tensor(5.0e-6, dtype=torch.float64),
        )
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        sphere = Sphere(radius_of_curvature=radius_param)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        assert isinstance(sphere.radius_of_curvature, torch.nn.Parameter)
        _assert_no_nan(refracted)

    def test_state_dict_round_trip_preserves_curvature(self) -> None:
        """
        Parameter Sphere dump-load 回自身：身份保持 Parameter，值精确保留
        """

        radius_param = torch.nn.Parameter(
            torch.tensor(5.0e-6, dtype=torch.float64),
        )
        sphere = Sphere(radius_of_curvature=radius_param)
        state = sphere.state_dict()
        round_trip = Sphere(
            radius_of_curvature=torch.nn.Parameter(
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
        )
        round_trip.load_state_dict(state)
        assert isinstance(round_trip.radius_of_curvature, torch.nn.Parameter)
        assert torch.isclose(
            round_trip.radius_of_curvature,
            torch.tensor(5.0e-6, dtype=torch.float64),
        )


class TestSphereImmutability:
    """
    refract_at 不修改输入 RayBundle（不可变物理值）
    """

    def test_input_bundle_tensors_unchanged(self) -> None:
        """
        refract_at 返回新对象；输入张量不被修改
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
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert refracted is not bundle
        assert torch.equal(bundle.position, original_position)
        assert torch.equal(bundle.direction, original_direction)
        assert torch.equal(bundle.optical_path, original_optical_path)


class TestRefractAtConicEvenAsphere:
    """
    refract_at/RefractAt 在 ConicEvenAsphere 上的证据：球面极限 Snell 一致、光程
    n × distance float64 累加、function/component duality、TIR 以有限 status 终止、
    可训练曲率梯度、meta/real schema 一致
    """

    def test_spherical_limit_refracts_like_sphere(self) -> None:
        """
        k=0/α=0 退化球面：折射后方向与等价 Sphere 折射一致
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
        sphere_refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        conic_refracted = refract_at(
            bundle,
            surface=conic,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert torch.allclose(
            sphere_refracted.direction,
            conic_refracted.direction,
            atol=1.0e-12,
        )
        assert torch.allclose(
            sphere_refracted.position,
            conic_refracted.position,
            atol=1.0e-12,
        )
        _assert_no_nan(conic_refracted)

    def test_oblique_refraction_matches_snell_law(self) -> None:
        """
        斜入射非球面：折射前后切向分量比 = n_i/n_t（远离 TIR）
        """

        n_i = 1.0
        n_t = 1.5
        radius = 8.0e-6
        theta = math.radians(18.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.3e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=direction)
        conic = ConicEvenAsphere(
            curvature=1.0 / radius,
            conic_constant=-0.3,
            even_coefficients=(2.0e3,),

        clear_aperture_radius=5.0e-6,)
        refracted = refract_at(
            bundle,
            surface=conic,
            destination_medium=ConstantMedium(index=n_t),
        )
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        outgoing = refracted.direction[0, 0]
        assert torch.isclose(
            outgoing.norm(),
            torch.ones_like(outgoing.norm()),
            atol=1.0e-9,
        )
        # 折射后方向 z 分量应大于入射（光密介质偏向法线）
        assert float(outgoing[2]) > float(direction[2])
        _assert_no_nan(refracted)

    def test_optical_path_graph_bears_trainable_curvature(self) -> None:
        """
        可训练曲率半径的折射光程保持 autograd 图
        """

        curvature_param = torch.nn.Parameter(
            torch.tensor(1.0 / 5.0e-6, dtype=torch.float64),
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
        conic = ConicEvenAsphere(
            curvature=curvature_param,
            conic_constant=0.0,
        )
        refracted = refract_at(
            bundle,
            surface=conic,
            destination_medium=ConstantMedium(index=1.6),
        )
        refracted.optical_path.sum().backward()
        assert curvature_param.grad is not None

    def test_conic_constant_gradient_matches_central_difference(self) -> None:
        """
        可训练圆锥常数：折射方向 x 分量的 autograd 与中心差分一致（远离 TIR/根切换）
        """

        theta = math.radians(18.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.3e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        base_conic_constant = -0.3
        step = 0.1

        def direction_x(conic_constant_value: float) -> float:
            """
            给定圆锥常数返回折射后方向 x 分量的中心差分参考
            """
            conic = ConicEvenAsphere(
                curvature=1.0 / 8.0e-6,
                conic_constant=torch.nn.Parameter(
                    torch.tensor(conic_constant_value, dtype=torch.float64),
                ),
                even_coefficients=(2.0e3,),

            clear_aperture_radius=5.0e-6,)
            bundle = _bundle(position=positions, direction=direction)
            refracted = refract_at(
                bundle,
                surface=conic,
                destination_medium=ConstantMedium(index=1.5),
            )
            return float(refracted.direction[0, 0, 0].detach())

        conic_constant_param = torch.nn.Parameter(
            torch.tensor(base_conic_constant, dtype=torch.float64),
        )
        conic = ConicEvenAsphere(
            curvature=1.0 / 8.0e-6,
            conic_constant=conic_constant_param,
            even_coefficients=(2.0e3,),

        clear_aperture_radius=5.0e-6,)
        bundle = _bundle(position=positions, direction=direction)
        component = RefractAt(
            surface=conic,
            destination_medium=ConstantMedium(index=1.5),
        )
        refracted = component(bundle)
        refracted.direction[0, 0, 0].backward()
        assert conic_constant_param.grad is not None
        autograd = float(conic_constant_param.grad.detach())
        central = (
            direction_x(base_conic_constant + step)
            - direction_x(base_conic_constant - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e-10)

    def test_even_coefficients_gradient_matches_central_difference(self) -> None:
        """
        可训练偶次系数：折射方向 x 分量的 autograd 与中心差分一致（远离 TIR/根切换）
        """

        theta = math.radians(18.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.3e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        base_coefficient = 2.0e3
        step = 1.0e3

        def direction_x(coefficient_value: float) -> float:
            """
            给定偶次系数返回折射后方向 x 分量的中心差分参考
            """
            conic = ConicEvenAsphere(
                curvature=1.0 / 8.0e-6,
                conic_constant=-0.3,
                even_coefficients=torch.nn.Parameter(
                    torch.tensor([coefficient_value], dtype=torch.float64),
                ),

            clear_aperture_radius=5.0e-6,)
            bundle = _bundle(position=positions, direction=direction)
            refracted = refract_at(
                bundle,
                surface=conic,
                destination_medium=ConstantMedium(index=1.5),
            )
            return float(refracted.direction[0, 0, 0].detach())

        coefficient_param = torch.nn.Parameter(
            torch.tensor([base_coefficient], dtype=torch.float64),
        )
        conic = ConicEvenAsphere(
            curvature=1.0 / 8.0e-6,
            conic_constant=-0.3,
            even_coefficients=coefficient_param,

        clear_aperture_radius=5.0e-6,)
        bundle = _bundle(position=positions, direction=direction)
        component = RefractAt(
            surface=conic,
            destination_medium=ConstantMedium(index=1.5),
        )
        refracted = component(bundle)
        refracted.direction[0, 0, 0].backward()
        assert coefficient_param.grad is not None
        autograd = float(coefficient_param.grad[0].detach())
        central = (
            direction_x(base_coefficient + step)
            - direction_x(base_coefficient - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e-10)

    def test_total_internal_reflection_terminates_transmission(self) -> None:
        """
        光密→光疏 + 大入射角 ⇒ TIR；圆锥面折射路径以有限 status 终止，不改写为反射
        """

        radius = 5.0e-6
        start = torch.tensor(
            [3.5e-6, 0.0, -3.0e-6],
            dtype=torch.float64,
        )
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=1.5),
        )
        conic = ConicEvenAsphere(
            curvature=1.0 / radius,
            conic_constant=0.0,
        )
        refracted = refract_at(
            bundle,
            surface=conic,
            destination_medium=Vacuum(),
        )
        assert refracted.status[0, 0] == RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        # TIR 不改写为反射：方向保持入射方向
        assert torch.allclose(refracted.direction[0, 0], _unit_z())
        # 功率不变（不发明 Fresnel）
        assert torch.equal(refracted.power, bundle.power)
        _assert_no_nan(refracted)

    def test_function_component_duality_on_conic(self) -> None:
        """
        refract_at 函数与 RefractAt 组件在圆锥面上输出完全一致
        """

        radius = 6.0e-6
        theta = math.radians(12.0)
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
            conic_constant=0.3,
            even_coefficients=(1.5e3,),

        clear_aperture_radius=5.0e-6,)
        component = RefractAt(
            surface=conic,
            destination_medium=ConstantMedium(index=1.5),
        )
        function_output = refract_at(
            bundle,
            surface=conic,
            destination_medium=ConstantMedium(index=1.5),
        )
        component_output = component(bundle)
        assert torch.equal(function_output.position, component_output.position)
        assert torch.equal(function_output.direction, component_output.direction)
        assert torch.equal(
            function_output.optical_path,
            component_output.optical_path,
        )
        assert torch.equal(function_output.status, component_output.status)

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
        refract = RefractAt(
            surface=ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=-0.5,
                even_coefficients=(1.0e3,),

            clear_aperture_radius=5.0e-6,),
            destination_medium=ConstantMedium(index=1.5),
        )
        with _meta_inference((source, refract)) as sandbox:
            bundle = sandbox.module(source)(grid)
            refracted = sandbox.module(refract)(bundle)
        assert refracted.position.is_meta
        assert refracted.position.dtype is torch.float64
        assert refracted.optical_path.dtype is torch.float64
        assert refracted.status.dtype is torch.uint8


class TestRefractAtConicRayBundleQuantities:
    """
    ``refract_at``/``RefractAt`` 在圆锥面上每条 Ray Bundle 量的公共接口直接证据
    ：成功透射路径的位置前进、逐光线折射率切目标、光程累加、功率不变；
    TIR 路径的折射率保留入射。该节点同时覆盖位置、光程、
    折射率切换/功率的整体量。
    """

    def test_active_transmit_advances_position_and_switches_index(self) -> None:
        """
        成功透射：位置前进到圆锥顶点；逐光线折射率切目标介质；光程累加入射 n × 距离；
        功率不变（非 TIR 路径）
        """

        n_i = 1.3
        n_t = 1.5
        curvature = 1.0 / 5.0e-6
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=n_i),
        )
        conic = ConicEvenAsphere(curvature=curvature, conic_constant=0.0)
        refracted = refract_at(
            bundle,
            surface=conic,
            destination_medium=ConstantMedium(index=n_t),
        )
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        # 位置前进到圆锥顶点（沿轴正入射命中顶点 z=0）
        assert torch.isclose(
            refracted.position[0, 0, 2],
            torch.tensor(0.0, dtype=torch.float64),
            atol=1.0e-12,
        )
        # 光程 = n_incident × 几何距离（distance = 3.0e-6）
        assert torch.allclose(
            refracted.optical_path,
            torch.tensor([[n_i * 3.0e-6]], dtype=torch.float64),
            atol=1.0e-18,
        )
        # 成功透射光线逐光线折射率切到目标介质评估值
        assert torch.allclose(
            refracted.refractive_index,
            torch.full_like(refracted.refractive_index, n_t),
        )
        # 功率不变（非 TIR 路径，不发明 Fresnel）
        assert torch.equal(refracted.power, bundle.power)
        _assert_no_nan(refracted)

    def test_tir_retains_incident_index_on_conic(self) -> None:
        """
        圆锥面 TIR：逐光线折射率精确保留入射值（不被目标介质改写）
        """

        n_i = 1.5
        radius = 5.0e-6
        start = torch.tensor(
            [3.5e-6, 0.0, -3.0e-6],
            dtype=torch.float64,
        )
        positions = start.unsqueeze(0).unsqueeze(0)
        bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            medium=ConstantMedium(index=n_i),
        )
        conic = ConicEvenAsphere(curvature=1.0 / radius, conic_constant=0.0)
        refracted = refract_at(
            bundle,
            surface=conic,
            destination_medium=Vacuum(),
        )
        assert refracted.status[0, 0] == RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        # 逐光线折射率精确保留入射值
        assert torch.allclose(
            refracted.refractive_index,
            torch.full_like(refracted.refractive_index, n_i),
        )

    def test_missed_ray_retains_incident_index_on_conic(self) -> None:
        """
        圆锥面未命中光线：逐光线折射率精确保留入射值（CONTEXT 核心正确性）
        """

        n_i = 1.3
        positions = torch.zeros((1, 4, 3), dtype=torch.float64)
        positions[..., 2] = -2.0e-6
        bundle = _bundle(
            position=positions,
            direction=torch.tensor([1.0, 0.0, 0.0]),
            medium=ConstantMedium(index=n_i),
        )
        conic = ConicEvenAsphere(curvature=1.0 / 5.0e-6, conic_constant=0.0)
        refracted = refract_at(
            bundle,
            surface=conic,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert bool(
            (refracted.status == RAY_STATUS_SURFACE_MISSED).all(),
        )
        # 未命中光线精确保留入射 per-ray 折射率
        assert torch.equal(
            refracted.refractive_index,
            bundle.refractive_index,
        )


class TestRefractAtMixedStatusPerRayIndex:
    """
    单 bundle 四态（active/missed/vignetted/TIR）逐光线折射率公共接口证据（
    CONTEXT 核心正确性）：成功透射光线切目标介质评估值；missed/vignetted/TIR 精确保留
    入射折射率。既有 ``test_four_terminal_states_distinguishable`` 证 status 不证
    逐光线折射率，此处补。
    """

    def test_four_terminal_states_per_ray_refractive_index(self) -> None:
        """
        四态同 bundle：active 切目标；missed/vignetted/TIR 精确保留入射折射率
        """

        radius = 5.0e-6
        aperture = 4.5e-6
        n_i = 1.5
        positions = torch.zeros((4, 3), dtype=torch.float64).unsqueeze(0)
        positions[0, 0] = torch.tensor([0.0, 0.0, -3.0e-6])
        positions[0, 1] = torch.tensor([8.0e-6, 0.0, -3.0e-6])
        positions[0, 2] = torch.tensor([4.8e-6, 0.0, -3.0e-6])
        positions[0, 3] = torch.tensor([4.0e-6, 0.0, -3.0e-6])
        directions = _unit_z().view(1, 1, 3).expand(1, 4, 3).clone()
        spectrum = _monochromatic()
        bundle = RayBundle(
            position=positions,
            direction=directions,
            polarization_vector=_transverse_polarization_for_direction(
                directions
            ),
            power=torch.ones((1, 4), dtype=torch.float64),
            refractive_index=torch.full((1, 4), n_i, dtype=torch.float64),
            optical_path=torch.zeros((1, 4), dtype=torch.float64),
            status=torch.full((1, 4), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=spectrum,
        )
        sphere = Sphere(
            vertex=(0.0, 0.0, 0.0),
            radius_of_curvature=radius,
            clear_aperture_radius=aperture,
        )
        destination = Vacuum()
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=destination,
        )
        # 状态四态齐备（沿用既有断言风格）
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        assert refracted.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert refracted.status[0, 2] == RAY_STATUS_VIGNETTED
        assert refracted.status[0, 3] == RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        # active 光线：逐光线折射率切到目标介质在 authored 波长评估值（真空 = 1.0）
        assert torch.isclose(
            refracted.refractive_index[0, 0],
            torch.tensor(1.0, dtype=torch.float64),
            atol=1.0e-12,
        )
        # missed/vignetted/TIR 光线：精确保留入射折射率 n_i
        for ray_index in (1, 2, 3):
            assert torch.isclose(
                refracted.refractive_index[0, ray_index],
                torch.tensor(n_i, dtype=torch.float64),
            )
        _assert_no_nan(refracted)


class TestSurfaceStateValidatedAtConsumption:
    """
    消费期 surface 状态验证：optimizer 变异 trainable Parameter 后，公共
    stateless 入口在数值工作前抛稳定身份；direct 调用与 component.forward（Workstation
    replay 的执行路径）行为一致
    """

    def test_mutated_sphere_radius_non_finite_rejected(self) -> None:
        """
        构造后把曲率半径改成 NaN ⇒ consumption 期抛身份
        （双精度；direct 与 replay 一致）
        """

        real_dtype = torch.float64
        radius_param = torch.nn.Parameter(
            torch.tensor(5.0e-6, dtype=torch.float64),
        )
        sphere = Sphere(radius_of_curvature=radius_param)
        component = RefractAt(
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        bundle = _bundle_at_origin(
            direction=_unit_z(real_dtype),
            real_dtype=real_dtype,
        )
        with torch.no_grad():
            radius_param.fill_(float("nan"))
        with pytest.raises(OpticalValueError) as direct_call:
            refract_at(
                bundle,
                surface=sphere,
                destination_medium=ConstantMedium(index=1.5),
            )
        assert (
            direct_call.value.identity
            == "sphere_radius_of_curvature_invalid"
        )
        with pytest.raises(OpticalValueError) as replay_path:
            component(bundle)
        assert (
            replay_path.value.identity
            == "sphere_radius_of_curvature_invalid"
        )

    def test_mutated_sphere_radius_zero_rejected(self) -> None:
        """
        构造后把曲率半径参数改成 0 ⇒ consumption 期抛同一身份（零曲率无球面意义）
        """

        radius_param = torch.nn.Parameter(
            torch.tensor(5.0e-6, dtype=torch.float64),
        )
        sphere = Sphere(radius_of_curvature=radius_param)
        component = RefractAt(
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        bundle = _bundle_at_origin(direction=_unit_z())
        with torch.no_grad():
            radius_param.zero_()
        with pytest.raises(OpticalValueError) as rejected:
            component(bundle)
        assert (
            rejected.value.identity == "sphere_radius_of_curvature_invalid"
        )

    def test_mutated_sphere_vertex_non_finite_rejected(self) -> None:
        """
        构造后把可训练顶点原点改成 NaN ⇒ consumption 期抛 ``sphere_vertex_invalid``
        （构造期验证不覆盖 optimizer 变异后，consumption 边界补验）
        """

        origin_param = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 5.0e-6), dtype=torch.float64),
        )
        sphere = Sphere(
            vertex=origin_param,
            radius_of_curvature=5.0e-6,
        )
        component = RefractAt(
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        bundle = _bundle_at_origin(direction=_unit_z())
        with torch.no_grad():
            origin_param[2].fill_(float("nan"))
        with pytest.raises(OpticalValueError) as direct_call:
            refract_at(
                bundle,
                surface=sphere,
                destination_medium=ConstantMedium(index=1.5),
            )
        assert direct_call.value.identity == "sphere_vertex_invalid"
        with pytest.raises(OpticalValueError) as replay_path:
            component(bundle)
        assert replay_path.value.identity == "sphere_vertex_invalid"

    def test_mutated_sphere_aperture_non_positive_rejected(self) -> None:
        """
        构造后把硬孔径 Buffer 改成负数 ⇒ consumption 期抛孔径身份
        """

        sphere = Sphere(
            radius_of_curvature=5.0e-6,
            clear_aperture_radius=1.0e-5,
        )
        component = RefractAt(
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        bundle = _bundle_at_origin(direction=_unit_z())
        with torch.no_grad():
            sphere.clear_aperture_radius.fill_(-1.0)
        with pytest.raises(OpticalValueError) as rejected:
            component(bundle)
        assert (
            rejected.value.identity
            == "sphere_clear_aperture_radius_invalid"
        )

    def test_mutated_conic_curvature_non_finite_rejected(self) -> None:
        """
        构造后把可训练曲率改成 NaN ⇒ consumption 期抛 ``conic_curvature_invalid``
        """

        curvature_param = torch.nn.Parameter(
            torch.tensor(1.0 / 5.0e-6, dtype=torch.float64),
        )
        conic = ConicEvenAsphere(
            curvature=curvature_param,
            conic_constant=-0.5,
        )
        component = RefractAt(
            surface=conic,
            destination_medium=ConstantMedium(index=1.5),
        )
        bundle = _bundle_at_origin(direction=_unit_z())
        with torch.no_grad():
            curvature_param.fill_(float("nan"))
        with pytest.raises(OpticalValueError) as direct_call:
            refract_at(
                bundle,
                surface=conic,
                destination_medium=ConstantMedium(index=1.5),
            )
        assert direct_call.value.identity == "conic_curvature_invalid"
        with pytest.raises(OpticalValueError) as replay_path:
            component(bundle)
        assert replay_path.value.identity == "conic_curvature_invalid"

    def test_mutated_conic_vertex_non_finite_rejected(self) -> None:
        """
        构造后把可训练圆锥面顶点改成 NaN ⇒ consumption 期抛 ``conic_vertex_invalid``
        """

        origin_param = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 5.0e-6), dtype=torch.float64),
        )
        conic = ConicEvenAsphere(
            vertex=origin_param,
            curvature=1.0 / 5.0e-6,
            conic_constant=-0.5,
        )
        component = RefractAt(
            surface=conic,
            destination_medium=ConstantMedium(index=1.5),
        )
        bundle = _bundle_at_origin(direction=_unit_z())
        with torch.no_grad():
            origin_param[0].fill_(float("inf"))
        with pytest.raises(OpticalValueError) as rejected:
            component(bundle)
        assert rejected.value.identity == "conic_vertex_invalid"

    def test_valid_trainable_surface_preserves_gradient_at_consumption(
        self,
    ) -> None:
        """
        valid trainable surface 的 consumption 验证不破坏计算图：梯度仍流过曲率半径
        与顶点原点两个 trainable Parameter（验证只读判断，不 detach/clone/标量提取）
        """

        radius_param = torch.nn.Parameter(
            torch.tensor(5.0e-6, dtype=torch.float64),
        )
        origin_param = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 5.0e-6), dtype=torch.float64),
        )
        sphere = Sphere(
            vertex=origin_param,
            radius_of_curvature=radius_param,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = _bundle(position=positions, direction=_unit_z())
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        refracted.position.sum().backward()
        assert radius_param.grad is not None
        assert torch.isfinite(radius_param.grad).all()
        assert origin_param.grad is not None
        assert torch.isfinite(origin_param.grad).all()

    # -- fixed Buffer 与 Parameter 姿态在消费边界经同一契约复核 ------------

    @pytest.mark.parametrize(
        ("factory", "pose_attribute", "expected_identity"),
        (
            (_posed_plane, "origin", "plane_origin_invalid"),
            (_posed_sphere, "vertex", "sphere_vertex_invalid"),
            (_posed_conic, "vertex", "conic_vertex_invalid"),
        ),
    )
    def test_fixed_buffer_origin_non_finite_rejected_at_consume_boundary(
        self,
        factory: _SurfaceFactory,
        pose_attribute: str,
        expected_identity: str,
    ) -> None:
        """
        构造后把固定 Buffer 姿态点变异为 NaN ⇒ 消费边界抛稳定的姿态点身份
        （reflect_at 在数值工作前复核，故动作抛错而不会
        返回 missed 状态——pytest.raises 本身即证明错误先于任何 status 返回）
        """

        surface = factory()
        pose_point = getattr(surface, pose_attribute)
        assert not isinstance(pose_point, torch.nn.Parameter)
        with torch.no_grad():
            pose_point[2].fill_(float("nan"))
        with pytest.raises(OpticalValueError) as rejected:
            reflect_at(_bundle_at_origin(direction=_unit_z()), surface=surface)
        assert rejected.value.identity == expected_identity

    @pytest.mark.parametrize(
        ("factory", "tangent_attribute", "expected_identity"),
        (
            (_posed_plane, "tangent_x", "plane_tangent_x_not_unit"),
            (_posed_plane, "tangent_y", "plane_tangent_y_not_unit"),
            (_posed_sphere, "tangent_x", "sphere_tangent_x_not_unit"),
            (_posed_sphere, "tangent_y", "sphere_tangent_y_not_unit"),
            (_posed_conic, "tangent_x", "conic_tangent_x_not_unit"),
            (_posed_conic, "tangent_y", "conic_tangent_y_not_unit"),
        ),
    )
    def test_fixed_buffer_pose_axis_non_unit_rejected_at_consume_boundary(
        self,
        factory: _SurfaceFactory,
        tangent_attribute: str,
        expected_identity: str,
    ) -> None:
        """
        构造后把固定 Buffer 基向量变异为 NaN（非单位）⇒ 消费边界抛
        ``<surface>_axis_*_not_unit``（镜像构造期 _require_unit_vector，同一身份；
        axis Buffer 在消费边界复核）
        """

        surface = factory()
        tangent = getattr(surface, tangent_attribute)
        assert not isinstance(tangent, torch.nn.Parameter)
        with torch.no_grad():
            tangent[0].fill_(float("nan"))
        with pytest.raises(OpticalValueError) as rejected:
            reflect_at(_bundle_at_origin(direction=_unit_z()), surface=surface)
        assert rejected.value.identity == expected_identity

    @pytest.mark.parametrize(
        ("factory", "prefix", "expected_identity"),
        (
            (_posed_plane, "plane", "plane_basis_not_orthogonal"),
            (_posed_sphere, "sphere", "sphere_basis_not_orthogonal"),
            (_posed_conic, "conic", "conic_basis_not_orthogonal"),
        ),
    )
    def test_fixed_buffer_pose_basis_non_orthonormal_rejected_at_consume_boundary(
        self,
        factory: _SurfaceFactory,
        prefix: str,
        expected_identity: str,
    ) -> None:
        """
        构造后把横向基向量旋至与纵向基向量非正交 ⇒ 消费边界抛
        ``<surface>_basis_not_orthogonal``（镜像构造期
        source-owned authored basis validation）
        """

        surface = factory()
        tangent_y = surface.tangent_y
        assert not isinstance(tangent_y, torch.nn.Parameter)
        tilted = torch.tensor(
            (0.7071067811865476, 0.7071067811865475, 0.0),
            dtype=torch.float64,
        )
        with torch.no_grad():
            tangent_y.copy_(tilted)
        with pytest.raises(OpticalValueError) as rejected:
            reflect_at(_bundle_at_origin(direction=_unit_z()), surface=surface)
        assert rejected.value.identity == expected_identity

    @pytest.mark.parametrize(
        ("factory", "pose_attribute", "expected_identity"),
        (
            (_posed_plane, "origin", "plane_origin_invalid"),
            (_posed_sphere, "vertex", "sphere_vertex_invalid"),
            (_posed_conic, "vertex", "conic_vertex_invalid"),
        ),
    )
    def test_buffer_and_parameter_origin_fail_identically(
        self,
        factory: _SurfaceFactory,
        pose_attribute: str,
        expected_identity: str,
    ) -> None:
        """
        固定 Buffer 原点与可训练 Parameter 原点变异为 NaN ⇒ 抛同一身份（DoD #10：
        authored fixed 与 trainable state 经同一稳定契约失败）。reflect_at 是基线下
        唯一同时接受三种面的公共消费边界，故两条路径都经它验证
        """

        buffer_surface = factory()
        buffer_pose_point = getattr(buffer_surface, pose_attribute)
        parameter_pose_point = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 0.0), dtype=torch.float64),
        )
        parameter_surface = factory(pose_point=parameter_pose_point)
        with torch.no_grad():
            buffer_pose_point[0].fill_(float("nan"))
            parameter_pose_point[0].fill_(float("nan"))
        with pytest.raises(OpticalValueError) as buffer_rejected:
            reflect_at(
                _bundle_at_origin(direction=_unit_z()),
                surface=buffer_surface,
            )
        with pytest.raises(OpticalValueError) as parameter_rejected:
            reflect_at(
                _bundle_at_origin(direction=_unit_z()),
                surface=parameter_surface,
            )
        assert buffer_rejected.value.identity == expected_identity
        assert parameter_rejected.value.identity == expected_identity


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_refract_at_surface_families_match_cpu_on_cuda() -> None:
    """
    RefractAt 在三类曲面上保持全部 Ray Bundle 量与 CPU 一致
    """

    positions = torch.tensor(
        [[[-0.2e-6, 0.0, -3.0e-6], [0.2e-6, 0.0, -3.0e-6]]],
        dtype=torch.float64,
    )
    for surface in (
        _posed_plane(),
        _posed_sphere(),
        _posed_conic(),
    ):
        cpu_bundle = _bundle(position=positions, direction=_unit_z())
        cuda_bundle = _bundle(
            position=positions,
            direction=_unit_z(),
            device="cuda:0",
        )
        cpu_output = refract_at(
            cpu_bundle,
            surface=surface,
            destination_medium=ConstantMedium(index=1.5),
        )
        cuda_output = refract_at(
            cuda_bundle,
            surface=surface.cuda(),
            destination_medium=ConstantMedium(index=1.5),
        )
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

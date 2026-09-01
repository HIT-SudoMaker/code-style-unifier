
from __future__ import annotations

from fractions import Fraction
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
from chromatix_next.optics.propagation import TraceTo, trace_to
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


def _bundle_at_origin(
    *,
    direction: torch.Tensor,
    spectrum: Spectrum | None = None,
    medium: Medium | None = None,
    spectral_count: int = 1,
    ray_count: int = 4,
    real_dtype: torch.dtype = torch.float64,
    requires_grad: bool = False,
    device: torch.device | str = "cpu",
) -> RayBundle:
    if spectrum is None:
        if spectral_count == 1:
            spectrum_value: Spectrum = _monochromatic()
        else:
            spectrum_value = Spectrum(
                wavelengths=tuple(
                    1.0e-6 + 0.2e-6 * index for index in range(spectral_count)
                ),
                weights=tuple(1.0 for _ in range(spectral_count)),
            )
    else:
        spectrum_value = spectrum
    positions = torch.zeros(
        (spectral_count, ray_count, 3),
        dtype=real_dtype,
        device=device,
        requires_grad=requires_grad,
    )
    direction_unit = direction.to(dtype=real_dtype, device=device)
    direction_broadcast = direction_unit.view(1, 1, 3).expand(
        spectral_count,
        ray_count,
        3,
    )
    power = torch.ones(
        (spectral_count, ray_count),
        dtype=real_dtype,
        device=device,
    )
    resolved_medium = medium or Vacuum()
    wavelengths = torch.tensor(
        spectrum_value.wavelengths,
        dtype=real_dtype,
        device=device,
    )
    indices = resolved_medium.refractive_index(wavelengths).to(real_dtype)
    refractive_index = indices.view(spectral_count, 1).expand(
        spectral_count,
        ray_count,
    )
    optical_path = torch.zeros(
        (spectral_count, ray_count),
        dtype=torch.float64,
        device=device,
    )
    status = torch.full(
        (spectral_count, ray_count),
        RAY_STATUS_ACTIVE,
        dtype=torch.uint8,
        device=device,
    )
    return RayBundle(
        position=positions,
        direction=direction_broadcast,
        polarization_vector=_transverse_polarization_for_direction(
            direction_broadcast
        ),
        power=power,
        refractive_index=refractive_index,
        optical_path=optical_path,
        status=status,
        spectrum=spectrum_value,
    )


def _unit_z_direction(real_dtype: torch.dtype = torch.float64) -> torch.Tensor:
    # 沿 +z 的单位方向
    direction = torch.zeros(3, dtype=real_dtype)
    direction[2] = 1.0
    return direction


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


class TestTraceToPlaneRoleContract:
    """
    trace_to 配对接口的传播角色契约与 Assembly/Host 接纳
    """

    def test_role_is_propagation_literal(self) -> None:
        """
        TraceTo 声明唯一不可改写的 propagation 角色
        """

        component = TraceTo(surface=Plane())
        assert component.role == "propagation"
        with pytest.raises(AttributeError):
            component.role = "element"  # type: ignore[misc]

    def test_forward_returns_ray_bundle(self) -> None:
        """
        真实前向只产生 RayBundle 强物理值
        """

        component = TraceTo(
            surface=Plane(origin=(0.0, 0.0, 1.0e-6)),
        )
        bundle = component(_bundle_at_origin(direction=_unit_z_direction()))
        assert isinstance(bundle, RayBundle)


class TestPlanePoseAndApertureValidation:
    """
    Plane 姿态与 aperture 校验：单位正交右手基；正有限 aperture 标量
    """

    def test_default_pose_yields_plus_z_normal(self) -> None:
        """
        默认 axis_y=ê_x、axis_x=ê_y ⇒ 法线 = +ê_z
        """

        plane = Plane()
        normal = plane.normal
        assert torch.allclose(
            normal,
            torch.tensor([0.0, 0.0, 1.0], dtype=normal.dtype),
            atol=1.0e-6,
        )

    def test_non_unit_axis_rejected(self) -> None:
        """
        非单位 axis ⇒ 拒绝；平面不静默归一化 authored 物理
        """

        with pytest.raises(OpticalValueError) as rejected:
            Plane(tangent_x=(2.0, 0.0, 0.0))
        assert rejected.value.identity == "plane_tangent_x_not_unit"

    def test_parallel_axes_rejected(self) -> None:
        """
        平行两轴 ⇒ 非正交拒绝
        """

        with pytest.raises(OpticalValueError) as rejected:
            Plane(
                tangent_x=(1.0, 0.0, 0.0),
                tangent_y=(1.0, 0.0, 0.0),
            )
        assert rejected.value.identity == "plane_basis_not_orthogonal"

    def test_swapped_basis_yields_minus_z_normal(self) -> None:
        """
        交换 axis_y/axis_x ⇒ 法线 = -ê_z；作者通过姿态控制朝向
        """

        plane = Plane(
            tangent_x=(0.0, 1.0, 0.0),
            tangent_y=(1.0, 0.0, 0.0),
        )
        normal = plane.normal
        assert torch.allclose(
            normal,
            torch.tensor([0.0, 0.0, -1.0], dtype=normal.dtype),
            atol=1.0e-6,
        )

    @pytest.mark.parametrize(
        "invalid_radius",
        (0.0, -1.0, float("nan"), float("inf")),
    )
    def test_non_positive_aperture_rejected(
        self,
        invalid_radius: float,
    ) -> None:
        """
        零、负、非有限 aperture ⇒ 拒绝
        """

        with pytest.raises(OpticalValueError) as rejected:
            Plane(clear_aperture_radius=invalid_radius)
        assert rejected.value.identity == "plane_clear_aperture_radius_invalid"

    def test_plain_non_parameter_tensor_aperture_rejected(self) -> None:
        """
        普通（非 Parameter）张量 ⇒ 稳定域类型错误，不泄漏裸断言
        """

        with pytest.raises(OpticalTypeError) as rejected:
            Plane(
                clear_aperture_radius=torch.tensor(4.0e-6),  # type: ignore[arg-type]
            )
        assert (
            rejected.value.identity
            == "plane_clear_aperture_radius_invalid"
        )

    def test_trace_to_rejects_unregistered_surface(self) -> None:
        """
        trace_to 只接受已注册的面类型；未注册的对象类型拒绝
        """

        bundle = _bundle_at_origin(direction=_unit_z_direction())
        with pytest.raises(OpticalTypeError) as rejected:
            trace_to(bundle, surface=object())  # type: ignore[arg-type]
        assert rejected.value.identity == "trace_to_surface_invalid"

    def test_trace_to_rejects_non_bundle_input(self) -> None:
        """
        trace_to 只能作用于 RayBundle；其他类型拒绝
        """

        with pytest.raises(OpticalTypeError) as rejected:
            trace_to(object(), surface=Plane())  # type: ignore[arg-type]
        assert rejected.value.identity == "trace_to_bundle_invalid"


class TestTraceToPlaneAnalyticIntersection:
    """
    独立解析的平面交集：ordinary/parallel/rear-facing/aperture-boundary 四类
    """

    def test_ordinary_intersection_matches_analytic(self) -> None:
        """
        沿 +z 的 ray 与 z=d 的平面相遇：位置 = (x, y, d)；解析 t = d
        """

        real_dtype = torch.float64
        axial_distance = 1.5e-6
        bundle = _bundle_at_origin(
            direction=_unit_z_direction(real_dtype),
            real_dtype=real_dtype,
        )
        plane = Plane(origin=(0.0, 0.0, axial_distance))
        advanced = trace_to(bundle, surface=plane)
        expected_z = torch.full(
            (1, bundle.ray_count),
            axial_distance,
            dtype=real_dtype,
        )
        assert torch.allclose(advanced.position[..., 2], expected_z)
        assert torch.allclose(
            advanced.position[..., :2],
            torch.zeros_like(advanced.position[..., :2]),
        )
        # 状态保持 active；方向与功率不变
        assert torch.equal(
            advanced.status,
            torch.full_like(advanced.status, RAY_STATUS_ACTIVE),
        )
        assert torch.equal(advanced.direction, bundle.direction)
        assert torch.equal(advanced.power, bundle.power)
        _assert_no_nan(advanced)

    def test_parallel_ray_marked_missed(self) -> None:
        """
        沿 +x 的 ray 与 z=d 平面：denominator=0 ⇒ 全部 missed，保留原位
        """

        along_x = torch.tensor([1.0, 0.0, 0.0])
        bundle = _bundle_at_origin(direction=along_x)
        plane = Plane(origin=(0.0, 0.0, 1.0e-6))
        advanced = trace_to(bundle, surface=plane)
        assert torch.equal(
            advanced.status,
            torch.full_like(advanced.status, RAY_STATUS_SURFACE_MISSED),
        )
        # 保留有限 last state：位置、光程、方向、功率均不变
        assert torch.equal(advanced.position, bundle.position)
        assert torch.equal(advanced.optical_path, bundle.optical_path)
        assert torch.equal(advanced.direction, bundle.direction)
        assert torch.equal(advanced.power, bundle.power)
        _assert_no_nan(advanced)

    def test_rear_facing_ray_marked_missed(self) -> None:
        """
        沿 -z 的 ray 与 z=d>0 平面：t=-d<0 ⇒ 全部 missed，保留原位
        """

        backward = torch.tensor([0.0, 0.0, -1.0])
        bundle = _bundle_at_origin(direction=backward)
        plane = Plane(origin=(0.0, 0.0, 1.0e-6))
        advanced = trace_to(bundle, surface=plane)
        assert torch.equal(
            advanced.status,
            torch.full_like(advanced.status, RAY_STATUS_SURFACE_MISSED),
        )
        assert torch.equal(advanced.position, bundle.position)
        assert torch.equal(advanced.optical_path, bundle.optical_path)
        _assert_no_nan(advanced)

    def test_aperture_boundary_active_inside_vignetted_outside(self) -> None:
        """
        半径 R 的圆形 aperture：径向 r<R ⇒ active；r>R ⇒ vignetted
        """

        radius = 1.0e-6
        positions = torch.tensor(
            [[0.5e-6, 0.0, 0.0], [2.0e-6, 0.0, 0.0]],
            dtype=torch.float64,
        ).unsqueeze(0)  # (1, 2, 3)
        direction = _unit_z_direction().view(1, 1, 3).expand(1, 2, 3)
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
        advanced = trace_to(bundle, surface=plane)
        # 第一束光线在孔径内：active
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        # 第二束光线在孔径外：vignetted
        assert advanced.status[0, 1] == RAY_STATUS_VIGNETTED
        # vignetted ray 仍前进到 aperture 平面交点（有限 last position）
        assert torch.isclose(
            advanced.position[0, 1, 2],
            torch.tensor(1.0e-6, dtype=torch.float64),
            atol=1.0e-12,
        )
        _assert_no_nan(advanced)

    def test_unapertured_plane_is_physically_infinite(self) -> None:
        """
        无 aperture 的平面不产生 vignetted；远距 ray 仍 active
        """

        positions = torch.tensor(
            [[1.0e3, -2.0e3, 0.0]],
            dtype=torch.float64,
        ).unsqueeze(0)
        direction = _unit_z_direction().view(1, 1, 3).expand(1, 1, 3)
        bundle = RayBundle(
            position=positions,
            direction=direction,
            polarization_vector=_transverse_polarization_for_direction(
                direction
            ),
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.ones((1, 1), dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        plane = Plane(origin=(0.0, 0.0, 1.0e-6))
        advanced = trace_to(bundle, surface=plane)
        assert torch.equal(
            advanced.status,
            torch.full_like(advanced.status, RAY_STATUS_ACTIVE),
        )

    def test_unrepresentable_active_distance_raises_stable_error(self) -> None:
        """
        拓扑命中但双精度距离不可表示时，以稳定身份闭合失败
        """

        diagonal_component = math.sqrt(0.5)
        tiny_component = 2.0**-600
        direction = torch.tensor(
            [diagonal_component, diagonal_component, tiny_component],
            dtype=torch.float64,
        )
        bundle = _bundle_at_origin(direction=direction, ray_count=1)
        plane = Plane(
            origin=direction.clone(),
            tangent_x=(diagonal_component, diagonal_component, 0.0),
            tangent_y=(
                -tiny_component * diagonal_component,
                tiny_component * diagonal_component,
                1.0,
            ),
        )

        with pytest.raises(OpticalValueError) as rejected:
            trace_to(bundle, surface=plane)
        assert rejected.value.identity == "ray_surface_distance_unresolvable"
        assert torch.equal(bundle.position, torch.zeros_like(bundle.position))
        assert torch.equal(bundle.optical_path, torch.zeros_like(bundle.optical_path))


class TestTraceToSurfaceIntegration:
    """
    三类公共表面各自承载追迹动作的复合证据
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
        每类表面均推进命中通道，并保留错过与既终态通道
        """

        bundle = _mixed_surface_bundle()
        advanced = trace_to(bundle, surface=surface)

        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert torch.allclose(
            advanced.position[0, 0],
            torch.zeros(3, dtype=torch.float64),
            atol=1.0e-12,
        )
        assert torch.equal(advanced.direction[0, 0], bundle.direction[0, 0])
        assert torch.isclose(
            advanced.optical_path[0, 0],
            torch.tensor(1.3 * 3.0e-6, dtype=torch.float64),
            atol=1.0e-15,
        )
        assert advanced.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert torch.equal(advanced.position[0, 1], bundle.position[0, 1])
        assert torch.equal(advanced.direction[0, 1], bundle.direction[0, 1])
        assert torch.equal(
            advanced.polarization_vector[0, 1],
            bundle.polarization_vector[0, 1],
        )
        assert torch.equal(advanced.power[0, 1], bundle.power[0, 1])
        assert torch.equal(
            advanced.refractive_index[0, 1],
            bundle.refractive_index[0, 1],
        )
        assert torch.equal(
            advanced.optical_path[0, 1],
            bundle.optical_path[0, 1],
        )
        assert torch.equal(advanced.position[0, 2], bundle.position[0, 2])
        assert torch.equal(advanced.direction[0, 2], bundle.direction[0, 2])
        assert torch.equal(
            advanced.polarization_vector[0, 2],
            bundle.polarization_vector[0, 2],
        )
        assert torch.equal(advanced.power[0, 2], bundle.power[0, 2])
        assert torch.equal(
            advanced.refractive_index[0, 2],
            bundle.refractive_index[0, 2],
        )
        assert torch.equal(
            advanced.optical_path[0, 2],
            bundle.optical_path[0, 2],
        )
        assert advanced.status[0, 2] == RAY_STATUS_VIGNETTED
        assert torch.equal(advanced.power, bundle.power)
        assert torch.equal(advanced.refractive_index, bundle.refractive_index)
        _assert_no_nan(advanced)

        if isinstance(surface, Plane):
            assert advanced.status[0, 3] == RAY_STATUS_VIGNETTED
            assert torch.allclose(
                advanced.position[0, 3],
                torch.tensor([3.0e-6, 0.0, 0.0], dtype=torch.float64),
                atol=1.0e-12,
            )
            assert torch.isclose(
                advanced.optical_path[0, 3],
                bundle.optical_path[0, 3]
                + bundle.refractive_index[0, 3]
                * torch.tensor(3.0e-6, dtype=torch.float64),
                atol=1.0e-15,
            )
            assert (
                advanced.refractive_index[0, 3]
                == bundle.refractive_index[0, 3]
            )
            assert advanced.power[0, 3] == bundle.power[0, 3]
            assert torch.equal(
                advanced.direction[0, 3],
                bundle.direction[0, 3],
            )
            assert torch.equal(
                advanced.polarization_vector[0, 3],
                bundle.polarization_vector[0, 3],
            )


class TestTraceToPlaneOpticalPath:
    """
    Optical Path 累加 n(λ) × 几何距离；float64 graph-bearing；多平面链累加
    """

    @pytest.mark.parametrize(
        ("index", "expected_factor"),
        ((1.0, 1.0), (1.5, 1.5), (2.0, 2.0)),
    )
    def test_optical_path_accumulates_index_times_distance(
        self,
        index: float,
        expected_factor: float,
    ) -> None:
        """
        OP_d = n × d；真空 n=1，恒定介质 n=index ⇒ OP=index × d
        """

        axial_distance = 2.0e-6
        medium = ConstantMedium(index=index)
        bundle = _bundle_at_origin(
            direction=_unit_z_direction(),
            medium=medium,
        )
        plane = Plane(origin=(0.0, 0.0, axial_distance))
        advanced = trace_to(bundle, surface=plane)
        assert advanced.optical_path.dtype is torch.float64
        expected_optical_path = torch.full(
            (1, bundle.ray_count),
            expected_factor * axial_distance,
            dtype=torch.float64,
        )
        assert torch.allclose(
            advanced.optical_path,
            expected_optical_path,
            atol=1.0e-18,
        )

    def test_optical_path_graph_bears_axial_spacing_gradient(self) -> None:
        """
        可训练轴向间距（origin.z 为 Parameter）的光程保持 autograd 计算图
        """

        origin = torch.nn.Parameter(
            torch.tensor(
                [0.0, 0.0, 2.0e-6],
                dtype=torch.float64,
            ),
        )
        bundle = _bundle_at_origin(
            direction=_unit_z_direction(),
            medium=ConstantMedium(index=1.5),
        )
        plane = Plane(origin=origin)
        advanced = trace_to(bundle, surface=plane)
        advanced.optical_path.sum().backward()
        # 光程 = n × 间距，对 4 条光线求和 ⇒ 总光程对 origin[2] 的导数 = 1.5 × 4
        assert origin.grad is not None
        assert torch.isclose(
            origin.grad[2],
            torch.tensor(6.0, dtype=torch.float64),
        )
        # 横向分量不参与光程累加 ⇒ 梯度为零
        assert torch.isclose(
            origin.grad[0],
            torch.tensor(0.0, dtype=torch.float64),
        )

    def test_optical_path_accumulates_across_multiple_planes(self) -> None:
        """
        通过两个平面：OP 累加 n × (d1 + d2)，方向/介质/功率不变
        """

        first_distance = 1.0e-6
        second_distance = 2.5e-6
        index = 1.3
        bundle = _bundle_at_origin(
            direction=_unit_z_direction(),
            medium=ConstantMedium(index=index),
        )
        first_plane = Plane(origin=(0.0, 0.0, first_distance))
        second_plane = Plane(
            origin=(0.0, 0.0, first_distance + second_distance),
        )
        after_first = trace_to(bundle, surface=first_plane)
        after_second = trace_to(after_first, surface=second_plane)
        total_optical_path = index * (first_distance + second_distance)
        expected = torch.full(
            (1, bundle.ray_count),
            total_optical_path,
            dtype=torch.float64,
        )
        assert torch.allclose(
            after_second.optical_path,
            expected,
            atol=1.0e-18,
        )
        # trace_to 不切换介质：per-ray 折射率、方向与功率均不变
        assert torch.equal(after_second.refractive_index, bundle.refractive_index)
        assert torch.equal(after_second.direction, bundle.direction)
        assert torch.equal(after_second.power, bundle.power)


class TestTraceToPlaneFunctionComponentDuality:
    """
    trace_to 与 TraceTo 行为完全一致；Source→TraceTo 链路产出 RayBundle
    """

    def test_function_and_component_agree(self) -> None:
        """
        同一入射 bundle、同一 Plane：trace_to 与 TraceTo 输出逐元素一致
        """

        axial_distance = 1.7e-6
        radius = 3.0e-6
        bundle = _bundle_at_origin(direction=_unit_z_direction())
        plane = Plane(
            origin=(0.0, 0.0, axial_distance),
            clear_aperture_radius=radius,
        )
        component = TraceTo(surface=plane)
        function_output = trace_to(bundle, surface=plane)
        component_output = component(bundle)
        assert function_output.position.shape == component_output.position.shape
        assert torch.equal(function_output.position, component_output.position)
        assert torch.equal(
            function_output.optical_path,
            component_output.optical_path,
        )
        assert torch.equal(function_output.status, component_output.status)

    def test_trace_to_consumes_authored_ray_bundle(self) -> None:
        """
        准直光源产出的光线束可直接进入 ``TraceTo`` 追迹动作
        """

        source = CollimatedRaySource(
            spectrum=_monochromatic(),

            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        grid = type(source).__module__  # 占位以保证 import 路径可见
        del grid
        from chromatix_next.optics import SpatialGrid

        launch_grid = SpatialGrid.centered(
            sample_counts=(3, 3),
            sample_spacing=(0.4e-6, 0.4e-6),
        )
        bundle = source(launch_grid)
        plane = Plane(origin=(0.0, 0.0, 5.0e-6))
        advanced = trace_to(bundle, surface=plane)
        assert advanced.position.shape == bundle.position.shape
        assert torch.all(
            torch.isclose(
                advanced.position[..., 2],
                torch.full_like(
                    advanced.position[..., 2],
                    5.0e-6,
                ),
            )
        )


class TestTraceToPlaneStatusPropagation:
    """
    inactive ray 不再参与 encounter；状态三态有限可诊断
    """

    def test_inactive_ray_retains_last_state(self) -> None:
        """
        已 vignetted 的 ray 再次 trace_to 不前进、不改状态
        """

        positions = torch.zeros((1, 2, 3), dtype=torch.float64)
        positions[0, 1, 0] = 5.0e-6  # 第二 ray 已偏离（模拟 last state）
        direction = _unit_z_direction().view(1, 1, 3).expand(1, 2, 3)
        status = torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8)
        status[0, 1] = RAY_STATUS_VIGNETTED  # 第二 ray 已 inactive
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
        plane = Plane(origin=(0.0, 0.0, 1.0e-6))
        advanced = trace_to(bundle, surface=plane)
        # inactive ray：保留原 status、位置、光程
        assert advanced.status[0, 1] == RAY_STATUS_VIGNETTED
        assert torch.equal(advanced.position[0, 1], positions[0, 1])
        assert torch.isclose(
            advanced.optical_path[0, 1],
            torch.tensor(0.7, dtype=torch.float64),
        )
        # active ray：正常前进
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert torch.isclose(
            advanced.position[0, 0, 2],
            torch.tensor(1.0e-6, dtype=torch.float64),
        )

    def test_three_terminal_states_distinguishable(self) -> None:
        """
        active/missed/vignetted 三态在同一 bundle 内可同时诊断
        """

        positions = torch.zeros((3, 3), dtype=torch.float64).unsqueeze(0)
        positions[0, 2, 0] = 5.0e-6  # 第三 ray 远离光轴
        directions = torch.zeros((3, 3), dtype=torch.float64).unsqueeze(0)
        directions[0, 0, 2] = 1.0  # +z
        directions[0, 1, 0] = 1.0  # +x
        directions[0, 2, 2] = 1.0  # +z
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
        plane = Plane(
            origin=(0.0, 0.0, 1.0e-6),
            clear_aperture_radius=1.0e-6,
        )
        advanced = trace_to(bundle, surface=plane)
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert advanced.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert advanced.status[0, 2] == RAY_STATUS_VIGNETTED
        _assert_no_nan(advanced)


class TestTraceToPlaneGradient:
    """
    smooth 路径的 autograd 与中心差分一致；边界显式声明分段
    """

    def test_axial_spacing_finite_difference_matches_autograd(self) -> None:
        """
        可训练 origin.z：sum(position.z) 的解析导数 = ray_count；与差分一致
        """

        def _sum_position_z(spacing_value: float) -> float:
            # 在独立 Plane 实例上累加 z 位置，供中心差分比对
            origin = torch.nn.Parameter(
                torch.tensor(
                    [0.0, 0.0, spacing_value],
                    dtype=torch.float64,
                ),
            )
            bundle = _bundle_at_origin(
                direction=_unit_z_direction(),
                ray_count=3,
            )
            plane = Plane(origin=origin)
            advanced = trace_to(bundle, surface=plane)
            return float(advanced.position[..., 2].sum().detach())

        origin = torch.nn.Parameter(
            torch.tensor(
                [0.0, 0.0, 2.0e-6],
                dtype=torch.float64,
            ),
        )
        bundle = _bundle_at_origin(direction=_unit_z_direction(), ray_count=3)
        plane = TraceTo(surface=Plane(origin=origin))
        advanced = plane(bundle)
        advanced.position[..., 2].sum().backward()
        assert origin.grad is not None
        autograd = float(origin.grad[2].detach())
        step = 1.0e-9
        central = (
            _sum_position_z(2.0e-6 + step)
            - _sum_position_z(2.0e-6 - step)
        ) / (2.0 * step)
        assert math.isclose(
            autograd,
            central,
            rel_tol=1.0e-6,
            abs_tol=1.0e-6,
        )
        assert math.isclose(
            autograd,
            3.0,
            rel_tol=1.0e-9,
            abs_tol=1.0e-9,
        )

    def test_launch_state_position_x_propagates_to_intersection(self) -> None:
        """
        可训练 launch x：交点 x = launch_x + d × tan(θ)；导数 = 1
        """

        theta = math.pi / 4.0
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        bundle = _bundle_at_origin(
            direction=direction,
            ray_count=1,
            requires_grad=True,
        )
        plane = Plane(origin=(0.0, 0.0, 2.0e-6))
        advanced = trace_to(bundle, surface=plane)
        advanced.position[..., 0].sum().backward()
        assert bundle.position.grad is not None
        assert torch.allclose(
            bundle.position.grad[..., 0],
            torch.ones_like(bundle.position.grad[..., 0]),
        )

    def test_aperture_boundary_is_piecewise_non_differentiable(self) -> None:
        """
        aperture 边界切换：在边界附近扰动 status 发生分段翻转，不声称连续导数
        """

        radius = 1.0e-6
        # 两条 ray：一条刚好在 aperture 内（r=R-ε），一条刚好在外（r=R+ε）
        eps = 1.0e-9
        positions = torch.tensor(
            [
                [radius - eps, 0.0, 0.0],
                [radius + eps, 0.0, 0.0],
            ],
            dtype=torch.float64,
        ).unsqueeze(0)
        direction = _unit_z_direction().view(1, 1, 3).expand(1, 2, 3)
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
        advanced = trace_to(bundle, surface=plane)
        # 在 ε 扰动内 status 从 active 翻转到 vignetted，证明边界分段
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert advanced.status[0, 1] == RAY_STATUS_VIGNETTED


class TestTraceToPlaneDevicePlacement:
    """
    设备放置同 meta/real 模式一致
    """

    def test_real_dtype_propagated_to_position(self) -> None:
        """
        输出的位置、方向、功率固定为 float64
        """

        real_dtype = torch.float64
        bundle = _bundle_at_origin(
            direction=_unit_z_direction(real_dtype),
            real_dtype=real_dtype,
        )
        plane = Plane(origin=(0.0, 0.0, 1.0e-6))
        advanced = trace_to(bundle, surface=plane)
        assert advanced.position.dtype is real_dtype
        assert advanced.direction.dtype is real_dtype
        assert advanced.power.dtype is real_dtype
        assert advanced.optical_path.dtype is torch.float64
        assert advanced.status.dtype is torch.uint8

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
        trace = TraceTo(surface=Plane(origin=(0.0, 0.0, 3.0e-6)))
        with _meta_inference((source, trace)) as sandbox:
            bundle = sandbox.module(source)(grid)
            advanced = sandbox.module(trace)(bundle)
        assert advanced.position.is_meta
        assert advanced.position.dtype is torch.float64
        assert advanced.optical_path.dtype is torch.float64
        assert advanced.status.dtype is torch.uint8


class TestTraceToPlaneImmutability:
    """
    trace_to 不修改输入 RayBundle（不可变物理值）
    """

    def test_input_bundle_tensors_unchanged(self) -> None:
        """
        trace_to 返回新对象；输入 position/optical_path/status 不被修改
        """

        bundle = _bundle_at_origin(direction=_unit_z_direction())
        original_position = bundle.position.clone()
        original_optical_path = bundle.optical_path.clone()
        original_status = bundle.status.clone()
        plane = Plane(origin=(0.0, 0.0, 1.0e-6))
        advanced = trace_to(bundle, surface=plane)
        assert advanced is not bundle
        assert torch.equal(bundle.position, original_position)
        assert torch.equal(bundle.optical_path, original_optical_path)
        assert torch.equal(bundle.status, original_status)


class TestPlaneHardAperture:
    """
    ``clear_aperture_radius`` 作为硬拓扑输入的窄化契约
    """

    def test_python_float_aperture_is_accepted_as_buffer(self) -> None:
        """
        Python float 注册为 float64 Buffer，孔径内/外分类正确
        """

        plane = Plane(
            origin=(0.0, 0.0, 1.0e-6),
            clear_aperture_radius=1.0e-6,
        )
        assert isinstance(plane.clear_aperture_radius, torch.Tensor)
        assert not isinstance(plane.clear_aperture_radius, torch.nn.Parameter)
        positions = torch.tensor(
            [[0.5e-6, 0.0, 0.0], [2.0e-6, 0.0, 0.0]],
            dtype=torch.float64,
        ).unsqueeze(0)
        direction = _unit_z_direction().view(1, 1, 3).expand(1, 2, 3)
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
        advanced = trace_to(bundle, surface=plane)
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert advanced.status[0, 1] == RAY_STATUS_VIGNETTED
        _assert_no_nan(advanced)

    def test_fixed_float64_tensor_aperture_is_accepted(self) -> None:
        """
        固定 float64 张量（``requires_grad=False``）注册为 Buffer
        """

        aperture = torch.tensor(1.5e-6, dtype=torch.float64)
        plane = Plane(clear_aperture_radius=aperture)
        assert isinstance(plane.clear_aperture_radius, torch.Tensor)
        assert not isinstance(plane.clear_aperture_radius, torch.nn.Parameter)
        assert torch.isclose(
            plane.clear_aperture_radius,
            torch.tensor(1.5e-6, dtype=torch.float64),
        )

    def test_parameter_aperture_rejected_at_construction(self) -> None:
        """
        ``Parameter`` 被拒（硬拓扑输入不支持可训练）
        """

        with pytest.raises(OpticalTypeError) as rejected:
            Plane(
                clear_aperture_radius=torch.nn.Parameter(
                    torch.tensor(1.0e-6, dtype=torch.float64),
                ),
            )
        assert (
            rejected.value.identity == "plane_clear_aperture_radius_invalid"
        )

    def test_requires_grad_tensor_aperture_rejected_at_construction(self) -> None:
        """
        ``requires_grad=True`` 的张量被拒
        """

        with pytest.raises(OpticalTypeError) as rejected:
            Plane(
                clear_aperture_radius=torch.tensor(
                    1.0e-6,
                    dtype=torch.float64,
                    requires_grad=True,
                ),
            )
        assert (
            rejected.value.identity == "plane_clear_aperture_radius_invalid"
        )

    def test_float32_tensor_aperture_rejected_at_construction(self) -> None:
        """
        非 float64 张量被拒（固定双精度硬拓扑输入）
        """

        with pytest.raises(OpticalTypeError) as rejected:
            Plane(
                clear_aperture_radius=torch.tensor(1.0e-6, dtype=torch.float32),
            )
        assert (
            rejected.value.identity == "plane_clear_aperture_radius_invalid"
        )

    def test_invalid_aperture_rejected_at_consume_seam(self) -> None:
        """
        变异 Buffer 为非法值后消费边界复校拒绝
        """

        plane = Plane(clear_aperture_radius=1.0e-6)
        with pytest.raises(OpticalValueError) as rejected:
            plane.clear_aperture_radius.zero_()
            plane._validate_physical_state()
        assert (
            rejected.value.identity == "plane_clear_aperture_radius_invalid"
        )


class TestTraceToConicEvenAsphere:
    """
    trace_to/TraceTo 在 ConicEvenAsphere 上的证据：球面极限对齐独立 Sphere 参考、
    光程按 n × distance 在 float64 累加、function/component duality、四态可诊断、
    device placement、可训练曲率梯度、meta/real schema 一致
    """

    def test_exact_forward_tangent_remains_a_surface_hit(self) -> None:
        origin_z = float(1.0 - 1.0e-3)
        direction = _unit_z_direction().view(1, 1, 3)
        bundle = RayBundle(
            position=torch.tensor(
                [[[1.0, 0.0, origin_z]]],
                dtype=torch.float64,
            ),
            direction=direction,
            polarization_vector=_transverse_polarization_for_direction(
                direction,
            ),
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.ones((1, 1), dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full(
                (1, 1),
                RAY_STATUS_ACTIVE,
                dtype=torch.uint8,
            ),
            spectrum=_monochromatic(),
        )

        exact_origin_z = Fraction.from_float(origin_z)
        coefficient_a = Fraction(1)
        coefficient_b = 2 * exact_origin_z - 2
        coefficient_c = (1 - exact_origin_z) ** 2
        exact_discriminant = (
            coefficient_b * coefficient_b
            - 4 * coefficient_a * coefficient_c
        )
        expected_distance = Fraction(1) - exact_origin_z

        advanced = trace_to(
            bundle,
            surface=ConicEvenAsphere(
                curvature=1.0,
                conic_constant=0.0,
            ),
        )

        assert exact_discriminant == 0
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert advanced.position[0, 0, 2] == torch.tensor(
            1.0,
            dtype=torch.float64,
        )
        assert advanced.optical_path[0, 0] == torch.tensor(
            float(expected_distance),
            dtype=torch.float64,
        )

    @pytest.mark.cuda
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
    def test_exact_forward_tangent_matches_on_cuda(self) -> None:
        """
        原始操作数精确双根在 CUDA 上保持同一命中拓扑与有限状态
        """

        device = torch.device("cuda:0")
        origin_z = float(1.0 - 1.0e-3)
        direction = _unit_z_direction().to(device).view(1, 1, 3)
        bundle = RayBundle(
            position=torch.tensor(
                [[[1.0, 0.0, origin_z]]],
                dtype=torch.float64,
                device=device,
            ),
            direction=direction,
            polarization_vector=_transverse_polarization_for_direction(
                direction,
            ),
            power=torch.ones((1, 1), dtype=torch.float64, device=device),
            refractive_index=torch.ones(
                (1, 1),
                dtype=torch.float64,
                device=device,
            ),
            optical_path=torch.zeros(
                (1, 1),
                dtype=torch.float64,
                device=device,
            ),
            status=torch.full(
                (1, 1),
                RAY_STATUS_ACTIVE,
                dtype=torch.uint8,
                device=device,
            ),
            spectrum=_monochromatic(),
        )

        advanced = trace_to(
            bundle,
            surface=ConicEvenAsphere(
                curvature=1.0,
                conic_constant=0.0,
            ).to(device),
        )

        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert torch.isfinite(advanced.position).all()
        assert advanced.position[0, 0, 2] == torch.tensor(
            1.0,
            dtype=torch.float64,
            device=device,
        )

    def test_polynomial_asphere_hit_preserves_trainable_gradients(self) -> None:
        direction_value = torch.tensor(
            [0.1, 0.0, math.sqrt(0.99)],
            dtype=torch.float64,
        )
        direction = direction_value.view(1, 1, 3)
        vertex = torch.nn.Parameter(
            torch.zeros(3, dtype=torch.float64),
        )
        curvature = torch.nn.Parameter(
            torch.tensor(0.5, dtype=torch.float64),
        )
        even_coefficients = torch.nn.Parameter(
            torch.tensor([0.01, -0.001], dtype=torch.float64),
        )
        bundle = RayBundle(
            position=torch.tensor(
                [[[0.3, 0.0, -2.0]]],
                dtype=torch.float64,
            ),
            direction=direction,
            polarization_vector=_transverse_polarization_for_direction(
                direction,
            ),
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.ones((1, 1), dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full(
                (1, 1),
                RAY_STATUS_ACTIVE,
                dtype=torch.uint8,
            ),
            spectrum=_monochromatic(),
        )

        advanced = trace_to(
            bundle,
            surface=ConicEvenAsphere(
                vertex=vertex,
                curvature=curvature,
                conic_constant=-0.3,
                even_coefficients=even_coefficients,
                clear_aperture_radius=1.0,
            ),
        )
        advanced.position.sum().backward()

        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert vertex.grad is not None
        assert torch.count_nonzero(vertex.grad) > 0
        assert curvature.grad is not None
        assert curvature.grad != 0.0
        assert even_coefficients.grad is not None
        assert torch.count_nonzero(even_coefficients.grad) > 0

    def test_spherical_limit_matches_sphere_anchor(self) -> None:
        """
        k=0/α=0 退化球面：trace_to 命中点 z 与 Sphere 同 R 解析锚点一致
        """

        radius = 5.0e-6
        conic = ConicEvenAsphere(
            curvature=1.0 / radius,
            conic_constant=0.0,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = RayBundle(
            position=positions,
            direction=_unit_z_direction().view(1, 1, 3),
            polarization_vector=_transverse_polarization_for_direction(
                _unit_z_direction().view(1, 1, 3),
            ),
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.ones((1, 1), dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        advanced = trace_to(bundle, surface=conic)
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert torch.isclose(
            advanced.position[0, 0, 2],
            torch.tensor(0.0, dtype=torch.float64),
            atol=1.0e-12,
        )
        _assert_no_nan(advanced)

    def test_optical_path_accumulates_incident_index_times_distance(self) -> None:
        """
        OP += n_incident × distance（设备本地 float64）；圆锥迭代距离仍走光程累加
        """

        radius = 5.0e-6
        axial_distance = 3.0e-6
        conic = ConicEvenAsphere(
            curvature=1.0 / radius,
            conic_constant=-1.0,
        )
        # ray 起点在顶点下方 3e-6：沿 +z 走 axial_distance 后命中顶点（sag(0)=0）
        positions = torch.tensor(
            [[[0.0, 0.0, -axial_distance]]],
            dtype=torch.float64,
        )
        bundle = RayBundle(
            position=positions,
            direction=_unit_z_direction().view(1, 1, 3),
            polarization_vector=_transverse_polarization_for_direction(
                _unit_z_direction().view(1, 1, 3),
            ),
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.full((1, 1), 1.3, dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        advanced = trace_to(bundle, surface=conic)
        assert advanced.optical_path.dtype is torch.float64
        expected = torch.tensor(
            1.3 * axial_distance,
            dtype=torch.float64,
        )
        assert torch.allclose(
            advanced.optical_path,
            expected.view(1, 1),
            atol=1.0e-15,
        )

    def test_function_and_component_agree_on_conic(self) -> None:
        """
        同入射 bundle、同 ConicEvenAsphere：trace_to 函数与 TraceTo 组件完全一致
        """

        radius = 5.0e-6
        conic = ConicEvenAsphere(
            curvature=1.0 / radius,
            conic_constant=0.5,
            even_coefficients=(1.0e3,),
            clear_aperture_radius=4.0e-6,
        )
        positions = torch.tensor(
            [[0.4e-6, 0.1e-6, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle = RayBundle(
            position=positions,
            direction=_unit_z_direction().view(1, 1, 3),
            polarization_vector=_transverse_polarization_for_direction(
                _unit_z_direction().view(1, 1, 3),
            ),
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.ones((1, 1), dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        function_output = trace_to(bundle, surface=conic)
        component_output = TraceTo(surface=conic)(bundle)
        assert torch.equal(function_output.position, component_output.position)
        assert torch.equal(
            function_output.optical_path,
            component_output.optical_path,
        )
        assert torch.equal(function_output.status, component_output.status)

    def test_three_terminal_states_distinguishable_on_conic(self) -> None:
        """
        active/missed/vignetted 三态在同一 ConicEvenAsphere bundle 内可同时诊断
        """

        radius = 5.0e-6
        aperture = 2.0e-6
        positions = torch.tensor(
            [
                [0.0, 0.0, -3.0e-6],
                [0.0, 0.0, -1.0e-6],
                [3.0e-6, 0.0, -3.0e-6],
            ],
            dtype=torch.float64,
        ).unsqueeze(0)
        directions = torch.zeros((1, 3, 3), dtype=torch.float64)
        directions[0, 0, 2] = 1.0
        directions[0, 1, 0] = 1.0
        directions[0, 2, 2] = 1.0
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
        conic = ConicEvenAsphere(
            curvature=1.0 / radius,
            conic_constant=0.0,
            clear_aperture_radius=aperture,
        )
        advanced = trace_to(bundle, surface=conic)
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert advanced.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert advanced.status[0, 2] == RAY_STATUS_VIGNETTED
        _assert_no_nan(advanced)

    def test_real_sag_root_switch_is_piecewise_non_differentiable(self) -> None:
        """
        ConicEvenAsphere 实数 sag 域根切换：横向偏移跨过 R 时 status 从 active
        翻转为 surface missed，不声称连续导数（与孔径/TIR 边界同型的分段边界）
        """

        radius = 5.0e-6
        eps = 0.05 * radius
        positions = torch.tensor(
            [
                [radius - eps, 0.0, -3.0e-6],
                [radius + eps, 0.0, -3.0e-6],
            ],
            dtype=torch.float64,
        ).unsqueeze(0)
        direction = _unit_z_direction().view(1, 1, 3).expand(1, 2, 3)
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
            curvature=1.0 / radius,
            conic_constant=0.0,
        )
        advanced = trace_to(bundle, surface=conic)
        # eps 扰动内 status 从 active 翻转到 surface missed，证明根切换边界分段
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert advanced.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        _assert_no_nan(advanced)

    def test_curvature_gradient_matches_central_difference(self) -> None:
        """
        可训练曲率：交点 z 的 autograd 与中心差分一致（远离根切换与孔径边界）
        """

        theta = math.radians(10.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)

        def intersection_z(curvature_value: float) -> float:
            """
            给定曲率返回追迹后交点 z 标量值的中心差分参考
            """
            curvature_param = torch.nn.Parameter(
                torch.tensor(curvature_value, dtype=torch.float64),
            )
            conic = ConicEvenAsphere(curvature=curvature_param)
            bundle = RayBundle(
                position=start.view(1, 1, 3),
                direction=direction.view(1, 1, 3),
                polarization_vector=_transverse_polarization_for_direction(
                    direction.view(1, 1, 3),
                ),
                power=torch.ones((1, 1), dtype=torch.float64),
                refractive_index=torch.ones((1, 1), dtype=torch.float64),
                optical_path=torch.zeros((1, 1), dtype=torch.float64),
                status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=_monochromatic(),
            )
            advanced = trace_to(bundle, surface=conic)
            return float(advanced.position[0, 0, 2].detach())

        curvature_param = torch.nn.Parameter(
            torch.tensor(1.0 / 5.0e-6, dtype=torch.float64),
        )
        conic = ConicEvenAsphere(curvature=curvature_param)
        bundle = RayBundle(
            position=start.view(1, 1, 3),
            direction=direction.view(1, 1, 3),
            polarization_vector=_transverse_polarization_for_direction(
                direction.view(1, 1, 3),
            ),
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.ones((1, 1), dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        advanced = trace_to(bundle, surface=conic)
        advanced.position[0, 0, 2].backward()
        assert curvature_param.grad is not None
        autograd = float(curvature_param.grad.detach())
        step = 1.0
        base = 1.0 / 5.0e-6
        central = (intersection_z(base + step) - intersection_z(base - step)) / (
            2.0 * step
        )
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e2)

    def test_conic_constant_gradient_matches_central_difference(self) -> None:
        """
        可训练圆锥常数：交点 z 的 autograd 与中心差分一致（远离根切换与孔径边界）
        """

        theta = math.radians(10.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        base_conic_constant = -0.3
        step = 0.1

        def intersection_z(conic_constant_value: float) -> float:
            """
            给定圆锥常数返回追迹后交点 z 标量值的中心差分参考
            """
            conic = ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=torch.nn.Parameter(
                    torch.tensor(conic_constant_value, dtype=torch.float64),
                ),
            )
            bundle = RayBundle(
                position=start.view(1, 1, 3),
                direction=direction.view(1, 1, 3),
                polarization_vector=_transverse_polarization_for_direction(
                    direction.view(1, 1, 3),
                ),
                power=torch.ones((1, 1), dtype=torch.float64),
                refractive_index=torch.ones((1, 1), dtype=torch.float64),
                optical_path=torch.zeros((1, 1), dtype=torch.float64),
                status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=_monochromatic(),
            )
            advanced = trace_to(bundle, surface=conic)
            return float(advanced.position[0, 0, 2].detach())

        conic_constant_param = torch.nn.Parameter(
            torch.tensor(base_conic_constant, dtype=torch.float64),
        )
        conic = ConicEvenAsphere(
            curvature=1.0 / 5.0e-6,
            conic_constant=conic_constant_param,
        )
        bundle = RayBundle(
            position=start.view(1, 1, 3),
            direction=direction.view(1, 1, 3),
            polarization_vector=_transverse_polarization_for_direction(
                direction.view(1, 1, 3),
            ),
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.ones((1, 1), dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        advanced = trace_to(bundle, surface=conic)
        advanced.position[0, 0, 2].backward()
        assert conic_constant_param.grad is not None
        autograd = float(conic_constant_param.grad.detach())
        central = (
            intersection_z(base_conic_constant + step)
            - intersection_z(base_conic_constant - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e-10)

    def test_even_coefficients_gradient_matches_central_difference(self) -> None:
        """
        可训练偶次系数：交点 z 的 autograd 与中心差分一致（远离根切换与孔径边界）
        """

        theta = math.radians(10.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor([0.0, 0.0, -3.0e-6], dtype=torch.float64)
        base_coefficient = 2.0e3
        step = 1.0e3

        def intersection_z(coefficient_value: float) -> float:
            """
            给定偶次系数返回追迹后交点 z 标量值的中心差分参考
            """
            conic = ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                even_coefficients=torch.nn.Parameter(
                    torch.tensor([coefficient_value], dtype=torch.float64),
                ),

            clear_aperture_radius=5.0e-6,)
            bundle = RayBundle(
                position=start.view(1, 1, 3),
                direction=direction.view(1, 1, 3),
                polarization_vector=_transverse_polarization_for_direction(
                    direction.view(1, 1, 3),
                ),
                power=torch.ones((1, 1), dtype=torch.float64),
                refractive_index=torch.ones((1, 1), dtype=torch.float64),
                optical_path=torch.zeros((1, 1), dtype=torch.float64),
                status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=_monochromatic(),
            )
            advanced = trace_to(bundle, surface=conic)
            return float(advanced.position[0, 0, 2].detach())

        coefficient_param = torch.nn.Parameter(
            torch.tensor([base_coefficient], dtype=torch.float64),
        )
        conic = ConicEvenAsphere(
            curvature=1.0 / 5.0e-6,
            even_coefficients=coefficient_param,

        clear_aperture_radius=5.0e-6,)
        bundle = RayBundle(
            position=start.view(1, 1, 3),
            direction=direction.view(1, 1, 3),
            polarization_vector=_transverse_polarization_for_direction(
                direction.view(1, 1, 3),
            ),
            power=torch.ones((1, 1), dtype=torch.float64),
            refractive_index=torch.ones((1, 1), dtype=torch.float64),
            optical_path=torch.zeros((1, 1), dtype=torch.float64),
            status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
            spectrum=_monochromatic(),
        )
        advanced = trace_to(bundle, surface=conic)
        advanced.position[0, 0, 2].backward()
        assert coefficient_param.grad is not None
        autograd = float(coefficient_param.grad[0].detach())
        central = (
            intersection_z(base_coefficient + step)
            - intersection_z(base_coefficient - step)
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-4, abs_tol=1.0e-10)

    def test_mixed_hit_miss_curvature_gradient_finite(self) -> None:
        """
        混合 hit/miss 圆锥束：miss 光线径向漂移离开实数 sag 域；前向有限、状态分段
        （active/surface_missed）；可训练曲率梯度有限且与独立中心差分参考一致，
        detect_anomaly 不再触发——共享 ``curvature`` Parameter 不被 miss 分支的
        0·NaN 污染
        """

        base_curvature = 2.0e5
        positions = torch.tensor(
            [
                [0.5e-6, 0.0, -3.0e-6],
                [0.0, 0.0, -1.0e-6],
            ],
            dtype=torch.float64,
        ).unsqueeze(0)
        directions = torch.zeros((1, 2, 3), dtype=torch.float64)
        directions[0, 0, 2] = 1.0  # ray0 +z（命中）
        directions[0, 1, 0] = 1.0  # ray1 +x（径向漂移，域外未命中）

        def _build(curvature_value: float) -> tuple[
            ConicEvenAsphere,
            RayBundle,
        ]:
            # 每次评估独立构造 surface 与 bundle，避免污染共享 Parameter
            curvature = torch.nn.Parameter(
                torch.tensor(curvature_value, dtype=torch.float64),
            )
            surface = ConicEvenAsphere(curvature=curvature, conic_constant=0.0)
            bundle = RayBundle(
                position=positions.clone(),
                direction=directions.clone(),
                polarization_vector=_transverse_polarization_for_direction(
                    directions.clone(),
                ),
                power=torch.ones((1, 2), dtype=torch.float64),
                refractive_index=torch.ones((1, 2), dtype=torch.float64),
                optical_path=torch.zeros((1, 2), dtype=torch.float64),
                status=torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8),
                spectrum=_monochromatic(),
            )
            return surface, bundle

        # 前向有限、状态分段：ray0 active、ray1 surface_missed，位置处处有限
        surface, bundle = _build(base_curvature)
        advanced = trace_to(bundle, surface=surface)
        assert advanced.status[0, 0] == RAY_STATUS_ACTIVE
        assert advanced.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert torch.isfinite(advanced.position).all()
        # 命中光线 z 与独立解析 sag（c·u/(1+√(1−c²·u))，u=r²，k=0）一致，不镜像私有核
        radial_squared = 0.25e-12
        one_minus = 1.0 - base_curvature * base_curvature * radial_squared
        analytic_sag = base_curvature * radial_squared / (
            1.0 + math.sqrt(one_minus)
        )
        assert math.isclose(
            float(advanced.position[0, 0, 2].detach()),
            analytic_sag,
            rel_tol=1.0e-12,
        )
        # miss 光线保留入射位置（z=-1e-6），不被推进
        assert math.isclose(
            float(advanced.position[0, 1, 2].detach()),
            -1.0e-6,
            rel_tol=1.0e-12,
        )

        # 反向：curvature.grad 必须有限（修复前为 NaN）。detect_anomaly 须保持干净
        with torch.autograd.set_detect_anomaly(True):
            advanced.position.sum().backward()
        assert surface.curvature.grad is not None  # type: ignore[union-attr]
        autograd = float(surface.curvature.grad.detach())  # type: ignore[union-attr]
        assert math.isfinite(autograd)
        assert autograd != 0.0

        # 独立中心差分参考：对公共 trace_to 前向输出做数值微分，不复用私有导数
        step = 1.0  # curvature=2e5；更小步长落入 float64 roundoff
        forward_plus = trace_to(bundle, surface=_build(base_curvature + step)[0])
        forward_minus = trace_to(
            bundle,
            surface=_build(base_curvature - step)[0],
        )
        central = (
            float(forward_plus.position.sum().detach())
            - float(forward_minus.position.sum().detach())
        ) / (2.0 * step)
        assert math.isclose(autograd, central, rel_tol=1.0e-6, abs_tol=1.0e-18)

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
        trace = TraceTo(
            surface=ConicEvenAsphere(curvature=1.0 / 5.0e-6, conic_constant=-0.5),
        )
        with _meta_inference((source, trace)) as sandbox:
            bundle = sandbox.module(source)(grid)
            advanced = sandbox.module(trace)(bundle)
        assert advanced.position.is_meta
        assert advanced.position.dtype is torch.float64
        assert advanced.optical_path.dtype is torch.float64
        assert advanced.status.dtype is torch.uint8


class TestPlaneStateValidatedAtConsumption:
    """
    平面消费期状态验证：变异 trainable origin/aperture 后，
    stateless 入口数值工作前抛稳定身份；direct 与 replay 路径一致
    """

    def test_mutated_origin_non_finite_rejected(self) -> None:
        """
        构造后把可训练平面原点改成 NaN ⇒ consumption 期抛 ``plane_origin_invalid``
        （direct 与 replay 一致；构造期验证不覆盖 optimizer 变异后）
        """

        origin_param = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 5.0e-6), dtype=torch.float64),
        )
        plane = Plane(origin=origin_param)
        component = TraceTo(surface=plane)
        bundle = _bundle_at_origin(direction=_unit_z_direction())
        with torch.no_grad():
            origin_param[2].fill_(float("nan"))
        with pytest.raises(OpticalValueError) as direct_call:
            trace_to(bundle, surface=plane)
        assert direct_call.value.identity == "plane_origin_invalid"
        with pytest.raises(OpticalValueError) as replay_path:
            component(bundle)
        assert replay_path.value.identity == "plane_origin_invalid"

    def test_mutated_plane_aperture_non_positive_rejected(self) -> None:
        """
        构造后把硬孔径 Buffer 改成负数 ⇒ consumption 期抛孔径身份（双精度）
        """

        plane = Plane(clear_aperture_radius=1.0e-5)
        component = TraceTo(surface=plane)
        bundle = _bundle_at_origin(direction=_unit_z_direction())
        with torch.no_grad():
            plane.clear_aperture_radius.fill_(-1.0)
        with pytest.raises(OpticalValueError) as rejected:
            component(bundle)
        assert (
            rejected.value.identity == "plane_clear_aperture_radius_invalid"
        )


@pytest.mark.cuda
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
def test_trace_to_public_action_matches_cpu_on_cuda() -> None:
    """
    TraceTo 公共动作在 CUDA 上保持全部 Ray Bundle 量与 CPU 一致
    """

    direction = _unit_z_direction()
    cpu_bundle = _bundle_at_origin(direction=direction)
    cuda_bundle = _bundle_at_origin(direction=direction, device="cuda:0")
    cpu_output = trace_to(
        cpu_bundle,
        surface=Plane(origin=(0.0, 0.0, 1.0e-3)),
    )
    cuda_output = trace_to(
        cuda_bundle,
        surface=Plane(origin=(0.0, 0.0, 1.0e-3)).cuda(),
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

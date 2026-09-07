
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next._numerics.surface_geometry.conic import conic_encounter
from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter
from chromatix_next._numerics.surface_geometry.sphere import sphere_encounter
from chromatix_next.errors import OpticalValueError


def _scalar_sag(
    r_squared: float,
    curvature: float,
    conic_constant: float,
    even_coefficients: tuple[float, ...],
) -> float:
    # 独立标量 sag 实现，与生产核分开写：圆锥项 + 偶次多项式 Σ α_i · r^(2i)（i 从 1）
    one_minus = 1.0 - (1.0 + conic_constant) * curvature * curvature * r_squared
    if one_minus < 0.0:
        return float("nan")
    sqrt_term = math.sqrt(one_minus)
    base = curvature * r_squared / (1.0 + sqrt_term)
    poly = 0.0
    for index, coefficient in enumerate(even_coefficients):
        power = index + 1
        poly += coefficient * (r_squared**power)
    return base + poly


def _scalar_residual(
    t: float,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    curvature: float,
    conic_constant: float,
    even_coefficients: tuple[float, ...],
) -> float:
    # F(t) = oz + t·dz − sag((ox+t·dx)² + (oy+t·dy)²)，独立标量实现
    ox, oy, oz = origin
    dx, dy, dz = direction
    x = ox + t * dx
    y = oy + t * dy
    z = oz + t * dz
    r_squared = x * x + y * y
    return z - _scalar_sag(r_squared, curvature, conic_constant, even_coefficients)


def _independent_bisect_root(
    *,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    curvature: float,
    conic_constant: float,
    even_coefficients: tuple[float, ...],
    t_low: float,
    t_high: float,
    iterations: int = 200,
) -> float:
    # 独立高精度二分参考：不复用生产牛顿核；假设 [t_low, t_high] 已包围根（F 异号）
    residual_low = _scalar_residual(
        t_low,
        origin,
        direction,
        curvature,
        conic_constant,
        even_coefficients,
    )
    residual_high = _scalar_residual(
        t_high,
        origin,
        direction,
        curvature,
        conic_constant,
        even_coefficients,
    )
    assert residual_low * residual_high <= 0.0, (
        "二分包络失效：两端点 F 同号，请手工核对区间"
    )
    t_mid = 0.5 * (t_low + t_high)
    for _ in range(iterations):
        residual_mid = _scalar_residual(
            t_mid,
            origin,
            direction,
            curvature,
            conic_constant,
            even_coefficients,
        )
        if residual_low * residual_mid <= 0.0:
            t_high = t_mid
            residual_high = residual_mid
        else:
            t_low = t_mid
            residual_low = residual_mid
        t_mid = 0.5 * (t_low + t_high)
    return t_mid


def _default_pose() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    # 默认全局姿态：vertex 在原点、tangent_x = ê_x、tangent_y = ê_y ⇒ normal = +ê_z
    tangent_x = torch.tensor([1.0, 0.0, 0.0], dtype=torch.float64)
    tangent_y = torch.tensor([0.0, 1.0, 0.0], dtype=torch.float64)
    vertex = torch.zeros(3, dtype=torch.float64)
    return vertex, tangent_x, tangent_y


def _unit_z() -> torch.Tensor:
    # 沿 +z 的单位方向
    direction = torch.zeros(3, dtype=torch.float64)
    direction[2] = 1.0
    return direction


def _run_conic_encounter(
    *,
    ray_origin: torch.Tensor,
    ray_direction: torch.Tensor,
    curvature: float,
    conic_constant: float,
    even_coefficients: tuple[float, ...] = (),
    clear_aperture_radius: float | None = None,
) -> SurfaceEncounter:
    # 把生产 conic_encounter 包装为单 ray 调用，返回相遇结果结构
    vertex, tangent_x, tangent_y = _default_pose()
    aperture_tensor: torch.Tensor | None
    if clear_aperture_radius is None:
        aperture_tensor = None
    else:
        aperture_tensor = torch.tensor(
            clear_aperture_radius,
            dtype=torch.float64,
        )
    even_tensor = torch.tensor(even_coefficients, dtype=torch.float64)
    return conic_encounter(
        ray_origin=ray_origin,
        ray_direction=ray_direction,
        conic_vertex=vertex,
        conic_tangent_x=tangent_x,
        conic_tangent_y=tangent_y,
        curvature=torch.tensor(curvature, dtype=torch.float64),
        conic_constant=torch.tensor(conic_constant, dtype=torch.float64),
        even_coefficients=even_tensor,
        clear_aperture_radius=aperture_tensor,
    )


def test_plane_conic_rejects_nonfinite_forward_distance() -> None:
    """
    平面分支不把有限方向导致的溢出距离误判为正向相遇
    """

    smallest_positive = torch.nextafter(
        torch.tensor(0.0, dtype=torch.float64),
        torch.tensor(1.0, dtype=torch.float64),
    )
    encounter = _run_conic_encounter(
        ray_origin=torch.tensor(
            [0.0, 0.0, -1.0],
            dtype=torch.float64,
        ),
        ray_direction=torch.stack(
            (
                torch.tensor(1.0, dtype=torch.float64),
                torch.tensor(0.0, dtype=torch.float64),
                smallest_positive,
            )
        ),
        curvature=0.0,
        conic_constant=0.0,
    )

    assert not bool(encounter.is_encountered)
    torch.testing.assert_close(
        encounter.distance,
        torch.zeros_like(encounter.distance),
        rtol=0.0,
        atol=0.0,
    )
    assert bool(torch.isfinite(encounter.intersection).all())


def _tensor_from_hexadecimal(
    values: tuple[str, ...],
    *,
    shape: tuple[int, ...],
) -> torch.Tensor:
    return torch.tensor(
        tuple(float.fromhex(value) for value in values),
        dtype=torch.float64,
    ).reshape(shape)


@pytest.mark.parametrize(
    (
        "origin",
        "curvature_value",
        "conic_constant_value",
        "even_coefficient_values",
        "aperture_value",
        "expected_distance",
        "expected_intersection",
        "expected_normal",
        "expected_origin_gradient",
        "expected_curvature_gradient",
        "expected_conic_constant_gradient",
        "expected_coefficient_gradient",
    ),
    (
        (
            (0.4e-6, 0.0, -3.0e-6),
            1.0 / 8.0e-6,
            0.5,
            (),
            None,
            ("0x1.929b2d324d99cp-19",),
            (
                "0x1.12c9885754886p-20",
                "0x0.0p+0",
                "-0x1.1b09b77cc8ec0p-24",
            ),
            (
                "-0x1.072308059c588p-3",
                "-0x0.0p+0",
                "-0x1.fbc19b6c866c2p-1",
            ),
            (
                "-0x1.a2c2299707f58p+16",
                "-0x1.ea49d350a171dp+16",
                "0x1.640600bb9b69cp+14",
            ),
            "-0x1.ddc7213c2e07ap-21",
            "-0x1.e0b47e303a1f6p-11",
            (),
        ),
        (
            (0.5e-6, 0.0, -3.0e-6),
            1.0 / 8.0e-6,
            0.5,
            (5.0e3, -2.0e8),
            5.0e-6,
            ("0x1.8ff59362e9db4p-19",),
            (
                "0x1.2c87b7ce49e03p-20",
                "0x0.0p+0",
                "-0x1.6de31ccc71b60p-24",
            ),
            (
                "-0x1.3638565b3b3e8p-3",
                "-0x0.0p+0",
                "-0x1.fa17943b89175p-1",
            ),
            (
                "-0x1.b3559607e4b2bp+16",
                "-0x1.08408fa0e3836p+17",
                "0x1.721ddf7baa3dbp+14",
            ),
            "-0x1.f9dec47d6212bp-21",
            "-0x1.30c39f950c125p-10",
            (
                "-0x1.e3911ae81095ap-20",
                "-0x1.4ff599af3d731p-58",
            ),
        ),
    ),
)
def test_conic_value_and_gradient_match_frozen_binary64_witness(
    origin: tuple[float, float, float],
    curvature_value: float,
    conic_constant_value: float,
    even_coefficient_values: tuple[float, ...],
    aperture_value: float | None,
    expected_distance: tuple[str, ...],
    expected_intersection: tuple[str, ...],
    expected_normal: tuple[str, ...],
    expected_origin_gradient: tuple[str, ...],
    expected_curvature_gradient: str,
    expected_conic_constant_gradient: str,
    expected_coefficient_gradient: tuple[str, ...],
) -> None:
    """
    Base 与 polynomial 代表光线的值和梯度逐 bit 保持重构前 witness
    """

    ray_origin = torch.tensor(
        [[origin]],
        dtype=torch.float64,
        requires_grad=True,
    )
    theta = math.radians(12.0)
    ray_direction = torch.tensor(
        [[(math.sin(theta), 0.0, math.cos(theta))]],
        dtype=torch.float64,
    )
    curvature = torch.tensor(
        curvature_value,
        dtype=torch.float64,
        requires_grad=True,
    )
    conic_constant = torch.tensor(
        conic_constant_value,
        dtype=torch.float64,
        requires_grad=True,
    )
    even_coefficients = torch.tensor(
        even_coefficient_values,
        dtype=torch.float64,
        requires_grad=True,
    )
    aperture = (
        None
        if aperture_value is None
        else torch.tensor(aperture_value, dtype=torch.float64)
    )
    vertex = torch.zeros(3, dtype=torch.float64)
    tangent_x = torch.tensor([0.0, 1.0, 0.0], dtype=torch.float64)
    tangent_y = torch.tensor([1.0, 0.0, 0.0], dtype=torch.float64)
    encounter = conic_encounter(
        ray_origin=ray_origin,
        ray_direction=ray_direction,
        conic_vertex=vertex,
        conic_tangent_x=tangent_x,
        conic_tangent_y=tangent_y,
        curvature=curvature,
        conic_constant=conic_constant,
        even_coefficients=even_coefficients,
        clear_aperture_radius=aperture,
    )
    assert bool(encounter.is_encountered)
    torch.testing.assert_close(
        encounter.distance,
        _tensor_from_hexadecimal(expected_distance, shape=(1, 1)),
        rtol=0.0,
        atol=0.0,
    )
    torch.testing.assert_close(
        encounter.intersection,
        _tensor_from_hexadecimal(expected_intersection, shape=(1, 1, 3)),
        rtol=0.0,
        atol=0.0,
    )
    torch.testing.assert_close(
        encounter.unit_normal,
        _tensor_from_hexadecimal(expected_normal, shape=(1, 1, 3)),
        rtol=0.0,
        atol=0.0,
    )
    witness_value = (
        encounter.distance.sum()
        + encounter.intersection.sum()
        + encounter.unit_normal.sum()
    )
    witness_value.backward()
    assert ray_origin.grad is not None
    assert curvature.grad is not None
    assert conic_constant.grad is not None
    torch.testing.assert_close(
        ray_origin.grad,
        _tensor_from_hexadecimal(
            expected_origin_gradient,
            shape=(1, 1, 3),
        ),
        rtol=0.0,
        atol=0.0,
    )
    assert float(curvature.grad) == float.fromhex(expected_curvature_gradient)
    assert float(conic_constant.grad) == float.fromhex(
        expected_conic_constant_gradient
    )
    if expected_coefficient_gradient:
        assert even_coefficients.grad is not None
        torch.testing.assert_close(
            even_coefficients.grad,
            _tensor_from_hexadecimal(
                expected_coefficient_gradient,
                shape=(len(expected_coefficient_gradient),),
            ),
            rtol=0.0,
            atol=0.0,
        )


class TestConicEncounterSphericalLimit:
    """
    k=0 且 α=0 时圆锥退化为球面：交点、法线、距离与独立 Sphere 参考一致
    """

    @pytest.mark.parametrize("radius_sign", (1.0, -1.0))
    def test_on_axis_matches_sphere_reference(self, radius_sign: float) -> None:
        """
        沿轴 ray 在球面极限下命中顶点：与 ``sphere_encounter`` 独立参考一致
        """

        radius = 5.0e-6 * radius_sign
        curvature = 1.0 / radius
        start = torch.tensor(
            [[0.0, 0.0, -3.0e-6 if radius_sign > 0 else -2.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle_origin = start
        bundle_direction = _unit_z().view(1, 1, 3)
        conic_result = _run_conic_encounter(
            ray_origin=bundle_origin,
            ray_direction=bundle_direction,
            curvature=curvature,
            conic_constant=0.0,
        )
        vertex, tangent_x, tangent_y = _default_pose()
        normal = torch.linalg.cross(tangent_x, tangent_y)
        sphere_center = vertex + torch.tensor(radius, dtype=torch.float64) * normal
        sphere_result = sphere_encounter(
            ray_origin=bundle_origin,
            ray_direction=bundle_direction,
            sphere_center=sphere_center,
            sphere_vertex=vertex,
            sphere_tangent_x=tangent_x,
            sphere_tangent_y=tangent_y,
            physical_radius=torch.tensor(abs(radius), dtype=torch.float64),
            clear_aperture_radius=None,
        )
        assert torch.allclose(
            conic_result.distance,
            sphere_result.distance,
            atol=1.0e-12,
        )
        assert torch.allclose(
            conic_result.intersection,
            sphere_result.intersection,
            atol=1.0e-12,
        )
        assert torch.allclose(
            conic_result.unit_normal,
            sphere_result.unit_normal,
            atol=1.0e-12,
        )

    def test_oblique_matches_sphere_reference(self) -> None:
        """
        斜入射 ray 在球面极限下与独立球面交集一致（凸面、远离根切换）
        """

        radius = 5.0e-6
        curvature = 1.0 / radius
        theta = math.radians(15.0)
        direction = torch.tensor(
            [math.sin(theta), 0.0, math.cos(theta)],
            dtype=torch.float64,
        )
        start = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle_origin = start
        bundle_direction = direction.view(1, 1, 3)
        conic_result = _run_conic_encounter(
            ray_origin=bundle_origin,
            ray_direction=bundle_direction,
            curvature=curvature,
            conic_constant=0.0,
        )
        vertex, tangent_x, tangent_y = _default_pose()
        normal = torch.linalg.cross(tangent_x, tangent_y)
        sphere_center = vertex + torch.tensor(radius, dtype=torch.float64) * normal
        sphere_result = sphere_encounter(
            ray_origin=bundle_origin,
            ray_direction=bundle_direction,
            sphere_center=sphere_center,
            sphere_vertex=vertex,
            sphere_tangent_x=tangent_x,
            sphere_tangent_y=tangent_y,
            physical_radius=torch.tensor(radius, dtype=torch.float64),
            clear_aperture_radius=None,
        )
        assert torch.allclose(
            conic_result.intersection,
            sphere_result.intersection,
            atol=1.0e-12,
        )
        # 球面极限下法线也应一致（同 sag 约定 ⇒ 同梯度 ⇒ 同单位法线）
        assert torch.allclose(
            conic_result.unit_normal,
            sphere_result.unit_normal,
            atol=1.0e-9,
        )


class TestConicEncounterIndependentRootReference:
    """
    非球面情形下生产迭代根与独立高精度二分参考一致
    """

    def test_paraboloid_on_axis_matches_bisect(self) -> None:
        """
        抛物面（k=−1）沿轴 ray：与独立二分根一致
        """

        radius = 5.0e-6
        curvature = 1.0 / radius
        start = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle_origin = start
        bundle_direction = _unit_z().view(1, 1, 3)
        result = _run_conic_encounter(
            ray_origin=bundle_origin,
            ray_direction=bundle_direction,
            curvature=curvature,
            conic_constant=-1.0,
        )
        expected_t = _independent_bisect_root(
            origin=(0.0, 0.0, -3.0e-6),
            direction=(0.0, 0.0, 1.0),
            curvature=curvature,
            conic_constant=-1.0,
            even_coefficients=(),
            t_low=0.0,
            t_high=10.0e-6,
        )
        assert torch.isclose(
            result.distance[0, 0],
            torch.tensor(expected_t, dtype=torch.float64),
            atol=1.0e-12,
        )

    def test_ellipsoid_with_even_terms_matches_bisect(self) -> None:
        """
        椭球（k=0.5）+ 偶次项：与独立二分根一致（斜入射）
        """

        radius = 8.0e-6
        curvature = 1.0 / radius
        even_coeffs = (5.0e3, -2.0e8)  # α_1 配 r²、α_2 配 r⁴（小幅度扰动）
        theta = math.radians(12.0)
        direction = (
            torch.tensor(
                [math.sin(theta), 0.0, math.cos(theta)],
                dtype=torch.float64,
            )
        ).view(1, 1, 3)
        start = torch.tensor(
            [[0.5e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        result = _run_conic_encounter(
            ray_origin=start,
            ray_direction=direction,
            curvature=curvature,
            conic_constant=0.5,
            even_coefficients=even_coeffs,
            clear_aperture_radius=5.0e-6,
        )
        expected_t = _independent_bisect_root(
            origin=(0.5e-6, 0.0, -3.0e-6),
            direction=(math.sin(theta), 0.0, math.cos(theta)),
            curvature=curvature,
            conic_constant=0.5,
            even_coefficients=even_coeffs,
            t_low=0.0,
            t_high=10.0e-6,
        )
        assert torch.isclose(
            result.distance[0, 0],
            torch.tensor(expected_t, dtype=torch.float64),
            atol=1.0e-12,
        )

    def test_residual_within_tolerance_at_root(self) -> None:
        """
        收敛根处 |z_local − sag(r²)| 残差小于 float64 容差（独立核校验）
        """

        radius = 5.0e-6
        curvature = 1.0 / radius
        even_coeffs = (1.0e3, -5.0e7)
        theta = math.radians(20.0)
        direction = (
            torch.tensor(
                [math.sin(theta), 0.0, math.cos(theta)],
                dtype=torch.float64,
            )
        ).view(1, 1, 3)
        start = torch.tensor(
            [[0.3e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        result = _run_conic_encounter(
            ray_origin=start,
            ray_direction=direction,
            curvature=curvature,
            conic_constant=-0.75,
            even_coefficients=even_coeffs,
            clear_aperture_radius=5.0e-6,
        )
        t_value = float(result.distance[0, 0])
        ox, oy, oz = (0.3e-6, 0.0, -3.0e-6)
        dx, dy, dz = (math.sin(theta), 0.0, math.cos(theta))
        x_root = ox + t_value * dx
        y_root = oy + t_value * dy
        z_root = oz + t_value * dz
        r_squared = x_root * x_root + y_root * y_root
        sag_value = _scalar_sag(r_squared, curvature, -0.75, even_coeffs)
        residual = abs(z_root - sag_value)
        assert residual < 1.0e-12


class TestConicEncounterPhysicalMissAndSolverFailure:
    """
    物理未命中（逐光线状态）与数值求解失败（域错误）严格区分
    """

    def test_rear_facing_ray_marked_missed(self) -> None:
        """
        偏轴 + 沿 −z 的 ray：解析候选根全在 ray 反向，故判物理未命中
        """

        radius = 5.0e-6
        curvature = 1.0 / radius
        backward = torch.tensor([[0.0, 0.0, -1.0]], dtype=torch.float64).view(1, 1, 3)
        bundle_origin = torch.tensor(
            [[[0.5e-6, 0.0, 0.0]]],
            dtype=torch.float64,
        )
        result = _run_conic_encounter(
            ray_origin=bundle_origin,
            ray_direction=backward,
            curvature=curvature,
            conic_constant=0.0,
        )
        assert bool(result.is_encountered[0, 0]) is False

    def test_parallel_ray_below_vertex_marked_missed(self) -> None:
        """
        沿 +x 的 ray 起点在 vertex 下方：径向漂移最终离开实数 sag 域 ⇒ 物理未命中
        """

        radius = 5.0e-6
        curvature = 1.0 / radius
        along_x = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float64).view(1, 1, 3)
        bundle_origin = torch.tensor(
            [[[0.0, 0.0, -1.0e-6]]],
            dtype=torch.float64,
        )
        result = _run_conic_encounter(
            ray_origin=bundle_origin,
            ray_direction=along_x,
            curvature=curvature,
            conic_constant=0.0,
        )
        assert bool(result.is_encountered[0, 0]) is False


class TestConicEncounterApertureBoundary:
    """
    圆形 aperture 在 r² = x² + y² 上闭边界分段
    """

    def test_aperture_splits_active_and_vignetted(self) -> None:
        """
        同一圆锥面、孔径半径 R_a：径向 ≤ R_a 命中内、> R_a 命中外（vignetted）
        """

        radius = 5.0e-6
        curvature = 1.0 / radius
        aperture = 2.0e-6
        positions = torch.tensor(
            [[1.0e-6, 0.0, -3.0e-6], [3.0e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        direction = _unit_z().view(1, 1, 3).expand(1, 2, 3)
        result = _run_conic_encounter(
            ray_origin=positions,
            ray_direction=direction,
            curvature=curvature,
            conic_constant=0.0,
            clear_aperture_radius=aperture,
        )
        assert bool(result.is_inside_aperture[0, 0]) is True
        assert bool(result.is_inside_aperture[0, 1]) is False


class TestConicEncounterNormals:
    """
    解析法线定向与入射侧一致（d·n ≤ 0）；轴向 ray 命中顶点时法线 = +z
    """

    def test_axial_incidence_normal_points_against_ray(self) -> None:
        """
        沿 +z ray 命中顶点：定向法线应为 −z（入射侧），使 d·n ≤ 0
        """

        radius = 5.0e-6
        curvature = 1.0 / radius
        start = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        bundle_direction = _unit_z().view(1, 1, 3)
        result = _run_conic_encounter(
            ray_origin=start,
            ray_direction=bundle_direction,
            curvature=curvature,
            conic_constant=0.0,
        )
        cos_incident = (bundle_direction * result.unit_normal).sum(dim=-1)
        assert bool((cos_incident <= 1.0e-12).all())
        # 顶点处法线幅度为单位向量
        normal_norm = result.unit_normal.norm(dim=-1)
        assert torch.isclose(
            normal_norm[0, 0],
            torch.ones_like(normal_norm[0, 0]),
            atol=1.0e-9,
        )

    def test_oblique_normal_is_unit_length(self) -> None:
        """
        斜入射非球面：法线逐条仍为单位向量
        """

        radius = 5.0e-6
        curvature = 1.0 / radius
        even_coeffs = (1.0e3, -5.0e7)
        theta = math.radians(18.0)
        direction = (
            torch.tensor(
                [math.sin(theta), 0.0, math.cos(theta)],
                dtype=torch.float64,
            )
        ).view(1, 1, 3)
        start = torch.tensor(
            [[0.4e-6, 0.0, -3.0e-6]],
            dtype=torch.float64,
        ).unsqueeze(0)
        result = _run_conic_encounter(
            ray_origin=start,
            ray_direction=direction,
            curvature=curvature,
            conic_constant=-0.5,
            even_coefficients=even_coeffs,
            clear_aperture_radius=5.0e-6,
        )
        normal_norm = result.unit_normal.norm(dim=-1)
        assert torch.isclose(
            normal_norm[0, 0],
            torch.ones_like(normal_norm[0, 0]),
            atol=1.0e-9,
        )

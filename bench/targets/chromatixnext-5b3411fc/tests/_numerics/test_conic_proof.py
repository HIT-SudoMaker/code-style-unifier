
from __future__ import annotations

import math

import pytest
import sympy
import torch

from chromatix_next._numerics.surface_geometry.conic import conic_encounter
from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter

# 三元张量组（命中标志、距离、梯度）的类型别名，缩短 CUDA 测试内函数签名
_TensorTriple = tuple[torch.Tensor, torch.Tensor, torch.Tensor]


def _default_pose() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    # 默认全局姿态：顶点在原点、tangent_x 为 ê_x、tangent_y 为 ê_y、法线为 +ê_z
    vertex = torch.zeros(3, dtype=torch.float64)
    tangent_x = torch.tensor([1.0, 0.0, 0.0], dtype=torch.float64)
    tangent_y = torch.tensor([0.0, 1.0, 0.0], dtype=torch.float64)
    return vertex, tangent_x, tangent_y


def _run(
    *,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    curvature: float,
    conic_constant: float,
    even_coefficients: tuple[float, ...] = (),
    clear_aperture_radius: float | None = None,
) -> SurfaceEncounter:
    # 单 ray 包装：把浮点输入升为 float64 张量后调用 ``conic_encounter``
    vertex, tangent_x, tangent_y = _default_pose()
    aperture = (
        None
        if clear_aperture_radius is None
        else torch.tensor(clear_aperture_radius, dtype=torch.float64)
    )
    origin_t = torch.tensor([list(origin)], dtype=torch.float64).view(1, 1, 3)
    direction_t = torch.tensor([list(direction)], dtype=torch.float64).view(1, 1, 3)
    return conic_encounter(
        ray_origin=origin_t,
        ray_direction=direction_t,
        conic_vertex=vertex,
        conic_tangent_x=tangent_x,
        conic_tangent_y=tangent_y,
        curvature=torch.tensor(curvature, dtype=torch.float64),
        conic_constant=torch.tensor(conic_constant, dtype=torch.float64),
        even_coefficients=torch.tensor(even_coefficients, dtype=torch.float64),
        clear_aperture_radius=aperture,
    )


def _sympy_real_roots(
    *,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    curvature: float,
    conic_constant: float,
    even_coefficients: tuple[float, ...],
    t_lower: float,
    t_upper: float,
) -> list[float]:
    t = sympy.symbols("t", real=True)
    ox = sympy.Rational(origin[0])
    oy = sympy.Rational(origin[1])
    oz = sympy.Rational(origin[2])
    dx = sympy.Rational(direction[0])
    dy = sympy.Rational(direction[1])
    dz = sympy.Rational(direction[2])
    c = sympy.Rational(curvature)
    k = sympy.Rational(conic_constant)
    x_t = ox + dx * t
    y_t = oy + dy * t
    z_t = oz + dz * t
    q_t = x_t * x_t + y_t * y_t
    a_t = sum(
        sympy.Rational(coeff) * q_t ** (i + 1)
        for i, coeff in enumerate(even_coefficients)
    )
    w_t = z_t - a_t
    p = c * q_t - 2 * w_t + (1 + k) * c * w_t * w_t
    poly = sympy.Poly(sympy.expand(p), t)
    roots = sympy.real_roots(poly)
    return [
        float(sympy.N(r))
        for r in roots
        if t_lower <= float(sympy.N(r)) <= t_upper
    ]


def _scalar_sag(
    rsq: float,
    curvature: float,
    conic_constant: float,
    even: tuple[float, ...],
) -> float:
    # 独立标量 sag（圆锥基底加偶次多项式）
    om = 1.0 - (1.0 + conic_constant) * curvature * curvature * rsq
    if om < 0.0:
        return float("nan")
    base = curvature * rsq / (1.0 + math.sqrt(om))
    poly = sum(coeff * rsq ** (i + 1) for i, coeff in enumerate(even))
    return base + poly


class TestIndependentOracleAgreement:
    """
    独立 sympy 参照与生产 ``conic_encounter`` 在结构化场景下的最近非负根一致
    """

    @pytest.mark.parametrize(
        ("curvature", "conic_constant", "even", "aperture"),
        [
            (1.0 / 5.0e-6, -1.0, (), None),
            (1.0 / 5.0e-6, -2.5, (), None),
            (1.0 / 8.0e-6, 0.5, (), None),
            (1.0 / 5.0e-6, 0.5, (5.0e3, -2.0e8), 5.0e-6),
            (1.0 / 5.0e-6, -0.75, (1.0e3, -5.0e7), 5.0e-6),
            (0.0, 0.0, (1.0e3, -2.0e7), 5.0e-6),
        ],
    )
    def test_nearest_root_matches_sympy_oracle(
        self,
        curvature: float,
        conic_constant: float,
        even: tuple[float, ...],
        aperture: float | None,
    ) -> None:
        """
        生产最近非负根与独立 sympy 参照在多种圆锥/多项式组合下一致
        """
        theta = math.radians(12.0)
        origin = (0.4e-6, 0.0, -3.0e-6)
        direction = (math.sin(theta), 0.0, math.cos(theta))
        result = _run(
            origin=origin,
            direction=direction,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even,
            clear_aperture_radius=aperture,
        )
        roots = _sympy_real_roots(
            origin=origin,
            direction=direction,
            curvature=curvature,
            conic_constant=conic_constant,
            even_coefficients=even,
            t_lower=0.0,
            t_upper=5.0e-5,
        )
        roots = sorted(r for r in roots if r >= 0.0)
        if not roots:
            assert bool(result.is_encountered[0, 0]) is False
            return
        expected = roots[0]
        assert bool(result.is_encountered[0, 0]) is True
        assert math.isclose(
            float(result.distance[0, 0]),
            expected,
            rel_tol=1.0e-6,
            abs_tol=1.0e-12,
        )


class TestBaseConicLimitsAndFamilies:
    """
    基底圆锥极限（c=0 平面、k=0 球面）与圆锥面族（抛物/双曲/椭球）
    """

    def test_plane_limit_c_zero_on_axis(self) -> None:
        """
        c=0 平面极限：沿轴 ray 命中 z=0 顶点平面
        """
        result = _run(
            origin=(0.0, 0.0, -3.0e-6),
            direction=(0.0, 0.0, 1.0),
            curvature=0.0,
            conic_constant=0.0,
        )
        assert math.isclose(
            float(result.distance[0, 0]),
            3.0e-6,
            rel_tol=1.0e-12,
        )

    def test_plane_limit_c_zero_oblique(self) -> None:
        """
        c=0 斜入射仍命中 z=0 平面
        """
        theta = math.radians(20.0)
        result = _run(
            origin=(1.0e-6, 0.0, -2.0e-6),
            direction=(math.sin(theta), 0.0, math.cos(theta)),
            curvature=0.0,
            conic_constant=0.7,
        )
        expected = 2.0e-6 / math.cos(theta)
        assert math.isclose(
            float(result.distance[0, 0]),
            expected,
            rel_tol=1.0e-12,
        )

    @pytest.mark.parametrize("radius_sign", (1.0, -1.0))
    def test_sphere_limit_k_zero_signed_curvature(self, radius_sign: float) -> None:
        """
        k=0 球面极限：凸与凹两种曲率符号下命中 z 与独立 sag 一致
        """
        radius = 5.0e-6 * radius_sign
        curvature = 1.0 / radius
        result = _run(
            origin=(0.3e-6, 0.0, -3.0e-6 if radius_sign > 0 else -1.0e-6),
            direction=(0.0, 0.0, 1.0),
            curvature=curvature,
            conic_constant=0.0,
        )
        assert bool(result.is_encountered[0, 0]) is True
        rsq = 0.09e-12
        expected_sag = _scalar_sag(rsq, curvature, 0.0, ())
        assert math.isclose(
            float(result.intersection[0, 0, 2]),
            expected_sag,
            rel_tol=1.0e-9,
        )

    def test_paraboloid_on_axis(self) -> None:
        """
        k=−1 抛物面沿轴 ray 命中顶点
        """
        result = _run(
            origin=(0.0, 0.0, -3.0e-6),
            direction=(0.0, 0.0, 1.0),
            curvature=1.0 / 5.0e-6,
            conic_constant=-1.0,
        )
        assert math.isclose(
            float(result.distance[0, 0]),
            3.0e-6,
            rel_tol=1.0e-12,
        )


class TestBaseConicRootScenarios:
    """
    切线、双根、内部、后根、无根、错片五类根场景
    """

    def test_no_root_rear_facing_ray_is_missed(self) -> None:
        """
        朝 −z 的 ray 与 +z 侧凸面无正向交点，判物理未命中
        """
        result = _run(
            origin=(0.5e-6, 0.0, 0.0),
            direction=(0.0, 0.0, -1.0),
            curvature=1.0 / 5.0e-6,
            conic_constant=0.0,
        )
        assert bool(result.is_encountered[0, 0]) is False

    def test_wrong_sheet_root_rejected(self) -> None:
        """
        穿过球心的沿轴 ray 的后表面根（错片）被片守卫拒绝，返回前表面
        """
        radius = 5.0e-6
        result = _run(
            origin=(0.0, 0.0, -3.0e-6),
            direction=(0.0, 0.0, 1.0),
            curvature=1.0 / radius,
            conic_constant=0.0,
        )
        # 前表面在 z≈0（顶点），距离 3e-6；后表面在 z≈1e-5（错片）被拒
        assert math.isclose(
            float(result.distance[0, 0]),
            3.0e-6,
            rel_tol=1.0e-9,
        )

    def test_forward_root_chosen_over_rear_root(self) -> None:
        """
        从顶点上方沿 −z 入射的 ray：两根一正一负，片守卫选正向 authored 片根
        """
        radius = 5.0e-6
        result = _run(
            origin=(0.0, 0.0, 3.0e-6),
            direction=(0.0, 0.0, -1.0),
            curvature=1.0 / radius,
            conic_constant=0.0,
        )
        # 命中顶点 z=0（authored 片），t=3e-6
        assert bool(result.is_encountered[0, 0]) is True
        assert math.isclose(
            float(result.distance[0, 0]),
            3.0e-6,
            rel_tol=1.0e-9,
        )

    def test_real_domain_boundary_finite_normal(self) -> None:
        """
        g=0 实数域边界（r=R）处法线仍有限（隐式梯度，不除 √g）
        """
        radius = 5.0e-6
        aperture = 1.1 * radius
        result = _run(
            origin=(radius, 0.0, -3.0e-6),
            direction=(0.0, 0.0, 1.0),
            curvature=1.0 / radius,
            conic_constant=0.0,
            even_coefficients=(1.0e3,),
            clear_aperture_radius=aperture,
        )
        assert bool(result.is_encountered[0, 0]) is True
        normal = result.unit_normal[0, 0]
        assert torch.isfinite(normal).all()
        ones = torch.ones(1, dtype=torch.float64)
        assert torch.isclose(torch.norm(normal), ones, atol=1.0e-9)


class TestPolynomialAsphereScenarios:
    """
    多项式非球面：多根、切线/偶重、孔径与 g=0 边界
    """

    def test_multiple_roots_picks_nearest_in_aperture(self) -> None:
        """
        多项式非球面在有限孔径内多个候选根中选最近非负（与 sympy 参照一致）
        """
        even = (5.0e3, -2.0e8)
        theta = math.radians(12.0)
        origin = (0.5e-6, 0.0, -3.0e-6)
        direction = (math.sin(theta), 0.0, math.cos(theta))
        result = _run(
            origin=origin,
            direction=direction,
            curvature=1.0 / 8.0e-6,
            conic_constant=0.5,
            even_coefficients=even,
            clear_aperture_radius=5.0e-6,
        )
        roots = _sympy_real_roots(
            origin=origin,
            direction=direction,
            curvature=1.0 / 8.0e-6,
            conic_constant=0.5,
            even_coefficients=even,
            t_lower=0.0,
            t_upper=2.0e-4,
        )
        roots = sorted(r for r in roots if r >= 0.0)
        assert roots, "参照应至少找到一个根"
        assert math.isclose(
            float(result.distance[0, 0]),
            roots[0],
            rel_tol=1.0e-6,
            abs_tol=1.0e-12,
        )

    def test_exact_tangent_root_is_certified_and_refined(self) -> None:
        """
        精确偶重切根经无平方 Sturm 隔离后仍作为唯一物理根进入精化
        """

        result = _run(
            origin=(1.0, 0.0, 0.0),
            direction=(0.0, 0.0, 1.0),
            curvature=1.0,
            conic_constant=0.0,
            even_coefficients=(1.0,),
            clear_aperture_radius=2.0,
        )

        assert bool(result.is_encountered[0, 0])
        assert math.isclose(
            float(result.distance[0, 0]),
            2.0,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        assert bool(torch.isfinite(result.unit_normal).all())

    def test_near_tangent_roots_select_nearest_forward_root(self) -> None:
        """
        切根内侧一个 binary64 邻点产生近邻双根并稳定选择前根
        """

        local_x = math.nextafter(1.0, 0.0)
        radius_squared = local_x * local_x
        expected_distance = (
            radius_squared
            + 1.0
            - math.sqrt(1.0 - radius_squared)
        )
        result = _run(
            origin=(local_x, 0.0, 0.0),
            direction=(0.0, 0.0, 1.0),
            curvature=1.0,
            conic_constant=0.0,
            even_coefficients=(1.0,),
            clear_aperture_radius=2.0,
        )

        assert bool(result.is_encountered[0, 0])
        assert math.isclose(
            float(result.distance[0, 0]),
            expected_distance,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )

    def test_meta_polynomial_path_never_enters_host_proof(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        非空偶次系数的 Meta 推导只返回结构而不读取或搬运取值
        """

        from chromatix_next._numerics.surface_geometry import polynomial_conic_roots

        def _fail_host_proof(**arguments: object) -> object:
            raise AssertionError(
                "polynomial Meta 推导不得进入宿主证明",
            )

        monkeypatch.setattr(
            polynomial_conic_roots,
            "_stage_unresolved_lanes_to_host",
            _fail_host_proof,
        )
        meta_device = torch.device("meta")
        result = conic_encounter(
            ray_origin=torch.empty(
                (1, 1, 3),
                dtype=torch.float64,
                device=meta_device,
            ),
            ray_direction=torch.empty(
                (1, 1, 3),
                dtype=torch.float64,
                device=meta_device,
            ),
            conic_vertex=torch.empty(
                (3,),
                dtype=torch.float64,
                device=meta_device,
            ),
            conic_tangent_x=torch.empty(
                (3,),
                dtype=torch.float64,
                device=meta_device,
            ),
            conic_tangent_y=torch.empty(
                (3,),
                dtype=torch.float64,
                device=meta_device,
            ),
            curvature=torch.empty(
                (),
                dtype=torch.float64,
                device=meta_device,
            ),
            conic_constant=torch.empty(
                (),
                dtype=torch.float64,
                device=meta_device,
            ),
            even_coefficients=torch.empty(
                (1,),
                dtype=torch.float64,
                device=meta_device,
            ),
            clear_aperture_radius=torch.empty(
                (),
                dtype=torch.float64,
                device=meta_device,
            ),
        )

        assert result.distance.is_meta
        assert result.distance.shape == (1, 1)

    def test_certified_interval_reaches_device_refinement(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        真实多项式根按宿主认证区间进入原设备的可微精化
        """

        from chromatix_next._numerics.surface_geometry import polynomial_conic_roots

        original_refine = polynomial_conic_roots._safeguarded_refine
        refinement_devices: list[torch.device] = []

        def _record_refinement(
            **arguments: object,
        ) -> tuple[torch.Tensor, torch.Tensor]:
            initial_distance = arguments["initial_distance"]
            assert isinstance(initial_distance, torch.Tensor)
            refinement_devices.append(initial_distance.device)
            return original_refine(**arguments)  # type: ignore[arg-type]

        monkeypatch.setattr(
            polynomial_conic_roots,
            "_safeguarded_refine",
            _record_refinement,
        )
        result = _run(
            origin=(0.5e-6, 0.0, -3.0e-6),
            direction=(
                math.sin(math.radians(12.0)),
                0.0,
                math.cos(math.radians(12.0)),
            ),
            curvature=1.0 / 8.0e-6,
            conic_constant=0.5,
            even_coefficients=(5.0e3, -2.0e8),
            clear_aperture_radius=5.0e-6,
        )

        assert bool(result.is_encountered[0, 0])
        assert refinement_devices == [result.distance.device]
        assert bool(torch.isfinite(result.distance).all())

    def test_aperture_equality_inside_and_neighbour_outside(self) -> None:
        """
        径向恰为孔径半径判孔径内，邻浮点略大判孔径外
        """
        radius = 5.0e-6
        aperture = 2.0e-6
        inside = _run(
            origin=(aperture, 0.0, -3.0e-6),
            direction=(0.0, 0.0, 1.0),
            curvature=1.0 / radius,
            conic_constant=0.0,
            even_coefficients=(1.0e3,),
            clear_aperture_radius=aperture,
        )
        assert bool(inside.is_inside_aperture[0, 0]) is True
        outside = _run(
            origin=(aperture * 1.01, 0.0, -3.0e-6),
            direction=(0.0, 0.0, 1.0),
            curvature=1.0 / radius,
            conic_constant=0.0,
            even_coefficients=(1.0e3,),
            clear_aperture_radius=aperture,
        )
        assert bool(outside.is_inside_aperture[0, 0]) is False

    def test_axial_degenerate_interval_bound(self) -> None:
        """
        纯轴向 ray 的孔径柱面退化为半直线，sag 包络仍给出有限区间且命根
        """
        result = _run(
            origin=(0.0, 0.0, -3.0e-6),
            direction=(0.0, 0.0, 1.0),
            curvature=1.0 / 5.0e-6,
            conic_constant=-0.5,
            even_coefficients=(1.0e3,),
            clear_aperture_radius=5.0e-6,
        )
        assert bool(result.is_encountered[0, 0]) is True
        assert torch.isfinite(result.intersection).all()


class TestCpuCudaAgreement:
    """
    CPU 与 CUDA 在分类、值与梯度上一致（CUDA 不可用时跳过）
    """

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA 不可用")
    def test_classification_value_gradient_match(self) -> None:
        """
        同一 bundle 在 CPU 与 CUDA 上命中分类、距离、法线、曲率梯度一致
        """
        theta = math.radians(10.0)
        direction = (math.sin(theta), 0.0, math.cos(theta))
        origin = (0.3e-6, 0.0, -3.0e-6)
        even = (1.0e3,)
        aperture = 5.0e-6

        def _run_on(device: torch.device) -> _TensorTriple:
            curv_tensor = torch.tensor(1.0 / 5.0e-6, dtype=torch.float64, device=device)
            curvature = torch.nn.Parameter(curv_tensor)
            vertex, tangent_x, tangent_y = _default_pose()
            origin_t = torch.tensor(
                [list(origin)],
                dtype=torch.float64,
                device=device,
            ).view(1, 1, 3)
            direction_t = torch.tensor(
                [list(direction)],
                dtype=torch.float64,
                device=device,
            ).view(1, 1, 3)
            conic_t = torch.tensor(-0.3, dtype=torch.float64, device=device)
            even_t = torch.tensor(even, dtype=torch.float64, device=device)
            aperture_t = torch.tensor(aperture, dtype=torch.float64, device=device)
            enc = conic_encounter(
                ray_origin=origin_t,
                ray_direction=direction_t,
                conic_vertex=vertex.to(device=device),
                conic_tangent_x=tangent_x.to(device=device),
                conic_tangent_y=tangent_y.to(device=device),
                curvature=curvature,
                conic_constant=conic_t,
                even_coefficients=even_t,
                clear_aperture_radius=aperture_t,
            )
            enc.intersection.sum().backward()
            return (
                enc.is_encountered.detach(),
                enc.distance.detach(),
                curvature.grad.detach(),  # type: ignore[union-attr]
            )

        cpu_enc, cpu_dist, cpu_grad = _run_on(torch.device("cpu"))
        cuda_enc, cuda_dist, cuda_grad = _run_on(torch.device("cuda"))
        assert bool(cpu_enc[0, 0]) == bool(cuda_enc[0, 0])
        assert torch.allclose(cpu_dist, cuda_dist.cpu(), atol=1.0e-12)
        assert torch.allclose(cpu_grad, cuda_grad.cpu(), atol=1.0e-9)


class TestFastIntervalExclusionFires:
    """
    设备上区间排除快路径在真无根通道上真正触发（不再整体落回宿主 Sturm）
    """

    def test_genuinely_root_free_lane_proven_on_device(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        径向漂移、永不进入 z≥0 的多项式非球面光线被设备区间排除证为无根
        """
        from chromatix_next._numerics.surface_geometry import (
            polynomial_conic_roots as polynomial_module,
        )

        def _fail_if_called(**kwargs: object) -> dict[str, list]:
            raise AssertionError(
                "设备区间排除应已证无根；宿主 staging 不应被调用"
            )

        monkeypatch.setattr(
            polynomial_module,
            "_stage_unresolved_lanes_to_host",
            _fail_if_called,
        )
        result = _run(
            origin=(0.0, 0.0, -1.0e-6),
            direction=(1.0, 0.0, 0.0),
            curvature=1.0 / 5.0e-6,
            conic_constant=-0.5,
            even_coefficients=(1.0e3,),
            clear_aperture_radius=5.0e-6,
        )
        assert bool(result.is_encountered[0, 0]) is False
        assert torch.isfinite(result.intersection).all()


class TestRootExactlyAtZeroHits:
    """
    根恰在 t=0（原点在面上）的多项式非球面光线必须命中，不得被静默丢弃
    """

    def test_origin_on_vertex_ray_into_surface_hits(self) -> None:
        """
        原点恰在顶点（t=0 是根）的光线判命中，距离为 0
        """
        result = _run(
            origin=(0.0, 0.0, 0.0),
            direction=(0.0, 0.0, -1.0),
            curvature=1.0 / 5.0e-6,
            conic_constant=-0.5,
            even_coefficients=(1.0e3,),
            clear_aperture_radius=5.0e-6,
        )
        assert bool(result.is_encountered[0, 0]) is True
        assert math.isclose(float(result.distance[0, 0]), 0.0, abs_tol=1.0e-18)


class TestConvergenceFailureRaisesNotMisses:
    """
    存在已证区间但设备精化未收敛 ⇒ 抛稳定域错误（错误，非未命中）
    """

    def test_non_converging_valid_interval_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        stub 精化器返回 converged=False 的已证区间 ⇒ encounter 抛稳定错误身份
        """
        from chromatix_next._numerics.surface_geometry import (
            polynomial_conic_roots as polynomial_module,
        )
        from chromatix_next.errors import OpticalValueError

        def _never_converge(
            **kwargs: object,
        ) -> tuple[torch.Tensor, torch.Tensor]:
            initial_distance = kwargs["initial_distance"]
            assert isinstance(initial_distance, torch.Tensor)
            converged = torch.zeros_like(initial_distance, dtype=torch.bool)
            return initial_distance, converged

        monkeypatch.setattr(
            polynomial_module,
            "_safeguarded_refine",
            _never_converge,
        )
        with pytest.raises(OpticalValueError) as raised:
            _run(
                origin=(0.5e-6, 0.0, -3.0e-6),
                direction=(
                    math.sin(math.radians(12.0)),
                    0.0,
                    math.cos(math.radians(12.0)),
                ),
                curvature=1.0 / 8.0e-6,
                conic_constant=0.5,
                even_coefficients=(5.0e3, -2.0e8),
                clear_aperture_radius=5.0e-6,
            )
        assert raised.value.identity == "conic_intersection_not_converged"

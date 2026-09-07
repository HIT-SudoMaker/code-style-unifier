
from __future__ import annotations

import pytest
import torch

from chromatix_next.errors import (
    OpticalRuntimeError,
    OpticalTypeError,
    OpticalValueError,
)
from chromatix_next.optics.surface import ConicEvenAsphere


class TestConicEvenAspherePoseValidation:
    """
    姿态、曲率、圆锥常数、偶次系数与 aperture 校验
    """

    @pytest.mark.parametrize(
        ("parameter_name", "valid_value", "identity"),
        (
            ("curvature", 0.5, "conic_curvature_invalid"),
            ("conic_constant", -1.0, "conic_constant_invalid"),
        ),
    )
    def test_float32_parameter_rejected_with_owner_identity(
        self,
        parameter_name: str,
        valid_value: float,
        identity: str,
    ) -> None:
        """
        曲率与圆锥常数的单精度 Parameter 在 Surface 边界拒绝
        """

        arguments: dict[str, object] = {
            "curvature": 0.5,
            "conic_constant": -1.0,
        }
        arguments[parameter_name] = torch.nn.Parameter(
            torch.tensor(valid_value, dtype=torch.float32),
        )
        with pytest.raises(OpticalValueError) as information:
            ConicEvenAsphere(**arguments)  # type: ignore[arg-type]
        assert information.value.identity == identity

    def test_default_normal_yields_plus_z(self) -> None:
        """
        默认 tangent_x=ê_x、tangent_y=ê_y
        ⇒ 顶点法线 = cross(tangent_x, tangent_y) = +ê_z
        """

        conic = ConicEvenAsphere(curvature=1.0 / 5.0e-6, conic_constant=0.0)
        normal = conic.normal
        assert torch.allclose(
            normal,
            torch.tensor([0.0, 0.0, 1.0], dtype=normal.dtype),
            atol=1.0e-6,
        )

    def test_non_unit_axis_rejected(self) -> None:
        """
        非单位 axis ⇒ 拒绝；圆锥面不静默归一化
        """

        with pytest.raises(OpticalValueError) as rejected:
            ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=0.0,
                tangent_x=(2.0, 0.0, 0.0),
            )
        assert rejected.value.identity == "conic_tangent_x_not_unit"

    def test_non_orthogonal_basis_rejected(self) -> None:
        """
        平行两轴 ⇒ 非正交拒绝
        """

        with pytest.raises(OpticalValueError) as rejected:
            ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=0.0,
                tangent_x=(1.0, 0.0, 0.0),
                tangent_y=(1.0, 0.0, 0.0),
            )
        assert rejected.value.identity == "conic_basis_not_orthogonal"

    @pytest.mark.parametrize(
        "invalid_curvature",
        (float("nan"), float("inf"), -float("inf")),
    )
    def test_non_finite_curvature_rejected(
        self,
        invalid_curvature: float,
    ) -> None:
        """
        非有限曲率 ⇒ 拒绝（零曲率合法，表示纯多项式非球面）
        """

        with pytest.raises(OpticalValueError) as rejected:
            ConicEvenAsphere(
                curvature=invalid_curvature,
                conic_constant=0.0,
            )
        assert rejected.value.identity == "conic_curvature_invalid"

    @pytest.mark.parametrize(
        "invalid_conic",
        (float("nan"), float("inf")),
    )
    def test_non_finite_conic_constant_rejected(
        self,
        invalid_conic: float,
    ) -> None:
        """
        非有限圆锥常数 ⇒ 拒绝（任意有限实数合法，包括 −1、<−1、>−1）
        """

        with pytest.raises(OpticalValueError) as rejected:
            ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=invalid_conic,
            )
        assert rejected.value.identity == "conic_constant_invalid"

    def test_non_finite_even_coefficient_rejected(self) -> None:
        """
        even_coefficients 含非有限值 ⇒ 拒绝
        """

        with pytest.raises(OpticalValueError) as rejected:
            ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=0.0,
                even_coefficients=(1.0, float("nan")),
            )
        assert rejected.value.identity == "conic_even_coefficients_invalid"

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
            ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=0.0,
                clear_aperture_radius=invalid_aperture,
            )
        assert rejected.value.identity == "conic_clear_aperture_radius_invalid"

    def test_aperture_outside_real_sag_domain_rejected_at_construction(
        self,
    ) -> None:
        with pytest.raises(OpticalValueError) as rejected:
            ConicEvenAsphere(
                curvature=1.0,
                conic_constant=0.0,
                even_coefficients=(1.0e-6,),
                clear_aperture_radius=2.0,
            )
        assert (
            rejected.value.identity
            == "conic_even_asphere_aperture_outside_real_domain"
        )

    def test_aperture_outside_real_sag_domain_rejected_at_consume_seam(
        self,
    ) -> None:
        conic = ConicEvenAsphere(
            curvature=0.1,
            conic_constant=0.0,
            even_coefficients=(1.0e-6,),
            clear_aperture_radius=2.0,
        )
        conic.curvature.fill_(1.0)

        with pytest.raises(OpticalValueError) as rejected:
            conic._validate_physical_state()  # noqa: SLF001

        assert (
            rejected.value.identity
            == "conic_even_asphere_aperture_outside_real_domain"
        )

    def test_plain_non_parameter_tensor_aperture_rejected(self) -> None:
        """
        普通（非 Parameter）张量 ⇒ 稳定域类型错误，不泄漏裸断言
        """

        with pytest.raises(OpticalTypeError) as rejected:
            ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=0.0,
                clear_aperture_radius=torch.tensor(4.0e-6),  # type: ignore[arg-type]
            )
        assert (
            rejected.value.identity
            == "conic_clear_aperture_radius_invalid"
        )

    def test_zero_curvature_accepted_for_pure_asphere(self) -> None:
        """
        零曲率 + 非零偶次系数 + 正孔径 ⇒ 合法（纯多项式非球面，无圆锥基底）
        """

        conic = ConicEvenAsphere(
            curvature=0.0,
            conic_constant=0.0,
            even_coefficients=(1.0e3, -2.0e7),
            clear_aperture_radius=5.0e-6,
        )
        assert torch.isclose(
            conic.curvature,
            torch.tensor(0.0, dtype=torch.float64),
        )
        assert conic.even_coefficients.shape == (2,)

    def test_even_asphere_without_clear_aperture_rejected(self) -> None:
        """
        非空偶次系数向量但无有限孔径 ⇒ 构造期以稳定身份拒绝
        （多项式非球面求交证明依赖孔径柱面导出有限搜索区间）
        """

        with pytest.raises(OpticalValueError) as rejected:
            ConicEvenAsphere(
                curvature=1.0 / 5.0e-6,
                conic_constant=0.0,
                even_coefficients=(1.0e3, -2.0e7),
            )
        assert (
            rejected.value.identity
            == "conic_even_asphere_clear_aperture_required"
        )

    def test_base_conic_without_aperture_accepted(self) -> None:
        """
        基底圆锥（空偶次系数）不要求孔径：合法（解析二次求交，无搜索区间需求）
        """

        conic = ConicEvenAsphere(
            curvature=1.0 / 5.0e-6,
            conic_constant=-0.5,
        )
        assert conic._aperture_value is None  # noqa: SLF001

    def test_consume_seam_rejects_even_asphere_without_aperture(self) -> None:
        """
        构造后把 even_coefficients 改成非空但无孔径 ⇒ consume seam 复核拒绝
        """

        conic = ConicEvenAsphere(
            curvature=1.0 / 5.0e-6,
            conic_constant=0.0,
            clear_aperture_radius=5.0e-6,
        )
        # 把 aperture buffer 移除模拟"构造后状态变异使孔径消失"；consume seam 必须拒绝
        del conic._buffers["clear_aperture_radius"]
        conic.even_coefficients = torch.nn.Parameter(
            torch.tensor([1.0e3], dtype=torch.float64)
        )
        with pytest.raises(OpticalValueError) as rejected:
            conic._validate_physical_state()  # noqa: SLF001
        assert (
            rejected.value.identity
            == "conic_even_asphere_clear_aperture_required"
        )


class TestConicEvenAsphereForwardRejected:
    """
    ConicEvenAsphere 是被动 adapter，forward 永远 raise（稳定身份）
    """

    def test_forward_raises_stable_identity(self) -> None:
        """
        被动 adapter 不提供 forward 动作而抛稳定身份错误

        错误身份为 ``conic_even_asphere_has_no_forward_action``
        """

        conic = ConicEvenAsphere(curvature=1.0 / 5.0e-6, conic_constant=0.0)
        with pytest.raises(OpticalRuntimeError) as rejected:
            conic()
        assert (
            rejected.value.identity
            == "conic_even_asphere_has_no_forward_action"
        )


class TestConicEvenAsphereTrainableState:
    """
    Parameter 身份保留与 state_dict 往返
    """

    def test_state_dict_has_exact_tangent_pose_key_set(self) -> None:
        """
        Conic 状态键集只保留新的 vertex 与 tangent 物理命名
        """

        conic = ConicEvenAsphere()
        assert frozenset(conic.state_dict()) == frozenset(
            {
                "vertex",
                "tangent_x",
                "tangent_y",
                "curvature",
                "conic_constant",
                "even_coefficients",
            }
        )

    def test_trainable_shape_parameters_keep_optimizer_identity(self) -> None:
        """
        曲率与圆锥常数 Parameter 保持同一注册对象并对优化器可见
        """

        curvature = torch.nn.Parameter(
            torch.tensor(1.0 / 5.0e-6, dtype=torch.float64),
        )
        conic_constant = torch.nn.Parameter(
            torch.tensor(-0.5, dtype=torch.float64),
        )
        conic = ConicEvenAsphere(
            curvature=curvature,
            conic_constant=conic_constant,
        )
        parameters = dict(conic.named_parameters())

        assert conic.curvature is curvature
        assert conic.conic_constant is conic_constant
        assert parameters["curvature"] is curvature
        assert parameters["conic_constant"] is conic_constant

    def test_trainable_even_coefficients_preserve_parameter_identity(self) -> None:
        """
        Parameter 偶次系数向量保持身份
        """

        coefficients_param = torch.nn.Parameter(
            torch.tensor([1.0e3, -2.0e7], dtype=torch.float64),
        )
        conic = ConicEvenAsphere(
            curvature=1.0 / 5.0e-6,
            conic_constant=0.0,
            even_coefficients=coefficients_param,
            clear_aperture_radius=5.0e-6,
        )
        assert isinstance(conic.even_coefficients, torch.nn.Parameter)

    def test_state_dict_round_trip_preserves_parameters(self) -> None:
        """
        Parameter Conic dump-load 回自身：身份保持 Parameter，值精确保留
        """

        curvature_param = torch.nn.Parameter(
            torch.tensor(1.0 / 5.0e-6, dtype=torch.float64),
        )
        conic_param = torch.nn.Parameter(
            torch.tensor(-0.5, dtype=torch.float64),
        )
        original = ConicEvenAsphere(
            curvature=curvature_param,
            conic_constant=conic_param,
            even_coefficients=(1.0e3,),
            clear_aperture_radius=5.0e-6,
        )
        state = original.state_dict()
        round_trip = ConicEvenAsphere(
            curvature=torch.nn.Parameter(
                torch.tensor(1.0e-6, dtype=torch.float64),
            ),
            conic_constant=torch.nn.Parameter(
                torch.tensor(0.0, dtype=torch.float64),
            ),
            even_coefficients=(0.0,),
            clear_aperture_radius=5.0e-6,
        )
        round_trip.load_state_dict(state)
        assert isinstance(round_trip.curvature, torch.nn.Parameter)
        assert torch.isclose(
            round_trip.curvature,
            torch.tensor(1.0 / 5.0e-6, dtype=torch.float64),
        )
        assert isinstance(round_trip.conic_constant, torch.nn.Parameter)
        assert torch.isclose(
            round_trip.conic_constant,
            torch.tensor(-0.5, dtype=torch.float64),
        )

    def test_validate_physical_state_rejects_mutated_curvature(self) -> None:
        """
        构造后把曲率参数改成 NaN ⇒ ``_validate_physical_state`` 拒绝
        """

        curvature_param = torch.nn.Parameter(
            torch.tensor(1.0 / 5.0e-6, dtype=torch.float64),
        )
        conic = ConicEvenAsphere(curvature=curvature_param, conic_constant=0.0)
        with torch.no_grad():
            curvature_param.fill_(float("nan"))
        with pytest.raises(OpticalValueError) as rejected:
            conic._validate_physical_state()  # noqa: SLF001
        assert rejected.value.identity == "conic_curvature_invalid"

    def test_validate_physical_state_rejects_mutated_origin(self) -> None:
        """
        构造后把可训练顶点原点改成 NaN ⇒ ``_validate_physical_state`` 拒绝
        （origin 作为 Parameter 可被 optimizer 变异，consumption 复核必须覆盖）
        """

        origin_param = torch.nn.Parameter(
            torch.tensor((0.0, 0.0, 5.0e-6), dtype=torch.float64),
        )
        conic = ConicEvenAsphere(
            vertex=origin_param,
            curvature=1.0 / 5.0e-6,
            conic_constant=0.0,
        )
        with torch.no_grad():
            origin_param[0].fill_(float("nan"))
        with pytest.raises(OpticalValueError) as rejected:
            conic._validate_physical_state()  # noqa: SLF001
        assert rejected.value.identity == "conic_vertex_invalid"

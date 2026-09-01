
from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from chromatix_next.optics import (
    ConstantMedium,
    Medium,
    SellmeierMedium,
    TabulatedMedium,
    Vacuum,
)


class TestTabulatedMedium:
    """
    表格插值介质契约
    """

    def test_linear_interpolation_matches_independent_reference(self) -> None:
        """线性插值结果须与独立实现的 numpy 插值一致

        证据层 2：实现使用 ``torch.searchsorted`` 路径；独立参照使用 ``numpy.interp``，
        刻意不同的代码路径提供真正的交叉验证。采样点覆盖表内多个区间。
        """
        wavelengths_table = (0.40e-6, 0.50e-6, 0.60e-6, 0.70e-6)
        indices_table = (1.53, 1.52, 1.51, 1.50)
        medium = TabulatedMedium(
            wavelengths=wavelengths_table,
            refractive_indices=indices_table,
        )
        query = torch.tensor(
            [0.45e-6, 0.55e-6, 0.65e-6, 0.50e-6],
            dtype=torch.float64,
        )
        result = medium.refractive_index(query)
        reference = np.interp(
            query.numpy(),
            np.array(wavelengths_table, dtype=np.float64),
            np.array(indices_table, dtype=np.float64),
        )
        assert torch.allclose(
            result,
            torch.from_numpy(reference),
            atol=1e-12,
        )

    def test_returns_positive_real_indices(self) -> None:
        """
        折射率须为正实数（规约"Propagation Medium"）
        """
        medium = TabulatedMedium(
            wavelengths=(0.40e-6, 0.70e-6),
            refractive_indices=(1.5, 1.4),
        )
        query = torch.tensor([0.50e-6, 0.60e-6], dtype=torch.float64)
        result = medium.refractive_index(query)
        assert not torch.is_complex(result)
        assert torch.all(result > 0)

    def test_out_of_range_wavelength_rejected_at_boundary(self) -> None:
        """表外波长须在介质边界以稳定身份拒绝，绝不静默外推

        规约"Propagation Medium"_Avoid_："silent extrapolation"。低于下限或高于上限
        均须拒绝。
        """
        medium = TabulatedMedium(
            wavelengths=(0.40e-6, 0.70e-6),
            refractive_indices=(1.5, 1.4),
        )
        with pytest.raises(

            ValueError,

            match="tabulated_medium_wavelength_out_of_range",

        ):
            medium.refractive_index(torch.tensor([0.30e-6], dtype=torch.float64))
        with pytest.raises(

            ValueError,

            match="tabulated_medium_wavelength_out_of_range",

        ):
            medium.refractive_index(torch.tensor([0.80e-6], dtype=torch.float64))

    def test_table_endpoints_accepted(self) -> None:
        """
        表端点波长须被接受（闭区间）
        """
        medium = TabulatedMedium(
            wavelengths=(0.40e-6, 0.70e-6),
            refractive_indices=(1.5, 1.4),
        )
        result = medium.refractive_index(
            torch.tensor([0.40e-6, 0.70e-6], dtype=torch.float64)
        )
        assert torch.allclose(result, torch.tensor([1.5, 1.4], dtype=torch.float64))

    def test_non_monotonic_wavelengths_rejected(self) -> None:
        """
        波长表须严格递增
        """
        with pytest.raises(ValueError, match="tabulated_medium_wavelengths_invalid"):
            TabulatedMedium(
                wavelengths=(0.50e-6, 0.40e-6, 0.60e-6),
                refractive_indices=(1.5, 1.4, 1.3),
            )

    def test_length_mismatch_rejected(self) -> None:
        """
        波长表与折射率表长度须一致
        """
        with pytest.raises(

            ValueError,

            match="tabulated_medium_refractive_indices_invalid",

        ):
            TabulatedMedium(
                wavelengths=(0.40e-6, 0.70e-6),
                refractive_indices=(1.5, 1.4, 1.3),
            )

    def test_non_positive_index_rejected(self) -> None:
        """
        折射率表项须为正有限实数
        """
        for bad_index in (0.0, -1.0, float("nan")):
            with pytest.raises(

                ValueError,

                match="tabulated_medium_refractive_indices_invalid",

            ):
                TabulatedMedium(
                    wavelengths=(0.40e-6, 0.70e-6),
                    refractive_indices=(1.5, bad_index),
                )

    def test_too_short_table_rejected(self) -> None:
        """
        表至少需要 2 个采样点以定义插值
        """
        with pytest.raises(ValueError, match="tabulated_medium_wavelengths_invalid"):
            TabulatedMedium(
                wavelengths=(0.50e-6,),
                refractive_indices=(1.5,),
            )

    def test_immutable(self) -> None:
        """
        介质为不可变物理值
        """
        medium = TabulatedMedium(
            wavelengths=(0.40e-6, 0.70e-6),
            refractive_indices=(1.5, 1.4),
        )
        with pytest.raises(AttributeError):
            medium.wavelengths = (0.30e-6, 0.80e-6)  # type: ignore[misc]

    def test_is_medium(self) -> None:
        """
        表格介质实现 ``Medium`` 抽象接口
        """
        medium = TabulatedMedium(
            wavelengths=(0.40e-6, 0.70e-6),
            refractive_indices=(1.5, 1.4),
        )
        assert isinstance(medium, Medium)


class TestSellmeierMedium:
    """
    Sellmeier 色散介质契约
    """

    # N-BK7（SCHOTT）标准 Sellmeier 系数；λ 以 µm 为单位代入公式
    _BK7_B = (1.03961212, 0.231792344, 1.01046945)
    _BK7_C = (6.00069867e-3, 2.00179144e-2, 1.03560653e2)
    _BK7_RANGE = (0.3e-6, 2.5e-6)

    def _bk7(self) -> SellmeierMedium:
        # 构造 N-BK7 Sellmeier 介质
        return SellmeierMedium(
            b_coefficients=self._BK7_B,
            c_coefficients=self._BK7_C,
            wavelength_min=self._BK7_RANGE[0],
            wavelength_max=self._BK7_RANGE[1],
        )

    def test_matches_independent_sellmeier_formula(self) -> None:
        """折射率须与独立实现的 Sellmeier 公式一致

        证据层 2：n²(λ) = 1 + Σᵢ Bᵢλ²/(λ² − Cᵢ)，λ 以 µm 代入。测试用纯 Python 循环
        独立重算公式，刻意避开实现内部张量化路径，提供交叉验证。采样覆盖可见与近红外。
        """
        medium = self._bk7()
        wavelengths = torch.tensor(
            [0.40e-6, 0.50e-6, 0.60e-6, 1.00e-6, 2.00e-6],
            dtype=torch.float64,
        )
        result = medium.refractive_index(wavelengths)
        reference = torch.empty_like(result)
        for index, wavelength in enumerate(wavelengths.tolist()):
            lambda_um = wavelength * 1.0e6
            squared = 1.0
            for b_coeff, c_coeff in zip(self._BK7_B, self._BK7_C, strict=True):
                squared += b_coeff * lambda_um**2 / (lambda_um**2 - c_coeff)
            reference[index] = math.sqrt(squared)
        assert torch.allclose(result, reference, atol=1e-12)

    def test_bk7_anchors_to_known_literature_value(self) -> None:
        """N-BK7 在 He d 线（587.6 nm）折射率锚定文献值 ≈ 1.5168

        证据层 2（文献锚点）：SCHOTT N-BK7 数据表在 587.561 nm 给出 n_d ≈ 1.51680。
        """
        medium = self._bk7()
        wavelength = torch.tensor([587.561e-9], dtype=torch.float64)
        result = medium.refractive_index(wavelength)
        assert float(result.item()) == pytest.approx(1.5168, abs=2.0e-4)

    def test_returns_positive_real_indices(self) -> None:
        """
        折射率须为正实数
        """
        medium = self._bk7()
        query = torch.tensor([0.40e-6, 0.50e-6], dtype=torch.float64)
        result = medium.refractive_index(query)
        assert not torch.is_complex(result)
        assert torch.all(result > 1.0)

    def test_out_of_range_wavelength_rejected_at_boundary(self) -> None:
        """
        声明范围外的波长须在介质边界以稳定身份拒绝
        """
        medium = self._bk7()
        with pytest.raises(

            ValueError,

            match="sellmeier_medium_wavelength_out_of_range",

        ):
            medium.refractive_index(torch.tensor([0.20e-6], dtype=torch.float64))
        with pytest.raises(

            ValueError,

            match="sellmeier_medium_wavelength_out_of_range",

        ):
            medium.refractive_index(torch.tensor([3.00e-6], dtype=torch.float64))

    def test_range_endpoints_accepted(self) -> None:
        """
        声明范围端点须被接受（闭区间）
        """
        medium = self._bk7()
        result = medium.refractive_index(
            torch.tensor([0.3e-6, 2.5e-6], dtype=torch.float64)
        )
        assert torch.all(result > 0)

    def test_coefficient_length_mismatch_rejected(self) -> None:
        """
        B 系数与 C 系数长度须一致
        """
        with pytest.raises(

            ValueError,

            match="sellmeier_medium_coefficients_invalid",

        ):
            SellmeierMedium(
                b_coefficients=(1.0, 0.2),
                c_coefficients=(1.0e-3,),
                wavelength_min=0.3e-6,
                wavelength_max=2.5e-6,
            )

    def test_non_finite_coefficient_rejected(self) -> None:
        """
        系数须为有限实数
        """
        with pytest.raises(

            ValueError,

            match="sellmeier_medium_coefficients_invalid",

        ):
            SellmeierMedium(
                b_coefficients=(float("nan"), 0.2),
                c_coefficients=(1.0e-3, 2.0e-2),
                wavelength_min=0.3e-6,
                wavelength_max=2.5e-6,
            )

    def test_inverted_range_rejected(self) -> None:
        """
        声明范围下限须严格小于上限
        """
        with pytest.raises(ValueError, match="sellmeier_medium_range_invalid"):
            SellmeierMedium(
                b_coefficients=self._BK7_B,
                c_coefficients=self._BK7_C,
                wavelength_min=2.5e-6,
                wavelength_max=0.3e-6,
            )

    def test_immutable(self) -> None:
        """
        介质为不可变物理值
        """
        medium = self._bk7()
        with pytest.raises(AttributeError):
            medium.b_coefficients = (0.0,)  # type: ignore[misc]

    def test_is_medium(self) -> None:
        """
        Sellmeier 介质实现 ``Medium`` 抽象接口
        """
        assert isinstance(self._bk7(), Medium)


class TestMediumHierarchy:
    """
    介质等级与既有介质回归
    """

    def test_vacuum_and_constant_medium_still_work(self) -> None:
        """
        ``Vacuum``/``ConstantMedium`` 保持固定双精度查询（固定双精度查询）
        """
        wavelengths = torch.tensor(
            [0.5e-6, 0.6e-6],
            dtype=torch.float64,
        )
        assert torch.allclose(
            Vacuum().refractive_index(wavelengths),
            torch.ones(2, dtype=torch.float64),
        )
        assert torch.allclose(
            ConstantMedium(index=1.33).refractive_index(wavelengths),
            torch.full((2,), 1.33, dtype=torch.float64),
        )

    def test_fp64_query_yields_independent_sellmeier_reference(self) -> None:
        """float64 查询下 Sellmeier 折射率与独立 Python 公式一致

        原 ``test_precision_consistency`` 跨 f32/f64 一致性 parametrize
        是兼容性证据（"f32 也给出物理同一值"），不属于当前固定双精度契约。本测试
        固定双精度独立参照：用 Python 浮点循环独立重算 Sellmeier 公式（不依赖实
        现内部的张量化路径），与介质查询结果交叉验证。
        """
        medium = self._bk7_like()
        wavelengths_64 = torch.tensor(
            [0.45e-6, 0.55e-6],
            dtype=torch.float64,
        )
        result = medium.refractive_index(wavelengths_64)
        # 独立参照：纯 Python Sellmeier 公式
        b_coefficients = (1.03961212, 0.231792344, 1.01046945)
        c_coefficients = (6.00069867e-3, 2.00179144e-2, 1.03560653e2)
        reference = torch.empty_like(result)
        for index, wavelength in enumerate(wavelengths_64.tolist()):
            lambda_um = wavelength * 1.0e6
            squared = 1.0
            for b_coeff, c_coeff in zip(
                b_coefficients,
                c_coefficients,
                strict=True,
            ):
                squared += b_coeff * lambda_um**2 / (
                    lambda_um**2 - c_coeff
                )
            reference[index] = math.sqrt(squared)
        assert torch.allclose(result, reference, atol=1.0e-12)

    @staticmethod
    def _bk7_like() -> SellmeierMedium:
        # 构造测试用 Sellmeier 介质
        return SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.01046945),
            c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.03560653e2),
            wavelength_min=0.3e-6,
            wavelength_max=2.5e-6,
        )


class TestMediumPhysicalIdentity:
    """
    介质缓存身份契约：身份由各 Medium 自其固定状态派生

    色散介质身份必须包含状态内容；``_medium_identity`` 不得仅以
    类型限定名 + 可选折射率 ``index`` 标识介质，导致 ``TabulatedMedium``/
    ``SellmeierMedium``（无 ``.index``）不论其实际表/系数如何都被判为同一身份——
    当按携带色散介质的光场缓存派生量时构成潜在契约缺口。身份现由各
    Medium 经 ``physical_identity()`` 自其完整固定物理载荷派生。
    """

    def test_vacuum_and_constant_medium_identity(self) -> None:
        """
        真空身份为常量；恒定介质身份由折射率唯一决定且相等介质产生相等身份
        """
        assert Vacuum().physical_identity() == Vacuum().physical_identity()
        assert ConstantMedium(index=1.5).physical_identity() == ConstantMedium(
            index=1.5
        ).physical_identity()
        assert (
            ConstantMedium(index=1.5).physical_identity()
            != ConstantMedium(index=1.6).physical_identity()
        )

    def test_tabulated_distinguishes_different_tables(self) -> None:
        """
        折射率表或波长表不同的表格介质须给出不同身份
        """
        medium_a = TabulatedMedium(
            wavelengths=(0.40e-6, 0.70e-6),
            refractive_indices=(1.5, 1.4),
        )
        medium_a_same = TabulatedMedium(
            wavelengths=(0.40e-6, 0.70e-6),
            refractive_indices=(1.5, 1.4),
        )
        medium_b = TabulatedMedium(
            wavelengths=(0.40e-6, 0.70e-6),
            refractive_indices=(1.6, 1.4),  # 不同折射率表
        )
        medium_c = TabulatedMedium(
            wavelengths=(0.40e-6, 0.80e-6),  # 不同波长表
            refractive_indices=(1.5, 1.4),
        )
        # 相等介质产生相等身份
        assert medium_a.physical_identity() == medium_a_same.physical_identity()
        # 不同折射率表产生不同身份
        assert medium_a.physical_identity() != medium_b.physical_identity()
        # 不同波长表产生不同身份
        assert medium_a.physical_identity() != medium_c.physical_identity()

    def test_sellmeier_distinguishes_different_coefficients(self) -> None:
        """
        B/C 系数或声明范围不同的 Sellmeier 介质须给出不同身份
        """
        bk7 = SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.01046945),
            c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.03560653e2),
            wavelength_min=0.3e-6,
            wavelength_max=2.5e-6,
        )
        bk7_same = SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.01046945),
            c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.03560653e2),
            wavelength_min=0.3e-6,
            wavelength_max=2.5e-6,
        )
        different_b = SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.02046945),  # 改第三项 B
            c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.03560653e2),
            wavelength_min=0.3e-6,
            wavelength_max=2.5e-6,
        )
        different_c = SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.01046945),
            c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.04560653e2),  # 改第三项 C
            wavelength_min=0.3e-6,
            wavelength_max=2.5e-6,
        )
        different_range = SellmeierMedium(
            b_coefficients=(1.03961212, 0.231792344, 1.01046945),
            c_coefficients=(6.00069867e-3, 2.00179144e-2, 1.03560653e2),
            wavelength_min=0.3e-6,
            wavelength_max=2.0e-6,  # 不同声明范围上限
        )
        assert bk7.physical_identity() == bk7_same.physical_identity()
        assert bk7.physical_identity() != different_b.physical_identity()
        assert bk7.physical_identity() != different_c.physical_identity()
        assert bk7.physical_identity() != different_range.physical_identity()


class TestFiniteMediumState:
    """
    内建传播介质的有限输入、有限状态与有限输出边界
    """

    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_constant_medium_rejects_nonfinite_index(
        self,
        invalid_value: float,
    ) -> None:
        """
        恒定折射率中的 NaN 与正负无穷须由 ConstantMedium 拒绝
        """

        with pytest.raises(
            ValueError,
            match="constant_medium_index_nonfinite",
        ):
            ConstantMedium(index=invalid_value)

    @pytest.mark.parametrize(
        ("medium", "error_identity"),
        [
            (Vacuum(), "medium_wavelength_query_invalid"),
            (
                ConstantMedium(index=1.5),
                "medium_wavelength_query_invalid",
            ),
            (
                TabulatedMedium(
                    wavelengths=(0.4e-6, 0.7e-6),
                    refractive_indices=(1.5, 1.4),
                ),
                "medium_wavelength_query_invalid",
            ),
            (
                SellmeierMedium(
                    b_coefficients=(1.0,),
                    c_coefficients=(0.01,),
                    wavelength_min=0.3e-6,
                    wavelength_max=0.8e-6,
                ),
                "medium_wavelength_query_invalid",
            ),
        ],
        ids=["vacuum", "constant", "tabulated", "sellmeier"],
    )
    @pytest.mark.parametrize(
        "invalid_value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_builtin_medium_rejects_nonfinite_wavelength_query(
        self,
        medium: Medium,
        error_identity: str,
        invalid_value: float,
    ) -> None:
        """
        每个内建介质都须在公式计算前拒绝非有限查询波长
        """

        with pytest.raises(ValueError, match=error_identity):
            medium.refractive_index(
                torch.tensor([invalid_value], dtype=torch.float64),
            )

    def test_sellmeier_rejects_nonfinite_formula_output(self) -> None:
        """
        Sellmeier 共振奇点产生非有限 n² 时须由介质边界拒绝
        """

        medium = SellmeierMedium(
            b_coefficients=(1.0,),
            c_coefficients=(0.25,),
            wavelength_min=0.4e-6,
            wavelength_max=0.6e-6,
        )

        with pytest.raises(
            ValueError,
            match="medium_refractive_index_output_invalid",
        ):
            medium.refractive_index(
                torch.tensor([0.5e-6], dtype=torch.float64),
            )

    def test_distinct_medium_types_produce_distinct_identities(self) -> None:
        """
        不同类型介质身份互不相同（避免跨类型碰撞）
        """
        identities = {
            Vacuum().physical_identity(),
            ConstantMedium(index=1.0).physical_identity(),
            TabulatedMedium(
                wavelengths=(0.40e-6, 0.70e-6),
                refractive_indices=(1.0, 1.0),
            ).physical_identity(),
            SellmeierMedium(
                b_coefficients=(1.0,),
                c_coefficients=(1.0e-3,),
                wavelength_min=0.3e-6,
                wavelength_max=2.5e-6,
            ).physical_identity(),
        }
        assert len(identities) == 4


class _ThirdPartyMedium(Medium):
    def __init__(self, result_kind: str = "valid") -> None:
        """
        构造指定公式输出类别的第三方介质替身
        """

        self.result_kind = result_kind

    def _evaluate_refractive_index(
        self,
        wavelengths: torch.Tensor,
    ) -> torch.Tensor:
        if self.result_kind == "negative":
            return torch.full_like(wavelengths, -1.0)
        if self.result_kind == "nonfinite":
            return torch.full_like(wavelengths, float("nan"))
        if self.result_kind == "wrong_shape":
            return torch.ones((1,), dtype=wavelengths.dtype)
        if self.result_kind == "wrong_dtype":
            return torch.ones(wavelengths.shape, dtype=torch.float32)
        return torch.ones_like(wavelengths)

    def _physical_identity(self) -> tuple[object, ...]:
        return ("third_party", self.result_kind)


class _TensorIdentityMedium(_ThirdPartyMedium):
    def _physical_identity(self) -> tuple[object, ...]:
        return ("tensor_identity", torch.tensor(1.0))


class _UnstableIdentityMedium(_ThirdPartyMedium):
    def __init__(self) -> None:
        """
        构造每次读取都会改变身份载荷的介质替身
        """

        super().__init__()
        self.call_count = 0

    def _physical_identity(self) -> tuple[object, ...]:
        self.call_count += 1
        return ("unstable_identity", self.call_count)


class TestMediumPublicBoundary:
    """
    Medium 公共入口统一拥有查询、公式输出与完整物理身份契约
    """

    @pytest.mark.parametrize(
        "invalid_query",
        [
            object(),
            torch.tensor(0.5e-6),
            torch.ones((1, 1), dtype=torch.float64),
            torch.ones((1,), dtype=torch.int64),
            torch.ones((1,), dtype=torch.complex128),
            torch.ones((1,), dtype=torch.float32),
            torch.tensor([0.0], dtype=torch.float64),
            torch.tensor([float("nan")], dtype=torch.float64),
        ],
        ids=[
            "not_tensor",
            "scalar",
            "matrix",
            "integer",
            "complex",
            "float32",
            "nonpositive",
            "nonfinite",
        ],
    )
    def test_public_query_contract_uses_stable_medium_owner(
        self,
        invalid_query: object,
    ) -> None:
        """
        查询形状、float64 精度、有限性和正值均由 Medium 公共入口统一拒绝

        float32 一维波长张量不再被静默
        镜像，而是在 owner 入口直接拒绝。
        """

        error_type = TypeError if not isinstance(
            invalid_query,
            torch.Tensor,
        ) else ValueError
        with pytest.raises(
            error_type,
            match="medium_wavelength_query_invalid",
        ):
            _ThirdPartyMedium().refractive_index(
                invalid_query,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "result_kind",
        ["negative", "nonfinite", "wrong_shape", "wrong_dtype"],
    )
    def test_third_party_output_is_guarded_by_medium(
        self,
        result_kind: str,
    ) -> None:
        """
        第三方公式无法绕过正实、有限、同形状和同精度输出契约
        """

        with pytest.raises(
            ValueError,
            match="medium_refractive_index_output_invalid",
        ):
            _ThirdPartyMedium(result_kind).refractive_index(
                torch.tensor([0.5e-6, 0.6e-6], dtype=torch.float64),
            )

    def test_physical_identity_rejects_tensor_payload(self) -> None:
        """
        介质物理身份必须是无张量载荷
        """

        with pytest.raises(
            TypeError,
            match="medium_physical_identity_invalid",
        ):
            _TensorIdentityMedium().physical_identity()

    def test_physical_identity_rejects_unstable_payload(self) -> None:
        """
        介质物理身份必须跨相邻读取保持确定
        """

        with pytest.raises(
            ValueError,
            match="medium_physical_identity_unstable",
        ):
            _UnstableIdentityMedium().physical_identity()

    def test_cache_identity_alias_is_removed(self) -> None:
        """
        公开介质词汇只保留物理身份，不泄漏缓存治理术语
        """

        assert not hasattr(Vacuum(), "cache_identity")

    def test_public_refractive_index_cannot_be_overridden(self) -> None:
        """
        第三方介质只能提供私有公式，不能绕开 Medium 的统一公共守卫
        """

        with pytest.raises(
            TypeError,
            match="medium_refractive_index_override_forbidden",
        ):

            class _PublicOverrideMedium(Medium):
                def refractive_index(
                    self,
                    wavelengths: torch.Tensor,
                ) -> torch.Tensor:
                    """
                    故意覆盖公共入口以验证类定义期拒绝
                    """

                    return wavelengths

                def _evaluate_refractive_index(
                    self,
                    wavelengths: torch.Tensor,
                ) -> torch.Tensor:
                    return wavelengths

                def _physical_identity(self) -> tuple[object, ...]:
                    return ("public_override",)

    def test_public_physical_identity_cannot_be_overridden(self) -> None:
        """
        第三方介质不能直接替换物理身份公共守卫
        """

        with pytest.raises(
            TypeError,
            match="medium_physical_identity_override_forbidden",
        ):

            class _PublicIdentityOverrideMedium(Medium):
                def physical_identity(self) -> tuple[object, ...]:
                    """
                    故意覆盖公共身份入口以验证类定义期拒绝
                    """

                    return ("public_identity_override",)

                def _evaluate_refractive_index(
                    self,
                    wavelengths: torch.Tensor,
                ) -> torch.Tensor:
                    return wavelengths

                def _physical_identity(self) -> tuple[object, ...]:
                    return ("private_identity",)

    def test_leading_mixin_cannot_replace_refractive_index(self) -> None:
        """
        前置 mixin 不能经 MRO 替换折射率公共守卫
        """

        class _RefractiveIndexMixin:
            def refractive_index(
                self,
                wavelengths: torch.Tensor,
            ) -> torch.Tensor:
                """
                故意由前置 mixin 提供公共公式入口
                """

                return wavelengths

        with pytest.raises(
            TypeError,
            match="medium_refractive_index_override_forbidden",
        ):

            class _MixedRefractiveIndexMedium(
                _RefractiveIndexMixin,
                Medium,
            ):
                def _evaluate_refractive_index(
                    self,
                    wavelengths: torch.Tensor,
                ) -> torch.Tensor:
                    return wavelengths

                def _physical_identity(self) -> tuple[object, ...]:
                    return ("mixed_refractive_index",)

    def test_leading_mixin_cannot_replace_physical_identity(self) -> None:
        """
        前置 mixin 不能经 MRO 替换物理身份公共守卫
        """

        class _PhysicalIdentityMixin:
            def physical_identity(self) -> tuple[object, ...]:
                """
                故意由前置 mixin 提供公共身份入口
                """

                return ("mixed_public_identity",)

        with pytest.raises(
            TypeError,
            match="medium_physical_identity_override_forbidden",
        ):

            class _MixedPhysicalIdentityMedium(
                _PhysicalIdentityMixin,
                Medium,
            ):
                def _evaluate_refractive_index(
                    self,
                    wavelengths: torch.Tensor,
                ) -> torch.Tensor:
                    return wavelengths

                def _physical_identity(self) -> tuple[object, ...]:
                    return ("mixed_physical_identity",)

    def test_leading_mixin_without_public_medium_entries_is_allowed(
        self,
    ) -> None:
        """
        不定义公共介质入口的普通前置 mixin 仍可参与第三方实现
        """

        class _LabelMixin:
            label = "ordinary_mixin"

        class _MixedMedium(_LabelMixin, Medium):
            def _evaluate_refractive_index(
                self,
                wavelengths: torch.Tensor,
            ) -> torch.Tensor:
                return torch.ones_like(wavelengths)

            def _physical_identity(self) -> tuple[object, ...]:
                return ("mixed_medium", self.label)

        medium = _MixedMedium()
        query = torch.tensor([0.5e-6], dtype=torch.float64)
        assert torch.equal(medium.refractive_index(query), torch.ones_like(query))
        assert medium.physical_identity()[-1] == (
            "mixed_medium",
            "ordinary_mixin",
        )

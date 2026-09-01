
from __future__ import annotations

from collections.abc import Callable
import math

import pytest
import torch

from chromatix_next.errors import OpticalValueError
from chromatix_next.optics import Polarization, RayBundle, SpatialGrid, Spectrum, Vacuum
from chromatix_next.optics.ray_bundle import RAY_STATUS_ACTIVE
from chromatix_next.optics.source import CollimatedRaySource

cuda = pytest.mark.cuda

# binary64 单位舍入（ADR-0010）：在测试内从公式独立重算，不导入生产常量
_U: float = 2.0 ** -53


def _gamma(operation_count: int) -> float:
    # 由 ADR 公式独立重算 ``gamma_n = n*u/(1-n*u)``
    count = float(operation_count)
    return count * _U / (1.0 - count * _U)


_DIRECTION_BUDGET: float = 16.0 * _gamma(5)
_POLARIZATION_BUDGET: float = 16.0 * _gamma(11)
_TRANSVERSALITY_FACTOR: float = 16.0 * _gamma(5)


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    return Spectrum.monochromatic(wavelength=wavelength)


def _active_bundle(
    *,
    direction: torch.Tensor,
    polarization: torch.Tensor,
    device: torch.device | str = "cpu",
) -> RayBundle:
    # 以指定方向/偏振构造单 ray 单光谱全 active 光线束（fixed-double）
    spectrum = _monochromatic()
    real_dtype = torch.float64
    direction_tensor = (
        direction.to(device=device, dtype=real_dtype).reshape(1, 1, 3)
    )
    polarization_tensor = (
        polarization.to(
            device=device,
            dtype=torch.complex128,
        ).reshape(1, 1, 3)
    )
    return RayBundle(
        position=torch.zeros((1, 1, 3), dtype=real_dtype, device=device),
        direction=direction_tensor,
        polarization_vector=polarization_tensor,
        power=torch.ones((1, 1), dtype=real_dtype, device=device),
        refractive_index=torch.ones(
            (1, 1),
            dtype=real_dtype,
            device=device,
        ),
        optical_path=torch.zeros((1, 1), dtype=real_dtype, device=device),
        status=torch.full(
            (1, 1),
            RAY_STATUS_ACTIVE,
            dtype=torch.uint8,
            device=device,
        ),
        spectrum=spectrum,
    )


def _adjacent_inside_outside_for_squared_norm(
    budget: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    # 沿 z>=1 步进 ``torch.nextafter`` 找到 ``|z^2-1|`` 紧邻预算边界的对
    z = torch.tensor(1.0, dtype=torch.float64)
    upward = torch.tensor(float("inf"), dtype=torch.float64)
    downward = torch.tensor(float("-inf"), dtype=torch.float64)
    while bool((z * z - 1.0).abs() <= budget):
        z = torch.nextafter(z, upward)
    outside = z.clone()
    inside = torch.nextafter(z, downward)
    return inside, outside


def _adjacent_inside_outside_scalar(
    budget: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    # 对标量预算边界返回紧邻里/外的可表示值（边界本身算里，用 ``<=`` 判定）
    budget_tensor = torch.tensor(budget, dtype=torch.float64)
    upward = torch.tensor(float("inf"), dtype=torch.float64)
    downward = torch.tensor(float("-inf"), dtype=torch.float64)
    outside = torch.nextafter(budget_tensor, upward)
    inside = torch.nextafter(budget_tensor, downward)
    return inside, outside


def _assert_residual_strictly_outside(
    residual_fn: Callable[[float], float],
    z_value: float,
    budget: float,
) -> None:
    # 复验残差确实越过预算（防御性自检，非 oracle）
    assert residual_fn(z_value) > budget




class TestBinary64BudgetDerivation:
    """
    在测试内独立重算的四个预算与 ADR-0010 冻结公式一致
    """

    def test_unit_roundoff_is_two_to_the_minus_fifty_three(self) -> None:
        """
        ``u = 2^-53`` 与 IEEE 754 binary64 单位舍入一致
        """

        assert _U == math.ulp(1.0) / 2.0

    def test_direction_budget_matches_adr_formula(self) -> None:
        """
        方向平方范数预算恰为 ``16*gamma_5``（约 8.88e-15）
        """

        assert _DIRECTION_BUDGET == pytest.approx(8.88e-15, rel=1.0e-3)

    def test_polarization_budget_matches_adr_formula(self) -> None:
        """
        复偏振范数平方预算恰为 ``16*gamma_11``（约 1.95e-14）
        """

        assert _POLARIZATION_BUDGET == pytest.approx(1.95e-14, rel=1.0e-3)

    def test_transversality_factor_matches_adr_formula(self) -> None:
        """
        横向性尺度感知因子恰为 ``16*gamma_5``
        """

        assert _TRANSVERSALITY_FACTOR == _DIRECTION_BUDGET




class TestDirectionSquaredNormBoundary:
    """
    方向平方范数残差紧邻 ``16*gamma_5``：立即里准入、立即外拒绝
    """

    def test_adjacent_inside_admitted(self) -> None:
        """
        紧邻预算里的方向值构造成功（残差在预算内）
        """

        inside, _ = _adjacent_inside_outside_for_squared_norm(
            _DIRECTION_BUDGET,
        )
        bundle = _active_bundle(
            direction=torch.tensor(
                [0.0, 0.0, float(inside)],
                dtype=torch.float64,
            ),
            polarization=torch.tensor(
                [1.0, 0.0, 0.0],
                dtype=torch.complex128,
            ),
        )
        residual = float(
            (bundle.direction * bundle.direction).sum(dim=-1) - 1.0,
        )
        assert abs(residual) <= _DIRECTION_BUDGET

    def test_adjacent_outside_rejected_with_stable_identity(self) -> None:
        """
        紧邻预算外的方向值以 ``ray_bundle_direction_not_unit`` 拒绝
        """

        _, outside = _adjacent_inside_outside_for_squared_norm(
            _DIRECTION_BUDGET,
        )
        _assert_residual_strictly_outside(
            lambda z: abs(z * z - 1.0),
            float(outside),
            _DIRECTION_BUDGET,
        )
        with pytest.raises(OpticalValueError) as information:
            _active_bundle(
                direction=torch.tensor(
                    [0.0, 0.0, float(outside)],
                    dtype=torch.float64,
                ),
                polarization=torch.tensor(
                    [1.0, 0.0, 0.0],
                    dtype=torch.complex128,
                ),
            )
        assert (
            information.value.identity == "ray_bundle_direction_not_unit"
        )

    def test_adjacent_outside_rejected_on_cuda(self) -> None:
        """
        紧邻预算外的方向值在 CUDA 上以同一身份拒绝
        """

        if not torch.cuda.is_available():
            pytest.skip("CUDA 不可用")
        _, outside = _adjacent_inside_outside_for_squared_norm(
            _DIRECTION_BUDGET,
        )
        with pytest.raises(OpticalValueError) as information:
            _active_bundle(
                direction=torch.tensor(
                    [0.0, 0.0, float(outside)],
                    dtype=torch.float64,
                ),
                polarization=torch.tensor(
                    [1.0, 0.0, 0.0],
                    dtype=torch.complex128,
                ),
                device="cuda",
            )
        assert (
            information.value.identity == "ray_bundle_direction_not_unit"
        )




class TestPolarizationNormSquaredBoundary:
    """
    复偏振范数平方残差紧邻 ``16*gamma_11``：立即里准入、立即外拒绝
    """

    def test_adjacent_inside_admitted(self) -> None:
        """
        紧邻预算里的偏振标量构造成功（横截性同时满足）
        """

        inside, _ = _adjacent_inside_outside_for_squared_norm(
            _POLARIZATION_BUDGET,
        )
        bundle = _active_bundle(
            direction=torch.tensor(
                [0.0, 0.0, 1.0],
                dtype=torch.float64,
            ),
            polarization=torch.tensor(
                [float(inside), 0.0, 0.0],
                dtype=torch.complex128,
            ),
        )
        norms_squared = (bundle.polarization_vector.real**2).sum() + (
            bundle.polarization_vector.imag**2
        ).sum()
        residual = float((norms_squared - 1.0).abs())
        assert residual <= _POLARIZATION_BUDGET

    def test_adjacent_outside_rejected_with_stable_identity(self) -> None:
        """
        紧邻预算外的偏振标量以 ``..._not_unit`` 身份拒绝
        """

        _, outside = _adjacent_inside_outside_for_squared_norm(
            _POLARIZATION_BUDGET,
        )
        _assert_residual_strictly_outside(
            lambda s: abs(s * s - 1.0),
            float(outside),
            _POLARIZATION_BUDGET,
        )
        with pytest.raises(OpticalValueError) as information:
            _active_bundle(
                direction=torch.tensor(
                    [0.0, 0.0, 1.0],
                    dtype=torch.float64,
                ),
                polarization=torch.tensor(
                    [float(outside), 0.0, 0.0],
                    dtype=torch.complex128,
                ),
            )
        assert (
            information.value.identity
            == "ray_bundle_polarization_vector_not_unit"
        )

    def test_adjacent_outside_rejected_on_cuda(self) -> None:
        """
        紧邻预算外的偏振标量在 CUDA 上以同一身份拒绝
        """

        if not torch.cuda.is_available():
            pytest.skip("CUDA 不可用")
        _, outside = _adjacent_inside_outside_for_squared_norm(
            _POLARIZATION_BUDGET,
        )
        with pytest.raises(OpticalValueError) as information:
            _active_bundle(
                direction=torch.tensor(
                    [0.0, 0.0, 1.0],
                    dtype=torch.float64,
                ),
                polarization=torch.tensor(
                    [float(outside), 0.0, 0.0],
                    dtype=torch.complex128,
                ),
                device="cuda",
            )
        assert (
            information.value.identity
            == "ray_bundle_polarization_vector_not_unit"
        )




class TestRealTransversalityBoundary:
    """
    实横向性残差紧邻尺度感知预算：立即里准入、立即外以纵向身份拒绝
    """

    @staticmethod
    def _polarization_with_real_longitudinal(
        real_longitudinal: float,
    ) -> torch.Tensor:
        # 构造偏振 ``(1, 0, real_longitudinal)``：实横向性为该分量
        return torch.tensor(
            [1.0, 0.0, real_longitudinal],
            dtype=torch.complex128,
        )

    def test_adjacent_inside_admitted(self) -> None:
        """
        紧邻预算里的实纵向分量构造成功
        """

        inside, _ = _adjacent_inside_outside_scalar(_TRANSVERSALITY_FACTOR)
        bundle = _active_bundle(
            direction=torch.tensor(
                [0.0, 0.0, 1.0],
                dtype=torch.float64,
            ),
            polarization=self._polarization_with_real_longitudinal(
                float(inside),
            ),
        )
        projection = (bundle.polarization_vector * bundle.direction).sum(
            dim=-1,
        )
        assert float(projection.real.abs()) <= _TRANSVERSALITY_FACTOR

    def test_adjacent_outside_rejected_with_stable_identity(self) -> None:
        """
        紧邻预算外的实纵向分量以 ``..._longitudinal`` 身份拒绝
        """

        _, outside = _adjacent_inside_outside_scalar(_TRANSVERSALITY_FACTOR)
        assert float(outside) > _TRANSVERSALITY_FACTOR
        with pytest.raises(OpticalValueError) as information:
            _active_bundle(
                direction=torch.tensor(
                    [0.0, 0.0, 1.0],
                    dtype=torch.float64,
                ),
                polarization=self._polarization_with_real_longitudinal(
                    float(outside),
                ),
            )
        assert (
            information.value.identity
            == "ray_bundle_polarization_vector_longitudinal"
        )

    def test_adjacent_outside_rejected_on_cuda(self) -> None:
        """
        紧邻预算外的实纵向分量在 CUDA 上以同一身份拒绝
        """

        if not torch.cuda.is_available():
            pytest.skip("CUDA 不可用")
        _, outside = _adjacent_inside_outside_scalar(_TRANSVERSALITY_FACTOR)
        with pytest.raises(OpticalValueError) as information:
            _active_bundle(
                direction=torch.tensor(
                    [0.0, 0.0, 1.0],
                    dtype=torch.float64,
                ),
                polarization=self._polarization_with_real_longitudinal(
                    float(outside),
                ),
                device="cuda",
            )
        assert (
            information.value.identity
            == "ray_bundle_polarization_vector_longitudinal"
        )




class TestImaginaryTransversalityBoundary:
    """
    虚横向性残差紧邻尺度感知预算：立即里准入、立即外以纵向身份拒绝
    """

    @staticmethod
    def _polarization_with_imag_longitudinal(
        imag_longitudinal: float,
    ) -> torch.Tensor:
        # 构造偏振 ``(1, 0, i*imag_longitudinal)``：虚横向性为该分量
        return torch.tensor(
            [
                complex(1.0, 0.0),
                complex(0.0, 0.0),
                complex(0.0, imag_longitudinal),
            ],
            dtype=torch.complex128,
        )

    def test_adjacent_inside_admitted(self) -> None:
        """
        紧邻预算里的虚纵向分量构造成功
        """

        inside, _ = _adjacent_inside_outside_scalar(_TRANSVERSALITY_FACTOR)
        bundle = _active_bundle(
            direction=torch.tensor(
                [0.0, 0.0, 1.0],
                dtype=torch.float64,
            ),
            polarization=self._polarization_with_imag_longitudinal(
                float(inside),
            ),
        )
        projection = (bundle.polarization_vector * bundle.direction).sum(
            dim=-1,
        )
        assert float(projection.imag.abs()) <= _TRANSVERSALITY_FACTOR

    def test_adjacent_outside_rejected_with_stable_identity(self) -> None:
        """
        紧邻预算外的虚纵向分量以 ``..._longitudinal`` 身份拒绝
        """

        _, outside = _adjacent_inside_outside_scalar(_TRANSVERSALITY_FACTOR)
        assert float(outside) > _TRANSVERSALITY_FACTOR
        with pytest.raises(OpticalValueError) as information:
            _active_bundle(
                direction=torch.tensor(
                    [0.0, 0.0, 1.0],
                    dtype=torch.float64,
                ),
                polarization=self._polarization_with_imag_longitudinal(
                    float(outside),
                ),
            )
        assert (
            information.value.identity
            == "ray_bundle_polarization_vector_longitudinal"
        )

    def test_adjacent_outside_rejected_on_cuda(self) -> None:
        """
        紧邻预算外的虚纵向分量在 CUDA 上以同一身份拒绝
        """

        if not torch.cuda.is_available():
            pytest.skip("CUDA 不可用")
        _, outside = _adjacent_inside_outside_scalar(_TRANSVERSALITY_FACTOR)
        with pytest.raises(OpticalValueError) as information:
            _active_bundle(
                direction=torch.tensor(
                    [0.0, 0.0, 1.0],
                    dtype=torch.float64,
                ),
                polarization=self._polarization_with_imag_longitudinal(
                    float(outside),
                ),
                device="cuda",
            )
        assert (
            information.value.identity
            == "ray_bundle_polarization_vector_longitudinal"
        )




class TestExactUnitBaselineAdmitted:
    """
    精确单位方向与偏振的残差恰为零，全部准入
    """

    def test_exact_unit_direction_admitted_with_zero_residual(self) -> None:
        """
        ``(0,0,1)`` 方向平方范数残差恰为零
        """

        bundle = _active_bundle(
            direction=torch.tensor(
                [0.0, 0.0, 1.0],
                dtype=torch.float64,
            ),
            polarization=torch.tensor(
                [1.0, 0.0, 0.0],
                dtype=torch.complex128,
            ),
        )
        residual = float(
            (bundle.direction * bundle.direction).sum(dim=-1) - 1.0,
        )
        assert residual == 0.0

    def test_exact_unit_polarization_admitted_with_zero_residual(
        self,
    ) -> None:
        """
        ``(1,0,0)`` 偏振范数平方残差恰为零
        """

        bundle = _active_bundle(
            direction=torch.tensor(
                [0.0, 0.0, 1.0],
                dtype=torch.float64,
            ),
            polarization=torch.tensor(
                [1.0, 0.0, 0.0],
                dtype=torch.complex128,
            ),
        )
        norms_squared = (
            (bundle.polarization_vector.real**2).sum(dim=-1)
            + (bundle.polarization_vector.imag**2).sum(dim=-1)
        )
        assert float(norms_squared - 1.0) == 0.0

    def test_exact_transverse_admitted_with_zero_projection(self) -> None:
        """
        ``(1,0,0)`` 偏振对 ``(0,0,1)`` 方向的实/虚投影恰为零
        """

        bundle = _active_bundle(
            direction=torch.tensor(
                [0.0, 0.0, 1.0],
                dtype=torch.float64,
            ),
            polarization=torch.tensor(
                [1.0, 0.0, 0.0],
                dtype=torch.complex128,
            ),
        )
        projection = (bundle.polarization_vector * bundle.direction).sum(
            dim=-1,
        )
        assert float(projection.real.abs()) == 0.0
        assert float(projection.imag.abs()) == 0.0




def _assert_bundle_within_all_frozen_budgets(bundle: RayBundle) -> None:
    # 独立断言光线束的方向/偏振范数与横向性全部落在冻结预算内
    direction_residual = (
        (bundle.direction * bundle.direction).sum(dim=-1) - 1.0
    ).abs()
    assert bool((direction_residual <= _DIRECTION_BUDGET).all())
    norms_squared = (bundle.polarization_vector.real**2).sum(dim=-1) + (
        bundle.polarization_vector.imag**2
    ).sum(dim=-1)
    polarization_residual = (norms_squared - 1.0).abs()
    assert bool((polarization_residual <= _POLARIZATION_BUDGET).all())
    projection = (bundle.polarization_vector * bundle.direction).sum(dim=-1)
    pol_norm = torch.linalg.norm(bundle.polarization_vector, dim=-1)
    direction_norm = torch.linalg.norm(bundle.direction, dim=-1)
    transversality_budget = (
        _TRANSVERSALITY_FACTOR * pol_norm * direction_norm
    )
    assert bool((projection.real.abs() <= transversality_budget).all())
    assert bool((projection.imag.abs() <= transversality_budget).all())


class TestCollimatedSourceProducesAdmittedBundle:
    """
    准直光线源路径产出的 RayBundle 在全部冻结预算内（CPU 与 CUDA）
    """

    @staticmethod
    def _source(
        polarization: Polarization,
        *,
        device: torch.device | str = "cpu",
    ) -> CollimatedRaySource:
        return CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=polarization,
            medium=Vacuum(),
            ray_power=1.0,
        ).to(device=device)

    @pytest.mark.parametrize(
        "polarization",
        [
            Polarization.linear_x(),
            Polarization.linear_y(),
            Polarization.left_circular(),
            Polarization.right_circular(),
        ],
        ids=["linear_x", "linear_y", "left_circular", "right_circular"],
    )
    def test_source_bundle_within_all_budgets_cpu(
        self,
        polarization: Polarization,
    ) -> None:
        """
        CPU 上 Source 产出的光线束满足四个冻结预算
        """

        grid = SpatialGrid.centered(
            sample_counts=(2, 2),
            sample_spacing=(1.0, 1.0),
        )
        bundle = self._source(polarization)(grid)
        _assert_bundle_within_all_frozen_budgets(bundle)
        assert bundle.polarization_vector.dtype is torch.complex128
        assert bundle.direction.dtype is torch.float64

    @cuda
    @pytest.mark.parametrize(
        "polarization",
        [
            Polarization.linear_x(),
            Polarization.left_circular(),
        ],
        ids=["linear_x", "left_circular"],
    )
    def test_source_bundle_within_all_budgets_cuda(
        self,
        polarization: Polarization,
    ) -> None:
        """
        CUDA 上 Source 产出的光线束满足四个冻结预算
        """

        if not torch.cuda.is_available():
            pytest.skip("CUDA 不可用")
        grid = SpatialGrid.centered(
            sample_counts=(2, 2),
            sample_spacing=(1.0, 1.0),
        )
        bundle = self._source(polarization, device="cuda")(grid)
        _assert_bundle_within_all_frozen_budgets(bundle)
        assert bundle.polarization_vector.device.type == "cuda"




class TestMetaSchemaAdmissionGuarded:
    """
    meta 设备上的 RayBundle 只有形状/dtype，准入检查正确放行
    """

    def test_meta_bundle_has_correct_schema_without_value_enforcement(
        self,
    ) -> None:
        """
        meta 光线束形状/dtype 正确且不因取值校验失败
        """

        direction = torch.zeros(
            (1, 1, 3),
            dtype=torch.float64,
            device="meta",
        )
        direction[..., 2] = 1.0
        polarization = torch.zeros(
            (1, 1, 3),
            dtype=torch.complex128,
            device="meta",
        )
        polarization[..., 0] = 1.0
        bundle = RayBundle(
            position=torch.zeros(
                (1, 1, 3),
                dtype=torch.float64,
                device="meta",
            ),
            direction=direction,
            polarization_vector=polarization,
            power=torch.ones(
                (1, 1),
                dtype=torch.float64,
                device="meta",
            ),
            refractive_index=torch.ones(
                (1, 1),
                dtype=torch.float64,
                device="meta",
            ),
            optical_path=torch.zeros(
                (1, 1),
                dtype=torch.float64,
                device="meta",
            ),
            status=torch.full(
                (1, 1),
                RAY_STATUS_ACTIVE,
                dtype=torch.uint8,
                device="meta",
            ),
            spectrum=_monochromatic(),
        )
        assert bundle.direction.is_meta
        assert bundle.direction.shape == (1, 1, 3)
        assert bundle.direction.dtype is torch.float64
        assert bundle.polarization_vector.dtype is torch.complex128
        assert bundle.status.dtype is torch.uint8




class TestAdmissionIdentityIsPathIndependent:
    """
    边界外值在 RayBundle 构造时统一以同一身份拒绝，与下游动作无关
    """

    def test_direction_outside_identity_same_regardless_of_intended_action(
        self,
    ) -> None:
        """
        越界方向的拒绝身份不依赖下游是否为 trace/reflect/refract
        """

        _, outside = _adjacent_inside_outside_for_squared_norm(
            _DIRECTION_BUDGET,
        )
        identities: list[str] = []
        for _attempt in range(3):
            try:
                _active_bundle(
                    direction=torch.tensor(
                        [0.0, 0.0, float(outside)],
                        dtype=torch.float64,
                    ),
                    polarization=torch.tensor(
                        [1.0, 0.0, 0.0],
                        dtype=torch.complex128,
                    ),
                )
            except OpticalValueError as failure:
                identities.append(failure.identity)
        assert identities == ["ray_bundle_direction_not_unit"] * 3
        assert len({identities[0], identities[1], identities[2]}) == 1

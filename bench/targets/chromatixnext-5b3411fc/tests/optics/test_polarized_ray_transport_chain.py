
from __future__ import annotations

import math

import pytest
import torch

from chromatix_next.optics import ConstantMedium, Spectrum, Vacuum
from chromatix_next.optics.element import reflect_at, refract_at, retarder_at
from chromatix_next.optics.propagation import trace_to
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)
from chromatix_next.optics.surface import Plane

cuda = pytest.mark.cuda

_U: float = 2.0 ** -53
_GAMMA_5: float = 5.0 * _U / (1.0 - 5.0 * _U)
_GAMMA_11: float = 11.0 * _U / (1.0 - 11.0 * _U)
_DIRECTION_BUDGET: float = 16.0 * _GAMMA_5
_POLARIZATION_BUDGET: float = 16.0 * _GAMMA_11
_TRANSVERSALITY_FACTOR: float = 16.0 * _GAMMA_5


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    return Spectrum.monochromatic(wavelength=wavelength)


def _active_bundle(
    *,
    direction: torch.Tensor,
    polarization: torch.Tensor,
    positions: torch.Tensor | None = None,
    refractive_index_value: float = 1.0,
    spectrum: Spectrum | None = None,
) -> RayBundle:
    # 以指定方向/偏振构造单 ray 单光谱全 active 光线束（fixed-double）
    if spectrum is None:
        spectrum = _monochromatic()
    if positions is None:
        positions_tensor = torch.zeros((1, 3), dtype=torch.float64)
        positions_tensor[..., 2] = -1.0e-6
    else:
        positions_tensor = positions.to(dtype=torch.float64)
    ray_count = positions_tensor.shape[-2]
    spectral_count = spectrum.count
    direction_broadcast = (
        direction.to(dtype=torch.float64).reshape(1, 1, 3).expand(
            spectral_count,
            ray_count,
            3,
        )
    )
    position_broadcast = positions_tensor.reshape(1, ray_count, 3).expand(
        spectral_count,
        ray_count,
        3,
    )
    polarization_broadcast = (
        polarization.to(dtype=torch.complex128).reshape(1, 1, 3).expand(
            spectral_count,
            ray_count,
            3,
        )
    )
    wavelengths = torch.tensor(spectrum.wavelengths, dtype=torch.float64)
    indices = torch.full(
        (spectral_count,),
        refractive_index_value,
        dtype=torch.float64,
    )
    return RayBundle(
        position=position_broadcast,
        direction=direction_broadcast,
        polarization_vector=polarization_broadcast,
        power=torch.ones(
            (spectral_count, ray_count),
            dtype=torch.float64,
        ),
        refractive_index=indices.view(spectral_count, 1).expand(
            spectral_count,
            ray_count,
        ),
        optical_path=torch.zeros(
            (spectral_count, ray_count),
            dtype=torch.float64,
        ),
        status=torch.full(
            (spectral_count, ray_count),
            RAY_STATUS_ACTIVE,
            dtype=torch.uint8,
        ),
        spectrum=spectrum,
    )


def _assert_within_all_frozen_budgets(bundle: RayBundle) -> None:
    # 独立断言光线束在全部四个冻结准入预算内
    direction_residual = (
        (bundle.direction * bundle.direction).sum(dim=-1) - 1.0
    ).abs()
    assert bool((direction_residual <= _DIRECTION_BUDGET).all()), (
        "方向平方范数残差越出冻结预算"
    )
    norms_squared = (bundle.polarization_vector.real**2).sum(dim=-1) + (
        bundle.polarization_vector.imag**2
    ).sum(dim=-1)
    polarization_residual = (norms_squared - 1.0).abs()
    assert bool(
        (polarization_residual <= _POLARIZATION_BUDGET).all()
    ), "偏振范数平方残差越出冻结预算"
    projection = (
        bundle.polarization_vector * bundle.direction
    ).sum(dim=-1)
    pol_norm = torch.linalg.norm(bundle.polarization_vector, dim=-1)
    direction_norm = torch.linalg.norm(bundle.direction, dim=-1)
    budget = _TRANSVERSALITY_FACTOR * pol_norm * direction_norm
    assert bool(
        (projection.real.abs() <= budget).all()
    ), "实横向性残差越出冻结预算"
    assert bool(
        (projection.imag.abs() <= budget).all()
    ), "虚横向性残差越出冻结预算"




class TestRefractCriticalAngle:
    """
    折射临界角行为良定义且两侧分类一致
    """

    @staticmethod
    def _critical_direction(offset_ulp: int) -> torch.Tensor:
        # 构造玻璃到空气临界角附近的方向（offset_ulp > 0 偏超临界）
        source_index = 1.5
        destination_index = 1.0
        ratio = destination_index / source_index
        critical_angle = math.asin(ratio)
        sin_critical = torch.tensor(
            math.sin(critical_angle),
            dtype=torch.float64,
        )
        if offset_ulp > 0:
            upward = torch.tensor(float("inf"), dtype=torch.float64)
            target_sin = sin_critical.clone()
            for _ in range(offset_ulp):
                target_sin = torch.nextafter(target_sin, upward)
        else:
            downward = torch.tensor(float("-inf"), dtype=torch.float64)
            target_sin = sin_critical.clone()
            for _ in range(-offset_ulp):
                target_sin = torch.nextafter(target_sin, downward)
        sin_value = float(target_sin)
        cos_value = math.sqrt(max(1.0 - sin_value * sin_value, 0.0))
        return torch.tensor(
            [sin_value, 0.0, cos_value],
            dtype=torch.float64,
        )



class TestRefractNoninteractingLanes:
    """
    折射的未中、渐晕与已终态通道偏振精确保留
    """



class TestRepeatedActionChainNoAccumulation:
    """
    长动作链在每个公共边界不累积超出预算的漂移
    """

    def test_six_step_chain_remains_within_budget_at_every_boundary(
        self,
    ) -> None:
        """
        六步链每步输出仍满足全部冻结准入预算
        """

        direction = torch.tensor(
            [0.3, 0.0, math.sqrt(1.0 - 0.09)],
            dtype=torch.float64,
        )
        positions = torch.tensor(
            [[0.0, 0.0, -1.0e-6]],
            dtype=torch.float64,
        )
        bundle = _active_bundle(
            direction=direction,
            polarization=torch.tensor(
                [0.0, 1.0, 0.0],
                dtype=torch.complex128,
            ),
            positions=positions,
            refractive_index_value=1.0,
        )
        plane = Plane(
            origin=(0.0, 0.0, 0.0),
            clear_aperture_radius=10.0,
        )
        # 步 1：追迹到 z=0 面
        step1 = trace_to(bundle, surface=plane)
        _assert_within_all_frozen_budgets(step1)
        # 步 2：延迟器（非零延迟变换后仍准入）
        step2 = retarder_at(
            step1,
            surface=plane,
            retardance_cycles=0.18,
            retarded_eigenstate_azimuth_radians=math.radians(22.0),
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        _assert_within_all_frozen_budgets(step2)
        # 步 3：反射（反射映射传送后仍准入）
        step3 = reflect_at(step2, surface=plane)
        _assert_within_all_frozen_budgets(step3)
        # 步 4：追迹反射后的光线到下一个面
        downstream = Plane(
            origin=(0.0, 0.0, -2.0),
            clear_aperture_radius=10.0,
        )
        step4 = trace_to(step3, surface=downstream)
        _assert_within_all_frozen_budgets(step4)
        # 步 5：折射进入玻璃（最小旋转传送后仍准入）
        glass = ConstantMedium(index=1.3)
        step5 = refract_at(
            step4,
            surface=downstream,
            destination_medium=glass,
        )
        active_mask = step5.status == RAY_STATUS_ACTIVE
        if bool(active_mask.any()):
            _assert_within_all_frozen_budgets(step5)
        # 步 6：延迟器再一次延迟
        step6 = retarder_at(
            step5,
            surface=downstream,
            retardance_cycles=0.31,
            retarded_eigenstate_azimuth_radians=math.radians(15.0),
            retarded_eigenstate_ellipticity_radians=math.radians(3.0),
        )
        _assert_within_all_frozen_budgets(step6)

    def test_repeated_zero_retardance_chain_preserves_exactly(self) -> None:
        """
        连续零延迟与追迹五步链偏振精确保留
        """

        direction = torch.tensor(
            [0.0, 0.0, 1.0],
            dtype=torch.float64,
        )
        bundle = _active_bundle(
            direction=direction,
            polarization=torch.tensor(
                [1.0, 0.0, 0.0],
                dtype=torch.complex128,
            ),
        )
        plane = Plane(origin=(0.0, 0.0, 0.0))
        current = bundle
        for _step in range(5):
            current = retarder_at(
                current,
                surface=plane,
                retardance_cycles=0.0,
                retarded_eigenstate_azimuth_radians=math.radians(30.0),
                retarded_eigenstate_ellipticity_radians=math.radians(10.0),
            )
            current = trace_to(current, surface=plane)
        assert torch.equal(
            current.polarization_vector,
            bundle.polarization_vector,
        )

    @cuda
    def test_chain_within_budgets_on_cuda(self) -> None:
        """
        三步链在真实 CUDA 上每步仍准入
        """

        if not torch.cuda.is_available():
            pytest.skip("CUDA 不可用")
        direction = torch.tensor(
            [0.3, 0.0, math.sqrt(1.0 - 0.09)],
            dtype=torch.float64,
            device="cuda",
        )
        polarization = torch.tensor(
            [0.0, 1.0, 0.0],
            dtype=torch.complex128,
            device="cuda",
        )
        position = torch.zeros(
            (1, 1, 3),
            dtype=torch.float64,
            device="cuda",
        )
        position[..., 2] = -1.0e-6
        bundle = RayBundle(
            position=position,
            direction=direction.reshape(1, 1, 3),
            polarization_vector=polarization.reshape(1, 1, 3),
            power=torch.ones(
                (1, 1),
                dtype=torch.float64,
                device="cuda",
            ),
            refractive_index=torch.ones(
                (1, 1),
                dtype=torch.float64,
                device="cuda",
            ),
            optical_path=torch.zeros(
                (1, 1),
                dtype=torch.float64,
                device="cuda",
            ),
            status=torch.full(
                (1, 1),
                RAY_STATUS_ACTIVE,
                dtype=torch.uint8,
                device="cuda",
            ),
            spectrum=_monochromatic(),
        )
        cuda_plane = Plane(
            origin=(0.0, 0.0, 0.0),
            clear_aperture_radius=10.0,
        ).to(device="cuda")
        step1 = trace_to(bundle, surface=cuda_plane)
        step2 = retarder_at(
            step1,
            surface=cuda_plane,
            retardance_cycles=0.18,
            retarded_eigenstate_azimuth_radians=math.radians(22.0),
            retarded_eigenstate_ellipticity_radians=0.0,
        )
        step3 = reflect_at(step2, surface=cuda_plane)
        _assert_within_all_frozen_budgets(step3)
        assert step3.polarization_vector.device.type == "cuda"

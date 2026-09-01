
from __future__ import annotations

import pytest
import torch

from chromatix_next.optics import ConstantMedium, RayBundle, Spectrum, Vacuum
from chromatix_next.optics.element import refract_at
from chromatix_next.optics.propagation import trace_to
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
    RAY_STATUS_VIGNETTED,
)
from chromatix_next.optics.surface import Plane, Sphere
from tests.optics._valid_ray_inputs import _transverse_polarization_for_direction


def _monochromatic(wavelength: float = 5.0e-7) -> Spectrum:
    # 单色光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _bundle_with_per_ray_index(
    *,
    positions: torch.Tensor,
    directions: torch.Tensor,
    refractive_index: torch.Tensor,
    spectrum: Spectrum,
    real_dtype: torch.dtype = torch.float64,
    status: torch.Tensor | None = None,
) -> RayBundle:
    scalar_shape = positions.shape[:-1]
    power = torch.ones(scalar_shape, dtype=real_dtype)
    optical_path = torch.zeros(scalar_shape, dtype=torch.float64)
    if status is None:
        status = torch.full(
            scalar_shape,
            RAY_STATUS_ACTIVE,
            dtype=torch.uint8,
        )
    return RayBundle(
        position=positions.to(dtype=real_dtype),
        direction=directions.to(dtype=real_dtype),
        polarization_vector=_transverse_polarization_for_direction(
            directions.to(dtype=real_dtype),
        ),
        power=power,
        refractive_index=refractive_index.to(dtype=real_dtype),
        optical_path=optical_path,
        status=status,
        spectrum=spectrum,
    )


class TestMixedStatusRefractiveIndexRetention:
    """
    折射后 mixed-status bundle 的逐 ray 折射率：只有透射 ray 切目标介质
    """

    def test_four_states_retain_or_switch_refractive_index_correctly(self) -> None:
        """
        同一 bundle 内 active/missed/vignetted/TIR 四态：透射 ray 切目标，其余保留入射
        """

        radius = 5.0e-6
        aperture = 4.5e-6
        spectrum = _monochromatic()
        positions = torch.zeros((4, 3), dtype=torch.float64).unsqueeze(0)
        positions[0, 0] = torch.tensor([0.0, 0.0, -3.0e-6])
        positions[0, 1] = torch.tensor([8.0e-6, 0.0, -3.0e-6])
        positions[0, 2] = torch.tensor([4.8e-6, 0.0, -3.0e-6])
        positions[0, 3] = torch.tensor([4.0e-6, 0.0, -3.0e-6])
        directions = torch.zeros((4, 3), dtype=torch.float64).unsqueeze(0)
        directions[..., 2] = 1.0
        # 入射折射率全部为 1.5（光密介质）
        incident_index = torch.full((1, 4), 1.5, dtype=torch.float64)
        bundle = _bundle_with_per_ray_index(
            positions=positions,
            directions=directions,
            refractive_index=incident_index,
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
        # status 四态确认
        assert refracted.status[0, 0] == RAY_STATUS_ACTIVE
        assert refracted.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert refracted.status[0, 2] == RAY_STATUS_VIGNETTED
        assert refracted.status[0, 3] == RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        # 只有 ray 0（成功透射）切到目标介质评估值 1.0；其余三条 ray 精确保留入射 1.5
        assert torch.isclose(
            refracted.refractive_index[0, 0],
            torch.tensor(1.0, dtype=torch.float64),
        )
        assert torch.allclose(
            refracted.refractive_index[0, 1:],
            torch.full((3,), 1.5, dtype=torch.float64),
        )

    def test_already_inactive_ray_keeps_incident_index_through_refraction(self) -> None:
        """
        折射前已 inactive 的 ray：折射率、status、位置、光程均不变（不再参与相遇）
        """

        spectrum = _monochromatic()
        positions = torch.zeros((1, 2, 3), dtype=torch.float64)
        positions[0, 1, 0] = 5.0e-6  # 第二 ray 已偏离
        directions = torch.zeros((1, 2, 3), dtype=torch.float64)
        directions[..., 2] = 1.0
        # 入射折射率：ray 0 = 1.0（真空），ray 1 = 1.7（已终止于某光密介质）
        incident_index = torch.tensor([[1.0, 1.7]], dtype=torch.float64)
        status = torch.full((1, 2), RAY_STATUS_ACTIVE, dtype=torch.uint8)
        status[0, 1] = RAY_STATUS_VIGNETTED  # ray 1 已 inactive
        bundle = _bundle_with_per_ray_index(
            positions=positions,
            directions=directions,
            refractive_index=incident_index,
            spectrum=spectrum,
            status=status,
        )
        sphere = Sphere(radius_of_curvature=5.0e-6)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        # inactive ray 1：折射率、status 不变
        assert refracted.status[0, 1] == RAY_STATUS_VIGNETTED
        assert torch.isclose(
            refracted.refractive_index[0, 1],
            torch.tensor(1.7, dtype=torch.float64),
        )


class TestPerRayOpticalPath:
    """
    trace_to 用逐 ray 入射折射率累加 OP：同 bundle 不同 ray 各取自己的 n
    """

    def test_per_ray_index_produces_per_ray_optical_path(self) -> None:
        """
        同 bundle 中 ray 0 n=1.0、ray 1 n=1.5：同距离下 OP 分别为 1.0×d 与 1.5×d
        """

        spectrum = _monochromatic()
        # 两条 ray 都沿 +z 走 2.0e-6 到达 plane
        axial_distance = 2.0e-6
        positions = torch.zeros((2, 3), dtype=torch.float64).unsqueeze(0)
        directions = torch.zeros((2, 3), dtype=torch.float64).unsqueeze(0)
        directions[..., 2] = 1.0
        # 逐 ray 入射折射率：ray 0 = 1.0（真空），ray 1 = 1.5（玻璃）
        incident_index = torch.tensor([[1.0, 1.5]], dtype=torch.float64)
        bundle = _bundle_with_per_ray_index(
            positions=positions,
            directions=directions,
            refractive_index=incident_index,
            spectrum=spectrum,
        )
        plane = Plane(origin=(0.0, 0.0, axial_distance))
        advanced = trace_to(bundle, surface=plane)
        assert torch.isclose(
            advanced.optical_path[0, 0],
            torch.tensor(1.0 * axial_distance, dtype=torch.float64),
            atol=1.0e-18,
        )
        assert torch.isclose(
            advanced.optical_path[0, 1],
            torch.tensor(1.5 * axial_distance, dtype=torch.float64),
            atol=1.0e-18,
        )

    def test_multi_wavelength_index_spans_spectrum_axis(self) -> None:
        """
        多波长：每个波长层的折射率沿 spectrum 轴独立取值，OP 按各自 n × 距离累加
        """

        # 多波长光谱：两个波长。手动构造每条 ray 在两个波长层各取不同折射率
        spectrum = Spectrum(
            wavelengths=(4.0e-7, 6.0e-7),
            weights=(0.5, 0.5),
        )
        axial_distance = 1.5e-6
        # shape (批量=1, 光谱=2, 光线=1, xyz=3)：沿 +z 单条光线
        positions = torch.zeros((1, 2, 1, 3), dtype=torch.float64)
        directions = torch.zeros((1, 2, 1, 3), dtype=torch.float64)
        directions[..., 2] = 1.0
        # 逐 (batch, spectrum, ray) 折射率：波长 0 为 1.0，波长 1 为 1.5——模拟色散
        incident_index = torch.tensor([[[1.0], [1.5]]], dtype=torch.float64)
        bundle = _bundle_with_per_ray_index(
            positions=positions,
            directions=directions,
            refractive_index=incident_index,
            spectrum=spectrum,
        )
        plane = Plane(origin=(0.0, 0.0, axial_distance))
        advanced = trace_to(bundle, surface=plane)
        # 波长层 0 (n=1.0)：OP = 1.0 × d；波长层 1 (n=1.5)：OP = 1.5 × d
        assert torch.isclose(
            advanced.optical_path[0, 0, 0],
            torch.tensor(1.0 * axial_distance, dtype=torch.float64),
            atol=1.0e-18,
        )
        assert torch.isclose(
            advanced.optical_path[0, 1, 0],
            torch.tensor(1.5 * axial_distance, dtype=torch.float64),
            atol=1.0e-18,
        )


class TestPerRayRefractiveIndexGradient:
    """
    逐 ray 折射率是 OP 路径上的可微节点：autograd 与解析导数（dOP/dn = distance）一致
    """

    def test_refractive_index_gradient_matches_distance(self) -> None:
        """
        OP = n × 距离（trace_to），故 dOP/dn = 距离；自动微分与解析一致
        """

        spectrum = _monochromatic()
        axial_distance = 2.5e-6
        positions = torch.zeros((1, 1, 3), dtype=torch.float64)
        directions = torch.zeros((1, 1, 3), dtype=torch.float64)
        directions[..., 2] = 1.0
        # 可训练逐 ray 折射率：起点 1.3
        incident_index = torch.nn.Parameter(
            torch.tensor([[1.3]], dtype=torch.float64),
        )
        bundle = _bundle_with_per_ray_index(
            positions=positions,
            directions=directions,
            refractive_index=incident_index,
            spectrum=spectrum,
        )
        plane = Plane(origin=(0.0, 0.0, axial_distance))
        advanced = trace_to(bundle, surface=plane)
        advanced.optical_path.sum().backward()
        # dOP/dn = 距离；sum 后梯度仍为距离
        assert incident_index.grad is not None
        assert torch.allclose(
            incident_index.grad,
            torch.full_like(incident_index.grad, axial_distance),
            atol=1.0e-18,
        )


class TestChainedRefractionRefractiveIndexHistory:
    """
    refract → trace → refract 链：终止 ray 的入射折射率跨多面精确保留
    """

    def test_missed_ray_keeps_incident_index_across_second_refraction(self) -> None:
        """
        第一次折射中 missed 的 ray 在第二次折射（不同目标介质）中仍保留原入射折射率
        """

        spectrum = _monochromatic()
        # ray 0 沿轴命中两球面；ray 1 偏离两球面（missed 两次）
        positions = torch.zeros((2, 3), dtype=torch.float64).unsqueeze(0)
        positions[0, 1] = torch.tensor([1.0e-3, 0.0, -3.0e-6])  # 远离光轴 ⇒ missed
        directions = torch.zeros((2, 3), dtype=torch.float64).unsqueeze(0)
        directions[..., 2] = 1.0
        # 入射折射率：两条 ray 都从 n=1.4 出发
        incident_index = torch.full((1, 2), 1.4, dtype=torch.float64)
        bundle = _bundle_with_per_ray_index(
            positions=positions,
            directions=directions,
            refractive_index=incident_index,
            spectrum=spectrum,
        )
        first_sphere = Sphere(
            vertex=(0.0, 0.0, 0.0),
            radius_of_curvature=5.0e-6,
        )
        after_first = refract_at(
            bundle,
            surface=first_sphere,
            destination_medium=ConstantMedium(index=1.6),
        )
        # ray 1 第一次就 missed：保留入射 1.4；ray 0 透射：切到 1.6
        assert after_first.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert torch.isclose(
            after_first.refractive_index[0, 0],
            torch.tensor(1.6, dtype=torch.float64),
        )
        assert torch.isclose(
            after_first.refractive_index[0, 1],
            torch.tensor(1.4, dtype=torch.float64),
        )
        # 第二次折射到不同目标介质（1.8）
        second_sphere = Sphere(
            vertex=(0.0, 0.0, 1.0e-6),
            radius_of_curvature=5.0e-6,
        )
        after_second = refract_at(
            after_first,
            surface=second_sphere,
            destination_medium=ConstantMedium(index=1.8),
        )
        # ray 1 仍 missed（已 inactive 不再参与）：折射率继续保留 1.4，绝不被 1.8 污染
        assert after_second.status[0, 1] == RAY_STATUS_SURFACE_MISSED
        assert torch.isclose(
            after_second.refractive_index[0, 1],
            torch.tensor(1.4, dtype=torch.float64),
        )


class TestPerRayRefractiveIndexDtype:
    """
    逐 ray 折射率固定为 float64（与位置/方向/功率同 dtype）
    """

    def test_refractive_index_dtype_is_float64(self) -> None:
        """
        折射后逐 ray 折射率与位置/方向/功率同为 float64
        """

        real_dtype = torch.float64
        spectrum = _monochromatic()
        positions = torch.tensor(
            [[0.0, 0.0, -3.0e-6]],
            dtype=real_dtype,
        ).unsqueeze(0)
        directions = torch.zeros((1, 1, 3), dtype=real_dtype)
        directions[..., 2] = 1.0
        incident_index = torch.full((1, 1), 1.0, dtype=real_dtype)
        bundle = _bundle_with_per_ray_index(
            positions=positions,
            directions=directions,
            refractive_index=incident_index,
            spectrum=spectrum,
            real_dtype=real_dtype,
        )
        sphere = Sphere(radius_of_curvature=5.0e-6)
        refracted = refract_at(
            bundle,
            surface=sphere,
            destination_medium=ConstantMedium(index=1.5),
        )
        assert refracted.refractive_index.dtype is real_dtype
        assert refracted.position.dtype is real_dtype
        assert refracted.power.dtype is real_dtype
        assert refracted.optical_path.dtype is torch.float64
        assert refracted.status.dtype is torch.uint8


def test_per_ray_index_evidence_compiles_with_no_nan() -> None:
    """
    收尾不变量：所有 per-ray 折射率证据路径上的张量处处有限
    """

    spectrum = _monochromatic()
    positions = torch.tensor(
        [[0.0, 0.0, -3.0e-6]],
        dtype=torch.float64,
    ).unsqueeze(0)
    directions = torch.zeros((1, 1, 3), dtype=torch.float64)
    directions[..., 2] = 1.0
    incident_index = torch.full((1, 1), 1.0, dtype=torch.float64)
    bundle = _bundle_with_per_ray_index(
        positions=positions,
        directions=directions,
        refractive_index=incident_index,
        spectrum=spectrum,
    )
    sphere = Sphere(radius_of_curvature=5.0e-6)
    refracted = refract_at(
        bundle,
        surface=sphere,
        destination_medium=ConstantMedium(index=1.5),
    )
    assert torch.isfinite(refracted.refractive_index).all()
    assert (refracted.refractive_index > 0).all()

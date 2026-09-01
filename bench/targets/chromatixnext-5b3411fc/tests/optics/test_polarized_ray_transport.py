
from __future__ import annotations

from collections.abc import Mapping
import math

import pytest
import torch

from chromatix_next.optics import (
    ConstantMedium,
    Polarization,
    RayBundle,
    SpatialGrid,
    Spectrum,
)
from chromatix_next.optics.element import ReflectAt, RefractAt, reflect_at, refract_at
from chromatix_next.optics.propagation import TraceTo, trace_to
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
)
from chromatix_next.optics.source import CollimatedRaySource
from chromatix_next.optics.surface import Plane, Sphere

cuda = pytest.mark.cuda


def _monochromatic(wavelength: float = 2.0e-6) -> Spectrum:
    # 单位权重单波长光谱
    return Spectrum.monochromatic(wavelength=wavelength)


def _grid(counts: tuple[int, int] = (3, 4)) -> SpatialGrid:
    # 中心对齐小型横向网格
    return SpatialGrid.centered(sample_counts=counts, sample_spacing=(1.0, 1.0))


def _workstation_ray_calculation(
    root: torch.nn.Module,
    grid: SpatialGrid,
) -> Mapping[str, RayBundle]:
    # 工作站 calculation：模块级纯函数，把光源输出包成命名 Mapping
    return {"rays": root(grid)}


def _householder_polarization(
    polarization: torch.Tensor,
    unit_normal: torch.Tensor,
) -> torch.Tensor:
    # 独立参考：实 Householder p ↦ p − 2(p·n̂)n̂（n̂ 实，p 复）
    projection = (polarization * unit_normal).sum(dim=-1)
    return polarization - (2.0 * projection).unsqueeze(-1) * unit_normal


def _rodrigues_rotation_matrix(
    incident: torch.Tensor,
    transmitted: torch.Tensor,
) -> torch.Tensor:
    # 独立参考：R = I + K + K²/(1+c)，K 为 d_i × d_t 的反对称矩阵，c = d_i · d_t
    v = torch.linalg.cross(incident, transmitted)
    c = (incident * transmitted).sum(-1)
    zeros = torch.zeros_like(c)
    rows = (
        torch.stack((zeros, -v[..., 2], v[..., 1]), dim=-1),
        torch.stack((v[..., 2], zeros, -v[..., 0]), dim=-1),
        torch.stack((-v[..., 1], v[..., 0], zeros), dim=-1),
    )
    skew = torch.stack(rows, dim=-2)
    skew_sq = torch.einsum("...ij,...jk->...ik", skew, skew)
    batch_shape = skew.shape[:-2]
    identity = torch.eye(3, dtype=skew.dtype, device=skew.device)
    identity = identity.expand(*batch_shape, 3, 3)
    return identity + skew + skew_sq / (1.0 + c).unsqueeze(-1).unsqueeze(-1)


def _bundle_with_polarization(
    polarization: Polarization,
    *,
    direction_axis_y: tuple[float, float, float] = (1.0, 0.0, 0.0),
    direction_axis_x: tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> RayBundle:
    # 以给定偏振与发射姿态构造一个最小光线束
    source = CollimatedRaySource(
        spectrum=_monochromatic(),
        polarization=polarization,
        launch_tangent_x=direction_axis_y,
        launch_tangent_y=direction_axis_x,
        ray_power=1.0,
    )
    return source(_grid(counts=(2, 2)))




class TestCollimatedSourceJonesEmbedding:
    """
    Jones 分量嵌入全局发射面基的证据
    """



class TestTracePolarizationIdentity:
    """
    TraceTo 偏振逐通道原样返回，位置/光程/状态行为不变
    """

class TestReflectPolarizationHouseholder:
    """
    ReflectAt 把同一实 Householder 作用到复偏振，非交互通道精确保留
    """

class TestRefractPolarizationMinimalRotation:
    """
    RefractAt 以唯一最小真旋转搬运偏振，正入射恒等，TIR 与非交互通道保留
    """



class TestPolarizationGradientsAndMeta:
    """
    梯度经源/面参数与偏振传输到达 leaf，meta 推导隔离，工作站枚举偏振契约
    """

    def test_gradient_flows_through_polarization_transport(self) -> None:
        """
        可训练球面曲率法线随交点变化，反射偏振依赖曲率，梯度到达 leaf
        """

        theta = math.radians(25.0)
        bundle = _bundle_with_polarization(
            Polarization.linear_x(),
            direction_axis_y=(math.cos(theta), 0.0, math.sin(theta)),
            direction_axis_x=(0.0, 1.0, 0.0),
        )
        radius = torch.nn.Parameter(torch.tensor(5.0, dtype=torch.float64))
        sphere = Sphere(
            vertex=(0.0, 0.0, 5.0),
            radius_of_curvature=radius,
            clear_aperture_radius=10.0,
        )
        reflected = reflect_at(bundle, surface=sphere)
        reflected.polarization_vector.real.sum().backward()
        assert radius.grad is not None
        assert radius.grad.abs().item() > 0.0

    def test_meta_inference_produces_same_polarization_shape_and_dtype(self) -> None:
        """
        meta 推导与真实运行的偏振形状与 dtype 一致
        """

        from chromatix_next.optics._meta_inference import _meta_inference

        source = CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            ray_power=1.0,
        )
        grid = _grid()
        real_bundle = source(grid)
        with _meta_inference(tuple(source.modules())) as sandbox:
            meta_bundle = sandbox.module(source)(grid)
        assert (
            meta_bundle.polarization_vector.shape
            == real_bundle.polarization_vector.shape
        )
        assert (
            meta_bundle.polarization_vector.dtype
            == real_bundle.polarization_vector.dtype
        )

    def test_workstation_run_enumerates_polarization_vector_contract(self) -> None:
        """
        工作站运行边界产出 complex128 偏振与位置同形
        """

        from chromatix_next import Workstation

        source = CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=Polarization.linear_x(),
            ray_power=torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float64)),
        )
        workstation = Workstation.cpu()
        workstation.host(source)
        outputs, _record = workstation.run(
            _workstation_ray_calculation,
            root=source,
            inputs=lambda device: (_grid().to(device=device, dtype=torch.float64),),
            seed=7,
        )
        bundle = outputs["rays"]
        assert isinstance(bundle, RayBundle)
        assert bundle.polarization_vector.dtype is torch.complex128
        assert bundle.polarization_vector.shape == bundle.position.shape




@cuda
class TestPolarizedRayCudaParity:
    """
    真实 CUDA 与 CPU 在固定 double 下偏振张量数值一致
    """

    @staticmethod
    def _device_bundle(device: torch.device) -> RayBundle:
        # 倾斜姿态构造一个光线束并搬到目标设备
        theta = math.radians(20.0)
        source = CollimatedRaySource(
            spectrum=_monochromatic(),
            polarization=Polarization.left_circular(),
            launch_tangent_x=(math.cos(theta), 0.0, math.sin(theta)),
            launch_tangent_y=(0.0, 1.0, 0.0),
            ray_power=1.0,
        )
        source.to(device=device)
        return source(_grid())

    def test_reflect_polarization_matches_cpu(self) -> None:
        """
        反射偏振在 CPU 与真实 CUDA 上一致（固定 double）
        """

        if not torch.cuda.is_available():
            pytest.skip("需要真实 CUDA 设备")
        cpu_bundle = self._device_bundle(torch.device("cpu"))
        cuda_bundle = self._device_bundle(torch.device("cuda"))
        mirror = Plane(origin=(0.0, 0.0, 5.0))
        cpu_out = reflect_at(cpu_bundle, surface=mirror)
        cuda_out = reflect_at(cuda_bundle, surface=mirror.to(device="cuda"))
        assert torch.allclose(
            cpu_out.polarization_vector,
            cuda_out.polarization_vector.cpu(),
            atol=1.0e-10,
        )

    def test_refract_polarization_matches_cpu(self) -> None:
        """
        折射偏振在 CPU 与真实 CUDA 上一致（固定 double）
        """

        if not torch.cuda.is_available():
            pytest.skip("需要真实 CUDA 设备")
        cpu_bundle = self._device_bundle(torch.device("cpu"))
        cuda_bundle = self._device_bundle(torch.device("cuda"))
        glass = ConstantMedium(index=1.5)
        plane = Plane(origin=(0.0, 0.0, 5.0))
        cpu_out = refract_at(cpu_bundle, surface=plane, destination_medium=glass)
        cuda_out = refract_at(
            cuda_bundle,
            surface=plane.to(device="cuda"),
            destination_medium=glass,
        )
        assert torch.allclose(
            cpu_out.polarization_vector,
            cuda_out.polarization_vector.cpu(),
            atol=1.0e-10,
        )

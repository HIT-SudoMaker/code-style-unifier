from __future__ import annotations

from collections.abc import Callable, Mapping
import math
from typing import cast

import pytest
import torch

from chromatix_next.errors import WorkstationError
from chromatix_next.optics import (
    ConstantMedium,
    Polarization,
    RayBundle,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.element import RefractAt
from chromatix_next.optics.propagation import TraceTo
from chromatix_next.optics.source import CollimatedRaySource
from chromatix_next.optics.surface import Plane, Sphere
from chromatix_next.workstation import NamedOutputs, RunRecord, Workstation


def _spectrum() -> Spectrum:
    # 单色光谱（真空波长 500 nm）
    return Spectrum.monochromatic(wavelength=5.0e-7)

def _centered_grid(
    *,
    sample_counts: tuple[int, int] = (3, 3),
    sample_spacing: tuple[float, float] = (4.0e-5, 4.0e-5),
) -> SpatialGrid:
    # 小高度横向网格，保持光线落在 paraxial 区域；vignetting 证据改用更宽 spacing
    return SpatialGrid.centered(
        sample_counts=sample_counts,
        sample_spacing=sample_spacing,
    )

class _BiconvexLensPrescription(torch.nn.Module):
    spectrum: Spectrum
    glass: ConstantMedium

    def __init__(
        self,
        *,
        index: float = 1.5,
        is_curvature_trainable: bool = True,
    ) -> None:
        """
        构造光源 → 光阑 → 前表面折射 → 后表面折射 → 像平面的顺序处方
        """

        super().__init__()
        spectrum = _spectrum()
        front_radius = (
            torch.nn.Parameter(torch.tensor(0.1, dtype=torch.float64))
            if is_curvature_trainable
            else 0.1
        )
        back_radius = (
            torch.nn.Parameter(torch.tensor(-0.1, dtype=torch.float64))
            if is_curvature_trainable
            else -0.1
        )
        self.spectrum = spectrum
        self.glass = ConstantMedium(index=index)
        self.source = CollimatedRaySource(
            spectrum=spectrum,

            polarization=Polarization.linear_x(),
            medium=Vacuum(),
            launch_origin=(0.0, 0.0, -0.3),
            ray_power=torch.nn.Parameter(
                torch.tensor(1.0, dtype=torch.float64),
            ),
        )
        self.stop = TraceTo(
            surface=Plane(
                origin=(0.0, 0.0, -0.05),
                clear_aperture_radius=2.0e-4,
            ),
        )
        self.front = RefractAt(
            surface=Sphere(
                vertex=(0.0, 0.0, 0.0),
                radius_of_curvature=front_radius,
            ),
            destination_medium=self.glass,
        )
        self.back = RefractAt(
            surface=Sphere(
                vertex=torch.nn.Parameter(
                    torch.tensor(
                        [0.0, 0.0, 0.02],
                        dtype=torch.float64,
                    ),
                ),
                radius_of_curvature=back_radius,
            ),
            destination_medium=Vacuum(),
        )
        self.image = TraceTo(
            surface=Plane(origin=(0.0, 0.0, 0.5)),
        )

    def forward(self, grid: SpatialGrid) -> RayBundle:  # type: ignore[override]
        """
        按作者顺序逐行追迹完整折射处方到像平面
        """

        bundle = self.source(grid)
        bundle = self.stop(bundle)
        bundle = self.front(bundle)
        bundle = self.back(bundle)
        return self.image(bundle)

def _prescription_calculation(
    root: _BiconvexLensPrescription,
    grid: SpatialGrid,
) -> Mapping[str, RayBundle]:
    # 模块级 calculation：把处方输出包成 Named Outputs 的有序映射
    return {"rays": root(grid)}

def _inputs_factory(
    grid: SpatialGrid,
) -> Callable[[torch.device], tuple[object, ...]]:
    # 返回 inputs(device) 工厂；网格按目标设备迁移

    def factory(
        device: torch.device,
    ) -> tuple[object, ...]:
        """
        按目标设备返回可重放输入参数元组
        """

        return (
            grid.to(
                device=device,
                dtype=torch.float64,
            ),
        )

    return factory

def test_run_returns_named_ray_bundle_for_full_prescription() -> None:
    """
    工作站运行完整多面折射处方 ⇒ 命名输出含 RayBundle；dtype/device 固定 float64
    """

    real_dtype = torch.float64
    workstation = Workstation.cpu()
    prescription = _BiconvexLensPrescription()
    workstation.host(prescription)
    grid = _centered_grid()
    outputs, record = workstation.run(
        _prescription_calculation,
        root=prescription,
        inputs=_inputs_factory(grid),
    )
    assert isinstance(outputs, NamedOutputs)
    assert isinstance(record, RunRecord)
    assert tuple(outputs) == ("rays",)
    bundle = outputs["rays"]
    assert isinstance(bundle, RayBundle)
    assert bundle.position.dtype is real_dtype
    assert bundle.direction.dtype is real_dtype
    assert bundle.power.dtype is real_dtype
    assert bundle.optical_path.dtype is torch.float64
    assert bundle.status.dtype is torch.uint8
    assert bundle.position.device == workstation.device

def test_meta_real_schema_agree_for_full_prescription() -> None:
    """
    同一处方跨运行重复执行 ⇒ RayBundle 各字段逐元素一致（meta/real schema 同构）
    """

    workstation = Workstation.cpu()
    prescription = _BiconvexLensPrescription()
    workstation.host(prescription)
    grid = _centered_grid()
    outputs_first, _ = workstation.run(
        _prescription_calculation,
        root=prescription,
        inputs=_inputs_factory(grid),
    )
    outputs_second, _ = workstation.run(
        _prescription_calculation,
        root=prescription,
        inputs=_inputs_factory(grid),
    )
    bundle_first = outputs_first["rays"]
    bundle_second = outputs_second["rays"]
    assert isinstance(bundle_first, RayBundle)
    assert isinstance(bundle_second, RayBundle)
    for first, second in (
        (bundle_first.position, bundle_second.position),
        (bundle_first.direction, bundle_second.direction),
        (bundle_first.power, bundle_second.power),
        (bundle_first.refractive_index, bundle_second.refractive_index),
        (bundle_first.optical_path, bundle_second.optical_path),
        (bundle_first.status, bundle_second.status),
    ):
        assert torch.equal(first, second)

class TestEndToEndGradient:
    """
    端到端 gradient 经平滑 active path 到达 leaf Parameters，与中心差分一致
    """

    def _loss(
        self,
        prescription: _BiconvexLensPrescription,
        grid: SpatialGrid,
    ) -> torch.Tensor:
        # 像方横向位置的平方和作为可微标量目标
        bundle = prescription(grid)
        return (bundle.position[..., :2] ** 2).sum()


    def test_gradient_reaches_curvature_and_spacing_leaves(
        self,
    ) -> None:
        """
        几何 loss 对前后球面曲率半径与第二面轴向间距的自动梯度非空
        """

        dtype = torch.float64
        prescription = _BiconvexLensPrescription()
        grid = _centered_grid().to(device=torch.device("cpu"), dtype=dtype)
        loss = self._loss(prescription, grid)
        loss.backward()
        front_surface = cast(Sphere, prescription.front.surface)
        back_surface = cast(Sphere, prescription.back.surface)
        front_radius = front_surface.radius_of_curvature
        back_radius = back_surface.radius_of_curvature
        back_origin = back_surface.vertex
        assert front_radius.grad is not None
        assert back_radius.grad is not None
        assert back_origin.grad is not None
        for grad in (front_radius.grad, back_radius.grad, back_origin.grad):
            assert isinstance(grad, torch.Tensor)
            assert bool(torch.isfinite(grad).all())


    @pytest.mark.parametrize(
        "leaf_name",
        ["front_radius", "back_radius", "back_spacing"],
    )
    def test_autograd_matches_central_finite_difference(
        self,
        leaf_name: str,
    ) -> None:
        """
        平滑 active path 上：autograd 与中心差分在 float64 下一致
        """

        dtype = torch.float64
        step = 1.0e-6
        prescription = _BiconvexLensPrescription()
        grid = _centered_grid().to(device=torch.device("cpu"), dtype=dtype)

        def geometry_loss() -> torch.Tensor:
            """
            每次重新前向以避免 autograd 图被 ``torch.no_grad`` 扰动后污染
            """
            return self._loss(prescription, grid)

        if leaf_name == "back_spacing":
            leaf = cast(
                torch.Tensor,
                cast(Sphere, prescription.back.surface).vertex,
            )
            analytic = torch.autograd.grad(
                geometry_loss(),
                leaf,
                retain_graph=False,
            )[0].detach()
            analytic_value = float(analytic[2].item())
            with torch.no_grad():
                original = leaf.detach().clone()
                leaf[2] = original[2] + step
                loss_plus = geometry_loss().detach()
                leaf[2] = original[2] - step
                loss_minus = geometry_loss().detach()
                leaf[2] = original[2]
        else:
            leaf = cast(
                torch.Tensor,
                {
                    "front_radius": (
                        cast(Sphere, prescription.front.surface).radius_of_curvature
                    ),
                    "back_radius": (
                        cast(Sphere, prescription.back.surface).radius_of_curvature
                    ),
                }[leaf_name],
            )
            analytic = torch.autograd.grad(
                geometry_loss(),
                leaf,
                retain_graph=False,
            )[0].detach()
            analytic_value = float(analytic.item())
            with torch.no_grad():
                original = leaf.detach().clone()
                leaf.copy_(original + step)
                loss_plus = geometry_loss().detach()
                leaf.copy_(original - step)
                loss_minus = geometry_loss().detach()
                leaf.copy_(original)
        numeric = (loss_plus - loss_minus) / (2.0 * step)
        assert math.isclose(
            analytic_value,
            float(numeric.item()),
            rel_tol=1.0e-5,
            abs_tol=1.0e-8,
        )

def test_prescription_runs_on_cuda_when_available() -> None:
    """
    双精度在可用 CUDA 上的端到端资格契约

    无逐光线 Python 循环、无陈旧缓存
    """

    if not torch.cuda.is_available():
        pytest.skip("CUDA 不可用，跳过 native device 资格")
    workstation = Workstation.cuda(0)
    prescription = _BiconvexLensPrescription()
    workstation.host(prescription)
    grid = _centered_grid()
    outputs, _ = workstation.run(
        _prescription_calculation,
        root=prescription,
        inputs=_inputs_factory(grid),
    )
    bundle = outputs["rays"]
    assert isinstance(bundle, RayBundle)
    assert bundle.position.device.type == "cuda"
    assert bundle.position.dtype is torch.float64
    assert bundle.optical_path.dtype is torch.float64

def test_module_root_rejects_non_component_child() -> None:
    """
    透明组合根的直属子模块若非合法光学元件 ⇒ WorkstationError（架构守护）
    """

    class _ForeignLeaf(torch.nn.Module):
        @property
        def role(self) -> str:  # type: ignore[override]
            """
            声明角色字面量而 forward 签名不匹配任何已知入参形状
            """

            return "element"

        def forward(  # type: ignore[override]
            self,
            unrelated: int,
        ) -> int:
            """
            非物理入参形状被角色契约拒绝
            """

            return unrelated

    class _BadRoot(torch.nn.Module):
        def __init__(self) -> None:
            """
            持有一个非法子模块的伪透明根
            """

            super().__init__()
            self.foreign = _ForeignLeaf()

    workstation = Workstation.cpu()
    with pytest.raises(WorkstationError):
        workstation.host(_BadRoot())

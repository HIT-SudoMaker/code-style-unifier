
from __future__ import annotations

from collections.abc import Callable, Mapping

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
from chromatix_next.optics.source import CollimatedRaySource
from chromatix_next.workstation import NamedOutputs, RunRecord, Workstation


def _collimated_ray_bundle_calculation(
    root: torch.nn.Module,
    grid: SpatialGrid,
) -> Mapping[str, RayBundle]:
    # 模块级 calculation：每物理行一个动作，把光源输出包成命名 Mapping
    return {"rays": root(grid)}


def _collimated_with_precision_drift_calculation(
    root: torch.nn.Module,
    grid: SpatialGrid,
) -> Mapping[str, RayBundle]:
    bundle = root(grid)
    for field in ("position", "direction", "power", "refractive_index"):
        object.__setattr__(
            bundle,
            field,
            getattr(bundle, field).to(torch.float32),
        )
    return {"rays": bundle}


def _bare_tensor_payload_calculation(
    root: torch.nn.Module,
    grid: SpatialGrid,
) -> Mapping[str, RayBundle]:
    # 故意返回裸张量而非 RayBundle，触发命名输出值类型校验
    del root, grid
    return {"rays": torch.zeros((1, 4, 3))}  # type: ignore[return-value]


def _grid(
    counts: tuple[int, int] = (3, 4),
    spacing: tuple[float, float] = (1.0, 2.0),
) -> SpatialGrid:
    # 中心对齐的小型横向网格
    return SpatialGrid.centered(
        sample_counts=counts,
        sample_spacing=spacing,
    )


def _spectrum() -> Spectrum:
    # 单色光谱
    return Spectrum.monochromatic(wavelength=2.0e-6)


def _collimated_source(
    *,
    ray_power: float | torch.nn.Parameter = 1.0,
) -> CollimatedRaySource:
    # 默认真空介质、沿 +z 方向的准直源
    return CollimatedRaySource(
        spectrum=_spectrum(),

        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        ray_power=ray_power,
    )


def _inputs_factory(
    grid: SpatialGrid,
) -> Callable[[torch.device], tuple[object, ...]]:
    # 返回 inputs(device) 工厂；网格按目标设备迁移（固定 double → float64）
    def factory(device: torch.device) -> tuple[object, ...]:
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


class TestRunRayBundleOutput:
    """
    端到端运行：``CollimatedRaySource`` 以命名输出产出 ``RayBundle``
    """

    def test_run_returns_named_ray_bundle(self) -> None:
        """
        工作站运行模块级 calculation，命名输出含 RayBundle；real dtype 固定为 float64
        """
        workstation = Workstation.cpu()
        source = _collimated_source()
        workstation.host(source)
        grid = _grid()
        outputs, record = workstation.run(
            _collimated_ray_bundle_calculation,
            root=source,
            inputs=_inputs_factory(grid),
        )
        assert isinstance(outputs, NamedOutputs)
        assert isinstance(record, RunRecord)
        assert tuple(outputs) == ("rays",)
        bundle = outputs["rays"]
        assert isinstance(bundle, RayBundle)
        assert bundle.position.dtype is torch.float64
        assert bundle.direction.dtype is torch.float64
        assert bundle.power.dtype is torch.float64
        assert bundle.optical_path.dtype is torch.float64
        assert bundle.status.dtype is torch.uint8
        assert bundle.position.device == workstation.device

    def test_meta_real_schema_agree_for_ray_bundle(self) -> None:
        """
        同一计算跨运行重复执行（默认 seed） ⇒ RayBundle 输出逐元素一致
        """
        workstation = Workstation.cpu()
        source = _collimated_source()
        workstation.host(source)
        grid = _grid()
        outputs_first, _ = workstation.run(
            _collimated_ray_bundle_calculation,
            root=source,
            inputs=_inputs_factory(grid),
        )
        outputs_second, _ = workstation.run(
            _collimated_ray_bundle_calculation,
            root=source,
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

    def test_host_preserves_fixed_double_ray_power(self) -> None:
        """
        源以 float64 构造；host 后 ray_power 与输出 real state 保持 float64
        """
        source = CollimatedRaySource(
            spectrum=_spectrum(),

            polarization=Polarization.linear_x(),
            medium=ConstantMedium(index=1.2),
            ray_power=torch.nn.Parameter(torch.tensor(1.0, dtype=torch.float64)),
        )
        workstation = Workstation.cpu()
        workstation.host(source)
        assert source._scale_value.dtype is torch.float64  # noqa: SLF001
        grid = _grid()
        outputs, _ = workstation.run(
            _collimated_ray_bundle_calculation,
            root=source,
            inputs=_inputs_factory(grid),
        )
        bundle = outputs["rays"]
        assert isinstance(bundle, RayBundle)
        assert bundle.position.dtype is torch.float64
        assert bundle.power.dtype is torch.float64
        assert bundle.optical_path.dtype is torch.float64

    def test_run_rejects_precision_mismatch_in_ray_bundle_output(self) -> None:
        """
        组件返回错误 dtype 的 RayBundle ⇒ WorkstationError（在任何失实记录前）
        """
        workstation = Workstation.cpu()
        source = _collimated_source()
        workstation.host(source)
        grid = _grid()
        with pytest.raises(
            WorkstationError,
            match="workstation_run_physical_value_dtype_invalid",
        ):
            workstation.run(
                _collimated_with_precision_drift_calculation,
                root=source,
                inputs=_inputs_factory(grid),
            )


def test_named_outputs_value_invalid_rejects_non_physical_payload() -> None:
    """
    模块级 calculation 返回非物理值（普通张量）⇒ WorkstationError
    """
    workstation = Workstation.cpu()
    source = _collimated_source()
    workstation.host(source)

    with pytest.raises(WorkstationError) as rejected:
        workstation.run(
            _bare_tensor_payload_calculation,
            root=source,
            inputs=_inputs_factory(_grid()),
        )
    assert (
        "workstation_calculation_output_value_invalid" in rejected.value.identity
    )

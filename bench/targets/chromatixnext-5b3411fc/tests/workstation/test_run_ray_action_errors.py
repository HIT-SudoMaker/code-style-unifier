
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import importlib
from typing import Any

import pytest
import torch

from chromatix_next.errors import AssemblyError, OpticalError
from chromatix_next.optics import (
    Assembly,
    ConstantMedium,
    Polarization,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics._ray_surface_advance import RaySurfaceAdvance
from chromatix_next.optics.element import ReflectAt, RefractAt
from chromatix_next.optics.propagation import TraceTo
from chromatix_next.optics.source import CollimatedRaySource
from chromatix_next.optics.surface import Plane
from chromatix_next.workstation import Workstation


def _ray_grid() -> SpatialGrid:
    # 准直光线源发射网格：光线从 z=0 沿 +z 发射，命中 z=1e-3 平面
    return SpatialGrid.centered(
        sample_counts=(3, 3),
        sample_spacing=(0.2e-3, 0.2e-3),
    )


def _source() -> CollimatedRaySource:
    return CollimatedRaySource(
        spectrum=Spectrum.monochromatic(wavelength=2.0e-6),

        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        ray_power=1.0,
    )


def _corrupt_position(
    original: Callable[..., RaySurfaceAdvance],
) -> Callable[..., RaySurfaceAdvance]:
    # 腐蚀 advance 输出位置为 NaN（保持其余字段），驱动动作的输出有限性守卫
    def _bad(
        bundle: object,
        surface: object,
        **kwargs: object,
    ) -> RaySurfaceAdvance:
        real = original(bundle, surface, **kwargs)  # type: ignore[arg-type]
        return replace(
            real,
            position=torch.full_like(real.position, float("nan")),
        )

    return _bad


def _corrupt_position_and_normal(
    original: Callable[..., RaySurfaceAdvance],
) -> Callable[..., RaySurfaceAdvance]:
    def _bad(
        bundle: object,
        surface: object,
        **kwargs: object,
    ) -> RaySurfaceAdvance:
        real = original(bundle, surface, **kwargs)  # type: ignore[arg-type]
        return replace(
            real,
            position=torch.full_like(real.position, float("nan")),
            unit_normal=torch.full_like(real.unit_normal, float("nan")),
        )

    return _bad


def _build_ray_assembly(component: Any, name: str) -> Assembly:
    assembly = Assembly()
    grid = _ray_grid()
    source = _source()
    assembly.include(source, name="source", grid=grid)
    assembly.include(component, name=name)
    assembly.connect(source, component)
    assembly.expose(component, name="bundle")
    return assembly


@pytest.mark.parametrize(
    ("action_name", "submodule", "bare_identity", "corrupt", "component_factory"),
    (
        (
            "trace_to",
            "chromatix_next.optics.propagation.trace_to",
            "trace_to_output_position_nonfinite",
            _corrupt_position,
            lambda: TraceTo(surface=Plane(origin=(0.0, 0.0, 1.0e-3))),
        ),
        (
            "reflect_at",
            "chromatix_next.optics.element.reflect_at",
            "reflect_at_output_state_nonfinite",
            _corrupt_position_and_normal,
            lambda: ReflectAt(surface=Plane(origin=(0.0, 0.0, 1.0e-3))),
        ),
        (
            "refract_at",
            "chromatix_next.optics.element.refract_at",
            "refract_at_output_state_nonfinite",
            _corrupt_position_and_normal,
            lambda: RefractAt(
                surface=Plane(origin=(0.0, 0.0, 1.0e-3)),
                destination_medium=ConstantMedium(index=1.5),
            ),
        ),
    ),
    ids=("trace_to", "reflect_at", "refract_at"),
)
def test_workstation_run_propagates_action_specific_nonfinite_identity(
    action_name: str,
    submodule: str,
    bare_identity: str,
    corrupt: Callable[..., Callable[..., RaySurfaceAdvance]],
    component_factory: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    数值核退化（advance 输出 NaN）经工作站真实重放 ⇒ 按 action 特定裸身份失败（非通用
    bundle 身份）；稳定身份在管道中保留

    装配/冻结的 meta 推导对值依赖的非有限身份不触发（见下一个测试的语义边界），故不产生
    ``assembly_element_forward_failed`` 包装身份；工作站私有重放按设计透传原异常
    （``_assembly_replay.py`` ``_replay`` findings=None）。稳定身份仍为 action 特定的
    ``*_output_*_nonfinite``，符合 CONTEXT 的稳定域错误契约。
    """

    module = importlib.import_module(submodule)
    original = module.advance_ray_surface
    monkeypatch.setattr(module, "advance_ray_surface", corrupt(original))

    assembly = _build_ray_assembly(component_factory(), action_name)
    workstation = Workstation.cpu()
    assembly.freeze()
    workstation.host(assembly)
    with pytest.raises(OpticalError) as caught:
        workstation.run(assembly)
    # 裸 action 特定身份透传（非通用 bundle 身份，非 assembly 包装身份）
    assert caught.value.identity == bare_identity


def test_assembly_check_does_not_fire_value_dependent_nonfinite_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    装配检查（meta 推导）对值依赖的非有限身份不触发：诚实记录此语义边界

    meta 推导期 finite 守卫以 ``is_finite_state_tensor`` 不可读早返豁免（守卫
    ``is X is False`` 不触发）；非有限身份仅在真实重放触发（见上测试）。故
    assembly.check() 对该退化几何返回成功，而非抛包装身份。这与表示门控（值无关、
    meta 期触发并包装）形成对照。
    """

    module = importlib.import_module("chromatix_next.optics.propagation.trace_to")
    original = module.advance_ray_surface
    monkeypatch.setattr(
        module,
        "advance_ray_surface",
        _corrupt_position(original),
    )
    assembly = _build_ray_assembly(
        TraceTo(surface=Plane(origin=(0.0, 0.0, 1.0e-3))),
        "trace_to",
    )
    # meta 推导不读张量值 ⇒ finite 守卫早返豁免 ⇒ check() 不抛
    assembly.check()

from __future__ import annotations

from dataclasses import dataclass
from typing import get_args

import torch

from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter
from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

from .medium import Medium
from .ray_bundle import RayBundle
from .surface.conic import ConicEvenAsphere
from .surface.plane import Plane
from .surface.sphere import Sphere

# 三面闭合集合的规范类型别名；运行时 isinstance 元组由它机械派生
SurfaceForAdvance = Plane | Sphere | ConicEvenAsphere

_ADVANCE_SURFACE_TYPES: tuple[type[object], ...] = get_args(
    SurfaceForAdvance,
)

_SurfaceOrEncounterForAdvance = SurfaceForAdvance | SurfaceEncounter


def wavelengths_for_bundle(
    bundle: RayBundle,
    *,
    device: torch.device,
    real_dtype: torch.dtype,
) -> torch.Tensor:
    """
    派生与 ray 设备/精度对齐的逐分量波长张量

    """

    return torch.tensor(
        bundle.spectrum.wavelengths,
        device=device,
        dtype=real_dtype,
    )


def refractive_indices_aligned(
    medium: Medium,
    bundle: RayBundle,
    *,
    real_dtype: torch.dtype,
) -> torch.Tensor:
    """
    在 bundle 波长上评估介质色散律，reshape 到 (1,...,1, spectrum, 1) 与逐 ray 可广播

    """

    wavelengths = wavelengths_for_bundle(
        bundle,
        device=bundle.position.device,
        real_dtype=real_dtype,
    )
    refractive_indices = medium.refractive_index(wavelengths).to(
        device=bundle.position.device,
        dtype=real_dtype,
    )
    batch_ndim = bundle.position.dim() - 3
    view_shape = (1,) * batch_ndim + (bundle.spectral_count, 1)
    return refractive_indices.view(view_shape)


def is_finite_position_tensor(position: torch.Tensor) -> bool | None:
    """
    判断位置张量是否处处有限；meta 设备读不出取值时返回 None

    """

    is_finite = torch.isfinite(position).all()
    if not is_value_readable(is_finite):
        return None
    return bool(is_finite)


def is_finite_state_tensor(
    position: torch.Tensor,
    direction: torch.Tensor,
) -> bool | None:
    """
    判断位置与方向张量是否处处有限；meta 设备读不出取值时返回 None

    """

    is_finite = torch.isfinite(position).all() & torch.isfinite(
        direction,
    ).all()
    if not is_value_readable(is_finite):
        return None
    return bool(is_finite)


@dataclass(frozen=True, slots=True)
class RaySurfaceAdvance:
    """
    共享光线-面推进的结构化结果（私有，承载六动作都需要的事实）

    """

    position: torch.Tensor
    optical_path: torch.Tensor
    status: torch.Tensor
    unit_normal: torch.Tensor
    is_interacted: torch.Tensor


def advance_ray_surface(
    bundle: RayBundle,
    surface: _SurfaceOrEncounterForAdvance,
    *,
    active_status_value: int,
    missed_status_value: int,
    vignetted_status_value: int,
) -> RaySurfaceAdvance:
    """
    在闭合面处推进光线束，返回六动作共享的推进事实

    一次闭合类型判定、一次 encounter 求值；活动光线位置前进到全局交点、按入射折射率累
    加光程，并完成孔径与状态分类（命中孔径内为活动、孔径外为遮挡、未命中为错过、终态光
    线原样保留），非活动通道处处有限。不改写方向、折射率或功率——这些归各动作自己拥
    有。折射动作在此结果上对全内反射光线做活动→TIR 的状态覆写。

    """

    if isinstance(surface, SurfaceEncounter):
        encounter = surface
    elif isinstance(surface, _ADVANCE_SURFACE_TYPES):
        # 一次 encounter 求值（面局部求交、法线、孔径投影归各面数值核所有）
        encounter = surface._encounter(  # noqa: SLF001
            bundle.position,
            bundle.direction,
        )
    else:
        message = (
            "光线-面共享推进只接受 Plane、Sphere 或 ConicEvenAsphere，"
            f"收到的是 {type(surface).__name__}"
        )
        raise _errors.OpticalTypeError(
            "ray_surface_advance_surface_invalid",
            message,
        )
    is_active_input = bundle.status == active_status_value
    is_unresolvable_active_encounter = (
        is_active_input
        & encounter.is_encountered
        & (~encounter.is_continuous_distance_resolvable)
    )
    has_unresolvable_active_encounter = (
        is_unresolvable_active_encounter.any()
    )
    if is_value_readable(has_unresolvable_active_encounter) and bool(
        has_unresolvable_active_encounter
    ):
        message = (
            "精确拓扑确认活动光线与表面相交，但固定双精度无法表示连续交点距离；"
            "请调整光路尺度或几何条件"
        )
        raise _errors.OpticalValueError(
            "ray_surface_distance_unresolvable",
            message,
        )
    is_encountered_active = is_active_input & encounter.is_encountered
    is_inside_aperture = encounter.is_inside_aperture
    is_interacted = is_encountered_active & is_inside_aperture
    next_position = torch.where(
        is_encountered_active.unsqueeze(-1),
        encounter.intersection,
        bundle.position,
    )
    optical_path_increment = (
        bundle.refractive_index * encounter.distance.to(torch.float64)
    )
    next_optical_path = torch.where(
        is_encountered_active,
        bundle.optical_path + optical_path_increment,
        bundle.optical_path,
    )
    active_status = torch.full_like(bundle.status, active_status_value)
    vignetted_status = torch.full_like(
        bundle.status,
        vignetted_status_value,
    )
    missed_status = torch.full_like(bundle.status, missed_status_value)
    encountered_status = torch.where(
        is_inside_aperture,
        active_status,
        vignetted_status,
    )
    next_status = torch.where(
        is_encountered_active,
        encountered_status,
        torch.where(
            is_active_input,
            missed_status,
            bundle.status,
        ),
    )
    return RaySurfaceAdvance(
        position=next_position,
        optical_path=next_optical_path,
        status=next_status,
        unit_normal=encounter.unit_normal,
        is_interacted=is_interacted,
    )

from __future__ import annotations

import torch

import chromatix_next.errors as _errors

from .._meta_inference import _is_meta_inference_active
from .._ray_surface_advance import (
    _ADVANCE_SURFACE_TYPES,
    SurfaceForAdvance,
    advance_ray_surface,
    is_finite_position_tensor,
)
from .._role_contract import _PropagationRole
from ..ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)


def _validate_bundle(bundle: object) -> None:
    if not isinstance(bundle, RayBundle):
        message = (
            "trace_to 只能作用于光线束物理值，"
            f"收到的是 {type(bundle).__name__}"
        )
        raise _errors.OpticalTypeError(
            "trace_to_bundle_invalid",
            message,
        )


SurfaceForTrace = SurfaceForAdvance



def _validate_surface_kind(surface: object) -> None:
    if not isinstance(surface, _ADVANCE_SURFACE_TYPES):
        message = (
            "trace_to 当前接受 Plane、Sphere 或 ConicEvenAsphere 作为目标 Surface，"
            f"收到的是 {type(surface).__name__}"
        )
        raise _errors.OpticalTypeError(
            "trace_to_surface_invalid",
            message,
        )


def trace_to(
    bundle: RayBundle,
    *,
    surface: SurfaceForTrace,
) -> RayBundle:
    """
    把光线束通过最近正向交集传到指定 posed 平面、球面或圆锥偶次非球面

    Args:
        bundle: 待与表面相互作用的光线束
        surface: 定义相交几何、孔径与局部坐标架的表面

    Returns:
        输出更新后的 RayBundle，保留射线状态和谱道顺序

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

        OpticalTypeError: 输入对象物理类型不满足该 Interface
    """

    _validate_bundle(bundle)
    _validate_surface_kind(surface)
    if not _is_meta_inference_active():
        surface._validate_physical_state()  # noqa: SLF001
    advance = advance_ray_surface(
        bundle,
        surface,
        active_status_value=RAY_STATUS_ACTIVE,
        missed_status_value=RAY_STATUS_SURFACE_MISSED,
        vignetted_status_value=RAY_STATUS_VIGNETTED,
    )
    is_advance_finite = is_finite_position_tensor(advance.position)
    if is_advance_finite is False:
        message = (
            "trace_to 的输出位置必须处处有限；非数说明上游几何已经发散，"
            "请检查 Plane/Sphere/ConicEvenAsphere 姿态或入射光线束状态"
        )
        raise _errors.OpticalValueError(
            "trace_to_output_position_nonfinite",
            message,
        )
    return RayBundle(
        position=advance.position,
        direction=bundle.direction,
        polarization_vector=bundle.polarization_vector,
        power=bundle.power,
        refractive_index=bundle.refractive_index,
        optical_path=advance.optical_path,
        status=advance.status,
        spectrum=bundle.spectrum,
    )


class TraceTo(torch.nn.Module):
    """
    持有 posed 平面、球面或圆锥偶次非球面并把入射光线束传到该面的传播组件

    Args:
        surface: 定义相交几何、孔径与局部坐标架的表面

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface

    """

    surface: SurfaceForTrace

    def __init__(
        self,
        *,
        surface: SurfaceForTrace,
    ) -> None:

        super().__init__()
        _validate_surface_kind(surface)
        surface._validate_physical_state()  # noqa: SLF001
        self.surface = surface

    @property
    def role(self) -> _PropagationRole:
        """
        传播角色字面量

        Returns:
            返回该组件声明的 Propagation 角色

        """

        return "propagation"

    def forward(self, bundle: RayBundle) -> RayBundle:  # type: ignore[override]
        """
        把入射光线束通过最近正向交集传到所持面

        Args:
            bundle: 待与表面相互作用的光线束

        Returns:
            输出更新后的 RayBundle，保留射线状态和谱道顺序

        """

        return trace_to(bundle, surface=self.surface)

    def _validate_physical_state(self) -> None:
        self.surface._validate_physical_state()  # noqa: SLF001

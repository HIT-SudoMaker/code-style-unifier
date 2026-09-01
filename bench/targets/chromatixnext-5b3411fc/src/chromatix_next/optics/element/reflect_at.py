from __future__ import annotations

import torch

from chromatix_next._numerics.ray_polarization import reflect_polarization_direction
from chromatix_next._numerics.reflection import reflect_direction
from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

from .._meta_inference import _is_meta_inference_active
from .._ray_surface_advance import (
    _ADVANCE_SURFACE_TYPES,
    SurfaceForAdvance,
    advance_ray_surface,
    is_finite_state_tensor,
)
from .._role_contract import _ElementRole
from ..ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)


def _validate_bundle(bundle: object) -> None:
    if not isinstance(bundle, RayBundle):
        message = (
            "reflect_at 只能作用于光线束物理值，"
            f"收到的是 {type(bundle).__name__}"
        )
        raise _errors.OpticalTypeError(
            "reflect_at_bundle_invalid",
            message,
        )


SurfaceForReflect = SurfaceForAdvance



def _validate_surface_kind(surface: object) -> None:
    if not isinstance(surface, _ADVANCE_SURFACE_TYPES):
        message = (
            "reflect_at 当前接受 Plane、Sphere 或 ConicEvenAsphere 作为反射面，"
            f"收到的是 {type(surface).__name__}"
        )
        raise _errors.OpticalTypeError(
            "reflect_at_surface_invalid",
            message,
        )


def reflect_at(
    bundle: RayBundle,
    *,
    surface: SurfaceForReflect,
) -> RayBundle:
    """
    把光线束在指定平面、球面或圆锥偶次非球面处按镜面反射律反射

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
    reflected_direction = reflect_direction(
        ray_direction=bundle.direction,
        unit_normal=advance.unit_normal,
        is_interacted=advance.is_interacted,
    )
    reflected_polarization = reflect_polarization_direction(
        ray_polarization=bundle.polarization_vector,
        unit_normal=advance.unit_normal,
        is_interacted=advance.is_interacted,
    )
    is_reflected_finite = is_finite_state_tensor(
        advance.position,
        reflected_direction,
    )
    if is_reflected_finite is False:
        message = (
            "reflect_at 的输出位置与方向必须处处有限；非数说明上游几何已经发散，"
            "请检查 Plane/Sphere/ConicEvenAsphere 姿态、曲率参数或入射光线束状态"
        )
        raise _errors.OpticalValueError(
            "reflect_at_output_state_nonfinite",
            message,
        )
    is_polarization_finite = torch.isfinite(
        reflected_polarization
    ).all()
    if is_value_readable(is_polarization_finite) and not bool(
        is_polarization_finite
    ):
        message = (
            "reflect_at 的输出偏振方向必须处处有限；非数说明反射 Householder 已退化，"
            "请检查入射偏振方向或面法线"
        )
        raise _errors.OpticalValueError(
            "reflect_at_output_polarization_nonfinite",
            message,
        )
    return RayBundle(
        position=advance.position,
        direction=reflected_direction,
        polarization_vector=reflected_polarization,
        power=bundle.power,
        refractive_index=bundle.refractive_index,
        optical_path=advance.optical_path,
        status=advance.status,
        spectrum=bundle.spectrum,
    )


class ReflectAt(torch.nn.Module):
    """
    持有 posed 反射面并把入射光线束在该面处反射的元件组件

    Args:
        surface: 定义相交几何、孔径与局部坐标架的表面

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface

    """

    surface: SurfaceForReflect

    def __init__(
        self,
        *,
        surface: SurfaceForReflect,
    ) -> None:

        super().__init__()
        _validate_surface_kind(surface)
        surface._validate_physical_state()  # noqa: SLF001
        self.surface = surface

    @property
    def role(self) -> _ElementRole:
        """
        元件角色字面量

        Returns:
            返回该组件声明的 Element 角色

        """

        return "element"

    def forward(self, bundle: RayBundle) -> RayBundle:  # type: ignore[override]
        """
        把入射光线束在所持面处按镜面反射律反射

        Args:
            bundle: 待与表面相互作用的光线束

        Returns:
            输出更新后的 RayBundle，保留射线状态和谱道顺序

        """

        return reflect_at(bundle, surface=self.surface)

    def _validate_physical_state(self) -> None:
        self.surface._validate_physical_state()  # noqa: SLF001

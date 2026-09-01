from __future__ import annotations

import torch

from chromatix_next._numerics.ray_polarization import rotate_polarization_minimal
from chromatix_next._numerics.refraction import refract_at_advance
from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

from .._meta_inference import _is_meta_inference_active
from .._ray_surface_advance import (
    _ADVANCE_SURFACE_TYPES,
    SurfaceForAdvance,
    advance_ray_surface,
    is_finite_state_tensor,
    refractive_indices_aligned,
)
from .._role_contract import _ElementRole
from ..medium import Medium
from ..ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_TOTAL_INTERNAL_REFLECTION,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)


def _validate_bundle(bundle: object) -> None:
    if not isinstance(bundle, RayBundle):
        message = (
            "refract_at 只能作用于光线束物理值，"
            f"收到的是 {type(bundle).__name__}"
        )
        raise _errors.OpticalTypeError(
            "refract_at_bundle_invalid",
            message,
        )


SurfaceForRefract = SurfaceForAdvance



def _validate_surface_kind(surface: object) -> None:
    if not isinstance(surface, _ADVANCE_SURFACE_TYPES):
        message = (
            "refract_at 当前接受 Plane、Sphere 或 ConicEvenAsphere 作为目标 Surface，"
            f"收到的是 {type(surface).__name__}"
        )
        raise _errors.OpticalTypeError(
            "refract_at_surface_invalid",
            message,
        )


def _validate_destination_medium(destination_medium: object) -> None:
    if not isinstance(destination_medium, Medium):
        message = (
            "refract_at 必须显式命名目标介质，"
            f"收到的是 {type(destination_medium).__name__}"
        )
        raise _errors.OpticalTypeError(
            "refract_at_destination_medium_invalid",
            message,
        )


def refract_at(
    bundle: RayBundle,
    *,
    surface: SurfaceForRefract,
    destination_medium: Medium,
) -> RayBundle:
    """
    把光线束在平面、球面或圆锥偶次非球面处按向量 Snell 折射进指定目标介质

    Args:
        bundle: 待与表面相互作用的光线束
        surface: 定义相交几何、孔径与局部坐标架的表面
        destination_medium: 透射侧使用的折射率模型

    Returns:
        输出更新后的 RayBundle，保留射线状态和谱道顺序

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

        OpticalTypeError: 输入对象物理类型不满足该 Interface
    """

    _validate_bundle(bundle)
    _validate_surface_kind(surface)
    _validate_destination_medium(destination_medium)
    if not _is_meta_inference_active():
        surface._validate_physical_state()  # noqa: SLF001
    real_dtype = bundle.position.dtype
    destination_refractive_indices = refractive_indices_aligned(
        destination_medium,
        bundle,
        real_dtype=real_dtype,
    )
    advance = advance_ray_surface(
        bundle,
        surface,
        active_status_value=RAY_STATUS_ACTIVE,
        missed_status_value=RAY_STATUS_SURFACE_MISSED,
        vignetted_status_value=RAY_STATUS_VIGNETTED,
    )
    refracted = refract_at_advance(
        ray_direction=bundle.direction,
        incident_refractive_indices=bundle.refractive_index,
        destination_refractive_indices=destination_refractive_indices,
        unit_normal=advance.unit_normal,
        is_interacted=advance.is_interacted,
        base_status=advance.status,
        total_internal_reflection_status_value=(
            RAY_STATUS_TOTAL_INTERNAL_REFLECTION
        ),
    )
    is_refracted_finite = is_finite_state_tensor(
        advance.position,
        refracted.direction,
    )
    if is_refracted_finite is False:
        message = (
            "refract_at 的输出位置与方向必须处处有限；非数说明上游几何已经发散，"
            "请检查 Plane/Sphere/ConicEvenAsphere 姿态、曲率参数或入射光线束状态"
        )
        raise _errors.OpticalValueError(
            "refract_at_output_state_nonfinite",
            message,
        )
    rotated_polarization = rotate_polarization_minimal(
        incident_direction=bundle.direction,
        transmitted_direction=refracted.direction,
        ray_polarization=bundle.polarization_vector,
        is_refracted=refracted.is_refracted,
    )
    is_polarization_finite = torch.isfinite(rotated_polarization).all()
    if is_value_readable(is_polarization_finite) and not bool(
        is_polarization_finite
    ):
        message = (
            "refract_at 的输出偏振方向必须处处有限；非数说明最小旋转已退化，"
            "请检查入射偏振方向或入射/透射方向几何"
        )
        raise _errors.OpticalValueError(
            "refract_at_output_polarization_nonfinite",
            message,
        )
    return RayBundle(
        position=advance.position,
        direction=refracted.direction,
        polarization_vector=rotated_polarization,
        power=bundle.power,
        refractive_index=refracted.refractive_index,
        optical_path=advance.optical_path,
        status=refracted.status,
        spectrum=bundle.spectrum,
    )


class RefractAt(torch.nn.Module):
    """
    持有 posed 平面、球面或圆锥偶次非球面与目标介质并把入射光线束折射进该介质的元件组件

    Args:
        surface: 定义相交几何、孔径与局部坐标架的表面
        destination_medium: 透射侧使用的折射率模型

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface

    """

    surface: SurfaceForRefract
    destination_medium: Medium

    def __init__(
        self,
        *,
        surface: SurfaceForRefract,
        destination_medium: Medium,
    ) -> None:

        super().__init__()
        _validate_surface_kind(surface)
        _validate_destination_medium(destination_medium)
        surface._validate_physical_state()  # noqa: SLF001
        self.surface = surface
        self.destination_medium = destination_medium

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
        把入射光线束在所持面处折射进所持目标介质

        Args:
            bundle: 待与表面相互作用的光线束

        Returns:
            输出更新后的 RayBundle，保留射线状态和谱道顺序

        """

        return refract_at(
            bundle,
            surface=self.surface,
            destination_medium=self.destination_medium,
        )

    def _validate_physical_state(self) -> None:
        self.surface._validate_physical_state()  # noqa: SLF001

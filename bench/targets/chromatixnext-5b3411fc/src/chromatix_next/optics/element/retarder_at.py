from __future__ import annotations

import math

import torch

from chromatix_next._numerics.ray_polarization import (
    derive_plane_local_jones_frame,
    retard_ray_polarization,
)
from chromatix_next._tensors import (
    is_finite_fixed_double_scalar,
    is_finite_fixed_double_scalar_in_closed_interval,
    is_value_readable,
    register_fixed_double_real_scalar,
)
import chromatix_next.errors as _errors

from .._meta_inference import _is_meta_inference_active
from .._ray_surface_advance import advance_ray_surface, is_finite_state_tensor
from .._role_contract import _ElementRole
from ..ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)
from ..surface.plane import Plane


def _validate_bundle(bundle: object) -> None:
    if not isinstance(bundle, RayBundle):
        message = (
            "retarder_at 只能作用于光线束物理值，"
            f"收到的是 {type(bundle).__name__}"
        )
        raise _errors.OpticalTypeError(
            "retarder_at_bundle_invalid",
            message,
        )



def _validate_surface_kind(surface: object) -> None:
    if not isinstance(surface, Plane):
        message = (
            "retarder_at 当前只接受 Plane 作为延迟面（Plane-local Jones 帧），"
            f"收到的是 {type(surface).__name__}"
        )
        raise _errors.OpticalTypeError(
            "retarder_at_surface_invalid",
            message,
        )


def _validate_retardance_cycles(retardance_cycles: object) -> None:
    if not is_finite_fixed_double_scalar(retardance_cycles):
        raise _errors.OpticalValueError(
            "retarder_at_retardance_cycles_invalid",
            "延迟量必须是以周期计的有限实数标量",
        )


def _validate_retarded_eigenstate_azimuth_radians(
    retarded_eigenstate_azimuth_radians: object,
) -> None:
    # 方位角须为有限实数标量（周期相位权威；弧度仅用于本征态取向构造）
    if not is_finite_fixed_double_scalar(
        retarded_eigenstate_azimuth_radians
    ):
        raise _errors.OpticalValueError(
            "retarder_at_retarded_eigenstate_azimuth_radians_invalid",
            "延迟本征态方位角必须是以弧度计的有限实数标量",
        )


def _validate_retarded_eigenstate_ellipticity_radians(
    retarded_eigenstate_ellipticity_radians: object,
) -> None:
    lower_bound = -math.pi / 4.0
    upper_bound = math.pi / 4.0
    if not is_finite_fixed_double_scalar_in_closed_interval(
        retarded_eigenstate_ellipticity_radians,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    ):
        raise _errors.OpticalValueError(
            "retarder_at_retarded_eigenstate_ellipticity_radians_invalid",
            "延迟本征态椭率角必须是 [-pi/4, +pi/4] 内的有限实数标量",
        )


def retarder_at(
    bundle: RayBundle,
    *,
    surface: Plane,
    retardance_cycles: float | torch.Tensor,
    retarded_eigenstate_azimuth_radians: float | torch.Tensor,
    retarded_eigenstate_ellipticity_radians: float | torch.Tensor,
) -> RayBundle:
    """
    把光线束在指定平面处按零均值 SU(2) 律延迟（Plane-local Jones 帧）

    Args:
        bundle: 待与表面相互作用的光线束
        surface: 定义相交几何、孔径与局部坐标架的表面
        retardance_cycles: 两个偏振本征态之间以周期表示的相位延迟
        retarded_eigenstate_azimuth_radians: 慢轴本征态在局部偏振平面的方位角
        retarded_eigenstate_ellipticity_radians: 慢轴本征态的椭圆率角

    Returns:
        输出更新后的 RayBundle，保留射线状态和谱道顺序

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

        OpticalTypeError: 输入对象物理类型不满足该 Interface
    """

    _validate_bundle(bundle)
    _validate_surface_kind(surface)
    _validate_retardance_cycles(retardance_cycles)
    _validate_retarded_eigenstate_azimuth_radians(
        retarded_eigenstate_azimuth_radians,
    )
    _validate_retarded_eigenstate_ellipticity_radians(
        retarded_eigenstate_ellipticity_radians,
    )
    if not _is_meta_inference_active():
        surface._validate_physical_state()  # noqa: SLF001
    real_dtype = bundle.position.dtype
    device = bundle.position.device
    aligned_retardance_cycles = torch.as_tensor(
        retardance_cycles,
        device=device,
        dtype=real_dtype,
    )
    aligned_retarded_eigenstate_azimuth_radians = torch.as_tensor(
        retarded_eigenstate_azimuth_radians,
        device=device,
        dtype=real_dtype,
    )
    aligned_retarded_eigenstate_ellipticity_radians = torch.as_tensor(
        retarded_eigenstate_ellipticity_radians,
        device=device,
        dtype=real_dtype,
    )
    advance = advance_ray_surface(
        bundle,
        surface,
        active_status_value=RAY_STATUS_ACTIVE,
        missed_status_value=RAY_STATUS_SURFACE_MISSED,
        vignetted_status_value=RAY_STATUS_VIGNETTED,
    )
    plane_tangent_x = surface.tangent_x.to(device=device, dtype=real_dtype)
    plane_local_frame = derive_plane_local_jones_frame(
        ray_direction=bundle.direction,
        plane_tangent_x=plane_tangent_x,
        is_interacted=advance.is_interacted,
    )
    has_degenerate_interaction = (
        plane_local_frame.is_interaction_degenerate.any()
    )
    if is_value_readable(has_degenerate_interaction) and bool(
        has_degenerate_interaction
    ):
        message = (
            "retarder_at 的 Plane-local Jones 帧在交互通道上遇到精确零投影：作者 "
            "Plane 姿态的 tangent_x 平行于入射光线方向，无法构造横截基底；"
            "请检查 Plane 姿态或入射光线束方向"
        )
        raise _errors.OpticalValueError(
            "retarder_at_plane_local_projection_degenerate",
            message,
        )
    has_unresolvable_projection = (
        ~plane_local_frame.is_projection_resolvable
    ).any()
    if is_value_readable(has_unresolvable_projection) and bool(
        has_unresolvable_projection
    ):
        message = (
            "retarder_at 的 Plane-local Jones 投影在精确非退化交互通道上无法以 "
            "binary64 构造有限非零基底；请调整 Plane 姿态或入射方向的数值尺度"
        )
        raise _errors.OpticalValueError(
            "retarder_at_plane_local_projection_unresolvable",
            message,
        )
    retarded_polarization = retard_ray_polarization(
        ray_polarization=bundle.polarization_vector,
        plane_local_frame=plane_local_frame,
        is_interacted=advance.is_interacted,
        retardance_cycles=aligned_retardance_cycles,
        retarded_eigenstate_azimuth_radians=(
            aligned_retarded_eigenstate_azimuth_radians
        ),
        retarded_eigenstate_ellipticity_radians=(
            aligned_retarded_eigenstate_ellipticity_radians
        ),
    )
    is_state_finite = is_finite_state_tensor(
        advance.position,
        bundle.direction,
    )
    if is_state_finite is False:
        message = (
            "retarder_at 的输出位置与方向必须处处有限；非数说明上游几何已经发散，"
            "请检查 Plane 姿态或入射光线束状态"
        )
        raise _errors.OpticalValueError(
            "retarder_at_output_state_nonfinite",
            message,
        )
    is_polarization_finite = torch.isfinite(retarded_polarization).all()
    if is_value_readable(is_polarization_finite) and not bool(
        is_polarization_finite
    ):
        message = (
            "retarder_at 的输出偏振方向必须处处有限；非数说明 Plane-local Jones 帧或"
            "SU(2) 延迟已退化，请检查入射偏振方向、Plane 姿态或延迟参数"
        )
        raise _errors.OpticalValueError(
            "retarder_at_output_polarization_nonfinite",
            message,
        )
    return RayBundle(
        position=advance.position,
        direction=bundle.direction,
        polarization_vector=retarded_polarization,
        power=bundle.power,
        refractive_index=bundle.refractive_index,
        optical_path=advance.optical_path,
        status=advance.status,
        spectrum=bundle.spectrum,
    )


class RetarderAt(torch.nn.Module):
    """
    持有 posed Plane 与延迟参数并把入射光线束在该面处按零均值 SU(2) 律延迟的元件组件

    Args:
        surface: 定义相交几何、孔径与局部坐标架的表面
        retardance_cycles: 两个偏振本征态之间以周期表示的相位延迟
        retarded_eigenstate_azimuth_radians: 慢轴本征态在局部偏振平面的方位角
        retarded_eigenstate_ellipticity_radians: 慢轴本征态的椭圆率角

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    surface: Plane
    retardance_cycles: torch.Tensor
    retarded_eigenstate_azimuth_radians: torch.Tensor
    retarded_eigenstate_ellipticity_radians: torch.Tensor

    def __init__(
        self,
        *,
        surface: Plane,
        retardance_cycles: float | torch.Tensor,
        retarded_eigenstate_azimuth_radians: float | torch.Tensor,
        retarded_eigenstate_ellipticity_radians: float | torch.Tensor,
    ) -> None:

        super().__init__()
        _validate_surface_kind(surface)
        _validate_retardance_cycles(retardance_cycles)
        _validate_retarded_eigenstate_azimuth_radians(
            retarded_eigenstate_azimuth_radians,
        )
        _validate_retarded_eigenstate_ellipticity_radians(
            retarded_eigenstate_ellipticity_radians,
        )
        surface._validate_physical_state()  # noqa: SLF001
        self.surface = surface
        register_fixed_double_real_scalar(
            self,
            name="retardance_cycles",
            value=retardance_cycles,
        )
        register_fixed_double_real_scalar(
            self,
            name="retarded_eigenstate_azimuth_radians",
            value=retarded_eigenstate_azimuth_radians,
        )
        register_fixed_double_real_scalar(
            self,
            name="retarded_eigenstate_ellipticity_radians",
            value=retarded_eigenstate_ellipticity_radians,
        )

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
        对所持 Plane 处的交互光线偏振施加零均值 SU(2) 延迟

        Args:
            bundle: 待与表面相互作用的光线束

        Returns:
            输出更新后的 RayBundle，保留射线状态和谱道顺序

        """

        return retarder_at(
            bundle,
            surface=self.surface,
            retardance_cycles=self.retardance_cycles,
            retarded_eigenstate_azimuth_radians=(
                self.retarded_eigenstate_azimuth_radians
            ),
            retarded_eigenstate_ellipticity_radians=(
                self.retarded_eigenstate_ellipticity_radians
            ),
        )

    def _validate_physical_state(self) -> None:
        self.surface._validate_physical_state()  # noqa: SLF001
        _validate_retardance_cycles(self.retardance_cycles)
        _validate_retarded_eigenstate_azimuth_radians(
            self.retarded_eigenstate_azimuth_radians,
        )
        _validate_retarded_eigenstate_ellipticity_radians(
            self.retarded_eigenstate_ellipticity_radians,
        )

from __future__ import annotations

import torch

from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter
from chromatix_next._numerics.surface_geometry.plane import plane_encounter
import chromatix_next.errors as _errors

from ._pose_state import (
    _register_hard_aperture,
    _register_surface_pose,
    _require_positive_finite_scalar,
    _require_valid_surface_pose,
)


class Plane(torch.nn.Module):
    """
    拥有全局姿态与可选圆形 clear aperture 的无限平面

    Args:
        origin: 平面的空间原点
        tangent_x: 表面局部 x 方向的 authored 切向量
        tangent_y: 表面局部 y 方向的 authored 切向量
        clear_aperture_radius: 以表面局部坐标定义的通光孔径半径

    """

    origin: torch.Tensor
    tangent_x: torch.Tensor
    tangent_y: torch.Tensor
    clear_aperture_radius: torch.Tensor

    def __init__(
        self,
        *,
        origin: (
            tuple[float, float, float] | torch.Tensor | torch.nn.Parameter
        ) = (
            0.0,
            0.0,
            0.0,
        ),
        tangent_x: tuple[float, float, float] | torch.Tensor = (
            1.0,
            0.0,
            0.0,
        ),
        tangent_y: tuple[float, float, float] | torch.Tensor = (
            0.0,
            1.0,
            0.0,
        ),
        clear_aperture_radius: float | torch.Tensor | None = None,
    ) -> None:

        super().__init__()
        _register_surface_pose(
            self,
            surface_name="plane",
            origin=origin,
            tangent_x=tangent_x,
            tangent_y=tangent_y,
        )
        self._register_aperture(
            "clear_aperture_radius",
            clear_aperture_radius,
        )

    @property
    def normal(self) -> torch.Tensor:
        """
        平面法线（tangent_x × tangent_y），与平面朝向同向

        Returns:
            平面顶点处的 float64 法线张量，由 authored 切向量叉积直接派生
            （在 8γ₃ authored 预算内近似单位，未做显式归一化）

        """

        return torch.linalg.cross(self.tangent_x, self.tangent_y)

    def forward(self) -> None:  # type: ignore[override]
        """
        平面是被动 state adapter，没有独立 forward 计算

        Raises:
            OpticalRuntimeError: 调用时的状态或拓扑不满足该 Interface 契约

        """

        raise _errors.OpticalRuntimeError(
            "plane_has_no_forward_action",
            "Plane 是被动 Surface adapter，由 trace/refract/reflect action 消费，"
            "不暴露独立 forward",
        )

    def _encounter(
        self,
        ray_origin: torch.Tensor,
        ray_direction: torch.Tensor,
    ) -> SurfaceEncounter:
        device = ray_origin.device
        real_dtype = ray_origin.dtype
        origin = self.origin.to(device=device, dtype=real_dtype)
        tangent_x = self.tangent_x.to(device=device, dtype=real_dtype)
        tangent_y = self.tangent_y.to(device=device, dtype=real_dtype)
        aperture = self._aperture_on(device=device, dtype=real_dtype)
        return plane_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            plane_origin=origin,
            plane_tangent_x=tangent_x,
            plane_tangent_y=tangent_y,
            clear_aperture_radius=aperture,
        )

    def _aperture_on(
        self,
        *,
        device: torch.device,
        dtype: torch.dtype,
    ) -> torch.Tensor | None:
        aperture = self._aperture_value
        if aperture is None:
            return None
        return aperture.to(device=device, dtype=dtype)

    def _register_aperture(
        self,
        name: str,
        value: float | torch.Tensor | None,
    ) -> None:
        _register_hard_aperture(
            self,
            name=name,
            value=value,
            owner_identity=f"plane_{name}_invalid",
        )

    def _validate_physical_state(self) -> None:
        _require_valid_surface_pose(
            surface_name="plane",
            origin=self.origin,
            tangent_x=self.tangent_x,
            tangent_y=self.tangent_y,
        )
        aperture = self._aperture_value
        if aperture is None:
            return
        _require_positive_finite_scalar(
            aperture,
            field_name="clear_aperture_radius",
            error_identity="plane_clear_aperture_radius_invalid",
        )

    @property
    def _aperture_value(self) -> torch.Tensor | None:
        candidate = self._parameters.get("clear_aperture_radius")
        if candidate is not None:
            return candidate
        return self._buffers.get("clear_aperture_radius")

from __future__ import annotations

import torch

from chromatix_next._numerics.surface_geometry.encounter import SurfaceEncounter
from chromatix_next._numerics.surface_geometry.sphere import sphere_encounter
from chromatix_next._tensors import is_nonzero_finite_fixed_double_scalar
import chromatix_next.errors as _errors

from ._pose_state import (
    _register_hard_aperture,
    _register_surface_pose,
    _require_positive_finite_scalar,
    _require_valid_surface_pose,
)


def _require_valid_radius_of_curvature(value: object) -> None:
    if is_nonzero_finite_fixed_double_scalar(value):
        return
    message = (
        "radius_of_curvature 必须是非零有限 float64 实标量；"
        "正负号只编码曲率中心相对顶点法线的方向，"
        f"收到的是 {value!r}"
    )
    raise _errors.OpticalValueError(
        "sphere_radius_of_curvature_invalid",
        message,
    )

class Sphere(torch.nn.Module):
    """
    拥有全局姿态、符号曲率半径与可选圆形 clear aperture 的球面

    Args:
        vertex: 曲面顶点的空间位置
        tangent_x: 表面局部 x 方向的 authored 切向量
        tangent_y: 表面局部 y 方向的 authored 切向量
        radius_of_curvature: 球面的有符号曲率半径
        clear_aperture_radius: 以表面局部坐标定义的通光孔径半径

    """

    vertex: torch.Tensor
    tangent_x: torch.Tensor
    tangent_y: torch.Tensor
    radius_of_curvature: torch.Tensor
    clear_aperture_radius: torch.Tensor

    def __init__(
        self,
        *,
        vertex: (
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
        radius_of_curvature: float | torch.nn.Parameter,
        clear_aperture_radius: float | torch.Tensor | None = None,
    ) -> None:

        super().__init__()
        _register_surface_pose(
            self,
            surface_name="sphere",
            origin=vertex,
            tangent_x=tangent_x,
            tangent_y=tangent_y,
        )
        self._register_radius(radius_of_curvature)
        self._register_aperture(
            "clear_aperture_radius",
            clear_aperture_radius,
        )

    @property
    def normal(self) -> torch.Tensor:
        """
        顶点处单位法线（tangent_x × tangent_y），定义面朝向与曲率中心方向

        Returns:
            球面顶点处的 float64 单位法线张量

        """

        return torch.linalg.cross(self.tangent_x, self.tangent_y)

    def forward(self) -> None:  # type: ignore[override]
        """
        球面是被动 state adapter，没有独立 forward 计算

        Raises:
            OpticalRuntimeError: 调用时的状态或拓扑不满足该 Interface 契约

        """

        raise _errors.OpticalRuntimeError(
            "sphere_has_no_forward_action",
            "Sphere 是被动 Surface adapter，由 refract/reflect action 消费，"
            "不暴露独立 forward",
        )

    def _encounter(
        self,
        ray_origin: torch.Tensor,
        ray_direction: torch.Tensor,
    ) -> SurfaceEncounter:
        device = ray_origin.device
        real_dtype = ray_origin.dtype
        vertex = self.vertex.to(device=device, dtype=real_dtype)
        tangent_x = self.tangent_x.to(device=device, dtype=real_dtype)
        tangent_y = self.tangent_y.to(device=device, dtype=real_dtype)
        normal = torch.linalg.cross(tangent_x, tangent_y)
        signed_radius = self.radius_of_curvature.to(
            device=device,
            dtype=real_dtype,
        )
        center = vertex + signed_radius * normal
        physical_radius = torch.abs(signed_radius)
        aperture = self._aperture_on(device=device, dtype=real_dtype)
        return sphere_encounter(
            ray_origin=ray_origin,
            ray_direction=ray_direction,
            sphere_center=center,
            sphere_vertex=vertex,
            sphere_tangent_x=tangent_x,
            sphere_tangent_y=tangent_y,
            physical_radius=physical_radius,
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

    def _register_radius(
        self,
        value: float | torch.nn.Parameter,
    ) -> None:
        if isinstance(value, torch.Tensor) and not isinstance(
            value,
            torch.nn.Parameter,
        ):
            message = (
                "radius_of_curvature 作为张量提供时必须是 torch.nn.Parameter；"
                f"若不需要训练请传 Python 标量，收到的是 {value!r}"
            )
            raise _errors.OpticalTypeError(
                "sphere_radius_of_curvature_invalid",
                message,
            )
        _require_valid_radius_of_curvature(value)
        if isinstance(value, torch.nn.Parameter):
            self.register_parameter("radius_of_curvature", value)
            return
        self.register_buffer(
            "radius_of_curvature",
            torch.tensor(float(value), dtype=torch.float64),
        )

    def _register_aperture(
        self,
        name: str,
        value: float | torch.Tensor | None,
    ) -> None:
        _register_hard_aperture(
            self,
            name=name,
            value=value,
            owner_identity=f"sphere_{name}_invalid",
        )

    def _validate_physical_state(self) -> None:
        _require_valid_surface_pose(
            surface_name="sphere",
            origin=self.vertex,
            tangent_x=self.tangent_x,
            tangent_y=self.tangent_y,
        )
        _require_valid_radius_of_curvature(self.radius_of_curvature)
        aperture = self._aperture_value
        if aperture is None:
            return
        _require_positive_finite_scalar(
            aperture,
            field_name="clear_aperture_radius",
            error_identity="sphere_clear_aperture_radius_invalid",
        )

    @property
    def _aperture_value(self) -> torch.Tensor | None:
        candidate = self._parameters.get("clear_aperture_radius")
        if candidate is not None:
            return candidate
        return self._buffers.get("clear_aperture_radius")

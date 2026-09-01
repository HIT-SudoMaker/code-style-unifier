from __future__ import annotations

import math
from typing import Literal

import torch

from chromatix_next._numerics.aperture import (
    circular_aperture_mask,
    square_aperture_mask,
)
from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

from .._grid_state import _fixed_output_grid_for, _GridState
from .._role_contract import _ElementRole
from ..field import OpticalField, _transform_field
from ..grid import SpatialGrid


def circular_pupil(
    field: OpticalField,
    *,
    grid: SpatialGrid,
    radius: float | torch.Tensor,
) -> OpticalField:
    """
    以闭圆孔径限制光场

    Args:
        field: 待处理的入射光场
        grid: 定义采样位置与间距的空间网格
        radius: 圆形通光孔径的半径

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    """
    return _apply_pupil(
        field,
        grid=grid,
        extent=radius,
        shape="circular",
    )

_PupilShape = Literal["circular", "square"]



class CircularPupil(torch.nn.Module):
    """
    固定闭圆孔径光瞳

    Args:
        radius: 圆形通光孔径的半径
        grid: 定义采样位置与间距的空间网格

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    radius: torch.Tensor

    def __init__(
        self,
        *,
        grid: SpatialGrid,
        radius: float | torch.Tensor,
    ) -> None:
        super().__init__()
        _validate_grid(grid, prefix="circular_pupil_")
        _validate_extent(
            radius,
            prefix="circular_pupil_",
            extent_name="radius",
        )
        self._grid_state = _GridState(grid)
        self.register_buffer(
            "radius",
            _fixed_extent(radius),
        )

    @property
    def role(self) -> _ElementRole:
        """
        元件角色字面量

        Returns:
            返回该组件声明的 Element 角色

        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        对输入光场施加圆孔径

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """
        return circular_pupil(
            field,
            grid=self.grid,
            radius=self.radius,
        )

    @property
    def grid(self) -> SpatialGrid:
        """
        圆孔径配准的空间网格；入射光场必须配准到同一网格

        Returns:
            与圆孔径掩膜配准的 SpatialGrid

        Raises:
            OpticalTypeError: 输入对象物理类型不满足该 Interface
            OpticalValueError: 输入数值/形状/精度/适用域不满足契约

        """
        _validate_extent(
            self.radius,
            prefix="circular_pupil_",
            extent_name="radius",
        )
        return self._grid_state.value

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        return _resolve_output_grid(
            input_grid=field.grid,
            registered_grid=self.grid,
            prefix="circular_pupil_",
        )


def square_pupil(
    field: OpticalField,
    *,
    grid: SpatialGrid,
    width: float | torch.Tensor,
) -> OpticalField:
    """
    以闭方孔径限制光场

    Args:
        field: 待处理的入射光场
        grid: 定义采样位置与间距的空间网格
        width: 方形通光孔径的边长

    Returns:
        返回应用孔径后的复振幅光场，保留输入采样与谱道语义

    """
    return _apply_pupil(
        field,
        grid=grid,
        extent=width,
        shape="square",
    )


class SquarePupil(torch.nn.Module):
    """
    固定闭方孔径光瞳

    Args:
        width: 方形通光孔径的边长
        grid: 定义采样位置与间距的空间网格

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    width: torch.Tensor

    def __init__(
        self,
        *,
        grid: SpatialGrid,
        width: float | torch.Tensor,
    ) -> None:
        super().__init__()
        _validate_grid(grid, prefix="square_pupil_")
        _validate_extent(
            width,
            prefix="square_pupil_",
            extent_name="width",
        )
        self._grid_state = _GridState(grid)
        self.register_buffer(
            "width",
            _fixed_extent(width),
        )

    @property
    def role(self) -> _ElementRole:
        """
        元件角色字面量

        Returns:
            返回该组件声明的 Element 角色

        """
        return "element"

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        对输入光场施加方孔径

        Args:
            field: 待处理的入射光场

        Returns:
            返回应用孔径后的复振幅光场，保留输入采样与谱道语义

        """
        return square_pupil(
            field,
            grid=self.grid,
            width=self.width,
        )

    @property
    def grid(self) -> SpatialGrid:
        """
        方孔径配准的空间网格；入射光场必须配准到同一网格

        Returns:
            与方孔径掩膜配准的 SpatialGrid

        Raises:
            OpticalTypeError: 输入对象物理类型不满足该 Interface
            OpticalValueError: 输入数值/形状/精度/适用域不满足契约

        """
        _validate_extent(
            self.width,
            prefix="square_pupil_",
            extent_name="width",
        )
        return self._grid_state.value

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        return _resolve_output_grid(
            input_grid=field.grid,
            registered_grid=self.grid,
            prefix="square_pupil_",
        )


def _apply_pupil(
    field: OpticalField,
    *,
    grid: SpatialGrid,
    extent: float | torch.Tensor,
    shape: _PupilShape,
) -> OpticalField:
    prefix = f"{shape}_pupil_"
    extent_name = "radius" if shape == "circular" else "width"
    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            prefix + "field_invalid",
            "光瞳只能作用于光场，"
            f"收到的是 {type(field).__name__}",
        )
    _validate_grid(grid, prefix=prefix)
    _validate_extent(
        extent,
        prefix=prefix,
        extent_name=extent_name,
    )
    _resolve_output_grid(
        input_grid=field.grid,
        registered_grid=grid,
        prefix=prefix,
    )
    aligned_extent = _aligned_extent(extent, field=field)
    mask_arguments = {
        "sample_counts": grid.sample_counts,
        "signed_spacing": grid.signed_spacing,
        "first_sample_position": grid.first_sample_position,
    }
    mask = (
        circular_aperture_mask(
            **mask_arguments,
            radius=aligned_extent,
        )
        if shape == "circular"
        else square_aperture_mask(
            **mask_arguments,
            width=aligned_extent,
        )
    )
    # 二元孔径掩膜 ⇒ 复包络逐点乘掩膜（掩膜 device/dtype 对齐到包络）
    return _transform_field(
        field,
        envelope=field.envelope * mask.to(
            device=field.envelope.device,
            dtype=field.envelope.dtype,
        ),
    )


def _validate_grid(
    grid: object,
    *,
    prefix: str,
) -> None:
    if not isinstance(grid, SpatialGrid):
        raise _errors.OpticalTypeError(
            prefix + "grid_invalid",
            "光瞳必须给出用于采样孔径的空间网格，"
            f"收到的是 {type(grid).__name__}",
        )


def _resolve_output_grid(
    *,
    input_grid: SpatialGrid,
    registered_grid: SpatialGrid,
    prefix: str,
) -> SpatialGrid:
    return _fixed_output_grid_for(
        input_grid,
        registered_grid,
        mismatch_identity=prefix + "grid_mismatch",
        mismatch_message=(
            "光瞳与入射光场必须配准在同一空间网格，"
            f"光瞳网格为 {registered_grid!r}，光场网格为 {input_grid!r}"
        ),
    )


def _validate_extent(
    extent: object,
    *,
    prefix: str,
    extent_name: str,
) -> None:
    if isinstance(extent, torch.nn.Parameter):
        raise _errors.OpticalTypeError(
            prefix + extent_name + "_invalid",
            "二元光瞳几何是固定状态，不接受可训练 Parameter",
        )
    if isinstance(extent, torch.Tensor):
        if extent.requires_grad:
            raise _errors.OpticalTypeError(
                prefix + extent_name + "_invalid",
                "二元光瞳几何是固定状态，不接受 requires_grad=True 的张量",
            )
        is_structure_invalid = (
            extent.dim() != 0
            or extent.dtype is not torch.float64
        )
        is_value_invalid = False
        if not is_structure_invalid:
            is_finite = torch.isfinite(extent)
            is_positive = extent > 0.0
            if is_value_readable(is_finite):
                is_value_invalid = not bool(is_finite) or not bool(is_positive)
        if not is_structure_invalid and not is_value_invalid:
            return
    elif (
        not isinstance(extent, bool)
        and isinstance(extent, (int, float))
        and math.isfinite(extent)
        and extent > 0.0
    ):
        return
    raise _errors.OpticalValueError(
        prefix + extent_name + "_invalid",
        "光瞳孔径尺寸必须是正的有限实数长度，"
        f"收到的是 {extent!r}",
    )


def _fixed_extent(extent: float | torch.Tensor) -> torch.Tensor:
    if isinstance(extent, torch.Tensor):
        return extent
    return torch.tensor(extent, dtype=torch.float64)


def _aligned_extent(
    extent: float | torch.Tensor,
    *,
    field: OpticalField,
) -> torch.Tensor:
    if isinstance(extent, torch.Tensor):
        return extent.to(device=field.envelope.device)
    return torch.tensor(
        extent,
        device=field.envelope.device,
        dtype=field.envelope.real.dtype,
    )

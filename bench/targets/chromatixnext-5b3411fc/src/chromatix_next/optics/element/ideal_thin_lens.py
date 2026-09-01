from __future__ import annotations

import math

import torch

from chromatix_next._numerics.thin_transmission import ideal_thin_lens_phase_factor
from chromatix_next._tensors import (
    is_nonzero_finite_fixed_double_scalar,
    is_value_readable,
)
import chromatix_next.errors as _errors

from .._grid_state import _fixed_output_grid_for, _GridState
from .._role_contract import _ElementRole
from ..field import OpticalField, _transform_field
from ..grid import SpatialGrid

LensCenter = tuple[
    float | torch.Tensor,
    float | torch.Tensor,
]



def _validate_grid(grid: object) -> None:
    if not isinstance(grid, SpatialGrid):
        raise _errors.OpticalTypeError(
            "ideal_thin_lens_grid_invalid",
            "理想薄透镜必须配准到一个空间网格，"
            f"收到的是 {type(grid).__name__}",
        )


def _validate_focal_length(focal_length: object) -> None:
    if isinstance(focal_length, torch.Tensor) and (
        focal_length.dtype is not torch.float64
    ):
        raise _errors.OpticalValueError(
            "ideal_thin_lens_focal_length_invalid",
            "焦距必须是以米计的 float64 实数标量（固定双精度核，"
            "不再静默镜像输入 dtype——请在上游以 float64 构造），"
            f"收到的精度是 {focal_length.dtype}",
        )
    if is_nonzero_finite_fixed_double_scalar(focal_length):
        return
    raise _errors.OpticalValueError(
        "ideal_thin_lens_focal_length_invalid",
        "焦距必须是以米计的有限非零实数标量",
    )


def _validate_lens_center(lens_center: object) -> None:
    if not isinstance(lens_center, tuple) or len(lens_center) != 2:
        raise _errors.OpticalValueError(
            "ideal_thin_lens_center_invalid",
            "透镜中心必须是纵横两个有限实数米坐标",
        )
    for value in lens_center:
        if isinstance(value, torch.Tensor):
            if isinstance(value, torch.nn.Parameter) or value.requires_grad:
                raise _errors.OpticalValueError(
                    "ideal_thin_lens_center_trainable",
                    "理想薄透镜中心是固定坐标，不能接收 Parameter "
                    "或 requires_grad=True 的张量",
                )
            is_structure_invalid = (
                value.dim() != 0
                or value.dtype is not torch.float64
            )
            is_finite = torch.isfinite(value)
            if is_structure_invalid or (
                is_value_readable(is_finite)
                and not bool(is_finite)
            ):
                raise _errors.OpticalValueError(
                    "ideal_thin_lens_center_invalid",
                    "透镜中心必须是纵横两个有限实数米坐标",
                )
        elif (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise _errors.OpticalValueError(
                "ideal_thin_lens_center_invalid",
                "透镜中心必须是纵横两个有限实数米坐标",
            )


def _scalar_tensor(
    value: float | torch.Tensor,
    *,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    return (
        value.to(device=device)
        if isinstance(value, torch.Tensor)
        else torch.tensor(value, device=device, dtype=dtype)
    )


def _fixed_lens_center_coordinate(
    value: float | torch.Tensor,
) -> torch.Tensor:
    if isinstance(value, torch.Tensor):
        return value
    return torch.tensor(value, dtype=torch.float64)


def ideal_thin_lens(
    field: OpticalField,
    *,
    grid: SpatialGrid,
    focal_length: float | torch.Tensor,
    lens_center: LensCenter = (0.0, 0.0),
) -> OpticalField:
    """
    以 Goodman 负二次相位施加理想薄透镜

    Args:
        field: 待处理的入射光场
        grid: 定义采样位置与间距的空间网格
        focal_length: 薄透镜或聚焦模型的焦距
        lens_center: 薄透镜中心在网格坐标中的位置

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

        OpticalValueError: 输入数值/形状/精度/适用域不满足契约
    """

    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "ideal_thin_lens_field_invalid",
            "理想薄透镜只能施加于光场，"
            f"收到的是 {type(field).__name__}",
        )
    _validate_grid(grid)
    _resolve_output_grid(
        input_grid=field.grid,
        registered_grid=grid,
    )
    _validate_focal_length(focal_length)
    _validate_lens_center(lens_center)
    real_dtype = field.envelope.real.dtype
    device = field.envelope.device
    wavelengths = torch.tensor(
        field.spectrum.wavelengths,
        device=device,
        dtype=real_dtype,
    )
    phase_factor = ideal_thin_lens_phase_factor(
        sample_counts=grid.sample_counts,
        signed_spacing=grid.signed_spacing,
        first_sample_position=grid.first_sample_position,
        wavelengths=wavelengths,
        refractive_indices=field.medium.refractive_index(
            wavelengths,
        ).to(device=device, dtype=real_dtype),
        focal_length=_scalar_tensor(
            focal_length,
            device=device,
            dtype=real_dtype,
        ),
        lens_center=(
            _scalar_tensor(
                lens_center[0],
                device=device,
                dtype=real_dtype,
            ),
            _scalar_tensor(
                lens_center[1],
                device=device,
                dtype=real_dtype,
            ),
        ),
    ).unsqueeze(1)
    return _transform_field(
        field,
        envelope=field.envelope * phase_factor,
    )


class IdealThinLens(torch.nn.Module):
    """
    拥有焦距、中心和配准网格的近轴理想薄透镜

    Args:
        focal_length: 薄透镜或聚焦模型的焦距
        grid: 定义采样位置与间距的空间网格
        lens_center: 薄透镜中心在网格坐标中的位置

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    focal_length: torch.Tensor
    lens_center_x: torch.Tensor
    lens_center_y: torch.Tensor

    def __init__(
        self,
        *,
        grid: SpatialGrid,
        focal_length: float | torch.Tensor,
        lens_center: LensCenter = (0.0, 0.0),
    ) -> None:

        super().__init__()
        _validate_grid(grid)
        _validate_focal_length(focal_length)
        _validate_lens_center(lens_center)
        self._grid_state = _GridState(grid)
        if isinstance(focal_length, torch.nn.Parameter):
            self.register_parameter("focal_length", focal_length)
        elif isinstance(focal_length, torch.Tensor):
            self.register_buffer(
                "focal_length",
                focal_length.to(dtype=torch.float64),
            )
        else:
            self.register_buffer(
                "focal_length",
                torch.tensor(focal_length, dtype=torch.float64),
            )
        self.register_buffer(
            "lens_center_y",
            _fixed_lens_center_coordinate(lens_center[0]),
        )
        self.register_buffer(
            "lens_center_x",
            _fixed_lens_center_coordinate(lens_center[1]),
        )

    @property
    def role(self) -> _ElementRole:
        """
        元件角色字面量

        Returns:
            返回该组件声明的 Element 角色

        """

        return "element"

    @property
    def grid(self) -> SpatialGrid:
        """
        薄透镜配准的空间网格；入射光场必须配准到同一网格

        Returns:
            与薄透镜相位图配准的 SpatialGrid

        Raises:
            OpticalValueError: 输入数值/形状/精度/适用域不满足契约

        """

        _validate_lens_center(self.lens_center)
        return self._grid_state.value

    @property
    def lens_center(self) -> LensCenter:
        """
        透镜纵横中心 (纵向 y, 横向 x)，单位米

        由两个固定 Buffer 持有，构造期校验为有限实数且不可训练，
        故参与普通 Buffer 生命周期且运行期不可重赋。

        Returns:
            返回透镜中心在空间网格坐标中的二维位置

        """

        return (self.lens_center_y, self.lens_center_x)

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        对入射光场施加 Goodman 负二次相位的薄透镜作用

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """

        return ideal_thin_lens(
            field,
            grid=self.grid,
            focal_length=self.focal_length,
            lens_center=self.lens_center,
        )

    def _validate_physical_state(self) -> None:
        _validate_lens_center(self.lens_center)
        _validate_focal_length(self.focal_length)

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        return _resolve_output_grid(
            input_grid=field.grid,
            registered_grid=self.grid,
        )


def _resolve_output_grid(
    *,
    input_grid: SpatialGrid,
    registered_grid: SpatialGrid,
) -> SpatialGrid:
    return _fixed_output_grid_for(
        input_grid,
        registered_grid,
        mismatch_identity="ideal_thin_lens_grid_mismatch",
        mismatch_message="理想薄透镜只能作用于它配准的空间网格",
    )

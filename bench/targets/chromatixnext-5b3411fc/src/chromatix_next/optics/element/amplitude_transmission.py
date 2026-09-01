from __future__ import annotations

import torch

from chromatix_next._tensors import is_value_readable
import chromatix_next.errors as _errors

from .._grid_state import _fixed_output_grid_for, _GridState
from .._role_contract import _ElementRole
from ..field import OpticalField, _transform_field
from ..grid import SpatialGrid


def _validate_grid(grid: object) -> None:
    if not isinstance(grid, SpatialGrid):
        raise _errors.OpticalTypeError(
            "amplitude_transmission_map_grid_invalid",
            "振幅透射图必须配准到一个空间网格，"
            f"收到的是 {type(grid).__name__}",
        )

def _validate_amplitude(
    grid: SpatialGrid,
    amplitude_transmission: object,
) -> None:
    if not isinstance(amplitude_transmission, torch.Tensor):
        raise _errors.OpticalTypeError(
            "amplitude_transmission_map_values_invalid",
            "振幅透射图必须以张量逐点给出，"
            f"收到的是 {type(amplitude_transmission).__name__}",
        )
    if (
        torch.is_complex(amplitude_transmission)
        or not amplitude_transmission.is_floating_point()
        or amplitude_transmission.dtype is not torch.float64
    ):
        raise _errors.OpticalValueError(
            "amplitude_transmission_map_values_invalid",
            "振幅透射图必须是连续的 float64 实数浮点张量（固定双精度核，"
            "不再静默镜像输入 dtype——请在上游以 float64 构造）",
        )
    if tuple(amplitude_transmission.shape) != grid.sample_counts:
        raise _errors.OpticalValueError(
            "amplitude_transmission_map_shape_mismatch",
            "振幅透射图必须逐点配准到空间网格，"
            f"网格为 {grid.sample_counts}，图形状为 "
            f"{tuple(amplitude_transmission.shape)}",
        )
    is_finite = torch.isfinite(amplitude_transmission).all()
    if is_value_readable(is_finite) and not bool(is_finite):
        raise _errors.OpticalValueError(
            "amplitude_transmission_map_values_invalid",
            "振幅透射图的每个采样点都必须有限",
        )
    is_below_range = torch.any(amplitude_transmission < 0)
    is_above_range = torch.any(amplitude_transmission > 1)
    if is_value_readable(is_below_range) and (
        bool(is_below_range)
        or bool(is_above_range)
    ):
        raise _errors.OpticalValueError(
            "amplitude_transmission_map_values_invalid",
            "被动振幅透射必须位于闭区间 [0, 1]",
        )


def amplitude_transmission_map(
    field: OpticalField,
    *,
    grid: SpatialGrid,
    amplitude_transmission: torch.Tensor | torch.nn.Parameter,
) -> OpticalField:
    """
    以配准的无量纲振幅透射图逐点调制光场

    Args:
        field: 待处理的入射光场
        grid: 定义采样位置与间距的空间网格
        amplitude_transmission: 配准到网格、取值位于闭区间 [0, 1] 的振幅透射图

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

        OpticalValueError: 输入数值/形状/精度/适用域不满足契约
    """

    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "amplitude_transmission_map_field_invalid",
            "振幅透射图只能施加于光场，"
            f"收到的是 {type(field).__name__}",
        )
    _validate_grid(grid)
    _resolve_output_grid(
        input_grid=field.grid,
        registered_grid=grid,
    )
    _validate_amplitude(grid, amplitude_transmission)
    amplitude = amplitude_transmission.to(
        device=field.envelope.device,
        dtype=field.envelope.real.dtype,
    )
    # 振幅透射 ⇒ 复包络逐点乘已配对的实振幅图（dtype/device 已对齐到包络）
    return _transform_field(
        field,
        envelope=field.envelope * amplitude,
    )


class AmplitudeTransmissionMap(torch.nn.Module):
    """
    拥有配准网格和无量纲振幅透射图的光学元件

    Args:
        amplitude_transmission: 配准到网格、取值位于闭区间 [0, 1] 的振幅透射图
        grid: 定义采样位置与间距的空间网格

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    amplitude_transmission: torch.Tensor

    def __init__(
        self,
        *,
        grid: SpatialGrid,
        amplitude_transmission: torch.Tensor | torch.nn.Parameter,
    ) -> None:

        super().__init__()
        _validate_grid(grid)
        _validate_amplitude(grid, amplitude_transmission)
        self._grid_state = _GridState(grid)
        if isinstance(amplitude_transmission, torch.nn.Parameter):
            self.register_parameter(
                "amplitude_transmission",
                amplitude_transmission,
            )
        else:
            self.register_buffer(
                "amplitude_transmission",
                amplitude_transmission.to(dtype=torch.float64),
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
        振幅透射图配准的空间网格；入射光场必须配准到同一网格

        Returns:
            与振幅透射图配准的 SpatialGrid

        """

        return self._grid_state.value

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        对入射光场包络逐点乘注册的振幅透射图

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """

        return amplitude_transmission_map(
            field,
            grid=self.grid,
            amplitude_transmission=self.amplitude_transmission,
        )

    def _validate_physical_state(self) -> None:
        _validate_amplitude(
            self.grid,
            self.amplitude_transmission,
        )

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
        mismatch_identity="amplitude_transmission_map_grid_mismatch",
        mismatch_message="振幅透射图只能作用于它配准的空间网格",
    )

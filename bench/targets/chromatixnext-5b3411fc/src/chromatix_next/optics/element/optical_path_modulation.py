from __future__ import annotations

import torch

from chromatix_next._numerics.optical_path_reference import (
    accumulate_optical_path_lengths,
)
from chromatix_next._numerics.thin_transmission import optical_path_phase_factor
from chromatix_next._tensors import is_finite_fixed_double_scalar, is_value_readable
import chromatix_next.errors as _errors

from .._grid_state import _fixed_output_grid_for, _GridState
from .._role_contract import _ElementRole
from ..field import OpticalField, OpticalPathReference, _transform_field
from ..grid import SpatialGrid


def _validate_grid(grid: object) -> None:
    if not isinstance(grid, SpatialGrid):
        raise _errors.OpticalTypeError(
            "optical_path_modulation_grid_invalid",
            "光程变化图必须配准到一个空间网格，"
            f"收到的是 {type(grid).__name__}",
        )

def _validate_variation(
    grid: SpatialGrid,
    optical_path_variation: object,
) -> None:
    if not isinstance(optical_path_variation, torch.Tensor):
        raise _errors.OpticalTypeError(
            "optical_path_modulation_variation_invalid",
            "光程变化必须以张量逐点给出，"
            f"收到的是 {type(optical_path_variation).__name__}",
        )
    if optical_path_variation.dtype is not torch.float64:
        raise _errors.OpticalValueError(
            "optical_path_modulation_variation_invalid",
            "光程变化必须是以米计的 float64 实数浮点张量（固定双精度核，"
            "不再静默镜像输入 dtype——请在上游以 float64 构造），"
            f"收到的精度是 {optical_path_variation.dtype}",
        )
    if tuple(optical_path_variation.shape) != grid.sample_counts:
        raise _errors.OpticalValueError(
            "optical_path_modulation_variation_shape_mismatch",
            "光程变化图必须逐点配准到空间网格，"
            f"网格为 {grid.sample_counts}，图形状为 "
            f"{tuple(optical_path_variation.shape)}",
        )
    is_finite = torch.isfinite(optical_path_variation).all()
    if is_value_readable(is_finite) and not bool(is_finite):
        raise _errors.OpticalValueError(
            "optical_path_modulation_variation_invalid",
            "光程变化图的每个采样点都必须有限",
        )


def _validate_baseline(optical_path_baseline: object) -> None:
    if is_finite_fixed_double_scalar(optical_path_baseline):
        return
    raise _errors.OpticalValueError(
        "optical_path_modulation_baseline_invalid",
        "光程基线必须是以米计的有限 float64 实数标量（固定双精度核，"
        "不再静默升精度——张量须已是零维 float64）",
    )


def optical_path_modulation(
    field: OpticalField,
    *,
    grid: SpatialGrid,
    optical_path_variation: torch.Tensor | torch.nn.Parameter,
    optical_path_baseline: float | torch.Tensor = 0.0,
) -> OpticalField:
    """
    以空间光程变化调制相位并以均匀基线移动光程参考

    Args:
        field: 待处理的入射光场
        grid: 定义采样位置与间距的空间网格
        optical_path_variation: 配准到网格的逐点光程变化
        optical_path_baseline: 从逐点变化中分离的公共光程基线

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约

        OpticalValueError: 输入数值/形状/精度/适用域不满足契约
    """

    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "optical_path_modulation_field_invalid",
            "光程调制只能施加于光场，"
            f"收到的是 {type(field).__name__}",
        )
    _validate_grid(grid)
    _resolve_output_grid(
        input_grid=field.grid,
        registered_grid=grid,
    )
    _validate_variation(grid, optical_path_variation)
    _validate_baseline(optical_path_baseline)
    real_dtype = field.envelope.real.dtype
    device = field.envelope.device
    wavelengths = torch.tensor(
        field.spectrum.wavelengths,
        device=device,
        dtype=real_dtype,
    )
    variation = optical_path_variation.to(device=device)
    return _transform_field(
        field,
        envelope=field.envelope
        * optical_path_phase_factor(
            wavelengths=wavelengths,
            optical_path_variation=variation,
        ).unsqueeze(1),
        path_reference=OpticalPathReference(
            lengths=accumulate_optical_path_lengths(
                field.path_reference.lengths,
                optical_path_baseline,
                device=device,
            ),
        ),
    )


class OpticalPathModulation(torch.nn.Module):
    """
    拥有空间光程变化与均匀光程基线的光学元件

    Args:
        optical_path_baseline: 从逐点变化中分离的公共光程基线
        optical_path_variation: 配准到网格的逐点光程变化
        grid: 定义采样位置与间距的空间网格

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    optical_path_baseline: torch.Tensor
    optical_path_variation: torch.Tensor

    def __init__(
        self,
        *,
        grid: SpatialGrid,
        optical_path_variation: torch.Tensor | torch.nn.Parameter,
        optical_path_baseline: float | torch.Tensor = 0.0,
    ) -> None:

        super().__init__()
        _validate_grid(grid)
        _validate_variation(grid, optical_path_variation)
        _validate_baseline(optical_path_baseline)
        self._grid_state = _GridState(grid)
        if isinstance(optical_path_variation, torch.nn.Parameter):
            self.register_parameter(
                "optical_path_variation",
                optical_path_variation,
            )
        else:
            self.register_buffer(
                "optical_path_variation",
                optical_path_variation,
            )
        if isinstance(optical_path_baseline, torch.nn.Parameter):
            self.register_parameter(
                "optical_path_baseline",
                optical_path_baseline,
            )
        elif isinstance(optical_path_baseline, torch.Tensor):
            self.register_buffer(
                "optical_path_baseline",
                optical_path_baseline,
            )
        else:
            self.register_buffer(
                "optical_path_baseline",
                torch.tensor(
                    optical_path_baseline,
                    dtype=torch.float64,
                ),
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
        光程变化图配准的空间网格；入射光场必须配准到同一网格

        Returns:
            与光程变化图配准的 SpatialGrid

        """

        return self._grid_state.value

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        对入射光场施加逐点空间光程相位并按基线平移光程参考

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """

        return optical_path_modulation(
            field,
            grid=self.grid,
            optical_path_variation=self.optical_path_variation,
            optical_path_baseline=self.optical_path_baseline,
        )

    def _validate_physical_state(self) -> None:
        _validate_variation(
            self.grid,
            self.optical_path_variation,
        )
        _validate_baseline(self.optical_path_baseline)

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
        mismatch_identity="optical_path_modulation_grid_mismatch",
        mismatch_message="光程变化图只能作用于它配准的空间网格",
    )

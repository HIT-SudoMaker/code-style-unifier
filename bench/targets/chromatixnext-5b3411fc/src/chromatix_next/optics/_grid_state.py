from __future__ import annotations

import torch

import chromatix_next.errors as _errors

from .grid import SpatialGrid, _is_centered_grid


class _GridState(torch.nn.Module):
    """
    将空间网格张量纳入标准 PyTorch 状态生命周期

    """

    def __init__(self, grid: SpatialGrid) -> None:
        super().__init__()
        if not isinstance(grid, SpatialGrid):
            raise _errors.OpticalValueError(
                "grid_state_grid_invalid",
                "网格状态适配器只接受空间网格物理值",
            )
        self.sample_counts = grid.sample_counts
        self.orientation = grid.orientation
        self._is_centered = _is_centered_grid(grid)
        self._register_scalar("sample_spacing_y", grid.sample_spacing[0])
        self._register_scalar("sample_spacing_x", grid.sample_spacing[1])
        if not self._is_centered:
            first_y, first_x = grid.first_sample_position
            self._register_scalar("first_sample_position_y", first_y)
            self._register_scalar("first_sample_position_x", first_x)

    @property
    def value(self) -> SpatialGrid:
        """
        由当前登记状态重建空间网格

        """
        spacing = (
            self._registered_scalar("sample_spacing_y"),
            self._registered_scalar("sample_spacing_x"),
        )
        if self._is_centered:
            return SpatialGrid.centered(
                sample_counts=self.sample_counts,
                sample_spacing=spacing,
                orientation=self.orientation,
            )
        return SpatialGrid(
            sample_counts=self.sample_counts,
            sample_spacing=spacing,
            first_sample_position=(
                self._registered_scalar("first_sample_position_y"),
                self._registered_scalar("first_sample_position_x"),
            ),
            orientation=self.orientation,
        )

    def _register_scalar(self, name: str, value: torch.Tensor) -> None:
        if value.requires_grad and not value.is_leaf:
            raise _errors.OpticalValueError(
                "grid_state_nonleaf_tensor_unsupported",
                "模块拥有的网格不能长期保存带计算公式的非叶可微张量；"
                "中心网格请把独立采样间距写成 Parameter，显式网格请把间距和"
                "首样本位置写成 Parameter 或叶张量，使每次运行都读取当前状态",
            )
        if isinstance(value, torch.nn.Parameter):
            self.register_parameter(name, value)
        else:
            self.register_buffer(name, value)

    def _registered_scalar(self, name: str) -> torch.Tensor:
        parameter = self._parameters.get(name)
        if parameter is not None:
            return parameter
        buffer = self._buffers.get(name)
        assert buffer is not None
        return buffer


def _fixed_output_grid_for(
    input_grid: SpatialGrid,
    registered_grid: SpatialGrid,
    *,
    mismatch_identity: str,
    mismatch_message: str,
) -> SpatialGrid:
    if not input_grid.is_inference_compatible_with(registered_grid):
        raise _errors.OpticalValueError(
            mismatch_identity,
            mismatch_message,
        )
    return input_grid

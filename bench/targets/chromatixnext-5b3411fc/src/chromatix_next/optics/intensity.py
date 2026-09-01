from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import torch

import chromatix_next.errors as _errors

from .._tensors import is_value_readable
from .field import FieldNormalization
from .grid import SpatialGrid


@dataclass(frozen=True, slots=True, eq=False)
class Intensity:
    """
    承载与空间网格配准的实值光强

    Attributes:
        values: 按批量轴和末尾两个空间轴排列的非负 float64 强度
        grid: 强度样本所在的空间网格
        normalization: 数值对应相对强度或辐照度的归一化语义

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    values: torch.Tensor
    grid: SpatialGrid
    normalization: FieldNormalization

    def __post_init__(self) -> None:
        if not isinstance(self.values, torch.Tensor):
            raise _errors.OpticalTypeError(
                "intensity_values_invalid",
                "光强的数值必须是张量，"
                f"收到的是 {type(self.values).__name__}",
            )
        if (
            not torch.is_complex(self.values)
            and self.values.dtype is not torch.float64
        ):
            raise _errors.OpticalTypeError(
                "intensity_values_dtype_invalid",
                "光强数值固定以 float64 承载（ADR-0005 固定双精度核），"
                "单精度实光强不再被支持，请在上游以 float64 构造；"
                f"收到的是 {self.values.dtype}",
            )
        if torch.is_complex(self.values):
            raise _errors.OpticalValueError(
                "intensity_values_not_real",
                "光强是实数可观测量，复振幅要先取模平方再构造光强，"
                f"收到的是 {self.values.dtype}",
            )
        if self.values.dim() < 2:
            raise _errors.OpticalValueError(
                "intensity_values_rank_invalid",
                "光强至少要有高度与宽度两个空间轴，批量轴排在它们之前，"
                f"收到的形状是 {tuple(self.values.shape)}",
            )
        # meta 同样执行取值谓词张量核以进入内存轨迹，只跳过布尔读取
        is_finite = torch.isfinite(self.values).all()
        if is_value_readable(is_finite):
            if not bool(is_finite):
                raise _errors.OpticalValueError(
                    "intensity_values_nonfinite",
                    "光强处处都要是有限值，无穷或非数说明上游归一化已经发散，"
                    f"收到的形状是 {tuple(self.values.shape)}",
                )
        is_nonnegative = torch.all(self.values >= 0)
        if is_value_readable(is_nonnegative):
            if not bool(is_nonnegative):
                raise _errors.OpticalValueError(
                    "intensity_values_negative",
                    "光强是非负可观测量，负值说明它不是由光场取模平方得来的，"
                    f"收到的形状是 {tuple(self.values.shape)}",
                )
        if not isinstance(self.grid, SpatialGrid):
            raise _errors.OpticalTypeError(
                "intensity_grid_invalid",
                "光强必须携带它所在的横向网格，"
                f"收到的是 {type(self.grid).__name__}",
            )
        if not isinstance(self.normalization, FieldNormalization):
            raise _errors.OpticalTypeError(
                "intensity_normalization_invalid",
                "光强的归一化决定单位是相对量还是瓦每平方米，"
                f"收到的是 {type(self.normalization).__name__}",
            )
        if self.values.shape[-2] != self.grid.sample_counts[0]:
            raise _errors.OpticalValueError(
                "intensity_height_axis_mismatch",
                "光强在高度方向的样本数必须与所在网格一致，"
                f"收到的是 {self.values.shape[-2]}，"
                f"网格给出的是 {self.grid.sample_counts[0]}",
            )
        if self.values.shape[-1] != self.grid.sample_counts[1]:
            raise _errors.OpticalValueError(
                "intensity_width_axis_mismatch",
                "光强在宽度方向的样本数必须与所在网格一致，"
                f"收到的是 {self.values.shape[-1]}，"
                f"网格给出的是 {self.grid.sample_counts[1]}",
            )

    @property
    def batch_shape(self) -> tuple[int, ...]:
        """
        返回空间轴之前的批量维形状

        Returns:
            空间轴之前的批量维长度元组

        """
        return tuple(self.values.shape[:-2])

    @property
    def spectral_reduction(self) -> Literal["weighted_sum"]:
        """
        返回探测所采用的显式光谱约减：按 Spectrum 权重求和

        Returns:
            返回强度值的谱道归一化数量

        """

        return "weighted_sum"

    @property
    def units(
        self,
    ) -> Literal["dimensionless", "watts_per_square_metre"]:
        """
        返回由光场归一化唯一决定的光强单位

        Returns:
            返回强度值的单位标识

        """

        if self.normalization is FieldNormalization.POWER:
            return "watts_per_square_metre"
        return "dimensionless"

    @property
    def axis_meaning(self) -> tuple[str, ...]:
        """
        返回批量轴及高度、宽度空间轴的自然语言含义

        Returns:
            批量、高度、宽度轴含义的字符串元组

        """

        batch_axes = tuple(
            f"batch_{axis}"
            for axis in range(len(self.batch_shape))
        )
        return batch_axes + ("height", "width")

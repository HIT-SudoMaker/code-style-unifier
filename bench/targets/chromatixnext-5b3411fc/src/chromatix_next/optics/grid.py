from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import TypeAlias

import torch

import chromatix_next.errors as _errors

_INCREASING = "increasing"

_DECREASING = "decreasing"

_SUPPORTED_ORIENTATIONS = (_INCREASING, _DECREASING)

_GRID_REAL_DTYPE = torch.float64

_RealScalar: TypeAlias = int | float | torch.Tensor

_ScalarPair: TypeAlias = tuple[_RealScalar, _RealScalar]

_TensorPair: TypeAlias = tuple[torch.Tensor, torch.Tensor]

@dataclass(frozen=True, slots=True, eq=False, init=False)
class SpatialGrid:
    """
    已配准的均匀笛卡尔横向采样网格

    Args:
        sample_counts: 沿 y 与 x 方向的采样点数
        sample_spacing: 沿 y 与 x 方向以米表示的采样间距
        orientation: 网格切向基相对实验坐标的空间姿态
        first_sample_position: 网格首个样本沿 y 与 x 方向的物理位置

    Raises:
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    sample_counts: tuple[int, int]
    sample_spacing: _TensorPair
    orientation: tuple[str, str]
    _first_sample_position: _TensorPair | None = field(
        repr=False,
    )

    def __init__(
        self,
        *,
        sample_counts: tuple[int, int],
        sample_spacing: _ScalarPair,
        first_sample_position: _ScalarPair,
        orientation: tuple[str, str] = (_INCREASING, _INCREASING),
    ) -> None:
        _validate_sample_counts(sample_counts)
        _validate_orientation(orientation)
        normalized_spacing = _normalize_scalar_pair(
            sample_spacing,
            identity="spatial_grid_sample_spacing_invalid",
            nonfinite_identity="spatial_grid_sample_spacing_nonfinite",
            quantity_name="采样间距",
            is_positive=True,
        )
        normalized_position = _normalize_scalar_pair(
            first_sample_position,
            identity="spatial_grid_first_sample_position_invalid",
            nonfinite_identity=(
                "spatial_grid_first_sample_position_nonfinite"
            ),
            quantity_name="首样本位置",
            is_positive=False,
        )
        _validate_shared_placement(
            (*normalized_spacing, *normalized_position),
        )
        object.__setattr__(self, "sample_counts", sample_counts)
        object.__setattr__(self, "sample_spacing", normalized_spacing)
        object.__setattr__(self, "orientation", orientation)
        object.__setattr__(
            self,
            "_first_sample_position",
            normalized_position,
        )

    @classmethod
    def centered(
        cls,
        *,
        sample_counts: tuple[int, int],
        sample_spacing: _ScalarPair,
        orientation: tuple[str, str] = (_INCREASING, _INCREASING),
    ) -> SpatialGrid:
        """
        构造每轴索引 N // 2 位于坐标原点的空间网格

        Args:
            sample_counts: 沿 y 与 x 方向的采样点数
            sample_spacing: 沿 y 与 x 方向以米表示的采样间距
            orientation: 网格切向基相对实验坐标的空间姿态

        Returns:
            按给定姿态和采样间距构造的 SpatialGrid

        Raises:
            OpticalValueError: 输入数值/形状/精度/适用域不满足契约

        """
        _validate_sample_counts(sample_counts)
        _validate_orientation(orientation)
        normalized_spacing = _normalize_scalar_pair(
            sample_spacing,
            identity="spatial_grid_sample_spacing_invalid",
            nonfinite_identity="spatial_grid_sample_spacing_nonfinite",
            quantity_name="采样间距",
            is_positive=True,
        )
        return _new_spatial_grid(
            sample_counts=sample_counts,
            sample_spacing=normalized_spacing,
            first_sample_position=None,
            orientation=orientation,
        )

    @property
    def first_sample_position(self) -> _TensorPair:
        """
        返回纵向与横向首样本坐标

        Returns:
            (y, x) 首样本坐标的 float64 张量

        """
        if self._first_sample_position is not None:
            return self._first_sample_position
        signs = (
            1.0 if self.orientation[0] == _INCREASING else -1.0,
            1.0 if self.orientation[1] == _INCREASING else -1.0,
        )
        return (
            -signs[0]
            * (self.sample_counts[0] // 2)
            * self.sample_spacing[0],
            -signs[1]
            * (self.sample_counts[1] // 2)
            * self.sample_spacing[1],
        )

    @property
    def signed_spacing(self) -> _TensorPair:
        """
        返回带坐标朝向符号的采样步进

        Returns:
            (dy, dx) 带方向采样间距的 float64 张量

        """
        return (
            self.sample_spacing[0]
            if self.orientation[0] == _INCREASING
            else -self.sample_spacing[0],
            self.sample_spacing[1]
            if self.orientation[1] == _INCREASING
            else -self.sample_spacing[1],
        )

    @property
    def cell_area(self) -> torch.Tensor:
        """
        返回横向采样单元面积

        Returns:
            每个采样单元面积的 float64 标量张量

        """
        return self.sample_spacing[0] * self.sample_spacing[1]

    def is_physically_equivalent_to(self, other: object) -> bool:
        """
        判断另一网格是否描述完全相同的采样坐标

        真实张量脱离自动微分图后作精确比较。meta 张量没有可读值；结构一致时，
        同别名可直接证明相等，其余留给进入 meta 推导前的真实物理检查。

        Args:
            other: 要与当前网格比较采样与姿态身份的对象

        Returns:
            返回两个网格在采样数量、间距、姿态与首样本位置上的物理等价性

        """
        if not isinstance(other, SpatialGrid):
            return False
        if (
            self.sample_counts != other.sample_counts
            or self.orientation != other.orientation
        ):
            return False
        own_values = self.sample_spacing
        other_values = other.sample_spacing
        if not (_is_centered_grid(self) and _is_centered_grid(other)):
            own_values = (*own_values, *self.first_sample_position)
            other_values = (*other_values, *other.first_sample_position)
        for own_value, other_value in zip(
            own_values,
            other_values,
            strict=True,
        ):
            if own_value is other_value:
                continue
            if own_value.is_meta or other_value.is_meta:
                return False
            if not torch.equal(
                own_value.detach().to(device="cpu"),
                other_value.detach().to(device="cpu"),
            ):
                return False
        return True

    def is_inference_compatible_with(self, other: SpatialGrid) -> bool:
        """
        判断另一网格在隔离 meta 推导前是否结构兼容

        采样数与朝向必须一致；坐标全为真实张量时回归精确物理等价，
        任一坐标为 meta 张量时放行，留给真实物理检查。

        Args:
            other: 要与当前网格比较采样与姿态身份的对象

        Returns:
            返回两个网格能否在当前推导中共享采样语义

        """
        if (
            self.sample_counts != other.sample_counts
            or self.orientation != other.orientation
        ):
            return False
        own_coordinates = (
            self.sample_spacing
            if _is_centered_grid(self)
            else (*self.sample_spacing, *self.first_sample_position)
        )
        other_coordinates = (
            other.sample_spacing
            if _is_centered_grid(other)
            else (*other.sample_spacing, *other.first_sample_position)
        )
        if any(
            coordinate.is_meta
            for coordinate in (*own_coordinates, *other_coordinates)
        ):
            return True
        return self.is_physically_equivalent_to(other)

    def to(
        self,
        *,
        device: torch.device | str,
        dtype: torch.dtype,
    ) -> SpatialGrid:
        """
        返回位于指定设备和实数精度的等价网格

        Args:
            device: 承载固定双精度结果的 PyTorch 设备
            dtype: 坐标张量使用的固定双精度实数 dtype

        Returns:
            保持几何内容并转换到目标 device/dtype 的 SpatialGrid

        Raises:
            OpticalValueError: 输入数值、形状、精度或适用域不满足契约

        """
        if dtype is not _GRID_REAL_DTYPE:
            raise _errors.OpticalValueError(
                "spatial_grid_dtype_invalid",
                "空间网格固定以 float64 承载（ADR-0005 固定双精度核），"
                f"收到的是 {dtype}",
            )
        target_device = torch.device(device)
        moved_spacing = (
            self.sample_spacing[0].to(
                device=target_device,
                dtype=dtype,
            ),
            self.sample_spacing[1].to(
                device=target_device,
                dtype=dtype,
            ),
        )
        if self._first_sample_position is None:
            return _new_spatial_grid(
                sample_counts=self.sample_counts,
                sample_spacing=moved_spacing,
                first_sample_position=None,
                orientation=self.orientation,
            )
        moved_position = (
            self._first_sample_position[0].to(
                device=target_device,
                dtype=dtype,
            ),
            self._first_sample_position[1].to(
                device=target_device,
                dtype=dtype,
            ),
        )
        return _new_spatial_grid(
            sample_counts=self.sample_counts,
            sample_spacing=moved_spacing,
            first_sample_position=moved_position,
            orientation=self.orientation,
        )


def _new_spatial_grid(
    *,
    sample_counts: tuple[int, int],
    sample_spacing: _TensorPair,
    first_sample_position: _TensorPair | None,
    orientation: tuple[str, str],
) -> SpatialGrid:
    instance = object.__new__(SpatialGrid)
    object.__setattr__(instance, "sample_counts", sample_counts)
    object.__setattr__(instance, "sample_spacing", sample_spacing)
    object.__setattr__(instance, "orientation", orientation)
    object.__setattr__(
        instance,
        "_first_sample_position",
        first_sample_position,
    )
    return instance


def _is_centered_grid(grid: SpatialGrid) -> bool:
    return grid._first_sample_position is None


def _validate_sample_counts(sample_counts: object) -> None:
    if (
        not isinstance(sample_counts, tuple)
        or len(sample_counts) != 2
        or any(
            isinstance(count, bool)
            or not isinstance(count, int)
            or count <= 0
            for count in sample_counts
        )
    ):
        raise _errors.OpticalValueError(
            "spatial_grid_sample_counts_invalid",
            "空间网格的采样数必须是纵向与横向两个正整数，"
            f"收到的是 {sample_counts!r}",
        )


def _validate_orientation(orientation: object) -> None:
    if (
        not isinstance(orientation, tuple)
        or len(orientation) != 2
        or any(
            not isinstance(direction, str)
            or direction not in _SUPPORTED_ORIENTATIONS
            for direction in orientation
        )
    ):
        raise _errors.OpticalValueError(
            "spatial_grid_orientation_invalid",
            "空间网格朝向必须分别声明纵向与横向坐标随索引递增或递减，"
            f"收到的是 {orientation!r}",
        )


def _normalize_scalar_pair(
    values: object,
    *,
    identity: str,
    nonfinite_identity: str,
    quantity_name: str,
    is_positive: bool,
) -> _TensorPair:
    if not isinstance(values, tuple) or len(values) != 2:
        raise _errors.OpticalValueError(
            identity,
            f"空间网格的{quantity_name}必须恰好包含纵向与横向两个实数标量",
        )
    normalized = tuple(
        _normalize_scalar(
            value,
            identity=identity,
            nonfinite_identity=nonfinite_identity,
            quantity_name=quantity_name,
            is_positive=is_positive,
        )
        for value in values
    )
    pair = (normalized[0], normalized[1])
    _validate_shared_placement(pair)
    return pair


def _normalize_scalar(
    value: object,
    *,
    identity: str,
    nonfinite_identity: str,
    quantity_name: str,
    is_positive: bool,
) -> torch.Tensor:
    if isinstance(value, torch.Tensor):
        if (
            value.dim() != 0
            or torch.is_complex(value)
            or value.dtype is not _GRID_REAL_DTYPE
        ):
            raise _errors.OpticalValueError(
                identity,
                f"空间网格的{quantity_name}必须是零维 float64 实数张量，"
                f"收到的形状是 {tuple(value.shape)}、dtype 是 {value.dtype}",
            )
        normalized = value
    elif (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise _errors.OpticalValueError(
            identity,
            f"空间网格的{quantity_name}必须是有限实数或零维实数浮点张量，"
            f"收到的是 {value!r}",
        )
    elif not math.isfinite(value):
        raise _errors.OpticalValueError(
            nonfinite_identity,
            f"空间网格的{quantity_name}必须是有限值",
        )
    else:
        normalized = torch.tensor(
            value,
            dtype=_GRID_REAL_DTYPE,
        )
    if normalized.is_meta:
        return normalized
    if not bool(torch.isfinite(normalized)):
        raise _errors.OpticalValueError(
            nonfinite_identity,
            f"空间网格的{quantity_name}必须是有限值",
        )
    if is_positive and not bool(normalized > 0.0):
        raise _errors.OpticalValueError(
            identity,
            f"空间网格的{quantity_name}必须为正数，"
            "坐标方向应由朝向而不是负间距表达",
        )
    return normalized


def _validate_shared_placement(values: tuple[torch.Tensor, ...]) -> None:
    first = values[0]
    if any(
        value.device != first.device or value.dtype is not first.dtype
        for value in values[1:]
    ):
        raise _errors.OpticalValueError(
            "spatial_grid_scalar_placement_mismatch",
            "同一空间网格的采样间距与首样本位置必须位于同一设备并使用同一实数精度",
        )


class PropagationExterior(str, Enum):
    """
    采样横向窗口以外的物理语义

    """

    PERIODIC = "periodic"
    ISOLATED = "isolated"

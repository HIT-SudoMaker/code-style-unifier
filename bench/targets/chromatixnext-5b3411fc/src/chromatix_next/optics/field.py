from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import Enum
import math
from typing import TypeVar

import torch

import chromatix_next.errors as _errors

from .._numerics.optical_path_reference import normalize_optical_path_lengths
from .._tensors import is_finite_fixed_double_scalar, is_value_readable
from .grid import SpatialGrid
from .medium import Medium
from .polarization import PolarizationRepresentation
from .spectrum import Spectrum


class FieldNormalization(str, Enum):
    """
    光场包络模方的科学解释方式

    """

    RELATIVE = "relative"
    POWER = "power"


class _SourceLineage:

    """
    以对象身份表示相干源谱系

    """

    __slots__ = ()

    def __copy__(self) -> "_SourceLineage":

        return self

    def __deepcopy__(self, memo: dict[int, object]) -> "_SourceLineage":

        del memo
        return self


_FieldValue = TypeVar("_FieldValue", bound="OpticalField")
_MetadataValue = TypeVar("_MetadataValue")


@dataclass(frozen=True, slots=True)
class OpticalPathReference:
    """
    各光谱分量的不可变光程长度（SI 米）

    Args:
        lengths: 各光谱采样共享载波参考的光程长度

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    lengths: tuple[float | torch.Tensor, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.lengths, tuple) or not self.lengths:
            raise _errors.OpticalTypeError(
                "optical_path_reference_lengths_invalid",
                "光程参考要给出非空的元组，每个光谱分量一条以米计的光程，"
                f"收到的是 {self.lengths!r}",
            )
        for length in self.lengths:
            if isinstance(length, torch.Tensor):
                if (
                    length.dim() != 0
                    or torch.is_complex(length)
                    or length.dtype is not torch.float64
                ):
                    raise _errors.OpticalTypeError(
                        "optical_path_reference_lengths_invalid",
                        "以张量给出的光程必须是零维 float64 实张量（固定双精度核，"
                        "不再静默升精度——请在上游以 float64 构造），"
                        f"收到的形状是 {tuple(length.shape)}、dtype 是 "
                        f"{length.dtype}",
                    )
                continue
            if isinstance(length, bool) or not isinstance(length, (int, float)):
                raise _errors.OpticalTypeError(
                    "optical_path_reference_lengths_invalid",
                    "光程要么是实数，要么是零维实张量，"
                    f"收到的是 {type(length).__name__}",
                )
        if any(not is_finite_fixed_double_scalar(length) for length in self.lengths):
            raise _errors.OpticalValueError(
                "optical_path_reference_lengths_nonfinite",
                "每条光程都要是有限米数，无穷或非数通常来自未定义的传播距离，"
                f"收到的是 {self.lengths!r}",
            )
        object.__setattr__(
            self,
            "lengths",
            normalize_optical_path_lengths(self.lengths),
        )


@dataclass(frozen=True, slots=True, eq=False)
class OpticalField:
    """
    采样复包络的不可变物理值

    Args:
        envelope: 按偏振、光谱和空间轴排列的复包络
        grid: 定义采样位置与间距的空间网格
        spectrum: 光谱采样、权重与波长语义
        polarization_representation: 包络采用的标量、横向或完整偏振表示
        medium: 光所在位置的折射率模型
        normalization: 包络或强度数值对应的物理归一化语义
        path_reference: 从复包络中分离出来的光谱载波参考

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    envelope: torch.Tensor
    grid: SpatialGrid
    spectrum: Spectrum
    polarization_representation: PolarizationRepresentation
    medium: Medium
    normalization: FieldNormalization
    path_reference: OpticalPathReference
    _source_lineage: _SourceLineage = dataclass_field(
        default_factory=_SourceLineage,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.envelope, torch.Tensor):
            raise _errors.OpticalTypeError(
                "optical_field_envelope_invalid",
                "光场包络要以张量承载采样复振幅，"
                f"收到的是 {type(self.envelope).__name__}；"
                "数组或标量需先转成张量",
            )
        if not torch.is_complex(self.envelope):
            raise _errors.OpticalValueError(
                "optical_field_envelope_not_complex",
                "包络承载的是复振幅，相位要靠复数数据类型才能保留，"
                f"收到的是 {self.envelope.dtype}",
            )
        if self.envelope.dtype is not torch.complex128:
            raise _errors.OpticalValueError(
                "optical_field_envelope_dtype_invalid",
                "光场包络固定以 complex128 承载（ADR-0005 固定双精度核），"
                "单精度复包络不再被支持，请在上游以 complex128 构造；"
                f"收到的是 {self.envelope.dtype}",
            )
        # meta 同样执行有限性张量核以进入内存轨迹，只跳过不可读取的布尔判定
        is_finite = torch.isfinite(self.envelope).all()
        if is_value_readable(is_finite) and not bool(is_finite):
            raise _errors.OpticalValueError(
                "optical_field_envelope_nonfinite",
                "包络出现无穷或非数样本，通常来自除零或发散的传播步骤，"
                f"收到的形状是 {tuple(self.envelope.shape)}",
            )
        if self.envelope.dim() < 4:
            raise _errors.OpticalValueError(
                "optical_field_envelope_rank_invalid",
                "包络至少要有光谱、偏振、高、宽四个轴，批量轴可选，"
                f"收到的是 {self.envelope.dim()} 维",
            )
        if not isinstance(self.grid, SpatialGrid):
            raise _errors.OpticalTypeError(
                "optical_field_grid_invalid",
                "光场的横向采样要由网格物理值给出，"
                f"收到的是 {type(self.grid).__name__}；"
                "采样数与间距的元组需先构造成网格",
            )
        if not isinstance(self.spectrum, Spectrum):
            raise _errors.OpticalTypeError(
                "optical_field_spectrum_invalid",
                "光场的波长构成要由光谱物理值给出，"
                f"收到的是 {type(self.spectrum).__name__}；"
                "单一波长也要包成光谱",
            )
        if not isinstance(
            self.polarization_representation,
            PolarizationRepresentation,
        ):
            raise _errors.OpticalTypeError(
                "optical_field_polarization_representation_invalid",
                "光场的偏振轴必须声明为标量、横向或完整表示，"
                f"收到的是 {type(self.polarization_representation).__name__}",
            )
        if not isinstance(self.medium, Medium):
            raise _errors.OpticalTypeError(
                "optical_field_medium_invalid",
                "光场所在的传播介质要由介质物理值给出，"
                f"收到的是 {type(self.medium).__name__}；"
                "裸折射率数值需先包成介质",
            )
        if not isinstance(self.normalization, FieldNormalization):
            raise _errors.OpticalTypeError(
                "optical_field_normalization_invalid",
                "包络模方的单位含义要用归一化枚举声明为相对或功率，"
                f"收到的是 {type(self.normalization).__name__}",
            )
        if self.envelope.shape[-4] != self.spectrum.count:
            raise _errors.OpticalValueError(
                "optical_field_spectrum_axis_mismatch",
                f"光谱有 {self.spectrum.count} 个分量，包络对应轴却是 "
                f"{self.envelope.shape[-4]}；每个波长各占一层",
            )
        if (
            self.envelope.shape[-3]
            != self.polarization_representation.component_count
        ):
            raise _errors.OpticalValueError(
                "optical_field_polarization_axis_mismatch",
                "偏振表示有 "
                f"{self.polarization_representation.component_count} 个分量，"
                f"包络对应轴却是 {self.envelope.shape[-3]}",
            )
        if self.envelope.shape[-2] != self.grid.sample_counts[0]:
            raise _errors.OpticalValueError(
                "optical_field_height_axis_mismatch",
                f"网格纵向有 {self.grid.sample_counts[0]} 个采样，"
                f"包络高度轴却是 {self.envelope.shape[-2]}",
            )
        if self.envelope.shape[-1] != self.grid.sample_counts[1]:
            raise _errors.OpticalValueError(
                "optical_field_width_axis_mismatch",
                f"网格横向有 {self.grid.sample_counts[1]} 个采样，"
                f"包络宽度轴却是 {self.envelope.shape[-1]}",
            )
        if not isinstance(self.path_reference, OpticalPathReference):
            raise _errors.OpticalTypeError(
                "optical_field_path_reference_invalid",
                "光场的光程要由光程参考物理值给出，"
                f"收到的是 {type(self.path_reference).__name__}；"
                "米数元组需先包成光程参考",
            )
        if len(self.path_reference.lengths) != self.spectrum.count:
            raise _errors.OpticalValueError(
                "optical_field_path_reference_spectrum_mismatch",
                f"光谱有 {self.spectrum.count} 个分量，每个都要一条光程，"
                f"光程参考给出的是 {len(self.path_reference.lengths)} 条",
            )

    @property
    def batch_shape(self) -> tuple[int, ...]:
        """
        返回光谱轴之前的批量维形状

        Returns:
            光谱轴之前的批量维长度元组

        """
        return tuple(self.envelope.shape[:-4])

    @property
    def spectral_count(self) -> int:
        """
        返回光谱分量数目

        Returns:
            返回场对象的谱道数量

        """
        return int(self.envelope.shape[-4])

    @property
    def envelope_shape(self) -> tuple[int, ...]:
        """
        返回完整包络形状

        Returns:
            完整包络的维长度元组

        """
        return tuple(self.envelope.shape)


class _UnchangedFieldValue:
    """
    标记光场变换中必须原样保留的物理值

    """

    __slots__ = ()


_UNCHANGED_FIELD_VALUE = _UnchangedFieldValue()


def _transform_field(
    field: OpticalField,
    *,
    envelope: torch.Tensor,
    grid: SpatialGrid | _UnchangedFieldValue = _UNCHANGED_FIELD_VALUE,
    medium: Medium | _UnchangedFieldValue = _UNCHANGED_FIELD_VALUE,
    normalization: (
        FieldNormalization | _UnchangedFieldValue
    ) = _UNCHANGED_FIELD_VALUE,
    polarization_representation: (
        PolarizationRepresentation | _UnchangedFieldValue
    ) = _UNCHANGED_FIELD_VALUE,
    path_reference: (
        OpticalPathReference | _UnchangedFieldValue
    ) = _UNCHANGED_FIELD_VALUE,
) -> OpticalField:
    transformed = OpticalField(
        envelope=envelope,
        grid=_changed_or_existing(field.grid, grid),
        spectrum=field.spectrum,
        polarization_representation=_changed_or_existing(
            field.polarization_representation,
            polarization_representation,
        ),
        medium=_changed_or_existing(field.medium, medium),
        normalization=_changed_or_existing(
            field.normalization,
            normalization,
        ),
        path_reference=_changed_or_existing(
            field.path_reference,
            path_reference,
        ),
    )
    return _inherit_source_lineage(field, transformed)


def _changed_or_existing(
    existing: _MetadataValue,
    changed: _MetadataValue | _UnchangedFieldValue,
) -> _MetadataValue:
    if isinstance(changed, _UnchangedFieldValue):
        return existing
    return changed


def _inherit_source_lineage(
    source: OpticalField,
    result: _FieldValue,
) -> _FieldValue:
    object.__setattr__(result, "_source_lineage", source._source_lineage)
    return result


def _own_field_value(
    result: _FieldValue,
    lineage: _SourceLineage,
) -> _FieldValue:
    # Source 的唯一赋权缝；谱系不进入公开构造器，也不进入 PyTorch state_dict
    object.__setattr__(result, "_source_lineage", lineage)
    return result


def _has_same_source_lineage(
    first: OpticalField,
    second: OpticalField,
) -> bool:
    return first._source_lineage is second._source_lineage


@dataclass(frozen=True, slots=True)
class PropagationDirection:
    """
    平面波的归一化前向传播方向（横向方向余弦表示）

    以一对横向方向余弦 (cy, cx) 表示，法向余弦 cz = sqrt(1 - cy² - cx²) 由勾股关系
    派生（前向半空间 cz > 0）。对多光谱源，一个传播方向意味着所有光谱分量沿同一方向
    传播，仅波矢模 |k| 随波长与介质变化（规约"Propagation Direction"）。

    Args:
        direction_cosine_y: 传播方向在网格 y 切向上的方向余弦
        direction_cosine_x: 传播方向在网格 x 切向上的方向余弦

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    direction_cosine_y: float
    direction_cosine_x: float

    def __post_init__(self) -> None:
        for value in (self.direction_cosine_y, self.direction_cosine_x):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise _errors.OpticalValueError(
                    "propagation_direction_value_invalid",
                    "方向余弦要是有限实数，取值落在 -1 与 1 之间，"
                    f"收到的是 {value!r}",
                )
        squared_transverse = (
            float(self.direction_cosine_y) ** 2
            + float(self.direction_cosine_x) ** 2
        )
        if squared_transverse >= 1.0:
            raise _errors.OpticalValueError(
                "propagation_direction_normalization_invalid",
                "横向余弦平方和要小于 1 才有前向传播分量，等于 1 是掠射、"
                f"大于 1 已经倏逝，收到的是 {squared_transverse}",
            )

    @classmethod
    def forward(cls) -> "PropagationDirection":
        """
        构造沿正法线传播的轴向入射方向（横向余弦为 0）

        Returns:
            返回传播后的 OpticalField，并保留当前载体状态

        """
        return cls(0.0, 0.0)

    @property
    def direction_cosine_z(self) -> float:
        """
        返回前向法向余弦 cz = sqrt(1 - cy² - cx²)（> 0）

        Returns:
            返回传播方向在全局 z 轴上的方向余弦

        """
        return math.sqrt(
            1.0
            - float(self.direction_cosine_y) ** 2
            - float(self.direction_cosine_x) ** 2,
        )


@dataclass(frozen=True, slots=True)
class TransverseWavevector:
    """
    平面波的显式横向空间载波 (ky, kx)

    SI 单位：弧度每米（rad/m）。共享横向波矢 ⇒ 各光谱分量方向随波长变化（|k(λ)| 随 λ
    与介质变化，故 cy(λ) = ky/|k(λ)|、cx(λ) = kx/|k(λ)| 随波长变化）。零矢量合法（等价
    于轴向传播）。传播条件（ky² + kx² < |k(λ)|²，按每分量独立判定）在源边界处拒绝倏逝
    分量，绝不静默裁剪（规约"Transverse Wavevector"）。

    Args:
        wavevector_y: 横向波矢在网格 y 方向的分量
        wavevector_x: 横向波矢在网格 x 方向的分量

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    wavevector_y: float
    wavevector_x: float

    def __post_init__(self) -> None:
        for value in (self.wavevector_y, self.wavevector_x):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise _errors.OpticalValueError(
                    "transverse_wavevector_value_invalid",
                    "横向波矢分量要是以弧度每米计的有限实数，零矢量即轴向传播，"
                    f"收到的是 {value!r}",
                )

    @classmethod
    def axial(cls) -> "TransverseWavevector":
        """
        构造零横向波矢的轴向传播特例（ky 与 kx 均为 0）

        与 PropagationDirection.forward() 对偶：那里给出轴向的方向余弦特例
        （cy=cx=0），这里给出同一轴向入射的横向波矢特例（零矢量合法）

        Returns:
            返回 transverse wavevector 的轴向分量

        """
        return cls(0.0, 0.0)

    @property
    def transverse_magnitude_squared(self) -> float:
        """
        返回横向波矢模平方 ky² + kx²（rad²/m²）

        Returns:
            返回 transverse wavevector 的横向模平方

        """
        return (
            float(self.wavevector_y) ** 2 + float(self.wavevector_x) ** 2
        )

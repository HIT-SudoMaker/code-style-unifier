from __future__ import annotations

from dataclasses import dataclass
import math

import torch

from chromatix_next._numerics.wave_propagation.radiative_spectrum import (
    _computational_window_facts,
)
from chromatix_next._numerics.wave_propagation.scalar_angular_spectrum import (
    propagate_scalar_angular_spectrum,
    scalar_angular_spectrum_calculation,
    scalar_angular_spectrum_support_statistics,
)
from chromatix_next._tensors import (
    is_finite_fixed_double_scalar,
    is_value_readable,
    register_fixed_double_real_scalar,
)
import chromatix_next.errors as _errors

from . import _field_state
from .._grid_state import _GridState
from .._role_contract import _PropagationRole
from ..field import OpticalField, _transform_field
from ..grid import PropagationExterior, SpatialGrid
from ..polarization import PolarizationRepresentation


@dataclass(frozen=True, slots=True)
class ScalarAngularSpectrumDiagnostic:
    """
    一次角谱诊断的逐光谱频率支撑与输入功率保留结果

    Args:
        retained_power_ratio: 传播带限后保留的离散功率比例
        surviving_frequency_count: 通过传播带限判定的频率样本数

    """

    retained_power_ratio: torch.Tensor
    surviving_frequency_count: torch.Tensor

@dataclass(frozen=True, slots=True)
class _PreparedScalarAngularSpectrum:
    """
    承载标量角谱传播的预计算事实

    """

    output_grid: SpatialGrid
    computational_counts: tuple[int, int]
    padding: tuple[int, int]
    transfer: torch.Tensor


def scalar_angular_spectrum(
    field: OpticalField,
    *,
    axial_distance: float | torch.Tensor,
    exterior: PropagationExterior = PropagationExterior.PERIODIC,
    destination_grid: SpatialGrid | None = None,
) -> OpticalField:
    """
    以辐射角谱关系把光场传播到一个平行目标平面

    Args:
        field: 待处理的入射光场
        axial_distance: 沿传播轴的有符号距离
        exterior: 输入网格之外的显式延拓值
        destination_grid: 传播结果必须配准到的目标空间网格

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """
    prepared = _prepare_scalar_angular_spectrum(
        field,
        axial_distance=axial_distance,
        exterior=exterior,
        destination_grid=destination_grid,
    )
    propagated = propagate_scalar_angular_spectrum(
        envelope=field.envelope,
        transfer=prepared.transfer,
        computational_counts=prepared.computational_counts,
        window_counts=field.grid.sample_counts,
        padding=prepared.padding,
    )
    return _transform_field(
        field,
        envelope=propagated,
        grid=prepared.output_grid,
        path_reference=_field_state._advance_path_reference(
            field=field,
            axial_distances=(axial_distance,),
        ),
    )


def _prepare_scalar_angular_spectrum(
    field: OpticalField,
    *,
    axial_distance: float | torch.Tensor,
    exterior: PropagationExterior,
    destination_grid: SpatialGrid | None,
) -> _PreparedScalarAngularSpectrum:
    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "scalar_angular_spectrum_field_invalid",
            "角谱传播只能作用于光场，"
            f"收到的是 {type(field).__name__}",
        )
    if field.polarization_representation is PolarizationRepresentation.FULL:
        raise _errors.OpticalValueError(
            "scalar_angular_spectrum_polarization_full_unsupported",
            "标量传播在均匀各向同性偏振中性近似下只作用于标量或横向光场；"
            "完整矢量光场请使用矢量角谱传播",
        )
    _validate_axial_distance(axial_distance)
    _validate_exterior(exterior)
    _validate_destination_grid(destination_grid)
    output_grid = _resolve_output_grid(
        field=field,
        destination_grid=destination_grid,
    )
    (
        aligned_axial_distance,
        wavelengths,
        refractive_indices,
    ) = _field_state._propagation_spectrum(
        field,
        axial_distance,
        reference=field.envelope.real,
    )
    displacement = _resolve_displacement(
        input_grid=field.grid,
        output_grid=output_grid,
    )
    window_facts = _computational_window_facts(
        input_counts=field.grid.sample_counts,
        sample_spacing=field.grid.sample_spacing,
        displacement=displacement,
        exterior=exterior.value,
    )
    if (
        is_value_readable(window_facts.is_outside_support)
        and bool(window_facts.is_outside_support)
    ):
        raise _errors.OpticalValueError(
            "scalar_angular_spectrum_isolated_displacement_outside_support",
            "孤立外部的目标位移超出固定三倍计算窗口的零延拓支撑；"
            "请扩大输入窗口、调整采样间距或改用适合该目标几何的传播方法",
        )
    calculation = scalar_angular_spectrum_calculation(
        computational_counts=window_facts.computational_counts,
        signed_spacing=field.grid.signed_spacing,
        displacement=displacement,
        axial_distance=aligned_axial_distance,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        real_dtype=field.envelope.real.dtype,
        complex_dtype=field.envelope.dtype,
        device=field.envelope.device,
    )
    if (
        is_value_readable(calculation.has_narrow_alias_band)
        and bool(calculation.has_narrow_alias_band)
    ):
        raise _errors.OpticalValueError(
            "scalar_angular_spectrum_alias_band_too_narrow",
            "角谱混叠安全带已经窄于网格的首个非零频率箱；"
            "请缩短传播距离、扩大计算窗口或调整采样间距",
        )
    _validate_numerical_shapes(
        field=field,
        transfer=calculation.transfer,
        computational_counts=window_facts.computational_counts,
    )
    return _PreparedScalarAngularSpectrum(
        output_grid=output_grid,
        computational_counts=window_facts.computational_counts,
        padding=window_facts.padding,
        transfer=calculation.transfer,
    )


def _validate_numerical_shapes(
    *,
    field: OpticalField,
    transfer: torch.Tensor,
    computational_counts: tuple[int, int],
) -> None:
    if tuple(field.envelope.shape[-2:]) != field.grid.sample_counts:
        raise _errors.OpticalValueError(
            "scalar_angular_spectrum_envelope_window_mismatch",
            f"包络的空间形状 {tuple(field.envelope.shape[-2:])} 与传播窗口 "
            f"{field.grid.sample_counts} 不一致，传播窗口必须与输入网格的采样数相同",
        )
    if transfer.shape[0] != field.envelope.shape[-4]:
        raise _errors.OpticalValueError(
            "scalar_angular_spectrum_transfer_spectrum_mismatch",
            f"传递张量的光谱维长度 {transfer.shape[0]} 与包络的光谱维长度 "
            f"{field.envelope.shape[-4]} 不一致，传递张量必须逐波长对应",
        )
    if tuple(transfer.shape[-2:]) != computational_counts:
        raise _errors.OpticalValueError(
            "scalar_angular_spectrum_transfer_grid_mismatch",
            f"传递张量的空间形状 {tuple(transfer.shape[-2:])} 与计算网格 "
            f"{computational_counts} 不一致，传递张量必须在零延拓后的网格上给出",
        )


class ScalarAngularSpectrum(torch.nn.Module):
    """
    拥有轴向距离、目标网格与传播外部的辐射角谱传播组件

    Args:
        axial_distance: 沿传播轴的有符号距离
        exterior: 输入网格之外的显式延拓值
        destination_grid: 传播结果必须配准到的目标空间网格

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    axial_distance: torch.Tensor

    def __init__(
        self,
        *,
        axial_distance: float | torch.Tensor,
        exterior: PropagationExterior = PropagationExterior.PERIODIC,
        destination_grid: SpatialGrid | None = None,
    ) -> None:
        super().__init__()
        _validate_axial_distance(axial_distance)
        _validate_exterior(exterior)
        _validate_destination_grid(destination_grid)
        self.exterior = exterior
        self._destination_grid_state = (
            None
            if destination_grid is None
            else _GridState(destination_grid)
        )
        register_fixed_double_real_scalar(
            self,
            name="axial_distance",
            value=axial_distance,
        )

    @property
    def role(self) -> _PropagationRole:
        """
        传播角色字面量

        Returns:
            返回该组件声明的 Propagation 角色

        """
        return "propagation"

    @property
    def destination_grid(self) -> SpatialGrid | None:
        """
        显式目标空间网格；省略时保留输入网格，仅支持同几何平移

        Returns:
            标量角谱传播使用的目标 SpatialGrid

        """
        if self._destination_grid_state is None:
            return None
        return self._destination_grid_state.value

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        以辐射角谱关系把入射光场传播到目标平面

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """
        return scalar_angular_spectrum(
            field,
            axial_distance=self.axial_distance,
            exterior=self.exterior,
            destination_grid=self.destination_grid,
        )

    def diagnose(self, field: OpticalField) -> ScalarAngularSpectrumDiagnostic:
        """
        纯查询当前传播对输入频率支撑和功率的保留情况

        Args:
            field: 待处理的入射光场

        Returns:
            返回 Scalar Angular Spectrum 的诊断统计与支撑判定

        Raises:
            OpticalTypeError: 输入对象物理类型不满足该 Interface
            OpticalValueError: 输入数值/形状/精度/适用域不满足契约

        """
        prepared = _prepare_scalar_angular_spectrum(
            field,
            axial_distance=self.axial_distance,
            exterior=self.exterior,
            destination_grid=self.destination_grid,
        )
        statistics = scalar_angular_spectrum_support_statistics(
            envelope=field.envelope,
            transfer=prepared.transfer,
            computational_counts=prepared.computational_counts,
            padding=prepared.padding,
        )
        return ScalarAngularSpectrumDiagnostic(
            retained_power_ratio=statistics.retained_power_ratio,
            surviving_frequency_count=statistics.surviving_frequency_count,
        )

    def _validate_physical_state(self) -> None:
        _validate_axial_distance(self.axial_distance)

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        return _resolve_output_grid(
            field=field,
            destination_grid=self.destination_grid,
        )


def _validate_axial_distance(axial_distance: object) -> None:
    if isinstance(axial_distance, torch.Tensor):
        if (
            axial_distance.dim() != 0
            or torch.is_complex(axial_distance)
            or not axial_distance.is_floating_point()
            or not is_finite_fixed_double_scalar(axial_distance)
        ):
            raise _errors.OpticalValueError(
                "scalar_angular_spectrum_axial_distance_invalid",
                "以张量给出的轴向距离须是有限的零维实数标量，零与负值都合法，"
                f"收到的是 {axial_distance!r}",
            )
        return
    if (
        isinstance(axial_distance, bool)
        or not isinstance(axial_distance, (int, float))
        or not math.isfinite(float(axial_distance))
    ):
        raise _errors.OpticalValueError(
            "scalar_angular_spectrum_axial_distance_invalid",
            "轴向距离须是有限的带符号实数米值，零与负值都合法，"
            f"收到的是 {axial_distance!r}",
        )


def _validate_exterior(exterior: object) -> None:
    if not isinstance(exterior, PropagationExterior):
        raise _errors.OpticalTypeError(
            "scalar_angular_spectrum_exterior_invalid",
            "传播外部须从周期延拓与孤立零场两种约定中选一个，"
            f"收到的是 {exterior!r}",
        )


def _validate_destination_grid(destination_grid: object) -> None:
    if destination_grid is not None and not isinstance(
        destination_grid,
        SpatialGrid,
    ):
        raise _errors.OpticalTypeError(
            "scalar_angular_spectrum_destination_grid_invalid",
            "目标网格须是空间网格，省略则原样保留输入网格，"
            f"收到的是 {type(destination_grid).__name__}",
        )


def _resolve_output_grid(
    *,
    field: OpticalField,
    destination_grid: SpatialGrid | None,
) -> SpatialGrid:
    input_grid = field.grid
    if destination_grid is None:
        return input_grid
    input_geometry = SpatialGrid.centered(
        sample_counts=input_grid.sample_counts,
        sample_spacing=input_grid.sample_spacing,
        orientation=input_grid.orientation,
    )
    destination_geometry = SpatialGrid.centered(
        sample_counts=destination_grid.sample_counts,
        sample_spacing=destination_grid.sample_spacing,
        orientation=destination_grid.orientation,
    )
    if not input_geometry.is_inference_compatible_with(destination_geometry):
        raise _errors.OpticalValueError(
            "scalar_angular_spectrum_destination_grid_not_applicable",
            "目标网格当前只支持平移，不支持改变采样数、采样间距或朝向，"
            f"输入网格为 {input_grid!r}，"
            f"目标网格为 {destination_grid!r}",
        )
    return destination_grid


def _resolve_displacement(
    *,
    input_grid: SpatialGrid,
    output_grid: SpatialGrid,
) -> tuple[torch.Tensor, torch.Tensor]:
    return (
        output_grid.first_sample_position[0]
        - input_grid.first_sample_position[0],
        output_grid.first_sample_position[1]
        - input_grid.first_sample_position[1],
    )

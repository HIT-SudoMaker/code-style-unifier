from __future__ import annotations

from dataclasses import dataclass
import math

import torch

from chromatix_next._numerics.wave_propagation.radiative_spectrum import (
    _computational_window_facts,
)
from chromatix_next._numerics.wave_propagation.vector_angular_spectrum import (
    VectorAngularSpectrumCalculation,
    propagate_vector_angular_spectrum,
    vector_angular_spectrum_calculation,
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
from ..field import FieldNormalization, OpticalField, _transform_field
from ..grid import PropagationExterior, SpatialGrid
from ..polarization import PolarizationRepresentation


@dataclass(frozen=True, slots=True)
class _PreparedVectorAngularSpectrum:
    """
    承载矢量角谱传播的预计算事实

    """

    output_grid: SpatialGrid
    computational_counts: tuple[int, int]
    padding: tuple[int, int]
    calculation: VectorAngularSpectrumCalculation

def vector_angular_spectrum(
    field: OpticalField,
    *,
    axial_distance: float | torch.Tensor,
    exterior: PropagationExterior = PropagationExterior.PERIODIC,
    destination_grid: SpatialGrid | None = None,
) -> OpticalField:
    """
    以辐射矢量角谱关系把矢量光场传播到平行目标平面

    Args:
        field: 待处理的入射光场
        axial_distance: 沿传播轴的有符号距离
        exterior: 输入网格之外的显式延拓值
        destination_grid: 传播结果必须配准到的目标空间网格

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

        OpticalTypeError: 输入对象物理类型不满足该 Interface
    """
    prepared = _prepare_vector_angular_spectrum(
        field,
        axial_distance=axial_distance,
        exterior=exterior,
        destination_grid=destination_grid,
    )
    propagated, is_full_field_transverse = propagate_vector_angular_spectrum(
        envelope=field.envelope,
        calculation=prepared.calculation,
        computational_counts=prepared.computational_counts,
        padding=prepared.padding,
        is_full=(
            field.polarization_representation
            is PolarizationRepresentation.FULL
        ),
    )
    if (
        is_value_readable(is_full_field_transverse)
        and not bool(is_full_field_transverse)
    ):
        raise _errors.OpticalValueError(
            "vector_angular_spectrum_full_field_not_transverse",
            "完整矢量光场在辐射支撑内不满足波矢与电场正交；"
            "请修正纵向分量，或以横向表示让传播方法重建它",
        )
    return _transform_field(
        field,
        envelope=propagated,
        grid=prepared.output_grid,
        polarization_representation=PolarizationRepresentation.FULL,
        path_reference=_field_state._advance_path_reference(
            field=field,
            axial_distances=(axial_distance,),
        ),
    )


def _prepare_vector_angular_spectrum(
    field: OpticalField,
    *,
    axial_distance: float | torch.Tensor,
    exterior: PropagationExterior,
    destination_grid: SpatialGrid | None,
) -> _PreparedVectorAngularSpectrum:
    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "vector_angular_spectrum_field_invalid",
            "矢量角谱传播只能作用于光场；"
            f"收到的是 {type(field).__name__}",
        )
    if (
        field.polarization_representation
        is PolarizationRepresentation.SCALAR
    ):
        raise _errors.OpticalValueError(
            "vector_angular_spectrum_polarization_scalar_unsupported",
            "矢量角谱传播需要横向或完整矢量光场；"
            "标量光场请使用标量角谱传播",
        )
    if field.normalization is not FieldNormalization.RELATIVE:
        raise _errors.OpticalValueError(
            "vector_angular_spectrum_normalization_unsupported",
            "首个矢量角谱切片只支持相对场归一化；"
            "功率归一化需要先冻结矢量场的面积与阻抗约定",
        )
    _validate_fixed_grid(field.grid, is_destination=False)
    _validate_axial_distance(axial_distance)
    _validate_exterior(exterior)
    _validate_destination_grid(destination_grid)
    if destination_grid is not None:
        _validate_fixed_grid(destination_grid, is_destination=True)
    output_grid = _resolve_output_grid(
        field=field,
        destination_grid=destination_grid,
    )
    distance, wavelengths, refractive_indices = (
        _field_state._propagation_spectrum(
            field,
            axial_distance,
            reference=field.envelope.real,
        )
    )
    displacement = (
        output_grid.first_sample_position[0]
        - field.grid.first_sample_position[0],
        output_grid.first_sample_position[1]
        - field.grid.first_sample_position[1],
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
            "vector_angular_spectrum_isolated_displacement_outside_support",
            "孤立外部的目标位移超出固定三倍计算窗口；"
            "请扩大输入窗口或改用适合该目标几何的传播方法",
        )
    calculation = vector_angular_spectrum_calculation(
        computational_counts=window_facts.computational_counts,
        signed_spacing=field.grid.signed_spacing,
        displacement=displacement,
        axial_distance=distance,
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
            "vector_angular_spectrum_alias_band_too_narrow",
            "矢量角谱的混叠安全带已经窄于首个非零频率箱；"
            "请缩短传播距离、扩大计算窗口或调整采样间距",
        )
    return _PreparedVectorAngularSpectrum(
        output_grid=output_grid,
        computational_counts=window_facts.computational_counts,
        padding=window_facts.padding,
        calculation=calculation,
    )


class VectorAngularSpectrum(torch.nn.Module):
    """
    拥有轴向距离、目标网格与外部约定的矢量角谱组件

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
        if destination_grid is not None:
            _validate_fixed_grid(destination_grid, is_destination=True)
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
            矢量角谱传播使用的目标 SpatialGrid

        """
        if self._destination_grid_state is None:
            return None
        return self._destination_grid_state.value

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        以辐射矢量角谱关系把入射光场传播到目标平面

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """
        return vector_angular_spectrum(
            field,
            axial_distance=self.axial_distance,
            exterior=self.exterior,
            destination_grid=self.destination_grid,
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
                "vector_angular_spectrum_axial_distance_invalid",
                "轴向距离必须是有限的零维实数浮点张量",
            )
        return
    if (
        isinstance(axial_distance, bool)
        or not isinstance(axial_distance, (int, float))
        or not math.isfinite(float(axial_distance))
    ):
        raise _errors.OpticalValueError(
            "vector_angular_spectrum_axial_distance_invalid",
            "轴向距离必须是有限的带符号实数米值",
        )


def _validate_exterior(exterior: object) -> None:
    if not isinstance(exterior, PropagationExterior):
        raise _errors.OpticalTypeError(
            "vector_angular_spectrum_exterior_invalid",
            "传播外部必须是周期延拓或孤立零场",
        )


def _validate_destination_grid(destination_grid: object) -> None:
    if destination_grid is not None and not isinstance(
        destination_grid,
        SpatialGrid,
    ):
        raise _errors.OpticalTypeError(
            "vector_angular_spectrum_destination_grid_invalid",
            "目标网格必须是空间网格，省略时保留输入网格",
        )


def _validate_fixed_grid(
    grid: SpatialGrid,
    *,
    is_destination: bool,
) -> None:
    coordinates = (
        *grid.sample_spacing,
        *grid.first_sample_position,
    )
    if any(coordinate.requires_grad for coordinate in coordinates):
        identity = (
            "vector_angular_spectrum_destination_grid_requires_grad"
            if is_destination
            else "vector_angular_spectrum_input_grid_requires_grad"
        )
        raise _errors.OpticalValueError(
            identity,
            "矢量角谱只声明输入包络与轴向距离梯度；"
            "网格间距、朝向和位置必须是固定几何",
        )


def _resolve_output_grid(
    *,
    field: OpticalField,
    destination_grid: SpatialGrid | None,
) -> SpatialGrid:
    if destination_grid is None:
        return field.grid
    input_geometry = SpatialGrid.centered(
        sample_counts=field.grid.sample_counts,
        sample_spacing=field.grid.sample_spacing,
        orientation=field.grid.orientation,
    )
    destination_geometry = SpatialGrid.centered(
        sample_counts=destination_grid.sample_counts,
        sample_spacing=destination_grid.sample_spacing,
        orientation=destination_grid.orientation,
    )
    if not input_geometry.is_inference_compatible_with(destination_geometry):
        raise _errors.OpticalValueError(
            "vector_angular_spectrum_destination_grid_not_applicable",
            "目标网格只能平移，不能改变采样数、采样间距或朝向",
        )
    return destination_grid

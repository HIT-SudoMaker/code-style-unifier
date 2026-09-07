from __future__ import annotations

from dataclasses import dataclass
import math

import torch

from chromatix_next._numerics.spatial_sampling import (
    isolated_destination_within_tripled_window,
)
from chromatix_next._numerics.wave_propagation.radiative_spectrum import (
    _computational_window_facts,
)
from chromatix_next._numerics.wave_propagation.scaled_angular_spectrum import (
    propagate_scaled_angular_spectrum,
    scaled_angular_spectrum_calculation,
    scaled_angular_spectrum_destination_sampling_too_coarse,
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
class _PreparedScaledAngularSpectrum:
    """
    承载缩放角谱传播的预计算事实

    """

    computational_counts: tuple[int, int]
    padding: tuple[int, int]
    transfer: torch.Tensor

def scaled_angular_spectrum(
    field: OpticalField,
    *,
    axial_distance: float | torch.Tensor,
    destination_grid: SpatialGrid,
    exterior: PropagationExterior = PropagationExterior.PERIODIC,
) -> OpticalField:
    """
    以辐射角谱关系把光场传播到带尺度与平移的目标平面

    Args:
        field: 待处理的入射光场
        axial_distance: 沿传播轴的有符号距离
        destination_grid: 传播结果必须配准到的目标空间网格
        exterior: 输入网格之外的显式延拓值

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    prepared = _prepare_scaled_angular_spectrum(
        field,
        axial_distance=axial_distance,
        exterior=exterior,
        destination_grid=destination_grid,
    )
    propagated = propagate_scaled_angular_spectrum(
        envelope=field.envelope,
        transfer=prepared.transfer,
        computational_counts=prepared.computational_counts,
        padding=prepared.padding,
        input_signed_spacing=field.grid.signed_spacing,
        input_first_sample_position=field.grid.first_sample_position,
        output_sample_counts=destination_grid.sample_counts,
        output_signed_spacing=destination_grid.signed_spacing,
        output_first_sample_position=(
            destination_grid.first_sample_position
        ),
    )
    return _transform_field(
        field,
        envelope=propagated,
        grid=destination_grid,
        path_reference=_field_state._advance_path_reference(
            field=field,
            axial_distances=(axial_distance,),
        ),
    )


class ScaledAngularSpectrum(torch.nn.Module):
    """
    拥有轴向距离、目标网格与传播外部的带尺度角谱传播组件

    Args:
        axial_distance: 沿传播轴的有符号距离
        destination_grid: 传播结果必须配准到的目标空间网格
        exterior: 输入网格之外的显式延拓值

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    axial_distance: torch.Tensor

    def __init__(
        self,
        *,
        axial_distance: float | torch.Tensor,
        destination_grid: SpatialGrid,
        exterior: PropagationExterior = PropagationExterior.PERIODIC,
    ) -> None:

        super().__init__()
        _validate_axial_distance(axial_distance)
        _validate_exterior(exterior)
        _validate_destination_grid(destination_grid)
        self.exterior = exterior
        self._destination_grid_state = _GridState(destination_grid)
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
    def destination_grid(self) -> SpatialGrid:
        """
        显式带尺度目标空间网格

        Returns:
            缩放角谱传播使用的目标 SpatialGrid

        """

        return self._destination_grid_state.value

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        以辐射角谱关系把入射光场传播到带尺度目标平面

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """

        return scaled_angular_spectrum(
            field,
            axial_distance=self.axial_distance,
            destination_grid=self.destination_grid,
            exterior=self.exterior,
        )

    def _validate_physical_state(self) -> None:
        _validate_axial_distance(self.axial_distance)

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        del field
        return self.destination_grid


def _prepare_scaled_angular_spectrum(
    field: OpticalField,
    *,
    axial_distance: float | torch.Tensor,
    exterior: PropagationExterior,
    destination_grid: SpatialGrid,
) -> _PreparedScaledAngularSpectrum:
    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "scaled_angular_spectrum_field_invalid",
            "带尺度角谱传播只能作用于光场，"
            f"收到的是 {type(field).__name__}",
        )
    if field.polarization_representation is PolarizationRepresentation.FULL:
        raise _errors.OpticalValueError(
            "scaled_angular_spectrum_polarization_full_unsupported",
            "标量传播在均匀各向同性偏振中性近似下只作用于标量或横向光场；"
            "完整矢量光场请使用矢量角谱传播",
        )
    _validate_axial_distance(axial_distance)
    _validate_exterior(exterior)
    _validate_destination_grid(destination_grid)
    if destination_grid.orientation != field.grid.orientation:
        raise _errors.OpticalValueError(
            "scaled_angular_spectrum_orientation_mismatch",
            "目标网格朝向当前必须与源网格一致，否则需先在源一侧显式翻转；"
            f"源朝向为 {field.grid.orientation}，"
            f"目标朝向为 {destination_grid.orientation}",
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
    window_facts = _computational_window_facts(
        input_counts=field.grid.sample_counts,
        sample_spacing=field.grid.sample_spacing,
        displacement=(
            destination_grid.first_sample_position[0]
            - field.grid.first_sample_position[0],
            destination_grid.first_sample_position[1]
            - field.grid.first_sample_position[1],
        ),
        exterior=exterior.value,
    )
    _validate_isolated_destination(
        field=field,
        destination_grid=destination_grid,
        exterior=exterior,
    )
    calculation = scaled_angular_spectrum_calculation(
        computational_counts=window_facts.computational_counts,
        input_signed_spacing=field.grid.signed_spacing,
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
            "scaled_angular_spectrum_alias_band_too_narrow",
            "带尺度角谱的混叠安全带已经窄于网格的首个非零频率箱；"
            "请缩短传播距离、扩大计算窗口或调整采样间距",
        )
    destination_sampling_too_coarse = (
        scaled_angular_spectrum_destination_sampling_too_coarse(
            input_signed_spacing=field.grid.signed_spacing,
            output_signed_spacing=destination_grid.signed_spacing,
            wavelengths=wavelengths,
            refractive_indices=refractive_indices,
            real_dtype=field.envelope.real.dtype,
            device=field.envelope.device,
        )
    )
    if (
        is_value_readable(destination_sampling_too_coarse)
        and bool(destination_sampling_too_coarse)
    ):
        raise _errors.OpticalValueError(
            "scaled_angular_spectrum_destination_sampling_too_coarse",
            "带尺度角谱的目标采样已经粗于传播后场的逐轴带宽（输入奈奎斯特与辐射"
            "带限 n / λ 的较小者）；请改用更细的目标间距或更粗的输入间距",
        )
    _validate_numerical_shapes(
        field=field,
        transfer=calculation.transfer,
        computational_counts=window_facts.computational_counts,
    )
    return _PreparedScaledAngularSpectrum(
        computational_counts=window_facts.computational_counts,
        padding=window_facts.padding,
        transfer=calculation.transfer,
    )


def _validate_isolated_destination(
    *,
    field: OpticalField,
    destination_grid: SpatialGrid,
    exterior: PropagationExterior,
) -> None:
    if exterior is not PropagationExterior.ISOLATED:
        return
    is_inside = isolated_destination_within_tripled_window(
        input_sample_counts=field.grid.sample_counts,
        input_signed_spacing=field.grid.signed_spacing,
        input_first_sample_position=field.grid.first_sample_position,
        output_sample_counts=destination_grid.sample_counts,
        output_signed_spacing=destination_grid.signed_spacing,
        output_first_sample_position=(
            destination_grid.first_sample_position
        ),
        reference=field.envelope.real,
    )
    if is_value_readable(is_inside) and not bool(is_inside):
        raise _errors.OpticalValueError(
            "scaled_angular_spectrum_isolated_destination_outside_support",
            "孤立外部的目标足迹超出源采样窗口的零延拓支撑；"
            "请扩大输入窗口、调整目标尺度或改用周期外部",
        )


def _validate_numerical_shapes(
    *,
    field: OpticalField,
    transfer: torch.Tensor,
    computational_counts: tuple[int, int],
) -> None:
    if tuple(field.envelope.shape[-2:]) != field.grid.sample_counts:
        raise _errors.OpticalValueError(
            "scaled_angular_spectrum_envelope_window_mismatch",
            f"包络的空间形状 {tuple(field.envelope.shape[-2:])} 与传播窗口 "
            f"{field.grid.sample_counts} 不一致，传播窗口必须与输入网格的采样数相同",
        )
    if transfer.shape[0] != field.envelope.shape[-4]:
        raise _errors.OpticalValueError(
            "scaled_angular_spectrum_transfer_spectrum_mismatch",
            f"传递张量的光谱维长度 {transfer.shape[0]} 与包络的光谱维长度 "
            f"{field.envelope.shape[-4]} 不一致，传递张量必须逐波长对应",
        )
    if tuple(transfer.shape[-2:]) != computational_counts:
        raise _errors.OpticalValueError(
            "scaled_angular_spectrum_transfer_grid_mismatch",
            f"传递张量的空间形状 {tuple(transfer.shape[-2:])} 与计算网格 "
            f"{computational_counts} 不一致，传递张量必须在零延拓后的网格上给出",
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
                "scaled_angular_spectrum_axial_distance_invalid",
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
            "scaled_angular_spectrum_axial_distance_invalid",
            "轴向距离须是有限的带符号实数米值，零与负值都合法，"
            f"收到的是 {axial_distance!r}",
        )


def _validate_exterior(exterior: object) -> None:
    if not isinstance(exterior, PropagationExterior):
        raise _errors.OpticalTypeError(
            "scaled_angular_spectrum_exterior_invalid",
            "传播外部须从周期延拓与孤立零场两种约定中选一个，"
            f"收到的是 {exterior!r}",
        )


def _validate_destination_grid(destination_grid: object) -> None:
    if not isinstance(destination_grid, SpatialGrid):
        raise _errors.OpticalTypeError(
            "scaled_angular_spectrum_destination_grid_invalid",
            "目标网格须是空间网格，带尺度传播必须显式给出目标网格，"
            f"收到的是 {type(destination_grid).__name__}",
        )

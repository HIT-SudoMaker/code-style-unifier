from __future__ import annotations

from dataclasses import dataclass

import torch

from chromatix_next._numerics.spatial_sampling import (
    isolated_destination_within_tripled_window,
)
from chromatix_next._numerics.wave_propagation.radiative_spectrum import (
    _computational_window_facts,
)
from chromatix_next._numerics.wave_propagation.scaled_fresnel import (
    ScaledFresnelCalculation,
    propagate_scaled_fresnel,
    scaled_fresnel_calculation,
    scaled_fresnel_sampling_facts,
)
from chromatix_next._tensors import (
    is_nonzero_finite_fixed_double_scalar,
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
class _PreparedScaledFresnel:
    """
    承载缩放菲涅耳传播的预计算事实

    """

    computational_counts: tuple[int, int]
    padding: tuple[int, int]
    distance: torch.Tensor
    calculation: ScaledFresnelCalculation

def scaled_fresnel(
    field: OpticalField,
    *,
    axial_distance: float | torch.Tensor,
    destination_grid: SpatialGrid,
    exterior: PropagationExterior = PropagationExterior.PERIODIC,
) -> OpticalField:
    """
    以近轴 Collins 积分把光场带尺度传播到目标平面

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

    prepared = _prepare_scaled_fresnel(
        field,
        axial_distance=axial_distance,
        exterior=exterior,
        destination_grid=destination_grid,
    )
    propagated = propagate_scaled_fresnel(
        envelope=field.envelope,
        calculation=prepared.calculation,
        computational_counts=prepared.computational_counts,
        padding=prepared.padding,
        output_sample_counts=destination_grid.sample_counts,
        axial_distance=prepared.distance,
        real_dtype=field.envelope.real.dtype,
        complex_dtype=field.envelope.dtype,
        device=field.envelope.device,
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


class ScaledFresnel(torch.nn.Module):
    """
    拥有轴向距离、目标网格与传播外部的带尺度 Fresnel 传播组件

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
            缩放 Fresnel 传播使用的目标 SpatialGrid

        """

        return self._destination_grid_state.value

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        以近轴 Collins 积分把入射光场带尺度传播到目标平面

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """

        return scaled_fresnel(
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


def _prepare_scaled_fresnel(
    field: OpticalField,
    *,
    axial_distance: float | torch.Tensor,
    exterior: PropagationExterior,
    destination_grid: SpatialGrid,
) -> _PreparedScaledFresnel:
    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "scaled_fresnel_field_invalid",
            "带尺度 Fresnel 传播只能作用于光场，"
            f"收到的是 {type(field).__name__}",
        )
    if field.polarization_representation is PolarizationRepresentation.FULL:
        raise _errors.OpticalValueError(
            "scaled_fresnel_polarization_full_unsupported",
            "标量传播在均匀各向同性偏振中性近似下只作用于标量或横向光场；"
            "完整矢量光场请使用矢量角谱传播",
        )
    _validate_axial_distance(axial_distance)
    _validate_exterior(exterior)
    _validate_destination_grid(destination_grid)
    if destination_grid.orientation != field.grid.orientation:
        raise _errors.OpticalValueError(
            "scaled_fresnel_orientation_mismatch",
            "目标网格朝向当前必须与源网格一致，否则需先在源一侧显式翻转；"
            f"源朝向为 {field.grid.orientation}，"
            f"目标朝向为 {destination_grid.orientation}",
        )
    distance, wavelengths, refractive_indices = (
        _field_state._propagation_spectrum(
            field,
            axial_distance,
            reference=field.envelope.real,
        )
    )
    if destination_grid.sample_counts[0] < 1 or destination_grid.sample_counts[
        1
    ] < 1:
        raise _errors.OpticalValueError(
            "scaled_fresnel_destination_grid_not_applicable",
            "目标采样数必须为正整数，"
            f"收到的是 {destination_grid.sample_counts}",
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
    computational_first_y = (
        field.grid.first_sample_position[0]
        - window_facts.padding[0] * field.grid.signed_spacing[0]
    )
    computational_first_x = (
        field.grid.first_sample_position[1]
        - window_facts.padding[1] * field.grid.signed_spacing[1]
    )
    calculation = scaled_fresnel_calculation(
        computational_counts=window_facts.computational_counts,
        computational_first_sample_position=(
            computational_first_y,
            computational_first_x,
        ),
        input_signed_spacing=field.grid.signed_spacing,
        output_sample_counts=destination_grid.sample_counts,
        output_signed_spacing=destination_grid.signed_spacing,
        output_first_sample_position=destination_grid.first_sample_position,
        axial_distance=distance,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        real_dtype=field.envelope.real.dtype,
        complex_dtype=field.envelope.dtype,
        device=field.envelope.device,
    )
    sampling_facts = scaled_fresnel_sampling_facts(
        input_counts=field.grid.sample_counts,
        input_signed_spacing=field.grid.signed_spacing,
        output_counts=destination_grid.sample_counts,
        output_signed_spacing=destination_grid.signed_spacing,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        axial_distance=distance,
        real_dtype=field.envelope.real.dtype,
        device=field.envelope.device,
    )
    if is_value_readable(sampling_facts.input_chirp_too_narrow) and bool(
        sampling_facts.input_chirp_too_narrow,
    ):
        raise _errors.OpticalValueError(
            "scaled_fresnel_input_chirp_too_narrow",
            "带尺度 Fresnel 的输入二次相位啁啾已经超出输入采样的奈奎斯特；"
            "请增大传播距离、扩大输入窗口或调整采样间距",
        )
    if (
        is_value_readable(sampling_facts.transform_coupling_too_narrow)
        and bool(sampling_facts.transform_coupling_too_narrow)
    ):
        raise _errors.OpticalValueError(
            "scaled_fresnel_transform_coupling_too_narrow",
            "带尺度 Fresnel 的双线性变换耦合（携带放大率）已经超出正反向采样"
            "奈奎斯特；请增大传播距离、扩大输入或目标窗口或调整采样间距",
        )
    if (
        is_value_readable(sampling_facts.output_chirp_too_narrow)
        and bool(sampling_facts.output_chirp_too_narrow)
    ):
        raise _errors.OpticalValueError(
            "scaled_fresnel_output_chirp_too_narrow",
            "带尺度 Fresnel 的输出二次相位啁啾已经超出目标采样的奈奎斯特；"
            "请增大传播距离、扩大目标窗口或调整采样间距",
        )
    _validate_numerical_shapes(
        field=field,
        input_chirp=calculation.input_chirp,
        output_chirp=calculation.output_chirp,
        computational_counts=window_facts.computational_counts,
        destination_grid=destination_grid,
    )
    return _PreparedScaledFresnel(
        computational_counts=window_facts.computational_counts,
        padding=window_facts.padding,
        distance=distance,
        calculation=calculation,
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
            "scaled_fresnel_isolated_destination_outside_support",
            "孤立外部的目标足迹超出源采样窗口的零延拓支撑；"
            "请扩大输入窗口、调整目标尺度或改用周期外部",
        )


def _validate_numerical_shapes(
    *,
    field: OpticalField,
    input_chirp: torch.Tensor,
    output_chirp: torch.Tensor,
    computational_counts: tuple[int, int],
    destination_grid: SpatialGrid,
) -> None:
    if tuple(field.envelope.shape[-2:]) != field.grid.sample_counts:
        raise _errors.OpticalValueError(
            "scaled_fresnel_envelope_window_mismatch",
            f"包络的空间形状 {tuple(field.envelope.shape[-2:])} 与传播窗口 "
            f"{field.grid.sample_counts} 不一致，传播窗口必须与输入网格的采样数相同",
        )
    if input_chirp.shape[0] != field.envelope.shape[-4]:
        raise _errors.OpticalValueError(
            "scaled_fresnel_input_chirp_spectrum_mismatch",
            f"输入二次相位的光谱维长度 {input_chirp.shape[0]} 与包络的光谱维长度 "
            f"{field.envelope.shape[-4]} 不一致，二次相位必须逐波长对应",
        )
    if tuple(input_chirp.shape[-2:]) != computational_counts:
        raise _errors.OpticalValueError(
            "scaled_fresnel_input_chirp_grid_mismatch",
            f"输入二次相位的空间形状 {tuple(input_chirp.shape[-2:])} 与计算网格 "
            f"{computational_counts} 不一致，二次相位必须在零延拓后的网格上给出",
        )
    if output_chirp.shape[0] != field.envelope.shape[-4]:
        raise _errors.OpticalValueError(
            "scaled_fresnel_output_chirp_spectrum_mismatch",
            f"输出二次相位的光谱维长度 {output_chirp.shape[0]} 与包络的光谱维长度 "
            f"{field.envelope.shape[-4]} 不一致，二次相位必须逐波长对应",
        )
    if tuple(output_chirp.shape[-2:]) != destination_grid.sample_counts:
        raise _errors.OpticalValueError(
            "scaled_fresnel_output_chirp_grid_mismatch",
            f"输出二次相位的空间形状 {tuple(output_chirp.shape[-2:])} "
            f"与目标网格 {destination_grid.sample_counts} 不一致，"
            "二次相位必须在目标采样上给出",
        )


def _validate_axial_distance(axial_distance: object) -> None:
    if not is_nonzero_finite_fixed_double_scalar(axial_distance):
        raise _errors.OpticalValueError(
            "scaled_fresnel_axial_distance_invalid",
            "带尺度 Fresnel 的轴向距离须是有限的非零实数米值，"
            "零值不合法（近轴 Collins 积分需要非零传播距离），"
            f"收到的是 {axial_distance!r}",
        )


def _validate_exterior(exterior: object) -> None:
    if not isinstance(exterior, PropagationExterior):
        raise _errors.OpticalTypeError(
            "scaled_fresnel_exterior_invalid",
            "传播外部须从周期延拓与孤立零场两种约定中选一个，"
            f"收到的是 {exterior!r}",
        )


def _validate_destination_grid(destination_grid: object) -> None:
    if not isinstance(destination_grid, SpatialGrid):
        raise _errors.OpticalTypeError(
            "scaled_fresnel_destination_grid_invalid",
            "目标网格须是空间网格，带尺度 Fresnel 传播必须显式给出目标网格，"
            f"收到的是 {type(destination_grid).__name__}",
        )

from __future__ import annotations

import math

import torch

from chromatix_next._numerics.wave_propagation.aplanatic_focus import (
    aplanatic_focus_applicability,
    aplanatic_focus_envelope,
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
from ..grid import SpatialGrid
from ..polarization import PolarizationRepresentation


def aplanatic_focus(
    field: OpticalField,
    *,
    focal_length: float | torch.Tensor,
    maximum_convergence_angle: float | torch.Tensor,
    axial_distance_from_focus: float | torch.Tensor,
    destination_grid: SpatialGrid,
) -> OpticalField:
    """
    通过理想消球差物镜把横向入瞳光场聚焦到指定平面

    Args:
        field: 待处理的入射光场
        focal_length: 薄透镜或聚焦模型的焦距
        maximum_convergence_angle: 物镜模型接纳的最大会聚半角
        axial_distance_from_focus: 目标平面相对焦面的有符号轴向距离
        destination_grid: 传播结果必须配准到的目标空间网格

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    _validate_field(field)
    _validate_fixed_positive_scalar(
        focal_length,
        identity="aplanatic_focus_focal_length_invalid",
        gradient_identity="aplanatic_focus_focal_length_requires_grad",
        quantity_name="焦距",
    )
    _validate_maximum_convergence_angle(maximum_convergence_angle)
    _validate_axial_distance(axial_distance_from_focus)
    _validate_destination_grid(destination_grid)
    _validate_fixed_grid(field.grid, is_destination=False)
    _validate_fixed_grid(destination_grid, is_destination=True)
    distance, wavelengths, refractive_indices = (
        _field_state._propagation_spectrum(
            field,
            axial_distance_from_focus,
            reference=field.envelope.real,
        )
    )
    aligned_focal_length = torch.as_tensor(
        focal_length,
        dtype=field.envelope.real.dtype,
        device=field.envelope.device,
    )
    aligned_maximum_convergence_angle = torch.as_tensor(
        maximum_convergence_angle,
        dtype=field.envelope.real.dtype,
        device=field.envelope.device,
    )
    _validate_applicability(
        field=field,
        destination_grid=destination_grid,
        focal_length=aligned_focal_length,
        maximum_convergence_angle=aligned_maximum_convergence_angle,
        axial_distance_from_focus=distance,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
    )
    focused = aplanatic_focus_envelope(
        envelope=field.envelope,
        input_sample_counts=field.grid.sample_counts,
        input_signed_spacing=field.grid.signed_spacing,
        input_first_sample_position=field.grid.first_sample_position,
        output_sample_counts=destination_grid.sample_counts,
        output_signed_spacing=destination_grid.signed_spacing,
        output_first_sample_position=destination_grid.first_sample_position,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        focal_length=aligned_focal_length,
        maximum_convergence_angle=aligned_maximum_convergence_angle,
        axial_distance_from_focus=distance,
    )
    return _transform_field(
        field,
        envelope=focused,
        grid=destination_grid,
        polarization_representation=PolarizationRepresentation.FULL,
        path_reference=_field_state._advance_path_reference(
            field=field,
            axial_distances=(
                focal_length,
                axial_distance_from_focus,
            ),
        ),
    )

class AplanaticFocus(torch.nn.Module):
    """
    拥有理想物镜几何并委托配对聚焦动作

    Args:
        focal_length: 薄透镜或聚焦模型的焦距
        maximum_convergence_angle: 物镜模型接纳的最大会聚半角
        axial_distance_from_focus: 目标平面相对焦面的有符号轴向距离
        destination_grid: 传播结果必须配准到的目标空间网格

    Raises:
        OpticalTypeError: 输入对象物理类型不满足该 Interface
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    focal_length: torch.Tensor
    maximum_convergence_angle: torch.Tensor
    axial_distance_from_focus: torch.Tensor

    def __init__(
        self,
        *,
        focal_length: float | torch.Tensor,
        maximum_convergence_angle: float | torch.Tensor,
        axial_distance_from_focus: float | torch.Tensor,
        destination_grid: SpatialGrid,
    ) -> None:
        super().__init__()
        _validate_fixed_positive_scalar(
            focal_length,
            identity="aplanatic_focus_focal_length_invalid",
            gradient_identity=(
                "aplanatic_focus_focal_length_requires_grad"
            ),
            quantity_name="焦距",
        )
        _validate_maximum_convergence_angle(maximum_convergence_angle)
        _validate_axial_distance(axial_distance_from_focus)
        _validate_destination_grid(destination_grid)
        _validate_fixed_grid(destination_grid, is_destination=True)
        register_fixed_double_real_scalar(
            self,
            name="focal_length",
            value=focal_length,
        )
        register_fixed_double_real_scalar(
            self,
            name="maximum_convergence_angle",
            value=maximum_convergence_angle,
        )
        register_fixed_double_real_scalar(
            self,
            name="axial_distance_from_focus",
            value=axial_distance_from_focus,
        )
        self._destination_grid_state = _GridState(destination_grid)

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
        聚焦目标空间网格；入瞳光场采样几何须与之确定且固定

        Returns:
            该聚焦作用使用的目标 SpatialGrid

        """
        return self._destination_grid_state.value

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        把横向入瞳光场通过理想物镜聚焦到目标平面

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """
        return aplanatic_focus(
            field,
            focal_length=self.focal_length,
            maximum_convergence_angle=self.maximum_convergence_angle,
            axial_distance_from_focus=self.axial_distance_from_focus,
            destination_grid=self.destination_grid,
        )

    def _validate_physical_state(self) -> None:
        _validate_fixed_positive_scalar(
            self.focal_length,
            identity="aplanatic_focus_focal_length_invalid",
            gradient_identity=(
                "aplanatic_focus_focal_length_requires_grad"
            ),
            quantity_name="焦距",
        )
        _validate_maximum_convergence_angle(
            self.maximum_convergence_angle,
        )
        _validate_axial_distance(self.axial_distance_from_focus)

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        del field
        return self.destination_grid


def _validate_field(field: object) -> None:
    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "aplanatic_focus_field_invalid",
            "消球差聚焦只能作用于光场",
        )
    if (
        field.polarization_representation
        is not PolarizationRepresentation.TRANSVERSE
    ):
        raise _errors.OpticalValueError(
            "aplanatic_focus_polarization_unsupported",
            "消球差聚焦要求具有两个横向分量的入瞳光场",
        )
    if field.normalization is not FieldNormalization.RELATIVE:
        raise _errors.OpticalValueError(
            "aplanatic_focus_normalization_unsupported",
            "消球差聚焦当前只接受相对场归一化",
        )


def _validate_fixed_positive_scalar(
    value: object,
    *,
    identity: str,
    gradient_identity: str,
    quantity_name: str,
) -> None:
    if not is_finite_fixed_double_scalar(value):
        raise _errors.OpticalValueError(
            identity,
            f"{quantity_name}必须是有限的零维实数",
        )
    if isinstance(value, torch.Tensor):
        if value.requires_grad:
            raise _errors.OpticalValueError(
                gradient_identity,
                f"{quantity_name}属于固定几何，不能要求梯度",
            )
        if value.is_meta:
            return
        is_positive = value > 0.0
        if not bool(is_positive):
            raise _errors.OpticalValueError(
                identity,
                f"{quantity_name}必须严格大于零",
            )
        return
    assert isinstance(value, (int, float))
    if value <= 0.0:
        raise _errors.OpticalValueError(
            identity,
            f"{quantity_name}必须严格大于零",
        )


def _validate_maximum_convergence_angle(value: object) -> None:
    _validate_fixed_positive_scalar(
        value,
        identity="aplanatic_focus_maximum_convergence_angle_invalid",
        gradient_identity=(
            "aplanatic_focus_maximum_convergence_angle_requires_grad"
        ),
        quantity_name="最大会聚半角",
    )
    if isinstance(value, torch.Tensor):
        if value.is_meta:
            return
        is_below_right_angle = value < math.pi / 2.0
        if not bool(is_below_right_angle):
            raise _errors.OpticalValueError(
                "aplanatic_focus_maximum_convergence_angle_invalid",
                "最大会聚半角必须严格小于 π/2",
            )
        return
    assert isinstance(value, (int, float))
    if value >= math.pi / 2.0:
        raise _errors.OpticalValueError(
            "aplanatic_focus_maximum_convergence_angle_invalid",
            "最大会聚半角必须严格小于 π/2",
        )


def _validate_axial_distance(value: object) -> None:
    if not is_finite_fixed_double_scalar(value):
        raise _errors.OpticalValueError(
            "aplanatic_focus_axial_distance_invalid",
            "离焦轴向距离必须是有限的零维实数",
        )


def _validate_destination_grid(value: object) -> None:
    if not isinstance(value, SpatialGrid):
        raise _errors.OpticalTypeError(
            "aplanatic_focus_destination_grid_invalid",
            "消球差聚焦必须显式给出目标空间网格",
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
            "aplanatic_focus_destination_grid_requires_grad"
            if is_destination
            else "aplanatic_focus_input_grid_requires_grad"
        )
        raise _errors.OpticalValueError(
            identity,
            "入瞳与目标网格属于固定采样几何，不能要求梯度",
        )


def _validate_applicability(
    *,
    field: OpticalField,
    destination_grid: SpatialGrid,
    focal_length: torch.Tensor,
    maximum_convergence_angle: torch.Tensor,
    axial_distance_from_focus: torch.Tensor,
    wavelengths: torch.Tensor,
    refractive_indices: torch.Tensor,
) -> None:
    reference = field.envelope.real
    if refractive_indices.requires_grad:
        raise _errors.OpticalValueError(
            "aplanatic_focus_medium_requires_grad",
            "消球差聚焦当前把介质色散视为固定几何，不能要求梯度",
        )
    (
        is_beyond_objective,
        footprint_contains_disk,
        maximum_phase_increment,
    ) = aplanatic_focus_applicability(
        input_sample_counts=field.grid.sample_counts,
        input_signed_spacing=field.grid.signed_spacing,
        input_first_sample_position=field.grid.first_sample_position,
        output_sample_counts=destination_grid.sample_counts,
        output_signed_spacing=destination_grid.signed_spacing,
        output_first_sample_position=destination_grid.first_sample_position,
        wavelengths=wavelengths,
        refractive_indices=refractive_indices,
        focal_length=focal_length,
        maximum_convergence_angle=maximum_convergence_angle,
        axial_distance_from_focus=axial_distance_from_focus,
        reference=reference,
    )
    if is_value_readable(is_beyond_objective) and not bool(
        is_beyond_objective,
    ):
        raise _errors.OpticalValueError(
            "aplanatic_focus_plane_not_beyond_objective",
            "目标平面必须位于物镜之后，即焦距与离焦距离之和严格大于零",
        )
    if is_value_readable(footprint_contains_disk) and not bool(
        footprint_contains_disk,
    ):
        raise _errors.OpticalValueError(
            "aplanatic_focus_objective_disk_not_contained",
            "入瞳采样单元的完整覆盖范围必须包含物镜圆盘",
        )
    is_aliased = maximum_phase_increment > math.pi
    if is_value_readable(is_aliased) and bool(is_aliased):
        raise _errors.OpticalValueError(
            "aplanatic_focus_phase_increment_aliased",
            "入瞳相邻样本在目标窗口角点的展开相位增量不得超过 π",
        )

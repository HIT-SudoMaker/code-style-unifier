from __future__ import annotations

import torch

from chromatix_next._numerics.wave_propagation.fresnel_transform import (
    fresnel_output_spacing,
    fresnel_transform_envelope,
)
from chromatix_next._tensors import (
    is_nonzero_finite_fixed_double_scalar,
    register_fixed_double_real_scalar,
)
import chromatix_next.errors as _errors

from . import _field_state
from .._role_contract import _PropagationRole
from ..field import OpticalField, _transform_field
from ..grid import SpatialGrid
from ..polarization import PolarizationRepresentation


def _validate_axial_distance(axial_distance: object) -> None:
    if is_nonzero_finite_fixed_double_scalar(axial_distance):
        return
    raise _errors.OpticalValueError(
        "fresnel_transform_axial_distance_invalid",
        "Fresnel 变换的轴向距离必须是有限非零实数米值",
    )

def _resolve_fresnel(
    field: OpticalField,
    axial_distance: float | torch.Tensor,
    reference: torch.Tensor,
) -> tuple[SpatialGrid, torch.Tensor, torch.Tensor]:
    _validate_axial_distance(axial_distance)
    if field.spectrum.count != 1:
        raise _errors.OpticalValueError(
            "fresnel_transform_spectrum_not_monochromatic",
            "Fresnel 变换的每个波长需要不同输出采样，当前入口只接受单色光场",
        )
    propagation_state = _field_state._propagation_spectrum(
        field,
        axial_distance,
        reference=reference,
    )
    distance, wavelengths, refractive_indices = propagation_state
    wavelength_distance = wavelengths[0] * distance / refractive_indices[0]
    output_spacing = fresnel_output_spacing(
        sample_counts=field.grid.sample_counts,
        input_spacing=field.grid.sample_spacing,
        wavelength_distance=wavelength_distance,
    )
    output_grid = SpatialGrid.centered(
        sample_counts=field.grid.sample_counts,
        sample_spacing=output_spacing,
        orientation=field.grid.orientation,
    )
    return output_grid, distance, wavelength_distance


def fresnel_transform(
    field: OpticalField,
    *,
    axial_distance: float | torch.Tensor,
) -> OpticalField:
    """
    以单次傅里叶变换作单色 Fresnel 传播

    Args:
        field: 待处理的入射光场
        axial_distance: 沿传播轴的有符号距离

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "fresnel_transform_field_invalid",
            "Fresnel 变换只能作用于光场",
        )
    if field.polarization_representation is PolarizationRepresentation.FULL:
        raise _errors.OpticalValueError(
            "fresnel_transform_polarization_full_unsupported",
            "标量传播在均匀各向同性偏振中性近似下只作用于标量或横向光场；"
            "完整矢量光场请使用矢量角谱传播",
        )
    fresnel_state = _resolve_fresnel(
        field,
        axial_distance,
        field.envelope.real,
    )
    output_grid, _, wavelength_distance = fresnel_state
    propagated = fresnel_transform_envelope(
        envelope=field.envelope,
        sample_counts=field.grid.sample_counts,
        input_signed_spacing=field.grid.signed_spacing,
        input_first_sample_position=field.grid.first_sample_position,
        output_signed_spacing=output_grid.signed_spacing,
        output_first_sample_position=output_grid.first_sample_position,
        wavelength_distance=wavelength_distance,
    )
    return _transform_field(
        field,
        envelope=propagated,
        grid=output_grid,
        path_reference=_field_state._advance_path_reference(
            field=field,
            axial_distances=(axial_distance,),
        ),
    )


class FresnelTransform(torch.nn.Module):
    """
    拥有非零轴向距离的单色 Fresnel 变换传播

    Args:
        axial_distance: 沿传播轴的有符号距离

    Raises:
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    axial_distance: torch.Tensor

    def __init__(self, *, axial_distance: float | torch.Tensor) -> None:

        super().__init__()
        _validate_axial_distance(axial_distance)
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

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        以单次 FFT 把单色入射光场作近轴 Fresnel 传播

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """

        return fresnel_transform(
            field,
            axial_distance=self.axial_distance,
        )

    def _validate_physical_state(self) -> None:
        _validate_axial_distance(self.axial_distance)

    def _output_grid_for(self, field: OpticalField) -> SpatialGrid:
        return _resolve_fresnel(
            field,
            self.axial_distance,
            field.grid.sample_spacing[0],
        )[0]

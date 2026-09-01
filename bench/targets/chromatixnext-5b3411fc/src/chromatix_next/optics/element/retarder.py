from __future__ import annotations

import math

import torch

from chromatix_next._numerics.jones_calculus import _retarder_envelope
from chromatix_next._tensors import (
    is_finite_fixed_double_scalar,
    is_finite_fixed_double_scalar_in_closed_interval,
    register_fixed_double_real_scalar,
)
import chromatix_next.errors as _errors

from .._role_contract import _ElementRole
from ..field import OpticalField, _transform_field
from ..polarization import PolarizationRepresentation


def _validate_retardance_cycles(retardance_cycles: object) -> None:
    if not is_finite_fixed_double_scalar(retardance_cycles):
        raise _errors.OpticalValueError(
            "retarder_retardance_cycles_invalid",
            "延迟量必须是以周期计的有限实数标量",
        )

def _validate_retarded_eigenstate_azimuth_radians(
    retarded_eigenstate_azimuth_radians: object,
) -> None:
    if not is_finite_fixed_double_scalar(retarded_eigenstate_azimuth_radians):
        raise _errors.OpticalValueError(
            "retarder_retarded_eigenstate_azimuth_radians_invalid",
            "延迟本征态方位角必须是以弧度计的有限实数标量",
        )


def _validate_retarded_eigenstate_ellipticity_radians(
    retarded_eigenstate_ellipticity_radians: object,
) -> None:
    lower_bound = -math.pi / 4.0
    upper_bound = math.pi / 4.0
    if not is_finite_fixed_double_scalar_in_closed_interval(
        retarded_eigenstate_ellipticity_radians,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    ):
        raise _errors.OpticalValueError(
            "retarder_retarded_eigenstate_ellipticity_radians_invalid",
            "延迟本征态椭率角必须是 [-pi/4, +pi/4] 内的有限实数标量",
        )


def retarder(
    field: OpticalField,
    *,
    retardance_cycles: float | torch.Tensor,
    retarded_eigenstate_azimuth_radians: float | torch.Tensor,
    retarded_eigenstate_ellipticity_radians: float | torch.Tensor,
) -> OpticalField:
    """
    在横向二分量光场上施加理想零均值 SU(2) 延迟

    Args:
        field: 待处理的入射光场
        retardance_cycles: 两个偏振本征态之间以周期表示的相位延迟
        retarded_eigenstate_azimuth_radians: 慢轴本征态在局部偏振平面的方位角
        retarded_eigenstate_ellipticity_radians: 慢轴本征态的椭圆率角

    Returns:
        输出保留输入采样和谱道语义的复振幅光场

    Raises:
        OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    if not isinstance(field, OpticalField):
        raise _errors.OpticalTypeError(
            "retarder_field_invalid",
            "延迟器只能作用于光场",
        )
    if (
        field.polarization_representation
        is not PolarizationRepresentation.TRANSVERSE
    ):
        raise _errors.OpticalValueError(
            "retarder_polarization_representation_invalid",
            "延迟器需要按 Ex、Ey 排列的横向二分量光场",
        )
    _validate_retardance_cycles(retardance_cycles)
    _validate_retarded_eigenstate_azimuth_radians(
        retarded_eigenstate_azimuth_radians,
    )
    _validate_retarded_eigenstate_ellipticity_radians(
        retarded_eigenstate_ellipticity_radians,
    )
    real_dtype = field.envelope.real.dtype
    device = field.envelope.device
    aligned_retardance_cycles = torch.as_tensor(
        retardance_cycles,
        device=device,
        dtype=real_dtype,
    )
    aligned_retarded_eigenstate_azimuth_radians = torch.as_tensor(
        retarded_eigenstate_azimuth_radians,
        device=device,
        dtype=real_dtype,
    )
    aligned_retarded_eigenstate_ellipticity_radians = torch.as_tensor(
        retarded_eigenstate_ellipticity_radians,
        device=device,
        dtype=real_dtype,
    )
    output_envelope = _retarder_envelope(
        envelope=field.envelope,
        retardance_cycles=aligned_retardance_cycles,
        retarded_eigenstate_azimuth_radians=(
            aligned_retarded_eigenstate_azimuth_radians
        ),
        retarded_eigenstate_ellipticity_radians=(
            aligned_retarded_eigenstate_ellipticity_radians
        ),
    )
    return _transform_field(
        field,
        envelope=output_envelope,
    )


class Retarder(torch.nn.Module):
    """
    拥有延迟量、延迟本征态方位角与椭率角的理想零均值 SU(2) 延迟器

    Args:
        retardance_cycles: 两个偏振本征态之间以周期表示的相位延迟
        retarded_eigenstate_azimuth_radians: 慢轴本征态在局部偏振平面的方位角
        retarded_eigenstate_ellipticity_radians: 慢轴本征态的椭圆率角

    Raises:
        OpticalValueError: 输入数值/形状/精度/适用域不满足契约

    """

    retardance_cycles: torch.Tensor
    retarded_eigenstate_azimuth_radians: torch.Tensor
    retarded_eigenstate_ellipticity_radians: torch.Tensor

    def __init__(
        self,
        *,
        retardance_cycles: float | torch.Tensor,
        retarded_eigenstate_azimuth_radians: float | torch.Tensor,
        retarded_eigenstate_ellipticity_radians: float | torch.Tensor,
    ) -> None:

        super().__init__()
        _validate_retardance_cycles(retardance_cycles)
        _validate_retarded_eigenstate_azimuth_radians(
            retarded_eigenstate_azimuth_radians,
        )
        _validate_retarded_eigenstate_ellipticity_radians(
            retarded_eigenstate_ellipticity_radians,
        )
        register_fixed_double_real_scalar(
            self,
            name="retardance_cycles",
            value=retardance_cycles,
        )
        register_fixed_double_real_scalar(
            self,
            name="retarded_eigenstate_azimuth_radians",
            value=retarded_eigenstate_azimuth_radians,
        )
        register_fixed_double_real_scalar(
            self,
            name="retarded_eigenstate_ellipticity_radians",
            value=retarded_eigenstate_ellipticity_radians,
        )

    @property
    def role(self) -> _ElementRole:
        """
        元件角色字面量

        Returns:
            返回该组件声明的 Element 角色

        """

        return "element"

    def forward(self, field: OpticalField) -> OpticalField:  # type: ignore[override]
        """
        对横向偏振施加零均值 SU(2) 延迟

        Args:
            field: 待处理的入射光场

        Returns:
            输出保留输入采样和谱道语义的复振幅光场

        """

        return retarder(
            field,
            retardance_cycles=self.retardance_cycles,
            retarded_eigenstate_azimuth_radians=(
                self.retarded_eigenstate_azimuth_radians
            ),
            retarded_eigenstate_ellipticity_radians=(
                self.retarded_eigenstate_ellipticity_radians
            ),
        )

    def _validate_physical_state(self) -> None:
        _validate_retardance_cycles(self.retardance_cycles)
        _validate_retarded_eigenstate_azimuth_radians(
            self.retarded_eigenstate_azimuth_radians,
        )
        _validate_retarded_eigenstate_ellipticity_radians(
            self.retarded_eigenstate_ellipticity_radians,
        )

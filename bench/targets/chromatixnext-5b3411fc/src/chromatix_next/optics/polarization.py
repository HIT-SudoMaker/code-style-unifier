from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

import chromatix_next.errors as _errors


class PolarizationRepresentation(str, Enum):
    """
    支持的光场偏振表示

    """

    SCALAR = "scalar"
    TRANSVERSE = "transverse"
    FULL = "full"

    @property
    def component_count(self) -> int:
        """
        返回该偏振表示拥有的显式场分量数

        Returns:
            返回偏振表示的分量数量

        """
        return _COMPONENT_COUNT[self]


_COMPONENT_COUNT = {
    PolarizationRepresentation.SCALAR: 1,
    PolarizationRepresentation.TRANSVERSE: 2,
    PolarizationRepresentation.FULL: 3,
}


@dataclass(frozen=True, slots=True)
class Polarization:
    """
    在负时间指数约定下归一化的不可变复偏振状态

    Args:
        representation: 偏振分量采用的表示方式
        components: 依照表示方式排列的复偏振分量

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    representation: PolarizationRepresentation
    components: tuple[complex, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.representation, PolarizationRepresentation):
            raise _errors.OpticalValueError(
                "polarization_representation_invalid",
                "偏振表示只能取标量、横向、完整三者之一，"
                f"收到的是 {self.representation!r}",
            )
        expected_count = _COMPONENT_COUNT[self.representation]
        if (
            not isinstance(self.components, tuple)
            or len(self.components) != expected_count
        ):
            raise _errors.OpticalValueError(
                "polarization_state_component_count_invalid",
                f"该偏振表示需要 {expected_count} 个复振幅分量，"
                f"收到的是 {self.components!r}",
            )
        if any(
            isinstance(component, bool)
            or not isinstance(component, (int, float, complex))
            for component in self.components
        ):
            raise _errors.OpticalValueError(
                "polarization_state_invalid",
                "琼斯矢量只接受 Python 实数或复数分量，不接受 Tensor 或布尔值，"
                f"收到的是 {self.components!r}",
            )
        components = tuple(
            complex(component) for component in self.components
        )
        if any(
            not math.isfinite(component.real)
            or not math.isfinite(component.imag)
            for component in components
        ):
            raise _errors.OpticalValueError(
                "polarization_state_nonfinite",
                "琼斯矢量各分量的实部与虚部都必须是有限值，"
                f"收到的是 {components!r}",
            )
        norm_squared = sum(
            abs(component) * abs(component) for component in components
        )
        if not math.isfinite(norm_squared):
            raise _errors.OpticalValueError(
                "polarization_state_norm_nonfinite",
                "各分量的模方之和已溢出，无法归一化，请把振幅缩到合理量级，"
                f"收到的是 {components!r}",
            )
        if norm_squared == 0.0:
            raise _errors.OpticalValueError(
                "polarization_state_zero",
                "全零琼斯矢量没有确定的偏振方向，请至少给出一个非零分量",
            )
        norm = math.sqrt(norm_squared)
        normalized = tuple(component / norm for component in components)
        object.__setattr__(self, "components", normalized)

    @classmethod
    def _restore_normalized_state(
        cls,
        *,
        representation: PolarizationRepresentation,
        components: tuple[complex, ...],
    ) -> "Polarization":
        if not isinstance(representation, PolarizationRepresentation):
            raise _errors.OpticalValueError(
                "polarization_restored_representation_invalid",
                "还原偏振态时给的表示不是标量、横向、完整中的任何一种，"
                f"收到的是 {representation!r}",
            )
        expected_count = _COMPONENT_COUNT[representation]
        if (
            not isinstance(components, tuple)
            or len(components) != expected_count
        ):
            raise _errors.OpticalValueError(
                "polarization_restored_component_count_invalid",
                f"还原的偏振态在该表示下应有 {expected_count} 个分量，"
                f"收到的是 {components!r}",
            )
        if any(
            not isinstance(component, complex)
            or not math.isfinite(component.real)
            or not math.isfinite(component.imag)
            for component in components
        ):
            raise _errors.OpticalValueError(
                "polarization_restored_state_invalid",
                "还原的琼斯矢量分量必须已经是有限的复振幅，"
                f"收到的是 {components!r}",
            )
        norm_squared = sum(abs(component) ** 2 for component in components)
        if not math.isclose(
            norm_squared,
            1.0,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise _errors.OpticalValueError(
                "polarization_restored_state_not_normalized",
                "还原的偏振态应当已归一化，各分量模方之和须为 1，"
                f"收到的是 {norm_squared!r}",
            )
        restored = object.__new__(cls)
        object.__setattr__(restored, "representation", representation)
        object.__setattr__(restored, "components", components)
        return restored

    @classmethod
    def scalar(cls) -> "Polarization":
        """
        构造不冒充实验室坐标偏振的标量表示

        Returns:
            返回标量偏振分量

        """
        return cls(
            PolarizationRepresentation.SCALAR,
            (1.0 + 0.0j,),
        )

    @classmethod
    def linear_x(cls) -> "Polarization":
        """
        构造实验室坐标 x 线偏振

        Returns:
            返回沿局部 x 轴的线偏振分量

        """
        return cls.transverse(components=(1.0, 0.0))

    @classmethod
    def linear_y(cls) -> "Polarization":
        """
        构造实验室坐标 y 线偏振

        Returns:
            返回沿局部 y 轴的线偏振分量

        """
        return cls.transverse(components=(0.0, 1.0))

    @classmethod
    def left_circular(cls) -> "Polarization":
        """
        构造正 z 传播下的左圆偏振

        Returns:
            返回左旋圆偏振分量

        """
        scale = 1.0 / math.sqrt(2.0)
        return cls.transverse(
            components=(scale, -1j * scale),
        )

    @classmethod
    def right_circular(cls) -> "Polarization":
        """
        构造正 z 传播下的右圆偏振

        Returns:
            返回右旋圆偏振分量

        """
        scale = 1.0 / math.sqrt(2.0)
        return cls.transverse(
            components=(scale, 1j * scale),
        )

    @classmethod
    def transverse(
        cls,
        *,
        components: tuple[complex, complex] = (1.0, 0.0),
    ) -> "Polarization":
        """
        构造按 Ex、Ey 排列的横向偏振

        Args:
            components: 依照表示方式排列的复偏振分量

        Returns:
            返回横向偏振分量

        """
        return cls(
            PolarizationRepresentation.TRANSVERSE,
            components,
        )

    @classmethod
    def full(
        cls,
        *,
        components: tuple[complex, complex, complex] = (1.0, 0.0, 0.0),
    ) -> "Polarization":
        """
        构造按 Ex、Ey、Ez 排列的完整偏振

        Args:
            components: 依照表示方式排列的复偏振分量

        Returns:
            返回完整三维偏振分量

        """
        return cls(
            PolarizationRepresentation.FULL,
            components,
        )

    @property
    def component_count(self) -> int:
        """
        返回偏振表示的显式分量数

        Returns:
            返回偏振表示的分量数量

        """
        return self.representation.component_count

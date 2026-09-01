from __future__ import annotations

import abc
from dataclasses import dataclass
import math
from typing import Any

import torch

import chromatix_next.errors as _errors

from .._tensors import is_value_readable


def _validate_wavelength_query(wavelengths: object) -> torch.Tensor:
    if not isinstance(wavelengths, torch.Tensor):
        raise _errors.OpticalTypeError(
            "medium_wavelength_query_invalid",
            "查询折射率的波长必须以张量给出，"
            f"收到的是 {type(wavelengths).__name__}",
        )
    if (
        wavelengths.dim() != 1
        or wavelengths.numel() == 0
        or torch.is_complex(wavelengths)
        or wavelengths.dtype is not torch.float64
    ):
        raise _errors.OpticalValueError(
            "medium_wavelength_query_invalid",
            "查询波长必须排成非空的一维 float64 实浮点序列（固定双精度核，"
            "不再静默镜像输入 dtype——请在上游以 float64 构造），"
            f"收到的是形状 {tuple(wavelengths.shape)}、"
            f"精度 {wavelengths.dtype}",
        )
    # meta 同样执行谓词张量核以进入内存轨迹，只跳过布尔读取
    is_finite = torch.isfinite(wavelengths).all()
    is_positive = (wavelengths > 0).all()
    if is_value_readable(is_finite) and (
        not bool(is_finite)
        or not bool(is_positive)
    ):
        raise _errors.OpticalValueError(
            "medium_wavelength_query_invalid",
            "每个查询波长都必须是有限正值，"
            f"收到的是形状 {tuple(wavelengths.shape)}、"
            f"精度 {wavelengths.dtype}",
        )
    return wavelengths

def _validate_refractive_index_output(
    refractive_indices: object,
    wavelengths: torch.Tensor,
) -> torch.Tensor:
    # 第三方公式与内建公式共享唯一输出边界，不允许悄然改形状、精度或设备
    if not isinstance(refractive_indices, torch.Tensor):
        raise _errors.OpticalTypeError(
            "medium_refractive_index_output_invalid",
            "介质的色散公式必须逐波长返回折射率张量，"
            f"收到的是 {type(refractive_indices).__name__}",
        )
    # 结构先查，取值后查：复数张量不能被拿去做大小比较，meta 张量没有取值
    is_structure_invalid = (
        refractive_indices.shape != wavelengths.shape
        or refractive_indices.dtype is not wavelengths.dtype
        or refractive_indices.device != wavelengths.device
        or torch.is_complex(refractive_indices)
        or not refractive_indices.is_floating_point()
    )
    if is_structure_invalid:
        raise _errors.OpticalValueError(
            "medium_refractive_index_output_invalid",
            "折射率必须逐项为有限正实数，并与查询波长同形状、同精度、同设备，"
            f"收到的是形状 {tuple(refractive_indices.shape)}、"
            f"精度 {refractive_indices.dtype}",
        )
    is_finite = torch.isfinite(refractive_indices).all()
    is_positive = (refractive_indices > 0).all()
    if is_value_readable(is_finite) and (
        not bool(is_finite)
        or not bool(is_positive)
    ):
        raise _errors.OpticalValueError(
            "medium_refractive_index_output_invalid",
            "折射率必须逐项为有限正实数，并与查询波长同形状、同精度、同设备，"
            f"收到的是形状 {tuple(refractive_indices.shape)}、"
            f"精度 {refractive_indices.dtype}",
        )
    return refractive_indices


def _is_physical_identity_payload_valid(value: object) -> bool:
    if isinstance(value, tuple):
        return all(_is_physical_identity_payload_valid(item) for item in value)
    if isinstance(value, bool) or value is None:
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, complex):
        return math.isfinite(value.real) and math.isfinite(value.imag)
    return isinstance(value, (str, bytes))


class Medium(abc.ABC):
    """
    传播介质的抽象接口，按波长返回正实折射率

    """

    def __init_subclass__(cls) -> None:

        super().__init_subclass__()
        if getattr(cls, "refractive_index") is not Medium.refractive_index:
            raise _errors.OpticalTypeError(
                "medium_refractive_index_override_forbidden",
                f"介质 {cls.__name__} 不得改写折射率查询入口，"
                "波长与折射率的守卫都在此入口，色散公式请写进私有求值方法",
            )
        if getattr(cls, "physical_identity") is not Medium.physical_identity:
            raise _errors.OpticalTypeError(
                "medium_physical_identity_override_forbidden",
                f"介质 {cls.__name__} 不得改写物理身份入口，"
                "决定该介质光学行为的固定参数请由私有身份方法声明",
            )

    def refractive_index(self, wavelengths: torch.Tensor) -> torch.Tensor:
        """
        经统一查询和输出守卫返回逐波长正实折射率

        Args:
            wavelengths: 以米为单位、严格递增的真空波长

        Returns:
            与 wavelengths 一一对应的 float64 折射率张量

        Raises:
            OpticalTypeError: 输入对象物理类型不满足该 Interface
            OpticalValueError: 输入数值/形状/精度/适用域不满足契约

        """

        query = _validate_wavelength_query(wavelengths)
        refractive_indices = self._evaluate_refractive_index(query)
        return _validate_refractive_index_output(refractive_indices, query)

    @abc.abstractmethod
    def _evaluate_refractive_index(
        self,
        wavelengths: torch.Tensor,
    ) -> torch.Tensor:
        # 仅计算折射率公式；公共输入和输出契约由 refractive_index 拥有
        raise NotImplementedError

    def physical_identity(self) -> tuple[Any, ...]:
        """
        返回类型完整、无张量且确定的介质物理身份

        Returns:
            顺序为 (module_name, qualified_name, parameter_snapshot) 的稳定身份元组

        Raises:
            OpticalTypeError: 输入对象的物理类型不满足该 Interface 契约
            OpticalValueError: 输入数值、形状、精度或适用域不满足契约

        """

        first_payload = self._physical_identity()
        second_payload = self._physical_identity()
        if not isinstance(first_payload, tuple) or not (
            _is_physical_identity_payload_valid(first_payload)
        ):
            raise _errors.OpticalTypeError(
                "medium_physical_identity_invalid",
                "介质的物理身份必须是只含有限标量的元组，不能夹带张量，"
                f"收到的是 {first_payload!r}",
            )
        if not isinstance(second_payload, tuple) or not (
            _is_physical_identity_payload_valid(second_payload)
        ):
            raise _errors.OpticalTypeError(
                "medium_physical_identity_invalid",
                "介质的物理身份必须是只含有限标量的元组，不能夹带张量，"
                f"再次求值得到的是 {second_payload!r}",
            )
        if first_payload != second_payload:
            raise _errors.OpticalValueError(
                "medium_physical_identity_unstable",
                "同一介质两次求值必须给出同一物理身份，否则复用与比对失效，"
                f"两次分别是 {first_payload!r} 与 {second_payload!r}",
            )
        return (
            type(self).__module__,
            type(self).__qualname__,
            first_payload,
        )

    @abc.abstractmethod
    def _physical_identity(self) -> tuple[Any, ...]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Vacuum(Medium):
    """
    折射率恒为 1 的真空介质

    """

    def _evaluate_refractive_index(
        self,
        wavelengths: torch.Tensor,
    ) -> torch.Tensor:
        return torch.ones_like(wavelengths)

    def _physical_identity(self) -> tuple[Any, ...]:
        return ()


@dataclass(frozen=True, slots=True)
class ConstantMedium(Medium):
    """
    对所有波长返回同一恒定折射率的均匀介质

    Args:
        index: 无量纲折射率值

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    index: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.index, (int, float)) or isinstance(
            self.index,
            bool,
        ):
            raise _errors.OpticalValueError(
                "constant_medium_index_invalid",
                "均匀介质的折射率必须是一个实数，"
                f"收到的是 {type(self.index).__name__}",
            )
        if not math.isfinite(float(self.index)):
            raise _errors.OpticalValueError(
                "constant_medium_index_nonfinite",
                "均匀介质的折射率必须是有限值，"
                f"收到的是 {self.index!r}",
            )
        if self.index <= 0.0:
            raise _errors.OpticalValueError(
                "constant_medium_index_invalid",
                "折射率必须为正，真空为 1，常见玻璃在 1.4 至 1.9 之间，"
                f"收到的是 {self.index!r}",
            )

    def _evaluate_refractive_index(
        self,
        wavelengths: torch.Tensor,
    ) -> torch.Tensor:
        return torch.full_like(wavelengths, float(self.index))

    def _physical_identity(self) -> tuple[Any, ...]:
        return (float(self.index),)


@dataclass(frozen=True, slots=True)
class TabulatedMedium(Medium):
    """
    按波长表线性插值的色散介质

    波长以米为单位、严格递增；折射率为正实数。查询波长落在声明范围
    [wavelengths[0], wavelengths[-1]] 之外时，以稳定身份
    ``tabulated_medium_wavelength_out_of_range`` 拒绝，绝不静默外推。

    Args:
        wavelengths: 以米为单位、严格递增的真空波长
        refractive_indices: 与波长逐项对应的折射率

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    wavelengths: tuple[float, ...]
    refractive_indices: tuple[float, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.wavelengths, tuple)
            or len(self.wavelengths) < 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) <= 0.0
                for value in self.wavelengths
            )
        ):
            raise _errors.OpticalValueError(
                "tabulated_medium_wavelengths_invalid",
                "色散表的波长以米为单位，至少要有两个有限正波长才能插值，"
                f"收到的是 {self.wavelengths!r}",
            )
        for first, second in zip(self.wavelengths, self.wavelengths[1:]):
            if float(second) <= float(first):
                raise _errors.OpticalValueError(
                    "tabulated_medium_wavelengths_invalid",
                    "色散表的波长必须严格递增，插值区间才唯一，"
                    f"{first!r} 之后出现了不更大的 {second!r}",
                )
        if (
            not isinstance(self.refractive_indices, tuple)
            or len(self.refractive_indices) != len(self.wavelengths)
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) <= 0.0
                for value in self.refractive_indices
            )
        ):
            raise _errors.OpticalValueError(
                "tabulated_medium_refractive_indices_invalid",
                "色散表里每个波长都要配一个有限正折射率，"
                f"波长有 {len(self.wavelengths)} 个，"
                f"折射率收到的是 {self.refractive_indices!r}",
            )

    def _evaluate_refractive_index(
        self,
        wavelengths: torch.Tensor,
    ) -> torch.Tensor:
        table_wavelengths = torch.tensor(
            self.wavelengths,
            dtype=wavelengths.dtype,
            device=wavelengths.device,
        )
        table_indices = torch.tensor(
            self.refractive_indices,
            dtype=wavelengths.dtype,
            device=wavelengths.device,
        )
        is_below_range = (wavelengths < table_wavelengths[0]).any()
        is_above_range = (wavelengths > table_wavelengths[-1]).any()
        if is_value_readable(is_below_range) and (
            bool(is_below_range)
            or bool(is_above_range)
        ):
            raise _errors.OpticalValueError(
                "tabulated_medium_wavelength_out_of_range",
                f"该介质的色散数据只覆盖 {self.wavelengths[0]!r} 至 "
                f"{self.wavelengths[-1]!r} 米，"
                "表外波长绝不外推，请改用覆盖该波段的介质",
            )
        position = torch.searchsorted(
            table_wavelengths,
            wavelengths,
            right=True,
        )
        position = torch.clamp(position, min=1, max=len(self.wavelengths) - 1)
        wavelength_left = table_wavelengths[position - 1]
        wavelength_right = table_wavelengths[position]
        refractive_index_left = table_indices[position - 1]
        refractive_index_right = table_indices[position]
        slope = (refractive_index_right - refractive_index_left) / (
            wavelength_right - wavelength_left
        )
        return refractive_index_left + slope * (wavelengths - wavelength_left)

    def _physical_identity(self) -> tuple[Any, ...]:
        return (self.wavelengths, self.refractive_indices)


@dataclass(frozen=True, slots=True)
class SellmeierMedium(Medium):
    """
    Sellmeier 色散介质

    折射率满足 n²(λ) = 1 + Σᵢ Bᵢλ² / (λ² − Cᵢ)，标准形式中 λ 以微米为单位、Cᵢ 以
    平方微米为单位。查询波长以米为单位传入（SI），内部转换为微米后代入公式。波长落在
    声明范围 [wavelength_min, wavelength_max] 之外时，以稳定身份
    ``sellmeier_medium_wavelength_out_of_range`` 拒绝。仅承认正实折射率。

    Args:
        b_coefficients: Sellmeier 模型的无量纲 B 系数
        c_coefficients: 以平方米表示的 Sellmeier C 系数
        wavelength_min: 模型允许的最短真空波长
        wavelength_max: 模型允许的最长真空波长

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    b_coefficients: tuple[float, ...]
    c_coefficients: tuple[float, ...]
    wavelength_min: float
    wavelength_max: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.b_coefficients, tuple)
            or not self.b_coefficients
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in self.b_coefficients
            )
        ):
            raise _errors.OpticalValueError(
                "sellmeier_medium_coefficients_invalid",
                "Sellmeier 色散式至少需要一项有限实数的 B 系数，"
                f"收到的是 {self.b_coefficients!r}",
            )
        if (
            not isinstance(self.c_coefficients, tuple)
            or len(self.c_coefficients) != len(self.b_coefficients)
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in self.c_coefficients
            )
        ):
            raise _errors.OpticalValueError(
                "sellmeier_medium_coefficients_invalid",
                "每个 B 系数都要配一个有限实数的 C 系数（单位平方微米），"
                f"B 有 {len(self.b_coefficients)} 项，"
                f"C 收到的是 {self.c_coefficients!r}",
            )
        if (
            not isinstance(self.wavelength_min, (int, float))
            or isinstance(self.wavelength_min, bool)
            or not math.isfinite(float(self.wavelength_min))
            or float(self.wavelength_min) <= 0.0
            or not isinstance(self.wavelength_max, (int, float))
            or isinstance(self.wavelength_max, bool)
            or not math.isfinite(float(self.wavelength_max))
            or float(self.wavelength_max) <= float(self.wavelength_min)
        ):
            raise _errors.OpticalValueError(
                "sellmeier_medium_range_invalid",
                "声明的有效波段以米为单位，须是两个有限正值且下限严格小于上限，"
                f"收到的是 {self.wavelength_min!r} 至 "
                f"{self.wavelength_max!r}",
            )

    def _evaluate_refractive_index(
        self,
        wavelengths: torch.Tensor,
    ) -> torch.Tensor:
        # 执行 Sellmeier 公式；范围外波长以具体范围身份拒绝
        minimum = torch.tensor(
            float(self.wavelength_min),
            dtype=wavelengths.dtype,
            device=wavelengths.device,
        )
        maximum = torch.tensor(
            float(self.wavelength_max),
            dtype=wavelengths.dtype,
            device=wavelengths.device,
        )
        is_below_range = (wavelengths < minimum).any()
        is_above_range = (wavelengths > maximum).any()
        if is_value_readable(is_below_range) and (
            bool(is_below_range)
            or bool(is_above_range)
        ):
            raise _errors.OpticalValueError(
                "sellmeier_medium_wavelength_out_of_range",
                f"这组 Sellmeier 系数只在 {self.wavelength_min!r} 至 "
                f"{self.wavelength_max!r} 米内拟合有效，"
                "波段外绝不外推，请改用覆盖该波段的介质",
            )
        # 波长由米转换为微米（标准 Sellmeier 形式以微米为单位）
        wavelengths_micrometres = wavelengths * 1.0e6
        wavelengths_micrometres_squared = (
            wavelengths_micrometres * wavelengths_micrometres
        )
        squared_refractive_index = torch.ones_like(wavelengths)
        for b_coefficient, c_coefficient in zip(
            self.b_coefficients,
            self.c_coefficients,
            strict=True,
        ):
            squared_refractive_index = (
                squared_refractive_index
                + float(b_coefficient)
                * wavelengths_micrometres_squared
                / (wavelengths_micrometres_squared - float(c_coefficient))
            )
        return torch.sqrt(squared_refractive_index)

    def _physical_identity(self) -> tuple[Any, ...]:
        return (
            self.b_coefficients,
            self.c_coefficients,
            float(self.wavelength_min),
            float(self.wavelength_max),
        )

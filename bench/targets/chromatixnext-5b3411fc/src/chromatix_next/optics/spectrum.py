from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math

import chromatix_next.errors as _errors


def _float_tuple(value: object, error_identity: str) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise _errors.OpticalValueError(
            error_identity,
            "光谱的波长与权重都要给成明确的 Python 实数序列，"
            f"收到的是 {value!r}",
        )
    items = tuple(value)
    if any(
        isinstance(item, bool) or not isinstance(item, (int, float))
        for item in items
    ):
        raise _errors.OpticalValueError(
            error_identity,
            "光谱的波长与权重只接受 Python 实数分量，不接受 Tensor、"
            f"布尔值或复数，收到的是 {value!r}",
        )
    return tuple(float(item) for item in items)


@dataclass(frozen=True, slots=True, init=False)
class Spectrum:
    """
    按波长排列的不可变无张量光谱分量与约减权重

    Args:
        wavelengths: 以米为单位、严格递增的真空波长
        weights: 与波长逐项对应的非负光谱权重

    Raises:
        OpticalValueError: 输入数值、形状、精度或适用域不满足契约

    """

    wavelengths: tuple[float, ...]
    weights: tuple[float, ...]

    def __init__(self, wavelengths: object, weights: object) -> None:
        wavelength_values = _float_tuple(
            wavelengths,
            "spectrum_wavelengths_invalid",
        )
        weight_values = _float_tuple(
            weights,
            "spectrum_weights_invalid",
        )
        if len(wavelength_values) != len(weight_values):
            raise _errors.OpticalValueError(
                "spectrum_length_mismatch",
                "每个波长分量都要配一个权重，"
                f"波长有 {len(wavelength_values)} 个，"
                f"权重有 {len(weight_values)} 个",
            )
        if not wavelength_values:
            raise _errors.OpticalValueError(
                "spectrum_empty",
                "光谱至少要含一个波长分量，单色场请用单色构造器给出唯一波长",
            )
        if any(
            not math.isfinite(wavelength)
            for wavelength in wavelength_values
        ):
            raise _errors.OpticalValueError(
                "spectrum_wavelength_nonfinite",
                "光谱的每个波长都必须是有限值，"
                f"收到的是 {wavelength_values!r}",
            )
        if any(not math.isfinite(weight) for weight in weight_values):
            raise _errors.OpticalValueError(
                "spectrum_weight_nonfinite",
                "权重给出各波长的相对强度占比，必须是有限值，"
                f"收到的是 {weight_values!r}",
            )
        if any(wavelength <= 0.0 for wavelength in wavelength_values):
            raise _errors.OpticalValueError(
                "spectrum_wavelength_nonpositive",
                "波长以米为单位且必须为正，可见光约在 0.4 至 0.7 微米之间，"
                f"收到的是 {wavelength_values!r}",
            )
        if any(weight < 0.0 for weight in weight_values):
            raise _errors.OpticalValueError(
                "spectrum_weight_negative",
                "权重是各波长的强度贡献，不能为负，"
                f"收到的是 {weight_values!r}",
            )
        object.__setattr__(self, "wavelengths", wavelength_values)
        object.__setattr__(self, "weights", weight_values)

    @classmethod
    def monochromatic(cls, wavelength: float) -> "Spectrum":
        """
        构造单波长且单位权重的光谱

        Args:
            wavelength: 以米表示、要查询光谱权重的真空波长

        Returns:
            返回单色谱的波长、权重与采样数量

        Raises:
            OpticalValueError: 输入数值、形状、精度或适用域不满足契约

        """
        if not isinstance(wavelength, (int, float)) or isinstance(
            wavelength,
            bool,
        ):
            raise _errors.OpticalValueError(
                "spectrum_monochromatic_wavelength_invalid",
                "单色光谱要的是一个以米为单位的实数波长，"
                f"收到的是 {type(wavelength).__name__}",
            )
        if not math.isfinite(float(wavelength)):
            raise _errors.OpticalValueError(
                "spectrum_wavelength_nonfinite",
                "单色光谱的波长必须是有限值，"
                f"收到的是 {wavelength!r}",
            )
        if wavelength <= 0.0:
            raise _errors.OpticalValueError(
                "spectrum_wavelength_nonpositive",
                "波长以米为单位且必须为正，可见光约在 0.4 至 0.7 微米之间，"
                f"收到的是 {wavelength!r}",
            )
        return cls(
            wavelengths=(float(wavelength),),
            weights=(1.0,),
        )

    @property
    def count(self) -> int:
        """
        返回光谱分量数目

        Returns:
            返回谱中 wavelength 通道的数量

        """
        return len(self.wavelengths)

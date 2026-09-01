from __future__ import annotations

from dataclasses import dataclass, field, replace
from numbers import Integral
from pathlib import Path
from typing import Any

VALIDATION_SIZES = ("tiny", "middle", "full")
VALIDATION_SUITES = ("data", "layers")
VALIDATION_COLORMAPS = {
    "data_intensity": "gray",
    "optical_amplitude": "hot",
    "optical_intensity": "hot",
    "phase_wrapped": "twilight_shifted",
    "error": "magma",
    "psf": "gray",
}
VALIDATION_FIGURE_SIZES = {
    "data_transformation_trace": (12.8, 3.6),
    "data_degradation_response": (11.8, 13.2),
    "detection_intensity_response": (10.8, 3.6),
    "modulation_phase_construction": (10.8, 6.8),
    "modulation_trainable_phase_action": (10.8, 3.6),
    "lens_phase": (11.2, 3.6),
    "lens_fixed_phase_action": (10.8, 3.6),
    "diffraction_propagation_response": (10.8, 6.4),
    "diffraction_transfer_evolution": (8.8, 7.2),
    "diffraction_cache_performance": (10.8, 4.4),
    "layer_device_agreement": (5.6, 4.4),
}


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        message = f"{name} must be a positive integer"
        raise ValueError(message)
    value_int = int(value)
    if value_int <= 0:
        message = f"{name} must be a positive integer"
        raise ValueError(message)
    return value_int


def _positive_float(name: str, value: object) -> float:
    try:
        value_float = float(value)
    except (TypeError, ValueError) as exc:
        message = f"{name} must be a positive number"
        raise ValueError(message) from exc
    if value_float <= 0.0:
        message = f"{name} must be a positive number"
        raise ValueError(message)
    return value_float


def validation_figure_size(name: str) -> tuple[float, float]:
    """
    返回 validation 语义图幅尺寸
    """
    try:
        return VALIDATION_FIGURE_SIZES[name]
    except KeyError as exc:
        message = f"unknown validation figure size: {name}"
        raise ValueError(message) from exc


def validation_panel_figure_size(
    *,
    columns: int,
    rows: int = 1,
    panel_width: float = 3.0,
    panel_height: float = 3.0,
) -> tuple[float, float]:
    """
    根据子图行列数生成 validation 图幅尺寸
    """
    column_count = _positive_integer("columns", columns)
    row_count = _positive_integer("rows", rows)
    width = _positive_float("panel_width", panel_width)
    height = _positive_float("panel_height", panel_height)
    return (column_count * width, row_count * height)


def _nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral):
        message = f"{name} must be a non-negative integer"
        raise ValueError(message)
    if int(value) < 0:
        message = f"{name} must be a non-negative integer"
        raise ValueError(message)


def _tuple_from_sequence(name: str, value: object) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)):
        message = f"{name} must be a sequence"
        raise ValueError(message)
    try:
        return tuple(value)  # type: ignore[arg-type]
    except TypeError as exc:
        message = f"{name} must be a sequence"
        raise ValueError(message) from exc


@dataclass(frozen=True, slots=True)
class ValidationBasicConfig:
    """
    保存 validation 运行的基础配置
    """

    output_root: Path | str = Path("results/validation")
    device: str = "auto"
    seed: int = 42
    size: str = "middle"

    def normalized(self) -> "ValidationBasicConfig":
        """
        返回输出路径已规范化的基础配置
        """
        self.validate()
        return replace(self, output_root=Path(self.output_root))

    def validate(self) -> None:
        """
        校验设备、随机种子和尺寸档位
        """
        if self.device not in {"auto", "cpu", "cuda"}:
            message = "device must be one of: auto, cpu, cuda"
            raise ValueError(message)
        _nonnegative_integer("seed", self.seed)
        if self.size not in VALIDATION_SIZES:
            message = "size must be one of: tiny, middle, full"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ValidationRunConfig:
    """
    保存 validation 组合运行的配置
    """

    basic: ValidationBasicConfig = field(default_factory=ValidationBasicConfig)
    suites: tuple[str, ...] = VALIDATION_SUITES

    def __post_init__(self) -> None:
        """
        将套件列表规范化为不可变元组
        """
        object.__setattr__(self, "suites", _tuple_from_sequence("suites", self.suites))

    def normalized(self) -> "ValidationRunConfig":
        """
        返回基础配置和套件集合已规范化的运行配置
        """
        self.validate()
        return replace(self, basic=self.basic.normalized())

    def validate(self) -> None:
        """
        校验基础配置和启用的 validation 套件
        """
        self.basic.validate()
        if not self.suites:
            message = "suites must not be empty"
            raise ValueError(message)
        invalid = [suite for suite in self.suites if suite not in VALIDATION_SUITES]
        if invalid:
            message = f"suites must be drawn from {VALIDATION_SUITES}: {invalid}"
            raise ValueError(message)


def coerce_basic_config(
    config: ValidationBasicConfig | ValidationRunConfig | None,
    *,
    output_root: str | Path,
    device: str,
    seed: int,
    size: str,
) -> ValidationBasicConfig:
    """
    将可选配置和扁平参数合并为基础配置
    """
    if config is None:
        return ValidationBasicConfig(
            output_root=output_root,
            device=device,
            seed=seed,
            size=size,
        ).normalized()
    if isinstance(config, ValidationRunConfig):
        return config.normalized().basic
    if isinstance(config, ValidationBasicConfig):
        return config.normalized()
    message = "config must be ValidationBasicConfig, ValidationRunConfig, or None"
    raise TypeError(message)


def coerce_run_config(
    config: ValidationBasicConfig | ValidationRunConfig | None,
    *,
    output_root: str | Path,
    device: str,
    seed: int,
    size: str,
) -> ValidationRunConfig:
    """
    将可选配置和扁平参数合并为完整运行配置
    """
    if config is None:
        return ValidationRunConfig(
            basic=ValidationBasicConfig(
                output_root=output_root,
                device=device,
                seed=seed,
                size=size,
            )
        ).normalized()
    if isinstance(config, ValidationRunConfig):
        return config.normalized()
    if isinstance(config, ValidationBasicConfig):
        return ValidationRunConfig(basic=config).normalized()
    message = "config must be ValidationBasicConfig, ValidationRunConfig, or None"
    raise TypeError(message)

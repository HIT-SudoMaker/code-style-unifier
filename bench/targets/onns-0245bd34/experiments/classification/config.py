from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
from numbers import Integral, Real
from pathlib import Path
import re
from typing import Any
from experiments.classification.geometry import normalize_topology
from experiments.classification.model import (
    CLASSIFICATION_FOCAL_LENGTH,
    CLASSIFICATION_PROPAGATION_DISTANCE,
)

_RUN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _validate_run_name(run_name: str) -> str:
    if not isinstance(run_name, str):
        message = "run_name must be a string"
        raise ValueError(message)
    if not run_name:
        message = "run_name must not be empty"
        raise ValueError(message)
    if not _RUN_NAME_PATTERN.fullmatch(run_name):
        message = "run_name must contain only letters, numbers, '.', '_', or '-'"
        raise ValueError(message)
    if run_name in {".", ".."}:
        message = "run_name must not be a path traversal segment"
        raise ValueError(message)
    return run_name


def _finite_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        message = f"{name} must be a finite real number"
        raise ValueError(message)
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        message = f"{name} must be a finite real number"
        raise ValueError(message)
    return numeric_value


def _positive(name: str, value: object) -> None:
    if _finite_real(name, value) <= 0.0:
        message = f"{name} must be positive"
        raise ValueError(message)


def _nonnegative(name: str, value: object) -> None:
    if _finite_real(name, value) < 0.0:
        message = f"{name} must be non-negative"
        raise ValueError(message)


def _positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral):
        message = f"{name} must be a positive integer"
        raise ValueError(message)
    if int(value) <= 0:
        message = f"{name} must be positive"
        raise ValueError(message)


def _optional_positive_integer(name: str, value: object | None) -> None:
    if value is None:
        return
    _positive_integer(name, value)


def _nonnegative_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral):
        message = f"{name} must be a non-negative integer"
        raise ValueError(message)
    if int(value) < 0:
        message = f"{name} must be non-negative"
        raise ValueError(message)


def _boolean(name: str, value: object) -> None:
    if not isinstance(value, bool):
        message = f"{name} must be a boolean"
        raise ValueError(message)


def _tuple_from_sequence(name: str, value: object) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)):
        message = f"{name} must be a non-empty sequence"
        raise ValueError(message)
    try:
        normalized = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        message = f"{name} must be a non-empty sequence"
        raise ValueError(message) from error
    if not normalized:
        message = f"{name} must be a non-empty sequence"
        raise ValueError(message)
    return normalized


def _positive_range_pair(name: str, value: object) -> tuple[float, float]:
    values = _tuple_from_sequence(name, value)
    if len(values) != 2:
        message = f"{name} must contain exactly two values"
        raise ValueError(message)
    low = _finite_real(name, values[0])
    high = _finite_real(name, values[1])
    if low <= 0.0 or high <= 0.0:
        message = f"{name} values must be positive"
        raise ValueError(message)
    if low >= high:
        message = f"{name} must be in ascending order"
        raise ValueError(message)
    return (low, high)


@dataclass(slots=True)
class BasicConfig:
    """
    保存分类实验的运行级基础配置
    """

    project_root: Path | str = Path.cwd()
    run_name: str = "default"
    device: str = "cpu"
    seed: int = 42

    def normalized(self) -> "BasicConfig":
        """
        返回路径字段规范化后的基础配置
        """
        self.validate()
        return replace(self, project_root=Path(self.project_root))

    def validate(self) -> None:
        """
        校验基础配置字段是否满足运行约束
        """
        _validate_run_name(self.run_name)
        if self.device not in {"auto", "cpu", "cuda"}:
            message = "device must be one of: auto, cpu, cuda"
            raise ValueError(message)
        if isinstance(self.seed, bool) or not isinstance(self.seed, Integral):
            message = "seed must be a non-negative integer"
            raise ValueError(message)
        if int(self.seed) < 0:
            message = "seed must be a non-negative integer"
            raise ValueError(message)


@dataclass(slots=True)
class ModelConfig:
    """
    保存分类 ONN 的拓扑与光学模型配置
    """

    topology: str = "without_lens"
    resize_mode: str = "bilinear"
    phase_parameterization: str = "direct"
    phase_initialization: str = "uniform"
    propagation_distance: float = CLASSIFICATION_PROPAGATION_DISTANCE
    focal_length: float = CLASSIFICATION_FOCAL_LENGTH

    def normalized(self) -> "ModelConfig":
        """
        返回拓扑名称规范化后的模型配置
        """
        self.validate()
        return replace(self, topology=normalize_topology(self.topology))

    def validate(self) -> None:
        """
        校验模型配置字段是否满足分类拓扑约束
        """
        normalize_topology(self.topology)
        if self.resize_mode not in {"nearest", "bilinear"}:
            message = "resize_mode must be one of: nearest, bilinear"
            raise ValueError(message)
        if not isinstance(self.phase_parameterization, str) or not self.phase_parameterization:
            message = "phase_parameterization must be a non-empty string"
            raise ValueError(message)
        if not isinstance(self.phase_initialization, str) or not self.phase_initialization:
            message = "phase_initialization must be a non-empty string"
            raise ValueError(message)
        _positive("propagation_distance", self.propagation_distance)
        _positive("focal_length", self.focal_length)


@dataclass(slots=True)
class SearchConfig:
    """
    保存分类 Optuna 搜索空间配置
    """

    trials: int = 10
    trial_epochs: int = 3
    is_best_retraining_enabled: bool = False
    seed: int = 42
    samples_per_class: int | None = None
    topology_candidates: tuple[str, ...] = ("without_lens", "with_lens")
    batch_size_candidates: tuple[int, ...] = (128, 200)
    resize_mode_candidates: tuple[str, ...] = ("bilinear",)
    learning_rate_range: tuple[float, float] = (5e-4, 5e-3)
    propagation_distance_range: tuple[float, float] = (2e-3, 8e-3)

    def normalized(self) -> "SearchConfig":
        """
        返回候选序列和范围字段规范化后的搜索配置
        """
        self.validate()
        return replace(
            self,
            topology_candidates=tuple(
                normalize_topology(topology)
                for topology in _tuple_from_sequence(
                    "topology_candidates",
                    self.topology_candidates,
                )
            ),
            batch_size_candidates=tuple(
                int(batch_size)
                for batch_size in _tuple_from_sequence(
                    "batch_size_candidates",
                    self.batch_size_candidates,
                )
            ),
            resize_mode_candidates=tuple(
                str(resize_mode)
                for resize_mode in _tuple_from_sequence(
                    "resize_mode_candidates",
                    self.resize_mode_candidates,
                )
            ),
            learning_rate_range=_positive_range_pair(
                "learning_rate_range",
                self.learning_rate_range,
            ),
            propagation_distance_range=_positive_range_pair(
                "propagation_distance_range",
                self.propagation_distance_range,
            ),
        )

    def validate(self) -> None:
        """
        校验搜索空间字段是否满足 Optuna 采样约束
        """
        _positive_integer("trials", self.trials)
        _positive_integer("trial_epochs", self.trial_epochs)
        _nonnegative_integer("seed", self.seed)
        _optional_positive_integer("samples_per_class", self.samples_per_class)
        _boolean("is_best_retraining_enabled", self.is_best_retraining_enabled)

        for topology in _tuple_from_sequence("topology_candidates", self.topology_candidates):
            normalize_topology(topology)

        for batch_size in _tuple_from_sequence(
            "batch_size_candidates",
            self.batch_size_candidates,
        ):
            _positive_integer("batch_size_candidates", batch_size)

        for resize_mode in _tuple_from_sequence(
            "resize_mode_candidates",
            self.resize_mode_candidates,
        ):
            if resize_mode not in {"nearest", "bilinear"}:
                message = "resize_mode_candidates must contain only: nearest, bilinear"
                raise ValueError(message)

        _positive_range_pair("learning_rate_range", self.learning_rate_range)
        _positive_range_pair(
            "propagation_distance_range",
            self.propagation_distance_range,
        )


@dataclass(slots=True, init=False)
class TrainingConfig:
    """
    组合分类训练所需的基础、模型和优化配置
    """

    basic: BasicConfig = field(default_factory=BasicConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    batch_size: int = 128
    learning_rate: float = 0.0037
    weight_decay: float = 0.0
    epochs: int = 50
    samples_per_class: int | None = None
    is_scheduler_enabled: bool = False

    def __init__(
        self,
        *,
        basic: BasicConfig | None = None,
        model: ModelConfig | None = None,
        batch_size: int = 128,
        learning_rate: float = 0.0037,
        weight_decay: float = 0.0,
        epochs: int = 50,
        samples_per_class: int | None = None,
        is_scheduler_enabled: bool = False,
        topology: str | None = None,
        device: str | None = None,
        seed: int | None = None,
        run_name: str | None = None,
        project_root: str | Path | None = None,
        resize_mode: str | None = None,
        phase_parameterization: str | None = None,
        phase_initialization: str | None = None,
        propagation_distance: float | None = None,
        focal_length: float | None = None,
    ) -> None:
        """
        支持组合配置和旧式扁平参数构造训练配置
        """
        basic_config = basic or BasicConfig()
        if (
            device is not None
            or seed is not None
            or run_name is not None
            or project_root is not None
        ):
            basic_config = BasicConfig(
                project_root=(
                    project_root
                    if project_root is not None
                    else basic_config.project_root
                ),
                run_name=run_name if run_name is not None else basic_config.run_name,
                device=device if device is not None else basic_config.device,
                seed=seed if seed is not None else basic_config.seed,
            )

        model_config = model or ModelConfig()
        if (
            topology is not None
            or resize_mode is not None
            or phase_parameterization is not None
            or phase_initialization is not None
            or propagation_distance is not None
            or focal_length is not None
        ):
            model_config = ModelConfig(
                topology=topology if topology is not None else model_config.topology,
                resize_mode=resize_mode if resize_mode is not None else model_config.resize_mode,
                phase_parameterization=(
                    phase_parameterization
                    if phase_parameterization is not None
                    else model_config.phase_parameterization
                ),
                phase_initialization=(
                    phase_initialization
                    if phase_initialization is not None
                    else model_config.phase_initialization
                ),
                propagation_distance=(
                    propagation_distance
                    if propagation_distance is not None
                    else model_config.propagation_distance
                ),
                focal_length=(
                    focal_length if focal_length is not None else model_config.focal_length
                ),
            )

        self.basic = basic_config
        self.model = model_config
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.epochs = epochs
        self.samples_per_class = samples_per_class
        self.is_scheduler_enabled = is_scheduler_enabled

    @property
    def topology(self) -> str:
        """
        返回分类拓扑名称
        """
        return self.model.topology

    @property
    def resize_mode(self) -> str:
        """
        返回输入图像缩放模式
        """
        return self.model.resize_mode

    @property
    def phase_parameterization(self) -> str:
        """
        返回相位层参数化方式
        """
        return self.model.phase_parameterization

    @property
    def phase_initialization(self) -> str:
        """
        相位初值
        """
        return self.model.phase_initialization

    @property
    def propagation_distance(self) -> float:
        """
        光学距离
        """
        return self.model.propagation_distance

    @property
    def focal_length(self) -> float:
        """
        透镜焦距
        """
        return self.model.focal_length

    @property
    def project_root(self) -> Path | str:
        """
        返回实验项目根目录
        """
        return self.basic.project_root

    @property
    def run_name(self) -> str:
        """
        返回实验运行名称
        """
        return self.basic.run_name

    @property
    def device(self) -> str:
        """
        返回训练设备请求
        """
        return self.basic.device

    @property
    def seed(self) -> int:
        """
        返回随机种子
        """
        return self.basic.seed

    def normalized(self) -> "TrainingConfig":
        """
        返回所有子配置规范化后的训练配置
        """
        self.validate()
        return TrainingConfig(
            basic=self.basic.normalized(),
            model=self.model.normalized(),
            batch_size=self.batch_size,
            learning_rate=self.learning_rate,
            weight_decay=self.weight_decay,
            epochs=self.epochs,
            samples_per_class=self.samples_per_class,
            is_scheduler_enabled=self.is_scheduler_enabled,
        )

    def validate(self) -> None:
        """
        校验训练配置字段是否满足训练入口约束
        """
        self.basic.validate()
        self.model.validate()
        _positive_integer("batch_size", self.batch_size)
        _positive_integer("epochs", self.epochs)
        _nonnegative("learning_rate", self.learning_rate)
        _nonnegative("weight_decay", self.weight_decay)
        _optional_positive_integer("samples_per_class", self.samples_per_class)
        _boolean("is_scheduler_enabled", self.is_scheduler_enabled)

    def to_flat_dict(self) -> dict[str, Any]:
        """
        返回兼容旧版 artifact 的扁平配置字典
        """
        normalized = self.normalized()
        return {
            "topology": normalized.topology,
            "batch_size": normalized.batch_size,
            "learning_rate": normalized.learning_rate,
            "weight_decay": normalized.weight_decay,
            "epochs": normalized.epochs,
            "device": normalized.device,
            "seed": normalized.seed,
            "run_name": normalized.run_name,
            "project_root": normalized.project_root,
            "resize_mode": normalized.resize_mode,
            "phase_parameterization": normalized.phase_parameterization,
            "phase_initialization": normalized.phase_initialization,
            "propagation_distance": normalized.propagation_distance,
            "focal_length": normalized.focal_length,
            "samples_per_class": normalized.samples_per_class,
            "is_scheduler_enabled": normalized.is_scheduler_enabled,
        }

def resolve_default_epochs(topology: str = "without_lens") -> int:
    """
    返回指定分类拓扑的默认训练轮数
    """
    normalize_topology(topology)
    return 50


def build_default_training_config(
    topology: str = "without_lens",
    project_root: str | Path = Path.cwd(),
) -> TrainingConfig:
    """
    构造指定拓扑的默认分类训练配置
    """
    normalized_topology = normalize_topology(topology)
    return TrainingConfig(
        topology=normalized_topology,
        epochs=resolve_default_epochs(normalized_topology),
        project_root=Path(project_root),
    )

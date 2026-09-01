from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Literal

from experiments.restoration.optical_bench import (
    IntensityNormalizationPolicy,
    OpticalBenchConfig,
)
from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
from experiments.restoration.fixed_measurement.learning.connection import ConnectionConfig
from experiments.restoration.fixed_measurement.learning.schemas import (
    DEFAULT_TRAINABLE_PARAMETERS_BY_MODEL_ROLE,
    RESTORATION_METHOD_NAMES,
    RESTORATION_MODEL_ROLES,
    TRAINABLE_PARAMETERS_BY_MODEL_ROLE,
    ModelRole,
    RestorationMethodName,
    model_role_for_method,
    validate_method_model_role,
)
from experiments.restoration.fixed_measurement.learning.validation import (
    boolean,
    finite_real,
    nonnegative,
    nonnegative_integer,
    positive,
    positive_integer,
    tuple_from_sequence,
    validate_backend_role,
    validate_connection_role,
    validate_backend_connection_compatibility,
    validate_intensity_normalization_policy,
    validate_phase_options,
    validate_resolution_pair,
)

TrainingMode = Literal["single", "optuna_search", "optuna_with_final_retrain"]

_RUN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_TRAINED_BENCHMARK_METHODS = {
    "full_frontend_trained_phase",
    "digital_backend",
    "frozen_optical_frontend_digital_backend",
    "joint_optical_frontend_digital_backend",
}
_BACKEND_MODEL_ROLES = {
    "backend_only",
    "frozen_optical_frontend_digital_backend",
    "joint_optical_frontend_digital_backend",
}
_HYBRID_MODEL_ROLES = {
    "frozen_optical_frontend_digital_backend",
    "joint_optical_frontend_digital_backend",
}


def _invalid_configuration(message: str) -> ValueError:
    return ValueError(message)


def _validate_run_name(run_name: str) -> None:
    if not isinstance(run_name, str):
        raise _invalid_configuration("run_name must be a string")
    if not run_name:
        raise _invalid_configuration("run_name must not be empty")
    if not _RUN_NAME_PATTERN.fullmatch(run_name):
        raise _invalid_configuration(
            "run_name must contain only letters, numbers, '.', '_', or '-'"
        )
    if run_name in {".", ".."}:
        raise _invalid_configuration("run_name must not be a path traversal segment")


def _freeze_search_space_value(name: str, value: object) -> Any:
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_search_space_value(name, item) for item in value)
    try:
        hash(value)
    except TypeError as exc:
        raise _invalid_configuration(f"{name} contains an unhashable value") from exc
    return value


def _validate_model_role(
    model_role: str,
    *,
    can_include_deterministic: bool = False,
) -> None:
    valid_roles = RESTORATION_MODEL_ROLES
    if not can_include_deterministic:
        valid_roles = tuple(role for role in valid_roles if role != "deterministic")
    if model_role not in valid_roles:
        raise _invalid_configuration(f"model_role must be one of: {', '.join(valid_roles)}")


def _validate_trainable_parameters_for_model_role(
    model_role: str,
    trainable_parameters: tuple[str, ...],
) -> None:
    expected = TRAINABLE_PARAMETERS_BY_MODEL_ROLE.get(model_role)
    if expected is None:
        valid_roles = ", ".join(TRAINABLE_PARAMETERS_BY_MODEL_ROLE)
        raise _invalid_configuration(
            "model_role with trainable parameters must be one of: "
            f"{valid_roles}"
        )
    if trainable_parameters not in expected:
        raise _invalid_configuration(
            f"trainable_parameters for {model_role} must be one of: {expected}"
        )


@dataclass(frozen=True, slots=True)
class BasicConfig:
    """
    瀹氫箟閰嶇疆鏁版嵁缁撴瀯
    """
    project_root: Path | str = Path.cwd()
    run_name: str = "default"
    device: str = "auto"
    seed: int = 2026

    def normalized(self) -> "BasicConfig":
        """
        瀹炵幇閰嶇疆杈呭姪閫昏緫
        """
        self.validate()
        project_root = Path(self.project_root)
        return replace(self, project_root=project_root)

    def validate(self) -> None:
        """
        瀹炵幇閰嶇疆杈呭姪閫昏緫
        """
        _validate_run_name(self.run_name)
        if self.device not in {"auto", "cpu", "cuda"}:
            raise _invalid_configuration("device must be one of: auto, cpu, cuda")
        nonnegative_integer("seed", self.seed)


@dataclass(frozen=True, slots=True)
class CharacterizationConfig:
    """
    瀹氫箟閰嶇疆鏁版嵁缁撴瀯
    """
    basic: BasicConfig = field(default_factory=BasicConfig)
    model: OpticalBenchConfig = field(default_factory=OpticalBenchConfig)
    target_names: tuple[str, ...] = (
        "point_grid",
        "slanted_edge",
        "sinusoidal_gratings",
        "usaf_bars",
        "siemens_star",
    )
    baseline_names: tuple[str, ...] = (
        "input_identity",
        "reference_arm_only",
        "process_arm_phase_zero",
        "full_frontend_phase_zero",
        "interference_term",
    )
    focal_length_candidates: tuple[float, ...] = (0.10,)
    phase_mask_resolution_candidates: tuple[int, ...] = (512, 1024)
    aperture_policy_candidates: tuple[str, ...] = (
        "full_slm_active_area",
        "radius_0_75",
        "radius_0_50",
    )
    phase_offset_reference_candidates: tuple[float, ...] = (
        0.0,
        math.pi / 2,
        math.pi,
        3 * math.pi / 2,
    )
    broad_sweep_camera_oversampling_factor: int = 1
    final_camera_oversampling_factor: int = 1
    selected_target_for_point_response: str = "point_grid"
    selected_target_for_edge_mtf: str = "slanted_edge"
    selected_target_for_grating_ctf: str = "sinusoidal_gratings"
    selected_target_for_phase_scan: str = "slanted_edge"
    operating_point_policy: str = "conservative_mtf50"

    def __post_init__(self) -> None:
        """
        鏍￠獙琛ㄥ緛瀹為獙閰嶇疆
        """
        for field_name in (
            "target_names",
            "baseline_names",
            "focal_length_candidates",
            "phase_mask_resolution_candidates",
            "aperture_policy_candidates",
            "phase_offset_reference_candidates",
        ):
            object.__setattr__(
                self,
                field_name,
                tuple_from_sequence(field_name, getattr(self, field_name)),
            )

    def validate(self) -> None:
        """
        瀹炵幇閰嶇疆杈呭姪閫昏緫
        """
        self.basic.validate()
        self.model.validate()
        if not self.target_names:
            raise _invalid_configuration("target_names must not be empty")
        if not self.baseline_names:
            raise _invalid_configuration("baseline_names must not be empty")
        if not self.focal_length_candidates:
            raise _invalid_configuration("focal_length_candidates must not be empty")
        for index, focal_length in enumerate(self.focal_length_candidates):
            positive(f"focal_length_candidates[{index}]", focal_length)
        if not self.phase_mask_resolution_candidates:
            raise _invalid_configuration("phase_mask_resolution_candidates must not be empty")
        for index, resolution in enumerate(self.phase_mask_resolution_candidates):
            positive_integer(f"phase_mask_resolution_candidates[{index}]", resolution)
        if not self.aperture_policy_candidates:
            raise _invalid_configuration("aperture_policy_candidates must not be empty")
        for index, aperture_policy in enumerate(self.aperture_policy_candidates):
            if not isinstance(aperture_policy, str) or not aperture_policy:
                raise _invalid_configuration(
                    f"aperture_policy_candidates[{index}] must be a non-empty string"
                )
        if not self.phase_offset_reference_candidates:
            raise _invalid_configuration("phase_offset_reference_candidates must not be empty")
        for index, phase_offset in enumerate(self.phase_offset_reference_candidates):
            finite_real(f"phase_offset_reference_candidates[{index}]", phase_offset)
        positive_integer(
            "broad_sweep_camera_oversampling_factor",
            self.broad_sweep_camera_oversampling_factor,
        )
        positive_integer("final_camera_oversampling_factor", self.final_camera_oversampling_factor)
        target_names = set(self.target_names)
        for field_name in (
            "selected_target_for_point_response",
            "selected_target_for_edge_mtf",
            "selected_target_for_grating_ctf",
            "selected_target_for_phase_scan",
        ):
            if getattr(self, field_name) not in target_names:
                raise _invalid_configuration(f"{field_name} must be one of target_names")


def _default_search_space() -> Mapping[str, tuple[Any, ...]]:
    return {
        "learning_rate": (1e-3, 3e-3, 1e-2),
        "batch_size": (4, 8, 16),
        "weight_decay": ("float", 0.0, 1e-3),
        "loss_l1_weight": ("float", 0.5, 2.0),
        "loss_ssim_weight": (0.0, 0.2, 0.5),
        "loss_frequency_weight": (0.0, 0.1, 0.3),
        "phase_smoothness_weight": (0.0, 1e-4, 1e-3),
        "phase_offset_reference": ("float", 0.0, 2 * math.pi),
        "gain_balance": ("float", 0.5, 2.0),
        "phase_parameterization": ("direct",),
        "phase_initialization": ("zeros", "uniform"),
    }


@dataclass(frozen=True, slots=True)
class SearchConfig:
    """
    瀹氫箟閰嶇疆鏁版嵁缁撴瀯
    """
    enabled: bool = False
    mode: TrainingMode = "single"
    study_name: str = "restoration_optuna"
    storage: str | None = None
    n_trials: int = 25
    timeout: float | None = None
    direction: str = "minimize"
    sampler_name: str = "tpe"
    sampler_seed: int = 2026
    pruner_name: str = "median"
    final_retrain: bool = True
    objective_metric: str = "val_ssim"
    secondary_objective_metric: str | None = None
    vary_trial_seed: bool = True
    require_all_trials_complete: bool = False
    trial_epochs: int = 3
    final_epochs: int = 50
    top_k_final_runs: int = 1
    search_space: Mapping[str, tuple[Any, ...]] = field(default_factory=_default_search_space)
    allow_operating_point_search: bool = False

    def __post_init__(self) -> None:
        """
        鏍￠獙 Optuna 鎼滅储閰嶇疆
        """
        try:
            search_space_items = self.search_space.items()
        except AttributeError as exc:
            raise _invalid_configuration("search_space must be a mapping") from exc
        try:
            search_space = MappingProxyType(
                {
                    str(key): tuple(
                        _freeze_search_space_value(f"search_space[{key!r}]", item)
                        for item in value
                    )
                    for key, value in search_space_items
                }
            )
        except TypeError as exc:
            raise _invalid_configuration("search_space values must be iterable") from exc
        object.__setattr__(self, "search_space", search_space)
        self.validate()

    def __hash__(self) -> int:
        """
        瀹炵幇閰嶇疆杈呭姪閫昏緫
        """
        return hash(
            (
                self.enabled,
                self.mode,
                self.study_name,
                self.storage,
                self.n_trials,
                self.timeout,
                self.direction,
                self.sampler_name,
                self.sampler_seed,
                self.pruner_name,
                self.final_retrain,
                self.objective_metric,
                self.secondary_objective_metric,
                self.vary_trial_seed,
                self.require_all_trials_complete,
                self.trial_epochs,
                self.final_epochs,
                self.top_k_final_runs,
                tuple(sorted(self.search_space.items())),
                self.allow_operating_point_search,
            )
        )

    def validate(self) -> None:
        """
        瀹炵幇閰嶇疆杈呭姪閫昏緫
        """
        boolean("enabled", self.enabled)
        boolean("final_retrain", self.final_retrain)
        boolean("vary_trial_seed", self.vary_trial_seed)
        boolean("require_all_trials_complete", self.require_all_trials_complete)
        boolean("allow_operating_point_search", self.allow_operating_point_search)
        if self.mode not in {"single", "optuna_search", "optuna_with_final_retrain"}:
            raise _invalid_configuration(
                "mode must be one of: single, optuna_search, "
                "optuna_with_final_retrain"
            )
        positive_integer("n_trials", self.n_trials)
        if self.timeout is not None:
            positive("timeout", self.timeout)
        if self.direction not in {"maximize", "minimize"}:
            raise _invalid_configuration("direction must be maximize or minimize")
        if not isinstance(self.sampler_name, str) or not self.sampler_name:
            raise _invalid_configuration("sampler_name must be a non-empty string")
        nonnegative_integer("sampler_seed", self.sampler_seed)
        if not isinstance(self.pruner_name, str) or not self.pruner_name:
            raise _invalid_configuration("pruner_name must be a non-empty string")
        if (
            self.secondary_objective_metric is not None
            and (
                not isinstance(self.secondary_objective_metric, str)
                or not self.secondary_objective_metric
            )
        ):
            raise _invalid_configuration(
                "secondary_objective_metric must be a non-empty string or None"
            )
        positive_integer("trial_epochs", self.trial_epochs)
        positive_integer("final_epochs", self.final_epochs)
        positive_integer("top_k_final_runs", self.top_k_final_runs)


@dataclass(frozen=True, slots=True)
class FrontendSourceConfig:
    """
    鎻忚堪鍓嶇妫€鏌ョ偣鏉ユ簮閰嶇疆
    """
    checkpoint_path: Path | str
    run_id: str
    source_config_hash: str
    source_geometry_hash: str
    source_degradation_hash: str
    source_profile_name: str | None = None
    source_seed: int | None = None
    source_run_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "checkpoint_path", Path(self.checkpoint_path))

    def validate(self) -> None:
        """
        鏍￠獙鍓嶇鏉ユ簮閰嶇疆
        """
        if str(self.checkpoint_path) in {"", "."}:
            raise _invalid_configuration("checkpoint_path must not be empty")
        if not isinstance(self.run_id, str) or not self.run_id:
            raise _invalid_configuration("run_id must not be empty")
        if not isinstance(self.source_config_hash, str) or not self.source_config_hash:
            raise _invalid_configuration("source_config_hash must not be empty")
        if not isinstance(self.source_geometry_hash, str) or not self.source_geometry_hash:
            raise _invalid_configuration("source_geometry_hash must not be empty")
        if (
            not isinstance(self.source_degradation_hash, str)
            or not self.source_degradation_hash
        ):
            raise _invalid_configuration("source_degradation_hash must not be empty")
        scientific_identity = (
            self.source_profile_name,
            self.source_seed,
            self.source_run_key,
        )
        if any(value is not None for value in scientific_identity):
            if (
                not isinstance(self.source_profile_name, str)
                or not self.source_profile_name
            ):
                raise _invalid_configuration("source_profile_name must not be empty")
            nonnegative_integer("source_seed", self.source_seed)
            if not isinstance(self.source_run_key, str) or not self.source_run_key:
                raise _invalid_configuration("source_run_key must not be empty")


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    """
    瀹氫箟閰嶇疆鏁版嵁缁撴瀯
    """
    basic: BasicConfig = field(default_factory=BasicConfig)
    operating_point_path: Path | str = Path(
        "results/restoration/characterization/default/operating_point.json"
    )
    train_dataset_config: Any | None = None
    val_dataset_config: Any | None = None
    training_mode: TrainingMode = "single"
    model_role: ModelRole = "frontend_only"
    backend: BackendConfig | None = None
    frontend_source: FrontendSourceConfig | None = None
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    search: SearchConfig | None = None
    epochs: int = 50
    batch_size: int = 8
    effective_batch_size: int | None = None
    max_optimizer_updates: int | None = None
    learning_rate: float = 1e-2
    frontend_to_backend_lr_ratio: float = 1.0
    weight_decay: float = 0.0
    phase_parameterization: str = "direct"
    phase_initialization: str = "zeros"
    loss_l1_weight: float = 1.0
    loss_ssim_weight: float = 0.2
    loss_frequency_weight: float = 0.1
    phase_smoothness_weight: float = 1e-4
    intensity_normalization_policy: IntensityNormalizationPolicy = "fixed_dataset_level"
    trainable_parameters: tuple[str, ...] = DEFAULT_TRAINABLE_PARAMETERS_BY_MODEL_ROLE[
        "frontend_only"
    ]
    checkpoint_policy: str = "best_and_last"
    visualization_sample_count: int = 4

    def __post_init__(self) -> None:
        """
        鏍￠獙璁粌瀹為獙閰嶇疆
        """
        object.__setattr__(self, "model_role", str(self.model_role))
        object.__setattr__(
            self,
            "trainable_parameters",
            tuple_from_sequence("trainable_parameters", self.trainable_parameters),
        )
        if isinstance(self.connection, ConnectionConfig):
            connection = self.connection
        elif isinstance(self.connection, Mapping):
            try:
                connection = ConnectionConfig(**self.connection)
            except TypeError as exc:
                raise _invalid_configuration("connection is malformed") from exc
        else:
            raise _invalid_configuration("connection must be a ConnectionConfig or mapping")
        object.__setattr__(self, "connection", connection)
        if self.frontend_source is None:
            frontend_source = None
        elif isinstance(self.frontend_source, FrontendSourceConfig):
            frontend_source = self.frontend_source
        elif isinstance(self.frontend_source, Mapping):
            try:
                frontend_source = FrontendSourceConfig(**self.frontend_source)
            except TypeError as exc:
                raise _invalid_configuration("frontend_source is malformed") from exc
        else:
            raise _invalid_configuration(
                "frontend_source must be a FrontendSourceConfig or mapping"
            )
        object.__setattr__(self, "frontend_source", frontend_source)
        if self.backend is None and self.model_role in {
            "backend_only",
            "frozen_optical_frontend_digital_backend",
            "joint_optical_frontend_digital_backend",
        }:
            backend = BackendConfig()
        elif self.backend is None:
            backend = None
        elif isinstance(self.backend, BackendConfig):
            backend = self.backend
        elif isinstance(self.backend, Mapping):
            try:
                backend = BackendConfig(**self.backend)
            except TypeError as exc:
                raise _invalid_configuration("backend is malformed") from exc
        else:
            raise _invalid_configuration("backend must be a BackendConfig, mapping, or None")
        object.__setattr__(self, "backend", backend)
        self.validate()

    def __hash__(self) -> int:
        """
        瀹炵幇閰嶇疆杈呭姪閫昏緫
        """
        return hash(
            (
                self.basic,
                Path(self.operating_point_path),
                self.training_mode,
                self.model_role,
                self.backend,
                self.frontend_source,
                self.connection,
                self.search,
                self.epochs,
                self.batch_size,
                self.effective_batch_size,
                self.max_optimizer_updates,
                self.learning_rate,
                self.frontend_to_backend_lr_ratio,
                self.weight_decay,
                self.phase_parameterization,
                self.phase_initialization,
                self.loss_l1_weight,
                self.loss_ssim_weight,
                self.loss_frequency_weight,
                self.phase_smoothness_weight,
                self.intensity_normalization_policy,
                self.trainable_parameters,
                self.checkpoint_policy,
                self.visualization_sample_count,
            )
        )

    def validate(self) -> None:
        """
        瀹炵幇閰嶇疆杈呭姪閫昏緫
        """
        self.basic.validate()
        if self.training_mode not in {"single", "optuna_search", "optuna_with_final_retrain"}:
            raise _invalid_configuration(
                "training_mode must be one of: single, optuna_search, "
                "optuna_with_final_retrain"
            )
        _validate_model_role(self.model_role)
        validate_phase_options(self.phase_parameterization, self.phase_initialization)
        validate_backend_role(self.model_role, self.backend)
        self.connection.validate()
        validate_backend_connection_compatibility(
            self.connection.mode,
            self.backend,
        )
        validate_connection_role(self.model_role, self.connection.mode)
        if (
            "connection" in self.trainable_parameters
            and self.connection.mode != "optical_residual_gate"
        ):
            raise _invalid_configuration(
                "trainable connection requires optical_residual_gate connection mode"
            )
        if self.model_role in _HYBRID_MODEL_ROLES:
            if self.frontend_source is None:
                raise _invalid_configuration("frontend_source is required for hybrid training")
            self.frontend_source.validate()
        elif self.frontend_source is not None:
            raise _invalid_configuration("frontend_source is only valid for hybrid training")
        positive_integer("epochs", self.epochs)
        positive_integer("batch_size", self.batch_size)
        if self.effective_batch_size is not None:
            positive_integer("effective_batch_size", self.effective_batch_size)
            if self.effective_batch_size < self.batch_size:
                raise _invalid_configuration(
                    "effective_batch_size must be at least batch_size"
                )
            if self.effective_batch_size % self.batch_size != 0:
                raise _invalid_configuration(
                    "effective_batch_size must be divisible by batch_size"
                )
        if self.max_optimizer_updates is not None:
            positive_integer("max_optimizer_updates", self.max_optimizer_updates)
        positive("learning_rate", self.learning_rate)
        positive("frontend_to_backend_lr_ratio", self.frontend_to_backend_lr_ratio)
        if (
            self.model_role != "joint_optical_frontend_digital_backend"
            and self.frontend_to_backend_lr_ratio != 1.0
        ):
            raise _invalid_configuration(
                "frontend_to_backend_lr_ratio is only configurable for joint training"
            )
        nonnegative("weight_decay", self.weight_decay)
        nonnegative("loss_l1_weight", self.loss_l1_weight)
        nonnegative("loss_ssim_weight", self.loss_ssim_weight)
        nonnegative("loss_frequency_weight", self.loss_frequency_weight)
        nonnegative("phase_smoothness_weight", self.phase_smoothness_weight)
        validate_intensity_normalization_policy(self.intensity_normalization_policy)
        _validate_trainable_parameters_for_model_role(
            self.model_role,
            self.trainable_parameters,
        )
        positive_integer("visualization_sample_count", self.visualization_sample_count)
        if self.search is not None and not isinstance(self.search, SearchConfig):
            raise _invalid_configuration("search must be a SearchConfig or None")
        if self.search is not None:
            self.search.validate()


@dataclass(frozen=True, slots=True)
class BenchmarkMethodSource:
    """
    淇濆瓨璁粌鍩哄噯鏂规硶妫€鏌ョ偣鏉ユ簮
    """
    method_name: RestorationMethodName
    checkpoint_path: Path | str
    run_id: str = ""
    source_config_hash: str = ""
    source_degradation_hash: str = ""
    source_config_path: Path | str | None = None
    model_role: ModelRole | None = None
    backend: BackendConfig | None = None
    phase_parameterization: str = "direct"
    phase_initialization: str = "zeros"
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)

    def __post_init__(self) -> None:
        """
        瑙勮寖鍩哄噯鏂规硶鏉ユ簮鏍囪瘑涓庤矾寰?        """
        method_name = str(self.method_name)
        object.__setattr__(self, "method_name", method_name)
        object.__setattr__(self, "checkpoint_path", Path(self.checkpoint_path))
        if self.source_config_path is not None:
            object.__setattr__(
                self,
                "source_config_path",
                Path(self.source_config_path),
            )
        if self.model_role is None:
            object.__setattr__(self, "model_role", model_role_for_method(method_name))
        else:
            object.__setattr__(self, "model_role", str(self.model_role))
        if isinstance(self.connection, ConnectionConfig):
            connection = self.connection
        elif isinstance(self.connection, Mapping):
            try:
                connection = ConnectionConfig(**self.connection)
            except TypeError as exc:
                raise _invalid_configuration("connection is malformed") from exc
        else:
            raise _invalid_configuration("connection must be a ConnectionConfig or mapping")
        object.__setattr__(self, "connection", connection)
        if self.backend is None:
            backend = None
        elif isinstance(self.backend, BackendConfig):
            backend = self.backend
        elif isinstance(self.backend, Mapping):
            try:
                backend = BackendConfig(**self.backend)
            except TypeError as exc:
                raise _invalid_configuration("backend is malformed") from exc
        else:
            raise _invalid_configuration("backend must be a BackendConfig, mapping, or None")
        object.__setattr__(self, "backend", backend)
        self.validate()

    def validate(self) -> None:
        """
        鏍￠獙璁粌鍩哄噯鏂规硶妫€鏌ョ偣鏉ユ簮
        """
        if self.method_name not in RESTORATION_METHOD_NAMES:
            allowed = ", ".join(RESTORATION_METHOD_NAMES)
            raise _invalid_configuration(f"method_name must be one of: {allowed}")
        validate_method_model_role(self.method_name, str(self.model_role))
        if self.model_role == "deterministic":
            raise _invalid_configuration("deterministic methods must not define checkpoints")
        if str(self.checkpoint_path) in {"", "."}:
            raise _invalid_configuration("checkpoint_path must not be empty")
        if not isinstance(self.run_id, str) or not self.run_id:
            raise _invalid_configuration("run_id must not be empty")
        if not isinstance(self.source_config_hash, str) or not self.source_config_hash:
            raise _invalid_configuration("source_config_hash must not be empty")
        if (
            not isinstance(self.source_degradation_hash, str)
            or not self.source_degradation_hash
        ):
            raise _invalid_configuration("source_degradation_hash must not be empty")
        if (
            self.source_config_path is not None
            and str(self.source_config_path) in {"", "."}
        ):
            raise _invalid_configuration("source_config_path must not be empty")
        validate_phase_options(self.phase_parameterization, self.phase_initialization)
        self.connection.validate()
        validate_backend_connection_compatibility(
            self.connection.mode,
            self.backend,
        )
        validate_connection_role(str(self.model_role), self.connection.mode)
        validate_backend_role(str(self.model_role), self.backend)


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    """
    瀹氫箟閰嶇疆鏁版嵁缁撴瀯
    """
    basic: BasicConfig = field(default_factory=BasicConfig)
    study_name: str = "default"
    dataset_config: Any | None = None
    operating_point_path: Path | str = Path(
        "results/restoration/characterization/default/operating_point.json"
    )
    method_names: tuple[RestorationMethodName, ...] = (
        "degraded",
        "reference_arm",
        "process_arm_zero_phase",
        "full_frontend_zero_phase",
    )
    batch_size: int = 8
    intensity_normalization_policy: IntensityNormalizationPolicy = "fixed_dataset_level"
    max_samples: int | None = None
    method_sources: tuple[BenchmarkMethodSource, ...] = ()

    def __post_init__(self) -> None:
        """
        鏍￠獙 benchmark 瀹為獙閰嶇疆
        """
        object.__setattr__(
            self,
            "method_names",
            tuple(str(name) for name in self.method_names),
        )
        object.__setattr__(self, "operating_point_path", Path(self.operating_point_path))
        normalized_sources: list[BenchmarkMethodSource] = []
        for index, source in enumerate(
            tuple_from_sequence("method_sources", self.method_sources)
        ):
            if isinstance(source, BenchmarkMethodSource):
                normalized_sources.append(source)
            elif isinstance(source, Mapping):
                try:
                    normalized_sources.append(BenchmarkMethodSource(**source))
                except TypeError as exc:
                    raise _invalid_configuration(f"method_sources[{index}] is malformed") from exc
            else:
                raise _invalid_configuration(
                    f"method_sources[{index}] must be a BenchmarkMethodSource or mapping"
                )
        object.__setattr__(self, "method_sources", tuple(normalized_sources))

    def validate(self) -> None:
        """
        瀹炵幇閰嶇疆杈呭姪閫昏緫
        """
        self.basic.validate()
        _validate_run_name(self.study_name)
        if self.dataset_config is None:
            raise _invalid_configuration("dataset_config must not be None")
        unknown = [
            name for name in self.method_names if name not in RESTORATION_METHOD_NAMES
        ]
        if unknown:
            allowed = ", ".join(RESTORATION_METHOD_NAMES)
            raise _invalid_configuration(f"method_names must contain only: {allowed}")
        positive_integer("batch_size", self.batch_size)
        if self.max_samples is not None:
            positive_integer("max_samples", self.max_samples)
        validate_intensity_normalization_policy(self.intensity_normalization_policy)
        method_names = set(self.method_names)
        source_names: set[str] = set()
        for source in self.method_sources:
            source.validate()
            if source.method_name not in method_names:
                raise _invalid_configuration("method_sources must reference enabled method_names")
            if source.method_name in source_names:
                raise _invalid_configuration(
                    "method_sources must contain exactly one source per method: "
                    f"{source.method_name}"
                )
            source_names.add(source.method_name)
        trained_names = method_names.intersection(_TRAINED_BENCHMARK_METHODS)
        missing_sources = sorted(trained_names.difference(source_names))
        if missing_sources:
            raise _invalid_configuration(
                "trained benchmark methods require method_sources: "
                + ", ".join(missing_sources)
            )


@dataclass(frozen=True, slots=True)
class BoundaryConfig:
    """
    瀹氫箟閰嶇疆鏁版嵁缁撴瀯
    """
    basic: BasicConfig = field(default_factory=BasicConfig)
    study_name: str = "default"
    dataset_config: Any | None = None
    operating_point_path: Path | str = Path(
        "results/restoration/characterization/default/operating_point.json"
    )
    method_names: tuple[RestorationMethodName, ...] = (
        "degraded",
        "full_frontend_zero_phase",
        "full_frontend_trained_phase",
    )
    blur_levels: tuple[float, ...] = (0.0, 1.0, 2.0, 3.0)
    noise_levels: tuple[float, ...] = (0.0, 0.01, 0.03, 0.05)
    no_recovery_psnr_delta: float = 0.5
    no_recovery_ssim_delta: float = 0.01
    no_frontend_gain_psnr_delta: float = 0.2
    hybrid_no_gain_psnr_delta: float = 0.2
    hybrid_no_gain_ssim_delta: float = 0.005

    def __post_init__(self) -> None:
        """
        鏍￠獙杈圭晫鎵弿閰嶇疆
        """
        method_names = tuple_from_sequence("method_names", self.method_names)
        blur_levels = tuple_from_sequence("blur_levels", self.blur_levels)
        noise_levels = tuple_from_sequence("noise_levels", self.noise_levels)
        object.__setattr__(
            self,
            "method_names",
            tuple(str(name) for name in method_names),
        )
        object.__setattr__(
            self,
            "blur_levels",
            tuple(
                finite_real(f"blur_levels[{index}]", value)
                for index, value in enumerate(blur_levels)
            ),
        )
        object.__setattr__(
            self,
            "noise_levels",
            tuple(
                finite_real(f"noise_levels[{index}]", value)
                for index, value in enumerate(noise_levels)
            ),
        )
        object.__setattr__(
            self,
            "operating_point_path",
            Path(self.operating_point_path),
        )

    def validate(self) -> None:
        """
        瀹炵幇閰嶇疆杈呭姪閫昏緫
        """
        self.basic.validate()
        _validate_run_name(self.study_name)
        if self.dataset_config is None:
            raise _invalid_configuration("dataset_config must not be None")
        if not self.method_names:
            raise _invalid_configuration("method_names must not be empty")
        unknown = [
            name for name in self.method_names if name not in RESTORATION_METHOD_NAMES
        ]
        if unknown:
            allowed = ", ".join(RESTORATION_METHOD_NAMES)
            raise _invalid_configuration(f"method_names must contain only: {allowed}")
        if not self.blur_levels:
            raise _invalid_configuration("blur_levels must not be empty")
        if not self.noise_levels:
            raise _invalid_configuration("noise_levels must not be empty")
        for index, value in enumerate(self.blur_levels):
            nonnegative(f"blur_levels[{index}]", value)
        for index, value in enumerate(self.noise_levels):
            nonnegative(f"noise_levels[{index}]", value)
        for field_name in (
            "no_recovery_psnr_delta",
            "no_recovery_ssim_delta",
            "no_frontend_gain_psnr_delta",
            "hybrid_no_gain_psnr_delta",
            "hybrid_no_gain_ssim_delta",
        ):
            nonnegative(field_name, getattr(self, field_name))

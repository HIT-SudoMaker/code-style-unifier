from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
import math
from pathlib import Path
from typing import get_args

import pytest

import experiments.restoration.fixed_measurement.learning.config as restoration_config
from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
from experiments.restoration.fixed_measurement.learning.config import (
    BasicConfig,
    BenchmarkConfig,
    BoundaryConfig,
    CharacterizationConfig,
    FrontendSourceConfig,
    SearchConfig,
    TrainingConfig,
    TrainingMode,
)
from experiments.restoration.optical_bench import (
    IntensityNormalizationPolicy,
    OpticalBenchConfig,
)
from experiments.restoration.fixed_measurement.learning.connection import ConnectionConfig
from experiments.restoration.fixed_measurement.learning.validation import validate_phase_options


def test_basic_config_normalizes_project_root() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = BasicConfig(project_root="relative_root")
    normalized = config.normalized()

    assert isinstance(normalized.project_root, Path)
    assert normalized.project_root == Path("relative_root")
    assert normalized.run_name == "default"
    assert normalized.device == "auto"


def test_config_dataclasses_are_frozen_and_slotted() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = OpticalBenchConfig()

    assert is_dataclass(config)
    assert hasattr(config, "__slots__")
    with pytest.raises(FrozenInstanceError):
        config.focal_length = 0.3  # type: ignore[misc]


def test_geometry_config_defaults_use_unit_magnification_and_distinct_pixels() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = OpticalBenchConfig()

    assert config.input_plane_pixel_size == 8e-6
    assert config.slm1_pixel_size == 8e-6
    assert config.slm2_pixel_size == 8e-6
    assert config.camera_pixel_size == 2.9e-6
    assert config.camera_resolution == (2160, 3840)
    assert config.camera_oversampling_factor == 1
    assert config.camera_binning_policy == "none"
    assert config.focal_length == pytest.approx(0.1)
    assert config.slm2_active_resolution == (1024, 1024)
    assert config.system_magnification == 1.0
    assert config.spatial_frequency_unit == "cycles_per_meter"
    assert config.fft_shift_policy == "centered_frequency_grid"


def test_geometry_config_rejects_invalid_split_ratios() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match="split ratios"):
        OpticalBenchConfig(
            split_ratio_reference=0.7,
            split_ratio_process=0.6,
        ).validate()


def test_geometry_config_rejects_negative_gains() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match="amplitude_gain_reference"):
        OpticalBenchConfig(amplitude_gain_reference=-1.0).validate()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("wavelength", True),
        ("focal_length", math.nan),
        ("system_magnification", math.inf),
        ("input_plane_pixel_size", 1 + 2j),
        ("phase_offset_reference", math.nan),
    ],
)
def test_geometry_config_rejects_invalid_positive_physical_fields(
    field_name: str,
    value: object,
) -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match=field_name):
        OpticalBenchConfig(**{field_name: value}).validate()  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("slm1_resolution", (1200,)),
        ("slm2_resolution", (True, 1920)),
        ("camera_resolution", (1200, 0)),
        ("input_array_resolution", (512.5, 512)),
        ("phase_mask_resolution", True),
        ("camera_oversampling_factor", 0),
    ],
)
def test_geometry_config_rejects_invalid_integer_geometry_fields(
    field_name: str,
    value: object,
) -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match=field_name):
        OpticalBenchConfig(**{field_name: value}).validate()  # type: ignore[arg-type]


def test_characterization_config_defaults_match_public_baselines() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = CharacterizationConfig()

    assert config.target_names == (
        "point_grid",
        "slanted_edge",
        "sinusoidal_gratings",
        "usaf_bars",
        "siemens_star",
    )
    assert config.selected_target_for_point_response == "point_grid"
    assert config.baseline_names == (
        "input_identity",
        "reference_arm_only",
        "process_arm_phase_zero",
        "full_frontend_phase_zero",
        "interference_term",
    )
    assert config.final_camera_oversampling_factor == 1


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("baseline_names", ()),
        ("focal_length_candidates", ()),
        ("focal_length_candidates", (math.inf,)),
        ("phase_mask_resolution_candidates", ()),
        ("phase_mask_resolution_candidates", (True,)),
        ("aperture_policy_candidates", ()),
        ("aperture_policy_candidates", ("",)),
        ("aperture_policy_candidates", (None,)),
        ("phase_offset_reference_candidates", ()),
        ("phase_offset_reference_candidates", (math.nan,)),
        ("broad_sweep_camera_oversampling_factor", True),
        ("final_camera_oversampling_factor", 0),
        ("selected_target_for_point_response", "unknown_target"),
        ("selected_target_for_edge_mtf", "unknown_target"),
        ("selected_target_for_grating_ctf", "unknown_target"),
        ("selected_target_for_phase_scan", "unknown_target"),
    ],
)
def test_characterization_config_rejects_incomplete_candidates_and_unknown_targets(
    field_name: str,
    value: object,
) -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match=field_name):
        CharacterizationConfig(**{field_name: value}).validate()  # type: ignore[arg-type]


def test_training_config_defaults_freeze_operating_point_search() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = TrainingConfig(
        operating_point_path=Path(
            "results/restoration/characterization/default/operating_point.json"
        ),
    )

    assert config.training_mode == "single"
    assert config.trainable_parameters == ("phase_mask_fourier",)
    assert config.phase_parameterization == "direct"
    assert config.intensity_normalization_policy == "fixed_dataset_level"


def test_training_config_defaults_to_frontend_only_model_role() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = TrainingConfig()

    assert config.model_role == "frontend_only"
    assert config.backend is None
    assert config.trainable_parameters == ("phase_mask_fourier",)
    config.validate()


def test_training_config_accepts_update_matched_batch_budget() -> None:
    """
    验证训练配置接受更新数匹配的有效批量预算
    """
    config = TrainingConfig(
        batch_size=2,
        effective_batch_size=8,
        max_optimizer_updates=6000,
    )

    assert config.effective_batch_size == 8
    assert config.max_optimizer_updates == 6000


@pytest.mark.parametrize("effective_batch_size", [1, 3, 6])
def test_training_config_rejects_incompatible_effective_batch_size(
    effective_batch_size: int,
) -> None:
    """
    验证训练配置拒绝无法由微批量整除的有效批量
    """
    with pytest.raises(ValueError, match="effective_batch_size"):
        TrainingConfig(
            batch_size=4,
            effective_batch_size=effective_batch_size,
        )


def test_training_config_normalizes_backend_mapping() -> None:
    """
    Canonical serialized training configs read nested backend mappings back.
    """
    config = TrainingConfig(
        model_role="backend_only",
        trainable_parameters=("backend",),
        backend={
            "family": "restoration_native",
            "model_name": "nafnet_m",
            "residual_learning": False,
        },
    )

    assert config.backend == BackendConfig(
        model_name="nafnet_m",
        residual_learning=False,
    )
    config.validate()


def test_training_config_allows_frontend_phase_offset_training() -> None:
    """
    Validate frontend phase offset training configuration.
    """
    config = TrainingConfig(
        trainable_parameters=("phase_mask_fourier", "phase_offset_reference"),
    )

    assert config.trainable_parameters == (
        "phase_mask_fourier",
        "phase_offset_reference",
    )
    config.validate()


def test_validate_phase_options_accepts_uniform_and_rejects_random_uniform() -> None:
    """
    验证均匀分布是规范随机相位初始化方式
    """
    validate_phase_options("direct", "uniform")

    with pytest.raises(
        ValueError,
        match="phase_initialization must be one of: zeros, uniform, normal",
    ):
        validate_phase_options("direct", "random_uniform")


def test_training_config_creates_default_restoration_native_backend() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = TrainingConfig(
        model_role="backend_only",
        trainable_parameters=("backend",),
    )

    assert isinstance(config.backend, BackendConfig)
    assert config.backend.family == "restoration_native"
    assert config.backend.model_name == "nafnet_s"
    config.validate()


@pytest.mark.parametrize(
    ("legacy_role", "trainable_parameters"),
    [
        (
            "frozen_frontend_backend",
            ("backend",),
        ),
        (
            "joint_frontend_backend",
            ("phase_mask_fourier", "backend"),
        ),
    ],
)
def test_training_config_rejects_legacy_hybrid_roles(
    legacy_role: str,
    trainable_parameters: tuple[str, ...],
) -> None:
    """
    Legacy hybrid roles are rejected instead of normalized.
    """
    with pytest.raises(
        ValueError,
        match="frozen_optical_frontend_digital_backend",
    ):
        TrainingConfig(
            model_role=legacy_role,  # type: ignore[arg-type]
            trainable_parameters=trainable_parameters,
        )


def test_training_config_rejects_backend_for_frontend_only_role() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match="backend must be None"):
        TrainingConfig(
            backend=BackendConfig(),
        ).validate()


def test_training_config_rejects_invalid_backend_for_backend_role() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match="backend must be a BackendConfig"):
        TrainingConfig(
            model_role="backend_only",
            backend="bad",
            trainable_parameters=("backend",),
        ).validate()


def test_training_config_rejects_mismatched_trainable_parameters() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match="trainable_parameters for backend_only"):
        TrainingConfig(
            model_role="backend_only",
            trainable_parameters=("phase_mask_fourier",),
        ).validate()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("weight_decay", -1e-4),
        ("learning_rate", 0.0),
        ("loss_l1_weight", -1.0),
        ("loss_ssim_weight", -0.2),
        ("loss_frequency_weight", -0.1),
        ("phase_smoothness_weight", -1e-4),
        ("visualization_sample_count", 0),
    ],
)
def test_training_config_rejects_invalid_scalar_training_values(
    field_name: str,
    value: object,
) -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match=field_name):
        TrainingConfig(**{field_name: value}).validate()  # type: ignore[arg-type]


def test_training_config_accepts_plan_training_modes() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    TrainingConfig(training_mode="single").validate()
    TrainingConfig(training_mode="optuna_search").validate()
    TrainingConfig(training_mode="optuna_with_final_retrain").validate()

    with pytest.raises(ValueError, match="training_mode"):
        TrainingConfig(training_mode="search").validate()  # type: ignore[arg-type]


def test_training_mode_stays_training_flow_not_model_role() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    assert get_args(TrainingMode) == (
        "single",
        "optuna_search",
        "optuna_with_final_retrain",
    )


def test_training_config_accepts_plan_intensity_normalization_policies() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    TrainingConfig(intensity_normalization_policy="fixed_dataset_level").validate()
    TrainingConfig(intensity_normalization_policy="characterization_calibrated_gain").validate()
    TrainingConfig(intensity_normalization_policy="per_image_min_max").validate()


def test_benchmark_config_defaults_to_deterministic_methods() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = BenchmarkConfig(
        dataset_config={"kind": "unit"},
        operating_point_path=Path(
            "results/restoration/characterization/default/operating_point.json"
        ),
    )

    assert config.method_names == (
        "degraded",
        "reference_arm",
        "process_arm_zero_phase",
        "full_frontend_zero_phase",
    )
    assert config.study_name == "default"


def test_benchmark_config_rejects_legacy_method_names() -> None:
    """
    Legacy benchmark method names are rejected instead of normalized.
    """
    config = BenchmarkConfig(
        dataset_config={"kind": "unit"},
        method_names=("degraded", "joint_frontend_backend"),  # type: ignore[arg-type]
    )

    assert config.method_names == ("degraded", "joint_frontend_backend")
    with pytest.raises(
        ValueError,
        match="joint_optical_frontend_digital_backend",
    ):
        config.validate()


def test_benchmark_method_source_validates_trained_backend_source() -> None:
    """
    Benchmark method sources record trained backend checkpoint provenance.
    """
    source_cls = restoration_config.BenchmarkMethodSource

    source = source_cls(
        method_name="digital_backend",
        checkpoint_path="results/restoration/training/backend/checkpoints/best.pt",
        run_id="backend-run",
        source_config_hash="abc123",
        source_degradation_hash="degradation123",
        source_config_path="results/restoration/training/backend/config.json",
        backend=BackendConfig(model_name="nafnet_s"),
    )

    assert source.method_name == "digital_backend"
    assert source.model_role == "backend_only"
    assert source.checkpoint_path == Path(
        "results/restoration/training/backend/checkpoints/best.pt"
    )
    assert source.source_config_path == Path(
        "results/restoration/training/backend/config.json"
    )
    assert source.backend == BackendConfig(model_name="nafnet_s")
    source.validate()


def test_benchmark_method_source_normalizes_backend_mapping() -> None:
    """
    Benchmark source backend identity is stored as nested BackendConfig.
    """
    source = restoration_config.BenchmarkMethodSource(
        method_name="digital_backend",
        checkpoint_path="checkpoints/backend.pt",
        run_id="backend-run",
        source_config_hash="abc123",
        source_degradation_hash="degradation123",
        backend={
            "family": "restoration_native",
            "model_name": "nafnet_m",
            "residual_learning": False,
        },
    )

    assert source.backend == BackendConfig(
        model_name="nafnet_m",
        residual_learning=False,
    )
    source.validate()


def test_benchmark_method_source_rejects_flat_backend_identity_aliases() -> None:
    """
    Legacy flat backend source fields are not accepted as read-side aliases.
    """
    with pytest.raises(ValueError, match=r"method_sources\[0\] is malformed"):
        BenchmarkConfig(
            dataset_config={"kind": "unit"},
            method_names=("digital_backend",),
            method_sources=(
                {
                    "method_name": "digital_backend",
                    "checkpoint_path": "checkpoints/backend.pt",
                    "run_id": "backend-run",
                    "source_config_hash": "abc123",
                    "source_degradation_hash": "degradation123",
                    "backend_family": "restoration_native",
                    "backend_model": "nafnet_s",
                },
            ),
        )


def test_benchmark_method_source_rejects_legacy_method_name() -> None:
    """
    Legacy benchmark source method names fail before traceability checks.
    """
    with pytest.raises(
        ValueError,
        match="joint_optical_frontend_digital_backend",
    ):
        restoration_config.BenchmarkMethodSource(
            method_name="joint_frontend_backend",  # type: ignore[arg-type]
            checkpoint_path="checkpoints/joint.pt",
            run_id="joint-run",
            source_config_hash="abc123",
            source_degradation_hash="degradation123",
            backend=BackendConfig(model_name="nafnet_s"),
        )


def test_benchmark_method_source_rejects_empty_source_degradation_hash() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="source_degradation_hash"):
        restoration_config.BenchmarkMethodSource(
            method_name="digital_backend",
            checkpoint_path="checkpoints/backend.pt",
            run_id="backend-run",
            source_config_hash="abc123",
            source_degradation_hash="",
            backend=BackendConfig(model_name="nafnet_s"),
        )


@pytest.mark.parametrize(
    "method_name",
    (
        "full_frontend_trained_phase",
        "digital_backend",
        "frozen_optical_frontend_digital_backend",
        "joint_optical_frontend_digital_backend",
    ),
)
def test_benchmark_config_requires_sources_for_trained_methods(method_name: str) -> None:
    """
    Trained benchmark methods require checkpoint source metadata.
    """
    config = BenchmarkConfig(
        dataset_config={"kind": "unit"},
        method_names=(method_name,),
    )

    with pytest.raises(ValueError, match="trained benchmark methods require method_sources"):
        config.validate()


def test_benchmark_config_missing_sources_error_names_missing_methods() -> None:
    """
    Missing source diagnostics identify the trained method without source metadata.
    """
    source = restoration_config.BenchmarkMethodSource(
        method_name="digital_backend",
        checkpoint_path="checkpoints/backend.pt",
        run_id="backend-run",
        source_config_hash="abc123",
        source_degradation_hash="degradation123",
        backend=BackendConfig(model_name="nafnet_s"),
    )
    config = BenchmarkConfig(
        dataset_config={"kind": "unit"},
        method_names=("digital_backend", "joint_optical_frontend_digital_backend"),
        method_sources=(source,),
    )

    with pytest.raises(
        ValueError,
        match=(
            "trained benchmark methods require method_sources: "
            "joint_optical_frontend_digital_backend"
        ),
    ):
        config.validate()


def test_benchmark_config_rejects_duplicate_method_sources() -> None:
    """
    Benchmark method sources must be unique per trained method.
    """
    sources = (
        restoration_config.BenchmarkMethodSource(
            method_name="digital_backend",
            checkpoint_path="checkpoints/backend-a.pt",
            run_id="backend-run-a",
            source_config_hash="abc123",
            source_degradation_hash="degradation123",
            backend=BackendConfig(model_name="nafnet_s"),
        ),
        restoration_config.BenchmarkMethodSource(
            method_name="digital_backend",
            checkpoint_path="checkpoints/backend-b.pt",
            run_id="backend-run-b",
            source_config_hash="def456",
            source_degradation_hash="degradation456",
            backend=BackendConfig(model_name="nafnet_s"),
        ),
    )
    config = BenchmarkConfig(
        dataset_config={"kind": "unit"},
        method_names=("digital_backend",),
        method_sources=sources,
    )

    with pytest.raises(
        ValueError,
        match="method_sources.*digital_backend",
    ):
        config.validate()


@pytest.mark.parametrize(
    "method_name",
    (
        "full_frontend_trained_phase",
        "digital_backend",
        "frozen_optical_frontend_digital_backend",
        "joint_optical_frontend_digital_backend",
    ),
)
def test_benchmark_config_accepts_sources_for_trained_methods(method_name: str) -> None:
    """
    Valid source metadata satisfies trained benchmark method requirements.
    """
    source_kwargs: dict[str, object] = {
        "method_name": method_name,
        "checkpoint_path": f"checkpoints/{method_name}.pt",
        "run_id": f"{method_name}-run",
        "source_config_hash": "abc123",
        "source_degradation_hash": "degradation123",
    }
    if method_name != "full_frontend_trained_phase":
        source_kwargs.update(
            backend=BackendConfig(model_name="nafnet_s"),
        )
    source = restoration_config.BenchmarkMethodSource(**source_kwargs)
    config = BenchmarkConfig(
        dataset_config={"kind": "unit"},
        method_names=(method_name,),
        method_sources=(source,),
    )

    config.validate()


def test_benchmark_config_normalizes_method_source_mappings() -> None:
    """
    BenchmarkConfig accepts mapping payloads for method_sources.
    """
    config = BenchmarkConfig(
        dataset_config={"kind": "unit"},
        method_names=("digital_backend",),
        method_sources=(
            {
                "method_name": "digital_backend",
                "checkpoint_path": "checkpoints/backend.pt",
                "run_id": "backend-run",
                "source_config_hash": "abc123",
                "source_degradation_hash": "degradation123",
                "backend": {
                    "family": "restoration_native",
                    "model_name": "nafnet_s",
                    "residual_learning": True,
                },
            },
        ),
    )

    assert isinstance(config.method_sources[0], restoration_config.BenchmarkMethodSource)
    assert config.method_sources[0].checkpoint_path == Path("checkpoints/backend.pt")
    assert config.method_sources[0].backend == BackendConfig(model_name="nafnet_s")
    config.validate()


@pytest.mark.parametrize(
    "source_payload",
    (
        {"method_name": "digital_backend"},
        {
            "method_name": "digital_backend",
            "checkpoint_path": "checkpoints/backend.pt",
            "unexpected": "value",
        },
        object(),
    ),
)
def test_benchmark_config_rejects_malformed_method_sources_with_index(
    source_payload: object,
) -> None:
    """
    Malformed method source payload errors include the source index.
    """
    with pytest.raises(ValueError, match=r"method_sources\[0\]"):
        BenchmarkConfig(
            dataset_config={"kind": "unit"},
            method_names=("digital_backend",),
            method_sources=(source_payload,),  # type: ignore[arg-type]
        )


def test_benchmark_config_rejects_source_for_disabled_method() -> None:
    """
    Source metadata cannot reference methods outside method_names.
    """
    source = restoration_config.BenchmarkMethodSource(
        method_name="digital_backend",
        checkpoint_path="checkpoints/backend.pt",
        run_id="backend-run",
        source_config_hash="abc123",
        source_degradation_hash="degradation123",
        backend=BackendConfig(model_name="nafnet_s"),
    )
    config = BenchmarkConfig(
        dataset_config={"kind": "unit"},
        method_names=("degraded",),
        method_sources=(source,),
    )

    with pytest.raises(ValueError, match="method_sources must reference enabled method_names"):
        config.validate()


def test_benchmark_method_source_rejects_frontend_source_backend_fields() -> None:
    """
    Frontend-only sources must not declare backend metadata.
    """
    with pytest.raises(ValueError, match="backend must be None for frontend_only"):
        restoration_config.BenchmarkMethodSource(
            method_name="full_frontend_trained_phase",
            checkpoint_path="checkpoints/frontend.pt",
            run_id="frontend-run",
            source_config_hash="abc123",
            source_degradation_hash="degradation123",
            backend=BackendConfig(model_name="nafnet_s"),
        )


def test_benchmark_method_source_records_frontend_construction_fields() -> None:
    """
    Source metadata records the frontend behavior needed for benchmark rebuilds.
    """
    source = restoration_config.BenchmarkMethodSource(
        method_name="full_frontend_trained_phase",
        checkpoint_path="checkpoints/frontend.pt",
        run_id="frontend-run",
        source_config_hash="abc123",
        source_degradation_hash="degradation123",
        phase_parameterization="sigmoid",
        phase_initialization="uniform",
    )

    assert source.phase_parameterization == "sigmoid"
    assert source.phase_initialization == "uniform"


def test_benchmark_method_source_rejects_empty_source_config_path() -> None:
    """
    Source config paths must not normalize to the current directory.
    """
    with pytest.raises(ValueError, match="source_config_path"):
        restoration_config.BenchmarkMethodSource(
            method_name="digital_backend",
            checkpoint_path="checkpoints/backend.pt",
            run_id="backend-run",
            source_config_hash="abc123",
            source_degradation_hash="degradation123",
            source_config_path="",
            backend=BackendConfig(model_name="nafnet_s"),
        )


def test_benchmark_method_source_rejects_deterministic_checkpoints() -> None:
    """
    Deterministic methods do not have checkpoint sources.
    """
    with pytest.raises(
        ValueError,
        match="deterministic methods must not define checkpoints",
    ):
        restoration_config.BenchmarkMethodSource(
            method_name="degraded",
            checkpoint_path="checkpoints/degraded.pt",
            run_id="deterministic-run",
            source_config_hash="abc123",
            source_degradation_hash="degradation123",
        )


def test_benchmark_method_source_rejects_missing_backend() -> None:
    """
    Backend sources must identify the trained nested backend.
    """
    with pytest.raises(
        ValueError,
        match="backend must be a BackendConfig for backend and hybrid roles",
    ):
        restoration_config.BenchmarkMethodSource(
            method_name="digital_backend",
            checkpoint_path="checkpoints/backend.pt",
            run_id="backend-run",
            source_config_hash="abc123",
            source_degradation_hash="degradation123",
        )


def test_benchmark_config_rejects_unknown_method() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = BenchmarkConfig(
        dataset_config={"kind": "unit"},
        method_names=("unknown",),
    )

    with pytest.raises(ValueError, match="method_names must contain only"):
        config.validate()


def test_benchmark_config_rejects_missing_dataset() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match="dataset_config"):
        BenchmarkConfig().validate()


def test_boundary_config_normalizes_grid_and_path_values() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = BoundaryConfig(
        dataset_config={"kind": "unit"},
        operating_point_path="results/restoration/characterization/default/operating_point.json",
        method_names=["degraded", "full_frontend_trained_phase"],  # type: ignore[arg-type]
        blur_levels=[0, 1],  # type: ignore[arg-type]
        noise_levels=[0, 0.05],  # type: ignore[arg-type]
    )

    config.validate()

    assert config.operating_point_path == Path(
        "results/restoration/characterization/default/operating_point.json"
    )
    assert config.method_names == ("degraded", "full_frontend_trained_phase")
    assert config.blur_levels == (0.0, 1.0)
    assert config.noise_levels == (0.0, 0.05)


def test_boundary_config_rejects_legacy_method_names() -> None:
    """
    Legacy boundary method names are rejected instead of normalized.
    """
    config = BoundaryConfig(
        dataset_config={"kind": "unit"},
        method_names=["degraded", "joint_frontend_backend"],  # type: ignore[arg-type]
    )

    assert config.method_names == ("degraded", "joint_frontend_backend")
    with pytest.raises(
        ValueError,
        match="joint_optical_frontend_digital_backend",
    ):
        config.validate()


def test_boundary_config_rejects_unknown_method() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = BoundaryConfig(
        dataset_config={"kind": "unit"},
        method_names=("unknown",),
    )

    with pytest.raises(ValueError, match="method_names must contain only"):
        config.validate()


def test_boundary_config_rejects_missing_dataset() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match="dataset_config"):
        BoundaryConfig().validate()


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("blur_levels", ()),
        ("noise_levels", ()),
    ),
)
def test_boundary_config_rejects_empty_degradation_levels(
    field_name: str,
    value: object,
) -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = BoundaryConfig(dataset_config={"kind": "unit"}, **{field_name: value})

    with pytest.raises(ValueError, match=field_name):
        config.validate()


@pytest.mark.parametrize(
    "field_name",
    (
        "no_recovery_psnr_delta",
        "no_recovery_ssim_delta",
        "no_frontend_gain_psnr_delta",
        "hybrid_no_gain_psnr_delta",
        "hybrid_no_gain_ssim_delta",
    ),
)
def test_boundary_config_rejects_negative_thresholds(field_name: str) -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = BoundaryConfig(dataset_config={"kind": "unit"}, **{field_name: -0.1})

    with pytest.raises(ValueError, match=field_name):
        config.validate()


def test_intensity_normalization_literal_matches_plan_contract() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    assert get_args(IntensityNormalizationPolicy) == (
        "fixed_dataset_level",
        "characterization_calibrated_gain",
        "per_image_min_max",
    )


def test_search_config_defaults_do_not_modify_operating_point() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = SearchConfig()

    assert config.allow_operating_point_search is False
    assert "focal_length" not in config.search_space
    assert "loss_l1_weight" in config.search_space
    assert "phase_offset_reference" in config.search_space
    assert "gain_balance" in config.search_space
    assert config.objective_metric == "val_ssim"


def test_search_config_defensively_copies_and_freezes_search_space() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    external_search_space = {"learning_rate": ["float", 1e-4, 1e-2]}
    config = SearchConfig(search_space=external_search_space)  # type: ignore[arg-type]

    external_search_space["learning_rate"].append(1e-1)
    external_search_space["added_after_construction"] = ["float", 0.0, 1.0]

    assert config.search_space["learning_rate"] == ("float", 1e-4, 1e-2)
    assert "added_after_construction" not in config.search_space
    with pytest.raises(TypeError):
        config.search_space["new_key"] = ("float", 0.0, 1.0)  # type: ignore[index]


def test_search_config_recursively_freezes_nested_search_space_values() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    nested_value = [[1], 2]
    config = SearchConfig(search_space={"x": nested_value})  # type: ignore[arg-type]

    nested_value[0].append(3)

    assert config.search_space["x"] == ((1,), 2)
    assert isinstance(hash(config), int)


def test_search_config_defaults_match_plan_search_contract() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = SearchConfig()

    assert config.enabled is False
    assert config.mode == "single"
    assert config.study_name == "restoration_optuna"
    assert config.storage is None
    assert config.n_trials == 25
    assert config.timeout is None
    assert config.direction == "minimize"
    assert config.sampler_name == "tpe"
    assert config.sampler_seed == 2026
    assert config.pruner_name == "median"
    assert config.final_retrain is True
    assert config.objective_metric == "val_ssim"
    assert config.trial_epochs == 3
    assert config.final_epochs == 50
    assert config.top_k_final_runs == 1


def test_search_config_validates_mode_sampler_and_pruner_names() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    SearchConfig(mode="single").validate()
    SearchConfig(mode="optuna_search").validate()
    SearchConfig(mode="optuna_with_final_retrain").validate()

    with pytest.raises(ValueError, match="mode"):
        SearchConfig(mode="search")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="sampler_name"):
        SearchConfig(sampler_name="").validate()
    with pytest.raises(ValueError, match="pruner_name"):
        SearchConfig(pruner_name="").validate()


@pytest.mark.parametrize("field_name", ["enabled", "final_retrain", "allow_operating_point_search"])
@pytest.mark.parametrize("value", ["false", 0, None])
def test_search_config_rejects_non_boolean_control_fields(field_name: str, value: object) -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match=field_name):
        SearchConfig(**{field_name: value}).validate()  # type: ignore[arg-type]


def test_search_config_default_search_space_covers_training_and_optical_knobs() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    search_space = SearchConfig().search_space

    assert {
        "learning_rate",
        "weight_decay",
        "loss_l1_weight",
        "loss_ssim_weight",
        "loss_frequency_weight",
        "phase_smoothness_weight",
        "phase_offset_reference",
        "gain_balance",
    }.issubset(search_space)
    SearchConfig().validate()


def test_characterization_config_normalizes_sequence_inputs_for_hashability() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = CharacterizationConfig(
        target_names=[
            "point_grid",
            "slanted_edge",
            "sinusoidal_gratings",
            "usaf_bars",
            "siemens_star",
        ],
        baseline_names=[
            "input_identity",
            "reference_arm_only",
            "process_arm_phase_zero",
            "full_frontend_phase_zero",
            "interference_term",
        ],
        focal_length_candidates=[0.20, 0.25, 0.30],
        phase_mask_resolution_candidates=[512, 1024],
        aperture_policy_candidates=["full_slm_active_area", "radius_0_75", "radius_0_50"],
        phase_offset_reference_candidates=[0.0, math.pi / 2, math.pi, 3 * math.pi / 2],
    )

    config.validate()
    assert isinstance(config.target_names, tuple)
    assert isinstance(config.baseline_names, tuple)
    assert isinstance(config.focal_length_candidates, tuple)
    assert isinstance(config.phase_mask_resolution_candidates, tuple)
    assert isinstance(config.aperture_policy_candidates, tuple)
    assert isinstance(config.phase_offset_reference_candidates, tuple)
    assert isinstance(hash(config), int)


def test_training_config_hashes_unhashable_dataset_payloads() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    config = TrainingConfig(
        train_dataset_config={"name": "train"},
        val_dataset_config=["validation"],
        trainable_parameters=["phase_mask_fourier"],
    )

    config.validate()
    assert config.trainable_parameters == ("phase_mask_fourier",)
    assert isinstance(hash(config), int)


def test_frontend_source_config_normalizes_checkpoint_path() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    source = FrontendSourceConfig(
        checkpoint_path="checkpoints/frontend.pt",
        run_id="frontend-run",
        source_config_hash="config-hash",
        source_geometry_hash="geometry-hash",
        source_degradation_hash="degradation-hash",
    )

    assert source.checkpoint_path == Path("checkpoints/frontend.pt")
    source.validate()


@pytest.mark.parametrize(
    "field_name",
    (
        "checkpoint_path",
        "run_id",
        "source_config_hash",
        "source_geometry_hash",
        "source_degradation_hash",
    ),
)
def test_frontend_source_config_rejects_empty_required_fields(field_name: str) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    values = {
        "checkpoint_path": "checkpoints/frontend.pt",
        "run_id": "frontend-run",
        "source_config_hash": "config-hash",
        "source_geometry_hash": "geometry-hash",
        "source_degradation_hash": "degradation-hash",
    }
    values[field_name] = ""

    with pytest.raises(ValueError, match=field_name):
        FrontendSourceConfig(**values).validate()  # type: ignore[arg-type]


def test_public_invalid_inputs_raise_value_error() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    with pytest.raises(ValueError, match="run_name"):
        BasicConfig(run_name=123).validate()  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="search"):
        TrainingConfig(search="x").validate()  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="search_space"):
        SearchConfig(search_space={"x": 1})  # type: ignore[arg-type]


def test_restoration_config_dataclasses_are_hashable() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    configs = (
        BasicConfig(),
        OpticalBenchConfig(),
        CharacterizationConfig(),
        BackendConfig(),
        SearchConfig(),
        TrainingConfig(),
    )

    for config in configs:
        assert isinstance(hash(config), int)


def test_config_module_removes_legacy_restoration_prefixed_names() -> None:
    """
    鏍￠獙閰嶇疆濂戠害
    """
    for name in (
        "RestorationBasicConfig",
        "RestorationGeometryConfig",
        "RestorationCharacterizationConfig",
        "RestorationTrainingConfig",
        "RestorationSearchConfig",
    ):
        assert not hasattr(restoration_config, name)


def test_training_config_connection_participates_in_hash() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    frontend_source = FrontendSourceConfig(
        checkpoint_path="checkpoints/frontend.pt",
        run_id="frontend-run",
        source_config_hash="config-hash",
        source_geometry_hash="geometry-hash",
        source_degradation_hash="degradation-hash",
    )
    shared_values = {
        "model_role": "frozen_optical_frontend_digital_backend",
        "trainable_parameters": ("backend",),
        "frontend_source": frontend_source,
    }
    serial = TrainingConfig(
        **shared_values,
        connection=ConnectionConfig("serial"),
    )
    gated = TrainingConfig(
        **shared_values,
        connection=ConnectionConfig.with_optical_residual_gate(),
    )

    assert hash(serial) != hash(gated)


def test_training_config_rejects_nonserial_connection_for_backend_only() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="non-serial connection"):
        TrainingConfig(
            model_role="backend_only",
            trainable_parameters=("backend",),
            connection=ConnectionConfig.with_optical_residual_gate(),
        )


def test_training_config_requires_frontend_source_for_hybrid_role() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="frontend_source"):
        TrainingConfig(
            model_role="frozen_optical_frontend_digital_backend",
            trainable_parameters=("backend",),
        ).validate()


def test_training_config_rejects_frontend_source_for_non_hybrid_role() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="frontend_source"):
        TrainingConfig(
            frontend_source=FrontendSourceConfig(
                checkpoint_path="checkpoints/frontend.pt",
                run_id="frontend-run",
                source_config_hash="config-hash",
                source_geometry_hash="geometry-hash",
                source_degradation_hash="degradation-hash",
            ),
        ).validate()


def test_training_config_normalizes_frontend_source_mapping() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    config = TrainingConfig(
        model_role="joint_optical_frontend_digital_backend",
        trainable_parameters=("phase_mask_fourier", "backend"),
        frontend_source={
            "checkpoint_path": "checkpoints/frontend.pt",
            "run_id": "frontend-run",
            "source_config_hash": "config-hash",
            "source_geometry_hash": "geometry-hash",
            "source_degradation_hash": "degradation-hash",
        },
    )

    assert isinstance(config.frontend_source, FrontendSourceConfig)
    assert config.frontend_source.checkpoint_path == Path("checkpoints/frontend.pt")
    config.validate()


def test_training_config_allows_trainable_connection_for_hybrid_role() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    config = TrainingConfig(
        model_role="frozen_optical_frontend_digital_backend",
        trainable_parameters=("connection", "backend"),
        connection=ConnectionConfig.with_optical_residual_gate(),
        frontend_source=FrontendSourceConfig(
            checkpoint_path="checkpoints/frontend.pt",
            run_id="frontend-run",
            source_config_hash="config-hash",
            source_geometry_hash="geometry-hash",
            source_degradation_hash="degradation-hash",
        ),
    )

    config.validate()


@pytest.mark.parametrize("mode", ["serial", "degraded_image"])
def test_training_config_rejects_trainable_connection_without_connection_parameters(
    mode: str,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="trainable connection"):
        TrainingConfig(
            model_role="frozen_optical_frontend_digital_backend",
            trainable_parameters=("connection", "backend"),
            connection=ConnectionConfig(mode),  # type: ignore[arg-type]
            frontend_source=FrontendSourceConfig(
                checkpoint_path="checkpoints/frontend.pt",
                run_id="frontend-run",
                source_config_hash="config-hash",
                source_geometry_hash="geometry-hash",
                source_degradation_hash="degradation-hash",
            ),
        ).validate()


def test_benchmark_method_source_normalizes_connection_mapping() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    source = restoration_config.BenchmarkMethodSource(
        method_name="frozen_optical_frontend_digital_backend",
        checkpoint_path="checkpoints/frozen.pt",
        run_id="frozen-run",
        source_config_hash="abc123",
        source_degradation_hash="degradation123",
        backend=BackendConfig(model_name="nafnet_s"),
        connection={"mode": "optical_residual_gate"},
    )

    assert source.connection == ConnectionConfig("optical_residual_gate")
    source.validate()


def test_benchmark_method_source_rejects_nonserial_connection_for_backend_only() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="non-serial connection"):
        restoration_config.BenchmarkMethodSource(
            method_name="digital_backend",
            model_role="backend_only",
            checkpoint_path=Path("checkpoint.pt"),
            run_id="run",
            source_config_hash="hash",
            source_degradation_hash="degradation-hash",
            backend=BackendConfig(model_name="nafnet_s"),
            connection=ConnectionConfig.with_optical_residual_gate(),
        )


@pytest.mark.parametrize(
    "mode",
    ["dual_channel", "dual_channel_optical_zeroed"],
)
def test_training_config_rejects_dual_channel_with_single_channel_backend(
    mode: str,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="multi-channel backend"):
        TrainingConfig(
            model_role="frozen_optical_frontend_digital_backend",
            trainable_parameters=("backend",),
            backend=BackendConfig(model_name="nafnet_s"),
            connection=ConnectionConfig(mode),  # type: ignore[arg-type]
            frontend_source=FrontendSourceConfig(
                checkpoint_path="checkpoints/frontend.pt",
                run_id="frontend-run",
                source_config_hash="config-hash",
                source_geometry_hash="geometry-hash",
                source_degradation_hash="degradation-hash",
            ),
        ).validate()


def test_training_config_allows_optical_residual_gate_with_single_channel_backend() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    config = TrainingConfig(
        model_role="frozen_optical_frontend_digital_backend",
        trainable_parameters=("backend",),
        backend=BackendConfig(model_name="nafnet_s"),
        connection=ConnectionConfig.with_optical_residual_gate(),
        frontend_source=FrontendSourceConfig(
            checkpoint_path="checkpoints/frontend.pt",
            run_id="frontend-run",
            source_config_hash="config-hash",
            source_geometry_hash="geometry-hash",
            source_degradation_hash="degradation-hash",
        ),
    )

    config.validate()


def test_benchmark_method_source_rejects_dual_channel_with_single_channel_backend() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="multi-channel backend"):
        restoration_config.BenchmarkMethodSource(
            method_name="frozen_optical_frontend_digital_backend",
            checkpoint_path="checkpoints/frozen.pt",
            run_id="frozen-run",
            source_config_hash="abc123",
            source_degradation_hash="degradation123",
            backend=BackendConfig(model_name="nafnet_s"),
            connection=ConnectionConfig("dual_channel"),
        )

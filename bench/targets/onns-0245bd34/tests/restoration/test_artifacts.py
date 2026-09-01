from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path

import pytest

import experiments.restoration.fixed_measurement.evidence.training_artifacts as artifacts
from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
from experiments.restoration.fixed_measurement.learning.config import (
    BasicConfig,
    CharacterizationConfig,
)
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.fixed_measurement.learning.connection import ConnectionConfig
from experiments.restoration.optical_bench import build_theoretical_resolution_budget


def test_build_characterization_paths_uses_semantic_directory(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    basic = BasicConfig(project_root=tmp_path, run_name="resolution_scan")

    paths = artifacts.build_characterization_paths(basic)

    run_dir = tmp_path / "results" / "restoration" / "characterization" / "resolution_scan"
    assert paths["run_dir"] == run_dir
    assert paths["figures_dir"] == run_dir / "figures"
    assert paths["metrics_csv"] == run_dir / "metrics.csv"
    assert paths["summary_md"] == run_dir / "summary.md"
    assert paths["config_json"] == run_dir / "config.json"
    assert paths["runtime_json"] == run_dir / "runtime.json"
    assert paths["operating_point_json"] == run_dir / "operating_point.json"


def test_write_json_uses_semantic_connection_fields(tmp_path: Path) -> None:
    """
    校验配置产物使用当前语义字段并可直接重建对象
    """
    path = artifacts.write_json(tmp_path / "connection.json", ConnectionConfig())

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload == {
        "mode": "serial",
        "optical_residual_gate_logit": 0.0,
    }
    assert ConnectionConfig(**payload) == ConnectionConfig()


def test_build_training_paths_nests_frontend_only_under_training_role(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    basic = BasicConfig(project_root=tmp_path, run_name="train_a")

    paths = artifacts.build_training_paths(basic, model_role="frontend_only")

    run_dir = tmp_path / "results" / "restoration" / "training" / "frontend_only" / "train_a"
    assert paths["run_dir"] == run_dir
    assert paths["figures_dir"] == run_dir / "figures"
    assert paths["checkpoints_dir"] == run_dir / "checkpoints"
    assert paths["best_checkpoint"] == run_dir / "checkpoints" / "best.pt"
    assert paths["last_checkpoint"] == run_dir / "checkpoints" / "last.pt"
    assert paths["operating_point_used_json"] == run_dir / "operating_point_used.json"
    assert paths["checks_json"] == run_dir / "checks.json"
    assert paths["phase_masks_dir"] == run_dir / "phase_masks"
    assert paths["epoch_metrics_csv"] == run_dir / "epoch_metrics.csv"
    assert paths["final_metrics_json"] == run_dir / "final_metrics.json"
    assert paths["summary_md"] == run_dir / "summary.md"
    assert paths["config_json"] == run_dir / "config.json"
    assert paths["runtime_json"] == run_dir / "runtime.json"
    assert paths["optuna_dir"] == run_dir / "optuna"
    assert paths["optuna_study_json"] == run_dir / "optuna" / "study_summary.json"


def test_build_training_paths_requires_backend_metadata_for_backend_only(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    basic = BasicConfig(project_root=tmp_path, run_name="train_backend")

    with pytest.raises(ValueError, match="backend is required"):
        artifacts.build_training_paths(basic, model_role="backend_only")


def test_build_training_paths_nests_backend_only_under_backend_model(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    basic = BasicConfig(project_root=tmp_path, run_name="train_backend")

    paths = artifacts.build_training_paths(
        basic,
        model_role="backend_only",
        backend=BackendConfig(model_name="nafnet_s"),
    )

    run_dir = (
        tmp_path
        / "results"
        / "restoration"
        / "training"
        / "backend_only"
        / "restoration_native"
        / "nafnet_s"
        / "train_backend"
    )
    assert paths["run_dir"] == run_dir
    assert paths["best_checkpoint"] == run_dir / "checkpoints" / "best.pt"
    assert paths["last_checkpoint"] == run_dir / "checkpoints" / "last.pt"
    assert paths["operating_point_used_json"] == run_dir / "operating_point_used.json"
    assert paths["checks_json"] == run_dir / "checks.json"
    assert paths["phase_masks_dir"] == run_dir / "phase_masks"


def test_build_training_paths_rejects_legacy_hybrid_role(tmp_path: Path) -> None:
    """
    Legacy hybrid roles are rejected instead of normalized into paths.
    """
    basic = BasicConfig(project_root=tmp_path, run_name="train_hybrid")

    with pytest.raises(
        ValueError,
        match="joint_optical_frontend_digital_backend",
    ):
        artifacts.build_training_paths(
            basic,
            model_role="joint_frontend_backend",
            backend=BackendConfig(model_name="nafnet_s"),
        )


def test_build_training_paths_rejects_invalid_model_role(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    basic = BasicConfig(project_root=tmp_path, run_name="train_invalid")

    with pytest.raises(ValueError, match="model_role must be one of"):
        artifacts.build_training_paths(basic, model_role="deterministic")


def test_build_benchmark_paths_uses_study_layout(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    paths = artifacts.build_benchmark_paths(tmp_path, study_name="ablation")

    root = tmp_path / "results" / "restoration" / "benchmark" / "ablation"
    assert paths["run_dir"] == root
    assert paths["sample_metrics_csv"] == root / "sample_metrics.csv"
    assert paths["baseline_metrics_csv"] == root / "baseline_metrics.csv"
    assert paths["method_manifest_json"] == root / "method_manifest.json"
    assert paths["examples_dir"] == root / "examples"


def test_build_boundary_paths_uses_study_layout(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    paths = artifacts.build_boundary_paths(tmp_path, study_name="stress")

    root = tmp_path / "results" / "restoration" / "boundary" / "stress"
    assert paths["run_dir"] == root
    assert paths["figures_dir"] == root / "figures"
    assert paths["examples_dir"] == root / "examples"
    assert paths["config_json"] == root / "config.json"
    assert paths["runtime_json"] == root / "runtime.json"
    assert paths["dataset_manifest_json"] == root / "dataset_manifest.json"
    assert paths["method_manifest_json"] == root / "method_manifest.json"
    assert paths["degradation_grid_csv"] == root / "degradation_grid.csv"
    assert paths["boundary_metrics_csv"] == root / "boundary_metrics.csv"
    assert paths["failure_boundary_csv"] == root / "failure_boundary.csv"
    assert paths["summary_md"] == root / "summary.md"


def test_write_benchmark_sample_metrics_uses_fixed_field_order(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    path = artifacts.write_benchmark_sample_metrics(
        tmp_path / "sample_metrics.csv",
        [
            {
                "study_name": "ablation",
                "schema_version": "restoration_benchmark_v4",
                "condition_id": "condition_000",
                "sample_id": "sample_000",
                "dataset_name": "unit",
                "method_name": "degraded",
                "model_role": "deterministic",
                "source_run_id": "",
                "source_checkpoint_path": "",
                "source_config_hash": "",
                "source_degradation_hash": "",
                "frontend_condition": "none",
                "backend_family": "none",
                "backend_model": "none",
                "degradation_family": "unit",
                "degradation_level": 0.0,
                "metric_name": "psnr",
                "metric_value": 12.0,
                "metric_unit": "dB",
                "status": "PASS",
            }
        ],
    )

    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith(
        "schema_version,study_name,condition_id,sample_id,dataset_name"
    )


def test_write_benchmark_baseline_metrics_uses_fixed_field_order(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    path = artifacts.write_benchmark_baseline_metrics(
        tmp_path / "baseline_metrics.csv",
        [
            {
                "study_name": "ablation",
                "schema_version": "restoration_benchmark_v4",
                "condition_id": "condition_000",
                "method_name": "degraded",
                "model_role": "deterministic",
                "source_run_id": "",
                "source_checkpoint_path": "",
                "source_config_hash": "",
                "source_degradation_hash": "",
                "frontend_condition": "none",
                "backend_family": "none",
                "backend_model": "none",
                "metric_name": "psnr",
                "mean_value": 12.0,
                "std_value": 0.0,
                "median_value": 12.0,
                "num_samples": 1,
                "metric_unit": "dB",
                "status": "PASS",
            }
        ],
    )

    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("schema_version,study_name,condition_id,method_name")


def test_write_boundary_grid_uses_fixed_field_order(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    path = artifacts.write_boundary_grid(
        tmp_path / "degradation_grid.csv",
        [
            {
                "study_name": "stress",
                "condition_id": "condition_000",
                "degradation_family": "blur_noise",
                "blur_level": 1.0,
                "noise_level": 0.01,
                "seed": 2026,
                "status": "PASS",
            }
        ],
    )

    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("study_name,condition_id,degradation_family")


def test_write_failure_boundary_uses_fixed_field_order(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    path = artifacts.write_failure_boundary(
        tmp_path / "failure_boundary.csv",
        [
            {
                "study_name": "stress",
                "condition_id": "condition_000",
                "method_name": "full_frontend_trained_phase",
                "model_role": "frontend_only",
                "frontend_condition": "full_frontend_trained_phase",
                "backend_family": "none",
                "backend_model": "none",
                "reference_method_name": "degraded",
                "primary_metric_name": "psnr",
                "primary_metric_delta": 0.2,
                "secondary_metric_name": "ssim",
                "secondary_metric_delta": 0.005,
                "failure_label": "no_recovery",
                "failure_reason": "below threshold",
                "status": "PASS",
            }
        ],
    )

    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("study_name,condition_id,method_name,model_role")


def test_json_writer_preserves_sorted_schema(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    @dataclass(frozen=True)
    class Payload:
        """
        鎻愪緵浜х墿娴嬭瘯澶瑰叿
        """
        z_path: Path
        a_pair: tuple[int, int]

    path = artifacts.write_json(
        tmp_path / "nested" / "payload.json",
        {
            "payload": Payload(z_path=Path("outputs/config.json"), a_pair=(2, 1)),
            "items": ({"b": 2, "a": 1}, ["x", Path("y")]),
        },
    )

    assert path == tmp_path / "nested" / "payload.json"
    text = path.read_text(encoding="utf-8")
    assert text == (
        "{\n"
        '  "items": [\n'
        "    {\n"
        '      "a": 1,\n'
        '      "b": 2\n'
        "    },\n"
        "    [\n"
        '      "x",\n'
        '      "y"\n'
        "    ]\n"
        "  ],\n"
        '  "payload": {\n'
        '    "a_pair": [\n'
        "      2,\n"
        "      1\n"
        "    ],\n"
        '    "z_path": "outputs/config.json"\n'
        "  }\n"
        "}\n"
    )
    assert json.loads(text)["payload"]["a_pair"] == [2, 1]


def test_scalar_like_item_values_serialize_as_json_numbers_and_hash_like_scalars(
    tmp_path: Path,
) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    class FakeScalar:
        """
        鎻愪緵浜х墿娴嬭瘯澶瑰叿
        """
        def __init__(self, value: object) -> None:
            """
            淇濆瓨鍙?JSON 搴忓垪鍖栫殑娴嬭瘯鍊?            """
            self.value = value

        def item(self) -> object:
            """
            鏋勫缓浜х墿娴嬭瘯鏁版嵁
            """
            return self.value

    path = artifacts.write_json(
        tmp_path / "scalar.json",
        {"x": FakeScalar(7), "y": FakeScalar(2.5)},
    )

    assert json.loads(path.read_text(encoding="utf-8")) == {"x": 7, "y": 2.5}
    assert artifacts.compute_config_hash({"x": FakeScalar(7)}) == artifacts.compute_config_hash(
        {"x": 7}
    )
    assert artifacts.compute_config_hash({"x": FakeScalar(2.5)}) == artifacts.compute_config_hash(
        {"x": 2.5}
    )


def test_write_json_rejects_nonfinite_float_values(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    path = tmp_path / "bad.json"

    with pytest.raises(ValueError):
        artifacts.write_json(path, {"x": float("inf")})

    assert not path.exists()


def test_compute_config_hash_rejects_nonfinite_float_values() -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    with pytest.raises(ValueError):
        artifacts.compute_config_hash({"x": float("nan")})


def test_scalar_like_item_nonfinite_values_raise_value_error(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    class FakeScalar:
        """
        鎻愪緵浜х墿娴嬭瘯澶瑰叿
        """
        def item(self) -> float:
            """
            鏋勫缓浜х墿娴嬭瘯鏁版嵁
            """
            return float("inf")

    with pytest.raises(ValueError):
        artifacts.write_json(tmp_path / "bad_scalar.json", {"x": FakeScalar()})


def test_unsupported_objects_raise_type_error_instead_of_stringifying(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    class Unsupported:
        """
        鎻愪緵浜х墿娴嬭瘯澶瑰叿
        """
        pass

    with pytest.raises(TypeError, match="unsupported evidence value"):
        artifacts.write_json(tmp_path / "unsupported.json", {"x": Unsupported()})

    with pytest.raises(TypeError, match="unsupported evidence value"):
        artifacts.compute_config_hash({"x": Unsupported()})


def test_characterization_metrics_csv_has_required_long_form_fields(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    required_fields = (
        "candidate_id",
        "sweep_step",
        "run_name",
        "target_name",
        "target_variant",
        "baseline_name",
        "focal_length",
        "phase_mask_resolution",
        "aperture_policy",
        "slm2_active_area_policy",
        "padding_policy",
        "phase_offset_reference",
        "camera_oversampling_factor",
        "camera_sampling",
        "camera_binning_policy",
        "spatial_frequency",
        "metric_name",
        "metric_value",
        "metric_unit",
        "status",
    )
    row = {
        "candidate_id": "candidate-001",
        "sweep_step": "broad",
        "run_name": "resolution_scan",
        "target_name": "slanted_edge",
        "target_variant": "vertical",
        "baseline_name": "reference_arm_only",
        "focal_length": 0.25,
        "phase_mask_resolution": 512,
        "aperture_policy": "full_slm_active_area",
        "slm2_active_area_policy": "center_square",
        "padding_policy": "center_pad",
        "phase_offset_reference": 0.0,
        "camera_oversampling_factor": 1,
        "camera_sampling": "native_sensor",
        "camera_binning_policy": "none",
        "spatial_frequency": 12.5,
        "metric_name": "mtf50",
        "metric_value": 0.42,
        "metric_unit": "cycles_per_meter",
        "status": "PASS",
        "ignored_extra": "does not enter schema",
    }

    path = artifacts.write_characterization_metrics(tmp_path / "metrics" / "metrics.csv", [row])

    assert artifacts.CHARACTERIZATION_METRIC_FIELDS[: len(required_fields)] == required_fields
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(artifacts.CHARACTERIZATION_METRIC_FIELDS)
        assert list(reader) == [
            {
                field: str(row[field])
                for field in artifacts.CHARACTERIZATION_METRIC_FIELDS
            }
        ]


def test_operating_point_includes_hashes_and_source_paths(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    basic = BasicConfig(project_root=tmp_path, run_name="resolution_scan")
    geometry = OpticalBenchConfig()
    characterization = CharacterizationConfig(basic=basic, model=geometry)
    selected_values = {
        "focal_length": 0.25,
        "phase_mask_resolution": 512,
        "phase_offset_reference": 0.0,
    }
    theoretical_budget = build_theoretical_resolution_budget(geometry)

    path = artifacts.write_operating_point(
        tmp_path / "operating" / "operating_point.json",
        basic=basic,
        model=geometry,
        characterization=characterization,
        theoretical_budget=theoretical_budget,
        selected_values=selected_values,
        source_config_path=tmp_path / "config.json",
        source_metrics_path=tmp_path / "metrics.csv",
        code_version="abc123",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["stage"] == "characterization"
    assert payload["status"] == "PASS"
    assert payload["created_at"]
    assert payload["config_hash"] == artifacts.compute_config_hash(characterization)
    assert payload["geometry_hash"] == artifacts.compute_config_hash(geometry)
    assert isinstance(payload["config_hash"], str)
    assert isinstance(payload["geometry_hash"], str)
    assert payload["source_config_path"] == str(tmp_path / "config.json")
    assert payload["source_metrics_path"] == str(tmp_path / "metrics.csv")
    assert payload["code_version"] == "abc123"
    assert payload["selected_values"] == selected_values


def test_training_epoch_fields_include_raw_and_normalized_metrics(tmp_path: Path) -> None:
    """
    鏍￠獙浜х墿濂戠害
    """
    required_fields = (
        "epoch",
        "split",
        "optimizer_updates",
        "loss_total",
        "loss_l1",
        "loss_ssim",
        "loss_frequency",
        "phase_smoothness",
        "psnr_raw",
        "ssim_raw",
        "psnr_normalized",
        "ssim_normalized",
        "energy_throughput",
        "clipping_ratio",
        "learning_rate",
        "phase_offset_reference",
        "optical_residual_gate",
        "operating_point_hash",
        "status",
    )
    rows = [
        {
            "epoch": 1,
            "split": "train",
            "optimizer_updates": 1,
            "loss_total": 0.7,
            "loss_l1": 0.4,
            "loss_ssim": 0.2,
            "loss_frequency": 0.1,
            "phase_smoothness": 0.01,
            "psnr_raw": 24.5,
            "ssim_raw": 0.75,
            "psnr_normalized": 26.0,
            "ssim_normalized": 0.82,
            "energy_throughput": 0.9,
            "clipping_ratio": 0.02,
            "learning_rate": 0.001,
            "phase_offset_reference": 0.0,
            "optical_residual_gate": 0.99,
            "operating_point_hash": "op-hash",
            "status": "PASS",
            "ignored_extra": "does not enter schema",
        },
        {
            "epoch": 1,
            "split": "val",
            "optimizer_updates": 1,
            "loss_total": 0.8,
            "status": "PASS",
        },
    ]

    path = tmp_path / "metrics" / "epoch_metrics.csv"
    artifacts.append_training_epoch_metrics(path, [rows[0]])
    artifacts.append_training_epoch_metrics(path, [rows[1]])

    assert artifacts.TRAINING_EPOCH_FIELDS[: len(required_fields)] == required_fields
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        written_rows = list(reader)
    assert reader.fieldnames == list(artifacts.TRAINING_EPOCH_FIELDS)
    assert len(written_rows) == 2
    assert written_rows[0] == {
        field: str(rows[0][field])
        for field in artifacts.TRAINING_EPOCH_FIELDS
    }
    assert written_rows[1]["epoch"] == "1"
    assert written_rows[1]["split"] == "val"
    assert written_rows[1]["loss_total"] == "0.8"
    assert written_rows[1]["loss_l1"] == ""
    assert written_rows[1]["status"] == "PASS"

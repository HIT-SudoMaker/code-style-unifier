from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
from types import SimpleNamespace

import torch
import pytest

from experiments.restoration.fixed_measurement.learning.config import TrainingConfig
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.fixed_measurement import (
    FixedMeasurementRequest,
    record_fixed_optical_states,
    run_fixed_measurement,
)
from experiments.restoration.fixed_measurement.optics.frontend import RestorationFrontend


def _request(tmp_path: Path) -> FixedMeasurementRequest:
    operating_point = tmp_path / "operating_point.json"
    operating_point.write_text(
        json.dumps({"geometry_hash": "geometry-hash"}),
        encoding="utf-8",
    )
    return FixedMeasurementRequest(
        project_root=tmp_path,
        operating_point_path=operating_point,
        split_manifest={"records": []},
        execution_mode="train",
    )


def test_run_fixed_measurement_hides_one_four_role_matrix(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from experiments.restoration.fixed_measurement import experiment

    captured = {}
    monkeypatch.setattr(experiment, "verify_protocol_inputs", lambda inputs: None)

    def execute(plan):
        captured["plan"] = plan
        return SimpleNamespace(
            status="PASS",
            studies=tuple(SimpleNamespace() for _ in plan.studies),
            report_json=tmp_path / "experiment_report.json",
            summary_md=tmp_path / "summary.md",
            skipped_run_ids=(),
        )

    monkeypatch.setattr(experiment, "run_experiment", execute)

    record = run_fixed_measurement(_request(tmp_path))

    plan = captured["plan"]
    assert record.status == "PASS"
    assert record.execution_mode == "trained"
    assert record.study_count == 45
    assert Counter(study.study_id for study in plan.studies) == {
        "trained_phase_frontend_only": 9,
        "digital_backend_only": 18,
        "frozen_frontend_serial": 9,
        "joint_frontend_serial": 9,
    }
    assert all(
        isinstance(study.configuration, TrainingConfig) for study in plan.studies
    )
    digital_bearing = [
        study
        for study in plan.studies
        if study.study_id != "trained_phase_frontend_only"
    ]
    backend_counts = Counter(
        study.configuration.backend.model_name
        for study in digital_bearing
        if study.configuration.backend is not None
    )
    assert backend_counts == {"nafnet_s": 27, "nafnet_m": 9}
    assert all(
        study.study_id == "digital_backend_only"
        for study in digital_bearing
        if study.configuration.backend is not None
        and study.configuration.backend.model_name == "nafnet_m"
    )
    assert not any(
        "eleven" in study.configuration.basic.run_name for study in plan.studies
    )

    source_by_profile_seed = {
        (study.profile_name, study.seed): study
        for study in plan.studies
        if study.study_id == "trained_phase_frontend_only"
    }
    for study in plan.studies:
        if study.study_id not in {
            "frozen_frontend_serial",
            "joint_frontend_serial",
        }:
            continue
        source = source_by_profile_seed[(study.profile_name, study.seed)]
        assert study.upstream_run_ids == (source.run_id,)
        assert study.configuration.frontend_source is not None
        assert study.configuration.frontend_source.run_id == source.run_id


def test_run_fixed_measurement_loads_native_archive_by_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from experiments.restoration.fixed_measurement import experiment

    monkeypatch.setattr(experiment, "verify_protocol_inputs", lambda inputs: None)
    source_report = tmp_path / "source_report.json"
    summary = tmp_path / "summary.md"
    monkeypatch.setattr(
        experiment,
        "load_native_fixed_archive",
        lambda inputs: SimpleNamespace(
            status="PASS",
            studies=tuple(SimpleNamespace() for _ in range(45)),
            report_json=source_report,
            summary_md=summary,
            skipped_run_ids=(),
        ),
    )

    def reject_training(plan):
        raise AssertionError("native archive loading must not launch training")

    monkeypatch.setattr(experiment, "run_experiment", reject_training)
    request = _request(tmp_path)
    request = FixedMeasurementRequest(
        project_root=request.project_root,
        operating_point_path=request.operating_point_path,
        split_manifest=request.split_manifest,
    )

    record = run_fixed_measurement(request)

    assert record.status == "PASS"
    assert record.study_count == 45
    assert record.execution_mode == "loaded"
    assert record.report_json == source_report


def test_fixed_optical_record_names_arms_and_interference_without_ambiguity() -> None:
    frontend = RestorationFrontend(
        OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    )
    with torch.no_grad():
        frontend.phase_mask_fourier.fill_(0.25)
    input_field = torch.full(
        (1, 1, 8, 8),
        math.sqrt(0.25),
        dtype=torch.complex64,
    )

    record = record_fixed_optical_states(frontend, input_field)

    assert tuple(record.as_mapping()) == (
        "reference_arm_only",
        "zero_phase_processing_arm_only",
        "trained_phase_processing_arm_only",
        "zero_phase_interference_output",
        "trained_phase_interference_output",
    )
    assert record.reference_arm_only.shape == input_field.shape
    assert record.zero_phase_processing_arm_only.shape == input_field.shape
    assert record.trained_phase_processing_arm_only.shape == input_field.shape
    assert not torch.equal(
        record.zero_phase_interference_output,
        record.trained_phase_interference_output,
    )
    assert torch.allclose(
        record.zero_phase_interference_output
        - record.reference_arm_only
        - record.zero_phase_processing_arm_only,
        record.zero_phase_interference_term,
    )
    assert torch.allclose(
        record.trained_phase_interference_output
        - record.reference_arm_only
        - record.trained_phase_processing_arm_only,
        record.trained_phase_interference_term,
    )


def test_fixed_optical_record_is_immutable_and_retains_phase_identity(
    tmp_path: Path,
) -> None:
    frontend = RestorationFrontend(
        OpticalBenchConfig(input_array_resolution=(8, 8), phase_mask_resolution=8)
    )
    input_field = torch.ones((1, 1, 8, 8), dtype=torch.complex64)
    record = record_fixed_optical_states(frontend, input_field)
    output_path = tmp_path / "controls.pt"

    record.write(
        output_path,
        metadata={"sample_id": "sample-001", "split": "validation"},
    )

    payload = torch.load(output_path, map_location="cpu", weights_only=True)
    assert payload["schema_version"] == "fixed_optical_record_v1"
    assert payload["metadata"] == {
        "sample_id": "sample-001",
        "split": "validation",
    }
    assert payload["state_manifest"]["reference_arm_only"] == {
        "is_reference_enabled": True,
        "is_processing_enabled": False,
        "processing_phase_state": "not_applicable",
    }
    assert payload["state_manifest"]["trained_phase_interference_output"] == {
        "is_reference_enabled": True,
        "is_processing_enabled": True,
        "processing_phase_state": "trained",
    }
    assert torch.equal(payload["input_intensity"], input_field.abs().square())
    assert torch.equal(
        payload["trained_phase_radians"],
        record.trained_phase_radians,
    )
    with pytest.raises(FileExistsError, match="already exists"):
        record.write(output_path, metadata={"sample_id": "replacement"})

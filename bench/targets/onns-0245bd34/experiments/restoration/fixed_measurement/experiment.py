from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from experiments.restoration.fixed_measurement.protocol.inputs import verify_protocol_inputs
from experiments.restoration.fixed_measurement.learning.execution import run_experiment
from experiments.restoration.fixed_measurement.protocol.plan import (
    compile_fixed_experiment_plan,
)
from experiments.restoration.fixed_measurement.evidence.archive import (
    load_native_fixed_archive,
)
from experiments.restoration.fixed_measurement.protocol.settings import ProtocolInputs


@dataclass(frozen=True, slots=True)
class FixedMeasurementRequest:
    """Declare one complete run of the frozen Fixed Measurement matrix."""

    project_root: Path | str
    operating_point_path: Path | str
    split_manifest: Mapping[str, object]
    dataset_root: Path | str = Path("data/raw")
    device: str = "auto"
    execution_mode: Literal["load", "train"] = "load"

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_root", Path(self.project_root))
        object.__setattr__(
            self,
            "operating_point_path",
            Path(self.operating_point_path),
        )
        object.__setattr__(
            self,
            "split_manifest",
            MappingProxyType(dict(self.split_manifest)),
        )
        object.__setattr__(self, "dataset_root", Path(self.dataset_root))
        if self.execution_mode not in {"load", "train"}:
            raise ValueError("execution_mode must be load or train")

    def _protocol_inputs(self) -> ProtocolInputs:
        return ProtocolInputs(
            project_root=self.project_root,
            operating_point_path=self.operating_point_path,
            split_manifest=self.split_manifest,
            dataset_root=self.dataset_root,
            device=self.device,
        )


@dataclass(frozen=True, slots=True)
class FixedMeasurementRecord:
    """Summarize the canonical evidence written by one Fixed experiment."""

    status: str
    study_count: int
    report_json: Path
    summary_md: Path
    skipped_run_ids: tuple[str, ...]
    execution_mode: Literal["loaded", "trained"]


def run_fixed_measurement(
    request: FixedMeasurementRequest,
) -> FixedMeasurementRecord:
    """Verify, compile, execute, and record the four-role Fixed experiment."""
    if not isinstance(request, FixedMeasurementRequest):
        raise TypeError("request must be a FixedMeasurementRequest")
    inputs = request._protocol_inputs()
    verify_protocol_inputs(inputs)
    if request.execution_mode == "load":
        report = load_native_fixed_archive(inputs)
        return FixedMeasurementRecord(
            status=report.status,
            study_count=len(report.studies),
            report_json=report.report_json,
            summary_md=report.summary_md,
            skipped_run_ids=report.skipped_run_ids,
            execution_mode="loaded",
        )
    plan = compile_fixed_experiment_plan(inputs)
    report = run_experiment(plan)
    return FixedMeasurementRecord(
        status=report.status,
        study_count=len(report.studies),
        report_json=report.report_json,
        summary_md=report.summary_md,
        skipped_run_ids=report.skipped_run_ids,
        execution_mode="trained",
    )

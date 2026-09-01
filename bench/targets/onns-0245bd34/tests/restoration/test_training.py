from __future__ import annotations

from collections.abc import Mapping
import csv
import inspect
import json
from pathlib import Path
from typing import get_type_hints

import pytest
import torch
from torch.utils.data import Dataset

from data.configs import (
    DefocusBlurConfig,
    PerturbationConfig,
    SourceConfig,
)
from experiments.restoration.fixed_measurement.learning.data_loading import RestorationDataConfig
import experiments.restoration.fixed_measurement.learning.model_assembly as model_assembly
import experiments.restoration.fixed_measurement.learning.training as training
from experiments.restoration.fixed_measurement.learning import checkpoints
from experiments.restoration.fixed_measurement.evidence.training_artifacts import (
    TRAINING_EPOCH_FIELDS,
    compute_config_hash,
    write_operating_point,
)
from experiments.restoration.fixed_measurement.learning.backend import BackendConfig, build_restoration_backend
from experiments.restoration.fixed_measurement.learning.config import (
    BasicConfig,
    CharacterizationConfig,
    FrontendSourceConfig,
    TrainingConfig,
)
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.fixed_measurement.learning.connection import (
    ConnectionConfig,
    DualChannelConnection,
    DualChannelOpticalZeroedConnection,
    build_connection,
)
from experiments.restoration.fixed_measurement.learning.data_loading import target_from_batch
from experiments.restoration.fixed_measurement.evidence.studies import build_study_artifacts
from experiments.restoration.fixed_measurement.protocol.records import StudyConfig
from experiments.restoration.fixed_measurement.optics.frontend import RestorationFrontend
from experiments.restoration.optical_bench import build_theoretical_resolution_budget
from experiments.restoration.fixed_measurement.learning.standard_configs import (
    build_standard_dataset_config,
    degradation_hash_for_dataset_config,
)
from experiments.restoration.fixed_measurement.learning.training import run_training


_SIMULATED_INTERRUPTION = "simulated interruption"


def test_restoration_engine_exports_compute_kernel_contract() -> None:
    """
    Engine exposes the pure training compute kernel API.
    """
    import experiments.restoration.fixed_measurement.learning.engine as engine

    for name in (
        "run_epoch",
        "baseline_metrics",
        "finite_mean",
        "degraded_image_from_batch",
        "clipping_ratio",
    ):
        assert callable(getattr(engine, name))
    assert tuple(engine.EpochRow.__annotations__) == TRAINING_EPOCH_FIELDS


def test_restoration_engine_preserves_public_batch_mapping_contract() -> None:
    """
    Engine keeps the batch abstraction broad and returns EpochRow without suppression.
    """
    import experiments.restoration.fixed_measurement.learning.engine as engine

    hints = get_type_hints(engine.degraded_image_from_batch)
    assert hints["batch"] == Mapping[str, object]
    assert "type: ignore[return-value]" not in inspect.getsource(engine.run_epoch)


class _EncodedTinyDataset(Dataset):
    """
    鎻愪緵璁粌娴嬭瘯澶瑰叿
    """

    def __init__(self, sample_count: int = 2) -> None:
        """
        淇濆瓨缂栫爜鏍锋湰鏁伴噺
        """
        self.sample_count = sample_count

    def __len__(self) -> int:
        """
        杩斿洖娴嬭瘯鏁版嵁闀垮害
        """
        return self.sample_count

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        杩斿洖鍗曚釜娴嬭瘯鏍锋湰
        """
        image = torch.linspace(0.0, 1.0, steps=64, dtype=torch.float32).reshape(1, 8, 8)
        if index % 2:
            image = torch.flip(image, dims=(-1,))
        field = torch.sqrt(image).to(torch.complex64)
        return {
            "input_field": field,
            "input_image": image,
            "degraded_image": image,
            "clean_image": image.clone(),
            "label": index,
            "category": "tiny",
            "provenance": {"index": index},
        }


class _EncodedZeroDataset(Dataset):
    """
    鎻愪緵璁粌娴嬭瘯澶瑰叿
    """

    def __len__(self) -> int:
        """
        杩斿洖娴嬭瘯鏁版嵁闀垮害
        """
        return 2

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        杩斿洖鍗曚釜娴嬭瘯鏍锋湰
        """
        image = torch.zeros((1, 8, 8), dtype=torch.float32)
        return {
            "input_field": image.to(torch.complex64),
            "input_image": image,
            "degraded_image": image,
            "clean_image": image.clone(),
            "label": index,
            "category": "zero",
            "provenance": {"index": index},
        }


def _unit_model_config(*, phase_offset_reference: float = 0.0) -> OpticalBenchConfig:
    """
    Build the unit-test optical geometry shared by training tests.
    """
    return OpticalBenchConfig(
        wavelength=1.0,
        input_plane_pixel_size=1.0,
        slm1_pixel_size=1.0,
        slm2_pixel_size=1.0,
        camera_pixel_size=1.0,
        focal_length=1.0,
        input_array_resolution=(8, 8),
        slm1_resolution=(8, 8),
        slm2_resolution=(8, 8),
        camera_resolution=(8, 8),
        phase_mask_resolution=8,
        slm2_active_resolution=(8, 8),
        phase_offset_reference=phase_offset_reference,
    )


def _tiny_operating_point(
    tmp_path: Path,
    *,
    phase_offset_reference: float = 0.0,
) -> tuple[Path, OpticalBenchConfig]:
    """
    鏋勫缓璁粌娴嬭瘯鏁版嵁
    """
    basic = BasicConfig(project_root=tmp_path, run_name="characterized")
    geometry = _unit_model_config(phase_offset_reference=phase_offset_reference)
    characterization = CharacterizationConfig(
        basic=basic,
        model=geometry,
        focal_length_candidates=(geometry.focal_length,),
        phase_mask_resolution_candidates=(geometry.phase_mask_resolution,),
    )
    theoretical_budget = build_theoretical_resolution_budget(geometry)
    operating_point_path = tmp_path / "operating_point.json"
    write_operating_point(
        operating_point_path,
        basic=basic,
        model=geometry,
        characterization=characterization,
        theoretical_budget=theoretical_budget,
        selected_values={
            "selected_focal_length": geometry.focal_length,
            "selected_phase_mask_resolution": geometry.phase_mask_resolution,
            "selected_phase_offset_reference": geometry.phase_offset_reference,
        },
        source_config_path=tmp_path / "characterization_config.json",
        source_metrics_path=tmp_path / "characterization_metrics.csv",
    )
    return operating_point_path, geometry


def _training_config(
    tmp_path: Path,
    operating_point_path: Path,
    **overrides: object,
) -> TrainingConfig:
    """
    鏋勫缓璁粌娴嬭瘯鏁版嵁
    """
    values: dict[str, object] = {
        "basic": BasicConfig(
            project_root=tmp_path,
            run_name="train_tiny",
            device="cpu",
            seed=7,
        ),
        "operating_point_path": operating_point_path,
        "train_dataset_config": {"kind": "tiny"},
        "val_dataset_config": {"kind": "tiny"},
        "epochs": 1,
        "batch_size": 2,
        "learning_rate": 1e-3,
    }
    values.update(overrides)
    return TrainingConfig(**values)  # type: ignore[arg-type]


def _assemble_training_model(
    config: TrainingConfig,
    geometry: OpticalBenchConfig,
    *,
    defocus_operator: object | None = None,
) -> torch.nn.Module:
    return model_assembly.assemble_model(
        model_role=config.model_role,
        bench_config=geometry,
        phase_parameterization=config.phase_parameterization,
        phase_initialization=config.phase_initialization,
        trainable_parameters=config.trainable_parameters,
        backend=config.backend,
        connection_config=config.connection,
        defocus_operator=defocus_operator,
    )


def _stub_training_figure_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Replace training figures when a test only cares about path contracts.
    """
    figure_check_stub = lambda *args, **kwargs: {
        "name": "figures_written",
        "status": "PASS",
        "details": {"skipped": "path_contract_test"},
    }
    monkeypatch.setattr(
        training, "_write_training_diagnostic_figures", figure_check_stub
    )


def _frontend_source_config(
    checkpoint_path: Path,
    *,
    config_hash: str = "source-config-hash",
    geometry_hash: str = "source-geometry-hash",
    degradation_hash: str = "source-degradation-hash",
) -> FrontendSourceConfig:
    """
    鎻愪緵娴嬭瘯杈呭姪閫昏緫
    """
    return FrontendSourceConfig(
        checkpoint_path=checkpoint_path,
        run_id="frontend-run",
        source_config_hash=config_hash,
        source_geometry_hash=geometry_hash,
        source_degradation_hash=degradation_hash,
    )


def _write_frontend_source_checkpoint(
    path: Path,
    geometry: OpticalBenchConfig,
    *,
    config_hash: str,
    geometry_hash: str,
    degradation_hash: str,
    fill_value: float = 0.25,
    phase_offset_reference: float | None = None,
) -> None:
    """
    鎻愪緵娴嬭瘯杈呭姪閫昏緫
    """
    frontend = RestorationFrontend(geometry)
    with torch.no_grad():
        frontend.phase_mask_fourier.fill_(fill_value)
        if phase_offset_reference is not None:
            frontend.phase_offset_reference.data.fill_(phase_offset_reference)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "config_hash": config_hash,
            "geometry_hash": geometry_hash,
            "degradation_hash": degradation_hash,
            "model_role": "frontend_only",
            "backend": None,
            "model_state_dict": frontend.state_dict(),
        },
        path,
    )


def _defocus_dataset_config(radius: int = 6) -> RestorationDataConfig:
    """
    Build a JSON-serializable dataset config carrying a defocus degradation op.
    """
    return RestorationDataConfig(
        source=SourceConfig(dataset_name="tiny"),
        perturbation=PerturbationConfig(operations=(DefocusBlurConfig(radius=radius),)),
    )


def test_run_training_records_defocus_operator_provenance_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Training records the operator provenance hash derived from the defocus config.
    """
    radius = 6
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    dataset_config = _defocus_dataset_config(radius)

    result = run_training(
        _training_config(
            tmp_path,
            operating_point_path,
            train_dataset_config=dataset_config,
            val_dataset_config=dataset_config,
        )
    )

    final_metrics = json.loads(
        Path(result["paths"]["final_metrics_json"]).read_text(encoding="utf-8")
    )
    assert final_metrics["defocus_operator_provenance_hash"] == compute_config_hash(
        DefocusBlurConfig(radius=radius)
    )
    assert final_metrics["reference_phase_offset"] is None


def test_run_training_records_live_reference_phase_offset_for_hybrid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Hybrid training records the LIVE loaded reference phase offset, not the static default.
    """

    class _TinyBackend(torch.nn.Module):
        def __init__(self, config: BackendConfig) -> None:
            super().__init__()
            self.config = config
            self.weight = torch.nn.Parameter(torch.tensor(0.5))

        def forward(self, image: torch.Tensor) -> torch.Tensor:
            return torch.clamp(image * self.weight, 0.0, 1.0)

    def _build_backend(config: BackendConfig, **kwargs: object) -> _TinyBackend:
        del kwargs
        return _TinyBackend(config)

    live_phase_offset = 0.6125
    operating_point_path, geometry = _tiny_operating_point(tmp_path)
    assert geometry.phase_offset_reference == 0.0
    geometry_hash = compute_config_hash(geometry)
    source_config_hash = "source-config-hash"
    source_degradation_hash = training._degradation_hash_for_training_config(
        _training_config(tmp_path, operating_point_path)
    )
    frontend_checkpoint = tmp_path / "frontend_source.pt"
    _write_frontend_source_checkpoint(
        frontend_checkpoint,
        geometry,
        config_hash=source_config_hash,
        geometry_hash=geometry_hash,
        degradation_hash=source_degradation_hash,
        phase_offset_reference=live_phase_offset,
    )
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    monkeypatch.setattr(
        model_assembly,
        "build_restoration_backend",
        _build_backend,
    )
    _stub_training_figure_check(monkeypatch)

    result = run_training(
        _training_config(
            tmp_path,
            operating_point_path,
            model_role="frozen_optical_frontend_digital_backend",
            trainable_parameters=("backend",),
            frontend_source=_frontend_source_config(
                frontend_checkpoint,
                config_hash=source_config_hash,
                geometry_hash=geometry_hash,
                degradation_hash=source_degradation_hash,
            ),
        )
    )

    final_metrics = json.loads(
        Path(result["paths"]["final_metrics_json"]).read_text(encoding="utf-8")
    )
    assert final_metrics["reference_phase_offset"] == pytest.approx(live_phase_offset)
    assert final_metrics["reference_phase_offset"] != geometry.phase_offset_reference


def test_run_training_injects_live_reference_arm_into_backend_for_hybrid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Post-load injection hands the LIVE checkpoint reference phase to the backend.
    """

    class _StubBackend(torch.nn.Module):
        def __init__(self, config: BackendConfig) -> None:
            super().__init__()
            self.config = config
            self.weight = torch.nn.Parameter(torch.tensor(0.5))
            self.received_reference_arm = None

        def set_reference_arm(self, reference_arm: object) -> None:
            """
            淇濆瓨璁粌娉ㄥ叆鐨勫弬鑰冭噦
            """
            self.received_reference_arm = reference_arm

        def forward(self, image: torch.Tensor) -> torch.Tensor:
            return torch.clamp(image * self.weight, 0.0, 1.0)

    created_backends: list[_StubBackend] = []
    live_phase_offset = 0.6125
    operating_point_path, geometry = _tiny_operating_point(tmp_path)
    assert geometry.phase_offset_reference == 0.0
    geometry_hash = compute_config_hash(geometry)
    source_config_hash = "source-config-hash"
    source_degradation_hash = training._degradation_hash_for_training_config(
        _training_config(tmp_path, operating_point_path)
    )
    frontend_checkpoint = tmp_path / "frontend_source.pt"
    _write_frontend_source_checkpoint(
        frontend_checkpoint,
        geometry,
        config_hash=source_config_hash,
        geometry_hash=geometry_hash,
        degradation_hash=source_degradation_hash,
        phase_offset_reference=live_phase_offset,
    )
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )

    def _build_stub(config: BackendConfig, **kwargs: object) -> _StubBackend:
        backend = _StubBackend(config)
        created_backends.append(backend)
        return backend

    monkeypatch.setattr(model_assembly, "build_restoration_backend", _build_stub)
    _stub_training_figure_check(monkeypatch)

    run_training(
        _training_config(
            tmp_path,
            operating_point_path,
            model_role="frozen_optical_frontend_digital_backend",
            trainable_parameters=("backend",),
            frontend_source=_frontend_source_config(
                frontend_checkpoint,
                config_hash=source_config_hash,
                geometry_hash=geometry_hash,
                degradation_hash=source_degradation_hash,
            ),
        )
    )

    assert len(created_backends) == 1
    injected = created_backends[0].received_reference_arm
    assert injected is not None
    assert injected.phase_offset() == pytest.approx(live_phase_offset)
    assert injected.phase_offset() != geometry.phase_offset_reference


def test_run_training_writes_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )

    result = run_training(_training_config(tmp_path, operating_point_path))

    assert result["status"] in {"PASS", "WARN"}
    paths = result["paths"]
    assert paths["run_dir"] == (
        tmp_path
        / "results"
        / "restoration"
        / "training"
        / "frontend_only"
        / "train_tiny"
    )
    for key in (
        "epoch_metrics_csv",
        "final_metrics_json",
        "best_checkpoint",
        "last_checkpoint",
        "operating_point_used_json",
        "checks_json",
        "summary_md",
    ):
        assert paths[key].exists(), key
    checkpoint = torch.load(paths["last_checkpoint"], map_location="cpu")
    assert checkpoint["model_role"] == "frontend_only"
    assert checkpoint["backend"] is None
    assert "backend_family" not in checkpoint
    assert "backend_model" not in checkpoint
    assert checkpoint["connection"] == {
        "mode": "serial",
    }
    assert isinstance(checkpoint["degradation_hash"], str)
    assert checkpoint["degradation_hash"]
    assert paths["phase_masks_dir"].is_dir()


def test_run_training_accepts_fixed_measurement_artifact_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉璁粌鎺ュ彈鍥哄畾娴嬮噺浜х墿璺緞
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    _stub_training_figure_check(monkeypatch)
    training_config = _training_config(tmp_path, operating_point_path)
    study = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=training_config.basic.seed,
        project_root=tmp_path,
        configuration=training_config,
    )
    artifacts = build_study_artifacts(study, project_root=tmp_path)

    result = run_training(
        training_config,
        artifact_paths=artifacts.as_training_paths(),
        is_resume=False,
    )

    assert result["paths"]["run_dir"] == artifacts.run_dir
    assert artifacts.final_metrics_json.is_file()


def test_run_training_resumes_incomplete_fixed_measurement_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉璁粌浠庢湭瀹屾垚鍥哄畾娴嬮噺杩愯鎭㈠
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    _stub_training_figure_check(monkeypatch)
    training_config = _training_config(
        tmp_path,
        operating_point_path,
        epochs=2,
    )
    study = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=training_config.basic.seed,
        project_root=tmp_path,
        configuration=training_config,
    )
    artifacts = build_study_artifacts(study, project_root=tmp_path)
    original_run_epoch = training.run_epoch

    def interrupt_before_second_epoch(*args: object, **kwargs: object) -> object:
        """
        鍦ㄧ浜岃疆璁粌鍓嶆ā鎷熶腑鏂?        """
        if kwargs.get("epoch") == 2 and kwargs.get("split") == "train":
            raise RuntimeError(_SIMULATED_INTERRUPTION)
        return original_run_epoch(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(training, "run_epoch", interrupt_before_second_epoch)
    with pytest.raises(RuntimeError, match=_SIMULATED_INTERRUPTION):
        run_training(
            training_config,
            artifact_paths=artifacts.as_training_paths(),
            is_resume=False,
        )

    checkpoint = torch.load(artifacts.last_checkpoint, map_location="cpu")
    assert checkpoint["epoch"] == 1

    monkeypatch.setattr(training, "run_epoch", original_run_epoch)
    result = run_training(
        training_config,
        artifact_paths=artifacts.as_training_paths(),
        is_resume=True,
    )

    with artifacts.epoch_metrics_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [(row["epoch"], row["split"]) for row in rows] == [
        ("1.0", "train"),
        ("1.0", "val"),
        ("2.0", "train"),
        ("2.0", "val"),
    ]
    assert result["final_metrics"]["best_epoch"] in {1, 2}


def test_run_training_restores_partial_effective_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Resume preserves both pending sample count and gradients across epochs.
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(sample_count=10),
    )
    _stub_training_figure_check(monkeypatch)
    training_config = _training_config(
        tmp_path,
        operating_point_path,
        batch_size=2,
        effective_batch_size=8,
        max_optimizer_updates=3,
    )
    study = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=training_config.basic.seed,
        project_root=tmp_path,
        configuration=training_config,
    )
    artifacts = build_study_artifacts(study, project_root=tmp_path)
    original_run_epoch = training.run_epoch

    def interrupt_before_second_epoch(*args: object, **kwargs: object) -> object:
        if kwargs.get("epoch") == 2 and kwargs.get("split") == "train":
            raise RuntimeError(_SIMULATED_INTERRUPTION)
        return original_run_epoch(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(training, "run_epoch", interrupt_before_second_epoch)
    with pytest.raises(RuntimeError, match=_SIMULATED_INTERRUPTION):
        run_training(
            training_config,
            artifact_paths=artifacts.as_training_paths(),
            is_resume=False,
        )

    interrupted_checkpoint = torch.load(
        artifacts.last_checkpoint,
        map_location="cpu",
        weights_only=True,
    )
    assert interrupted_checkpoint["gradient_accumulation"]["pending_samples"] == 2
    assert interrupted_checkpoint["gradient_accumulation"]["parameter_gradients"]

    monkeypatch.setattr(training, "run_epoch", original_run_epoch)
    result = run_training(
        training_config,
        artifact_paths=artifacts.as_training_paths(),
        is_resume=True,
    )

    completed_checkpoint = torch.load(
        artifacts.last_checkpoint,
        map_location="cpu",
        weights_only=True,
    )
    assert result["final_metrics"]["optimizer_updates"] == 3
    assert completed_checkpoint["gradient_accumulation"]["pending_samples"] == 0


def test_run_training_restarts_when_no_epoch_was_committed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉棣栨妫€鏌ョ偣鍓嶄腑鏂殑杩愯鍙互鍦ㄥ師鐩綍鍙潬閲嶅惎
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    _stub_training_figure_check(monkeypatch)
    training_config = _training_config(tmp_path, operating_point_path)
    study = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=training_config.basic.seed,
        project_root=tmp_path,
        configuration=training_config,
    )
    artifacts = build_study_artifacts(study, project_root=tmp_path)
    artifacts.run_dir.mkdir(parents=True)
    artifacts.epoch_metrics_csv.write_text("uncommitted\n", encoding="utf-8")

    result = run_training(
        training_config,
        artifact_paths=artifacts.as_training_paths(),
        is_resume=True,
    )

    checks = {check["name"]: check for check in result["checks"]}
    assert checks["training_restarted"]["status"] == "PASS"
    assert artifacts.last_checkpoint.is_file()
    with artifacts.epoch_metrics_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [(row["epoch"], row["split"]) for row in rows] == [
        ("1.0", "train"),
        ("1.0", "val"),
    ]


def test_run_training_discards_metrics_newer_than_last_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉鎭㈠鏃朵互鍘熷瓙妫€鏌ョ偣涓哄噯涓㈠純灏氭湭鎻愪氦鐨勮疆娆℃寚鏍?    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    _stub_training_figure_check(monkeypatch)
    training_config = _training_config(
        tmp_path,
        operating_point_path,
        epochs=2,
    )
    study = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=training_config.basic.seed,
        project_root=tmp_path,
        configuration=training_config,
    )
    artifacts = build_study_artifacts(study, project_root=tmp_path)
    original_append = training.append_training_epoch_metrics

    def interrupt_after_second_epoch(
        path: Path,
        rows: object,
    ) -> Path:
        """
        鍦ㄧ浜岃疆鎸囨爣钀界洏鑰屾鏌ョ偣灏氭湭鎻愪氦鏃舵ā鎷熶腑鏂?        """
        materialized_rows = tuple(rows)  # type: ignore[arg-type]
        output_path = original_append(path, materialized_rows)
        if any(
            int(row["epoch"]) == 2 and row["split"] == "val"
            for row in materialized_rows
        ):
            raise RuntimeError(_SIMULATED_INTERRUPTION)
        return output_path

    monkeypatch.setattr(
        training,
        "append_training_epoch_metrics",
        interrupt_after_second_epoch,
    )
    with pytest.raises(RuntimeError, match=_SIMULATED_INTERRUPTION):
        run_training(
            training_config,
            artifact_paths=artifacts.as_training_paths(),
            is_resume=False,
        )

    checkpoint = torch.load(artifacts.last_checkpoint, map_location="cpu")
    assert checkpoint["epoch"] == 1

    monkeypatch.setattr(
        training,
        "append_training_epoch_metrics",
        original_append,
    )
    run_training(
        training_config,
        artifact_paths=artifacts.as_training_paths(),
        is_resume=True,
    )

    with artifacts.epoch_metrics_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [(row["epoch"], row["split"]) for row in rows] == [
        ("1.0", "train"),
        ("1.0", "val"),
        ("2.0", "train"),
        ("2.0", "val"),
    ]


def test_run_training_checkpoints_include_degradation_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )

    result = run_training(_training_config(tmp_path, operating_point_path))

    best_checkpoint = torch.load(result["paths"]["best_checkpoint"], map_location="cpu")
    last_checkpoint = torch.load(result["paths"]["last_checkpoint"], map_location="cpu")
    expected_hash = training._degradation_hash_for_training_config(
        _training_config(tmp_path, operating_point_path)
    )
    assert best_checkpoint["degradation_hash"] == expected_hash
    assert last_checkpoint["degradation_hash"] == expected_hash


def test_degradation_hash_for_training_config_accepts_matching_train_val() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    train_config = build_standard_dataset_config(
        profile_name="medium",
        split="train",
        split_manifest={"records": []},
    )
    val_config = build_standard_dataset_config(
        profile_name="medium",
        split="val",
        split_manifest={"records": []},
    )
    config = TrainingConfig(
        train_dataset_config=train_config,
        val_dataset_config=val_config,
    )

    assert training._degradation_hash_for_training_config(
        config
    ) == degradation_hash_for_dataset_config(train_config)


def test_degradation_hash_for_training_config_rejects_train_val_mismatch() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    train_config = build_standard_dataset_config(
        profile_name="medium",
        split="train",
        split_manifest={"records": []},
    )
    val_config = build_standard_dataset_config(
        profile_name="heavy",
        split="val",
        split_manifest={"records": []},
    )
    config = TrainingConfig(
        train_dataset_config=train_config,
        val_dataset_config=val_config,
    )

    with pytest.raises(ValueError, match="train_dataset_config.*val_dataset_config"):
        training._degradation_hash_for_training_config(config)


def test_backend_only_training_uses_backend_role_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """

    class _TinyBackend(torch.nn.Module):
        """
        鎻愪緵璁粌娴嬭瘯澶瑰叿
        """

        def __init__(self, config: BackendConfig) -> None:
            """
            鎸傝浇鍚庣閰嶇疆鍜屾潈閲?            """
            super().__init__()
            self.config = config
            self.weight = torch.nn.Parameter(torch.tensor(0.5))

        def forward(self, image: torch.Tensor) -> torch.Tensor:
            """
            鎵ц璁粌鍓嶅悜浼犳挱
            """
            return torch.clamp(image * self.weight, 0.0, 1.0)

    def _build_backend(config: BackendConfig, **kwargs: object) -> _TinyBackend:
        del kwargs
        return _TinyBackend(config)

    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    monkeypatch.setattr(
        model_assembly,
        "build_restoration_backend",
        _build_backend,
    )
    stat_calls = {"parameters": 0, "macs": 0}

    def count_parameters(model: torch.nn.Module) -> int:
        """
        Return a fixed parameter count for backend path assertions.
        """
        stat_calls["parameters"] += 1
        return 123

    def count_macs(model: torch.nn.Module, example_input: torch.Tensor) -> int:
        """
        Return a fixed MAC count after checking the example input.
        """
        stat_calls["macs"] += 1
        assert tuple(example_input.shape) == (1, 1, 8, 8)
        return 456

    monkeypatch.setattr(training, "count_trainable_parameters", count_parameters)
    monkeypatch.setattr(training, "count_model_macs", count_macs)

    result = run_training(
        _training_config(
            tmp_path,
            operating_point_path,
            model_role="backend_only",
            trainable_parameters=("backend",),
        )
    )

    assert result["status"] == "PASS"
    paths = result["paths"]
    assert paths["run_dir"] == (
        tmp_path
        / "results"
        / "restoration"
        / "training"
        / "backend_only"
        / "restoration_native"
        / "nafnet_s"
        / "train_tiny"
    )
    checks = {check["name"]: check for check in result["checks"]}
    assert checks["trainable_parameters_exact"]["details"]["actual"] == ["backend"]
    assert checks["figures_written"]["status"] == "PASS"
    final_metrics = result["final_metrics"]
    assert final_metrics["phase_mask_stats"]["status"] == "not_applicable"
    assert final_metrics["model_role"] == "backend_only"
    assert final_metrics["backend"] == {
        "family": "restoration_native",
        "model_name": "nafnet_s",
        "residual_learning": True,
    }
    assert "backend_family" not in final_metrics
    assert "backend_model" not in final_metrics
    final_metrics_json = json.loads(
        paths["final_metrics_json"].read_text(encoding="utf-8")
    )
    assert final_metrics_json["backend"] == final_metrics["backend"]
    assert "backend_family" not in final_metrics_json
    assert "backend_model" not in final_metrics_json
    assert final_metrics["model_parameter_count"] == 123
    assert final_metrics["model_conv2d_macs"] == 456
    assert stat_calls == {"parameters": 1, "macs": 1}
    checkpoint = torch.load(paths["last_checkpoint"], map_location="cpu")
    assert checkpoint["model_role"] == "backend_only"
    assert checkpoint["backend"] == {
        "family": "restoration_native",
        "model_name": "nafnet_s",
        "residual_learning": True,
    }
    assert "backend_family" not in checkpoint
    assert "backend_model" not in checkpoint
    assert "weight" in checkpoint["model_state_dict"]


def test_optical_residual_gate_records_curve_and_final_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉鐩撮€氬鐩婂悓鏃惰繘鍏ヨ疆娆℃洸绾垮拰鏈€缁堟満鍒惰瘉鎹?    """
    operating_point_path, geometry = _tiny_operating_point(tmp_path)
    geometry_hash = compute_config_hash(geometry)
    source_config_hash = "source-config-hash"
    source_degradation_hash = training._degradation_hash_for_training_config(
        _training_config(tmp_path, operating_point_path)
    )
    frontend_checkpoint = tmp_path / "frontend_source.pt"
    _write_frontend_source_checkpoint(
        frontend_checkpoint,
        geometry,
        config_hash=source_config_hash,
        geometry_hash=geometry_hash,
        degradation_hash=source_degradation_hash,
    )
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    _stub_training_figure_check(monkeypatch)
    result = run_training(
        _training_config(
            tmp_path,
            operating_point_path,
            model_role="frozen_optical_frontend_digital_backend",
            trainable_parameters=("connection", "backend"),
            backend=BackendConfig(model_name="nafnet_s"),
            connection=ConnectionConfig.with_optical_residual_gate(
                initial_gate=0.99,
            ),
            frontend_source=_frontend_source_config(
                frontend_checkpoint,
                config_hash=source_config_hash,
                geometry_hash=geometry_hash,
                degradation_hash=source_degradation_hash,
            ),
        )
    )

    assert result["status"] == "PASS"
    history = result["history"]
    assert all(row["optical_residual_gate"] is not None for row in history)
    final_metrics = result["final_metrics"]
    assert final_metrics["mechanism_parameters"][
        "optical_residual_gate"
    ] == pytest.approx(final_metrics["final_optical_residual_gate"])
    assert final_metrics["best_optical_residual_gate"] is not None


def test_joint_hybrid_training_uses_hybrid_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """

    class _TinyBackend(torch.nn.Module):
        """
        鎻愪緵璁粌娴嬭瘯澶瑰叿
        """

        def __init__(self, config: BackendConfig) -> None:
            """
            鎸傝浇鍚庣閰嶇疆鍜屾潈閲?            """
            super().__init__()
            self.config = config
            self.weight = torch.nn.Parameter(torch.tensor(0.5))

        def forward(self, image: torch.Tensor) -> torch.Tensor:
            """
            鎵ц璁粌鍓嶅悜浼犳挱
            """
            return torch.clamp(image * self.weight, 0.0, 1.0)

    def _build_backend(config: BackendConfig, **kwargs: object) -> _TinyBackend:
        del kwargs
        return _TinyBackend(config)

    operating_point_path, geometry = _tiny_operating_point(tmp_path)
    geometry_hash = compute_config_hash(geometry)
    source_config_hash = "source-config-hash"
    source_degradation_hash = training._degradation_hash_for_training_config(
        _training_config(tmp_path, operating_point_path)
    )
    frontend_checkpoint = tmp_path / "frontend_source.pt"
    _write_frontend_source_checkpoint(
        frontend_checkpoint,
        geometry,
        config_hash=source_config_hash,
        geometry_hash=geometry_hash,
        degradation_hash=source_degradation_hash,
    )
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    monkeypatch.setattr(
        model_assembly,
        "build_restoration_backend",
        _build_backend,
    )
    _stub_training_figure_check(monkeypatch)

    result = run_training(
        _training_config(
            tmp_path,
            operating_point_path,
            model_role="joint_optical_frontend_digital_backend",
            trainable_parameters=("phase_mask_fourier", "backend"),
            frontend_source=_frontend_source_config(
                frontend_checkpoint,
                config_hash=source_config_hash,
                geometry_hash=geometry_hash,
                degradation_hash=source_degradation_hash,
            ),
        )
    )

    assert result["status"] == "PASS"
    paths = result["paths"]
    assert paths["run_dir"] == (
        tmp_path
        / "results"
        / "restoration"
        / "training"
        / "hybrid"
        / "joint_optical_frontend_digital_backend"
        / "restoration_native"
        / "nafnet_s"
        / "train_tiny"
    )
    checks = {check["name"]: check for check in result["checks"]}
    assert checks["trainable_parameters_exact"]["details"]["actual"] == [
        "phase_mask_fourier",
        "backend",
    ]
    checkpoint = torch.load(paths["last_checkpoint"], map_location="cpu")
    assert checkpoint["model_role"] == "joint_optical_frontend_digital_backend"
    assert checkpoint["backend"] == {
        "family": "restoration_native",
        "model_name": "nafnet_s",
        "residual_learning": True,
    }
    assert "frontend.phase_mask_fourier" in checkpoint["model_state_dict"]
    assert "backend.weight" in checkpoint["model_state_dict"]
    assert torch.allclose(
        checkpoint["model_state_dict"]["frontend.phase_mask_fourier"],
        torch.full_like(
            checkpoint["model_state_dict"]["frontend.phase_mask_fourier"],
            0.25,
        ),
        atol=1e-2,
    )


def test_build_trainable_hybrid_uses_configured_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Hybrid training builds and trains the configured connection module.
    """

    class _RecordingBackend(torch.nn.Module):
        """
        Capture backend input for configured connection assertions.
        """

        def __init__(self) -> None:
            """
            Install a backend parameter to keep backend trainability observable.
            """
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(1.0))
            self.last_input: torch.Tensor | None = None

        def forward(self, image: torch.Tensor) -> torch.Tensor:
            """
            Echo and capture the backend input.
            """
            self.last_input = image.detach().clone()
            return image * self.weight

    backend = _RecordingBackend()

    def _build_backend(config: object, **kwargs: object) -> _RecordingBackend:
        del config, kwargs
        return backend

    monkeypatch.setattr(
        model_assembly,
        "build_restoration_backend",
        _build_backend,
    )
    config = _training_config(
        tmp_path,
        tmp_path / "operating_point.json",
        model_role="joint_optical_frontend_digital_backend",
        trainable_parameters=("phase_mask_fourier", "connection", "backend"),
        connection=ConnectionConfig.with_optical_residual_gate(
            initial_gate=0.75,
        ),
        frontend_source=_frontend_source_config(tmp_path / "frontend.pt"),
    )
    model = _assemble_training_model(config, _unit_model_config())
    field = torch.full((1, 1, 8, 8), 0.5 + 0.0j, dtype=torch.complex64)

    output = model(field)

    assert output.shape == (1, 1, 8, 8)
    assert backend.last_input is not None
    degraded_image = field.abs().square().real
    optical_restoration_image = model.frontend(field).to(dtype=torch.float32)
    expected_input = degraded_image + 0.75 * (
        optical_restoration_image - degraded_image
    )
    assert torch.allclose(backend.last_input, expected_input)
    assert any(parameter.requires_grad for parameter in model.connection.parameters())
    assert model.trainable_parameter_names() == [
        "phase_mask_fourier",
        "connection",
        "backend",
    ]


def test_load_frontend_source_loads_checkpoint_into_hybrid_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """

    class _TinyBackend(torch.nn.Module):
        """
        鎻愪緵娴嬭瘯杈呭姪鏇胯韩
        """

        def forward(self, image: torch.Tensor) -> torch.Tensor:
            """
            鎻愪緵娴嬭瘯杈呭姪閫昏緫
            """
            return image

    def _build_backend(config: object, **kwargs: object) -> _TinyBackend:
        del config, kwargs
        return _TinyBackend()

    geometry = _unit_model_config()
    geometry_hash = compute_config_hash(geometry)
    degradation_hash = "target-degradation-hash"
    config_hash = "source-config-hash"
    checkpoint_path = tmp_path / "frontend_source.pt"
    _write_frontend_source_checkpoint(
        checkpoint_path,
        geometry,
        config_hash=config_hash,
        geometry_hash=geometry_hash,
        degradation_hash=degradation_hash,
        fill_value=0.75,
    )
    monkeypatch.setattr(
        model_assembly,
        "build_restoration_backend",
        _build_backend,
    )
    config = TrainingConfig(
        model_role="frozen_optical_frontend_digital_backend",
        trainable_parameters=("backend",),
        frontend_source=_frontend_source_config(
            checkpoint_path,
            config_hash=config_hash,
            geometry_hash=geometry_hash,
            degradation_hash=degradation_hash,
        ),
    )
    model = _assemble_training_model(config, geometry)

    checkpoints.load_frontend_source_if_needed(
        model,
        config,
        geometry_hash=geometry_hash,
        target_degradation_hash=degradation_hash,
    )

    assert torch.allclose(
        model.frontend.phase_mask_fourier,
        torch.full_like(model.frontend.phase_mask_fourier, 0.75),
    )


def test_load_frontend_source_rejects_target_degradation_hash_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """

    class _TinyBackend(torch.nn.Module):
        """
        鎻愪緵娴嬭瘯杈呭姪鏇胯韩
        """

        def forward(self, image: torch.Tensor) -> torch.Tensor:
            """
            鎻愪緵娴嬭瘯杈呭姪閫昏緫
            """
            return image

    def _build_backend(config: object, **kwargs: object) -> _TinyBackend:
        del config, kwargs
        return _TinyBackend()

    geometry = _unit_model_config()
    geometry_hash = compute_config_hash(geometry)
    config_hash = "source-config-hash"
    checkpoint_path = tmp_path / "frontend_source.pt"
    _write_frontend_source_checkpoint(
        checkpoint_path,
        geometry,
        config_hash=config_hash,
        geometry_hash=geometry_hash,
        degradation_hash="source-degradation-hash",
    )
    monkeypatch.setattr(
        model_assembly,
        "build_restoration_backend",
        _build_backend,
    )
    config = TrainingConfig(
        model_role="joint_optical_frontend_digital_backend",
        trainable_parameters=("phase_mask_fourier", "backend"),
        frontend_source=_frontend_source_config(
            checkpoint_path,
            config_hash=config_hash,
            geometry_hash=geometry_hash,
            degradation_hash="source-degradation-hash",
        ),
    )
    model = _assemble_training_model(config, geometry)

    with pytest.raises(ValueError, match="source_vs_target_degradation_hash"):
        checkpoints.load_frontend_source_if_needed(
            model,
            config,
            geometry_hash=geometry_hash,
            target_degradation_hash="target-degradation-hash",
        )


def test_training_freezes_geometry_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """
    operating_point_path, geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )

    result = run_training(_training_config(tmp_path, operating_point_path))

    checks = {check["name"]: check for check in result["checks"]}
    assert checks["geometry_hash_matches"]["status"] == "PASS"
    used_payload = json.loads(
        result["paths"]["operating_point_used_json"].read_text(encoding="utf-8")
    )
    original_payload = json.loads(operating_point_path.read_text(encoding="utf-8"))
    assert used_payload["geometry_hash"] == original_payload["geometry_hash"]
    assert used_payload["geometry_hash"] == compute_config_hash(geometry)


def test_training_contract_metrics_and_trainable_parameters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )

    result = run_training(_training_config(tmp_path, operating_point_path))

    checks = {check["name"]: check for check in result["checks"]}
    assert checks["trainable_parameters_exact"]["status"] == "PASS"
    assert checks["trainable_parameters_exact"]["details"]["actual"] == [
        "phase_mask_fourier"
    ]

    with result["paths"]["epoch_metrics_csv"].open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert {row["split"] for row in rows} == {"train", "val"}
    for field in (
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
    ):
        assert all(row[field] != "" for row in rows), field

    final_metrics = json.loads(
        result["paths"]["final_metrics_json"].read_text(encoding="utf-8")
    )
    assert {
        "best_val_loss",
        "best_epoch",
        "best_val_ssim",
        "best_val_psnr",
        "final_train_loss",
        "final_val_loss",
        "phase_zero_vs_clean_psnr",
        "trained_vs_clean_psnr",
        "trained_minus_phase_zero_psnr",
    }.issubset(final_metrics)


def test_training_uses_effective_batch_and_exact_optimizer_update_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉璁粌涓ユ牸閬靛畧鏈夋晥鎵归噺鍜屼紭鍖栧櫒鏇存柊鏁伴绠?    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(sample_count=4),
    )
    _stub_training_figure_check(monkeypatch)

    result = run_training(
        _training_config(
            tmp_path,
            operating_point_path,
            epochs=1,
            batch_size=2,
            effective_batch_size=4,
            max_optimizer_updates=3,
        )
    )

    assert result["status"] == "PASS"
    assert result["final_metrics"]["optimizer_updates"] == 3
    assert result["final_metrics"]["effective_batch_size"] == 4
    train_rows = [row for row in result["history"] if row["split"] == "train"]
    assert [row["optimizer_updates"] for row in train_rows] == [1, 2, 3]


def test_training_aborts_before_training_when_geometry_hash_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    payload = json.loads(operating_point_path.read_text(encoding="utf-8"))
    payload["geometry_hash"] = "corrupted-hash"
    operating_point_path.write_text(json.dumps(payload), encoding="utf-8")

    def fail_if_dataset_is_built(config: object) -> None:
        """
        妯℃嫙璁粌娴嬭瘯鍦烘櫙
        """
        raise AssertionError(
            "dataset should not be built when geometry hash mismatches"
        )

    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        fail_if_dataset_is_built,
    )

    result = run_training(_training_config(tmp_path, operating_point_path))

    checks = {check["name"]: check for check in result["checks"]}
    assert result["status"] == "FAIL"
    assert checks["geometry_hash_matches"]["status"] == "FAIL"
    assert result["paths"]["operating_point_used_json"].exists()
    assert result["paths"]["checks_json"].exists()
    assert result["paths"]["summary_md"].exists()
    assert not result["paths"]["best_checkpoint"].exists()
    assert not result["paths"]["last_checkpoint"].exists()


def test_training_sanitizes_non_finite_metrics_for_json_and_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedZeroDataset(),
    )

    result = run_training(_training_config(tmp_path, operating_point_path))

    metrics_text = result["paths"]["final_metrics_json"].read_text(encoding="utf-8")
    assert "Infinity" not in metrics_text
    final_metrics = json.loads(metrics_text)
    assert final_metrics["best_val_psnr"] == "inf"

    csv_text = result["paths"]["epoch_metrics_csv"].read_text(encoding="utf-8")
    assert "inf" in csv_text
    assert "Infinity" not in csv_text


def test_training_updates_phase_mask_parameter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )

    result = run_training(_training_config(tmp_path, operating_point_path))

    checkpoint = torch.load(result["paths"]["last_checkpoint"], map_location="cpu")
    phase_mask = checkpoint["model_state_dict"]["phase_mask_fourier"]
    assert not torch.allclose(phase_mask, torch.zeros_like(phase_mask))


def test_training_can_update_reference_phase_offset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Validate training can update the reference phase offset.
    """
    operating_point_path, _geometry = _tiny_operating_point(
        tmp_path,
        phase_offset_reference=0.5,
    )
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )

    result = run_training(
        _training_config(
            tmp_path,
            operating_point_path,
            learning_rate=1e-2,
            trainable_parameters=("phase_mask_fourier", "phase_offset_reference"),
        )
    )

    checks = {check["name"]: check for check in result["checks"]}
    assert checks["trainable_parameters_exact"]["details"]["actual"] == [
        "phase_mask_fourier",
        "phase_offset_reference",
    ]
    checkpoint = torch.load(result["paths"]["last_checkpoint"], map_location="cpu")
    phase_offset = checkpoint["model_state_dict"]["phase_offset_reference"]
    assert phase_offset.ndim == 0
    assert not torch.allclose(phase_offset, torch.tensor(0.5))

    with result["paths"]["epoch_metrics_csv"].open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows[-1]["phase_offset_reference"] != "0.5"


def test_run_training_writes_diagnostic_figures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )

    result = run_training(_training_config(tmp_path, operating_point_path))

    figures_dir = result["paths"]["figures_dir"]
    for stem in (
        "01_training_dynamics",
        "02_restoration_examples",
        "03_phase_mask_evolution",
        "04_frequency_response_comparison",
        "05_operating_point_trace",
    ):
        assert (figures_dir / f"{stem}.png").exists(), stem
        assert (figures_dir / f"{stem}.svg").exists(), stem

    checks = {check["name"]: check for check in result["checks"]}
    assert checks["figures_written"]["status"] == "PASS"


def test_run_training_fails_figure_check_when_generation_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙璁粌濂戠害
    """
    operating_point_path, _geometry = _tiny_operating_point(tmp_path)
    config = _training_config(tmp_path, operating_point_path)
    figures_dir = (
        tmp_path
        / "results"
        / "restoration"
        / "training"
        / "frontend_only"
        / config.basic.run_name
        / "figures"
    )
    figures_dir.mkdir(parents=True)
    for stem in (
        "01_training_dynamics.png",
        "02_restoration_examples.png",
        "03_phase_mask_evolution.png",
        "04_frequency_response_comparison.png",
        "05_operating_point_trace.png",
    ):
        (figures_dir / stem).write_bytes(b"stale")

    def fail_visualization(*args: object, **kwargs: object) -> None:
        """
        妯℃嫙璁粌娴嬭瘯鍦烘櫙
        """
        raise RuntimeError("figure writer failed")

    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.data_loading.build_restoration_dataset",
        lambda config: _EncodedTinyDataset(),
    )
    monkeypatch.setattr(
        "experiments.restoration.fixed_measurement.learning.training.visualize_training_dynamics",
        fail_visualization,
    )

    result = run_training(config)

    checks = {check["name"]: check for check in result["checks"]}
    assert result["status"] == "FAIL"
    assert checks["figures_written"]["status"] == "FAIL"
    assert "figure writer failed" in checks["figures_written"]["details"]["error"]
    assert "01_training_dynamics.svg" in checks["figures_written"]["details"]["missing"]


def test_collect_restoration_examples_prefers_degraded_image() -> None:
    """
    鏍￠獙璁粌绀轰緥閫€鍖栧浘鍍忓绾?    """

    class _ExampleFrontend(torch.nn.Module):
        """
        鎻愪緵璁粌绀轰緥鏀堕泦娴嬭瘯妯″瀷
        """

        def forward(self, input_field: torch.Tensor) -> torch.Tensor:
            """
            杩斿洖鍥哄畾褰㈢姸鐨勬仮澶嶅浘鍍?            """
            return input_field.abs().square().real

        def phase_zero_baselines(
            self, input_field: torch.Tensor
        ) -> dict[str, torch.Tensor]:
            """
            杩斿洖鍥哄畾褰㈢姸鐨勯浂鐩镐綅鍩虹嚎
            """
            return {"image_full_frontend_phase_zero": input_field.abs().square().real}

    clean_image = torch.full((1, 1, 2, 2), 0.9, dtype=torch.float32)
    degraded_image = torch.full((1, 1, 2, 2), 0.7, dtype=torch.float32)
    input_image = torch.full((1, 1, 2, 2), 0.2, dtype=torch.float32)
    batch = {
        "input_field": input_image.to(torch.complex64),
        "input_image": input_image,
        "degraded_image": degraded_image,
        "clean_image": clean_image,
    }

    examples = training._collect_restoration_examples(
        _ExampleFrontend(),
        [batch],  # type: ignore[arg-type]
        TrainingConfig(intensity_normalization_policy="fixed_dataset_level"),
        torch.device("cpu"),
    )

    assert torch.equal(examples["degraded"], degraded_image)


def test_target_from_batch_rejects_missing_clean_image() -> None:
    """
    鏍￠獙璁粌濂戠害
    """
    input_image = torch.ones((2, 1, 8, 8), dtype=torch.float32)

    with pytest.raises(ValueError, match="clean_image"):
        target_from_batch({"clean_image": None, "input_image": input_image})
    with pytest.raises(ValueError, match="clean_image"):
        target_from_batch({"clean_image": "bad", "input_image": input_image})
    with pytest.raises(ValueError, match="clean_image"):
        target_from_batch({"clean_image": None, "input_image": None})


def test_training_stats_include_optical_residual_gate() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    geometry = _unit_model_config()
    config = TrainingConfig(
        model_role="frozen_optical_frontend_digital_backend",
        trainable_parameters=("connection", "backend"),
        backend=BackendConfig(model_name="nafnet_s"),
        connection=ConnectionConfig.with_optical_residual_gate(initial_gate=0.75),
        frontend_source=_frontend_source_config(Path("checkpoints/frontend.pt")),
    )
    model = _assemble_training_model(config, geometry)

    stats = model_assembly._phase_mask_stats(model)

    assert stats["connection_mode"] == "optical_residual_gate"
    assert stats["optical_residual_gate"] == pytest.approx(0.75)


@pytest.mark.parametrize(
    ("connection_cls", "expected_mode"),
    [
        (DualChannelConnection, "dual_channel"),
        (DualChannelOpticalZeroedConnection, "dual_channel_optical_zeroed"),
    ],
)
def test_connection_stats_reports_dual_channel_modes(
    connection_cls: type[torch.nn.Module],
    expected_mode: str,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    model = torch.nn.Module()
    model.connection = connection_cls()

    stats = model_assembly._connection_stats(model)

    assert stats["connection_mode"] == expected_mode


def test_mechanism_parameter_stats_reports_optical_residual_gate() -> None:
    """
    楠岃瘉鏈哄埗璇佹嵁璁板綍鎺㈡祴鍚庡厜瀛﹀浘鍍忕洿閫氱郴鏁?    """
    model = torch.nn.Module()
    model.connection = build_connection(
        ConnectionConfig.with_optical_residual_gate(
            initial_gate=0.75,
        )
    )

    stats = model_assembly._mechanism_parameter_stats(model)

    assert stats == {"optical_residual_gate": pytest.approx(0.75)}

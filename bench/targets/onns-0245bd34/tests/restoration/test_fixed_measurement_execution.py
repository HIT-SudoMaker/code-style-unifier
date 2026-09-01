from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

import pytest

from experiments.restoration.fixed_measurement.learning import training
from experiments.restoration.fixed_measurement.learning.config import (
    BasicConfig,
    FrontendSourceConfig,
    TrainingConfig,
)
from experiments.restoration.fixed_measurement.evidence.studies import (
    StudyArtifacts,
    build_study_artifacts,
    inspect_study_run,
    prepare_study_run,
)
from experiments.restoration.fixed_measurement.protocol.records import (
    ExperimentPlan,
    StudyConfig,
)
from experiments.restoration.fixed_measurement.learning.execution import (
    StudyExecution,
    TrainingStudyExecutor,
    run_experiment,
    run_study,
)


class _PassingExecutor:
    def execute(
        self,
        config: StudyConfig,
        artifacts: StudyArtifacts,
        *,
        is_resume: bool,
    ) -> StudyExecution:
        """
        杩斿洖閫氳繃鐨勭爺绌舵墽琛岀粨鏋?        """
        del config, artifacts, is_resume
        return StudyExecution(status="PASS", metrics={"psnr": 34.5})


class _RecordingExecutor:
    def __init__(self, calls: list[str]) -> None:
        """
        淇濆瓨杩愯椤哄簭鍒楄〃
        """
        self.calls = calls

    def execute(
        self,
        config: StudyConfig,
        artifacts: StudyArtifacts,
        *,
        is_resume: bool,
    ) -> StudyExecution:
        """
        璁板綍鐮旂┒杩愯鏍囪瘑骞惰繑鍥炵粨鏋?        """
        del artifacts, is_resume
        self.calls.append(config.run_id)
        return StudyExecution(status="PASS", metrics={"study_id": config.study_id})


class _StatusExecutor:
    def __init__(self, calls: list[str], status: str) -> None:
        """
        淇濆瓨璋冪敤鍒楄〃涓庡浐瀹氱姸鎬?        """
        self.calls = calls
        self.status = status

    def execute(
        self,
        config: StudyConfig,
        artifacts: StudyArtifacts,
        *,
        is_resume: bool,
    ) -> StudyExecution:
        """
        璁板綍鐮旂┒骞惰繑鍥炲浐瀹氱姸鎬?        """
        del artifacts, is_resume
        self.calls.append(config.run_id)
        return StudyExecution(status=self.status, metrics={"run_id": config.run_id})


class _RaisingExecutor:
    def execute(
        self,
        config: StudyConfig,
        artifacts: StudyArtifacts,
        *,
        is_resume: bool,
    ) -> StudyExecution:
        del config, artifacts, is_resume
        raise RuntimeError("camera acquisition failed")


def test_study_artifact_state_distinguishes_missing_resumable_and_completed(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鍙浜х墿绱㈠紩鍖哄垎涓夌鍋ュ悍鐘舵€?    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration={"epochs": 50},
    )

    assert inspect_study_run(config).status == "missing"
    prepare_study_run(config, project_root=tmp_path)
    assert inspect_study_run(config).status == "resumable"
    run_study(config, executor=_PassingExecutor())
    completed = inspect_study_run(config)
    assert completed.status == "completed"
    assert completed.training_status == "PASS"


def test_study_artifact_state_marks_untrusted_evidence_invalid(tmp_path: Path) -> None:
    """
    楠岃瘉缂哄皯鍖归厤鏉ユ簮鐨勮瘉鎹笉浼氳闈欓粯澶嶇敤
    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration={"epochs": 50},
    )
    artifacts = prepare_study_run(config, project_root=tmp_path).artifacts
    artifacts.provenance_json.unlink()
    artifacts.epoch_metrics_csv.write_text("epoch,loss\n1,0.5\n", encoding="utf-8")

    state = inspect_study_run(config)

    assert state.status == "invalid"
    assert "provenance" in state.reason


def test_experiment_plan_requires_typed_studies() -> None:
    """
    楠岃瘉瀹為獙璁″垝鍙帴鍙楀師瀛愮爺绌堕厤缃?    """
    with pytest.raises(TypeError, match="StudyConfig"):
        ExperimentPlan(
            plan_id="invalid_study",
            studies=({"study_id": "frontend_only"},),  # type: ignore[arg-type]
        )


def test_run_study_returns_a_typed_result_and_persists_metrics(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鍗曢」鐮旂┒杩斿洖绫诲瀷鍖栫粨鏋滃苟鎸佷箙鍖栨寚鏍?    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        replicate_id=1,
        project_root=tmp_path,
        configuration={"epochs": 50},
    )

    result = run_study(config, executor=_PassingExecutor())

    assert result.study_id == "frontend_only"
    assert result.status == "PASS"
    assert result.run_id == config.run_id
    assert result.run_dir.is_dir()
    assert result.metrics == {"psnr": 34.5}
    assert (result.run_dir / "final_metrics.json").is_file()
    result_payload = json.loads(
        (result.run_dir / "study_result.json").read_text(encoding="utf-8")
    )
    assert result_payload["status"] == "PASS"
    assert result_payload["metrics"] == {"psnr": 34.5}


def test_run_study_preserves_original_runtime_when_resuming(tmp_path: Path) -> None:
    """
    楠岃瘉鎭㈠鐮旂┒淇濈暀棣栨杩愯鐜璁板綍
    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration={"epochs": 50},
    )
    prepared = prepare_study_run(config, project_root=tmp_path)
    original_runtime = '{"created_at": "original"}\n'
    prepared.artifacts.runtime_json.write_text(
        original_runtime,
        encoding="utf-8",
    )

    run_study(config, executor=_PassingExecutor())

    assert (
        prepared.artifacts.runtime_json.read_text(encoding="utf-8") == original_runtime
    )


def test_run_study_appends_failures_without_marking_the_run_complete(
    tmp_path: Path,
) -> None:
    config = StudyConfig(
        study_id="trained_phase_frontend_only",
        method_id="fourier_phase",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration={"epochs": 50},
    )

    for expected_count in (1, 2):
        with pytest.raises(RuntimeError, match="camera acquisition failed"):
            run_study(config, executor=_RaisingExecutor())
        artifacts = build_study_artifacts(config, project_root=tmp_path)
        failures = sorted(artifacts.failure_records_dir.glob("failure_*.json"))
        assert len(failures) == expected_count
        payload = json.loads(failures[-1].read_text(encoding="utf-8"))
        assert payload["status"] == "ERROR"
        assert payload["scientific_role"] == "trained_phase_frontend_only"
        assert payload["error_type"] == "RuntimeError"
        assert not artifacts.study_result_json.exists()


def test_new_fixed_role_records_its_complete_scientific_identity(
    tmp_path: Path,
) -> None:
    config = StudyConfig(
        study_id="digital_backend_only",
        method_id="nafnet_s",
        profile_name="heavy",
        seed=3407,
        project_root=tmp_path,
        upstream_run_ids=("upstream-run",),
        configuration={"backend": "nafnet_s", "updates": 6000},
    )

    result = run_study(config, executor=_PassingExecutor())
    artifacts = build_study_artifacts(config, project_root=tmp_path)
    provenance = json.loads(artifacts.provenance_json.read_text(encoding="utf-8"))
    persisted_result = json.loads(
        artifacts.study_result_json.read_text(encoding="utf-8")
    )

    expected_identity = {
        "scientific_role": "digital_backend_only",
        "profile_name": "heavy",
        "seed": 3407,
        "replicate_id": 1,
        "upstream_run_ids": ["upstream-run"],
    }
    assert result.status == "PASS"
    assert all(
        provenance[field_name] == value
        for field_name, value in expected_identity.items()
    )
    assert all(
        persisted_result[field_name] == value
        for field_name, value in expected_identity.items()
    )


def test_training_executor_adapts_existing_training_to_fixed_artifacts(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉璁粌閫傞厤鍣ㄥ啓鍏ュ浐瀹氭祴閲忎骇鐗╃洰褰?    """
    captured: dict[str, object] = {}

    def training_runner(
        training_config: TrainingConfig,
        *,
        artifact_paths: Mapping[str, Path],
        is_resume: bool,
    ) -> dict[str, object]:
        """
        璁板綍璁粌閫傞厤鍣ㄦ敹鍒扮殑鍙傛暟
        """
        captured["config"] = training_config
        captured["run_dir"] = artifact_paths["run_dir"]
        captured["is_resume"] = is_resume
        return {
            "status": "PASS",
            "final_metrics": {"best_val_psnr": 31.25},
        }

    training_config = TrainingConfig(
        basic=BasicConfig(project_root=tmp_path, seed=42),
    )
    study = StudyConfig(
        study_id="trained_phase_frontend_only",
        method_id="fourier_phase",
        profile_name="medium",
        seed=42,
        replicate_id=1,
        project_root=tmp_path,
        configuration=training_config,
    )

    result = run_study(
        study,
        executor=TrainingStudyExecutor(training_runner=training_runner),
    )

    assert captured == {
        "config": training_config,
        "run_dir": result.run_dir,
        "is_resume": False,
    }
    assert result.metrics == {"best_val_psnr": 31.25}


def test_training_executor_rejects_a_different_training_project_root(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鐮旂┒鏍戜笌璁粌閰嶇疆涓嶈兘鍐欏叆涓嶅悓椤圭洰鏍圭洰褰?    """
    training_config = TrainingConfig(
        basic=BasicConfig(project_root=tmp_path / "other", seed=42),
    )
    study = StudyConfig(
        study_id="trained_phase_frontend_only",
        method_id="fourier_phase",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration=training_config,
    )
    artifacts = prepare_study_run(study, project_root=tmp_path).artifacts

    with pytest.raises(ValueError, match="project_root"):
        TrainingStudyExecutor(training_runner=lambda *args, **kwargs: {}).execute(
            study,
            artifacts,
            is_resume=False,
        )


def test_hybrid_training_source_must_be_an_explicit_upstream_run(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉娣峰悎璁粌鐨勫厜瀛﹀墠绔潵婧愯繘鍏ユ樉寮忎緷璧栧浘
    """
    source_run_id = "medium_s42_r1_c12345678"
    training_config = TrainingConfig(
        basic=BasicConfig(project_root=tmp_path, seed=42),
        model_role="frozen_optical_frontend_digital_backend",
        frontend_source=FrontendSourceConfig(
            checkpoint_path=tmp_path / "frontend.pt",
            run_id=source_run_id,
            source_config_hash="config",
            source_geometry_hash="geometry",
            source_degradation_hash="degradation",
        ),
        trainable_parameters=("backend",),
    )
    study = StudyConfig(
        study_id="frozen_frontend_serial",
        method_id="nafnet_s",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration=training_config,
    )
    artifacts = prepare_study_run(study, project_root=tmp_path).artifacts

    with pytest.raises(ValueError, match="upstream_run_ids"):
        TrainingStudyExecutor(training_runner=lambda *args, **kwargs: {}).execute(
            study,
            artifacts,
            is_resume=False,
        )


def test_run_study_selects_training_adapter_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉鍗曢」鐮旂┒榛樿閫夋嫨璁粌閫傞厤鍣?    """

    def training_runner(
        training_config: TrainingConfig,
        *,
        artifact_paths: Mapping[str, Path],
        is_resume: bool,
    ) -> dict[str, object]:
        """
        杩斿洖鏈€灏忚缁冪粨鏋?        """
        del training_config, artifact_paths, is_resume
        return {"status": "PASS", "final_metrics": {"best_val_psnr": 30.0}}

    monkeypatch.setattr(training, "run_training", training_runner)
    training_config = TrainingConfig(
        basic=BasicConfig(project_root=tmp_path, seed=42),
    )
    study = StudyConfig(
        study_id="trained_phase_frontend_only",
        method_id="fourier_phase",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration=training_config,
    )

    result = run_study(study)

    assert result.status == "PASS"
    assert result.metrics == {"best_val_psnr": 30.0}


def test_run_experiment_executes_explicit_run_dependencies_in_order(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉瀹為獙鎸夋樉寮忚繍琛屼緷璧栭『搴忔墽琛?    """
    frontend = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration={"kind": "frontend"},
    )
    frozen = StudyConfig(
        study_id="frozen_cascade",
        method_id="nafnet_s",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        upstream_run_ids=(frontend.run_id,),
        configuration={"kind": "frozen"},
    )
    plan = ExperimentPlan(
        plan_id="medium_seed_42",
        studies=(frozen, frontend),
    )
    calls: list[str] = []
    executor = _RecordingExecutor(calls)

    report = run_experiment(
        plan,
        executors={frontend.run_id: executor, frozen.run_id: executor},
    )

    assert calls == [frontend.run_id, frozen.run_id]
    assert report.status == "PASS"
    assert [result.run_id for result in report.studies] == calls
    assert report.report_dir == (
        tmp_path
        / "results"
        / "restoration"
        / "fixed_measurement"
        / "reports"
        / "medium_seed_42"
    )
    assert report.report_json.is_file()
    assert report.summary_md.is_file()


def test_run_experiment_reuses_completed_upstream_study(tmp_path: Path) -> None:
    """
    楠岃瘉瀹為獙璁″垝澶嶇敤宸插畬鎴愪笂娓哥爺绌?    """
    frontend = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration={"kind": "frontend"},
    )
    run_study(frontend, executor=_PassingExecutor())
    frozen = StudyConfig(
        study_id="frozen_cascade",
        method_id="nafnet_s",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        upstream_run_ids=(frontend.run_id,),
        configuration={"kind": "frozen"},
    )
    calls: list[str] = []
    executor = _RecordingExecutor(calls)

    report = run_experiment(
        ExperimentPlan(plan_id="reuse_frontend", studies=(frontend, frozen)),
        executors={frontend.run_id: executor, frozen.run_id: executor},
    )

    assert calls == [frozen.run_id]
    assert [result.run_id for result in report.studies] == [
        frontend.run_id,
        frozen.run_id,
    ]


def test_run_experiment_continues_independent_branch_after_failed_dependency(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉渚濊禆澶辫触涓嶉樆鏂嫭绔嬬爺绌跺垎鏀?    """
    frontend = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration={"kind": "frontend"},
    )
    frozen = StudyConfig(
        study_id="frozen_cascade",
        method_id="nafnet_s",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        upstream_run_ids=(frontend.run_id,),
        configuration={"kind": "frozen"},
    )
    backend = StudyConfig(
        study_id="backend_only",
        method_id="nafnet_s",
        profile_name="medium",
        seed=42,
        replicate_id=2,
        project_root=tmp_path,
        configuration={"kind": "backend"},
    )
    calls: list[str] = []
    failed = _StatusExecutor(calls, "FAIL")
    passed = _StatusExecutor(calls, "PASS")

    report = run_experiment(
        ExperimentPlan(
            plan_id="independent_branch",
            studies=(frontend, frozen, backend),
        ),
        executors={
            frontend.run_id: failed,
            frozen.run_id: passed,
            backend.run_id: passed,
        },
    )

    assert calls == [frontend.run_id, backend.run_id]
    assert report.status == "FAIL"
    assert report.skipped_run_ids == (frozen.run_id,)


def test_run_experiment_skips_all_descendants_of_a_failed_study(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉澶辫触鐮旂┒鐨勯棿鎺ヤ緷璧栦篃浼氳鏍囪涓鸿烦杩?    """
    frontend = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        configuration={"kind": "frontend"},
    )
    frozen = StudyConfig(
        study_id="frozen_cascade",
        method_id="nafnet_s",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        upstream_run_ids=(frontend.run_id,),
        configuration={"kind": "frozen"},
    )
    joint = StudyConfig(
        study_id="joint_cascade",
        method_id="spectral_dual_stream",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        upstream_run_ids=(frozen.run_id,),
        configuration={"kind": "joint"},
    )
    calls: list[str] = []

    report = run_experiment(
        ExperimentPlan(
            plan_id="failed_descendants",
            studies=(joint, frozen, frontend),
        ),
        executors={
            frontend.run_id: _StatusExecutor(calls, "FAIL"),
            frozen.run_id: _StatusExecutor(calls, "PASS"),
            joint.run_id: _StatusExecutor(calls, "PASS"),
        },
    )

    assert calls == [frontend.run_id]
    assert report.skipped_run_ids == (frozen.run_id, joint.run_id)


def test_run_experiment_accepts_a_verified_external_upstream_run(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉瀹归噺璁″垝鍙互澹版槑宸茬敱鏍稿績闂ㄧ楠岃瘉鐨勫閮ㄥ厜瀛︽簮
    """
    capacity = StudyConfig(
        study_id="frozen_cascade",
        method_id="fourier_phase_nafnet_m",
        profile_name="medium",
        seed=42,
        project_root=tmp_path,
        upstream_run_ids=("verified-optical-run",),
        configuration={"kind": "capacity"},
    )
    calls: list[str] = []

    report = run_experiment(
        ExperimentPlan(plan_id="capacity_only", studies=(capacity,)),
        executors={capacity.run_id: _RecordingExecutor(calls)},
        external_passed_run_ids=("verified-optical-run",),
    )

    assert report.status == "PASS"
    assert calls == [capacity.run_id]

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from experiments.restoration.fixed_measurement.evidence.training_artifacts import write_json, write_runtime
from experiments.restoration.fixed_measurement.evidence.studies import (
    STUDY_RESULT_SCHEMA_VERSION,
    StudyArtifacts,
    build_study_artifacts,
    load_completed_study_result,
    prepare_study_run,
    write_study_failure,
)
from experiments.restoration.fixed_measurement.protocol.records import (
    ExperimentPlan,
    ExperimentReport,
    StudyConfig,
    StudyResult,
)
from experiments.restoration.fixed_measurement.protocol.vocabulary import (
    fixed_role_for_model_role,
)

if TYPE_CHECKING:
    from experiments.restoration.fixed_measurement.learning.config import TrainingConfig


TrainingRunner = Callable[..., Mapping[str, object]]

_TRAINING_CONFIG_REQUIRED = "training study configuration must be TrainingConfig"
_ROLE_MISMATCH = "study_id {study_id!r} does not match model_role {model_role!r}"
_SEED_MISMATCH = "study seed must match TrainingConfig.basic.seed"
_PROJECT_ROOT_MISMATCH = (
    "study project_root must match TrainingConfig.basic.project_root"
)
_FRONTEND_UPSTREAM_REQUIRED = (
    "hybrid frontend_source.run_id must appear in study upstream_run_ids"
)
_TRAINING_STATUS_REQUIRED = "training runner must return PASS or FAIL status"
_TRAINING_METRICS_REQUIRED = "training runner must return final_metrics mapping"
_EXECUTOR_STATUS_REQUIRED = "study executor status must be PASS or FAIL"
_MISSING_UPSTREAM = "study {run_id} has missing upstream runs: {missing_names}"
_DEPENDENCY_CYCLE = "experiment plan contains a dependency cycle"


@dataclass(frozen=True, slots=True)
class StudyExecution:
    """
    鎵胯浇鍥哄畾娴嬮噺鎵ц缁撴灉
    """

    status: str
    metrics: Mapping[str, object]


class StudyExecutor(Protocol):
    """
    瀹氫箟宸插噯澶囧師瀛愮爺绌剁殑鎵ц鎺ュ彛
    """

    def execute(
        self,
        config: StudyConfig,
        artifacts: StudyArtifacts,
        *,
        is_resume: bool,
    ) -> StudyExecution:
        """
        杩斿洖宸插噯澶囩爺绌剁殑鍙瀵熺粨鏋?        """


@dataclass(frozen=True, slots=True)
class TrainingStudyExecutor:
    """
    灏嗘棦鏈夎缁冨紩鎿庨€傞厤鍒板浐瀹氭祴閲忔帴鍙?    """

    training_runner: TrainingRunner | None = None

    def execute(
        self,
        config: StudyConfig,
        artifacts: StudyArtifacts,
        *,
        is_resume: bool,
    ) -> StudyExecution:
        """
        鍦ㄦ寚瀹氫骇鐗╂爲涓墽琛岀被鍨嬪寲璁粌鐮旂┒
        """
        from experiments.restoration.fixed_measurement.learning.config import TrainingConfig

        if not isinstance(config.configuration, TrainingConfig):
            raise TypeError(_TRAINING_CONFIG_REQUIRED)
        training_config = config.configuration
        expected_study_id = fixed_role_for_model_role(training_config.model_role)
        if config.study_id != expected_study_id:
            message = _ROLE_MISMATCH.format(
                study_id=config.study_id,
                model_role=training_config.model_role,
            )
            raise ValueError(message)
        if config.seed != training_config.basic.seed:
            raise ValueError(_SEED_MISMATCH)
        if config.project_root.resolve() != Path(
            training_config.basic.project_root
        ).resolve():
            raise ValueError(_PROJECT_ROOT_MISMATCH)
        if training_config.model_role in {
            "frozen_optical_frontend_digital_backend",
            "joint_optical_frontend_digital_backend",
        }:
            frontend_source = training_config.frontend_source
            if (
                frontend_source is None
                or frontend_source.run_id not in config.upstream_run_ids
            ):
                raise ValueError(_FRONTEND_UPSTREAM_REQUIRED)

        runner = self.training_runner
        if runner is None:
            from experiments.restoration.fixed_measurement.learning.training import run_training

            runner = run_training
        payload = runner(
            training_config,
            artifact_paths=artifacts.as_training_paths(),
            is_resume=is_resume,
        )
        status = payload.get("status")
        metrics = payload.get("final_metrics")
        if status not in {"PASS", "FAIL"}:
            raise ValueError(_TRAINING_STATUS_REQUIRED)
        if not isinstance(metrics, Mapping):
            raise ValueError(_TRAINING_METRICS_REQUIRED)
        return StudyExecution(status=status, metrics=dict(metrics))


def run_study(
    config: StudyConfig,
    *,
    executor: StudyExecutor | None = None,
) -> StudyResult:
    """
    閫氳繃宸叉敞鍐岄€傞厤鍣ㄦ墽琛屽崟娆″浐瀹氭祴閲忕爺绌?    """
    if executor is None:
        executor = TrainingStudyExecutor()
    prepared = prepare_study_run(config, project_root=config.project_root)
    if prepared.disposition == "new" or not prepared.artifacts.config_json.is_file():
        write_json(prepared.artifacts.config_json, config.configuration)
    if prepared.disposition == "new" or not prepared.artifacts.runtime_json.is_file():
        write_runtime(prepared.artifacts.runtime_json)
    try:
        execution = executor.execute(
            config,
            prepared.artifacts,
            is_resume=prepared.disposition == "resume",
        )
    except Exception as error:
        write_study_failure(prepared.artifacts, config, error)
        raise
    if execution.status not in {"PASS", "FAIL"}:
        raise ValueError(_EXECUTOR_STATUS_REQUIRED)
    write_json(prepared.artifacts.final_metrics_json, execution.metrics)
    write_json(
        prepared.artifacts.study_result_json,
        {
            "schema_version": STUDY_RESULT_SCHEMA_VERSION,
            "study_id": config.study_id,
            "method_id": config.method_id,
            "run_id": config.run_id,
            "config_fingerprint": config.config_fingerprint,
            "profile_name": config.profile_name,
            "seed": config.seed,
            "replicate_id": config.replicate_id,
            "upstream_run_ids": config.upstream_run_ids,
            "scientific_role": config.study_id,
            "status": execution.status,
            "metrics": execution.metrics,
        },
    )
    return StudyResult(
        study_id=config.study_id,
        status=execution.status,
        run_id=config.run_id,
        run_dir=prepared.artifacts.run_dir,
        metrics=dict(execution.metrics),
    )


def run_experiment(
    plan: ExperimentPlan,
    *,
    executors: Mapping[str, StudyExecutor] | None = None,
    external_passed_run_ids: tuple[str, ...] = (),
) -> ExperimentReport:
    """
    鎵ц骞舵眹鎬诲疄楠岃鍒掍腑鐨勫師瀛愮爺绌?    """
    external_passed_run_id_set = set(external_passed_run_ids)
    execution_order = _study_execution_order(
        plan,
        external_passed_run_ids=external_passed_run_id_set,
    )
    executor_by_run_id = executors or {}
    results: list[StudyResult] = []
    result_by_run_id: dict[str, StudyResult] = {}
    skipped_run_ids: list[str] = []
    skipped_run_id_set: set[str] = set()
    for study in execution_order:
        if any(
            upstream_run_id not in external_passed_run_id_set
            and (
                upstream_run_id in skipped_run_id_set
                or result_by_run_id[upstream_run_id].status != "PASS"
            )
            for upstream_run_id in study.upstream_run_ids
        ):
            skipped_run_ids.append(study.run_id)
            skipped_run_id_set.add(study.run_id)
            continue
        artifacts = build_study_artifacts(
            study,
            project_root=study.project_root,
        )
        if artifacts.study_result_json.is_file():
            result = load_completed_study_result(study, artifacts=artifacts)
        else:
            result = run_study(
                study,
                executor=executor_by_run_id.get(study.run_id),
            )
        results.append(result)
        result_by_run_id[study.run_id] = result
    status = "PASS" if len(results) == len(plan.studies) and all(
        result.status == "PASS" for result in results
    ) else "FAIL"
    report_dir = (
        Path(plan.studies[0].project_root)
        / "results"
        / "restoration"
        / "fixed_measurement"
        / "reports"
        / plan.plan_id
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / "experiment_report.json"
    summary_md = report_dir / "summary.md"
    report = ExperimentReport(
        plan_id=plan.plan_id,
        status=status,
        studies=tuple(results),
        report_dir=report_dir,
        report_json=report_json,
        summary_md=summary_md,
        skipped_run_ids=tuple(skipped_run_ids),
    )
    write_json(
        report_json,
        {
            "schema_version": "fixed_measurement_experiment_v1",
            "plan_id": plan.plan_id,
            "status": status,
            "study_count": len(results),
            "skipped_run_ids": skipped_run_ids,
            "studies": results,
        },
    )
    summary_md.write_text(
        "# Fixed-Measurement Experiment\n\n"
        f"- Plan: {plan.plan_id}\n"
        f"- Status: {status}\n"
        f"- Completed studies: {len(results)}/{len(plan.studies)}\n",
        encoding="utf-8",
    )
    return report


def _study_execution_order(
    plan: ExperimentPlan,
    *,
    external_passed_run_ids: set[str] | None = None,
) -> tuple[StudyConfig, ...]:
    external_run_ids = external_passed_run_ids or set()
    study_by_run_id = {study.run_id: study for study in plan.studies}
    for study in plan.studies:
        missing = (
            set(study.upstream_run_ids)
            - study_by_run_id.keys()
            - external_run_ids
        )
        if missing:
            missing_names = ", ".join(sorted(missing))
            message = _MISSING_UPSTREAM.format(
                run_id=study.run_id,
                missing_names=missing_names,
            )
            raise ValueError(message)

    ordered: list[StudyConfig] = []
    completed: set[str] = set(external_run_ids)
    remaining = list(plan.studies)
    while remaining:
        ready_index = next(
            (
                index
                for index, study in enumerate(remaining)
                if set(study.upstream_run_ids).issubset(completed)
            ),
            None,
        )
        if ready_index is None:
            raise ValueError(_DEPENDENCY_CYCLE)
        study = remaining.pop(ready_index)
        ordered.append(study)
        completed.add(study.run_id)
    return tuple(ordered)

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
from experiments.restoration.fixed_measurement.learning.config import (
    BasicConfig,
    FrontendSourceConfig,
    TrainingConfig,
)
from experiments.restoration.fixed_measurement.learning.connection import ConnectionConfig
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.fixed_measurement.evidence.studies import (
    build_study_artifacts,
)
from experiments.restoration.fixed_measurement.protocol.records import (
    ExperimentPlan,
    StudyConfig,
)
from experiments.restoration.fixed_measurement.protocol.settings import (
    CAPACITY_MAX_OPTIMIZER_UPDATES,
    EFFECTIVE_BATCH_SIZE,
    FIXED_TRAINING_POLICY,
    MICRO_BATCH_SIZE,
    PRIMARY_MAX_OPTIMIZER_UPDATES,
    PROFILES,
    TRAINING_SEEDS,
    ProtocolInputs,
)
from experiments.restoration.fixed_measurement.protocol.vocabulary import (
    FIXED_TRAINING_ROLES,
    FixedTrainingRole,
    MODEL_ROLE_BY_FIXED_ROLE,
)
from experiments.restoration.fixed_measurement.learning.schemas import (
    DEFAULT_TRAINABLE_PARAMETERS_BY_MODEL_ROLE,
    ModelRole,
)
from experiments.restoration.fixed_measurement.learning.standard_configs import (
    build_standard_dataset_config,
    degradation_hash_for_dataset_config,
)


FIXED_BACKEND_MODEL = "nafnet_s"
CAPACITY_CHALLENGE_BACKEND_MODEL = "nafnet_m"
FIXED_PLAN_ID = "fixed_measurement_claim_matrix_v3"
_SERIAL_ROLES = {"frozen_frontend_serial", "joint_frontend_serial"}
_DEFAULT_HYPERPARAMETERS = {
    "learning_rate": 3e-3,
    "weight_decay": 0.0,
    "loss_l1_weight": 1.0,
    "loss_ssim_weight": 0.2,
    "loss_frequency_weight": 0.1,
    "phase_smoothness_weight": 1e-4,
}


def compile_fixed_experiment_plan(inputs: ProtocolInputs) -> ExperimentPlan:
    """Compile the four-role matrix and its digital-capacity challenge."""
    frontend_studies: dict[tuple[str, int], StudyConfig] = {}
    studies: list[StudyConfig] = []
    for profile_name in PROFILES:
        for seed in TRAINING_SEEDS:
            study = _compile_fixed_study(
                inputs=inputs,
                role="trained_phase_frontend_only",
                profile_name=profile_name,
                seed=seed,
                frontend_source=None,
            )
            frontend_studies[(profile_name, seed)] = study
            studies.append(study)

    for role in FIXED_TRAINING_ROLES[1:]:
        for profile_name in PROFILES:
            for seed in TRAINING_SEEDS:
                frontend_source = None
                if role in _SERIAL_ROLES:
                    frontend_source = frontend_studies[(profile_name, seed)]
                studies.append(
                    _compile_fixed_study(
                        inputs=inputs,
                        role=role,
                        profile_name=profile_name,
                        seed=seed,
                        frontend_source=frontend_source,
                    )
                )

    for profile_name in PROFILES:
        for seed in TRAINING_SEEDS:
            studies.append(
                _compile_fixed_study(
                    inputs=inputs,
                    role="digital_backend_only",
                    profile_name=profile_name,
                    seed=seed,
                    frontend_source=None,
                    backend_model=CAPACITY_CHALLENGE_BACKEND_MODEL,
                )
            )

    _validate_fixed_matrix(studies)
    return ExperimentPlan(plan_id=FIXED_PLAN_ID, studies=tuple(studies))


def _compile_fixed_study(
    *,
    inputs: ProtocolInputs,
    role: FixedTrainingRole,
    profile_name: str,
    seed: int,
    frontend_source: StudyConfig | None,
    backend_model: str = FIXED_BACKEND_MODEL,
) -> StudyConfig:
    model_role = MODEL_ROLE_BY_FIXED_ROLE[role]
    if (role in _SERIAL_ROLES) != (frontend_source is not None):
        raise invalid_restoration_contract(
            "only serial Fixed roles receive a trained frontend source"
        )
    training = TrainingConfig(
        basic=BasicConfig(
            project_root=inputs.project_root,
            run_name=f"{role}_{profile_name}_s{seed}",
            device=inputs.device,
            seed=seed,
        ),
        operating_point_path=inputs.operating_point_path,
        train_dataset_config=_dataset_config(inputs, profile_name, "train"),
        val_dataset_config=_dataset_config(inputs, profile_name, "val"),
        training_mode="single",
        model_role=model_role,
        backend=(
            None
            if role == "trained_phase_frontend_only"
            else BackendConfig(model_name=backend_model)
        ),
        frontend_source=_frontend_source_config(
            inputs=inputs,
            source_study=frontend_source,
        ),
        connection=ConnectionConfig(mode="serial"),
        search=None,
        epochs=(
            CAPACITY_MAX_OPTIMIZER_UPDATES
            if backend_model == CAPACITY_CHALLENGE_BACKEND_MODEL
            else PRIMARY_MAX_OPTIMIZER_UPDATES
        ),
        batch_size=MICRO_BATCH_SIZE,
        effective_batch_size=EFFECTIVE_BATCH_SIZE,
        max_optimizer_updates=(
            CAPACITY_MAX_OPTIMIZER_UPDATES
            if backend_model == CAPACITY_CHALLENGE_BACKEND_MODEL
            else PRIMARY_MAX_OPTIMIZER_UPDATES
        ),
        trainable_parameters=DEFAULT_TRAINABLE_PARAMETERS_BY_MODEL_ROLE[model_role],
        **_fixed_hyperparameters(role, profile_name),
    )
    upstream_run_ids = ()
    if frontend_source is not None:
        upstream_run_ids = (frontend_source.run_id,)
    return StudyConfig(
        study_id=role,
        method_id=(
            "fourier_phase"
            if role == "trained_phase_frontend_only"
            else backend_model
        ),
        profile_name=profile_name,
        seed=seed,
        configuration=training,
        project_root=inputs.project_root,
        upstream_run_ids=upstream_run_ids,
    )


def _frontend_source_config(
    *,
    inputs: ProtocolInputs,
    source_study: StudyConfig | None,
) -> FrontendSourceConfig | None:
    if source_study is None:
        return None
    source_training = _training_configuration(source_study)
    operating_point = json.loads(
        Path(inputs.operating_point_path).read_text(encoding="utf-8")
    )
    geometry_hash = operating_point.get("geometry_hash")
    if not isinstance(geometry_hash, str) or not geometry_hash:
        raise invalid_restoration_contract("operating point must contain geometry_hash")
    source_artifacts = build_study_artifacts(
        source_study,
        project_root=inputs.project_root,
    )
    return FrontendSourceConfig(
        checkpoint_path=source_artifacts.best_checkpoint,
        run_id=source_study.run_id,
        source_config_hash=compute_config_hash(source_training),
        source_geometry_hash=geometry_hash,
        source_degradation_hash=degradation_hash_for_dataset_config(
            source_training.train_dataset_config
        ),
        source_profile_name=source_study.profile_name,
        source_seed=source_study.seed,
        source_run_key=source_training.basic.run_name,
    )


def _fixed_hyperparameters(
    role: FixedTrainingRole,
    profile_name: str,
) -> dict[str, object]:
    values = dict(_DEFAULT_HYPERPARAMETERS)
    family = "optical" if role == "trained_phase_frontend_only" else "digital"
    if role == "digital_backend_only":
        values["loss_frequency_weight"] = 0.0
        values["phase_smoothness_weight"] = 0.0
    elif role == "frozen_frontend_serial":
        values["phase_smoothness_weight"] = 0.0
    values.update(FIXED_TRAINING_POLICY[(family, profile_name)])
    return values


def _dataset_config(
    inputs: ProtocolInputs,
    profile_name: str,
    split: str,
) -> dict[str, object]:
    return build_standard_dataset_config(
        profile_name=profile_name,
        split=split,
        split_manifest=inputs.split_manifest,
        dataset_root=(Path(inputs.project_root) / Path(inputs.dataset_root)).resolve(),
    )


def _training_configuration(study: StudyConfig) -> TrainingConfig:
    if not isinstance(study.configuration, TrainingConfig):
        raise invalid_restoration_contract(
            "Fixed experiment studies must contain TrainingConfig"
        )
    return study.configuration


def _validate_fixed_matrix(studies: list[StudyConfig]) -> None:
    role_counts = Counter(study.study_id for study in studies)
    expected_counts = {
        "trained_phase_frontend_only": 9,
        "digital_backend_only": 18,
        "frozen_frontend_serial": 9,
        "joint_frontend_serial": 9,
    }
    if role_counts != expected_counts:
        raise invalid_restoration_contract(
            "Fixed matrix must contain 36 primary runs and nine digital-capacity runs"
        )
    for study in studies:
        training = _training_configuration(study)
        expected_model_role: ModelRole = MODEL_ROLE_BY_FIXED_ROLE[
            study.study_id  # type: ignore[index]
        ]
        if training.model_role != expected_model_role:
            raise invalid_restoration_contract(
                "Fixed role does not match its native model structure"
            )
        if study.study_id == "trained_phase_frontend_only":
            if training.backend is not None:
                raise invalid_restoration_contract(
                    "trained-phase frontend-only runs must not have a backend"
                )
            continue
        if training.backend is None:
            raise invalid_restoration_contract(
                "digital-bearing Fixed roles must declare a backend"
            )
        if study.study_id == "digital_backend_only":
            if training.backend.model_name not in {
                FIXED_BACKEND_MODEL,
                CAPACITY_CHALLENGE_BACKEND_MODEL,
            }:
                raise invalid_restoration_contract(
                    "digital-only runs must use NAFNet-S or NAFNet-M"
                )
            continue
        if training.backend.model_name != FIXED_BACKEND_MODEL:
            raise invalid_restoration_contract(
                "serial Fixed roles must use the common NAFNet-S backend"
            )

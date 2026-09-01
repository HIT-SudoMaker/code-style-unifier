from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.restoration.fixed_measurement.evidence.studies import (
    StudyRunExistsError,
    StudyRunProvenanceError,
    build_study_artifacts,
    load_completed_study_result,
    prepare_study_run,
)
from experiments.restoration.fixed_measurement.protocol.records import StudyConfig


def test_fixed_measurement_run_path_is_compact_and_hierarchical(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鍥哄畾娴嬮噺杩愯璺緞鐭皬涓斿垎灞?    """
    config = StudyConfig(
        study_id="frozen_cascade",
        method_id="spectral_dual_stream",
        profile_name="medium",
        seed=42,
        replicate_id=1,
        configuration={"learning_rate": 3e-4, "epochs": 50},
    )

    artifacts = build_study_artifacts(config, project_root=tmp_path)

    assert config.run_id.startswith("medium_s42_r1_c")
    assert len(config.run_id) <= 48
    assert artifacts.run_dir == (
        tmp_path
        / "results"
        / "restoration"
        / "fixed_measurement"
        / "frozen_cascade"
        / "spectral_dual_stream"
        / config.run_id
    )
    assert "optuna_dir" not in artifacts.as_training_paths()
    assert "optuna_study_json" not in artifacts.as_training_paths()
    assert not hasattr(artifacts, "optuna_dir")
    assert not hasattr(artifacts, "optuna_study_json")


def test_completed_study_run_is_never_silently_overwritten(tmp_path: Path) -> None:
    """
    楠岃瘉宸插畬鎴愮爺绌朵笉鍙闈欓粯瑕嗙洊
    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="light",
        seed=42,
        replicate_id=1,
        configuration={"epochs": 50},
    )

    prepared = prepare_study_run(config, project_root=tmp_path)
    prepared.artifacts.study_result_json.write_text("{}\n", encoding="utf-8")

    with pytest.raises(StudyRunExistsError, match="already complete"):
        prepare_study_run(config, project_root=tmp_path)


def test_partial_final_metrics_do_not_mark_study_complete(tmp_path: Path) -> None:
    """
    楠岃瘉璁粌鎸囨爣鍏堝啓鍏ユ椂鍘熷瓙鐮旂┒浠嶅彲鎭㈠
    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        configuration={"epochs": 50},
    )
    prepared = prepare_study_run(config, project_root=tmp_path)
    prepared.artifacts.final_metrics_json.write_text("{}\n", encoding="utf-8")

    resumed = prepare_study_run(config, project_root=tmp_path)

    assert resumed.disposition == "resume"


def test_empty_run_directory_left_before_provenance_is_recovered(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鏉ユ簮鍐欏叆鍓嶄腑鏂暀涓嬬殑绌虹洰褰曚粛鍙垵濮嬪寲
    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        configuration={"epochs": 50},
    )
    artifacts = build_study_artifacts(config, project_root=tmp_path)
    artifacts.checkpoints_dir.mkdir(parents=True)

    prepared = prepare_study_run(config, project_root=tmp_path)

    assert prepared.disposition == "new"
    assert prepared.artifacts.provenance_json.is_file()


def test_nonempty_run_directory_without_provenance_fails_loudly(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鏈煡鏉ユ簮鏂囦欢涓嶈兘琚嚜鍔ㄨ棰?    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        configuration={"epochs": 50},
    )
    artifacts = build_study_artifacts(config, project_root=tmp_path)
    artifacts.run_dir.mkdir(parents=True)
    (artifacts.run_dir / "unknown.txt").write_text("unknown\n", encoding="utf-8")

    with pytest.raises(StudyRunProvenanceError, match="missing provenance"):
        prepare_study_run(config, project_root=tmp_path)


def test_completed_run_still_requires_matching_provenance(tmp_path: Path) -> None:
    """
    楠岃瘉瀹屾垚鏍囪涓嶈兘缁曡繃杩愯鏉ユ簮鏍￠獙
    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        configuration={"epochs": 50},
    )
    prepared = prepare_study_run(config, project_root=tmp_path)
    prepared.artifacts.study_result_json.write_text(
        json.dumps(
            {
                "study_id": config.study_id,
                "run_id": config.run_id,
                "config_fingerprint": config.config_fingerprint,
                "status": "PASS",
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )
    prepared.artifacts.provenance_json.unlink()

    with pytest.raises(StudyRunProvenanceError, match="missing provenance"):
        prepare_study_run(config, project_root=tmp_path)


def test_incomplete_study_run_resumes_only_with_matching_provenance(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鏈畬鎴愮爺绌朵粎鍦ㄦ潵婧愪竴鑷存椂鎭㈠
    """
    config = StudyConfig(
        study_id="backend_only",
        method_id="nafnet_s",
        profile_name="heavy",
        seed=3407,
        replicate_id=1,
        configuration={"epochs": 50},
    )

    first = prepare_study_run(config, project_root=tmp_path)
    second = prepare_study_run(config, project_root=tmp_path)

    assert first.disposition == "new"
    assert second.disposition == "resume"

    provenance = json.loads(first.artifacts.provenance_json.read_text(encoding="utf-8"))
    provenance["config_fingerprint"] = "different"
    first.artifacts.provenance_json.write_text(
        json.dumps(provenance),
        encoding="utf-8",
    )

    with pytest.raises(StudyRunProvenanceError, match="fingerprint"):
        prepare_study_run(config, project_root=tmp_path)


def test_matching_fingerprint_cannot_hide_provenance_identity_mismatch(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鏉ユ簮鎸囩汗涓€鑷存椂浠嶆牎楠屽彲璇荤爺绌惰韩浠?    """
    config = StudyConfig(
        study_id="backend_only",
        method_id="nafnet_s",
        profile_name="medium",
        seed=42,
        configuration={"epochs": 50},
    )
    prepared = prepare_study_run(config, project_root=tmp_path)
    provenance = json.loads(
        prepared.artifacts.provenance_json.read_text(encoding="utf-8")
    )
    provenance["method_id"] = "different"
    prepared.artifacts.provenance_json.write_text(
        json.dumps(provenance),
        encoding="utf-8",
    )

    with pytest.raises(StudyRunProvenanceError, match="identity"):
        prepare_study_run(config, project_root=tmp_path)


def test_completed_study_result_requires_current_schema(tmp_path: Path) -> None:
    """
    楠岃瘉瀹屾垚鏍囪澹版槑鍥哄畾娴嬮噺缁撴灉妯″紡
    """
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        configuration={"epochs": 50},
    )
    prepared = prepare_study_run(config, project_root=tmp_path)
    prepared.artifacts.study_result_json.write_text(
        json.dumps(
            {
                "schema_version": "unexpected",
                "study_id": config.study_id,
                "method_id": config.method_id,
                "run_id": config.run_id,
                "config_fingerprint": config.config_fingerprint,
                "status": "PASS",
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(StudyRunProvenanceError, match="schema"):
        load_completed_study_result(config, artifacts=prepared.artifacts)


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    (
        ("study_id", "s" * 49),
        ("method_id", "m" * 49),
        ("profile_name", "p" * 25),
    ),
)
def test_study_identity_rejects_segments_that_expand_windows_paths(
    field_name: str,
    field_value: str,
) -> None:
    """
    楠岃瘉鐮旂┒韬唤瀛楁鍏锋湁鏄惧紡闀垮害涓婇檺
    """
    values = {
        "study_id": "frontend_only",
        "method_id": "optical_frontend",
        "profile_name": "medium",
    }
    values[field_name] = field_value

    with pytest.raises(ValueError, match="at most"):
        StudyConfig(
            **values,
            seed=42,
            configuration={"epochs": 50},
        )


def test_study_seed_must_fit_reproducible_rng_range() -> None:
    """
    楠岃瘉鐮旂┒闅忔満绉嶅瓙閫傞厤 NumPy 涓?Torch 鐨勫叕鍏辫寖鍥?    """
    with pytest.raises(ValueError, match="4294967295"):
        StudyConfig(
            study_id="frontend_only",
            method_id="optical_frontend",
            profile_name="medium",
            seed=2**32,
            configuration={"epochs": 50},
        )


def test_study_replicate_id_keeps_run_segment_bounded() -> None:
    """
    楠岃瘉閲嶅缂栧彿涓嶄細鏃犻檺鎵╁紶 Windows 璺緞
    """
    with pytest.raises(ValueError, match="9999"):
        StudyConfig(
            study_id="frontend_only",
            method_id="optical_frontend",
            profile_name="medium",
            seed=42,
            replicate_id=10_000,
            configuration={"epochs": 50},
        )


def test_study_identity_rejects_configuration_mutation_before_run(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鍘熷瓙鐮旂┒韬唤涓嶄細闅忓彲鍙橀厤缃潤榛樻紓绉?    """
    configuration = {"epochs": 50}
    config = StudyConfig(
        study_id="frontend_only",
        method_id="optical_frontend",
        profile_name="medium",
        seed=42,
        configuration=configuration,
    )
    original_run_id = config.run_id
    configuration["epochs"] = 60

    assert config.run_id == original_run_id
    with pytest.raises(ValueError, match="mutated after StudyConfig creation"):
        prepare_study_run(config, project_root=tmp_path)

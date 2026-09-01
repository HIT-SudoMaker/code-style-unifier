from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import pytest

from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.optical_bench import OpticalBenchConfig
from experiments.restoration.fixed_measurement.protocol.inputs import (
    DEFAULT_OPERATING_POINT,
    DEFAULT_SPLIT_MANIFEST,
    load_protocol_inputs,
    verify_protocol_inputs,
)
from experiments.restoration.fixed_measurement.learning.splits import build_real_fmd_split_manifest


def _write_archive(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.restoration.fixed_measurement.learning import splits

    source_root = project_root / "data/raw/fmd/averaged"
    records = []
    for index, image_id in enumerate(
        (
            "fmd/Confocal_BPAE_G/1/avg50",
            "fmd/Confocal_BPAE_G/2/avg50",
            "fmd/Confocal_BPAE_G/3/avg50",
        )
    ):
        source_path = source_root / f"{image_id.removeprefix('fmd/')}.png"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(f"clean-image-{index}".encode("utf-8"))
        records.append(
            type("Record", (), {"image_id": image_id, "source_path": source_path})()
        )
    monkeypatch.setattr(
        splits,
        "build_file_source_records",
        lambda **kwargs: (source_root, records, "single"),
    )
    manifest = build_real_fmd_split_manifest(
        dataset_root=project_root / "data/raw",
    )
    manifest["source_dataset_root_hint"] = "data/raw/fmd/averaged"
    for record in manifest["records"]:
        record["source_path"] = Path(record["source_path"]).relative_to(
            project_root
        ).as_posix()

    split_path = project_root / DEFAULT_SPLIT_MANIFEST
    split_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.write_text(json.dumps(manifest), encoding="utf-8")

    characterization_dir = (project_root / DEFAULT_OPERATING_POINT).parent
    characterization_dir.mkdir(parents=True, exist_ok=True)
    source_config = characterization_dir / "config.json"
    source_metrics = characterization_dir / "metrics.csv"
    source_checks = characterization_dir / "checks.json"
    source_resolution_budget = characterization_dir / "theoretical_resolution_budget.json"
    source_config.write_text("{}\n", encoding="utf-8")
    source_metrics.write_text("metric_name,metric_value\nmtf50,0.25\n", encoding="utf-8")
    source_checks.write_text('[{"status": "PASS"}]\n', encoding="utf-8")
    source_resolution_budget.write_text(
        '{"status": "PASS", "criterion": "rayleigh"}\n',
        encoding="utf-8",
    )

    geometry = OpticalBenchConfig()
    operating_point = {
        "stage": "characterization",
        "status": "PASS",
        "geometry": asdict(geometry),
        "geometry_hash": compute_config_hash(geometry),
        "config_hash": compute_config_hash({}),
        "selected_values": {
            "selection_metrics": {"edge_mtf50_cycles_per_pixel": 0.25},
        },
        "operating_point": {
            "focal_length": 0.1,
            "fourier_plane_pixel_size_x": 15.576171875e-6,
        },
        "source_config_path": source_config.relative_to(project_root).as_posix(),
        "source_metrics_path": source_metrics.relative_to(project_root).as_posix(),
        "source_checks_path": source_checks.relative_to(project_root).as_posix(),
        "source_resolution_budget_path": source_resolution_budget.relative_to(
            project_root
        ).as_posix(),
        "source_artifact_sha256": {
            source_config.relative_to(project_root).as_posix(): hashlib.sha256(
                source_config.read_bytes()
            ).hexdigest(),
            source_metrics.relative_to(project_root).as_posix(): hashlib.sha256(
                source_metrics.read_bytes()
            ).hexdigest(),
            source_checks.relative_to(project_root).as_posix(): hashlib.sha256(
                source_checks.read_bytes()
            ).hexdigest(),
            source_resolution_budget.relative_to(
                project_root
            ).as_posix(): hashlib.sha256(
                source_resolution_budget.read_bytes()
            ).hexdigest(),
        },
    }
    (project_root / DEFAULT_OPERATING_POINT).write_text(
        json.dumps(operating_point),
        encoding="utf-8",
    )


def test_load_protocol_inputs_verifies_portable_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉涓€娆¤皟鐢ㄥ嵆鍙杞藉苟鏍搁獙鏁版嵁涓庣墿鐞嗗伐浣滅偣
    """
    _write_archive(tmp_path, monkeypatch)

    inputs = load_protocol_inputs(project_root=tmp_path, device="cpu")

    assert inputs.project_root == tmp_path
    assert inputs.operating_point_path == tmp_path / DEFAULT_OPERATING_POINT
    assert inputs.split_manifest["schema_version"] == "restoration_fmd_split_v2"
    assert inputs.dataset_root == "data/raw"


def test_protocol_inputs_reject_a_dataset_root_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Formal training must read the same project tree whose image bytes were verified.
    """
    _write_archive(tmp_path, monkeypatch)
    inputs = load_protocol_inputs(project_root=tmp_path, device="cpu")

    with pytest.raises(ValueError, match="dataset root"):
        verify_protocol_inputs(
            replace(inputs, dataset_root=tmp_path / "alternate-data")
        )


def test_load_protocol_inputs_rejects_changed_clean_image(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉 manifest 鍐荤粨鍚庝慨鏀规暟鎹枃浠朵細闃绘柇姝ｅ紡璁粌
    """
    _write_archive(tmp_path, monkeypatch)
    changed_image = next((tmp_path / "data/raw/fmd/averaged").rglob("*.png"))
    changed_image.write_bytes(b"changed-after-freeze")

    with pytest.raises(ValueError, match="content hash mismatch"):
        load_protocol_inputs(project_root=tmp_path, device="cpu")


def test_load_protocol_inputs_rejects_broken_characterization_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉鐗╃悊宸ヤ綔鐐圭殑鏉ユ簮閰嶇疆銆佹寚鏍囧拰妫€鏌ュ繀椤诲叡鍚屽瓨鍦?    """
    _write_archive(tmp_path, monkeypatch)
    (tmp_path / DEFAULT_OPERATING_POINT).parent.joinpath("metrics.csv").unlink()

    with pytest.raises(ValueError, match="characterization source"):
        load_protocol_inputs(project_root=tmp_path, device="cpu")


def test_load_protocol_inputs_rejects_changed_characterization_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉琛ㄥ緛鏉ユ簮鍦ㄥ皝妗ｅ悗鍙戠敓鍙樺寲浼氶樆鏂寮忚缁?    """
    _write_archive(tmp_path, monkeypatch)
    metrics_path = (tmp_path / DEFAULT_OPERATING_POINT).parent / "metrics.csv"
    metrics_path.write_text("changed-after-freeze\n", encoding="utf-8")

    with pytest.raises(ValueError, match="characterization source hash mismatch"):
        load_protocol_inputs(project_root=tmp_path, device="cpu")


def test_load_protocol_inputs_rejects_changed_resolution_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The archived theoretical resolution budget is part of the physical gate.
    """
    _write_archive(tmp_path, monkeypatch)
    budget_path = (
        (tmp_path / DEFAULT_OPERATING_POINT).parent
        / "theoretical_resolution_budget.json"
    )
    budget_path.write_text("changed-after-freeze\n", encoding="utf-8")

    with pytest.raises(ValueError, match="characterization source hash mismatch"):
        load_protocol_inputs(project_root=tmp_path, device="cpu")

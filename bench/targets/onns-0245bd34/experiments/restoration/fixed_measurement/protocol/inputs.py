from __future__ import annotations

from collections.abc import Mapping
import json
import math
from pathlib import Path
from typing import cast

from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.fixed_measurement.evidence.integrity import sha256_file
from experiments.restoration.fixed_measurement.protocol.settings import ProtocolInputs
from experiments.restoration.fixed_measurement.learning.splits import (
    FMD_ARCHIVE_SPLIT_SCHEMA_VERSION,
    validate_split_manifest,
)


PROTOCOL_ASSET_DIRECTORY = Path(
    "experiments/restoration/fixed_measurement/protocol_assets"
)
DEFAULT_SPLIT_MANIFEST = PROTOCOL_ASSET_DIRECTORY / "fmd_split_manifest.json"
DEFAULT_OPERATING_POINT = (
    PROTOCOL_ASSET_DIRECTORY / "characterization" / "operating_point.json"
)

_EXPECTED_WAVELENGTH_M = 638e-9
_EXPECTED_FOCAL_LENGTH_M = 0.1
_EXPECTED_INPUT_PIXEL_PITCH_M = 8e-6
_EXPECTED_ARRAY_SIZE = 512
_EXPECTED_PHASE_MASK_SIZE = 512
_EXPECTED_SLM2_ACTIVE_SIZE = (1024, 1024)
_EXPECTED_SLM2_PIXEL_PITCH_M = 8e-6


def archived_training_device(
    *,
    project_root: str | Path,
    artifact_sha256: Mapping[str, object],
) -> str:
    """Read the uniform runtime identity recorded by the formal core archive."""
    root = Path(project_root).resolve()
    config_paths = sorted(
        path
        for path in artifact_sha256
        if isinstance(path, str) and path.endswith("/config.json")
    )
    devices: set[str] = set()
    for relative_path in config_paths:
        config_path = _project_path(root, relative_path)
        expected_hash = artifact_sha256[relative_path]
        if (
            not isinstance(expected_hash, str)
            or sha256_file(config_path) != expected_hash
        ):
            raise invalid_restoration_contract(
                f"archived Fixed configuration hash mismatch: {relative_path}"
            )
        config = _read_json_object(
            config_path,
            artifact_name="archived Fixed configuration",
        )
        basic = config.get("basic")
        device = basic.get("device") if isinstance(basic, Mapping) else None
        if not isinstance(device, str) or not device:
            raise invalid_restoration_contract(
                "archived Fixed configurations must record their device"
            )
        devices.add(device)
    if len(config_paths) != 36 or len(devices) != 1:
        raise invalid_restoration_contract(
            "the formal Fixed archive must contain one uniform device identity"
        )
    return devices.pop()


def load_protocol_inputs(
    *,
    project_root: str | Path,
    operating_point_path: str | Path = DEFAULT_OPERATING_POINT,
    split_manifest_path: str | Path = DEFAULT_SPLIT_MANIFEST,
    device: str = "auto",
) -> ProtocolInputs:
    """
    瑁呰浇骞舵牳楠屽浐瀹氭祴閲忚缁冩墍闇€鐨勫畬鏁村皝妗ｈ緭鍏?    """
    root = Path(project_root).resolve()
    resolved_operating_point = _project_path(root, operating_point_path)
    resolved_split_manifest = _project_path(root, split_manifest_path)
    split_manifest = _read_json_object(
        resolved_split_manifest,
        artifact_name="split manifest",
    )
    dataset_root = _archived_dataset_root(root, split_manifest)
    inputs = ProtocolInputs(
        project_root=root,
        operating_point_path=resolved_operating_point,
        split_manifest=split_manifest,
        dataset_root=dataset_root.relative_to(root).as_posix(),
        device=device,
    )
    verify_protocol_inputs(inputs)
    return inputs


def verify_protocol_inputs(inputs: ProtocolInputs) -> None:
    """
    鍦ㄤ换浣曟寮忚缁冨啓鐩樺墠澶嶆牳灏佹。鏁版嵁涓庣墿鐞嗘潵婧?    """
    project_root = Path(inputs.project_root).resolve()
    archived_dataset_root = _verify_split_archive(
        project_root,
        inputs.split_manifest,
    )
    configured_dataset_root = _project_path(project_root, inputs.dataset_root)
    if configured_dataset_root != archived_dataset_root:
        raise invalid_restoration_contract(
            "fixed-measurement dataset root must match the archived data tree"
        )
    _verify_operating_point_archive(
        project_root,
        Path(inputs.operating_point_path).resolve(),
    )


def _verify_split_archive(
    project_root: Path,
    manifest: Mapping[str, object],
) -> Path:
    validate_split_manifest(manifest)
    if manifest.get("schema_version") != FMD_ARCHIVE_SPLIT_SCHEMA_VERSION:
        raise invalid_restoration_contract(
            "fixed measurement requires an archival FMD split manifest"
        )
    dataset_root = _archived_dataset_root(project_root, manifest)
    source_root = _project_path(
        project_root,
        cast(str, manifest["source_dataset_root_hint"]),
    )
    records = cast(list[Mapping[str, object]], manifest["records"])
    for record in records:
        source_path = record.get("source_path")
        expected_hash = record.get("content_sha256")
        if not isinstance(source_path, str) or Path(source_path).is_absolute():
            raise invalid_restoration_contract(
                "fixed-measurement source paths must be project-relative"
            )
        resolved_source = _project_path(project_root, source_path)
        if not resolved_source.is_relative_to(source_root):
            raise invalid_restoration_contract(
                "fixed-measurement source image must belong to the archived FMD tree"
            )
        if not resolved_source.is_file():
            raise invalid_restoration_contract(
                f"fixed-measurement source image is missing: {source_path}"
            )
        if sha256_file(resolved_source) != expected_hash:
            raise invalid_restoration_contract(
                f"fixed-measurement content hash mismatch: {source_path}"
            )
    return dataset_root


def _archived_dataset_root(
    project_root: Path,
    manifest: Mapping[str, object],
) -> Path:
    source_root_hint = manifest.get("source_dataset_root_hint")
    if not isinstance(source_root_hint, str) or Path(source_root_hint).is_absolute():
        raise invalid_restoration_contract(
            "fixed-measurement source_dataset_root_hint must be project-relative"
        )
    source_root = _project_path(project_root, source_root_hint)
    if source_root.parts[-2:] != ("fmd", "averaged"):
        raise invalid_restoration_contract(
            "fixed-measurement FMD source root must end with fmd/averaged"
        )
    return source_root.parent.parent


def _verify_operating_point_archive(
    project_root: Path,
    operating_point_path: Path,
) -> None:
    payload = _read_json_object(
        operating_point_path,
        artifact_name="operating point",
    )
    if payload.get("stage") != "characterization" or payload.get("status") != "PASS":
        raise invalid_restoration_contract(
            "fixed-measurement operating point must be a PASS characterization"
        )
    geometry = payload.get("geometry")
    if not isinstance(geometry, Mapping):
        raise invalid_restoration_contract(
            "fixed-measurement operating point requires geometry"
        )
    if payload.get("geometry_hash") != compute_config_hash(geometry):
        raise invalid_restoration_contract(
            "fixed-measurement operating point geometry hash mismatch"
        )
    _verify_fixed_geometry(geometry, payload)

    selected_values = payload.get("selected_values")
    selection_metrics = (
        selected_values.get("selection_metrics")
        if isinstance(selected_values, Mapping)
        else None
    )
    if not isinstance(selection_metrics, Mapping) or not selection_metrics:
        raise invalid_restoration_contract(
            "fixed-measurement characterization metrics are missing"
        )

    source_hashes = payload.get("source_artifact_sha256")
    if not isinstance(source_hashes, Mapping) or not source_hashes:
        raise invalid_restoration_contract(
            "fixed-measurement characterization source hashes are missing"
        )
    source_paths: dict[str, Path] = {}
    for field_name in (
        "source_config_path",
        "source_metrics_path",
        "source_checks_path",
        "source_resolution_budget_path",
    ):
        field_value = payload.get(field_name)
        if not isinstance(field_value, str) or Path(field_value).is_absolute():
            raise invalid_restoration_contract(
                "fixed-measurement characterization source paths must be relative"
            )
        source_path = _project_path(project_root, field_value)
        if not source_path.is_file() or source_path.stat().st_size == 0:
            raise invalid_restoration_contract(
                f"fixed-measurement characterization source is missing: {field_value}"
            )
        if sha256_file(source_path) != source_hashes.get(field_value):
            raise invalid_restoration_contract(
                "fixed-measurement characterization source hash mismatch: "
                f"{field_value}"
            )
        source_paths[field_name] = source_path
    source_config = _read_json_object(
        source_paths["source_config_path"],
        artifact_name="characterization config",
    )
    if compute_config_hash(source_config) != payload.get("config_hash"):
        raise invalid_restoration_contract(
            "fixed-measurement characterization config hash mismatch"
        )
    checks = json.loads(source_paths["source_checks_path"].read_text(encoding="utf-8"))
    if (
        not isinstance(checks, list)
        or not checks
        or any(
            not isinstance(check, Mapping) or check.get("status") != "PASS"
            for check in checks
        )
    ):
        raise invalid_restoration_contract(
            "fixed-measurement characterization checks must all PASS"
        )


def _verify_fixed_geometry(
    geometry: Mapping[str, object],
    payload: Mapping[str, object],
) -> None:
    expected_values = {
        "wavelength": _EXPECTED_WAVELENGTH_M,
        "focal_length": _EXPECTED_FOCAL_LENGTH_M,
        "input_plane_pixel_size": _EXPECTED_INPUT_PIXEL_PITCH_M,
        "input_array_resolution": [_EXPECTED_ARRAY_SIZE, _EXPECTED_ARRAY_SIZE],
        "phase_mask_resolution": _EXPECTED_PHASE_MASK_SIZE,
        "slm2_active_resolution": list(_EXPECTED_SLM2_ACTIVE_SIZE),
        "slm2_pixel_size": _EXPECTED_SLM2_PIXEL_PITCH_M,
    }
    mismatches = {
        field_name: (expected, geometry.get(field_name))
        for field_name, expected in expected_values.items()
        if geometry.get(field_name) != expected
    }
    if mismatches:
        raise invalid_restoration_contract(
            f"fixed-measurement geometry mismatch: {mismatches}"
        )
    operating_point = payload.get("operating_point")
    if not isinstance(operating_point, Mapping):
        raise invalid_restoration_contract(
            "fixed-measurement operating point summary is missing"
        )
    expected_fourier_pitch = (
        _EXPECTED_WAVELENGTH_M
        * _EXPECTED_FOCAL_LENGTH_M
        / (_EXPECTED_ARRAY_SIZE * _EXPECTED_INPUT_PIXEL_PITCH_M)
    )
    measured_fourier_pitch = operating_point.get("fourier_plane_pixel_size_x")
    if not isinstance(measured_fourier_pitch, (int, float)) or not math.isclose(
        float(measured_fourier_pitch),
        expected_fourier_pitch,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise invalid_restoration_contract(
            "fixed-measurement Fourier-plane pitch must be 15.576171875 um"
        )


def _read_json_object(path: Path, *, artifact_name: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise invalid_restoration_contract(
            f"fixed-measurement {artifact_name} is unreadable: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise invalid_restoration_contract(
            f"fixed-measurement {artifact_name} must be a JSON object"
        )
    return payload


def _project_path(project_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    resolved = (
        candidate.resolve()
        if candidate.is_absolute()
        else (project_root / candidate).resolve()
    )
    if not resolved.is_relative_to(project_root):
        raise invalid_restoration_contract(
            f"fixed-measurement archive path escapes project root: {path}"
        )
    return resolved

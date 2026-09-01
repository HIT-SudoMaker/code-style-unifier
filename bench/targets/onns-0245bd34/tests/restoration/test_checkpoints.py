from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest
import torch
from torch import nn

from experiments.restoration.fixed_measurement.learning.backend import BackendConfig
from experiments.restoration.fixed_measurement.learning.checkpoints import (
    backend_payload,
    capture_rng_state,
    load_frontend_source_if_needed,
    restore_rng_state,
    save_checkpoint,
    verify_provenance,
)
from experiments.restoration.fixed_measurement.learning.config import (
    BasicConfig,
    FrontendSourceConfig,
    TrainingConfig,
)
from experiments.restoration.fixed_measurement.learning.connection import ConnectionConfig, build_connection


def _checkpoint_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "config_hash": "config-hash",
        "geometry_hash": "geometry-hash",
        "degradation_hash": "degradation-hash",
        "model_role": "frontend_only",
    }
    payload.update(overrides)
    return payload


def test_verify_provenance_passes_when_all_fields_match() -> None:
    """
    楠岃瘉鍏ㄩ儴鏉ユ簮瀛楁涓€鑷存椂鏍￠獙閫氳繃
    """
    checkpoint = _checkpoint_payload()
    expected = dict(checkpoint)

    verify_provenance(
        checkpoint,
        expected,
        fields=("config_hash", "geometry_hash", "degradation_hash", "model_role"),
    )


def test_verify_provenance_accepts_legacy_passthrough_default() -> None:
    """
    楠岃瘉鏃х増 NAFNet 韬唤榛樿鍏抽棴鍙涔犵洿閫氬鐩?    """
    checkpoint = {
        "backend": {
            "family": "restoration_native",
            "model_name": "nafnet_s",
            "residual_learning": True,
            "trainable_passthrough_gain": False,
        }
    }

    verify_provenance(
        checkpoint,
        {"backend": backend_payload(BackendConfig(model_name="nafnet_s"))},
        fields=("backend",),
    )


@pytest.mark.parametrize(
    "field_name",
    ("config_hash", "geometry_hash", "degradation_hash", "model_role"),
)
def test_verify_provenance_raises_on_each_field_mismatch(field_name: str) -> None:
    """
    楠岃瘉浠讳竴鏉ユ簮瀛楁涓嶄竴鑷存椂鏍￠獙澶辫触
    """
    checkpoint = _checkpoint_payload(**{field_name: "checkpoint-value"})
    expected = _checkpoint_payload(**{field_name: "expected-value"})

    with pytest.raises(ValueError, match=field_name):
        verify_provenance(
            checkpoint,
            expected,
            fields=("config_hash", "geometry_hash", "degradation_hash", "model_role"),
        )


def test_verify_provenance_raises_on_cross_equality_mismatch() -> None:
    """
    楠岃瘉璺ㄦ潵婧愮瓑寮忎笉鎴愮珛鏃舵牎楠屽け璐?    """
    checkpoint = _checkpoint_payload(geometry_hash="source-geometry-hash")
    expected = dict(checkpoint)

    with pytest.raises(ValueError, match="source_vs_target_geometry_hash"):
        verify_provenance(
            checkpoint,
            expected,
            fields=("geometry_hash",),
            cross_equality=(
                (
                    "source_vs_target_geometry_hash",
                    "source-geometry-hash",
                    "target-geometry-hash",
                ),
            ),
        )


def test_verify_provenance_passes_cross_equality_when_equal() -> None:
    """
    楠岃瘉璺ㄦ潵婧愮瓑寮忔垚绔嬫椂鏍￠獙閫氳繃
    """
    checkpoint = _checkpoint_payload(geometry_hash="shared-geometry-hash")
    expected = dict(checkpoint)

    verify_provenance(
        checkpoint,
        expected,
        fields=("geometry_hash",),
        cross_equality=(
            (
                "source_vs_target_geometry_hash",
                "shared-geometry-hash",
                "shared-geometry-hash",
            ),
        ),
    )


def test_verify_provenance_cross_equality_compares_values_not_field_names() -> None:
    """
    楠岃瘉璺ㄦ潵婧愮瓑寮忔瘮杈冨瓧娈靛€艰€岄潪瀛楁鍚?    """
    checkpoint = _checkpoint_payload(geometry_hash="source-hash")

    with pytest.raises(ValueError, match="source_vs_target_geometry_hash"):
        verify_provenance(
            checkpoint,
            dict(checkpoint),
            fields=("geometry_hash",),
            cross_equality=(("source_vs_target_geometry_hash", "source-hash", "target-hash"),),
        )


def test_verify_provenance_checks_merged_benchmark_fields() -> None:
    """
    楠岃瘉鍚堝苟鍩哄噯鐨勫畬鏁存潵婧愬瓧娈?    """
    checkpoint: Mapping[str, object] = {
        "config_hash": "config-hash",
        "geometry_hash": "geometry-hash",
        "degradation_hash": "degradation-hash",
        "model_role": "joint_optical_frontend_digital_backend",
        "backend": {
            "family": "restoration_native",
            "model_name": "nafnet_s",
            "residual_learning": True,
        },
        "connection": {
            "mode": "optical_residual_gate",
            "initial_optical_residual_gate": 0.75,
        },
        "phase_parameterization": "sigmoid",
        "phase_initialization": "uniform",
    }
    expected = dict(checkpoint)
    fields = (
        "config_hash",
        "geometry_hash",
        "degradation_hash",
        "model_role",
        "backend",
        "connection",
        "phase_parameterization",
        "phase_initialization",
    )

    verify_provenance(checkpoint, expected, fields=fields)
    with pytest.raises(ValueError, match="backend"):
        verify_provenance(
            {
                **checkpoint,
                "backend": {
                    "family": "restoration_native",
                    "model_name": "nafnet_m",
                    "residual_learning": True,
                },
            },
            expected,
            fields=fields,
        )


def test_verify_provenance_rejects_missing_canonical_backend_key() -> None:
    """
    楠岃瘉缂哄け鏁板瓧鍚庣閿笉绛変环浜庢樉寮忕┖鍊?    """
    checkpoint = _checkpoint_payload()
    expected = {**checkpoint, "backend": None}

    with pytest.raises(ValueError, match="backend"):
        verify_provenance(checkpoint, expected, fields=("backend",))


def test_save_checkpoint_persists_nested_backend_identity_only(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉妫€鏌ョ偣浠呬繚瀛樺祵濂楁暟瀛楀悗绔韩浠?    """
    model = nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    config = TrainingConfig(
        basic=BasicConfig(project_root=tmp_path, run_name="backend"),
        model_role="backend_only",
        backend=BackendConfig(model_name="nafnet_m", residual_learning=False),
        trainable_parameters=("backend",),
    )
    path = tmp_path / "last.pt"

    save_checkpoint(
        path,
        model,
        optimizer,
        config,
        epoch=1,
        geometry_hash="geometry-hash",
        degradation_hash="degradation-hash",
        metrics={"loss_total": 0.5},
    )

    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    assert checkpoint["backend"] == {
        "family": "restoration_native",
        "model_name": "nafnet_m",
        "residual_learning": False,
    }
    assert "backend_family" not in checkpoint
    assert "backend_model" not in checkpoint


def test_save_checkpoint_persists_frontend_backend_none(tmp_path: Path) -> None:
    """
    楠岃瘉绾墠绔鏌ョ偣淇濆瓨绌烘暟瀛楀悗绔?    """
    model = nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    config = TrainingConfig(
        basic=BasicConfig(project_root=tmp_path, run_name="frontend"),
        model_role="frontend_only",
        backend=None,
    )
    path = tmp_path / "frontend.pt"

    save_checkpoint(
        path,
        model,
        optimizer,
        config,
        epoch=1,
        geometry_hash="geometry-hash",
        degradation_hash="degradation-hash",
        metrics={},
    )

    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    assert checkpoint["backend"] is None


def test_save_checkpoint_persists_optical_residual_gate_identity(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉妫€鏌ョ偣鍚屾椂淇濆瓨鐩撮€氬鐩婇厤缃拰褰撳墠鏁板€?    """
    model = nn.Module()
    model.connection = build_connection(
        ConnectionConfig.with_optical_residual_gate(initial_gate=0.99)
    )
    model.backend = nn.Linear(1, 1)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    config = TrainingConfig(
        basic=BasicConfig(project_root=tmp_path, run_name="optical_gate"),
        model_role="frozen_optical_frontend_digital_backend",
        backend=BackendConfig(model_name="nafnet_s"),
        frontend_source=FrontendSourceConfig(
            checkpoint_path=tmp_path / "frontend.pt",
            run_id="frontend-run",
            source_config_hash="source-config-hash",
            source_geometry_hash="geometry-hash",
            source_degradation_hash="degradation-hash",
        ),
        connection=ConnectionConfig.with_optical_residual_gate(initial_gate=0.99),
        trainable_parameters=("connection", "backend"),
    )
    path = tmp_path / "optical_gate.pt"

    save_checkpoint(
        path,
        model,
        optimizer,
        config,
        epoch=1,
        geometry_hash="geometry-hash",
        degradation_hash="degradation-hash",
        metrics={"loss_total": 0.5},
    )

    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    assert checkpoint["connection"]["mode"] == "optical_residual_gate"
    assert checkpoint["connection"]["initial_optical_residual_gate"] == pytest.approx(
        0.99
    )
    assert checkpoint["mechanism_parameters"] == {
        "optical_residual_gate": pytest.approx(0.99)
    }
    assert "backend_family" not in checkpoint
    assert "backend_model" not in checkpoint


def test_restore_rng_state_rejects_non_byte_cuda_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉CUDA闅忔満鐘舵€佸繀椤讳繚鎸丅yteTensor濂戠害
    """
    payload = capture_rng_state()
    payload["torch_cuda"] = [torch.zeros(16, dtype=torch.float32)]
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)

    with pytest.raises(ValueError, match="CUDA"):
        restore_rng_state(payload)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is required")
def test_restore_rng_state_moves_cuda_checkpoint_state_to_cpu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    楠岃瘉鎸塁UDA璁惧鍔犺浇鐨勬鏌ョ偣闅忔満鐘舵€佷細杞洖CPU ByteTensor
    """
    payload = capture_rng_state()
    payload["torch_cuda"] = [
        torch.cuda.get_rng_state().to(device="cuda")
    ]
    restored_states: list[torch.Tensor] = []

    def record_states(states: list[torch.Tensor]) -> None:
        """
        璁板綍浜ょ粰 CUDA 闅忔満鐘舵€佹仮澶嶆帴鍙ｇ殑寮犻噺
        """
        restored_states.extend(states)

    monkeypatch.setattr(torch.cuda, "set_rng_state_all", record_states)

    restore_rng_state(payload)

    assert len(restored_states) == 1
    assert restored_states[0].dtype == torch.uint8
    assert restored_states[0].device.type == "cpu"


def test_load_frontend_source_rejects_retired_flat_backend_identity(
    tmp_path: Path,
) -> None:
    """
    楠岃瘉鍓嶇鏉ユ簮鎷掔粷鏈縼绉荤殑鎵佸钩鍚庣韬唤
    """
    path = tmp_path / "frontend.pt"
    torch.save(
        {
            "config_hash": "config-hash",
            "geometry_hash": "geometry-hash",
            "degradation_hash": "degradation-hash",
            "model_role": "frontend_only",
            "backend_family": "none",
            "backend_model": "none",
            "model_state_dict": {},
        },
        path,
    )
    config = TrainingConfig(
        model_role="frozen_optical_frontend_digital_backend",
        frontend_source={
            "checkpoint_path": path,
            "run_id": "frontend-run",
            "source_config_hash": "config-hash",
            "source_geometry_hash": "geometry-hash",
            "source_degradation_hash": "degradation-hash",
        },
        trainable_parameters=("backend",),
    )

    with pytest.raises(ValueError, match="outside the sealed Fixed protocol"):
        load_frontend_source_if_needed(
            nn.Module(),
            config,
            geometry_hash="geometry-hash",
            target_degradation_hash="degradation-hash",
        )

from __future__ import annotations

import pytest
import torch

from experiments.restoration.fixed_measurement.evidence.training_artifacts import compute_config_hash
from experiments.restoration.fixed_measurement.learning.connection import (
    ConnectionConfig,
    DegradedImageConnection,
    OpticalResidualGateConnection,
    SerialOpticalRestorationConnection,
    build_connection,
)


def test_connection_config_defaults_to_serial() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    config = ConnectionConfig()

    assert config.mode == "serial"
    assert config.optical_residual_gate_logit == 0.0


def test_serial_connection_uses_one_canonical_config_hash_identity() -> None:
    """The serial connection hashes to its declared canonical payload."""
    canonical_payload = {
        "mode": "serial",
        "scalar_gate_initial_logit": 0.0,
    }

    assert compute_config_hash(ConnectionConfig()) == compute_config_hash(
        canonical_payload
    )


@pytest.mark.parametrize(
    "mode",
    ["serial", "degraded_image", "optical_residual_gate"],
)
def test_connection_config_accepts_supported_modes(mode: str) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    ConnectionConfig(mode=mode).validate()


def test_connection_config_rejects_legacy_aliases() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="optical_residual_gate"):
        ConnectionConfig(mode="relay")


@pytest.mark.parametrize(
    "optical_residual_gate_logit",
    [float("nan"), float("inf"), float("-inf")],
)
def test_connection_config_rejects_nonfinite_optical_residual_gate_logit(
    optical_residual_gate_logit: float,
) -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    with pytest.raises(ValueError, match="finite"):
        ConnectionConfig(
            mode="optical_residual_gate",
            optical_residual_gate_logit=optical_residual_gate_logit,
        )


def test_build_connection_uses_mode() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    assert isinstance(
        build_connection(ConnectionConfig("serial")),
        SerialOpticalRestorationConnection,
    )
    assert isinstance(
        build_connection(ConnectionConfig("degraded_image")),
        DegradedImageConnection,
    )
    assert isinstance(
        build_connection(ConnectionConfig.with_optical_residual_gate()),
        OpticalResidualGateConnection,
    )


def test_optical_residual_gate_interpolates_from_degraded_to_optical() -> None:
    """
    鏍￠獙鐩爣琛屼负
    """
    degraded_image = torch.full((1, 1, 4, 4), 0.25)
    optical_restoration_image = torch.full((1, 1, 4, 4), 0.75)
    connection = build_connection(
        ConnectionConfig.with_optical_residual_gate(initial_gate=0.75)
    )

    output = connection(degraded_image, optical_restoration_image)

    expected = torch.full_like(degraded_image, 0.625)
    assert isinstance(connection, OpticalResidualGateConnection)
    assert torch.allclose(output, expected)
    assert connection.optical_residual_gate.item() == pytest.approx(0.75)
    assert connection.trainable_parameter_names() == ["connection"]


def test_optical_residual_gate_intervention_restores_learned_gate() -> None:
    """
    鏍￠獙闆堕棬涓庡崟浣嶉棬骞查涓ユ牸鍛戒腑绔偣涓斾笉浼氭敼鍙樺涔犵粨鏋?    """
    degraded_image = torch.full((1, 1, 2, 2), 0.25)
    optical_restoration_image = torch.full((1, 1, 2, 2), 0.75)
    connection = build_connection(
        ConnectionConfig.with_optical_residual_gate(initial_gate=0.75)
    )
    assert isinstance(connection, OpticalResidualGateConnection)

    with connection.override_optical_residual_gate(0.0):
        zero_gate_image = connection(degraded_image, optical_restoration_image)
        assert connection.optical_residual_gate.item() == 0.0
    with connection.override_optical_residual_gate(1.0):
        one_gate_image = connection(degraded_image, optical_restoration_image)
        assert connection.optical_residual_gate.item() == 1.0

    torch.testing.assert_close(zero_gate_image, degraded_image)
    torch.testing.assert_close(one_gate_image, optical_restoration_image)
    assert connection.optical_residual_gate.item() == pytest.approx(0.75)


@pytest.mark.parametrize("initial_gate", [0.0, 1.0, -0.1, 1.1])
def test_optical_residual_gate_requires_open_unit_interval(
    initial_gate: float,
) -> None:
    """
    楠岃瘉鍙井闂ㄦ帶鍒濆€煎繀椤讳弗鏍间綅浜庨浂鍜屼竴涔嬮棿
    """
    with pytest.raises(ValueError, match="initial_gate"):
        ConnectionConfig.with_optical_residual_gate(initial_gate=initial_gate)


@pytest.mark.parametrize("logit", [-1000.0, 1000.0])
def test_initial_optical_residual_gate_is_stable_for_extreme_logits(
    logit: float,
) -> None:
    """
    鏍￠獙浠绘剰鏈夐檺 logit 鍧囩ǔ瀹氭槧灏勫埌寮€鍗曚綅鍖洪棿
    """
    gate = ConnectionConfig(
        mode="optical_residual_gate",
        optical_residual_gate_logit=logit,
    ).initial_optical_residual_gate

    assert gate is not None
    assert 0.0 < gate < 1.0


def test_dual_channel_stacks_degraded_optical_and_residual() -> None:
    """
    楠岃瘉鍙屾祦杩炴帴渚濇鍫嗗彔閫€鍖栧浘鍍忋€佸厜瀛﹀浘鍍忎笌娈嬪樊
    """
    connection = build_connection(ConnectionConfig(mode="dual_channel"))
    degraded = torch.rand(2, 1, 8, 8)
    optical = torch.rand(2, 1, 8, 8)
    out = connection(degraded, optical)
    assert out.shape == (2, 3, 8, 8)
    torch.testing.assert_close(out[:, 0:1], degraded)
    torch.testing.assert_close(out[:, 1:2], optical)
    torch.testing.assert_close(out[:, 2:3], optical - degraded)


def test_dual_channel_optical_zeroed_keeps_degraded_only() -> None:
    """
    楠岃瘉鍏夊缃浂瀵圭収浠呬繚鐣欓€€鍖栧浘鍍忛€氶亾
    """
    connection = build_connection(ConnectionConfig(mode="dual_channel_optical_zeroed"))
    degraded = torch.rand(2, 1, 8, 8)
    optical = torch.rand(2, 1, 8, 8)
    out = connection(degraded, optical)
    assert out.shape == (2, 3, 8, 8)
    torch.testing.assert_close(out[:, 0:1], degraded)
    assert torch.count_nonzero(out[:, 1:3]) == 0

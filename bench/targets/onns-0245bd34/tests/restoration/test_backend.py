from __future__ import annotations

import pytest
import torch

from experiments.restoration.fixed_measurement.learning.backend import BackendConfig, build_restoration_backend
from experiments.restoration.fixed_measurement.learning.backends.nafnet import NAFNET_MODEL_SPECS


def test_backend_config_defaults_to_nafnet_s() -> None:
    """
    Verify backend config defaults to the small NAFNet preset.
    """
    config = BackendConfig()

    assert config.family == "restoration_native"
    assert config.model_name == "nafnet_s"


def test_backend_config_accepts_nafnet_scales() -> None:
    """
    Verify backend config accepts each project NAFNet scale.
    """
    assert BackendConfig(model_name="nafnet_s").model_name == "nafnet_s"
    assert BackendConfig(model_name="nafnet_m").model_name == "nafnet_m"


def test_backend_config_rejects_invalid_backend_values() -> None:
    """
    Verify backend config rejects unknown family and model values.
    """
    with pytest.raises(ValueError, match="family"):
        BackendConfig(family="invalid_family")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="model_name"):
        BackendConfig(model_name="unknown_model")  # type: ignore[arg-type]


def test_build_restoration_backend_returns_single_channel_model() -> None:
    """
    Verify the backend factory returns a clamped single-channel model.
    """
    model = build_restoration_backend(BackendConfig(model_name="nafnet_s"))
    image = torch.rand(2, 1, 32, 32)

    output = model(image)

    assert output.shape == image.shape
    assert torch.all(output >= 0.0)
    assert torch.all(output <= 1.0)


def test_backend_config_rejects_removed_passthrough_gain() -> None:
    """
    楠岃瘉鍏抽棴娈嬪樊鎹峰緞鏃朵笉鑳藉０鏄庡彲璁粌鍏夊鐩撮€氬鐩?    """
    with pytest.raises(TypeError, match="trainable_passthrough_gain"):
        BackendConfig(
            model_name="nafnet_s",
            residual_learning=False,
            trainable_passthrough_gain=True,
        )


def test_build_restoration_backend_preserves_non_divisible_input_shape() -> None:
    """
    Verify NAFNet pads and crops non-divisible spatial sizes.
    """
    model = build_restoration_backend(BackendConfig(model_name="nafnet_s"))
    image = torch.rand(1, 1, 33, 47)

    output = model(image)

    assert output.shape == image.shape
    assert torch.all(output >= 0.0)
    assert torch.all(output <= 1.0)


def test_builder_accepts_and_ignores_physics_kwargs_for_nafnet() -> None:
    """
    Verify the canonical builder accepts physics kwargs that NAFNet ignores.
    """
    model = build_restoration_backend(
        BackendConfig(model_name="nafnet_s"),
        defocus_operator=None,
        reference_arm=None,
    )

    assert model.__class__.__name__ == "NafNetRestorationBackend"


def test_nafnet_specs_are_ordered_by_capacity() -> None:
    """
    Verify project NAFNet presets increase by channel capacity.
    """
    widths = [
        NAFNET_MODEL_SPECS["nafnet_s"].width,
        NAFNET_MODEL_SPECS["nafnet_m"].width,
    ]

    assert widths == sorted(widths)
    assert len(set(widths)) == 2

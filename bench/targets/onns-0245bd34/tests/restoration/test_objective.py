from __future__ import annotations

import math

import pytest
import torch

from experiments.restoration.fixed_measurement.learning.objective import (
    frequency_loss,
    phase_smoothness_loss,
    restoration_loss,
)
from experiments.restoration.metrics import normalize_intensity


def test_normalize_intensity_fixed_dataset_level_uses_scale() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    image = torch.full((1, 1), 2.0, dtype=torch.float32)

    normalized = normalize_intensity(
        image,
        policy="fixed_dataset_level",
        scale=4.0,
    )

    assert torch.allclose(normalized, torch.full_like(image, 0.5))


def test_per_image_min_max_is_supported_for_diagnostics() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    image = torch.tensor([[[[2.0, 4.0]]]], dtype=torch.float32)

    normalized = normalize_intensity(image, policy="per_image_min_max")

    assert torch.allclose(
        normalized,
        torch.tensor([[[[0.0, 1.0]]]], dtype=torch.float32),
    )


def test_phase_smoothness_respects_wrap_boundary() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    phase = torch.tensor([[0.0, 2.0 * math.pi - 1e-4]], dtype=torch.float32)

    loss = phase_smoothness_loss(phase)

    assert loss < 1e-6


def test_frequency_loss_is_zero_for_identical_images() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    image = torch.ones((8, 8), dtype=torch.float32)

    loss = frequency_loss(image, image)

    assert loss == torch.tensor(0.0)


def test_frequency_loss_scale_is_stable_across_resolutions() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    generator = torch.Generator().manual_seed(1234)
    small_error = torch.randn((8, 8), generator=generator, dtype=torch.float32)
    large_error = torch.randn((16, 16), generator=generator, dtype=torch.float32)

    small_loss = frequency_loss(small_error, torch.zeros_like(small_error))
    large_loss = frequency_loss(large_error, torch.zeros_like(large_error))

    assert torch.isclose(large_loss, small_loss, rtol=0.35)


def test_restoration_loss_returns_named_components() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    image = torch.ones((1, 1, 8, 8), dtype=torch.float32)
    phase = torch.zeros((1, 1, 8, 8), dtype=torch.float32)

    losses = restoration_loss(image, image, phase=phase)

    assert set(losses) == {
        "loss_total",
        "loss_l1",
        "loss_ssim",
        "loss_frequency",
        "phase_smoothness",
    }
    assert all(isinstance(value, torch.Tensor) for value in losses.values())
    assert torch.isclose(losses["loss_total"], torch.tensor(0.0))


def test_restoration_loss_preserves_prediction_and_phase_gradients() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    prediction = torch.linspace(0.0, 1.0, steps=16, dtype=torch.float32).reshape(1, 1, 4, 4)
    prediction.requires_grad_()
    target = torch.zeros_like(prediction)
    phase = torch.linspace(0.0, 1.0, steps=16, dtype=torch.float32).reshape(1, 1, 4, 4)
    phase.requires_grad_()

    restoration_loss(prediction, target, phase=phase)["loss_total"].backward()

    assert prediction.grad is not None
    assert phase.grad is not None
    assert bool(torch.isfinite(prediction.grad).all())
    assert bool(torch.isfinite(phase.grad).all())


@pytest.mark.parametrize("policy", ["fixed_dataset_level", "characterization_calibrated_gain"])
@pytest.mark.parametrize("scale", [None, 0.0, -1.0, math.nan, math.inf])
def test_normalize_intensity_rejects_invalid_required_scales(
    policy: str,
    scale: float | None,
) -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    image = torch.ones((2, 2), dtype=torch.float32)

    with pytest.raises(ValueError, match="scale"):
        normalize_intensity(image, policy=policy, scale=scale)


def test_normalize_intensity_rejects_unknown_policy() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    image = torch.ones((2, 2), dtype=torch.float32)

    with pytest.raises(ValueError, match="unknown"):
        normalize_intensity(image, policy="sample_peak")


def test_frequency_loss_rejects_mismatched_shapes() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    prediction = torch.ones((4, 4), dtype=torch.float32)
    target = torch.ones((4, 5), dtype=torch.float32)

    with pytest.raises(ValueError, match="compatible"):
        frequency_loss(prediction, target)


def test_restoration_loss_rejects_negative_weights() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    image = torch.ones((4, 4), dtype=torch.float32)
    phase = torch.zeros((4, 4), dtype=torch.float32)

    with pytest.raises(ValueError, match="nonnegative"):
        restoration_loss(image, image, phase=phase, image_l1_weight=-1.0)


def test_phase_smoothness_handles_single_pixel_phase() -> None:
    """
    鏍￠獙璁粌鐩爣濂戠害
    """
    phase = torch.zeros((1, 1), dtype=torch.float32)

    loss = phase_smoothness_loss(phase)

    assert loss == torch.tensor(0.0)

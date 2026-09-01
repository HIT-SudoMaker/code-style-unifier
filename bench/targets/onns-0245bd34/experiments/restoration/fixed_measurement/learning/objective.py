from __future__ import annotations

import math
from numbers import Real

import torch
import torch.nn.functional as functional

from experiments.restoration.errors import invalid_restoration_contract


def _tensor(name: str, value: torch.Tensor) -> torch.Tensor:
    if not isinstance(value, torch.Tensor):
        raise invalid_restoration_contract(f"{name} must be a torch.Tensor")
    if value.numel() == 0:
        raise invalid_restoration_contract(f"{name} must not be empty")
    if not bool(torch.isfinite(value).all()):
        raise invalid_restoration_contract(f"{name} must contain only finite values")
    if torch.is_floating_point(value):
        return value
    return value.to(dtype=torch.float32)


def _compatible_tensors(**tensors: torch.Tensor) -> dict[str, torch.Tensor]:
    converted = {name: _tensor(name, value) for name, value in tensors.items()}
    shapes = {tuple(value.shape) for value in converted.values()}
    if len(shapes) != 1:
        raise invalid_restoration_contract("tensors must have compatible shapes")
    return converted


def _nonnegative_weight(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise invalid_restoration_contract(
            f"{name} must be a nonnegative finite real number"
        )
    numeric_value = float(value)
    if not math.isfinite(numeric_value) or numeric_value < 0.0:
        raise invalid_restoration_contract(
            f"{name} must be a nonnegative finite real number"
        )
    return numeric_value


def _spatial_dims(tensor: torch.Tensor) -> tuple[int, ...]:
    if tensor.ndim == 0:
        return ()
    if tensor.ndim == 1:
        return (0,)
    return (-2, -1)


def _per_image_dims(tensor: torch.Tensor) -> tuple[int, ...]:
    if tensor.ndim >= 4:
        return tuple(range(1, tensor.ndim))
    return tuple(range(tensor.ndim))


def _ssim_loss(prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    tensors = _compatible_tensors(prediction=prediction, target=target)
    prediction_tensor = tensors["prediction"]
    target_tensor = tensors["target"]
    dims = _per_image_dims(prediction_tensor)
    c1 = 0.01**2
    c2 = 0.03**2
    prediction_mean = torch.mean(prediction_tensor, dim=dims, keepdim=True)
    target_mean = torch.mean(target_tensor, dim=dims, keepdim=True)
    prediction_delta = prediction_tensor - prediction_mean
    target_delta = target_tensor - target_mean
    prediction_variance = torch.mean(prediction_delta.square(), dim=dims, keepdim=True)
    target_variance = torch.mean(target_delta.square(), dim=dims, keepdim=True)
    covariance = torch.mean(prediction_delta * target_delta, dim=dims, keepdim=True)
    numerator = (2.0 * prediction_mean * target_mean + c1) * (2.0 * covariance + c2)
    denominator = (prediction_mean.square() + target_mean.square() + c1) * (
        prediction_variance + target_variance + c2
    )
    score = torch.clamp(numerator / denominator, min=-1.0, max=1.0)
    return 1.0 - torch.mean(score)


def frequency_loss(prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """
    实现训练目标辅助逻辑
    """
    tensors = _compatible_tensors(prediction=prediction, target=target)
    prediction_tensor = tensors["prediction"]
    target_tensor = tensors["target"]
    dims = _spatial_dims(prediction_tensor)
    if not dims:
        return functional.l1_loss(prediction_tensor.abs(), target_tensor.abs())
    prediction_magnitude = torch.abs(torch.fft.fftn(prediction_tensor, dim=dims, norm="ortho"))
    target_magnitude = torch.abs(torch.fft.fftn(target_tensor, dim=dims, norm="ortho"))
    return functional.l1_loss(prediction_magnitude, target_magnitude)


def phase_smoothness_loss(phase: torch.Tensor) -> torch.Tensor:
    """
    实现训练目标辅助逻辑
    """
    phase_tensor = _tensor("phase", phase)
    dims = [
        dimension
        for dimension in _spatial_dims(phase_tensor)
        if phase_tensor.shape[dimension] > 1
    ]
    if not dims:
        return phase_tensor.sum() * 0.0

    phasor = torch.exp(1j * phase_tensor)
    direction_losses = []
    for dimension in dims:
        difference = torch.diff(phasor, dim=dimension)
        direction_losses.append(difference.abs().square().mean())
    return torch.stack(direction_losses).mean()


def restoration_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    *,
    phase: torch.Tensor | None = None,
    image_l1_weight: float = 1.0,
    image_ssim_weight: float = 1.0,
    frequency_weight: float = 1.0,
    phase_smoothness_weight: float = 1.0,
) -> dict[str, torch.Tensor]:
    """
    实现训练目标辅助逻辑
    """
    tensors = _compatible_tensors(prediction=prediction, target=target)
    prediction_tensor = tensors["prediction"]
    target_tensor = tensors["target"]
    l1_weight = _nonnegative_weight("image_l1_weight", image_l1_weight)
    ssim_weight = _nonnegative_weight("image_ssim_weight", image_ssim_weight)
    frequency_loss_weight = _nonnegative_weight("frequency_weight", frequency_weight)
    phase_loss_weight = _nonnegative_weight("phase_smoothness_weight", phase_smoothness_weight)

    image_l1 = functional.l1_loss(prediction_tensor, target_tensor)
    image_ssim = _ssim_loss(prediction_tensor, target_tensor)
    image_frequency = frequency_loss(prediction_tensor, target_tensor)
    if phase is None:
        phase_smoothness = prediction_tensor.sum() * 0.0
    else:
        phase_smoothness = phase_smoothness_loss(phase)

    total = (
        (l1_weight * image_l1)
        + (ssim_weight * image_ssim)
        + (frequency_loss_weight * image_frequency)
        + (phase_loss_weight * phase_smoothness)
    )
    return {
        "loss_total": total,
        "loss_l1": image_l1,
        "loss_ssim": image_ssim,
        "loss_frequency": image_frequency,
        "phase_smoothness": phase_smoothness,
    }

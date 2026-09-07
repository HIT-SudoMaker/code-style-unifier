from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import math
from typing import TypedDict

import torch
from torch.utils.data import DataLoader

from experiments.restoration.fixed_measurement.learning.config import TrainingConfig
from experiments.restoration.fixed_measurement.learning.data_loading import (
    degraded_from_batch,
    ensure_batched_field,
    target_from_batch,
)
from experiments.restoration.errors import invalid_restoration_contract
from experiments.restoration.metrics import (
    energy_throughput,
    normalize_intensity,
    psnr,
    ssim_global,
)
from experiments.restoration.fixed_measurement.learning.model_assembly import (
    _effective_phase_for_model,
    optical_residual_gate_for_model,
    _phase_offset_reference_for_model,
)
from experiments.restoration.fixed_measurement.learning.objective import restoration_loss


class EpochRow(TypedDict):
    """
    鎻忚堪鍗曡疆璁粌鎴栭獙璇佹寚鏍?    """

    epoch: int
    split: str
    optimizer_updates: int
    loss_total: float
    loss_l1: float
    loss_ssim: float
    loss_frequency: float
    phase_smoothness: float
    psnr_raw: float
    ssim_raw: float
    psnr_normalized: float
    ssim_normalized: float
    energy_throughput: float
    clipping_ratio: float
    learning_rate: float
    phase_offset_reference: float | None
    optical_residual_gate: float | None
    operating_point_hash: str
    status: str


@dataclass(slots=True)
class GradientAccumulationState:
    """
    鍦ㄦ暟鎹姞杞借疆娆′箣闂存壙鎺ヤ弗鏍肩殑鏈夋晥鎵归噺
    """

    pending_samples: int = 0


def run_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    config: TrainingConfig,
    device: torch.device,
    *,
    epoch: int,
    split: str,
    optimizer: torch.optim.Optimizer | None,
    operating_point_hash: str,
    optimizer_update_start: int = 0,
    optimizer_update_limit: int | None = None,
    gradient_accumulation: GradientAccumulationState | None = None,
) -> EpochRow:
    """
    鎵ц涓€杞鍘熻缁冩垨楠岃瘉
    """
    is_train = optimizer is not None
    model.train(is_train)
    totals: dict[str, float] = {
        "loss_total": 0.0,
        "loss_l1": 0.0,
        "loss_ssim": 0.0,
        "loss_frequency": 0.0,
        "phase_smoothness": 0.0,
        "psnr_raw": 0.0,
        "ssim_raw": 0.0,
        "psnr_normalized": 0.0,
        "ssim_normalized": 0.0,
        "energy_throughput": 0.0,
        "clipping_ratio": 0.0,
    }
    sample_count = 0
    optimizer_updates = optimizer_update_start
    pending_samples = 0
    if is_train:
        if config.effective_batch_size is None:
            optimizer.zero_grad(set_to_none=True)
        else:
            if gradient_accumulation is None:
                raise invalid_restoration_contract(
                    "effective-batch training requires gradient accumulation state"
                )
            pending_samples = gradient_accumulation.pending_samples
            if not 0 <= pending_samples < config.effective_batch_size:
                raise invalid_restoration_contract(
                    "pending gradient samples must be below effective batch size"
                )
            if pending_samples == 0:
                optimizer.zero_grad(set_to_none=True)
    context = torch.enable_grad() if is_train else torch.no_grad()
    with context:
        for batch in loader:
            target_raw = target_from_batch(batch).to(device=device, dtype=torch.float32)
            if config.model_role == "backend_only":
                model_input = degraded_image_from_batch(batch).to(
                    device=device,
                    dtype=torch.float32,
                )
                prediction_raw = model(model_input)
                input_intensity = model_input
                batch_size = int(model_input.shape[0])
                phase = None
            else:
                input_field = ensure_batched_field(batch["input_field"]).to(device)
                prediction_raw = model(input_field)
                input_intensity = input_field.abs().square().real
                batch_size = int(input_field.shape[0])
                phase = _effective_phase_for_model(model)
            prediction_normalized = normalize_intensity(
                prediction_raw,
                policy=config.intensity_normalization_policy,
                scale=1.0,
            )
            target_normalized = normalize_intensity(
                target_raw,
                policy=config.intensity_normalization_policy,
                scale=1.0,
            )
            losses = restoration_loss(
                prediction_normalized,
                target_normalized,
                phase=phase,
                image_l1_weight=config.loss_l1_weight,
                image_ssim_weight=config.loss_ssim_weight,
                frequency_weight=config.loss_frequency_weight,
                phase_smoothness_weight=config.phase_smoothness_weight,
            )
            if is_train:
                if config.effective_batch_size is None:
                    losses["loss_total"].backward()
                    optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                    optimizer_updates += 1
                else:
                    effective_batch_size = config.effective_batch_size
                    (
                        losses["loss_total"] * (batch_size / effective_batch_size)
                    ).backward()
                    pending_samples += batch_size
                    if pending_samples > effective_batch_size:
                        raise invalid_restoration_contract(
                            "micro-batches crossed the effective batch boundary"
                        )
                    if pending_samples == effective_batch_size:
                        optimizer.step()
                        optimizer.zero_grad(set_to_none=True)
                        optimizer_updates += 1
                        pending_samples = 0
                        gradient_accumulation.pending_samples = 0

            sample_count += batch_size
            batch_metrics = {
                **{name: float(value.detach().item()) for name, value in losses.items()},
                "psnr_raw": _mean_per_sample_metric(
                    psnr,
                    prediction_raw.detach(),
                    target_raw.detach(),
                ),
                "ssim_raw": _mean_per_sample_metric(
                    ssim_global,
                    prediction_raw.detach(),
                    target_raw.detach(),
                ),
                "psnr_normalized": _mean_per_sample_metric(
                    psnr,
                    prediction_normalized.detach(),
                    target_normalized.detach(),
                ),
                "ssim_normalized": _mean_per_sample_metric(
                    ssim_global,
                    prediction_normalized.detach(),
                    target_normalized.detach(),
                ),
                "energy_throughput": energy_throughput(
                    input_intensity.detach(),
                    prediction_raw.detach(),
                ),
                "clipping_ratio": clipping_ratio(prediction_raw.detach()),
            }
            for name, value in batch_metrics.items():
                totals[name] += float(value) * batch_size
            if (
                is_train
                and optimizer_update_limit is not None
                and optimizer_updates >= optimizer_update_limit
            ):
                break

    if is_train and config.effective_batch_size is not None:
        assert gradient_accumulation is not None
        gradient_accumulation.pending_samples = pending_samples

    if sample_count == 0:
        raise invalid_restoration_contract(f"{split} loader must not be empty")
    averaged = {name: value / sample_count for name, value in totals.items()}
    return EpochRow(
        epoch=epoch,
        split=split,
        optimizer_updates=optimizer_updates,
        loss_total=averaged["loss_total"],
        loss_l1=averaged["loss_l1"],
        loss_ssim=averaged["loss_ssim"],
        loss_frequency=averaged["loss_frequency"],
        phase_smoothness=averaged["phase_smoothness"],
        psnr_raw=averaged["psnr_raw"],
        ssim_raw=averaged["ssim_raw"],
        psnr_normalized=averaged["psnr_normalized"],
        ssim_normalized=averaged["ssim_normalized"],
        energy_throughput=averaged["energy_throughput"],
        clipping_ratio=averaged["clipping_ratio"],
        learning_rate=config.learning_rate,
        phase_offset_reference=_phase_offset_reference_for_model(model),
        optical_residual_gate=optical_residual_gate_for_model(model),
        operating_point_hash=operating_point_hash,
        status="PASS",
    )
def _mean_per_sample_metric(
    metric: Callable[..., float],
    prediction: torch.Tensor,
    target: torch.Tensor,
) -> float:
    """
    璁＄畻涓嶅彈杩愯鏃跺井鎵归噺鍒掑垎褰卞搷鐨勯€愭牱鏈钩鍧囨寚鏍?    """
    values = [
        float(
            metric(
                prediction[index : index + 1],
                target[index : index + 1],
                data_range=1.0,
            )
        )
        for index in range(int(prediction.shape[0]))
    ]
    return sum(values) / len(values)


def clipping_ratio(image: torch.Tensor) -> float:
    """
    杩斿洖瓒呭嚭鏍囧噯寮哄害鑼冨洿鐨勫儚绱犳瘮渚?    """
    clipped = (image < 0.0) | (image > 1.0)
    return float(clipped.to(dtype=torch.float32).mean().item())


def degraded_image_from_batch(batch: Mapping[str, object]) -> torch.Tensor:
    """
    浠庝弗鏍兼壒娆′腑璇诲彇閫€鍖栧浘鍍?    """
    image = degraded_from_batch(batch)
    if image.ndim == 3:
        image = image.unsqueeze(0)
    if image.ndim != 4 or image.shape[1] != 1:
        raise invalid_restoration_contract(
            "degraded_image must have shape (B, 1, H, W)"
        )
    return image


def baseline_metrics(
    model: torch.nn.Module,
    loader: DataLoader,
    config: TrainingConfig,
    device: torch.device,
) -> dict[str, float]:
    """
    璁＄畻妯″瀷鐩稿鐗╃悊鎴栭€€鍖栧熀绾跨殑鎸囨爣
    """
    model.eval()
    baseline_values: list[float] = []
    trained_values: list[float] = []
    with torch.no_grad():
        for batch in loader:
            target_raw = target_from_batch(batch).to(device=device, dtype=torch.float32)
            if config.model_role == "backend_only":
                degraded_image = degraded_image_from_batch(batch).to(
                    device=device,
                    dtype=torch.float32,
                )
                baseline = degraded_image
                trained = model(degraded_image)
            else:
                input_field = ensure_batched_field(batch["input_field"]).to(device)
                baseline_getter = getattr(model, "phase_zero_baselines")
                baseline = baseline_getter(input_field)["image_full_frontend_phase_zero"]
                trained = model(input_field)
            target_normalized = normalize_intensity(
                target_raw,
                policy=config.intensity_normalization_policy,
                scale=1.0,
            )
            baseline_normalized = normalize_intensity(
                baseline,
                policy=config.intensity_normalization_policy,
                scale=1.0,
            )
            trained_normalized = normalize_intensity(
                trained,
                policy=config.intensity_normalization_policy,
                scale=1.0,
            )
            baseline_values.append(psnr(baseline_normalized, target_normalized, data_range=1.0))
            trained_values.append(psnr(trained_normalized, target_normalized, data_range=1.0))
    baseline_psnr = finite_mean(baseline_values)
    trained_psnr = finite_mean(trained_values)
    metrics = {
        "phase_zero_vs_clean_psnr": baseline_psnr,
        "trained_vs_clean_psnr": trained_psnr,
        "trained_minus_phase_zero_psnr": trained_psnr - baseline_psnr,
    }
    if config.model_role == "backend_only":
        metrics.update(
            {
                "degraded_vs_clean_psnr": baseline_psnr,
                "trained_minus_degraded_psnr": trained_psnr - baseline_psnr,
            }
        )
    return metrics


def finite_mean(values: list[float]) -> float:
    """
    璁＄畻淇濈暀鏃犵┓璇箟鐨勬湁闄愬潎鍊?    """
    if not values:
        return 0.0
    if any(value == math.inf for value in values):
        return math.inf
    if any(value == -math.inf for value in values):
        return -math.inf
    finite_values = [value for value in values if math.isfinite(value)]
    if finite_values:
        return sum(finite_values) / len(finite_values)
    return math.nan

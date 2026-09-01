from __future__ import annotations

from collections.abc import Iterable, Mapping

import torch


def build_target_distribution(
    target_distribution: torch.Tensor,
    split: str = "train",
) -> torch.Tensor:
    """
    探测目标分布缩放
    """
    if split == "train":
        scale = 0.1
    elif split in {"val", "test"}:
        scale = 0.01
    else:
        message = f"unsupported split: {split}"
        raise ValueError(message)
    return target_distribution.float() * scale


def _extract_batch(
    batch: Mapping[str, object],
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    input_field = batch["input_field"]
    label = batch["label"]
    target_distribution = batch["target_detector_distribution"]
    if not isinstance(input_field, torch.Tensor):
        input_field = torch.as_tensor(input_field)
    if not isinstance(label, torch.Tensor):
        label = torch.as_tensor(label)
    if not isinstance(target_distribution, torch.Tensor):
        target_distribution = torch.as_tensor(target_distribution)
    return (
        input_field.to(device),
        label.to(device).long(),
        target_distribution.to(device).float(),
    )


def _run_epoch(
    *,
    model: torch.nn.Module,
    dataloader: Iterable[Mapping[str, object]],
    criterion: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> tuple[float, float]:
    model.train()
    total_loss = 0.0
    correct = 0
    sample_count = 0
    for batch in dataloader:
        input_field, labels, target_distribution = _extract_batch(batch, device)
        optimizer.zero_grad()
        prediction, _ = model(input_field)
        loss = criterion(
            prediction,
            build_target_distribution(target_distribution, split="train"),
        )
        loss.backward()
        optimizer.step()
        batch_size = int(labels.shape[0])
        total_loss += float(loss.item())
        correct += int((prediction.argmax(dim=1) == labels).sum().item())
        sample_count += batch_size
    return total_loss / max(sample_count, 1), correct / max(sample_count, 1)


def _evaluate_loss_accuracy(
    *,
    model: torch.nn.Module,
    dataloader: Iterable[Mapping[str, object]],
    criterion: torch.nn.Module,
    device: torch.device,
    split: str,
) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    correct = 0
    sample_count = 0
    with torch.no_grad():
        for batch in dataloader:
            input_field, labels, target_distribution = _extract_batch(batch, device)
            prediction, _ = model(input_field)
            loss = criterion(
                prediction,
                build_target_distribution(target_distribution, split=split),
            )
            total_loss += float(loss.item())
            correct += int((prediction.argmax(dim=1) == labels).sum().item())
            sample_count += int(labels.shape[0])
    return total_loss / max(sample_count, 1), correct / max(sample_count, 1)

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch

from experiments.classification.dataset_adapter import build_classification_dataloaders
from experiments.classification.model import (
    ClassificationONN,
    normalize_topology,
)


def _extract_batch(
    batch: dict[str, object],
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    input_field = batch["input_field"]
    labels = batch["label"]
    if not isinstance(input_field, torch.Tensor):
        input_field = torch.as_tensor(input_field)
    if not isinstance(labels, torch.Tensor):
        labels = torch.as_tensor(labels)
    return input_field.to(device), labels.to(device).long()


def evaluate_model(
    *,
    model: torch.nn.Module,
    dataloader: object,
    device: torch.device,
) -> dict[str, Any]:
    """
    璇勪及鍒嗙被妯″瀷鍑嗙‘鐜囧拰娣锋穯鐭╅樀
    """
    model.eval()
    confusion_matrix = torch.zeros((10, 10), dtype=torch.int64)
    correct = 0
    sample_count = 0
    with torch.no_grad():
        for batch in dataloader:
            input_field, labels = _extract_batch(batch, device)
            prediction, _ = model(input_field)
            predicted = prediction.argmax(dim=1)
            correct += int((predicted == labels).sum().item())
            sample_count += int(labels.numel())
            for actual, predicted_label in zip(labels.cpu(), predicted.cpu(), strict=True):
                confusion_matrix[int(actual), int(predicted_label)] += 1
    per_class_total = confusion_matrix.sum(dim=1).clamp_min(1)
    per_class_accuracy = confusion_matrix.diag().float() / per_class_total.float()
    return {
        "accuracy": correct / max(sample_count, 1),
        "sample_count": sample_count,
        "confusion_matrix": confusion_matrix.tolist(),
        "per_class_accuracy": per_class_accuracy.tolist(),
    }


def _checkpoint_topology(checkpoint: dict[str, object]) -> str:
    training_config = checkpoint.get("training_config", {})
    if isinstance(training_config, dict):
        topology = training_config.get("topology", "without_lens")
        if isinstance(topology, str):
            return normalize_topology(topology)
    return "without_lens"


def _checkpoint_model_kwargs(checkpoint: dict[str, object]) -> dict[str, object]:
    training_config = checkpoint.get("training_config", {})
    if not isinstance(training_config, dict):
        return {}
    supported_keys = (
        "phase_parameterization",
        "phase_initialization",
        "propagation_distance",
        "focal_length",
        "pixel_size",
    )
    return {key: training_config[key] for key in supported_keys if key in training_config}


def evaluate_checkpoint(
    checkpoint_path: Path | str,
    project_root: Path | str = Path.cwd(),
    device: str = "cpu",
) -> dict[str, Any]:
    """
    鍔犺浇 checkpoint 骞跺湪娴嬭瘯闆嗘垨楠岃瘉闆嗕笂璇勪及
    """
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    if "model_state_dict" not in checkpoint:
        message = "checkpoint is missing required model_state_dict"
        raise ValueError(message)
    torch_device = torch.device(device)
    topology = _checkpoint_topology(checkpoint)
    model = ClassificationONN(
        topology=topology,
        **_checkpoint_model_kwargs(checkpoint),
    )
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.to(torch_device)
    dataloaders = build_classification_dataloaders(topology=topology)
    evaluation_split = "test" if "test" in dataloaders else "val"
    summary = evaluate_model(
        model=model,
        dataloader=dataloaders[evaluation_split],
        device=torch_device,
    )
    summary.update(
        {
            "evaluation_split": evaluation_split,
            "test_loader_available": evaluation_split == "test",
        }
    )
    output_path = Path(project_root) / "results" / "classification" / "eval_summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> dict[str, Any]:
    """
    鍛戒护琛岃瘎浼板叆鍙?
    """
    parser = argparse.ArgumentParser(description="Evaluate a classification checkpoint.")
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--project-root", default=Path.cwd(), type=Path)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)
    return evaluate_checkpoint(
        checkpoint_path=args.checkpoint,
        project_root=args.project_root,
        device=args.device,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

import torch
from torch import nn

from experiments.classification.artifacts import _write_json
from experiments.classification.engine import _extract_batch


READOUT_RENDER_CACHE_SCHEMA_VERSION = 1


def _to_cpu_tensor(value: object) -> torch.Tensor:
    if isinstance(value, torch.Tensor):
        return value.detach().cpu()
    return torch.as_tensor(value).detach().cpu()


def _to_float_list(value: object) -> list[float]:
    tensor = _to_cpu_tensor(value)
    return [float(item) for item in tensor.flatten()]


def _split_model_output(output: object) -> tuple[torch.Tensor, torch.Tensor]:
    if isinstance(output, Mapping):
        detector_distribution = output.get("detector_distribution", output.get("prediction"))
        intensity_map = output.get("intensity_map", output.get("intensity"))
        if detector_distribution is None or intensity_map is None:
            message = "model output mapping must include detector and intensity data"
            raise ValueError(message)
        return _to_cpu_tensor(detector_distribution), _to_cpu_tensor(intensity_map)
    if isinstance(output, (tuple, list)) and len(output) >= 2:
        return _to_cpu_tensor(output[0]), _to_cpu_tensor(output[1])
    if isinstance(output, torch.Tensor):
        tensor = _to_cpu_tensor(output)
        return tensor, tensor
    message = "model output must be a mapping, tensor, or detector/intensity tuple"
    raise TypeError(message)


def _batched_item(tensor: torch.Tensor, index: int, batch_size: int) -> torch.Tensor:
    if tensor.ndim > 0 and int(tensor.shape[0]) == batch_size:
        return tensor[index]
    return tensor


def _visualization_safe_intensity(tensor: torch.Tensor) -> torch.Tensor:
    if tensor.ndim == 0:
        return tensor.reshape(1, 1)
    if tensor.ndim == 1:
        return tensor.unsqueeze(0)
    return tensor


def _as_intensity_2d(intensity_map: torch.Tensor) -> torch.Tensor:
    tensor = _to_cpu_tensor(intensity_map).to(torch.float32)
    if tensor.ndim == 3 and tensor.shape[0] == 1:
        tensor = tensor.squeeze(0)
    if tensor.ndim != 2:
        message = "intensity evidence requires a 2D intensity map"
        raise ValueError(message)
    return tensor


def _find_detector_index(
    coordinate: tuple[int, int],
    detector_regions: Sequence[Sequence[int]],
) -> int | None:
    x_peak, y_peak = coordinate
    for index, region in enumerate(detector_regions):
        x0, x1, y0, y1 = [int(value) for value in region]
        if x0 <= x_peak < x1 and y0 <= y_peak < y1:
            return index
    return None


def _detector_evidence(
    *,
    intensity_map: torch.Tensor,
    detector_distribution: torch.Tensor,
    target_distribution: torch.Tensor,
    detector_regions: Sequence[Sequence[int]],
) -> dict[str, object]:
    intensity_2d = _as_intensity_2d(intensity_map)
    total_energy = float(intensity_2d.sum().item())
    detector_sums: list[float] = []
    for region in detector_regions:
        x0, x1, y0, y1 = [int(value) for value in region]
        detector_sums.append(float(intensity_2d[y0:y1, x0:x1].sum().item()))

    detector_total = sum(detector_sums)
    predicted_index = int(_to_cpu_tensor(detector_distribution).argmax().item())
    target_index = int(_to_cpu_tensor(target_distribution).argmax().item())
    peak_flat = int(intensity_2d.argmax().item())
    y_peak, x_peak = divmod(peak_flat, int(intensity_2d.shape[1]))
    peak_coordinate = (x_peak, y_peak)
    peak_detector_index = _find_detector_index(peak_coordinate, detector_regions)
    detector_denominator = max(detector_total, 1e-12)

    return {
        "detector_regions": [
            tuple(int(value) for value in region) for region in detector_regions
        ],
        "detector_total_energy_fraction": detector_total / max(total_energy, 1e-12),
        "target_detector_energy_fraction": (
            detector_sums[target_index] / detector_denominator
        ),
        "predicted_detector_energy_fraction": (
            detector_sums[predicted_index] / detector_denominator
        ),
        "peak_coordinate": peak_coordinate,
        "peak_detector_index": peak_detector_index,
        "is_peak_in_any_detector": peak_detector_index is not None,
        "is_peak_in_target_detector": peak_detector_index == target_index,
    }


def _readout_metadata(example: Mapping[str, object]) -> dict[str, object]:
    input_image = _to_cpu_tensor(example["input_image"])
    intensity_value = (
        example["intensity_map"] if "intensity_map" in example else example["intensity"]
    )
    intensity_map = _to_cpu_tensor(intensity_value)
    detector_distribution = _to_cpu_tensor(example["detector_distribution"])
    target_distribution = _to_cpu_tensor(example["target_detector_distribution"])
    return {
        "sample_index": int(example["sample_index"]),
        "true_label": int(example["true_label"]),
        "predicted_label": int(example["predicted_label"]),
        "detector_distribution": _to_float_list(detector_distribution),
        "target_detector_distribution": _to_float_list(target_distribution),
        "input_image_min": float(input_image.min().item()),
        "input_image_max": float(input_image.max().item()),
        "intensity_min": float(intensity_map.min().item()),
        "intensity_max": float(intensity_map.max().item()),
        "detector_regions": [
            [int(value) for value in region]
            for region in example.get("detector_regions", [])
        ],
        "detector_total_energy_fraction": (
            None
            if "detector_total_energy_fraction" not in example
            else float(example["detector_total_energy_fraction"])
        ),
        "target_detector_energy_fraction": (
            None
            if "target_detector_energy_fraction" not in example
            else float(example["target_detector_energy_fraction"])
        ),
        "predicted_detector_energy_fraction": (
            None
            if "predicted_detector_energy_fraction" not in example
            else float(example["predicted_detector_energy_fraction"])
        ),
        "peak_coordinate": (
            None
            if "peak_coordinate" not in example
            else [int(value) for value in example["peak_coordinate"]]
        ),
        "peak_detector_index": (
            None
            if example.get("peak_detector_index") is None
            else int(example["peak_detector_index"])
        ),
        "is_peak_in_any_detector": (
            None
            if "is_peak_in_any_detector" not in example
            else bool(example["is_peak_in_any_detector"])
        ),
        "is_peak_in_target_detector": (
            None
            if "is_peak_in_target_detector" not in example
            else bool(example["is_peak_in_target_detector"])
        ),
    }


def _normalize_detector_regions(value: object) -> list[list[int]]:
    regions = []
    for region in value or []:
        regions.append([int(item) for item in region])
    return regions


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_coordinate(value: object) -> list[int] | None:
    if value is None:
        return None
    return [int(item) for item in value]


def _render_cache_example(example: Mapping[str, object]) -> dict[str, object]:
    intensity_value = (
        example["intensity_map"] if "intensity_map" in example else example["intensity"]
    )
    return {
        "sample_index": int(example["sample_index"]),
        "true_label": int(example["true_label"]),
        "predicted_label": int(example["predicted_label"]),
        "input_image": _to_cpu_tensor(example["input_image"]).to(torch.float32),
        "input_field_magnitude": _to_cpu_tensor(
            example["input_field_magnitude"]
        ).to(torch.float32),
        "intensity_map": _to_cpu_tensor(intensity_value).to(torch.float32),
        "detector_distribution": _to_cpu_tensor(
            example["detector_distribution"]
        ).to(torch.float32),
        "target_detector_distribution": _to_cpu_tensor(
            example["target_detector_distribution"]
        ).to(torch.float32),
        "detector_regions": _normalize_detector_regions(
            example.get("detector_regions", [])
        ),
        "detector_total_energy_fraction": _optional_float(
            example.get("detector_total_energy_fraction")
        ),
        "target_detector_energy_fraction": _optional_float(
            example.get("target_detector_energy_fraction")
        ),
        "predicted_detector_energy_fraction": _optional_float(
            example.get("predicted_detector_energy_fraction")
        ),
        "peak_coordinate": _optional_coordinate(example.get("peak_coordinate")),
        "peak_detector_index": _optional_int(example.get("peak_detector_index")),
        "is_peak_in_any_detector": _optional_bool(
            example.get("is_peak_in_any_detector")
        ),
        "is_peak_in_target_detector": _optional_bool(
            example.get("is_peak_in_target_detector")
        ),
    }


def _write_readout_render_cache(
    path: str | Path,
    examples: Sequence[Mapping[str, object]],
    *,
    source_checkpoint: str,
    source_checkpoint_path: str | Path,
    config_hash: str,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": READOUT_RENDER_CACHE_SCHEMA_VERSION,
        "source_checkpoint": source_checkpoint,
        "source_checkpoint_path": str(Path(source_checkpoint_path)),
        "config_hash": config_hash,
        "examples": [_render_cache_example(example) for example in examples],
    }
    torch.save(payload, output_path)
    return output_path


def _read_readout_render_cache(path: str | Path) -> dict[str, object]:
    payload = torch.load(Path(path), map_location="cpu")
    if not isinstance(payload, dict):
        message = "readout render cache must be a dictionary"
        raise ValueError(message)
    if payload.get("schema_version") != READOUT_RENDER_CACHE_SCHEMA_VERSION:
        message = "unsupported readout render cache schema_version"
        raise ValueError(message)
    examples = payload.get("examples")
    if not isinstance(examples, list):
        message = "readout render cache examples must be a list"
        raise ValueError(message)
    if not all(isinstance(example, dict) for example in examples):
        message = "readout render cache examples must contain dictionaries"
        raise ValueError(message)
    return payload


def _readout_selection_score(example: Mapping[str, object]) -> tuple[int, float, int]:
    true_label = int(example["true_label"])
    predicted_label = int(example["predicted_label"])
    detector_distribution = _to_cpu_tensor(example["detector_distribution"]).flatten()
    target_score = (
        float(detector_distribution[true_label].item())
        if 0 <= true_label < int(detector_distribution.numel())
        else float("-inf")
    )
    return (
        1 if predicted_label == true_label else 0,
        target_score,
        -int(example["sample_index"]),
    )


def _collect_readout_examples(
    *,
    model: nn.Module,
    dataloader: Iterable[Mapping[str, object]],
    device: torch.device,
    max_examples: int = 10,
) -> list[dict[str, object]]:
    was_training = model.training
    examples_by_label: dict[int, dict[str, object]] = {}
    sample_index = 0
    detector_regions = getattr(model, "detector_regions", ())
    model.eval()
    try:
        with torch.no_grad():
            for batch in dataloader:
                if "input_image" not in batch:
                    continue
                input_field, labels, target_distribution = _extract_batch(batch, device)
                detector_distribution, intensity_map = _split_model_output(model(input_field))
                detector_distribution = detector_distribution.cpu()
                intensity_map = intensity_map.cpu()
                predictions = detector_distribution.argmax(dim=1)
                input_images = _to_cpu_tensor(batch["input_image"])
                input_field_magnitude = input_field.detach().abs().cpu()
                labels = labels.detach().cpu()
                target_distribution = target_distribution.detach().cpu()
                batch_size = int(labels.shape[0])
                for index in range(batch_size):
                    sample_intensity = _batched_item(
                        intensity_map,
                        index,
                        batch_size,
                    )
                    sample_intensity = _visualization_safe_intensity(sample_intensity)
                    example = {
                        "sample_index": sample_index,
                        "true_label": int(labels[index].item()),
                        "predicted_label": int(predictions[index].item()),
                        "input_image": _batched_item(input_images, index, batch_size),
                        "input_field_magnitude": _batched_item(
                            input_field_magnitude,
                            index,
                            batch_size,
                        ),
                        "intensity": sample_intensity,
                        "intensity_map": sample_intensity,
                        "detector_distribution": _batched_item(
                            detector_distribution,
                            index,
                            batch_size,
                        ),
                        "target_detector_distribution": _batched_item(
                            target_distribution,
                            index,
                            batch_size,
                        ),
                    }
                    if detector_regions:
                        example.update(
                            _detector_evidence(
                                intensity_map=sample_intensity,
                                detector_distribution=example["detector_distribution"],
                                target_distribution=example[
                                    "target_detector_distribution"
                                ],
                                detector_regions=detector_regions,
                            )
                        )
                    true_label = int(example["true_label"])
                    current_example = examples_by_label.get(true_label)
                    current_score = (
                        _readout_selection_score(current_example)
                        if current_example is not None
                        else None
                    )
                    candidate_score = _readout_selection_score(example)
                    if current_score is None or candidate_score > current_score:
                        examples_by_label[true_label] = example
                    sample_index += 1
    finally:
        if was_training:
            model.train()
    return [
        examples_by_label[label]
        for label in sorted(examples_by_label)
    ][:max_examples]


def _write_readout_examples(
    path: str | Path,
    examples: Sequence[Mapping[str, object]],
) -> Path:
    payload = {
        "examples": [_readout_metadata(example) for example in examples],
        "warnings": [] if examples else ["No optical readout examples were collected."],
    }
    return _write_json(path, payload)

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

import experiments.classification.readout as readout
from experiments.classification import train
from experiments.classification.visualize import visualize_optical_readout_examples


class _TinyReadoutModel(torch.nn.Module):
    def forward(self, input_field: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        返回固定读出张量
        """
        detector_distribution = torch.zeros((input_field.shape[0], 10), dtype=torch.float32)
        detector_distribution[:, 3] = 1.0
        intensity = torch.arange(
            input_field.shape[0] * 4,
            dtype=torch.float32,
        ).reshape(input_field.shape[0], 1, 2, 2)
        return detector_distribution, intensity


class _TensorOnlyReadoutModel(torch.nn.Module):
    def forward(self, input_field: torch.Tensor) -> torch.Tensor:
        """
        返回无强度图的探测器张量
        """
        detector_distribution = torch.zeros(
            (input_field.shape[0], 10),
            dtype=torch.float32,
        )
        detector_distribution[:, 3] = 1.0
        return detector_distribution


class _DetectorAwareReadoutModel(torch.nn.Module):
    detector_regions = (
        (0, 1, 0, 1),
        (1, 2, 0, 1),
        (2, 3, 0, 1),
        (0, 1, 1, 2),
        (1, 2, 1, 2),
        (2, 3, 1, 2),
        (3, 4, 1, 2),
        (0, 1, 2, 3),
        (1, 2, 2, 3),
        (2, 3, 2, 3),
    )

    def forward(self, input_field: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        执行测试替身前向传播
        """
        intensity = torch.zeros((input_field.shape[0], 1, 4, 4), dtype=torch.float32)
        intensity[:, 0, 0, 1] = 5.0
        detector_distribution = torch.zeros(
            (input_field.shape[0], 10),
            dtype=torch.float32,
        )
        detector_distribution[:, 1] = 1.0
        return detector_distribution, intensity


class _EncodedReadoutModel(torch.nn.Module):
    def forward(self, input_field: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        执行测试替身前向传播
        """
        encoded = input_field.detach().real.cpu()
        labels = encoded[:, 0, 0, 0].to(torch.long)
        target_scores = encoded[:, 0, 0, 1].to(torch.float32)
        competitor_scores = encoded[:, 0, 1, 0].to(torch.float32)
        detector_distribution = torch.zeros((input_field.shape[0], 10), dtype=torch.float32)
        intensity = torch.zeros((input_field.shape[0], 1, 2, 2), dtype=torch.float32)
        for index, label in enumerate(labels.tolist()):
            competitor_label = (label + 1) % 10
            detector_distribution[index, label] = target_scores[index]
            detector_distribution[index, competitor_label] = competitor_scores[index]
            intensity[index, 0, 0, 0] = target_scores[index]
        return detector_distribution, intensity


def _batch(labels: list[int]) -> dict[str, torch.Tensor]:
    label_tensor = torch.tensor(labels, dtype=torch.long)
    return {
        "input_image": torch.arange(
            len(labels) * 4,
            dtype=torch.float32,
        ).reshape(len(labels), 1, 2, 2),
        "input_field": torch.ones((len(labels), 1, 2, 2), dtype=torch.complex64),
        "target_detector_distribution": torch.eye(10, dtype=torch.float32)[label_tensor],
        "label": label_tensor,
    }


def _encoded_batch(
    labels: list[int],
    target_scores: list[float],
    competitor_scores: list[float],
) -> dict[str, torch.Tensor]:
    input_field = torch.zeros((len(labels), 1, 2, 2), dtype=torch.complex64)
    input_field[:, 0, 0, 0] = torch.tensor(labels, dtype=torch.float32)
    input_field[:, 0, 0, 1] = torch.tensor(target_scores, dtype=torch.float32)
    input_field[:, 0, 1, 0] = torch.tensor(competitor_scores, dtype=torch.float32)
    label_tensor = torch.tensor(labels, dtype=torch.long)
    return {
        "input_image": torch.arange(
            len(labels) * 4,
            dtype=torch.float32,
        ).reshape(len(labels), 1, 2, 2),
        "input_field": input_field,
        "target_detector_distribution": torch.eye(10, dtype=torch.float32)[label_tensor],
        "label": label_tensor,
    }


def test_split_model_output_accepts_sequence_output() -> None:
    """
    元组输出拆分契约
    """
    detector_distribution = torch.ones((2, 10), dtype=torch.float32)
    intensity = torch.ones((2, 1, 2, 2), dtype=torch.float32)

    split_distribution, split_intensity = readout._split_model_output(
        (detector_distribution, intensity)
    )

    assert torch.equal(split_distribution, detector_distribution)
    assert torch.equal(split_intensity, intensity)


def test_split_model_output_accepts_plain_tensor_for_compatibility() -> None:
    """
    张量输出读出契约
    """
    output = torch.ones((2, 10), dtype=torch.float32)

    detector_distribution, intensity = readout._split_model_output(output)

    assert torch.equal(detector_distribution, output)
    assert torch.equal(intensity, output)


def test_batched_item_returns_sample_only_when_first_dimension_matches_batch() -> None:
    """
    批次样本选择边界
    """
    batched = torch.tensor([[1, 2], [3, 4]])
    unbatched = torch.tensor([1, 2])

    assert torch.equal(readout._batched_item(batched, 1, batch_size=2), torch.tensor([3, 4]))
    assert torch.equal(readout._batched_item(unbatched, 1, batch_size=3), unbatched)


def test_collect_readout_examples_keeps_requested_fields_and_limit() -> None:
    """
    读出样本字段契约
    """
    examples = readout._collect_readout_examples(
        model=_TinyReadoutModel(),
        dataloader=[_batch([1, 2, 3])],
        device=torch.device("cpu"),
        max_examples=2,
    )

    assert [example["sample_index"] for example in examples] == [0, 1]
    assert [example["true_label"] for example in examples] == [1, 2]
    assert [example["predicted_label"] for example in examples] == [3, 3]
    for example in examples:
        assert {
            "sample_index",
            "true_label",
            "predicted_label",
            "detector_distribution",
            "target_detector_distribution",
            "input_image",
            "input_field_magnitude",
            "intensity",
            "intensity_map",
        } <= set(example)
        assert example["detector_distribution"].shape == (10,)
        assert example["target_detector_distribution"].shape == (10,)
        assert example["input_image"].shape == (1, 2, 2)
        assert example["intensity"].shape == (1, 2, 2)


def test_collect_readout_examples_selects_best_representative_per_class() -> None:
    """
    验证分类测试契约保持稳定
    """
    examples = readout._collect_readout_examples(
        model=_EncodedReadoutModel(),
        dataloader=[
            _encoded_batch(
                labels=[0, 0, 1, 1, 2],
                target_scores=[0.95, 0.80, 0.40, 0.70, 0.60],
                competitor_scores=[1.00, 0.10, 0.20, 0.10, 0.90],
            )
        ],
        device=torch.device("cpu"),
    )

    assert [example["true_label"] for example in examples] == [0, 1, 2]
    assert [example["sample_index"] for example in examples] == [1, 3, 4]
    assert [example["predicted_label"] for example in examples] == [0, 1, 3]


def test_readout_examples_include_detector_evidence() -> None:
    """
    验证分类测试契约保持稳定
    """
    batch = _batch([1])
    batch["input_field"] = torch.ones((1, 1, 4, 4), dtype=torch.complex64)
    batch["input_image"] = torch.ones((1, 1, 4, 4), dtype=torch.float32)

    examples = readout._collect_readout_examples(
        model=_DetectorAwareReadoutModel(),
        dataloader=[batch],
        device=torch.device("cpu"),
        max_examples=1,
    )

    example = examples[0]
    assert example["detector_regions"][1] == (1, 2, 0, 1)
    assert example["detector_total_energy_fraction"] == pytest.approx(1.0)
    assert example["target_detector_energy_fraction"] == pytest.approx(1.0)
    assert example["predicted_detector_energy_fraction"] == pytest.approx(1.0)
    assert example["peak_coordinate"] == (1, 0)
    assert example["peak_detector_index"] == 1
    assert example["is_peak_in_any_detector"] is True
    assert example["is_peak_in_target_detector"] is True


def test_collect_readout_examples_keeps_tensor_only_outputs_visualizable(
    tmp_path: Path,
) -> None:
    """
    张量读出形状契约
    """
    examples = readout._collect_readout_examples(
        model=_TensorOnlyReadoutModel(),
        dataloader=[_batch([1])],
        device=torch.device("cpu"),
        max_examples=1,
    )

    assert tuple(examples[0]["intensity_map"].shape) == (1, 10)
    outputs = visualize_optical_readout_examples(
        examples,
        tmp_path / "tensor_only_readout",
    )

    assert Path(outputs["upper_png"]).exists()
    assert Path(outputs["upper_svg"]).exists()
    assert Path(outputs["lower_png"]).exists()
    assert Path(outputs["lower_svg"]).exists()


def test_write_readout_examples_writes_stable_json_schema(tmp_path: Path) -> None:
    """
    读出 JSON 契约
    """
    examples = readout._collect_readout_examples(
        model=_TinyReadoutModel(),
        dataloader=[_batch([1])],
        device=torch.device("cpu"),
        max_examples=1,
    )

    output_path = readout._write_readout_examples(tmp_path / "readout.json", examples)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(payload) == {"examples", "warnings"}
    assert payload["warnings"] == []
    assert len(payload["examples"]) == 1
    expected_example_keys = {
        "sample_index",
        "true_label",
        "predicted_label",
        "detector_distribution",
        "target_detector_distribution",
        "input_image_min",
        "input_image_max",
        "intensity_min",
        "intensity_max",
        "detector_regions",
        "detector_total_energy_fraction",
        "target_detector_energy_fraction",
        "predicted_detector_energy_fraction",
        "peak_coordinate",
        "peak_detector_index",
        "is_peak_in_any_detector",
        "is_peak_in_target_detector",
    }
    assert set(payload["examples"][0]) == expected_example_keys
    assert len(payload["examples"][0]["detector_distribution"]) == 10


def test_write_readout_examples_warns_when_empty(tmp_path: Path) -> None:
    """
    空读出告警契约
    """
    output_path = readout._write_readout_examples(tmp_path / "readout.json", [])

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {
        "examples": [],
        "warnings": ["No optical readout examples were collected."],
    }


def test_write_readout_render_cache_writes_schema_and_tensors(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    examples = [
        {
            "sample_index": 0,
            "true_label": 1,
            "predicted_label": 1,
            "input_image": torch.ones((1, 8, 8)),
            "input_field_magnitude": torch.ones((8, 8)),
            "intensity_map": torch.arange(64, dtype=torch.float32).reshape(8, 8),
            "detector_distribution": torch.ones(10),
            "target_detector_distribution": torch.eye(10)[1],
            "detector_regions": [(0, 2, 0, 2)],
            "detector_total_energy_fraction": 0.5,
            "target_detector_energy_fraction": 0.4,
            "predicted_detector_energy_fraction": 0.4,
            "peak_coordinate": (7, 7),
            "peak_detector_index": None,
            "is_peak_in_any_detector": False,
            "is_peak_in_target_detector": False,
        }
    ]

    path = readout._write_readout_render_cache(
        tmp_path / "readout_examples.pt",
        examples,
        source_checkpoint="best",
        source_checkpoint_path=tmp_path / "best.pt",
        config_hash="abc123",
    )

    payload = torch.load(path, map_location="cpu")
    example = payload["examples"][0]
    assert payload["schema_version"] == 1
    assert payload["source_checkpoint"] == "best"
    assert payload["source_checkpoint_path"] == str(tmp_path / "best.pt")
    assert payload["config_hash"] == "abc123"
    assert example["sample_index"] == 0
    assert example["detector_regions"] == [[0, 2, 0, 2]]
    assert example["peak_coordinate"] == [7, 7]
    assert example["peak_detector_index"] is None
    assert example["is_peak_in_any_detector"] is False
    assert isinstance(example["intensity_map"], torch.Tensor)
    assert example["intensity_map"].device.type == "cpu"
    assert example["intensity_map"].dtype == torch.float32


def test_readout_render_cache_roundtrip_is_visualization_ready(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    examples = [
        {
            "sample_index": 2,
            "true_label": 3,
            "predicted_label": 4,
            "input_image": torch.zeros((1, 4, 4)),
            "input_field_magnitude": torch.ones((4, 4)),
            "intensity_map": torch.ones((4, 4)),
            "detector_distribution": torch.ones(10),
            "target_detector_distribution": torch.eye(10)[3],
            "detector_regions": [],
        }
    ]
    path = readout._write_readout_render_cache(
        tmp_path / "readout_examples.pt",
        examples,
        source_checkpoint="last",
        source_checkpoint_path=tmp_path / "last.pt",
        config_hash="hash",
    )

    payload = readout._read_readout_render_cache(path)
    example = payload["examples"][0]

    assert payload["schema_version"] == 1
    assert payload["source_checkpoint"] == "last"
    assert example["true_label"] == 3
    assert example["input_image"].shape == (1, 4, 4)
    assert example["input_image"].device.type == "cpu"
    assert example["input_image"].dtype == torch.float32


def test_readout_render_cache_rejects_unsupported_schema_version(
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    path = tmp_path / "readout_examples.pt"
    torch.save({"schema_version": 999, "examples": []}, path)

    with pytest.raises(ValueError, match="schema_version"):
        readout._read_readout_render_cache(path)


def test_readout_render_cache_rejects_malformed_payloads(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    path = tmp_path / "readout_examples.pt"
    torch.save(["not", "a", "dict"], path)

    with pytest.raises(ValueError, match="dictionary"):
        readout._read_readout_render_cache(path)

    torch.save({"schema_version": 1, "examples": "not a list"}, path)

    with pytest.raises(ValueError, match="examples"):
        readout._read_readout_render_cache(path)


def test_train_re_exports_readout_helpers() -> None:
    """
    训练模块读出接口
    """
    assert train._collect_readout_examples is readout._collect_readout_examples
    assert train._write_readout_examples is readout._write_readout_examples

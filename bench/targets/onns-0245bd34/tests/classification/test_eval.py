from __future__ import annotations

from pathlib import Path

import pytest
import torch

from experiments.classification import eval as classification_eval


class _TinyEvalModel(torch.nn.Module):
    calls: list[dict[str, object]] = []

    def __init__(self, topology: str = "without_lens", **kwargs: object) -> None:
        """
        初始化评估模型并保存参数
        """
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(0.0))
        self.topology = topology
        self.model_kwargs = kwargs
        self.calls.append({"topology": topology, **kwargs})

    def forward(self, input_field: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Return fixed predictions and intensity.
        """
        prediction = torch.zeros((input_field.shape[0], 10), dtype=torch.float32)
        prediction[:, 0] = 1.0
        prediction = prediction + self.weight
        intensity = torch.zeros((input_field.shape[0], 1, 64, 64), dtype=torch.float32)
        return prediction, intensity


def _batch(labels: list[int]) -> dict[str, torch.Tensor]:
    return {
        "input_field": torch.ones((len(labels), 1, 64, 64), dtype=torch.complex64),
        "label": torch.tensor(labels, dtype=torch.long),
    }


def test_evaluate_model_returns_accuracy_confusion_matrix_and_per_class_accuracy() -> None:
    """
    模型评估契约
    """
    summary = classification_eval.evaluate_model(
        model=_TinyEvalModel(),
        dataloader=[_batch([0, 1]), _batch([0])],
        device=torch.device("cpu"),
    )

    assert summary["accuracy"] == pytest.approx(2 / 3)
    assert summary["sample_count"] == 3
    assert len(summary["confusion_matrix"]) == 10
    assert all(len(row) == 10 for row in summary["confusion_matrix"])
    assert summary["confusion_matrix"][0][0] == 2
    assert summary["confusion_matrix"][1][0] == 1
    assert summary["per_class_accuracy"][0] == pytest.approx(1.0)
    assert summary["per_class_accuracy"][1] == pytest.approx(0.0)


def test_evaluate_checkpoint_loads_topology_and_writes_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    检查点评估契约
    """
    checkpoint_path = tmp_path / "checkpoint.pt"
    torch.save(
        {
            "model_state_dict": _TinyEvalModel(topology="with_lens").state_dict(),
            "training_config": {
                "topology": "with_lens",
                "phase_parameterization": "wrapped",
                "phase_initialization": "zeros",
                "propagation_distance": 0.007,
                "focal_length": 0.009,
                "pixel_size": 3e-6,
            },
        },
        checkpoint_path,
    )
    _TinyEvalModel.calls = []
    dataloader_calls: list[dict[str, object]] = []

    monkeypatch.setattr(classification_eval, "ClassificationONN", _TinyEvalModel)

    def _fake_build_classification_dataloaders(
        **kwargs: object,
    ) -> dict[str, list[dict[str, torch.Tensor]]]:
        dataloader_calls.append(kwargs)
        return {"train": [_batch([9])], "val": [_batch([0])]}

    monkeypatch.setattr(
        classification_eval,
        "build_classification_dataloaders",
        _fake_build_classification_dataloaders,
    )

    summary = classification_eval.evaluate_checkpoint(
        checkpoint_path=checkpoint_path,
        project_root=tmp_path,
        device="cpu",
    )

    assert _TinyEvalModel.calls[-1]["topology"] == "with_lens"
    assert _TinyEvalModel.calls[-1]["phase_parameterization"] == "wrapped"
    assert _TinyEvalModel.calls[-1]["phase_initialization"] == "zeros"
    assert _TinyEvalModel.calls[-1]["propagation_distance"] == pytest.approx(0.007)
    assert _TinyEvalModel.calls[-1]["focal_length"] == pytest.approx(0.009)
    assert _TinyEvalModel.calls[-1]["pixel_size"] == pytest.approx(3e-6)
    assert dataloader_calls[-1]["topology"] == "with_lens"
    assert summary["accuracy"] == pytest.approx(1.0)
    assert (tmp_path / "results" / "classification" / "eval_summary.json").exists()


def test_evaluate_checkpoint_raises_when_missing_model_state_dict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    checkpoint_path = tmp_path / "checkpoint.pt"

    def load_checkpoint_stub(
        path: Path,
        map_location: str | None = None,
    ) -> dict[str, int]:
        """
        Return a checkpoint without model weights.
        """
        return {"epoch": 1}

    monkeypatch.setattr(
        classification_eval.torch,
        "load",
        load_checkpoint_stub,
    )

    with pytest.raises(ValueError, match="model_state_dict"):
        classification_eval.evaluate_checkpoint(checkpoint_path, project_root=tmp_path)


def test_evaluate_checkpoint_uses_val_when_test_loader_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    閺嶏繝鐛欑紓鍝勭毌test閺冩湹濞囬悽鈺瞐l
    """
    checkpoint_path = tmp_path / "checkpoint.pt"
    torch.save({"model_state_dict": _TinyEvalModel().state_dict()}, checkpoint_path)

    monkeypatch.setattr(classification_eval, "ClassificationONN", _TinyEvalModel)
    monkeypatch.setattr(
        classification_eval,
        "build_classification_dataloaders",
        lambda **kwargs: {"train": [_batch([9])], "val": [_batch([0])]},
    )

    summary = classification_eval.evaluate_checkpoint(
        checkpoint_path=checkpoint_path,
        project_root=tmp_path,
    )

    assert summary["evaluation_split"] == "val"
    assert summary["test_loader_available"] is False


def test_main_parses_cli_arguments_and_calls_evaluate_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    calls: list[dict[str, object]] = []

    def _fake_evaluate_checkpoint(
        checkpoint_path: Path,
        project_root: Path,
        device: str = "cpu",
    ) -> dict[str, object]:
        calls.append(
            {
                "checkpoint_path": checkpoint_path,
                "project_root": project_root,
                "device": device,
            }
        )
        return {"accuracy": 1.0}

    monkeypatch.setattr(classification_eval, "evaluate_checkpoint", _fake_evaluate_checkpoint)

    classification_eval.main(
        [
            "--checkpoint",
            str(tmp_path / "checkpoint.pt"),
            "--project-root",
            str(tmp_path),
        ]
    )

    assert calls == [
        {
            "checkpoint_path": tmp_path / "checkpoint.pt",
            "project_root": tmp_path,
            "device": "cpu",
        }
    ]

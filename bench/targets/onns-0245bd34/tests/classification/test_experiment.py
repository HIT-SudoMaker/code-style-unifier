from __future__ import annotations

from collections.abc import Callable
import csv
import json
from pathlib import Path

import pytest
import torch

from experiments.classification import experiment
from experiments.classification.config import (
    BasicConfig,
    ModelConfig,
    TrainingConfig,
)


class _TinyModel(torch.nn.Module):
    calls: list[str] = []

    def __init__(self, topology: str = "without_lens") -> None:
        """
        拓扑模型替身
        """
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(0.0))
        self.topology = topology
        self.calls.append(topology)

    def forward(self, input_field: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        返回固定零类预测和强度图
        """
        prediction = torch.zeros((input_field.shape[0], 10), dtype=torch.float32)
        prediction[:, 0] = 1.0
        prediction = prediction + self.weight
        intensity = torch.zeros((input_field.shape[0], 1, 64, 64), dtype=torch.float32)
        return prediction, intensity


def _batch(labels: list[int]) -> dict[str, torch.Tensor]:
    label_tensor = torch.tensor(labels, dtype=torch.long)
    return {
        "input_image": torch.zeros((len(labels), 1, 32, 32), dtype=torch.float32),
        "input_field": torch.ones((len(labels), 1, 64, 64), dtype=torch.complex64),
        "target_detector_distribution": torch.eye(10, dtype=torch.float32)[label_tensor],
        "label": label_tensor,
    }


def _build_classification_dataloaders_fake(
    dataloaders: dict[str, list[dict[str, torch.Tensor]]],
) -> Callable[..., dict[str, list[dict[str, torch.Tensor]]]]:
    """
    构建实验数据加载工厂替身
    """

    def fake_build_classification_dataloaders(
        *,
        batch_size: int,
        topology: str,
        resize_mode: str,
        samples_per_class: int | None,
        random_seed: int,
        image_size: int | tuple[int, int] | None = None,
        **kwargs: object,
    ) -> dict[str, list[dict[str, torch.Tensor]]]:
        """
        校验实验加载参数并返回固定批次
        """
        assert batch_size == 128
        assert topology == "without_lens"
        assert resize_mode == "bilinear"
        assert samples_per_class is None
        assert random_seed == 42
        assert image_size in (None, 32, (32, 32))
        assert kwargs == {}
        return dataloaders

    return fake_build_classification_dataloaders


def _assert_publication_figure_pair(root: Path, figure_name: str) -> None:
    figure_root = root / "diagnostic_figures"
    assert (figure_root / f"{figure_name}.png").exists()
    assert (figure_root / f"{figure_name}.svg").exists()


def test_run_experiment_writes_artifacts_and_uses_test_split(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    实验产物契约
    """
    dataloaders = {
        "train": [_batch([0])],
        "val": [_batch([0])],
        "test": [_batch([0])],
    }
    _TinyModel.calls = []
    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        _build_classification_dataloaders_fake(dataloaders),
    )
    monkeypatch.setattr(experiment, "ClassificationONN", _TinyModel)

    result = experiment.run_experiment(
        TrainingConfig(
            topology="without_lens",
            epochs=1,
            learning_rate=0.0,
            project_root=tmp_path,
            run_name="unit",
        )
    )

    root = tmp_path / "results" / "classification" / "without_lens" / "unit"
    assert _TinyModel.calls == ["without_lens"]
    assert result["paths"]["root"] == root
    assert result["best_checkpoint"] == root / "model_checkpoints" / "best.pt"
    assert result["last_checkpoint"] == root / "model_checkpoints" / "last.pt"
    assert result["summary_path"] == root / "summary.md"

    assert (root / "config.json").exists()
    assert (root / "runtime.json").exists()
    assert (root / "epoch_metrics.csv").exists()
    assert (root / "final_metrics.json").exists()
    assert (root / "summary.md").exists()
    assert (root / "model_checkpoints" / "best.pt").exists()
    assert (root / "model_checkpoints" / "last.pt").exists()
    checkpoint = torch.load(
        root / "model_checkpoints" / "best.pt",
        map_location="cpu",
        weights_only=True,
    )
    assert isinstance(checkpoint["training_config"]["project_root"], str)
    _assert_publication_figure_pair(root, "01_training_dynamics")
    _assert_publication_figure_pair(root, "02_confusion_matrix")
    _assert_publication_figure_pair(root, "03_per_class_accuracy")
    _assert_publication_figure_pair(root, "04_optical_readout_examples_upper")
    _assert_publication_figure_pair(root, "04_optical_readout_examples_lower")
    assert not (root / "diagnostic_figures" / "04_optical_readout_examples.png").exists()
    assert not (root / "diagnostic_figures" / "04_optical_readout_examples.svg").exists()
    assert (root / "diagnostic_figures" / "readout_examples.json").exists()
    assert not (root / "diagnostic_figures" / "training_curves.png").exists()
    assert not (root / "diagnostic_figures" / "training_curves.svg").exists()

    rows = list(csv.DictReader((root / "epoch_metrics.csv").open(encoding="utf-8")))
    assert rows[0]["epoch"] == "1"

    final_metrics = json.loads((root / "final_metrics.json").read_text(encoding="utf-8"))
    assert final_metrics["evaluation_split"] == "test"
    assert final_metrics["test_loader_available"] is True
    assert final_metrics["evaluation_accuracy"] == pytest.approx(1.0)
    assert final_metrics["test_accuracy"] == pytest.approx(1.0)
    assert final_metrics["accuracy"] == pytest.approx(
        final_metrics["evaluation_accuracy"]
    )


def test_run_experiment_project_root_argument_overrides_config_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    项目根目录优先级
    """
    dataloaders = {
        "train": [_batch([0])],
        "val": [_batch([0])],
        "test": [_batch([0])],
    }
    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        _build_classification_dataloaders_fake(dataloaders),
    )
    monkeypatch.setattr(experiment, "ClassificationONN", _TinyModel)

    result = experiment.run_experiment(
        TrainingConfig(
            topology="without_lens",
            epochs=1,
            learning_rate=0.0,
            project_root=Path("ignored"),
            run_name="unit",
        ),
        project_root=tmp_path,
    )

    root = tmp_path / "results" / "classification" / "without_lens" / "unit"
    assert result["paths"]["root"] == root
    assert (root / "config.json").exists()
    assert not (Path("ignored") / "results").exists()


def test_run_experiment_accepts_standard_training_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    dataloaders = {
        "train": [_batch([0])],
        "val": [_batch([0])],
        "test": [_batch([0])],
    }
    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        _build_classification_dataloaders_fake(dataloaders),
    )
    monkeypatch.setattr(experiment, "ClassificationONN", _TinyModel)

    result = experiment.run_experiment(
        TrainingConfig(
            basic=BasicConfig(project_root=tmp_path, run_name="standard"),
            model=ModelConfig(topology="without_lens"),
            epochs=1,
            learning_rate=0.0,
        )
    )

    root = tmp_path / "results" / "classification" / "without_lens" / "standard"
    assert result["paths"]["root"] == root
    config_payload = json.loads((root / "config.json").read_text(encoding="utf-8"))
    assert config_payload["topology"] == "without_lens"
    assert config_payload["run_name"] == "standard"
    assert config_payload["epochs"] == 1

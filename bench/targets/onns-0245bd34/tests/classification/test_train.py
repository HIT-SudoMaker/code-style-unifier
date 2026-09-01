from __future__ import annotations

from collections.abc import Callable
import csv
import json
from pathlib import Path

import pytest
import torch

from experiments.classification import config
from experiments.classification import dataset_adapter
from experiments.classification import experiment, train
from experiments.classification import model
from experiments.classification import visualize


class _TinyModel(torch.nn.Module):
    calls: list[str] = []

    def __init__(self, topology: str = "without_lens") -> None:
        """
        训练模型替身
        """
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(0.0))
        self.topology = topology
        self.calls.append(topology)

    def forward(self, input_field: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        返回固定预测和零强度图
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
    构建训练数据加载工厂替身
    """

    def fake_build_classification_dataloaders(
        *,
        batch_size: int,
        resize_mode: str,
        samples_per_class: int | None,
        random_seed: int,
        image_size: int | tuple[int, int] | None = None,
        topology: str = "without_lens",
    ) -> dict[str, list[dict[str, torch.Tensor]]]:
        """
        校验训练加载参数并返回固定批次
        """
        assert batch_size == 128
        assert resize_mode == "bilinear"
        assert samples_per_class is None
        assert random_seed == 42
        assert image_size in (None, 32, (32, 32))
        assert topology == "without_lens"
        return dataloaders

    return fake_build_classification_dataloaders


def _one_epoch_training_config(tmp_path: Path, run_name: str) -> train.TrainingConfig:
    """
    Build a one-epoch training config for fast tests.
    """
    training_config = train.TrainingConfig(project_root=tmp_path, run_name=run_name)
    training_config.epochs = 1
    training_config.learning_rate = 0.0
    return training_config


def _assert_publication_figure_pair(root: Path, figure_name: str) -> None:
    figure_root = root / "diagnostic_figures"
    assert (figure_root / f"{figure_name}.png").exists()
    assert (figure_root / f"{figure_name}.svg").exists()


def _assert_readout_examples_schema(readout_path: Path) -> list[dict[str, object]]:
    payload = json.loads(readout_path.read_text(encoding="utf-8"))
    assert set(payload) == {"examples", "warnings"}
    assert isinstance(payload["examples"], list)
    assert isinstance(payload["warnings"], list)
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
    for example in payload["examples"]:
        assert set(example) == expected_example_keys
        assert isinstance(example["detector_distribution"], list)
        assert isinstance(example["target_detector_distribution"], list)
        assert len(example["detector_distribution"]) == 10
        assert len(example["target_detector_distribution"]) == 10
        assert example["detector_regions"] == []
        assert example["detector_total_energy_fraction"] is None
        assert example["target_detector_energy_fraction"] is None
        assert example["predicted_detector_energy_fraction"] is None
        assert example["peak_coordinate"] is None
        assert example["peak_detector_index"] is None
        assert example["is_peak_in_any_detector"] is None
        assert example["is_peak_in_target_detector"] is None
    return payload["examples"]


def test_default_training_config_uses_50_epochs(tmp_path: Path) -> None:
    """
    默认轮次契约
    """
    training_config = train.build_default_training_config(
        topology="without_lens",
        project_root=tmp_path,
    )

    assert training_config.epochs == 50
    assert training_config.topology == "without_lens"
    assert training_config.batch_size == 128
    assert training_config.learning_rate == pytest.approx(0.0037)
    assert training_config.weight_decay == pytest.approx(0.0)
    assert training_config.device == "cpu"
    assert training_config.seed == 42
    assert training_config.run_name == "default"
    assert training_config.project_root == tmp_path


def test_build_run_paths_match_results_classification(tmp_path: Path) -> None:
    """
    分类产物目录契约
    """
    paths = train.build_run_paths(tmp_path, topology="with_lens", run_name="smoke")

    root = tmp_path / "results" / "classification" / "with_lens" / "smoke"
    assert paths["root"] == root
    assert paths["epoch_metrics"] == root / "epoch_metrics.csv"
    assert paths["final_metrics"] == root / "final_metrics.json"
    assert paths["config"] == root / "config.json"
    assert paths["runtime"] == root / "runtime.json"
    assert paths["summary"] == root / "summary.md"
    assert paths["best_checkpoint"] == root / "model_checkpoints" / "best.pt"
    assert paths["last_checkpoint"] == root / "model_checkpoints" / "last.pt"
    assert paths["figures"] == root / "diagnostic_figures"


def test_build_run_paths_rejects_unsafe_run_names(tmp_path: Path) -> None:
    """
    运行名称安全契约
    """
    unsafe_run_names = [
        "",
        ".",
        "..",
        "../victim",
        r"..\victim",
        str(tmp_path / "absolute"),
    ]

    for run_name in unsafe_run_names:
        with pytest.raises(ValueError, match="run_name"):
            train.build_run_paths(tmp_path, topology="without_lens", run_name=run_name)


def test_collect_readout_examples_defaults_to_class_representatives() -> None:
    """
    默认读出样本数
    """
    examples = train._collect_readout_examples(
        model=_TinyModel(),
        dataloader=[_batch([0, 1, 2, 3, 4])],
        device=torch.device("cpu"),
    )

    assert [example["sample_index"] for example in examples] == [0, 1, 2, 3, 4]
    assert [example["true_label"] for example in examples] == [0, 1, 2, 3, 4]


def test_train_reexports_import_compatibility_surface() -> None:
    """
    保持 train 旧导入
    """
    assert (
        train.build_classification_dataloaders
        is dataset_adapter.build_classification_dataloaders
    )
    assert train.ClassificationONN is model.ClassificationONN
    assert train.TrainingConfig is config.TrainingConfig
    assert train.BasicConfig is config.BasicConfig
    assert train.ModelConfig is config.ModelConfig
    assert train.TrainingConfig.__module__.endswith(".config")
    assert train.BasicConfig.__module__.endswith(".config")
    assert train.ModelConfig.__module__.endswith(".config")
    removed_config_names = (
        "Train" + "Config",
        "Classification" + "BasicConfig",
        "Classification" + "ModelConfig",
        "Classification" + "TrainingConfig",
    )
    for removed_name in removed_config_names:
        assert not hasattr(train, removed_name)
    assert train.visualize_confusion_matrix is visualize.visualize_confusion_matrix
    assert (
        train.visualize_optical_readout_examples
        is visualize.visualize_optical_readout_examples
    )
    assert train.visualize_per_class_accuracy is visualize.visualize_per_class_accuracy
    assert train.visualize_training_curves is visualize.visualize_training_curves
    assert train.visualize_training_dynamics is visualize.visualize_training_dynamics


def test_run_training_writes_task5_artifacts_and_epoch_csv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    训练产物完整性
    """
    dataloaders = {"train": [_batch([0])], "val": [_batch([0])]}
    _TinyModel.calls = []

    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        _build_classification_dataloaders_fake(dataloaders),
    )
    monkeypatch.setattr(experiment, "ClassificationONN", _TinyModel)

    result = train.run_training(
        train.TrainingConfig(
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
    assert (root / "config.json").exists()
    assert (root / "runtime.json").exists()
    assert (root / "summary.md").exists()
    assert (root / "model_checkpoints" / "best.pt").exists()
    assert (root / "model_checkpoints" / "last.pt").exists()
    assert not (root / "diagnostic_figures" / "training_curves.png").exists()
    assert not (root / "diagnostic_figures" / "training_curves.svg").exists()
    _assert_publication_figure_pair(root, "01_training_dynamics")
    _assert_publication_figure_pair(root, "02_confusion_matrix")
    _assert_publication_figure_pair(root, "03_per_class_accuracy")
    _assert_publication_figure_pair(root, "04_optical_readout_examples_upper")
    _assert_publication_figure_pair(root, "04_optical_readout_examples_lower")
    assert not (root / "diagnostic_figures" / "04_optical_readout_examples.png").exists()
    assert not (root / "diagnostic_figures" / "04_optical_readout_examples.svg").exists()

    rows = list(csv.DictReader((root / "epoch_metrics.csv").open(encoding="utf-8")))
    assert rows[0].keys() == {
        "epoch",
        "train_loss",
        "val_loss",
        "train_accuracy",
        "val_accuracy",
        "seconds",
    }
    assert rows[0]["epoch"] == "1"
    assert float(rows[0]["train_accuracy"]) == pytest.approx(1.0)
    assert float(rows[0]["val_accuracy"]) == pytest.approx(1.0)

    final_metrics = json.loads((root / "final_metrics.json").read_text(encoding="utf-8"))
    assert final_metrics["evaluation_split"] == "val"
    assert final_metrics["test_loader_available"] is False
    assert final_metrics["test_accuracy"] is None
    assert "accuracy" in final_metrics
    assert final_metrics["evaluation_accuracy"] == pytest.approx(1.0)
    assert final_metrics["accuracy"] == pytest.approx(
        final_metrics["evaluation_accuracy"]
    )
    assert final_metrics["validation_accuracy_substitute"] == pytest.approx(
        final_metrics["evaluation_accuracy"]
    )

    readout_path = root / "diagnostic_figures" / "readout_examples.json"
    assert readout_path.exists()
    _assert_readout_examples_schema(readout_path)
    summary_text = (root / "summary.md").read_text(encoding="utf-8")
    assert "diagnostic_figures/01_training_dynamics.png" in summary_text
    assert "diagnostic_figures/02_confusion_matrix.png" in summary_text
    assert "diagnostic_figures/03_per_class_accuracy.png" in summary_text
    assert "diagnostic_figures/04_optical_readout_examples_upper.png" in summary_text
    assert "diagnostic_figures/04_optical_readout_examples_lower.png" in summary_text
    assert "diagnostic_figures/04_optical_readout_examples.png" not in summary_text
    assert "diagnostic_figures/02_evaluation_summary.png" not in summary_text
    assert "diagnostic_figures/readout_examples.json" in summary_text
    assert (
        "- 02_confusion_matrix: diagnostic_figures/02_confusion_matrix.png"
        in summary_text
    )
    assert (
        "- 03_per_class_accuracy: diagnostic_figures/03_per_class_accuracy.png"
        in summary_text
    )
    assert (
        "- diagnostic_training_curves: diagnostic_figures/training_curves.png"
        not in summary_text
    )
    assert "legacy_" not in summary_text


def test_run_training_rejects_retired_no_lens_topology(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    拒绝旧拓扑名
    """
    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        lambda **kwargs: pytest.fail("dataloader should not be built"),
    )

    with pytest.raises(ValueError, match="Unsupported topology"):
        train.run_training(
            train.TrainingConfig(
                topology="no_lens",
                epochs=1,
                project_root=tmp_path,
            )
        )


def test_run_training_replaces_stale_epoch_csv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    重复运行清理契约
    """
    dataloaders = {"train": [_batch([0])], "val": [_batch([0])]}
    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        _build_classification_dataloaders_fake(dataloaders),
    )
    monkeypatch.setattr(experiment, "ClassificationONN", _TinyModel)
    training_config = train.TrainingConfig(
        epochs=1,
        learning_rate=0.0,
        project_root=tmp_path,
        run_name="repeat",
    )

    train.run_training(training_config)
    train.run_training(training_config)

    history_path = (
        tmp_path
        / "results"
        / "classification"
        / "without_lens"
        / "repeat"
        / "epoch_metrics.csv"
    )
    rows = list(csv.DictReader(history_path.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["epoch"] == "1"


def test_run_training_rejects_path_traversal_run_name_before_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    路径穿越防护
    """
    victim_epoch_metrics = (
        tmp_path
        / "results"
        / "classification"
        / "victim"
        / "epoch_metrics.csv"
    )
    victim_epoch_metrics.parent.mkdir(parents=True)
    victim_epoch_metrics.write_text("do not delete\n", encoding="utf-8")
    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        lambda **kwargs: pytest.fail("dataloader should not be built"),
    )

    with pytest.raises(ValueError, match="run_name"):
        train.run_training(
            train.TrainingConfig(
                epochs=1,
                project_root=tmp_path,
                run_name="../victim",
            )
        )

    assert victim_epoch_metrics.read_text(encoding="utf-8") == "do not delete\n"


def test_run_training_uses_test_loader_when_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    优先使用测试集指标
    """
    dataloaders = {
        "train": [_batch([0])],
        "val": [_batch([0])],
        "test": [_batch([1])],
    }
    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        _build_classification_dataloaders_fake(dataloaders),
    )
    monkeypatch.setattr(experiment, "ClassificationONN", _TinyModel)

    result = train.run_training(
        train.TrainingConfig(
            epochs=1,
            learning_rate=0.0,
            project_root=tmp_path,
            run_name="test_split",
        )
    )

    final_metrics = result["final_metrics"]
    assert final_metrics["evaluation_split"] == "test"
    assert final_metrics["test_loader_available"] is True
    assert final_metrics["test_accuracy"] == pytest.approx(0.0)
    assert final_metrics["evaluation_accuracy"] == pytest.approx(0.0)
    assert "accuracy" in final_metrics
    assert "evaluation_accuracy" in final_metrics
    assert final_metrics["accuracy"] == pytest.approx(
        final_metrics["evaluation_accuracy"]
    )
    assert "validation_accuracy_substitute" not in final_metrics


def test_run_training_writes_empty_readout_artifacts_when_no_examples(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    空读出写入警告
    """
    dataloaders = {"train": [_batch([0])], "val": [_batch([0])]}
    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        _build_classification_dataloaders_fake(dataloaders),
    )
    monkeypatch.setattr(experiment, "ClassificationONN", _TinyModel)

    def collect_empty_readout_examples_stub(*args: object, **kwargs: object) -> list:
        """
        Return no optical readout examples.
        """
        return []

    monkeypatch.setattr(
        experiment,
        "_collect_readout_examples",
        collect_empty_readout_examples_stub,
    )

    training_config = _one_epoch_training_config(tmp_path, "empty_readout")
    train.run_training(training_config)

    root = tmp_path / "results" / "classification" / "without_lens" / "empty_readout"
    readout_path = root / "diagnostic_figures" / "readout_examples.json"
    assert readout_path.exists()
    payload = json.loads(readout_path.read_text(encoding="utf-8"))
    assert set(payload) == {"examples", "warnings"}
    assert payload["examples"] == []
    assert payload["warnings"] == ["No optical readout examples were collected."]
    _assert_publication_figure_pair(root, "04_optical_readout_examples_upper")
    _assert_publication_figure_pair(root, "04_optical_readout_examples_lower")
    assert not (root / "diagnostic_figures" / "04_optical_readout_examples.png").exists()
    assert not (root / "diagnostic_figures" / "04_optical_readout_examples.svg").exists()


@pytest.mark.parametrize("epochs", [0, -1])
def test_run_training_rejects_non_positive_epochs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    epochs: int,
) -> None:
    """
    非法 epoch 先失败
    """
    monkeypatch.setattr(
        experiment,
        "build_classification_dataloaders",
        lambda **kwargs: pytest.fail("dataloader should not be built"),
    )

    with pytest.raises(ValueError, match="epochs"):
        train.run_training(train.TrainingConfig(epochs=epochs, project_root=tmp_path))


def test_parse_args_accepts_canonical_topologies(tmp_path: Path) -> None:
    """
    接受规范拓扑
    """
    normalized = train.parse_args(
        ["--topology", "without_lens", "--project-root", str(tmp_path)]
    )

    assert normalized.topology == "without_lens"
    assert normalized.epochs == 50


def test_parse_args_rejects_retired_no_lens_topology(tmp_path: Path) -> None:
    """
    拒绝旧 CLI 拓扑
    """
    with pytest.raises(SystemExit):
        train.parse_args(["--topology", "no_lens", "--project-root", str(tmp_path)])

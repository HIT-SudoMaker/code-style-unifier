from __future__ import annotations

from collections.abc import Iterable, Mapping

import pytest
import torch

from experiments.classification import engine
from experiments.classification import train


class _TinyModule(torch.nn.Module):
    def __init__(self) -> None:
        """
        训练模块替身
        """
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor(0.0))
        self.forward_modes: list[tuple[bool, bool]] = []

    def forward(self, input_field: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        返回探测器预测和占位强度
        """
        self.forward_modes.append((self.training, torch.is_grad_enabled()))
        prediction = input_field.float() * self.weight
        intensity = torch.zeros((input_field.shape[0], 1, 2, 2), dtype=torch.float32)
        return prediction, intensity


def _batch(
    labels: list[int],
    *,
    target_value: float = 10.0,
) -> dict[str, torch.Tensor]:
    return {
        "input_field": torch.ones((len(labels), 3), dtype=torch.float32),
        "target_detector_distribution": torch.full(
            (len(labels), 3),
            target_value,
            dtype=torch.float32,
        ),
        "label": torch.tensor(labels),
    }


class _RecordingCriterion(torch.nn.Module):
    def __init__(self) -> None:
        """
        损失目标记录器
        """
        super().__init__()
        self.targets: list[torch.Tensor] = []

    def forward(
        self,
        prediction: torch.Tensor,
        target_distribution: torch.Tensor,
    ) -> torch.Tensor:
        """
        记录目标分布并返回 MSE
        """
        self.targets.append(target_distribution.detach().clone())
        return torch.nn.functional.mse_loss(
            prediction,
            target_distribution,
            reduction="sum",
        )


def _sample_count(dataloader: Iterable[Mapping[str, object]]) -> int:
    return sum(int(batch["label"].shape[0]) for batch in dataloader)


def test_build_target_distribution_scales_by_split() -> None:
    """
    按训练和评估规则缩放目标
    """
    target = torch.tensor([[10.0, 20.0]])

    train_target = engine.build_target_distribution(target, split="train")
    val_target = engine.build_target_distribution(target, split="val")
    test_target = engine.build_target_distribution(target, split="test")

    assert torch.allclose(train_target, torch.tensor([[1.0, 2.0]]))
    assert torch.allclose(val_target, torch.tensor([[0.1, 0.2]]))
    assert torch.allclose(test_target, torch.tensor([[0.1, 0.2]]))


def test_build_target_distribution_rejects_unsupported_split() -> None:
    """
    目标分布 split 校验
    """
    with pytest.raises(ValueError, match="split"):
        engine.build_target_distribution(torch.ones((1, 3)), split="dev")


def test_extract_batch_returns_tensors_on_device_with_label_contract() -> None:
    """
    批次张量设备契约
    """
    batch = {
        "input_field": [[1.0, 2.0, 3.0]],
        "target_detector_distribution": [[10, 20, 30]],
        "label": [2],
    }

    input_field, labels, target_distribution = engine._extract_batch(
        batch,
        torch.device("cpu"),
    )

    assert input_field.device.type == "cpu"
    assert labels.device.type == "cpu"
    assert target_distribution.device.type == "cpu"
    assert labels.dtype == torch.long
    assert target_distribution.dtype == torch.float32
    assert torch.equal(target_distribution, torch.tensor([[10.0, 20.0, 30.0]]))


def test_run_epoch_uses_optimizer_train_mode_and_train_target_scaling() -> None:
    """
    单轮训练契约
    """
    model = _TinyModule()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    criterion = _RecordingCriterion()
    dataloader = [_batch([0, 0], target_value=10.0)]

    loss, accuracy = engine._run_epoch(
        model=model,
        dataloader=dataloader,
        criterion=criterion,
        optimizer=optimizer,
        device=torch.device("cpu"),
    )

    assert model.forward_modes == [(True, True)]
    assert model.weight.detach().item() != pytest.approx(0.0)
    assert torch.allclose(criterion.targets[0], torch.ones((2, 3)))
    assert loss == pytest.approx(6.0 / _sample_count(dataloader))
    assert accuracy == pytest.approx(1.0)


def test_evaluate_loss_accuracy_uses_eval_no_grad_and_split_target_scaling() -> None:
    """
    评估缩放契约
    """
    model = _TinyModule()
    criterion = _RecordingCriterion()
    dataloader = [_batch([1, 0], target_value=10.0)]

    loss, accuracy = engine._evaluate_loss_accuracy(
        model=model,
        dataloader=dataloader,
        criterion=criterion,
        device=torch.device("cpu"),
        split="test",
    )

    assert model.forward_modes == [(False, False)]
    assert torch.allclose(criterion.targets[0], torch.full((2, 3), 0.1))
    assert loss == pytest.approx(0.06 / _sample_count(dataloader))
    assert accuracy == pytest.approx(0.5)


def test_train_module_reexports_engine_surface() -> None:
    """
    训练模块引擎接口
    """
    assert train.build_target_distribution is engine.build_target_distribution
    assert train._extract_batch is engine._extract_batch
    assert train._run_epoch is engine._run_epoch
    assert train._evaluate_loss_accuracy is engine._evaluate_loss_accuracy

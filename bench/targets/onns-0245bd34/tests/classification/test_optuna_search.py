from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys
import types

import pytest


def test_optuna_search_exposes_named_public_entry_point() -> None:
    """
    Optuna 搜索公开入口命名
    """
    from experiments.classification import optuna_search

    assert hasattr(optuna_search, "run_optuna_search")
    assert not hasattr(optuna_search, "run")


def test_optuna_missing_writes_skipped_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Optuna 缺失摘要
    """
    from experiments.classification import optuna_search

    monkeypatch.setattr(optuna_search.importlib.util, "find_spec", lambda name: None)

    summary = optuna_search.run_optuna_search(
        project_root=tmp_path,
        trials=2,
        device="cpu",
    )

    assert summary["status"] == "SKIPPED"
    assert (
        tmp_path / "results" / "classification" / "optuna" / "summary.md"
    ).exists()


def test_optuna_skipped_clears_stale_trial_artifacts(tmp_path: Path) -> None:
    """
    Optuna 跳过清理
    """
    from experiments.classification import optuna_search

    output_dir = tmp_path / "results" / "classification" / "optuna"
    output_dir.mkdir(parents=True)
    (output_dir / "optuna_trials.csv").write_text("stale\n", encoding="utf-8")
    (output_dir / "optimization_history.png").write_text("stale", encoding="utf-8")

    summary = optuna_search.write_skipped(project_root=tmp_path, reason="skip")

    assert summary["status"] == "SKIPPED"
    assert not (output_dir / "optuna_trials.csv").exists()
    assert not (output_dir / "optimization_history.png").exists()
    assert (output_dir / "summary.md").exists()


def test_save_optimization_history_uses_classification_local_style(
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    from experiments.classification import optuna_search

    class FakeTrial:
        def __init__(self, number: int, value: float) -> None:
            """
            初始化历史 trial 记录项
            """
            self.number = number
            self.value = value

    study = types.SimpleNamespace(
        trials=[
            FakeTrial(0, 0.25),
            FakeTrial(1, 0.5),
        ]
    )

    warnings = optuna_search._save_optimization_history(study, tmp_path)

    assert warnings == []
    assert (tmp_path / "optimization_history.png").exists()
    assert (tmp_path / "optimization_history.svg").exists()
    source = Path(optuna_search.__file__).read_text(encoding="utf-8")
    assert "experiments.figure_style" not in source
    assert "_CLASSIFICATION_STYLE" not in source
    assert "_CLASSIFICATION_PALETTE" not in source


def test_optuna_search_uses_training_without_default_retrain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Optuna 默认重训策略
    """
    from experiments.classification import optuna_search

    class FakeTrial:
        """
        提供 Optuna trial 替身
        """

        def __init__(self, number: int) -> None:
            """
            确定性 trial 替身
            """
            self.number = number
            self.params: dict[str, object] = {}
            self.value: float | None = None

        def suggest_float(
            self,
            name: str,
            low: float,
            high: float,
            **kwargs: object,
        ) -> float:
            """
            返回固定浮点建议
            """
            del low, high, kwargs
            value = 0.01 if name == "learning_rate" else 0.0001
            self.params[name] = value
            return value

        def suggest_categorical(self, name: str, choices: list[object]) -> object:
            """
            返回首个分类候选
            """
            value = choices[0]
            self.params[name] = value
            return value

        def suggest_int(self, name: str, low: int, high: int) -> int:
            """
            返回整数下界
            """
            assert name == "epochs"
            assert low == 1
            assert high == 3
            self.params[name] = low
            return low

    class FakeStudy:
        """
        提供 Optuna study 替身
        """

        def __init__(self) -> None:
            """
            空 study 替身
            """
            self.trials: list[FakeTrial] = []
            self.best_trial: FakeTrial | None = None
            self.best_params: dict[str, object] = {}
            self.best_value = 0.0

        def optimize(
            self,
            objective: Callable[[FakeTrial], float],
            n_trials: int,
        ) -> None:
            """
            运行 fake trial 并记录最优值
            """
            for number in range(n_trials):
                trial = FakeTrial(number)
                trial.value = float(objective(trial))
                self.trials.append(trial)
            self.best_trial = max(self.trials, key=lambda item: item.value or 0.0)
            self.best_params = dict(self.best_trial.params)
            self.best_value = float(self.best_trial.value or 0.0)

    fake_optuna = types.SimpleNamespace(
        create_study=lambda direction: FakeStudy(),
        visualization=types.SimpleNamespace(),
    )
    monkeypatch.setattr(
        optuna_search.importlib.util,
        "find_spec",
        lambda name: object() if name == "optuna" else None,
    )
    monkeypatch.setitem(sys.modules, "optuna", fake_optuna)
    seen_epochs: list[int] = []
    seen_scheduler_flags: list[bool] = []

    def fake_run_training(
        config: optuna_search.TrainingConfig,
        project_root: Path | None = None,
    ) -> dict[str, object]:
        """
        记录 trial 训练配置
        """
        del project_root
        seen_epochs.append(config.epochs)
        seen_scheduler_flags.append(config.is_scheduler_enabled)
        return {
            "final_metrics": {
                "best_val_accuracy": 0.25 + len(seen_epochs) * 0.1,
                "test_accuracy": 0.2,
            }
        }

    monkeypatch.setattr(optuna_search, "run_training", fake_run_training)

    summary = optuna_search.run_optuna_search(
        project_root=tmp_path,
        trials=2,
        device="cpu",
    )

    output_dir = tmp_path / "results" / "classification" / "optuna"
    assert summary["status"] == "PASS"
    assert seen_epochs == [1, 1]
    assert seen_scheduler_flags == [False, False]
    assert (output_dir / "optuna_trials.csv").exists()
    assert (output_dir / "best_params.json").exists()
    assert (output_dir / "best_trial_summary.txt").exists()


def test_optuna_search_uses_search_config_space_and_keyword_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    from experiments.classification import optuna_search
    from experiments.classification.config import SearchConfig

    class FakeTrial:
        def __init__(self, number: int) -> None:
            """
            初始化搜索 trial 记录项
            """
            self.number = number
            self.params: dict[str, object] = {}
            self.value: float | None = None

        def suggest_float(
            self,
            name: str,
            low: float,
            high: float,
            **kwargs: object,
        ) -> float:
            """
            返回测试 Optuna 浮点候选值
            """
            if name == "learning_rate":
                assert low == pytest.approx(1e-3)
                assert high == pytest.approx(2e-3)
                assert kwargs == {"log": True}
                value = low
            else:
                assert name == "propagation_distance"
                assert low == pytest.approx(3e-3)
                assert high == pytest.approx(4e-3)
                value = high
            self.params[name] = value
            return value

        def suggest_categorical(self, name: str, choices: list[object]) -> object:
            """
            返回测试 Optuna 分类候选值
            """
            expected_choices = {
                "topology": ["with_lens"],
                "batch_size": [64],
                "resize_mode": ["nearest"],
            }
            assert choices == expected_choices[name]
            value = choices[0]
            self.params[name] = value
            return value

        def suggest_int(self, name: str, low: int, high: int) -> int:
            """
            返回测试 Optuna 整数候选值
            """
            assert name == "epochs"
            assert low == 1
            assert high == 2
            self.params[name] = low
            return low

    class FakeStudy:
        def __init__(self) -> None:
            """
            初始化搜索 study 状态
            """
            self.trials: list[FakeTrial] = []
            self.best_trial: FakeTrial | None = None
            self.best_params: dict[str, object] = {}
            self.best_value = 0.0

        def optimize(
            self,
            objective: Callable[[FakeTrial], float],
            n_trials: int,
        ) -> None:
            """
            执行测试 Optuna 优化流程
            """
            assert n_trials == 1
            trial = FakeTrial(0)
            trial.value = float(objective(trial))
            self.trials.append(trial)
            self.best_trial = trial
            self.best_params = dict(trial.params)
            self.best_value = float(trial.value or 0.0)

    fake_optuna = types.SimpleNamespace(
        create_study=lambda direction: FakeStudy(),
        visualization=types.SimpleNamespace(),
    )
    monkeypatch.setattr(
        optuna_search.importlib.util,
        "find_spec",
        lambda name: object() if name == "optuna" else None,
    )
    monkeypatch.setitem(sys.modules, "optuna", fake_optuna)
    seen_configs: list[optuna_search.TrainingConfig] = []

    def fake_run_training(
        config: optuna_search.TrainingConfig,
        project_root: Path | None = None,
    ) -> dict[str, object]:
        """
        捕获解析后的训练配置
        """
        del project_root
        seen_configs.append(config)
        return {"final_metrics": {"best_val_accuracy": 0.75}}

    monkeypatch.setattr(optuna_search, "run_training", fake_run_training)

    search = SearchConfig(
        trials=5,
        trial_epochs=2,
        seed=100,
        samples_per_class=9,
        topology_candidates=("with_lens",),
        batch_size_candidates=(64,),
        resize_mode_candidates=("nearest",),
        learning_rate_range=(1e-3, 2e-3),
        propagation_distance_range=(3e-3, 4e-3),
    )
    summary = optuna_search.run_optuna_search(
        project_root=tmp_path,
        device="cpu",
        search=search,
        trials=1,
    )

    assert summary["status"] == "PASS"
    assert len(seen_configs) == 1
    assert seen_configs[0].topology == "with_lens"
    assert seen_configs[0].batch_size == 64
    assert seen_configs[0].resize_mode == "nearest"
    assert seen_configs[0].learning_rate == pytest.approx(1e-3)
    assert seen_configs[0].propagation_distance == pytest.approx(4e-3)
    assert seen_configs[0].seed == 100
    assert seen_configs[0].samples_per_class == 9


def test_resolve_search_config_explicit_samples_none_clears_search_value() -> None:
    """
    验证分类测试契约保持稳定
    """
    from experiments.classification import optuna_search
    from experiments.classification.config import SearchConfig

    resolved = optuna_search._resolve_search_config(
        SearchConfig(samples_per_class=7),
        samples_per_class=None,
    )

    assert resolved.samples_per_class is None


def test_resolve_search_config_retains_search_samples_when_override_omitted() -> None:
    """
    验证分类测试契约保持稳定
    """
    from experiments.classification import optuna_search
    from experiments.classification.config import SearchConfig

    resolved = optuna_search._resolve_search_config(SearchConfig(samples_per_class=7))

    assert resolved.samples_per_class == 7


def test_optuna_main_builds_search_config_from_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    from experiments.classification import optuna_search
    from experiments.classification.config import SearchConfig

    seen: dict[str, object] = {}

    def fake_run_optuna_search(
        project_root: str | Path,
        device: str,
        *,
        search: SearchConfig | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        """
        捕获 CLI 传入参数
        """
        seen["project_root"] = Path(project_root)
        seen["device"] = device
        seen["search"] = search
        seen["kwargs"] = kwargs
        return {"status": "PASS"}

    monkeypatch.setattr(optuna_search, "run_optuna_search", fake_run_optuna_search)

    result = optuna_search.main(
        [
            "--project-root",
            str(tmp_path),
            "--trials",
            "4",
            "--device",
            "cpu",
            "--retrain-best",
            "--trial-epochs",
            "2",
            "--samples-per-class",
            "3",
        ]
    )

    assert result["status"] == "PASS"
    assert seen["project_root"] == tmp_path
    assert seen["device"] == "cpu"
    assert seen["kwargs"] == {}
    search = seen["search"]
    assert isinstance(search, SearchConfig)
    assert search.trials == 4
    assert search.trial_epochs == 2
    assert search.is_best_retraining_enabled is True
    assert search.samples_per_class == 3

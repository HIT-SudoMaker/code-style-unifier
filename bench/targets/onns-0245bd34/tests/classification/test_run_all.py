from __future__ import annotations

from pathlib import Path

import pytest


def test_run_all_defaults_to_canonical_baselines_without_optuna(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    from experiments.classification import run_all

    calls: list[str] = []

    def fake_run_training(config: object) -> dict[str, object]:
        """
        记录默认基线训练配置
        """
        calls.append(f"train:{config.topology}:{config.epochs}")
        return {"status": "PASS", "topology": config.topology}

    def fake_write_skipped(
        *,
        project_root: Path,
        reason: str,
    ) -> dict[str, str]:
        """
        记录 Optuna 跳过摘要参数
        """
        calls.append(f"skip:{Path(project_root).name}:{reason}")
        return {"status": "SKIPPED"}

    def fake_optuna_run(**kwargs: object) -> None:
        """
        防止默认流程运行 Optuna
        """
        raise AssertionError("Optuna should not run by default")

    monkeypatch.setattr(run_all.train, "run_training", fake_run_training)
    monkeypatch.setattr(run_all.optuna_search, "write_skipped", fake_write_skipped)
    monkeypatch.setattr(run_all.optuna_search, "run_optuna_search", fake_optuna_run)
    monkeypatch.setattr(
        run_all.reference_comparison,
        "run",
        lambda project_root: {"status": "PASS"},
    )
    monkeypatch.setattr(
        run_all.report,
        "run",
        lambda project_root: Path(project_root) / "summary.md",
    )

    result = run_all.run(project_root=tmp_path, epochs=3, device="cpu")

    assert result["optuna"] == {"status": "SKIPPED"}
    assert calls == [
        "train:without_lens:3",
        "train:with_lens:3",
        f"skip:{tmp_path.name}:Optuna search skipped for canonical baseline run.",
    ]


def test_run_all_still_runs_only_two_public_topologies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    import experiments.classification.run_all as run_all

    seen: list[str] = []

    def _fake_run_training(config: object) -> dict[str, object]:
        """
        记录规范基线拓扑
        """
        seen.append(config.topology)
        return {"final_metrics": {"evaluation_accuracy": 0.91}}

    monkeypatch.setattr(run_all.train, "run_training", _fake_run_training)
    monkeypatch.setattr(run_all.optuna_search, "write_skipped", lambda **kwargs: {})
    monkeypatch.setattr(run_all.reference_comparison, "run", lambda **kwargs: {})
    monkeypatch.setattr(run_all.report, "run", lambda **kwargs: tmp_path / "summary.md")

    run_all.run(project_root=tmp_path, epochs=1, device="cpu")

    assert seen == ["without_lens", "with_lens"]


def test_run_all_runs_optuna_only_when_explicitly_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    from experiments.classification import run_all

    calls: list[str] = []

    def fake_run_training(config: object) -> dict[str, object]:
        """
        记录启用搜索前训练配置
        """
        calls.append(f"train:{config.topology}:{config.epochs}")
        return {"status": "PASS", "topology": config.topology}

    def fake_optuna_run(**kwargs: object) -> dict[str, str]:
        """
        记录显式 Optuna 搜索参数
        """
        calls.append(f"optuna:{kwargs['trials']}:{Path(kwargs['project_root']).name}")
        return {"status": "PASS"}

    def fake_write_skipped(**kwargs: object) -> None:
        """
        防止启用搜索时写入跳过摘要
        """
        raise AssertionError("Optuna skip writer should not run when enabled")

    monkeypatch.setattr(run_all.train, "run_training", fake_run_training)
    monkeypatch.setattr(run_all.optuna_search, "run_optuna_search", fake_optuna_run)
    monkeypatch.setattr(run_all.optuna_search, "write_skipped", fake_write_skipped)
    monkeypatch.setattr(
        run_all.reference_comparison,
        "run",
        lambda project_root: {"status": "PASS"},
    )
    monkeypatch.setattr(
        run_all.report,
        "run",
        lambda project_root: Path(project_root) / "summary.md",
    )

    result = run_all.run(
        project_root=tmp_path,
        epochs=2,
        device="cpu",
        is_optuna_enabled=True,
        optuna_trials=4,
    )

    assert result["optuna"] == {"status": "PASS"}
    assert calls == [
        "train:without_lens:2",
        "train:with_lens:2",
        f"optuna:4:{tmp_path.name}",
    ]


def test_parse_args_uses_enable_optuna_flag() -> None:
    """
    验证分类测试契约保持稳定
    """
    from experiments.classification import run_all

    default_args = run_all.parse_args([])
    enabled_args = run_all.parse_args(["--enable-optuna", "--optuna-trials", "3"])

    assert default_args.enable_optuna is False
    assert enabled_args.enable_optuna is True
    assert enabled_args.optuna_trials == 3

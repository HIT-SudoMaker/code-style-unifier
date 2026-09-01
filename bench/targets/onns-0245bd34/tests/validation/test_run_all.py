from __future__ import annotations

from pathlib import Path


def test_run_all_clears_stale_output_and_runs_all_suites(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证 run_all 清空旧产物并调度全部验证器
    """

    from experiments.validation import run_all

    stale_file = tmp_path / "layers" / "old" / "stale.png"
    stale_file.parent.mkdir(parents=True)
    stale_file.write_text("old", encoding="utf-8")

    calls: list[str] = []

    def _run_data(**kwargs: object) -> dict[str, object]:
        calls.append(f"data:{kwargs['size']}:{kwargs['device']}")
        return {"status": "PASS", "data": []}

    def _run_layers(**kwargs: object) -> dict[str, object]:
        calls.append(f"layers:{kwargs['size']}:{kwargs['device']}")
        return {"status": "PASS", "layers": []}

    monkeypatch.setattr(run_all.run_data, "run", _run_data)
    monkeypatch.setattr(run_all.run_layers, "run", _run_layers)

    result = run_all.run(output_root=tmp_path, device="cpu", size="tiny", seed=7)

    assert not stale_file.exists()
    assert result["status"] == "PASS"
    assert "systems" not in result
    assert calls == ["data:tiny:cpu", "layers:tiny:cpu"]


def test_run_all_accepts_validation_run_config(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证顶层 runner 接受 suite 级配置对象
    """
    from experiments.validation import run_all
    from experiments.validation.config import ValidationBasicConfig, ValidationRunConfig

    calls: list[str] = []

    def _run_data(**kwargs: object) -> dict[str, object]:
        calls.append(f"data:{kwargs['output_root']}:{kwargs['size']}:{kwargs['seed']}")
        return {"status": "PASS", "data": []}

    def _run_layers(**kwargs: object) -> dict[str, object]:
        calls.append(f"layers:{kwargs['output_root']}:{kwargs['size']}:{kwargs['seed']}")
        return {"status": "PASS", "layers": []}

    monkeypatch.setattr(run_all.run_data, "run", _run_data)
    monkeypatch.setattr(run_all.run_layers, "run", _run_layers)
    config = ValidationRunConfig(
        basic=ValidationBasicConfig(output_root=tmp_path, device="cpu", seed=11, size="tiny"),
        suites=("layers",),
    )

    result = run_all.run(config=config)

    assert result["status"] == "PASS"
    assert "data" not in result
    assert "systems" not in result
    assert calls == [f"layers:{tmp_path / 'layers'}:tiny:11"]


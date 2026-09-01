from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_run_data_runs_three_validators_and_continues_after_failure(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    调度器遇到失败后继续运行
    """
    from experiments.validation.data import run_data

    calls: list[str] = []

    def _validator(name: str, status: str) -> SimpleNamespace:
        def _run(**kwargs: object) -> dict[str, object]:
            del kwargs
            calls.append(name)
            return {"data": name, "status": status, "checks": []}

        return SimpleNamespace(run=_run)

    monkeypatch.setattr(
        run_data,
        "VALIDATORS",
        (
            _validator("raw_sources", "PASS"),
            _validator("degradation_scenarios", "FAIL"),
            _validator("end_to_end_pipeline", "PASS"),
        ),
    )

    result = run_data.run(output_root=tmp_path, device="cpu", size="tiny", seed=7)

    assert calls == [
        "raw_sources",
        "degradation_scenarios",
        "end_to_end_pipeline",
    ]
    assert result["status"] == "FAIL"
    assert [record["data"] for record in result["data"]] == calls


def test_run_data_default_validators_match_data_validation_suite() -> None:
    """
    默认只暴露三类验证器
    """
    from experiments.validation.data import run_data

    assert tuple(
        validator.__name__.rsplit(".", maxsplit=1)[-1]
        for validator in run_data.VALIDATORS
    ) == (
        "validate_raw_sources",
        "validate_degradation_scenarios",
        "validate_end_to_end_pipeline",
    )


def test_run_data_accepts_validation_basic_config(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证 data runner 接受基础配置对象
    """
    from experiments.validation.config import ValidationBasicConfig
    from experiments.validation.data import run_data

    calls: list[tuple[str, object, object]] = []

    def _run(**kwargs: object) -> dict[str, object]:
        calls.append((str(kwargs["output_root"]), kwargs["size"], kwargs["seed"]))
        return {"data": "raw_sources", "status": "PASS", "checks": []}

    monkeypatch.setattr(run_data, "VALIDATORS", (SimpleNamespace(run=_run),))

    result = run_data.run(
        config=ValidationBasicConfig(
            output_root=tmp_path,
            device="cpu",
            seed=11,
            size="tiny",
        )
    )

    assert result["status"] == "PASS"
    assert calls == [(str(tmp_path), "tiny", 11)]

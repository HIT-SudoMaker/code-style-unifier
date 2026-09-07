from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_run_layers_continues_after_layer_failure(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证单层失败不会阻断后续 layer 验证器
    """

    from experiments.validation.layers import run_layers

    calls: list[str] = []

    def _validator(name: str, status: str) -> SimpleNamespace:
        def _run(**kwargs: object) -> dict[str, object]:
            del kwargs
            calls.append(name)
            return {"layer": name, "status": status, "checks": []}

        return SimpleNamespace(run=_run)

    monkeypatch.setattr(
        run_layers,
        "VALIDATORS",
        (
            _validator("diffraction", "PASS"),
            _validator("modulation", "FAIL"),
            _validator("lens", "PASS"),
        ),
    )

    result = run_layers.run(output_root=tmp_path, device="cpu", size="tiny", seed=7)

    assert calls == ["diffraction", "modulation", "lens"]
    assert result["status"] == "FAIL"


def test_run_layers_accepts_validation_basic_config(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证 layers runner 接受基础配置对象
    """
    from experiments.validation.config import ValidationBasicConfig
    from experiments.validation.layers import run_layers

    calls: list[tuple[str, object, object]] = []

    def _run(**kwargs: object) -> dict[str, object]:
        calls.append((str(kwargs["output_root"]), kwargs["size"], kwargs["seed"]))
        return {"layer": "diffraction", "status": "PASS", "checks": []}

    monkeypatch.setattr(run_layers, "VALIDATORS", (SimpleNamespace(run=_run),))

    result = run_layers.run(
        config=ValidationBasicConfig(
            output_root=tmp_path,
            device="cpu",
            seed=11,
            size="tiny",
        )
    )

    assert result["status"] == "PASS"
    assert calls == [(str(tmp_path), "tiny", 11)]


def test_run_layers_uses_physical_layer_order(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证 runner 使用稳定的物理层阅读顺序
    """
    from experiments.validation.layers import run_layers

    calls: list[str] = []

    def _validator(name: str) -> SimpleNamespace:
        def _run(**kwargs: object) -> dict[str, object]:
            del kwargs
            calls.append(name)
            return {"layer": name, "status": "PASS", "checks": []}

        return SimpleNamespace(run=_run)

    monkeypatch.setattr(
        run_layers,
        "VALIDATORS",
        tuple(
            _validator(name)
            for name in ("diffraction", "modulation", "lens", "detection")
        ),
    )

    result = run_layers.run(output_root=tmp_path, device="cpu", size="tiny")

    assert result["status"] == "PASS"
    assert calls == ["diffraction", "modulation", "lens", "detection"]


@pytest.mark.parametrize(
    ("module_name", "layer_name"),
    (
        ("validate_diffraction", "diffraction"),
        ("validate_modulation", "modulation"),
        ("validate_lens", "lens"),
        ("validate_detection", "detection"),
    ),
)
def test_layer_validator_reports_unavailable_cuda_consistently(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module_name: str,
    layer_name: str,
) -> None:
    """
    验证 CUDA 缺席时检查、摘要与图像保持同一结论
    """
    import torch

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    validator = import_module(
        f"experiments.validation.layers.{module_name}",
    )
    if module_name == "validate_diffraction":
        monkeypatch.setattr(validator, "_BENCHMARK_REPEATS", 2)

    result = validator.run(
        output_root=tmp_path,
        device="cpu",
        seed=7,
        size="tiny",
    )

    cpu_gpu_check = next(
        check
        for check in result["checks"]
        if check["name"] == "cpu_gpu_consistency"
    )
    output_dir = tmp_path / layer_name
    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    device_svg = (output_dir / "device_agreement.svg").read_text(
        encoding="utf-8",
    )

    assert cpu_gpu_check["status"] == "SKIPPED"
    assert "cpu_gpu_consistency: SKIPPED" in summary
    assert "CUDA Unavailable" in device_svg

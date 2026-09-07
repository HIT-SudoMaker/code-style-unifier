from __future__ import annotations

import csv
from pathlib import Path


def test_modulation_validation_writes_source_aligned_evidence_suite(
    tmp_path: Path,
) -> None:
    """
    验证调制层生成六种相位、前向作用与设备证据
    """
    from experiments.validation.layers import validate_modulation

    result = validate_modulation.run(
        output_root=tmp_path,
        device="cpu",
        seed=7,
        size="tiny",
    )

    output_dir = tmp_path / "modulation"
    assert result["layer"] == "modulation"
    assert result["status"] == "PASS"
    assert [check["name"] for check in result["checks"]] == [
        "construction",
        "phase_generation",
        "amplitude_preservation",
        "feature_contract",
        "autograd_parameter_gradient",
        "cpu_gpu_consistency",
    ]
    figure_names = {
        "phase_construction",
        "trainable_phase_action",
        "device_agreement",
    }
    assert set(result["figures"]) == figure_names
    for figure_name in figure_names:
        assert (output_dir / f"{figure_name}.png").exists()
        assert (output_dir / f"{figure_name}.svg").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "summary.md").exists()
    assert not any(path.name[:2].isdigit() for path in output_dir.glob("*.png"))

    svg_text = (output_dir / "phase_construction.svg").read_text(
        encoding="utf-8",
    )
    for label in (
        "Normal",
        "Zeros",
        "Uniform",
        "Direct",
        "Sigmoid",
    ):
        assert label in svg_text

    field_svg = (output_dir / "trainable_phase_action.svg").read_text(encoding="utf-8")
    for label in (
        "Input Phase",
        "Effective Phase",
        "Output Phase",
    ):
        assert label in field_svg

    device_svg = (output_dir / "device_agreement.svg").read_text(encoding="utf-8")
    assert "CPU–GPU Absolute Difference" in device_svg

    rows = list(csv.DictReader((output_dir / "metrics.csv").open(encoding="utf-8")))
    metric_names = {row["metric"] for row in rows}
    assert {
        "amplitude_max_abs_error",
        "direct_phase_max_abs_error",
        "sigmoid_phase_max_abs_error",
        "modulation_phase_gradient_max_abs",
        "invalid_initialization_rejected",
        "invalid_parameterization_rejected",
    }.issubset(metric_names)
    if result["checks"][-1]["status"] == "PASS":
        assert {
            "cpu_gpu_direct_max_abs_error",
            "cpu_gpu_sigmoid_max_abs_error",
        }.issubset(metric_names)


def test_modulation_validation_main_accepts_cli_options(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证调制层命令行入口传递基础配置
    """
    from experiments.validation.layers import validate_modulation

    calls: list[dict[str, object]] = []

    def _run(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return {"layer": "modulation", "status": "PASS", "checks": []}

    monkeypatch.setattr(validate_modulation, "run", _run)
    result = validate_modulation.main(
        [
            "--output-root",
            str(tmp_path),
            "--device",
            "cpu",
            "--seed",
            "11",
            "--size",
            "tiny",
        ],
    )

    assert result["status"] == "PASS"
    assert calls == [
        {
            "output_root": tmp_path,
            "device": "cpu",
            "seed": 11,
            "size": "tiny",
        },
    ]

from __future__ import annotations

import csv
from pathlib import Path


def test_detection_validation_writes_source_aligned_evidence_suite(
    tmp_path: Path,
) -> None:
    """
    验证探测层生成强度响应与设备证据
    """
    from experiments.validation.layers import validate_detection

    result = validate_detection.run(
        output_root=tmp_path,
        device="cpu",
        seed=7,
        size="tiny",
    )

    output_dir = tmp_path / "detection"
    assert result["layer"] == "detection"
    assert result["status"] == "PASS"
    assert [check["name"] for check in result["checks"]] == [
        "construction",
        "intensity_readout",
        "normalization",
        "feature_contract",
        "autograd_input_gradient",
        "cpu_gpu_consistency",
    ]
    figure_names = {
        "intensity_response",
        "device_agreement",
    }
    assert set(result["figures"]) == figure_names
    for figure_name in figure_names:
        assert (output_dir / f"{figure_name}.png").exists()
        assert (output_dir / f"{figure_name}.svg").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "summary.md").exists()
    assert not any(path.name[:2].isdigit() for path in output_dir.glob("*.png"))

    svg_text = (output_dir / "intensity_response.svg").read_text(encoding="utf-8")
    for label in (
        "Input Amplitude",
        "Detected Intensity",
        "Normalized Intensity",
    ):
        assert label in svg_text

    device_svg = (output_dir / "device_agreement.svg").read_text(encoding="utf-8")
    assert "CPU–GPU Absolute Difference" in device_svg

    summary_text = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert "Status: PASS" in summary_text
    assert "Layer: detection" in summary_text
    cpu_gpu_status = result["checks"][-1]["status"]
    assert cpu_gpu_status in {"PASS", "SKIPPED"}
    assert f"cpu_gpu_consistency: {cpu_gpu_status}" in summary_text

    rows = list(csv.DictReader((output_dir / "metrics.csv").open(encoding="utf-8")))
    metric_names = {row["metric"] for row in rows}
    assert {
        "raw_intensity_max_abs_error",
        "normalized_peak_error",
        "zero_field_max_abs",
        "input_gradient_max_abs",
        "invalid_normalization_flag_raises",
    }.issubset(metric_names)
    if cpu_gpu_status == "PASS":
        assert {
            "cpu_gpu_raw_max_abs_error",
            "cpu_gpu_normalized_max_abs_error",
        }.issubset(metric_names)


def test_detection_validation_main_accepts_cli_options(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证探测层命令行入口传递基础配置
    """
    from experiments.validation.layers import validate_detection

    calls: list[dict[str, object]] = []

    def _run(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return {"layer": "detection", "status": "PASS", "checks": []}

    monkeypatch.setattr(validate_detection, "run", _run)
    result = validate_detection.main(
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

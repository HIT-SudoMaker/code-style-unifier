from __future__ import annotations

import csv
from pathlib import Path


def test_lens_validation_writes_source_aligned_evidence_suite(
    tmp_path: Path,
) -> None:
    """
    验证透镜层生成固定相位、前向作用与设备证据
    """
    from experiments.validation.layers import validate_lens

    result = validate_lens.run(
        output_root=tmp_path,
        device="cpu",
        seed=7,
        size="tiny",
    )

    output_dir = tmp_path / "lens"
    assert result["layer"] == "lens"
    assert result["status"] == "PASS"
    assert [check["name"] for check in result["checks"]] == [
        "construction",
        "phase_formula",
        "amplitude_preservation",
        "feature_contract",
        "cpu_gpu_consistency",
    ]
    figure_names = {
        "lens_phase",
        "fixed_phase_action",
        "device_agreement",
    }
    assert set(result["figures"]) == figure_names
    for figure_name in figure_names:
        assert (output_dir / f"{figure_name}.png").exists()
        assert (output_dir / f"{figure_name}.svg").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "summary.md").exists()
    assert not any(path.name[:2].isdigit() for path in output_dir.glob("*.png"))

    phase_svg = (output_dir / "lens_phase.svg").read_text(encoding="utf-8")
    for label in ("Converging Phase", "Diverging Phase"):
        assert label in phase_svg

    svg_text = (output_dir / "fixed_phase_action.svg").read_text(encoding="utf-8")
    for label in (
        "Input Phase",
        "Lens Phase",
        "Output Phase",
    ):
        assert label in svg_text

    device_svg = (output_dir / "device_agreement.svg").read_text(encoding="utf-8")
    assert "CPU–GPU Absolute Difference" in device_svg

    rows = list(csv.DictReader((output_dir / "metrics.csv").open(encoding="utf-8")))
    metric_names = {row["metric"] for row in rows}
    assert {
        "positive_phase_max_abs_error",
        "negative_phase_max_abs_error",
        "amplitude_max_abs_error",
        "invalid_wavelength_rejected",
        "invalid_focal_length_rejected",
        "invalid_pixel_size_rejected",
    }.issubset(metric_names)
    if result["checks"][-1]["status"] == "PASS":
        assert {
            "cpu_gpu_positive_focal_max_abs_error",
            "cpu_gpu_negative_focal_max_abs_error",
        }.issubset(metric_names)


def test_lens_validation_main_accepts_cli_options(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证透镜层命令行入口传递基础配置
    """
    from experiments.validation.layers import validate_lens

    calls: list[dict[str, object]] = []

    def _run(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return {"layer": "lens", "status": "PASS", "checks": []}

    monkeypatch.setattr(validate_lens, "run", _run)
    result = validate_lens.main(
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

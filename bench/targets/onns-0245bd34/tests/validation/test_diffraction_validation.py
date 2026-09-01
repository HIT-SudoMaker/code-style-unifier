from __future__ import annotations

import csv
from pathlib import Path


def test_diffraction_validation_writes_source_aligned_evidence_suite(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证衍射层生成与传播、传递函数、缓存和设备契约对齐的证据
    """
    from experiments.validation.layers import validate_diffraction

    assert validate_diffraction._BENCHMARK_REPEATS == 1000
    monkeypatch.setattr(validate_diffraction, "_BENCHMARK_REPEATS", 2)
    result = validate_diffraction.run(
        output_root=tmp_path,
        device="cpu",
        seed=7,
        size="tiny",
    )

    output_dir = tmp_path / "diffraction"
    assert result["layer"] == "diffraction"
    assert result["status"] == "PASS"
    assert [check["name"] for check in result["checks"]] == [
        "construction",
        "energy_conservation",
        "transfer_function",
        "plane_wave_phase",
        "cache_contract",
        "autograd_input_gradient",
        "cpu_gpu_consistency",
    ]
    figure_names = {
        "propagation_response",
        "transfer_evolution",
        "device_agreement",
        "cache_performance",
    }
    assert set(result["figures"]) == figure_names
    for figure_name in figure_names:
        assert (output_dir / f"{figure_name}.png").exists()
        assert (output_dir / f"{figure_name}.svg").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "summary.md").exists()
    assert not any(path.name[:2].isdigit() for path in output_dir.glob("*.png"))

    svg_text = (output_dir / "propagation_response.svg").read_text(encoding="utf-8")
    for label in (
        "Circular Aperture",
        "2.5 mm",
        "5.0 mm",
        "7.5 mm",
    ):
        assert label in svg_text

    transfer_svg = (output_dir / "transfer_evolution.svg").read_text(encoding="utf-8")
    for label in ("Transfer Amplitude", "Phase at 2.5 mm", "Phase at 5.0 mm", "Phase at 7.5 mm"):
        assert label in transfer_svg

    cache_svg = (output_dir / "cache_performance.svg").read_text(encoding="utf-8")
    for label in ("Forward", "Forward + Backward", "CPU", "2 evaluations"):
        assert label in cache_svg

    device_svg = (output_dir / "device_agreement.svg").read_text(encoding="utf-8")
    assert "CPU–GPU Absolute Difference" in device_svg

    rows = list(csv.DictReader((output_dir / "metrics.csv").open(encoding="utf-8")))
    metric_names = {row["metric"] for row in rows}
    assert {
        "energy_relative_error",
        "transfer_amplitude_max_abs_error",
        "plane_wave_max_abs_error",
        "cache_repeat_max_abs_error",
        "cpu_forward_cache_speedup",
        "cpu_training_cache_speedup",
        "input_gradient_max_abs",
        "invalid_wavelength_rejected",
        "invalid_pixel_size_rejected",
        "invalid_cache_flag_rejected",
    }.issubset(metric_names)


def test_diffraction_validation_main_accepts_cli_options(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    """
    验证衍射层命令行入口传递基础配置
    """
    from experiments.validation.layers import validate_diffraction

    calls: list[dict[str, object]] = []

    def _run(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        return {"layer": "diffraction", "status": "PASS", "checks": []}

    monkeypatch.setattr(validate_diffraction, "run", _run)
    result = validate_diffraction.main(
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


def test_diffraction_cold_benchmark_clears_cache_before_each_call(
    monkeypatch: object,
) -> None:
    """
    验证冷缓存协议逐次制造未命中而不是关闭缓存
    """
    import torch

    from experiments.validation.layers import validate_diffraction
    from layers import DiffractionLayer

    original = DiffractionLayer._clear_cache
    clear_calls = 0

    def _record_clear(layer: DiffractionLayer) -> None:
        nonlocal clear_calls
        clear_calls += 1
        original(layer)

    monkeypatch.setattr(DiffractionLayer, "_clear_cache", _record_clear)
    validate_diffraction._benchmark_condition(
        32,
        torch.device("cpu"),
        3,
        is_cold=False,
        includes_backward=False,
    )
    warm_clear_calls = clear_calls
    clear_calls = 0
    validate_diffraction._benchmark_condition(
        32,
        torch.device("cpu"),
        3,
        is_cold=True,
        includes_backward=False,
    )

    assert clear_calls - warm_clear_calls == 3

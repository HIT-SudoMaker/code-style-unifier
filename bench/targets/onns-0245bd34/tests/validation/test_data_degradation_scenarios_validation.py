from __future__ import annotations

import csv
from pathlib import Path


EXPECTED_CHECK_NAMES = {
    "noise_strength_control",
    "poisson_gaussian_strength_control",
    "blur_strength_control",
    "defocus_strength_control",
    "psf_convolution_contract",
    "edge_operator_contract",
    "deterministic_degradation_seed",
    "operation_provenance_contract",
}

EXPECTED_FIGURE_NAMES = {
    "01_gaussian_noise_strength_grid",
    "02_poisson_gaussian_strength_grid",
    "03_blur_strength_grid",
    "04_defocus_strength_grid",
    "05_psf_convolution_trace",
    "06_edge_operator_grid",
}

EXPECTED_OPERATION_NAMES = {
    "add_additive_gaussian_noise",
    "add_poisson_gaussian_noise",
    "apply_gaussian_blur",
    "apply_defocus_blur",
    "apply_psf_kernel",
    "build_canny_edge_map",
    "build_sobel_edge_map",
    "build_laplacian_of_gaussian_edge_map",
}


def test_degradation_scenarios_validation_writes_required_artifacts(
    tmp_path: Path,
) -> None:
    """
    验证退化场景validator会写出检查项、图像对和完整算子指标
    """
    from experiments.validation.data import validate_degradation_scenarios

    result = validate_degradation_scenarios.run(
        output_root=tmp_path,
        device="cpu",
        seed=7,
        size="tiny",
    )

    output_dir = tmp_path / "degradation_scenarios"
    assert result["data"] == "degradation_scenarios"
    assert result["status"] == "PASS"
    assert Path(result["output_dir"]) == output_dir
    assert {check["name"] for check in result["checks"]} == EXPECTED_CHECK_NAMES
    assert set(result["figures"]) == EXPECTED_FIGURE_NAMES
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "metrics.csv").exists()

    for figure_name in EXPECTED_FIGURE_NAMES:
        assert (output_dir / f"{figure_name}.png").exists()
        assert (output_dir / f"{figure_name}.svg").exists()

    metrics_text = (output_dir / "metrics.csv").read_text(encoding="utf-8")
    for operation_name in EXPECTED_OPERATION_NAMES:
        assert operation_name in metrics_text


def test_degradation_scenarios_deterministic_seed_check_is_exact(
    tmp_path: Path,
) -> None:
    """
    验证显式degradation_seed使重复执行完全一致
    """
    from experiments.validation.data import validate_degradation_scenarios

    result = validate_degradation_scenarios.run(
        output_root=tmp_path,
        device="cpu",
        seed=11,
        size="tiny",
    )

    deterministic_check = next(
        check
        for check in result["checks"]
        if check["name"] == "deterministic_degradation_seed"
    )
    assert deterministic_check["status"] == "PASS"
    assert deterministic_check["max_abs_error"] == 0.0

    with (tmp_path / "degradation_scenarios" / "metrics.csv").open(
        encoding="utf-8",
        newline="",
    ) as file_handle:
        rows = list(csv.DictReader(file_handle))

    deterministic_rows = [
        row for row in rows if row["scenario"] == "deterministic_repeat"
    ]
    assert deterministic_rows
    assert {row["operation"] for row in deterministic_rows} == {
        "add_additive_gaussian_noise"
    }
    assert {row["max_abs_error"] for row in deterministic_rows} == {"0.0"}

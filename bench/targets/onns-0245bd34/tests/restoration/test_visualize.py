from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import pytest
import torch

import experiments.restoration.fixed_measurement.learning.visualize as visualize
import experiments.restoration.fixed_measurement.learning.visualize_panels as visualize_panels
from experiments.figure_style import DEFAULT_FONT_SIZES
from experiments.restoration.fixed_measurement.learning.visualize import (
    FIGURE_TEXT_SPEC,
    visualize_edge_derived_intensity_mtf,
    visualize_frequency_response_comparison,
    visualize_grating_ctf,
    visualize_operating_point_summary,
    visualize_operating_point_trace,
    visualize_phase_mask_evolution,
    visualize_phase_offset_sensitivity,
    visualize_point_response,
    visualize_resolution_budget,
    visualize_restoration_examples,
    visualize_siemens_star_diagnostic,
    visualize_training_dynamics,
    visualize_usaf_resolution,
)


def test_characterization_figure_names_match_design() -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    assert FIGURE_TEXT_SPEC["01_resolution_budget"]["title"] == "Resolution Budget"
    assert FIGURE_TEXT_SPEC["02_point_response"]["title"] == "Point Response"
    assert (
        FIGURE_TEXT_SPEC["03_edge_derived_intensity_mtf"]["title"]
        == "Edge Derived Intensity MTF"
    )
    assert FIGURE_TEXT_SPEC["04_grating_ctf"]["title"] == "Grating CTF"
    assert FIGURE_TEXT_SPEC["05_usaf_resolution"]["title"] == "USAF Resolution"
    assert FIGURE_TEXT_SPEC["06_siemens_star_diagnostic"]["title"] == "Siemens Star Diagnostic"
    assert FIGURE_TEXT_SPEC["07_phase_offset_sensitivity"]["title"] == "Phase Offset Sensitivity"
    assert FIGURE_TEXT_SPEC["08_operating_point_summary"]["title"] == "Operating Point Summary"
    for spec in FIGURE_TEXT_SPEC.values():
        assert "_" not in spec["title"]


def test_restoration_palette_is_local_and_fixed() -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    assert visualize._RESTORATION_PALETTE == {
        "primary": "#587184",
        "primary_fill": "#8faec0",
        "secondary": "#7897a8",
        "warning": "#b06f6f",
        "accent": "#c98f65",
        "violet": "#817695",
        "neutral": "#d7dde2",
        "dark_text": "#000000",
        "muted_text": "#000000",
        "halo": "#f5f7f8",
        "panel_bg": "#ffffff",
    }


def test_restoration_uses_project_font_contract() -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    assert visualize._RESTORATION_STYLE.font_sizes == DEFAULT_FONT_SIZES
    assert not hasattr(visualize, "_RESTORATION_FONT_SIZES")


def test_restoration_visualize_uses_project_aesthetic_standard_colors() -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    source = Path(
        "experiments/restoration/fixed_measurement/learning/visualize.py"
    ).read_text(encoding="utf-8")

    assert "#4477aa" not in source
    assert "#228833" not in source
    assert "#cc6677" not in source
    assert "#ee7733" not in source
    assert "#aa3377" not in source
    assert "#bbbbbb" not in source
    assert "#222222" not in source
    assert "#666666" not in source
    assert "#1f77b4" not in source
    assert "#d62728" not in source


def test_apply_restoration_figure_style_applies_font_contract() -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    fig, axis = plt.subplots()
    try:
        axis.plot([0, 1], [0, 1], label="Series")
        axis.set_title("Subplot")
        axis.set_xlabel("x")
        axis.set_ylabel("y")
        axis.text(0.5, 0.5, "Annotation")
        axis.legend()
        fig.suptitle("Figure")

        visualize._apply_restoration_figure_style(fig)

        assert fig._suptitle.get_fontsize() == DEFAULT_FONT_SIZES.title
        assert axis.title.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.xaxis.label.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.yaxis.label.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.get_xticklabels()[0].get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.texts[0].get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.get_legend().get_texts()[0].get_fontsize() == DEFAULT_FONT_SIZES.text
    finally:
        plt.close(fig)


def test_restoration_visualize_uses_project_style_module_without_common_package() -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    source = Path(
        "experiments/restoration/fixed_measurement/learning/visualize.py"
    ).read_text(encoding="utf-8")

    assert "experiments.figure_style" in source
    assert "experiments.common" not in source
    assert "project_style" not in source
    assert "utils.figure_style" not in source


def test_save_figure_pair_uses_shared_style_helper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_named_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
        style: object,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        captured["name"] = name
        captured["style"] = style
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(visualize, "save_named_figure_pair", fake_save_named_figure_pair)

    fig, _axis = plt.subplots()
    outputs = visualize._save_figure_pair(fig, tmp_path, "style_probe")

    assert captured["name"] == "style_probe"
    assert captured["style"] == visualize._RESTORATION_STYLE
    assert visualize._RESTORATION_STYLE.dpi == 300
    assert outputs["png"].endswith("style_probe.png")
    assert outputs["svg"].endswith("style_probe.svg")


def test_restoration_visualize_functions_use_single_save_helper() -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    source = Path(
        "experiments/restoration/fixed_measurement/learning/visualize.py"
    ).read_text(encoding="utf-8")

    assert "_save_restoration_figure_pair" not in source
    assert "return _save_figure_pair(fig, output_dir, figure_name)" in source


def test_restoration_visualize_reexports_panel_helpers_from_panels_module() -> None:
    """
    楠岃瘉鍙鍖栨ā鍧楄浆鍙戠嫭绔嬮潰鏉垮啓鍏ュ櫒
    """
    assert visualize._PANEL_WRITERS["bar"] is visualize_panels.write_bar_figure
    assert (
        visualize._PANEL_WRITERS["edge_mtf"]
        is visualize_panels.write_edge_mtf_figure
    )
    assert (
        visualize._PANEL_WRITERS["grating_ctf"]
        is visualize_panels.write_grating_ctf_figure
    )
    assert (
        visualize._PANEL_WRITERS["point_response"]
        is visualize_panels.write_point_response_figure
    )
    assert (
        visualize._PANEL_WRITERS["labeled_bar"]
        is visualize_panels.write_labeled_bar_figure
    )
    assert visualize._PANEL_WRITERS["check"] is visualize_panels.write_check_figure


def test_visualize_resolution_budget_writes_png_and_svg(tmp_path: Path) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    budget = {
        "input_nyquist_frequency": 62500.0,
        "slm1_nyquist_frequency": 62500.0,
        "slm2_nyquist_frequency": 62500.0,
        "camera_nyquist_frequency": 172413.793,
        "aperture_cutoff_frequency": 36090.0,
    }

    outputs = visualize_resolution_budget(budget, tmp_path)

    assert Path(outputs["png"]).name == "01_resolution_budget.png"
    assert Path(outputs["svg"]).name == "01_resolution_budget.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()


def test_visualize_resolution_budget_uses_theoretical_budget_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        axis = fig.axes[0]
        captured["name"] = name
        captured["labels"] = [tick.get_text() for tick in axis.get_yticklabels()]
        captured["xlabel"] = axis.get_xlabel()
        captured["widths"] = [patch.get_width() for patch in axis.patches]
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", fake_save_figure_pair)

    visualize.visualize_resolution_budget(
        {
            "input_nyquist_frequency": 62500.0,
            "slm1_nyquist_frequency": 62500.0,
            "slm2_nyquist_frequency": 62500.0,
            "camera_nyquist_frequency": 172413.793,
            "aperture_cutoff_frequency": 36090.0,
        },
        tmp_path,
    )

    assert captured["name"] == "01_resolution_budget"
    assert captured["labels"] == [
        "Fourier Aperture Cutoff",
        "SLM1/Input Nyquist",
        "SLM2 Mask Nyquist",
        "ASI585MM Camera Nyquist",
    ]
    assert captured["xlabel"] == "Spatial Frequency (cycles/mm)"
    assert captured["widths"] == pytest.approx([36.09, 62.5, 62.5, 172.413793])


def test_visualize_resolution_budget_marks_bottleneck_without_explanatory_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        axis = fig.axes[0]
        captured["name"] = name
        captured["labels"] = [tick.get_text() for tick in axis.get_yticklabels()]
        captured["xlabel"] = axis.get_xlabel()
        captured["texts"] = [text.get_text() for text in axis.texts]
        captured["colors"] = [
            patch.get_facecolor()
            for patch in axis.patches
            if hasattr(patch, "get_width")
        ]
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(
        visualize,
        "_save_figure_pair",
        fake_save_figure_pair,
    )

    visualize.visualize_resolution_budget(
        {
            "input_nyquist_frequency": 62500.0,
            "slm1_nyquist_frequency": 62500.0,
            "slm2_nyquist_frequency": 62500.0,
            "camera_nyquist_frequency": 172413.793,
            "aperture_cutoff_frequency": 36090.0,
        },
        tmp_path,
    )

    assert captured["name"] == "01_resolution_budget"
    assert "Fourier Aperture Cutoff" in captured["labels"]
    assert captured["xlabel"] == "Spatial Frequency (cycles/mm)"
    assert captured["texts"] == []
    accent = to_rgba(visualize._RESTORATION_PALETTE["accent"])  # noqa: SLF001
    assert any(color == accent for color in captured["colors"])


def test_visualize_resolution_budget_omits_bottleneck_without_positive_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        axis = fig.axes[0]
        captured["name"] = name
        captured["texts"] = [text.get_text() for text in axis.texts]
        captured["widths"] = [patch.get_width() for patch in axis.patches]
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(
        visualize,
        "_save_figure_pair",
        fake_save_figure_pair,
    )

    visualize.visualize_resolution_budget(
        {
            "input_nyquist_frequency": 0.0,
            "slm1_nyquist_frequency": 0.0,
            "slm2_nyquist_frequency": 0.0,
            "camera_nyquist_frequency": 0.0,
            "aperture_cutoff_frequency": 0.0,
        },
        tmp_path,
    )

    assert captured["name"] == "01_resolution_budget"
    assert captured["widths"] == [0.0, 0.0, 0.0, 0.0]
    assert any(
        "No positive resolution limit available" in text
        for text in captured["texts"]
    )


def test_visualize_point_response_writes_png_and_svg(tmp_path: Path) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    image = torch.ones((1, 1, 16, 16), dtype=torch.float32)
    target_baselines = {
        "point_grid": {
            "image_input_identity": image,
            "image_reference_arm_only": image * 0.5,
            "image_process_arm_phase_zero": image * 0.25,
            "image_full_frontend_phase_zero": image * 0.75,
            "image_interference_term": image * -0.1,
        }
    }

    outputs = visualize_point_response(target_baselines, tmp_path)

    assert Path(outputs["png"]).name == "02_point_response.png"
    assert Path(outputs["svg"]).name == "02_point_response.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()


def test_visualize_edge_derived_intensity_mtf_writes_png_and_svg(tmp_path: Path) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    metric_rows = [
        {
            "target_name": "slanted_edge",
            "baseline_name": "full_frontend_phase_zero",
            "metric_name": "edge_mtf50_cycles_per_pixel",
            "metric_value": 0.25,
        },
        {
            "target_name": "slanted_edge",
            "baseline_name": "full_frontend_phase_zero",
            "metric_name": "edge_mtf10_cycles_per_pixel",
            "metric_value": 0.42,
        },
        {
            "target_name": "slanted_edge",
            "baseline_name": "full_frontend_phase_zero",
            "metric_name": "edge_nyquist_response",
            "metric_value": 0.15,
        },
        {
            "target_name": "slanted_edge",
            "baseline_name": "full_frontend_phase_zero",
            "metric_name": "edge_mtf_auc",
            "metric_value": 0.3,
        },
    ]

    outputs = visualize_edge_derived_intensity_mtf(metric_rows, tmp_path)

    assert Path(outputs["png"]).name == "03_edge_derived_intensity_mtf.png"
    assert Path(outputs["svg"]).name == "03_edge_derived_intensity_mtf.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()


def test_visualize_edge_derived_intensity_mtf_prefers_curve_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        axis = fig.axes[0]
        captured["name"] = name
        captured["line_count"] = len(axis.lines)
        captured["line_data"] = [
            (tuple(line.get_xdata()), tuple(line.get_ydata()))
            for line in axis.lines
        ]
        captured["xlabel"] = axis.get_xlabel()
        captured["ylabel"] = axis.get_ylabel()
        legend = axis.get_legend()
        captured["legend_labels"] = [
            text.get_text()
            for text in legend.get_texts()
        ] if legend is not None else []
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(
        visualize,
        "_save_figure_pair",
        fake_save_figure_pair,
    )

    visualize.visualize_edge_derived_intensity_mtf(
        [],
        tmp_path,
        curve_rows=[
            None,
            "bad",
            {},
            {
                "target_name": "slanted_edge",
                "baseline_name": "full_frontend_phase_zero",
                "frequencies_cycles_per_pixel": [0.0, 0.25, 0.5],
                "mtf": [1.0, 0.62, 0.18],
            }
        ],
    )

    assert captured["name"] == "03_edge_derived_intensity_mtf"
    assert captured["line_count"] >= 1
    assert captured["xlabel"] == "Spatial Frequency (cycles per pixel)"
    assert captured["ylabel"] == "Intensity MTF"
    assert "Full Frontend Phase Zero" in captured["legend_labels"]
    line_data = captured["line_data"]
    assert any(all(y == 0.5 for y in ydata) for _, ydata in line_data)
    assert any(all(y == 0.1 for y in ydata) for _, ydata in line_data)
    assert any(all(x == 0.5 for x in xdata) for xdata, _ in line_data)


def test_visualize_grating_ctf_writes_png_and_svg(tmp_path: Path) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    metric_rows = [
        {
            "target_name": "sinusoidal_gratings",
            "target_variant": "4_cycles",
            "baseline_name": "full_frontend_phase_zero",
            "spatial_frequency": 0.125,
            "metric_name": "grating_ctf",
            "metric_value": 0.85,
        },
    ]

    outputs = visualize_grating_ctf(metric_rows, tmp_path)

    assert Path(outputs["png"]).name == "04_grating_ctf.png"
    assert Path(outputs["svg"]).name == "04_grating_ctf.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()


def test_visualize_grating_ctf_uses_curve_axis_and_reference_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        axis = fig.axes[0]
        captured["xlabel"] = axis.get_xlabel()
        captured["ylabel"] = axis.get_ylabel()
        captured["line_count"] = len(axis.lines)
        captured["vertical_line_x_values"] = [
            list(line.get_xdata())
            for line in axis.lines
            if len(line.get_xdata()) >= 2
            and all(abs(float(x) - 0.5) < 1e-9 for x in line.get_xdata())
        ]
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(
        visualize,
        "_save_figure_pair",
        fake_save_figure_pair,
    )

    visualize.visualize_grating_ctf(
        [
            {
                "target_name": "sinusoidal_gratings",
                "baseline_name": "full_frontend_phase_zero",
                "spatial_frequency": 0.0625,
                "metric_name": "grating_ctf",
                "metric_value": 0.9,
            },
            {
                "target_name": "sinusoidal_gratings",
                "baseline_name": "full_frontend_phase_zero",
                "spatial_frequency": 0.25,
                "metric_name": "grating_ctf",
                "metric_value": 0.52,
            },
        ],
        tmp_path,
    )

    assert captured["xlabel"] == "Spatial Frequency (cycles per pixel)"
    assert captured["ylabel"] == "Contrast Transfer"
    assert captured["line_count"] >= 1
    assert captured["vertical_line_x_values"]


def test_visualize_grating_ctf_empty_rows_show_no_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        axis = fig.axes[0]
        captured["texts"] = [text.get_text() for text in axis.texts]
        captured["line_count"] = len(axis.lines)
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(
        visualize,
        "_save_figure_pair",
        fake_save_figure_pair,
    )

    visualize.visualize_grating_ctf([], tmp_path)

    assert "No CTF data" in captured["texts"]
    assert captured["line_count"] == 1


def test_visualize_usaf_resolution_writes_png_and_svg(tmp_path: Path) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    image = torch.ones((1, 1, 16, 16), dtype=torch.float32)
    target_baselines = {
        "usaf_bars": {
            "image_input_identity": image,
            "image_process_arm_phase_zero": image * 0.25,
            "image_full_frontend_phase_zero": image * 0.75,
        }
    }

    outputs = visualize_usaf_resolution(target_baselines, tmp_path)

    assert Path(outputs["png"]).name == "05_usaf_resolution.png"
    assert Path(outputs["svg"]).name == "05_usaf_resolution.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()


def test_visualize_siemens_star_diagnostic_writes_png_and_svg(tmp_path: Path) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    image = torch.ones((1, 1, 16, 16), dtype=torch.float32)
    target_baselines = {
        "siemens_star": {
            "image_input_identity": image,
            "image_process_arm_phase_zero": image * 0.25,
            "image_full_frontend_phase_zero": image * 0.75,
        }
    }

    outputs = visualize_siemens_star_diagnostic(target_baselines, tmp_path)

    assert Path(outputs["png"]).name == "06_siemens_star_diagnostic.png"
    assert Path(outputs["svg"]).name == "06_siemens_star_diagnostic.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()


def test_visualize_phase_offset_sensitivity_writes_png_and_svg(tmp_path: Path) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    metric_rows = [
        {
            "metric_name": "interference_reconstruction_error",
            "metric_value": 0.01,
            "spatial_frequency": 0.0,
        },
        {
            "metric_name": "interference_reconstruction_error",
            "metric_value": 0.05,
            "spatial_frequency": 1.0,
        },
    ]

    outputs = visualize_phase_offset_sensitivity(metric_rows, tmp_path)

    assert Path(outputs["png"]).name == "07_phase_offset_sensitivity.png"
    assert Path(outputs["svg"]).name == "07_phase_offset_sensitivity.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()


def test_visualize_phase_offset_sensitivity_uses_phase_and_visibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        axis = fig.axes[0]
        line = axis.lines[0]
        captured["name"] = name
        captured["x"] = list(line.get_xdata())
        captured["y"] = list(line.get_ydata())
        captured["xlabel"] = axis.get_xlabel()
        captured["ylabel"] = axis.get_ylabel()
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", fake_save_figure_pair)

    visualize.visualize_phase_offset_sensitivity(
        [
            {
                "metric_name": "interference_visibility",
                "metric_value": 0.2,
                "phase_offset_reference": 1.57079632679,
                "sweep_step": "phase_offset_scan",
                "spatial_frequency": 0.0,
            },
            {
                "metric_name": "interference_visibility",
                "metric_value": 0.1,
                "phase_offset_reference": 0.0,
                "sweep_step": "phase_offset_scan",
                "spatial_frequency": 1.0,
            },
            {
                "metric_name": "interference_visibility",
                "metric_value": 0.9,
                "phase_offset_reference": 0.0,
                "sweep_step": "characterization",
                "spatial_frequency": 0.0,
            },
        ],
        tmp_path,
    )

    assert captured["name"] == "07_phase_offset_sensitivity"
    assert captured["x"] == pytest.approx([0.0, 1.57079632679])
    assert captured["y"] == pytest.approx([0.1, 0.2])
    assert captured["xlabel"] == "Phase Offset Reference"
    assert captured["ylabel"] == "Interference Visibility"


def test_visualize_phase_offset_sensitivity_uses_symbolic_phase_labels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        axis = fig.axes[0]
        captured["labels"] = [tick.get_text() for tick in axis.get_xticklabels()]
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(
        visualize,
        "_save_figure_pair",
        fake_save_figure_pair,
    )

    visualize.visualize_phase_offset_sensitivity(
        [
            {
                "metric_name": "interference_visibility",
                "metric_value": 0.2,
                "phase_offset_reference": 0.0,
                "sweep_step": "phase_offset_scan",
            },
            {
                "metric_name": "interference_visibility",
                "metric_value": 0.3,
                "phase_offset_reference": 1.5707963267948966,
                "sweep_step": "phase_offset_scan",
            },
            {
                "metric_name": "interference_visibility",
                "metric_value": 0.4,
                "phase_offset_reference": 3.141592653589793,
                "sweep_step": "phase_offset_scan",
            },
            {
                "metric_name": "interference_visibility",
                "metric_value": 0.5,
                "phase_offset_reference": 4.71238898038469,
                "sweep_step": "phase_offset_scan",
            },
        ],
        tmp_path,
    )

    assert captured["labels"] == ["0", "pi/2", "pi", "3pi/2"]


def test_phase_tick_label_wraps_near_zero() -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    assert visualize._phase_tick_label(0.0) == "0"
    assert visualize._phase_tick_label(2.0 * math.pi) == "0"
    assert visualize._phase_tick_label(2.0 * math.pi - 1e-12) == "0"
    assert visualize._phase_tick_label(-1e-12) == "0"
    assert visualize._phase_tick_label(0.5 * math.pi) == "pi/2"


def test_visualize_operating_point_summary_writes_png_and_svg(tmp_path: Path) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    payload = {
        "checks": [
            {"name": "finite_fields", "status": "PASS"},
            {"name": "nonnegative_intensities", "status": "PASS"},
            {"name": "edge_mtf_available", "status": "FAIL"},
        ],
        "metric_rows": [{"metric_name": "energy_throughput", "metric_value": 0.9}],
        "operating_point": {"selected_focal_length": 0.25},
    }

    outputs = visualize_operating_point_summary(payload, tmp_path)

    assert Path(outputs["png"]).name == "08_operating_point_summary.png"
    assert Path(outputs["svg"]).name == "08_operating_point_summary.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()


def test_visualize_operating_point_summary_is_decision_panel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        captured["name"] = name
        captured["axis_count"] = len(fig.axes)
        captured["texts"] = [
            text.get_text()
            for axis in fig.axes
            for text in axis.texts
        ]
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", fake_save_figure_pair)

    visualize.visualize_operating_point_summary(
        {
            "checks": [
                {"name": "finite_fields", "status": "PASS"},
                {"name": "nonnegative_intensities", "status": "PASS"},
                {"name": "interference_reconstruction_matches_full", "status": "PASS"},
                {"name": "operating_point_written", "status": "PASS"},
            ],
            "metric_rows": [
                {
                    "metric_name": "edge_mtf50_cycles_per_pixel",
                    "metric_value": 0.31,
                    "baseline_name": "full_frontend_phase_zero",
                },
                {
                    "metric_name": "energy_throughput",
                    "metric_value": 0.88,
                    "baseline_name": "full_frontend_phase_zero",
                },
                {
                    "metric_name": "interference_visibility",
                    "metric_value": 0.99,
                    "baseline_name": "interference_term",
                },
            ],
            "operating_point": {
                "selected_focal_length": 0.25,
                "selected_phase_mask_resolution": 512,
                "selected_camera_sampling": "native_sensor",
                "selected_aperture_policy": "full_slm_active_area",
                "selected_phase_offset_reference": 0.0,
                "selection_metrics": {
                    "edge_mtf50_cycles_per_pixel": 0.32,
                    "energy_throughput": 0.89,
                    "interference_visibility": 0.98,
                },
            },
        },
        tmp_path,
    )

    assert captured["name"] == "08_operating_point_summary"
    assert captured["axis_count"] >= 3
    assert any("MTF50" in text for text in captured["texts"])
    assert any("0.320" in text for text in captured["texts"])
    assert any("Throughput" in text for text in captured["texts"])
    assert any("0.890" in text for text in captured["texts"])
    assert any("Visibility" in text for text in captured["texts"])
    assert any("0.980" in text for text in captured["texts"])
    assert any("Phase Mask" in text for text in captured["texts"])
    assert any("ASI585MM Native" in text for text in captured["texts"])
    assert captured["texts"].count("PASS") == 5
    assert "FAIL" not in captured["texts"]


def test_visualize_operating_point_summary_prefers_non_phase_scan_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        captured["texts"] = [text.get_text() for axis in fig.axes for text in axis.texts]
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", fake_save_figure_pair)

    visualize.visualize_operating_point_summary(
        {
            "checks": [],
            "metric_rows": [
                {
                    "metric_name": "interference_visibility",
                    "metric_value": 0.1,
                    "baseline_name": "interference_term",
                    "sweep_step": "phase_offset_scan",
                },
                {
                    "metric_name": "interference_visibility",
                    "metric_value": 0.99,
                    "baseline_name": "interference_term",
                    "sweep_step": "characterization",
                },
            ],
            "operating_point": {},
        },
        tmp_path,
    )

    assert "Visibility\n0.990" in captured["texts"]
    assert "Visibility\n0.100" not in captured["texts"]


def test_visualize_operating_point_summary_uses_na_for_missing_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    captured: dict[str, object] = {}

    def fake_save_figure_pair(
        fig: plt.Figure,
        output_dir: Path | str,
        name: str,
    ) -> dict[str, str]:
        """
        妯℃嫙鍙鍖栨祴璇曞満鏅?        """
        captured["texts"] = [text.get_text() for axis in fig.axes for text in axis.texts]
        plt.close(fig)
        return {
            "png": str(Path(output_dir) / f"{name}.png"),
            "svg": str(Path(output_dir) / f"{name}.svg"),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", fake_save_figure_pair)

    visualize.visualize_operating_point_summary(
        {"checks": [], "metric_rows": [], "operating_point": {}},
        tmp_path,
    )

    assert any("n/a" in text for text in captured["texts"])


def test_training_visualization_writes_required_figure_names(tmp_path: Path) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    history_rows = [
        {
            "epoch": 1,
            "split": "train",
            "loss_total": 1.0,
            "loss_l1": 0.4,
            "loss_ssim": 0.2,
            "loss_frequency": 0.1,
            "phase_smoothness": 0.0,
            "psnr_normalized": 5.0,
            "ssim_normalized": 0.1,
        },
        {
            "epoch": 1,
            "split": "val",
            "loss_total": 0.8,
            "loss_l1": 0.3,
            "loss_ssim": 0.1,
            "loss_frequency": "inf",
            "phase_smoothness": 0.0,
            "psnr_normalized": 6.0,
            "ssim_normalized": 0.2,
        },
    ]
    image = torch.linspace(0.0, 1.0, steps=64, dtype=torch.float32).reshape(1, 1, 8, 8)
    figure_outputs = [
        visualize_training_dynamics(history_rows, tmp_path),
        visualize_restoration_examples(
            {
                "clean": image,
                "degraded": image * 0.8,
                "phase_zero": image * 0.7,
                "restored": image * 0.9,
            },
            tmp_path,
        ),
        visualize_phase_mask_evolution(torch.zeros((8, 8)), torch.ones((8, 8)), tmp_path),
        visualize_frequency_response_comparison(
            {
                "phase_zero_vs_clean_psnr": 5.0,
                "trained_vs_clean_psnr": 7.0,
            },
            tmp_path,
        ),
        visualize_operating_point_trace(
            {
                "selected_values": {
                    "selected_focal_length": 0.1,
                    "selected_phase_mask_resolution": 8,
                    "selected_phase_offset_reference": 0.0,
                }
            },
            tmp_path,
        ),
    ]

    assert [Path(output["png"]).name for output in figure_outputs] == [
        "01_training_dynamics.png",
        "02_restoration_examples.png",
        "03_phase_mask_evolution.png",
        "04_frequency_response_comparison.png",
        "05_operating_point_trace.png",
    ]
    for output in figure_outputs:
        assert Path(output["png"]).exists()
        assert Path(output["svg"]).exists()


def test_visualize_restoration_examples_writes_placeholder_for_missing_images(
    tmp_path: Path,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    outputs = visualize_restoration_examples({"clean": torch.ones((1, 1, 8, 8))}, tmp_path)

    assert Path(outputs["png"]).name == "02_restoration_examples.png"
    assert Path(outputs["svg"]).name == "02_restoration_examples.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()

def test_visualize_restoration_examples_writes_placeholder_for_empty_payload(
    tmp_path: Path,
) -> None:
    """
    鏍￠獙鍙鍖栧绾?    """
    outputs = visualize_restoration_examples({}, tmp_path)

    assert Path(outputs["png"]).name == "02_restoration_examples.png"
    assert Path(outputs["svg"]).name == "02_restoration_examples.svg"
    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()

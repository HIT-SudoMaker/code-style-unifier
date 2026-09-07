from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from typing import Any

import matplotlib
import numpy as np
import pytest
import torch

matplotlib.use("Agg", force=True)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _import_visualize_module() -> Any:
    sys.modules.pop("experiments.classification.visualize", None)
    return importlib.import_module("experiments.classification.visualize")


def _assert_figure_pair(outputs: dict[str, str]) -> None:
    png_path = Path(outputs["png"])
    svg_path = Path(outputs["svg"])
    assert png_path.exists()
    assert svg_path.exists()
    assert png_path.read_bytes().startswith(PNG_SIGNATURE)
    assert svg_path.read_text(encoding="utf-8", errors="ignore").lstrip().startswith(
        "<?xml"
    ) or "<svg" in svg_path.read_text(encoding="utf-8", errors="ignore")[:200]


def test_visualize_module_requests_agg_backend_before_matplotlib_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Validate that visualization requests the Agg backend first.
    """
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
    real_use = matplotlib.use

    def _fake_use(*args: object, **kwargs: object) -> Any:
        calls.append((args[0], args[1:], dict(kwargs)))
        return real_use(*args, **kwargs)

    monkeypatch.setattr(matplotlib, "use", _fake_use)

    module = _import_visualize_module()

    assert calls
    assert calls[0][0] == "Agg"
    assert module is not None


def test_style_config_json_defines_publication_visual_roles() -> None:
    """
    验证分类测试契约保持稳定
    """
    config_path = (
        Path(__file__).resolve().parents[2]
        / "experiments"
        / "classification"
        / "style_config.json"
    )
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    assert set(payload) == {
        "font",
        "export",
        "palette",
        "colormaps",
        "lines",
        "overlays",
        "figures",
    }
    assert payload["export"] == {
        "dpi": 500,
        "formats": ["png", "svg"],
        "bbox_inches": "tight",
        "facecolor": "#ffffff",
    }
    assert payload["font"] == {
        "figure_title": 11,
        "axis_title": 9,
        "axis_label": 8,
        "tick_label": 7,
        "legend": 7,
        "annotation": 7,
        "matrix_cell": 5,
    }
    assert payload["palette"]["detector_red"] == "#b65a4a"
    assert payload["palette"]["confusion_high"] == "#486a80"
    assert payload["palette"]["energy_high"] == "#486a80"
    assert payload["palette"]["train_line"] == "#486a80"
    assert payload["palette"]["validation_line"] == "#b65a4a"
    assert payload["overlays"]["detector_region"] == {
        "color": "detector_red",
        "linewidth": 0.7,
        "linestyle": "--",
        "alpha": 0.85,
    }
    assert payload["figures"]["training_dynamics"]["figsize"] == [6.8, 3.2]
    assert payload["figures"]["training_dynamics"]["accuracy_ymin"] == 0.8
    assert payload["figures"]["training_dynamics"]["legend_columns"] == 2
    assert payload["figures"]["training_dynamics"]["uses_gap_annotation"] is False
    assert "training_curves" not in payload["figures"]
    assert payload["figures"]["confusion_matrix"]["filename"] == "02_confusion_matrix"
    assert payload["figures"]["confusion_matrix"]["figsize"] == [4.3, 3.7]
    assert payload["figures"]["per_class_accuracy"]["filename"] == "03_per_class_accuracy"
    assert payload["figures"]["per_class_accuracy"]["figsize"] == [4.8, 2.7]
    assert payload["figures"]["per_class_accuracy"]["accuracy_ymin"] == 0.88
    assert (
        payload["figures"]["optical_readout_examples"]["filename"]
        == "04_optical_readout_examples"
    )
    assert payload["figures"]["optical_readout_examples"]["figsize"] == [7.2, 7.6]
    assert payload["figures"]["optical_readout_examples"]["row_height"] == 1.04
    assert payload["figures"]["optical_readout_examples"]["column_width_ratios"] == [
        1.0,
        1.0,
        1.0,
        1.55,
    ]
    assert payload["figures"]["optical_readout_examples"]["detector_column_gap"] == 0.16
    assert payload["figures"]["optical_readout_examples"]["column_wspace"] == 0.15
    assert payload["figures"]["optical_readout_examples"]["row_hspace"] == 0.32
    assert payload["figures"]["optical_readout_examples"]["grid_left"] == 0.055
    assert payload["figures"]["optical_readout_examples"]["grid_right"] == 0.98
    assert payload["figures"]["optical_readout_examples"]["grid_top"] == 0.91
    assert payload["figures"]["optical_readout_examples"]["grid_bottom"] == 0.045
    assert payload["figures"]["optical_readout_examples"]["bbox_inches"] is None
    assert payload["figures"]["optical_readout_examples"]["uses_detector_xlabel"] is False
    assert payload["figures"]["topology_comparison"]["filename"] == "05_topology_comparison"


def test_visualize_module_uses_local_style_config_not_shared_figure_style() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    source = Path(visualize.__file__).read_text(encoding="utf-8")
    legacy_names = ("_CLASSIFICATION_STYLE", "_CLASSIFICATION_PALETTE")

    assert "experiments.figure_style" not in source
    for legacy_name in legacy_names:
        assert legacy_name not in source
        assert not hasattr(visualize, legacy_name)


def test_classification_uses_local_font_contract() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    style = visualize.load_style_config()

    assert style.font.figure_title == 11
    assert style.font.axis_title == 9
    assert style.font.axis_label == 8
    assert style.font.tick_label == 7
    assert style.font.legend == 7
    assert style.font.annotation == 7
    assert style.font.matrix_cell == 5
    assert not hasattr(style.font, "detector_label")
    assert not hasattr(style.font, "panel_label")
    assert not hasattr(style.font, "readout_annotation")
    assert not hasattr(visualize, "_CLASSIFICATION_FONT_SIZES")
    assert not hasattr(visualize, "_MATRIX_ANNOTATION_FONT_SIZE")


def test_save_classification_figure_pair_accepts_bbox_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    fig = visualize.plt.figure()
    calls: list[object] = []

    def _capture_savefig(output_path: str | Path, **kwargs: object) -> None:
        del output_path
        calls.append(kwargs["bbox_inches"])

    monkeypatch.setattr(fig, "savefig", _capture_savefig)

    outputs = visualize.save_classification_figure_pair(
        fig,
        tmp_path / "bbox_override",
        bbox_inches=None,
    )

    assert set(outputs) == {"png", "svg"}
    assert calls == [None, None]


def test_classification_figure_style_applies_font_contract() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    fig, axis = visualize.plt.subplots()
    try:
        axis.plot([0, 1], [0, 1], label="Series")
        axis.set_title("Subplot")
        axis.set_xlabel("x")
        axis.set_ylabel("y")
        axis.legend()
        fig.suptitle("Figure")

        visualize._apply_classification_figure_style(fig)

        style = visualize.load_style_config()
        assert fig._suptitle.get_fontsize() == style.font.figure_title
        assert axis.title.get_fontsize() == style.font.axis_title
        assert axis.xaxis.label.get_fontsize() == style.font.axis_label
        assert axis.yaxis.label.get_fontsize() == style.font.axis_label
        assert axis.get_xticklabels()[0].get_fontsize() == style.font.tick_label
        assert axis.get_legend().get_texts()[0].get_fontsize() == style.font.legend
    finally:
        visualize.plt.close(fig)


def test_classification_colorbar_uses_local_ticks_and_outline() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    fig, axis = visualize.plt.subplots()
    try:
        image = axis.imshow([[0.0, 1.0]], cmap=visualize.make_colormap("confusion_matrix"))
        colorbar = fig.colorbar(image, ax=axis)

        visualize.style_classification_colorbar(colorbar)

        tick_colors = {tick.get_color() for tick in colorbar.ax.get_yticklabels()}
        assert tick_colors == {visualize.palette_color("paper_text")}
        assert visualize.matplotlib.colors.to_hex(colorbar.outline.get_edgecolor()) == (
            visualize.palette_color("grid")
        )
    finally:
        visualize.plt.close(fig)


def test_style_optical_axis_uses_optical_panel_roles() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    fig, axis = visualize.plt.subplots()
    try:
        axis.set_title("Optical panel")
        axis.set_xlabel("x")
        axis.set_ylabel("y")
        axis.plot([0, 1], [0, 1])

        visualize.style_optical_axis(axis)

        assert axis.get_facecolor() == visualize.matplotlib.colors.to_rgba(
            visualize.palette_color("intensity_low")
        )
        assert axis.title.get_color() == visualize.palette_color("intensity_high")
        assert axis.title.get_fontsize() == visualize.font_size("axis_title")
        assert not axis.get_xticks().size
        assert not axis.get_yticks().size
        assert all(not spine.get_visible() for spine in axis.spines.values())
    finally:
        visualize.plt.close(fig)


def test_classification_matrix_annotation_contrast_uses_cell_luminance() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()

    assert visualize._matrix_annotation_color(0.0) == visualize.palette_color("paper_text")
    assert visualize._matrix_annotation_color(1.0) == "#ffffff"


def test_confusion_matrix_cell_annotations_use_matrix_cell_font(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    captured: dict[str, object] = {}

    def _capture_figure_pair(fig: object, output_base: str | Path) -> dict[str, str]:
        base_path = Path(output_base)
        captured["fig"] = fig
        return {
            "png": str(base_path.with_suffix(".png")),
            "svg": str(base_path.with_suffix(".svg")),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", _capture_figure_pair)

    visualize.visualize_confusion_matrix(
        [[4, 1], [2, 3]],
        tmp_path / "02_confusion_matrix",
    )

    fig = captured["fig"]
    try:
        axis = fig.axes[0]
        cell_texts = [text for text in axis.texts if text.get_text().isdigit()]
        assert cell_texts
        assert {text.get_fontsize() for text in cell_texts} == {
            visualize.font_size("matrix_cell")
        }
    finally:
        visualize.plt.close(fig)


def test_confusion_matrix_draws_square_matrix_area(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    captured: dict[str, object] = {}

    def _capture_figure_pair(fig: object, output_base: str | Path) -> dict[str, str]:
        base_path = Path(output_base)
        captured["fig"] = fig
        return {
            "png": str(base_path.with_suffix(".png")),
            "svg": str(base_path.with_suffix(".svg")),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", _capture_figure_pair)
    matrix = np.eye(10, dtype=int) * 8

    visualize.visualize_confusion_matrix(matrix, tmp_path / "02_confusion_matrix")

    fig = captured["fig"]
    try:
        fig.canvas.draw()
        figure_width, figure_height = fig.get_size_inches()
        matrix_axis = fig.axes[0]
        matrix_box = matrix_axis.get_position()
        matrix_width = matrix_box.width * figure_width
        matrix_height = matrix_box.height * figure_height

        assert matrix_width == pytest.approx(matrix_height, rel=0.01)
    finally:
        visualize.plt.close(fig)


def test_confusion_matrix_title_centers_over_matrix_and_colorbar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    captured: dict[str, object] = {}

    def _capture_figure_pair(fig: object, output_base: str | Path) -> dict[str, str]:
        base_path = Path(output_base)
        captured["fig"] = fig
        return {
            "png": str(base_path.with_suffix(".png")),
            "svg": str(base_path.with_suffix(".svg")),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", _capture_figure_pair)

    visualize.visualize_confusion_matrix(
        np.eye(10, dtype=int),
        tmp_path / "02_confusion_matrix",
    )

    fig = captured["fig"]
    try:
        fig.canvas.draw()
        matrix_box = fig.axes[0].get_position()
        colorbar_box = fig.axes[1].get_position()
        content_center = (
            min(matrix_box.x0, colorbar_box.x0) + max(matrix_box.x1, colorbar_box.x1)
        ) / 2.0

        assert fig._suptitle is not None
        assert fig._suptitle.get_position()[0] == pytest.approx(
            content_center,
            abs=0.005,
        )
    finally:
        visualize.plt.close(fig)


def test_visualize_training_curves_writes_png_and_svg(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    outputs = visualize.visualize_training_curves(
        [
            {
                "epoch": 1,
                "train_loss": 1.0,
                "val_loss": 1.1,
                "train_accuracy": 0.4,
                "val_accuracy": 0.5,
            },
            {
                "epoch": 2,
                "train_loss": 0.8,
                "val_loss": 0.9,
                "train_accuracy": 0.6,
                "val_accuracy": 0.7,
            },
        ],
        tmp_path / "training_curves",
    )

    _assert_figure_pair(outputs)


def test_visualize_training_dynamics_uses_configured_axis_and_shared_legend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    captured: dict[str, object] = {}

    def _capture_figure_pair(fig: object, output_base: str | Path) -> dict[str, str]:
        captured["fig"] = fig
        base_path = Path(output_base)
        return {
            "png": str(base_path.with_suffix(".png")),
            "svg": str(base_path.with_suffix(".svg")),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", _capture_figure_pair)

    outputs = visualize.visualize_training_dynamics(
        [
            {
                "epoch": 1,
                "train_loss": 0.12,
                "val_loss": 0.13,
                "train_accuracy": 0.82,
                "val_accuracy": 0.9,
            },
            {
                "epoch": 2,
                "train_loss": 0.09,
                "val_loss": 0.1,
                "train_accuracy": 0.94,
                "val_accuracy": 0.95,
            },
        ],
        tmp_path / "01_training_dynamics",
        best_epoch=2,
    )

    fig = captured["fig"]
    try:
        loss_axis, accuracy_axis = fig.axes[:2]
        assert outputs["png"].endswith("01_training_dynamics.png")
        assert tuple(fig.get_size_inches()) == pytest.approx(
            visualize.figure_style("training_dynamics").figsize
        )
        assert loss_axis.get_title() == ""
        assert accuracy_axis.get_title() == ""
        assert loss_axis.get_legend() is None
        assert accuracy_axis.get_legend() is None
        assert len(fig.legends) == 1
        legend = fig.legends[0]
        assert [text.get_text() for text in legend.get_texts()] == [
            "Train",
            "Validation",
        ]
        assert getattr(legend, "_ncols", None) == 2
        assert accuracy_axis.get_ylim()[0] == pytest.approx(
            visualize.figure_style("training_dynamics").accuracy_ymin
        )
        assert all(
            "Gap" not in text.get_text()
            for axis in fig.axes
            for text in axis.texts
        )
        assert visualize.matplotlib.colors.to_hex(loss_axis.lines[0].get_color()) == (
            visualize.palette_color("train_line")
        )
        assert visualize.matplotlib.colors.to_hex(loss_axis.lines[1].get_color()) == (
            visualize.palette_color("validation_line")
        )
    finally:
        visualize.plt.close(fig)


def test_visualize_confusion_matrix_writes_png_and_svg(tmp_path: Path) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    matrix = [[0 for _ in range(10)] for _ in range(10)]
    matrix[0][0] = 2
    matrix[1][0] = 1

    outputs = visualize.visualize_confusion_matrix(
        matrix,
        tmp_path / "02_confusion_matrix",
    )

    _assert_figure_pair(outputs)
    assert Path(outputs["png"]).name == "02_confusion_matrix.png"
    assert Path(outputs["svg"]).name == "02_confusion_matrix.svg"
    svg_text = Path(outputs["svg"]).read_text(encoding="utf-8", errors="ignore")
    assert "#486a80" in svg_text
    assert "#42d313" not in svg_text


def test_visualize_confusion_matrix_handles_empty_matrix(tmp_path: Path) -> None:
    """
    空混淆矩阵兼容性
    """
    visualize = _import_visualize_module()

    outputs = visualize.visualize_confusion_matrix(
        [],
        tmp_path / "empty_confusion_matrix",
    )

    _assert_figure_pair(outputs)


def test_visualize_per_class_accuracy_writes_png_and_svg(tmp_path: Path) -> None:
    """
    鏍￠獙鍒嗙被鍑嗙‘鐜囧浘浜х墿
    """
    visualize = _import_visualize_module()

    outputs = visualize.visualize_per_class_accuracy(
        [1.0, 0.5] + [0.0] * 8,
        tmp_path / "03_per_class_accuracy",
    )

    _assert_figure_pair(outputs)
    assert Path(outputs["png"]).name == "03_per_class_accuracy.png"
    assert Path(outputs["svg"]).name == "03_per_class_accuracy.svg"
    svg_text = Path(outputs["svg"]).read_text(encoding="utf-8", errors="ignore")
    assert "#6f8fa3" in svg_text
    assert "#304858" in svg_text
    assert "#1f77b4" not in svg_text


def test_visualize_per_class_accuracy_uses_configured_ymin_without_clipping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    captured: list[object] = []

    def _capture_figure_pair(fig: object, output_base: str | Path) -> dict[str, str]:
        base_path = Path(output_base)
        captured.append(fig)
        return {
            "png": str(base_path.with_suffix(".png")),
            "svg": str(base_path.with_suffix(".svg")),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", _capture_figure_pair)

    visualize.visualize_per_class_accuracy(
        [0.97, 0.95, 0.99, 0.94],
        tmp_path / "03_per_class_accuracy_high",
    )
    visualize.visualize_per_class_accuracy(
        [0.97, 0.86, 0.99, 0.94],
        tmp_path / "03_per_class_accuracy_low",
    )

    high_fig, low_fig = captured
    try:
        high_axis = high_fig.axes[0]
        low_axis = low_fig.axes[0]
        assert high_axis.get_ylim()[0] == pytest.approx(
            visualize.figure_style("per_class_accuracy").accuracy_ymin
        )
        assert low_axis.get_ylim()[0] == pytest.approx(0.84)
        assert high_axis.get_ylim()[1] == pytest.approx(1.0)
        assert low_axis.get_ylim()[1] == pytest.approx(1.0)
    finally:
        visualize.plt.close(high_fig)
        visualize.plt.close(low_fig)


def test_diagnostic_phase_and_prediction_visualizations_use_style_config_roles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    figure_roles: list[str] = []
    colormap_roles: list[str] = []
    real_figure_style = visualize.figure_style
    real_make_colormap = visualize.make_colormap

    def recording_figure_style(role: str) -> object:
        """
        记录诊断图样式角色
        """
        figure_roles.append(role)
        return real_figure_style(role)

    def recording_make_colormap(role: str) -> object:
        """
        记录诊断图色图角色
        """
        colormap_roles.append(role)
        return real_make_colormap(role)

    monkeypatch.setattr(visualize, "figure_style", recording_figure_style)
    monkeypatch.setattr(visualize, "make_colormap", recording_make_colormap)

    detector_path = visualize.visualize_detector_layout(tmp_path / "detectors.png")
    phase_path = visualize.visualize_phase_mask(
        torch.zeros((8, 8)),
        tmp_path / "phase.png",
    )
    prediction_path = visualize.visualize_prediction_example(
        input_image=torch.zeros((1, 4, 4)),
        input_field_magnitude=torch.ones((1, 4, 4)),
        intensity_map=torch.ones((1, 4, 4)),
        detector_distribution=torch.linspace(0.0, 1.0, steps=10),
        output_path=tmp_path / "prediction.png",
    )

    assert detector_path.read_bytes().startswith(PNG_SIGNATURE)
    assert phase_path.read_bytes().startswith(PNG_SIGNATURE)
    assert prediction_path.read_bytes().startswith(PNG_SIGNATURE)
    assert {"detector_layout", "phase_mask", "prediction_example"} <= set(figure_roles)
    assert "phase" in colormap_roles
    assert colormap_roles.count("intensity") >= 2


def test_visualize_training_dynamics_writes_numbered_pair(tmp_path: Path) -> None:
    """
    Validate numbered training-dynamics PNG/SVG output.
    """
    visualize = _import_visualize_module()

    outputs = visualize.visualize_training_dynamics(
        [
            {
                "epoch": 1,
                "train_loss": 1.2,
                "val_loss": 1.3,
                "train_accuracy": 0.2,
                "val_accuracy": 0.3,
                "seconds": 0.5,
            },
            {
                "epoch": 2,
                "train_loss": 0.8,
                "val_loss": 0.9,
                "train_accuracy": 0.7,
                "val_accuracy": 0.6,
                "seconds": 0.4,
            },
        ],
        tmp_path / "01_training_dynamics",
        best_epoch=2,
    )

    _assert_figure_pair(outputs)
    assert Path(outputs["png"]).name == "01_training_dynamics.png"
    assert Path(outputs["svg"]).name == "01_training_dynamics.svg"


def test_visualize_evaluation_summary_is_removed() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()

    assert not hasattr(visualize, "visualize_evaluation_summary")
    assert not hasattr(visualize, "_normalize_confusion_matrix")


def test_visualize_optical_readout_examples_writes_upper_and_lower_pairs(
    tmp_path: Path,
) -> None:
    """
    Validate upper/lower optical readout PNG/SVG output.
    """
    visualize = _import_visualize_module()
    example = {
        "sample_index": 0,
        "true_label": 3,
        "predicted_label": 3,
        "input_image": torch.zeros((1, 4, 4), dtype=torch.float32),
        "input_field_magnitude": torch.ones((1, 4, 4), dtype=torch.float32),
        "intensity_map": torch.ones((1, 4, 4), dtype=torch.float32),
        "detector_distribution": torch.eye(10, dtype=torch.float32)[3],
    }

    outputs = visualize.visualize_optical_readout_examples(
        [example],
        tmp_path / "04_optical_readout_examples",
    )

    assert set(outputs) == {"upper_png", "upper_svg", "lower_png", "lower_svg"}
    assert Path(outputs["upper_png"]).name == "04_optical_readout_examples_upper.png"
    assert Path(outputs["upper_svg"]).name == "04_optical_readout_examples_upper.svg"
    assert Path(outputs["lower_png"]).name == "04_optical_readout_examples_lower.png"
    assert Path(outputs["lower_svg"]).name == "04_optical_readout_examples_lower.svg"
    for path in outputs.values():
        assert Path(path).exists()
    assert not (tmp_path / "04_optical_readout_examples.png").exists()
    assert not (tmp_path / "04_optical_readout_examples.svg").exists()


def test_mask_detector_intensity_keeps_only_detector_regions_and_normalizes() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    intensity = np.arange(16, dtype=np.float32).reshape(4, 4)

    masked = visualize._masked_detector_intensity(
        intensity,
        {"detector_regions": [(1, 3, 1, 3)]},
    )

    expected = np.zeros((4, 4), dtype=np.float32)
    expected[1:3, 1:3] = intensity[1:3, 1:3] / intensity[1:3, 1:3].max()
    assert masked == pytest.approx(expected)


def test_normalize_detector_distribution_uses_max_reference() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()

    normalized = visualize._normalize_detector_distribution(
        torch.tensor([0.0, 2.0, 6.0], dtype=torch.float32)
    )

    assert normalized.tolist() == pytest.approx([0.0, 1.0 / 3.0, 1.0])


def test_draw_detector_regions_places_red_dashed_rectangle_on_pixel_edges() -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    fig, axis = visualize.plt.subplots()
    try:
        visualize._draw_detector_regions(
            axis,
            {"detector_regions": [(1, 3, 2, 5)]},
        )

        assert len(axis.patches) == 1
        outline_patch = axis.patches[0]
        assert outline_patch.get_xy() == pytest.approx((0.5, 1.5))
        assert outline_patch.get_width() == pytest.approx(2.0)
        assert outline_patch.get_height() == pytest.approx(3.0)
        overlay = visualize.overlay_style("detector_region")
        to_hex = visualize.matplotlib.colors.to_hex
        assert to_hex(outline_patch.get_edgecolor()) == visualize.palette_color(
            overlay.color
        )
        assert outline_patch.get_linewidth() == pytest.approx(overlay.linewidth)
        assert outline_patch.get_linestyle() == overlay.linestyle
        assert outline_patch.get_alpha() == pytest.approx(overlay.alpha)
    finally:
        visualize.plt.close(fig)


def test_visualize_optical_readout_examples_accepts_detector_evidence(
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    example = {
        "sample_index": 0,
        "true_label": 3,
        "predicted_label": 3,
        "input_image": torch.zeros((1, 8, 8), dtype=torch.float32),
        "input_field_magnitude": torch.ones((1, 8, 8), dtype=torch.float32),
        "intensity_map": torch.ones((1, 8, 8), dtype=torch.float32),
        "detector_distribution": torch.eye(10, dtype=torch.float32)[3],
        "detector_regions": [(1, 3, 1, 3), (5, 7, 5, 7)],
        "detector_total_energy_fraction": 0.5,
        "target_detector_energy_fraction": 0.7,
        "predicted_detector_energy_fraction": 0.7,
        "peak_coordinate": (2, 2),
        "peak_detector_index": 0,
        "is_peak_in_any_detector": True,
        "is_peak_in_target_detector": False,
    }

    outputs = visualize.visualize_optical_readout_examples(
        [example],
        tmp_path / "04_optical_readout_examples",
    )

    svg_text = Path(outputs["upper_svg"]).read_text(encoding="utf-8", errors="ignore")
    assert "Detector energy" not in svg_text
    assert "Target share" not in svg_text
    assert "Peak in target" not in svg_text
    assert "#b65a4a" in svg_text
    assert "#486a80" in svg_text
    assert "#d47a00" not in svg_text
    assert "#1f77b4" not in svg_text


def test_visualize_optical_readout_examples_uses_compact_configured_layout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()
    captured: dict[str, object] = {}
    bbox_overrides: dict[str, object] = {}

    def _capture_figure_pair(
        fig: object,
        output_base: str | Path,
        *,
        bbox_inches: object = "not-provided",
    ) -> dict[str, str]:
        base_path = Path(output_base)
        captured[base_path.name] = fig
        bbox_overrides[base_path.name] = bbox_inches
        return {
            "png": str(base_path.with_suffix(".png")),
            "svg": str(base_path.with_suffix(".svg")),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", _capture_figure_pair)
    examples = [
        {
            "sample_index": digit,
            "true_label": digit,
            "predicted_label": digit,
            "input_image": torch.zeros((1, 4, 4), dtype=torch.float32),
            "input_field_magnitude": torch.ones((1, 4, 4), dtype=torch.float32),
            "intensity_map": torch.ones((1, 4, 4), dtype=torch.float32),
            "detector_distribution": torch.eye(10, dtype=torch.float32)[digit],
        }
        for digit in range(10)
    ]

    visualize.visualize_optical_readout_examples(
        examples,
        tmp_path / "04_optical_readout_examples",
    )

    upper_fig = captured["04_optical_readout_examples_upper"]
    lower_fig = captured["04_optical_readout_examples_lower"]
    try:
        style = visualize.figure_style("optical_readout_examples")
        for fig in (upper_fig, lower_fig):
            assert tuple(fig.get_size_inches()) == pytest.approx(style.figsize)
            fig.canvas.draw()
            figure_width, figure_height = fig.get_size_inches()
            first_axis = fig.axes[0]
            detector_axis = fig.axes[3]
            detector_to_image_width = (
                detector_axis.get_position().width / first_axis.get_position().width
            )
            assert detector_to_image_width >= (
                style.column_width_ratios[3] / style.column_width_ratios[0]
            )
            assert detector_to_image_width <= 2.25
            for image_axis in fig.axes[:3]:
                image_box = image_axis.get_position()
                image_width = image_box.width * figure_width
                image_height = image_box.height * figure_height
                assert image_width == pytest.approx(image_height, rel=0.03)
                assert image_height >= style.row_height
            output_gap = (
                detector_axis.get_position().x0 - fig.axes[2].get_position().x1
            )
            assert output_gap >= first_axis.get_position().width * (
                style.detector_column_gap * 0.9
            )
            assert fig.axes[0].get_position().y1 <= style.grid_top + 1e-6
            assert fig.axes[-1].get_position().y0 >= style.grid_bottom - 1e-6
            vertical_gap = fig.axes[0].get_position().y0 - fig.axes[4].get_position().y1
            assert vertical_gap > 0.03
        assert bbox_overrides == {
            "04_optical_readout_examples_upper": None,
            "04_optical_readout_examples_lower": None,
        }
        assert [axis.get_ylabel() for axis in upper_fig.axes[::4]] == [
            f"True {digit} / Pred {digit}" for digit in range(5)
        ]
        assert [axis.get_ylabel() for axis in lower_fig.axes[::4]] == [
            f"True {digit} / Pred {digit}" for digit in range(5, 10)
        ]
        assert [axis.get_xlabel() for axis in upper_fig.axes[3::4]] == [""] * 5
        assert [axis.get_xlabel() for axis in lower_fig.axes[3::4]] == [""] * 5
    finally:
        visualize.plt.close(upper_fig)
        visualize.plt.close(lower_fig)


def test_visualize_optical_readout_examples_handles_empty_distribution(
    tmp_path: Path,
) -> None:
    """
    空探测器分布兼容性
    """
    visualize = _import_visualize_module()
    example = {
        "sample_index": 0,
        "true_label": 3,
        "predicted_label": 3,
        "input_image": torch.zeros((1, 4, 4), dtype=torch.float32),
        "input_field_magnitude": torch.ones((1, 4, 4), dtype=torch.float32),
        "intensity_map": torch.ones((1, 4, 4), dtype=torch.float32),
        "detector_distribution": torch.tensor([], dtype=torch.float32),
    }

    outputs = visualize.visualize_optical_readout_examples(
        [example],
        tmp_path / "04_optical_readout_examples_empty_distribution",
    )

    for path in outputs.values():
        assert Path(path).exists()


def test_visualize_optical_readout_examples_handles_empty_examples(
    tmp_path: Path,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    visualize = _import_visualize_module()

    outputs = visualize.visualize_optical_readout_examples(
        [],
        tmp_path / "04_optical_readout_examples",
    )

    for path in outputs.values():
        assert Path(path).exists()


def test_visualize_topology_comparison_writes_numbered_pair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    缂栧彿鎷撴墤瀵规瘮鍥惧啓鍑篜NG鍜孲VG
    """
    visualize = _import_visualize_module()
    captured: dict[str, object] = {}

    def _capture_figure_pair(fig: object, output_base: str | Path) -> dict[str, str]:
        captured["fig"] = fig
        base_path = Path(output_base)
        return {
            "png": str(base_path.with_suffix(".png")),
            "svg": str(base_path.with_suffix(".svg")),
        }

    monkeypatch.setattr(visualize, "_save_figure_pair", _capture_figure_pair)
    rows = [
        {
            "topology": "without_lens",
            "evaluation_accuracy": 0.82,
            "best_val_accuracy": 0.85,
            "mean_epoch_seconds": 1.2,
            "is_available": True,
        },
        {
            "topology": "with_lens",
            "evaluation_accuracy": None,
            "best_val_accuracy": None,
            "mean_epoch_seconds": None,
            "is_available": False,
        },
    ]

    outputs = visualize.visualize_topology_comparison(
        rows,
        tmp_path / "05_topology_comparison",
    )

    assert Path(outputs["png"]).name == "05_topology_comparison.png"
    assert Path(outputs["svg"]).name == "05_topology_comparison.svg"
    fig = captured["fig"]
    try:
        tick_labels = [tick.get_text() for tick in fig.axes[0].get_xticklabels()]
        assert tick_labels == ["Without lens", "With lens"]
        assert all("_" not in label for label in tick_labels)
        assert fig.axes[1].get_ylabel() == "Mean epoch time (s)"
    finally:
        visualize.plt.close(fig)


def test_visualize_training_history_handles_ragged_history(tmp_path: Path) -> None:
    """
    非齐整历史兼容性
    """
    visualize = _import_visualize_module()

    output_path = visualize.visualize_training_history(
        {
            "train_loss": [1.0, 0.8, 0.6],
            "val_loss": [1.1],
            "train_accuracy": [0.3, 0.5],
            "val_accuracy": [],
        },
        tmp_path / "training_history.png",
    )

    assert output_path.read_bytes().startswith(PNG_SIGNATURE)


def test_removed_helpers_are_absent_from_visualize_module() -> None:
    """
    旧绘图接口边界
    """
    visualize = _import_visualize_module()
    current_names = (
        "visualize_training_dynamics",
        "visualize_optical_readout_examples",
        "visualize_topology_comparison",
        "visualize_training_curves",
        "visualize_confusion_matrix",
        "visualize_per_class_accuracy",
        "visualize_detector_layout",
        "visualize_phase_mask",
        "visualize_prediction_example",
        "visualize_training_history",
    )

    for name in (name.replace("visualize_", "p" "lot_") for name in current_names):
        assert not hasattr(visualize, name)

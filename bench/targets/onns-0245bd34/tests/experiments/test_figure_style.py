from __future__ import annotations

from pathlib import Path

from matplotlib.colors import to_rgba

from experiments.figure_style import (
    AnnotationPolicy,
    DEFAULT_FONT_SIZES,
    FigureFontSizes,
    FigureStyle,
    apply_figure_style,
    configure_matplotlib_style,
    save_figure_pair,
    style_colorbar,
)
from matplotlib import pyplot as plt


EXPERIMENT_STYLE_CONSUMER_PATHS = (
    Path("experiments/restoration"),
    Path("experiments/validation"),
)


def test_default_font_sizes_match_project_contract() -> None:
    assert DEFAULT_FONT_SIZES == FigureFontSizes(
        text=12,
        title=16,
    )


def test_configure_matplotlib_style_sets_shared_rcparams() -> None:
    style = FigureStyle(
        text_color="#000000",
        muted_text_color="#000000",
        grid_color="#d7dde2",
    )

    configure_matplotlib_style(style, color_cycle=("#111111", "#222222"))

    assert plt.rcParams["font.family"] == ["Arial"]
    assert plt.rcParams["font.size"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["axes.titlesize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["axes.labelsize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["xtick.labelsize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["ytick.labelsize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["legend.fontsize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["svg.fonttype"] == "none"
    assert plt.rcParams["axes.edgecolor"] == "#d7dde2"


def test_apply_figure_style_sets_axis_color_legend_and_font_sizes() -> None:
    style = FigureStyle(
        text_color="#000000",
        muted_text_color="#000000",
        grid_color="#d7dde2",
    )
    fig, axis = plt.subplots()
    try:
        axis.plot([0, 1], [0, 1], label="Series")
        axis.set_title("Subplot")
        axis.set_xlabel("x")
        axis.set_ylabel("y")
        axis.text(0.5, 0.5, "Annotation")
        axis.legend()
        fig.suptitle("Figure")

        apply_figure_style(fig, style)

        assert fig.get_facecolor() == to_rgba(style.panel_facecolor)
        assert fig._suptitle.get_fontsize() == DEFAULT_FONT_SIZES.title
        assert axis.title.get_color() == style.text_color
        assert axis.title.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.xaxis.label.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.yaxis.label.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.get_xticklabels()[0].get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.texts[0].get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.get_legend().get_texts()[0].get_fontsize() == DEFAULT_FONT_SIZES.text
    finally:
        plt.close(fig)


def test_style_colorbar_uses_shared_font_sizes() -> None:
    style = FigureStyle(
        text_color="#000000",
        muted_text_color="#000000",
        grid_color="#d7dde2",
    )
    fig, axis = plt.subplots()
    try:
        image = axis.imshow([[0.0, 1.0]])
        colorbar = fig.colorbar(image, ax=axis)
        colorbar.set_label("Scale")

        style_colorbar(colorbar, style)

        assert colorbar.ax.yaxis.label.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert colorbar.ax.get_yticklabels()[0].get_fontsize() == DEFAULT_FONT_SIZES.text
    finally:
        plt.close(fig)


def test_apply_figure_style_can_preserve_annotation_style() -> None:
    style = FigureStyle(
        text_color="#000000",
        muted_text_color="#000000",
        grid_color="#d7dde2",
    )
    fig, axis = plt.subplots()
    try:
        annotation = axis.text(0.5, 0.5, "Small", color="#b06f6f", fontsize=5)

        apply_figure_style(
            fig,
            style,
            annotation_policy=AnnotationPolicy.PRESERVE_ALL,
        )

        assert annotation.get_color() == "#b06f6f"
        assert annotation.get_fontsize() == 5
    finally:
        plt.close(fig)


def test_save_figure_pair_writes_png_and_svg_with_style(tmp_path: Path) -> None:
    style = FigureStyle(
        text_color="#000000",
        muted_text_color="#000000",
        grid_color="#d7dde2",
    )
    fig, axis = plt.subplots()
    axis.plot([0, 1], [1, 0], label="Series")
    axis.legend()
    fig.suptitle("Figure")

    outputs = save_figure_pair(fig, tmp_path / "styled", style)

    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()
    svg_text = Path(outputs["svg"]).read_text(encoding="utf-8", errors="ignore")
    assert "#d7dde2" in svg_text


def test_save_figure_pair_accepts_custom_style_applier(tmp_path: Path) -> None:
    style = FigureStyle(
        text_color="#000000",
        muted_text_color="#000000",
        grid_color="#d7dde2",
    )
    fig, axis = plt.subplots()
    axis.text(0.5, 0.5, "Diagnostic", color="#b06f6f", fontsize=5)

    def custom_applier(figure: object) -> None:
        apply_figure_style(
            figure,
            style,
            annotation_policy=AnnotationPolicy.PRESERVE_ALL,
        )

    outputs = save_figure_pair(
        fig,
        tmp_path / "custom",
        style,
        style_applier=custom_applier,
    )

    assert Path(outputs["png"]).exists()
    svg_text = Path(outputs["svg"]).read_text(encoding="utf-8", errors="ignore")
    assert "#b06f6f" in svg_text


def test_experiment_packages_do_not_redefine_shared_style_rules() -> None:
    forbidden_tokens = (
        "DEFAULT_FONT_SIZES",
        "FigureFontSizes",
        "fig.savefig",
        "savefig(",
        "rcParams",
        ".grid(",
        "tick_params(",
        "set_fontsize(",
        "linewidth=0.4",
        "alpha=0.25",
        "alpha=0.35",
        "alpha=0.55",
        "alpha=0.75",
        "bbox_inches",
        "dpi=500",
        "dpi=300",
    )
    violations: list[str] = []
    for root in EXPERIMENT_STYLE_CONSUMER_PATHS:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for token in forbidden_tokens:
                if token in source:
                    violations.append(f"{path}: contains {token}")

    assert violations == []

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_hex, to_rgba

from experiments.figure_style import DEFAULT_FONT_SIZES
from experiments.validation.config import (
    VALIDATION_COLORMAPS,
    VALIDATION_FIGURE_SIZES,
    validation_figure_size,
    validation_panel_figure_size,
)
from experiments.validation import style as utils


def test_validation_palette_matches_project_aesthetic_standard() -> None:
    """
    验证 validation 调色板保持低饱和项目风格
    """
    assert utils.VALIDATION_PALETTE == {
        "primary": "#587184",
        "primary_fill": "#8faec0",
        "secondary": "#7897a8",
        "warning": "#b06f6f",
        "accent": "#c98f65",
        "neutral": "#d7dde2",
        "text": "#000000",
        "muted_text": "#000000",
        "panel_bg": "#ffffff",
    }


def test_validation_colormaps_record_semantic_figure_contract() -> None:
    """
    验证语义 colormap 契约稳定
    """
    assert VALIDATION_COLORMAPS == {
        "data_intensity": "gray",
        "optical_amplitude": "hot",
        "optical_intensity": "hot",
        "phase_wrapped": "twilight_shifted",
        "error": "magma",
        "psf": "gray",
    }


def test_validation_figure_sizes_record_semantic_layout_contract() -> None:
    """
    验证 validation 图幅尺寸集中配置
    """
    assert VALIDATION_FIGURE_SIZES["data_transformation_trace"] == (12.8, 3.6)
    assert VALIDATION_FIGURE_SIZES["data_degradation_response"] == (11.8, 13.2)
    assert VALIDATION_FIGURE_SIZES["diffraction_propagation_response"] == (10.8, 6.4)
    assert VALIDATION_FIGURE_SIZES["diffraction_transfer_evolution"] == (8.8, 7.2)
    assert VALIDATION_FIGURE_SIZES["modulation_phase_construction"] == (10.8, 6.8)
    assert VALIDATION_FIGURE_SIZES["lens_phase"] == (11.2, 3.6)
    assert VALIDATION_FIGURE_SIZES["lens_fixed_phase_action"] == (10.8, 3.6)
    assert validation_figure_size("detection_intensity_response") == (10.8, 3.6)
    assert validation_figure_size("layer_device_agreement") == (5.6, 4.4)
    assert validation_panel_figure_size(columns=4, panel_width=3.0) == (12.0, 3.0)


def test_validation_figure_size_rejects_unknown_name() -> None:
    """
    验证未知图幅尺寸名称会失败
    """
    import pytest

    with pytest.raises(ValueError, match="unknown validation figure size"):
        validation_figure_size("unknown")


def test_validation_uses_project_font_contract() -> None:
    """
    验证 validation 复用项目字体规格
    """
    assert utils.VALIDATION_STYLE.font_sizes == DEFAULT_FONT_SIZES
    assert not hasattr(utils, "VALIDATION_FONT_SIZES")


def test_setup_plot_style_sets_low_saturation_defaults() -> None:
    """
    验证绘图默认样式符合低饱和规范
    """
    utils.setup_plot_style()

    assert plt.rcParams["font.family"] == ["Arial"]
    assert plt.rcParams["font.sans-serif"] == ["Arial"]
    assert plt.rcParams["font.size"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["axes.edgecolor"] == utils.VALIDATION_PALETTE["neutral"]
    assert plt.rcParams["axes.labelcolor"] == utils.VALIDATION_PALETTE["text"]
    assert plt.rcParams["axes.titlesize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["axes.labelsize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["xtick.labelsize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["ytick.labelsize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["legend.fontsize"] == DEFAULT_FONT_SIZES.text
    assert plt.rcParams["figure.dpi"] == 600
    assert plt.rcParams["savefig.dpi"] == 600
    assert plt.rcParams["svg.fonttype"] == "none"
    assert plt.rcParams["xtick.color"] == utils.VALIDATION_PALETTE["muted_text"]
    assert plt.rcParams["ytick.color"] == utils.VALIDATION_PALETTE["muted_text"]
    assert plt.rcParams["grid.color"] == utils.VALIDATION_PALETTE["neutral"]


def test_save_figure_pair_applies_validation_style(tmp_path: Path) -> None:
    """
    验证保存图像时自动应用 validation 样式
    """
    fig, axis = plt.subplots()
    axis.plot([0, 1], [0, 1], color="#1f77b4")

    outputs = utils.save_figure_pair(fig, tmp_path, "style_probe")

    assert Path(outputs["png"]).exists()
    assert Path(outputs["svg"]).exists()
    svg_text = Path(outputs["svg"]).read_text(encoding="utf-8", errors="ignore")
    assert utils.VALIDATION_PALETTE["primary"] in svg_text
    assert utils.VALIDATION_PALETTE["neutral"] in svg_text
    assert utils.VALIDATION_PALETTE["muted_text"] in svg_text
    assert "#1f77b4" not in svg_text
    assert "#d62728" not in svg_text


def test_save_figure_pair_centers_titles_on_exported_content(tmp_path: Path) -> None:
    """
    验证保存后总图题仍以完整可见内容为中心
    """
    utils.setup_plot_style()
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.0, 3.2),
        constrained_layout=True,
    )
    fig.suptitle("Forward Intensity Trace")
    for axis, title in zip(axes, ("Input Amplitude", "Input Phase"), strict=True):
        utils.plot_image_with_colorbar(
            axis,
            [[0.0, 1.0], [1.0, 0.0]],
            title,
            "optical_intensity",
        )

    utils.save_figure_pair(fig, tmp_path, "aligned_titles")

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    tight_box = fig.get_tightbbox(renderer).transformed(fig.dpi_scale_trans)
    suptitle_box = fig._suptitle.get_window_extent(renderer)
    tight_center = tight_box.x0 + tight_box.width / 2.0
    suptitle_center = suptitle_box.x0 + suptitle_box.width / 2.0
    assert abs(suptitle_center - tight_center) <= 10.0

    for axis in axes:
        title_box = axis.title.get_window_extent(renderer)
        panel_center = axis.bbox.x0 + axis.bbox.width / 2.0
        title_center = title_box.x0 + title_box.width / 2.0
        assert abs(title_center - panel_center) <= 10.0


def test_plot_image_with_colorbar_styles_colorbar() -> None:
    """
    验证带 colorbar 图像使用统一样式
    """
    fig, axis = plt.subplots()
    try:
        utils.plot_image_with_colorbar(axis, [[0.0, 1.0], [1.0, 0.0]], "Image", "gray")
        utils.apply_validation_figure_style(fig)

        colorbar_axis = fig.axes[-1]
        assert {
            to_hex(spine.get_edgecolor()) for spine in axis.spines.values()
        } == {utils.VALIDATION_PALETTE["text"]}
        assert {
            spine.get_linewidth() for spine in axis.spines.values()
        } == {utils.VALIDATION_STYLE.spine_linewidth}
        tick_colors = {tick.get_color() for tick in colorbar_axis.get_yticklabels()}
        assert tick_colors == {utils.VALIDATION_PALETTE["muted_text"]}
        tick_sizes = {tick.get_fontsize() for tick in colorbar_axis.get_yticklabels()}
        assert tick_sizes == {DEFAULT_FONT_SIZES.text}
        assert colorbar_axis.yaxis.label.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert to_hex(colorbar_axis.spines["outline"].get_edgecolor()) == (
            utils.VALIDATION_PALETTE["text"]
        )
        assert colorbar_axis.spines["outline"].get_linewidth() == (
            utils.VALIDATION_STYLE.spine_linewidth
        )
    finally:
        plt.close(fig)


def test_plot_image_with_colorbar_uses_fixed_physical_geometry() -> None:
    """
    验证 colorbar 宽度与图像间距不随画布宽度变化
    """
    geometries = []
    for figure_width in (4.0, 8.0):
        fig, axis = plt.subplots(figsize=(figure_width, 3.0))
        try:
            utils.plot_image_with_colorbar(
                axis,
                [[0.0, 1.0], [1.0, 0.0]],
                "Image",
                "error",
            )
            fig.canvas.draw()
            colorbar_axis = fig.axes[-1]
            geometries.append(
                (
                    (
                        colorbar_axis.get_position().x0
                        - axis.get_position().x1
                    )
                    * fig.get_figwidth(),
                    colorbar_axis.get_position().width * fig.get_figwidth(),
                )
            )
        finally:
            plt.close(fig)

    for gap_inches, width_inches in geometries:
        assert (
            abs(gap_inches - utils.VALIDATION_STYLE.colorbar_gap_inches)
            < 1e-6
        )
        assert (
            abs(width_inches - utils.VALIDATION_STYLE.colorbar_width_inches)
            < 1e-6
        )


def test_plot_image_with_colorbar_maps_semantic_intensity_to_hot() -> None:
    """
    验证强度语义 colormap 映射到 hot
    """
    fig, axis = plt.subplots()
    try:
        handle = utils.plot_image_with_colorbar(
            axis,
            [[0.0, 1.0], [1.0, 0.0]],
            "Intensity",
            "optical_intensity",
        )

        assert handle.get_cmap().name == "hot"
    finally:
        plt.close(fig)


def test_plot_image_with_colorbar_leaves_hot_as_matplotlib_hot() -> None:
    """
    验证原生 hot colormap 保持不变
    """
    fig, axis = plt.subplots()
    try:
        handle = utils.plot_image_with_colorbar(
            axis,
            [[0.0, 1.0], [1.0, 0.0]],
            "Intensity",
            "hot",
        )

        assert handle.get_cmap().name == "hot"
    finally:
        plt.close(fig)


def test_plot_image_with_colorbar_maps_semantic_phase_to_cyclic_cmap() -> None:
    """
    验证相位语义 colormap 映射到循环色图
    """
    fig, axis = plt.subplots()
    try:
        handle = utils.plot_image_with_colorbar(
            axis,
            [[-3.14, 3.14], [0.0, 1.0]],
            "Phase",
            "phase_wrapped",
        )

        assert handle.get_cmap().name == "twilight_shifted"
    finally:
        plt.close(fig)


def test_plot_image_with_colorbar_maps_semantic_error_to_magma() -> None:
    """
    验证误差语义 colormap 映射到 magma
    """
    fig, axis = plt.subplots()
    try:
        handle = utils.plot_image_with_colorbar(
            axis,
            [[0.0, 1.0], [1.0, 0.0]],
            "Error",
            "error",
        )

        assert handle.get_cmap().name == "magma"
    finally:
        plt.close(fig)


def test_validation_style_helper_updates_axes_without_changing_data() -> None:
    """
    验证样式 helper 不改变图中数据
    """
    fig, axis = plt.subplots()
    try:
        line = axis.plot([0, 1], [1, 0])[0]
        axis.set_title("Subplot")
        axis.set_xlabel("x")
        axis.set_ylabel("y")
        axis.text(0.5, 0.5, "Annotation")
        axis.legend(["Series"])
        fig.suptitle("Figure")

        utils.apply_validation_figure_style(fig)

        assert tuple(line.get_xdata()) == (0, 1)
        assert tuple(line.get_ydata()) == (1, 0)
        assert fig.get_facecolor() == to_rgba(utils.VALIDATION_PALETTE["panel_bg"])
        assert fig._suptitle.get_fontsize() == DEFAULT_FONT_SIZES.title
        assert axis.title.get_color() == utils.VALIDATION_PALETTE["text"]
        assert axis.title.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.xaxis.label.get_color() == utils.VALIDATION_PALETTE["text"]
        assert axis.xaxis.label.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.yaxis.label.get_color() == utils.VALIDATION_PALETTE["text"]
        assert axis.yaxis.label.get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.get_xticklabels()[0].get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.texts[0].get_fontsize() == DEFAULT_FONT_SIZES.text
        assert axis.get_legend().get_texts()[0].get_fontsize() == DEFAULT_FONT_SIZES.text
        assert {
            to_hex(spine.get_edgecolor()) for spine in axis.spines.values()
        } == {utils.VALIDATION_PALETTE["neutral"]}
    finally:
        plt.close(fig)

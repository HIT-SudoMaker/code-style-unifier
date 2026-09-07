from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

from matplotlib import pyplot as plt


@dataclass(frozen=True, slots=True)
class FigureFontSizes:
    """
    保存共享绘图字体大小配置
    """

    text: int = 12
    title: int = 16


@dataclass(frozen=True, slots=True)
class FigureStyle:
    """
    保存共享绘图视觉样式配置
    """

    text_color: str
    muted_text_color: str
    grid_color: str
    panel_facecolor: str = "#ffffff"
    font_sizes: FigureFontSizes = FigureFontSizes()
    dpi: int = 600
    colorbar_width_inches: float = 0.10
    colorbar_gap_inches: float = 0.08
    line_width: float = 1.6
    spine_linewidth: float = 1.0
    grid_linewidth: float = 0.4
    grid_alpha: float = 0.55
    subtle_grid_alpha: float = 0.35
    diagnostic_grid_alpha: float = 0.25
    histogram_edge_linewidth: float = 0.4
    histogram_alpha: float = 0.9


class AnnotationPolicy(str, Enum):
    """
    约束图内标注的共享样式接管范围
    """

    STANDARDIZE = "standardize"
    PRESERVE_COLORS = "preserve_colors"
    PRESERVE_FONT_SIZES = "preserve_font_sizes"
    PRESERVE_ALL = "preserve_all"


DEFAULT_FONT_SIZES = FigureFontSizes()
HIGH_RESOLUTION_DPI = 600
STANDARD_FIGURE_DPI = 300
DEFAULT_DPI = HIGH_RESOLUTION_DPI


def configure_matplotlib_style(
    style: FigureStyle,
    *,
    dpi: int | None = None,
    color_cycle: list[str] | tuple[str, ...] | None = None,
) -> None:
    """
    配置 Matplotlib 全局绘图样式
    """

    resolved_dpi = style.dpi if dpi is None else dpi
    rc_params: dict[str, object] = {
        "figure.dpi": resolved_dpi,
        "savefig.dpi": resolved_dpi,
        "savefig.bbox": "tight",
        "savefig.facecolor": style.panel_facecolor,
        "figure.facecolor": style.panel_facecolor,
        "axes.facecolor": style.panel_facecolor,
        "axes.edgecolor": style.grid_color,
        "axes.labelcolor": style.text_color,
        "axes.titlesize": style.font_sizes.text,
        "axes.titlecolor": style.text_color,
        "axes.labelsize": style.font_sizes.text,
        "axes.linewidth": style.spine_linewidth,
        "xtick.color": style.muted_text_color,
        "ytick.color": style.muted_text_color,
        "xtick.labelsize": style.font_sizes.text,
        "ytick.labelsize": style.font_sizes.text,
        "grid.color": style.grid_color,
        "grid.linewidth": style.grid_linewidth,
        "grid.alpha": style.grid_alpha,
        "font.size": style.font_sizes.text,
        "font.family": "Arial",
        "font.sans-serif": ["Arial"],
        "legend.fontsize": style.font_sizes.text,
        "lines.linewidth": style.line_width,
        "image.interpolation": "nearest",
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
    if color_cycle is not None:
        rc_params["axes.prop_cycle"] = matplotlib.cycler(color=list(color_cycle))
    plt.rcParams.update(rc_params)


def apply_figure_style(
    fig: Any,
    style: FigureStyle,
    *,
    annotation_policy: AnnotationPolicy = AnnotationPolicy.STANDARDIZE,
) -> None:
    """
    应用共享样式到整张图
    """

    fig.patch.set_facecolor(style.panel_facecolor)
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None:
        suptitle.set_color(style.text_color)
        suptitle.set_fontsize(style.font_sizes.title)
    for axis in fig.axes:
        style_axis(
            axis,
            style,
            annotation_policy=annotation_policy,
        )


def style_axis(
    axis: Any,
    style: FigureStyle,
    *,
    annotation_policy: AnnotationPolicy = AnnotationPolicy.STANDARDIZE,
) -> None:
    """
    应用共享样式到单个坐标轴
    """

    axis.set_facecolor(style.panel_facecolor)
    axis.title.set_color(style.text_color)
    axis.title.set_fontsize(style.font_sizes.text)
    axis.xaxis.label.set_color(style.text_color)
    axis.xaxis.label.set_fontsize(style.font_sizes.text)
    axis.yaxis.label.set_color(style.text_color)
    axis.yaxis.label.set_fontsize(style.font_sizes.text)
    axis.tick_params(colors=style.muted_text_color, labelsize=style.font_sizes.text)
    for spine in axis.spines.values():
        spine.set_color(style.grid_color)
        spine.set_linewidth(style.spine_linewidth)
    for gridline in [*axis.get_xgridlines(), *axis.get_ygridlines()]:
        gridline.set_color(style.grid_color)
        gridline.set_alpha(style.grid_alpha)
        gridline.set_linewidth(style.grid_linewidth)
    preserves_colors = annotation_policy in {
        AnnotationPolicy.PRESERVE_COLORS,
        AnnotationPolicy.PRESERVE_ALL,
    }
    preserves_font_sizes = annotation_policy in {
        AnnotationPolicy.PRESERVE_FONT_SIZES,
        AnnotationPolicy.PRESERVE_ALL,
    }
    for text in axis.texts:
        if not preserves_font_sizes:
            text.set_fontsize(style.font_sizes.text)
        if (
            not preserves_colors
            and text.get_color() != style.panel_facecolor
        ):
            text.set_color(style.text_color)
    legend = axis.get_legend()
    if legend is not None:
        legend.get_frame().set_edgecolor(style.grid_color)
        legend.get_frame().set_facecolor(style.panel_facecolor)
        for text in legend.get_texts():
            text.set_color(style.text_color)
            text.set_fontsize(style.font_sizes.text)


def style_colorbar(colorbar: Any, style: FigureStyle) -> None:
    """
    应用共享样式到颜色条
    """

    colorbar.ax.tick_params(
        colors=style.muted_text_color,
        labelsize=style.font_sizes.text,
    )
    colorbar.ax.yaxis.label.set_color(style.text_color)
    colorbar.ax.yaxis.label.set_fontsize(style.font_sizes.text)
    if hasattr(colorbar, "outline"):
        colorbar.outline.set_edgecolor(style.grid_color)
        colorbar.outline.set_linewidth(style.spine_linewidth)
    for spine in colorbar.ax.spines.values():
        spine.set_color(style.grid_color)
        spine.set_linewidth(style.spine_linewidth)


def style_grid(
    axis: Any,
    style: FigureStyle,
    *,
    is_enabled: bool = True,
    grid_axis: str = "both",
    alpha: float | None = None,
) -> None:
    """
    配置坐标轴网格样式
    """

    axis.grid(
        is_enabled,
        axis=grid_axis,
        linewidth=style.grid_linewidth,
        alpha=style.grid_alpha if alpha is None else alpha,
        color=style.grid_color,
    )


def save_figure_pair(
    fig: Any,
    output_base: str | Path,
    style: FigureStyle,
    *,
    dpi: int | None = None,
    style_applier: Callable[[Any], None] | None = None,
) -> dict[str, str]:
    """
    保存同名 PNG 和 SVG 图像
    """

    base_path = Path(output_base)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    png_path = base_path.with_suffix(".png")
    svg_path = base_path.with_suffix(".svg")
    if style_applier is None:
        apply_figure_style(fig, style)
    else:
        style_applier(fig)
    resolved_dpi = style.dpi if dpi is None else dpi
    fig.savefig(png_path, dpi=resolved_dpi, bbox_inches="tight", facecolor=style.panel_facecolor)
    fig.savefig(svg_path, bbox_inches="tight", facecolor=style.panel_facecolor)
    plt.close(fig)
    return {"png": str(png_path), "svg": str(svg_path)}


def save_figure(
    fig: Any,
    output_path: str | Path,
    style: FigureStyle,
    *,
    dpi: int | None = None,
    style_applier: Callable[[Any], None] | None = None,
) -> Path:
    """
    保存单个图像文件
    """

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if style_applier is None:
        apply_figure_style(fig, style)
    else:
        style_applier(fig)
    resolved_dpi = style.dpi if dpi is None else dpi
    fig.savefig(path, dpi=resolved_dpi, bbox_inches="tight", facecolor=style.panel_facecolor)
    plt.close(fig)
    return path


def save_named_figure_pair(
    fig: Any,
    output_dir: str | Path,
    name: str,
    style: FigureStyle,
    *,
    dpi: int | None = None,
    style_applier: Callable[[Any], None] | None = None,
) -> dict[str, str]:
    """
    保存目录下的同名 PNG 和 SVG 图像
    """

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return save_figure_pair(
        fig,
        directory / name,
        style,
        dpi=dpi,
        style_applier=style_applier,
    )

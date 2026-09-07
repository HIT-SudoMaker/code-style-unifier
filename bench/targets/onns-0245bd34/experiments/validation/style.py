from __future__ import annotations

from collections.abc import Sequence
import math
from pathlib import Path
from typing import Any

import matplotlib
from matplotlib.colors import to_hex
from mpl_toolkits.axes_grid1 import ImageGrid
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1.axes_size import Fixed
import numpy as np

from experiments.figure_style import (
    AnnotationPolicy,
    DEFAULT_DPI,
    FigureStyle,
    apply_figure_style as apply_project_figure_style,
    configure_matplotlib_style,
    save_figure_pair as save_project_figure_pair,
    style_axis as style_project_axis,
    style_colorbar as style_project_colorbar,
    style_grid as style_project_grid,
)
from experiments.validation.artifacts import ensure_output_dir
from experiments.validation.config import (
    VALIDATION_COLORMAPS,
    validation_figure_size,
    validation_panel_figure_size,
)

FIGURE_DPI = DEFAULT_DPI
VALIDATION_PALETTE = {
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
VALIDATION_STYLE = FigureStyle(
    text_color=VALIDATION_PALETTE["text"],
    muted_text_color=VALIDATION_PALETTE["muted_text"],
    grid_color=VALIDATION_PALETTE["neutral"],
    panel_facecolor=VALIDATION_PALETTE["panel_bg"],
)
_MATPLOTLIB_DEFAULT_COLORS = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
)


def setup_plot_style(dpi: int = FIGURE_DPI) -> None:
    """
    配置无界面科研绘图风格
    """
    matplotlib.use("Agg", force=True)
    configure_matplotlib_style(
        VALIDATION_STYLE,
        dpi=dpi,
        color_cycle=[
            VALIDATION_PALETTE["primary"],
            VALIDATION_PALETTE["secondary"],
            VALIDATION_PALETTE["accent"],
            VALIDATION_PALETTE["warning"],
        ],
    )


def resolve_validation_cmap(cmap: str) -> str:
    """
    解析验证语义色图
    """
    return VALIDATION_COLORMAPS.get(cmap, cmap)


def style_validation_colorbar(colorbar: Any) -> None:
    """
    统一验证色条
    """
    style_project_colorbar(colorbar, VALIDATION_STYLE)
    colorbar.ax._validation_colorbar = True
    if hasattr(colorbar, "outline"):
        colorbar.outline.set_edgecolor(VALIDATION_PALETTE["text"])
        colorbar.outline.set_linewidth(VALIDATION_STYLE.spine_linewidth)
    _style_validation_frame(colorbar.ax)


def style_validation_grid(
    axis: Any,
    *,
    grid_axis: str = "both",
    level: str = "subtle",
) -> None:
    """
    统一验证网格
    """
    alpha_by_level = {
        "subtle": VALIDATION_STYLE.subtle_grid_alpha,
        "diagnostic": VALIDATION_STYLE.diagnostic_grid_alpha,
        "default": VALIDATION_STYLE.grid_alpha,
    }
    if level not in alpha_by_level:
        message = f"level must be one of {tuple(alpha_by_level)}, got {level}"
        raise ValueError(message)
    style_project_grid(
        axis,
        VALIDATION_STYLE,
        grid_axis=grid_axis,
        alpha=alpha_by_level[level],
    )


def apply_validation_figure_style(fig: Any) -> None:
    """
    应用验证图形风格且不改变数据
    """
    apply_project_figure_style(
        fig,
        VALIDATION_STYLE,
        annotation_policy=AnnotationPolicy.PRESERVE_COLORS,
    )
    for axis in fig.axes:
        _style_validation_axis(axis)
    _align_validation_figure_title(fig)


def save_figure_pair(
    fig: Any,
    output_dir: Path,
    name: str,
    dpi: int = FIGURE_DPI,
) -> dict[str, str]:
    """
    保存 PNG 与 SVG 图像对
    """
    return save_project_figure_pair(
        fig,
        ensure_output_dir(output_dir) / name,
        VALIDATION_STYLE,
        dpi=dpi,
        style_applier=apply_validation_figure_style,
    )


def add_validation_colorbar(
    axis: Any,
    handle: Any,
    label: str | None = None,
) -> Any:
    """
    添加固定物理尺寸的色条
    """
    divider = make_axes_locatable(axis)
    colorbar_axis = divider.append_axes(
        "right",
        size=Fixed(VALIDATION_STYLE.colorbar_width_inches),
        pad=Fixed(VALIDATION_STYLE.colorbar_gap_inches),
    )
    colorbar = axis.figure.colorbar(handle, cax=colorbar_axis)
    if label is not None:
        colorbar.set_label(label)
    style_validation_colorbar(colorbar)
    return colorbar


def plot_image_with_colorbar(
    axis: Any,
    image: object,
    title: str,
    cmap: str,
    label: str | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
) -> Any:
    """
    绘制带色条的图像面板
    """
    handle = axis.imshow(
        tensor_to_numpy(image),
        cmap=resolve_validation_cmap(cmap),
        vmin=vmin,
        vmax=vmax,
    )
    axis.set_title(title)
    axis.set_xticks([])
    axis.set_yticks([])
    add_validation_colorbar(axis, handle, label)
    _style_validation_axis(axis)
    return handle


def plot_shared_image_grid(
    fig: Any,
    *,
    images: Sequence[object],
    titles: Sequence[str],
    shape: tuple[int, int],
    cmap: str,
    label: str | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    axes_pad: float = 0.35,
) -> Sequence[Any]:
    """
    绘制共用单一色条的等尺度图像网格
    """
    if len(images) != len(titles) or len(images) != shape[0] * shape[1]:
        message = "shared image grid requires aligned images, titles, and shape"
        raise ValueError(message)
    grid = ImageGrid(
        fig,
        111,
        nrows_ncols=shape,
        axes_pad=axes_pad,
        cbar_mode="single",
        cbar_location="right",
        cbar_pad=VALIDATION_STYLE.colorbar_gap_inches,
        cbar_size=VALIDATION_STYLE.colorbar_width_inches,
    )
    handle = None
    for axis, image, title in zip(grid, images, titles, strict=True):
        handle = axis.imshow(
            tensor_to_numpy(image),
            cmap=resolve_validation_cmap(cmap),
            vmin=vmin,
            vmax=vmax,
        )
        axis.set_title(title)
        axis.set_xticks([])
        axis.set_yticks([])
        _style_validation_axis(axis)
    assert handle is not None
    colorbar = fig.colorbar(handle, cax=grid.cbar_axes[0])
    if label is not None:
        colorbar.set_label(label)
    style_validation_colorbar(colorbar)
    return tuple(grid)


def save_device_agreement_figure(
    output_dir: Path,
    *,
    difference: object | None = None,
    mean_abs_error: float | None = None,
    max_abs_error: float | None = None,
) -> dict[str, str]:
    """
    保存统一的 CPU 与 GPU 数值差异证据
    """
    from matplotlib import pyplot as plt

    fig, axis = plt.subplots(
        figsize=validation_figure_size("layer_device_agreement"),
        constrained_layout=True,
    )
    if difference is None:
        axis.set_title("Device Agreement")
        axis.text(
            0.5,
            0.5,
            "CUDA Unavailable",
            ha="center",
            va="center",
            transform=axis.transAxes,
        )
        axis.set_axis_off()
        return save_figure_pair(fig, output_dir, "device_agreement")

    values = tensor_to_numpy(difference)
    maximum = float(np.max(values))
    upper = maximum if maximum > 0.0 else 1e-7
    plot_image_with_colorbar(
        axis,
        values,
        "CPU–GPU Absolute Difference",
        "error",
        "Absolute difference",
        vmin=0.0,
        vmax=upper,
    )
    if mean_abs_error is None or max_abs_error is None:
        message = "device agreement metrics are required with a difference image"
        raise ValueError(message)
    axis.set_xlabel(
        f"Mean {mean_abs_error:.3e}   ·   Max {max_abs_error:.3e}",
        labelpad=10,
    )
    fig.suptitle("Device Agreement")
    return save_figure_pair(fig, output_dir, "device_agreement")


def style_error_scale(
    axis: Any,
    values: Sequence[float],
    *,
    floor: float,
) -> None:
    """
    按误差跨度选择纵轴，并标明仅用于显示的数值下限
    """
    positive = [value for value in values if value > floor]
    has_display_floor = any(value <= floor for value in values)
    if (
        not has_display_floor
        and positive
        and max(positive) / min(positive) < 10.0
    ):
        axis.ticklabel_format(
            axis="y",
            style="sci",
            scilimits=(0, 0),
            useMathText=True,
        )
    else:
        axis.set_yscale("log")
    if has_display_floor:
        exponent = round(math.log10(floor))
        axis.text(
            0.98,
            0.05,
            rf"Display floor: $10^{{{exponent}}}$",
            transform=axis.transAxes,
            ha="right",
            va="bottom",
            color="#5f6368",
        )


def plot_complex_field_pair(
    axes: Sequence[Any],
    field: object,
    title_prefix: str,
) -> None:
    """
    绘制复数光场的振幅与相位
    """
    values = tensor_to_numpy(field)
    plot_image_with_colorbar(
        axes[0],
        np.abs(values),
        f"{title_prefix} amplitude",
        "optical_amplitude",
    )
    plot_image_with_colorbar(
        axes[1],
        np.angle(values),
        f"{title_prefix} phase",
        "phase_wrapped",
        vmin=-np.pi,
        vmax=np.pi,
    )


def tensor_to_numpy(value: object) -> np.ndarray:
    """
    将张量或数组转换为数值图像数组
    """
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.squeeze(np.asarray(value))


def _default_matplotlib_hex(value: object) -> str | None:
    try:
        hex_color = to_hex(value).lower()
    except (TypeError, ValueError):
        return None
    return hex_color if hex_color in _MATPLOTLIB_DEFAULT_COLORS else None


def _style_validation_frame(axis: Any) -> None:
    for spine in axis.spines.values():
        spine.set_color(VALIDATION_PALETTE["text"])
        spine.set_linewidth(VALIDATION_STYLE.spine_linewidth)


def _style_validation_axis(axis: Any) -> None:
    style_project_axis(
        axis,
        VALIDATION_STYLE,
        annotation_policy=AnnotationPolicy.PRESERVE_COLORS,
    )
    palette_cycle = (
        VALIDATION_PALETTE["primary"],
        VALIDATION_PALETTE["secondary"],
        VALIDATION_PALETTE["accent"],
        VALIDATION_PALETTE["warning"],
    )
    for index, line in enumerate(axis.lines):
        if _default_matplotlib_hex(line.get_color()) is not None:
            line.set_color(palette_cycle[index % len(palette_cycle)])
    for patch in axis.patches:
        if _default_matplotlib_hex(patch.get_facecolor()) is not None:
            patch.set_facecolor(VALIDATION_PALETTE["primary_fill"])
            patch.set_edgecolor(VALIDATION_PALETTE["primary"])
    legend = axis.get_legend()
    if legend is not None:
        legend.get_frame().set_edgecolor(VALIDATION_PALETTE["neutral"])
        legend.get_frame().set_facecolor(VALIDATION_PALETTE["panel_bg"])
        for text in legend.get_texts():
            text.set_color(VALIDATION_PALETTE["text"])
    if axis.images or getattr(axis, "_validation_colorbar", False):
        _style_validation_frame(axis)


def _align_validation_figure_title(fig: Any) -> None:
    fig.canvas.draw()
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is None:
        return
    renderer = fig.canvas.get_renderer()
    tight_box = fig.get_tightbbox(renderer).transformed(fig.dpi_scale_trans)
    tight_center = tight_box.x0 + tight_box.width / 2.0
    suptitle_x = fig.transFigure.inverted().transform((tight_center, 0.0))[0]
    suptitle.set_x(float(suptitle_x))
    fig.set_layout_engine(None)

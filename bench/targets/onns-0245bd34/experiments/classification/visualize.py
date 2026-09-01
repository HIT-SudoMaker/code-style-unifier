from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import TypeVar

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.colors
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle
import numpy as np
import torch


_STYLE_CONFIG_PATH = Path(__file__).with_name("style_config.json")
_DEFAULT_BBOX_INCHES = object()
_REQUIRED_TOP_LEVEL_SECTIONS = frozenset(
    ("font", "export", "palette", "colormaps", "lines", "overlays", "figures")
)
_REQUIRED_FONT_ROLES = frozenset(
    (
        "figure_title",
        "axis_title",
        "axis_label",
        "tick_label",
        "legend",
        "annotation",
        "matrix_cell",
    )
)
_REQUIRED_PALETTE_ROLES = frozenset(
    (
        "paper_text",
        "muted_text",
        "grid",
        "panel_bg",
        "train_line",
        "validation_line",
        "report_bar",
        "report_bar_edge",
        "topology_secondary",
        "timing_bar",
        "detector_red",
        "detector_halo",
        "max_energy",
        "intensity_low",
        "intensity_high",
        "confusion_low",
        "confusion_mid",
        "confusion_high",
        "energy_low",
        "energy_mid",
        "energy_high",
        "phase_low",
        "phase_mid",
        "phase_high",
    )
)
_REQUIRED_COLORMAP_ROLES = frozenset(
    ("confusion_matrix", "energy_distribution", "phase", "intensity")
)
_REQUIRED_LINE_ROLES = frozenset(
    ("axis_spine", "grid", "training_curve", "best_epoch", "bar_edge")
)
_REQUIRED_OVERLAY_ROLES = frozenset(("detector_region", "max_detector_region"))
_REQUIRED_FIGURE_ROLES = frozenset(
    (
        "training_dynamics",
        "confusion_matrix",
        "per_class_accuracy",
        "optical_readout_examples",
        "topology_comparison",
        "phase_mask",
        "detector_layout",
        "prediction_example",
        "optimization_history",
    )
)
_SUPPORTED_EXPORT_FORMATS = frozenset(("png", "svg"))
_MISSING = object()
_ConfigT = TypeVar("_ConfigT")


@dataclass(frozen=True, slots=True)
class FontConfig:
    """
    保存分类绘图使用的字体字号角色
    """

    figure_title: float
    axis_title: float
    axis_label: float
    tick_label: float
    legend: float
    annotation: float
    matrix_cell: float


@dataclass(frozen=True, slots=True)
class ExportConfig:
    """
    保存图像导出配置
    """

    dpi: int
    formats: tuple[str, ...]
    bbox_inches: str
    facecolor: str


@dataclass(frozen=True, slots=True)
class LineConfig:
    """
    保存分类绘图线条样式配置
    """

    width: float
    alpha: float = 1.0
    linestyle: str = "-"


@dataclass(frozen=True, slots=True)
class OverlayConfig:
    """
    保存分类绘图叠加标注样式配置
    """

    color: str
    linewidth: float
    linestyle: str
    alpha: float


@dataclass(frozen=True, slots=True)
class FigureConfig:
    """
    保存单张分类图的布局和语义配置
    """

    filename: str
    title: str
    figsize: tuple[float, float]
    style: str
    accuracy_ymin: float | None = None
    legend_columns: int = 1
    uses_gap_annotation: bool = True
    row_height: float = 1.9
    column_width_ratios: tuple[float, ...] = (1.0, 1.0, 1.0, 1.0)
    detector_column_gap: float = 0.0
    column_wspace: float | None = None
    row_hspace: float | None = None
    grid_left: float | None = None
    grid_right: float | None = None
    grid_top: float | None = None
    grid_bottom: float | None = None
    bbox_inches: str | None = None
    uses_detector_xlabel: bool = True


@dataclass(frozen=True, slots=True)
class ColormapConfig:
    """
    保存分类绘图 colormap 名称和色阶角色
    """

    name: str
    colors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClassificationStyleConfig:
    """
    保存分类实验的完整本地绘图风格配置
    """

    font: FontConfig
    export: ExportConfig
    palette: dict[str, str]
    colormaps: dict[str, ColormapConfig]
    lines: dict[str, LineConfig]
    overlays: dict[str, OverlayConfig]
    figures: dict[str, FigureConfig]


def _require_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        message = f"{context} must be an object"
        raise ValueError(message)
    return value


def _validate_required_roles(
    values: Mapping[str, object],
    required_roles: frozenset[str],
    context: str,
) -> None:
    missing_roles = sorted(required_roles.difference(values))
    if missing_roles:
        joined = ", ".join(missing_roles)
        message = f"{context} is missing required role(s): {joined}"
        raise ValueError(message)


def _coerce_number(
    values: Mapping[str, object],
    key: str,
    context: str,
    *,
    default: object = _MISSING,
) -> float:
    value = values.get(key, default)
    if value is _MISSING:
        message = f"{context}.{key} is required"
        raise ValueError(message)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        message = f"{context}.{key} must be a number"
        raise ValueError(message)
    return float(value)


def _coerce_positive_int(values: Mapping[str, object], key: str, context: str) -> int:
    value = values.get(key, _MISSING)
    if value is _MISSING:
        message = f"{context}.{key} is required"
        raise ValueError(message)
    if isinstance(value, bool) or not isinstance(value, int):
        message = f"{context}.{key} must be an integer"
        raise ValueError(message)
    if value <= 0:
        message = f"{context}.{key} must be positive"
        raise ValueError(message)
    return value


def _coerce_optional_number(
    values: Mapping[str, object],
    key: str,
    context: str,
) -> float | None:
    value = values.get(key, None)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        message = f"{context}.{key} must be a number"
        raise ValueError(message)
    return float(value)


def _coerce_optional_number_tuple(
    values: Mapping[str, object],
    key: str,
    context: str,
) -> tuple[float, ...] | None:
    raw_values = values.get(key, None)
    if raw_values is None:
        return None
    if isinstance(raw_values, (str, bytes)) or not isinstance(raw_values, Sequence):
        message = f"{context}.{key} must be a list of numbers"
        raise ValueError(message)
    normalized: list[float] = []
    for index, value in enumerate(raw_values):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            message = f"{context}.{key}[{index}] must be a number"
            raise ValueError(message)
        numeric_value = float(value)
        if numeric_value <= 0.0:
            message = f"{context}.{key}[{index}] must be positive"
            raise ValueError(message)
        normalized.append(numeric_value)
    return tuple(normalized)


def _coerce_optional_string(
    values: Mapping[str, object],
    key: str,
    context: str,
) -> str | None:
    value = values.get(key, None)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        message = f"{context}.{key} must be null or a non-empty string"
        raise ValueError(message)
    return value


def _coerce_optional_positive_int(
    values: Mapping[str, object],
    key: str,
    context: str,
    *,
    default: int,
) -> int:
    value = values.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        message = f"{context}.{key} must be a positive integer"
        raise ValueError(message)
    if value <= 0:
        message = f"{context}.{key} must be positive"
        raise ValueError(message)
    return value


def _coerce_string(
    values: Mapping[str, object],
    key: str,
    context: str,
    *,
    default: object = _MISSING,
) -> str:
    value = values.get(key, default)
    if value is _MISSING:
        message = f"{context}.{key} is required"
        raise ValueError(message)
    if not isinstance(value, str) or not value:
        message = f"{context}.{key} must be a non-empty string"
        raise ValueError(message)
    return value


def _coerce_string_tuple(values: Mapping[str, object], key: str, context: str) -> tuple[str, ...]:
    raw_values = values.get(key, _MISSING)
    if raw_values is _MISSING:
        message = f"{context}.{key} is required"
        raise ValueError(message)
    if isinstance(raw_values, (str, bytes)) or not isinstance(raw_values, Sequence):
        message = f"{context}.{key} must be a list of strings"
        raise ValueError(message)
    strings: list[str] = []
    for index, value in enumerate(raw_values):
        if not isinstance(value, str) or not value:
            message = f"{context}.{key}[{index}] must be a non-empty string"
            raise ValueError(message)
        strings.append(value)
    return tuple(strings)


def _coerce_figsize(values: Mapping[str, object], context: str) -> tuple[float, float]:
    raw_values = values.get("figsize", _MISSING)
    if raw_values is _MISSING:
        message = f"{context}.figsize is required"
        raise ValueError(message)
    if isinstance(raw_values, (str, bytes)) or not isinstance(raw_values, Sequence):
        message = f"{context}.figsize must contain two numbers"
        raise ValueError(message)
    if len(raw_values) != 2:
        message = f"{context}.figsize must contain two numbers"
        raise ValueError(message)
    width, height = raw_values
    if (
        isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, (int, float))
        or not isinstance(height, (int, float))
    ):
        message = f"{context}.figsize must contain two numbers"
        raise ValueError(message)
    return (float(width), float(height))


def _coerce_font_config(values: Mapping[str, object]) -> FontConfig:
    _validate_required_roles(values, _REQUIRED_FONT_ROLES, "font")
    return FontConfig(
        figure_title=_coerce_number(values, "figure_title", "font"),
        axis_title=_coerce_number(values, "axis_title", "font"),
        axis_label=_coerce_number(values, "axis_label", "font"),
        tick_label=_coerce_number(values, "tick_label", "font"),
        legend=_coerce_number(values, "legend", "font"),
        annotation=_coerce_number(values, "annotation", "font"),
        matrix_cell=_coerce_number(values, "matrix_cell", "font"),
    )


def _coerce_export_config(values: Mapping[str, object]) -> ExportConfig:
    raw_formats = _coerce_string_tuple(values, "formats", "export")
    formats = tuple(format_name.lower() for format_name in raw_formats)
    if not formats:
        message = "export.formats must not be empty"
        raise ValueError(message)
    unsupported_formats = sorted(set(formats).difference(_SUPPORTED_EXPORT_FORMATS))
    if unsupported_formats:
        joined = ", ".join(unsupported_formats)
        message = f"export.formats contains unsupported format(s): {joined}"
        raise ValueError(message)
    return ExportConfig(
        dpi=_coerce_positive_int(values, "dpi", "export"),
        formats=formats,
        bbox_inches=_coerce_string(values, "bbox_inches", "export"),
        facecolor=_coerce_string(values, "facecolor", "export"),
    )


def _coerce_palette(values: Mapping[str, object]) -> dict[str, str]:
    _validate_required_roles(values, _REQUIRED_PALETTE_ROLES, "palette")
    palette: dict[str, str] = {}
    for role, color in values.items():
        if not isinstance(color, str) or not color:
            message = f"palette.{role} must be a non-empty string"
            raise ValueError(message)
        palette[role] = color
    return palette


def _coerce_colormap_config(values: Mapping[str, object], context: str) -> ColormapConfig:
    return ColormapConfig(
        name=_coerce_string(values, "name", context),
        colors=_coerce_string_tuple(values, "colors", context),
    )


def _coerce_line_config(values: Mapping[str, object], context: str) -> LineConfig:
    return LineConfig(
        width=_coerce_number(values, "width", context),
        alpha=_coerce_number(values, "alpha", context, default=1.0),
        linestyle=_coerce_string(values, "linestyle", context, default="-"),
    )


def _coerce_overlay_config(values: Mapping[str, object], context: str) -> OverlayConfig:
    return OverlayConfig(
        color=_coerce_string(values, "color", context),
        linewidth=_coerce_number(values, "linewidth", context),
        linestyle=_coerce_string(values, "linestyle", context),
        alpha=_coerce_number(values, "alpha", context),
    )


def _coerce_figure_config(values: Mapping[str, object], context: str) -> FigureConfig:
    row_height = _coerce_optional_number(values, "row_height", context)
    detector_column_gap = _coerce_optional_number(
        values,
        "detector_column_gap",
        context,
    )
    if detector_column_gap is not None and detector_column_gap < 0.0:
        message = f"{context}.detector_column_gap must be non-negative"
        raise ValueError(message)
    column_width_ratios = _coerce_optional_number_tuple(
        values,
        "column_width_ratios",
        context,
    )
    gap_annotation = values.get("uses_gap_annotation", True)
    if not isinstance(gap_annotation, bool):
        message = f"{context}.uses_gap_annotation must be a boolean"
        raise ValueError(message)
    detector_xlabel = values.get("uses_detector_xlabel", True)
    if not isinstance(detector_xlabel, bool):
        message = f"{context}.uses_detector_xlabel must be a boolean"
        raise ValueError(message)
    return FigureConfig(
        filename=_coerce_string(values, "filename", context),
        title=_coerce_string(values, "title", context),
        figsize=_coerce_figsize(values, context),
        style=_coerce_string(values, "style", context),
        accuracy_ymin=_coerce_optional_number(values, "accuracy_ymin", context),
        legend_columns=_coerce_optional_positive_int(
            values,
            "legend_columns",
            context,
            default=1,
        ),
        uses_gap_annotation=gap_annotation,
        row_height=1.9 if row_height is None else row_height,
        column_width_ratios=(
            (1.0, 1.0, 1.0, 1.0)
            if column_width_ratios is None
            else column_width_ratios
        ),
        detector_column_gap=(
            0.0 if detector_column_gap is None else detector_column_gap
        ),
        column_wspace=_coerce_optional_number(values, "column_wspace", context),
        row_hspace=_coerce_optional_number(values, "row_hspace", context),
        grid_left=_coerce_optional_number(values, "grid_left", context),
        grid_right=_coerce_optional_number(values, "grid_right", context),
        grid_top=_coerce_optional_number(values, "grid_top", context),
        grid_bottom=_coerce_optional_number(values, "grid_bottom", context),
        bbox_inches=_coerce_optional_string(values, "bbox_inches", context),
        uses_detector_xlabel=detector_xlabel,
    )


def _coerce_role_map(
    values: Mapping[str, object],
    required_roles: frozenset[str],
    context: str,
    factory: Callable[[Mapping[str, object], str], _ConfigT],
) -> dict[str, _ConfigT]:
    _validate_required_roles(values, required_roles, context)
    resolved: dict[str, _ConfigT] = {}
    for role, raw_config in values.items():
        role_context = f"{context}.{role}"
        resolved[role] = factory(_require_mapping(raw_config, role_context), role_context)
    return resolved


@lru_cache(maxsize=1)
def load_style_config() -> ClassificationStyleConfig:
    """
    读取并校验分类本地绘图风格配置
    """
    payload = json.loads(_STYLE_CONFIG_PATH.read_text(encoding="utf-8"))
    root = _require_mapping(payload, "classification style config")
    _validate_required_roles(
        root,
        _REQUIRED_TOP_LEVEL_SECTIONS,
        "classification style config",
    )

    font_values = _require_mapping(root["font"], "font")
    export_values = _require_mapping(root["export"], "export")
    palette_values = _require_mapping(root["palette"], "palette")
    colormap_values = _require_mapping(root["colormaps"], "colormaps")
    line_values = _require_mapping(root["lines"], "lines")
    overlay_values = _require_mapping(root["overlays"], "overlays")
    figure_values = _require_mapping(root["figures"], "figures")

    return ClassificationStyleConfig(
        font=_coerce_font_config(font_values),
        export=_coerce_export_config(export_values),
        palette=_coerce_palette(palette_values),
        colormaps=_coerce_role_map(
            colormap_values,
            _REQUIRED_COLORMAP_ROLES,
            "colormaps",
            _coerce_colormap_config,
        ),
        lines=_coerce_role_map(
            line_values,
            _REQUIRED_LINE_ROLES,
            "lines",
            _coerce_line_config,
        ),
        overlays=_coerce_role_map(
            overlay_values,
            _REQUIRED_OVERLAY_ROLES,
            "overlays",
            _coerce_overlay_config,
        ),
        figures=_coerce_role_map(
            figure_values,
            _REQUIRED_FIGURE_ROLES,
            "figures",
            _coerce_figure_config,
        ),
    )


def font_size(role: str) -> float:
    """
    返回指定字体角色的字号
    """
    if role not in FontConfig.__dataclass_fields__:
        message = f"Unknown font role: {role}"
        raise KeyError(message)
    return float(getattr(load_style_config().font, role))


def palette_color(role: str) -> str:
    """
    返回指定调色板角色的颜色值
    """
    if role.startswith("#"):
        return role
    palette = load_style_config().palette
    if role not in palette:
        message = f"Unknown palette role: {role}"
        raise KeyError(message)
    return palette[role]


def line_style(role: str) -> LineConfig:
    """
    返回指定线条角色的样式配置
    """
    lines = load_style_config().lines
    if role not in lines:
        message = f"Unknown line role: {role}"
        raise KeyError(message)
    return lines[role]


def overlay_style(role: str) -> OverlayConfig:
    """
    返回指定叠加层角色的样式配置
    """
    overlays = load_style_config().overlays
    if role not in overlays:
        message = f"Unknown overlay role: {role}"
        raise KeyError(message)
    return overlays[role]


def figure_style(role: str) -> FigureConfig:
    """
    返回指定图像角色的布局配置
    """
    figures = load_style_config().figures
    if role not in figures:
        message = f"Unknown figure role: {role}"
        raise KeyError(message)
    return figures[role]


def make_colormap(role: str) -> object:
    """
    返回指定颜色映射角色的 Matplotlib colormap
    """
    colormaps = load_style_config().colormaps
    if role not in colormaps:
        message = f"Unknown colormap role: {role}"
        raise KeyError(message)
    config = colormaps[role]
    if not config.colors:
        return plt.get_cmap(config.name)
    return matplotlib.colors.LinearSegmentedColormap.from_list(
        config.name,
        [palette_color(color_role) for color_role in config.colors],
    )


def _style_axis(
    axis: object,
    *,
    uses_existing_annotation_colors: bool,
    uses_existing_annotation_font_sizes: bool,
) -> None:
    axis.set_facecolor(palette_color("panel_bg"))
    axis.title.set_color(palette_color("paper_text"))
    axis.title.set_fontsize(font_size("axis_title"))
    axis.xaxis.label.set_color(palette_color("paper_text"))
    axis.xaxis.label.set_fontsize(font_size("axis_label"))
    axis.yaxis.label.set_color(palette_color("paper_text"))
    axis.yaxis.label.set_fontsize(font_size("axis_label"))
    axis.tick_params(
        colors=palette_color("paper_text"),
        labelsize=font_size("tick_label"),
    )
    spine_style = line_style("axis_spine")
    for spine in axis.spines.values():
        spine.set_color(palette_color("grid"))
        spine.set_linewidth(spine_style.width)
    grid_style = line_style("grid")
    for gridline in [*axis.get_xgridlines(), *axis.get_ygridlines()]:
        gridline.set_color(palette_color("grid"))
        gridline.set_alpha(grid_style.alpha)
        gridline.set_linewidth(grid_style.width)
    for text in axis.texts:
        if not uses_existing_annotation_font_sizes:
            text.set_fontsize(font_size("annotation"))
        if (
            not uses_existing_annotation_colors
            and text.get_color() != palette_color("panel_bg")
        ):
            text.set_color(palette_color("paper_text"))
    legend = axis.get_legend()
    if legend is not None:
        legend.get_frame().set_edgecolor(palette_color("grid"))
        legend.get_frame().set_facecolor(palette_color("panel_bg"))
        for text in legend.get_texts():
            text.set_color(palette_color("paper_text"))
            text.set_fontsize(font_size("legend"))


def style_report_axis(
    axis: object,
    *,
    grid_axis: str = "y",
    is_grid_enabled: bool = True,
) -> None:
    """
    报告坐标轴样式
    """
    _style_axis(
        axis,
        uses_existing_annotation_colors=True,
        uses_existing_annotation_font_sizes=True,
    )
    grid_style = line_style("grid")
    if not is_grid_enabled:
        axis.grid(False, axis=grid_axis)
        return
    axis.grid(
        True,
        axis=grid_axis,
        linewidth=grid_style.width,
        alpha=grid_style.alpha,
        color=palette_color("grid"),
    )


def style_optical_axis(axis: object) -> None:
    """
    光学坐标轴样式
    """
    axis.set_facecolor(palette_color("intensity_low"))
    axis.title.set_color(palette_color("intensity_high"))
    axis.title.set_fontsize(font_size("axis_title"))
    axis.xaxis.label.set_color(palette_color("intensity_high"))
    axis.yaxis.label.set_color(palette_color("intensity_high"))
    axis.set_xticks([])
    axis.set_yticks([])
    axis.tick_params(
        left=False,
        bottom=False,
        labelleft=False,
        labelbottom=False,
        colors=palette_color("intensity_high"),
    )
    for spine in axis.spines.values():
        spine.set_visible(False)
    for text in axis.texts:
        text.set_color(palette_color("intensity_high"))
        text.set_fontsize(font_size("annotation"))


def style_classification_colorbar(colorbar: object) -> None:
    """
    分类色条样式
    """
    colorbar.ax.tick_params(
        colors=palette_color("paper_text"),
        labelsize=font_size("tick_label"),
    )
    colorbar.ax.yaxis.label.set_color(palette_color("paper_text"))
    colorbar.ax.yaxis.label.set_fontsize(font_size("axis_label"))
    spine_style = line_style("axis_spine")
    if hasattr(colorbar, "outline"):
        colorbar.outline.set_edgecolor(palette_color("grid"))
        colorbar.outline.set_linewidth(spine_style.width)
    for spine in colorbar.ax.spines.values():
        spine.set_color(palette_color("grid"))
        spine.set_linewidth(spine_style.width)


_style_classification_colorbar = style_classification_colorbar


def _apply_classification_figure_style(fig: object) -> None:
    fig.patch.set_facecolor(load_style_config().export.facecolor)
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None:
        suptitle.set_color(palette_color("paper_text"))
        suptitle.set_fontsize(font_size("figure_title"))
    for axis in fig.axes:
        _style_axis(
            axis,
            uses_existing_annotation_colors=True,
            uses_existing_annotation_font_sizes=True,
        )


def save_classification_figure(
    fig: object,
    output_path: str | Path,
    *,
    style_applier: Callable[[object], None] | None = None,
) -> Path:
    """
    保存单一分类图并返回输出路径
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    export = load_style_config().export
    applier = (
        _apply_classification_figure_style
        if style_applier is None
        else style_applier
    )
    try:
        applier(fig)
        fig.savefig(
            path,
            dpi=export.dpi,
            bbox_inches=export.bbox_inches,
            facecolor=export.facecolor,
        )
    finally:
        plt.close(fig)
    return path


def save_classification_figure_pair(
    fig: object,
    output_base: str | Path,
    *,
    style_applier: Callable[[object], None] | None = None,
    bbox_inches: str | None | object = _DEFAULT_BBOX_INCHES,
) -> dict[str, str]:
    """
    保存分类图的 PNG/SVG 配对并返回路径映射
    """
    base_path = Path(output_base)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    export = load_style_config().export
    outputs: dict[str, str] = {}
    applier = (
        _apply_classification_figure_style
        if style_applier is None
        else style_applier
    )
    resolved_bbox_inches = (
        export.bbox_inches if bbox_inches is _DEFAULT_BBOX_INCHES else bbox_inches
    )
    try:
        applier(fig)
        for export_format in export.formats:
            output_path = base_path.with_suffix(f".{export_format}")
            fig.savefig(
                output_path,
                dpi=export.dpi,
                bbox_inches=resolved_bbox_inches,
                facecolor=export.facecolor,
            )
            outputs[export_format] = str(output_path)
    finally:
        plt.close(fig)
    return outputs


def _save_figure_pair(
    fig: object,
    output_base: str | Path,
    *,
    bbox_inches: str | None | object = _DEFAULT_BBOX_INCHES,
) -> dict[str, str]:
    return save_classification_figure_pair(
        fig,
        output_base,
        bbox_inches=bbox_inches,
    )


def _center_suptitle_over_axes(fig: object, axes: Sequence[object]) -> None:
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is None or not axes:
        return
    x0 = min(axis.get_position().x0 for axis in axes)
    x1 = max(axis.get_position().x1 for axis in axes)
    suptitle.set_x((x0 + x1) / 2.0)


def _as_float(value: object) -> float:
    if isinstance(value, torch.Tensor):
        return float(value.detach().cpu().item())
    return float(value)


def _to_numpy_2d(tensor: object) -> object:
    if isinstance(tensor, torch.Tensor):
        array = tensor.detach().cpu()
        if array.ndim == 3 and array.shape[0] == 1:
            array = array.squeeze(0)
        return array.numpy()
    return np.asarray(tensor)


def _set_empty_axis(axis: object, message: str) -> None:
    axis.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        transform=axis.transAxes,
        color=palette_color("paper_text"),
    )
    axis.set_xticks([])
    axis.set_yticks([])


def _classification_matrix_cmap() -> object:
    return make_colormap("confusion_matrix")


def _style_classification_axis(
    axis: object,
    *,
    is_grid_enabled: bool = True,
    grid_axis: str = "y",
) -> None:
    style_report_axis(
        axis,
        grid_axis=grid_axis,
        is_grid_enabled=is_grid_enabled,
    )


def _matrix_annotation_color(value: float) -> str:
    red, green, blue, _ = _classification_matrix_cmap()(float(np.clip(value, 0.0, 1.0)))
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    if luminance < 0.70:
        return "#ffffff"
    return palette_color("paper_text")


def _annotate_matrix(
    axis: object,
    values: object,
    color_values: object,
    *,
    value_format: str,
    minimum_value: float = 0.0,
) -> None:
    value_array = np.asarray(values)
    color_array = np.asarray(color_values, dtype=np.float32)
    if value_array.size == 0:
        return
    for row_index in range(value_array.shape[0]):
        for column_index in range(value_array.shape[1]):
            value = float(value_array[row_index, column_index])
            if value <= minimum_value:
                continue
            label = value_format.format(value)
            axis.text(
                column_index,
                row_index,
                label,
                ha="center",
                va="center",
                fontsize=font_size("matrix_cell"),
                color=_matrix_annotation_color(float(color_array[row_index, column_index])),
            )


def _draw_detector_regions(axis: object, example: Mapping[str, object]) -> None:
    overlay = overlay_style("detector_region")
    for region in example.get("detector_regions", []):
        x0, x1, y0, y1 = [int(value) for value in region]
        axis.add_patch(
            Rectangle(
                (x0 - 0.5, y0 - 0.5),
                x1 - x0,
                y1 - y0,
                fill=False,
                edgecolor=palette_color(overlay.color),
                linewidth=overlay.linewidth,
                linestyle=overlay.linestyle,
                alpha=overlay.alpha,
            )
        )


def _format_readout_evidence(example: Mapping[str, object]) -> str:
    detector_fraction = example.get("detector_total_energy_fraction")
    target_fraction = example.get("target_detector_energy_fraction")
    peak_target = example.get("is_peak_in_target_detector")
    if detector_fraction is None or target_fraction is None:
        return ""
    if peak_target is True:
        peak_text = "yes"
    elif peak_target is False:
        peak_text = "no"
    else:
        peak_text = "unknown"
    return (
        f"Detector energy: {float(detector_fraction):.3f}\n"
        f"Target share: {float(target_fraction):.3f}\n"
        f"Peak in target: {peak_text}"
    )


def _masked_detector_intensity(
    intensity_map: object,
    example: Mapping[str, object],
) -> object:
    intensity = np.asarray(_to_numpy_2d(intensity_map), dtype=np.float32)
    masked = np.zeros_like(intensity, dtype=np.float32)
    for region in example.get("detector_regions", []):
        x0, x1, y0, y1 = [int(value) for value in region]
        masked[y0:y1, x0:x1] = intensity[y0:y1, x0:x1]
    max_value = float(masked.max()) if masked.size else 0.0
    if max_value > 0.0:
        masked = masked / max_value
    return masked


def _normalize_detector_distribution(distribution: object) -> object:
    if isinstance(distribution, torch.Tensor):
        values = distribution.detach().cpu().to(torch.float32).numpy()
    else:
        values = np.asarray(distribution, dtype=np.float32)
    max_value = float(values.max()) if values.size else 0.0
    if max_value > 0.0:
        return values / max_value
    return np.zeros_like(values, dtype=np.float32)


def _history_value(history: dict[str, list[float]], key: str, index: int) -> float:
    values = history.get(key, [])
    if index >= len(values):
        return 0.0
    return float(values[index])


def _display_topology_label(topology: object) -> str:
    label = str(topology).replace("_", " ").strip()
    return label.capitalize() if label else ""


def visualize_training_dynamics(
    history_rows: Sequence[Mapping[str, object]],
    output_base: str | Path,
    *,
    best_epoch: int | None = None,
) -> dict[str, str]:
    """
    保存编号训练动态图
    """
    epochs = [int(row["epoch"]) for row in history_rows]
    train_loss = [_as_float(row["train_loss"]) for row in history_rows]
    val_loss = [_as_float(row["val_loss"]) for row in history_rows]
    train_accuracy = [_as_float(row["train_accuracy"]) for row in history_rows]
    val_accuracy = [_as_float(row["val_accuracy"]) for row in history_rows]

    style = figure_style("training_dynamics")
    fig, (loss_axis, accuracy_axis) = plt.subplots(1, 2, figsize=style.figsize)
    training_line = line_style("training_curve")
    best_line = line_style("best_epoch")
    if epochs:
        loss_axis.plot(
            epochs,
            train_loss,
            label="Train",
            linewidth=training_line.width,
            color=palette_color("train_line"),
        )
        loss_axis.plot(
            epochs,
            val_loss,
            label="Validation",
            linewidth=training_line.width,
            color=palette_color("validation_line"),
        )
        accuracy_axis.plot(
            epochs,
            train_accuracy,
            label="Train",
            linewidth=training_line.width,
            color=palette_color("train_line"),
        )
        accuracy_axis.plot(
            epochs,
            val_accuracy,
            label="Validation",
            linewidth=training_line.width,
            color=palette_color("validation_line"),
        )
        if best_epoch is not None:
            for axis in (loss_axis, accuracy_axis):
                axis.axvline(
                    best_epoch,
                    color=palette_color("muted_text"),
                    linestyle=best_line.linestyle,
                    linewidth=best_line.width,
                )
        if style.uses_gap_annotation:
            gap = train_accuracy[-1] - val_accuracy[-1]
            accuracy_axis.text(
                0.02,
                0.04,
                f"Gap: {gap:+.3f}",
                transform=accuracy_axis.transAxes,
                color=palette_color("paper_text"),
            )
    loss_axis.set_xlabel("Epoch")
    loss_axis.set_ylabel("Loss")
    _style_classification_axis(loss_axis)

    accuracy_axis.set_xlabel("Epoch")
    accuracy_axis.set_ylabel("Accuracy")
    if style.accuracy_ymin is not None:
        accuracy_axis.set_ylim(style.accuracy_ymin, 1.0)
    else:
        accuracy_axis.set_ylim(0.0, 1.0)
    _style_classification_axis(accuracy_axis)
    handles, labels = loss_axis.get_legend_handles_labels()
    if handles:
        legend = fig.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.88),
            ncol=style.legend_columns,
            frameon=False,
        )
        for text in legend.get_texts():
            text.set_color(palette_color("paper_text"))
            text.set_fontsize(font_size("legend"))
    fig.suptitle(style.title)
    fig.subplots_adjust(
        left=0.09,
        right=0.98,
        bottom=0.16,
        top=0.78,
        wspace=0.26,
    )
    return _save_figure_pair(fig, output_base)


def visualize_training_curves(
    history_rows: Sequence[Mapping[str, object]],
    output_base: str | Path,
) -> dict[str, str]:
    """
    保存训练 loss 与 accuracy 曲线
    """
    return visualize_training_dynamics(history_rows, output_base)


_READOUT_PAGE_DEFINITIONS = (
    ("upper", range(0, 5), "Digits 0-4"),
    ("lower", range(5, 10), "Digits 5-9"),
)


def _page_output_base(output_base: str | Path, page_name: str) -> Path:
    base_path = Path(output_base)
    return base_path.with_name(f"{base_path.name}_{page_name}")


def _readout_page_rows(
    example_rows: Sequence[Mapping[str, object]],
    labels: range,
) -> list[Mapping[str, object]]:
    label_set = set(labels)
    return [
        example
        for example in example_rows
        if int(example.get("true_label", -1)) in label_set
    ]


def _remove_legacy_readout_pair(output_base: str | Path) -> None:
    base_path = Path(output_base)
    for suffix in (".png", ".svg"):
        legacy_path = base_path.with_suffix(suffix)
        if legacy_path.exists():
            legacy_path.unlink()


def _visualize_optical_readout_page(
    example_rows: Sequence[Mapping[str, object]],
    output_base: str | Path,
    *,
    page_title: str,
    style: FigureConfig,
) -> dict[str, str]:
    row_count = max(len(example_rows), 1)
    base_width, base_height = style.figsize
    fig = plt.figure(
        figsize=(base_width, max(base_height, style.row_height * row_count + 0.8))
    )
    grid_column_count = 4
    data_column_indices = tuple(range(4))
    width_ratios = style.column_width_ratios
    if style.detector_column_gap > 0.0:
        width_ratios = (
            style.column_width_ratios[0],
            style.column_width_ratios[1],
            style.column_width_ratios[2],
            style.detector_column_gap,
            style.column_width_ratios[3],
        )
        grid_column_count = 5
        data_column_indices = (0, 1, 2, 4)
    grid_kwargs: dict[str, object] = {
        "figure": fig,
        "width_ratios": width_ratios,
    }
    if style.column_wspace is not None:
        grid_kwargs["wspace"] = style.column_wspace
    if style.row_hspace is not None:
        grid_kwargs["hspace"] = style.row_hspace
    if style.grid_left is not None:
        grid_kwargs["left"] = style.grid_left
    if style.grid_right is not None:
        grid_kwargs["right"] = style.grid_right
    if style.grid_top is not None:
        grid_kwargs["top"] = style.grid_top
    if style.grid_bottom is not None:
        grid_kwargs["bottom"] = style.grid_bottom
    grid = GridSpec(
        row_count,
        grid_column_count,
        **grid_kwargs,
    )
    axes = np.asarray(
        [
            [
                fig.add_subplot(grid[row_index, column_index])
                for column_index in data_column_indices
            ]
            for row_index in range(row_count)
        ],
        dtype=object,
    )
    column_titles = (
        "Input image",
        "Input field magnitude",
        "Output intensity",
        "Detector distribution",
    )
    for axis, title in zip(axes[0], column_titles, strict=True):
        axis.set_title(title)
    if not example_rows:
        for axis in axes[0]:
            axis.axis("off")
        axes[0, 1].text(
            0.5,
            0.5,
            "No examples available",
            ha="center",
            va="center",
            transform=axes[0, 1].transAxes,
        )
    for row_index, example in enumerate(example_rows):
        image_panels = (
            _to_numpy_2d(example["input_image"]),
            _to_numpy_2d(example["input_field_magnitude"]),
            _masked_detector_intensity(example["intensity_map"], example),
        )
        intensity_cmap = make_colormap("intensity")
        for axis, image in zip(axes[row_index, :3], image_panels, strict=True):
            axis.imshow(
                image,
                cmap=intensity_cmap,
                vmin=0.0,
                vmax=1.0,
                aspect="equal",
            )
            axis.set_box_aspect(1.0)
            axis.axis("off")
        output_axis = axes[row_index, 2]
        _draw_detector_regions(output_axis, example)
        distribution_values = _normalize_detector_distribution(
            example["detector_distribution"]
        )
        if distribution_values.size:
            axes[row_index, 3].bar(
                range(len(distribution_values)),
                distribution_values,
                color=palette_color("energy_high"),
                edgecolor=palette_color("report_bar_edge"),
                linewidth=line_style("bar_edge").width,
            )
            axes[row_index, 3].set_ylim(0.0, 1.1)
            axes[row_index, 3].set_xticks(range(len(distribution_values)))
        else:
            _set_empty_axis(axes[row_index, 3], "No detector data")
            axes[row_index, 3].set_ylim(0.0, 1.0)
        if style.uses_detector_xlabel:
            axes[row_index, 3].set_xlabel("Class")
        _style_classification_axis(axes[row_index, 3])
        axes[row_index, 0].set_ylabel(
            f"True {example['true_label']} / Pred {example['predicted_label']}",
            rotation=90,
            labelpad=8,
        )
    fig.suptitle(f"{style.title} ({page_title})")
    return _save_figure_pair(fig, output_base, bbox_inches=style.bbox_inches)


def visualize_optical_readout_examples(
    example_rows: Sequence[Mapping[str, object]],
    output_base: str | Path,
) -> dict[str, str]:
    """
    保存分类光学读出示例分页图
    """
    style = figure_style("optical_readout_examples")
    _remove_legacy_readout_pair(output_base)
    outputs: dict[str, str] = {}
    for page_name, labels, page_title in _READOUT_PAGE_DEFINITIONS:
        page_outputs = _visualize_optical_readout_page(
            _readout_page_rows(example_rows, labels),
            _page_output_base(output_base, page_name),
            page_title=page_title,
            style=style,
        )
        for export_format, output_path in page_outputs.items():
            outputs[f"{page_name}_{export_format}"] = output_path
    return outputs


def visualize_topology_comparison(
    topology_rows: Sequence[Mapping[str, object]],
    output_base: str | Path,
) -> dict[str, str]:
    """
    保存编号拓扑对比图
    """
    labels = [_display_topology_label(row["topology"]) for row in topology_rows]
    evaluation = [
        np.nan if row.get("evaluation_accuracy") is None else float(row["evaluation_accuracy"])
        for row in topology_rows
    ]
    best_validation = [
        np.nan if row.get("best_val_accuracy") is None else float(row["best_val_accuracy"])
        for row in topology_rows
    ]
    mean_seconds = [
        np.nan if row.get("mean_epoch_seconds") is None else float(row["mean_epoch_seconds"])
        for row in topology_rows
    ]
    positions = np.arange(len(labels), dtype=np.float32)
    style = figure_style("topology_comparison")
    fig, (accuracy_axis, timing_axis) = plt.subplots(1, 2, figsize=style.figsize)
    width = 0.35
    bar_line = line_style("bar_edge")
    accuracy_axis.bar(
        positions - width / 2,
        evaluation,
        width,
        label="Test",
        color=palette_color("report_bar"),
        edgecolor=palette_color("report_bar_edge"),
        linewidth=bar_line.width,
    )
    accuracy_axis.bar(
        positions + width / 2,
        best_validation,
        width,
        label="Best validation",
        color=palette_color("topology_secondary"),
        edgecolor=palette_color("report_bar_edge"),
        linewidth=bar_line.width,
    )
    accuracy_axis.set_xticks(positions)
    accuracy_axis.set_xticklabels(labels)
    accuracy_axis.set_ylim(0.0, 1.0)
    accuracy_axis.set_ylabel("Accuracy")
    accuracy_axis.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.12),
        ncol=2,
        frameon=False,
    )
    _style_classification_axis(accuracy_axis)

    timing_axis.bar(
        positions,
        mean_seconds,
        color=palette_color("timing_bar"),
        edgecolor=palette_color("report_bar_edge"),
        linewidth=bar_line.width,
    )
    timing_axis.set_xticks(positions)
    timing_axis.set_xticklabels(labels)
    timing_axis.set_ylabel("Mean epoch time (s)")
    _style_classification_axis(timing_axis)
    for axis, values in ((accuracy_axis, evaluation), (timing_axis, mean_seconds)):
        for position, value in zip(positions, values, strict=True):
            if np.isnan(value):
                axis.text(
                    position,
                    0.05,
                    "n/a",
                    ha="center",
                    va="bottom",
                    color=palette_color("paper_text"),
                )
    fig.suptitle(style.title)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
    return _save_figure_pair(fig, output_base)


def visualize_confusion_matrix(
    confusion_matrix: Sequence[Sequence[int]],
    output_base: str | Path,
) -> dict[str, str]:
    """
    保存用于诊断分类错误分布的紧凑混淆矩阵图
    """
    style = figure_style("confusion_matrix")
    fig, axis = plt.subplots(figsize=style.figsize)
    matrix = np.asarray(confusion_matrix)
    title_axes = [axis]
    if matrix.size:
        row_count, column_count = matrix.shape
        image = axis.pcolormesh(
            np.arange(column_count + 1) - 0.5,
            np.arange(row_count + 1) - 0.5,
            matrix,
            cmap=_classification_matrix_cmap(),
        )
        axis.set_xlim(-0.5, column_count - 0.5)
        axis.set_ylim(row_count - 0.5, -0.5)
        colorbar = fig.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
        colorbar.set_label("Count")
        _style_classification_colorbar(colorbar)
        axis.set_box_aspect(1.0)
        title_axes.append(colorbar.ax)
    else:
        _set_empty_axis(axis, "No confusion data")
    axis.set_xlabel("Predicted")
    axis.set_ylabel("Actual")
    if matrix.size:
        axis.set_xticks(range(matrix.shape[1]))
        axis.set_yticks(range(matrix.shape[0]))
        max_value = float(np.max(matrix))
        color_values = matrix / max(max_value, 1.0)
        _annotate_matrix(axis, matrix, color_values, value_format="{:.0f}")
    _style_classification_axis(axis, is_grid_enabled=False)
    fig.suptitle(style.title)
    fig.tight_layout()
    fig.canvas.draw()
    _center_suptitle_over_axes(fig, title_axes)
    return _save_figure_pair(fig, output_base)


def visualize_per_class_accuracy(
    per_class_accuracy: Sequence[float],
    output_base: str | Path,
) -> dict[str, str]:
    """
    保存用于诊断类别间性能差异的逐类准确率图
    """
    style = figure_style("per_class_accuracy")
    fig, axis = plt.subplots(figsize=style.figsize)
    accuracy_values = [float(value) for value in per_class_accuracy]
    axis.bar(
        range(len(accuracy_values)),
        accuracy_values,
        color=palette_color("report_bar"),
        edgecolor=palette_color("report_bar_edge"),
        linewidth=line_style("bar_edge").width,
    )
    axis.set_xlabel("Class")
    axis.set_ylabel("Accuracy")
    if style.accuracy_ymin is None or not accuracy_values:
        y_min = 0.0
    else:
        y_min = max(0.0, min(style.accuracy_ymin, min(accuracy_values) - 0.02))
    axis.set_ylim(y_min, 1.0)
    axis.set_xticks(range(len(accuracy_values)))
    _style_classification_axis(axis)
    fig.suptitle(style.title)
    fig.tight_layout()
    return _save_figure_pair(fig, output_base)


def _prepare_png_path(output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def visualize_detector_layout(output_path: str | Path) -> Path:
    """
    保存分类探测器布局图
    """
    from experiments.classification.dataset_adapter import CLASSIFICATION_DETECTOR_REGIONS
    from matplotlib.patches import Rectangle

    path = _prepare_png_path(output_path)
    style = figure_style("detector_layout")
    fig, axis = plt.subplots(figsize=style.figsize)
    axis.imshow(
        torch.zeros((64, 64)).numpy(),
        cmap=make_colormap("intensity"),
        vmin=0.0,
        vmax=1.0,
    )
    overlay = overlay_style("detector_region")
    for x0, x1, y0, y1 in CLASSIFICATION_DETECTOR_REGIONS:
        axis.add_patch(
            Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                fill=False,
                edgecolor=palette_color(overlay.color),
                linewidth=overlay.linewidth,
                linestyle=overlay.linestyle,
                alpha=overlay.alpha,
            )
        )
    axis.set_xlim(0, 64)
    axis.set_ylim(64, 0)
    axis.axis("off")
    fig.tight_layout()
    return save_classification_figure(fig, path)


def visualize_phase_mask(phase_mask: torch.Tensor, output_path: str | Path) -> Path:
    """
    保存相位掩膜图
    """
    path = _prepare_png_path(output_path)
    style = figure_style("phase_mask")
    fig, axis = plt.subplots(figsize=style.figsize)
    image = phase_mask.detach().cpu().numpy()
    axis.imshow(image, cmap=make_colormap("phase"))
    axis.set_title(style.title)
    axis.axis("off")
    fig.tight_layout()
    return save_classification_figure(fig, path)


def visualize_prediction_example(
    input_image: torch.Tensor,
    input_field_magnitude: torch.Tensor,
    intensity_map: torch.Tensor,
    detector_distribution: torch.Tensor,
    output_path: str | Path,
) -> Path:
    """
    保存单样本预测示例图
    """
    path = _prepare_png_path(output_path)
    style = figure_style("prediction_example")
    fig, axes = plt.subplots(1, 4, figsize=style.figsize)
    panels = [input_image, input_field_magnitude, intensity_map]
    intensity_cmap = make_colormap("intensity")
    for axis, tensor in zip(axes[:3], panels, strict=True):
        image = tensor.detach().cpu()
        if image.ndim == 3 and image.shape[0] == 1:
            image = image.squeeze(0)
        axis.imshow(image.numpy(), cmap=intensity_cmap)
        axis.axis("off")
    detector_values = detector_distribution.detach().cpu().numpy()
    max_value = float(np.max(detector_values)) if detector_values.size else 0.0
    if max_value > 0:
        detector_values = detector_values / max_value
    axes[3].bar(
        range(len(detector_values)),
        detector_values,
        color=palette_color("report_bar"),
        edgecolor=palette_color("report_bar_edge"),
        linewidth=line_style("bar_edge").width,
    )
    axes[3].set_xlabel("Detector")
    axes[3].set_ylabel("Score")
    axes[3].set_ylim(0.0, 1.1)
    _style_classification_axis(axes[3])
    fig.suptitle(style.title)
    fig.tight_layout()
    return save_classification_figure(fig, path)


def visualize_training_history(
    history: dict[str, list[float]],
    output_path: Path | str,
) -> Path:
    """
    保存用于诊断训练收敛过程的 loss 与 accuracy 曲线
    """
    epoch_count = max(
        len(history.get("train_loss", [])),
        len(history.get("val_loss", [])),
        len(history.get("train_accuracy", [])),
        len(history.get("val_accuracy", [])),
    )
    rows = []
    for epoch in range(1, epoch_count + 1):
        index = epoch - 1
        rows.append(
            {
                "epoch": epoch,
                "train_loss": _history_value(history, "train_loss", index),
                "val_loss": _history_value(history, "val_loss", index),
                "train_accuracy": _history_value(history, "train_accuracy", index),
                "val_accuracy": _history_value(history, "val_accuracy", index),
            }
        )
    outputs = visualize_training_curves(rows, Path(output_path).with_suffix(""))
    return Path(outputs["png"])

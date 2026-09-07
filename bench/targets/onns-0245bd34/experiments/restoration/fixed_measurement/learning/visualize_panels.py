from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from experiments.figure_style import FigureStyle, style_grid


SaveFigurePair = Callable[[plt.Figure, Path | str, str], dict[str, str]]


def write_bar_figure(
    output_dir: Path | str,
    figure_name: str,
    values: Sequence[float],
    *,
    ylabel: str,
    figure_text_spec: Mapping[str, Mapping[str, str]],
    palette: Mapping[str, str],
    save_figure_pair: SaveFigurePair,
) -> dict[str, str]:
    """
    写入基础柱状面板
    """
    fig, axis = plt.subplots(figsize=(6, 4), constrained_layout=True)
    x_values = np.arange(len(values))
    axis.bar(x_values, values, color=palette["primary_fill"])
    axis.set_title(figure_text_spec[figure_name]["title"])
    axis.set_xlabel("Measurement")
    axis.set_ylabel(ylabel)
    return save_figure_pair(fig, output_dir, figure_name)


def write_edge_mtf_figure(
    output_dir: Path | str,
    figure_name: str,
    metric_rows: Sequence[Mapping[str, object]],
    *,
    curve_rows: Sequence[Mapping[str, object]] | None = None,
    figure_text_spec: Mapping[str, Mapping[str, str]],
    palette: Mapping[str, str],
    restoration_style: FigureStyle,
    title_case: Callable[[object], str],
    finite_float: Callable[[object], float | None],
    edge_mtf_curve_series: Callable[
        [Sequence[Mapping[str, object]]],
        list[tuple[str, list[tuple[float, float]]]],
    ],
    write_labeled_bar_figure: Callable[
        [Path | str, str, Sequence[tuple[str, float]]],
        dict[str, str],
    ],
    save_figure_pair: SaveFigurePair,
) -> dict[str, str]:
    """
    写入边缘调制传递函数面板
    """
    curve_series = edge_mtf_curve_series(curve_rows or [])
    if curve_series:
        fig, axis = plt.subplots(figsize=(6, 4), constrained_layout=True)
        colors = (
            palette["primary"],
            palette["secondary"],
            palette["accent"],
            palette["violet"],
        )
        for index, (baseline_name, points) in enumerate(curve_series):
            marker_step = max(1, len(points) // 14)
            axis.plot(
                [point[0] for point in points],
                [point[1] for point in points],
                marker="o",
                markersize=3.0,
                markevery=marker_step,
                linewidth=1.2,
                label=title_case(baseline_name),
                color=colors[index % len(colors)],
            )
        axis.set_title(figure_text_spec[figure_name]["title"])
        axis.set_xlabel("Spatial Frequency (cycles per pixel)")
        axis.set_ylabel("Intensity MTF")
        axis.set_xlim(left=0.0)
        axis.set_ylim(0.0, 1.05)
        style_grid(axis, restoration_style, alpha=restoration_style.subtle_grid_alpha)
        axis.axhline(
            0.5,
            color=palette["accent"],
            linestyle="--",
            linewidth=restoration_style.spine_linewidth,
        )
        axis.axhline(
            0.1,
            color=palette["neutral"],
            linestyle="--",
            linewidth=restoration_style.spine_linewidth,
        )
        axis.axvline(
            0.5,
            color=palette["neutral"],
            linestyle=":",
            linewidth=restoration_style.spine_linewidth,
        )
        axis.legend()
        return save_figure_pair(fig, output_dir, figure_name)

    metrics = (
        ("edge_mtf50_cycles_per_pixel", "MTF50"),
        ("edge_mtf10_cycles_per_pixel", "MTF10"),
        ("edge_nyquist_response", "Nyquist"),
        ("edge_mtf_auc", "AUC"),
    )
    values: list[tuple[str, float]] = []
    for metric_name, label in metrics:
        for row in metric_rows:
            if row.get("metric_name") != metric_name:
                continue
            if row.get("baseline_name") != "full_frontend_phase_zero":
                continue
            value = finite_float(row.get("metric_value"))
            if value is not None:
                values.append((label, value))
                break
    if not values:
        values = [("MTF50", 0.0), ("MTF10", 0.0), ("Nyquist", 0.0), ("AUC", 0.0)]
    return write_labeled_bar_figure(
        output_dir,
        figure_name,
        values,
        ylabel="Cycles per pixel / ratio",
    )


def write_grating_ctf_figure(
    output_dir: Path | str,
    figure_name: str,
    metric_rows: Sequence[Mapping[str, object]],
    *,
    figure_text_spec: Mapping[str, Mapping[str, str]],
    palette: Mapping[str, str],
    restoration_style: FigureStyle,
    save_figure_pair: SaveFigurePair,
) -> dict[str, str]:
    """
    写入光栅对比度传递函数面板
    """
    points = [
        (float(row["spatial_frequency"]), float(row["metric_value"]))
        for row in metric_rows
        if row.get("target_name") == "sinusoidal_gratings"
        and row.get("metric_name") == "grating_ctf"
        and row.get("baseline_name") == "full_frontend_phase_zero"
    ]
    points.sort(key=lambda point: point[0])
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]

    fig, axis = plt.subplots(figsize=(6, 4), constrained_layout=True)
    if points:
        axis.plot(
            x_values,
            y_values,
            marker="o",
            markersize=3.2,
            linewidth=1.1,
            color=palette["primary"],
        )
        axis.axhline(
            1.0,
            color=palette["neutral"],
            linestyle="--",
            linewidth=restoration_style.spine_linewidth,
        )
    else:
        axis.text(
            0.5,
            0.5,
            "No CTF data",
            ha="center",
            va="center",
            transform=axis.transAxes,
            color=palette["neutral"],
        )
    axis.axvline(
        0.5,
        color=palette["neutral"],
        linestyle=":",
        linewidth=restoration_style.spine_linewidth,
    )
    axis.set_title(figure_text_spec[figure_name]["title"])
    axis.set_xlabel("Spatial Frequency (cycles per pixel)")
    axis.set_ylabel("Contrast Transfer")
    if points and min(y_values) > 0.9:
        axis.set_ylim(max(0.0, min(y_values) - 0.025), 1.01)
    else:
        axis.set_ylim(0.0, 1.05)
    style_grid(axis, restoration_style, alpha=restoration_style.subtle_grid_alpha)
    return save_figure_pair(fig, output_dir, figure_name)


def write_point_response_figure(
    output_dir: Path | str,
    figure_name: str,
    metric_rows: Sequence[Mapping[str, object]],
    *,
    first_metric_value: Callable[[Sequence[Mapping[str, object]], str], float | None],
    write_labeled_bar_figure: Callable[
        [Path | str, str, Sequence[tuple[str, float]]],
        dict[str, str],
    ],
) -> dict[str, str]:
    """
    写入点响应面板
    """
    values = [
        ("FWHM", first_metric_value(metric_rows, "point_response_fwhm")),
        (
            "Peak Sidelobe",
            first_metric_value(metric_rows, "point_response_peak_sidelobe_ratio"),
        ),
    ]
    return write_labeled_bar_figure(
        output_dir,
        figure_name,
        [(label, value if value is not None else 0.0) for label, value in values],
        ylabel="Pixels / ratio",
    )


def write_labeled_bar_figure(
    output_dir: Path | str,
    figure_name: str,
    values: Sequence[tuple[str, float]],
    *,
    ylabel: str,
    figure_text_spec: Mapping[str, Mapping[str, str]],
    palette: Mapping[str, str],
    save_figure_pair: SaveFigurePair,
) -> dict[str, str]:
    """
    写入带标签柱状面板
    """
    fig, axis = plt.subplots(figsize=(6, 4), constrained_layout=True)
    x_values = np.arange(len(values))
    axis.bar(
        x_values,
        [value for _label, value in values],
        color=palette["primary_fill"],
    )
    axis.set_xticks(
        x_values,
        labels=[label for label, _value in values],
        rotation=20,
        ha="right",
    )
    axis.set_title(figure_text_spec[figure_name]["title"])
    axis.set_xlabel("Measurement")
    axis.set_ylabel(ylabel)
    return save_figure_pair(fig, output_dir, figure_name)


def write_check_figure(
    output_dir: Path | str,
    figure_name: str,
    checks: Sequence[Mapping[str, object]],
    *,
    figure_text_spec: Mapping[str, Mapping[str, str]],
    palette: Mapping[str, str],
    title_case: Callable[[object], str],
    save_figure_pair: SaveFigurePair,
) -> dict[str, str]:
    """
    写入检查状态面板
    """
    names = [title_case(check.get("name", "check")) for check in checks[:10]] or [
        "Checks"
    ]
    statuses = [
        1.0 if check.get("status") == "PASS" else 0.0 for check in checks[:10]
    ] or [0.0]
    fig, axis = plt.subplots(figsize=(8, 4), constrained_layout=True)
    y_values = np.arange(len(names))
    axis.barh(y_values, statuses, color=palette["secondary"])
    axis.set_yticks(y_values, labels=names)
    axis.set_xlim(0.0, 1.0)
    axis.set_xlabel("Pass")
    axis.set_title(figure_text_spec[figure_name]["title"])
    return save_figure_pair(fig, output_dir, figure_name)

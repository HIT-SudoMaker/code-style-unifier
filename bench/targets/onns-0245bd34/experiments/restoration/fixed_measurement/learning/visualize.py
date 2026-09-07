from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from experiments.figure_style import (
    AnnotationPolicy,
    FigureStyle,
    STANDARD_FIGURE_DPI,
    apply_figure_style,
    save_named_figure_pair,
    style_grid,
)
from experiments.restoration.fixed_measurement.learning import visualize_panels


FIGURE_TEXT_SPEC = {
    "01_resolution_budget": {"title": "Resolution Budget"},
    "02_point_response": {"title": "Point Response"},
    "03_edge_derived_intensity_mtf": {"title": "Edge Derived Intensity MTF"},
    "04_grating_ctf": {"title": "Grating CTF"},
    "05_usaf_resolution": {"title": "USAF Resolution"},
    "06_siemens_star_diagnostic": {"title": "Siemens Star Diagnostic"},
    "07_phase_offset_sensitivity": {"title": "Phase Offset Sensitivity"},
    "08_operating_point_summary": {"title": "Operating Point Summary"},
    "01_training_dynamics": {"title": "Training Dynamics"},
    "02_restoration_examples": {"title": "Restoration Examples"},
    "03_phase_mask_evolution": {"title": "Phase Mask Evolution"},
    "04_frequency_response_comparison": {"title": "Frequency Response Comparison"},
    "05_operating_point_trace": {"title": "Operating Point Trace"},
    "01_method_comparison": {"title": "Method Comparison"},
}


_RESTORATION_PALETTE = {
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
_RESTORATION_STYLE = FigureStyle(
    text_color=_RESTORATION_PALETTE["dark_text"],
    muted_text_color=_RESTORATION_PALETTE["muted_text"],
    grid_color=_RESTORATION_PALETTE["neutral"],
    panel_facecolor=_RESTORATION_PALETTE["panel_bg"],
    dpi=STANDARD_FIGURE_DPI,
)

_PANEL_WRITERS = {
    "bar": visualize_panels.write_bar_figure,
    "edge_mtf": visualize_panels.write_edge_mtf_figure,
    "grating_ctf": visualize_panels.write_grating_ctf_figure,
    "point_response": visualize_panels.write_point_response_figure,
    "labeled_bar": visualize_panels.write_labeled_bar_figure,
    "check": visualize_panels.write_check_figure,
}
_IMAGE_2D_REQUIRED = "image must be reducible to a 2D array"


def _title_case(value: object) -> str:
    return str(value).replace("_", " ").title()


def _to_numpy(image: object) -> np.ndarray:
    detach = getattr(image, "detach", None)
    if callable(detach):
        array = detach().cpu().numpy()
    else:
        array = np.asarray(image)
    if np.iscomplexobj(array):
        array = np.abs(array)
    while array.ndim > 2:
        array = array[0]
    if array.ndim != 2:
        raise ValueError(_IMAGE_2D_REQUIRED)
    return np.asarray(array, dtype=np.float32)


def _center_crop(image: np.ndarray, crop_size: int = 64) -> np.ndarray:
    height, width = image.shape
    resolved_size = min(crop_size, height, width)
    start_y = max(0, (height - resolved_size) // 2)
    start_x = max(0, (width - resolved_size) // 2)
    return image[start_y:start_y + resolved_size, start_x:start_x + resolved_size]


def _normalize_display_image(image: np.ndarray) -> np.ndarray:
    finite_values = image[np.isfinite(image)]
    if finite_values.size == 0:
        return np.zeros_like(image)
    minimum = float(np.min(finite_values))
    maximum = float(np.max(finite_values))
    if maximum <= minimum:
        return np.zeros_like(image)
    return (image - minimum) / (maximum - minimum)


def _normalize_signed_display_image(image: np.ndarray) -> np.ndarray:
    finite_values = image[np.isfinite(image)]
    if finite_values.size == 0:
        return np.zeros_like(image)
    limit = float(np.max(np.abs(finite_values)))
    if limit <= 0.0:
        return np.zeros_like(image)
    return image / limit


def _finite_float(value: object) -> float | None:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric_value):
        return None
    return numeric_value


def _cycles_per_meter_to_cycles_per_mm(value: float) -> float:
    return value * 1e-3


def _first_available_float(
    values: Mapping[str, object],
    keys: Sequence[str],
) -> float | None:
    for key in keys:
        value = _finite_float(values.get(key))
        if value is not None:
            return value
    return None


def _phase_tick_label(value: float) -> str:
    normalized = value % (2.0 * math.pi)
    if abs(normalized) < 1e-6 or abs(normalized - 2.0 * math.pi) < 1e-6:
        return "0"
    candidates = (
        (0.0, "0"),
        (0.5 * math.pi, "pi/2"),
        (math.pi, "pi"),
        (1.5 * math.pi, "3pi/2"),
    )
    for candidate, label in candidates:
        if abs(normalized - candidate) < 1e-6:
            return label
    return f"{normalized / math.pi:.2g}pi"


def _save_figure_pair(fig: plt.Figure, output_dir: Path | str, name: str) -> dict[str, str]:
    return save_named_figure_pair(
        fig,
        output_dir,
        name,
        _RESTORATION_STYLE,
    )


def _apply_restoration_figure_style(fig: plt.Figure) -> None:
    apply_figure_style(
        fig,
        _RESTORATION_STYLE,
        annotation_policy=AnnotationPolicy.PRESERVE_COLORS,
    )


def visualize_benchmark_method_comparison(
    baseline_rows: Sequence[Mapping[str, object]],
    output_dir: Path | str,
    figure_name: str = "01_method_comparison",
) -> dict[str, str]:
    """
    绘制 benchmark 方法 PSNR 对比图
    """
    rows = [
        row
        for row in baseline_rows
        if row.get("metric_name") == "psnr"
        and _finite_float(row.get("mean_value")) is not None
    ]

    fig, axis = plt.subplots(figsize=(6.4, 3.4), constrained_layout=True)
    if rows:
        labels = [_benchmark_method_label(row) for row in rows]
        values = [
            float(_finite_float(row.get("mean_value")) or 0.0)
            for row in rows
        ]
        x_values = np.arange(len(values))
        axis.bar(
            x_values,
            values,
            color=_RESTORATION_PALETTE["primary_fill"],
            edgecolor=_RESTORATION_PALETTE["primary"],
            linewidth=_RESTORATION_STYLE.spine_linewidth,
            width=0.68,
        )
        axis.set_xticks(x_values, labels=labels, rotation=20, ha="right")
        axis.set_ylabel("PSNR vs clean (dB)")
        style_grid(
            axis,
            _RESTORATION_STYLE,
            grid_axis="y",
            alpha=_RESTORATION_STYLE.subtle_grid_alpha,
        )
    else:
        axis.text(
            0.5,
            0.5,
            "No finite PSNR data",
            ha="center",
            va="center",
            transform=axis.transAxes,
        )
        axis.set_xticks([])
        axis.set_ylabel("PSNR vs clean (dB)")
    axis.set_title(FIGURE_TEXT_SPEC[figure_name]["title"])
    return _save_figure_pair(fig, output_dir, figure_name)


def _benchmark_method_label(row: Mapping[str, object]) -> str:
    label = _title_case(row.get("method_name", "method"))
    gate_state = str(row.get("optical_residual_gate_state", ""))
    gate_labels = {
        "zero": "γ=0",
        "learned": "learned γ",
        "one": "γ=1",
    }
    gate_label = gate_labels.get(gate_state)
    return label if gate_label is None else f"{label}\n({gate_label})"


def visualize_training_dynamics(
    history_rows: Sequence[Mapping[str, object]],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "01_training_dynamics"
    metrics = (
        ("loss_total", "Total Loss"),
        ("ssim_normalized", "Normalized SSIM"),
        ("psnr_normalized", "Normalized PSNR"),
        ("loss_frequency", "Frequency Loss"),
    )
    split_colors = {
        "train": _RESTORATION_PALETTE["primary"],
        "val": _RESTORATION_PALETTE["warning"],
    }
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for axis, (metric_name, label) in zip(axes.ravel(), metrics):
        plotted = False
        for split, color in split_colors.items():
            points: list[tuple[float, float]] = []
            for row in history_rows:
                if row.get("split") != split:
                    continue
                epoch = _finite_float(row.get("epoch"))
                value = _finite_float(row.get(metric_name))
                if epoch is None or value is None:
                    continue
                points.append((epoch, value))
            if points:
                points.sort(key=lambda point: point[0])
                axis.plot(
                    [point[0] for point in points],
                    [point[1] for point in points],
                    marker="o",
                    label=split,
                    color=color,
                )
                plotted = True
        axis.set_title(label)
        axis.set_xlabel("Epoch")
        axis.set_ylabel(label)
        if plotted:
            axis.legend()
        else:
            axis.text(
                0.5,
                0.5,
                "No finite data",
                ha="center",
                va="center",
                transform=axis.transAxes,
            )
    fig.suptitle(FIGURE_TEXT_SPEC[figure_name]["title"])
    return _save_figure_pair(fig, output_dir, figure_name)


def visualize_restoration_examples(
    examples: Mapping[str, object],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "02_restoration_examples"
    clean = _image_from_examples(examples, "clean")
    degraded = _image_from_examples(examples, "degraded")
    phase_zero = _image_from_examples(examples, "phase_zero")
    restored = _image_from_examples(examples, "restored")
    residual = (
        np.abs(restored - clean)
        if clean is not None and restored is not None and clean.shape == restored.shape
        else None
    )
    images = (
        ("Clean", clean, "gray"),
        ("Degraded", degraded, "gray"),
        ("Phase Zero", phase_zero, "gray"),
        ("Restored", restored, "gray"),
        ("Residual", residual, "magma"),
    )
    fig, axes = plt.subplots(1, 5, figsize=(15, 3), constrained_layout=True)
    for axis, (title, image, cmap) in zip(axes, images):
        axis.set_title(title)
        axis.set_xticks([])
        axis.set_yticks([])
        if image is None:
            axis.text(
                0.5,
                0.5,
                "Missing",
                ha="center",
                va="center",
                transform=axis.transAxes,
            )
            continue
        axis.imshow(image, cmap=cmap, vmin=0.0)
    fig.suptitle(FIGURE_TEXT_SPEC[figure_name]["title"])
    return _save_figure_pair(fig, output_dir, figure_name)


def _image_from_examples(examples: Mapping[str, object], key: str) -> np.ndarray | None:
    if key not in examples:
        return None
    try:
        return _to_numpy(examples[key])
    except (TypeError, ValueError):
        return None


def visualize_phase_mask_evolution(
    initial_phase: object,
    best_phase: object,
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "03_phase_mask_evolution"
    initial = _to_numpy(initial_phase)
    final = _to_numpy(best_phase)
    finite_values = final[np.isfinite(final)]
    if finite_values.size == 0:
        finite_values = np.asarray([0.0], dtype=np.float32)
    phase_min = float(min(np.nanmin(initial), np.nanmin(final)))
    phase_max = float(max(np.nanmax(initial), np.nanmax(final)))
    if phase_min == phase_max:
        phase_min -= 1.0
        phase_max += 1.0

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5), constrained_layout=True)
    for axis, title, image in (
        (axes[0], "Initial Phase", initial),
        (axes[1], "Best/Final Phase", final),
    ):
        handle = axis.imshow(image, cmap="twilight", vmin=phase_min, vmax=phase_max)
        axis.set_title(title)
        axis.set_xticks([])
        axis.set_yticks([])
        fig.colorbar(handle, ax=axis, fraction=0.046, pad=0.04)
    axes[2].hist(
        finite_values.ravel(),
        bins=min(30, max(5, finite_values.size)),
        color=_RESTORATION_PALETTE["primary_fill"],
    )
    axes[2].set_title("Final Phase Histogram")
    axes[2].set_xlabel("Phase")
    axes[2].set_ylabel("Pixels")
    fig.suptitle(FIGURE_TEXT_SPEC[figure_name]["title"])
    return _save_figure_pair(fig, output_dir, figure_name)


def visualize_frequency_response_comparison(
    payload: Mapping[str, object],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "04_frequency_response_comparison"
    frequencies = payload.get("spatial_frequencies", payload.get("frequencies"))
    responses = payload.get("frequency_response", payload.get("responses"))

    fig, axis = plt.subplots(figsize=(6, 4), constrained_layout=True)
    if (
        isinstance(frequencies, Sequence)
        and not isinstance(frequencies, (str, bytes))
        and isinstance(responses, Sequence)
        and not isinstance(responses, (str, bytes))
    ):
        points = []
        for x_value, y_value in zip(frequencies, responses):
            frequency = _finite_float(x_value)
            response = _finite_float(y_value)
            if frequency is not None and response is not None:
                points.append((frequency, response))
        if points:
            points.sort(key=lambda point: point[0])
            axis.plot(
                [point[0] for point in points],
                [point[1] for point in points],
                marker="o",
                color=_RESTORATION_PALETTE["primary"],
            )
            axis.set_xlabel("Spatial Frequency")
            axis.set_ylabel("Response")
        else:
            _plot_psnr_bars(axis, payload)
    else:
        _plot_psnr_bars(axis, payload)
    axis.set_title(FIGURE_TEXT_SPEC[figure_name]["title"])
    return _save_figure_pair(fig, output_dir, figure_name)


def _plot_psnr_bars(axis: plt.Axes, payload: Mapping[str, object]) -> None:
    values = [
        ("Phase Zero", _finite_float(payload.get("phase_zero_vs_clean_psnr"))),
        ("Trained", _finite_float(payload.get("trained_vs_clean_psnr"))),
    ]
    finite_values = [(label, value) for label, value in values if value is not None]
    if not finite_values:
        axis.text(
            0.5,
            0.5,
            "No finite performance data",
            ha="center",
            va="center",
            transform=axis.transAxes,
        )
        axis.set_xticks([])
        axis.set_ylabel("PSNR vs clean (dB)")
        return
    axis.bar(
        [label for label, _value in finite_values],
        [value for _label, value in finite_values],
        color=_RESTORATION_PALETTE["primary_fill"],
    )
    axis.set_xlabel("Intensity-domain comparison")
    axis.set_ylabel("PSNR vs clean (dB)")


def visualize_operating_point_trace(
    operating_point: Mapping[str, object],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "05_operating_point_trace"
    selected_values = operating_point.get("selected_values", operating_point)
    if not isinstance(selected_values, Mapping):
        selected_values = {}
    numeric_items = (
        (key, _finite_float(value)) for key, value in selected_values.items()
    )
    values = [
        (str(key).replace("selected_", "").replace("_", " ").title(), numeric_value)
        for key, numeric_value in numeric_items
        if numeric_value is not None
    ]

    fig, axis = plt.subplots(figsize=(8, 4), constrained_layout=True)
    if values:
        x_values = np.arange(len(values))
        axis.bar(
            x_values,
            [value for _label, value in values],
            color=_RESTORATION_PALETTE["secondary"],
        )
        axis.set_xticks(
            x_values,
            labels=[label for label, _value in values],
            rotation=20,
            ha="right",
        )
        axis.set_ylabel("Selected Value")
    else:
        axis.text(
            0.5,
            0.5,
            "No numeric selected values",
            ha="center",
            va="center",
            transform=axis.transAxes,
        )
        axis.set_xticks([])
    axis.set_title(FIGURE_TEXT_SPEC[figure_name]["title"])
    return _save_figure_pair(fig, output_dir, figure_name)


def visualize_resolution_budget(
    budget: Mapping[str, object],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "01_resolution_budget"
    entries: list[tuple[str, float]] = []
    for keys, label in (
        (("aperture_cutoff_frequency",), "Fourier Aperture Cutoff"),
        (("slm1_nyquist_frequency", "input_nyquist_frequency"), "SLM1/Input Nyquist"),
        (("slm2_nyquist_frequency", "input_nyquist_frequency"), "SLM2 Mask Nyquist"),
        (("camera_nyquist_frequency",), "ASI585MM Camera Nyquist"),
    ):
        value = _first_available_float(budget, keys)
        if value is not None:
            entries.append((label, _cycles_per_meter_to_cycles_per_mm(value)))
    if not entries:
        entries = [("No data", 0.0)]

    finite_entries = [(label, value) for label, value in entries if value > 0.0]
    bottleneck_label: str | None = None
    bottleneck_value: float | None = None
    if finite_entries:
        bottleneck_label, bottleneck_value = min(finite_entries, key=lambda item: item[1])

    fig, axis = plt.subplots(figsize=(7.2, 3.4), constrained_layout=True)
    y_values = np.arange(len(entries))
    labels = [label for label, _value in entries]
    colors = [
        _RESTORATION_PALETTE["accent"]
        if bottleneck_label is not None and label == bottleneck_label
        else _RESTORATION_PALETTE["primary"]
        for label in labels
    ]
    axis.barh(
        y_values,
        [value for _label, value in entries],
        color=colors,
        edgecolor=_RESTORATION_PALETTE["primary"],
        linewidth=_RESTORATION_STYLE.spine_linewidth,
    )
    axis.set_yticks(y_values, labels=labels)
    axis.invert_yaxis()
    axis.set_title(FIGURE_TEXT_SPEC[figure_name]["title"])
    axis.set_xlabel("Spatial Frequency (cycles/mm)")
    style_grid(
        axis,
        _RESTORATION_STYLE,
        grid_axis="x",
        alpha=_RESTORATION_STYLE.subtle_grid_alpha,
    )
    if bottleneck_label is None or bottleneck_value is None:
        axis.text(
            0.5,
            0.5,
            "No positive resolution limit available",
            transform=axis.transAxes,
            ha="center",
            va="center",
            color=_RESTORATION_PALETTE["dark_text"],
        )
    return _save_figure_pair(fig, output_dir, figure_name)


def _visualize_baseline_triptych(
    figure_name: str,
    baselines: Mapping[str, object],
    output_dir: Path | str,
) -> dict[str, str]:
    images = (
        ("Input Identity", baselines.get("image_input_identity"), "gray"),
        ("Process Arm Phase Zero", baselines.get("image_process_arm_phase_zero"), "gray"),
        ("Full Frontend Phase Zero", baselines.get("image_full_frontend_phase_zero"), "gray"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(9, 3), constrained_layout=True)
    for axis, (title, image, cmap) in zip(axes, images):
        axis.set_title(title)
        axis.set_xticks([])
        axis.set_yticks([])
        if image is None:
            axis.text(0.5, 0.5, "Missing", ha="center", va="center", transform=axis.transAxes)
            continue
        axis.imshow(_to_numpy(image), cmap=cmap, vmin=0.0)
    fig.suptitle(FIGURE_TEXT_SPEC[figure_name]["title"])
    return _save_figure_pair(fig, output_dir, figure_name)


def visualize_point_response(
    target_baselines: Mapping[str, Mapping[str, object]],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "02_point_response"
    point_key = None
    for key in target_baselines:
        if "point" in key:
            point_key = key
            break
    if point_key is None:
        keys = list(target_baselines.keys())
        point_key = keys[0] if keys else ""
    baselines = target_baselines.get(point_key, {})
    columns = (
        "image_input_identity",
        "image_process_arm_phase_zero",
        "image_full_frontend_phase_zero",
        "image_interference_term",
    )
    titles = ("Input", "Process Arm", "Full Frontend", "Interference")
    fig, axes = plt.subplots(1, 4, figsize=(12, 3), constrained_layout=True)
    for axis, column_name, title in zip(axes, columns, titles):
        axis.set_title(title)
        axis.set_xticks([])
        axis.set_yticks([])
        image_data = baselines.get(column_name)
        if image_data is None:
            axis.text(0.5, 0.5, "Missing", ha="center", va="center", transform=axis.transAxes)
            continue
        image = _to_numpy(image_data)
        image = _center_crop(image)
        if column_name == "image_interference_term":
            axis.imshow(
                _normalize_signed_display_image(image),
                cmap="coolwarm",
                vmin=-1.0,
                vmax=1.0,
            )
        else:
            axis.imshow(_normalize_display_image(image), cmap="gray", vmin=0.0, vmax=1.0)
    fig.suptitle(FIGURE_TEXT_SPEC[figure_name]["title"])
    return _save_figure_pair(fig, output_dir, figure_name)


def visualize_edge_derived_intensity_mtf(
    metric_rows: Sequence[Mapping[str, object]],
    output_dir: Path | str,
    *,
    curve_rows: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    return _write_edge_mtf_figure(
        output_dir,
        "03_edge_derived_intensity_mtf",
        metric_rows,
        curve_rows=curve_rows,
    )


def visualize_grating_ctf(
    metric_rows: Sequence[Mapping[str, object]],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    return _write_grating_ctf_figure(
        output_dir,
        "04_grating_ctf",
        metric_rows,
    )


def visualize_usaf_resolution(
    target_baselines: Mapping[str, Mapping[str, object]],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "05_usaf_resolution"
    usaf_key = None
    for key in target_baselines:
        if "usaf" in key:
            usaf_key = key
            break
    if usaf_key is None:
        keys = list(target_baselines.keys())
        usaf_key = keys[0] if keys else ""
    baselines = target_baselines.get(usaf_key, {})
    return _visualize_baseline_triptych(figure_name, baselines, output_dir)


def visualize_siemens_star_diagnostic(
    target_baselines: Mapping[str, Mapping[str, object]],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "06_siemens_star_diagnostic"
    star_key = None
    for key in target_baselines:
        if "siemens" in key:
            star_key = key
            break
    if star_key is None:
        keys = list(target_baselines.keys())
        star_key = keys[0] if keys else ""
    baselines = target_baselines.get(star_key, {})
    return _visualize_baseline_triptych(figure_name, baselines, output_dir)


def visualize_phase_offset_sensitivity(
    metric_rows: Sequence[Mapping[str, object]],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "07_phase_offset_sensitivity"
    visibility_rows = [
        row
        for row in metric_rows
        if row.get("metric_name") == "interference_visibility"
        and _finite_float(row.get("phase_offset_reference")) is not None
        and _finite_float(row.get("metric_value")) is not None
    ]
    scan_rows = [
        row
        for row in visibility_rows
        if row.get("sweep_step") == "phase_offset_scan"
    ]
    rows_to_plot = scan_rows or visibility_rows
    points = [
        (float(row["phase_offset_reference"]), float(row["metric_value"]))
        for row in rows_to_plot
    ]
    if not points:
        points = [(0.0, 0.0)]
    points.sort(key=lambda point: point[0])
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]

    fig, axis = plt.subplots(figsize=(6, 4), constrained_layout=True)
    axis.plot(
        x_values,
        y_values,
        marker="o",
        color=_RESTORATION_PALETTE["primary"],
    )
    axis.set_xticks(
        x_values,
        labels=[_phase_tick_label(value) for value in x_values],
    )
    axis.set_title(FIGURE_TEXT_SPEC[figure_name]["title"])
    axis.set_xlabel("Phase Offset Reference")
    axis.set_ylabel("Interference Visibility")
    style_grid(axis, _RESTORATION_STYLE, alpha=_RESTORATION_STYLE.subtle_grid_alpha)
    return _save_figure_pair(fig, output_dir, figure_name)


def visualize_operating_point_summary(
    payload: Mapping[str, object],
    output_dir: Path | str,
) -> dict[str, str]:
    """
    实现可视化辅助逻辑
    """
    figure_name = "08_operating_point_summary"
    checks = (
        list(payload.get("checks", []))
        if isinstance(payload.get("checks", []), (list, tuple))
        else []
    )
    metric_rows = (
        list(payload.get("metric_rows", []))
        if isinstance(payload.get("metric_rows", []), (list, tuple))
        else []
    )
    operating_point = payload.get("operating_point", {})
    if not isinstance(operating_point, Mapping):
        operating_point = {}

    check_aliases = {
        "interference_reconstruction": (
            "interference_reconstruction_matches_full",
            "interference_reconstructs_full",
        ),
        "operating_point_selected": ("operating_point_written",),
        "artifact_write_complete": ("operating_point_written",),
    }
    check_status_by_name = {
        str(check.get("name")): str(check.get("status", ""))
        for check in checks
        if isinstance(check, Mapping)
    }
    check_names = (
        "finite_fields",
        "nonnegative_intensities",
        "interference_reconstruction",
        "operating_point_selected",
        "artifact_write_complete",
    )
    decision_checks: list[tuple[str, bool]] = []
    for check_name in check_names:
        status = check_status_by_name.get(check_name)
        for alias in check_aliases.get(check_name, ()):
            if status is not None:
                break
            status = check_status_by_name.get(alias)
        decision_checks.append((check_name, status == "PASS"))

    fig = plt.figure(figsize=(8.6, 4.2), constrained_layout=True)
    grid = fig.add_gridspec(3, 3, height_ratios=[0.72, 1.42, 1.0])
    check_axis = fig.add_subplot(grid[0, :])
    metric_axes = [fig.add_subplot(grid[1, index]) for index in range(3)]
    parameter_axis = fig.add_subplot(grid[2, :])

    x_positions = np.arange(len(decision_checks))
    check_axis.bar(
        x_positions,
        [1.0 for _name, _passed in decision_checks],
        color=[
            _RESTORATION_PALETTE["secondary"] if passed else _RESTORATION_PALETTE["warning"]
            for _name, passed in decision_checks
        ],
        edgecolor=_RESTORATION_PALETTE["panel_bg"],
        linewidth=_RESTORATION_STYLE.spine_linewidth,
    )
    check_axis.set_ylim(0.0, 1.0)
    check_axis.set_yticks([])
    check_axis.set_xticks(
        x_positions,
        labels=[name.replace("_", "\n") for name, _passed in decision_checks],
    )
    check_axis.set_title("Decision Checks")
    for index, (check_name, passed) in enumerate(decision_checks):
        check_axis.text(
            index,
            0.5,
            "PASS" if passed else "FAIL",
            ha="center",
            va="center",
            color=_RESTORATION_PALETTE["panel_bg"],
            fontweight="bold",
        )

    headline_metrics = (
        (
            "MTF50",
            _summary_metric_for_operating_point(
                operating_point,
                metric_rows,
                "edge_mtf50_cycles_per_pixel",
                baseline_name="full_frontend_phase_zero",
            ),
        ),
        (
            "Throughput",
            _summary_metric_for_operating_point(
                operating_point,
                metric_rows,
                "energy_throughput",
                baseline_name="full_frontend_phase_zero",
            ),
        ),
        (
            "Visibility",
            _summary_metric_for_operating_point(
                operating_point,
                metric_rows,
                "interference_visibility",
                baseline_name="interference_term",
            ),
        ),
    )
    metric_colors = (
        _RESTORATION_PALETTE["primary"],
        _RESTORATION_PALETTE["secondary"],
        _RESTORATION_PALETTE["violet"],
    )
    for axis, (label, value), color in zip(metric_axes, headline_metrics, metric_colors):
        if label == "MTF50":
            limit = 0.5
            xlabel = "cycles/pixel"
        elif label == "Throughput":
            limit = 2.0
            xlabel = "ratio"
        else:
            limit = 1.0
            xlabel = "ratio"
        bar_value = 0.0 if value is None else max(0.0, value)
        x_limit = max(limit, bar_value * 1.08, 1e-6)
        axis.barh(
            [0.18],
            [bar_value],
            height=0.22,
            color=color,
            edgecolor=color,
            linewidth=_RESTORATION_STYLE.spine_linewidth,
        )
        axis.set_xlim(0.0, x_limit)
        axis.set_ylim(0.0, 1.0)
        axis.set_xticks([0.0, limit])
        axis.set_yticks([])
        axis.set_xlabel(xlabel)
        style_grid(
            axis,
            _RESTORATION_STYLE,
            grid_axis="x",
            alpha=_RESTORATION_STYLE.diagnostic_grid_alpha,
        )
        axis.text(
            0.5,
            0.68,
            _metric_text(label, value),
            ha="center",
            va="center",
            transform=axis.transAxes,
            fontweight="bold",
        )

    parameter_keys = (
        ("Array", ("selected_array_size", "array_size")),
        ("Phase Mask", ("selected_phase_mask_resolution", "phase_mask_resolution")),
        ("SLM Active", ("selected_slm2_active_resolution", "slm2_active_resolution")),
        ("Focal Length", ("selected_focal_length", "focal_length")),
        ("Fourier Px", ("fourier_plane_pixel_size_x",)),
        ("Aperture", ("selected_aperture_policy", "aperture_policy")),
        (
            "Camera",
            ("selected_camera_sampling", "camera_sampling"),
        ),
        (
            "Phase Offset",
            ("selected_phase_offset_reference", "phase_offset_reference"),
        ),
    )
    parameter_items: list[tuple[str, str]] = []
    for label, candidate_keys in parameter_keys:
        value = None
        for key in candidate_keys:
            if key in operating_point:
                value = operating_point[key]
                break
        parameter_items.append((label, _format_operating_point_value(label, value)))
    parameter_axis.set_xticks([])
    parameter_axis.set_yticks([])
    parameter_axis.set_title("Selected Parameters")
    parameter_axis.set_xlim(0.0, float(len(parameter_items)))
    parameter_axis.set_ylim(0.0, 1.0)
    for index, (label, value) in enumerate(parameter_items):
        x_value = index + 0.5
        parameter_axis.text(
            x_value,
            0.64,
            label,
            ha="center",
            va="center",
            fontweight="bold",
        )
        parameter_axis.text(
            x_value,
            0.32,
            value,
            ha="center",
            va="center",
        )
    fig.suptitle(FIGURE_TEXT_SPEC[figure_name]["title"])
    return _save_figure_pair(fig, output_dir, figure_name)


def _summary_metric_for_operating_point(
    operating_point: Mapping[str, object],
    metric_rows: Sequence[Mapping[str, object]],
    metric_name: str,
    *,
    baseline_name: str | None = None,
) -> float | None:
    selection_metrics = operating_point.get("selection_metrics")
    if isinstance(selection_metrics, Mapping):
        value = _finite_float(selection_metrics.get(metric_name))
        if value is not None:
            return value
    flat_aliases = {
        "edge_mtf50_cycles_per_pixel": ("measured_mtf50",),
        "energy_throughput": ("energy_throughput",),
        "interference_visibility": ("interference_visibility",),
    }
    value = _first_available_float(operating_point, flat_aliases.get(metric_name, ()))
    if value is not None:
        return value
    return _first_metric_for_summary(
        metric_rows,
        metric_name,
        baseline_name=baseline_name,
    )


def _format_operating_point_value(label: str, value: object) -> str:
    if value is None:
        return "n/a"
    if label == "Focal Length":
        numeric_value = _finite_float(value)
        return "n/a" if numeric_value is None else f"{numeric_value:.2f} m"
    if label == "Phase Offset":
        numeric_value = _finite_float(value)
        return "n/a" if numeric_value is None else f"{numeric_value:.2f} rad"
    if label == "SLM Active" and isinstance(value, Sequence) and not isinstance(value, str):
        values = list(value)
        if len(values) == 2:
            return f"{values[0]}x{values[1]}"
    if label == "Fourier Px":
        numeric_value = _finite_float(value)
        return "n/a" if numeric_value is None else f"{numeric_value * 1e6:.2f} um"
    if label == "Aperture" and str(value) == "full_slm_active_area":
        return "Full SLM"
    if label == "Camera" and str(value) == "native_sensor":
        return "ASI585MM Native"
    return str(value)


def _first_metric_for_summary(
    metric_rows: Sequence[Mapping[str, object]],
    metric_name: str,
    *,
    baseline_name: str | None = None,
) -> float | None:
    def _matching_value(row: Mapping[str, object]) -> float | None:
        if row.get("metric_name") != metric_name:
            return None
        if baseline_name is not None and row.get("baseline_name") != baseline_name:
            return None
        return _finite_float(row.get("metric_value"))

    matching_rows = [row for row in metric_rows if isinstance(row, Mapping)]
    candidate_rows = [
        row for row in matching_rows if row.get("sweep_step") != "phase_offset_scan"
    ] or matching_rows
    for row in candidate_rows:
        value = _matching_value(row)
        if value is not None:
            return value
    return None


def _metric_text(label: str, value: float | None, precision: int = 3) -> str:
    if value is None:
        return f"{label}\nn/a"
    return f"{label}\n{value:.{precision}f}"


def _metric_values(metric_rows: Sequence[Mapping[str, object]], metric_name: str) -> list[float]:
    values: list[float] = []
    for row in metric_rows:
        if row.get("metric_name") != metric_name:
            continue
        try:
            values.append(float(row.get("metric_value", 0.0)))
        except (TypeError, ValueError):
            continue
    return values[:12] or [0.0]


def _write_bar_figure(
    output_dir: Path | str,
    figure_name: str,
    values: Sequence[float],
    *,
    ylabel: str,
) -> dict[str, str]:
    return _PANEL_WRITERS["bar"](
        output_dir,
        figure_name,
        values,
        ylabel=ylabel,
        figure_text_spec=FIGURE_TEXT_SPEC,
        palette=_RESTORATION_PALETTE,
        save_figure_pair=_save_figure_pair,
    )

def _write_edge_mtf_figure(
    output_dir: Path | str,
    figure_name: str,
    metric_rows: Sequence[Mapping[str, object]],
    *,
    curve_rows: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, str]:
    def write_labeled_bar(
        nested_output_dir: Path | str,
        nested_figure_name: str,
        values: Sequence[tuple[str, float]],
        *,
        ylabel: str,
    ) -> dict[str, str]:
        """
        写入带标签柱状面板
        """
        return _write_labeled_bar_figure(
            nested_output_dir,
            nested_figure_name,
            values,
            ylabel=ylabel,
        )

    return _PANEL_WRITERS["edge_mtf"](
        output_dir,
        figure_name,
        metric_rows,
        curve_rows=curve_rows,
        figure_text_spec=FIGURE_TEXT_SPEC,
        palette=_RESTORATION_PALETTE,
        restoration_style=_RESTORATION_STYLE,
        title_case=_title_case,
        finite_float=_finite_float,
        edge_mtf_curve_series=_edge_mtf_curve_series,
        write_labeled_bar_figure=write_labeled_bar,
        save_figure_pair=_save_figure_pair,
    )

def _edge_mtf_curve_series(
    curve_rows: Sequence[Mapping[str, object]],
) -> list[tuple[str, list[tuple[float, float]]]]:
    series: list[tuple[str, list[tuple[float, float]]]] = []
    for row in curve_rows:
        if not isinstance(row, Mapping):
            continue
        frequencies = row.get("frequencies_cycles_per_pixel")
        mtf_values = row.get("mtf")
        if not isinstance(frequencies, Sequence) or isinstance(frequencies, (str, bytes)):
            continue
        if not isinstance(mtf_values, Sequence) or isinstance(mtf_values, (str, bytes)):
            continue
        points: list[tuple[float, float]] = []
        for frequency_value, mtf_value in zip(frequencies, mtf_values):
            frequency = _finite_float(frequency_value)
            response = _finite_float(mtf_value)
            if frequency is None or response is None:
                continue
            points.append((frequency, response))
        if not points:
            continue
        points.sort(key=lambda point: point[0])
        series.append((str(row.get("baseline_name", "baseline")), points))
    return series


def _write_grating_ctf_figure(
    output_dir: Path | str,
    figure_name: str,
    metric_rows: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    return _PANEL_WRITERS["grating_ctf"](
        output_dir,
        figure_name,
        metric_rows,
        figure_text_spec=FIGURE_TEXT_SPEC,
        palette=_RESTORATION_PALETTE,
        restoration_style=_RESTORATION_STYLE,
        save_figure_pair=_save_figure_pair,
    )

def _write_point_response_figure(
    output_dir: Path | str,
    figure_name: str,
    metric_rows: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    def write_labeled_bar(
        nested_output_dir: Path | str,
        nested_figure_name: str,
        values: Sequence[tuple[str, float]],
        *,
        ylabel: str,
    ) -> dict[str, str]:
        """
        写入带标签柱状面板
        """
        return _write_labeled_bar_figure(
            nested_output_dir,
            nested_figure_name,
            values,
            ylabel=ylabel,
        )

    return _PANEL_WRITERS["point_response"](
        output_dir,
        figure_name,
        metric_rows,
        first_metric_value=_first_metric_value,
        write_labeled_bar_figure=write_labeled_bar,
    )

def _first_metric_value(
    metric_rows: Sequence[Mapping[str, object]],
    metric_name: str,
) -> float | None:
    for row in metric_rows:
        if row.get("metric_name") != metric_name:
            continue
        value = _finite_float(row.get("metric_value"))
        if value is not None:
            return value
    return None


def _write_labeled_bar_figure(
    output_dir: Path | str,
    figure_name: str,
    values: Sequence[tuple[str, float]],
    *,
    ylabel: str,
) -> dict[str, str]:
    return _PANEL_WRITERS["labeled_bar"](
        output_dir,
        figure_name,
        values,
        ylabel=ylabel,
        figure_text_spec=FIGURE_TEXT_SPEC,
        palette=_RESTORATION_PALETTE,
        save_figure_pair=_save_figure_pair,
    )

def _write_check_figure(
    output_dir: Path | str,
    figure_name: str,
    checks: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    return _PANEL_WRITERS["check"](
        output_dir,
        figure_name,
        checks,
        figure_text_spec=FIGURE_TEXT_SPEC,
        palette=_RESTORATION_PALETTE,
        title_case=_title_case,
        save_figure_pair=_save_figure_pair,
    )

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import torch

from experiments.validation.artifacts import (
    aggregate_status,
    clear_output_dir,
    write_metrics,
    write_summary,
)
from experiments.validation.layers._shared import (
    finite_max_abs,
    gaussian_field,
    layer_check,
    metric_rows,
    resolve_device,
    size_to_resolution,
    summary_lines,
)
from experiments.validation.style import (
    plot_image_with_colorbar,
    save_device_agreement_figure,
    save_figure_pair,
    setup_plot_style,
    validation_figure_size,
)
from layers import DetectionLayer

_LAYER_NAME = "detection"
_FIGURE_NAMES = ("intensity_response", "device_agreement")


@dataclass(frozen=True, slots=True)
class _Study:
    resolution: int
    device: torch.device
    raw_layer: DetectionLayer
    normalized_layer: DetectionLayer
    input_field: torch.Tensor
    expected_intensity: torch.Tensor
    detected_intensity: torch.Tensor
    normalized_intensity: torch.Tensor
    raw_device_difference: torch.Tensor | None
    normalized_device_difference: torch.Tensor | None


def _measure(*, device: str, size: str) -> _Study:
    resolved_device = resolve_device(device)
    resolution = size_to_resolution(size)
    input_field = 1.5 * gaussian_field(resolution, resolved_device)
    raw_layer = DetectionLayer((resolution, resolution), False).to(resolved_device)
    normalized_layer = DetectionLayer((resolution, resolution), True).to(
        resolved_device,
    )
    expected_intensity = input_field.abs().square()
    with torch.no_grad():
        detected_intensity = raw_layer(input_field)
        normalized_intensity = normalized_layer(input_field)
    raw_difference, normalized_difference = _device_differences(
        input_field.detach().cpu(),
    )
    return _Study(
        resolution=resolution,
        device=resolved_device,
        raw_layer=raw_layer,
        normalized_layer=normalized_layer,
        input_field=input_field,
        expected_intensity=expected_intensity,
        detected_intensity=detected_intensity,
        normalized_intensity=normalized_intensity,
        raw_device_difference=raw_difference,
        normalized_device_difference=normalized_difference,
    )


def _device_differences(
    input_field: torch.Tensor,
) -> tuple[torch.Tensor | None, torch.Tensor | None]:
    if not torch.cuda.is_available():
        return None, None
    resolution = input_field.shape[-1]
    differences = []
    for is_normalized in (False, True):
        cpu_layer = DetectionLayer((resolution, resolution), is_normalized)
        gpu_layer = DetectionLayer((resolution, resolution), is_normalized).cuda()
        with torch.no_grad():
            cpu_output = cpu_layer(input_field)
            gpu_output = gpu_layer(input_field.cuda()).cpu()
        differences.append(torch.abs(cpu_output - gpu_output))
    return differences[0], differences[1]


def _construction_check(study: _Study) -> dict[str, object]:
    rejected = False
    try:
        DetectionLayer(
            (study.resolution, study.resolution),
            is_normalization_enabled=1,  # type: ignore[arg-type]
        )
    except ValueError:
        rejected = True
    return layer_check(
        "construction",
        rejected,
        invalid_normalization_flag_raises=rejected,
    )


def _intensity_check(study: _Study) -> dict[str, object]:
    error = finite_max_abs(study.detected_intensity - study.expected_intensity)
    return layer_check(
        "intensity_readout",
        error <= 1e-7,
        raw_intensity_max_abs_error=error,
    )


def _normalization_check(study: _Study) -> dict[str, object]:
    expected = study.expected_intensity / study.expected_intensity.amax(
        dim=(-2, -1),
        keepdim=True,
    )
    normalized_error = finite_max_abs(study.normalized_intensity - expected)
    peak_error = finite_max_abs(
        study.normalized_intensity.amax(dim=(-2, -1)) - 1.0,
    )
    zero_output = study.normalized_layer(torch.zeros_like(study.input_field))
    zero_error = finite_max_abs(zero_output)
    return layer_check(
        "normalization",
        normalized_error <= 1e-7 and peak_error <= 1e-7 and zero_error == 0.0,
        normalized_max_abs_error=normalized_error,
        normalized_peak_error=peak_error,
        zero_field_max_abs=zero_error,
    )


def _feature_check(study: _Study) -> dict[str, object]:
    outputs = (study.detected_intensity, study.normalized_intensity)
    passed = all(
        output.shape == study.input_field.shape
        and output.dtype == torch.float32
        and bool(torch.isfinite(output).all())
        for output in outputs
    )
    return layer_check(
        "feature_contract",
        passed,
        output_shape=tuple(study.detected_intensity.shape),
        output_dtype=str(study.detected_intensity.dtype),
        outputs_finite=all(bool(torch.isfinite(output).all()) for output in outputs),
    )


def _autograd_check(study: _Study) -> dict[str, object]:
    input_field = study.input_field.detach().clone().requires_grad_(True)
    study.raw_layer(input_field).sum().backward()
    gradient = input_field.grad
    assert gradient is not None
    maximum = finite_max_abs(gradient)
    return layer_check(
        "autograd_input_gradient",
        bool(torch.isfinite(gradient).all()) and maximum > 0.0,
        input_gradient_max_abs=maximum,
    )


def _cpu_gpu_check(study: _Study) -> dict[str, object]:
    if study.raw_device_difference is None or study.normalized_device_difference is None:
        return layer_check("cpu_gpu_consistency", None, detail="CUDA unavailable")
    raw_error = finite_max_abs(study.raw_device_difference)
    normalized_error = finite_max_abs(study.normalized_device_difference)
    return layer_check(
        "cpu_gpu_consistency",
        max(raw_error, normalized_error) <= 1e-6,
        cpu_gpu_raw_max_abs_error=raw_error,
        cpu_gpu_normalized_max_abs_error=normalized_error,
    )


def _checks(study: _Study) -> list[dict[str, object]]:
    return [
        _construction_check(study),
        _intensity_check(study),
        _normalization_check(study),
        _feature_check(study),
        _autograd_check(study),
        _cpu_gpu_check(study),
    ]


def _save_intensity_response(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    fig, axes = plt.subplots(
        1,
        3,
        figsize=validation_figure_size("detection_intensity_response"),
        constrained_layout=True,
    )
    panels = (
        (study.input_field.abs(), "Input Amplitude", "optical_amplitude", None),
        (study.detected_intensity, "Detected Intensity", "optical_intensity", None),
        (study.normalized_intensity, "Normalized Intensity", "optical_intensity", 1.0),
    )
    for axis, (image, title, cmap, vmax) in zip(axes, panels, strict=True):
        plot_image_with_colorbar(
            axis,
            image,
            title,
            cmap,
            vmin=0.0,
            vmax=vmax,
        )
    fig.suptitle("Intensity Response")
    return save_figure_pair(fig, output_dir, "intensity_response")


def _save_device_agreement(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    difference = study.normalized_device_difference
    if difference is None:
        return save_device_agreement_figure(output_dir)
    return save_device_agreement_figure(
        output_dir,
        difference=difference,
        mean_abs_error=float(difference.mean()),
        max_abs_error=finite_max_abs(difference),
    )


def run(
    output_root: str | Path,
    *,
    device: str = "auto",
    seed: int = 42,
    size: str = "middle",
) -> dict[str, object]:
    """
    验证探测层的强度读出、归一化与设备一致性
    """
    torch.manual_seed(seed)
    setup_plot_style()
    output_dir = clear_output_dir(Path(output_root) / _LAYER_NAME)
    study = _measure(device=device, size=size)
    checks = _checks(study)
    status = aggregate_status(checks)
    metrics = metric_rows(_LAYER_NAME, checks)
    figure_savers = {
        "intensity_response": _save_intensity_response,
        "device_agreement": _save_device_agreement,
    }
    assert tuple(figure_savers) == _FIGURE_NAMES
    figures = {
        name: saver(output_dir, study)
        for name, saver in figure_savers.items()
    }
    write_metrics(output_dir, metrics)
    write_summary(
        output_dir,
        summary_lines(
            _LAYER_NAME,
            status,
            checks,
            figure_names=tuple(figures),
            physical_contract=(
                "- Raw readout: I = |E|^2",
                "- Normalization: per-sample spatial peak",
            ),
        ),
    )
    return {
        "layer": _LAYER_NAME,
        "status": status,
        "checks": checks,
        "metrics": metrics,
        "figures": figures,
        "output_dir": output_dir.as_posix(),
    }


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    解析命令行参数并运行探测层验证
    """
    parser = argparse.ArgumentParser(description="Validate DetectionLayer.")
    parser.add_argument("--output-root", type=Path, default=Path("results/validation/layers"))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--size", choices=("tiny", "middle", "full"), default="middle")
    args = parser.parse_args(argv)
    return run(
        output_root=args.output_root,
        device=args.device,
        seed=args.seed,
        size=args.size,
    )


if __name__ == "__main__":
    main()

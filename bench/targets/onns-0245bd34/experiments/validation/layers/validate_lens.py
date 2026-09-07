from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import math
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
    grating_field,
    layer_check,
    metric_rows,
    PIXEL_SIZE_M,
    resolve_device,
    size_to_resolution,
    summary_lines,
    WAVELENGTH_M,
)
from experiments.validation.style import (
    plot_shared_image_grid,
    save_device_agreement_figure,
    save_figure_pair,
    setup_plot_style,
    validation_figure_size,
)
from layers import LensLayer

_LAYER_NAME = "lens"
_FIGURE_NAMES = ("lens_phase", "fixed_phase_action", "device_agreement")
_FOCAL_LENGTH_M = 5e-3
_TWO_PI = float(2.0 * torch.pi)


@dataclass(frozen=True, slots=True)
class _Study:
    resolution: int
    device: torch.device
    positive_lens: LensLayer
    negative_lens: LensLayer
    input_field: torch.Tensor
    positive_phase: torch.Tensor
    negative_phase: torch.Tensor
    positive_output: torch.Tensor
    negative_output: torch.Tensor
    positive_device_difference: torch.Tensor | None
    negative_device_difference: torch.Tensor | None


def _new_lens(
    resolution: int,
    focal_length: float,
    device: torch.device,
) -> LensLayer:
    return LensLayer(
        wavelength=WAVELENGTH_M,
        focal_length=focal_length,
        pixel_size=PIXEL_SIZE_M,
        array_resolution=(resolution, resolution),
    ).to(device)


def _measure(*, device: str, size: str) -> _Study:
    resolved_device = resolve_device(device)
    resolution = size_to_resolution(size)
    positive_lens = _new_lens(resolution, _FOCAL_LENGTH_M, resolved_device)
    negative_lens = _new_lens(resolution, -_FOCAL_LENGTH_M, resolved_device)
    input_field = gaussian_field(resolution, resolved_device) * grating_field(
        resolution,
        resolved_device,
        cycles=2.0,
    )
    with torch.no_grad():
        positive_output = positive_lens(input_field)
        negative_output = negative_lens(input_field)
    positive_difference, negative_difference = _device_differences(
        input_field.detach().cpu(),
    )
    return _Study(
        resolution=resolution,
        device=resolved_device,
        positive_lens=positive_lens,
        negative_lens=negative_lens,
        input_field=input_field,
        positive_phase=positive_lens.get_lens_phase_information(),
        negative_phase=negative_lens.get_lens_phase_information(),
        positive_output=positive_output,
        negative_output=negative_output,
        positive_device_difference=positive_difference,
        negative_device_difference=negative_difference,
    )


def _device_differences(
    input_field: torch.Tensor,
) -> tuple[torch.Tensor | None, torch.Tensor | None]:
    if not torch.cuda.is_available():
        return None, None
    resolution = input_field.shape[-1]
    differences = []
    for focal_length in (_FOCAL_LENGTH_M, -_FOCAL_LENGTH_M):
        cpu_lens = _new_lens(resolution, focal_length, torch.device("cpu"))
        gpu_lens = _new_lens(resolution, focal_length, torch.device("cuda"))
        with torch.no_grad():
            cpu_output = cpu_lens(input_field)
            gpu_output = gpu_lens(input_field.cuda()).cpu()
        differences.append(torch.abs(cpu_output - gpu_output))
    return differences[0], differences[1]


def _invalid_lens_rejected(
    resolution: int,
    *,
    wavelength: float = WAVELENGTH_M,
    focal_length: float = _FOCAL_LENGTH_M,
    pixel_size: float = PIXEL_SIZE_M,
) -> bool:
    try:
        LensLayer(
            wavelength=wavelength,
            focal_length=focal_length,
            pixel_size=pixel_size,
            array_resolution=(resolution, resolution),
        )
    except ValueError:
        return True
    return False


def _construction_check(study: _Study) -> dict[str, object]:
    rejected = {
        "invalid_wavelength_rejected": _invalid_lens_rejected(
            study.resolution,
            wavelength=0.0,
        ),
        "invalid_focal_length_rejected": _invalid_lens_rejected(
            study.resolution,
            focal_length=0.0,
        ),
        "invalid_pixel_size_rejected": _invalid_lens_rejected(
            study.resolution,
            pixel_size=0.0,
        ),
    }
    return layer_check("construction", all(rejected.values()), **rejected)


def _expected_phase(lens: LensLayer) -> torch.Tensor:
    height, width = (int(value) for value in lens.array_resolution.tolist())
    y_coordinates = (
        torch.arange(height, device=lens.pixel_size.device) - (height - 1) / 2.0
    ) * lens.pixel_size
    x_coordinates = (
        torch.arange(width, device=lens.pixel_size.device) - (width - 1) / 2.0
    ) * lens.pixel_size
    y_grid, x_grid = torch.meshgrid(y_coordinates, x_coordinates, indexing="ij")
    raw_phase = (
        -lens.wavenumber
        * (x_grid.square() + y_grid.square())
        / (2.0 * lens.focal_length)
    )
    return torch.remainder(raw_phase, _TWO_PI)


def _phase_check(study: _Study) -> dict[str, object]:
    positive_error = finite_max_abs(
        study.positive_phase - _expected_phase(study.positive_lens),
    )
    negative_error = finite_max_abs(
        study.negative_phase - _expected_phase(study.negative_lens),
    )
    conjugate_error = finite_max_abs(
        torch.exp(1j * study.positive_phase)
        - torch.conj(torch.exp(1j * study.negative_phase)),
    )
    return layer_check(
        "phase_formula",
        max(positive_error, negative_error, conjugate_error) <= 1e-5,
        positive_phase_max_abs_error=positive_error,
        negative_phase_max_abs_error=negative_error,
        focal_sign_conjugate_max_abs_error=conjugate_error,
    )


def _amplitude_check(study: _Study) -> dict[str, object]:
    input_amplitude = study.input_field.abs()
    error = max(
        finite_max_abs(study.positive_output.abs() - input_amplitude),
        finite_max_abs(study.negative_output.abs() - input_amplitude),
    )
    return layer_check(
        "amplitude_preservation",
        error <= 1e-6,
        amplitude_max_abs_error=error,
    )


def _feature_check(study: _Study) -> dict[str, object]:
    outputs = (study.positive_output, study.negative_output)
    passed = all(
        output.shape == study.input_field.shape
        and output.dtype == torch.complex64
        and bool(torch.isfinite(output).all())
        for output in outputs
    )
    return layer_check(
        "feature_contract",
        passed,
        output_shape=tuple(study.positive_output.shape),
        output_dtype=str(study.positive_output.dtype),
        outputs_finite=all(bool(torch.isfinite(output).all()) for output in outputs),
    )


def _cpu_gpu_check(study: _Study) -> dict[str, object]:
    if (
        study.positive_device_difference is None
        or study.negative_device_difference is None
    ):
        return layer_check("cpu_gpu_consistency", None, detail="CUDA unavailable")
    positive_error = finite_max_abs(study.positive_device_difference)
    negative_error = finite_max_abs(study.negative_device_difference)
    return layer_check(
        "cpu_gpu_consistency",
        max(positive_error, negative_error) <= 1e-5,
        cpu_gpu_positive_focal_max_abs_error=positive_error,
        cpu_gpu_negative_focal_max_abs_error=negative_error,
    )


def _checks(study: _Study) -> list[dict[str, object]]:
    return [
        _construction_check(study),
        _phase_check(study),
        _amplitude_check(study),
        _feature_check(study),
        _cpu_gpu_check(study),
    ]


def _save_lens_phase(output_dir: Path, study: _Study) -> dict[str, str]:
    from matplotlib import pyplot as plt

    fig = plt.figure(figsize=validation_figure_size("lens_phase"))
    plot_shared_image_grid(
        fig,
        images=(study.positive_phase, study.negative_phase),
        titles=("Converging Phase", "Diverging Phase"),
        shape=(1, 2),
        cmap="phase_wrapped",
        label="Phase (rad)",
        vmin=0.0,
        vmax=_TWO_PI,
    )
    fig.suptitle("Lens Phase")
    return save_figure_pair(fig, output_dir, "lens_phase")


def _save_fixed_phase_action(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    applied_phase = torch.angle(torch.exp(1j * study.positive_phase))
    fig = plt.figure(figsize=validation_figure_size("lens_fixed_phase_action"))
    plot_shared_image_grid(
        fig,
        images=(
            torch.angle(study.input_field),
            applied_phase,
            torch.angle(study.positive_output),
        ),
        titles=("Input Phase", "Lens Phase", "Output Phase"),
        shape=(1, 3),
        cmap="phase_wrapped",
        label="Phase (rad)",
        vmin=-math.pi,
        vmax=math.pi,
        axes_pad=0.28,
    )
    fig.suptitle("Fixed Phase Action")
    return save_figure_pair(fig, output_dir, "fixed_phase_action")


def _save_device_agreement(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    difference = study.positive_device_difference
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
    验证透镜层的固定相位、前向作用与设备一致性
    """
    torch.manual_seed(seed)
    setup_plot_style()
    output_dir = clear_output_dir(Path(output_root) / _LAYER_NAME)
    study = _measure(device=device, size=size)
    checks = _checks(study)
    status = aggregate_status(checks)
    metrics = metric_rows(_LAYER_NAME, checks)
    figure_savers = {
        "lens_phase": _save_lens_phase,
        "fixed_phase_action": _save_fixed_phase_action,
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
                f"- Wavelength: {WAVELENGTH_M:g} m",
                f"- Focal magnitude: {_FOCAL_LENGTH_M:g} m",
                f"- Pixel size: {PIXEL_SIZE_M:g} m",
                "- Forward response: fixed phase-only modulation",
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
    解析命令行参数并运行透镜层验证
    """
    parser = argparse.ArgumentParser(description="Validate LensLayer.")
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

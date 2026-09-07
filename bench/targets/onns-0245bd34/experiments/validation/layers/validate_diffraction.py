from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import math
from pathlib import Path
import time

import numpy as np
import torch

from experiments.validation.artifacts import (
    aggregate_status,
    clear_output_dir,
    write_metrics,
    write_summary,
)
from experiments.validation.layers._shared import (
    finite_max_abs,
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
    resolve_validation_cmap,
    save_device_agreement_figure,
    save_figure_pair,
    setup_plot_style,
    style_validation_colorbar,
    style_validation_grid,
    tensor_to_numpy,
    validation_figure_size,
    VALIDATION_PALETTE,
)
from layers import DiffractionLayer

_LAYER_NAME = "diffraction"
_FIGURE_NAMES = (
    "propagation_response",
    "transfer_evolution",
    "device_agreement",
    "cache_performance",
)
_PROPAGATION_DISTANCE_M = 5e-3
_DISTANCES_M = tuple(
    _PROPAGATION_DISTANCE_M * factor
    for factor in (0.5, 1.0, 1.5)
)
_DISTANCE_LABELS = ("2.5 mm", "5.0 mm", "7.5 mm")
_BENCHMARK_REPEATS = 1000
_BENCHMARK_BLOCKS = 10
_PLANE_WAVE_X_CYCLES = 3
_PLANE_WAVE_Y_CYCLES = 2


def _circular_aperture_field(
    resolution: int,
    device: torch.device,
) -> torch.Tensor:
    coordinates = torch.linspace(-1.0, 1.0, resolution, device=device)
    y_grid, x_grid = torch.meshgrid(coordinates, coordinates, indexing="ij")
    aperture = x_grid.square() + y_grid.square() <= 0.18**2
    return aperture.to(torch.complex64).unsqueeze(0).unsqueeze(0)


def _plane_wave_field(
    resolution: int,
    device: torch.device,
) -> torch.Tensor:
    coordinates = torch.arange(resolution, dtype=torch.float32, device=device)
    y_grid, x_grid = torch.meshgrid(coordinates, coordinates, indexing="ij")
    phase = (
        2.0
        * torch.pi
        * (_PLANE_WAVE_X_CYCLES * x_grid + _PLANE_WAVE_Y_CYCLES * y_grid)
        / resolution
    )
    return torch.exp(1j * phase).to(torch.complex64).unsqueeze(0).unsqueeze(0)


@dataclass(frozen=True, slots=True)
class _Study:
    resolution: int
    device: torch.device
    layer: DiffractionLayer
    input_field: torch.Tensor
    output_fields: tuple[torch.Tensor, ...]
    transfer_amplitude: torch.Tensor
    transfer_phases: tuple[torch.Tensor, ...]
    device_difference: torch.Tensor | None
    benchmark: dict[str, float]


def _new_layer(
    resolution: int,
    device: torch.device,
    *,
    is_cache_enabled: bool = True,
) -> DiffractionLayer:
    return DiffractionLayer(
        wavelength=WAVELENGTH_M,
        pixel_size=PIXEL_SIZE_M,
        array_resolution=(resolution, resolution),
        is_cache_enabled=is_cache_enabled,
    ).to(device)


def _measure(*, device: str, size: str) -> _Study:
    resolved_device = resolve_device(device)
    resolution = size_to_resolution(size)
    layer = _new_layer(resolution, resolved_device)
    input_field = _circular_aperture_field(resolution, resolved_device)
    with torch.no_grad():
        output_fields = tuple(
            layer(input_field, distance).detach()
            for distance in _DISTANCES_M
        )
        transfer_amplitude = layer.get_transfer_function_information(
            _DISTANCES_M[0],
            "amplitude",
        )
        transfer_phases = tuple(
            layer.get_transfer_function_information(distance, "phase")
            for distance in _DISTANCES_M
        )
    return _Study(
        resolution=resolution,
        device=resolved_device,
        layer=layer,
        input_field=input_field,
        output_fields=output_fields,
        transfer_amplitude=transfer_amplitude,
        transfer_phases=transfer_phases,
        device_difference=_device_difference(input_field.detach().cpu()),
        benchmark=_benchmark_cache(resolution, _BENCHMARK_REPEATS),
    )


def _device_difference(input_field: torch.Tensor) -> torch.Tensor | None:
    if not torch.cuda.is_available():
        return None
    resolution = input_field.shape[-1]
    cpu_layer = _new_layer(resolution, torch.device("cpu"))
    gpu_layer = _new_layer(resolution, torch.device("cuda"))
    with torch.no_grad():
        cpu_output = cpu_layer(input_field, _PROPAGATION_DISTANCE_M)
        gpu_output = gpu_layer(
            input_field.cuda(),
            _PROPAGATION_DISTANCE_M,
        ).cpu()
    return torch.abs(cpu_output - gpu_output)


def _invalid_layer_rejected(
    resolution: int,
    *,
    wavelength: float = WAVELENGTH_M,
    pixel_size: float = PIXEL_SIZE_M,
    is_cache_enabled: bool = True,
) -> bool:
    try:
        DiffractionLayer(
            wavelength=wavelength,
            pixel_size=pixel_size,
            array_resolution=(resolution, resolution),
            is_cache_enabled=is_cache_enabled,
        )
    except ValueError:
        return True
    return False


def _construction_check(study: _Study) -> dict[str, object]:
    rejected = {
        "invalid_wavelength_rejected": _invalid_layer_rejected(
            study.resolution,
            wavelength=0.0,
        ),
        "invalid_pixel_size_rejected": _invalid_layer_rejected(
            study.resolution,
            pixel_size=0.0,
        ),
        "invalid_cache_flag_rejected": _invalid_layer_rejected(
            study.resolution,
            is_cache_enabled=1,  # type: ignore[arg-type]
        ),
    }
    output = study.output_fields[1]
    passed = (
        all(rejected.values())
        and output.shape == study.input_field.shape
        and output.dtype == torch.complex64
    )
    return layer_check("construction", passed, **rejected)


def _energy_check(study: _Study) -> dict[str, object]:
    input_energy = float(study.input_field.abs().square().sum())
    errors = tuple(
        abs(float(output.abs().square().sum()) - input_energy) / input_energy
        for output in study.output_fields
    )
    return layer_check(
        "energy_conservation",
        max(errors) <= 1e-5,
        input_energy=input_energy,
        energy_relative_error=max(errors),
    )


def _transfer_check(study: _Study) -> dict[str, object]:
    expected = study.layer.frequency_mask.to(study.transfer_amplitude.dtype)
    amplitude_error = finite_max_abs(study.transfer_amplitude - expected)
    phase_finite = all(bool(torch.isfinite(phase).all()) for phase in study.transfer_phases)
    return layer_check(
        "transfer_function",
        amplitude_error <= 1e-7 and phase_finite,
        transfer_amplitude_max_abs_error=amplitude_error,
        transfer_phase_finite=phase_finite,
        propagating_fraction=float(expected.mean()),
    )


def _plane_wave_check(study: _Study) -> dict[str, object]:
    plane_wave = _plane_wave_field(study.resolution, study.device)
    frequency_x = _PLANE_WAVE_X_CYCLES / (study.resolution * PIXEL_SIZE_M)
    frequency_y = _PLANE_WAVE_Y_CYCLES / (study.resolution * PIXEL_SIZE_M)
    normalized_wavevector_z = math.sqrt(
        1.0 - WAVELENGTH_M**2 * (frequency_x**2 + frequency_y**2),
    )
    phase_advance = (
        math.tau
        / WAVELENGTH_M
        * normalized_wavevector_z
        * _PROPAGATION_DISTANCE_M
    )
    expected = plane_wave * torch.exp(
        torch.tensor(
            1j * phase_advance,
            dtype=torch.complex64,
            device=study.device,
        ),
    )
    with torch.no_grad():
        actual = study.layer(plane_wave, _PROPAGATION_DISTANCE_M)
    error = finite_max_abs(actual - expected)
    return layer_check(
        "plane_wave_phase",
        error <= 2e-4,
        plane_wave_max_abs_error=error,
    )


def _cache_check(study: _Study) -> dict[str, object]:
    cached = _new_layer(study.resolution, study.device, is_cache_enabled=True)
    uncached = _new_layer(study.resolution, study.device, is_cache_enabled=False)
    input_field = study.input_field.detach().clone().requires_grad_(True)
    cached_output = cached(input_field, _PROPAGATION_DISTANCE_M)
    cached_output.abs().square().mean().backward()
    assert input_field.grad is not None
    cached_gradient = input_field.grad.detach().clone()
    input_field.grad = None
    uncached_output = uncached(input_field, _PROPAGATION_DISTANCE_M)
    uncached_output.abs().square().mean().backward()
    assert input_field.grad is not None
    output_error = finite_max_abs(cached_output - uncached_output)
    gradient_error = finite_max_abs(cached_gradient - input_field.grad)
    cached(study.input_field, _PROPAGATION_DISTANCE_M)
    cache_stats = cached.get_cache_statistics()
    return layer_check(
        "cache_contract",
        output_error <= 1e-7
        and gradient_error <= 1e-7
        and int(cache_stats["hits"]) >= 1,
        cache_repeat_max_abs_error=output_error,
        cache_gradient_max_abs_error=gradient_error,
        cpu_forward_cache_speedup=study.benchmark["cpu_forward_speedup"],
        cpu_training_cache_speedup=study.benchmark["cpu_training_speedup"],
        **{
            key: value
            for key, value in study.benchmark.items()
            if key not in {"cpu_forward_speedup", "cpu_training_speedup"}
        },
    )


def _autograd_check(study: _Study) -> dict[str, object]:
    input_field = study.input_field.detach().clone().requires_grad_(True)
    study.layer(input_field, _PROPAGATION_DISTANCE_M).real.mean().backward()
    gradient = input_field.grad
    assert gradient is not None
    maximum = finite_max_abs(gradient)
    return layer_check(
        "autograd_input_gradient",
        bool(torch.isfinite(gradient).all()) and maximum > 0.0,
        input_gradient_max_abs=maximum,
    )


def _cpu_gpu_check(study: _Study) -> dict[str, object]:
    if study.device_difference is None:
        return layer_check("cpu_gpu_consistency", None, detail="CUDA unavailable")
    maximum = finite_max_abs(study.device_difference)
    return layer_check(
        "cpu_gpu_consistency",
        maximum <= 2e-5,
        cpu_gpu_max_abs_error=maximum,
        cpu_gpu_mean_abs_error=float(study.device_difference.mean()),
    )


def _checks(study: _Study) -> list[dict[str, object]]:
    return [
        _construction_check(study),
        _energy_check(study),
        _transfer_check(study),
        _plane_wave_check(study),
        _cache_check(study),
        _autograd_check(study),
        _cpu_gpu_check(study),
    ]


def _block_sizes(repeats: int) -> tuple[int, ...]:
    block_count = min(_BENCHMARK_BLOCKS, repeats)
    quotient, remainder = divmod(repeats, block_count)
    return tuple(
        quotient + int(index < remainder)
        for index in range(block_count)
    )


def _synchronize(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def _benchmark_condition(
    resolution: int,
    device: torch.device,
    repeats: int,
    *,
    is_cold: bool,
    includes_backward: bool,
) -> tuple[float, float]:
    layer = _new_layer(resolution, device, is_cache_enabled=True)
    field = _circular_aperture_field(resolution, device)
    if includes_backward:
        field.requires_grad_(True)
    if not is_cold:
        with torch.no_grad():
            layer(field.detach(), _PROPAGATION_DISTANCE_M)

    def call() -> None:
        if is_cold:
            layer._clear_cache()
        if includes_backward:
            output = layer(field, _PROPAGATION_DISTANCE_M)
            output.abs().square().mean().backward()
            field.grad = None
            return
        with torch.no_grad():
            layer(field, _PROPAGATION_DISTANCE_M)

    samples = []
    for block_size in _block_sizes(repeats):
        _synchronize(device)
        started = time.perf_counter()
        for _ in range(block_size):
            call()
        _synchronize(device)
        samples.append((time.perf_counter() - started) * 1000.0 / block_size)
    values = np.asarray(samples)
    return float(np.median(values)), float(np.percentile(values, 75) - np.percentile(values, 25))


def _benchmark_device(
    resolution: int,
    device: torch.device,
    repeats: int,
) -> dict[str, float]:
    results: dict[str, float] = {}
    for operation, includes_backward in (
        ("forward", False),
        ("training", True),
    ):
        for cache_state, is_cold in (("cold", True), ("warm", False)):
            median, iqr = _benchmark_condition(
                resolution,
                device,
                repeats,
                is_cold=is_cold,
                includes_backward=includes_backward,
            )
            results[f"{device.type}_{operation}_{cache_state}_ms"] = median
            results[f"{device.type}_{operation}_{cache_state}_iqr_ms"] = iqr
        results[f"{device.type}_{operation}_speedup"] = (
            results[f"{device.type}_{operation}_cold_ms"]
            / results[f"{device.type}_{operation}_warm_ms"]
        )
    return results


def _benchmark_cache(resolution: int, repeats: int) -> dict[str, float]:
    if repeats <= 0:
        message = "benchmark repeats must be positive"
        raise ValueError(message)
    benchmark = _benchmark_device(resolution, torch.device("cpu"), repeats)
    if torch.cuda.is_available():
        benchmark.update(
            _benchmark_device(resolution, torch.device("cuda"), repeats),
        )
    return benchmark


def _save_propagation_response(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    intensities = (study.input_field.abs().square(),) + tuple(
        output.abs().square()
        for output in study.output_fields
    )
    maximum = max(float(image.max()) for image in intensities)
    fig = plt.figure(figsize=validation_figure_size("diffraction_propagation_response"))
    plot_shared_image_grid(
        fig,
        images=intensities,
        titles=("Circular Aperture", *_DISTANCE_LABELS),
        shape=(2, 2),
        cmap="optical_intensity",
        label="Intensity",
        vmin=0.0,
        vmax=maximum,
        axes_pad=0.28,
    )
    fig.suptitle("Propagation Response")
    return save_figure_pair(fig, output_dir, "propagation_response")


def _save_transfer_evolution(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    fig, axes = plt.subplots(
        2,
        2,
        figsize=validation_figure_size("diffraction_transfer_evolution"),
        constrained_layout=True,
    )
    amplitude_handle = axes[0, 0].imshow(
        tensor_to_numpy(study.transfer_amplitude),
        cmap="gray",
        vmin=0.0,
        vmax=1.0,
    )
    axes[0, 0].set_title("Transfer Amplitude")
    phase_handle = None
    for axis, phase, label in zip(
        (axes[0, 1], axes[1, 0], axes[1, 1]),
        study.transfer_phases,
        _DISTANCE_LABELS,
        strict=True,
    ):
        phase_handle = axis.imshow(
            tensor_to_numpy(phase),
            cmap=resolve_validation_cmap("phase_wrapped"),
            vmin=-math.pi,
            vmax=math.pi,
        )
        axis.set_title(f"Phase at {label}")
    for axis in axes.flat:
        axis.set_xticks([])
        axis.set_yticks([])
    amplitude_colorbar = fig.colorbar(
        amplitude_handle,
        ax=axes[0, 0],
        fraction=0.046,
        pad=0.04,
    )
    amplitude_colorbar.set_label("Amplitude")
    style_validation_colorbar(amplitude_colorbar)
    assert phase_handle is not None
    phase_colorbar = fig.colorbar(
        phase_handle,
        ax=(axes[0, 1], axes[1, 0], axes[1, 1]),
        fraction=0.025,
        pad=0.04,
    )
    phase_colorbar.set_label("Phase (rad)")
    style_validation_colorbar(phase_colorbar)
    fig.suptitle("Transfer Evolution")
    return save_figure_pair(fig, output_dir, "transfer_evolution")


def _save_device_agreement(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    difference = study.device_difference
    if difference is None:
        return save_device_agreement_figure(output_dir)
    return save_device_agreement_figure(
        output_dir,
        difference=difference,
        mean_abs_error=float(difference.mean()),
        max_abs_error=finite_max_abs(difference),
    )


def _bar_values(
    benchmark: dict[str, float],
    operation: str,
) -> tuple[list[str], list[float], list[float]]:
    devices = ["cpu"] + (["cuda"] if f"cuda_{operation}_cold_ms" in benchmark else [])
    cold = [benchmark[f"{device}_{operation}_cold_ms"] for device in devices]
    warm = [benchmark[f"{device}_{operation}_warm_ms"] for device in devices]
    return [device.upper() for device in devices], cold, warm


def _save_cache_performance(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    fig, axes = plt.subplots(
        1,
        2,
        figsize=validation_figure_size("diffraction_cache_performance"),
        constrained_layout=True,
    )
    for axis, operation, title in zip(
        axes,
        ("forward", "training"),
        ("Forward", "Forward + Backward"),
        strict=True,
    ):
        labels, cold, warm = _bar_values(study.benchmark, operation)
        positions = np.arange(len(labels))
        width = 0.34
        axis.bar(
            positions - width / 2,
            cold,
            width,
            label="Cold",
            color=VALIDATION_PALETTE["neutral"],
            edgecolor=VALIDATION_PALETTE["primary"],
        )
        axis.bar(
            positions + width / 2,
            warm,
            width,
            label="Warm",
            color=VALIDATION_PALETTE["primary_fill"],
            edgecolor=VALIDATION_PALETTE["primary"],
        )
        axis.set_title(title)
        axis.set_xticks(positions, labels)
        axis.set_ylabel("Latency (ms per call)")
        style_validation_grid(axis, grid_axis="y", level="subtle")
    axes[0].legend()
    fig.suptitle(f"Cache Performance — {_BENCHMARK_REPEATS} evaluations per condition")
    return save_figure_pair(fig, output_dir, "cache_performance")


def run(
    output_root: str | Path,
    *,
    device: str = "auto",
    seed: int = 42,
    size: str = "middle",
) -> dict[str, object]:
    """
    验证衍射层的传播、传递函数、设备一致性与缓存性能
    """
    torch.manual_seed(seed)
    setup_plot_style()
    output_dir = clear_output_dir(Path(output_root) / _LAYER_NAME)
    study = _measure(device=device, size=size)
    checks = _checks(study)
    status = aggregate_status(checks)
    metrics = metric_rows(_LAYER_NAME, checks)
    figure_savers = {
        "propagation_response": _save_propagation_response,
        "transfer_evolution": _save_transfer_evolution,
        "device_agreement": _save_device_agreement,
        "cache_performance": _save_cache_performance,
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
                f"- Pixel size: {PIXEL_SIZE_M:g} m",
                "- Input: centered circular aperture",
                "- Method: angular spectrum propagation",
                f"- Cache benchmark: {_BENCHMARK_REPEATS} evaluations per condition",
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
    解析命令行参数并运行衍射层验证
    """
    parser = argparse.ArgumentParser(description="Validate DiffractionLayer.")
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

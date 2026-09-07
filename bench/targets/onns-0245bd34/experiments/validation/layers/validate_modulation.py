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
    resolve_device,
    size_to_resolution,
    summary_lines,
)
from experiments.validation.style import (
    plot_shared_image_grid,
    save_device_agreement_figure,
    save_figure_pair,
    setup_plot_style,
    validation_figure_size,
)
from layers import ModulationLayer

_LAYER_NAME = "modulation"
_FIGURE_NAMES = (
    "phase_construction",
    "trainable_phase_action",
    "device_agreement",
)
_INITIALIZATIONS = ("normal", "zeros", "uniform")
_PARAMETERIZATIONS = ("direct", "sigmoid")
_TWO_PI = float(2.0 * torch.pi)


@dataclass(frozen=True, slots=True)
class _Study:
    resolution: int
    device: torch.device
    input_field: torch.Tensor
    latent_parameter: torch.Tensor
    direct_layer: ModulationLayer
    sigmoid_layer: ModulationLayer
    direct_phase: torch.Tensor
    sigmoid_phase: torch.Tensor
    direct_output: torch.Tensor
    sigmoid_output: torch.Tensor
    construction_phases: tuple[torch.Tensor, ...]
    direct_device_difference: torch.Tensor | None
    sigmoid_device_difference: torch.Tensor | None


def _new_layer(
    resolution: int,
    parameterization: str,
    initialization: str,
    device: torch.device,
) -> ModulationLayer:
    return ModulationLayer(
        array_resolution=(resolution, resolution),
        phase_parameterization=parameterization,
        phase_initialization=initialization,
    ).to(device)


def _paired_layers(
    resolution: int,
    initialization: str,
    device: torch.device,
) -> tuple[ModulationLayer, ModulationLayer]:
    source = _new_layer(resolution, "direct", initialization, device)
    latent_parameter = source.modulation_phase.detach().clone()
    direct = _new_layer(resolution, "direct", initialization, device)
    sigmoid = _new_layer(resolution, "sigmoid", initialization, device)
    with torch.no_grad():
        direct.modulation_phase.copy_(latent_parameter)
        sigmoid.modulation_phase.copy_(latent_parameter)
    return direct, sigmoid


def _measure(*, device: str, size: str) -> _Study:
    resolved_device = resolve_device(device)
    resolution = size_to_resolution(size)
    pairs = {
        initialization: _paired_layers(
            resolution,
            initialization,
            resolved_device,
        )
        for initialization in _INITIALIZATIONS
    }
    direct_layer, sigmoid_layer = pairs["normal"]
    input_field = gaussian_field(resolution, resolved_device) * grating_field(
        resolution,
        resolved_device,
        cycles=2.0,
    )
    with torch.no_grad():
        direct_phase = direct_layer.get_modulation_phase_information()
        sigmoid_phase = sigmoid_layer.get_modulation_phase_information()
        direct_output = direct_layer(input_field)
        sigmoid_output = sigmoid_layer(input_field)
        construction_phases = tuple(
            pairs[initialization][parameterization_index]
            .get_modulation_phase_information()
            .detach()
            for parameterization_index in range(len(_PARAMETERIZATIONS))
            for initialization in _INITIALIZATIONS
        )
    direct_difference, sigmoid_difference = _device_differences(
        input_field.detach().cpu(),
        direct_layer.modulation_phase.detach().cpu(),
    )
    return _Study(
        resolution=resolution,
        device=resolved_device,
        input_field=input_field,
        latent_parameter=direct_layer.modulation_phase.detach(),
        direct_layer=direct_layer,
        sigmoid_layer=sigmoid_layer,
        direct_phase=direct_phase.detach(),
        sigmoid_phase=sigmoid_phase.detach(),
        direct_output=direct_output.detach(),
        sigmoid_output=sigmoid_output.detach(),
        construction_phases=construction_phases,
        direct_device_difference=direct_difference,
        sigmoid_device_difference=sigmoid_difference,
    )


def _device_differences(
    input_field: torch.Tensor,
    latent_parameter: torch.Tensor,
) -> tuple[torch.Tensor | None, torch.Tensor | None]:
    if not torch.cuda.is_available():
        return None, None
    resolution = input_field.shape[-1]
    differences = []
    for parameterization in _PARAMETERIZATIONS:
        cpu_layer = _new_layer(
            resolution,
            parameterization,
            "zeros",
            torch.device("cpu"),
        )
        gpu_layer = _new_layer(
            resolution,
            parameterization,
            "zeros",
            torch.device("cuda"),
        )
        with torch.no_grad():
            cpu_layer.modulation_phase.copy_(latent_parameter)
            gpu_layer.modulation_phase.copy_(latent_parameter.cuda())
            cpu_output = cpu_layer(input_field)
            gpu_output = gpu_layer(input_field.cuda()).cpu()
        differences.append(torch.abs(cpu_output - gpu_output))
    return differences[0], differences[1]


def _invalid_option_rejected(
    resolution: int,
    *,
    initialization: str = "zeros",
    parameterization: str = "direct",
) -> bool:
    try:
        _new_layer(
            resolution,
            parameterization,
            initialization,
            torch.device("cpu"),
        )
    except ValueError:
        return True
    return False


def _construction_check(study: _Study) -> dict[str, object]:
    invalid_initialization = _invalid_option_rejected(
        study.resolution,
        initialization="invalid",
    )
    invalid_parameterization = _invalid_option_rejected(
        study.resolution,
        parameterization="invalid",
    )
    return layer_check(
        "construction",
        len(study.construction_phases) == 6
        and invalid_initialization
        and invalid_parameterization,
        supported_combination_count=len(study.construction_phases),
        invalid_initialization_rejected=invalid_initialization,
        invalid_parameterization_rejected=invalid_parameterization,
    )


def _phase_check(study: _Study) -> dict[str, object]:
    expected_direct = torch.remainder(study.latent_parameter * _TWO_PI, _TWO_PI)
    expected_sigmoid = torch.sigmoid(study.latent_parameter) * _TWO_PI
    direct_error = finite_max_abs(study.direct_phase - expected_direct)
    sigmoid_error = finite_max_abs(study.sigmoid_phase - expected_sigmoid)
    in_range = all(
        float(phase.min()) >= 0.0 and float(phase.max()) <= _TWO_PI + 1e-6
        for phase in study.construction_phases
    )
    return layer_check(
        "phase_generation",
        max(direct_error, sigmoid_error) <= 1e-6 and in_range,
        direct_phase_max_abs_error=direct_error,
        sigmoid_phase_max_abs_error=sigmoid_error,
    )


def _amplitude_check(study: _Study) -> dict[str, object]:
    input_amplitude = study.input_field.abs()
    error = max(
        finite_max_abs(study.direct_output.abs() - input_amplitude),
        finite_max_abs(study.sigmoid_output.abs() - input_amplitude),
    )
    return layer_check(
        "amplitude_preservation",
        error <= 1e-6,
        amplitude_max_abs_error=error,
    )


def _feature_check(study: _Study) -> dict[str, object]:
    outputs = (study.direct_output, study.sigmoid_output)
    passed = all(
        output.shape == study.input_field.shape
        and output.dtype == torch.complex64
        and bool(torch.isfinite(output).all())
        for output in outputs
    )
    return layer_check(
        "feature_contract",
        passed,
        output_shape=tuple(study.direct_output.shape),
        output_dtype=str(study.direct_output.dtype),
        outputs_finite=all(bool(torch.isfinite(output).all()) for output in outputs),
    )


def _autograd_check(study: _Study) -> dict[str, object]:
    study.sigmoid_layer.zero_grad(set_to_none=True)
    study.sigmoid_layer(study.input_field).real.mean().backward()
    gradient = study.sigmoid_layer.modulation_phase.grad
    assert gradient is not None
    maximum = finite_max_abs(gradient)
    return layer_check(
        "autograd_parameter_gradient",
        bool(torch.isfinite(gradient).all()) and maximum > 0.0,
        modulation_phase_gradient_max_abs=maximum,
    )


def _cpu_gpu_check(study: _Study) -> dict[str, object]:
    if (
        study.direct_device_difference is None
        or study.sigmoid_device_difference is None
    ):
        return layer_check("cpu_gpu_consistency", None, detail="CUDA unavailable")
    direct_error = finite_max_abs(study.direct_device_difference)
    sigmoid_error = finite_max_abs(study.sigmoid_device_difference)
    return layer_check(
        "cpu_gpu_consistency",
        max(direct_error, sigmoid_error) <= 1e-5,
        cpu_gpu_direct_max_abs_error=direct_error,
        cpu_gpu_sigmoid_max_abs_error=sigmoid_error,
    )


def _checks(study: _Study) -> list[dict[str, object]]:
    return [
        _construction_check(study),
        _phase_check(study),
        _amplitude_check(study),
        _feature_check(study),
        _autograd_check(study),
        _cpu_gpu_check(study),
    ]


def _save_phase_construction(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    fig = plt.figure(figsize=validation_figure_size("modulation_phase_construction"))
    axes = plot_shared_image_grid(
        fig,
        images=study.construction_phases,
        titles=("Normal", "Zeros", "Uniform", "", "", ""),
        shape=(2, 3),
        cmap="phase_wrapped",
        label="Effective phase (rad)",
        vmin=0.0,
        vmax=_TWO_PI,
        axes_pad=0.24,
    )
    axes[0].set_ylabel("Direct")
    axes[3].set_ylabel("Sigmoid")
    fig.suptitle("Phase Construction")
    return save_figure_pair(fig, output_dir, "phase_construction")


def _save_trainable_phase_action(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    effective_phase = torch.angle(torch.exp(1j * study.sigmoid_phase))
    fig = plt.figure(
        figsize=validation_figure_size("modulation_trainable_phase_action"),
    )
    plot_shared_image_grid(
        fig,
        images=(
            torch.angle(study.input_field),
            effective_phase,
            torch.angle(study.sigmoid_output),
        ),
        titles=("Input Phase", "Effective Phase", "Output Phase"),
        shape=(1, 3),
        cmap="phase_wrapped",
        label="Phase (rad)",
        vmin=-math.pi,
        vmax=math.pi,
        axes_pad=0.28,
    )
    fig.suptitle("Trainable Phase Action")
    return save_figure_pair(fig, output_dir, "trainable_phase_action")


def _save_device_agreement(
    output_dir: Path,
    study: _Study,
) -> dict[str, str]:
    difference = study.sigmoid_device_difference
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
    验证调制层的相位构建、前向作用与设备一致性
    """
    torch.manual_seed(seed)
    setup_plot_style()
    output_dir = clear_output_dir(Path(output_root) / _LAYER_NAME)
    study = _measure(device=device, size=size)
    checks = _checks(study)
    status = aggregate_status(checks)
    metrics = metric_rows(_LAYER_NAME, checks)
    figure_savers = {
        "phase_construction": _save_phase_construction,
        "trainable_phase_action": _save_trainable_phase_action,
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
                "- Initializations: normal, zeros, uniform",
                "- Direct phase: remainder(2πp, 2π)",
                "- Sigmoid phase: 2π sigmoid(p)",
                "- Forward response: trainable phase-only modulation",
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
    解析命令行参数并运行调制层验证
    """
    parser = argparse.ArgumentParser(description="Validate ModulationLayer.")
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

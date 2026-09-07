from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import torch

from data.configs import (
    AdditiveGaussianNoiseConfig,
    CannyEdgesConfig,
    DefocusBlurConfig,
    GaussianBlurConfig,
    LaplacianOfGaussianEdgesConfig,
    PerturbationConfig,
    PoissonGaussianNoiseConfig,
    PsfConvolutionConfig,
    SobelEdgesConfig,
)
from data.perturbation.dataset import PerturbedDataset
from data.perturbation.optics.circular_pupil_functions import (
    build_circular_pupil_function,
)
from data.perturbation.optics.coherent_imaging import (
    point_spread_function_from_pupil_function,
)
from experiments.validation.data.data_validation_utils import (
    clear_output_dir,
    data_check,
    plot_image_with_colorbar,
    save_figure_pair,
    setup_plot_style,
    tensor_image_to_numpy,
    title_from_figure_name,
    validation_figure_size,
    validation_panel_figure_size,
    write_metrics,
    write_summary,
)
from experiments.validation.layers.validation_utils import aggregate_status

VALIDATOR_NAME = "degradation_scenarios"
IMAGE_RESOLUTION = 64
GAUSSIAN_NOISE_SIGMAS = (0.0, 0.03, 0.08, 0.15)
POISSON_GAUSSIAN_SCENARIOS = (
    (200.0, 0.0),
    (80.0, 0.005),
    (30.0, 0.01),
    (12.0, 0.02),
)
GAUSSIAN_BLUR_KERNEL_SIZES = (1, 3, 5, 9)
DEFOCUS_RADII = (1, 2, 4, 6)
FIGURE_NAMES = (
    "01_gaussian_noise_strength_grid",
    "02_poisson_gaussian_strength_grid",
    "03_blur_strength_grid",
    "04_defocus_strength_grid",
    "05_psf_convolution_trace",
    "06_edge_operator_grid",
)
EXPECTED_OPERATION_NAMES = {
    "add_additive_gaussian_noise",
    "add_poisson_gaussian_noise",
    "apply_gaussian_blur",
    "apply_defocus_blur",
    "apply_psf_kernel",
    "build_canny_edge_map",
    "build_sobel_edge_map",
    "build_laplacian_of_gaussian_edge_map",
}


@dataclass(slots=True, frozen=True)
class _ScenarioResult:
    scenario: str
    image: np.ndarray
    clean_image: np.ndarray
    operation_record: dict[str, object]
    perturbation: dict[str, object]


class _SyntheticPreparedDataset:
    def __init__(
        self,
        *,
        image: np.ndarray,
        source_name: str,
        source_index: int,
        seed: int,
    ) -> None:
        """
        绑定单张synthetic prepared图像及其provenance参数
        """
        self._image = image.astype(np.float32, copy=True)
        self._source_name = source_name
        self._source_index = source_index
        self._seed = seed

    def __len__(self) -> int:
        """
        返回固定synthetic样本数
        """
        return 1

    def __getitem__(self, index: int) -> dict[str, object]:
        """
        返回用于扰动验证的prepared样本
        """
        image = torch.from_numpy(self._image.copy()).unsqueeze(0)
        return {
            "image": image,
            "label": self._source_index,
            "category": self._source_name,
            "provenance": {
                "dataset_name": f"synthetic_{self._source_name}",
                "split_name": "validation",
                "source_index": self._source_index,
                "sampled_index": index,
                "sampling_seed": self._seed,
                "raw_resolution": self._image.shape,
                "stage": "prepared",
            },
        }


def _smooth_microscopy_like_image(resolution: int = IMAGE_RESOLUTION) -> np.ndarray:
    coordinate = np.linspace(-1.0, 1.0, resolution, dtype=np.float32)
    y_grid, x_grid = np.meshgrid(coordinate, coordinate, indexing="ij")
    image = np.full((resolution, resolution), 0.12, dtype=np.float32)
    blobs = (
        (-0.45, -0.25, 0.42, 0.11),
        (0.32, -0.38, 0.35, 0.08),
        (-0.12, 0.30, 0.50, 0.14),
        (0.48, 0.34, 0.28, 0.07),
    )
    for center_x, center_y, amplitude, width in blobs:
        radius_squared = (x_grid - center_x) ** 2 + (y_grid - center_y) ** 2
        image += amplitude * np.exp(-radius_squared / (2.0 * width))
    texture = 0.035 * np.sin(18.0 * x_grid + 0.4) * np.cos(14.0 * y_grid)
    image = image + texture.astype(np.float32, copy=False)
    image = (image - float(image.min())) / float(image.max() - image.min())
    return (0.20 + 0.60 * image).astype(np.float32, copy=False)


def _line_pair_target(resolution: int = IMAGE_RESOLUTION) -> np.ndarray:
    image = np.full((resolution, resolution), 0.08, dtype=np.float32)
    x_coordinates = np.arange(resolution, dtype=np.int32)
    y_coordinates = np.arange(resolution, dtype=np.int32)

    for block_index, period in enumerate((2, 4, 8)):
        y_start = 6 + block_index * 18
        y_stop = y_start + 12
        stripe = ((x_coordinates // period) % 2).astype(np.float32)
        image[y_start:y_stop, 6:30] = 0.12 + 0.78 * stripe[6:30]

    for block_index, period in enumerate((2, 4, 8)):
        x_start = 36
        x_stop = 58
        y_start = 6 + block_index * 18
        y_stop = y_start + 12
        stripe = ((y_coordinates // period) % 2).astype(np.float32)
        image[y_start:y_stop, x_start:x_stop] = (
            0.12 + 0.78 * stripe[y_start:y_stop, None]
        )

    image[30:34, 30:34] = 1.0
    return image.astype(np.float32, copy=False)


def _mnist_like_centered_square(resolution: int = IMAGE_RESOLUTION) -> np.ndarray:
    image = np.zeros((resolution, resolution), dtype=np.float32)
    start = resolution // 2 - 12
    stop = resolution // 2 + 12
    image[start:stop, start:stop] = 0.82
    image[start + 5 : stop - 5, start + 5 : stop - 5] = 0.18
    image[start + 9 : stop - 9, start + 9 : stop - 9] = 0.95
    return image


def _apply_operation(
    *,
    image: np.ndarray,
    source_name: str,
    source_index: int,
    operation: object,
    seed: int,
    scenario: str,
) -> _ScenarioResult:
    dataset = PerturbedDataset(
        prepared_dataset=_SyntheticPreparedDataset(
            image=image,
            source_name=source_name,
            source_index=source_index,
            seed=seed,
        ),
        perturbation_config=PerturbationConfig(
            operations=(operation,),
            degradation_seed=seed,
        ),
    )
    sample = dataset[0]
    perturbation = sample["provenance"]["perturbation"]
    applied_operations = perturbation["applied_operations"]
    operation_record = applied_operations[0]
    return _ScenarioResult(
        scenario=scenario,
        image=tensor_image_to_numpy(sample["image"]),
        clean_image=tensor_image_to_numpy(sample["reference_image"]),
        operation_record=operation_record,
        perturbation=perturbation,
    )


def _json_text(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _gradient_energy(image: np.ndarray) -> float:
    gradient_y = np.diff(image, axis=0)
    gradient_x = np.diff(image, axis=1)
    return float(np.mean(np.abs(gradient_x)) + np.mean(np.abs(gradient_y)))


def _metric_row(
    result: _ScenarioResult,
    *,
    strength_metric: float | None = None,
    max_abs_error: float | None = None,
) -> dict[str, object]:
    values = result.image.astype(np.float32, copy=False)
    operation = str(result.operation_record["name"])
    parameters = result.operation_record.get("parameters", {})
    row: dict[str, object] = {
        "scenario": result.scenario,
        "operation": operation,
        "parameters": _json_text(parameters),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "operation_record": _json_text(result.operation_record),
    }
    if strength_metric is not None:
        row["strength_metric"] = strength_metric
    if max_abs_error is not None:
        row["max_abs_error"] = max_abs_error
    return row


def _plot_strength_grid(
    *,
    output_dir: Path,
    figure_name: str,
    images: Sequence[np.ndarray],
    titles: Sequence[str],
    cmap: str = "data_intensity",
) -> str:
    from matplotlib import pyplot as plt

    panel_width, panel_height = validation_figure_size("data_strength_grid_panel")
    fig, axes = plt.subplots(
        1,
        len(images),
        figsize=validation_panel_figure_size(
            columns=len(images),
            panel_width=panel_width,
            panel_height=panel_height,
        ),
    )
    axes_array = np.atleast_1d(axes)
    for axis, image, title in zip(axes_array, images, titles, strict=True):
        plot_image_with_colorbar(axis, image, title, cmap, vmin=0.0, vmax=1.0)
    fig.suptitle(title_from_figure_name(figure_name))
    save_figure_pair(fig, output_dir, figure_name)
    return figure_name


def _plot_psf_trace(
    *,
    output_dir: Path,
    clean_image: np.ndarray,
    psf: np.ndarray,
    degraded_image: np.ndarray,
) -> str:
    from matplotlib import pyplot as plt

    figure_name = "05_psf_convolution_trace"
    fig, axes = plt.subplots(1, 4, figsize=validation_figure_size("data_psf_trace"))
    plot_image_with_colorbar(
        axes[0],
        clean_image,
        "Input",
        "data_intensity",
        vmin=0.0,
        vmax=1.0,
    )
    plot_image_with_colorbar(axes[1], psf, "PSF", "psf")
    plot_image_with_colorbar(
        axes[2],
        degraded_image,
        "Convolved",
        "data_intensity",
        vmin=0.0,
        vmax=1.0,
    )
    plot_image_with_colorbar(
        axes[3],
        np.abs(degraded_image - clean_image),
        "Absolute Delta",
        "error",
    )
    fig.suptitle(title_from_figure_name(figure_name))
    save_figure_pair(fig, output_dir, figure_name)
    return figure_name


def _summary_lines(
    *,
    status: str,
    checks: Sequence[dict[str, object]],
    figures: Sequence[str],
) -> list[str]:
    lines = [
        "# Degradation Scenario Validation",
        "",
        f"Status: {status}",
        "Validator: degradation_scenarios",
        "",
        "## Checks",
    ]
    for check in checks:
        details = {
            key: value
            for key, value in check.items()
            if key not in {"name", "status"}
        }
        lines.append(
            f"- {check['name']}: {check['status']} - {_json_text(details)}"
        )
    lines.extend(["", "## Figures"])
    for figure in figures:
        lines.append(f"- {figure}.png / {figure}.svg")
    return lines


def run(
    output_root: str | Path,
    *,
    device: str = "auto",
    seed: int = 42,
    size: str = "tiny",
) -> dict[str, object]:
    """
    运行数据退化验证
    """
    del device
    if size not in {"tiny", "middle", "full"}:
        message = "size must be one of tiny, middle, or full"
        raise ValueError(message)

    torch.manual_seed(seed)
    np.random.seed(seed)
    setup_plot_style()

    output_dir = clear_output_dir(Path(output_root) / VALIDATOR_NAME)
    smooth_image = _smooth_microscopy_like_image()
    line_pair_image = _line_pair_target()
    square_image = _mnist_like_centered_square()

    metrics: list[dict[str, object]] = []
    figures: list[str] = []

    gaussian_results = [
        _apply_operation(
            image=smooth_image,
            source_name="smooth_microscopy",
            source_index=0,
            operation=AdditiveGaussianNoiseConfig(sigma=sigma),
            seed=seed,
            scenario=f"additive_sigma_{sigma:.3f}",
        )
        for sigma in GAUSSIAN_NOISE_SIGMAS
    ]
    gaussian_residuals = [
        float(np.std(result.image - result.clean_image)) for result in gaussian_results
    ]
    metrics.extend(
        _metric_row(result, strength_metric=strength_metric)
        for result, strength_metric in zip(
            gaussian_results,
            gaussian_residuals,
            strict=True,
        )
    )
    figures.append(
        _plot_strength_grid(
            output_dir=output_dir,
            figure_name="01_gaussian_noise_strength_grid",
            images=[result.image for result in gaussian_results],
            titles=[f"sigma={sigma:g}" for sigma in GAUSSIAN_NOISE_SIGMAS],
        )
    )

    poisson_results = [
        _apply_operation(
            image=smooth_image,
            source_name="smooth_microscopy",
            source_index=0,
            operation=PoissonGaussianNoiseConfig(
                peak_photons=peak_photons,
                read_noise_sigma=read_noise_sigma,
            ),
            seed=seed,
            scenario=(
                "poisson_gaussian_"
                f"photons_{peak_photons:g}_read_{read_noise_sigma:g}"
            ),
        )
        for peak_photons, read_noise_sigma in POISSON_GAUSSIAN_SCENARIOS
    ]
    poisson_residuals = [
        float(np.std(result.image - result.clean_image)) for result in poisson_results
    ]
    metrics.extend(
        _metric_row(result, strength_metric=strength_metric)
        for result, strength_metric in zip(
            poisson_results,
            poisson_residuals,
            strict=True,
        )
    )
    figures.append(
        _plot_strength_grid(
            output_dir=output_dir,
            figure_name="02_poisson_gaussian_strength_grid",
            images=[result.image for result in poisson_results],
            titles=[
                f"{peak_photons:g} ph, rn={read_noise_sigma:g}"
                for peak_photons, read_noise_sigma in POISSON_GAUSSIAN_SCENARIOS
            ],
        )
    )

    blur_results = [
        _apply_operation(
            image=line_pair_image,
            source_name="line_pair_target",
            source_index=1,
            operation=GaussianBlurConfig(kernel_size=kernel_size),
            seed=seed,
            scenario=f"gaussian_blur_kernel_{kernel_size}",
        )
        for kernel_size in GAUSSIAN_BLUR_KERNEL_SIZES
    ]
    blur_edge_energy = [_gradient_energy(result.image) for result in blur_results]
    metrics.extend(
        _metric_row(result, strength_metric=strength_metric)
        for result, strength_metric in zip(
            blur_results,
            blur_edge_energy,
            strict=True,
        )
    )
    figures.append(
        _plot_strength_grid(
            output_dir=output_dir,
            figure_name="03_blur_strength_grid",
            images=[result.image for result in blur_results],
            titles=[f"kernel={kernel_size}" for kernel_size in GAUSSIAN_BLUR_KERNEL_SIZES],
        )
    )

    defocus_results = [
        _apply_operation(
            image=line_pair_image,
            source_name="line_pair_target",
            source_index=1,
            operation=DefocusBlurConfig(radius=radius),
            seed=seed,
            scenario=f"defocus_radius_{radius}",
        )
        for radius in DEFOCUS_RADII
    ]
    defocus_edge_energy = [_gradient_energy(result.image) for result in defocus_results]
    metrics.extend(
        _metric_row(result, strength_metric=strength_metric)
        for result, strength_metric in zip(
            defocus_results,
            defocus_edge_energy,
            strict=True,
        )
    )
    figures.append(
        _plot_strength_grid(
            output_dir=output_dir,
            figure_name="04_defocus_strength_grid",
            images=[result.image for result in defocus_results],
            titles=[f"radius={radius}" for radius in DEFOCUS_RADII],
        )
    )

    pupil = build_circular_pupil_function(
        shape=(64, 64),
        radius_fraction=0.35,
    )
    psf = point_spread_function_from_pupil_function(pupil)
    psf_result = _apply_operation(
        image=square_image,
        source_name="mnist_square",
        source_index=2,
        operation=PsfConvolutionConfig(kernel=psf),
        seed=seed,
        scenario="psf_convolution_circular_pupil",
    )
    metrics.append(_metric_row(psf_result, strength_metric=_gradient_energy(psf_result.image)))
    figures.append(
        _plot_psf_trace(
            output_dir=output_dir,
            clean_image=psf_result.clean_image,
            psf=psf,
            degraded_image=psf_result.image,
        )
    )

    edge_operations = (
        ("canny", CannyEdgesConfig(threshold1=10.0, threshold2=20.0)),
        ("sobel", SobelEdgesConfig(kernel_size=3)),
        ("laplacian_of_gaussian", LaplacianOfGaussianEdgesConfig(kernel_size=3, sigma=0.0)),
    )
    edge_results = [
        _apply_operation(
            image=line_pair_image,
            source_name="line_pair_target",
            source_index=1,
            operation=operation,
            seed=seed,
            scenario=f"edge_{name}",
        )
        for name, operation in edge_operations
    ]
    metrics.extend(
        _metric_row(result, strength_metric=float(np.mean(result.image > 0.0)))
        for result in edge_results
    )
    figures.append(
        _plot_strength_grid(
            output_dir=output_dir,
            figure_name="06_edge_operator_grid",
            images=[line_pair_image, *[result.image for result in edge_results]],
            titles=["source", "Canny", "Sobel", "LoG"],
        )
    )

    deterministic_config = PerturbationConfig(
        operations=(AdditiveGaussianNoiseConfig(sigma=0.08),),
        degradation_seed=seed,
    )
    deterministic_dataset = _SyntheticPreparedDataset(
        image=smooth_image,
        source_name="smooth_microscopy",
        source_index=0,
        seed=seed,
    )
    first_repeat = PerturbedDataset(
        prepared_dataset=deterministic_dataset,
        perturbation_config=deterministic_config,
    )[0]
    second_repeat = PerturbedDataset(
        prepared_dataset=deterministic_dataset,
        perturbation_config=deterministic_config,
    )[0]
    max_abs_error = float(
        torch.max(torch.abs(first_repeat["image"] - second_repeat["image"])).item()
    )
    repeat_record = first_repeat["provenance"]["perturbation"]["applied_operations"][0]
    repeat_result = _ScenarioResult(
        scenario="deterministic_repeat",
        image=tensor_image_to_numpy(first_repeat["image"]),
        clean_image=tensor_image_to_numpy(first_repeat["reference_image"]),
        operation_record=repeat_record,
        perturbation=first_repeat["provenance"]["perturbation"],
    )
    metrics.append(_metric_row(repeat_result, max_abs_error=max_abs_error))

    all_results = [
        *gaussian_results,
        *poisson_results,
        *blur_results,
        *defocus_results,
        psf_result,
        *edge_results,
        repeat_result,
    ]
    operation_names = {
        str(result.operation_record["name"]) for result in all_results
    }
    poisson_records_have_seed = all(
        result.operation_record["parameters"].get("random_seed") is not None
        for result in poisson_results
    )
    additive_records_are_deterministic = all(
        result.perturbation.get("noise_rng", {}).get("mode") == "deterministic"
        for result in [*gaussian_results, repeat_result]
    )
    operation_records_match = all(
        result.operation_record.get("name") in EXPECTED_OPERATION_NAMES
        and isinstance(result.operation_record.get("parameters"), dict)
        for result in all_results
    )
    gaussian_monotonic = all(
        left <= right + 1e-6
        for left, right in zip(gaussian_residuals, gaussian_residuals[1:])
    )
    poisson_monotonic = all(
        left <= right + 1e-6
        for left, right in zip(poisson_residuals, poisson_residuals[1:])
    )
    blur_monotonic = all(
        left + 1e-6 >= right
        for left, right in zip(blur_edge_energy, blur_edge_energy[1:])
    )
    defocus_monotonic = all(
        left + 1e-6 >= right
        for left, right in zip(defocus_edge_energy, defocus_edge_energy[1:])
    )

    checks = [
        data_check(
            "noise_strength_control",
            gaussian_residuals[0] == 0.0 and gaussian_monotonic,
            residual_std=gaussian_residuals,
        ),
        data_check(
            "poisson_gaussian_strength_control",
            poisson_monotonic,
            residual_std=poisson_residuals,
        ),
        data_check(
            "blur_strength_control",
            blur_edge_energy[-1] < blur_edge_energy[0] and blur_monotonic,
            gradient_energy=blur_edge_energy,
        ),
        data_check(
            "defocus_strength_control",
            defocus_edge_energy[-1] < defocus_edge_energy[0] and defocus_monotonic,
            gradient_energy=defocus_edge_energy,
        ),
        data_check(
            "psf_convolution_contract",
            psf.shape == (64, 64)
            and np.isclose(float(psf.sum()), 1.0)
            and psf_result.operation_record["name"] == "apply_psf_kernel"
            and psf_result.image.shape == square_image.shape
            and bool(np.isfinite(psf_result.image).all()),
            psf_shape=psf.shape,
            psf_sum=float(psf.sum()),
        ),
        data_check(
            "edge_operator_contract",
            {result.operation_record["name"] for result in edge_results}
            == {
                "build_canny_edge_map",
                "build_sobel_edge_map",
                "build_laplacian_of_gaussian_edge_map",
            }
            and all(bool(np.isfinite(result.image).all()) for result in edge_results)
            and all(result.image.shape == line_pair_image.shape for result in edge_results),
            edge_operations=[result.operation_record["name"] for result in edge_results],
        ),
        data_check(
            "deterministic_degradation_seed",
            max_abs_error == 0.0,
            max_abs_error=max_abs_error,
        ),
        data_check(
            "operation_provenance_contract",
            operation_names >= EXPECTED_OPERATION_NAMES
            and poisson_records_have_seed
            and additive_records_are_deterministic
            and operation_records_match,
            operation_names=sorted(operation_names),
            poisson_random_seed_recorded=poisson_records_have_seed,
            additive_noise_rng_mode="deterministic",
        ),
    ]
    status = aggregate_status(checks)

    write_metrics(output_dir, metrics)
    write_summary(
        output_dir,
        _summary_lines(status=status, checks=checks, figures=figures),
    )

    return {
        "data": VALIDATOR_NAME,
        "status": status,
        "checks": checks,
        "metrics": metrics,
        "figures": figures,
        "output_dir": str(output_dir),
    }


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    解析命令行并运行数据退化验证
    """
    parser = argparse.ArgumentParser(description="Run degradation scenario validation.")
    parser.add_argument("--output-root", type=Path, default=Path("results/validation/data"))
    parser.add_argument("--device", default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--size", choices=("tiny", "middle", "full"), default="tiny")
    args = parser.parse_args(argv)
    return run(
        output_root=args.output_root,
        device=args.device,
        seed=args.seed,
        size=args.size,
    )


if __name__ == "__main__":
    main()

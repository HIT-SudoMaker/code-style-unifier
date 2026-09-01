from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from data.configs import (
    AdditiveGaussianNoiseConfig,
    DefocusBlurConfig,
    GaussianBlurConfig,
    PerturbationConfig,
    PoissonGaussianNoiseConfig,
    PsfConvolutionConfig,
)
from data.encoding.dataset import EncodedDataset
from data.perturbation.dataset import PerturbedDataset
from data.perturbation.optics.circular_pupil_functions import (
    build_circular_pupil_function,
)
from data.perturbation.optics.coherent_imaging import (
    point_spread_function_from_pupil_function,
)
from data.preparation.dataset import PreparedDataset
from experiments.validation.data.data_validation_utils import (
    build_raw_dataset,
    clear_output_dir,
    data_check,
    plot_image_with_colorbar,
    save_figure_pair,
    setup_plot_style,
    shape_text,
    validation_figure_size,
    write_metrics,
    write_summary,
)

_VALIDATOR_NAME = "end_to_end_pipeline"
_SAMPLE_COUNT = 3
_IMAGE_RESOLUTION = (64, 64)
_ARRAY_RESOLUTION = (128, 128)
_OPERATOR_FAMILY_FIGURE_NAME = "01_end_to_end_operator_family_grid"
_RESTORATION_RECIPE_FIGURE_NAME = "02_restoration_recipe_grid"
_EDGE_OPERATION_NAMES = {
    "build_canny_edge_map",
    "build_sobel_edge_map",
    "build_laplacian_of_gaussian_edge_map",
}


@dataclass(frozen=True, slots=True)
class _PipelineRecipe:
    name: str
    operations: tuple[object, ...]


def _build_psf_kernel() -> np.ndarray:
    pupil = build_circular_pupil_function(
        shape=(64, 64),
        radius_fraction=0.35,
    )
    return point_spread_function_from_pupil_function(pupil)


def _operator_family_recipes() -> tuple[_PipelineRecipe, ...]:
    psf_kernel = _build_psf_kernel()
    return (
        _PipelineRecipe(
            name="additive_gaussian_noise",
            operations=(AdditiveGaussianNoiseConfig(sigma=0.05),),
        ),
        _PipelineRecipe(
            name="poisson_gaussian_noise",
            operations=(
                PoissonGaussianNoiseConfig(
                    peak_photons=40.0,
                    read_noise_sigma=0.01,
                ),
            ),
        ),
        _PipelineRecipe(
            name="gaussian_blur",
            operations=(GaussianBlurConfig(kernel_size=5),),
        ),
        _PipelineRecipe(
            name="defocus_blur",
            operations=(DefocusBlurConfig(radius=3),),
        ),
        _PipelineRecipe(
            name="psf_convolution",
            operations=(PsfConvolutionConfig(kernel=psf_kernel),),
        ),
    )


def _restoration_recipes() -> tuple[_PipelineRecipe, ...]:
    return (
        _PipelineRecipe(
            name="noise",
            operations=(
                PoissonGaussianNoiseConfig(
                    peak_photons=40.0,
                    read_noise_sigma=0.01,
                ),
            ),
        ),
        _PipelineRecipe(
            name="blur",
            operations=(GaussianBlurConfig(kernel_size=5),),
        ),
        _PipelineRecipe(
            name="defocus",
            operations=(DefocusBlurConfig(radius=3),),
        ),
        _PipelineRecipe(
            name="combined_degradation",
            operations=(
                DefocusBlurConfig(radius=2),
                PoissonGaussianNoiseConfig(
                    peak_photons=40.0,
                    read_noise_sigma=0.01,
                ),
            ),
        ),
    )


def _aggregate_status(checks: Sequence[dict[str, object]]) -> str:
    return "FAIL" if any(check["status"] == "FAIL" for check in checks) else "PASS"


def _operation_records(sample: dict[str, object]) -> list[dict[str, object]]:
    provenance = sample.get("provenance", {})
    if not isinstance(provenance, dict):
        return []
    perturbation = provenance.get("perturbation", {})
    if not isinstance(perturbation, dict):
        return []
    operations = perturbation.get("applied_operations", [])
    if not isinstance(operations, list):
        return []
    return [
        operation
        for operation in operations
        if isinstance(operation, dict)
    ]


def _operation_names(sample: dict[str, object]) -> tuple[str, ...]:
    return tuple(str(operation.get("name", "")) for operation in _operation_records(sample))


def _provenance_keys(sample: dict[str, object]) -> str:
    provenance = sample.get("provenance", {})
    if not isinstance(provenance, dict):
        return ""
    return ";".join(sorted(str(key) for key in provenance.keys()))


def _max_abs_error(left: torch.Tensor, right: torch.Tensor) -> float:
    return float(torch.max(torch.abs(left.detach().cpu() - right.detach().cpu())))


def _build_encoded_datasets(
    prepared_dataset: PreparedDataset,
    recipes: Sequence[_PipelineRecipe],
    *,
    seed: int,
) -> dict[str, EncodedDataset]:
    encoded_datasets: dict[str, EncodedDataset] = {}
    for recipe in recipes:
        perturbed_dataset = PerturbedDataset(
            prepared_dataset=prepared_dataset,
            perturbation_config=PerturbationConfig(
                operations=recipe.operations,
                degradation_seed=seed,
            ),
        )
        encoded_datasets[recipe.name] = EncodedDataset(
            source_dataset=perturbed_dataset,
            encoding_method="intensity",
        )
    return encoded_datasets


def _collect_samples(
    prepared_dataset: PreparedDataset,
    encoded_datasets: dict[str, EncodedDataset],
    recipes: Sequence[_PipelineRecipe],
) -> tuple[list[dict[str, object]], dict[int, dict[str, dict[str, object]]]]:
    prepared_samples = [prepared_dataset[index] for index in range(_SAMPLE_COUNT)]
    encoded_samples: dict[int, dict[str, dict[str, object]]] = {}
    for sample_index in range(_SAMPLE_COUNT):
        encoded_samples[sample_index] = {
            recipe.name: encoded_datasets[recipe.name][sample_index]
            for recipe in recipes
        }
    return prepared_samples, encoded_samples


def _flatten_encoded_samples(
    encoded_samples: dict[int, dict[str, dict[str, object]]],
    recipes: Sequence[_PipelineRecipe],
    figure_group: str,
) -> list[tuple[int, str, str, dict[str, object]]]:
    rows: list[tuple[int, str, str, dict[str, object]]] = []
    for sample_index in sorted(encoded_samples):
        for recipe in recipes:
            rows.append(
                (
                    sample_index,
                    figure_group,
                    recipe.name,
                    encoded_samples[sample_index][recipe.name],
                ),
            )
    return rows


def _validate_recipe_construction(
    operator_family_recipes: Sequence[_PipelineRecipe],
    restoration_recipes: Sequence[_PipelineRecipe],
) -> dict[str, object]:
    expected_operator_family = {
        "additive_gaussian_noise": (AdditiveGaussianNoiseConfig,),
        "poisson_gaussian_noise": (PoissonGaussianNoiseConfig,),
        "gaussian_blur": (GaussianBlurConfig,),
        "defocus_blur": (DefocusBlurConfig,),
        "psf_convolution": (PsfConvolutionConfig,),
    }
    expected_restoration = {
        "noise": (PoissonGaussianNoiseConfig,),
        "blur": (GaussianBlurConfig,),
        "defocus": (DefocusBlurConfig,),
        "combined_degradation": (DefocusBlurConfig, PoissonGaussianNoiseConfig),
    }
    operator_signatures = {
        recipe.name: tuple(type(operation) for operation in recipe.operations)
        for recipe in operator_family_recipes
    }
    restoration_signatures = {
        recipe.name: tuple(type(operation) for operation in recipe.operations)
        for recipe in restoration_recipes
    }
    return data_check(
        "pipeline_recipe_construction",
        operator_signatures == expected_operator_family
        and restoration_signatures == expected_restoration,
        operator_family_recipe_count=len(operator_family_recipes),
        restoration_recipe_count=len(restoration_recipes),
    )


def _validate_multi_sample_execution(
    prepared_samples: Sequence[dict[str, object]],
    encoded_rows: Sequence[tuple[int, str, str, dict[str, object]]],
    recipe_count: int,
) -> dict[str, object]:
    return data_check(
        "multi_sample_pipeline_execution",
        len(prepared_samples) == _SAMPLE_COUNT
        and len(encoded_rows) == _SAMPLE_COUNT * recipe_count,
        sample_count=len(prepared_samples),
        encoded_sample_count=len(encoded_rows),
    )


def _validate_clean_degraded_preservation(
    prepared_samples: Sequence[dict[str, object]],
    encoded_rows: Sequence[tuple[int, str, str, dict[str, object]]],
) -> dict[str, object]:
    passed = True
    max_reference_error = 0.0
    for sample_index, _, _, sample in encoded_rows:
        if "reference_image" not in sample or "input_image" not in sample:
            passed = False
            continue
        clean_image = sample["reference_image"]
        degraded_image = sample["input_image"]
        input_image = sample["input_image"]
        if not isinstance(clean_image, torch.Tensor):
            passed = False
            continue
        if not isinstance(degraded_image, torch.Tensor) or not isinstance(
            input_image,
            torch.Tensor,
        ):
            passed = False
            continue
        reference_image = prepared_samples[sample_index]["image"]
        if not isinstance(reference_image, torch.Tensor):
            passed = False
            continue
        reference_error = _max_abs_error(clean_image, reference_image)
        max_reference_error = max(max_reference_error, reference_error)
        if reference_error > 1e-6 or not torch.equal(degraded_image, input_image):
            passed = False
    return data_check(
        "clean_degraded_reference_preservation",
        passed,
        max_reference_error=max_reference_error,
    )


def _validate_encoded_field_contract(
    encoded_rows: Sequence[tuple[int, str, str, dict[str, object]]],
) -> dict[str, object]:
    passed = True
    image_dtypes: set[str] = set()
    field_dtypes: set[str] = set()
    for _, _, _, sample in encoded_rows:
        input_image = sample.get("input_image")
        input_field = sample.get("input_field")
        if not isinstance(input_image, torch.Tensor) or not isinstance(input_field, torch.Tensor):
            passed = False
            continue
        image_dtypes.add(str(input_image.dtype))
        field_dtypes.add(str(input_field.dtype))
        spatial_match = tuple(input_field.shape[-2:]) == tuple(input_image.shape[-2:])
        if (
            input_image.dtype != torch.float32
            or input_field.dtype != torch.complex64
            or not torch.is_complex(input_field)
            or not spatial_match
        ):
            passed = False
    return data_check(
        "encoded_field_contract",
        passed,
        input_image_dtype=";".join(sorted(image_dtypes)),
        input_field_dtype=";".join(sorted(field_dtypes)),
    )


def _validate_provenance_contract(
    encoded_rows: Sequence[tuple[int, str, str, dict[str, object]]],
) -> dict[str, object]:
    passed = True
    for _, _, _, sample in encoded_rows:
        provenance = sample.get("provenance", {})
        operations = _operation_records(sample)
        if not isinstance(provenance, dict):
            passed = False
            continue
        if provenance.get("stage") != "encoded":
            passed = False
        if provenance.get("encoding_method") != "intensity":
            passed = False
        if "perturbation" not in provenance or not operations:
            passed = False
        missing_operation_keys = any(
            "name" not in operation or "parameters" not in operation
            for operation in operations
        )
        if missing_operation_keys:
            passed = False
    return data_check("pipeline_provenance_contract", passed)


def _validate_restoration_operator_scope(
    encoded_rows: Sequence[tuple[int, str, str, dict[str, object]]],
) -> dict[str, object]:
    operations = {
        operation_name
        for _, _, _, sample in encoded_rows
        for operation_name in _operation_names(sample)
    }
    edge_operations = sorted(operations & _EDGE_OPERATION_NAMES)
    return data_check(
        "restoration_operator_scope",
        not edge_operations,
        excluded_edge_operations=edge_operations,
        operation_names=sorted(operations),
    )


def _metrics_rows(
    encoded_rows: Sequence[tuple[int, str, str, dict[str, object]]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for sample_index, figure_group, recipe_name, sample in encoded_rows:
        clean_image = sample["reference_image"]
        degraded_image = sample["input_image"]
        assert isinstance(clean_image, torch.Tensor)
        assert isinstance(degraded_image, torch.Tensor)
        rows.append(
            {
                "sample_index": sample_index,
                "figure_group": figure_group,
                "recipe": recipe_name,
                "image_shape": shape_text(sample["input_image"]),
                "field_shape": shape_text(sample["input_field"]),
                "image_dtype": str(sample["input_image"].dtype),
                "field_dtype": str(sample["input_field"].dtype),
                "operations": ";".join(_operation_names(sample)),
                "clean_degraded_max_abs_error": _max_abs_error(
                    clean_image,
                    degraded_image,
                ),
                "provenance_keys": _provenance_keys(sample),
            }
        )
    return rows


def _recipe_title(recipe_name: str) -> str:
    overrides = {
        "psf": "PSF",
    }
    return " ".join(
        overrides.get(part, part.title())
        for part in recipe_name.split("_")
    )


def _visualize_grid(
    prepared_samples: Sequence[dict[str, object]],
    encoded_samples: dict[int, dict[str, dict[str, object]]],
    recipes: Sequence[_PipelineRecipe],
    output_dir: Path,
    figure_name: str,
    figure_title: str,
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    column_count = len(recipes) + 1
    fig, axes = plt.subplots(
        _SAMPLE_COUNT,
        column_count,
        figsize=validation_figure_size("data_pipeline_grid"),
        constrained_layout=True,
    )
    fig.suptitle(figure_title)
    for row_index in range(_SAMPLE_COUNT):
        plot_image_with_colorbar(
            axes[row_index, 0],
            prepared_samples[row_index]["image"],
            f"Sample {row_index} Reference",
            "data_intensity",
            "Intensity",
            vmin=0.0,
            vmax=1.0,
        )
        for column_index, recipe in enumerate(recipes, start=1):
            sample = encoded_samples[row_index][recipe.name]
            plot_image_with_colorbar(
                axes[row_index, column_index],
                sample["input_image"],
                _recipe_title(recipe.name),
                "data_intensity",
                "Intensity",
                vmin=0.0,
                vmax=1.0,
            )
    return save_figure_pair(fig, output_dir, figure_name)


def _summary_lines(
    *,
    status: str,
    checks: Sequence[dict[str, object]],
    metrics: Sequence[dict[str, object]],
    figures: dict[str, dict[str, str]],
    seed: int,
    size: str,
) -> list[str]:
    lines = [
        "# End-To-End Pipeline Validation",
        "",
        f"Status: {status}",
        f"Validator: {_VALIDATOR_NAME}",
        "Source: fmd",
        f"Seed: {seed}",
        f"Size: {size}",
        f"Prepared image resolution: {_IMAGE_RESOLUTION}",
        f"Array resolution: {_ARRAY_RESOLUTION}",
        "",
        "## Checks",
    ]
    lines.extend(f"- {check['name']}: {check['status']}" for check in checks)
    lines.extend(
        [
            "",
            "## Metrics",
            f"- rows: {len(metrics)}",
            "",
            "## Figures",
        ]
    )
    for figure_name, figure_paths in figures.items():
        lines.extend(
            [
                f"- {figure_name}: PASS",
                f"  - png: {figure_paths['png']}",
                f"  - svg: {figure_paths['svg']}",
            ],
        )
    return lines


def run(
    output_root: str | Path,
    *,
    device: str = "auto",
    seed: int = 42,
    size: str = "tiny",
) -> dict[str, object]:
    """
    运行端到端data pipeline验证并写出标准artifact
    """
    del device
    torch.manual_seed(seed)
    np.random.seed(seed)
    setup_plot_style()

    output_dir = clear_output_dir(Path(output_root) / _VALIDATOR_NAME)
    raw_dataset = build_raw_dataset("fmd", max_samples=_SAMPLE_COUNT, random_seed=seed)
    prepared_dataset = PreparedDataset(
        source_dataset=raw_dataset,
        image_resolution=_IMAGE_RESOLUTION,
        array_resolution=_ARRAY_RESOLUTION,
    )
    operator_family_recipes = _operator_family_recipes()
    restoration_recipes = _restoration_recipes()
    operator_encoded_datasets = _build_encoded_datasets(
        prepared_dataset,
        operator_family_recipes,
        seed=seed,
    )
    restoration_encoded_datasets = _build_encoded_datasets(
        prepared_dataset,
        restoration_recipes,
        seed=seed,
    )
    prepared_samples, operator_encoded_samples = _collect_samples(
        prepared_dataset,
        operator_encoded_datasets,
        operator_family_recipes,
    )
    _, restoration_encoded_samples = _collect_samples(
        prepared_dataset,
        restoration_encoded_datasets,
        restoration_recipes,
    )
    encoded_rows = [
        *_flatten_encoded_samples(
            operator_encoded_samples,
            operator_family_recipes,
            "operator_family",
        ),
        *_flatten_encoded_samples(
            restoration_encoded_samples,
            restoration_recipes,
            "restoration_recipe",
        ),
    ]

    checks = [
        _validate_recipe_construction(operator_family_recipes, restoration_recipes),
        _validate_multi_sample_execution(
            prepared_samples,
            encoded_rows,
            len(operator_family_recipes) + len(restoration_recipes),
        ),
        _validate_clean_degraded_preservation(prepared_samples, encoded_rows),
        _validate_encoded_field_contract(encoded_rows),
        _validate_provenance_contract(encoded_rows),
        _validate_restoration_operator_scope(encoded_rows),
    ]
    status = _aggregate_status(checks)
    metrics = _metrics_rows(encoded_rows)
    figures = {
        _OPERATOR_FAMILY_FIGURE_NAME: _visualize_grid(
            prepared_samples,
            operator_encoded_samples,
            operator_family_recipes,
            output_dir,
            _OPERATOR_FAMILY_FIGURE_NAME,
            "End-To-End Operator Family Grid",
        ),
        _RESTORATION_RECIPE_FIGURE_NAME: _visualize_grid(
            prepared_samples,
            restoration_encoded_samples,
            restoration_recipes,
            output_dir,
            _RESTORATION_RECIPE_FIGURE_NAME,
            "Restoration Recipe Grid",
        ),
    }

    write_summary(
        output_dir,
        _summary_lines(
            status=status,
            checks=checks,
            metrics=metrics,
            figures=figures,
            seed=seed,
            size=size,
        ),
    )
    write_metrics(output_dir, metrics)
    return {
        "data": _VALIDATOR_NAME,
        "status": status,
        "checks": checks,
        "metrics": metrics,
        "figures": figures,
        "output_dir": output_dir.as_posix(),
    }


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    解析命令行参数并运行端到端data pipeline验证
    """
    parser = argparse.ArgumentParser(description="Validate the end-to-end data pipeline.")
    parser.add_argument("--output-root", type=Path, default=Path("results/validation/data"))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
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

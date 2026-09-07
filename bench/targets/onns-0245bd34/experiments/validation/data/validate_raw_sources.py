from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from data.data_source.assets.specs import inspect_raw_dataset_assets
from experiments.validation.data.data_validation_utils import (
    build_raw_dataset,
    clear_output_dir,
    CORE_SOURCE_NAMES,
    data_check,
    image_contract_record,
    MICROSCOPY_SOURCE_NAMES,
    required_provenance_keys,
    save_figure_pair,
    setup_plot_style,
    resolve_validation_cmap,
    TARGET_SOURCE_NAMES,
    tensor_image_to_numpy,
    title_from_figure_name,
    validation_figure_size,
    write_metrics,
    write_summary,
)
from experiments.validation.layers.validation_utils import aggregate_status

_VALIDATOR_NAME = "raw_sources"
_FIGURE_NAMES = (
    "01_raw_source_gallery_mnist",
    "02_raw_source_gallery_fashion_mnist",
    "03_raw_source_gallery_microscopy",
    "04_raw_source_gallery_targets",
)
_CLASSIFICATION_SOURCES = ("mnist", "fashion_mnist")
_REQUIRED_CLASS_LABELS = tuple(range(10))
_SAMPLE_COUNTS = {
    "mnist": 10,
    "fashion_mnist": 10,
    "fmd": 6,
    "biosr": 6,
    "bbbc038": 6,
    "bbbc039": 6,
    "target_usaf": 1,
    "target_siemens": 1,
    "target_slanted_edge": 1,
    "target_line_pairs": 1,
}
_SCAN_LIMITS = {"tiny": 512, "middle": 4096, "full": 20000}


def _asset_name_for_source(source: str) -> str:
    if source.startswith("target_"):
        return "targets"
    return source


def _asset_readiness_records(dataset_root: str | Path | None) -> list[dict[str, object]]:
    statuses = {
        status.dataset_name: status
        for status in inspect_raw_dataset_assets(dataset_root=dataset_root)
    }
    records: list[dict[str, object]] = []
    for source in CORE_SOURCE_NAMES:
        asset_name = _asset_name_for_source(source)
        status = statuses.get(asset_name)
        records.append(
            {
                "source": source,
                "asset": asset_name,
                "expected_path": str(status.expected_path) if status else "",
                "is_ready": bool(status and status.is_ready),
            },
        )
    return records


def _readiness_check(records: Sequence[dict[str, object]]) -> dict[str, object]:
    by_source = {str(record.get("source")): record for record in records}
    missing = [
        source
        for source in CORE_SOURCE_NAMES
        if not bool(by_source.get(source, {}).get("is_ready"))
    ]
    if missing:
        return data_check(
            "raw_asset_readiness",
            False,
            detail="missing raw assets: " + ", ".join(missing),
            records=list(records),
        )
    return data_check(
        "raw_asset_readiness",
        True,
        detail="all core raw assets are ready",
        records=list(records),
    )


def _max_samples_for_source(source: str, *, size: str) -> int:
    if source in _CLASSIFICATION_SOURCES:
        return _scan_limit(size)
    return _SAMPLE_COUNTS[source]


def _build_datasets(seed: int, *, size: str) -> tuple[dict[str, Any], dict[str, str]]:
    datasets: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for source in CORE_SOURCE_NAMES:
        try:
            datasets[source] = build_raw_dataset(
                source,
                max_samples=_max_samples_for_source(source, size=size),
                random_seed=seed,
            )
        except Exception as error:
            errors[source] = f"{error.__class__.__name__}: {error}"
    return datasets, errors


def _dataset_construction_check(
    datasets: dict[str, Any],
    errors: dict[str, str],
    readiness: dict[str, object],
) -> dict[str, object]:
    if readiness["status"] == "FAIL" and not datasets and not errors:
        return data_check(
            "dataset_construction",
            False,
            detail="skipped because raw asset readiness failed",
        )
    if errors:
        return data_check(
            "dataset_construction",
            False,
            detail="failed sources: " + ", ".join(sorted(errors)),
            errors=errors,
        )
    return data_check(
        "dataset_construction",
        set(datasets) == set(CORE_SOURCE_NAMES),
        detail="constructed all core raw datasets",
    )


def _scan_limit(size: str) -> int:
    try:
        return _SCAN_LIMITS[size]
    except KeyError as error:
        supported = ", ".join(sorted(_SCAN_LIMITS))
        message = f"size must be one of {supported}, got {size}"
        raise ValueError(message) from error


def _sample_label(sample: dict[str, object]) -> int:
    return int(sample["label"])


def _collect_class_samples(
    source: str,
    dataset: Any,
    *,
    scan_limit: int,
) -> tuple[list[dict[str, object]], list[str]]:
    by_label: dict[int, dict[str, object]] = {}
    errors: list[str] = []
    for sample_index in range(min(len(dataset), scan_limit)):
        try:
            sample = dataset[sample_index]
            if not isinstance(sample, dict):
                errors.append(f"{source}[{sample_index}] is not a dict")
                continue
            label = _sample_label(sample)
            by_label.setdefault(
                label,
                {
                    "source": source,
                    "sample_index": sample_index,
                    "sample": sample,
                },
            )
        except Exception as error:
            errors.append(f"{source}[{sample_index}]: {error}")
        if all(label in by_label for label in _REQUIRED_CLASS_LABELS):
            break
    selected = [
        by_label[label]
        for label in _REQUIRED_CLASS_LABELS
        if label in by_label
    ]
    return selected, errors


def _collect_first_samples(
    source: str,
    dataset: Any,
    count: int,
) -> tuple[list[dict[str, object]], list[str]]:
    selected: list[dict[str, object]] = []
    errors: list[str] = []
    for sample_index in range(min(len(dataset), count)):
        try:
            sample = dataset[sample_index]
            if not isinstance(sample, dict):
                errors.append(f"{source}[{sample_index}] is not a dict")
                continue
            selected.append(
                {
                    "source": source,
                    "sample_index": sample_index,
                    "sample": sample,
                },
            )
        except Exception as error:
            errors.append(f"{source}[{sample_index}]: {error}")
    return selected, errors


def _collect_gallery_samples(
    datasets: dict[str, Any],
    *,
    size: str,
) -> tuple[dict[str, list[dict[str, object]]], list[str]]:
    samples: dict[str, list[dict[str, object]]] = {}
    errors: list[str] = []
    scan_limit = _scan_limit(size)
    for source, dataset in datasets.items():
        if source in _CLASSIFICATION_SOURCES:
            source_samples, source_errors = _collect_class_samples(
                source,
                dataset,
                scan_limit=scan_limit,
            )
        else:
            source_samples, source_errors = _collect_first_samples(
                source,
                dataset,
                _SAMPLE_COUNTS[source],
            )
        samples[source] = source_samples
        errors.extend(source_errors)
    return samples, errors


def _all_sample_records(
    samples_by_source: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for source in CORE_SOURCE_NAMES:
        records.extend(samples_by_source.get(source, []))
    return records


def _sample_contract_check(
    sample_records: Sequence[dict[str, object]],
    sample_errors: Sequence[str],
) -> dict[str, object]:
    missing_fields: list[str] = []
    for record in sample_records:
        source = str(record["source"])
        sample_index = int(record["sample_index"])
        sample = record["sample"]
        assert isinstance(sample, dict)
        for key in ("image", "label", "category", "provenance"):
            if key not in sample:
                missing_fields.append(f"{source}[{sample_index}].{key}")
    passed = bool(sample_records) and not missing_fields and not sample_errors
    detail = "samples expose image, label, category, and provenance"
    if missing_fields or sample_errors:
        detail = "; ".join([*missing_fields, *sample_errors])
    return data_check("sample_contract", passed, detail=detail)


def _metric_row(record: dict[str, object]) -> dict[str, object]:
    sample = record["sample"]
    assert isinstance(sample, dict)
    provenance = sample.get("provenance", {})
    if not isinstance(provenance, dict):
        provenance = {}
    image_record = image_contract_record(str(record["source"]), sample["image"])
    return {
        **image_record,
        "sample_index": int(record["sample_index"]),
        "label": sample.get("label", ""),
        "category": sample.get("category", ""),
        "provenance_keys": ";".join(sorted(str(key) for key in provenance)),
    }


def _metrics_rows(sample_records: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in sample_records:
        sample = record["sample"]
        if isinstance(sample, dict) and "image" in sample:
            rows.append(_metric_row(record))
    return rows


def _image_contract_check(metrics: Sequence[dict[str, object]]) -> dict[str, object]:
    passed = bool(metrics) and all(
        bool(row["is_finite"]) and float(row["min"]) <= float(row["max"])
        for row in metrics
    )
    return data_check(
        "image_contract",
        passed,
        detail="all selected source images are finite with ordered ranges",
    )


def _provenance_contract_check(
    sample_records: Sequence[dict[str, object]],
) -> dict[str, object]:
    required_keys = set(required_provenance_keys())
    missing: list[str] = []
    for record in sample_records:
        sample = record["sample"]
        assert isinstance(sample, dict)
        provenance = sample.get("provenance", {})
        if not isinstance(provenance, dict):
            missing.append(f"{record['source']}[{record['sample_index']}]: provenance")
            continue
        absent = sorted(required_keys - set(provenance))
        if absent:
            missing.append(
                f"{record['source']}[{record['sample_index']}]: "
                + ",".join(absent),
            )
    return data_check(
        "provenance_contract",
        bool(sample_records) and not missing,
        detail="all selected samples include required raw provenance keys"
        if not missing
        else "; ".join(missing),
    )


def _class_coverage_check(
    samples_by_source: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    details: list[str] = []
    passed = True
    for source in CORE_SOURCE_NAMES:
        records = samples_by_source.get(source, [])
        if source in _CLASSIFICATION_SOURCES:
            labels = {
                _sample_label(record["sample"])
                for record in records
                if isinstance(record.get("sample"), dict)
            }
            source_passed = labels == set(_REQUIRED_CLASS_LABELS)
            details.append(f"{source}: {len(labels)}/10 classes")
        else:
            expected_count = _SAMPLE_COUNTS[source]
            source_passed = len(records) >= expected_count
            details.append(f"{source}: {len(records)}/{expected_count} samples")
        passed = passed and source_passed
    return data_check("class_coverage", passed, detail="; ".join(details))


def _plot_image(ax: Any, record: dict[str, object], title: str) -> None:
    sample = record["sample"]
    assert isinstance(sample, dict)
    image = tensor_image_to_numpy(sample["image"])
    ax.imshow(
        image,
        cmap=resolve_validation_cmap("data_intensity"),
        vmin=float(np.nanmin(image)),
        vmax=float(np.nanmax(image)),
    )
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])


def _save_class_gallery(
    output_dir: Path,
    figure_name: str,
    source: str,
    records: Sequence[dict[str, object]],
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    fig, axes = plt.subplots(
        1,
        10,
        figsize=validation_figure_size("raw_class_gallery"),
        squeeze=False,
    )
    for axis, record in zip(axes.flat, records):
        sample = record["sample"]
        assert isinstance(sample, dict)
        _plot_image(axis, record, str(sample.get("label", "")))
    for axis in axes.flat[len(records) :]:
        axis.axis("off")
    fig.suptitle(title_from_figure_name(figure_name))
    fig.text(0.01, 0.5, source, va="center", rotation="vertical")
    fig.tight_layout()
    return save_figure_pair(fig, output_dir, figure_name)


def _save_microscopy_gallery(
    output_dir: Path,
    samples_by_source: dict[str, list[dict[str, object]]],
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    figure_name = "03_raw_source_gallery_microscopy"
    fig, axes = plt.subplots(
        4,
        6,
        figsize=validation_figure_size("raw_microscopy_gallery"),
        squeeze=False,
    )
    for row_index, source in enumerate(MICROSCOPY_SOURCE_NAMES):
        records = samples_by_source.get(source, [])
        for column_index in range(6):
            axis = axes[row_index, column_index]
            if column_index < len(records):
                _plot_image(axis, records[column_index], str(column_index))
            else:
                axis.axis("off")
            if column_index == 0:
                axis.set_ylabel(source)
    fig.suptitle(title_from_figure_name(figure_name))
    fig.tight_layout()
    return save_figure_pair(fig, output_dir, figure_name)


def _save_target_gallery(
    output_dir: Path,
    samples_by_source: dict[str, list[dict[str, object]]],
) -> dict[str, str]:
    from matplotlib import pyplot as plt

    figure_name = "04_raw_source_gallery_targets"
    fig, axes = plt.subplots(
        1,
        4,
        figsize=validation_figure_size("raw_target_gallery"),
        squeeze=False,
    )
    for axis, source in zip(axes.flat, TARGET_SOURCE_NAMES):
        records = samples_by_source.get(source, [])
        if records:
            _plot_image(axis, records[0], source.removeprefix("target_"))
        else:
            axis.axis("off")
    fig.suptitle(title_from_figure_name(figure_name))
    fig.tight_layout()
    return save_figure_pair(fig, output_dir, figure_name)


def _save_figures(
    output_dir: Path,
    samples_by_source: dict[str, list[dict[str, object]]],
) -> dict[str, dict[str, str]]:
    figures = {
        "01_raw_source_gallery_mnist": _save_class_gallery(
            output_dir,
            "01_raw_source_gallery_mnist",
            "mnist",
            samples_by_source.get("mnist", []),
        ),
        "02_raw_source_gallery_fashion_mnist": _save_class_gallery(
            output_dir,
            "02_raw_source_gallery_fashion_mnist",
            "fashion_mnist",
            samples_by_source.get("fashion_mnist", []),
        ),
        "03_raw_source_gallery_microscopy": _save_microscopy_gallery(
            output_dir,
            samples_by_source,
        ),
        "04_raw_source_gallery_targets": _save_target_gallery(
            output_dir,
            samples_by_source,
        ),
    }
    return figures


def _summary_lines(
    *,
    status: str,
    checks: Sequence[dict[str, object]],
    figures: dict[str, dict[str, str]],
) -> list[str]:
    lines = [
        "# Raw Sources Validation",
        "",
        f"Status: {status}",
        "",
        "## Checks",
    ]
    for check in checks:
        lines.append(
            f"- {check['name']}: {check['status']} - {check.get('detail', '')}"
        )
    lines.extend(["", "## Figures"])
    for figure_name in _FIGURE_NAMES:
        state = "GENERATED" if figure_name in figures else "SKIPPED"
        lines.append(f"- {figure_name}: {state}")
    return lines


def run(
    output_root: str | Path,
    *,
    device: str = "auto",
    seed: int = 42,
    size: str = "tiny",
) -> dict[str, object]:
    """
    运行核心raw source验证并写出标准artifact
    """
    del device
    setup_plot_style()
    output_dir = clear_output_dir(Path(output_root) / _VALIDATOR_NAME)
    readiness_records = _asset_readiness_records(None)
    readiness = _readiness_check(readiness_records)

    datasets: dict[str, Any] = {}
    construction_errors: dict[str, str] = {}
    if readiness["status"] == "PASS":
        datasets, construction_errors = _build_datasets(seed, size=size)
    construction = _dataset_construction_check(
        datasets,
        construction_errors,
        readiness,
    )

    samples_by_source: dict[str, list[dict[str, object]]] = {}
    sample_errors: list[str] = []
    if construction["status"] == "PASS":
        samples_by_source, sample_errors = _collect_gallery_samples(
            datasets,
            size=size,
        )
    sample_records = _all_sample_records(samples_by_source)
    metrics = _metrics_rows(sample_records)
    checks = [
        readiness,
        construction,
        _sample_contract_check(sample_records, sample_errors),
        _image_contract_check(metrics),
        _provenance_contract_check(sample_records),
        _class_coverage_check(samples_by_source),
    ]

    figures: dict[str, dict[str, str]] = {}
    if aggregate_status(checks) == "PASS":
        figures = _save_figures(output_dir, samples_by_source)

    status = aggregate_status(checks)
    write_summary(output_dir, _summary_lines(status=status, checks=checks, figures=figures))
    write_metrics(output_dir, metrics)

    return {
        "data": _VALIDATOR_NAME,
        "status": status,
        "checks": checks,
        "metrics": metrics,
        "figures": figures,
        "output_dir": str(output_dir),
    }


def main(argv: Sequence[str] | None = None) -> dict[str, object]:
    """
    解析命令行参数并运行raw source验证
    """
    parser = argparse.ArgumentParser(description="Run raw source data validation.")
    parser.add_argument("--output-root", type=Path, default=Path("results/validation/data"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--size", choices=("tiny", "middle", "full"), default="tiny")
    args = parser.parse_args(argv)
    return run(output_root=args.output_root, seed=args.seed, size=args.size)


if __name__ == "__main__":
    main()

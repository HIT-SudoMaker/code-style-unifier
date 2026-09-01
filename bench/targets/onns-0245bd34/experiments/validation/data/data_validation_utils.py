from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from data import load
from data.configs import SourceConfig
from experiments.validation.layers.validation_utils import (
    apply_validation_figure_style,
    clear_output_dir,
    ensure_output_dir,
    plot_image_with_colorbar,
    save_figure_pair,
    resolve_validation_cmap,
    setup_plot_style,
    style_validation_colorbar,
    style_validation_grid,
    validation_figure_size,
    validation_panel_figure_size,
    VALIDATION_PALETTE,
    VALIDATION_STYLE,
    write_metrics,
    write_summary,
)

CORE_SOURCE_NAMES = (
    "mnist",
    "fashion_mnist",
    "fmd",
    "biosr",
    "bbbc038",
    "bbbc039",
    "target_usaf",
    "target_siemens",
    "target_slanted_edge",
    "target_line_pairs",
)
MICROSCOPY_SOURCE_NAMES = ("fmd", "biosr", "bbbc038", "bbbc039")
TARGET_SOURCE_NAMES = (
    "target_usaf",
    "target_siemens",
    "target_slanted_edge",
    "target_line_pairs",
)
CLASSIFICATION_SOURCE_NAMES = ("mnist", "fashion_mnist")

_TITLE_OVERRIDES = {
    "mnist": "MNIST",
    "psf": "PSF",
    "cpu": "CPU",
    "gpu": "GPU",
}


def data_check(name: str, is_passed: bool, **details: object) -> dict[str, object]:
    """
    构建统一的data validation检查记录
    """
    return {"name": name, "status": "PASS" if is_passed else "FAIL", **details}


def title_from_figure_name(name: str) -> str:
    """
    生成图文件展示标题
    """
    parts = name.split("_")
    if parts and parts[0].isdigit():
        parts = parts[1:]
    return " ".join(_TITLE_OVERRIDES.get(part, part.title()) for part in parts)


def build_raw_dataset(
    dataset_name: str,
    *,
    dataset_root: str | Path | None = None,
    max_samples: int | None = None,
    random_seed: int = 42,
) -> Any:
    """
    通过统一data pipeline入口构建raw阶段数据集
    """
    config = SourceConfig(
        dataset_name=dataset_name,
        dataset_root=dataset_root,
        max_samples=max_samples,
        random_seed=random_seed,
    )
    return load(config)


def tensor_image_to_numpy(image: object) -> np.ndarray:
    """
    二维 float32 图像数组
    """
    if isinstance(image, torch.Tensor):
        values = image.detach().cpu().float().numpy()
    else:
        values = np.asarray(image, dtype=np.float32)
    values = np.squeeze(values)
    return values.astype(np.float32, copy=False)


def shape_text(value: object) -> str:
    """
    格式化对象 shape
    """
    shape = getattr(value, "shape", ())
    return "x".join(str(axis) for axis in shape)


def image_contract_record(source: str, image: object) -> dict[str, object]:
    """
    记录图像shape、dtype、有限性和数值范围
    """
    values = tensor_image_to_numpy(image)
    if isinstance(image, torch.Tensor):
        dtype = str(image.dtype)
        shape = shape_text(image)
    else:
        dtype = str(values.dtype)
        shape = shape_text(values)
    finite = bool(np.isfinite(values).all())
    return {
        "source": source,
        "image_shape": shape,
        "dtype": dtype,
        "is_finite": finite,
        "min": float(np.nanmin(values)),
        "max": float(np.nanmax(values)),
    }


def required_provenance_keys() -> tuple[str, str, str, str, str]:
    """
    返回raw sample必须保留的基础provenance字段
    """
    return (
        "dataset_name",
        "split_name",
        "source_index",
        "sampled_index",
        "raw_resolution",
    )


__all__ = [
    "CLASSIFICATION_SOURCE_NAMES",
    "CORE_SOURCE_NAMES",
    "MICROSCOPY_SOURCE_NAMES",
    "TARGET_SOURCE_NAMES",
    "apply_validation_figure_style",
    "build_raw_dataset",
    "clear_output_dir",
    "data_check",
    "ensure_output_dir",
    "image_contract_record",
    "plot_image_with_colorbar",
    "required_provenance_keys",
    "resolve_validation_cmap",
    "save_figure_pair",
    "setup_plot_style",
    "shape_text",
    "style_validation_colorbar",
    "style_validation_grid",
    "tensor_image_to_numpy",
    "title_from_figure_name",
    "validation_figure_size",
    "validation_panel_figure_size",
    "VALIDATION_PALETTE",
    "VALIDATION_STYLE",
    "write_metrics",
    "write_summary",
]

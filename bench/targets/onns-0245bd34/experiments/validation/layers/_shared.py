from __future__ import annotations

from collections.abc import Sequence

import torch

WAVELENGTH_M = 532e-9
PIXEL_SIZE_M = 5.32e-6
SIZE_PRESETS = {"tiny": 128, "middle": 256, "full": 512}


def layer_check(
    name: str,
    is_passed: bool | None,
    **details: object,
) -> dict[str, object]:
    """
    构造物理层验证检查记录
    """
    if is_passed is None:
        status = "SKIPPED"
    else:
        status = "PASS" if is_passed else "FAIL"
    return {"name": name, "status": status, **details}


def metric_rows(
    layer: str,
    checks: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """
    展开物理层检查中的可追溯指标
    """
    rows: list[dict[str, object]] = []
    for check in checks:
        for metric, value in check.items():
            if metric in {"name", "status", "error", "detail"}:
                continue
            rows.append(
                {
                    "layer": layer,
                    "check": check["name"],
                    "metric": metric,
                    "value": _metric_value(value),
                    "status": check["status"],
                },
            )
    return rows


def summary_lines(
    layer: str,
    status: str,
    checks: Sequence[dict[str, object]],
    *,
    figure_names: Sequence[str],
    physical_contract: Sequence[str] = (),
) -> list[str]:
    """
    构造物理层验证摘要
    """
    lines = [
        f"# {layer.title()} Validation",
        "",
        f"Status: {status}",
        f"Layer: {layer}",
        "",
        "## Checks",
    ]
    lines.extend(f"- {check['name']}: {check['status']}" for check in checks)
    if physical_contract:
        lines.extend(["", "## Physical Contract", *physical_contract])
    lines.extend(
        [
            "",
            "## Figures",
        ],
    )
    lines.extend(f"- {name}.png / {name}.svg" for name in figure_names)
    return lines


def size_to_resolution(size: str) -> int:
    """
    将档位映射为正方形阵列分辨率
    """
    try:
        return SIZE_PRESETS[size]
    except KeyError as error:
        message = f"size must be one of {tuple(SIZE_PRESETS)}, got {size}"
        raise ValueError(message) from error


def resolve_device(device: str) -> torch.device:
    """
    解析验证设备
    """
    if device == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device == "cuda" and not torch.cuda.is_available():
        message = "CUDA was requested but is not available"
        raise RuntimeError(message)
    if device not in {"cpu", "cuda"}:
        message = f"device must be auto, cpu, or cuda, got {device}"
        raise ValueError(message)
    return torch.device(device)


def gaussian_field(
    resolution: int,
    device: torch.device,
    dtype: torch.dtype = torch.complex64,
) -> torch.Tensor:
    """
    生成批量复数高斯光场
    """
    coordinates = torch.linspace(-1.0, 1.0, resolution, device=device)
    y_grid, x_grid = torch.meshgrid(coordinates, coordinates, indexing="ij")
    amplitude = torch.exp(-4.0 * (x_grid.square() + y_grid.square()))
    return amplitude.to(dtype).unsqueeze(0).unsqueeze(0)


def grating_field(
    resolution: int,
    device: torch.device,
    cycles: float = 4.0,
) -> torch.Tensor:
    """
    生成线性相位光栅光场
    """
    coordinates = torch.arange(resolution, dtype=torch.float32, device=device)
    phase = 2.0 * torch.pi * cycles * coordinates / resolution
    field = torch.exp(1j * phase).expand(resolution, resolution)
    return field.to(torch.complex64).unsqueeze(0).unsqueeze(0)


def finite_max_abs(value: torch.Tensor) -> float:
    """
    返回张量绝对值最大值
    """
    return float(torch.max(torch.abs(value.detach())).cpu())


def _metric_value(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)

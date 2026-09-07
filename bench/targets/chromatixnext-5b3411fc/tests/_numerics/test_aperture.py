from __future__ import annotations

import pytest
import torch

from chromatix_next._numerics.aperture import (
    circular_aperture_mask,
    square_aperture_mask,
)


def _scalar_pair(
    value_y: float,
    value_x: float,
    *,
    dtype: torch.dtype,
    device: torch.device | str = "cpu",
) -> tuple[torch.Tensor, torch.Tensor]:
    return (
        torch.tensor(value_y, dtype=dtype, device=device),
        torch.tensor(value_x, dtype=dtype, device=device),
    )


def test_circular_aperture_respects_signed_sampling_and_closed_boundary() -> None:
    """
    圆孔径按带方向采样坐标合成，并把恰在半径上的样本纳入孔径（固定双精度证据）

    ``_numerics.aperture`` 是物理值所有者共用的内部精度无关工具；
    保留固定双精度分支作为方程专属证据。早先的 float32 兼容性 parametrize 已删除。
    """

    real_dtype = torch.float64
    mask = circular_aperture_mask(
        sample_counts=(2, 4),
        signed_spacing=_scalar_pair(-1.0, 0.5, dtype=real_dtype),
        first_sample_position=_scalar_pair(1.0, -1.0, dtype=real_dtype),
        radius=torch.tensor(0.5, dtype=real_dtype),
    )
    expected = torch.tensor(
        [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 1.0, 1.0],
        ],
        dtype=real_dtype,
    )

    assert mask.dtype is real_dtype
    assert torch.equal(mask, expected)


def test_square_aperture_respects_signed_sampling_and_closed_boundary() -> None:
    """
    方孔径按带方向采样坐标合成，并把恰在半宽上的样本纳入孔径（固定双精度证据）

    保留固定双精度分支作为方程专属证据；float32 parametrize 已删除。
    """

    real_dtype = torch.float64
    mask = square_aperture_mask(
        sample_counts=(3, 4),
        signed_spacing=_scalar_pair(-0.5, 0.5, dtype=real_dtype),
        first_sample_position=_scalar_pair(0.75, -1.0, dtype=real_dtype),
        width=torch.tensor(1.0, dtype=real_dtype),
    )
    expected = torch.tensor(
        [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0, 1.0],
        ],
        dtype=real_dtype,
    )

    assert mask.dtype is real_dtype
    assert torch.equal(mask, expected)


def test_aperture_masks_detach_hard_support_from_tensor_grid() -> None:
    """
    二元孔径支撑不声称对尺寸或空间采样的连续梯度
    """

    spacing_y = torch.tensor(
        0.5,
        dtype=torch.float64,
        requires_grad=True,
    )
    origin_y = torch.tensor(
        -0.5,
        dtype=torch.float64,
        requires_grad=True,
    )
    radius = torch.tensor(
        0.75,
        dtype=torch.float64,
        requires_grad=True,
    )
    mask = circular_aperture_mask(
        sample_counts=(3, 3),
        signed_spacing=(
            spacing_y,
            torch.tensor(0.5, dtype=torch.float64),
        ),
        first_sample_position=(
            origin_y,
            torch.tensor(-0.5, dtype=torch.float64),
        ),
        radius=radius,
    )

    assert mask.shape == (3, 3)
    assert not mask.requires_grad


@pytest.mark.parametrize(
    ("mask_function", "extent_name"),
    [
        (circular_aperture_mask, "radius"),
        (square_aperture_mask, "width"),
    ],
)
def test_aperture_masks_run_with_tensor_grid_on_meta(
    mask_function: object,
    extent_name: str,
) -> None:
    """
    圆形与方形硬支撑经同一张量坐标路径完成 meta 推导（固定双精度）
    """

    real_dtype = torch.float64
    arguments = {
        "sample_counts": (3, 5),
        "signed_spacing": (
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        "first_sample_position": (
            torch.empty((), dtype=real_dtype, device="meta"),
            torch.empty((), dtype=real_dtype, device="meta"),
        ),
        extent_name: torch.empty((), dtype=real_dtype, device="meta"),
    }
    mask = mask_function(**arguments)  # type: ignore[operator]

    assert mask.shape == (3, 5)
    assert mask.dtype == real_dtype
    assert mask.device.type == "meta"


@pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="CUDA is unavailable",
)
def test_aperture_numerics_match_cpu_on_cuda() -> None:
    """
    同一孔径数值所有者在 CPU 与可用 CUDA 设备上保持逐样本一致（固定双精度）

    保留固定双精度 CPU/CUDA 一致性证据；float32 跨精度 parametrize
    已删除（complex64/float32 兼容性证据不再保留）。
    """

    real_dtype = torch.float64
    radius = torch.tensor(0.7, dtype=real_dtype)
    cpu_mask = circular_aperture_mask(
        sample_counts=(5, 6),
        signed_spacing=_scalar_pair(-0.25, 0.2, dtype=real_dtype),
        first_sample_position=_scalar_pair(0.5, -0.5, dtype=real_dtype),
        radius=radius,
    )
    cuda_mask = circular_aperture_mask(
        sample_counts=(5, 6),
        signed_spacing=_scalar_pair(
            -0.25,
            0.2,
            dtype=real_dtype,
            device="cuda",
        ),
        first_sample_position=_scalar_pair(
            0.5,
            -0.5,
            dtype=real_dtype,
            device="cuda",
        ),
        radius=radius.cuda(),
    )
    width = torch.tensor(1.0, dtype=real_dtype)
    cpu_square_mask = square_aperture_mask(
        sample_counts=(5, 6),
        signed_spacing=_scalar_pair(-0.25, 0.2, dtype=real_dtype),
        first_sample_position=_scalar_pair(0.5, -0.5, dtype=real_dtype),
        width=width,
    )
    cuda_square_mask = square_aperture_mask(
        sample_counts=(5, 6),
        signed_spacing=_scalar_pair(
            -0.25,
            0.2,
            dtype=real_dtype,
            device="cuda",
        ),
        first_sample_position=_scalar_pair(
            0.5,
            -0.5,
            dtype=real_dtype,
            device="cuda",
        ),
        width=width.cuda(),
    )

    assert torch.equal(cpu_mask, cuda_mask.cpu())
    assert torch.equal(cpu_square_mask, cuda_square_mask.cpu())

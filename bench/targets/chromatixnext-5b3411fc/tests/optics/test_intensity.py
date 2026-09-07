from __future__ import annotations

import dataclasses

import pytest
import torch

from chromatix_next.errors import OpticalTypeError, OpticalValueError
from chromatix_next.optics import FieldNormalization, Intensity, SpatialGrid


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(2, 3),
        sample_spacing=(1.0, 1.0),
    )


def test_intensity_preserves_values_and_exposes_physical_axis_meaning() -> None:
    """
    光强保留作者张量身份，并由归一化与批量形状导出单位和自然轴含义
    """

    values = torch.ones((4, 2, 3), dtype=torch.float64)
    intensity = Intensity(
        values=values,
        grid=_grid(),
        normalization=FieldNormalization.POWER,
    )

    assert intensity.values is values
    assert intensity.batch_shape == (4,)
    assert intensity.axis_meaning == ("batch_0", "height", "width")
    assert intensity.units == "watts_per_square_metre"
    assert intensity.spectral_reduction == "weighted_sum"

    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(intensity, "values", torch.zeros_like(values))


@pytest.mark.parametrize(
    ("values", "identity"),
    (
        (torch.ones((2, 3), dtype=torch.float32), "intensity_values_dtype_invalid"),
        (torch.ones((2, 3), dtype=torch.complex128), "intensity_values_not_real"),
        (torch.ones((3,), dtype=torch.float64), "intensity_values_rank_invalid"),
        (
            torch.tensor(
                ((1.0, 1.0, float("nan")),) * 2,
                dtype=torch.float64,
            ),
            "intensity_values_nonfinite",
        ),
        (
            torch.tensor(
                ((1.0, -1.0, 1.0),) * 2,
                dtype=torch.float64,
            ),
            "intensity_values_negative",
        ),
        (torch.ones((3, 3), dtype=torch.float64), "intensity_height_axis_mismatch"),
        (torch.ones((2, 2), dtype=torch.float64), "intensity_width_axis_mismatch"),
    ),
)
def test_intensity_rejects_invalid_values_with_stable_identity(
    values: torch.Tensor,
    identity: str,
) -> None:
    """
    光强对精度、实值、秩、有限性、非负性及空间形状分别稳定拒绝
    """

    with pytest.raises((OpticalTypeError, OpticalValueError)) as rejected:
        Intensity(
            values=values,
            grid=_grid(),
            normalization=FieldNormalization.RELATIVE,
        )

    assert rejected.value.identity == identity

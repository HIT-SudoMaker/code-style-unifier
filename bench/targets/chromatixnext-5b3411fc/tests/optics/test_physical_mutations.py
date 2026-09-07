from __future__ import annotations

from collections.abc import Callable
import math

import pytest
import torch

from chromatix_next.optics import (
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    Polarization,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.element import IdealThinLens


def _lens_case() -> tuple[OpticalField, float]:
    # 构造相位符号与焦距变异共用的单色均匀场
    grid = SpatialGrid.centered(
        sample_counts=(9, 9),
        sample_spacing=(0.5e-6, 0.5e-6),
    )
    spectrum = Spectrum.monochromatic(wavelength=2.0e-6)
    field = OpticalField(
        envelope=torch.ones((1, 1, 9, 9), dtype=torch.complex128),
        grid=grid,
        spectrum=spectrum,
        polarization_representation=(Polarization.scalar()).representation,
        medium=Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(lengths=(0.0,)),
    )
    return field, 8.0e-6


def _independent_lens_envelope(
    field: OpticalField,
    focal_length: float,
    *,
    phase_sign: float = -1.0,
) -> torch.Tensor:
    # 以显式坐标和 torch.polar 独立计算前向近轴薄透镜相位
    height, width = field.grid.sample_counts
    spacing_y, spacing_x = field.grid.signed_spacing
    first_y, first_x = field.grid.first_sample_position
    position_y = (
        torch.arange(height, dtype=torch.float64) * spacing_y + first_y
    )
    position_x = (
        torch.arange(width, dtype=torch.float64) * spacing_x + first_x
    )
    radius_squared = position_y[:, None].square() + position_x[None, :].square()
    wave_number = 2.0 * math.pi / field.spectrum.wavelengths[0]
    phase = phase_sign * wave_number * radius_squared / (2.0 * focal_length)
    multiplier = torch.polar(torch.ones_like(phase), phase)
    return field.envelope * multiplier.unsqueeze(0).unsqueeze(0)


def _assert_lens_oracle(candidate: torch.Tensor) -> None:
    field, focal_length = _lens_case()
    expected = _independent_lens_envelope(field, focal_length)
    torch.testing.assert_close(candidate, expected, atol=1.0e-12, rtol=1.0e-12)


def _correct_lens() -> torch.Tensor:
    field, focal_length = _lens_case()
    return IdealThinLens(
        grid=field.grid,
        focal_length=focal_length,
    )(field).envelope


def _reversed_lens_phase() -> torch.Tensor:
    field, focal_length = _lens_case()
    return _independent_lens_envelope(
        field,
        focal_length,
        phase_sign=1.0,
    )


def _doubled_lens_focal_length() -> torch.Tensor:
    field, focal_length = _lens_case()
    return _independent_lens_envelope(field, 2.0 * focal_length)


def _removed_lens() -> torch.Tensor:
    field, _focal_length = _lens_case()
    return field.envelope


def test_public_thin_lens_passes_independent_phase_oracle() -> None:
    """
    公开理想薄透镜通过与实现路径不同的解析相位 oracle
    """

    _assert_lens_oracle(_correct_lens())


@pytest.mark.parametrize(
    "mutant",
    (
        pytest.param(_reversed_lens_phase, id="reversed-phase-sign"),
        pytest.param(_doubled_lens_focal_length, id="doubled-focal-length"),
        pytest.param(_removed_lens, id="removed-lens"),
    ),
)
def test_lens_oracle_kills_each_test_local_mutant(
    mutant: Callable[[], torch.Tensor],
) -> None:
    """
    同一解析相位 oracle 杀死符号、焦距与缺失元件变异
    """

    with pytest.raises(AssertionError):
        _assert_lens_oracle(mutant())


def _assert_left_circular_oracle(state: tuple[complex, ...]) -> None:
    # 独立冻结 exp(-iωt) 下正 z 左圆偏振及四分之一周期实场旋向
    scale = 1.0 / math.sqrt(2.0)
    assert state == pytest.approx((scale + 0.0j, -1j * scale))
    quarter_period = -1j
    quarter_real = tuple(
        (component * quarter_period).real for component in state
    )
    assert quarter_real == pytest.approx((0.0, -scale))


def _reversed_time_convention() -> tuple[complex, ...]:
    scale = 1.0 / math.sqrt(2.0)
    return (scale + 0.0j, 1j * scale)


def _reversed_polarization_handedness() -> tuple[complex, ...]:
    return Polarization.right_circular().components


def test_public_left_circular_passes_time_evolution_oracle() -> None:
    """
    公开左圆偏振通过负时间指数下的独立时间演化 oracle
    """

    _assert_left_circular_oracle(Polarization.left_circular().components)


@pytest.mark.parametrize(
    "mutant",
    (
        pytest.param(_reversed_time_convention, id="reversed-time-convention"),
        pytest.param(
            _reversed_polarization_handedness,
            id="reversed-polarization-handedness",
        ),
    ),
)
def test_polarization_oracle_kills_each_test_local_mutant(
    mutant: Callable[[], tuple[complex, ...]],
) -> None:
    """
    同一时间演化 oracle 杀死时间约定与偏振旋向变异
    """

    with pytest.raises(AssertionError):
        _assert_left_circular_oracle(mutant())


from __future__ import annotations

import pytest
import torch

from chromatix_next.optics import (
    FieldNormalization,
    Medium,
    OpticalField,
    OpticalPathReference,
    PolarizationRepresentation,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.element import (
    amplitude_transmission_map,
    circular_pupil,
    ideal_thin_lens,
    optical_path_modulation,
    square_pupil,
)


def _field_from_envelope(
    envelope: torch.Tensor,
    *,
    grid: SpatialGrid,
    spectrum: Spectrum,
    representation: PolarizationRepresentation,
    medium: Medium | None = None,
) -> OpticalField:
    # 以显式包络构造光场，偏振轴长度由表示决定；介质省略时取真空
    return OpticalField(
        envelope=envelope,
        grid=grid,
        spectrum=spectrum,
        polarization_representation=representation,
        medium=medium if medium is not None else Vacuum(),
        normalization=FieldNormalization.RELATIVE,
        path_reference=OpticalPathReference(
            lengths=(0.0,) * spectrum.count,
        ),
    )


def _random_component(
    counts: tuple[int, int],
    *,
    generator: torch.Generator,
) -> torch.Tensor:
    # 固定种子下生成空间变化的复场
    real = torch.randn(counts, generator=generator, dtype=torch.float64)
    imaginary = torch.randn(counts, generator=generator, dtype=torch.float64)
    return torch.complex(real, imaginary)


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(7, 7),
        sample_spacing=(0.5e-6, 0.5e-6),
    )


def _spectrum() -> Spectrum:
    return Spectrum.monochromatic(wavelength=2.0e-6)


def _amplitude_map(grid: SpatialGrid) -> torch.Tensor:
    # 构造落在 [0,1] 的随空间位置衰减的振幅透射图
    counts_y, counts_x = grid.sample_counts
    row = torch.arange(counts_y, dtype=torch.float64) / max(counts_y - 1, 1)
    column = torch.arange(counts_x, dtype=torch.float64) / max(counts_x - 1, 1)
    return 0.4 + 0.5 * (row[:, None] * column[None, :])


def _path_variation(grid: SpatialGrid) -> torch.Tensor:
    # 构造以米为单位的随空间位置线性变化的光程变化图
    counts_y, counts_x = grid.sample_counts
    row = torch.arange(counts_y, dtype=torch.float64) / max(counts_y - 1, 1)
    column = torch.arange(counts_x, dtype=torch.float64) / max(counts_x - 1, 1)
    return (row[:, None] + column[None, :]) * 0.15 * 2.0e-6


_FOCAL_LENGTH = 12.0e-6
_PUPIL_RADIUS = 1.4e-6
_PUPIL_WIDTH = 2.8e-6


def _apply_element(
    name: str,
    field: OpticalField,
    grid: SpatialGrid,
    amplitude: torch.Tensor,
    variation: torch.Tensor,
) -> OpticalField:
    # 按元件名把光场送入对应中性元件函数
    if name == "amplitude_transmission_map":
        return amplitude_transmission_map(
            field,
            grid=grid,
            amplitude_transmission=amplitude,
        )
    if name == "optical_path_modulation":
        return optical_path_modulation(
            field,
            grid=grid,
            optical_path_variation=variation,
        )
    if name == "ideal_thin_lens":
        return ideal_thin_lens(
            field,
            grid=grid,
            focal_length=_FOCAL_LENGTH,
        )
    if name == "circular_pupil":
        return circular_pupil(field, grid=grid, radius=_PUPIL_RADIUS)
    return square_pupil(field, grid=grid, width=_PUPIL_WIDTH)


# 五种偏振中性元件的逐分量律证据：元件名
_ELEMENT_CASES = [
    "amplitude_transmission_map",
    "optical_path_modulation",
    "ideal_thin_lens",
    "circular_pupil",
    "square_pupil",
]


@pytest.mark.parametrize("element_name", _ELEMENT_CASES)
@pytest.mark.parametrize(
    ("representation", "component_count"),
    (
        (PolarizationRepresentation.TRANSVERSE, 2),
        (PolarizationRepresentation.FULL, 3),
    ),
    ids=["transverse", "full"],
)
def test_neutral_element_applies_same_scalar_law_to_every_component(
    element_name: str,
    representation: PolarizationRepresentation,
    component_count: int,
) -> None:
    """
    偏振中性元件保持表示并在每一分量上施加同一标量律

    整体处理多分量光场后，每个分量与该分量单独作为标量光场经同一元件处理的输出
    完全一致；表示与帧保持不变。
    """
    grid = _grid()
    spectrum = _spectrum()
    amplitude = _amplitude_map(grid)
    variation = _path_variation(grid)
    counts = grid.sample_counts
    generator = torch.Generator(device="cpu").manual_seed(2025)
    components = [
        _random_component(counts, generator=generator)
        for _ in range(component_count)
    ]
    multi_envelope = torch.stack(components).unsqueeze(0)
    field_multi = _field_from_envelope(
        multi_envelope,
        grid=grid,
        spectrum=spectrum,
        representation=representation,
    )

    output_multi = _apply_element(
        element_name,
        field_multi,
        grid,
        amplitude,
        variation,
    )

    assert output_multi.polarization_representation is representation
    assert output_multi.envelope.shape[-3] == component_count
    assert output_multi.grid.is_physically_equivalent_to(grid)
    assert output_multi.medium is field_multi.medium
    assert output_multi.normalization is field_multi.normalization

    tolerance = torch.finfo(torch.float64).eps * 512.0
    for index, component in enumerate(components):
        field_single = _field_from_envelope(
            component.unsqueeze(0).unsqueeze(0),
            grid=grid,
            spectrum=spectrum,
            representation=PolarizationRepresentation.SCALAR,
        )
        output_single = _apply_element(
            element_name,
            field_single,
            grid,
            amplitude,
            variation,
        )
        assert torch.allclose(
            output_multi.envelope[..., index, :, :],
            output_single.envelope[..., 0, :, :],
            rtol=tolerance,
            atol=tolerance,
        )


@pytest.mark.parametrize("element_name", _ELEMENT_CASES)
def test_neutral_element_preserves_scalar_representation(
    element_name: str,
) -> None:
    """
    偏振中性元件对标量输入保持标量表示

    逐分量律已由横向/完整用例证明；此处集中断言标量输入经任一中性元件后表示保持为
    标量、分量数保持为 1，且帧与介质不变。
    """

    grid = _grid()
    spectrum = _spectrum()
    amplitude = _amplitude_map(grid)
    variation = _path_variation(grid)
    generator = torch.Generator(device="cpu").manual_seed(2030)
    single_component = _random_component(
        grid.sample_counts,
        generator=generator,
    )
    field_scalar = _field_from_envelope(
        single_component.unsqueeze(0).unsqueeze(0),
        grid=grid,
        spectrum=spectrum,
        representation=PolarizationRepresentation.SCALAR,
    )

    output = _apply_element(
        element_name,
        field_scalar,
        grid,
        amplitude,
        variation,
    )

    assert output.polarization_representation is (
        PolarizationRepresentation.SCALAR
    )
    assert output.envelope.shape[-3] == 1
    assert output.grid.is_physically_equivalent_to(grid)
    assert output.medium is field_scalar.medium
    assert output.normalization is field_scalar.normalization

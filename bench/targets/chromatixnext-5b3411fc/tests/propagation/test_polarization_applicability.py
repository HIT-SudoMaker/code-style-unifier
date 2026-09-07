
from __future__ import annotations

import pytest
import torch

from chromatix_next.errors import OpticalError
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
from chromatix_next.optics.propagation import (
    fresnel_transform,
    scalable_angular_spectrum,
    scalar_angular_spectrum,
    scaled_angular_spectrum,
    scaled_fresnel,
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
    # 固定种子下生成空间变化的复场，使全部频率箱参与传播，避免 DC 退化
    real = torch.randn(counts, generator=generator, dtype=torch.float64)
    imaginary = torch.randn(counts, generator=generator, dtype=torch.float64)
    return torch.complex(real, imaginary)


def _propagate(
    method: str,
    field: OpticalField,
    destination: SpatialGrid | None,
    distance: float,
) -> OpticalField:
    # 按方法名把光场送入对应标量传播函数
    if method == "scalar_angular_spectrum":
        return scalar_angular_spectrum(field, axial_distance=distance)
    if method == "fresnel_transform":
        return fresnel_transform(field, axial_distance=distance)
    if method == "scaled_angular_spectrum":
        return scaled_angular_spectrum(
            field,
            axial_distance=distance,
            destination_grid=destination,  # type: ignore[arg-type]
        )
    if method == "scaled_fresnel":
        return scaled_fresnel(
            field,
            axial_distance=distance,
            destination_grid=destination,  # type: ignore[arg-type]
        )
    return scalable_angular_spectrum(
        field,
        axial_distance=distance,
        destination_grid=destination,  # type: ignore[arg-type]
    )


def _scalar_angular_spectrum_grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(16, 16),
        sample_spacing=(
            torch.tensor(1.0e-6, dtype=torch.float64),
            torch.tensor(1.0e-6, dtype=torch.float64),
        ),
    )


def _fresnel_grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(8, 10),
        sample_spacing=(4.0e-6, 5.0e-6),
    )


def _scaled_grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(6, 7),
        sample_spacing=(4.0e-6, 5.0e-6),
    )


def _scaled_as_grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(5, 6),
        sample_spacing=(4.0e-6, 5.0e-6),
    )


def _scaled_destination() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(4, 5),
        sample_spacing=(3.0e-6, 4.0e-6),
    )


def _scaled_fresnel_destination() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(5, 6),
        sample_spacing=(4.0e-6, 5.0e-6),
    )


_SCALAR_METHOD_CASES = [
    (
        "scalar_angular_spectrum",
        "scalar_angular_spectrum_polarization_full_unsupported",
        _scalar_angular_spectrum_grid(),
        Spectrum.monochromatic(wavelength=2.0e-6),
        None,
        1.0e-6,
    ),
    (
        "fresnel_transform",
        "fresnel_transform_polarization_full_unsupported",
        _fresnel_grid(),
        Spectrum.monochromatic(wavelength=600.0e-9),
        None,
        20.0e-3,
    ),
    (
        "scaled_angular_spectrum",
        "scaled_angular_spectrum_polarization_full_unsupported",
        _scaled_as_grid(),
        Spectrum.monochromatic(wavelength=0.8e-6),
        _scaled_destination(),
        1.1e-6,
    ),
    (
        "scaled_fresnel",
        "scaled_fresnel_polarization_full_unsupported",
        _scaled_grid(),
        Spectrum.monochromatic(wavelength=0.5e-6),
        _scaled_fresnel_destination(),
        400.0e-6,
    ),
    (
        "scalable_angular_spectrum",
        "scalable_angular_spectrum_polarization_full_unsupported",
        _scaled_grid(),
        Spectrum.monochromatic(wavelength=0.5e-6),
        _scaled_fresnel_destination(),
        550.0e-6,
    ),
]


def _case_id(value: tuple[str, str, SpatialGrid, Spectrum, object, float]) -> str:
    return value[0]


@pytest.mark.parametrize(
    "case",
    _SCALAR_METHOD_CASES,
    ids=[case[0] for case in _SCALAR_METHOD_CASES],
)
def test_transverse_propagates_component_wise(
    case: tuple[str, str, SpatialGrid, Spectrum, object, float],
) -> None:
    """
    横向光场逐分量等价：整体传播等同于每个分量单独作为标量光场传播

    证据独立于生产传递核的偏振轴广播：Ex、Ey 各自构造为单分量标量光场（同一网格、
    同一光谱、同一介质、同一光程参考），经同一方法独立传播后与横向整体传播的对应
    分量逐一相等。这同时是规约接受复选框 2 的直接证据。
    """
    method, _identity, grid, spectrum, destination, distance = case
    counts = grid.sample_counts
    generator = torch.Generator(device="cpu").manual_seed(2024)
    ex = _random_component(counts, generator=generator)
    ey = _random_component(counts, generator=generator)
    transverse_envelope = torch.stack((ex, ey)).unsqueeze(0)
    field_transverse = _field_from_envelope(
        transverse_envelope,
        grid=grid,
        spectrum=spectrum,
        representation=PolarizationRepresentation.TRANSVERSE,
    )

    output_transverse = _propagate(
        method,
        field_transverse,
        destination,  # type: ignore[arg-type]
        distance,
    )

    assert (
        output_transverse.polarization_representation
        is PolarizationRepresentation.TRANSVERSE
    )
    field_ex = _field_from_envelope(
        ex.unsqueeze(0).unsqueeze(0),
        grid=grid,
        spectrum=spectrum,
        representation=PolarizationRepresentation.SCALAR,
    )
    output_ex = _propagate(
        method,
        field_ex,
        destination,  # type: ignore[arg-type]
        distance,
    )
    field_ey = _field_from_envelope(
        ey.unsqueeze(0).unsqueeze(0),
        grid=grid,
        spectrum=spectrum,
        representation=PolarizationRepresentation.SCALAR,
    )
    output_ey = _propagate(
        method,
        field_ey,
        destination,  # type: ignore[arg-type]
        distance,
    )

    tolerance = torch.finfo(torch.float64).eps * 512.0
    assert torch.allclose(
        output_transverse.envelope[..., 0, :, :],
        output_ex.envelope[..., 0, :, :],
        rtol=tolerance,
        atol=tolerance,
    )
    assert torch.allclose(
        output_transverse.envelope[..., 1, :, :],
        output_ey.envelope[..., 0, :, :],
        rtol=tolerance,
        atol=tolerance,
    )


@pytest.mark.parametrize(
    "case",
    _SCALAR_METHOD_CASES,
    ids=[case[0] for case in _SCALAR_METHOD_CASES],
)
def test_full_vector_rejected_before_expensive_calculation(
    case: tuple[str, str, SpatialGrid, Spectrum, object, float],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    完整矢量拒绝先于任何 FFT 或 CZT 计算

    把 FFT 入口替换为断言失败，确认拒绝在进入数值核之前发生。
    """
    method, identity, grid, spectrum, destination, distance = case
    counts = grid.sample_counts
    full_envelope = torch.ones(
        (spectrum.count, 3, counts[0], counts[1]),
        dtype=torch.complex128,
    )
    field_full = _field_from_envelope(
        full_envelope,
        grid=grid,
        spectrum=spectrum,
        representation=PolarizationRepresentation.FULL,
    )

    def reject_fft(*_arguments: object, **_keywords: object) -> torch.Tensor:
        """
        拒绝适用性失败后仍进入 FFT 的非法执行
        """
        error_identity = "fft_called_after_polarization_rejection"
        raise AssertionError(error_identity)

    monkeypatch.setattr(torch.fft, "fftn", reject_fft)
    monkeypatch.setattr(torch.fft, "ifftn", reject_fft)
    monkeypatch.setattr(torch.fft, "fft2", reject_fft)
    monkeypatch.setattr(torch.fft, "ifft2", reject_fft)

    with pytest.raises(OpticalError) as caught:
        _propagate(
            method,
            field_full,
            destination,  # type: ignore[arg-type]
            distance,
        )

    assert caught.value.identity == identity


@pytest.mark.parametrize(
    "case",
    _SCALAR_METHOD_CASES,
    ids=[case[0] for case in _SCALAR_METHOD_CASES],
)
def test_scalar_input_remains_accepted(
    case: tuple[str, str, SpatialGrid, Spectrum, object, float],
) -> None:
    """
    标量输入继续被各传播方法接受，对应接受复选框 1
    """
    method, _identity, grid, spectrum, destination, distance = case
    counts = grid.sample_counts
    generator = torch.Generator(device="cpu").manual_seed(31)
    component = _random_component(counts, generator=generator)
    field_scalar = _field_from_envelope(
        component.unsqueeze(0).unsqueeze(0),
        grid=grid,
        spectrum=spectrum,
        representation=PolarizationRepresentation.SCALAR,
    )

    output = _propagate(
        method,
        field_scalar,
        destination,  # type: ignore[arg-type]
        distance,
    )

    assert (
        output.polarization_representation is PolarizationRepresentation.SCALAR
    )
    assert output.envelope.shape[-3] == 1
    assert bool(torch.isfinite(output.envelope).all())

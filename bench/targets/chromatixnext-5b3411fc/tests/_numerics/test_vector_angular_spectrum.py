
from __future__ import annotations

import torch

from chromatix_next._numerics.wave_propagation.vector_angular_spectrum import (
    propagate_vector_angular_spectrum,
    vector_angular_spectrum_calculation,
)


def _pair(
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


def _calculation(**over: object) -> object:
    base: dict[str, object] = dict(
        computational_counts=(8, 8),
        signed_spacing=_pair(0.25e-6, 0.25e-6, dtype=torch.float64),
        displacement=_pair(0.0, 0.0, dtype=torch.float64),
        axial_distance=torch.tensor(0.0, dtype=torch.float64),
        wavelengths=torch.tensor([1.0e-6], dtype=torch.float64),
        refractive_indices=torch.tensor([1.0], dtype=torch.float64),
        real_dtype=torch.float64,
        complex_dtype=torch.complex128,
        device=torch.device("cpu"),
    )
    base.update(over)
    return vector_angular_spectrum_calculation(**base)  # type: ignore[arg-type]


def test_support_outside_radiative_is_zeroed_in_transfer() -> None:
    """
    传递在严格 ``Q>0`` 辐射支撑外严格为零（倏逝与精确掠入均被分类排除）
    """

    calc = _calculation()
    transfer = calc.transfer  # type: ignore[attr-defined]
    support = calc.support  # type: ignore[attr-defined]
    assert bool(torch.isfinite(transfer).all())
    assert torch.equal(transfer != 0, support)
    assert int(torch.count_nonzero(transfer)) > 0


def test_calculation_exposes_polarization_facts() -> None:
    """
    建结果携带逐光谱波数事实，供施函数重建纵向分量
    """

    calc = _calculation()
    facts = calc.facts  # type: ignore[attr-defined]
    assert facts.wave_number.shape == (1, 1, 1)
    assert facts.transverse_wavevector_y.shape[-3] == 1
    assert calc.has_narrow_alias_band.shape == ()  # type: ignore[attr-defined]


def test_calculation_runs_on_meta() -> None:
    """
    meta 路径仅推导传递与支撑的形状和精度
    """

    calc = _calculation(
        signed_spacing=_pair(0.0, 0.0, dtype=torch.float32, device="meta"),
        displacement=_pair(0.0, 0.0, dtype=torch.float32, device="meta"),
        axial_distance=torch.empty((), dtype=torch.float32, device="meta"),
        wavelengths=torch.empty((2,), dtype=torch.float32, device="meta"),
        refractive_indices=torch.empty((2,), dtype=torch.float32, device="meta"),
        real_dtype=torch.float32,
        complex_dtype=torch.complex64,
        device=torch.device("meta"),
        computational_counts=(8, 10),
    )
    transfer = calc.transfer  # type: ignore[attr-defined]
    assert transfer.shape == (2, 8, 10)
    assert transfer.dtype == torch.complex64
    assert transfer.device.type == "meta"


def test_propagate_reconstructs_longitudinal_from_transverse_field() -> None:
    """
    横向两分量包络经施函数重建纵向分量并保持横向
    """

    calc = _calculation(computational_counts=(8, 8))
    envelope = torch.zeros((1, 2, 8, 8), dtype=torch.complex128)
    envelope[0, 0, 4, 4] = 1.0
    propagated, is_full_field_transverse = propagate_vector_angular_spectrum(
        envelope=envelope,
        calculation=calc,  # type: ignore[arg-type]
        computational_counts=(8, 8),
        padding=(0, 0),
        is_full=False,
    )
    assert propagated.shape == (1, 3, 8, 8)
    assert bool(torch.isfinite(propagated).all())
    assert bool(is_full_field_transverse)

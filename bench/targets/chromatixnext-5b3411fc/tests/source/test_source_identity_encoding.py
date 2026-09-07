
from __future__ import annotations

from collections.abc import Callable
import inspect
from typing import Any

import pytest
import torch

from chromatix_next.optics._source_lifecycle import _encode_source_identity_fields
from chromatix_next.optics.field import PropagationDirection
from chromatix_next.optics.medium import ConstantMedium
from chromatix_next.optics.polarization import Polarization
from chromatix_next.optics.source import (
    CollimatedRaySource,
    GaussianBeam,
    PlaneWave,
    PointSource,
)
from chromatix_next.optics.spectrum import Spectrum


def _spectrum() -> Spectrum:
    return Spectrum(
        wavelengths=(4.5e-7, 5.5e-7),
        weights=(0.25, 0.75),
    )


def _scalar(value: float, *, is_trainable: bool) -> float | torch.nn.Parameter:
    if not is_trainable:
        return value
    return torch.nn.Parameter(torch.tensor(value, dtype=torch.float64))


def _position(
    *,
    is_trainable: bool,
) -> tuple[float, float, float] | torch.nn.Parameter:
    coordinates = (0.0, 0.0, 5.0e-6)
    if not is_trainable:
        return coordinates
    return torch.nn.Parameter(torch.tensor(coordinates, dtype=torch.float64))


def _source_factories(
    *,
    is_trainable: bool,
) -> dict[str, Callable[[], torch.nn.Module]]:
    spectrum = _spectrum()
    polarization = Polarization.linear_x()
    medium = ConstantMedium(index=1.3)
    return {
        "plane_wave": lambda: PlaneWave(
            spectrum=spectrum,
            polarization=polarization,
            medium=medium,
            propagation_direction=PropagationDirection.forward(),
            total_power=_scalar(2.0, is_trainable=is_trainable),
        ),
        "gaussian_beam": lambda: GaussianBeam(
            spectrum=spectrum,
            polarization=polarization,
            medium=medium,
            waist=_scalar(2.0e-6, is_trainable=is_trainable),
            total_power=_scalar(2.0, is_trainable=is_trainable),
        ),
        "point_source": lambda: PointSource(
            spectrum=spectrum,
            polarization=polarization,
            medium=medium,
            position=_position(is_trainable=is_trainable),
            total_power=_scalar(2.0, is_trainable=is_trainable),
        ),
        "collimated_ray": lambda: CollimatedRaySource(
            spectrum=spectrum,
            polarization=polarization,
            medium=medium,
            ray_power=_scalar(2.0, is_trainable=is_trainable),
        ),
    }


def _expected_common_identity() -> dict[str, object]:
    return {
        "spectrum": {
            "wavelengths": (4.5e-7, 5.5e-7),
            "weights": (0.25, 0.75),
        },
        "polarization": {
            "representation": "transverse",
            "components": ((1.0, 0.0), (0.0, 0.0)),
        },
        "medium_identity": (
            "chromatix_next.optics.medium",
            "ConstantMedium",
            (1.3,),
        ),
    }


def test_identity_encoder_has_only_explicit_physical_facts() -> None:
    """
    断言共享 owner 不接受 Source 或源特定结构策略
    """

    assert tuple(inspect.signature(_encode_source_identity_fields).parameters) == (
        "spectrum",
        "polarization",
        "medium_identity",
    )
    assert _encode_source_identity_fields(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        medium_identity=ConstantMedium(index=1.3).physical_identity(),
    ) == _expected_common_identity()


@pytest.mark.parametrize("is_trainable", [False, True], ids=["buffer", "parameter"])
def test_all_sources_preserve_frozen_extra_state_values(
    is_trainable: bool,
) -> None:
    """
    断言固定量与可训练量模式下四源附加状态逐键逐值保持冻结基线

    :param is_trainable: 是否以 Parameter 承载各源可训练的局部物理量
    """

    expected_common = _expected_common_identity()
    expected_local_fields: dict[str, dict[str, object]] = {
        "plane_wave": {
            "direction_kind": "propagation",
            "normalization": "power",
        },
        "gaussian_beam": {"normalization": "power"},
        "point_source": {"normalization": "power"},
        "collimated_ray": {},
    }
    for source_name, factory in _source_factories(
        is_trainable=is_trainable,
    ).items():
        expected = expected_common | expected_local_fields[source_name]
        assert factory().get_extra_state() == expected


from __future__ import annotations

from collections.abc import Callable
import copy

import pytest
import torch

from chromatix_next.optics.field import PropagationDirection
from chromatix_next.optics.grid import SpatialGrid
from chromatix_next.optics.medium import Vacuum
from chromatix_next.optics.polarization import Polarization
from chromatix_next.optics.source import (
    CollimatedRaySource,
    GaussianBeam,
    PlaneWave,
    PointSource,
)
from chromatix_next.optics.spectrum import Spectrum


def _monochromatic() -> Spectrum:
    return Spectrum(
        wavelengths=(0.5e-6,),
        weights=(1.0,),
    )


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(8, 8),
        sample_spacing=(0.5e-6, 0.5e-6),
    )


def _plane_wave(amplitude: torch.nn.Parameter) -> PlaneWave:
    return PlaneWave(
        spectrum=_monochromatic(),
        polarization=Polarization.linear_y(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=amplitude,
    )


def _gaussian_beam(
    waist: torch.nn.Parameter,
    amplitude: torch.nn.Parameter,
) -> GaussianBeam:
    return GaussianBeam(
        spectrum=_monochromatic(),
        polarization=Polarization.linear_y(),
        medium=Vacuum(),
        waist=waist,
        waist_location=0.0,
        relative_amplitude=amplitude,
    )


def _point_source(
    position: torch.nn.Parameter,
    amplitude: torch.nn.Parameter,
) -> PointSource:
    return PointSource(
        spectrum=_monochromatic(),
        polarization=Polarization.linear_y(),
        medium=Vacuum(),
        position=position,
        relative_amplitude=amplitude,
    )


def _position_parameter() -> torch.nn.Parameter:
    return torch.nn.Parameter(
        torch.tensor([0.0, 0.0, 5.0e-6], dtype=torch.float64),
    )


def _collimated(ray_power: torch.nn.Parameter) -> CollimatedRaySource:
    return CollimatedRaySource(
        spectrum=_monochromatic(),

        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        ray_power=ray_power,
    )


def _trainable(value: float, dtype: torch.dtype = torch.float64) -> torch.nn.Parameter:
    return torch.nn.Parameter(torch.tensor(value, dtype=dtype))


@pytest.mark.parametrize(
    ("factory", "parameter_name"),
    [
        (lambda: _plane_wave(_trainable(1.25)), "relative_amplitude"),
        (lambda: _gaussian_beam(_trainable(2.0e-6), _trainable(1.25)), "waist"),
        (
            lambda: _point_source(_position_parameter(), _trainable(1.25)),
            "position",
        ),
        (lambda: _collimated(_trainable(1.25)), "ray_power"),
    ],
    ids=["plane_wave", "gaussian_beam", "point_source", "collimated"],
)
def test_trainable_parameter_keeps_identity_and_state_dict_keys(
    factory: Callable[[], torch.nn.Module],
    parameter_name: str,
) -> None:
    """
    断言可训练 Parameter 经共享生命周期注册后仍是原 leaf 对象

    :param factory: 构造一个带可训练 Parameter 的 Source 的零参可调用对象
    :param parameter_name: 待校验身份的 Parameter 在 named_parameters 中的键名
    """

    source = factory()
    registered = dict(source.named_parameters())[parameter_name]

    assert registered.requires_grad is True
    assert registered.is_leaf
    keys_before = set(source.state_dict().keys())
    round_trip = copy.deepcopy(source)
    assert dict(round_trip.named_parameters())[parameter_name] is not registered
    assert set(round_trip.state_dict().keys()) == keys_before
    source(_grid())
    assert dict(source.named_parameters())[parameter_name] is registered


def test_wave_sources_keep_envelope_cache_out_of_state_dict() -> None:
    """
    断言非持久化单位包络缓存不进入 state_dict
    """

    amplitude = _trainable(1.25)
    plane_wave = _plane_wave(amplitude)
    plane_wave(_grid())
    assert dict(plane_wave.named_buffers())["_unit_envelope_cache"] is not None
    assert "_unit_envelope_cache" not in plane_wave.state_dict()

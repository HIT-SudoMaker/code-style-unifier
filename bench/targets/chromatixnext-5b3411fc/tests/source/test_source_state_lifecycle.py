from __future__ import annotations

from collections.abc import Callable, Mapping
import copy
from typing import Any

import pytest
import torch

from chromatix_next import install_state
from chromatix_next.errors import AssemblyError, OpticalError
from chromatix_next.optics.combination import coherent_combination
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
from chromatix_next.workstation import Workstation


def _monochromatic(wavelength: float = 0.5e-6) -> Spectrum:
    return Spectrum(
        wavelengths=(wavelength,),
        weights=(1.0,),
    )


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(8, 8),
        sample_spacing=(0.5e-6, 0.5e-6),
    )


def _plane_wave(
    polarization: Polarization = Polarization.linear_y(),
) -> PlaneWave:
    return PlaneWave(
        spectrum=_monochromatic(),
        polarization=polarization,
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.25,
    )


def _gaussian_beam(
    polarization: Polarization = Polarization.linear_x(),
) -> GaussianBeam:
    return GaussianBeam(
        spectrum=_monochromatic(),
        polarization=polarization,
        waist=2.0e-6,
        relative_amplitude=1.25,
    )


def _point_source(
    polarization: Polarization = Polarization.linear_y(),
) -> PointSource:
    return PointSource(
        spectrum=_monochromatic(),
        polarization=polarization,
        medium=Vacuum(),
        position=(0.0, 0.0, 5.0e-6),
        relative_amplitude=1.25,
    )


def _collimated(
    polarization: Polarization = Polarization.linear_x(),
) -> CollimatedRaySource:
    return CollimatedRaySource(
        spectrum=_monochromatic(),
        polarization=polarization,
        medium=Vacuum(),
        ray_power=1.25,
    )


def _plane_wave_donor() -> PlaneWave:
    return _plane_wave(Polarization.linear_x())


def _gaussian_beam_donor() -> GaussianBeam:
    return _gaussian_beam(Polarization.linear_y())


def _point_source_donor() -> PointSource:
    return _point_source(Polarization.linear_x())


_SOURCE_FACTORIES: tuple[Callable[[], Any], ...] = (
    _plane_wave,
    _gaussian_beam,
    _point_source,
    _collimated,
)

_WAVE_SOURCE_PAIRS: tuple[
    tuple[Callable[[], Any], Callable[[], Any]],
    ...,
] = (
    (_plane_wave, _plane_wave_donor),
    (_gaussian_beam, _gaussian_beam_donor),
    (_point_source, _point_source_donor),
)


def _assert_state_dict_equal(
    actual: Mapping[str, object],
    expected: Mapping[str, object],
) -> None:
    assert actual.keys() == expected.keys()
    for name, expected_value in expected.items():
        actual_value = actual[name]
        if isinstance(expected_value, torch.Tensor):
            assert isinstance(actual_value, torch.Tensor)
            assert torch.equal(actual_value, expected_value), name
        else:
            assert actual_value == expected_value, name


@pytest.mark.parametrize(
    "factory",
    _SOURCE_FACTORIES,
    ids=["plane_wave", "gaussian_beam", "point_source", "collimated"],
)
def test_same_spectrum_extra_state_round_trip_preserves_metadata(
    factory: Callable[[], Any],
) -> None:
    """
    Source 只接受自身完整且同构的物理身份载荷
    """

    source = factory()
    state = source.get_extra_state()
    restored = factory()

    restored.set_extra_state(state)

    assert restored.get_extra_state() == state


@pytest.mark.parametrize(
    ("target_factory", "donor_factory"),
    _WAVE_SOURCE_PAIRS,
    ids=["plane_wave", "gaussian_beam", "point_source"],
)
def test_wave_source_install_state_rebuilds_next_emission(
    target_factory: Callable[[], Any],
    donor_factory: Callable[[], Any],
) -> None:
    """
    波源状态安装后按新物理状态重建下一次发射
    """

    grid = _grid()
    target = target_factory()
    donor = donor_factory()
    target(grid)
    expected = donor(grid)

    install_state(target, donor.state_dict())
    actual = target(grid)

    assert target.get_extra_state() == donor.get_extra_state()
    assert torch.equal(actual.envelope, expected.envelope)


@pytest.mark.parametrize(
    "factory",
    _SOURCE_FACTORIES,
    ids=["plane_wave", "gaussian_beam", "point_source", "collimated"],
)
def test_source_copies_emit_and_deep_copy_can_be_hosted_independently(
    factory: Callable[[], Any],
) -> None:
    """
    Source 深副本在独立托管前保持可独立执行
    """

    grid = _grid()
    original = factory()
    shallow_copy = copy.copy(original)
    deep_copy = copy.deepcopy(original)

    original(grid)
    shallow_copy(grid)
    deep_copy(grid)

    workstation_original = Workstation.cpu()
    workstation_original.host(original)

    workstation_deep_copy = Workstation.cpu()
    workstation_deep_copy.host(deep_copy)


@pytest.mark.parametrize(
    "factory",
    _SOURCE_FACTORIES,
    ids=["plane_wave", "gaussian_beam", "point_source", "collimated"],
)
def test_state_dict_round_trip_preserves_physical_metadata(
    factory: Callable[[], Any],
) -> None:
    """
    同构状态往返保留物理元数据与键集
    """

    source = factory()
    restored = factory()

    restored.load_state_dict(source.state_dict())

    assert restored.get_extra_state() == source.get_extra_state()
    assert frozenset(restored.state_dict()) == frozenset(source.state_dict())


def test_source_lineage_stays_on_values_but_not_on_copied_or_reloaded_sources() -> None:
    """
    相干组合区分同源值与复制或重载的 Source
    """

    source = _plane_wave()
    first_field = source(_grid())
    second_field = source(_grid())
    copied_field = copy.copy(first_field)
    shallow_source = copy.copy(source)
    deep_source = copy.deepcopy(source)
    restored_source = _plane_wave()
    install_state(restored_source, source.state_dict())

    coherent_combination(first_field, second_field)
    coherent_combination(first_field, copied_field)

    independent_fields = (
        shallow_source(_grid()),
        deep_source(_grid()),
        restored_source(_grid()),
    )
    for independent_field in independent_fields:
        with pytest.raises(AssemblyError) as rejected:
            coherent_combination(first_field, independent_field)
        assert (
            rejected.value.identity
            == "coherent_combination_source_lineage_mismatch"
        )


def test_collimated_malformed_extra_state_rejects_without_mutation() -> None:
    """
    畸形准直光线源元数据在公开状态边界原子失败
    """

    source = _collimated()
    malformed_state = copy.deepcopy(source.get_extra_state())
    del malformed_state["spectrum"]
    before = copy.deepcopy(source.state_dict())

    with pytest.raises(OpticalError) as rejected:
        source.set_extra_state(malformed_state)

    assert rejected.value.identity == "collimated_ray_source_extra_state_invalid"
    _assert_state_dict_equal(source.state_dict(), before)


def test_collimated_structure_mismatch_keeps_stable_identity() -> None:
    """
    准直光线源在状态变更前以稳定身份拒绝异构介质
    """

    source = _collimated()
    incompatible_state = copy.deepcopy(source.get_extra_state())
    incompatible_state["medium_identity"] = ("foreign_medium",)
    before = copy.deepcopy(source.state_dict())

    with pytest.raises(OpticalError) as rejected:
        source.set_extra_state(incompatible_state)

    assert (
        rejected.value.identity
        == "collimated_ray_source_extra_state_structure_mismatch"
    )
    _assert_state_dict_equal(source.state_dict(), before)

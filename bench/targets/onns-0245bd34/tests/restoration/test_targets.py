from __future__ import annotations

import numpy as np
import pytest

from experiments.restoration.targets import (
    build_resolution_targets,
    point_grid,
    siemens_star,
    sinusoidal_grating,
    slanted_edge,
)


def test_point_grid_has_center_impulse() -> None:
    """
    校验分辨率靶标契约
    """
    target = point_grid((9, 9))

    assert target.image.shape == (9, 9)
    assert target.image[4, 4] == 1.0
    assert target.metadata["target_name"] == "point_grid"


def test_slanted_edge_is_normalized_and_not_axis_aligned() -> None:
    """
    校验分辨率靶标契约
    """
    target = slanted_edge((32, 32), angle_degrees=5.0)

    assert target.image.min() >= 0.0
    assert target.image.max() <= 1.0
    assert target.metadata["angle_degrees"] == 5.0
    assert not np.array_equal(target.image[0], target.image[-1])


def test_sinusoidal_grating_metadata_records_frequency() -> None:
    """
    校验分辨率靶标契约
    """
    target = sinusoidal_grating((32, 32), cycles_per_image=4)

    assert target.image.shape == (32, 32)
    assert target.image.min() >= 0.0
    assert target.image.max() <= 1.0
    assert not np.all(target.image == target.image[0, 0])
    assert target.metadata["cycles_per_image"] == 4
    assert target.metadata["target_variant"] == "4_cycles"
    assert target.metadata["target_name"] == "sinusoidal_gratings"


@pytest.mark.parametrize("cycles_per_image", [0, -1, True, 16, 32])
def test_sinusoidal_grating_rejects_invalid_cycles(cycles_per_image: object) -> None:
    """
    校验分辨率靶标契约
    """
    with pytest.raises(ValueError, match="cycles_per_image"):
        sinusoidal_grating(
            (32, 32),
            cycles_per_image=cycles_per_image,  # type: ignore[arg-type]
        )


def test_siemens_star_default_is_normalized_and_non_degenerate() -> None:
    """
    校验分辨率靶标契约
    """
    target = siemens_star((32, 32))

    assert target.image.shape == (32, 32)
    assert target.image.min() >= 0.0
    assert target.image.max() <= 1.0
    assert target.image.min() < target.image.max()
    assert target.metadata["spokes"] == 32


def test_siemens_star_small_resolution_default_is_safe() -> None:
    """
    校验分辨率靶标契约
    """
    target = siemens_star((16, 16))

    assert target.image.shape == (16, 16)
    assert target.image.min() >= 0.0
    assert target.image.max() <= 1.0
    assert target.image.min() < target.image.max()
    assert target.metadata["target_name"] == "siemens_star"
    assert target.metadata["spokes"] <= 16


@pytest.mark.parametrize("spokes", [0, 1, 3, 33, True])
def test_siemens_star_rejects_invalid_spokes(spokes: object) -> None:
    """
    校验分辨率靶标契约
    """
    with pytest.raises(ValueError, match="spokes"):
        siemens_star((32, 32), spokes=spokes)  # type: ignore[arg-type]


def test_build_resolution_targets_returns_default_set() -> None:
    """
    校验分辨率靶标契约
    """
    targets = build_resolution_targets((32, 32))

    target_names = {target.metadata["target_name"] for target in targets}
    assert {
        "point_grid",
        "slanted_edge",
        "sinusoidal_gratings",
        "usaf_bars",
        "siemens_star",
    }.issubset(target_names)
    grating_cycles = [
        int(target.metadata["cycles_per_image"])
        for target in targets
        if target.metadata["target_name"] == "sinusoidal_gratings"
    ]
    assert len(grating_cycles) >= 6
    assert grating_cycles == sorted(grating_cycles)
    assert max(grating_cycles) < 16


def test_build_resolution_targets_returns_default_512_set() -> None:
    """
    校验分辨率靶标契约
    """
    targets = build_resolution_targets((512, 512))

    target_names = {target.metadata["target_name"] for target in targets}
    assert {
        "point_grid",
        "slanted_edge",
        "sinusoidal_gratings",
        "usaf_bars",
        "siemens_star",
    }.issubset(target_names)
    for target in targets:
        assert target.image.shape == (512, 512)
        assert target.image.min() >= 0.0
        assert target.image.max() <= 1.0
        assert target.image.min() < target.image.max()


def test_build_resolution_targets_small_resolution_uses_safe_defaults() -> None:
    """
    校验分辨率靶标契约
    """
    targets = build_resolution_targets((16, 16))

    target_names = {target.metadata["target_name"] for target in targets}
    assert {
        "point_grid",
        "slanted_edge",
        "sinusoidal_gratings",
        "usaf_bars",
        "siemens_star",
    }.issubset(target_names)
    for target in targets:
        assert target.image.shape == (16, 16)
        assert target.image.min() >= 0.0
        assert target.image.max() <= 1.0
        assert target.image.min() < target.image.max()
    cycles = [
        target.metadata["cycles_per_image"]
        for target in targets
        if target.metadata["target_name"] == "sinusoidal_gratings"
    ]
    assert len(cycles) >= 2
    assert len(set(cycles)) == len(cycles)
    assert all(isinstance(cycle, int) and cycle < 8 for cycle in cycles)

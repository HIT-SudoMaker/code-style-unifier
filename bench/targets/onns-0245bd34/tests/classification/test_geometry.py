from __future__ import annotations

import pytest

from experiments.classification.geometry import (
    SUPPORTED_TOPOLOGIES,
    get_classification_geometry,
    normalize_topology,
)


def test_supported_topologies_stay_clean() -> None:
    """
    验证分类测试契约保持稳定
    """
    assert SUPPORTED_TOPOLOGIES == ("without_lens", "with_lens")
    with pytest.raises(ValueError, match="Unsupported topology"):
        normalize_topology("passive")
    with pytest.raises(ValueError, match="Unsupported topology"):
        normalize_topology("reference_fo_128")


def test_without_lens_geometry_matches_compact_baseline() -> None:
    """
    验证分类测试契约保持稳定
    """
    geometry = get_classification_geometry("without_lens")

    assert geometry.image_resolution == (32, 32)
    assert geometry.array_resolution == (64, 64)
    assert geometry.wavelength == pytest.approx(532e-9)
    assert geometry.pixel_size == pytest.approx(532e-9 * 10)
    assert geometry.propagation_distance == pytest.approx(5e-3)
    assert geometry.focal_length == pytest.approx(5e-3)
    assert geometry.detector_size == 4
    assert geometry.detector_padding == 6
    assert geometry.detector_sets == (3, 4, 3)
    assert geometry.detector_steps_x == (5, 3, 5)
    assert geometry.detector_step_y == 5
    assert geometry.detector_regions == (
        (6, 10, 6, 10),
        (30, 34, 6, 10),
        (54, 58, 6, 10),
        (6, 10, 30, 34),
        (22, 26, 30, 34),
        (38, 42, 30, 34),
        (54, 58, 30, 34),
        (6, 10, 54, 58),
        (30, 34, 54, 58),
        (54, 58, 54, 58),
    )


def test_with_lens_geometry_matches_standard_4f_contract() -> None:
    """
    验证分类测试契约保持稳定
    """
    geometry = get_classification_geometry("with_lens")

    assert geometry.image_resolution == (64, 64)
    assert geometry.array_resolution == (128, 128)
    assert geometry.wavelength == pytest.approx(532e-9)
    assert geometry.pixel_size == pytest.approx(2e-6)
    assert geometry.propagation_distance == pytest.approx(5e-3)
    assert geometry.focal_length == pytest.approx(5e-3)
    assert geometry.detector_size == 9
    assert geometry.detector_padding == 32
    assert geometry.detector_sets == (3, 4, 3)
    assert geometry.detector_steps_x == (2, 1, 2)
    assert geometry.detector_step_y == 2
    assert geometry.detector_regions == (
        (32, 41, 32, 41),
        (59, 68, 32, 41),
        (86, 95, 32, 41),
        (32, 41, 59, 68),
        (50, 59, 59, 68),
        (68, 77, 59, 68),
        (86, 95, 59, 68),
        (32, 41, 86, 95),
        (59, 68, 86, 95),
        (86, 95, 86, 95),
    )

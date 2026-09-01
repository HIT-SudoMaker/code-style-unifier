from __future__ import annotations

import importlib

import pytest

from chromatix_next.optics.source import CollimatedRaySource


def test_collimated_ray_source_has_one_direct_module_path() -> None:
    """
    准直光线源仅保留表意明确的直接模块路径，包级公开身份不变
    """

    direct_module = importlib.import_module(
        "chromatix_next.optics.source.collimated_ray",
    )
    assert direct_module.CollimatedRaySource is CollimatedRaySource

    unsupported_module = "chromatix_next.optics.source.collimated"
    with pytest.raises(ModuleNotFoundError) as caught:
        importlib.import_module(unsupported_module)
    assert caught.value.name == unsupported_module

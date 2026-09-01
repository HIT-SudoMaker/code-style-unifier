from __future__ import annotations

from dataclasses import replace

import pytest
import torch

from experiments.classification import model as model_module
from experiments.classification.geometry import get_classification_geometry
from experiments.classification.model import (
    ClassificationONN,
    SingleLayerClassificationONN,
    SUPPORTED_TOPOLOGIES,
    aggregate_detector_regions,
    normalize_topology,
)
from layers import LensLayer

CLASSIFICATION_DETECTOR_REGIONS = get_classification_geometry(
    "without_lens"
).detector_regions


def _count_lens_layers(model: torch.nn.Module) -> int:
    return sum(1 for module in model.modules() if isinstance(module, LensLayer))


def test_aggregate_detector_regions_returns_normalized_per_sample_distribution() -> None:
    """
    归一化行
    """
    intensity_map = torch.zeros((2, 1, 64, 64), dtype=torch.float32)
    for region_index, (x0, x1, y0, y1) in enumerate(CLASSIFICATION_DETECTOR_REGIONS):
        intensity_map[0, 0, y0:y1, x0:x1] = float(region_index + 1)
        intensity_map[1, 0, y0:y1, x0:x1] = float(
            len(CLASSIFICATION_DETECTOR_REGIONS) - region_index
    )

    detector_distribution = aggregate_detector_regions(
        intensity_map,
        CLASSIFICATION_DETECTOR_REGIONS,
    )

    expected_first = torch.arange(
        1,
        len(CLASSIFICATION_DETECTOR_REGIONS) + 1,
        dtype=torch.float32,
    )
    expected_first = expected_first / expected_first.sum()
    expected_second = torch.flip(expected_first, dims=(0,))

    assert detector_distribution.shape == (2, len(CLASSIFICATION_DETECTOR_REGIONS))
    assert torch.allclose(detector_distribution.sum(dim=1), torch.ones(2), atol=1e-6)
    assert torch.allclose(detector_distribution[0], expected_first, atol=1e-6)
    assert torch.allclose(detector_distribution[1], expected_second, atol=1e-6)


def test_aggregate_detector_regions_uses_uniform_fallback_for_zero_energy_rows() -> None:
    """
    均匀兜底
    """
    intensity_map = torch.zeros((3, 1, 64, 64), dtype=torch.float32)

    detector_distribution = aggregate_detector_regions(
        intensity_map,
        CLASSIFICATION_DETECTOR_REGIONS,
    )

    expected = torch.full(
        (len(CLASSIFICATION_DETECTOR_REGIONS),),
        1.0 / len(CLASSIFICATION_DETECTOR_REGIONS),
        dtype=torch.float32,
    )
    assert torch.allclose(detector_distribution, expected.expand_as(detector_distribution))


def test_supported_topologies_are_without_and_with_lens() -> None:
    """
    拓扑名称
    """
    assert SUPPORTED_TOPOLOGIES == ("without_lens", "with_lens")


@pytest.mark.parametrize(
    ("raw_topology", "expected"),
    [
        ("without_lens", "without_lens"),
        ("with_lens", "with_lens"),
    ],
)
def test_normalize_topology_accepts_supported_names(
    raw_topology: str,
    expected: str,
) -> None:
    """
    拓扑归一化
    """
    assert normalize_topology(raw_topology) == expected


@pytest.mark.parametrize("raw_topology", ["bogus", "no_lens"])
def test_normalize_topology_rejects_unknown_name(raw_topology: str) -> None:
    """
    非法拓扑
    """
    with pytest.raises(ValueError, match="Unsupported topology"):
        normalize_topology(raw_topology)


def test_classification_onn_rejects_no_lens_name() -> None:
    """
    拒绝旧名称
    """
    with pytest.raises(ValueError, match="Unsupported topology"):
        ClassificationONN(topology="no_lens")


def test_classification_onn_with_lens_contains_real_lens_layers() -> None:
    """
    物理透镜
    """
    model = ClassificationONN(topology="with_lens")

    assert model.topology == "with_lens"
    assert _count_lens_layers(model) == 2


@pytest.mark.parametrize(
    ("topology", "shape"),
    [
        ("without_lens", (2, 1, 64, 64)),
        ("with_lens", (2, 1, 128, 128)),
    ],
)
def test_classification_onn_returns_distribution_and_intensity_map(
    topology: str,
    shape: tuple[int, int, int, int],
) -> None:
    """
    模型输出
    """
    model = ClassificationONN(topology=topology)
    input_field = torch.ones(shape, dtype=torch.complex64)

    detector_distribution, intensity_map = model(input_field)

    assert detector_distribution.shape == (2, 10)
    assert intensity_map.shape == shape
    assert torch.allclose(detector_distribution.sum(dim=1), torch.ones(2), atol=1e-5)


def test_classification_onn_with_lens_uses_128_geometry() -> None:
    """
    验证分类测试契约保持稳定
    """
    model = ClassificationONN(topology="with_lens")
    input_field = torch.ones((2, 1, 128, 128), dtype=torch.complex64)

    detector_distribution, intensity_map = model(input_field)

    assert detector_distribution.shape == (2, 10)
    assert intensity_map.shape == (2, 1, 128, 128)
    assert model.detector_regions[0] == (32, 41, 32, 41)
    assert model.detector_regions[-1] == (86, 95, 86, 95)


def test_with_lens_constructs_layers_from_topology_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    geometry = replace(
        get_classification_geometry("with_lens"),
        wavelength=633e-9,
    )
    diffraction_kwargs: list[dict[str, object]] = []
    lens_kwargs: list[dict[str, object]] = []

    class _FakeDiffractionLayer(torch.nn.Module):
        def __init__(self, **kwargs: object) -> None:
            """
            初始化衍射层并记录参数
            """
            super().__init__()
            diffraction_kwargs.append(kwargs)

        def forward(self, input_field: torch.Tensor, distance: float) -> torch.Tensor:
            """
            执行测试替身前向传播
            """
            return input_field

    class _FakeLensLayer(torch.nn.Module):
        def __init__(self, **kwargs: object) -> None:
            """
            初始化透镜层并记录参数
            """
            super().__init__()
            lens_kwargs.append(kwargs)

        def forward(self, input_field: torch.Tensor) -> torch.Tensor:
            """
            执行测试替身前向传播
            """
            return input_field

    class _FakeModulationLayer(torch.nn.Module):
        def __init__(self, **kwargs: object) -> None:
            """
            初始化调制层替身模块
            """
            super().__init__()

        def forward(self, input_field: torch.Tensor) -> torch.Tensor:
            """
            执行测试替身前向传播
            """
            return input_field

    monkeypatch.setattr(
        model_module,
        "get_classification_geometry",
        lambda topology: geometry,
    )
    monkeypatch.setattr(
        model_module,
        "_load_optical_layer_classes",
        lambda: (_FakeDiffractionLayer, _FakeLensLayer, _FakeModulationLayer),
    )

    ClassificationONN(topology="with_lens")

    assert len(diffraction_kwargs) == 4
    assert len(lens_kwargs) == 2
    for kwargs in [*diffraction_kwargs, *lens_kwargs]:
        assert kwargs["wavelength"] == pytest.approx(geometry.wavelength)
        assert kwargs["pixel_size"] == pytest.approx(geometry.pixel_size)
        assert kwargs["array_resolution"] == geometry.array_resolution


def test_with_lens_uses_four_focal_length_propagations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    验证分类测试契约保持稳定
    """
    calls: list[tuple[str, float | None]] = []

    class _FakeDiffractionLayer(torch.nn.Module):
        def __init__(self, **kwargs: object) -> None:
            """
            初始化衍射层替身模块
            """
            super().__init__()

        def forward(self, input_field: torch.Tensor, distance: float) -> torch.Tensor:
            """
            执行测试替身前向传播
            """
            calls.append(("propagate", float(distance)))
            return input_field

    class _FakeLensLayer(torch.nn.Module):
        def __init__(self, **kwargs: object) -> None:
            """
            初始化透镜层替身模块
            """
            super().__init__()

        def forward(self, input_field: torch.Tensor) -> torch.Tensor:
            """
            执行测试替身前向传播
            """
            calls.append(("lens", None))
            return input_field

    class _FakeModulationLayer(torch.nn.Module):
        def __init__(self, **kwargs: object) -> None:
            """
            初始化调制层替身模块
            """
            super().__init__()

        def forward(self, input_field: torch.Tensor) -> torch.Tensor:
            """
            执行测试替身前向传播
            """
            calls.append(("mask", None))
            return input_field

    monkeypatch.setattr(
        model_module,
        "_load_optical_layer_classes",
        lambda: (_FakeDiffractionLayer, _FakeLensLayer, _FakeModulationLayer),
    )
    model = ClassificationONN(topology="with_lens")

    model(torch.ones((1, 1, 128, 128), dtype=torch.complex64))

    assert calls == [
        ("propagate", pytest.approx(5e-3)),
        ("lens", None),
        ("propagate", pytest.approx(5e-3)),
        ("mask", None),
        ("propagate", pytest.approx(5e-3)),
        ("lens", None),
        ("propagate", pytest.approx(5e-3)),
    ]


def test_single_layer_classification_onn_remains_without_lens_model() -> None:
    """
    基线变体
    """
    model = SingleLayerClassificationONN()

    assert isinstance(model, ClassificationONN)
    assert model.topology == "without_lens"
    assert _count_lens_layers(model) == 0

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_TOPOLOGIES = ("without_lens", "with_lens")
TOPOLOGY_ALIASES = {topology: topology for topology in SUPPORTED_TOPOLOGIES}
CLASSIFICATION_WAVELENGTH = 532e-9


@dataclass(frozen=True, slots=True)
class ClassificationGeometry:
    """
    描述分类拓扑的光学阵列和探测器几何
    """

    topology: str
    image_resolution: tuple[int, int]
    array_resolution: tuple[int, int]
    wavelength: float
    pixel_size: float
    propagation_distance: float
    focal_length: float
    detector_size: int
    detector_padding: int
    detector_sets: tuple[int, int, int]
    detector_steps_x: tuple[int, int, int]
    detector_step_y: int
    detector_regions: tuple[tuple[int, int, int, int], ...]


def normalize_topology(topology: str) -> str:
    """
    返回受支持的规范化分类拓扑名称
    """
    try:
        return TOPOLOGY_ALIASES[topology]
    except KeyError as error:
        message = f"Unsupported topology: {topology}"
        raise ValueError(message) from error


def build_detector_regions(
    *,
    detector_size: int,
    detector_padding: int,
    detector_sets: tuple[int, int, int],
    detector_steps_x: tuple[int, int, int],
    detector_step_y: int,
) -> tuple[tuple[int, int, int, int], ...]:
    """
    构造按行排列的分类探测器区域
    """
    regions: list[tuple[int, int, int, int]] = []
    for row_index, detector_count in enumerate(detector_sets):
        top = detector_padding + row_index * (detector_step_y + 1) * detector_size
        for detector_index in range(detector_count):
            left = (
                detector_padding
                + detector_index
                * (detector_steps_x[row_index] + 1)
                * detector_size
            )
            regions.append((left, left + detector_size, top, top + detector_size))
    return tuple(regions)


def _make_geometry(
    *,
    topology: str,
    image_resolution: tuple[int, int],
    array_resolution: tuple[int, int],
    pixel_size: float,
    propagation_distance: float,
    focal_length: float,
    detector_size: int,
    detector_padding: int,
    detector_steps_x: tuple[int, int, int],
    detector_step_y: int,
) -> ClassificationGeometry:
    detector_sets = (3, 4, 3)
    detector_regions = build_detector_regions(
        detector_size=detector_size,
        detector_padding=detector_padding,
        detector_sets=detector_sets,
        detector_steps_x=detector_steps_x,
        detector_step_y=detector_step_y,
    )
    return ClassificationGeometry(
        topology=topology,
        image_resolution=image_resolution,
        array_resolution=array_resolution,
        wavelength=CLASSIFICATION_WAVELENGTH,
        pixel_size=pixel_size,
        propagation_distance=propagation_distance,
        focal_length=focal_length,
        detector_size=detector_size,
        detector_padding=detector_padding,
        detector_sets=detector_sets,
        detector_steps_x=detector_steps_x,
        detector_step_y=detector_step_y,
        detector_regions=detector_regions,
    )


_GEOMETRIES = {
    "without_lens": _make_geometry(
        topology="without_lens",
        image_resolution=(32, 32),
        array_resolution=(64, 64),
        pixel_size=10 * CLASSIFICATION_WAVELENGTH,
        propagation_distance=5e-3,
        focal_length=5e-3,
        detector_size=4,
        detector_padding=6,
        detector_steps_x=(5, 3, 5),
        detector_step_y=5,
    ),
    "with_lens": _make_geometry(
        topology="with_lens",
        image_resolution=(64, 64),
        array_resolution=(128, 128),
        pixel_size=2e-6,
        propagation_distance=5e-3,
        focal_length=5e-3,
        detector_size=9,
        detector_padding=32,
        detector_steps_x=(2, 1, 2),
        detector_step_y=2,
    ),
}


def get_classification_geometry(topology: str) -> ClassificationGeometry:
    """
    返回指定分类拓扑的固定几何配置
    """
    return _GEOMETRIES[normalize_topology(topology)]

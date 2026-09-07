from __future__ import annotations

import torch
import torch.nn as nn

from experiments.classification.geometry import (
    SUPPORTED_TOPOLOGIES,
    get_classification_geometry,
    normalize_topology,
)

CLASSIFICATION_PROPAGATION_DISTANCE = 5e-3
CLASSIFICATION_FOCAL_LENGTH = 5e-3


def _load_optical_layer_classes() -> tuple[type[nn.Module], type[nn.Module], type[nn.Module]]:
    from layers import DiffractionLayer, LensLayer, ModulationLayer

    return DiffractionLayer, LensLayer, ModulationLayer


def aggregate_detector_regions(
    intensity_map: torch.Tensor,
    detector_regions: tuple[tuple[int, int, int, int], ...],
) -> torch.Tensor:
    """
    将输出强度图聚合为归一化探测器分布
    """
    detector_sums = [
        intensity_map[:, :, y0:y1, x0:x1].sum(dim=(1, 2, 3))
        for x0, x1, y0, y1 in detector_regions
    ]
    detector_distribution = torch.stack(detector_sums, dim=1)
    detector_energy = detector_distribution.sum(dim=1, keepdim=True)
    normalized_distribution = detector_distribution / detector_energy.clamp_min(1e-10)
    zero_energy_rows = detector_energy <= 1e-10
    if zero_energy_rows.any():
        uniform_distribution = torch.full_like(
            normalized_distribution,
            1.0 / len(detector_regions),
        )
        normalized_distribution = torch.where(
            zero_energy_rows,
            uniform_distribution,
            normalized_distribution,
        )
    return normalized_distribution


class ClassificationONN(nn.Module):
    """
    实现分类实验使用的可选透镜 ONN 前向模型
    """

    def __init__(
        self,
        topology: str = "without_lens",
        *,
        phase_parameterization: str = "direct",
        phase_initialization: str = "uniform",
        propagation_distance: float | None = None,
        focal_length: float | None = None,
        pixel_size: float | None = None,
        num_phase_layers: int | None = None,
    ) -> None:
        """
        构造指定分类拓扑的光学传播和调制层
        """
        super().__init__()
        self.topology = normalize_topology(topology)
        self.geometry = get_classification_geometry(self.topology)
        if num_phase_layers is None:
            num_phase_layers = 1
        if num_phase_layers <= 0:
            message = "num_phase_layers must be positive"
            raise ValueError(message)
        if self.topology == "with_lens" and num_phase_layers != 1:
            message = "with_lens currently supports exactly one 4F phase mask"
            raise ValueError(message)

        self.propagation_distance = float(
            self.geometry.propagation_distance
            if propagation_distance is None
            else propagation_distance
        )
        self.focal_length = float(
            self.geometry.focal_length if focal_length is None else focal_length
        )
        self.detector_regions = self.geometry.detector_regions
        self.array_resolution = self.geometry.array_resolution
        self.pixel_size = float(self.geometry.pixel_size if pixel_size is None else pixel_size)
        diffraction_count = 4 if self.topology == "with_lens" else num_phase_layers + 1
        DiffractionLayer, LensLayer, ModulationLayer = _load_optical_layer_classes()

        self.diffraction_layers = nn.ModuleList(
            [
                DiffractionLayer(
                    wavelength=self.geometry.wavelength,
                    pixel_size=self.pixel_size,
                    array_resolution=self.array_resolution,
                )
                for _ in range(diffraction_count)
            ]
        )
        self.modulation_layers = nn.ModuleList(
            [
                ModulationLayer(
                    array_resolution=self.array_resolution,
                    phase_parameterization=phase_parameterization,
                    phase_initialization=phase_initialization,
                )
                for _ in range(num_phase_layers)
            ]
        )
        if self.topology == "with_lens":
            self.input_lens = LensLayer(
                wavelength=self.geometry.wavelength,
                focal_length=self.focal_length,
                pixel_size=self.pixel_size,
                array_resolution=self.array_resolution,
            )
            self.output_lens = LensLayer(
                wavelength=self.geometry.wavelength,
                focal_length=self.focal_length,
                pixel_size=self.pixel_size,
                array_resolution=self.array_resolution,
            )

    def forward(self, input_field: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        返回探测器分类分布和输出强度图
        """
        if self.topology == "with_lens":
            output_field = self._forward_with_lens(input_field)
        else:
            output_field = self._forward_without_lens(input_field)
        intensity_map = output_field.abs().square()
        detector_distribution = aggregate_detector_regions(
            intensity_map,
            self.detector_regions,
        )
        return detector_distribution, intensity_map

    def _forward_without_lens(self, input_field: torch.Tensor) -> torch.Tensor:
        output = input_field
        for index, modulation_layer in enumerate(self.modulation_layers):
            output = self.diffraction_layers[index](output, self.propagation_distance)
            output = modulation_layer(output)
        return self.diffraction_layers[-1](output, self.propagation_distance)

    def _forward_with_lens(self, input_field: torch.Tensor) -> torch.Tensor:
        output = self.diffraction_layers[0](input_field, self.focal_length)
        output = self.input_lens(output)
        output = self.diffraction_layers[1](output, self.focal_length)
        output = self.modulation_layers[0](output)
        output = self.diffraction_layers[2](output, self.focal_length)
        output = self.output_lens(output)
        return self.diffraction_layers[3](output, self.focal_length)


class SingleLayerClassificationONN(ClassificationONN):
    """
    提供无透镜单相位层分类 ONN 的兼容入口
    """

    def __init__(self) -> None:
        """
        构造默认无透镜单层分类模型
        """
        super().__init__(topology="without_lens", num_phase_layers=1)

from __future__ import annotations

import copy

import pytest

from chromatix_next.errors import AssemblyError
from chromatix_next.optics import (
    Assembly,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.combination import CoherentCombination
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(4, 4),
        sample_spacing=(2.0e-6, 2.0e-6),
    )


def _source(*, amplitude: float = 1.0) -> PlaneWave:
    return PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=1.0e-6),
        polarization=Polarization.scalar(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=amplitude,
    )


def test_source_lineage_survives_values_but_not_source_copy_or_state() -> None:
    """
    光场值复制保留谱系，而 Source 复制与状态加载不转移谱系
    """

    grid = _grid()
    source = _source()
    same_source_a = source(grid)
    same_source_b = source(grid)
    CoherentCombination()(same_source_a, same_source_b)
    CoherentCombination()(same_source_a, copy.copy(same_source_a))
    CoherentCombination()(same_source_a, copy.deepcopy(same_source_a))
    for copied_source in (copy.copy(source), copy.deepcopy(source)):
        with pytest.raises(
            AssemblyError,
            match="coherent_combination_source_lineage_mismatch",
        ):
            CoherentCombination()(source(grid), copied_source(grid))

    restored_source = _source()
    restored_source.load_state_dict(source.state_dict())
    with pytest.raises(
        AssemblyError,
        match="coherent_combination_source_lineage_mismatch",
    ):
        CoherentCombination()(source(grid), restored_source(grid))


def test_coherence_rejects_independent_lineage_not_reference_offset() -> None:
    """
    独立谱系仍被拒绝，但确定性光程参考差不构成相干性失配
    """

    grid = _grid()
    first_source = _source()
    second_source = _source()
    first_field = ScalarAngularSpectrum(axial_distance=1.0e-6)(first_source(grid))
    second_field = ScalarAngularSpectrum(axial_distance=2.0e-6)(second_source(grid))

    with pytest.raises(AssemblyError) as information:
        CoherentCombination()(first_field, second_field)

    assert information.value.identity == (
        "coherent_combination_source_lineage_mismatch"
    )


def test_assembly_rejects_two_independent_sources_as_coherent_inputs() -> None:
    """
    数值相同的两个独立 Source 在装配检查时仍以谱系失配拒绝
    """

    grid = _grid()
    source_1 = _source()
    source_2 = _source()
    combination = CoherentCombination()
    assembly = Assembly()
    assembly.include(source_1, name="source_1", grid=grid)
    assembly.include(source_2, name="source_2", grid=grid)
    assembly.include(combination, name="combination")
    assembly.connect(source_1, combination, destination_port="field_1")
    assembly.connect(source_2, combination, destination_port="field_2")
    assembly.expose(combination, name="output")
    with pytest.raises(
        AssemblyError,
        match="coherent_combination_source_lineage_mismatch",
    ):
        assembly.check()


def test_one_output_port_cannot_drive_two_downstream_inputs() -> None:
    """
    一个输出端口不得替代真实分束驱动两个下游输入
    """

    grid = _grid()
    source = _source()
    detector_1 = IntensityDetection()
    detector_2 = IntensityDetection()
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include(detector_1, name="detector_1")
    assembly.include(detector_2, name="detector_2")
    assembly.connect(source, detector_1)
    with pytest.raises(
        AssemblyError,
        match="assembly_output_port_reused:source:None",
    ):
        assembly.connect(source, detector_2)

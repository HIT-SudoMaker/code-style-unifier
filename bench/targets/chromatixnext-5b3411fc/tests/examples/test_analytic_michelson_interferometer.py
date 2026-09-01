from __future__ import annotations

import cmath
import math
from pathlib import Path
from typing import cast

import pytest
import torch

from chromatix_next import Workstation
from chromatix_next.errors import AssemblyError
from chromatix_next.optics import (
    Assembly,
    FieldNormalization,
    Intensity,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPlanarMirror,
    MirrorTerminal,
)
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave
from examples.analytic_michelson_interferometer.example import (
    COMPLEMENTARY_SUM_ABSOLUTE_ERROR,
    DENSE_COMPLEX_OPERATOR_MAX_ABSOLUTE_ERROR,
    MINIMUM_COUNTERFACTUAL_PORT_SEPARATION,
    PORT_RATIO_ABSOLUTE_ERROR,
    REFRACTIVE_INDEX,
    RELATIVE_PHASE_POINTS,
    RIGHT_ARM_LENGTH,
    SAMPLE_COUNTS,
    SAMPLE_SPACING,
    SPECTRAL_WEIGHT,
    TOP_ARM_OFFSETS,
    VISIBILITY_ABSOLUTE_ERROR,
    WAVELENGTH,
    build_assembly,
    run,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NONDEGENERATE_PHASE = math.pi / 3.0


def _independent_port_ratios(
    relative_phase: float,
    *,
    right_mirror_scalar: complex = -1.0 + 0.0j,
    top_mirror_scalar: complex = -1.0 + 0.0j,
    phase_multiplier: float = 1.0,
) -> tuple[float, float]:
    # 独立写出平衡 Cube 的 t=1/sqrt(2)、r=i/sqrt(2) 两次作用
    transmission = 1.0 / math.sqrt(2.0)
    reflection = 1.0j / math.sqrt(2.0)
    top_phase = cmath.exp(
        1.0j * phase_multiplier * relative_phase,
    )
    right_return = transmission * right_mirror_scalar
    top_return = reflection * top_mirror_scalar * top_phase
    left = transmission * right_return + reflection * top_return
    bottom = reflection * right_return + transmission * top_return
    return abs(left) ** 2, abs(bottom) ** 2


def _maximum_port_separation(
    baseline: tuple[float, float],
    challenged: tuple[float, float],
) -> float:
    return max(
        abs(baseline_value - challenged_value)
        for baseline_value, challenged_value in zip(
            baseline,
            challenged,
            strict=True,
        )
    )


def _run_assembly(assembly: Assembly) -> tuple[float, float]:
    workstation = Workstation.cpu()
    workstation.host(assembly)
    try:
        outputs, _record = workstation.run(assembly)
    finally:
        workstation.release(assembly)
    left = outputs["left_intensity"]
    bottom = outputs["bottom_intensity"]
    assert isinstance(left, Intensity)
    assert isinstance(bottom, Intensity)
    return (
        float(left.values.mean().item()),
        float(bottom.values.mean().item()),
    )


def _build_second_owner_counterfactual() -> Assembly:
    baseline = build_assembly(relative_phase=NONDEGENERATE_PHASE)
    source = cast(PlaneWave, baseline._component("source"))  # noqa: SLF001
    outward_cube_owner = cast(  # noqa: SLF001
        IdealNonpolarizingCubeBeamSplitter,
        baseline._component("cube"),
    )
    right_mirror = cast(  # noqa: SLF001
        IdealPlanarMirror,
        baseline._component("right_mirror"),
    )
    top_mirror = cast(  # noqa: SLF001
        IdealPlanarMirror,
        baseline._component("top_mirror"),
    )
    right_out = cast(  # noqa: SLF001
        ScalarAngularSpectrum,
        baseline._component("right_out"),
    )
    right_back = cast(  # noqa: SLF001
        ScalarAngularSpectrum,
        baseline._component("right_back"),
    )
    top_out = cast(  # noqa: SLF001
        ScalarAngularSpectrum,
        baseline._component("top_out"),
    )
    top_back = cast(  # noqa: SLF001
        ScalarAngularSpectrum,
        baseline._component("top_back"),
    )
    second_cube_owner = IdealNonpolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=0.0,
    )
    left_detector = IntensityDetection()
    bottom_detector = IntensityDetection()
    grid = SpatialGrid.centered(
        sample_counts=SAMPLE_COUNTS,
        sample_spacing=SAMPLE_SPACING,
    )

    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    for name, component in (
        ("right_out", right_out),
        ("right_back", right_back),
        ("top_out", top_out),
        ("top_back", top_back),
        ("left_detector", left_detector),
        ("bottom_detector", bottom_detector),
    ):
        assembly.include(component, name=name)
    assembly.include_directional(outward_cube_owner, name="cube")
    assembly.include_directional(
        second_cube_owner,
        name="second_cube",
    )
    assembly.include_directional(right_mirror, name="right_mirror")
    assembly.include_directional(top_mirror, name="top_mirror")

    outward_cube = assembly.wave_encounter(
        outward_cube_owner,
        name="outward_cube",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    right_mirror_turn = assembly.wave_encounter(
        right_mirror,
        name="right_mirror_turn",
        incident_terminals=(MirrorTerminal.FRONT,),
    )
    top_mirror_turn = assembly.wave_encounter(
        top_mirror,
        name="top_mirror_turn",
        incident_terminals=(MirrorTerminal.FRONT,),
    )
    return_cube = assembly.wave_encounter(
        second_cube_owner,
        name="return_cube",
        incident_terminals=(CubeTerminal.TOP, CubeTerminal.RIGHT),
    )

    assembly.connect(
        source,
        outward_cube,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        outward_cube,
        right_out,
        source_terminal=CubeTerminal.RIGHT,
    )
    assembly.connect(
        right_out,
        right_mirror_turn,
        destination_terminal=MirrorTerminal.FRONT,
    )
    assembly.connect(
        right_mirror_turn,
        right_back,
        source_terminal=MirrorTerminal.FRONT,
    )
    assembly.connect(
        right_back,
        return_cube,
        destination_terminal=CubeTerminal.RIGHT,
    )
    assembly.connect(
        outward_cube,
        top_out,
        source_terminal=CubeTerminal.TOP,
    )
    assembly.connect(
        top_out,
        top_mirror_turn,
        destination_terminal=MirrorTerminal.FRONT,
    )
    assembly.connect(
        top_mirror_turn,
        top_back,
        source_terminal=MirrorTerminal.FRONT,
    )
    assembly.connect(
        top_back,
        return_cube,
        destination_terminal=CubeTerminal.TOP,
    )
    assembly.connect(
        return_cube,
        left_detector,
        source_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        return_cube,
        bottom_detector,
        source_terminal=CubeTerminal.BOTTOM,
    )
    assembly.expose(left_detector, name="left_intensity")
    assembly.expose(bottom_detector, name="bottom_intensity")
    assembly.freeze()
    return assembly


def test_fixture_pins_the_complete_relative_reference_card() -> None:
    assembly = build_assembly(relative_phase=NONDEGENERATE_PHASE)
    source = cast(PlaneWave, assembly._component("source"))  # noqa: SLF001
    cube = cast(  # noqa: SLF001
        IdealNonpolarizingCubeBeamSplitter,
        assembly._component("cube"),
    )
    right_mirror = cast(  # noqa: SLF001
        IdealPlanarMirror,
        assembly._component("right_mirror"),
    )
    top_mirror = cast(  # noqa: SLF001
        IdealPlanarMirror,
        assembly._component("top_mirror"),
    )
    expected_top_length = RIGHT_ARM_LENGTH + WAVELENGTH / 12.0
    grid = SpatialGrid.centered(
        sample_counts=SAMPLE_COUNTS,
        sample_spacing=SAMPLE_SPACING,
    )
    field = source(grid)

    assert WAVELENGTH == 632.8e-9
    assert SPECTRAL_WEIGHT == 1.0
    assert REFRACTIVE_INDEX == 1.0
    assert SAMPLE_COUNTS == (8, 12)
    assert SAMPLE_SPACING == (7.0e-6, 11.0e-6)
    assert RIGHT_ARM_LENGTH == 1.0e-3
    assert RELATIVE_PHASE_POINTS == (
        0.0,
        math.pi / 3.0,
        2.0 * math.pi / 3.0,
        math.pi,
    )
    assert TOP_ARM_OFFSETS == (
        0.0,
        WAVELENGTH / 12.0,
        WAVELENGTH / 6.0,
        WAVELENGTH / 4.0,
    )
    assert DENSE_COMPLEX_OPERATOR_MAX_ABSOLUTE_ERROR == 5.0e-13
    assert PORT_RATIO_ABSOLUTE_ERROR == 2.0e-12
    assert COMPLEMENTARY_SUM_ABSOLUTE_ERROR == 2.0e-12
    assert VISIBILITY_ABSOLUTE_ERROR == 2.0e-12
    assert MINIMUM_COUNTERFACTUAL_PORT_SEPARATION == 0.20

    assert torch.equal(
        cast(torch.Tensor, source.wavelengths),
        torch.tensor((WAVELENGTH,), dtype=torch.float64),
    )
    assert torch.equal(
        cast(torch.Tensor, source.spectral_weights),
        torch.tensor((SPECTRAL_WEIGHT,), dtype=torch.float64),
    )
    assert torch.equal(
        cast(torch.Tensor, source.polarization_state),
        torch.tensor(
            (1.0 + 0.0j, 0.0 + 0.0j),
            dtype=torch.complex128,
        ),
    )
    assert field.normalization is FieldNormalization.RELATIVE
    assert torch.equal(
        field.envelope[..., 0, :, :],
        torch.ones((1, 8, 12), dtype=torch.complex128),
    )
    assert torch.count_nonzero(field.envelope[..., 1, :, :]) == 0
    assert torch.equal(cube.origin, torch.zeros(3, dtype=torch.float64))
    assert torch.equal(
        cube.route_right,
        torch.tensor((1.0, 0.0, 0.0), dtype=torch.float64),
    )
    assert torch.equal(
        cube.route_top,
        torch.tensor((0.0, 1.0, 0.0), dtype=torch.float64),
    )
    assert cube.coating_diagonal is CubeCoatingDiagonal.RISING
    assert float(cube.mixing_angle) == math.pi / 4.0
    assert torch.equal(
        right_mirror.origin,
        torch.tensor(
            (RIGHT_ARM_LENGTH, 0.0, 0.0),
            dtype=torch.float64,
        ),
    )
    assert torch.equal(
        top_mirror.origin,
        torch.tensor((0.0, expected_top_length, 0.0), dtype=torch.float64),
    )
    assert torch.equal(
        right_mirror.outward_normal,
        torch.tensor((-1.0, 0.0, 0.0), dtype=torch.float64),
    )
    assert torch.equal(
        top_mirror.outward_normal,
        torch.tensor((0.0, -1.0, 0.0), dtype=torch.float64),
    )
    assert torch.equal(
        right_mirror.transverse_up,
        torch.tensor((0.0, 0.0, 1.0), dtype=torch.float64),
    )
    assert torch.equal(top_mirror.transverse_up, right_mirror.transverse_up)

    expected_distances = {
        "right_out": RIGHT_ARM_LENGTH,
        "right_back": RIGHT_ARM_LENGTH,
        "top_out": expected_top_length,
        "top_back": expected_top_length,
    }
    for name, expected in expected_distances.items():
        propagation = cast(  # noqa: SLF001
            ScalarAngularSpectrum,
            assembly._component(name),
        )
        assert float(propagation.axial_distance) == expected

    right_out = cast(  # noqa: SLF001
        ScalarAngularSpectrum,
        assembly._component("right_out"),
    )
    right_back = cast(  # noqa: SLF001
        ScalarAngularSpectrum,
        assembly._component("right_back"),
    )
    top_out = cast(  # noqa: SLF001
        ScalarAngularSpectrum,
        assembly._component("top_out"),
    )
    top_back = cast(  # noqa: SLF001
        ScalarAngularSpectrum,
        assembly._component("top_back"),
    )
    right_round_trip = right_back(right_out(field))
    top_round_trip = top_back(top_out(field))
    assert float(right_round_trip.path_reference.lengths[0]) == (
        2.0 * REFRACTIVE_INDEX * RIGHT_ARM_LENGTH
    )
    assert float(top_round_trip.path_reference.lengths[0]) == (
        2.0 * REFRACTIVE_INDEX * expected_top_length
    )


def test_one_cube_owner_is_reused_and_every_output_is_disposed() -> None:
    assembly = build_assembly(relative_phase=NONDEGENERATE_PHASE)
    facts = assembly._execution_facts()  # noqa: SLF001
    encounters = {
        encounter.encounter_name: encounter
        for encounter in facts.encounters
    }

    assert assembly.exposed_names() == (
        "left_intensity",
        "bottom_intensity",
    )
    assert encounters["outward_cube"].owner_name == "cube"
    assert encounters["return_cube"].owner_name == "cube"
    assert encounters["outward_cube"].incident_terminals == ("left",)
    assert encounters["return_cube"].incident_terminals == (
        "top",
        "right",
    )
    assert tuple(
        name for name in assembly.state_dict() if name.startswith("cube.")
    ) == (
        "cube.origin",
        "cube.route_right",
        "cube.route_top",
        "cube._coating_diagonal_code",
        "cube.mixing_angle",
    )
    assert len(facts.dispositions) == 6
    assert all(
        disposition.connection_targets
        and not disposition.exposure_names
        and disposition.route_end_reason is None
        for disposition in facts.dispositions
    )


def test_frozen_relative_sweep_matches_analytic_port_ratios() -> None:
    result = run(workstation=Workstation.cpu())

    assert tuple(
        observation.relative_phase
        for observation in result.observations
    ) == RELATIVE_PHASE_POINTS
    for observation in result.observations:
        expected_left = math.sin(observation.relative_phase / 2.0) ** 2
        expected_bottom = math.cos(observation.relative_phase / 2.0) ** 2
        assert observation.left_ratio == pytest.approx(
            expected_left,
            abs=PORT_RATIO_ABSOLUTE_ERROR,
        )
        assert observation.bottom_ratio == pytest.approx(
            expected_bottom,
            abs=PORT_RATIO_ABSOLUTE_ERROR,
        )
        assert observation.ratio_sum == pytest.approx(
            1.0,
            abs=COMPLEMENTARY_SUM_ABSOLUTE_ERROR,
        )
    assert result.left_visibility == pytest.approx(
        1.0,
        abs=VISIBILITY_ABSOLUTE_ERROR,
    )
    assert result.bottom_visibility == pytest.approx(
        1.0,
        abs=VISIBILITY_ABSOLUTE_ERROR,
    )


def test_one_arm_mirror_omission_is_visible_at_pi_over_three() -> None:
    baseline = _independent_port_ratios(NONDEGENERATE_PHASE)
    challenged = _independent_port_ratios(
        NONDEGENERATE_PHASE,
        right_mirror_scalar=1.0 + 0.0j,
    )

    assert _maximum_port_separation(baseline, challenged) >= (
        MINIMUM_COUNTERFACTUAL_PORT_SEPARATION
    )


def test_phase_omission_and_double_count_are_discriminating() -> None:
    baseline = _independent_port_ratios(NONDEGENERATE_PHASE)
    omitted_phase = 0.0 * NONDEGENERATE_PHASE
    doubled_phase = 2.0 * NONDEGENERATE_PHASE
    omitted = _independent_port_ratios(
        NONDEGENERATE_PHASE,
        phase_multiplier=0.0,
    )
    doubled = _independent_port_ratios(
        NONDEGENERATE_PHASE,
        phase_multiplier=2.0,
    )

    assert omitted_phase == 0.0
    assert doubled_phase == 2.0 * math.pi / 3.0
    assert omitted[0] == pytest.approx(0.0, abs=PORT_RATIO_ABSOLUTE_ERROR)
    assert doubled[0] == pytest.approx(
        0.75,
        abs=PORT_RATIO_ABSOLUTE_ERROR,
    )
    assert _maximum_port_separation(baseline, omitted) >= (
        MINIMUM_COUNTERFACTUAL_PORT_SEPARATION
    )
    assert _maximum_port_separation(baseline, doubled) >= (
        MINIMUM_COUNTERFACTUAL_PORT_SEPARATION
    )


def test_split_then_add_intensity_loses_return_interference() -> None:
    baseline = _independent_port_ratios(NONDEGENERATE_PHASE)
    transmission = 1.0 / math.sqrt(2.0)
    reflection = 1.0j / math.sqrt(2.0)
    split_then_add_left = (
        abs(transmission * transmission) ** 2
        + abs(reflection * reflection) ** 2
    )

    assert split_then_add_left == pytest.approx(0.5)
    assert abs(split_then_add_left - baseline[0]) >= (
        MINIMUM_COUNTERFACTUAL_PORT_SEPARATION
    )


def test_real_balanced_cube_counterfactual_creates_power() -> None:
    # 错误模型仅存在于独立 oracle：它把合格反射 i/sqrt(2) 错写成实数
    inverse_root_two = 1.0 / math.sqrt(2.0)
    correct = torch.tensor(
        (
            (inverse_root_two, 1.0j * inverse_root_two),
            (1.0j * inverse_root_two, inverse_root_two),
        ),
        dtype=torch.complex128,
    )
    forbidden_real = torch.full(
        (2, 2),
        inverse_root_two,
        dtype=torch.complex128,
    )
    incident = torch.ones(2, dtype=torch.complex128)
    identity = torch.eye(2, dtype=torch.complex128)

    assert float(torch.max(torch.abs(correct.mH @ correct - identity))) <= (
        DENSE_COMPLEX_OPERATOR_MAX_ABSOLUTE_ERROR
    )
    correct_power = float(torch.sum(torch.abs(correct @ incident) ** 2))
    forbidden_power = float(
        torch.sum(torch.abs(forbidden_real @ incident) ** 2)
    )
    assert correct_power == pytest.approx(2.0)
    assert forbidden_power == pytest.approx(4.0)
    assert forbidden_power - correct_power >= (
        MINIMUM_COUNTERFACTUAL_PORT_SEPARATION
    )


def test_second_cube_owner_mutation_fails_the_physical_oracle() -> None:
    baseline = _run_assembly(
        build_assembly(relative_phase=NONDEGENERATE_PHASE),
    )
    challenged = _run_assembly(_build_second_owner_counterfactual())

    assert _maximum_port_separation(baseline, challenged) >= (
        MINIMUM_COUNTERFACTUAL_PORT_SEPARATION
    )


def test_missing_directional_output_disposition_rejects_freeze() -> None:
    grid = SpatialGrid.centered(
        sample_counts=SAMPLE_COUNTS,
        sample_spacing=SAMPLE_SPACING,
    )
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=WAVELENGTH),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    cube = IdealNonpolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=math.pi / 4.0,
    )
    assembly = Assembly()
    assembly.include(source, name="source", grid=grid)
    assembly.include_directional(cube, name="cube")
    encounter = assembly.wave_encounter(
        cube,
        name="outward_cube",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    assembly.connect(
        source,
        encounter,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.expose(
        encounter,
        name="right_field",
        source_terminal=CubeTerminal.RIGHT,
    )

    with pytest.raises(AssemblyError) as rejected:
        assembly.freeze()

    assert rejected.value.identity.startswith(
        "assembly_directional_output_disposition_missing:"
    )
    assert not assembly.is_frozen


def test_example_has_no_manual_field_sum_or_flattened_topology() -> None:
    source = (
        PROJECT_ROOT
        / "examples"
        / "analytic_michelson_interferometer"
        / "example.py"
    ).read_text(encoding="utf-8")

    assert "envelope" not in source
    assert "coherent_combination" not in source.casefold()
    assert "intensity_combination" not in source.casefold()
    assert "torch" not in source
    assert "Experiment" not in source
    assert "notebook" not in source.casefold()
    assert source.count("assembly.wave_encounter(") == 4
    assert source.count("assembly.connect(") == 11

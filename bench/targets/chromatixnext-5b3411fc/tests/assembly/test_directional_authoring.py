from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import itertools
import math
import pickle

import pytest
import torch

from chromatix_next.errors import AssemblyError
from chromatix_next.optics import (
    Assembly,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
)
from chromatix_next.optics._assembly_facts import _FrozenAssembly
from chromatix_next.optics.assembly import RayEncounter, WaveEncounter
from chromatix_next.optics.detection import IntensityDetection
from chromatix_next.optics.element.ideal_cube_beam_splitter import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
)
from chromatix_next.optics.element.ideal_planar_mirror import (
    IdealPlanarMirror,
    MirrorTerminal,
)
from chromatix_next.optics.element.ideal_thin_lens import IdealThinLens
from chromatix_next.optics.source import CollimatedRaySource, PlaneWave


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(4, 6),
        sample_spacing=(0.5e-6, 0.7e-6),
    )


def _spectrum() -> Spectrum:
    return Spectrum.monochromatic(wavelength=1.55e-6)


def _wave_source() -> PlaneWave:
    return PlaneWave(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )


def _ray_source() -> CollimatedRaySource:
    return CollimatedRaySource(
        spectrum=_spectrum(),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        ray_power=1.0,
    )


def _cube() -> IdealNonpolarizingCubeBeamSplitter:
    return IdealNonpolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=math.pi / 4.0,
    )


def _mirror() -> IdealPlanarMirror:
    return IdealPlanarMirror(
        origin=(0.0, 0.0, 0.0),
        outward_normal=(-1.0, 0.0, 0.0),
        transverse_up=(0.0, 0.0, 1.0),
    )


def _serialized_authoring(assembly: Assembly) -> bytes:
    return pickle.dumps(assembly, protocol=5)


def _assert_identity(
    assembly: Assembly,
    identity: str,
    action: object,
) -> None:
    before = _serialized_authoring(assembly)
    with pytest.raises(AssemblyError) as rejected:
        assert callable(action)
        action()
    assert rejected.value.identity == identity
    assert _serialized_authoring(assembly) == before


def _directional_identity(
    base: str,
    *,
    owner: str = "-",
    encounter: str = "-",
    incident: str = "-",
    outgoing: str = "-",
    route: str = "-",
    underlying: str = "-",
) -> str:
    return (
        f"{base}:owner={owner}:encounter={encounter}:incident={incident}:"
        f"outgoing={outgoing}:route={route}:underlying={underlying}"
    )


def test_encounter_references_are_distinct_frozen_state_free_scoped_types() -> None:
    assembly = Assembly()
    cube = _cube()
    mirror = _mirror()
    assembly.include_directional(cube, name="cube")
    assembly.include_directional(mirror, name="mirror")
    wave = assembly.wave_encounter(
        cube,
        name="wave",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    ray = assembly.ray_encounter(
        mirror,
        name="ray",
        incident_terminal=MirrorTerminal.FRONT,
    )

    assert type(wave) is WaveEncounter
    assert type(ray) is RayEncounter
    assert type(wave) is not type(ray)
    for reference in (wave, ray):
        assert is_dataclass(reference)
        assert tuple(field.name for field in fields(reference)) == (
            "_scope",
            "_name",
        )
        assert not isinstance(reference, torch.nn.Module)
        assert not any(
            isinstance(value, (torch.Tensor, torch.nn.Module))
            or callable(value)
            for value in (
                reference._scope,  # noqa: SLF001
                reference._name,  # noqa: SLF001
            )
        )
        with pytest.raises(FrozenInstanceError):
            reference._name = "changed"  # type: ignore[misc]  # noqa: SLF001

    other = Assembly()
    other_cube = _cube()
    other.include_directional(other_cube, name="cube")
    other_wave = other.wave_encounter(
        other_cube,
        name="wave",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    _assert_identity(
        assembly,
        _directional_identity("assembly_connect_endpoint_category_invalid"),
        lambda: assembly.connect(
            wave,
            other_wave,
            source_terminal=CubeTerminal.RIGHT,
            destination_terminal=CubeTerminal.LEFT,
        ),
    )


def test_all_fifteen_cube_wave_incidence_masks_author_in_canonical_order() -> None:
    assembly = Assembly()
    cube = _cube()
    assembly.include_directional(cube, name="cube")
    terminal_order = tuple(CubeTerminal)
    mask_index = 0
    for count in range(1, len(terminal_order) + 1):
        for mask in itertools.combinations(terminal_order, count):
            assembly.wave_encounter(
                cube,
                name=f"mask_{mask_index}",
                incident_terminals=tuple(reversed(mask)),
            )
            mask_index += 1

    assert mask_index == 15
    assert len(assembly._encounters) == 15  # noqa: SLF001
    for declaration in assembly._encounters:  # noqa: SLF001
        positions = tuple(
            terminal_order.index(CubeTerminal(value))
            for value in declaration.incident_terminals
        )
        assert positions == tuple(sorted(positions))


def test_directional_owner_and_encounter_identities_have_exact_locators() -> None:
    empty = Assembly()
    _assert_identity(
        empty,
        _directional_identity(
            "assembly_include_directional_owner_invalid",
            owner="ordinary",
        ),
        lambda: empty.include_directional(
            _wave_source(),
            name="ordinary",
        ),
    )

    assembly = Assembly()
    cube = _cube()
    assembly.include_directional(cube, name="cube")
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_include_directional_owner_duplicate",
            owner="cube",
        ),
        lambda: assembly.include_directional(cube, name="second_cube"),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_name_invalid",
            owner="cube",
        ),
        lambda: assembly.wave_encounter(
            cube,
            name="not valid",
            incident_terminals=(CubeTerminal.LEFT,),
        ),
    )
    split = assembly.wave_encounter(
        cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_duplicate_name",
            owner="cube",
            encounter="split",
        ),
        lambda: assembly.wave_encounter(
            cube,
            name="split",
            incident_terminals=(CubeTerminal.LEFT,),
        ),
    )
    foreign_cube = _cube()
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_owner_unknown",
            encounter="foreign",
        ),
        lambda: assembly.wave_encounter(
            foreign_cube,
            name="foreign",
            incident_terminals=(CubeTerminal.LEFT,),
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_owner_unsupported",
            owner="cube",
            encounter="unsupported",
        ),
        lambda: assembly._declare_encounter(  # noqa: SLF001
            cube,
            name="unsupported",
            domain="hybrid",
            incident_terminals=(CubeTerminal.LEFT,),
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_route_end_output_unknown",
            owner="cube",
            encounter="split",
            outgoing="bottom",
        ),
        lambda: assembly.end_route(
            split,
            source_terminal=CubeTerminal.BOTTOM,
            reason="outside_modeled_system",
        ),
    )


def test_duplicate_name_precedes_unknown_owner_and_references_need_issuer() -> None:
    assembly = Assembly()
    cube = _cube()
    assembly.include_directional(cube, name="cube")
    assembly.wave_encounter(
        cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    foreign_cube = _cube()
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_duplicate_name",
            encounter="split",
        ),
        lambda: assembly.wave_encounter(
            foreign_cube,
            name="split",
            incident_terminals=(CubeTerminal.LEFT,),
        ),
    )

    for reference_type in (WaveEncounter, RayEncounter):
        with pytest.raises(AssemblyError) as rejected:
            reference_type(
                _issuer=object(),
                _scope=object(),
                _name="direct",
            )
        assert rejected.value.identity == _directional_identity(
            "assembly_encounter_owner_unknown"
        )


def test_invalid_incidence_is_atomic_and_valid_retry_succeeds() -> None:
    assembly = Assembly()
    cube = _cube()
    assembly.include_directional(cube, name="cube")
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_incident_empty",
            owner="cube",
            encounter="split",
        ),
        lambda: assembly.wave_encounter(
            cube,
            name="split",
            incident_terminals=(),
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_incident_duplicate",
            owner="cube",
            encounter="split",
            incident="left",
        ),
        lambda: assembly.wave_encounter(
            cube,
            name="split",
            incident_terminals=(CubeTerminal.LEFT, CubeTerminal.LEFT),
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_terminal_unknown",
            owner="cube",
            encounter="split",
        ),
        lambda: assembly.wave_encounter(
            cube,
            name="split",
            incident_terminals=("left",),  # type: ignore[arg-type]
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_terminal_unknown",
            owner="cube",
            encounter="split",
        ),
        lambda: assembly.wave_encounter(
            cube,
            name="split",
            incident_terminals=[CubeTerminal.LEFT],  # type: ignore[arg-type]
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_terminal_unknown",
            owner="cube",
            encounter="split",
        ),
        lambda: assembly.ray_encounter(
            cube,
            name="split",
            incident_terminal=(CubeTerminal.LEFT,),  # type: ignore[arg-type]
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_encounter_ray_multiple_incident",
            owner="cube",
            encounter="split",
            incident="top",
        ),
        lambda: assembly.ray_encounter(
            cube,
            name="split",
            incident_terminal=(  # type: ignore[arg-type]
                CubeTerminal.LEFT,
                CubeTerminal.TOP,
            ),
        ),
    )
    split = assembly.wave_encounter(
        cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    assert isinstance(split, WaveEncounter)


def test_all_four_endpoint_forms_compile_into_one_frozen_plan() -> None:
    assembly = Assembly()
    source = _wave_source()
    lens = IdealThinLens(grid=_grid(), focal_length=1.0e-3)
    cube = _cube()
    assembly.include(source, name="source", grid=_grid())
    assembly.include(lens, name="lens")
    assembly.include_directional(cube, name="cube")
    first = assembly.wave_encounter(
        cube,
        name="first",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    second = assembly.wave_encounter(
        cube,
        name="second",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    third = assembly.wave_encounter(
        cube,
        name="third",
        incident_terminals=(CubeTerminal.LEFT,),
    )

    assembly.connect(
        source,
        first,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        first,
        lens,
        source_terminal=CubeTerminal.RIGHT,
    )
    assembly.connect(
        lens,
        second,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        second,
        third,
        source_terminal=CubeTerminal.RIGHT,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.end_route(
        first,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )
    assembly.end_route(
        second,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )
    assembly.expose(
        third,
        name="field",
        source_terminal=CubeTerminal.RIGHT,
    )
    assembly.end_route(
        third,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )

    assembly.freeze()
    facts = assembly._frozen_facts  # noqa: SLF001
    assert facts is not None
    assert tuple(step.name for step in facts.replay_order) == (
        "source",
        "first",
        "lens",
        "second",
        "third",
    )
    assert facts.exposure_order == ("field",)
    assert len(facts.value_flows) == 4


def test_valid_ordinary_directional_and_mixed_controls_share_one_replay(
) -> None:
    ordinary = Assembly()
    ordinary_source = _wave_source()
    ordinary_detector = IntensityDetection()
    ordinary.include(ordinary_source, name="source", grid=_grid())
    ordinary.include(ordinary_detector, name="detector")
    ordinary.connect(ordinary_source, ordinary_detector)
    ordinary.expose(ordinary_detector, name="intensity")

    directional = Assembly()
    directional_source = _wave_source()
    directional_cube = _cube()
    directional.include(
        directional_source,
        name="source",
        grid=_grid(),
    )
    directional.include_directional(directional_cube, name="cube")
    directional_split = directional.wave_encounter(
        directional_cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    directional.connect(
        directional_source,
        directional_split,
        destination_terminal=CubeTerminal.LEFT,
    )
    directional.expose(
        directional_split,
        name="right_field",
        source_terminal=CubeTerminal.RIGHT,
    )
    directional.end_route(
        directional_split,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )

    mixed = Assembly()
    mixed_ordinary_source = _wave_source()
    mixed_detector = IntensityDetection()
    mixed_directional_source = _wave_source()
    mixed_cube = _cube()
    mixed.include(
        mixed_ordinary_source,
        name="ordinary_source",
        grid=_grid(),
    )
    mixed.include(mixed_detector, name="detector")
    mixed.include(
        mixed_directional_source,
        name="directional_source",
        grid=_grid(),
    )
    mixed.include_directional(mixed_cube, name="cube")
    mixed_split = mixed.wave_encounter(
        mixed_cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    mixed.connect(mixed_ordinary_source, mixed_detector)
    mixed.connect(
        mixed_directional_source,
        mixed_split,
        destination_terminal=CubeTerminal.LEFT,
    )
    mixed.expose(mixed_detector, name="intensity")
    mixed.expose(
        mixed_split,
        name="right_field",
        source_terminal=CubeTerminal.RIGHT,
    )
    mixed.end_route(
        mixed_split,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )

    controls = (
        (ordinary, ("intensity",)),
        (directional, ("right_field",)),
        (mixed, ("intensity", "right_field")),
    )
    for assembly, exposed_names in controls:
        assembly.freeze()
        facts = assembly._frozen_facts  # noqa: SLF001
        assert isinstance(facts, _FrozenAssembly)
        assert assembly._execution_facts() is facts  # noqa: SLF001
        assert tuple(assembly._replay()) == exposed_names  # noqa: SLF001


def test_category_direction_occupancy_and_type_rejections_are_atomic() -> None:
    assembly = Assembly()
    source = _wave_source()
    second_source = _wave_source()
    ray_source = _ray_source()
    cube = _cube()
    assembly.include(source, name="source", grid=_grid())
    assembly.include(second_source, name="second_source", grid=_grid())
    assembly.include(ray_source, name="ray_source", grid=_grid())
    assembly.include_directional(cube, name="cube")
    wave = assembly.wave_encounter(
        cube,
        name="wave",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    ray = assembly.ray_encounter(
        cube,
        name="ray",
        incident_terminal=CubeTerminal.LEFT,
    )

    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_connect_endpoint_category_invalid",
            owner="cube",
            encounter="wave",
        ),
        lambda: assembly.connect(
            source,
            wave,
            destination_port="left",
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_connect_endpoint_category_invalid",
            owner="cube",
            encounter="wave",
        ),
        lambda: assembly.connect(
            wave,
            source,
            source_port="right",
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_connect_terminal_direction_invalid",
            owner="cube",
            encounter="wave",
            incident="top",
        ),
        lambda: assembly.connect(
            source,
            wave,
            destination_terminal=CubeTerminal.TOP,
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_connect_structural_zero",
            owner="cube",
            encounter="wave",
            outgoing="bottom",
        ),
        lambda: assembly.connect(
            wave,
            ray,
            source_terminal=CubeTerminal.BOTTOM,
            destination_terminal=CubeTerminal.LEFT,
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_connection_domain_mismatch",
            owner="cube",
            encounter="wave",
            incident="left",
        ),
        lambda: assembly.connect(
            ray_source,
            wave,
            destination_terminal=CubeTerminal.LEFT,
        ),
    )
    assembly.connect(
        source,
        wave,
        destination_terminal=CubeTerminal.LEFT,
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_input_port_count_mismatch",
            owner="cube",
            encounter="wave",
            incident="left",
        ),
        lambda: assembly.connect(
            second_source,
            wave,
            destination_terminal=CubeTerminal.LEFT,
        ),
    )


def test_route_end_and_disposition_failures_are_atomic_and_retryable() -> None:
    assembly = Assembly()
    source = _wave_source()
    cube = _cube()
    assembly.include(source, name="source", grid=_grid())
    assembly.include_directional(cube, name="cube")
    split = assembly.wave_encounter(
        cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    assembly.connect(
        source,
        split,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.expose(
        split,
        name="transmitted",
        source_terminal=CubeTerminal.RIGHT,
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_route_end_reason_invalid",
            owner="cube",
            encounter="split",
            outgoing="top",
        ),
        lambda: assembly.end_route(
            split,
            source_terminal=CubeTerminal.TOP,
            reason="absorbed",
        ),
    )
    _assert_identity(
        assembly,
        _directional_identity(
            "assembly_route_end_output_disposed",
            owner="cube",
            encounter="split",
            outgoing="right",
        ),
        lambda: assembly.end_route(
            split,
            source_terminal=CubeTerminal.RIGHT,
            reason="outside_modeled_system",
        ),
    )
    before = _serialized_authoring(assembly)
    with pytest.raises(AssemblyError) as rejected:
        assembly.freeze()
    assert rejected.value.identity == _directional_identity(
        "assembly_directional_output_disposition_missing",
        owner="cube",
        encounter="split",
        outgoing="top",
    )
    assert not assembly.is_frozen
    assert assembly._frozen_facts is None  # noqa: SLF001
    assert _serialized_authoring(assembly) == before

    assembly.end_route(
        split,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )
    assembly.freeze()
    assert assembly.is_frozen


def test_all_route_ends_without_exposure_reject_atomically_and_retry() -> None:
    assembly = Assembly()
    source = _wave_source()
    cube = _cube()
    assembly.include(source, name="source", grid=_grid())
    assembly.include_directional(cube, name="cube")
    split = assembly.wave_encounter(
        cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    assembly.connect(
        source,
        split,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.end_route(
        split,
        source_terminal=CubeTerminal.RIGHT,
        reason="outside_modeled_system",
    )
    assembly.end_route(
        split,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )

    for operation in (assembly.check, assembly.freeze):
        _assert_identity(
            assembly,
            "assembly_output_not_exposed",
            operation,
        )
        assert not assembly.is_frozen
        assert assembly._frozen_facts is None  # noqa: SLF001

    assembly.expose(source, name="incident_field")
    assert assembly.check() is None
    assembly.freeze()

    assert assembly.is_frozen
    assert isinstance(assembly._frozen_facts, _FrozenAssembly)  # noqa: SLF001
    assert tuple(assembly._replay()) == ("incident_field",)  # noqa: SLF001


def test_directional_owner_only_is_empty_and_retryable() -> None:
    assembly = Assembly()
    assembly.include_directional(_cube(), name="cube")

    for operation in (assembly.check, assembly.freeze):
        _assert_identity(
            assembly,
            "assembly_empty",
            operation,
        )
        assert not assembly.is_frozen
        assert assembly._frozen_facts is None  # noqa: SLF001

    source = _wave_source()
    assembly.include(source, name="source", grid=_grid())
    assembly.expose(source, name="field")
    assert assembly.check() is None
    assembly.freeze()

    assert assembly.is_frozen
    assert isinstance(assembly._frozen_facts, _FrozenAssembly)  # noqa: SLF001
    assert tuple(assembly._replay()) == ("field",)  # noqa: SLF001


def test_mutated_owner_state_aggregates_under_exact_assembly_identity() -> None:
    assembly = Assembly()
    cube = _cube()
    assembly.include_directional(cube, name="cube")
    original = cube.mixing_angle.detach().clone()
    with torch.no_grad():
        cube.mixing_angle.fill_(math.nan)
    with pytest.raises(AssemblyError) as rejected:
        assembly.check()
    assert rejected.value.identity == "; ".join(
        (
            "assembly_directional_owner_state_invalid:owner=cube:"
            "encounter=-:incident=-:outgoing=-:route=-:underlying="
            "cube_beam_splitter_mixing_angle_nonfinite",
            "assembly_empty",
        )
    )
    assert not assembly.is_frozen
    with torch.no_grad():
        cube.mixing_angle.copy_(original)


def test_owner_state_failure_precedes_all_missing_dispositions() -> None:
    assembly = Assembly()
    source = _wave_source()
    cube = _cube()
    assembly.include(source, name="source", grid=_grid())
    assembly.include_directional(cube, name="cube")
    split = assembly.wave_encounter(
        cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    assembly.connect(
        source,
        split,
        destination_terminal=CubeTerminal.LEFT,
    )
    with torch.no_grad():
        cube.mixing_angle.fill_(math.nan)

    with pytest.raises(AssemblyError) as rejected:
        assembly.check()
    assert rejected.value.identity == "; ".join(
        (
            _directional_identity(
                "assembly_directional_owner_state_invalid",
                owner="cube",
                underlying="cube_beam_splitter_mixing_angle_nonfinite",
            ),
            _directional_identity(
                "assembly_directional_output_disposition_missing",
                owner="cube",
                encounter="split",
                outgoing="top",
            ),
            _directional_identity(
                "assembly_directional_output_disposition_missing",
                owner="cube",
                encounter="split",
                outgoing="right",
            ),
        )
    )
    assert not assembly.is_frozen


def test_ordinary_expose_accepts_existing_port_and_frozen_source_port_forms() -> None:
    first = Assembly()
    first_source = _wave_source()
    first.include(first_source, name="source", grid=_grid())
    first.expose(first_source, name="field", port=None)
    first.freeze()

    second = Assembly()
    second_source = _wave_source()
    second.include(second_source, name="source", grid=_grid())
    second.expose(second_source, name="field", source_port=None)
    second.freeze()
    assert first.exposed_names() == second.exposed_names() == ("field",)

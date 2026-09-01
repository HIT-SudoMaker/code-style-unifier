from __future__ import annotations

from dataclasses import fields
from typing import Literal

import pytest
import torch

from chromatix_next.errors import AssemblyError
from chromatix_next.optics import (
    Assembly,
    ConstantMedium,
    OpticalField,
    Polarization,
    PropagationDirection,
    SpatialGrid,
    Spectrum,
    Vacuum,
    _assembly_facts,
    _route_geometry,
)
from chromatix_next.optics.element.ideal_cube_beam_splitter import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
)
from chromatix_next.optics.element.ideal_planar_mirror import (
    IdealPlanarMirror,
    MirrorTerminal,
)
from chromatix_next.optics.propagation import ScalarAngularSpectrum
from chromatix_next.optics.source import PlaneWave

_ARM_LENGTH = 1.0e-3


class _ThickSampleProbe(torch.nn.Module):
    # 仅以外部厚度参与 Route 的未来深 Propagation 探针

    axial_distance: torch.Tensor

    def __init__(self, *, axial_distance: float) -> None:
        super().__init__()
        self.register_buffer(
            "axial_distance",
            torch.tensor(axial_distance, dtype=torch.float64),
        )

    @property
    def role(self) -> Literal["propagation"]:
        return "propagation"

    def forward(self, field: OpticalField) -> OpticalField:
        return field

    @property
    def internal_slices(self) -> tuple[torch.Tensor, ...]:
        raise AssertionError("Route 不得检查 Thick Sample 的内部切片")


def _grid() -> SpatialGrid:
    return SpatialGrid.centered(
        sample_counts=(4, 6),
        sample_spacing=(0.5e-6, 0.7e-6),
    )


def _source() -> PlaneWave:
    return PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
        polarization=Polarization.linear_x(),
        medium=Vacuum(),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )


def _cube() -> IdealNonpolarizingCubeBeamSplitter:
    return IdealNonpolarizingCubeBeamSplitter(
        origin=(0.0, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 1.0, 0.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=0.25,
    )


def _mirror(
    *,
    origin: tuple[float, float, float] = (_ARM_LENGTH, 0.0, 0.0),
    outward_normal: tuple[float, float, float] = (-1.0, 0.0, 0.0),
    transverse_up: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> IdealPlanarMirror:
    return IdealPlanarMirror(
        origin=origin,
        outward_normal=outward_normal,
        transverse_up=transverse_up,
    )


def _author_one_way(
    *,
    propagation_actions: tuple[torch.nn.Module, ...],
    mirror: IdealPlanarMirror | None = None,
) -> tuple[Assembly, tuple[torch.nn.Module, ...]]:
    assembly = Assembly()
    source = _source()
    cube = _cube()
    turn_owner = _mirror() if mirror is None else mirror
    assembly.include(source, name="source", grid=_grid())
    for index, propagation in enumerate(propagation_actions):
        assembly.include(propagation, name=f"propagation_{index}")
    assembly.include_directional(cube, name="cube")
    assembly.include_directional(turn_owner, name="mirror")
    split = assembly.wave_encounter(
        cube,
        name="split",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    turn = assembly.wave_encounter(
        turn_owner,
        name="turn",
        incident_terminals=(MirrorTerminal.FRONT,),
    )
    assembly.connect(
        source,
        split,
        destination_terminal=CubeTerminal.LEFT,
    )
    previous: torch.nn.Module | object = split
    for index, propagation in enumerate(propagation_actions):
        if index == 0:
            assembly.connect(
                split,
                propagation,
                source_terminal=CubeTerminal.RIGHT,
            )
        else:
            assembly.connect(previous, propagation)
        previous = propagation
    if propagation_actions:
        assembly.connect(
            previous,
            turn,
            destination_terminal=MirrorTerminal.FRONT,
        )
    else:
        assembly.connect(
            split,
            turn,
            source_terminal=CubeTerminal.RIGHT,
            destination_terminal=MirrorTerminal.FRONT,
        )
    assembly.end_route(
        split,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )
    assembly.expose(
        turn,
        name="returned",
        source_terminal=MirrorTerminal.FRONT,
    )
    return assembly, propagation_actions


def _route_identity(base: str) -> str:
    route = "split.right.outgoing__to__turn.front.incident"
    return (
        f"{base}:owner=cube:encounter=split:incident=front:outgoing=right:"
        f"route={route}:underlying=-"
    )


def _scalar_propagation(distance: float) -> ScalarAngularSpectrum:
    return ScalarAngularSpectrum(axial_distance=distance)


def test_freeze_derives_route_and_accepts_ordered_multiple_propagations() -> None:
    assembly, _ = _author_one_way(
        propagation_actions=(
            _scalar_propagation(_ARM_LENGTH / 3.0),
            _scalar_propagation(2.0 * _ARM_LENGTH / 3.0),
        ),
    )

    assembly.freeze()
    facts = assembly._execution_facts()  # noqa: SLF001

    assert tuple(route.route_name for route in facts.route_segments) == (
        "split.right.outgoing__to__turn.front.incident",
    )
    route = facts.route_segments[0]
    assert route.inline_component_names == (
        "propagation_0",
        "propagation_1",
    )
    assert route.source_frame is None
    assert route.destination_frame is None
    assert route.basis_transport is not None
    assert (
        route.source_value.encounter_name,
        route.source_value.owner_name,
        route.source_value.terminal,
        route.source_value.direction,
    ) == ("split", "cube", "right", "outgoing")
    assert (
        route.destination_value.encounter_name,
        route.destination_value.owner_name,
        route.destination_value.terminal,
        route.destination_value.direction,
    ) == ("turn", "mirror", "front", "incident")


def test_zero_adjacency_and_reversed_world_axis_use_no_implicit_distance() -> None:
    adjacent, _ = _author_one_way(
        propagation_actions=(),
        mirror=_mirror(origin=(0.0, 0.0, 0.0)),
    )
    adjacent.freeze()
    assert adjacent._execution_facts().route_segments  # noqa: SLF001

    source = _route_geometry._terminal_frame_input(
        owner_name="mirror",
        terminal="front",
        frame=_mirror()._terminal_frame(MirrorTerminal.FRONT),  # noqa: SLF001
    )
    destination = _route_geometry._terminal_frame_input(
        owner_name="cube",
        terminal="right",
        frame=_cube()._terminal_frame(CubeTerminal.RIGHT),  # noqa: SLF001
    )
    reversed_route = _route_geometry._validate_route(
        source=source,
        destination=destination,
        propagation_displacements=(_ARM_LENGTH,),
    )
    assert reversed_route.failure is None


@pytest.mark.parametrize(
    ("distances", "expected_identity"),
    (
        ((), "assembly_route_segment_geometry_mismatched"),
        ((_ARM_LENGTH, _ARM_LENGTH), "assembly_route_segment_geometry_mismatched"),
        ((-_ARM_LENGTH,), "assembly_route_segment_geometry_mismatched"),
    ),
)
def test_missing_double_counted_and_negative_directional_distance_reject(
    distances: tuple[float, ...],
    expected_identity: str,
) -> None:
    assembly, _ = _author_one_way(
        propagation_actions=tuple(
            _scalar_propagation(distance)
            for distance in distances
        ),
    )

    with pytest.raises(AssemblyError) as rejected:
        assembly.freeze()

    assert rejected.value.identity == _route_identity(expected_identity)
    assert not assembly.is_frozen


def test_unresolvable_distance_has_exact_identity_and_freeze_is_atomic() -> None:
    propagation = _scalar_propagation(_ARM_LENGTH)
    assembly, _ = _author_one_way(
        propagation_actions=(propagation,),
    )
    propagation.axial_distance = torch.empty(
        (),
        dtype=torch.float64,
        device="meta",
    )

    with pytest.raises(AssemblyError) as rejected:
        assembly.freeze()

    assert rejected.value.identity == _route_identity(
        "assembly_route_segment_distance_unresolvable"
    )
    assert not assembly.is_frozen
    assert assembly._frozen_facts is None  # noqa: SLF001


def test_geometry_failure_allows_state_repair_and_valid_freeze_retry() -> None:
    propagation = _scalar_propagation(_ARM_LENGTH * 0.5)
    assembly, _ = _author_one_way(
        propagation_actions=(propagation,),
    )
    with pytest.raises(AssemblyError) as rejected:
        assembly.freeze()
    assert rejected.value.identity == _route_identity(
        "assembly_route_segment_geometry_mismatched"
    )
    assert not assembly.is_frozen

    with torch.no_grad():
        propagation.axial_distance.copy_(
            torch.tensor(_ARM_LENGTH, dtype=torch.float64)
        )
    assembly.freeze()
    assert assembly.is_frozen


def test_direction_and_nonpermutation_basis_fail_at_exact_route_boundary() -> None:
    wrong_direction, _ = _author_one_way(
        propagation_actions=(_scalar_propagation(_ARM_LENGTH),),
        mirror=_mirror(outward_normal=(0.0, -1.0, 0.0)),
    )
    with pytest.raises(AssemblyError) as direction_error:
        wrong_direction.freeze()
    assert direction_error.value.identity == _route_identity(
        "assembly_route_segment_geometry_mismatched"
    )

    inverse_root_two = 2.0**-0.5
    incompatible_basis, _ = _author_one_way(
        propagation_actions=(_scalar_propagation(_ARM_LENGTH),),
        mirror=_mirror(
            transverse_up=(
                0.0,
                inverse_root_two,
                inverse_root_two,
            )
        ),
    )
    with pytest.raises(AssemblyError) as basis_error:
        incompatible_basis.freeze()
    assert basis_error.value.identity == _route_identity(
        "assembly_route_segment_basis_incompatible"
    )


def test_sampling_and_jones_use_one_signed_axis_swap_on_asymmetric_grid() -> None:
    source_cube = _cube()
    destination_cube = IdealNonpolarizingCubeBeamSplitter(
        origin=(_ARM_LENGTH, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 0.0, 1.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=0.25,
    )
    source = _route_geometry._terminal_frame_input(
        owner_name="source_cube",
        terminal="right",
        frame=source_cube._terminal_frame(CubeTerminal.RIGHT),  # noqa: SLF001
    )
    destination = _route_geometry._terminal_frame_input(
        owner_name="destination_cube",
        terminal="left",
        frame=destination_cube._terminal_frame(CubeTerminal.LEFT),  # noqa: SLF001
    )
    validation = _route_geometry._validate_route(
        source=source,
        destination=destination,
        propagation_displacements=(_ARM_LENGTH,),
    )
    assert validation.failure is None
    assert validation.basis_transport is not None
    transport = validation.basis_transport
    assert transport.destination_yx_from_source_yx == ((0, -1), (1, 0))
    assert transport.destination_hv_from_source_hv == ((0, 1), (-1, 0))

    grid = SpatialGrid(
        sample_counts=(3, 5),
        sample_spacing=(2.0, 7.0),
        first_sample_position=(-2.0, -14.0),
    )
    transformed_grid = _route_geometry._transport_grid(
        grid,
        transport=transport,
    )
    expected_grid = SpatialGrid(
        sample_counts=(5, 3),
        sample_spacing=(7.0, 2.0),
        first_sample_position=(14.0, -2.0),
        orientation=("decreasing", "increasing"),
    )
    assert transformed_grid.is_physically_equivalent_to(expected_grid)
    assert not grid.is_inference_compatible_with(expected_grid)
    assert _route_geometry._grids_coregister_after_transport(
        grid,
        expected_grid,
        transport=transport,
    )

    values = torch.arange(
        2 * 3 * 5,
        dtype=torch.float64,
    ).to(torch.complex128).reshape(1, 1, 2, 3, 5)
    jones_values = _route_geometry._transport_jones_values(
        values,
        transport=transport,
    )
    transported_values = _route_geometry._transport_sampling_values(
        jones_values,
        transport=transport,
    )
    assert torch.equal(
        transported_values[..., 0, :, :],
        values[..., 1, :, :].transpose(-2, -1),
    )
    assert torch.equal(
        transported_values[..., 1, :, :],
        -values[..., 0, :, :].transpose(-2, -1),
    )


def test_equal_shape_misregistration_rejects_before_transform_equivalence() -> None:
    transport = _route_geometry._RouteBasisTransport(
        destination_yx_from_source_yx=((1, 0), (0, 1)),
        destination_hv_from_source_hv=((1, 0), (0, 1)),
    )
    source = SpatialGrid(
        sample_counts=(3, 5),
        sample_spacing=(2.0, 7.0),
        first_sample_position=(-2.0, -14.0),
    )
    shifted = SpatialGrid(
        sample_counts=(3, 5),
        sample_spacing=(2.0, 7.0),
        first_sample_position=(-1.0, -14.0),
    )
    assert not _route_geometry._grids_coregister_after_transport(
        source,
        shifted,
        transport=transport,
    )
    meta_source = source.to(device="meta", dtype=torch.float64)
    meta_destination = _route_geometry._transport_grid(
        meta_source,
        transport=transport,
    )
    assert meta_destination.sample_counts == source.sample_counts
    assert meta_destination.orientation == source.orientation


def test_route_facts_refuse_phase_or_distance_state_and_double_count_probe() -> None:
    assembly, _ = _author_one_way(
        propagation_actions=(_scalar_propagation(_ARM_LENGTH),),
    )
    assembly.freeze()
    route = assembly._execution_facts().route_segments[0]  # noqa: SLF001
    forbidden = {
        "distance",
        "medium",
        "opr",
        "phase",
        "optical_path_reference",
        "tensor",
        "parameter",
        "checkpoint",
        "trainable",
    }
    assert forbidden.isdisjoint(field.name for field in fields(route))
    with pytest.raises((AttributeError, TypeError)):
        route.phase = 1.0  # type: ignore[attr-defined, misc]
    with pytest.raises((AttributeError, TypeError)):
        route.distance = _ARM_LENGTH  # type: ignore[attr-defined, misc]
    assert not any(
        isinstance(value, (torch.Tensor, torch.nn.Module))
        for value in (
            route.source_frame,
            route.destination_frame,
            route.basis_transport,
        )
    )

    source_frame = _route_geometry._terminal_frame_input(
        owner_name="cube",
        terminal="right",
        frame=_cube()._terminal_frame(CubeTerminal.RIGHT),  # noqa: SLF001
    )
    destination_frame = _route_geometry._terminal_frame_input(
        owner_name="mirror",
        terminal="front",
        frame=_mirror()._terminal_frame(MirrorTerminal.FRONT),  # noqa: SLF001
    )
    doubled = _route_geometry._validate_route(
        source=source_frame,
        destination=destination_frame,
        propagation_displacements=(_ARM_LENGTH, _ARM_LENGTH),
    )
    assert doubled.failure == "geometry_mismatched"
    for pure_value in (
        route,
        route.basis_transport,
        doubled,
    ):
        assert pure_value is not None
        assert not hasattr(pure_value, "__dict__")
        assert forbidden.isdisjoint(
            field.name.lower()
            for field in fields(pure_value)
        )


def test_thick_sample_probe_reads_one_external_displacement_only() -> None:
    thick_sample = _ThickSampleProbe(axial_distance=_ARM_LENGTH)
    assembly, _ = _author_one_way(
        propagation_actions=(thick_sample,),
    )

    assembly.freeze()

    route = assembly._execution_facts().route_segments[0]  # noqa: SLF001
    assert route.inline_component_names == ("propagation_0",)
    assert not hasattr(route, "internal_slices")


def test_two_positive_propagations_advance_out_and_back_opr_exactly_once() -> None:
    distance = 1.0e-8
    refractive_index = 1.4
    source = PlaneWave(
        spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
        polarization=Polarization.scalar(),
        medium=ConstantMedium(index=refractive_index),
        propagation_direction=PropagationDirection.forward(),
        relative_amplitude=1.0,
    )
    outbound = _scalar_propagation(distance)
    returned = _scalar_propagation(distance)

    field = source(_grid())
    at_mirror = outbound(field)
    result = returned(at_mirror)

    assert torch.equal(
        at_mirror.path_reference.lengths[0],
        torch.tensor(refractive_index * distance, dtype=torch.float64),
    )
    assert torch.equal(
        result.path_reference.lengths[0],
        torch.tensor(
            2.0 * refractive_index * distance,
            dtype=torch.float64,
        ),
    )


def test_negative_distance_remains_valid_on_an_ordinary_wave_path() -> None:
    distance = -1.0e-8
    propagation = _scalar_propagation(distance)

    result = propagation(_source()(_grid()))

    assert torch.equal(
        result.path_reference.lengths[0],
        torch.tensor(distance, dtype=torch.float64),
    )


def test_tolerance_uses_frozen_unit_roundoff_and_route_local_scale() -> None:
    tolerance = _route_geometry._length_tolerance(
        delta=(1.0e-3, 0.0, 0.0),
        propagation_displacements=(4.0e-4, 6.0e-4),
    )
    expected = 192.0 * 2.0**-53 * 1.0e-3

    assert tolerance == expected
    assert _route_geometry._DIRECTION_TOLERANCE == 128.0 * 2.0**-53


def test_route_derivation_does_not_create_an_extra_graph_or_runtime_state() -> None:
    production_names = {
        value
        for value in vars(_assembly_facts)
        if not value.startswith("__")
    }

    assert "EvidenceGraph" not in production_names
    assert "RouteGraph" not in production_names
    assert "ReferencePlane" not in production_names

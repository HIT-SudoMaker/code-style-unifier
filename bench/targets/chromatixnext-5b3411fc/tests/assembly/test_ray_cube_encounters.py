from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import pytest
import torch

from chromatix_next.errors import AssemblyError, OpticalValueError
from chromatix_next.optics import Assembly, SpatialGrid, Spectrum
import chromatix_next.optics._ray_directional as _ray_directional
from chromatix_next.optics.element.ideal_cube_beam_splitter import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
)
from chromatix_next.optics.ray_bundle import (
    RAY_STATUS_ACTIVE,
    RAY_STATUS_SURFACE_MISSED,
    RAY_STATUS_VIGNETTED,
    RayBundle,
)
from tests.qualification.cube_oracles import (
    OracleCoatingDiagonal,
    OracleRouteKind,
    OracleTerminal,
    coating_basis,
    coating_plane_normal,
    geometry_pair_kinds,
)

_TERMINALS = tuple(CubeTerminal)


class _ReplayRaySource(torch.nn.Module):
    position: torch.Tensor
    direction: torch.Tensor
    polarization_vector: torch.Tensor
    power: torch.Tensor
    refractive_index: torch.Tensor
    optical_path: torch.Tensor
    status: torch.Tensor

    def __init__(self, bundle: RayBundle) -> None:
        super().__init__()
        self.register_buffer("position", bundle.position)
        self.register_buffer("direction", bundle.direction)
        self.register_buffer(
            "polarization_vector",
            bundle.polarization_vector,
        )
        self.register_buffer("power", bundle.power)
        self.register_buffer("refractive_index", bundle.refractive_index)
        self.register_buffer("optical_path", bundle.optical_path)
        self.register_buffer("status", bundle.status)
        self.spectrum = bundle.spectrum

    @property
    def role(self) -> Literal["source"]:
        """
        返回测试 Source 的封闭角色

        Returns:
            source 角色字面量

        """
        return "source"

    def forward(self, grid: SpatialGrid) -> RayBundle:
        """
        返回测试持有的 RayBundle 状态

        Args:
            grid: Assembly Source 的必需作者锚，本 Ray 探针不消费采样值

        Returns:
            注册张量构造的 fixed-double RayBundle

        """
        del grid
        return RayBundle(
            position=self.position,
            direction=self.direction,
            polarization_vector=self.polarization_vector,
            power=self.power,
            refractive_index=self.refractive_index,
            optical_path=self.optical_path,
            status=self.status,
            spectrum=self.spectrum,
        )


def _grid() -> SpatialGrid:
    return SpatialGrid(
        sample_counts=(2, 3),
        sample_spacing=(7.0e-6, 11.0e-6),
        first_sample_position=(-3.5e-6, -11.0e-6),
    )


def _cube(
    diagonal: CubeCoatingDiagonal,
    *,
    mixing_angle: float | torch.Tensor | torch.nn.Parameter = 0.37,
    polarizing: bool = False,
) -> (
    IdealNonpolarizingCubeBeamSplitter
    | IdealPolarizingCubeBeamSplitter
):
    common = {
        "origin": (0.0, 0.0, 0.0),
        "route_right": (1.0, 0.0, 0.0),
        "route_top": (0.0, 1.0, 0.0),
        "coating_diagonal": diagonal,
    }
    if polarizing:
        return IdealPolarizingCubeBeamSplitter(**common)
    return IdealNonpolarizingCubeBeamSplitter(
        **common,
        mixing_angle=mixing_angle,
    )


def _terminal_outward(terminal: CubeTerminal) -> torch.Tensor:
    return {
        CubeTerminal.LEFT: torch.tensor(
            (-1.0, 0.0, 0.0),
            dtype=torch.float64,
        ),
        CubeTerminal.TOP: torch.tensor(
            (0.0, 1.0, 0.0),
            dtype=torch.float64,
        ),
        CubeTerminal.RIGHT: torch.tensor(
            (1.0, 0.0, 0.0),
            dtype=torch.float64,
        ),
        CubeTerminal.BOTTOM: torch.tensor(
            (0.0, -1.0, 0.0),
            dtype=torch.float64,
        ),
    }[terminal]


def _structural_outputs(
    diagonal: CubeCoatingDiagonal,
    incident: CubeTerminal,
) -> tuple[CubeTerminal, CubeTerminal]:
    pair_kinds = geometry_pair_kinds(
        OracleCoatingDiagonal(diagonal.value),
    )
    outputs = tuple(
        outgoing
        for outgoing in _TERMINALS
        if pair_kinds[
            OracleTerminal(incident.value),
            OracleTerminal(outgoing.value),
        ]
        is not OracleRouteKind.STRUCTURAL_ZERO
    )
    assert len(outputs) == 2
    return outputs  # type: ignore[return-value]


def _route_output(
    diagonal: CubeCoatingDiagonal,
    incident: CubeTerminal,
    kind: OracleRouteKind,
) -> CubeTerminal:
    pair_kinds = geometry_pair_kinds(
        OracleCoatingDiagonal(diagonal.value),
    )
    return next(
        outgoing
        for outgoing in _TERMINALS
        if pair_kinds[
            OracleTerminal(incident.value),
            OracleTerminal(outgoing.value),
        ]
        is kind
    )


def _central_bundle(
    incident: CubeTerminal,
    *,
    polarization: torch.Tensor | None = None,
    power: torch.Tensor | None = None,
) -> RayBundle:
    outward = _terminal_outward(incident)
    direction = -outward
    resolved_polarization = (
        torch.tensor((0.0, 0.0, 1.0), dtype=torch.complex128)
        if polarization is None
        else polarization
    )
    resolved_power = (
        torch.tensor([[2.0]], dtype=torch.float64)
        if power is None
        else power
    )
    return RayBundle(
        position=outward.reshape(1, 1, 3) * 2.0e-3,
        direction=direction.reshape(1, 1, 3),
        polarization_vector=resolved_polarization.reshape(1, 1, 3),
        power=resolved_power,
        refractive_index=torch.tensor([[1.23]], dtype=torch.float64),
        optical_path=torch.tensor([[4.5e-3]], dtype=torch.float64),
        status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
        spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
    )


def _run_cube(
    *,
    owner: (
        IdealNonpolarizingCubeBeamSplitter
        | IdealPolarizingCubeBeamSplitter
    ),
    incident: CubeTerminal,
    bundle: RayBundle,
) -> tuple[Assembly, Mapping[str, RayBundle]]:
    source = _ReplayRaySource(bundle)
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include_directional(owner, name="cube")
    encounter = assembly.ray_encounter(
        owner,
        name="cube_use",
        incident_terminal=incident,
    )
    assembly.connect(
        source,
        encounter,
        destination_terminal=incident,
    )
    for outgoing in _structural_outputs(owner.coating_diagonal, incident):
        assembly.expose(
            encounter,
            name=outgoing.value,
            source_terminal=outgoing,
        )
    assembly.freeze()
    return assembly, assembly._replay()  # type: ignore[return-value]  # noqa: SLF001


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
@pytest.mark.parametrize("incident", _TERMINALS)
@pytest.mark.parametrize("polarizing", (False, True))
def test_all_single_incidence_choices_share_closed_owner_topology(
    diagonal: CubeCoatingDiagonal,
    incident: CubeTerminal,
    polarizing: bool,
) -> None:
    owner = _cube(diagonal, polarizing=polarizing)
    bundle = _central_bundle(incident)

    assembly, outputs = _run_cube(
        owner=owner,
        incident=incident,
        bundle=bundle,
    )

    assert tuple(outputs) == tuple(
        terminal.value
        for terminal in _structural_outputs(diagonal, incident)
    )
    assert assembly._frozen_facts is not None  # noqa: SLF001
    owner_fact = assembly._frozen_facts.directional_owners[0]  # noqa: SLF001
    assert set(owner_fact.routes) == {
        (incoming.value, outgoing.value)
        for incoming in _TERMINALS
        for outgoing in _TERMINALS
        if geometry_pair_kinds(OracleCoatingDiagonal(diagonal.value))[
            OracleTerminal(incoming.value),
            OracleTerminal(outgoing.value),
        ]
        is not OracleRouteKind.STRUCTURAL_ZERO
    }
    for output in outputs.values():
        assert output.position.dtype is torch.float64
        assert output.direction.dtype is torch.float64
        assert output.polarization_vector.dtype is torch.complex128
        assert output.power.dtype is torch.float64
        assert output.position.device.type == "cpu"


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
@pytest.mark.parametrize("incident", _TERMINALS)
def test_nbs_uses_cosine_squared_sine_squared_and_householder_transport(
    diagonal: CubeCoatingDiagonal,
    incident: CubeTerminal,
) -> None:
    angle = 0.37
    bundle = _central_bundle(incident)
    _assembly, outputs = _run_cube(
        owner=_cube(diagonal, mixing_angle=angle),
        incident=incident,
        bundle=bundle,
    )
    transmitted = _route_output(
        diagonal,
        incident,
        OracleRouteKind.TRANSMISSION,
    )
    reflected = _route_output(
        diagonal,
        incident,
        OracleRouteKind.REFLECTION,
    )
    transmitted_bundle = outputs[transmitted.value]
    reflected_bundle = outputs[reflected.value]
    expected_transmitted_power = bundle.power * torch.cos(
        torch.tensor(angle, dtype=torch.float64)
    ).square()
    expected_reflected_power = bundle.power * torch.sin(
        torch.tensor(angle, dtype=torch.float64)
    ).square()
    torch.testing.assert_close(
        transmitted_bundle.power,
        expected_transmitted_power,
        atol=2.0e-15,
        rtol=0.0,
    )
    torch.testing.assert_close(
        reflected_bundle.power,
        expected_reflected_power,
        atol=2.0e-15,
        rtol=0.0,
    )
    assert torch.equal(transmitted_bundle.direction, bundle.direction)
    assert torch.equal(
        transmitted_bundle.polarization_vector,
        bundle.polarization_vector,
    )
    expected_reflected_direction = _terminal_outward(reflected).reshape(
        1,
        1,
        3,
    )
    torch.testing.assert_close(
        reflected_bundle.direction,
        expected_reflected_direction,
        atol=5.0e-15,
        rtol=0.0,
    )
    coating_normal = coating_plane_normal(
        OracleCoatingDiagonal(diagonal.value),
    )
    expected_reflected_polarization = (
        bundle.polarization_vector
        - 2.0
        * (
            bundle.polarization_vector * coating_normal
        ).sum(dim=-1, keepdim=True)
        * coating_normal
    )
    torch.testing.assert_close(
        reflected_bundle.polarization_vector,
        expected_reflected_polarization,
        atol=2.0e-15,
        rtol=0.0,
    )
    assert torch.equal(
        transmitted_bundle.position,
        torch.zeros_like(bundle.position),
    )
    assert torch.equal(
        reflected_bundle.position,
        transmitted_bundle.position,
    )
    assert torch.equal(transmitted_bundle.status, bundle.status)
    assert torch.equal(reflected_bundle.status, bundle.status)
    expected_optical_path = bundle.optical_path + (
        bundle.refractive_index * 2.0e-3
    )
    assert torch.equal(
        transmitted_bundle.optical_path,
        expected_optical_path,
    )
    assert torch.equal(
        reflected_bundle.optical_path,
        expected_optical_path,
    )
    torch.testing.assert_close(
        transmitted_bundle.power + reflected_bundle.power,
        bundle.power,
        atol=2.0e-15,
        rtol=0.0,
    )


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
@pytest.mark.parametrize("incident", _TERMINALS)
def test_pbs_uses_exact_p_s_projected_power_and_normalized_vectors(
    diagonal: CubeCoatingDiagonal,
    incident: CubeTerminal,
) -> None:
    direction = -_terminal_outward(incident)
    s_axis, p_axis = coating_basis(
        direction,
        coating_plane_normal(OracleCoatingDiagonal(diagonal.value)),
    )
    polarization = (
        p_axis.to(torch.complex128)
        + 1j * s_axis.to(torch.complex128)
    ) / torch.sqrt(torch.tensor(2.0, dtype=torch.float64))
    bundle = _central_bundle(incident, polarization=polarization)

    _assembly, outputs = _run_cube(
        owner=_cube(diagonal, polarizing=True),
        incident=incident,
        bundle=bundle,
    )

    transmitted = _route_output(
        diagonal,
        incident,
        OracleRouteKind.TRANSMISSION,
    )
    reflected = _route_output(
        diagonal,
        incident,
        OracleRouteKind.REFLECTION,
    )
    transmitted_bundle = outputs[transmitted.value]
    reflected_bundle = outputs[reflected.value]
    torch.testing.assert_close(
        transmitted_bundle.power,
        bundle.power * 0.5,
        atol=2.0e-15,
        rtol=0.0,
    )
    torch.testing.assert_close(
        reflected_bundle.power,
        bundle.power * 0.5,
        atol=2.0e-15,
        rtol=0.0,
    )
    expected_transmitted = p_axis.to(torch.complex128).reshape(1, 1, 3)
    torch.testing.assert_close(
        transmitted_bundle.polarization_vector,
        expected_transmitted,
        atol=2.0e-15,
        rtol=0.0,
    )
    reflected_incident = (
        1j * s_axis.to(torch.complex128)
    ).reshape(1, 1, 3)
    normal = coating_plane_normal(
        OracleCoatingDiagonal(diagonal.value),
    )
    expected_reflected = reflected_incident - 2.0 * (
        reflected_incident * normal
    ).sum(dim=-1, keepdim=True) * normal
    torch.testing.assert_close(
        reflected_bundle.polarization_vector,
        expected_reflected,
        atol=2.0e-15,
        rtol=0.0,
    )
    for output in (transmitted_bundle, reflected_bundle):
        polarization_norm = (
            output.polarization_vector.real.square().sum(dim=-1)
            + output.polarization_vector.imag.square().sum(dim=-1)
        )
        torch.testing.assert_close(
            polarization_norm,
            torch.ones_like(polarization_norm),
            atol=2.0e-15,
            rtol=0.0,
        )
        torch.testing.assert_close(
            (
                output.polarization_vector * output.direction
            ).sum(dim=-1),
            torch.zeros_like(output.power, dtype=torch.complex128),
            atol=2.0e-15,
            rtol=0.0,
        )


@pytest.mark.parametrize(
    ("projection_kind", "zero_route_kind"),
    (
        ("p", OracleRouteKind.REFLECTION),
        ("s", OracleRouteKind.TRANSMISSION),
    ),
)
def test_pbs_zero_projection_uses_deterministic_unit_basis(
    projection_kind: str,
    zero_route_kind: OracleRouteKind,
) -> None:
    diagonal = CubeCoatingDiagonal.RISING
    incident = CubeTerminal.LEFT
    direction = -_terminal_outward(incident)
    s_axis, p_axis = coating_basis(
        direction,
        coating_plane_normal(OracleCoatingDiagonal.RISING),
    )
    polarization = p_axis if projection_kind == "p" else s_axis
    bundle = _central_bundle(
        incident,
        polarization=polarization.to(torch.complex128),
    )
    _assembly, outputs = _run_cube(
        owner=_cube(diagonal, polarizing=True),
        incident=incident,
        bundle=bundle,
    )
    zero_terminal = _route_output(
        diagonal,
        incident,
        zero_route_kind,
    )
    zero_output = outputs[zero_terminal.value]
    assert torch.equal(zero_output.power, torch.zeros_like(bundle.power))
    assert bool(torch.isfinite(zero_output.polarization_vector).all())
    norm = (
        zero_output.polarization_vector.real.square().sum(dim=-1)
        + zero_output.polarization_vector.imag.square().sum(dim=-1)
    )
    torch.testing.assert_close(
        norm,
        torch.ones_like(norm),
        atol=2.0e-15,
        rtol=0.0,
    )


def test_missed_and_existing_inactive_history_is_carried_exactly_once() -> None:
    diagonal = CubeCoatingDiagonal.RISING
    incident = CubeTerminal.LEFT
    positions = torch.tensor(
        (
            ((-2.0e-3, 0.0, 0.0),),
            ((-2.0e-3, 1.0e-4, 0.0),),
            ((-3.0e-3, 2.0e-4, 0.0),),
            ((-4.0e-3, 3.0e-4, 0.0),),
        ),
        dtype=torch.float64,
    ).movedim(0, 1)
    directions = torch.tensor(
        (
            ((1.0, 0.0, 0.0),),
            ((0.0, 0.0, 1.0),),
            ((-1.0, 0.0, 0.0),),
            ((1.0, 0.0, 0.0),),
        ),
        dtype=torch.float64,
    ).movedim(0, 1)
    polarizations = torch.tensor(
        (
            ((0.0, 0.0, 1.0),),
            ((1.0, 0.0, 0.0),),
            ((0.0, 0.0, 1.0),),
            ((0.0, 0.0, 1.0),),
        ),
        dtype=torch.complex128,
    ).movedim(0, 1)
    power = torch.tensor([[2.0, 3.0, 5.0, 7.0]], dtype=torch.float64)
    status = torch.tensor(
        [[
            RAY_STATUS_ACTIVE,
            RAY_STATUS_ACTIVE,
            RAY_STATUS_ACTIVE,
            RAY_STATUS_VIGNETTED,
        ]],
        dtype=torch.uint8,
    )
    bundle = RayBundle(
        position=positions,
        direction=directions,
        polarization_vector=polarizations,
        power=power,
        refractive_index=torch.full_like(power, 1.4),
        optical_path=torch.tensor(
            [[1.0e-3, 2.0e-3, 3.0e-3, 4.0e-3]],
            dtype=torch.float64,
        ),
        status=status,
        spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
    )
    _assembly, outputs = _run_cube(
        owner=_cube(diagonal, mixing_angle=0.31),
        incident=incident,
        bundle=bundle,
    )
    transmitted = outputs[
        _route_output(
            diagonal,
            incident,
            OracleRouteKind.TRANSMISSION,
        ).value
    ]
    reflected = outputs[
        _route_output(
            diagonal,
            incident,
            OracleRouteKind.REFLECTION,
        ).value
    ]
    assert torch.equal(
        transmitted.status,
        torch.tensor(
            [[
                RAY_STATUS_ACTIVE,
                RAY_STATUS_SURFACE_MISSED,
                RAY_STATUS_SURFACE_MISSED,
                RAY_STATUS_VIGNETTED,
            ]],
            dtype=torch.uint8,
        ),
    )
    assert torch.equal(reflected.status, transmitted.status)
    assert torch.equal(transmitted.power[0, 1:], power[0, 1:])
    assert torch.equal(
        reflected.power[0, 1:],
        torch.zeros_like(power[0, 1:]),
    )
    for output in (transmitted, reflected):
        assert torch.equal(output.position[0, 1:], positions[0, 1:])
        assert torch.equal(output.direction[0, 1:], directions[0, 1:])
        assert torch.equal(
            output.polarization_vector[0, 1:],
            polarizations[0, 1:],
        )
        assert torch.equal(
            output.refractive_index[0, 1:],
            bundle.refractive_index[0, 1:],
        )
        assert torch.equal(
            output.optical_path[0, 1:],
            bundle.optical_path[0, 1:],
        )
        assert torch.equal(
            output.optical_path[0, :1],
            bundle.optical_path[0, :1]
            + bundle.refractive_index[0, :1] * 2.0e-3,
        )
    torch.testing.assert_close(
        transmitted.power + reflected.power,
        power,
        atol=2.0e-15,
        rtol=0.0,
    )


def test_outgoing_half_space_inconsistency_rejects_before_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def inconsistent_reflection(
        *,
        ray_direction: torch.Tensor,
        unit_normal: torch.Tensor,
        is_interacted: torch.Tensor,
    ) -> torch.Tensor:
        del unit_normal, is_interacted
        return -ray_direction

    monkeypatch.setattr(
        _ray_directional,
        "reflect_direction",
        inconsistent_reflection,
    )
    with pytest.raises(OpticalValueError) as rejected:
        _run_cube(
            owner=_cube(CubeCoatingDiagonal.RISING),
            incident=CubeTerminal.LEFT,
            bundle=_central_bundle(CubeTerminal.LEFT),
        )
    assert rejected.value.identity == "ray_cube_outgoing_terminal_inconsistent"


def test_ray_encounter_rejects_multiple_incidence_before_replay() -> None:
    owner = _cube(CubeCoatingDiagonal.RISING)
    assembly = Assembly()
    assembly.include_directional(owner, name="cube")
    with pytest.raises(AssemblyError) as rejected:
        assembly.ray_encounter(
            owner,
            name="cube_use",
            incident_terminal=(CubeTerminal.LEFT, CubeTerminal.TOP),
        )
    assert rejected.value.identity.startswith(
        "assembly_encounter_ray_multiple_incident:"
    )


def test_continuous_geometry_power_and_polarization_gradients_are_nonzero() -> None:
    incident = CubeTerminal.LEFT
    raw_direction = torch.tensor(
        [[[1.0, 0.12, 0.05]]],
        dtype=torch.float64,
        requires_grad=True,
    )
    direction = raw_direction / torch.linalg.vector_norm(
        raw_direction,
        dim=-1,
        keepdim=True,
    )
    raw_polarization = torch.tensor(
        [[[0.2 + 0.3j, 0.7 - 0.1j, 0.4 + 0.2j]]],
        dtype=torch.complex128,
        requires_grad=True,
    )
    longitudinal = (
        raw_polarization * direction
    ).sum(dim=-1, keepdim=True)
    transverse = raw_polarization - longitudinal * direction
    polarization = transverse / torch.linalg.vector_norm(
        transverse,
        dim=-1,
        keepdim=True,
    )
    position = torch.tensor(
        [[[-2.0e-3, 0.3e-3, -0.2e-3]]],
        dtype=torch.float64,
        requires_grad=True,
    )
    power = torch.tensor([[2.0]], dtype=torch.float64, requires_grad=True)
    bundle = RayBundle(
        position=position,
        direction=direction,
        polarization_vector=polarization,
        power=power,
        refractive_index=torch.ones((1, 1), dtype=torch.float64),
        optical_path=torch.zeros((1, 1), dtype=torch.float64),
        status=torch.full((1, 1), RAY_STATUS_ACTIVE, dtype=torch.uint8),
        spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
    )
    angle = torch.nn.Parameter(torch.tensor(0.31, dtype=torch.float64))
    _assembly, outputs = _run_cube(
        owner=_cube(
            CubeCoatingDiagonal.RISING,
            mixing_angle=angle,
        ),
        incident=incident,
        bundle=bundle,
    )
    loss = sum(
        output.position.square().sum()
        + output.direction.square().sum() * 0.3
        + output.polarization_vector.real.sum() * 0.2
        + output.power.sum() * index
        for index, output in enumerate(outputs.values(), start=1)
    )
    loss.backward()
    for gradient in (
        position.grad,
        raw_direction.grad,
        raw_polarization.grad,
        power.grad,
        angle.grad,
    ):
        assert gradient is not None
        assert bool(torch.isfinite(gradient).all())
        assert int(torch.count_nonzero(gradient)) > 0


def test_pbs_projection_gradient_is_nonzero_away_from_zero_projection() -> None:
    raw_polarization = torch.tensor(
        [[[0.0 + 0.0j, 0.6 + 0.2j, 0.5 - 0.3j]]],
        dtype=torch.complex128,
        requires_grad=True,
    )
    polarization = raw_polarization / torch.linalg.vector_norm(
        raw_polarization,
        dim=-1,
        keepdim=True,
    )
    bundle = _central_bundle(
        CubeTerminal.LEFT,
        polarization=polarization,
    )
    _assembly, outputs = _run_cube(
        owner=_cube(
            CubeCoatingDiagonal.RISING,
            polarizing=True,
        ),
        incident=CubeTerminal.LEFT,
        bundle=bundle,
    )
    ordered = tuple(outputs.values())
    loss = (
        0.7 * ordered[0].power.sum()
        + 1.3 * ordered[1].power.sum()
        + 0.2 * ordered[0].polarization_vector.real.sum()
        - 0.4 * ordered[1].polarization_vector.imag.sum()
    )

    loss.backward()

    assert raw_polarization.grad is not None
    assert bool(torch.isfinite(raw_polarization.grad).all())
    assert int(torch.count_nonzero(raw_polarization.grad)) > 0


@pytest.mark.parametrize("polarizing", (False, True))
def test_cpu_and_meta_use_the_same_private_replay_with_fixed_double_outputs(
    polarizing: bool,
) -> None:
    assembly, cpu_outputs = _run_cube(
        owner=_cube(
            CubeCoatingDiagonal.FALLING,
            polarizing=polarizing,
        ),
        incident=CubeTerminal.TOP,
        bundle=_central_bundle(CubeTerminal.TOP),
    )

    meta_outputs = assembly.to(device="meta")._replay()  # noqa: SLF001

    assert tuple(meta_outputs) == tuple(cpu_outputs)
    for name, cpu_output in cpu_outputs.items():
        meta_output = meta_outputs[name]
        assert isinstance(meta_output, RayBundle)
        for field_name in (
            "position",
            "direction",
            "polarization_vector",
            "power",
            "refractive_index",
            "optical_path",
            "status",
        ):
            cpu_value = getattr(cpu_output, field_name)
            meta_value = getattr(meta_output, field_name)
            assert meta_value.device.type == "meta"
            assert meta_value.shape == cpu_value.shape
            assert meta_value.dtype is cpu_value.dtype
        assert meta_output.position.dtype is torch.float64
        assert meta_output.direction.dtype is torch.float64
        assert meta_output.polarization_vector.dtype is torch.complex128
        assert meta_output.power.dtype is torch.float64
        assert meta_output.optical_path.dtype is torch.float64
        assert meta_output.status.dtype is torch.uint8


def test_private_ray_adapter_contains_no_wave_phase_or_second_state_owner() -> None:
    source = Path(_ray_directional.__file__).read_text(encoding="utf-8")
    assert "1j" not in source
    assert "OpticalField" not in source
    assert "SourceLineage" not in source
    assert "coherent" not in source.lower()
    assert "torch.nn.Module" not in source
    assert "response_matrix" not in source
    assert "scattering" not in source.lower()

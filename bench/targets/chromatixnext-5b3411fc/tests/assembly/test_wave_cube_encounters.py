from __future__ import annotations

from collections.abc import Mapping
from itertools import combinations
from typing import Literal

import pytest
import torch

import chromatix_next._numerics.cube_response as _cube_response
from chromatix_next.errors import AssemblyError, OpticalRuntimeError
from chromatix_next.optics import Assembly, SpatialGrid, Spectrum, Vacuum
from chromatix_next.optics.element.ideal_cube_beam_splitter import (
    CubeCoatingDiagonal,
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
)
from chromatix_next.optics.field import (
    FieldNormalization,
    OpticalField,
    OpticalPathReference,
    _own_field_value,
    _SourceLineage,
)
from chromatix_next.optics.polarization import PolarizationRepresentation
from tests.qualification.cube_oracles import (
    OracleCoatingDiagonal,
    OracleRouteKind,
    OracleTerminal,
    coating_basis,
    coating_plane_normal,
    dense_all_real_balanced_adversary,
    dense_nbs_operator,
    dense_pbs_operator,
    geometry_pair_kinds,
)

_TERMINALS = tuple(CubeTerminal)
_HEIGHT = 3
_WIDTH = 5


class _ReplayFieldSource(torch.nn.Module):
    # 以测试给定包络和共享 lineage 产生合法 transverse OpticalField

    envelope: torch.Tensor

    def __init__(
        self,
        *,
        envelope: torch.Tensor,
        lineage: _SourceLineage,
        path_length: float = 0.0,
        normalization: FieldNormalization = FieldNormalization.RELATIVE,
        corruption: str | None = None,
    ) -> None:
        super().__init__()
        self.register_buffer("envelope", envelope)
        self._lineage = lineage
        self._path_length = path_length
        self._normalization = normalization
        self._corruption = corruption

    @property
    def role(self) -> Literal["source"]:
        """
        返回测试 Source 的封闭角色

        Returns:
            source 角色字面量

        """
        return "source"

    def forward(self, grid: SpatialGrid) -> OpticalField:
        """
        在作者网格上返回一束测试 transverse 光场

        Args:
            grid: Assembly 为本 Source 注册的采样锚

        Returns:
            保留共享 lineage 的 OpticalField

        """
        field = OpticalField(
            envelope=self.envelope,
            grid=grid,
            spectrum=Spectrum.monochromatic(wavelength=632.8e-9),
            polarization_representation=(
                PolarizationRepresentation.TRANSVERSE
            ),
            medium=Vacuum(),
            normalization=self._normalization,
            path_reference=OpticalPathReference(
                lengths=(self._path_length,),
            ),
        )
        _own_field_value(field, self._lineage)
        if self._corruption == "complex64":
            object.__setattr__(
                field,
                "envelope",
                field.envelope.to(torch.complex64),
            )
        elif self._corruption == "nonfinite":
            corrupted = field.envelope.clone()
            corrupted[..., 0, 0] = complex(float("nan"), 0.0)
            object.__setattr__(field, "envelope", corrupted)
        return field


class _RoutePropagationProbe(torch.nn.Module):
    # 仅为本票隔离 Route 基传输而保留包络的 Propagation 探针

    axial_distance: torch.Tensor

    def __init__(self, *, axial_distance: float) -> None:
        super().__init__()
        self.register_buffer(
            "axial_distance",
            torch.tensor(axial_distance, dtype=torch.float64),
        )

    @property
    def role(self) -> Literal["propagation"]:
        """
        返回测试 Propagation 的封闭角色

        Returns:
            propagation 角色字面量

        """
        return "propagation"

    def forward(self, field: OpticalField) -> OpticalField:
        """
        保持输入光场以隔离并观测 Route 采样/Jones 变换

        Args:
            field: 进入 Route 探针的 OpticalField

        Returns:
            未改写的同一 OpticalField

        """
        return field


def _grid(
    *,
    sample_counts: tuple[int, int] = (_HEIGHT, _WIDTH),
) -> SpatialGrid:
    return SpatialGrid(
        sample_counts=sample_counts,
        sample_spacing=(7.0e-6, 11.0e-6),
        first_sample_position=(-13.0e-6, 19.0e-6),
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


def _source(
    envelope: torch.Tensor,
    *,
    lineage: _SourceLineage,
    path_length: float = 0.0,
    normalization: FieldNormalization = FieldNormalization.RELATIVE,
    corruption: str | None = None,
) -> _ReplayFieldSource:
    return _ReplayFieldSource(
        envelope=envelope,
        lineage=lineage,
        path_length=path_length,
        normalization=normalization,
        corruption=corruption,
    )


def _constant_envelope(
    horizontal: complex = 1.0 + 0.0j,
    vertical: complex = 0.0 + 0.0j,
    *,
    sample_counts: tuple[int, int] = (_HEIGHT, _WIDTH),
    requires_grad: bool = False,
) -> torch.Tensor:
    values = torch.empty(
        (1, 2, *sample_counts),
        dtype=torch.complex128,
    )
    values[:, 0].fill_(horizontal)
    values[:, 1].fill_(vertical)
    return values.requires_grad_(requires_grad)


def _structural_outputs(
    diagonal: CubeCoatingDiagonal,
    incidents: tuple[CubeTerminal, ...],
) -> tuple[CubeTerminal, ...]:
    pair_kinds = geometry_pair_kinds(
        OracleCoatingDiagonal(diagonal.value),
    )
    return tuple(
        outgoing
        for outgoing in _TERMINALS
        if any(
            pair_kinds[
                OracleTerminal(incident.value),
                OracleTerminal(outgoing.value),
            ]
            is not OracleRouteKind.STRUCTURAL_ZERO
            for incident in incidents
        )
    )


def _run_cube(
    *,
    owner: (
        IdealNonpolarizingCubeBeamSplitter
        | IdealPolarizingCubeBeamSplitter
    ),
    incident_sources: Mapping[CubeTerminal, _ReplayFieldSource],
    source_grids: Mapping[CubeTerminal, SpatialGrid] | None = None,
    encounter_name: str = "cube_use",
) -> tuple[Assembly, Mapping[str, OpticalField]]:
    assembly = Assembly()
    for terminal in _TERMINALS:
        if terminal not in incident_sources:
            continue
        source = incident_sources[terminal]
        assembly.include(
            source,
            name=f"source_{terminal.value}",
            grid=(
                _grid()
                if source_grids is None
                else source_grids[terminal]
            ),
        )
    assembly.include_directional(owner, name="cube")
    encounter = assembly.wave_encounter(
        owner,
        name=encounter_name,
        incident_terminals=tuple(incident_sources),
    )
    for terminal in _TERMINALS:
        if terminal not in incident_sources:
            continue
        assembly.connect(
            incident_sources[terminal],
            encounter,
            destination_terminal=terminal,
        )
    for outgoing in _structural_outputs(
        owner.coating_diagonal,
        tuple(incident_sources),
    ):
        assembly.expose(
            encounter,
            name=outgoing.value,
            source_terminal=outgoing,
        )
    assembly.freeze()
    outputs = assembly._replay()  # noqa: SLF001
    return assembly, outputs  # type: ignore[return-value]


def _all_nonempty_masks() -> tuple[tuple[CubeTerminal, ...], ...]:
    return tuple(
        mask
        for size in range(1, len(_TERMINALS) + 1)
        for mask in combinations(_TERMINALS, size)
    )


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
@pytest.mark.parametrize("polarizing", (False, True))
@pytest.mark.parametrize("incident_mask", _all_nonempty_masks())
def test_all_fifteen_wave_masks_replay_only_structural_outputs(
    diagonal: CubeCoatingDiagonal,
    polarizing: bool,
    incident_mask: tuple[CubeTerminal, ...],
) -> None:
    lineage = _SourceLineage()
    sources = {
        terminal: _source(
            _constant_envelope(),
            lineage=lineage,
        )
        for terminal in incident_mask
    }

    _assembly, outputs = _run_cube(
        owner=_cube(
            diagonal,
            polarizing=polarizing,
        ),
        incident_sources=sources,
    )

    assert tuple(outputs) == tuple(
        terminal.value
        for terminal in _structural_outputs(diagonal, incident_mask)
    )
    assert all(
        output.envelope.dtype is torch.complex128
        and bool(torch.isfinite(output.envelope).all())
        for output in outputs.values()
    )


def _frame_axes(
    terminal: CubeTerminal,
    *,
    direction: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    route_right = torch.tensor((1.0, 0.0, 0.0), dtype=torch.float64)
    route_top = torch.tensor((0.0, 1.0, 0.0), dtype=torch.float64)
    vertical = torch.linalg.cross(route_right, route_top)
    outward = {
        CubeTerminal.LEFT: -route_right,
        CubeTerminal.TOP: route_top,
        CubeTerminal.RIGHT: route_right,
        CubeTerminal.BOTTOM: -route_top,
    }[terminal]
    travel = -outward if direction == "incident" else outward
    horizontal = torch.linalg.cross(vertical, travel)
    return travel, horizontal, vertical


def _local_hv_to_ps(
    envelope: torch.Tensor,
    *,
    terminal: CubeTerminal,
    diagonal: CubeCoatingDiagonal,
    direction: str,
) -> torch.Tensor:
    travel, horizontal, vertical = _frame_axes(
        terminal,
        direction=direction,
    )
    s_axis, p_axis = coating_basis(
        travel,
        coating_plane_normal(OracleCoatingDiagonal(diagonal.value)),
    )
    p_value = (
        torch.dot(p_axis, horizontal) * envelope[..., 0, :, :]
        + torch.dot(p_axis, vertical) * envelope[..., 1, :, :]
    )
    s_value = (
        torch.dot(s_axis, horizontal) * envelope[..., 0, :, :]
        + torch.dot(s_axis, vertical) * envelope[..., 1, :, :]
    )
    return torch.stack((p_value, s_value), dim=-3)


def _ps_to_local_hv(
    envelope: torch.Tensor,
    *,
    terminal: CubeTerminal,
    diagonal: CubeCoatingDiagonal,
    direction: str,
) -> torch.Tensor:
    travel, horizontal, vertical = _frame_axes(
        terminal,
        direction=direction,
    )
    s_axis, p_axis = coating_basis(
        travel,
        coating_plane_normal(OracleCoatingDiagonal(diagonal.value)),
    )
    horizontal_value = (
        torch.dot(horizontal, p_axis) * envelope[..., 0, :, :]
        + torch.dot(horizontal, s_axis) * envelope[..., 1, :, :]
    )
    vertical_value = (
        torch.dot(vertical, p_axis) * envelope[..., 0, :, :]
        + torch.dot(vertical, s_axis) * envelope[..., 1, :, :]
    )
    return torch.stack((horizontal_value, vertical_value), dim=-3)


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
@pytest.mark.parametrize("polarizing", (False, True))
def test_random_complex_replay_matches_independent_dense_operator(
    diagonal: CubeCoatingDiagonal,
    polarizing: bool,
) -> None:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(20260824)
    lineage = _SourceLineage()
    local_inputs = {
        terminal: torch.complex(
            torch.randn(
                (1, 2, _HEIGHT, _WIDTH),
                generator=generator,
                dtype=torch.float64,
            ),
            torch.randn(
                (1, 2, _HEIGHT, _WIDTH),
                generator=generator,
                dtype=torch.float64,
            ),
        )
        for terminal in _TERMINALS
    }
    owner = _cube(
        diagonal,
        mixing_angle=0.37,
        polarizing=polarizing,
    )

    _assembly, outputs = _run_cube(
        owner=owner,
        incident_sources={
            terminal: _source(envelope, lineage=lineage)
            for terminal, envelope in local_inputs.items()
        },
    )

    canonical_inputs = torch.stack(
        tuple(
            _local_hv_to_ps(
                local_inputs[terminal],
                terminal=terminal,
                diagonal=diagonal,
                direction="incident",
            ).movedim(-3, -1)
            for terminal in _TERMINALS
        ),
        dim=-2,
    )
    flattened_inputs = canonical_inputs.reshape(
        1,
        _HEIGHT,
        _WIDTH,
        8,
    )
    operator = (
        dense_pbs_operator(OracleCoatingDiagonal(diagonal.value))
        if polarizing
        else dense_nbs_operator(
            OracleCoatingDiagonal(diagonal.value),
            0.37,
        )
    )
    expected = torch.einsum(
        "ij,bhwj->bhwi",
        operator,
        flattened_inputs,
    ).reshape(1, _HEIGHT, _WIDTH, 4, 2)
    for index, terminal in enumerate(_TERMINALS):
        actual = _local_hv_to_ps(
            outputs[terminal.value].envelope,
            terminal=terminal,
            diagonal=diagonal,
            direction="outgoing",
        ).movedim(-3, -1)
        torch.testing.assert_close(
            actual,
            expected[..., index, :],
            atol=5.0e-13,
            rtol=0.0,
        )


@pytest.mark.parametrize("diagonal", tuple(CubeCoatingDiagonal))
def test_full_replay_preserves_energy_and_rejects_bad_real_cube_oracle(
    diagonal: CubeCoatingDiagonal,
) -> None:
    incidents = (
        (CubeTerminal.TOP, CubeTerminal.RIGHT)
        if diagonal is CubeCoatingDiagonal.RISING
        else (CubeTerminal.LEFT, CubeTerminal.TOP)
    )
    lineage = _SourceLineage()
    canonical_inputs = {
        terminal: torch.tensor(
            [[[[1.0]], [[0.0]]]],
            dtype=torch.complex128,
        )
        for terminal in incidents
    }
    local_inputs = {
        terminal: _ps_to_local_hv(
            canonical_inputs[terminal],
            terminal=terminal,
            diagonal=diagonal,
            direction="incident",
        ).expand(1, 2, _HEIGHT, _WIDTH).clone()
        for terminal in incidents
    }

    _assembly, outputs = _run_cube(
        owner=_cube(diagonal, mixing_angle=torch.pi / 4.0),
        incident_sources={
            terminal: _source(envelope, lineage=lineage)
            for terminal, envelope in local_inputs.items()
        },
    )

    input_power = sum(
        field.abs().square().sum()
        for field in local_inputs.values()
    )
    output_power = sum(
        field.envelope.abs().square().sum()
        for field in outputs.values()
    )
    torch.testing.assert_close(
        output_power,
        input_power,
        atol=5.0e-13,
        rtol=0.0,
    )
    canonical_vector = torch.zeros(8, dtype=torch.complex128)
    for terminal in incidents:
        canonical_vector[2 * _TERMINALS.index(terminal)] = 1.0
    adversarial = dense_all_real_balanced_adversary(
        OracleCoatingDiagonal(diagonal.value),
    ) @ canonical_vector
    assert float(adversarial.abs().square().sum()) == pytest.approx(4.0)


def test_replay_rejects_missing_reflection_quadrature_counterfactual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_quadrature_response(
        *,
        incident_terminal_p_s_values: torch.Tensor,
        mixing_angle: torch.Tensor,
        reflection_input_indices: tuple[int, int, int, int],
    ) -> torch.Tensor:
        transmission_indices = torch.tensor(
            (2, 3, 0, 1),
            dtype=torch.int64,
            device=incident_terminal_p_s_values.device,
        )
        reflection_indices = torch.tensor(
            reflection_input_indices,
            dtype=torch.int64,
            device=incident_terminal_p_s_values.device,
        )
        transmitted = torch.index_select(
            incident_terminal_p_s_values,
            dim=-2,
            index=transmission_indices,
        )
        reflected = torch.index_select(
            incident_terminal_p_s_values,
            dim=-2,
            index=reflection_indices,
        )
        return torch.cos(mixing_angle) * transmitted + (
            torch.sin(mixing_angle) * reflected
        )

    monkeypatch.setattr(
        _cube_response,
        "apply_closed_nonpolarizing_cube_response",
        missing_quadrature_response,
    )
    lineage = _SourceLineage()
    with pytest.raises(OpticalRuntimeError) as rejected:
        _run_cube(
            owner=_cube(
                CubeCoatingDiagonal.RISING,
                mixing_angle=torch.pi / 4.0,
            ),
            incident_sources={
                CubeTerminal.TOP: _source(
                    _constant_envelope(),
                    lineage=lineage,
                ),
                CubeTerminal.RIGHT: _source(
                    _constant_envelope(),
                    lineage=lineage,
                ),
            },
        )
    assert (
        rejected.value.identity
        == "cube_beam_splitter_response_invariant_violated"
    )


def test_exact_cancellation_output_exists_and_opr_reference_is_deterministic() -> None:
    diagonal = CubeCoatingDiagonal.RISING
    lineage = _SourceLineage()
    cancellation_owner = _cube(
        diagonal,
        mixing_angle=torch.pi / 4.0,
    )
    assert isinstance(
        cancellation_owner,
        IdealNonpolarizingCubeBeamSplitter,
    )
    live_cosine = torch.cos(cancellation_owner.mixing_angle).detach()
    live_sine = torch.sin(cancellation_owner.mixing_angle).detach()
    top_ps = torch.tensor(
        [[[[1.0j * live_cosine]], [[0.0]]]],
        dtype=torch.complex128,
    ).expand(1, 2, _HEIGHT, _WIDTH).clone()
    right_ps = torch.tensor(
        [[[[live_sine]], [[0.0]]]],
        dtype=torch.complex128,
    ).expand(1, 2, _HEIGHT, _WIDTH).clone()
    top = _ps_to_local_hv(
        top_ps,
        terminal=CubeTerminal.TOP,
        diagonal=diagonal,
        direction="incident",
    )
    right = _ps_to_local_hv(
        right_ps,
        terminal=CubeTerminal.RIGHT,
        diagonal=diagonal,
        direction="incident",
    )
    _assembly, outputs = _run_cube(
        owner=cancellation_owner,
        incident_sources={
            CubeTerminal.TOP: _source(top, lineage=lineage),
            CubeTerminal.RIGHT: _source(right, lineage=lineage),
        },
    )

    assert "left" in outputs
    assert torch.equal(
        outputs["left"].envelope,
        torch.zeros_like(outputs["left"].envelope),
    )

    wavelength = 632.8e-9
    top_rephased = _ps_to_local_hv(
        right_ps,
        terminal=CubeTerminal.TOP,
        diagonal=diagonal,
        direction="incident",
    )
    _assembly, rephased = _run_cube(
        owner=_cube(diagonal, mixing_angle=torch.pi / 4.0),
        incident_sources={
            CubeTerminal.TOP: _source(
                top_rephased,
                lineage=lineage,
                path_length=wavelength / 4.0,
            ),
            CubeTerminal.RIGHT: _source(
                right,
                lineage=lineage,
            ),
        },
    )
    assert rephased["left"].path_reference.lengths == (
        wavelength / 4.0,
    )
    assert float(rephased["left"].envelope.abs().amax()) < 5.0e-15


def test_contributor_compatibility_is_output_local_after_basis_transform() -> None:
    lineage = _SourceLineage()
    relative = _source(
        _constant_envelope(),
        lineage=lineage,
        normalization=FieldNormalization.RELATIVE,
    )
    power = _source(
        _constant_envelope(),
        lineage=lineage,
        normalization=FieldNormalization.POWER,
    )
    _assembly, separated_outputs = _run_cube(
        owner=_cube(CubeCoatingDiagonal.RISING),
        incident_sources={
            CubeTerminal.LEFT: relative,
            CubeTerminal.TOP: power,
        },
    )
    assert tuple(separated_outputs) == ("left", "top", "right", "bottom")

    with pytest.raises(AssemblyError) as rejected:
        _run_cube(
            owner=_cube(CubeCoatingDiagonal.RISING),
            incident_sources={
                CubeTerminal.LEFT: _source(
                    _constant_envelope(),
                    lineage=lineage,
                    normalization=FieldNormalization.RELATIVE,
                ),
                CubeTerminal.BOTTOM: _source(
                    _constant_envelope(),
                    lineage=lineage,
                    normalization=FieldNormalization.POWER,
                ),
            },
        )
    assert rejected.value.identity == (
        "assembly_wave_contributors_incompatible:owner=cube:"
        "encounter=cube_use:incident=bottom:outgoing=top:route=-:"
        "underlying=normalization_mismatch"
    )


def test_route_axis_swap_coregisters_asymmetric_sampling_and_jones_together() -> None:
    arm_length = 1.0e-3
    lineage = _SourceLineage()
    source_envelope = torch.arange(
        2 * _HEIGHT * _WIDTH,
        dtype=torch.float64,
    ).to(torch.complex128).reshape(1, 2, _HEIGHT, _WIDTH)
    source = _source(source_envelope, lineage=lineage)
    second_incident = _source(
        torch.zeros(
            (1, 2, _WIDTH, _HEIGHT),
            dtype=torch.complex128,
        ),
        lineage=lineage,
    )
    propagation = _RoutePropagationProbe(axial_distance=arm_length)
    first_owner = _cube(
        CubeCoatingDiagonal.RISING,
        mixing_angle=0.0,
    )
    second_owner = IdealNonpolarizingCubeBeamSplitter(
        origin=(arm_length, 0.0, 0.0),
        route_right=(1.0, 0.0, 0.0),
        route_top=(0.0, 0.0, 1.0),
        coating_diagonal=CubeCoatingDiagonal.RISING,
        mixing_angle=0.0,
    )
    transformed_grid = SpatialGrid(
        sample_counts=(_WIDTH, _HEIGHT),
        sample_spacing=(11.0e-6, 7.0e-6),
        first_sample_position=(-19.0e-6, -13.0e-6),
        orientation=("decreasing", "increasing"),
    )
    assembly = Assembly()
    assembly.include(source, name="source", grid=_grid())
    assembly.include(
        second_incident,
        name="second_incident",
        grid=transformed_grid,
    )
    assembly.include(propagation, name="outbound")
    assembly.include_directional(first_owner, name="first_cube")
    assembly.include_directional(second_owner, name="second_cube")
    first = assembly.wave_encounter(
        first_owner,
        name="first_use",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    second = assembly.wave_encounter(
        second_owner,
        name="second_use",
        incident_terminals=(CubeTerminal.LEFT, CubeTerminal.BOTTOM),
    )
    assembly.connect(
        source,
        first,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        first,
        propagation,
        source_terminal=CubeTerminal.RIGHT,
    )
    assembly.connect(
        propagation,
        second,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        second_incident,
        second,
        destination_terminal=CubeTerminal.BOTTOM,
    )
    assembly.expose(
        first,
        name="first_right",
        source_terminal=CubeTerminal.RIGHT,
    )
    assembly.end_route(
        first,
        source_terminal=CubeTerminal.TOP,
        reason="outside_modeled_system",
    )
    assembly.expose(
        second,
        name="second_right",
        source_terminal=CubeTerminal.RIGHT,
    )
    assembly.expose(
        second,
        name="second_top",
        source_terminal=CubeTerminal.TOP,
    )
    assembly.freeze()

    outputs = assembly._replay()  # noqa: SLF001

    propagated = propagation(outputs["first_right"])
    expected = torch.stack(
        (
            propagated.envelope[..., 1, :, :],
            -propagated.envelope[..., 0, :, :],
        ),
        dim=-3,
    ).transpose(-2, -1)
    assert outputs["second_right"].grid.is_physically_equivalent_to(
        transformed_grid,
    )
    torch.testing.assert_close(
        outputs["second_right"].envelope,
        expected,
        atol=5.0e-13,
        rtol=0.0,
    )
    assert outputs["second_top"].envelope.shape[-2:] == (
        _WIDTH,
        _HEIGHT,
    )


@pytest.mark.parametrize(
    ("corruption", "underlying"),
    (
        ("complex64", "optical_field_envelope_dtype_invalid"),
        ("nonfinite", "optical_field_envelope_nonfinite"),
    ),
)
def test_invalid_wave_input_has_stable_error_and_no_published_outputs(
    corruption: str,
    underlying: str,
) -> None:
    source = _source(
        _constant_envelope(),
        lineage=_SourceLineage(),
        corruption=corruption,
    )
    with pytest.raises(AssemblyError) as rejected:
        _run_cube(
            owner=_cube(CubeCoatingDiagonal.RISING),
            incident_sources={CubeTerminal.LEFT: source},
        )

    assert rejected.value.identity == (
        "assembly_wave_contributors_incompatible:owner=cube:"
        "encounter=cube_use:incident=left:outgoing=-:route=-:"
        f"underlying={underlying}"
    )


def test_gradients_reach_each_input_jones_lane_and_shared_owner_parameter() -> None:
    angle = torch.nn.Parameter(torch.tensor(0.31, dtype=torch.float64))
    owner = _cube(
        CubeCoatingDiagonal.FALLING,
        mixing_angle=angle,
    )
    lineage = _SourceLineage()
    envelopes = {
        terminal: _constant_envelope(
            horizontal=complex(index + 1.0, 0.2 * index),
            vertical=complex(0.3 * index + 0.5, -0.1 * index),
            requires_grad=True,
        )
        for index, terminal in enumerate(_TERMINALS)
    }
    _assembly, outputs = _run_cube(
        owner=owner,
        incident_sources={
            terminal: _source(envelope, lineage=lineage)
            for terminal, envelope in envelopes.items()
        },
    )
    loss = sum(
        (index + 1.0) * output.envelope.real.sum()
        + (index + 0.5) * output.envelope.imag.sum()
        for index, output in enumerate(outputs.values())
    )

    loss.backward()

    assert angle.grad is not None
    assert float(angle.grad.abs()) > 0.0
    for envelope in envelopes.values():
        assert envelope.grad is not None
        assert torch.count_nonzero(envelope.grad[:, 0]) > 0
        assert torch.count_nonzero(envelope.grad[:, 1]) > 0


def test_two_encounters_sum_gradients_on_one_owner_parameter() -> None:
    angle = torch.nn.Parameter(torch.tensor(0.29, dtype=torch.float64))
    owner = _cube(
        CubeCoatingDiagonal.RISING,
        mixing_angle=angle,
    )
    lineage = _SourceLineage()
    assembly = Assembly()
    first_source = _source(
        _constant_envelope(1.0 + 0.2j, 0.4 - 0.1j),
        lineage=lineage,
    )
    second_source = _source(
        _constant_envelope(0.7 - 0.3j, 0.2 + 0.5j),
        lineage=lineage,
    )
    assembly.include(first_source, name="first_source", grid=_grid())
    assembly.include(second_source, name="second_source", grid=_grid())
    assembly.include_directional(owner, name="cube")
    first = assembly.wave_encounter(
        owner,
        name="first_use",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    second = assembly.wave_encounter(
        owner,
        name="second_use",
        incident_terminals=(CubeTerminal.LEFT,),
    )
    assembly.connect(
        first_source,
        first,
        destination_terminal=CubeTerminal.LEFT,
    )
    assembly.connect(
        second_source,
        second,
        destination_terminal=CubeTerminal.LEFT,
    )
    for prefix, encounter in (("first", first), ("second", second)):
        assembly.expose(
            encounter,
            name=f"{prefix}_right",
            source_terminal=CubeTerminal.RIGHT,
        )
        assembly.expose(
            encounter,
            name=f"{prefix}_top",
            source_terminal=CubeTerminal.TOP,
        )
    assembly.freeze()
    outputs = assembly._replay()  # noqa: SLF001
    first_loss = outputs["first_right"].envelope.real.sum() + (
        0.7 * outputs["first_top"].envelope.imag.sum()
    )
    second_loss = 1.3 * outputs["second_right"].envelope.imag.sum() + (
        outputs["second_top"].envelope.real.sum()
    )

    first_gradient = torch.autograd.grad(
        first_loss,
        angle,
        retain_graph=True,
    )[0]
    second_gradient = torch.autograd.grad(
        second_loss,
        angle,
        retain_graph=True,
    )[0]
    summed_gradient = torch.autograd.grad(
        first_loss + second_loss,
        angle,
    )[0]

    torch.testing.assert_close(
        summed_gradient,
        first_gradient + second_gradient,
        atol=2.0e-12,
        rtol=2.0e-12,
    )
    assert len(
        [
            name
            for name, _parameter in assembly.named_parameters()
            if name == "cube.mixing_angle"
        ]
    ) == 1

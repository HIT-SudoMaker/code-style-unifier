from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import torch

from chromatix_next._numerics.optical_path_reference import (
    express_envelope_in_optical_path_reference,
)
import chromatix_next.errors as _errors

from . import _assembly_facts, _route_geometry
from ._coherence import _collect_coherent_field_findings
from .element.ideal_cube_beam_splitter import (
    CubeTerminal,
    IdealNonpolarizingCubeBeamSplitter,
    IdealPolarizingCubeBeamSplitter,
)
from .field import OpticalField, _transform_field
from .polarization import PolarizationRepresentation

_CubeOwner: TypeAlias = (
    IdealNonpolarizingCubeBeamSplitter
    | IdealPolarizingCubeBeamSplitter
)


@dataclass(frozen=True, slots=True)
class _WaveIncident:
    """
    关联一个 incident Terminal、来场与可选 Route 基传输

    """

    terminal: str
    field: OpticalField
    route_name: str | None
    route_transport: _route_geometry._RouteBasisTransport | None


def _wave_cube_outputs(
    *,
    owner: object,
    owner_name: str,
    encounter_name: str,
    terminal_order: tuple[str, ...],
    structural_routes: tuple[tuple[str, str], ...],
    incidents: tuple[_WaveIncident, ...],
    outgoing_terminals: tuple[str, ...],
) -> tuple[OpticalField, ...]:
    # 每个 output 独立收集结构贡献者，再消费 owner 的唯一闭合响应
    if not isinstance(
        owner,
        (
            IdealNonpolarizingCubeBeamSplitter,
            IdealPolarizingCubeBeamSplitter,
        ),
    ):
        raise _errors.AssemblyError(
            _assembly_facts._directional_finding(
                "assembly_encounter_owner_unsupported",
                owner=owner_name,
                encounter=encounter_name,
            ),
            "Wave Cube Encounter 只能消费冻结计划中的理想 NBS/PBS Cube owner",
        )
    incident_by_terminal = {
        incident.terminal: incident
        for incident in incidents
    }
    coating_fields = {
        terminal: _incident_field_in_coating_basis(
            owner=owner,
            owner_name=owner_name,
            encounter_name=encounter_name,
            incident=incident_by_terminal[terminal],
        )
        for terminal in terminal_order
        if terminal in incident_by_terminal
    }
    outputs: list[OpticalField] = []
    for outgoing_terminal in outgoing_terminals:
        contributor_terminals = tuple(
            terminal
            for terminal in terminal_order
            if terminal in coating_fields
            and (terminal, outgoing_terminal) in structural_routes
        )
        if not contributor_terminals:
            raise _errors.AssemblyError(
                _assembly_facts._directional_finding(
                    "assembly_connect_structural_zero",
                    owner=owner_name,
                    encounter=encounter_name,
                    outgoing=outgoing_terminal,
                ),
                "冻结 Encounter 声明了没有结构贡献者的 outgoing Terminal",
            )
        contributors = tuple(
            coating_fields[terminal]
            for terminal in contributor_terminals
        )
        _require_compatible_contributors(
            owner_name=owner_name,
            encounter_name=encounter_name,
            outgoing_terminal=outgoing_terminal,
            contributor_terminals=contributor_terminals,
            contributors=contributors,
            incident_by_terminal=incident_by_terminal,
        )
        reference = contributors[0]
        expressed_envelopes = tuple(
            express_envelope_in_optical_path_reference(
                envelope=field.envelope,
                wavelengths=field.spectrum.wavelengths,
                source_reference_lengths=field.path_reference.lengths,
                destination_reference_lengths=(
                    reference.path_reference.lengths
                ),
            )
            for field in contributors
        )
        terminal_envelopes = {
            terminal: envelope
            for terminal, envelope in zip(
                contributor_terminals,
                expressed_envelopes,
                strict=True,
            )
        }
        exact_zero = torch.zeros_like(reference.envelope)
        canonical_incident = torch.stack(
            tuple(
                terminal_envelopes.get(terminal, exact_zero).movedim(-3, -1)
                for terminal in terminal_order
            ),
            dim=-2,
        )
        canonical_outgoing = owner._canonical_response(  # noqa: SLF001
            canonical_incident,
        )
        outgoing_index = terminal_order.index(outgoing_terminal)
        coating_envelope = canonical_outgoing.select(
            dim=-2,
            index=outgoing_index,
        ).movedim(-1, -3)
        coating_output = _transform_field(
            reference,
            envelope=coating_envelope,
        )
        outputs.append(
            _outgoing_field_in_terminal_basis(
                owner=owner,
                field=coating_output,
                terminal=CubeTerminal(outgoing_terminal),
            )
        )
    return tuple(outputs)


def _incident_field_in_coating_basis(
    *,
    owner: _CubeOwner,
    owner_name: str,
    encounter_name: str,
    incident: _WaveIncident,
) -> OpticalField:
    _require_wave_input(
        owner_name=owner_name,
        encounter_name=encounter_name,
        incident=incident,
    )
    field = incident.field
    if incident.route_transport is not None:
        field = _transport_field(
            field,
            transport=incident.route_transport,
        )
    terminal = CubeTerminal(incident.terminal)
    frame = owner._terminal_frame(terminal)  # noqa: SLF001
    p_axis, s_axis = owner._coating_p_s_basis(  # noqa: SLF001
        frame.incident_direction,
    )
    transport = _basis_transport(
        source_horizontal=frame.incident_horizontal,
        source_vertical=frame.incident_vertical,
        destination_horizontal=p_axis,
        destination_vertical=s_axis,
    )
    return _transport_field(field, transport=transport)


def _outgoing_field_in_terminal_basis(
    *,
    owner: _CubeOwner,
    field: OpticalField,
    terminal: CubeTerminal,
) -> OpticalField:
    frame = owner._terminal_frame(terminal)  # noqa: SLF001
    p_axis, s_axis = owner._coating_p_s_basis(  # noqa: SLF001
        frame.outgoing_direction,
    )
    transport = _basis_transport(
        source_horizontal=p_axis,
        source_vertical=s_axis,
        destination_horizontal=frame.outgoing_horizontal,
        destination_vertical=frame.outgoing_vertical,
    )
    return _transport_field(field, transport=transport)


def _basis_transport(
    *,
    source_horizontal: torch.Tensor,
    source_vertical: torch.Tensor,
    destination_horizontal: torch.Tensor,
    destination_vertical: torch.Tensor,
) -> _route_geometry._RouteBasisTransport:
    transport = _route_geometry._basis_transport(
        source_horizontal=_route_geometry._fixed_vector(source_horizontal),
        source_vertical=_route_geometry._fixed_vector(source_vertical),
        destination_horizontal=_route_geometry._fixed_vector(
            destination_horizontal,
        ),
        destination_vertical=_route_geometry._fixed_vector(
            destination_vertical,
        ),
    )
    if transport is None:
        raise _errors.AssemblyError(
            _assembly_facts._directional_finding(
                "assembly_route_segment_basis_incompatible",
            ),
            "Cube Terminal 与 coating p/s 基必须形成同一有符号采样/Jones 置换",
        )
    return transport


def _transport_field(
    field: OpticalField,
    *,
    transport: _route_geometry._RouteBasisTransport,
) -> OpticalField:
    jones_envelope = _route_geometry._transport_jones_values(
        field.envelope,
        transport=transport,
    )
    envelope = _route_geometry._transport_sampling_values(
        jones_envelope,
        transport=transport,
    )
    grid = _route_geometry._transport_grid(
        field.grid,
        transport=transport,
    )
    return _transform_field(
        field,
        envelope=envelope,
        grid=grid,
    )


def _require_wave_input(
    *,
    owner_name: str,
    encounter_name: str,
    incident: _WaveIncident,
) -> None:
    field = incident.field
    underlying = "-"
    if not isinstance(field, OpticalField):
        underlying = "wave_cube_input_value_invalid"
    elif field.envelope.dtype is not torch.complex128:
        underlying = "optical_field_envelope_dtype_invalid"
    elif (
        field.polarization_representation
        is not PolarizationRepresentation.TRANSVERSE
        or field.envelope.shape[-3] != 2
    ):
        underlying = "wave_cube_polarization_representation_invalid"
    elif not field.envelope.is_meta and not bool(
        torch.isfinite(field.envelope).all()
    ):
        underlying = "optical_field_envelope_nonfinite"
    if underlying == "-":
        return
    raise _errors.AssemblyError(
        _assembly_facts._directional_finding(
            "assembly_wave_contributors_incompatible",
            owner=owner_name,
            encounter=encounter_name,
            incident=incident.terminal,
            route=incident.route_name or "-",
            underlying=underlying,
        ),
        "Wave Cube contributor 必须是有限、transverse、fixed-double OpticalField",
    )


def _require_compatible_contributors(
    *,
    owner_name: str,
    encounter_name: str,
    outgoing_terminal: str,
    contributor_terminals: tuple[str, ...],
    contributors: tuple[OpticalField, ...],
    incident_by_terminal: dict[str, _WaveIncident],
) -> None:
    reference = contributors[0]
    for terminal, contributor in zip(
        contributor_terminals[1:],
        contributors[1:],
        strict=True,
    ):
        findings = _collect_coherent_field_findings(
            reference,
            contributor,
            prefix="",
        )
        if not findings:
            continue
        incident = incident_by_terminal[terminal]
        raise _errors.AssemblyError(
            _assembly_facts._directional_finding(
                "assembly_wave_contributors_incompatible",
                owner=owner_name,
                encounter=encounter_name,
                incident=terminal,
                outgoing=outgoing_terminal,
                route=incident.route_name or "-",
                underlying=findings[0],
            ),
            "同一 outgoing Terminal 的结构贡献者必须在基变换后满足相干兼容性；"
            f"发现 {', '.join(findings)}",
        )

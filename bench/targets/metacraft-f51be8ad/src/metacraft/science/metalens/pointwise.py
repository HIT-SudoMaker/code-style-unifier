from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import math

import numpy
from numpy.typing import NDArray
import torch

from .aperture import (
    Aperture,
    Lattice,
    Response,
    State,
    form_reference_surface_field,
    require_assignment_lattice,
    reference_surface_cautions,
)
from .brief import ControlStrategy
from .design import MetalensDesign
from .geometric_phase import OrientationRelation
from .propagation_phase import (
    PropagationCellLibrary,
    PropagationResponse,
)
from ...authority import Document, Reference
from ...authority.reference import reference_matches
from ...canonical import encode_bytes
from ...field.reference_surface import (
    AdmittedReferenceSurface,
    ReferenceSurfaceResponse,
    RequestedInputBasis,
    restore_reference_surface,
)
from ...field.sample import (
    ComponentBasis,
    Field,
    FieldComponent,
    PlaneSurface,
)
from ..phase import (
    FULL_TURN,
    PHASE_KEY_SCALE,
    canonical_phase,
    phase_key,
)
from ..study import Caution


CELL_SURFACE_TABLE_SCHEMA = (
    "metacraft.science.metalens.pointwise.cell_surface_table"
)
GEOMETRIC_SURFACE_TRANSFORM_SCHEMA = (
    "metacraft.science.metalens.pointwise.geometric_surface_transform"
)
_FULL_TURN_KEY = int(
    (FULL_TURN * PHASE_KEY_SCALE).to_integral_value()
)
_GEOMETRIC_SURFACE_CONCERN = "analytic geometric-phase surface transform"
_GEOMETRIC_SURFACE_EXPLANATION = (
    "One admitted circular-input reference surface is decomposed into "
    "retained and converted circular channels; only the converted channel "
    "receives the declared analytic twice-orientation phase. The sampled "
    "coordinates are not presented as a separately solved rotated cell."
)


@dataclass(frozen=True, slots=True)
class CellSurface:
    """
    Couples one fabricable cell identity to its admitted sampled response.
    """

    cell_identity: str
    admitted: AdmittedReferenceSurface

    def __post_init__(self) -> None:
        """
        Refuse an unnamed fabrication cell.
        """

        if not self.cell_identity:
            raise ValueError("cell_surface_identity_empty")


@dataclass(frozen=True, slots=True)
class CellSurfaceTable:
    """
    Binds one admitted cell source to independently admitted surface patches.
    """

    source_reference: Reference
    surfaces: tuple[CellSurface, ...]

    def __post_init__(self) -> None:
        """
        Sort and validate one complete, unambiguous surface table.
        """

        if not self.surfaces:
            raise ValueError("cell_surface_table_empty")
        ordered = tuple(
            sorted(self.surfaces, key=lambda item: item.cell_identity)
        )
        identities = tuple(item.cell_identity for item in ordered)
        references = tuple(item.admitted.reference for item in ordered)
        if len(set(identities)) != len(identities):
            raise ValueError("cell_surface_identity_duplicate")
        if len(set(references)) != len(references):
            raise ValueError("cell_surface_reference_duplicate")
        _require_common_response(
            tuple(item.admitted.response for item in ordered)
        )
        object.__setattr__(self, "surfaces", ordered)

    @property
    def cell_identities(self) -> tuple[str, ...]:
        """
        Return the stable fabrication identities represented by the table.
        """

        return tuple(item.cell_identity for item in self.surfaces)

    def surface_for(self, cell_identity: str) -> AdmittedReferenceSurface:
        """
        Return one cell's admitted sampled response without an ambiguous key.
        """

        for surface in self.surfaces:
            if surface.cell_identity == cell_identity:
                return surface.admitted
        raise ValueError("cell_surface_missing")

    def document(self) -> Document:
        """
        Encode the exact source-to-surface association for authority admission.
        """

        return Document(
            CELL_SURFACE_TABLE_SCHEMA,
            {
                "source_reference": self.source_reference.as_mapping(),
                "surfaces": {
                    item.cell_identity: item.admitted.reference.as_mapping()
                    for item in self.surfaces
                },
            },
        )

    def reference_matches(self, reference: Reference) -> bool:
        """
        Verify one reference names this exact table and no reordered variant.
        """

        return reference_matches(reference, self.document().to_bytes())

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        fetch: Callable[[Reference], bytes],
    ) -> CellSurfaceTable:
        """
        Restore every admitted patch without repeating a solver observation.
        """

        if document.schema_identifier != CELL_SURFACE_TABLE_SCHEMA:
            raise ValueError("cell_surface_table_schema_invalid")
        values = _mapping(
            document.values,
            "cell_surface_table_document_invalid",
        )
        if set(values) != {"source_reference", "surfaces"}:
            raise ValueError("cell_surface_table_document_invalid")
        encoded = _mapping(
            values["surfaces"],
            "cell_surface_table_document_invalid",
        )
        restored = cls(
            source_reference=_reference(values["source_reference"]),
            surfaces=tuple(
                CellSurface(
                    str(identity),
                    restore_reference_surface(
                        _reference(reference),
                        fetch,
                    ),
                )
                for identity, reference in encoded.items()
            ),
        )
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("cell_surface_table_document_mismatch")
        return restored


@dataclass(frozen=True, slots=True)
class GeometricSurfaceTransform:
    """
    Records the analytic circular-channel transform of two linear patches.
    """

    orientation_relation_reference: Reference
    x_linear_response_reference: Reference
    y_linear_response_reference: Reference
    requested_input_basis: RequestedInputBasis
    phase_sign: int
    circular_basis: str = (
        "right=(x-i y)/sqrt(2); left=(x+i y)/sqrt(2)"
    )
    converted_channel_rule: str = (
        "circular input is formed by linear superposition; converted circular "
        "channel gains exp(i 2 phase_sign orientation)"
    )
    spatial_rule: str = "sampled coordinates remain unrotated"

    def __post_init__(self) -> None:
        """
        Refuse a non-circular request or an unsupported phase sign.
        """

        if self.requested_input_basis not in {
            RequestedInputBasis.RIGHT_CIRCULAR,
            RequestedInputBasis.LEFT_CIRCULAR,
        }:
            raise ValueError("geometric_surface_input_not_circular")
        if self.phase_sign not in {-1, 1}:
            raise ValueError("geometric_surface_phase_sign_invalid")

    def document(self) -> Document:
        """
        Encode the exact analytic transform without claiming a new solve.
        """

        return Document(
            GEOMETRIC_SURFACE_TRANSFORM_SCHEMA,
            {
                "circular_basis": self.circular_basis,
                "converted_channel_rule": self.converted_channel_rule,
                "orientations_reference": (
                    self.orientation_relation_reference.as_mapping()
                ),
                "phase_sign": self.phase_sign,
                "requested_input_basis": self.requested_input_basis.value,
                "x_linear_response_reference": (
                    self.x_linear_response_reference.as_mapping()
                ),
                "y_linear_response_reference": (
                    self.y_linear_response_reference.as_mapping()
                ),
                "spatial_rule": self.spatial_rule,
            },
        )

    def reference_matches(self, reference: Reference) -> bool:
        """
        Verify that one admitted reference names this exact transformation.
        """

        return reference_matches(reference, self.document().to_bytes())

    @classmethod
    def from_document(
        cls,
        document: Document,
    ) -> GeometricSurfaceTransform:
        """
        Restore one analytic transform without repeating a solver observation.
        """

        if document.schema_identifier != GEOMETRIC_SURFACE_TRANSFORM_SCHEMA:
            raise ValueError("geometric_surface_transform_schema_invalid")
        values = _mapping(
            document.values,
            "geometric_surface_transform_document_invalid",
        )
        if set(values) != {
            "circular_basis",
            "converted_channel_rule",
            "orientations_reference",
            "phase_sign",
            "requested_input_basis",
            "spatial_rule",
            "x_linear_response_reference",
            "y_linear_response_reference",
        }:
            raise ValueError("geometric_surface_transform_document_invalid")
        restored = cls(
            orientation_relation_reference=_reference(
                values["orientations_reference"]
            ),
            x_linear_response_reference=_reference(
                values["x_linear_response_reference"]
            ),
            y_linear_response_reference=_reference(
                values["y_linear_response_reference"]
            ),
            requested_input_basis=RequestedInputBasis(
                str(values["requested_input_basis"])
            ),
            phase_sign=int(str(values["phase_sign"])),
            circular_basis=str(values["circular_basis"]),
            converted_channel_rule=str(
                values["converted_channel_rule"]
            ),
            spatial_rule=str(values["spatial_rule"]),
        )
        if restored.document().to_bytes() != document.to_bytes():
            raise ValueError("geometric_surface_transform_document_mismatch")
        return restored


def derive_geometric_surface_transform(
    relation: OrientationRelation,
    x_linear_response: AdmittedReferenceSurface,
    y_linear_response: AdmittedReferenceSurface,
    *,
    relation_reference: Reference,
    requested_input_basis: RequestedInputBasis,
) -> GeometricSurfaceTransform:
    """
    Declare how two linear-input patches follow the admitted orientation law.
    """

    if not relation.reference_matches(relation_reference):
        raise ValueError("orientations_reference_mismatch")
    if (
        x_linear_response.response.requested_input_basis
        is not RequestedInputBasis.X_LINEAR
        or y_linear_response.response.requested_input_basis
        is not RequestedInputBasis.Y_LINEAR
    ):
        raise ValueError("geometric_surface_linear_pair_required")
    _require_common_response(
        (
            x_linear_response.response,
            y_linear_response.response,
        ),
        should_ignore_input_basis=True,
    )
    return GeometricSurfaceTransform(
        orientation_relation_reference=relation_reference,
        x_linear_response_reference=x_linear_response.reference,
        y_linear_response_reference=y_linear_response.reference,
        requested_input_basis=requested_input_basis,
        phase_sign=relation.phase_sign,
    )


def assign_pointwise_cells(
    design: MetalensDesign,
    library: PropagationCellLibrary,
    surfaces: CellSurfaceTable,
    *,
    surfaces_reference: Reference,
    device: str | None = None,
    maximum_sites_per_chunk: int = 65_536,
    lattice: Lattice | None = None,
    lattice_reference: Reference | None = None,
) -> Aperture:
    """
    Select one full-library cell at each occupied site by cyclic phase loss.

    Phase bins and lookup stay vectorized in Torch. Equal phase loss prefers
    greater transmitted magnitude and then the stable fabrication identity.
    Chunk capacity affects execution only; it is absent from the aperture
    evidence and identity.
    """

    if design.control_strategy is not ControlStrategy.PROPAGATION_PHASE:
        raise ValueError("pointwise_propagation_design_required")
    if surfaces.source_reference != library.evidence_reference:
        raise ValueError("cell_surface_source_mismatch")
    if not surfaces.reference_matches(surfaces_reference):
        raise ValueError("cell_surface_table_reference_mismatch")
    responses = tuple(
        sorted(
            library.responses,
            key=lambda item: (
                -_transmitted_magnitude_squared(item),
                item.cell.identity,
            ),
        )
    )
    cell_identities = tuple(item.cell.identity for item in responses)
    if set(cell_identities) != set(surfaces.cell_identities):
        raise ValueError("cell_surface_table_incomplete")
    lattice, lattice_evidence = require_assignment_lattice(
        design,
        spacing_nm=responses[0].cell.period_nm,
        lattice=lattice,
        lattice_reference=lattice_reference,
    )
    state_by_cell = {
        response.cell.identity: _pointwise_state(
            response,
            surfaces.surface_for(response.cell.identity).reference,
        )
        for response in responses
    }
    selected_cells = select_pointwise_cells(
        lattice.target_phase[lattice.is_occupied],
        responses,
        device=device,
        maximum_sites_per_chunk=maximum_sites_per_chunk,
    )
    sorted_cells = numpy.asarray(sorted(cell_identities), dtype=numpy.str_)
    sorted_states = numpy.asarray(
        [state_by_cell[identity].identity for identity in sorted_cells],
        dtype=numpy.str_,
    )
    selected_indices = numpy.searchsorted(sorted_cells, selected_cells)
    state_identities = numpy.full(
        lattice.is_occupied.shape,
        "",
        dtype=sorted_states.dtype,
    )
    state_identities[lattice.is_occupied] = sorted_states[selected_indices]
    evidence = tuple(
        dict.fromkeys(
            (
                surfaces_reference,
                library.evidence_reference,
                library.height_choice_reference,
                library.binding_reference,
                *lattice_evidence,
                *(response.source_reference for response in responses),
                *(
                    surface.admitted.reference
                    for surface in surfaces.surfaces
                ),
            )
        )
    )
    return Aperture(
        cells=tuple(response.cell for response in responses),
        states=tuple(
            state_by_cell[identity] for identity in sorted(state_by_cell)
        ),
        coordinates_nm=lattice.coordinates_nm,
        is_occupied=lattice.is_occupied,
        target_phase=lattice.target_phase,
        state_identities=state_identities,
        spacing_nm=lattice.spacing_nm,
        half_span_nm=lattice.half_span_nm,
        evidence=evidence,
        footprint=lattice.footprint,
        phase_levels=None,
    )


def select_pointwise_cells(
    target_phases: NDArray[numpy.floating],
    candidates: tuple[PropagationResponse, ...],
    *,
    device: str | None = None,
    maximum_sites_per_chunk: int = 65_536,
) -> NDArray[numpy.str_]:
    """
    Match phase bins in bounded Torch chunks without per-site library scans.
    """

    if not candidates:
        raise ValueError("pointwise_candidates_empty")
    if maximum_sites_per_chunk <= 0:
        raise ValueError("pointwise_chunk_invalid")
    phases = numpy.asarray(target_phases, dtype=numpy.float64)
    if not numpy.isfinite(phases).all():
        raise ValueError("pointwise_target_phase_not_finite")
    tie_order = tuple(
        sorted(
            candidates,
            key=lambda item: (
                -_transmitted_magnitude_squared(item),
                item.cell.identity,
            ),
        )
    )
    best_for_phase: dict[int, PropagationResponse] = {}
    tie_rank: dict[str, int] = {}
    for rank, candidate in enumerate(tie_order):
        tie_rank[candidate.cell.identity] = rank
        best_for_phase.setdefault(phase_key(candidate.realized_phase), candidate)
    ordered = tuple(
        candidate
        for _key, candidate in sorted(best_for_phase.items())
    )
    identities = numpy.asarray(
        [candidate.cell.identity for candidate in ordered],
        dtype=numpy.str_,
    )
    selected_device = device or _selected_device()
    target = torch.as_tensor(
        phases.reshape(-1),
        dtype=torch.float64,
        device=selected_device,
    )
    candidate_keys = torch.tensor(
        [phase_key(item.realized_phase) for item in ordered],
        dtype=torch.int64,
        device=selected_device,
    )
    candidate_ranks = torch.tensor(
        [tie_rank[item.cell.identity] for item in ordered],
        dtype=torch.int64,
        device=selected_device,
    )
    selected = numpy.empty(target.numel(), dtype=identities.dtype)
    scale = float(PHASE_KEY_SCALE)
    full_turn = float(FULL_TURN)
    for start in range(0, target.numel(), maximum_sites_per_chunk):
        stop = min(start + maximum_sites_per_chunk, target.numel())
        keys = torch.round(
            torch.remainder(target[start:stop], full_turn) * scale
        ).to(torch.int64)
        insertion = torch.searchsorted(candidate_keys, keys)
        upper = torch.remainder(insertion, candidate_keys.numel())
        lower = torch.remainder(insertion - 1, candidate_keys.numel())
        lower_distance = _cyclic_key_distance(
            keys,
            candidate_keys[lower],
        )
        upper_distance = _cyclic_key_distance(
            keys,
            candidate_keys[upper],
        )
        should_choose_upper = (upper_distance < lower_distance) | (
            (upper_distance == lower_distance)
            & (candidate_ranks[upper] < candidate_ranks[lower])
        )
        indices = torch.where(
            should_choose_upper,
            upper,
            lower,
        ).cpu().numpy()
        selected[start:stop] = identities[indices]
    return selected.reshape(phases.shape)


def restrict_surfaces_to_aperture(
    aperture: Aperture,
    surfaces: CellSurfaceTable,
) -> dict[str, AdmittedReferenceSurface]:
    """
    Relate used optical states to admitted patches through stable cell identity.
    """

    surface_by_cell = {
        item.cell_identity: item.admitted for item in surfaces.surfaces
    }
    used = set(
        aperture.state_identities[aperture.is_occupied].tolist()
    )
    table = {
        state.identity: surface_by_cell[state.cell_identity]
        for state in aperture.states
        if state.identity in used
    }
    if set(table) != used:
        raise ValueError("pointwise_surface_state_missing")
    return table


def form_pointwise_surface_field(
    aperture: Aperture,
    surfaces: CellSurfaceTable,
    *,
    aperture_reference: Reference,
) -> Field:
    """
    Form one propagation aperture field from its selected sampled patches.
    """

    sampled = form_reference_surface_field(
        aperture,
        responses=restrict_surfaces_to_aperture(aperture, surfaces),
        aperture_reference=aperture_reference,
    )
    return extract_tangential_field(sampled)


def extract_tangential_field(field: Field) -> Field:
    """
    Form the transverse boundary consumed by vector angular spectrum.

    The admitted reference-surface documents retain the complete Cartesian
    observation, including its normal component. The propagation boundary
    carries x and y only because the qualified vector realization reconstructs
    the longitudinal field from Maxwell transversality in the homogeneous
    output medium.
    """

    if (
        field.basis is not ComponentBasis.CARTESIAN
        or field.component_names != ("x", "y", "z")
    ):
        raise ValueError("cartesian_reference_surface_required")
    return Field(
        wavelength_m=field.wavelength_m,
        surface=field.surface,
        frame=field.frame,
        medium=field.medium,
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=(
            FieldComponent("x", field.electric("x")),
            FieldComponent("y", field.electric("y")),
        ),
        source_references=field.source_references,
        incident_reference_power=field.incident_reference_power,
    )


def form_geometric_surface_field(
    aperture: Aperture,
    relation: OrientationRelation,
    x_linear_response: AdmittedReferenceSurface,
    y_linear_response: AdmittedReferenceSurface,
    transform: GeometricSurfaceTransform,
    *,
    aperture_reference: Reference,
    transform_reference: Reference,
    device: str | None = None,
    maximum_sites_per_chunk: int = 65_536,
) -> Field:
    """
    Apply the admitted twice-orientation law to one circular-channel patch.

    The base sampled coordinates stay fixed. Only the declared converted
    circular channel receives geometric phase; no orientation is presented as
    another solver observation.
    """

    if aperture.phase_levels is not None:
        raise ValueError("continuous_geometric_aperture_required")
    if (
        transform.orientation_relation_reference not in aperture.evidence
        or transform.x_linear_response_reference
        != x_linear_response.reference
        or transform.y_linear_response_reference
        != y_linear_response.reference
        or transform.phase_sign != relation.phase_sign
        or not transform.reference_matches(transform_reference)
    ):
        raise ValueError("geometric_surface_transform_mismatch")
    x_response = x_linear_response.response
    y_response = y_linear_response.response
    _require_common_response(
        (x_response, y_response),
        should_ignore_input_basis=True,
    )
    if (
        x_response.requested_input_basis
        is not RequestedInputBasis.X_LINEAR
        or y_response.requested_input_basis
        is not RequestedInputBasis.Y_LINEAR
    ):
        raise ValueError("geometric_surface_linear_pair_required")
    field = x_response.field
    if (
        field.basis is not ComponentBasis.CARTESIAN
        or field.component_names != ("x", "y", "z")
    ):
        raise ValueError("geometric_surface_components_unsupported")
    if maximum_sites_per_chunk <= 0:
        raise ValueError("pointwise_chunk_invalid")
    selected_device = device or _selected_device()
    x_input_x = torch.tensor(
        x_response.field.electric("x"),
        dtype=torch.complex128,
        device=selected_device,
    )
    x_input_y = torch.tensor(
        x_response.field.electric("y"),
        dtype=torch.complex128,
        device=selected_device,
    )
    y_input_x = torch.tensor(
        y_response.field.electric("x"),
        dtype=torch.complex128,
        device=selected_device,
    )
    y_input_y = torch.tensor(
        y_response.field.electric("y"),
        dtype=torch.complex128,
        device=selected_device,
    )
    square_root_two = math.sqrt(2)
    incident_sign = (
        -1
        if transform.requested_input_basis
        is RequestedInputBasis.RIGHT_CIRCULAR
        else 1
    )
    electric_x = (
        x_input_x + incident_sign * 1j * y_input_x
    ) / square_root_two
    electric_y = (
        x_input_y + incident_sign * 1j * y_input_y
    ) / square_root_two
    right = (electric_x + 1j * electric_y) / square_root_two
    left = (electric_x - 1j * electric_y) / square_root_two
    phases = torch.tensor(
        aperture.target_phase.reshape(-1),
        dtype=torch.float64,
        device=selected_device,
    )
    is_occupied = torch.tensor(
        aperture.is_occupied.reshape(-1),
        dtype=torch.bool,
        device=selected_device,
    )
    converted_offset = float(relation.converted_phase)
    patch_rows, patch_columns = field.surface.shape
    period_m = aperture.spacing_nm * 1e-9
    if not (
        math.isclose(
            patch_rows * field.surface.spacing_m,
            period_m,
            rel_tol=0,
            abs_tol=1e-15,
        )
        and math.isclose(
            patch_columns * field.surface.spacing_m,
            period_m,
            rel_tol=0,
            abs_tol=1e-15,
        )
    ):
        raise ValueError("geometric_surface_patch_span_mismatch")
    site_count = phases.numel()
    output_x = numpy.zeros(
        (site_count, patch_rows, patch_columns),
        dtype=numpy.complex128,
    )
    output_y = numpy.zeros_like(output_x)
    for start in range(0, site_count, maximum_sites_per_chunk):
        stop = min(start + maximum_sites_per_chunk, site_count)
        phase = torch.exp(
            1j * (phases[start:stop] - converted_offset)
        )[:, None, None]
        if transform.requested_input_basis is RequestedInputBasis.RIGHT_CIRCULAR:
            right_chunk = right.expand(stop - start, -1, -1)
            left_chunk = left[None, :, :] * phase
        else:
            right_chunk = right[None, :, :] * phase
            left_chunk = left.expand(stop - start, -1, -1)
        is_occupied_batch = is_occupied[start:stop, None, None]
        formed_x = torch.where(
            is_occupied_batch,
            (right_chunk + left_chunk) / square_root_two,
            0,
        )
        formed_y = torch.where(
            is_occupied_batch,
            1j * (left_chunk - right_chunk) / square_root_two,
            0,
        )
        output_x[start:stop] = formed_x.cpu().numpy()
        output_y[start:stop] = formed_y.cpu().numpy()
    aperture_rows, aperture_columns = aperture.is_occupied.shape
    formed = []
    for name, values in (("x", output_x), ("y", output_y)):
        samples = (
            values.reshape(
                aperture_rows,
                aperture_columns,
                patch_rows,
                patch_columns,
            )
            .transpose(0, 2, 1, 3)
            .reshape(
                aperture_rows * patch_rows,
                aperture_columns * patch_columns,
            )
        )
        samples.setflags(write=False)
        formed.append(FieldComponent(name, samples))
    return Field(
        wavelength_m=field.wavelength_m,
        surface=PlaneSurface(
            position_m=field.surface.position_m,
            spacing_m=field.surface.spacing_m,
            shape=(
                aperture_rows * patch_rows,
                aperture_columns * patch_columns,
            ),
        ),
        frame=field.frame,
        medium=field.medium,
        basis=ComponentBasis.TRANSVERSE_LINEAR,
        electric_components=tuple(formed),
        source_references=tuple(
            dict.fromkeys(
                (
                    aperture_reference,
                    x_linear_response.reference,
                    y_linear_response.reference,
                    transform_reference,
                )
            )
        ),
        incident_reference_power=(
            aperture.site_count * field.incident_reference_power
        ),
    )


def identify_geometric_surface_cautions(
    transform: GeometricSurfaceTransform,
    transform_reference: Reference,
    x_linear_response: ReferenceSurfaceResponse,
    y_linear_response: ReferenceSurfaceResponse,
) -> tuple[Caution, ...]:
    """
    Keep response and analytic-transform limitations beside the result.
    """

    if not transform.reference_matches(transform_reference):
        raise ValueError("geometric_surface_transform_reference_mismatch")
    _require_common_response(
        (x_linear_response, y_linear_response),
        should_ignore_input_basis=True,
    )
    return (
        *reference_surface_cautions(
            x_linear_response,
            transform.x_linear_response_reference,
        ),
        Caution(
            concern=_GEOMETRIC_SURFACE_CONCERN,
            explanation=_GEOMETRIC_SURFACE_EXPLANATION,
            source_reference=transform_reference,
        ),
    )


def _pointwise_state(
    response: PropagationResponse,
    surface_reference: Reference,
) -> State:
    identity = _identity(
        encode_bytes(
            {
                "cell_identity": response.cell.identity,
                "response_reference": response.source_reference,
                "surface_reference": surface_reference,
            }
        )
    )
    return State(
        identity=identity,
        cell_identity=response.cell.identity,
        responses=(
            Response(
                channel="transmission",
                real_part=response.transmission_real,
                imaginary_part=response.transmission_imaginary,
                power=response.useful_power,
            ),
        ),
        source=surface_reference,
        target_phase=canonical_phase(response.realized_phase),
        realized_phase=canonical_phase(response.realized_phase),
        useful_power=response.useful_power,
        leakage_power=response.leakage_power,
    )


def _require_common_response(
    responses: tuple[ReferenceSurfaceResponse, ...],
    *,
    should_ignore_input_basis: bool = False,
) -> None:
    first = responses[0]
    field = first.field
    for response in responses[1:]:
        candidate = response.field
        if (
            candidate.wavelength_m != field.wavelength_m
            or candidate.surface != field.surface
            or candidate.frame != field.frame
            or candidate.medium != field.medium
            or candidate.basis is not field.basis
            or candidate.component_names != field.component_names
            or candidate.incident_reference_power
            != field.incident_reference_power
            or (
                not should_ignore_input_basis
                and response.requested_input_basis
                is not first.requested_input_basis
            )
            or response.order_regime != first.order_regime
            or response.assembly_model != first.assembly_model
        ):
            raise ValueError("cell_surface_context_mismatch")


def _transmitted_magnitude_squared(
    response: PropagationResponse,
) -> Decimal:
    return (
        response.transmission_real * response.transmission_real
        + response.transmission_imaginary * response.transmission_imaginary
    )


def _cyclic_key_distance(
    left: torch.Tensor,
    right: torch.Tensor,
) -> torch.Tensor:
    difference = torch.abs(left - right)
    return torch.minimum(difference, _FULL_TURN_KEY - difference)


def _selected_device() -> str:
    if torch.cuda.is_available():
        return f"cuda:{torch.cuda.current_device()}"
    return "cpu"


def _identity(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _reference(value: object) -> Reference:
    try:
        return Reference.from_mapping(
            _mapping(value, "pointwise_reference_invalid")
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("pointwise_reference_invalid") from error


def _mapping(
    value: object,
    finding: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value

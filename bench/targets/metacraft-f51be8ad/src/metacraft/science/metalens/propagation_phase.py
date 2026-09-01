from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
import hashlib

from .aperture import (
    Aperture,
    Cell,
    Circle,
    Lattice,
    Material,
    Response,
    Square,
    State,
    assign_quantized,
)
from ...authority.protocol import Document, Reference
from ...authority.reference import reference_matches
from ...canonical import canonicalize, encode_bytes
from .design import require_metalens_design
from ..phase import (
    FULL_TURN,
    canonical_phase,
    cyclic_distance,
    level_tolerance,
    phase_key,
    uniform_targets,
)
from ..result import EvidenceOrigin, require_exact_evidence
from ..study import Study


CELL_LIBRARY_SCHEMA = (
    "metacraft.science.metalens.propagation_phase.cell_library"
)
PERIODIC_TRANSMISSION_SCHEMA = (
    "metacraft.science.metalens.propagation_phase.periodic_transmission"
)
PHASE_SET_SCHEMA = "metacraft.science.metalens.propagation_phase.phase_set"
PHASE_IDENTITY_TOLERANCE = Decimal("1e-24")


@dataclass(frozen=True, slots=True, kw_only=True)
class PropagationResponse:
    """
    Binds one cell to its admitted complex transmission response.

    Identity follows the cell, response, and exact source reference; no
    route name is carried.
    """

    binding_reference: Reference
    height_choice_reference: Reference
    phase_planes: str
    cell: Cell
    transmission_real: Decimal
    transmission_imaginary: Decimal
    realized_phase: Decimal
    useful_power: Decimal
    leakage_power: Decimal
    solver_status: str
    warnings: tuple[str, ...]
    is_construction_valid: bool
    execution_origin: EvidenceOrigin
    source_reference: Reference

    def __post_init__(self) -> None:
        """
        Validate one propagation response.
        """
        if not self.phase_planes:
            raise ValueError("propagation_response_phase_planes_empty")
        values = (
            self.transmission_real,
            self.transmission_imaginary,
            self.realized_phase,
            self.useful_power,
            self.leakage_power,
        )
        if not all(value.is_finite() for value in values):
            raise ValueError("propagation_response_not_finite")
        object.__setattr__(
            self,
            "realized_phase",
            canonical_phase(self.realized_phase),
        )
        if self.useful_power < 0 or self.leakage_power < 0:
            raise ValueError("propagation_response_power_invalid")
        if self.solver_status != "complete":
            raise ValueError("propagation_response_incomplete")
        if not self.is_construction_valid:
            raise ValueError("propagation_construction_invalid")
        if self.cell.source != self.source_reference:
            raise ValueError("propagation_cell_source_mismatch")

    @property
    def phase_key(self) -> int:
        """
        Normalize phase to a stable integer lookup key.
        """

        return phase_key(self.realized_phase)

    @property
    def selection_order(self) -> tuple[int, int, str]:
        """
        State deterministic order independently of input enumeration.
        """

        return (
            self.phase_key,
            self.cell.geometry.span_nm,
            self.cell.identity,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PropagationCellLibrary:
    """
    Holds one admitted fixed-height propagation response library.

    Identity follows the binding, height choice, and admitted responses;
    no route name is carried.
    """

    binding_reference: Reference
    height_choice_reference: Reference
    evidence_reference: Reference
    phase_planes: str
    responses: tuple[PropagationResponse, ...]

    def __post_init__(self) -> None:
        """
        Validate one fixed-height propagation library.
        """
        if not self.phase_planes or not self.responses:
            raise ValueError("propagation_library_empty")
        cells = tuple(response.cell for response in self.responses)
        if {
            response.binding_reference for response in self.responses
        } != {self.binding_reference}:
            raise ValueError("propagation_library_binding_mixed")
        if {
            response.height_choice_reference for response in self.responses
        } != {self.height_choice_reference}:
            raise ValueError("propagation_library_height_choice_mixed")
        if {
            response.phase_planes for response in self.responses
        } != {self.phase_planes}:
            raise ValueError("propagation_library_phase_planes_mixed")
        if len({cell.identity for cell in cells}) != len(cells):
            raise ValueError("propagation_library_geometry_duplicate")
        if len({cell.height_nm for cell in cells}) != 1:
            raise ValueError("propagation_library_height_mixed")
        if len({cell.period_nm for cell in cells}) != 1:
            raise ValueError("propagation_library_period_mixed")
        if len({cell.shape for cell in cells}) != 1:
            raise ValueError("propagation_library_shape_mixed")
        if len({cell.atom for cell in cells}) != 1:
            raise ValueError("propagation_library_atom_material_mixed")
        if len({cell.substrate for cell in cells}) != 1:
            raise ValueError("propagation_library_substrate_material_mixed")
        if len(
            {response.execution_origin for response in self.responses}
        ) != 1:
            raise ValueError("propagation_library_execution_mixed")
        source_references = tuple(
            response.source_reference for response in self.responses
        )
        if len(set(source_references)) != len(source_references):
            raise ValueError("propagation_library_evidence_duplicate")
        if not reference_matches(
            self.evidence_reference,
            self.document().to_bytes(),
        ):
            raise ValueError("propagation_library_reference_mismatch")

    @property
    def height_nm(self) -> int:
        """
        Return the library's single qualified height.
        """
        return self.responses[0].cell.height_nm

    @property
    def source_references(self) -> tuple[Reference, ...]:
        """
        Return source evidence in stable response order.
        """
        return tuple(response.source_reference for response in self.responses)

    def document(self) -> Document:
        """
        Return the exact aggregate document named by the evidence reference.
        """

        return self.document_from(
            binding_reference=self.binding_reference,
            height_choice_reference=self.height_choice_reference,
            phase_planes=self.phase_planes,
            responses=self.responses,
        )

    @classmethod
    def document_from(
        cls,
        *,
        binding_reference: Reference,
        height_choice_reference: Reference,
        phase_planes: str,
        responses: tuple[PropagationResponse, ...],
    ) -> Document:
        """
        Form one fixed-height library before authority admission.
        """

        ordered = tuple(
            sorted(
                responses,
                key=lambda response: response.selection_order,
            )
        )
        return Document(
            CELL_LIBRARY_SCHEMA,
            {
                "binding_reference": binding_reference.as_mapping(),
                "height_choice_reference": height_choice_reference.as_mapping(),
                "phase_planes": phase_planes,
                "responses": {
                    response.cell.identity: _response_mapping(response)
                    for response in ordered
                },
            },
        )

    @classmethod
    def from_document(
        cls,
        document: Document,
        *,
        evidence_reference: Reference,
        binding_reference: Reference,
        height_choice_reference: Reference,
    ) -> PropagationCellLibrary:
        """
        Restore the exact scientific cells carried by one admitted library.
        """

        if document.schema_identifier != CELL_LIBRARY_SCHEMA:
            raise ValueError("propagation_library_schema_invalid")
        if not reference_matches(evidence_reference, document.to_bytes()):
            raise ValueError("propagation_library_reference_mismatch")
        values = _mapping(document.values, "propagation_library_document_invalid")
        if set(values) != {
            "binding_reference",
            "height_choice_reference",
            "phase_planes",
            "responses",
        }:
            raise ValueError("propagation_library_document_invalid")
        document_binding_reference = _reference(
            values["binding_reference"]
        )
        document_height_choice_reference = _reference(
            values["height_choice_reference"]
        )
        if document_binding_reference != binding_reference:
            raise ValueError("propagation_library_binding_stale")
        if document_height_choice_reference != height_choice_reference:
            raise ValueError("propagation_library_height_choice_stale")
        encoded_responses = _mapping(
            values["responses"],
            "propagation_library_document_invalid",
        )
        responses = tuple(
            _response_from_mapping(
                encoded,
                expected_identity=str(identity),
            )
            for identity, encoded in encoded_responses.items()
        )
        return cls(
            binding_reference=document_binding_reference,
            height_choice_reference=document_height_choice_reference,
            evidence_reference=evidence_reference,
            phase_planes=str(values["phase_planes"]),
            responses=responses,
        )


@dataclass(frozen=True, slots=True)
class PropagationPhaseState:
    """
    Records one target phase and its distinct selected cell.
    """

    phase_level: int
    phase_levels: int
    target_phase: Decimal
    realized_phase: Decimal
    phase_error: Decimal
    transmission_real: Decimal
    transmission_imaginary: Decimal
    useful_power: Decimal
    leakage_power: Decimal
    cell_id: str
    source_reference: Reference
    loss: Decimal
    selection_order: tuple[int, int, str]

    def __post_init__(self) -> None:
        """
        Validate one propagation-phase state.
        """
        values = (
            self.target_phase,
            self.realized_phase,
            self.phase_error,
            self.transmission_real,
            self.transmission_imaginary,
            self.useful_power,
            self.leakage_power,
            self.loss,
        )
        if not all(value.is_finite() for value in values):
            raise ValueError("phase_state_value_not_finite")
        object.__setattr__(
            self,
            "target_phase",
            canonical_phase(self.target_phase),
        )
        object.__setattr__(
            self,
            "realized_phase",
            canonical_phase(self.realized_phase),
        )
        if self.phase_levels <= 0 or not 0 <= self.phase_level < self.phase_levels:
            raise ValueError("phase_state_level_invalid")
        if self.useful_power < 0 or self.leakage_power < 0:
            raise ValueError("phase_state_power_invalid")
        realized_phase_key, feature_size_nm, cell_id = self.selection_order
        if (
            not isinstance(realized_phase_key, int)
            or not isinstance(feature_size_nm, int)
            or feature_size_nm <= 0
            or cell_id != self.cell_id
            or realized_phase_key != phase_key(self.realized_phase)
        ):
            raise ValueError("phase_state_selection_key_invalid")

    @property
    def state_id(self) -> str:
        """
        Derive stable optical-state identity without a floating lookup key.
        """

        realized_phase_key, feature_size_nm, _ = self.selection_order
        return _identity(
            encode_bytes(
                {
                    "cell_id": self.cell_id,
                    "feature_size_nm": feature_size_nm,
                    "phase_level": self.phase_level,
                    "phase_levels": self.phase_levels,
                    "realized_phase_key": realized_phase_key,
                    "source_reference": self.source_reference.as_mapping(),
                    "target_phase_key": phase_key(self.target_phase),
                }
            )
        )

    def as_mapping(self) -> dict[str, object]:
        """
        Return one traceable selection without binary phase values.
        """

        phase_key, feature_size_nm, cell_id = self.selection_order
        return {
            "cell_id": self.cell_id,
            "leakage_power": format(self.leakage_power, "f"),
            "loss": format(self.loss, "f"),
            "phase_error": format(self.phase_error, "f"),
            "phase_level": self.phase_level,
            "phase_levels": self.phase_levels,
            "realized_phase": format(self.realized_phase, "f"),
            "selection_order": {
                "cell_id": cell_id,
                "feature_size_nm": feature_size_nm,
                "phase_key": phase_key,
            },
            "source_reference": self.source_reference.as_mapping(),
            "state_id": self.state_id,
            "target_phase": format(self.target_phase, "f"),
            "transmission": {
                "imaginary": format(self.transmission_imaginary, "f"),
                "real": format(self.transmission_real, "f"),
            },
            "useful_power": format(self.useful_power, "f"),
        }


@dataclass(frozen=True, slots=True)
class PhaseSet:
    """
    Holds one independently comparable propagation-phase quantization.
    """

    levels: int
    states: tuple[PropagationPhaseState, ...]
    binding_reference: Reference
    height_choice_reference: Reference
    library_reference: Reference
    phase_planes: str
    global_phase_offset: Decimal = Decimal("0")
    useful_power_floor: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        """
        Validate one complete phase set.
        """
        if self.levels not in {8, 12, 16}:
            raise ValueError("phase_levels_unsupported")
        if len(self.states) != self.levels:
            raise ValueError("phase_set_incomplete")
        if tuple(state.phase_level for state in self.states) != tuple(
            range(self.levels)
        ):
            raise ValueError("phase_set_levels_invalid")
        if len({state.cell_id for state in self.states}) != self.levels:
            raise ValueError("phase_set_cells_not_distinct")
        if len({state.state_id for state in self.states}) != self.levels:
            raise ValueError("phase_set_states_not_distinct")
        if (
            not self.global_phase_offset.is_finite()
            or not self.useful_power_floor.is_finite()
            or self.useful_power_floor < 0
        ):
            raise ValueError("phase_set_response_gate_invalid")
        phase_step = FULL_TURN / Decimal(self.levels)
        object.__setattr__(
            self,
            "global_phase_offset",
            self.global_phase_offset % phase_step,
        )
        maximum_error = level_tolerance(self.levels)
        for target, state in zip(
            uniform_targets(self.levels),
            self.states,
            strict=True,
        ):
            expected_phase = canonical_phase(
                target + self.global_phase_offset
            )
            expected_error = cyclic_distance(
                expected_phase,
                state.realized_phase,
            )
            if (
                cyclic_distance(state.target_phase, target)
                > PHASE_IDENTITY_TOLERANCE
                or abs(state.phase_error - expected_error)
                > PHASE_IDENTITY_TOLERANCE
                or state.phase_error > maximum_error
            ):
                raise ValueError("phase_set_coverage_invalid")
            if state.useful_power <= self.useful_power_floor:
                raise ValueError("phase_set_useful_power_inadequate")

    @property
    def identity(self) -> str:
        """
        Derive this phase set's canonical identity.
        """
        return _identity(self.canonical_bytes())

    def canonical_bytes(self) -> bytes:
        """
        Return the canonical phase-set document bytes.
        """
        return encode_bytes(
            {
                "binding_reference": self.binding_reference.as_mapping(),
                "height_choice_reference": (
                    self.height_choice_reference.as_mapping()
                ),
                "global_phase_offset": format(
                    self.global_phase_offset,
                    "f",
                ),
                "levels": self.levels,
                "library_reference": self.library_reference.as_mapping(),
                "phase_planes": self.phase_planes,
                "state_identities": tuple(
                    state.state_id for state in self.states
                ),
                "useful_power_floor": format(
                    self.useful_power_floor,
                    "f",
                ),
            }
        )

    def document(self) -> Document:
        """
        Wrap the complete phase set for structured authority admission.
        """

        return Document(
            PHASE_SET_SCHEMA,
            self.as_mapping(),
        )

    def references(self) -> tuple[Reference, ...]:
        """
        Return the exact library, choice, binding, and response closure.
        """

        ordered = (
            self.binding_reference,
            self.height_choice_reference,
            self.library_reference,
            *(state.source_reference for state in self.states),
        )
        return tuple(dict.fromkeys(ordered))

    def reference_matches(self, reference: Reference) -> bool:
        """
        Verify that one admitted reference names this exact phase set.
        """

        return reference_matches(reference, self.document().to_bytes())

    def as_mapping(self) -> dict[str, object]:
        """
        Return the separate phase-set document shape used downstream.
        """

        return {
            "binding_reference": self.binding_reference.as_mapping(),
            "global_phase_offset": format(
                self.global_phase_offset,
                "f",
            ),
            "height_choice_reference": (
                self.height_choice_reference.as_mapping()
            ),
            "identity": self.identity,
            "levels": self.levels,
            "library_reference": self.library_reference.as_mapping(),
            "phase_planes": self.phase_planes,
            "states": {
                state.state_id: state.as_mapping() for state in self.states
            },
            "useful_power_floor": format(
                self.useful_power_floor,
                "f",
            ),
        }

    @classmethod
    def from_document(cls, document: Document) -> PhaseSet:
        """
        Restore one admitted phase set without rematching its library.
        """

        if document.schema_identifier != PHASE_SET_SCHEMA:
            raise ValueError("phase_set_schema_invalid")
        values = _mapping(document.values, "phase_set_document_invalid")
        if set(values) != {
            "binding_reference",
            "global_phase_offset",
            "height_choice_reference",
            "identity",
            "levels",
            "library_reference",
            "phase_planes",
            "states",
            "useful_power_floor",
        }:
            raise ValueError("phase_set_document_invalid")
        encoded_states = _mapping(
            values["states"],
            "phase_set_document_invalid",
        )
        states = tuple(
            sorted(
                (
                    _phase_state_from_mapping(
                        value,
                        identity=str(identity),
                    )
                    for identity, value in encoded_states.items()
                ),
                key=lambda state: state.phase_level,
            )
        )
        phase_set = cls(
            levels=_integer(values["levels"]),
            states=states,
            global_phase_offset=Decimal(
                str(values["global_phase_offset"])
            ),
            useful_power_floor=Decimal(
                str(values["useful_power_floor"])
            ),
            binding_reference=_reference(values["binding_reference"]),
            height_choice_reference=_reference(
                values["height_choice_reference"]
            ),
            library_reference=_reference(values["library_reference"]),
            phase_planes=str(values["phase_planes"]),
        )
        if (
            phase_set.identity != values["identity"]
            or phase_set.document().to_bytes() != document.to_bytes()
        ):
            raise ValueError("phase_set_document_mismatch")
        return phase_set


@dataclass(frozen=True, slots=True)
class PhaseSelection:
    """
    States the explicit response gate and joint matching policy.

    ``useful_power_floor`` is a strict lower bound. Its zero default preserves
    the existing call shape while preventing a zero-useful-power response from
    becoming a phase state; callers may declare a stronger floor explicitly.
    """

    phase_weight: Decimal = Decimal("1")
    useful_power_weight: Decimal = Decimal("0.1")
    leakage_weight: Decimal = Decimal("0.1")
    useful_power_floor: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        """
        Validate one quantized phase selection.
        """
        values = (
            self.phase_weight,
            self.useful_power_weight,
            self.leakage_weight,
        )
        if not all(value.is_finite() and value >= 0 for value in values):
            raise ValueError("phase_selection_weight_invalid")
        if self.phase_weight == 0:
            raise ValueError("phase_selection_phase_weight_required")
        if (
            not self.useful_power_floor.is_finite()
            or self.useful_power_floor < 0
        ):
            raise ValueError("phase_selection_useful_power_floor_invalid")


@dataclass(frozen=True, slots=True)
class PhaseCoverageDiagnostic:
    """
    Report phase-span context without turning it into a coverage verdict.

    The necessary span is only a one-way diagnostic. Exact qualification
    still requires one distinct, useful-power-qualified response inside each
    shifted target's cyclic half-step tolerance.
    """

    response_phase_span: Decimal
    qualified_phase_span: Decimal
    necessary_phase_span: Decimal
    has_necessary_qualified_span: bool
    evaluated_global_offsets: int

    def as_mapping(self) -> dict[str, object]:
        """
        Return the diagnostic quantities without claiming coverage.
        """

        return {
            "evaluated_global_offsets": self.evaluated_global_offsets,
            "has_necessary_qualified_span": (
                self.has_necessary_qualified_span
            ),
            "necessary_phase_span": format(
                self.necessary_phase_span,
                "f",
            ),
            "qualified_phase_span": format(
                self.qualified_phase_span,
                "f",
            ),
            "response_phase_span": format(
                self.response_phase_span,
                "f",
            ),
        }


@dataclass(frozen=True, slots=True)
class QuantizationRefusal:
    """
    Reports why one requested quantization could not be formed.
    """

    levels: int
    reason: str
    available_cells: int
    required_cells: int
    qualified_cells: int | None = None
    coverage_diagnostic: PhaseCoverageDiagnostic | None = None

    def as_mapping(self) -> dict[str, object]:
        """
        Return one refusal as exact arithmetic facts.
        """

        values: dict[str, object] = {
            "available_cells": self.available_cells,
            "levels": self.levels,
            "reason": self.reason,
            "required_cells": self.required_cells,
        }
        if self.qualified_cells is not None:
            values["qualified_cells"] = self.qualified_cells
        if self.coverage_diagnostic is not None:
            values["coverage_diagnostic"] = (
                self.coverage_diagnostic.as_mapping()
            )
        return values


@dataclass(frozen=True, slots=True)
class PhaseSetFormation:
    """
    Separates phase sets that formed from quantizations that did not.
    """

    phase_sets: tuple[PhaseSet, ...]
    refusals: tuple[QuantizationRefusal, ...]

    def __post_init__(self) -> None:
        """
        Validate one complete phase-set formation.
        """
        delivered = tuple(phase_set.levels for phase_set in self.phase_sets)
        refused = tuple(refusal.levels for refusal in self.refusals)
        if tuple(sorted((*delivered, *refused))) != (8, 12, 16):
            raise ValueError("phase_set_formation_incomplete")

    def as_mapping(self) -> dict[str, object]:
        """
        Report every delivered and refused quantization together.
        """

        return {
            "delivered": [
                phase_set.levels for phase_set in self.phase_sets
            ],
            "refused": [
                refusal.as_mapping() for refusal in self.refusals
            ],
        }


def form_phase_sets(
    library: PropagationCellLibrary,
    policy: PhaseSelection | None = None,
) -> tuple[PhaseSet, ...]:
    """
    Form every independently supported approved quantization.
    """

    return assess_phase_sets(library, policy).phase_sets


def assess_phase_sets(
    library: PropagationCellLibrary,
    policy: PhaseSelection | None = None,
) -> PhaseSetFormation:
    """
    Form every provable quantization and report each ordinary refusal.
    """

    selected_policy = policy or PhaseSelection()
    formed = []
    refusals = []
    for levels in (8, 12, 16):
        answer = _attempt_phase_set(library, levels, selected_policy)
        if isinstance(answer, QuantizationRefusal):
            refusals.append(answer)
        else:
            formed.append(answer)
    return PhaseSetFormation(tuple(formed), tuple(refusals))


def assign_aperture(
    study: Study,
    library: PropagationCellLibrary,
    phase_set: PhaseSet,
    phase_set_reference: Reference,
    *,
    lattice: Lattice | None = None,
    lattice_reference: Reference | None = None,
) -> Aperture:
    """
    Place one admitted quantized phase set over the metalens aperture.
    """

    library_reference = require_exact_evidence(
        study,
        "cell_library",
        library.document(),
    )
    if library_reference != library.evidence_reference:
        raise ValueError("cell_library_reference_mismatch")
    admitted = require_exact_evidence(
        study,
        "phase_set",
        phase_set.document(),
    )
    if admitted != phase_set_reference:
        raise ValueError("phase_set_reference_mismatch")
    _validate_phase_set_relationship(
        library,
        phase_set,
        phase_set_reference,
    )
    response_by_cell = {
        response.cell.identity: response for response in library.responses
    }
    cells = tuple(
        response_by_cell[state.cell_id].cell
        for state in phase_set.states
    )
    states = tuple(
        State(
            identity=state.state_id,
            cell_identity=state.cell_id,
            responses=(
                Response(
                    channel="transmission",
                    real_part=state.transmission_real,
                    imaginary_part=state.transmission_imaginary,
                    power=state.useful_power,
                ),
            ),
            source=state.source_reference,
            target_phase=state.target_phase,
            realized_phase=state.realized_phase,
            useful_power=state.useful_power,
            leakage_power=state.leakage_power,
            phase_level=state.phase_level,
        )
        for state in phase_set.states
    )
    evidence = tuple(
        dict.fromkeys(
            (
                phase_set_reference,
                phase_set.library_reference,
                phase_set.height_choice_reference,
                phase_set.binding_reference,
                *(state.source_reference for state in phase_set.states),
            )
        )
    )
    return assign_quantized(
        require_metalens_design(study),
        spacing_nm=library.responses[0].cell.period_nm,
        cells=cells,
        states=states,
        evidence=evidence,
        lattice=lattice,
        lattice_reference=lattice_reference,
    )


def _validate_phase_set_relationship(
    library: PropagationCellLibrary,
    phase_set: PhaseSet,
    phase_set_reference: Reference,
) -> None:
    if phase_set.library_reference != library.evidence_reference:
        raise ValueError("phase_set_library_mismatch")
    if phase_set.binding_reference != library.binding_reference:
        raise ValueError("phase_set_binding_mismatch")
    if phase_set.height_choice_reference != library.height_choice_reference:
        raise ValueError("phase_set_height_choice_mismatch")
    if phase_set.phase_planes != library.phase_planes:
        raise ValueError("phase_set_reference_plane_mismatch")
    if not phase_set.reference_matches(phase_set_reference):
        raise ValueError("phase_set_reference_mismatch")
    responses = {
        response.cell.identity: response for response in library.responses
    }
    for state in phase_set.states:
        response = responses.get(state.cell_id)
        if response is None:
            raise ValueError("phase_state_cell_missing")
        if (
            state.source_reference != response.source_reference
            or state.transmission_real != response.transmission_real
            or state.transmission_imaginary != response.transmission_imaginary
            or cyclic_distance(
                state.realized_phase,
                response.realized_phase,
            )
            > PHASE_IDENTITY_TOLERANCE
            or state.useful_power != response.useful_power
            or state.leakage_power != response.leakage_power
        ):
            raise ValueError("phase_state_response_mismatch")


def _attempt_phase_set(
    library: PropagationCellLibrary,
    levels: int,
    policy: PhaseSelection,
) -> PhaseSet | QuantizationRefusal:
    candidates = tuple(
        sorted(library.responses, key=lambda response: response.selection_order)
    )
    qualified = tuple(
        response
        for response in candidates
        if response.useful_power > policy.useful_power_floor
    )
    if len(candidates) < levels:
        return QuantizationRefusal(
            levels=levels,
            reason="cell_library_insufficient",
            available_cells=len(candidates),
            qualified_cells=len(qualified),
            required_cells=levels,
            coverage_diagnostic=_coverage_diagnostic(
                candidates,
                qualified,
                levels=levels,
                evaluated_global_offsets=0,
            ),
        )
    if len(qualified) < levels:
        return QuantizationRefusal(
            levels=levels,
            reason="cell_library_useful_power_inadequate",
            available_cells=len(candidates),
            qualified_cells=len(qualified),
            required_cells=levels,
            coverage_diagnostic=_coverage_diagnostic(
                candidates,
                qualified,
                levels=levels,
                evaluated_global_offsets=0,
            ),
        )
    targets = uniform_targets(levels)
    offsets = _global_phase_offsets(
        tuple(response.realized_phase for response in qualified),
        levels,
    )
    formations = tuple(
        formation
        for offset in offsets
        if (
            formation := _formation_at_offset(
                qualified,
                targets=targets,
                global_phase_offset=offset,
                policy=policy,
            )
        )
        is not None
    )
    if not formations:
        return QuantizationRefusal(
            levels=levels,
            reason="cell_library_coverage_inadequate",
            available_cells=len(candidates),
            qualified_cells=len(qualified),
            required_cells=levels,
            coverage_diagnostic=_coverage_diagnostic(
                candidates,
                qualified,
                levels=levels,
                evaluated_global_offsets=len(offsets),
            ),
        )
    (
        _rank,
        global_phase_offset,
        assignment,
        raw_costs,
    ) = min(formations, key=lambda item: item[0])
    shifted_targets = tuple(
        canonical_phase(target + global_phase_offset)
        for target in targets
    )
    states = []
    for level, candidate_index in enumerate(assignment):
        response = qualified[candidate_index]
        target = targets[level]
        error = cyclic_distance(
            shifted_targets[level],
            response.realized_phase,
        )
        assert error <= level_tolerance(levels)
        states.append(
            PropagationPhaseState(
                phase_level=level,
                phase_levels=levels,
                target_phase=target,
                realized_phase=canonical_phase(response.realized_phase),
                phase_error=error,
                transmission_real=response.transmission_real,
                transmission_imaginary=response.transmission_imaginary,
                useful_power=response.useful_power,
                leakage_power=response.leakage_power,
                cell_id=response.cell.identity,
                source_reference=response.source_reference,
                loss=raw_costs[level][candidate_index],
                selection_order=response.selection_order,
            )
        )
    return PhaseSet(
        levels=levels,
        states=tuple(states),
        global_phase_offset=global_phase_offset,
        useful_power_floor=policy.useful_power_floor,
        binding_reference=library.binding_reference,
        height_choice_reference=library.height_choice_reference,
        library_reference=library.evidence_reference,
        phase_planes=library.phase_planes,
    )


def _formation_at_offset(
    candidates: tuple[PropagationResponse, ...],
    *,
    targets: tuple[Decimal, ...],
    global_phase_offset: Decimal,
    policy: PhaseSelection,
) -> tuple[
    tuple[object, ...],
    Decimal,
    tuple[int, ...],
    tuple[tuple[Decimal, ...], ...],
] | None:
    """
    Form one exact distinct assignment at a canonical global offset.
    """

    shifted_targets = tuple(
        canonical_phase(target + global_phase_offset)
        for target in targets
    )
    raw_costs = tuple(
        tuple(_loss(target, response, policy) for response in candidates)
        for target in shifted_targets
    )
    maximum_error = level_tolerance(len(targets))
    is_allowed = tuple(
        tuple(
            cyclic_distance(target, response.realized_phase) <= maximum_error
            for response in candidates
        )
        for target in shifted_targets
    )
    if any(not any(row) for row in is_allowed):
        return None
    largest_allowed_cost = max(
        raw_costs[row][column]
        for row in range(len(targets))
        for column in range(len(candidates))
        if is_allowed[row][column]
    )
    forbidden_cost = (
        largest_allowed_cost + Decimal(1)
    ) * Decimal(len(targets) + 1)
    assignment = _assign(
        tuple(
            tuple(
                raw_costs[row][column]
                if is_allowed[row][column]
                else forbidden_cost
                for column in range(len(candidates))
            )
            for row in range(len(targets))
        )
    )
    if any(
        not is_allowed[row][column]
        for row, column in enumerate(assignment)
    ):
        return None
    errors = tuple(
        cyclic_distance(
            shifted_targets[row],
            candidates[column].realized_phase,
        )
        for row, column in enumerate(assignment)
    )
    losses = tuple(
        raw_costs[row][column]
        for row, column in enumerate(assignment)
    )
    rank: tuple[object, ...] = (
        sum(losses, Decimal(0)),
        max(errors),
        sum(errors, Decimal(0)),
        tuple(candidates[column].selection_order for column in assignment),
        phase_key(global_phase_offset),
    )
    return rank, global_phase_offset, assignment, raw_costs


def _global_phase_offsets(
    phases: tuple[Decimal, ...],
    levels: int,
) -> tuple[Decimal, ...]:
    """
    Enumerate every deterministic adjacency and loss breakpoint.

    A uniform level set is unchanged by an integer level step, so offsets are
    canonical on ``[0, 2*pi/levels)``. Adjacency changes only at half-step
    boundaries, while response alignments cover every piecewise-linear loss
    minimum. A boundary has every edge of its adjacent open regions because
    the half-step tolerance is inclusive, so no interval midpoint is needed.
    """

    phase_step = FULL_TURN / Decimal(levels)
    half_step = phase_step / Decimal(2)
    critical = {Decimal(0)}
    for phase in phases:
        alignment = canonical_phase(phase) % phase_step
        critical.add(alignment)
        critical.add((alignment - half_step) % phase_step)
    return tuple(sorted(critical))


def _coverage_diagnostic(
    responses: tuple[PropagationResponse, ...],
    qualified: tuple[PropagationResponse, ...],
    *,
    levels: int,
    evaluated_global_offsets: int,
) -> PhaseCoverageDiagnostic:
    """
    Report the familiar span check without using it as a verdict.
    """

    necessary_span = (
        FULL_TURN * Decimal(levels - 2) / Decimal(levels)
    )
    qualified_span = _minimum_covering_arc(
        tuple(response.realized_phase for response in qualified)
    )
    return PhaseCoverageDiagnostic(
        response_phase_span=_minimum_covering_arc(
            tuple(response.realized_phase for response in responses)
        ),
        qualified_phase_span=qualified_span,
        necessary_phase_span=necessary_span,
        has_necessary_qualified_span=qualified_span >= necessary_span,
        evaluated_global_offsets=evaluated_global_offsets,
    )


def _minimum_covering_arc(phases: tuple[Decimal, ...]) -> Decimal:
    """
    Return the shortest phase-circle arc containing every supplied phase.
    """

    ordered = tuple(sorted({canonical_phase(phase) for phase in phases}))
    if len(ordered) < 2:
        return Decimal(0)
    gaps = tuple(
        (
            ordered[index + 1] - phase
            if index + 1 < len(ordered)
            else ordered[0] + FULL_TURN - phase
        )
        for index, phase in enumerate(ordered)
    )
    return FULL_TURN - max(gaps)


def _response_from_mapping(
    value: object,
    *,
    expected_identity: str,
) -> PropagationResponse:
    response = _mapping(value, "propagation_response_document_invalid")
    if set(response) != {
        "binding_reference",
        "cell",
        "construction_valid",
        "execution_origin",
        "height_choice_reference",
        "leakage_power",
        "phase_planes",
        "realized_phase",
        "solver_status",
        "source_reference",
        "transmission_imaginary",
        "transmission_real",
        "useful_power",
        "warnings",
    }:
        raise ValueError("propagation_response_document_invalid")
    cell = _cell_from_mapping(response["cell"])
    if cell.identity != expected_identity:
        raise ValueError("propagation_library_cell_key_mismatch")
    warnings = response["warnings"]
    if not isinstance(warnings, (list, tuple)) or not all(
        isinstance(item, str) for item in warnings
    ):
        raise ValueError("propagation_response_document_invalid")
    if not isinstance(response["construction_valid"], bool):
        raise ValueError("propagation_response_document_invalid")
    return PropagationResponse(
        binding_reference=_reference(response["binding_reference"]),
        height_choice_reference=_reference(
            response["height_choice_reference"]
        ),
        phase_planes=str(response["phase_planes"]),
        cell=cell,
        transmission_real=Decimal(str(response["transmission_real"])),
        transmission_imaginary=Decimal(
            str(response["transmission_imaginary"])
        ),
        realized_phase=Decimal(str(response["realized_phase"])),
        useful_power=Decimal(str(response["useful_power"])),
        leakage_power=Decimal(str(response["leakage_power"])),
        solver_status=str(response["solver_status"]),
        warnings=tuple(warnings),
        is_construction_valid=response["construction_valid"],
        execution_origin=EvidenceOrigin(str(response["execution_origin"])),
        source_reference=_reference(response["source_reference"]),
    )


def _response_mapping(response: PropagationResponse) -> dict[str, object]:
    values = canonicalize(response)
    values["construction_valid"] = values.pop("is_construction_valid")
    cell = canonicalize(response.cell)
    cell["geometry"] = response.cell.geometry.as_mapping()
    values["cell"] = cell
    return values


def _phase_state_from_mapping(
    value: object,
    *,
    identity: str,
) -> PropagationPhaseState:
    state = _mapping(value, "phase_state_document_invalid")
    if set(state) != {
        "cell_id",
        "leakage_power",
        "loss",
        "phase_error",
        "phase_level",
        "phase_levels",
        "realized_phase",
        "selection_order",
        "source_reference",
        "state_id",
        "target_phase",
        "transmission",
        "useful_power",
    }:
        raise ValueError("phase_state_document_invalid")
    order = _mapping(
        state["selection_order"],
        "phase_state_document_invalid",
    )
    transmission = _mapping(
        state["transmission"],
        "phase_state_document_invalid",
    )
    if (
        set(order) != {"cell_id", "feature_size_nm", "phase_key"}
        or set(transmission) != {"imaginary", "real"}
    ):
        raise ValueError("phase_state_document_invalid")
    restored = PropagationPhaseState(
        phase_level=_integer(state["phase_level"]),
        phase_levels=_integer(state["phase_levels"]),
        target_phase=Decimal(str(state["target_phase"])),
        realized_phase=Decimal(str(state["realized_phase"])),
        phase_error=Decimal(str(state["phase_error"])),
        transmission_real=Decimal(str(transmission["real"])),
        transmission_imaginary=Decimal(str(transmission["imaginary"])),
        useful_power=Decimal(str(state["useful_power"])),
        leakage_power=Decimal(str(state["leakage_power"])),
        cell_id=str(state["cell_id"]),
        source_reference=_reference(state["source_reference"]),
        loss=Decimal(str(state["loss"])),
        selection_order=(
            _integer(order["phase_key"]),
            _integer(order["feature_size_nm"]),
            str(order["cell_id"]),
        ),
    )
    if restored.state_id != identity or state["state_id"] != identity:
        raise ValueError("phase_state_identity_mismatch")
    return restored


def _cell_from_mapping(value: object) -> Cell:
    cell = _mapping(value, "propagation_cell_document_invalid")
    if set(cell) != {
        "atom",
        "geometry",
        "height_nm",
        "identity",
        "period_nm",
        "source",
        "substrate",
    }:
        raise ValueError("propagation_cell_document_invalid")
    atom = _material_from_mapping(cell["atom"])
    substrate = _material_from_mapping(cell["substrate"])
    geometry_values = _mapping(
        cell["geometry"],
        "propagation_cell_document_invalid",
    )
    if set(geometry_values) == {"diameter_nm"}:
        geometry = Circle(_integer(geometry_values["diameter_nm"]))
    elif set(geometry_values) == {"width_nm"}:
        geometry = Square(_integer(geometry_values["width_nm"]))
    else:
        raise ValueError("propagation_cell_geometry_invalid")
    return Cell(
        identity=str(cell["identity"]),
        atom=atom,
        substrate=substrate,
        period_nm=_integer(cell["period_nm"]),
        height_nm=_integer(cell["height_nm"]),
        geometry=geometry,
        source=_reference(cell["source"]),
    )


def _material_from_mapping(value: object) -> Material:
    material = _mapping(value, "propagation_cell_material_invalid")
    if set(material) != {"name", "source"}:
        raise ValueError("propagation_cell_material_invalid")
    return Material(str(material["name"]), str(material["source"]))


def _reference(value: object) -> Reference:
    try:
        return Reference.from_mapping(
            _mapping(value, "propagation_reference_invalid")
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("propagation_reference_invalid") from error


def _mapping(value: object, finding: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(finding)
    return value


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("propagation_integer_invalid")
    return value


def _loss(
    target: Decimal,
    response: PropagationResponse,
    policy: PhaseSelection,
) -> Decimal:
    return (
        policy.phase_weight * cyclic_distance(target, response.realized_phase)
        + policy.useful_power_weight
        * max(Decimal(0), Decimal(1) - response.useful_power)
        + policy.leakage_weight * response.leakage_power
    )


def _assign(costs: tuple[tuple[Decimal, ...], ...]) -> tuple[int, ...]:
    """
    Solve one rectangular minimum-cost assignment with stable column order.
    """

    row_count = len(costs)
    column_count = len(costs[0])
    if row_count > column_count:
        raise ValueError("cell_library_insufficient")
    zero = Decimal(0)
    infinity = Decimal("Infinity")
    row_potential = [zero] * (row_count + 1)
    column_potential = [zero] * (column_count + 1)
    matched_row = [0] * (column_count + 1)
    path = [0] * (column_count + 1)
    for row in range(1, row_count + 1):
        matched_row[0] = row
        minimum = [infinity] * (column_count + 1)
        is_used = [False] * (column_count + 1)
        column = 0
        while True:
            is_used[column] = True
            current_row = matched_row[column]
            delta = infinity
            next_column = 0
            for candidate in range(1, column_count + 1):
                if is_used[candidate]:
                    continue
                reduced = (
                    costs[current_row - 1][candidate - 1]
                    - row_potential[current_row]
                    - column_potential[candidate]
                )
                if reduced < minimum[candidate]:
                    minimum[candidate] = reduced
                    path[candidate] = column
                if (
                    minimum[candidate] < delta
                    or (
                        minimum[candidate] == delta
                        and candidate < next_column
                    )
                ):
                    delta = minimum[candidate]
                    next_column = candidate
            for candidate in range(column_count + 1):
                if is_used[candidate]:
                    row_potential[matched_row[candidate]] += delta
                    column_potential[candidate] -= delta
                else:
                    minimum[candidate] -= delta
            column = next_column
            if matched_row[column] == 0:
                break
        while True:
            previous = path[column]
            matched_row[column] = matched_row[previous]
            column = previous
            if column == 0:
                break
    assignment = [0] * row_count
    for column in range(1, column_count + 1):
        if matched_row[column]:
            assignment[matched_row[column] - 1] = column - 1
    return tuple(assignment)
def _identity(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"
